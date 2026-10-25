"""Compact numerical graph checkpoints preserve exact source features."""
from __future__ import annotations

import copy
import io
import pickle
import unittest
from unittest.mock import patch
import zlib

import numpy as np
import torch
import gwrl_cpp

from studies.campaign import numeric_storage as storage


def packed_graph():
    numeric = np.zeros((3, 8), dtype=np.float64)
    numeric[2, 0] = -0.0
    return {"schema": "campaign-numeric-graph-v1", "buckets": 128,
            "token_ids": np.array([4, 5, 6], dtype=np.int64),
            "token_offsets": np.array([0, 1, 2, 3], dtype=np.int64),
            "types": np.array([5, 3, 2], dtype=np.int64), "numeric": numeric,
            "sources": np.array([0, 1, 0, 2], dtype=np.int64),
            "targets": np.array([1, 0, 2, 0], dtype=np.int64),
            "relations": np.array([0, 1, 0, 1], dtype=np.int64),
            "identities": {"海軍\x00é🙂": (0,)}, "references": ((1, "海軍\x00é🙂"),), "leaf_count": 2}


class CampaignNumericStorageTests(unittest.TestCase):
    def assert_state_equal(self, first, second):
        self.assertEqual(set(first), set(second))
        for name, value in first.items():
            if isinstance(value, np.ndarray):
                self.assertEqual(value.dtype, second[name].dtype)
                self.assertEqual(value.shape, second[name].shape)
                np.testing.assert_array_equal(value.view(np.uint8), second[name].view(np.uint8))
            else:
                self.assertEqual(value, second[name])

    def test_frame_roundtrip_preserves_float_bits_arrays_unicode_and_metadata(self):
        state = packed_graph()
        envelope = storage.pack_graph(state)
        self.assertEqual(envelope[0], storage.SCHEMA)
        self.assertIs(type(envelope[2]), torch.Tensor)
        self.assertEqual(envelope[2].dtype, torch.uint8)
        self.assert_state_equal(state, storage.unpack_graph(envelope))
        self.assertTrue(np.signbit(storage.unpack_graph(envelope)["numeric"][2, 0]))

    def test_legacy_dictionary_and_oversized_graph_keep_existing_native_validation(self):
        state = packed_graph()
        self.assertIs(storage.unpack_graph(state), state)
        legacy = gwrl_cpp.CampaignNumericGraph.__new__(gwrl_cpp.CampaignNumericGraph)
        legacy.__setstate__(state)
        self.assertEqual(legacy, gwrl_cpp.CampaignNumericGraph.from_packed(state))
        raw = pickle.dumps(state, protocol=5)
        self.assert_state_equal(state, storage.unpack_graph((storage.BYTES_SCHEMA, len(raw), zlib.compress(raw))))
        with patch.object(storage, "MAX_RAW_BYTES", 1):
            self.assertIs(storage.pack_graph(state), state)
        self.assert_state_equal(state, gwrl_cpp.CampaignNumericGraph.from_packed(storage.unpack_graph(state)).packed_state())

    def test_native_pickle_and_torch_save_use_compact_frame_and_exact_owned_restore(self):
        graph = gwrl_cpp.CampaignNumericGraph.from_packed(packed_graph())
        envelope = graph.__getstate__()
        self.assertEqual(envelope[0], storage.SCHEMA)
        self.assertEqual(graph, pickle.loads(pickle.dumps(graph, protocol=2)))
        self.assertEqual(graph, pickle.loads(pickle.dumps(graph, protocol=5)))
        self.assertIs(copy.deepcopy(graph), graph)
        for protocol in (2, 5):
            stream = io.BytesIO()
            torch.save({"first": graph, "second": graph}, stream, pickle_protocol=protocol)
            stream.seek(0)
            loaded = torch.load(stream, weights_only=False)
            self.assertIs(loaded["first"], loaded["second"])
            self.assertEqual(graph, loaded["first"])
            for array in loaded["first"].arrays().values():
                self.assertFalse(array.flags.writeable)
            self.assertNotEqual(id(graph), id(loaded["first"]))

    def test_compression_reduces_repeated_feature_payload_without_loss(self):
        state = packed_graph()
        state["numeric"] = np.tile(state["numeric"], (10000, 1))
        frame = storage.pack_graph(state)
        self.assertLess(len(frame[2]), frame[1] // 10)
        self.assert_state_equal(state, storage.unpack_graph(frame))

    def test_invalid_envelopes_lengths_crc_truncation_and_trailing_streams_are_rejected(self):
        frame = storage.pack_graph(packed_graph())
        _, size, tensor = frame
        schema, payload = storage.BYTES_SCHEMA, tensor.numpy().tobytes()
        damaged = payload[:-1] + bytes([payload[-1] ^ 1])
        invalid = [None, [], (), (schema, size), [schema, size, payload],
                   ("future", size, payload), (1, size, payload),
                   (schema, True, payload), (schema, 0, payload), (schema, -1, payload),
                   (schema, storage.MAX_RAW_BYTES + 1, payload), (schema, size, bytearray(payload)),
                   (schema, size, b""), (schema, size, damaged), (schema, size, payload[:-1]),
                   (schema, size, payload + b"extra"), (schema, size, payload + payload),
                   (schema, size - 1, payload), (schema, size + 1, payload)]
        for state in invalid:
            with self.subTest(state=repr(state)[:100]):
                with self.assertRaises(ValueError):
                    storage.unpack_graph(state)

    def test_storage_tensor_envelope_rejects_wrong_device_dtype_shape_and_layout(self):
        _, size, valid = storage.pack_graph(packed_graph())
        invalid = [valid.numpy(), valid.to(torch.float32), valid.view(1, -1), valid[::2],
                   torch.empty(0, dtype=torch.uint8), torch.tensor(3, dtype=torch.uint8),
                   torch.empty(1, device="meta", dtype=torch.uint8),
                   valid.to_sparse(), torch.nn.Parameter(valid, requires_grad=False)]
        for payload in invalid:
            with self.subTest(payload=type(payload).__name__):
                with self.assertRaises(ValueError):
                    storage.unpack_graph((storage.SCHEMA, size, payload))
        # The wire storage is a private copy, never an alias into the graph.
        graph = gwrl_cpp.CampaignNumericGraph.from_packed(packed_graph())
        before = graph.packed_state()
        frame = graph.__getstate__()
        frame[2].zero_()
        self.assert_state_equal(before, graph.packed_state())
        with self.assertRaises(ValueError):
            storage.unpack_graph(frame)

    def test_inner_pickle_must_be_exactly_one_dictionary_then_native_fields_validate(self):
        for raw in (pickle.dumps([]), pickle.dumps(packed_graph()) + pickle.dumps({}), b"not a pickle"):
            with self.subTest(length=len(raw)):
                with self.assertRaises(ValueError):
                    storage.unpack_graph((storage.BYTES_SCHEMA, len(raw), zlib.compress(raw)))
        incomplete = packed_graph()
        del incomplete["types"]
        with self.assertRaises(ValueError):
            gwrl_cpp.CampaignNumericGraph.from_packed(storage.unpack_graph(storage.pack_graph(incomplete)))
        invalid = packed_graph()
        invalid["numeric"][2, 0] = np.nan
        with self.assertRaises(ValueError):
            gwrl_cpp.CampaignNumericGraph.from_packed(storage.unpack_graph(storage.pack_graph(invalid)))

    def test_declared_small_size_bounds_decompression_even_for_a_large_valid_stream(self):
        raw = b"x" * (1024 * 1024)
        with self.assertRaises(ValueError):
            storage.unpack_graph((storage.BYTES_SCHEMA, 32, zlib.compress(raw, level=1)))


if __name__ == "__main__":
    unittest.main()
