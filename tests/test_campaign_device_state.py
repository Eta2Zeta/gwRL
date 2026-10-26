"""Lossless privileged snapshots: every field, choice, payload and RNG survives."""
from __future__ import annotations

import dataclasses
import gc
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext, SECTION_NAMES
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported

EXACT_MPS = torch.backends.mps.is_available() and mps_int64_indexing_supported()

SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"


def menu(env, interrupts=False):
    values = env.legal_interrupts() if interrupts else env.legal_actions()
    return [(a.id, a.kind, a.player, a.nation, a.decision, a.parameters) for a in values]


def real_states():
    opening = gwrl_cpp.CampaignEnv(str(SCENARIO), 91, training_actions=True)
    later = opening.clone()
    for _ in range(4):
        later.apply_action(next(a for a in later.legal_actions() if a.kind == "end_phase"))
    later.apply_action(next(a for a in later.legal_actions() if a.kind == "recruitment_roll"))
    resolved = later.clone()
    resolved.resolve_chance()
    return [opening, later, resolved]


def rich_fixture():
    # JSON is a TEST authoring/oracle boundary, never the production transfer.
    env = gwrl_cpp.CampaignEnv(str(SCENARIO), 17, training_actions=True)
    value = json.loads(env.serialize())
    state = value["state"]
    opaque = {"absent_is_different": None, "empty": {}, "array": [False, True, -0.0, 1.0000000000000002],
              "unicode": "蒙古 / Ma Clique / \u0000", "nested": {"finite": 1e200, "negative": -123.5}}
    state["politics"]["pending"]["device_opaque_fixture"] = opaque
    state["history"].append({"kind": "device_fixture", "payload": opaque, "after_state_key": "preserved-arbitrary-key"})
    state["flags"]["min_native_integer"] = -(2**31)
    state["flags"]["max_native_integer"] = 2**31 - 1
    state["nations"]["japan"]["treasury"] = 0
    state["nations"]["japan"]["turn_flags"]["custom_dynamic:flag"] = -17
    state["nations"]["japan"]["income_components"]["original_custom_component"] = -7
    state["territories"]["land_jap_tokyo"]["flags"]["city_damage"] = -39
    unit = next(iter(state["units"].values()))
    unit["route"] = [unit["zone"], unit["zone"]]
    unit["commitments"] = ["device_custom_commitment"]
    unit["turn_flags"]["custom_status"] = -3
    unit["game_flags"]["custom_status"] = 9
    state["construction"]["device_build"] = {"id": "device_build", "owner": "japan", "type": "infantry",
        "site": "land_jap_tokyo", "queue_position": 3, "paid_ipp": 2, "remaining_payments": [1, 2], "flags": {"custom": 3}}
    state["repairs"]["device_repair"] = {"id": "device_repair", "owner": "japan", "target": "land_jap_tokyo",
        "remaining_damage": 2, "remaining_cost": 1, "restricts_action": False, "endpoint": None}
    state["rails"]["device_rail"] = {"id": "device_rail", "endpoint_a": "land_china_shensi",
        "endpoint_b": "land_china_hopeh", "damage_by_endpoint": {"land_china_shensi": 2}}
    state["decisions"] = [{"id": "device_choice", "kind": "device_fixture_choice", "nation": "ccp",
        "reaction": True, "continuation": "device_opaque_fixture", "options": [
            {"id": "device_option", "kind": "device_fixture_option", "nation": "ccp", "player": "comintern",
             "decision": "device_choice", "parameters": opaque}]}]
    state["battles"]["device_battle"] = {"id": "device_battle", "zone": "land_china_shensi", "attacker": "ccp",
        "defender": "kmt", "stage": "device_fixture_stage", "attackers": [], "defenders": [],
        "pending_hits": {"kmt": 2}, "flags": {"negative_sentinel": -3}, "data": opaque}
    state["battle_order"] = ["device_battle"]
    value["random"].update(actual=str(2**64-1), search=str(2**63+17), training="0", active="search",
                            test_tape=[12, 1, 6], tape_position="1")
    env.restore(json.dumps(value, separators=(",", ":"), ensure_ascii=False))
    return env


class CampaignDeviceStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def assert_roundtrip(self, device):
        envs = real_states() + [rich_fixture()]
        original = [env.serialize() for env in envs]
        keys = [env.planning_key() for env in envs]
        menus = [(menu(env), menu(env, True)) for env in envs]
        context = gwrl_cpp.device_state_context(envs[0])
        with patch.object(json, "loads", side_effect=AssertionError("JSON input transfer")), \
             patch.object(json, "dumps", side_effect=AssertionError("JSON output transfer")):
            native = gwrl_cpp.capture_device_states(context, envs)
            resident = DeviceStateBatch.from_native(native, device=device)
            roundtrip = resident.to_native()
            restored = gwrl_cpp.restore_device_states(roundtrip)
        self.assertEqual([env.serialize() for env in envs], original)
        self.assertEqual([env.serialize() for env in restored], original)
        self.assertEqual([env.planning_key() for env in restored], keys)
        self.assertEqual([(menu(env), menu(env, True)) for env in restored], menus)
        np.testing.assert_array_equal(native.record_array(), roundtrip.record_array())
        np.testing.assert_array_equal(native.lane_offsets(), roundtrip.lane_offsets())
        np.testing.assert_array_equal(native.section_array(), roundtrip.section_array())
        np.testing.assert_array_equal(native.string_bytes(), roundtrip.string_bytes())
        self.assertEqual(tuple(native.section_names), SECTION_NAMES)
        again = gwrl_cpp.capture_device_states(context, restored)
        np.testing.assert_array_equal(native.record_array(), again.record_array())
        np.testing.assert_array_equal(native.string_bytes(), again.string_bytes())
        # No float64 device tensors: the negative-zero double keeps its raw bits.
        rows = native.record_array()
        self.assertTrue(np.any((rows[:, 0] == 4) & (rows[:, 2] == 0) & (rows[:, 3] == 0x80000000)))
        return resident, envs

    def test_cpu_complete_state_and_raw_rng_roundtrip_without_json_route(self):
        self.assert_roundtrip("cpu")

    @unittest.skipUnless(EXACT_MPS, "MPS exact int64 indexing unavailable; select tested GPU environment")
    def test_mps_complete_state_and_raw_rng_roundtrip_without_json_route(self):
        self.assert_roundtrip("mps")

    def test_device_forks_repeat_roots_independently_and_keep_shared_static_context(self):
        envs = real_states()
        resident = DeviceStateBatch.capture(envs)
        before = resident.records.clone()
        selected = torch.tensor([2, 0, 2, 1], dtype=torch.int64)
        with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Hot fork host transfer")), \
             patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Hot fork host values")), \
             patch.object(torch.Tensor, "item", side_effect=AssertionError("Hot fork host scalar")):
            child = resident.fork(selected)
            snapshot = child.snapshot()
        self.assertIs(child.context, resident.context)
        self.assertIs(child.string_bytes, resident.string_bytes)
        self.assertTrue(torch.equal(resident.records, before))
        self.assertNotEqual(child.records.data_ptr(), resident.records.data_ptr())
        self.assertNotEqual(snapshot.records.data_ptr(), child.records.data_ptr())
        restored = child.restore_envs()
        self.assertEqual([env.serialize() for env in restored], [envs[i].serialize() for i in selected.tolist()])
        child.records[0, 0, 0] = 999
        self.assertFalse(torch.equal(child.records[0], child.records[2]))
        self.assertTrue(torch.equal(resident.records, before))
        self.assertNotEqual(snapshot.records[0, 0, 0].item(), 999)

    @unittest.skipUnless(EXACT_MPS, "MPS exact int64 indexing unavailable; select tested GPU environment")
    def test_mps_fork_is_a_resident_gather_and_reports_invalid_device_indices(self):
        resident = DeviceStateBatch.capture(real_states(), device="mps")
        selected = torch.tensor([1, 1, -1, 4], device="mps", dtype=torch.int64)
        with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Hot fork host transfer")), \
             patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Hot fork host values")), \
             patch.object(torch.Tensor, "item", side_effect=AssertionError("Hot fork host scalar")):
            child = resident.fork(selected)
        torch.mps.synchronize()
        self.assertEqual(child.errors.cpu().tolist(), [0, 0, 1, 1])
        self.assertEqual(child.lengths.cpu().tolist()[2:], [0, 0])
        self.assertTrue(torch.equal(child.records[0], child.records[1]))
        with self.assertRaises(ValueError): child.to_native()
        with self.assertRaises(ValueError): resident.fork([-1])

    def test_buffers_are_immutable_owning_views_and_snapshot_capacity_is_not_a_rule_cap(self):
        env = rich_fixture()
        context = gwrl_cpp.device_state_context(env)
        native = gwrl_cpp.capture_device_states(context, [env])
        arrays = [context.record_array(), context.string_bytes(), context.string_offsets(),
                  native.record_array(), native.lane_offsets(), native.section_array(), native.string_bytes(), native.string_offsets()]
        expected = [value.copy() for value in arrays]
        for value in arrays:
            self.assertTrue(value.flags.c_contiguous)
            self.assertFalse(value.flags.writeable)
            with self.assertRaises(ValueError): value.setflags(write=True)
        del native, context, env
        gc.collect()
        for actual, value in zip(arrays, expected, strict=True): np.testing.assert_array_equal(actual, value)

    def test_native_decoder_rejects_unknown_fields_bad_types_offsets_and_subtrees(self):
        env = real_states()[0]
        context = gwrl_cpp.device_state_context(env)
        native = gwrl_cpp.capture_device_states(context, [env])
        arrays = [native.record_array().copy(), native.lane_offsets().copy(),
                  native.string_bytes().copy(), native.string_offsets().copy()]
        for column, value in ((0, 999), (1, 3), (4, len(arrays[0]) + 1)):
            modified = [a.copy() for a in arrays]; modified[0][0, column] = value
            with self.assertRaises(ValueError): gwrl_cpp.device_state_batch_from_packed(context, *modified, wire_context_fingerprint=context.wire_context_fingerprint)
        modified = [a.copy() for a in arrays]; modified[1][0] = 1
        with self.assertRaises(ValueError): gwrl_cpp.device_state_batch_from_packed(context, *modified, wire_context_fingerprint=context.wire_context_fingerprint)
        with self.assertRaises(ValueError): gwrl_cpp.device_state_batch_from_packed(context, arrays[0].astype(np.float64), *arrays[1:], wire_context_fingerprint=context.wire_context_fingerprint)
        resident = DeviceStateBatch.from_native(native)
        with self.assertRaises(ValueError): dataclasses.replace(resident, lengths=resident.lengths.float()).to_native()

    def test_native_string_pool_rejects_aliases_against_prefix_and_suffix(self):
        env = real_states()[0]
        context = gwrl_cpp.device_state_context(env)
        native = gwrl_cpp.capture_device_states(context, [env])
        data, lanes = native.record_array().copy(), native.lane_offsets().copy()
        original_bytes, offsets = native.string_bytes().copy(), native.string_offsets().copy()
        prefix_bytes, prefix_offsets = context.string_bytes(), context.string_offsets()
        self.assertGreater(len(offsets), 1)
        for repeated in (prefix_bytes[:prefix_offsets[1]], original_bytes[offsets[0]:offsets[1]]):
            extended = np.concatenate((original_bytes, repeated)).astype(np.uint8)
            extended_offsets = np.concatenate((offsets, np.array([len(extended)], dtype=np.int64)))
            with self.assertRaisesRegex(ValueError, "duplicate device string"):
                gwrl_cpp.device_state_batch_from_packed(context, data, lanes, extended, extended_offsets, context.wire_context_fingerprint)

    def test_zero_lane_and_definition_mismatch_do_not_fabricate_states(self):
        env = real_states()[0]
        context = DeviceStateContext(gwrl_cpp.device_state_context(env))
        empty = DeviceStateBatch.capture([], context=context)
        self.assertEqual(empty.lane_count, 0)
        self.assertEqual(empty.restore_envs(), [])
        self.assertEqual(empty.fork([]).lane_count, 0)
        different = gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO), 3, 91, training_actions=True)
        before = different.serialize()
        with self.assertRaises(ValueError): DeviceStateBatch.capture([different], context=context)
        self.assertEqual(different.serialize(), before)

    @unittest.skipUnless(EXACT_MPS, "MPS exact int64 indexing unavailable; select tested GPU environment")
    def test_explicit_device_never_silently_uses_a_different_shared_context(self):
        env = real_states()[0]
        native_context = gwrl_cpp.device_state_context(env)
        native = gwrl_cpp.capture_device_states(native_context, [env])
        cpu, mps = DeviceStateContext(native_context), DeviceStateContext(native_context, "mps")
        with self.assertRaisesRegex(ValueError, "Explicit device"):
            DeviceStateBatch.from_native(native, device="mps", context=cpu)
        with self.assertRaisesRegex(ValueError, "Explicit device"):
            DeviceStateBatch.capture([env], device="cpu", context=mps)
        self.assertEqual(DeviceStateBatch.from_native(native, context=mps).device.type, "mps")

    def test_wire_context_identity_and_fixed_protocol_strings_are_explicit(self):
        env = real_states()[0]
        context = gwrl_cpp.device_state_context(env)
        repeated = gwrl_cpp.device_state_context(env)
        self.assertEqual(context.wire_context_fingerprint, repeated.wire_context_fingerprint)
        names = ("actual", "search", "training", "territorial", "china_control_bonus", "major", "city_ipp_lost", "city_damage")
        ids = context.prefix_lookup_ids(names)
        self.assertEqual(len(set(ids.tolist())), len(names))
        with self.assertRaises(IndexError): context.prefix_lookup_ids(("unknown_fixed_protocol_string",))
        native = gwrl_cpp.capture_device_states(context, [env])
        with self.assertRaisesRegex(ValueError, "wire context mismatch"):
            gwrl_cpp.device_state_batch_from_packed(context, native.record_array(), native.lane_offsets(),
                native.string_bytes(), native.string_offsets(), "wrong-wire-context")

    def test_actual_future_chance_continues_from_identical_restored_streams(self):
        pending = real_states()[1]
        restored = DeviceStateBatch.capture([pending]).restore_envs()[0]
        pending.resolve_chance(); restored.resolve_chance()
        self.assertEqual(pending.serialize(), restored.serialize())
        self.assertEqual(menu(pending), menu(restored))


if __name__ == "__main__":
    unittest.main()
