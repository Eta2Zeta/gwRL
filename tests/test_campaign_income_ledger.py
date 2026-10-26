"""Native accounting oracle and exact device-only ledger state updates."""
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

from studies.campaign.backends.income_kernel import INVALID_IPP, OK
from studies.campaign.backends.income_ledger import (
    COLLECTION_OVERFLOW, CURRENT_NATION_ABSENT, INVALID_LEDGER_INPUT, IncomeLedgerTensorContext,
)

SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"


def context():
    return SimpleNamespace(definition_fingerprint="ledger-fixture", territory_ids=("capital", "invalid"),
        nation_ids=("japan", "minor"), int_minimum=-(2**31), int_maximum=2**31-1,
        territory_array=lambda: np.array([[5, 1, 0], [0, 0, 0]], dtype=np.int64),
        nation_array=lambda: np.array([[1, 1], [0, 0]], dtype=np.int64))


def inputs(rows=1, device="cpu"):
    data = (
        torch.tensor([[[1, 0, 0, 0], [1, 1, 0, 0]]], dtype=torch.int64),
        torch.tensor([[[1, 1, 1, 0, 1, 0], [1, 0, 0, 0, 0, -1]]], dtype=torch.int64),
        torch.tensor([[[10, 0], [0, 0]]], dtype=torch.int64),
        torch.tensor([[[[1, -7], [0, 0], [1, 37]], [[1, 8], [0, 0], [1, -9]]]], dtype=torch.int64),
        torch.tensor([[0, 0]], dtype=torch.int64),
    )
    return [value.repeat((rows,) + (1,) * (value.ndim - 1)).to(device) for value in data]


IDS = ("territorial", "china_control_bonus", "old_custom_component")


class IncomeLedgerTensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def test_collection_refreshes_all_ledgers_and_second_application_does_not_pay(self):
        kernel = IncomeLedgerTensorContext(context())
        original = inputs()
        copies = [value.clone() for value in original]
        result = kernel.compute(*original, IDS)
        self.assertEqual(result.error.tolist(), [OK])
        self.assertEqual(result.ledger.tolist(), [[[15, 1], [0, 1]]])
        self.assertEqual(result.clock.tolist(), [[0, 1]])
        self.assertEqual(result.components.tolist(), [[[[1, 5], [1, 0], [0, 0]], [[0, 0], [0, 0], [0, 0]]]])
        second = kernel.compute(original[0], original[1], result.ledger, result.components, result.clock, IDS)
        for name in ("error", "ledger", "components", "clock"):
            self.assertTrue(torch.equal(getattr(second, name), getattr(result, name)))
        for before, after in zip(copies, original, strict=True):
            self.assertTrue(torch.equal(before, after))
        inspected = kernel.inspect(result)[0]
        self.assertEqual(inspected["nations"]["japan"]["treasury"], 15)
        self.assertEqual(inspected["nations"]["minor"]["income_components"], {})

    def test_optional_zero_absent_surrendered_and_lost_capital_accounts(self):
        kernel = IncomeLedgerTensorContext(context())
        t, n, ledger, components, clock = inputs(5)
        ledger[0, 0, 0] = 0  # Zero cash is still an income account.
        ledger[1, 0, 0] = 0; n[1, 0, 1] = 0  # Absent account.
        n[2, 0, 3] = 1  # Surrendered identity.
        t[3, 0, 1] = 1  # Major's existing capital is held by someone else.
        clock[4, 0] = 1  # Non-account minor is still marked finished.
        result = kernel.compute(t, n, ledger, components, clock, IDS)
        self.assertEqual(result.error.tolist(), [OK] * 5)
        self.assertEqual(result.ledger[:, 0, 0].tolist(), [5, 0, 10, 10, 10])
        self.assertEqual(result.clock[:, 1].tolist(), [1] * 5)
        inspected = kernel.inspect(result)
        self.assertIsNone(inspected[1]["nations"]["japan"]["treasury"])
        self.assertEqual(inspected[0]["nations"]["japan"]["treasury"], 5)

    def test_overflow_and_refresh_error_rollback_every_field_in_only_failed_lanes(self):
        kernel = IncomeLedgerTensorContext(context())
        data = inputs(3)
        data[2][1:, 0, 0] = 2**31-1
        data[1][2, 1, 1:3] = 1  # Eligible minor-major owns invalid IPP.
        result = kernel.compute(*data, IDS)
        self.assertEqual(result.error.tolist(), [OK, COLLECTION_OVERFLOW, INVALID_IPP])
        for lane in (1, 2):
            for field, before in ((result.ledger, data[2]), (result.components, data[3]), (result.clock, data[4])):
                self.assertTrue(torch.equal(field[lane], before[lane]))
        self.assertEqual(result.error_nations.tolist(), [0, 0, 1])
        with self.assertRaisesRegex(RuntimeError, "IPP overflow"):
            kernel.inspect(kernel.compute(*(value[1:2] for value in data), IDS))

    def test_absent_current_nation_and_absent_other_nation_keep_distinct_behavior(self):
        kernel = IncomeLedgerTensorContext(context())
        data = inputs(2)
        data[1][0, 1, 0] = 0
        data[1][1, 0, 0] = 0
        result = kernel.compute(*data, IDS)
        self.assertEqual(result.error.tolist(), [OK, CURRENT_NATION_ABSENT])
        self.assertTrue(torch.equal(result.components[0, 1], data[3][0, 1]))
        self.assertTrue(torch.equal(result.ledger[1], data[2][1]))

    def test_native_integer_domains_layouts_and_component_identities_are_checked(self):
        kernel = IncomeLedgerTensorContext(context())
        data = inputs(3)
        data[0][0, 0, 2] = -(2**63)
        data[2][1, 0, 0] = 2**63-1
        data[4][2, 1] = 2
        result = kernel.compute(*data, IDS)
        self.assertEqual(result.error.tolist(), [INVALID_LEDGER_INPUT] * 3)
        for result_field, old in ((result.ledger, data[2]), (result.components, data[3]), (result.clock, data[4])):
            self.assertTrue(torch.equal(result_field, old))
        with self.assertRaises(ValueError): kernel.compute(*inputs(), ("territorial", "territorial", "x"))
        bad = inputs(); bad[2] = bad[2].float()
        with self.assertRaises(ValueError): kernel.compute(*bad, IDS)
        bad = inputs(); bad[4] = bad[4][:, :1]
        with self.assertRaises(ValueError): kernel.compute(*bad, IDS)

    def test_resident_compute_uses_no_host_scalar_reads_and_accepts_strided_arrays(self):
        kernel = IncomeLedgerTensorContext(context())
        data = [value.repeat_interleave(2, dim=-1)[..., ::2] for value in inputs(2)]
        with patch.object(torch.Tensor, "item", side_effect=AssertionError("host item")), \
                patch.object(torch.Tensor, "tolist", side_effect=AssertionError("host list")), \
                patch.object(torch.Tensor, "cpu", side_effect=AssertionError("host transfer")), \
                patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("host scalar")):
            result = kernel.compute(*data, IDS)
        self.assertEqual(result.ledger[:, 0, 0].tolist(), [15, 15])

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_mps_matches_cpu_for_success_errors_strides_and_empty_batches(self):
        cpu, gpu = IncomeLedgerTensorContext(context()), IncomeLedgerTensorContext(context(), "mps")
        data = inputs(4)
        data[2][1, 0, 0] = 2**31-1
        data[4][2, 1] = 1
        data[1][3, 0, 1] = 0
        for values in (data, [value[:0] for value in data]):
            expected = cpu.compute(*values, IDS)
            actual = gpu.compute(*(value.to("mps") for value in values), IDS)
            for field in ("error", "error_nations", "ledger", "components", "clock"):
                self.assertTrue(torch.equal(getattr(expected, field), getattr(actual, field).cpu()))


