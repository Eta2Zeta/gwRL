"""RNG component benchmark contracts without running a timed GPU workload."""
from dataclasses import replace
import json
import unittest

from tools.benchmark_campaign_random import GAMMA, MASK64, RandomConfig, make_workload, verify_rows


class RandomBenchmarkTests(unittest.TestCase):
    def test_exact_workload_preserves_all_streams_rejection_edges_and_tape(self):
        config = RandomConfig()
        requests, initial = make_workload(256, config)
        self.assertEqual(len(requests), len(initial))
        self.assertTrue(all(len(row["dice"]) == 16 for row in requests))
        self.assertTrue(all(die["sides"] == 12 and die["max_rerolls"] == 2 and die["reroll_faces"] == [1, 2]
                            for row in requests for die in row["dice"]))
        self.assertEqual({row["active"] for row in initial}, {"actual", "search", "training"})
        for row in initial[:3]:
            self.assertEqual(int(row[row["active"]]), (-GAMMA) & MASK64)
        taped = [row for row in initial if row["test_tape"]]
        self.assertTrue(taped)
        self.assertTrue(all(len(row["test_tape"]) == 49 and row["tape_position"] == "1" for row in taped))
        self.assertEqual((requests, initial), make_workload(256, config))

    def test_resource_and_workload_changes_are_explicitly_bounded(self):
        for change in ({"dice": 8}, {"lanes": (4, 4)}, {"lanes": (60,)}, {"lanes": (True,)},
                       {"threads": 3}, {"seconds": 121}, {"seconds": float("nan")},
                       {"memory_bytes": 7_000_000_000}, {"mps_reserve_bytes": 0}, {"repeats": 0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(RandomConfig(), **change)

    def test_parity_checks_every_stream_cursor_full_face_path_and_effective_result(self):
        before = {"actual": "0", "search": "7", "training": "8", "active": "actual",
                  "test_tape": [], "tape_position": "0"}
        after = {**before, "actual": str(GAMMA)}
        row = {"error": 0, "faces": [[3]], "effective": [4], "random": after}
        native = {**row, "error": "", "random": json.dumps(after)}
        result = verify_rows([row], [native], [before])
        self.assertTrue(result["all_lanes_bit_exact"])
        self.assertEqual(result["splitmix_draws_per_invocation_including_rejections"], 1)
        for changed in ({**row, "faces": [[2, 3]]}, {**row, "effective": [5]},
                        {**row, "random": {**after, "training": "9"}},
                        {**row, "random": {**after, "tape_position": "1"}}):
            with self.assertRaises(ValueError): verify_rows([changed], [native], [before])


if __name__ == "__main__":
    unittest.main()
