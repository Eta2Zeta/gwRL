"""Lossless JSON traversal and variable entity graphs for campaign observations.

Every JSON container and scalar becomes a node; nothing is selected by a fixed
unit list, field allowlist, or sequence limit. Directed edges retain the JSON
hierarchy, matching registry identities, and physical geography adjacency.
Strings use a documented hashed lexical vocabulary: both the complete UTF-8
string and *every* word/punctuation token contribute. Hash collisions are an
ordinary finite embedding approximation, not an unknown-field/drop policy.
Parsed graphs contain integers/numbers only and may be cached; learned vectors
must be recomputed on every forward pass.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from studies.shared.immutable_json import FrozenDict

try:
    from gwrl_cpp import CampaignNumericSnapshot, compile_campaign_graph as _native_compile_graph
except ImportError:
    CampaignNumericSnapshot = _native_compile_graph = None

SCHEMA = "campaign-neural-input-v1"
NODE_TYPES = ("null", "bool", "number", "string", "array", "object")
NUMERIC_DIM = 8
RELATIONS = 6
PARENT_TO_CHILD, CHILD_TO_PARENT, IDENTITY_REFERENCE, REFERENCE_BACK, ADJACENT, EXTERNAL_REFERENCE = range(RELATIONS)
ENTITY_COLLECTIONS = frozenset({
    "nodes", "factions", "nations", "units", "territories", "facilities",
    "construction", "repairs", "rails", "battles",
})
LEXEMES = re.compile(r"[^\W_]+|_|[^\w\s]", re.UNICODE)


def canonical(value: Any) -> str:
    if isinstance(value, FrozenDict):
        return value.canonical_json
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


@lru_cache(maxsize=131072)
def lexical_ids(text: str, role: str, buckets: int) -> tuple[int, ...]:
    def token_id(value: str) -> int:
        return int.from_bytes(hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest(), "little") % buckets

    return (token_id(role + ":full:" + text),
            *(token_id(role + ":part:" + token.group()) for token in LEXEMES.finditer(text)))


@dataclass(frozen=True)
class Graph:
    """A complete document graph; IDs below are local node indices."""
    token_ids: tuple[int, ...]
    token_offsets: tuple[int, ...]  # Includes the final offset for EmbeddingBag.
    types: tuple[int, ...]
    numeric: tuple[tuple[float, ...], ...]
    edges: tuple[tuple[int, int, int], ...]
    identities: dict[str, tuple[int, ...]]
    references: tuple[tuple[int, str], ...]
    leaf_count: int

    @property
    def node_count(self) -> int:
        return len(self.types)


def compile_graph_python(value: Any, buckets: int) -> Graph:
    """Reference traversal, retained as the exact oracle and portable fallback."""
    if buckets < 2:
        raise ValueError("The lexical vocabulary needs at least two buckets")
    tokens: list[int] = []
    offsets = [0]
    types: list[int] = []
    numeric: list[tuple[float, ...]] = []
    edges: list[tuple[int, int, int]] = []
    identities: dict[str, set[int]] = {}
    references: list[tuple[int, str]] = []
    paths: dict[tuple[Any, ...], int] = {}
    leaves = 0

    def bind(identity: str, index: int) -> None:
        identities.setdefault(identity, set()).add(index)

    def visit(item: Any, path: tuple[Any, ...], key: str, position: int) -> int:
        nonlocal leaves
        index = len(types)
        paths[path] = index
        words = list(lexical_ids(key, "field", buckets))
        number, length, size = 0.0, 0, 0
        if item is None:
            kind = "null"
        elif isinstance(item, bool):
            kind, number = "bool", float(item)
        elif isinstance(item, (int, float)):
            kind, number = "number", float(item)
            if not math.isfinite(number):
                raise ValueError("Neural features require finite JSON numbers")
        elif isinstance(item, str):
            kind, length = "string", len(item.encode("utf-8"))
            words.extend(lexical_ids(item, "value", buckets))
            references.append((index, item))
            # Turn serials are JSON strings to preserve exact integer storage.
            # Retain the string tokens while also exposing their magnitude.
            if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", item):
                candidate = float(item)
                if math.isfinite(candidate):
                    number = candidate
        elif isinstance(item, list):
            kind, size = "array", len(item)
        elif isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                raise ValueError("JSON object keys must be strings")
            kind, size = "object", len(item)
        else:
            raise TypeError(f"Unsupported neural JSON value: {type(item).__name__}")
        tokens.extend(words)
        offsets.append(len(tokens))
        types.append(NODE_TYPES.index(kind))
        magnitude = math.log1p(abs(number))
        # No numerical clipping: signed log compression remains unbounded.
        numeric.append((math.copysign(magnitude, number), float(number != 0),
                        float(number < 0), math.log1p(length), math.log1p(size),
                        math.log1p(position), math.sin(position), math.cos(position)))
        if kind == "object":
            if isinstance(item.get("id"), str):
                bind(item["id"], index)
            for field, child in sorted(item.items()):
                target = visit(child, path + (field,), field, 0)
                edges.extend(((index, target, PARENT_TO_CHILD), (target, index, CHILD_TO_PARENT)))
                if key in ENTITY_COLLECTIONS and isinstance(child, dict):
                    bind(field, target)
        elif kind == "array":
            for position, child in enumerate(item):
                target = visit(child, path + (position,), "[]", position)
                edges.extend(((index, target, PARENT_TO_CHILD), (target, index, CHILD_TO_PARENT)))
        else:
            leaves += 1
        return index

    visit(value, (), "$", 0)
    for source, identity in references:
        for target in sorted(identities.get(identity, ())):
            if source != target:
                edges.extend(((target, source, IDENTITY_REFERENCE), (source, target, REFERENCE_BACK)))
    # Map links get direct message-passing edges as well as their complete
    # JSON representation (which retains river/rail/directional attributes).
    if isinstance(value, dict):
        geography = value.get("geography", {})
        nodes = geography.get("nodes", {}) if isinstance(geography, dict) else {}
        for identity, node in nodes.items():
            if not isinstance(node, dict):
                continue
            source = paths.get(("geography", "nodes", identity))
            for neighbor in node.get("neighbors", []):
                target = paths.get(("geography", "nodes", neighbor.get("neighbor_id")))
                if source is not None and target is not None:
                    edges.append((source, target, ADJACENT))
    return Graph(tuple(tokens), tuple(offsets), tuple(types), tuple(numeric), tuple(edges),
                 {name: tuple(sorted(indices)) for name, indices in identities.items()},
                 tuple(references), leaves)


@lru_cache(maxsize=131072)
def _string_descriptor(text: str) -> tuple[int, float]:
    """Keep Python's UTF-8 and Unicode decimal semantics in the native path."""
    number = 0.0
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        candidate = float(text)
        if math.isfinite(candidate):
            number = candidate
    return len(text.encode("utf-8")), number


