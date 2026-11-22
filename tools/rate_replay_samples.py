#!/usr/bin/env python3
"""Rate the training samples in a run's replay buffer: search targets and values by game round.

Loads the replay buffer of a run's checkpoint, `RUN/run/checkpoint.pt`, with the
run's frozen copy of the code, `RUN/code`, whose zone inputs and model exports
it needs, and rates every training sample with the network generation that
played its decision. That network was exported before the decision's game
ended, so the game's samples had not trained it: the rating is on games new to
the network, like the fresh-game losses of `manifest.json`, but sample by
sample, so it can be split by game round and by kind of decision.

    .venv/bin/python tools/rate_replay_samples.py RUN --output rating.json [--rows rows.jsonl]

It reports:

- **The search's targets**, by the number of legal actions and by the kind of
  decision (the commonest kind among the decision's legal actions other than
  ending the phase): the visit share of the most visited action; how many
  actions the search visited; the chance that the move played, drawn from the
  visit shares at temperature 1, is not a most visited one; the KL divergence of
  the network's probabilities from the visit shares; and how often the
  network's likeliest action is a most visited one.
- **The values, by game round**: for each alliance, the share of the variance
  of its final scores that the network's values explain on the samples of that
  game round. Beside it, the same share for a linear model of the same input:
  ridge regression on the global feature values and on the zone feature values
  summed over the 37 zones, each feature value a as sign(a) ln(1 + |a|), as the
  network reads it. The linear model is fitted for each game round in five
  folds that keep each game's samples together, each fold predicted by a model
  fitted on the other four, with the ridge penalty chosen by the same kind of
  folds within those four.
- **The two losses' gradients**, in the newest exported network, over 20
  minibatches of 32 training samples drawn from the replay buffer: the size of
  the value loss's gradient and of the policy loss's on each group of
  parameters (the value head, the layers only the policy reads, and the layers
  both heads read), and the cosine of the angle between the two.

A game is known by its three final scores, which every one of its training
samples stores. The kind of a decision and its game round come from the
decision's input (`kind:` action features and the `round` global feature).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ALLIANCES = ("axis", "allies", "comintern")
FAMILIES = (("naval", "naval_"), ("land combat", "land_"), ("air", "air_"), ("economy", "economy_"),
            ("recruitment", "recruitment_"), ("politics", "politics_"), ("movement", "movement_"))
OPTION_BUCKETS = ((1, "1"), (4, "2-4"), (16, "5-16"), (63, "17-63"), (math.inf, "64 or more"))
PENALTIES = (1, 3, 10, 30, 100, 300, 1000, 3000)
FOLDS = 5


def decision_kind(kinds: dict[str, int]) -> str:
    """The commonest kind among a decision's legal actions, ending the phase only if nothing else is legal."""
    others = {kind: count for kind, count in kinds.items() if kind != "end_phase"}
    return max(sorted(others), key=others.get) if others else "end_phase"


def family(kind: str) -> str:
    return next((name for name, prefix in FAMILIES if kind.startswith(prefix)), kind)


def option_bucket(options: int) -> str:
    return next(label for edge, label in OPTION_BUCKETS if options <= edge)


def target_facts(visits: Sequence[float], prior: Sequence[float]) -> dict[str, float]:
    """What one decision's visit shares say, against the network's probabilities `prior`."""
    top = max(visits)
    best = max(range(len(prior)), key=prior.__getitem__)
    return {"top_share": top,
            "visited": sum(1 for share in visits if share > 0),
            # Drawn at temperature 1: the move played is one of the most visited with this chance.
            "not_top": 1 - sum(share for share in visits if share == top),
            "kl": sum(share * math.log(share / max(p, 1e-12)) for share, p in zip(visits, prior) if share > 0),
            "agree": float(visits[best] == top)}


def explained(predicted: np.ndarray, target: np.ndarray) -> float | None:
    """The share of the target's variance that the predictions explain (negative if worse than its mean)."""
    variance = float(np.var(target))
    return None if variance == 0 else 1 - float(np.mean((predicted - target) ** 2)) / variance


