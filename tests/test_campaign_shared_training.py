"""Training games whose positions are evaluated together by the main process."""
from __future__ import annotations

from dataclasses import asdict
from functools import partial
import json
import multiprocessing
from multiprocessing.shared_memory import SharedMemory
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import torch

from studies.campaign import run, shared_evaluator
from studies.campaign.curriculum import make_env
from studies.campaign.episode_workers import EpisodeWorkers, SharedEpisodeWorkers, _play_game
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
from studies.campaign.shared_evaluator import SharedEvaluatorServer, game_process, play_shared_games
from studies.shared.multiplayer_mcts import PLAYERS

TINY = dict(calendar_rounds=1, simulations=2, max_depth=2, hidden_dim=16, complete_episodes=True,
            parallel_envs=2, episode_workers=2, batch_size=4)
ARGUMENTS = ["--calendar-rounds", "1", "--complete-episodes", "--batches", "2", "--parallel-envs", "4",
             "--episode-workers", "2", "--games-per-process", "2", "--transitions-per-batch", "2000",
             "--simulations", "2", "--max-depth", "2", "--hidden-dim", "16",
             "--batch-size", "4", "--epochs", "2"]


def tiny_learner():
    config = run.RunConfig(**TINY)
    learner = run._learner(config, make_env(config.seed, calendar_rounds=1))
    learner.env = make_env(config.seed, calendar_rounds=1)
    return learner


def settings(learner):
    return dict(calendar_rounds=1, model_config=learner.model_config, learning_config=asdict(learner.config),
                rules_version=learner.compatibility["rules"])


def shared_workers(learner, processes=1, games_per_process=1):
    return SharedEpisodeWorkers(processes, games_per_process, device=torch.device("cpu"), **settings(learner))


def weights(seed):
    torch.manual_seed(seed)
    config = CampaignModelConfig(hidden_dim=16, message_layers=1)
    return {player: CampaignPolicyValueNet(config).state_dict() for player in PLAYERS}


def dies_sending_a_record(slots, _connections, _names, _tasks, results):
    """The other process plays on, so the coordinator keeps serving."""
    if slots == [0]:
        os.write(results.fileno(), struct.pack("!i", 1 << 20) + b"half a message")
        os._exit(9)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(60)


def killed_while_starting(*_):
    os.kill(os.getpid(), signal.SIGKILL)


def reports_each_task(_slots, _connections, _names, tasks, results):
    """Plays a task by reporting it at once, until the task pipe ends."""
    while True:
        try:
            number, task = tasks.recv()
        except EOFError:
            return
        results.send((number, {"root": task}))


def dies_in_its_second_game(marker, slots, connections, names, tasks, results):
    """The first process to start reports one game and dies in its second; the
    processes after it play on. With `marker` already there, every process dies in
    its first game."""
    try:
        open(marker, "x").close()
    except FileExistsError:
        if os.path.getsize(marker):
            tasks.recv()
            os.kill(os.getpid(), signal.SIGKILL)
        return reports_each_task(slots, connections, names, tasks, results)
    number, task = tasks.recv()
    results.send((number, {"root": task}))
    tasks.recv()
    os.kill(os.getpid(), signal.SIGKILL)


