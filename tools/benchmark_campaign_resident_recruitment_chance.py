#!/usr/bin/env python3
"""Matched complete recruitment chance timing, never full-game/RL throughput.

Valid restored controlled-minor positions issue the original legal roll Action.
Native and MPS then consume identical untaped pending requests/streams. Input
clones/setup, namespace normalization and full State/history/RNG verification
are outside hot timing; Engine's own transactional clone and validation remain
inside native resolveChance. All published timings retain the full operation.
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

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.benchmark_campaign_device_state import StateConfig,atomic_json,require,supervise

SCHEMA="campaign-complete-recruitment-chance-benchmark-v5"
FAMILIES=("small_success","small_failure","wide_success","infrastructure_success")
STREAMS=("actual","search","training")
PROFILE_STAGES=("preflight","sample","effects","income","reset","forward_capability","forward",
                "clock","validation","identity","payload","event","random","publish")


@dataclass(frozen=True)
class ChanceConfig(StateConfig):
    devices: tuple[str,...] = ("mps",)
    batch_sizes: tuple[int,...] = (1,4,16,64)
    native_workers: int = 10
    profile_repeats: int = 1
    formatter: str = "reference"
    digest_implementation: str = "reference"
    digest_group_size: int | None = None
    reuse_certified_source: bool = False
    field_group_size: int = 1
    editor_implementation: str = "reference"
    container_implementation: str = "reference"

    def __post_init__(self):
        super().__post_init__()
        require(self.devices==("mps",),"Complete chance timing requires explicit MPS")
        require(type(self.native_workers) is int and 1<=self.native_workers<=10 and
                self.native_workers+self.threads<=self.cpu_budget,"Native pool plus reserved tensor threads must fit twelve cores")
        require(type(self.profile_repeats) is int and self.profile_repeats>0,"Profile repeats must be positive")
        require(self.formatter in {"reference","parallel_units","parallel_fields"},"Choose an explicit supported State formatter")
        require(self.digest_implementation in {"reference","unrolled"},"Choose an explicit supported digest kernel")
        require(self.digest_group_size is None or type(self.digest_group_size) is int and self.digest_group_size>0,
                "Digest group size must be a positive integer or default")
        require(type(self.reuse_certified_source) is bool,"Certified source reuse must be explicit bool")
        require(type(self.field_group_size) is int and self.field_group_size>0,"Field group size must be a positive integer")
        require(type(self.editor_implementation) is str and self.editor_implementation in {"reference","parallel"},
                "Choose an explicit supported State editor")
        require(type(self.container_implementation) is str and self.container_implementation in {"reference","parallel"},
                "Choose an explicit supported container builder")


def gpu_selection(config):
    return {name:getattr(config,name) for name in
        ("formatter","digest_implementation","digest_group_size","reuse_certified_source","field_group_size",
         "editor_implementation","container_implementation")}


def provenance():
    from tools.benchmark_campaign_backends import provenance as base
    value=base()
    value["chance_harness_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    value["chance_probe_sha256"]=hashlib.sha256((ROOT/"src/python_recruitment.inc").read_bytes()).hexdigest()
    value["diagnostic_pool_sha256"]=hashlib.sha256((ROOT/"src/python_diagnostic_pool.inc").read_bytes()).hexdigest()
    return value


def _strings(batch):
    import numpy as np
    result=[]
    for data,offsets in ((batch.context.string_bytes(),batch.context.string_offsets()),(batch.string_bytes(),batch.string_offsets())):
        data=bytes(np.asarray(data));offsets=np.asarray(offsets)
        result.extend(data[int(a):int(b)] for a,b in zip(offsets,offsets[1:]))
    return result


def canonical_native(batch):
    """Normalize ONLY string IDs; retain every record/number/end/RNG word.

    Append-only GPU pools retain dead IDs that a fresh native snapshot omits.
    All referenced string bytes are compared exactly, while unused pool capacity
    is separately checked as a source buffer/usage invariant.
    """
    import numpy as np
    rows=np.array(batch.record_array(),copy=True);offsets=np.array(batch.lane_offsets(),copy=True)
    strings=_strings(batch);mask=rows[:,0]==5;ids=np.unique(rows[mask,1])
    referenced=sorted({strings[int(index)] for index in ids});order={text:i for i,text in enumerate(referenced)}
    mapping=np.zeros(len(strings),dtype=np.int64)
    for index in ids:mapping[int(index)]=order[strings[int(index)]]
    rows[mask,1]=mapping[rows[mask,1]]
    checksum=hashlib.sha256(rows.tobytes()+offsets.tobytes())
    for text in referenced:checksum.update(len(text).to_bytes(8,"little"));checksum.update(text)
    return rows,offsets,referenced,checksum.hexdigest()


def require_exact(actual,expected):
    import numpy as np
    got=canonical_native(actual)
    np.testing.assert_array_equal(got[0],expected[0]);np.testing.assert_array_equal(got[1],expected[1])
    require(got[2]==expected[2],"A referenced State/history/RNG string changed")
    return got[3]


def resident_digest(state):
    from tools.benchmark_campaign_backends import numeric_digest
    return numeric_digest({name:getattr(state,name).detach().cpu().numpy() for name in
        ("records","lengths","sections","string_bytes","string_offsets","errors","suffix_usage")})


def templates(config,deadline):
    """Fixture construction is explicit authoring, never hot rule execution."""
    import gwrl_cpp
    scenario=ROOT/"game_content/scenarios/japan_china_1936"
    base=gwrl_cpp.CampaignEnv(str(scenario),config.seed,training_actions=True)
    initial=json.loads(base.serialize());candidates=[]
    for minor in sorted(name for name in initial["state"]["nations"] if name.startswith("warlord_")):
        require(time.monotonic()<deadline,"Fixture setup exhausted the shared deadline")
        doc=json.loads(base.serialize());state=doc["state"]
        state["clock"].update(nation_index=2,player_turn_serial="2",phase="place_units")
        state["completed_turns"]={"ccp":1,"mongolia":1,"japan":0,"kmt":0}
        state["nations"][minor].update(controller_nation="japan",player=None,power_status="minor")
        env=base.clone();env.restore(json.dumps(doc))
        query=gwrl_cpp.campaign_recruitment_oracle(gwrl_cpp.campaign_recruitment_context(env),[env],[(0,minor)])[0]
        rolls=[action for action in env.legal_actions() if action.kind=="recruitment_roll" and action.parameters["beneficiary"]==minor]
        if rolls and query["threshold"]>0:candidates.append((len(query["choices"]),minor,query["threshold"],env,rolls[0]))
    require(candidates,"No valid controlled-minor recruitment fixture")
    fallible=[row for row in candidates if row[2]<12]
    require(fallible,"No recruitment fixture permits a failed D12 roll")
    small=min(fallible,key=lambda row:(row[0],row[1]));wide=max(candidates,key=lambda row:(row[0],row[1]))
    output={}
    for label,row in (("small_success",small),("small_failure",small),("wide_success",wide),("infrastructure_success",wide)):
        _,minor,threshold,template,_=row;env=template.clone()
        if label=="infrastructure_success":
            doc=json.loads(env.serialize());state=doc["state"]
            land=next(zone for zone,t in state["territories"].items() if t["possessor"]==minor)
            for suffix in ("A","B"):
                identity="benchmark_ship_"+suffix
                state["construction"][identity]={"id":identity,"owner":minor,"type":"battleship","site":None,
                    "queue_position":2,"paid_ipp":7,"remaining_payments":[3],"flags":{}}
            identity="benchmark_damaged_airbase"
            state["facilities"][identity]={"id":identity,"type":"airbase","zone":land,"damage":1,"flags":{}}
            env.restore(json.dumps(doc))
        action=next(a for a in env.legal_actions() if a.kind=="recruitment_roll" and a.parameters["beneficiary"]==minor)
        env.apply_action(action)
        query=gwrl_cpp.campaign_recruitment_oracle(gwrl_cpp.campaign_recruitment_context(env),[env],[(0,minor)])[0]
        output[label]={"env":env,"minor":minor,"threshold":threshold,"choices":len(query["choices"]),
            "request":env.chance_request(),"desired_success":label!="small_failure"}
    return output


def lanes(template,count,seed,deadline):
    """Choose untaped native draws; seed search/setup are excluded from timing."""
    import gwrl_cpp
    request=json.dumps(template["request"]);result=[];evidence=[];cursor=seed
    for lane in range(count):
        active=STREAMS[lane%3]
        while True:
            require(time.monotonic()<deadline,"Untaped fixture seed search exhausted deadline")
            candidate=template["env"].clone_for_search(cursor);doc=json.loads(candidate.serialize())
            # A native seeded search word is a valid full-width state of any
            # identical execution stream; retain all other streams/tape fields.
            doc["random"][active]=doc["random"]["search"];doc["random"]["active"]=active
            sample=gwrl_cpp.campaign_sample_chance_probe([request],[json.dumps(doc["random"])])["rows"][0]
            require(not sample["error"],"Native fixture draw failed")
            raw=sample["effective"][0];chosen=cursor;cursor+=1
            if (raw<=template["threshold"])==template["desired_success"]:break
        candidate.restore(json.dumps(doc));result.append(candidate)
        evidence.append({"native_search_seed":chosen,"active_stream":active,"raw_face":raw,
            "success":template["desired_success"],"minor":template["minor"],"threshold":template["threshold"],
            "choice_count_on_success":template["choices"],"taped":False})
    return result,evidence


def worker(config,device,output,deadline):
    import torch,gwrl_cpp
    from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
    from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
    from studies.campaign.backends.resident_recruitment import ResidentRecruitment
    from studies.campaign.backends.resident_recruitment_effects import ResidentRecruitmentEffects
    from studies.campaign.backends.resident_state_income import ResidentIncomeContext
    from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
    from studies.campaign.backends.resident_state_json import ResidentStateJson
    from studies.campaign.backends.resident_state_json_parallel import ParallelUnitStateJson
    from studies.campaign.backends.resident_state_json_fields import ParallelFieldStateJson
    from studies.campaign.backends.content_digest_metal import inspect_digests
    from studies.campaign.backends.resident_recruitment_chance import ResidentRecruitmentChance,RecruitmentChanceCapacities
    require(device=="mps","No CPU fallback")
    torch.set_num_threads(config.threads)
    torch.set_num_interop_threads(1)
    torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    started=time.perf_counter();source_provenance=provenance();prepared=templates(config,deadline)
    pool=gwrl_cpp.CampaignDiagnosticPool(config.native_workers) if config.native_workers>1 else None
    report={"schema":SCHEMA,"status":"running","config":asdict(config),"provenance":source_provenance,"cases":[],
        "fixture_scope":"Valid restored controlled-minor positions issue the original legal recruitment_roll Action; not a sampled full campaign distribution",
        "scope":"Complete supported recruitment chance transition only; not full-game, MCTS, learning or strategic strength",
        "gpu_selection":gpu_selection(config),
        "certified_reuse_scope":"Repeated immutable source with a precomputed expected identity; no chronological-game or changed-source cache claim",
        "native_pool":{"workers":config.native_workers,"startup_seconds":pool.startup_seconds if pool else 0.},
        "gpu_profile_scope":"Separate synchronized stage diagnostics; synchronization changes overlap and is not end-to-end throughput"}
    def persist():atomic_json(output,report)
    persist()
    for family in FAMILIES:
        for B in config.batch_sizes:
            require(time.monotonic()<deadline,"Shared deadline exhausted")
            setup=time.perf_counter();envs,evidence=lanes(prepared[family],B,config.seed,deadline)
            context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps",editor_implementation=config.editor_implementation,
                container_implementation=config.container_implementation)
            captured=gwrl_cpp.capture_device_states(context.native,envs);before=DeviceStateBatch.from_native(captured,context=context)
            relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
            recruitment=ResidentRecruitment(relations,gwrl_cpp.campaign_recruitment_context(envs[0]))
            formatter_type={"reference":ResidentStateJson,"parallel_units":ParallelUnitStateJson,
                "parallel_fields":ParallelFieldStateJson}[config.formatter]
            field_options={"fragment_group_size":config.field_group_size} if config.formatter=="parallel_fields" else {}
            formatter=formatter_type(CanonicalJsonContext(captured,context),
                digest_implementation=config.digest_implementation,digest_group_size=config.digest_group_size,**field_options)
            handler=ResidentRecruitmentChance(context,ResidentRecruitmentEffects(recruitment),
                ResidentIncomeContext(context,gwrl_cpp.campaign_income_context(envs[0])),formatter,
                reuse_certified_source=config.reuse_certified_source)
            maximum=prepared[family]["choices"];C=before.records.shape[1];N=len(relations.nation_ids)
            cap=C+7+14*maximum+4*N+64;choices=B*maximum
            caps=RecruitmentChanceCapacities(cap,cap,choices,512,
                before.string_offsets.numel()-1+choices+2*B,before.string_bytes.numel()+choices*recruitment.id_capacity+94*B,
                9,262144,1,1)
            before=handler.reserve(before,caps);expected=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
            keys=[env.planning_key() for env in envs]
            require(inspect_digests(expected.engine_keys)==tuple(keys),"Expected source Engine keys differ")
            source_digest=resident_digest(before);torch.mps.synchronize()
            case={"family":family,"lanes":B,"fixtures":evidence,"capacities":asdict(caps),"setup_seconds":time.perf_counter()-setup,
                  "source_buffer_sha256":source_digest,"native":{},"gpu_seconds":[],"gpu_stage_profile_seconds":[]}
            expected_output=None
            for label,executor in (("serial",None),("pool",pool)):
                if label=="pool" and executor is None:continue
                require(time.monotonic()<deadline,"Native timing exhausted deadline")
                native=gwrl_cpp.campaign_recruitment_chance_benchmark(context.native,envs,keys,config.repeats,pool=executor)
                require(native["source_unchanged"] and native["repeated_outputs_exact"],"Native timed source/output drift")
                current=canonical_native(native["output"])
                if expected_output is None:expected_output=current
                else:require_exact(native["output"],expected_output)
                require_exact(native["original"],canonical_native(captured))
                case["native"][label]={key:value for key,value in native.items() if key not in {"original","output"}}
            for _ in range(config.warmups):
                require(time.monotonic()<deadline,"Warmup exhausted deadline")
                result=handler.resolve(before,expected,capacities=caps);torch.mps.synchronize()
                require(result.committed.item(),f"GPU warmup failed: {result.errors.cpu().tolist()}")
                require_exact(result.state.to_native(),expected_output)
            for _ in range(config.repeats):
                require(time.monotonic()<deadline,"GPU timing exhausted deadline")
                result=None;torch.mps.synchronize();tick=time.perf_counter()
                result=handler.resolve(before,expected,capacities=caps);torch.mps.synchronize()
                case["gpu_seconds"].append(time.perf_counter()-tick)
                require(result.committed.item(),f"GPU transition failed: {result.errors.cpu().tolist()}")
                require_exact(result.state.to_native(),expected_output)
                require(inspect_digests(result.identities.engine_keys)==tuple(native["output_engine_keys"]),"Output Engine key changed")
            for _ in range(config.profile_repeats):
                require(time.monotonic()<deadline,"Stage profile exhausted deadline")
                torch.mps.synchronize();last=time.perf_counter();stages={}
                def profile(name):
                    nonlocal last
                    torch.mps.synchronize();now=time.perf_counter();stages[name]=now-last;last=now
                result=handler.resolve(before,expected,capacities=caps,profile=profile);torch.mps.synchronize()
                require(result.committed.item(),"Profiled operation failed")
                require_exact(result.state.to_native(),expected_output);case["gpu_stage_profile_seconds"].append(stages)
            case["output_record_sha256"]=expected_output[3]
            registry=getattr(formatter,"_source_identity_certificates",None)
            case["certified_source_hits"]=registry.hits if registry is not None else 0
            case["certified_source_misses"]=registry.misses if registry is not None else 0
            expected_hits=config.warmups+config.repeats+config.profile_repeats if config.reuse_certified_source else 0
            require(case["certified_source_hits"]==expected_hits and case["certified_source_misses"]==0,
                    "Benchmark did not exercise the declared source identity reuse policy")
            case["source_unchanged"]=resident_digest(before)==source_digest
            require(case["source_unchanged"],"GPU mutated source records/pool/RNG")
            case["full_state_history_rng_and_keys_exact"]=True
            report["cases"].append(case);persist()
            del result,handler,formatter,recruitment,relations,before,captured,context,envs,expected,expected_output,native
            gc.collect();torch.mps.empty_cache()
    report["sources_unchanged"]=source_provenance==provenance()
    report["status"]="completed" if report["sources_unchanged"] else "changed_inputs"
    report["worker_elapsed_seconds"]=time.perf_counter()-started;persist();return report


def finalize(report,config):
    def durations(values,count):
        return isinstance(values,list) and len(values)==count and all(
            type(value) in (int,float) and math.isfinite(value) and value>=0 for value in values)
    def native_valid(value,workers,B):
        return isinstance(value,dict) and value.get("schema")=="campaign-native-recruitment-chance-timing-v1" and \
            value.get("batch_size")==B and value.get("trials")==config.repeats and value.get("workers")==workers and \
            value.get("execution")==("serial_native" if workers==1 else "persistent_native_pool") and \
            value.get("profiled") is False and value.get("source_unchanged") is True and \
            value.get("repeated_outputs_exact") is True and all(durations(value.get(name),config.repeats) for name in
                ("seconds","input_clone_seconds","verification_seconds")) and \
            durations([value.get("pool_startup_seconds")],1) and \
            len(value.get("output_engine_keys",[]))==B and all(isinstance(key,str) and len(key)==64 and
                not set(key)-set("0123456789abcdef") for key in value["output_engine_keys"])
    def case_valid(row):
        B=row.get("lanes");native=row.get("native",{})
        profiles=row.get("gpu_stage_profile_seconds",[])
        return row.get("full_state_history_rng_and_keys_exact") is True and row.get("source_unchanged") is True and \
            row.get("certified_source_hits")== (config.warmups+config.repeats+config.profile_repeats if config.reuse_certified_source else 0) and \
            row.get("certified_source_misses")==0 and \
            durations(row.get("gpu_seconds"),config.repeats) and \
            len(profiles)==config.profile_repeats and all(isinstance(p,dict) and set(p)==set(PROFILE_STAGES) and
                durations(list(p.values()),len(PROFILE_STAGES)) for p in profiles) and \
            set(native)==({"serial"} if config.native_workers==1 else {"serial","pool"}) and \
            native_valid(native.get("serial"),1,B) and (config.native_workers==1 or
                native_valid(native.get("pool"),config.native_workers,B))
    expected={(family,B) for family in FAMILIES for B in config.batch_sizes};cases=report.get("cases",[])
    valid=report.get("schema")==SCHEMA and report.get("status")=="completed" and report.get("sources_unchanged") is True and len(cases)==len(expected)
    valid=valid and report.get("gpu_selection")==gpu_selection(config)
    valid=valid and {(row.get("family"),row.get("lanes")) for row in cases}==expected
    valid=valid and all(case_valid(row) for row in cases)
    pool=report.get("native_pool",{})
    valid=valid and pool.get("workers")==config.native_workers and durations([pool.get("startup_seconds")],1)
    report["matched_complete_transitions"]=bool(valid)
    if report.get("status")=="completed" and not valid:report["status"]="incomplete_or_mismatch"
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--batch-sizes",nargs="+",type=int,default=(1,4,16,64))
    parser.add_argument("--repeats",type=int,default=3);parser.add_argument("--profile-repeats",type=int,default=1)
    parser.add_argument("--native-workers",type=int,default=10);parser.add_argument("--seconds",type=float,default=180)
    parser.add_argument("--formatter",choices=("reference","parallel_units","parallel_fields"),default="reference")
    parser.add_argument("--field-group-size",type=int,default=1)
    parser.add_argument("--digest-implementation",choices=("reference","unrolled"),default="reference")
    parser.add_argument("--digest-group-size",type=int)
    parser.add_argument("--reuse-certified-source",action="store_true")
    parser.add_argument("--editor-implementation",choices=("reference","parallel"),default="reference")
    parser.add_argument("--container-implementation",choices=("reference","parallel"),default="reference")
    parser.add_argument("--_worker",type=Path,help=argparse.SUPPRESS);parser.add_argument("--_device",help=argparse.SUPPRESS)
    parser.add_argument("--_deadline",type=float,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args._worker:
        settings=json.loads(args._worker.read_text());settings["devices"]=tuple(settings["devices"]);settings["batch_sizes"]=tuple(settings["batch_sizes"])
        worker(ChanceConfig(**settings),args._device,args.output,args._deadline);return 0
    config=ChanceConfig(batch_sizes=tuple(args.batch_sizes),repeats=args.repeats,profile_repeats=args.profile_repeats,
        native_workers=args.native_workers,seconds=args.seconds,formatter=args.formatter,
        digest_implementation=args.digest_implementation,digest_group_size=args.digest_group_size,
        reuse_certified_source=args.reuse_certified_source,field_group_size=args.field_group_size,
        editor_implementation=args.editor_implementation,container_implementation=args.container_implementation)
    require(not args.output.exists(),"Choose a fresh evidence path")
    result=supervise(config,"mps",args.output,deadline=time.monotonic()+config.seconds,worker_script=Path(__file__))
    result=finalize(result,config);atomic_json(args.output,result)
    return 0 if result.get("matched_complete_transitions") else 2


if __name__=="__main__":raise SystemExit(main())
