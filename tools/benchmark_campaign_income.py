#!/usr/bin/env python3
"""Guarded native-C++ versus CPU/MPS income-component measurements.

A fresh completed scripted three-round game supplies real frozen opening/later
positions. This measures only income evaluation: no gameplay, search, network or
learning speedup is implied. Native capture, upload, synchronized compute, host
inspection and end-to-end component latency are reported separately.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
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
SCHEMA = "campaign-income-component-benchmark-v1"


def require(yes, message):
    if not yes:
        raise ValueError(message)


def atomic_json(path, value):
    from tools.supervise_campaign_training import atomic_json as save
    save(Path(path), value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class IncomeConfig:
    devices: tuple[str, ...] = ("cpu", "mps")
    seed: int = 1951
    batch_sizes: tuple[int, ...] = (1, 4, 16, 64)
    repeats: int = 10
    native_repeats: int = 100
    warmups: int = 1
    threads: int = 2
    cpu_budget: int = 12
    memory_bytes: int = 8_000_000_000
    seconds: float = 180.0

    def __post_init__(self):
        require(self.devices and len(set(self.devices)) == len(self.devices) and
                not set(self.devices) - {"cpu", "mps"}, "Select distinct explicit CPU/MPS targets")
        require(type(self.seed) is int and 0 <= self.seed < 2 ** 64, "Seed must fit unsigned 64-bit")
        require(self.batch_sizes and len(set(self.batch_sizes)) == len(self.batch_sizes) and
                all(type(n) is int and n > 0 for n in self.batch_sizes), "Batch sizes must be distinct positive integers")
        for name in ("repeats", "native_repeats", "warmups", "threads"):
            require(type(getattr(self, name)) is int and getattr(self, name) > 0, f"Invalid {name}")
        require(type(self.cpu_budget) is int and self.threads + 3 <= self.cpu_budget <= min(12, os.cpu_count() or 1),
                "Tensor threads and three coordinators must fit the 12-core allowance")
        require(type(self.memory_bytes) is int and 2_000_000_000 < self.memory_bytes <= 30_000_000_000,
                "Aggregate component memory must leave a reserve and fit 30 GB")
        require(type(self.seconds) in (float, int) and math.isfinite(self.seconds) and 0 < self.seconds <= 3600,
                "Component wall allowance must be positive and at most one hour")


def provenance():
    from tools.benchmark_campaign_backends import provenance as base
    value = base()
    value["income_harness_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return value


def exact_oracle(result, oracle):
    """Native exceptions and every defined component/value must agree exactly."""
    import numpy as np
    actual = result.income.detach().cpu().numpy()
    effective = result.effective.detach().cpu().numpy()
    errors = result.effective_error.detach().cpu().numpy()
    expected, expected_effective = oracle.income_array(), oracle.effective_array()
    classes = np.array([0, 1, 1, 2, 3, 1], dtype=np.int64)
    np.testing.assert_array_equal(classes[actual[:, :, 0]], expected[:, :, 0])
    valid = expected[:, :, 0] == 0
    np.testing.assert_array_equal(actual[:, :, 1:][valid], expected[:, :, 1:][valid])
    np.testing.assert_array_equal(classes[errors], expected_effective[:, :, 0])
    valid_effective = expected_effective[:, :, 0] == 0
    np.testing.assert_array_equal(effective[valid_effective], expected_effective[:, :, 1][valid_effective])
    return {"income_sha256": hashlib.sha256(actual.tobytes()).hexdigest(),
            "effective_sha256": hashlib.sha256(effective.tobytes()).hexdigest(),
            "effective_errors_sha256": hashlib.sha256(errors.tobytes()).hexdigest(), "exact": True}


def worker(config, device, progress):
    started, deadline = time.perf_counter(), time.monotonic() + config.seconds
    import torch
    import gwrl_cpp
    from studies.campaign.backends.income_kernel import IncomeTensorContext
    from studies.campaign.curriculum import make_env
    from studies.campaign.device_runtime import runtime_policy_for_device
    from tools.benchmark_campaign_backends import Config as ReplayConfig, prepare
    torch.set_num_threads(config.threads)
    torch.set_num_interop_threads(1)
    sync = torch.mps.synchronize if device == "mps" else lambda: None
    policy = runtime_policy_for_device(device)
    allocator = 0
    if device == "mps":
        recommended = torch.mps.recommended_max_memory()
        allocator = min((config.memory_bytes - 2_000_000_000) // 2, recommended)
        torch.mps.set_per_process_memory_fraction(allocator / recommended)
    report = {"schema": SCHEMA, "config": asdict(config), "device": device, "status": "preparing",
        "provenance": provenance(), "cases": [], "allocator_reservation_bytes": allocator,
        "software": {"torch": torch.__version__, "python": sys.version.split()[0],
                     "threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
                     "mps_fallback_env": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK")},
        "scope": "Income evaluation only; no phase advance, full GPU rules engine, self-play or learning throughput",
        "measurement": "Native baseline evaluates present nations. Tensor kernel returns all frozen nation slots, including absence errors. Diverse real positions cycle across batch lanes."}
    def persist():
        report["elapsed_worker_seconds"] = time.perf_counter() - started
        report["device_memory"] = ({"allocated_bytes": torch.mps.current_allocated_memory(),
                                    "driver_allocated_bytes": torch.mps.driver_allocated_memory()} if device == "mps" else {})
        report["device_runtime"] = policy.stats() if policy is not None else None
        atomic_json(progress, report)
    persist()
    prep_started = time.perf_counter()
    workload = prepare(ReplayConfig(seeds=(config.seed,)), deadline=deadline)
    report.update(preparation_seconds=time.perf_counter() - prep_started, task=workload["task"],
                  workload_sha256=digest(workload), status="running")
    positions = []
    for fixture in workload["fixtures"]:
        env = make_env(fixture["seed"], calendar_rounds=3)
        env.restore(fixture["serialized"])
        positions.append((fixture["label"], env.raw))
    context = gwrl_cpp.campaign_income_context(positions[0][1])
    setup_started = time.perf_counter()
    kernel = IncomeTensorContext(context, device)
    sync()
    report["static_context_setup_seconds"] = time.perf_counter() - setup_started
    report["static_context"] = {"definition_fingerprint": context.definition_fingerprint,
        "territory_count": len(context.territory_ids), "nation_count": len(context.nation_ids),
        "native_int_min": context.int_minimum, "native_int_max": context.int_maximum}
    persist()
    for size in config.batch_sizes:
        require(time.monotonic() < deadline, "Income wall guard before batch")
        lanes = [positions[i % len(positions)][1].clone() for i in range(size)]
        snapshots = [env.serialize() for env in lanes]
        capture = lambda: gwrl_cpp.capture_campaign_income(context, lanes)
        batch = capture()
        upload = lambda batch: (torch.tensor(batch.territory_array(), dtype=torch.int64, device=kernel.device),
                                torch.tensor(batch.nation_array(), dtype=torch.int64, device=kernel.device))
        t, n = upload(batch)
        cold = time.perf_counter(); result = kernel.compute(t, n); sync(); cold = time.perf_counter() - cold
        oracle = gwrl_cpp.campaign_income_oracle(context, lanes)
        evidence = exact_oracle(result, oracle)
        case = {"batch_size": size, "positions": [positions[i % len(positions)][0] for i in range(size)],
            "state_sha256": [hashlib.sha256(state.encode()).hexdigest() for state in snapshots],
            "cold_compute_seconds": cold, "capture_seconds": [], "upload_seconds": [],
            "compute_seconds": [], "inspection_seconds": [], "end_to_end_seconds": [], **evidence}
        for _ in range(config.warmups):
            kernel.compute(t, n)
        sync()
        for _ in range(config.repeats):
            require(time.monotonic() < deadline, "Income wall guard inside batch")
            before = time.perf_counter(); current = capture(); case["capture_seconds"].append(time.perf_counter() - before)
            sync(); before = time.perf_counter(); t, n = upload(current); sync(); case["upload_seconds"].append(time.perf_counter() - before)
            sync(); before = time.perf_counter(); result = kernel.compute(t, n); sync(); case["compute_seconds"].append(time.perf_counter() - before)
            before = time.perf_counter(); kernel.inspect_income(result); case["inspection_seconds"].append(time.perf_counter() - before)
            sync(); before = time.perf_counter(); current = capture(); et, en = upload(current); kernel.compute(et, en); sync()
            case["end_to_end_seconds"].append(time.perf_counter() - before)
            # Housekeeping happens after complete read-only operations, outside timers.
            if policy is not None:
                policy.completed(2)
        case["native_present_nations"] = gwrl_cpp.benchmark_campaign_income_oracle(lanes, config.native_repeats)
        case["native_present_nations"]["repeats"] = config.native_repeats
        case["read_only_state_and_rng"] = all(env.serialize() == state for env, state in zip(lanes, snapshots, strict=True))
        require(case["read_only_state_and_rng"], "Income operation mutated state/history/RNG")
        report["cases"].append(case)
        persist()
    ending = provenance()
    report["sources_unchanged"] = report["provenance"] == ending
    report["status"] = "completed" if report["sources_unchanged"] else "changed_inputs"
    persist()
    return report


def supervise(config, device, output):
    from tools.supervise_campaign_training import aggregate_rss, memory_metric, monitor_error_details
    started, peak, stopped, diagnostic = time.monotonic(), 0, None, None
    with tempfile.TemporaryDirectory(prefix="campaign-income-") as directory:
        directory = Path(directory); settings, progress = directory / "config.json", directory / "progress.json"
        atomic_json(settings, asdict(config))
        environment = {**os.environ, "PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
            "PYTORCH_ENABLE_MPS_FALLBACK": "0", "PYTORCH_MPS_FAST_MATH": "0",
            **{name: str(config.threads) for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}}
        # Charge the complete configured GPU allocation limit throughout the job,
        # plus CPU/process-tree footprint. This can double-count shared pages.
        allocator = (config.memory_bytes - 2_000_000_000) // 2 if device == "mps" else 0
        with (directory / "stderr").open("w") as stderr, (directory / "stdout").open("w") as stdout:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--_worker", str(settings),
                "--_device", device, "--output", str(progress)], cwd=ROOT, env=environment,
                stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                while process.poll() is None:
                    if time.monotonic() - started >= config.seconds:
                        stopped = "wall_limit"; break
                    try:
                        charged = aggregate_rss(process.pid) + allocator
                        peak = max(peak, charged)
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        if process.poll() is not None: break
                        stopped, diagnostic = "memory_monitor_failure", monitor_error_details(error, "income_component_memory", root_pid=process.pid)
                        break
                    if charged >= config.memory_bytes - 1_000_000_000:
                        stopped = "memory_limit"; break
                    time.sleep(.1)
            finally:
                if process.poll() is None:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                process.wait(timeout=5)
        report = json.loads(progress.read_text()) if progress.exists() else {"schema": SCHEMA, "device": device}
        if stopped:
            report["status"] = stopped
        elif process.returncode != 0 or report.get("status") != "completed":
            report["status"] = "worker_error"
            report["error"] = (directory / "stderr").read_text()[-4000:]
        report["guard"] = {"elapsed_seconds": time.monotonic() - started,
            "sampled_peak_charged_bytes": peak, "memory_bytes": config.memory_bytes,
            "margin_bytes": 1_000_000_000, "cpu_budget": config.cpu_budget,
            "allocator_reserved_bytes": allocator, "diagnostic": diagnostic,
            "metric": memory_metric() + " plus full MPS allocator reservation; conservative possible double counting"}
        atomic_json(output, report)
        return report


def paired(config, output):
    output = Path(output).resolve()
    paths = {device: output.with_name(output.stem + "." + device + ".json") for device in config.devices}
    require(not output.exists() and all(not p.exists() for p in paths.values()), "Choose new output paths")
    reports = {device: supervise(config, device, path) for device, path in paths.items()}
    completed = all(report.get("status") == "completed" for report in reports.values())
    exact = completed and len({report["workload_sha256"] for report in reports.values()}) == 1
    if exact:
        for rows in zip(*(report["cases"] for report in reports.values()), strict=True):
            exact = exact and len({(row["batch_size"], row["income_sha256"], row["effective_sha256"],
                                   row["effective_errors_sha256"]) for row in rows}) == 1
    report = {"schema": SCHEMA, "status": "completed" if completed and exact else "incomplete_or_mismatch",
              "matched_inputs_and_integer_outputs": bool(exact), "devices": reports,
              "scope": "Income component only; not full GPU rules, search, self-play or training speed"}
    atomic_json(output, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--devices", nargs="+", choices=("cpu", "mps"), default=("cpu", "mps"))
    parser.add_argument("--batch-sizes", nargs="+", type=int, default=(1, 4, 16, 64))
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--native-repeats", type=int, default=100)
    parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--memory-bytes", type=int, default=8_000_000_000)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_device", choices=("cpu", "mps"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        value = json.loads(args._worker.read_text()); value["devices"] = tuple(value["devices"]); value["batch_sizes"] = tuple(value["batch_sizes"])
        config = IncomeConfig(**value)
        worker(config, args._device, args.output)
        return 0
    config = IncomeConfig(devices=tuple(args.devices), batch_sizes=tuple(args.batch_sizes), repeats=args.repeats,
        native_repeats=args.native_repeats, seconds=args.seconds, memory_bytes=args.memory_bytes)
    return 0 if paired(config, args.output)["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
