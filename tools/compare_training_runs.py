#!/usr/bin/env python3
"""Compare matched training runs: speed, losses on fresh games and held-out games.

Reads the run directories that `studies.campaign.run` writes in self-play that
never stops (progress.jsonl and manifest.json) and the evaluation bundles of
`studies.campaign.run evaluate`, prints a summary, and with --output saves every
number as JSON:

    .venv/bin/python tools/compare_training_runs.py \
        --run three=RUN_A --run one=RUN_B \
        --evaluation three=A-axis.json,A-allies.json,A-comintern.json \
        --evaluation one=B-axis.json,B-allies.json,B-comintern.json \
        --output comparison.json

A run stopped and resumed has several invocations. Each ends with an
`interrupted` line in progress.jsonl and restarts its clock and the inference
server's counters; a run's *active time* adds up the seconds of its invocations.

- **Speed**, per invocation: seconds, network updates, games and decisions, and
  per hour; the inference server's forward-pass time per evaluation and
  evaluations per inference batch.
- **Losses on fresh games**, per hour of active time: each network update's
  `fresh_games`, where every finished game was scored by the networks serving
  self-play before it trained them. The value loss, the variance of the games'
  final scores, the share of that variance the value loss explains, the policy
  cross-entropy and the KL divergence, overall and by deciding alliance. The
  variance is that of the final scores divided by value_scale, weighted by each
  game's kept decisions and averaged over the three alliances: the value loss of
  always predicting the window's mean score.
- **Held-out games**, per named group of evaluation bundles: for each target
  alliance, the target's mean final score and its standard error over seeds;
  and for every two groups the paired difference over their common seeds, with
  the number of seeds where the first group scored higher.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
from pathlib import Path

PLAYERS = ("axis", "allies", "comintern")  # The order of studies.shared.multiplayer_mcts.PLAYERS.
HOUR = 3600.0


def _named(text: str) -> tuple[str, str]:
    name, separator, value = text.partition("=")
    if not separator or not name or not value:
        raise argparse.ArgumentTypeError(f"expected NAME=VALUE, got {text!r}")
    return name, value


def invocations(progress: list[dict]) -> list[list[dict]]:
    """Progress lines split into invocations, each ending with its 'interrupted' line."""
    blocks, current = [], []
    for line in progress:
        current.append(line)
        if line.get("event") == "interrupted":
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def read_run(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text())
    progress = [json.loads(line) for line in (directory / "progress.jsonl").read_text().splitlines() if line.strip()]
    updates = manifest["runner"]["updates"]
    blocks = invocations(progress)

    # Each network update's active time, and the invocation it belongs to.
    offsets, total = [], 0.0
    for block in blocks:
        offsets.append(total)
        total += block[-1]["elapsed_seconds"]
    placed, index, previous = [], 0, None
    for update in updates:
        if previous is not None and update["elapsed_seconds"] < previous:
            index += 1
        placed.append((index, offsets[index] + update["elapsed_seconds"]))
        previous = update["elapsed_seconds"]

    speed, before = [], dict.fromkeys(("updates", "episodes", "decisions", "transitions"), 0)
    for number, block in enumerate(blocks):
        end = block[-1]
        seconds, counters = end["elapsed_seconds"], end["counters"]
        change = {name: counters[name] - before[name] for name in before}
        served = [update["evaluator"] for update, (owner, _) in zip(updates, placed) if owner == number]
        last = served[-1] if served else {}
        speed.append({
            "invocation": number + 1, "seconds": seconds, "network_updates": change["updates"],
            "games": change["episodes"], "decisions": change["decisions"],
            "decisions_per_hour": change["decisions"] / seconds * HOUR,
            "games_per_hour": change["episodes"] / seconds * HOUR,
            "decisions_per_game": change["decisions"] / change["episodes"] if change["episodes"] else None,
            "network_update_seconds": statistics.fmean(update["update_seconds"] for update, (owner, _) in zip(updates, placed)
                                                      if owner == number) if served else None,
            "forward_microseconds_per_evaluation": 1e6 * last["forward_seconds"] / last["evaluations"] if last else None,
            "evaluations_per_inference_batch": last["evaluations"] / last["serving_rounds"] if last else None,
            "server_idle_share": last["idle_seconds"] / served_seconds(updates, placed, number) if last else None})
        before = {name: counters[name] for name in before}

    scale = float(manifest["runner"]["config"]["value_scale"])
    return {"directory": str(directory), "networks": manifest["runner"]["config"].get("networks", "three"),
            "status": manifest.get("status"), "active_seconds": total, "speed": speed,
            "updates": [{"network_update": number + 1, "active_seconds": seconds,
                         "fresh": fresh_totals(update, scale)} for number, (update, (_, seconds)) in enumerate(zip(updates, placed))],
            "hours": [window(updates, placed, scale, start, start + HOUR)
                      for start in (hour * HOUR for hour in range(math.ceil(total / HOUR)))],
            # The first hour's games include those that generation 0 scored, far off the mark.
            "after_first_hour": window(updates, placed, scale, HOUR, total)}


def served_seconds(updates: list[dict], placed: list[tuple[int, float]], number: int) -> float:
    return max(update["elapsed_seconds"] for update, (owner, _) in zip(updates, placed) if owner == number)


def fresh_totals(update: dict, scale: float) -> dict:
    """One network update's fresh-game losses per kept decision, overall and by alliance."""
    return summarize_games(update.get("episodes") or [], scale)


