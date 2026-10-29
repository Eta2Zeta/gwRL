#!/usr/bin/env python3
"""Time each stage of the shared GPU coordinator's model call on real positions.

A call merges the waiting positions' arrays, sends them to the device, issues
the network's tensor operations, waits for the device and reads the outputs
back; each stage is timed with the device drained after the operations are
issued. A second pass drains the device around each part of the network to
show where the device time goes. Positions come from seeded random play
across whole games. Run with the PyTorch environment that has MPS
(tmp/gpu-mps-env/bin/python) on an otherwise idle machine.
"""
from __future__ import annotations

import argparse
import random
import statistics as st
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", default="5000,5001,5002", help="Random-play games that supply positions")
    parser.add_argument("--sizes", default="1,4,10,32", help="Positions per model call to time")
    parser.add_argument("--repeats", type=int, default=150)
    parser.add_argument("--device", default="mps")
    args = parser.parse_args(argv)

    import numpy as np
    import torch
    from torch.utils._python_dispatch import TorchDispatchMode

    from studies.campaign import shared_evaluator as se
    from studies.campaign.curriculum import make_env
    from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet

    buckets = 16384
    torch.manual_seed(1951)
    device = torch.device(args.device)
    model = CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=64, message_layers=2, token_buckets=buckets,
                                                       value_scale=100.0)).eval().to(device)
    drain = torch.mps.synchronize if device.type == "mps" else (lambda: None)

    positions = []
    for seed in (int(text) for text in args.seeds.split(",")):
        env = make_env(seed, calendar_rounds=11)
        rng = random.Random(seed)
        for step in range(4000):
            if env.is_terminal():
                break
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            actions = list(env.legal_actions())
            if step % 9 == 0 and len(actions) > 1:
                positions.append(se.prepare(env, tuple(actions), buckets))
            ending = [a for a in actions if a.id.endswith(":play:end_phase")]
            env.apply_action(ending[0] if ending and rng.random() < 0.05 else rng.choice(actions))
    contexts = se._Contexts()
    for key, arrays, context in positions:
        contexts.arrays.setdefault(key, {**se._graph_arrays(context, "ctx_"),
                                         "ctx_nodes": np.asarray([context.node_count])})
    items = [(key, arrays) for key, arrays, _ in positions]
    print(f"{len(items)} positions, {st.mean(len(a['act_nodes']) for _, a in items):.1f} legal actions on average")

    marks: dict[str, float] = {}
    send = se._Transfer.send

    def timed_send(self, target):
        marks["merged"] = time.perf_counter()
        out = send(self, target)
        marks["sent"] = time.perf_counter()
        return out

    class Count(TorchDispatchMode):
        def __init__(self):
            super().__init__()
            self.operations = 0

        def __torch_dispatch__(self, func, types, args=(), kwargs=None):
            self.operations += 1
            return func(*args, **(kwargs or {}))

    def one(batch):
        started = time.perf_counter()
        outputs = se.forward_prepared(model, batch, contexts, device)
        issued = time.perf_counter()
        drain()
        finished = time.perf_counter()
        se.collect(model, *outputs)
        done = time.perf_counter()
        return {"merge": marks["merged"] - started, "send": marks["sent"] - marks["merged"],
                "issue": issued - marks["sent"], "device": finished - issued, "outputs": done - finished,
                "total": done - started}

    se._Transfer.send = timed_send
    sizes = [int(text) for text in args.sizes.split(",")]
    rng = random.Random(7)
    with torch.inference_mode():
        for _ in range(40):
            one(rng.sample(items, 4))
        for size in sizes:
            rows = [one(rng.sample(items, size)) for _ in range(args.repeats)]
            with Count() as counter:
                se.forward_prepared(model, rng.sample(items, size), contexts, device)
            drain()
            mean = {name: st.mean(row[name] for row in rows) * 1000 for name in rows[0]}
            print(f"{size:>2} positions: " + ", ".join(f"{name} {value:.2f} ms" for name, value in mean.items())
                  + f"; {mean['total'] / size:.2f} ms per position; {counter.operations} tensor operations")

        # Device time by part of the network, draining before and after each part.
        encode, factored, parts, calls = se._encode, se._factored, {}, []

        def timed(name, function):
            def run(*call_args, **call_kwargs):
                drain()
                began = time.perf_counter()
                out = function(*call_args, **call_kwargs)
                drain()
                parts[name] = parts.get(name, 0.0) + time.perf_counter() - began
                return out
            return run

        def which_encode(*call_args, **call_kwargs):
            calls.append(None)  # The observation graph is encoded before the action graphs.
            name = "observation graph" if len(calls) % 2 else "action graphs"
            return timed(name, encode)(*call_args, **call_kwargs)

        se._encode, se._factored = which_encode, timed("factored policy", factored)
        for size in sizes:
            parts.clear()
            calls.clear()
            rows = [one(rng.sample(items, size)) for _ in range(args.repeats)]
            total = st.mean(row["total"] for row in rows) * 1000
            print(f"{size:>2} positions, drained between parts: total {total:.2f} ms; "
                  + ", ".join(f"{name} {seconds / args.repeats * 1000:.2f} ms" for name, seconds in parts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
