"""tools/train_on_saved_samples.py: which games train and which are held out, the value report, and training
steps on a toy network that reads made-up samples."""
from __future__ import annotations

import unittest

import numpy as np
import torch

from studies.campaign.neural import _conditional_log_softmax
from tools.train_on_saved_samples import HELD_FOLD, rate, split_games, train_copy, value_report


class SplitGamesTest(unittest.TestCase):
    def test_only_games_played_on_after_the_start_generation_count_and_each_stays_whole(self) -> None:
        # Three games, known by their final scores: one played only by generation 2, one by 2 then 3, one by 4.
        old, mixed, new = [1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]
        targets = [old, old, mixed, mixed, new]
        generations = [2, 2, 2, 3, 4]
        fold = np.array([1, 1, HELD_FOLD, HELD_FOLD, 2])
        train, held = split_games(targets, generations, start=3, fold=fold)
        self.assertEqual(train, [4])
        self.assertEqual(held, [2, 3])  # The mixed game's generation-2 sample comes with it.


class ValueReportTest(unittest.TestCase):
    def test_explained_variance_by_game_round_and_the_value_loss(self) -> None:
        targets = np.array([[10.0, -10.0, 0.0], [-10.0, 10.0, 0.0], [20.0, -20.0, 4.0], [-20.0, 20.0, -4.0]])
        predicted = targets.copy()
        predicted[:, 1] = 0.0
        rounds = np.array([1, 1, 2, 2])
        report = value_report(predicted, targets, rounds, scale=100.0)
        self.assertAlmostEqual(report["overall"]["axis"], 1.0)
        self.assertAlmostEqual(report["overall"]["allies"], 0.0)
        self.assertAlmostEqual(report["by_round"]["2"]["comintern"], 1.0)
        self.assertAlmostEqual(report["value_loss"], np.mean(((predicted - targets) / 100) ** 2))


class ToyNetwork(torch.nn.Module):
    """Reads a sample's input, a vector, and gives three values and one logit per legal action."""

    def __init__(self) -> None:
        super().__init__()
        torch.manual_seed(0)
        self.values = torch.nn.Linear(2, 3)
        self.logits = torch.nn.Linear(2, 2)

    def forward_batch(self, inputs: list[torch.Tensor]) -> tuple[list[torch.Tensor], torch.Tensor]:
        stacked = torch.stack(inputs)
        return list(self.logits(stacked)), self.values(stacked)


class TrainCopyTest(unittest.TestCase):
    def test_training_steps_lower_the_weighted_value_loss_and_report_at_each_check(self) -> None:
        samples = [{"input": torch.tensor([float(i % 2), 1.0]), "policy": [0.75, 0.25],
                    "values": [30.0 if i % 2 else -30.0, 0.0, 10.0]} for i in range(16)]
        targets = np.array([sample["values"] for sample in samples])

        def check(model: ToyNetwork, step: int) -> dict:
            values, _ = rate(model, [sample["input"] for sample in samples], 100.0, torch)
            return {"step": step, "value_loss": float(np.mean(((values - targets) / 100) ** 2))}

        history = train_copy(ToyNetwork(), samples, list(range(16)), weight=50.0, steps=60, batch_size=4,
                             learning_rate=0.05, scale=100.0, log_softmax=_conditional_log_softmax, torch=torch,
                             seed=1, check_every=20, check=check)
        self.assertEqual([entry["step"] for entry in history], [0, 20, 40, 60])
        self.assertLess(history[-1]["value_loss"], history[0]["value_loss"] / 4)


if __name__ == "__main__":
    unittest.main()
