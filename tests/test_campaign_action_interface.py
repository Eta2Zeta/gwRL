"""Versioned AI order construction, complete public state and exact resume."""
from __future__ import annotations

import copy
import json
import unittest

import gwrl_cpp

from studies.campaign.curriculum import compatibility, make_env
from studies.campaign.replay import _recorded_env


def ship_fixture():
    env = make_env(1951, calendar_rounds=2)
    value = json.loads(env.raw.serialize())
    state = value["state"]
    state["clock"].update(nation_index=2, player_turn_serial="2", phase="combat_movement")
    state["completed_turns"] = {"ccp": 1, "mongolia": 1, "japan": 0, "kmt": 0}
    ships = [(key, unit) for key, unit in state["units"].items()
             if unit["owner"] == "japan" and unit["type"] == "destroyer"][:2]
    if len(ships) != 2:
        raise AssertionError("Fixture needs two initial Japanese destroyers")
    state["units"] = dict(ships)
    for unit in state["units"].values():
        unit.update(zone="sea_p16", turn_origin="sea_p16", cargo=[], carried_by=None,
                    route=[], commitments=[], turn_flags={}, game_flags={})
    env.raw.restore(json.dumps(value))
    return env


class CampaignActionInterfaceTests(unittest.TestCase):
    def test_new_profile_is_explicit_and_old_recordings_keep_their_profile(self):
        current = make_env(9, calendar_rounds=1)
        legacy = make_env(9, calendar_rounds=1, training_actions=False)
        schema = gwrl_cpp.CAMPAIGN_ACTION_SCHEMA
        self.assertEqual(current.context()["action_interface"], schema)
        self.assertEqual(compatibility(current)["actions"], schema)
        self.assertNotIn("actions", compatibility(legacy))
        self.assertNotIn("action_interface", legacy.context())
        self.assertNotEqual(json.loads(current.raw.serialize())["rules_id"],
                            json.loads(legacy.raw.serialize())["rules_id"])
        task = {"compatibility": compatibility(current)}
        self.assertEqual(_recorded_env(9, 1, task).serialize(), current.serialize())
        self.assertEqual(_recorded_env(9, 1, {"compatibility": compatibility(legacy)}).serialize(),
                         legacy.serialize())
        with self.assertRaisesRegex(ValueError, "Unsupported recorded action interface"):
            _recorded_env(9, 1, {"compatibility": {"actions": "unknown"}})
        before = current.serialize()
        with self.assertRaises(RuntimeError):
            current.restore(legacy.serialize())
        self.assertEqual(current.serialize(), before)

    def test_pending_order_clone_restore_cache_and_real_execution_match(self):
        env = ship_fixture()
        initial = env.serialize()
        # Resolve observable declaration offers without making any declaration.
        while env.decision_kind() == "declaration_offer":
            env.apply_action(next(a for a in env.legal_actions() if a.kind == "pass_interrupt"))
        moves = [a for a in env.legal_actions() if a.raw["kind"] == "naval_start_move"]
        chosen = min(moves, key=lambda a: a.raw["parameters"]["unit"])
        env.apply_action(chosen)
        self.assertEqual(env.decision_kind(), "naval_force_selection")
        self.assertNotEqual(env.serialize(), initial)
        menu = env.legal_actions()
        self.assertFalse({"naval_cancel_move", "naval_force_remove"} & {a.raw["kind"] for a in menu})
        frozen = env.neural_observation()
        exact, searched = env.clone(), env.clone_for_search(1809)
        self.assertEqual(exact.serialize(), env.serialize())
        self.assertEqual(searched.planning_key(), env.planning_key())
        self.assertEqual(searched.observation(), env.observation())
        self.assertIs(exact.neural_observation(), frozen)
        saved = env.serialize()
        restored = ship_fixture()
        restored.restore(saved)
        self.assertEqual(restored.serialize(), saved)
        self.assertEqual(restored.observation(), env.observation())
        add = next(a for a in menu if a.raw["kind"] == "naval_force_add")
        env.apply_action(add)
        restored.apply_action(next(a for a in restored.legal_actions() if a.id == add.id))
        self.assertEqual(restored.serialize(), env.serialize())
        self.assertEqual(exact.serialize(), saved)
        self.assertIsNot(env.neural_observation(), frozen)
        after_add = env.serialize()
        with self.assertRaises(ValueError):
            env.apply_action(add)
        self.assertEqual(env.serialize(), after_add)
        route = next(a for a in env.legal_actions() if a.raw["kind"] == "naval_route")
        env.apply_action(route)
        restored.apply_action(next(a for a in restored.legal_actions() if a.id == route.id))
        self.assertEqual(restored.serialize(), env.serialize())
        self.assertNotEqual(env.serialize(), after_add)

    def test_invalid_action_interface_restore_is_transactional(self):
        env = make_env(4)
        original = env.serialize()
        for metadata in ([], {"schema": "unknown"}, {"visited_configurations": "bad"}):
            value = json.loads(env.raw.serialize())
            value["state"]["action_interface"] = copy.deepcopy(metadata)
            with self.assertRaises(RuntimeError):
                env.raw.restore(json.dumps(value))
            self.assertEqual(env.serialize(), original)


if __name__ == "__main__":
    unittest.main()
