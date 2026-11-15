#!/usr/bin/env python3
"""Play random games and record which of the network's questions are ever answered.

The network's input asks fixed questions about each zone, about the position as
a whole and about each legal move (docs/design/network_input.md). This plays
the games of tools/check_zone_names.py, encodes every decision and every dice
position, and writes for each question that was answered: in how many encoded
positions, in how many games, and its smallest and largest answer. For the
board a position counts once if any zone answers the question, for the moves
once if any move does.

A question no game answers is a candidate for removal, not a proof: only the
rules can show that it is impossible. A question answered alike in every
position tells no two positions apart. Run it before and after changing the
lists of questions.

    ./.venv/bin/python tools/answer_census.py OUT.json --first-seed 7000 9000 --games 240 --workers 8

Every part's families are always counted. `--detail` names the parts whose
answered questions are also listed one by one; the full list of all three is
about half a megabyte.

Measured on 15 November 2026 (M4 Max): 480 games take about four minutes on 8
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
# The input's three parts, with the names its arrays and its layout use for them.
PARTS = (("board", "zone"), ("position", "global"), ("moves", "action"))


def play(job: tuple[int, int]) -> tuple[int, bool, int, int, dict[str, dict[int, tuple[int, int, int]]], dict[str, int]]:
    seed, rounds = job
    sys.path.insert(0, str(ROOT))
    import numpy as np

    import gwrl_cpp
    from studies.campaign.curriculum import make_env

    gwrl_cpp.zone_encoding_unknowns(True)
    env, rng = make_env(seed, calendar_rounds=rounds), random.Random(seed)
    spec = env.raw.zone_encoding_spec()
    sizes = {part: int(spec[f"{key}_columns"]) for part, key in PARTS}
    count = {part: np.zeros(size, dtype=np.int64) for part, size in sizes.items()}
    least = {part: np.full(size, np.iinfo(np.int64).max, dtype=np.int64) for part, size in sizes.items()}
    most = {part: np.full(size, np.iinfo(np.int64).min, dtype=np.int64) for part, size in sizes.items()}
    # The same policy as tools/check_zone_names.py.
    end_early = (0.02, 0.05, 0.10)[seed % 3]
    decisions = dice = 0

    def note(zone) -> None:
        arrays = zone.arrays()
        for part, key in PARTS:
            columns, values = arrays[f"{key}_column"], arrays[f"{key}_value"]
            count[part][np.unique(columns)] += 1
            np.minimum.at(least[part], columns, values)
            np.maximum.at(most[part], columns, values)

    while not env.is_terminal() and decisions < 6000:
        if env.decision_kind() == "chance":
            note(env.zone_input(()))
            dice += 1
            env.resolve_chance()
            continue
        actions = tuple(env.legal_actions())
        note(env.zone_input(actions))
        ends = [action for action in actions if action.id.endswith(":play:end_phase")]
        if ends and rng.random() < end_early:
            env.apply_action(ends[0])
        else:
            env.apply_action(rng.choice(actions))
        decisions += 1
    answered = {part: {int(i): (int(count[part][i]), int(least[part][i]), int(most[part][i]))
                       for i in np.nonzero(count[part])[0]} for part, _ in PARTS}
    return seed, env.is_terminal(), decisions, dice, answered, gwrl_cpp.zone_encoding_unknowns(True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out")
    parser.add_argument("--first-seed", type=int, nargs="+", default=[7000], help="each starts a run of --games seeds")
    parser.add_argument("--games", type=int, default=240)
    parser.add_argument("--rounds", type=int, default=11)
    parser.add_argument("--workers", type=int, default=8, help="at most the allowed CPU cores")
    parser.add_argument("--detail", nargs="*", choices=[part for part, _ in PARTS], default=[part for part, _ in PARTS],
                        help="the parts whose answered questions are listed one by one (default: all three)")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    from studies.campaign.curriculum import make_env

    spec = make_env(args.first_seed[0], calendar_rounds=args.rounds).raw.zone_encoding_spec()
    names = {part: list(spec[f"{key}_column_names"]) for part, key in PARTS}
    jobs = [(seed, args.rounds) for first in args.first_seed for seed in range(first, first + args.games)]
    with get_context("spawn").Pool(args.workers) as pool:
        results = pool.map(play, jobs, chunksize=1)

    positions = sum(result[2] + result[3] for result in results)
    unknown: collections.Counter[str] = collections.Counter()
    parts = {}
    for part, _ in PARTS:
        seen: dict[int, list[int]] = {}
        for _, _, _, _, answered, _ in results:
            for index, (count, low, high) in answered[part].items():
                entry = seen.setdefault(index, [0, 0, low, high])
                entry[0] += count
                entry[1] += 1
                entry[2] = min(entry[2], low)
                entry[3] = max(entry[3], high)
        families: dict[str, list[int]] = {}
        for index, name in enumerate(names[part]):
            family = families.setdefault(name.split(":")[0], [0, 0])
            family[0] += 1
            family[1] += index in seen
        parts[part] = {
            "questions": len(names[part]),
            "answered_questions": len(seen),
            # Answered in every encoded position, always with the same answer.
            "always_the_same": sorted(names[part][i] for i, (count, _, low, high) in seen.items()
                                      if count == positions and low == high),
            "families": {family: {"questions": total, "answered": answered} for family, (total, answered) in families.items()},
        }
        if part in args.detail:
            parts[part]["answered"] = {names[part][i]: seen[i] for i in sorted(seen)}
    for result in results:
        unknown.update(result[5])
    report = {
        "layout": spec["version"], "first_seeds": args.first_seed, "games": len(results), "rounds": args.rounds,
        "finished": sum(1 for result in results if result[1]),
        "decisions": sum(result[2] for result in results), "dice_positions": sum(result[3] for result in results),
        "answered_columns": ["encoded positions", "games", "smallest answer", "largest answer"],
        "unknown": dict(unknown.most_common()),
        "parts": parts,
    }
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    summary = {key: value for key, value in report.items() if key != "parts"}
    summary["answered_questions"] = {part: f"{parts[part]['answered_questions']} of {parts[part]['questions']}" for part, _ in PARTS}
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
