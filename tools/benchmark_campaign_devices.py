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
import traceback

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
    processes: int = 1
    # Process-parallel MPS self-play: games each process plays at once, one per
    # thread, all evaluated in shared batches by the coordinating process.
    games_per_process: int = 1
    calendar_rounds: int = 3
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
        if type(self.calendar_rounds) is not int or not 1 <= self.calendar_rounds <= 11:
            raise ValueError("Self-play horizon must be between one and eleven rounds")
        if self.search_evaluation not in {"batched", "per_search"}:
            raise ValueError("Search evaluation must be batched or per_search")
        if type(self.processes) is not int or not 1 <= self.processes <= len(self.seeds):
            raise ValueError("Self-play processes must be between one and the number of games")
        if self.processes > 1 and (self.mode != "selfplay" or self.search_evaluation != "per_search" or self.threads != 1):
            raise ValueError("Process-parallel self-play needs per-search evaluation and one tensor thread")
        if type(self.games_per_process) is not int or self.games_per_process < 1 or (
                self.games_per_process > 1 and (self.processes < 2 or self.devices != ("mps",))):
            raise ValueError("Several games per process need process-parallel self-play on the shared MPS evaluator")
        if self.processes > 1 and {"cpu", "mps"} <= set(self.devices):
            raise ValueError("Paired CPU/MPS runs need one process: compare_selfplay compares per-game traces, "
                             "which shared MPS self-play does not record; run each device separately")
        if self.processes > 1 and self.devices == ("mps",) and len(self.seeds) < self.processes * self.games_per_process:
            # Fewer games would leave slots idle from the start and void the all-slots-busy rate.
            raise ValueError("Shared MPS self-play needs at least one game for every game slot")
        roots = len(self.seeds) if self.mode == "selfplay" else 0
        # Game processes run tensors on their search threads: one busy core per
        # process, plus this coordinator and its supervisor.
        cores = self.processes + 2 if self.processes > 1 else self.threads + roots + 3
        if type(self.cpu_budget) is not int or not 3 <= self.cpu_budget <= min(12, os.cpu_count() or 1) or cores > self.cpu_budget:
            raise ValueError("Tensor threads, search workers and coordinators must fit the 12-core allowance")
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


def game_failure(env, count, error):
    """A failed game's actual position, and the searched one where search found no move."""
    return {"error": f"{type(error).__name__}: {error}", "decisions": count["decisions"],
            "clock": env.observation()["state"]["clock"], "position": env.serialize(),
            "searched_position": getattr(error, "state", None)}


