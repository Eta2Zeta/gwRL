#!/usr/bin/env python3
"""Encode every decision of random games and report names the zone encoding lacks.

The encoder translates the engine's names through fixed lists; a name missing
from its list falls into an "other" question and is counted. This plays
eleven-round games with uniformly random moves, ending a phase early with a
small probability so games reach later rounds, encodes every decision and
prints the counted names. An empty "unknown" means every name met has its own
question. Run it before a long self-play run, and after a rule change that may
write new names.

    ./.venv/bin/python tools/check_zone_names.py OUT.json --first-seed 7000 --games 240 --workers 8

Measured on 4 November 2026 (M4 Max): 240 games take about two minutes on 8
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


def play(job: tuple[int, int]) -> tuple[int, bool, int, dict[str, int]]:
    seed, rounds = job
    sys.path.insert(0, str(ROOT))
    import gwrl_cpp
    from studies.campaign.curriculum import make_env

    gwrl_cpp.zone_encoding_unknowns(True)
    env, rng = make_env(seed, calendar_rounds=rounds), random.Random(seed)
    end_early = (0.02, 0.05, 0.10)[seed % 3]
    decisions = 0
    while not env.is_terminal() and decisions < 6000:
        if env.decision_kind() == "chance":
            env.zone_input(())
            env.resolve_chance()
            continue
        actions = tuple(env.legal_actions())
        env.zone_input(actions)
        ends = [action for action in actions if action.kind == "end_phase"]
        env.apply_action(ends[0] if ends and rng.random() < end_early else rng.choice(actions))
        decisions += 1
    return seed, env.is_terminal(), decisions, gwrl_cpp.zone_encoding_unknowns(True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out")
    parser.add_argument("--first-seed", type=int, default=7000)
    parser.add_argument("--games", type=int, default=240)
    parser.add_argument("--rounds", type=int, default=11)
    parser.add_argument("--workers", type=int, default=8, help="at most the allowed CPU cores")
    args = parser.parse_args()
    jobs = [(seed, args.rounds) for seed in range(args.first_seed, args.first_seed + args.games)]
    with get_context("spawn").Pool(args.workers) as pool:
        results = pool.map(play, jobs, chunksize=1)
    unknown: collections.Counter[str] = collections.Counter()
    seeds: dict[str, list[int]] = collections.defaultdict(list)
    for seed, _, _, names in results:
        unknown.update(names)
        for name in names:
            seeds[name].append(seed)
    report = {
        "first_seed": args.first_seed, "games": len(results), "rounds": args.rounds,
        "finished": sum(1 for r in results if r[1]), "decisions": sum(r[2] for r in results),
        "unknown": dict(unknown.most_common()),
        "unknown_seeds": {name: seeds[name][:10] for name, _ in unknown.most_common()},
    }
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "unknown_seeds"}, indent=1))


if __name__ == "__main__":
    main()
