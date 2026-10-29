#!/usr/bin/env python3
"""Find campaign dead ends and engine errors with seeded random games.

Each game plays the campaign through the environment that search uses, choosing
uniformly among legal actions and ending a phase with extra probability (2%, 5%
or 10% by seed) so games reach later rounds. A game stops at a nonterminal
decision with no legal action, at an engine error, at a Combat Movement move
that leaves some airborne aircraft no reachable joint landing plan, when ending
a phase loses aircraft that had no landing (the engine's "stranded_aircraft_lost"
alarm), or at its end. Legal play should never do the middle two. Dice can also
break a plan, as when a reaction sinks a carrier while it sails; aircraft lost
at the end of that same Combat Movement are noted with the game, which plays on.
Failing positions are saved for inspection; replaying the seed reproduces the game.
Random play reaches far more unusual positions per second than search-driven
self-play, so run it after rules changes and before long self-play runs.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
from pathlib import Path
import random
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BIASES = (0.02, 0.05, 0.1)
# Casualty choices in Combat Movement's immediate naval battles, where a lost
# carrier is a combat outcome rather than a move that broke a landing plan.
CASUALTY_CHOICES = {"naval_take_casualty", "naval_casualty_accept", "naval_casualty_dispute"}
CLOCK = re.compile(r'"clock":(\{[^}]*\})')
STRANDED = re.compile(r'"stranded_aircraft_lost":(\d+)')


def turn_phase(serialized: str) -> tuple[int, int, str]:
    """The serialized clock's completed rounds, nation index and phase."""
    clock = json.loads(CLOCK.search(serialized).group(1))
    return clock["completed_rounds"], clock["nation_index"], clock["phase"]


def stranded(serialized: str) -> int:
    """Aircraft the engine has removed for want of a landing, its alarm count."""
    found = STRANDED.search(serialized)
    return int(found.group(1)) if found else 0


def play(seed: int, rounds: int, max_decisions: int, output: Path) -> dict:
    """Play one seeded random game, saving the position of any failure."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from studies.campaign.curriculum import make_env
    started = time.perf_counter()
    bias = BIASES[seed % len(BIASES)]
    env = make_env(seed, calendar_rounds=rounds)
    rng = random.Random(f"fuzz:{seed}")
    decisions, problem, notes = 0, None, []
    broken_by_dice = None  # The Combat Movement in which dice last broke the landing plan.
    while not env.is_terminal() and decisions < max_decisions:
        if env.decision_kind() == "chance":
            planned = env.raw.landing_plan_reachable()
            env.resolve_chance()
            if planned and not env.raw.landing_plan_reachable():
                # Chance never moves the clock, so reading it only after a broken
                # plan gives the phase the dice fell in.
                rolled = turn_phase(env.raw.serialize())
                if rolled[2] == "combat_movement":
                    broken_by_dice = rolled
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
        moment = turn_phase(before)
        movement = moment[2] == "combat_movement" and choice not in ending
        planned = movement and env.raw.landing_plan_reachable()
        try:
            env.apply_action(choice)
        except (RuntimeError, ValueError) as error:
            problem = {"kind": "engine_error", "error": str(error), "action": choice.id}
            (output / f"error-{seed}.json").write_text(json.dumps({"seed": seed, **problem, "state": before}) + "\n")
            break
        decisions += 1
        if planned and not env.raw.landing_plan_reachable():
            if choice.raw["kind"] in CASUALTY_CHOICES:
                broken_by_dice = moment
            else:
                problem = {"kind": "landing_plan_broken", "action": choice.id}
                (output / f"broken-{seed}.json").write_text(json.dumps({"seed": seed, **problem, "state": before}) + "\n")
                break
        lost = stranded(env.raw.serialize()) - stranded(before) if choice in ending else 0
        if lost and moment == broken_by_dice:
            notes.append({"kind": "stranded_after_dice", "action": choice.id, "aircraft_lost": lost,
                          "completed_rounds": moment[0], "nation_index": moment[1], "decisions": decisions})
        elif lost:
            problem = {"kind": "stranded_aircraft_lost", "action": choice.id}
            (output / f"stranded-{seed}.json").write_text(json.dumps({"seed": seed, **problem, "state": before}) + "\n")
            break
    clock = json.loads(env.raw.serialize())["state"]["clock"]
    return {"seed": seed, "bias": bias, "decisions": decisions, "terminal": env.is_terminal(),
            "completed_rounds": clock["completed_rounds"], "problem": problem, "notes": notes,
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
    noted = [result for result in results if result["notes"]]
    # Notes are dice outcomes, not engine defects, so they do not fail the run.
    print(json.dumps({"games": len(results), "completed": sum(result["terminal"] for result in results),
                      "problems": len(failed), "seeds": sorted(result["seed"] for result in failed),
                      "notes": sum(len(result["notes"]) for result in noted),
                      "noted_seeds": sorted(result["seed"] for result in noted)}))
    return 1 if failed else 0


def _play(task):
    return play(*task)


if __name__ == "__main__":
    raise SystemExit(main())
