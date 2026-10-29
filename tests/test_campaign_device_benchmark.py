"""Device timing stays synchronized, matched and honest about unfinished games."""
from __future__ import annotations

import copy
from concurrent.futures import Future
import json
from pathlib import Path
import time
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from studies.shared.multiplayer_mcts import NoLegalActionError
from tools.benchmark_campaign_devices import (Config, TimedEvaluator, compare_selfplay,
    mps_allocator_limit, numerical_comparison, parallel_selfplay, selfplay, setup_models, supervise_device)


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
    def test_configuration_validates_search_budget_horizon_and_resource_allowance(self):
        selfplay_values = {"mode": "selfplay", "devices": ("cpu",), "threads": 1, "search_evaluation": "per_search"}
        self.assertEqual((Config(simulations=64, max_depth=24, calendar_rounds=11).simulations), 64)
        for values in ({"devices": ("cpu", "auto")}, {"simulations": 0}, {"max_depth": 0}, {"calendar_rounds": 12},
                       {"threads": 10}, {"memory_bytes": 30_000_000_001}, {"batch_sizes": (1, 1)},
                       {"search_evaluation": "streamed"}, {**selfplay_values, "processes": 5},
                       {**selfplay_values, "processes": 2, "search_evaluation": "batched"},
                       {**selfplay_values, "processes": 2, "threads": 2},
                       {**selfplay_values, "processes": 11, "seeds": tuple(range(11))}):
            with self.subTest(values=values), self.assertRaises(ValueError): Config(**values)
        self.assertEqual(Config(**selfplay_values, processes=10, seeds=tuple(range(10))).processes, 10)
        self.assertEqual(len(Config(**selfplay_values, processes=10, seeds=tuple(range(30))).seeds), 30)

    def test_parallel_selfplay_merges_games_in_seed_order_and_requires_identical_weights(self):
        class Immediate:
            def submit(self, function, *arguments):
                future = Future(); future.set_result(function(*arguments)); return future
        calls = []
        starts = {5: 100., 6: 101., 7: 110.}  # Seed 7 waits for the first free process.
        def run_group(values, seeds, deadline_epoch):
            calls.append(tuple(seeds))
            begin = starts[seeds[0]]
            return {"weights_sha256": "w", "process": 40 + seeds[0] % 2,
                    "forward": {"seconds": 1., "calls": len(seeds), "batch_sizes": {1: len(seeds)}},
                    "evaluator": {"synchronized_seconds": 2., "calls": len(seeds), "requests": len(seeds), "batch_sizes": {1: len(seeds)}},
                    "result": {"task": {"seed": seeds[0]}, "status": "completed", "stop_reason": None, "selection": "s", "failed_games": 0,
                               "started_at_epoch": begin, "ended_at_epoch": begin + 10 * len(seeds), "cohort_wall_seconds": 10. * len(seeds),
                               "preparation_seconds": 0., "warmup_seconds": 0., "timing_seconds": {"search": 3.},
                               "inference_calls": len(seeds), "inference_requests": len(seeds), "actual_inference_batch_sizes": {1: len(seeds)},
                               "games": [{"seed": seed, "terminal": True} for seed in seeds]}}
        config = Config(mode="selfplay", devices=("cpu",), threads=1, search_evaluation="per_search", processes=2,
                        seeds=(5, 6, 7), seconds=60.)
        summary, forward, evaluated = parallel_selfplay(config, "w", float("inf"), run_group=run_group, executor=Immediate())
        self.assertEqual(calls, [(5,), (6,), (7,)])
        self.assertEqual([game["seed"] for game in summary["games"]], [5, 6, 7])
        self.assertEqual([task["process"] for task in summary["game_tasks"]], [41, 40, 41])
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["cohort_wall_seconds"], 20.)  # 100 to 120, first start to last end
        self.assertEqual(summary["process_utilization"], 30. / 40.)
        self.assertEqual(summary["timing_seconds_summed_across_processes"], {"search": 9.})
        self.assertEqual((forward["calls"], evaluated["requests"]), (3, 3))
        self.assertEqual(summary["task"], {"seed": 5})
        with self.assertRaisesRegex(ValueError, "different fresh weights"):
            parallel_selfplay(config, "other", float("inf"), run_group=run_group, executor=Immediate())

    def test_real_game_processes_reproduce_single_process_games_exactly(self):
        config = Config(mode="selfplay", devices=("cpu",), threads=1, search_evaluation="per_search", processes=2,
                        seeds=(1951, 1952), max_transitions=2, seconds=240.)
        models, evaluator, forward_stats, metadata = setup_models(config, "cpu")
        summary, _, _ = parallel_selfplay(config, metadata["weights_sha256"], time.monotonic() + 240.)
        alone = selfplay(config, "cpu", models, evaluator, forward_stats, time.monotonic() + 240., lambda result=None: None)
        self.assertEqual([task["seed"] for task in summary["game_tasks"]], [1951, 1952])
        self.assertTrue(all(type(task["process"]) is int for task in summary["game_tasks"]))
        self.assertEqual([game["trace_sha256"] for game in summary["games"]], [game["trace_sha256"] for game in alone["games"]])
        self.assertEqual([game["final_state_and_rng_sha256"] for game in summary["games"]],
                         [game["final_state_and_rng_sha256"] for game in alone["games"]])
        self.assertTrue(all(game["transitions"] == 2 for game in summary["games"]))

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

    def run_toy(self, steps=1, cap=5000, seeds=(7,), choose=lambda env: "move", fail=None):
        config = Config(mode="selfplay", devices=("cpu",), seeds=seeds, threads=1, cpu_budget=4 + len(seeds),
                        max_transitions=cap)
        evaluator = FakeEvaluator()
        def search(envs, evaluator, *, configs, stats, **kwargs):
            self.assertTrue(all(row.simulations == row.max_depth == 16 for row in configs))
            stats.elapsed_seconds = 0.
            if fail is not None:
                raise fail
            return [SimpleNamespace(actions=[choose(env)], policy=[1.]) for env in envs]
        with patch("studies.campaign.curriculum.make_env", side_effect=lambda seed, **_: ToyEnv(seed, steps)), \
             patch("studies.campaign.curriculum.task_manifest", return_value={"calendar_rounds": 3}), \
             patch("studies.campaign.batching.search_many", side_effect=search):
            return selfplay(config, "cpu", {}, evaluator, {"seconds": 0.}, float("inf"), lambda _: None)

    def test_selfplay_requires_real_terminal_clock_and_preserves_search_settings(self):
        report = self.run_toy()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["completed_games"], 1)
        self.assertGreater(report["complete_games_per_hour"], 0)
        self.assertEqual(report["games"][0]["clock"]["completed_rounds"], 3)

    def test_truncated_selfplay_has_no_completed_cohort_throughput_or_fake_returns(self):
        report = self.run_toy(steps=3, cap=1)
        self.assertEqual(report["status"], "truncated")
        self.assertIsNone(report["complete_games_per_hour"])
        self.assertIsNone(report["games"][0]["terminal_returns"])
        self.assertEqual(report["completed_games"], 0)

    def test_a_failing_game_keeps_its_position_and_spares_the_others(self):
        report = self.run_toy(seeds=(7, 8), choose=lambda env: "stuck" if env.seed == 8 else "move")
        self.assertEqual(report["status"], "game_error")
        self.assertEqual((report["completed_games"], report["failed_games"]), (1, 1))
        self.assertIsNone(report["complete_games_per_hour"])
        self.assertIsNone(report["games"][0]["failure"])
        failure = report["games"][1]["failure"]
        self.assertEqual(failure["error"], "ValueError: invalid")
        self.assertEqual(json.loads(failure["position"]), [8, 0])
        searched = self.run_toy(fail=NoLegalActionError(ToyEnv(9)))["games"][0]["failure"]
        self.assertEqual(json.loads(searched["searched_position"]), [9, 0])

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
