"""Complete campaign graphs, exact legal menus and actor-routed neural values."""
from __future__ import annotations

import copy
from dataclasses import asdict
import json
from pathlib import Path
import unittest
from unittest import mock

import torch
from torch import nn

from studies.campaign.features import (ADJACENT, IDENTITY_REFERENCE, cached_action,
                                      cached_context, cached_observation, compile_graph)
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator, make_input
from studies.shared.multiplayer_mcts import PLAYERS


def action(identity, kind="move", **parameters):
    return {"id": identity, "kind": "play", "player": "axis",
            "action": {"id": identity, "kind": kind, "parameters": parameters}}


class PublicEnv:
    def __init__(self, actor="axis", *, kind="combat_movement", terminal=False):
        self.actor, self.kind, self.terminal = actor, kind, terminal
        self.public = {
            "current_decision_player": actor, "decision_kind": kind,
            "state": {"units": {f"unit_{i}": {"id": f"unit_{i}", "type": "infantry",
                                              "zone": "land_a", "movement_remaining": i % 3}
                                for i in range(17)},
                      "clock": {"phase": kind, "turn": 3}, "pending": None},
        }
        self.static = {
            "players": list(PLAYERS),
            "geography": {"nodes": {
                "land_a": {"id": "land_a", "ipp": 2, "neighbors": [{"neighbor_id": "land_b", "river": True}]},
                "land_b": {"id": "land_b", "ipp": 1, "neighbors": [{"neighbor_id": "land_a", "river": False}]},
            }},
            "catalog": {"units": [{"id": "infantry", "attack": 2, "defense": 4}]},
        }

    def current_decision_player(self):
        return self.actor

    def decision_kind(self):
        return "terminal" if self.terminal else self.kind

    def observation(self):
        return self.public

    def context(self):
        return self.static

    def is_terminal(self):
        return self.terminal

    def returns(self):
        return [700.0, -30.0, -400.0]

    def serialize(self):
        raise AssertionError("Neural code must never request a checkpoint or future RNG")

    def planning_key(self):
        raise AssertionError("Planning hashes must not be neural features")


class ConstantNet(nn.Module):
    def __init__(self, values, scale):
        super().__init__()
        self.config = CampaignModelConfig(hidden_dim=8, token_buckets=64, value_scale=scale)
        self.value = nn.Parameter(torch.tensor(values, dtype=torch.float64) / scale)
        self.call_sizes = []

    def forward_batch(self, inputs):
        self.call_sizes.append(len(inputs))
        # Distinct logits ensure the evaluator uses each model's policy too.
        return [torch.arange(len(item["actions"]), dtype=torch.float64) for item in inputs], self.value.expand(len(inputs), -1)


class CampaignNeuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def setUp(self):
        torch.manual_seed(81)

    def model(self, **kwargs):
        return CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=12, message_layers=1,
                                                         token_buckets=256, **kwargs))

    def test_config_roundtrip_and_positive_finite_value_scale(self):
        config = CampaignModelConfig(value_scale=250)
        self.assertEqual(CampaignModelConfig(**asdict(config)), config)
        for scale in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                CampaignModelConfig(value_scale=scale)
        for parameters in ({"hidden_dim": 3}, {"hidden_dim": 8.5}, {"message_layers": 0},
                           {"token_buckets": 1}, {"policy_factorization": "yes"}):
            with self.assertRaises(ValueError):
                CampaignModelConfig(**parameters)

    def test_every_nested_field_and_entity_is_visited_without_a_cap(self):
        env = PublicEnv()
        env.public["state"]["new_rule"] = {"unfamiliar": [False, None, [], {}, "complete Unicode 海軍", 999999]}
        item = make_input(env, [action("a", unit="unit_16", route=["land_a", "land_b"])])
        graph = compile_graph(item["observation"], 256)

        def counts(value):
            if isinstance(value, dict):
                values = [counts(child) for child in value.values()]
            elif isinstance(value, list):
                values = [counts(child) for child in value]
            else:
                return 1, 1
            return 1 + sum(v[0] for v in values), sum(v[1] for v in values)

        self.assertEqual((graph.node_count, graph.leaf_count), counts(item["observation"]))
        self.assertEqual(len([name for name in graph.identities if name.startswith("unit_")]), 17)
        self.assertIn("unit_16", graph.identities)
        self.assertTrue(any(relation == IDENTITY_REFERENCE for _, _, relation in graph.edges))
        geography = compile_graph(item["context"], 256)
        self.assertEqual(sum(relation == ADJACENT for _, _, relation in geography.edges), 2)
        source, target = geography.identities["land_a"][0], geography.identities["land_b"][0]
        self.assertIn((source, target, ADJACENT), geography.edges)

    def test_input_snapshot_is_plain_detached_and_rejects_execution_data(self):
        env = PublicEnv()
        actions = [action("last", unit="unit_16")]
        item = make_input(env, actions)
        self.assertEqual(json.loads(json.dumps(item)), item)
        env.public["state"]["units"]["unit_16"]["movement_remaining"] = 99
        actions[0]["id"] = "changed"
        self.assertNotEqual(item["observation"], env.public)
        self.assertEqual(item["actions"][0]["id"], "last")
        for name in ("history", "rng", "dice_tape", "future_tape", "planning_key"):
            bad = PublicEnv()
            bad.public["state"][name] = [1]
            with self.assertRaises(ValueError):
                make_input(bad, [])

    def test_variable_menus_are_padding_free_and_batch_independent(self):
        env = PublicEnv()
        menus = [[], [action("one", unit="unit_1")],
                 [action(str(i), unit=f"unit_{i}", target="land_b") for i in range(17)]]
        inputs = [make_input(env, menu) for menu in menus]
        model = self.model()
        batched, values = model.forward_batch(inputs)
        self.assertEqual([tuple(row.shape) for row in batched], [(0,), (1,), (17,)])
        self.assertEqual(tuple(values.shape), (3, 3))
        for i, item in enumerate(inputs):
            individual, value = model.forward_batch([item])
            torch.testing.assert_close(individual[0], batched[i], atol=2e-6, rtol=2e-6)
            torch.testing.assert_close(value[0], values[i], atol=2e-6, rtol=2e-6)
            if batched[i].numel():
                self.assertAlmostEqual(batched[i].softmax(0).sum().item(), 1.0, places=6)
        empty, empty_values = model.forward_batch([])
        self.assertEqual(empty, [])
        self.assertEqual(tuple(empty_values.shape), (0, 3))

    def test_action_permutation_preserves_exact_leaf_scores_and_state_values(self):
        env = PublicEnv()
        menu = [action(str(i), kind="move" if i < 4 else "purchase", unit=f"unit_{i}",
                       route=["land_a", "land_b"], target="land_b") for i in range(9)]
        permutation = [8, 2, 5, 0, 6, 1, 7, 3, 4]
        inputs = [make_input(env, menu), make_input(env, [menu[i] for i in permutation])]
        logits, values = self.model().forward_batch(inputs)
        torch.testing.assert_close(logits[1], logits[0][permutation], atol=2e-6, rtol=2e-6)
        torch.testing.assert_close(values[0], values[1], atol=2e-6, rtol=2e-6)

    def test_factored_readout_normalizes_families_without_pruning(self):
        env = PublicEnv()
        menu = [action("only", "capture"), *(action(f"move_{i}", "move") for i in range(3))]
        model = self.model()
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.zero_()
        logits, _ = model.forward_batch([make_input(env, menu)])
        torch.testing.assert_close(logits[0].softmax(0), torch.tensor([.5, 1 / 6, 1 / 6, 1 / 6]))
        self.assertEqual(logits[0].numel(), len(menu))
        flat = self.model(policy_factorization=False)
        with torch.no_grad():
            for parameter in flat.parameters():
                parameter.zero_()
        flat_logits, _ = flat.forward_batch([make_input(env, menu)])
        torch.testing.assert_close(flat_logits[0].softmax(0), torch.full((4,), .25))

    def test_unknown_fields_last_entity_and_graph_changes_affect_outputs(self):
        env = PublicEnv()
        original = make_input(env, [action("a", unit="unit_16", target="land_b")])
        changed_field = copy.deepcopy(original)
        changed_field["observation"]["state"]["units"]["unit_16"]["future_rule_status"] = {"active": True, "amount": 48}
        changed_registry = copy.deepcopy(original)
        changed_registry["context"]["catalog"]["units"][0]["new_ability"] = {"strength": 14}
        changed_graph = copy.deepcopy(original)
        changed_graph["context"]["geography"]["nodes"]["land_a"]["neighbors"] = []
        model = self.model()
        _, values = model.forward_batch([original, changed_field, changed_registry, changed_graph])
        for value in values[1:]:
            self.assertGreater((value - values[0]).abs().max().item(), 1e-7)

    def test_gradients_recompute_context_after_parameter_updates_and_values_are_unbounded(self):
        model = self.model()
        env = PublicEnv()
        item = make_input(env, [action("a", "move"), action("b", "purchase")])
        optimizer = torch.optim.SGD(model.parameters(), lr=.05)
        logits, values = model.forward_batch([item])
        before = values.detach().clone()
        loss = -logits[0].log_softmax(0)[0] + (values - 2).square().mean()
        loss.backward()
        self.assertGreater(model.encoder.tokens.weight.grad.abs().sum().item(), 0)
        self.assertGreater(model.factor_heads[0][-1].weight.grad.abs().sum().item(), 0)
        optimizer.step()
        optimizer.zero_grad()
        logits, changed = model.forward_batch([item])
        self.assertGreater((before - changed).abs().max().item(), 1e-5)
        (changed.square().sum() - logits[0][1]).backward()
        with torch.no_grad():
            model.value_head[-1].weight.zero_()
            model.value_head[-1].bias.copy_(torch.tensor([3., -4., 9.]))
        _, unbounded = model.forward_batch([item])
        torch.testing.assert_close(unbounded[0], torch.tensor([3., -4., 9.]))

    def test_source_graph_reuse_detects_mutations_in_every_input_section(self):
        cached_context.cache_clear()
        cached_observation.cache_clear()
        cached_action.cache_clear()
        item = make_input(PublicEnv(), [action("a", unit="unit_16"), action("b", unit="unit_1")])
        model = self.model()
        with mock.patch("studies.campaign.features.compile_graph", wraps=compile_graph) as compile_source:
            before_logits, before_values = model.forward_batch([item])
            cold_calls = compile_source.call_count
            logits, values = model.forward_batch([item])
            self.assertEqual(compile_source.call_count, cold_calls)
            torch.testing.assert_close(logits[0], before_logits[0])
            torch.testing.assert_close(values, before_values)
            for section in ("context", "observation", "actions"):
                changed = copy.deepcopy(item)
                target = changed[section][0] if section == "actions" else changed[section]
                target["previously_unknown_rule"] = {"enabled": True, "amount": 731}
                logits, values = model.forward_batch([changed])
                self.assertGreater(compile_source.call_count, cold_calls)
                cold_calls = compile_source.call_count
                difference = ((logits[0] - before_logits[0]).abs().max() if section == "actions"
                              else (values - before_values).abs().max())
                self.assertGreater(difference.item(), 1e-7)

    def test_inference_preparation_remains_trainable_and_respects_tensor_dtype(self):
        item = make_input(PublicEnv(), [action("a", "move"), action("b", "purchase")])
        model = self.model()
        with torch.inference_mode():
            _, inference_values = model.forward_batch([item])
        logits, values = model.forward_batch([item])
        torch.testing.assert_close(values, inference_values)
        (values.square().sum() - logits[0].log_softmax(0)[0]).backward()
        self.assertGreater(model.encoder.tokens.weight.grad.abs().sum().item(), 0)
        model.zero_grad(set_to_none=True)
        model.double()
        logits, values = model.forward_batch([item])
        self.assertEqual(values.dtype, torch.float64)
        (values.square().sum() - logits[0].log_softmax(0)[0]).backward()
        self.assertEqual(model.encoder.tokens.weight.grad.dtype, torch.float64)

    def test_actor_routing_batch_order_raw_scaling_and_chance_mean(self):
        raw_values = {"axis": [120, -400, 80], "allies": [-50, 240, 25], "comintern": [30, 45, 330]}
        scales = {"axis": 10., "allies": 25., "comintern": 100.}
        models = {player: ConstantNet(raw_values[player], scales[player]) for player in PLAYERS}
        evaluator = NeuralEvaluator(models, version="test-weights-7")
        menu = [action("a"), action("b")]
        requests = [(PublicEnv("allies"), menu), (PublicEnv("axis"), menu),
                    (PublicEnv(None, kind="chance"), []), (PublicEnv("axis"), menu),
                    (PublicEnv("comintern"), menu), (PublicEnv(None, terminal=True), [])]
        results = evaluator.evaluate_batch(requests)
        self.assertEqual(evaluator.version, "test-weights-7")
        for index, player in ((0, "allies"), (1, "axis"), (3, "axis"), (4, "comintern")):
            self.assertEqual(tuple(results[index].values), tuple(raw_values[player]))
            self.assertEqual(len(results[index].priors), 2)
            self.assertGreater(results[index].priors[1], results[index].priors[0])
        expected = tuple(sum(raw_values[player][i] for player in PLAYERS) / 3 for i in range(3))
        self.assertEqual(tuple(results[2].values), expected)
        self.assertEqual(results[2].priors, [])
        self.assertEqual(tuple(results[5].values), (700., -30., -400.))
        self.assertEqual([models[p].call_sizes for p in PLAYERS], [[3], [2], [2]])
        self.assertTrue(all(model.training for model in models.values()))
        self.assertEqual(evaluator.evaluate_batch([]), [])

    def test_evaluator_rejects_unknown_owners_and_nonfinite_output(self):
        models = {player: ConstantNet([1, 2, 3], 100) for player in PLAYERS}
        with self.assertRaises(ValueError):
            NeuralEvaluator({"axis": models["axis"]}, "missing")
        evaluator = NeuralEvaluator(models, "v1")
        with self.assertRaises(ValueError):
            evaluator.evaluate(PublicEnv("unlisted"), [action("a")])
        with self.assertRaises(ValueError):
            evaluator.evaluate(PublicEnv(None, kind="combat"), [])
        with torch.no_grad():
            models["axis"].value[0] = torch.inf
        with self.assertRaises(ValueError):
            evaluator.evaluate(PublicEnv("axis"), [action("a")])

    def test_actual_campaign_features_include_all_registries_and_ignore_search_rng(self):
        import gwrl_cpp
        from studies.shared.campaign_adapter import CampaignAdapter

        scenario = str(Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936")
        env = CampaignAdapter(gwrl_cpp.CampaignEnv(scenario, 91))
        item = make_input(env, env.legal_actions())
        clone = env.clone_for_search(99871)
        self.assertEqual(item, make_input(clone, clone.legal_actions()))
        self.assertEqual(len(item["observation"]["state"]["units"]), 99)
        self.assertEqual(len(item["context"]["geography"]["nodes"]), 37)
        self.assertEqual(len(item["context"]["catalog"]), 5)
        self.assertEqual(item["actions"], [choice.features() for choice in env.legal_actions()])
        logits, values = self.model().forward_batch([item])
        self.assertEqual(tuple(logits[0].shape), (len(env.legal_actions()),))
        self.assertEqual(tuple(values.shape), (1, 3))
        self.assertTrue(torch.isfinite(values).all())


if __name__ == "__main__":
    unittest.main()