def game_folds(targets: Sequence[Sequence[float]], folds: int = FOLDS, seed: int = 20261121) -> np.ndarray:
    """A fold for each sample, the same for every sample of one game (games known by their final scores)."""
    games: dict[tuple[float, ...], int] = {}
    game = np.array([games.setdefault(tuple(round(v, 6) for v in scores), len(games)) for scores in targets])
    return np.random.default_rng(seed).integers(0, folds, size=len(games))[game]


def ridge_fit_predict(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray, penalty: float) -> np.ndarray:
    """Ridge regression with an unpenalized intercept, solved in its dual form (fewer samples than features)."""
    mean_x, mean_y = train_x.mean(0), train_y.mean(0)
    centred = train_x - mean_x
    weights = np.linalg.solve(centred @ centred.T + penalty * np.eye(len(centred)), train_y - mean_y)
    return (test_x - mean_x) @ (centred.T @ weights) + mean_y


def choose_penalty(x: np.ndarray, y: np.ndarray, fold: np.ndarray) -> float:
    """The ridge penalty whose models, each fitted on all folds but one, predict the left-out folds best."""
    errors = []
    for penalty in PENALTIES:
        error = 0.0
        for part in sorted(set(fold.tolist())):
            fit, check = fold != part, fold == part
            error += float(((ridge_fit_predict(x[fit], y[fit], x[check], penalty) - y[check]) ** 2).sum())
        errors.append(error)
    return PENALTIES[int(np.argmin(errors))]


def linear_predictions(x: np.ndarray, y: np.ndarray, fold: np.ndarray) -> tuple[np.ndarray, list[float]]:
    """Each fold predicted by a ridge model fitted on the other folds, its penalty chosen within them."""
    predicted, chosen = np.zeros_like(y), []
    for held in sorted(set(fold.tolist())):
        train, test = fold != held, fold == held
        penalty = choose_penalty(x[train], y[train], fold[train])
        chosen.append(penalty)
        predicted[test] = ridge_fit_predict(x[train], y[train], x[test], penalty)
    return predicted, chosen


def describe(rows: list[dict[str, Any]]) -> dict[str, float] | None:
    if not rows:
        return None
    mean = lambda name: statistics.fmean(row[name] for row in rows)  # noqa: E731
    return {"samples": len(rows), "mean_options": mean("options"),
            "median_options": statistics.median(row["options"] for row in rows),
            "top_share": mean("top_share"), "visited": mean("visited"), "not_top": mean("not_top"),
            "kl": mean("kl"), "agree": mean("agree"), "kl_total": sum(row["kl"] for row in rows)}


