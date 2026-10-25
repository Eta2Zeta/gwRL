"""Numerical graph consumption preserves complete policies and training gradients."""
from __future__ import annotations

import copy
from functools import lru_cache
import unittest
from unittest import mock

import numpy as np
import torch

from studies.campaign import neural
from studies.campaign.features import (SCHEMA, action_factors, canonical,
                                      cached_action, cached_context, cached_observation)
from studies.shared.multiplayer_mcts import Evaluation, MctsConfig, PLAYERS, VectorMCTS


class _ArrayGraph:
    """Read-only native-buffer protocol double; the compiler has separate oracles."""
    def __init__(self, graph, buckets=128):
        self.graph, self.node_count, self.leaf_count = graph, graph.node_count, graph.leaf_count
        self.token_buckets = buckets
        sources, targets, relations = zip(*graph.edges) if graph.edges else ((), (), ())
        self.buffers = {"token_ids": np.asarray(graph.token_ids, dtype=np.int64),
                        "token_offsets": np.asarray(graph.token_offsets, dtype=np.int64),
                        "types": np.asarray(graph.types, dtype=np.int64),
                        "numeric": np.asarray(graph.numeric, dtype=np.float64),
                        "sources": np.asarray(sources, dtype=np.int64),
                        "targets": np.asarray(targets, dtype=np.int64),
                        "relations": np.asarray(relations, dtype=np.int64)}
        for value in self.buffers.values():
            value.flags.writeable = False
        self.nbytes = sum(array.nbytes for array in self.buffers.values()) + neural._graph_source_bytes(graph)

    def arrays(self):
        return self.buffers

    def external_references(self, context):
        pairs = [(destination, index) for destination, identity in self.graph.references
                 for index in context.graph.identities.get(identity, ())]
        destinations, indices = zip(*pairs) if pairs else ((), ())
        return np.asarray(destinations, dtype=np.int64), np.asarray(indices, dtype=np.int64)

    def debug_graph(self):
        return self.graph


@lru_cache(maxsize=32)
def _array_document(serialized, buckets, role):
    compiler = {"context": cached_context, "observation": cached_observation, "action": cached_action}[role]
    return _ArrayGraph(compiler(serialized, buckets), buckets)


def _numeric(item, buckets=128):
    return {"schema": neural.NUMERIC_SCHEMA, "owner": item["observation"].get("owner"),
            "context_key": canonical(item["context"]),
            "packed_graph": {
                "context": _array_document(canonical(item["context"]), buckets, "context"),
                "observation": _array_document(canonical(item["observation"]), buckets, "observation"),
                "actions": tuple(_array_document(canonical(action), buckets, "action") for action in item["actions"]),
                "action_factors": tuple(action_factors(action) for action in item["actions"])}}


def _action(identity, unit="u0", target="b", kind="move"):
    return {"id": identity, "kind": "play", "player": "axis", "action": {
        "id": identity, "kind": kind, "parameters": {"unit": unit, "target": target, "route": ["a", target]}}}


def _item():
    return {"schema": SCHEMA, "observation": {
        "owner": "axis", "state": {"units": {"u0": {"id": "u0", "zone": "a", "type": "infantry"},
                                                 "u1": {"id": "u1", "zone": "b", "type": "infantry"}},
                                      "pending": {"kind": "combat_movement", "zone": "a"}}},
            "context": {"geography": {"nodes": {
                "a": {"id": "a", "ipp": 2, "neighbors": [{"neighbor_id": "b"}]},
                "b": {"id": "b", "ipp": 1, "neighbors": [{"neighbor_id": "a"}]}}},
                        "catalog": {"units": [{"id": "infantry", "attack": 2, "defense": 4}]}},
            "actions": [_action("one"), _action("two", "u1", "a"), _action("three", kind="purchase")]}


