"""Training games whose positions are evaluated together by the main process."""
from __future__ import annotations

from dataclasses import asdict
import json
import multiprocessing
from multiprocessing.shared_memory import SharedMemory
import os
from pathlib import Path
import queue
import signal
import struct
import subprocess
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import torch

from studies.campaign import run
from studies.campaign.curriculum import make_env
from studies.campaign.episode_workers import EpisodeWorkers, SharedEpisodeWorkers, _play_game
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
from studies.campaign.shared_evaluator import game_process, play_shared_games
from studies.shared.multiplayer_mcts import PLAYERS

TINY = dict(calendar_rounds=1, simulations=2, max_depth=2, hidden_dim=16, token_buckets=2048, complete_episodes=True,
            parallel_envs=2, episode_workers=2, batch_size=4)
ARGUMENTS = ["--calendar-rounds", "1", "--complete-episodes", "--batches", "2", "--parallel-envs", "4",
             "--episode-workers", "2", "--games-per-process", "2", "--transitions-per-batch", "2000",
             "--simulations", "2", "--max-depth", "2", "--hidden-dim", "16", "--token-buckets", "2048",
             "--batch-size", "4", "--epochs", "2"]


def tiny_learner():
    config = run.RunConfig(**TINY)
    learner = run._learner(config, make_env(config.seed, calendar_rounds=1))
    learner.env = make_env(config.seed, calendar_rounds=1)
    return learner


def settings(learner):
    return dict(calendar_rounds=1, model_config=learner.model_config, learning_config=asdict(learner.config),
                rules_version=learner.compatibility["rules"], numeric=learner._numeric_models())


def shared_workers(learner, processes=1, games_per_process=1):
    return SharedEpisodeWorkers(processes, games_per_process, device=torch.device("cpu"), **settings(learner))


def weights(seed):
    torch.manual_seed(seed)
    config = CampaignModelConfig(hidden_dim=16, message_layers=1, token_buckets=2048)
    return {player: CampaignPolicyValueNet(config).state_dict() for player in PLAYERS}


def dies_sending_a_record(slots, _connections, _names, _tasks, results):
    """The other process plays on, so the coordinator keeps serving."""
    if slots == [0]:
        os.write(results._writer.fileno(), struct.pack("!i", 1 << 20) + b"half a message")
        os._exit(9)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(60)


def killed_while_starting(*_):
    os.kill(os.getpid(), signal.SIGKILL)


def stuck_in_a_game(*_):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(60)


class GameProcessEndingTests(unittest.TestCase):
    MODELS = dict.fromkeys(PLAYERS)

    def play(self, target, processes=1, **options):
        return play_shared_games(target, [1, 2], processes=processes, games_per_process=1, models=self.MODELS,
                                 device=torch.device("cpu"), **options)

    def test_a_process_dying_mid_record_is_reported_not_waited_for(self):
        with self.assertRaisesRegex(ValueError, "exited abnormally"):
            self.play(dies_sending_a_record, processes=2)

    def test_a_stop_outranks_a_process_it_killed_while_starting(self):
        checks = iter([True] * 80)  # Long enough for the process to die first.
        records, _ = self.play(killed_while_starting, keep_playing=lambda *_: next(checks, False), stop_seconds=1.0)
        self.assertEqual(records, [])

    def test_a_stop_kills_a_stuck_process_without_the_long_wait(self):
        started = time.monotonic()
        self.play(stuck_in_a_game, keep_playing=lambda *_: False, exit_seconds=60.0, stop_seconds=1.0)
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual(multiprocessing.active_children(), [])

    def test_an_orphan_does_not_wait_to_flush_its_records(self):
        parent, child = multiprocessing.Pipe()
        memory = SharedMemory(create=True, size=1 << 16)
        tasks, results = queue.Queue(), Mock()
        tasks.put(None)
        gone = Mock(is_alive=Mock(return_value=False))
        handler = signal.getsignal(signal.SIGTERM)
        try:
            with patch("multiprocessing.parent_process", return_value=gone):
                game_process(lambda *_: {}, 2048, "v", [0], [child], [memory.name], tasks, results)
        finally:
            parent.close()
            memory.close()
            memory.unlink()
        results.cancel_join_thread.assert_called_once_with()
        # Only a real game process ignores stop signals, and children inherit that.
        self.assertIs(signal.getsignal(signal.SIGTERM), handler)


