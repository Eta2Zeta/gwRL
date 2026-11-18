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

It reports the time per round, the best of --repeat passes over all rounds, with
each round's time split into its steps: reading the requests' arrays
(read_arrays), laying the positions out (pack_zone_arrays), making the pass's
calls (neural._forward, which on a GPU returns once the calls are handed over),
collecting the outputs (collect: on a GPU, waiting for it and copying the
outputs back, then the priors) and the rest of answering (grouping by alliance,
chance averages, the replies to the stand-in pipes). With --outputs it saves
every reply, so that two runs' replies can be compared with --compare:

    python tools/replay_coordinator_rounds.py ROOT ROUNDS.pickle --weights W.pt --outputs OUT.pickle
    python tools/replay_coordinator_rounds.py --compare OLD.pickle NEW.pickle

--device runs the networks on another device, such as mps or cuda. --merge K
answers K consecutive saved rounds together, as one round, to see larger passes
of real positions. --networks one gives every position to the Axis network, so
that one network evaluates the same positions, as one network shared by the
three alliances would; --networks padded also adds copies of the round's
positions, in order, up to three times as many as its largest network has, so
that one network evaluates as many positions as a layout padding each network
to the largest network's count would hold. --autocast float16 or bfloat16 runs
every pass under PyTorch's automatic mixed precision, which does matrix products in half
precision. --compile runs one network's zone and position layers compiled for
fixed numbers of states, as the inference server does with --compiled-forward
(with --networks one; neural.compiled_state_layers), and reports how often it
compiled. --weights names a file of the three alliances' state dicts;
--make-weights writes one from fresh networks of --hidden-dim and
--message-layers whose three column tables are filled with random numbers,
since a fresh network's rows are all zero and would compare sums of zeros. Run
with one tensor thread, as the coordinator does, and with MallocNanoZone unset,
as training runs do.
"""
from __future__ import annotations

import argparse
import json
import pickle
import statistics
import sys
import time
from pathlib import Path

STEPS = ("reading", "laying_out", "making_calls", "collecting")


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


class _StepTimes:
    """Seconds spent in each timed step of answering, since the last reset."""

    def __init__(self) -> None:
        self.seconds = dict.fromkeys(STEPS, 0.0)

    def reset(self) -> dict[str, float]:
        spent, self.seconds = self.seconds, dict.fromkeys(STEPS, 0.0)
        return spent

    def wrap(self, module, name: str, step: str) -> None:
        function = getattr(module, name)

        def timed(*args, **kwargs):
            started = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                self.seconds[step] += time.perf_counter() - started
        setattr(module, name, timed)


def load_models(weights: Path, device):
    from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
    import torch
    saved = torch.load(weights, weights_only=True)
    models = {}
    for player, state in saved["models"].items():
        model = CampaignPolicyValueNet(CampaignModelConfig(**saved["config"]), device=device)
        model.load_state_dict(state)
        models[player] = model.eval()
    return models, saved["config"]


def make_weights(path: Path, seed: int, hidden_dim: int, message_layers: int) -> None:
    import torch
    from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
    from studies.shared.multiplayer_mcts import PLAYERS
    torch.manual_seed(seed)
    config = {"hidden_dim": hidden_dim, "message_layers": message_layers}
    models = {}
    for player in PLAYERS:
        model = CampaignPolicyValueNet(CampaignModelConfig(**config))
        for table in (model.zone_columns, model.global_columns, model.option_columns):
            table.weight.data.normal_(0.0, 0.5)
        models[player] = model.state_dict()
    torch.save({"config": config, "seed": seed, "models": models}, path)


def merge_rounds(rounds, merge: int):
    """Every `merge` consecutive rounds as one round; a shorter tail is left out."""
    if merge <= 1:
        return rounds
    return [[request for saved in rounds[start:start + merge] for request in saved]
            for start in range(0, len(rounds) - merge + 1, merge)]


def one_network(rounds, padded: bool):
    """Every position of each round given to the Axis network; with `padded`, followed
    by copies of the round's positions, in order, up to three times as many as the
    round's largest network has (a chance position counts once for each network)."""
    alliances = ("axis", "allies", "comintern")
    changed = []
    for saved in rounds:
        one = [("axis", count, arrays) for _, count, arrays in saved]
        if padded:
            counts = dict.fromkeys(alliances, 0)
            for actor, _, _ in saved:
                for alliance in (alliances if actor is None else (actor,)):
                    counts[alliance] += 1
            one += [one[index % len(one)] for index in range(3 * max(counts.values()) - len(one))]
        changed.append(one)
    return changed


