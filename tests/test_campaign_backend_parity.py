"""Independent CPU-oracle conformance for the batched backend boundary.

These are rule/state transport checks, not GPU throughput measurements. The
reference drives CampaignAdapter directly rather than another backend wrapper.
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from studies.campaign.backends import CPUBatchBackend, create_backend
from studies.campaign.curriculum import make_env
from studies.campaign.features import make_numeric_input
from studies.shared.campaign_adapter import ScheduledAction
from tests.test_campaign_action_interface import ship_fixture


def action_kind(action):
    return action.raw["kind"] if action.raw is not None else action.kind


def pass_offers(env):
    while env.decision_kind() == "declaration_offer":
        env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))


def land_fixture():
    env = make_env(1951, calendar_rounds=2)
    value = json.loads(env.raw.serialize())
    value["state"]["clock"].update(nation_index=2, player_turn_serial="2", phase="combat_movement")
    value["state"]["completed_turns"] = {"ccp": 1, "mongolia": 1, "japan": 0, "kmt": 0}
    env.raw.restore(json.dumps(value))
    pass_offers(env)
    return env


def chance_fixture(seed=11):
    env = make_env(seed, calendar_rounds=2)
    # The native CCP turn exposes a real recruitment roll after its four phases.
    for _ in range(4):
        env.raw.apply_action(next(action for action in env.raw.legal_actions() if action.kind == "end_phase"))
    env.raw.apply_action(next(action for action in env.raw.legal_actions() if action.kind == "recruitment_roll"))
    if env.decision_kind() != "chance":
        raise AssertionError("Expected a real pending CCP recruitment request")
    return env


def terminal_fixture():
    env = make_env(3, calendar_rounds=1)
    value = json.loads(env.raw.serialize())
    state = value["state"]
    state["clock"].update(round_index=0, nation_index=3, completed_rounds=1,
                          phase="place_units", income_collected=True, player_turn_serial="4")
    state["completed_turns"] = {nation: 1 for nation in ("ccp", "mongolia", "japan", "kmt")}
    state["terminal"] = True
    env.raw.restore(json.dumps(value))
    return env


class CampaignBackendParityTests(unittest.TestCase):
    def pair(self, original):
        return original.clone(), CPUBatchBackend([original.clone()])

    def assert_lane(self, reference, backend, lane=0, *, numeric=False):
        self.assertEqual(backend.inspect_states((lane,)), (reference.serialize(),))
        batch = backend.decision_batch((lane,))
        inspection, = backend.inspect_decisions(batch)
        actions = reference.legal_actions()
        self.assertEqual(inspection.lane, lane)
        self.assertEqual(inspection.key, reference.planning_key())
        self.assertEqual(inspection.actor, reference.current_decision_player())
        self.assertEqual(inspection.kind, reference.decision_kind())
        self.assertEqual(inspection.terminal, reference.is_terminal())
        self.assertEqual(tuple(inspection.action_ids), tuple(action.id for action in actions))
        scalar = backend.scalar(lane)
        self.assertEqual(scalar.observation(), reference.observation())
        self.assertEqual(scalar.context(), reference.context())
        self.assertEqual(tuple(scalar.returns()), tuple(reference.returns()))
        self.assertEqual([action.features() for action in scalar.legal_actions()],
                         [action.features() for action in actions])
        if numeric:
            actual, = backend.inspect_numeric(backend.numeric_inputs(batch, buckets=128))
            expected = make_numeric_input(reference, actions, 128)
            self.assertEqual(set(actual), set(expected))
            for key in ("schema", "owner", "context_key"):
                self.assertEqual(actual[key], expected[key])
            a, b = actual["packed_graph"], expected["packed_graph"]
            self.assertEqual(a["context"], b["context"])
            self.assertEqual(a["observation"], b["observation"])
            self.assertEqual(tuple(a["actions"]), tuple(b["actions"]))
            self.assertEqual(tuple(a["action_factors"]), tuple(b["action_factors"]))
        return batch

    def apply_kind(self, reference, backend, kind, *, numeric=False):
        batch = self.assert_lane(reference, backend, numeric=numeric)
        action = next(action for action in reference.legal_actions() if action_kind(action) == kind)
        backend.apply_actions(batch, (action.id,))
        reference.apply_action(action)
        self.assert_lane(reference, backend)

    def test_initial_offer_and_pass_preserve_owner_menu_and_every_state_field(self):
        reference, backend = self.pair(make_env(1951, calendar_rounds=2))
        self.assertEqual(reference.decision_kind(), "declaration_offer")
        self.assert_lane(reference, backend, numeric=True)
        before = reference.raw.serialize()
        self.apply_kind(reference, backend, "pass_interrupt", numeric=True)
        self.assertEqual(reference.raw.serialize(), before)
        self.assert_lane(reference, backend, numeric=True)

    def test_actual_land_movement_matches_ordered_menu_and_native_input(self):
        reference, backend = self.pair(land_fixture())
        self.assertEqual(reference.decision_kind(), "combat_movement")
        self.apply_kind(reference, backend, "movement_route", numeric=True)
        self.assert_lane(reference, backend, numeric=True)

    def test_pending_naval_force_add_and_route_retain_complete_state(self):
        original = ship_fixture()
        pass_offers(original)
        reference, backend = self.pair(original)
        for kind in ("naval_start_move", "naval_force_add", "naval_route"):
            self.apply_kind(reference, backend, kind, numeric=True)
        self.assert_lane(reference, backend, numeric=True)

    def test_sampled_chance_matches_direct_execution_rng_and_history(self):
        reference, backend = self.pair(chance_fixture())
        batch = self.assert_lane(reference, backend, numeric=True)
        request, = backend.inspect_chance_requests(batch)
        self.assertEqual(request, reference.observation()["state"]["chance"])
        self.assertEqual(backend.inspect_states(), (reference.serialize(),))
        backend.resolve_chance(batch)
        reference.resolve_chance()
        self.assert_lane(reference, backend, numeric=True)

    def test_explicit_outcome_matches_sampled_rule_state_but_preserves_execution_rng(self):
        original = chance_fixture(51)
        reference = original.clone()
        cursor = reference.raw.history_size()
        reference.resolve_chance()
        event = next(event for event in reference.raw.history_since(cursor) if event["kind"] == "chance")
        faces = event["payload"]["outcome"]["faces"]
        backend = CPUBatchBackend([original.clone()])
        before_random = json.loads(original.raw.serialize())["random"]
        backend.resolve_chance(backend.decision_batch(), (faces,))
        actual = backend.scalar(0)
        expected_raw = json.loads(reference.raw.serialize())
        actual_raw = json.loads(json.loads(actual.serialize())["raw"])
        self.assertEqual(actual_raw["state"], expected_raw["state"])
        self.assertEqual(actual_raw["random"], before_random)
        self.assertEqual(actual.observation(), reference.observation())
        self.assertEqual(actual.planning_key(), reference.planning_key())

    def test_explicit_outcome_cannot_adopt_a_new_key_after_authorizing_the_old_request(self):
        env = chance_fixture(51)
        key = env.planning_key()
        pending = env._decision_cache()
        request = env.chance_request()
        faces = [[die["sides"]] for die in request["dice"]]
        intervening = json.loads(env.raw.serialize())
        intervening["state"]["flags"]["conformance_interleaving"] = 1
        def changed_after_inspection():
            env.raw.restore(json.dumps(intervening))
            return pending
        with patch.object(env, "_decision_cache", side_effect=changed_after_inspection):
            with self.assertRaises((RuntimeError, ValueError)):
                env.apply_chance_outcome(key, faces)
        self.assertEqual(json.loads(env.raw.serialize()), intervening)

    def test_chance_rejects_malformed_or_stale_outcomes_transactionally(self):
        reference, backend = self.pair(chance_fixture())
        batch = backend.decision_batch()
        request, = backend.inspect_chance_requests(batch)
        count = len(request["dice"])
        valid = [[die["sides"]] for die in request["dice"]]
        malformed = ([], valid + [[1]], [[]] * count,
                     [[0] for _ in range(count)], [[die["sides"] + 1] for die in request["dice"]],
                     [[True] for _ in range(count)], [[1.5] for _ in range(count)])
        before = backend.inspect_states()
        for faces in malformed:
            with self.subTest(faces=faces), self.assertRaises((TypeError, ValueError, RuntimeError)):
                backend.resolve_chance(batch, (faces,))
            self.assertEqual(backend.inspect_states(), before)
        backend.resolve_chance(batch, (valid,))
        after = backend.inspect_states()
        with self.assertRaises((ValueError, RuntimeError)):
            backend.resolve_chance(batch, (valid,))
        self.assertEqual(backend.inspect_states(), after)

    def test_reroll_paths_are_validated_before_the_rule_handler(self):
        original = chance_fixture()
        value = json.loads(original.raw.serialize())
        for die in value["state"]["chance"]["dice"]:
            die.update(sides=12, reroll_faces=[1], max_rerolls=2)
        original.raw.restore(json.dumps(value))
        backend = CPUBatchBackend([original.clone()])
        batch = backend.decision_batch()
        request, = backend.inspect_chance_requests(batch)
        count = len(request["dice"])
        before = backend.inspect_states()
        for path in ([1], [2, 3], [1, 1, 1, 12], [1, 13], []):
            faces = [path] + [[12] for _ in range(count - 1)]
            with self.subTest(path=path), self.assertRaisesRegex(RuntimeError, "reroll|die range"):
                backend.resolve_chance(batch, (faces,))
            self.assertEqual(backend.inspect_states(), before)
        # This modified political request isolates generic dice validation.
        # Successful rerolls are exercised by the runtime's FixtureRules test;
        # the real political handler correctly requires an unmodified D12.

    def test_raw_native_outcomes_reject_boolean_numeric_and_sequence_coercion(self):
        env = chance_fixture()
        raw = env.raw
        before = raw.serialize()
        key = raw.planning_key()

        class IntegerSubclass(int):
            pass

        for faces in ([[True]], [[1.5]], [[1.0]], [[IntegerSubclass(1)]], [1], "[[1]]", [["1"]]):
            with self.subTest(faces=faces), self.assertRaises((TypeError, ValueError, RuntimeError)):
                raw.apply_chance_outcome(key, faces)
            self.assertEqual(raw.serialize(), before)

    def test_terminal_snapshot_has_no_owner_or_actions_and_exact_return_vector(self):
        reference, backend = self.pair(terminal_fixture())
        batch = self.assert_lane(reference, backend, numeric=True)
        inspection, = backend.inspect_decisions(batch)
        self.assertTrue(inspection.terminal)
        self.assertIsNone(inspection.actor)
        self.assertEqual(tuple(inspection.action_ids), ())
        self.assertEqual(backend.inspect_chance_requests(batch), (None,))
        before = backend.inspect_states()
        with self.assertRaises((ValueError, RuntimeError)):
            backend.apply_actions(batch, (0,))
        self.assertEqual(backend.inspect_states(), before)

    def test_selected_lane_order_clone_search_clone_and_snapshot_restore(self):
        references = [make_env(seed, calendar_rounds=2) for seed in (9, 51)]
        backend = CPUBatchBackend([env.clone() for env in references])
        saved_states = backend.inspect_states()
        snapshot = backend.snapshot()
        actions = [env.legal_actions()[0] for env in references]
        backend.apply_actions(backend.decision_batch((1,)), (actions[1].id,))
        references[1].apply_action(actions[1])
        for lane, reference in enumerate(references):
            self.assert_lane(reference, backend, lane)
        clone = backend.clone((1, 0))
        self.assertEqual(clone.inspect_states(), (references[1].serialize(), references[0].serialize()))
        clone_before = clone.inspect_states()
        backend.restore(snapshot)
        self.assertEqual(backend.inspect_states(), saved_states)
        self.assertEqual(clone.inspect_states(), clone_before)
        scalar = backend.scalar(0)
        searched = scalar.clone_for_search(9182)
        expected = make_env(9, calendar_rounds=2).clone_for_search(9182)
        self.assertEqual(searched.serialize(), expected.serialize())
        searched.apply_action(searched.legal_actions()[0])
        self.assertEqual(backend.inspect_states(), saved_states)

    def test_stale_foreign_and_invalid_lane_selections_leave_whole_batch_unchanged(self):
        originals = [make_env(seed, calendar_rounds=2) for seed in (9, 51)]
        backend = CPUBatchBackend([env.clone() for env in originals])
        before = backend.inspect_states()
        batch = backend.decision_batch()
        for selection in ((0,), (0, "foreign-action"), (0, -1), (0, 10**9), (0, True), (0, 0.5)):
            with self.subTest(selection=selection), self.assertRaises((TypeError, ValueError, RuntimeError, IndexError)):
                backend.apply_actions(batch, selection)
            self.assertEqual(backend.inspect_states(), before)
        other = CPUBatchBackend([env.clone() for env in originals])
        with self.assertRaises((TypeError, ValueError, RuntimeError)):
            backend.apply_actions(other.decision_batch(), (0, 0))
        self.assertEqual(backend.inspect_states(), before)
        backend.apply_actions(batch, (0, 0))
        after = backend.inspect_states()
        with self.assertRaises((ValueError, RuntimeError)):
            backend.apply_actions(batch, (0, 0))
        self.assertEqual(backend.inspect_states(), after)
        for lanes in ((0, 0), (-1,), (2,), (True,), (0.5,)):
            with self.subTest(lanes=lanes), self.assertRaises((TypeError, ValueError, RuntimeError, IndexError)):
                backend.decision_batch(lanes)
        self.assertEqual(backend.inspect_states(), after)

    def test_mixed_chance_batch_validation_is_atomic_across_lanes(self):
        originals = [chance_fixture(11), chance_fixture(51)]
        backend = CPUBatchBackend([env.clone() for env in originals])
        batch = backend.decision_batch()
        requests = backend.inspect_chance_requests(batch)
        valid = [[[die["sides"]] for die in request["dice"]] for request in requests]
        before = backend.inspect_states()
        with self.assertRaises((TypeError, ValueError, RuntimeError)):
            backend.resolve_chance(batch, (valid[0], []))
        self.assertEqual(backend.inspect_states(), before)
        backend.resolve_chance(batch, valid)
        for lane, (reference, faces) in enumerate(zip(originals, valid, strict=True)):
            reference.apply_chance_outcome(reference.planning_key(), faces)
            self.assert_lane(reference, backend, lane)

    def test_scalar_foreign_payload_and_checkpoint_replay_cannot_bypass_legality(self):
        reference, backend = self.pair(make_env(9, calendar_rounds=2))
        scalar = backend.scalar(0)
        original = scalar.serialize()
        action = scalar.legal_actions()[0]
        forged = ScheduledAction(action.id, action.kind, "foreign-owner", action.raw)
        with self.assertRaises((TypeError, ValueError, RuntimeError)):
            scalar.apply_action(forged)
        self.assertEqual(scalar.serialize(), original)
        recording = []
        for _ in range(3):
            actions = reference.legal_actions()
            action = next((item for item in actions if item.kind == "pass_interrupt"), actions[0])
            recording.append(action.id)
            reference.apply_action(action)
            backend.apply_actions(backend.decision_batch(), (action.id,))
        final = backend.inspect_states()
        scalar.restore(original)
        for action_id in recording:
            backend.apply_actions(backend.decision_batch(), (action_id,))
        self.assertEqual(backend.inspect_states(), final)
        self.assert_lane(reference, backend)

    def test_factory_never_silently_substitutes_cpu_for_gpu(self):
        env = make_env(9, calendar_rounds=2)
        self.assertIsInstance(create_backend([env], backend="cpu"), CPUBatchBackend)
        for name in ("gpu", "cuda", "mps", "unknown"):
            with self.subTest(name=name), self.assertRaises((ValueError, NotImplementedError)):
                create_backend([env.clone()], backend=name)


if __name__ == "__main__":
    unittest.main()
