"""Static context transport must avoid work without sharing mutable state."""
from __future__ import annotations

import copy
import json
import pickle
import unittest

from studies.shared.campaign_adapter import CampaignAdapter
from studies.shared.immutable_json import FrozenDict, FrozenList, freeze_json


class ContextRaw:
    def __init__(self, definition=None, state=0):
        self.definition = copy.deepcopy(definition if definition is not None else {
            "players": ["axis", "allies", "comintern"],
            "opaque_registry": {"entries": [{"id": "retained", "label": "蒙古", "extra": [1, 2, 3]}]},
        })
        self.state = state
        self.context_calls = 0

    def context(self):
        self.context_calls += 1
        return copy.deepcopy(self.definition)

    def current_decision_player(self):
        return "axis"

    def decision_kind(self):
        return "choose"

    def is_terminal(self):
        return False

    def legal_actions(self):
        return [{"id": "choose", "player": "axis", "kind": "choose", "parameters": {"step": self.state}}]

    def observation(self):
        return {"current_decision_player": "axis", "decision_kind": "choose", "state": {"step": self.state}}

    def planning_key(self):
        return str(self.state)

    def clone(self):
        return ContextRaw(self.definition, self.state)

    def clone_for_search(self, seed):
        return self.clone()

    def serialize(self):
        return json.dumps({"state": self.state, "definition": self.definition})

    def restore(self, serialized):
        value = json.loads(serialized)
        self.state, self.definition = value["state"], value["definition"]


