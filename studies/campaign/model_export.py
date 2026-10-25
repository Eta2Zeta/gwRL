"""Small, validated policy snapshots for evaluation, separate from recovery.

Exports contain only the three live policies and their interpretation metadata.
They deliberately cannot resume learning: Adam, replay, active games and random
streams belong to the occasional full recovery checkpoint instead.
Files are trusted local Torch archives, as with the full runner checkpoints.
"""
from __future__ import annotations

import copy
import os
import random
import tempfile
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

from studies.shared.multiplayer_mcts import PLAYERS
from .curriculum import compatibility, make_env, task_manifest
from .learning import _model_digest
from .neural import CampaignModelConfig, CampaignPolicyValueNet

MODEL_EXPORT_SCHEMA = "campaign-evaluation-models-v1"
_KEYS = {"schema", "config", "task", "training_environment_seeds", "model_config",
         "compatibility", "generation", "model_versions", "models", "runtime_source_sha256"}


def _expected_model_config(config) -> dict:
    return asdict(CampaignModelConfig(hidden_dim=config.hidden_dim,
        message_layers=config.message_layers, token_buckets=config.token_buckets,
        value_scale=config.value_scale))


@contextmanager
def _preserve_random_and_threads():
    """Legacy recovery construction seeds globals; never leak that into a caller."""
    python_state, numpy_state = random.getstate(), np.random.get_state()
    threads = torch.get_num_threads()
    try:
        with torch.random.fork_rng(devices=list(range(torch.cuda.device_count()))):
            yield
    finally:
        random.setstate(python_state)
        np.random.set_state(numpy_state)
        torch.set_num_threads(threads)


def save_model_export(path: str | Path, learner, runner: dict) -> dict:
    """Atomically publish small CPU tensors without copying any training history.

    The caller supplies a completed update boundary. Tensor clones prevent the
    published snapshot from sharing mutable storage with subsequent updates.
    Neither model modes nor any random generator are changed.
    """
    from .run import RunConfig, source_hashes

    path = Path(path)
    config = RunConfig(**runner["config"])
    if learner.model_config != _expected_model_config(config):
        raise ValueError("Model export configuration differs from runner")
    if runner["runtime_source_sha256"] != source_hashes():
        raise ValueError("Runtime sources changed; cannot export a different runtime")
    if learner.compatibility != runner["task"]["compatibility"]:
        raise ValueError("Model export task and learner compatibility differ")
    versions = learner.model_versions()
    payload = {"schema": MODEL_EXPORT_SCHEMA,
        "config": copy.deepcopy(runner["config"]), "task": copy.deepcopy(runner["task"]),
        "training_environment_seeds": list(runner["training_environment_seeds"]),
        "model_config": copy.deepcopy(learner.model_config),
        "compatibility": copy.deepcopy(learner.compatibility),
        "generation": learner.generation, "model_versions": versions,
        "runtime_source_sha256": dict(runner["runtime_source_sha256"]),
        "models": {player: {name: tensor.detach().cpu().clone()
                             for name, tensor in learner.models[player].state_dict().items()}
                   for player in PLAYERS}}
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".models-", suffix=".pt", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": str(path), "bytes": path.stat().st_size,
            "generation": learner.generation, "model_versions": versions}


def validate_model_export(path: str | Path, learner, runner: dict) -> dict:
    """Verify an existing immutable generation without rebuilding a network.

    A resumed or rolled-back run may encounter an export it already published.
    Reuse only an exact match; never replace contradictory evaluation evidence.
    Training may have started more games since that generation was exported, so
    the recorded training seeds must be a prefix of the current seed history.
    """
    from .run import RunConfig, source_hashes

    path = Path(path)
    config = RunConfig(**runner["config"])
    if (runner["runtime_source_sha256"] != source_hashes()
            or learner.model_config != _expected_model_config(config)
            or learner.compatibility != runner["task"]["compatibility"]):
        raise ValueError("Current runner, learner or sources are incompatible with a model export")
    value = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(value, dict) or set(value) != _KEYS or value.get("schema") != MODEL_EXPORT_SCHEMA:
        raise ValueError("Unsupported existing campaign model export")
    expected = {"config": runner["config"], "task": runner["task"],
        "model_config": learner.model_config, "compatibility": learner.compatibility,
        "runtime_source_sha256": runner["runtime_source_sha256"]}
    if any(value[key] != expected_value for key, expected_value in expected.items()):
        raise ValueError("Existing model export metadata differs from current training")
    if type(value["generation"]) is not int or value["generation"] != learner.generation:
        raise ValueError("Existing model export generation differs from current training")
    seeds = value["training_environment_seeds"]
    if (not isinstance(seeds, list)
            or any(type(seed) is not int or not 0 <= seed < 2**64 for seed in seeds)
            or seeds != runner["training_environment_seeds"][:len(seeds)]):
        raise ValueError("Existing model export training seeds are not a prefix of current training")
    versions = learner.model_versions()
    if value["model_versions"] != versions:
        raise ValueError("Existing model export versions differ from current weights")
    if not isinstance(value["models"], dict) or set(value["models"]) != set(PLAYERS):
        raise ValueError("Existing model export must contain all three actor policies")
    for player in PLAYERS:
        saved, live = value["models"][player], learner.models[player].state_dict()
        if not isinstance(saved, dict) or set(saved) != set(live):
            raise ValueError("Existing model export tensor keys differ from current weights")
        for name, expected_tensor in live.items():
            tensor = saved[name]
            if (not isinstance(tensor, torch.Tensor) or tensor.dtype != expected_tensor.dtype
                    or tensor.shape != expected_tensor.shape
                    or not torch.equal(tensor, expected_tensor.detach().cpu())):
                raise ValueError("Existing model export tensors differ from current weights")
            if tensor.is_floating_point() and not torch.isfinite(tensor).all():
                raise ValueError("Existing model export contains nonfinite weights")
    return {"path": str(path), "bytes": path.stat().st_size,
            "generation": learner.generation, "model_versions": versions}