def selfplay(config, device, models, evaluator, forward_stats, deadline, persist):
    import random
    from studies.campaign.batching import BatchStats, search_many
    from studies.campaign.curriculum import make_env, task_manifest
    from studies.shared.multiplayer_mcts import MctsConfig, action_key
    from tools.benchmark_campaign_backends import check_terminal
    before = time.perf_counter()
    envs = [make_env(seed, calendar_rounds=config.calendar_rounds) for seed in config.seeds]
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
    started_epoch = time.time()
    completed_at = [None] * len(envs)
    # A rules defect ends only the games it reaches; the others play on.
    failures = {}
    while active := [index for index, env in enumerate(envs) if not env.is_terminal() and index not in failures]:
        if time.monotonic() >= deadline:
            stop_reason = "wall_limit"; break
        if any(counts[index]["transitions"] >= config.max_transitions or
               visits[index][envs[index].planning_key()] > config.max_state_visits for index in active):
            stop_reason = "transition_or_repetition_limit"; break
        searching, indices = [], []
        for index in active:
            env = envs[index]
            if env.decision_kind() == "chance":
                key, request, cursor = env.planning_key(), env.chance_request(), env.raw.history_size()
                before = time.perf_counter()
                try:
                    env.resolve_chance()
                except (RuntimeError, ValueError) as error:
                    failures[index] = game_failure(env, counts[index], error); continue
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
            try:
                results = search_many(searching, evaluator, configs=settings, add_root_noise=True, stats=stats,
                                      evaluation=config.search_evaluation)
            except (RuntimeError, ValueError) as error:
                # One search's defect cannot be told apart within a batch: it ends
                # every game searched with it, which is one game per process.
                failures.update((index, game_failure(envs[index], counts[index], error)) for index in indices)
                results = []
            timings["search"] += stats.elapsed_seconds
            for index, search in zip(indices, results):
                env = envs[index]
                chosen = policy_rngs[index].choices(search.actions, weights=search.policy, k=1)[0]
                event = {"kind": env.decision_kind(), "owner": env.current_decision_player(),
                         "action": action_key(chosen), "before": env.planning_key()}
                before = time.perf_counter()
                try:
                    env.apply_action(chosen)
                except (RuntimeError, ValueError) as error:
                    failures[index] = game_failure(env, counts[index], error); continue
                timings["actual_rules_execution"] += time.perf_counter() - before
                event["after"] = env.planning_key(); traces[index].append(event)
                counts[index].update(transitions=1, decisions=1)
                visits[index][env.planning_key()] += 1
        waves += 1
        for index, env in enumerate(envs):
            if env.is_terminal() and completed_at[index] is None:
                check_terminal(env, config.calendar_rounds); completed_at[index] = time.perf_counter() - started
        if waves % 10 == 0:
            result["progress"] = [{"seed": seed, **dict(count), "clock": env.observation()["state"]["clock"],
                                   "terminal": env.is_terminal()} for seed, env, count in zip(config.seeds, envs, counts)]
            persist(result)
    elapsed = time.perf_counter() - started
    complete = all(env.is_terminal() for env in envs)
    inference_seconds = evaluator.seconds - inference_before
    forward_seconds = forward_stats["seconds"] - forward_before
    result.update(status="completed" if complete else "game_error" if failures else "truncated", stop_reason=stop_reason,
        started_at_epoch=started_epoch, ended_at_epoch=started_epoch + elapsed,
        completed_games=sum(env.is_terminal() for env in envs), failed_games=len(failures), cohort_wall_seconds=elapsed,
        complete_games_per_hour=len(envs) * 3600 / elapsed if complete else None,
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
            "final_state_and_rng_sha256": hashlib.sha256(env.serialize().encode()).hexdigest(),
            "failure": failures.get(index)}
            for index, (seed, env, count, trace, ended) in enumerate(zip(config.seeds, envs, counts, traces, completed_at))])
    return result


def _selfplay_group(values, seeds, deadline_epoch):
    """Play some of a cohort's games in a separate process with the same fresh weights."""
    config = Config(**{**values, "seeds": tuple(seeds), "processes": 1, "devices": ("cpu",)})
    models, evaluator, forward_stats, metadata = setup_models(config, "cpu")
    seconds = max(1.0, deadline_epoch - time.time())
    result = selfplay(config, "cpu", models, evaluator, forward_stats, time.monotonic() + seconds,
                      lambda result=None: None)
    return {"result": result, "weights_sha256": metadata["weights_sha256"], "process": os.getpid(),
            "forward": {**forward_stats, "batch_sizes": dict(forward_stats["batch_sizes"])},
            "evaluator": {"synchronized_seconds": evaluator.seconds, "calls": evaluator.calls,
                          "requests": evaluator.requests, "batch_sizes": dict(evaluator.batch_sizes)}}


