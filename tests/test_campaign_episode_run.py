"""Fast runner integration with real search, terminal targets and Adam updates."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import random
import tempfile
import unittest
import weakref
from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from studies.campaign import run
from studies.campaign.learning import CampaignLearner, LearningConfig
from studies.campaign.neural import CampaignModelConfig
from studies.shared.multiplayer_mcts import PLAYERS
from test_campaign_learning import LearningToyEnv, TinyNet


class EpisodeRunEnv(LearningToyEnv):
    """Independent short episodes finish on different waves of the same batch."""

    def __init__(self, seed=31):
        super().__init__(seed, context_version="episode-run-toy-v1")
        self.episode_seed = seed
        self.finish_at = 4 + seed % 2

    def is_terminal(self):
        return self.node == self.finish_at

    def current_decision_player(self):
        return None if self.is_terminal() else super().current_decision_player()

    def decision_kind(self):
        return "terminal" if self.is_terminal() else super().decision_kind()

    def observation(self):
        value = super().observation()
        value["state"].update(finish_at=self.finish_at, episode_seed=self.episode_seed,
            clock={"completed_rounds": int(self.is_terminal()), "phase": self.decision_kind(),
                   "player_turn_serial": str(self.node)})
        return value

    def planning_key(self):
        return json.dumps([super().planning_key(), self.finish_at])

    def wealth(self):
        return {player: {"income_rate": amount, "units": 0, "treasury": 0,
                         "infrastructure": 0, "paid_construction": 0, "wealth": amount}
                for player, amount in zip(PLAYERS, (40 + self.score, 18, 12), strict=True)}

    def returns(self):
        if not self.is_terminal():
            return [0., 0., 0.]
        wealth = [self.wealth()[player]["wealth"] for player in PLAYERS]
        return [2 * value - sum(wealth) for value in wealth]

    def serialize(self):
        return json.dumps({"base": super().serialize(), "finish_at": self.finish_at,
                           "episode_seed": self.episode_seed}, sort_keys=True)

    def restore(self, serialized):
        value = json.loads(serialized)
        super().restore(value["base"])
        self.finish_at = value["finish_at"]
        self.episode_seed = value["episode_seed"]


class CampaignEpisodeRunTests(unittest.TestCase):
    """Exercise train(args), checkpoint files and resumptions without real games."""

    config = {"seed": 1947, "calendar_rounds": 1, "batches": 2,
              "transitions_per_batch": 10, "parallel_envs": 4, "simulations": 2,
              "max_depth": 6, "hidden_dim": 8, "message_layers": 1, "token_buckets": 128,
              "batch_size": 8, "epochs": 1, "replay_capacity": 128, "threads": 1,
              "checkpoint_every_waves": None, "complete_episodes": True}

    def setUp(self):
        self.old_threads = torch.get_num_threads()
        self.old_rng = random.getstate(), np.random.get_state(), torch.get_rng_state()
        self.temporary = tempfile.TemporaryDirectory(prefix="campaign-episode-run-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.factory_calls = []
        self.learners = []
        self.stack = contextlib.ExitStack()
        self.stack.enter_context(patch.object(run, "make_env", side_effect=self.environment))
        self.stack.enter_context(patch.object(run, "_learner", side_effect=self.learner))
        self.stack.enter_context(patch.object(run, "task_manifest", return_value={
            "full_target_game": False, "calendar_rounds": 1, "fixture": "episode-run-toy-v1",
            "compatibility": {"scenario": "toy-scenario-v1", "rules": "toy-rules-v1",
                              "schema": "toy-schema-v1"}}))
        self.stack.enter_context(patch.object(run, "source_hashes", return_value={
            "test-only-fixture": "stable-toy-runtime-v1"}))

    def tearDown(self):
        self.stack.close()
        random.setstate(self.old_rng[0])
        np.random.set_state(self.old_rng[1])
        torch.set_rng_state(self.old_rng[2])
        torch.set_num_threads(self.old_threads)

    def environment(self, seed, *, calendar_rounds):
        self.assertEqual(calendar_rounds, 1)
        self.factory_calls.append(seed)
        return EpisodeRunEnv(seed)

    def learner(self, config, _template):
        # Keep the actual collection/checkpoint/training implementation. Only
        # the expensive graph model and regional engine are replaced here.
        torch.set_num_threads(config.threads)
        random.seed(config.seed)
        np.random.seed(config.seed % 2**32)
        torch.manual_seed(config.seed)
        model_config = CampaignModelConfig(hidden_dim=config.hidden_dim, message_layers=config.message_layers,
            token_buckets=config.token_buckets, value_scale=config.value_scale)
        learning_config = LearningConfig(simulations=config.simulations, max_depth=config.max_depth,
            batch_size=config.batch_size, epochs=config.epochs, learning_rate=config.learning_rate,
            replay_capacity=config.replay_capacity, value_scale=config.value_scale, seed=config.seed)
        learner = CampaignLearner({player: TinyNet(model_config).eval() for player in PLAYERS},
            model_config, learning_config, compatibility={"scenario": "toy-scenario-v1",
                "rules": "toy-rules-v1", "schema": "toy-schema-v1"})
        self.learners.append(learner)
        return learner

    def train(self, directory, *, resume=False, stop_after_waves=None, extension=None, **config):
        values = {field.name: None for field in fields(run.RunConfig)}
        if not resume:
            values.update(self.config)
        values.update(config)
        args = argparse.Namespace(**values, run_dir=None if resume else directory,
            resume=directory / "checkpoint.pt" if resume else None, full_campaign=False,
            stop_after_waves=stop_after_waves, extend_episode_budget=extension)
        with contextlib.redirect_stdout(io.StringIO()):
            result = run.train(args)
        return result, self.read(directory / "checkpoint.pt")

    @staticmethod
    def read(path):
        return torch.load(path, map_location="cpu", weights_only=False)

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def assert_tree_equal(self, expected, actual, path="learner"):
        if isinstance(expected, torch.Tensor):
            self.assertTrue(torch.equal(expected, actual), f"Tensor differs at {path}")
        elif isinstance(expected, np.ndarray):
            self.assertTrue(np.array_equal(expected, actual), f"Array differs at {path}")
        elif isinstance(expected, dict):
            self.assertEqual(set(expected), set(actual), f"Keys differ at {path}")
            for key in expected:
                self.assert_tree_equal(expected[key], actual[key], f"{path}.{key}")
        elif isinstance(expected, (list, tuple)):
            self.assertEqual(type(expected), type(actual), f"Sequence type differs at {path}")
            self.assertEqual(len(expected), len(actual), f"Length differs at {path}")
            for index, (first, second) in enumerate(zip(expected, actual, strict=True)):
                self.assert_tree_equal(first, second, f"{path}[{index}]")
        else:
            self.assertEqual(expected, actual, f"Value differs at {path}")

    def test_resume_releases_input_archive_before_replay_collection(self):
        directory = self.directory / "release-restored-archive"
        self.train(directory, stop_after_waves=1)
        original_read, original_collect = run._read, CampaignLearner.collect_many
        archives = []

        class Archive(dict):
            pass

        def read_archive(path):
            archive = Archive(original_read(path))
            archives.append(weakref.ref(archive))
            return archive

        def collect(learner, *args, **kwargs):
            self.assertTrue(archives)
            self.assertTrue(all(reference() is None for reference in archives),
                            "The input checkpoint pins examples after restore")
            return original_collect(learner, *args, **kwargs)

        with patch.object(run, "_read", side_effect=read_archive), \
             patch.object(CampaignLearner, "collect_many", collect):
            status, result = self.train(directory, resume=True)
        self.assertEqual(status, 0)
        self.assertEqual(result["learner"]["counters"]["episodes"], 8)

    def test_two_batches_use_fresh_seeds_and_eight_genuine_terminal_episodes(self):
        directory = self.directory / "completed"
        status, checkpoint = self.train(directory)
        self.assertEqual(status, 0)
        runner, learner = checkpoint["runner"], checkpoint["learner"]
        self.assertEqual(learner["generation"], 2)
        self.assertEqual(learner["counters"]["episodes"], 8)
        seeds = runner["training_environment_seeds"]
        self.assertEqual(len(seeds), 8)
        self.assertEqual(len(set(seeds)), 8)
        self.assertEqual(self.factory_calls, [self.config["seed"], *seeds])
        self.assertEqual(learner["counters"]["chance_events"], 8)
        self.assertEqual(learner["counters"]["transitions"], sum(4 + seed % 2 for seed in seeds))
        self.assertEqual(runner["total_waves"], 10)
        self.assertEqual(len(runner["updates"]), 2)
        for index, batch in enumerate(runner["updates"]):
            self.assertEqual(batch["rollout"]["bootstrap_samples"], 0)
            self.assertTrue(batch["rollout"]["terminal"])
            self.assertEqual([episode["seed"] for episode in batch["episodes"]], seeds[index * 4:(index + 1) * 4])
            self.assertTrue(all(episode["terminal"] and episode["observed_terminal_returns"] is not None
                                for episode in batch["episodes"]))
        self.assertTrue(learner["replay"])
        self.assertTrue(all(row["target_source"] == "terminal" for row in learner["replay"]))
        terminal_values = {episode["seed"]: episode["observed_terminal_returns"]
                           for batch in runner["updates"] for episode in batch["episodes"]}
        for row in learner["replay"]:
            self.assertEqual(row["values"], terminal_values[row["input"]["observation"]["state"]["episode_seed"]])
        self.assertEqual({row["owner"] for row in learner["replay"]}, set(PLAYERS))
        self.assertIsNone(learner["frozen_models"])
        self.assertTrue(all(not pending for pending in learner["parallel_pending"]))
        self.assertTrue(any(size > 1 for size in runner["batch_sizes"]))
        self.assertEqual(json.loads((directory / "manifest.json").read_text())["status"], "completed")
        initial = self.read(directory / "initial.pt")
        for player in PLAYERS:
            self.assertTrue(learner["optimizers"][player]["state"])
            self.assertTrue(any(not torch.equal(value, learner["models"][player][name])
                                for name, value in initial["learner"]["models"][player].items()))

    def test_default_recovery_timer_does_not_rewrite_full_state_each_wave_or_update(self):
        self.assertIsNone(run.RunConfig().checkpoint_every_waves)
        self.assertEqual(run.RunConfig().checkpoint_interval_seconds, 1800.0)
        directory = self.directory / "infrequent-recovery"
        with patch.object(run, "_save", wraps=run._save) as saves:
            status, checkpoint = self.train(directory)
        self.assertEqual(status, 0)
        self.assertEqual(checkpoint["runner"]["batch_index"], 2)
        self.assertEqual(checkpoint["learner"]["counters"]["episodes"], 8)
        # Initial immutable state, initialized recovery state, orderly exit.
        # Neither ten collection waves nor the two updates force full saves.
        self.assertEqual([call.args[0].name for call in saves.call_args_list],
                         ["initial.pt", "checkpoint.pt", "checkpoint.pt"])
        manifest = json.loads((directory / "manifest.json").read_text())
        self.assertEqual(manifest["checkpoint_saves_this_invocation"], 3)
        self.assertEqual(manifest["model_exports_this_invocation"], 3)
        self.assertEqual(sorted(path.name for path in (directory / "models").glob("*.pt")),
                         ["generation-000000.pt", "generation-000001.pt", "generation-000002.pt"])
        self.assertEqual(manifest["latest_model_export"]["path"], "models/generation-000002.pt")

    def test_wall_clock_recovery_timer_saves_at_boundaries_without_sleeping(self):
        directory = self.directory / "timed-recovery"
        clock = [0.0]
        saves = []
        original_collect = CampaignLearner.collect_many
        original_save = run._save

        def collect_then_advance(learner, *args, **kwargs):
            result = original_collect(learner, *args, **kwargs)
            clock[0] += 10.0
            return result

        def record_save(path, learner, runner, **kwargs):
            saves.append((path.name, runner["total_waves"], runner["batch_index"], runner["wave_index"]))
            return original_save(path, learner, runner, **kwargs)

        with patch.object(CampaignLearner, "collect_many", collect_then_advance), \
                patch.object(run.time, "perf_counter", side_effect=lambda: clock[0]), \
                patch.object(run.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(run, "_save", side_effect=record_save):
            status, checkpoint = self.train(directory, checkpoint_interval_seconds=30.0)
        self.assertEqual(status, 0)
        self.assertEqual(saves, [("initial.pt", 0, 0, 0), ("checkpoint.pt", 0, 0, 0),
                                 ("checkpoint.pt", 3, 0, 3), ("checkpoint.pt", 6, 1, 1),
                                 ("checkpoint.pt", 9, 1, 4), ("checkpoint.pt", 10, 2, 0)])
        self.assertEqual(checkpoint["learner"]["counters"]["episodes"], 8)
        manifest = json.loads((directory / "manifest.json").read_text())
        self.assertEqual(manifest["checkpoint_saves_this_invocation"], 6)

    def test_ten_episode_limit_uses_short_final_batch_and_resumes_it_exactly(self):
        status, reference = self.train(self.directory / "ten-reference", batches=3, max_episodes=10)
        self.assertEqual(status, 0)
        self.assertEqual(reference["learner"]["counters"]["episodes"], 10)
        self.assertEqual(reference["learner"]["generation"], 3)
        self.assertEqual([len(batch["episodes"]) for batch in reference["runner"]["updates"]], [4, 4, 2])
        self.assertEqual(len(reference["runner"]["training_environment_seeds"]), 10)
        self.assertTrue(all(batch["rollout"]["bootstrap_samples"] == 0
                            for batch in reference["runner"]["updates"]))
        for waves in (11, reference["runner"]["total_waves"]):
            with self.subTest(stopped_after_waves=waves):
                directory = self.directory / f"ten-resume-{waves}"
                status, stopped = self.train(directory, batches=3, max_episodes=10, stop_after_waves=waves)
                self.assertEqual(status, 130)
                self.assertEqual(stopped["runner"]["batch_index"], 2)
                self.assertEqual(stopped["runner"]["wave_index"], waves - 10)
                self.assertEqual(stopped["learner"]["counters"]["episodes"], 8 if waves == 11 else 10)
                self.assertEqual(len(stopped["learner"]["parallel_envs"]), 2)
                self.assertIsNotNone(stopped["learner"]["frozen_models"])
                calls = len(self.factory_calls)
                status, resumed = self.train(directory, resume=True)
                self.assertEqual(status, 0)
                self.assert_tree_equal(reference["learner"], resumed["learner"])
                self.assert_tree_equal(reference["runner"], resumed["runner"], "runner")
                # Even when all ten games finished just before interruption,
                # resume must update the saved tail batch without new roots.
                self.assertEqual(self.factory_calls[calls:], [self.config["seed"]])

    def test_recovery_timer_requires_positive_finite_seconds(self):
        for interval in (0, -1, float("inf"), float("nan"), True):
            with self.subTest(interval=interval), self.assertRaisesRegex(ValueError, "[Cc]heckpoint"):
                run.RunConfig(checkpoint_interval_seconds=interval)

    def test_exhausted_episode_guard_preserves_frozen_pending_without_bootstrap_or_update(self):
        directory = self.directory / "exhausted"
        status, checkpoint = self.train(directory, transitions_per_batch=2)
        self.assertEqual(status, 2)
        runner, learner = checkpoint["runner"], checkpoint["learner"]
        self.assertEqual(runner["batch_index"], 0)
        self.assertEqual(runner["wave_index"], 2)
        self.assertEqual(runner["updates"], [])
        self.assertEqual(learner["generation"], 0)
        self.assertEqual(learner["counters"]["updates"], 0)
        self.assertEqual(learner["counters"]["episodes"], 0)
        self.assertIsNotNone(learner["frozen_models"])
        self.assertEqual([len(pending) for pending in learner["parallel_pending"]], [2] * 4)
        self.assertEqual(learner["replay"], [])
        self.assertEqual(learner["batch_records"], [])
        self.assertTrue(all("values" not in row for pending in learner["parallel_pending"] for row in pending))
        self.assertEqual(json.loads((directory / "manifest.json").read_text())["status"], "episode_budget_exhausted")
        initial = self.read(directory / "initial.pt")
        self.assert_tree_equal(initial["learner"]["models"], learner["models"])
        self.assert_tree_equal(initial["learner"]["optimizers"], learner["optimizers"])

    def test_explicit_episode_budget_extension_resumes_to_exact_uninterrupted_learner(self):
        status, reference = self.train(self.directory / "reference")
        self.assertEqual(status, 0)
        directory = self.directory / "extended"
        status, exhausted = self.train(directory, transitions_per_batch=2)
        self.assertEqual(status, 2)
        initial_digest = self.digest(directory / "initial.pt")
        status, resumed = self.train(directory, resume=True, extension=10)
        self.assertEqual(status, 0)
        self.assert_tree_equal(reference["learner"], resumed["learner"])
        self.assertEqual(resumed["runner"]["budget_extensions"], [
            {"old_limit": 2, "new_limit": 10, "batch": 0, "wave": 2}])
        self.assertEqual(resumed["runner"]["training_environment_seeds"], reference["runner"]["training_environment_seeds"])
        self.assertEqual(exhausted["learner"]["generation"], 0)
        self.assertEqual(self.digest(directory / "initial.pt"), initial_digest)

    def test_partial_and_all_terminal_safe_stops_resume_without_duplicate_episodes_or_rng(self):
        status, reference = self.train(self.directory / "reference")
        self.assertEqual(status, 0)
        for waves in (4, 5):
            with self.subTest(stopped_after_waves=waves):
                directory = self.directory / f"stopped-{waves}"
                status, stopped = self.train(directory, stop_after_waves=waves)
                self.assertEqual(status, 130)
                self.assertEqual(stopped["learner"]["generation"], 0)
                self.assertIsNotNone(stopped["learner"]["frozen_models"])
                self.assertEqual(stopped["learner"]["counters"]["episodes"], 2 if waves == 4 else 4)
                terminal = [json.loads(env["state"])["finish_at"] ==
                            json.loads(json.loads(env["state"])["base"])["node"]
                            for env in stopped["learner"]["parallel_envs"]]
                self.assertEqual(terminal, [True, True, False, False] if waves == 4 else [True] * 4)
                before = self.digest(directory / "initial.pt")
                calls = len(self.factory_calls)
                status, resumed = self.train(directory, resume=True)
                self.assertEqual(status, 0)
                self.assert_tree_equal(reference["learner"], resumed["learner"])
                self.assert_tree_equal(reference["runner"], resumed["runner"], "runner")
                # Resume constructs one restore template and only the next
                # batch's four fresh roots. Finished roots are never respawned.
                self.assertEqual(self.factory_calls[calls:], [self.config["seed"],
                    *reference["runner"]["training_environment_seeds"][4:]])
                self.assertEqual(self.digest(directory / "initial.pt"), before)

    def test_initial_checkpoint_remains_zero_generation_after_completion_and_resume(self):
        directory = self.directory / "initial-preserved"
        status, stopped = self.train(directory, stop_after_waves=3)
        self.assertEqual(status, 130)
        initial_path = directory / "initial.pt"
        original_digest = self.digest(initial_path)
        initial = self.read(initial_path)
        learner = initial["learner"]
        self.assertEqual(learner["generation"], 0)
        self.assertTrue(all(value == 0 for value in learner["counters"].values()))
        self.assertEqual(learner["parallel_envs"], [])
        self.assertEqual(learner["action_history"], [])
        self.assertIsNone(learner["frozen_models"])
        self.assertEqual(initial["runner"]["training_environment_seeds"], [])
        self.assertEqual(initial["runner"]["updates"], [])
        self.assertEqual(stopped["learner"]["generation"], 0)
        status, trained = self.train(directory, resume=True)
        self.assertEqual(status, 0)
        self.assertEqual(trained["learner"]["generation"], 2)
        self.assertEqual(self.digest(initial_path), original_digest)
        self.assert_tree_equal(initial, self.read(initial_path))

    def test_conservative_cpu_budget_validation_counts_search_and_tensor_threads(self):
        with patch.object(run.os, "cpu_count", return_value=16):
            config = run.RunConfig(cpu_budget=12, threads=4, parallel_envs=7)
            self.assertEqual(config.threads + config.parallel_envs + 1, 12)
            for values in ({"cpu_budget": 12, "threads": 4, "parallel_envs": 8},
                           {"cpu_budget": 17}, {"cpu_budget": 0},
                           {"cpu_budget": True}, {"cpu_budget": 12.0}):
                with self.subTest(values=values), self.assertRaisesRegex(ValueError, "CPU budget"):
                    run.RunConfig(**values)
        with patch.object(run.os, "cpu_count", return_value=None):
            with self.assertRaisesRegex(ValueError, "CPU budget"):
                run.RunConfig(cpu_budget=2)


if __name__ == "__main__":
    unittest.main()