def summarize(rows: list[dict[str, Any]], linear: dict[int, np.ndarray] | None = None) -> dict[str, Any]:
    """Search targets by legal actions, kind and alliance; values by game round, beside the linear model."""
    searched = [row for row in rows if row["options"] > 1]
    by = lambda group: {name: describe(members) for name, members in sorted(  # noqa: E731
        group.items(), key=lambda item: -len(item[1]))}
    families, kinds, owners = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in searched:
        families[row["family"]].append(row)
        kinds[row["kind"]].append(row)
        owners[row["owner"]].append(row)
    total_kl = sum(row["kl"] for row in searched) or 1.0
    out: dict[str, Any] = {
        "samples": len(rows), "forced": len(rows) - len(searched), "searched": describe(searched),
        "by_options": {label: describe([row for row in rows if row["bucket"] == label]) for _, label in OPTION_BUCKETS},
        "by_family": by(families), "by_kind": by(kinds), "by_owner": by(owners),
        "kl_share_by_family": {name: sum(row["kl"] for row in members) / total_kl for name, members in families.items()},
        "samples_by_generation": dict(sorted(Counter(str(row["generation"]) for row in rows).items())),
        "games": len({tuple(round(v, 6) for v in row["targets"]) for row in rows}),
    }
    generations = sorted({row["generation"] for row in rows})
    halves = (generations[:len(generations) // 2], generations[len(generations) // 2:])
    values: dict[str, Any] = {}
    for game_round in sorted({row["round"] for row in rows}):
        members = [index for index, row in enumerate(rows) if row["round"] == game_round]
        target = np.array([rows[index]["targets"] for index in members])
        network = np.array([rows[index]["predicted"] for index in members])
        entry: dict[str, Any] = {"samples": len(members)}
        for column, alliance in enumerate(ALLIANCES):
            entry[alliance] = {"network": explained(network[:, column], target[:, column]),
                               "typical_miss": math.sqrt(float(np.mean((network[:, column] - target[:, column]) ** 2))),
                               "spread": float(np.std(target[:, column]))}
            if linear is not None:
                entry[alliance]["linear"] = explained(linear[game_round][:, column], target[:, column])
            for label, half in zip(("earlier_generations", "later_generations"), halves):
                part = [i for i, index in enumerate(members) if rows[index]["generation"] in half]
                entry[alliance][label] = explained(network[part, column], target[part, column]) if part else None
        values[str(game_round)] = entry
    out["values_by_round"] = values
    out["generation_halves"] = [list(half) for half in halves]
    return out


def open_run(run: Path) -> dict[str, Any]:
    """The run's replay buffer and its exports, read with the run's own copy of the code (RUN/code).

    Returns the replay buffer's samples, the learner's metadata, each exported generation keyed by the
    version string its samples record, the input's `round` and `kind:` columns, and the run code's
    model loader and the log-softmax its training step uses.
    """
    code = run / "code"
    if "studies" in sys.modules:
        raise RuntimeError("Run this tool in a fresh process: it imports the run's own copy of the code")
    os.chdir(code)
    sys.path.insert(0, str(code))
    import torch
    torch.set_num_threads(1)
    from studies.campaign.curriculum import make_env
    from studies.campaign.learning import _fingerprint
    from studies.campaign.model_export import load_evaluation_models
    from studies.campaign.neural import _conditional_log_softmax

    env = make_env(1, calendar_rounds=1)
    spec = getattr(env, "raw", env).zone_encoding_spec()
    learner = torch.load(run / "run" / "checkpoint.pt", map_location="cpu", weights_only=False)["learner"]
    replay, metadata = learner["replay"], learner["metadata"]
    del learner
    # The version a sample records is the fingerprint the learner made of its generation's networks.
    exports = {}
    for path in sorted((run / "run" / "models").glob("generation-*.pt")):
        export = torch.load(path, map_location="cpu", weights_only=False)
        version = _fingerprint({"models": export["model_versions"], "mode": metadata["config"]["mode"],
                                "model_config": metadata["model_config"],
                                "compatibility": metadata["compatibility"]})
        exports[version] = (export["generation"], path)
    return {"torch": torch, "replay": replay, "metadata": metadata, "exports": exports,
            "round_column": spec["global_column_names"].index("round"),
            "kind_columns": {index: name.split(":", 1)[1] for index, name in enumerate(spec["action_column_names"])
                             if name.startswith("kind:")},
            "load_models": load_evaluation_models, "log_softmax": _conditional_log_softmax}


def sample_facts(sample: dict[str, Any], opened: dict[str, Any]) -> dict[str, Any]:
    """A training sample's alliance, game round, legal actions, kind, visit shares, final scores and generation."""
    arrays = sample["input"].arrays()
    columns = list(arrays["global_column"])
    round_column, kind_columns = opened["round_column"], opened["kind_columns"]
    game_round = int(arrays["global_value"][columns.index(round_column)]) if round_column in columns else 0
    offsets, action_columns = arrays["action_offsets"], arrays["action_column"]
    kinds = [next((kind_columns[int(c)] for c in action_columns[offsets[i]:offsets[i + 1]]
                   if int(c) in kind_columns), "unknown") for i in range(len(offsets) - 1)]
    kind = decision_kind(Counter(kinds))
    return {"owner": sample["owner"], "round": game_round, "options": len(kinds), "kind": kind,
            "family": family(kind), "bucket": option_bucket(len(kinds)),
            "visits": [float(share) for share in sample["policy"]], "targets": list(sample["values"]),
            "generation": opened["exports"].get(sample["rollout_version"], (None, None))[0]}


def load_rated_rows(run: Path) -> tuple[list[dict[str, Any]], list[Any], dict[str, Any]]:
    """Every replay sample's facts and the network's outputs for it, from the run's own code and exports,
    and the sizes of the two losses' gradients in the newest exported network."""
    opened = open_run(run)
    torch, replay, metadata, exports = opened["torch"], opened["replay"], opened["metadata"], opened["exports"]
    load_evaluation_models = opened["load_models"]
    rows = [sample_facts(sample, opened) for sample in replay]
    inputs = [sample["input"] for sample in replay]
    scale = metadata["config"]["value_scale"]
    for generation, path in sorted(exports.values()):
        if not any(row["generation"] == generation for row in rows):
            continue
        models = load_evaluation_models(path, device="cpu")["models"]
        for owner in ALLIANCES:  # The network that searched the decision: one for all three, or the owner's own.
            members = [index for index, row in enumerate(rows) if row["generation"] == generation
                       and row["owner"] == owner]
            model = models[owner]
            model.eval()
            with torch.inference_mode():
                for start in range(0, len(members), 64):
                    chunk = members[start:start + 64]
                    logits, values = model.forward_batch([inputs[index] for index in chunk])
                    for index, scores, predicted in zip(chunk, logits, (values.double() * scale).tolist()):
                        prior = torch.softmax(scores.double(), 0).tolist()
                        rows[index].update(target_facts(rows[index]["visits"], prior), predicted=predicted)
    unrated = [row for row in rows if "predicted" not in row]
    if unrated:
        raise ValueError(f"{len(unrated)} samples name no generation exported in RUN/run/models")
    newest_generation, newest = max(exports.values())
    models = load_evaluation_models(newest, device="cpu")["models"]
    gradients = gradient_sizes(models, replay, scale, opened["log_softmax"])
    gradients["generation"] = newest_generation
    return rows, inputs, gradients


GRADIENT_GROUPS = (
    ("value head", ("value_head",)),
    # no_zone stands in for a missing source or target zone of a legal action: only the policy reads it.
    ("policy only", ("option_columns", "option_norm", "option_encoder", "policy_head", "factor_heads", "no_zone")),
    ("shared: embedding tables and map facts", ("zone_columns", "global_columns", "zone_identity", "map_facts")),
    ("shared: message-passing layers", ("messages", "border_facts", "zone_updates", "position_updates",
                                        "zone_norm", "global_norm")),
    ("shared: state encoder", ("state_encoder",)),
)


def gradient_sizes(models: dict[str, Any], replay: list[dict[str, Any]], scale: float, log_softmax: Any,
                   minibatches: int = 20, size: int = 32, seed: int = 5) -> dict[str, Any]:
    """How large the value loss's and the policy loss's gradients are on each group of the Axis network's
    parameters, over minibatches drawn as a training step draws them, and how alike their directions are.

    The losses are those of `CampaignLearner.update`: the value loss on every sample, the policy loss on
    the samples whose owner this network decides for.
    """
    import random
    import torch
    model = models[ALLIANCES[0]]
    model.train()
    named = list(model.named_parameters())
    sums = {name: {"value": 0.0, "policy": 0.0, "product": 0.0} for name, _ in GRADIENT_GROUPS}
    sums["other"] = {"value": 0.0, "policy": 0.0, "product": 0.0}
    losses = []
    draw = random.Random(seed)
    for _ in range(minibatches):
        samples = draw.sample(replay, size)
        logits, predicted = model.forward_batch([sample["input"] for sample in samples])
        target = torch.as_tensor([sample["values"] for sample in samples], dtype=predicted.dtype) / scale
        value_loss = torch.mean((predicted - target) ** 2)
        owned = [index for index, sample in enumerate(samples) if models[sample["owner"]] is model]
        counts = [len(logits[index]) for index in owned]
        desired = np.concatenate([np.asarray(samples[index]["policy"], dtype=np.float64) for index in owned])
        picked = log_softmax(torch.cat([logits[index] for index in owned]),
                             torch.as_tensor(np.repeat(np.arange(len(owned)), counts)), len(owned))
        policy_loss = -(torch.as_tensor(desired, dtype=picked.dtype) * picked).sum() / len(owned)
        parameters = [parameter for _, parameter in named]
        by_value = torch.autograd.grad(value_loss, parameters, retain_graph=True, allow_unused=True)
        by_policy = torch.autograd.grad(policy_loss, parameters, allow_unused=True)
        losses.append((float(value_loss.detach()), float(policy_loss.detach())))
        for (name, parameter), value, policy in zip(named, by_value, by_policy):
            group = next((label for label, prefixes in GRADIENT_GROUPS if name.startswith(prefixes)), "other")
            value = torch.zeros_like(parameter) if value is None else value
            policy = torch.zeros_like(parameter) if policy is None else policy
            sums[group]["value"] += float((value * value).sum())
            sums[group]["policy"] += float((policy * policy).sum())
            sums[group]["product"] += float((value * policy).sum())
    groups = {}
    for group, total in sums.items():
        value, policy = math.sqrt(total["value"]), math.sqrt(total["policy"])
        if value == 0 and policy == 0:
            continue
        groups[group] = {"value_gradient": value, "policy_gradient": policy,
                         "value_over_policy": value / policy if policy else None,
                         "cosine": total["product"] / (value * policy) if value and policy else None}
    return {"minibatches": minibatches, "minibatch_size": size,
            "value_loss": statistics.fmean(loss[0] for loss in losses),
            "policy_loss": statistics.fmean(loss[1] for loss in losses), "groups": groups}


def input_features(inputs: Sequence[Any]) -> np.ndarray:
    """Global feature values and zone feature values summed over the zones, as sign(a) ln(1 + |a|)."""
    global_columns = 1 + max(int(np.max(item.arrays()["global_column"], initial=0)) for item in inputs)
    zone_columns = 1 + max(int(np.max(item.arrays()["zone_column"], initial=0)) for item in inputs)
    features = np.zeros((len(inputs), global_columns + zone_columns))
    for row, item in enumerate(inputs):
        arrays = item.arrays()
        for columns, values, offset in ((arrays["global_column"], arrays["global_value"], 0),
                                        (arrays["zone_column"], arrays["zone_value"], global_columns)):
            values = np.asarray(values, dtype=np.float64)
            np.add.at(features[row], np.asarray(columns, dtype=np.int64) + offset,
                      np.sign(values) * np.log1p(np.abs(values)))
    return features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run", type=Path, help="the run's folder, holding code/ and run/checkpoint.pt")
    parser.add_argument("--output", type=Path, required=True, help="the summary, as JSON")
    parser.add_argument("--rows", type=Path, help="also every sample's facts, one JSON line each")
    arguments = parser.parse_args()
    run, output = arguments.run.resolve(), arguments.output.resolve()
    rows_path = arguments.rows.resolve() if arguments.rows else None
    rows, inputs, gradients = load_rated_rows(run)
    fold = game_folds([row["targets"] for row in rows])
    linear, penalties = {}, {}
    for game_round in sorted({row["round"] for row in rows}):
        members = np.array([index for index, row in enumerate(rows) if row["round"] == game_round])
        x = input_features([inputs[index] for index in members])
        x = x[:, (x != 0).mean(0) >= 0.01]  # Features present in at least 1% of the game round's samples.
        y = np.array([rows[index]["targets"] for index in members])
        linear[game_round], penalties[str(game_round)] = linear_predictions(x, y, fold[members])
        for index, predicted in zip(members, linear[game_round].tolist()):
            rows[index]["linear"] = predicted
        print(f"game round {game_round}: {len(members)} samples, penalties {penalties[str(game_round)]}", flush=True)
    summary = summarize(rows, linear)
    summary["linear_penalties"] = penalties
    summary["loss_gradients"] = gradients
    summary["run"] = str(run)
    output.write_text(json.dumps(summary, indent=1) + "\n")
    if rows_path is not None:
        with rows_path.open("w") as handle:
            for row in rows:
                handle.write(json.dumps({k: v for k, v in row.items() if k != "visits"}) + "\n")
    print(f"{summary['samples']} samples from {summary['games']} games; written to {output}")


if __name__ == "__main__":
    main()
