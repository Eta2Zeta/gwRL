"""Contract, complete-buffer and paired-input checks without timed workloads."""
from dataclasses import replace
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch

from tools.benchmark_campaign_device_state import (
    POSITIONS, StateConfig, exact_resident, native_witnesses, paired,
)


def state(lanes=1):
    context = SimpleNamespace(identity=("schema", "definition", "rules"),
        records=torch.tensor([[4, 0, 0, 0x80000000, 1]], dtype=torch.int64),
        string_bytes=torch.tensor([0, 230, 151], dtype=torch.uint8),
        string_offsets=torch.tensor([0, 1, 3], dtype=torch.int64))
    records = torch.tensor([[[4, 0, 0, 0x80000000, 1], [3, 0, 0xffffffff, 0xffffffff, 2]]], dtype=torch.int64)
    return SimpleNamespace(context=context, lane_count=lanes, records=records.repeat(lanes, 1, 1),
        lengths=torch.full((lanes,), 2, dtype=torch.int64),
        sections=torch.tensor([[0, 1]], dtype=torch.int64).repeat(lanes, 1),
        errors=torch.zeros(lanes, dtype=torch.int64), string_bytes=context.string_bytes,
        string_offsets=context.string_offsets)


class CampaignDeviceStateBenchmarkTests(unittest.TestCase):
    def test_resource_and_workload_contract_rejects_fallback_or_unbounded_jobs(self):
        config = StateConfig()
        self.assertEqual(config.batch_sizes, (1, 4, 16, 64, 256))
        self.assertEqual(config.repeats, 5)
        for changes in ({"devices": ("gpu",)}, {"devices": ("mps", "mps")},
                        {"batch_sizes": (1, True)}, {"batch_sizes": ()}, {"repeats": 0},
                        {"memory_bytes": 8_000_000_001}, {"memory_bytes": 4_000_000_000},
                        {"seconds": 181}, {"seconds": float("nan")}, {"threads": 3}, {"seed": -1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(config, **changes)

    def test_oracle_checks_every_record_bit_section_and_shared_string(self):
        reference, actual = state(), state(4)
        evidence = exact_resident(actual, reference)
        self.assertTrue(evidence["exact"])
        self.assertEqual(evidence["verified_lanes"], 4)
        self.assertEqual(exact_resident(actual, reference, inspection_chunk_bytes=1)["buffer_sha256"],
                         evidence["buffer_sha256"], "Inspection chunking must retain every bit and hash order")
        for field, index in (("records", (3, 1, 2)), ("sections", (2, 1)),
                             ("lengths", (1,)), ("string_bytes", (2,))):
            broken = state(4)
            getattr(broken, field)[index] ^= 1
            with self.subTest(field=field), self.assertRaises(AssertionError):
                exact_resident(broken, reference)
        actual = state(2)
        actual.errors[1] = 1
        with self.assertRaises(AssertionError):
            exact_resident(actual, reference)

    def test_native_witnesses_require_full_serialization_including_randomness(self):
        serialized = '{"state":{"history":[]},"random":{"actual":"1","search":"2"}}'
        env = SimpleNamespace(serialize=lambda: serialized)
        batch = SimpleNamespace(lane_count=64, device=torch.device("cpu"),
            fork=lambda lanes: SimpleNamespace(restore_envs=lambda: [env for _ in lanes]))
        result = native_witnesses(batch, serialized)
        self.assertEqual(result["lanes"], (0, 32, 63))
        self.assertTrue(result["full_native_state_and_all_rng_exact"])
        env.serialize = lambda: serialized.replace('"search":"2"', '"search":"3"')
        with self.assertRaises(ValueError):
            native_witnesses(batch, serialized)

    def test_pairing_requires_complete_grid_same_sources_and_all_integer_bits(self):
        config = replace(StateConfig(), batch_sizes=(1,))
        def report(device, mismatch=None):
            rows = [{"position": position, "lanes": 1, "native_checkpoint_sha256": position,
                "resident_evidence": {"exact": True, "buffer_sha256": {"records": "same"}},
                "native_witnesses": {"full_native_state_and_all_rng_exact": True},
                "timed_native_clone_witnesses_exact": True} for position in POSITIONS]
            value = {"status": "completed", "sources_unchanged": True, "device": device,
                "workload_sha256": "1" * 64, "provenance": {"native_sha256": "binary"},
                "software": {"torch": "2.14.0"}, "cases": rows}
            if mismatch and device == "mps":
                if mismatch == "buffer":
                    rows[0]["resident_evidence"]["buffer_sha256"]["records"] = "changed"
                elif mismatch == "missing_case":
                    rows.pop()
                else:
                    value[mismatch] = "changed"
            return value
        with tempfile.TemporaryDirectory() as directory:
            for mismatch in (None, "buffer", "missing_case", "provenance", "workload_sha256"):
                output = Path(directory) / f"result-{mismatch}.json"
                deadlines = []
                def mocked(c, d, p, *, deadline):
                    deadlines.append(deadline)
                    return report(d, mismatch)
                with patch("tools.benchmark_campaign_device_state.supervise", side_effect=mocked):
                    result = paired(config, output)
                self.assertEqual(result["matched_complete_states_and_rng"], mismatch is None)
                self.assertEqual(len(set(deadlines)), 1, "CPU/MPS must share one wall budget")
            with self.assertRaises(ValueError):
                paired(config, Path(directory) / "result-None.json")


if __name__ == "__main__":
    unittest.main()
