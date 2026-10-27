"""Scoped diagnostics retain original implementations, buffers and failures."""
import copy
from dataclasses import dataclass
import itertools
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.profile_campaign_recruitment_effects import (
    Binding, EffectsConfig, EffectsStageProfiler, EXPECTED_LABELS, SCHEMA,
    compare_calls, compare_results, describe, finalize,
)


class EffectsProfilerTests(unittest.TestCase):
    def fixture(self):
        operations = SimpleNamespace()
        operations.inner = lambda value: {"bytes": b"\x00\xff", "source": value}
        operations.outer = lambda value: operations.inner(value)
        class Delegate:
            state_context = object()
            def apply(self, source, **kwargs): return operations.outer(source)
        delegate = Delegate(); fences = []; ticks = itertools.count()
        bindings = lambda _: (Binding(operations, "outer", ("outer",)), Binding(operations, "inner", ("inner",)))
        profiler = EffectsStageProfiler(delegate, synchronize=lambda: fences.append(True), clock=lambda: next(ticks), bindings=bindings)
        return operations, delegate, profiler, fences

    def test_inactive_delegation_adds_no_patches_clock_or_fences(self):
        ops, delegate, profiler, fences = self.fixture(); source = object(); original = ops.outer
        with patch.object(profiler, "bindings", side_effect=AssertionError("Implicit patch")), \
             patch.object(profiler, "clock", side_effect=AssertionError("Implicit clock")), \
             patch.object(profiler, "synchronize", side_effect=AssertionError("Implicit fence")):
            self.assertEqual(profiler.apply(source), delegate.apply(source))
        self.assertIs(ops.outer, original); self.assertEqual(fences, [])
        self.assertIs(profiler.state_context, delegate.state_context)

    def test_nested_spans_preserve_returns_and_untimed_observation_has_no_fences(self):
        ops, delegate, profiler, fences = self.fixture(); source = object(); originals = ops.outer, ops.inner
        with profiler.capture(timed=False) as observations:
            with patch.object(profiler, "clock", side_effect=AssertionError("Untimed clock")), \
                 patch.object(profiler, "synchronize", side_effect=AssertionError("Untimed fence")):
                observed = profiler.apply(source)
        self.assertEqual(fences, []); self.assertEqual((ops.outer, ops.inner), originals)
        with profiler.capture() as calls: result = profiler.apply(source)
        self.assertEqual(result, observed); self.assertEqual((ops.outer, ops.inner), originals)
        self.assertEqual([span.label for span in calls[0].spans], ["outer", "inner"])
        self.assertEqual([span.parent for span in calls[0].spans], [None, 0])
        self.assertEqual([span.seconds for span in calls[0].spans], [3, 1])
        self.assertEqual([span.exclusive_seconds for span in calls[0].spans], [2, 1])
        self.assertEqual(calls[0].total_seconds, 5)
        self.assertEqual((calls[0].prepare_seconds, calls[0].between_call_seconds, calls[0].publish_seconds), (1, 0, 1))
        self.assertTrue(compare_calls(calls[0], observations[0])["all_return_bytes_and_metadata_exact"])
        self.assertEqual(describe(calls[0])["spans"][0]["inclusive_seconds"], 3)
        with self.assertRaisesRegex(ValueError, "not timings"): describe(observations[0])

    def test_exception_restores_every_binding_capture_and_global_lock(self):
        ops, delegate, profiler, _ = self.fixture(); ordinary = ops.outer; source = object()
        def broken(value): ops.inner(value); raise RuntimeError("Original failure")
        ops.outer = broken
        with self.assertRaisesRegex(RuntimeError, "Original failure"):
            with profiler.capture(): profiler.apply(source)
        self.assertIs(ops.outer, broken); self.assertIsNone(profiler._capture)
        ops.outer = ordinary
        with profiler.capture() as calls: profiler.apply(source)
        self.assertEqual(len(calls), 1); self.assertIs(ops.outer, ordinary)

    def test_nested_or_overlapping_captures_and_trace_drift_fail_explicitly(self):
        ops, delegate, profiler, _ = self.fixture()
        with profiler.capture():
            with self.assertRaisesRegex(RuntimeError, "cannot nest"):
                with profiler.capture(): pass
        with self.assertRaises(TypeError):
            with profiler.capture(timed=1): pass
        second = EffectsStageProfiler(delegate, synchronize=lambda: None, bindings=profiler.bindings)
        original = ops.outer
        ops.outer = lambda value: second.apply(value)
        with profiler.capture(), second.capture():
            with self.assertRaisesRegex(RuntimeError, "cannot overlap"): profiler.apply(object())
        self.assertIsNot(ops.outer, original)
        ops.outer = original
        profiler.bindings = lambda _: (Binding(ops, "outer", ("outer", "unexpected_missing_call")),)
        with self.assertRaisesRegex(RuntimeError, "call count changed"):
            with profiler.capture(timed=False): profiler.apply(object())
        self.assertIs(ops.outer, original)

    def test_complete_tensor_bytes_metadata_and_intermediate_mutations_are_checked(self):
        import torch
        @dataclass(frozen=True)
        class Result:
            data: object
            flags: dict
        first = Result(torch.tensor([0, 2**63 - 1], dtype=torch.int64), {"required": torch.tensor([3])})
        equal = Result(first.data.clone(), {"required": first.flags["required"].clone()})
        self.assertEqual(compare_results(first, equal)["compared_tensors"], 2)
        equal.data[1] -= 1
        with self.assertRaisesRegex(ValueError, "tensor bits"): compare_results(first, equal)
        with self.assertRaisesRegex(ValueError, "mapping"): compare_results(first, Result(first.data, {}))
        squares = torch.ones((2, 2))
        with self.assertRaisesRegex(ValueError, "metadata"): compare_results(squares, squares.t())
        with self.assertRaisesRegex(ValueError, "metadata"): compare_results(torch.ones(4), torch.ones(5)[1:])
        with self.assertRaisesRegex(ValueError, "metadata"): compare_results(squares, squares.clone().requires_grad_())

    def test_finalizer_requires_complete_audited_trace_and_every_native_proof(self):
        config = EffectsConfig(batch_sizes=(1,), families=("small_success",), repeats=1)
        proof = {"all_return_bytes_and_metadata_exact": True, "compared_tensors": 1}
        sample = {"total_effects_seconds": .1, "prepare_seconds": .01, "between_call_setup_seconds": .01,
            "final_publish_seconds": .01, "full_native_state_history_rng_and_engine_keys_exact": True,
            "complete_output_proof": proof, "intermediate_output_proof": proof,
            "spans": [{"label": name, "parent": None, "inclusive_seconds": .001, "exclusive_seconds": .001} for name in EXPECTED_LABELS]}
        report = {"schema": SCHEMA, "status": "completed", "sources_unchanged": True,
            "cases": [{"family": "small_success", "lanes": 1, "source_unchanged": True,
                       "untimed_wrapper_all_outputs_exact": proof, "profiles": [sample]}]}
        self.assertTrue(finalize(copy.deepcopy(report), config)["effects_profile_exact"])
        for mutate in (lambda r: r.update(sources_unchanged=False), lambda r: r["cases"].clear(),
                       lambda r: r["cases"][0].update(source_unchanged=False),
                       lambda r: r["cases"][0]["profiles"][0]["spans"].pop(),
                       lambda r: r["cases"][0]["profiles"][0]["spans"][0].update(exclusive_seconds=.1),
                       lambda r: r["cases"][0]["profiles"][0].update(full_native_state_history_rng_and_engine_keys_exact=False)):
            changed = copy.deepcopy(report); mutate(changed)
            self.assertFalse(finalize(changed, config)["effects_profile_exact"])
        for kwargs in ({"devices": ("cpu",)}, {"families": ()}, {"families": ("bad",)}):
            with self.assertRaises(ValueError): EffectsConfig(**kwargs)


