"""Decision census for the regional campaign's training action interface.

Plays complete curriculum games with versioned scripted or uniform-random policies and
records every policy decision. It measures where decisions and legal options come from,
estimates which decisions proposed interface/rule changes would remove, compares an
attacking and a passive Japan under the terminal wealth-gap objective, and times
searches and their evaluations. It never edits engine state, dice or rules.

Run from the repository root:

    ./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 3 --seeds 1951
    ./.venv/bin/python tools/decision_census.py savings OUT.jsonl
    ./.venv/bin/python tools/decision_census.py symmetry --policy uniform --rounds 3 --seeds 1951 1952
    ./.venv/bin/python tools/decision_census.py incentive --rounds 3 --seeds 1951 1952 1953 1954
    ./.venv/bin/python tools/decision_census.py search OUT.jsonl --seed 1953 --simulations 64
    ./.venv/bin/python tools/decision_census.py export POSITIONS_DIR --seed 1952
    ./.venv/bin/python tools/decision_census.py targets --simulations 16 64

Exported positions feed tools/profile_campaign_menu_layers.cpp.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studies.campaign.baselines import baseline_distribution, raw_action  # noqa: E402
from studies.campaign.curriculum import make_env  # noqa: E402

# Decisions a proposal would no longer ask a policy to make. "P" proposals keep every
# legal outcome (interface changes); "R" proposals change the rules and need approval.
EXACT = ("P1_single_option", "P2_battle_bookkeeping", "P3_one_step_single_ship_orders",
         "P4_purchase_quantity", "P5_batch_placement", "P6_mission_complete_flights")
RULE = ("R1_automatic_casualties", "R2_automatic_retreat", "R3_static_warships")
UNIT_KEYS = ("unit", "transport", "cargo", "partner", "towed", "carrier", "ship")


def scripted_index(env, actions) -> int:
    probabilities = baseline_distribution(env, actions)
    return max(range(len(actions)), key=lambda i: probabilities[i])


def census(args: argparse.Namespace) -> None:
    summaries = []
    with open(args.out, "w") as out:
        for seed in args.seeds:
            env = make_env(seed, calendar_rounds=args.rounds)
            rng = random.Random(seed * 7919 + 17)
            decisions = chance = 0
            menu_s = apply_s = 0.0
            start = time.perf_counter()
            while not env.is_terminal():
                kind = env.decision_kind()
                if kind == "chance":
                    env.resolve_chance()
                    chance += 1
                    continue
                owner = env.current_decision_player()
                t0 = time.perf_counter()
                actions = env.legal_actions()
                t1 = time.perf_counter()
                index = scripted_index(env, actions) if args.policy == "balanced" else rng.randrange(len(actions))
                chosen = raw_action(actions[index])
                record = {"seed": seed, "i": decisions, "owner": owner, "adapter_kind": kind,
                          "nation": env.raw.current_nation(), "menu": len(actions),
                          "menu_kinds": dict(Counter(raw_action(a)["kind"] for a in actions)),
                          "chosen_kind": chosen.get("kind"), "params": chosen.get("parameters")}
                t2 = time.perf_counter()
                env.apply_action(actions[index])
                t3 = time.perf_counter()
                record["t_menu_ms"] = round((t1 - t0) * 1000, 3)
                record["t_apply_ms"] = round((t3 - t2) * 1000, 3)
                out.write(json.dumps(record, sort_keys=True) + "\n")
                menu_s += t1 - t0
                apply_s += t3 - t2
                decisions += 1
            summaries.append({"seed": seed, "rounds": args.rounds, "policy": args.policy, "decisions": decisions,
                              "chance_events": chance, "terminal": env.is_terminal(),
                              "returns": [round(x, 2) for x in env.returns()],
                              "wall_s": round(time.perf_counter() - start, 2),
                              "menu_s": round(menu_s, 2), "apply_s": round(apply_s, 2)})
            print(json.dumps(summaries[-1]), flush=True)
    with open(args.out + ".summary.json", "w") as handle:
        json.dump(summaries, handle, indent=1, sort_keys=True)


def place_key(parameters: dict) -> tuple:
    project = re.sub(r"_[0-9]+$", "", str(parameters.get("project", "")))
    return project, parameters.get("facility") or parameters.get("zone"), parameters.get("in_port")


def removal_marks(rows: list[dict]) -> dict[int, set[str]]:
    marks: dict[int, set[str]] = defaultdict(set)
    for index, row in enumerate(rows):
        kinds, chosen = set(row["menu_kinds"]), row["chosen_kind"]
        parameters = row.get("params") or {}
        previous = rows[index - 1] if index and rows[index - 1]["seed"] == row["seed"] else None
        before = (previous or {}).get("params") or {}
        if row["menu"] == 1:
            marks[index].add("P1_single_option")
        if chosen == "land_progress_battle" and kinds <= {"land_progress_battle"}:
            marks[index].add("P2_battle_bookkeeping")
        if chosen == "land_begin_battle" and kinds <= {"land_begin_battle"} and row["menu"] == 1:
            marks[index].add("P2_battle_bookkeeping")
        if chosen == "naval_route" and previous is not None and previous["chosen_kind"] == "naval_start_move":
            marks[index - 1].add("P3_one_step_single_ship_orders")
        if (chosen == "economy_purchase" and previous is not None and previous["chosen_kind"] == "economy_purchase"
                and before.get("row") == parameters.get("row")):
            marks[index].add("P4_purchase_quantity")
        if (chosen == "economy_place" and previous is not None and previous["chosen_kind"] == "economy_place"
                and place_key(before) == place_key(parameters)):
            marks[index].add("P5_batch_placement")
        if chosen == "air_fly":
            marks[index].add("P6_mission_complete_flights")
        if row["adapter_kind"] in {"land_casualty", "naval_shore_casualty", "air_casualty", "naval_casualty"}:
            marks[index].add("R1_automatic_casualties")
        if row["adapter_kind"] in {"land_retreat_or_continue", "land_retreat_destination"}:
            marks[index].add("R2_automatic_retreat")
        transport = "transport" in str(parameters.get("unit", ""))
        if chosen in {"naval_start_move", "naval_force_add"} and not transport:
            marks[index].add("R3_static_warships")
        if (chosen == "naval_route" and previous is not None
                and previous["chosen_kind"] in {"naval_start_move", "naval_force_add"}
                and "transport" not in str(before.get("unit", ""))):
            marks[index].add("R3_static_warships")
        if chosen in {"naval_enter_port", "naval_designate_raider", "naval_remove_raider"}:
            marks[index].add("R3_static_warships")
    return marks


def savings(args: argparse.Namespace) -> None:
    rows = []
    for path in args.logs:
        with open(path) as handle:
            rows.extend(json.loads(line) for line in handle)
    rows.sort(key=lambda r: (r["seed"], r["i"]))
    marks = removal_marks(rows)
    total, games = len(rows), len({r["seed"] for r in rows})
    result = {"games": games, "decisions": total, "forced_single_option": sum(r["menu"] == 1 for r in rows),
              "two_options": sum(r["menu"] == 2 for r in rows), "by_owner": dict(Counter(r["owner"] for r in rows)),
              "proposals": {name: sum(name in m for m in marks.values()) for name in EXACT + RULE},
              "union_exact": sum(bool(m & set(EXACT)) for m in marks.values()),
              "union_exact_and_rule": sum(bool(m) for m in marks.values())}
    # Searches already skip single-option roots, so report what the other proposals
    # remove from the decisions that are still searched.
    searched = [index for index, row in enumerate(rows) if row["menu"] > 1]
    later = set(EXACT) - {"P1_single_option"}
    result["searched_decisions"] = len(searched)
    result["searched_removed_by_P2_to_P6"] = sum(bool(marks.get(i, set()) & later) for i in searched)
    result["searched_removed_by_P2_to_P6_or_rules"] = sum(bool(marks.get(i, set()) - {"P1_single_option"})
                                                          for i in searched)
    result["searched_with_at_least_64_options"] = sum(rows[i]["menu"] >= 64 for i in searched)
    result["decisions_with_at_least_16_options"] = sum(row["menu"] >= 16 for row in rows)
    result["decisions_with_at_least_64_options"] = sum(row["menu"] >= 64 for row in rows)
    groups = defaultdict(list)
    for row in rows:
        groups[f"{row['owner']}|{row['adapter_kind']}"].append(row)
    result["by_owner_kind"] = {key: {"decisions": len(items), "menu_mean": round(statistics.mean(i["menu"] for i in items), 1),
                                     "menu_max": max(i["menu"] for i in items),
                                     "menu_ms_mean": round(statistics.mean(i["t_menu_ms"] for i in items), 2)}
                               for key, items in sorted(groups.items(), key=lambda kv: -len(kv[1]))}
    options = Counter()
    for row in rows:
        options.update(row["menu_kinds"])
    result["menu_options_by_kind"] = dict(options.most_common())
    result["chosen_by_kind"] = dict(Counter(r["chosen_kind"] for r in rows).most_common())
    print(json.dumps(result, indent=1))


def signature(units: dict, uid: str) -> str:
    unit = units.get(uid)
    if unit is None:
        return uid
    fields = {key: value for key, value in unit.items() if key not in ("id", "cargo")}
    fields["cargo"] = sorted(units[c]["type"] if c in units else c for c in unit.get("cargo", []))
    return json.dumps(fields, sort_keys=True)


def canonical_option(raw: dict, units: dict, drop_path: bool) -> str:
    parameters = dict(raw.get("parameters") or {})
    for key in UNIT_KEYS:
        if isinstance(parameters.get(key), str) and parameters[key] in units:
            parameters[key] = signature(units, parameters[key])
    if isinstance(parameters.get("units"), list):
        parameters["units"] = sorted(signature(units, x) if isinstance(x, str) else json.dumps(x)
                                     for x in parameters["units"])
    if drop_path and isinstance(parameters.get("path"), list) and parameters["path"]:
        path = parameters["path"]
        parameters["path"] = [path[0], len(path), path[-1]]
    return json.dumps({"kind": raw.get("kind"), "nation": raw.get("nation"), "p": parameters}, sort_keys=True)


def symmetry(args: argparse.Namespace) -> None:
    totals, by_kind = Counter(), defaultdict(Counter)
    for seed in args.seeds:
        env = make_env(seed, calendar_rounds=args.rounds)
        rng = random.Random(seed * 7919 + 17)
        while not env.is_terminal():
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            actions = env.legal_actions()
            units = env.raw.observation()["state"]["units"]
            raws = [raw_action(a) for a in actions]
            for label, drop in (("interchangeable_units", False), ("plus_same_destination", True)):
                distinct = {canonical_option(r, units, drop) for r in raws}
                totals[label] += len(distinct)
                for item in distinct:
                    by_kind[json.loads(item)["kind"]][label] += 1
            totals["options"] += len(raws)
            totals["decisions"] += 1
            for r in raws:
                by_kind[r["kind"]]["options"] += 1
            index = scripted_index(env, actions) if args.policy == "balanced" else rng.randrange(len(actions))
            env.apply_action(actions[index])
    print(json.dumps({"totals": dict(totals), "by_kind": {k: dict(v) for k, v in
                      sorted(by_kind.items(), key=lambda kv: -kv[1]["options"])}}, indent=1))


def incentive(args: argparse.Namespace) -> None:
    for seed in args.seeds:
        for passive in (False, True):
            env = make_env(seed, calendar_rounds=args.rounds)
            decisions = 0
            first_combat = None
            while not env.is_terminal():
                kind = env.decision_kind()
                if kind == "chance":
                    env.resolve_chance()
                    continue
                actions = env.legal_actions()
                owner = env.current_decision_player()
                kinds = [raw_action(a)["kind"] for a in actions]
                if passive and owner == "axis" and kind == "combat_movement" and "end_phase" in kinds:
                    index = kinds.index("end_phase")
                elif passive and owner == "axis" and kind == "declaration_offer":
                    index = next(i for i, a in enumerate(actions) if a.kind == "pass_interrupt")
                else:
                    index = scripted_index(env, actions)
                closing = (first_combat is None and owner == "axis" and kind == "combat"
                           and kinds[index] == "end_phase")
                before = env.wealth() if closing else None
                env.apply_action(actions[index])
                decisions += 1
                if closing:
                    # Warlord alignment and truce offers resolve when Japan's combat phase closes.
                    after = env.wealth()
                    first_combat = {"before": {k: round(v["wealth"], 2) for k, v in before.items()},
                                    "after": {k: round(v["wealth"], 2) for k, v in after.items()}}
            wealth = env.wealth()
            print(json.dumps({"seed": seed, "rounds": args.rounds, "axis_policy": "passive" if passive else "attack",
                              "returns": [round(x, 2) for x in env.returns()], "decisions": decisions,
                              "wealth": {k: {c: round(v[c], 2) for c in ("income_rate", "units", "infrastructure",
                                                                         "treasury", "wealth")}
                                         for k, v in wealth.items()},
                              "first_japan_combat_phase_close": first_combat}, sort_keys=True), flush=True)


def export(args: argparse.Namespace) -> None:
    """Save serialized engines at Japan's first movement decisions of each round (uniform play)."""
    env = make_env(args.seed, calendar_rounds=args.rounds)
    rng = random.Random(args.seed * 7919 + 17)
    Path(args.directory).mkdir(parents=True, exist_ok=True)
    saved = set()
    while not env.is_terminal():
        kind = env.decision_kind()
        if kind == "chance":
            env.resolve_chance()
            continue
        if env.current_decision_player() == "axis" and kind in {"combat_movement", "non_combat_movement"}:
            clock = env.raw.observation()["state"]["clock"]
            label = f"r{clock['round_index']}_{env.raw.current_nation()}_{kind}"
            if label not in saved:
                saved.add(label)
                (Path(args.directory) / f"{label}.json").write_text(env.raw.serialize())
                print(label, "options", len(env.legal_actions()), "history", env.raw.history_size())
        actions = env.legal_actions()
        env.apply_action(actions[rng.randrange(len(actions))])


