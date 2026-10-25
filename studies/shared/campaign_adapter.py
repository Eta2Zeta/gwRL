"""Explicit declaration-opportunity scheduling around the shared campaign API.

The versioned offer order is an engine convention. Actual declarations and their
mandatory priority reactions remain governed by the C++ rules. Passing an offer
is an observable policy choice, not an automatic opponent action.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Any

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
    _numeric_snapshot: Any = field(repr=False, compare=False)

    def __init__(self, id: str, kind: str, player: str, raw: Any = None):
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "player", player)
        native = getattr(raw, "scheduled_snapshot", None)
        object.__setattr__(self, "_source", raw if native is not None else None)
        object.__setattr__(self, "_raw", None if native is not None else
                           (freeze_json(_raw_features(raw)) if raw is not None else None))
        object.__setattr__(self, "_features", None)
        object.__setattr__(self, "_numeric_snapshot", native(id, kind, player) if native is not None else None)

    @property
    def raw(self) -> Any:
        # Public inspection remains immutable. Native self-play does not create
        # this Python action tree unless a trace/debug caller actually needs it.
        if self._source is not None and self._raw is None:
            object.__setattr__(self, "_raw", freeze_json(_raw_features(self._source)))
        return self._raw

    def neural_features(self) -> FrozenDict:
        if self._features is None:
            object.__setattr__(self, "_features", freeze_json({
                "id": self.id, "kind": self.kind, "player": self.player, "action": self.raw,
            }))
        return self._features

    def features(self) -> dict[str, Any]:
        return json.loads(self.neural_features().canonical_json)

    def numeric_snapshot(self) -> Any:
        if self._numeric_snapshot is None and self.kind == "pass_interrupt":
            from gwrl_cpp import campaign_pass_snapshot
            object.__setattr__(self, "_numeric_snapshot", campaign_pass_snapshot(self.id, self.kind, self.player))
        return self._numeric_snapshot

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        # Public action pickles retain their portable immutable feature payload;
        # learning checkpoints store numerical inputs, not native action handles.
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
    numeric: dict[int, Any] = field(default_factory=dict)


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
        self._neural_context: FrozenDict | None = None
        self._context_order = self.interrupt_order
        self._raw_interrupts: tuple[Any, ...] | None = None
        self._raw_actions: tuple[Any, ...] | None = None
        self._raw_observation: FrozenDict | None = None
        self._decision: _DecisionCache | None = None
        self._numeric_contexts: dict[Any, Any] = {}

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

    def apply_action(self, action: ScheduledAction) -> None:
        # Validate against the unchanged decision's canonical legal objects. A
        # forged or mutated public raw payload is never sent to the engine.
        decision = self._decision_cache()
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

    def is_terminal(self) -> bool:
        return bool(self.raw.is_terminal())

    def returns(self) -> Any:
        return self.raw.returns()

    def wealth(self) -> Any:
        return self.raw.wealth()

    def neural_observation(self) -> FrozenDict:
        """Complete immutable observation reused for one scheduled decision."""
        decision = self._decision_cache()
        if decision.observation is None:
            if self._raw_observation is None:
                self._raw_observation = freeze_json(dict(self.raw.observation()))
            observation = dict(self._raw_observation)
            observation.update({"current_decision_player": decision.owner,
                                "decision_kind": decision.kind,
                                "legal_actions": [action.neural_features() for action in self._legal_actions(decision)],
                                "interrupt_scheduler": {"schema": SCHEMA, "order": list(self.interrupt_order),
                                                        "passed": sorted(self._passed)}})
            decision.observation = freeze_json(observation)
        return decision.observation

    def numeric_input(self, actions: tuple[ScheduledAction, ...], buckets: int) -> Any:
        """Compile the unchanged complete decision directly from native trees."""
        if not hasattr(self.raw, "numeric_observation"):
            return None
        from studies.campaign.features import (NUMERIC_SCHEMA, cached_numeric_action,
                                              cached_numeric_context, compile_numeric)
        decision = self._decision_cache()
        menu = self._legal_actions(decision)
        lookup = {action.id: index for index, action in enumerate(menu)}
        try:
            indices = tuple(lookup[action.id] for action in actions)
        except KeyError as error:
            raise ValueError("Numerical input contains a stale/foreign action") from error
        if any(menu[index] is not action for index, action in zip(indices, actions)):
            # Equal external wrappers still require the authoritative public
            # validation path; they cannot inject a numerical feature payload.
            return None
        context_key = (buckets, self.interrupt_order)
        if context_key not in self._numeric_contexts:
            context = self.raw.numeric_context().scheduled_context(SCHEMA, self.interrupt_order)
            # This source fingerprint is evaluated once, and is the same context
            # compatibility key used by existing recovery checkpoints.
            source_key = hashlib.sha256(json.dumps(self.context(), sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            if len(self._numeric_contexts) >= 8:
                self._numeric_contexts.clear()
            self._numeric_contexts[context_key] = (source_key, cached_numeric_context(context, buckets, source_key))
        source_key, context_graph = self._numeric_contexts[context_key]
        if buckets not in decision.numeric:
            snapshots = tuple(action.numeric_snapshot() for action in menu)
            if any(snapshot is None for snapshot in snapshots):
                return None
            observation = self.raw.numeric_observation().scheduled_observation(
                decision.owner, decision.kind, snapshots, SCHEMA, self.interrupt_order, sorted(self._passed))
            prepared = tuple(cached_numeric_action(snapshot, buckets) for snapshot in snapshots)
            graphs, factors = tuple(item[0] for item in prepared), tuple(item[1] for item in prepared)
            if len(decision.numeric) >= 8:
                decision.numeric.clear()
            decision.numeric[buckets] = (compile_numeric(observation, buckets), graphs, factors)
        observation_graph, graphs, factors = decision.numeric[buckets]
        return {"schema": NUMERIC_SCHEMA, "owner": decision.owner, "context_key": source_key,
                "packed_graph": {"context": context_graph, "observation": observation_graph,
                                 "actions": tuple(graphs[index] for index in indices),
                                 "action_factors": tuple(factors[index] for index in indices)}}

    def observation(self) -> dict[str, Any]:
        # Public callers may edit a detached mutable observation; inference
        # retains the immutable source directly and avoids repeated conversion.
        return json.loads(self.neural_observation().canonical_json)

    def context(self) -> dict[str, Any]:
        # Public callers retain the detached, mutable JSON contract. Inference
        # uses the immutable snapshot instead of retranslating the registry on
        # every searched position.
        return json.loads(self.neural_context_key())

    def neural_context(self) -> FrozenDict:
        """Return the immutable definition shared by this environment's clones.

        Campaign context contains the scenario/rules definition, never changing
        game state or execution RNG. Restore replaces this cache transactionally.
        """
        if self._context_order != self.interrupt_order:
            self._neural_context = None
            self._context_order = self.interrupt_order
        if self._neural_context is None:
            context = dict(self.raw.context())
            context["interrupt_scheduler"] = {"schema": SCHEMA, "order": list(self.interrupt_order)}
            snapshot = freeze_json(context)
            # Validate the entire plain JSON definition before publishing it.
            snapshot.canonical_json
            self._neural_context = snapshot
        return self._neural_context

    def neural_context_key(self) -> str:
        return self.neural_context().canonical_json

    def clone(self) -> CampaignAdapter:
        self._sync()
        result = CampaignAdapter(self.raw.clone(), interrupt_order=self.interrupt_order)
        result._passed = self._passed.copy()
        result._neural_context = self._neural_context
        result._context_order = self._context_order
        result._numeric_contexts = self._numeric_contexts
        # Copy lazy cache containers while sharing their immutable source data.
        # Neither real-play nor search RNG is stored in these snapshots.
        if result._anchor == self._anchor:
            result._raw_interrupts = self._raw_interrupts
            result._raw_actions = self._raw_actions
            result._raw_observation = self._raw_observation
            result._decision = replace(self._decision, numeric=self._decision.numeric.copy()) if self._decision is not None else None
        return result

    def clone_for_search(self, seed: int) -> CampaignAdapter:
        self._sync()
        result = CampaignAdapter(self.raw.clone_for_search(seed), interrupt_order=self.interrupt_order)
        result._passed = self._passed.copy()
        result._neural_context = self._neural_context
        result._context_order = self._context_order
        result._numeric_contexts = self._numeric_contexts
        # Copy lazy cache containers while sharing their immutable source data.
        # Neither real-play nor search RNG is stored in these snapshots.
        if result._anchor == self._anchor:
            result._raw_interrupts = self._raw_interrupts
            result._raw_actions = self._raw_actions
            result._raw_observation = self._raw_observation
            result._decision = replace(self._decision, numeric=self._decision.numeric.copy()) if self._decision is not None else None
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
