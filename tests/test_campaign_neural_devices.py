"""Explicit neural devices with matched initialization, math and host outputs."""
from __future__ import annotations

import copy
import os
import unittest
from unittest.mock import patch

import torch

from studies.campaign import neural
from studies.campaign.neural import (CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator,
                                    clear_neural_caches, make_input, neural_device_memory,
                                    resolve_neural_device, synchronize_neural_device)
from studies.shared.multiplayer_mcts import PLAYERS
from tests.test_campaign_neural import PublicEnv, action


class CampaignNeuralDeviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def setUp(self):
        self.config = CampaignModelConfig(hidden_dim=8, message_layers=1, token_buckets=128)
        self.item = make_input(PublicEnv(), [action("a"), action("b", target="land_b")])
        clear_neural_caches()

    def tearDown(self):
        clear_neural_caches()

    def model(self, device="cpu"):
        torch.manual_seed(81)
        return CampaignPolicyValueNet(self.config, device=device)

    def test_explicit_devices_reject_unavailable_or_unknown_targets(self):
        self.assertEqual(resolve_neural_device(), torch.device("cpu"))
        self.assertEqual(resolve_neural_device("cpu:0"), torch.device("cpu"))
        for device in (None, 0, "auto", "meta", "xpu", "cpu:3", "mps:9"):
            with self.subTest(device=device), self.assertRaises(ValueError):
                resolve_neural_device(device)
        with patch("torch.backends.mps.is_available", return_value=False):
            with self.assertRaisesRegex(ValueError, "unavailable"):
                resolve_neural_device("mps")
        with patch("torch.cuda.is_available", return_value=False):
            with self.assertRaisesRegex(ValueError, "unavailable"):
                resolve_neural_device("cuda")
        with patch("torch.cuda.is_available", return_value=True), \
             patch("torch.cuda.device_count", return_value=2), \
             patch("torch.cuda.current_device", return_value=1):
            self.assertEqual(resolve_neural_device("cuda"), torch.device("cuda:1"))
            self.assertEqual(resolve_neural_device("cuda:0"), torch.device("cuda:0"))
            with self.assertRaisesRegex(ValueError, "index"):
                resolve_neural_device("cuda:2")

    def test_mps_cpu_fallback_is_explicitly_rejected(self):
        with patch("torch.backends.mps.is_available", return_value=True), \
             patch.dict(os.environ, {"PYTORCH_ENABLE_MPS_FALLBACK": "1"}):
            with self.assertRaisesRegex(ValueError, "fallback"):
                resolve_neural_device("mps")
            with self.assertRaisesRegex(ValueError, "fallback"):
                CampaignPolicyValueNet(self.config, device="mps")
        # An MPS-related environment setting does not alter CPU-only execution.
        with patch.dict(os.environ, {"PYTORCH_ENABLE_MPS_FALLBACK": "1"}):
            self.assertEqual(resolve_neural_device("cpu"), torch.device("cpu"))

    def test_default_and_explicit_cpu_initialization_are_identical(self):
        torch.manual_seed(81)
        default = CampaignPolicyValueNet(self.config)
        rng = torch.get_rng_state()
        explicit = self.model("cpu")
        self.assertTrue(torch.equal(rng, torch.get_rng_state()))
        self.assertEqual(default.config, explicit.config)
        for name, value in default.state_dict().items():
            self.assertTrue(torch.equal(value, explicit.state_dict()[name]), name)
        with torch.device("meta"):
            forced_cpu = self.model("cpu")
        self.assertTrue(all(parameter.device.type == "cpu" for parameter in forced_cpu.parameters()))

    def test_explicit_cache_release_preserves_parameters_and_cpu_memory_is_external(self):
        model = self.model().eval()
        saved = copy.deepcopy(model.state_dict())
        with torch.inference_mode():
            model.forward_batch([self.item], model_version="frozen")
        self.assertGreater(neural._GRAPH_TENSOR_BYTES, 0)
        self.assertTrue(model._static_contexts.values)
        clear_neural_caches((model,), device="cpu", release_allocator=True)
        self.assertEqual(neural._GRAPH_TENSOR_BYTES, 0)
        self.assertFalse(neural._GRAPH_TENSORS)
        self.assertFalse(neural._ENCODER_LAYOUTS.values)
        self.assertFalse(model._static_contexts.values)
        for name, value in model.state_dict().items():
            self.assertTrue(torch.equal(value, saved[name]), name)
        with self.assertRaisesRegex(ValueError, "explicit"):
            clear_neural_caches(release_allocator=True)
        self.assertIsNone(neural_device_memory("cpu")["allocated_bytes"])
        synchronize_neural_device("cpu")

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_mps_matches_cpu_initialization_forward_gradients_and_adam(self):
        cpu = self.model()
        rng = torch.get_rng_state()
        mps = self.model("mps")
        self.assertTrue(torch.equal(rng, torch.get_rng_state()))
        for name, value in cpu.state_dict().items():
            self.assertTrue(torch.equal(value, mps.state_dict()[name].cpu()), name)
        cpu_logits, cpu_values = cpu([self.item])
        mps_logits, mps_values = mps([self.item])
        self.assertEqual(mps_logits[0].device.type, "mps")
        self.assertEqual(mps_values.device.type, "mps")
        torch.testing.assert_close(mps_logits[0].cpu(), cpu_logits[0], rtol=2e-4, atol=2e-5)
        torch.testing.assert_close(mps_values.cpu(), cpu_values, rtol=2e-4, atol=2e-5)
        for logits, values in ((cpu_logits, cpu_values), (mps_logits, mps_values)):
            target = torch.tensor([1], device=values.device)
            (torch.nn.functional.cross_entropy(logits[0].unsqueeze(0), target) + values.square().mean()).backward()
        for (name, first), (_, second) in zip(cpu.named_parameters(), mps.named_parameters(), strict=True):
            if first.grad is not None:
                self.assertIsNotNone(second.grad, name)
                torch.testing.assert_close(second.grad.cpu(), first.grad, rtol=2e-4, atol=2e-5, msg=name)
        cpu_optimizer = torch.optim.Adam(cpu.parameters(), lr=.001)
        mps_optimizer = torch.optim.Adam(mps.parameters(), lr=.001)
        cpu_optimizer.step()
        mps_optimizer.step()
        synchronize_neural_device("mps")
        for (name, first), (_, second) in zip(cpu.named_parameters(), mps.named_parameters(), strict=True):
            torch.testing.assert_close(second.cpu(), first, rtol=2e-4, atol=2e-5, msg=name)
        state = mps_optimizer.state[next(mps.parameters())]
        self.assertEqual(state["exp_avg"].device.type, "mps")
        self.assertEqual(state["exp_avg_sq"].device.type, "mps")
        stats = neural_device_memory("mps")
        self.assertGreaterEqual(stats["driver_allocated_bytes"], stats["allocated_bytes"])
        self.assertGreater(stats["recommended_max_bytes"], 0)

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_mps_static_caches_do_not_survive_weight_device_changes(self):
        model = self.model().eval()
        with torch.inference_mode():
            before_logits, before_values = model.forward_batch([self.item], model_version="same-weights")
            model.to("mps")
            mps_logits, _ = model.forward_batch([self.item], model_version="same-weights")
            torch.testing.assert_close(mps_logits[0].cpu(), before_logits[0], rtol=2e-4, atol=2e-5)
            with patch.dict(os.environ, {"PYTORCH_ENABLE_MPS_FALLBACK": "1"}):
                with self.assertRaisesRegex(ValueError, "fallback"):
                    model.forward_batch([self.item], model_version="same-weights")
            model.to("cpu")
            after_logits, after_values = model.forward_batch([self.item], model_version="same-weights")
        self.assertTrue(torch.equal(before_logits[0], after_logits[0]))
        self.assertTrue(torch.equal(before_values, after_values))

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_mps_evaluator_keeps_actor_routing_complete_host_outputs(self):
        cpu_models = {player: self.model().eval() for player in PLAYERS}
        mps_models = {player: self.model("mps").eval() for player in PLAYERS}
        requests = [(PublicEnv("axis"), [action("a"), action("b")]),
                    (PublicEnv(None, kind="chance"), [])]
        expected = NeuralEvaluator(cpu_models, "matched").evaluate_batch(requests)
        actual = NeuralEvaluator(mps_models, "matched").evaluate_batch(requests)
        for first, second in zip(expected, actual, strict=True):
            self.assertEqual(len(first.priors), len(second.priors))
            torch.testing.assert_close(torch.tensor(first.priors), torch.tensor(second.priors), rtol=2e-4, atol=2e-5)
            torch.testing.assert_close(torch.tensor(first.values), torch.tensor(second.values), rtol=2e-4, atol=2e-3)
        self.assertEqual(actual[1].priors, [])
        self.assertTrue(all(isinstance(value, float) for value in actual[0].priors))
        self.assertTrue(all(isinstance(value, float) for value in actual[0].values))


if __name__ == "__main__":
    unittest.main()
