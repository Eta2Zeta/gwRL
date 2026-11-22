#!/usr/bin/env python3
"""Train copies of a run's network on its saved training samples, at several weights of the value loss.

Starts from one generation of a run, `RUN/run/models/generation-N.pt`, and uses only the games of the
run's last replay buffer (`RUN/run/checkpoint.pt`) that ended after that generation was exported, so that
it had trained on none of them: the games with at least one training sample from that generation or a
later one. A game is known by its three final scores, which all its training samples store. One fifth of
those games is held out, those in fold 0 of the folds `tools/rate_replay_samples.py` uses; the training
samples of the other four fifths train.

For each weight w a fresh copy of the network trains as a network update trains it
(`CampaignLearner.update` in `studies/campaign/learning.py`): Adam at the run's learning rate, minibatches
of the run's size drawn at random from the training samples, and the loss w times the value loss plus the
policy loss. Every weight draws the same minibatches. At the start and every --check-every training steps
the copy rates the held-out samples: the share of each alliance's final-score variance its values explain,
over all of them and game round by game round; its value loss; and its policy's KL divergence from the
visit shares at the searched decisions. It also rates a fixed fifth of the training samples, to show how
closely it fits the games it trains on.

Beside these, on the same held-out samples, two yardsticks: the networks that played the decisions, and a
linear model of the same input fitted game round by game round on the training games
(`rate_replay_samples.input_features`, its ridge penalty chosen in folds within the training games).

Run it, like `tools/rate_replay_samples.py`, in a fresh process; it reads the run with the run's own copy
of the code (`RUN/code`):

    .venv/bin/python tools/train_on_saved_samples.py RUN --start 3 --weights 1 10 50 --steps 4000 \\
        --check-every 500 --output weights.json
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

try:
    from tools.rate_replay_samples import (ALLIANCES, choose_penalty, explained, game_folds, input_features,
                                           open_run, ridge_fit_predict, sample_facts, target_facts)
except ImportError:  # Run as a script: tools/ is on the path, the repository is not.
    from rate_replay_samples import (ALLIANCES, choose_penalty, explained, game_folds, input_features,  # type: ignore
                                     open_run, ridge_fit_predict, sample_facts, target_facts)

HELD_FOLD = 0


def split_games(targets: Sequence[Sequence[float]], generations: Sequence[int | None], start: int,
                fold: np.ndarray | None = None) -> tuple[list[int], list[int]]:
    """The training and the held-out samples among the games with a sample from generation `start` or later."""
    keys = [tuple(round(v, 6) for v in scores) for scores in targets]
    latest: dict[tuple[float, ...], int] = {}
    for key, generation in zip(keys, generations):
        if generation is not None:
            latest[key] = max(latest.get(key, -1), generation)
    fold = game_folds(targets) if fold is None else fold
    kept = [index for index, key in enumerate(keys) if latest.get(key, -1) >= start]
    return ([index for index in kept if fold[index] != HELD_FOLD],
            [index for index in kept if fold[index] == HELD_FOLD])


def value_report(predicted: np.ndarray, targets: np.ndarray, rounds: np.ndarray, scale: float) -> dict[str, Any]:
    """Explained variance of each alliance's final scores, over all samples and by game round; the value loss."""
    report: dict[str, Any] = {"value_loss": float(np.mean(((predicted - targets) / scale) ** 2)),
                              "overall": {alliance: explained(predicted[:, column], targets[:, column])
                                          for column, alliance in enumerate(ALLIANCES)},
                              "by_round": {}}
    for game_round in sorted(set(rounds.tolist())):
        members = rounds == game_round
        report["by_round"][str(game_round)] = {alliance: explained(predicted[members, column], targets[members, column])
                                               for column, alliance in enumerate(ALLIANCES)}
    return report


def rate(model: Any, inputs: Sequence[Any], scale: float, torch: Any) -> tuple[np.ndarray, list[list[float]]]:
    """The network's three values, in points, and its action probabilities, for each input."""
    values, priors = [], []
    model.eval()
    with torch.inference_mode():
        for begin in range(0, len(inputs), 64):
            logits, predicted = model.forward_batch(list(inputs[begin:begin + 64]))
            values.extend((predicted.double() * scale).tolist())
            priors.extend(torch.softmax(scores.double(), 0).tolist() for scores in logits)
    return np.array(values), priors