def positions_in(saved) -> int:
    """A round's positions in its pass: a chance position counts once for each of the three networks."""
    return sum(3 if actor is None else 1 for actor, _, _ in saved)


def replay(rounds, models, device, repeat: int, keep_outputs: bool, autocast: str | None,
           compiled: bool = False):
    import contextlib
    import torch
    from studies.campaign import features, neural, shared_evaluator
    write = _writer(shared_evaluator)
    version = next(iter(models.values())).layout_version
    steps = _StepTimes()
    steps.wrap(shared_evaluator, "read_arrays", "reading")
    steps.wrap(features, "pack_zone_arrays", "laying_out")
    steps.wrap(neural, "_forward", "making_calls")
    steps.wrap(shared_evaluator, "collect", "collecting")
    prepared = []
    for saved in rounds:
        requests, memories = [], {}
        for actor, count, arrays in saved:
            pipe, memory = _Pipe(), _Buffer(sum(values.nbytes for values in arrays.values()) + 4096)
            header = write(memory.buf, arrays)
            memories[pipe] = memory
            requests.append((pipe, (actor, count, version, header)))
        prepared.append((requests, memories))
    server = shared_evaluator.SharedEvaluatorServer(models, device, [], [], compiled_forward=compiled)
    mixed = (torch.autocast(device_type=device.type, dtype=getattr(torch, autocast))
             if autocast else contextlib.nullcontext())
    passes, outputs, warm_up = [], None, 0.0
    for index in range(repeat + 1):  # The first pass warms up and is not timed.
        rows, began = [], time.perf_counter()
        for requests, memories in prepared:
            server.memories = memories
            steps.reset()
            started = time.perf_counter()
            with mixed:
                server.answer(requests)
            total = time.perf_counter() - started
            rows.append((total, steps.reset()))
        if index:
            passes.append(rows)
        else:
            warm_up = time.perf_counter() - began
        if keep_outputs and outputs is None:
            outputs = [[pipe.replies[-1] for pipe, _ in requests] for requests, _ in prepared]
    return passes, outputs, warm_up


def _fit(xs, ys):
    """Least-squares line y = a + b x."""
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    spread = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / spread if spread else 0.0
    return mean_y - slope * mean_x, slope


def report_of(rounds, passes, *, root: Path, device, config, merge: int, autocast: str | None,
              compiled: bool, warm_up: float) -> dict:
    import torch
    totals = [sum(total for total, _ in rows) for rows in passes]
    best = min(range(len(passes)), key=lambda index: totals[index])
    rows = passes[best]
    requests = sum(len(saved) for saved in rounds)
    positions = [positions_in(saved) for saved in rounds]
    per_round = {step: statistics.fmean(spent[step] for _, spent in rows) * 1e6 for step in STEPS}
    per_round["rest"] = statistics.fmean(total - sum(spent.values()) for total, spent in rows) * 1e6
    intercept, slope = _fit(positions, [total * 1e6 for total, _ in rows])
    calls_intercept, calls_slope = _fit(positions, [spent["making_calls"] * 1e6 for _, spent in rows])
    return {"root": str(root), "device": str(device), "torch": torch.__version__,
            "threads": torch.get_num_threads(), "config": config, "merge": merge, "autocast": autocast,
            "compiled": compiled, "warm_up_seconds": warm_up, **_compile_counts(compiled),
            "rounds": len(rounds), "requests": requests, "positions": sum(positions),
            "positions_per_round": sum(positions) / len(rounds),
            "pass_seconds": totals, "best_pass_seconds": totals[best],
            "best_us_per_round": totals[best] / len(rounds) * 1e6,
            "best_us_per_request": totals[best] / requests * 1e6,
            "best_us_per_position": totals[best] / sum(positions) * 1e6,
            "median_round_us": statistics.median(total for total, _ in rows) * 1e6,
            "steps_us_per_round": per_round,
            "fit_us": {"round": {"fixed": intercept, "per_position": slope},
                       "making_calls": {"fixed": calls_intercept, "per_position": calls_slope}},
            "per_round": [[len(saved), count, round(total * 1e6, 1)]
                          + [round(spent[step] * 1e6, 1) for step in STEPS]
                          for saved, count, (total, spent) in zip(rounds, positions, rows)],
            "per_round_columns": ["requests", "positions", "total_us", *[f"{step}_us" for step in STEPS]]}


