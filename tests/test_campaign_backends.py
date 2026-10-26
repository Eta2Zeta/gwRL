"""Batch-boundary validation and reuse, independent of campaign rule fixtures."""
from __future__ import annotations

from dataclasses import replace
import copy
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from studies.campaign.backends import CPUBatchBackend, create_backend
from studies.shared.campaign_adapter import CampaignAdapter
from studies.shared.multiplayer_mcts import MctsConfig, VectorMCTS


class TinyRaw:
    def __init__(self, seed=1, phase="choose"):
        self.state, self.seed, self.phase, self.draws = 0, seed, phase, 0
        self.calls = {"actions": 0, "observation": 0}

    def planning_key(self):
        return json.dumps([self.state, self.phase])

    def current_decision_player(self):
        return None if self.phase == "chance" else "axis"

    def decision_kind(self):
        return self.phase

    def is_terminal(self):
        return False

    def legal_actions(self):
        self.calls["actions"] += 1
        return [] if self.phase == "chance" else [
            {"id": f"choice-{self.state}-{index}", "player": "axis", "kind": "choose",
             "parameters": {"index": index, "step": self.state}} for index in range(2)]

    def observation(self):
        self.calls["observation"] += 1
        return {"state": {"step": self.state, "opaque": {"retained": [None, "蒙古", False]}},
                "current_decision_player": self.current_decision_player(), "decision_kind": self.phase}

    def context(self):
        return {"scenario": "unchanged-complete-definition", "extra": [1, 2, 3]}

    def apply_action(self, action):
        index = action["parameters"]["index"]
        if action["parameters"]["step"] != self.state or index not in (0, 1):
            raise ValueError("Invalid fake native action")
        self.state += index + 1

    def chance_request(self):
        return None if self.phase != "chance" else {"id": f"roll-{self.state}", "dice": [{"sides": 6}]}

    def resolve_chance(self):
        if self.phase != "chance":
            raise ValueError("No pending roll")
        self.draws += 1
        self.seed = (self.seed * 17 + 3) % 101
        self.state += self.seed % 6 + 1
        self.phase = "choose"

    def apply_chance_outcome(self, key, faces):
        if key != self.planning_key() or self.phase != "chance" or len(faces) != 1 or len(faces[0]) != 1 \
                or not 1 <= faces[0][0] <= 6:
            raise ValueError("Invalid explicit outcome")
        self.state += faces[0][0]
        self.phase = "choose"

    def serialize(self):
        return json.dumps({"state": self.state, "seed": self.seed, "phase": self.phase, "draws": self.draws})

    def restore(self, serialized):
        value = json.loads(serialized)
        if value["state"] < 0:
            raise ValueError("Invalid saved state")
        self.state, self.seed, self.phase, self.draws = (value[name] for name in ("state", "seed", "phase", "draws"))

    def clone(self):
        return copy.deepcopy(self)

    def clone_for_search(self, seed):
        result = self.clone()
        result.seed = seed
        return result


def lane(seed=1, phase="choose"):
    return CampaignAdapter(TinyRaw(seed, phase))


