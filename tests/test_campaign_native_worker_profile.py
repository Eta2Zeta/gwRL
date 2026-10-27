"""Native-only stage sweep preserves one-pool lifetime and complete outputs."""
import copy
from dataclasses import asdict
import gc
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

import gwrl_cpp

from tools.profile_campaign_native_workers import (
    FAMILIES, SCHEMA, STAGES, NativeWorkerConfig, executions, finalize,
    invoke_profile, summarize_profile, valid_profile,
)


def profile(config, count):
    return {'schema':'campaign-native-recruitment-chance-timing-v1','batch_size':config.batch_size,'trials':config.trials,
        'workers':count if count is not None else 1,'execution':'persistent_native_pool' if count is not None else 'serial_native',
        'profiled':True,'source_unchanged':True,'repeated_outputs_exact':True,'output_engine_keys':['a'*64]*config.batch_size,
        **{name:[.1]*config.trials for name in ('seconds','input_clone_seconds','verification_seconds',*STAGES)}}


class NativeWorkerHarnessTests(unittest.TestCase):
    def test_default_complete_grid_and_resource_bounds_are_explicit(self):
        config=NativeWorkerConfig()
        self.assertEqual((config.batch_size,config.trials,config.families),(512,3,FAMILIES))
        self.assertEqual([n for n,_ in executions(config)],['serial','pool_1','pool_2','pool_4','pool_6','pool_8','pool_10'])
        self.assertEqual((config.memory_bytes,config.seconds),(4_000_000_000,240))
        for kwargs in ({'batch_size':True},{'worker_counts':(1,1)},{'worker_counts':(2,1)},{'worker_counts':(True,)},
                       {'worker_counts':(11,)},{'cpu_budget':11},{'seconds':241},{'memory_bytes':4_000_000_001},{'families':()}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):NativeWorkerConfig(**kwargs)

    def test_only_one_pool_survives_each_service_call_and_profile_argument_is_exact(self):
        events=[];alive=set()
        class Pool:
            def __init__(self,count):
                self.count=count;alive.add(id(self));events.append(('created',count));self.assert_single()
            def assert_single(self):
                if len(alive)!=1:raise AssertionError('Overlapping pools')
            def __del__(self):alive.discard(id(self));events.append(('released',self.count))
        def probe(context,envs,keys,trials,*,pool,profile):
            self.assertIs(context,'context');self.assertEqual((envs,keys,trials),(['env'],['key'],3));self.assertIs(profile,True)
            events.append(('called',pool.count if pool else None));return {'value':1}
        for count in (None,1,2,4,6,8,10):
            result,lifetime=invoke_profile('context',['env'],['key'],3,count,probe=probe,pool_factory=Pool)
            self.assertEqual(result,{'value':1});self.assertFalse(alive)
            self.assertGreaterEqual(lifetime['pool_release_wall_seconds'],0)
        self.assertEqual(events[0],('called',None));self.assertEqual(events[-1],('released',10))

    def test_original_probe_exception_is_preserved_and_pool_does_not_escape(self):
        alive=[]
        class Pool:
            def __init__(self,count):alive.append(count)
            def __del__(self):alive.pop()
        def fail(*args,**kwargs):raise RuntimeError('Original native failure')
        with self.assertRaisesRegex(RuntimeError,'Original native failure'):
            invoke_profile(None,[],[],1,2,probe=fail,pool_factory=Pool)
        gc.collect();self.assertEqual(alive,[])

    def test_lane_wall_sums_are_explicit_and_not_reported_as_cpu_utilization(self):
        config=NativeWorkerConfig(batch_size=2,trials=1,worker_counts=(1,2),families=('small_success',))
        value=profile(config,2);value['seconds']=[.2];value['guard_worker_seconds']=[.1];value['resolve_worker_seconds']=[.8];value['output_key_worker_seconds']=[.1]
        summary=summarize_profile(value)
        self.assertEqual(summary['summed_lane_wall_seconds'],1.)
        self.assertEqual(summary['summed_lane_wall_over_total_wall'],5.)
        self.assertFalse(any('cpu_time' in name or 'utilization' in name for name in summary))

    def test_finalizer_requires_every_execution_profile_exact_source_and_summary(self):
        config=NativeWorkerConfig(batch_size=2,trials=1,worker_counts=(1,2),families=('small_success',))
        rows=[]
        for label,count in executions(config):
            row=profile(config,count);row.update(label=label,all_native_state_history_rng_keys_exact=True,source_native_checkpoints_unchanged=True,
                pool_creation_wall_seconds=0.,pool_release_wall_seconds=0.,external_complete_verification_seconds=0.,summary=summarize_profile(row));rows.append(row)
        report={'schema':SCHEMA,'status':'completed','config':asdict(config),'sources_unchanged':True,'gpu_runtime_used':False,'mps_allocator_reserved_bytes':0,
                'declared_execution_order':[n for n,_ in executions(config)],'cases':[{'family':'small_success','lanes':2,'source_unchanged':True,'reference_engine_keys':['a'*64]*2,'executions':rows}]}
        self.assertTrue(finalize(copy.deepcopy(report),config)['native_sweep_exact'])
        for mutate in (lambda r:r.update(sources_unchanged=False),lambda r:r.update(mps_allocator_reserved_bytes=1),lambda r:r['cases'][0]['executions'].pop(),
                       lambda r:r['cases'][0]['executions'][0].update(profiled=False),lambda r:r['cases'][0]['executions'][0].update(resolve_worker_seconds=[]),
                       lambda r:r['cases'][0]['executions'][0]['seconds'].__setitem__(0,float('nan')),
                       lambda r:r['cases'][0]['executions'][0].update(summary={}),lambda r:r['cases'][0].update(source_unchanged=False),
                       lambda r:r['cases'][0].update(reference_engine_keys=['b'*64]*2)):
            changed=copy.deepcopy(report);mutate(changed);self.assertFalse(finalize(changed,config)['native_sweep_exact'])

    def test_import_and_package_metadata_do_not_import_torch_or_initialize_mps(self):
        root=Path(__file__).resolve().parents[1]
        code="import sys; import tools.profile_campaign_native_workers as p; r=p.provenance(); assert 'torch' not in sys.modules; assert r['torch_imported'] is False; print(r['package_versions']['torch'])"
        result=subprocess.run([sys.executable,'-c',code],cwd=root,check=True,capture_output=True,text=True,timeout=20)
        self.assertTrue(result.stdout.strip())

    def test_small_actual_serial_pool_profile_matches_full_native_reference_and_sources(self):
        from tools.benchmark_campaign_resident_recruitment_chance import canonical_native,require_exact,templates,lanes
        config=NativeWorkerConfig(batch_size=3,trials=1,worker_counts=(1,2),families=('small_success',))
        deadline=time.monotonic()+30;fixture=templates(config,deadline)['small_success'];envs,_=lanes(fixture,3,config.seed,deadline)
        context=gwrl_cpp.device_state_context(envs[0]);before=[e.serialize() for e in envs];keys=[e.planning_key() for e in envs]
        future=[]
        for env in envs:
            clone=env.clone();clone.resolve_chance();future.append(clone)
        reference=canonical_native(gwrl_cpp.capture_device_states(context,future));source=canonical_native(gwrl_cpp.capture_device_states(context,envs))
        for _,count in executions(config):
            result,_=invoke_profile(context,envs,keys,config.trials,count)
            self.assertTrue(valid_profile(result,config,count));require_exact(result['output'],reference);require_exact(result['original'],source)
            self.assertEqual(result['output_engine_keys'],[e.planning_key() for e in future]);self.assertEqual([e.serialize() for e in envs],before)


if __name__=='__main__':unittest.main()
