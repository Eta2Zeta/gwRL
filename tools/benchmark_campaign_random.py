#!/usr/bin/env python3
"""Bounded native C++ versus exact Apple GPU campaign chance sampling.

This measures one RNG/dice component, not full game transitions or training.
Each repeat starts from the same complete immutable snapshots on both devices.
Packing, upload, cold compilation/dispatch and host inspection are separate.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, fields
import hashlib
import json
import math
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "campaign-exact-apple-random-benchmark-v1"
MASK64 = (1 << 64) - 1
GAMMA = 0x9E3779B97F4A7C15
STREAMS = ("actual", "search", "training")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def atomic_json(path, value):
    from tools.supervise_campaign_training import atomic_json as write
    write(Path(path), value)


@dataclass(frozen=True)
class RandomConfig:
    lanes: tuple[int, ...] = (4, 256, 4096)
    dice: int = 16
    repeats: int = 20
    warmups: int = 2
    seed: int = 9187
    threads: int = 2
    memory_bytes: int = 6_000_000_000
    mps_reserve_bytes: int = 2_000_000_000
    seconds: float = 120.

    def __post_init__(self):
        require(self.lanes and len(set(self.lanes)) == len(self.lanes) and
                all(type(value) is int and value in (4, 256, 4096) for value in self.lanes),
                "Select distinct complete 4/256/4096-lane workloads")
        require(type(self.dice) is int and self.dice == 16, "The matched workload preserves sixteen D12 per lane")
        require(type(self.repeats) is int and 1 <= self.repeats <= 100 and
                type(self.warmups) is int and 0 <= self.warmups <= 10, "Repetition counts must be explicitly bounded")
        require(type(self.seed) is int and 0 <= self.seed < 2**64, "Workload seed must be unsigned64")
        require(type(self.threads) is int and 1 <= self.threads <= 2, "This component benchmark uses at most two tensor threads")
        require(type(self.memory_bytes) is int and 4_000_000_000 < self.memory_bytes <= 6_000_000_000 and
                self.mps_reserve_bytes == 2_000_000_000, "Keep the six-GB aggregate guard and two-GB MPS reservation")
        require(type(self.seconds) in (int, float) and math.isfinite(self.seconds) and 0 < self.seconds <= 120.,
                "The complete benchmark has one deadline of at most 120 seconds")


def make_workload(lanes, config):
    """All streams, uint64 extremes, forced rejection and finite tape paths."""
    rng = random.Random(config.seed)
    requests, initial = [], []
    for lane in range(lanes):
        requests.append({"id": f"rng-{lane}", "purpose": "component_probe", "nation": "japan", "continuation": "probe",
            "dice": [{"sides": 12, "modifier": index % 3 - 1, "max_rerolls": 2, "reroll_faces": [1, 2]}
                     for index in range(config.dice)]})
        active = STREAMS[lane % 3]
        states = {name: rng.getrandbits(64) for name in STREAMS}
        if lane < 3:
            # Incremented state zero produces SplitMix output zero. D12 rejects
            # that draw because unsigned(-12)%12 == 4, then consumes another.
            states[active] = (-GAMMA) & MASK64
            states[STREAMS[(lane + 1) % 3]] = MASK64
            states[STREAMS[(lane + 2) % 3]] = 1 << 63
        tape = [6, *([1, 2, 12] * config.dice)] if lane % 7 == 6 else []
        initial.append({**{name: str(value) for name, value in states.items()}, "active": active,
                        "test_tape": tape, "tape_position": "1" if tape else "0"})
    return requests, initial


def provenance():
    import gwrl_cpp
    from studies.campaign.run import source_hashes
    sources = source_hashes()
    return {"parent_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "native_path": str(Path(gwrl_cpp.__file__).resolve()), "native_sha256": sha(gwrl_cpp.__file__),
            "runtime_source_sha256": sources, "runtime_source_set_sha256": digest(sources),
            "tool_sha256": sha(__file__)}


def verify_rows(actual, native, initial):
    require(len(actual) == len(native) == len(initial), "Sampling lane count differs")
    normalized, faces, draws, tape_lanes = [], 0, 0, 0
    inverse = pow(GAMMA, -1, 1 << 64)
    for index, (gpu, cpu, before) in enumerate(zip(actual, native, initial, strict=True)):
        require(not cpu["error"] and gpu["error"] == 0, f"Valid sampling lane {index} was rejected")
        expected = {"faces": cpu["faces"], "effective": cpu["effective"], "random": json.loads(cpu["random"])}
        require({key: gpu[key] for key in expected} == expected,
                f"Lane {index} differs in full face paths/effective results/all three RNG streams/tape cursor")
        for stream in STREAMS:
            if stream != before["active"] or before["test_tape"]:
                require(expected["random"][stream] == before[stream], "Unselected or tape-backed stream advanced")
        faces += sum(map(len, gpu["faces"]))
        active = before["active"]
        draws += ((int(gpu["random"][active]) - int(before[active])) * inverse) & MASK64
        tape_lanes += bool(before["test_tape"])
        normalized.append(expected)
    return {"all_lanes_bit_exact": True, "lanes_checked": len(actual), "complete_outcome_sha256": digest(normalized),
            "sampled_faces_per_invocation": faces, "splitmix_draws_per_invocation_including_rejections": draws,
            "tape_lanes": tape_lanes, "forced_zero_draw_rejection_lanes": list(range(min(3, len(actual)))),
            "first_lane": normalized[0] if normalized else None, "last_lane": normalized[-1] if normalized else None}


def perform(config, deadline):
    import gwrl_cpp
    import torch
    from studies.campaign.backends.random_metal import (inspect_sampled_chance, pack_chance_requests,
        pack_random_streams, sample_chance_metal)
    require(torch.backends.mps.is_available(), "Apple GPU unavailable; no CPU fallback")
    torch.set_num_threads(config.threads)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    recommended = torch.mps.recommended_max_memory()
    require(recommended >= config.mps_reserve_bytes, "Required MPS reservation exceeds the recommended working set")
    torch.mps.set_per_process_memory_fraction(config.mps_reserve_bytes / recommended)
    before = provenance()
    report = {"schema": SCHEMA, "status": "running", "config": asdict(config), "provenance": before,
              "torch_version": str(torch.__version__), "device": "mps", "recommended_max_bytes": recommended,
              "workloads": [], "limitation": "Exact RNG/dice component only; no combat effects, game completion, training throughput or learning-strength claim"}
    for workload_index, lanes in enumerate(config.lanes):
        require(time.monotonic() < deadline, "Shared RNG benchmark deadline reached")
        requests, initial = make_workload(lanes, config)
        started = time.perf_counter()
        encoded_requests, encoded_random = [canonical(row) for row in requests], [canonical(row) for row in initial]
        encoding_seconds = time.perf_counter() - started
        started = time.perf_counter()
        native = gwrl_cpp.campaign_sample_chance_probe(encoded_requests, encoded_random, config.repeats)
        native_total_seconds = time.perf_counter() - started
        started = time.perf_counter()
        cpu_dice, cpu_random = pack_chance_requests(requests), pack_random_streams(initial)
        packing_seconds = time.perf_counter() - started
        torch.mps.synchronize()
        started = time.perf_counter()
        dice, random_state = cpu_dice.to("mps"), cpu_random.to("mps")
        torch.mps.synchronize()
        transfer_seconds = time.perf_counter() - started
        started = time.perf_counter()
        cold = sample_chance_metal(dice, random_state)
        torch.mps.synchronize()
        cold_seconds = time.perf_counter() - started
        for _ in range(config.warmups):
            sampled = sample_chance_metal(dice, random_state)
            torch.mps.synchronize()
        torch.mps.synchronize()
        started = time.perf_counter()
        for _ in range(config.repeats):
            sampled = sample_chance_metal(dice, random_state)
            torch.mps.synchronize()
        warm_seconds = time.perf_counter() - started
        started = time.perf_counter()
        checked = verify_rows(inspect_sampled_chance(sampled), native["rows"], initial)
        cold_checked = verify_rows(inspect_sampled_chance(cold), native["rows"], initial)
        require(checked["complete_outcome_sha256"] == cold_checked["complete_outcome_sha256"], "Cold/warm sampling differs")
        for host, gpu in ((cpu_dice, dice), (cpu_random, random_state)):
            require(all(torch.equal(getattr(host, field.name), getattr(gpu, field.name).cpu()) for field in fields(host)),
                    "Sampling modified an input tensor")
        inspection_seconds = time.perf_counter() - started
        report["workloads"].append({"lanes": lanes, "dice_per_lane": config.dice, "repeats": config.repeats,
            "workload_sha256": digest({"requests": requests, "initial_random": initial}), "parity": checked,
            "host_json_encoding_seconds": encoding_seconds, "host_tensor_packing_seconds": packing_seconds,
            "device_upload_and_synchronize_seconds": transfer_seconds,
            "native_rules_seconds": native["rules_seconds"], "native_call_including_parse_and_output_seconds": native_total_seconds,
            "cold_dispatch_and_synchronize_seconds": cold_seconds,
            "shader_compile_included_in_cold": workload_index == 0,
            "gpu_warm_dispatch_and_synchronize_seconds": warm_seconds,
            "gpu_warm_seconds_per_invocation": warm_seconds / config.repeats,
            "native_rules_seconds_per_invocation": native["rules_seconds"] / config.repeats,
            "native_rules_over_gpu_warm_ratio": native["rules_seconds"] / warm_seconds,
            "explicit_host_inspection_and_verification_seconds": inspection_seconds,
            "device_memory": {"live_tensor_bytes": torch.mps.current_allocated_memory(),
                              "driver_bytes": torch.mps.driver_allocated_memory()},
            "warm_timing_scope": "Same complete immutable snapshots each repeat, one full sampler dispatch and synchronization per repeat; excludes packing/upload/inspection",
            "native_timing_scope": "Actual native RandomStreams::roll and effectiveResults, initial snapshots parsed once outside rules timer; each repeat starts from those snapshots"})
        del cold, sampled, dice, random_state, cpu_dice, cpu_random, native
        torch.mps.synchronize()
        torch.mps.empty_cache()
    require(provenance() == before, "Parent/runtime/native/tool changed during benchmark")
    report.update(status="completed", source_stable=True,
        rng_algorithm="Unchanged native SplitMix64 + unsigned64 rejection sampling and exact conditional rerolls")
    return report


def run(config, output):
    from tools.supervise_campaign_training import aggregate_rss, memory_metric, monitor_error_details
    output = Path(output).resolve()
    require(not output.exists(), "Choose fresh output; existing evidence is preserved")
    output.parent.mkdir(parents=True, exist_ok=True)
    settings, progress = output.with_suffix(".config.json"), output.with_suffix(".progress.json")
    require(not settings.exists() and not progress.exists(), "Choose a fresh artifact prefix")
    atomic_json(settings, asdict(config))
    started, deadline, peak, reason, diagnostic = time.monotonic(), time.monotonic() + config.seconds, 0, None, None
    environment = {**os.environ, "PYTORCH_ENABLE_MPS_FALLBACK": "0", "PYTORCH_MPS_FAST_MATH": "0",
                   "OMP_NUM_THREADS": str(config.threads), "MKL_NUM_THREADS": str(config.threads),
                   "VECLIB_MAXIMUM_THREADS": str(config.threads), "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}
    environment.pop("PYTORCH_MPS_PREFER_METAL", None)
    command = [sys.executable, str(Path(__file__).resolve()), "--_worker", str(settings), "--output", str(progress),
               "--_deadline", str(deadline)]
    with output.with_suffix(".stdout.log").open("w") as stdout, output.with_suffix(".stderr.log").open("w") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            while process.poll() is None:
                try:
                    charge = aggregate_rss(process.pid) + config.mps_reserve_bytes
                    peak = max(peak, charge)
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    if process.poll() is not None:
                        break
                    reason, diagnostic = "memory_monitor_failure", monitor_error_details(error, "random_component_benchmark", root_pid=process.pid)
                    break
                if charge >= config.memory_bytes - 1_000_000_000:
                    reason = "memory_limit"; break
                if time.monotonic() >= deadline:
                    reason = "wall_limit"; break
                time.sleep(.1)
            if reason:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
    report = json.loads(progress.read_text()) if progress.exists() else {"schema": SCHEMA, "status": "incomplete"}
    if reason or process.returncode:
        report.update(status="incomplete", stop_reason=reason or "worker_error", diagnostic=diagnostic)
    report["guard"] = {"peak_charged_bytes": peak, "memory_bytes": config.memory_bytes,
        "mps_reservation_bytes": config.mps_reserve_bytes, "stop_threshold_bytes": config.memory_bytes - 1_000_000_000,
        "metric": memory_metric(), "charge_scope": "Whole parent/worker process tree plus entire two-GB MPS allocator reservation; possible conservative double counting",
        "elapsed_seconds": time.monotonic() - started, "seconds": config.seconds, "worker_returncode": process.returncode,
        "tensor_threads": config.threads}
    atomic_json(output, report)
    require(report["status"] == "completed", f"RNG benchmark incomplete: {report.get('stop_reason')}; see stderr artifact")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lanes", default="4,256,4096")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--seconds", type=float, default=120.)
    parser.add_argument("--_worker", type=Path)
    parser.add_argument("--_deadline", type=float)
    args = parser.parse_args(argv)
    if args._worker:
        values = json.loads(args._worker.read_text()); values["lanes"] = tuple(values["lanes"])
        result = perform(RandomConfig(**values), args._deadline)
        atomic_json(args.output, result)
    else:
        result = run(RandomConfig(lanes=tuple(int(value) for value in args.lanes.split(",")), repeats=args.repeats,
                                  seconds=args.seconds), args.output)
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return result


if __name__ == "__main__":
    main()
