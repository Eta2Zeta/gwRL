"""Complete native chance probe and strict paired-timing evidence contract."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import time
import unittest

import gwrl_cpp
import numpy as np

from tools.benchmark_campaign_resident_recruitment_chance import (
    ChanceConfig,FAMILIES,PROFILE_STAGES,SCHEMA,canonical_native,finalize,gpu_selection,lanes,require_exact,templates,
)

SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"


def pending(active="actual",seed=41):
    env=gwrl_cpp.CampaignEnv(str(SCENARIO),seed,training_actions=True)
    doc=json.loads(env.serialize());state=doc["state"]
    state["clock"].update(nation_index=2,player_turn_serial="2",phase="place_units")
    state["completed_turns"].update(ccp=1,mongolia=1)
    minor=next(name for name in state["nations"] if name.startswith("warlord_"))
    state["nations"][minor].update(controller_nation="japan",player=None,power_status="minor")
    env.restore(json.dumps(doc))
    env.apply_action(next(action for action in env.legal_actions() if action.kind=="recruitment_roll" and action.parameters["beneficiary"]==minor))
    doc=json.loads(env.serialize());doc["random"].update(active=active,test_tape=[],tape_position="0")
    env.restore(json.dumps(doc));return env


class RecruitmentChanceNativeBenchmarkTests(unittest.TestCase):
    def test_complete_probe_serial_and_pool_match_original_engine_and_keys_without_mutation(self):
        envs=[pending(active,41+i) for i,active in enumerate(("actual","search","training"))]
        context=gwrl_cpp.device_state_context(envs[0]);keys=[env.planning_key() for env in envs]
        source=[env.serialize() for env in envs];expected=[]
        for env in envs:
            out=env.clone();out.resolve_chance();expected.append(out)
        packed=gwrl_cpp.capture_device_states(context,expected);canonical=canonical_native(packed)
        pool=gwrl_cpp.CampaignDiagnosticPool(2)
        for executor in (None,pool):
            result=gwrl_cpp.campaign_recruitment_chance_benchmark(context,envs,keys,2,pool=executor)
            self.assertTrue(result["source_unchanged"]);self.assertTrue(result["repeated_outputs_exact"])
            self.assertEqual(result["workers"],2 if executor else 1)
            self.assertEqual(result["output_engine_keys"],[env.planning_key() for env in expected])
            self.assertEqual([env.serialize() for env in gwrl_cpp.restore_device_states(result["output"])],[env.serialize() for env in expected])
            require_exact(result["output"],canonical)
            require_exact(result["original"],canonical_native(gwrl_cpp.capture_device_states(context,envs)))
            for name in ("seconds","input_clone_seconds","verification_seconds"):
                self.assertEqual(len(result[name]),2);self.assertTrue(all(value>=0 for value in result[name]))
            self.assertEqual(result["guard_worker_seconds"],[]);self.assertFalse(result["profiled"])
            self.assertIn("internal clone/validation/history/RNG",result["timed_scope"])
            self.assertIn("input trial clones",result["excluded_scope"])
        self.assertEqual([env.serialize() for env in envs],source)

    def test_worker_exception_and_profile_are_reusable_and_never_commit_sources(self):
        envs=[pending("actual"),pending("training")];context=gwrl_cpp.device_state_context(envs[0])
        keys=[env.planning_key() for env in envs];source=[env.serialize() for env in envs]
        pool=gwrl_cpp.CampaignDiagnosticPool(2)
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError,"Stale recruitment benchmark Engine key"):
                gwrl_cpp.campaign_recruitment_chance_benchmark(context,envs,[keys[0],"0"*64],2,pool=pool)
            result=gwrl_cpp.campaign_recruitment_chance_benchmark(context,envs,keys,2,pool=pool,profile=True)
            self.assertTrue(result["profiled"])
            for name in ("guard_worker_seconds","resolve_worker_seconds","output_key_worker_seconds"):
                self.assertEqual(len(result[name]),2);self.assertTrue(all(value>=0 for value in result[name]))
            self.assertTrue(result["source_unchanged"]);self.assertTrue(result["repeated_outputs_exact"])
        self.assertEqual([env.serialize() for env in envs],source)

    def test_context_request_key_and_trial_failures_remain_errors(self):
        env=pending();context=gwrl_cpp.device_state_context(env);source=env.serialize()
        for envs,keys,trials in (([],[],1),([env],[],1),([env],[env.planning_key()],0),
                                ([env],[env.planning_key()],1000001),([env],["A"*64],1)):
            with self.assertRaises(ValueError):gwrl_cpp.campaign_recruitment_chance_benchmark(context,envs,keys,trials)
        other=gwrl_cpp.CampaignEnv(str(SCENARIO),41,training_actions=True)
        with self.assertRaisesRegex(ValueError,"pending recruitment"):
            gwrl_cpp.campaign_recruitment_chance_benchmark(context,[other],[other.planning_key()],1)
        self.assertEqual(env.serialize(),source)

    def test_fixture_families_are_valid_untaped_and_native_outcomes_match_intent(self):
        config=ChanceConfig(batch_sizes=(1,),repeats=1,native_workers=2)
        deadline=time.monotonic()+25;fixtures=templates(config,deadline)
        self.assertEqual(set(fixtures),set(FAMILIES))
        for name,fixture in fixtures.items():
            envs,evidence=lanes(fixture,3,config.seed,deadline)
            self.assertEqual([row["active_stream"] for row in evidence],["actual","search","training"])
            for env,row in zip(envs,evidence,strict=True):
                self.assertFalse(row["taped"]);self.assertEqual(json.loads(env.serialize())["random"]["test_tape"],[])
                old=env.serialize();out=env.clone();out.resolve_chance();self.assertEqual(env.serialize(),old)
                self.assertEqual(bool(json.loads(out.serialize())["state"]["decisions"]),fixture["desired_success"])
                self.assertEqual(row["raw_face"]<=row["threshold"],fixture["desired_success"])

    def test_string_namespace_normalization_keeps_every_other_record_bit(self):
        def fake(pool,ids,number=1):
            data=b"".join(pool);offsets=np.array([0]+list(np.cumsum([len(x) for x in pool])),dtype=np.int64)
            rows=np.array([[5,ids[0],0,0,1],[5,ids[1],0,0,2],[4,0,number,2**31,3]],dtype=np.int64)
            return SimpleNamespace(context=SimpleNamespace(string_bytes=lambda:np.zeros(0,dtype=np.uint8),
                string_offsets=lambda:np.array([0],dtype=np.int64)),string_bytes=lambda:np.frombuffer(data,dtype=np.uint8),
                string_offsets=lambda:offsets,record_array=lambda:rows,lane_offsets=lambda:np.array([0,3],dtype=np.int64))
        first=fake([b"alpha",b"beta"],[0,1]);same=fake([b"dead",b"beta",b"alpha"],[2,1])
        self.assertEqual(require_exact(same,canonical_native(first)),canonical_native(first)[3])
        with self.assertRaises(AssertionError):require_exact(fake([b"alpha",b"beta"],[0,1],number=2),canonical_native(first))

    def test_finalizer_requires_complete_grid_finite_timings_and_native_pool_proof(self):
        config=ChanceConfig(batch_sizes=(1,),repeats=1,native_workers=2)
        def native(workers):
            return {"schema":"campaign-native-recruitment-chance-timing-v1","batch_size":1,"trials":1,"workers":workers,
                "execution":"serial_native" if workers==1 else "persistent_native_pool","profiled":False,
                "source_unchanged":True,"repeated_outputs_exact":True,"seconds":[.1],"input_clone_seconds":[.01],
                "verification_seconds":[.02],"pool_startup_seconds":.01,"output_engine_keys":["a"*64]}
        report={"schema":SCHEMA,"status":"completed","sources_unchanged":True,"native_pool":{"workers":2,"startup_seconds":.01},
            "gpu_selection":gpu_selection(config),
            "cases":[{"family":family,"lanes":1,"source_unchanged":True,"full_state_history_rng_and_keys_exact":True,
                "certified_source_hits":0,"certified_source_misses":0,
                "gpu_seconds":[.1],"gpu_stage_profile_seconds":[dict.fromkeys(PROFILE_STAGES,.01)],
                "native":{"serial":native(1),"pool":native(2)}} for family in FAMILIES]}
        self.assertTrue(finalize(copy.deepcopy(report),config)["matched_complete_transitions"])
        # Atomic JSON writes sort keys; stage order is not a serialized contract.
        self.assertTrue(finalize(json.loads(json.dumps(report,sort_keys=True)),config)["matched_complete_transitions"])
        for mutate in (lambda r:r["cases"].pop(),lambda r:r["cases"][0]["gpu_seconds"].__setitem__(0,float("nan")),
                       lambda r:r["cases"][0]["native"]["pool"].update(workers=1),lambda r:r.pop("native_pool"),
                       lambda r:r["gpu_selection"].update(formatter="parallel_units"),
                       lambda r:r["cases"][0].update(certified_source_hits=1),
                       lambda r:r["cases"][0].update(source_unchanged=False),
                       lambda r:r["cases"][0]["native"]["serial"].update(repeated_outputs_exact=False)):
            bad=copy.deepcopy(report);mutate(bad);self.assertFalse(finalize(bad,config)["matched_complete_transitions"])
        for kwargs in ({"native_workers":11},{"native_workers":True},{"profile_repeats":0}):
            with self.assertRaises(ValueError):ChanceConfig(**kwargs)

    def test_explicit_optimization_choices_preserve_default_and_reuse_evidence(self):
        baseline=ChanceConfig()
        self.assertEqual(gpu_selection(baseline),dict(formatter="reference",digest_implementation="reference",
            digest_group_size=None,reuse_certified_source=False))
        for kwargs in ({"formatter":"auto"},{"digest_implementation":"unknown"},{"digest_group_size":True},
                       {"digest_group_size":0},{"digest_group_size":1.5},{"reuse_certified_source":1}):
            with self.assertRaises(ValueError):ChanceConfig(**kwargs)
        chosen=ChanceConfig(formatter="parallel_units",digest_implementation="unrolled",digest_group_size=32,
            reuse_certified_source=True)
        self.assertEqual(gpu_selection(chosen),dict(formatter="parallel_units",digest_implementation="unrolled",
            digest_group_size=32,reuse_certified_source=True))


if __name__=="__main__":unittest.main()
