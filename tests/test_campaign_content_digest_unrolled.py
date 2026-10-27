"""Alternate compression retains every native identity byte and error mask."""
import hashlib
import random
import time
import unittest
from dataclasses import replace
from unittest.mock import patch

import torch
import gwrl_cpp

from studies.campaign.backends.content_digest_metal import (
    MessageBatch, RangedMessageBatch, content_digests_metal, inspect_digests, pack_messages,
)
from studies.campaign.backends.content_digest_unrolled import UNROLLED_SOURCE


class UnrolledDigestSelectionTests(unittest.TestCase):
    def test_alternative_is_explicit_and_group_size_has_strict_host_metadata(self):
        cpu = pack_messages([b"abc"])
        for value in ("unknown", "unrolled_group"):
            with self.assertRaisesRegex(ValueError, "implementation"):
                content_digests_metal(cpu, implementation=value)
        for value in (True, False, 0, -1, 1.5, "32"):
            with self.assertRaisesRegex(ValueError, "group size"):
                content_digests_metal(cpu, implementation="unrolled", group_size=value)
        with self.assertRaisesRegex(ValueError, "Apple GPU"):
            content_digests_metal(cpu, implementation="unrolled", group_size=1)

    def test_generated_schedule_has_sixteen_scalar_words_and_literal_round_constants(self):
        self.assertNotIn("w[", UNROLLED_SOURCE)
        self.assertEqual(UNROLLED_SOURCE.count("const uint t1 ="), 64)
        self.assertEqual(UNROLLED_SOURCE.count("uint w"), 16)
        self.assertIn("0x428a2f98u", UNROLLED_SOURCE)
        self.assertIn("0xc67178f2u", UNROLLED_SOURCE)


