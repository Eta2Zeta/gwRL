#!/usr/bin/env python3
"""Bounded native C++ / Torch CPU / MPS explicit-dice primitive comparison.

No engine transition, neural network, RNG, self-play or learning is measured.
Native parsing, host packing, device transfer, resident validation/results and
diagnostic copies are timed separately. GPU timing explicitly synchronizes.
"""
from __future__ import annotations

import argparse
from dataclasses import fields
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA = "campaign-tensor-dice-benchmark-v1"
GPU_RESERVE = 1_000_000_000


def workload(lanes, dice_per_lane, rerolls):
    requests, outcomes = [], []
    for lane in range(lanes):
        dice, faces = [], []
        for index in range(1 + lane % dice_per_lane):
            special = rerolls and (lane + index) % 3 == 0
            dice.append({"sides": 6 if special else 12, "modifier": -1 if special else 0,
                         "reroll_faces": [1] if special else [], "max_rerolls": 2 if special else 0})
            faces.append([1, 1, 6] if special else [1 + (lane + index) % 12])
        requests.append({"id": str(lane), "purpose": "primitive-probe", "nation": "japan",
                         "continuation": "no-game", "dice": dice})
        outcomes.append(faces)
    return requests, outcomes


def write(path, value):
    from tools.supervise_campaign_training import atomic_json
    atomic_json(Path(path), value)


