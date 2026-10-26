"""Native/CPU scheduler oracles for device-only declaration-offer passes."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import itertools
import unittest
from unittest.mock import patch

import torch

from studies.campaign.backends.device_scheduler import (
    METADATA_WIDTH, OWNERS, PASSED, RAW_KEY, RAW_KIND, DeviceSchedulerBatch,
    SchedulerError, capture_schedulers, inspect_schedulers, pass_interrupt, scheduler_decisions,
)
from studies.shared.campaign_adapter import CampaignAdapter, SCHEMA
from studies.shared.multiplayer_mcts import PLAYERS
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported


class SchedulerRaw:
    def __init__(self, *, offers=PLAYERS, kind="production", actor="axis", terminal=False, key="start"):
        self.offers, self.kind, self.actor, self.terminal = offers, kind, actor, terminal
        self.key = hashlib.sha256(key.encode()).hexdigest()
        self.calls = 0

    def planning_key(self):
        return self.key

    def decision_kind(self):
        return self.kind

    def current_decision_player(self):
        return self.actor

    def is_terminal(self):
        return self.terminal

    def legal_interrupts(self):
        self.calls += 1
        # Multiplicity and input order deliberately differ from actor order.
        return [{"id": f"declare-{index}-{actor}", "player": actor, "kind": "declare_war",
                 "nation": actor, "decision": "interrupt", "parameters": {"opaque": [index, actor]}}
                for index, actor in enumerate(self.offers)]


def expected(env):
    offer = env.decision_kind() == "declaration_offer"
    return {"key": env.planning_key(), "actor": env.current_decision_player(), "kind": env.decision_kind(),
            "terminal": env.is_terminal(), "passed": tuple(sorted(env._passed)),
            "interrupt_action_ids": tuple(action.id for action in env.legal_actions()) if offer else ()}


class SchedulerChecks:
    device = "cpu"

    def capture(self, envs):
        return capture_schedulers(envs, device=self.device)

    def assert_reference(self, batch, envs):
        actual = inspect_schedulers(batch)
        for value, env in zip(actual, envs, strict=True):
            for key, reference in expected(env).items():
                self.assertEqual(value[key], reference, key)

    def apply_pass(self, batch, mask=None):
        decision = scheduler_decisions(batch)
        if mask is None:
            mask = decision.is_offer
        result = pass_interrupt(batch, decision.keys, decision.offered, mask)
        self.assertTrue(bool(result.committed.cpu()))
        return result.batch

    def test_all_orders_multiplicity_and_nonprefix_passed_sets_match_reference(self):
        envs = []
        for order in itertools.permutations(PLAYERS):
            env = CampaignAdapter(SchedulerRaw(offers=("comintern", "axis", "allies", "axis")), interrupt_order=order)
            # Imported restored states need not be a prefix of current order.
            env._passed = {"allies"}
            envs.append(env)
        batch = self.capture(envs)
        self.assert_reference(batch, envs)
        for _ in range(2):
            batch = self.apply_pass(batch)
            for env in envs:
                env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))
            self.assert_reference(batch, envs)
        self.assertEqual([env.raw.calls for env in envs], [1] * len(envs))
        self.assertEqual(batch.menu_lengths.cpu().tolist(), [4] * len(envs))

    def test_phase_terminal_chance_pending_and_empty_menu_do_not_invent_offers(self):
        envs = [CampaignAdapter(SchedulerRaw(kind=kind, terminal=terminal, offers=offers, actor=actor))
                for kind, terminal, offers, actor in (
                    ("combat_movement", False, (), "axis"), ("production", True, PLAYERS, None),
                    ("chance", False, PLAYERS, None), ("casualties", False, PLAYERS, "comintern"),
                    ("combat", False, ("allies",), "axis"),
                    ("non_combat_movement", False, ("axis",), "allies"),
                    ("place_units", False, ("comintern",), "allies"))]
        batch = self.capture(envs)
        self.assert_reference(batch, envs)
        self.assertEqual(scheduler_decisions(batch).is_offer.cpu().tolist(), [False] * 4 + [True] * 3)
        result = pass_interrupt(batch, scheduler_decisions(batch).keys,
                                scheduler_decisions(batch).offered,
                                torch.ones(len(envs), dtype=torch.bool, device=self.device))
        self.assertFalse(bool(result.committed.cpu()))
        self.assertTrue(torch.equal(result.batch.metadata, batch.metadata))

    def test_stale_wrong_actor_and_malformed_menu_abort_entire_selected_batch(self):
        batch = self.capture([CampaignAdapter(SchedulerRaw()), CampaignAdapter(SchedulerRaw(key="other"))])
        decision = scheduler_decisions(batch)
        selected = torch.ones(2, dtype=torch.bool, device=self.device)
        stale = decision.keys.clone()
        stale[1, RAW_KEY.start] ^= 1
        cases = [(batch, stale, decision.offered, SchedulerError.STALE_KEY),
                 (batch, decision.keys, (decision.offered + 1) % 3, SchedulerError.WRONG_ACTOR)]
        broken_ids = batch.menu_ids.clone()
        broken_ids[1, 0] = len(batch.context.action_ids)
        cases.append((replace(batch, menu_ids=broken_ids), decision.keys, decision.offered, SchedulerError.SPECIFICATION))
        broken_owners = batch.metadata.clone()
        broken_owners[1, OWNERS] = 0
        cases.append((replace(batch, metadata=broken_owners), broken_owners.clone(), decision.offered,
                      SchedulerError.SPECIFICATION))
        for source, keys, actors, error in cases:
            result = pass_interrupt(source, keys, actors, selected)
            self.assertFalse(bool(result.committed.cpu()))
            self.assertTrue(torch.equal(result.batch.metadata, source.metadata))
            self.assertTrue(any(value & int(error) for value in result.errors.cpu().tolist()))
            self.assertEqual(result.accepted.cpu().tolist(), [False, False])
        first = self.apply_pass(batch)
        second = pass_interrupt(first, decision.keys, decision.offered, selected)
        self.assertTrue(all(value & int(SchedulerError.STALE_KEY) for value in second.errors.cpu().tolist()))

    def test_unselected_bad_lane_does_not_veto_and_forks_are_independent(self):
        batch = self.capture([CampaignAdapter(SchedulerRaw())])
        fork = batch.fork(torch.tensor([0, 0, 0], dtype=torch.int64, device=self.device))
        self.assertTrue(torch.equal(fork.metadata.cpu(), batch.metadata.cpu().expand(3, -1)),
                        "Fork must preserve all full SHA256 digest words exactly")
        metadata = fork.metadata.clone()
        metadata[2, RAW_KIND] = -1
        fork = replace(fork, metadata=metadata)
        decision = scheduler_decisions(fork)
        selected = torch.tensor([True, False, False], device=self.device)
        result = pass_interrupt(fork, decision.keys, decision.offered, selected)
        self.assertTrue(bool(result.committed.cpu()))
        self.assertEqual(result.accepted.cpu().tolist(), [True, False, False])
        self.assertEqual(result.batch.metadata[:, PASSED].cpu().tolist(), [1, 0, 0])
        self.assertEqual(batch.metadata[:, PASSED].cpu().tolist(), [0])
        self.assertEqual(fork.metadata[:, PASSED].cpu().tolist(), [0, 0, 0])
        snapshot = result.batch.snapshot()
        result.batch.metadata[0, PASSED] = 7
        self.assertEqual(snapshot.metadata[:, PASSED].cpu().tolist(), [1, 0, 0])

    def test_execution_never_reads_tensor_values_on_host(self):
        batch = self.capture([CampaignAdapter(SchedulerRaw())])
        lanes = torch.tensor([0, 0], dtype=torch.int64, device=self.device)
        selected = torch.ones(2, dtype=torch.bool, device=self.device)
        with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("host copy")), \
             patch.object(torch.Tensor, "tolist", side_effect=AssertionError("host list")), \
             patch.object(torch.Tensor, "item", side_effect=AssertionError("host scalar")), \
             patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("host condition")):
            fork = batch.fork(lanes)
            first = scheduler_decisions(fork)
            one = pass_interrupt(fork, first.keys, first.offered, selected)
            second = scheduler_decisions(one.batch)
            two = pass_interrupt(one.batch, second.keys, second.offered, selected)
        self.assertEqual(two.batch.metadata[:, PASSED].cpu().tolist(), [3, 3])

    def test_native_adapter_and_packed_state_remain_exact_after_all_passes(self):
        from studies.campaign.curriculum import make_env
        from studies.campaign.backends.device_state import DeviceStateBatch
        env = make_env(1951, calendar_rounds=3)
        raw_before = env.raw.serialize()
        packed = DeviceStateBatch.capture([env.raw], device=self.device)
        raw_snapshot = packed.snapshot()
        batch = self.capture([env])
        steps = 0
        while env.decision_kind() == "declaration_offer":
            self.assert_reference(batch, [env])
            batch = self.apply_pass(batch)
            env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))
            steps += 1
        self.assertGreater(steps, 0)
        self.assert_reference(batch, [env])
        self.assertEqual(env.raw.serialize(), raw_before)
        self.assertTrue(torch.equal(packed.records, raw_snapshot.records))
        self.assertTrue(torch.equal(packed.sections, raw_snapshot.sections))
        restored, = packed.restore_envs()
        self.assertEqual(restored.serialize(), raw_before)


class CPUSchedulerTests(SchedulerChecks, unittest.TestCase):
    pass


@unittest.skipUnless(torch.backends.mps.is_available() and mps_int64_indexing_supported(),
                     "Apple MPS unavailable or its int64 indexing is inexact; use tmp/gpu-mps-env/bin/python")
class MPSSchedulerTests(SchedulerChecks, unittest.TestCase):
    device = "mps"


class SchedulerBoundaryTests(unittest.TestCase):
    def test_unsupported_mps_integer_indexing_is_rejected_without_cast_or_fallback(self):
        with patch("torch.backends.mps.is_available", return_value=True), \
             patch("studies.campaign.backends.metal_validation.require_lossless_mps_indexing",
                   side_effect=RuntimeError("MPS int64 indexing is inexact; use tmp/gpu-mps-env/bin/python")):
            with self.assertRaisesRegex(RuntimeError, "indexing is inexact"):
                capture_schedulers([CampaignAdapter(SchedulerRaw())], device="mps")

    def test_rejects_incomplete_keys_wrong_dtypes_devices_and_layouts(self):
        env = CampaignAdapter(SchedulerRaw())
        batch = capture_schedulers([env])
        decision = scheduler_decisions(batch)
        mask = torch.ones(1, dtype=torch.bool)
        for keys, actors, selected in ((decision.keys.float(), decision.offered, mask),
                                      (decision.keys[:, :METADATA_WIDTH - 1], decision.offered, mask),
                                      (decision.keys, decision.offered.bool(), mask),
                                      (decision.keys, decision.offered, mask.long())):
            with self.assertRaises(ValueError):
                pass_interrupt(batch, keys, actors, selected)
        with self.assertRaises(ValueError):
            scheduler_decisions(replace(batch, menu_lengths=torch.zeros(2, dtype=torch.int64)))
        env.raw.key = "short-key"
        with self.assertRaises(ValueError):
            capture_schedulers([env])

    def test_empty_batch_has_no_implicit_rule_capacity(self):
        batch = capture_schedulers([])
        decision = scheduler_decisions(batch)
        result = pass_interrupt(batch, decision.keys, decision.offered, decision.is_offer)
        self.assertEqual(tuple(result.batch.metadata.shape), (0, METADATA_WIDTH))
        self.assertEqual(tuple(result.batch.menu_ids.shape), (0, 0))
        self.assertTrue(bool(result.committed))


if __name__ == "__main__":
    unittest.main()
