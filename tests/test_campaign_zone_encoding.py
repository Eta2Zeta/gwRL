"""The zone encoding as the adapter hands it to the network: cached, selectable, portable."""
from __future__ import annotations

import pickle
import random
import re
import unittest
from pathlib import Path

import numpy as np

import gwrl_cpp
from studies.campaign.curriculum import make_env


def option_rows(zone, index):
    a = zone.arrays()
    lo, hi = a["action_offsets"][index], a["action_offsets"][index + 1]
    plo, phi = a["path_offsets"][index], a["path_offsets"][index + 1]
    return (a["action_column"][lo:hi].tolist(), a["action_value"][lo:hi].tolist(), int(a["action_source"][index]),
            int(a["action_target"][index]), a["path_zone"][plo:phi].tolist())


def groups(zone):
    return zone.arrays()["factor_groups"].reshape(-1, 4)


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
        # Policy groups are renumbered from zero but keep which options share them.
        whole, part = groups(full), groups(subset)
        for level in range(4):
            seen = {}
            for row, index in enumerate(chosen):
                self.assertEqual(seen.setdefault(int(whole[index, level]), int(part[row, level])), part[row, level])
            self.assertEqual(sorted(set(part[:, level].tolist())), list(range(len(seen))))
        value_only = full.without_actions()
        self.assertEqual(value_only.action_count, 0)
        self.assertEqual(position_rows(value_only), position_rows(full))

    def test_stale_or_foreign_options_are_refused(self):
        actions = tuple(self.env.legal_actions())
        other = make_env(1952, calendar_rounds=3)
        with self.assertRaises(ValueError):
            self.env.zone_input(tuple(other.legal_actions()[:1]) + actions[:1])

    def test_equal_options_of_a_copy_select_the_same_encoding(self):
        actions = tuple(self.env.legal_actions())
        clone = self.env.clone_for_search(5)
        self.assertTrue(clone.zone_input(actions[::-1]) == self.env.zone_input(actions).select(list(range(len(actions)))[::-1]))

    def test_pickles_and_rebuilds_without_change(self):
        zone = self.env.zone_input(tuple(self.env.legal_actions()))
        restored = pickle.loads(pickle.dumps(zone))
        self.assertTrue(restored == zone)
        rebuilt = gwrl_cpp.campaign_zone_input(zone.version, zone.arrays())
        self.assertTrue(rebuilt == zone)
        for name, change in (("action_offsets", lambda a: a[:-1]), ("zone_index", lambda a: a[::-1]),
                             ("factor_groups", lambda a: a + 1), ("factor_groups", lambda a: a[:-1])):
            broken = zone.arrays()
            broken[name] = change(broken[name])
            with self.subTest(name=name), self.assertRaises(ValueError):
                gwrl_cpp.campaign_zone_input(zone.version, broken)

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
        # Two whole eleven-round games, about 3.5 seconds each. A random move is
        # sometimes replaced by ending the phase, so some phases do little and
        # others much. tools/check_zone_names.py plays hundreds.
        gwrl_cpp.zone_encoding_unknowns(True)
        early = 0
        for seed in (1952, 1953):
            env = make_env(seed, calendar_rounds=11)
            rng = random.Random(seed)
            while not env.is_terminal():
                if env.decision_kind() == "chance":
                    env.zone_input(())
                    env.resolve_chance()
                    continue
                actions = tuple(env.legal_actions())
                env.zone_input(actions)
                # A wrapper action's kind is the scheduler's label; the engine's
                # move name ends its id.
                ends = [action for action in actions if action.id.endswith(":play:end_phase")]
                if ends and rng.random() < 0.05:
                    env.apply_action(ends[0])
                    early += 1
                else:
                    env.apply_action(actions[rng.randrange(len(actions))])
        self.assertGreater(early, 0, "no phase was ended early")
        self.assertEqual(gwrl_cpp.zone_encoding_unknowns(True), {})


ROOT = Path(__file__).resolve().parents[1]
WORD = r'V\((?:std::string|Id)\("([a-z_0-9]+)"\)\)'


