"""GPU bulk paths match the retained scalar-row GPU math and all gradients."""
from __future__ import annotations

from contextlib import contextmanager
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import torch
import gwrl_cpp

from studies.campaign import neural
from studies.campaign.features import (NUMERIC_SCHEMA, action_factors, canonical, compile_graph,
                                      context_source_key)
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator, clear_neural_caches
from studies.shared.multiplayer_mcts import PLAYERS
from tests.test_campaign_neural import PublicEnv, action


def scalar_factor_batch(model, states, latent, scores, lengths, factors):
    rows, offset = [], 0
    for row, count in enumerate(lengths):
        part = scores[offset:offset + count]
        rows.append(model._factored_logits(states[row], latent[offset:offset + count], part, factors[row]) if count else part)
        offset += count
    return torch.cat(rows)


@contextmanager
def scalar_gpu_reference():
    with patch.object(neural, "_gpu_encoder_layout", neural._reference_encoder_layout), \
         patch.object(CampaignPolicyValueNet, "_factored_logits_batch", scalar_factor_batch):
        yield


def native_graph(graph, buckets):
    sources, targets, relations = zip(*graph.edges) if graph.edges else ((), (), ())
    return gwrl_cpp.CampaignNumericGraph.from_packed({"schema": "campaign-numeric-graph-v1", "buckets": buckets,
        "token_ids": np.asarray(graph.token_ids, dtype=np.int64),
        "token_offsets": np.asarray(graph.token_offsets, dtype=np.int64), "types": np.asarray(graph.types, dtype=np.int64),
        "numeric": np.asarray(graph.numeric, dtype=np.float64), "sources": np.asarray(sources, dtype=np.int64),
        "targets": np.asarray(targets, dtype=np.int64), "relations": np.asarray(relations, dtype=np.int64),
        "identities": graph.identities, "references": graph.references, "leaf_count": graph.leaf_count})


def numeric_item(item, buckets, cache):
    def convert(value):
        text = canonical(value)
        if text not in cache:
            cache[text] = native_graph(compile_graph(value, buckets), buckets)
        return cache[text]
    return {"schema": NUMERIC_SCHEMA, "owner": item["observation"]["current_decision_player"],
        "context_key": context_source_key(canonical(item["context"])), "packed_graph": {
            "context": convert(item["context"]), "observation": convert(item["observation"]),
            "actions": tuple(convert(value) for value in item["actions"]),
            "action_factors": tuple(action_factors(value) for value in item["actions"])}}


class CampaignGPUBatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def setUp(self):
        clear_neural_caches()
        self.config = CampaignModelConfig(hidden_dim=8, message_layers=2, token_buckets=128)
        self.menu = [action("duplicate_a", "move", unit="unit_1", path=["land_a", "land_b"], zone="land_b"),
            action("duplicate_b", "move", unit="unit_1", path=["land_a", "land_b"], zone="land_b"),
            action("source", "move", unit="unit_2", path=["land_a", "land_b"], zone="land_b"),
            action("path", "move", unit="unit_1", path=["land_a", "land_a"], zone="land_a"),
            action("target", "move", unit="unit_1", path=["land_a", "land_b"], zone="land_a"),
            action("attack", "attack", unit="unit_3", zone="land_b")]

    def tearDown(self):
        clear_neural_caches()

    def model(self, device="mps"):
        torch.manual_seed(416)
        return CampaignPolicyValueNet(self.config, device=device)

    def assert_close(self, first, second):
        torch.testing.assert_close(first.detach().cpu(), second.detach().cpu(), rtol=2e-4, atol=2e-5)

    def inputs(self):
        first, second = PublicEnv(), PublicEnv()
        second.static = copy.deepcopy(second.static)
        second.static["geography"]["nodes"]["land_a"]["ipp"] = 9
        second.static["catalog"]["units"][0]["attack"] = 5
        raw = [neural.make_input(first, self.menu), neural.make_input(first, self.menu[:1]),
               neural.make_input(second, self.menu[:3]), neural.make_input(PublicEnv(None, kind="chance"), [])]
        cache = {}
        return [raw[0], numeric_item(raw[1], 128, cache), numeric_item(raw[2], 128, cache), raw[3], raw[0]]

    @staticmethod
    def loss(logits, values):
        result = values.square().mean()
        for row, scores in enumerate(logits):
            if scores.numel(): result = result + (row + 1) * scores.square().mean()
        return result

    def test_cpu_path_remains_exact_and_never_calls_gpu_bulk_helpers(self):
        model, items = self.model("cpu").eval(), self.inputs()
        with torch.inference_mode(): expected = model.forward_batch(items, model_version="fixed")
        clear_neural_caches((model,))
        with patch.object(neural, "_gpu_encoder_layout", side_effect=AssertionError("GPU packing on CPU")), \
             patch.object(CampaignPolicyValueNet, "_factored_logits_batch", side_effect=AssertionError("GPU factors on CPU")), \
             torch.inference_mode():
            actual = model.forward_batch(items, model_version="fixed")
        self.assertTrue(torch.equal(expected[1], actual[1]))
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(expected[0], actual[0], strict=True)))

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_gpu_mixed_graphs_ragged_menus_forward_all_gradients_and_adam_match_reference(self):
        fast, reference, items = self.model(), self.model(), self.inputs()
        actual = fast.forward_batch(items)
        self.loss(*actual).backward()
        clear_neural_caches((fast, reference))
        with scalar_gpu_reference():
            expected = reference.forward_batch(items)
            self.loss(*expected).backward()
        self.assert_close(actual[1], expected[1])
        for a, b in zip(actual[0], expected[0], strict=True): self.assert_close(a, b)
        for (name, a), (_, b) in zip(fast.named_parameters(), reference.named_parameters(), strict=True):
            self.assertEqual(a.grad is None, b.grad is None, name)
            if a.grad is not None: self.assert_close(a.grad, b.grad)
        torch.optim.Adam(fast.parameters(), lr=.001).step()
        torch.optim.Adam(reference.parameters(), lr=.001).step()
        for a, b in zip(fast.parameters(), reference.parameters(), strict=True): self.assert_close(a, b)

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_gpu_batched_factors_keep_rows_and_duplicate_leaf_groups_independent(self):
        fast, reference = self.model(), self.model()
        factors = [tuple(action_factors(value) for value in self.menu), (),
                   tuple(action_factors(value) for value in self.menu[:1]),
                   tuple(action_factors(value) for value in self.menu[1:4])]
        lengths = [len(row) for row in factors]
        torch.manual_seed(91)
        cpu_states = torch.randn(len(lengths), 8); cpu_latent = torch.randn(sum(lengths), 8); cpu_scores = torch.randn(sum(lengths))
        def leaf(value): return value.to("mps").detach().requires_grad_()
        a = [leaf(value) for value in (cpu_states, cpu_latent, cpu_scores)]
        b = [leaf(value) for value in (cpu_states, cpu_latent, cpu_scores)]
        actual = fast._factored_logits_batch(*a, lengths, factors)
        expected = scalar_factor_batch(reference, *b, lengths, factors)
        self.assert_close(actual, expected)
        actual.square().sum().backward(); expected.square().sum().backward()
        for x, y in zip(a, b, strict=True): self.assert_close(x.grad, y.grad)
        for x, y in zip(fast.factor_heads.parameters(), reference.factor_heads.parameters(), strict=True):
            self.assert_close(x.grad, y.grad)

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_external_bank_aliases_same_graph_different_learned_nodes_and_cache_reuse(self):
        fast, reference = self.model().encoder, self.model().encoder
        graph = compile_graph({"source": "land_a", "target": "land_b"}, 128)
        registry = compile_graph(PublicEnv().static, 128)
        torch.manual_seed(37)
        data = [torch.randn(registry.node_count, 8), torch.randn(registry.node_count, 8) + 2.]
        def external():
            leaves = [value.to("mps").detach().requires_grad_() for value in data]
            encoded = [neural._EncodedGraph(registry, value, value.mean(0)) for value in leaves]
            return [[encoded[0]], [encoded[0]], [encoded[1]]], leaves
        rows, actual_leaves = external()
        actual = fast([graph] * 3, rows)
        coefficients = torch.arange(1, 9, device="mps", dtype=torch.float32)
        sum((value.pooled * coefficients).sum() for value in actual).backward()
        clear_neural_caches()
        rows, expected_leaves = external()
        with scalar_gpu_reference():
            expected = reference([graph] * 3, rows)
            sum((value.pooled * coefficients).sum() for value in expected).backward()
        for a, b in zip(actual, expected, strict=True): self.assert_close(a.nodes, b.nodes); self.assert_close(a.pooled, b.pooled)
        for a, b in zip(actual_leaves, expected_leaves, strict=True): self.assert_close(a.grad, b.grad)
        clear_neural_caches()
        rows, _ = external()
        first = neural._gpu_encoder_layout([graph] * 3, rows, torch.device("mps"), torch.float32)
        self.assertEqual(len(first.external_banks), 2)
        fresh_rows, _ = external()
        self.assertIs(first, neural._gpu_encoder_layout([graph] * 3, fresh_rows, torch.device("mps"), torch.float32))
        separate = [[fresh_rows[0][0]], [fresh_rows[2][0]], [fresh_rows[2][0]]]
        self.assertIsNot(first, neural._gpu_encoder_layout([graph] * 3, separate, torch.device("mps"), torch.float32))

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_empty_chance_and_all_actor_routing_match_scalar_gpu_reference(self):
        actual_models = {player: self.model().eval() for player in PLAYERS}
        expected_models = {player: self.model().eval() for player in PLAYERS}
        for index, player in enumerate(PLAYERS):
            with torch.no_grad():
                actual_models[player].value_head[-1].bias.add_(index / 10)
                expected_models[player].value_head[-1].bias.add_(index / 10)
        requests = [(PublicEnv(player), self.menu[:index + 1]) for index, player in enumerate(PLAYERS)]
        requests.extend([(PublicEnv(None, kind="chance"), []), (PublicEnv(terminal=True), [])])
        actual = NeuralEvaluator(actual_models, "frozen").evaluate_batch(requests)
        clear_neural_caches(tuple(actual_models.values()) + tuple(expected_models.values()))
        with scalar_gpu_reference(): expected = NeuralEvaluator(expected_models, "frozen").evaluate_batch(requests)
        for a, b in zip(actual, expected, strict=True):
            self.assert_close(torch.tensor(a.priors), torch.tensor(b.priors))
            self.assert_close(torch.tensor(a.values), torch.tensor(b.values))
        logits, values = actual_models["axis"].forward_batch([])
        self.assertEqual(logits, []); self.assertEqual(tuple(values.shape), (0, 3))

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_recorded_real_opening_and_combat_native_inputs_match_reference(self):
        root = Path(__file__).resolve().parents[1]
        paths = sorted((root / "studies/campaign/runs/backend-foundation-2026-10-25").glob("*.workload.json"))
        if not paths: self.skipTest("Optional recorded real workload is not present in this checkout")
        workload = json.loads(paths[0].read_text())
        selected = [next(row for row in workload["fixtures"] if row["label"] == label)
                    for label in ("opening", "japan_combat_movement")]
        from studies.campaign.curriculum import make_env
        from studies.campaign.features import make_numeric_input
        items = []
        for row in selected:
            env = make_env(row["seed"], calendar_rounds=3); env.restore(row["serialized"])
            items.append(make_numeric_input(env, env.legal_actions(), 128))
        self.assertTrue(all(item["schema"] == NUMERIC_SCHEMA for item in items))
        fast, reference = self.model().eval(), self.model().eval()
        with torch.inference_mode(): actual = fast.forward_batch(items, model_version="real-frozen")
        clear_neural_caches((fast, reference))
        with scalar_gpu_reference(), torch.inference_mode(): expected = reference.forward_batch(items, model_version="real-frozen")
        self.assert_close(actual[1], expected[1])
        for a, b in zip(actual[0], expected[0], strict=True): self.assert_close(a, b)


if __name__ == "__main__": unittest.main()
