#!/usr/bin/env python3
"""Time each stage of the shared GPU coordinator's model call on real positions.

A call lays the waiting positions' zone inputs out as one batch, sends it to
the device, issues the network's tensor operations, waits for the device and
reads the outputs back; each stage is timed with the device drained after the
operations are issued. A second pass drains the device around each part of the
network to show where the device time goes. Positions come from seeded random
play across whole games. Run with the PyTorch environment that has MPS
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

    import torch
    from torch.utils._python_dispatch import TorchDispatchMode

    from studies.campaign import neural, shared_evaluator as se
    from studies.campaign.curriculum import make_env
    from studies.campaign.features import make_zone_input
    from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet

    torch.manual_seed(1951)
    device = torch.device(args.device)
    model = CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=64, message_layers=2,
                                                       value_scale=100.0)).eval().to(device)
    drain = torch.mps.synchronize if device.type == "mps" else (lambda: None)

    items = []
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
                # The arrays a game thread writes into its shared buffer.
                items.append(make_zone_input(env, tuple(actions)).arrays())
            ending = [a for a in actions if a.id.endswith(":play:end_phase")]
            env.apply_action(ending[0] if ending and rng.random() < 0.05 else rng.choice(actions))
    print(f"{len(items)} positions, {st.mean(len(a['action_source']) for a in items):.1f} legal actions on average")

    marks: dict[str, float] = {}
    send = neural.batch_tensors

    def timed_send(batch, target, **kwargs):
        marks["merged"] = time.perf_counter()
        out = send(batch, target, **kwargs)
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
        outputs = se.forward_prepared(model, batch, device)
        issued = time.perf_counter()
        drain()
        finished = time.perf_counter()
        se.collect(model, *outputs)
        done = time.perf_counter()
        return {"merge": marks["merged"] - started, "send": marks["sent"] - marks["merged"],
                "issue": issued - marks["sent"], "device": finished - issued, "outputs": done - finished,
                "total": done - started}

    neural.batch_tensors = timed_send
    sizes = [int(text) for text in args.sizes.split(",")]
    rng = random.Random(7)
    with torch.inference_mode():
        for _ in range(40):
            one(rng.sample(items, 4))
        for size in sizes:
            rows = [one(rng.sample(items, size)) for _ in range(args.repeats)]
            with Count() as counter:
                se.forward_prepared(model, rng.sample(items, size), device)
            drain()
            mean = {name: st.mean(row[name] for row in rows) * 1000 for name in rows[0]}
            print(f"{size:>2} positions: " + ", ".join(f"{name} {value:.2f} ms" for name, value in mean.items())
                  + f"; {mean['total'] / size:.2f} ms per position; {counter.operations} tensor operations")

        # Device time by part of the network, draining before and after each part.
        bag, parts, began = neural._bag, {}, {}

        def timed(name, function):
            def run(*call_args, **call_kwargs):
                drain()
                started = time.perf_counter()
                out = function(*call_args, **call_kwargs)
                drain()
                parts[name] = parts.get(name, 0.0) + time.perf_counter() - started
                return out
            return run

        tables = {id(model.zone_columns.weight): "zone answers", id(model.global_columns.weight): "position answers",
                  id(model.option_columns.weight): "option answers"}

        def which_bag(table, *call_args):
            return timed(tables[id(table)], bag)(table, *call_args)

        # A message-passing layer runs from its message to its position update.
        def layer_started(*_):
            drain()
            began["layer"] = time.perf_counter()

        def layer_finished(*_):
            drain()
            parts["message passing"] = parts.get("message passing", 0.0) + time.perf_counter() - began["layer"]

        for message, position_update in zip(model.messages, model.position_updates, strict=True):
            message.register_forward_pre_hook(layer_started)
            position_update.register_forward_hook(layer_finished)
        neural._bag, model._factored = which_bag, timed("factored policy", model._factored)
        for size in sizes:
            parts.clear()
            rows = [one(rng.sample(items, size)) for _ in range(args.repeats)]
            total = st.mean(row["total"] for row in rows) * 1000
            print(f"{size:>2} positions, drained between parts: total {total:.2f} ms; "
                  + ", ".join(f"{name} {seconds / args.repeats * 1000:.2f} ms" for name, seconds in parts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
