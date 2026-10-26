#!/usr/bin/env python3
"""Bounded CPU/GPU comparison of the actual three-policy learning update.

One fresh balanced-baseline game supplies complete numerical menus and genuinely
terminal three-round value labels. Its policy targets are baseline supervision,
not MCTS targets or evidence of learning strength. Preparation is outside update
timing. Each fresh device worker runs CampaignLearner.update unchanged, with the
same initial CPU weights, replay rows and sampled minibatch order.
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
import random
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA = "campaign-device-update-benchmark-v1"
FIXTURE_SCHEMA = "campaign-terminal-supervised-update-fixture-v1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def atomic_json(path, value):
    from tools.supervise_campaign_training import atomic_json as save
    save(Path(path), value)


@dataclass(frozen=True)
class UpdateConfig:
    devices: tuple[str, ...] = ("cpu", "mps")
    game_seed: int = 1951
    model_seed: int = 1951
    threads: int = 2
    cpu_budget: int = 12
    memory_bytes: int = 24_000_000_000
    seconds: float = 900.0
    max_transitions: int = 5000
    max_state_visits: int = 20
    batch_size: int = 32
    epochs: int = 16
    hidden_dim: int = 16
    message_layers: int = 1
    token_buckets: int = 2048
    replay_capacity: int = 16384
    learning_rate: float = .001
    value_scale: float = 100.0
    atol: float = .002
    rtol: float = .002

    def __post_init__(self):
        require(self.devices and len(set(self.devices)) == len(self.devices) and
                not set(self.devices) - {"cpu", "mps"}, "Select distinct explicit cpu/mps devices")
        for name in ("game_seed", "model_seed"):
            require(type(getattr(self, name)) is int and 0 <= getattr(self, name) < 2**63,
                    f"{name} must be a nonnegative signed 64-bit integer")
        for name in ("max_transitions", "max_state_visits", "threads"):
            require(type(getattr(self, name)) is int and getattr(self, name) > 0, f"Invalid {name}")
        require(type(self.cpu_budget) is int and self.threads + 3 <= self.cpu_budget <= min(12, os.cpu_count() or 1),
                "Tensor threads and benchmark coordinators must fit twelve CPU cores")
        require(type(self.memory_bytes) is int and 2_000_000_000 < self.memory_bytes <= 30_000_000_000,
                "Aggregate benchmark memory must fit thirty GB with a reserve")
        require(all(type(getattr(self, name)) is int for name in (
            "batch_size", "epochs", "hidden_dim", "message_layers", "token_buckets", "replay_capacity")),
            "Model and update counts must be integers")
        require((self.batch_size, self.epochs, self.hidden_dim, self.message_layers, self.token_buckets,
                 self.replay_capacity, self.learning_rate, self.value_scale) == (32, 16, 16, 1, 2048, 16384, .001, 100.0),
                "This comparison preserves the campaign's actual batch32/epochs16/model16x1/2048 settings")
        for name in ("seconds", "atol", "rtol"):
            value = getattr(self, name)
            require(type(value) in (int, float) and math.isfinite(value) and value > 0, f"Invalid {name}")
        require(self.seconds <= 3600, "The update microbenchmark must be bounded to one hour")


def prepare_fixture(config, *, factory=None, deadline=None):
    """Save every decision and label it only after a genuine terminal game."""
    from studies.campaign.baselines import scripted_policy
    from studies.campaign.curriculum import compatibility, make_env, task_manifest
    from studies.campaign.features import NUMERIC_SCHEMA, make_numeric_input
    from studies.campaign.learning import CampaignLearner, TARGET_SCHEMA
    from studies.campaign.run import source_hashes
    from studies.shared.multiplayer_mcts import PLAYERS, OpponentPolicy, action_key, probabilities, vector
    from tools.benchmark_campaign_backends import check_terminal
    started = time.perf_counter()
    env = (factory or (lambda seed: make_env(seed, calendar_rounds=3)))(config.game_seed)
    initial = env.serialize()
    task, compatible = task_manifest(env), compatibility(env)
    policy, policy_rng = scripted_policy("balanced"), random.Random(config.game_seed)
    samples, menus, selected, chance_events = [], [], [], []
    visits = Counter({env.planning_key(): 1})
    transitions = 0
    while not env.is_terminal():
        require(deadline is None or time.monotonic() < deadline, "Preparation wall guard reached before terminal")
        require(transitions < config.max_transitions and visits[env.planning_key()] <= config.max_state_visits,
                "Preparation transition/repetition guard reached before terminal; no terminal labels were invented")
        if env.decision_kind() == "chance":
            cursor = env.raw.history_size()
            env.resolve_chance()
            chance_events.extend(event for event in env.raw.history_since(cursor) if event["kind"] == "chance")
        else:
            actions, owner = env.legal_actions(), env.current_decision_player()
            require(owner in PLAYERS and actions, "A real decision lacks an actor or legal menu")
            desired = probabilities(policy.distribution(env, actions), len(actions))
            features = make_numeric_input(env, actions, config.token_buckets)
            require(features["schema"] == NUMERIC_SCHEMA, "Real fixture requires direct complete numerical inputs")
            sample = {"input": features, "owner": owner, "policy": desired, "rollout_version": policy.version}
            CampaignLearner._validate_sample(sample, labeled=False, buckets=config.token_buckets)
            # The same standard sampler consumes the already computed complete
            # distribution instead of regenerating baseline observations twice.
            chosen = OpponentPolicy(policy.version, lambda _env, _actions: desired).sample(env, actions, policy_rng)
            samples.append(sample)
            menus.append(tuple(action_key(action) for action in actions))
            selected.append(chosen)
            env.apply_action(actions[chosen])
        transitions += 1
        visits[env.planning_key()] += 1
    check_terminal(env)
    terminal = list(vector(env.returns()))
    for sample in samples:
        sample.update(values=terminal.copy(), target_source="terminal", target_schema=TARGET_SCHEMA)
    require(len(samples) >= config.batch_size, "Terminal game has fewer than thirty-two real decisions")
    require(len(samples) <= config.replay_capacity, "Fixture exceeds unchanged replay capacity; nothing was truncated")
    require(set(sample["owner"] for sample in samples) == set(PLAYERS), "Terminal game lacks an actor's decisions")
    return {"schema": FIXTURE_SCHEMA, "policy_targets": "unchanged balanced-baseline distribution; supervised workload, not MCTS",
            "baseline_version": policy.version, "game_seed": config.game_seed, "calendar_rounds": 3,
            "task": task, "compatibility": compatible, "runtime_source_sha256": source_hashes(),
            "tool_sha256": sha(__file__), "samples": samples, "menus": menus, "selected_indices": selected,
            "chance_events": chance_events, "transitions": transitions, "terminal_returns": terminal,
            "initial_checkpoint_sha256": hashlib.sha256(initial.encode()).hexdigest(),
            "terminal_checkpoint": env.serialize(), "owner_counts": dict(Counter(row["owner"] for row in samples)),
            "preparation_seconds": time.perf_counter() - started, "bootstrap_samples": 0}


def validate_fixture(fixture, config):
    from studies.campaign.curriculum import compatibility, make_env, task_manifest
    from studies.campaign.features import NUMERIC_SCHEMA
    from studies.campaign.learning import CampaignLearner
    from studies.campaign.run import source_hashes
    from studies.shared.multiplayer_mcts import PLAYERS
    from tools.benchmark_campaign_backends import check_terminal
    require(fixture.get("schema") == FIXTURE_SCHEMA and fixture.get("calendar_rounds") == 3 and
            fixture.get("bootstrap_samples") == 0, "Fixture lacks real terminal provenance")
    require(fixture["runtime_source_sha256"] == source_hashes() and fixture["tool_sha256"] == sha(__file__),
            "Fixture runtime/tool changed; prepare a fresh game rather than retagging samples")
    terminal = make_env(fixture["game_seed"], calendar_rounds=3)
    terminal.restore(fixture["terminal_checkpoint"])
    check_terminal(terminal)
    require(task_manifest(terminal) == fixture["task"] and compatibility(terminal) == fixture["compatibility"]
            and list(terminal.returns()) == fixture["terminal_returns"],
            "Fixture terminal checkpoint/task/actual returns differ from its labels")
    samples = fixture["samples"]
    require(config.batch_size <= len(samples) <= config.replay_capacity and len(fixture["menus"]) == len(samples)
            and len(fixture["selected_indices"]) == len(samples), "Incomplete fixture decision records")
    require(set(row["owner"] for row in samples) == set(PLAYERS), "Fixture lacks an actor")
    for row, menu, selected in zip(samples, fixture["menus"], fixture["selected_indices"], strict=True):
        CampaignLearner._validate_sample(row, labeled=True, buckets=config.token_buckets)
        require(row["input"]["schema"] == NUMERIC_SCHEMA and row["target_source"] == "terminal" and
                row["values"] == fixture["terminal_returns"] and len(menu) == len(row["policy"])
                and len(set(menu)) == len(menu) and type(selected) is int and 0 <= selected < len(menu),
                "Fixture dropped menu information or contains a nonterminal/mismatched label")
    return samples


class RecordingReplayRandom:
    """Observe the unchanged standard-library sampler used by learner.update."""
    def __init__(self, original, samples):
        self.original = original
        self.indices = {id(sample): index for index, sample in enumerate(samples)}
        self.orders = []

    def sample(self, population, count):
        selected = self.original.sample(population, count)
        self.orders.append([self.indices[id(sample)] for sample in selected])
        return selected

    def getstate(self):
        return self.original.getstate()


def perform_update(fixture, device, config):
    """Call actual update once; return small CPU weights for matched comparison."""
    import torch
    from studies.campaign.learning import CampaignLearner, LearningConfig
    from studies.campaign.neural import (CampaignModelConfig, CampaignPolicyValueNet, clear_neural_caches,
        neural_device_memory, resolve_neural_device, synchronize_neural_device)
    from studies.shared.multiplayer_mcts import PLAYERS
    from tools.benchmark_campaign_devices import model_digest, mps_allocator_limit
    started = time.perf_counter()
    target = resolve_neural_device(device)
    allocator = None
    if target.type == "mps":
        allocator = mps_allocator_limit(config.memory_bytes, neural_device_memory(target)["recommended_max_bytes"])
        torch.mps.set_per_process_memory_fraction(allocator["per_process_fraction"])
    torch.set_num_threads(config.threads)
    samples = validate_fixture(fixture, config)
    clear_neural_caches(device=target, release_allocator=True)
    torch.manual_seed(config.model_seed)
    model_config = CampaignModelConfig(hidden_dim=config.hidden_dim, message_layers=config.message_layers,
                                       token_buckets=config.token_buckets, value_scale=config.value_scale)
    models = {player: CampaignPolicyValueNet(model_config, device=target).eval() for player in PLAYERS}
    learning = LearningConfig(simulations=16, max_depth=16, batch_size=config.batch_size, epochs=config.epochs,
        learning_rate=config.learning_rate, replay_capacity=config.replay_capacity, value_scale=config.value_scale,
        seed=config.model_seed)
    learner = CampaignLearner(models, model_config, learning, compatibility=fixture["compatibility"])
    learner.replay = samples
    recorder = RecordingReplayRandom(learner.replay_random, samples)
    learner.replay_random = recorder
    before_weights = model_digest(models)
    synchronize_neural_device(target)
    setup_seconds = time.perf_counter() - started
    started = time.perf_counter()
    result = learner.update()
    synchronize_neural_device(target)
    update_seconds = time.perf_counter() - started
    from studies.campaign.run import source_hashes
    require(fixture["runtime_source_sha256"] == source_hashes() and fixture["tool_sha256"] == sha(__file__),
            "Runtime/tool changed during update; this measurement is incompatible")
    require(result["updated"] and len(recorder.orders) == config.epochs and
            all(len(order) == config.batch_size for order in recorder.orders), "Update did not preserve sixteen full minibatches")
    require(all(len(result["losses"][player]) == config.epochs for player in PLAYERS), "An actor missed an Adam step")
    weights = {player: {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}
               for player, model in models.items()}
    report = {"status": "completed", "device": str(target), "setup_and_validation_seconds": setup_seconds,
              "synchronized_update_seconds": update_seconds, "initial_weights_sha256": before_weights,
              "final_weights_sha256": model_digest(models), "minibatch_orders": recorder.orders,
              "minibatch_orders_sha256": hashlib.sha256(canonical(recorder.orders).encode()).hexdigest(),
              "adam_steps_per_agent": config.epochs, "total_adam_steps": config.epochs * len(PLAYERS),
              "replay_rows": len(samples), "update": result, "device_memory": neural_device_memory(target),
              "interop_threads": torch.get_num_interop_threads(),
              "runtime_source_sha256": fixture["runtime_source_sha256"], "tool_sha256": fixture["tool_sha256"],
              "allocator": allocator, "settings": asdict(config),
              "timing_scope": "Actual CampaignLearner.update including first-use device tensor assembly, all three forward/backward/Adam loops, loss host reads and model-version digests; fixture/loading/model setup excluded",
              "limitation": "Baseline-policy supervised update workload; no self-play throughput or improved play claim"}
    return report, weights


def compare_updates(first, second, first_weights, second_weights, *, atol, rtol):
    import torch
    require(first["initial_weights_sha256"] == second["initial_weights_sha256"], "Initial model weights differ")
    require(first["minibatch_orders"] == second["minibatch_orders"], "Actual sampled minibatch order differs")
    checks, maximum = {}, 0.0
    for player in first_weights:
        require(set(first_weights[player]) == set(second_weights[player]), "Compared architectures differ")
        matched = True
        for name, tensor in first_weights[player].items():
            other = second_weights[player][name]
            require(torch.isfinite(tensor).all() and torch.isfinite(other).all(), "Compared model contains nonfinite weights")
            difference = float((tensor - other).abs().max()) if tensor.numel() else 0.0
            maximum = max(maximum, difference)
            matched = matched and bool(torch.allclose(tensor, other, atol=atol, rtol=rtol))
        a = [row[key] for row in first["update"]["losses"][player] for key in ("policy", "value", "total")]
        b = [row[key] for row in second["update"]["losses"][player] for key in ("policy", "value", "total")]
        checks[player] = {"weights_within_tolerance": matched,
                          "losses_within_tolerance": bool(torch.allclose(torch.tensor(a), torch.tensor(b), atol=atol, rtol=rtol))}
    return {"initial_weights_exact": True, "sample_order_exact": True, "atol": atol, "rtol": rtol,
            "max_weight_absolute_difference": maximum, "by_agent": checks,
            "numerically_matched": all(all(row.values()) for row in checks.values()),
            "update_speed_ratio_first_over_second": first["synchronized_update_seconds"] / second["synchronized_update_seconds"]}


def worker(stage, device, config, fixture_path, output, weights_path):
    import torch
    torch.set_num_threads(config.threads)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    if stage == "prepare":
        fixture = prepare_fixture(config, deadline=time.monotonic() + config.seconds)
        torch.save(fixture, fixture_path, pickle_protocol=5)
        result = {key: value for key, value in fixture.items() if key not in {"samples", "menus", "selected_indices", "chance_events", "terminal_checkpoint"}}
        result.update(status="completed", fixture_sha256=sha(fixture_path), rows=len(fixture["samples"]))
    else:
        before = time.perf_counter()
        fixture_hash = sha(fixture_path)
        fixture = torch.load(fixture_path, map_location="cpu", weights_only=False)
        require(sha(fixture_path) == fixture_hash, "Fixture changed while it was loaded")
        loading = time.perf_counter() - before
        result, weights = perform_update(fixture, device, config)
        torch.save(weights, weights_path, pickle_protocol=5)
        require(sha(fixture_path) == fixture_hash, "Fixture changed during update")
        result.update(fixture_loading_seconds=loading, fixture_sha256=fixture_hash, weights_sha256=sha(weights_path))
    atomic_json(output, result)
    return result


def supervise(stage, device, config, fixture, output, weights, deadline):
    from tools.supervise_campaign_training import aggregate_rss, memory_metric, monitor_error_details
    settings = Path(output).with_suffix(".config.json")
    atomic_json(settings, asdict(config))
    command = [sys.executable, str(Path(__file__).resolve()), "--_stage", stage, "--_device", device,
               "--_config", str(settings), "--fixture", str(fixture), "--output", str(output), "--_weights", str(weights)]
    environment = {**os.environ, "PYTORCH_ENABLE_MPS_FALLBACK": "0", "OPENBLAS_NUM_THREADS": "1",
                   **{key: str(config.threads) for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}}
    peak, reason, diagnostic = 0, None, None
    # Charge the whole configured MPS allocator reserve throughout the update,
    # including intervals with no host telemetry. This intentionally may count
    # the same unified-memory pages twice, rather than omit driver allocations.
    allocator_reserve = (config.memory_bytes - 2_000_000_000) // 2 if device == "mps" else 0
    with Path(output).with_suffix(".stdout.log").open("w") as stdout, Path(output).with_suffix(".stderr.log").open("w") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            while process.poll() is None:
                try:
                    charged = aggregate_rss(process.pid) + allocator_reserve
                    peak = max(peak, charged)
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    reason, diagnostic = "memory_monitor_failure", monitor_error_details(error, "update_benchmark_memory", root_pid=process.pid)
                    break
                if charged >= config.memory_bytes - 1_000_000_000:
                    reason = "memory_limit"; break
                if time.monotonic() >= deadline:
                    reason = "wall_limit"; break
                time.sleep(.2)
            if reason:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
    result = json.loads(Path(output).read_text()) if Path(output).exists() else {}
    require(reason is None and process.returncode == 0 and result.get("status") == "completed",
            f"{stage}/{device} did not complete: {reason or 'worker_error'}; returncode={process.returncode}; diagnostic={diagnostic}; see stderr log")
    result["guard"] = {"peak_charged_bytes": peak, "memory_bytes": config.memory_bytes, "metric": memory_metric(),
                       "absolute_deadline_monotonic": deadline, "allocator_limit": result.get("allocator"),
                       "extra_mps_allocator_reservation_bytes": allocator_reserve,
                       "gpu_scope": "Full configured allocator reservation added to physical process-tree charge; conservative possible double counting"}
    return result


def run(config, output):
    import torch
    torch.set_num_threads(config.threads)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    artifacts = output.with_name(output.stem + ".artifacts")
    require(not output.exists() and not artifacts.exists(), "Choose fresh benchmark output; existing evidence is preserved")
    artifacts.mkdir()
    deadline = time.monotonic() + config.seconds
    fixture = artifacts / "terminal-game.pt"
    report = {"schema": SCHEMA, "status": "running", "config": asdict(config), "devices": [],
              "purpose": "Matched actual learning-update timing, not end-to-end training throughput or playing strength"}
    atomic_json(output, report)
    try:
        report["preparation"] = supervise("prepare", "cpu", config, fixture, artifacts / "prepare.json", artifacts / "unused.pt", deadline)
        for device in config.devices:
            result = supervise("update", device, config, fixture, artifacts / f"{device}.json", artifacts / f"{device}-weights.pt", deadline)
            require(result["fixture_sha256"] == report["preparation"]["fixture_sha256"] == sha(fixture),
                    "Device worker used different fixture bytes from preparation")
            report["devices"].append(result)
            atomic_json(output, report)
        if len(config.devices) > 1:
            a, b = config.devices[:2]
            report["comparison"] = compare_updates(report["devices"][0], report["devices"][1],
                torch.load(artifacts / f"{a}-weights.pt", map_location="cpu", weights_only=False),
                torch.load(artifacts / f"{b}-weights.pt", map_location="cpu", weights_only=False), atol=config.atol, rtol=config.rtol)
        report["status"] = "completed"
    except BaseException as error:
        report.update(status="incomplete", error=f"{type(error).__name__}: {error}")
        atomic_json(output, report)
        raise
    atomic_json(output, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--devices", default="cpu,mps")
    parser.add_argument("--seconds", type=float, default=900.)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--memory-bytes", type=int, default=24_000_000_000)
    parser.add_argument("--game-seed", type=int, default=1951)
    parser.add_argument("--_stage", choices=("prepare", "update"))
    parser.add_argument("--_device", default="cpu")
    parser.add_argument("--_config", type=Path)
    parser.add_argument("--_weights", type=Path)
    args = parser.parse_args(argv)
    if args._stage:
        values = json.loads(args._config.read_text()); values["devices"] = tuple(values["devices"])
        return worker(args._stage, args._device, UpdateConfig(**values), args.fixture, args.output, args._weights)
    result = run(UpdateConfig(devices=tuple(args.devices.split(",")), seconds=args.seconds, threads=args.threads,
                              memory_bytes=args.memory_bytes, game_seed=args.game_seed), args.output)
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return result


if __name__ == "__main__":
    main()
