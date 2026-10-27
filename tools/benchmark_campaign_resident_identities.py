#!/usr/bin/env python3
"""Exact State/Engine identity pipeline comparisons, outside game transitions.

Four explicit combinations compare the original/parallel-unit State serializer
and original/unrolled SHA. Complete native State bytes and both keys remain the
oracle. Capture/upload, inspection, JIT-first-call and fenced substages are
reported separately. No source certificate, State cache or rule shortcut is used.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
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
from tools.benchmark_campaign_resident_recruitment_chance import FAMILIES, lanes, resident_digest, templates

SCHEMA = "campaign-resident-identity-combinations-benchmark-v1"
SERIALIZERS = ("reference", "parallel_units")
DIGESTS = ("reference", "unrolled")
ROLES = ("source_preflight", "after_effects")
STAGES = ("state_serialize", "state_sha256", "outer_engine_json", "engine_sha256")


@dataclass(frozen=True)
class IdentityConfig(StateConfig):
    devices: tuple[str, ...] = ("mps",)
    batch_sizes: tuple[int, ...] = (1, 4, 16, 64)
    repeats: int = 3
    families: tuple[str, ...] = FAMILIES
    serializers: tuple[str, ...] = SERIALIZERS
    digests: tuple[str, ...] = DIGESTS
    digest_group_size: int | None = None
    byte_capacity: int = 262144

    def __post_init__(self):
        super().__post_init__()
        require(self.devices == ("mps",), "Identity comparison requires explicit MPS")
        for values, allowed, label in ((self.families, FAMILIES, "families"),
                                       (self.serializers, SERIALIZERS, "serializers"), (self.digests, DIGESTS, "digests")):
            require(values and len(set(values)) == len(values) and not set(values) - set(allowed),
                    f"Select distinct supported identity {label}")
        require(self.digest_group_size is None or type(self.digest_group_size) is int and self.digest_group_size > 0,
                "Digest group size must be a positive integer or default")
        require(type(self.byte_capacity) is int and self.byte_capacity > 0, "Identity output capacity must be positive; insufficient buffers fail")


def provenance():
    from tools.benchmark_campaign_backends import provenance as base
    value = base()
    value["identity_harness_sources"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        "tools/benchmark_campaign_resident_identities.py", "tools/benchmark_campaign_device_state.py",
        "tools/benchmark_campaign_resident_recruitment_chance.py", "tools/supervise_campaign_training.py",
        "studies/campaign/backends/resident_state_json.py", "studies/campaign/backends/resident_state_json_parallel.py",
        "studies/campaign/backends/canonical_json_metal.py", "studies/campaign/backends/content_digest_metal.py",
        "studies/campaign/backends/content_digest_unrolled.py", "src/python_state_json.inc")}
    return value


def fixtures(config, deadline):
    """Use precisely the controlled-minor fixtures from the identity profiler."""
    import gwrl_cpp
    prepared = templates(config, deadline)
    output = []
    for family in config.families:
        envs, evidence = lanes(prepared[family], 1, config.seed, deadline)
        before = envs[0]; original = before.serialize(); after = before.clone(); after.resolve_chance()
        for role, env, row in zip(ROLES, (before, after), gwrl_cpp.campaign_state_json_oracle([before, after]), strict=True):
            outer = b'{"rules_id":' + row["rules_json"] + b',"state_key":"' + row["state_key"].encode() + b'"}'
            require(hashlib.sha256(row["json"]).hexdigest() == row["state_key"] and
                    hashlib.sha256(outer).hexdigest() == row["engine_key"], "Native canonical bytes and keys disagree")
            output.append({"family": family, "role": role, "env": env, "native": row,
                "outer": outer, "draw_evidence": evidence[0], "serialized": env.serialize()})
        require(before.serialize() == original, "Fixture/oracle altered source history or RNG")
    return output


def digest_json(encoded, *, implementation, group_size=None):
    """The original canonical_json_digests envelope with explicit SHA selection.

    This harness-only helper retains original range construction and error ORs.
    It adds no production formatter hook or certificate issuance seam.
    """
    import torch
    from studies.campaign.backends.content_digest_metal import RangedMessageBatch, content_digests_metal
    rows, capacity = encoded.data.shape
    starts = torch.arange(rows, dtype=torch.int64, device=encoded.data.device) * capacity
    ranges = torch.stack((starts, starts + encoded.lengths), dim=1)
    result = content_digests_metal(RangedMessageBatch(encoded.data.flatten(), ranges, encoded.count),
                                   implementation=implementation, group_size=group_size)
    return replace(result, errors=result.errors | encoded.errors, batch_error=result.batch_error | encoded.batch_error)


def identities(formatter, source, *, byte_capacity, digest_implementation, digest_group_size=None,
               stages=None, synchronize=None, clock=None):
    """Run the complete identity operations; optional fences are diagnostic only."""
    from studies.campaign.backends.resident_state_json import StateIdentityBatch
    if stages is not None:
        require(synchronize is not None and clock is not None, "Fenced stages require explicit fence and clock")
        synchronize(); last = clock()
        def done(name):
            nonlocal last
            synchronize(); now = clock(); stages[name] = now - last; last = now
    else:
        def done(name): pass
    encoded = formatter.serialize(source, byte_capacity=byte_capacity); done(STAGES[0])
    state_keys = digest_json(encoded, implementation=digest_implementation, group_size=digest_group_size); done(STAGES[1])
    outer = formatter.outer_engine_json(state_keys); done(STAGES[2])
    engine_keys = digest_json(outer, implementation=digest_implementation, group_size=digest_group_size); done(STAGES[3])
    return StateIdentityBatch(source, encoded, state_keys, outer, engine_keys)


def check_identity(actual, expected, native, outer, lanes):
    """Explicit post-timer, complete byte/metadata comparison and native oracle."""
    import torch
    from studies.campaign.backends.content_digest_metal import inspect_digests
    require(actual.source is expected.source, "Identity lost exact source binding")
    for name in ("state_json", "state_keys", "engine_json", "engine_keys"):
        left, right = getattr(actual, name), getattr(expected, name)
        require(type(left) is type(right), "Identity output type changed")
        for field in left.__dataclass_fields__:
            require(torch.equal(getattr(left, field), getattr(right, field)), f"Identity {name}.{field} changed")
    for encoded, content in ((actual.state_json, native["json"]), (actual.engine_json, outer)):
        require(encoded.batch_error.cpu().tolist() == [0] and encoded.errors.cpu().tolist() == [0] * lanes,
                "Native identity workload reported a serialization error")
        lengths = encoded.lengths.cpu().tolist()
        require(lengths == [len(content)] * lanes and encoded.required_bytes.cpu().tolist() == lengths,
                "Full native identity byte count changed")
        data = encoded.data.cpu().numpy()
        require(all(bytes(row[:length]) == content for row, length in zip(data, lengths, strict=True)),
                "Native identity bytes changed")
    require(inspect_digests(actual.state_keys) == (native["state_key"],) * lanes and
            inspect_digests(actual.engine_keys) == (native["engine_key"],) * lanes, "Native State or Engine key changed")


def worker(config, device, output, deadline):
    import torch, gwrl_cpp
    from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
    from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
    from studies.campaign.backends.resident_state_json import ResidentStateJson
    from studies.campaign.backends.resident_state_json_parallel import ParallelUnitStateJson
    from studies.campaign.device_runtime import runtime_policy_for_device
    require(device == "mps" and torch.backends.mps.is_available(), "Explicit MPS required; no CPU fallback")
    torch.set_num_threads(config.threads); torch.set_num_interop_threads(1)
    torch.mps.set_per_process_memory_fraction(3_000_000_000 / torch.mps.recommended_max_memory())
    policy = runtime_policy_for_device(device)
    start = time.perf_counter(); pinned = provenance()
    report = {"schema": SCHEMA, "status": "preparing", "config": asdict(config), "provenance": pinned,
        "cases": [], "scope": __doc__, "source_identity_certificate_used": False,
        "software": {"torch": torch.__version__, "python": sys.version, "threads": torch.get_num_threads(),
                     "interop_threads": torch.get_num_interop_threads()},
        "timing": "Unfenced four-operation pipeline with one final device fence; separately fenced substages are intrusive diagnostics",
        "population": "Same exact native source/after-effects State replicated across all lanes; complete history/RNG kept in source",
        "parallel_unit_threadgroup_size": 32}
    def guard(): require(time.monotonic() < deadline, "Shared identity benchmark deadline exhausted")
    def persist():
        report["elapsed_worker_seconds"] = time.perf_counter() - start
        report["device_memory"] = {"live_bytes": torch.mps.current_allocated_memory(), "driver_bytes": torch.mps.driver_allocated_memory()}
        atomic_json(output, report)
    def timed(call):
        guard(); torch.mps.synchronize(); now = time.perf_counter(); result = call(); torch.mps.synchronize()
        seconds = time.perf_counter() - now
        if policy is not None: policy.completed(1)
        return result, seconds
    persist(); prep = time.perf_counter(); prepared = fixtures(config, deadline)
    report["native_fixture_preparation_seconds"] = time.perf_counter() - prep
    report["status"] = "running"; persist()
    for fixture in prepared:
        for B in config.batch_sizes:
            guard(); setup = time.perf_counter(); raw = fixture["env"]
            native_context = gwrl_cpp.device_state_context(raw)
            context, static_seconds = timed(lambda: DeviceStateContext(native_context, "mps"))
            captured = gwrl_cpp.capture_device_states(native_context, [raw] * B)
            source, upload_seconds = timed(lambda: DeviceStateBatch.from_native(captured, context=context))
            numbers, number_seconds = timed(lambda: CanonicalJsonContext(captured, context))
            formatters = {"reference": ResidentStateJson(numbers), "parallel_units": ParallelUnitStateJson(numbers)}
            before = resident_digest(source)
            expected = ResidentStateJson.identities(formatters["reference"], source, byte_capacity=config.byte_capacity)
            torch.mps.synchronize()
            check_identity(expected, expected, fixture["native"], fixture["outer"], B)
            # Structural diagnostics are explicit setup inspection, never hot
            # predicates or a limit on the actual unit map.
            records = source.records.cpu().numpy(); roots = source.section("state.units").cpu().tolist()
            units = [int(records[i, root, 1]) for i, root in enumerate(roots)]
            K = source.records.shape[1]; U = max(K // 16, 1)
            case = {key: fixture[key] for key in ("family", "role", "draw_evidence")}
            case.update(lanes=B, message_bytes=len(fixture["native"]["json"]), state_key=fixture["native"]["state_key"],
                engine_key=fixture["native"]["engine_key"], native_checkpoint_sha256=hashlib.sha256(fixture["serialized"].encode()).hexdigest(),
                static_context_upload_seconds=static_seconds, state_upload_seconds=upload_seconds, number_context_seconds=number_seconds,
                complete_setup_seconds=time.perf_counter() - setup, record_capacity=K, actual_units_per_lane=units,
                parallel_unit_task_capacity_per_lane=U, allocated_unit_tasks=B * U, active_unit_tasks=sum(units),
                full_stack_scratch_bytes=B * K * 5 * 8, unit_task_scratch_bytes=B * U * (4 * 8 + 4), measurements=[])
            for serializer in config.serializers:
                for digest in config.digests:
                    formatter = formatters[serializer]
                    operation = lambda: identities(formatter, source, byte_capacity=config.byte_capacity,
                        digest_implementation=digest, digest_group_size=config.digest_group_size)
                    cold, cold_seconds = timed(operation)
                    check_identity(cold, expected, fixture["native"], fixture["outer"], B)
                    for _ in range(config.warmups):
                        warm, _ = timed(operation); check_identity(warm, expected, fixture["native"], fixture["outer"], B)
                    durations = []; fenced = []; inspections = []
                    for _ in range(config.repeats):
                        result, seconds = timed(operation); durations.append(seconds)
                        inspect_start = time.perf_counter(); check_identity(result, expected, fixture["native"], fixture["outer"], B)
                        inspections.append(time.perf_counter() - inspect_start)
                    for _ in range(config.repeats):
                        guard(); stages = {}
                        result = identities(formatter, source, byte_capacity=config.byte_capacity,
                            digest_implementation=digest, digest_group_size=config.digest_group_size,
                            stages=stages, synchronize=torch.mps.synchronize, clock=time.perf_counter)
                        fenced.append(stages)
                        if policy is not None: policy.completed(1)
                        check_identity(result, expected, fixture["native"], fixture["outer"], B)
                    case["measurements"].append({"serializer": serializer, "digest": digest,
                        "cold_pipeline_seconds": cold_seconds, "warm_pipeline_seconds": durations,
                        "fenced_substage_seconds": fenced, "inspection_seconds": inspections,
                        "all_native_bytes_words_keys_counts_errors_and_padding_exact": True})
                    del result, cold, warm
            case["source_unchanged"] = resident_digest(source) == before and raw.serialize() == fixture["serialized"]
            require(case["source_unchanged"], "Identity calculation changed source State/history/RNG")
            report["cases"].append(case); persist()
            del source, context, captured, native_context, numbers, formatters, formatter, expected, records
            gc.collect(); torch.mps.empty_cache()
    report["sources_unchanged"] = pinned == provenance()
    report["runtime_policy"] = policy.stats() if policy is not None else None
    report["status"] = "completed" if report["sources_unchanged"] else "changed_inputs"
    persist(); return report


def finalize(report, config):
    grid = {(serializer, digest) for serializer in config.serializers for digest in config.digests}
    population = {(family, role, B) for family in config.families for role in ROLES for B in config.batch_sizes}
    cases = report.get("cases", [])
    def finite(value): return type(value) in (int, float) and math.isfinite(value) and value >= 0
    def sha(value): return isinstance(value, str) and len(value) == 64 and not set(value) - set("0123456789abcdef")
    def valid(case):
        rows = case.get("measurements", [])
        return (case.get("source_unchanged") is True and
                all(sha(case.get(name)) for name in ("state_key", "engine_key", "native_checkpoint_sha256")) and
                type(case.get("message_bytes")) is int and case["message_bytes"] > 0 and len(rows) == len(grid) and
                {(row.get("serializer"), row.get("digest")) for row in rows} == grid and
                all(row.get("all_native_bytes_words_keys_counts_errors_and_padding_exact") is True and
                    len(row.get("warm_pipeline_seconds", [])) == config.repeats and all(finite(t) for t in row["warm_pipeline_seconds"]) and
                    len(row.get("fenced_substage_seconds", [])) == config.repeats and all(set(stage) == set(STAGES) and
                        all(finite(t) for t in stage.values()) for stage in row["fenced_substage_seconds"]) for row in rows))
    exact = (report.get("schema") == SCHEMA and report.get("status") == "completed" and report.get("sources_unchanged") is True and
             report.get("source_identity_certificate_used") is False and len(cases) == len(population) and
             {(case.get("family"), case.get("role"), case.get("lanes")) for case in cases} == population and all(valid(case) for case in cases))
    if exact:
        exact = all(len({(case["state_key"], case["engine_key"], case["native_checkpoint_sha256"], case["message_bytes"])
                         for case in cases if (case["family"], case["role"]) == (family, role)}) == 1
                    for family in config.families for role in ROLES)
    report["matched_complete_native_identity_pipeline"] = bool(exact)
    if report.get("status") == "completed" and not exact: report["status"] = "incomplete_or_mismatch"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path); parser.add_argument("--batch-sizes", type=int, nargs="+", default=(1,4,16,64))
    parser.add_argument("--families", choices=FAMILIES, nargs="+", default=FAMILIES)
    parser.add_argument("--serializers", choices=SERIALIZERS, nargs="+", default=SERIALIZERS)
    parser.add_argument("--digests", choices=DIGESTS, nargs="+", default=DIGESTS)
    parser.add_argument("--digest-group-size", type=int); parser.add_argument("--byte-capacity", type=int, default=262144)
    parser.add_argument("--repeats", type=int, default=3); parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS); parser.add_argument("--_device", help=argparse.SUPPRESS)
    parser.add_argument("--_deadline", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        values = json.loads(args._worker.read_text())
        for name in ("devices", "batch_sizes", "families", "serializers", "digests"): values[name] = tuple(values[name])
        worker(IdentityConfig(**values), args._device, args.output, args._deadline); return 0
    config = IdentityConfig(batch_sizes=tuple(args.batch_sizes), families=tuple(args.families), serializers=tuple(args.serializers),
        digests=tuple(args.digests), digest_group_size=args.digest_group_size, byte_capacity=args.byte_capacity,
        repeats=args.repeats, seconds=args.seconds)
    require(not args.output.exists(), "Choose a fresh evidence path")
    report = supervise(config, "mps", args.output, deadline=time.monotonic() + config.seconds, worker_script=Path(__file__))
    report = finalize(report, config); atomic_json(args.output, report)
    return 0 if report["matched_complete_native_identity_pipeline"] else 2


if __name__ == "__main__": raise SystemExit(main())
