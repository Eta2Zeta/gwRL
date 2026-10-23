"""Explicit declaration-opportunity scheduling around the shared campaign API.

The versioned offer order is an engine convention. Actual declarations and their
mandatory priority reactions remain governed by the C++ rules. Passing an offer
is an observable policy choice, not an automatic opponent action.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .multiplayer_mcts import PLAYERS, action_key

SCHEMA = "campaign-interrupt-scheduler-v1"
PHASES = {"production", "combat_movement", "combat", "non_combat_movement", "place_units"}


def _field(action: Any, name: str) -> Any:
    return action[name] if isinstance(action, dict) else getattr(action, name)


def _raw_features(action: Any) -> dict[str, Any]:
    if isinstance(action, dict):
        return action.copy()
    return {name: getattr(action, name) for name in ("id", "kind", "player", "nation", "decision", "parameters")}


@dataclass(frozen=True, slots=True)
class ScheduledAction:
    id: str
    kind: str
    player: str
    raw: Any = None

    def features(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "player": self.player,
                "action": _raw_features(self.raw) if self.raw is not None else None}


class CampaignAdapter:
    def __init__(self, raw: Any, *, interrupt_order: tuple[str, ...] = PLAYERS):
        if len(interrupt_order) != 3 or set(interrupt_order) != set(PLAYERS):
            raise ValueError("Interrupt order must contain each alliance exactly once")
        self.raw = raw
        self.interrupt_order = tuple(interrupt_order)
        self._anchor = raw.planning_key()
        self._passed: set[str] = set()

    def _sync(self) -> None:
        key = self.raw.planning_key()
        if key != self._anchor:
            self._anchor, self._passed = key, set()

    def _offered_player(self) -> str | None:
        self._sync()
        if self.raw.is_terminal() or self.raw.decision_kind() not in PHASES:
            return None
        owners = {_field(action, "player") for action in self.raw.legal_interrupts()}
        if not owners.issubset(PLAYERS):
            raise ValueError("Interrupt names an unknown decision owner")
        return next((player for player in self.interrupt_order if player in owners and player not in self._passed), None)

    def current_decision_player(self) -> str | None:
        return self._offered_player() or self.raw.current_decision_player()

    def decision_kind(self) -> str:
        return "declaration_offer" if self._offered_player() is not None else self.raw.decision_kind()

    def legal_actions(self) -> list[ScheduledAction]:
        offered = self._offered_player()
        if offered is not None:
            actions = [ScheduledAction(f"{SCHEMA}:interrupt:{action_key(action)}", "interrupt", offered, action)
                       for action in self.raw.legal_interrupts() if _field(action, "player") == offered]
            actions.append(ScheduledAction(f"{SCHEMA}:pass:{offered}", "pass_interrupt", offered))
            return actions
        owner = self.raw.current_decision_player()
        return [ScheduledAction(f"{SCHEMA}:play:{action_key(action)}", "play", str(owner), action)
                for action in self.raw.legal_actions()]

    def apply_action(self, action: ScheduledAction) -> None:
        # Use the current legal object, never a caller-supplied raw payload with
        # a copied ID. Validation occurs before changing wrapper or engine state.
        candidates = [candidate for candidate in self.legal_actions()
                      if candidate.id == action.id and candidate.kind == action.kind and candidate.player == action.player]
        if len(candidates) != 1:
            raise ValueError("Illegal scheduled campaign action")
        chosen = candidates[0]
        if chosen.kind == "pass_interrupt":
            self._passed.add(chosen.player)
        elif chosen.kind == "interrupt":
            self.raw.apply_interrupt(chosen.raw)
            self._sync()
        else:
            self.raw.apply_action(chosen.raw)
            self._sync()

    def resolve_chance(self) -> None:
        if self.decision_kind() != "chance":
            raise ValueError("No scheduled chance event is pending")
        self.raw.resolve_chance()
        self._sync()

    def is_terminal(self) -> bool:
        return bool(self.raw.is_terminal())

    def returns(self) -> Any:
        return self.raw.returns()

    def wealth(self) -> Any:
        return self.raw.wealth()

    def observation(self) -> dict[str, Any]:
        self._sync()
        observation = dict(self.raw.observation())
        observation.update({"current_decision_player": self.current_decision_player(),
                            "decision_kind": self.decision_kind(),
                            "legal_actions": [action.features() for action in self.legal_actions()],
                            "interrupt_scheduler": {"schema": SCHEMA, "order": list(self.interrupt_order),
                                                    "passed": sorted(self._passed)}})
        return observation

    def context(self) -> dict[str, Any]:
        context = dict(self.raw.context())
        context["interrupt_scheduler"] = {"schema": SCHEMA, "order": list(self.interrupt_order)}
        return context

    def clone(self) -> CampaignAdapter:
        self._sync()
        result = CampaignAdapter(self.raw.clone(), interrupt_order=self.interrupt_order)
        result._passed = self._passed.copy()
        return result

    def clone_for_search(self, seed: int) -> CampaignAdapter:
        self._sync()
        result = CampaignAdapter(self.raw.clone_for_search(seed), interrupt_order=self.interrupt_order)
        result._passed = self._passed.copy()
        return result

    def planning_key(self) -> str:
        self._sync()
        value = {"schema": SCHEMA, "raw_key": self._anchor, "order": self.interrupt_order, "passed": sorted(self._passed)}
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def serialize(self) -> str:
        self._sync()
        return json.dumps({"schema": SCHEMA, "raw": self.raw.serialize(), "order": self.interrupt_order,
                           "passed": sorted(self._passed), "anchor": self._anchor}, sort_keys=True, separators=(",", ":"))

    def restore(self, serialized: str) -> None:
        value = json.loads(serialized)
        if value.get("schema") != SCHEMA or set(value) != {"schema", "raw", "order", "passed", "anchor"}:
            raise ValueError("Invalid campaign scheduler checkpoint")
        raw = self.raw.clone()
        raw.restore(value["raw"])
        replacement = CampaignAdapter(raw, interrupt_order=tuple(value["order"]))
        passed = value["passed"]
        if len(set(passed)) != len(passed) or not set(passed).issubset(PLAYERS) or value["anchor"] != raw.planning_key():
            raise ValueError("Invalid checkpoint declaration-opportunity state")
        replacement._passed = set(passed)
        self.__dict__.update(replacement.__dict__)
