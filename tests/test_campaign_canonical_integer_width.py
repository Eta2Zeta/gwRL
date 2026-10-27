"""The guarded int32 decimal magnitude is exactly representable in uint."""
from dataclasses import replace
import json
import struct
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends import canonical_json_metal as canonical
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
import tests.test_campaign_canonical_json_metal as generic
import tests.test_campaign_resident_state_json as native_state

CURRENT = "uint magnitude=value<0?uint(-value):uint(value);"
ORIGINAL = "ulong magnitude=value<0?ulong(-value):ulong(value);"
EXACT_MPS = torch.backends.mps.is_available() and mps_int64_indexing_supported()
PROBE = r'''
kernel void canonical_integer_width_probe(device const long* values[[buffer(0)]],
 device uchar* bytes[[buffer(1)]],device long* lengths[[buffer(2)]],device long* required[[buffer(3)]],
 device int* errors[[buffer(4)]],device const long* dims[[buffer(5)]],uint row[[thread_position_in_grid]]){
 if(long(row)>=dims[0])return;
 CanonicalWriter w;w.bytes=bytes+ulong(row)*ulong(dims[2]);w.capacity=dims[1];w.position=0;w.error=0;
 canonical_integer(w,values[row]);required[row]=w.position;errors[row]=w.error|(w.position>w.capacity?2:0);
 lengths[row]=errors[row]?0:w.position;
}
'''


class CanonicalIntegerProofTests(unittest.TestCase):
    def test_guard_before_long_negation_and_only_int32_magnitude_changes(self):
        self.assertEqual(canonical.SOURCE.count(CURRENT), 1)
        body = canonical.SOURCE.split("inline void canonical_integer(", 1)[1].split("inline bool canonical_number_integer(", 1)[0]
        self.assertLess(body.index("if(value<INT_MIN||value>INT_MAX)"), body.index(CURRENT))
        self.assertIn("value<0?uint(-value):uint(value)", body)
        for value in (-2**31, -1, 0, 1, 2**31-1):
            self.assertTrue(0 <= abs(value) < 2**32)
            self.assertEqual(str(abs(value)), str(abs(value) & (2**32-1)))
        from studies.campaign.backends import resident_state_json
        self.assertIn("ulong value=state_raw_bits", resident_state_json.HELPERS)


