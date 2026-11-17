#!/usr/bin/env python3
"""Check that two builds of the engine play the same, and measure what each costs.

A speed change to the engine must leave every legal move and every position the
same. This plays the same seeded games on a checkout, each in its own process,
and records them, so that two checkouts' records can be compared:

  random   Random eleven-round games through the environment the search uses.
           Each move is drawn with random.Random("trace:<seed>"), and ending the
           phase is chosen with a probability of 2%, 5% or 10% by seed. Every
           step adds the legal moves, the chosen move and the position reached,
           by its canonical key, to a running digest. Each engine call's thread
           CPU time is measured, and on macOS the instructions the process ran
           during it (tools/log_process_load.py).
  search   Complete games searched as in training (64 simulations, depth 16),
           with networks whose first-layer tables hold random numbers
           (tools/replay_coordinator_rounds.py --make-weights), evaluated one
           position at a time on one thread, so that a game plays the same on
           every run. Every event's kind and move go into the digest, and the
           final position's canonical key is kept; the process's instructions
           and CPU time are measured.
  compare  Whether two records hold the same games, step by step, and what each
           cost.

ROOT is a checkout with its extension built, such as a copy of an older commit
made with `git archive`. Run random games with the project environment and
searched games with the training environment, which has PyTorch:

    .venv/bin/python tools/compare_engine_builds.py random ROOT OUT.jsonl --seeds 7000-7299
    tmp/gpu-mps-env/bin/python tools/compare_engine_builds.py search ROOT OUT.jsonl --weights W.pt --seeds 41-44
    .venv/bin/python tools/compare_engine_builds.py compare OLD.jsonl NEW.jsonl
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

BIASES = (0.02, 0.05, 0.1)
CALLS = ("legal_actions", "apply_action", "resolve_chance")


def _instruction_reader(root: str):
    """A function giving this process's instructions so far, or None off macOS."""
    if sys.platform != "darwin":
        return None
    sys.path.insert(1, os.path.join(root, "tools"))
    sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
    from log_process_load import reader
    read, pid = reader(), os.getpid()
    return lambda: read(pid)["instructions"]


def position_key(env) -> str:
    """A position's identity that every build gives the same position: the digest
    of its canonical text. Builds older than the canonical key had their planning
    key computed that way, so it serves for them."""
    raw = getattr(env, "raw", env)
    canonical = getattr(raw, "canonical_key", None)
    return canonical() if canonical is not None else raw.planning_key()


def play_random(task: tuple[str, int, int]) -> dict:
    root, seed, rounds = task
    sys.path.insert(0, root)
    from studies.campaign.curriculum import make_env
    instructions = _instruction_reader(root)
    clock = time.thread_time_ns
    env = make_env(seed, calendar_rounds=rounds)
    rng, bias = random.Random(f"trace:{seed}"), BIASES[seed % len(BIASES)]
    digests, rolling = [], hashlib.sha256()
    cost = {name: {"calls": 0, "cpu_ns": 0, "instructions": 0} for name in CALLS}

    def timed(name, call, *args):
        started, counted = clock(), instructions() if instructions else 0
        result = call(*args)
        entry = cost[name]
        entry["instructions"] += (instructions() - counted) if instructions else 0
        entry["cpu_ns"] += clock() - started
        entry["calls"] += 1
        return result

    error = None
    while not env.is_terminal():
        if env.decision_kind() == "chance":
            timed("resolve_chance", env.resolve_chance)
            rolling.update(b"chance|" + position_key(env).encode())
        else:
            options = list(timed("legal_actions", env.legal_actions))
            if not options:
                error = "no legal action"
                break
            ending = [action for action in options if action.id.endswith(":play:end_phase")]
            choice = ending[0] if ending and rng.random() < bias else rng.choice(options)
            rolling.update(("|".join(action.id for action in options) + "#" + choice.id).encode())
            try:
                timed("apply_action", env.apply_action, choice)
            except (RuntimeError, ValueError) as caught:
                error = f"{type(caught).__name__}: {caught}"
                break
            rolling.update(b"|" + position_key(env).encode())
        digests.append(rolling.hexdigest()[:16])
    return {"kind": "random", "seed": seed, "steps": len(digests), "terminal": env.is_terminal(), "error": error,
            "final": position_key(env), "digests": digests, "calls": cost}


