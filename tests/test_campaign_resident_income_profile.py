"""The income diagnostic delegates unchanged and verifies every retained output."""
import copy
from dataclasses import dataclass, replace
import itertools
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.profile_campaign_resident_income import (
    EXPECTED_LABELS, IncomeConfig, IncomeStageProfiler, SCHEMA, compare_calls,
    compare_results, describe_call, finalize, selection,
)


class IncomeProfilerTests(unittest.TestCase):
    def fixture(self):
        import torch
        @dataclass(frozen=True)
        class Result:
            source: object
            blocks: object
            lengths: object
            errors: object
            selected: object
            capacity: object
        class Library:
            def extract_resident_income(self, source): return source.clone()
            def write_resident_income(self, *args, **kwargs):
                args[11].copy_(args[7]); args[12].fill_(2); args[13].zero_()
        module = SimpleNamespace(_kernels=lambda: library)
        editor = SimpleNamespace(replace_subtrees=lambda source, blocks, lengths, errors, selected, capacity:
                                 Result(source, blocks, lengths, errors, selected, capacity))
        class Rates:
            def compute(self, source): return source + 3
        class Income:
            def __init__(self): self.state_context = object(); self.ledger_context = SimpleNamespace(income=Rates()); self.other = None
            def extract(self, source): return module._kernels().extract_resident_income(source)
            def refresh(self, source, selected=None, *, capacity=None):
                if self.other is not None: self.other.extract(source); self.other.ledger_context.income.compute(source)
                inputs = self.extract(source); rates = self.ledger_context.income.compute(inputs)
                blocks = torch.empty_like(rates); lengths = torch.empty(1, dtype=torch.int64); errors = torch.empty_like(lengths)
                args = [None]*16; args[7] = rates; args[11:14] = [blocks, lengths, errors]
                module._kernels().write_resident_income(*args, threads=1)
                return editor.replace_subtrees(source, blocks, lengths, errors, selected, capacity)
        library = Library(); delegate = Income(); fences = []; ticks = itertools.count()
        profiler = IncomeStageProfiler(delegate, synchronize=lambda: fences.append(True), clock=lambda: next(ticks),
                                       income_module=module, editor_module=editor)
        return module, editor, delegate, profiler, fences

    def test_inactive_exact_delegation_and_service_identity_without_patches_or_fences(self):
        import torch
        module, editor, delegate, profiler, fences = self.fixture(); source = torch.tensor([0, 2**31-1])
        getter, replace_tree = module._kernels, editor.replace_subtrees
        with patch.object(profiler, "synchronize", side_effect=AssertionError("Implicit fence")), \
             patch.object(profiler, "clock", side_effect=AssertionError("Implicit clock")), \
             patch("tools.profile_campaign_resident_income._RefreshDelegate", side_effect=AssertionError("Implicit proxy")):
            compare_results(profiler.refresh(source, capacity=19), delegate.refresh(source, capacity=19))
        self.assertIs(module._kernels, getter); self.assertIs(editor.replace_subtrees, replace_tree)
        self.assertIs(profiler.state_context, delegate.state_context); self.assertEqual(fences, [])

    def test_four_original_spans_and_writer_buffers_exact_with_instance_scoped_bindings(self):
        import torch
        module, editor, delegate, profiler, fences = self.fixture(); source = torch.tensor([1, 2])
        delegate.other = type(delegate)()  # Same classes, different service: must not enter the four audited spans.
        original_getter, original_editor = module._kernels, editor.replace_subtrees
        own_extract, foreign_extract = delegate.extract, delegate.other.extract
        with profiler.capture(timed=False) as observed:
            result = profiler.refresh(source, capacity=29)
        self.assertEqual(fences, [])
        with profiler.capture() as timed:
            actual = profiler.refresh(source, capacity=29)
        self.assertIs(module._kernels, original_getter); self.assertIs(editor.replace_subtrees, original_editor)
        self.assertEqual(delegate.extract, own_extract); self.assertEqual(delegate.other.extract, foreign_extract)
        self.assertNotIn("extract", delegate.__dict__); self.assertNotIn("compute", delegate.ledger_context.income.__dict__)
        self.assertEqual([span.label for span in timed[0].execution.spans], list(EXPECTED_LABELS))
        self.assertEqual([span.parent for span in timed[0].execution.spans], [None]*4)
        self.assertTrue(compare_results(result, actual)["all_return_bytes_and_metadata_exact"])
        self.assertTrue(compare_calls(timed[0], observed[0])["all_return_bytes_and_metadata_exact"])
        self.assertIs(timed[0].writer_outputs.blocks, actual.blocks)
        self.assertEqual(describe_call(timed[0])["total_income_refresh_seconds"], 9)
        self.assertEqual([span.seconds for span in timed[0].execution.spans], [1]*4)
        with self.assertRaisesRegex(ValueError, "not timings"): describe_call(observed[0])

    def test_errors_restore_writer_getter_instance_bindings_and_shared_patch_lock(self):
        import torch
        module, editor, delegate, profiler, _ = self.fixture(); source = torch.tensor([1])
        getter, replace_tree = module._kernels, editor.replace_subtrees
        library = getter(); original = library.write_resident_income
        with patch.object(library, "write_resident_income", side_effect=RuntimeError("Original writer failure")):
            with self.assertRaisesRegex(RuntimeError, "Original writer failure"):
                with profiler.capture(): profiler.refresh(source)
        self.assertIs(module._kernels, getter); self.assertIs(editor.replace_subtrees, replace_tree)
        self.assertNotIn("extract", delegate.__dict__); self.assertIsNone(profiler._capture)
        self.assertEqual(library.write_resident_income, original)
        with profiler.capture(timed=False) as calls: profiler.refresh(source)
        self.assertEqual(len(calls), 1)

    def test_nested_overlap_and_call_drift_are_rejected_and_all_globals_restored(self):
        import torch
        module, editor, delegate, profiler, _ = self.fixture(); source = torch.tensor([1])
        with profiler.capture():
            with self.assertRaisesRegex(RuntimeError, "cannot nest"):
                with profiler.capture(): pass
        with self.assertRaises(TypeError):
            with profiler.capture(timed=1): pass
        second = IncomeStageProfiler(delegate, synchronize=lambda: None, income_module=module, editor_module=editor)
        extract = delegate.extract; getter = module._kernels
        def nested(value): return second.refresh(value)
        with patch.object(delegate, "extract", nested):
            with profiler.capture(), second.capture():
                with self.assertRaisesRegex(RuntimeError, "cannot overlap"): profiler.refresh(source)
        self.assertIs(module._kernels, getter); self.assertEqual(delegate.extract, extract)
        with patch.object(delegate.ledger_context.income, "compute", lambda _: delegate.extract(source)):
            with profiler.capture(timed=False):
                with self.assertRaisesRegex(RuntimeError, "call count changed"): profiler.refresh(source)
        self.assertIs(module._kernels, getter)

    def test_complete_intermediate_source_writer_storage_and_version_comparisons(self):
        import torch
        _, _, _, profiler, _ = self.fixture(); source = torch.tensor([1, 2])
        with profiler.capture(timed=False) as first: profiler.refresh(source.clone())
        with profiler.capture(timed=False) as second: profiler.refresh(source.clone())
        self.assertIsNot(first[0].execution.source, second[0].execution.source)
        compare_calls(first[0], second[0])
        second[0].writer_outputs.blocks[0] += 1
        with self.assertRaisesRegex(ValueError, "tensor bits"): compare_calls(first[0], second[0])
        a = torch.ones(2); b = a.clone(); b.add_(1); b.sub_(1)
        with self.assertRaisesRegex(ValueError, "version metadata"): compare_results(a, b)
        with self.assertRaisesRegex(ValueError, "storage/version metadata"): compare_results(a, torch.ones(3)[:2])
        with self.assertRaisesRegex(ValueError, "metadata"): compare_results(torch.ones((2, 2)), torch.ones((2, 2)).t())

    def test_finalizer_rejects_incomplete_traces_proofs_or_changed_selection(self):
        config = IncomeConfig(batch_sizes=(1,), families=("small_success",), repeats=1)
        proof = {"all_return_bytes_and_metadata_exact": True, "compared_tensors": 1}
        profile = {"total_income_refresh_seconds": .1, "prepare_seconds": .01, "between_call_setup_seconds": .01,
                   "final_publish_seconds": .01, "full_native_state_history_rng_and_engine_keys_exact": True,
                   "complete_output_proof": proof, "intermediate_output_proof": proof,
                   "spans": [{"label": name, "parent": None, "inclusive_seconds": .001, "exclusive_seconds": .001} for name in EXPECTED_LABELS]}
        report = {"schema": SCHEMA, "status": "completed", "sources_unchanged": True,
                  "selected_implementation": selection(config), "cases": [{"family": "small_success", "lanes": 1,
                  "source_unchanged": True, "untimed_wrapper_all_outputs_exact": proof, "profiles": [profile]}]}
        self.assertTrue(finalize(copy.deepcopy(report), config)["income_profile_exact"])
        for mutate in (lambda r: r.update(sources_unchanged=False), lambda r: r["cases"].clear(),
                       lambda r: r["selected_implementation"].update(editor="parallel"),
                       lambda r: r["cases"][0].update(source_unchanged=False),
                       lambda r: r["cases"][0]["profiles"][0]["spans"].pop(),
                       lambda r: r["cases"][0]["profiles"][0]["spans"][0].update(parent=0),
                       lambda r: r["cases"][0]["profiles"][0].update(full_native_state_history_rng_and_engine_keys_exact=False)):
            changed = copy.deepcopy(report); mutate(changed)
            self.assertFalse(finalize(changed, config)["income_profile_exact"])
        for kwargs in ({"devices": ("cpu",)}, {"families": ()}, {"editor_implementation": "bad"}):
            with self.assertRaises(ValueError): IncomeConfig(**kwargs)


