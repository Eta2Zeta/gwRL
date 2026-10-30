"""The full campaign API exposes each real choice and sampled chance separately."""

from __future__ import annotations

import json
from pathlib import Path
import random
import unittest

import gwrl_cpp


SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"


def end_phase(env):
    env.apply_action(next(a for a in env.legal_actions() if a.kind == "end_phase"))


def play_search_copy_beside_ordinary_copy(test, seed, rounds):
    """Play one random complete game on a search copy and on an ordinary engine, comparing every step."""
    in_place = gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO), rounds, seed, training_actions=True).clone_for_search(seed)
    copying = in_place.clone()
    choice = random.Random(f"search-copy:{seed}")
    steps = 0
    while True:
        steps += 1
        test.assertEqual(in_place.planning_key(), copying.planning_key())
        test.assertEqual(in_place.serialize(), copying.serialize())
        if in_place.is_terminal():
            test.assertTrue(copying.is_terminal())
            return steps
        if in_place.decision_kind() == "chance":
            in_place.resolve_chance()
            copying.resolve_chance()
            continue
        actions, interrupts = in_place.legal_actions(), in_place.legal_interrupts()
        test.assertEqual([action.describe() for action in actions], [action.describe() for action in copying.legal_actions()])
        test.assertEqual([action.describe() for action in interrupts],
                         [action.describe() for action in copying.legal_interrupts()])
        if interrupts and choice.random() < 0.02:
            action = choice.choice(interrupts)
            in_place.apply_interrupt(action)
            copying.apply_interrupt(action)
            continue
        ending = [action for action in actions if action.kind == "end_phase"]
        action = ending[0] if ending and choice.random() < 0.05 else choice.choice(actions)
        in_place.apply_action(action)
        copying.apply_action(action)


def env_with_unhandled_decision(seed):
    """A saved game whose pending decision lists an option the rules accept, then fail on."""
    env = gwrl_cpp.CampaignEnv(str(SCENARIO), seed)
    saved = json.loads(env.serialize())
    decision = "unhandled_decision"
    option = {"id": "unhandled", "kind": "unhandled", "player": "allies", "nation": "kmt",
              "decision": decision, "parameters": {}}
    saved["state"]["decisions"].append({"id": decision, "kind": "unhandled_reaction", "nation": "kmt", "reaction": True,
                                        "continuation": "unhandled", "options": [option]})
    env.restore(json.dumps(saved, sort_keys=True, separators=(",", ":")))
    return env