def summarize_games(games: list[dict], scale: float) -> dict:
    sums = {owner: {"samples": 0, "value_squared_error": 0.0, "policy_cross_entropy": 0.0, "policy_kl": 0.0}
            for owner in (*PLAYERS, "all")}
    moments = {owner: [0.0, [0.0] * 3, [0.0] * 3] for owner in (*PLAYERS, "all")}  # weight, sum, sum of squares
    for game in games:
        losses = game.get("fresh_losses") or {}
        scores = game.get("observed_terminal_returns")
        if not losses or scores is None:
            continue
        scores = [score / scale for score in scores]
        for owner, values in losses.items():
            for target in (owner, "all"):
                for name in sums[target]:
                    sums[target][name] += values[name]
                weight = values["samples"]
                moments[target][0] += weight
                for alliance in range(3):
                    moments[target][1][alliance] += weight * scores[alliance]
                    moments[target][2][alliance] += weight * scores[alliance] ** 2
    result = {}
    for owner, total in sums.items():
        samples = total["samples"]
        if not samples:
            continue
        weight, first, second = moments[owner]
        variance = statistics.fmean(second[i] / weight - (first[i] / weight) ** 2 for i in range(3))
        value = total["value_squared_error"] / samples
        result[owner] = {"samples": samples, "value_loss": value, "score_variance": variance,
                         "explained": 1.0 - value / variance if variance > 0 else None,
                         "policy_cross_entropy": total["policy_cross_entropy"] / samples,
                         "policy_kl": total["policy_kl"] / samples}
    return result


def window(updates: list[dict], placed: list[tuple[int, float]], scale: float, start: float, end: float) -> dict:
    picked = [update for update, (_, seconds) in zip(updates, placed) if start <= seconds < end]
    games = [game for update in picked for game in update.get("episodes") or []]
    return {"from_hours": start / HOUR, "to_hours": end / HOUR, "network_updates": len(picked),
            "games": len(games), "losses": summarize_games(games, scale)}


