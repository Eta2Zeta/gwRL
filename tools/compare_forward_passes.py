#!/usr/bin/env python3
"""Time the inference server's forward pass of an earlier revision against the checkout's.

Both run in one process on the same saved inference batches, alternating, so
that a busier or quieter Mac weighs on both alike. --old-root names a copy of
the earlier revision (git archive REV | tar -x -C DIR, with the compiled engine
module copied in); its studies/campaign/neural.py is loaded beside the
checkout's. One network serves every state, with the same weights in both: a
fresh network whose three column tables are filled with random numbers, since a
fresh network's rows are zero. --compiled runs the checkout's zone and position
layers compiled for fixed numbers of states (neural.compiled_state_layers).

    tmp/gpu-mps-env/bin/python tools/compare_forward_passes.py --old-root OLD \\
        --rounds ROUNDS.pickle --device mps --hidden-dim 256 --message-layers 8 --merge 8 --compiled --out OUT.json

The saved inference batches come from tools/profile_coordinator.py --save-every.
The first run of each side includes its warm-up, and for a compiled pass its
compilations; the report gives every run's time and the best of the others.
Run with one tensor thread, as the inference server does, and with
MallocNanoZone unset, as training does.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pickle
import statistics
import sys
import time
from pathlib import Path


def load_old(root: Path):
    spec = importlib.util.spec_from_file_location("studies.campaign.neural_earlier",
                                                  root / "studies" / "campaign" / "neural.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--old-root", type=Path, required=True, help="A copy of the earlier revision")
    parser.add_argument("--rounds", type=Path, required=True, help="Saved inference batches")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--message-layers", type=int, default=2)
    parser.add_argument("--merge", type=int, default=1, help="Answer this many saved inference batches as one")
    parser.add_argument("--limit", type=int, help="Only the first N inference batches, after merging")
    parser.add_argument("--repeat", type=int, default=4, help="Runs of each side, the first one included")
    parser.add_argument("--compiled", action="store_true", help="Compile the checkout's zone and position layers")
    parser.add_argument("--seed", type=int, default=20261118)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # The checkout's studies package.
    import torch
    from studies.campaign import neural
    from studies.campaign.features import default_zone_spec, pack_zone_arrays
    torch.set_num_threads(1)
    old = load_old(args.old_root)
    saved = pickle.loads(args.rounds.read_bytes())
    if args.merge > 1:
        saved = [[request for part in saved[start:start + args.merge] for request in part]
                 for start in range(0, len(saved) - args.merge + 1, args.merge)]
    batches = [[arrays for _, _, arrays in part] for part in saved[:args.limit]]
    spec = default_zone_spec()
    torch.manual_seed(args.seed)
    config = {"hidden_dim": args.hidden_dim, "message_layers": args.message_layers}
    new_model = neural.CampaignPolicyValueNet(neural.CampaignModelConfig(**config))
    for table in (new_model.zone_columns, new_model.global_columns, new_model.option_columns):
        table.weight.data.normal_(0.0, 0.5)
    old_model = old.CampaignPolicyValueNet(old.CampaignModelConfig(**config))
    old_model.load_state_dict(new_model.state_dict())
    new_model.to(args.device).eval()
    old_model.to(args.device).eval()
    sides = {"earlier": old.NetworkStack([old_model]),
             "checkout": neural.NetworkStack([new_model], compiled=args.compiled)}
    runs = {name: [] for name in sides}
    outputs = {}
    with torch.inference_mode():
        for run in range(args.repeat):
            for name, stack in sides.items():
                kept = []
                began = time.perf_counter()
                for items in batches:
                    scores, values = stack.forward_packed(pack_zone_arrays(items, spec))
                    scores, values = scores.cpu(), values.cpu()
                    if run == 0:
                        kept.append((scores, values))
                runs[name].append(time.perf_counter() - began)
                if run == 0:
                    outputs[name] = kept
    differences = [(float((a[0] - b[0]).abs().max()) if a[0].numel() else 0.0, float((a[1] - b[1]).abs().max()))
                   for a, b in zip(outputs["earlier"], outputs["checkout"])]
    per_batch = {name: [1e6 * seconds / len(batches) for seconds in values] for name, values in runs.items()}
    best = {name: min(values[1:]) for name, values in per_batch.items()}
    report = {"device": args.device, "torch": torch.__version__, "old_root": str(args.old_root), "config": config,
              "merge": args.merge, "batches": len(batches),
              "states_per_batch": statistics.fmean(len(items) for items in batches), "compiled": args.compiled,
              "us_per_batch_by_run": per_batch, "best_us_per_batch": best,
              "change": best["checkout"] / best["earlier"] - 1,
              "first_run_seconds": {name: values[0] for name, values in runs.items()},
              "largest_score_difference": max(score for score, _ in differences),
              "largest_value_difference": max(value for _, value in differences)}
    print(json.dumps({key: value for key, value in report.items() if key != "us_per_batch_by_run"}, indent=1))
    if args.out:
        args.out.write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
