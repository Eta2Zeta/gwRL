#!/usr/bin/env python3
"""Find campaign dead ends and engine errors with seeded random games.

Each game plays the campaign through the environment that search uses, choosing
uniformly among legal actions and ending a phase with extra probability (2%, 5%
or 10% by seed) so games reach later rounds. A game stops at a nonterminal
decision with no legal action, at an engine error, or at its end. Failing
positions are saved for inspection; replaying the seed reproduces the game.
Random play reaches far more unusual positions per second than search-driven
self-play, so run it after rules changes and before long self-play runs.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BIASES = (0.02, 0.05, 0.1)


def play(seed: int, rounds: int, max_decisions: int, output: Path) -> dict:
    """Play one seeded random game, saving the position of any failure."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from studies.campaign.curriculum import make_env
    started = time.perf_counter()
    bias = BIASES[seed % len(BIASES)]
    env = make_env(seed, calendar_rounds=rounds)
    rng = random.Random(f"fuzz:{seed}")
    decisions, problem = 0, None
    while not env.is_terminal() and decisions < max_decisions:
        if env.decision_kind() == "chance":
            env.resolve_chance()
            continue
        options = list(env.legal_actions())
        if not options:
            problem = {"kind": "no_legal_action", "decision_kind": env.decision_kind(),
                       "player": env.current_decision_player()}
            (output / f"dead-end-{seed}.json").write_text(json.dumps({"seed": seed, **problem,
                                                                      "state": env.raw.serialize()}) + "\n")
            break
        ending = [action for action in options if action.id.endswith(":play:end_phase")]
        choice = ending[0] if ending and rng.random() < bias else rng.choice(options)
        before = env.raw.serialize()
        try:
            env.apply_action(choice)
        except (RuntimeError, ValueError) as error:
            problem = {"kind": "engine_error", "error": str(error), "action": choice.id}
            (output / f"error-{seed}.json").write_text(json.dumps({"seed": seed, **problem, "state": before}) + "\n")
            break
        decisions += 1
    clock = json.loads(env.raw.serialize())["state"]["clock"]
    return {"seed": seed, "bias": bias, "decisions": decisions, "terminal": env.is_terminal(),
            "completed_rounds": clock["completed_rounds"], "problem": problem,
            "seconds": time.perf_counter() - started}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True, help="Directory for results and failing positions")
    parser.add_argument("--first-seed", type=int, default=5000)
    parser.add_argument("--games", type=int, default=320)
    parser.add_argument("--rounds", type=int, default=11)
    parser.add_argument("--max-decisions", type=int, default=8000)
    parser.add_argument("--processes", type=int, default=10, help="Game processes; keep within the CPU allowance")
    parser.add_argument("--seconds", type=float, default=1800.)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.seconds
    seeds = range(args.first_seed, args.first_seed + args.games)
    tasks = [(seed, args.rounds, args.max_decisions, args.output) for seed in seeds]
    results = []
    with (args.output / "results.jsonl").open("a") as log, \
            multiprocessing.get_context("spawn").Pool(args.processes, maxtasksperchild=20) as pool:
        for result in pool.imap_unordered(_play, tasks):
            results.append(result)
            log.write(json.dumps(result) + "\n"); log.flush()
            if result["problem"]:
                print(json.dumps(result), flush=True)
            if time.monotonic() > deadline:
                pool.terminate()
                break
    failed = [result for result in results if result["problem"]]
    print(json.dumps({"games": len(results), "completed": sum(result["terminal"] for result in results),
                      "problems": len(failed), "seeds": sorted(result["seed"] for result in failed)}))
    return 1 if failed else 0


def _play(task):
    return play(*task)


if __name__ == "__main__":
    raise SystemExit(main())