class CampaignEnvironmentTests(unittest.TestCase):
    def test_past_event_inspection_is_detached_and_does_not_reveal_future_dice(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 11)
        initial = env.serialize()
        self.assertEqual(env.history_size(), 0)
        self.assertEqual(env.history_since(0), [])
        self.assertEqual(env.serialize(), initial)
        for _ in range(4):
            end_phase(env)
        env.apply_action(next(a for a in env.legal_actions() if a.kind == "recruitment_roll"))
        cursor = env.history_size()
        pending = env.serialize()
        self.assertEqual(env.decision_kind(), "chance")
        self.assertEqual(env.history_since(cursor), [])
        self.assertEqual(env.serialize(), pending)
        env.resolve_chance()
        checkpoint = env.serialize()
        events = env.history_since(cursor)
        self.assertEqual(events, json.loads(checkpoint)["state"]["history"][cursor:])
        self.assertTrue(any(event["kind"] == "chance" and "outcome" in event["payload"] for event in events))
        self.assertTrue(all(set(event) == {"kind", "payload", "after_state_key"} for event in events))
        events[0]["payload"]["caller_only"] = True
        self.assertNotEqual(events, env.history_since(cursor))
        self.assertEqual(env.serialize(), checkpoint)
        with self.assertRaises((IndexError, RuntimeError)):
            env.history_since(env.history_size() + 1)
        self.assertEqual(env.serialize(), checkpoint)

    def test_graph_registry_and_complete_dynamic_entities(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 91)
        observation, context = env.observation(), env.context()
        self.assertEqual(gwrl_cpp.CAMPAIGN_SCHEMA, "campaign_entities_v1")
        self.assertEqual(context["players"], ["axis", "allies", "comintern"])
        self.assertEqual(len(context["geography"]["nodes"]), 37)
        self.assertEqual(len(observation["state"]["units"]), 99)
        self.assertEqual(len(context["catalog"]), 5)
        self.assertEqual(env.current_decision_player(), "comintern")
        self.assertEqual(observation["current_decision_player"], "comintern")
        self.assertNotIn("random", observation)
        self.assertNotIn("history", observation["state"])
        self.assertNotIn("definition_fingerprint", observation["state"])
        self.assertEqual(env.returns(), [0.0, 0.0, 0.0])

    def test_exact_clone_and_search_do_not_read_future_actual_dice(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 91)
        checkpoint = env.serialize()
        clone = env.clone()
        self.assertEqual(clone.serialize(), checkpoint)
        end_phase(clone)
        self.assertEqual(env.serialize(), checkpoint)
        self.assertNotEqual(clone.planning_key(), env.planning_key())
        clone.restore(checkpoint)
        self.assertEqual(clone.serialize(), checkpoint)
        search = env.clone_for_search(500)
        self.assertEqual(search.observation(), env.observation())
        self.assertEqual(search.planning_key(), env.planning_key())
        self.assertNotEqual(search.serialize(), env.serialize())

    def test_search_copies_play_complete_games_exactly_like_ordinary_engines(self):
        for seed in (61, 62, 63):
            with self.subTest(seed=seed):
                self.assertGreater(play_search_copy_beside_ordinary_copy(self, seed, 2), 100)

    def test_search_copy_that_fails_mid_move_refuses_every_later_call(self):
        env = env_with_unhandled_decision(71)
        checkpoint, key, observation = env.serialize(), env.planning_key(), env.observation()
        search = env.clone_for_search(5)
        option = search.legal_actions()[0]
        ordinary = env.clone()
        with self.assertRaises(RuntimeError):
            ordinary.apply_action(option)
        self.assertEqual(ordinary.serialize(), checkpoint)
        with self.assertRaises(RuntimeError):
            search.apply_action(option)
        calls = {"is_terminal": (), "current_decision_player": (), "current_nation": (), "decision_kind": (),
                 "legal_actions": (), "legal_interrupts": (), "apply_action": (option,), "apply_interrupt": (option,),
                 "resolve_chance": (), "chance_request": (), "apply_chance_outcome": (key, ()), "returns": (),
                 "wealth": (), "observation": (), "numeric_observation": (), "numeric_context": (), "context": (),
                 "clone": (), "clone_for_search": (1,), "planning_key": (), "landing_plan_reachable": (),
                 "landing_shortfall": (), "serialize": (), "history_size": (), "history_since": (0,),
                 "restore": (checkpoint,)}
        for name, arguments in calls.items():
            with self.subTest(call=name), self.assertRaisesRegex(RuntimeError, "Search copy failed"):
                getattr(search, name)(*arguments)
        self.assertEqual((env.serialize(), env.planning_key(), env.observation()), (checkpoint, key, observation))
        self.assertEqual(env.clone_for_search(6).planning_key(), key)

    def test_rejected_actions_leave_a_search_copy_usable(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 72)
        other = gwrl_cpp.CampaignEnv(str(SCENARIO), 72)
        end_phase(other)
        stale = other.legal_actions()[0]
        search = env.clone_for_search(5)
        before = search.serialize()
        with self.assertRaises(RuntimeError):
            search.apply_action(stale)
        with self.assertRaises(RuntimeError):
            search.resolve_chance()
        self.assertEqual(search.serialize(), before)
        end_phase(search)
        self.assertEqual(search.planning_key(), other.planning_key())

    def test_recruitment_is_a_chance_node_and_does_not_advance_the_turn(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 11)
        for _ in range(4):
            end_phase(env)
        self.assertEqual(env.decision_kind(), "place_units")
        recruit = next(a for a in env.legal_actions() if a.kind == "recruitment_roll")
        env.apply_action(recruit)
        self.assertEqual(env.decision_kind(), "chance")
        self.assertIsNone(env.current_decision_player())
        self.assertEqual(env.legal_actions(), [])
        self.assertEqual(env.legal_interrupts(), [])
        self.assertEqual(env.current_nation(), "ccp")
        checkpoint = env.serialize()
        clone = env.clone()
        env.resolve_chance()
        clone.resolve_chance()
        self.assertEqual(clone.serialize(), env.serialize())
        self.assertEqual(env.current_nation(), "ccp")
        self.assertEqual(env.current_decision_player(), "comintern")
        # Independent simulated dice cannot consume the actual stream.
        reference = gwrl_cpp.CampaignEnv(str(SCENARIO), 22)
        reference.restore(checkpoint)
        simulated = reference.clone_for_search(999)
        simulated.resolve_chance()
        reference.resolve_chance()
        self.assertEqual(reference.serialize(), env.serialize())

    def test_terminal_wealth_is_an_ordered_general_sum_vector(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 3)
        state = json.loads(env.serialize())
        clock = state["state"]["clock"]
        clock.update(round_index=10, nation_index=3, completed_rounds=11,
                     phase="place_units", income_collected=True,
                     player_turn_serial="44")
        state["state"]["completed_turns"] = {n: 11 for n in ("ccp", "mongolia", "japan", "kmt")}
        state["state"]["terminal"] = True
        env.restore(json.dumps(state))
        self.assertTrue(env.is_terminal())
        self.assertEqual(env.decision_kind(), "terminal")
        self.assertIsNone(env.current_decision_player())
        self.assertEqual(env.legal_actions(), [])
        wealth = env.wealth()
        values = [wealth[p]["wealth"] for p in ("axis", "allies", "comintern")]
        for i, result in enumerate(env.returns()):
            self.assertAlmostEqual(result, 2 * values[i] - sum(values))
        self.assertAlmostEqual(sum(env.returns()), -sum(values))
        self.assertEqual(wealth["axis"]["paid_construction"], 10)

    def test_mismatched_definition_is_rejected_transactionally(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 3)
        checkpoint = env.serialize()
        bad = json.loads(checkpoint)
        bad["state"]["definition_fingerprint"] = "another-rules-profile"
        with self.assertRaises(RuntimeError):
            env.restore(json.dumps(bad))
        self.assertEqual(env.serialize(), checkpoint)

    def test_stochastic_vector_search_uses_the_actual_campaign_adapter(self):
        from studies.shared.campaign_adapter import CampaignAdapter
        from studies.shared.multiplayer_mcts import MctsConfig, VectorMCTS

        env = CampaignAdapter(gwrl_cpp.CampaignEnv(str(SCENARIO), 17))
        checkpoint = env.serialize()
        result = VectorMCTS(config=MctsConfig(simulations=4, max_depth=4, seed=7)).search(env)
        self.assertEqual(env.serialize(), checkpoint)
        self.assertEqual(sum(result.visit_counts), 4)
        self.assertEqual(len(result.values), 3)
        chosen = result.best_action()
        self.assertEqual(chosen.player, env.current_decision_player())
        env.apply_action(chosen)
        self.assertNotEqual(env.planning_key(), result.root.state_key)
        clone = env.clone()
        clone.restore(env.serialize())
        self.assertEqual(clone.serialize(), env.serialize())


if __name__ == "__main__":
    unittest.main()
