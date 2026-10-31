"""Long-run controls: sample share, warm starts, the last-batch time and all cores."""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import torch

from studies.campaign.curriculum import compatibility, make_env
from studies.campaign.learning import CampaignLearner, LearningConfig, play_episode
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
from studies.campaign.run import RunConfig, main
from studies.shared.multiplayer_mcts import PLAYERS
from tools.record_campaign_games import game_arguments
from tools.supervise_campaign_training import SupervisorConfig, validate_training_arguments

SMALL = ["--calendar-rounds", "1", "--batches", "1", "--transitions-per-batch", "4", "--parallel-envs", "1",
         "--simulations", "2", "--max-depth", "2", "--hidden-dim", "16", "--token-buckets", "2048"]


def manifest(run_dir: Path) -> dict:
    return json.loads((run_dir / "manifest.json").read_text())


class SampleFractionTests(unittest.TestCase):
    def play(self, fraction: float) -> dict:
        config = CampaignModelConfig(hidden_dim=16, message_layers=1, token_buckets=2048)
        torch.manual_seed(5)
        evaluator = NeuralEvaluator({player: CampaignPolicyValueNet(config).eval() for player in PLAYERS}, version="v")
        env = make_env(91, calendar_rounds=1)
        return play_episode(env, evaluator, config=LearningConfig(simulations=2, max_depth=2, sample_fraction=fraction),
                            rules_version=compatibility(env)["rules"], numeric=True, token_buckets=2048,
                            batch_version="v", environment_seed=91, max_transitions=2000)

    def test_keeping_fewer_samples_plays_the_same_game(self):
        everything, some = self.play(1.0), self.play(.25)
        self.assertTrue(everything["terminal"])
        self.assertEqual(some["events"], everything["events"])
        self.assertEqual(some["counts"], everything["counts"])
        self.assertEqual(len(everything["records"]), everything["counts"]["decisions"])
        self.assertLess(0, len(some["records"]))
        self.assertLess(len(some["records"]), len(everything["records"]) / 2)
        self.assertEqual({tuple(record["values"]) for record in some["records"]}, {tuple(everything["returns"])})

    def test_the_share_must_make_sense(self):
        for fraction in (0, -.5, 1.5):
            with self.assertRaisesRegex(ValueError, "Sample fraction"):
                LearningConfig(sample_fraction=fraction)
        with self.assertRaisesRegex(ValueError, "episode workers"):
            RunConfig(sample_fraction=.5)
        RunConfig(sample_fraction=.5, complete_episodes=True, episode_workers=2, parallel_envs=2)


class RunControlTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="campaign-night-run-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def train(self, name: str, *extra: str) -> Path:
        run_dir = self.directory / name
        with patch("builtins.print"), patch("torch.set_num_interop_threads"):
            self.assertEqual(main(["train", "--run-dir", str(run_dir), *SMALL, *extra]), 0)
        return run_dir

    def test_a_passed_last_start_time_ends_the_run_as_completed(self):
        run_dir = self.train("late", "--batches", "5", "--no-new-batch-after", str(time.time() - 1))
        self.assertEqual(manifest(run_dir)["status"], "completed")
        self.assertEqual(manifest(run_dir)["runner"]["batch_index"], 0)

    def test_initial_models_start_a_fresh_run_from_their_weights(self):
        source = self.train("source")
        export = source / "models/generation-000001.pt"
        versions = torch.load(export, map_location="cpu", weights_only=False)["model_versions"]
        started = self.train("warm", "--seed", "7", "--initial-models", str(export))
        first = torch.load(started / "models/generation-000000.pt", map_location="cpu", weights_only=False)
        # A version is its generation and weight digest, and this run counts from zero.
        digests = {player: version.rsplit(":", 1)[1] for player, version in versions.items()}
        self.assertEqual({player: version.rsplit(":", 1)[1] for player, version in first["model_versions"].items()}, digests)
        recorded = manifest(started)["runner"]["initial_models"]
        self.assertEqual((recorded["generation"], recorded["model_versions"]), (1, versions))
        self.assertEqual(manifest(started)["runner"]["batch_index"], 1)

    def test_initial_models_must_be_the_same_network_size(self):
        source = self.train("small")
        with self.assertRaisesRegex(ValueError, "different network size"):
            self.train("other", "--hidden-dim", "32", "--initial-models", str(source / "models/generation-000001.pt"))

    def test_recorded_games_copy_the_exports_game_search_and_network(self):
        config = {"calendar_rounds": 11, "simulations": 64, "max_depth": 16, "hidden_dim": 64, "message_layers": 2,
                  "token_buckets": 16384, "value_scale": 100.0}
        arguments = game_arguments(config, Path("models.pt"), 9, Path("game"))
        for flag, value in (("--calendar-rounds", "11"), ("--simulations", "64"), ("--max-depth", "16"),
                            ("--hidden-dim", "64"), ("--message-layers", "2"), ("--token-buckets", "16384"),
                            ("--seed", "9"), ("--initial-models", "models.pt")):
            self.assertEqual(arguments[arguments.index(flag) + 1], value)
        self.assertIn("--full-campaign", game_arguments({**config, "calendar_rounds": None}, Path("m"), 9, Path("g")))


class DeviceMemoryTests(unittest.TestCase):
    def test_only_a_gpu_learner_releases_memory(self):
        learner = object.__new__(CampaignLearner)
        learner._device_runtime = None
        learner.release_device_memory()
        learner._device_runtime = Mock()
        learner.release_device_memory()
        learner._device_runtime.reset.assert_called_once_with()


class AllCoresTests(unittest.TestCase):
    WORKERS = ["--threads", "1", "--parallel-envs", "13", "--episode-workers", "13", "--cpu-budget", "14"]

    def test_all_cores_needs_the_owners_go_ahead(self):
        with patch("os.cpu_count", return_value=14):
            with self.assertRaisesRegex(ValueError, "12 cores"):
                SupervisorConfig(seconds=2, cpu_budget=14)
            config = SupervisorConfig(seconds=2, cpu_budget=14, all_cores=True)
            with self.assertRaisesRegex(ValueError, "14 cores"):
                SupervisorConfig(seconds=2, cpu_budget=15, all_cores=True)
        validate_training_arguments(self.WORKERS, config)

    def test_worker_runs_count_workers_not_threads_plus_games(self):
        with patch("os.cpu_count", return_value=14):
            config = SupervisorConfig(seconds=2, cpu_budget=14, all_cores=True)
        with self.assertRaisesRegex(ValueError, "exceed training CPU budget"):
            validate_training_arguments(["--threads", "1", "--parallel-envs", "13", "--cpu-budget", "14"], config)
        with self.assertRaisesRegex(ValueError, "exceed training CPU budget"):
            validate_training_arguments(["--threads", "1", "--parallel-envs", "14", "--episode-workers", "14",
                                         "--cpu-budget", "14"], config)


if __name__ == "__main__":
    unittest.main()
