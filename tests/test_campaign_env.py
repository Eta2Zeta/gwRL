"""The full campaign API exposes each real choice and sampled chance separately."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

import gwrl_cpp


SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"


def end_phase(env):
    env.apply_action(next(a for a in env.legal_actions() if a.kind == "end_phase"))


class CampaignEnvironmentTests(unittest.TestCase):
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
