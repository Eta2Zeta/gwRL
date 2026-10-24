"""Static context transport must avoid work without sharing mutable state."""
from __future__ import annotations

import copy
import json
import pickle
import unittest

from studies.shared.campaign_adapter import CampaignAdapter, ScheduledAction
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


class DecisionRaw(ContextRaw):
    """Small counted rule API with choices, offers and a chance transition."""
    def __init__(self, *, offers=(), phase="choose", state=0):
        super().__init__(state=state)
        self.offers = list(offers)
        self.phase = phase
        self.rule_version = "rules-v1"
        self.calls = {"legal_actions": 0, "legal_interrupts": 0, "observation": 0}
        self.applied = None
        self.draws = 0

    def current_decision_player(self):
        return None if self.phase == "chance" else "axis"

    def decision_kind(self):
        return self.phase

    def _action(self):
        return {"id": f"choose-{self.state}", "player": "axis", "kind": "choose",
                "parameters": {"step": self.state, "retained": ["蒙古", {"opaque": True}]}}

    def legal_actions(self):
        self.calls["legal_actions"] += 1
        return [] if self.phase == "chance" else [self._action()]

    def legal_interrupts(self):
        self.calls["legal_interrupts"] += 1
        return [{"id": f"declare-{player}", "player": player, "kind": "declare",
                 "parameters": {"retained": [self.state]}} for player in self.offers]

    def observation(self):
        self.calls["observation"] += 1
        return {"current_decision_player": self.current_decision_player(), "decision_kind": self.phase,
                "state": {"step": self.state, "pending": {"opaque": [1, 2, 3]}},
                "unknown_future_field": {"retained": [False, None, "蒙古"]},
                "legal_actions": [] if self.phase == "chance" else [self._action()]}

    def apply_action(self, action):
        self.applied = copy.deepcopy(dict(action))
        if action != self._action():
            raise ValueError("Illegal raw choice")
        self.state += 1

    def apply_interrupt(self, action):
        self.applied = copy.deepcopy(dict(action))
        if action["player"] not in self.offers:
            raise ValueError("Illegal raw declaration")
        self.offers.remove(action["player"])
        self.phase = "priority"
        self.state += 1

    def resolve_chance(self):
        if self.phase != "chance":
            raise ValueError("No chance pending")
        self.draws += 1
        self.state += 1
        self.phase = "choose"

    def planning_key(self):
        return json.dumps([self.state, self.phase, self.offers, self.rule_version])

    def clone(self):
        result = copy.deepcopy(self)
        result.calls = dict.fromkeys(self.calls, 0)
        return result

    def serialize(self):
        return json.dumps({"state": self.state, "phase": self.phase, "offers": self.offers,
                           "rules": self.rule_version, "draws": self.draws})

    def restore(self, serialized):
        value = json.loads(serialized)
        self.state, self.phase, self.offers = value["state"], value["phase"], value["offers"]
        self.rule_version, self.draws = value["rules"], value["draws"]


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