def targets(args: argparse.Namespace) -> None:
    """Visit distribution of a root search at Japan's first combat-movement decision.

    The evaluator returns deterministic pseudo-random values and peaked priors per state,
    a stand-in for a trained network whose values differ between positions.
    """
    import hashlib

    from studies.shared.multiplayer_mcts import Evaluation, MctsConfig, VectorMCTS

    class HashedEvaluator:
        version = "census-hashed-values-v1"

        def evaluate(self, env, actions):
            r = random.Random(int(hashlib.sha256(env.planning_key().encode()).hexdigest()[:16], 16))
            values = [r.uniform(-50, 50) for _ in range(3)]
            return Evaluation([r.random() ** 2 for _ in actions], values)

    env = make_env(args.seed, calendar_rounds=args.rounds)
    while not (env.current_decision_player() == "axis" and env.decision_kind() == "combat_movement"):
        if env.decision_kind() == "chance":
            env.resolve_chance()
            continue
        actions = env.legal_actions()
        env.apply_action(actions[scripted_index(env, actions)])
    menu = len(env.legal_actions())
    for simulations in args.simulations:
        config = MctsConfig(simulations=simulations, max_depth=16, seed=7, rules_version="census")
        result = VectorMCTS(HashedEvaluator(), config).search(env, add_root_noise=True, reuse_root=False)
        visits = sorted((v for v in result.visit_counts if v), reverse=True)
        print(json.dumps({"menu": menu, "simulations": simulations, "distinct_children_visited": len(visits),
                          "largest_visit_counts": visits[:5], "largest_target_probability": round(max(result.policy), 4)}))


