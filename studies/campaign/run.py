"""Foreground campaign learning, checkpoint resume, evaluation and profiling.

Run ``python -m studies.campaign.run --help``. Defaults are deliberately bounded;
this module never launches another process or a background training job.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
from .learning import CampaignLearner, LearningConfig
from .neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator

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
    checkpoint_every_waves: int = 4
    complete_episodes: bool = False
    cpu_budget: int | None = None

    def __post_init__(self):
        positive = ("batches", "transitions_per_batch", "parallel_envs", "simulations", "max_depth",
                    "hidden_dim", "message_layers", "token_buckets", "batch_size", "epochs",
                    "replay_capacity", "threads", "checkpoint_every_waves")
        if any(type(getattr(self, key)) is not int or getattr(self, key) <= 0 for key in positive):
            raise ValueError("Run counts and dimensions must be positive integers")
        if self.calendar_rounds is not None and (type(self.calendar_rounds) is not int or not 1 <= self.calendar_rounds <= 11):
            raise ValueError("Curriculum horizon must be between one and eleven rounds")
        if type(self.seed) is not int or not 0 <= self.seed < 2**64:
            raise ValueError("Run seed must be an unsigned 64-bit integer")
        if type(self.complete_episodes) is not bool:
            raise ValueError("complete_episodes must be Boolean")
        if self.cpu_budget is not None:
            if type(self.cpu_budget) is not int or self.cpu_budget <= 0 or self.cpu_budget > (os.cpu_count() or 1):
                raise ValueError("CPU budget must fit available logical cores")
            if self.threads + self.parallel_envs + 1 > self.cpu_budget:
                raise ValueError("Tensor threads, search workers and coordinator exceed CPU budget")


def source_hashes() -> dict[str, str]:
    paths = [*sorted((ROOT / "studies/campaign").glob("*.py")),
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
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _learner(config: RunConfig, template):
    torch.set_num_threads(config.threads)
    random.seed(config.seed)
    np.random.seed(config.seed % (2 ** 32))
    torch.manual_seed(config.seed)
    model_config = CampaignModelConfig(hidden_dim=config.hidden_dim, message_layers=config.message_layers,
        token_buckets=config.token_buckets, value_scale=config.value_scale)
    models = {player: CampaignPolicyValueNet(model_config).eval() for player in PLAYERS}
    learning = LearningConfig(simulations=config.simulations, max_depth=config.max_depth,
        batch_size=config.batch_size, epochs=config.epochs, learning_rate=config.learning_rate,
        replay_capacity=config.replay_capacity, value_scale=config.value_scale, seed=config.seed)
    return CampaignLearner(models, model_config, learning, compatibility=compatibility(template))


def _save(path: Path, learner: CampaignLearner, runner: dict):
    payload = {"schema": RUN_SCHEMA, "runner": runner, "learner": learner.checkpoint()}
    descriptor, temporary = tempfile.mkstemp(prefix=".checkpoint-", suffix=".pt", dir=path.parent)
    os.close(descriptor)
    try:
        torch.save(payload, temporary)
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
    loaded = _read(args.resume) if args.resume else None
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
    started = time.perf_counter()
    initial_waves = runner["total_waves"]
    initial_transitions = learner.counters["transitions"]
    timings = {name: 0.0 for name in ("collection", "learning_updates", "checkpoint_save", "progress_reporting")}

    @contextmanager
    def measure(name):
        before = time.perf_counter()
        try:
            yield
        finally:
            timings[name] += time.perf_counter() - before

    def save_checkpoint(path):
        with measure("checkpoint_save"):
            _save(path, learner, runner)

    def factory(seed):
        runner["training_environment_seeds"].append(seed)
        return make_env(seed, calendar_rounds=config.calendar_rounds)

    def persist(status):
        save_checkpoint(checkpoint_path)
        with measure("progress_reporting"):
            _json(manifest_path, {"schema": RUN_SCHEMA, "status": status,
                "checkpoint": checkpoint_path.name, "runner": runner, "counters": learner.counters,
                "software": {"torch": torch.__version__, "device": "cpu", "threads": config.threads},
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
        if loaded is None:
            save_checkpoint(output / "initial.pt")
            persist("initialized")
        while runner["batch_index"] < config.batches and not stopped:
            if learner.frozen_models is None:
                with measure("collection"):
                    runner["batch_start_history"] = len(learner.action_history)
                    if config.complete_episodes or not learner.parallel_envs:
                        roots = [learner._new_env(factory) for _ in range(config.parallel_envs)]
                        runner["active_episode_seeds"] = runner["training_environment_seeds"][-config.parallel_envs:]
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
                if runner["wave_index"] % config.checkpoint_every_waves == 0:
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
                persist("running")
                progress("update")
        status = "interrupted" if stopped else "episode_budget_exhausted" if exhausted else "completed"
        persist(status)
        progress(status)
        print(json.dumps({"run_dir": str(output), "status": status,
                          "stop_reason": signal_name, "checkpoint": str(checkpoint_path)}, sort_keys=True), flush=True)
        return 130 if stopped else 2 if exhausted else 0
    finally:
        for number, handler in old_handlers.items():
            signal.signal(number, handler)


def evaluate_command(args) -> int:
    from .evaluation import evaluate, validate_heldout_seeds
    loaded = _read(args.checkpoint)
    config = RunConfig(**loaded["runner"]["config"])
    template = make_env(config.seed, calendar_rounds=config.calendar_rounds)
    learner = _learner(config, template)
    learner.restore(loaded["learner"], env_template=template)
    versions = learner.model_versions()
    version = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
    evaluator = NeuralEvaluator(learner.models, version=version)
    seeds = [int(value) for value in args.seeds.split(",")]
    targets = PLAYERS if args.target == "all" else (args.target,)
    separation = validate_heldout_seeds({player: seeds for player in PLAYERS},
                                      [config.seed, *loaded["runner"]["training_environment_seeds"]])
    report = {"schema": "campaign-evaluation-bundle-v1", "task": task_manifest(template),
              "training_seed": config.seed, "seed_separation": separation,
              "model_versions": versions, "results": []}
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
    versions = learner.model_versions()
    version = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
    evaluator = NeuralEvaluator(learner.models, version=version)
    envs = learner.parallel_envs or [template]
    report = profile(envs, evaluator, repeats=args.repeats)
    report.update(task=task_manifest(template), model_versions=versions,
                  software={"torch": torch.__version__, "device": "cpu", "threads": config.threads})
    _json(args.output, report)
    print(json.dumps({"output": str(args.output), "actual_state_unchanged": report["actual_state_unchanged"]}), flush=True)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    training = commands.add_parser("train", help="Bounded foreground vector-MCTS self-play")
    training.add_argument("--run-dir", type=Path)
    training.add_argument("--resume", type=Path, help="Only a trusted local checkpoint produced by this runner")
    training.add_argument("--stop-after-waves", type=int, help="Safe bounded interruption for resume verification")
    training.add_argument("--extend-episode-budget", type=int,
                          help="Explicitly increase the resumable complete-episode transition guard")
    for field in fields(RunConfig):
        if field.name == "complete_episodes":
            training.add_argument("--complete-episodes", action=argparse.BooleanOptionalAction, default=None,
                                  help="Freeze each batch until all games finish; a guard saves without updating")
            continue
        kind = float if field.name in {"value_scale", "learning_rate"} else int
        training.add_argument("--" + field.name.replace("_", "-"), type=kind, default=None)
    training.add_argument("--full-campaign", action="store_true", help="Use the original July1936–July1941 target")
    evaluation = commands.add_parser("evaluate", help="Held-out fixed-opponent games without training noise")
    evaluation.add_argument("--checkpoint", type=Path, required=True)
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