class EngineNamesHaveColumnsTests(unittest.TestCase):
    """Names written in the engine's source have questions in the zone encoding.

    The encoder translates the engine's names through fixed lists, and a name
    missing from a list only falls into an "other" question. These checks read
    the rule code for the usual ways it writes battle notes, marks, the words in
    battle notes and move details, and prices, so a rule that adds a name fails
    here rather than in a long random-play check.
    """

    @classmethod
    def setUpClass(cls):
        spec = make_env(1951, calendar_rounds=3).raw.zone_encoding_spec()
        cls.zone_columns = set(spec["zone_column_names"])
        cls.global_columns = set(spec["global_column_names"])
        cls.action_columns = set(spec["action_column_names"])
        cls.places = set(spec["zones"]) | set(spec["nations"])
        skip = {"zone_encoding.cpp", "campaign_state.cpp", "python_bindings.cpp", "simple_json.cpp"}
        cls.sources = {path.name: path.read_text() for path in sorted((ROOT / "src").glob("*.cpp")) if path.name not in skip}
        cls.battle_sources = {name: text for name, text in cls.sources.items() if "BattleState" in text}

    def missing(self, found, has):
        return sorted(f"{name} ({', '.join(sorted(files))})" for name, files in found.items() if not has(name))

    def test_battle_notes(self):
        accessor = re.compile(
            r'(?:\bput\(\s*[\w>.\-\[\]()]+\s*,\s*|\b(?:str|string|text|integer|boolean|object|array)\(\s*\w+\s*,\s*'
            r'|\.data\.(?:find|require|contains)\(|\bdata\.(?:find|at|erase|contains|count)\(|\bdata\[)"([a-z_0-9]+)"')
        found = {}
        for name, text in self.battle_sources.items():
            for match in accessor.finditer(text):
                found.setdefault(match.group(1), set()).add(name)
        self.assertGreater(len(found), 60)
        self.assertEqual(self.missing(found, lambda key: f"battle_data:{key}" in self.zone_columns), [])

    def test_marks(self):
        written = re.compile(r'(?:turnFlags|gameFlags|flags|commitments)\s*(?:\[|\.insert\(|\.emplace\()\s*(?:std::string\()?"([a-z_0-9]+)')
        found = {}
        for name, text in self.sources.items():
            for match in written.finditer(text):
                base = re.sub(r"_\d+$", "", match.group(1).rstrip("_"))
                found.setdefault(base, set()).add(name)
        self.assertGreater(len(found), 150)
        known = lambda flag: f"nation_flag:japan:{flag}" in self.global_columns or f"state_flag:{flag}" in self.global_columns
        self.assertEqual(self.missing(found, known), [])

    def test_words_in_battle_notes(self):
        found = {}
        for name, text in self.battle_sources.items():
            for match in re.finditer(r'\bput\(\s*\w+\s*,\s*"([a-z_0-9]+)"\s*,\s*' + WORD, text):
                found.setdefault((match.group(1), match.group(2)), set()).add(name)
            for match in re.finditer(r'\{\s*"(context|kind|reaction_context)"\s*,\s*' + WORD, text):
                found.setdefault((match.group(1), match.group(2)), set()).add(name)
            for match in re.finditer(r'\bfinishBattle\(\s*s\s*,\s*\w+\s*,([^;]*)\);', text):
                result = re.sub(r'\b(?:string|str|text)\(\s*\w+\s*,\s*"[a-z_0-9]+"\s*\)', "", match.group(1))
                for word in re.findall(r'"([a-z_0-9]+)"', result):
                    found.setdefault(("result", word), set()).add(name)
        self.assertGreater(len(found), 20)
        listed = lambda pair: (f"battle_data_word:{pair[0]}:{pair[1]}" in self.zone_columns or pair[1] in self.places)
        self.assertEqual(self.missing({f"{k}={w}": f for (k, w), f in found.items()},
                                      lambda text: listed(tuple(text.split("=")))), [])

    def test_words_in_moves_and_prices(self):
        found = {}
        call = re.compile(r'\b(?:action|politicalAction)\(')
        for name, text in self.sources.items():
            for start in (m.end() for m in call.finditer(text)):
                depth, end = 1, start
                while end < len(text) and depth:
                    depth += {"(": 1, ")": -1}.get(text[end], 0)
                    end += 1
                for match in re.finditer(r'\{\s*"([a-z_0-9]+)"\s*,\s*' + WORD, text[start:end]):
                    found.setdefault((match.group(1), match.group(2)), set()).add(name)
        prices = re.findall(r'out\.push_back\(\{"([a-z_0-9]+)"', self.sources["catalog.cpp"])
        self.assertIn("improved_construction_discount", prices)
        for price in prices + ["printed"]:
            found.setdefault(("price", price), set()).add("catalog.cpp")
        listed = lambda pair: f"value:{pair[0]}:{pair[1]}" in self.action_columns or pair[1] in self.places
        self.assertEqual(self.missing({f"{k}={w}": f for (k, w), f in found.items()},
                                      lambda text: listed(tuple(text.split("=")))), [])

    def test_battle_stages(self):
        found = {}
        for name, text in self.battle_sources.items():
            for match in re.finditer(r'\bstage\s*(?:=|==|!=)\s*"([a-z_0-9]+)"', text):
                found.setdefault(match.group(1), set()).add(name)
        self.assertGreater(len(found), 40)
        self.assertEqual(self.missing(found, lambda stage: f"battle_stage:{stage}" in self.zone_columns), [])


if __name__ == "__main__":
    unittest.main()
