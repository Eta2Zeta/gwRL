#!/usr/bin/env python3
"""Compare one genuine four-game learning batch in two frozen runtimes.

The existing foreground runner owns collection, Adam, saving and restoration.
The existing scaling supervisor owns CPU, RSS and wall guards. This wrapper
adds matched-result fingerprints; it never changes rules, search or learning.
Run old and new invocations sequentially, never alongside another heavy job.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
from dataclasses import asdict
from functools import wraps
import hashlib
import json
from pathlib import Path
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "campaign-numeric-learning-benchmark-v1"


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(value):
    """A type-tagged logical digest, independent of pickle storage or addresses."""
    import numpy as np
    import torch

    digest = hashlib.sha256()

    def block(tag, data):
        digest.update(tag + struct.pack("<Q", len(data)) + data)

    def visit(item):
        if isinstance(item, torch.Tensor):
            tensor = item.detach().cpu().contiguous()
            block(b"T", str(tensor.dtype).encode())
            visit(tuple(tensor.shape))
            block(b"B", tensor.reshape(-1).view(torch.uint8).numpy().tobytes())
        elif isinstance(item, np.ndarray):
            block(b"A", item.dtype.str.encode())
            visit(tuple(item.shape))
            block(b"B", np.ascontiguousarray(item).tobytes())
        elif isinstance(item, np.generic):
            visit(item.item())
        elif item is None:
            digest.update(b"N")
        elif isinstance(item, bool):
            digest.update(b"Y" if item else b"Z")
        elif isinstance(item, int):
            block(b"I", str(item).encode())
        elif isinstance(item, float):
            digest.update(b"F" + struct.pack("<d", item))
        elif isinstance(item, str):
            block(b"S", item.encode("utf-8"))
        elif isinstance(item, dict):
            digest.update(b"D" + struct.pack("<Q", len(item)))
            for key in sorted(item, key=lambda key: (type(key).__name__, repr(key))):
                visit(key)
                visit(item[key])
        elif isinstance(item, (tuple, list)):
            digest.update((b"U" if isinstance(item, tuple) else b"L") + struct.pack("<Q", len(item)))
            for child in item:
                visit(child)
        else:
            raise TypeError(f"Unsupported logical fingerprint value: {type(item).__name__}")

    visit(value)
    return digest.hexdigest()


def graph_digest(graph, buckets):
    """Normalize old tuple graphs and native arrays into identical numeric data."""
    import numpy as np

    if hasattr(graph, "arrays"):
        packed = graph.packed_state()
        arrays = graph.arrays()
        identities, references = packed["identities"], packed["references"]
    else:
        sources, targets, relations = zip(*graph.edges) if graph.edges else ((), (), ())
        arrays = {"token_ids": np.asarray(graph.token_ids, dtype=np.int64),
                  "token_offsets": np.asarray(graph.token_offsets, dtype=np.int64),
                  "types": np.asarray(graph.types, dtype=np.int64),
                  "numeric": np.asarray(graph.numeric, dtype=np.float64),
                  "sources": np.asarray(sources, dtype=np.int64),
                  "targets": np.asarray(targets, dtype=np.int64),
                  "relations": np.asarray(relations, dtype=np.int64)}
        identities, references = graph.identities, graph.references
    return tree_digest({"arrays": arrays, "identities": identities, "references": references,
                        "leaf_count": graph.leaf_count, "buckets": buckets})


def replay_graph_digest(samples, buckets):
    """Post-timing verification of every retained input, with bounded graph reuse."""
    from studies.campaign import features

    # Retain at most 32 MB of small compiled legacy action graphs. Static
    # contexts are hashed once. Observation graphs are consumed immediately.
    context_cache, action_cache = {}, OrderedDict()
    action_bytes = 0
    output = hashlib.sha256()

    def action_digest(serialized):
        nonlocal action_bytes
        if serialized in action_cache:
            action_cache.move_to_end(serialized)
            return action_cache[serialized][0]
        value = graph_digest(features.compile_graph(json.loads(serialized), buckets), buckets)
        size = len(serialized.encode()) + len(value)
        if size <= 32 * 1024**2:
            while action_cache and action_bytes + size > 32 * 1024**2:
                _, (_, removed_size) = action_cache.popitem(last=False)
                action_bytes -= removed_size
            action_cache[serialized] = (value, size)
            action_bytes += size
        return value

    for sample in samples:
        item = sample["input"]
        if item["schema"] == "campaign-numeric-input-v1":
            packed = item["packed_graph"]
            context_key = item["context_key"]
            if context_key not in context_cache:
                context_cache[context_key] = graph_digest(packed["context"], buckets)
            observation = graph_digest(packed["observation"], buckets)
            actions = tuple(graph_digest(graph, buckets) for graph in packed["actions"])
            factors = tuple(tuple(factor) for factor in packed["action_factors"])
        else:
            context_key = features.canonical(item["context"])
            if context_key not in context_cache:
                context_cache[context_key] = graph_digest(
                    features.compile_graph(json.loads(context_key), buckets), buckets)
            observation = graph_digest(features.compile_graph(
                json.loads(features.canonical(item["observation"])), buckets), buckets)
            actions = tuple(action_digest(features.canonical(action)) for action in item["actions"])
            factors = tuple(features.action_factors(action) for action in item["actions"])
        output.update(bytes.fromhex(tree_digest({"context": context_cache[context_key],
            "observation": observation, "actions": actions, "action_factors": factors})))
    return {"rows": len(samples), "sha256": output.hexdigest(),
            "scope": "Every retained row's complete ordered numeric graph, exact reference metadata and action factors; source JSON transport is normalized."}


def learner_core(learner):
    import random
    import numpy as np
    import torch

    sample_metadata = [{key: value for key, value in sample.items() if key != "input"}
                       for sample in learner.replay]
    return {"metadata": learner._metadata(), "generation": learner.generation,
        "counters": learner.counters.copy(), "model_versions": learner.model_versions(),
        "model_tensor_sha256": tree_digest({player: model.state_dict() for player, model in learner.models.items()}),
        "adam_sha256": tree_digest({player: optimizer.state_dict() for player, optimizer in learner.optimizers.items()}),
        "action_history_count": len(learner.action_history), "action_history_sha256": tree_digest(learner.action_history),
        "replay_rows": len(learner.replay), "replay_targets_policy_provenance_sha256": tree_digest(sample_metadata),
        "final_engine_state_and_rng_sha256": [hashlib.sha256(env.serialize().encode()).hexdigest()
                                               for env in learner.parallel_envs],
        "terminal": [env.is_terminal() for env in learner.parallel_envs],
        "terminal_returns": [list(env.returns()) if env.is_terminal() else None for env in learner.parallel_envs],
        "pending_rows": [len(rows) for rows in learner.parallel_pending],
        "batch_records": len(learner.batch_records), "frozen": learner.frozen_models is not None,
        "random_states_sha256": tree_digest({"python": random.getstate(), "numpy": np.random.get_state(),
            "torch": torch.get_rng_state(), "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            "mps": None, "policy": learner.policy_random.getstate(), "search": learner.search_random.getstate(),
            "replay": learner.replay_random.getstate(), "environment": learner.environment_random.getstate()})}


def worker(args):
    runtime = args.runtime.resolve()
    sys.path.insert(0, str(runtime))
    import torch
    import gwrl_cpp
    from studies.campaign import batching, run
    from studies.campaign.scaling_benchmark import BenchmarkConfig, _peak_bytes, _write
    from studies.shared.multiplayer_mcts import action_key

    native_path = Path(gwrl_cpp.__file__).resolve()
    if not native_path.is_relative_to(runtime) or not Path(run.__file__).resolve().is_relative_to(runtime):
        raise RuntimeError("Selected runtime must supply its own Python code and native extension")
    config = BenchmarkConfig(**json.loads(args._worker.read_text()))
    if (config.mode != "episode" or config.roots != 4 or config.calendar_rounds != 3 or
            config.seed != 1951 or config.simulations != 16 or config.max_depth != 16 or
            config.hidden_dim != 16 or config.message_layers != 1 or config.token_buckets != 2048 or config.threads != 4):
        raise ValueError("This matched pilot requires the documented unchanged four-game settings")
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    values = dict(seed=config.seed, calendar_rounds=3, batches=1, transitions_per_batch=5000,
        parallel_envs=4, simulations=16, max_depth=16, hidden_dim=16, message_layers=1,
        token_buckets=2048, value_scale=100., batch_size=32, epochs=16, learning_rate=.001,
        replay_capacity=16384, threads=4, checkpoint_every_waves=None,
        checkpoint_interval_seconds=1800., complete_episodes=True, max_episodes=4, cpu_budget=11)
    run_config = run.RunConfig(**values)
    train_args = argparse.Namespace(**values, run_dir=args.run_dir, resume=None,
        full_campaign=False, stop_after_waves=None, extend_episode_budget=None, record_replay=False)
    report = {"schema": SCHEMA, "status": "initializing", "config": asdict(config),
        "run_config": asdict(run_config), "run_dir": str(args.run_dir),
        "provenance": {"runtime": str(runtime), "declared_source_commit": args.source_commit,
            "runtime_source_sha256": run.source_hashes(), "native_extension": str(native_path),
            "native_sha256": file_digest(native_path), "wrapper_sha256": file_digest(__file__)},
        "limits": "Matched implementation/continuation pilot, not a playing-strength evaluation."}
    _write(args.output, report)
    captured, step_calls = [], {}
    original_learner, original_search = run._learner, batching.search_many
    original_report = run._json
    search_digest = hashlib.sha256()
    search_count, fingerprint_seconds = 0, 0.

    def capture(config, template):
        learner = original_learner(config, template)
        report["initial_model_versions"] = learner.model_versions()
        for player, optimizer in learner.optimizers.items():
            step_calls[player] = 0
            original_step = optimizer.step

            @wraps(original_step)
            def step(*a, _player=player, _original=original_step, **kw):
                result = _original(*a, **kw)
                step_calls[_player] += 1
                return result

            optimizer.step = step
        captured.append(learner)
        return learner

    def search(*a, **kw):
        nonlocal search_count, fingerprint_seconds
        results = original_search(*a, **kw)
        before = time.perf_counter()
        for result in results:
            search_digest.update(json.dumps({"actions": [action_key(action) for action in result.actions],
                "visits": result.visit_counts, "policy": result.policy, "priors": result.priors,
                "values": result.values, "action_values": result.action_values},
                sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
            search_count += 1
        fingerprint_seconds += time.perf_counter() - before
        return results

    def progress(path, value):
        original_report(path, value)
        report.update(status="running", last_runner_status=value.get("status"),
                      counters=value.get("counters"), training_manifest=str(path))
        _write(args.output, report)

    run._learner, batching.search_many, run._json = capture, search, progress
    before = time.perf_counter()
    status = run.train(train_args)
    training_wall = time.perf_counter() - before
    learner = captured[0]
    manifest = json.loads((args.run_dir / "manifest.json").read_text())
    core = learner_core(learner)
    report.update(status="verifying" if status == 0 else manifest["status"],
        training_returncode=status, training_wall_seconds=training_wall,
        training_worker_peak_rss_bytes=_peak_bytes(),
        runner_timings_seconds=manifest["timings_seconds_this_invocation"],
        checkpoint_saves=manifest["checkpoint_saves_this_invocation"],
        model_exports=manifest["model_exports_this_invocation"],
        training_environment_seeds=manifest["runner"]["training_environment_seeds"],
        task=manifest["runner"]["task"], updates=manifest["runner"]["updates"],
        adam_step_calls=step_calls, logical_core=core,
        search={"count": search_count, "sha256": search_digest.hexdigest(),
                "fingerprinting_seconds_in_collection": fingerprint_seconds})
    _write(args.output, report)
    if status != 0:
        return
    checks = {"four_terminal_episodes": core["counters"]["episodes"] == 4 and core["terminal"] == [True] * 4,
        "one_update": core["generation"] == core["counters"]["updates"] == 1,
        "sixteen_adam_calls_per_actor": all(value == 16 for value in step_calls.values()),
        "no_bootstrap_samples": all(update["rollout"]["bootstrap_samples"] == 0 for update in report["updates"]),
        "no_unfinished_examples": not core["frozen"] and not core["batch_records"] and not any(core["pending_rows"])}
    before = time.perf_counter()
    report["replay_feature_graphs"] = replay_graph_digest(learner.replay, config.token_buckets)
    report["verification_graph_digest_seconds"] = time.perf_counter() - before
    before = time.perf_counter()
    checkpoint = run._read(args.run_dir / "checkpoint.pt")
    report["checkpoint_load_seconds"] = time.perf_counter() - before
    before = time.perf_counter()
    template = run.make_env(config.seed, calendar_rounds=3)
    restored = original_learner(run_config, template)
    restored.restore(checkpoint["learner"], env_template=template)
    report["checkpoint_reconstruction_seconds"] = time.perf_counter() - before
    restored_core = learner_core(restored)
    checks["validated_restore_exact_logical_core"] = restored_core == core
    report["restored_logical_core_sha256"] = tree_digest(restored_core)
    report["logical_checkpoint_sha256"] = tree_digest({"core": core,
        "replay_feature_graphs": report["replay_feature_graphs"]})
    report["physical_checkpoint"] = {"path": str(args.run_dir / "checkpoint.pt"),
        "bytes": (args.run_dir / "checkpoint.pt").stat().st_size,
        "sha256": file_digest(args.run_dir / "checkpoint.pt"),
        "scope": "Physical pickle/array layout differs between runtimes; this hash is provenance, not cross-format parity."}
    report["checks"] = checks
    report["worker_peak_rss_bytes"] = _peak_bytes()
    report["status"] = "completed" if all(checks.values()) else "verification_failed"
    _write(args.output, report)


def compare_reports(actual, reference):
    fields = {"completed": actual.get("status") == reference.get("status") == "completed"}
    for key in ("config", "run_config", "initial_model_versions", "training_environment_seeds", "task",
                "updates", "adam_step_calls", "logical_core", "replay_feature_graphs", "logical_checkpoint_sha256"):
        fields[key] = key in actual and key in reference and actual[key] == reference[key]
    for key in ("count", "sha256"):
        first, second = actual.get("search", {}), reference.get("search", {})
        fields["search_" + key] = key in first and key in second and first[key] == second[key]
    wrapper = actual.get("provenance", {}).get("wrapper_sha256")
    fields["same_wrapper"] = isinstance(wrapper, str) and wrapper == reference.get("provenance", {}).get("wrapper_sha256")
    matched = all(fields.values())
    return {"matched": matched, "checks": fields,
        "reference_training_wall_seconds": reference.get("training_wall_seconds"),
        "actual_training_wall_seconds": actual.get("training_wall_seconds"),
        "training_speedup_if_matched": reference["training_wall_seconds"] / actual["training_wall_seconds"] if matched else None,
        "scope": "Training wall includes initialization, complete collection, real update, normal saves/exports/reporting and search fingerprinting; post-run graph verification/load/restore are separate."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=ROOT)
    parser.add_argument("--source-commit", help="Frozen source revision label; actual source/binary hashes are also recorded")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    args.run_dir = args.run_dir.resolve()
    if args._worker:
        worker(args)
        return 0
    if args.config is None:
        parser.error("Supply a scaling BenchmarkConfig JSON with --config")
    if args.run_dir.exists() and any(args.run_dir.iterdir()):
        parser.error("Choose a new empty training directory")
    sys.path.insert(0, str(ROOT))
    from studies.campaign.scaling_benchmark import BenchmarkConfig, _write, supervise
    config = BenchmarkConfig(**json.loads(args.config.read_text()))
    prefix = [sys.executable, str(Path(__file__).resolve()), "--runtime", str(args.runtime.resolve()),
              "--run-dir", str(args.run_dir)]
    if args.source_commit:
        prefix.extend(["--source-commit", args.source_commit])
    report = supervise(config, args.output.resolve(), worker_prefix=prefix)
    report["run_dir"] = str(args.run_dir)
    if args.compare_to:
        report["comparison"] = compare_reports(report, json.loads(args.compare_to.read_text()))
    _write(args.output.resolve(), report)
    print(json.dumps({"output": str(args.output.resolve()), "status": report["status"],
                      "comparison": report.get("comparison"), "training_wall_seconds": report.get("training_wall_seconds")}), flush=True)
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
