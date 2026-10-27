#!/usr/bin/env python3
"""Bounded stage timings for the unchanged resident supplied-route preparation.

Relations, LandAttack declarations and route indexing each include Python input
validation, result allocation, their native Metal dispatch and synchronization.
The full reference preparation is also measured without intermediate fences.
No rule, action, search, model or game-horizon setting is changed.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.benchmark_campaign_device_state import StateConfig,atomic_json,require,supervise
from tools.benchmark_campaign_resident_routes import prepare_workload,provenance as route_provenance,POSITIONS
SCHEMA="campaign-route-preparation-profile-v1"

@dataclass(frozen=True)
class ProfileConfig(StateConfig):
    devices:tuple[str,...]=("mps",)
    batch_sizes:tuple[int,...]=(4,64)
    def __post_init__(self):
        super().__post_init__()
        require(self.devices==("mps",),"Route preparation profile requires explicit MPS")

def provenance():
    result=route_provenance();result["preparation_profiler_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();return result

def worker(config,device,progress,deadline):
    import gc
    import gwrl_cpp
    import torch
    from studies.campaign.curriculum import make_env
    from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
    from studies.campaign.backends.resident_routes import ResidentRoutes
    from studies.campaign.device_runtime import runtime_policy_for_device
    require(device=="mps" and torch.backends.mps.is_available(),"Explicit MPS is required")
    torch.set_num_threads(config.threads);torch.set_num_interop_threads(1)
    torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    policy=runtime_policy_for_device("mps");started=time.perf_counter()
    report={"schema":SCHEMA,"config":asdict(config),"status":"preparing","provenance":provenance(),"cases":[],"scope":__doc__}
    def persist():
        report["elapsed_worker_seconds"]=time.perf_counter()-started
        report["device_memory"]={"live_bytes":torch.mps.current_allocated_memory(),"driver_bytes":torch.mps.driver_allocated_memory()}
        report["device_runtime"]=policy.stats();atomic_json(progress,report)
    def timed(operation):
        require(time.monotonic()<deadline,"Preparation profile shared deadline exhausted")
        torch.mps.synchronize();before=time.perf_counter();result=operation();torch.mps.synchronize()
        return result,time.perf_counter()-before
    persist();workload=prepare_workload(config,deadline)
    report.update(status="running",preparation_completed_three_round_games=1)
    for fixture in workload["fixtures"]:
        env=make_env(fixture["seed"],calendar_rounds=3);env.restore(fixture["serialized"]);raw=env.raw
        serialized=raw.serialize();context=DeviceStateContext(gwrl_cpp.device_state_context(raw),"mps")
        source=DeviceStateBatch.capture([raw],context=context)
        kernel=ResidentRoutes(context,gwrl_cpp.campaign_movement_context(raw))
        for size in config.batch_sizes:
            state=source.fork(torch.zeros(size,dtype=torch.int64,device="mps"))
            def stages():
                fresh=replace(state)
                relation,a=timed(lambda:kernel.relations_context.compute(fresh))
                declaration,b=timed(lambda:kernel.declaration_context.compute(fresh,relations=relation))
                prepared,c=timed(lambda:kernel.prepare(fresh,relations=relation,declarations=declaration))
                combined,d=timed(lambda:kernel.prepare(replace(state)))
                return relation,declaration,prepared,combined,(a,b,c,d)
            for _ in range(config.warmups):stages()
            row={"position":fixture["label"],"lanes":size,"relations_seconds":[],"declarations_seconds":[],
                 "indexes_seconds":[],"full_reference_prepare_seconds":[],
                 "native_checkpoint_sha256":hashlib.sha256(serialized.encode()).hexdigest()}
            for _ in range(config.repeats):
                relation,declaration,prepared,combined,values=stages()
                for key,value in zip(("relations_seconds","declarations_seconds","indexes_seconds","full_reference_prepare_seconds"),values,strict=True):row[key].append(value)
                policy.completed(1)
            for name in ("pairs","pair_errors","nations","nation_errors","present","metadata"):
                require(torch.equal(getattr(relation,name),getattr(combined.relations,name)),"Profile relation result changed")
            for name in ("allowed","errors","presence"):
                require(torch.equal(getattr(declaration,name),getattr(combined.declarations,name)),"Profile declaration result changed")
            require(torch.equal(prepared.indexes,combined.indexes),"Profile index result changed")
            require(raw.serialize()==serialized,"Profile changed source State/history/RNG")
            row["all_prepared_fields_exact"]=True;report["cases"].append(row);persist()
            del state,relation,declaration,prepared,combined;kernel._prepared=None;gc.collect()
        del kernel,source,context,raw,env;gc.collect()
    report["sources_unchanged"]=report["provenance"]==provenance()
    expected={(p,b) for p in POSITIONS for b in config.batch_sizes}
    report["status"]="completed" if report["sources_unchanged"] and len(report["cases"])==len(expected) and {(r["position"],r["lanes"]) for r in report["cases"]}==expected else "changed_inputs"
    persist();return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--batch-sizes",nargs="+",type=int,default=(4,64))
    parser.add_argument("--repeats",type=int,default=5);parser.add_argument("--seconds",type=float,default=180)
    parser.add_argument("--_worker",type=Path,help=argparse.SUPPRESS);parser.add_argument("--_device",help=argparse.SUPPRESS)
    parser.add_argument("--_deadline",type=float,help=argparse.SUPPRESS);args=parser.parse_args(argv)
    if args._worker:
        fields=json.loads(args._worker.read_text());fields["devices"]=tuple(fields["devices"]);fields["batch_sizes"]=tuple(fields["batch_sizes"])
        worker(ProfileConfig(**fields),args._device,args.output,args._deadline);return 0
    require(not args.output.exists(),"Use a fresh profile output; previous evidence is preserved")
    config=ProfileConfig(batch_sizes=tuple(args.batch_sizes),repeats=args.repeats,seconds=args.seconds)
    report=supervise(config,"mps",args.output,deadline=time.monotonic()+config.seconds,worker_script=Path(__file__))
    return 0 if report.get("status")=="completed" else 2
if __name__=="__main__":raise SystemExit(main())
