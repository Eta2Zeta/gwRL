"""The income microbenchmark refuses invalid contracts and mismatched outputs."""
from dataclasses import replace
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from tools.benchmark_campaign_income import IncomeConfig, exact_oracle, paired


class CampaignIncomeBenchmarkTests(unittest.TestCase):
    def test_contract_has_explicit_device_and_resource_limits(self):
        config = IncomeConfig()
        for changes in ({"devices": ("gpu",)}, {"devices": ("cpu", "cpu")},
                        {"batch_sizes": (1, 0)}, {"batch_sizes": (True,)},
                        {"memory_bytes": 30_000_000_001}, {"threads": 10},
                        {"cpu_budget": 13}, {"repeats": 0}, {"native_repeats": 0},
                        {"seconds": float("inf")}, {"seed": -1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(config, **changes)

    def test_oracle_compares_full_components_and_maps_native_error_classes(self):
        income = np.array([[[0, 3, 1, 8, 2, 10], [1, 0, 0, 0, 0, 0]]], dtype=np.int64)
        effective = np.array([[3, 0]], dtype=np.int64)
        errors = np.array([[0, 5]], dtype=np.int64)
        result = SimpleNamespace(income=torch.tensor(income), effective=torch.tensor(effective), effective_error=torch.tensor(errors))
        expected = income.copy()
        oracle = SimpleNamespace(income_array=lambda: expected,
            effective_array=lambda: np.array([[[0, 3], [1, 0]]], dtype=np.int64))
        self.assertTrue(exact_oracle(result, oracle)["exact"])
        expected[0, 0, 4] += 1
        with self.assertRaises(AssertionError): exact_oracle(result, oracle)

    def test_paired_requires_same_workload_and_exact_integer_outputs(self):
        def record(device, sha="same"):
            return {"status": "completed", "device": device, "workload_sha256": "fixture",
                    "cases": [{"batch_size": 1, "income_sha256": sha,
                               "effective_sha256": "effective", "effective_errors_sha256": "errors"}]}
        with tempfile.TemporaryDirectory() as directory:
            with patch("tools.benchmark_campaign_income.supervise", side_effect=lambda c, d, p: record(d)):
                report = paired(IncomeConfig(), Path(directory) / "same.json")
            self.assertEqual(report["status"], "completed")
            self.assertTrue(report["matched_inputs_and_integer_outputs"])
            with patch("tools.benchmark_campaign_income.supervise", side_effect=lambda c, d, p: record(d, d)):
                report = paired(IncomeConfig(), Path(directory) / "different.json")
            self.assertEqual(report["status"], "incomplete_or_mismatch")
            self.assertFalse(report["matched_inputs_and_integer_outputs"])
            with self.assertRaises(ValueError): paired(IncomeConfig(), Path(directory) / "same.json")


if __name__ == "__main__":
    unittest.main()
