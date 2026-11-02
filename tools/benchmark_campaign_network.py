#!/usr/bin/env python3
"""Matched network measurements on fixed positions, for any checkout.

ROOT is a checkout of this repository with its extension built. The same
scripted games give the same positions in every checkout with the same rules,
and the report's planning-key digest shows whether two reports measured the
same positions. Checkouts before the zone encoding (such as d411d24) measure
the graph input and its network; later ones the zone input and its network.

    ./.venv/bin/python tools/benchmark_campaign_network.py . OUT.json --threads 1

It times input building, forward passes of fresh inputs one at a time and in
batches of 16, and training steps as CampaignLearner.update runs them. It
trains nothing beyond those steps and plays only two scripted games.
"""
import argparse
import hashlib
import json
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("root")
parser.add_argument("out")
parser.add_argument("--threads", type=int, default=1)
parser.add_argument("--seeds", type=int, nargs="+", default=[3101, 3102])
parser.add_argument("--rounds", type=int, default=11)
parser.add_argument("--stride", type=int, default=12)
parser.add_argument("--hidden", type=int, default=64)
parser.add_argument("--layers", type=int, default=2)
parser.add_argument("--buckets", type=int, default=16384)
parser.add_argument("--train-steps", type=int, default=12)
args = parser.parse_args()
sys.path.insert(0, args.root)

import torch  # noqa: E402

torch.set_num_threads(args.threads)
torch.set_num_interop_threads(1)

from studies.campaign import neural  # noqa: E402
from studies.campaign.baselines import baseline_distribution  # noqa: E402
from studies.campaign.curriculum import make_env  # noqa: E402
from studies.shared.multiplayer_mcts import PLAYERS  # noqa: E402

OLD = "token_buckets" in neural.CampaignModelConfig.__dataclass_fields__
if OLD:
    from studies.campaign.features import make_numeric_input
    from studies.campaign.learning import _value_only_input, retained_numeric_input

    config = neural.CampaignModelConfig(hidden_dim=args.hidden, message_layers=args.layers, token_buckets=args.buckets)

    def prepare(env, actions):
        return make_numeric_input(env, actions, args.buckets)

    def value_only(item):
        return _value_only_input(item)

    def stored_bytes(item):
        packed = retained_numeric_input(item)["packed_graph"]
        return packed["observation"].nbytes + sum(graph.nbytes for graph in packed["actions"])

    def count(item):
        return len(item["packed_graph"]["actions"])
else:
    from studies.campaign.features import make_zone_input

    config = neural.CampaignModelConfig(hidden_dim=args.hidden, message_layers=args.layers)

    def prepare(env, actions):
        return make_zone_input(env, actions)

    def value_only(item):
        return item.without_actions()

    def stored_bytes(item):
        return item.nbytes

    def count(item):
        return item.action_count


def positions():
    """Every stride-th decision of scripted games, with its owner."""
    found = []
    for seed in args.seeds:
        env = make_env(seed, calendar_rounds=args.rounds)
        step = 0
        while not env.is_terminal():
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            actions = list(env.legal_actions())
            step += 1
            if step % args.stride == 0:
                found.append((env.clone(), env.current_decision_player()))
            weights = baseline_distribution(env, actions)
            env.apply_action(actions[max(range(len(actions)), key=weights.__getitem__)])
    return found


def summary(values):
    ordered = sorted(values)
    return {"median": round(statistics.median(ordered), 4), "mean": round(statistics.fmean(ordered), 4),
            "p90": round(ordered[int(0.9 * (len(ordered) - 1))], 4), "max": round(ordered[-1], 4),
            "count": len(ordered)}


def fresh(found):
    """New inputs from new copies, so nothing is reused from an earlier pass."""
    items, seconds = [], []
    for env, _owner in found:
        copy = env.clone()
        actions = tuple(copy.legal_actions())
        started = time.perf_counter()
        items.append(prepare(copy, actions))
        seconds.append((time.perf_counter() - started) * 1000)
    return items, seconds


