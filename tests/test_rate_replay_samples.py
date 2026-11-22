"""The arithmetic of tools/rate_replay_samples.py, on samples made up here."""
from __future__ import annotations

import math
import unittest

import numpy as np

from tools.rate_replay_samples import (decision_kind, explained, game_folds, linear_predictions,
                                       option_bucket, ridge_fit_predict, summarize, target_facts)


class TargetFactsTest(unittest.TestCase):
    def test_a_split_search_names_its_most_visited_action_and_the_chance_of_another(self) -> None:
        facts = target_facts([0.5, 0.25, 0.25, 0.0], [0.1, 0.6, 0.2, 0.1])
        self.assertEqual(facts["top_share"], 0.5)
        self.assertEqual(facts["visited"], 3)
        self.assertAlmostEqual(facts["not_top"], 0.5)
        self.assertEqual(facts["agree"], 0.0)  # The network likes the second action best.
        expected = 0.5 * math.log(0.5 / 0.1) + 0.25 * math.log(0.25 / 0.6) + 0.25 * math.log(0.25 / 0.2)
        self.assertAlmostEqual(facts["kl"], expected)

    def test_tied_most_visited_actions_count_as_most_visited(self) -> None:
        facts = target_facts([0.4, 0.4, 0.2], [0.2, 0.7, 0.1])
        self.assertAlmostEqual(facts["not_top"], 0.2)
        self.assertEqual(facts["agree"], 1.0)

    def test_a_forced_decision_teaches_nothing_about_the_policy(self) -> None:
        facts = target_facts([1.0], [1.0])
        self.assertEqual((facts["not_top"], facts["kl"], facts["agree"]), (0.0, 0.0, 1.0))


class KindAndBucketTest(unittest.TestCase):
    def test_ending_the_phase_names_a_decision_only_when_nothing_else_is_legal(self) -> None:
        self.assertEqual(decision_kind({"end_phase": 1, "movement_route": 3, "naval_route": 2}), "movement_route")
        self.assertEqual(decision_kind({"end_phase": 1}), "end_phase")

    def test_buckets_of_legal_actions(self) -> None:
        self.assertEqual([option_bucket(n) for n in (1, 2, 4, 5, 16, 17, 63, 64, 300)],
                         ["1", "2-4", "2-4", "5-16", "5-16", "17-63", "17-63", "64 or more", "64 or more"])


class LinearModelTest(unittest.TestCase):
    def test_ridge_with_a_small_penalty_recovers_a_linear_rule(self) -> None:
        rng = np.random.default_rng(1)
        x = rng.normal(size=(40, 5))
        y = x @ np.array([[1.0], [-2.0], [0.0], [0.5], [3.0]]) + 7.0
        predicted = ridge_fit_predict(x[:30], y[:30], x[30:], 1e-8)
        np.testing.assert_allclose(predicted, y[30:], atol=1e-5)

    def test_folds_keep_each_games_samples_together(self) -> None:
        targets = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [1.0, 2.0, 3.0], [7.0, 8.0, 9.0]] * 10
        fold = game_folds(targets)
        for first in range(len(targets)):
            for second in range(len(targets)):
                if targets[first] == targets[second]:
                    self.assertEqual(fold[first], fold[second])

    def test_held_out_games_are_predicted_without_their_own_samples(self) -> None:
        rng = np.random.default_rng(2)
        x = rng.normal(size=(200, 3))
        y = np.column_stack([x[:, 0] * 10, x[:, 1] * -5, x[:, 2]]) + rng.normal(scale=0.1, size=(200, 3))
        fold = np.arange(200) % 5
        predicted, penalties = linear_predictions(x, y, fold)
        self.assertEqual(len(penalties), 5)
        self.assertGreater(explained(predicted[:, 0], y[:, 0]), 0.99)

    def test_explained_variance_is_negative_when_worse_than_the_mean(self) -> None:
        target = np.array([1.0, -1.0, 1.0, -1.0])
        self.assertAlmostEqual(explained(np.zeros(4), target), 0.0)
        self.assertLess(explained(-target, target), 0.0)
        self.assertIsNone(explained(np.zeros(2), np.array([3.0, 3.0])))


class SummaryTest(unittest.TestCase):
    def test_values_by_game_round_beside_the_linear_model(self) -> None:
        rows = []
        for index in range(8):
            score = float(index)
            rows.append({"owner": "axis", "round": 1 + index % 2, "options": 3, "kind": "movement_route",
                         "family": "movement", "bucket": "2-4", "generation": index % 2,
                         "targets": [score, -score, 0.5 * score], "predicted": [score, 0.0, 0.0],
                         **target_facts([0.5, 0.5, 0.0], [0.4, 0.4, 0.2])})
        linear = {game_round: np.array([row["targets"] for row in rows if row["round"] == game_round])
                  for game_round in (1, 2)}
        summary = summarize(rows, linear)
        first = summary["values_by_round"]["1"]
        self.assertEqual(first["samples"], 4)
        self.assertAlmostEqual(first["axis"]["network"], 1.0)
        self.assertAlmostEqual(first["axis"]["linear"], 1.0)
        self.assertLess(first["allies"]["network"], 0.0)
        self.assertEqual(summary["forced"], 0)
        self.assertEqual(summary["games"], 8)
        self.assertAlmostEqual(summary["by_options"]["2-4"]["not_top"], 0.0)


if __name__ == "__main__":
    unittest.main()
