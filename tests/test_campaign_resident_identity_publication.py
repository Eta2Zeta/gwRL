"""Trusted recruitment publication keeps actual checks distinct from masks."""
from dataclasses import replace
import gc
import unittest
import weakref
from unittest.mock import patch

import torch

from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_identity_certificates import (
    _PublishedSourceCheck,_check_snapshot,source_identity_check,
)
from studies.campaign.backends.resident_recruitment_chance import ResidentRecruitmentChance,RecruitmentChanceCapacities
from studies.campaign.backends.resident_recruitment_effects import ResidentRecruitmentEffects
from tests import test_campaign_resident_recruitment_chance as chance_tests
from tests import test_campaign_resident_recruitment_action as action_tests
from tests import test_campaign_resident_recruitment_start as start_tests
from tests import test_campaign_resident_identity_certificates as certificate_tests

EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()


@unittest.skipUnless(EXACT,"Exact MPS required")
class ResidentIdentityPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs=None):
        return chance_tests.ResidentRecruitmentChanceTests().setup(envs or [chance_tests.pending_fixture(training=True,face=1)])

    def proof(self,formatter,result,capacity=262144):
        check=source_identity_check(formatter,result.state,result.identities,byte_capacity=capacity,reuse=True)
        self.assertIsInstance(check,_PublishedSourceCheck)
        ordinary=formatter.identities(result.state,byte_capacity=capacity)
        for field in ordinary.engine_keys.__dataclass_fields__:
            self.assertTrue(torch.equal(getattr(check.engine_keys,field),getattr(ordinary.engine_keys,field)),field)
        for field in check.state_json.__dataclass_fields__:
            self.assertTrue(torch.equal(getattr(check.state_json,field),getattr(ordinary.state_json,field)),field)
        return check

    def compare(self,reference,actual):certificate_tests.ResidentIdentityCertificateTests()._same_result(reference,actual)

    def test_chronological_start_then_chance_reuses_actual_source_and_matches_native(self):
        helper=action_tests.ResidentRecruitmentActionTests()
        pairs=[start_tests.start_fixture(training=True,active=active) for active in ("actual","search","training")]
        envs=[env for env,minor in pairs];setup=helper.setup(envs,[minor for env,minor in pairs])
        before,handler,caps,key,*_=setup
        reference_start=helper.apply(setup);handler.reuse_certified_source=True;actual_start=helper.apply(setup)
        self.compare(reference_start,actual_start);_,native=helper.assert_native(setup,actual_start,envs)
        self.proof(handler.state_json,actual_start)
        S=actual_start.state.records.shape[1]+4096
        fixed=RecruitmentChanceCapacities(S,S,128,1024,actual_start.state.string_offsets.numel()-1+256,
            actual_start.state.string_bytes.numel()+65536,32,262144,1,1)
        chance=ResidentRecruitmentChance(before.context,ResidentRecruitmentEffects(handler.effects.recruitment),handler.income,handler.state_json)
        reference=chance.resolve(reference_start.state,reference_start.identities,capacities=fixed)
        chance.reuse_certified_source=True;registry=handler.state_json._source_identity_certificates;hits=registry.hits
        actual=chance.resolve(actual_start.state,actual_start.identities,capacities=fixed)
        self.assertEqual(registry.hits,hits+1,"Only real preflight counts as a hit; issuance peeks do not")
        self.compare(reference,actual);self.proof(handler.state_json,actual)
        for env in native:env.resolve_chance()
        self.assertEqual([env.serialize() for env in actual.state.restore_envs()],[env.serialize() for env in native])

    def test_success_failed_roll_and_unselected_lanes_have_exact_actual_checks(self):
        envs=[chance_tests.pending_fixture(training=True,active=active,face=face)
              for active in ("actual","search","training") for face in (1,12)]
        before,handler,caps,expected=self.setup(envs)
        for selected in (None,torch.tensor([True,False,True,False,True,False],device="mps"),torch.zeros(6,dtype=torch.bool,device="mps")):
            handler.reuse_certified_source=False;reference=handler.resolve(before,expected,capacities=caps,selected=selected)
            handler.reuse_certified_source=True;actual=handler.resolve(before,expected,capacities=caps,selected=selected)
            self.compare(reference,actual);self.proof(handler.state_json,actual)
            enabled=None if selected is None else selected.cpu().tolist()
            chance_tests.ResidentRecruitmentChanceTests().assert_native(before,actual,envs,enabled)

    def test_effect_cohort_failure_preserves_before_check_and_public_invalid_masks(self):
        def malformed(doc,minor):
            continuation=doc["state"]["chance"]["continuation"]
            doc["state"]["politics"]["pending"][continuation].pop("threshold")
        envs=[chance_tests.pending_fixture(training=True,face=1),chance_tests.pending_fixture(training=True,face=1,mutate=malformed)]
        before,handler,caps,expected=self.setup(envs)
        reference=handler.resolve(before,expected,capacities=caps)
        handler.reuse_certified_source=True;actual=handler.resolve(before,expected,capacities=caps)
        self.compare(reference,actual);chance_tests.ResidentRecruitmentChanceTests().assert_rollback(before,actual)
        check=self.proof(handler.state_json,actual)
        self.assertFalse(check.engine_keys.errors.any().item())
        self.assertTrue(actual.identities.engine_keys.errors.all().item())
        again=handler.resolve(actual.state,actual.identities,capacities=caps)
        self.assertTrue((again.stage_errors["preflight"]&8).all().item())
        chance_tests.ResidentRecruitmentChanceTests().assert_rollback(actual.state,again)
        self.proof(handler.state_json,again)

    def test_payload_event_state_and_json_capacity_rollbacks_select_actual_before_sizes(self):
        before,handler,caps,expected=self.setup();successful=handler.resolve(before,expected,capacities=caps)
        state_need=successful.required["event_state"].max().item()
        strings,bytes_=successful.required["effects_strings"].cpu().tolist()
        cases=(replace(caps,payload_capacity=0),replace(caps,state_capacity=max(before.records.shape[1],state_need-1)),
            replace(caps,string_capacity=max(before.string_offsets.numel()-1,strings),byte_capacity=max(before.string_bytes.numel(),bytes_)),
            replace(caps,json_byte_capacity=0))
        for fixed in cases:
            handler.reuse_certified_source=False;reference=handler.resolve(before,expected,capacities=fixed)
            handler.reuse_certified_source=True;actual=handler.resolve(before,expected,capacities=fixed)
            self.compare(reference,actual);chance_tests.ResidentRecruitmentChanceTests().assert_rollback(before,actual)
            self.proof(handler.state_json,actual,fixed.json_byte_capacity)

    def test_invalid_expected_rolls_back_and_capacity_changes_use_full_authority(self):
        before,handler,caps,expected=self.setup();damaged=expected.engine_keys.hex_bytes.clone();damaged[0,0]^=1
        stale=replace(expected,engine_keys=replace(expected.engine_keys,hex_bytes=damaged))
        reference=handler.resolve(before,stale,capacities=caps)
        handler.reuse_certified_source=True;actual=handler.resolve(before,stale,capacities=caps)
        self.compare(reference,actual);self.proof(handler.state_json,actual)
        for capacity in (0,262143,262145):
            changed=source_identity_check(handler.state_json,actual.state,actual.identities,byte_capacity=capacity,reuse=True)
            self.assertNotIsInstance(changed,_PublishedSourceCheck)
            certificate_tests.ResidentIdentityCertificateTests().same(changed,handler.state_json.identities(actual.state,byte_capacity=capacity))
        manual=replace(actual.identities)
        self.assertNotIsInstance(source_identity_check(handler.state_json,actual.state,manual,byte_capacity=262144,reuse=True),_PublishedSourceCheck)

    def test_public_private_and_source_alias_tamper_invalidates_the_complete_certificate(self):
        before,handler,caps,expected=self.setup();handler.reuse_certified_source=True;formatter=handler.state_json
        for target in ("public","private","source","commit"):
            result=handler.resolve(before,expected,capacities=caps);check=self.proof(formatter,result)
            if target=="public":result.identities.engine_keys.hex_bytes.view(-1).add_(0)
            elif target=="private":check.engine_keys.hex_bytes.view(-1).add_(0)
            elif target=="source":result.state.records.view(-1).add_(0)
            else:check.committed.logical_not_()
            fallback=source_identity_check(formatter,result.state,result.identities,byte_capacity=262144,reuse=True)
            self.assertNotIsInstance(fallback,_PublishedSourceCheck,target)
            certificate_tests.ResidentIdentityCertificateTests().same(fallback,formatter.identities(result.state,byte_capacity=262144))

    def test_private_check_is_small_weak_and_never_retains_old_source_json_or_history(self):
        before,handler,caps,expected=self.setup();handler.reuse_certified_source=True;formatter=handler.state_json
        result=handler.resolve(before,expected,capacities=caps);published=result.identities
        check=self.proof(formatter,result);_,tensors=_check_snapshot(check)
        self.assertLess(sum(t.numel()*t.element_size() for t in tensors),512)
        self.assertFalse(hasattr(check,"source"));self.assertFalse(hasattr(check.state_json,"data"))
        old=weakref.ref(before);live=weakref.ref(result.state);public=weakref.ref(published)
        registry=formatter._source_identity_certificates;entry=id(published)
        del before,expected,result,handler;gc.collect()
        self.assertIsNone(old());self.assertIsNotNone(live())
        del published;gc.collect()
        self.assertIsNone(public());self.assertIsNone(live());self.assertNotIn(entry,registry.entries)

    def test_action_cohort_rollback_and_no_host_default_paths_keep_reference_masks(self):
        helper=action_tests.ResidentRecruitmentActionTests();good,minor=start_tests.start_fixture(training=True)
        bad,_=start_tests.start_fixture(training=True,sequence=2**31-1)
        setup=helper.setup([good,bad],[minor,minor]);before,handler,caps,*_=setup
        reference=helper.apply(setup);handler.reuse_certified_source=True;actual=helper.apply(setup)
        self.compare(reference,actual);helper.assert_rollback(before,actual);self.proof(handler.state_json,actual)
        selected=torch.tensor([True,False],device="mps")
        handler.reuse_certified_source=False;reference=helper.apply(setup,selected=selected)
        handler.reuse_certified_source=True
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host list")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(torch.mps,"synchronize",side_effect=AssertionError("Hot fence")):
            actual=helper.apply(setup,selected=selected)
            check=source_identity_check(handler.state_json,actual.state,actual.identities,byte_capacity=262144,reuse=True)
        self.assertIsInstance(check,_PublishedSourceCheck);self.compare(reference,actual)
        helper.assert_native(setup,actual,[good,bad],[True,False])

    def test_reviewed_field_formatter_unrolled_source_publication_and_fragment_config_tamper(self):
        from studies.campaign.backends.resident_state_json_fields import ParallelFieldStateJson
        envs=[chance_tests.pending_fixture(training=True,face=1),chance_tests.pending_fixture(training=True,face=12,active="search")]
        before,handler,caps,expected=self.setup(envs);reference=handler.resolve(before,expected,capacities=caps)
        formatter=ParallelFieldStateJson(handler.state_json.number_context,fragment_group_size=1,
            digest_implementation="unrolled",digest_group_size=1)
        key=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
        certificate_tests.ResidentIdentityCertificateTests().same(key,expected)
        self.assertIs(source_identity_check(formatter,before,key,byte_capacity=262144,reuse=True),key)
        handler.state_json=formatter;handler.reuse_certified_source=True
        actual=handler.resolve(before,key,capacities=caps);self.compare(reference,actual)
        chance_tests.ResidentRecruitmentChanceTests().assert_native(before,actual,envs)
        private=self.proof(formatter,actual)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch("studies.campaign.backends.resident_state_json_fields._kernels",side_effect=AssertionError("Redundant JSON")):
            self.assertIs(source_identity_check(formatter,actual.state,actual.identities,byte_capacity=262144,reuse=True),private)
        formatter.fragment_group_size=4
        fallback=source_identity_check(formatter,actual.state,actual.identities,byte_capacity=262144,reuse=True)
        self.assertNotIsInstance(fallback,_PublishedSourceCheck)
        certificate_tests.ResidentIdentityCertificateTests().same(fallback,formatter.identities(actual.state,byte_capacity=262144))
        class Unknown(ParallelFieldStateJson):pass
        foreign=Unknown(formatter.number_context,digest_implementation="unrolled",digest_group_size=1)
        manual=foreign.identities(before,byte_capacity=262144)
        self.assertIsNot(source_identity_check(foreign,before,manual,byte_capacity=262144,reuse=True),manual)


if __name__=="__main__":unittest.main()