def play_search(task: tuple[str, int, int, str]) -> dict:
    root, seed, rounds, weights = task
    sys.path.insert(0, root)
    sys.path.insert(1, os.path.join(root, "tools"))
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    from replay_coordinator_rounds import load_models
    from studies.campaign.curriculum import make_env
    from studies.campaign.learning import LearningConfig, play_episode
    from studies.campaign.neural import NeuralEvaluator
    instructions = _instruction_reader(root)
    evaluator = NeuralEvaluator(load_models(Path(weights)), "compare")
    config = LearningConfig(simulations=64, max_depth=16, seed=20261104, sample_fraction=0.05)
    env = make_env(seed, calendar_rounds=rounds)
    counted, started = instructions() if instructions else 0, time.process_time()
    with torch.inference_mode():
        result = play_episode(env, evaluator, config=config, rules_version="compare", batch_version="compare",
                              environment_seed=seed, max_transitions=100000)
    spent, cpu = (instructions() - counted) if instructions else 0, time.process_time() - started
    digests, rolling = [], hashlib.sha256()
    # The events' positions are planning keys, whose form a build may change, so
    # the digest takes each event's kind and move, and the final position by
    # its canonical key.
    for event in result["events"]:
        rolling.update(json.dumps([event.get("kind"), str(event.get("action"))]).encode())
        digests.append(rolling.hexdigest()[:16])
    return {"kind": "search", "seed": seed, "steps": len(digests), "decisions": result["counts"]["decisions"],
            "terminal": result["terminal"], "error": None, "final": position_key(env), "digests": digests,
            "process": {"cpu_seconds": cpu, "instructions": spent}}


def run(kind: str, args: argparse.Namespace) -> int:
    first, last = (int(part) for part in args.seeds.split("-"))
    root = str(Path(args.root).resolve())
    if kind == "random":
        tasks, play = [(root, seed, args.rounds) for seed in range(first, last + 1)], play_random
    else:
        tasks, play = [(root, seed, args.rounds, str(Path(args.weights).resolve()))
                       for seed in range(first, last + 1)], play_search
    started = time.time()
    with ProcessPoolExecutor(args.processes) as pool, open(args.output, "w") as out:
        for result in pool.map(play, tasks):
            out.write(json.dumps(result) + "\n")
            out.flush()
    print(f"{len(tasks)} {kind} games in {time.time() - started:.0f} s")
    return 0


def totals(rows: list[dict]) -> dict:
    if rows and rows[0]["kind"] == "random":
        out = {}
        for name in CALLS:
            calls = sum(row["calls"][name]["calls"] for row in rows)
            cpu = sum(row["calls"][name]["cpu_ns"] for row in rows)
            instructions = sum(row["calls"][name]["instructions"] for row in rows)
            out[name] = {"calls": calls, "cpu_seconds": round(cpu / 1e9, 1),
                         "microseconds_per_call": round(cpu / max(calls, 1) / 1e3),
                         "million_instructions_per_call": round(instructions / max(calls, 1) / 1e6, 2)}
        return out
    return {"cpu_seconds": round(sum(row["process"]["cpu_seconds"] for row in rows), 1),
            "billion_instructions": round(sum(row["process"]["instructions"] for row in rows) / 1e9)}


def compare(old_path: Path, new_path: Path) -> int:
    old = {row["seed"]: row for row in map(json.loads, old_path.read_text().splitlines())}
    new = {row["seed"]: row for row in map(json.loads, new_path.read_text().splitlines())}
    shared = sorted(set(old) & set(new))
    same = 0
    for seed in shared:
        a, b = old[seed], new[seed]
        if a["digests"] == b["digests"] and a["final"] == b["final"] and a["error"] == b["error"]:
            same += 1
            continue
        differs = next((i for i, (x, y) in enumerate(zip(a["digests"], b["digests"])) if x != y),
                       min(len(a["digests"]), len(b["digests"])))
        print(f"seed {seed}: differs at step {differs} of {a['steps']} and {b['steps']}")
    steps = sum(old[seed]["steps"] for seed in shared)
    print(json.dumps({"games_compared": len(shared), "identical": same, "steps": steps,
                      "old": totals([old[seed] for seed in shared]),
                      "new": totals([new[seed] for seed in shared])}, indent=1))
    return 0 if same == len(shared) else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("random", "search"):
        command = commands.add_parser(name)
        command.add_argument("root", help="Checkout whose gwrl_cpp and studies are played")
        command.add_argument("output", help="New JSON-lines record")
        command.add_argument("--seeds", default="7000-7059" if name == "random" else "41-44")
        command.add_argument("--rounds", type=int, default=11)
        command.add_argument("--processes", type=int, default=4)
        if name == "search":
            command.add_argument("--weights", required=True, help="tools/replay_coordinator_rounds.py --make-weights")
    command = commands.add_parser("compare")
    command.add_argument("old", type=Path)
    command.add_argument("new", type=Path)
    args = parser.parse_args(argv)
    if args.command == "compare":
        return compare(args.old, args.new)
    return run(args.command, args)


if __name__ == "__main__":
    raise SystemExit(main())
