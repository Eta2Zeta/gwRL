"""Explicit declaration-opportunity scheduling around the shared campaign API.

The versioned offer order is an engine convention. Actual declarations and their
mandatory priority reactions remain governed by the C++ rules. Passing an offer
is an observable policy choice, not an automatic opponent action.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from operator import is_
from typing import Any

try:
    from gwrl_cpp import CampaignAction as _NativeAction
except ImportError:  # JSON test environments need no extension.
    _NativeAction = None

from .immutable_json import FrozenDict, freeze_json
from .multiplayer_mcts import PLAYERS, action_key

SCHEMA = "campaign-interrupt-scheduler-v1"
PHASES = {"production", "combat_movement", "combat", "non_combat_movement", "place_units"}


def _field(action: Any, name: str) -> Any:
    return action[name] if isinstance(action, dict) else getattr(action, name)


def _raw_features(action: Any) -> dict[str, Any]:
    if isinstance(action, dict):
        return action.copy()
    return {name: getattr(action, name) for name in ("id", "kind", "player", "nation", "decision", "parameters")}


@dataclass(frozen=True, slots=True, init=False)
class ScheduledAction:
    id: str
    kind: str
    player: str
    _source: Any = field(repr=False, compare=False)
    _raw: Any = field(repr=False, compare=False)
    _features: Any = field(repr=False, compare=False)

    def __init__(self, id: str, kind: str, player: str, raw: Any = None):
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "player", player)
        native = _NativeAction is not None and type(raw) is _NativeAction
        object.__setattr__(self, "_source", raw if native else None)
        object.__setattr__(self, "_raw", None if native else
                           (freeze_json(_raw_features(raw)) if raw is not None else None))
        object.__setattr__(self, "_features", None)

    @property
    def raw(self) -> Any:
        # Public inspection remains immutable. Self-play does not create this
        # Python action tree unless a trace or inspection caller needs it.
        if self._source is not None and self._raw is None:
            object.__setattr__(self, "_raw", freeze_json(_raw_features(self._source)))
        return self._raw

    def frozen_features(self) -> FrozenDict:
        """The option as immutable JSON, for observations, traces and replays."""
        if self._features is None:
            object.__setattr__(self, "_features", freeze_json({
                "id": self.id, "kind": self.kind, "player": self.player, "action": self.raw,
            }))
        return self._features

    def features(self) -> dict[str, Any]:
        return json.loads(self.frozen_features().canonical_json)

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        # Public action pickles retain their portable immutable feature payload;
        # learning checkpoints store zone inputs, not native action handles.
        return type(self), (self.id, self.kind, self.player, self.raw)


@dataclass(slots=True)
class _DecisionCache:
    key: tuple[str, tuple[str, ...], tuple[str, ...]]
    offered: str | None
    owner: str | None
    kind: str
    actions: tuple[ScheduledAction, ...] | None = None
    raw_actions: tuple[Any, ...] | None = None
    observation: FrozenDict | None = None
    zone: Any = None


def _canonical_raw(action: Any) -> Any:
    # Native actions have value fields and stay private. JSON fake environments
    # also retain a detached canonical payload instead of a caller-owned dict.
    return freeze_json(action) if isinstance(action, dict) else action


class CampaignAdapter:
    def __init__(self, raw: Any, *, interrupt_order: tuple[str, ...] = PLAYERS):
        if len(interrupt_order) != 3 or set(interrupt_order) != set(PLAYERS):
            raise ValueError("Interrupt order must contain each alliance exactly once")
        self.raw = raw
        self.interrupt_order = tuple(interrupt_order)
        self._anchor = raw.planning_key()
        self._passed: set[str] = set()
        self._frozen_context: FrozenDict | None = None
        self._context_order = self.interrupt_order
        self._raw_interrupts: tuple[Any, ...] | None = None
        self._raw_actions: tuple[Any, ...] | None = None
        self._raw_observation: FrozenDict | None = None
        self._decision: _DecisionCache | None = None

    def _invalidate_raw(self) -> None:
        self._raw_interrupts = self._raw_actions = None
        self._raw_observation = None
        self._decision = None

    def _sync(self) -> None:
        key = self.raw.planning_key()
        if key != self._anchor:
            self._anchor, self._passed = key, set()
            self._invalidate_raw()

    def _decision_cache(self) -> _DecisionCache:
        self._sync()
        key = (self._anchor, self.interrupt_order, tuple(sorted(self._passed)))
        if self._decision is not None and self._decision.key == key:
            return self._decision
        kind = self.raw.decision_kind()
        offered = None
        if not self.raw.is_terminal() and kind in PHASES:
            if self._raw_interrupts is None:
                self._raw_interrupts = tuple(_canonical_raw(action) for action in self.raw.legal_interrupts())
            owners = {_field(action, "player") for action in self._raw_interrupts}
            if not owners.issubset(PLAYERS):
                raise ValueError("Interrupt names an unknown decision owner")
            offered = next((player for player in self.interrupt_order
                            if player in owners and player not in self._passed), None)
        self._decision = _DecisionCache(key, offered, offered or self.raw.current_decision_player(),
                                        "declaration_offer" if offered is not None else kind)
        return self._decision

    def _offered_player(self) -> str | None:
        return self._decision_cache().offered

    def current_decision_player(self) -> str | None:
        return self._decision_cache().owner

    def decision_kind(self) -> str:
        return self._decision_cache().kind

    def _legal_actions(self, decision: _DecisionCache) -> tuple[ScheduledAction, ...]:
        if decision.actions is None:
            if decision.offered is not None:
                raw_actions = tuple(action for action in self._raw_interrupts or ()
                                    if _field(action, "player") == decision.offered)
                actions = [ScheduledAction(f"{SCHEMA}:interrupt:{action_key(action)}", "interrupt",
                                           decision.offered, action) for action in raw_actions]
                actions.append(ScheduledAction(f"{SCHEMA}:pass:{decision.offered}", "pass_interrupt", decision.offered))
                decision.raw_actions = (*raw_actions, None)
            else:
                if self._raw_actions is None:
                    self._raw_actions = tuple(_canonical_raw(action) for action in self.raw.legal_actions())
                decision.raw_actions = self._raw_actions
                actions = [ScheduledAction(f"{SCHEMA}:play:{action_key(action)}", "play", str(decision.owner), action)
                           for action in self._raw_actions]
            decision.actions = tuple(actions)
        return decision.actions

    def legal_actions(self) -> list[ScheduledAction]:
        return list(self._legal_actions(self._decision_cache()))

    def _apply_native_play(self, action: ScheduledAction, decision: _DecisionCache) -> bool:
        """Let the engine check a move it issued, without listing the menu here.

        Engine::step compares the whole payload with its menu entry for this id,
        and Python cannot build or change a native action. A refusal leaves the
        engine untouched, so apply_action's full check then decides. Any other
        failure may have damaged the engine and must not be retried.
        """
        source = getattr(action, "_source", None)
        if source is None or decision.offered is not None or action.kind != "play" or action.player != decision.owner:
            return False
        from gwrl_cpp import CampaignAction
        if type(source) is not CampaignAction or action.id != f"{SCHEMA}:play:{source.id}":
            return False
        try:
            self.raw.apply_action(source)
        except RuntimeError as error:
            if str(error) != "Illegal campaign action":
                raise
            return False
        return True

    def apply_action(self, action: ScheduledAction) -> None:
        decision = self._decision_cache()
        if self._apply_native_play(action, decision):
            self._invalidate_raw()
            self._sync()
            return
        # Validate against the unchanged decision's canonical legal objects. A
        # forged or mutated public raw payload is never sent to the engine.
        actions = self._legal_actions(decision)
        matches = [index for index, candidate in enumerate(actions)
                   if candidate.id == action.id and candidate.kind == action.kind and candidate.player == action.player]
        if len(matches) != 1:
            raise ValueError("Illegal scheduled campaign action")
        index = matches[0]
        chosen = actions[index]
        if chosen.kind == "pass_interrupt":
            self._passed.add(chosen.player)
            self._decision = None
        else:
            assert decision.raw_actions is not None
            if chosen.kind == "interrupt":
                self.raw.apply_interrupt(decision.raw_actions[index])
            else:
                self.raw.apply_action(decision.raw_actions[index])
            self._invalidate_raw()
            self._sync()

    def resolve_chance(self) -> None:
        if self.decision_kind() != "chance":
            raise ValueError("No scheduled chance event is pending")
        self.raw.resolve_chance()
        self._invalidate_raw()
        self._sync()

    def chance_request(self) -> dict[str, Any] | None:
        """Inspect only the pending distribution, never future execution dice."""
        if self.decision_kind() != "chance":
            return None
        return self.raw.chance_request()

    def apply_chance_outcome(self, expected_key: str, faces: Any) -> None:
        """Apply recorded faces for conformance; leave execution RNG unchanged."""
        decision = self._decision_cache()
        raw_key, order, passed = decision.key
        scheduled_key = hashlib.sha256(json.dumps({"schema": SCHEMA, "raw_key": raw_key,
            "order": order, "passed": passed}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if scheduled_key != expected_key or decision.kind != "chance":
            raise ValueError("Stale or absent scheduled chance request")
        if (not isinstance(faces, (tuple, list)) or any(
                not isinstance(die, (tuple, list)) or any(type(face) is not int for face in die)
                for die in faces)):
            raise ValueError("Chance outcomes require complete integer face sequences")
        # Keep the raw identity from the decision we authorized. Re-reading a
        # newer key here could apply an old outcome to a concurrently changed
        # request; the native check and application are one locked operation.
        self.raw.apply_chance_outcome(raw_key, faces)
        self._invalidate_raw()
        self._sync()

    def is_terminal(self) -> bool:
        return bool(self.raw.is_terminal())

    def returns(self) -> Any:
        return self.raw.returns()

    def wealth(self) -> Any:
        return self.raw.wealth()

    def frozen_observation(self) -> FrozenDict:
        """Complete immutable observation reused for one scheduled decision."""
        decision = self._decision_cache()
        if decision.observation is None:
            if self._raw_observation is None:
                self._raw_observation = freeze_json(dict(self.raw.observation()))
            observation = dict(self._raw_observation)
            observation.update({"current_decision_player": decision.owner,
                                "decision_kind": decision.kind,
                                "legal_actions": [action.frozen_features() for action in self._legal_actions(decision)],
                                "interrupt_scheduler": {"schema": SCHEMA, "order": list(self.interrupt_order),
                                                        "passed": sorted(self._passed)}})
            decision.observation = freeze_json(observation)
        return decision.observation

    def zone_input(self, actions: tuple[ScheduledAction, ...] | None = None) -> Any:
        """This decision in the fixed zone encoding: the network's input.

        The decision is encoded once; `actions` picks options from it by their
        content-derived IDs, in any order and any subset, and None means every
        option. An option not on this decision's menu is refused.
        """
        if not hasattr(self.raw, "zone_input"):
            return None
        decision = self._decision_cache()
        menu = () if self.raw.is_terminal() else self._legal_actions(decision)
        if decision.zone is None:
            # The engine encodes its own action objects and refuses anything
            # else; a pass has none. JSON test environments get their raw form.
            options = [(action.kind, action.player, action._source if action._source is not None else action.raw)
                       for action in menu]
            decision.zone = self.raw.zone_input(decision.owner, decision.kind, decision.offered,
                                                sorted(self._passed), list(self.interrupt_order), options)
        if actions is None or (len(actions) == len(menu) and all(map(is_, actions, menu))):
            return decision.zone
        lookup = {action.id: index for index, action in enumerate(menu)}
        try:
            indices = [lookup[action.id] for action in actions]
        except KeyError as error:
            raise ValueError("Zone input requested for an option not on this decision's menu") from error
        return decision.zone.select(indices)

    def observation(self) -> dict[str, Any]:
        # Public callers may edit a detached mutable observation; inference
        # retains the immutable source directly and avoids repeated conversion.
        return json.loads(self.frozen_observation().canonical_json)

    def context(self) -> dict[str, Any]:
        # Public callers retain the detached, mutable JSON contract. Replays and
        # inspection use the immutable snapshot instead of retranslating the
        # registry each time.
        return json.loads(self.context_json())

    def frozen_context(self) -> FrozenDict:
        """Return the immutable definition shared by this environment's clones.

        Campaign context contains the scenario/rules definition, never changing
        game state or execution RNG. Restore replaces this cache transactionally.
        """
        if self._context_order != self.interrupt_order:
            self._frozen_context = None
            self._context_order = self.interrupt_order
        if self._frozen_context is None:
            context = dict(self.raw.context())
            context["interrupt_scheduler"] = {"schema": SCHEMA, "order": list(self.interrupt_order)}
            snapshot = freeze_json(context)
            # Validate the entire plain JSON definition before publishing it.
            snapshot.canonical_json
            self._frozen_context = snapshot
        return self._frozen_context

    def context_json(self) -> str:
        return self.frozen_context().canonical_json

    def clone(self) -> CampaignAdapter:
        self._sync()
        result = CampaignAdapter(self.raw.clone(), interrupt_order=self.interrupt_order)
        result._passed = self._passed.copy()
        result._frozen_context = self._frozen_context
        result._context_order = self._context_order
        # Copy lazy cache containers while sharing their immutable source data.
        # Neither real-play nor search RNG is stored in these snapshots.
        if result._anchor == self._anchor:
            result._raw_interrupts = self._raw_interrupts
            result._raw_actions = self._raw_actions
            result._raw_observation = self._raw_observation
            result._decision = replace(self._decision) if self._decision is not None else None
        return result

    def clone_for_search(self, seed: int) -> CampaignAdapter:
        self._sync()
        result = CampaignAdapter(self.raw.clone_for_search(seed), interrupt_order=self.interrupt_order)
        result._passed = self._passed.copy()
        result._frozen_context = self._frozen_context
        result._context_order = self._context_order
        # Copy lazy cache containers while sharing their immutable source data.
        # Neither real-play nor search RNG is stored in these snapshots.
        if result._anchor == self._anchor:
            result._raw_interrupts = self._raw_interrupts
            result._raw_actions = self._raw_actions
            result._raw_observation = self._raw_observation
            result._decision = replace(self._decision) if self._decision is not None else None
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