def parallel_selfplay(config, weights, deadline, *, run_group=_selfplay_group, executor=None):
    """Play a cohort's games from a queue on processes, each with its own interpreter lock.

    Each game is one task taken by whichever process is free, as in training, so
    a long game leaves no process idle while games remain. Per-search games do
    not depend on which process plays them, so each game matches its
    single-process result. Cohort wall time runs from the first game's start to
    the last one's end; timings and counts are summed.
    """
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    values = asdict(config)
    # Queued games start late, so they share the cohort's absolute deadline.
    deadline_epoch = time.time() + max(1.0, deadline - time.monotonic())
    pool = executor or ProcessPoolExecutor(max_workers=config.processes, mp_context=multiprocessing.get_context("spawn"))
    try:
        futures = [pool.submit(run_group, values, (seed,), deadline_epoch) for seed in config.seeds]
        parts = [future.result() for future in futures]
    finally:
        if executor is None:
            pool.shutdown(wait=True, cancel_futures=True)
    require(all(part["weights_sha256"] == weights for part in parts), "A game process built different fresh weights")
    results = [part["result"] for part in parts]
    order = {seed: index for index, seed in enumerate(config.seeds)}
    games = sorted((game for result in results for game in result["games"]), key=lambda game: order[game["seed"]])
    complete = all(result["status"] == "completed" for result in results)
    started = min(result["started_at_epoch"] for result in results)
    span = max(result["ended_at_epoch"] for result in results) - started
    busy = sum(result["ended_at_epoch"] - result["started_at_epoch"] for result in results)
    timing = Counter()
    for result in results:
        timing.update(result["timing_seconds"])
    def merged(name):
        return sum((Counter(part[name]["batch_sizes"]) for part in parts), Counter())
    forward = {"seconds": sum(part["forward"]["seconds"] for part in parts),
               "calls": sum(part["forward"]["calls"] for part in parts), "batch_sizes": merged("forward")}
    evaluated = {"synchronized_seconds": sum(part["evaluator"]["synchronized_seconds"] for part in parts),
                 "calls": sum(part["evaluator"]["calls"] for part in parts),
                 "requests": sum(part["evaluator"]["requests"] for part in parts), "batch_sizes": merged("evaluator")}
    failed = sum(result["failed_games"] for result in results)
    summary = {"task": results[0]["task"], "status": "completed" if complete else "game_error" if failed else "truncated",
        "stop_reason": [result["stop_reason"] for result in results], "root_noise": True,
        "selection": results[0]["selection"], "processes": config.processes,
        "started_at_epoch": started, "ended_at_epoch": started + span,
        "completed_games": sum(game["terminal"] for game in games), "failed_games": failed, "cohort_wall_seconds": span,
        "complete_games_per_hour": len(games) * 3600 / span if complete else None,
        "process_utilization": busy / (config.processes * span) if span > 0 else None,
        "search_simulations": config.simulations, "search_depth_cap": config.max_depth,
        "timing_seconds_summed_across_processes": dict(timing),
        "inference_calls": sum(result["inference_calls"] for result in results),
        "inference_requests": sum(result["inference_requests"] for result in results),
        "actual_inference_batch_sizes": dict(sum((Counter(result["actual_inference_batch_sizes"]) for result in results), Counter())),
        "game_tasks": [{"seed": seed, "process": part["process"], "status": result["status"],
                        "started_at_epoch": result["started_at_epoch"], "ended_at_epoch": result["ended_at_epoch"],
                        "preparation_seconds": result["preparation_seconds"], "warmup_seconds": result["warmup_seconds"],
                        "timing_seconds": result["timing_seconds"]} for seed, part, result in zip(config.seeds, parts, results)],
        "games": games}
    return summary, forward, evaluated


SHARED_BUFFER_BYTES = 8 * 1024 * 1024  # One prepared position; 11-round inputs take about 1 MB.


