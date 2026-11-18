"""tools/compare_training_runs.py on a small run directory and evaluation bundles written here."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.compare_training_runs import HOUR, paired, read_evaluations, read_run


def _game(axis_score: float, allies_score: float, value_error: float) -> dict:
    return {"observed_terminal_returns": [axis_score, allies_score, 0.0],
            "fresh_losses": {"axis": {"samples": 1, "value_squared_error": value_error,
                                      "policy_cross_entropy": 2.0, "policy_kl": 0.5}}}


def _update(elapsed: float, decisions: int, evaluations: int, games: list[dict]) -> dict:
    return {"elapsed_seconds": elapsed, "update_seconds": 10.0, "episodes": games,
            "evaluator": {"evaluations": evaluations, "forward_seconds": evaluations * 1e-4,
                          "idle_seconds": 1.0, "serving_rounds": evaluations // 10}}


class CompareTrainingRunsTest(unittest.TestCase):
    def test_a_resumed_run_adds_its_parts_and_scores_against_the_variance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            # Two invocations: the second restarts its clock and its server counters.
            progress = [
                {"event": "update", "elapsed_seconds": 1000.0, "counters": {}},
                {"event": "update", "elapsed_seconds": 3000.0, "counters": {}},
                {"event": "interrupted", "elapsed_seconds": 3200.0,
                 "counters": {"updates": 2, "episodes": 4, "decisions": 4000, "transitions": 5000}},
                {"event": "update", "elapsed_seconds": 500.0, "counters": {}},
                {"event": "interrupted", "elapsed_seconds": 1600.0,
                 "counters": {"updates": 3, "episodes": 6, "decisions": 7000, "transitions": 8000}},
            ]
            (run / "progress.jsonl").write_text("".join(json.dumps(line) + "\n" for line in progress))
            updates = [
                _update(1000.0, 1000, 1000, [_game(100.0, -100.0, 0.5), _game(-100.0, 100.0, 0.5)]),
                _update(3000.0, 3000, 3000, []),
                _update(500.0, 500, 600, [_game(50.0, -50.0, 0.1)]),
            ]
            manifest = {"status": "interrupted",
                        "runner": {"config": {"value_scale": 100.0, "networks": "one"}, "updates": updates}}
            (run / "manifest.json").write_text(json.dumps(manifest))

            report = read_run(run)

        self.assertEqual(report["networks"], "one")
        self.assertEqual(report["active_seconds"], 4800.0)
        self.assertEqual([update["active_seconds"] for update in report["updates"]], [1000.0, 3000.0, 3700.0])
        first, second = report["speed"]
        self.assertEqual((first["seconds"], first["network_updates"], first["games"], first["decisions"]),
                         (3200.0, 2, 4, 4000))
        self.assertEqual((second["seconds"], second["network_updates"], second["games"], second["decisions"]),
                         (1600.0, 1, 2, 3000))
        self.assertAlmostEqual(second["decisions_per_hour"], 3000 / 1600 * HOUR)
        # The server's counters at each part's last network update: 3,000 evaluations, then 600.
        self.assertAlmostEqual(first["forward_microseconds_per_evaluation"], 100.0)
        self.assertAlmostEqual(first["evaluations_per_inference_batch"], 10.0)
        self.assertAlmostEqual(second["server_idle_share"], 1.0 / 500.0)

        # The first hour's two games: final scores ±1 for the Axis and the Allies, 0 for the
        # Comintern after dividing by value_scale, so the variance averaged over the three
        # alliances is 2/3 and a value loss of 0.5 explains a quarter of it.
        hour = report["hours"][0]
        self.assertEqual((hour["network_updates"], hour["games"]), (2, 2))  # The second update had no games.
        self.assertAlmostEqual(hour["losses"]["all"]["score_variance"], 2 / 3)
        self.assertAlmostEqual(hour["losses"]["all"]["explained"], 0.25)
        self.assertAlmostEqual(hour["losses"]["axis"]["policy_kl"], 0.5)
        # Hour two holds the resumed part's update, at 3,200 + 500 = 3,700 active seconds.
        self.assertEqual((report["hours"][1]["network_updates"], report["hours"][1]["games"]), (1, 1))
        self.assertEqual(report["after_first_hour"]["network_updates"], 1)

    def test_held_out_games_are_paired_by_seed(self) -> None:
        def bundle(path: Path, target: str, scores: dict[int, float]) -> None:
            index = ("axis", "allies", "comintern").index(target)
            games = []
            for seed, score in scores.items():
                returns = [0.0, 0.0, 0.0]
                returns[index] = score
                games.append({"seed": seed, "observed_terminal_returns": returns,
                              "decisions_by_actor": {target: 10}})
            games.append({"seed": 99, "truncated": True, "observed_terminal_returns": None,
                          "decisions_by_actor": {target: 5}})
            path.write_text(json.dumps({"results": [{"target_player": target, "games": games}]}))

        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "first.json", Path(directory) / "second.json"
            bundle(first, "allies", {1: 10.0, 2: 20.0, 3: 30.0})
            bundle(second, "allies", {1: 5.0, 2: 25.0})
            a, b = read_evaluations([first]), read_evaluations([second])

        self.assertEqual((a["allies"]["games"], a["allies"]["unfinished"]), (3, 1))
        self.assertAlmostEqual(a["allies"]["mean"], 20.0)
        self.assertAlmostEqual(a["allies"]["standard_error"], 10.0 / 3 ** 0.5)
        difference = paired(a, b)["allies"]
        # Seeds 1 and 2 only: differences +5 and -5.
        self.assertEqual((difference["seeds"], difference["first_higher"]), (2, 1))
        self.assertAlmostEqual(difference["mean"], 0.0)
        self.assertAlmostEqual(difference["standard_error"], 5.0)


if __name__ == "__main__":
    unittest.main()
