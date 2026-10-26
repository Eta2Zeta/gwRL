"""Lossless state initialization checks actual integer behavior, not versions."""
import unittest
from unittest.mock import patch

import torch

from studies.campaign.backends import metal_validation
from studies.campaign.backends.device_state import _device


class CampaignMetalValidationTests(unittest.TestCase):
    def test_cpu_never_runs_gpu_capability_probe(self):
        with patch.object(metal_validation, "_probe", side_effect=AssertionError("Unexpected GPU initialization")):
            self.assertEqual(_device("cpu"), torch.device("cpu"))

    def test_failure_is_explicit_actionable_and_never_silently_selects_cpu(self):
        failed = {"torch": "2.11.example", "supported": False, "reason": "integer sentinel mismatch"}
        with patch.object(metal_validation, "_probe", return_value=failed), \
             patch.object(torch.backends.mps, "is_available", return_value=True):
            self.assertFalse(metal_validation.mps_int64_indexing_supported())
            with self.assertRaisesRegex(RuntimeError, "tmp/gpu-mps-env/bin/python"):
                _device("mps")
        self.assertEqual(_device("cpu"), torch.device("cpu"))

    def test_inspection_detaches_mutable_cached_witnesses(self):
        witness = {"torch": "test", "supported": True, "reason": "exact", "actual": [1, 2]}
        with patch.object(metal_validation, "_probe", return_value=witness):
            observed = metal_validation.mps_int64_indexing_capability()
            observed["actual"].append(3)
            self.assertEqual(witness["actual"], [1, 2])
            metal_validation.require_lossless_mps_indexing()

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS hardware unavailable")
    def test_measured_runtime_result_is_self_consistent(self):
        observed = metal_validation.mps_int64_indexing_capability()
        self.assertEqual(observed["supported"], metal_validation.mps_int64_indexing_supported())
        if observed["supported"]:
            self.assertEqual(observed["expected"], observed["actual"])
            metal_validation.require_lossless_mps_indexing()
        else:
            with self.assertRaisesRegex(RuntimeError, "exact MPS int64 indexing"):
                metal_validation.require_lossless_mps_indexing()


if __name__ == "__main__":
    unittest.main()
