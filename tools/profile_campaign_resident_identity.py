#!/usr/bin/env python3
"""Fenced identity diagnostics inside complete supported recruitment chances.

Every ordinary transition and cached expected-key check remains unchanged. Only
this explicit diagnostic wrapper synchronizes between the four existing identity
operations. These intrusive stage measurements are not end-to-end throughput.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict,dataclass
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.benchmark_campaign_device_state import StateConfig,atomic_json,require,supervise
from tools.benchmark_campaign_resident_recruitment_chance import (
    FAMILIES,canonical_native,lanes,provenance as chance_provenance,require_exact,resident_digest,templates,
)

SCHEMA="campaign-resident-identity-substage-profile-v1"
STAGES=("state_serialize","state_sha256","outer_engine_json","engine_sha256")
ROLES=("source_preflight","after_effects")


@dataclass(frozen=True)
class IdentityConfig(StateConfig):
    devices:tuple[str,...]=("mps",)
    batch_sizes:tuple[int,...]=(1,)
    repeats:int=3
    families:tuple[str,...]=FAMILIES

    def __post_init__(self):
        super().__post_init__()
        require(self.devices==("mps",),"Identity diagnostics require explicit exact MPS")
        require(self.families and len(set(self.families))==len(self.families) and not set(self.families)-set(FAMILIES),
                "Choose distinct supported recruitment fixture families")


@dataclass(frozen=True)
class IdentityCall:
    source:object
    result:object
    seconds:dict


class IdentityStageProfiler:
    """Harness-only delegate; inactive calls use the original implementation.

    ``capture`` is explicit and cannot nest. The wrapper retains the two result
    references only until the caller releases the returned call list; it never
    clones or transfers a State and does not modify production cache behavior.
    """
    def __init__(self,delegate,*,synchronize=None,clock=None,digest=None):
        if synchronize is None:
            import torch
            synchronize=torch.mps.synchronize
        if digest is None:
            from studies.campaign.backends.canonical_json_metal import canonical_json_digests
            def digest(result):
                return canonical_json_digests(result,implementation=delegate.digest_implementation,
                                             group_size=delegate.digest_group_size)
        self.delegate=delegate;self.synchronize=synchronize;self.clock=clock or time.perf_counter
        self.digest=digest;self._calls=None

    def __getattr__(self,name):return getattr(self.delegate,name)

    @contextmanager
    def capture(self):
        if self._calls is not None:raise ValueError("Identity profiling captures cannot nest")
        calls=[];self._calls=calls
        try:yield calls
        finally:self._calls=None

    def identities(self,state,*,byte_capacity):
        if self._calls is None:return self.delegate.identities(state,byte_capacity=byte_capacity)
        from studies.campaign.backends.resident_state_json import StateIdentityBatch
        self.synchronize();last=self.clock();seconds={}
        def done(name):
            nonlocal last
            self.synchronize();now=self.clock();seconds[name]=now-last;last=now
        encoded=self.delegate.serialize(state,byte_capacity=byte_capacity);done(STAGES[0])
        keys=self.digest(encoded);done(STAGES[1])
        outer=self.delegate.outer_engine_json(keys);done(STAGES[2])
        engine=self.digest(outer);done(STAGES[3])
        result=StateIdentityBatch(state,encoded,keys,outer,engine)
        self._calls.append(IdentityCall(state,result,seconds));return result


def provenance():
    value=chance_provenance()
    value["identity_profile_sources"]={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
        "tools/profile_campaign_resident_identity.py","tools/benchmark_campaign_device_state.py",
        "tools/supervise_campaign_training.py")}
    return value


def _same_identity(actual,expected):
    """Explicit post-timing comparison of every output byte/metadata tensor."""
    import torch
    require(actual.source is expected.source,"Profiled identity lost exact source binding")
    for group in ("state_json","state_keys","engine_json","engine_keys"):
        left,right=getattr(actual,group),getattr(expected,group)
        for name in left.__dataclass_fields__:
            require(torch.equal(getattr(left,name),getattr(right,name)),f"Identity profiler changed {group}.{name}")


def _describe(call,role):
    value=call.result
    return {"role":role,"seconds":call.seconds,"sum_stage_seconds":sum(call.seconds.values()),
        "lanes":call.source.lane_count,"state_record_capacity":call.source.records.shape[1],
        "state_record_lengths":call.source.lengths.cpu().tolist(),
        "state_json_byte_capacity":value.state_json.data.shape[1],
        "state_json_bytes":value.state_json.lengths.cpu().tolist(),
        "state_json_required_bytes":value.state_json.required_bytes.cpu().tolist(),
        "outer_engine_byte_capacity":value.engine_json.data.shape[1],
        "outer_engine_bytes":value.engine_json.lengths.cpu().tolist(),
        "expected_key_construction_included":False}


def worker(config,device,output,deadline):
    import torch,gwrl_cpp
    from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
    from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
    from studies.campaign.backends.resident_recruitment import ResidentRecruitment
    from studies.campaign.backends.resident_recruitment_effects import ResidentRecruitmentEffects
    from studies.campaign.backends.resident_state_income import ResidentIncomeContext
    from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
    from studies.campaign.backends.resident_state_json import ResidentStateJson
    from studies.campaign.backends.content_digest_metal import inspect_digests
    from studies.campaign.backends.resident_recruitment_chance import ResidentRecruitmentChance,RecruitmentChanceCapacities
    require(device=="mps","No CPU fallback")
    torch.set_num_threads(config.threads);torch.set_num_interop_threads(1)
    torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    started=time.perf_counter();source_provenance=provenance();prepared=templates(config,deadline)
    report={"schema":SCHEMA,"status":"running","config":asdict(config),"provenance":source_provenance,"cases":[],
        "scope":"Intrusive fenced identity substages inside exact complete supported recruitment chances; not throughput or game/search speed",
        "source_preflight":"Recomputed full source identity versus the cached expected Engine key; expected-key construction remains setup-only",
        "after_effects":"Full current State after rules/income/reset/forward and before Event/RNG commit; output keys verified against actual native Engine",
        "excluded":"Fixture authoring, capture, fixed reservation, expected-key construction, warmup, native oracle, all inspection and verification"}
    atomic_json(output,report)
    for family in config.families:
        for B in config.batch_sizes:
            require(time.monotonic()<deadline,"Shared diagnostic deadline exhausted")
            setup=time.perf_counter();envs,evidence=lanes(prepared[family],B,config.seed,deadline)
            context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
            captured=gwrl_cpp.capture_device_states(context.native,envs);before=DeviceStateBatch.from_native(captured,context=context)
            relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
            recruitment=ResidentRecruitment(relations,gwrl_cpp.campaign_recruitment_context(envs[0]))
            formatter=ResidentStateJson(CanonicalJsonContext(captured,context));profiled=IdentityStageProfiler(formatter)
            handler=ResidentRecruitmentChance(context,ResidentRecruitmentEffects(recruitment),
                ResidentIncomeContext(context,gwrl_cpp.campaign_income_context(envs[0])),profiled)
            maximum=prepared[family]["choices"];C=before.records.shape[1];N=len(relations.nation_ids);cap=C+7+14*maximum+4*N+64
            choices=B*maximum
            caps=RecruitmentChanceCapacities(cap,cap,choices,512,before.string_offsets.numel()-1+choices+2*B,
                before.string_bytes.numel()+choices*recruitment.id_capacity+94*B,9,262144,1,1)
            before=handler.reserve(before,caps);expected=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
            source_keys=tuple(env.planning_key() for env in envs)
            require(inspect_digests(expected.engine_keys)==source_keys,"Cached expected source Engine keys differ from native")
            native_outputs=[]
            for env in envs:
                candidate=env.clone();candidate.resolve_chance();native_outputs.append(candidate)
            output_keys=tuple(env.planning_key() for env in native_outputs)
            native_output=canonical_native(gwrl_cpp.capture_device_states(context.native,native_outputs))
            source_digest=resident_digest(before)
            for _ in range(config.warmups):
                require(time.monotonic()<deadline,"Warmup exhausted shared deadline")
                result=handler.resolve(before,expected,capacities=caps);torch.mps.synchronize()
                require(result.committed.item(),"Unprofiled warmup failed")
                require_exact(result.state.to_native(),native_output)
            case={"family":family,"lanes":B,"fixtures":evidence,"capacities":asdict(caps),"profiles":[],
                  "setup_seconds":time.perf_counter()-setup,"source_buffer_sha256":source_digest}
            for _ in range(config.repeats):
                require(time.monotonic()<deadline,"Identity profiling exhausted shared deadline")
                result=None
                with profiled.capture() as calls:
                    result=handler.resolve(before,expected,capacities=caps)
                torch.mps.synchronize();checked=time.perf_counter()
                require(result.committed.item(),"Profiled complete transaction failed")
                require(len(calls)==2 and calls[0].source is before and calls[1].source is not before,
                        "Complete handler identity call order/source changed")
                require_exact(result.state.to_native(),native_output)
                require(inspect_digests(result.identities.engine_keys)==output_keys,"Final native Engine key mismatch")
                require(inspect_digests(calls[0].result.engine_keys)==source_keys,"Source profile changed cached-key validation")
                require(inspect_digests(calls[1].result.engine_keys)==output_keys,"After-effects Engine key differs")
                for call in calls:
                    ordinary=formatter.identities(call.source,byte_capacity=caps.json_byte_capacity)
                    torch.mps.synchronize();_same_identity(call.result,ordinary)
                case["profiles"].append({"calls":[_describe(call,role) for call,role in zip(calls,ROLES,strict=True)],
                    "full_state_history_rng_and_keys_exact":True,"all_identity_bytes_and_metadata_exact":True,
                    "verification_seconds":time.perf_counter()-checked})
            case["source_unchanged"]=resident_digest(before)==source_digest
            require(case["source_unchanged"],"Profile mutated original State/pool/history/RNG")
            case["output_record_sha256"]=native_output[3];report["cases"].append(case);atomic_json(output,report)
            del result,ordinary,call,calls,profiled,handler,formatter,recruitment,relations,before,captured,context,envs,expected,native_outputs,native_output,candidate
            gc.collect();torch.mps.empty_cache()
    report["sources_unchanged"]=source_provenance==provenance()
    report["status"]="completed" if report["sources_unchanged"] else "changed_inputs"
    report["worker_elapsed_seconds"]=time.perf_counter()-started;atomic_json(output,report);return report


def finalize(report,config):
    def valid_call(call,role,B):
        seconds=call.get("seconds",{})
        arrays=("state_record_lengths","state_json_bytes","state_json_required_bytes","outer_engine_bytes")
        return call.get("role")==role and call.get("lanes")==B and call.get("expected_key_construction_included") is False and \
            set(seconds)==set(STAGES) and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in seconds.values()) and \
            all(isinstance(call.get(name),list) and len(call[name])==B and all(type(v) is int and v>0 for v in call[name]) for name in arrays) and \
            call["state_json_bytes"]==call["state_json_required_bytes"]
    expected={(family,B) for family in config.families for B in config.batch_sizes};cases=report.get("cases",[])
    valid=report.get("schema")==SCHEMA and report.get("status")=="completed" and report.get("sources_unchanged") is True
    valid=valid and len(cases)==len(expected) and {(row.get("family"),row.get("lanes")) for row in cases}==expected
    valid=valid and all(row.get("source_unchanged") is True and len(row.get("profiles",[]))==config.repeats and all(
        profile.get("full_state_history_rng_and_keys_exact") is True and profile.get("all_identity_bytes_and_metadata_exact") is True and
        len(profile.get("calls",[]))==2 and all(valid_call(call,role,row["lanes"]) for call,role in zip(profile["calls"],ROLES,strict=True))
        for profile in row["profiles"]) for row in cases)
    report["identity_profile_exact"]=bool(valid)
    if report.get("status")=="completed" and not valid:report["status"]="incomplete_or_mismatch"
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--batch-sizes",type=int,nargs="+",default=(1,))
    parser.add_argument("--families",nargs="+",choices=FAMILIES,default=FAMILIES)
    parser.add_argument("--repeats",type=int,default=3);parser.add_argument("--seconds",type=float,default=120)
    parser.add_argument("--_worker",type=Path,help=argparse.SUPPRESS);parser.add_argument("--_device",help=argparse.SUPPRESS)
    parser.add_argument("--_deadline",type=float,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args._worker:
        settings=json.loads(args._worker.read_text())
        for key in ("devices","batch_sizes","families"):settings[key]=tuple(settings[key])
        worker(IdentityConfig(**settings),args._device,args.output,args._deadline);return 0
    config=IdentityConfig(batch_sizes=tuple(args.batch_sizes),families=tuple(args.families),repeats=args.repeats,seconds=args.seconds)
    require(not args.output.exists(),"Choose a fresh evidence path")
    result=supervise(config,"mps",args.output,deadline=time.monotonic()+config.seconds,worker_script=Path(__file__))
    result=finalize(result,config);atomic_json(args.output,result)
    return 0 if result.get("identity_profile_exact") else 2


if __name__=="__main__":raise SystemExit(main())
