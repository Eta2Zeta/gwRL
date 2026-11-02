"""The zone encoding as the adapter hands it to the network: cached, selectable, portable."""
from __future__ import annotations

import pickle
import random
import unittest

import numpy as np

import gwrl_cpp
from studies.campaign.curriculum import make_env


def option_rows(zone, index):
    a = zone.arrays()
    lo, hi = a["action_offsets"][index], a["action_offsets"][index + 1]
    plo, phi = a["path_offsets"][index], a["path_offsets"][index + 1]
    return (a["action_column"][lo:hi].tolist(), a["action_value"][lo:hi].tolist(), int(a["action_source"][index]),
            int(a["action_target"][index]), a["path_zone"][plo:phi].tolist(), zone.factors()[index])


def position_rows(zone):
    a = zone.arrays()
    return [a[name].tolist() for name in ("zone_index", "zone_column", "zone_value", "global_column", "global_value")]


class ZoneEncodingTests(unittest.TestCase):
    def setUp(self):
        self.env = make_env(1951, calendar_rounds=3)
        while self.env.decision_kind() != "combat_movement":
            if self.env.decision_kind() == "chance":
                self.env.resolve_chance()
            else:
                self.env.apply_action(self.env.legal_actions()[-1])

    def test_one_decision_is_encoded_once_and_reused(self):
        actions = tuple(self.env.legal_actions())
        first = self.env.zone_input(actions)
        self.assertIs(self.env.zone_input(actions), first)
        self.assertIs(self.env.zone_input(), first)
        self.assertEqual(first.action_count, len(actions))
        self.assertEqual(first.version, self.env.raw.zone_encoding_spec()["version"])
        for array in first.arrays().values():
            self.assertEqual(array.dtype, np.int32)

    def test_subsets_list_exactly_the_requested_options(self):
        actions = tuple(self.env.legal_actions())
        full = self.env.zone_input(actions)
        order = list(range(len(actions)))
        random.Random(3).shuffle(order)
        chosen = order[: max(1, len(order) // 2)]
        subset = self.env.zone_input(tuple(actions[i] for i in chosen))
        self.assertEqual(subset.action_count, len(chosen))
        self.assertEqual(position_rows(subset), position_rows(full))
        for row, index in enumerate(chosen):
            self.assertEqual(option_rows(subset, row), option_rows(full, index))
        value_only = full.without_actions()
        self.assertEqual(value_only.action_count, 0)
        self.assertEqual(position_rows(value_only), position_rows(full))

    def test_stale_or_foreign_options_are_refused(self):
        actions = tuple(self.env.legal_actions())
        other = make_env(1952, calendar_rounds=3)
        with self.assertRaises(ValueError):
            self.env.zone_input(tuple(other.legal_actions()[:1]) + actions[:1])

    def test_pickles_and_rebuilds_without_change(self):
        zone = self.env.zone_input(tuple(self.env.legal_actions()))
        restored = pickle.loads(pickle.dumps(zone))
        self.assertTrue(restored == zone)
        rebuilt = gwrl_cpp.campaign_zone_input(zone.version, zone.arrays(), zone.factors())
        self.assertTrue(rebuilt == zone)
        broken = zone.arrays()
        broken["action_offsets"] = broken["action_offsets"][:-1]
        with self.assertRaises(ValueError):
            gwrl_cpp.campaign_zone_input(zone.version, broken, zone.factors())

    def test_a_new_decision_gets_a_new_encoding(self):
        actions = tuple(self.env.legal_actions())
        before = self.env.zone_input(actions)
        self.env.apply_action(actions[0])
        after = self.env.zone_input(None if self.env.decision_kind() != "chance" else ())
        self.assertFalse(after == before)

    def test_chance_positions_encode_without_options(self):
        env = make_env(1951, calendar_rounds=3)
        rng = random.Random(1)
        for _ in range(400):
            if env.decision_kind() == "chance":
                zone = env.zone_input(())
                self.assertEqual(zone.action_count, 0)
                self.assertGreater(len(zone.arrays()["global_column"]), 0)
                return
            actions = env.legal_actions()
            env.apply_action(actions[rng.randrange(len(actions))])
        self.fail("No chance position was reached")

    def test_every_name_in_random_play_has_a_column(self):
        gwrl_cpp.zone_encoding_unknowns(True)
        env = make_env(1952, calendar_rounds=3)
        rng = random.Random(2)
        while not env.is_terminal():
            if env.decision_kind() == "chance":
                env.zone_input(())
                env.resolve_chance()
                continue
            actions = tuple(env.legal_actions())
            env.zone_input(actions)
            env.apply_action(actions[rng.randrange(len(actions))])
        self.assertEqual(gwrl_cpp.zone_encoding_unknowns(True), {})


if __name__ == "__main__":
    unittest.main()
