"""Terminal-only held-out metrics, fixed opponents and nonmutating profiles."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from studies.campaign.evaluation import evaluate, profile, uncertainty, validate_heldout_seeds
from studies.shared.multiplayer_mcts import Evaluation, OpponentPolicy, PLAYERS


class EvaluationEnv:
    """Two target choices, a real die, two other actors, and a true endpoint."""
    owners = ("axis", "axis", None, "allies", "comintern", None)

    def __init__(self, seed):
        self.node, self.score, self.draws = 0, 0, 0
        self.random = random.Random(seed)
        self.search_copy = False
        self.applied = []
        self.units = {"japan_unit": {"owner": "japan", "type": "infantry"},
                      "kmt_unit": {"owner": "kmt", "type": "infantry"},
                      "ccp_unit": {"owner": "ccp", "type": "cavalry"}}
        self.territories = {"land_a": {"possessor": "japan"}, "land_b": {"possessor": "kmt"}}

    def current_decision_player(self):
        return self.owners[self.node]

    def decision_kind(self):
        return "terminal" if self.is_terminal() else "chance" if self.node == 2 else "choose"

    def legal_actions(self):
        owner = self.current_decision_player()
        return [] if owner is None else [{"id": name, "kind": "evaluation_select", "player": owner,
                                          "parameters": {"amount": amount}} for name, amount in (("a", 1), ("b", 2))]

    def apply_action(self, action):
        if action not in self.legal_actions():
            raise ValueError("Illegal fixture action")
        self.applied.append((self.current_decision_player(), action["id"]))
        self.score += action["parameters"]["amount"]
        if self.node == 0:
            self.units.pop("kmt_unit")
            self.territories["land_b"]["possessor"] = "japan"
        elif self.node == 3:
            self.units["ccp_unit"]["owner"] = "kmt"  # Transfer, not a casualty.
            self.units["recruit"] = {"owner": "kmt", "type": "infantry"}
        elif self.node == 4:
            self.units.pop("japan_unit")
        self.node += 1

    def resolve_chance(self):
        if self.node != 2:
            raise ValueError("No fixture die is pending")
        self.draws += 1
        self.score += self.random.randrange(4)
        self.node += 1

    def is_terminal(self):
        return self.node == 5

    def wealth(self):
        result = {}
        for i, (player, nation) in enumerate(zip(PLAYERS, ("japan", "kmt", "ccp"), strict=True)):
            components = {"income_rate": [30 + self.score, 15, 12][i], "infrastructure": 0,
                          "treasury": 0, "paid_construction": 0,
                          "units": 2 * sum(unit["owner"] == nation for unit in self.units.values())}
            result[player] = {**components, "wealth": components["income_rate"] + .1 * components["units"]}
        return result

    def returns(self):
        if not self.is_terminal():
            return [0., 0., 0.]
        values = [self.wealth()[player]["wealth"] for player in PLAYERS]
        return [2 * value - sum(values) for value in values]

    def observation(self):
        # Intentionally returns mutable unit/territory maps to catch aliasing in
        # before/after casualty snapshots.
        return {"current_decision_player": self.current_decision_player(), "decision_kind": self.decision_kind(),
                "state": {"units": self.units, "territories": self.territories,
                          "clock": {"completed_rounds": int(self.is_terminal()), "phase": self.decision_kind(),
                                    "player_turn_serial": str(self.node)}, "node": self.node,
                          "score": self.score, "completed_turns": {player: int(self.is_terminal()) for player in PLAYERS}}}

    def context(self):
        return {"players": list(PLAYERS), "catalog": {}, "geography": {"nodes": {
            "land_a": {"id": "land_a", "ipp_value": 2, "neighbors": []},
            "land_b": {"id": "land_b", "ipp_value": 1, "neighbors": []}}}}

    def planning_key(self):
        return json.dumps(self.observation(), sort_keys=True)

    def serialize(self):
        return json.dumps({"state": self.observation(), "random": self.random.getstate(), "draws": self.draws}, sort_keys=True)

    def clone(self):
        return copy.deepcopy(self)

    def clone_for_search(self, seed):
        clone = self.clone()
        clone.random = random.Random(seed)
        clone.search_copy = True
        return clone


class CountingEvaluator:
    version = "evaluation-test-vector-v1"

    def __init__(self):
        self.batches = []

    def evaluate(self, env, actions):
        return Evaluation([1.] * len(actions), [10., -5., -8.])

    def evaluate_batch(self, requests):
        self.batches.append(len(requests))
        return [self.evaluate(env, actions) for env, actions in requests]


class ToggleEnv(EvaluationEnv):
    """A legal two-state decision cycle; applied history is not decision state."""
    def is_terminal(self):
        return False

    def decision_kind(self):
        return "choose"

    def apply_action(self, action):
        if action not in self.legal_actions():
            raise ValueError("Illegal toggle action")
        self.applied.append((self.current_decision_player(), action["id"]))
        self.node = 1 - self.node


class CampaignEvaluationTests(unittest.TestCase):
    def test_repeated_state_guard_is_a_nonterminal_four_step_cutoff(self):
        actual = []

        def factory(seed):
            env = ToggleEnv(seed)
            actual.append(env)
            return env

        report = evaluate(factory, CountingEvaluator(), target_player="axis", seeds=[7],
                          simulations=1, max_depth=1, max_transitions=1500, max_state_visits=3)
        game = report["games"][0]
        self.assertEqual(game["counts"]["transitions"], 4)
        self.assertEqual(len(actual[0].applied), 4)
        self.assertFalse(actual[0].is_terminal())
        self.assertFalse(game["terminal"])
        self.assertTrue(game["truncated"])
        self.assertEqual(game["stop_reason"], "repeated_state_guard")
        self.assertEqual(game["repeated_state_guard"], {
            "threshold": 3, "max_seen": 3, "repeated_key": game["initial"]["planning_key"],
            "includes_initial_state": True, "triggered": True})
        self.assertIsNotNone(game["first_search_value_prediction"])
        self.assertIsNone(game["observed_terminal_returns"])
        self.assertIsNone(game["terminal_squared_value_error"])
        self.assertEqual(report["value_calibration"]["complete_games"], 0)
        self.assertEqual(report["observed_return_statistics"]["axis"]["n"], 0)
        self.assertEqual(report["max_transitions"], 1500)
        json.dumps(report, allow_nan=False)

    def test_repeated_state_guard_can_be_disabled_and_roots_stop_independently(self):
        disabled = evaluate(ToggleEnv, CountingEvaluator(), target_player="axis", seeds=[7],
                            simulations=1, max_depth=1, max_transitions=7, max_state_visits=None)
        game = disabled["games"][0]
        self.assertEqual(game["counts"]["transitions"], 7)
        self.assertEqual(game["stop_reason"], "transition_budget")
        self.assertIsNone(game["repeated_state_guard"]["threshold"])
        self.assertEqual(game["repeated_state_guard"]["max_seen"], 4)
        self.assertFalse(game["repeated_state_guard"]["triggered"])
        mixed = evaluate(lambda seed: ToggleEnv(seed) if seed == 7 else EvaluationEnv(seed),
                         CountingEvaluator(), target_player="axis", seeds=[7, 11],
                         simulations=1, max_depth=1, max_transitions=10, max_state_visits=3)
        self.assertEqual([g["stop_reason"] for g in mixed["games"]], ["repeated_state_guard", "terminal"])
        self.assertEqual(mixed["terminal_games"], 1)
        self.assertEqual(mixed["truncated_games"], 1)
        self.assertEqual(mixed["observed_return_statistics"]["axis"]["n"], 1)
        self.assertEqual(mixed["value_calibration"]["complete_games"], 1)

    def test_repeated_state_guard_threshold_requires_a_positive_integer(self):
        for threshold in (0, -1, True, 3.0, "3"):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                evaluate(ToggleEnv, CountingEvaluator(), target_player="axis", seeds=[7],
                         max_state_visits=threshold)
    def test_complete_games_report_raw_vectors_wealth_casualties_and_calibration(self):
        report = evaluate(EvaluationEnv, CountingEvaluator(), target_player="axis", seeds=[1009, 1013],
                          simulations=4, max_depth=4, max_transitions=5)
        self.assertEqual((report["terminal_games"], report["truncated_games"]), (2, 0))
        self.assertEqual(report["value_calibration"]["complete_games"], 2)
        self.assertFalse(report["root_noise"])
        self.assertEqual(report["search_mode"], "fixed_opponents")
        for game in report["games"]:
            self.assertEqual(game["stop_reason"], "terminal")
            self.assertEqual(game["counts"]["transitions"], 5)
            self.assertEqual(game["counts"]["chance_events"], 1)
            self.assertEqual(game["decisions_by_actor"], {"axis": 2, "allies": 1, "comintern": 1})
            self.assertEqual(game["casualties_by_nation"], {"kmt": 1, "japan": 1})
            self.assertEqual(game["casualties_by_nation_and_type"]["kmt"], {"infantry": 1})
            self.assertNotIn("ccp", game["casualties_by_nation"])
            self.assertEqual(game["territorial_control"], {"japan": 2})
            wealth = [game["wealth_components_at_stop"][player]["wealth"] for player in PLAYERS]
            self.assertEqual(game["observed_terminal_returns"], [2 * value - sum(wealth) for value in wealth])
            errors = [p - v for p, v in zip(game["first_search_value_prediction"], game["observed_terminal_returns"], strict=True)]
            self.assertEqual(game["terminal_squared_value_error"], [error ** 2 for error in errors])
            self.assertEqual(game["illegal_actions"], 0)
        for player in PLAYERS:
            self.assertEqual(report["observed_return_statistics"][player]["n"], 2)
            self.assertEqual(report["observed_terminal_wealth_statistics"][player]["wealth"]["n"], 2)
        json.dumps(report, allow_nan=False)

    def test_transition_cutoff_never_invents_returns_or_resolves_pending_dice(self):
        actual = []

        def factory(seed):
            env = EvaluationEnv(seed)
            actual.append(env)
            return env

        report = evaluate(factory, CountingEvaluator(), target_player="axis", seeds=[19, 23],
                          simulations=2, max_depth=2, max_transitions=2)
        self.assertEqual((report["terminal_games"], report["truncated_games"]), (0, 2))
        self.assertEqual([env.draws for env in actual], [0, 0])
        self.assertEqual(report["value_calibration"]["complete_games"], 0)
        for game in report["games"]:
            self.assertEqual(game["clock"]["phase"], "chance")
            self.assertEqual(game["stop_reason"], "transition_budget")
            self.assertIsNone(game["observed_terminal_returns"])
            self.assertIsNone(game["terminal_squared_value_error"])
            self.assertIsNotNone(game["first_search_value_prediction"])
        for player in PLAYERS:
            self.assertEqual(report["observed_return_statistics"][player]["n"], 0)
            self.assertIsNone(report["value_calibration"]["squared_error"][player]["mean"])

    def test_all_search_waves_are_aggregated_and_batch_sizes_are_measured(self):
        evaluator = CountingEvaluator()
        report = evaluate(EvaluationEnv, evaluator, target_player="axis", seeds=[7, 11, 13],
                          simulations=1, max_depth=1, max_transitions=2)
        metrics = report["inference_batches"]
        self.assertEqual(metrics["search_calls"], 2)
        self.assertEqual(metrics["roots"], 6)  # Three roots searched in each of two waves.
        self.assertEqual(metrics["batch_sizes"], evaluator.batches)
        self.assertEqual(metrics["batches"], len(evaluator.batches))
        self.assertEqual(metrics["requests"], sum(evaluator.batches))
        self.assertGreaterEqual(max(metrics["batch_sizes"]), 3)

    def test_the_same_fixed_policy_is_sampled_in_search_and_actual_play(self):
        calls, actual = [], []

        def distribution(env, actions):
            calls.append((env.search_copy, env.current_decision_player()))
            return [0., 1.]

        policy = OpponentPolicy("fixed-opponent-witness-v1", distribution)

        def factory(seed):
            env = EvaluationEnv(seed)
            actual.append(env)
            return env

        with patch("studies.campaign.evaluation.scripted_policy", return_value=policy):
            report = evaluate(factory, CountingEvaluator(), target_player="axis", seeds=[37],
                              simulations=12, max_depth=8, max_transitions=5)
        self.assertEqual(report["opponent_policy"], policy.version)
        for owner in ("allies", "comintern"):
            self.assertIn((False, owner), calls)
            self.assertIn((True, owner), calls)
            self.assertIn((owner, "b"), actual[0].applied)

    def test_scripted_control_has_no_fake_neural_calibration(self):
        evaluator = CountingEvaluator()
        report = evaluate(EvaluationEnv, evaluator, target_player="comintern", seeds=[43],
                          target_script="cautious", max_transitions=5)
        self.assertEqual(report["search_mode"], "scripted_control")
        self.assertEqual(report["terminal_games"], 1)
        self.assertEqual(report["inference_batches"]["requests"], 0)
        self.assertEqual(report["value_calibration"]["complete_games"], 0)
        self.assertIsNone(report["games"][0]["first_search_value_prediction"])
        self.assertEqual(evaluator.batches, [])

    def test_weight_version_cannot_change_between_search_waves(self):
        evaluator = CountingEvaluator()

        class MutatingEnv(EvaluationEnv):
            def apply_action(self, action):
                super().apply_action(action)
                if not self.search_copy and self.node == 1:
                    evaluator.version = "changed-after-first-real-action"

        with self.assertRaisesRegex(ValueError, "between search waves"):
            evaluate(MutatingEnv, evaluator, target_player="axis", seeds=[17],
                     simulations=1, max_depth=1, max_transitions=2)

    def test_all_targets_exclude_training_but_may_share_paired_heldout_seeds(self):
        heldout = {player: [1009, 1013] for player in PLAYERS}
        checked = validate_heldout_seeds(heldout, [1, 2, 2, 3])
        self.assertTrue(checked["disjoint_from_training"])
        self.assertEqual(checked["distinct_training_seeds"], 3)
        for player in PLAYERS:
            wrong = copy.deepcopy(heldout)
            wrong[player] = [1, 1013]
            with self.assertRaisesRegex(ValueError, "overlap training"):
                validate_heldout_seeds(wrong, [1, 2, 3])
        with self.assertRaises(ValueError):
            validate_heldout_seeds({"axis": [10]}, [1])
        with self.assertRaises(ValueError):
            validate_heldout_seeds({player: [10, 10] for player in PLAYERS}, [1])

    def test_validation_and_uncertainty_do_not_claim_one_game_precision(self):
        self.assertEqual(uncertainty([])["n"], 0)
        self.assertIsNone(uncertainty([2])["approximate_95_percent_interval"])
        result = uncertainty([1, 3])
        self.assertEqual(result["mean"], 2)
        self.assertEqual(result["standard_error"], 1)
        self.assertAlmostEqual(result["approximate_95_percent_interval"][0], .04)
        self.assertAlmostEqual(result["approximate_95_percent_interval"][1], 3.96)
        for arguments in ({"seeds": [1, 1]}, {"seeds": [-1]}, {"seeds": [True]},
                          {"max_transitions": 0}, {"simulations": 0}, {"max_depth": 0}):
            options = {"target_player": "axis", "seeds": [3], **arguments}
            with self.assertRaises(ValueError):
                evaluate(EvaluationEnv, CountingEvaluator(), **options)

    def test_profile_uses_real_batches_and_preserves_live_state_and_rng(self):
        envs = [EvaluationEnv(101), EvaluationEnv(103)]
        envs[1].apply_action(envs[1].legal_actions()[0])
        envs[1].apply_action(envs[1].legal_actions()[0])
        self.assertEqual(envs[1].decision_kind(), "chance")
        before = [env.serialize() for env in envs]
        evaluator = CountingEvaluator()
        report = profile(envs, evaluator, repeats=2)
        self.assertTrue(report["actual_state_unchanged"])
        self.assertEqual(report["inference_batch_sizes"], [2, 2])
        self.assertEqual(evaluator.batches, [2, 2])
        self.assertEqual([env.serialize() for env in envs], before)
        self.assertEqual(envs[1].draws, 0)
        self.assertEqual(len(report["timings_seconds"]["rule_transition"]["samples"]), 4)
        self.assertTrue(all(value >= 0 for timing in report["timings_seconds"].values() for value in timing["samples"]))

    def test_actual_completed_campaign_checkpoint_reports_engine_wealth_and_returns(self):
        import gwrl_cpp
        from studies.shared.campaign_adapter import CampaignAdapter

        root = Path(__file__).resolve().parents[1]
        trace = json.loads((root / "game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/mixed_seed_1936/trace.json").read_text())
        actual = []

        def factory(seed):
            raw = gwrl_cpp.CampaignEnv(str(root / "game_content/scenarios/japan_china_1936"), seed)
            raw.restore(trace["final_checkpoint"])
            env = CampaignAdapter(raw)
            actual.append(env)
            return env

        evaluator = CountingEvaluator()
        report = evaluate(factory, evaluator, target_player="axis", seeds=[1009], max_transitions=1,
                          max_state_visits=1)
        game = report["games"][0]
        self.assertEqual(report["terminal_games"], 1)
        self.assertEqual(game["wealth_components_at_stop"], actual[0].wealth())
        self.assertEqual(game["observed_terminal_returns"], actual[0].returns())
        self.assertEqual(game["clock"]["completed_rounds"], 11)
        self.assertEqual(game["stop_reason"], "terminal")
        self.assertFalse(game["repeated_state_guard"]["triggered"])
        self.assertEqual(game["counts"].get("transitions", 0), 0)
        self.assertEqual(report["value_calibration"]["complete_games"], 0)
        self.assertEqual(evaluator.batches, [])


if __name__ == "__main__":
    unittest.main()
