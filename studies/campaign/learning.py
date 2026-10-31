"""Bounded three-policy self play with raw vector targets and exact resume.

A rollout batch freezes all three policies. Only after its terminal or bootstrap
targets have been recorded may the live models update. A transition budget is a
collection cutoff, never a terminal condition or an alternative reward rule.
"""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
import math
import os
import platform
import random
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np
import torch
from torch import nn

from studies.shared.multiplayer_mcts import (
    PLAYERS, MctsConfig, VectorMCTS, action_key, probabilities, vector,
)
from studies.shared.immutable_json import FrozenDict, freeze_json

CHECKPOINT_SCHEMA = "campaign-learning-checkpoint-v1"
TARGET_SCHEMA = "campaign-raw-vector-target-v1"
REPLAY_TRACE_SCHEMA = "campaign-self-play-trace-v1"


class ReplayTraceWriter:
    """Append-only inspection data, deliberately separate from learner checkpoints.

    One writer describes one fresh invocation. It never changes the learner RNG
    or serializes a full position for every transition. A killed run can leave a
    valid prefix; absence of ``run_end`` explicitly means it is incomplete.
    """

    def __init__(self, path: str | Path, metadata: Mapping[str, Any]):
        self.path = Path(path)
        self._handle = self.path.open("x")
        self({"type": "run_start", **dict(metadata),
              "verification": "initial_serialized_sha256_then_planning_keys_and_seed",
              "resume_supported": False})

    def __call__(self, record: Mapping[str, Any]) -> None:
        self._handle.write(_canonical({"schema": REPLAY_TRACE_SCHEMA, **record}) + "\n")
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()


def _read_only(*_args, **_kwargs):
    raise TypeError("Replay context snapshots are read-only")


class _ReadOnlyDict(dict):
    """JSON-compatible immutable containers; pickle retains shared references."""
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _read_only

    def __reduce_ex__(self, _protocol):
        return type(self), (dict(self),)


class _ReadOnlyList(list):
    __setitem__ = __delitem__ = append = clear = extend = insert = pop = remove = reverse = sort = _read_only
    __iadd__ = __imul__ = _read_only

    def __reduce_ex__(self, _protocol):
        return type(self), (list(self),)


def _read_only_snapshot(value: Any) -> Any:
    # Retain the legacy container classes above for existing local checkpoints.
    # New snapshots also retain their canonical source text for graph reuse.
    return freeze_json(value)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _intern_context(context: dict[str, Any], pool: dict[str, dict[str, Any]]) -> dict[str, Any]:
    key = _fingerprint(context)  # Validates every static field before retaining it.
    if key not in pool:
        pool[key] = _read_only_snapshot(context)
    return pool[key]


def _intern_numeric_context(features: dict[str, Any], pool: dict[tuple[str, int], Any]) -> None:
    """Share immutable native buffers using source identity and vocabulary."""
    packed = features["packed_graph"]
    context = packed["context"]
    key = (features["context_key"], context.token_buckets)
    if key not in pool:
        if len(pool) >= 8:
            pool.clear()  # Existing replay rows retain their shared buffers.
        pool[key] = context
    # Detach the small wrapper; neither the caller's input nor native arrays
    # change when two replay rows share their static context.
    features["packed_graph"] = {**packed, "context": pool[key]}


def _same_numeric_graph(first: Any, second: Any) -> bool:
    if first is second:
        return True
    left, right = first.packed_state(), second.packed_state()
    return (set(left) == set(right) and all(
        (item.dtype == right[key].dtype and item.shape == right[key].shape and
         np.array_equal(item.view(np.uint8), right[key].view(np.uint8)))
        if isinstance(item, np.ndarray) else item == right[key]
        for key, item in left.items()))


def _value_only_input(features: dict[str, Any]) -> dict[str, Any]:
    from .features import NUMERIC_SCHEMA
    if features["schema"] == NUMERIC_SCHEMA:
        return {**features, "packed_graph": {**features["packed_graph"], "actions": (), "action_factors": ()}}
    return {**features, "actions": []}


def _selected_features(action: Any) -> dict[str, Any]:
    """Materialize one selected action for diagnostics, outside neural input."""
    if hasattr(action, "features"):
        feature = action.features()
    elif hasattr(action, "neural_features"):
        feature = action.neural_features()
    else:
        feature = action
    if not isinstance(feature, dict):
        raise TypeError("Campaign action features must be a JSON object")
    return feature


def retained_numeric_input(features: dict[str, Any]) -> dict[str, Any]:
    """A numeric input to keep for a run: its observation has no spare capacity."""
    packed = features["packed_graph"]
    return {**features, "packed_graph": {**packed, "observation": packed["observation"].compacted()}}


def _sample_index(actions: Any, policy: list[float], rng: random.Random) -> int:
    order = sorted(range(len(actions)), key=lambda index: action_key(actions[index]))
    threshold = rng.random()
    for index in order:
        threshold -= policy[index]
        if threshold < 0:
            return index
    return order[-1]


