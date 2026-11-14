#!/usr/bin/env python3
"""Play random games and record where every kind of move is offered.

The engine pages in docs/engine say in which phase each kind of move is made
and whether it is the active nation's own move or an answer to a waiting
decision. This plays eleven-round games with uniformly random moves, ending a
phase early with a small probability so that games reach later rounds, and
writes for every kind of move: how often it was offered and chosen, in which
phases, for which nations, the decision kinds it answered, its detail names and
one example. It also counts decision kinds and what the dice were rolled for.
Run it again after a rule change that adds or moves a kind of move.

    ./.venv/bin/python tools/move_census.py OUT.json --games 240 --workers 8 --first-seed 9000

Measured on 14 November 2026 (M4 Max): 240 games take about six minutes on 8
workers.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTERS = ("phases", "decision_kinds", "nations", "answers")


def _new_entry() -> dict:
    return {"offered_at": 0, "chosen": 0, "parameters": set(), "example": None,
            **{name: collections.Counter() for name in COUNTERS}}


def _kind(action) -> tuple[str, dict]:
    """The engine's kind of a move and its record; a pass has only the scheduler's label."""
    raw = action.features().get("action") or {}
    return raw.get("kind") or action.kind, raw


def play(seed: int) -> dict:
    sys.path.insert(0, str(ROOT))
    from studies.campaign.curriculum import make_env

    env, rng = make_env(seed, calendar_rounds=11), random.Random(seed)
    end_early = (0.02, 0.05, 0.10)[seed % 3]
    kinds: dict[str, dict] = collections.defaultdict(_new_entry)
    decision_kinds: collections.Counter = collections.Counter()
    chance: collections.Counter = collections.Counter()
    decisions = largest_menu = 0
    while not env.is_terminal() and decisions < 8000:
        if env.decision_kind() == "chance":
            request = env.chance_request() or {}
            chance[(request.get("purpose", "?"), tuple(die.get("sides") for die in request.get("dice", [])))] += 1
            env.resolve_chance()
            continue
        actions = tuple(env.legal_actions())
        clock = env.observation()["state"]["clock"]
        phase, decision_kind = clock["phase"], env.decision_kind()
        decision_kinds[decision_kind] += 1
        largest_menu = max(largest_menu, len(actions))
        seen = set()
        for action in actions:
            kind, raw = _kind(action)
            if kind in seen:
                continue
            seen.add(kind)
            entry = kinds[kind]
            entry["offered_at"] += 1
            entry["phases"][phase] += 1
            entry["decision_kinds"][decision_kind] += 1
            entry["nations"][raw.get("nation", "?")] += 1
            entry["answers"]["a waiting decision" if raw.get("decision") else "own move"] += 1
            entry["parameters"].update((raw.get("parameters") or {}).keys())
            if entry["example"] is None:
                entry["example"] = {"seed": seed, "round": clock["round_index"] + 1, "phase": phase,
                                    "player": env.current_decision_player(), "nation": raw.get("nation"),
                                    "parameters": raw.get("parameters")}
        ends = [action for action in actions if action.id.endswith(":play:end_phase")]
        chosen = ends[0] if ends and rng.random() < end_early else rng.choice(actions)
        kinds[_kind(chosen)[0]]["chosen"] += 1
        env.apply_action(chosen)
        decisions += 1
    return {"seed": seed, "terminal": env.is_terminal(), "decisions": decisions, "largest_menu": largest_menu,
            "kinds": {kind: {**entry, "parameters": sorted(entry["parameters"]),
                             **{name: dict(entry[name]) for name in COUNTERS}} for kind, entry in kinds.items()},
            "decision_kinds": dict(decision_kinds),
            "chance": [[purpose, list(sides), count] for (purpose, sides), count in chance.items()]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out")
    parser.add_argument("--first-seed", type=int, default=9000)
    parser.add_argument("--games", type=int, default=240)
    parser.add_argument("--workers", type=int, default=8, help="at most the allowed CPU cores")
    args = parser.parse_args()
    seeds = range(args.first_seed, args.first_seed + args.games)
    with get_context("spawn").Pool(args.workers) as pool:
        results = pool.map(play, seeds, chunksize=1)
    kinds: dict[str, dict] = {}
    decision_kinds: collections.Counter = collections.Counter()
    chance: collections.Counter = collections.Counter()
    for result in results:
        decision_kinds.update(result["decision_kinds"])
        for purpose, sides, count in result["chance"]:
            chance[(purpose, "D" + "+D".join(str(side) for side in sorted(set(sides))))] += count
        for kind, entry in result["kinds"].items():
            total = kinds.setdefault(kind, {"games": 0, "offered_at": 0, "chosen": 0, "parameters": set(),
                                            "example": entry["example"], **{name: {} for name in COUNTERS}})
            total["games"] += 1
            total["offered_at"] += entry["offered_at"]
            total["chosen"] += entry["chosen"]
            total["parameters"].update(entry["parameters"])
            for name in COUNTERS:
                for key, count in entry[name].items():
                    total[name][key] = total[name].get(key, 0) + count
    for entry in kinds.values():
        entry["parameters"] = sorted(entry["parameters"])
    lengths = sorted(result["decisions"] for result in results)
    report = {
        "first_seed": args.first_seed, "games": len(results), "finished": sum(r["terminal"] for r in results),
        "decisions": sum(lengths), "decisions_per_game": {"least": lengths[0], "median": lengths[len(lengths) // 2],
                                                          "most": lengths[-1]},
        "largest_menu": max(r["largest_menu"] for r in results),
        "kinds_seen": len(kinds), "kinds": dict(sorted(kinds.items())),
        "decision_kinds": dict(decision_kinds.most_common()),
        "dice": [{"purpose": purpose, "dice": dice, "rolls": count} for (purpose, dice), count in chance.most_common()],
    }
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({key: report[key] for key in ("games", "finished", "decisions", "decisions_per_game",
                                                   "largest_menu", "kinds_seen")}, indent=1))


if __name__ == "__main__":
    main()
