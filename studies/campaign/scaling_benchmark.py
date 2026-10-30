"""Bounded CPU-only campaign search benchmarks, without optimizer updates.

Each CLI invocation supervises one fresh worker process. The wall limit includes
Python/model startup and scripted preparation. A sampled aggregate RSS guard
stops the worker before the requested memory envelope, with a safety margin;
this is not a kernel-enforced instantaneous allocation limit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA = "campaign-scaling-benchmark-v1"
MEMORY_MARGIN_BYTES = 128 * 1024**2


@dataclass(frozen=True)
class BenchmarkConfig:
    mode: str = "search"
    seed: int = 1951
    roots: int = 4
    simulations: int = 4
    max_depth: int = 8
    waves: int = 4
    calendar_rounds: int | None = 2
    start_round: int = 1
    start_nation_index: int = 0
    start_phase: str = "production"
    start_decision_kind: str | None = None
    preparation_transitions: int = 10000
    max_transitions: int = 1024
    max_state_visits: int = 12
    seconds: float = 60.0
    threads: int = 4
    cpu_budget: int = 12
    memory_bytes: int = 30_000_000_000
    hidden_dim: int = 16
    message_layers: int = 1
    token_buckets: int = 2048
    checkpoint_weights: str | None = None

    def __post_init__(self):
        for name in ("roots", "simulations", "max_depth", "waves", "start_round",
                     "preparation_transitions", "max_transitions", "max_state_visits",
                     "threads", "cpu_budget", "memory_bytes", "hidden_dim",
                     "message_layers", "token_buckets"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.cpu_budget > min(12, os.cpu_count() or 1):
            raise ValueError("CPU budget exceeds the authorized 12 cores or available hardware")
        if self.threads + self.roots + 2 > self.cpu_budget:
            raise ValueError("Tensor threads, search workers and two coordinators exceed CPU budget")
        if not MEMORY_MARGIN_BYTES < self.memory_bytes <= 30_000_000_000:
            raise ValueError("Memory envelope must fit the authorized 30 GB, above the guard margin")
        if self.mode not in {"search", "episode"}:
            raise ValueError("Unknown benchmark mode")
        if self.calendar_rounds is not None and (type(self.calendar_rounds) is not int or not 1 <= self.calendar_rounds <= 11):
            raise ValueError("Calendar horizon must be one to eleven rounds, or full campaign")
        if not 1 <= self.start_round <= (self.calendar_rounds or 11):
            raise ValueError("Starting round must be inside the real task horizon")
        if type(self.start_nation_index) is not int or not 0 <= self.start_nation_index < 4:
            raise ValueError("Starting nation index must be zero to three")
        if self.start_phase not in {"production", "combat_movement", "combat", "non_combat_movement", "place_units"}:
            raise ValueError("Unknown starting calendar phase")
        if self.start_decision_kind is not None and (not isinstance(self.start_decision_kind, str) or not self.start_decision_kind):
            raise ValueError("Starting decision kind must be a nonempty string or None")
        if self.mode == "episode" and (self.start_round != 1 or self.start_nation_index != 0 or
                                      self.start_phase != "production" or self.start_decision_kind is not None):
            raise ValueError("Episode measurements must start from the approved initial position")
        if type(self.seed) is not int or not 0 <= self.seed < 2**64 - self.roots:
            raise ValueError("Seed and derived root seeds must fit unsigned 64-bit integers")
        if isinstance(self.seconds, bool) or not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError("Wall limit must be finite and positive")
        if self.hidden_dim < 4 or self.token_buckets < 2:
            raise ValueError("Model dimensions do not meet the neural model contract")
        if self.checkpoint_weights is not None and (not isinstance(self.checkpoint_weights, str) or not Path(self.checkpoint_weights).is_file()):
            raise ValueError("Weights source must be an existing trusted local runner checkpoint")


def _write(path: Path, value: dict):
    descriptor, temporary = tempfile.mkstemp(prefix=".benchmark-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _rss_bytes(pid: int) -> int:
    """Current resident bytes via the OS; fail closed if monitoring is unavailable."""
    result = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, timeout=2)
    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        raise ProcessLookupError(f"Cannot inspect process {pid} resident memory")
    return int(value) * 1024


def _peak_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def _clock(env):
    return dict(env.observation()["state"]["clock"])


def _sample(env, actions):
    from .baselines import raw_action
    return {"clock": _clock(env), "decision_kind": env.decision_kind(),
            "owner": env.current_decision_player(), "menu_size": len(actions),
            "menu_kinds": dict(Counter(raw_action(action)["kind"] for action in actions)),
            "planning_key": env.planning_key()}


def run_case(config: BenchmarkConfig, progress_path: Path | None = None, *,
             replay_output: Path | None = None) -> dict:
    """Run inside an already supervised worker; also useful for tiny smoke tests."""
    if replay_output is not None and config.mode != "episode":
        raise ValueError("Replay recording requires episode mode with real executed choices")
    import random
    import numpy as np
    import torch
    from studies.shared.multiplayer_mcts import PLAYERS, MctsConfig, action_key
    from .baselines import BASELINE_VERSION, baseline_distribution
    from .batching import BatchStats, search_many
    from .curriculum import SCENARIO, make_env, task_manifest
    from .features import graph_compiler_backend
    from .neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
    from .run import source_hashes
    from .learning import ReplayTraceCapture, ReplayTraceWriter

    started = time.perf_counter()
    torch.set_num_threads(config.threads)
    # This worker is fresh; setting inter-op threads is safe before inference.
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    random.seed(config.seed)
    np.random.seed(config.seed % 2**32)
    torch.manual_seed(config.seed)
    weights = None
    transfer = None
    if config.checkpoint_weights:
        path = Path(config.checkpoint_weights).resolve()
        # This is an explicitly requested trusted local file. Import weights
        # only: never restore the learner, optimizer, RNG, replay or old states.
        payload = torch.load(path, map_location="cpu", weights_only=False)
        if payload.get("schema") != "campaign-foreground-run-v1":
            raise ValueError("Weights transfer requires a foreground-run checkpoint")
        model_config = CampaignModelConfig(**payload["learner"]["metadata"]["model_config"])
        weights = payload["learner"]["models"]
        transfer = {"source": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "source_compatibility": payload["learner"]["metadata"]["compatibility"],
                    "purpose": "inference-only transfer into fresh current-rule environments; not a training resume"}
    else:
        model_config = CampaignModelConfig(hidden_dim=config.hidden_dim, message_layers=config.message_layers,
                                           token_buckets=config.token_buckets)
    models = {player: CampaignPolicyValueNet(model_config).eval() for player in PLAYERS}
    if weights is not None:
        if set(weights) != set(PLAYERS):
            raise ValueError("Weights must contain exactly the three campaign players")
        for player, model in models.items():
            model.load_state_dict(weights[player], strict=True)
    versions = {player: hashlib.sha256(b"".join(value.detach().cpu().numpy().tobytes()
                for value in model.state_dict().values())).hexdigest() for player, model in models.items()}
    evaluator = NeuralEvaluator(models, version=hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest())
    envs = [make_env(config.seed + index, calendar_rounds=config.calendar_rounds) for index in range(config.roots)]
    nation_order = json.loads((SCENARIO / "manifest.json").read_text())["campaign"]["national_turn_order"]
    report = {"schema": SCHEMA, "status": "running", "config": asdict(config),
              "task": task_manifest(envs[0]), "model": {"config": asdict(model_config), "versions": versions,
              "initialization": "checkpoint weights transfer" if transfer else "fresh seeded weights",
              "weights_transfer": transfer, "frozen": True, "training_updates": 0},
              "runtime_source_sha256": source_hashes(), "software": {"python": sys.version.split()[0],
              "torch": torch.__version__, "device": "cpu", "graph_compiler": graph_compiler_backend()},
              "resources": {"cpu_budget": config.cpu_budget, "tensor_threads": torch.get_num_threads(),
              "interop_threads": torch.get_num_interop_threads(), "search_workers": config.roots,
              "coordinators": 2, "conservative_thread_budget": config.threads + config.roots + 2,
              "memory_limit_bytes": config.memory_bytes},
              "preparation": {"policy": BASELINE_VERSION + ":balanced", "roots": [],
              "target": {"round": config.start_round, "nation_index": config.start_nation_index,
                         "nation": nation_order[config.start_nation_index], "phase": config.start_phase,
                         "decision_kind": config.start_decision_kind},
              "national_turn_order": nation_order},
              "waves": [], "samples": [], "decisions": 0, "executed_decisions": 0, "chance_events": 0,
              "timings_seconds": {"initialization": time.perf_counter() - started, "preparation": 0.0,
              "search": 0.0, "inference": 0.0, "search_outside_inference": 0.0, "execution": 0.0},
              "timing_scope": "Inference includes feature assembly and neural evaluation; search outside inference "
                              "includes rules, tree work and synchronization, and is not a pure rules timer.",
              "limits": "Frozen-policy throughput measurements; not evidence of learning or strategic strength.",
              "policy": "Fixed unchanged roots in search mode; episode mode uses visit-policy sampling with root noise",
              "fixed_roots": config.mode == "search"}
    counts: list[Counter] | None = None

    def persist():
        report["elapsed_worker_seconds"] = time.perf_counter() - started
        report["worker_peak_rss_bytes"] = _peak_bytes()
        report["last_clocks"] = [_clock(env) for env in envs]
        report["last_terminal"] = [env.is_terminal() for env in envs]
        report["root_progress"] = [{"index": index, "clock": report["last_clocks"][index],
            "terminal": report["last_terminal"][index],
            "observed_terminal_returns": list(env.returns()) if report["last_terminal"][index] else None,
            **(dict(counts[index]) if counts is not None else
               {"transitions": 0, "decisions": 0, "chance_events": 0})}
            for index, env in enumerate(envs)]
        if progress_path is not None:
            _write(progress_path, report)

    persist()
    preparation_started = time.perf_counter()
    for index, env in enumerate(envs):
        transitions = 0
        visits = Counter({env.planning_key(): 1})
        reason = "reached"
        if config.mode == "search":
            while not env.is_terminal():
                clock = _clock(env)
                target_round = config.start_round - 1
                if (clock["round_index"] == target_round and clock["nation_index"] == config.start_nation_index
                        and clock["phase"] == config.start_phase and env.decision_kind() != "chance"
                        and (config.start_decision_kind is None or env.decision_kind() == config.start_decision_kind)):
                    break
                passed_target_nation = (clock["round_index"] > target_round or
                    (clock["round_index"] == target_round and clock["nation_index"] > config.start_nation_index))
                if passed_target_nation or transitions >= config.preparation_transitions:
                    reason = "preparation_limit"
                    break
                if visits[env.planning_key()] >= config.max_state_visits:
                    reason = "preparation_repetition_limit"
                    break
                if time.perf_counter() - started >= config.seconds:
                    reason = "wall_limit"
                    break
                if env.decision_kind() == "chance":
                    env.resolve_chance()
                else:
                    actions = env.legal_actions()
                    weights = baseline_distribution(env, actions)
                    env.apply_action(actions[max(range(len(actions)), key=weights.__getitem__)])
                transitions += 1
                visits[env.planning_key()] += 1
            if env.is_terminal():
                reason = "terminal_before_target"
        report["preparation"]["roots"].append({"index": index, "seed": config.seed + index,
            "transitions": transitions, "status": reason, "clock": _clock(env), "terminal": env.is_terminal()})
        report["timings_seconds"]["preparation"] = time.perf_counter() - preparation_started
        persist()
        if reason != "reached":
            report["status"] = reason
            persist()
            return report

    actual_snapshots = [env.serialize() for env in envs]
    report["prepared_state_sha256"] = [hashlib.sha256(value.encode()).hexdigest() for value in actual_snapshots]
    replay_writer = None
    replay_capture = None
    if replay_output is not None:
        replay_writer = ReplayTraceWriter(replay_output, {
            "kind": "frozen_policy_benchmark", "config": asdict(config), "task": report["task"],
            "runtime_source_sha256": report["runtime_source_sha256"], "model": report["model"]})
        replay_capture = ReplayTraceCapture(replay_writer)
        for index, env in enumerate(envs):
            replay_capture.remember_seed(env, config.seed + index)
        report["replay_trace"] = str(replay_output.resolve())
    try:
        counts = [Counter(transitions=0, decisions=0, chance_events=0) for _ in envs]
        visits = [Counter({env.planning_key(): 1}) for env in envs]
        search_rngs = [random.Random(config.seed + i ^ 0x9E3779B97F4A7C15) for i in range(len(envs))]
        policy_rngs = [random.Random(config.seed + i ^ 0xD1B54A32D192ED03) for i in range(len(envs))]
        waves = 0

        def record(index, chance):
            counts[index]["transitions"] += 1
            counts[index]["chance_events" if chance else "decisions"] += 1
            report["chance_events" if chance else "executed_decisions"] += 1
            visits[index][envs[index].planning_key()] += 1

        def reason(index):
            env = envs[index]
            if env.is_terminal():
                return "terminal"
            if config.mode == "search":
                return None
            if counts[index]["transitions"] >= config.max_transitions:
                return "transition_limit"
            if visits[index][env.planning_key()] >= config.max_state_visits:
                return "repetition_limit"
            return None

        while True:
            if time.perf_counter() - started >= config.seconds:
                report["status"] = "wall_limit"
                break
            if config.mode == "search" and waves >= config.waves:
                report["status"] = "completed"
                break
            active = [index for index in range(len(envs)) if reason(index) is None]
            if not active:
                report["status"] = "completed" if all(env.is_terminal() for env in envs) else "collection_limit"
                break
            searching, indices = [], []
            for index in active:
                env = envs[index]
                if env.decision_kind() == "chance":
                    before = time.perf_counter()
                    replay = replay_capture.before(env, index) if replay_capture is not None else None
                    planning_before = env.planning_key() if replay is not None else None
                    env.resolve_chance()
                    if replay is not None:
                        replay_capture.after(env, replay, {"kind": "chance", "owner": None, "action": None,
                            "before": planning_before, "after": env.planning_key(), "terminal": env.is_terminal()})
                    report["timings_seconds"]["execution"] += time.perf_counter() - before
                    record(index, True)
                else:
                    actions = env.legal_actions()
                    report["samples"].append({"root": index, "wave": waves, **_sample(env, actions)})
                    searching.append(env)
                    indices.append(index)
            if searching:
                stats = BatchStats()
                configs = [MctsConfig(simulations=config.simulations, max_depth=config.max_depth,
                                     seed=search_rngs[index].getrandbits(64),
                                     search_forced_root=config.mode == "search") for index in indices]
                report["pending_wave"] = {"index": waves, "root_indices": indices,
                                          "search_configs": [asdict(value) for value in configs]}
                persist()
                results = search_many(searching, evaluator, configs=configs, add_root_noise=True, stats=stats)
                report["pending_wave"] = None
                report["timings_seconds"]["search"] += stats.elapsed_seconds
                report["timings_seconds"]["inference"] += stats.inference_seconds
                report["timings_seconds"]["search_outside_inference"] += max(0.0, stats.elapsed_seconds - stats.inference_seconds)
                report["waves"].append({"index": waves, "root_indices": indices,
                    "cache_temperature": "cold_first_search" if waves == 0 else "warm_feature_caches",
                    "search_configs": [asdict(value) for value in configs], "add_root_noise": True, **asdict(stats)})
                report["decisions"] += sum(result.values is not None for result in results)
                before = time.perf_counter()
                if config.mode == "episode":
                    for index, result in zip(indices, results, strict=True):
                        chosen = policy_rngs[index].choices(result.actions, weights=result.policy, k=1)[0]
                        env = envs[index]
                        replay = replay_capture.before(env, index) if replay_capture is not None else None
                        if replay is not None:
                            menu = [action.features() if hasattr(action, "features") else dict(action)
                                    for action in result.actions]
                            selected_index = next(i for i, action in enumerate(result.actions) if action is chosen)
                            replay.update(selected_index=selected_index, selected_action=menu[selected_index], decision_menu=menu,
                                search={"visit_counts": result.visit_counts, "priors": result.priors,
                                        "policy": result.policy, "sampling_policy": result.policy,
                                        "values": None if result.values is None else list(result.values),
                                        "action_values": result.action_values,
                                        "simulations": config.simulations, "max_depth": config.max_depth,
                                        "rollout_version": evaluator.version})
                            event = {"kind": env.decision_kind(), "owner": env.current_decision_player(),
                                     "action": action_key(chosen), "before": env.planning_key()}
                        env.apply_action(chosen)
                        if replay is not None:
                            event.update(after=env.planning_key(), terminal=env.is_terminal())
                            replay_capture.after(env, replay, event)
                        record(index, False)
                else:
                    report["actual_state_and_rng_unchanged"] = all(env.serialize() == snapshot
                        for env, snapshot in zip(envs, actual_snapshots, strict=True))
                    if not report["actual_state_and_rng_unchanged"]:
                        raise RuntimeError("A fixed-root search changed an actual state or execution RNG")
                report["timings_seconds"]["execution"] += time.perf_counter() - before
                waves += 1
            persist()

        report["roots"] = [{"index": index, "clock": _clock(env), "terminal": env.is_terminal(),
                            "stop_reason": reason(index) or report["status"], **dict(counts[index]),
                            "observed_terminal_returns": list(env.returns()) if env.is_terminal() else None}
                           for index, env in enumerate(envs)]
        report["search_decisions_per_second"] = report["decisions"] / report["timings_seconds"]["search"] if report["timings_seconds"]["search"] else None
        persist()
        if replay_writer is not None:
            replay_writer({"type": "run_end", "status": report["status"], "roots": report["roots"]})
        return report
    finally:
        if replay_writer is not None:
            replay_writer.close()


def supervise(config: BenchmarkConfig, output: Path, *, record_replay: bool = False,
              worker_prefix: list[str] | None = None) -> dict:
    """Enforce a wall deadline even if native code or an inference call stalls."""
    replay_output = output.with_suffix(".replay.jsonl") if record_replay else None
    if record_replay and config.mode != "episode":
        raise ValueError("Replay recording requires episode mode with real executed choices")
    if output.exists() or (replay_output is not None and replay_output.exists()):
        raise ValueError("Choose a new output file; existing benchmark results are preserved")
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    peak = 0
    stopped = None
    with tempfile.TemporaryDirectory(prefix="campaign-scaling-") as temporary:
        directory = Path(temporary)
        settings, progress = directory / "config.json", directory / "progress.json"
        _write(settings, asdict(config))
        environment = {**os.environ, "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": str(config.threads),
                       "MKL_NUM_THREADS": str(config.threads), "OPENBLAS_NUM_THREADS": "1",
                       "VECLIB_MAXIMUM_THREADS": str(config.threads), "NUMEXPR_NUM_THREADS": "1"}
        with (directory / "stdout").open("w") as stdout, (directory / "stderr").open("w") as stderr:
            prefix = worker_prefix or [sys.executable, "-m", "studies.campaign.scaling_benchmark"]
            process = subprocess.Popen([*prefix,
                "--_worker", str(settings), "--output", str(progress),
                *(["--replay-output", str(replay_output)] if replay_output is not None else [])], env=environment,
                stdout=stdout, stderr=stderr)
            try:
                while process.poll() is None:
                    if time.monotonic() - started >= config.seconds:
                        stopped = "wall_limit"
                        break
                    try:
                        resident = _rss_bytes(os.getpid()) + _rss_bytes(process.pid)
                    except (ProcessLookupError, OSError, ValueError, subprocess.TimeoutExpired):
                        if process.poll() is not None:
                            break
                        stopped = "memory_monitor_failure"
                        break
                    peak = max(peak, resident)
                    if resident >= config.memory_bytes - MEMORY_MARGIN_BYTES:
                        stopped = "memory_limit"
                        break
                    time.sleep(0.1)
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
        report = json.loads(progress.read_text()) if progress.exists() else {"schema": SCHEMA, "config": asdict(config)}
        if stopped is not None:
            report["status"] = stopped
        elif process.returncode != 0:
            report["status"] = "worker_error"
        report["watchdog"] = {"elapsed_seconds": time.monotonic() - started,
            "aggregate_sampled_peak_rss_bytes": peak, "memory_limit_bytes": config.memory_bytes,
            "memory_stop_threshold_bytes": config.memory_bytes - MEMORY_MARGIN_BYTES,
            "poll_interval_seconds": 0.1, "scope": "Supervisor and single worker RSS; worker search uses threads, no subprocesses",
            "limitation": "Sampled RSS with a safety margin, not a kernel-enforced instantaneous limit",
            "worker_returncode": process.returncode, "last_progress_preserved": progress.exists()}
        if process.returncode != 0 and stopped is None:
            report["worker_error"] = (directory / "stderr").read_text()[-8000:]
        _write(output, report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--record-replay", action="store_true", help="Write an adjacent .replay.jsonl for real episode choices")
    parser.add_argument("--replay-output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--mode", choices=("search", "episode"), default="search")
    parser.add_argument("--full-campaign", action="store_true")
    for name, default in asdict(BenchmarkConfig()).items():
        if name in {"mode", "seconds"}:
            continue
        parser.add_argument("--" + name.replace("_", "-"),
                            type=str if name in {"start_phase", "start_decision_kind", "checkpoint_weights"} else int,
                            default=default)
    parser.add_argument("--seconds", type=float, default=60.0)
    args = parser.parse_args(argv)
    if args._worker:
        run_case(BenchmarkConfig(**json.loads(args._worker.read_text())), args.output, replay_output=args.replay_output)
        return 0
    values = {name: getattr(args, name) for name in asdict(BenchmarkConfig())}
    if args.full_campaign:
        values["calendar_rounds"] = None
    try:
        report = supervise(BenchmarkConfig(**values), args.output.resolve(), record_replay=args.record_replay)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output.resolve()), "status": report["status"],
                      "decisions": report.get("decisions", 0), "watchdog": report["watchdog"]}), flush=True)
    return 1 if report["status"] in {"worker_error", "memory_monitor_failure"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
