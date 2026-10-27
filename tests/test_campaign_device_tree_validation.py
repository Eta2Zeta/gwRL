"""Independent stack grammar and original serial-builder source-error oracles."""
from dataclasses import replace
import random
import struct
import unittest
from unittest.mock import patch

import torch

from studies.campaign.backends.device_state import DeviceStateBatch
from studies.campaign.backends.device_state_edits import _host_tree, _strings
from studies.campaign.backends.device_tree_validation import validate_source
from studies.campaign.backends.device_map_edits import ContainerError, MapMode, build_map_edits
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from tests.test_campaign_device_state import real_states, rich_fixture

EXACT_MPS = torch.backends.mps.is_available() and mps_int64_indexing_supported()
MASK64 = (1 << 64) - 1


def leaf(tag, count=0, bits=0):
    return [[tag, count, bits & 0xffffffff, (bits >> 32) & 0xffffffff, 1]]


def tree(tag, children):
    rows = [[tag, len(children) // 2 if tag in (7, 13) else len(children), 0, 0, 0]]
    for child in children:
        start = len(rows)
        rows += [[a, b, lo, hi, end + start] for a, b, lo, hi, end in child]
    rows[0][4] = len(rows)
    return rows


def serial_source_valid(state, selected):
    B, C = state.records.shape[:2]
    # Deliberately invalid target stops a valid source before any target bytes
    # are accessed. Later map-key failures can reuse SOURCE bit1, so a real map
    # target would conflate the source grammar with a separate lookup failure.
    result = build_map_edits(state, torch.full((B,), -1, dtype=torch.int64, device=state.device),
        torch.zeros(B, dtype=torch.int64, device=state.device),
        torch.full((B,), int(MapMode.ERASE), dtype=torch.int64, device=state.device),
        torch.zeros((B, 0, 5), dtype=torch.int64, device=state.device),
        torch.zeros(B, dtype=torch.int64, device=state.device), selected, capacity=max(C, 1))
    return (result.errors & int(ContainerError.SOURCE)) == 0


class TreeValidationSelectionTests(unittest.TestCase):
    def test_cpu_execution_is_explicitly_rejected(self):
        state = DeviceStateBatch.capture([real_states()[0]])
        with self.assertRaisesRegex(ValueError, "Apple GPU"):
            validate_source(state, torch.ones(1, dtype=torch.bool))


@unittest.skipUnless(EXACT_MPS, "Lossless Apple GPU runtime unavailable")
class DeviceTreeValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads(); torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000 / torch.mps.recommended_max_memory())
        cls.base = DeviceStateBatch.capture([rich_fixture()], device="mps")
        cls.strings = _strings(DeviceStateBatch.capture([rich_fixture()]))
        unique = {}
        for i, value in enumerate(cls.strings): unique.setdefault(value, i)
        cls.ordered_ids = [unique[value] for value in sorted(unique)]

    @classmethod
    def tearDownClass(cls):
        del cls.base
        torch.set_num_threads(cls.old_threads)

    def frame(self, forests, *, capacity=None, lengths=None, inherited=None):
        B = len(forests); C = max((len(rows) for rows in forests), default=0) if capacity is None else capacity
        values = torch.zeros((B, C, 5), dtype=torch.int64, device="mps")
        for i, rows in enumerate(forests):
            if rows: values[i, :len(rows)] = torch.tensor(rows, dtype=torch.int64, device="mps")
        return replace(self.base, records=values,
            lengths=torch.tensor([len(rows) for rows in forests] if lengths is None else lengths, dtype=torch.int64, device="mps"),
            sections=torch.zeros((B, 27), dtype=torch.int64, device="mps"),
            errors=torch.tensor([0] * B if inherited is None else inherited, dtype=torch.int64, device="mps"))

    def compare(self, state, *, selected=None, host=True):
        B, C = state.records.shape[:2]
        if selected is None: selected = [True] * B
        selection = torch.tensor(selected, dtype=torch.bool, device="mps")
        before = state.records.clone()
        result = validate_source(state, selection)
        self.assertIs(result.source, state); self.assertEqual(result.valid.dtype, torch.bool)
        self.assertEqual(result.node_errors.dtype, torch.int32); self.assertEqual(result.node_errors.shape, (B, max(C, 1)))
        self.assertTrue(torch.equal(result.valid, serial_source_valid(state, selection)))
        self.assertTrue(torch.equal(state.records, before))
        if host:
            rows, sizes = state.records.cpu().tolist(), state.lengths.cpu().tolist()
            expected = [not active or _host_tree(value[:size], self.strings)
                        for value, size, active in zip(rows, sizes, selected, strict=True)]
            self.assertEqual(result.valid.cpu().tolist(), expected)
        return result

    def test_real_complete_frames_and_every_scalar_numeric_bit_domain(self):
        real = DeviceStateBatch.capture(real_states() + [rich_fixture()], device="mps")
        selection = torch.ones(real.lane_count, dtype=torch.bool, device="mps")
        self.assertTrue(validate_source(real, selection).valid.all().item())
        self.assertTrue(torch.equal(validate_source(real, selection).valid, serial_source_valid(real, selection)))
        forests = [leaf(0), leaf(1, 0), leaf(1, 1), leaf(5, self.ordered_ids[3])]
        forests += [leaf(2, bits=value & MASK64) for value in (-2**31, -1, 0, 1, 2**31 - 1)]
        forests += [leaf(3, bits=value) for value in (0, 2**32 - 1, 2**32, 2**63, MASK64)]
        finite = (0, 1, 0x8000000000000000, 0x8000000000000001, 0x7fefffffffffffff, 0xffefffffffffffff)
        finite += tuple(struct.unpack("<Q", struct.pack("<d", x))[0] for x in (1., -1e200, 1.0000000000000002))
        forests += [leaf(4, bits=value) for value in finite]
        invalid = [leaf(1, 2), leaf(0, 1), leaf(2, bits=2**31), leaf(2, bits=(-2**31 - 1) & MASK64),
                   leaf(3, 1), leaf(4, 1), leaf(5, len(self.strings))]
        invalid += [leaf(4, bits=value) for value in (0x7ff0000000000000, 0xfff0000000000000, 0x7ff8000000000001, 0x7ff0000000000001)]
        result = self.compare(self.frame(forests + invalid))
        self.assertEqual(result.valid.cpu().tolist(), [True] * len(forests) + [False] * len(invalid))

    def test_all_containers_exact_coverage_order_and_no_record_arity_cap(self):
        ids = self.ordered_ids[:4]
        values = [leaf(0), leaf(3, bits=MASK64), tree(12, [leaf(1, 1)])]
        good = [tree(tag, values) for tag in (6, 10, 12)]
        good += [tree(tag, []) for tag in (6, 7, 8, 9, 10, 12, 13)]
        good += [tree(9, [values[2]]), tree(11, values[:2]),
                 tree(8, [leaf(2, bits=value & MASK64) for value in (-2**31, -1, 0, 2**31 - 1)]),
                 tree(8, [leaf(5, i) for i in ids])]
        good += [tree(tag, [item for i in ids for item in (leaf(5, i), values[i % 3])]) for tag in (7, 13)]
        bad = [tree(9, values[:2]), tree(11, values[:1]), tree(11, values),
               tree(8, [leaf(2), leaf(5, ids[0])]), tree(8, [leaf(2), leaf(2)]),
               tree(8, [leaf(5, ids[1]), leaf(5, ids[0])]),
               tree(7, [leaf(2), leaf(0)]), tree(13, [leaf(5, ids[0]), leaf(0), leaf(5, ids[0]), leaf(1)])]
        malformed = tree(6, [tree(6, [leaf(0)]), leaf(1)])
        for index, end in ((0, 1), (1, len(malformed) + 1), (2, 4)):
            value = copy_rows(malformed); value[index][4] = end; bad.append(value)
        forest = leaf(0) + [[0, 0, 0, 0, 2]]; bad.append(forest)
        result = self.compare(self.frame(good + bad))
        self.assertEqual(result.valid.cpu().tolist(), [True] * len(good) + [False] * len(bad))

    def test_deep_nesting_and_random_valid_and_mutated_forests_against_both_oracles(self):
        depth = 2048
        deep = [[9, 1, 0, 0, depth + 1] for _ in range(depth)] + [[0, 0, 0, 0, depth + 1]]
        self.assertEqual(self.compare(self.frame([deep])).valid.cpu().tolist(), [True])
        rng = random.Random(271)
        def generate(level=0):
            if level > 3 or rng.random() < .4:
                tag = rng.choice((0, 1, 2, 3, 4, 5))
                if tag == 1: return leaf(1, rng.randrange(2))
                if tag == 2: return leaf(2, bits=rng.randint(-2**31, 2**31 - 1) & MASK64)
                if tag == 3: return leaf(3, bits=rng.getrandbits(64))
                if tag == 4: return leaf(4, bits=rng.choice((0, 1, 0x8000000000000000, 0x7fefffffffffffff)))
                if tag == 5: return leaf(5, rng.choice(self.ordered_ids))
                return leaf(0)
            tag = rng.choice((6, 7, 8, 9, 10, 11, 12, 13))
            if tag in (7, 13):
                ids = sorted(rng.sample(self.ordered_ids, rng.randrange(5)), key=lambda i: self.strings[i])
                return tree(tag, [row for i in ids for row in (leaf(5, i), generate(level + 1))])
            if tag == 8:
                values = sorted(rng.sample(range(-100, 100), rng.randrange(5)))
                return tree(8, [leaf(2, bits=x & MASK64) for x in values])
            amount = 2 if tag == 11 else rng.randrange(2) if tag == 9 else rng.randrange(5)
            return tree(tag, [generate(level + 1) for _ in range(amount)])
        good = [generate() for _ in range(100)]; variants = []
        for rows in good:
            for _ in range(4):
                value = copy_rows(rows); index = rng.randrange(len(value)); column = rng.randrange(5)
                value[index][column] = rng.choice((-1, 0, 1, 2, 14, len(value) + 1, 2**32))
                variants.append(value)
        result = self.compare(self.frame(good + variants))
        self.assertTrue(all(result.valid[:len(good)].cpu().tolist()))

    def test_lazy_string_offsets_raw_bytes_and_byte_order_not_numeric_id_order(self):
        # An unused interior offset may be invalid. A standalone string and a
        # one-element map/set do not ask the serial predicate to read its bytes.
        base = self.frame([leaf(5, 1), tree(7, [leaf(5, 1), leaf(0)]), tree(8, [leaf(5, 1)])])
        context = shallow_context(base.context)
        self.assertFalse(hasattr(context, "container_implementation"))
        self.assertFalse(hasattr(context, "editor_implementation"))
        offsets = context.string_offsets.clone(); offsets[1] = context.string_bytes.numel() + 7
        context.string_offsets = offsets; state = replace(base, context=context)
        self.assertEqual(self.compare(state, host=False).valid.cpu().tolist(), [True, True, True])
        ordered = self.frame([tree(8, [leaf(5, 1), leaf(5, 2)])])
        ordered = replace(ordered, context=context)
        self.assertEqual(self.compare(ordered, host=False).valid.cpu().tolist(), [False])
        # Valid raw bytes include NUL/invalid UTF8; no encoding checks are added.
        strings = [b"\x00", b"\x80", b"\xff"]
        from studies.campaign.backends.device_strings import intern_bytes, pack_byte_requests
        requests, lengths = pack_byte_requests(strings, device="mps")
        pool = intern_bytes(self.base, requests, lengths, string_capacity=self.base.string_offsets.numel() + 3,
                            byte_capacity=self.base.string_bytes.numel() + requests.numel())
        ids = pool.ids.cpu().tolist()
        state = replace(self.frame([tree(8, [leaf(5, i) for i in ids])]),
                        string_bytes=pool.state.string_bytes, string_offsets=pool.state.string_offsets, suffix_usage=pool.state.suffix_usage)
        self.assertEqual(self.compare(state, host=False).valid.cpu().tolist(), [True])

    def test_usage_errors_masks_zero_capacity_and_padding_are_exact(self):
        valid = leaf(0); state = self.frame([valid, valid], capacity=17)
        records = state.records.clone(); records[:, 1:] = -99
        result = self.compare(replace(state, records=records))
        self.assertEqual(result.node_errors.cpu().tolist(), [[0] * 17] * 2)
        for changed in (replace(state, lengths=torch.tensor([0, 18], dtype=torch.int64, device="mps")),
                        replace(state, errors=torch.tensor([7, 8], dtype=torch.int64, device="mps")),
                        replace(state, suffix_usage=torch.tensor([-1, 0], dtype=torch.int64, device="mps"))):
            result = self.compare(changed, selected=[True, False], host=False)
            self.assertEqual(result.valid.cpu().tolist(), [False, True]); self.assertEqual(result.node_errors[0, 0].item(), 1)
            self.assertEqual(result.node_errors[1].cpu().tolist(), [0] * 17)
        empty = self.frame([[], []], capacity=0)
        self.assertEqual(self.compare(empty, selected=[True, False], host=False).node_errors.cpu().tolist(), [[1], [0]])
        zero = self.frame([], capacity=0)
        output = validate_source(zero, torch.empty(0, dtype=torch.bool, device="mps"))
        self.assertEqual(output.valid.shape, (0,)); self.assertEqual(output.node_errors.shape, (0, 1))

    def test_hot_validation_has_no_host_values_or_state_mutation_and_rejects_bad_layouts(self):
        state = self.base; selection = torch.ones(1, dtype=torch.bool, device="mps"); before = state.records.clone()
        with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Host list")), \
             patch.object(torch.Tensor, "item", side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("Host truth")):
            result = validate_source(state, selection)
        self.assertTrue(result.valid.item()); self.assertTrue(torch.equal(before, state.records))
        for selected in (selection.to(torch.int64), selection.reshape(1, 1), torch.ones(1, dtype=torch.bool)):
            with self.assertRaisesRegex(ValueError, "selection"): validate_source(state, selected)


def copy_rows(rows): return [list(row) for row in rows]


def shallow_context(original):
    from types import SimpleNamespace
    metadata = dict(vars(original))
    metadata["device"] = original.device
    metadata.pop("container_implementation", None)
    metadata.pop("editor_implementation", None)
    return SimpleNamespace(**metadata)


if __name__ == "__main__": unittest.main()
