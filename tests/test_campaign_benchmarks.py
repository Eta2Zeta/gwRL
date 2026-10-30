"""Public study APIs use canonical campaign gameplay; no training is run."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import gwrl_cpp


ROOT = Path(__file__).resolve().parents[1]
TINY = ROOT / "game_content/scenarios/china_simplified_setup.json"
CAMPAIGN = ROOT / "game_content/scenarios/japan_china_1936"


def choose(env, kind):
    action = next(a for a in env.legal_actions() if a.kind == kind)
    return env.step(action)


class CampaignBenchmarkTests(unittest.TestCase):
    def test_tiny_public_actions_and_features_are_canonical(self):
        env = gwrl_cpp.JapanTrainingEnv(str(TINY))
        self.assertEqual(gwrl_cpp.BENCHMARK_SCHEMA, "campaign_v1")
        self.assertEqual(env.current_phase(), "production")
        self.assertEqual(env.unit_count_for("Japan"), 4)
        self.assertEqual(env.nation_treasury("Japan"), 13)
        self.assertEqual(len(env.encode_state()), len(env.state_feature_labels()))
        actions = env.legal_actions()
        self.assertTrue(actions)
        self.assertIsInstance(actions[0], gwrl_cpp.CampaignAction)
        self.assertIsInstance(actions[0].parameters, dict)
        self.assertEqual(json.loads(actions[0].describe())["kind"], actions[0].kind)
        self.assertEqual(len(actions), len(env.encode_legal_actions()))

    def test_tiny_completes_all_national_turns(self):
        env = gwrl_cpp.JapanTrainingEnv(str(TINY))
        for _ in range(150):
            if env.is_terminal():
                break
            actions = env.legal_actions()
            env.step(next((a for a in actions if a.kind == "end_phase"), actions[0]))
        self.assertTrue(env.is_terminal())
        self.assertEqual([env.completed_turns_for(n) for n in ("Japan", "KMT", "CCP")], [2, 2, 2])
        self.assertEqual(env.legal_actions(), [])

    def test_composition_exposes_real_defender_and_attacker_casualties(self):
        env = gwrl_cpp.CompositionBattleEnv(3, 3)
        env.set_dice_tape_for_testing([1] * 50)
        choose(env, "benchmark_compose_units")
        choose(env, "benchmark_finish_composition")
        self.assertEqual(env.current_nation(), "Defender")
        choose(env, "benchmark_compose_units")
        choose(env, "benchmark_finish_composition")
        self.assertFalse(env.is_terminal())
        casualty_owners = set()
        for _ in range(80):
            if env.is_terminal():
                break
            actions = env.legal_actions()
            action = next((a for a in actions if "decline" in a.kind), actions[0])
            if action.kind == "land_take_casualty":
                casualty_owners.add(action.nation)
            env.step(action)
        self.assertTrue(env.is_terminal())
        self.assertEqual(casualty_owners, {"japan", "kmt"})
        self.assertEqual(env.unit_count_for("Attacker"), 0)
        self.assertEqual(env.unit_count_for("Defender"), 0)
        self.assertEqual(env.final_reward(), 0)
        self.assertEqual(env.terminal_reward_for("Defender"), 0)

    def test_checkpoint_clone_and_search_randomness_are_separate(self):
        env = gwrl_cpp.CompositionBattleEnv()
        snapshot = env.serialize()
        clone = env.clone()
        clone.step(clone.legal_actions()[0])
        self.assertEqual(env.serialize(), snapshot)
        clone.restore(snapshot)
        self.assertEqual(clone.serialize(), snapshot)
        search = env.clone_for_search(201)
        self.assertEqual(search.encode_state(), env.encode_state())
        self.assertNotEqual(search.serialize(), env.serialize())

    def test_search_copies_play_like_ordinary_engines(self):
        foreign = gwrl_cpp.CampaignEnv(str(CAMPAIGN), 1).legal_actions()[0]
        for make in (gwrl_cpp.CompositionBattleEnv, lambda: gwrl_cpp.JapanTrainingEnv(str(TINY))):
            env = make()
            search = env.clone_for_search(202)
            ordinary = env.clone()
            ordinary.restore(search.serialize())
            with self.assertRaises(RuntimeError):
                search.step(foreign)
            for _ in range(300):
                self.assertEqual(search.serialize(), ordinary.serialize())
                if search.is_terminal():
                    break
                action = search.legal_actions()[0]
                search.step(action)
                ordinary.step(action)
            self.assertEqual(search.serialize(), ordinary.serialize())

    def test_invalid_configuration_and_empty_forces(self):
        with self.assertRaises(RuntimeError):
            gwrl_cpp.CompositionBattleEnv(-1, 2)
        with self.assertRaises(RuntimeError):
            gwrl_cpp.CompositionBattleEnv(3, 3, "invented")
        env = gwrl_cpp.CompositionBattleEnv(0, 0)
        choose(env, "benchmark_finish_composition")
        choose(env, "benchmark_finish_composition")
        self.assertTrue(env.is_terminal())
        self.assertEqual(env.winner_id(), "")

    def test_mini_trainer_starts_at_real_production_and_preserves_old_exports(self):
        from studies.mini_japan_two_turn.train import (
            build_first_decision_after_declaration_snapshot,
            verify_against_cpp_example,
        )
        env = gwrl_cpp.JapanTrainingEnv(str(TINY))
        state, encoded_actions, actions = build_first_decision_after_declaration_snapshot(env)
        self.assertEqual(env.current_phase(), "production")
        self.assertEqual(len(state), 512)
        self.assertEqual(len(actions), len(encoded_actions))
        with tempfile.TemporaryDirectory() as directory:
            historical = Path(directory) / "export.json"
            historical.write_text('{"state_features": [0]}')
            result = verify_against_cpp_example(env, historical)
            self.assertTrue(result["skipped"])
            self.assertEqual(historical.read_text(), '{"state_features": [0]}')


if __name__ == "__main__":
    unittest.main()
