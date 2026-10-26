#!/usr/bin/env python3
"""Paired, resumable held-out Japanese expansion evaluation for three-round runs.

Example (trusted local model export or legacy recovery checkpoint)::

    .venv/bin/python tools/evaluate_three_round_campaign.py \
        --checkpoint studies/campaign/runs/three-round/models/generation-000000.pt \
        --output-dir studies/campaign/runs/three-round/evaluation-initial

Reissue exactly the same command after interruption. Completed seed/mode files
are atomic and reused; an interrupted game restarts from its seed under the same
execution contract. Accelerator floating-point nondeterminism still applies.
Training and active self-play resume from their separate runner checkpoint.
Plans predating execution-runtime identity are preserved but cannot be resumed
or paired by this helper; rerun them in a fresh directory rather than guessing
their historical device, numerical settings or PyTorch version.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "campaign-three-round-expansion-evaluation-v1"
HELDOUT_SEEDS = (40009, 40013, 40031, 40037, 40039, 40063, 40087, 40093)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def execution_runtime(models: dict) -> dict:
    """Record actual model placement and numerical settings, without GPU work."""
    import torch
    from studies.shared.multiplayer_mcts import PLAYERS
    devices, dtypes = {}, {}
    for player in PLAYERS:
        parameters = tuple(models[player].parameters())
        if not parameters:
            raise ValueError("Evaluation actor model has no parameters")
        placed = {str(parameter.device) for parameter in parameters}
        if len(placed) != 1:
            raise ValueError("Evaluation actor parameters span multiple neural devices")
        devices[player] = placed.pop()
        dtypes[player] = sorted({str(parameter.dtype) for parameter in parameters})
    if len(set(devices.values())) != 1:
        raise ValueError("Evaluation actor models must share one neural device")
    device = next(iter(devices.values()))
    target = torch.device(device)
    result = {"schema": "campaign-evaluation-execution-runtime-v1", "rules_device": "cpu",
              "search_device": "cpu", "neural_device": device, "model_devices": devices,
              "parameter_dtypes": dtypes, "torch_version": str(torch.__version__),
              "intraop_threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
              "float32_matmul_precision": torch.get_float32_matmul_precision()}
    if target.type == "mps":
        result["mps_environment"] = {
            "cpu_fallback_enabled": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "0") not in {"", "0"},
            "fast_math_enabled": os.environ.get("PYTORCH_MPS_FAST_MATH", "0") not in {"", "0"},
            # PyTorch's preference checks presence: '=0' also enables it.
            "prefer_metal_env_present": "PYTORCH_MPS_PREFER_METAL" in os.environ}
    elif target.type == "cuda":
        result["cuda_matmul_allow_tf32"] = bool(torch.backends.cuda.matmul.allow_tf32)
    return result


def _require_execution_runtime(plan: dict, label: str) -> None:
    if not isinstance(plan.get("evaluation", {}).get("execution_runtime"), dict):
        raise ValueError(f"Legacy {label} lacks execution runtime identity; rerun the evaluation in a fresh directory. Existing results are preserved")


def summarize(records: list[dict]) -> dict:
    from studies.campaign.evaluation import uncertainty
    complete = [record["result"]["games"][0] for record in records
                if record["result"]["games"][0]["terminal"]]
    return {"attempted_games": len(records), "terminal_games": len(complete),
        "truncated_games": len(records) - len(complete),
        "newly_held_chinese_land": uncertainty([game["japan_chinese_home_country"]["newly_held"]["count"]
                                                for game in complete]),
        "newly_held_chinese_ipp": uncertainty([game["japan_chinese_home_country"]["newly_held"]["ipp"]
                                               for game in complete]),
        "net_chinese_ipp_change": uncertainty([game["japan_chinese_home_country"]["net_ipp_change"]
                                                for game in complete]),
        "japanese_units_removed": uncertainty([game["casualties_by_nation"].get("japan", 0)
                                                for game in complete]),
        "axis_terminal_wealth": uncertainty([game["wealth_components_at_stop"]["axis"]["wealth"]
                                             for game in complete]),
        "axis_terminal_return": uncertainty([game["observed_terminal_returns"][0] for game in complete])}


def paired_comparison(current: list[dict], previous: list[dict]) -> dict:
    """Only genuine terminal games contribute paired outcome differences."""
    from studies.campaign.evaluation import uncertainty
    before = {(row["mode"], row["seed"]): row for row in previous}
    pairs = []
    for row in current:
        old = before.get((row["mode"], row["seed"]))
        if old is None:
            continue
        first, last = old["result"]["games"][0], row["result"]["games"][0]
        complete = first["terminal"] and last["terminal"]
        pairs.append({"mode": row["mode"], "seed": row["seed"],
            "both_terminal": complete, "initial_stop_reason": first["stop_reason"],
            "final_stop_reason": last["stop_reason"],
            "delta": {"newly_held_chinese_land": last["japan_chinese_home_country"]["newly_held"]["count"] -
                                                  first["japan_chinese_home_country"]["newly_held"]["count"],
                      "newly_held_chinese_ipp": last["japan_chinese_home_country"]["newly_held"]["ipp"] -
                                                 first["japan_chinese_home_country"]["newly_held"]["ipp"],
                      "net_chinese_ipp_change": last["japan_chinese_home_country"]["net_ipp_change"] -
                                                 first["japan_chinese_home_country"]["net_ipp_change"],
                      "japanese_units_removed": last["casualties_by_nation"].get("japan", 0) -
                                                  first["casualties_by_nation"].get("japan", 0),
                      "axis_terminal_wealth": last["wealth_components_at_stop"]["axis"]["wealth"] -
                                               first["wealth_components_at_stop"]["axis"]["wealth"],
                      "axis_terminal_return": last["observed_terminal_returns"][0] -
                                               first["observed_terminal_returns"][0]} if complete else None})
    metrics = ("newly_held_chinese_land", "newly_held_chinese_ipp", "net_chinese_ipp_change",
               "japanese_units_removed", "axis_terminal_wealth", "axis_terminal_return")
    return {"pairs": pairs, "by_mode": {mode: {"complete_pairs": sum(
        pair["both_terminal"] for pair in pairs if pair["mode"] == mode),
        "delta_statistics": {metric: uncertainty([pair["delta"][metric] for pair in pairs
            if pair["mode"] == mode and pair["both_terminal"]]) for metric in metrics}}
        for mode in sorted({pair["mode"] for pair in pairs})},
        "interpretation": "Final minus initial on paired seeds against unchanged fixed opponents; "
                          "same seeds do not imply identical dice events after policies choose different actions. "
                          "Small samples and approximate intervals do not establish general playing strength."}


def main(argv=None) -> int:
    import torch
    from studies.shared.multiplayer_mcts import PLAYERS
    from studies.campaign.baselines import scripted_policy
    from studies.campaign.curriculum import make_env, task_manifest
    from studies.campaign.evaluation import evaluate, validate_heldout_seeds
    from studies.campaign.neural import NeuralEvaluator
    from studies.campaign.run import RunConfig, _json
    from studies.campaign.model_export import load_evaluation_models
    from studies.campaign.device_runtime import runtime_policy_for_device

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--seeds", default=",".join(map(str, HELDOUT_SEEDS)))
    parser.add_argument("--modes", default="network_only,search")
    parser.add_argument("--simulations", type=int, default=16)
    parser.add_argument("--max-depth", type=int, default=16)
    parser.add_argument("--max-transitions", type=int, default=5000)
    parser.add_argument("--max-state-visits", type=int, default=20)
    parser.add_argument("--wall-seconds", type=float, default=3600,
                        help="Invocation guard checked between actual transitions/search waves")
    args = parser.parse_args(argv)
    if args.wall_seconds <= 0 or not __import__("math").isfinite(args.wall_seconds):
        parser.error("--wall-seconds must be finite and positive")
    modes = args.modes.split(",")
    if len(set(modes)) != len(modes) or not modes or set(modes) - {"network_only", "search"}:
        parser.error("--modes must be unique network_only and/or search")
    seeds = [int(value) for value in args.seeds.split(",")]
    # The evaluation is sequential: one tensor thread, one root/search worker,
    # and a coordinator fit a conservative three-core allowance.
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    loaded = load_evaluation_models(args.checkpoint)
    config = RunConfig(**loaded["config"])
    if config.calendar_rounds != 3:
        raise ValueError("This evaluation requires the explicit three-round campaign")
    separation = validate_heldout_seeds({player: seeds for player in PLAYERS},
        [config.seed, *loaded["training_environment_seeds"]])
    template = make_env(config.seed, calendar_rounds=3)
    # Legacy recovery loading may construct a learner using the training thread
    # setting; exports never do. Evaluation remains deliberately one thread.
    torch.set_num_threads(1)
    versions = loaded["model_versions"]
    execution = execution_runtime(loaded["models"])
    runtime_policy = runtime_policy_for_device(execution["neural_device"])
    evaluator = NeuralEvaluator(loaded["models"], version=fingerprint(versions), runtime_policy=runtime_policy)
    evaluation_contract = {"task": task_manifest(template), "seeds": seeds, "modes": modes,
        "target": "axis", "opponent": scripted_policy("balanced").version,
        "simulations": args.simulations, "max_depth": args.max_depth,
        "max_transitions": args.max_transitions, "max_state_visits": args.max_state_visits,
        "root_noise": False, "network_selection": "maximum prior, action-key tie break",
        "territorial_scope": "authoritative KMT Chinese Home Country, Japan possession only",
        "execution_runtime": execution}
    contract = {"schema": SCHEMA, "evaluation": evaluation_contract,
        "checkpoint_sha256": digest(args.checkpoint), "model_versions": versions,
        "runtime_source_sha256": loaded["runtime_source_sha256"],
        "model_artifact_schema": loaded["source_schema"], "generation": loaded["generation"],
        "helper_sha256": digest(Path(__file__)), "seed_separation": separation}
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    plan_path = output / "plan.json"
    if plan_path.exists():
        saved_plan = json.loads(plan_path.read_text())
        _require_execution_runtime(saved_plan, "evaluation plan")
        if saved_plan != contract:
            raise ValueError("Existing evaluation belongs to different weights, sources, seeds, settings or execution runtime")
    else:
        if any(output.iterdir()):
            raise ValueError("Choose an empty evaluation directory or resume its matching plan")
        _json(plan_path, contract)
    contract_sha = fingerprint(contract)
    previous = []
    if args.compare_to:
        old_plan = json.loads((args.compare_to / "plan.json").read_text())
        _require_execution_runtime(old_plan, "initial comparison plan")
        if old_plan["schema"] != SCHEMA or old_plan["evaluation"] != evaluation_contract:
            raise ValueError("Paired evaluation requires identical task, opponents, seeds, budgets and execution runtime")
        old_sha = fingerprint(old_plan)
        for mode in modes:
            for seed in seeds:
                path = args.compare_to / f"{mode}-{seed}.json"
                if path.exists():
                    record = json.loads(path.read_text())
                    if record["contract_sha256"] != old_sha or (record["mode"], record["seed"]) != (mode, seed):
                        raise ValueError("Initial per-game result does not match its evaluation plan")
                    previous.append(record)
    stopped = False
    started = time.monotonic()

    def request_stop(_number, _frame):
        nonlocal stopped
        stopped = True

    def stop_requested():
        return stopped or time.monotonic() - started >= args.wall_seconds

    handlers = {number: signal.signal(number, request_stop) for number in (signal.SIGINT, signal.SIGTERM)}
    records = []
    try:
        for mode in modes:
            for seed in seeds:
                path = output / f"{mode}-{seed}.json"
                if path.exists():
                    record = json.loads(path.read_text())
                    if record["contract_sha256"] != contract_sha or (record["mode"], record["seed"]) != (mode, seed):
                        raise ValueError("Per-game result does not match its evaluation plan")
                    records.append(record)
                    continue
                if stop_requested():
                    break
                result = evaluate(lambda seed: make_env(seed, calendar_rounds=3), evaluator,
                    target_player="axis", seeds=[seed], baseline_style="balanced",
                    simulations=args.simulations, max_depth=args.max_depth,
                    max_transitions=args.max_transitions, max_state_visits=args.max_state_visits,
                    selection_mode=mode, track_japan=True, stop_requested=stop_requested)
                record = {"schema": SCHEMA, "contract_sha256": contract_sha,
                          "mode": mode, "seed": seed, "result": result}
                interrupted = result["games"][0]["stop_reason"] == "external_stop"
                _json(output / f"interrupted-{mode}-{seed}.json" if interrupted else path, record)
                if interrupted:
                    break
                records.append(record)
                print(json.dumps({"mode": mode, "seed": seed,
                    "terminal": result["games"][0]["terminal"],
                    "seconds": result["decision_throughput"]["wall_seconds"],
                    "newly_held": result["games"][0]["japan_chinese_home_country"]["newly_held"]}), flush=True)
        complete = len(records) == len(modes) * len(seeds)
        report = {"schema": SCHEMA, "contract_sha256": contract_sha,
            "status": "completed" if complete else "interrupted", "records": records,
            "by_mode": {mode: summarize([row for row in records if row["mode"] == mode]) for mode in modes},
            "paired_comparison": paired_comparison(records, previous) if args.compare_to else None,
            "elapsed_seconds_this_invocation": time.monotonic() - started,
            "resume": "Atomic completed seed/mode results are reused; interrupted evaluation games restart "
                      "from their seed. Training and self-play use the runner checkpoint separately.",
            "limits": ["Only terminal games contribute terminal outcome and expansion summary statistics.",
                       "Removed unit identities include combat, surrender and forced removal.",
                       "This evaluates Axis/Japan against fixed verification opponents, not general game strength."]}
        _json(output / "report.json", report)
        return 0 if complete else 130
    finally:
        for number, handler in handlers.items():
            signal.signal(number, handler)


if __name__ == "__main__":
    raise SystemExit(main())
