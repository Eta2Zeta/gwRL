#!/usr/bin/env python3
"""Network cost by size, positions per pass and device, through the coordinator's own code.

ROOT is a checkout of this repository with its extension built. Positions are
every --stride-th decision of two scripted eleven-round games. For each network
size (width x message layers) the three alliance networks are built with their
column tables filled with small random numbers, stacked as the coordinator
stacks them (neural.NetworkStack), and passes are timed through
shared_evaluator.forward_prepared and collect: laying the positions out, the
pass, and the outputs' copy to the host with the softmax there. A pass's
positions are a random sample, grouped by the alliance that decides. Each cell
is the median pass over --seconds or 400 passes, after two passes of warm-up.
It also times training steps of one network (forward, backward, Adam) with a
stand-in loss, the squared outputs, on --train-rows decisions.

    tmp/gpu-mps-env/bin/python tools/benchmark_network_sizes.py . OUT.json --device mps
    tmp/gpu-mps-env/bin/python tools/benchmark_network_sizes.py . OUT.json --device cpu --threads 1

Run with MallocNanoZone unset, as training runs do. Measured in
docs/archive/records/network_and_search_cost_2026_11_14.md.
"""
import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("root")
parser.add_argument("out")
parser.add_argument("--device", default="cpu")
parser.add_argument("--threads", type=int, default=1)
parser.add_argument("--sizes", nargs="+", default=["64x2", "128x4", "256x8", "384x12", "512x16"])
parser.add_argument("--batches", type=int, nargs="+", default=[1, 4, 16, 64, 256])
parser.add_argument("--seconds", type=float, default=2.0)
parser.add_argument("--train-rows", type=int, default=128)
parser.add_argument("--train-steps", type=int, default=6)
parser.add_argument("--stride", type=int, default=6)
args = parser.parse_args()
sys.path.insert(0, args.root)

import torch  # noqa: E402

torch.set_num_threads(args.threads)
torch.set_num_interop_threads(1)

from studies.campaign import neural  # noqa: E402
from studies.campaign.baselines import baseline_distribution  # noqa: E402
from studies.campaign.curriculum import make_env  # noqa: E402
from studies.campaign.features import make_zone_input  # noqa: E402
from studies.campaign.shared_evaluator import collect, forward_prepared  # noqa: E402  (the coordinator's path)
from studies.shared.multiplayer_mcts import PLAYERS  # noqa: E402

device = neural.resolve_neural_device(args.device)


def positions():
    found = []
    for seed in (3101, 3102):
        env = make_env(seed, calendar_rounds=11)
        step = 0
        while not env.is_terminal():
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            actions = list(env.legal_actions())
            step += 1
            if step % args.stride == 0:
                found.append((make_zone_input(env, actions), env.current_decision_player()))
            weights = baseline_distribution(env, actions)
            env.apply_action(actions[max(range(len(actions)), key=weights.__getitem__)])
    return found


began = time.perf_counter()
found = positions()
arrays = [(item.arrays(), owner) for item, owner in found]
options = sorted(len(a["action_source"]) for a, _ in arrays)
rng = random.Random(7)


def batch_of(size):
    chosen = rng.sample(arrays, size) if size <= len(arrays) else [rng.choice(arrays) for _ in range(size)]
    grouped = [item for player in PLAYERS for item, owner in chosen if owner == player]
    counts = [sum(1 for _, owner in chosen if owner == player) for player in PLAYERS]
    return grouped, counts


def sync():
    neural.synchronize_neural_device(device)


def make_models(hidden, layers):
    torch.manual_seed(0)
    config = neural.CampaignModelConfig(hidden_dim=hidden, message_layers=layers)
    models = []
    for _ in PLAYERS:
        model = neural.CampaignPolicyValueNet(config, device=device).eval()
        with torch.no_grad():
            for table in (model.zone_columns, model.global_columns, model.option_columns):
                table.weight.normal_(0.0, 0.05)
        models.append(model)
    return models


report = {"device": str(device), "threads": args.threads, "torch": torch.__version__,
          "positions": len(arrays), "options_median": statistics.median(options),
          "options_p90": options[int(0.9 * (len(options) - 1))], "sizes": {}}

for size in args.sizes:
    hidden, layers = (int(part) for part in size.split("x"))
    models = make_models(hidden, layers)
    parameters = sum(p.numel() for p in models[0].parameters())
    table_parameters = sum(m.weight.numel() for m in (models[0].zone_columns, models[0].global_columns,
                                                       models[0].option_columns))
    stack = neural.NetworkStack(models)
    cells = {}
    for count in args.batches:
        batches = [batch_of(count) for _ in range(6)]
        with torch.inference_mode():
            for items, counts in batches[:2]:  # warm-up
                collect(stack, *forward_prepared(stack, items, device, counts))
            times, done, start = [], 0, time.perf_counter()
            while done < 3 or (time.perf_counter() - start < args.seconds and done < 400):
                items, counts = batches[done % len(batches)]
                t0 = time.perf_counter()
                collect(stack, *forward_prepared(stack, items, device, counts))
                times.append(time.perf_counter() - t0)
                done += 1
        median = statistics.median(times)
        cells[str(count)] = {"passes": done, "ms_per_pass": round(median * 1000, 3),
                             "positions_per_second": round(count / median, 1)}
        print(size, count, cells[str(count)], flush=True)
    # Training steps of one network on train_rows decisions: forward, backward, Adam.
    model = models[0]
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    step_times = []
    for step in range(args.train_steps + 2):
        rows = [item for item, _ in rng.sample(found, args.train_rows)]
        sync()
        t0 = time.perf_counter()
        optimizer.zero_grad(set_to_none=True)
        logits, values = model.forward_batch(rows)
        loss = (values ** 2).mean() + torch.cat(logits).pow(2).mean()
        loss.backward()
        optimizer.step()
        sync()
        if step >= 2:
            step_times.append(time.perf_counter() - t0)
    model.eval()
    step = statistics.median(step_times)
    report["sizes"][size] = {"hidden": hidden, "layers": layers, "parameters": parameters,
                             "table_parameters": table_parameters, "passes": cells,
                             "train_ms_per_step": round(step * 1000, 2), "train_rows": args.train_rows,
                             "train_rows_per_second": round(args.train_rows / step, 1)}
    print(size, "train", report["sizes"][size]["train_ms_per_step"], "ms/step", flush=True)
    del stack, models, model, optimizer
    if device.type == "mps":
        torch.mps.empty_cache()

report["seconds"] = round(time.perf_counter() - began, 1)
Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
