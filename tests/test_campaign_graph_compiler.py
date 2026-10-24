"""Exact native/reference features, including numeric bits and learned gradients."""
from __future__ import annotations

import copy
import json
import random
import struct
import unittest
from unittest.mock import patch

import torch

from studies.campaign import features
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
from studies.shared.immutable_json import freeze_json


class CampaignGraphCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if features.graph_compiler_backend() != "native":
            raise RuntimeError("Rebuild gwrl_cpp before testing the native campaign graph compiler")
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def assert_graph_equal(self, value, buckets=2048):
        expected = features.compile_graph_python(value, buckets)
        actual = features.compile_graph(value, buckets)
        self.assertEqual(actual, expected)
        # Ordinary float equality cannot distinguish -0.0 from +0.0.
        self.assertEqual(b"".join(struct.pack("!8d", *row) for row in actual.numeric),
                         b"".join(struct.pack("!8d", *row) for row in expected.numeric))
        return actual

    def test_all_scalar_types_unicode_numeric_strings_and_signed_zero(self):
        values = [None, True, False, 0, -0.0, 1, -1, 2**200, 1e-310, -1e200,
                  "", "海軍", "emoji 🛳️", "a\x00b", "12", "+12.5", "-0", "+0.0",
                  "١٢.٥", "１２", "-١٢", "1e3", "NaN", "Infinity", "1x", " 12", ".5",
                  "_./:[] punctuation!", "7" * 400, [], {}, [None, [], {}]]
        for buckets in (2, 7, 2048, 16384):
            with self.subTest(buckets=buckets):
                self.assert_graph_equal({"unknown_field": values, "negative_zero": -0.0}, buckets)
        # Exercise the shared numeric constant cache in both zero orders.
        for values in ([0.0, -0.0], [-0.0, 0.0], ["-0", "0"], ["0", "-0"]):
            self.assert_graph_equal(values)

    def test_entities_reference_duplicates_and_unsorted_geography_edge_order(self):
        value = {"geography": {"nodes": {
            "z": {"id": "z", "neighbors": [{"neighbor_id": "a"}, {"neighbor_id": "a"}]},
            "a": {"id": "a", "neighbors": [{"neighbor_id": "z"}]},
        }}, "units": {"u": {"id": "duplicate", "zone": "a"}, "v": {"id": "duplicate", "zone": "z"}},
                 "references": ["duplicate", "duplicate", "u", "a", "z"]}
        graph = self.assert_graph_equal(value)
        self.assertGreater(len(graph.identities["duplicate"]), 1)
        # The public direct compiler preserves input geography insertion order;
        # the serialized cache path starts with canonical key order instead.
        canonical = json.loads(features.canonical(value))
        self.assert_graph_equal(canonical)
        self.assert_graph_equal(freeze_json(canonical))

    def test_generated_nested_documents_and_caller_mutation(self):
        rng = random.Random(4281)
        leaves = [None, False, True, -0.0, 123456789, -1.25, "７", "海軍", "unit_1", ""]

        def document(depth):
            if depth == 0 or rng.randrange(4) == 0:
                return rng.choice(leaves)
            if rng.randrange(2):
                return [document(depth - 1) for _ in range(rng.randrange(5))]
            return {f"field_{i}": document(depth - 1) for i in range(rng.randrange(5))}

        for _ in range(40):
            self.assert_graph_equal(document(5), 256)
        value = {"units": {"unit_1": {"id": "unit_1", "damage": 0}}}
        before = self.assert_graph_equal(value)
        value["units"]["unit_1"]["damage"] = 2
        after = self.assert_graph_equal(value)
        self.assertNotEqual(before, after)

    def test_invalid_inputs_keep_reference_errors_and_callback_failures_propagate(self):
        for value in (float("nan"), float("inf"), -float("inf"), {1: "bad key"}, (1, 2), object(), 10**400):
            with self.subTest(value=type(value).__name__):
                try:
                    features.compile_graph_python(value, 256)
                except Exception as expected:
                    with self.assertRaises(type(expected)):
                        features.compile_graph(value, 256)
                else:
                    self.fail("Invalid fixture was accepted by the reference")
        for buckets in (0, 1, -1):
            with self.assertRaises(ValueError):
                features.compile_graph({}, buckets)
        with patch.object(features, "lexical_ids", side_effect=RuntimeError("callback rejected")):
            with self.assertRaisesRegex(RuntimeError, "callback rejected"):
                features.compile_graph({"field": "value"}, 256)

    def test_actual_campaign_complete_observation_context_and_legal_actions(self):
        from studies.campaign.curriculum import make_env
        env = make_env(1951, calendar_rounds=1)
        for _ in range(12):
            item = features.make_input(env, env.legal_actions() if env.decision_kind() != "chance" else [])
            self.assert_graph_equal(item["observation"])
            if _ == 0:
                self.assert_graph_equal(item["context"])
            for action in item["actions"]:
                self.assert_graph_equal(action)
            if env.decision_kind() == "chance":
                env.resolve_chance()
            else:
                choices = env.legal_actions()
                # Resolve declaration offers, then move the calendar forward.
                chosen = next((a for a in choices if (a.features().get("action") or {}).get("kind") == "end_phase"), choices[-1])
                env.apply_action(chosen)

    def test_numeric_subclasses_preserve_the_reference_float_conversion(self):
        class CustomFloat(float):
            def __float__(self):
                return -0.0

        class CustomInteger(int):
            def __float__(self):
                return 9.25

        self.assert_graph_equal([CustomFloat(7.0), CustomInteger(3)])

    def test_callback_mutation_cannot_invalidate_retained_source_or_tokens(self):
        lexical = features.lexical_ids

        def changing_source(compiler):
            source = {"units": {"u": {"id": "unit_1", "zone": "land"}}}

            def callback(text, role, buckets):
                if text == "unit_1" and role == "value":
                    source["units"].clear()
                return lexical(text, role, buckets)

            if compiler == "reference":
                with patch.object(features, "lexical_ids", callback):
                    return features.compile_graph_python(source, 256)
            return features.Graph(**features._native_compile_graph(
                source, 256, callback, features._string_descriptor, features._numeric_features))

        self.assertEqual(changing_source("native"), changing_source("reference"))
        shared = [1234567]

        def mutable_lexical(text, _role, _buckets):
            if text == "$":
                return shared
            shared.clear()
            return [9]

        result = features._native_compile_graph({"field": 2}, 256, mutable_lexical,
                                                features._string_descriptor, features._numeric_features)
        self.assertEqual(result["token_ids"][0], 1234567)
        self.assertEqual(shared, [])

    def test_model_outputs_and_gradients_match_the_reference_exactly(self):
        item = {"schema": features.SCHEMA,
                "context": {"geography": {"nodes": {"land": {"id": "land", "neighbors": []}}}},
                "observation": {"state": {"units": {"unit": {"id": "unit", "zone": "land", "damage": -0.0}},
                                          "new_rule": ["１２", None, True, [], {}]}},
                "actions": [{"id": "one", "kind": "move", "parameters": {"unit": "unit", "zone": "land"}},
                            {"id": "two", "kind": "pass", "parameters": {}}]}
        torch.manual_seed(813)
        reference = CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=8, message_layers=1, token_buckets=128))
        native = copy.deepcopy(reference)

        def run(model):
            for cache in (features.cached_context, features.cached_observation, features.cached_action):
                cache.cache_clear()
            logits, values = model.forward_batch([item])
            loss = values.square().sum() - logits[0].log_softmax(0)[0]
            loss.backward()
            return logits, values

        with patch.object(features, "_native_compile_graph", None):
            expected_logits, expected_values = run(reference)
        actual_logits, actual_values = run(native)
        torch.testing.assert_close(actual_logits[0], expected_logits[0], rtol=0, atol=0)
        torch.testing.assert_close(actual_values, expected_values, rtol=0, atol=0)
        for (name, left), (_, right) in zip(reference.named_parameters(), native.named_parameters(), strict=True):
            self.assertEqual(left.grad is None, right.grad is None, name)
            if left.grad is not None:
                torch.testing.assert_close(right.grad, left.grad, rtol=0, atol=0, msg=name)
        self.assertGreater(native.encoder.tokens.weight.grad.abs().sum().item(), 0)


if __name__ == "__main__":
    unittest.main()