def read_evaluations(files: list[Path]) -> dict:
    """Each target alliance's final score by seed, over a group's evaluation bundles."""
    targets: dict[str, dict] = {}
    for path in files:
        bundle = json.loads(path.read_text())
        for result in bundle["results"]:
            target = result["target_player"]
            entry = targets.setdefault(target, {"scores": {}, "unfinished": 0, "decisions": 0})
            for game in result["games"]:
                if game.get("truncated") or game.get("observed_terminal_returns") is None:
                    entry["unfinished"] += 1
                    continue
                if game["seed"] in entry["scores"]:
                    raise ValueError(f"{path}: seed {game['seed']} of {target} appears twice")
                entry["scores"][game["seed"]] = game["observed_terminal_returns"][PLAYERS.index(target)]
                entry["decisions"] += game["decisions_by_actor"][target]
    for entry in targets.values():
        scores = list(entry["scores"].values())
        entry["games"] = len(scores)
        entry["mean"] = statistics.fmean(scores)
        entry["standard_error"] = statistics.stdev(scores) / math.sqrt(len(scores)) if len(scores) > 1 else None
        entry["decisions_per_game"] = entry["decisions"] / len(scores)
    return targets


def paired(first: dict, second: dict) -> dict:
    result = {}
    for target in PLAYERS:
        if target not in first or target not in second:
            continue
        seeds = sorted(set(first[target]["scores"]) & set(second[target]["scores"]))
        differences = [first[target]["scores"][seed] - second[target]["scores"][seed] for seed in seeds]
        if len(differences) < 2:
            continue
        result[target] = {"seeds": len(seeds), "mean": statistics.fmean(differences),
                          "standard_error": statistics.stdev(differences) / math.sqrt(len(differences)),
                          "first_higher": sum(1 for difference in differences if difference > 0)}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=_named, action="append", default=[], metavar="NAME=DIRECTORY",
                        help="A run directory, under a name; repeat for each run")
    parser.add_argument("--evaluation", type=_named, action="append", default=[], metavar="NAME=FILE,FILE",
                        help="Evaluation bundles, comma-separated, under a group name; repeat for each group")
    parser.add_argument("--output", type=Path, help="Write every number here as JSON")
    args = parser.parse_args(argv)
    report = {"runs": {name: read_run(Path(directory)) for name, directory in args.run},
              "evaluations": {name: read_evaluations([Path(path) for path in files.split(",")])
                              for name, files in args.evaluation}}
    report["paired"] = {f"{a} minus {b}": paired(report["evaluations"][a], report["evaluations"][b])
                        for a, b in itertools.combinations(report["evaluations"], 2)}

    for name, run in report["runs"].items():
        print(f"== {name}: --networks {run['networks']}, {run['active_seconds'] / HOUR:.2f} active hours, {run['status']}")
        for block in run["speed"]:
            print(f"   invocation {block['invocation']}: {block['seconds']:.0f} s, {block['network_updates']} network updates, "
                  f"{block['games']} games, {block['decisions']:,} decisions, {block['decisions_per_hour']:,.0f} decisions/h, "
                  f"forward pass {block['forward_microseconds_per_evaluation']:.0f} us per evaluation, "
                  f"network update {block['network_update_seconds']:.1f} s")
        for hour in (*run["hours"], run["after_first_hour"]):
            overall = hour["losses"].get("all")
            if not overall:
                continue
            print(f"   hours {hour['from_hours']:.0f}-{hour['to_hours']:.0f}: {hour['network_updates']} network updates, "
                  f"value loss {overall['value_loss']:.4f} of variance {overall['score_variance']:.4f} "
                  f"({100 * overall['explained']:.1f}% explained), policy KL {overall['policy_kl']:.4f}; "
                  + ", ".join(f"{p} KL {hour['losses'][p]['policy_kl']:.3f}" for p in PLAYERS if p in hour["losses"]))
    for name, targets in report["evaluations"].items():
        print(f"== held-out games, {name}: "
              + "; ".join(f"{target} {entry['mean']:+.1f} ± {entry['standard_error']:.1f} ({entry['games']} games, "
                          f"{entry['unfinished']} unfinished)" for target, entry in targets.items()))
    for label, targets in report["paired"].items():
        print(f"== {label}: " + "; ".join(f"{target} {entry['mean']:+.1f} ± {entry['standard_error']:.1f}, "
                                          f"higher in {entry['first_higher']} of {entry['seeds']} seeds"
                                          for target, entry in targets.items()))
    if args.output:
        args.output.write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
