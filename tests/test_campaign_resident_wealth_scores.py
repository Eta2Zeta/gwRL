"""Native-bit score arithmetic, including fused rounding and terminal targets."""
import json
import math
from pathlib import Path
import random
import struct
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_wealth_scores import native_wealth_scores
from tests.test_campaign_resident_wealth import ResidentWealthTests, bare, changed

EXACT_MPS = torch.backends.mps.is_available() and mps_int64_indexing_supported()
SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"


def bits(value):
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def python_scores(rows, terminal):
    wealth, gaps, returns, targets = [], [], [], []
    for row, finished in zip(rows, terminal, strict=True):
        values = []
        for player in row:
            x = [float(value) * .5 for value in player]
            values.append(math.fma(.1, ((x[1] + x[2]) + x[3]) + x[4], x[0]))
        total = (values[0] + values[1]) + values[2]
        gap = [2 * value - total for value in values]
        result = gap if finished else [0.] * 3
        wealth.append([bits(value) for value in values]);gaps.append([bits(value) for value in gap])
        returns.append([bits(value) for value in result])
        targets.append(np.asarray(result, dtype=np.float32).view(np.uint32).tolist())
    return dict(wealth_bits=wealth, gap_bits=gaps, terminal_bits=returns, terminal_float32_bits=targets)


@unittest.skipUnless(EXACT_MPS, "Lossless Apple GPU runtime unavailable")
class ResidentWealthScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000 / torch.mps.recommended_max_memory())

    @classmethod
    def tearDownClass(cls):
        torch.mps.empty_cache();torch.set_num_threads(cls.old_threads)

    def evaluate(self, rows, terminal):
        count = len(rows)
        components = torch.tensor(rows, dtype=torch.int64, device="mps").reshape(count, 3, 5)
        zero = torch.zeros(count, dtype=torch.int64, device="mps")
        return native_wealth_scores(components, zero, zero, torch.tensor(terminal, dtype=torch.int64, device="mps"))

    def assert_bits(self, result, expected):
        self.assertEqual(result.errors.cpu().tolist(), [0] * len(expected["wealth_bits"]))
        self.assertEqual(result.terminal_errors.cpu().tolist(), [0] * len(expected["wealth_bits"]))
        for name in ("wealth_bits", "gap_bits", "terminal_bits"):
            actual = getattr(result, name).cpu().numpy().view(np.uint64)
            np.testing.assert_array_equal(actual, np.asarray(expected[name], dtype=np.uint64).reshape(-1, 3), name)
        np.testing.assert_array_equal(result.terminal_targets.cpu().numpy().view(np.uint32),
            np.asarray(expected["terminal_float32_bits"], dtype=np.uint32).reshape(-1, 3))

    def test_integer_metal_matches_python_fma_full_component_domain(self):
        generator = random.Random(17431)
        edges = [0, 1, -1, 2**53-1, 2**53, 2**53+1, -(2**53+1), 2**63-1, -2**63]
        rows = [[[2 * income, assets, 0, 0, 0], [0]*5, [0]*5]
                for income in range(-20, 21) for assets in range(-100, 101)]
        for _ in range(4096):
            rows.append([[generator.choice(edges) if generator.randrange(3) else generator.randrange(-2**63, 2**63)
                          for _ in range(5)] for _ in range(3)])
        terminal = [index % 3 != 0 for index in range(len(rows))]
        result = self.evaluate(rows, terminal)
        self.assert_bits(result, python_scores(rows, terminal))
        native = gwrl_cpp.campaign_wealth_scores_probe([sum(row, []) for row in rows], terminal)
        self.assert_bits(result, native)

    def test_native_fused_rounding_probe_and_float32_ties(self):
        # 1 + .1*7 is 1.7000000000000002 unfused and 1.7 fused.
        rows = [[[2, 14, 0, 0, 0], [2, -20, 0, 0, 0], [0]*5]]
        for number in (2**24-1, 2**24+1, -(2**24+1), 2**53+1, 2**63-1):
            rows.append([[2 * (number // 2), 1, 0, 0, 0], [0, number, 0, 0, 0], [0]*5])
        terminal = [True] * len(rows)
        expected = gwrl_cpp.campaign_wealth_scores_probe([sum(row, []) for row in rows], terminal)
        self.assertEqual(expected["wealth_bits"][0][0], bits(1.7))
        self.assertNotEqual(bits(1.7), bits(1.+.1*7.))
        self.assert_bits(self.evaluate(rows, terminal), expected)

    def test_real_state_native_scores_and_read_only_hot_path(self):
        fixture = ResidentWealthTests()
        first = gwrl_cpp.CampaignEnv(str(SCENARIO), 17)
        cleared = bare(first)
        def finish(state):
            state.update(terminal=True, decisions=[], chance=None, battles={}, battle_order=[])
            state["clock"].update(round_index=10, nation_index=3, phase="place_units", completed_rounds=11,
                                  player_turn_serial="44", income_collected=True)
            state["completed_turns"] = {key:11 for key in state["completed_turns"]}
        terminal = changed(cleared, finish)
        def damage(state):
            state["facilities"]["damaged-factory"] = dict(id="damaged-factory", type="major_factory",
                zone="land_jap_honshu", damage=20, flags={})
        damaged = changed(cleared, damage)
        envs = [first, cleared, terminal, damaged]
        state, context, native = fixture.setup(envs)
        oracle = gwrl_cpp.campaign_wealth_oracle(native, envs)
        components = context.evaluate(state)
        context.scores(components)
        before = [env.serialize() for env in envs]
        with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Host read")), \
                patch.object(torch.Tensor, "item", side_effect=AssertionError("Host read")), \
                patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Host read")), \
                patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("Host read")), \
                patch.object(gwrl_cpp, "campaign_wealth_oracle", side_effect=AssertionError("Native fallback")), \
                patch.object(json, "loads", side_effect=AssertionError("JSON fallback")):
            result = context.scores(components)
        expected = {name: array.view(np.uint64).tolist() for name, array in (
            ("wealth_bits", oracle.wealth_array()), ("gap_bits", oracle.gap_array()),
            ("terminal_bits", oracle.terminal_array()))}
        expected["terminal_float32_bits"] = oracle.terminal_array().astype(np.float32).view(np.uint32).tolist()
        self.assert_bits(result, expected)
        self.assertEqual([env.serialize() for env in envs], before)

    def test_error_propagation_empty_batches_and_layout_rejection(self):
        result = self.evaluate([], [])
        self.assertEqual(tuple(result.wealth_bits.shape), (0, 3))
        values = torch.zeros((2, 3, 5), dtype=torch.int64, device="mps")
        errors = torch.tensor([2, 3], dtype=torch.int64, device="mps")
        terminals = torch.tensor([0, 1], dtype=torch.int64, device="mps")
        result = native_wealth_scores(values, errors, errors, terminals)
        self.assertEqual(result.errors.cpu().tolist(), [2, 3])
        self.assertEqual(result.terminal_errors.cpu().tolist(), [2, 3])
        with self.assertRaises(ValueError):native_wealth_scores(values.cpu(), errors, errors, terminals)
        with self.assertRaises(ValueError):native_wealth_scores(values[:,:,::2], errors, errors, terminals)


if __name__ == "__main__":
    unittest.main()
