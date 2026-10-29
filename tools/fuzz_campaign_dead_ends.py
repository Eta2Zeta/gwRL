#!/usr/bin/env python3
"""Find campaign dead ends and engine errors with seeded random games.

Each game plays the campaign through the environment that search uses, choosing
uniformly among legal actions and ending a phase with extra probability (2%, 5%
or 10% by seed) so games reach later rounds. A game stops at a nonterminal
decision with no legal action, at an engine error, at its end or decision cap,
or when the landing rule fails. That rule counts the airborne aircraft that no
reachable joint landing plan lands (the engine's landing shortfall): no move in
either movement phase may raise it, and ending Combat Movement may lose only
that many aircraft (the "stranded_aircraft_lost" count). The shortfall is
compared between settled positions, with no naval move or Chinese-truce battle
pending. Dice may raise it, as when a reaction sinks a carrier while it sails,
by at most the seats of the carriers they sink or damage; so may a declaration
of war, which the engine does not check. Such rises are noted with the game,
which plays on, and so is every aircraft lost as Combat Movement ends. Failing
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
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BIASES = (0.02, 0.05, 0.1)
# Seats per carrier type; damage lowers a carrier's movement, not its seats.
CARRIERS = {"light_carrier": 1, "fleet_carrier": 2, "heavy_fleet_carrier": 3}
MOVEMENT_PHASES = {"combat_movement", "non_combat_movement"}
CLOCK = re.compile(r'"clock":(\{[^}]*\})')
STRANDED = re.compile(r'"stranded_aircraft_lost":(\d+)')
UNDER_WAY = re.compile(r'"immediate_(?:land|naval)_battles":[1-9]')


def turn_phase(serialized: str) -> tuple[int, int, str]:
    """The serialized clock's completed rounds, nation index and phase."""
    clock = json.loads(CLOCK.search(serialized).group(1))
    return clock["completed_rounds"], clock["nation_index"], clock["phase"]


def stranded(serialized: str) -> int:
    """Aircraft the engine has removed for want of a landing, its alarm count."""
    found = STRANDED.search(serialized)
    return int(found.group(1)) if found else 0


def explained_rise(before: str, after: str) -> dict:
    """What between two positions can raise the landing shortfall without an engine
    defect: carriers lost or damaged, with the seats they held, and new wars."""
    old, new = json.loads(before)["state"], json.loads(after)["state"]
    carriers = {key: unit for key, unit in old["units"].items() if unit["type"] in CARRIERS}
    hit = sorted(key for key, unit in carriers.items()
                 if key not in new["units"] or new["units"][key]["damage"] > unit["damage"])
    wars = sorted(f"{key}:{enemy}" for key, nation in new["nations"].items()
                  for enemy in nation["at_war_with"] if enemy not in old["nations"][key]["at_war_with"])
    return {"carriers": hit, "seats": sum(CARRIERS[carriers[key]["type"]] for key in hit), "wars": wars}


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
    settled = None  # (moment, landing shortfall, serialized state) at the last settled movement position.
    span: list[str] = []  # Actions since then.
    current = None  # The serialized present position, kept until the next change.

    def check_settled(action: str) -> dict | None:
        """Compares the landing shortfall with the last settled position of this phase,
        saving the earlier position of a rise that neither dice nor a war explains."""
        nonlocal settled, span, current
        current = text = env.raw.serialize()
        span.append(action)
        moment = turn_phase(text)
        if moment[2] not in MOVEMENT_PHASES or UNDER_WAY.search(text):
            return None
        shortfall = env.raw.landing_shortfall()
        previous, settled, actions, span = settled, (moment, shortfall, text), span, []
        if previous is None or previous[0] != moment or shortfall <= previous[1]:
            return None
        cause = explained_rise(previous[2], text)
        if cause["wars"] or shortfall - previous[1] <= cause["seats"]:
            notes.append({"kind": "landing_shortfall_after_war" if cause["wars"] else "landing_shortfall_after_dice",
                          "actions": actions, **cause, "shortfall": [previous[1], shortfall],
                          "completed_rounds": moment[0], "nation_index": moment[1], "decisions": decisions})
            return None
        broken = {"kind": "landing_plan_broken", "actions": actions, "shortfall": [previous[1], shortfall]}
        (output / f"broken-{seed}.json").write_text(json.dumps({"seed": seed, **broken, "state": previous[2]}) + "\n")
        return broken

    while not env.is_terminal() and decisions < max_decisions and problem is None:
        if env.decision_kind() == "chance":
            env.resolve_chance()
            problem = check_settled("chance")
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
        before = current if current is not None else env.raw.serialize()
        moment = turn_phase(before)
        # Ending Combat Movement may lose only the aircraft that no plan lands.
        allowed = env.raw.landing_shortfall() if choice in ending and moment[2] == "combat_movement" else 0
        try:
            env.apply_action(choice)
        except (RuntimeError, ValueError) as error:
            problem = {"kind": "engine_error", "error": str(error), "action": choice.id}
            (output / f"error-{seed}.json").write_text(json.dumps({"seed": seed, **problem, "state": before}) + "\n")
            break
        decisions += 1
        # After an ending, this sets the new phase's first settled position.
        problem = check_settled(choice.id)
        lost = stranded(current) - stranded(before) if choice in ending else 0
        if lost > allowed:
            problem = {"kind": "stranded_aircraft_lost", "action": choice.id, "aircraft_lost": lost,
                       "shortfall": allowed}
            (output / f"stranded-{seed}.json").write_text(json.dumps({"seed": seed, **problem, "state": before}) + "\n")
        elif lost:
            notes.append({"kind": "aircraft_lost_without_landing", "action": choice.id, "aircraft_lost": lost,
                          "completed_rounds": moment[0], "nation_index": moment[1], "decisions": decisions})
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
    # Notes record dice, wars or another nation's turn, not engine defects, so they do not fail the run.
    print(json.dumps({"games": len(results), "completed": sum(result["terminal"] for result in results),
                      "problems": len(failed), "seeds": sorted(result["seed"] for result in failed),
                      "notes": sum(len(result["notes"]) for result in noted),
                      "noted_seeds": sorted(result["seed"] for result in noted)}))
    return 1 if failed else 0


def _play(task):
    return play(*task)


if __name__ == "__main__":
    raise SystemExit(main())
