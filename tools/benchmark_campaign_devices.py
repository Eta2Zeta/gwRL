#!/usr/bin/env python3
"""Matched CPU/MPS neural inference and hybrid CPU-rules self-play benchmarks.

Fresh CPU-initialized weights, rules, seeds, horizons and search budgets are
shared. Only neural execution changes device. Floating-point results and chosen
actions may differ; this is neither a GPU rules engine nor a learning run.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA = "campaign-neural-device-benchmark-v1"


@dataclass(frozen=True)
class Config:
    mode: str = "inference"
    devices: tuple[str, ...] = ("cpu", "mps")
    seeds: tuple[int, ...] = (1951, 1952, 1953, 1954)
    model_seed: int = 1951
    batch_sizes: tuple[int, ...] = (1, 4)
    position_labels: tuple[str, ...] = ("opening", "japan_combat_movement", "round2_japan_combat_movement")
    cold_repeats: int = 2
    warm_repeats: int = 3
    warmups: int = 1
    threads: int = 4
    cpu_budget: int = 12
    memory_bytes: int = 24_000_000_000
    seconds: float = 120.0
    simulations: int = 16
    max_depth: int = 16
    max_transitions: int = 5000
    max_state_visits: int = 20
    search_evaluation: str = "batched"
    hidden_dim: int = 16
    message_layers: int = 1
    token_buckets: int = 2048
    value_scale: float = 100.0
    atol: float = .002
    rtol: float = .0002

    def __post_init__(self):
        if self.mode not in {"inference", "selfplay"}:
            raise ValueError("Mode must be inference or selfplay")
        if not self.devices or len(set(self.devices)) != len(self.devices) or set(self.devices) - {"cpu", "mps"}:
            raise ValueError("Devices must be distinct explicit cpu/mps targets; no fallback is available")
        if not self.seeds or len(set(self.seeds)) != len(self.seeds) or any(type(n) is not int or not 0 <= n < 2**64 for n in self.seeds):
            raise ValueError("Seeds must be distinct unsigned 64-bit integers")
        if type(self.model_seed) is not int or not 0 <= self.model_seed < 2**63:
            raise ValueError("Model seed must fit a nonnegative signed 64-bit integer")
        if not self.batch_sizes or len(set(self.batch_sizes)) != len(self.batch_sizes) or any(type(n) is not int or n <= 0 for n in self.batch_sizes):
            raise ValueError("Batch sizes must be distinct positive integers")
        if not self.position_labels or len(set(self.position_labels)) != len(self.position_labels) or set(self.position_labels) - {
                "opening", "first_chance", "japan_combat_movement", "round2_japan_combat_movement"}:
            raise ValueError("Unknown or repeated real position label")
        for name in ("cold_repeats", "warm_repeats", "warmups", "threads", "simulations", "max_depth",
                     "max_transitions", "max_state_visits", "hidden_dim", "message_layers", "token_buckets"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.hidden_dim < 4 or self.token_buckets < 2:
            raise ValueError("Model dimensions violate the current model contract")
        if self.simulations != 16 or self.max_depth != 16:
            raise ValueError("This matched benchmark preserves 16 simulations and depth cap 16")
        if self.search_evaluation not in {"batched", "per_search"}:
            raise ValueError("Search evaluation must be batched or per_search")
        roots = len(self.seeds) if self.mode == "selfplay" else 0
        if type(self.cpu_budget) is not int or not 3 <= self.cpu_budget <= min(12, os.cpu_count() or 1) or self.threads + roots + 3 > self.cpu_budget:
            raise ValueError("Tensor threads, search workers and three coordinators must fit the 12-core allowance")
        if type(self.memory_bytes) is not int or not 2_000_000_000 < self.memory_bytes <= 30_000_000_000:
            raise ValueError("Aggregate memory must leave a CPU/monitor reserve and fit 30 GB")
        for name in ("seconds", "value_scale", "atol", "rtol"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def atomic_json(path, value):
    from tools.supervise_campaign_training import atomic_json as write
    write(Path(path), value)


def mps_allocator_limit(memory_bytes, recommended):
    require(isinstance(recommended, int) and recommended > 0, "MPS recommended working-set memory is unavailable")
    # The allocator is bounded before any model/batch transfer. Half the
    # remaining envelope leaves room for CPU/native data and conservative
    # footprint-plus-driver accounting; no requested batch is silently reduced.
    limit = min((memory_bytes - 2_000_000_000) // 2, recommended)
    require(limit > 0, "No safe MPS allocator allowance remains")
    return {"allocator_limit_bytes": limit, "recommended_max_bytes": recommended,
            "per_process_fraction": limit / recommended, "cpu_native_reserve_bytes": memory_bytes - limit}


def model_digest(models):
    result = hashlib.sha256()
    for player, model in sorted(models.items()):
        for name, tensor in model.state_dict().items():
            value = tensor.detach().cpu().contiguous()
            result.update(canonical([player, name, str(value.dtype), list(value.shape)]).encode())
            result.update(value.numpy().tobytes())
    return result.hexdigest()


class TimedEvaluator:
    """Blocking evaluator timing includes source assembly and host output transfer.

    Per-search evaluation calls it from several threads; seconds are then summed
    across those threads.
    """
    def __init__(self, evaluator, device, synchronize):
        self.inner, self.device, self.synchronize = evaluator, device, synchronize
        self.version = evaluator.version
        self.seconds, self.calls, self.requests = 0.0, 0, 0
        self.batch_sizes = Counter()
        self._lock = threading.Lock()

    @property
    def concurrent_evaluation(self):
        return getattr(self.inner, "concurrent_evaluation", True)

    def evaluate_batch(self, requests):
        self.synchronize(self.device)
        before = time.perf_counter()
        result = self.inner.evaluate_batch(requests)
        self.synchronize(self.device)
        elapsed = time.perf_counter() - before
        with self._lock:
            self.seconds += elapsed
            self.calls += 1; self.requests += len(requests); self.batch_sizes[len(requests)] += 1
        return result

    def evaluate(self, env, actions):
        return self.evaluate_batch([(env, actions)])[0]


def setup_models(config, device):
    import torch
    from studies.campaign.device_runtime import runtime_policy_for_device
    from studies.shared.multiplayer_mcts import PLAYERS
    from studies.campaign.neural import (CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator,
        neural_device_memory, resolve_neural_device, synchronize_neural_device)
    target = resolve_neural_device(device)
    allocator = None
    if device == "mps":
        memory = neural_device_memory(target)
        allocator = mps_allocator_limit(config.memory_bytes, memory["recommended_max_bytes"])
        torch.mps.set_per_process_memory_fraction(allocator["per_process_fraction"])
    runtime_policy = runtime_policy_for_device(target)
    torch.set_num_threads(config.threads)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    torch.manual_seed(config.model_seed)
    stats = {"seconds": 0.0, "calls": 0, "batch_sizes": Counter()}
    stats_lock = threading.Lock()
    class MeasuredModel(CampaignPolicyValueNet):
        def forward_batch(self, inputs, **kwargs):
            synchronize_neural_device(target)
            before = time.perf_counter()
            result = super().forward_batch(inputs, **kwargs)
            synchronize_neural_device(target)
            elapsed = time.perf_counter() - before
            with stats_lock:
                stats["seconds"] += elapsed
                stats["calls"] += 1; stats["batch_sizes"][len(inputs)] += 1
            return result
    model_config = CampaignModelConfig(hidden_dim=config.hidden_dim, message_layers=config.message_layers,
        token_buckets=config.token_buckets, value_scale=config.value_scale)
    models = {player: MeasuredModel(model_config, device=target).eval() for player in PLAYERS}
    require(all(parameter.device.type == device for model in models.values() for parameter in model.parameters()),
            "A model parameter is on a different device; fallback is forbidden")
    weights = model_digest(models)
    base = NeuralEvaluator(models, version=weights, runtime_policy=runtime_policy)
    evaluator = TimedEvaluator(base, target, synchronize_neural_device)
    return models, evaluator, stats, {"config": asdict(model_config), "weights_sha256": weights,
        "initialization": "fresh CPU-initialized current weights, same model seed; no learned checkpoint imported",
        "allocator": allocator, "device": str(target), "training_updates": 0}


def outputs(evaluations):
    return [{"priors": list(row.priors), "values": list(row.values)} for row in evaluations]


def inference(config, device, models, evaluator, forward_stats, deadline, persist):
    from studies.campaign.curriculum import make_env
    from studies.campaign.neural import clear_neural_caches, neural_device_memory, synchronize_neural_device
    from tools.benchmark_campaign_backends import Config as ReplayConfig, prepare
    before = time.perf_counter()
    workload = prepare(ReplayConfig(seeds=(config.seeds[0],), max_transitions=config.max_transitions,
        max_state_visits=config.max_state_visits), deadline=deadline)
    fixtures = [row for row in workload["fixtures"] if row["label"] in config.position_labels]
    require(len(fixtures) == len(config.position_labels), "Not all requested real positions were reached")
    result = {"task": workload["task"], "preparation_seconds": time.perf_counter() - before,
              "fixture_workload_sha256": digest(workload), "cases": [], "status": "running"}
    persist(result)
    for fixture in fixtures:
        env = make_env(fixture["seed"], calendar_rounds=3); env.restore(fixture["serialized"])
        actions = tuple(env.legal_actions()); initial = env.serialize()
        # Prepare the complete host numerical graphs once. Cold measurements
        # clear device/layout/model caches, not these immutable source graphs.
        from studies.campaign.features import make_numeric_input
        input_started = time.perf_counter(); numeric = make_numeric_input(env, actions, config.token_buckets)
        input_seconds = time.perf_counter() - input_started
        for size in config.batch_sizes:
            case = {"position": fixture["label"], "seed": fixture["seed"], "batch_size": size,
                    "request_population": "replicas of one real frozen position; ideal shared source/cache reuse, not independent games",
                    "state_sha256": fixture["serialized_sha256"], "action_ids": [action.id for action in actions],
                    "host_numeric_preparation_seconds": input_seconds,
                    "source_numeric_sha256": __import__("tools.benchmark_campaign_backends", fromlist=["numeric_digest"]).numeric_digest(numeric),
                    "cold_scope": "Model/device tensor caches cleared; prepared host source graphs and Metal executable caches may remain",
                    "cache_reset_seconds": [], "cold_seconds": [], "warm_seconds": []}
            requests = [(env, actions)] * size
            try:
                for _ in range(config.cold_repeats):
                    require(time.monotonic() < deadline, "inference_wall_limit")
                    reset_started = time.perf_counter()
                    clear_neural_caches(tuple(models.values()), device=device, release_allocator=True)
                    synchronize_neural_device(device)
                    case["cache_reset_seconds"].append(time.perf_counter() - reset_started)
                    synchronize_neural_device(device); before = time.perf_counter()
                    values = evaluator.evaluate_batch(requests)
                    synchronize_neural_device(device)
                    case["cold_seconds"].append(time.perf_counter() - before)
                    case["cold_outputs"] = outputs(values)
                before = time.perf_counter()
                for _ in range(config.warmups):
                    evaluator.evaluate_batch(requests)
                case["warmup_seconds"] = time.perf_counter() - before
                for _ in range(config.warm_repeats):
                    require(time.monotonic() < deadline, "inference_wall_limit")
                    synchronize_neural_device(device); before = time.perf_counter()
                    values = evaluator.evaluate_batch(requests)
                    synchronize_neural_device(device)
                    case["warm_seconds"].append(time.perf_counter() - before)
                case.update(status="completed", outputs=outputs(values), device_memory=neural_device_memory(device))
            except RuntimeError as error:
                case.update(status="device_error", error=str(error)[:2000])
                result["cases"].append(case); result["status"] = "device_error"; persist(result); return result
            result["cases"].append(case); persist(result)
        require(env.serialize() == initial, "Inference changed the real state or its RNG")
    result["status"] = "completed"
    result["inference_actor_forward_batch_sizes"] = dict(forward_stats["batch_sizes"])
    return result


def selfplay(config, device, models, evaluator, forward_stats, deadline, persist):
    import random
    from studies.campaign.batching import BatchStats, search_many
    from studies.campaign.curriculum import make_env, task_manifest
    from studies.shared.multiplayer_mcts import MctsConfig, action_key
    from tools.benchmark_campaign_backends import check_terminal
    before = time.perf_counter()
    envs = [make_env(seed, calendar_rounds=3) for seed in config.seeds]
    search_rngs = [random.Random(seed ^ 0x9E3779B97F4A7C15) for seed in config.seeds]
    policy_rngs = [random.Random(seed ^ 0xD1B54A32D192ED03) for seed in config.seeds]
    visits = [Counter({env.planning_key(): 1}) for env in envs]
    traces, counts = [[] for _ in envs], [Counter(transitions=0, decisions=0, chance_events=0) for _ in envs]
    initial = [env.serialize() for env in envs]
    result = {"task": task_manifest(envs[0]), "status": "running", "root_noise": True,
              "selection": "visit-policy sampling, independent per-game policy/search RNG streams",
              "preparation_seconds": time.perf_counter() - before, "progress": []}
    before = time.perf_counter()
    for _ in range(config.warmups):
        evaluator.evaluate_batch([(env, tuple(env.legal_actions())) for env in envs])
    result["warmup_seconds"] = time.perf_counter() - before
    require([env.serialize() for env in envs] == initial, "Warmup changed actual self-play states or RNG")
    inference_before, forward_before = evaluator.seconds, forward_stats["seconds"]
    calls_before, requests_before = evaluator.calls, evaluator.requests
    histogram_before = evaluator.batch_sizes.copy()
    timings = {"search": 0.0, "actual_rules_execution": 0.0}
    started, waves, stop_reason = time.perf_counter(), 0, None
    completed_at = [None] * len(envs)
    while not all(env.is_terminal() for env in envs):
        if time.monotonic() >= deadline:
            stop_reason = "wall_limit"; break
        active = [index for index, env in enumerate(envs) if not env.is_terminal()]
        if any(counts[index]["transitions"] >= config.max_transitions or
               visits[index][envs[index].planning_key()] > config.max_state_visits for index in active):
            stop_reason = "transition_or_repetition_limit"; break
        searching, indices = [], []
        for index in active:
            env = envs[index]
            if env.decision_kind() == "chance":
                key, request, cursor = env.planning_key(), env.chance_request(), env.raw.history_size()
                before = time.perf_counter(); env.resolve_chance()
                timings["actual_rules_execution"] += time.perf_counter() - before
                traces[index].append({"kind": "chance", "owner": None, "before": key, "after": env.planning_key(),
                    "request": request, "recorded_events": env.raw.history_since(cursor)})
                counts[index].update(transitions=1, chance_events=1)
                visits[index][env.planning_key()] += 1
            else:
                searching.append(env); indices.append(index)
        if searching:
            settings = [MctsConfig(simulations=config.simulations, max_depth=config.max_depth,
                                  seed=search_rngs[index].getrandbits(64)) for index in indices]
            stats = BatchStats()
            results = search_many(searching, evaluator, configs=settings, add_root_noise=True, stats=stats,
                                  evaluation=config.search_evaluation)
            timings["search"] += stats.elapsed_seconds
            for index, search in zip(indices, results):
                env = envs[index]
                chosen = policy_rngs[index].choices(search.actions, weights=search.policy, k=1)[0]
                event = {"kind": env.decision_kind(), "owner": env.current_decision_player(),
                         "action": action_key(chosen), "before": env.planning_key()}
                before = time.perf_counter(); env.apply_action(chosen)
                timings["actual_rules_execution"] += time.perf_counter() - before
                event["after"] = env.planning_key(); traces[index].append(event)
                counts[index].update(transitions=1, decisions=1)
                visits[index][env.planning_key()] += 1
        waves += 1
        for index, env in enumerate(envs):
            if env.is_terminal() and completed_at[index] is None:
                check_terminal(env); completed_at[index] = time.perf_counter() - started
        if waves % 10 == 0:
            result["progress"] = [{"seed": seed, **dict(count), "clock": env.observation()["state"]["clock"],
                                   "terminal": env.is_terminal()} for seed, env, count in zip(config.seeds, envs, counts)]
            persist(result)
    elapsed = time.perf_counter() - started
    complete = all(env.is_terminal() for env in envs)
    inference_seconds = evaluator.seconds - inference_before
    forward_seconds = forward_stats["seconds"] - forward_before
    result.update(status="completed" if complete else "truncated", stop_reason=stop_reason,
        completed_games=sum(env.is_terminal() for env in envs), cohort_wall_seconds=elapsed,
        complete_three_round_games_per_hour=len(envs) * 3600 / elapsed if complete else None,
        search_simulations=config.simulations, search_depth_cap=config.max_depth,
        timing_seconds={**timings, "synchronized_evaluator": inference_seconds,
            "synchronized_model_forward_including_tensor_preparation_and_transfers": forward_seconds,
            "evaluator_outside_forward": max(0.0, inference_seconds - forward_seconds),
            "search_outside_evaluator": max(0.0, timings["search"] - inference_seconds),
            "driver_audit_and_reporting": max(0.0, elapsed - sum(timings.values()))},
        inference_calls=evaluator.calls - calls_before, inference_requests=evaluator.requests - requests_before,
        actual_inference_batch_sizes=dict(evaluator.batch_sizes - histogram_before),
        games=[{"seed": seed, **dict(count), "terminal": env.is_terminal(),
            "clock": env.observation()["state"]["clock"], "completed_after_seconds": ended,
            "terminal_returns": list(env.returns()) if env.is_terminal() else None,
            "wealth_at_stop": env.wealth(), "trace": trace, "trace_sha256": digest(trace),
            "final_state_and_rng_sha256": hashlib.sha256(env.serialize().encode()).hexdigest()}
            for seed, env, count, trace, ended in zip(config.seeds, envs, counts, traces, completed_at)])
    return result


def compare_selfplay(before, after):
    require(before["status"] == after["status"] == "completed", "Incomplete games cannot establish matched throughput")
    require(before["task"] == after["task"] and before["search_simulations"] == after["search_simulations"] == 16 and
            before["search_depth_cap"] == after["search_depth_cap"] == 16, "Self-play tasks or budgets differ")
    pairs = []
    require([game["seed"] for game in before["games"]] == [game["seed"] for game in after["games"]], "Game seeds differ")
    for left, right in zip(before["games"], after["games"]):
        require(left["terminal"] and right["terminal"], "An evaluated game was unfinished")
        common = 0
        for first, last in zip(left["trace"], right["trace"]):
            if first != last: break
            common += 1
        pairs.append({"seed": left["seed"], "common_exact_trace_prefix": common,
            "cpu_trace_events": len(left["trace"]), "mps_trace_events": len(right["trace"]),
            "identical_trace": left["trace"] == right["trace"],
            "identical_final_state_and_rng": left["final_state_and_rng_sha256"] == right["final_state_and_rng_sha256"]})
    return {"cpu_complete_games_per_hour": before["complete_three_round_games_per_hour"],
            "mps_complete_games_per_hour": after["complete_three_round_games_per_hour"], "pairs": pairs,
            "interpretation": "Equal weights/seeds/settings, but floating-point priors/value differences may change search, choices and later dice; throughput is not an exact matched action workload or a playing-strength comparison."}


def source_provenance():
    from tools.benchmark_campaign_backends import provenance
    value = provenance()
    value["device_harness_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return value


def worker(config, device, progress):
    started, deadline = time.perf_counter(), time.monotonic() + config.seconds
    import torch
    from studies.campaign.neural import neural_device_memory
    report = {"schema": SCHEMA, "config": asdict(config), "device": device, "status": "starting",
              "provenance": source_provenance(), "execution": "hybrid CPU rules/search; neural network on explicit device",
              "limits": ["No GPU rules engine or learning updates are measured.",
                         "Synchronized forward wall includes CPU tensor/layout work and transfers, not GPU kernel time alone.",
                         "Inference sweeps replicate one real position per batch, with ideal source/cache reuse; do not extrapolate to diverse self-play from that sweep alone.",
                         "Identical weights/seeds do not guarantee identical floating-point results, actions or later dice."]}
    def persist(result=None):
        if result is not None:
            report["result"] = result
        report["elapsed_worker_seconds"] = time.perf_counter() - started
        report["device_memory"] = neural_device_memory(device)
        policy = evaluator.inner.runtime_policy
        report["device_runtime"] = policy.stats() if policy is not None else None
        report["forward"] = {**forward_stats, "batch_sizes": dict(forward_stats["batch_sizes"])}
        report["evaluator"] = {"synchronized_seconds": evaluator.seconds, "calls": evaluator.calls,
                               "requests": evaluator.requests, "batch_sizes": dict(evaluator.batch_sizes)}
        atomic_json(progress, report)
    models, evaluator, forward_stats, metadata = setup_models(config, device)
    report.update(model=metadata, startup_seconds=time.perf_counter() - started, status="running",
                  software={"python": sys.version.split()[0], "torch": torch.__version__,
                            "mps_fallback_env": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"),
                            "mps_environment": {name: os.environ.get(name) for name in (
                                "PYTORCH_ENABLE_MPS_FALLBACK", "PYTORCH_MPS_FAST_MATH", "PYTORCH_MPS_PREFER_METAL",
                                "PYTORCH_MPS_HIGH_WATERMARK_RATIO", "PYTORCH_MPS_LOW_WATERMARK_RATIO")},
                            "cpu_threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads()})
    persist()
    if config.mode == "inference":
        result = inference(config, device, models, evaluator, forward_stats, deadline, persist)
    else:
        result = selfplay(config, device, models, evaluator, forward_stats, deadline, persist)
    report["result"] = result; report["status"] = result["status"]
    report["weights_unchanged"] = model_digest(models) == metadata["weights_sha256"]
    report["forward"] = {**forward_stats, "batch_sizes": dict(forward_stats["batch_sizes"])}
    report["evaluator"] = {"synchronized_seconds": evaluator.seconds, "calls": evaluator.calls,
                           "requests": evaluator.requests, "batch_sizes": dict(evaluator.batch_sizes)}
    ending = source_provenance()
    report["sources_unchanged"] = all(report["provenance"][key] == ending[key] for key in (
        "commit", "runtime_source_sha256", "backend_source_sha256", "native_sha256", "device_harness_sha256"))
    if not report["weights_unchanged"] or not report["sources_unchanged"]:
        report["status"] = "changed_inputs"
    persist(); return report


def numerical_comparison(before, after, *, atol, rtol):
    require(len(before) == len(after), "Different inference row counts")
    absolute = relative = 0.0; mismatches = outside = count = 0
    for left, right in zip(before, after):
        for key in ("priors", "values"):
            require(len(left[key]) == len(right[key]), "Different inference vector lengths")
            for a, b in zip(left[key], right[key]):
                require(math.isfinite(a) and math.isfinite(b), "Nonfinite inference result")
                error = abs(a - b); absolute = max(absolute, error)
                relative = max(relative, error / max(abs(a), 1e-12))
                absolute_tolerance = min(atol, .00002) if key == "priors" else atol
                outside += error > absolute_tolerance + rtol * abs(a); count += 1
        if left["priors"]:
            mismatches += max(range(len(left["priors"])), key=left["priors"].__getitem__) != max(
                range(len(right["priors"])), key=right["priors"].__getitem__)
    return {"scalars": count, "maximum_absolute_error": absolute, "maximum_relative_error": relative,
            "outside_tolerance_scalars": outside, "top_action_mismatches": mismatches,
            "raw_value_atol": atol, "policy_atol": min(atol, .00002), "rtol": rtol, "within_tolerance": outside == 0}


def supervise_device(config, device, output, seconds):
    from tools.supervise_campaign_training import aggregate_rss, memory_metric, monitor_error_details
    output = Path(output); started = time.monotonic(); peak = 0; stopped = None; diagnostic = None
    with tempfile.TemporaryDirectory(prefix="campaign-device-") as directory:
        directory = Path(directory); settings = directory / "config.json"; progress = directory / "progress.json"
        atomic_json(settings, {**asdict(config), "seconds": seconds})
        environment = {**os.environ, "PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
            "PYTORCH_ENABLE_MPS_FALLBACK": "0",
            "PYTORCH_MPS_FAST_MATH": "0",
            **{name: str(config.threads) for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}}
        environment.pop("PYTORCH_MPS_PREFER_METAL", None)
        with (directory / "stderr").open("w") as stderr, (directory / "stdout").open("w") as stdout:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--_worker", str(settings),
                "--_device", device, "--output", str(progress)], cwd=ROOT, env=environment,
                stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                while process.poll() is None:
                    if time.monotonic() - started >= seconds:
                        stopped = "wall_limit"; break
                    try:
                        charged = aggregate_rss(process.pid)
                        if progress.exists():
                            memory = json.loads(progress.read_text()).get("device_memory", {})
                            charged += memory.get("driver_allocated_bytes") or 0
                        peak = max(peak, charged)
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        if process.poll() is not None:
                            break
                        stopped = "memory_monitor_failure"; diagnostic = monitor_error_details(error, "aggregate_device_memory", root_pid=process.pid); break
                    if charged >= config.memory_bytes - 1_000_000_000:
                        stopped = "memory_limit"; break
                    time.sleep(.1)
            finally:
                if process.poll() is None:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                process.wait(timeout=5)
        report = json.loads(progress.read_text()) if progress.exists() else {"schema": SCHEMA, "device": device}
        if stopped:
            report["status"] = stopped
        elif (report.get("status") not in {"completed", "truncated", "device_error", "changed_inputs"} or
              (process.returncode != 0 and not (process.returncode == 2 and report.get("status") in {
                  "truncated", "device_error", "changed_inputs"}))):
            report["status"] = "worker_error"; report["error"] = (directory / "stderr").read_text()[-4000:]
        report["guard"] = {"elapsed_seconds": time.monotonic() - started, "sampled_peak_charged_bytes": peak,
            "memory_bytes": config.memory_bytes, "margin_bytes": 1_000_000_000,
            "metric": memory_metric() + " plus last published MPS driver allocation (conservative possible double counting)",
            "cpu_budget": config.cpu_budget, "worker_returncode": process.returncode, "diagnostic": diagnostic}
        atomic_json(output, report); return report


def paired(config, output):
    output = Path(output).resolve(); require(not output.exists(), "Choose a new output file")
    paths = {device: output.with_name(output.stem + "." + device + ".json") for device in config.devices}
    require(not any(path.exists() for path in paths.values()), "Existing device results are preserved")
    output.parent.mkdir(parents=True, exist_ok=True)
    started, reports = time.monotonic(), {}
    for device in config.devices:
        remaining = config.seconds - (time.monotonic() - started)
        if remaining <= 0:
            break
        reports[device] = supervise_device(config, device, paths[device], remaining)
    complete = len(reports) == len(config.devices) and all(report["status"] == "completed" for report in reports.values())
    result = {"schema": SCHEMA, "status": "completed" if complete else "incomplete", "config": asdict(config),
              "device_reports": {key: str(path) for key, path in paths.items()},
              "elapsed_seconds_including_startups": time.monotonic() - started,
              "limits": "Hybrid device timing only; no learned-strength or full-GPU-rules claim. Same seeds do not force identical trajectories."}
    if complete and {"cpu", "mps"}.issubset(reports):
        require(reports["cpu"]["model"]["weights_sha256"] == reports["mps"]["model"]["weights_sha256"], "Initial model weights differ")
        require(reports["cpu"]["model"]["config"] == reports["mps"]["model"]["config"], "Model interpretation differs")
        require(all(reports["cpu"]["provenance"][key] == reports["mps"]["provenance"][key] for key in (
            "commit", "runtime_source_sha256", "backend_source_sha256", "native_sha256", "device_harness_sha256")),
            "CPU/MPS source or native provenance differs")
        if config.mode == "inference":
            left, right = reports["cpu"]["result"], reports["mps"]["result"]
            require(left["fixture_workload_sha256"] == right["fixture_workload_sha256"], "Frozen real inputs differ")
            require(len(left["cases"]) == len(right["cases"]) == len(config.position_labels) * len(config.batch_sizes),
                    "Incomplete inference case inventory")
            comparisons = []
            for a, b in zip(left["cases"], right["cases"]):
                require((a["position"], a["batch_size"], a["source_numeric_sha256"], a["action_ids"]) ==
                        (b["position"], b["batch_size"], b["source_numeric_sha256"], b["action_ids"]), "Inference cases differ")
                comparisons.append({"position": a["position"], "batch_size": a["batch_size"],
                    "warm_numerical": numerical_comparison(a["outputs"], b["outputs"], atol=config.atol, rtol=config.rtol),
                    "cold_numerical": numerical_comparison(a["cold_outputs"], b["cold_outputs"], atol=config.atol, rtol=config.rtol),
                    "cpu_cold_seconds": a["cold_seconds"], "mps_cold_seconds": b["cold_seconds"],
                    "cpu_warm_seconds": a["warm_seconds"], "mps_warm_seconds": b["warm_seconds"]})
            result["comparison"] = comparisons
            result["numerical_within_tolerance"] = all(row[key]["within_tolerance"] for row in comparisons
                                                        for key in ("warm_numerical", "cold_numerical"))
            if not result["numerical_within_tolerance"]:
                result["status"] = "numerical_mismatch"
        else:
            result["comparison"] = compare_selfplay(reports["cpu"]["result"], reports["mps"]["result"])
    atomic_json(output, result); return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    for name, default in asdict(Config()).items():
        if name in {"devices", "seeds", "batch_sizes", "position_labels"}:
            parser.add_argument("--" + name.replace("_", "-"), default=",".join(map(str, default)))
        elif name == "mode": parser.add_argument("--mode", choices=("inference", "selfplay"), default=default)
        elif name == "search_evaluation":
            parser.add_argument("--search-evaluation", choices=("batched", "per_search"), default=default)
        else: parser.add_argument("--" + name.replace("_", "-"), type=float if name in {"seconds", "value_scale", "atol", "rtol"} else int, default=default)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_device", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args._worker:
            values = json.loads(args._worker.read_text())
        else:
            values = {name: getattr(args, name) for name in asdict(Config())}
            for name in ("devices", "seeds", "batch_sizes", "position_labels"):
                values[name] = values[name].split(",")
            for name in ("seeds", "batch_sizes"): values[name] = [int(value) for value in values[name]]
        for name in ("devices", "seeds", "batch_sizes", "position_labels"): values[name] = tuple(values[name])
        config = Config(**values)
        report = worker(config, args._device, args.output) if args._worker else paired(config, args.output)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({"status": report["status"], "output": str(args.output.resolve())}), flush=True)
    return 0 if report["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
