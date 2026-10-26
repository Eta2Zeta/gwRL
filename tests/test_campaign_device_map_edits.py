"""Native-oracle container construction, complete payloads and resident rollback."""
from __future__ import annotations

from contextlib import ExitStack
import dataclasses
import json
import unittest
from unittest.mock import patch

import torch

from studies.campaign.backends.device_state import DeviceStateBatch
from studies.campaign.backends.device_map_edits import (
    ContainerError, MapMode, SetMode, build_map_edits, build_set_edits,
    build_sequence_splices, commit_container_edits,
)
from studies.campaign.backends.device_state_edits import _strings
from studies.campaign.backends.device_strings import intern_bytes, pack_byte_requests
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from tests.test_campaign_device_state import rich_fixture, real_states

EXACT_MPS = torch.backends.mps.is_available() and mps_int64_indexing_supported()


def scalar(tag, value=0):
    if tag in (2, 3):
        bits = value & ((1 << 64)-1)
        return [tag, 0, bits & 0xffffffff, bits >> 32, 1]
    return [tag, value, 0, 0, 1]


def tensor(state, values, dtype=torch.int64):
    return torch.tensor(values, dtype=dtype, device=state.device)


def fixture(device="cpu", count=1):
    env = rich_fixture()
    data = json.loads(env.serialize())
    data["state"]["flags"].update({"aaa_existing": 11, "mmm_existing": 22, "zzz_existing": 33})
    env.restore(json.dumps(data, separators=(",", ":")))
    envs = [env] + [env.clone() for _ in range(count-1)]
    return DeviceStateBatch.capture(envs, device=device), envs


def intern(state, values):
    requests, lengths = pack_byte_requests(values, device=state.device)
    result = intern_bytes(state, requests, lengths,
        string_capacity=state.string_offsets.numel()-1+len(values),
        byte_capacity=state.string_bytes.numel()+requests.numel())
    return result.state, result.ids


def child(state, root, index):
    rows = state.records[0].cpu().tolist()
    at = root+1
    for _ in range(index): at = rows[at][4]
    return at


def lookup(state, root, text):
    # Explicit test authoring/inspection; production builders never use this.
    rows, strings = state.records[0].cpu().tolist(), _strings(dataclasses.replace(
        state, string_bytes=state.string_bytes.cpu(), string_offsets=state.string_offsets.cpu(),
        suffix_usage=state.suffix_usage.cpu(), context=_cpu_context(state)))
    at = root+1
    for _ in range(rows[root][1]):
        if strings[rows[at][1]] == text.encode(): return at+1
        at = rows[at+1][4]
    raise KeyError(text)


def _cpu_context(state):
    class Context:
        string_bytes = state.context.string_bytes.cpu()
        string_offsets = state.context.string_offsets.cpu()
    return Context()


def local_rows(state, root):
    rows = state.records[0].cpu()
    end = rows[root, 4].item()
    value = rows[root:end].clone(); value[:, 4] -= root
    return value.tolist()


def expected(env, mutate):
    data = json.loads(env.serialize()); mutate(data)
    clone = env.clone(); clone.restore(json.dumps(data, separators=(",", ":"), ensure_ascii=False))
    return clone.serialize()


def map_build(state, roots, keys, mode, rows, *, selected=None, capacity=None):
    B = state.lane_count
    return build_map_edits(state, roots, keys, torch.full((B,), int(mode), dtype=torch.int64, device=state.device),
        tensor(state, [rows]*B).reshape(B, len(rows), 5), torch.full((B,), len(rows), dtype=torch.int64, device=state.device),
        torch.ones(B, dtype=torch.bool, device=state.device) if selected is None else selected, capacity=capacity)


class CampaignDeviceMapEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads(); torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls): torch.set_num_threads(cls.old_threads)

    def map_roundtrip(self, device):
        state, envs = fixture(device)
        original = state.records.clone()
        state, ids = intern(state, [b"000_new_first", b"qqq_new_middle", b"zzzz_new_last", b"aaa_existing", b"absent"])
        for index, value in ((0, -31), (1, 42), (2, 2**31-1)):
            build = map_build(state, state.section("state.flags").contiguous(), ids[index:index+1], MapMode.UPSERT, [scalar(2, value)])
            result = commit_container_edits(build, capacity=state.records.shape[1]+3)
            self.assertEqual(result.errors.cpu().tolist(), [0]); self.assertTrue(result.accepted.cpu().item())
            state = result.state
        actual = state.restore_envs()[0]
        self.assertEqual(actual.serialize(), expected(envs[0], lambda data: data["state"]["flags"].update(
            {"000_new_first": -31, "qqq_new_middle": 42, "zzzz_new_last": 2**31-1})))
        # Already-present insertion ignores the entire unused malformed value.
        build = map_build(state, state.section("state.flags").contiguous(), ids[3:4], MapMode.INSERT_IF_ABSENT, [[99, 0, 0, 0, 17]])
        noop = commit_container_edits(build)
        self.assertEqual(noop.errors.cpu().tolist(), [0]); self.assertEqual(noop.changed.cpu().tolist(), [False])
        self.assertTrue(torch.equal(noop.state.records, state.records))
        erased = commit_container_edits(map_build(state, state.section("state.flags").contiguous(), ids[3:4], MapMode.ERASE, []))
        self.assertEqual(erased.errors.cpu().tolist(), [0])
        missing = commit_container_edits(map_build(erased.state, erased.state.section("state.flags").contiguous(), ids[4:5], MapMode.ERASE, []))
        self.assertEqual(missing.errors.cpu().tolist(), [0]); self.assertFalse(missing.changed.cpu().item())
        self.assertEqual(json.loads(erased.state.restore_envs()[0].serialize())["state"]["flags"].get("aaa_existing"), None)
        self.assertTrue(torch.equal(original, DeviceStateBatch.capture(envs, device=device).records))

    def test_cpu_byte_sorted_map_insert_update_erase_and_idempotence_native_oracle(self):
        self.map_roundtrip("cpu")

    @unittest.skipUnless(EXACT_MPS, "Lossless MPS indexing unavailable")
    def test_mps_byte_sorted_map_insert_update_erase_and_idempotence_native_oracle(self):
        self.map_roundtrip("mps")

    def test_json_object_preserves_every_unknown_nested_number_null_empty_payload_and_rng(self):
        for device in (("cpu", "mps") if EXACT_MPS else ("cpu",)):
            with self.subTest(device=device):
                state, envs = fixture(device)
                state, ids = intern(state, [b"000_opaque_copy", b"zzzz_empty", b"absent_is_different"])
                politics = state.section("state.politics")[0].cpu().item()
                pending = child(state, politics, 10)
                opaque = lookup(state, pending, "device_opaque_fixture")
                rows = local_rows(state, opaque)
                built = map_build(state, tensor(state, [opaque]), ids[:1], MapMode.UPSERT, rows)
                result = commit_container_edits(built, capacity=state.records.shape[1]+len(rows)+1)
                self.assertEqual(result.errors.cpu().tolist(), [0])
                original = json.loads(envs[0].serialize())["state"]["politics"]["pending"]["device_opaque_fixture"]
                expected_value = dict(original); expected_value["000_opaque_copy"] = original
                self.assertEqual(result.state.restore_envs()[0].serialize(), expected(envs[0], lambda data:
                    data["state"]["politics"]["pending"].__setitem__("device_opaque_fixture", expected_value)))
                # Empty object is present, distinct from null and absent fields.
                built = map_build(result.state, tensor(state, [opaque]), ids[1:2], MapMode.UPSERT, [[13, 0, 0, 0, 1]])
                result = commit_container_edits(built, capacity=result.state.records.shape[1]+2)
                self.assertEqual(result.errors.cpu().tolist(), [0])
                value = json.loads(result.state.restore_envs()[0].serialize())["state"]["politics"]["pending"]["device_opaque_fixture"]
                self.assertIsNone(value["absent_is_different"]); self.assertEqual(value["zzzz_empty"], {})
                self.assertEqual(json.loads(result.state.restore_envs()[0].serialize())["random"], json.loads(envs[0].serialize())["random"])

    def test_string_and_integer_sets_sort_values_and_idempotent_operations(self):
        for device in (("cpu", "mps") if EXACT_MPS else ("cpu",)):
            with self.subTest(device=device):
                state, envs = fixture(device)
                state, ids = intern(state, [b"000_new_commitment", b"zzz_new_commitment"])
                units = state.section("state.units")[0].cpu().item()
                first_unit = units+2
                commitments = child(state, first_unit, 11)
                for index in (1, 0, 0):
                    element = tensor(state, [[[5, 0, 0, 0, 1]]]); element[:, 0, 1] = ids[index]
                    build = build_set_edits(state, tensor(state, [commitments]), tensor(state, [SetMode.INSERT]), element,
                                            tensor(state, [True], torch.bool))
                    result = commit_container_edits(build, capacity=state.records.shape[1]+1)
                    self.assertEqual(result.errors.cpu().tolist(), [0]); state = result.state
                value = json.loads(state.restore_envs()[0].serialize())["state"]["units"]
                first = next(iter(value.values()))
                self.assertEqual(first["commitments"], ["000_new_commitment", "device_custom_commitment", "zzz_new_commitment"])
                # Native set<int> in a real pending chance request.
                chance_env = real_states()[1]
                value = json.loads(chance_env.serialize())
                value["state"]["chance"]["dice"][0]["reroll_faces"] = [1, 6]
                chance_env.restore(json.dumps(value, separators=(",", ":")))
                chance = DeviceStateBatch.capture([chance_env], device=device)
                optional = chance.section("state.chance")[0].cpu().item()
                request = optional+1; dice = child(chance, request, 4); die = dice+1; faces = child(chance, die, 2)
                build = build_set_edits(chance, tensor(chance, [faces]), tensor(chance, [SetMode.INSERT]),
                    tensor(chance, [[scalar(2, 2)]]), tensor(chance, [True], torch.bool))
                result = commit_container_edits(build, capacity=chance.records.shape[1]+1)
                self.assertEqual(result.errors.cpu().tolist(), [0])
                self.assertEqual(result.state.restore_envs()[0].serialize(), expected(chance_env,
                    lambda data: data["state"]["chance"]["dice"][0].__setitem__("reroll_faces", [1, 2, 6])))

    def test_sequence_splices_append_replace_remove_and_empty_keep_full_native_rng(self):
        for device in (("cpu", "mps") if EXACT_MPS else ("cpu",)):
            with self.subTest(device=device):
                state, envs = fixture(device)
                # Cursor1 remains valid for the resulting nonempty tape.
                forest = [scalar(2, 3), scalar(2, 4)]
                forest[1][4] = 2
                build = build_sequence_splices(state, state.section("random.test_tape").contiguous(), tensor(state, [1]),
                    tensor(state, [1]), tensor(state, [forest]), tensor(state, [2]), tensor(state, [2]), tensor(state, [True], torch.bool))
                result = commit_container_edits(build, capacity=state.records.shape[1]+1)
                self.assertEqual(result.errors.cpu().tolist(), [0])
                self.assertEqual(result.state.restore_envs()[0].serialize(), expected(envs[0], lambda data:
                    data["random"].__setitem__("test_tape", [12, 3, 4, 6])))
                # Arbitrary nested JSON values are a complete forest, no per-value width cap.
                politics = result.state.section("state.politics")[0].cpu().item()
                pending = child(result.state, politics, 10); opaque = lookup(result.state, pending, "device_opaque_fixture")
                array = lookup(result.state, opaque, "array")
                root_rows = local_rows(result.state, opaque)
                build = build_sequence_splices(result.state, tensor(state, [array]), tensor(state, [4]), tensor(state, [0]),
                    tensor(state, [root_rows]), tensor(state, [len(root_rows)]), tensor(state, [1]), tensor(state, [True], torch.bool))
                grown = commit_container_edits(build, capacity=result.state.records.shape[1]+len(root_rows))
                self.assertEqual(grown.errors.cpu().tolist(), [0])
                original = json.loads(result.state.restore_envs()[0].serialize())["state"]["politics"]["pending"]["device_opaque_fixture"]
                self.assertEqual(grown.state.restore_envs()[0].serialize(), expected(result.state.restore_envs()[0], lambda data:
                    data["state"]["politics"]["pending"]["device_opaque_fixture"]["array"].append(original)))

    def test_builder_and_final_state_capacity_failures_return_sizes_and_retry_exactly(self):
        for device in (("cpu", "mps") if EXACT_MPS else ("cpu",)):
            state, _ = fixture(device); state, ids = intern(state, [b"new_capacity_key"])
            roots = state.section("state.flags").contiguous()
            build = map_build(state, roots, ids, MapMode.UPSERT, [scalar(2, 9)], capacity=1)
            failed = commit_container_edits(build)
            self.assertEqual(failed.errors.cpu().tolist(), [int(ContainerError.CAPACITY)])
            self.assertGreater(build.required_capacity.cpu().item(), 1)
            self.assertTrue(torch.equal(failed.state.records, state.records))
            build = map_build(state, roots, ids, MapMode.UPSERT, [scalar(2, 9)])
            failed = commit_container_edits(build)
            self.assertFalse(failed.committed.cpu().item()); self.assertEqual(failed.required_state_capacity.cpu().item(), state.lengths.cpu().item()+2)
            self.assertTrue(torch.equal(failed.state.records, state.records))
            success = commit_container_edits(build, capacity=state.records.shape[1]+2)
            self.assertTrue(success.committed.cpu().item())

    def test_selected_cohort_atomic_rollback_missing_key_bad_value_and_unused_lanes(self):
        for device in (("cpu", "mps") if EXACT_MPS else ("cpu",)):
            state, _ = fixture(device, count=2); state, ids = intern(state, [b"aaa_existing", b"new_absent"])
            roots = state.section("state.flags").contiguous()
            build = map_build(state, roots, ids, MapMode.REPLACE_EXISTING, [scalar(2, 5)])
            result = commit_container_edits(build)
            self.assertEqual(result.errors.cpu().tolist(), [0, int(ContainerError.MISSING)])
            self.assertEqual(result.accepted.cpu().tolist(), [False, False]); self.assertTrue(torch.equal(result.state.records, state.records))
            build = map_build(state, roots, ids, MapMode.REPLACE_EXISTING, [scalar(2, 5)], selected=tensor(state, [True, False], torch.bool))
            result = commit_container_edits(build)
            self.assertEqual(result.errors.cpu().tolist(), [0, 0]); self.assertEqual(result.accepted.cpu().tolist(), [True, False])
            bad = map_build(state, roots, ids, MapMode.UPSERT, [[6, 1, 0, 0, 1]])
            result = commit_container_edits(bad)
            self.assertEqual(result.errors.cpu().tolist(), [int(ContainerError.VALUE)]*2)
            self.assertTrue(torch.equal(result.state.records, state.records))

    @unittest.skipUnless(EXACT_MPS, "Lossless MPS indexing unavailable")
    def test_mps_builders_and_commit_match_cpu_without_host_reads(self):
        cpu, envs = fixture(count=3)
        mps = DeviceStateBatch.capture(envs, device="mps")
        cpu, cpu_ids = intern(cpu, [b"000_insert", b"aaa_existing", b"zzz_insert"])
        mps, mps_ids = intern(mps, [b"000_insert", b"aaa_existing", b"zzz_insert"])
        modes = [MapMode.UPSERT, MapMode.REPLACE_EXISTING, MapMode.INSERT_IF_ABSENT]
        args = lambda state, ids: (state, state.section("state.flags").contiguous(), ids,
            tensor(state, modes), tensor(state, [[scalar(2, -7)]]*3), tensor(state, [1]*3), tensor(state, [True]*3, torch.bool))
        expected_build = build_map_edits(*args(cpu, cpu_ids)); expected_result = commit_container_edits(expected_build, capacity=cpu.records.shape[1]+2)
        mps_args = args(mps, mps_ids)
        with ExitStack() as stack:
            for name in ("cpu", "tolist", "item"):
                stack.enter_context(patch.object(torch.Tensor, name, side_effect=AssertionError("Hot host state read")))
            actual_build = build_map_edits(*mps_args)
            actual_result = commit_container_edits(actual_build, capacity=mps.records.shape[1]+2)
        torch.mps.synchronize()
        for name in ("lengths", "errors", "required_capacity", "changed"):
            self.assertTrue(torch.equal(getattr(expected_build, name), getattr(actual_build, name).cpu()), name)
        for name in ("records", "lengths", "sections", "suffix_usage"):
            self.assertTrue(torch.equal(getattr(expected_result.state, name), getattr(actual_result.state, name).cpu()), name)
        self.assertEqual([env.serialize() for env in expected_result.state.restore_envs()], [env.serialize() for env in actual_result.state.restore_envs()])

    def test_invalid_controls_types_bounds_forests_and_source_errors_do_not_commit(self):
        for device in (("cpu", "mps") if EXACT_MPS else ("cpu",)):
            state, _ = fixture(device); state, ids = intern(state, [b"aaa_existing"])
            roots = state.section("state.flags").contiguous()
            for key, mode, error in ((ids, 4, ContainerError.MODE), (tensor(state, [-1]), 0, ContainerError.KEY)):
                result = commit_container_edits(map_build(state, roots, key, mode, [scalar(2, 1)]))
                self.assertEqual(result.errors.cpu().tolist(), [int(error)])
            bad_source = dataclasses.replace(state, errors=tensor(state, [1]))
            self.assertEqual(map_build(bad_source, roots, ids, MapMode.UPSERT, [scalar(2, 1)]).errors.cpu().tolist(), [int(ContainerError.SOURCE)])
            for begin, remove, length, count, error in ((4, 0, 1, 1, ContainerError.BOUNDS), (0, 4, 1, 1, ContainerError.BOUNDS),
                    (0, 0, 1, 0, ContainerError.VALUE), (0, 0, 1, 2, ContainerError.BOUNDS)):
                build = build_sequence_splices(state, state.section("random.test_tape").contiguous(), tensor(state, [begin]),
                    tensor(state, [remove]), tensor(state, [[scalar(2, 3)]]), tensor(state, [length]), tensor(state, [count]), tensor(state, [True], torch.bool))
                result = commit_container_edits(build)
                self.assertEqual(result.errors.cpu().tolist(), [int(error)]); self.assertTrue(torch.equal(result.state.records, state.records))
            with self.assertRaises(ValueError):
                build_map_edits(state, roots, ids.to(torch.float32), tensor(state, [0]), tensor(state, [[scalar(2, 1)]]), tensor(state, [1]), tensor(state, [True], torch.bool))

    def test_empty_cohorts_empty_vectors_and_absent_optionals_remain_distinct(self):
        for device in (("cpu", "mps") if EXACT_MPS else ("cpu",)):
            state, envs = fixture(device)
            empty = state.fork([])
            roots = tensor(empty, [])
            build = build_map_edits(empty, roots, roots, roots, tensor(empty, []).reshape(0, 0, 5), roots,
                tensor(empty, [], torch.bool))
            result = commit_container_edits(build)
            self.assertTrue(result.committed.cpu().item()); self.assertEqual(result.state.records.shape[0], 0)
            # Invalid controls on an unselected lane are not examined.
            ignored = map_build(state, tensor(state, [-1]), tensor(state, [-1]), 99, [[99, 0, 0, 0, 1]],
                selected=tensor(state, [False], torch.bool))
            result = commit_container_edits(ignored)
            self.assertEqual(result.errors.cpu().tolist(), [0]); self.assertTrue(torch.equal(result.state.records, state.records))
            # A native empty vector stays present. It does not become Optional
            # none or a generic JSON null, and removing everything is legal.
            data = json.loads(envs[0].serialize()); data["random"]["tape_position"] = "0"
            env = envs[0].clone(); env.restore(json.dumps(data, separators=(",", ":")))
            tape_state = DeviceStateBatch.capture([env], device=device)
            build = build_sequence_splices(tape_state, tape_state.section("random.test_tape").contiguous(),
                tensor(state, [0]), tensor(state, [3]), tensor(state, []).reshape(1, 0, 5), tensor(state, [0]),
                tensor(state, [0]), tensor(state, [True], torch.bool))
            cleared = commit_container_edits(build)
            self.assertEqual(cleared.errors.cpu().tolist(), [0])
            self.assertEqual(cleared.state.restore_envs()[0].serialize(), expected(env, lambda data:
                data["random"].__setitem__("test_tape", [])))
            units = state.section("state.units")[0].cpu().item()
            carried = child(state, units+2, 8)
            invalid = build_sequence_splices(state, tensor(state, [carried]), tensor(state, [0]), tensor(state, [0]),
                tensor(state, []).reshape(1, 0, 5), tensor(state, [0]), tensor(state, [0]), tensor(state, [True], torch.bool))
            self.assertEqual(invalid.errors.cpu().tolist(), [int(ContainerError.TARGET)])


if __name__ == "__main__":
    unittest.main()