class _SearchEnv:
    def __init__(self, depth=0, path=""):
        self.depth, self.path = depth, path

    def current_decision_player(self):
        return None if self.is_terminal() else PLAYERS[self.depth % 3]

    def decision_kind(self):
        return "terminal" if self.is_terminal() else "choose"

    def is_terminal(self):
        return self.depth == 3

    def legal_actions(self):
        return [] if self.is_terminal() else [_action("a"), _action("b", target="a")]

    def apply_action(self, action):
        self.depth += 1
        self.path += action["id"]

    def clone_for_search(self, seed):
        return copy.copy(self)

    def planning_key(self):
        return f"{self.depth}:{self.path}"

    def observation(self):
        value = _item()["observation"]
        value.update(owner=self.current_decision_player(), depth=self.depth, path=self.path)
        return value

    def context(self):
        return _item()["context"]

    def returns(self):
        return [float(self.path.count("a")), float(self.path.count("b")), 0.0]


class CampaignNumericNeuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def setUp(self):
        torch.manual_seed(813)
        for cache in (neural._REFERENCE_INDICES, neural._ENCODER_LAYOUTS, neural._ACTION_FACTORS, neural._FACTOR_LAYOUTS):
            cache.clear()
        neural._GRAPH_TENSORS.clear()
        neural._GRAPH_TENSOR_BYTES = 0
        _array_document.cache_clear()

    def model(self):
        return neural.CampaignPolicyValueNet(neural.CampaignModelConfig(
            hidden_dim=8, message_layers=2, token_buckets=128))

    def assert_outputs_equal(self, first, second):
        left, right = first[0], second[0]
        self.assertEqual(len(left), len(right))
        for a, b in zip(left, right, strict=True):
            torch.testing.assert_close(a, b, atol=0, rtol=0)
        torch.testing.assert_close(first[1], second[1], atol=0, rtol=0)

    def test_numeric_and_raw_logits_values_and_all_training_gradients_are_bitwise_equal(self):
        item = _item()
        empty = copy.deepcopy(item)
        empty["actions"] = []
        changed = copy.deepcopy(item)
        changed["context"]["catalog"]["unknown_future_rule"] = {"active": True, "value": -0.0}
        changed["observation"]["state"]["new_rule"] = [None, "海軍", 73]
        inputs = [item, empty, changed]
        raw, numeric = self.model(), self.model()
        numeric.load_state_dict(raw.state_dict())
        outputs = raw.forward_batch(inputs), numeric.forward_batch([_numeric(item) for item in inputs])
        self.assert_outputs_equal(*outputs)
        for model, (logits, values) in zip((raw, numeric), outputs, strict=True):
            loss = values.square().sum() - sum(row.log_softmax(0)[0] for row in logits if row.numel())
            loss.backward()
        for (name, left), (other_name, right) in zip(raw.named_parameters(), numeric.named_parameters(), strict=True):
            self.assertEqual(name, other_name)
            torch.testing.assert_close(left.grad, right.grad, atol=0, rtol=0, msg=name)

    def test_prepared_buffers_need_no_json_or_python_graph_compilation_and_cache_references(self):
        item, model = _numeric(_item()), self.model()
        with mock.patch.object(neural, "canonical", side_effect=AssertionError("No raw JSON conversion")), \
             mock.patch.object(neural, "cached_context", side_effect=AssertionError("No graph compilation")), \
             mock.patch.object(_ArrayGraph, "external_references", autospec=True,
                               side_effect=original_match) as matches:
            first = model.forward_batch([item])
            calls = matches.call_count
            second = model.forward_batch([item])
            self.assertGreater(calls, 0)
            self.assertEqual(matches.call_count, calls)
            self.assert_outputs_equal(first, second)

    def test_numerical_graphs_reject_wrong_vocabulary_and_incomplete_policy_factors(self):
        item, model = _numeric(_item(), buckets=64), self.model()
        with self.assertRaisesRegex(ValueError, "lexical vocabulary"):
            model.forward_batch([item])
        item = _numeric(_item())
        item["packed_graph"]["action_factors"] = item["packed_graph"]["action_factors"][:-1]
        with self.assertRaisesRegex(ValueError, "four exact policy factors"):
            model.forward_batch([item])

    def test_strong_graph_references_are_included_in_cache_memory_budget(self):
        item, model = _numeric(_item()), self.model().eval()
        with torch.inference_mode():
            model.forward_batch([item], model_version="weights")
        for cache in (neural._REFERENCE_INDICES, neural._ENCODER_LAYOUTS, model._static_contexts):
            expected_sources = {}
            for key, identities in cache.entry_sources.items():
                for identity in identities:
                    expected_sources[identity] = expected_sources.get(identity, 0) + 1
            for identity, (source, references, size) in cache.source_refs.items():
                self.assertEqual(references, expected_sources[identity])
                self.assertGreaterEqual(size, source.nbytes)
            accounted = sum(size for _, size in cache.values.values())
            accounted += sum(size for _, _, size in cache.source_refs.values())
            self.assertEqual(cache.bytes, accounted)

    def test_shared_source_storage_is_charged_once_and_released_after_last_eviction(self):
        source = _numeric(_item())["packed_graph"]["context"]
        source_size = neural._graph_source_bytes(source)
        cache = neural._SourceCache(source_size + 12, 2)
        cache.put(("a",), (source, "a"), 4, sources=(source, source))
        cache.put(("b",), (source, "b"), 4, sources=(source,))
        self.assertEqual(cache.bytes, source_size + 8)
        self.assertEqual(cache.source_refs[id(source)][1], 2)
        cache.put(("c",), (source, "c"), 4, sources=(source,))
        self.assertIsNone(cache.get(("a",)))
        self.assertEqual(cache.bytes, source_size + 8)
        self.assertEqual(cache.source_refs[id(source)][1], 2)
        cache.put(("plain",), "no source", 8)
        self.assertEqual(cache.bytes, source_size + 12)
        cache.put(("plain2",), "no source", 4)
        self.assertEqual(cache.bytes, 12)
        self.assertEqual(cache.source_refs, {})
        self.assertEqual(len(cache.entry_sources), 2)
        cache.clear()
        self.assertEqual(cache.bytes, 0)
        self.assertEqual(cache.entry_sources, {})

    def test_evaluator_preserves_legacy_subclass_contract_and_passes_supported_versions(self):
        class Legacy(neural.CampaignPolicyValueNet):
            def forward_batch(self, inputs):
                self.received = [item["schema"] for item in inputs], None
                self.assert_raw = [item["actions"] for item in inputs]
                return super().forward_batch(inputs)

        class Versioned(neural.CampaignPolicyValueNet):
            def forward_batch(self, inputs, *, model_version=None):
                self.received = [item["schema"] for item in inputs], model_version
                return super().forward_batch(inputs, model_version=model_version)

        class Flexible(neural.CampaignPolicyValueNet):
            def forward_batch(self, inputs, **kwargs):
                self.received = [item["schema"] for item in inputs], kwargs["model_version"]
                return super().forward_batch(inputs, **kwargs)

        reference, env = self.model(), _SearchEnv()
        actions = env.legal_actions()
        raw = neural.make_input(env, actions)
        expected = None
        for kind in (Legacy, Versioned, Flexible):
            model = kind(reference.config)
            model.load_state_dict(reference.state_dict())
            evaluator = neural.NeuralEvaluator({player: model for player in PLAYERS}, "frozen-v1")
            with mock.patch("studies.campaign.features.make_numeric_input", return_value=_numeric(raw)) as prepare:
                actual = evaluator.evaluate(env, actions)
            if kind is Legacy:
                self.assertEqual(model.received, ([SCHEMA], None))
                prepare.assert_not_called()
                expected = actual
            else:
                self.assertEqual(model.received, ([neural.NUMERIC_SCHEMA], "frozen-v1"))
                self.assertEqual(actual, expected)
                prepare.assert_called_once()

    def test_frozen_context_cache_requires_version_and_never_reuses_training_gradients(self):
        item, model = _numeric(_item()), self.model()
        baseline = copy.deepcopy(model)
        model.eval()
        with mock.patch.object(model.encoder, "forward", wraps=model.encoder.forward) as calls:
            with torch.inference_mode():
                cold = model.forward_batch([item], model_version="weights-1")
                self.assertEqual(calls.call_count, 3)
                warm = model.forward_batch([item], model_version="weights-1")
                self.assertEqual(calls.call_count, 5)
                uncached = model.forward_batch([item])
                self.assertEqual(calls.call_count, 8)
                self.assert_outputs_equal(cold, warm)
                self.assert_outputs_equal(cold, uncached)
            model.train()
            trained = model.forward_batch([item], model_version="weights-1")
            self.assertEqual(calls.call_count, 11)
        expected = baseline.forward_batch([item])
        self.assert_outputs_equal(trained, expected)
        for candidate, result in ((model, trained), (baseline, expected)):
            (result[1].square().sum() - result[0][0].log_softmax(0)[0]).backward()
        for left, right in zip(model.parameters(), baseline.parameters(), strict=True):
            torch.testing.assert_close(left.grad, right.grad, atol=0, rtol=0)

    def test_frozen_cache_invalidates_weights_buffers_version_context_and_restore(self):
        item, model = _numeric(_item()), self.model().eval()
        model.register_buffer("test_buffer", torch.tensor([1.0]))
        state = copy.deepcopy(model.state_dict())
        with mock.patch.object(model.encoder, "forward", wraps=model.encoder.forward) as calls, torch.inference_mode():
            def verify_recomputation(version="v1", source=item):
                previous = calls.call_count
                cached = model.forward_batch([source], model_version=version)
                self.assertEqual(calls.call_count - previous, 3)
                uncached = model.forward_batch([source])
                self.assert_outputs_equal(cached, uncached)
            verify_recomputation()
            verify_recomputation("v2")
            model.encoder.numbers.weight.add_(.125)
            verify_recomputation("v2")
            model.test_buffer.add_(1)
            verify_recomputation("v2")
            changed = _item()
            changed["context"]["new_registry_entry"] = {"id": "new", "rule": 7}
            verify_recomputation("v2", _numeric(changed))
            model.load_state_dict(state)
            self.assertEqual(model._static_contexts.bytes, 0)
            verify_recomputation("v2")
        model.double()
        with torch.inference_mode():
            self.assert_outputs_equal(model.forward_batch([item], model_version="v2"), model.forward_batch([item]))
        self.assertTrue(all(value.nodes.dtype == torch.float64
                            for values, _ in model._static_contexts.values.values() for value in values))

    def test_cache_limits_evict_and_disabled_caches_preserve_exact_outputs(self):
        item, model = _numeric(_item()), self.model().eval()
        caches = (neural._REFERENCE_INDICES, neural._ENCODER_LAYOUTS, neural._ACTION_FACTORS,
                  neural._FACTOR_LAYOUTS, model._static_contexts)
        with torch.inference_mode():
            expected = model.forward_batch([item], model_version="fixed")
            for cache in caches:
                self.assertLessEqual(cache.bytes, cache.limit)
                self.assertLessEqual(len(cache.values), cache.entries)
        old_limits = [(cache.limit, cache.entries) for cache in caches]
        try:
            for cache in caches:
                cache.clear()
                cache.limit, cache.entries = 1, 1
            with torch.inference_mode():
                self.assert_outputs_equal(expected, model.forward_batch([item], model_version="fixed"))
            for cache in caches:
                self.assertEqual(cache.bytes, 0)
                self.assertEqual(len(cache.values), 0)
        finally:
            for cache, (limit, entries) in zip(caches, old_limits, strict=True):
                cache.limit, cache.entries = limit, entries
        cache = neural._SourceCache(8, 2)
        cache.put(("a",), "a", 4)
        cache.put(("b",), "b", 4)
        self.assertEqual(cache.get(("a",)), "a")
        cache.put(("c",), "c", 4)
        self.assertIsNone(cache.get(("b",)))
        self.assertEqual(cache.bytes, 8)

    def test_cached_and_uncached_numeric_search_visits_actions_and_values_are_identical(self):
        model = self.model().eval()

        class Evaluator:
            version = "numeric-oracle-1"
            def __init__(self, cached):
                self.cached = cached
            def evaluate(self, env, actions):
                raw = {"schema": SCHEMA, "context": env.context(), "observation": env.observation(), "actions": actions}
                with torch.inference_mode():
                    logits, values = model.forward_batch([_numeric(raw)], model_version=self.version if self.cached else None)
                return Evaluation(logits[0].softmax(0).tolist(), (values[0] * model.config.value_scale).tolist())

        config = MctsConfig(simulations=12, max_depth=2, seed=57, record_trace=True)
        cached = VectorMCTS(Evaluator(True), config).search(_SearchEnv())
        plain = VectorMCTS(Evaluator(False), config).search(_SearchEnv())
        self.assertEqual(cached, plain)


original_match = _ArrayGraph.external_references

if __name__ == "__main__":
    unittest.main()