@unittest.skipUnless(EXACT_MPS, "Lossless Apple GPU runtime required")
class CanonicalIntegerWidthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads(); torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
        cls.original_source = canonical.SOURCE.replace(CURRENT, ORIGINAL, 1)
        cls.old_library = torch.mps.compile_shader(cls.original_source + PROBE)
        cls.new_library = torch.mps.compile_shader(canonical.SOURCE + PROBE)

    @classmethod
    def tearDownClass(cls):
        del cls.old_library, cls.new_library
        torch.set_num_threads(cls.old_threads)

    def probe(self, library, values, capacity):
        N = len(values); P = max(capacity, 1)
        inputs = torch.tensor(values, dtype=torch.int64, device="mps")
        data = torch.full((N, P), 171, dtype=torch.uint8, device="mps")
        lengths = torch.empty(N, dtype=torch.int64, device="mps"); required = torch.empty_like(lengths)
        errors = torch.empty(N, dtype=torch.int32, device="mps")
        dims = torch.tensor([N, capacity, P], dtype=torch.int64, device="mps")
        library.canonical_integer_width_probe(inputs, data, lengths, required, errors, dims, threads=N)
        return data, lengths, required, errors

    def test_dense_decimal_boundaries_native_bytes_all_capacities_and_range_guards(self):
        values = set(range(-128, 129)) | {-(2**31), 2**31-1}
        for power in range(10):
            for delta in range(-3, 4):
                value = 10**power+delta
                for signed in (value, -value):
                    if -(2**31) <= signed <= 2**31-1: values.add(signed)
        valid = sorted(values); outside = [-(2**63), -(2**31)-1, 2**31, 2**63-1]; values = valid + outside
        native = tuple(x.encode() for x in gwrl_cpp.campaign_canonical_json_probe([str(v) for v in valid]))
        self.assertEqual(native, tuple(str(v).encode() for v in valid))
        for capacity in (*range(12), 17):
            with self.subTest(capacity=capacity):
                old = self.probe(self.old_library, values, capacity); new = self.probe(self.new_library, values, capacity)
                for a, b in zip(old, new, strict=True): self.assertTrue(torch.equal(a, b))
                data, lengths, required, errors = (x.cpu().tolist() for x in new)
                self.assertEqual(required, [len(x) for x in native]+[0]*len(outside))
                self.assertEqual(errors, [0 if len(x)<=capacity else 2 for x in native]+[1]*len(outside))
                self.assertEqual(lengths, [len(x) if len(x)<=capacity else 0 for x in native]+[0]*len(outside))
                for row, text in zip(data, native): self.assertEqual(bytes(row[:min(capacity, len(text))]), text[:capacity])
                self.assertTrue(all(all(byte==171 for byte in row) for row in data[-len(outside):]))

    def compare_generic(self, state, requests, context, capacity):
        with patch.object(canonical, "_library", self.old_library):
            old = canonical.canonical_json_subtrees(state, requests, context, byte_capacity=capacity)
        with patch.object(canonical, "_library", self.new_library):
            new = canonical.canonical_json_subtrees(state, requests, context, byte_capacity=capacity)
        for name in ("lengths", "required_bytes", "errors", "count", "batch_error"):
            self.assertTrue(torch.equal(getattr(old, name), getattr(new, name)), name)
        required = new.required_bytes.cpu().tolist()
        for i, size in enumerate(required): self.assertTrue(torch.equal(old.data[i, :min(size,capacity)], new.data[i, :min(size,capacity)]))
        return new

    def test_generic_integer_negative_zero_cached_and_unknown_number_paths_unchanged(self):
        helper = generic.CanonicalJsonTests()
        values = [-(2**31), 2**31-1, -0.0, 0.1, 1.0000000000000002, 2**31, -(2**31)-1, 1e200, 1e-200]
        state, requests, context, expected = helper.setup_batch([values])
        for capacity in (0, 1, 8, len(expected[0])-1, len(expected[0]), len(expected[0])+10):
            result = self.compare_generic(state, requests, context, capacity)
            if capacity >= len(expected[0]): self.assertEqual(canonical.inspect_canonical_json(result), expected)
        # Values not in the number cache still follow exactly the old lookup
        # failure, while fresh int32 bits require no cached spelling.
        records = state.records.clone(); bits = struct.unpack("Q", struct.pack("d", .1))[0]
        index = next(i for i,row in enumerate(records[0].cpu().tolist()) if row[0]==4 and row[2]|row[3]<<32==bits)
        for value, error in ((-(2**31), 0), (2**31-1, 0), (.123456789, 4)):
            data = records.clone(); bits = struct.unpack("Q", struct.pack("d", value))[0]
            data[0,index,2]=bits&0xffffffff; data[0,index,3]=bits>>32
            result = self.compare_generic(replace(state, records=data), requests, context, len(expected[0])+100)
            self.assertEqual(result.errors.cpu().tolist(), [error])

    def test_all_state_serializers_preserve_full_uint64_turn_serial_and_native_keys(self):
        from studies.campaign.backends.resident_state_json import ResidentStateJson
        from studies.campaign.backends.resident_state_json_parallel import ParallelUnitStateJson
        from studies.campaign.backends.resident_state_json_fields import ParallelFieldStateJson
        from studies.campaign.backends.content_digest_metal import inspect_digests
        original = gwrl_cpp.CampaignEnv(str(native_state.SCENARIO), 1951)
        def edge(doc, serial):
            doc['state']['clock']['player_turn_serial'] = str(serial)
            doc['state']['flags'].update({'integer_width_min':-(2**31),'integer_width_max':2**31-1})
        envs = [native_state.changed(original, lambda doc, serial=serial:edge(doc,serial)) for serial in (0,2**32-1,2**32,2**63,2**64-1)]
        state, reference = native_state.ResidentStateJsonTests().setup_batch(envs)
        expected = gwrl_cpp.campaign_state_json_oracle(envs)
        for implementation in (ResidentStateJson, ParallelUnitStateJson, ParallelFieldStateJson):
            formatter = implementation(reference.number_context)
            result = formatter.identities(state, byte_capacity=262144)
            self.assertEqual(canonical.inspect_canonical_json(result.state_json), tuple(x['json'] for x in expected))
            self.assertEqual(inspect_digests(result.state_keys), tuple(x['state_key'] for x in expected))
            self.assertEqual(inspect_digests(result.engine_keys), tuple(x['engine_key'] for x in expected))
            self.assertIn(b'18446744073709551615', canonical.inspect_canonical_json(result.state_json)[-1])


if __name__ == "__main__": unittest.main()
