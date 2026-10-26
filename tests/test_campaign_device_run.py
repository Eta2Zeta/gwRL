"""Real GPU learning/recovery integration; CPU remains the runner default."""
from __future__ import annotations

import io
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

import torch

from studies.campaign.learning import CampaignLearner, LearningConfig
from studies.campaign.model_export import load_evaluation_models, save_model_export
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
from studies.campaign.run import RunConfig, _config, _learner, source_hashes
from studies.campaign.curriculum import make_env, task_manifest
from studies.shared.multiplayer_mcts import PLAYERS
from tests.test_campaign_learning import LearningToyEnv


class DeviceRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def test_cpu_default_and_explicit_device_is_immutable_on_resume(self):
        self.assertEqual(RunConfig().neural_device, "cpu")
        for invalid in ("auto", "gpu", "mps:1", "cuda:-1", "cuda:bad", 1, None):
            with self.subTest(device=invalid), self.assertRaises(ValueError):
                RunConfig(neural_device=invalid)
        from types import SimpleNamespace
        with self.assertRaisesRegex(ValueError, "Resume configuration differs: neural_device"):
            _config(SimpleNamespace(neural_device="mps"), asdict(RunConfig()))

    @unittest.skipUnless(torch.backends.mps.is_available(), "Apple GPU unavailable")
    def test_actual_cpu_gpu_runner_initialization_has_identical_weights(self):
        config = RunConfig(hidden_dim=8, token_buckets=128, threads=1)
        template = make_env(config.seed, calendar_rounds=1)
        cpu = _learner(config, template)
        rng = torch.get_rng_state().clone()
        gpu = _learner(replace(config, neural_device="mps"), template)
        self.assertTrue(torch.equal(rng, torch.get_rng_state()))
        for player in PLAYERS:
            for name, tensor in cpu.models[player].state_dict().items():
                self.assertEqual(gpu.models[player].state_dict()[name].device.type, "mps")
                self.assertTrue(torch.equal(tensor, gpu.models[player].state_dict()[name].cpu()))

    @unittest.skipUnless(torch.backends.mps.is_available(), "Apple GPU unavailable")
    def test_actual_gpu_adam_and_unfinished_rollout_survive_cpu_storage_roundtrip(self):
        config = CampaignModelConfig(hidden_dim=8, message_layers=1, token_buckets=128)
        learning = LearningConfig(simulations=2, max_depth=3, batch_size=4, epochs=1,
                                  replay_capacity=16, root_noise=False, seed=37)
        def learner():
            torch.manual_seed(31)
            models = {p: CampaignPolicyValueNet(config, device="mps") for p in PLAYERS}
            return CampaignLearner(models, config, learning, compatibility={
                "scenario": "toy", "rules": "toy-rules", "schema": "toy-schema"})
        original = learner()
        original.run_batch_many(LearningToyEnv, 5, parallel_envs=2)
        original.begin_batch_many([LearningToyEnv(51), LearningToyEnv(52)])
        original.collect_many(1)
        self.assertTrue(any(original.parallel_pending))
        checkpoint = original.checkpoint()
        storage = io.BytesIO()
        torch.save(checkpoint, storage, pickle_protocol=5)
        storage.seek(0)
        loaded = torch.load(storage, map_location="cpu", weights_only=False)
        recovered = learner()
        recovered.restore(loaded, env_template=LearningToyEnv())
        self.assertEqual(original.model_versions(), recovered.model_versions())
        self.assertEqual([e.serialize() for e in original.parallel_envs],
                         [e.serialize() for e in recovered.parallel_envs])
        self.assertEqual(original.policy_random.getstate(), recovered.policy_random.getstate())
        self.assertEqual(original.search_random.getstate(), recovered.search_random.getstate())
        self.assertEqual(original.replay_random.getstate(), recovered.replay_random.getstate())
        self.assertEqual(original.counters, recovered.counters)
        for player in PLAYERS:
            for parameter, state in recovered.optimizers[player].state.items():
                self.assertEqual(parameter.device.type, "mps")
                self.assertTrue(state)
                for name in ("exp_avg", "exp_avg_sq"):
                    self.assertEqual(state[name].device.type, "mps")
            for name, tensor in original.frozen_models[player].state_dict().items():
                self.assertTrue(torch.equal(tensor.cpu(), recovered.frozen_models[player].state_dict()[name].cpu()))
        original.collect_many(4)
        recovered.collect_many(4)
        self.assertTrue(all(e.is_terminal() for e in recovered.parallel_envs))
        self.assertEqual(original.action_history, recovered.action_history)
        original.finish_batch()
        recovered.finish_batch()
        original.update()
        recovered.update()
        for player in PLAYERS:
            for name, tensor in original.models[player].state_dict().items():
                torch.testing.assert_close(tensor.cpu(), recovered.models[player].state_dict()[name].cpu(),
                                           atol=2e-6, rtol=2e-5)

    @unittest.skipUnless(torch.backends.mps.is_available(), "Apple GPU unavailable")
    def test_gpu_export_can_evaluate_on_cpu_without_migrating_training(self):
        config = RunConfig(hidden_dim=8, token_buckets=128, neural_device="mps", threads=1)
        env = make_env(config.seed, calendar_rounds=1)
        learner = _learner(config, env)
        runner = {"config": asdict(config), "task": task_manifest(env),
                  "training_environment_seeds": [], "runtime_source_sha256": source_hashes()}
        before = torch.mps.get_rng_state().clone()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "models.pt"
            save_model_export(path, learner, runner)
            loaded = load_evaluation_models(path, device="cpu")
            self.assertEqual(loaded["neural_device"], "cpu")
            self.assertEqual(loaded["config"]["neural_device"], "mps")
            self.assertEqual(loaded["model_versions"], learner.model_versions())
            self.assertTrue(all(next(model.parameters()).device.type == "cpu" for model in loaded["models"].values()))
        self.assertTrue(torch.equal(before, torch.mps.get_rng_state()))
        self.assertTrue(all(next(model.parameters()).device.type == "mps" for model in learner.models.values()))


if __name__ == "__main__":
    unittest.main()