class CampaignDecisionReuseTests(unittest.TestCase):
    def test_unchanged_selection_observation_and_apply_build_each_raw_source_once(self):
        env = CampaignAdapter(DecisionRaw())
        first = env.legal_actions()
        expected = first[0].features()
        snapshot = env.neural_observation()
        for _ in range(4):
            self.assertEqual(env.current_decision_player(), "axis")
            self.assertEqual(env.decision_kind(), "choose")
            self.assertEqual(env.legal_actions()[0].features(), expected)
            self.assertIs(env.neural_observation(), snapshot)
            self.assertEqual(env.observation(), snapshot)
        self.assertEqual(env.raw.calls, {"legal_actions": 1, "legal_interrupts": 0, "observation": 1})
        self.assertEqual(snapshot["unknown_future_field"], {"retained": [False, None, "蒙古"]})
        env.apply_action(first[0])
        self.assertEqual(env.raw.calls, {"legal_actions": 1, "legal_interrupts": 0, "observation": 1})
        self.assertEqual(env.raw.applied, expected["action"])
        self.assertEqual(env.neural_observation()["state"]["step"], 1)
        self.assertEqual(env.raw.calls, {"legal_actions": 2, "legal_interrupts": 0, "observation": 2})

    def test_public_payloads_cannot_poison_canonical_actions_or_neural_observation(self):
        env = CampaignAdapter(DecisionRaw())
        action = env.legal_actions()[0]
        snapshot = env.neural_observation()
        public = env.observation()
        public["state"]["pending"]["opaque"].append("poison")
        public["legal_actions"][0]["action"]["parameters"]["step"] = -1
        feature = action.features()
        feature["action"]["parameters"]["retained"].clear()
        env.legal_actions().clear()
        with self.assertRaises(TypeError):
            action.raw["parameters"]["step"] = -1
        with self.assertRaises(TypeError):
            action.neural_features()["action"]["parameters"]["retained"].append("poison")
        self.assertIs(snapshot, env.neural_observation())
        self.assertEqual(env.observation()["state"]["pending"]["opaque"], [1, 2, 3])
        self.assertEqual(action.features()["action"]["parameters"]["retained"], ["蒙古", {"opaque": True}])
        forged = ScheduledAction(action.id, action.kind, action.player,
                                 {"id": "forged", "parameters": {"step": -1}})
        env.apply_action(forged)
        self.assertEqual(env.raw.applied["id"], "choose-0")
        self.assertEqual(env.raw.applied["parameters"]["step"], 0)

    def test_passing_offers_changes_scheduled_cache_without_rebuilding_raw_sources(self):
        env = CampaignAdapter(DecisionRaw(offers=("allies", "comintern"), phase="production"))
        raw_key = env.raw.planning_key()
        first_key = env.planning_key()
        first = env.neural_observation()
        self.assertEqual(first["current_decision_player"], "allies")
        for player in ("allies", "comintern"):
            self.assertEqual(env.current_decision_player(), player)
            env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))
            current = env.neural_observation()
            self.assertIsNot(current, first)
            self.assertEqual(env.raw.planning_key(), raw_key)
            self.assertNotEqual(env.planning_key(), first_key)
        self.assertEqual(current["current_decision_player"], "axis")
        self.assertEqual(current["decision_kind"], "production")
        self.assertEqual(current["interrupt_scheduler"]["passed"], ["allies", "comintern"])
        self.assertEqual(env.raw.calls, {"legal_actions": 1, "legal_interrupts": 1, "observation": 1})
        # Reordering offers changes the scheduled identity, even when the raw
        # board and already-passed actors are unchanged.
        env.interrupt_order = tuple(reversed(env.interrupt_order))
        reordered = env.neural_observation()
        self.assertIsNot(reordered, current)
        self.assertEqual(reordered["interrupt_scheduler"]["order"], list(env.interrupt_order))
        self.assertEqual(env.raw.calls["observation"], 1)

    def test_clones_share_snapshots_but_invalidate_independently_on_actions_and_offers(self):
        env = CampaignAdapter(DecisionRaw(offers=("allies", "comintern"), phase="production"))
        original = env.neural_observation()
        original_actions = env.legal_actions()
        for clone in (env.clone(), env.clone_for_search(71)):
            self.assertIs(clone.neural_observation(), original)
            self.assertIs(clone.legal_actions()[0], original_actions[0])
            self.assertEqual(clone.raw.calls, dict.fromkeys(clone.raw.calls, 0))
            clone.apply_action(next(action for action in clone.legal_actions() if action.kind == "pass_interrupt"))
            self.assertEqual(clone.current_decision_player(), "comintern")
            self.assertEqual(env.current_decision_player(), "allies")
            self.assertIsNot(clone.neural_observation(), original)
            clone.apply_action(next(action for action in clone.legal_actions() if action.kind == "interrupt"))
            self.assertEqual(clone.neural_observation()["state"]["step"], 1)
            self.assertEqual(env.neural_observation()["state"]["step"], 0)
            self.assertEqual(clone.raw.calls["observation"], 1)
        self.assertIs(env.neural_observation(), original)
        self.assertEqual(env.raw.calls["observation"], 1)

    def test_chance_and_external_raw_changes_invalidate_complete_decision(self):
        env = CampaignAdapter(DecisionRaw(phase="chance"))
        chance = env.neural_observation()
        self.assertEqual(chance["legal_actions"], [])
        self.assertEqual(env.raw.draws, 0)
        clone = env.clone_for_search(99)
        self.assertIs(clone.neural_observation(), chance)
        clone.resolve_chance()
        self.assertEqual(clone.raw.draws, 1)
        self.assertEqual(env.raw.draws, 0)
        self.assertEqual(clone.neural_observation()["state"]["step"], 1)
        env.resolve_chance()
        selected = env.legal_actions()[0]
        normal = env.neural_observation()
        env.raw.state += 1
        with self.assertRaises(ValueError):
            env.apply_action(selected)
        self.assertIsNot(env.neural_observation(), normal)
        self.assertEqual(env.neural_observation()["state"]["step"], 2)
        # A rules change is also part of the raw API's complete planning key.
        current = env.neural_observation()
        env.raw.rule_version = "rules-v2"
        self.assertIsNot(env.neural_observation(), current)

    def test_successful_restore_replaces_cache_and_rejected_restore_preserves_it(self):
        env = CampaignAdapter(DecisionRaw(offers=("allies", "comintern"), phase="production"))
        checkpoint = env.serialize()
        first = env.neural_observation()
        env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))
        changed = env.neural_observation()
        invalid = json.loads(checkpoint)
        invalid["passed"] = ["allies", "allies"]
        with self.assertRaises(ValueError):
            env.restore(json.dumps(invalid))
        self.assertIs(env.neural_observation(), changed)
        env.restore(checkpoint)
        restored = env.neural_observation()
        self.assertEqual(restored, first)
        self.assertIsNot(restored, changed)
        self.assertEqual(env.current_decision_player(), "allies")
        self.assertEqual(env.serialize(), checkpoint)


if __name__ == "__main__":
    unittest.main()
