#!/usr/bin/env python3
"""Guarded matched native/Metal supplied-path validation component benchmark.

The unchanged sampled balanced script must finish a genuine three-round game.
Four complete Japan snapshots supply all current movement-controlled land units,
all simple one/two-hop geometric paths, and every full movement-route menu path.
Every candidate is retained. Native validateRoute computes complete owned native
results under a native timer: Python boxing, unique mutex locking and inspection
are excluded. GPU measurements separately cover fresh relation/index preparation
plus queries, and queries reusing source-bound preparation. This is neither a
complete legal-menu generator nor full gameplay, search or training throughput.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.benchmark_campaign_device_state import (
    StateConfig, atomic_json, digest, require, supervise,
)

SCHEMA = "campaign-resident-route-query-benchmark-v1"
POSITIONS = tuple(f"japan_round{round_number}_{phase}" for round_number in (1, 2)
                  for phase in ("combat_movement", "non_combat_movement"))
MODES = ("ordinary", "blitz", "strategic_rail", "strategic_river", "narrow_crossing")


@dataclass(frozen=True)
class RouteConfig(StateConfig):
    devices: tuple[str, ...] = ("mps",)
    batch_sizes: tuple[int, ...] = (1, 4, 16, 64)
    preparation_implementation: str = "reference"
    synthetic_history_strings_per_lane: int = 0

    def __post_init__(self):
        super().__post_init__()
        require(self.devices == ("mps",), "Routes require explicit Apple MPS; no CPU fallback")
        require(self.preparation_implementation in {"reference", "fused", "fused_indexed"}, "Choose reference, fused or fused_indexed route preparation")
        require(type(self.synthetic_history_strings_per_lane) is int and self.synthetic_history_strings_per_lane>=0,
                "Synthetic history size must be an explicit nonnegative integer; it is never silently capped")


def provenance():
    from tools.benchmark_campaign_device_state import provenance as base
    value = base()
    value["route_harness_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    value["route_native_probe_sha256"] = hashlib.sha256((ROOT / "src/python_movement_context.inc").read_bytes()).hexdigest()
    value["route_native_boundary_sha256"] = hashlib.sha256((ROOT / "src/python_bindings.cpp").read_bytes()).hexdigest()
    return value


def fixture_label(clock, kind):
    if (clock["nation_index"] == 2 and clock["round_index"] in (0, 1) and
            kind in {"combat_movement", "non_combat_movement"}):
        return f"japan_round{clock['round_index'] + 1}_{kind}"
    return None


def prepare_workload(config, deadline):
    """Use the same sampled_step policy/chance implementation as the CPU scaffold."""
    from studies.campaign.curriculum import make_env, task_manifest
    from tools.benchmark_campaign_backends import Config as ReplayConfig, sampled_step, check_terminal
    reference = ReplayConfig(seeds=(config.seed,))
    env = make_env(config.seed, calendar_rounds=3)
    task, initial = task_manifest(env), env.serialize()
    steps, fixtures, found = [], [], set()
    visits = Counter({env.planning_key(): 1})
    while not env.is_terminal():
        require(time.monotonic() < deadline, "Route preparation exhausted the shared wall deadline")
        require(len(steps) < reference.max_transitions and visits[env.planning_key()] <= reference.max_state_visits,
                "Scripted preparation hit its unchanged safety limit; unfinished games are not terminal")
        clock, kind = env.observation()["state"]["clock"], env.decision_kind()
        label = fixture_label(clock, kind)
        if label is not None and label not in found:
            serialized = env.serialize()
            fixtures.append({"label": label, "seed": config.seed, "step": len(steps), "serialized": serialized,
                             "serialized_sha256": hashlib.sha256(serialized.encode()).hexdigest()})
            found.add(label)
        steps.append(sampled_step(env))
        visits[env.planning_key()] += 1
    check_terminal(env)
    require(found == set(POSITIONS), "Completed sampled game did not supply all four real route phases")
    return {"task": task, "seed": config.seed, "initial": initial, "steps": steps, "fixtures": fixtures,
            "terminal_checkpoint_sha256": hashlib.sha256(env.serialize().encode()).hexdigest(),
            "terminal_returns": list(env.returns()), "completed_three_round_games": 1,
            "selection": "campaign-active-baseline-v2:balanced; unchanged sampled_step; no neural model",
            "max_transitions": reference.max_transitions, "max_state_visits": reference.max_state_visits}


def candidate_requests(state, zones, node_rows, edge_rows, controlled_nations, menu_routes=()):
    """Author a complete stated component workload; never cap entities or paths.

    This deliberately includes invalid paths/modes, so it is not an enumeration
    of only legal choices. All hops within each ordered path are preserved.
    """
    land = {name for name, row in zip(zones, node_rows, strict=True) if row[0]}
    adjacency = {zone: set() for zone in land}
    for a, origin in enumerate(zones):
        if origin in land:
            for b, target in enumerate(zones):
                if target in land and edge_rows[a][b][0]:
                    adjacency[origin].add(target)
    for rail in state["rails"].values():
        a, b = rail["endpoint_a"], rail["endpoint_b"]
        if a in land and b in land:
            adjacency[a].add(b); adjacency[b].add(a)
    attack = state["clock"]["phase"] == "combat_movement"
    requests, seen, paths_by_unit = [], set(), {}

    def add(unit, path, mode="ordinary", combat=attack, towed=None):
        require(mode in MODES, "Unknown supplied route mode; it cannot be silently skipped")
        row = {"unit": unit, "path": list(path), "mode": mode, "combat": combat}
        if towed is not None:
            row["towed"] = towed
        key = (unit, tuple(path), mode, combat, towed)
        if key not in seen:
            seen.add(key); requests.append(row)

    moving = [(key, unit) for key, unit in sorted(state["units"].items())
              if unit["owner"] in controlled_nations and unit["zone"] in land]
    for identity, unit in moving:
        origin = unit["zone"]
        paths = [(origin, target) for target in sorted(adjacency[origin])]
        paths += [(origin, intermediate, target) for intermediate in sorted(adjacency[origin])
                  for target in sorted(adjacency[intermediate]) if target != origin]
        paths_by_unit[identity] = paths
        for path in paths:
            for mode in MODES:
                add(identity, path, mode)
            add(identity, path, combat=not attack)  # explicit wrong-phase query
    for identity, unit in moving:
        if unit["type"] == "motorized_infantry":
            for gun_id, gun in sorted(state["units"].items()):
                if (gun["owner"] == unit["owner"] and gun["zone"] == unit["zone"] and
                        gun["type"] in {"artillery", "advanced_artillery", "anti_aircraft_artillery"}):
                    for path in paths_by_unit[identity]:
                        add(identity, path, towed=gun_id)
    for parameters in menu_routes:
        add(parameters["unit"], parameters["path"], parameters.get("mode", "ordinary"),
            parameters.get("combat", False), parameters.get("towed"))
    require(requests, "A real route position supplied no candidate routes")
    return requests


def normalized(value):
    if isinstance(value, dict):
        return {key: normalized(child) for key, child in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, (list, tuple)):
        return [normalized(child) for child in value]
    return value


def exact_results(oracle, fresh, reused, requests):
    require(len(oracle) == len(fresh) == len(reused) == len(requests), "A route query or result was dropped")
    for index, (expected, a, b) in enumerate(zip(oracle, fresh, reused, strict=True)):
        for label, actual in (("fresh", a), ("reused", b)):
            require(actual.get("supported") is True, f"Unsupported {label} route query {index}")
            require({k: v for k, v in actual.items() if k != "supported"} == expected,
                    f"Native/{label} route mismatch at query {index}: {requests[index]}")
    outcomes = Counter("allowed" if row["allowed"] else (row["reason"] or f"exception:{row['exception']}") for row in oracle)
    modes = {}
    for request, result in zip(requests, oracle, strict=True):
        row = modes.setdefault(request["mode"], {"queries": 0, "allowed": 0, "exceptions": 0})
        row["queries"] += 1; row["allowed"] += int(result["allowed"]); row["exceptions"] += int(result["exception"] != 0)
    return {"exact": True, "verified_queries": len(oracle), "complete_native_results_sha256": digest(normalized(oracle)),
            "outcomes": dict(outcomes), "modes": modes, "allowed_queries": sum(row["allowed"] for row in oracle),
            "disallowed_queries": sum(not row["allowed"] for row in oracle),
            "fields": "Every RouteResult field, full approach/terrain/region sets and native exception class/message"}


def _pool_strings(data, offsets):
    raw=bytes(data);bounds=list(offsets)
    return {raw[a:b].decode("utf8") for a,b in zip(bounds,bounds[1:])}


def synthetic_history_lane(raw,lane,count,namespace,*,forbidden_strings=()):
    """Explicit setup only: clone a full state and append a marked audit annotation.

    The annotation is schema-valid synthetic data, not a claim that a new game
    action occurred. Original events, every board field and all RNG are retained.
    """
    require(type(lane) is int and lane>=0 and type(count) is int and count>=0 and
            isinstance(namespace,str) and namespace,"Invalid synthetic history parameters")
    original=raw.serialize();before=json.loads(original)
    values=[f"__gwrl_synthetic_route_history__/{namespace}/lane-{lane:08d}/entry-{i:08d}" for i in range(count)]
    require(not any(value in forbidden_strings for value in values),"Synthetic audit IDs overlap the original string pool")
    document=json.loads(original)
    if count:
        document["state"]["history"].append({"kind":"synthetic_route_history_stress",
            "after_state_key":raw.planning_key(),"payload":{"synthetic_benchmark_annotation":True,
                "namespace":namespace,"lane":lane,"unique_strings":values}})
    clone=raw.clone();clone.restore(json.dumps(document,allow_nan=False))
    actual=json.loads(clone.serialize())
    board=lambda value:{**value,"state":{key:child for key,child in value["state"].items() if key!="history"}}
    require(board(actual)==board(before),"History annotation changed a board/schema/rule/RNG field")
    require(actual["state"]["history"][:len(before["state"]["history"])]==before["state"]["history"],"Original audit history was not retained")
    require(raw.serialize()==original,"Synthetic authoring mutated the original source")
    return clone,{"state_without_history_sha256":digest({k:v for k,v in before["state"].items() if k!="history"}),
                  "random_sha256":digest(before["random"]),"original_history_events":len(before["state"]["history"]),
                  "added_history_events":int(count>0),"requested_unique_strings":count,
                  "original_history_prefix_preserved":True,"boards_and_random_unchanged":True}


def exact_mixed_resident(actual,reference,*,inspection_chunk_bytes=32_000_000):
    """Every mixed lane equals an independent WHOLE-batch native CPU capture.

    Whole-batch capture is essential: independently capturing a subset would
    assign a different shared suffix namespace and is not a bit-level oracle.
    """
    import numpy as np
    require(actual.context.identity==reference.context.identity and actual.lane_count==reference.lane_count,
            "Mixed native/device source context or lane count differs")
    require(type(inspection_chunk_bytes) is int and inspection_chunk_bytes>0,"Inspection chunk budget must be positive")
    hashes={}
    for field in ("records","lengths","sections","errors"):
        left,right=getattr(actual,field),getattr(reference,field)
        require(left.dtype==right.dtype and left.shape==right.shape,"Mixed source field layout differs: "+field)
        h=hashlib.sha256();row_bytes=max(1,math.prod(left.shape[1:])*left.element_size())
        chunk=max(1,inspection_chunk_bytes//row_bytes)
        for start in range(0,actual.lane_count,chunk):
            value=left[start:start+chunk].detach().cpu().numpy()
            np.testing.assert_array_equal(value,right[start:start+chunk].detach().cpu().numpy());h.update(value.tobytes())
        hashes[field]=h.hexdigest()
    for label,owner,expected,fields in (("dynamic",actual,reference,("string_bytes","string_offsets","suffix_usage")),
        ("static",actual.context,reference.context,("records","string_bytes","string_offsets"))):
        for field in fields:
            value=getattr(owner,field).detach().cpu().numpy();other=getattr(expected,field).detach().cpu().numpy()
            np.testing.assert_array_equal(value,other);hashes[label+"_"+field]=hashlib.sha256(value.tobytes()).hexdigest()
    require(not np.any(actual.errors.detach().cpu().numpy()),"Mixed source contains an invalid lane")
    return {"exact":True,"verified_lanes":actual.lane_count,"buffer_sha256":hashes,
            "inspection_chunk_budget_bytes":inspection_chunk_bytes,
            "verification":"Every record/padding/section/error/shared string/usage/static-definition bit equals an independent full mixed native batch"}


def mixed_native_witnesses(actual,serialized):
    import torch
    require(actual.lane_count==len(serialized) and serialized,"Every mixed lane needs its complete native source")
    lanes=tuple(sorted({0,len(serialized)//2,len(serialized)-1}))
    restored=actual.fork(torch.tensor(lanes,dtype=torch.int64,device=actual.device)).restore_envs()
    require(all(raw.serialize()==serialized[lane] for raw,lane in zip(restored,lanes,strict=True)),
            "Mixed native restore changed a state, original/synthetic history or any RNG stream")
    return {"lanes":lanes,"full_native_state_and_all_rng_exact":True,
            "native_checkpoint_sha256_by_witness":[hashlib.sha256(serialized[lane].encode()).hexdigest() for lane in lanes]}


def worker(config, device, progress, deadline):
    import gc
    import gwrl_cpp
    import torch
    from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
    from studies.campaign.backends.resident_routes import ResidentRoutes, TensorRouteRequests
    from studies.campaign.curriculum import make_env
    from studies.campaign.device_runtime import runtime_policy_for_device
    from tools.benchmark_campaign_device_state import exact_resident, native_witnesses
    require(device == "mps" and torch.backends.mps.is_available(), "Exact Apple MPS is required")
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
              "native_baseline": "Sequential original validateRoute on one native thread, prebuilt requests, strong owners/unique locks/pointers/output-vector allocation before native timer; complete owned result construction inside timer; Python boxing outside",
              "gpu_paths": ["New immutable view over unchanged resident buffers: shared politics/declarations/index preparation + path query",
                            "Supplied source-bound preparation: path query allocation/dispatch/synchronization only"],
              "candidate_scope": "All movement-controlled units on retained land; every simple one/two-hop directed geometry or constructed-rail path x five modes + ordinary wrong-phase queries, all co-located tow pairs, and every complete legal-menu movement_route path; no arbitrary candidate cap",
              "limitations": ["Replicated states exercise batched query parallelism, not varied simultaneous games.",
                              "Native timing is a sequential component baseline, not a twelve-core parallel route service.",
                              "Geometric paths include illegal candidates; report allowed/rejection distributions before interpreting speed.",
                              "Path validation does not enumerate all game actions or commit movements, and does not measure search or learning."]}

    def persist():
        report["elapsed_worker_seconds"] = time.perf_counter() - started
        report["device_memory"] = {"live_bytes": torch.mps.current_allocated_memory(), "driver_bytes": torch.mps.driver_allocated_memory()}
        report["device_runtime"] = policy.stats(); atomic_json(progress, report)

    def timed(operation, gpu=False):
        require(time.monotonic() < deadline, "Shared route benchmark wall deadline exhausted")
        torch.mps.synchronize(); before = time.perf_counter(); value = operation()
        if gpu:
            torch.mps.synchronize()
        return value, time.perf_counter() - before

    if config.synthetic_history_strings_per_lane:
        report["limitations"][0]="Identical real boards with schema-valid synthetic lane-specific audit annotations; this is history-namespace stress, not distinct played games."
        report["synthetic_history_scope"]="Append-only annotations; all original history, full board/rule/schema fields, queries and random streams are retained."
    persist(); before = time.perf_counter(); workload = prepare_workload(config, deadline)
    report.update(status="running", task=workload["task"], workload_sha256=digest(workload),
                  preparation_seconds=time.perf_counter() - before,
                  preparation_completed_three_round_games=workload["completed_three_round_games"],
                  terminal_checkpoint_sha256=workload["terminal_checkpoint_sha256"],
                  scripted_transitions=len(workload["steps"]), preparation_selection=workload["selection"],
                  preparation_safety_limits={k: workload[k] for k in ("max_transitions", "max_state_visits")})
    persist()
    for fixture in workload["fixtures"]:
        env = make_env(fixture["seed"], calendar_rounds=3); env.restore(fixture["serialized"])
        raw = env.raw; original = raw.serialize(); snapshot = json.loads(original)["state"]
        native_context, context_seconds = timed(lambda: gwrl_cpp.device_state_context(raw))
        context, static_upload_seconds = timed(lambda: DeviceStateContext(native_context, "mps"), gpu=True)
        capture, capture_seconds = timed(lambda: gwrl_cpp.capture_device_states(native_context, [raw]))
        source, upload_seconds = timed(lambda: DeviceStateBatch.from_native(capture, context=context), gpu=True)
        native_routes, movement_context_seconds = timed(lambda: gwrl_cpp.campaign_movement_context(raw))
        kernel, movement_upload_seconds = timed(lambda: ResidentRoutes(context, native_routes, preparation_implementation=config.preparation_implementation), gpu=True)
        before = time.perf_counter()
        permission_oracle = gwrl_cpp.campaign_relations_oracle(native_routes.relations_context, [raw])
        permissions, permission_errors = permission_oracle.nation_array()[0, :, 2], permission_oracle.nation_error_array()[0, :, 2]
        nation_indexes = {name: index for index, name in enumerate(native_routes.nations)}
        require(all(permission_errors[nation_indexes[unit["owner"]]] == 0 for unit in snapshot["units"].values()),
                "Movement-controller failure cannot silently drop a source unit")
        controlled = {name for name, value in zip(native_routes.nations, permissions, strict=True) if value}
        menu = [action.raw["parameters"] for action in env.legal_actions()
                if action.raw is not None and action.raw["kind"] == "movement_route"]
        rows = candidate_requests(snapshot, native_routes.zones, native_routes.node_array(),
                                  native_routes.edge_array(), controlled, menu)
        host_request_seconds = time.perf_counter() - before
        reference = DeviceStateBatch.capture([raw.clone()], device="cpu")
        active_string_ids=source.context.string_count+int(source.suffix_usage.cpu().tolist()[0])
        original_pool_strings=None
        if config.synthetic_history_strings_per_lane:
            original_pool_strings=_pool_strings(native_context.string_bytes(),native_context.string_offsets())|_pool_strings(capture.string_bytes(),capture.string_offsets())
        one, host_pack_upload_seconds = timed(lambda: kernel.pack_requests(source, rows), gpu=True)
        require(one.metadata.shape[0] == len(rows), "Host request packing truncated choices")
        for size in config.batch_sizes:
            lanes = torch.zeros(size, dtype=torch.int64, device="mps")
            mixed_reference=None;source_serialized=None;history_proof=None;history_setup={}
            case_active_sids=active_string_ids;case_checkpoint=original
            if config.synthetic_history_strings_per_lane:
                before=time.perf_counter()
                authored=[synthetic_history_lane(raw,lane,config.synthetic_history_strings_per_lane,fixture["label"],
                    forbidden_strings=original_pool_strings) for lane in range(size)]
                envs=[row[0] for row in authored];proofs=[row[1] for row in authored]
                history_setup["annotation_authoring_seconds"]=time.perf_counter()-before
                source_serialized=[item.serialize() for item in envs];case_checkpoint=source_serialized[0]
                mixed_capture,elapsed=timed(lambda:gwrl_cpp.capture_device_states(native_context,envs))
                history_setup["native_mixed_capture_seconds"]=elapsed
                resident,elapsed=timed(lambda:DeviceStateBatch.from_native(mixed_capture,context=context),gpu=True)
                history_setup["mixed_dynamic_upload_seconds"]=elapsed
                populate_seconds=sum(history_setup[k] for k in ("native_mixed_capture_seconds","mixed_dynamic_upload_seconds"))
                before=time.perf_counter()
                mixed_reference=DeviceStateBatch.capture(envs,device="cpu",context=DeviceStateContext(native_context,"cpu"))
                history_setup["independent_cpu_mixed_capture_seconds"]=time.perf_counter()-before
                case_active_sids=resident.context.string_count+int(resident.suffix_usage.cpu().tolist()[0])
                require(case_active_sids-active_string_ids>=size*config.synthetic_history_strings_per_lane,
                        "Synthetic shared string namespace did not grow by every requested lane-unique ID")
                require(len({row["state_without_history_sha256"] for row in proofs})==1 and len({row["random_sha256"] for row in proofs})==1,
                        "Synthetic lanes no longer have identical boards and random states")
                history_proof={"enabled":True,"schema_valid_synthetic_annotations":True,
                    "strings_per_lane":config.synthetic_history_strings_per_lane,"added_events_per_lane":1,
                    "distinct_synthetic_strings":size*config.synthetic_history_strings_per_lane,
                    "original_history_prefix_preserved":all(row["original_history_prefix_preserved"] for row in proofs),
                    "boards_and_random_unchanged":all(row["boards_and_random_unchanged"] for row in proofs),
                    "state_without_history_sha256":proofs[0]["state_without_history_sha256"],"random_sha256":proofs[0]["random_sha256"],
                    "base_native_checkpoint_sha256":hashlib.sha256(original.encode()).hexdigest(),
                    "native_lane_checkpoint_sha256":[hashlib.sha256(value.encode()).hexdigest() for value in source_serialized],
                    "active_global_sid_growth":case_active_sids-active_string_ids}
            else:
                resident, populate_seconds = timed(lambda: source.fork(lanes), gpu=True)
                envs=[raw]*size
            expanded = [{**row, "lane": lane} for lane in range(size) for row in rows]
            native_queries, native_request_seconds = timed(lambda: [gwrl_cpp.CampaignMovementQuery(
                row["lane"], row["unit"], row["path"], row["mode"], row["combat"], row.get("towed")) for row in expanded])
            def upload_requests():
                if config.synthetic_history_strings_per_lane:return kernel.pack_requests(resident,expanded)
                metadata = one.metadata.repeat(size, 1)
                metadata[:, 0] = torch.arange(size, device="mps", dtype=torch.int64).repeat_interleave(len(rows))
                return TensorRouteRequests(metadata, one.paths.repeat(size, 1))
            requests, request_replication_seconds = timed(upload_requests, gpu=True)
            def fresh_query():
                # A new immutable source identity forces correct per-state
                # preparation, without charging either side for a state copy.
                fresh = replace(resident)
                return kernel.query(fresh, requests)
            before = time.perf_counter(); policy.reset(); torch.mps.synchronize(); reset_seconds = time.perf_counter() - before
            oracle, cold_native_wall = timed(lambda: gwrl_cpp.benchmark_campaign_route_oracle(native_routes, envs, native_queries))
            fresh, cold_fresh = timed(fresh_query, gpu=True)
            prepared, prepare_seconds = timed(lambda: kernel.prepare(resident), gpu=True)
            reused, cold_reused = timed(lambda: kernel.query(resident, requests, prepared=prepared), gpu=True)
            case = {"position": fixture["label"], "seed": fixture["seed"], "lanes": size,
                    "clock": snapshot["clock"], "queries_per_lane": len(rows), "queries": len(expanded),
                    "preparation_work_per_lane": {"unit_entries": len(snapshot["units"]), "territory_entries": len(snapshot["territories"]),
                        "active_sid_slots": case_active_sids, "allocated_sid_slots": kernel._dims(resident)[9],
                        "unused_sid_capacity": kernel._dims(resident)[9]-case_active_sids,
                        "nonunit_active_sids": case_active_sids-len(snapshot["units"])},
                    "request_sha256": digest(expanded), "one_lane_requests_sha256": digest(rows),
                    "native_checkpoint_sha256": hashlib.sha256(case_checkpoint.encode()).hexdigest(),
                    "native_context_seconds": context_seconds, "native_capture_seconds": capture_seconds,
                    "static_upload_seconds": static_upload_seconds, "dynamic_upload_seconds": upload_seconds,
                    "movement_context_seconds": movement_context_seconds, "movement_metadata_upload_seconds": movement_upload_seconds,
                    "host_candidate_preparation_seconds": host_request_seconds, "one_lane_pack_and_upload_seconds": host_pack_upload_seconds,
                    "native_request_construction_seconds": native_request_seconds, "device_request_replication_seconds": request_replication_seconds,
                    "resident_population_seconds": populate_seconds, "cold_reset_seconds": reset_seconds,
                    "cold_native_query_seconds": oracle.seconds, "cold_native_wrapper_wall_seconds": cold_native_wall,
                    "cold_gpu_prepare_query_seconds": cold_fresh, "cold_gpu_prepared_query_seconds": cold_reused,
                    "independent_gpu_preparation_seconds": prepare_seconds,
                    "cold_scope": "Public allocator/graph reset; first shader compilation included when not already compiled; process/OS caches may remain",
                    "native_query_seconds": [], "native_wrapper_wall_seconds": [],
                    "gpu_prepare_query_seconds": [], "gpu_prepared_query_seconds": []}
            if history_proof is not None:
                case["synthetic_history"]=history_proof;case["history_setup"]=history_setup
                case["device_request_mode"]="Full request packing against the mixed shared suffix pool; outside query timing"
                case["native_checkpoint_scope"]="Lane zero; every lane hash is retained in synthetic_history"
            for _ in range(config.warmups):
                _, _ = timed(lambda: gwrl_cpp.benchmark_campaign_route_oracle(native_routes, envs, native_queries))
                _, _ = timed(fresh_query, gpu=True)
                _, _ = timed(lambda: kernel.query(resident, requests, prepared=prepared), gpu=True)
            for _ in range(config.repeats):
                oracle, elapsed = timed(lambda: gwrl_cpp.benchmark_campaign_route_oracle(native_routes, envs, native_queries))
                case["native_query_seconds"].append(oracle.seconds); case["native_wrapper_wall_seconds"].append(elapsed)
                fresh, elapsed = timed(fresh_query, gpu=True); case["gpu_prepare_query_seconds"].append(elapsed)
                reused, elapsed = timed(lambda: kernel.query(resident, requests, prepared=prepared), gpu=True)
                case["gpu_prepared_query_seconds"].append(elapsed); policy.completed(1)
            before = time.perf_counter()
            require(oracle.calls == len(expanded) and oracle.query_count == len(expanded), "Native probe omitted a query")
            case["evidence"] = exact_results(oracle.inspect(), kernel.inspect(fresh), kernel.inspect(reused), expanded)
            if mixed_reference is not None:
                case["resident_source_evidence"]=exact_mixed_resident(resident,mixed_reference)
                case["native_source_witnesses"]=mixed_native_witnesses(resident,source_serialized)
                require(all(item.serialize()==value for item,value in zip(envs,source_serialized,strict=True)),
                        "Queries mutated a complete mixed source/history/RNG")
            else:
                case["resident_source_evidence"] = exact_resident(resident, reference)
                require(torch.equal(resident.suffix_usage.cpu(), reference.suffix_usage), "Queries changed actual string-pool usage")
                case["native_source_witnesses"] = native_witnesses(resident, original)
            require(raw.serialize() == original, "Queries mutated complete source State/history/RNG")
            case["source_unchanged"] = True; case["host_inspection_seconds"] = time.perf_counter() - before
            report["cases"].append(case); persist()
            del resident, expanded, native_queries, requests, envs, oracle, prepared, fresh, reused, lanes
            if mixed_reference is not None:del mixed_reference,mixed_capture,authored,proofs
            gc.collect()
        del raw, env, reference, source, capture, context, native_context, native_routes, kernel, one
        gc.collect()
    report["sources_unchanged"] = report["provenance"] == provenance()
    report["status"] = "completed" if report["sources_unchanged"] else "changed_inputs"; persist(); return report


def finalize(result, config):
    expected = {(position, size) for position in POSITIONS for size in config.batch_sizes}
    cases = result.get("cases", [])
    def sha(value):
        return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)
    def history_valid(case):
        if not config.synthetic_history_strings_per_lane:return True
        row=case.get("synthetic_history",{});lanes=case.get("lanes",0);hashes=row.get("native_lane_checkpoint_sha256",[])
        return (row.get("enabled") is True and row.get("schema_valid_synthetic_annotations") is True and
                row.get("strings_per_lane")==config.synthetic_history_strings_per_lane and row.get("added_events_per_lane")==1 and
                row.get("distinct_synthetic_strings")==lanes*config.synthetic_history_strings_per_lane and
                row.get("active_global_sid_growth",0)>=lanes*config.synthetic_history_strings_per_lane and
                row.get("original_history_prefix_preserved") is True and row.get("boards_and_random_unchanged") is True and
                sha(row.get("state_without_history_sha256")) and sha(row.get("random_sha256")) and sha(row.get("base_native_checkpoint_sha256")) and
                len(hashes)==lanes and len(set(hashes))==lanes and all(sha(value) for value in hashes) and
                bool(hashes) and hashes[0]==case.get("native_checkpoint_sha256"))
    def valid(case):
        q = case.get("queries", 0)
        return (history_valid(case) and type(q) is int and q > 0 and type(case.get("queries_per_lane")) is int and case["queries_per_lane"] > 0 and
                q == case["queries_per_lane"] * case.get("lanes", 0) and case.get("seed") == config.seed and
                all(sha(case.get(field)) for field in ("request_sha256", "one_lane_requests_sha256", "native_checkpoint_sha256")) and
                case.get("evidence", {}).get("exact") is True and case["evidence"].get("verified_queries") == q and
                case.get("resident_source_evidence", {}).get("exact") is True and
                case["resident_source_evidence"].get("verified_lanes") == case.get("lanes") and
                case.get("native_source_witnesses", {}).get("full_native_state_and_all_rng_exact") is True and
                case.get("source_unchanged") is True and all(
                    len(case.get(field, [])) == config.repeats and all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in case[field])
                    for field in ("native_query_seconds", "native_wrapper_wall_seconds", "gpu_prepare_query_seconds", "gpu_prepared_query_seconds")))
    exact = (result.get("status") == "completed" and result.get("sources_unchanged") is True and
             result.get("preparation_completed_three_round_games") == 1 and sha(result.get("workload_sha256")) and
             sha(result.get("terminal_checkpoint_sha256")) and
             len(cases) == len(expected) and {(row.get("position"), row.get("lanes")) for row in cases} == expected and
             all(valid(case) for case in cases) and all(
                 len({(row["queries_per_lane"], row["one_lane_requests_sha256"], row["native_checkpoint_sha256"])
                      for row in cases if row["position"] == position}) == 1 for position in POSITIONS))
    result["matched_complete_route_queries_and_sources"] = bool(exact)
    if result.get("status") == "completed" and not exact:
        result["status"] = "incomplete_or_mismatch"
    coverage = {}
    for position in POSITIONS:
        row = next((r for r in cases if r.get("position") == position and type(r.get("lanes")) is int and r["lanes"] > 0), {})
        evidence, lanes = row.get("evidence", {}), row.get("lanes", 1)
        coverage[position] = {"allowed_queries_per_lane": evidence.get("allowed_queries", 0) // lanes,
                              "disallowed_queries_per_lane": evidence.get("disallowed_queries", 0) // lanes}
    result["coverage"] = coverage
    return result


def run(config, output):
    output = Path(output).resolve(); require(not output.exists(), "Choose a fresh output; prior evidence is never overwritten")
    result = supervise(config, "mps", output, deadline=time.monotonic() + config.seconds, worker_script=Path(__file__))
    result = finalize(result, config); atomic_json(output, result); return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-sizes", nargs="+", type=int, default=(1, 4, 16, 64))
    parser.add_argument("--repeats", type=int, default=5); parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--memory-bytes", type=int, default=8_000_000_000)
    parser.add_argument("--preparation-implementation", choices=("reference", "fused", "fused_indexed"), default="reference")
    parser.add_argument("--synthetic-history-strings-per-lane", type=int, default=0)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_device", choices=("mps",), help=argparse.SUPPRESS)
    parser.add_argument("--_deadline", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        settings = json.loads(args._worker.read_text()); settings["devices"] = tuple(settings["devices"])
        settings["batch_sizes"] = tuple(settings["batch_sizes"])
        worker(RouteConfig(**settings), args._device, args.output, args._deadline); return 0
    config = RouteConfig(batch_sizes=tuple(args.batch_sizes), repeats=args.repeats, seconds=args.seconds, memory_bytes=args.memory_bytes,
                         preparation_implementation=args.preparation_implementation,
                         synthetic_history_strings_per_lane=args.synthetic_history_strings_per_lane)
    return 0 if run(config, args.output)["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
