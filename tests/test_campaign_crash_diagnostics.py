"""What a training run keeps so that a crashed game process can be looked into:
each game's move log, which rebuilds its position, and the crash report."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import gwrl_cpp

from studies.campaign.curriculum import make_env
from studies.campaign.episode_workers import _lost_game, _play_game, game_moves_name
from studies.campaign.learning import MOVES_SCHEMA, LearningConfig, play_episode
from studies.campaign.shared_evaluator import keep_crash_report
from studies.shared.multiplayer_mcts import UniformEvaluator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from replay_game_moves import read_log, replay  # noqa: E402

SEED = 7


def played_game() -> tuple[str, object]:
    """A one-round game searched with uniform priors, and its move log."""
    moves = io.StringIO()
    moves.write(json.dumps({"schema": MOVES_SCHEMA, "root": 0, "seed": SEED, "calendar_rounds": 1}) + "\n")
    env = make_env(SEED, calendar_rounds=1)
    play_episode(env, UniformEvaluator(), config=LearningConfig(simulations=4, max_depth=4, sample_fraction=0.05),
                 rules_version="test", batch_version="test", environment_seed=SEED, max_transitions=100000,
                 moves=moves)
    return moves.getvalue(), env


class MoveLogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log, cls.env = played_game()

    def write(self, directory: str, text: str) -> Path:
        path = Path(directory) / "game.jsonl"
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_move_log_rebuilds_the_game(self):
        self.assertTrue(self.env.is_terminal())
        with tempfile.TemporaryDirectory() as directory:
            header, moves = read_log(self.write(directory, self.log))
        kinds = {move["kind"] for move in moves}
        self.assertEqual(kinds, {"search", "action", "chance"})
        # A kept decision's full search adds exploration noise; any other's fast search adds none and
        # counts the visits its root holds from the reused tree toward its budget.
        self.assertEqual({(move["simulations"], move["root_noise"], move["count_reused_visits"], move["max_depth"],
                           move["simulations_per_request"]) for move in moves if move["kind"] == "search"},
                         {(4, True, False, 4, 1), (4, False, True, 4, 1)})
        result = replay(header, moves)
        self.assertEqual(result["outcome"], "replayed")
        self.assertEqual(result["final_planning_key"], self.env.planning_key())
        self.assertTrue(result["terminal"])
        self.assertIsNone(result["search_under_way"])

    def test_a_log_cut_during_a_search_shows_the_search_and_searches_again(self):
        lines = self.log.splitlines()
        searches = [index for index, line in enumerate(lines) if json.loads(line).get("kind") == "search"]
        cut = searches[5]  # The process died during the sixth decision's search, and a line was half written.
        text = "\n".join(lines[:cut + 1]) + "\n" + lines[cut + 1][:7]
        with tempfile.TemporaryDirectory() as directory:
            header, moves = read_log(self.write(directory, text))
        result = replay(header, moves, search_last=2)
        self.assertEqual(result["outcome"], "replayed")
        self.assertEqual(result["search_under_way"], json.loads(lines[cut]))
        self.assertEqual(result["searches"], 3)  # The last two decisions played, and the one under way.

    def test_a_move_the_position_does_not_offer_is_named(self):
        lines = self.log.splitlines()
        first = next(index for index, line in enumerate(lines) if json.loads(line).get("kind") == "action")
        changed = json.loads(lines[first])
        changed["action"] = "no-such-action"
        lines[first] = json.dumps(changed)
        with tempfile.TemporaryDirectory() as directory:
            header, moves = read_log(self.write(directory, "\n".join(lines) + "\n"))
        self.assertEqual(replay(header, moves)["outcome"], "move_not_offered")


class GameProcessMoveLogTest(unittest.TestCase):
    def settings(self, directory: str) -> dict:
        return dict(calendar_rounds=1, learning_config={"simulations": 4, "max_depth": 4, "sample_fraction": 0.05},
                    rules_version="test", game_moves=str(Path(directory) / "game-moves"))

    def task(self) -> dict:
        return {"root": 3, "seed": SEED, "batch_version": "test", "max_transitions": 100000}

    def test_a_finished_game_removes_its_log(self):
        with tempfile.TemporaryDirectory() as directory:
            record = _play_game(self.settings(directory), UniformEvaluator(), self.task())
            self.assertNotIn("failure", record)
            self.assertEqual(list((Path(directory) / "game-moves").iterdir()), [])

    def test_a_failed_game_keeps_its_log_and_a_stopped_game_does_not(self):
        def failing(error):
            def play(*args, moves, **kwargs):
                moves.write('{"kind":"chance","move":0}\n')
                raise error
            return play

        for error, kept in ((RuntimeError("A zone number names no zone"), True),
                            (gwrl_cpp.InferenceClosed("The shared evaluator closed this game thread's pipe"), False)):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                with mock.patch("studies.campaign.learning.play_episode", failing(error)):
                    record = _play_game(self.settings(directory), UniformEvaluator(), self.task())
                path = Path(directory) / "game-moves" / game_moves_name(self.task())
                self.assertEqual(path.exists(), kept)
                self.assertEqual(record.get("moves"), f"game-moves/{path.name}" if kept else None)
                if kept:
                    header, moves = read_log(path)
                    self.assertEqual((header["schema"], header["seed"], moves), (MOVES_SCHEMA, SEED, [
                        {"kind": "chance", "move": 0}]))

    def test_a_game_lost_with_its_process_names_its_log(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.settings(directory)
            reason = "GameProcessEnded: game process 1 ended with signal SIGABRT"
            self.assertNotIn("moves", _lost_game(settings, self.task(), reason, 9.0))
            path = Path(settings["game_moves"]) / game_moves_name(self.task())
            path.parent.mkdir()
            path.write_text("{}\n")
            record = _lost_game(settings, self.task(), reason, 9.0)
        self.assertEqual(record, {"root": 3, "seed": SEED, "failure": reason, "seconds": 9.0,
                                  "moves": f"game-moves/{path.name}"})


class CrashReportTest(unittest.TestCase):
    def test_the_report_with_the_dead_process_pid_is_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            reports, run = Path(directory) / "reports", Path(directory) / "run" / "crash-reports"
            reports.mkdir()
            for name, pid in (("python3.13-a.ips", 11), ("python3.13-b.ips", 12)):
                (reports / name).write_text(json.dumps({"bug_type": "309"}) + "\n" + json.dumps({"pid": pid}))
            thread = keep_crash_report(12, str(run), reports=reports, wait_seconds=5.0)
            thread.join(10.0)
            self.assertEqual((run / "game-process-12.ips").read_text().split("\n")[1], json.dumps({"pid": 12}))
            self.assertEqual(sorted(path.name for path in run.iterdir()), ["game-process-12.ips"])


if __name__ == "__main__":
    unittest.main()
