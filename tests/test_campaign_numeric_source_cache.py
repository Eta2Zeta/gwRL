"""Authoritative complete source keys reuse graphs without merging game choices."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
import unittest
from unittest import mock

import gwrl_cpp
import numpy as np

from studies.campaign import features
from studies.campaign.features import (NUMERIC_SCHEMA, cached_numeric_action, cached_numeric_context,
                                      compile_graph_python, make_input, make_numeric_input)
from studies.shared.campaign_adapter import CampaignAdapter

SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"
BUCKETS = 128


class CampaignNumericSourceCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial = gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO), 3, 91, training_actions=True)

    def setUp(self):
        features._NUMERIC_ACTION_SOURCES.clear()
        features._NUMERIC_CONTEXT_SOURCES.clear()

    def env(self, order=("axis", "allies", "comintern")):
        return CampaignAdapter(self.initial.clone(), interrupt_order=order)

    def assert_oracle(self, graph, value, buckets=BUCKETS):
        expected = compile_graph_python(json.loads(features.canonical(value)), buckets)
        debug = graph.debug_graph()
        for field in ("token_ids", "token_offsets", "types", "edges", "identities", "references", "leaf_count"):
            self.assertEqual(debug[field], getattr(expected, field), field)
        np.testing.assert_array_equal(graph.arrays()["numeric"].view(np.uint64),
                                      np.asarray(expected.numeric, dtype=np.float64).view(np.uint64))

    def test_independent_roots_share_complete_context_actions_and_factor_sources(self):
        first, second = self.env(), self.env()
        a = make_numeric_input(first, first.legal_actions(), BUCKETS)
        b = make_numeric_input(second, second.legal_actions(), BUCKETS)
        self.assertEqual(a["schema"], NUMERIC_SCHEMA)
        self.assertIs(a["packed_graph"]["context"], b["packed_graph"]["context"])
        self.assertEqual(len(a["packed_graph"]["actions"]), len(b["packed_graph"]["actions"]))
        for left, right in zip(a["packed_graph"]["actions"], b["packed_graph"]["actions"], strict=True):
            self.assertIs(left, right)
        self.assertIsNot(a["packed_graph"]["observation"], b["packed_graph"]["observation"])
        self.assertEqual(a["packed_graph"]["action_factors"], b["packed_graph"]["action_factors"])
        for cache in (features._NUMERIC_ACTION_SOURCES, features._NUMERIC_CONTEXT_SOURCES):
            self.assertGreater(cache.cache_info()["hits"], 0)
            self.assertLessEqual(cache.bytes, cache.byte_limit)
        raw = make_input(first, first.legal_actions())
        self.assert_oracle(a["packed_graph"]["context"], raw["context"])
        self.assert_oracle(a["packed_graph"]["observation"], raw["observation"])
        for graph, action in zip(a["packed_graph"]["actions"], raw["actions"], strict=True):
            self.assert_oracle(graph, action)

    def test_wrapper_fields_raw_parameters_and_vocabulary_are_all_in_action_identity(self):
        raw = self.initial.clone()
        legal = raw.legal_actions()
        pair = next(((left, right) for left in legal for right in legal
                     if left.kind == right.kind and left.parameters != right.parameters), None)
        self.assertIsNotNone(pair, "Fixture must exercise different complete parameters in the same family")
        first, second = pair
        variants = [first.scheduled_snapshot("same-wrapper", "play", "axis"),
                    first.scheduled_snapshot("different-wrapper", "play", "axis"),
                    first.scheduled_snapshot("same-wrapper", "interrupt", "axis"),
                    first.scheduled_snapshot("same-wrapper", "play", "allies"),
                    second.scheduled_snapshot("same-wrapper", "play", "axis")]
        prepared = [cached_numeric_action(snapshot, BUCKETS) for snapshot in variants]
        self.assertEqual(len({id(graph) for graph, _ in prepared}), len(variants))
        for snapshot, (graph, factors) in zip(variants, prepared, strict=True):
            self.assert_oracle(graph, snapshot.to_python())
            self.assertEqual(factors, features.action_factors(snapshot.to_python()))
        original = first.scheduled_snapshot("same-wrapper", "play", "axis")
        same, _ = cached_numeric_action(original, BUCKETS)
        self.assertIs(same, prepared[0][0])
        other, _ = cached_numeric_action(original, BUCKETS * 2)
        self.assertIsNot(same, other)
        self.assert_oracle(other, original.to_python(), BUCKETS * 2)

    def test_changed_position_reuses_only_unchanged_actions_and_rebuilds_observation(self):
        env = self.env()
        while env.decision_kind() == "declaration_offer":
            env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))
        menu = env.legal_actions()
        first = make_numeric_input(env, menu, BUCKETS)
        before = {action.numeric_snapshot().cache_key: graph
                  for action, graph in zip(menu, first["packed_graph"]["actions"], strict=True)}
        env.apply_action(next(action for action in menu if action.raw["kind"] == "economy_purchase"))
        while env.decision_kind() == "declaration_offer":
            env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))
        menu = env.legal_actions()
        second = make_numeric_input(env, menu, BUCKETS)
        after = {action.numeric_snapshot().cache_key: graph
                 for action, graph in zip(menu, second["packed_graph"]["actions"], strict=True)}
        common = before.keys() & after.keys()
        self.assertTrue(common, "At least the unchanged phase completion choice should remain legal")
        for key in common:
            self.assertIs(before[key], after[key])
        self.assertIsNot(first["packed_graph"]["observation"], second["packed_graph"]["observation"])
        raw = make_input(env, menu)
        self.assert_oracle(second["packed_graph"]["observation"], raw["observation"])
        for graph, action in zip(second["packed_graph"]["actions"], raw["actions"], strict=True):
            self.assert_oracle(graph, action)

    def test_context_content_and_vocabulary_changes_never_alias(self):
        first, second = self.env(), self.env(("comintern", "allies", "axis"))
        a = make_numeric_input(first, first.legal_actions(), BUCKETS)
        b = make_numeric_input(second, second.legal_actions(), BUCKETS)
        c = make_numeric_input(first, first.legal_actions(), BUCKETS * 2)
        self.assertNotEqual(a["context_key"], b["context_key"])
        self.assertEqual(a["context_key"], c["context_key"])
        self.assertEqual(len({id(item["packed_graph"]["context"]) for item in (a, b, c)}), 3)
        self.assert_oracle(b["packed_graph"]["context"], make_input(second, second.legal_actions())["context"])

    def test_sources_without_native_authoritative_action_key_are_never_interned(self):
        snapshot = self.initial.legal_actions()[0].scheduled_snapshot("overridden", "play", "axis").scheduled_context(
            "test", ["axis", "allies", "comintern"])
        self.assertIsNone(getattr(snapshot, "cache_key", None))
        first, factors = cached_numeric_action(snapshot, BUCKETS)
        second, other_factors = cached_numeric_action(snapshot, BUCKETS)
        self.assertIsNot(first, second)
        self.assertEqual(factors, other_factors)
        self.assertEqual(features._NUMERIC_ACTION_SOURCES.cache_info()["entries"], 0)
        class Foreign:
            cache_key = ("same-wrapper", "play", "axis", "pretended-authority")
            def factor_json(self):
                return ('"move"', '{}', '{}', '{}')
        with mock.patch.object(features, "compile_numeric", side_effect=[first, second]) as compile_source:
            self.assertIs(cached_numeric_action(Foreign(), BUCKETS)[0], first)
            self.assertIs(cached_numeric_action(Foreign(), BUCKETS)[0], second)
        self.assertEqual(compile_source.call_count, 2)
        self.assertEqual(features._NUMERIC_ACTION_SOURCES.cache_info()["entries"], 0)

    def test_global_cache_byte_limits_include_keys_factors_and_native_storage(self):
        env = self.env()
        prepared = make_numeric_input(env, env.legal_actions(), BUCKETS)
        for cache in (features._NUMERIC_ACTION_SOURCES, features._NUMERIC_CONTEXT_SOURCES):
            info = cache.cache_info()
            self.assertEqual(info["bytes"], sum(size for _, size in cache.values.values()))
            self.assertLessEqual(info["bytes"], info["byte_limit"])
            for key, (value, size) in cache.values.items():
                graph = value[0] if isinstance(value, tuple) else value
                self.assertGreaterEqual(size, graph.nbytes + features._source_key_bytes(key))
        cache = features._NUMERIC_ACTION_SOURCES
        limits = cache.byte_limit, cache.entry_limit
        try:
            cache.clear()
            cache.byte_limit, cache.entry_limit = 1, 1
            action = env.legal_actions()[0]
            graph, factors = cached_numeric_action(action.numeric_snapshot(), BUCKETS)
            self.assertEqual(cache.cache_info()["entries"], 0)
            self.assertEqual(cache.bytes, 0)
            self.assert_oracle(graph, action.features())
        finally:
            cache.byte_limit, cache.entry_limit = limits
        self.assertEqual(prepared["packed_graph"]["context"].token_buckets, BUCKETS)

    def test_publication_double_check_reuses_one_handle_and_lru_is_bounded(self):
        cache = features._NumericSourceCache(8, 2)
        barrier = threading.Barrier(4)
        def one(index):
            self.assertIsNone(cache.get(("same",)))
            barrier.wait(timeout=5)
            return cache.publish(("same",), object(), 4)
        with ThreadPoolExecutor(max_workers=4) as pool:
            values = list(pool.map(one, range(4)))
        self.assertEqual(len({id(value) for value in values}), 1)
        self.assertEqual(cache.bytes, 4)
        cache.publish(("second",), "b", 4)
        cache.get(("same",))
        cache.publish(("third",), "c", 4)
        self.assertIsNone(cache.get(("second",)))
        self.assertEqual(cache.cache_info()["entries"], 2)
        self.assertEqual(cache.bytes, 8)
        cache.clear()
        self.assertEqual(cache.cache_info()["entries"], 0)
        self.assertEqual(cache.bytes, 0)


if __name__ == "__main__":
    unittest.main()
