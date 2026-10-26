#!/usr/bin/env python3
"""Guarded exact native/Metal full political-query matrix comparison.

This is a resident rules-query component, not game transitions, MCTS or learning.
Both sides compute every native relation/player/movement-control/LandAttack
query on identical complete snapshots. Native oracle API is already batched;
GPU extraction and shared relation preparation are included in warm timing.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass,asdict
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.benchmark_campaign_device_state import StateConfig,POSITIONS,atomic_json,digest,require,supervise

SCHEMA='campaign-resident-political-queries-benchmark-v1'

@dataclass(frozen=True)
class QueryConfig(StateConfig):
    devices: tuple[str,...]=('mps',)
    batch_sizes: tuple[int,...]=(1,4,64,256)
    def __post_init__(self):
        super().__post_init__()
        require(self.devices==('mps',),'Queries require explicit Apple MPS; no CPU fallback')


def provenance():
    from tools.benchmark_campaign_device_state import provenance as base
    value=base();value['query_harness_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return value


def worker(config,device,progress,deadline):
    import gc
    import gwrl_cpp
    import numpy as np
    import torch
    from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
    from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
    from studies.campaign.backends.resident_declarations import ResidentLandAttackDeclarations
    from studies.campaign.curriculum import make_env
    from studies.campaign.device_runtime import runtime_policy_for_device
    from tools.benchmark_campaign_backends import Config as ReplayConfig,prepare
    require(device=='mps' and torch.backends.mps.is_available(),'Exact Apple MPS is required')
    started=time.perf_counter();torch.set_num_threads(config.threads);torch.set_num_interop_threads(1)
    recommended=torch.mps.recommended_max_memory();require(recommended>0,'MPS allocator allowance unavailable')
    torch.mps.set_per_process_memory_fraction(min(3_000_000_000,recommended)/recommended)
    policy=runtime_policy_for_device('mps')
    report={'schema':SCHEMA,'config':asdict(config),'device':device,'status':'preparing',
            'provenance':provenance(),'cases':[],'scope':__doc__,
            'software':{'torch':str(torch.__version__),'python':sys.version.split()[0],
                        'threads':torch.get_num_threads(),'interop_threads':torch.get_num_interop_threads()},
            'population':'Each case repeats one real complete snapshot; all relation pairs including dormant/playerless error results are queried',
            'native_baseline':'One batched native oracle call computes all original predicates; result arrays/inspection outside timing',
            'gpu_path':'Resident complete state -> shared relation matrices -> LandAttack declarations; allocation, both dispatches and synchronization included'}
    def persist():
        report['elapsed_worker_seconds']=time.perf_counter()-started
        report['device_memory']={'live_bytes':torch.mps.current_allocated_memory(),'driver_bytes':torch.mps.driver_allocated_memory()}
        report['device_runtime']=policy.stats();atomic_json(progress,report)
    def timed(operation,gpu=False):
        require(time.monotonic()<deadline,'Shared query benchmark wall deadline exhausted')
        torch.mps.synchronize();before=time.perf_counter();value=operation()
        if gpu:torch.mps.synchronize()
        return value,time.perf_counter()-before
    def exact(oracle,relation,declaration):
        pairs=[('pairs',relation.pairs,oracle.pair_array()),('pair_errors',relation.pair_errors,oracle.pair_error_array()),
               ('nations',relation.nations,oracle.nation_array()),('nation_errors',relation.nation_errors,oracle.nation_error_array()),
               ('present',relation.present,oracle.present_array()),('land_attack',declaration.allowed,oracle.land_attack_array()),
               ('land_attack_errors',declaration.errors,oracle.land_attack_error_array())]
        witnesses={}
        for label,actual,expected in pairs:
            host=actual.detach().cpu().numpy();np.testing.assert_array_equal(host,expected)
            witnesses[label]={'shape':list(host.shape),'sha256':hashlib.sha256(host.tobytes()).hexdigest()}
        return {'exact':True,'all_query_arrays':witnesses}
    persist();before=time.perf_counter()
    workload=prepare(ReplayConfig(seeds=(config.seed,)),deadline=deadline)
    fixtures=[row for row in workload['fixtures'] if row['label'] in POSITIONS]
    require(len(fixtures)==len(POSITIONS) and {r['label'] for r in fixtures}==set(POSITIONS),'Missing required real fixtures')
    report.update(status='running',task=workload['task'],workload_sha256=digest(workload),
                  preparation_seconds=time.perf_counter()-before,
                  preparation_completed_three_round_games=len(workload['plans']))
    persist()
    for fixture in fixtures:
        env=make_env(fixture['seed'],calendar_rounds=3);env.restore(fixture['serialized']);raw=env.raw
        original=raw.serialize()
        native_state,context_seconds=timed(lambda:gwrl_cpp.device_state_context(raw))
        context,static_upload_seconds=timed(lambda:DeviceStateContext(native_state,'mps'),gpu=True)
        captured,capture_seconds=timed(lambda:gwrl_cpp.capture_device_states(native_state,[raw]))
        source,upload_seconds=timed(lambda:DeviceStateBatch.from_native(captured,context=context),gpu=True)
        native_relations,relation_context_seconds=timed(lambda:gwrl_cpp.campaign_relations_context(raw))
        def prepare_rules():
            relations=ResidentPoliticalRelations(context,native_relations)
            return relations,ResidentLandAttackDeclarations(relations)
        (relations,declarations),rule_upload_seconds=timed(prepare_rules,gpu=True)
        def gpu_query(state):
            shared=relations.compute(state)
            return shared,declarations.compute(state,shared)
        _,initialization_seconds=timed(lambda:gpu_query(source),gpu=True)
        for size in config.batch_sizes:
            lanes=torch.zeros(size,dtype=torch.int64,device='mps')
            resident,populate_seconds=timed(lambda:source.fork(lanes),gpu=True)
            envs=[raw]*size
            before=time.perf_counter();policy.reset();torch.mps.synchronize();reset_seconds=time.perf_counter()-before
            oracle,cold_native=timed(lambda:gwrl_cpp.campaign_relations_oracle(native_relations,envs))
            (shared,decl),cold_gpu=timed(lambda:gpu_query(resident),gpu=True)
            case={'position':fixture['label'],'lanes':size,
                  'native_checkpoint_sha256':hashlib.sha256(original.encode()).hexdigest(),
                  'native_context_seconds':context_seconds,'native_capture_seconds':capture_seconds,
                  'static_upload_seconds':static_upload_seconds,'dynamic_upload_seconds':upload_seconds,
                  'native_relation_context_seconds':relation_context_seconds,'rule_metadata_upload_seconds':rule_upload_seconds,
                  'initial_gpu_kernel_setup_seconds':initialization_seconds,'resident_population_seconds':populate_seconds,
                  'cold_reset_seconds':reset_seconds,'cold_native_query_seconds':cold_native,'cold_gpu_query_seconds':cold_gpu,
                  'cold_scope':'Public allocator/graph reset; compiled custom shaders and OS caches may remain',
                  'native_query_seconds':[],'gpu_query_seconds':[]}
            for _ in range(config.warmups):
                _,_=timed(lambda:gwrl_cpp.campaign_relations_oracle(native_relations,envs))
                _,_=timed(lambda:gpu_query(resident),gpu=True)
            for _ in range(config.repeats):
                oracle,elapsed=timed(lambda:gwrl_cpp.campaign_relations_oracle(native_relations,envs));case['native_query_seconds'].append(elapsed)
                (shared,decl),elapsed=timed(lambda:gpu_query(resident),gpu=True);case['gpu_query_seconds'].append(elapsed)
                policy.completed(1)
            before=time.perf_counter();case['evidence']=exact(oracle,shared,decl)
            case['host_inspection_seconds']=time.perf_counter()-before
            require(raw.serialize()==original,'Query mutated complete source State/history/RNG')
            case['source_unchanged']=True;report['cases'].append(case);persist()
            del oracle,shared,decl,resident,lanes,envs;gc.collect()
        del source,captured,context,native_state,native_relations,relations,declarations,raw,env;gc.collect()
    report['sources_unchanged']=report['provenance']==provenance()
    report['status']='completed' if report['sources_unchanged'] else 'changed_inputs';persist();return report


def finalize(result,config):
    expected={(p,b) for p in POSITIONS for b in config.batch_sizes};cases=result.get('cases',[])
    exact=(result.get('status')=='completed' and result.get('sources_unchanged') is True and
           len(cases)==len(expected) and {(r.get('position'),r.get('lanes')) for r in cases}==expected and
           all(r.get('evidence',{}).get('exact') is True and r.get('source_unchanged') is True and
               len(r.get('native_query_seconds',[]))==config.repeats and len(r.get('gpu_query_seconds',[]))==config.repeats
               for r in cases))
    result['matched_complete_queries']=bool(exact)
    if result.get('status')=='completed' and not exact:result['status']='incomplete_or_mismatch'
    return result


def run(config,output):
    output=Path(output).resolve();require(not output.exists(),'Choose a fresh output; previous evidence is preserved')
    report=supervise(config,'mps',output,deadline=time.monotonic()+config.seconds,worker_script=Path(__file__))
    report=finalize(report,config);atomic_json(output,report);return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--batch-sizes',nargs='+',type=int,default=(1,4,64,256))
    parser.add_argument('--repeats',type=int,default=5);parser.add_argument('--seconds',type=float,default=180)
    parser.add_argument('--memory-bytes',type=int,default=8_000_000_000)
    parser.add_argument('--_worker',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--_device',choices=('mps',),help=argparse.SUPPRESS)
    parser.add_argument('--_deadline',type=float,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args._worker:
        value=json.loads(args._worker.read_text());value['devices']=tuple(value['devices']);value['batch_sizes']=tuple(value['batch_sizes'])
        worker(QueryConfig(**value),args._device,args.output,args._deadline);return 0
    config=QueryConfig(batch_sizes=tuple(args.batch_sizes),repeats=args.repeats,seconds=args.seconds,memory_bytes=args.memory_bytes)
    return 0 if run(config,args.output)['status']=='completed' else 2

if __name__=='__main__':raise SystemExit(main())
