"""Bounded, inference-only profiling of a real Japan Combat Movement root.

The parent supervises one fresh worker so an unresponsive native call cannot
escape the wall deadline. Resident memory is sampled, with a 128 MiB margin;
this is not a kernel-enforced instantaneous allocation limit. No engine or
training checkpoint is changed. Outputs are diagnostic JSON and cProfile data.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def repository_root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents
                if (parent / "studies/campaign/evaluation.py").is_file())


ROOT = repository_root()
MEMORY_BYTES = 30_000_000_000
MEMORY_MARGIN_BYTES = 128 * 1024**2


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".profile-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def rss_bytes(pid: int) -> int:
    result = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)],
                            capture_output=True, text=True, timeout=0.5)
    if result.returncode or not result.stdout.strip():
        raise ProcessLookupError(f"Cannot inspect process {pid} resident memory")
    return int(result.stdout.strip()) * 1024


def worker(args) -> dict:
    sys.path.insert(0, str(ROOT))
    report = {"schema": "campaign-fixed-position-diagnostic-v1", "status": "initializing",
              "resources": {"cpu_budget": 12, "tensor_threads": 4, "serial_searches": 1,
                            "conservative_thread_budget": 7, "memory_limit_bytes": MEMORY_BYTES},
              "training_updates": 0, "profiles": {}}
    progress = args.output_dir / "progress.json"
    write_json(progress, report)
    import cProfile
    from collections import Counter
    from dataclasses import asdict
    import pstats
    import random

    import numpy as np
    import torch
    from studies.campaign.baselines import BASELINE_VERSION, baseline_distribution, raw_action
    from studies.campaign.curriculum import make_env, task_manifest
    from studies.campaign.evaluation import profile
    from studies.campaign.features import graph_compiler_backend
    from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
    from studies.campaign.run import source_hashes
    from studies.shared.multiplayer_mcts import MctsConfig, PLAYERS, VectorMCTS

    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    random.seed(args.seed)
    np.random.seed(args.seed % 2**32)
    torch.manual_seed(args.seed)
    report["software"] = {"python": sys.version.split()[0], "torch": torch.__version__, "device": "cpu",
                          "graph_compiler": graph_compiler_backend()}
    report["resources"]["interop_threads"] = torch.get_num_interop_threads()
    report["runtime_source_sha256"] = source_hashes()
    report["diagnostic_source_sha256"] = digest(Path(__file__).resolve())
    reference = json.loads(args.matched_report.read_text()) if args.matched_report else None
    if reference is not None:
        if reference["config"]["seed"] != args.seed or reference["config"]["calendar_rounds"] is not None:
            raise ValueError("Matched report must use the same seed and the full campaign")
        report["matched_report"] = {"path": str(args.matched_report), "sha256": digest(args.matched_report)}

    report["status"] = "preparing_position"
    write_json(progress, report)
    env = make_env(args.seed, calendar_rounds=None)
    preparation_started = time.perf_counter()
    visits = Counter({env.planning_key(): 1})
    transitions = 0
    while not env.is_terminal():
        clock = env.observation()["state"]["clock"]
        if (clock["round_index"] == 0 and clock["nation_index"] == 2
                and clock["phase"] == "combat_movement" and env.decision_kind() == "combat_movement"):
            break
        if transitions >= 10000 or visits[env.planning_key()] >= 12:
            raise RuntimeError("Scripted preparation reached its transition or repetition limit")
        if clock["round_index"] > 0 or clock["nation_index"] > 2:
            raise RuntimeError("Scripted preparation passed the requested Japan position")
        if env.decision_kind() == "chance":
            env.resolve_chance()
        else:
            actions = env.legal_actions()
            weights = baseline_distribution(env, actions)
            env.apply_action(actions[max(range(len(actions)), key=weights.__getitem__)])
        transitions += 1
        visits[env.planning_key()] += 1
    if env.is_terminal():
        raise RuntimeError("Campaign ended before the requested position")
    actual = env.serialize()
    actual_sha = hashlib.sha256(actual.encode()).hexdigest()
    actions = env.legal_actions()
    report["position"] = {"seed": args.seed, "task": task_manifest(env),
                          "clock": dict(env.observation()["state"]["clock"]),
                          "decision_kind": env.decision_kind(), "actor": env.current_decision_player(),
                          "planning_key": env.planning_key(), "prepared_state_sha256": actual_sha,
                          "legal_menu_size": len(actions),
                          "legal_menu_kinds": dict(Counter(raw_action(action)["kind"] for action in actions)),
                          "preparation_policy": BASELINE_VERSION + ":balanced",
                          "preparation_transitions": transitions,
                          "preparation_seconds": time.perf_counter() - preparation_started}
    if reference is not None:
        expected = reference["prepared_state_sha256"][0]
        report["position"]["matched_first_root_sha256"] = expected
        if actual_sha != expected:
            raise RuntimeError(f"Prepared position mismatch: actual {actual_sha}, expected {expected}")
        report["position"]["matched_first_root"] = True
    write_json(progress, report)

    checkpoint_before = digest(args.checkpoint_weights)
    payload = torch.load(args.checkpoint_weights, map_location="cpu", weights_only=False)
    if payload.get("schema") != "campaign-foreground-run-v1":
        raise ValueError("Expected a trusted local foreground-run checkpoint")
    model_config = CampaignModelConfig(**payload["learner"]["metadata"]["model_config"])
    if (model_config.hidden_dim, model_config.message_layers, model_config.token_buckets) != (16, 1, 2048):
        raise ValueError("Pilot checkpoint must contain the intended 16-wide, one-layer, 2048-bucket architecture")
    weights = payload["learner"]["models"]
    if set(weights) != set(PLAYERS):
        raise ValueError("Checkpoint must contain exactly the three campaign players")
    models = {player: CampaignPolicyValueNet(model_config).eval() for player in PLAYERS}
    for player, model in models.items():
        model.load_state_dict(weights[player], strict=True)
    source_compatibility = payload["learner"]["metadata"]["compatibility"]
    del weights, payload

    def model_versions(items):
        return {player: hashlib.sha256(b"".join(value.detach().cpu().numpy().tobytes()
                    for value in model.state_dict().values())).hexdigest()
                for player, model in items.items()}

    def make_evaluator(items):
        versions = model_versions(items)
        version = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
        return NeuralEvaluator(items, version=version), versions

    evaluator, small_versions = make_evaluator(models)
    report["models"] = {"pilot": {"config": asdict(model_config), "versions": small_versions,
                         "initialization": "checkpoint model weights only", "frozen": True,
                         "source": str(args.checkpoint_weights), "source_sha256": checkpoint_before,
                         "source_compatibility": source_compatibility}}
    if reference is not None and reference["model"]["versions"] != small_versions:
        raise RuntimeError("Pilot model weights differ from the matched timing report")
    report["status"] = "profiling_pilot_operations"
    write_json(progress, report)
    report["profiles"]["pilot_operations"] = profile([env], evaluator, repeats=3)
    if env.serialize() != actual:
        raise RuntimeError("Pilot operation profile mutated actual state or execution RNG")
    write_json(progress, report)

    search_seed = args.search_seed
    if search_seed is None:
        if reference is not None:
            search_seed = reference["waves"][0]["search_configs"][0]["seed"]
        else:
            search_seed = random.Random(args.seed ^ 0x9E3779B97F4A7C15).getrandbits(64)
    config = MctsConfig(simulations=16, max_depth=16, seed=search_seed, mode="multiplayer", record_trace=True,
                        search_forced_root=True)
    report["status"] = "profiling_serial_search"
    report["serial_search"] = {"config": asdict(config), "add_root_noise": True,
                              "cache_scope": "Root features warmed by three operation-profile repeats; descendants first-use",
                              "note": "Serial cProfile timings include profiler overhead and are not batched throughput estimates"}
    write_json(progress, report)
    profiler = cProfile.Profile()
    search_started = time.perf_counter()
    try:
        profiler.enable()
        result = VectorMCTS(evaluator, config).search(env, add_root_noise=True)
    finally:
        profiler.disable()
        profiler.dump_stats(str(args.output_dir / "search.prof"))
    elapsed = time.perf_counter() - search_started
    stats = pstats.Stats(profiler)
    rows = [{"file": file, "line": line, "function": function, "primitive_calls": values[0],
             "calls": values[1], "self_seconds": values[2], "cumulative_seconds": values[3]}
            for (file, line, function), values in stats.stats.items()]
    report["serial_search"].update({"wall_seconds": elapsed, "actual_state_and_rng_unchanged": env.serialize() == actual,
        "total_calls": stats.total_calls, "primitive_calls": stats.prim_calls,
        "profile_self_seconds": stats.total_tt,
        "profile_wall_time_fully_accounted": abs(stats.total_tt - elapsed) <= max(0.05, elapsed * 0.1),
        "profile_accounting_note": "Compare recorded self-time with search wall time before attributing costs. "
                                   "If they differ materially, profiler rows are partial diagnostics; "
                                   "use the separate operation wall timers rather than percentages of total search.",
        "top20_cumulative": sorted(rows, key=lambda row: row["cumulative_seconds"], reverse=True)[:20],
        "top20_self": sorted(rows, key=lambda row: row["self_seconds"], reverse=True)[:20],
        "visit_count_sum": sum(result.visit_counts), "values": list(result.values),
        "simulation_depth_histogram": dict(Counter(len(simulation.selections) for simulation in result.simulations)),
        "simulation_leaf_sources": dict(Counter(simulation.leaf_source for simulation in result.simulations)),
        "selected_action": raw_action(result.best_action()), "actual_actions_executed": 0})
    if not report["serial_search"]["actual_state_and_rng_unchanged"]:
        raise RuntimeError("Serial search mutated actual state or execution RNG")
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).sort_stats("cumulative").print_stats(20)
    (args.output_dir / "search-top20.txt").write_text(stream.getvalue())
    write_json(progress, report)

    torch.manual_seed(args.seed)
    large_config = CampaignModelConfig(hidden_dim=64, message_layers=2, token_buckets=16384)
    large_models = {player: CampaignPolicyValueNet(large_config).eval() for player in PLAYERS}
    large_evaluator, large_versions = make_evaluator(large_models)
    report["models"]["larger"] = {"config": asdict(large_config), "versions": large_versions,
                                   "initialization": "fresh weights seeded identically to the matrix", "frozen": True}
    report["status"] = "profiling_larger_operations"
    write_json(progress, report)
    report["profiles"]["larger_operations"] = profile([env], large_evaluator, repeats=3)
    report["actual_state_and_rng_unchanged"] = env.serialize() == actual
    report["model_weights_unchanged"] = (model_versions(models) == small_versions
                                         and model_versions(large_models) == large_versions)
    report["source_checkpoint_unchanged"] = digest(args.checkpoint_weights) == checkpoint_before
    if not all(report[name] for name in ("actual_state_and_rng_unchanged", "model_weights_unchanged", "source_checkpoint_unchanged")):
        raise RuntimeError("Diagnostics mutated actual state, execution RNG, frozen weights or source checkpoint")
    report["status"] = "completed"
    report["limits"] = ["Frozen inference-only timing, not training or a claim of strategic strength.",
                        "Operation profile compares the same real menu; first calls include token parsing.",
                        "Cumulative profiler rows overlap and must not be added together.",
                        "Native engine/PyTorch internals appear at their Python-call boundaries.",
                        "Single-root serial profiling does not measure independent-root batching efficiency."]
    write_json(progress, report)
    return report


def supervise(args) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any(args.output_dir.iterdir()):
        raise ValueError("Choose an empty output directory; existing diagnostic results are preserved")
    environment = {**os.environ, "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4",
                   "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "4", "NUMEXPR_NUM_THREADS": "1"}
    command = [sys.executable, str(Path(__file__).resolve()), "--_worker", "--output-dir", str(args.output_dir),
               "--checkpoint-weights", str(args.checkpoint_weights), "--seed", str(args.seed)]
    if args.matched_report:
        command.extend(["--matched-report", str(args.matched_report)])
    if args.search_seed is not None:
        command.extend(["--search-seed", str(args.search_seed)])
    started = time.monotonic()
    stopped = None
    peak = 0
    with (args.output_dir / "worker.stdout").open("w") as stdout, (args.output_dir / "worker.stderr").open("w") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr)
        try:
            while process.poll() is None:
                if time.monotonic() - started >= args.seconds:
                    stopped = "wall_limit"
                    break
                try:
                    resident = rss_bytes(os.getpid()) + rss_bytes(process.pid)
                except (ProcessLookupError, OSError, ValueError, subprocess.TimeoutExpired):
                    if process.poll() is not None:
                        break
                    stopped = "memory_monitor_failure"
                    break
                peak = max(peak, resident)
                if resident >= MEMORY_BYTES - MEMORY_MARGIN_BYTES:
                    stopped = "memory_limit"
                    break
                time.sleep(0.1)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
    progress = args.output_dir / "progress.json"
    report = json.loads(progress.read_text()) if progress.exists() else {"schema": "campaign-fixed-position-diagnostic-v1"}
    if stopped is not None:
        report["status"] = stopped
    elif process.returncode:
        report["status"] = "worker_error"
        report["worker_error"] = (args.output_dir / "worker.stderr").read_text()[-8000:]
    report["watchdog"] = {"elapsed_seconds": time.monotonic() - started,
        "wall_limit_seconds": args.seconds, "aggregate_sampled_peak_rss_bytes": peak,
        "memory_limit_bytes": MEMORY_BYTES, "memory_stop_threshold_bytes": MEMORY_BYTES - MEMORY_MARGIN_BYTES,
        "poll_interval_seconds": 0.1, "worker_returncode": process.returncode,
        "scope": "Supervisor and one worker; serial search, CPU-only model inference",
        "limitation": "Sampled RSS with a safety margin, not an instantaneous kernel allocation cap"}
    write_json(args.output_dir / "report.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--checkpoint-weights", type=Path, required=True)
    parser.add_argument("--matched-report", type=Path)
    parser.add_argument("--seed", type=int, default=1951)
    parser.add_argument("--search-seed", type=int)
    parser.add_argument("--seconds", type=float, default=90.0)
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    import math
    if not math.isfinite(args.seconds) or not 0 < args.seconds <= 90:
        parser.error("Wall allowance must be finite and between zero and 90 seconds")
    if not 0 <= args.seed < 2**64 or args.search_seed is not None and not 0 <= args.search_seed < 2**64:
        parser.error("Seeds must fit unsigned 64-bit integers")
    if (os.cpu_count() or 1) < 7:
        parser.error("This four-thread diagnostic requires at least seven available logical cores")
    args.output_dir = args.output_dir.resolve()
    args.checkpoint_weights = args.checkpoint_weights.resolve()
    if not args.checkpoint_weights.is_file():
        parser.error("The trusted local source checkpoint must exist")
    if args.matched_report:
        args.matched_report = args.matched_report.resolve()
        if not args.matched_report.is_file():
            parser.error("Matched timing report must exist")
    if args._worker:
        worker(args)
        return 0
    try:
        report = supervise(args)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output_dir / "report.json"), "status": report["status"],
                      "position": report.get("position"), "watchdog": report["watchdog"]}, sort_keys=True), flush=True)
    if "serial_search" in report and "top20_cumulative" in report["serial_search"]:
        print((args.output_dir / "search-top20.txt").read_text(), flush=True)
        print(json.dumps({"operation_profiles": report["profiles"]}, sort_keys=True), flush=True)
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