def train_copy(model: Any, samples: Sequence[dict[str, Any]], train: Sequence[int], *, weight: float, steps: int,
               batch_size: int, learning_rate: float, scale: float, log_softmax: Callable, torch: Any, seed: int,
               check_every: int, check: Callable[[Any, int], dict[str, Any]]) -> list[dict[str, Any]]:
    """Training steps as `CampaignLearner.update` takes them, with the value loss times `weight`."""
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    draw = random.Random(seed)
    history = [check(model, 0)]
    for step in range(1, steps + 1):
        model.train()
        chosen = [samples[index] for index in draw.sample(list(train), batch_size)]
        optimizer.zero_grad(set_to_none=True)
        logits, predicted = model.forward_batch([sample["input"] for sample in chosen])
        target = torch.as_tensor([sample["values"] for sample in chosen], dtype=predicted.dtype) / scale
        value_loss = torch.mean((predicted - target) ** 2)
        counts = [len(scores) for scores in logits]
        desired = np.concatenate([np.asarray(sample["policy"], dtype=np.float64) for sample in chosen])
        picked = log_softmax(torch.cat(logits), torch.as_tensor(np.repeat(np.arange(len(chosen)), counts)),
                             len(chosen))
        policy_loss = -(torch.as_tensor(desired, dtype=picked.dtype) * picked).sum() / len(chosen)
        (weight * value_loss + policy_loss).backward()
        optimizer.step()
        if step % check_every == 0:
            history.append(check(model, step))
    return history


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run", type=Path, help="the run's folder, holding code/, run/checkpoint.pt and run/models/")
    parser.add_argument("--start", type=int, required=True, help="the generation the copies start from")
    parser.add_argument("--weights", type=float, nargs="+", required=True, help="weights of the value loss")
    parser.add_argument("--steps", type=int, default=4000, help="training steps for each weight")
    parser.add_argument("--check-every", type=int, default=500, help="training steps between ratings")
    parser.add_argument("--seed", type=int, default=20261122, help="seed of the minibatch draws")
    parser.add_argument("--output", type=Path, required=True, help="every number, as JSON")
    arguments = parser.parse_args()
    run, output = arguments.run.resolve(), arguments.output.resolve()
    began = time.time()
    opened = open_run(run)
    torch, replay, metadata = opened["torch"], opened["replay"], opened["metadata"]
    if metadata["config"]["networks"] != "one":
        raise ValueError("This test trains one network for the three alliances")
    scale = metadata["config"]["value_scale"]
    facts = [sample_facts(sample, opened) for sample in replay]
    targets = [fact["targets"] for fact in facts]
    fold = game_folds(targets)
    train, held = split_games(targets, [fact["generation"] for fact in facts], arguments.start, fold)
    games = lambda indices: len({tuple(round(v, 6) for v in targets[i]) for i in indices})  # noqa: E731
    exports = {generation: path for generation, path in opened["exports"].values()}
    load = lambda generation: opened["load_models"](exports[generation], device="cpu")["models"][ALLIANCES[0]]  # noqa: E731

    held_inputs = [replay[index]["input"] for index in held]
    held_targets = np.array([targets[index] for index in held])
    held_rounds = np.array([facts[index]["round"] for index in held])
    searched = [position for position, index in enumerate(held) if facts[index]["options"] > 1]
    fit_sample = sorted(random.Random(arguments.seed + 1).sample(train, len(train) // 5))
    fit_inputs = [replay[index]["input"] for index in fit_sample]
    fit_targets = np.array([targets[index] for index in fit_sample])

    def check(model: Any, step: int) -> dict[str, Any]:
        values, priors = rate(model, held_inputs, scale, torch)
        report = value_report(values, held_targets, held_rounds, scale)
        report["kl"] = statistics.fmean(target_facts(facts[held[position]]["visits"], priors[position])["kl"]
                                        for position in searched)
        fitted, _ = rate(model, fit_inputs, scale, torch)
        report["training_value_loss"] = float(np.mean(((fitted - fit_targets) / scale) ** 2))
        report["step"] = step
        report["seconds"] = time.time() - began
        print(f"step {step}: held-out value loss {report['value_loss']:.5f}, explained "
              + ", ".join(f"{a} {100 * report['overall'][a]:.1f}%" for a in ALLIANCES)
              + f", KL {report['kl']:.3f}, training value loss {report['training_value_loss']:.5f}", flush=True)
        return report

    # Yardsticks: the networks that played the held-out decisions, and the linear model.
    played = np.zeros_like(held_targets)
    for generation in sorted({facts[index]["generation"] for index in held}):
        positions = [position for position, index in enumerate(held) if facts[index]["generation"] == generation]
        values, _ = rate(load(generation), [held_inputs[position] for position in positions], scale, torch)
        played[positions] = values
    linear = np.zeros_like(held_targets)
    penalties = {}
    for game_round in sorted(set(held_rounds.tolist())):
        fitting = [index for index in train if facts[index]["round"] == game_round]
        testing = [position for position, index in enumerate(held) if facts[index]["round"] == game_round]
        x = input_features([replay[index]["input"] for index in fitting] + [held_inputs[p] for p in testing])
        x = x[:, (x[:len(fitting)] != 0).mean(0) >= 0.01]  # Features in at least 1% of the training samples.
        y = np.array([targets[index] for index in fitting])
        penalty = choose_penalty(x[:len(fitting)], y, fold[fitting])
        penalties[str(game_round)] = penalty
        linear[testing] = ridge_fit_predict(x[:len(fitting)], y, x[len(fitting):], penalty)
    result: dict[str, Any] = {
        "run": str(run), "start_generation": arguments.start,
        "settings": {"weights": arguments.weights, "steps": arguments.steps, "check_every": arguments.check_every,
                     "seed": arguments.seed, "batch_size": metadata["config"]["batch_size"],
                     "learning_rate": metadata["config"]["learning_rate"], "value_scale": scale},
        "training": {"games": games(train), "samples": len(train)},
        "held_out": {"games": games(held), "samples": len(held), "searched": len(searched)},
        "yardsticks": {"played_by": value_report(played, held_targets, held_rounds, scale),
                       "linear_model": value_report(linear, held_targets, held_rounds, scale),
                       "linear_penalties": penalties},
        "weights": {},
    }
    print(f"{result['training']} training, {result['held_out']} held out; yardsticks rated", flush=True)
    for weight in arguments.weights:
        result["weights"][str(weight)] = train_copy(
            load(arguments.start), replay, train, weight=weight, steps=arguments.steps,
            batch_size=metadata["config"]["batch_size"], learning_rate=metadata["config"]["learning_rate"],
            scale=scale, log_softmax=opened["log_softmax"], torch=torch, seed=arguments.seed,
            check_every=arguments.check_every, check=check)
        output.write_text(json.dumps(result, indent=1) + "\n")  # Kept after each weight.
    print(f"written to {output} after {time.time() - began:.0f} s")


if __name__ == "__main__":
    main()
