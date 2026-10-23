from __future__ import annotations

import copy
import io
import json
import random
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest import mock

import numpy as np
import torch
from torch import nn

from studies.campaign.learning import CampaignLearner, LearningConfig
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, make_input
from studies.shared.campaign_adapter import CampaignAdapter
from studies.shared.multiplayer_mcts import PLAYERS


def _tuples(value):
    return tuple(_tuples(item) for item in value) if isinstance(value, list) else value


class LearningToyEnv:
    """Consecutive Axis choices, explicit chance, defender reaction, third actor."""
    owners = ("axis", "axis", None, "allies", "comintern", None)

    def __init__(self, seed=31, context_version="toy-v1"):
        self.node, self.score, self.actual_draws = 0, 0, 0
        self.random = random.Random(seed)
        self.context_version = context_version

    def current_decision_player(self):
        return self.owners[self.node]

    def decision_kind(self):
        return "terminal" if self.node == 5 else "chance" if self.node == 2 else "defender_reaction" if self.node == 3 else "choose"

    def legal_actions(self):
        owner = self.current_decision_player()
        return [] if owner is None else [
            {"id": f"choose-{amount}", "kind": "choose", "player": owner, "parameters": {"amount": amount}}
            for amount in (1, 2)]

    def apply_action(self, action):
        if action not in self.legal_actions():
            raise ValueError("Illegal toy action")
        self.score += action["parameters"]["amount"]
        self.node += 1

    def resolve_chance(self):
        if self.node != 2:
            raise ValueError("No chance event")
        self.score += self.random.randrange(4)
        self.actual_draws += 1
        self.node += 1

    def is_terminal(self):
        return self.node == 5

    def returns(self):
        return [350 + self.score, -70 - self.score / 4, -280 - self.score * 3 / 4] if self.is_terminal() else [0, 0, 0]

    def observation(self):
        return {"schema": "campaign_entities_v1", "current_decision_player": self.current_decision_player(),
                "decision_kind": self.decision_kind(), "state": {"node": self.node, "score": self.score}}

    def context(self):
        return {"schema": self.context_version, "players": list(PLAYERS), "geography": {"zones": [{"id": "one"}]}}

    def planning_key(self):
        return json.dumps([self.context_version, self.node, self.score])

    def clone(self):
        return copy.deepcopy(self)

    def clone_for_search(self, seed):
        result = self.clone()
        result.random = random.Random(seed)
        return result

    def serialize(self):
        return json.dumps({"node": self.node, "score": self.score, "draws": self.actual_draws,
                           "random": self.random.getstate(), "context": self.context_version}, sort_keys=True)

    def restore(self, serialized):
        value = json.loads(serialized)
        if value["context"] != self.context_version:
            raise ValueError("Toy context differs")
        generator = random.Random()
        generator.setstate(_tuples(value["random"]))
        self.node, self.score, self.actual_draws = value["node"], value["score"], value["draws"]
        self.random = generator


class TinyNet(nn.Module):
    """An exact controllable policy/vector head for target and optimizer checks."""
    def __init__(self, config, values=(0.2, 0.3, -0.5)):
        super().__init__()
        self.config = config
        self.logits = nn.Parameter(torch.tensor([0.15, -0.1]))
        self.values = nn.Parameter(torch.tensor(values))

    def forward_batch(self, inputs):
        return [self.logits[:len(item["actions"])] for item in inputs], self.values.unsqueeze(0).expand(len(inputs), -1)


class SchedulingToyRaw(LearningToyEnv):
    def __init__(self):
        super().__init__()
        self.declared = False

    def decision_kind(self):
        return "production" if self.node == 0 else super().decision_kind()

    def legal_interrupts(self):
        return [{"id": "allies-declaration", "kind": "declare_war", "player": "allies", "parameters": {}}] \
            if self.node == 0 and not self.declared else []

    def apply_interrupt(self, action):
        if action not in self.legal_interrupts():
            raise ValueError("Illegal declaration")
        self.declared = True

    def planning_key(self):
        return json.dumps([super().planning_key(), self.declared])

    def serialize(self):
        return json.dumps({"raw": super().serialize(), "declared": self.declared}, sort_keys=True)

    def restore(self, serialized):
        value = json.loads(serialized)
        super().restore(value["raw"])
        self.declared = value["declared"]


