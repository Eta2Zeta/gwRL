"""Parallel replacement grammar keeps all editor errors/layouts/rollback exact."""
from dataclasses import replace
import random
import unittest
from unittest.mock import patch

import torch

import tests.test_campaign_device_state_edits as baseline
import tests.test_campaign_parallel_state_edits as inherited
from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
from studies.campaign.backends.device_state_edits import EditError, _host_tree, _strings, replace_subtrees
from tests.test_campaign_device_tree_validation import leaf, tree, shallow_context


class GeneratedPlanTests(unittest.TestCase):
    def test_only_original_grammar_predicate_name_and_bool_binding_change(self):
        from studies.campaign.backends import device_state_edits_parallel as module
        plan = module._validated_plan.replace("kernel void parallel_edit_plan_validated(", module._PLAN_BEGIN, 1)
        plan = plan.replace("device const long* suffix_usage[[buffer(19)]],device const bool* replacement_valid[[buffer(20)]],uint lane[[thread_position_in_grid]]){", module._signature, 1)
        plan = plan.replace("replacement_valid[lane]", module._predicate, 1)
        self.assertEqual(plan, module._plan)
        body = module._validated_plan.split("){", 1)[1]
        self.assertTrue(all(name not in body for name in ("stack_ends", "stack_remaining", "stack_previous")))


