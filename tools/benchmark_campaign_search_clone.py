#!/usr/bin/env python3
"""Guarded connected native/GPU cloneForSearch component comparison.

Matched complete native snapshots and uint64 seeds are used in a Python loop of
raw CampaignEnv.clone_for_search versus the composed resident GPU state fork,
exact SplitMix seed kernel and RandomStreams subtree replacement. This measures
neither a full GPU rules backend nor Monte Carlo search or learning throughput.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.benchmark_campaign_device_state import (
    StateConfig, POSITIONS, atomic_json, digest, require, supervise,
)

SCHEMA = "campaign-connected-search-clone-benchmark-v1"


@dataclass(frozen=True)
class SearchCloneConfig(StateConfig):
    devices: tuple[str, ...] = ("mps",)
    batch_sizes: tuple[int, ...] = (1, 4, 64, 256)

    def __post_init__(self):
        super().__post_init__()
        require(self.devices == ("mps",), "Connected search clone currently requires explicit Apple MPS; no CPU tensor fallback")


def provenance():
    from tools.benchmark_campaign_device_state import provenance as state_provenance
    value = state_provenance()
    value["search_clone_harness_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return value


def seed_values(size, seed):
    """Preparation only: explicit boundary seeds plus fixed full-width values."""
    edges = [0, 1, 2**63, 2**64 - 1, 2**24 + 1, 2**31 + 1, 2**32 - 1, 2**63 - 1]
    generator = random.Random(seed)
    return (edges + [generator.getrandbits(64) for _ in range(max(0, size - len(edges)))])[:size]


def exact_native_clones(actual, clones, *, inspection_chunk_bytes=32_000_000):
    """Check EVERY output bit against actual native clones in host chunks.

    Chunking limits verification scratch only; no lane, history, state field or
    seed is dropped. Native clones are measured separately and retained from
    the final repetition, so the oracle is independent of the GPU seed kernel.
    """
    import numpy as np
    import torch
    from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
    require(type(inspection_chunk_bytes) is int and inspection_chunk_bytes > 0, "Inspection budget must be positive")
    require(actual.lane_count == len(clones) and clones, "Every GPU destination needs a native clone oracle")
    count, capacity = actual.records.shape[:2]
    row_bytes = math.prod(actual.records.shape[1:]) * actual.records.element_size()
    chunk_lanes = max(1, inspection_chunk_bytes // max(row_bytes, 1))
    hashes = {field: hashlib.sha256() for field in ("records", "lengths", "sections", "errors")}
    full_native_hash = hashlib.sha256()
    maximum_records = 0
    reference_context = DeviceStateContext(actual.context.native, device="cpu")
    for start in range(0, count, chunk_lanes):
        stop = min(count, start + chunk_lanes)
        reference = DeviceStateBatch.capture(clones[start:stop], device="cpu", context=reference_context)
        require(reference.context.identity == actual.context.identity, "Native/GPU wire contexts differ")
        expected_records = reference.records.numpy()
        records = actual.records[start:stop].detach().cpu().numpy()
        require(expected_records.shape[1] <= capacity, "GPU clone unexpectedly truncated native records")
        np.testing.assert_array_equal(records[:, :expected_records.shape[1]], expected_records)
        require(not np.any(records[:, expected_records.shape[1]:]), "Unused GPU record allocation must remain canonical zero padding")
        hashes["records"].update(memoryview(records))
        maximum_records = max(maximum_records, int(reference.lengths.max()))
        for field in ("lengths", "sections", "errors"):
            value = getattr(actual, field)[start:stop].detach().cpu().numpy()
            np.testing.assert_array_equal(value, getattr(reference, field).numpy())
            hashes[field].update(memoryview(value))
        for owner, expected in ((actual, reference), (actual.context, reference.context)):
            for field in (("string_bytes", "string_offsets") if owner is actual else
                          ("records", "string_bytes", "string_offsets")):
                np.testing.assert_array_equal(getattr(owner, field).detach().cpu().numpy(), getattr(expected, field).numpy())
        for env in clones[start:stop]:
            serialized = env.serialize().encode()
            full_native_hash.update(len(serialized).to_bytes(8, "little")); full_native_hash.update(serialized)
    witnesses = tuple(sorted({0, count // 2, count - 1}))
    restored = actual.fork(torch.tensor(witnesses, dtype=torch.int64, device=actual.device)).restore_envs()
    require(all(env.serialize() == clones[index].serialize() for env, index in zip(restored, witnesses, strict=True)),
            "Native witness restore changed state, history or any random stream")
    return {"exact": True, "verified_lanes": count, "maximum_native_records": maximum_records,
        "resident_capacity": capacity, "inspection_chunk_target_bytes": inspection_chunk_bytes,
        "buffer_sha256": {field: value.hexdigest() for field, value in hashes.items()},
        "full_native_clones_sha256": full_native_hash.hexdigest(),
        "native_witness_lanes": witnesses, "native_witnesses_exact": True,
        "verification": "Every record/length/section/error and shared string/definition bit equals each actual native clone; representative full native restores include all history/RNG"}


def worker(config, device, progress, deadline):
    import gc
    import gwrl_cpp
    import torch
    from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
    from studies.campaign.backends.device_search_clone import clone_for_search
    from studies.campaign.curriculum import make_env
    from studies.campaign.device_runtime import runtime_policy_for_device
    from tools.benchmark_campaign_backends import Config as ReplayConfig, prepare
    require(device == "mps" and torch.backends.mps.is_available(), "Exact Apple MPS execution is required")
    started = time.perf_counter()
    torch.set_num_threads(config.threads); torch.set_num_interop_threads(1)
    recommended = torch.mps.recommended_max_memory()
    require(recommended > 0, "MPS allocator allowance unavailable")
    torch.mps.set_per_process_memory_fraction(min(3_000_000_000, recommended) / recommended)
    policy = runtime_policy_for_device("mps")
    report = {"schema": SCHEMA, "config": asdict(config), "device": device, "status": "preparing",
        "provenance": provenance(), "cases": [], "scope": __doc__,
        "software": {"torch": str(torch.__version__), "python": sys.version.split()[0],
            "threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads()},
        "population": "Replicas of real raw Engine snapshots; complete state/history/RNG retained; explicit full-width uint64 seeds",
        "provenance_scope": "Compiled native binary and current source/tool hashes are pinned separately. Dirty worktree paths are recorded; no claim is made that every worktree file is linked into that native binary.",
        "native_baseline": "Python call loop raw.clone_for_search(seed); Python/native boundary and native copied-state construction included",
        "gpu_path": "Resident DeviceStateBatch.fork + exact seed Metal kernel + RandomStreams subtree editor; no gameplay/search algorithm"}

    def persist():
        report["elapsed_worker_seconds"] = time.perf_counter() - started
        report["device_memory"] = {"live_bytes": torch.mps.current_allocated_memory(), "driver_bytes": torch.mps.driver_allocated_memory()}
        report["device_runtime"] = policy.stats()
        atomic_json(progress, report)

    def timed(operation, gpu=False):
        require(time.monotonic() < deadline, "Connected search-clone shared wall deadline exhausted")
        torch.mps.synchronize(); before = time.perf_counter(); value = operation()
        if gpu:
            torch.mps.synchronize()
        return value, time.perf_counter() - before

    persist()
    prep_start = time.perf_counter()
    workload = prepare(ReplayConfig(seeds=(config.seed,)), deadline=deadline)
    fixtures = [row for row in workload["fixtures"] if row["label"] in POSITIONS]
    require(len(fixtures) == len(POSITIONS) and {row["label"] for row in fixtures} == set(POSITIONS), "Missing required real fixtures")
    report.update(status="running", task=workload["task"], workload_sha256=digest(workload),
        preparation_seconds=time.perf_counter() - prep_start, preparation_completed_three_round_games=len(workload["plans"]))
    persist()
    for fixture in fixtures:
        env = make_env(fixture["seed"], calendar_rounds=3); env.restore(fixture["serialized"])
        raw, serialized = env.raw, env.raw.serialize()
        native_context, context_seconds = timed(lambda: gwrl_cpp.device_state_context(raw))
        context, static_upload_seconds = timed(lambda: DeviceStateContext(native_context, device), gpu=True)
        captured, capture_seconds = timed(lambda: gwrl_cpp.capture_device_states(native_context, [raw]))
        source, upload_seconds = timed(lambda: DeviceStateBatch.from_native(captured, context=context), gpu=True)
        initial_seeds = torch.zeros(1, dtype=torch.int64, device=device)
        initialized, initialization_seconds = timed(lambda: clone_for_search(source, initial_seeds), gpu=True)
        require(initialized.errors.cpu().tolist() == [0], "Connected kernel initialization failed")
        del initialized, initial_seeds
        for size in config.batch_sizes:
            before = time.perf_counter()
            values = seed_values(size, config.seed)
            seed_bits = [value if value < 2**63 else value - 2**64 for value in values]
            seed_preparation_seconds = time.perf_counter() - before
            (seeds, lanes), seed_upload_seconds = timed(lambda: (
                torch.tensor(seed_bits, dtype=torch.int64, device=device),
                torch.zeros(size, dtype=torch.int64, device=device)), gpu=True)
            before = time.perf_counter(); policy.reset(); reset_seconds = time.perf_counter() - before
            clones, native_cold = timed(lambda: [raw.clone_for_search(seed) for seed in values])
            result, gpu_cold = timed(lambda: clone_for_search(source, seeds, lanes), gpu=True)
            del clones, result
            case = {"position": fixture["label"], "lanes": size,
                "native_checkpoint_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
                "seed_values_uint64": [str(value) for value in values], "seed_values_sha256": digest(values),
                "host_seed_preparation_seconds": seed_preparation_seconds,
                "seed_and_lane_upload_seconds": seed_upload_seconds,
                "native_context_seconds": context_seconds, "native_capture_seconds": capture_seconds,
                "static_upload_seconds": static_upload_seconds, "dynamic_upload_seconds": upload_seconds,
                "initial_connected_kernel_setup_seconds": initialization_seconds,
                "cold_reset_seconds": reset_seconds, "cold_native_clone_loop_seconds": native_cold,
                "cold_gpu_connected_clone_seconds": gpu_cold, "native_clone_loop_seconds": [],
                "gpu_connected_clone_seconds": [],
                "cold_scope": "Public graph/allocator cache reset; compiled custom Metal libraries and OS caches may remain",
                "scheduler": "Raw Engine component only; wrapper metadata conformance is covered by focused tests"}
            for _ in range(config.warmups):
                temporary, _ = timed(lambda: [raw.clone_for_search(seed) for seed in values]); del temporary
                temporary, _ = timed(lambda: clone_for_search(source, seeds, lanes), gpu=True); del temporary
            for repetition in range(config.repeats):
                clones, elapsed = timed(lambda: [raw.clone_for_search(seed) for seed in values])
                case["native_clone_loop_seconds"].append(elapsed)
                result, elapsed = timed(lambda: clone_for_search(source, seeds, lanes), gpu=True)
                case["gpu_connected_clone_seconds"].append(elapsed)
                if repetition != config.repeats - 1:
                    del clones, result
                policy.completed(1)
            before = time.perf_counter()
            require(result.errors.cpu().tolist() == [0] * size and result.accepted.cpu().tolist() == [True] * size,
                    "Connected GPU clone returned invalid destinations")
            case["evidence"] = exact_native_clones(result.state, clones)
            case["host_inspection_native_capture_and_restore_seconds"] = time.perf_counter() - before
            require(raw.serialize() == serialized, "Component benchmark changed source state/history/RNG")
            report["cases"].append(case); persist()
            del clones, result, lanes, seeds
            gc.collect()
        del source, captured, context, native_context, raw, env
        gc.collect()
    report["sources_unchanged"] = report["provenance"] == provenance()
    report["status"] = "completed" if report["sources_unchanged"] else "changed_inputs"
    persist()
    return report


def run(config, output):
    output = Path(output).resolve()
    require(not output.exists(), "Choose a new output; existing evidence is preserved")
    result = supervise(config, "mps", output, deadline=time.monotonic() + config.seconds,
                       worker_script=Path(__file__).resolve())
    result["schema"] = SCHEMA
    expected = {(position, size) for position in POSITIONS for size in config.batch_sizes}
    cases = result.get("cases", [])
    exact = (result.get("status") == "completed" and result.get("sources_unchanged") is True and
        len(cases) == len(expected) and {(row["position"], row["lanes"]) for row in cases} == expected and
        all(row.get("evidence", {}).get("exact") is True and
            row["evidence"].get("verified_lanes") == row["lanes"] and
            row["evidence"].get("native_witnesses_exact") is True for row in cases))
    result["matched_full_native_clones_and_rng"] = bool(exact)
    if result.get("status") == "completed" and not exact:
        result["status"] = "incomplete_or_mismatch"
    atomic_json(output, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-sizes", nargs="+", type=int, default=(1, 4, 64, 256))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--memory-bytes", type=int, default=8_000_000_000)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_device", choices=("mps",), help=argparse.SUPPRESS)
    parser.add_argument("--_deadline", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        value = json.loads(args._worker.read_text())
        value["devices"], value["batch_sizes"] = tuple(value["devices"]), tuple(value["batch_sizes"])
        worker(SearchCloneConfig(**value), args._device, args.output, args._deadline)
        return 0
    config = SearchCloneConfig(batch_sizes=tuple(args.batch_sizes), repeats=args.repeats,
                              seconds=args.seconds, memory_bytes=args.memory_bytes)
    return 0 if run(config, args.output)["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
