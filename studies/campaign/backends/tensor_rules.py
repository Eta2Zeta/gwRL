"""Device-resident integer implementation of campaign effectiveResults.

This is one rules primitive, not a campaign transition engine. It validates
complete supplied dice/reroll paths and computes modified results without
sampling randomness, creating casualties or advancing a game. Native C++ still
owns those effects and its explicit-outcome commit consumes full face paths.

All capacities are explicit tensor shapes, not rule limits. The host packer
uses the actual batch maxima and retains mismatched counts for device validation.
It rejects values/capacities outside int32 explicitly; it never truncates them.
The kernel reads only tensor metadata on the host and returns device error masks.
Packing and inspect_outcomes are separate, explicit host boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from enum import IntFlag
import os
from typing import Any, Sequence

import torch
from torch import Tensor


INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1
_MPS_FALLBACK_AT_IMPORT = os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1"


class DiceError(IntFlag):
    SPECIFICATION = 1
    DICE_COUNT = 2
    ROLL_COUNT = 4
    FACE_RANGE = 8
    REROLL_PATH = 16
    RESULT_OVERFLOW = 32


@dataclass(frozen=True, slots=True)
class TensorDiceBatch:
    sides: Tensor                 # [lane, die]
    modifiers: Tensor             # [lane, die]
    max_rerolls: Tensor            # [lane, die]
    reroll_faces: Tensor          # [lane, die, set entry], padded values ignored
    reroll_counts: Tensor         # [lane, die]
    faces: Tensor                 # [lane, die, roll], padded values ignored
    face_counts: Tensor           # [lane, die]
    dice_counts: Tensor           # [lane], request die count
    outcome_counts: Tensor        # [lane], supplied outcome die count

    def to(self, device: str | torch.device) -> TensorDiceBatch:
        target = _device(device)
        return type(self)(**{field.name: getattr(self, field.name).to(target) for field in fields(self)})


@dataclass(frozen=True, slots=True)
class TensorOutcomeResult:
    effective: Tensor             # int32 [lane, die]; invalid lanes are zeroed
    die_errors: Tensor            # int32 [lane, die], DiceError bits
    lane_errors: Tensor           # int32 [lane], DiceError bits
    dice_counts: Tensor           # original requested counts, retained on device

    @property
    def valid(self) -> Tensor:
        return self.lane_errors == 0


def _device(device: str | torch.device) -> torch.device:
    value = torch.device(device)
    if value.type not in {"cpu", "mps", "cuda"}:
        raise ValueError("Dice tensors support explicit cpu, mps or cuda devices")
    if value.type == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS was requested but is unavailable; no CPU fallback is used")
    if value.type == "mps" and (_MPS_FALLBACK_AT_IMPORT or os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1"):
        raise RuntimeError("MPS CPU fallback must be disabled for the dice kernel")
    if value.type == "mps" and value.index not in (None, 0):
        raise ValueError("MPS supports only its available device zero")
    if value.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable; no CPU fallback is used")
    if value.type == "cuda" and value.index is not None and value.index >= torch.cuda.device_count():
        raise ValueError("Requested CUDA device index is unavailable")
    return value


def _int32(value: Any) -> int:
    if type(value) is not int:
        raise TypeError("Dice specifications and faces require exact integers")
    if not INT32_MIN <= value <= INT32_MAX:
        raise OverflowError("Dice tensor integer exceeds int32; use the native reference explicitly")
    return value


def _sequence(value: Any, name: str) -> Sequence:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} requires a complete list or tuple")
    if len(value) > INT32_MAX:
        raise OverflowError(f"{name} exceeds int32 count capacity; it is not truncated")
    return value


def pack_outcomes(requests: Sequence[dict], outcomes: Sequence[Sequence[Sequence[int]]], *,
                  device: str | torch.device = "cpu") -> TensorDiceBatch:
    """Explicit host packing; no shape/face/specification is silently discarded.

    Each request is the public chance_request dictionary. This primitive uses
    its dice only; request identity/ownership and the corresponding game state
    remain the responsibility of the transition backend.
    """
    requests, outcomes = _sequence(requests, "Request batch"), _sequence(outcomes, "Outcome batch")
    if len(requests) != len(outcomes):
        raise ValueError("Request and outcome batches must have identical lane counts")
    parsed = []
    dice_capacity = roll_capacity = set_capacity = 0
    for request, outcome in zip(requests, outcomes, strict=True):
        if not isinstance(request, dict):
            raise TypeError("Each chance request must expose its complete dice specifications")
        dice, outcome = _sequence(request["dice"], "Request dice"), _sequence(outcome, "Outcome dice")
        specifications, rolls = [], []
        for die in dice:
            if not isinstance(die, dict):
                raise TypeError("Each die specification must be a dictionary")
            reroll = tuple(_int32(face) for face in _sequence(die["reroll_faces"], "Reroll faces"))
            if len(set(reroll)) != len(reroll):
                raise ValueError("Reroll faces represent a set and must be unique")
            specifications.append((_int32(die["sides"]), _int32(die["modifier"]),
                                   _int32(die["max_rerolls"]), reroll))
            set_capacity = max(set_capacity, len(reroll))
        for die in outcome:
            faces = tuple(_int32(face) for face in _sequence(die, "Die face path"))
            rolls.append(faces)
            roll_capacity = max(roll_capacity, len(faces))
        dice_capacity = max(dice_capacity, len(dice), len(outcome))
        parsed.append((specifications, rolls))
    lanes, dice = len(parsed), dice_capacity
    shape = (lanes, dice)
    # Fill host tensors once. Device transfer is explicit and separately timed
    # by callers; future device samplers can construct this structure directly.
    sides = torch.full(shape, 2, dtype=torch.int32)
    modifiers = torch.zeros(shape, dtype=torch.int32)
    max_rerolls = torch.zeros(shape, dtype=torch.int32)
    reroll_counts = torch.zeros(shape, dtype=torch.int32)
    face_counts = torch.zeros(shape, dtype=torch.int32)
    reroll_faces = torch.zeros((*shape, set_capacity), dtype=torch.int32)
    faces = torch.zeros((*shape, roll_capacity), dtype=torch.int32)
    dice_counts = torch.zeros(lanes, dtype=torch.int32)
    outcome_counts = torch.zeros(lanes, dtype=torch.int32)
    for lane, (specifications, rolls) in enumerate(parsed):
        dice_counts[lane], outcome_counts[lane] = len(specifications), len(rolls)
        for die, (side, modifier, maximum, reroll) in enumerate(specifications):
            sides[lane, die], modifiers[lane, die], max_rerolls[lane, die] = side, modifier, maximum
            reroll_counts[lane, die] = len(reroll)
            if reroll:
                reroll_faces[lane, die, :len(reroll)] = torch.tensor(reroll, dtype=torch.int32)
        for die, path in enumerate(rolls):
            face_counts[lane, die] = len(path)
            if path:
                faces[lane, die, :len(path)] = torch.tensor(path, dtype=torch.int32)
    return TensorDiceBatch(sides, modifiers, max_rerolls, reroll_faces, reroll_counts,
                           faces, face_counts, dice_counts, outcome_counts).to(device)


def _validate_layout(batch: TensorDiceBatch) -> tuple[int, int, int, int]:
    if not isinstance(batch, TensorDiceBatch):
        raise TypeError("Expected a TensorDiceBatch")
    if any(not isinstance(getattr(batch, field.name), Tensor) for field in fields(batch)):
        raise TypeError("Every dice field must be an explicit tensor")
    if not isinstance(batch.sides, Tensor) or batch.sides.ndim != 2:
        raise ValueError("Dice specifications require [lane, die] tensors")
    lanes, dice = batch.sides.shape
    if batch.faces.ndim != 3 or batch.reroll_faces.ndim != 3:
        raise ValueError("Faces and reroll sets require [lane, die, entry] tensors")
    rolls, sets = batch.faces.shape[-1], batch.reroll_faces.shape[-1]
    expected = {"sides": (lanes, dice), "modifiers": (lanes, dice), "max_rerolls": (lanes, dice),
                "reroll_counts": (lanes, dice), "face_counts": (lanes, dice),
                "faces": (lanes, dice, rolls), "reroll_faces": (lanes, dice, sets),
                "dice_counts": (lanes,), "outcome_counts": (lanes,)}
    if max(lanes, dice, rolls, sets) > INT32_MAX:
        raise OverflowError("Dice tensor capacity exceeds int32; no entries are truncated")
    device = _device(batch.sides.device)
    for field in fields(batch):
        value = getattr(batch, field.name)
        if not isinstance(value, Tensor) or value.dtype != torch.int32 or value.device != device:
            raise ValueError("Every dice tensor must be int32 on the same explicit device")
        if tuple(value.shape) != expected[field.name]:
            raise ValueError(f"Incorrect shape for dice tensor {field.name}")
    return lanes, dice, rolls, sets


def effective_results(batch: TensorDiceBatch) -> TensorOutcomeResult:
    """Compute exact integer results and validation masks entirely on device.

    Error masks can contain several bits, unlike C++'s first thrown exception.
    A lane is usable only when lane_errors == 0. There are no scalar tensor
    reads, host reductions, sampling calls, silent CPU fallbacks or lane loops.
    """
    lanes, dice, rolls, sets = _validate_layout(batch)
    device = batch.sides.device
    index = torch.arange(dice, dtype=torch.int32, device=device).unsqueeze(0)
    active = index < batch.dice_counts.unsqueeze(1)
    invalid_count = ((batch.dice_counts < 0) | (batch.dice_counts > dice) |
                     (batch.outcome_counts < 0) | (batch.outcome_counts > dice) |
                     (batch.dice_counts != batch.outcome_counts))
    lane_errors = invalid_count.to(torch.int32) * int(DiceError.DICE_COUNT)
    die_errors = torch.zeros_like(batch.sides)
    bad_spec = (batch.sides < 2) | (batch.max_rerolls < 0) | (batch.reroll_counts < 0) | (batch.reroll_counts > sets)
    if sets:
        set_index = torch.arange(sets, dtype=torch.int32, device=device).reshape(1, 1, sets)
        set_active = set_index < batch.reroll_counts.unsqueeze(-1)
        bad_spec = bad_spec | (set_active & ((batch.reroll_faces <= 0) |
                                      (batch.reroll_faces > batch.sides.unsqueeze(-1)))).any(dim=-1)
        # A static-capacity loop launches batched device comparisons; it never
        # reads a lane or count on the host and avoids [lane,die,set,set] memory.
        for entry in range(sets):
            duplicate = ((batch.reroll_faces == batch.reroll_faces[..., entry].unsqueeze(-1)) &
                         set_active & (set_index > entry) & (entry < batch.reroll_counts).unsqueeze(-1))
            bad_spec = bad_spec | duplicate.any(dim=-1)
    else:
        set_active = None
    bad_roll_count = ((batch.face_counts <= 0) | (batch.face_counts > rolls) |
                      (batch.face_counts.clamp(min=1) - 1 > batch.max_rerolls))
    if rolls:
        roll_index = torch.arange(rolls, dtype=torch.int32, device=device).reshape(1, 1, rolls)
        face_active = roll_index < batch.face_counts.unsqueeze(-1)
        bad_range = (face_active & ((batch.faces <= 0) | (batch.faces > batch.sides.unsqueeze(-1)))).any(dim=-1)
        if sets:
            # Keep temporary storage linear in the supplied tensor sizes;
            # arbitrary reroll-set lengths do not create a roll×set broadcast.
            reroll_member = torch.zeros_like(batch.faces, dtype=torch.bool)
            for entry in range(sets):
                reroll_member = reroll_member | ((batch.faces == batch.reroll_faces[..., entry].unsqueeze(-1)) &
                                                 (entry < batch.reroll_counts).unsqueeze(-1))
        else:
            reroll_member = torch.zeros_like(batch.faces, dtype=torch.bool)
        must_reroll = reroll_member & (roll_index < batch.max_rerolls.unsqueeze(-1))
        has_next = roll_index < (batch.face_counts.clamp(min=1) - 1).unsqueeze(-1)
        bad_path = (face_active & (must_reroll != has_next)).any(dim=-1)
        last = roll_index == (batch.face_counts.clamp(min=1) - 1).unsqueeze(-1)
        final_face = torch.where(last, batch.faces, torch.zeros_like(batch.faces)).sum(dim=-1, dtype=torch.int32)
    else:
        bad_range = bad_path = torch.zeros_like(batch.sides, dtype=torch.bool)
        final_face = torch.zeros_like(batch.sides)
    # A valid face is positive, so an int32 modifier cannot underflow. Compare
    # before trusting addition, without requiring unsupported float64/int64 math.
    bad_overflow = (final_face > 0) & (batch.modifiers > INT32_MAX - final_face.clamp(min=0))
    for bit, condition in ((DiceError.SPECIFICATION, bad_spec), (DiceError.ROLL_COUNT, bad_roll_count),
                           (DiceError.FACE_RANGE, bad_range), (DiceError.REROLL_PATH, bad_path),
                           (DiceError.RESULT_OVERFLOW, bad_overflow)):
        flagged = condition & active
        die_errors = die_errors | (flagged.to(torch.int32) * int(bit))
        lane_errors = lane_errors | (flagged.any(dim=1).to(torch.int32) * int(bit))
    effective = torch.where(active & (lane_errors == 0).unsqueeze(1),
                            final_face + batch.modifiers, torch.zeros_like(final_face))
    return TensorOutcomeResult(effective, die_errors, lane_errors, batch.dice_counts)


def inspect_outcomes(result: TensorOutcomeResult) -> tuple[dict[str, Any], ...]:
    """Explicit diagnostic synchronization; never called by the device kernel."""
    values, dies, errors, counts = (value.detach().cpu().tolist() for value in
        (result.effective, result.die_errors, result.lane_errors, result.dice_counts))
    rows = []
    for value, die, error, count in zip(values, dies, errors, counts, strict=True):
        usable_count = max(0, min(count, len(value)))
        rows.append({"valid": error == 0, "errors": error,
                     "effective": tuple(value[:usable_count]), "die_errors": tuple(die[:usable_count])})
    return tuple(rows)


def effective_results_metal(batch: TensorDiceBatch) -> TensorOutcomeResult:
    """Opt in to the fused MPS primitive; the portable default is unchanged."""
    from .tensor_rules_metal import effective_results_metal as execute
    return execute(batch)
