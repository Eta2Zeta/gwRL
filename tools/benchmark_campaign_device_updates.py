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
# Each scalar is added to every sibling logit before a conditional softmax.
# These five exact parameters are functionally redundant, but their raw drift
# remains part of the original parameter-conformance verdict below.
COMMON_LOGIT_BIASES = ("policy_head.2.bias", *(f"factor_heads.{index}.2.bias" for index in range(4)))
FUNCTIONAL_ROWS = 32
FUNCTIONAL_POLICY_ATOL = .00002
FUNCTIONAL_VALUE_ATOL = .002
FUNCTIONAL_RTOL = .0002


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
    from studies.campaign.learning import CampaignLearner, TARGET_SCHEMA, retained_numeric_input
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
            features = retained_numeric_input(features)
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
              "device_runtime": learner._device_runtime.stats() if learner._device_runtime is not None else None,
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
    checks, maximum, parameter_details = {}, 0.0, {}
    for player in first_weights:
        require(set(first_weights[player]) == set(second_weights[player]), "Compared architectures differ")
        require(all(name in first_weights[player] and first_weights[player][name].shape == (1,) and
                    second_weights[player][name].shape == (1,) for name in COMMON_LOGIT_BIASES),
                "The five common-logit biases must have their exact names and scalar shapes")
        matched, nonredundant_matched, details = True, True, []
        for name, tensor in first_weights[player].items():
            other = second_weights[player][name]
            require(tensor.shape == other.shape and tensor.dtype == other.dtype, "Compared parameter layouts differ")
            require(torch.isfinite(tensor).all() and torch.isfinite(other).all(), "Compared model contains nonfinite weights")
            difference = float((tensor - other).abs().max()) if tensor.numel() else 0.0
            maximum = max(maximum, difference)
            within = bool(torch.allclose(tensor, other, atol=atol, rtol=rtol))
            redundant = name in COMMON_LOGIT_BIASES
            matched = matched and within
            nonredundant_matched = nonredundant_matched and (redundant or within)
            details.append({"name": name, "shape": list(tensor.shape), "common_logit_bias": redundant,
                            "max_absolute_difference": difference, "within_original_tolerance": within,
                            "outside_original_tolerance_scalars": int(((tensor - other).abs() >
                                atol + rtol * other.abs()).sum())})
        a = [row[key] for row in first["update"]["losses"][player] for key in ("policy", "value", "total")]
        b = [row[key] for row in second["update"]["losses"][player] for key in ("policy", "value", "total")]
        checks[player] = {"weights_within_tolerance": matched,
                          "losses_within_tolerance": bool(torch.allclose(torch.tensor(a), torch.tensor(b), atol=atol, rtol=rtol))}
        parameter_details[player] = {"nonredundant_weights_within_original_tolerance": nonredundant_matched,
                                    "max_nonredundant_absolute_difference": max(
                                        (row["max_absolute_difference"] for row in details if not row["common_logit_bias"]), default=0.),
                                    "parameters": details}
    return {"initial_weights_exact": True, "sample_order_exact": True, "atol": atol, "rtol": rtol,
            "max_weight_absolute_difference": maximum, "by_agent": checks,
            "parameter_diagnostics": {"excluded_from_nonredundant_check_only": list(COMMON_LOGIT_BIASES),
                                      "by_agent": parameter_details,
                                      "nonredundant_weights_within_original_tolerance": all(
                                          row["nonredundant_weights_within_original_tolerance"] for row in parameter_details.values()),
                                      "raw_parameter_verdict_unchanged": True},
            "numerically_matched": all(all(row.values()) for row in checks.values()),
            "update_speed_ratio_first_over_second": first["synchronized_update_seconds"] / second["synchronized_update_seconds"]}


def functional_row_indices(samples):
    """Thirty-two chronological positions spread across all three actors."""
    from studies.shared.multiplayer_mcts import PLAYERS
    require(len(samples) >= FUNCTIONAL_ROWS and set(row["owner"] for row in samples) == set(PLAYERS),
            "Functional diagnostics require thirty-two rows and all three actors")
    populations = {player: [index for index, row in enumerate(samples) if row["owner"] == player] for player in PLAYERS}
    counts = dict.fromkeys(PLAYERS, 0)
    for _ in range(FUNCTIONAL_ROWS):
        available = [player for player in PLAYERS if counts[player] < len(populations[player])]
        player = min(available, key=lambda item: counts[item])
        counts[player] += 1
    selected = []
    for player, count in counts.items():
        population = populations[player]
        selected.extend(population[round(index * (len(population) - 1) / (count - 1))] if count > 1 else population[0]
                        for index in range(count))
    require(len(set(selected)) == FUNCTIONAL_ROWS, "Functional stratification repeated a position")
    return sorted(selected), counts


