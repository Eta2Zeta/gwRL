"""Historical JSON and new numerical rows preserve one registry and exact updates."""
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign import features, neural


def native_graph(value):
    graph = features.compile_graph(value, 128)
    edges = np.asarray(graph.edges, dtype=np.int64).reshape(-1, 3)
    return gwrl_cpp.CampaignNumericGraph.from_packed({
        "schema": "campaign-numeric-graph-v1", "buckets": 128,
        "token_ids": np.asarray(graph.token_ids, dtype=np.int64),
        "token_offsets": np.asarray(graph.token_offsets, dtype=np.int64),
        "types": np.asarray(graph.types, dtype=np.int64),
        "numeric": np.asarray(graph.numeric, dtype=np.float64),
        "sources": edges[:, 0], "targets": edges[:, 1], "relations": edges[:, 2],
        "identities": graph.identities, "references": graph.references, "leaf_count": graph.leaf_count})


def rows():
    context = {"geography": {"nodes": {
        "a": {"id": "a", "name": "海軍é", "neighbors": [{"neighbor_id": "b"}]},
        "b": {"id": "b", "neighbors": [{"neighbor_id": "a"}]}}},
        "catalog": {"units": [{"id": "infantry", "attack": 2}]}}
    result = []
    for index in range(3):
        actions = [{"id": f"choice-{index}-{target}", "kind": "play", "player": "axis",
                    "action": {"id": f"move-{target}", "kind": "move", "parameters": {
                        "unit": "u", "target": target, "path": ["a", target]}}} for target in ("a", "b")]
        result.append({"schema": features.SCHEMA, "context": context,
                       "observation": {"current_decision_player": "axis", "state": {
                           "units": {"u": {"id": "u", "type": "infantry", "zone": "a"}},
                           "clock": index, "flag": index % 2}}, "actions": actions})
    return result


def numerical(item):
    return {"schema": features.NUMERIC_SCHEMA, "owner": "axis",
            "context_key": features.context_source_key(features.canonical(item["context"])),
            "packed_graph": {"context": native_graph(item["context"]),
                             "observation": native_graph(item["observation"]),
                             "actions": tuple(native_graph(action) for action in item["actions"]),
                             "action_factors": tuple(features.action_factors(action) for action in item["actions"])}}


class MixedReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def assert_tree_equal(self, a, b):
        if isinstance(a, torch.Tensor):
            self.assertTrue(torch.equal(a, b))
        elif isinstance(a, dict):
            self.assertEqual(set(a), set(b))
            for key in a:
                self.assert_tree_equal(a[key], b[key])
        elif isinstance(a, (tuple, list)):
            self.assertEqual(len(a), len(b))
            for x, y in zip(a, b):
                self.assert_tree_equal(x, y)
        else:
            self.assertEqual(a, b)

    def train_once(self, base, inputs, expected_contexts):
        model = copy.deepcopy(base)
        optimizer = torch.optim.Adam(model.parameters(), lr=.001)
        with patch.object(model.encoder, "forward", wraps=model.encoder.forward) as calls:
            logits, values = model.forward_batch(inputs)
            self.assertEqual(len(calls.call_args_list[0].args[0]), expected_contexts)
        loss = values.square().sum() + sum(value.square().sum() for value in logits)
        loss.backward()
        gradients = {name: parameter.grad.detach().clone() for name, parameter in model.named_parameters()}
        optimizer.step()
        return ([value.detach() for value in logits], values.detach(), gradients,
                model.state_dict(), optimizer.state_dict())

    def test_frozen_legacy_context_is_fully_validated_once_across_replay_rows(self):
        import json
        from studies.campaign.learning import CampaignLearner
        from studies.shared.immutable_json import freeze_json

        raw = rows()[0]
        context = freeze_json(raw["context"])
        sample = {"input": {**raw, "context": context}, "owner": "axis", "policy": [.5, .5],
                  "rollout_version": "preserved-policy"}
        original, checked = json.dumps, []

        def dumps(value, **kwargs):
            if value is context:
                checked.append(value)
            return original(value, **kwargs)

        with patch("studies.shared.immutable_json.json.dumps", side_effect=dumps):
            CampaignLearner._validate_sample(sample, labeled=False)
            CampaignLearner._validate_sample(sample, labeled=False)
        self.assertEqual(len(checked), 1)
        invalid = {**sample, "input": {**raw, "context": freeze_json({"bad": float("nan")})}}
        with self.assertRaises(ValueError):
            CampaignLearner._validate_sample(invalid, labeled=False)

    def test_all_transport_orders_preserve_outputs_gradients_and_adam_with_one_context(self):
        raw = rows()
        packed = [numerical(item) for item in raw]
        for dtype in (torch.float32, torch.float64):
            with self.subTest(dtype=dtype):
                torch.manual_seed(1951)
                base = neural.CampaignPolicyValueNet(neural.CampaignModelConfig(
                    hidden_dim=8, message_layers=2, token_buckets=128)).to(dtype=dtype)
                expected = self.train_once(base, raw, 1)
                for inputs in (packed, [raw[0], packed[1], raw[2]], [packed[0], raw[1], packed[2]]):
                    # Mixed matching must use compact metadata, not a complete
                    # native-to-Python scalar graph conversion.
                    with patch.object(gwrl_cpp.CampaignNumericGraph, "debug_graph",
                                      side_effect=AssertionError("full scalar conversion")):
                        self.assert_tree_equal(expected, self.train_once(base, inputs, 1))

    def test_different_contexts_remain_distinct_in_mixed_batches(self):
        raw = rows()
        raw[2] = copy.deepcopy(raw[2])
        raw[2]["context"]["catalog"]["units"][0]["attack"] = 7
        torch.manual_seed(19)
        base = neural.CampaignPolicyValueNet(neural.CampaignModelConfig(
            hidden_dim=8, message_layers=1, token_buckets=128))
        expected = self.train_once(base, raw, 2)
        self.assert_tree_equal(expected, self.train_once(base, [numerical(raw[0]), raw[1], numerical(raw[2])], 2))


if __name__ == "__main__":
    unittest.main()
