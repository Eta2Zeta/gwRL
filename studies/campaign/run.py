"""Foreground campaign learning, checkpoint resume, evaluation and profiling.

Run ``python -m studies.campaign.run --help``. Defaults are deliberately bounded;
this module never launches another process or a background training job.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import signal
import tempfile
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import torch

from studies.shared.multiplayer_mcts import PLAYERS
from .curriculum import ROOT, compatibility, make_env, task_manifest
from .features import graph_compiler_backend
from .learning import CampaignLearner, LearningConfig, ReplayTraceWriter
from .model_export import load_evaluation_models, save_model_export, validate_model_export
from .neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator, resolve_neural_device

RUN_SCHEMA = "campaign-foreground-run-v1"


@dataclass(frozen=True)
class RunConfig:
    seed: int = 1936
    calendar_rounds: int | None = 1
    batches: int = 1
    transitions_per_batch: int = 6
    parallel_envs: int = 2
    simulations: int = 2
    max_depth: int = 4
    hidden_dim: int = 16
    message_layers: int = 1
    token_buckets: int = 2048
    value_scale: float = 100.0
    batch_size: int = 8
    epochs: int = 1
    learning_rate: float = 0.001
    replay_capacity: int = 512
    threads: int = 1
    checkpoint_every_waves: int | None = None
    checkpoint_interval_seconds: float = 1800.0
    complete_episodes: bool = False
    max_episodes: int | None = None
    cpu_budget: int | None = None
    neural_device: str = "cpu"

    def __post_init__(self):
        if not isinstance(self.neural_device, str) or self.neural_device not in {"cpu", "mps", "cuda"} and not (
                self.neural_device.startswith("cuda:") and self.neural_device[5:].isdigit()):
            raise ValueError("Neural device must be cpu, mps or an explicit CUDA device")
        positive = ("batches", "transitions_per_batch", "parallel_envs", "simulations", "max_depth",
                    "hidden_dim", "message_layers", "token_buckets", "batch_size", "epochs",
                    "replay_capacity", "threads")
        if any(type(getattr(self, key)) is not int or getattr(self, key) <= 0 for key in positive):
            raise ValueError("Run counts and dimensions must be positive integers")
        if self.calendar_rounds is not None and (type(self.calendar_rounds) is not int or not 1 <= self.calendar_rounds <= 11):
            raise ValueError("Curriculum horizon must be between one and eleven rounds")
        if type(self.seed) is not int or not 0 <= self.seed < 2**64:
            raise ValueError("Run seed must be an unsigned 64-bit integer")
        if type(self.complete_episodes) is not bool:
            raise ValueError("complete_episodes must be Boolean")
        if self.checkpoint_every_waves is not None and (
                type(self.checkpoint_every_waves) is not int or self.checkpoint_every_waves <= 0):
            raise ValueError("Explicit checkpoint wave interval must be a positive integer")
        if (type(self.checkpoint_interval_seconds) not in (int, float)
                or not math.isfinite(self.checkpoint_interval_seconds) or self.checkpoint_interval_seconds <= 0):
            raise ValueError("Checkpoint time interval must be positive and finite")
        if self.max_episodes is not None and (
                type(self.max_episodes) is not int or self.max_episodes <= 0 or not self.complete_episodes):
            raise ValueError("An exact episode limit requires complete episodes and a positive integer")
        if self.cpu_budget is not None:
            if type(self.cpu_budget) is not int or self.cpu_budget <= 0 or self.cpu_budget > (os.cpu_count() or 1):
                raise ValueError("CPU budget must fit available logical cores")
            if self.threads + self.parallel_envs + 1 > self.cpu_budget:
                raise ValueError("Tensor threads, search workers and coordinator exceed CPU budget")


def source_hashes() -> dict[str, str]:
    paths = [*sorted((ROOT / "studies/campaign").glob("*.py")),
             *sorted((ROOT / "studies/campaign/backends").rglob("*.py")),
             ROOT / "studies/shared/campaign_adapter.py", ROOT / "studies/shared/multiplayer_mcts.py",
             ROOT / "studies/shared/immutable_json.py",
             *sorted((ROOT / "include").rglob("*.hpp")), *sorted((ROOT / "src").rglob("*.cpp"))]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".report-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _learner(config: RunConfig, template):
    device = resolve_neural_device(config.neural_device)
    torch.set_num_threads(config.threads)
    random.seed(config.seed)
    np.random.seed(config.seed % (2 ** 32))
    torch.manual_seed(config.seed)
    model_config = CampaignModelConfig(hidden_dim=config.hidden_dim, message_layers=config.message_layers,
        token_buckets=config.token_buckets, value_scale=config.value_scale)
    models = {player: CampaignPolicyValueNet(model_config, device=device).eval() for player in PLAYERS}
    learning = LearningConfig(simulations=config.simulations, max_depth=config.max_depth,
        batch_size=config.batch_size, epochs=config.epochs, learning_rate=config.learning_rate,
        replay_capacity=config.replay_capacity, value_scale=config.value_scale, seed=config.seed)
    return CampaignLearner(models, model_config, learning, compatibility=compatibility(template))


def _save(path: Path, learner: CampaignLearner, runner: dict, *, backup_current=True):
    payload = {"schema": RUN_SCHEMA, "runner": runner, "learner": learner.checkpoint()}
    descriptor, temporary = tempfile.mkstemp(prefix=".checkpoint-", suffix=".pt", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            # Protocol 5 writes graph frame bytes directly; protocol 2 creates
            # Latin-1 text copies that inflate mature replay snapshots.
            torch.save(payload, handle, pickle_protocol=5)
            handle.flush()
            os.fsync(handle.fileno())
        if backup_current and path.exists():
            # Keep the last fully written snapshot independently of the new
            # rename. A hard link shares immutable bytes, not another copy of
            # what may be a large replay buffer. Both names are on this volume.
            backup_descriptor, backup = tempfile.mkstemp(prefix=".checkpoint-previous-", dir=path.parent)
            os.close(backup_descriptor)
            os.unlink(backup)
            try:
                os.link(path, backup)
                os.replace(backup, path.with_name(path.name + ".previous"))
            finally:
                if os.path.exists(backup):
                    os.unlink(backup)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _read(path: Path):
    # Our own local checkpoints contain optimizer/RNG objects as well as tensors.
    value = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(value, dict) or set(value) != {"schema", "runner", "learner"} or value["schema"] != RUN_SCHEMA:
        raise ValueError("Unsupported foreground-run checkpoint")
    if value["runner"]["runtime_source_sha256"] != source_hashes():
        raise ValueError("Runtime sources changed; an explicit checkpoint migration is required")
    return value


def recovery_checkpoint_due(config: RunConfig, wave_index: int, last_saved: float, now: float) -> bool:
    """Explicit wave cadence is retained for controlled comparisons and tests.

    Normal runs use elapsed wall time, independently of game/learning progress.
    The caller advances last_saved only after a successful durable write.
    """
    if config.checkpoint_every_waves is not None:
        return wave_index % config.checkpoint_every_waves == 0
    return now - last_saved >= config.checkpoint_interval_seconds


def _config(args, saved=None):
    values = asdict(RunConfig()) if saved is None else dict(saved)
    for field in fields(RunConfig):
        override = getattr(args, field.name, None)
        if override is not None:
            if saved is not None and override != values[field.name]:
                raise ValueError(f"Resume configuration differs: {field.name}")
            values[field.name] = override
    if getattr(args, "full_campaign", False):
        if saved is not None and values["calendar_rounds"] is not None:
            raise ValueError("Cannot resume a curriculum checkpoint as a full campaign")
        values["calendar_rounds"] = None
    return RunConfig(**values)


def train(args) -> int:
    if getattr(args, "record_replay", False) and args.resume:
        raise ValueError("--record-replay currently requires a fresh run; existing replay prefixes are preserved")
    loaded = _read(args.resume) if args.resume else None
    resuming = loaded is not None
    config = _config(args, loaded["runner"]["config"] if loaded else None)
    output = (args.run_dir or (args.resume.parent if args.resume else ROOT / "studies/campaign/runs" /
              f"{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}" )).resolve()
    continuing_here = args.resume is not None and output == args.resume.parent.resolve()
    if not continuing_here and output.exists() and any(output.iterdir()):
        raise ValueError("Choose an empty run directory; existing results are preserved")
    output.mkdir(parents=True, exist_ok=True)
    template = make_env(config.seed, calendar_rounds=config.calendar_rounds)
    learner = _learner(config, template)
    runner = loaded["runner"] if loaded else {
        "config": asdict(config), "runtime_source_sha256": source_hashes(),
        "batch_index": 0, "wave_index": 0, "training_environment_seeds": [],
        "task": task_manifest(template), "updates": [], "batch_sizes": [],
        "batch_start_history": 0, "active_episode_seeds": [], "total_waves": 0,
        "episode_wave_limit": config.transitions_per_batch, "budget_extensions": []}
    if loaded:
        learner.restore(loaded["learner"], env_template=template)
    # Restore owns its committed state. Keeping the input archive alive pins
    # every original replay row even after the learner evicts those examples.
    loaded = None
    extension = getattr(args, "extend_episode_budget", None)
    if extension is not None:
        old_limit = runner["episode_wave_limit"]
        if not config.complete_episodes or extension <= old_limit:
            raise ValueError("An episode budget extension must increase the existing complete-episode limit")
        runner["budget_extensions"].append({"old_limit": old_limit, "new_limit": extension,
                                           "batch": runner["batch_index"], "wave": runner["wave_index"]})
        runner["episode_wave_limit"] = extension
    stopped = False
    exhausted = False
    signal_name = None

    def request_stop(number, _frame):
        nonlocal stopped, signal_name
        stopped, signal_name = True, signal.Signals(number).name

    old_handlers = {number: signal.signal(number, request_stop) for number in (signal.SIGINT, signal.SIGTERM)}
    manifest_path, checkpoint_path = output / "manifest.json", output / "checkpoint.pt"
    recovering_previous = resuming and args.resume.resolve() == checkpoint_path.with_name(
        checkpoint_path.name + ".previous").resolve()
    started = time.perf_counter()
    initial_waves = runner["total_waves"]
    initial_transitions = learner.counters["transitions"]
    replay_writer = None
    timings = {name: 0.0 for name in (
        "collection", "learning_updates", "checkpoint_save", "model_export", "progress_reporting")}
    checkpoint_saves = 0
    model_exports = 0
    latest_model_export = None
    last_checkpoint_time = time.monotonic()

    @contextmanager
    def measure(name):
        before = time.perf_counter()
        try:
            yield
        finally:
            timings[name] += time.perf_counter() - before

    def save_checkpoint(path):
        nonlocal recovering_previous, checkpoint_saves, last_checkpoint_time
        with measure("checkpoint_save"):
            # A caller explicitly recovering the backup has not vouched for
            # the newest file. Do not overwrite that known-good backup with it.
            _save(path, learner, runner, backup_current=not (recovering_previous and path == checkpoint_path))
            checkpoint_saves += 1
            if path == checkpoint_path:
                recovering_previous = False
                last_checkpoint_time = time.monotonic()

    def export_model():
        nonlocal latest_model_export, model_exports
        relative = Path("models") / f"generation-{learner.generation:06d}.pt"
        with measure("model_export"):
            if (output / relative).exists():
                metadata = validate_model_export(output / relative, learner, runner)
            else:
                metadata = save_model_export(output / relative, learner, runner)
                model_exports += 1
        latest_model_export = {**metadata, "path": str(relative)}

    def factory(seed):
        runner["training_environment_seeds"].append(seed)
        return make_env(seed, calendar_rounds=config.calendar_rounds)

    def persist(status, *, recovery=True):
        if recovery:
            save_checkpoint(checkpoint_path)
        with measure("progress_reporting"):
            _json(manifest_path, {"schema": RUN_SCHEMA, "status": status,
                "checkpoint": checkpoint_path.name, "runner": runner, "counters": learner.counters,
                "latest_model_export": latest_model_export,
                "checkpoint_saves_this_invocation": checkpoint_saves,
                "model_exports_this_invocation": model_exports,
                "recovery_policy": {"interval_seconds": config.checkpoint_interval_seconds,
                                    "explicit_wave_override": config.checkpoint_every_waves,
                                    "save_after_each_update": False},
                "replay_trace": replay_writer.path.name if replay_writer else None,
                "software": {"torch": torch.__version__, "device": config.neural_device, "threads": config.threads,
                             "rules_device": "cpu", "search_device": "cpu",
                             "graph_compiler": graph_compiler_backend()},
                "resources": {"logical_cores": os.cpu_count(), "cpu_budget": config.cpu_budget,
                              "conservative_thread_budget": config.threads + config.parallel_envs + 1,
                              "interop_threads": torch.get_num_interop_threads()},
                "elapsed_seconds_this_invocation": time.perf_counter() - started,
                "timings_seconds_this_invocation": dict(timings),
                "collection_transitions_per_second_this_invocation":
                    (learner.counters["transitions"] - initial_transitions) / timings["collection"]
                    if timings["collection"] else None,
                # Timing is an invocation report, never deterministic runner
                # state. This snapshot excludes its own JSON write and later
                # progress output; subsequent reports include earlier writes.
                "timing_scope": "After initialization, non-overlapping buckets through this snapshot; "
                                "current report write and later output excluded; learning includes finish_batch.",
                "full_target_game": runner["task"]["full_target_game"],
                "limits": "Bounded training and bootstrapped cutoffs are not evidence of strategic strength."})

    def progress(event, collection=None):
        with measure("progress_reporting"):
            value = {"event": event, "batch": runner["batch_index"], "wave": runner["wave_index"],
                     "counters": learner.counters.copy(), "elapsed_seconds": time.perf_counter() - started,
                     "clocks": [env.observation()["state"]["clock"] for env in learner.parallel_envs],
                     "terminal": [env.is_terminal() for env in learner.parallel_envs],
                     "last_actions": collection["events"] if collection else [],
                     "terminal_returns": [list(env.returns()) if env.is_terminal() else None
                                          for env in learner.parallel_envs]}
            print(json.dumps(value, sort_keys=True), flush=True)
            with (output / "progress.jsonl").open("a") as handle:
                handle.write(json.dumps(value, sort_keys=True) + "\n")
                handle.flush()

    try:
        if getattr(args, "record_replay", False):
            replay_writer = ReplayTraceWriter(output / "replay.jsonl", {
                "kind": "training", "config": asdict(config), "task": runner["task"],
                "runtime_source_sha256": runner["runtime_source_sha256"],
                "model_config": learner.model_config, "initial_model_versions": learner.model_versions()})
            learner.set_replay_observer(replay_writer)
        if not resuming:
            export_model()
            save_checkpoint(output / "initial.pt")
            persist("initialized")
        else:
            # Preserve already published generation files when restoring an
            # earlier recovery point. The current recovery generation, rather
            # than a possibly newer manifest/export, is authoritative here.
            export_model()
        while (runner["batch_index"] < config.batches and not stopped
               and (config.max_episodes is None or learner.counters["episodes"] < config.max_episodes
                    or learner.frozen_models is not None)):
            if learner.frozen_models is None:
                with measure("collection"):
                    runner["batch_start_history"] = len(learner.action_history)
                    if config.complete_episodes or not learner.parallel_envs:
                        root_count = config.parallel_envs
                        if config.max_episodes is not None:
                            root_count = min(root_count, config.max_episodes - learner.counters["episodes"])
                        roots = [learner._new_env(factory) for _ in range(root_count)]
                        runner["active_episode_seeds"] = runner["training_environment_seeds"][-root_count:]
                    else:
                        roots = learner.parallel_envs
                    learner.begin_batch_many(roots)
            limit = runner["episode_wave_limit"] if config.complete_episodes else config.transitions_per_batch
            while runner["wave_index"] < limit and not stopped:
                if config.complete_episodes and all(env.is_terminal() for env in learner.parallel_envs):
                    break
                with measure("collection"):
                    result = learner.collect_many(1, None if config.complete_episodes else factory)
                runner["batch_sizes"].extend(result.get("inference_batch_sizes", []))
                runner["wave_index"] += 1
                progress("episode_completed" if any(event["terminal"] for event in result["events"]) else "rollout", result)
                completed_waves = runner["total_waves"] + 1
                runner["total_waves"] = completed_waves
                if recovery_checkpoint_due(config, runner["wave_index"], last_checkpoint_time, time.monotonic()):
                    persist("running")
                if args.stop_after_waves is not None and completed_waves - initial_waves >= args.stop_after_waves:
                    stopped, signal_name = True, "bounded_smoke_stop"
            if not stopped:
                if config.complete_episodes and not all(env.is_terminal() for env in learner.parallel_envs):
                    exhausted = True
                    break
                with measure("progress_reporting"):
                    history = learner.action_history[runner["batch_start_history"]:]
                    episodes = []
                    for index, env in enumerate(learner.parallel_envs):
                        events = [event for event in history if event["root"] == index]
                        episodes.append({"root": index, "seed": runner["active_episode_seeds"][index],
                            "terminal": env.is_terminal(), "transitions_this_batch": len(events),
                            "decisions_by_actor": dict(Counter(e["owner"] for e in events if e["owner"] is not None)),
                            "action_counts": dict(Counter(e.get("action_kind", e["kind"]) for e in events)),
                            "clock": env.observation()["state"]["clock"], "wealth": env.wealth(),
                            "observed_terminal_returns": list(env.returns()) if env.is_terminal() else None})
                with measure("learning_updates"):
                    rollout = learner.finish_batch()
                    if config.complete_episodes and rollout["bootstrap_samples"]:
                        raise RuntimeError("Complete-episode training must never create bootstrap labels")
                    update = learner.update()
                runner["updates"].append({"rollout": rollout, "update": update, "episodes": episodes})
                runner["batch_index"] += 1
                runner["wave_index"] = 0
                export_model()
                persist("running", recovery=False)
                progress("update")
        status = "interrupted" if stopped else "episode_budget_exhausted" if exhausted else "completed"
        persist(status)
        progress(status)
        if replay_writer is not None:
            replay_writer({"type": "run_end", "status": status, "stop_reason": signal_name,
                           "counters": learner.counters.copy()})
        print(json.dumps({"run_dir": str(output), "status": status,
                          "stop_reason": signal_name, "checkpoint": str(checkpoint_path)}, sort_keys=True), flush=True)
        return 130 if stopped else 2 if exhausted else 0
    finally:
        if replay_writer is not None:
            replay_writer.close()
        for number, handler in old_handlers.items():
            signal.signal(number, handler)


def evaluate_command(args) -> int:
    from .evaluation import evaluate, validate_heldout_seeds
    torch.set_num_threads(1)
    requested_device = getattr(args, "neural_device", None)
    loaded = (load_evaluation_models(args.checkpoint) if requested_device is None else
              load_evaluation_models(args.checkpoint, device=requested_device))
    config = RunConfig(**loaded["config"])
    torch.set_num_threads(config.threads)
    template = make_env(config.seed, calendar_rounds=config.calendar_rounds)
    versions = loaded["model_versions"]
    version = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
    evaluator = NeuralEvaluator(loaded["models"], version=version)
    seeds = [int(value) for value in args.seeds.split(",")]
    targets = PLAYERS if args.target == "all" else (args.target,)
    separation = validate_heldout_seeds({player: seeds for player in PLAYERS},
                                      [config.seed, *loaded["training_environment_seeds"]])
    report = {"schema": "campaign-evaluation-bundle-v1", "task": task_manifest(template),
              "training_seed": config.seed, "seed_separation": separation,
              "model_versions": versions,
              "execution": {"rules": "cpu", "search": "cpu", "neural_device":
                            str(next(loaded["models"][PLAYERS[0]].parameters()).device)},
              "results": []}
    for player in targets:
        result = evaluate(lambda seed: make_env(seed, calendar_rounds=config.calendar_rounds), evaluator,
            target_player=player, seeds=seeds, baseline_style=args.baseline_style,
            simulations=args.simulations, max_depth=args.max_depth, max_transitions=args.max_transitions,
            target_script=args.target_script)
        report["results"].append(result)
        print(json.dumps({"target": player, "terminal_games": result["terminal_games"],
                          "truncated_games": result["truncated_games"]}), flush=True)
    _json(args.output, report)
    print(json.dumps({"output": str(args.output)}), flush=True)
    return 0


def profile_command(args) -> int:
    from .evaluation import profile
    loaded = _read(args.checkpoint)
    config = RunConfig(**loaded["runner"]["config"])
    template = make_env(config.seed, calendar_rounds=config.calendar_rounds)
    learner = _learner(config, template)
    learner.restore(loaded["learner"], env_template=template)
    loaded = None
    versions = learner.model_versions()
    version = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
    evaluator = NeuralEvaluator(learner.models, version=version)
    envs = learner.parallel_envs or [template]
    report = profile(envs, evaluator, repeats=args.repeats)
    report.update(task=task_manifest(template), model_versions=versions,
                  software={"torch": torch.__version__, "device": config.neural_device, "threads": config.threads})
    _json(args.output, report)
    print(json.dumps({"output": str(args.output), "actual_state_unchanged": report["actual_state_unchanged"]}), flush=True)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    training = commands.add_parser("train", help="Bounded foreground vector-MCTS self-play")
    training.add_argument("--run-dir", type=Path)
    training.add_argument("--resume", type=Path, help="Only a trusted local checkpoint produced by this runner")
    training.add_argument("--record-replay", action="store_true",
                          help="Write real choices, search preferences and observed events to replay.jsonl (fresh runs only)")
    training.add_argument("--stop-after-waves", type=int, help="Safe bounded interruption for resume verification")
    training.add_argument("--extend-episode-budget", type=int,
                          help="Explicitly increase the resumable complete-episode transition guard")
    for field in fields(RunConfig):
        if field.name == "neural_device":
            training.add_argument("--neural-device", default=None,
                                  help="cpu (default), mps (Apple GPU) or cuda[:index]; rules/search remain CPU")
            continue
        if field.name == "complete_episodes":
            training.add_argument("--complete-episodes", action=argparse.BooleanOptionalAction, default=None,
                                  help="Freeze each batch until all games finish; a guard saves without updating")
            continue
        kind = float if field.name in {"value_scale", "learning_rate", "checkpoint_interval_seconds"} else int
        training.add_argument("--" + field.name.replace("_", "-"), type=kind, default=None)
    training.add_argument("--full-campaign", action="store_true", help="Use the original July1936–July1941 target")
    evaluation = commands.add_parser("evaluate", help="Held-out fixed-opponent games without training noise")
    evaluation.add_argument("--checkpoint", type=Path, required=True)
    evaluation.add_argument("--neural-device", default=None,
                            help="Explicit evaluation device; never changes a saved learning checkpoint")
    evaluation.add_argument("--output", type=Path, required=True)
    evaluation.add_argument("--target", choices=["all", *PLAYERS], default="all")
    evaluation.add_argument("--seeds", default="1009,1013")
    evaluation.add_argument("--baseline-style", choices=["balanced", "cautious"], default="balanced")
    evaluation.add_argument("--target-script", choices=["balanced", "cautious"])
    evaluation.add_argument("--simulations", type=int, default=2)
    evaluation.add_argument("--max-depth", type=int, default=4)
    evaluation.add_argument("--max-transitions", type=int, default=40)
    profiling = commands.add_parser("profile", help="Bounded real-state operations and batched inference")
    profiling.add_argument("--checkpoint", type=Path, required=True)
    profiling.add_argument("--output", type=Path, required=True)
    profiling.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args(argv)
    torch.set_num_interop_threads(1)
    if getattr(args, "stop_after_waves", None) is not None and args.stop_after_waves < 1:
        parser.error("--stop-after-waves must be positive")
    return {"train": train, "evaluate": evaluate_command, "profile": profile_command}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
