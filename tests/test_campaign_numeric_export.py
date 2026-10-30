"""Native numerical transport retains the complete campaign feature contract."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import gc
import json
from pathlib import Path
import pickle
import threading
import unittest
from unittest import mock

import numpy as np
import gwrl_cpp

from studies.campaign.features import (Graph, NUMERIC_SCHEMA, SCHEMA, _numeric_features,
                                      _string_descriptor, action_factors, canonical,
                                      compile_graph_python, lexical_ids, make_input,
                                      make_numeric_input, numeric_compiler, validate_numeric_input)
from studies.shared.campaign_adapter import SCHEMA as SCHEDULER, CampaignAdapter, ScheduledAction


SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"
BUCKETS = 128


def oracle(value):
    # The pre-existing production path compiles canonical, parsed documents.
    # This also fixes geography adjacency insertion order for the comparison.
    return compile_graph_python(json.loads(canonical(value)), BUCKETS)


def end_phase(raw):
    raw.apply_action(next(action for action in raw.legal_actions() if action.kind == "end_phase"))


class CampaignNumericExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial = gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO), 3, 91, training_actions=True)

    def setUp(self):
        self.raw = self.initial.clone()
        self.env = CampaignAdapter(self.raw)

    def assert_graph_equal(self, graph, expected):
        arrays, debug = graph.arrays(), graph.debug_graph()
        self.assertEqual(set(arrays), {"token_ids", "token_offsets", "types", "numeric",
                                       "sources", "targets", "relations"})
        self.assertEqual(graph.node_count, expected.node_count)
        self.assertEqual(graph.leaf_count, expected.leaf_count)
        self.assertEqual(graph.token_buckets, BUCKETS)
        for field in ("token_ids", "token_offsets", "types"):
            np.testing.assert_array_equal(arrays[field], np.asarray(getattr(expected, field), dtype=np.int64))
        expected_numeric = np.asarray(expected.numeric, dtype=np.float64)
        np.testing.assert_array_equal(arrays["numeric"].view(np.uint64), expected_numeric.view(np.uint64))
        edges = np.column_stack((arrays["sources"], arrays["targets"], arrays["relations"]))
        np.testing.assert_array_equal(edges, np.asarray(expected.edges, dtype=np.int64).reshape(-1, 3))
        for key in ("token_ids", "token_offsets", "types", "edges", "identities", "references", "leaf_count"):
            self.assertEqual(debug[key], getattr(expected, key), key)
        for key, array in arrays.items():
            self.assertEqual(array.dtype, np.float64 if key == "numeric" else np.int64)
            self.assertTrue(array.flags.c_contiguous, key)
            self.assertFalse(array.flags.writeable, key)
        self.assertGreaterEqual(graph.nbytes, sum(array.nbytes for array in arrays.values()))

    def assert_input_equal(self, numeric, raw):
        self.assertEqual(numeric["schema"], NUMERIC_SCHEMA)
        self.assertEqual(validate_numeric_input(numeric, buckets=BUCKETS), len(raw["actions"]))
        packed = numeric["packed_graph"]
        self.assert_graph_equal(packed["context"], oracle(raw["context"]))
        self.assert_graph_equal(packed["observation"], oracle(raw["observation"]))
        self.assertEqual(len(packed["actions"]), len(raw["actions"]))
        for graph, action in zip(packed["actions"], raw["actions"], strict=True):
            self.assert_graph_equal(graph, oracle(action))
        self.assertEqual(packed["action_factors"], tuple(action_factors(action) for action in raw["actions"]))
        self.assertEqual(numeric["owner"], raw["observation"]["current_decision_player"])

    def test_actual_complete_input_all_arrays_factors_and_external_edges_match_oracle(self):
        checkpoint = self.raw.serialize()
        actions = self.env.legal_actions()
        numeric = make_numeric_input(self.env, actions, BUCKETS)
        raw = make_input(self.env, actions)
        self.assert_input_equal(numeric, raw)
        context, observation = numeric["packed_graph"]["context"], numeric["packed_graph"]["observation"]
        source_oracle, context_oracle = oracle(raw["observation"]), oracle(raw["context"])
        expected = [(destination, index) for destination, identity in source_oracle.references
                    for index in context_oracle.identities.get(identity, ())]
        destinations, indices = observation.external_references(context)
        np.testing.assert_array_equal(np.column_stack((destinations, indices)),
                                      np.asarray(expected, dtype=np.int64).reshape(-1, 2))
        self.assertTrue(expected, "The actual campaign must exercise cross-document references")
        self.assertEqual(self.raw.serialize(), checkpoint)

    def test_unicode_negative_zero_and_scalar_callbacks_are_exact_and_reused(self):
        calls = {"lexical": 0, "descriptor": 0, "numeric": 0}

        def lexical(*args):
            calls["lexical"] += 1
            return lexical_ids(*args)

        def descriptor(*args):
            calls["descriptor"] += 1
            return _string_descriptor(*args)

        def numeric(*args):
            calls["numeric"] += 1
            return _numeric_features(*args)

        compiler = gwrl_cpp.CampaignNumericGraphCompiler(BUCKETS, lexical, descriptor, numeric)
        snapshot = self.raw.numeric_context().scheduled_context("海軍\x00é🙂", ["-0", "١٢", "𝟚", "海軍", ""])
        first = compiler.compile(snapshot)
        expected = oracle(snapshot.to_python())
        self.assert_graph_equal(first, expected)
        warm_calls = dict(calls)
        self.assertTrue(all(value > 0 for value in warm_calls.values()))
        self.assert_graph_equal(compiler.compile(snapshot), expected)
        self.assertEqual(calls, warm_calls)
        negative_zero = next(source for source, text in expected.references if text == "-0")
        self.assertTrue(np.signbit(first.arrays()["numeric"][negative_zero, 0]))
        stats = compiler.cache_stats()
        self.assertLessEqual(stats["numeric_features"], stats["numeric_capacity"])
        self.assertLessEqual(stats["field_tokens"], stats["lexical_capacity"])
        self.assertLessEqual(stats["value_tokens"], stats["lexical_capacity"])
        self.assertLessEqual(stats["retained_string_bytes"], stats["string_byte_capacity"])
        self.assertEqual(stats["cache_sets"], 1)
        compiler.clear_caches()
        self.assertEqual(compiler.cache_stats()["numeric_features"], 0)
        self.assert_graph_equal(compiler.compile(snapshot), expected)
        self.assertGreater(calls["lexical"], warm_calls["lexical"])

    def test_scheduled_observation_shares_the_menu_and_keeps_its_complete_json(self):
        menu = self.env.legal_actions()
        decision = self.env._decision_cache()
        snapshots = [action.numeric_snapshot() for action in menu]
        base = self.raw.numeric_observation()
        self.assertNotIn("legal_actions", base.to_python())
        scheduled = base.scheduled_observation(decision.owner, decision.kind, snapshots, SCHEDULER,
                                               self.env.interrupt_order, sorted(self.env._passed))
        document = scheduled.to_python()
        self.assertEqual(document["legal_actions"], [snapshot.to_python() for snapshot in snapshots])
        self.assertEqual(document["current_decision_player"], decision.owner)
        self.assertEqual(document["interrupt_scheduler"], {"schema": SCHEDULER, "order": list(self.env.interrupt_order),
                                                           "passed": []})
        self.assert_graph_equal(numeric_compiler(BUCKETS).compile(scheduled), oracle(document))
        empty = base.scheduled_observation(decision.owner, decision.kind, [], SCHEDULER, self.env.interrupt_order, [])
        self.assertEqual(empty.to_python()["legal_actions"], [])
        self.assert_graph_equal(numeric_compiler(BUCKETS).compile(empty), oracle(empty.to_python()))
        with_overrides = snapshots[0].scheduled_context("schema", ["axis"])
        wrapped = base.scheduled_observation(decision.owner, decision.kind, [with_overrides], SCHEDULER,
                                             self.env.interrupt_order, [])
        self.assertEqual(wrapped.to_python()["legal_actions"], [with_overrides.to_python()])
        self.assert_graph_equal(numeric_compiler(BUCKETS).compile(wrapped), oracle(wrapped.to_python()))

    def test_scheduled_snapshots_keep_every_action_and_wrapper_field(self):
        for action in self.raw.legal_actions():
            self.assertEqual(action.scheduled_snapshot(f"wrapper:{action.id}", "interrupt", "allies").to_python(),
                             {"id": f"wrapper:{action.id}", "kind": "interrupt", "player": "allies",
                              "action": {"id": action.id, "kind": action.kind, "player": action.player,
                                         "nation": action.nation, "decision": action.decision,
                                         "parameters": action.parameters}})
        self.assertEqual(gwrl_cpp.campaign_pass_snapshot("pass", "pass_interrupt", "axis").to_python(),
                         {"id": "pass", "kind": "pass_interrupt", "player": "axis", "action": None})

    def test_old_native_snapshot_and_buffers_outlive_mutation_environment_and_compiler(self):
        raw = self.raw.clone()
        snapshot = raw.numeric_observation()
        original = snapshot.to_python()
        compiler = numeric_compiler(BUCKETS)
        graph = compiler.compile(snapshot)
        expected = oracle(original)
        end_phase(raw)
        self.assertNotEqual(raw.observation(), original)
        self.assertEqual(snapshot.to_python(), original)
        self.assert_graph_equal(compiler.compile(snapshot), expected)
        buffers = graph.arrays()
        saved = {key: array.copy() for key, array in buffers.items()}
        del raw, snapshot, graph, compiler
        gc.collect()
        for key, array in buffers.items():
            np.testing.assert_array_equal(array.view(np.uint64), saved[key].view(np.uint64))
            if array.size:
                with self.assertRaises(ValueError):
                    array.flat[0] = 0
                with self.assertRaises(ValueError):
                    array.setflags(write=True)

    def test_finished_observation_arrays_are_reused_and_live_graphs_never_change(self):
        first, second = self.env.clone(), self.env.clone()
        second.apply_action(next(action for action in second.legal_actions() if action.kind == "pass_interrupt"))
        # Its own compiler, so no other graph can reach these spare arrays first.
        compiler = gwrl_cpp.CampaignNumericGraphCompiler(BUCKETS, lexical_ids, _string_descriptor, _numeric_features)
        scheduled = []
        for env in (first, second):
            menu = env.legal_actions()
            decision = env._decision_cache()
            scheduled.append(env.raw.numeric_observation().scheduled_observation(
                decision.owner, decision.kind, tuple(action.numeric_snapshot() for action in menu),
                SCHEDULER, env.interrupt_order, sorted(env._passed)))
        expected = [oracle(snapshot.to_python()) for snapshot in scheduled]
        kept = compiler.compile(scheduled[0])
        finished = compiler.compile(scheduled[1])
        views = finished.arrays()
        saved = {key: array.copy() for key, array in views.items()}
        address = views["numeric"].ctypes.data
        del finished
        # Only the views still pin these arrays, so a new graph must not take them.
        other = compiler.compile(scheduled[0])
        self.assertNotEqual(other.arrays()["numeric"].ctypes.data, address)
        for key, array in views.items():
            np.testing.assert_array_equal(array.view(np.uint64), saved[key].view(np.uint64))
        del views, array
        reused = compiler.compile(scheduled[1])
        self.assertEqual(reused.arrays()["numeric"].ctypes.data, address)
        self.assert_graph_equal(reused, expected[1])
        self.assert_graph_equal(kept, expected[0])
        self.assert_graph_equal(other, expected[0])

    def test_threads_reusing_observation_arrays_keep_their_graphs_intact(self):
        env = self.env.clone()
        menu = env.legal_actions()
        decision = env._decision_cache()
        snapshots = [env.raw.numeric_observation().scheduled_observation(
            decision.owner, decision.kind, tuple(action.numeric_snapshot() for action in actions), SCHEDULER,
            env.interrupt_order, sorted(env._passed)) for actions in (menu, menu[:len(menu) // 2], menu[:1])]
        compiler = numeric_compiler(BUCKETS)
        expected = [compiler.compile(snapshot).compacted() for snapshot in snapshots]

        def work(thread):
            for step in range(60):
                index = (thread + step) % len(snapshots)
                if not compiler.compile(snapshots[index]) == expected[index]:
                    return False
            return True

        with ThreadPoolExecutor(4) as pool:
            self.assertTrue(all(pool.map(work, range(4))))

    def test_compacted_observation_is_an_equal_independent_graph(self):
        observation = make_numeric_input(self.env, self.env.legal_actions(), BUCKETS)["packed_graph"]["observation"]
        expected = Graph(**observation.debug_graph())
        compact = observation.compacted()
        self.assertIsNot(compact, observation)
        self.assertEqual(compact, observation)
        self.assertLessEqual(compact.nbytes, observation.nbytes)
        self.assertNotEqual(compact.arrays()["numeric"].ctypes.data, observation.arrays()["numeric"].ctypes.data)
        del observation
        self.env._decision = None
        gc.collect()
        self.assert_graph_equal(compact, expected)

    def test_threads_compiling_together_use_separate_bounded_cache_sets(self):
        threads = 4
        inside = threading.Barrier(threads)

        def numeric(*args):
            # Every thread is inside one compile at once, or this times out.
            inside.wait(timeout=60)
            return _numeric_features(*args)

        compiler = gwrl_cpp.CampaignNumericGraphCompiler(BUCKETS, lexical_ids, _string_descriptor, numeric)
        snapshot = gwrl_cpp.campaign_pass_snapshot("pass", "pass_interrupt", "axis")
        expected = oracle(snapshot.to_python())
        with ThreadPoolExecutor(threads) as pool:
            for graph in pool.map(lambda _: compiler.compile(snapshot), range(threads)):
                self.assert_graph_equal(graph, expected)
        stats = compiler.cache_stats()
        self.assertEqual(stats["cache_sets"], threads)
        compiler.clear_caches()
        self.assertEqual(compiler.cache_stats()["cache_sets"], 0)
        threads = stats["set_capacity"] + 3
        inside = threading.Barrier(threads)
        with ThreadPoolExecutor(threads) as pool:
            for graph in pool.map(lambda _: compiler.compile(snapshot), range(threads)):
                self.assert_graph_equal(graph, expected)
        self.assertEqual(compiler.cache_stats()["cache_sets"], stats["set_capacity"])

    def test_clearing_caches_during_a_compile_drops_the_old_set(self):
        entered, release = threading.Event(), threading.Event()

        def lexical(*args):
            entered.set()
            release.wait(timeout=60)
            return lexical_ids(*args)

        compiler = gwrl_cpp.CampaignNumericGraphCompiler(BUCKETS, lexical, _string_descriptor, _numeric_features)
        snapshot = gwrl_cpp.campaign_pass_snapshot("pass", "pass_interrupt", "axis")
        with ThreadPoolExecutor(1) as pool:
            running = pool.submit(compiler.compile, snapshot)
            self.assertTrue(entered.wait(timeout=60))
            compiler.clear_caches()
            release.set()
            self.assert_graph_equal(running.result(timeout=60), oracle(snapshot.to_python()))
        self.assertEqual(compiler.cache_stats()["cache_sets"], 0)

    def test_oversized_scalars_are_encoded_completely_without_being_retained(self):
        text = "x" * (9 << 20)
        calls = {"oversized": 0, "other": 0}

        def lexical(value, role, buckets):
            calls["oversized" if value == text else "other"] += 1
            return lexical_ids(value, role, buckets)

        compiler = gwrl_cpp.CampaignNumericGraphCompiler(BUCKETS, lexical, _string_descriptor, _numeric_features)
        snapshot = gwrl_cpp.campaign_pass_snapshot(text, "pass_interrupt", "axis")
        expected = oracle(snapshot.to_python())
        self.assert_graph_equal(compiler.compile(snapshot), expected)
        cold = calls["other"]
        self.assert_graph_equal(compiler.compile(snapshot), expected)
        self.assertEqual(calls, {"oversized": 2, "other": cold})
        self.assertLess(compiler.cache_stats()["retained_string_bytes"], 1 << 20)

    def test_scheduler_pass_clone_subset_order_and_mutation_invalidate_only_changed_decision(self):
        actions = self.env.legal_actions()
        first = make_numeric_input(self.env, actions, BUCKETS)
        clone = self.env.clone_for_search(721)
        clone_actions = clone.legal_actions()
        same = make_numeric_input(clone, clone_actions, BUCKETS)
        self.assertIs(first["packed_graph"]["context"], same["packed_graph"]["context"])
        self.assertIs(first["packed_graph"]["observation"], same["packed_graph"]["observation"])
        subset = tuple(reversed(actions[::2]))
        self.assert_input_equal(make_numeric_input(self.env, subset, BUCKETS), make_input(self.env, subset))
        passes = [action for action in clone_actions if action.kind == "pass_interrupt"]
        if not passes:
            self.fail("The opening native campaign should offer an explicit declaration pass")
        clone.apply_action(passes[0])
        later_actions = clone.legal_actions()
        later = make_numeric_input(clone, later_actions, BUCKETS)
        self.assert_input_equal(later, make_input(clone, later_actions))
        self.assertIs(later["packed_graph"]["context"], first["packed_graph"]["context"])
        self.assertIsNot(later["packed_graph"]["observation"], first["packed_graph"]["observation"])
        self.assertIs(make_numeric_input(self.env, actions, BUCKETS)["packed_graph"]["observation"],
                      first["packed_graph"]["observation"])
        self.assertNotEqual(clone.neural_observation()["interrupt_scheduler"]["passed"],
                            self.env.neural_observation()["interrupt_scheduler"]["passed"])

    def test_native_input_after_fixed_context_warmup_needs_no_python_state_or_menu_tree(self):
        make_numeric_input(self.env, self.env.legal_actions(), BUCKETS)
        action = next((item for item in self.env.legal_actions() if item.kind == "pass_interrupt"),
                      self.env.legal_actions()[0])
        self.env.apply_action(action)
        actions = self.env.legal_actions()
        with mock.patch.object(CampaignAdapter, "neural_observation", side_effect=AssertionError("Python state tree")), \
             mock.patch.object(CampaignAdapter, "neural_context", side_effect=AssertionError("Python fixed context")), \
             mock.patch.object(ScheduledAction, "neural_features", side_effect=AssertionError("Python action tree")):
            prepared = make_numeric_input(self.env, actions, BUCKETS)
        self.assertEqual(validate_numeric_input(prepared, buckets=BUCKETS), len(actions))

    def test_pending_naval_force_and_route_choices_keep_every_field_and_factor(self):
        from tests.test_campaign_action_interface import ship_fixture

        env = ship_fixture()
        while env.decision_kind() == "declaration_offer":
            env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))
        for kind in ("naval_start_move", "naval_force_add", "naval_route"):
            actions = env.legal_actions()
            self.assert_input_equal(make_numeric_input(env, actions, BUCKETS), make_input(env, actions))
            chosen = next(action for action in actions if action.raw["kind"] == kind)
            env.apply_action(chosen)
        self.assert_input_equal(make_numeric_input(env, env.legal_actions(), BUCKETS),
                                make_input(env, env.legal_actions()))

    def test_chance_snapshot_has_empty_menu_no_owner_and_does_not_consume_dice(self):
        for _ in range(4):
            end_phase(self.raw)
        self.raw.apply_action(next(action for action in self.raw.legal_actions() if action.kind == "recruitment_roll"))
        self.assertEqual(self.raw.decision_kind(), "chance")
        checkpoint = self.raw.serialize()
        self.assert_input_equal(make_numeric_input(self.env, (), BUCKETS), make_input(self.env, ()))
        self.assertEqual(self.raw.serialize(), checkpoint)
        reference = self.raw.clone()
        self.raw.resolve_chance()
        reference.resolve_chance()
        self.assertEqual(self.raw.serialize(), reference.serialize())

    def test_foreign_and_equal_external_wrappers_do_not_reuse_native_menu_payloads(self):
        actions = self.env.legal_actions()
        chosen = actions[0]
        equal = ScheduledAction(chosen.id, chosen.kind, chosen.player, chosen.raw)
        self.assertIsNone(self.env.numeric_input((equal,), BUCKETS))
        self.assertEqual(make_numeric_input(self.env, (equal,), BUCKETS)["schema"], SCHEMA)
        foreign = ScheduledAction("foreign-menu-id", "play", chosen.player, chosen.raw)
        with self.assertRaisesRegex(ValueError, "stale/foreign"):
            self.env.numeric_input((foreign,), BUCKETS)
        self.env.apply_action(chosen)
        try:
            stale = self.env.numeric_input((chosen,), BUCKETS)
        except ValueError:
            pass
        else:
            self.assertIsNone(stale)

    def test_generator_menu_survives_plain_json_fallback(self):
        from tests.test_campaign_adapter import ContextRaw

        fallback = CampaignAdapter(ContextRaw())
        actions = fallback.legal_actions()
        expected = make_input(fallback, actions)
        self.assertEqual(make_numeric_input(fallback, iter(actions), BUCKETS), expected)

    def test_explicit_action_pickle_remains_portable_and_uses_authoritative_execution(self):
        actions = self.env.legal_actions()
        selected = [actions[0], next(action for action in actions if action.kind == "pass_interrupt")]
        for action in selected:
            with self.subTest(kind=action.kind):
                restored = pickle.loads(pickle.dumps(action, protocol=5))
                self.assertEqual(restored.features(), action.features())
                self.assertEqual((restored.id, restored.kind, restored.player),
                                 (action.id, action.kind, action.player))
                first, second = self.env.clone(), self.env.clone()
                first.apply_action(action)
                second.apply_action(restored)
                self.assertEqual(first.serialize(), second.serialize())

    def test_packed_pickle_and_deepcopy_preserve_bits_metadata_and_owned_lifetimes(self):
        original = make_numeric_input(self.env, self.env.legal_actions(), BUCKETS)
        graph = original["packed_graph"]["context"]
        expected = Graph(**graph.debug_graph())
        self.assertIs(copy.deepcopy(graph), graph)
        self.assertIs(copy.deepcopy(original)["packed_graph"]["context"], graph)
        restored = gwrl_cpp.CampaignNumericGraph.from_packed(graph.packed_state())
        self.assert_graph_equal(restored, expected)
        loaded = pickle.loads(pickle.dumps(original, protocol=5))
        self.assertEqual(validate_numeric_input(loaded, buckets=BUCKETS), len(self.env.legal_actions()))
        self.assert_graph_equal(loaded["packed_graph"]["context"], expected)
        destinations, indices = original["packed_graph"]["observation"].external_references(graph)
        actual = loaded["packed_graph"]["observation"].external_references(loaded["packed_graph"]["context"])
        np.testing.assert_array_equal(actual[0], destinations)
        np.testing.assert_array_equal(actual[1], indices)
        self.assertIsNot(restored, graph)

    def test_native_numeric_zero_and_finite_free_fields_match_public_json(self):
        value = json.loads(self.raw.serialize())
        value["state"]["politics"]["pending"]["numeric_export_fixture"] = {
            "negative_zero": -0.0, "positive_zero": 0.0, "fraction": 0.125,
            "extreme": 1.7976931348623157e308,
        }
        self.raw.restore(json.dumps(value))
        self.env = CampaignAdapter(self.raw)
        actions = self.env.legal_actions()
        self.assert_input_equal(make_numeric_input(self.env, actions, BUCKETS), make_input(self.env, actions))

    def test_graph_value_equality_compares_complete_buffers_and_numeric_bits(self):
        graph = numeric_compiler(BUCKETS).compile(self.raw.numeric_context())
        loaded = pickle.loads(pickle.dumps(graph, protocol=5))
        self.assertEqual(graph, loaded)
        self.assertEqual(graph, graph)
        self.assertNotEqual(graph, object())
        packed = graph.packed_state()
        numeric = np.array(packed["numeric"], copy=True)
        row, col = np.argwhere(numeric == 0)[0]
        numeric[row, col] = -0.0 if not np.signbit(numeric[row, col]) else 0.0
        changed = gwrl_cpp.CampaignNumericGraph.from_packed({**packed, "numeric": numeric})
        self.assertNotEqual(graph, changed)

    def test_packed_restore_rejects_corrupt_shapes_types_offsets_edges_and_metadata(self):
        graph = numeric_compiler(BUCKETS).compile(self.raw.numeric_context())
        packed = graph.packed_state()

        def modified_array(key, operation):
            value = np.array(packed[key], copy=True)
            operation(value)
            return {**packed, key: value}

        first_identity = next(iter(packed["identities"]))
        first_target = packed["identities"][first_identity][0]
        first_reference = packed["references"][0]
        invalid = {
            "unknown field": {**packed, "unknown": True},
            "missing field": {key: value for key, value in packed.items() if key != "types"},
            "wrong schema": {**packed, "schema": "future"},
            "wrong vocabulary": {**packed, "buckets": 1},
            "boolean vocabulary": {**packed, "buckets": True},
            "wrong leaf count": {**packed, "leaf_count": graph.leaf_count + 1},
            "float leaf count": {**packed, "leaf_count": float(graph.leaf_count)},
            "numeric rank": {**packed, "numeric": packed["numeric"].ravel()},
            "numeric width": {**packed, "numeric": packed["numeric"][:, :7]},
            "types dtype": {**packed, "types": packed["types"].astype(np.float64)},
            "numeric dtype": {**packed, "numeric": packed["numeric"].astype(np.float32)},
            "missing edge": {**packed, "sources": packed["sources"][:-1]},
            "missing references": {**packed, "references": packed["references"][:-1]},
            "wrong reference value": {**packed, "references": ((first_reference[0], 7), *packed["references"][1:])},
            "wrong reference source": {**packed, "references": ((-1, first_reference[1]), *packed["references"][1:])},
            "float reference source": {**packed, "references": ((float(first_reference[0]), first_reference[1]), *packed["references"][1:])},
            "empty identity": {**packed, "identities": {first_identity: ()}},
            "duplicate identity index": {**packed, "identities": {first_identity: (first_target, first_target)}},
            "negative identity index": {**packed, "identities": {first_identity: (-1,)}},
            "scalar identity target": {**packed, "identities": {first_identity: (first_reference[0],)}},
            "nonstring identity": {**packed, "identities": {1: (first_target,)}},
            "list identity target": {**packed, "identities": {first_identity: [first_target]}},
            "bad token": modified_array("token_ids", lambda value: value.__setitem__(0, BUCKETS)),
            "bad offset": modified_array("token_offsets", lambda value: value.__setitem__(0, -1)),
            "nonmonotone offsets": modified_array("token_offsets", lambda value: value.__setitem__(1, -1)),
            "bad node type": modified_array("types", lambda value: value.__setitem__(0, 6)),
            "bad edge source": modified_array("sources", lambda value: value.__setitem__(0, graph.node_count)),
            "bad edge target": modified_array("targets", lambda value: value.__setitem__(0, -1)),
            "bad relation": modified_array("relations", lambda value: value.__setitem__(0, 5)),
        }
        for number in (float("nan"), float("inf"), -float("inf")):
            invalid[f"nonfinite {number}"] = modified_array("numeric", lambda value, n=number: value.__setitem__((0, 0), n))
        for label, state in invalid.items():
            with self.subTest(label=label), self.assertRaises((ValueError, TypeError)):
                gwrl_cpp.CampaignNumericGraph.from_packed(state)


if __name__ == "__main__":
    unittest.main()