class NativeIncomeLedgerTests(unittest.TestCase):
    def oracle_matches(self, envs, device="cpu"):
        context = gwrl_cpp.campaign_income_context(envs[0])
        before = [env.serialize() for env in envs]
        kernel = IncomeLedgerTensorContext(context, device)
        with patch.object(json, "loads", side_effect=AssertionError("Input JSON route")):
            batch = gwrl_cpp.capture_campaign_income_ledger(context, envs)
            oracle = gwrl_cpp.campaign_income_ledger_oracle(context, envs)
            result = kernel.capture(batch)
        classes = np.array([0, 1, 1, 2, 3, 1, 2, 1, 3], dtype=np.int64)
        np.testing.assert_array_equal(classes[result.error.cpu().numpy()], oracle.error_array())
        self.assertEqual(tuple(batch.component_ids), tuple(oracle.after.component_ids))
        for actual, expected in ((result.ledger, oracle.after.ledger_array()),
                                 (result.components, oracle.after.component_array()),
                                 (result.clock, oracle.after.clock_array())):
            np.testing.assert_array_equal(actual.cpu().numpy(), expected)
        self.assertEqual([env.serialize() for env in envs], before)
        return kernel, batch, oracle, result

    @staticmethod
    def changed(env, mutate):
        document = json.loads(env.serialize())
        mutate(document["state"])
        out = env.clone()
        out.restore(json.dumps(document))
        return out

    def test_native_helper_matches_real_opening_and_custom_ledgers_without_state_or_rng_writes(self):
        first = gwrl_cpp.CampaignEnv(str(SCENARIO), 91)
        current = first.current_nation()
        def customize(state):
            for value in state["nations"].values():
                value["income_known"] = False
                value["income_components"] = {"old_custom_component": -19, "territorial": 9}
            state["nations"][current]["treasury"] = 0
        custom = self.changed(first, customize)
        kernel, _, _, result = self.oracle_matches([first, custom])
        self.assertTrue(all(row["income_collected"] for row in kernel.inspect(result)))
        self.assertTrue(all(nation["income_known"] for row in kernel.inspect(result) for nation in row["nations"].values()))

    def test_native_overflow_rollback_preserves_old_components_and_already_collected_does_not_error(self):
        first = gwrl_cpp.CampaignEnv(str(SCENARIO), 1)
        current = first.current_nation()
        def overflow(state):
            state["nations"][current]["treasury"] = 2**31-1
            state["nations"][current]["income_components"] = {"preserved_on_error": 23}
        bad = self.changed(first, overflow)
        def collected(state):
            overflow(state)
            state["clock"]["phase"] = "place_units"
            state["clock"]["income_collected"] = True
        paid = self.changed(first, collected)
        _, batch, oracle, result = self.oracle_matches([bad, paid])
        self.assertEqual(result.error.tolist(), [COLLECTION_OVERFLOW, OK])
        self.assertEqual(oracle.error_array().tolist(), [2, 0])
        np.testing.assert_array_equal(result.components[0].numpy(), batch.component_array()[0])

    def test_native_export_buffers_are_immutable_and_own_their_lifetime(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 7)
        context = gwrl_cpp.campaign_income_context(env)
        batch = gwrl_cpp.capture_campaign_income_ledger(context, [env])
        arrays = [batch.ledger_array(), batch.component_array(), batch.clock_array(), batch.income_inputs.nation_array()]
        expected = [value.copy() for value in arrays]
        self.assertIs(batch.context, context)
        del batch, context, env
        gc.collect()
        for value, original in zip(arrays, expected, strict=True):
            self.assertFalse(value.flags.writeable)
            self.assertTrue(value.flags.c_contiguous)
            with self.assertRaises(ValueError): value.setflags(write=True)
            np.testing.assert_array_equal(value, original)

    def test_native_zero_lanes_and_definition_mismatch_are_explicit(self):
        env = gwrl_cpp.CampaignEnv(str(SCENARIO), 1)
        context = gwrl_cpp.campaign_income_context(env)
        empty = gwrl_cpp.capture_campaign_income_ledger(context, [])
        result = IncomeLedgerTensorContext(context).capture(empty)
        self.assertEqual(tuple(result.ledger.shape), (0, 13, 2))
        self.assertEqual(tuple(result.clock.shape), (0, 2))
        other = gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO), 3, 1)
        with self.assertRaises(ValueError): gwrl_cpp.capture_campaign_income_ledger(context, [other])

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_native_oracle_matches_mps(self):
        self.oracle_matches([gwrl_cpp.CampaignEnv(str(SCENARIO), 1)], "mps")


if __name__ == "__main__":
    unittest.main()