def play_shared_game(config, seed, evaluator, deadline_epoch):
    """One game as selfplay plays it, with a RemoteEvaluator answering searches.

    When the coordinator closes the pipe at the end of the run, the game stops
    without a failure.
    """
    import random
    from studies.campaign.curriculum import make_env
    from studies.campaign.shared_evaluator import EvaluatorClosed
    from studies.shared.multiplayer_mcts import MctsConfig, VectorMCTS
    from tools.benchmark_campaign_backends import check_terminal
    started_epoch, started = time.time(), time.perf_counter()
    env = make_env(seed, calendar_rounds=config.calendar_rounds)
    search_rng = random.Random(seed ^ 0x9E3779B97F4A7C15)
    policy_rng = random.Random(seed ^ 0xD1B54A32D192ED03)
    visits, count = Counter({env.planning_key(): 1}), Counter(transitions=0, decisions=0, chance_events=0)
    timings, failure, stop_reason = Counter(), None, None
    before_stats = (evaluator.stats.requests, evaluator.stats.prepare_seconds, evaluator.stats.wait_seconds)
    while not env.is_terminal():
        if time.time() >= deadline_epoch:
            stop_reason = "wall_limit"; break
        if count["transitions"] >= config.max_transitions or visits[env.planning_key()] > config.max_state_visits:
            stop_reason = "transition_or_repetition_limit"; break
        try:
            if env.decision_kind() == "chance":
                before = time.perf_counter(); env.resolve_chance()
                timings["actual_rules_execution"] += time.perf_counter() - before
                count.update(transitions=1, chance_events=1)
            else:
                settings = MctsConfig(simulations=config.simulations, max_depth=config.max_depth,
                                      seed=search_rng.getrandbits(64))
                before = time.perf_counter()
                search = VectorMCTS(evaluator, settings).search(env, add_root_noise=True)
                timings["search"] += time.perf_counter() - before
                chosen = policy_rng.choices(search.actions, weights=search.policy, k=1)[0]
                before = time.perf_counter(); env.apply_action(chosen)
                timings["actual_rules_execution"] += time.perf_counter() - before
                count.update(transitions=1, decisions=1)
            if env.is_terminal():
                check_terminal(env, config.calendar_rounds)
        except EvaluatorClosed:
            stop_reason = "evaluator_closed"; break
        except (RuntimeError, ValueError) as error:
            failure = game_failure(env, count, error); break
        visits[env.planning_key()] += 1
    elapsed = time.perf_counter() - started
    requests, prepared, waited = (now - then for now, then in zip(
        (evaluator.stats.requests, evaluator.stats.prepare_seconds, evaluator.stats.wait_seconds), before_stats))
    timings.update(input_preparation=prepared, waiting_for_evaluations=waited)
    return {"seed": seed, **dict(count), "terminal": env.is_terminal(), "stop_reason": stop_reason,
            "clock": env.observation()["state"]["clock"], "started_at_epoch": started_epoch,
            "ended_at_epoch": started_epoch + elapsed, "game_seconds": elapsed, "evaluations": requests,
            "terminal_returns": list(env.returns()) if env.is_terminal() else None,
            "timing_seconds": dict(timings), "failure": failure, "process": os.getpid()}


