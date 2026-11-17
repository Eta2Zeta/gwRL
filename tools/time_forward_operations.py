#!/usr/bin/env python3
"""Time each PyTorch operation of the inference server's forward pass on real inference batches.

tools/profile_coordinator.py --save-every N keeps every Nth inference batch of a
training iteration: each inference request's alliance (None at a chance state)
and its zone-input arrays. This merges --merge consecutive saved inference
batches into one, collates it as the inference server does (pack_zone_arrays
in studies/campaign/features.py) and runs the three networks' forward pass
(NetworkStack.forward_packed in studies/campaign/neural.py) on --device under
a dispatch mode that times every operation PyTorch's dispatcher runs: it waits
for the device, runs the operation --repeat times, waits again and divides.
One PyTorch call runs one or more such operations. Waiting before and after
each operation adds its own time, so the operations' sum exceeds the forward
pass timed without the dispatch mode, which is reported beside it.

Each operation is put in one part of the forward pass: the per-border work,
any operation with an input or output of one row per border of each state
(gathering each border's source zone, adding the border's own terms, GELU,
summing the messages into their target zones); the linear layers; and the
rest. Values computed under the dispatch mode are not used: operations that
change an array in place run --repeat times.

    python tools/time_forward_operations.py ROUNDS.pickle WEIGHTS.pt --merge 8 --device mps --out OUT.json

WEIGHTS is a file of the three alliances' state dicts, as
tools/replay_coordinator_rounds.py --make-weights writes. Run with
MallocNanoZone unset, as training runs do.
"""
from __future__ import annotations

import argparse
import collections
import json
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLIANCES = ("axis", "allies", "comintern")


def _wait(torch, device) -> None:
    if device.type == "mps":
        torch.mps.synchronize()
    elif device.type == "cuda":
        torch.cuda.synchronize(device)


def _rows(value) -> int:
    shape = getattr(value, "shape", None)
    return int(shape[0]) if shape is not None and len(shape) else 0


def time_operations(torch, device, repeat: int, forward, border_rows: int, width: int) -> dict:
    """Seconds of each operation of one call of forward(), by operation and by part.

    An operation belongs to the per-border work if an input or output has a row
    per border of each state, or as many numbers as one vector of `width` per border."""
    from torch.utils._python_dispatch import TorchDispatchMode

    class Timer(TorchDispatchMode):
        def __init__(self) -> None:
            super().__init__()
            self.calls = []

        def __torch_dispatch__(self, func, types, args=(), kwargs=None):
            kwargs = kwargs or {}
            _wait(torch, device)
            started = time.perf_counter()
            for _ in range(repeat):
                out = func(*args, **kwargs)
            _wait(torch, device)
            spent = (time.perf_counter() - started) / repeat
            arrays = [value for value in (*args, *kwargs.values()) if isinstance(value, torch.Tensor)]
            outputs = out if isinstance(out, (tuple, list)) else (out,)
            tensors = [value for value in (*arrays, *outputs) if isinstance(value, torch.Tensor)]
            per_border = any(_rows(value) == border_rows or value.numel() == border_rows * width
                             for value in tensors)
            name = func.__name__
            part = ("per-border work" if per_border else
                    "linear layers" if name.split(".")[0] in ("linear", "addmm", "mm", "bmm", "baddbmm") else
                    "the rest")
            shape = list(out.shape) if isinstance(out, torch.Tensor) else None
            self.calls.append((name, shape, part, spent))
            return out

    timer = Timer()
    with timer:
        forward()
    by_operation = collections.defaultdict(lambda: [0.0, 0])
    by_part = collections.defaultdict(float)
    for name, _, part, spent in timer.calls:
        by_operation[name][0] += spent
        by_operation[name][1] += 1
        by_part[part] += spent
    return {"operations": len(timer.calls), "seconds": sum(by_part.values()),
            "by_operation": {name: {"seconds": seconds, "count": count}
                             for name, (seconds, count) in by_operation.items()},
            "by_part": dict(by_part),
            "largest": sorted(([name, shape, part, spent] for name, shape, part, spent in timer.calls),
                              key=lambda item: -item[3])[:40]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("rounds", type=Path, help="Inference batches saved by tools/profile_coordinator.py")
    parser.add_argument("weights", type=Path)
    parser.add_argument("--merge", type=int, default=1, help="Merge this many consecutive saved inference batches")
    parser.add_argument("--device", default="mps")
    parser.add_argument("--inference-batches", type=int, default=3,
                        help="How many merged inference batches to time, spread over the run")
    parser.add_argument("--repeat", type=int, default=20, help="Runs of each operation between two waits")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    import torch
    torch.set_num_threads(1)
    from studies.campaign.features import pack_zone_arrays
    from studies.campaign.neural import (CampaignModelConfig, CampaignPolicyValueNet, NetworkStack,
                                         resolve_neural_device)
    device = resolve_neural_device(args.device)
    saved = torch.load(args.weights, weights_only=True)
    models = []
    for alliance in ALLIANCES:
        model = CampaignPolicyValueNet(CampaignModelConfig(**saved["config"]), device=device)
        model.load_state_dict(saved["models"][alliance])
        models.append(model.eval())
    stack = NetworkStack(models)
    saved_batches = pickle.loads(args.rounds.read_bytes())
    merged = [[request for batch in saved_batches[start:start + args.merge] for request in batch]
              for start in range(0, len(saved_batches) - args.merge + 1, args.merge)]
    chosen = merged[::max(1, len(merged) // args.inference_batches)][:args.inference_batches]
    timed = []
    with torch.inference_mode():
        for requests in chosen:
            rows = {alliance: [] for alliance in ALLIANCES}
            for row, (actor, _, _) in enumerate(requests):
                for alliance in (ALLIANCES if actor is None else (actor,)):
                    rows[alliance].append(row)
            order = [row for alliance in ALLIANCES for row in rows[alliance]]
            batch = pack_zone_arrays([requests[row][2] for row in order], stack.spec,
                                     [len(rows[alliance]) for alliance in ALLIANCES])
            for _ in range(2):  # Warm-up: the device's own caches for these shapes.
                stack.forward_packed(batch)
            _wait(torch, device)
            started = time.perf_counter()
            stack.forward_packed(batch)
            _wait(torch, device)
            forward_seconds = time.perf_counter() - started
            result = time_operations(torch, device, args.repeat, lambda: stack.forward_packed(batch),
                                     batch.positions * len(stack.spec.edge_source), stack.config.hidden_dim)
            timed.append({"states": batch.positions, "network_states": batch.network_positions,
                          "forward_pass_seconds": forward_seconds, **result})
    count = len(timed)
    parts = collections.defaultdict(float)
    for entry in timed:
        for part, seconds in entry["by_part"].items():
            parts[part] += seconds
    total = sum(parts.values())
    report = {"weights": str(args.weights), "config": saved["config"], "device": str(device),
              "torch": torch.__version__, "merge": args.merge, "repeat": args.repeat,
              "states_per_inference_batch": sum(entry["states"] for entry in timed) / count,
              "forward_pass_ms": 1e3 * sum(entry["forward_pass_seconds"] for entry in timed) / count,
              "operations_ms": 1e3 * total / count,
              "share_by_part": {part: seconds / total for part, seconds in parts.items()},
              "inference_batches": timed}
    summary = {key: value for key, value in report.items() if key != "inference_batches"}
    print(json.dumps(summary, indent=1))
    if args.out:
        args.out.write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
