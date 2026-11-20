#!/usr/bin/env python3
"""Replay, in a fresh process, a failed move that a training run kept.

A game that fails on a move the engine had accepted, such as a move after which
the state fails the engine's check (State::validate in src/campaign_state.cpp),
keeps the position before the move and the move in its run's failed-positions/
folder (FailedMoveError in studies/shared/campaign_adapter.py). This tool loads
that position and plays the move again, as the game or the search's copy played
it, and reports one outcome:

- position_fails_on_loading: the kept position fails the engine's check as it
  loads, so it was damaged before the move, after the check of the move before
  it had passed;
- same_failure: the move fails again with the same error, so the failure
  follows from the position and the move: a defect of the rules;
- move_succeeds or different_failure: the failure did not follow from the
  position and the move, so something outside them caused it, most likely
  damaged memory in the game process;
- move_not_offered: the loaded position does not offer the move;
- no_position: the game process could not write the position.

Run it with the code that played the game (a run's frozen copy), whose rules
made the position; the run's manifest, two folders up, gives the game rounds:

    .venv/bin/python tools/replay_failed_move.py RUN/failed-positions/game-N-seed-S.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studies.shared.campaign_adapter import FAILED_MOVE_SCHEMA  # noqa: E402

EXPLANATIONS = {
    "position_fails_on_loading": "The kept position fails the engine's check as it loads: it was damaged "
                                 "before the move, after the check of the move before it had passed.",
    "same_failure": "The move fails again with the same error: the failure follows from the position and "
                    "the move, a defect of the rules.",
    "different_failure": "The move fails with another error: the original failure did not follow from the "
                         "position and the move alone.",
    "move_succeeds": "The move succeeds: the failure did not follow from the position and the move, so "
                     "something outside them caused it, most likely damaged memory in the game process.",
    "move_not_offered": "The loaded position does not offer the move.",
    "no_position": "The game process could not write the position.",
}


def calendar_rounds_of(path: Path) -> int | None:
    """The game rounds of the run whose failed-positions/ folder holds `path`."""
    manifest = path.resolve().parent.parent / "manifest.json"
    if not manifest.is_file():
        return None
    return json.loads(manifest.read_text())["runner"]["config"]["calendar_rounds"]


def _one(actions: list[Any], identity: str, kind: str | None = None) -> Any:
    matches = [action for action in actions if action.id == identity and (kind is None or action.kind == kind)]
    return matches[0] if len(matches) == 1 else None


def replay(document: dict[str, Any], calendar_rounds: int | None) -> dict[str, Any]:
    """Load the kept position, play the kept move, and say what happened."""
    from studies.campaign.curriculum import make_env

    if document.get("schema") != FAILED_MOVE_SCHEMA:
        raise ValueError(f"Not a failed move ({FAILED_MOVE_SCHEMA})")
    result = {"where": document["where"], "move": document["move"], "error": document["error"]}
    if document.get("position") is None:
        return {**result, "outcome": "no_position", "position_error": document.get("position_error")}
    env = make_env(0, calendar_rounds=calendar_rounds)  # Only its scenario and rules are used.
    try:
        env.restore(document["position"])
    except Exception as error:
        return {**result, "outcome": "position_fails_on_loading", "loading_error": f"{type(error).__name__}: {error}"}
    move = document["move"]
    try:
        if "search_stream" not in move:
            # Played through the adapter, as the game or the Python search plays
            # a move; the kept position holds its dice as they stood.
            if move["kind"] == "chance":
                env.resolve_chance()
            else:
                action = _one(env.legal_actions(), move["id"], move["kind"])
                if action is None:
                    return {**result, "outcome": "move_not_offered"}
                env.apply_action(action)
        else:
            # As the C++ search played it: on a search copy whose dice stand where they stood.
            copy = env.raw.clone_for_search_from(int(move["search_stream"]))
            if move["kind"] == "chance":
                copy.resolve_chance()
            else:
                listed = copy.legal_interrupts() if move["kind"] == "interrupt" else copy.legal_actions()
                action = _one(listed, move["id"])
                if action is None:
                    return {**result, "outcome": "move_not_offered"}
                (copy.apply_interrupt if move["kind"] == "interrupt" else copy.apply_action)(action)
    except Exception as error:
        outcome = "same_failure" if str(error) == document["error"] else "different_failure"
        return {**result, "outcome": outcome, "replay_error": f"{type(error).__name__}: {error}"}
    return {**result, "outcome": "move_succeeds"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("path", type=Path, help="A failed move's file in a run's failed-positions/ folder")
    parser.add_argument("--calendar-rounds", type=int,
                        help="The game rounds of the run; read from the run's manifest when left out")
    args = parser.parse_args(argv)
    rounds = args.calendar_rounds if args.calendar_rounds is not None else calendar_rounds_of(args.path)
    result = replay(json.loads(args.path.read_text()), rounds)
    print(json.dumps({**result, "explanation": EXPLANATIONS[result["outcome"]]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