def _shared_game_process(values, slots, connections, buffer_names, tasks, results, deadline_epoch, version):
    """A game process: one thread per game slot, each taking seeds until its stop marker."""
    from studies.campaign.shared_evaluator import RemoteEvaluator
    config = Config(**values)
    def slot(index, connection, name):
        evaluator = RemoteEvaluator(connection, name, config.token_buckets, version)
        try:
            # A blocking get: get_nowait can report an empty queue before the
            # coordinator's queued seeds reach this process.
            while (seed := tasks.get()) is not None:
                started, requests = time.time(), evaluator.stats.requests
                try:
                    record = play_shared_game(config, seed, evaluator, deadline_epoch)
                except BaseException as error:
                    # Any other defect ends only this game; the slot takes the next seed.
                    ended = time.time()
                    record = {"seed": seed, "terminal": False, "stop_reason": "game_exception",
                              "started_at_epoch": started, "ended_at_epoch": ended, "game_seconds": ended - started,
                              "evaluations": evaluator.stats.requests - requests, "terminal_returns": None,
                              "timing_seconds": {}, "process": os.getpid(),
                              "failure": {"error": f"{type(error).__name__}: {error}",
                                          "traceback": traceback.format_exc()}}
                results.put({**record, "slot": index})
        finally:
            evaluator.close()
    threads = [threading.Thread(target=slot, args=arguments, name=f"campaign-game-{arguments[0]}", daemon=True)
               for arguments in zip(slots, connections, buffer_names)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def shared_selfplay(config, device, models, weights, deadline, persist, runtime_policy=None):
    """Game processes keep rules, search and input preparation; this process
    evaluates every waiting position in shared device batches.

    Each process plays `games_per_process` games at once, one per thread, taking
    seeds from one queue, so a finished game's slot starts the next game. See
    studies/campaign/shared_evaluator.py for the request protocol. Returns the
    report and, as parallel_selfplay does, the traffic as model forwards and
    evaluator calls.
    """
    import multiprocessing
    import queue
    import resource
    from multiprocessing import shared_memory
    import torch
    from studies.campaign.curriculum import make_env, task_manifest
    from studies.campaign.shared_evaluator import SharedEvaluatorServer
    context = multiprocessing.get_context("spawn")
    slots = config.processes * config.games_per_process
    pipes = [context.Pipe() for _ in range(slots)]
    memories = [shared_memory.SharedMemory(create=True, size=SHARED_BUFFER_BYTES) for _ in range(slots)]
    tasks, results = context.Queue(), context.Queue()
    for seed in [*config.seeds, *[None] * slots]:  # One stop marker per game slot.
        tasks.put(seed)
    # Games stop a minute and a half before the worker's deadline: their searches
    # get half a minute to finish, then the pipes close, the processes get 20
    # seconds to exit, and the report is written before the supervisor's own
    # wall limit.
    deadline_epoch = time.time() + max(1.0, deadline - time.monotonic() - 90)
    values, processes, games, samples = asdict(config), [], [], []
    self_before = resource.getrusage(resource.RUSAGE_SELF)
    children_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    server = None
    try:
        for index in range(config.processes):
            members = range(index * config.games_per_process, (index + 1) * config.games_per_process)
            process = context.Process(target=_shared_game_process, daemon=True, args=(
                values, list(members), [pipes[member][1] for member in members],
                [memories[member].name for member in members], tasks, results, deadline_epoch, weights))
            process.start()
            processes.append(process)
        for _, child in pipes:
            child.close()
        server = SharedEvaluatorServer(models, torch.device(device), [parent for parent, _ in pipes],
                                       [memory.name for memory in memories], runtime_policy)
        # (epoch, requests answered) about every 10 seconds, for the rate while
        # every slot plays.
        samples.append((time.time(), 0))
        last_persist = time.monotonic()
        def keep_running():
            nonlocal last_persist
            while True:
                try:
                    games.append(results.get_nowait())
                except queue.Empty:
                    break
            require(all(process.is_alive() or process.exitcode == 0 for process in processes),
                    "A game process exited abnormally")
            now = time.time()
            if now - samples[-1][0] >= 10:
                samples.append((now, server.stats.requests))
            if time.monotonic() - last_persist > 60:
                persist({"status": "running", "finished_games": len(games), "server_requests": server.stats.requests,
                         "server_rounds": server.stats.rounds}); last_persist = time.monotonic()
            # Game threads stop at the deadline; allow them half a minute to report.
            return now < deadline_epoch + 30
        server.serve(keep_running)
        samples.append((time.time(), server.stats.requests))
        # The server closed every pipe still open, so a thread still waiting for
        # an evaluation ends its game. A process exits only once its queued
        # results reach the pipe, so collect them while all processes exit
        # against one deadline.
        stop = time.monotonic() + 20
        while time.monotonic() < stop and any(process.is_alive() for process in processes):
            try:
                games.append(results.get(timeout=0.1))
            except queue.Empty:
                pass
        stragglers = [process for process in processes if process.is_alive()]
        for process in stragglers:
            process.kill()
        for process in stragglers:
            process.join(timeout=1)  # Reaped, so their CPU time is counted.
        # A process killed or crashed mid-message leaves half of it, on which a
        # read would wait forever, so drain only after every process exited cleanly.
        clean = all(process.exitcode == 0 for process in processes)
        stop = time.monotonic() + 5
        while clean and len(games) < len(config.seeds) and time.monotonic() < stop:
            try:
                games.append(results.get(timeout=0.5))
            except queue.Empty:
                break
    finally:
        for process in processes:
            if process.is_alive():
                process.kill()
        if server is not None:
            server.close()
        for memory in memories:
            memory.close(); memory.unlink()
        for parent, _ in pipes:
            parent.close()
    self_after, children = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    return shared_summary(config, games, server.stats, samples,
        task=task_manifest(make_env(config.seeds[0], calendar_rounds=config.calendar_rounds)),
        game_process_cpu_seconds=(children.ru_utime - children_before.ru_utime) + (children.ru_stime - children_before.ru_stime),
        coordinator_cpu_seconds=(self_after.ru_utime - self_before.ru_utime) + (self_after.ru_stime - self_before.ru_stime))


def all_slots_busy(games, samples):
    """The evaluation rate from the earliest game start to the first game end.

    Config gives every slot a first game, so in that window every slot plays,
    apart from the seconds the later slots take to start: it is the rate a long
    queue of games sustains. Only games send requests, so none precede the
    earliest start; the count at the first end is interpolated between the
    server's (epoch, requests answered) samples.
    """
    import numpy as np
    if not games or not samples:
        return None
    start = min(game["started_at_epoch"] for game in games)
    end = min(game["ended_at_epoch"] for game in games)
    if end <= start:
        return None
    times, counts = zip(*samples)
    evaluations = float(np.interp(end, times, counts))
    return {"seconds": end - start, "evaluations": evaluations, "evaluations_per_second": evaluations / (end - start)}


def shared_summary(config, games, stats, samples, *, task, game_process_cpu_seconds, coordinator_cpu_seconds):
    """shared_selfplay's report from its game records and the server's statistics.

    Like parallel_selfplay, it also returns the traffic as model forwards (one
    per alliance model with positions in a serving round) and evaluator calls
    (one per serving round).
    """
    order = {seed: index for index, seed in enumerate(config.seeds)}
    games = sorted(games, key=lambda game: order[game["seed"]])
    reported = {game["seed"] for game in games}
    missing = [seed for seed in config.seeds if seed not in reported]
    failed = sum(game["failure"] is not None for game in games)
    complete = not missing and not failed and all(game["terminal"] for game in games)
    finished = [game for game in games if game["terminal"] and game["failure"] is None]
    started = min(game["started_at_epoch"] for game in games) if games else time.time()
    span = max(game["ended_at_epoch"] for game in games) - started if games else 0.0
    timing = Counter()
    for game in games:
        timing.update(game["timing_seconds"])
    busy = all_slots_busy(games, samples)
    per_game = sum(game["evaluations"] for game in finished) / len(finished) if finished else None
    mean_seconds = sum(game["game_seconds"] for game in finished) / len(finished) if finished else None
    positions = sum(size * count for size, count in stats.positions_per_forward.items())
    result = {"task": task,
        "status": "game_error" if failed or missing else "completed" if complete else "truncated", "root_noise": True,
        "selection": "visit-policy sampling, independent per-game policy/search RNG streams",
        "evaluation": "every game's positions batched by one coordinating process on the device",
        "processes": config.processes, "games_per_process": config.games_per_process,
        "game_slots": config.processes * config.games_per_process,
        "started_at_epoch": started, "ended_at_epoch": started + span, "completed_games": len(finished),
        "failed_games": failed, "missing_seeds": missing, "cohort_wall_seconds": span,
        "complete_games_per_hour": len(games) * 3600 / span if complete and span > 0 else None,
        # Slots over the mean game length: an upper bound on a long queue's rate,
        # since the last games run faster once others finish and stop competing
        # for the coordinator. steady_state_games_per_hour estimates the long-run
        # rate from the window in which every slot plays.
        # Unfinished games are the long ones, so only a complete cohort counts.
        "queue_estimate_games_per_hour": len({game["slot"] for game in finished}) * 3600 / mean_seconds
                                         if complete else None,
        "all_slots_busy": busy, "mean_evaluations_per_finished_game": per_game,
        "steady_state_games_per_hour": busy["evaluations_per_second"] * 3600 / per_game if complete and busy else None,
        "search_simulations": config.simulations, "search_depth_cap": config.max_depth,
        "timing_seconds_summed_across_games": dict(timing),
        "game_process_cpu_seconds": game_process_cpu_seconds,
        "game_process_utilization": game_process_cpu_seconds / (config.processes * span) if span else None,
        "coordinator_cpu_seconds": coordinator_cpu_seconds,
        "inference_requests": stats.requests, "serving_rounds": stats.rounds,
        "mean_requests_per_serving_round": stats.requests / stats.rounds if stats.rounds else None,
        "requests_per_serving_round": dict(sorted(stats.requests_per_round.items())),
        "model_forwards": stats.forwards,
        "mean_positions_per_model_forward": positions / stats.forwards if stats.forwards else None,
        "positions_per_model_forward": dict(sorted(stats.positions_per_forward.items())),
        "server_seconds": {"receiving_requests": stats.receive_seconds,
                           "forward_including_merge_transfer_and_outputs": stats.forward_seconds,
                           "sending_replies": stats.reply_seconds, "waiting_for_requests": stats.idle_seconds},
        "games": games}
    forward = {"seconds": stats.forward_seconds, "calls": stats.forwards,
               "batch_sizes": dict(sorted(stats.positions_per_forward.items()))}
    evaluated = {"synchronized_seconds": stats.receive_seconds + stats.forward_seconds + stats.reply_seconds,
                 "calls": stats.rounds, "requests": stats.requests,
                 "batch_sizes": dict(sorted(stats.requests_per_round.items()))}
    return result, forward, evaluated


def compare_selfplay(before, after):
    require(before["status"] == after["status"] == "completed", "Incomplete games cannot establish matched throughput")
    require(before["task"] == after["task"] and before["search_simulations"] == after["search_simulations"] and
            before["search_depth_cap"] == after["search_depth_cap"], "Self-play tasks or budgets differ")
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
    return {"cpu_complete_games_per_hour": before["complete_games_per_hour"],
            "mps_complete_games_per_hour": after["complete_games_per_hour"], "pairs": pairs,
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
    elif config.processes > 1:
        if device == "mps":
            result, forward, evaluated = shared_selfplay(config, device, models, metadata["weights_sha256"], deadline,
                                                         persist, evaluator.inner.runtime_policy)
        else:
            result, forward, evaluated = parallel_selfplay(config, metadata["weights_sha256"], deadline)
        # Report the game processes' merged traffic, or the shared server's model
        # forwards and serving rounds; this process's own evaluator is unused.
        forward_stats.update(seconds=forward["seconds"], calls=forward["calls"], batch_sizes=forward["batch_sizes"])
        evaluator.seconds, evaluator.calls = evaluated["synchronized_seconds"], evaluated["calls"]
        evaluator.requests, evaluator.batch_sizes = evaluated["requests"], evaluated["batch_sizes"]
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
        elif (report.get("status") not in {"completed", "truncated", "game_error", "device_error", "changed_inputs"} or
              (process.returncode != 0 and not (process.returncode == 2 and report.get("status") in {
                  "truncated", "game_error", "device_error", "changed_inputs"}))):
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
