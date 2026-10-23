import json
import unittest

import gwrl_cpp

from studies.campaign.curriculum import SCENARIO, compatibility, make_env, task_manifest


class CampaignCurriculumTests(unittest.TestCase):
    def test_explicit_short_horizon_is_a_distinct_real_game(self):
        full = make_env(19)
        short = make_env(19, calendar_rounds=1)
        self.assertEqual(len(short.observation()["state"]["units"]), 99)
        self.assertNotEqual(compatibility(full), compatibility(short))
        self.assertTrue(task_manifest(full)["full_target_game"])
        self.assertFalse(task_manifest(short)["full_target_game"])
        original = full.serialize()
        with self.assertRaises(RuntimeError):
            full.restore(short.serialize())
        self.assertEqual(full.serialize(), original)
        raw = short.raw
        for _ in range(30):
            if raw.is_terminal():
                break
            actions = raw.legal_actions()
            preferred = next((a for a in actions if a.kind == "end_phase"), None)
            raw.apply_action(preferred or next(a for a in actions if a.kind == "economy_finish_research"))
        self.assertTrue(raw.is_terminal())
        state = raw.observation()["state"]
        self.assertEqual(state["completed_turns"], {n: 1 for n in ("ccp", "mongolia", "japan", "kmt")})
        self.assertEqual(state["clock"]["player_turn_serial"], "4")
        values = [raw.wealth()[p]["wealth"] for p in ("axis", "allies", "comintern")]
        self.assertEqual(raw.returns(), [2 * value - sum(values) for value in values])

    def test_invalid_horizons_reject_without_touching_full_campaign(self):
        for rounds in (0, -1, 12):
            with self.assertRaises(ValueError):
                gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO), rounds)
        self.assertNotIn("curriculum", make_env(1).context()["rules"])


if __name__ == "__main__":
    unittest.main()
