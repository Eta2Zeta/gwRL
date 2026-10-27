#!/usr/bin/env python3
"""Intrusive income-refresh diagnostics inside complete recruitment transitions.

Only an explicit capture fences calls. The original extractor, income-rate
kernel, full-State writer and subtree editor remain the sole implementations.
Writer buffers and returned objects are retained for exact outside-timer checks;
these fenced timings and extended lifetimes are not self-play throughput.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from tools.benchmark_campaign_device_state import StateConfig, atomic_json, require, supervise
from tools.benchmark_campaign_resident_recruitment_chance import (
    FAMILIES, canonical_native, lanes, require_exact, resident_digest, templates,
)
from tools.profile_campaign_recruitment_effects import (
    Binding, EffectsCall, EffectsStageProfiler, compare_results as _compare_results, describe, static_digest,
)

SCHEMA = "campaign-resident-income-refresh-substage-profile-v1"
EXPECTED_LABELS = ("extract", "income_rates", "state_writer", "editor")


@dataclass(frozen=True)
class WriterOutputs:
    blocks: object
    lengths: object
    errors: object


@dataclass(frozen=True)
class IncomeCall:
    execution: EffectsCall
    writer_outputs: WriterOutputs


class _WriterDispatch:
    def __init__(self): self.original = None; self.outputs = []

    def write(self, *args, **kwargs):
        result = self.original(*args, **kwargs)
        # Complete original write_resident_income ABI. Retain references, do not
        # copy or inspect them; the native writer returns None.
        require(len(args) == 16, "Audited income writer argument count changed")
        self.outputs.append(WriterOutputs(args[11], args[12], args[13]))
        return result


class _LibraryProxy:
    def __init__(self, library, dispatcher): self.library = library; self.dispatcher = dispatcher

    def __getattr__(self, name):
        if name != "write_resident_income": return getattr(self.library, name)
        self.dispatcher.original = self.library.write_resident_income
        return self.dispatcher.write


class _RefreshDelegate:
    """Install the kernel proxy only after the shared profiler patch lock."""
    def __init__(self, income, income_module, editor_module):
        self.income = income; self.module = income_module; self.editor = editor_module
        self.original_getter = income_module._kernels; self.dispatcher = _WriterDispatch()

    def bindings(self, _):
        return (
            Binding(self.income, "extract", ("extract",)),
            Binding(self.income.ledger_context.income, "compute", ("income_rates",)),
            Binding(self.dispatcher, "write", ("state_writer",)),
            Binding(self.editor, "replace_subtrees", ("editor",)),
        )

    def apply(self, before, *args, **kwargs):
        def get_library(): return _LibraryProxy(self.original_getter(), self.dispatcher)
        with patch.object(self.module, "_kernels", get_library):
            return self.income.refresh(before, *args, **kwargs)


class IncomeStageProfiler:
    """Service-scoped capture; inactive refresh is a literal delegation.

    Optional modules permit the same audited wrapper to be checked with small
    deterministic services. The actual worker always uses the production income
    and editor modules. The shared EffectsStageProfiler lock forbids overlapping
    process-wide patches, including captures from the effects diagnostic tool.
    """
    def __init__(self, delegate, *, synchronize=None, clock=None, income_module=None, editor_module=None):
        if income_module is None:
            from studies.campaign.backends import resident_state_income as income_module
        if editor_module is None:
            from studies.campaign.backends import device_state_edits as editor_module
        self.delegate = delegate; self.income_module = income_module; self.editor_module = editor_module
        self.synchronize = synchronize; self.clock = clock; self._capture = None

    def __getattr__(self, name): return getattr(self.delegate, name)

    @contextmanager
    def capture(self, *, timed=True):
        if type(timed) is not bool: raise TypeError("Capture timing must be explicit bool")
        if self._capture is not None: raise RuntimeError("Income captures cannot nest")
        calls = []; self._capture = (calls, timed)
        try: yield calls
        finally: self._capture = None

    def refresh(self, before, *args, **kwargs):
        if self._capture is None: return self.delegate.refresh(before, *args, **kwargs)
        destination, timed = self._capture
        adapter = _RefreshDelegate(self.delegate, self.income_module, self.editor_module)
        profiler = EffectsStageProfiler(adapter, synchronize=self.synchronize, clock=self.clock, bindings=adapter.bindings)
        with profiler.capture(timed=timed) as calls:
            result = profiler.apply(before, *args, **kwargs)
        require(len(calls) == 1 and len(adapter.dispatcher.outputs) == 1,
                "Audited income refresh/writer call count changed")
        require(tuple(span.label for span in calls[0].spans) == EXPECTED_LABELS and
                all(span.parent is None for span in calls[0].spans), "Audited income refresh call trace changed")
        destination.append(IncomeCall(calls[0], adapter.dispatcher.outputs[0]))
        return result


def compare_results(actual, expected):
    """Check complete output bytes plus storage capacity and version metadata."""
    import torch
    from dataclasses import fields, is_dataclass
    result = _compare_results(actual, expected)
    seen = set()
    def check(left, right):
        key = id(left), id(right)
        if key in seen: return
        seen.add(key)
        if isinstance(left, torch.Tensor):
            left_version = None if left.is_inference() else left._version
            right_version = None if right.is_inference() else right._version
            require(left.is_inference() == right.is_inference() and left_version == right_version and
                    left.is_leaf == right.is_leaf and left.untyped_storage().nbytes() == right.untyped_storage().nbytes(),
                    "Profiled tensor storage/version metadata changed")
        elif is_dataclass(left):
            for field in fields(left): check(getattr(left, field.name), getattr(right, field.name))
        elif isinstance(left, dict):
            for name in left: check(left[name], right[name])
        elif isinstance(left, (tuple, list)):
            for a, b in zip(left, right, strict=True): check(a, b)
    check(actual, expected)
    return result


def compare_calls(actual, expected):
    """Full inputs may be fresh intermediate allocations of the same handler."""
    left, right = actual.execution, expected.execution
    require([span.label for span in left.spans] == [span.label for span in right.spans] and
            [span.parent for span in left.spans] == [span.parent for span in right.spans],
            "Profiled income call order/nesting changed")
    pairs = [(left.source, right.source), (left.result, right.result),
             (actual.writer_outputs, expected.writer_outputs)]
    pairs.extend((a.result, b.result) for a, b in zip(left.spans, right.spans, strict=True))
    proofs = [compare_results(a, b) for a, b in pairs]
    return {"all_return_bytes_and_metadata_exact": True,
            "compared_tensors": sum(row["compared_tensors"] for row in proofs),
            "compared_tensor_bytes": sum(row["compared_tensor_bytes"] for row in proofs)}


def describe_call(call):
    result = describe(call.execution)
    result["total_income_refresh_seconds"] = result.pop("total_effects_seconds")
    return result


@dataclass(frozen=True)
class IncomeConfig(StateConfig):
    devices: tuple[str, ...] = ("mps",)
    batch_sizes: tuple[int, ...] = (1, 64)
    repeats: int = 3
    families: tuple[str, ...] = FAMILIES
    editor_implementation: str = "reference"
    container_implementation: str = "reference"

    def __post_init__(self):
        super().__post_init__()
        require(self.devices == ("mps",), "Income diagnostics require explicit MPS")
        require(self.families and len(set(self.families)) == len(self.families) and not set(self.families) - set(FAMILIES),
                "Select distinct supported income fixture families")
        require(self.editor_implementation in {"reference", "parallel"} and
                self.container_implementation in {"reference", "parallel"}, "Select explicit supported edit policies")


def selection(config):
    return {"formatter": "parallel_units", "digest": "unrolled", "certified_source_reuse": True,
            "editor": config.editor_implementation, "container": config.container_implementation}


def provenance():
    from tools.benchmark_campaign_backends import provenance as base
    result = base()
    result["income_profile_sources"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        "tools/profile_campaign_resident_income.py", "tools/profile_campaign_recruitment_effects.py",
        "tools/benchmark_campaign_device_state.py", "tools/benchmark_campaign_resident_recruitment_chance.py",
        "tools/supervise_campaign_training.py")}
    return result


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
    require(device == "mps", "Income profile has no CPU fallback")
    torch.set_num_threads(config.threads); torch.set_num_interop_threads(1)
    torch.mps.set_per_process_memory_fraction(3_000_000_000 / torch.mps.recommended_max_memory())
    start = time.perf_counter(); pinned = provenance(); prepared = templates(config, deadline)
    report = {"schema": SCHEMA, "status": "running", "config": asdict(config), "provenance": pinned, "cases": [],
        "scope": __doc__, "selected_implementation": selection(config),
        "timing_scope": "Original income.refresh inside the complete handler; fenced extract/rates/writer/editor, not a complete-step timer",
        "rate_semantics": "Refresh incomeComponents/incomeKnown; treasury and collection clock are preserved, not income collection",
        "allocation_lifetimes": "Original return objects and writer output buffers retained until outside-timer verification; no added copies",
        "fixture_scope": "Same controlled-minor legal recruitment rolls as complete-step comparisons; not campaign-position frequency"}
    def guard(): require(time.monotonic() < deadline, "Shared income diagnostic deadline exhausted")
    def save():
        report["worker_elapsed_seconds"] = time.perf_counter() - start; atomic_json(output, report)
    save()
    for family in config.families:
        for B in config.batch_sizes:
            guard(); setup = time.perf_counter(); envs, evidence = lanes(prepared[family], B, config.seed, deadline)
            original_native = [env.serialize() for env in envs]
            context = DeviceStateContext(gwrl_cpp.device_state_context(envs[0]), "mps",
                editor_implementation=config.editor_implementation, container_implementation=config.container_implementation)
            native = gwrl_cpp.capture_device_states(context.native, envs)
            before = DeviceStateBatch.from_native(native, context=context)
            relations = ResidentPoliticalRelations(context, gwrl_cpp.campaign_relations_context(envs[0]))
            recruitment = ResidentRecruitment(relations, gwrl_cpp.campaign_recruitment_context(envs[0]))
            formatter = ParallelUnitStateJson(CanonicalJsonContext(native, context), digest_implementation="unrolled")
            income = ResidentIncomeContext(context, gwrl_cpp.campaign_income_context(envs[0]))
            handler = ResidentRecruitmentChance(context, ResidentRecruitmentEffects(recruitment), income, formatter,
                                              reuse_certified_source=True)
            maximum = prepared[family]["choices"]; C = before.records.shape[1]; N = len(relations.nation_ids)
            cap = C + 7 + 14 * maximum + 4 * N + 64; choices = B * maximum
            caps = RecruitmentChanceCapacities(cap, cap, choices, 512,
                before.string_offsets.numel()-1 + choices + 2*B,
                before.string_bytes.numel() + choices*recruitment.id_capacity + 94*B, 9, 262144, 1, 1)
            before = handler.reserve(before, caps); expected = formatter.identities(before, byte_capacity=caps.json_byte_capacity)
            source_hash, context_hash = resident_digest(before), static_digest(before)
            require(inspect_digests(expected.engine_keys) == tuple(env.planning_key() for env in envs), "Source native Engine keys differ")
            futures = [env.clone() for env in envs]
            for env in futures: env.resolve_chance()
            expected_native = canonical_native(gwrl_cpp.capture_device_states(context.native, futures))
            output_keys = tuple(env.planning_key() for env in futures)
            for _ in range(config.warmups):
                guard(); warmed = handler.resolve(before, expected, capacities=caps); torch.mps.synchronize()
                require(warmed.committed.item(), "Unprofiled warmup failed"); require_exact(warmed.state.to_native(), expected_native)
            ordinary = handler.resolve(before, expected, capacities=caps); torch.mps.synchronize()
            require(ordinary.committed.item(), "Original complete transition failed"); require_exact(ordinary.state.to_native(), expected_native)
            profiled = IncomeStageProfiler(income); handler.income = profiled
            with profiled.capture(timed=False) as observed_calls:
                observed = handler.resolve(before, expected, capacities=caps)
            torch.mps.synchronize(); require(len(observed_calls) == 1, "Handler changed income refresh count")
            observed_proof = compare_results(observed, ordinary); require_exact(observed.state.to_native(), expected_native)
            case = {"family": family, "lanes": B, "fixtures": evidence, "capacities": asdict(caps),
                "source_buffer_sha256": source_hash, "static_context_sha256": context_hash,
                "native_output_record_sha256": expected_native[3], "setup_seconds": time.perf_counter()-setup,
                "untimed_wrapper_all_outputs_exact": observed_proof, "profiles": []}
            for _ in range(config.repeats):
                guard()
                with profiled.capture() as calls: result = handler.resolve(before, expected, capacities=caps)
                torch.mps.synchronize(); checked = time.perf_counter()
                require(len(calls) == 1 and result.committed.item(), "Profiled complete transition failed")
                whole = compare_results(result, ordinary); intermediate = compare_calls(calls[0], observed_calls[0])
                require_exact(result.state.to_native(), expected_native)
                require(inspect_digests(result.identities.engine_keys) == output_keys, "Profiled native output Engine key differs")
                case["profiles"].append({**describe_call(calls[0]), "complete_output_proof": whole,
                    "intermediate_output_proof": intermediate, "full_native_state_history_rng_and_engine_keys_exact": True,
                    "verification_seconds": time.perf_counter()-checked})
                del result, calls
            case["source_unchanged"] = (resident_digest(before) == source_hash and static_digest(before) == context_hash and
                                        [env.serialize() for env in envs] == original_native)
            require(case["source_unchanged"], "Income profiler changed source State/history/RNG/static buffers")
            report["cases"].append(case); save()
            del ordinary, observed, observed_calls, warmed, handler, profiled, income, recruitment, relations
            del before, expected, native, context, futures, expected_native, formatter
            gc.collect(); torch.mps.empty_cache()
    report["sources_unchanged"] = pinned == provenance()
    report["status"] = "completed" if report["sources_unchanged"] else "changed_inputs"
    save(); return report


def finalize(report, config):
    expected = {(family, B) for family in config.families for B in config.batch_sizes}
    finite = lambda value: type(value) in (int, float) and math.isfinite(value) and value >= 0
    def proof(value):
        return isinstance(value, dict) and value.get("all_return_bytes_and_metadata_exact") is True and value.get("compared_tensors", 0) > 0
    def profile(row):
        spans = row.get("spans", [])
        return (row.get("full_native_state_history_rng_and_engine_keys_exact") is True and
                proof(row.get("complete_output_proof")) and proof(row.get("intermediate_output_proof")) and
                all(finite(row.get(name)) for name in ("total_income_refresh_seconds", "prepare_seconds", "between_call_setup_seconds", "final_publish_seconds")) and
                [span.get("label") for span in spans] == list(EXPECTED_LABELS) and
                all(span.get("parent") is None and finite(span.get("inclusive_seconds")) and finite(span.get("exclusive_seconds")) and
                    span["exclusive_seconds"] == span["inclusive_seconds"] for span in spans))
    cases = report.get("cases", [])
    exact = (report.get("schema") == SCHEMA and report.get("status") == "completed" and report.get("sources_unchanged") is True and
             report.get("selected_implementation") == selection(config) and
             len(cases) == len(expected) and {(case.get("family"), case.get("lanes")) for case in cases} == expected and
             all(case.get("source_unchanged") is True and proof(case.get("untimed_wrapper_all_outputs_exact")) and
                 len(case.get("profiles", [])) == config.repeats and all(profile(row) for row in case["profiles"]) for case in cases))
    report["income_profile_exact"] = bool(exact)
    if report.get("status") == "completed" and not exact: report["status"] = "incomplete_or_mismatch"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path); parser.add_argument("--batch-sizes", nargs="+", type=int, default=(1,64))
    parser.add_argument("--families", choices=FAMILIES, nargs="+", default=FAMILIES)
    parser.add_argument("--repeats", type=int, default=3); parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--editor-implementation", choices=("reference", "parallel"), default="reference")
    parser.add_argument("--container-implementation", choices=("reference", "parallel"), default="reference")
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS); parser.add_argument("--_device", help=argparse.SUPPRESS)
    parser.add_argument("--_deadline", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        settings = json.loads(args._worker.read_text())
        for key in ("devices", "batch_sizes", "families"): settings[key] = tuple(settings[key])
        worker(IncomeConfig(**settings), args._device, args.output, args._deadline); return 0
    config = IncomeConfig(batch_sizes=tuple(args.batch_sizes), families=tuple(args.families), repeats=args.repeats,
        seconds=args.seconds, editor_implementation=args.editor_implementation, container_implementation=args.container_implementation)
    require(not args.output.exists(), "Choose a fresh evidence path")
    result = supervise(config, "mps", args.output, deadline=time.monotonic()+config.seconds, worker_script=Path(__file__))
    result = finalize(result, config); atomic_json(args.output, result)
    return 0 if result["income_profile_exact"] else 2


if __name__ == "__main__": raise SystemExit(main())
