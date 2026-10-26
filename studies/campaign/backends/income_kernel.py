"""Exact integer income evaluation on direct native state buffers.

This component evaluates income only: it does not collect cash, advance phases,
change a board or consume random values. Immutable scenario tensors transfer once;
two dynamic buffers transfer in bulk. Host dictionaries and errors are an explicit
inspection boundary. The device result may remain resident.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch

OK, NATION_ABSENT, CAPITAL_TERRITORY_ABSENT, INVALID_IPP, INT_OVERFLOW, TERRITORY_ABSENT = range(6)


@dataclass(frozen=True)
class IncomeResult:
    # income[B,N,6]: error, component-mask, collectable, territorial, bonus, total.
    income: Any
    effective: Any
    effective_error: Any


class IncomeTensorContext:
    """Shared static context plus a portable CPU/MPS/CUDA integer kernel.

    Inputs come from capture_campaign_income's native int buffers. There is no
    entity cap or float conversion. int64 arithmetic detects undefined native
    int overflow instead of inventing a wrapping rule.
    """
    def __init__(self, native_context, device="cpu"):
        target = torch.device(device)
        if target.type not in {"cpu", "mps", "cuda"}:
            raise ValueError("Explicit CPU/MPS/CUDA income device required")
        if target.type == "mps":
            import os
            if target.index not in (None, 0):
                raise ValueError("MPS supports device zero only")
            if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "0") not in {"", "0"}:
                raise ValueError("MPS CPU fallback is forbidden")
            if not torch.backends.mps.is_available():
                raise ValueError("MPS unavailable")
        if target.type == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA unavailable")
        self.definition_fingerprint = native_context.definition_fingerprint
        self.territory_ids = tuple(native_context.territory_ids)
        self.nation_ids = tuple(native_context.nation_ids)
        self._territory_index = {name: i for i, name in enumerate(self.territory_ids)}
        self._nation_index = {name: i for i, name in enumerate(self.nation_ids)}
        self.int_min, self.int_max = native_context.int_minimum, native_context.int_maximum
        self.static_t = torch.tensor(native_context.territory_array(), dtype=torch.int64, device=target)
        self.static_n = torch.tensor(native_context.nation_array(), dtype=torch.int64, device=target)
        if (self.static_t.shape != (len(self.territory_ids), 3) or
                self.static_n.shape != (len(self.nation_ids), 2)):
            raise ValueError("Income static buffers must preserve the complete indexed shapes")
        if self.static_t.device.type != target.type or self.static_n.device != self.static_t.device:
            raise RuntimeError("Income buffers did not reach the requested device")
        self.device = self.static_t.device  # Canonical actual index, e.g. mps:0.
        self._base = self.static_t[:, 0].unsqueeze(0)
        self._valid_ipp = self.static_t[:, 1].bool().unsqueeze(0)
        self._bonus_zones = self.static_t[:, 2].bool().view(1, 1, -1)
        self._account_identity = self.static_n[:, 0].bool().unsqueeze(0)
        self._japan_identity = self.static_n[:, 1].bool().unsqueeze(0)
        self._nation_ids = torch.arange(len(self.nation_ids), device=self.device, dtype=torch.int64).view(1, -1)

    def capture(self, native_batch):
        if native_batch.context.definition_fingerprint != self.definition_fingerprint:
            raise ValueError("Income definition mismatch")
        # Two contiguous native buffers: no JSON, tolist, or Python field loop.
        territories = torch.tensor(native_batch.territory_array(), dtype=torch.int64, device=self.device)
        nations = torch.tensor(native_batch.nation_array(), dtype=torch.int64, device=self.device)
        return self.compute(territories, nations)

    def compute(self, territories, nations):
        """Evaluate complete native-shaped int64 inputs, returning device buffers."""
        T, N = len(self.territory_ids), len(self.nation_ids)
        if (territories.dtype != torch.int64 or nations.dtype != torch.int64 or
                territories.device != self.device or nations.device != self.device or
                territories.ndim != 3 or nations.ndim != 3 or
                territories.shape[1:] != (T, 4) or nations.shape[1:] != (N, 6) or
                territories.shape[0] != nations.shape[0]):
            raise ValueError("Income buffers must preserve complete native shapes, device and int64 dtype")
        present, owner = territories[:, :, 0].bool(), territories[:, :, 1]
        # C++ signed integer division truncates toward zero, including negatives.
        lost = torch.maximum(territories[:, :, 2], torch.div(territories[:, :, 3], 20, rounding_mode="trunc"))
        raw = self._base - lost
        effective = raw.clamp_min(0)
        effective_error = torch.where(~present, TERRITORY_ABSENT,
            torch.where(~self._valid_ipp, INVALID_IPP,
                torch.where((raw < self.int_min) | (raw > self.int_max), INT_OVERFLOW, OK)))
        nation_present, major = nations[:, :, 0].bool(), nations[:, :, 2].bool()
        eligible = nation_present & (self._account_identity | major) & nations[:, :, 1].bool() & ~nations[:, :, 3].bool()
        owned = present.unsqueeze(1) & (owner.unsqueeze(1) == self._nation_ids.unsqueeze(2))
        territorial = torch.where(owned, effective.unsqueeze(1), 0).sum(2)
        bonus = torch.where(self._japan_identity, (owned & self._bonus_zones).sum(2), 0)
        bad_ipp = (owned & (effective_error == INVALID_IPP).unsqueeze(1)).any(2)
        bad_range = (owned & (effective_error == INT_OVERFLOW).unsqueeze(1)).any(2)
        capital = nations[:, :, 5]
        if T:
            safe = capital.clamp(0, T - 1)
            capital_exists = (capital >= 0) & (capital < T) & present.gather(1, safe)
            capital_held = owner.gather(1, safe) == self._nation_ids
        else:
            capital_exists, capital_held = torch.zeros_like(eligible), torch.zeros_like(eligible)
        capital_map_present = nations[:, :, 4].bool()
        capital_error = eligible & major & capital_map_present & ~capital_exists
        collectable = eligible & (~major | (capital_map_present & capital_exists & capital_held))
        # nations.at -> early-out -> major capital.at -> owned territory reads.
        # An absent capital MAP is not an exception and retains components.
        error = torch.where(~nation_present, NATION_ABSENT,
            torch.where(capital_error, CAPITAL_TERRITORY_ABSENT,
                torch.where(eligible & bad_ipp, INVALID_IPP,
                    torch.where(eligible & (bad_range | (territorial > self.int_max) |
                                           ((territorial + bonus) > self.int_max)), INT_OVERFLOW, OK))))
        mask = eligible.to(torch.int64) * (1 + 2 * self.static_n[:, 1].unsqueeze(0))
        components_t, components_b = torch.where(eligible, territorial, 0), torch.where(eligible, bonus, 0)
        total = torch.where(collectable, territorial + bonus, 0)
        income = torch.stack((error, mask, collectable.to(torch.int64), components_t, components_b, total), 2)
        return IncomeResult(income, effective, effective_error)

    @staticmethod
    def _raise(error, identity):
        if error in (NATION_ABSENT, CAPITAL_TERRITORY_ABSENT, TERRITORY_ABSENT):
            raise IndexError(f"Income lookup absent: {identity} (code {error})")
        if error == INVALID_IPP:
            raise RuntimeError(f"Income IPP field is invalid: {identity}")
        if error == INT_OVERFLOW:
            raise OverflowError("Outside defined C++ int arithmetic; no wrap behavior is invented")

    @staticmethod
    def _lane(lane, count):
        if type(lane) is not int or not 0 <= lane < count:
            raise IndexError(f"Income lane absent: {lane}")
        return lane

    def inspect_income(self, result, queries=None):
        rows = result.income.detach().cpu().tolist()  # Explicit output boundary.
        if queries is None:
            queries = [(b, name) for b, row in enumerate(rows)
                       for name, value in zip(self.nation_ids, row) if value[0] != NATION_ABSENT]
        inspected = []
        for lane, name in queries:
            lane = self._lane(lane, len(rows))
            if name not in self._nation_index:
                raise IndexError(f"Unknown income nation: {name}")
            error, mask, collectable, territorial, bonus, total = rows[lane][self._nation_index[name]]
            self._raise(error, name)
            components = {}
            if mask & 1:
                components["territorial"] = territorial
            if mask & 2:
                components["china_control_bonus"] = bonus
            inspected.append({"lane": lane, "nation": name, "components": components,
                              "collectable": bool(collectable), "total": total})
        return inspected

    def inspect_effective(self, result, queries):
        values = result.effective.detach().cpu().tolist()
        errors = result.effective_error.detach().cpu().tolist()
        out = []
        for lane, name in queries:
            lane = self._lane(lane, len(values))
            if name not in self._territory_index:
                raise IndexError(f"Unknown income territory: {name}")
            territory = self._territory_index[name]
            self._raise(errors[lane][territory], name)
            out.append(values[lane][territory])
        return out
