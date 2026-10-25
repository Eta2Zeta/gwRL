"""Matched-pilot fingerprints compare logical data, preserving numerical bits."""
from __future__ import annotations

import copy
import unittest

import gwrl_cpp

from studies.campaign.features import (_numeric_features, _string_descriptor,
                                      compile_graph_python, lexical_ids)
from tools.benchmark_campaign_numeric_learning import compare_reports, graph_digest, tree_digest


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


if __name__ == "__main__":
    unittest.main()