def search(args: argparse.Namespace) -> None:
    from studies.shared.multiplayer_mcts import MctsConfig, UniformEvaluator, VectorMCTS

    env = make_env(args.seed, calendar_rounds=args.rounds)
    rng = random.Random(args.seed)
    config = MctsConfig(simulations=args.simulations, max_depth=args.depth, seed=args.seed, rules_version="census")
    totals = defaultdict(lambda: [0, 0.0])
    # Every expanded decision node in a search tree costs one network evaluation.
    expansions = Counter()
    with open(args.out, "w") as handle:
        while not env.is_terminal():
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            actions = env.legal_actions()
            kinds = {raw_action(a)["kind"] for a in actions}
            start = time.perf_counter()
            mcts = VectorMCTS(UniformEvaluator(), config)
            result = mcts.search(env, add_root_noise=True, reuse_root=False)
            elapsed = time.perf_counter() - start
            for node in mcts.nodes.values():
                if node.expanded and node.edges:
                    expansions["single_option" if len(node.edges) == 1 else node.kind] += 1
            # The scripted policy plays the same game on any interface that keeps its
            # choices, so the search work of two engine versions can be compared.
            index = scripted_index(env, actions) if args.policy == "balanced" else rng.randrange(len(actions))
            chosen = raw_action(actions[index])["kind"]
            if len(actions) == 1:
                category = "single_option"
            elif kinds <= {"land_progress_battle", "land_begin_battle"}:
                category = "battle_bookkeeping"
            elif chosen in {"naval_start_move", "naval_route", "naval_force_add"}:
                category = "naval_order"
            else:
                category = "other"
            totals[category][0] += 1
            totals[category][1] += elapsed
            handle.write(json.dumps({"menu": len(actions), "category": category, "chosen": chosen,
                                     "owner": env.current_decision_player(), "search_s": round(elapsed, 4)}) + "\n")
            env.apply_action(actions[index])
    print(json.dumps({"returns": [round(x, 2) for x in env.returns()],
                      "by_root_category": {category: {"decisions": n, "search_s": round(seconds, 1)}
                                           for category, (n, seconds) in totals.items()},
                      "expanded_decision_nodes": sum(expansions.values()),
                      "expanded_decision_nodes_by_kind": dict(expansions.most_common())}, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("census", "symmetry", "incentive"):
        command = commands.add_parser(name)
        if name == "census":
            command.add_argument("out")
        if name != "incentive":
            command.add_argument("--policy", default="balanced", choices=["balanced", "uniform"])
        command.add_argument("--rounds", type=int, default=3)
        command.add_argument("--seeds", type=int, nargs="+", default=[1951])
    command = commands.add_parser("savings")
    command.add_argument("logs", nargs="+")
    command = commands.add_parser("search")
    command.add_argument("out")
    command.add_argument("--seed", type=int, default=1953)
    command.add_argument("--rounds", type=int, default=3)
    command.add_argument("--simulations", type=int, default=16)
    command.add_argument("--depth", type=int, default=16)
    command.add_argument("--policy", default="uniform", choices=["balanced", "uniform"])
    command = commands.add_parser("export")
    command.add_argument("directory")
    command.add_argument("--seed", type=int, default=1952)
    command.add_argument("--rounds", type=int, default=3)
    command = commands.add_parser("targets")
    command.add_argument("--seed", type=int, default=1951)
    command.add_argument("--rounds", type=int, default=3)
    command.add_argument("--simulations", type=int, nargs="+", default=[16, 64])
    args = parser.parse_args()
    {"census": census, "savings": savings, "symmetry": symmetry, "incentive": incentive, "search": search,
     "export": export, "targets": targets}[args.command](args)


if __name__ == "__main__":
    main()
