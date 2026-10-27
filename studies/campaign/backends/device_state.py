"""Lossless resident campaign snapshots and device-only independent forks.

PRIVILEGED: these snapshots contain history and execution RNG, including test
faces. They must never be passed to neural feature builders or policies. This
is a state substrate, not a registered full GPU campaign transition backend.
Native transfer traverses C++ fields directly; JSON encoding/parsing is absent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import torch

SCHEMA = "campaign-device-state-v2"
SECTION_NAMES = (
    "state", "random", "state.nations", "state.territories", "state.units",
    "state.facilities", "state.rails", "state.construction", "state.repairs",
    "state.clock", "state.politics", "state.turn_start", "state.completed_turns",
    "state.decisions", "state.battles", "state.battle_order", "state.chance",
    "state.flags", "state.history", "state.action_interface", "state.terminal",
    "random.actual", "random.search", "random.training", "random.active",
    "random.test_tape", "random.tape_position",
)


def _device(device):
    target = torch.device(device)
    if target.type not in {"cpu", "mps"}:
        raise ValueError("Device state currently supports explicit CPU/MPS execution")
    if target.type == "mps":
        import os
        if target.index not in (None, 0) or not torch.backends.mps.is_available():
            raise ValueError("Requested MPS device is unavailable; no CPU fallback")
        if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "0") not in {"", "0"}:
            raise ValueError("MPS CPU fallback is forbidden for device state")
        from .metal_validation import require_lossless_mps_indexing
        require_lossless_mps_indexing()
    return target


class DeviceStateContext:
    """One immutable definition/catalog/string prefix shared by all forks."""
    def __init__(self, native, device="cpu", *, editor_implementation="reference",container_implementation="reference"):
        target = _device(device)
        if type(editor_implementation) is not str or editor_implementation not in {"reference","parallel"}:
            raise ValueError("State editor implementation must be reference or parallel")
        if editor_implementation=="parallel" and target.type!="mps":
            raise ValueError("Parallel resident editing requires explicit Apple GPU execution")
        self._editor_implementation=editor_implementation
        if type(container_implementation) is not str or container_implementation not in {"reference","parallel"}:
            raise ValueError("Container implementation must be reference or parallel")
        if container_implementation=="parallel" and target.type!="mps":
            raise ValueError("Parallel container building requires explicit Apple GPU execution")
        self._container_implementation=container_implementation
        if native.schema != SCHEMA:
            raise ValueError("Unsupported native device state schema")
        self.native = native
        self.definition_fingerprint = native.definition_fingerprint
        self.rules_id = native.rules_id
        self.wire_context_fingerprint = native.wire_context_fingerprint
        self.random_stream_ids = tuple(int(value) for value in native.prefix_lookup_ids(("actual", "search", "training")))
        self.records = torch.tensor(native.record_array(), dtype=torch.int64, device=target)
        self.string_bytes = torch.tensor(native.string_bytes(), dtype=torch.uint8, device=target)
        self.string_offsets = torch.tensor(native.string_offsets(), dtype=torch.int64, device=target)
        self.string_count = native.string_count
        self.device = self.records.device
        if self.device.type != target.type:
            raise RuntimeError("Static device state did not reach the explicit target")

    @property
    def identity(self):
        return SCHEMA, self.definition_fingerprint, self.rules_id, self.wire_context_fingerprint

    @property
    def editor_implementation(self):
        """Execution strategy only; neither a rule nor a neural-input field."""
        return self._editor_implementation

    @property
    def container_implementation(self):
        """Source validation/copy policy; the complete rules State is unchanged."""
        return self._container_implementation

    def prefix_lookup_ids(self, names):
        """One-time host metadata lookup of exact fixed protocol spellings."""
        return self.native.prefix_lookup_ids(tuple(names))


@dataclass(frozen=True)
class DeviceStateBatch:
    context: DeviceStateContext
    records: Any       # int64 [lane, allocated_record_capacity, 5]; end is local.
    lengths: Any       # int64 [lane], actual complete record counts.
    sections: Any      # int64 [lane, len(SECTION_NAMES)], local record indices.
    string_bytes: Any  # uint8 dynamic suffix shared immutably by forks.
    string_offsets: Any
    errors: Any        # int64 [lane]; invalid device selection is explicit.
    suffix_usage: Any = None  # int64 [2]: actual strings/bytes, independent of capacity.

    @classmethod
    def from_native(cls, native, *, device=None, context=None):
        if context is None:
            context = DeviceStateContext(native.context, "cpu" if device is None else device)
        elif device is not None and _device(device).type != context.device.type:
            raise ValueError("Explicit device does not match the shared state context")
        if (native.context.definition_fingerprint, native.context.rules_id, native.context.wire_context_fingerprint) != context.identity[1:]:
            raise ValueError("Device state definition/rules mismatch")
        if tuple(native.section_names) != SECTION_NAMES:
            raise ValueError("Unknown or missing device state fields")
        target = context.device
        flat = torch.tensor(native.record_array(), dtype=torch.int64, device=target)
        offsets = torch.tensor(native.lane_offsets(), dtype=torch.int64, device=target)
        lengths = offsets[1:] - offsets[:-1]
        capacity, lanes = native.max_lane_records, native.lane_count
        if lanes and capacity:
            positions = torch.arange(capacity, dtype=torch.int64, device=target).view(1, -1)
            indices = offsets[:-1].view(-1, 1) + positions
            safe = indices.clamp(0, max(flat.shape[0] - 1, 0))
            records = flat.index_select(0, safe.flatten()).view(lanes, capacity, 5)
            records = torch.where((positions < lengths.view(-1, 1)).unsqueeze(2), records, 0)
        else:
            records = torch.zeros((lanes, capacity, 5), dtype=torch.int64, device=target)
        result = cls(context, records, lengths,
            torch.tensor(native.section_array(), dtype=torch.int64, device=target),
            torch.tensor(native.string_bytes(), dtype=torch.uint8, device=target),
            torch.tensor(native.string_offsets(), dtype=torch.int64, device=target),
            torch.zeros(lanes, dtype=torch.int64, device=target),
            torch.tensor([native.string_offsets().shape[0]-1, native.string_bytes().shape[0]], dtype=torch.int64, device=target))
        result._metadata()
        return result

    @classmethod
    def capture(cls, envs: Sequence, *, device=None, context=None):
        import gwrl_cpp
        envs = tuple(envs)
        if context is None:
            if not envs:
                raise ValueError("An empty capture needs an explicit shared context")
            context = DeviceStateContext(gwrl_cpp.device_state_context(envs[0]), "cpu" if device is None else device)
        native = gwrl_cpp.capture_device_states(context.native, envs)
        return cls.from_native(native, device=device, context=context)

    @property
    def device(self):
        return self.context.device

    @property
    def lane_count(self):
        return self.records.shape[0]

    def _metadata(self):
        if not isinstance(self.suffix_usage, torch.Tensor):
            raise ValueError("Missing v2 resident suffix_usage counters; recapture the complete state, do not retag old buffers")
        lanes = self.records.shape[0]
        values = (self.records, self.lengths, self.sections, self.string_offsets, self.errors, self.suffix_usage)
        if (any(not isinstance(value, torch.Tensor) or value.device != self.device or value.dtype != torch.int64 for value in values) or
                self.string_bytes.device != self.device or self.string_bytes.dtype != torch.uint8 or
                self.records.ndim != 3 or self.records.shape[2] != 5 or
                self.lengths.shape != (lanes,) or self.sections.shape != (lanes, len(SECTION_NAMES)) or
                self.errors.shape != (lanes,) or self.string_bytes.ndim != 1 or self.string_offsets.ndim != 1 or
                self.string_offsets.numel() < 1 or self.suffix_usage.shape != (2,) or not self.suffix_usage.is_contiguous()):
            raise ValueError("Device state metadata/shape/device mismatch")

    def section(self, name):
        """Return resident local node indices without reading device values."""
        return self.sections[:, SECTION_NAMES.index(name)]

    def fork(self, lanes):
        """Independent device gather; repeated roots are allowed for simulations.

        Host selections are checked immediately. Device selections stay resident:
        invalid lanes get explicit error masks and zero invalid state, never a
        silently clamped alternative board. Consumers must propagate those masks.
        """
        self._metadata()
        if not isinstance(lanes, torch.Tensor):
            lanes = tuple(lanes)
            if any(type(lane) is not int or not 0 <= lane < self.lane_count for lane in lanes):
                raise ValueError("Device state lane outside batch")
            lanes = torch.tensor(lanes, dtype=torch.int64, device=self.device)
        if lanes.dtype != torch.int64 or lanes.device != self.device or lanes.ndim != 1:
            raise ValueError("Device fork indices must be a resident one-dimensional int64 tensor")
        if self.lane_count == 0:
            if lanes.shape[0]:
                raise ValueError("Cannot fork a nonempty selection from an empty device batch")
            return self.snapshot()
        valid = (lanes >= 0) & (lanes < self.lane_count)
        safe = lanes.clamp(0, self.lane_count - 1)
        records = self.records.index_select(0, safe)
        lengths, sections = self.lengths.index_select(0, safe), self.sections.index_select(0, safe)
        errors = self.errors.index_select(0, safe) | (~valid).to(torch.int64)
        return type(self)(self.context, torch.where(valid.view(-1, 1, 1), records, 0),
            torch.where(valid, lengths, 0), torch.where(valid.view(-1, 1), sections, 0),
            self.string_bytes, self.string_offsets, errors, self.suffix_usage)

    def snapshot(self):
        self._metadata()
        return type(self)(self.context, self.records.clone(), self.lengths.clone(), self.sections.clone(),
                         self.string_bytes, self.string_offsets, self.errors.clone(), self.suffix_usage)

    def to_native(self):
        """Explicit privileged host boundary; validate and decode every field."""
        import gwrl_cpp
        import numpy as np
        self._metadata()
        errors = self.errors.detach().cpu().tolist()
        if any(errors):
            raise ValueError("Invalid device state lanes: " + str(errors))
        lengths = self.lengths.detach().cpu().tolist()
        data = self.records.detach().cpu().numpy()
        if any(not 0 < length <= data.shape[1] for length in lengths):
            raise ValueError("Invalid device record lengths")
        pieces = [data[lane, :length].copy() for lane, length in enumerate(lengths)]
        flat = np.concatenate(pieces, axis=0) if pieces else np.empty((0, 5), dtype=np.int64)
        offsets = np.asarray([0, *np.cumsum(lengths, dtype=np.int64)], dtype=np.int64)
        count, used_bytes = self.suffix_usage.detach().cpu().tolist()
        if not 0 <= count < self.string_offsets.numel() or not 0 <= used_bytes <= self.string_bytes.numel():
            raise ValueError("Device string usage exceeds allocated buffers; no truncation")
        return gwrl_cpp.device_state_batch_from_packed(self.context.native, flat, offsets,
            self.string_bytes.detach().cpu().numpy()[:used_bytes], self.string_offsets.detach().cpu().numpy()[:count+1],
            self.context.wire_context_fingerprint)

    def restore_envs(self):
        """Fresh native oracle environments, for explicit inspection/conformance."""
        import gwrl_cpp
        return gwrl_cpp.restore_device_states(self.to_native())
