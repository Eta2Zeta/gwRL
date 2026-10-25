"""Evaluation snapshots preserve policies without serializing recovery state."""
from __future__ import annotations

import copy
import random
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch

from studies.campaign.curriculum import make_env, task_manifest
from studies.campaign.model_export import (MODEL_EXPORT_SCHEMA, load_evaluation_models,
                                          save_model_export, validate_model_export)
from studies.campaign.neural import NeuralEvaluator
from studies.campaign.run import RunConfig, _learner, _save, source_hashes
from studies.shared.multiplayer_mcts import PLAYERS, action_key


class CampaignModelExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="campaign-model-export-")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "models" / "generation-000000.pt"
        self.old_threads = torch.get_num_threads()
        self.old_random = random.getstate(), np.random.get_state(), torch.get_rng_state()
        torch.set_num_threads(1)
        self.config = RunConfig(calendar_rounds=3, hidden_dim=8, token_buckets=128, threads=1)
        self.env = make_env(self.config.seed, calendar_rounds=3)
        self.learner = _learner(self.config, self.env)
        self.runner = {"config": asdict(self.config), "task": task_manifest(self.env),
            "training_environment_seeds": [111, 222], "runtime_source_sha256": source_hashes()}

    def tearDown(self):
        random.setstate(self.old_random[0])
        np.random.set_state(self.old_random[1])
        torch.set_rng_state(self.old_random[2])
        torch.set_num_threads(self.old_threads)

    def assert_random_equal(self, expected):
        self.assertEqual(random.getstate(), expected[0])
        actual_numpy = np.random.get_state()
        self.assertEqual(actual_numpy[0], expected[1][0])
        self.assertTrue(np.array_equal(actual_numpy[1], expected[1][1]))
        self.assertEqual(actual_numpy[2:], expected[1][2:])
        self.assertTrue(torch.equal(torch.get_rng_state(), expected[2]))

    def test_small_export_excludes_all_replay_optimizer_and_game_state(self):
        # These deliberately unserializable entries must never be inspected.
        self.learner.replay = [lambda: None]
        self.learner.pending = [lambda: None]
        self.learner.action_history = [lambda: None]
        with patch.object(self.learner, "checkpoint", side_effect=AssertionError("No recovery snapshot")):
            manifest = save_model_export(self.path, self.learner, self.runner)
        value = torch.load(self.path, map_location="cpu", weights_only=True)
        self.assertEqual(value["schema"], MODEL_EXPORT_SCHEMA)
        self.assertEqual(set(value), {"schema", "config", "task", "training_environment_seeds",
            "model_config", "compatibility", "generation", "model_versions", "models", "runtime_source_sha256"})
        self.assertEqual(set(value["models"]), set(PLAYERS))
        self.assertEqual(manifest["model_versions"], self.learner.model_versions())
        self.assertEqual(manifest["bytes"], self.path.stat().st_size)
        self.assertLess(manifest["bytes"], 200_000)

    def test_model_only_loading_never_constructs_a_learner_or_optimizer(self):
        save_model_export(self.path, self.learner, self.runner)
        with patch("studies.campaign.run._learner", side_effect=AssertionError("No learner")), \
             patch("torch.optim.Adam", side_effect=AssertionError("No optimizer")):
            loaded = load_evaluation_models(self.path)
        self.assertEqual(loaded["source_schema"], MODEL_EXPORT_SCHEMA)
        self.assertEqual(loaded["generation"], 0)
        self.assertEqual(loaded["training_environment_seeds"], [111, 222])
        self.assertEqual(loaded["model_versions"], self.learner.model_versions())

    def test_export_and_full_recovery_load_have_identical_outputs_and_action_choices(self):
        save_model_export(self.path, self.learner, self.runner)
        full = self.path.parent / "recovery.pt"
        _save(full, self.learner, self.runner)
        small_loaded, full_loaded = load_evaluation_models(self.path), load_evaluation_models(full)
        self.assertEqual(small_loaded["model_versions"], full_loaded["model_versions"])
        actions = self.env.legal_actions()[:3]
        self.assertTrue(actions)
        first = NeuralEvaluator(small_loaded["models"], version="same").evaluate(self.env, actions)
        second = NeuralEvaluator(full_loaded["models"], version="same").evaluate(self.env, actions)
        self.assertEqual(first, second)
        choose = lambda result: min(zip(actions, result.priors), key=lambda item: (-item[1], action_key(item[0])))[0]
        self.assertEqual(choose(first), choose(second))
        for player in PLAYERS:
            for name, expected in self.learner.models[player].state_dict().items():
                self.assertTrue(torch.equal(expected, small_loaded["models"][player].state_dict()[name]))

    def test_save_and_load_preserve_rng_threads_modes_and_training_tensors(self):
        before = random.getstate(), np.random.get_state(), torch.get_rng_state()
        versions = self.learner.model_versions()
        self.learner.models["axis"].train()
        save_model_export(self.path, self.learner, self.runner)
        self.assert_random_equal(before)
        loaded = load_evaluation_models(self.path)
        self.assert_random_equal(before)
        self.assertEqual(torch.get_num_threads(), 1)
        self.assertTrue(self.learner.models["axis"].training)
        self.assertTrue(all(not model.training for model in loaded["models"].values()))
        self.assertEqual(versions, self.learner.model_versions())
        # Changing the live network afterwards cannot modify its durable export.
        with torch.no_grad():
            next(self.learner.models["axis"].parameters()).add_(1)
        self.assertEqual(load_evaluation_models(self.path)["model_versions"], versions)

    def test_incompatible_metadata_missing_actor_or_modified_weights_are_rejected(self):
        save_model_export(self.path, self.learner, self.runner)
        original = torch.load(self.path, map_location="cpu", weights_only=True)
        def source(value):
            value["runtime_source_sha256"]["fixture"] = "changed"
        def task(value):
            value["task"]["calendar_rounds"] = 11
        def rules(value):
            value["compatibility"]["rules"] = "changed"
        def config(value):
            value["model_config"]["hidden_dim"] = 12
        def actor(value):
            del value["models"]["axis"]
        def weights(value):
            next(iter(value["models"]["axis"].values())).add_(1)
        def nonfinite(value):
            next(iter(value["models"]["axis"].values())).fill_(float("nan"))
        def generation(value):
            value["generation"] = True
        for mutate in (source, task, rules, config, actor, weights, nonfinite, generation):
            with self.subTest(mutation=mutate.__name__):
                value = copy.deepcopy(original)
                mutate(value)
                torch.save(value, self.path)
                with self.assertRaises(ValueError):
                    load_evaluation_models(self.path)

    def test_failed_atomic_save_preserves_previous_export_and_cleans_temporary_file(self):
        save_model_export(self.path, self.learner, self.runner)
        previous = self.path.read_bytes()
        with patch("torch.save", side_effect=OSError("simulated failed write")):
            with self.assertRaisesRegex(OSError, "failed write"):
                save_model_export(self.path, self.learner, self.runner)
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_existing_generation_validation_accepts_seed_prefix_without_constructing_models(self):
        expected = save_model_export(self.path, self.learner, self.runner)
        previous = self.path.read_bytes()
        self.runner["training_environment_seeds"].append(333)
        with patch("studies.campaign.model_export.CampaignPolicyValueNet", side_effect=AssertionError("No model constructor")), \
             patch("torch.optim.Adam", side_effect=AssertionError("No optimizer")):
            self.assertEqual(validate_model_export(self.path, self.learner, self.runner), expected)
        self.assertEqual(self.path.read_bytes(), previous)

    def test_existing_generation_rejects_different_metadata_or_weights_without_rewriting(self):
        save_model_export(self.path, self.learner, self.runner)
        original = torch.load(self.path, map_location="cpu", weights_only=True)
        mutations = {
            "schema": lambda value: value.update(schema="different-schema"),
            "sources": lambda value: value["runtime_source_sha256"].update(fixture="changed"),
            "config": lambda value: value["config"].update(seed=1937),
            "task": lambda value: value["task"].update(calendar_rounds=11),
            "model_config": lambda value: value["model_config"].update(hidden_dim=12),
            "compatibility": lambda value: value["compatibility"].update(rules="changed"),
            "generation": lambda value: value.update(generation=1),
            "versions": lambda value: value["model_versions"].update(axis="changed"),
            "weights": lambda value: next(iter(value["models"]["axis"].values())).add_(1),
            "missing_actor": lambda value: value["models"].pop("axis"),
            "seed_prefix": lambda value: value.update(training_environment_seeds=[333]),
            "seed_future": lambda value: value.update(training_environment_seeds=[111, 222, 333]),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                value = copy.deepcopy(original)
                mutate(value)
                torch.save(value, self.path)
                previous = self.path.read_bytes()
                with self.assertRaises(ValueError):
                    validate_model_export(self.path, self.learner, self.runner)
                self.assertEqual(self.path.read_bytes(), previous)

    def test_existing_generation_validation_uses_actual_learner_tensor_shapes(self):
        # Runner scheduling fixtures use an intentionally tiny policy. Validation
        # must compare that learner directly, rather than instantiate production nets.
        from studies.campaign.learning import CampaignLearner, LearningConfig
        from studies.campaign.neural import CampaignModelConfig
        from test_campaign_learning import TinyNet
        model_config = CampaignModelConfig(**self.learner.model_config)
        learner = CampaignLearner({player: TinyNet(model_config) for player in PLAYERS},
            model_config, LearningConfig(value_scale=self.config.value_scale),
            compatibility=self.learner.compatibility)
        expected = save_model_export(self.path, learner, self.runner)
        previous = self.path.read_bytes()
        with patch("studies.campaign.model_export.CampaignPolicyValueNet", side_effect=AssertionError("No model constructor")):
            self.assertEqual(validate_model_export(self.path, learner, self.runner), expected)
        self.assertEqual(self.path.read_bytes(), previous)

    def test_direct_evaluation_bounds_loader_threads_then_restores_saved_setting(self):
        from studies.campaign.run import evaluate_command
        configured = {**asdict(self.config), "threads": 2}
        loaded = {"config": configured, "task": self.runner["task"],
            "training_environment_seeds": [111], "models": self.learner.models,
            "model_versions": self.learner.model_versions(), "generation": 0,
            "runtime_source_sha256": self.runner["runtime_source_sha256"],
            "source_schema": MODEL_EXPORT_SCHEMA}
        args = SimpleNamespace(checkpoint=self.path, seeds="1009", target="axis",
            baseline_style="balanced", simulations=1, max_depth=1, max_transitions=1,
            target_script=None, output=self.path.parent / "evaluation.json")
        def loader(_path):
            self.assertEqual(torch.get_num_threads(), 1, "Loading must stay within the initialization budget")
            return loaded
        def evaluate(*_args, **_kwargs):
            self.assertEqual(torch.get_num_threads(), 2, "Evaluation must respect its saved tensor budget")
            return {"terminal_games": 0, "truncated_games": 0}
        torch.set_num_threads(3)
        with patch("studies.campaign.run.load_evaluation_models", side_effect=loader), \
             patch("studies.campaign.evaluation.evaluate", side_effect=evaluate):
            self.assertEqual(evaluate_command(args), 0)


if __name__ == "__main__":
    unittest.main()
