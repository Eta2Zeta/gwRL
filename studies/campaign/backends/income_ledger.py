"""Exact out-of-place income accounting on resident numerical state.

This is applyIncomeLedger, not an end-turn or end-phase implementation. Repairs,
placement, political/surrender hooks and clock progression remain separate. A
failed lane preserves its original entire ledger, as the native Engine's cloned
transaction does. No environment is modified and no RNG is consumed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch

from .income_kernel import IncomeTensorContext, OK

COLLECTION_OVERFLOW, CURRENT_NATION_ABSENT, INVALID_LEDGER_INPUT = 6, 7, 8
COMPONENT_IDS = ("territorial", "china_control_bonus")


@dataclass(frozen=True)
class IncomeLedgerResult:
    error: Any                    # [B], device error code; zero commits the lane.
    error_nations: Any            # [B], first failing nation in native map order.
    nations: Any                  # [B,N,6], unchanged presence/optional metadata.
    ledger: Any                   # [B,N,2], treasury value and incomeKnown.
    components: Any               # [B,N,K,2], component presence/value.
    clock: Any                    # [B,2], current index and incomeCollected only.
    component_ids: tuple[str, ...]
    definition_fingerprint: str


class IncomeLedgerTensorContext:
    def __init__(self, native_context, device="cpu"):
        self.income = IncomeTensorContext(native_context, device)
        self.device = self.income.device
        self.nation_ids = self.income.nation_ids
        self.definition_fingerprint = self.income.definition_fingerprint

    def capture(self, native_batch):
        if native_batch.context.definition_fingerprint != self.definition_fingerprint:
            raise ValueError("Income ledger definition mismatch")
        # Five whole native buffers, with shared immutable scenario data already
        # resident in self.income. No JSON or Python per-field/per-lane route.
        inputs = native_batch.income_inputs
        return self.compute(
            torch.tensor(inputs.territory_array(), dtype=torch.int64, device=self.device),
            torch.tensor(inputs.nation_array(), dtype=torch.int64, device=self.device),
            torch.tensor(native_batch.ledger_array(), dtype=torch.int64, device=self.device),
            torch.tensor(native_batch.component_array(), dtype=torch.int64, device=self.device),
            torch.tensor(native_batch.clock_array(), dtype=torch.int64, device=self.device),
            tuple(native_batch.component_ids))

    def compute(self, territories, nations, ledger, components, clock, component_ids=COMPONENT_IDS):
        """Apply accounting; all lane validation and updates stay on device.

        Inputs are complete native-shaped int64 buffers. The original component
        key union is retained without caps, including custom keys on error lanes.
        Reusing the returned ledger/components/clock makes collection idempotent.
        """
        if self.device.type == "mps":
            import os
            if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "0") not in {"", "0"}:
                raise ValueError("MPS CPU fallback is forbidden")
        ids = tuple(component_ids)
        if (ids[:2] != COMPONENT_IDS or any(not isinstance(name, str) for name in ids) or len(set(ids)) != len(ids)):
            raise ValueError("Complete distinct component identities must begin with territorial and china_control_bonus")
        if not isinstance(territories, torch.Tensor) or territories.ndim != 3:
            raise ValueError("Income ledger buffers must preserve complete native shapes, device and int64 dtype")
        B, N, T, K = territories.shape[0], len(self.nation_ids), len(self.income.territory_ids), len(ids)
        expected = ((B, T, 4), (B, N, 6), (B, N, 2), (B, N, K, 2), (B, 2))
        values = (territories, nations, ledger, components, clock)
        if any(not isinstance(value, torch.Tensor) or value.dtype != torch.int64 or value.device != self.device or
               tuple(value.shape) != shape for value, shape in zip(values, expected, strict=True)):
            raise ValueError("Income ledger buffers must preserve complete native shapes, device and int64 dtype")
        # Guard the native signed-int input domain before subtraction/sums. This
        # rejects arbitrary int64 extremes rather than allowing int64 wraparound
        # to masquerade as defined C++ int arithmetic.
        minimum, maximum = self.income.int_min, self.income.int_max
        bad = (((territories[:, :, 2:] < minimum) | (territories[:, :, 2:] > maximum)).any((1, 2)) |
               ((territories[:, :, 0] < 0) | (territories[:, :, 0] > 1) |
                (territories[:, :, 1] < -1) | (territories[:, :, 1] >= N)).any(1) |
               ((nations[:, :, :5] < 0) | (nations[:, :, :5] > 1)).any((1, 2)) |
               ((nations[:, :, 5] < -1) | (nations[:, :, 5] >= T)).any(1) |
               ((ledger[:, :, 0] < 0) | (ledger[:, :, 0] > maximum) |
                (ledger[:, :, 1] < 0) | (ledger[:, :, 1] > 1)).any(1) |
               ((components[:, :, :, 0] < 0) | (components[:, :, :, 0] > 1) |
                (components[:, :, :, 1] < minimum) | (components[:, :, :, 1] > maximum)).any((1, 2)) |
               (clock[:, 1] < 0) | (clock[:, 1] > 1))
        safe_territories = territories.clamp(minimum, maximum)
        result = self.income.compute(safe_territories, nations)
        present = nations[:, :, 0].bool()
        if N:
            indices = torch.arange(N, dtype=torch.int64, device=self.device).unsqueeze(0)
            first_error = torch.where(present & (result.income[:, :, 0] != OK), indices, N).amin(1)
            income_error = result.income[:, :, 0].gather(1, first_error.clamp_max(N - 1).unsqueeze(1)).squeeze(1)
            current = clock[:, 0]
            safe_current = current.clamp(0, N - 1).unsqueeze(1)
            current_present = ((current >= 0) & (current < N) & present.gather(1, safe_current).squeeze(1))
            total = result.income[:, :, 5].gather(1, safe_current).squeeze(1)
            cash = ledger[:, :, 0].gather(1, safe_current).squeeze(1)
            collectable = result.income[:, :, 2].gather(1, safe_current).squeeze(1).bool()
            treasury_present = nations[:, :, 1].gather(1, safe_current).squeeze(1).bool()
            pay = ~clock[:, 1].bool() & current_present & collectable & treasury_present
            error = torch.where(first_error < N, income_error,
                torch.where(~current_present, CURRENT_NATION_ABSENT,
                    torch.where(pay & (cash > maximum - total), COLLECTION_OVERFLOW, OK)))
            error_nations = torch.where(first_error < N, first_error, current)
            amount = torch.where((indices == current.unsqueeze(1)) & pay.unsqueeze(1), total.unsqueeze(1), 0)
        else:
            error = torch.full((B,), CURRENT_NATION_ABSENT, dtype=torch.int64, device=self.device)
            error_nations = clock[:, 0]
            amount = torch.zeros_like(ledger[:, :, 0])
        error = torch.where(bad, INVALID_LEDGER_INPUT, error)
        error_nations = torch.where(bad, -1, error_nations)
        success = error == OK
        next_ledger = torch.stack((ledger[:, :, 0] + amount, torch.where(present, 1, ledger[:, :, 1])), 2)
        next_ledger = torch.where(success[:, None, None], next_ledger, ledger)
        component_index = torch.arange(K, dtype=torch.int64, device=self.device).view(1, 1, K)
        mask = result.income[:, :, 1].unsqueeze(2)
        next_presence = (((component_index == 0) & ((mask & 1) != 0)) |
                         ((component_index == 1) & ((mask & 2) != 0))).to(torch.int64)
        next_value = torch.where(component_index == 0, result.income[:, :, 3].unsqueeze(2),
                                torch.where(component_index == 1, result.income[:, :, 4].unsqueeze(2), 0))
        next_components = torch.stack((next_presence, next_value), 3)
        # refreshIncome visits only present nations; absent slots retain their
        # original numerical payload rather than inventing a nation.
        next_components = torch.where((success[:, None] & present)[:, :, None, None], next_components, components)
        next_clock = torch.stack((clock[:, 0], torch.where(success, 1, clock[:, 1])), 1)
        return IncomeLedgerResult(error, error_nations, nations, next_ledger, next_components, next_clock,
                                  ids, self.definition_fingerprint)

    def inspect(self, result):
        """Explicit host boundary; no implicit writes to a native environment."""
        if result.definition_fingerprint != self.definition_fingerprint:
            raise ValueError("Income ledger result definition mismatch")
        errors = result.error.detach().cpu().tolist()
        failing = result.error_nations.detach().cpu().tolist()
        nations = result.nations.detach().cpu().tolist()
        ledger = result.ledger.detach().cpu().tolist()
        components = result.components.detach().cpu().tolist()
        clock = result.clock.detach().cpu().tolist()
        output = []
        for lane, error in enumerate(errors):
            if error == COLLECTION_OVERFLOW:
                raise RuntimeError("IPP overflow")
            if error == CURRENT_NATION_ABSENT:
                raise IndexError("Current income nation is absent")
            if error == INVALID_LEDGER_INPUT:
                raise ValueError("Income ledger input is outside native integer/flag domains")
            if error:
                identity = self.nation_ids[failing[lane]] if 0 <= failing[lane] < len(self.nation_ids) else "unknown"
                self.income._raise(error, identity)
            output.append({"current_nation": self.nation_ids[clock[lane][0]], "income_collected": bool(clock[lane][1]),
                "nations": {name: {"treasury": ledger[lane][n][0] if nations[lane][n][1] else None,
                                    "income_known": bool(ledger[lane][n][1]),
                                    "income_components": {key: value for key, (present, value) in
                                        zip(result.component_ids, components[lane][n], strict=True) if present}}
                            for n, name in enumerate(self.nation_ids) if nations[lane][n][0]}})
        return output