@lru_cache(maxsize=32768)
def _cached_numeric_features(number: float, negative: bool, length: int, size: int,
                             position: int) -> tuple[float, ...]:
    # Include the sign separately in the cache key: -0.0 == 0.0 in Python,
    # but their signed-log feature must retain its exact floating-point sign.
    magnitude = math.log1p(abs(number))
    return (math.copysign(magnitude, -1.0 if negative else 1.0), float(number != 0),
            float(number < 0), math.log1p(length), math.log1p(size),
            math.log1p(position), math.sin(position), math.cos(position))


def _numeric_features(number: float, length: int, size: int, position: int) -> tuple[float, ...]:
    return _cached_numeric_features(number, math.copysign(1.0, number) < 0, length, size, position)


def graph_compiler_backend() -> str:
    return "native" if _native_compile_graph is not None else "python_reference"


def compile_graph(value: Any, buckets: int) -> Graph:
    """Visit every JSON field with the same ordered graph as the reference.

    Only source tokens, numeric constants and topology are compiled/cached.
    Model embeddings, policy/value predictions and gradients are never cached.
    Rebuild the extension to use native traversal; the reference remains usable
    on a machine without that binding and is reported by graph_compiler_backend.
    """
    if _native_compile_graph is None or not isinstance(buckets, int):
        return compile_graph_python(value, buckets)
    return Graph(**_native_compile_graph(value, buckets, lexical_ids,
                                        _string_descriptor, _numeric_features))


@lru_cache(maxsize=8)
def cached_context(serialized: str, buckets: int) -> Graph:
    """Cache source tokens/topology only, never tensors from model parameters."""
    return compile_graph(json.loads(serialized), buckets)


@lru_cache(maxsize=256)
def cached_observation(serialized: str, buckets: int) -> Graph:
    """Reuse complete source graphs across replay samples and actor models.

    Content keys detect edits to caller-owned JSON. No learned embeddings or
    autograd tensors are retained, and the cache has a bounded entry count.
    """
    return compile_graph(json.loads(serialized), buckets)


@lru_cache(maxsize=4096)
def cached_action(serialized: str, buckets: int) -> Graph:
    """Keep small legal-action graphs separate from larger observation graphs."""
    return compile_graph(json.loads(serialized), buckets)


