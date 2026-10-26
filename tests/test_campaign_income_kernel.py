"""Direct native income buffers and exact portable integer evaluation."""
from __future__ import annotations

import gc
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.income_kernel import (
    CAPITAL_TERRITORY_ABSENT, INT_OVERFLOW, INVALID_IPP, NATION_ABSENT, OK,
    TERRITORY_ABSENT, IncomeTensorContext,
)

SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"


def small_context():
    # Deliberately includes a missing base IPP field and a zero-valued bonus zone.
    return SimpleNamespace(definition_fingerprint="fixture", territory_ids=("capital", "bonus", "invalid"),
        nation_ids=("japan", "minor"), int_minimum=-(2 ** 31), int_maximum=2 ** 31 - 1,
        territory_array=lambda: np.array([[5, 1, 0], [0, 1, 1], [0, 0, 0]], dtype=np.int64),
        nation_array=lambda: np.array([[1, 1], [0, 0]], dtype=np.int64))


def small_inputs(rows=1):
    territories = torch.tensor([[[1, 0, 0, 0], [1, 0, 0, 0], [1, 1, 0, 0]]], dtype=torch.int64).repeat(rows, 1, 1)
    nations = torch.tensor([[[1, 1, 1, 0, 1, 0], [1, 1, 0, 0, 0, -1]]], dtype=torch.int64).repeat(rows, 1, 1)
    return territories, nations


class CampaignIncomeKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def assert_oracle(self, kernel, batch, oracle):
        result = kernel.capture(batch)
        actual, effective = result.income.cpu().numpy(), result.effective.cpu().numpy()
        errors = result.effective_error.cpu().numpy()
        native, native_effective = oracle.income_array(), oracle.effective_array()
        classes = np.array([0, 1, 1, 2, 3, 1], dtype=np.int64)
        np.testing.assert_array_equal(classes[actual[:, :, 0]], native[:, :, 0])
        good = native[:, :, 0] == 0
        np.testing.assert_array_equal(actual[:, :, 1:][good], native[:, :, 1:][good])
        np.testing.assert_array_equal(classes[errors], native_effective[:, :, 0])
        good = native_effective[:, :, 0] == 0
        np.testing.assert_array_equal(effective[good], native_effective[:, :, 1][good])
        return result

    def native_lanes(self):
        first = gwrl_cpp.CampaignEnv(str(SCENARIO), 91)
        later = first.clone()
        for _ in range(4):
            later.apply_action(next(a for a in later.legal_actions() if a.kind == "end_phase"))
        later.apply_action(next(a for a in later.legal_actions() if a.kind == "recruitment_roll"))
        self.assertEqual(later.decision_kind(), "chance")
        resolved = later.clone()
        resolved.resolve_chance()
        return [first, later, resolved]

    def test_native_capture_matches_existing_oracle_in_opening_later_and_chance_states_read_only(self):
        lanes = self.native_lanes()
        before = [env.serialize() for env in lanes]
        keys = [env.planning_key() for env in lanes]
        context = gwrl_cpp.campaign_income_context(lanes[0])
        kernel = IncomeTensorContext(context)
        with patch.object(json, "loads", side_effect=AssertionError("Input JSON route")):
            batch = gwrl_cpp.capture_campaign_income(context, lanes)
            oracle = gwrl_cpp.campaign_income_oracle(context, lanes)
            result = self.assert_oracle(kernel, batch, oracle)
        self.assertEqual([env.serialize() for env in lanes], before)
        self.assertEqual([env.planning_key() for env in lanes], keys)
        self.assertIs(batch.context, context)
        self.assertEqual(batch.territory_array().shape, (3, 37, 4))
        self.assertEqual(batch.nation_array().shape, (3, 13, 6))
        japan = kernel.inspect_income(result, [(0, "japan")])[0]
        self.assertEqual(japan["total"], 15)
        self.assertEqual(japan["components"], {"territorial": 15, "china_control_bonus": 0})

    def test_native_buffers_are_immutable_owning_views_and_share_context(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 1)
        context = gwrl_cpp.campaign_income_context(env)
        batch = gwrl_cpp.capture_campaign_income(context, [env, env.clone()])
        static, dynamic = context.territory_array(), batch.territory_array()
        expected_static, expected_dynamic = static.copy(), dynamic.copy()
        for array in (static, dynamic, context.nation_array(), batch.nation_array()):
            self.assertEqual(array.dtype, np.int64)
            self.assertTrue(array.flags.c_contiguous)
            self.assertFalse(array.flags.writeable)
            with self.assertRaises(ValueError): array.setflags(write=True)
        del batch, context, env
        gc.collect()
        np.testing.assert_array_equal(static, expected_static)
        np.testing.assert_array_equal(dynamic, expected_dynamic)

    def test_native_definition_mismatch_rejected_without_changing_either_state(self):
        original = gwrl_cpp.CampaignEnv(str(SCENARIO), 1)
        different = gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO), 3, 1)
        before = different.serialize(), original.serialize()
        context = gwrl_cpp.campaign_income_context(original)
        with self.assertRaises(ValueError): gwrl_cpp.capture_campaign_income(context, [original, different])
        self.assertEqual((different.serialize(), original.serialize()), before)
        kernel = IncomeTensorContext(context)
        other_context = gwrl_cpp.campaign_income_context(different)
        with self.assertRaises(ValueError): kernel.capture(gwrl_cpp.capture_campaign_income(other_context, [different]))

    def test_zero_lane_batch_is_not_truncated_or_fabricated(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 1)
        context = gwrl_cpp.campaign_income_context(env)
        result = self.assert_oracle(IncomeTensorContext(context), gwrl_cpp.capture_campaign_income(context, []),
                                    gwrl_cpp.campaign_income_oracle(context, []))
        self.assertEqual(tuple(result.income.shape), (0, 13, 6))

    def test_early_out_masks_errors_and_keeps_empty_components(self):
        kernel = IncomeTensorContext(small_context())
        t, n = small_inputs(4)
        t[:, 2, 1] = 0  # Japan owns the invalid-IPP territory.
        n[:, 0, 5] = -1  # Invalid capital reference too.
        n[0, 0, 1] = 0  # No treasury.
        n[1, 0, 3] = 1  # Surrendered.
        n[2, 0, 0] = 0  # Absent nation must still error first.
        result = kernel.compute(t, n)
        self.assertEqual(result.income[:, 0, 0].tolist(), [OK, OK, NATION_ABSENT, CAPITAL_TERRITORY_ABSENT])
        self.assertEqual(result.income[:2, 0, 1:].tolist(), [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0]])
        self.assertEqual(kernel.inspect_income(result, [(0, "japan")])[0]["components"], {})

    def test_major_capital_map_absent_and_unowned_retain_components_but_missing_territory_errors(self):
        kernel = IncomeTensorContext(small_context())
        t, n = small_inputs(4)
        n[0, 0, 4] = 0  # No map entry, with otherwise invalid referenced index.
        n[0, 0, 5] = -1
        t[1, 0, 1] = 1  # Existing capital held by the other nation.
        t[2, 0, 0] = 0  # Referenced capital absent from state.
        n[3, 0, 2] = 0  # Nonmajor ignores a missing capital.
        n[3, 0, 5] = -1
        result = kernel.compute(t, n)
        self.assertEqual(result.income[:, 0, 0].tolist(), [OK, OK, CAPITAL_TERRITORY_ABSENT, OK])
        for lane, territorial in ((0, 5), (1, 0)):
            inspected = kernel.inspect_income(result, [(lane, "japan")])[0]
            self.assertFalse(inspected["collectable"])
            self.assertEqual(inspected["total"], 0)
            self.assertEqual(inspected["components"], {"territorial": territorial, "china_control_bonus": 1})
        self.assertTrue(kernel.inspect_income(result, [(3, "japan")])[0]["collectable"])

    def test_signed_damage_division_and_noncity_flags_are_exact(self):
        kernel = IncomeTensorContext(small_context())
        damage = [-40, -39, -20, -19, 0, 19, 20, 39, 40]
        t, n = small_inputs(len(damage))
        t[:, 0, 2] = -3
        t[:, 0, 3] = torch.tensor(damage)
        result = kernel.compute(t, n)
        self.assertEqual(result.effective[:, 0].tolist(), [7, 6, 6, 5, 5, 5, 4, 4, 3])
        self.assertEqual(result.effective_error[:, 0].tolist(), [OK] * len(damage))

    def test_dynamic_major_accounts_and_exact_national_ownership(self):
        kernel = IncomeTensorContext(small_context())
        t, n = small_inputs(3)
        t[:, 2, 0] = 0  # Remove deliberately invalid fixture territory.
        t[:, 1, 1] = 1  # Minor/controller possession never gives Japan bonus.
        n[1, 1, 2] = 1
        n[1, 1, 4:] = torch.tensor([1, 1])
        n[2, 1, 2] = 1
        n[2, 1, 4:] = torch.tensor([1, 1])
        n[2, 1, 1] = 0
        result = kernel.compute(t, n)
        self.assertEqual(result.income[:, 1, 1].tolist(), [0, 1, 0])
        self.assertEqual(result.income[:, 0, 4].tolist(), [0, 0, 0])
        self.assertEqual(result.income[1, 1, 2].item(), 1)

    def test_lazy_invalid_ipp_and_undefined_native_integer_overflow_rejected(self):
        context = small_context()
        context.territory_array = lambda: np.array([[2 ** 31 - 3, 1, 0], [0, 1, 1], [0, 0, 0]], dtype=np.int64)
        kernel = IncomeTensorContext(context)
        t, n = small_inputs(4)
        t[0, 2, 1] = 0  # Owned invalid field.
        t[1, 2, 0] = 0  # Absent invalid field is ignored by income.
        t[2, 0, 2:] = torch.tensor([-3, -60])  # Representable native int inputs; subtraction overflows.
        t[3, :2, 2:] = torch.tensor([-1, -20])  # Each effective value fits; components sum overflows.
        result = kernel.compute(t, n)
        self.assertEqual(result.income[:, 0, 0].tolist(), [INVALID_IPP, OK, INT_OVERFLOW, INT_OVERFLOW])
        self.assertEqual(result.effective_error[1, 2].item(), TERRITORY_ABSENT)
        with self.assertRaises(RuntimeError): kernel.inspect_income(result, [(0, "japan")])
        with self.assertRaises(OverflowError): kernel.inspect_income(result, [(2, "japan")])
        with self.assertRaises(IndexError): kernel.inspect_effective(result, [(1, "invalid")])

    def test_shapes_dtypes_and_explicit_inspection_queries_are_validated(self):
        kernel = IncomeTensorContext(small_context())
        t, n = small_inputs()
        for bad_t, bad_n in ((t.float(), n), (t[:, :2], n), (t, n[:, :1]), (t.repeat(2, 1, 1), n)):
            with self.assertRaises(ValueError): kernel.compute(bad_t, bad_n)
        result = kernel.compute(t, n)
        for query in ((-1, "japan"), (1, "japan"), (True, "japan"), (0, "unknown")):
            with self.assertRaises(IndexError): kernel.inspect_income(result, [query])
        with self.assertRaises(ValueError): IncomeTensorContext(small_context(), "meta")

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_mps_int64_native_batches_and_signed_error_boundaries_match_cpu_exactly(self):
        lanes = self.native_lanes()
        before = [env.serialize() for env in lanes]
        context = gwrl_cpp.campaign_income_context(lanes[0])
        batch, oracle = gwrl_cpp.capture_campaign_income(context, lanes), gwrl_cpp.campaign_income_oracle(context, lanes)
        self.assert_oracle(IncomeTensorContext(context, "mps"), batch, oracle)
        cpu, mps = IncomeTensorContext(small_context()), IncomeTensorContext(small_context(), "mps")
        t, n = small_inputs(12)
        t[:9, 0, 2] = -3
        t[:9, 0, 3] = torch.tensor([-40, -39, -20, -19, 0, 19, 20, 39, 40])
        t[9, 2, 1] = 0
        t[10, 0, 2:] = torch.tensor([-3, -60])
        t[11, :2, 2:] = torch.tensor([-1, -20])
        a, b = cpu.compute(t, n), mps.compute(t.to(mps.device), n.to(mps.device))
        torch.mps.synchronize()
        for name in ("income", "effective", "effective_error"):
            self.assertTrue(torch.equal(getattr(a, name), getattr(b, name).cpu()), name)
        high = small_context()
        high.territory_array = lambda: np.array([[2 ** 31 - 3, 1, 0], [0, 1, 1], [0, 0, 0]], dtype=np.int64)
        high_cpu, high_mps = IncomeTensorContext(high), IncomeTensorContext(high, "mps")
        a, b = high_cpu.compute(t, n), high_mps.compute(t.to(high_mps.device), n.to(high_mps.device))
        torch.mps.synchronize()
        for name in ("income", "effective", "effective_error"):
            self.assertTrue(torch.equal(getattr(a, name), getattr(b, name).cpu()), name)
        self.assertEqual(a.income[10:, 0, 0].tolist(), [INT_OVERFLOW, INT_OVERFLOW])
        self.assertEqual([env.serialize() for env in lanes], before)


if __name__ == "__main__":
    unittest.main()
