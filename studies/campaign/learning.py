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

CHECKPOINT_SCHEMA = "campaign-learning-checkpoint-v1"
TARGET_SCHEMA = "campaign-raw-vector-target-v1"


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
    if isinstance(value, dict):
        return _ReadOnlyDict({key: _read_only_snapshot(item) for key, item in value.items()})
    if isinstance(value, list):
        return _ReadOnlyList(_read_only_snapshot(item) for item in value)
    return value


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _intern_context(context: dict[str, Any], pool: dict[str, dict[str, Any]]) -> dict[str, Any]:
    key = _fingerprint(context)  # Validates every static field before retaining it.
    if key not in pool:
        pool[key] = _read_only_snapshot(context)
    return pool[key]


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
        if self.mode != "multiplayer":
            raise ValueError("Learning updates all three policies in multiplayer mode")


class CampaignLearner:
    """Owns live models, replay, RNG, and an optional active CampaignAdapter.

    ``compatibility`` must contain scenario/rules/schema fingerprints. It may
    also contain curriculum, opponent or source versions, all checked exactly.
    Checkpoints are trusted local Torch files, not an untrusted import format.
    """

    def __init__(self, models: Mapping[str, nn.Module], model_config: Any,
                 config: LearningConfig | None = None, *, compatibility: Mapping[str, Any]):
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
        self.optimizers = {player: self._optimizer(self.models[player]) for player in PLAYERS}
        self.policy_random = random.Random(self.config.seed)
        self.search_random = random.Random(self.config.seed ^ 0x9E3779B97F4A7C15)
        self.replay_random = random.Random(self.config.seed ^ 0xD1B54A32D192ED03)
        self.environment_random = random.Random(self.config.seed ^ 0x94D049BB133111EB)
        self.env: Any = None
        self.parallel_envs: list[Any] = []
        self.parallel_pending: list[list[dict[str, Any]]] = []
        self.replay: list[dict[str, Any]] = []
        # Only immutable source JSON is shared; learned tensors are never cached.
        self._context_pool: dict[str, dict[str, Any]] = {}
        self.pending: list[dict[str, Any]] = []
        self.batch_records: list[dict[str, Any]] = []
        self.frozen_models: dict[str, nn.Module] | None = None
        self.frozen_versions: dict[str, str] | None = None
        self.batch_version: str | None = None
        self.generation = 0
        self.counters = dict(transitions=0, decisions=0, chance_events=0,
                             episodes=0, batches=0, updates=0)
        self.action_history: list[dict[str, Any]] = []

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
            return factory()
        return factory(seed)

    def model_versions(self) -> dict[str, str]:
        return {player: f"{player}:generation-{self.generation}:{_model_digest(self.models[player])}"
                for player in PLAYERS}

    def _evaluator(self):
        from .neural import NeuralEvaluator
        if self.frozen_models is None or self.batch_version is None:
            raise ValueError("No frozen rollout batch is active")
        return NeuralEvaluator(self.frozen_models, version=self.batch_version)

    def begin_batch(self, env: Any = None) -> None:
        if self.frozen_models is not None:
            raise ValueError("Finish the current rollout batch before starting another")
        if env is not None:
            self.env = env
        if self.env is None:
            raise ValueError("A rollout needs an environment")
        self.parallel_envs, self.parallel_pending = [], []
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

    def _apply_search_result(self, env: Any, result: Any, pending: list[dict[str, Any]]) -> dict[str, Any]:
        from .neural import make_input
        owner = env.current_decision_player()
        if owner not in PLAYERS:
            raise ValueError("A policy choice must belong to one of the three actors")
        logs = [math.log(p) / self.config.temperature if p > 0 else -math.inf for p in result.policy]
        maximum = max(logs)
        policy = probabilities([math.exp(value - maximum) for value in logs], len(logs))
        index = self._sample(result.actions, policy)
        features = make_input(env, result.actions)  # Already detached and JSON-validated.
        features["context"] = _intern_context(features["context"], self._context_pool)
        pending.append({"input": features,
                        "owner": owner, "policy": policy, "rollout_version": self.batch_version})
        action = result.actions[index]
        selected = features["actions"][index]
        raw = selected.get("action")
        raw = raw if isinstance(raw, dict) else selected
        event = {"kind": env.decision_kind(), "owner": owner, "action": action_key(action),
                 "action_kind": raw.get("kind", "unknown"),
                 "action_parameters": copy.deepcopy(raw.get("parameters", {}))}
        env.apply_action(action)
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
                event = self._apply_search_result(self.env, result, self.pending)
            self.counters["transitions"] += 1
            event.update(before=before, after=self.env.planning_key(), terminal=self.env.is_terminal())
            events.append(event)
            self.action_history.append(event)
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

        def record(index, before, event):
            env = self.parallel_envs[index]
            self.counters["transitions"] += 1
            counts[index] += 1
            event.update(root=index, before=before, after=env.planning_key(), terminal=env.is_terminal())
            events.append(event)
            self.action_history.append(event)
            if env.is_terminal():
                self._label_samples(self.parallel_pending[index], env.returns(), "terminal")
                self.parallel_pending[index] = []
                self.counters["episodes"] += 1

        for _ in range(transitions_per_env):
            decision_indices = []
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
                if env.decision_kind() == "chance":
                    before = env.planning_key()
                    env.resolve_chance()
                    self.counters["chance_events"] += 1
                    record(index, before, {"kind": "chance", "owner": None, "action": None})
                else:
                    if env.current_decision_player() not in PLAYERS:
                        raise ValueError("Parallel choice lacks an entitled actor")
                    decision_indices.append(index)
            if decision_indices:
                stats = BatchStats()
                results = search_many([self.parallel_envs[index] for index in decision_indices], evaluator,
                                      configs=[self._search_config() for _ in decision_indices],
                                      add_root_noise=self.config.root_noise, stats=stats)
                metrics.append(asdict(stats))
                for index, result in zip(decision_indices, results, strict=True):
                    env = self.parallel_envs[index]
                    before = env.planning_key()
                    event = self._apply_search_result(env, result, self.parallel_pending[index])
                    record(index, before, event)
        return {"transitions": sum(counts), "transitions_per_env": counts, "events": events,
                "terminal": [env.is_terminal() for env in self.parallel_envs],
                "pending_samples": [len(rows) for rows in self.parallel_pending],
                "batch_samples": len(self.batch_records), "inference": metrics,
                "inference_batch_sizes": [size for stat in metrics for size in stat["batch_sizes"]]}

    def _sample(self, actions: Any, policy: list[float]) -> int:
        order = sorted(range(len(actions)), key=lambda index: action_key(actions[index]))
        threshold = self.policy_random.random()
        for index in order:
            threshold -= policy[index]
            if threshold < 0:
                return index
        return order[-1]

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
                  "terminal": all(env.is_terminal() for env in self.parallel_envs) if self.parallel_envs else self.env.is_terminal(),
                  "rollout_version": self.batch_version}
        self.pending, self.batch_records = [], []
        self.frozen_models, self.frozen_versions, self.batch_version = None, None, None
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
            inputs = [sample["input"] for sample in samples]
            for player in PLAYERS:
                model, optimizer = self.models[player], self.optimizers[player]
                model.train()
                optimizer.zero_grad(set_to_none=True)
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
        self.generation += 1
        self.counters["updates"] += 1
        return {"updated": True, "samples": min(self.config.batch_size, len(self.replay)), "losses": losses,
                "generation": self.generation, "model_versions": self.model_versions()}

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
    def _validate_sample(sample: Any, *, labeled: bool) -> None:
        from .features import SCHEMA as INPUT_SCHEMA
        required = {"input", "owner", "policy", "rollout_version"}
        if labeled:
            required |= {"values", "target_source", "target_schema"}
        if not isinstance(sample, dict) or set(sample) != required or sample["owner"] not in PLAYERS:
            raise ValueError("Invalid replay sample")
        if not isinstance(sample["rollout_version"], str) or not sample["rollout_version"]:
            raise ValueError("Replay sample lacks policy version")
        features = sample["input"]
        if (not isinstance(features, dict) or set(features) != {"schema", "observation", "context", "actions"}
                or features["schema"] != INPUT_SCHEMA or not isinstance(features["observation"], dict)
                or not isinstance(features["context"], dict)):
            raise ValueError("Unsupported replay input schema")
        if features["observation"].get("current_decision_player") != sample["owner"]:
            raise ValueError("Replay owner differs from actual observation owner")
        # Interned context was validated in full once and cannot be mutated.
        # Validate each changing observation/menu without serializing that same
        # large registry once per trajectory row during checkpoint restoration.
        _canonical({key: item for key, item in features.items() if key != "context"})
        if not isinstance(features["context"], _ReadOnlyDict):
            _canonical(features["context"])
        if not isinstance(features.get("actions"), list) or not features["actions"]:
            raise ValueError("Replay sample must contain legal action features")
        normalized = probabilities(sample["policy"], len(features["actions"]))
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
                self._validate_sample(sample, labeled=name != "pending")
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
                self._validate_sample(sample, labeled=False)
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
        if any(context_keys[id(sample["input"]["context"])] != value["env_context"] for sample in samples):
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
        self.models, self.optimizers, self.env = models, optimizers, env
        self._context_pool = context_pool
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
            torch.save(self.checkpoint(), temporary)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def load_checkpoint(self, path: str | Path, *, env_template: Any = None) -> None:
        # This format contains optimizer/RNG Python objects from our own runner.
        self.restore(torch.load(path, map_location="cpu", weights_only=False), env_template=env_template)
