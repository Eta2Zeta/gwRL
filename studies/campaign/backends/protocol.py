"""Device-neutral batch execution and explicit host inspection contracts.

Execution payloads, numerical inputs and action selections may be device-resident
buffers. A backend need not convert them to Python lists for each operation.
Canonical inspection and snapshots are explicit boundaries, not hot-path inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from studies.shared.multiplayer_mcts import SearchEnv

SNAPSHOT_SCHEMA = "campaign-backend-snapshot-v1"


@dataclass(frozen=True, slots=True)
class DecisionBatch:
    backend: str
    lanes: tuple[int, ...]
    payload: Any


@dataclass(frozen=True, slots=True)
class BackendBuffer:
    backend: str
    lanes: tuple[int, ...]
    payload: Any


@dataclass(frozen=True, slots=True)
class BackendSnapshot:
    schema: str
    backend: str
    lanes: tuple[int, ...]
    payload: Any


@dataclass(frozen=True, slots=True)
class DecisionInspection:
    lane: int
    key: str
    actor: str | None
    kind: str
    terminal: bool
    action_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BackendInfo:
    name: str
    device: str
    execution: str
    native_batch_execution: bool


class CampaignBackend(Protocol):
    """Independent game lanes with complete, authoritative decision identities.

    Action selections and explicit chance outcomes align with the supplied batch.
    Their representation belongs to the backend. The CPU reference accepts action
    indices or canonical IDs, and nested integer die faces for explicit outcomes.
    No state, entity, legal-action or dice-count limit is part of this contract.
    Search forks accept opaque seed buffers so a GPU implementation can retain
    them on device. Repeated source lanes are allowed for independent simulations
    of one root; each destination is a distinct lane in the returned backend.
    """
    info: BackendInfo

    @property
    def lane_count(self) -> int: ...
    def decision_batch(self, lanes: Sequence[int] | None = None) -> DecisionBatch: ...
    def apply_actions(self, batch: DecisionBatch, selections: Any) -> None: ...
    def resolve_chance(self, batch: DecisionBatch, outcomes: Any = None) -> None: ...
    def numeric_inputs(self, batch: DecisionBatch, buckets: int = 2048) -> BackendBuffer: ...
    def inspect_decisions(self, batch: DecisionBatch) -> tuple[DecisionInspection, ...]: ...
    def inspect_numeric(self, buffer: BackendBuffer) -> Any: ...
    def inspect_chance_requests(self, batch: DecisionBatch) -> Any: ...
    def inspect_states(self, lanes: Sequence[int] | None = None) -> Any: ...
    def snapshot(self, lanes: Sequence[int] | None = None) -> BackendSnapshot: ...
    def restore(self, snapshot: BackendSnapshot) -> None: ...
    def clone(self, lanes: Sequence[int] | None = None) -> CampaignBackend: ...
    def clone_for_search(self, seeds: Any, lanes: Sequence[int] | None = None) -> CampaignBackend: ...
    def scalar(self, lane: int) -> SearchEnv: ...
