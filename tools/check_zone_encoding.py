#!/usr/bin/env python3
"""Check the zone encoding on positions from complete games.

For every decision it encodes the position and its options, then checks that
  * positions with the same encoding offer the same options, compared by their
    encodings: otherwise the network cannot tell apart positions whose legal
    moves differ;
  * options of one position with the same encoding lead to positions with the
    same encoding: otherwise two different moves look alike.
It also reports names that fell into an "other" column, and the stored size
and build time of the zone input against the graph input it replaces.

Run from the repository root:

    ./.venv/bin/python tools/check_zone_encoding.py OUT.json --rounds 3 --seeds 1951 1952
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studies.campaign.baselines import baseline_distribution, raw_action  # noqa: E402
from studies.campaign.curriculum import make_env  # noqa: E402

import gwrl_cpp  # noqa: E402


def _digest(*parts) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(memoryview(part).cast("B") if hasattr(part, "tobytes") else repr(part).encode())
        h.update(b"|")
    return h.hexdigest()


def keys(zone) -> tuple[str, list[str]]:
    """The position's key and one key per option, from the encoding alone."""
    a = zone.arrays()
    state = _digest(a["zone_index"], a["zone_column"], a["zone_value"], a["global_column"], a["global_value"])
    options = []
    for i in range(zone.action_count):
        lo, hi = a["action_offsets"][i], a["action_offsets"][i + 1]
        plo, phi = a["path_offsets"][i], a["path_offsets"][i + 1]
        options.append(_digest(a["action_column"][lo:hi], a["action_value"][lo:hi],
                               a["action_source"][i:i + 1], a["action_target"][i:i + 1], a["path_zone"][plo:phi]))
    return state, options


def describe(action) -> str:
    raw = raw_action(action) or {}
    return f"{action.kind}:{raw.get('kind', '')}"


def successor_key(env, action) -> str:
    copy = env.clone()
    copy.apply_action(action)
    if copy.is_terminal():
        return "terminal"
    actions = () if copy.decision_kind() == "chance" else tuple(copy.legal_actions())
    state, options = keys(copy.zone_input(actions))
    return _digest(state, sorted(options))


def graph_input_bytes(env, actions) -> int:
    from studies.campaign.features import make_numeric_input
    item = make_numeric_input(env, tuple(actions), 16384)
    packed = item["packed_graph"]
    return packed["observation"].compacted().nbytes + sum(graph.nbytes for graph in packed["actions"])


def check(args) -> dict:
    gwrl_cpp.zone_encoding_unknowns(True)
    seen: dict[str, tuple[list[str], str]] = {}
    collisions, collision_examples = 0, []
    duplicate_groups = nonequivalent = 0
    nonequivalent_examples = []
    positions = chance_positions = 0
    zone_bytes, graph_bytes, zone_ms, graph_ms = [], [], [], []
    version = None
    for seed in args.seeds:
        env = make_env(seed, calendar_rounds=args.rounds)
        version = env.raw.zone_encoding_spec()["version"]
        rng = random.Random(seed * 7919 + 17)
        step = 0
        while not env.is_terminal():
            step += 1
            kind = env.decision_kind()
            actions = () if kind == "chance" else tuple(env.legal_actions())
            started = time.perf_counter()
            zone = env.zone_input(actions)
            zone_ms.append((time.perf_counter() - started) * 1000)
            if zone is None:
                raise RuntimeError("The environment produced no zone input")
            positions += 1
            chance_positions += kind == "chance"
            if step % args.size_stride == 0:
                zone_bytes.append(zone.nbytes)
                started = time.perf_counter()
                graph_bytes.append(graph_input_bytes(env, actions))
                graph_ms.append((time.perf_counter() - started) * 1000)
            state, options = keys(zone)
            menu = sorted(options)
            label = f"seed {seed} step {step} {kind}"
            if state in seen:
                if seen[state][0] != menu:
                    collisions += 1
                    if len(collision_examples) < args.examples:
                        first, where = seen[state]
                        collision_examples.append({"first": where, "second": label,
                                                   "only_first": len(Counter(first) - Counter(menu)),
                                                   "only_second": len(Counter(menu) - Counter(first)),
                                                   "kinds_second": sorted({describe(a) for a in actions})[:6]})
            else:
                seen[state] = (menu, label)
            if kind != "chance" and step % args.successor_stride == 0:
                groups = defaultdict(list)
                for index, key in enumerate(options):
                    groups[key].append(index)
                checked = 0
                for members in groups.values():
                    if len(members) < 2 or checked >= args.groups_per_position:
                        continue
                    checked += 1
                    duplicate_groups += 1
                    first, second = (actions[members[0]], actions[members[1]])
                    if successor_key(env, first) != successor_key(env, second):
                        nonequivalent += 1
                        if len(nonequivalent_examples) < args.examples:
                            nonequivalent_examples.append({
                                "where": label, "options": [describe(first), describe(second)],
                                "first": str((raw_action(first) or {}).get("parameters"))[:300],
                                "second": str((raw_action(second) or {}).get("parameters"))[:300]})
            if kind == "chance":
                env.resolve_chance()
                continue
            if args.policy == "balanced":
                weights = baseline_distribution(env, list(actions))
                choice = max(range(len(actions)), key=lambda i: weights[i])
            else:
                choice = rng.randrange(len(actions))
            env.apply_action(actions[choice])
        print(json.dumps({"seed": seed, "positions": positions, "collisions": collisions,
                          "nonequivalent": nonequivalent}), file=sys.stderr, flush=True)

    def summary(values):
        if not values:
            return None
        ordered = sorted(values)
        return {"median": round(statistics.median(ordered), 3), "mean": round(statistics.fmean(ordered), 3),
                "max": round(ordered[-1], 3), "count": len(ordered)}

    unknowns = gwrl_cpp.zone_encoding_unknowns(True)
    return {
        "encoding_version": version,
        "seeds": args.seeds, "rounds": args.rounds, "policy": args.policy,
        "size_stride": args.size_stride, "successor_stride": args.successor_stride,
        "groups_per_position": args.groups_per_position,
        "positions": positions, "chance_positions": chance_positions, "distinct_encodings": len(seen),
        "positions_whose_encoding_matched_an_earlier_one_with_different_options": collisions,
        "collision_examples": collision_examples,
        "identical_option_groups_checked": duplicate_groups,
        "identical_options_with_different_successors": nonequivalent,
        "nonequivalent_examples": nonequivalent_examples,
        "names_in_other_columns": dict(sorted(unknowns.items(), key=lambda item: -item[1])),
        "zone_input_bytes": summary(zone_bytes), "graph_input_bytes": summary(graph_bytes),
        "zone_input_ms": summary(zone_ms), "graph_input_ms": summary(graph_ms),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1951])
    parser.add_argument("--policy", choices=("uniform", "balanced"), default="uniform")
    parser.add_argument("--size-stride", type=int, default=10, help="compare sizes at every n-th position")
    parser.add_argument("--successor-stride", type=int, default=5, help="check identical options at every n-th position")
    parser.add_argument("--groups-per-position", type=int, default=2)
    parser.add_argument("--examples", type=int, default=8)
    args = parser.parse_args()
    result = check(args)
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("examples") and k != "names_in_other_columns"}, indent=1))


if __name__ == "__main__":
    main()
