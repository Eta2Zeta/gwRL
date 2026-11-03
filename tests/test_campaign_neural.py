"""The zone network: complete legal menus, batch independence and actor-routed values."""
from __future__ import annotations

import copy
from dataclasses import asdict
from functools import lru_cache
import pickle
import random
import unittest

import numpy as np
import torch
from torch import nn

import gwrl_cpp
from studies.campaign.curriculum import make_env
from studies.campaign.features import default_zone_spec, make_zone_input
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
from studies.shared.multiplayer_mcts import PLAYERS


def synthetic_zone(options: int, version: str | None = None):
    """A real zone input without an engine: one answer per option, in the default layout."""
    arrays = {"zone_index": [0, 0, 3], "zone_column": [1, 5, 1], "zone_value": [2, -1, 1],
              "global_column": [3], "global_value": [1],
              "action_offsets": list(range(options + 1)), "action_column": list(range(options)),
              "action_value": [1] * options, "action_source": [0] * options, "action_target": [1] * options,
              "path_offsets": [2 * i for i in range(options + 1)], "path_zone": [0, 1] * options,
              "factor_groups": [value for i in range(options) for value in (0, i // 2, i, i)]}
    return gwrl_cpp.campaign_zone_input(version or default_zone_spec().version,
                                        {name: np.asarray(values, dtype=np.int32) for name, values in arrays.items()})


def action(identity):
    return {"id": identity}


class PublicEnv:
    """A decision without an engine, handing out a synthetic zone input."""

    def __init__(self, actor="axis", *, kind="combat_movement", terminal=False):
        self.actor, self.kind, self.terminal = actor, kind, terminal

    def current_decision_player(self):
        return self.actor

    def decision_kind(self):
        return "terminal" if self.terminal else self.kind

    def is_terminal(self):
        return self.terminal

    def returns(self):
        return [700.0, -30.0, -400.0]

    def zone_input(self, actions):
        return synthetic_zone(len(actions))

    def serialize(self):
        raise AssertionError("Neural code must never request a checkpoint or future RNG")

    def planning_key(self):
        raise AssertionError("Planning hashes must not be neural features")


class ConstantNet(nn.Module):
    def __init__(self, values, scale):
        super().__init__()
        self.config = CampaignModelConfig(hidden_dim=8, value_scale=scale)
        self.value = nn.Parameter(torch.tensor(values, dtype=torch.float64) / scale)
        self.call_sizes = []

    def forward_batch(self, inputs):
        self.call_sizes.append(len(inputs))
        # Distinct logits ensure the evaluator uses each model's policy too.
        return [torch.arange(item.action_count, dtype=torch.float64) for item in inputs], self.value.expand(len(inputs), -1)


@lru_cache(maxsize=1)
def real_decisions():
    """Zone inputs of decisions from one random three-round game, and one chance position."""
    env = make_env(1951, calendar_rounds=3)
    rng = random.Random(4)
    found, chance, step = [], None, 0
    while not env.is_terminal() and len(found) < 12:
        if env.decision_kind() == "chance":
            if chance is None:
                chance = make_zone_input(env, ())
            env.resolve_chance()
            continue
        actions = tuple(env.legal_actions())
        step += 1
        if step % 9 == 0 and len(actions) > 2:
            found.append(make_zone_input(env, actions))
        env.apply_action(actions[rng.randrange(len(actions))])
    return tuple(found), chance


class CampaignNeuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        cls.decisions, cls.chance = real_decisions()

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def setUp(self):
        torch.manual_seed(81)

    def model(self, **kwargs):
        return CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=12, message_layers=2, **kwargs)).eval()

    def test_config_roundtrip_and_positive_finite_value_scale(self):
        config = CampaignModelConfig(value_scale=250)
        self.assertEqual(CampaignModelConfig(**asdict(config)), config)
        for scale in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                CampaignModelConfig(value_scale=scale)
        for parameters in ({"hidden_dim": 3}, {"hidden_dim": 8.5}, {"message_layers": 0},
                           {"policy_factorization": "yes"}):
            with self.assertRaises(ValueError):
                CampaignModelConfig(**parameters)

    def test_one_vector_per_column_and_layout_outside_the_state_dict(self):
        spec = default_zone_spec()
        model = self.model()
        self.assertEqual(model.layout_version, spec.version)
        self.assertEqual(model.zone_columns.weight.shape, (spec.zone_columns, 12))
        self.assertEqual(model.global_columns.weight.shape, (spec.global_columns, 12))
        self.assertEqual(model.option_columns.weight.shape, (spec.action_columns, 12))
        self.assertEqual(model.zone_identity.weight.shape[0], len(spec.zones))
        # Map facts and borders belong to the layout, which its version names.
        self.assertFalse({"zone_static", "edge_source", "edge_target", "edge_static", "in_degree"} & set(model.state_dict()))
        restored = self.model()
        restored.load_state_dict(model.state_dict())
        with torch.inference_mode():
            first, second = model.forward_batch(self.decisions[:2]), restored.forward_batch(self.decisions[:2])
        for a, b in zip(first[0], second[0], strict=True):
            self.assertTrue(torch.equal(a, b))
        self.assertTrue(torch.equal(first[1], second[1]))
        copied = copy.deepcopy(model)
        self.assertEqual(copied.layout_version, model.layout_version)

    def test_every_option_gets_one_finite_logit_and_the_menu_is_normalized(self):
        model = self.model()
        with torch.inference_mode():
            logits, values = model.forward_batch([*self.decisions, self.chance])
        self.assertEqual(values.shape, (len(self.decisions) + 1, 3))
        self.assertTrue(torch.isfinite(values).all())
        for item, scores in zip([*self.decisions, self.chance], logits, strict=True):
            self.assertEqual(scores.shape, (item.action_count,))
            self.assertTrue(torch.isfinite(scores).all())
            if item.action_count:
                # Factored logits are the exact options' log-probabilities.
                self.assertAlmostEqual(float(scores.exp().sum()), 1.0, places=5)
        self.assertEqual(logits[-1].numel(), 0)

    def test_batches_are_independent_of_their_neighbours(self):
        model = self.model()
        with torch.inference_mode():
            together = model.forward_batch(self.decisions)
            alone = [model.forward_batch([item]) for item in self.decisions]
        for index, (logits, values) in enumerate(alone):
            torch.testing.assert_close(together[0][index], logits[0], rtol=1e-5, atol=1e-5)
            torch.testing.assert_close(together[1][index], values[0], rtol=1e-5, atol=1e-5)

    def test_reordered_options_permute_their_logits_and_values_ignore_the_menu(self):
        model = self.model()
        item = max(self.decisions, key=lambda zone: zone.action_count)
        order = list(range(item.action_count))
        random.Random(9).shuffle(order)
        with torch.inference_mode():
            (full,), full_values = model.forward_batch([item])
            (shuffled,), shuffled_values = model.forward_batch([item.select(order)])
            (_,), value_only = model.forward_batch([item.without_actions()])
        torch.testing.assert_close(shuffled, full[order], rtol=1e-5, atol=1e-5)
        torch.testing.assert_close(shuffled_values, full_values, rtol=1e-6, atol=1e-6)
        torch.testing.assert_close(value_only, full_values, rtol=1e-6, atol=1e-6)

    def test_factorization_changes_only_the_readout(self):
        flat = self.model(policy_factorization=False)
        factored = self.model()
        factored.load_state_dict(flat.state_dict())
        with torch.inference_mode():
            raw, raw_values = flat.forward_batch(self.decisions[:3])
            normalized, values = factored.forward_batch(self.decisions[:3])
        torch.testing.assert_close(raw_values, values)
        self.assertFalse(all(torch.allclose(a, b) for a, b in zip(raw, normalized)))

    def test_one_changed_answer_changes_the_outputs(self):
        model = self.model()
        item = self.decisions[0]
        arrays = item.arrays()
        zone = arrays.copy()
        zone["zone_value"] = zone["zone_value"].copy()
        zone["zone_value"][0] += 1
        option = arrays.copy()
        option["action_value"] = option["action_value"].copy()
        option["action_value"][0] += 1
        zone_input = gwrl_cpp.campaign_zone_input(item.version, zone)
        option_input = gwrl_cpp.campaign_zone_input(item.version, option)
        # Input rows start at zero: an answer no training has reached adds nothing.
        with torch.inference_mode():
            (base,), base_values = model.forward_batch([item])
            (_,), zone_values = model.forward_batch([zone_input])
            (changed,), _ = model.forward_batch([option_input])
        torch.testing.assert_close(base_values, zone_values)
        torch.testing.assert_close(base, changed)
        # Once rows are trained, every answer reaches the outputs.
        with torch.no_grad():
            for table in (model.zone_columns, model.global_columns, model.option_columns):
                torch.nn.init.normal_(table.weight)
        with torch.inference_mode():
            (base,), base_values = model.forward_batch([item])
            (_,), zone_values = model.forward_batch([zone_input])
            (changed,), option_values = model.forward_batch([option_input])
        self.assertFalse(torch.allclose(base_values, zone_values))
        self.assertFalse(torch.allclose(base, changed))
        torch.testing.assert_close(base_values, option_values)

    def test_training_reaches_every_parameter_and_runs_in_double_precision(self):
        model = self.model().train()
        logits, values = model.forward_batch([*self.decisions[:4], self.chance])
        loss = values.square().mean() + sum(-scores.log_softmax(0)[0] for scores in logits if scores.numel())
        loss.backward()
        for name, parameter in model.named_parameters():
            self.assertIsNotNone(parameter.grad, name)
            self.assertTrue(torch.isfinite(parameter.grad).all(), name)
        used = torch.from_numpy(self.decisions[0].arrays()["zone_column"].astype(np.int64))
        self.assertGreater(float(model.zone_columns.weight.grad[used].abs().sum()), 0)
        double = self.model().double()
        logits, values = double.forward_batch(self.decisions[:2])
        self.assertEqual(values.dtype, torch.float64)
        self.assertEqual(logits[0].dtype, torch.float64)

    def test_inputs_of_another_layout_or_out_of_range_are_refused(self):
        model = self.model()
        with self.assertRaisesRegex(ValueError, "layout"):
            model.forward_batch([synthetic_zone(2, "campaign-zone-v0-other")])
        broken = synthetic_zone(2).arrays()
        broken["zone_column"] = broken["zone_column"].copy()
        broken["zone_column"][0] = default_zone_spec().zone_columns
        with self.assertRaisesRegex(ValueError, "range"):
            model.forward_batch([gwrl_cpp.campaign_zone_input(default_zone_spec().version, broken)])
        self.assertEqual(model.forward_batch([])[1].shape, (0, 3))

    def test_pickled_inputs_give_identical_outputs(self):
        model = self.model()
        restored = pickle.loads(pickle.dumps(self.decisions))
        with torch.inference_mode():
            first, second = model.forward_batch(self.decisions), model.forward_batch(list(restored))
        for a, b in zip(first[0], second[0], strict=True):
            self.assertTrue(torch.equal(a, b))
        self.assertTrue(torch.equal(first[1], second[1]))

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

    def test_actual_campaign_evaluation_ignores_search_randomness(self):
        env = make_env(91, calendar_rounds=3)
        while env.decision_kind() == "chance":
            env.resolve_chance()
        models = {player: self.model() for player in PLAYERS}
        evaluator = NeuralEvaluator(models, "v1")
        actions = env.legal_actions()
        first = evaluator.evaluate(env, actions)
        clone = env.clone_for_search(99871)
        second = evaluator.evaluate(clone, clone.legal_actions())
        self.assertEqual(len(first.priors), len(actions))
        self.assertAlmostEqual(sum(first.priors), 1.0, places=6)
        self.assertEqual(first.priors, second.priors)
        self.assertEqual(first.values, second.values)


if __name__ == "__main__":
    unittest.main()