def worker(config, output):
    import torch
    import gwrl_cpp
    from studies.campaign.backends.tensor_rules import (effective_results, effective_results_metal,
                                                        inspect_outcomes, pack_outcomes)
    from studies.campaign.backends.tensor_rules_metal import metal_compilation_stats
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if "mps" in config["devices"]:
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS requested but unavailable; no CPU substitution")
        if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1":
            raise RuntimeError("MPS CPU fallback must be disabled")
        recommended = torch.mps.recommended_max_memory()
        torch.mps.set_per_process_memory_fraction(min(GPU_RESERVE / recommended, 1.0))
    paths = [ROOT / "studies/campaign/backends/tensor_rules.py", ROOT / "studies/campaign/backends/tensor_rules_metal.py",
             ROOT / "src/campaign_runtime.cpp",
             ROOT / "src/python_bindings.cpp", ROOT / "src/campaign_state.cpp", ROOT / "include/game/campaign.hpp",
             Path(__file__).resolve(), Path(gwrl_cpp.__file__).resolve()]
    hashes = lambda: {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report = {"schema": SCHEMA, "status": "running", "config": config, "provenance_sha256": hashes(),
              "torch": torch.__version__, "rows": [], "training_games": 0, "training_updates": 0,
              "limits": ["This is only exact dice validation/results; native commit and all other rules remain CPU.",
                         "Native JSON preparation and result transport are separate from its internal C++ timer.",
                         "Torch resident timing includes validation/status masks and Python operator launches; GPU is synchronized.",
                         "Implementation selection applies to MPS; CPU always supplies the portable Torch reference. Metal is explicit, one dispatch, and MPS-only.",
                         "Metal compilation and first-call shape-buffer setup are included in separately reported warmup, excluded from resident timing.",
                         "Packing, transfer and diagnostic copies are separate costs, not included in resident ratios.",
                         "Two deterministic synthetic spec families and one timing sample per case do not establish whole-game speedup."]}
    write(output, report)
    started = time.perf_counter()
    for lanes in config["lanes"]:
        for rerolls in (False, True):
            requests, outcomes = workload(lanes, config["dice_per_lane"], rerolls)
            before = time.perf_counter()
            request_json = [json.dumps(value) for value in requests]
            outcome_json = [json.dumps({"faces": value}) for value in outcomes]
            json_seconds = time.perf_counter() - before
            before = time.perf_counter()
            native = gwrl_cpp.campaign_effective_results_probe(request_json, outcome_json, config["repetitions"])
            native_wall = time.perf_counter() - before
            before = time.perf_counter(); batch = pack_outcomes(requests, outcomes)
            packing = time.perf_counter() - before
            row = {"lanes": lanes, "family": "conditional_rerolls" if rerolls else "ordinary_D12",
                   "dice": sum(len(req["dice"]) for req in requests), "repetitions": config["repetitions"],
                   "request_outcome_sha256": hashlib.sha256(json.dumps([requests, outcomes], sort_keys=True).encode()).hexdigest(),
                   "json_encoding_seconds": json_seconds, "host_tensor_packing_seconds": packing,
                   "native": {key: value for key, value in native.items() if key != "results"},
                   "native_total_call_seconds": native_wall, "devices": []}
            for device in config["devices"]:
                sync = torch.mps.synchronize if device == "mps" else lambda: None
                sync(); before = time.perf_counter(); resident = batch.to(device); sync()
                transfer = time.perf_counter() - before
                implementations = config["implementations"] if device == "mps" else ("portable",)
                for implementation in implementations:
                    execute = effective_results_metal if implementation == "metal" else effective_results
                    compilation_before = metal_compilation_stats()["compilation_seconds"]
                    before = time.perf_counter(); execute(resident); sync()
                    warmup = time.perf_counter() - before
                    compilation = metal_compilation_stats()["compilation_seconds"] - compilation_before
                    before = time.perf_counter()
                    for _ in range(config["repetitions"]):
                        result = execute(resident)
                    sync(); elapsed = time.perf_counter() - before
                    before = time.perf_counter(); inspected = inspect_outcomes(result); sync()
                    inspection = time.perf_counter() - before
                    if not all(value["valid"] for value in inspected) or [list(value["effective"]) for value in inspected] != native["results"]:
                        raise ValueError("Full native/Torch/Metal dice outcome parity failed")
                    row["devices"].append({"device": device, "implementation": implementation,
                        "device_tensor_bytes": sum(getattr(resident, field.name).numel() * 4 for field in fields(resident)),
                        "transfer_seconds": transfer, "transfer_shared_between_implementations": device == "mps" and len(implementations) > 1,
                        "warmup_calls": 1, "first_call_or_warmup_seconds": warmup,
                        "new_metal_compilation_seconds_within_warmup": compilation,
                        "resident_seconds": elapsed, "diagnostic_copy_seconds": inspection,
                        "native_rules_over_resident_ratio": native["rules_seconds"] / elapsed,
                        "all_results_and_error_masks_match_native": True,
                        "driver_allocated_bytes": torch.mps.driver_allocated_memory() if device == "mps" else 0})
                    del result
                del resident
            report["rows"].append(row); write(output, report)
    report.update(status="completed", worker_seconds=time.perf_counter() - started,
                  sources_unchanged=hashes() == report["provenance_sha256"])
    if not report["sources_unchanged"]:
        report["status"] = "source_changed"
    write(output, report)


def supervise(config, output):
    from tools.supervise_campaign_training import aggregate_rss, memory_metric
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a new output; previous measurements are preserved")
    started, peak, reason = time.monotonic(), 0, None
    with tempfile.TemporaryDirectory(prefix="campaign-dice-probe-") as directory:
        directory = Path(directory); settings, progress = directory / "settings.json", directory / "progress.json"
        write(settings, config)
        environment = {**os.environ, **{name: "1" for name in (
            "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")},
            "OMP_NUM_THREADS": "2"}
        with (directory / "errors").open("w") as errors:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--_worker", str(settings),
                "--output", str(progress)], cwd=ROOT, env=environment, stderr=errors, stdout=subprocess.DEVNULL,
                start_new_session=True)
            try:
                while process.poll() is None:
                    if time.monotonic() - started >= config["seconds"]:
                        reason = "wall_limit"; break
                    try:
                        charged = aggregate_rss(process.pid)
                    except (OSError, ValueError, subprocess.SubprocessError):
                        if process.poll() is not None:
                            break
                        reason = "monitor_failure"; break
                    peak = max(peak, charged)
                    # Keep an additional full allocator allowance outside the
                    # process-tree footprint to conservatively cover GPU pages.
                    if charged >= config["memory_bytes"] - GPU_RESERVE - 1_000_000_000:
                        reason = "memory_limit"; break
                    time.sleep(.1)
            finally:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait(timeout=5)
        report = json.loads(progress.read_text()) if progress.exists() else {"schema": SCHEMA, "config": config}
        if reason or process.returncode != 0:
            report.update(status=reason or "worker_error", error=(directory / "errors").read_text()[-4000:])
        report["guard"] = {"seconds": time.monotonic() - started, "peak_process_charge_bytes": peak,
            "process_memory_metric": memory_metric(), "memory_bytes": config["memory_bytes"],
            "gpu_allocator_reserve_bytes": GPU_RESERVE, "additional_margin_bytes": 1_000_000_000,
            "max_tensor_threads": 2, "reserved_processes": 3, "sampled_guard_not_kernel_cap": True,
            "worker_returncode": process.returncode}
        write(output, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lanes", default="4,256,4096")
    parser.add_argument("--devices", default="cpu,mps")
    parser.add_argument("--implementation", default="portable,metal",
                        help="MPS implementations to compare; CPU retains the portable reference")
    parser.add_argument("--dice-per-lane", type=int, default=16)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--memory-bytes", type=int, default=6_000_000_000)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        worker(json.loads(args._worker.read_text()), args.output)
        return 0
    lanes, devices = tuple(int(value) for value in args.lanes.split(",")), tuple(args.devices.split(","))
    implementations = tuple(args.implementation.split(","))
    if (not lanes or len(set(lanes)) != len(lanes) or any(not 1 <= value <= 4096 for value in lanes) or
            not devices or len(set(devices)) != len(devices) or set(devices) - {"cpu", "mps"} or
            not implementations or len(set(implementations)) != len(implementations) or set(implementations) - {"portable", "metal"} or
            not 1 <= args.dice_per_lane <= 64 or not 1 <= args.repetitions <= 100 or
            not 0 < args.seconds <= 600 or not 3_000_000_000 < args.memory_bytes <= 30_000_000_000):
        parser.error("Use unique lanes1..4096, cpu/mps, portable/metal, dice1..64, repetitions1..100, seconds<=600 and memory(3,30]GB")
    report = supervise({"lanes": lanes, "devices": devices, "implementations": implementations, "dice_per_lane": args.dice_per_lane,
        "repetitions": args.repetitions, "seconds": args.seconds, "memory_bytes": args.memory_bytes}, args.output)
    print(json.dumps({"status": report["status"], "output": str(args.output.resolve())}))
    return 0 if report["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
