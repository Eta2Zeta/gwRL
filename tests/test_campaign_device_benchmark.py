"""Device timing stays synchronized, matched and honest about unfinished games."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from tools.benchmark_campaign_devices import (Config, TimedEvaluator, compare_selfplay,
    mps_allocator_limit, numerical_comparison, selfplay, setup_models, supervise_device)


class ToyEnv:
    def __init__(self, seed, steps=1):
        self.seed, self.steps, self.state = seed, steps, 0
    def serialize(self): return json.dumps([self.seed, self.state])
    def planning_key(self): return self.serialize()
    def is_terminal(self): return self.state == self.steps
    def decision_kind(self): return "terminal" if self.is_terminal() else "production"
    def current_decision_player(self): return "axis"
    def legal_actions(self): return ["move"] if not self.is_terminal() else []
    def apply_action(self, action):
        if action != "move": raise ValueError("invalid")
        self.state += 1
    def returns(self): return [1., 2., 3.]
    def wealth(self): return {"axis": {"wealth": 1.}}
    def observation(self):
        done = self.is_terminal()
        return {"state": {"clock": {"completed_rounds": 3 if done else 0, "round_index": 2 if done else 0,
                "nation_index": 3 if done else 0, "phase": "place_units" if done else "production",
                "income_collected": done, "player_turn_serial": "12" if done else "0"},
                "completed_turns": {nation: 3 if done else 0 for nation in ("ccp", "mongolia", "japan", "kmt")}}}


class FakeEvaluator:
    version = "test"
    def __init__(self):
        from collections import Counter
        self.seconds, self.calls, self.requests, self.batch_sizes = 0., 0, 0, Counter()
    def evaluate_batch(self, requests):
        self.calls += 1; self.requests += len(requests); self.batch_sizes[len(requests)] += 1
        return [SimpleNamespace(priors=[1.], values=[0., 0., 0.]) for _ in requests]


class CampaignDeviceBenchmarkTests(unittest.TestCase):
    def test_configuration_preserves_search_budget_and_resource_allowance(self):
        for values in ({"devices": ("cpu", "auto")}, {"simulations": 4}, {"max_depth": 8},
                       {"threads": 10}, {"memory_bytes": 30_000_000_001}, {"batch_sizes": (1, 1)}):
            with self.subTest(values=values), self.assertRaises(ValueError): Config(**values)

    def test_allocator_cap_leaves_room_for_native_cpu_and_aggregate_guard(self):
        result = mps_allocator_limit(24_000_000_000, 30_000_000_000)
        self.assertEqual(result["allocator_limit_bytes"], 11_000_000_000)
        self.assertEqual(result["cpu_native_reserve_bytes"], 13_000_000_000)
        self.assertLessEqual(result["per_process_fraction"], 1.)
        with self.assertRaises(ValueError): mps_allocator_limit(24_000_000_000, 0)

    def test_timed_evaluator_synchronizes_both_boundaries(self):
        events = []
        class Inner:
            version = "same"
            def evaluate_batch(self, requests): events.append("forward"); return requests
        evaluator = TimedEvaluator(Inner(), "mps", lambda device: events.append(device))
        self.assertEqual(evaluator.evaluate_batch([1, 2]), [1, 2])
        self.assertEqual(events, ["mps", "forward", "mps"])
        self.assertEqual(evaluator.requests, 2)
        self.assertEqual(evaluator.batch_sizes[2], 1)

    def test_numerical_comparison_allows_close_top_action_divergence_but_detects_large_errors(self):
        left = [{"priors": [.5000001, .4999999], "values": [10., 20., 30.]}]
        right = [{"priors": [.4999999, .5000001], "values": [10.0001, 20., 30.]}]
        result = numerical_comparison(left, right, atol=.002, rtol=.0002)
        self.assertTrue(result["within_tolerance"]); self.assertEqual(result["top_action_mismatches"], 1)
        right[0]["values"][0] = 11.
        self.assertFalse(numerical_comparison(left, right, atol=.002, rtol=.0002)["within_tolerance"])
        with self.assertRaises(ValueError): numerical_comparison(left, [], atol=.002, rtol=.0002)

    def test_fresh_cpu_weights_match_without_changing_current_model_dimensions(self):
        config = Config(devices=("cpu",), threads=1, cpu_budget=4)
        first = setup_models(config, "cpu")
        second = setup_models(config, "cpu")
        self.assertEqual(first[3]["weights_sha256"], second[3]["weights_sha256"])
        self.assertEqual(first[3]["config"]["hidden_dim"], 16)
        self.assertEqual(first[3]["config"]["message_layers"], 1)
        self.assertEqual(first[3]["config"]["token_buckets"], 2048)
        self.assertTrue(all(parameter.device.type == "cpu" for model in first[0].values() for parameter in model.parameters()))

    def run_toy(self, steps=1, cap=5000):
        config = Config(mode="selfplay", devices=("cpu",), seeds=(7,), threads=1, cpu_budget=5, max_transitions=cap)
        evaluator = FakeEvaluator()
        def search(envs, evaluator, *, configs, stats, **kwargs):
            self.assertTrue(all(row.simulations == row.max_depth == 16 for row in configs))
            stats.elapsed_seconds = 0.
            return [SimpleNamespace(actions=["move"], policy=[1.]) for _ in envs]
        with patch("studies.campaign.curriculum.make_env", side_effect=lambda seed, **_: ToyEnv(seed, steps)), \
             patch("studies.campaign.curriculum.task_manifest", return_value={"calendar_rounds": 3}), \
             patch("studies.campaign.batching.search_many", side_effect=search):
            return selfplay(config, "cpu", {}, evaluator, {"seconds": 0.}, float("inf"), lambda _: None)

    def test_selfplay_requires_real_terminal_clock_and_preserves_search_settings(self):
        report = self.run_toy()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["completed_games"], 1)
        self.assertGreater(report["complete_three_round_games_per_hour"], 0)
        self.assertEqual(report["games"][0]["clock"]["completed_rounds"], 3)

    def test_truncated_selfplay_has_no_completed_cohort_throughput_or_fake_returns(self):
        report = self.run_toy(steps=3, cap=1)
        self.assertEqual(report["status"], "truncated")
        self.assertIsNone(report["complete_three_round_games_per_hour"])
        self.assertIsNone(report["games"][0]["terminal_returns"])
        self.assertEqual(report["completed_games"], 0)

    def test_selfplay_comparison_reports_divergence_without_claiming_exact_workload(self):
        left = self.run_toy(); right = copy.deepcopy(left)
        right["games"][0]["trace"][0]["action"] = "different"
        result = compare_selfplay(left, right)
        self.assertFalse(result["pairs"][0]["identical_trace"])
        self.assertEqual(result["pairs"][0]["common_exact_trace_prefix"], 0)
        right["status"] = "truncated"
        with self.assertRaises(ValueError): compare_selfplay(left, right)

    def test_fresh_worker_explicitly_disables_mps_fallback_and_handles_null_cpu_driver_memory(self):
        class Process:
            pid, returncode, polls = 4242, 0, 0
            def poll(self):
                self.polls += 1
                return None if self.polls == 1 else 0
            def wait(self, timeout): return 0
        environments = []
        def launch(command, **kwargs):
            environments.append(kwargs["env"])
            Path(command[command.index("--output") + 1]).write_text(json.dumps(
                {"status": "completed", "device_memory": {"driver_allocated_bytes": None}}))
            return Process()
        with tempfile.TemporaryDirectory() as directory, \
             patch("tools.benchmark_campaign_devices.subprocess.Popen", side_effect=launch), \
             patch("tools.supervise_campaign_training.aggregate_rss", return_value=1_000_000), \
             patch("tools.benchmark_campaign_devices.time.sleep"):
            report = supervise_device(Config(threads=1, cpu_budget=4), "cpu", Path(directory) / "out.json", 5.)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(environments[0]["PYTORCH_ENABLE_MPS_FALLBACK"], "0")

    def test_guard_preserves_intentional_incomplete_exit(self):
        class Process:
            pid, returncode = 4242, 2
            def poll(self): return 2
            def wait(self, timeout): return 2
        def launch(command, **kwargs):
            Path(command[command.index("--output") + 1]).write_text(json.dumps({"status": "truncated"}))
            return Process()
        with tempfile.TemporaryDirectory() as directory, patch(
                "tools.benchmark_campaign_devices.subprocess.Popen", side_effect=launch):
            report = supervise_device(Config(threads=1, cpu_budget=4), "cpu", Path(directory) / "out.json", 5.)
        self.assertEqual(report["status"], "truncated")
        self.assertEqual(report["guard"]["worker_returncode"], 2)


if __name__ == "__main__": unittest.main()
