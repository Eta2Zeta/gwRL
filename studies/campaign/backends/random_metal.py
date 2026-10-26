"""Exact native SplitMix64 chance sampling on the Apple GPU.

Each GPU lane consumes its own execution/search/training stream in native die
order, including rejection sampling and conditional rerolls. This does not commit
combat/political effects. Invalid lanes retain their original random state and
return errors; no lane, face path or stream is silently discarded. Host packing
and inspection are explicit boundaries, not part of the resident operation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
import threading
from typing import Sequence

import torch
from torch import Tensor

from .tensor_rules import INT32_MAX, TensorDiceBatch, _device, _validate_layout, pack_outcomes

MASK64 = (1 << 64) - 1
STREAMS = ("actual", "search", "training")


@dataclass(frozen=True, slots=True)
class TensorRandomStreams:
    # int64 is only the storage type: all stream bits are unsigned uint64.
    streams: Tensor             # [lane, 3]
    active: Tensor              # int32 [lane], actual/search/training = 0/1/2
    test_tape: Tensor           # int32 [lane, capacity], actual lengths below
    tape_counts: Tensor         # int32 [lane]
    tape_positions: Tensor      # int64 [lane]

    def to(self, device):
        target = _device(device)
        return type(self)(*(getattr(self, name).to(target) for name in self.__dataclass_fields__))


@dataclass(frozen=True, slots=True)
class SampledChance:
    dice: TensorDiceBatch
    random: TensorRandomStreams
    effective: Tensor
    errors: Tensor


def _counter(value):
    if isinstance(value, str):
        if not value or not value.isascii() or not value.isdecimal() or (len(value) > 1 and value[0] == "0"):
            raise ValueError("Invalid canonical unsigned counter")
        value = int(value)
    if type(value) is not int or not 0 <= value <= MASK64:
        raise ValueError("Random counters must be exact unsigned64 integers")
    return value


def pack_random_streams(rows: Sequence[dict], *, device="cpu") -> TensorRandomStreams:
    """Pack complete privileged random snapshots, never neural observations."""
    rows = tuple(rows)
    if len(rows) > INT32_MAX:
        raise OverflowError("Random lane capacity exceeds int32; no lanes truncated")
    parsed = []
    for row in rows:
        if set(row) != {*STREAMS, "active", "test_tape", "tape_position"}:
            raise ValueError("Random snapshot fields do not match native schema")
        active = row["active"]
        if active not in STREAMS:
            raise ValueError("Unknown active random stream")
        tape = tuple(row["test_tape"])
        if len(tape) > INT32_MAX or any(type(v) is not int or not 0 < v <= INT32_MAX for v in tape):
            raise ValueError("Test tape must retain complete positive native int32 faces")
        position = _counter(row["tape_position"])
        if position > len(tape):
            raise ValueError("Test tape position exceeds tape length")
        bits = [_counter(row[name]) for name in STREAMS]
        parsed.append(([v if v < (1 << 63) else v - (1 << 64) for v in bits],
                       STREAMS.index(active), tape, position))
    lanes, capacity = len(rows), max((len(row[2]) for row in parsed), default=0)
    states = torch.empty((lanes, 3), dtype=torch.int64)
    active = torch.empty(lanes, dtype=torch.int32)
    tape = torch.zeros((lanes, capacity), dtype=torch.int32)
    counts = torch.empty(lanes, dtype=torch.int32)
    positions = torch.empty(lanes, dtype=torch.int64)
    for lane, (bits, selected, values, position) in enumerate(parsed):
        states[lane] = torch.tensor(bits, dtype=torch.int64)
        active[lane], counts[lane], positions[lane] = selected, len(values), position
        if values:
            tape[lane, :len(values)] = torch.tensor(values, dtype=torch.int32)
    return TensorRandomStreams(states, active, tape, counts, positions).to(device)


def pack_chance_requests(requests, *, device="cpu") -> TensorDiceBatch:
    """Allocate the actual maximum potential face path, with no reroll cap."""
    batch = pack_outcomes(requests, [[] for _ in requests])
    maximum = max((die["max_rerolls"] for request in requests for die in request["dice"]), default=-1)
    rolls = max(0, maximum + 1)
    if rolls > INT32_MAX:
        raise OverflowError("Required roll capacity exceeds int32; no path is truncated")
    batch = replace(batch, faces=torch.zeros((*batch.sides.shape, rolls), dtype=torch.int32),
                    outcome_counts=batch.dice_counts.clone())
    return batch.to(device)


SOURCE = r"""
#include <metal_stdlib>
using namespace metal;