def _decide(env: Any, result: Any, pending: list[dict[str, Any]], *, config: LearningConfig,
            rng: random.Random, numeric: bool, token_buckets: int, batch_version: str,
            numeric_pool: dict[tuple[str, int], Any], context_pool: dict[str, dict[str, Any]],
            replay: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sample the played move from a search result, record its sample and apply it."""
    from .features import NUMERIC_SCHEMA, make_numeric_input, validate_numeric_input
    from .neural import make_input
    owner = env.current_decision_player()
    if owner not in PLAYERS:
        raise ValueError("A policy choice must belong to one of the three actors")
    logs = [math.log(p) / config.temperature if p > 0 else -math.inf for p in result.policy]
    maximum = max(logs)
    policy = probabilities([math.exp(value - maximum) for value in logs], len(logs))
    index = _sample_index(result.actions, policy, rng)
    features = make_numeric_input(env, result.actions, token_buckets) if numeric else make_input(env, result.actions)
    numerical = features["schema"] == NUMERIC_SCHEMA
    if numerical:
        if (validate_numeric_input(features, buckets=token_buckets) != len(result.actions)
                or features["owner"] != owner):
            raise ValueError("Numerical replay differs from actual choice owner/menu")
        features = retained_numeric_input(features)
        _intern_numeric_context(features, numeric_pool)
    else:
        features["context"] = _intern_context(features["context"], context_pool)
    pending.append({"input": features, "owner": owner, "policy": policy, "rollout_version": batch_version})
    action = result.actions[index]
    if numerical:
        menu = [_selected_features(action) for action in result.actions] if replay is not None else None
        selected = menu[index] if menu is not None else _selected_features(action)
    else:
        menu, selected = features["actions"], features["actions"][index]
    raw = selected.get("action")
    raw = raw if isinstance(raw, dict) else selected
    if replay is not None:
        replay.update(selected_index=index, selected_action=selected, decision_menu=menu,
            search={"visit_counts": result.visit_counts, "priors": result.priors,
                    "policy": result.policy, "sampling_policy": policy,
                    "values": None if result.values is None else list(result.values),
                    "action_values": result.action_values, "simulations": config.simulations,
                    "max_depth": config.max_depth, "rollout_version": batch_version})
    event = {"kind": env.decision_kind(), "owner": owner, "action": action_key(action),
             "action_kind": raw.get("kind", "unknown"),
             "action_parameters": copy.deepcopy(raw.get("parameters", {}))}
    env.apply_action(action)
    return event


def episode_streams(learner_seed: int, environment_seed: int) -> tuple[random.Random, random.Random]:
    """One game's own search-seed and move-sampling streams.

    They depend only on the run seed and the game's environment seed, never on
    other games, so an episode plays the same in any process or batch makeup.
    """
    return (random.Random(f"campaign-episode-search:{learner_seed}:{environment_seed}"),
            random.Random(f"campaign-episode-policy:{learner_seed}:{environment_seed}"))


def play_episode(env: Any, evaluator: Any, *, config: LearningConfig, rules_version: str, numeric: bool,
                 token_buckets: int, batch_version: str, environment_seed: int,
                 max_transitions: int) -> dict[str, Any]:
    """Play one game to its end, or to the transition guard, with frozen policies.

    A finished game returns terminal-labelled samples. A game stopped by the
    guard returns no samples: complete-episode batches never bootstrap.
    """
    search_random, policy_random = episode_streams(config.seed, environment_seed)
    # Its own stream, so the game plays the same whatever share is kept.
    sample_random = random.Random(f"campaign-episode-samples:{config.seed}:{environment_seed}")
    pending: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    counts = dict(transitions=0, decisions=0, chance_events=0)
    numeric_pool: dict[tuple[str, int], Any] = {}
    context_pool: dict[str, dict[str, Any]] = {}
    while not env.is_terminal() and counts["transitions"] < max_transitions:
        before = env.planning_key()
        if env.decision_kind() == "chance":
            env.resolve_chance()
            counts["chance_events"] += 1
            event = {"kind": "chance", "owner": None, "action": None}
        else:
            search = MctsConfig(
                simulations=config.simulations, max_depth=config.max_depth, c_puct=config.c_puct,
                seed=search_random.getrandbits(64), rules_version=rules_version, mode=config.mode,
                root_dirichlet_alpha=config.root_dirichlet_alpha, root_dirichlet_epsilon=config.root_dirichlet_epsilon)
            result = VectorMCTS(evaluator, search).search(env, add_root_noise=config.root_noise, reuse_root=False)
            event = _decide(env, result, pending, config=config, rng=policy_random, numeric=numeric,
                            token_buckets=token_buckets, batch_version=batch_version,
                            numeric_pool=numeric_pool, context_pool=context_pool)
            if sample_random.random() >= config.sample_fraction:
                pending.pop()
            counts["decisions"] += 1
        counts["transitions"] += 1
        event.update(before=before, after=env.planning_key(), terminal=env.is_terminal())
        events.append(event)
    terminal = env.is_terminal()
    target = list(vector(env.returns())) if terminal else None
    records = [{**sample, "values": target.copy(), "target_source": "terminal", "target_schema": TARGET_SCHEMA}
               for sample in pending] if terminal else []
    return {"terminal": terminal, "records": records, "events": events, "counts": counts,
            "returns": target, "clock": env.observation()["state"]["clock"], "wealth": env.wealth()}


def _checkpoint_contexts(payload: dict[str, Any]):
    """Visit sample contexts without requiring a valid checkpoint up front."""
    groups = [payload.get(name, []) for name in ("replay", "pending", "batch_records")]
    parallel = payload.get("parallel_pending", [])
    if isinstance(parallel, list):
        groups.extend(parallel)
    for group in groups:
        if isinstance(group, list):
            for sample in group:
                if isinstance(sample, dict) and isinstance(sample.get("input"), dict):
                    context = sample["input"].get("context")
                    if isinstance(context, dict):
                        yield context


def _model_digest(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        tensor = value.detach().cpu().contiguous()
        digest.update(_canonical([name, str(tensor.dtype), list(tensor.shape)]).encode())
        digest.update(tensor.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class LearningConfig:
    simulations: int = 8
    max_depth: int = 16
    batch_size: int = 32
    epochs: int = 1
    learning_rate: float = 1e-3
    replay_capacity: int = 4096
    value_scale: float = 100.0
    c_puct: float = 1.5
    temperature: float = 1.0
    root_noise: bool = True
    root_dirichlet_alpha: float = 0.3
    root_dirichlet_epsilon: float = 0.25
    seed: int = 1
    mode: str = "multiplayer"
    # Share of a worker game's decisions kept as samples. A whole game holds over a
    # thousand close positions of about a megabyte each.
    sample_fraction: float = 1.0

    def __post_init__(self) -> None:
        for name in ("simulations", "max_depth", "batch_size", "epochs", "replay_capacity"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("learning_rate", "value_scale", "temperature", "root_dirichlet_alpha"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive and finite")
        if not math.isfinite(self.c_puct) or self.c_puct < 0:
            raise ValueError("c_puct must be finite and nonnegative")
        if not 0 <= self.root_dirichlet_epsilon <= 1:
            raise ValueError("Root noise mixture must be between zero and one")
        if not 0 < self.sample_fraction <= 1:
            raise ValueError("Sample fraction must be above zero and at most one")
        if self.mode != "multiplayer":
            raise ValueError("Learning updates all three policies in multiplayer mode")


class ReplayTraceCapture:
    """Record only actual transitions; full state is hashed once per episode."""

    def __init__(self, observer: Callable[[dict[str, Any]], None]):
        self.replay_observer = observer
        self._replay_roots: dict[int, dict[str, Any]] = {}
        self._replay_seeds: dict[int, int] = {}
        self._replay_contexts: set[str] = set()

    def remember_seed(self, env: Any, seed: int) -> None:
        self._replay_seeds[id(env)] = seed

    def before(self, env: Any, root: int) -> dict[str, Any] | None:
        """Start an inspection episode and remember only its past-event cursor."""
        if self.replay_observer is None:
            return None
        current = self._replay_roots.get(root)
        if current is None or current["env"] is not env:
            number = current["number"] + 1 if current else 0
            context = env.context()
            context_key = _fingerprint(context)
            if context_key not in self._replay_contexts:
                self.replay_observer({"type": "context", "context_sha256": context_key, "context": context})
                self._replay_contexts.add(context_key)
            serialized = env.serialize()  # Once per episode, never once per action.
            current = {"env": env, "number": number, "episode_id": f"{root}:{number}", "sequence": 0}
            self._replay_roots[root] = current
            self.replay_observer({"type": "episode_start", "root": root, "episode_id": current["episode_id"],
                "seed": self._replay_seeds.pop(id(env), None), "context_sha256": context_key,
                "initial_state_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
                "initial_planning_key": env.planning_key(), "initial_observation": env.observation()})
        raw = getattr(env, "raw", env)
        cursor = raw.history_size() if hasattr(raw, "history_size") else None
        return {"root": root, "episode_id": current["episode_id"], "sequence": current["sequence"],
                "history_cursor": cursor}

    def after(self, env: Any, replay: dict[str, Any] | None, event: dict[str, Any]) -> None:
        if replay is None:
            return
        cursor = replay.pop("history_cursor")
        raw = getattr(env, "raw", env)
        observed = raw.history_since(cursor) if cursor is not None else None
        self.replay_observer({"type": "transition", **replay, "event": event,
            "observed_events": observed,
            "dice_verification": "recorded_past_events" if observed is not None else "seed_and_planning_key",
            "terminal_returns": list(env.returns()) if env.is_terminal() else None})
        self._replay_roots[replay["root"]]["sequence"] += 1


class CampaignLearner:
    """Owns live models, replay, RNG, and an optional active CampaignAdapter.

    ``compatibility`` must contain scenario/rules/schema fingerprints. It may
    also contain curriculum, opponent or source versions, all checked exactly.
    Checkpoints are trusted local Torch files, not an untrusted import format.
    """

    def __init__(self, models: Mapping[str, nn.Module], model_config: Any,
                 config: LearningConfig | None = None, *, compatibility: Mapping[str, Any],
                 replay_observer: Callable[[dict[str, Any]], None] | None = None,
                 runtime_policy: Any = None):
        self.config = config or LearningConfig()
        self.model_config = copy.deepcopy(asdict(model_config))
        self.compatibility = json.loads(_canonical(dict(compatibility)))
        if any(not isinstance(self.compatibility.get(name), str) or not self.compatibility[name]
               for name in ("scenario", "rules", "schema")):
            raise ValueError("Scenario, rules and schema fingerprints are required")
        if set(models) != set(PLAYERS):
            raise ValueError("Learning requires all three actor policies")
        if self.model_config.get("value_scale") != self.config.value_scale:
            raise ValueError("Model and learner must use the same positive value scale")
        self.models = dict(models)
        if len({id(model) for model in self.models.values()}) != 3:
            raise ValueError("Actor policies must be separate model instances")
        if any(asdict(getattr(model, "config", None)) != self.model_config for model in self.models.values()):
            raise ValueError("Every actor model configuration must match the learner model configuration")
        from .device_runtime import runtime_policy_for_device
        self._mps_actor_count = sum(next(model.parameters()).device.type == "mps"
                                    for model in self.models.values())
        self._device_runtime = (runtime_policy if runtime_policy is not None else
                                runtime_policy_for_device("mps") if self._mps_actor_count else None)
        self.optimizers = {player: self._optimizer(self.models[player]) for player in PLAYERS}
        self.policy_random = random.Random(self.config.seed)
        self.search_random = random.Random(self.config.seed ^ 0x9E3779B97F4A7C15)
        self.replay_random = random.Random(self.config.seed ^ 0xD1B54A32D192ED03)
        self.environment_random = random.Random(self.config.seed ^ 0x94D049BB133111EB)
        self.env: Any = None
        self.parallel_envs: list[Any] = []
        self.parallel_pending: list[list[dict[str, Any]]] = []
        self.replay: list[dict[str, Any]] = []
        # Source JSON or immutable native buffers can be shared. Neither pool
        # contains learned tensors or changes the model/schema meaning.
        self._context_pool: dict[str, dict[str, Any]] = {}
        self._numeric_context_pool: dict[tuple[str, int], Any] = {}
        self.pending: list[dict[str, Any]] = []
        self.batch_records: list[dict[str, Any]] = []
        self.frozen_models: dict[str, nn.Module] | None = None
        self.frozen_versions: dict[str, str] | None = None
        self.batch_version: str | None = None
        self.generation = 0
        self.counters = dict(transitions=0, decisions=0, chance_events=0,
                             episodes=0, batches=0, updates=0)
        self.action_history: list[dict[str, Any]] = []
        self._episodes_terminal: bool | None = None
        # Inspection-only callbacks are never checkpointed or restored. Their
        # absence leaves collection unchanged and performs no replay conversion.
        self.set_replay_observer(replay_observer)

    def _optimizer(self, model: nn.Module) -> torch.optim.Optimizer:
        return torch.optim.Adam(model.parameters(), lr=self.config.learning_rate)

    def _new_env(self, factory: Callable[..., Any]) -> Any:
        """Seed-aware factories need no hidden external episode/seed counter.

        A zero-argument factory remains supported and must be stateless for
        exact continuation. The recommended factory accepts one seed argument.
        """
        seed = self.environment_random.getrandbits(63)
        try:
            signature = inspect.signature(factory)
            signature.bind(seed)
        except (TypeError, ValueError):
            env = factory()
            seed = None
        else:
            env = factory(seed)
        if self.replay_capture is not None and seed is not None:
            self.replay_capture.remember_seed(env, seed)
        return env

    def set_replay_observer(self, observer: Callable[[dict[str, Any]], None] | None) -> None:
        """Attach a new inspection segment without altering checkpoint state."""
        self.replay_capture = ReplayTraceCapture(observer) if observer is not None else None

    def _replay_before(self, env: Any, root: int) -> dict[str, Any] | None:
        return self.replay_capture.before(env, root) if self.replay_capture is not None else None

    def _replay_after(self, env: Any, replay: dict[str, Any] | None, event: dict[str, Any]) -> None:
        if self.replay_capture is not None:
            self.replay_capture.after(env, replay, event)

    def model_versions(self) -> dict[str, str]:
        return {player: f"{player}:generation-{self.generation}:{_model_digest(self.models[player])}"
                for player in PLAYERS}

    def _evaluator(self):
        from .neural import NeuralEvaluator
        if self.frozen_models is None or self.batch_version is None:
            raise ValueError("No frozen rollout batch is active")
        return NeuralEvaluator(self.frozen_models, version=self.batch_version,
                               runtime_policy=self._device_runtime)

    def begin_batch(self, env: Any = None) -> None:
        if self.frozen_models is not None:
            raise ValueError("Finish the current rollout batch before starting another")
        if env is not None:
            self.env = env
        if self.env is None:
            raise ValueError("A rollout needs an environment")
        self.parallel_envs, self.parallel_pending = [], []
        self._freeze_policies()

    def _freeze_policies(self) -> None:
        self.frozen_models = {player: copy.deepcopy(self.models[player]).eval() for player in PLAYERS}
        self.frozen_versions = self.model_versions()
        self.batch_version = _fingerprint({"models": self.frozen_versions, "mode": self.config.mode,
                                           "model_config": self.model_config,
                                           "compatibility": self.compatibility})
        self.pending, self.batch_records = [], []

    def begin_batch_many(self, envs: Any = None) -> None:
        roots = list(envs) if envs is not None else self.parallel_envs.copy()
        if not roots:
            raise ValueError("Parallel collection needs at least one environment")
        contexts = {_fingerprint(env.context()) for env in roots}
        if len(contexts) != 1 or len({id(env) for env in roots}) != len(roots):
            raise ValueError("Parallel roots must be independent environments with the same static context")
        self.begin_batch(roots[0])
        self.parallel_envs = roots
        self.parallel_pending = [[] for _ in roots]

    def _label_pending(self, values: Any, source: str) -> None:
        self._label_samples(self.pending, values, source)
        self.pending = []

    def _label_samples(self, samples: list[dict[str, Any]], values: Any, source: str) -> None:
        target = list(vector(values))
        if source not in {"terminal", "bootstrap"}:
            raise ValueError("Targets must identify their terminal or bootstrap source")
        for sample in samples:
            self.batch_records.append({**sample, "values": target.copy(), "target_source": source,
                                       "target_schema": TARGET_SCHEMA})

    def _search_config(self) -> MctsConfig:
        return MctsConfig(
            simulations=self.config.simulations, max_depth=self.config.max_depth,
            c_puct=self.config.c_puct, seed=self.search_random.getrandbits(64),
            rules_version=self.compatibility["rules"], mode=self.config.mode,
            root_dirichlet_alpha=self.config.root_dirichlet_alpha,
            root_dirichlet_epsilon=self.config.root_dirichlet_epsilon)

    def _numeric_models(self) -> bool:
        from .neural import CampaignPolicyValueNet
        return all(isinstance(model, CampaignPolicyValueNet) for model in self.models.values())

    def _apply_search_result(self, env: Any, result: Any, pending: list[dict[str, Any]],
                             replay: dict[str, Any] | None = None) -> dict[str, Any]:
        event = _decide(env, result, pending, config=self.config, rng=self.policy_random,
                        numeric=self._numeric_models(), token_buckets=self.model_config["token_buckets"],
                        batch_version=self.batch_version, numeric_pool=self._numeric_context_pool,
                        context_pool=self._context_pool, replay=replay)
        self.counters["decisions"] += 1
        return event

    def collect(self, max_transitions: int, env_factory: Callable[..., Any] | None = None) -> dict[str, Any]:
        """Advance at most this many real action/chance transitions, without updates."""
        if type(max_transitions) is not int or max_transitions < 0:
            raise ValueError("Collection budget must be a nonnegative integer")
        if self.frozen_models is None:
            self.begin_batch()
        if self.parallel_envs:
            raise ValueError("Use collect_many for a parallel rollout batch")
        evaluator = self._evaluator()
        events = []
        for _ in range(max_transitions):
            if self.env.is_terminal():
                if self.pending:
                    self._label_pending(self.env.returns(), "terminal")
                    self.counters["episodes"] += 1
                if env_factory is None:
                    break
                replacement = self._new_env(env_factory)
                if _fingerprint(replacement.context()) != _fingerprint(self.env.context()):
                    raise ValueError("A rollout batch cannot mix scenario/rules contexts")
                self.env = replacement
                if self.env.is_terminal():
                    raise ValueError("Environment factory returned a terminal starting position")
            before = self.env.planning_key()
            replay = self._replay_before(self.env, 0)
            if self.env.decision_kind() == "chance":
                self.env.resolve_chance()
                self.counters["chance_events"] += 1
                event = {"kind": "chance", "owner": None, "action": None}
            else:
                owner = self.env.current_decision_player()
                if owner not in PLAYERS:
                    raise ValueError("A policy choice must belong to one of the three actors")
                result = VectorMCTS(evaluator, self._search_config()).search(
                    self.env, add_root_noise=self.config.root_noise, reuse_root=False)
                event = self._apply_search_result(self.env, result, self.pending, replay)
            self.counters["transitions"] += 1
            event.update(before=before, after=self.env.planning_key(), terminal=self.env.is_terminal())
            events.append(event)
            self.action_history.append(event)
            self._replay_after(self.env, replay, event)
            if self.env.is_terminal():
                self._label_pending(self.env.returns(), "terminal")
                self.counters["episodes"] += 1
        return {"transitions": len(events), "events": events, "terminal": self.env.is_terminal(),
                "pending_samples": len(self.pending), "batch_samples": len(self.batch_records)}

    def collect_many(self, transitions_per_env: int, env_factory: Callable[..., Any] | None = None) -> dict[str, Any]:
        """Batch inference across actual independent rollout roots.

        Every root gets at most ``transitions_per_env`` real transitions. Chance
        consumes a real transition and is resolved solely by that root's rules
        RNG. Checkpoint boundaries are between complete search waves.
        """
        from .batching import BatchStats, search_many
        if type(transitions_per_env) is not int or transitions_per_env < 0:
            raise ValueError("Per-environment budget must be a nonnegative integer")
        if self.frozen_models is None:
            self.begin_batch_many()
        if not self.parallel_envs:
            raise ValueError("Begin a parallel batch before collect_many")
        evaluator = self._evaluator()
        counts = [0] * len(self.parallel_envs)
        events, metrics = [], []

        def record(index, before, event, replay):
            env = self.parallel_envs[index]
            self.counters["transitions"] += 1
            counts[index] += 1
            event.update(root=index, before=before, after=env.planning_key(), terminal=env.is_terminal())
            events.append(event)
            self.action_history.append(event)
            self._replay_after(env, replay, event)
            if env.is_terminal():
                self._label_samples(self.parallel_pending[index], env.returns(), "terminal")
                self.parallel_pending[index] = []
                self.counters["episodes"] += 1

        for _ in range(transitions_per_env):
            decision_indices = []
            decision_replays = {}
            for index, env in enumerate(self.parallel_envs):
                if env.is_terminal():
                    if env_factory is None:
                        continue
                    replacement = self._new_env(env_factory)
                    if replacement.is_terminal() or _fingerprint(replacement.context()) != _fingerprint(env.context()):
                        raise ValueError("Parallel factory must return a nonterminal compatible environment")
                    env = self.parallel_envs[index] = replacement
                    if index == 0:
                        self.env = env
                replay = self._replay_before(env, index)
                if env.decision_kind() == "chance":
                    before = env.planning_key()
                    env.resolve_chance()
                    self.counters["chance_events"] += 1
                    record(index, before, {"kind": "chance", "owner": None, "action": None}, replay)
                else:
                    if env.current_decision_player() not in PLAYERS:
                        raise ValueError("Parallel choice lacks an entitled actor")
                    decision_indices.append(index)
                    decision_replays[index] = replay
            if decision_indices:
                stats = BatchStats()
                results = search_many([self.parallel_envs[index] for index in decision_indices], evaluator,
                                      configs=[self._search_config() for _ in decision_indices],
                                      add_root_noise=self.config.root_noise, stats=stats)
                metrics.append(asdict(stats))
                for index, result in zip(decision_indices, results, strict=True):
                    env = self.parallel_envs[index]
                    before = env.planning_key()
                    replay = decision_replays[index]
                    event = self._apply_search_result(env, result, self.parallel_pending[index], replay)
                    record(index, before, event, replay)
        return {"transitions": sum(counts), "transitions_per_env": counts, "events": events,
                "terminal": [env.is_terminal() for env in self.parallel_envs],
                "pending_samples": [len(rows) for rows in self.parallel_pending],
                "batch_samples": len(self.batch_records), "inference": metrics,
                "inference_batch_sizes": [size for stat in metrics for size in stat["batch_sizes"]]}

    def _sample(self, actions: Any, policy: list[float]) -> int:
        return _sample_index(actions, policy, self.policy_random)

    def begin_episode_batch(self) -> None:
        """Freeze all three policies for complete episodes played by worker processes.

        ``env`` stays a reference position whose static context checkpoints
        verify; workers play the batch's games from their own seeds.
        """
        if self.frozen_models is not None:
            raise ValueError("Finish the current rollout batch before starting another")
        if self.env is None:
            raise ValueError("Episode batches need a reference environment for context checks")
        self.parallel_envs, self.parallel_pending = [], []
        self._freeze_policies()
        self._episodes_terminal = None

    def abandon_batch(self) -> None:
        """Drop an unfinished frozen batch; nothing it collected is kept."""
        self.frozen_models, self.frozen_versions, self.batch_version = None, None, None
        self.pending, self.batch_records = [], []
        self.parallel_envs, self.parallel_pending = [], []
        self._episodes_terminal = None

    def collect_episodes(self, workers: Any, count: int, max_transitions: int, *,
                         stop: Callable[[], bool] = lambda: False) -> dict[str, Any] | None:
        """Play this many complete episodes in worker processes and keep their samples.

        Each episode draws only from its own random streams, so results do not
        depend on the number of workers. Nothing is recorded unless every episode
        finishes; a stop request or the transition guard abandons the batch and
        rewinds the environment-seed stream, so the batch replays exactly later.
        Returns None when stopped.
        """
        from .features import NUMERIC_SCHEMA
        if type(count) is not int or count <= 0 or type(max_transitions) is not int or max_transitions <= 0:
            raise ValueError("Episode count and transition guard must be positive integers")
        if self.frozen_models is None:
            self.begin_episode_batch()
        if self.parallel_envs or self.pending:
            raise ValueError("An in-process rollout batch is active")
        before = self.environment_random.getstate()
        seeds = [self.environment_random.getrandbits(63) for _ in range(count)]
        weights = {player: {name: tensor.detach().cpu() for name, tensor in model.state_dict().items()}
                   for player, model in self.frozen_models.items()}
        results = workers.play(list(enumerate(seeds)), weights=weights, batch_version=self.batch_version,
                               max_transitions=max_transitions, stop=stop)
        failed = [result for result in results or [] if "failure" in result]
        if len(failed) * 2 > count:
            raise RuntimeError(f"Most of a batch's games failed, first with {failed[0]['failure']}")
        results = None if results is None else [result for result in results if "failure" not in result]
        if results is None or not all(result["terminal"] for result in results):
            self.environment_random.setstate(before)
            self.abandon_batch()
            return None if results is None else {"seeds": seeds, "exhausted": True, "results": results}
        for result in results:
            for record in result["records"]:
                if record["input"]["schema"] == NUMERIC_SCHEMA:
                    _intern_numeric_context(record["input"], self._numeric_context_pool)
                else:
                    record["input"]["context"] = _intern_context(record["input"]["context"], self._context_pool)
            self.batch_records.extend(result["records"])
            for name in ("transitions", "decisions", "chance_events"):
                self.counters[name] += result["counts"][name]
            self.counters["episodes"] += 1
            self.action_history.extend({**event, "root": result["root"]} for event in result["events"])
        self._episodes_terminal = True
        return {"seeds": seeds, "exhausted": False, "results": results, "failed": failed}

    def finish_batch(self) -> dict[str, Any]:
        if self.frozen_models is None:
            raise ValueError("No rollout batch is active")
        if self.parallel_envs:
            for index, env in enumerate(self.parallel_envs):
                samples = self.parallel_pending[index]
                if samples:
                    actions = list(env.legal_actions()) if env.decision_kind() not in {"chance", "terminal"} else []
                    values = env.returns() if env.is_terminal() else self._evaluator().evaluate(env, actions).values
                    self._label_samples(samples, values, "terminal" if env.is_terminal() else "bootstrap")
                    self.parallel_pending[index] = []
        elif self.pending:
            if self.env.is_terminal():
                self._label_pending(self.env.returns(), "terminal")
            else:
                # No zero return, fake terminal, clipping, shaping or discount.
                actions = list(self.env.legal_actions()) if self.env.decision_kind() != "chance" else []
                self._label_pending(self._evaluator().evaluate(self.env, actions).values, "bootstrap")
        records = self.batch_records
        self.replay = (self.replay + records)[-self.config.replay_capacity:]
        result = {"samples": len(records), "terminal_samples": sum(r["target_source"] == "terminal" for r in records),
                  "bootstrap_samples": sum(r["target_source"] == "bootstrap" for r in records),
                  "terminal": (self._episodes_terminal if self._episodes_terminal is not None
                               else all(env.is_terminal() for env in self.parallel_envs) if self.parallel_envs
                               else self.env.is_terminal()),
                  "rollout_version": self.batch_version}
        self.pending, self.batch_records = [], []
        self.frozen_models, self.frozen_versions, self.batch_version = None, None, None
        self._episodes_terminal = None
        self.counters["batches"] += 1
        return result

    def update(self) -> dict[str, Any]:
        """Fit all value heads; policy targets only train their actual owner."""
        if self.frozen_models is not None:
            raise ValueError("Cannot update policies while a rollout batch is frozen")
        if not self.replay:
            return {"updated": False, "samples": 0, "losses": {}}
        losses: dict[str, list[dict[str, float]]] = {player: [] for player in PLAYERS}
        for _ in range(self.config.epochs):
            samples = self.replay_random.sample(self.replay, min(self.config.batch_size, len(self.replay)))
            for player in PLAYERS:
                model, optimizer = self.models[player], self.optimizers[player]
                model.train()
                optimizer.zero_grad(set_to_none=True)
                # Every position trains the value head, while only its owner
                # has a policy target. State values do not read action graphs,
                # so avoid encoding other actors' unused policy menus. Keep
                # replay and the complete observation/context unchanged.
                inputs = [sample["input"] if sample["owner"] == player
                          else _value_only_input(sample["input"]) for sample in samples]
                logits, predicted = model.forward_batch(inputs)
                target = torch.as_tensor([sample["values"] for sample in samples], dtype=predicted.dtype,
                                         device=predicted.device) / self.config.value_scale
                value_loss = torch.mean((predicted - target) ** 2)
                terms = []
                for index, sample in enumerate(samples):
                    if sample["owner"] == player:
                        desired = torch.as_tensor(sample["policy"], dtype=logits[index].dtype,
                                                  device=logits[index].device)
                        terms.append(-(desired * torch.log_softmax(logits[index], dim=0)).sum())
                policy_loss = torch.stack(terms).mean() if terms else value_loss.new_zeros(())
                loss = value_loss + policy_loss
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite learning loss")
                loss.backward()
                losses[player].append({"policy": float(policy_loss.detach()), "value": float(value_loss.detach()),
                                       "total": float(loss.detach()), "policy_samples": len(terms)})
            # No actor changes until gradients for all three have been formed.
            for player in PLAYERS:
                self.optimizers[player].step()
                self.models[player].eval()
            if self._device_runtime is not None and self._mps_actor_count:
                # All actor gradients and updates have completed; no pending
                # autograd work is discarded by compilation-cache housekeeping.
                self._device_runtime.completed(self._mps_actor_count)
        self.generation += 1
        self.counters["updates"] += 1
        return {"updated": True, "samples": min(self.config.batch_size, len(self.replay)), "losses": losses,
                "generation": self.generation, "model_versions": self.model_versions()}

    def release_device_memory(self) -> None:
        """Between phases: game processes need the memory the GPU keeps cached."""
        if self._device_runtime is not None:
            self._device_runtime.reset()

    def run_batch(self, env_factory: Callable[..., Any], max_transitions: int) -> dict[str, Any]:
        if self.env is None:
            self.env = self._new_env(env_factory)
        if self.frozen_models is None:
            self.begin_batch()
        collection = self.collect(max_transitions, env_factory)
        rollout = self.finish_batch()
        return {"collection": collection, "rollout": rollout, "update": self.update(),
                "counters": self.counters.copy()}

    def run_batch_many(self, env_factory: Callable[..., Any], transitions_per_env: int,
                       parallel_envs: int = 2) -> dict[str, Any]:
        if type(parallel_envs) is not int or parallel_envs <= 0:
            raise ValueError("Parallel environment count must be positive")
        if self.parallel_envs and len(self.parallel_envs) != parallel_envs:
            raise ValueError("Existing parallel rollout count differs; use an explicit new batch")
        if self.frozen_models is None:
            roots = self.parallel_envs or [self._new_env(env_factory) for _ in range(parallel_envs)]
            self.begin_batch_many(roots)
        elif not self.parallel_envs:
            raise ValueError("Cannot resume a scalar batch as a parallel rollout")
        collection = self.collect_many(transitions_per_env, env_factory)
        rollout = self.finish_batch()
        return {"collection": collection, "rollout": rollout, "update": self.update(),
                "counters": self.counters.copy()}

    def _metadata(self) -> dict[str, Any]:
        return {"config": asdict(self.config), "model_config": self.model_config,
                "compatibility": self.compatibility, "players": list(PLAYERS), "target_schema": TARGET_SCHEMA,
                "software": {"python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__,
                             "torch_threads": torch.get_num_threads(),
                             "devices": {p: str(next(self.models[p].parameters()).device) for p in PLAYERS}}}

    def checkpoint(self) -> dict[str, Any]:
        """Snapshot also works halfway through a frozen rollout batch."""
        return copy.deepcopy({
            "schema": CHECKPOINT_SCHEMA, "metadata": self._metadata(),
            "models": {p: self.models[p].state_dict() for p in PLAYERS}, "model_versions": self.model_versions(),
            "optimizers": {p: self.optimizers[p].state_dict() for p in PLAYERS},
            "frozen_models": {p: self.frozen_models[p].state_dict() for p in PLAYERS} if self.frozen_models else None,
            "frozen_versions": self.frozen_versions, "batch_version": self.batch_version,
            "replay": self.replay, "pending": self.pending, "batch_records": self.batch_records,
            "generation": self.generation, "counters": self.counters, "action_history": self.action_history,
            "env": self.env.serialize() if self.env is not None else None,
            "env_context": _fingerprint(self.env.context()) if self.env is not None else None,
            "parallel_envs": [{"state": env.serialize(), "context": _fingerprint(env.context())}
                              for env in self.parallel_envs],
            "parallel_pending": self.parallel_pending,
            "rng": {"python": random.getstate(), "numpy": np.random.get_state(), "torch": torch.get_rng_state(),
                    "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
                    "mps": torch.mps.get_rng_state() if any(
                        next(model.parameters()).device.type == "mps" for model in self.models.values()) else None,
                    "policy": self.policy_random.getstate(), "search": self.search_random.getstate(),
                    "replay": self.replay_random.getstate(), "environment": self.environment_random.getstate()},
        })

    @staticmethod
    def _validate_sample(sample: Any, *, labeled: bool, buckets: int | None = None) -> None:
        from .features import SCHEMA as INPUT_SCHEMA, NUMERIC_SCHEMA, validate_numeric_input
        required = {"input", "owner", "policy", "rollout_version"}
        if labeled:
            required |= {"values", "target_source", "target_schema"}
        if not isinstance(sample, dict) or set(sample) != required or sample["owner"] not in PLAYERS:
            raise ValueError("Invalid replay sample")
        if not isinstance(sample["rollout_version"], str) or not sample["rollout_version"]:
            raise ValueError("Replay sample lacks policy version")
        features = sample["input"]
        if isinstance(features, dict) and features.get("schema") == NUMERIC_SCHEMA:
            action_count = validate_numeric_input(features, buckets=buckets)
            if features["owner"] != sample["owner"]:
                raise ValueError("Replay owner differs from actual numerical input owner")
        elif (not isinstance(features, dict) or set(features) != {"schema", "observation", "context", "actions"}
                or features["schema"] != INPUT_SCHEMA or not isinstance(features["observation"], dict)
                or not isinstance(features["context"], dict)):
            raise ValueError("Unsupported replay input schema")
        else:
            if features["observation"].get("current_decision_player") != sample["owner"]:
                raise ValueError("Replay owner differs from actual observation owner")
            # Validate changing source JSON without serializing the shared
            # registry once per trajectory row during checkpoint restoration.
            _canonical({key: item for key, item in features.items() if key != "context"})
            if isinstance(features["context"], FrozenDict):
                features["context"].canonical_json
            elif not isinstance(features["context"], _ReadOnlyDict):
                _canonical(features["context"])
            if not isinstance(features.get("actions"), list):
                raise ValueError("Replay sample must contain legal action features")
            action_count = len(features["actions"])
        if not action_count:
            raise ValueError("Replay sample must contain legal action features")
        normalized = probabilities(sample["policy"], action_count)
        if any(abs(a-b) > 1e-9 for a,b in zip(normalized, sample["policy"])):
            raise ValueError("Replay policy must already be normalized")
        if labeled:
            vector(sample["values"])
            if sample["target_source"] not in {"terminal", "bootstrap"} or sample["target_schema"] != TARGET_SCHEMA:
                raise ValueError("Invalid replay value target provenance")

    def restore(self, payload: Mapping[str, Any], *, env_template: Any = None) -> None:
        """Validate staged replacements before changing models, environment or RNG."""
        incoming = dict(payload)
        context_pool: dict[str, dict[str, Any]] = {}
        memo = {}
        for context in _checkpoint_contexts(incoming):
            if id(context) not in memo:
                memo[id(context)] = _intern_context(context, context_pool)
        value = copy.deepcopy(incoming, memo)
        expected = {"schema", "metadata", "models", "model_versions", "optimizers", "frozen_models",
                    "frozen_versions", "batch_version", "replay", "pending", "batch_records", "generation",
                    "counters", "action_history", "env", "env_context", "rng", "parallel_envs", "parallel_pending"}
        if set(value) != expected or value["schema"] != CHECKPOINT_SCHEMA or value["metadata"] != self._metadata():
            raise ValueError("Incompatible campaign learning checkpoint metadata")
        if type(value["generation"]) is not int or value["generation"] < 0:
            raise ValueError("Invalid model generation")
        if set(value["counters"]) != set(self.counters) or any(type(n) is not int or n < 0 for n in value["counters"].values()):
            raise ValueError("Invalid learning counters")
        for name in ("replay", "pending", "batch_records"):
            if not isinstance(value[name], list):
                raise ValueError("Invalid replay container")
            for sample in value[name]:
                self._validate_sample(sample, labeled=name != "pending", buckets=self.model_config["token_buckets"])
        if len(value["replay"]) > self.config.replay_capacity:
            raise ValueError("Replay exceeds configured capacity")
        if value["counters"]["updates"] != value["generation"]:
            raise ValueError("Update counter and model generation disagree")
        models, optimizers = {}, {}
        if (set(value["models"]) != set(PLAYERS) or set(value["optimizers"]) != set(PLAYERS)
                or set(value["model_versions"]) != set(PLAYERS)):
            raise ValueError("Checkpoint must contain all actor states")
        for player in PLAYERS:
            models[player] = copy.deepcopy(self.models[player])
            models[player].load_state_dict(value["models"][player], strict=True)
            if value["model_versions"].get(player) != f"{player}:generation-{value['generation']}:{_model_digest(models[player])}":
                raise ValueError("Model version does not match weights")
            for tensor in models[player].state_dict().values():
                if tensor.is_floating_point() and not torch.isfinite(tensor).all():
                    raise ValueError("Checkpoint contains nonfinite model weights")
            optimizers[player] = self._optimizer(models[player])
            expected_groups = [{key: item for key, item in group.items() if key != "params"}
                               for group in optimizers[player].param_groups]
            optimizers[player].load_state_dict(value["optimizers"][player])
            for group, expected_group in zip(optimizers[player].param_groups, expected_groups, strict=True):
                if {key: item for key, item in group.items() if key != "params"} != expected_group:
                    raise ValueError("Optimizer hyperparameters differ from configuration")
                for parameter in group["params"]:
                    state = optimizers[player].state.get(parameter, {})
                    for key, item in state.items():
                        if isinstance(item, torch.Tensor):
                            if not torch.isfinite(item).all() or (key != "step" and item.shape != parameter.shape):
                                raise ValueError("Invalid optimizer tensor state")
            models[player].eval()
        frozen = None
        if value["frozen_models"] is not None:
            if set(value["frozen_models"]) != set(PLAYERS) or set(value["frozen_versions"] or {}) != set(PLAYERS):
                raise ValueError("Frozen rollout must contain all actor policies")
            frozen = {p: copy.deepcopy(models[p]).eval() for p in PLAYERS}
            for player in PLAYERS:
                frozen[player].load_state_dict(value["frozen_models"][player], strict=True)
                if any(tensor.is_floating_point() and not torch.isfinite(tensor).all()
                       for tensor in frozen[player].state_dict().values()):
                    raise ValueError("Nonfinite frozen policy weights")
                expected_version = f"{player}:generation-{value['generation']}:{_model_digest(frozen[player])}"
                if value["frozen_versions"][player] != expected_version:
                    raise ValueError("Frozen policy version does not match weights")
            expected_version = _fingerprint({"models": value["frozen_versions"], "mode": self.config.mode,
                                             "model_config": self.model_config, "compatibility": self.compatibility})
            if value["batch_version"] != expected_version:
                raise ValueError("Rollout batch identity is incompatible")
            if any(s["rollout_version"] != expected_version for name in ("pending", "batch_records") for s in value[name]):
                raise ValueError("Pending rollout contains mixed policy generations")
        elif value["batch_version"] is not None or value["frozen_versions"] is not None or value["pending"] or value["batch_records"]:
            raise ValueError("Pending rollout lacks frozen policies")
        env = None
        if value["env"] is not None:
            template = env_template if env_template is not None else self.env
            if template is None or _fingerprint(template.context()) != value["env_context"]:
                raise ValueError("Checkpoint requires a compatible environment template")
            env = template.clone()
            env.restore(value["env"])
            if _fingerprint(env.context()) != value["env_context"]:
                raise ValueError("Restored environment static context differs")
        elif value["env_context"] is not None or frozen is not None:
            raise ValueError("Active rollout environment is missing")
        parallel = []
        if not isinstance(value["parallel_envs"], list) or not isinstance(value["parallel_pending"], list):
            raise ValueError("Invalid parallel rollout state")
        if len(value["parallel_envs"]) != len(value["parallel_pending"]):
            raise ValueError("Parallel pending samples do not match environment count")
        for item, samples in zip(value["parallel_envs"], value["parallel_pending"], strict=True):
            if env is None or not isinstance(item, dict) or set(item) != {"state", "context"}:
                raise ValueError("Invalid parallel environment checkpoint")
            if item["context"] != value["env_context"] or not isinstance(samples, list):
                raise ValueError("Parallel rollout contexts differ")
            replacement = env.clone()
            replacement.restore(item["state"])
            if _fingerprint(replacement.context()) != item["context"]:
                raise ValueError("Parallel environment context differs after restore")
            for sample in samples:
                self._validate_sample(sample, labeled=False, buckets=self.model_config["token_buckets"])
                if frozen is None or sample["rollout_version"] != value["batch_version"]:
                    raise ValueError("Parallel pending sample lacks the frozen batch policy")
            parallel.append(replacement)
        if parallel:
            if value["pending"] or parallel[0].serialize() != env.serialize():
                raise ValueError("Parallel primary environment state disagrees")
            env = parallel[0]
        samples = [sample for name in ("replay", "pending", "batch_records") for sample in value[name]]
        samples.extend(sample for rows in value["parallel_pending"] for sample in rows)
        if samples and env is None:
            raise ValueError("Replay requires an environment with a verified static context")
        context_keys = {id(context): key for key, context in context_pool.items()}
        numeric_context_pool: dict[tuple[str, int], Any] = {}
        checked_numeric_contexts: set[int] = set()
        expected_numeric = None
        from .features import NUMERIC_SCHEMA, make_numeric_input
        for sample in samples:
            features = sample["input"]
            if features["schema"] == NUMERIC_SCHEMA:
                if features["context_key"] != value["env_context"]:
                    raise ValueError("Numerical replay context differs from campaign compatibility context")
                context = features["packed_graph"]["context"]
                if id(context) not in checked_numeric_contexts:
                    if expected_numeric is None:
                        expected_numeric = make_numeric_input(env, (), self.model_config["token_buckets"])
                        if expected_numeric["schema"] != NUMERIC_SCHEMA:
                            raise ValueError("Numerical replay requires a compatible numerical environment template")
                    if (expected_numeric["context_key"] != value["env_context"] or
                            not _same_numeric_graph(context, expected_numeric["packed_graph"]["context"])):
                        raise ValueError("Numerical replay graph differs from campaign compatibility context")
                    checked_numeric_contexts.add(id(context))
                _intern_numeric_context(features, numeric_context_pool)
            elif context_keys[id(features["context"])] != value["env_context"]:
                raise ValueError("Replay sample context differs from campaign compatibility context")
        rng = value["rng"]
        if set(rng) != {"python", "numpy", "torch", "cuda", "mps", "policy", "search", "replay", "environment"}:
            raise ValueError("Incomplete random-generator checkpoint")
        random.Random().setstate(rng["python"])
        np.random.RandomState().set_state(rng["numpy"])
        torch.Generator().set_state(rng["torch"])
        local_rngs = {}
        for name in ("policy", "search", "replay", "environment"):
            local_rngs[name] = random.Random()
            local_rngs[name].setstate(rng[name])
        if len(rng["cuda"]) != torch.cuda.device_count():
            raise ValueError("CUDA random-generator devices differ")
        for index, state in enumerate(rng["cuda"]):
            torch.Generator(device=f"cuda:{index}").set_state(state)
        needs_mps = any(next(model.parameters()).device.type == "mps" for model in models.values())
        if needs_mps != (rng["mps"] is not None):
            raise ValueError("MPS random-generator devices differ")
        if needs_mps:
            expected_mps = torch.mps.get_rng_state()
            if rng["mps"].dtype != expected_mps.dtype or rng["mps"].shape != expected_mps.shape:
                raise ValueError("Invalid MPS random-generator state")
        # All parsing, compatibility and object loading succeeded. Commit once.
        if self._device_runtime is not None:
            self._device_runtime.reset()
        self.models, self.optimizers, self.env = models, optimizers, env
        self._context_pool = context_pool
        self._numeric_context_pool = numeric_context_pool
        self.parallel_envs, self.parallel_pending = parallel, value["parallel_pending"]
        self.frozen_models, self.frozen_versions, self.batch_version = frozen, value["frozen_versions"], value["batch_version"]
        self.replay, self.pending, self.batch_records = value["replay"], value["pending"], value["batch_records"]
        self.generation, self.counters, self.action_history = value["generation"], value["counters"], value["action_history"]
        self.policy_random, self.search_random, self.replay_random = local_rngs["policy"], local_rngs["search"], local_rngs["replay"]
        self.environment_random = local_rngs["environment"]
        random.setstate(rng["python"])
        np.random.set_state(rng["numpy"])
        torch.set_rng_state(rng["torch"])
        if rng["cuda"]:
            torch.cuda.set_rng_state_all(rng["cuda"])
        if needs_mps:
            torch.mps.set_rng_state(rng["mps"])

    def save_checkpoint(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        os.close(handle)
        try:
            torch.save(self.checkpoint(), temporary, pickle_protocol=5)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def load_checkpoint(self, path: str | Path, *, env_template: Any = None) -> None:
        # This format contains optimizer/RNG Python objects from our own runner.
        self.restore(torch.load(path, map_location="cpu", weights_only=False), env_template=env_template)