class CampaignBackendBoundaryTests(unittest.TestCase):
    def test_default_cpu_registry_has_no_gpu_dependency_or_fallback(self):
        backend = create_backend([lane()])
        self.assertEqual(backend.info.name, "cpu")
        self.assertEqual(backend.info.execution, "sequential_reference")
        self.assertFalse(backend.info.native_batch_execution)
        for name in ("gpu", "cuda", "mps", "unknown"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                create_backend([lane()], backend=name)
        result = subprocess.run([sys.executable, "-c",
            "import sys; from studies.campaign.backends import CPUBatchBackend; "
            "assert 'torch' not in sys.modules; assert 'cupy' not in sys.modules"],
            capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_lanes_are_independent_and_menus_are_reused_without_rng_draws(self):
        envs = [lane(1), lane(2)]
        backend = CPUBatchBackend(envs)
        before = backend.inspect_states()
        first = backend.decision_batch()
        for _ in range(3):
            self.assertEqual(backend.inspect_decisions(backend.decision_batch()), backend.inspect_decisions(first))
        self.assertEqual([env.raw.calls["actions"] for env in envs], [1, 1])
        self.assertEqual(backend.inspect_states(), before)
        unchanged = backend.decision_batch((1,))
        backend.apply_actions(backend.decision_batch((0,)), (1,))
        self.assertEqual(backend.inspect_decisions(unchanged)[0].lane, 1)
        self.assertEqual(backend.inspect_states((1,)), (before[1],))
        self.assertNotEqual(backend.inspect_states((0,)), (before[0],))

    def test_duplicate_mutable_lanes_are_rejected(self):
        env = lane()
        with self.assertRaises(ValueError):
            CPUBatchBackend([env, env])
        with self.assertRaises(ValueError):
            CPUBatchBackend([env, CampaignAdapter(env.raw)])

    def test_numerical_export_is_reused_and_host_inspection_cannot_poison_it(self):
        backend = CPUBatchBackend([lane()])
        batch = backend.decision_batch()
        with patch("studies.campaign.features.make_numeric_input", return_value={
                "schema": "test", "nested": {"retained": [None, "蒙古"]}}) as export:
            first = backend.numeric_inputs(batch, buckets=128)
            second = backend.numeric_inputs(backend.decision_batch(), buckets=128)
            self.assertEqual(export.call_count, 1)
        inspected = backend.inspect_numeric(first)
        inspected[0]["nested"]["retained"].append("caller edit")
        self.assertEqual(backend.inspect_numeric(second)[0]["nested"]["retained"], [None, "蒙古"])
        backend.apply_actions(batch, (0,))
        self.assertEqual(backend.inspect_numeric(first)[0]["schema"], "test")
        with self.assertRaises(ValueError):
            backend.numeric_inputs(batch)
        other = CPUBatchBackend([lane()])
        with self.assertRaises(ValueError):
            other.inspect_numeric(first)
        with self.assertRaises(ValueError):
            backend.inspect_numeric(replace(first, lanes=(999,)))

    def test_invalid_later_selection_does_not_mutate_any_lane(self):
        backend = CPUBatchBackend([lane(), lane(2)])
        before = backend.inspect_states()
        batch = backend.decision_batch()
        for choices in ((0, True), (0, 0.5), (0, -1), (0, "unknown"), (0,)):
            with self.subTest(choices=choices), self.assertRaises(ValueError):
                backend.apply_actions(batch, choices)
            self.assertEqual(backend.inspect_states(), before)
        backend.apply_actions(batch, (backend.inspect_decisions(batch)[0].action_ids[0], 1))
        with self.assertRaises(ValueError):
            backend.apply_actions(batch, (0, 0))

    def test_restore_stages_every_lane_and_retained_scalar_views_follow_commit(self):
        backend = CPUBatchBackend([lane(), lane(2)])
        snapshot = backend.snapshot()
        view = backend.scalar(0)
        backend.apply_actions(backend.decision_batch(), (0, 1))
        before = backend.inspect_states()
        invalid = replace(snapshot, payload=(snapshot.payload[0], "not JSON"))
        with self.assertRaises(ValueError):
            backend.restore(invalid)
        self.assertEqual(backend.inspect_states(), before)
        self.assertEqual(view.serialize(), before[0])
        old_batch = backend.decision_batch()
        backend.restore(snapshot)
        self.assertEqual(view.serialize(), snapshot.payload[0])
        with self.assertRaises(ValueError):
            backend.apply_actions(old_batch, (0, 0))
        clone = backend.clone((1, 0))
        self.assertEqual(clone.inspect_states(), tuple(reversed(snapshot.payload)))
        clone.scalar(0).apply_action(clone.scalar(0).legal_actions()[0])
        self.assertEqual(backend.inspect_states(), snapshot.payload)

    def test_explicit_chance_preserves_rng_and_invalid_later_outcome_is_transactional(self):
        backend = CPUBatchBackend([lane(1, "chance"), lane(2, "chance")])
        batch, before = backend.decision_batch(), backend.inspect_states()
        self.assertEqual(len(backend.inspect_chance_requests(batch)), 2)
        self.assertEqual(backend.inspect_states(), before)
        with self.assertRaises(ValueError):
            backend.resolve_chance(batch, (((2,),), ((7,),)))
        self.assertEqual(backend.inspect_states(), before)
        backend.resolve_chance(batch, (((2,),), ((3,),)))
        for index in range(2):
            value = json.loads(json.loads(backend.inspect_states()[index])["raw"])
            self.assertEqual(value["draws"], 0)
            self.assertEqual(value["seed"], index + 1)

    def test_sampled_chance_and_search_clone_keep_lanes_independent(self):
        envs = [lane(1, "chance"), lane(2, "chance")]
        expected = envs[0].clone()
        expected.resolve_chance()
        backend = CPUBatchBackend(envs)
        before = backend.inspect_states()
        backend.resolve_chance(backend.decision_batch((0,)))
        self.assertEqual(backend.inspect_states((0,)), (expected.serialize(),))
        self.assertEqual(backend.inspect_states((1,)), (before[1],))
        searched = backend.scalar(0).clone_for_search(91)
        searched.apply_action(searched.legal_actions()[0])
        self.assertEqual(backend.inspect_states((0,)), (expected.serialize(),))

    def test_scalar_view_runs_existing_vector_mcts_without_mutating_search_root(self):
        backend = CPUBatchBackend([lane()])
        before = backend.inspect_states()
        menu = backend.inspect_decisions(backend.decision_batch())[0].action_ids
        result = VectorMCTS(config=MctsConfig(simulations=3, max_depth=2, seed=7)).search(backend.scalar(0))
        self.assertEqual(tuple(action.id for action in result.actions), menu)
        self.assertEqual(backend.inspect_states(), before)
        backend.scalar(0).apply_action(result.best_action())
        self.assertNotEqual(backend.inspect_states(), before)

    def test_bulk_search_forks_repeat_one_source_and_create_independent_destinations(self):
        original = lane(71)
        backend = CPUBatchBackend([original])
        before = backend.inspect_states()
        seeds = (0, 13, 2**64 - 1)
        forked = backend.clone_for_search(seeds, lanes=(0, 0, 0))
        expected = tuple(original.clone_for_search(seed).serialize() for seed in seeds)
        self.assertEqual(forked.lane_count, 3)
        self.assertEqual(forked.inspect_states(), expected)
        self.assertEqual(backend.inspect_states(), before)
        forked.apply_actions(forked.decision_batch((0,)), (0,))
        self.assertNotEqual(forked.inspect_states((0,)), (expected[0],))
        self.assertEqual(forked.inspect_states((1, 2)), expected[1:])
        self.assertEqual(backend.inspect_states(), before)
        with self.assertRaises(ValueError):
            forked.decision_batch((0, 0))

    def test_bulk_search_forks_follow_source_order_and_allow_common_random_seeds(self):
        originals = [lane(71), lane(72)]
        backend = CPUBatchBackend(originals)
        before = backend.inspect_states()
        forked = backend.clone_for_search((91, 91), lanes=(1, 0))
        self.assertEqual(forked.inspect_states(), tuple(originals[index].clone_for_search(91).serialize()
                                                     for index in (1, 0)))
        self.assertEqual(backend.inspect_states(), before)

    def test_bulk_search_seed_and_lane_validation_precedes_every_clone(self):
        originals = [lane(71), lane(72)]
        backend = CPUBatchBackend(originals)
        before = backend.inspect_states()
        with patch.object(originals[0], "clone_for_search", wraps=originals[0].clone_for_search) as first, \
             patch.object(originals[1], "clone_for_search", wraps=originals[1].clone_for_search) as second:
            for seeds in ((1,), (1, True), (1, 1.5), (1, -1), (1, 2**64), None):
                with self.subTest(seeds=seeds), self.assertRaises(ValueError):
                    backend.clone_for_search(seeds)
            for lanes in ((2,), (-1,), (True,), (0.5,)):
                with self.subTest(lanes=lanes), self.assertRaises(ValueError):
                    backend.clone_for_search((1,), lanes=lanes)
            first.assert_not_called()
            second.assert_not_called()
        self.assertEqual(backend.inspect_states(), before)


if __name__ == "__main__":
    unittest.main()
