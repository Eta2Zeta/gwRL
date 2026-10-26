"""Connected clone component contract and full native oracle checks."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.benchmark_campaign_search_clone import (
    POSITIONS, SearchCloneConfig, exact_native_clones, run, seed_values,
)
from tools.benchmark_campaign_device_state import StateConfig, supervise


class CampaignSearchCloneBenchmarkTests(unittest.TestCase):
    def test_explicit_device_and_complete_seed_domain(self):
        config = SearchCloneConfig()
        self.assertEqual(config.batch_sizes, (1, 4, 64, 256))
        self.assertEqual(seed_values(4, 1951), [0, 1, 2**63, 2**64 - 1])
        self.assertEqual(seed_values(256, 1951), seed_values(256, 1951))
        self.assertEqual(len(seed_values(256, 1951)), 256)
        for changes in ({"devices": ("cpu",)}, {"devices": ("cpu", "mps")},
                        {"seconds": 181}, {"threads": 3}, {"repeats": 0}, {"memory_bytes": 8_000_000_001},
                        {"implementation": "unknown"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(config, **changes)

    def test_complete_oracle_detects_one_changed_random_bit(self):
        from studies.campaign.backends.device_state import DeviceStateBatch
        from studies.campaign.curriculum import make_env
        source = make_env(1951, calendar_rounds=3).raw
        clones = [source.clone_for_search(0), source.clone_for_search(2**64 - 1)]
        actual = DeviceStateBatch.capture(clones, device="cpu")
        evidence = exact_native_clones(actual, clones, inspection_chunk_bytes=1)
        self.assertTrue(evidence["exact"])
        self.assertEqual(evidence["verified_lanes"], 2)
        self.assertTrue(evidence["native_witnesses_exact"])
        position = int(actual.section("random.search")[1])
        actual.records[1, position, 2] ^= 1
        with self.assertRaises(AssertionError):
            exact_native_clones(actual, clones)

    def test_shared_guard_rejects_worker_outside_trusted_repository_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "outside.py"
            script.write_text("raise RuntimeError('must never execute')\n")
            with self.assertRaisesRegex(ValueError, "inside this repository"):
                supervise(StateConfig(), "cpu", Path(directory) / "output.json", deadline=10**20, worker_script=script)

    def test_report_requires_complete_grid_all_lanes_and_pins_worker_script(self):
        config = replace(SearchCloneConfig(), batch_sizes=(1,))
        def record(mismatch):
            cases = [{"position": label, "lanes": 1, "evidence": {
                "exact": True, "verified_lanes": 1, "native_witnesses_exact": True}} for label in POSITIONS]
            report = {"status": "completed", "sources_unchanged": True, "cases": cases}
            if mismatch == "missing":
                cases.pop()
            elif mismatch == "unchecked_lane":
                cases[0]["evidence"]["verified_lanes"] = 0
            elif mismatch == "changed_source":
                report["sources_unchanged"] = False
            return report
        with tempfile.TemporaryDirectory() as directory:
            for mismatch in (None, "missing", "unchecked_lane", "changed_source"):
                with patch("tools.benchmark_campaign_search_clone.supervise", return_value=record(mismatch)) as wrapped:
                    result = run(config, Path(directory) / f"{mismatch}.json")
                self.assertEqual(result["matched_full_native_clones_and_rng"], mismatch is None)
                self.assertEqual(wrapped.call_args.kwargs["worker_script"].name, "benchmark_campaign_search_clone.py")
            with self.assertRaises(ValueError):
                run(config, Path(directory) / "None.json")


if __name__ == "__main__":
    unittest.main()