class CampaignContextTransportTests(unittest.TestCase):
    def test_neural_context_translates_once_and_clones_share_definition(self):
        env = CampaignAdapter(ContextRaw())
        self.assertEqual(env.raw.context_calls, 0)
        context = env.neural_context()
        self.assertIs(context, env.neural_context())
        self.assertEqual(env.raw.context_calls, 1)
        for clone in (env.clone(), env.clone_for_search(23)):
            self.assertIs(clone.neural_context(), context)
            self.assertEqual(clone.raw.context_calls, 0)
            clone.raw.state = 1
            self.assertIs(clone.neural_context(), context)
            self.assertEqual(env.raw.state, 0)
        self.assertEqual(json.loads(env.neural_context_key()), env.context())
        self.assertEqual(env.raw.context_calls, 1)

    def test_public_context_returns_fresh_mutable_detached_json(self):
        env = CampaignAdapter(ContextRaw())
        first, second = env.context(), env.context()
        self.assertIs(type(first), dict)
        self.assertIs(type(first["players"]), list)
        self.assertEqual(first, second)
        first["opaque_registry"]["entries"][0]["label"] = "caller changed"
        first["players"].append("caller alliance")
        first["interrupt_scheduler"]["order"].reverse()
        self.assertEqual(second, env.context())
        self.assertEqual(env.neural_context()["opaque_registry"]["entries"][0]["label"], "蒙古")
        self.assertEqual(env.raw.context_calls, 1)

    def test_neural_input_and_inference_share_complete_immutable_context_across_clones(self):
        import torch
        from studies.campaign.features import canonical, make_input
        from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet

        env = CampaignAdapter(ContextRaw())
        expected = copy.deepcopy(env.raw.definition)
        expected["interrupt_scheduler"] = {"schema": "campaign-interrupt-scheduler-v1",
                                           "order": ["axis", "allies", "comintern"]}
        original = make_input(env, env.legal_actions())
        context = original["context"]
        self.assertEqual(context, expected)
        self.assertIs(context, env.neural_context())
        self.assertIs(canonical(context), context.canonical_json)
        clones = [env.clone(), env.clone_for_search(23)]
        inputs = [original, *(make_input(clone, clone.legal_actions()) for clone in clones)]
        self.assertTrue(all(item["context"] is context for item in inputs))
        self.assertEqual(json.loads(json.dumps(original))["context"], expected)
        with self.assertRaises(TypeError):
            context["opaque_registry"]["entries"][0]["extra"].append(4)

        previous_threads = torch.get_num_threads()
        try:
            torch.set_num_threads(1)
            model = CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=8, message_layers=1, token_buckets=64))
            with torch.inference_mode():
                logits, values = model.forward_batch(inputs)
            self.assertEqual(tuple(values.shape), (3, 3))
            self.assertEqual([tuple(row.shape) for row in logits], [(1,), (1,), (1,)])
            # Cached source tensors first created under inference must still
            # permit a subsequent optimizer update and fresh learned outputs.
            optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
            train_logits, train_values = model.forward_batch(inputs)
            loss = train_values.square().sum() + sum(row.square().sum() for row in train_logits)
            loss.backward()
            optimizer.step()
            with torch.inference_mode():
                _, updated = model.forward_batch(inputs)
            self.assertFalse(torch.equal(values, updated))
        finally:
            torch.set_num_threads(previous_threads)

        self.assertEqual(env.raw.context_calls, 1)
        self.assertEqual([clone.raw.context_calls for clone in clones], [0, 0])
        env.raw.state = 2
        later = make_input(env, env.legal_actions())
        self.assertIs(later["context"], context)
        self.assertEqual(original["observation"]["state"]["step"], 0)
        self.assertEqual(later["observation"]["state"]["step"], 2)
        self.assertEqual(env.raw.context_calls, 1)

    def test_restore_invalidates_cache_including_scheduler_order(self):
        env = CampaignAdapter(ContextRaw())
        previous = env.neural_context()
        checkpoint = json.loads(env.serialize())
        checkpoint["order"].reverse()
        raw = json.loads(checkpoint["raw"])
        raw["definition"]["opaque_registry"]["entries"][0]["extra"].append(4)
        checkpoint["raw"] = json.dumps(raw)
        env.restore(json.dumps(checkpoint))
        current = env.neural_context()
        self.assertIsNot(current, previous)
        self.assertEqual(current["interrupt_scheduler"]["order"], checkpoint["order"])
        self.assertEqual(current["opaque_registry"]["entries"][0]["extra"], [1, 2, 3, 4])
        self.assertEqual(previous["opaque_registry"]["entries"][0]["extra"], [1, 2, 3])

    def test_rejected_restore_preserves_cached_snapshot(self):
        env = CampaignAdapter(ContextRaw())
        previous = env.neural_context()
        checkpoint = json.loads(env.serialize())
        checkpoint["passed"] = ["axis", "axis"]
        with self.assertRaises(ValueError):
            env.restore(json.dumps(checkpoint))
        self.assertIs(env.neural_context(), previous)
        self.assertEqual(env.raw.context_calls, 1)

    def test_frozen_snapshot_detaches_nested_values_and_roundtrips(self):
        original = {"entries": [{"label": "蒙古", "values": [1, 2]}]}
        snapshot = freeze_json(original)
        self.assertIsInstance(snapshot, FrozenDict)
        self.assertIsInstance(snapshot["entries"], FrozenList)
        expected = json.dumps(original, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        self.assertEqual(snapshot.canonical_json, expected)
        self.assertIs(snapshot.canonical_json, snapshot.canonical_json)
        original["entries"][0]["values"].append(3)
        self.assertEqual(snapshot["entries"][0]["values"], [1, 2])
        self.assertIs(copy.deepcopy(snapshot), snapshot)
        restored = pickle.loads(pickle.dumps([snapshot, snapshot]))
        self.assertIs(restored[0], restored[1])
        self.assertEqual(restored[0].canonical_json, expected)
        self.assertIsInstance(restored[0]["entries"], FrozenList)

    def test_frozen_containers_reject_mutation_at_every_depth(self):
        snapshot = freeze_json({"entries": [{"label": "retained"}]})
        def replace_field():
            snapshot["extra"] = True
        def delete_field():
            del snapshot["entries"][0]["label"]
        def replace_slice():
            snapshot["entries"][:] = []
        def replace_cached_text():
            snapshot.canonical_json = "corrupted"
        mutations = [replace_field, delete_field, replace_slice, replace_cached_text,
                     lambda: snapshot.update({"extra": True}),
                     lambda: snapshot["entries"].append({}),
                     lambda: snapshot["entries"][0].clear(),
                     lambda: snapshot.__init__({}),
                     lambda: snapshot["entries"].__init__([])]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(TypeError):
                mutation()


if __name__ == "__main__":
    unittest.main()
