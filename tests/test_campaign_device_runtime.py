"""Version-gated, process-local graph-cache housekeeping, without learning state."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import torch

from studies.campaign.device_runtime import MPSGraphCachePolicy, mps_graph_cache_supported, runtime_policy_for_device


class MPSRuntimePolicyTests(unittest.TestCase):
    def test_supported_public_graph_cleanup_requires_stable_213_or_newer(self):
        for version, expected in (("2.11.0", False), ("2.12.2", False), ("2.13.0rc1", False),
                                  ("2.13.0", True), ("2.14.0", True), ("2.14.0+local", True), ("unknown", False)):
            with self.subTest(version=version):
                self.assertEqual(mps_graph_cache_supported(version), expected)
        with patch("torch.__version__", "2.11.0"), patch("torch.backends.mps.is_available", return_value=True):
            with self.assertRaisesRegex(ValueError, "2.13"):
                runtime_policy_for_device("mps")

    def test_cpu_cuda_do_not_probe_or_clear_mps(self):
        with patch("torch.mps.synchronize") as synchronize, patch("torch.mps.empty_cache") as clear, \
             patch("torch.backends.mps.is_available", side_effect=AssertionError("CPU/CUDA must not probe MPS")):
            self.assertIsNone(runtime_policy_for_device("cpu"))
            self.assertIsNone(runtime_policy_for_device("cuda:0"))
        synchronize.assert_not_called()
        clear.assert_not_called()

    def test_persistent_counter_clears_at_safe_boundaries_and_reset_is_derived(self):
        with patch("torch.__version__", "2.14.0"), patch("torch.backends.mps.is_available", return_value=True), \
             patch("torch.mps.synchronize") as synchronize, patch("torch.mps.empty_cache") as clear:
            policy = MPSGraphCachePolicy(clear_every=4)
            self.assertEqual(clear.call_count, 1)
            self.assertFalse(policy.completed(1))
            self.assertFalse(policy.completed(2))
            self.assertTrue(policy.completed(3))
            self.assertEqual(clear.call_count, 2)
            self.assertEqual(policy.stats()["total_actor_forwards"], 6)
            self.assertEqual(policy.stats()["pending_actor_forwards"], 0)
            self.assertFalse(policy.completed(1))
            policy.reset()
            self.assertEqual(policy.stats()["total_actor_forwards"], 7)
            self.assertEqual(policy.stats()["pending_actor_forwards"], 0)
            self.assertEqual(policy.stats()["resets"], 2)
            self.assertEqual(synchronize.call_count, clear.call_count)
            for value in (0, -1, True, 1.5):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    policy.completed(value)

    def test_fallback_and_fast_math_cannot_be_silently_enabled(self):
        with patch("torch.__version__", "2.14.0"), patch("torch.backends.mps.is_available", return_value=True):
            for name in ("PYTORCH_ENABLE_MPS_FALLBACK", "PYTORCH_MPS_FAST_MATH"):
                with self.subTest(name=name), patch.dict("os.environ", {name: "1"}):
                    with self.assertRaisesRegex(ValueError, name):
                        MPSGraphCachePolicy()


if __name__ == "__main__":
    unittest.main()
