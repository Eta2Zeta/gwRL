#!/usr/bin/env python3
"""Record, check and time campaign move menus along seeded random games.

Speed-only changes to move generation must offer the same choices in the same
order. `record` plays seeded random games and stores a digest of every decision
position's complete menu, legal actions and interrupts, with the time taken to
generate it. `check` replays the same games and stops each one at its first
differing menu, saving that position for inspection. The games choose by menu
index, so identical menus replay identical games and the generation times of
the two builds compare like for like.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA = "campaign-move-menus-v1"
END_PHASE_BIAS = 0.05


def play(seed, rounds, max_decisions, expected=None, mismatch_path=None):
    """Play one seeded random game, digesting each decision position's raw menu."""
    from studies.campaign.curriculum import make_env
    env = make_env(seed, calendar_rounds=rounds)
    rng = random.Random(f"move-menus:{seed}")
    digests, sizes, kinds, seconds = [], [], Counter(), Counter()
    mismatch = error = None
    while not env.is_terminal() and len(digests) < max_decisions and error is None:
        if env.raw.decision_kind() == "chance":
            env.resolve_chance()
            continue
        started = time.perf_counter()
        actions, interrupts = env.raw.legal_actions(), env.raw.legal_interrupts()
        elapsed = time.perf_counter() - started
        text = "\n".join(action.describe() for action in actions) + "\0" + "\n".join(
            action.describe() for action in interrupts)
        digest = hashlib.sha256(text.encode()).hexdigest()[:16]
        kind = env.raw.decision_kind()
        kinds[kind] += 1
        seconds[kind] += elapsed
        if expected is not None and (len(digests) >= len(expected["digests"])
                                     or expected["digests"][len(digests)] != digest):
            mismatch = {"position": len(digests), "kind": kind, "actions": len(actions),
                        "interrupts": len(interrupts),
                        "expected_size": (expected["sizes"][len(digests)] if len(digests) < len(expected["sizes"])
                                          else None)}
            if mismatch_path is not None:
                mismatch_path.write_text(json.dumps({**mismatch, "seed": seed, "state": env.raw.serialize(),
                                                     "menu": text.split("\0")[0].split("\n")}) + "\n")
            break
        digests.append(digest)
        sizes.append([len(actions), len(interrupts)])
        # Ending phases a little more often than uniform choice carries
        # games into later rounds within the decision limit.
        options = env.legal_actions()
        ending = [action for action in options if action.id.endswith(":play:end_phase")]
        try:
            env.apply_action(ending[0] if ending and rng.random() < END_PHASE_BIAS else rng.choice(options))
        except RuntimeError as failure:
            # An offered action the engine then rejects is a rules defect. It
            # ends this game; a check requires the same failure at the same place.
            error = str(failure)
    clock = json.loads(env.raw.serialize())["state"]["clock"]
    return {"seed": seed, "decisions": len(digests), "terminal": env.is_terminal(),
            "completed_rounds": clock["completed_rounds"], "error": error,
            "menu_seconds": sum(seconds.values()), "by_kind": {kind: {"positions": kinds[kind],
                                                                      "seconds": seconds[kind]}
                                                               for kind in sorted(kinds)},
            "digests": digests, "sizes": sizes, "mismatch": mismatch}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("record", "check"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path, help="A recorded file; required for check")
    parser.add_argument("--seeds", default="1951,1952,1953")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--max-decisions", type=int, default=5000)
    args = parser.parse_args(argv)
    if args.mode == "check":
        if args.reference is None:
            parser.error("check needs --reference")
        reference = json.loads(args.reference.read_text())
        if reference.get("schema") != SCHEMA:
            parser.error("Unsupported reference file")
        settings = reference["settings"]
        expected = {game["seed"]: game for game in reference["games"]}
    else:
        settings = {"seeds": [int(seed) for seed in args.seeds.split(",")], "rounds": args.rounds,
                    "max_decisions": args.max_decisions}
        expected = {}
    games = []
    for seed in settings["seeds"]:
        game = play(seed, settings["rounds"], settings["max_decisions"], expected.get(seed),
                    args.output.with_name(f"{args.output.stem}.mismatch-{seed}.json") if expected else None)
        games.append(game)
        if expected and game["mismatch"] is None and game["decisions"] != expected[seed]["decisions"]:
            game["mismatch"] = {"position": game["decisions"], "kind": "game ended at a different length"}
        if expected and game["mismatch"] is None and game["error"] != expected[seed].get("error"):
            game["mismatch"] = {"position": game["decisions"], "kind": "different engine error",
                                "error": game["error"], "expected_error": expected[seed].get("error")}
        line = {"seed": seed, "decisions": game["decisions"], "completed_rounds": game["completed_rounds"],
                "terminal": game["terminal"], "menu_seconds": round(game["menu_seconds"], 2)}
        if game["error"]:
            line["error"] = game["error"]
        if expected:
            line.update(identical=game["mismatch"] is None,
                        reference_menu_seconds=round(expected[seed]["menu_seconds"], 2))
            if game["mismatch"]:
                line["mismatch"] = game["mismatch"]
        print(json.dumps(line), flush=True)
    report = {"schema": SCHEMA, "settings": settings, "games": games,
              "menu_seconds": sum(game["menu_seconds"] for game in games)}
    if expected:
        report["identical"] = all(game["mismatch"] is None for game in games)
        report["reference_menu_seconds"] = sum(expected[seed]["menu_seconds"] for seed in settings["seeds"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    summary = {"positions": sum(game["decisions"] for game in games), "menu_seconds": round(report["menu_seconds"], 2)}
    if expected:
        summary.update(identical=report["identical"], reference_menu_seconds=round(report["reference_menu_seconds"], 2))
    print(json.dumps(summary), flush=True)
    return 0 if report.get("identical", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