class SharedEpisodeWorkerTests(unittest.TestCase):
    def test_one_game_at_a_time_matches_worker_games(self):
        learner = tiny_learner()
        workers = EpisodeWorkers(1, **settings(learner))
        try:
            alone = workers.play([(0, 91)], weights=weights(3), batch_version="v", max_transitions=2000)
        finally:
            workers.close()
        shared = shared_workers(learner).play([(0, 91)], weights=weights(3), batch_version="v", max_transitions=2000)
        self.assertTrue(alone[0]["terminal"])
        self.assertEqual(shared[0]["events"], alone[0]["events"])
        self.assertEqual(shared[0]["returns"], alone[0]["returns"])
        self.assertEqual(len(shared[0]["records"]), len(alone[0]["records"]))

    def test_each_batch_evaluates_with_its_own_weights(self):
        learner = tiny_learner()
        workers = shared_workers(learner)
        workers.play([(0, 91)], weights=weights(3), batch_version="old", max_transitions=2000)
        second = workers.play([(0, 91)], weights=weights(4), batch_version="new", max_transitions=2000)
        fresh = shared_workers(learner).play([(0, 91)], weights=weights(4), batch_version="new", max_transitions=2000)
        self.assertEqual(second[0]["events"], fresh[0]["events"])

    def test_games_share_processes_and_return_in_order(self):
        learner = tiny_learner()
        workers = shared_workers(learner, 2, 2)
        collection = learner.collect_episodes(workers, 5, 2000)
        self.assertEqual([result["root"] for result in collection["results"]], [0, 1, 2, 3, 4])
        self.assertEqual(learner.counters["episodes"], 5)
        self.assertEqual(collection["failed"], [])
        self.assertEqual({len(result["records"]) > 0 for result in collection["results"]}, {True})
        report = workers.report()
        self.assertEqual(report["evaluations"], workers.serving.requests)
        started = subprocess.run(["pgrep", "-P", "1", "torch_shm"], capture_output=True, text=True).stdout
        self.assertEqual(started, "")  # A manager would inherit the game pipes.
        self.assertGreater(max(workers.serving.requests_per_round), 1)
        self.assertEqual(multiprocessing.active_children(), [])

    def test_a_stop_abandons_the_batch_and_leaves_no_processes(self):
        learner = tiny_learner()
        checks = iter([False] * 40)
        collection = learner.collect_episodes(shared_workers(learner, 2, 1), 2, 2000, stop=lambda: next(checks, True))
        self.assertIsNone(collection)
        self.assertEqual(learner.counters["episodes"], 0)
        self.assertEqual(multiprocessing.active_children(), [])

    def test_a_game_that_fails_is_recorded_and_costs_only_itself(self):
        class Broken:
            version = "v"

            def evaluate(self, *_):
                raise RuntimeError("rules")
        learner = tiny_learner()
        task = {"root": 3, "seed": 91, "batch_version": "v", "max_transitions": 100}
        self.assertEqual(_play_game(settings(learner), Broken(), task)["failure"], "RuntimeError: rules")

    def test_numeric_inputs_are_required(self):
        with self.assertRaisesRegex(ValueError, "native numerical inputs"):
            SharedEpisodeWorkers(1, 1, device=torch.device("cpu"), calendar_rounds=1, model_config={},
                                 learning_config={}, rules_version="r", numeric=False)


class SharedTrainingRunTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="campaign-shared-training-")
        self.addCleanup(temporary.cleanup)
        self.run_dir = Path(temporary.name) / "run"

    def train(self, *extra):
        with patch("builtins.print"), patch("torch.set_num_interop_threads"):
            return run.main(["train", "--run-dir", str(self.run_dir), *extra])

    def test_a_run_trains_stops_and_resumes(self):
        self.assertEqual(self.train(*ARGUMENTS, "--stop-after-waves", "1"), 130)
        checkpoint = self.run_dir / "checkpoint.pt"
        self.assertEqual(self.train("--resume", str(checkpoint)), 0)
        manifest = json.loads((self.run_dir / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["counters"]["episodes"], 8)
        self.assertEqual(manifest["counters"]["updates"], 2)
        updates = manifest["runner"]["updates"]
        self.assertTrue(all(update["evaluator"]["evaluations"] > 0 for update in updates))
        self.assertTrue(all(update["rollout"]["terminal"] and not update["rollout"]["bootstrap_samples"]
                            for update in updates))

    def test_games_per_process_needs_episode_workers(self):
        with self.assertRaisesRegex(ValueError, "needs episode workers"):
            run.RunConfig(games_per_process=4)
        with self.assertRaisesRegex(ValueError, "nonnegative integer"):
            run.RunConfig(games_per_process=-1)


if __name__ == "__main__":
    unittest.main()
