#!/usr/bin/env python3
"""Explicit intrusive recruitment-effects diagnostics inside full transitions.

Production apply/menu implementations remain the sole implementations. During a
capture only, scoped wrappers fence existing calls and retain their returned
objects for exact post-timer comparison. Nested inclusive/exclusive spans and
setup/publication gaps are diagnostics, never self-play throughput estimates.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
from dataclasses import asdict, dataclass, fields, is_dataclass
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from tools.benchmark_campaign_device_state import StateConfig, atomic_json, require, supervise
from tools.benchmark_campaign_resident_recruitment_chance import (
    FAMILIES, canonical_native, lanes, require_exact, resident_digest, templates,
)

SCHEMA = "campaign-recruitment-effects-substage-profile-v1"
_patch_lock = threading.Lock()


@dataclass(frozen=True)
class Binding:
    owner: object
    name: str
    labels: tuple[str, ...]


@dataclass(frozen=True)
class Span:
    label: str
    parent: int | None
    result: object
    seconds: float | None
    exclusive_seconds: float | None
    start: float | None
    end: float | None


@dataclass(frozen=True)
class EffectsCall:
    source: object
    result: object
    spans: tuple[Span, ...]
    timed: bool
    total_seconds: float | None
    prepare_seconds: float | None
    between_call_seconds: float | None
    publish_seconds: float | None


def effect_bindings(delegate):
    """Audited original call sequence, with nested menu helpers kept separate."""
    from studies.campaign.backends import resident_recruitment_effects as effects
    from studies.campaign.backends import resident_recruitment as recruitment
    menu = delegate.recruitment
    return (
        Binding(effects, "_call", ("validate_sample", "summarize_menu", "prepare_decision", "write_decisions")),
        Binding(effects, "replace_subtrees", ("chance_clear",)),
        Binding(effects, "build_map_edits", ("pending_erase_build", "flags_build", "continuation_build")),
        Binding(effects, "commit_container_edits", ("pending_erase_commit", "flags_commit", "continuation_commit", "decisions_commit")),
        Binding(effects, "build_sequence_splices", ("decisions_build",)),
        Binding(effects, "intern_bytes", ("decision_name_intern",)),
        Binding(type(menu), "choices", ("choices",)),
        Binding(type(menu), "query", ("query",)),
        Binding(type(menu), "_menu", ("menu",)),
        Binding(type(menu.relations_context), "compute", ("relations",)),
        Binding(recruitment, "canonical_json_subtrees", ("parameter_json",)),
        Binding(recruitment, "canonical_json_digests", ("parameter_hash",)),
        Binding(recruitment, "action_id_strings", ("action_id_fields",)),
        Binding(recruitment, "construct_action_ids", ("action_id_bytes",)),
        Binding(recruitment, "intern_bytes", ("action_id_intern",)),
    )


EXPECTED_LABELS = (
    "validate_sample", "chance_clear", "pending_erase_build", "pending_erase_commit",
    "choices", "query", "relations", "menu", "parameter_json", "parameter_hash",
    "action_id_fields", "action_id_bytes", "action_id_intern", "summarize_menu",
    "prepare_decision", "decision_name_intern", "flags_build", "flags_commit",
    "continuation_build", "continuation_commit", "write_decisions", "decisions_build", "decisions_commit",
)


class EffectsStageProfiler:
    """Inactive calls delegate unchanged; capture owns only scoped call wrappers.

    Captures cannot nest or overlap process-wide module patching. The module
    functions/class methods are restored before apply returns or raises. Return
    objects are retained, not copied; this extends allocation lifetimes and is
    another reason to treat captured times as intrusive diagnostics.
    """
    def __init__(self, delegate, *, synchronize=None, clock=None, bindings=None):
        if synchronize is None:
            import torch
            synchronize = torch.mps.synchronize
        self.delegate = delegate
        self.synchronize = synchronize
        self.clock = clock or time.perf_counter
        self.bindings = bindings or effect_bindings
        self._capture = None

    def __getattr__(self, name): return getattr(self.delegate, name)

    @contextmanager
    def capture(self, *, timed=True):
        if type(timed) is not bool: raise TypeError("Capture timing must be explicit bool")
        if self._capture is not None: raise RuntimeError("Effects captures cannot nest")
        calls = []; self._capture = (calls, timed)
        try: yield calls
        finally: self._capture = None

    def apply(self, before, *args, **kwargs):
        if self._capture is None: return self.delegate.apply(before, *args, **kwargs)
        if not _patch_lock.acquire(blocking=False): raise RuntimeError("Effects profiling patches cannot overlap")
        calls, timed = self._capture
        events = []; stack = []; counts = []; started = None
        try:
            specifications = tuple(self.bindings(self.delegate))
            require(len({(id(spec.owner), spec.name) for spec in specifications}) == len(specifications), "Duplicate profile binding")
            if timed: self.synchronize(); started = self.clock()
            with ExitStack() as patches:
                for spec in specifications:
                    original = getattr(spec.owner, spec.name); index = len(counts); counts.append(0)
                    def wrapped(*values, _spec=spec, _original=original, _index=index, **options):
                        ordinal = counts[_index]; counts[_index] += 1
                        if ordinal >= len(_spec.labels): raise RuntimeError("Audited effects call count changed: " + _spec.name)
                        label = _spec.labels[ordinal]
                        if timed: self.synchronize(); beginning = self.clock()
                        else: beginning = None
                        parent = stack[-1] if stack else None
                        at = len(events); events.append(None); stack.append(at)
                        try: result = _original(*values, **options)
                        finally:
                            if timed: self.synchronize(); ending = self.clock()
                            else: ending = None
                            stack.pop()
                        duration = ending - beginning if timed else None
                        children = sum(event.seconds for event in events if event is not None and event.parent == at) if timed else None
                        events[at] = Span(label, parent, result, duration, max(0., duration - children) if timed else None, beginning, ending)
                        return result
                    patches.enter_context(patch.object(spec.owner, spec.name, wrapped))
                result = self.delegate.apply(before, *args, **kwargs)
                for spec, count in zip(specifications, counts, strict=True):
                    if count != len(spec.labels): raise RuntimeError("Audited effects call count changed: " + spec.name)
                if timed: self.synchronize(); ending = self.clock()
                else: ending = None
            top = [event for event in events if event.parent is None]
            if timed:
                prepare = (top[0].start - started) if top else ending - started
                between = sum(right.start - left.end for left, right in zip(top, top[1:]))
                publication = ending - top[-1].end if top else 0.
            else: prepare = between = publication = None
            call = EffectsCall(before, result, tuple(events), timed, ending - started if timed else None,
                               prepare, between, publication)
            calls.append(call)
            return result
        finally: _patch_lock.release()


def compare_results(actual, expected):
    """Explicit host verification of all dataclass fields and every tensor bit."""
    import torch
    seen = set(); count = 0; bytes_checked = 0
    def visit(left, right):
        nonlocal count, bytes_checked
        key = id(left), id(right)
        if key in seen: return
        seen.add(key)
        if isinstance(left, torch.Tensor):
            require(isinstance(right, torch.Tensor) and left.dtype == right.dtype and left.device == right.device and
                    left.layout == right.layout == torch.strided and tuple(left.shape) == tuple(right.shape) and
                    left.stride() == right.stride() and left.storage_offset() == right.storage_offset() and
                    left.requires_grad == right.requires_grad and torch.equal(left, right), "Profiled tensor bits/metadata changed")
            count += 1; bytes_checked += left.numel() * left.element_size(); return
        require(type(left) is type(right), "Profiled return type changed")
        if is_dataclass(left):
            for field in fields(left): visit(getattr(left, field.name), getattr(right, field.name))
        elif isinstance(left, dict):
            require(left.keys() == right.keys(), "Profiled return mapping changed")
            for name in left: visit(left[name], right[name])
        elif isinstance(left, (tuple, list)):
            require(len(left) == len(right), "Profiled return sequence changed")
            for a, b in zip(left, right, strict=True): visit(a, b)
        elif isinstance(left, (str, int, float, bool, bytes)) or left is None:
            require(left == right, "Profiled scalar return changed")
        else: require(left is right, "Profiled shared context identity changed")
    visit(actual, expected)
    return {"all_return_bytes_and_metadata_exact": True, "compared_tensors": count, "compared_tensor_bytes": bytes_checked}


def compare_calls(actual, expected):
    require(actual.source is expected.source, "Profile source binding changed")
    require([span.label for span in actual.spans] == [span.label for span in expected.spans] and
            [span.parent for span in actual.spans] == [span.parent for span in expected.spans], "Profiled call order/nesting changed")
    comparisons = [compare_results(actual.result, expected.result)]
    comparisons += [compare_results(a.result, b.result) for a, b in zip(actual.spans, expected.spans, strict=True)]
    return {"all_return_bytes_and_metadata_exact": True, "compared_tensors": sum(row["compared_tensors"] for row in comparisons),
            "compared_tensor_bytes": sum(row["compared_tensor_bytes"] for row in comparisons)}


def describe(call):
    require(call.timed, "Untimed observations are not timings")
    return {"total_effects_seconds": call.total_seconds, "prepare_seconds": call.prepare_seconds,
            "between_call_setup_seconds": call.between_call_seconds, "final_publish_seconds": call.publish_seconds,
            "spans": [{"label": span.label, "parent": span.parent, "inclusive_seconds": span.seconds,
                       "exclusive_seconds": span.exclusive_seconds} for span in call.spans]}


@dataclass(frozen=True)
class EffectsConfig(StateConfig):
    devices: tuple[str, ...] = ("mps",)
    batch_sizes: tuple[int, ...] = (1, 64)
    repeats: int = 3
    families: tuple[str, ...] = FAMILIES

    def __post_init__(self):
        super().__post_init__()
        require(self.devices == ("mps",), "Effects diagnostics require explicit MPS")
        require(self.families and len(set(self.families)) == len(self.families) and not set(self.families) - set(FAMILIES),
                "Select distinct supported effects fixture families")


def provenance():
    from tools.benchmark_campaign_backends import provenance as base
    value = base()
    value["effects_profile_sources"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        "tools/profile_campaign_recruitment_effects.py", "tools/benchmark_campaign_device_state.py",
        "tools/benchmark_campaign_resident_recruitment_chance.py", "tools/supervise_campaign_training.py")}
    return value


def static_digest(state):
    from tools.benchmark_campaign_backends import numeric_digest
    return numeric_digest({name: getattr(state.context, name).detach().cpu().numpy()
                           for name in ("records", "string_bytes", "string_offsets")})


def worker(config, device, output, deadline):
    import torch, gwrl_cpp
    from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
    from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
    from studies.campaign.backends.resident_recruitment import ResidentRecruitment
    from studies.campaign.backends.resident_recruitment_effects import ResidentRecruitmentEffects
    from studies.campaign.backends.resident_state_income import ResidentIncomeContext
    from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
    from studies.campaign.backends.resident_state_json_parallel import ParallelUnitStateJson
    from studies.campaign.backends.content_digest_metal import inspect_digests
    from studies.campaign.backends.resident_recruitment_chance import ResidentRecruitmentChance, RecruitmentChanceCapacities
    require(device == "mps", "Effects profile has no CPU fallback")
    torch.set_num_threads(config.threads); torch.set_num_interop_threads(1)
    torch.mps.set_per_process_memory_fraction(3_000_000_000 / torch.mps.recommended_max_memory())
    start = time.perf_counter(); pinned = provenance(); prepared = templates(config, deadline)
    report = {"schema": SCHEMA, "status": "running", "config": asdict(config), "provenance": pinned, "cases": [],
        "scope": __doc__, "selected_implementation": {"formatter": "parallel_units", "digest": "unrolled", "certified_source_reuse": True},
        "timing_scope": "Existing effects.apply with explicit nested fences; other full-handler stages remain unprofiled",
        "allocation_lifetimes": "Existing return objects retained until outside-timer exact verification; no extra state copies, but lifetimes increase",
        "fixture_scope": "Same controlled-minor legal recruitment rolls as the complete-step comparison; not a campaign-position distribution"}
    def guard(): require(time.monotonic() < deadline, "Shared effects diagnostic deadline exhausted")
    def save():
        report["worker_elapsed_seconds"] = time.perf_counter() - start
        atomic_json(output, report)
    save()
    for family in config.families:
        for B in config.batch_sizes:
            guard(); setup = time.perf_counter(); envs, evidence = lanes(prepared[family], B, config.seed, deadline)
            original_native = [env.serialize() for env in envs]
            context = DeviceStateContext(gwrl_cpp.device_state_context(envs[0]), "mps")
            native = gwrl_cpp.capture_device_states(context.native, envs)
            before = DeviceStateBatch.from_native(native, context=context)
            relations = ResidentPoliticalRelations(context, gwrl_cpp.campaign_relations_context(envs[0]))
            recruitment = ResidentRecruitment(relations, gwrl_cpp.campaign_recruitment_context(envs[0]))
            formatter = ParallelUnitStateJson(CanonicalJsonContext(native, context), digest_implementation="unrolled")
            effects = ResidentRecruitmentEffects(recruitment); profiled = EffectsStageProfiler(effects)
            handler = ResidentRecruitmentChance(context, effects,
                ResidentIncomeContext(context, gwrl_cpp.campaign_income_context(envs[0])), formatter, reuse_certified_source=True)
            maximum = prepared[family]["choices"]; C = before.records.shape[1]; N = len(relations.nation_ids)
            cap = C + 7 + 14 * maximum + 4 * N + 64; choices = B * maximum
            caps = RecruitmentChanceCapacities(cap, cap, choices, 512,
                before.string_offsets.numel() - 1 + choices + 2 * B,
                before.string_bytes.numel() + choices * recruitment.id_capacity + 94 * B, 9, 262144, 1, 1)
            before = handler.reserve(before, caps); expected = formatter.identities(before, byte_capacity=caps.json_byte_capacity)
            source_hash, context_hash = resident_digest(before), static_digest(before)
            require(inspect_digests(expected.engine_keys) == tuple(env.planning_key() for env in envs), "Source native Engine keys differ")
            futures = [env.clone() for env in envs]
            for env in futures: env.resolve_chance()
            expected_native = canonical_native(gwrl_cpp.capture_device_states(context.native, futures))
            output_keys = tuple(env.planning_key() for env in futures)
            for _ in range(config.warmups):
                guard(); warmed = handler.resolve(before, expected, capacities=caps); torch.mps.synchronize()
                require(warmed.committed.item(), "Unprofiled warmup failed")
                require_exact(warmed.state.to_native(), expected_native)
            ordinary = handler.resolve(before, expected, capacities=caps); torch.mps.synchronize()
            require(ordinary.committed.item(), "Original complete transition failed")
            require_exact(ordinary.state.to_native(), expected_native)
            handler.effects = profiled
            with profiled.capture(timed=False) as observed_calls:
                observed = handler.resolve(before, expected, capacities=caps)
            torch.mps.synchronize()
            require(len(observed_calls) == 1, "Handler changed its effects invocation count")
            require([span.label for span in observed_calls[0].spans] == list(EXPECTED_LABELS), "Audited effects call trace changed")
            observed_proof = compare_results(observed, ordinary)
            require_exact(observed.state.to_native(), expected_native)
            case = {"family": family, "lanes": B, "fixtures": evidence, "capacities": asdict(caps),
                "source_buffer_sha256": source_hash, "static_context_sha256": context_hash,
                "native_output_record_sha256": expected_native[3], "setup_seconds": time.perf_counter() - setup,
                "untimed_wrapper_all_outputs_exact": observed_proof, "profiles": []}
            for _ in range(config.repeats):
                guard()
                with profiled.capture() as calls:
                    result = handler.resolve(before, expected, capacities=caps)
                torch.mps.synchronize(); checked = time.perf_counter()
                require(len(calls) == 1 and result.committed.item(), "Profiled complete transition failed")
                whole = compare_results(result, ordinary); intermediate = compare_calls(calls[0], observed_calls[0])
                require_exact(result.state.to_native(), expected_native)
                require(inspect_digests(result.identities.engine_keys) == output_keys, "Profiled native output Engine key differs")
                case["profiles"].append({**describe(calls[0]), "complete_output_proof": whole,
                    "intermediate_output_proof": intermediate, "full_native_state_history_rng_and_engine_keys_exact": True,
                    "verification_seconds": time.perf_counter() - checked})
                del result, calls
            case["source_unchanged"] = (resident_digest(before) == source_hash and static_digest(before) == context_hash and
                                        [env.serialize() for env in envs] == original_native)
            require(case["source_unchanged"], "Profiled effects changed source State/history/RNG/static buffers")
            report["cases"].append(case); save()
            del ordinary, observed, observed_calls, warmed, handler, profiled, effects, recruitment, relations
            del before, expected, native, context, futures, expected_native, formatter
            gc.collect(); torch.mps.empty_cache()
    report["sources_unchanged"] = pinned == provenance()
    report["status"] = "completed" if report["sources_unchanged"] else "changed_inputs"
    save(); return report


def finalize(report, config):
    expected = {(family, B) for family in config.families for B in config.batch_sizes}
    def finite(value): return type(value) in (int, float) and math.isfinite(value) and value >= 0
    def proof(value):
        return isinstance(value, dict) and value.get("all_return_bytes_and_metadata_exact") is True and value.get("compared_tensors", 0) > 0
    def profile(row):
        spans = row.get("spans", [])
        return (row.get("full_native_state_history_rng_and_engine_keys_exact") is True and
                proof(row.get("complete_output_proof")) and proof(row.get("intermediate_output_proof")) and
                all(finite(row.get(name)) for name in ("total_effects_seconds", "prepare_seconds", "between_call_setup_seconds", "final_publish_seconds")) and
                [span.get("label") for span in spans] == list(EXPECTED_LABELS) and
                all(finite(span.get("inclusive_seconds")) and finite(span.get("exclusive_seconds")) and
                    span["exclusive_seconds"] <= span["inclusive_seconds"] and
                    (span.get("parent") is None or type(span["parent"]) is int and 0 <= span["parent"] < i)
                    for i, span in enumerate(spans)))
    cases = report.get("cases", [])
    exact = (report.get("schema") == SCHEMA and report.get("status") == "completed" and report.get("sources_unchanged") is True and
             len(cases) == len(expected) and {(case.get("family"), case.get("lanes")) for case in cases} == expected and
             all(case.get("source_unchanged") is True and proof(case.get("untimed_wrapper_all_outputs_exact")) and
                 len(case.get("profiles", [])) == config.repeats and all(profile(row) for row in case["profiles"]) for case in cases))
    report["effects_profile_exact"] = bool(exact)
    if report.get("status") == "completed" and not exact: report["status"] = "incomplete_or_mismatch"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path); parser.add_argument("--batch-sizes", nargs="+", type=int, default=(1,64))
    parser.add_argument("--families", choices=FAMILIES, nargs="+", default=FAMILIES)
    parser.add_argument("--repeats", type=int, default=3); parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS); parser.add_argument("--_device", help=argparse.SUPPRESS)
    parser.add_argument("--_deadline", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        settings = json.loads(args._worker.read_text())
        for key in ("devices", "batch_sizes", "families"): settings[key] = tuple(settings[key])
        worker(EffectsConfig(**settings), args._device, args.output, args._deadline); return 0
    config = EffectsConfig(batch_sizes=tuple(args.batch_sizes), families=tuple(args.families), repeats=args.repeats, seconds=args.seconds)
    require(not args.output.exists(), "Choose a fresh evidence path")
    result = supervise(config, "mps", args.output, deadline=time.monotonic() + config.seconds, worker_script=Path(__file__))
    result = finalize(result, config); atomic_json(args.output, result)
    return 0 if result["effects_profile_exact"] else 2


if __name__ == "__main__": raise SystemExit(main())
