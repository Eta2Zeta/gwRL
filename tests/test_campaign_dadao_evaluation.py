"""Separate Dadao possession evidence without changing gameplay or Japan metrics."""
from __future__ import annotations

import copy
import unittest

from studies.campaign.evaluation import JapanTerritoryTracker, TERRITORY_TRACKING_SCHEMA, evaluate
from test_campaign_evaluation import CountingEvaluator, EvaluationEnv


class DadaoExpansionEnv(EvaluationEnv):
    def __init__(self, seed):
        super().__init__(seed)
        self.observation_reads = 0

    def context(self):
        value = super().context()
        value["factions"] = {"kmt": {"home_country_known": True, "home_country": ["land_a", "land_b"]}}
        return value

    def apply_action(self, action):
        super().apply_action(action)
        if self.node == 1:
            self.territories["land_b"]["possessor"] = "dadao"

    def observation(self):
        self.observation_reads += 1
        return super().observation()


class DadaoEvaluationTests(unittest.TestCase):
    def test_national_trackers_keep_zones_ipp_recaptures_and_methods_separate(self):
        state = {"territories": {"a": {"possessor": "japan"}, "b": {"possessor": "kmt"},
                                  "c": {"possessor": "dadao"}, "other": {"possessor": "kmt"}},
                 "clock": {"round_index": 0}}
        context = {"factions": {"kmt": {"home_country_known": True, "home_country": ["a", "b", "c"]}},
                   "geography": {"nodes": {zone: {"ipp_value": ipp} for zone, ipp in
                                               (("a", 1), ("b", 2), ("c", 3), ("other", 99))}}}
        japan = JapanTerritoryTracker(context, state)
        dadao = JapanTerritoryTracker(context, state, nation="dadao")
        transitions = (("b", "dadao", "influence"), ("b", "kmt", "countercapture"),
                       ("b", "dadao", "battle_possession"), ("c", "japan", "japanese_capture"),
                       ("a", "kmt", "japanese_loss"), ("a", "dadao", "alignment"),
                       ("other", "dadao", "outside_scope"))
        for index, (zone, owner, kind) in enumerate(transitions, 1):
            state["clock"]["round_index"] = index
            state["territories"][zone]["possessor"] = owner
            for tracker in (japan, dadao):
                tracker.record(state, index, kind)
        jp, minor = japan.summary(terminal=True), dadao.summary(terminal=True)
        self.assertEqual(jp["nation"], "japan")
        self.assertEqual(jp["newly_held"], {"zones": ["c"], "count": 1, "ipp": 3})
        self.assertEqual(jp["initial_holdings_lost"], {"zones": ["a"], "count": 1, "ipp": 1})
        self.assertEqual(minor["nation"], "dadao")
        self.assertEqual(minor["newly_held"], {"zones": ["a", "b"], "count": 2, "ipp": 3})
        self.assertEqual(minor["initial_holdings_lost"], {"zones": ["c"], "count": 1, "ipp": 3})
        self.assertEqual((minor["gross_acquisition_events"], minor["gross_acquired_ipp"]), (3, 5))
        self.assertEqual((minor["gross_loss_events"], minor["gross_lost_ipp"]), (2, 5))
        self.assertEqual(minor["net_ipp_change"], 0)
        self.assertEqual([row["action_kind"] for row in minor["events"]],
                         ["influence", "countercapture", "battle_possession", "japanese_capture", "alignment"])
        self.assertFalse(any(row["zone"] == "other" for row in minor["events"]))
        state["clock"]["round_index"] = 100
        self.assertEqual(minor["events"][0]["clock"], {"round_index": 1})

    def test_diagnostic_channel_preserves_actual_actions_randomness_and_existing_outcomes(self):
        environments = {}

        def run(track):
            roots = []
            def factory(seed):
                env = DadaoExpansionEnv(seed)
                roots.append(env)
                return env
            report = evaluate(factory, CountingEvaluator(), target_player="axis", seeds=[7, 11],
                              selection_mode="network_only", track_japan=track, max_transitions=5)
            environments[track] = roots
            return report

        plain, tracked = run(False), run(True)
        self.assertEqual(tracked["territorial_tracking_schema"], TERRITORY_TRACKING_SCHEMA)
        self.assertNotIn("territorial_tracking_schema", plain)
        for original, enriched, old_env, new_env in zip(plain["games"], tracked["games"],
                                                       environments[False], environments[True], strict=True):
            expected = copy.deepcopy(enriched)
            japanese = expected.pop("japan_chinese_home_country")
            dadao = expected.pop("dadao_chinese_home_country")
            self.assertEqual(expected, original)
            self.assertEqual(japanese["newly_held"], {"zones": [], "count": 0, "ipp": 0})
            self.assertEqual(dadao["newly_held"], {"zones": ["land_b"], "count": 1, "ipp": 1})
            self.assertEqual(dadao["events"][0]["action_kind"], "evaluation_select")
            self.assertEqual(old_env.serialize(), new_env.serialize())
            self.assertEqual(old_env.applied, new_env.applied)
            self.assertEqual(old_env.random.getstate(), new_env.random.getstate())
            self.assertEqual(old_env.draws, new_env.draws)
            # Both national trackers reuse the same per-transition snapshot;
            # only their two initial diagnostic snapshots add observation reads.
            self.assertEqual(new_env.observation_reads - old_env.observation_reads, 2)

    def test_unfinished_dadao_holdings_remain_explicitly_nonterminal(self):
        report = evaluate(DadaoExpansionEnv, CountingEvaluator(), target_player="axis", seeds=[7],
                          selection_mode="network_only", track_japan=True, max_transitions=1)
        game = report["games"][0]
        self.assertFalse(game["terminal"])
        self.assertFalse(game["dadao_chinese_home_country"]["terminal"])
        self.assertIsNone(game["observed_terminal_returns"])
        self.assertEqual(game["dadao_chinese_home_country"]["at_stop"]["zones"], ["land_b"])


if __name__ == "__main__":
    unittest.main()