def _compile_counts(compiled: bool) -> dict:
    if not compiled:
        return {}
    from torch._dynamo.utils import counters
    return {"compile_counters": {group: dict(values) for group, values in counters.items()
                                 if group in ("stats", "graph_break", "recompiles")}}


def compare(old_path: Path, new_path: Path) -> dict:
    import numpy as np
    old, new = pickle.loads(old_path.read_bytes()), pickle.loads(new_path.read_bytes())
    if len(old) != len(new):
        raise SystemExit("The two files hold different rounds")
    identical = replies = top_changed = with_options = 0
    prior_error = value_error = relative_value_error = prior_sum = 0.0
    for old_round, new_round in zip(old, new):
        for (old_priors, old_values), (new_priors, new_values) in zip(old_round, new_round, strict=True):
            replies += 1
            same = old_priors == new_priors and old_values == new_values
            identical += same
            if len(old_priors) != len(new_priors):
                raise SystemExit("A reply lists a different number of options")
            if old_priors:
                with_options += 1
                top_changed += int(np.argmax(old_priors) != np.argmax(new_priors))
            if not same:
                if old_priors:
                    difference = np.abs(np.subtract(old_priors, new_priors))
                    prior_error = max(prior_error, float(difference.max()))
                    prior_sum += float(difference.max())
                difference = np.abs(np.subtract(old_values, new_values))
                value_error = max(value_error, float(difference.max()))
                relative_value_error = max(relative_value_error,
                                           float((difference / np.maximum(np.abs(old_values), 1e-9)).max()))
    return {"replies": replies, "identical_replies": identical, "max_prior_difference": prior_error,
            "mean_largest_prior_difference": prior_sum / with_options if with_options else 0.0,
            "replies_with_options": with_options, "most_likely_move_changed": top_changed,
            "max_value_difference": value_error, "max_relative_value_difference": relative_value_error}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("rounds", nargs="?", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--make-weights", type=Path, help="Write random-filled weights to this file and stop")
    parser.add_argument("--hidden-dim", type=int, default=64, help="Width of the networks --make-weights writes")
    parser.add_argument("--message-layers", type=int, default=2, help="Message layers of those networks")
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument("--device", default="cpu", help="Where the networks run: cpu, mps or cuda")
    parser.add_argument("--threads", type=int, default=1, help="PyTorch's CPU threads, 1 as in the coordinator")
    parser.add_argument("--merge", type=int, default=1, help="Answer this many consecutive saved rounds as one")
    parser.add_argument("--networks", choices=("three", "one", "padded"), default="three",
                        help="Replay the rounds as saved, through one network, or through one network "
                             "over as many positions as a padded layout of the three would hold")
    parser.add_argument("--autocast", choices=("float16", "bfloat16"),
                        help="Run every pass under automatic mixed precision of this type")
    parser.add_argument("--compile", action="store_true",
                        help="Compile one network's zone and position layers for fixed numbers of states")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--limit", type=int, help="Replay only the first N rounds, after merging")
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
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    if args.make_weights:
        make_weights(args.make_weights, args.seed, args.hidden_dim, args.message_layers)
        return 0
    if args.rounds is None or args.weights is None:
        parser.error("Name the saved rounds and the weights")
    from studies.campaign.neural import resolve_neural_device
    device = resolve_neural_device(args.device)
    rounds = merge_rounds(pickle.loads(args.rounds.read_bytes()), args.merge)
    if args.limit:
        rounds = rounds[:args.limit]
    if args.networks != "three":
        rounds = one_network(rounds, padded=args.networks == "padded")
    models, config = load_models(args.weights, device)
    if args.networks != "three":  # One network serves all three alliances: the Axis network.
        models = dict.fromkeys(models, models["axis"])
    if args.compile and args.networks == "three":
        parser.error("--compile compiles one network: add --networks one")
    with torch.inference_mode():
        passes, outputs, warm_up = replay(rounds, models, device, args.repeat, args.outputs is not None,
                                          args.autocast, args.compile)
    report = report_of(rounds, passes, root=args.root.resolve(), device=device, config=config,
                       merge=args.merge, autocast=args.autocast, compiled=args.compile, warm_up=warm_up)
    report["networks"] = args.networks
    summary = {key: value for key, value in report.items() if key not in ("per_round", "pass_seconds")}
    print(json.dumps(summary, indent=1))
    if args.report:
        args.report.write_text(json.dumps(report, indent=1))
    if args.outputs:
        args.outputs.write_bytes(pickle.dumps(outputs, protocol=pickle.HIGHEST_PROTOCOL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
