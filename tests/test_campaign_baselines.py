import copy
import json
import random
import unittest
from collections import Counter

from studies.campaign.baselines import raw_action, scripted_policy
from studies.campaign.curriculum import make_env
from studies.shared.multiplayer_mcts import action_key, apply_fixed_opponent


class CampaignBaselineTests(unittest.TestCase):
    def test_all_three_sides_act_in_a_true_short_campaign(self):
        env = make_env(413, calendar_rounds=1)
        policy = scripted_policy()
        owners, kinds = set(), Counter()
        rng = random.Random(31)
        for _ in range(350):
            if env.is_terminal():
                break
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            owner = env.current_decision_player()
            owners.add(owner)
            actions = env.legal_actions()
            index = policy.sample(env, actions, rng)
            kinds[raw_action(actions[index])["kind"]] += 1
            env.apply_action(actions[index])
        self.assertTrue(env.is_terminal(), "Active baseline failed to complete its one-round fixture")
        self.assertEqual(owners, {"axis", "allies", "comintern"})
        self.assertIn("economy_purchase", kinds)
        self.assertIn("movement_route", kinds)
        self.assertIn("naval_route", kinds)
        self.assertEqual(kinds["naval_cancel_move"], 0, "Baseline repeatedly opened a force picker without a usable route")
        self.assertEqual(env.observation()["state"]["clock"]["completed_rounds"], 1)

    def test_force_edit_options_do_not_masquerade_as_a_complete_naval_move(self):
        class PlannerEnv:
            def __init__(self, *, route_available=False, stage="start", route=None):
                self.route_available, self.stage, self.route = route_available, stage, route or []

            def context(self):
                return {"catalog": {}, "geography": {"nodes": {}}}

            def observation(self):
                return {"state": {"units": {"ship": {"cargo": [], "route": self.route}},
                                  "territories": {}, "battles": {}}}

            def clone(self):
                return copy.deepcopy(self)

            def serialize(self):
                return json.dumps(vars(self), sort_keys=True)

            def apply_action(self, action):
                self.stage = "picker" if action["kind"] == "naval_start_move" else "expanded"

            def legal_actions(self):
                def action(kind, **parameters):
                    return {"id": kind, "kind": kind, "nation": "japan", "parameters": parameters}
                if self.stage == "start":
                    return [action("naval_start_move", unit="ship"), action("end_phase")]
                choices = [action("naval_force_add", unit="escort"), action("naval_force_remove", unit="ship"),
                           action("naval_cancel_move")]
                if self.route_available:
                    choices.append(action("naval_route", request={"path": ["sea_a", "sea_b"]}))
                return choices

        policy = scripted_policy()
        for route_available, expected in ((False, "end_phase"), (True, "naval_start_move")):
            env = PlannerEnv(route_available=route_available)
            before = env.serialize()
            for actions in (env.legal_actions(), list(reversed(env.legal_actions()))):
                chosen = actions[policy.sample(env, actions, random.Random(9))]
                self.assertEqual(chosen["kind"], expected)
                self.assertEqual(env.serialize(), before)
        stranded = PlannerEnv(stage="picker")
        actions = stranded.legal_actions()
        self.assertEqual(actions[policy.sample(stranded, actions, random.Random(9))]["kind"], "naval_cancel_move")
        moved = PlannerEnv(route_available=True, route=["sea_b"])
        actions = moved.legal_actions()
        self.assertEqual(actions[policy.sample(moved, actions, random.Random(9))]["kind"], "end_phase",
                         "Already-recorded movement should not invite a pointless repeat sortie")

    def test_fixed_opponent_sampler_and_search_policy_are_identical(self):
        env = make_env(17, calendar_rounds=1)
        policy = scripted_policy("cautious")
        before = env.serialize()
        actions = env.legal_actions()
        expected = actions[policy.sample(env, actions, random.Random(9))]
        self.assertEqual(env.serialize(), before)
        other = "axis" if env.current_decision_player() != "axis" else "allies"
        actual = apply_fixed_opponent(env, other, policy, random.Random(9))
        self.assertEqual(action_key(actual), action_key(expected))
        shuffled = list(reversed(actions))
        probe = make_env(17, calendar_rounds=1)
        self.assertEqual(action_key(actions[policy.sample(probe, actions, random.Random(7))]),
                         action_key(shuffled[policy.sample(probe, shuffled, random.Random(7))]))

    def test_grounded_aircraft_do_not_repeat_optional_landing_but_flying_aircraft_return(self):
        class LandingEnv:
            def __init__(self, flying):
                self.flying = flying

            def context(self):
                return {"catalog": {}, "geography": {"nodes": {}}}

            def observation(self):
                return {"state": {"units": {"plane": {"zone": "home", "route": ["sea", "home"],
                                                         "turn_flags": {"air_in_flight": int(self.flying)}}},
                                  "territories": {}, "battles": {}}}

        actions = [{"id": "land", "kind": "air_land_noncombat", "nation": "japan",
                    "parameters": {"unit": "plane", "destination": "home"}},
                   {"id": "end", "kind": "end_phase", "parameters": {}}]
        for flying, expected in ((False, "end_phase"), (True, "air_land_noncombat")):
            policy = scripted_policy()
            chosen = actions[policy.sample(LandingEnv(flying), actions, random.Random(9))]
            self.assertEqual(chosen["kind"], expected)


if __name__ == "__main__":
    unittest.main()
