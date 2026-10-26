"""Resident arena edits preserve every unmodified field and reject truncation."""
from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.device_state import DeviceStateBatch
from studies.campaign.backends.device_state_edits import EditError, replace_subtrees
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported

SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"
EXACT_MPS = torch.backends.mps.is_available() and mps_int64_indexing_supported()


def scalar(tag, value=0):
    if tag in (2, 3):
        bits = value & ((1 << 64) - 1)
        return [tag, 0, bits & 0xffffffff, bits >> 32, 1]
    return [tag, value, 0, 0, 1]


def tape(values):
    return [[6, len(values), 0, 0, 1 + len(values)],
            *[[*scalar(2, value)[:4], index + 2] for index, value in enumerate(values)]]


def fixture(device="cpu", count=1):
    env = gwrl_cpp.CampaignEnv(str(SCENARIO), 31, training_actions=True)
    envs = [env] + [env.clone() for _ in range(count - 1)]
    return DeviceStateBatch.capture(envs, device=device), envs


def arguments(state, section, rows, selected=None):
    B = state.lane_count
    roots = state.section(section).contiguous()
    blocks = torch.tensor([rows] * B, dtype=torch.int64, device=state.device).contiguous()
    sizes = torch.full((B,), len(rows), dtype=torch.int64, device=state.device)
    mask = torch.ones(B, dtype=torch.bool, device=state.device) if selected is None else selected
    return roots, blocks, sizes, mask


def expected_change(env, *, random=None):
    value = json.loads(env.serialize())
    value["random"].update(random or {})
    clone = env.clone()
    clone.restore(json.dumps(value, separators=(",", ":")))
    return clone.serialize()


class CampaignDeviceStateEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def growth_roundtrip(self, device):
        state, envs = fixture(device)
        original = state.records.clone()
        args = arguments(state, "random.test_tape", tape([1, 2, 3]))
        failed = replace_subtrees(state, *args)
        self.assertEqual(failed.errors.cpu().tolist(), [int(EditError.CAPACITY)])
        self.assertFalse(failed.committed.cpu().item())
        self.assertTrue(torch.equal(failed.state.records, original))
        self.assertEqual(failed.required_capacity.cpu().tolist(), [state.records.shape[1] + 3])
        grown = replace_subtrees(state, *args, capacity=state.records.shape[1] + args[1].shape[1])
        self.assertEqual(grown.errors.cpu().tolist(), [0])
        self.assertTrue(grown.committed.cpu().item())
        self.assertEqual(grown.state.restore_envs()[0].serialize(), expected_change(envs[0], random={"test_tape": [1, 2, 3]}))
        self.assertTrue(torch.equal(state.records, original))
        # Engine and RandomStreams ancestors grow; the complete State stays put.
        self.assertEqual(grown.state.records[0, 0, 4].cpu().item(), state.records[0, 0, 4].cpu().item() + 3)
        self.assertEqual(grown.state.section("random.tape_position").cpu().item(), state.section("random.tape_position").cpu().item() + 3)
        self.assertTrue(torch.equal(state.section("state"), grown.state.section("state")))
        shrunk = replace_subtrees(grown.state, *arguments(grown.state, "random.test_tape", tape([])))
        self.assertEqual(shrunk.errors.cpu().tolist(), [0])
        self.assertEqual(shrunk.state.restore_envs()[0].serialize(), envs[0].serialize())

    def test_cpu_capacity_retry_growth_shrink_and_all_ancestor_section_offsets(self):
        self.growth_roundtrip("cpu")

    @unittest.skipUnless(EXACT_MPS, "Lossless MPS indexing unavailable")
    def test_mps_capacity_retry_growth_shrink_and_all_ancestor_section_offsets(self):
        self.growth_roundtrip("mps")

    def test_scalar_unsigned_all_bits_change_leaves_other_streams_state_and_history_exact(self):
        state, envs = fixture()
        result = replace_subtrees(state, *arguments(state, "random.search", [scalar(3, (1 << 64)-1)]))
        self.assertEqual(result.errors.tolist(), [0])
        self.assertEqual(result.state.restore_envs()[0].serialize(), expected_change(envs[0], random={"search": str((1 << 64)-1)}))
        self.assertTrue(torch.equal(state.sections, result.state.sections))

    @unittest.skipUnless(EXACT_MPS, "Lossless MPS indexing unavailable")
    def test_actual_mps_operation_has_no_host_state_reads_and_matches_cpu_reference(self):
        cpu, envs = fixture()
        mps = DeviceStateBatch.capture(envs, device="mps")
        rows = tape([1, 6, 12])
        expected = replace_subtrees(cpu, *arguments(cpu, "random.test_tape", rows), capacity=cpu.records.shape[1] + 4)
        args = arguments(mps, "random.test_tape", rows)
        with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Hot host transfer")), \
             patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Hot host values")), \
             patch.object(torch.Tensor, "item", side_effect=AssertionError("Hot host scalar")):
            actual = replace_subtrees(mps, *args, capacity=mps.records.shape[1] + 4)
        torch.mps.synchronize()
        for name in ("records", "lengths", "sections", "errors"):
            self.assertTrue(torch.equal(getattr(expected.state, name), getattr(actual.state, name).cpu()), name)
        self.assertTrue(torch.equal(expected.errors, actual.errors.cpu()))
        self.assertEqual(actual.state.restore_envs()[0].serialize(), expected.state.restore_envs()[0].serialize())

    def test_selected_cohort_rolls_back_all_lanes_on_one_invalid_block(self):
        state, _ = fixture(count=2)
        roots, blocks, sizes, selected = arguments(state, "random.search", [scalar(3, 91)])
        blocks[1, 0, 4] = 2
        result = replace_subtrees(state, roots, blocks, sizes, selected)
        self.assertEqual(result.errors.tolist(), [0, int(EditError.BLOCK)])
        self.assertEqual(result.accepted.tolist(), [False, False])
        self.assertTrue(torch.equal(result.state.records, state.records))
        self.assertTrue(torch.equal(result.state.sections, state.sections))
        selected[1] = False
        result = replace_subtrees(state, roots, blocks, sizes, selected)
        self.assertEqual(result.errors.tolist(), [0, 0])
        self.assertEqual(result.accepted.tolist(), [True, False])

    def test_malformed_tags_fields_string_ids_container_counts_and_targets_rejected(self):
        state, _ = fixture()
        cases = ([[99, 0, 0, 0, 1]], [[3, 1, 0, 0, 1]], [[3, 0, 1 << 32, 0, 1]],
                 [[6, 1, 0, 0, 1]], [[5, 1 << 30, 0, 0, 1]])
        for rows in cases:
            with self.subTest(rows=rows):
                result = replace_subtrees(state, *arguments(state, "random.search", rows))
                self.assertTrue(result.errors.item() & int(EditError.BLOCK))
                self.assertTrue(torch.equal(state.records, result.state.records))
        args = list(arguments(state, "random.search", [scalar(3, 1)])); args[0] = torch.tensor([-1])
        result = replace_subtrees(state, *args)
        self.assertEqual(result.errors.tolist(), [int(EditError.TARGET)])
        with self.assertRaises(ValueError): replace_subtrees(state, *arguments(state, "random.search", [scalar(3, 1)]), capacity=1)

    @unittest.skipUnless(EXACT_MPS, "Lossless MPS indexing unavailable")
    def test_whole_state_and_whole_engine_identity_replacements_validate_deep_nested_maps(self):
        from tests.test_campaign_device_state import rich_fixture
        envs = [rich_fixture()]
        state = DeviceStateBatch.capture(envs, device="mps")
        for name in ("state", "engine"):
            start = state.section("state").cpu().item() if name == "state" else 0
            end = state.records[0, start, 4].cpu().item()
            rows = state.records[0, start:end].cpu().clone()
            rows[:, 4] -= start
            blocks = rows.to(state.device).unsqueeze(0)
            roots = torch.tensor([start], dtype=torch.int64, device=state.device)
            sizes = torch.tensor([len(rows)], dtype=torch.int64, device=state.device)
            selected = torch.tensor([True], device=state.device)
            result = replace_subtrees(state, roots, blocks, sizes, selected)
            torch.mps.synchronize()
            self.assertEqual(result.errors.cpu().tolist(), [0])
            self.assertTrue(torch.equal(result.state.records, state.records))
            self.assertTrue(torch.equal(result.state.sections, state.sections))
            self.assertEqual(result.state.restore_envs()[0].serialize(), envs[0].serialize())

    def test_zero_selected_lanes_does_not_change_any_field(self):
        state, _ = fixture(count=2)
        args = arguments(state, "random.search", [[99, 0, 0, 0, 1]], torch.zeros(2, dtype=torch.bool))
        result = replace_subtrees(state, *args)
        self.assertEqual(result.errors.tolist(), [0, 0])
        self.assertTrue(torch.equal(result.state.records, state.records))
        self.assertTrue(torch.equal(result.state.lengths, state.lengths))


if __name__ == "__main__":
    unittest.main()
