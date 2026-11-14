#!/usr/bin/env python3
"""Time a checkout's coordinator on serving rounds saved from a real training batch.

tools/profile_coordinator.py --save-every N keeps every Nth serving round of a
training batch: each request's alliance (None at a chance position) and its
zone-input arrays. This replays those rounds through the coordinator code of
ROOT, a checkout of this repository with its extension built: each round's
requests are written into buffers as its game processes write them, and its
SharedEvaluatorServer.answer reads, groups, packs, evaluates and replies to
them, with the pipes replaced by in-memory stand-ins. The pipes' own cost is
not included.

It reports the time per round, the best of --repeat passes over all rounds, and
with --outputs saves every reply, so that two checkouts' replies can be
compared with --compare:

    python tools/replay_coordinator_rounds.py ROOT ROUNDS.pickle --weights W.pt --outputs OUT.pickle
    python tools/replay_coordinator_rounds.py --compare OLD.pickle NEW.pickle

--weights names a file of the three alliances' state dicts; --make-weights writes
one from fresh 64x2 networks whose three column tables are filled with random
numbers, since a fresh network's rows are all zero and would compare sums of
zeros. Run with one tensor thread, as the coordinator does, and with
MallocNanoZone unset, as training runs do.
"""
from __future__ import annotations

import argparse
import json
import pickle
import statistics
import sys
import time
from pathlib import Path


class _Pipe:
    """A game thread's end of the pipe, as the server sees it: replies are kept."""

    def __init__(self) -> None:
        self.replies = []

    def send(self, value) -> None:
        self.replies.append(value)


class _Buffer:
    def __init__(self, size: int) -> None:
        self.buf = memoryview(bytearray(size))


def _writer(shared_evaluator):
    """The checkout's way of writing a position's arrays into its buffer."""
    write = getattr(shared_evaluator, "write_arrays", None)
    if write is not None:
        return write
    import numpy as np

    def write_arrays(buffer, arrays):  # prepare_into's layout before write_arrays existed
        header, offset = [], 0
        for name, values in arrays.items():
            np.ndarray(values.shape, values.dtype, buffer=buffer, offset=offset)[...] = values
            header.append((name, values.dtype.str, values.shape, offset))
            offset += values.nbytes
        return header
    return write_arrays


def load_models(weights: Path):
    from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
    import torch
    saved = torch.load(weights, weights_only=True)
    models = {}
    for player, state in saved["models"].items():
        model = CampaignPolicyValueNet(CampaignModelConfig(**saved["config"]))
        model.load_state_dict(state)
        models[player] = model.eval()
    return models


def make_weights(path: Path, seed: int) -> None:
    import torch
    from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
    from studies.shared.multiplayer_mcts import PLAYERS
    torch.manual_seed(seed)
    config = {"hidden_dim": 64, "message_layers": 2}
    models = {}
    for player in PLAYERS:
        model = CampaignPolicyValueNet(CampaignModelConfig(**config))
        for table in (model.zone_columns, model.global_columns, model.option_columns):
            table.weight.data.normal_(0.0, 0.5)
        models[player] = model.state_dict()
    torch.save({"config": config, "seed": seed, "models": models}, path)


def replay(rounds, models, repeat: int, keep_outputs: bool):
    import torch
    from studies.campaign import shared_evaluator
    write = _writer(shared_evaluator)
    version = next(iter(models.values())).layout_version
    prepared = []
    for saved in rounds:
        requests, memories = [], {}
        for actor, count, arrays in saved:
            pipe, memory = _Pipe(), _Buffer(sum(values.nbytes for values in arrays.values()) + 4096)
            header = write(memory.buf, arrays)
            memories[pipe] = memory
            requests.append((pipe, (actor, count, version, header)))
        prepared.append((requests, memories))
    server = shared_evaluator.SharedEvaluatorServer(models, torch.device("cpu"), [], [])
    passes = []
    outputs = None
    for index in range(repeat + 1):  # The first pass warms up and is not timed.
        times = []
        for requests, memories in prepared:
            server.memories = memories
            started = time.perf_counter()
            server.answer(requests)
            times.append(time.perf_counter() - started)
        if index:
            passes.append(times)
        if keep_outputs and outputs is None:
            outputs = [[pipe.replies[-1] for pipe, _ in requests] for requests, _ in prepared]
    return passes, outputs


def compare(old_path: Path, new_path: Path) -> dict:
    import numpy as np
    old, new = pickle.loads(old_path.read_bytes()), pickle.loads(new_path.read_bytes())
    if len(old) != len(new):
        raise SystemExit("The two files hold different rounds")
    identical = replies = 0
    prior_error = value_error = relative_value_error = 0.0
    for old_round, new_round in zip(old, new):
        for (old_priors, old_values), (new_priors, new_values) in zip(old_round, new_round, strict=True):
            replies += 1
            same = old_priors == new_priors and old_values == new_values
            identical += same
            if not same:
                if len(old_priors) != len(new_priors):
                    raise SystemExit("A reply lists a different number of options")
                if old_priors:
                    prior_error = max(prior_error, float(np.max(np.abs(np.subtract(old_priors, new_priors)))))
                difference = np.abs(np.subtract(old_values, new_values))
                value_error = max(value_error, float(difference.max()))
                relative_value_error = max(relative_value_error,
                                           float((difference / np.maximum(np.abs(old_values), 1e-9)).max()))
    return {"replies": replies, "identical_replies": identical, "max_prior_difference": prior_error,
            "max_value_difference": value_error, "max_relative_value_difference": relative_value_error}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("rounds", nargs="?", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--make-weights", type=Path, help="Write random-filled weights to this file and stop")
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--limit", type=int, help="Replay only the first N rounds")
    parser.add_argument("--outputs", type=Path, help="Save every reply of the first pass here")
    parser.add_argument("--report", type=Path, help="Write the timing report here as JSON")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("OLD", "NEW"))
    args = parser.parse_args(argv)
    if args.compare:
        print(json.dumps(compare(*args.compare), indent=1))
        return 0
    if args.root is None:
        parser.error("Name the checkout to replay")
    sys.path.insert(0, str(args.root.resolve()))
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if args.make_weights:
        make_weights(args.make_weights, args.seed)
        return 0
    if args.rounds is None or args.weights is None:
        parser.error("Name the saved rounds and the weights")
    rounds = pickle.loads(args.rounds.read_bytes())
    if args.limit:
        rounds = rounds[:args.limit]
    models = load_models(args.weights)
    with torch.inference_mode():
        passes, outputs = replay(rounds, models, args.repeat, args.outputs is not None)
    totals = [sum(times) for times in passes]
    best = min(range(len(passes)), key=lambda index: totals[index])
    requests = sum(len(saved) for saved in rounds)
    report = {"root": str(args.root.resolve()), "rounds": len(rounds), "requests": requests,
              "pass_seconds": totals, "best_pass_seconds": totals[best],
              "best_us_per_round": totals[best] / len(rounds) * 1e6,
              "best_us_per_request": totals[best] / requests * 1e6,
              "median_round_us": statistics.median(passes[best]) * 1e6}
    print(json.dumps(report, indent=1))
    if args.report:
        args.report.write_text(json.dumps(report, indent=1))
    if args.outputs:
        args.outputs.write_bytes(pickle.dumps(outputs, protocol=pickle.HIGHEST_PROTOCOL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