def make_input(env: Any, actions: Any) -> dict[str, Any]:
    """Snapshot public features; reuse validated immutable decision data.

    Environments may expose immutable source snapshots for inference. Ordinary
    mutable JSON still gets validated and detached; neither path reads execution
    randomness or includes planning identities in the neural input.
    """
    shared_observation = getattr(env, "neural_observation", None)
    observation = shared_observation() if shared_observation is not None else env.observation()
    shared_context = getattr(env, "neural_context", None)
    context = shared_context() if shared_context is not None else env.context()
    if not isinstance(observation, dict) or not isinstance(context, dict):
        raise TypeError("Campaign neural inputs require observation/context objects")
    forbidden = {"history", "random", "rng", "rng_state", "random_state", "dice_tape",
                 "future_tape", "future_rolls", "planning_key", "definition_fingerprint"}
    state = observation.get("state", {})
    if forbidden.intersection(observation) or (isinstance(state, dict) and forbidden.intersection(state)):
        raise ValueError("Execution RNG, future dice, history and planning hashes are not neural features")
    features = []
    for action in actions:
        if hasattr(action, "neural_features"):
            feature = action.neural_features()
        elif hasattr(action, "features"):
            feature = action.features()
        elif isinstance(action, dict):
            feature = action
        else:
            raise TypeError("Campaign actions must expose features() or be plain JSON objects")
        if not isinstance(feature, dict):
            raise TypeError("Campaign action features must be a JSON object")
        features.append(feature)

    def snapshot(value: dict[str, Any]) -> dict[str, Any]:
        if isinstance(value, FrozenDict):
            # Canonical text validates the complete source once. The same frozen
            # observation/actions are then safe for search, replay and clones.
            value.canonical_json
            return value
        return json.loads(canonical(value))

    return {"schema": SCHEMA, "observation": snapshot(observation),
            "context": snapshot(context), "actions": [snapshot(feature) for feature in features]}


def action_factors(action: dict[str, Any]) -> tuple[str, str, str, str]:
    """Readout groups, never additional engine actions or interchangeability.

    Preserve the full authoritative action below these conditional categories.
    Unrecognized parameters still enter the action graph and final leaf score.
    Empty categories simply have one branch and change no probabilities.
    """
    raw = action.get("action")
    raw = raw if isinstance(raw, dict) else action
    parameters = raw.get("parameters", {})
    parameters = parameters if isinstance(parameters, dict) else {}
    groups = (
        ("source", "from", "origin", "source_zone", "unit", "units", "group", "force", "transport", "carrier", "facility", "battle"),
        ("path", "route", "sea_route", "land_route"),
        ("target", "destination", "to", "zone", "recipient", "endpoint"),
    )
    return (canonical(raw.get("kind", action.get("kind", "unspecified"))),
            *(canonical({key: parameters[key] for key in keys if key in parameters}) for keys in groups))

# The graph/model meaning is unchanged; only its transport/storage is numerical.
NUMERIC_SCHEMA = "campaign-numeric-input-v1"