def compare_functional_weights(fixture, first_weights, second_weights, config):
    """Evaluate final weights on one CPU backend, separately from update timing.

    This reports sampled function conformance, not equality of parameters or
    playing strength. No legal action is removed from an actor's selected menu;
    every model also predicts all three values at every selected position.
    """
    import torch
    from studies.campaign.learning import _value_only_input
    from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, clear_neural_caches
    from studies.campaign.run import source_hashes
    from studies.shared.multiplayer_mcts import PLAYERS
    from tools.benchmark_campaign_devices import numerical_comparison
    started = time.perf_counter()
    torch.set_num_threads(min(config.threads, 2))
    samples = validate_fixture(fixture, config)
    runtime_before, tool_before = source_hashes(), sha(__file__)
    indices, counts = functional_row_indices(samples)
    selected = [samples[index] for index in indices]
    model_config = CampaignModelConfig(hidden_dim=config.hidden_dim, message_layers=config.message_layers,
                                       token_buckets=config.token_buckets, value_scale=config.value_scale)
    require(set(first_weights) == set(second_weights) == set(PLAYERS), "Functional comparison requires all three models")
    gauge_weights = {}
    for player in PLAYERS:
        require(set(first_weights[player]) == set(second_weights[player]), "Compared architectures differ")
        for name in COMMON_LOGIT_BIASES:
            require(first_weights[player][name].shape == second_weights[player][name].shape == (1,),
                    "Common-logit gauge replacement requires five exact scalar biases")
        gauge_weights[player] = {name: (second_weights[player][name] if name in COMMON_LOGIT_BIASES else value)
                                 for name, value in first_weights[player].items()}
    variants = {}
    # Construction consumes only CPU randomness and all weights are overwritten.
    # Restore that randomness so this diagnostic cannot change later sampling.
    with torch.random.fork_rng(devices=[]):
        for variant, weights in (("first_final", first_weights), ("second_final", second_weights),
                                  ("first_final_only_common_biases_from_second", gauge_weights)):
            by_model = {}
            before = time.perf_counter()
            for player in PLAYERS:
                model = CampaignPolicyValueNet(model_config, device="cpu").eval()
                expected = model.state_dict()
                require(set(expected) == set(weights[player]) and all(value.device.type == "cpu" and
                        value.dtype == expected[name].dtype and value.shape == expected[name].shape and
                        bool(torch.isfinite(value).all()) for name, value in weights[player].items()),
                        "Functional diagnostics require complete finite CPU weights without dtype conversion")
                model.load_state_dict(weights[player], strict=True)
                inputs = [sample["input"] if sample["owner"] == player else _value_only_input(sample["input"])
                          for sample in selected]
                with torch.inference_mode():
                    logits, values = model.forward_batch(inputs)
                    raw_values = values * model_config.value_scale
                    by_model[player] = [{"fixture_index": index, "owner": sample["owner"],
                        "priors": logit.softmax(0).tolist() if logit.numel() else [],
                        "values": value.tolist(), "logits": logit.tolist()}
                        for index, sample, logit, value in zip(indices, selected, logits, raw_values, strict=True)]
                clear_neural_caches([model], device="cpu")
                del model, inputs, logits, values, raw_values, expected
            variants[variant] = {"cpu_seconds": time.perf_counter() - before, "by_model": by_model}
    comparisons = {}
    for variant in ("second_final", "first_final_only_common_biases_from_second"):
        by_model = {}
        for player in PLAYERS:
            left, right = variants["first_final"]["by_model"][player], variants[variant]["by_model"][player]
            result = numerical_comparison(left, right, atol=FUNCTIONAL_VALUE_ATOL, rtol=FUNCTIONAL_RTOL)
            rows = []
            for a, b in zip(left, right, strict=True):
                rows.append({"fixture_index": a["fixture_index"], "owner": a["owner"],
                    "policy_scalar_count": len(a["priors"]), "raw_value_scalar_count": len(a["values"]),
                    "maximum_policy_probability_error": max((abs(x-y) for x, y in zip(a["priors"], b["priors"], strict=True)), default=0.),
                    "maximum_raw_value_error": max(abs(x-y) for x, y in zip(a["values"], b["values"], strict=True)),
                    "maximum_logit_error": max((abs(x-y) for x, y in zip(a["logits"], b["logits"], strict=True)), default=0.)})
            by_model[player] = {**result, "rows": rows,
                "max_policy_probability_error": max(row["maximum_policy_probability_error"] for row in rows),
                "max_raw_value_error": max(row["maximum_raw_value_error"] for row in rows),
                "all_raw_values_bit_equal": all(a["values"] == b["values"] for a, b in zip(left, right, strict=True))}
        comparisons[variant] = by_model
    require(runtime_before == source_hashes() and tool_before == sha(__file__),
            "Runtime/tool changed during functional diagnostics; prepare a fresh fixture")
    return {"schema": "campaign-final-weight-functional-diagnostic-v1", "status": "completed", "device": "cpu",
            "torch_version": str(torch.__version__), "tensor_threads": torch.get_num_threads(),
            "runtime_source_sha256": runtime_before, "tool_sha256": tool_before,
            "fixture_rows": len(samples), "selected_indices": indices, "selected_owner_counts": counts,
            "selected_rows": [{"fixture_index": index, "owner": sample["owner"], "complete_menu_length": len(sample["policy"])}
                              for index, sample in zip(indices, selected, strict=True)],
            "selection": "Evenly spaced chronological positions within actor strata; thirty-two distinct real fixture rows",
            "policy_atol": FUNCTIONAL_POLICY_ATOL, "raw_value_atol": FUNCTIONAL_VALUE_ATOL, "rtol": FUNCTIONAL_RTOL,
            "common_logit_bias_names": list(COMMON_LOGIT_BIASES), "variants": variants, "comparisons": comparisons,
            "final_weights_functionally_within_unchanged_inference_tolerance": all(
                row["within_tolerance"] for row in comparisons["second_final"].values()),
            "bias_only_gauge_within_unchanged_inference_tolerance": all(
                row["within_tolerance"] for row in comparisons["first_final_only_common_biases_from_second"].values()),
            "cpu_seconds": time.perf_counter() - started,
            "timing_scope": "Separate CPU diagnostic after timed learning workers; fixture validation, model setup and all three final-weight variants included",
            "limitation": "Sampled functional conformance on thirty-two positions, not every state or evidence of improved play; strict raw parameter verdict is unchanged"}


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
    elif stage == "update":
        before = time.perf_counter()
        fixture_hash = sha(fixture_path)
        fixture = torch.load(fixture_path, map_location="cpu", weights_only=False)
        require(sha(fixture_path) == fixture_hash, "Fixture changed while it was loaded")
        loading = time.perf_counter() - before
        result, weights = perform_update(fixture, device, config)
        torch.save(weights, weights_path, pickle_protocol=5)
        require(sha(fixture_path) == fixture_hash, "Fixture changed during update")
        result.update(fixture_loading_seconds=loading, fixture_sha256=fixture_hash, weights_sha256=sha(weights_path))
    else:
        require(stage == "functional" and len(config.devices) == 2, "Functional diagnostics need two completed devices")
        paths = [Path(fixture_path), *(Path(weights_path) / f"{device}-weights.pt" for device in config.devices)]
        original = {str(path): sha(path) for path in paths}
        fixture, first, second = [torch.load(path, map_location="cpu", weights_only=False) for path in paths]
        result = compare_functional_weights(fixture, first, second, config)
        require(original == {str(path): sha(path) for path in paths}, "Functional diagnostic input files changed")
        result.update(source_files_sha256=original, fixture_sha256=original[str(paths[0])], tensor_threads=torch.get_num_threads())
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
    memory_limit = min(config.memory_bytes, 6_000_000_000) if stage == "functional" else config.memory_bytes
    if stage == "functional":
        deadline = min(deadline, time.monotonic() + 180.)
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
                if charged >= memory_limit - 1_000_000_000:
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
    result["guard"] = {"peak_charged_bytes": peak, "memory_bytes": memory_limit, "metric": memory_metric(),
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
            report["functional_final_weights"] = supervise("functional", "cpu", config, fixture,
                artifacts / "functional-final-weights.json", artifacts, deadline)
            require(report["functional_final_weights"]["fixture_sha256"] == report["preparation"]["fixture_sha256"],
                    "Functional diagnostic used different fixture bytes")
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
    parser.add_argument("--_stage", choices=("prepare", "update", "functional"))
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
