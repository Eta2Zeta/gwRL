"""Packed accelerator host outputs preserve the original per-row operations."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import torch
from torch import nn

from studies.campaign.neural import CampaignModelConfig, NeuralEvaluator, _gpu_evaluation_outputs
from studies.shared.multiplayer_mcts import PLAYERS, vector
from tests.test_campaign_neural import PublicEnv, action


class ConstantDeviceNet(nn.Module):
    def __init__(self, device):
        super().__init__()
        self.config = CampaignModelConfig(hidden_dim=8, token_buckets=64)
        self.value = nn.Parameter(torch.tensor([.25, -.1, .7], device=device))

    def forward_batch(self, items):
        return [torch.arange(len(item["actions"]), device=self.value.device, dtype=self.value.dtype) for item in items], \
            self.value.expand(len(items), -1)


class CampaignEvaluatorHostTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def fixture(self, device="cpu"):
        scores = [torch.tensor([5., -1., 2.], device=device), torch.empty(0, device=device),
                  torch.tensor([.2, .5], device=device)]
        values = torch.tensor([[.1, .2, .3], [-1., 0., 3.], [4., 5., -2.]], device=device)
        return scores, values, [3, 0, 2]

    def test_packed_rows_keep_same_softmax_and_two_host_boundaries(self):
        scores, values, counts = self.fixture()
        expected = ([row.softmax(0).tolist() if row.numel() else [] for row in scores],
                    [vector((row * 100).tolist()) for row in values])
        original = torch.Tensor.cpu
        copies = []

        def cpu_copy(tensor, *args, **kwargs):
            copies.append(tuple(tensor.shape))
            return original(tensor, *args, **kwargs)

        with patch.object(torch.Tensor, "cpu", cpu_copy):
            actual = _gpu_evaluation_outputs(scores, values, counts, 100)
        self.assertEqual(actual, expected)
        self.assertEqual(copies, [(5,), (3, 3)])

    def test_all_rows_are_validated_and_empty_menus_remain_empty(self):
        scores, values, counts = self.fixture()
        with self.assertRaisesRegex(ValueError, "logit"):
            _gpu_evaluation_outputs([*scores[:2], torch.ones(3)], values, counts, 100)
        with self.assertRaisesRegex(ValueError, "batch shape"):
            _gpu_evaluation_outputs(scores, values[:2], counts, 100)
        for invalid in (float("nan"), float("inf")):
            changed = [*scores[:2], torch.tensor([invalid, 1.])]
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "finite"):
                _gpu_evaluation_outputs(changed, values, counts, 100)
        changed_values = values.clone(); changed_values[-1, 0] = float("nan")
        with self.assertRaises(ValueError):
            _gpu_evaluation_outputs(scores, changed_values, counts, 100)
        self.assertEqual(_gpu_evaluation_outputs([torch.empty(0)] * 3, values, [0, 0, 0], 100)[0], [[], [], []])

    def test_cpu_evaluator_keeps_literal_reference_path_and_no_mps_callback(self):
        models = {player: ConstantDeviceNet("cpu") for player in PLAYERS}
        policy = Mock()
        requests = [(PublicEnv("axis"), [action("a"), action("b")]), (PublicEnv(None, kind="chance"), [])]
        with patch("studies.campaign.neural._gpu_evaluation_outputs", side_effect=AssertionError("CPU must bypass GPU helper")):
            result = NeuralEvaluator(models, "cpu", runtime_policy=policy).evaluate_batch(requests)
        self.assertEqual(len(result[0].priors), 2)
        self.assertEqual(result[1].priors, [])
        policy.completed.assert_not_called()
        self.assertTrue(all(model.training for model in models.values()))

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_mps_host_outputs_routing_and_shared_counter_across_evaluators(self):
        models = {player: ConstantDeviceNet("mps") for player in PLAYERS}
        policy = Mock()
        requests = [(PublicEnv("axis"), [action("a"), action("b")]),
                    (PublicEnv("allies"), [action("c")]), (PublicEnv(None, kind="chance"), []),
                    (PublicEnv(terminal=True), [])]
        cpu = NeuralEvaluator({player: ConstantDeviceNet("cpu") for player in PLAYERS}, "oracle").evaluate_batch(requests)
        for _ in range(2):
            actual = NeuralEvaluator(models, "gpu", runtime_policy=policy).evaluate_batch(requests)
            self.assertEqual(actual, cpu)
        self.assertEqual(policy.completed.call_count, 6)
        self.assertTrue(all(call.args == (1,) for call in policy.completed.call_args_list))
        self.assertTrue(all(model.training for model in models.values()))
        scores, values, counts = self.fixture("mps")
        with self.assertRaisesRegex(ValueError, "device-local"):
            _gpu_evaluation_outputs([scores[0].cpu(), *scores[1:]], values, counts, 100)


if __name__ == "__main__":
    unittest.main()