@unittest.skipUnless(torch.backends.mps.is_available(), "Apple GPU unavailable")
class UnrolledMetalDigestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000 / torch.mps.recommended_max_memory())

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def assert_same(self, batch, *, group_size=None):
        expected = content_digests_metal(batch)
        with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Hot host transfer")), \
             patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Hot host list")), \
             patch.object(torch.Tensor, "item", side_effect=AssertionError("Hot host scalar")), \
             patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("Hot tensor truth")):
            actual = content_digests_metal(batch, implementation="unrolled", group_size=group_size)
        for name in ("words", "hex_bytes", "errors", "batch_error", "count"):
            self.assertTrue(torch.equal(getattr(actual, name), getattr(expected, name)), name)
        return actual

    def test_block_boundaries_all_bytes_utf8_and_unaligned_ranges_match_native(self):
        rng = random.Random(1951)
        messages = [b"", b"abc", b"\x00", bytes(range(256)), "蒙古 / Ma Clique".encode(), b"\xff\x80\x00"]
        messages += [rng.randbytes(n) for n in (1, 7, 54, 55, 56, 57, 63, 64, 65, 111, 112, 119,
                                                   120, 127, 128, 129, 511, 512, 1000, 10000)]
        expected = tuple(hashlib.sha256(value).hexdigest() for value in messages)
        self.assertEqual(tuple(gwrl_cpp.campaign_content_digest_probe(messages)["digests"]), expected)
        packed = pack_messages(messages, device="mps")
        for group in (None, 1, 4, 32):
            self.assertEqual(inspect_digests(self.assert_same(packed, group_size=group)), expected)
        data = bytearray(b"gap"); ranges = []
        for value in messages:
            begin = len(data); data.extend(value); ranges.append((begin, len(data))); data.extend(b"\x00gap\xff")
        ranged = RangedMessageBatch(torch.tensor(data, dtype=torch.uint8, device="mps"),
            torch.tensor(ranges, dtype=torch.int64, device="mps"), packed.count)
        self.assertEqual(inspect_digests(self.assert_same(ranged, group_size=4)), expected)

    def test_long_native_state_and_engine_identity_messages_are_exact(self):
        from tools.benchmark_campaign_content_digests import DigestConfig, identity_messages
        rows = identity_messages(DigestConfig(batch_sizes=(1,)), time.monotonic() + 30)
        state_messages = [row["message"] for row in rows]
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(len(value) > 50_000 for value in state_messages))
        messages = state_messages + [row["outer_engine_message"] for row in rows]
        expected = tuple(hashlib.sha256(value).hexdigest() for value in messages)
        self.assertEqual(tuple(gwrl_cpp.campaign_content_digest_probe(messages)["digests"]), expected)
        result = self.assert_same(pack_messages(messages, device="mps"), group_size=4)
        self.assertEqual(inspect_digests(result), expected)
        for row in rows:
            self.assertEqual(hashlib.sha256(row["message"]).hexdigest(), row["state_key"])
            self.assertEqual(hashlib.sha256(row["outer_engine_message"]).hexdigest(), row["engine_key"])

    def test_random_long_messages_and_masked_spare_ranges_are_unchanged(self):
        rng = random.Random(713)
        messages = [rng.randbytes(n) for n in (58_000, 60_000, 62_000, 65_535, 65_536, 65_537)]
        batch = pack_messages(messages, device="mps")
        self.assertEqual(inspect_digests(self.assert_same(batch, group_size=32)),
                         tuple(hashlib.sha256(value).hexdigest() for value in messages))
        spare = replace(batch, count=torch.tensor([2], dtype=torch.int64, device="mps"))
        actual = self.assert_same(spare)
        self.assertEqual(actual.errors.cpu().tolist(), [0] * len(messages))
        self.assertEqual(actual.words[2:].cpu().tolist(), [[0] * 8] * (len(messages) - 2))
        self.assertEqual(actual.hex_bytes[2:].cpu().tolist(), [[0] * 64] * (len(messages) - 2))
        ranges = torch.tensor([[0, 58_000], [58_000, 118_000], [-1, 2**63 - 1]], dtype=torch.int64, device="mps")
        ranged = RangedMessageBatch(batch.data, ranges, torch.tensor([2], dtype=torch.int64, device="mps"))
        masked = self.assert_same(ranged, group_size=32)
        self.assertEqual(inspect_digests(masked), tuple(hashlib.sha256(value).hexdigest() for value in messages[:2]))
        self.assertEqual(masked.errors.cpu().tolist(), [0, 0, 0])

    def test_invalid_actual_counts_ranges_and_empty_capacity_retain_exact_errors(self):
        packed = pack_messages([b"abc", b"def"], device="mps")
        for actual in (-1, 3, 2**63 - 1):
            value = self.assert_same(replace(packed, count=torch.tensor([actual], dtype=torch.int64, device="mps")), group_size=32)
            self.assertEqual(value.batch_error.cpu().tolist(), [1])
            self.assertEqual(value.errors.cpu().tolist(), [1, 1])
            with self.assertRaisesRegex(ValueError, "count"): inspect_digests(value)
        for offsets in ((-1, 3, 6), (0, -1, 6), (0, 7, 6), (0, 3, 7)):
            value = self.assert_same(replace(packed, offsets=torch.tensor(offsets, dtype=torch.int64, device="mps")))
            with self.assertRaisesRegex(ValueError, "offsets"): inspect_digests(value)
        ranged = RangedMessageBatch(packed.data, torch.tensor([[2, 1], [-1, 4], [0, 9], [0, 0]],
            dtype=torch.int64, device="mps"), torch.tensor([3], dtype=torch.int64, device="mps"))
        value = self.assert_same(ranged, group_size=4)
        self.assertEqual(value.errors.cpu().tolist(), [2, 2, 2, 0])
        empty = pack_messages([], device="mps")
        for group in (None, 1, 32):
            self.assertEqual(inspect_digests(self.assert_same(empty, group_size=group)), ())
            invalid = self.assert_same(replace(empty, count=torch.tensor([1], dtype=torch.int64, device="mps")), group_size=group)
            self.assertEqual(invalid.batch_error.cpu().tolist(), [1])
        self.assertEqual(inspect_digests(self.assert_same(replace(packed,
            count=torch.tensor([0], dtype=torch.int64, device="mps")))), ())

    def test_group_limit_and_invalid_layouts_are_rejected_before_dispatch(self):
        packed = pack_messages([b"abc"], device="mps")
        with self.assertRaisesRegex(ValueError, "Metal kernel limit"):
            content_digests_metal(packed, implementation="unrolled", group_size=1 << 20)
        for batch in (replace(packed, count=packed.count.to(torch.int32)),
                      replace(packed, offsets=packed.offsets.reshape(1, 2)),
                      MessageBatch(packed.data.reshape(1, -1), packed.offsets, packed.count),
                      RangedMessageBatch(packed.data, packed.offsets.reshape(1, 2).to(torch.int32), packed.count)):
            with self.assertRaisesRegex(ValueError, "layouts"):
                content_digests_metal(batch, implementation="unrolled")


if __name__ == "__main__": unittest.main()
