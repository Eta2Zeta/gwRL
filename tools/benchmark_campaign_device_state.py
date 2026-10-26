#!/usr/bin/env python3
"""Guarded native-clone versus resident CPU/MPS state-fork measurements.

These are complete privileged Engine snapshots, including history and all RNG.
The native baseline is a Python loop calling raw CampaignEnv.clone; tensor forks
are batched gathers from an already resident snapshot. Initial capture/upload,
cold/warm fork latency and explicit host inspection are separate measurements.
This component benchmark does not measure full GPU gameplay, MCTS or learning.
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
SCHEMA = "campaign-device-state-fork-benchmark-v1"
POSITIONS = ("opening", "first_chance", "round2_japan_combat_movement")
MPS_RESERVE = 3_000_000_000
MARGIN = 1_000_000_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def atomic_json(path, value):
    from tools.supervise_campaign_training import atomic_json as save
    save(Path(path), value)


@dataclass(frozen=True)
class StateConfig:
    devices: tuple[str, ...] = ("cpu", "mps")
    seed: int = 1951
    batch_sizes: tuple[int, ...] = (1, 4, 16, 64, 256)
    repeats: int = 5
    warmups: int = 1
    threads: int = 2
    cpu_budget: int = 12
    memory_bytes: int = 8_000_000_000
    seconds: float = 180.0

    def __post_init__(self):
        require(self.devices and len(set(self.devices)) == len(self.devices) and
                not set(self.devices) - {"cpu", "mps"}, "Select distinct explicit CPU/MPS devices")
        require(type(self.seed) is int and 0 <= self.seed < 2**64, "Seed must be an unsigned 64-bit integer")
        require(self.batch_sizes and len(set(self.batch_sizes)) == len(self.batch_sizes) and
                all(type(size) is int and size > 0 for size in self.batch_sizes),
                "Batch sizes must be distinct positive integers; capacity is never truncated")
        for field in ("repeats", "warmups", "threads"):
            require(type(getattr(self, field)) is int and getattr(self, field) > 0, f"Invalid {field}")
        require(self.threads <= 2 and type(self.cpu_budget) is int and
                self.threads + 3 <= self.cpu_budget <= min(12, os.cpu_count() or 1),
                "At most two tensor threads plus coordinators must fit twelve cores")
        require(type(self.memory_bytes) is int and MPS_RESERVE + MARGIN < self.memory_bytes <= 8_000_000_000,
                "State benchmark must fit 8GB including 3GB MPS reservation and 1GB margin")
        require(type(self.seconds) in (int, float) and math.isfinite(self.seconds) and 0 < self.seconds <= 180,
                "The entire paired component benchmark must finish within 180 seconds")


def provenance():
    from tools.benchmark_campaign_backends import provenance as base
    value = base()
    value["state_harness_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    value["supervisor_source_sha256"] = hashlib.sha256((ROOT / "tools/supervise_campaign_training.py").read_bytes()).hexdigest()
    return value


def exact_resident(actual, reference, *, inspection_chunk_bytes=32_000_000):
    """Compare every complete lane against a one-lane CPU clone reference.

    Broadcast views avoid materializing another batch-sized expected snapshot.
    Copies and reductions here are explicit verification/inspection, outside
    fork timing. No record, padding, section, string or random stream is omitted.
    """
    import numpy as np
    require(reference.lane_count == 1, "Reference must be one complete CPU clone")
    require(actual.context.identity == reference.context.identity, "Device state definition/rules differ")
    require(type(inspection_chunk_bytes) is int and inspection_chunk_bytes > 0, "Inspection byte budget must be positive")
    arrays, hashes = {}, {}
    # Stream all record lanes through bounded host scratch. This limits only
    # inspection's temporary copies, never the state, history or fork capacity.
    expected_records = reference.records.detach().cpu().numpy()
    require(actual.records.dtype == reference.records.dtype and actual.records.shape[1:] == reference.records.shape[1:],
            "Resident record layout changed")
    row_bytes = math.prod(actual.records.shape[1:]) * actual.records.element_size()
    chunk_lanes = max(1, inspection_chunk_bytes // max(row_bytes, 1))
    record_hash = hashlib.sha256()
    for start in range(0, actual.lane_count, chunk_lanes):
        value = actual.records[start:start + chunk_lanes].detach().cpu().numpy()
        np.testing.assert_array_equal(value, np.broadcast_to(expected_records, value.shape))
        record_hash.update(memoryview(value))
    hashes["records"] = record_hash.hexdigest()
    for field in ("lengths", "sections", "errors"):
        value = getattr(actual, field).detach().cpu().numpy()
        expected = getattr(reference, field).detach().cpu().numpy()
        require(value.dtype == expected.dtype and value.shape[1:] == expected.shape[1:], "Resident field layout changed")
        np.testing.assert_array_equal(value, np.broadcast_to(expected, value.shape))
        arrays[field] = value
    for label, owner, expected_owner in (("dynamic", actual, reference), ("static", actual.context, reference.context)):
        fields = ("string_bytes", "string_offsets") if label == "dynamic" else ("records", "string_bytes", "string_offsets")
        for field in fields:
            value = getattr(owner, field).detach().cpu().numpy()
            expected = getattr(expected_owner, field).detach().cpu().numpy()
            np.testing.assert_array_equal(value, expected)
            arrays[f"{label}_{field}"] = value
    require(not np.any(arrays["errors"]), "Resident fork contains an invalid lane")
    hashes.update({field: hashlib.sha256(memoryview(value)).hexdigest() for field, value in arrays.items()})
    return {"exact": True, "buffer_sha256": hashes, "verified_lanes": actual.lane_count,
            "record_capacity": int(actual.records.shape[1]), "inspection_chunk_budget_bytes": inspection_chunk_bytes,
            "actual_records_per_lane": int(reference.lengths[0]),
            "verification": "Every record bit, length, section, error and shared definition/string buffer equals the CPU clone reference"}


def native_witnesses(actual, serialized):
    """Restore representative full native states after all-lane bit equality."""
    import torch
    count = actual.lane_count
    require(count > 0, "Native witnesses require real lanes")
    lanes = tuple(sorted({0, count // 2, count - 1}))
    selected = torch.tensor(lanes, dtype=torch.int64, device=actual.device)
    restored = actual.fork(selected).restore_envs()
    require(len(restored) == len(lanes) and all(env.serialize() == serialized for env in restored),
            "Native restore changed a state field, history or RNG stream")
    return {"lanes": lanes, "full_native_state_and_all_rng_exact": True,
            "native_checkpoint_sha256": hashlib.sha256(serialized.encode()).hexdigest()}


def worker(config, device, progress, deadline):
    import gc
    import gwrl_cpp
    import torch
    from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
    from studies.campaign.curriculum import make_env
    from studies.campaign.device_runtime import runtime_policy_for_device
    from tools.benchmark_campaign_backends import Config as ReplayConfig, prepare
    started = time.perf_counter()
    torch.set_num_threads(config.threads)
    torch.set_num_interop_threads(1)
    sync = torch.mps.synchronize if device == "mps" else lambda: None
    if device == "mps":
        require(torch.backends.mps.is_available(), "MPS is unavailable; no CPU fallback")
        recommended = torch.mps.recommended_max_memory()
        require(recommended > 0, "MPS allocator allowance is unavailable")
        torch.mps.set_per_process_memory_fraction(min(MPS_RESERVE, recommended) / recommended)
    policy = runtime_policy_for_device(device)
    report = {"schema": SCHEMA, "config": asdict(config), "device": device, "status": "preparing",
        "provenance": provenance(), "cases": [], "scope": __doc__,
        "software": {"torch": torch.__version__, "python": sys.version.split()[0],
            "threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
            "mps_fallback_env": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"),
            "mps_fast_math_env": os.environ.get("PYTORCH_MPS_FAST_MATH")},
        "population": "Replicas of one real frozen raw Engine position per case; every history and random field retained",
        "native_baseline": "Python call loop [raw_env.clone() for each lane]; includes Python/native boundary overhead",
        "tensor_path": "Resident batched DeviceStateBatch.fork; no native clone, state JSON or host inspection in fork timing"}

    def persist():
        report["elapsed_worker_seconds"] = time.perf_counter() - started
        report["device_memory"] = ({"live_bytes": torch.mps.current_allocated_memory(),
            "driver_bytes": torch.mps.driver_allocated_memory()} if device == "mps" else {})
        report["device_runtime"] = policy.stats() if policy is not None else None
        atomic_json(progress, report)

    def guard():
        require(time.monotonic() < deadline, "State-fork shared wall deadline exhausted")

    def timed(operation, *, device_work=False):
        guard()
        sync()
        before = time.perf_counter()
        value = operation()
        # The initial sync quiesces earlier work outside either timer. A CPU
        # clone/capture does not pay for an extra device fence in its result.
        # (The no-op CPU synchronizer remains harmless for tensor-CPU cases.)
        if device_work:
            sync()
        return value, time.perf_counter() - before

    persist()
    prep_start = time.perf_counter()
    workload = prepare(ReplayConfig(seeds=(config.seed,)), deadline=deadline)
    fixtures = [row for row in workload["fixtures"] if row["label"] in POSITIONS]
    require(len(fixtures) == len(POSITIONS) and {row["label"] for row in fixtures} == set(POSITIONS),
            "Fresh scripted game did not reach every required real position")
    report.update(status="running", task=workload["task"], workload_sha256=digest(workload),
        preparation_seconds=time.perf_counter() - prep_start,
        preparation_completed_three_round_games=len(workload["plans"]),
        preparation_scope="One fresh completed scripted game supplies fixtures; excluded from fork timing")
    persist()
    for fixture in fixtures:
        guard()
        env = make_env(fixture["seed"], calendar_rounds=3)
        env.restore(fixture["serialized"])
        raw, serialized = env.raw, env.raw.serialize()
        native_context, context_seconds = timed(lambda: gwrl_cpp.device_state_context(raw))
        context, static_upload_seconds = timed(lambda: DeviceStateContext(native_context, device), device_work=True)
        native, capture_seconds = timed(lambda: gwrl_cpp.capture_device_states(native_context, [raw]))
        resident, upload_seconds = timed(lambda: DeviceStateBatch.from_native(native, context=context), device_work=True)
        # A real native clone supplies the reference, not the device's own data.
        reference_raw = raw.clone()
        require(reference_raw.serialize() == serialized, "Native reference clone changed complete state/RNG")
        reference = DeviceStateBatch.capture([reference_raw], device="cpu")
        for size in config.batch_sizes:
            guard()
            indices = torch.zeros(size, dtype=torch.int64, device=device)
            # Public empty_cache in supported MPS runtimes also clears graphs;
            # cold reset is outside the timing and reported explicitly.
            before = time.perf_counter()
            if policy is not None:
                policy.reset()
            sync()
            reset_seconds = time.perf_counter() - before
            clones, cold_native = timed(lambda: [raw.clone() for _ in range(size)])
            actual, cold_device = timed(lambda: resident.fork(indices), device_work=True)
            case = {"position": fixture["label"], "seed": fixture["seed"], "lanes": size,
                "native_checkpoint_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
                "native_context_seconds": context_seconds, "native_capture_seconds": capture_seconds,
                "static_upload_seconds": static_upload_seconds, "dynamic_upload_seconds": upload_seconds,
                "setup_population": "One source snapshot, reused by all repeated-source forks",
                "cold_reset_seconds": reset_seconds, "cold_native_clone_loop_seconds": cold_native,
                "cold_tensor_fork_seconds": cold_device, "native_clone_loop_seconds": [],
                "tensor_fork_seconds": [], "cold_scope": "Supported public MPS cache reset; OS and process initialization are excluded"}
            del clones, actual
            for _ in range(config.warmups):
                value, _ = timed(lambda: [raw.clone() for _ in range(size)])
                del value
                value, _ = timed(lambda: resident.fork(indices), device_work=True)
                del value
            for repetition in range(config.repeats):
                clones, seconds = timed(lambda: [raw.clone() for _ in range(size)])
                case["native_clone_loop_seconds"].append(seconds)
                if repetition == config.repeats - 1:
                    clone_witnesses = [clones[index] for index in sorted({0, size // 2, size - 1})]
                # Destruction is outside both construction timers.
                del clones
                actual, seconds = timed(lambda: resident.fork(indices), device_work=True)
                case["tensor_fork_seconds"].append(seconds)
                if policy is not None:
                    policy.completed(1)
                if repetition != config.repeats - 1:
                    del actual
            before = time.perf_counter()
            require(all(clone.serialize() == serialized for clone in clone_witnesses),
                    "Timed native clone loop changed full state/history/RNG")
            case["timed_native_clone_witnesses_exact"] = True
            case["resident_evidence"] = exact_resident(actual, reference)
            case["native_witnesses"] = native_witnesses(actual, serialized)
            case["host_inspection_and_native_restore_seconds"] = time.perf_counter() - before
            require(raw.serialize() == serialized, "Benchmark changed the source state/history/RNG")
            report["cases"].append(case)
            persist()
            del actual, indices, clone_witnesses
            gc.collect()
        del reference, reference_raw, resident, native, context, native_context, raw, env
        gc.collect()
    report["sources_unchanged"] = report["provenance"] == provenance()
    report["status"] = "completed" if report["sources_unchanged"] else "changed_inputs"
    persist()
    return report


def supervise(config, device, output, *, deadline):
    from tools.supervise_campaign_training import aggregate_rss, memory_metric, monitor_error_details
    started, peak, stopped, diagnostic = time.monotonic(), 0, None, None
    reserve = MPS_RESERVE if device == "mps" else 0
    if started >= deadline:
        report = {"schema": SCHEMA, "device": device, "status": "wall_limit", "cases": []}
        atomic_json(output, report)
        return report
    with tempfile.TemporaryDirectory(prefix="campaign-state-fork-") as directory:
        directory = Path(directory)
        settings, progress = directory / "config.json", directory / "progress.json"
        atomic_json(settings, asdict(config))
        environment = {**os.environ, "PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
            "PYTORCH_ENABLE_MPS_FALLBACK": "0", "PYTORCH_MPS_FAST_MATH": "0",
            **{field: str(config.threads) for field in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}}
        with (directory / "stderr").open("w") as stderr, (directory / "stdout").open("w") as stdout:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--_worker", str(settings),
                "--_device", device, "--_deadline", str(deadline), "--output", str(progress)],
                cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                while process.poll() is None:
                    if time.monotonic() >= deadline:
                        stopped = "wall_limit"; break
                    try:
                        charged = aggregate_rss(process.pid) + reserve
                        peak = max(peak, charged)
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        if process.poll() is not None:
                            break
                        stopped, diagnostic = "memory_monitor_failure", monitor_error_details(error, "state_fork_memory", root_pid=process.pid)
                        break
                    if charged >= config.memory_bytes - MARGIN:
                        stopped = "memory_limit"; break
                    time.sleep(.1)
            finally:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait(timeout=5)
        report = json.loads(progress.read_text()) if progress.exists() else {"schema": SCHEMA, "device": device, "cases": []}
        if stopped:
            report["status"] = stopped
        elif process.returncode != 0 or report.get("status") != "completed":
            report["status"] = "worker_error"
            report["error"] = (directory / "stderr").read_text()[-4000:]
        report["guard"] = {"elapsed_seconds": time.monotonic() - started, "shared_deadline_monotonic": deadline,
            "sampled_peak_charged_bytes": peak, "memory_bytes": config.memory_bytes, "margin_bytes": MARGIN,
            "mps_allocator_reserved_bytes": reserve, "cpu_budget": config.cpu_budget, "diagnostic": diagnostic,
            "metric": memory_metric() + " plus full fixed MPS allocator reservation; conservative possible double counting"}
        atomic_json(output, report)
        return report


def paired(config, output):
    output = Path(output).resolve()
    paths = {device: output.with_name(output.stem + "." + device + ".json") for device in config.devices}
    require(not output.exists() and all(not path.exists() for path in paths.values()), "Choose new output paths; evidence is never overwritten")
    started = time.monotonic()
    deadline = started + config.seconds
    reports = {device: supervise(config, device, path, deadline=deadline) for device, path in paths.items()}
    completed = all(row.get("status") == "completed" and row.get("sources_unchanged") is True for row in reports.values())
    expected = {(position, size) for position in POSITIONS for size in config.batch_sizes}
    exact = (completed and all(isinstance(row.get("workload_sha256"), str) and len(row["workload_sha256"]) == 64
                              for row in reports.values()) and
             len({row["workload_sha256"] for row in reports.values()}) == 1 and
             len({digest(row.get("provenance")) for row in reports.values()}) == 1 and
             len({digest(row.get("software")) for row in reports.values()}) == 1)
    if exact:
        case_sets = []
        for row in reports.values():
            cases = row.get("cases", [])
            valid = len(cases) == len(expected) and {(case["position"], case["lanes"]) for case in cases} == expected
            exact = exact and valid and all(case.get("resident_evidence", {}).get("exact") is True and
                case.get("native_witnesses", {}).get("full_native_state_and_all_rng_exact") is True and
                case.get("timed_native_clone_witnesses_exact") is True for case in cases)
            if exact:
                case_sets.append({(case["position"], case["lanes"]):
                    (case["native_checkpoint_sha256"], case["resident_evidence"]["buffer_sha256"]) for case in cases})
        exact = exact and all(value == case_sets[0] for value in case_sets[1:])
    report = {"schema": SCHEMA, "status": "completed" if exact else "incomplete_or_mismatch",
        "matched_complete_states_and_rng": bool(exact), "config": asdict(config), "devices": reports,
        "elapsed_total_seconds": time.monotonic() - started,
        "scope": "Full-state fork component only. Python raw.clone loop versus resident batched gather; not full GPU gameplay, search or learning throughput."}
    atomic_json(output, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--devices", nargs="+", choices=("cpu", "mps"), default=("cpu", "mps"))
    parser.add_argument("--batch-sizes", nargs="+", type=int, default=(1, 4, 16, 64, 256))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--memory-bytes", type=int, default=8_000_000_000)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_device", choices=("cpu", "mps"), help=argparse.SUPPRESS)
    parser.add_argument("--_deadline", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        value = json.loads(args._worker.read_text())
        value["devices"], value["batch_sizes"] = tuple(value["devices"]), tuple(value["batch_sizes"])
        worker(StateConfig(**value), args._device, args.output, args._deadline)
        return 0
    config = StateConfig(devices=tuple(args.devices), batch_sizes=tuple(args.batch_sizes), repeats=args.repeats,
                         seconds=args.seconds, memory_bytes=args.memory_bytes)
    return 0 if paired(config, args.output)["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
