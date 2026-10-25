"""Matched-pilot fingerprints compare logical data, preserving numerical bits."""
from __future__ import annotations

import copy
import unittest
from unittest import mock

import gwrl_cpp

from studies.campaign.features import (_numeric_features, _string_descriptor,
                                      compile_graph_python, lexical_ids)
from tools.benchmark_campaign_numeric_learning import (compare_reports, graph_digest,
                                                        replay_features_equal, tree_digest)


class CampaignNumericLearningBenchmarkTests(unittest.TestCase):
    def test_tree_digest_retains_scalar_types_signed_zero_and_tensor_bits(self):
        import numpy as np
        import torch

        self.assertNotEqual(tree_digest(0.), tree_digest(-0.))
        self.assertNotEqual(tree_digest(1), tree_digest(1.))
        self.assertNotEqual(tree_digest([1, 2]), tree_digest((1, 2)))
        first = {"tensor": torch.tensor([0., -0.], dtype=torch.float64),
                 "numpy": np.asarray([0., -0.], dtype=np.float64)}
        self.assertEqual(tree_digest(first), tree_digest(copy.deepcopy(first)))
        first["tensor"][1] = 0.
        self.assertNotEqual(tree_digest(first), tree_digest({**first, "tensor": torch.tensor([0., -0.], dtype=torch.float64)}))

    def test_native_and_legacy_graph_digests_normalize_transport_exactly(self):
        compiler = gwrl_cpp.CampaignNumericGraphCompiler(128, lexical_ids, _string_descriptor, _numeric_features)
        snapshot = gwrl_cpp.campaign_pass_snapshot("pass:海軍", "pass_interrupt", "axis")
        native = compiler.compile(snapshot)
        legacy = compile_graph_python(snapshot.to_python(), 128)
        self.assertEqual(graph_digest(native, 128), graph_digest(legacy, 128))
        self.assertNotEqual(graph_digest(native, 128), graph_digest(legacy, 64))

    def test_comparison_requires_explicit_search_and_wrapper_fingerprints(self):
        fields = ("config", "run_config", "initial_model_versions", "training_environment_seeds", "task",
                  "updates", "adam_step_calls", "logical_core", "replay_feature_graphs", "logical_checkpoint_sha256")
        incomplete = {key: "same" for key in fields}
        incomplete.update(status="completed", training_wall_seconds=2.)
        self.assertFalse(compare_reports(incomplete, incomplete)["matched"])
        complete = {**incomplete, "search": {"count": 4, "sha256": "same"},
                    "provenance": {"wrapper_sha256": "same"}}
        faster = {**complete, "training_wall_seconds": 1.}
        comparison = compare_reports(faster, complete)
        self.assertTrue(comparison["matched"])
        self.assertEqual(comparison["training_speedup_if_matched"], 2.)
        changed = {**faster, "logical_core": "different"}
        self.assertFalse(compare_reports(changed, complete)["matched"])
        self.assertIsNone(compare_reports(changed, complete)["training_speedup_if_matched"])

    def test_restored_native_replay_checks_all_fields_and_detects_changed_numeric_bits(self):
        import numpy as np

        compiler = gwrl_cpp.CampaignNumericGraphCompiler(128, lexical_ids, _string_descriptor, _numeric_features)
        graph = compiler.compile(gwrl_cpp.campaign_pass_snapshot("pass", "pass_interrupt", "axis"))
        restored = gwrl_cpp.CampaignNumericGraph.from_packed(graph.packed_state())
        packed = {"context": graph, "observation": graph, "actions": (graph,),
                  "action_factors": (("kind", "source", "path", "target"),)}
        first = [{"input": {"schema": "campaign-numeric-input-v1", "owner": "axis", "context_key": "same",
                             "packed_graph": packed}}]
        second = copy.deepcopy(first)
        second[0]["input"]["packed_graph"] = {**packed, "context": restored, "observation": restored,
                                                "actions": (restored,)}
        self.assertTrue(replay_features_equal(first, second))
        state = graph.packed_state()
        state["numeric"] = np.array(state["numeric"], copy=True)
        state["numeric"][0, 0] = -0.
        changed = gwrl_cpp.CampaignNumericGraph.from_packed(state)
        self.assertFalse(replay_features_equal(first, [{"input": {**second[0]["input"],
            "packed_graph": {**second[0]["input"]["packed_graph"], "observation": changed}}}]))
        for field, value in (("context", changed), ("actions", (changed,)),
                             ("action_factors", (("changed", "source", "path", "target"),))):
            with self.subTest(field=field):
                altered = {**second[0]["input"], "packed_graph": {**second[0]["input"]["packed_graph"], field: value}}
                self.assertFalse(replay_features_equal(first, [{"input": altered}]))
        for field, value in (("owner", "allies"), ("context_key", "changed"), ("schema", "future")):
            with self.subTest(field=field):
                self.assertFalse(replay_features_equal(first, [{"input": {**second[0]["input"], field: value}}]))
        self.assertFalse(replay_features_equal(first, []))

    def test_restored_legacy_replay_checks_context_once_per_pair_and_keeps_signed_zero(self):
        from studies.campaign import features

        context = {"fixed": "蒙古"}
        first = [{"input": {"schema": "campaign-neural-input-v1", "context": context,
                             "observation": {"number": -0.}, "actions": [{"id": "one"}]}},
                 {"input": {"schema": "campaign-neural-input-v1", "context": context,
                             "observation": {"number": 2.}, "actions": [{"id": "two"}]}}]
        second = copy.deepcopy(first)
        original = features.canonical
        context_calls = []

        def canonical(value):
            if value is context or value is second[0]["input"]["context"]:
                context_calls.append(value)
            return original(value)

        with mock.patch.object(features, "canonical", side_effect=canonical):
            self.assertTrue(replay_features_equal(first, second))
        self.assertEqual(len(context_calls), 2)
        second[1]["input"]["actions"][0]["id"] = "changed"
        self.assertFalse(replay_features_equal(first, second))
        second = copy.deepcopy(first)
        second[0]["input"]["observation"]["number"] = 0.
        self.assertFalse(replay_features_equal(first, second))


if __name__ == "__main__":
    unittest.main()