def lost(task, reason, seconds):
    return {"root": task, "failure": reason, "seconds": seconds}


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
        def stopped_after_the_process_died(*_):
            deadline = time.monotonic() + 30
            while multiprocessing.active_children() and time.monotonic() < deadline:
                time.sleep(0.05)
            return False
        records, _ = self.play(killed_while_starting, keep_playing=stopped_after_the_process_died,
                               stop_seconds=1.0, lost_game=lost)
        self.assertEqual(records, [])

    def test_a_process_that_dies_is_replaced_and_its_games_fail(self):
        # One process of two game slots: the first dies in its second game, after
        # reporting one, and the process that takes its slots plays the rest.
        games, taken = iter(range(40)), []

        def keep_playing(_server, records):
            while records:
                taken.append(records.pop(0))
            return True
        with tempfile.TemporaryDirectory() as directory:
            target = partial(dies_in_its_second_game, os.path.join(directory, "marker"))
            records, _ = play_shared_games(target, [], processes=1, games_per_process=2, models=self.MODELS,
                                           device=torch.device("cpu"), keep_playing=keep_playing,
                                           feed=lambda: next(games, None), lost_game=lost)
        taken += records
        self.assertEqual(sorted(record["root"] for record in taken), list(range(40)))  # Each game once.
        failed = [record for record in taken if "failure" in record]
        # Its second game, and perhaps one more given to it while it was dying.
        self.assertIn([record["root"] for record in failed], ([1], [1, 2]))
        self.assertRegex(failed[0]["failure"], r"^GameProcessEnded: game process \d+ ended with signal SIGKILL$")
        self.assertEqual(multiprocessing.active_children(), [])

    def test_a_process_that_dies_before_reporting_a_game_ends_the_play(self):
        # The process that takes the dead one's game slots dies in its first game.
        with tempfile.TemporaryDirectory() as directory:
            marker = os.path.join(directory, "marker")
            target = partial(dies_in_its_second_game, marker)

            games, taken = iter(range(40)), []

            def keep_playing(_server, records):
                while records:
                    taken.append(records.pop(0))
                    with open(marker, "a") as file:  # Every later process dies in its first game.
                        file.write("x")
                return True
            with self.assertRaisesRegex(ValueError, "exited abnormally: GameProcessEnded"):
                play_shared_games(target, [], processes=1, games_per_process=2, models=self.MODELS,
                                  device=torch.device("cpu"), keep_playing=keep_playing,
                                  feed=lambda: next(games, None), lost_game=lost)
            self.assertEqual(taken[0], {"root": 0})  # The first process reported a game before it died.
        self.assertEqual(multiprocessing.active_children(), [])

    @unittest.skipIf(sys.platform == "win32", "a POSIX shell script starts the game processes")
    def test_game_processes_can_start_with_another_interpreter(self):
        # GWRL_GAME_PYTHON names what the game processes start with; the coordinator is unchanged.
        with tempfile.TemporaryDirectory() as directory:
            marker, script = Path(directory) / "started", Path(directory) / "game-python"
            script.write_text(f'#!/bin/sh\necho x >> "{marker}"\nexec "{sys.executable}" "$@"\n')
            script.chmod(0o755)
            previous = multiprocessing.get_context("spawn").get_executable() if hasattr(
                multiprocessing.get_context("spawn"), "get_executable") else sys.executable
            try:
                with patch.dict(os.environ, {"GWRL_GAME_PYTHON": str(script)}):
                    records, _ = self.play(reports_each_task, processes=2)
            finally:
                multiprocessing.set_executable(previous)
            self.assertEqual(sorted(record["root"] for record in records), [1, 2])
            self.assertEqual(marker.read_text(), "x\nx\n")  # Both game processes started through it.

    def test_a_crash_that_ends_the_play_waits_for_its_crash_report(self):
        # A game process that a crash signal ends before reporting a game ends the
        # play; its crash report, which macOS writes seconds later, is copied first.
        copied = []

        def keep(pid, folder):
            def copy():
                time.sleep(0.5)
                copied.append((pid, folder))
            thread = shared_evaluator.threading.Thread(target=copy)
            thread.start()
            return thread
        with patch.object(shared_evaluator, "keep_crash_report", keep), \
                patch.object(shared_evaluator, "CRASH_SIGNALS", {signal.SIGKILL}):  # No real crash report is made.
            with self.assertRaisesRegex(ValueError, "exited abnormally: GameProcessEnded"):
                self.play(killed_while_starting, crash_reports="crash-reports")
        self.assertEqual(len(copied), 1)
        self.assertEqual(copied[0][1], "crash-reports")

    def test_fed_games_go_on_when_their_records_are_taken(self):
        # Games are fed by how many reported, not by how many records the list
        # holds, so a caller that takes each record keeps getting games.
        games, taken, deadline = iter(range(40)), [], time.monotonic() + 30

        def keep_playing(_server, records):
            while records:
                taken.append(records.pop(0)["root"])
            return time.monotonic() < deadline
        records, _ = play_shared_games(reports_each_task, [], processes=1, games_per_process=2, models=self.MODELS,
                                       device=torch.device("cpu"), keep_playing=keep_playing,
                                       feed=lambda: next(games, None))
        self.assertLess(time.monotonic(), deadline)  # Every game reported; no stop was needed.
        self.assertTrue(taken)
        self.assertEqual(sorted(taken + [record["root"] for record in records]), list(range(40)))

    def test_a_stop_kills_a_stuck_process_without_the_long_wait(self):
        started = time.monotonic()
        self.play(stuck_in_a_game, keep_playing=lambda *_: False, exit_seconds=60.0, stop_seconds=1.0)
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual(multiprocessing.active_children(), [])

    def test_a_game_process_ends_when_its_coordinator_has_gone(self):
        # The coordinator's ends are closed: the game's record cannot be sent, and
        # the task pipe ends after the one game it held.
        parent, child = multiprocessing.Pipe()
        task_reader, task_writer = multiprocessing.Pipe(duplex=False)
        result_reader, result_writer = multiprocessing.Pipe(duplex=False)
        memory = SharedMemory(create=True, size=1 << 16)
        task_writer.send((0, "a game"))
        task_writer.close()
        result_reader.close()
        played, handler = [], signal.getsignal(signal.SIGTERM)
        try:
            game_process(lambda task, _: played.append(task) or {}, "v", [0], [child], [memory.name],
                         task_reader, result_writer)
        finally:
            parent.close()
            task_reader.close()
            result_writer.close()
            memory.close()
            memory.unlink()
        self.assertEqual(played, ["a game"])
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
        sizes = report["inference_batches"]
        self.assertEqual(sum(count for count, _ in sizes.values()), report["serving_rounds"])
        self.assertEqual(sum(int(size) * count for size, (count, _) in sizes.items()), report["evaluations"])
        self.assertTrue(all(seconds > 0 for _, seconds in sizes.values()))
        # The same span as reading, answering and replying, up to the clock reads between them.
        self.assertLessEqual(sum(seconds for _, seconds in sizes.values()),
                             sum(getattr(workers.serving, part) for part in ("receive_seconds", "forward_seconds",
                                                                             "reply_seconds")) + 1e-4 * report["serving_rounds"])
        if sys.platform != "win32":  # Windows has no shared-memory manager process.
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

            def evaluate_zone(self, *_):  # The C++ search's way in.
                raise RuntimeError("rules")
        learner = tiny_learner()
        task = {"root": 3, "seed": 91, "batch_version": "v", "max_transitions": 100}
        self.assertEqual(_play_game(settings(learner), Broken(), task)["failure"], "RuntimeError: rules")


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

    def test_self_play_that_never_stops_trains_beside_its_games_and_resumes(self):
        # Stopped after its first network update, then resumed from that checkpoint;
        # the games in play at the stop are lost.
        as_written, answer_as_written = [], SharedEvaluatorServer.answer_as_written

        def recorded(server, value):
            as_written.append(value)
            answer_as_written(server, value)
        # The records each call of the run's keep_playing saw, and those it left in the list.
        seen_records, left, play = [], [], shared_evaluator.play_shared_games

        def watched(*arguments, keep_playing, **options):
            def keep(server, records):
                seen = list(records)
                going = keep_playing(server, records)
                seen_records.extend(seen)
                left.extend(record for record in seen if any(record is kept for kept in records))
                return going
            return play(*arguments, keep_playing=keep, **options)
        with patch.object(SharedEvaluatorServer, "answer_as_written", recorded), \
                patch.object(shared_evaluator, "play_shared_games", watched):
            self.assertEqual(self.train(*ARGUMENTS, "--continuous", "--stop-after-waves", "1"), 130)
        # The run took each finished game's record as it read it: the list kept none.
        self.assertGreaterEqual(len(seen_records), 4)
        self.assertEqual(left, [])
        self.assertEqual(self.train("--resume", str(self.run_dir / "checkpoint.pt")), 0)
        manifest = json.loads((self.run_dir / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["counters"]["updates"], 2)
        updates = manifest["runner"]["updates"]
        # Each network update trained on the samples of at least parallel_envs
        # finished games, all of them complete.
        self.assertTrue(all(update["rollout"]["games"] >= 4 and update["rollout"]["terminal"]
                            and not update["rollout"]["bootstrap_samples"] for update in updates))
        # While the first network update trained beside the games, the inference
        # server ran the layers as written, and the compiled ones again after it.
        self.assertEqual(as_written, [True, False])
        # The games went on through the first network update, and the inference
        # server took up its networks: the second update's games were answered by a
        # version no game before the first update saw.
        first, second = (set(update["rollout"]["rollout_versions"]) for update in updates)
        self.assertEqual(len(first), 1)
        self.assertTrue(second - first)
        self.assertTrue(all(update["evaluator"]["evaluations"] > 0 for update in updates))
        self.assertTrue((self.run_dir / "models" / "generation-000002.pt").exists())
        self.assertGreaterEqual(manifest["counters"]["episodes"], 8)

    def test_self_play_that_never_stops_needs_one_inference_server(self):
        with self.assertRaisesRegex(ValueError, "needs games per process"):
            run.RunConfig(complete_episodes=True, parallel_envs=4, episode_workers=2, continuous=True)
        for device in ("cpu", "mps", "cuda"):  # The trainer works beside the inference server, on its device.
            config = run.RunConfig(complete_episodes=True, parallel_envs=4, episode_workers=2, games_per_process=2,
                                   continuous=True, neural_device=device)
            self.assertEqual(run.busy_cores(config), 4)  # Two game processes, the inference server, the trainer.

    def test_games_per_process_needs_episode_workers(self):
        with self.assertRaisesRegex(ValueError, "needs episode workers"):
            run.RunConfig(games_per_process=4)
        with self.assertRaisesRegex(ValueError, "nonnegative integer"):
            run.RunConfig(games_per_process=-1)


if __name__ == "__main__":
    unittest.main()