class MutableContextToyEnv(LearningToyEnv):
    def __init__(self):
        super().__init__()
        self.caller_context = super().context()
        self.caller_context["opaque_registry"] = {"entries": [{"name": "retained", "extra": [1, 2, 3]}]}

    def context(self):
        return self.caller_context


class CampaignLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def setUp(self):
        random.seed(23)
        np.random.seed(29)
        torch.manual_seed(31)
        self.model_config = CampaignModelConfig(hidden_dim=8, message_layers=1, token_buckets=128)
        self.config = LearningConfig(simulations=8, max_depth=6, batch_size=32, epochs=2,
                                     replay_capacity=64, root_noise=False, seed=37)
        self.compatibility = {"scenario": "toy-scenario-v1", "rules": "toy-rules-v1", "schema": "toy-schema-v1"}

    def learner(self, *, real=False, config=None, compatibility=None):
        models = {player: CampaignPolicyValueNet(self.model_config) if real else TinyNet(self.model_config)
                  for player in PLAYERS}
        return CampaignLearner(models, self.model_config, config or self.config,
                               compatibility=compatibility or self.compatibility)

    def assert_tree_equal(self, left, right):
        if isinstance(left, torch.Tensor):
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
            for first, second in zip(left, right):
                self.assert_tree_equal(first, second)
        else:
            self.assertEqual(left, right)

    def test_terminal_targets_are_raw_three_component_gaps_without_clipping(self):
        learner = self.learner()
        learner.begin_batch(LearningToyEnv())
        before = {p: copy.deepcopy(model.state_dict()) for p, model in learner.models.items()}
        learner.collect(5)
        for player in PLAYERS:
            self.assert_tree_equal(before[player], learner.models[player].state_dict())
        rollout = learner.finish_batch()
        self.assertTrue(rollout["terminal"])
        self.assertEqual(rollout["terminal_samples"], 4)
        self.assertEqual(rollout["bootstrap_samples"], 0)
        self.assertEqual([row["owner"] for row in learner.replay], ["axis", "axis", "allies", "comintern"])
        for row in learner.replay:
            self.assertEqual(row["values"], learner.env.returns())
            self.assertGreater(row["values"][0], learner.config.value_scale)
            self.assertLess(row["values"][2], -learner.config.value_scale)
        result = learner.update()
        self.assertTrue(result["updated"])
        self.assertEqual(result["losses"]["axis"][0]["policy_samples"], 2)
        self.assertEqual(result["losses"]["allies"][0]["policy_samples"], 1)
        self.assertEqual(result["losses"]["comintern"][0]["policy_samples"], 1)
        for player in PLAYERS:
            self.assertFalse(torch.equal(before[player]["values"], learner.models[player].values))

    def test_policy_loss_routes_only_to_actual_owner_and_scale_is_applied_once(self):
        learner = self.learner(config=replace(self.config, epochs=1))
        env = LearningToyEnv()
        learner.replay = [{"input": make_input(env, env.legal_actions()), "owner": "axis", "policy": [1.0, 0.0],
                           "values": [20.0, 30.0, -50.0], "rollout_version": "exact-fixture",
                           "target_source": "terminal", "target_schema": "campaign-raw-vector-target-v1"}]
        before = {p: copy.deepcopy(model.state_dict()) for p, model in learner.models.items()}
        result = learner.update()
        self.assertAlmostEqual(result["losses"]["axis"][0]["value"], 0.0, places=12)
        self.assertFalse(torch.equal(before["axis"]["logits"], learner.models["axis"].logits))
        for player in ("allies", "comintern"):
            self.assertEqual(result["losses"][player][0]["policy_samples"], 0)
            self.assert_tree_equal(before[player], learner.models[player].state_dict())

    def test_unused_policy_menus_are_skipped_without_changing_learning(self):
        learner = self.learner(real=True, config=replace(self.config, epochs=1))
        for index, node in enumerate((0, 1, 3, 4)):
            env = LearningToyEnv()
            env.node, env.score = node, index * 3
            learner.replay.append({
                "input": make_input(env, env.legal_actions()),
                "owner": env.current_decision_player(), "policy": [.8, .2],
                "values": [350. + index, -70. - index / 4, -280. - index * 3 / 4],
                "rollout_version": "unfiltered-reference", "target_source": "terminal",
                "target_schema": "campaign-raw-vector-target-v1",
            })
        original_replay = copy.deepcopy(learner.replay)
        baseline = copy.deepcopy(learner)
        samples = baseline.replay_random.sample(baseline.replay, len(baseline.replay))
        inputs = [sample["input"] for sample in samples]
        expected = {}
        # Reference the original computation: all actors encode every action
        # menu, although only the actual owner's policy contributes to loss.
        for player in PLAYERS:
            model, optimizer = baseline.models[player], baseline.optimizers[player]
            model.train()
            optimizer.zero_grad(set_to_none=True)
            logits, predicted = model.forward_batch(inputs)
            targets = predicted.new_tensor([sample["values"] for sample in samples]) / baseline.config.value_scale
            value_loss = (predicted - targets).square().mean()
            terms = [-(logits[index].new_tensor(sample["policy"]) * logits[index].log_softmax(0)).sum()
                     for index, sample in enumerate(samples) if sample["owner"] == player]
            policy_loss = torch.stack(terms).mean()
            loss = value_loss + policy_loss
            loss.backward()
            expected[player] = {"value": float(value_loss.detach()), "policy": float(policy_loss.detach()),
                                "total": float(loss.detach()), "policy_samples": len(terms)}
        for player in PLAYERS:
            baseline.optimizers[player].step()
            baseline.models[player].eval()

        with ExitStack() as stack:
            calls = {player: stack.enter_context(mock.patch.object(
                model, "forward_batch", wraps=model.forward_batch)) for player, model in learner.models.items()}
            result = learner.update()
        self.assertEqual(learner.replay, original_replay)
        for player in PLAYERS:
            forwarded = calls[player].call_args.args[0]
            for item, sample in zip(forwarded, samples, strict=True):
                self.assertEqual(item["observation"], sample["input"]["observation"])
                self.assertEqual(item["context"], sample["input"]["context"])
                self.assertEqual(item["actions"], sample["input"]["actions"] if sample["owner"] == player else [])
            actual = result["losses"][player][0]
            self.assertEqual(actual["policy_samples"], expected[player]["policy_samples"])
            for name in ("policy", "value", "total"):
                self.assertAlmostEqual(actual[name], expected[player][name], places=6)
            torch.testing.assert_close(learner.models[player].state_dict(), baseline.models[player].state_dict(),
                                       atol=2e-6, rtol=2e-5)
            torch.testing.assert_close(learner.optimizers[player].state_dict(), baseline.optimizers[player].state_dict(),
                                       atol=2e-6, rtol=2e-5)
            for parameter, reference in zip(learner.models[player].parameters(), baseline.models[player].parameters(), strict=True):
                self.assertEqual(parameter.grad is None, reference.grad is None)
                if parameter.grad is not None:
                    torch.testing.assert_close(parameter.grad, reference.grad, atol=2e-6, rtol=2e-5)

    def test_bounded_nonterminal_segment_bootstraps_instead_of_fake_terminal(self):
        learner = self.learner()
        learner.begin_batch(LearningToyEnv())
        learner.collect(1)
        with self.assertRaisesRegex(ValueError, "frozen"):
            learner.update()
        rollout = learner.finish_batch()
        self.assertFalse(rollout["terminal"])
        self.assertEqual(rollout["bootstrap_samples"], 1)
        self.assertEqual(learner.env.returns(), [0, 0, 0])
        np.testing.assert_allclose(learner.replay[0]["values"], [20, 30, -50], rtol=1e-6)
        self.assertEqual(learner.replay[0]["target_source"], "bootstrap")

    def test_chance_cutoff_averages_value_heads_without_policy_or_execution_roll(self):
        learner = self.learner()
        with torch.no_grad():
            learner.models["allies"].values.copy_(torch.tensor([0.8, 0.1, -0.9]))
            learner.models["comintern"].values.copy_(torch.tensor([-0.1, 0.7, -0.6]))
        learner.begin_batch(LearningToyEnv())
        learner.collect(2)
        self.assertEqual(learner.env.decision_kind(), "chance")
        self.assertEqual(learner.env.actual_draws, 0)
        state = learner.env.serialize()
        result = learner.finish_batch()
        self.assertEqual(result["bootstrap_samples"], 2)
        self.assertEqual(learner.env.serialize(), state)
        expected = np.array([[0.2, 0.3, -0.5], [0.8, 0.1, -0.9], [-0.1, 0.7, -0.6]]).mean(0) * 100
        for row in learner.replay:
            np.testing.assert_allclose(row["values"], expected, rtol=1e-6)
            self.assertIn(row["owner"], PLAYERS)
        learner.begin_batch()
        learner.collect(1)
        self.assertEqual(learner.env.actual_draws, 1)
        self.assertEqual(learner.counters["chance_events"], 1)

    def test_mid_rollout_resume_matches_uninterrupted_actions_optimizer_weights_and_rng(self):
        learner = self.learner()
        learner.run_batch(LearningToyEnv, 5)  # Populate Adam moments and replay first.
        learner.begin_batch()
        learner.collect(3, LearningToyEnv)  # Pending consecutive choices and a resolved die.
        snapshot = learner.checkpoint()
        self.assertEqual(len(snapshot["pending"]), 2)
        self.assertIsNotNone(snapshot["frozen_models"])
        learner.collect(9, LearningToyEnv)
        learner.finish_batch()
        learner.update()
        expected = learner.checkpoint()
        expected_draws = (random.random(), float(np.random.random()), torch.rand(5))
        resumed = self.learner()
        random.random()
        np.random.random()
        torch.rand(3)
        resumed.restore(snapshot, env_template=LearningToyEnv())
        resumed.collect(9, LearningToyEnv)
        resumed.finish_batch()
        resumed.update()
        self.assert_tree_equal(expected, resumed.checkpoint())
        actual_draws = (random.random(), float(np.random.random()), torch.rand(5))
        self.assert_tree_equal(expected_draws, actual_draws)

    def test_saved_checkpoint_roundtrip_keeps_active_batch(self):
        learner = self.learner()
        learner.begin_batch(LearningToyEnv())
        learner.collect(1)
        snapshot = learner.checkpoint()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "learner.pt"
            learner.save_checkpoint(path)
            resumed = self.learner()
            resumed.load_checkpoint(path, env_template=LearningToyEnv())
            self.assert_tree_equal(snapshot, resumed.checkpoint())

    def test_checkpoint_preserves_real_campaign_adapter_passed_interrupt_offer(self):
        adapter = CampaignAdapter(SchedulingToyRaw())
        self.assertEqual(adapter.current_decision_player(), "allies")
        adapter.apply_action(next(action for action in adapter.legal_actions() if action.kind == "pass_interrupt"))
        self.assertEqual(adapter.current_decision_player(), "axis")
        learner = self.learner()
        learner.begin_batch(adapter)
        payload = learner.checkpoint()
        resumed = self.learner()
        resumed.restore(payload, env_template=CampaignAdapter(SchedulingToyRaw()))
        self.assertEqual(resumed.env.current_decision_player(), "axis")
        self.assertEqual(resumed.env.decision_kind(), "production")
        self.assertEqual(json.loads(resumed.env.serialize())["passed"], ["allies"])
        self.assertEqual(resumed.env.planning_key(), adapter.planning_key())
        resumed.collect(1)
        self.assertEqual(resumed.pending[0]["owner"], "axis")

    def test_parallel_collection_uses_real_batches_and_labels_each_root_separately(self):
        learner = self.learner()
        learner.begin_batch_many([LearningToyEnv(seed=31), LearningToyEnv(seed=47)])
        collection = learner.collect_many(5)
        self.assertEqual(collection["transitions_per_env"], [5, 5])
        self.assertIn(2, collection["inference_batch_sizes"])
        self.assertEqual([env.actual_draws for env in learner.parallel_envs], [1, 1])
        self.assertEqual(len(collection["events"]), 10)
        terminal_values = [env.returns() for env in learner.parallel_envs]
        self.assertNotEqual(terminal_values[0], terminal_values[1])
        summary = learner.finish_batch()
        self.assertEqual(summary["terminal_samples"], 8)
        self.assertEqual(summary["bootstrap_samples"], 0)
        for values in terminal_values:
            self.assertEqual(sum(sample["values"] == values for sample in learner.replay), 4)
        self.assertEqual(learner.counters["episodes"], 2)
        self.assertTrue(learner.update()["updated"])

    def test_parallel_factory_seeds_are_independent_and_owned_by_checkpoint_rng(self):
        seeds = []

        def factory(seed):
            seeds.append(seed)
            return LearningToyEnv(seed=seed)

        learner = self.learner()
        learner.run_batch_many(factory, 0, parallel_envs=2)
        self.assertEqual(len(seeds), 2)
        self.assertNotEqual(seeds[0], seeds[1])
        self.assertNotEqual(learner.parallel_envs[0].serialize(), learner.parallel_envs[1].serialize())
        checkpoint = learner.checkpoint()
        expected = learner.environment_random.getrandbits(63)
        resumed = self.learner()
        resumed.restore(checkpoint, env_template=LearningToyEnv())
        self.assertEqual(resumed.environment_random.getrandbits(63), expected)

    def test_parallel_pending_rollouts_and_all_rng_resume_exactly(self):
        config = replace(self.config, root_noise=True)
        learner = self.learner(config=config)
        learner.run_batch_many(LearningToyEnv, 5, parallel_envs=2)
        learner.begin_batch_many()
        learner.collect_many(3, LearningToyEnv)
        checkpoint = learner.checkpoint()
        self.assertEqual([len(samples) for samples in checkpoint["parallel_pending"]], [2, 2])
        self.assertEqual(len(checkpoint["parallel_envs"]), 2)
        learner.collect_many(4, LearningToyEnv)
        learner.finish_batch()
        learner.update()
        expected = learner.checkpoint()
        resumed = self.learner(config=config)
        resumed.restore(checkpoint, env_template=LearningToyEnv())
        resumed.collect_many(4, LearningToyEnv)
        resumed.finish_batch()
        resumed.update()
        self.assert_tree_equal(expected, resumed.checkpoint())

    def test_parallel_partial_cutoff_bootstraps_each_active_root(self):
        learner = self.learner()
        learner.begin_batch_many([LearningToyEnv(seed=31), LearningToyEnv(seed=47)])
        learner.collect_many(2)
        states = [env.serialize() for env in learner.parallel_envs]
        summary = learner.finish_batch()
        self.assertFalse(summary["terminal"])
        self.assertEqual(summary["bootstrap_samples"], 4)
        self.assertEqual([env.serialize() for env in learner.parallel_envs], states)
        self.assertTrue(all(sample["target_source"] == "bootstrap" for sample in learner.replay))

    def test_parallel_corruption_is_rejected_without_partial_model_or_rng_load(self):
        learner = self.learner()
        learner.begin_batch_many([LearningToyEnv(), LearningToyEnv(seed=47)])
        learner.collect_many(1)
        checkpoint = learner.checkpoint()
        for field in ("context", "state", "pending"):
            broken = copy.deepcopy(checkpoint)
            if field == "context":
                broken["parallel_envs"][1]["context"] = "other-rules"
            elif field == "state":
                broken["parallel_envs"][1]["state"] = "not-json"
            else:
                broken["parallel_pending"][1][0]["owner"] = "allies"
            with self.assertRaises((ValueError, TypeError)):
                learner.restore(broken, env_template=LearningToyEnv())
            self.assert_tree_equal(checkpoint, learner.checkpoint())

    def test_context_snapshots_are_complete_interned_read_only_and_detached(self):
        env = MutableContextToyEnv()
        original = json.loads(json.dumps(env.context()))
        learner = self.learner()
        learner.begin_batch(env)
        learner.collect(2)
        first, second = [sample["input"]["context"] for sample in learner.pending]
        self.assertIs(first, second)
        self.assertIsNot(first, env.context())
        self.assertEqual(first, original)
        self.assertEqual(json.loads(json.dumps(first)), original)
        with self.assertRaisesRegex(TypeError, "read-only"):
            first["schema"] = "changed"
        with self.assertRaisesRegex(TypeError, "read-only"):
            first["opaque_registry"]["entries"].append({"name": "injected"})
        with self.assertRaisesRegex(TypeError, "read-only"):
            first["opaque_registry"]["entries"][0]["name"] = "changed"
        env.context()["opaque_registry"]["entries"][0]["name"] = "caller changed"
        env.context()["geography"]["zones"].append({"id": "later"})
        self.assertEqual(first, original)

    def test_checkpoint_and_restore_deduplicate_context_across_replay_and_pending(self):
        learner = self.learner()
        learner.run_batch(LearningToyEnv, 5)
        learner.begin_batch()
        learner.collect(2, LearningToyEnv)
        original = learner.replay[0]["input"]["context"]
        self.assertIs(original, learner.pending[0]["input"]["context"])
        payload = learner.checkpoint()
        saved_context = payload["replay"][0]["input"]["context"]
        self.assertEqual(saved_context, original)
        # An immutable source context may safely survive deepcopy by identity.
        with self.assertRaisesRegex(TypeError, "read-only"):
            saved_context["schema"] = "checkpoint mutation"
        self.assertTrue(all(sample["input"]["context"] is saved_context
                            for sample in payload["replay"] + payload["pending"]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shared-context.pt"
            torch.save(payload, path)
            loaded = torch.load(path, weights_only=False)
        loaded_context = loaded["replay"][0]["input"]["context"]
        self.assertTrue(all(sample["input"]["context"] is loaded_context
                            for sample in loaded["replay"] + loaded["pending"]))
        resumed = self.learner()
        resumed.restore(loaded, env_template=LearningToyEnv())
        restored_context = resumed.replay[0]["input"]["context"]
        self.assertEqual(restored_context, loaded_context)
        with self.assertRaisesRegex(TypeError, "read-only"):
            restored_context["geography"]["zones"].append({"id": "restored mutation"})
        self.assertTrue(all(sample["input"]["context"] is restored_context
                            for sample in resumed.replay + resumed.pending))
        self.assert_tree_equal(payload, resumed.checkpoint())

    def test_large_context_is_serialized_once_instead_of_once_per_sample(self):
        env = MutableContextToyEnv()
        blob = "complete-static-source:" + "x" * 128_000
        env.context()["full_registry_payload"] = blob
        learner = self.learner()
        learner.begin_batch(env)
        learner.collect(2)
        shared = learner.checkpoint()
        legacy = copy.deepcopy(shared)
        contexts = []
        for sample in legacy["pending"]:
            sample["input"]["context"] = json.loads(json.dumps(sample["input"]["context"]))
            contexts.append(sample["input"]["context"])
        self.assertIsNot(contexts[0]["full_registry_payload"], contexts[1]["full_registry_payload"])
        compact_file, repeated_file = io.BytesIO(), io.BytesIO()
        torch.save(shared, compact_file)
        torch.save(legacy, repeated_file)
        self.assertGreater(repeated_file.tell() - compact_file.tell(), len(blob) * 0.9)
        restored = self.learner()
        template = MutableContextToyEnv()
        template.context()["full_registry_payload"] = blob
        restored.restore(legacy, env_template=template)
        self.assertIs(restored.pending[0]["input"]["context"], restored.pending[1]["input"]["context"])

    def test_restore_interns_legacy_distinct_context_objects_without_mutating_caller(self):
        learner = self.learner()
        learner.begin_batch_many([LearningToyEnv(), LearningToyEnv(seed=47)])
        learner.collect_many(1)
        payload = learner.checkpoint()
        copies = []
        for group in payload["parallel_pending"]:
            for sample in group:
                sample["input"]["context"] = json.loads(json.dumps(sample["input"]["context"]))
                copies.append(sample["input"]["context"])
        self.assertIsNot(copies[0], copies[1])
        resumed = self.learner()
        resumed.restore(payload, env_template=LearningToyEnv())
        first, second = [group[0]["input"]["context"] for group in resumed.parallel_pending]
        self.assertIs(first, second)
        self.assertIsNot(first, copies[0])
        copies[0]["geography"]["zones"].append({"id": "caller mutation"})
        self.assertEqual(len(first["geography"]["zones"]), 1)
        self.assertEqual(len(copies[0]["geography"]["zones"]), 2)

    def test_selected_action_diagnostics_preserve_raw_kind_parameters_and_sampling(self):
        for env in (LearningToyEnv(), CampaignAdapter(SchedulingToyRaw())):
            learner = self.learner()
            learner.begin_batch(env)
            learner.collect(1)
            event = learner.action_history[-1]
            features = learner.pending[0]["input"]["actions"]
            chosen = next(feature for feature in features if feature["id"] == event["action"])
            raw = chosen.get("action") or chosen
            self.assertEqual(event["action_kind"], raw["kind"])
            self.assertEqual(event["action_parameters"], raw.get("parameters", {}))
            before = copy.deepcopy(event["action_parameters"])
            raw.setdefault("parameters", {})["caller_only"] = True
            self.assertEqual(event["action_parameters"], before)

    def test_incompatible_checkpoint_rejection_is_transactional_including_global_rng(self):
        learner = self.learner()
        learner.run_batch(LearningToyEnv, 5)
        learner.begin_batch()
        learner.collect(1, LearningToyEnv)
        snapshot = learner.checkpoint()

        def wrong_metadata(payload):
            payload["metadata"]["compatibility"]["rules"] = "different-rules"

        def wrong_model(payload):
            payload["models"]["axis"]["values"] = torch.ones(4)

        def wrong_optimizer(payload):
            state = next(iter(payload["optimizers"]["axis"]["state"].values()))
            state["exp_avg"] = torch.full_like(state["exp_avg"], float("nan"))

        def wrong_rng(payload):
            payload["rng"]["numpy"] = ("not-a-generator",)

        def wrong_replay_owner(payload):
            payload["pending"][0]["owner"] = "comintern"

        def wrong_input_schema(payload):
            payload["replay"][0]["input"]["schema"] = "older-input-schema"

        def wrong_context(payload):
            features = payload["replay"][0]["input"]
            features["context"] = json.loads(json.dumps(features["context"]))
            features["context"]["schema"] = "other-scenario"

        def wrong_optimizer_hyperparameters(payload):
            payload["optimizers"]["axis"]["param_groups"][0]["betas"] = (0.1, 0.2)

        for mutation in (wrong_metadata, wrong_model, wrong_optimizer, wrong_rng, wrong_replay_owner,
                         wrong_input_schema, wrong_context, wrong_optimizer_hyperparameters):
            with self.subTest(mutation=mutation.__name__):
                broken = copy.deepcopy(snapshot)
                mutation(broken)
                with self.assertRaises((ValueError, RuntimeError, TypeError)):
                    learner.restore(broken, env_template=LearningToyEnv())
                self.assert_tree_equal(snapshot, learner.checkpoint())
        with self.assertRaisesRegex(ValueError, "compatible environment"):
            learner.restore(snapshot, env_template=LearningToyEnv(context_version="different-world"))
        self.assert_tree_equal(snapshot, learner.checkpoint())

    def test_graph_network_real_gradient_update_and_resume(self):
        learner = self.learner(real=True, config=replace(self.config, simulations=2, max_depth=3, epochs=1))
        before = learner.model_versions()
        result = learner.run_batch(LearningToyEnv, 5)
        self.assertEqual(result["rollout"]["terminal_samples"], 4)
        for player in PLAYERS:
            self.assertNotEqual(before[player], learner.model_versions()[player])
            self.assertTrue(all(np.isfinite(loss["total"]) for loss in result["update"]["losses"][player]))
        payload = learner.checkpoint()
        resumed = self.learner(real=True, config=learner.config)
        resumed.restore(payload, env_template=LearningToyEnv())
        self.assert_tree_equal(payload, resumed.checkpoint())

    def test_positive_shared_value_scale_and_fingerprints_are_required(self):
        for scale in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                LearningConfig(value_scale=scale)
        with self.assertRaisesRegex(ValueError, "same positive value scale"):
            self.learner(config=replace(self.config, value_scale=200))
        with self.assertRaisesRegex(ValueError, "fingerprints"):
            self.learner(compatibility={"scenario": "x", "rules": "y"})
        mixed_models = {player: TinyNet(self.model_config) for player in PLAYERS}
        mixed_models["allies"] = TinyNet(replace(self.model_config, value_scale=200))
        with self.assertRaisesRegex(ValueError, "Every actor model configuration"):
            CampaignLearner(mixed_models, self.model_config, self.config, compatibility=self.compatibility)


if __name__ == "__main__":
    unittest.main()
