"""Income-rate refresh and compatibility after real outer-rule transitions."""
import json
import unittest

import gwrl_cpp

from studies.campaign.curriculum import make_env
from tools.benchmark_campaign_backends import sampled_step


class CampaignIncomeRefreshContractTests(unittest.TestCase):
    def assert_rates_current(self, env):
        state = json.loads(env.raw.serialize())["state"]
        expected = gwrl_cpp.campaign_refresh_income_oracle([env.raw])
        self.assertEqual(expected.error_array().tolist(), [0])
        refreshed = json.loads(expected.state_jsons[0])
        for nation, value in state["nations"].items():
            self.assertEqual(value["income_components"], refreshed["nations"][nation]["income_components"], nation)
            self.assertEqual(value["income_known"], refreshed["nations"][nation]["income_known"], nation)

    def test_legal_capture_refreshes_before_the_next_decision(self):
        # This real opening exposed the bug: the final CCP casualty decision
        # captures Hopeh, while the old outer hook left its territorial rate at 2.
        env = make_env(1951, calendar_rounds=3)
        seen_chance = seen_capture = False
        for _ in range(32):
            previous = json.loads(env.raw.serialize())["state"]
            row = sampled_step(env)
            seen_chance |= row["decision"]["kind"] == "chance"
            self.assert_rates_current(env)
            current = json.loads(env.raw.serialize())["state"]
            if (previous["territories"]["land_china_hopeh"]["possessor"] != "ccp"
                    and current["territories"]["land_china_hopeh"]["possessor"] == "ccp"):
                self.assertEqual(current["nations"]["ccp"]["income_components"]["territorial"], 3)
                self.assertFalse(current["clock"]["income_collected"])
                self.assertEqual(current["clock"]["phase"], "combat")
                seen_capture = True
                break
        self.assertTrue(seen_capture)
        self.assertTrue(seen_chance)

    def test_chance_hook_refreshes_without_collecting_income(self):
        env = make_env(1951, calendar_rounds=3)
        for _ in range(32):
            if env.decision_kind() == "chance":
                break
            sampled_step(env)
        self.assertEqual(env.decision_kind(), "chance")
        document = json.loads(env.raw.serialize())
        # An imported cached rate can be stale. A chance transition must refresh
        # it just as an action does, even when the roll changes no possession.
        document["state"]["nations"]["ccp"]["income_components"] = {"territorial": -71}
        env.raw.restore(json.dumps(document))
        treasury = document["state"]["nations"]["ccp"]["treasury"]
        env.resolve_chance()
        self.assert_rates_current(env)
        state = json.loads(env.raw.serialize())["state"]
        self.assertEqual(state["nations"]["ccp"]["treasury"], treasury)
        self.assertFalse(state["clock"]["income_collected"])

    def test_old_income_semantics_cannot_resume_silently(self):
        env = make_env(1951, calendar_rounds=3)
        original = env.raw.serialize()
        document = json.loads(original)
        marker = "gw36_v43_m4_politics_income_refresh_v1"
        self.assertIn(marker, document["rules_id"])
        document["rules_id"] = document["rules_id"].replace(marker, "gw36_v43_m4_politics")
        with self.assertRaisesRegex(Exception, "Checkpoint rules module mismatch"):
            env.raw.restore(json.dumps(document))
        self.assertEqual(env.raw.serialize(), original)


if __name__ == "__main__":
    unittest.main()
