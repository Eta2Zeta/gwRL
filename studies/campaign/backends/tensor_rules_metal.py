"""Explicit fused Metal dice primitive; CPU/CUDA keep the portable Torch path.

One dispatch validates/results all dice, with one GPU thread per lane. The shader
is embedded in this tracked module so runtime source fingerprints include it.
No rule/state transitions, RNG sampling or scalar host reads occur here.
"""
from functools import lru_cache
import threading
import time

import torch

from .tensor_rules import TensorOutcomeResult, _validate_layout


SOURCE = r"""
#include <metal_stdlib>
using namespace metal;

kernel void dice_effective(
    device const int* sides [[buffer(0)]],
    device const int* modifiers [[buffer(1)]],
    device const int* max_rerolls [[buffer(2)]],
    device const int* reroll_faces [[buffer(3)]],
    device const int* reroll_counts [[buffer(4)]],
    device const int* faces [[buffer(5)]],
    device const int* face_counts [[buffer(6)]],
    device const int* dice_counts [[buffer(7)]],
    device const int* outcome_counts [[buffer(8)]],
    device int* effective [[buffer(9)]],
    device int* die_errors [[buffer(10)]],
    device int* lane_errors [[buffer(11)]],
    device const int* dimensions [[buffer(12)]],
    uint lane [[thread_position_in_grid]]) {
    const int lanes = dimensions[0], dice = dimensions[1];
    const int rolls = dimensions[2], sets = dimensions[3];
    if (lane >= uint(lanes)) return;
    const int requested = dice_counts[lane], supplied = outcome_counts[lane];
    int lane_error = requested < 0 || requested > dice || supplied < 0 || supplied > dice || requested != supplied ? 2 : 0;
    for (int die = 0; die < dice; ++die) {
        const ulong index = ulong(lane) * ulong(dice) + ulong(die);
        effective[index] = 0;
        die_errors[index] = 0;
        if (die >= requested) continue;
        const int side = sides[index], modifier = modifiers[index];
        const int maximum = max_rerolls[index], set_count = reroll_counts[index];
        const int face_count = face_counts[index];
        const int present_sets = max(0, min(set_count, sets));
        const int present_faces = max(0, min(face_count, rolls));
        const int final_index = max(face_count, 1) - 1;
        int error = side < 2 || maximum < 0 || set_count < 0 || set_count > sets ? 1 : 0;
        for (int set = 0; set < present_sets; ++set) {
            const int face = reroll_faces[index * ulong(sets) + ulong(set)];
            if (face <= 0 || face > side) error |= 1;
            for (int other = set + 1; other < present_sets; ++other)
                if (face == reroll_faces[index * ulong(sets) + ulong(other)]) error |= 1;
        }
        if (face_count <= 0 || face_count > rolls || final_index > maximum) error |= 4;
        for (int roll = 0; roll < present_faces; ++roll) {
            const int face = faces[index * ulong(rolls) + ulong(roll)];
            if (face <= 0 || face > side) error |= 8;
            bool member = false;
            for (int set = 0; set < present_sets; ++set)
                member |= face == reroll_faces[index * ulong(sets) + ulong(set)];
            const bool must_reroll = member && roll < maximum;
            const bool has_next = roll < final_index;
            if (must_reroll != has_next) error |= 16;
        }
        // Match the portable error masks even for malformed count metadata:
        // its clamped last-index selection may read the first padded face.
        const int final_face = final_index < rolls ? faces[index * ulong(rolls) + ulong(final_index)] : 0;
        if (final_face > 0 && modifier > 2147483647 - final_face) error |= 32;
        die_errors[index] = error;
        lane_error |= error;
        // Unsigned modular arithmetic avoids signed-overflow UB, including on
        // invalid data that will be zeroed before any consumer can use it.
        effective[index] = as_type<int>(as_type<uint>(final_face) + as_type<uint>(modifier));
    }
    lane_errors[lane] = lane_error;
    if (lane_error != 0)
        for (int die = 0; die < dice; ++die)
            effective[ulong(lane) * ulong(dice) + ulong(die)] = 0;
}
"""

_library = None
_kernel = None
_compilation_seconds = 0.0
_library_lock = threading.Lock()


@lru_cache(maxsize=8)
def _shape_buffer(shape):
    return torch.tensor(shape, dtype=torch.int32, device="mps")


@lru_cache(maxsize=1)
def _dummy():
    return torch.empty(1, dtype=torch.int32, device="mps")


def metal_compilation_stats():
    """Host-only diagnostic; shader compilation is lazy and measured separately."""
    return {"compiled": _kernel is not None, "compilation_seconds": _compilation_seconds}


def effective_results_metal(batch):
    """Explicit contiguous MPS path, with exact device result/error tensors.

    Compilation and shape-buffer creation occur lazily on first use; callers
    measuring steady-state execution must report that first call separately.
    Noncontiguous input is rejected instead of inserting a hidden tensor copy.
    """
    global _library, _kernel, _compilation_seconds
    shape = _validate_layout(batch)
    if batch.sides.device.type != "mps":
        raise ValueError("Metal requires MPS tensors; use portable effective_results for CPU/CUDA")
    if any(not getattr(batch, name).is_contiguous() for name in batch.__dataclass_fields__):
        raise ValueError("Metal requires contiguous input tensors; no hidden copy is performed")
    lanes, dice, _, _ = shape
    effective = torch.empty_like(batch.sides)
    die_errors = torch.empty_like(batch.sides)
    lane_errors = torch.empty_like(batch.dice_counts)
    if not lanes:
        return TensorOutcomeResult(effective, die_errors, lane_errors, batch.dice_counts)
    if not hasattr(torch.mps, "compile_shader"):
        raise RuntimeError("This explicit Metal primitive requires torch.mps.compile_shader; no CPU fallback")
    if _kernel is None:
        with _library_lock:
            if _kernel is None:
                before = time.perf_counter()
                _library = torch.mps.compile_shader(SOURCE)
                _kernel = _library.dice_effective
                _compilation_seconds = time.perf_counter() - before
    tensors = [getattr(batch, name) for name in batch.__dataclass_fields__]
    tensors.extend((effective, die_errors, lane_errors, _shape_buffer(shape)))
    # Zero-sized buffers are never accessed by the corresponding capacity-zero
    # loops. Bind an owning dummy to avoid an invalid null Metal buffer argument.
    arguments = [value if value.numel() else _dummy() for value in tensors]
    _kernel(*arguments, threads=lanes)
    return TensorOutcomeResult(effective, die_errors, lane_errors, batch.dice_counts)
