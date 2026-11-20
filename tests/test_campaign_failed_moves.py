"""A move the engine accepts and then fails on keeps its position and the move, and replays."""
from __future__ import annotations

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import gwrl_cpp

from studies.campaign.curriculum import make_env
from studies.campaign.episode_workers import _play_game
from studies.campaign.native_search import search_decision
from studies.shared.campaign_adapter import FAILED_MOVE_SCHEMA, FailedMoveError
from studies.shared.multiplayer_mcts import MctsConfig, UniformEvaluator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from replay_failed_move import replay  # noqa: E402

TESTED_FAILURE = "A transition failed, as a test asked"


def kept(error: FailedMoveError) -> dict:
    document = json.loads(error.state)
    assert document["schema"] == FAILED_MOVE_SCHEMA
    return document


def at_chance() -> object:
    """A one-round game played at random until it reaches dice to roll."""
    env, chooser = make_env(7, calendar_rounds=1), random.Random(0)
    while env.decision_kind() != "chance":
        env.apply_action(chooser.choice(env.legal_actions()))
    return env


def with_tape(env, faces: list[int]) -> None:
    """Give the position a test dice tape through its serialized form."""
    position = json.loads(env.serialize())
    raw = json.loads(position["raw"])
    raw["random"].update(test_tape=faces, tape_position="0")
    position["raw"] = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    env.restore(json.dumps(position, sort_keys=True, separators=(",", ":")))


class FailedMoveTest(unittest.TestCase):
    def test_the_native_error_is_a_runtime_error(self):
        self.assertTrue(issubclass(gwrl_cpp.SearchMoveFailed, RuntimeError))
        self.assertTrue(issubclass(FailedMoveError, RuntimeError))

    def test_a_failed_game_move_keeps_the_position_before_it_and_the_move(self):
        env = make_env(7, calendar_rounds=1)
        before = env.serialize()
        env.raw.fail_transitions_for_testing()
        action = env.legal_actions()[0]
        with self.assertRaises(FailedMoveError) as raised:
            env.apply_action(action)
        self.assertEqual(str(raised.exception), TESTED_FAILURE)
        document = kept(raised.exception)
        self.assertEqual((document["where"], document["move"], document["position"], document["error"]),
                         ("game", {"kind": action.kind, "id": action.id}, before, TESTED_FAILURE))
        self.assertEqual(env.serialize(), before)  # An ordinary engine is left as it was.
        # A fresh position does not carry the test's failure, so the move succeeds.
        self.assertEqual(replay(document, 1)["outcome"], "move_succeeds")

    def test_a_failed_search_move_keeps_its_node_and_where_the_dice_stood(self):
        env = make_env(7, calendar_rounds=1)
        env.raw.fail_transitions_for_testing()
        config = MctsConfig(simulations=8, max_depth=4, seed=3, mode="multiplayer")
        with self.assertRaises(FailedMoveError) as raised:
            search_decision(env, UniformEvaluator(), config, add_root_noise=False)
        document = kept(raised.exception)
        self.assertEqual((document["where"], document["error"]), ("search", TESTED_FAILURE))
        self.assertEqual(set(document["move"]), {"kind", "id", "search_stream"})
        self.assertIn(document["move"]["id"], {action.id for action in env.raw.legal_actions()}
                      | {action.id for action in env.raw.legal_interrupts()})
        # The failure happened at the search's root: a search copy of this position.
        self.assertEqual(json.loads(document["position"])["anchor"], env.raw.planning_key())
        self.assertEqual(replay(document, 1)["outcome"], "move_succeeds")

    def test_a_python_search_copy_keeps_no_position(self):
        # The Python search's copies change in place, so a failed move leaves
        # nothing to keep; the C++ search keeps its node's position instead.
        from studies.shared.campaign_adapter import CampaignAdapter
        copy = CampaignAdapter(make_env(7, calendar_rounds=1).raw.clone_for_search(5))
        copy.raw.fail_transitions_for_testing()
        action = copy.legal_actions()[0]
        with self.assertRaises(FailedMoveError) as raised:
            copy.apply_action(action)
        document = kept(raised.exception)
        self.assertEqual((document["where"], document["position"], document["position_error"]),
                         ("unknown", None, "RuntimeError: Search copy failed during a transition"))
        self.assertEqual(replay(document, 1)["outcome"], "no_position")

    def test_a_failure_that_follows_from_the_position_fails_again(self):
        env = at_chance()
        with_tape(env, [99])  # No die has 99 faces.
        with self.assertRaises(FailedMoveError) as raised:
            env.resolve_chance()
        document = kept(raised.exception)
        self.assertEqual((document["where"], document["move"]), ("game", {"kind": "chance"}))
        result = replay(document, 1)
        self.assertEqual((result["outcome"], result["replay_error"]),
                         ("same_failure", "FailedMoveError: Test dice tape face outside die range"))

    def test_a_damaged_position_fails_as_it_loads(self):
        env = make_env(7, calendar_rounds=1)
        position = json.loads(env.serialize())
        raw = json.loads(position["raw"])
        unit = next(iter(raw["state"]["units"].values()))
        unit["zone"] = "no_such_zone"
        position["raw"] = json.dumps(raw, sort_keys=True, separators=(",", ":"))
        action = env.legal_actions()[0]
        document = json.loads(FailedMoveError("A zone number names no zone", where="game",
                                              move={"kind": action.kind, "id": action.id},
                                              position=json.dumps(position)).state)
        self.assertEqual(replay(document, 1)["outcome"], "position_fails_on_loading")

    def test_a_game_process_writes_a_failed_position_at_once(self):
        state = FailedMoveError("A zone number names no zone", where="search", move={"kind": "chance"},
                                position=None, position_error="unreadable").state

        def failing(*args, **kwargs):
            raise FailedMoveError.from_search(json.dumps({"error": "A zone number names no zone",
                                                          "move": {"kind": "chance"},
                                                          "position_error": "unreadable"}))

        with tempfile.TemporaryDirectory() as directory:
            settings = dict(calendar_rounds=1, learning_config={}, rules_version="r",
                            failed_positions=str(Path(directory) / "failed-positions"))
            with mock.patch("studies.campaign.learning.play_episode", failing):
                failure = _play_game(settings, None, {"root": 5, "seed": 11, "batch_version": "v",
                                                      "max_transitions": 9})
            written = (Path(directory) / "failed-positions" / "game-5-seed-11.json").read_text()
        self.assertEqual(failure["failure"], "FailedMoveError: A zone number names no zone")
        self.assertEqual(failure["position"], "failed-positions/game-5-seed-11.json")
        self.assertNotIn("state", failure)
        self.assertEqual(written, state)
        self.assertEqual(replay(json.loads(written), 1)["outcome"], "no_position")


if __name__ == "__main__":
    unittest.main()
