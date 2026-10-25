#!/usr/bin/env python3
"""Supervised matched native/search measurements, with optional diagnostics.

The existing scaling benchmark supplies rules, policies, search and resource
guards. This wrapper can run that same workload against a frozen old runtime.
Instrumented runs explain costs; use uninstrumented runs for throughput claims.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from functools import wraps
import hashlib
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


class Timers:
    """Per-thread nested accounting; sums across workers are not wall fractions."""

    def __init__(self):
        self.enabled = False
        self.coordinator = threading.get_ident()
        self.local = threading.local()
        self.lock = threading.Lock()
        self.rows = defaultdict(lambda: dict(calls=0, wall_seconds=0., exclusive_wall_seconds=0.,
                                             thread_cpu_seconds=0., exclusive_thread_cpu_seconds=0.))

    @contextmanager
    def measure(self, name):
        if not self.enabled:
            yield
            return
        role = "coordinator" if threading.get_ident() == self.coordinator else "search_worker"
        stack = getattr(self.local, "stack", None)
        if stack is None:
            stack = self.local.stack = []
        frame = [time.perf_counter(), time.thread_time(), 0., 0.]
        stack.append(frame)
        try:
            yield
        finally:
            wall, cpu = time.perf_counter() - frame[0], time.thread_time() - frame[1]
            stack.pop()
            if stack:
                stack[-1][2] += wall
                stack[-1][3] += cpu
            with self.lock:
                row = self.rows[f"{role}:{name}"]
                row["calls"] += 1
                row["wall_seconds"] += wall
                row["thread_cpu_seconds"] += cpu
                row["exclusive_wall_seconds"] += max(0., wall - frame[2])
                row["exclusive_thread_cpu_seconds"] += max(0., cpu - frame[3])

    def wrap(self, function, name):
        @wraps(function)
        def measured(*args, **kwargs):
            with self.measure(name):
                return function(*args, **kwargs)
        return measured

    def snapshot(self):
        return {key: dict(value) for key, value in sorted(self.rows.items())}


class TimedNative:
    """Instrumentation only: retain independent native clones and raw results."""

    def __init__(self, raw, timers):
        self._raw, self._timers = raw, timers

    def __getattr__(self, name):
        value = getattr(self._raw, name)
        if not callable(value):
            return value
        def call(*args, **kwargs):
            with self._timers.measure("engine." + name):
                result = value(*args, **kwargs)
            return TimedNative(result, self._timers) if name in {"clone", "clone_for_search"} else result
        return call


def native_probe(envs, repeats):
    """Same cold-cache native round trips, serial versus independent threads.

    This is diagnostic engine throughput, not complete self-play throughput.
    Each repetition restores the same complete state before applying one legal
    raw action (or resolving chance), so outcomes and RNG are comparable.
    """
    from concurrent.futures import ThreadPoolExecutor
    inputs = []
    for env in envs:
        raw = env.raw._raw if isinstance(env.raw, TimedNative) else env.raw
        inputs.append((raw.clone(), raw.serialize()))

    def one(item):
        raw, state = item
        result = hashlib.sha256()
        for _ in range(repeats):
            raw.restore(state)
            raw.planning_key()
            if raw.decision_kind() == "chance":
                raw.resolve_chance()
            elif not raw.is_terminal():
                actions = raw.legal_actions()
                raw.apply_action(min(actions, key=lambda action: action.id))
            result.update(raw.serialize().encode())
        return result.hexdigest()

    before = time.perf_counter()
    serial = [one(item) for item in inputs]
    serial_seconds = time.perf_counter() - before
    before = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(inputs)) as pool:
        parallel = list(pool.map(one, inputs))
    parallel_seconds = time.perf_counter() - before
    if serial != parallel:
        raise RuntimeError("Native round-trip results changed between serial and threaded execution")
    return {"roots": len(envs), "repeats_per_root": repeats,
            "serial_seconds": serial_seconds, "threaded_seconds": parallel_seconds,
            "serial_over_threaded": serial_seconds / parallel_seconds,
            "outcome_sha256": serial, "matched": True,
            "scope": "After primary measurement; serial then threaded restores/legal-action/serialization on independent native clones."}


def worker(args):
    # The wrapper stays identical while imported engine/search/model sources
    # come entirely from the selected runtime, including its native extension.
    sys.path.insert(0, str(args.runtime.resolve()))
    import studies.campaign.batching as batching
    import studies.campaign.curriculum as curriculum
    import studies.campaign.features as features
    import studies.campaign.neural as neural
    from studies.campaign.scaling_benchmark import BenchmarkConfig, _write, run_case
    from studies.shared.multiplayer_mcts import action_key
    import gwrl_cpp

    native_path = Path(gwrl_cpp.__file__).resolve()
    if not native_path.is_relative_to(args.runtime.resolve()):
        raise RuntimeError("Selected runtime did not supply its own native extension")

    timers = Timers()
    roots, model_batch_sizes = [], Counter()
    original_factory = curriculum.make_env
    def factory(*a, **kw):
        env = original_factory(*a, **kw)
        roots.append(env)
        if args.instrument:
            env.raw = TimedNative(env.raw, timers)
        return env
    curriculum.make_env = factory

    if args.instrument:
        neural.make_input = timers.wrap(neural.make_input, "input.prepare")
        neural._graph_tensors = timers.wrap(neural._graph_tensors, "input.graph_tensors")
        if features._native_compile_graph is not None:
            features._native_compile_graph = timers.wrap(features._native_compile_graph, "input.compile_graph")
        original_forward = neural.CampaignPolicyValueNet.forward_batch
        def forward(self, inputs):
            model_batch_sizes[len(inputs)] += 1
            with timers.measure("network.forward_with_input_graphs"):
                return original_forward(self, inputs)
        neural.CampaignPolicyValueNet.forward_batch = forward
        neural.NeuralEvaluator.evaluate_batch = timers.wrap(
            neural.NeuralEvaluator.evaluate_batch, "inference.total")

    original_search = batching.search_many
    search_digest = hashlib.sha256()
    searches = 0
    fingerprint_seconds = 0.
    def search(*a, **kw):
        nonlocal searches, fingerprint_seconds
        timers.enabled = args.instrument
        results = original_search(*a, **kw)
        before = time.perf_counter()
        for result in results:
            search_digest.update(json.dumps({"actions": [action_key(x) for x in result.actions],
                "visits": result.visit_counts, "policy": result.policy, "priors": result.priors,
                "values": result.values, "action_values": result.action_values},
                sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
            searches += 1
        fingerprint_seconds += time.perf_counter() - before
        return results
    batching.search_many = search
    config = BenchmarkConfig(**json.loads(args._worker.read_text()))
    report = run_case(config, args.output, replay_output=args.replay_output)
    accounting = timers.snapshot()
    timers.enabled = False
    report["concurrency_measurement"] = {
        "runtime": str(args.runtime.resolve()), "instrumented": args.instrument,
        "native_extension": str(native_path), "native_sha256": hashlib.sha256(native_path.read_bytes()).hexdigest(),
        "python_gil_enabled": getattr(sys, "_is_gil_enabled", lambda: None)(),
        "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "search_count": searches, "search_results_sha256": search_digest.hexdigest(),
        "fingerprinting_seconds": fingerprint_seconds,
        "final_engine_state_and_rng_sha256": [hashlib.sha256(env.serialize().encode()).hexdigest() for env in roots],
        "instrumentation": accounting, "per_model_forward_batch_sizes": dict(model_batch_sizes),
        "scope": "Diagnostic counters start at first searched wave and include later progress/execution calls. Engine-call wall sums can overlap across workers; never divide them by total wall time. Model forward includes graph preparation, whose nested timers are reported separately. Instrumented timings are not throughput claims."}
    if args.native_repeats and config.mode == "search" and report["status"] == "completed":
        report["concurrency_measurement"]["native_probe"] = native_probe(roots, args.native_repeats)
    _write(args.output, report)


def compare_reports(actual, reference):
    fields = {"completed": actual.get("status") == reference.get("status") == "completed",
        "task": actual.get("task") == reference.get("task"),
        "model": actual.get("model") == reference.get("model"),
        "prepared_states": actual.get("prepared_state_sha256") == reference.get("prepared_state_sha256"),
        "samples": actual.get("samples") == reference.get("samples"),
        "roots": actual.get("roots") == reference.get("roots")}
    first, second = actual.get("concurrency_measurement", {}), reference.get("concurrency_measurement", {})
    for key in ("search_count", "search_results_sha256", "final_engine_state_and_rng_sha256"):
        fields[key] = key in first and key in second and first[key] == second[key]
    fields["same_measurement_wrapper"] = (isinstance(first.get("wrapper_sha256"), str)
        and first["wrapper_sha256"] == second.get("wrapper_sha256"))
    fields["same_instrumentation"] = (type(first.get("instrumented")) is bool
        and first["instrumented"] == second.get("instrumented"))
    # Source hashes, native bytes and timing naturally differ across versions.
    fields["config"] = actual.get("config") == reference.get("config")
    return {"matched": all(fields.values()), "checks": fields,
            "reference_search_seconds": reference.get("timings_seconds", {}).get("search"),
            "actual_search_seconds": actual.get("timings_seconds", {}).get("search"),
            "instrumented_comparison": bool(first.get("instrumented") or second.get("instrumented"))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--instrument", action="store_true")
    parser.add_argument("--native-repeats", type=int, default=0)
    parser.add_argument("--record-replay", action="store_true")
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--replay-output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not (args.runtime / "studies/campaign/scaling_benchmark.py").is_file():
        parser.error("Runtime must contain the campaign benchmark and its matching native extension")
    if not 0 <= args.native_repeats <= 1000:
        parser.error("Native repeats must be between zero and one thousand")
    if args._worker:
        worker(args)
        return 0
    if args.config is None:
        parser.error("Supply a BenchmarkConfig JSON with --config")
    # Keep the resource supervisor from this checkout, not the historical
    # runtime; only its child imports the requested old/new runtime.
    sys.path.insert(0, str(ROOT))
    from studies.campaign.scaling_benchmark import BenchmarkConfig, _write, supervise
    config = BenchmarkConfig(**json.loads(args.config.read_text()))
    prefix = [sys.executable, str(Path(__file__).resolve()), "--runtime", str(args.runtime.resolve()),
              "--native-repeats", str(args.native_repeats)]
    if args.instrument:
        prefix.append("--instrument")
    report = supervise(config, args.output.resolve(), record_replay=args.record_replay, worker_prefix=prefix)
    if args.compare_to:
        report["comparison"] = compare_reports(report, json.loads(args.compare_to.read_text()))
        _write(args.output.resolve(), report)
    print(json.dumps({"output": str(args.output.resolve()), "status": report["status"],
                      "comparison": report.get("comparison"), "timings_seconds": report.get("timings_seconds")}), flush=True)
    return 1 if report["status"] in {"worker_error", "memory_monitor_failure"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
