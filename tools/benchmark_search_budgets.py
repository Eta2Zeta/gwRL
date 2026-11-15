#!/usr/bin/env python3
"""Game-process CPU and memory of one search, by simulation budget, without a network.

ROOT is a checkout of this repository with its extension built.

Searches decisions from two scripted eleven-round games with the training's
search (VectorMCTS, depth 16, root noise, no tree reuse). The evaluator builds
each evaluated position's zone input, as a game thread does before it asks the
coordinator, and returns uniform priors and zero values, so the time is the
engine's, the search's and the encoder's, not the network's. Memory is the
growth of the process's resident size while the first --keep trees are alive,
per node; run one budget per process so no freed tree's memory is reused.

    ./.venv/bin/python tools/benchmark_search_budgets.py . OUT.json --simulations 256

Run with MallocNanoZone unset, as training runs do. Measured in
docs/archive/records/network_and_search_cost_2026_11_14.md.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("root")
parser.add_argument("out")
parser.add_argument("--simulations", type=int, nargs="+", default=[64, 256, 1024])
parser.add_argument("--stride", type=int, default=40)
parser.add_argument("--keep", type=int, default=8)
args = parser.parse_args()
sys.path.insert(0, args.root)

from studies.campaign.baselines import baseline_distribution  # noqa: E402
from studies.campaign.curriculum import make_env  # noqa: E402
from studies.campaign.features import make_zone_input  # noqa: E402
from studies.shared.multiplayer_mcts import Evaluation, MctsConfig, VectorMCTS  # noqa: E402


class EncodingEvaluator:
    version = "bench-encoding-uniform"

    def __init__(self):
        self.calls = 0

    def evaluate(self, env, actions):
        make_zone_input(env, actions)
        self.calls += 1
        return Evaluation([1.0] * len(actions), (0.0, 0.0, 0.0))


def rss():
    if sys.platform == "win32":  # No ps there; the working set is Windows' resident size.
        from tools.windows_process_tree import working_set
        return working_set(os.getpid())
    return int(subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True,
                              text=True).stdout) * 1024


def positions():
    found, decisions, single = [], 0, 0
    for seed in (3101, 3102):
        env = make_env(seed, calendar_rounds=11)
        step = 0
        while not env.is_terminal():
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            actions = list(env.legal_actions())
            decisions += 1
            single += len(actions) == 1
            step += 1
            if step % args.stride == 0 and len(actions) > 1:
                found.append(env.clone())
            weights = baseline_distribution(env, actions)
            env.apply_action(actions[max(range(len(actions)), key=weights.__getitem__)])
    return found, decisions, single


began = time.perf_counter()
found, decisions, single = positions()
report = {"positions": len(found), "scripted_decisions": decisions, "single_option_decisions": single,
          "budgets": {}}
for simulations in args.simulations:
    # Memory first, in a process that has not yet freed any tree: keep the first
    # trees alive and divide the growth of the resident size by their nodes.
    kept, kept_nodes, before = [], 0, rss()
    for index, env in enumerate(found[:args.keep]):
        game = env.clone()
        search = VectorMCTS(EncodingEvaluator(), MctsConfig(simulations=simulations, max_depth=16, seed=index + 1))
        search.search(game, add_root_noise=True, reuse_root=False)
        kept.append((search, game))
        kept_nodes += len(search.nodes)
    grown = rss() - before
    del kept
    cpu_ms, nodes, evaluations = [], [], []
    for index, env in enumerate(found):
        game = env.clone()
        evaluator = EncodingEvaluator()
        search = VectorMCTS(evaluator, MctsConfig(simulations=simulations, max_depth=16, seed=index + 1))
        t0 = time.process_time()
        search.search(game, add_root_noise=True, reuse_root=False)
        cpu_ms.append((time.process_time() - t0) * 1000)
        nodes.append(len(search.nodes))
        evaluations.append(evaluator.calls)
        del search, game
    report["budgets"][str(simulations)] = {
        "cpu_ms_per_search": {"median": round(statistics.median(cpu_ms), 1), "mean": round(statistics.fmean(cpu_ms), 1)},
        "cpu_ms_per_simulation_mean": round(statistics.fmean(cpu_ms) / simulations, 3),
        "evaluations_per_search_mean": round(statistics.fmean(evaluations), 1),
        "tree_nodes_mean": round(statistics.fmean(nodes), 1),
        "memory_trees_kept": args.keep, "memory_nodes_kept": kept_nodes, "memory_bytes_grown": grown,
        "memory_bytes_per_node": int(grown / max(1, kept_nodes)),
    }
    print(simulations, report["budgets"][str(simulations)], flush=True)
report["seconds"] = round(time.perf_counter() - began, 1)
Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
