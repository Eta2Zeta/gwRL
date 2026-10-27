"""Fenced diagnostics delegate exactly; no production serializer changes."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.profile_campaign_resident_identity import (
    IdentityConfig,IdentityStageProfiler,ROLES,SCHEMA,STAGES,finalize,
)


class IdentityProfileTests(unittest.TestCase):
    def fixture(self):
        operations=[];sentinel=object();source=object()
        class Delegate:
            state_context=object()
            def identities(self,state,*,byte_capacity):operations.append(("ordinary",state,byte_capacity));return sentinel
            def serialize(self,state,*,byte_capacity):operations.append(("serialize",state,byte_capacity));return "encoded"
            def outer_engine_json(self,keys):operations.append(("outer",keys));return "outer_bytes"
        def digest(value):operations.append(("digest",value));return "key:"+value
        ticks=iter(range(10));sync=[]
        wrapper=IdentityStageProfiler(Delegate(),synchronize=lambda:sync.append(True),clock=lambda:next(ticks),digest=digest)
        return wrapper,source,sentinel,operations,sync

    def test_inactive_path_delegates_without_clocks_fences_or_extra_operations(self):
        wrapper,source,sentinel,operations,sync=self.fixture()
        with patch.object(wrapper,"clock",side_effect=AssertionError("Default diagnostic timer")), \
             patch.object(wrapper,"synchronize",side_effect=AssertionError("Default diagnostic fence")):
            self.assertIs(wrapper.identities(source,byte_capacity=17),sentinel)
        self.assertEqual(operations,[("ordinary",source,17)]);self.assertEqual(sync,[])
        self.assertIs(wrapper.state_context,wrapper.delegate.state_context)

    def test_explicit_capture_retains_exact_results_and_four_operation_order(self):
        wrapper,source,_,operations,sync=self.fixture()
        with wrapper.capture() as calls:result=wrapper.identities(source,byte_capacity=17)
        self.assertEqual(operations,[("serialize",source,17),("digest","encoded"),("outer","key:encoded"),("digest","outer_bytes")])
        self.assertEqual(len(sync),5);self.assertEqual(len(calls),1)
        self.assertIs(calls[0].source,source);self.assertIs(calls[0].result,result)
        self.assertIs(result.source,source);self.assertEqual(result.engine_keys,"key:outer_bytes")
        self.assertEqual(calls[0].seconds,dict.fromkeys(STAGES,1))

    def test_exception_resets_capture_and_never_leaves_implicit_profiling_enabled(self):
        wrapper,source,sentinel,_,sync=self.fixture()
        with self.assertRaisesRegex(RuntimeError,"injected"):
            with wrapper.capture():
                with patch.object(wrapper.delegate,"serialize",side_effect=RuntimeError("injected")):
                    wrapper.identities(source,byte_capacity=17)
        before=len(sync);self.assertIs(wrapper.identities(source,byte_capacity=17),sentinel);self.assertEqual(len(sync),before)
        with wrapper.capture() as calls:wrapper.identities(source,byte_capacity=17)
        self.assertEqual(len(calls),1)

    def test_capture_is_not_reentrant_and_config_does_not_reduce_requested_work(self):
        wrapper,source,_,_,_=self.fixture()
        with wrapper.capture() as calls:
            with self.assertRaisesRegex(ValueError,"cannot nest"):
                with wrapper.capture():pass
            wrapper.identities(source,byte_capacity=17)
        self.assertEqual(len(calls),1)
        self.assertEqual(IdentityConfig(batch_sizes=(1,4,16,64)).batch_sizes,(1,4,16,64))
        for kwargs in ({"families":()},{"families":("unknown",)},{"families":("small_success","small_success")},
                       {"devices":("cpu",)},{"repeats":0}):
            with self.assertRaises(ValueError):IdentityConfig(**kwargs)

    def test_final_report_requires_both_exact_roles_every_stage_and_complete_grid(self):
        config=IdentityConfig(batch_sizes=(1,),families=("small_success",),repeats=1)
        def call(role):
            return {"role":role,"lanes":1,"seconds":dict.fromkeys(STAGES,.01),"expected_key_construction_included":False,
                "state_record_lengths":[4000],"state_json_bytes":[35000],"state_json_required_bytes":[35000],"outer_engine_bytes":[200]}
        report={"schema":SCHEMA,"status":"completed","sources_unchanged":True,"cases":[{"family":"small_success","lanes":1,
            "source_unchanged":True,"profiles":[{"calls":[call(role) for role in ROLES],
                "full_state_history_rng_and_keys_exact":True,"all_identity_bytes_and_metadata_exact":True}]}]}
        self.assertTrue(finalize(json.loads(json.dumps(report,sort_keys=True)),config)["identity_profile_exact"])
        for mutate in (lambda r:r["cases"].clear(),lambda r:r.update(sources_unchanged=False),
                       lambda r:r["cases"][0]["profiles"][0]["calls"].pop(),
                       lambda r:r["cases"][0]["profiles"][0]["calls"][0].update(role="after_effects"),
                       lambda r:r["cases"][0]["profiles"][0]["calls"][0]["seconds"].update(state_sha256=float("nan")),
                       lambda r:r["cases"][0]["profiles"][0].update(all_identity_bytes_and_metadata_exact=False)):
            bad=copy.deepcopy(report);mutate(bad);self.assertFalse(finalize(bad,config)["identity_profile_exact"])


class IdentityProfileIntegrationTests(unittest.TestCase):
    def test_source_and_after_effects_full_handler_profiles_match_original_bytes_and_native(self):
        import torch
        from tools.profile_campaign_resident_identity import _same_identity,_describe
        from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
        from tests.test_campaign_resident_recruitment_chance import ResidentRecruitmentChanceTests,pending_fixture
        if not torch.backends.mps.is_available() or not mps_int64_indexing_supported():self.skipTest("Exact MPS unavailable")
        old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
        try:
            helper=ResidentRecruitmentChanceTests()
            envs=[pending_fixture(training=True,face=1),pending_fixture(training=True,face=12,active="search")]
            before,handler,caps,expected=helper.setup(envs)
            original=handler.state_json;wrapper=IdentityStageProfiler(original);handler.state_json=wrapper
            with wrapper.capture() as calls:result=handler.resolve(before,expected,capacities=caps)
            torch.mps.synchronize();helper.assert_native(before,result,envs)
            self.assertEqual(len(calls),2);self.assertIs(calls[0].source,before);self.assertIsNot(calls[1].source,before)
            for call,role in zip(calls,ROLES,strict=True):
                ordinary=original.identities(call.source,byte_capacity=caps.json_byte_capacity)
                torch.mps.synchronize();_same_identity(call.result,ordinary)
                description=_describe(call,role)
                self.assertEqual(set(description["seconds"]),set(STAGES));self.assertTrue(all(v>=0 for v in description["seconds"].values()))
                self.assertEqual(description["state_json_bytes"],description["state_json_required_bytes"])
            self.assertIsNone(wrapper._calls)
        finally:torch.set_num_threads(old)


if __name__=="__main__":unittest.main()