class EffectsProfilerIntegrationTests(unittest.TestCase):
    def test_whole_handler_and_every_effect_intermediate_match_native_without_hot_host_reads(self):
        import torch
        from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
        if not torch.backends.mps.is_available() or not mps_int64_indexing_supported(): self.skipTest("Exact MPS unavailable")
        from tests.test_campaign_resident_recruitment_chance import ResidentRecruitmentChanceTests, pending_fixture
        from tools.benchmark_campaign_resident_recruitment_chance import resident_digest
        from tools.profile_campaign_recruitment_effects import static_digest
        old = torch.get_num_threads(); torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000 / torch.mps.recommended_max_memory())
        try:
            helper = ResidentRecruitmentChanceTests()
            envs = [pending_fixture(training=True, face=1), pending_fixture(training=True, face=12, active="search")]
            before, handler, caps, expected = helper.setup(envs)
            source_hash, context_hash = resident_digest(before), static_digest(before)
            original = handler.resolve(before, expected, capacities=caps); helper.assert_native(before, original, envs)
            profiler = EffectsStageProfiler(handler.effects); handler.effects = profiler
            with profiler.capture(timed=False) as observed:
                ordinary = handler.resolve(before, expected, capacities=caps)
            torch.mps.synchronize(); compare_results(ordinary, original)
            with profiler.capture() as calls:
                with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Hot host transfer")), \
                     patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Hot host list")), \
                     patch.object(torch.Tensor, "item", side_effect=AssertionError("Hot host scalar")), \
                     patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("Hot host truth")):
                    result = handler.resolve(before, expected, capacities=caps)
            torch.mps.synchronize(); helper.assert_native(before, result, envs)
            self.assertEqual(len(calls), 1); self.assertEqual([span.label for span in calls[0].spans], list(EXPECTED_LABELS))
            self.assertTrue(compare_results(result, original)["all_return_bytes_and_metadata_exact"])
            self.assertTrue(compare_calls(calls[0], observed[0])["all_return_bytes_and_metadata_exact"])
            self.assertEqual(resident_digest(before), source_hash); self.assertEqual(static_digest(before), context_hash)
        finally: torch.set_num_threads(old)


if __name__ == "__main__": unittest.main()
