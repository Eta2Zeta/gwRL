#!/usr/bin/env python3
"""Rebuild a game from its move log, and search its last decisions again.

A training run writes each game's moves as it plays them to game-moves/ in its
run folder (write_move in studies/campaign/learning.py) and removes the log when
the game finishes or a stop ends it. A log that stays belongs to a game that
failed or whose game process died: the failed game's record in manifest.json
names it. With the game's seed, kept in the log's first line, the moves rebuild
the game's position exactly, because the game's own random stream rolls its
dice. The log's "search" lines give each decision's search seed, the size of
the search tree the game kept, the search's simulations, whether it added
exploration noise and, since 25 November 2026, its depth limit, its
simulations a request and whether its budget counted the reused tree's visits;
a log that ends with a "search" line belongs to a
game whose process died during that search, as all five crashes of 20 and 21
November 2026 did.

The tool replays the moves and reports how far the log goes, the final planning
key and whether a search was under way. With --search K it searches the last K
decisions again before playing their moves, in a search tree kept from one to
the next as in training, and then the decision that was under way, so that a
build with memory checks (AddressSanitizer) goes through the same positions and
the same freeing of tree nodes. The network's priors come from --model, a model
export run on the CPU, or are uniform without it; the trees then differ from
the game's, whose networks answered on the GPU.

Run it with the code that played the game (a run's frozen copy):

    .venv/bin/python tools/replay_game_moves.py RUN/game-moves/game-N-seed-S.jsonl [--search K] [--model PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def read_log(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The log's first line and its moves; a last line cut short by a crash is dropped."""
    lines = path.read_text(encoding="utf-8").split("\n")
    header = json.loads(lines[0])
    moves = []
    for line in lines[1:]:
        if not line:
            continue
        try:
            moves.append(json.loads(line))
        except ValueError:
            break  # Cut short as the process died.
    return header, moves


def replay(header: dict[str, Any], moves: list[dict[str, Any]], *, search_last: int = 0,
           evaluator: Any = None) -> dict[str, Any]:
    """Play the logged moves from the game's seed. With `search_last` K, search
    the last K decisions that were played, and the one under way, with their
    logged seeds and the training run's search settings, in one kept tree."""
    from studies.campaign.curriculum import make_env
    from studies.campaign.native_search import SearchTree, search_decision
    from studies.shared.multiplayer_mcts import MctsConfig, UniformEvaluator, action_key

    env = make_env(int(header["seed"]), calendar_rounds=header["calendar_rounds"])
    evaluator = evaluator if evaluator is not None else UniformEvaluator()
    search_lines = [index for index, move in enumerate(moves) if move["kind"] == "search"]
    under_way = bool(search_lines) and all(move["kind"] != "action" for move in moves[search_lines[-1] + 1:])
    if search_last > 0 and search_lines:
        count = search_last + (1 if under_way else 0)
        first_searched = search_lines[max(0, len(search_lines) - count)]
    else:
        first_searched = len(moves)
    tree, searches, played, pending = SearchTree(), 0, 0, None
    for index, move in enumerate(moves):
        if move["kind"] == "search":
            pending = move
            if index >= first_searched:
                # The logged search settings; logs written before 25 November 2026 name
                # only the simulations and the noise, and searched with a depth limit of
                # 16, one simulation a request and every search's whole budget.
                config = MctsConfig(simulations=int(move["simulations"]), max_depth=int(move.get("max_depth", 16)),
                                    c_puct=1.5, seed=int(move["search_seed"]), mode="multiplayer",
                                    root_dirichlet_alpha=0.3, root_dirichlet_epsilon=0.25,
                                    simulations_per_request=int(move.get("simulations_per_request", 1)),
                                    count_reused_visits=bool(move.get("count_reused_visits", False)))
                search_decision(env, evaluator, config, add_root_noise=bool(move["root_noise"]), tree=tree)
                searches += 1
            continue
        if move["kind"] == "chance":
            if env.decision_kind() != "chance":
                return {"outcome": "log_differs", "move": move, "played": played}
            env.resolve_chance()
        elif move["kind"] == "action":
            offered = {action_key(action): action for action in env.legal_actions()}
            if move["action"] not in offered:
                return {"outcome": "move_not_offered", "move": move, "played": played}
            env.apply_action(offered[move["action"]])
            pending = None
        played += 1
    return {"outcome": "replayed", "played": played, "searches": searches,
            "final_planning_key": env.planning_key(), "terminal": env.is_terminal(),
            "search_under_way": pending if under_way else None, "env": env}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("log", type=Path)
    parser.add_argument("--search", type=int, default=0, metavar="K",
                        help="search the last K decisions again, and the one under way")
    parser.add_argument("--model", type=Path, help="a model export whose network gives the searches' priors, on the CPU")
    parser.add_argument("--position", type=Path, help="write the rebuilt position here")
    args = parser.parse_args(argv)
    header, moves = read_log(args.log)
    if header.get("schema") != "campaign-game-moves-v1":
        parser.error(f"{args.log} is not a game move log")
    evaluator = None
    if args.model is not None:
        import torch
        torch.set_num_threads(1)
        from studies.campaign.neural import NeuralEvaluator
        from studies.campaign.run import load_evaluation_models
        evaluator = NeuralEvaluator(load_evaluation_models(str(args.model), device="cpu")["models"], version="replay")
    result = replay(header, moves, search_last=args.search, evaluator=evaluator)
    env = result.pop("env", None)
    if args.position is not None and env is not None:
        args.position.write_text(env.serialize(), encoding="utf-8")
        result["position"] = str(args.position)
    print(json.dumps({"log": str(args.log), "seed": header["seed"], "moves": len(moves), **result}, indent=1))
    return 0 if result["outcome"] == "replayed" else 1


if __name__ == "__main__":
    sys.exit(main())