@lru_cache(maxsize=8)
def context_source_key(serialized: str) -> str:
    """Use the same complete registry identity for raw and numeric replay.

    Canonical source text uses UTF-8; historical recovery context fingerprints
    use JSON ASCII escapes. Normalize that spelling once per fixed registry.
    """
    ascii_text = json.dumps(json.loads(serialized), sort_keys=True,
                            separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(ascii_text.encode()).hexdigest()


@lru_cache(maxsize=8)
def numeric_compiler(buckets: int):
    from gwrl_cpp import CampaignNumericGraphCompiler
    return CampaignNumericGraphCompiler(buckets, lexical_ids, _string_descriptor, _numeric_features)


def compile_numeric(snapshot: Any, buckets: int):
    return numeric_compiler(buckets).compile(snapshot)


def _source_key_bytes(value: Any) -> int:
    if isinstance(value, str):
        return 96 + 4 * len(value.encode("utf-8"))
    if isinstance(value, tuple):
        return 64 + 16 * len(value) + sum(_source_key_bytes(item) for item in value)
    return 64


class _NumericSourceCache:
    """Reuse immutable compiled sources across independent game roots.

    Lookup and publication hold the lock; compiler callbacks never do. A second
    check after compilation makes racing misses return the same owning handle.
    Keys include the full authoritative action payload or full context digest.
    """
    def __init__(self, byte_limit: int, entry_limit: int) -> None:
        self.byte_limit, self.entry_limit = byte_limit, entry_limit
        self.values: OrderedDict[tuple, tuple[Any, int]] = OrderedDict()
        self.bytes = self.hits = self.misses = 0
        self.lock = threading.RLock()

    def get(self, key: tuple) -> Any:
        with self.lock:
            found = self.values.get(key)
            if found is None:
                self.misses += 1
                return None
            self.hits += 1
            self.values.move_to_end(key)
            return found[0]

    def publish(self, key: tuple, value: Any, size: int) -> Any:
        with self.lock:
            found = self.values.get(key)
            if found is not None:
                self.values.move_to_end(key)
                return found[0]
            if self.entry_limit and size <= self.byte_limit:
                while self.values and (len(self.values) >= self.entry_limit or self.bytes + size > self.byte_limit):
                    _, (_, old_size) = self.values.popitem(last=False)
                    self.bytes -= old_size
                self.values[key] = value, size
                self.bytes += size
        return value

    def clear(self) -> None:
        with self.lock:
            self.values.clear()
            self.bytes = self.hits = self.misses = 0

    def cache_info(self) -> dict[str, int]:
        with self.lock:
            return {"entries": len(self.values), "bytes": self.bytes, "hits": self.hits, "misses": self.misses,
                    "entry_limit": self.entry_limit, "byte_limit": self.byte_limit}


_NUMERIC_ACTION_SOURCES = _NumericSourceCache(64 * 1024 * 1024, 4096)
_NUMERIC_CONTEXT_SOURCES = _NumericSourceCache(128 * 1024 * 1024, 8)


def cached_numeric_context(snapshot: Any, buckets: int, source_key: str):
    """Intern a complete registry using the existing exact-source fingerprint."""
    key = (source_key, buckets)
    cached = _NUMERIC_CONTEXT_SOURCES.get(key)
    if cached is not None:
        return cached
    graph = compile_numeric(snapshot, buckets)
    return _NUMERIC_CONTEXT_SOURCES.publish(key, graph, graph.nbytes + _source_key_bytes(key) + 256)


def cached_numeric_action(snapshot: Any, buckets: int):
    """Return the complete action graph and factors, never keyed by action ID alone."""
    source_key = getattr(snapshot, "cache_key", None) if isinstance(snapshot, CampaignNumericSnapshot) else None
    key = (source_key, buckets) if source_key is not None else None
    if key is not None:
        cached = _NUMERIC_ACTION_SOURCES.get(key)
        if cached is not None:
            return cached
    graph = compile_numeric(snapshot, buckets)
    factors = tuple(_native_factor(value) for value in snapshot.factor_json())
    result = graph, factors
    if key is None:
        return result
    size = graph.nbytes + _source_key_bytes(key) + _source_key_bytes(factors) + 256
    return _NUMERIC_ACTION_SOURCES.publish(key, result, size)


@lru_cache(maxsize=16384)
def _native_factor(serialized: str) -> str:
    # Four small category keys retain Python's exact JSON spelling, including
    # unusual numeric/Unicode parameters. No board or menu is parsed here.
    return canonical(json.loads(serialized))


def make_numeric_input(env: Any, actions: Any, buckets: int) -> dict[str, Any]:
    """Use complete native numerical snapshots; keep external JSON fallback."""
    actions = tuple(actions)
    export = getattr(env, "numeric_input", None)
    if export is None:
        return make_input(env, actions)
    prepared = export(actions, buckets)
    return make_input(env, actions) if prepared is None else prepared


def validate_numeric_input(item: Any, *, buckets: int | None = None) -> int:
    """Validate numerical replay structure without rebuilding its JSON source."""
    if (not isinstance(item, dict) or set(item) != {"schema", "owner", "context_key", "packed_graph"}
            or item.get("schema") != NUMERIC_SCHEMA or item["owner"] not in ("axis", "allies", "comintern", None)
            or not isinstance(item["context_key"], str) or len(item["context_key"]) != 64):
        raise ValueError("Invalid numerical replay input")
    packed = item["packed_graph"]
    if not isinstance(packed, dict) or set(packed) != {"context", "observation", "actions", "action_factors"}:
        raise ValueError("Incomplete numerical replay graph")
    actions, factors = packed["actions"], packed["action_factors"]
    if not isinstance(actions, (tuple, list)) or not isinstance(factors, (tuple, list)) or len(actions) != len(factors):
        raise ValueError("Numerical legal menu and factors disagree")
    from gwrl_cpp import CampaignNumericGraph
    for graph in (packed["context"], packed["observation"], *actions):
        if not isinstance(graph, CampaignNumericGraph) or graph.node_count < 1:
            raise ValueError("Invalid numerical graph handle")
        if buckets is not None and graph.token_buckets != buckets:
            raise ValueError("Numerical graph vocabulary differs from model")
    if any(len(factor) != 4 or any(not isinstance(value, str) for value in factor) for factor in factors):
        raise ValueError("Invalid numerical action factors")
    return len(actions)