@unittest.skipUnless(baseline.EXACT_MPS, "Lossless Apple GPU required")
class ParallelReplacementValidationTests(inherited.ParallelStateEditTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())

    def setUp(self):
        super().setUp(); self.contexts = {}
        def dispatch(state, *args, **kwargs):
            if state.device.type == "mps": state = self.pp(state)
            return replace_subtrees(state, *args, **kwargs)
        self.switch_pp = patch.object(inherited, "replace_subtrees", side_effect=dispatch)
        self.switch_pp.start(); self.addCleanup(self.switch_pp.stop)

    def pp(self, state):
        key = id(state.context)
        if key not in self.contexts:
            self.contexts[key] = (state.context, DeviceStateContext(state.context.native, "mps",
                editor_implementation="parallel", container_implementation="parallel"))
        return replace(state, context=self.contexts[key][1])

    def compare(self, state, args, **kwargs):
        reference = replace_subtrees(state, *args, implementation="reference", **kwargs)
        old = replace_subtrees(state, *args, implementation="parallel", **kwargs)
        # Select new grammar only, keeping the identical static context/pool.
        current = self.pp(state)
        actual = replace_subtrees(current, *args, implementation="parallel", **kwargs)
        for expected in (reference, old):
            for name in ("records", "lengths", "sections", "string_bytes", "string_offsets", "suffix_usage", "errors"):
                self.assertTrue(torch.equal(getattr(actual.state, name), getattr(expected.state, name)), name)
            for name in ("errors", "required_capacity", "accepted", "committed"):
                self.assertTrue(torch.equal(getattr(actual, name), getattr(expected, name)), name)
        return actual

    def forest_args(self, state, forests):
        B = len(forests); R = max((len(rows) for rows in forests), default=0)
        state = state.fork([0]*B)
        blocks = torch.zeros((B, R, 5), dtype=torch.int64, device="mps")
        for i, rows in enumerate(forests):
            if rows: blocks[i, :len(rows)] = torch.tensor(rows, dtype=torch.int64, device="mps")
        args = (state.section("random.test_tape").contiguous(), blocks,
                torch.tensor([len(rows) for rows in forests], dtype=torch.int64, device="mps"),
                torch.ones(B, dtype=torch.bool, device="mps"))
        return state, args

    def test_random_deep_malformed_blocks_all_flags_sizes_and_padding_match_three_paths(self):
        state, _ = baseline.fixture("mps"); rng = random.Random(439)
        ids = list(range(min(state.context.string_count, 7)))
        def generate(level=0):
            if level >= 3 or rng.random() < .4: return rng.choice([leaf(0), leaf(1, rng.randrange(2)), leaf(2, bits=rng.randrange(2**31)), leaf(3, bits=rng.getrandbits(64)), leaf(5, rng.choice(ids))])
            tag = rng.choice((6, 9, 10, 11, 12)); count = 2 if tag == 11 else rng.randrange(2) if tag == 9 else rng.randrange(4)
            return tree(tag, [generate(level+1) for _ in range(count)])
        good = [generate() for _ in range(40)]
        deep = [[6, 1, 0, 0, 2049] for _ in range(2048)] + [[0, 0, 0, 0, 2049]]
        good += [deep, tree(10, [leaf(3, bits=2**64-1)]*129)]
        variants = []
        for rows in good[:40]:
            for _ in range(3):
                value = [list(row) for row in rows]; at = rng.randrange(len(value)); col = rng.randrange(5)
                value[at][col] = rng.choice((-1, 0, 1, 14, len(value)+1, 2**32)); variants.append(value)
        strings = _strings(DeviceStateBatch.capture([baseline.fixture()[1][0]]))
        source, args = self.forest_args(state, good+variants)
        actual = self.compare(source, args, capacity=source.records.shape[1]+args[1].shape[1], allow_type_change=True)
        wanted = [not _host_tree(rows, strings) for rows in good+variants]
        self.assertEqual(((actual.errors & int(EditError.BLOCK)) != 0).cpu().tolist(), wanted)

    def test_combined_error_order_required_capacity_and_lazy_validity_consultation(self):
        state, _ = baseline.fixture("mps", count=2)
        args = list(baseline.arguments(state, "random.search", baseline.tape([1, 2])))
        args[1][:, 1, 0] = 99
        actual = self.compare(state, args)
        self.assertEqual(actual.errors.cpu().tolist(), [int(EditError.BLOCK|EditError.CAPACITY)]*2)
        self.assertEqual(actual.required_capacity.cpu().tolist(), [state.records.shape[1]+2]*2)
        roots = args[0].clone(); roots[0] = -1
        actual = self.compare(state, (roots, *args[1:]))
        self.assertEqual(actual.errors[0].item(), int(EditError.TARGET))
        self.assertEqual(actual.required_capacity[0].item(), state.lengths[0].item())
        for changed in (replace(state, errors=state.errors+1), replace(state, suffix_usage=state.suffix_usage+100000)):
            self.compare(changed, args)
        # Validator sees invalid block length but original source/target checks
        # continue to decide the exact combined bits and required-size timing.
        sizes = args[2].clone(); sizes[0] = 0; sizes[1] = args[1].shape[1]+1
        self.compare(state, (args[0], args[1], sizes, args[3]))

    def test_lazy_invalid_string_offsets_and_legacy_missing_policy_reference(self):
        state, _ = baseline.fixture("mps"); context = shallow_context(state.context)
        self.assertFalse(hasattr(context, "container_implementation"))
        original = replace(state, context=context)
        args = baseline.arguments(original, "random.test_tape", leaf(5, 1))
        with patch("studies.campaign.backends.device_state_edits_validated.validate_replacement", side_effect=AssertionError("Legacy path changed")):
            replace_subtrees(original, *args, implementation="parallel", allow_type_change=True)
        context.container_implementation = "parallel"; context.editor_implementation = "parallel"
        offsets = context.string_offsets.clone(); offsets[1] = context.string_bytes.numel()+9
        context.string_offsets = offsets
        lazy = replace(state, context=context)
        for rows in (leaf(5, 1), tree(7, [leaf(5, 1), leaf(0)]), tree(8, [leaf(5, 1)]), tree(8, [leaf(5, 1), leaf(5, 2)])):
            args = baseline.arguments(lazy, "random.test_tape", rows)
            reference = replace_subtrees(lazy, *args, implementation="reference", capacity=state.records.shape[1]+len(rows), allow_type_change=True)
            actual = replace_subtrees(lazy, *args, implementation="parallel", capacity=state.records.shape[1]+len(rows), allow_type_change=True)
            self.assertTrue(torch.equal(reference.errors, actual.errors)); self.assertTrue(torch.equal(reference.state.records, actual.state.records))

    def test_zero_source_or_replacement_capacity_partial_masks_and_all_false_are_exact(self):
        state, _ = baseline.fixture("mps", count=2)
        roots = state.section("random.search").contiguous()
        for C in (state.records.shape[1], 0):
            source = state if C else replace(state, records=state.records[:, :0].contiguous())
            for R in (0, 1):
                blocks = torch.zeros((2, R, 5), dtype=torch.int64, device="mps")
                if R: blocks[:, 0] = torch.tensor([99, 0, 0, 0, 1], device="mps")
                for chosen in ([True, True], [True, False], [False, False]):
                    args = (roots, blocks, torch.full((2,), R, dtype=torch.int64, device="mps"), torch.tensor(chosen, device="mps"))
                    self.compare(source, args)

    def test_hot_path_recomputes_every_time_and_borrows_all_pool_bits_without_host_reads(self):
        from studies.campaign.backends import device_state_edits_validated as helper
        state, _ = baseline.fixture("mps"); state = self.pp(state)
        args = baseline.arguments(state, "random.test_tape", baseline.tape([1, 12]))
        original = helper.validate_replacement
        with patch.object(helper, "validate_replacement", wraps=original) as validate:
            with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Hot host transfer")), \
                 patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Hot host values")), \
                 patch.object(torch.Tensor, "item", side_effect=AssertionError("Hot host scalar")), \
                 patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("Hot host truth")):
                first = replace_subtrees(state, *args, capacity=state.records.shape[1]+3)
                second = replace_subtrees(state, *args, capacity=state.records.shape[1]+3)
        self.assertEqual(validate.call_count, 2); self.assertTrue(torch.equal(first.state.records, second.state.records))
        checked = original(state, args[1], args[2], args[3])
        self.assertIs(checked.source.context, state.context); self.assertIs(checked.source.string_bytes, state.string_bytes)
        self.assertIs(checked.source.string_offsets, state.string_offsets); self.assertIs(checked.source.suffix_usage, state.suffix_usage)
        self.assertEqual(checked.source.errors.cpu().tolist(), [0])

    def test_complete_pp_transactions_keep_full_native_state_history_rng_and_keys(self):
        import tests.test_campaign_resident_recruitment_chance as whole
        envs = [whole.pending_fixture(training=True, face=1), whole.pending_fixture(training=True, face=12, active="search")]
        def context(*args, **kwargs):
            return DeviceStateContext(*args, **kwargs, editor_implementation="parallel", container_implementation="parallel")
        helper = whole.ResidentRecruitmentChanceTests()
        with patch.object(whole, "DeviceStateContext", context): before, handler, caps, expected = helper.setup(envs)
        result = handler.resolve(before, expected, capacities=caps)
        helper.assert_native(before, result, envs)
        self.assertTrue(result.committed.item())


if __name__ == "__main__": unittest.main()
