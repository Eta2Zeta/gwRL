"""Full native cloneForSearch conformance, including all unsigned seed bits."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import torch

from studies.campaign.backends.device_scheduler import (capture_schedulers, inspect_schedulers,
    pass_interrupt, scheduler_decisions)
from studies.campaign.backends.device_search_clone import DeviceSearchRoots, clone_for_search
from studies.campaign.backends.device_state import DeviceStateBatch
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.curriculum import make_env
from tests.test_campaign_device_state import real_states, rich_fixture

EXACT_MPS = torch.backends.mps.is_available() and mps_int64_indexing_supported()


def seed_tensor(values):
    return torch.tensor([value if value < 2**63 else value - 2**64 for value in values], dtype=torch.int64, device="mps")


@unittest.skipUnless(EXACT_MPS, "Exact MPS integer state unavailable; use tmp/gpu-mps-env/bin/python")
class CampaignDeviceSearchCloneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def test_every_seed_bit_all_active_streams_and_tapes_match_full_native_clone(self):
        raw = rich_fixture()
        originals = []
        for active in ("actual", "search", "training"):
            source = raw.clone()
            value = json.loads(source.serialize())
            value["random"]["active"] = active
            source.restore(json.dumps(value))
            originals.append(source)
        before = [env.serialize() for env in originals]
        state = DeviceStateBatch.capture(originals, device="mps")
        words = state.records.clone()
        seeds = [0, 1, 2**24 + 1, 2**31 + 1, 2**32 - 1, 2**63 - 1, 2**63, 2**64 - 1]
        lanes = [0, 1, 2, 0, 1, 2, 0, 1]
        result = clone_for_search(state, seed_tensor(seeds), torch.tensor(lanes, dtype=torch.int64, device="mps"))
        self.assertEqual(result.errors.cpu().tolist(), [0] * len(seeds))
        self.assertEqual(result.accepted.cpu().tolist(), [True] * len(seeds))
        source_words, cloned_words = state.records.cpu(), result.state.records.cpu()
        source_sections, cloned_sections = state.sections.cpu(), result.state.sections.cpu()
        for destination, origin in enumerate(lanes):
            start = int(source_sections[origin, 0])
            end = int(source_words[origin, start, 4])
            cloned_start = int(cloned_sections[destination, 0])
            cloned_end = int(cloned_words[destination, cloned_start, 4])
            self.assertEqual((cloned_start, cloned_end), (start, end))
            self.assertTrue(torch.equal(cloned_words[destination, cloned_start:cloned_end],
                                        source_words[origin, start:end]),
                            "Every unchanged State/history/IEEE payload bit must survive search cloning")
        restored = result.state.restore_envs()
        for index, actual in enumerate(restored):
            expected = originals[lanes[index]].clone_for_search(seeds[index])
            self.assertEqual(actual.serialize(), expected.serialize())
            self.assertEqual(actual.planning_key(), originals[lanes[index]].planning_key())
            value = json.loads(actual.serialize())["random"]
            self.assertEqual(value["active"], "search")
            self.assertEqual(value["test_tape"], [])
            self.assertEqual(value["tape_position"], "0")
        self.assertEqual([env.serialize() for env in originals], before)
        self.assertTrue(torch.equal(state.records, words))
        self.assertNotEqual(restored[0].serialize(), restored[3].serialize(), "Different seeds need independent search streams")

    def test_cloned_real_pending_chance_continues_with_exact_native_faces_and_events(self):
        pending = real_states()[1]
        original = pending.serialize()
        state = DeviceStateBatch.capture([pending], device="mps")
        seeds = (0, 1951, 2**63, 2**64 - 1)
        result = clone_for_search(state, seed_tensor(seeds), torch.zeros(len(seeds), dtype=torch.int64, device="mps"))
        for actual, seed in zip(result.state.restore_envs(), seeds, strict=True):
            expected = pending.clone_for_search(seed)
            actual.resolve_chance(); expected.resolve_chance()
            self.assertEqual(actual.serialize(), expected.serialize())
        self.assertEqual(pending.serialize(), original)

    def test_bound_scheduler_forks_keep_passed_order_actor_and_keys(self):
        env = make_env(1951, calendar_rounds=3)
        env.interrupt_order = ("comintern", "axis", "allies")
        # Retain a genuine passed offer alongside the unchanged raw position.
        if env.decision_kind() == "declaration_offer":
            env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))
        before = env.serialize()
        roots = DeviceSearchRoots.capture([env])
        result = roots.clone_for_search(seed_tensor((7, 8, 9)), torch.zeros(3, dtype=torch.int64, device="mps"))
        descriptors = inspect_schedulers(result.scheduler)
        native = result.state.restore_envs()
        for index, value in enumerate(descriptors):
            reference = env.clone_for_search((7, 8, 9)[index])
            self.assertEqual(value["key"], reference.planning_key())
            self.assertEqual(value["actor"], reference.current_decision_player())
            self.assertEqual(value["kind"], reference.decision_kind())
            self.assertEqual(value["passed"], tuple(sorted(reference._passed)))
            self.assertEqual(native[index].serialize(), reference.raw.serialize())
        self.assertEqual(env.serialize(), before)

    def test_hot_clone_and_scheduler_operations_have_no_host_reads(self):
        env = make_env(11, calendar_rounds=3)
        state = DeviceStateBatch.capture([env.raw], device="mps")
        scheduler = capture_schedulers([env], device="mps")
        seeds = seed_tensor((0, 2**64 - 1))
        lanes = torch.zeros(2, dtype=torch.int64, device="mps")
        with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("host copy")), \
             patch.object(torch.Tensor, "tolist", side_effect=AssertionError("host list")), \
             patch.object(torch.Tensor, "item", side_effect=AssertionError("host scalar")), \
             patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("host condition")):
            result = clone_for_search(state, seeds, lanes, scheduler=scheduler)
            decision = scheduler_decisions(result.scheduler)
            passed = pass_interrupt(result.scheduler, decision.keys, decision.offered, decision.is_offer)
        self.assertEqual(result.errors.cpu().tolist(), [0, 0])
        self.assertTrue(bool(passed.committed.cpu()))

    def test_invalid_device_lanes_and_random_records_remain_flagged_without_source_changes(self):
        source = DeviceStateBatch.capture([real_states()[0]], device="mps")
        before = source.records.clone()
        result = clone_for_search(source, seed_tensor((0, 1, 2)),
                                  torch.tensor([0, -1, 1], dtype=torch.int64, device="mps"))
        self.assertEqual(result.accepted.cpu().tolist(), [True, False, False])
        self.assertTrue(all(result.errors.cpu().tolist()[1:]))
        with self.assertRaises(ValueError):
            result.state.to_native()
        broken = source.snapshot()
        # Make the active-stream string ID unknown. This must be an error, not
        # a successful silent repair of an invalid original random record.
        active = int(source.section("random.active").cpu()[0])
        broken.records[0, active, 1] = -1
        rejected = clone_for_search(broken, seed_tensor((3,)))
        self.assertEqual(rejected.accepted.cpu().tolist(), [False])
        self.assertTrue(torch.equal(rejected.state.records, broken.records))
        self.assertTrue(torch.equal(source.records, before))
        with self.assertRaises(ValueError):
            rejected.state.to_native()

    def test_empty_destinations_and_strict_seed_layout(self):
        state = DeviceStateBatch.capture([real_states()[0]], device="mps")
        empty = clone_for_search(state, seed_tensor(()), torch.empty(0, dtype=torch.int64, device="mps"))
        self.assertEqual(empty.state.restore_envs(), [])
        self.assertEqual(tuple(empty.errors.shape), (0,))
        for seeds, lanes in ((torch.ones(1, dtype=torch.float32, device="mps"), None),
                             (torch.ones(1, dtype=torch.bool, device="mps"), None),
                             (torch.ones(1, dtype=torch.int64), None),
                             (seed_tensor((1, 2)), None),
                             (seed_tensor((1,)), torch.zeros(1, dtype=torch.int32, device="mps"))):
            with self.assertRaises(ValueError):
                clone_for_search(state, seeds, lanes)


class CampaignSearchCloneBoundaryTests(unittest.TestCase):
    def test_cpu_remains_an_explicit_separate_backend(self):
        state = DeviceStateBatch.capture([real_states()[0]], device="cpu")
        with self.assertRaisesRegex(ValueError, "requires Apple MPS"):
            clone_for_search(state, torch.tensor([1], dtype=torch.int64))


if __name__ == "__main__":
    unittest.main()
