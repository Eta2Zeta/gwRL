"""Update-workload contracts and actual learner calls on tiny test-only inputs."""
from __future__ import annotations

import copy
from dataclasses import replace
import random
import unittest
from unittest.mock import patch

import torch

from studies.campaign.learning import TARGET_SCHEMA
from studies.shared.multiplayer_mcts import PLAYERS
from tools.benchmark_campaign_device_updates import (
    COMMON_LOGIT_BIASES, FIXTURE_SCHEMA, RecordingReplayRandom, UpdateConfig, compare_functional_weights,
    compare_updates, functional_row_indices, perform_update, validate_fixture,
)


def test_samples():
    # This small synthetic fixture is exclusively a unit-test workload. The CLI
    # requires a real three-round terminal game with native numerical inputs.
    rows = []
    for index in range(36):
        owner = PLAYERS[index % 3]
        features = {"schema": "campaign-neural-input-v1", "context": {"registry": {"retained": [1, 2]}},
                    "observation": {"current_decision_player": owner, "state": {"step": index % 3}},
                    "actions": [{"id": str(choice), "kind": "play", "player": owner,
                                 "action": {"kind": "choose", "parameters": {"choice": choice}}} for choice in range(2)]}
        rows.append({"input": features, "owner": owner, "policy": [.25, .75], "rollout_version": "unit-test-only",
                     "values": [10., -3., -7.], "target_source": "terminal", "target_schema": TARGET_SCHEMA})
    return rows


class CampaignDeviceUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def test_workload_preserves_actual_model_batch_and_epoch_settings(self):
        config = UpdateConfig(devices=("cpu",))
        self.assertEqual((config.batch_size, config.epochs, config.hidden_dim, config.message_layers,
                          config.token_buckets), (32, 16, 16, 1, 2048))
        for change in ({"batch_size": 8}, {"epochs": 1}, {"hidden_dim": 8}, {"token_buckets": 128},
                       {"message_layers": 2}, {"devices": ("auto",)}, {"memory_bytes": 31_000_000_000},
                       {"threads": 10}, {"seconds": 3601}, {"game_seed": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(config, **change)

    def test_recording_sampler_retains_standard_random_results_and_state(self):
        rows = [object() for _ in range(36)]
        plain, original = random.Random(91), random.Random(91)
        recorder = RecordingReplayRandom(original, rows)
        for _ in range(16):
            self.assertEqual(recorder.sample(rows, 32), plain.sample(rows, 32))
        self.assertEqual(recorder.getstate(), plain.getstate())
        self.assertEqual(len(recorder.orders), 16)
        self.assertTrue(all(len(order) == len(set(order)) == 32 for order in recorder.orders))

    def test_actual_three_model_update_uses_sixteen_matched_minibatches(self):
        config = UpdateConfig(devices=("cpu",), model_seed=91)
        rows = test_samples()
        from studies.campaign.run import source_hashes
        from tools.benchmark_campaign_device_updates import sha
        import tools.benchmark_campaign_device_updates as tool
        fixture = {"samples": rows, "compatibility": {"scenario": "unit-test", "rules": "unit-test", "schema": "unit-test"},
                   "runtime_source_sha256": source_hashes(), "tool_sha256": sha(tool.__file__)}
        with patch("tools.benchmark_campaign_device_updates.validate_fixture", return_value=rows):
            first, a = perform_update(fixture, "cpu", config)
            second, b = perform_update(fixture, "cpu", config)
        self.assertEqual(first["adam_steps_per_agent"], 16)
        self.assertEqual(first["total_adam_steps"], 48)
        self.assertEqual(first["update"]["samples"], 32)
        self.assertEqual(first["update"]["generation"], 1)
        self.assertTrue(all(len(first["update"]["losses"][player]) == 16 for player in PLAYERS))
        rng = random.Random(config.model_seed ^ 0xD1B54A32D192ED03)
        self.assertEqual(first["minibatch_orders"], [rng.sample(range(len(rows)), 32) for _ in range(16)])
        comparison = compare_updates(first, second, a, b, atol=1e-8, rtol=1e-8)
        self.assertTrue(comparison["numerically_matched"])
        self.assertEqual(comparison["max_weight_absolute_difference"], 0)
        changed = copy.deepcopy(second)
        changed["minibatch_orders"][0].reverse()
        with self.assertRaisesRegex(ValueError, "order"):
            compare_updates(first, changed, a, b, atol=.002, rtol=.002)

    def test_fixture_rejects_bootstraps_or_changed_runtime_before_update(self):
        config = UpdateConfig(devices=("cpu",))
        with self.assertRaisesRegex(ValueError, "terminal provenance"):
            validate_fixture({"schema": FIXTURE_SCHEMA, "calendar_rounds": 3, "bootstrap_samples": 1}, config)
        fixture = {"schema": FIXTURE_SCHEMA, "calendar_rounds": 3, "bootstrap_samples": 0,
                   "runtime_source_sha256": {"changed": "old"}, "tool_sha256": "old"}
        with self.assertRaisesRegex(ValueError, "changed"):
            validate_fixture(fixture, config)

    @staticmethod
    def final_weights():
        from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(91)
            return {player: {name: tensor.detach().clone() for name, tensor in
                             CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=16, message_layers=1, token_buckets=2048)).state_dict().items()}
                    for player in PLAYERS}

    @staticmethod
    def update_report():
        return {"initial_weights_sha256": "same", "minibatch_orders": [[1, 2]], "synchronized_update_seconds": 1.,
                "update": {"losses": {player: [{"policy": 1., "value": 2., "total": 3.}] for player in PLAYERS}}}

    def functional_comparison(self, first, second):
        rows = test_samples()
        with patch("tools.benchmark_campaign_device_updates.validate_fixture", return_value=rows), \
                patch("studies.campaign.run.source_hashes", return_value={"unit": "stable"}):
            return compare_functional_weights({"samples": rows}, first, second, UpdateConfig(devices=("cpu",)))

    def test_common_logit_bias_drift_retains_raw_failure_and_checks_function(self):
        first = self.final_weights()
        second = copy.deepcopy(first)
        for player in PLAYERS:
            for name in COMMON_LOGIT_BIASES:
                second[player][name].add_(.03)
        raw = compare_updates(self.update_report(), self.update_report(), first, second, atol=.002, rtol=.002)
        self.assertFalse(raw["numerically_matched"])
        diagnostics = raw["parameter_diagnostics"]
        self.assertTrue(diagnostics["raw_parameter_verdict_unchanged"])
        self.assertTrue(diagnostics["nonredundant_weights_within_original_tolerance"])
        self.assertEqual(diagnostics["excluded_from_nonredundant_check_only"], list(COMMON_LOGIT_BIASES))
        rng = torch.get_rng_state().clone()
        result = self.functional_comparison(first, second)
        self.assertTrue(torch.equal(rng, torch.get_rng_state()))
        self.assertTrue(result["final_weights_functionally_within_unchanged_inference_tolerance"])
        self.assertTrue(result["bias_only_gauge_within_unchanged_inference_tolerance"])
        self.assertEqual((result["policy_atol"], result["raw_value_atol"], result["rtol"]), (.00002, .002, .0002))
        self.assertEqual(len(result["selected_indices"]), 32)
        self.assertEqual(result["selected_owner_counts"], dict(zip(PLAYERS, (11, 11, 10), strict=True)))
        actual = result["comparisons"]["second_final"]
        self.assertEqual(sum(row["scalars"] for row in actual.values()), 32 * (2 + 3 * 3))
        self.assertTrue(all(row["all_raw_values_bit_equal"] for row in actual.values()))

    def test_meaningful_parameter_corruption_fails_functional_check(self):
        first = self.final_weights()
        second = copy.deepcopy(first)
        second[PLAYERS[0]]["value_head.2.bias"][0] += 1.
        raw = compare_updates(self.update_report(), self.update_report(), first, second, atol=.002, rtol=.002)
        self.assertFalse(raw["numerically_matched"])
        self.assertFalse(raw["parameter_diagnostics"]["nonredundant_weights_within_original_tolerance"])
        functional = self.functional_comparison(first, second)
        self.assertFalse(functional["final_weights_functionally_within_unchanged_inference_tolerance"])
        self.assertTrue(functional["bias_only_gauge_within_unchanged_inference_tolerance"])
        self.assertGreater(functional["comparisons"]["second_final"][PLAYERS[0]]["max_raw_value_error"], 90.)

    def test_only_five_exact_scalar_parameters_are_excluded(self):
        first = self.final_weights()
        second = copy.deepcopy(first)
        for weights in (first, second):
            weights[PLAYERS[0]]["factor_heads.99.2.bias"] = torch.zeros(1)
        second[PLAYERS[0]]["factor_heads.99.2.bias"].add_(.03)
        result = compare_updates(self.update_report(), self.update_report(), first, second, atol=.002, rtol=.002)
        self.assertFalse(result["parameter_diagnostics"]["nonredundant_weights_within_original_tolerance"])
        details = result["parameter_diagnostics"]["by_agent"][PLAYERS[0]]["parameters"]
        self.assertFalse(next(row for row in details if row["name"] == "factor_heads.99.2.bias")["common_logit_bias"])
        for weights in (first, second):
            weights[PLAYERS[0]][COMMON_LOGIT_BIASES[0]] = torch.zeros(2)
        with self.assertRaisesRegex(ValueError, "scalar shapes"):
            compare_updates(self.update_report(), self.update_report(), first, second, atol=.002, rtol=.002)

    def test_stratification_uses_distinct_rows_when_one_actor_has_fewer(self):
        rows = [{"owner": PLAYERS[0]}] + [{"owner": PLAYERS[1]}] * 15 + [{"owner": PLAYERS[2]}] * 20
        indices, counts = functional_row_indices(rows)
        self.assertEqual(len(indices), len(set(indices)))
        self.assertEqual(len(indices), 32)
        self.assertEqual(counts[PLAYERS[0]], 1)
        self.assertEqual(sum(counts.values()), 32)


if __name__ == "__main__":
    unittest.main()
