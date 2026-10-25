"""Measurement helpers preserve results and avoid false matched speed claims."""
from __future__ import annotations

import copy
from types import SimpleNamespace
import unittest

from tools.benchmark_campaign_native_concurrency import TimedNative, Timers, compare_reports, native_probe


class RawToy:
    def __init__(self, value=0):
        self.value = value

    def clone(self):
        return RawToy(self.value)

    def clone_for_search(self, _seed):
        return self.clone()

    def serialize(self):
        return str(self.value)

    def restore(self, value):
        self.value = int(value)

    def planning_key(self):
        return self.serialize()

    def decision_kind(self):
        return "move"

    def is_terminal(self):
        return False

    def legal_actions(self):
        return [SimpleNamespace(id="b"), SimpleNamespace(id="a")]

    def apply_action(self, action):
        self.value += 1 if action.id == "a" else 2


class ConcurrencyBenchmarkHelpers(unittest.TestCase):
    def test_nested_timers_include_cpu_and_keep_exception_accounting(self):
        timers = Timers()
        timers.enabled = True
        with self.assertRaisesRegex(ValueError, "fixture"):
            with timers.measure("outer"):
                with timers.measure("inner"):
                    raise ValueError("fixture")
        values = timers.snapshot()
        outer, inner = values["coordinator:outer"], values["coordinator:inner"]
        self.assertEqual(outer["calls"], inner["calls"])
        self.assertEqual(outer["calls"], 1)
        self.assertGreaterEqual(outer["wall_seconds"], inner["wall_seconds"])
        self.assertLessEqual(outer["exclusive_wall_seconds"], outer["wall_seconds"])
        self.assertGreaterEqual(outer["thread_cpu_seconds"], 0)

    def test_native_proxy_clones_retain_instrumentation_without_sharing_state(self):
        timers = Timers()
        timers.enabled = True
        original = TimedNative(RawToy(7), timers)
        clone = original.clone_for_search(1)
        self.assertIsInstance(clone, TimedNative)
        clone.apply_action(clone.legal_actions()[0])
        self.assertEqual(original.serialize(), "7")
        self.assertEqual(clone.serialize(), "9")
        self.assertEqual(timers.snapshot()["coordinator:engine.clone_for_search"]["calls"], 1)

    def test_native_probe_restores_each_repetition_and_preserves_original_games(self):
        roots = [SimpleNamespace(raw=RawToy(7)), SimpleNamespace(raw=RawToy(11))]
        before = [env.raw.serialize() for env in roots]
        result = native_probe(roots, 3)
        self.assertTrue(result["matched"])
        self.assertEqual(result["roots"], 2)
        self.assertEqual(len(result["outcome_sha256"]), 2)
        self.assertEqual(before, [env.raw.serialize() for env in roots])

    def test_comparison_requires_complete_reports_and_identical_search_outputs(self):
        original = {"status": "completed", "task": {"rounds": 3}, "model": {"weights": "a"},
            "prepared_state_sha256": ["initial"], "samples": [], "roots": [{"terminal": True}],
            "config": {"simulations": 16}, "timings_seconds": {"search": 1.0},
            "concurrency_measurement": {"search_count": 1, "search_results_sha256": "search",
                "final_engine_state_and_rng_sha256": ["final"], "instrumented": False,
                "wrapper_sha256": "wrapper"}}
        modified = copy.deepcopy(original)
        modified["timings_seconds"]["search"] = 0.5
        self.assertTrue(compare_reports(modified, original)["matched"])
        modified["concurrency_measurement"]["search_results_sha256"] = "different"
        self.assertFalse(compare_reports(modified, original)["matched"])
        self.assertFalse(compare_reports({}, {})["matched"])
        modified = copy.deepcopy(original)
        modified["status"] = "wall_limit"
        self.assertFalse(compare_reports(modified, original)["matched"])


if __name__ == "__main__":
    unittest.main()
