"""Numerical replay retains training meaning and exact checkpoint continuation."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import torch

import gwrl_cpp
from studies.campaign.curriculum import compatibility, make_env
from studies.campaign.features import NUMERIC_SCHEMA, make_input, make_numeric_input
from studies.campaign.learning import CampaignLearner, LearningConfig
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
from studies.shared.campaign_adapter import ScheduledAction
from studies.shared.multiplayer_mcts import PLAYERS


def _result(env):
    actions = list(env.legal_actions())
    chosen = next((i for i, action in enumerate(actions) if action.kind == "pass_interrupt"), 0)
    policy = [float(i == chosen) for i in range(len(actions))]
    return SimpleNamespace(actions=actions, policy=policy, visit_counts=policy,
                           priors=policy, values=(0.0, 0.0, 0.0), action_values=[None] * len(actions))


@unittest.skipUnless(hasattr(gwrl_cpp, "CampaignNumericGraph"), "Native numerical binding required")
class CampaignNumericLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def setUp(self):
        torch.manual_seed(711)
        self.env = make_env(101, calendar_rounds=3)
        self.model_config = CampaignModelConfig(hidden_dim=4, message_layers=1, token_buckets=32)
        self.config = LearningConfig(simulations=1, max_depth=1, batch_size=2,
                                     replay_capacity=8, epochs=1, root_noise=False, seed=37)

    def learner(self):
        return CampaignLearner({player: CampaignPolicyValueNet(self.model_config) for player in PLAYERS},
                               self.model_config, self.config, compatibility=compatibility(self.env))

    def assert_tree_equal(self, left, right):
        if isinstance(left, gwrl_cpp.CampaignNumericGraph):
            self.assert_tree_equal(left.packed_state(), right.packed_state())
        elif isinstance(left, torch.Tensor):
            self.assertTrue(torch.equal(left, right))
        elif isinstance(left, np.ndarray):
            np.testing.assert_array_equal(left, right)
        elif isinstance(left, dict):
            self.assertEqual(set(left), set(right))
            for key in left:
                self.assert_tree_equal(left[key], right[key])
        elif isinstance(left, (tuple, list)):
            self.assertEqual(type(left), type(right))
            self.assertEqual(len(left), len(right))
            for first, second in zip(left, right, strict=True):
                self.assert_tree_equal(first, second)
        else:
            self.assertEqual(left, right)

    def test_collection_uses_numeric_buffers_and_materializes_only_selected_action(self):
        learner = self.learner()
        learner.begin_batch(self.env)
        result = _result(self.env)
        # Populate the one-time immutable context before prohibiting public
        # board conversion; subsequent decisions use native snapshots.
        make_numeric_input(self.env, result.actions, self.model_config.token_buckets)
        original = ScheduledAction.features
        with mock.patch.object(self.env, "observation", side_effect=AssertionError("No public board conversion")), \
             mock.patch.object(self.env, "neural_observation", side_effect=AssertionError("No source board conversion")), \
             mock.patch.object(ScheduledAction, "features", autospec=True, side_effect=original) as features:
            event = learner._apply_search_result(self.env, result, learner.pending)
        self.assertEqual(features.call_count, 1)
        saved = learner.pending[0]["input"]
        self.assertEqual(saved["schema"], NUMERIC_SCHEMA)
        self.assertNotIn("observation", saved)
        self.assertNotIn("actions", saved)
        self.assertIsInstance(saved["packed_graph"]["observation"], gwrl_cpp.CampaignNumericGraph)
        self.assertEqual(len(saved["packed_graph"]["actions"]), len(result.actions))
        selected = features.call_args.args[0]
        raw = selected.features().get("action") or selected.features()
        self.assertEqual(event["action_kind"], raw["kind"])
        self.assertEqual(event["action_parameters"], raw.get("parameters", {}))

    def test_trace_materializes_full_menu_without_changing_numeric_replay(self):
        learner = self.learner()
        learner.begin_batch(self.env)
        result, trace = _result(self.env), {}
        original = ScheduledAction.features
        with mock.patch.object(ScheduledAction, "features", autospec=True, side_effect=original) as features:
            learner._apply_search_result(self.env, result, learner.pending, trace)
        self.assertEqual(features.call_count, len(result.actions))
        self.assertEqual(trace["selected_action"], trace["decision_menu"][trace["selected_index"]])
        self.assertEqual(learner.pending[0]["input"]["schema"], NUMERIC_SCHEMA)

    def test_saved_midbatch_parallel_rollout_and_update_resume_exactly(self):
        learner = self.learner()
        learner.begin_batch_many([self.env, make_env(102, calendar_rounds=3)])
        learner.collect_many(1)
        contexts = [rows[0]["input"]["packed_graph"]["context"] for rows in learner.parallel_pending]
        self.assertIs(contexts[0], contexts[1])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "numeric-midbatch.pt"
            learner.save_checkpoint(path)
            expected_collection = learner.collect_many(1)
            expected_rollout = learner.finish_batch()
            expected_update = learner.update()
            expected = learner.checkpoint()
            resumed = self.learner()
            resumed.load_checkpoint(path, env_template=make_env(103, calendar_rounds=3))
            restored = [rows[0]["input"]["packed_graph"]["context"] for rows in resumed.parallel_pending]
            self.assertIs(restored[0], restored[1])
            actual_collection = resumed.collect_many(1)
            self.assertEqual(expected_collection["events"], actual_collection["events"])
            self.assertEqual(expected_rollout, resumed.finish_batch())
            self.assertEqual(expected_update, resumed.update())
            self.assert_tree_equal(expected, resumed.checkpoint())

    def test_legacy_json_and_numeric_replay_have_identical_outputs_gradients_and_updates(self):
        learner = self.learner()
        learner.begin_batch(self.env)
        result = _result(self.env)
        legacy_input = make_input(self.env, result.actions)
        numeric_input = make_numeric_input(self.env, result.actions, self.model_config.token_buckets)
        first = copy.deepcopy(learner.models[PLAYERS[0]])
        second = copy.deepcopy(first)
        logits_a, values_a = first.forward_batch([legacy_input])
        logits_b, values_b = second.forward_batch([numeric_input])
        self.assertTrue(torch.equal(logits_a[0], logits_b[0]))
        self.assertTrue(torch.equal(values_a, values_b))
        (logits_a[0].sum() + values_a.sum()).backward()
        (logits_b[0].sum() + values_b.sum()).backward()
        for a, b in zip(first.parameters(), second.parameters(), strict=True):
            self.assertEqual(a.grad is None, b.grad is None)
            if a.grad is not None:
                self.assertTrue(torch.equal(a.grad, b.grad))
        learner._apply_search_result(self.env, result, learner.pending)
        legacy_checkpoint = learner.checkpoint()
        legacy_checkpoint["pending"][0]["input"] = legacy_input
        restored = self.learner()
        restored.restore(legacy_checkpoint, env_template=make_env(102, calendar_rounds=3))
        self.assertEqual(learner.finish_batch(), restored.finish_batch())
        self.assertEqual(learner.update(), restored.update())
        for player in PLAYERS:
            self.assert_tree_equal(learner.models[player].state_dict(), restored.models[player].state_dict())
            self.assert_tree_equal(learner.optimizers[player].state_dict(), restored.optimizers[player].state_dict())

    def test_numeric_checkpoint_rejects_wrong_owner_vocabulary_context_and_policy_atomically(self):
        learner = self.learner()
        learner.begin_batch(self.env)
        learner._apply_search_result(self.env, _result(self.env), learner.pending)
        snapshot = learner.checkpoint()
        def wrong_owner(value):
            value["pending"][0]["input"]["owner"] = "axis"
        def wrong_vocabulary(value):
            item = value["pending"][0]["input"]
            item["packed_graph"]["context"] = make_numeric_input(self.env, self.env.legal_actions(), 64)["packed_graph"]["context"]
        def wrong_context_key(value):
            value["pending"][0]["input"]["context_key"] = "f" * 64
        def wrong_context_graph(value):
            packed = value["pending"][0]["input"]["packed_graph"]
            packed["context"] = packed["observation"]
        def changed_zero_sign(value):
            packed = value["pending"][0]["input"]["packed_graph"]
            source = packed["context"].packed_state()
            numeric = source["numeric"].copy()
            zero = tuple(np.argwhere(numeric == 0.0)[0])
            numeric[zero] = -0.0 if not np.signbit(numeric[zero]) else 0.0
            source["numeric"] = numeric
            packed["context"] = gwrl_cpp.CampaignNumericGraph.from_packed(source)
        def wrong_policy(value):
            value["pending"][0]["policy"] = [1.0] * len(value["pending"][0]["policy"])
        for change in (wrong_owner, wrong_vocabulary, wrong_context_key, wrong_context_graph, changed_zero_sign, wrong_policy):
            incoming = copy.deepcopy(snapshot)
            change(incoming)
            with self.assertRaises(ValueError):
                learner.restore(incoming, env_template=make_env(105, calendar_rounds=3))
            self.assert_tree_equal(snapshot, learner.checkpoint())


if __name__ == "__main__":
    unittest.main()
