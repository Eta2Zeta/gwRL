"""Resident declaration-offer scheduling and exact pass transitions.

This is the pass_interrupt subset of CampaignAdapter, not a registered campaign
backend. Raw declarations, phases and chance events are not implemented here.
Import and inspection are explicit host boundaries. Between them, decision
selection, validation, pass application and lane forks use device tensors only;
the packed native engine state, history and every RNG stream stay untouched.

The complete ordered raw interrupt menu is retained as resident ID/owner arrays.
Padding is the imported batch maximum, never a legal-action limit. A raw engine
mutation requires a fresh authoritative descriptor; generation counters alone
are not decision identities. Keys retain all 256 raw planning-key bits, order,
passed actors and the other decision fields.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
import hashlib
import json
import os
from typing import Any, Sequence

import torch
from torch import Tensor

from studies.shared.campaign_adapter import CampaignAdapter, SCHEMA, _field
from studies.shared.multiplayer_mcts import PLAYERS, action_key


PHASE_KINDS = ("production", "combat_movement", "combat", "non_combat_movement", "place_units")
TERMINAL, RAW_KIND, RAW_ACTOR, OWNERS, PASSED = range(5)
ORDER = slice(5, 8)
RAW_KEY = slice(8, 16)
METADATA_WIDTH = 16
_MPS_FALLBACK_AT_IMPORT = os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1"


class SchedulerError(IntFlag):
    SPECIFICATION = 1
    STALE_KEY = 2
    NO_OFFER = 4
    WRONG_ACTOR = 8


@dataclass(frozen=True, slots=True)
class DeviceSchedulerContext:
    # Host data are for explicit inspection, never read by the pass transition.
    raw_keys: tuple[tuple[tuple[int, ...], str], ...]
    kinds: tuple[str, ...]
    action_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeviceSchedulerBatch:
    context: DeviceSchedulerContext
    metadata: Tensor              # int64 [B,16]; layout constants above
    menu_ids: Tensor              # int64 [B,M], -1 padding
    menu_owners: Tensor           # int64 [B,M], -1 padding
    menu_lengths: Tensor         # int64 [B]

    @property
    def device(self) -> torch.device:
        return self.metadata.device

    @property
    def lane_count(self) -> int:
        return self.metadata.shape[0]

    def snapshot(self) -> DeviceSchedulerBatch:
        return type(self)(self.context, self.metadata.clone(), self.menu_ids.clone(),
                          self.menu_owners.clone(), self.menu_lengths.clone())

    def fork(self, lanes: Tensor) -> DeviceSchedulerBatch:
        """Device gather; repeated roots become independent destination lanes.

        Invalid resident indices become invalid descriptors (SPECIFICATION),
        never clamped aliases of another root or a hidden device-to-host read.
        """
        _layout(self)
        if (not isinstance(lanes, Tensor) or lanes.dtype != torch.int64 or
                lanes.device != self.device or lanes.ndim != 1):
            raise ValueError("Scheduler fork lanes must be a resident int64 vector")
        count, capacity = self.lane_count, self.menu_ids.shape[1]
        valid = (lanes >= 0) & (lanes < count)
        if count:
            safe = lanes.clamp(0, count - 1)
            metadata = self.metadata.index_select(0, safe)
            ids, owners = self.menu_ids.index_select(0, safe), self.menu_owners.index_select(0, safe)
            lengths = self.menu_lengths.index_select(0, safe)
        else:
            metadata = torch.zeros((lanes.shape[0], METADATA_WIDTH), dtype=torch.int64, device=self.device)
            ids = torch.full((lanes.shape[0], capacity), -1, dtype=torch.int64, device=self.device)
            owners, lengths = ids.clone(), torch.zeros_like(lanes)
        # An all-zero order contains duplicates and is explicitly invalid.
        metadata = torch.where(valid.unsqueeze(1), metadata, 0)
        ids, owners = torch.where(valid.unsqueeze(1), ids, -1), torch.where(valid.unsqueeze(1), owners, -1)
        lengths = torch.where(valid, lengths, 0)
        return type(self)(self.context, metadata, ids, owners, lengths)


@dataclass(frozen=True, slots=True)
class DeviceSchedulerDecision:
    keys: Tensor                  # complete descriptor snapshot [B,16]
    actor: Tensor                 # int64 [B], -1 means no raw owner
    offered: Tensor               # int64 [B], -1 means ordinary raw decision
    is_offer: Tensor              # bool [B]
    menu_mask: Tensor             # bool [B,M]; preserves raw menu positions/order
    errors: Tensor                # int64 [B]


@dataclass(frozen=True, slots=True)
class DevicePassResult:
    batch: DeviceSchedulerBatch
    errors: Tensor                # errors on selected lanes, zero elsewhere
    accepted: Tensor              # selected AND entire selected batch valid
    committed: Tensor             # scalar bool; no host reduction/read required


def _device(device: str | torch.device) -> torch.device:
    value = torch.device(device)
    if value.type not in {"cpu", "mps", "cuda"}:
        raise ValueError("Scheduler requires explicit cpu, mps or cuda tensors")
    if value.type == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS is unavailable; scheduler does not fall back to CPU")
        if _MPS_FALLBACK_AT_IMPORT or os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1":
            raise RuntimeError("MPS CPU fallback must be disabled for the scheduler")
        if value.index not in (None, 0):
            raise ValueError("MPS supports only device zero")
        from .metal_validation import require_lossless_mps_indexing
        require_lossless_mps_indexing()
    if value.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; scheduler does not fall back to CPU")
    return value


def _key_words(key: str) -> tuple[int, ...]:
    # Native planning keys are SHA256 hex. Preserve them directly, not a short
    # counter or a hash of just the visible board. Reject an unknown key schema.
    if not isinstance(key, str) or len(key) != 64 or key.lower() != key:
        raise ValueError("Scheduler import requires the complete native SHA256 planning key")
    try:
        raw = bytes.fromhex(key)
    except ValueError as error:
        raise ValueError("Native planning key is not SHA256 hex") from error
    if len(raw) != 32:
        raise ValueError("Native planning key is not SHA256 hex")
    return tuple(int.from_bytes(raw[start:start + 4], "big", signed=True) for start in range(0, 32, 4))


def capture_schedulers(adapters: Sequence[CampaignAdapter], *,
                       device: str | torch.device = "cpu") -> DeviceSchedulerBatch:
    """Import once from the authoritative cached adapter, without state JSON.

    This versioned bridge intentionally reads the existing adapter's scheduler
    cache: it retains *all* passed actors and reuses the full raw interrupt menu
    rather than rebuilding it per pass. No action is applied and no RNG drawn.
    """
    if not isinstance(adapters, (tuple, list)) or any(not isinstance(env, CampaignAdapter) for env in adapters):
        raise TypeError("Scheduler import requires CampaignAdapter lanes")
    target = _device(device)
    rows, menus, raw_keys, extra_kinds = [], [], {}, set()
    action_ids = [f"{SCHEMA}:pass:{actor}" for actor in PLAYERS]
    action_indices = {identity: index for index, identity in enumerate(action_ids)}
    for env in adapters:
        decision = env._decision_cache()
        raw_kind, terminal = env.raw.decision_kind(), bool(env.raw.is_terminal())
        raw_actor = env.raw.current_decision_player()
        if raw_actor is not None and raw_actor not in PLAYERS:
            raise ValueError("Raw decision names an unknown alliance")
        if len(env.interrupt_order) != 3 or set(env.interrupt_order) != set(PLAYERS):
            raise ValueError("Interrupt order must contain each alliance once")
        if not env._passed.issubset(PLAYERS):
            raise ValueError("Passed actors contain an unknown alliance")
        words = _key_words(env._anchor)
        raw_keys[words] = env._anchor
        if raw_kind not in PHASE_KINDS:
            extra_kinds.add(raw_kind)
        menu = []
        if not terminal and raw_kind in PHASE_KINDS:
            # _decision_cache has generated these once for this full raw key.
            for action in env._raw_interrupts or ():
                actor = _field(action, "player")
                if actor not in PLAYERS:
                    raise ValueError("Interrupt names an unknown decision owner")
                identity = f"{SCHEMA}:interrupt:{action_key(action)}"
                if identity not in action_indices:
                    action_indices[identity] = len(action_ids)
                    action_ids.append(identity)
                menu.append((action_indices[identity], PLAYERS.index(actor)))
        owners = sum(1 << actor for actor in {actor for _, actor in menu})
        passed = sum(1 << PLAYERS.index(actor) for actor in env._passed)
        rows.append([int(terminal), raw_kind, PLAYERS.index(raw_actor) if raw_actor is not None else -1,
                     owners, passed, *(PLAYERS.index(actor) for actor in env.interrupt_order), *words])
        menus.append(menu)
        # A cached canonical offer is a useful bridge-invariant check; no raw
        # action generation is needed to validate it.
        offered = next((actor for actor in env.interrupt_order if
                        owners & (1 << PLAYERS.index(actor)) and actor not in env._passed), None)
        if terminal or raw_kind not in PHASE_KINDS:
            offered = None
        if decision.offered != offered:
            raise ValueError("Authoritative scheduler descriptor changed during capture")
    kinds = (*PHASE_KINDS, *sorted(extra_kinds))
    for row in rows:
        row[RAW_KIND] = kinds.index(row[RAW_KIND])
    count, capacity = len(rows), max((len(menu) for menu in menus), default=0)
    metadata = torch.tensor(rows, dtype=torch.int64).reshape(count, METADATA_WIDTH)
    ids = torch.full((count, capacity), -1, dtype=torch.int64)
    owners = torch.full_like(ids, -1)
    lengths = torch.tensor([len(menu) for menu in menus], dtype=torch.int64)
    for lane, menu in enumerate(menus):
        if menu:
            ids[lane] = torch.tensor([item[0] for item in menu] + [-1] * (capacity - len(menu)))
            owners[lane] = torch.tensor([item[1] for item in menu] + [-1] * (capacity - len(menu)))
    context = DeviceSchedulerContext(tuple(raw_keys.items()), tuple(kinds), tuple(action_ids))
    return DeviceSchedulerBatch(context, metadata.to(target), ids.to(target), owners.to(target), lengths.to(target))


def _layout(batch: DeviceSchedulerBatch) -> tuple[int, int]:
    if not isinstance(batch, DeviceSchedulerBatch) or not isinstance(batch.context, DeviceSchedulerContext):
        raise TypeError("Expected a resident scheduler batch and immutable context")
    if not isinstance(batch.metadata, Tensor) or batch.metadata.ndim != 2:
        raise ValueError("Scheduler metadata must have [lane,field] shape")
    count = batch.metadata.shape[0]
    if not isinstance(batch.menu_ids, Tensor) or batch.menu_ids.ndim != 2:
        raise ValueError("Scheduler raw menu must have [lane,action] shape")
    capacity = batch.menu_ids.shape[1]
    shapes = ((count, METADATA_WIDTH), (count, capacity), (count, capacity), (count,))
    device = _device(batch.device)
    for value, shape in zip((batch.metadata, batch.menu_ids, batch.menu_owners, batch.menu_lengths), shapes, strict=True):
        if not isinstance(value, Tensor) or value.dtype != torch.int64 or value.device != device or tuple(value.shape) != shape:
            raise ValueError("Scheduler buffers must be int64 with complete matching shapes and device")
    if tuple(batch.context.kinds[:5]) != PHASE_KINDS or len(set(batch.context.kinds)) != len(batch.context.kinds):
        raise ValueError("Invalid scheduler raw-kind registry")
    if batch.context.action_ids[:3] != tuple(f"{SCHEMA}:pass:{actor}" for actor in PLAYERS):
        raise ValueError("Invalid canonical pass-action registry")
    if len(set(batch.context.action_ids)) != len(batch.context.action_ids):
        raise ValueError("Canonical interrupt-action IDs must be unique")
    return count, capacity


def scheduler_decisions(batch: DeviceSchedulerBatch) -> DeviceSchedulerDecision:
    """Validate and choose the next offer using resident integer operations."""
    count, capacity = _layout(batch)
    data = batch.metadata
    order = data[:, ORDER]
    invalid = ((data[:, TERMINAL] < 0) | (data[:, TERMINAL] > 1) |
               (data[:, RAW_KIND] < 0) | (data[:, RAW_KIND] >= len(batch.context.kinds)) |
               (data[:, RAW_ACTOR] < -1) | (data[:, RAW_ACTOR] > 2) |
               (data[:, OWNERS] < 0) | (data[:, OWNERS] > 7) |
               (data[:, PASSED] < 0) | (data[:, PASSED] > 7) |
               ((order < 0) | (order > 2)).any(1) |
               (order[:, 0] == order[:, 1]) | (order[:, 0] == order[:, 2]) | (order[:, 1] == order[:, 2]) |
               ((data[:, RAW_KEY] < -(2**31)) | (data[:, RAW_KEY] >= 2**31)).any(1) |
               (batch.menu_lengths < 0) | (batch.menu_lengths > capacity))
    position = torch.arange(capacity, dtype=torch.int64, device=batch.device).unsqueeze(0)
    active = position < batch.menu_lengths.unsqueeze(1)
    invalid = invalid | ((active & ((batch.menu_owners < 0) | (batch.menu_owners > 2) |
                                  (batch.menu_ids < 3) | (batch.menu_ids >= len(batch.context.action_ids)))) |
                                 (~active & ((batch.menu_ids != -1) | (batch.menu_owners != -1)))).any(1)
    powers = torch.tensor((1, 2, 4), dtype=torch.int64, device=batch.device)
    # The full menu is authoritative. No loss of multiplicity/order, and no
    # invented offer if a descriptor's owner mask disagrees with its raw menu.
    owner_flags = (active.unsqueeze(2) & (batch.menu_owners.unsqueeze(2) ==
                   torch.arange(3, device=batch.device).view(1, 1, 3))).any(1)
    actual_owners = (owner_flags.to(torch.int64) * powers).sum(1)
    invalid = invalid | (data[:, OWNERS] != actual_owners)
    phase = (data[:, RAW_KIND] >= 0) & (data[:, RAW_KIND] < len(PHASE_KINDS))
    invalid = invalid | ((data[:, TERMINAL].bool() | ~phase) & (batch.menu_lengths != 0))
    order_bits = powers[order.clamp(0, 2)]
    eligible = (((data[:, OWNERS].unsqueeze(1) & order_bits) != 0) &
                ((data[:, PASSED].unsqueeze(1) & order_bits) == 0))
    offered_position = torch.where(eligible, torch.arange(3, device=batch.device).view(1, 3), 3).amin(1)
    offer = (offered_position < 3) & phase & ~data[:, TERMINAL].bool() & ~invalid
    offered = torch.where(offer, order.gather(1, offered_position.clamp_max(2).unsqueeze(1)).squeeze(1), -1)
    actor = torch.where(offer, offered, data[:, RAW_ACTOR])
    mask = active & offer.unsqueeze(1) & (batch.menu_owners == offered.unsqueeze(1))
    errors = invalid.to(torch.int64) * int(SchedulerError.SPECIFICATION)
    return DeviceSchedulerDecision(data.clone(), actor, offered, offer, mask, errors)


def pass_interrupt(batch: DeviceSchedulerBatch, expected_keys: Tensor, actors: Tensor,
                   selected: Tensor) -> DevicePassResult:
    """Apply canonical pass actions, atomically across all selected lanes.

    A false committed scalar means no lane changed. Unselected padding lanes
    do not veto an otherwise valid selection. Errors and the scalar remain on
    device; inspecting them is an explicit caller choice, not a hidden sync.
    """
    decisions = scheduler_decisions(batch)
    count = batch.lane_count
    for value, shape, dtype in ((expected_keys, (count, METADATA_WIDTH), torch.int64),
                                (actors, (count,), torch.int64), (selected, (count,), torch.bool)):
        if not isinstance(value, Tensor) or tuple(value.shape) != shape or value.dtype != dtype or value.device != batch.device:
            raise ValueError("Pass selections require complete resident keys, int64 actors and a bool lane mask")
    errors = (decisions.errors |
              ((expected_keys != batch.metadata).any(1).to(torch.int64) * int(SchedulerError.STALE_KEY)) |
              ((~decisions.is_offer).to(torch.int64) * int(SchedulerError.NO_OFFER)) |
              ((actors != decisions.offered).to(torch.int64) * int(SchedulerError.WRONG_ACTOR)))
    errors = torch.where(selected, errors, 0)
    committed = ~(errors != 0).any()
    accepted = selected & committed
    bit = torch.tensor((1, 2, 4), dtype=torch.int64, device=batch.device)[actors.clamp(0, 2)]
    metadata = batch.metadata.clone()
    metadata[:, PASSED] = torch.where(accepted, metadata[:, PASSED] | bit, metadata[:, PASSED])
    result = DeviceSchedulerBatch(batch.context, metadata, batch.menu_ids, batch.menu_owners, batch.menu_lengths)
    return DevicePassResult(result, errors, accepted, committed)


def inspect_schedulers(batch: DeviceSchedulerBatch) -> tuple[dict[str, Any], ...]:
    """Canonical host inspection, including the existing public planning key."""
    decisions = scheduler_decisions(batch)
    rows = batch.metadata.detach().cpu().tolist()
    errors = decisions.errors.detach().cpu().tolist()
    offers = decisions.offered.detach().cpu().tolist()
    actors = decisions.actor.detach().cpu().tolist()
    menu_ids = batch.menu_ids.detach().cpu().tolist()
    mask = decisions.menu_mask.detach().cpu().tolist()
    keys = dict(batch.context.raw_keys)
    output = []
    for lane, row in enumerate(rows):
        if errors[lane]:
            raise ValueError(f"Invalid resident scheduler descriptor in lane {lane}")
        raw_key = keys.get(tuple(row[RAW_KEY]))
        if raw_key is None:
            raise ValueError("Resident scheduler raw key is absent from its import context")
        order = tuple(PLAYERS[index] for index in row[ORDER])
        passed = sorted(actor for index, actor in enumerate(PLAYERS) if row[PASSED] & (1 << index))
        key = hashlib.sha256(json.dumps({"schema": SCHEMA, "raw_key": raw_key, "order": order,
            "passed": passed}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        offered = PLAYERS[offers[lane]] if offers[lane] >= 0 else None
        actions = tuple(batch.context.action_ids[index] for index, active in zip(menu_ids[lane], mask[lane], strict=True) if active)
        if offered is not None:
            actions += (f"{SCHEMA}:pass:{offered}",)
        output.append({"key": key, "raw_key": raw_key, "order": order, "passed": tuple(passed),
            "actor": PLAYERS[actors[lane]] if actors[lane] >= 0 else None,
            "kind": "declaration_offer" if offered is not None else batch.context.kinds[row[RAW_KIND]],
            "terminal": bool(row[TERMINAL]), "offered": offered, "interrupt_action_ids": actions})
    return tuple(output)