class IncomeProfilerIntegrationTests(unittest.TestCase):
    def test_complete_handler_and_all_income_intermediates_match_native_no_hot_host_reads(self):
        import torch
        from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
        if not torch.backends.mps.is_available() or not mps_int64_indexing_supported(): self.skipTest("Exact MPS unavailable")
        from tests.test_campaign_resident_recruitment_chance import ResidentRecruitmentChanceTests, pending_fixture
        from tools.profile_campaign_recruitment_effects import static_digest
        from tools.benchmark_campaign_resident_recruitment_chance import resident_digest
        old = torch.get_num_threads(); torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
        try:
            helper = ResidentRecruitmentChanceTests()
            envs = [pending_fixture(training=True, face=1), pending_fixture(training=True, face=12, active="search")]
            before, handler, caps, expected = helper.setup(envs)
            source_hash, context_hash = resident_digest(before), static_digest(before)
            original = handler.resolve(before, expected, capacities=caps); helper.assert_native(before, original, envs)
            profiled = IncomeStageProfiler(handler.income); handler.income = profiled
            with profiled.capture(timed=False) as observed: ordinary = handler.resolve(before, expected, capacities=caps)
            torch.mps.synchronize(); compare_results(ordinary, original)
            with profiled.capture() as calls:
                with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Hot host transfer")), \
                     patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Hot host list")), \
                     patch.object(torch.Tensor, "item", side_effect=AssertionError("Hot host scalar")), \
                     patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("Hot host truth")):
                    result = handler.resolve(before, expected, capacities=caps)
            torch.mps.synchronize(); helper.assert_native(before, result, envs)
            self.assertEqual(len(calls), 1); self.assertEqual([span.label for span in calls[0].execution.spans], list(EXPECTED_LABELS))
            self.assertTrue(compare_results(result, original)["all_return_bytes_and_metadata_exact"])
            self.assertTrue(compare_calls(calls[0], observed[0])["all_return_bytes_and_metadata_exact"])
            self.assertEqual(resident_digest(before), source_hash); self.assertEqual(static_digest(before), context_hash)
        finally: torch.set_num_threads(old)


if __name__ == "__main__": unittest.main()