def load_evaluation_models(path: str | Path) -> dict[str, Any]:
    """Load policies without creating an optimizer or restoring rollout games.

    Existing full checkpoints remain accepted through their original, complete
    learner validation. This legacy path is intentionally expensive; new exports
    need only tensor loading, three model constructors and task compatibility.
    """
    from .run import RUN_SCHEMA, RunConfig, _learner, source_hashes

    value = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(value, dict):
        raise ValueError("Unsupported campaign model export or foreground-run checkpoint")
    if value.get("schema") == RUN_SCHEMA:
        # Same authoritative structural/source gate as run._read, applied to
        # the already loaded payload so a large recovery file is read only once.
        if set(value) != {"schema", "runner", "learner"}:
            raise ValueError("Unsupported foreground-run checkpoint")
        runner = value["runner"]
        if runner["runtime_source_sha256"] != source_hashes():
            raise ValueError("Runtime sources changed; an explicit checkpoint migration is required")
        config = RunConfig(**runner["config"])
        template = make_env(config.seed, calendar_rounds=config.calendar_rounds)
        if runner["task"] != task_manifest(template):
            raise ValueError("Model export task differs from current scenario or rules")
        with _preserve_random_and_threads():
            learner = _learner(config, template)
            learner.restore(value["learner"], env_template=template)
        return {"config": runner["config"], "task": runner["task"],
            "training_environment_seeds": runner["training_environment_seeds"],
            "model_versions": learner.model_versions(), "models": learner.models,
            "generation": learner.generation,
            "runtime_source_sha256": runner["runtime_source_sha256"], "source_schema": RUN_SCHEMA}
    if set(value) != _KEYS or value.get("schema") != MODEL_EXPORT_SCHEMA:
        raise ValueError("Unsupported campaign model export")
    if value["runtime_source_sha256"] != source_hashes():
        raise ValueError("Runtime sources changed; an explicit model migration is required")
    config = RunConfig(**value["config"])
    template = make_env(config.seed, calendar_rounds=config.calendar_rounds)
    if (value["task"] != task_manifest(template)
            or value["compatibility"] != compatibility(template)):
        raise ValueError("Model export task differs from current scenario or rules")
    if value["model_config"] != _expected_model_config(config):
        raise ValueError("Model export configuration differs from runner")
    if type(value["generation"]) is not int or value["generation"] < 0:
        raise ValueError("Invalid exported model generation")
    if (not isinstance(value["training_environment_seeds"], list)
            or any(type(seed) is not int or not 0 <= seed < 2**64
                   for seed in value["training_environment_seeds"])):
        raise ValueError("Invalid exported training environment seeds")
    if (not isinstance(value["models"], dict) or set(value["models"]) != set(PLAYERS)
            or not isinstance(value["model_versions"], dict)
            or set(value["model_versions"]) != set(PLAYERS)):
        raise ValueError("Model export must contain all three actor policies")
    # Constructors initialize tensors randomly before replacing every tensor.
    # fork_rng prevents those unused initializations from advancing training RNG.
    with torch.random.fork_rng(devices=[]):
        models = {player: CampaignPolicyValueNet(CampaignModelConfig(**value["model_config"])).eval()
                  for player in PLAYERS}
        for player, model in models.items():
            model.load_state_dict(value["models"][player], strict=True)
            if any(tensor.is_floating_point() and not torch.isfinite(tensor).all()
                   for tensor in model.state_dict().values()):
                raise ValueError("Model export contains nonfinite weights")
            version = f"{player}:generation-{value['generation']}:{_model_digest(model)}"
            if value["model_versions"][player] != version:
                raise ValueError("Exported model version does not match weights")
    return {"config": value["config"], "task": value["task"],
        "training_environment_seeds": value["training_environment_seeds"],
        "model_versions": value["model_versions"], "models": models,
        "generation": value["generation"], "runtime_source_sha256": value["runtime_source_sha256"],
        "source_schema": MODEL_EXPORT_SCHEMA}