inline ulong next_random(thread ulong& state) {
    ulong value = (state += 0x9e3779b97f4a7c15UL);
    value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9UL;
    value = (value ^ (value >> 27)) * 0x94d049bb133111ebUL;
    return value ^ (value >> 31);
}

inline int native_roll(thread ulong& state, int sides) {
    const ulong bound = ulong(sides), threshold = (ulong(0) - bound) % bound;
    ulong value;
    do { value = next_random(state); } while (value < threshold);
    return int(value % bound) + 1;
}

kernel void sample_chance(
    device const int* sides [[buffer(0)]],
    device const int* modifiers [[buffer(1)]],
    device const int* max_rerolls [[buffer(2)]],
    device const int* reroll_faces [[buffer(3)]],
    device const int* reroll_counts [[buffer(4)]],
    device const int* dice_counts [[buffer(5)]],
    device const ulong* streams [[buffer(6)]],
    device const int* active [[buffer(7)]],
    device const int* tape [[buffer(8)]],
    device const int* tape_counts [[buffer(9)]],
    device const long* positions [[buffer(10)]],
    device int* faces [[buffer(11)]],
    device int* face_counts [[buffer(12)]],
    device int* effective [[buffer(13)]],
    device ulong* new_streams [[buffer(14)]],
    device long* new_positions [[buffer(15)]],
    device int* errors [[buffer(16)]],
    device const int* dims [[buffer(17)]],
    uint lane [[thread_position_in_grid]]) {
    const int lanes = dims[0], dice = dims[1], rolls = dims[2], sets = dims[3], tapes = dims[4];
    if (lane >= uint(lanes)) return;
    const ulong row = ulong(lane) * ulong(dice);
    int error = 0;
    const int count = dice_counts[lane], selected = active[lane], tape_count = tape_counts[lane];
    long position = positions[lane];
    if (count < 0 || count > dice) error |= 1;
    if (selected < 0 || selected > 2) error |= 4;
    if (tape_count < 0 || tape_count > tapes || position < 0 || position > tape_count) error |= 8;
    for (int entry = 0; entry < max(0, min(tape_count, tapes)); ++entry)
        if (tape[ulong(lane) * ulong(tapes) + ulong(entry)] <= 0) error |= 8;
    for (int die = 0; die < dice; ++die) {
        const ulong index = row + ulong(die);
        effective[index] = 0; face_counts[index] = 0;
        for (int roll = 0; roll < rolls; ++roll) faces[index * ulong(rolls) + ulong(roll)] = 0;
        if (die >= count) continue;
        const int side = sides[index], maximum = max_rerolls[index], entries = reroll_counts[index];
        if (side < 2 || maximum < 0 || entries < 0 || entries > sets) { error |= 2; continue; }
        if (maximum >= rolls) error |= 128;
        for (int entry = 0; entry < entries; ++entry) {
            const int face = reroll_faces[index * ulong(sets) + ulong(entry)];
            if (face <= 0 || face > side) error |= 2;
            for (int other = entry + 1; other < entries; ++other)
                if (face == reroll_faces[index * ulong(sets) + ulong(other)]) error |= 2;
        }
    }
    ulong state = 0;
    if (selected >= 0 && selected <= 2) state = streams[ulong(lane) * 3 + ulong(selected)];
    if (!error) for (int die = 0; die < count; ++die) {
        const ulong index = row + ulong(die);
        const int side = sides[index], maximum = max_rerolls[index], entries = reroll_counts[index];
        int final_face = 0;
        for (int roll = 0; roll <= maximum; ++roll) {
            int face;
            if (tape_count) {
                if (position >= tape_count) { error |= 16; break; }
                face = tape[ulong(lane) * ulong(tapes) + ulong(position)];
                if (face <= 0 || face > side) { error |= 32; break; }
                ++position;
            } else face = native_roll(state, side);
            faces[index * ulong(rolls) + ulong(roll)] = face;
            face_counts[index] = roll + 1;
            final_face = face;
            bool reroll = false;
            for (int entry = 0; entry < entries; ++entry)
                reroll |= face == reroll_faces[index * ulong(sets) + ulong(entry)];
            if (!reroll) break;
        }
        if (error) break;
        if (modifiers[index] > 2147483647 - final_face) { error |= 64; break; }
        effective[index] = as_type<int>(as_type<uint>(final_face) + as_type<uint>(modifiers[index]));
    }
    for (int stream = 0; stream < 3; ++stream)
        new_streams[ulong(lane) * 3 + ulong(stream)] =
            !error && stream == selected ? state : streams[ulong(lane) * 3 + ulong(stream)];
    new_positions[lane] = error ? positions[lane] : position;
    errors[lane] = error;
    if (error) for (int die = 0; die < dice; ++die) {
        const ulong index = row + ulong(die);
        effective[index] = 0; face_counts[index] = 0;
        for (int roll = 0; roll < rolls; ++roll) faces[index * ulong(rolls) + ulong(roll)] = 0;
    }
}
"""

_library = None
_lock = threading.Lock()


@lru_cache(maxsize=8)
def _dimensions(shape):
    return torch.tensor(shape, dtype=torch.int32, device="mps")


@lru_cache(maxsize=1)
def _dummy():
    return torch.empty(1, dtype=torch.int64, device="mps")


def sample_chance_metal(batch: TensorDiceBatch, random: TensorRandomStreams) -> SampledChance:
    """One dispatch; inputs are unchanged, output streams advance valid lanes."""
    global _library
    shape = _validate_layout(batch)
    lanes, dice, rolls, sets = shape
    device = batch.sides.device
    if device.type != "mps":
        raise ValueError("This exact sampler requires Apple MPS tensors; no fallback")
    expected = {"streams": ((lanes, 3), torch.int64), "active": ((lanes,), torch.int32),
                "test_tape": ((lanes, random.test_tape.shape[-1]), torch.int32),
                "tape_counts": ((lanes,), torch.int32), "tape_positions": ((lanes,), torch.int64)}
    for name, (dimensions, dtype) in expected.items():
        value = getattr(random, name)
        if value.device != device or value.dtype != dtype or tuple(value.shape) != dimensions:
            raise ValueError(f"Invalid random tensor layout: {name}")
    tensors = [getattr(batch, name) for name in ("sides", "modifiers", "max_rerolls", "reroll_faces", "reroll_counts", "dice_counts")]
    tensors += [getattr(random, name) for name in random.__dataclass_fields__]
    if any(not value.is_contiguous() for value in (*tensors, batch.faces)):
        raise ValueError("Metal sampling requires contiguous inputs; no hidden copy")
    if random.test_tape.shape[-1] > INT32_MAX:
        raise OverflowError("Tape capacity exceeds int32; no entries truncated")
    faces, counts, effective = torch.empty_like(batch.faces), torch.empty_like(batch.face_counts), torch.empty_like(batch.sides)
    streams, positions = torch.empty_like(random.streams), torch.empty_like(random.tape_positions)
    errors = torch.empty_like(batch.dice_counts)
    result = SampledChance(replace(batch, faces=faces, face_counts=counts, outcome_counts=batch.dice_counts),
                           replace(random, streams=streams, tape_positions=positions), effective, errors)
    if not lanes:
        return result
    if not hasattr(torch.mps, "compile_shader"):
        raise RuntimeError("Apple GPU sampling requires torch.mps.compile_shader")
    if _library is None:
        with _lock:
            if _library is None:
                _library = torch.mps.compile_shader(SOURCE)
    tensors += [faces, counts, effective, streams, positions, errors, _dimensions((*shape, random.test_tape.shape[-1]))]
    _library.sample_chance(*(value if value.numel() else _dummy() for value in tensors), threads=lanes)
    return result


def inspect_sampled_chance(result: SampledChance) -> tuple[dict, ...]:
    """Explicit diagnostic synchronization, including privileged RNG state."""
    faces, counts, dice, effective, errors, states, active, tape, lengths, positions = (
        value.detach().cpu().tolist() for value in (result.dice.faces, result.dice.face_counts,
            result.dice.dice_counts, result.effective, result.errors, result.random.streams,
            result.random.active, result.random.test_tape, result.random.tape_counts, result.random.tape_positions))
    rows = []
    for lane, count in enumerate(dice):
        rows.append({'error': errors[lane], 'faces': [faces[lane][die][:counts[lane][die]] for die in range(max(0, min(count, len(counts[lane]))))],
                     'effective': effective[lane][:max(0, count)],
                     'random': {**{name: str(states[lane][index] & MASK64) for index, name in enumerate(STREAMS)},
                                'active': STREAMS[active[lane]] if 0 <= active[lane] < 3 else 'invalid',
                                'test_tape': tape[lane][:max(0, lengths[lane])], 'tape_position': str(positions[lane])}})
    return tuple(rows)
