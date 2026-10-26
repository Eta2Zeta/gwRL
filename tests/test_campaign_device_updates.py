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
    FIXTURE_SCHEMA, RecordingReplayRandom, UpdateConfig, compare_updates, perform_update, validate_fixture,
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


if __name__ == "__main__":
    unittest.main()
