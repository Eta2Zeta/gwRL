#!/usr/bin/env python3
"""Matched SHA-256 compression over exact native State identity messages.

This is a hash component benchmark. The current native canonical State bytes
are prepared once and uploaded before timing. It does not measure State JSON
serialization, a complete rule transition, self-play or training throughput.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from tools.benchmark_campaign_device_state import StateConfig, atomic_json, require, supervise
from tools.benchmark_campaign_resident_recruitment_chance import FAMILIES, lanes, templates

SCHEMA = "campaign-content-digest-compression-benchmark-v1"
IMPLEMENTATIONS = ("reference", "unrolled")
ROLES = ("source_preflight", "after_effects")


@dataclass(frozen=True)
class DigestConfig(StateConfig):
    devices: tuple[str, ...] = ("mps",)
    batch_sizes: tuple[int, ...] = (1, 4, 16, 64)
    repeats: int = 3
    families: tuple[str, ...] = FAMILIES
    implementations: tuple[str, ...] = IMPLEMENTATIONS
    group_sizes: tuple[int | None, ...] = (None, 1, 4, 32)

    def __post_init__(self):
        super().__post_init__()
        require(self.devices == ("mps",), "SHA diagnostics require explicit MPS")
        for values, allowed, label in ((self.families, FAMILIES, "families"),
                                       (self.implementations, IMPLEMENTATIONS, "implementations")):
            require(values and len(set(values)) == len(values) and not set(values) - set(allowed),
                    f"Choose distinct supported digest {label}")
        require(self.group_sizes and all(value is None or type(value) is int and value > 0 for value in self.group_sizes)
                and len(set(self.group_sizes)) == len(self.group_sizes), "Choose distinct positive integer or default group sizes")


def provenance():
    from tools.benchmark_campaign_backends import provenance as base
    value = base()
    value["digest_sources"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        "studies/campaign/backends/content_digest_metal.py", "studies/campaign/backends/content_digest_unrolled.py",
        "tools/benchmark_campaign_content_digests.py", "tools/benchmark_campaign_device_state.py",
        "tools/benchmark_campaign_resident_recruitment_chance.py", "tools/supervise_campaign_training.py",
        "src/python_content_digest.inc", "src/python_state_json.inc")}
    return value


def identity_messages(config, deadline):
    """Native bytes from the same legally issued recruitment profile fixtures.

    Restored controlled-minor fixture authoring is explicit setup. Both the
    pending roll and its completed native resolveChance are retained; the
    Engine's complete source/history/RNG serialization is checked unchanged.
    """
    import gwrl_cpp
    prepared = templates(config, deadline)
    result = []
    for family in config.families:
        require(time.monotonic() < deadline, "Identity fixture preparation exhausted deadline")
        sources, evidence = lanes(prepared[family], 1, config.seed, deadline)
        before = sources[0]
        original = before.serialize()
        after = before.clone(); after.resolve_chance()
        envs = (before, after)
        rows = gwrl_cpp.campaign_state_json_oracle(envs)
        require(before.serialize() == original, "Native oracle changed the complete source/RNG")
        for role, env, row in zip(ROLES, envs, rows, strict=True):
            message = row["json"]
            outer = b'{"rules_id":' + row["rules_json"] + b',"state_key":"' + row["state_key"].encode() + b'"}'
            require(type(message) is bytes and hashlib.sha256(message).hexdigest() == row["state_key"] and
                    hashlib.sha256(outer).hexdigest() == row["engine_key"], "Native identity bytes/keys do not agree")
            result.append({"family": family, "role": role, "message": message,
                "outer_engine_message": outer, "state_key": row["state_key"], "engine_key": row["engine_key"],
                "native_checkpoint_sha256": hashlib.sha256(env.serialize().encode()).hexdigest(),
                "draw_evidence": evidence[0],
                "fixture": "Restored controlled-minor campaign state followed by the original legal recruitment roll/resolveChance"})
    return result


def worker(config, device, output, deadline):
    import gwrl_cpp
    import torch
    from studies.campaign.backends.content_digest_metal import content_digests_metal, inspect_digests, pack_messages
    from studies.campaign.device_runtime import runtime_policy_for_device
    require(device == "mps" and torch.backends.mps.is_available(), "Explicit Apple GPU required; no CPU fallback")
    torch.set_num_threads(config.threads); torch.set_num_interop_threads(1)
    torch.mps.set_per_process_memory_fraction(3_000_000_000 / torch.mps.recommended_max_memory())
    policy = runtime_policy_for_device(device)
    started = time.perf_counter(); pinned = provenance()
    report = {"schema": SCHEMA, "status": "preparing", "config": asdict(config), "provenance": pinned,
        "cases": [], "scope": __doc__, "native_baseline": "Original native contentDigest, serial messages; Python boxing excluded by native timer",
        "group_size_semantics": "Independent complete-message threads per group; no per-message parallel compression or dropped bytes",
        "software": {"torch": torch.__version__, "python": sys.version, "threads": torch.get_num_threads(),
                     "interop_threads": torch.get_num_interop_threads()}}

    def guard(): require(time.monotonic() < deadline, "Shared digest benchmark deadline exhausted")
    def persist():
        report["elapsed_worker_seconds"] = time.perf_counter() - started
        report["device_memory"] = {"live_bytes": torch.mps.current_allocated_memory(), "driver_bytes": torch.mps.driver_allocated_memory()}
        atomic_json(output, report)
    def timed(call):
        guard(); torch.mps.synchronize(); now = time.perf_counter(); value = call(); torch.mps.synchronize()
        seconds = time.perf_counter() - now
        if policy is not None: policy.completed(1)
        return value, seconds
    def exact(result, expected):
        require(inspect_digests(result) == tuple(expected), "GPU/native/hashlib digest mismatch")
        require(result.batch_error.cpu().tolist() == [0] and not any(result.errors.cpu().tolist()), "Digest errors in valid workload")
        words = result.words.cpu().tolist()
        require(tuple("".join(f"{word & 0xffffffff:08x}" for word in row) for row in words) == tuple(expected),
                "Raw unsigned digest word bits changed")

    persist(); prep = time.perf_counter(); messages = identity_messages(config, deadline)
    report["fixture_preparation_seconds"] = time.perf_counter() - prep
    report["population"] = "Identical exact native State byte message replicated across all lanes per case, both source and native after-effects"
    report["status"] = "running"; persist()
    for fixture in messages:
        for size in config.batch_sizes:
            guard(); values = [fixture["message"]] * size
            expected = [hashlib.sha256(value).hexdigest() for value in values]
            native_check = gwrl_cpp.campaign_content_digest_probe(values)
            require(native_check["digests"] == expected, "Native/hashlib disagreement")
            batch, upload_seconds = timed(lambda: pack_messages(values, device="mps"))
            before = tuple(value.cpu().clone() for value in (batch.data, batch.offsets, batch.count))
            case = {key: fixture[key] for key in ("family", "role", "native_checkpoint_sha256", "fixture", "draw_evidence")}
            case.update(lanes=size, bytes_per_message=len(fixture["message"]), message_sha256=expected[0],
                        uploaded_bytes=batch.data.numel(), packing_upload_seconds=upload_seconds,
                        native_rule_seconds=[], native_wrapper_seconds=[], measurements=[])
            for _ in range(config.repeats):
                guard(); now = time.perf_counter(); native = gwrl_cpp.campaign_content_digest_probe(values)
                case["native_wrapper_seconds"].append(time.perf_counter() - now)
                case["native_rule_seconds"].append(native["rules_seconds"])
                require(native["digests"] == expected, "Timed native digest changed")
            for implementation in config.implementations:
                for group in config.group_sizes:
                    operation = lambda: content_digests_metal(batch, implementation=implementation, group_size=group)
                    cold, cold_seconds = timed(operation); exact(cold, expected)
                    for _ in range(config.warmups):
                        warm, _ = timed(operation); exact(warm, expected)
                    results = []; seconds = []
                    for _ in range(config.repeats):
                        result, elapsed = timed(operation); results.append(result); seconds.append(elapsed)
                    inspect_start = time.perf_counter()
                    for result in results: exact(result, expected)
                    case["measurements"].append({"implementation": implementation, "group_size": group,
                        "cold_dispatch_seconds": cold_seconds, "warm_dispatch_seconds": seconds,
                        "inspection_seconds": time.perf_counter() - inspect_start,
                        "all_output_words_hex_counts_errors_exact": True})
                    del results, result, warm, cold
            case["source_unchanged"] = all(torch.equal(old, actual.cpu()) for old, actual in
                zip(before, (batch.data, batch.offsets, batch.count), strict=True))
            require(case["source_unchanged"], "Hash operation mutated source bytes/counts/ranges")
            case["native_hashlib_exact"] = True; report["cases"].append(case); persist()
            del batch; gc.collect(); torch.mps.empty_cache()
    report["sources_unchanged"] = pinned == provenance()
    report["status"] = "completed" if report["sources_unchanged"] else "changed_inputs"
    report["runtime_policy"] = policy.stats() if policy is not None else None
    persist(); return report


def finalize(report, config):
    expected = {(family, role, size) for family in config.families for role in ROLES for size in config.batch_sizes}
    grid = {(mode, group) for mode in config.implementations for group in config.group_sizes}
    cases = report.get("cases", [])
    def times(values): return len(values) == config.repeats and all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in values)
    def valid(case):
        rows = case.get("measurements", [])
        return (case.get("source_unchanged") is True and case.get("native_hashlib_exact") is True and
                type(case.get("bytes_per_message")) is int and case["bytes_per_message"] > 0 and
                times(case.get("native_rule_seconds", [])) and times(case.get("native_wrapper_seconds", [])) and
                len(rows) == len(grid) and {(row.get("implementation"), row.get("group_size")) for row in rows} == grid and
                all(row.get("all_output_words_hex_counts_errors_exact") is True and times(row.get("warm_dispatch_seconds", [])) for row in rows))
    matched = (report.get("schema") == SCHEMA and report.get("status") == "completed" and report.get("sources_unchanged") is True and
               len(cases) == len(expected) and {(case.get("family"), case.get("role"), case.get("lanes")) for case in cases} == expected and
               all(valid(case) for case in cases))
    report["matched_native_hashlib_and_gpu_exact"] = bool(matched)
    if report.get("status") == "completed" and not matched: report["status"] = "incomplete_or_mismatch"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=(1, 4, 16, 64))
    parser.add_argument("--families", choices=FAMILIES, nargs="+", default=FAMILIES)
    parser.add_argument("--implementations", choices=IMPLEMENTATIONS, nargs="+", default=IMPLEMENTATIONS)
    parser.add_argument("--group-sizes", nargs="+", default=("default", "1", "4", "32"))
    parser.add_argument("--repeats", type=int, default=3); parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_device", help=argparse.SUPPRESS); parser.add_argument("--_deadline", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        values = json.loads(args._worker.read_text())
        for name in ("devices", "batch_sizes", "families", "implementations", "group_sizes"): values[name] = tuple(values[name])
        worker(DigestConfig(**values), args._device, args.output, args._deadline); return 0
    groups = tuple(None if value == "default" else int(value) for value in args.group_sizes)
    config = DigestConfig(batch_sizes=tuple(args.batch_sizes), families=tuple(args.families),
        implementations=tuple(args.implementations), group_sizes=groups, repeats=args.repeats, seconds=args.seconds)
    require(not args.output.exists(), "Choose a fresh evidence path")
    report = supervise(config, "mps", args.output, deadline=time.monotonic() + config.seconds, worker_script=Path(__file__))
    report = finalize(report, config); atomic_json(args.output, report)
    return 0 if report["matched_native_hashlib_and_gpu_exact"] else 2


if __name__ == "__main__": raise SystemExit(main())
