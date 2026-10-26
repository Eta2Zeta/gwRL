"""Batch facade for the unchanged C++ engine and campaign interrupt scheduler.

The reference executes lanes sequentially. It establishes the backend boundary;
it does not claim that a Python loop is parallel or GPU execution. Canonical
menus and numerical inputs are reused for each complete unchanged decision.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Sequence

from studies.shared.campaign_adapter import CampaignAdapter, ScheduledAction
from .protocol import (BackendBuffer, BackendInfo, BackendSnapshot, DecisionBatch,
                       DecisionInspection, SNAPSHOT_SCHEMA)


@dataclass(frozen=True, slots=True)
class _DecisionRow:
    lane: int
    env: CampaignAdapter
    key: str
    inspection: DecisionInspection
    actions: tuple[ScheduledAction, ...]
    action_indices: dict[str, int] = field(compare=False)
    numeric: dict[int, Any] = field(default_factory=dict, compare=False)


@dataclass(frozen=True, slots=True)
class _DecisionPayload:
    owner: object
    rows: tuple[_DecisionRow, ...]


@dataclass(frozen=True, slots=True)
class _NumericPayload:
    owner: object
    lanes: tuple[int, ...]
    values: tuple[Any, ...]


class CPUScalarView:
    """Explicit compatibility view; a retained view follows lane restoration.

    Search clones are ordinary independent CampaignAdapter instances. Existing
    scalar MCTS remains scalar and is not relabeled as a batched search.
    """
    __slots__ = ("_backend", "_lane")

    def __init__(self, backend: CPUBatchBackend, lane: int):
        self._backend, self._lane = backend, lane

    def __getattr__(self, name):
        return getattr(self._backend._envs[self._lane], name)


class CPUBatchBackend:
    info = BackendInfo("cpu", "cpu", "sequential_reference", False)
    name = "cpu"

    def __init__(self, envs: Sequence[CampaignAdapter]):
        self._envs = tuple(envs)
        if not self._envs or any(not isinstance(env, CampaignAdapter) for env in self._envs):
            raise ValueError("CPU backend requires independent CampaignAdapter lanes")
        if len({id(env) for env in self._envs}) != len(self._envs) or len(
                {id(env.raw) for env in self._envs}) != len(self._envs):
            raise ValueError("CPU backend lanes must not share a mutable environment")
        self._owner = object()
        self._rows: dict[int, _DecisionRow] = {}
        self._views: dict[int, CPUScalarView] = {}

    @property
    def lane_count(self) -> int:
        return len(self._envs)

    def _lanes(self, lanes, *, unique=True) -> tuple[int, ...]:
        if lanes is None:
            return tuple(range(self.lane_count))
        try:
            result = tuple(lanes)
        except TypeError as error:
            raise ValueError("Lane selection must be an integer sequence") from error
        if any(type(lane) is not int or not 0 <= lane < self.lane_count for lane in result):
            raise ValueError("Lane selection contains an invalid lane")
        if unique and len(set(result)) != len(result):
            raise ValueError("Each selected lane must occur once")
        return result

    def decision_batch(self, lanes=None) -> DecisionBatch:
        selected = self._lanes(lanes)
        rows = []
        for lane in selected:
            env = self._envs[lane]
            key = env.planning_key()
            row = self._rows.get(lane)
            if row is None or row.env is not env or row.key != key:
                actions = tuple(env.legal_actions())
                ids = tuple(action.id for action in actions)
                if len(set(ids)) != len(ids):
                    raise ValueError("CPU legal menu contains ambiguous action identities")
                inspection = DecisionInspection(lane, key, env.current_decision_player(),
                                                env.decision_kind(), env.is_terminal(), ids)
                row = _DecisionRow(lane, env, key, inspection, actions,
                                   {identity: index for index, identity in enumerate(ids)})
                self._rows[lane] = row
            rows.append(row)
        return DecisionBatch(self.name, selected, _DecisionPayload(self._owner, tuple(rows)))

    def _check_batch(self, batch) -> tuple[_DecisionRow, ...]:
        if not isinstance(batch, DecisionBatch) or batch.backend != self.name or not isinstance(
                batch.payload, _DecisionPayload) or batch.payload.owner is not self._owner:
            raise ValueError("Foreign CPU decision batch")
        rows = batch.payload.rows
        if batch.lanes != tuple(row.lane for row in rows) or self._lanes(batch.lanes) != batch.lanes:
            raise ValueError("Invalid CPU decision batch lane metadata")
        for row in rows:
            if row.env is not self._envs[row.lane] or row.key != row.env.planning_key():
                raise ValueError("Stale CPU decision batch")
        return rows

    def inspect_decisions(self, batch) -> tuple[DecisionInspection, ...]:
        return tuple(row.inspection for row in self._check_batch(batch))

    def apply_actions(self, batch, selections) -> None:
        rows = self._check_batch(batch)
        try:
            selected = tuple(selections)
        except TypeError as error:
            raise ValueError("CPU action selections must align with the decision batch") from error
        if len(selected) != len(rows):
            raise ValueError("CPU action selections must align with the decision batch")
        actions = []
        for row, selection in zip(rows, selected):
            if row.inspection.terminal or row.inspection.kind == "chance":
                raise ValueError("This lane has no player action")
            if type(selection) is int and 0 <= selection < len(row.actions):
                action = row.actions[selection]
            elif isinstance(selection, str) and selection in row.action_indices:
                action = row.actions[row.action_indices[selection]]
            else:
                raise ValueError("Illegal CPU action index or canonical identity")
            actions.append(action)
        # Every key and selection is validated before the first lane mutates.
        # Native rule application remains authoritative for each legal object.
        for row, action in zip(rows, actions):
            row.env.apply_action(action)

    def inspect_chance_requests(self, batch) -> tuple[Any, ...]:
        return tuple(copy.deepcopy(row.env.chance_request()) for row in self._check_batch(batch))

    def resolve_chance(self, batch, outcomes=None) -> None:
        rows = self._check_batch(batch)
        if any(row.inspection.terminal or row.inspection.kind != "chance" for row in rows):
            raise ValueError("Every selected lane must have a pending chance request")
        if outcomes is None:
            for row in rows:
                row.env.resolve_chance()
            return
        try:
            outcomes = tuple(outcomes)
        except TypeError as error:
            raise ValueError("Explicit outcomes must align with the chance batch") from error
        if len(outcomes) != len(rows):
            raise ValueError("Explicit outcomes must align with the chance batch")
        # This explicit conformance seam validates on independent clones. It
        # neither consumes execution RNG nor partially commits a bad batch.
        # Normal sampled execution above does not clone the game states.
        replacements = {}
        for row, outcome in zip(rows, outcomes):
            try:
                faces = tuple(tuple(die) for die in outcome)
            except TypeError as error:
                raise ValueError("Explicit outcomes require nested integer die faces") from error
            if any(type(face) is not int for die in faces for face in die):
                raise ValueError("Explicit outcomes require integer die faces")
            replacement = row.env.clone()
            replacement.apply_chance_outcome(row.key, faces)
            replacements[row.lane] = replacement
        self._replace(replacements)

    def numeric_inputs(self, batch, buckets=2048) -> BackendBuffer:
        if type(buckets) is not int or buckets <= 0:
            raise ValueError("Numerical input vocabulary size must be a positive integer")
        from studies.campaign.features import make_numeric_input
        rows = self._check_batch(batch)
        values = []
        for row in rows:
            if buckets not in row.numeric:
                if len(row.numeric) >= 8:
                    row.numeric.clear()
                row.numeric[buckets] = make_numeric_input(row.env, row.actions, buckets)
            values.append(row.numeric[buckets])
        return BackendBuffer(self.name, batch.lanes, _NumericPayload(self._owner, batch.lanes, tuple(values)))

    def inspect_numeric(self, buffer) -> tuple[Any, ...]:
        if not isinstance(buffer, BackendBuffer) or buffer.backend != self.name or not isinstance(
                buffer.payload, _NumericPayload) or buffer.payload.owner is not self._owner or buffer.lanes != \
                buffer.payload.lanes or len(buffer.lanes) != len(buffer.payload.values):
            raise ValueError("Foreign CPU numerical buffer")
        # Mutable dictionaries/lists are detached; immutable native graph
        # handles and frozen context trees retain their existing shared storage.
        return copy.deepcopy(buffer.payload.values)

    def inspect_states(self, lanes=None) -> tuple[str, ...]:
        return tuple(self._envs[lane].serialize() for lane in self._lanes(lanes))

    def snapshot(self, lanes=None) -> BackendSnapshot:
        selected = self._lanes(lanes)
        return BackendSnapshot(SNAPSHOT_SCHEMA, self.name, selected, self.inspect_states(selected))

    def _replace(self, replacements) -> None:
        envs = list(self._envs)
        for lane, env in replacements.items():
            envs[lane] = env
            self._rows.pop(lane, None)
        self._envs = tuple(envs)

    def restore(self, snapshot) -> None:
        if not isinstance(snapshot, BackendSnapshot) or snapshot.schema != SNAPSHOT_SCHEMA or snapshot.backend != self.name:
            raise ValueError("Unsupported CPU backend snapshot")
        selected = self._lanes(snapshot.lanes)
        if not isinstance(snapshot.payload, tuple) or len(snapshot.payload) != len(selected) or any(
                not isinstance(value, str) for value in snapshot.payload):
            raise ValueError("Invalid CPU backend snapshot payload")
        replacements = {}
        for lane, serialized in zip(selected, snapshot.payload):
            replacement = self._envs[lane].clone()
            replacement.restore(serialized)
            replacements[lane] = replacement
        self._replace(replacements)

    def clone(self, lanes=None) -> CPUBatchBackend:
        return type(self)([self._envs[lane].clone() for lane in self._lanes(lanes)])

    def clone_for_search(self, seeds, lanes=None) -> CPUBatchBackend:
        """Fork selected roots with independent search streams, without draws.

        CPU seeds are an aligned host sequence of unsigned 64-bit Python ints.
        Source lanes may repeat; destinations use dense independent lane IDs.
        """
        selected = self._lanes(lanes, unique=False)
        try:
            seeds = tuple(seeds)
        except TypeError as error:
            raise ValueError("CPU search seeds must align with source lanes") from error
        if len(seeds) != len(selected) or any(type(seed) is not int or not 0 <= seed < 2**64 for seed in seeds):
            raise ValueError("CPU search forks require one unsigned 64-bit seed per source lane")
        return type(self)([self._envs[lane].clone_for_search(seed) for lane, seed in zip(selected, seeds)])

    def scalar(self, lane) -> CPUScalarView:
        self._lanes((lane,))
        if lane not in self._views:
            self._views[lane] = CPUScalarView(self, lane)
        return self._views[lane]