started = time.perf_counter()
found = positions()
keys = [env.planning_key() for env, _ in found]
torch.manual_seed(0)
models = {player: neural.CampaignPolicyValueNet(config).eval() for player in PLAYERS}
parameters = sum(p.numel() for p in models["axis"].parameters())
state_bytes = sum(t.numel() * t.element_size() for t in models["axis"].state_dict().values())

items, prepare_ms = fresh(found)
options = [count(item) for item in items]
sizes = [stored_bytes(item) for item in items]


def forward(model, batch):
    with torch.inference_mode():
        logits, values = (model.forward_batch(batch, model_version="bench") if OLD else model.forward_batch(batch))
        torch.cat([*logits, values.reshape(-1)]).sum().item()


# Warm-up on a separate pass, then one timed pass of fresh inputs per batch size.
warm, _ = fresh(found[:40])
for item in warm:
    forward(models["axis"], [item])
results = {}
for size in (1, 16):
    batch_items, _ = fresh(found)
    seconds = []
    for start in range(0, len(batch_items), size):
        chunk = batch_items[start:start + size]
        began = time.perf_counter()
        forward(models["axis"], chunk)
        seconds.append((time.perf_counter() - began) * 1000 / len(chunk))
    results[f"forward_ms_per_position_batch_{size}"] = summary(seconds)

# Training steps as CampaignLearner.update runs them: 32 replay rows, each
# model reads its own rows in full and the others' rows without options.
replay = list(zip(items, [owner for _, owner in found]))
rng = random.Random(5)
optimizers = {player: torch.optim.Adam(models[player].parameters(), lr=1e-3) for player in PLAYERS}
step_ms = []
for step in range(args.train_steps + 2):
    rows = rng.sample(replay, 32)
    for player in PLAYERS:
        model, optimizer = models[player], optimizers[player]
        model.train()
        began = time.perf_counter()
        optimizer.zero_grad(set_to_none=True)
        inputs = [item if owner == player else value_only(item) for item, owner in rows]
        logits, predicted = model.forward_batch(inputs)
        value_loss = torch.mean(predicted ** 2)
        terms = [-(torch.log_softmax(logits[i], 0).mean()) for i, (_, owner) in enumerate(rows) if owner == player]
        loss = value_loss + (torch.stack(terms).mean() if terms else 0)
        loss.backward()
        optimizer.step()
        if step >= 2:
            step_ms.append((time.perf_counter() - began) * 1000)
        model.eval()
results["train_step_ms_per_model_32_rows"] = summary(step_ms)

def sources():
    """The measured checkout: its commit, whether it was modified, and its network sources."""
    root = Path(args.root)
    run = lambda *command: subprocess.run(["git", "-C", str(root), *command], capture_output=True, text=True).stdout.strip()
    names = ["studies/campaign/neural.py", "studies/campaign/features.py", "studies/campaign/learning.py",
             "src/python_bindings.cpp", "src/zone_encoding.cpp", "src/neural_graph.cpp", "src/numeric_graph.cpp"]
    return {"commit": run("rev-parse", "HEAD"), "modified": bool(run("status", "--porcelain", "--untracked-files=no")),
            "sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                       for name in names if (root / name).exists()}}


report = {
    "input": "graph" if OLD else "zone", "source": sources(), "threads": args.threads,
    "config": {"hidden_dim": args.hidden, "message_layers": args.layers, **({"token_buckets": args.buckets} if OLD else {})},
    "seeds": args.seeds, "rounds": args.rounds, "stride": args.stride, "positions": len(found),
    "planning_keys_sha": __import__("hashlib").sha256("\n".join(keys).encode()).hexdigest(),
    "options_per_position": summary(options),
    "parameters": parameters, "state_dict_bytes": state_bytes,
    "stored_bytes_per_decision": summary(sizes),
    "prepare_ms_first_build": summary(prepare_ms),
    **results,
    "seconds": round(time.perf_counter() - started, 1),
}
Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
print(json.dumps(report, indent=1))
