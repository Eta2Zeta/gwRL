"""Certified same-source reuse preserves authoritative preflight semantics."""
from dataclasses import replace
import copy
import gc
import json
import unittest
import weakref
from unittest.mock import patch

import torch

from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_identity_certificates import CAPACITY,source_identity_check
from studies.campaign.backends.resident_state_json import ResidentStateJson
from tests import test_campaign_resident_recruitment_chance as chance_tests

EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()


@unittest.skipUnless(EXACT,"Exact MPS required")
class ResidentIdentityCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs=None):
        before,handler,caps,expected=chance_tests.ResidentRecruitmentChanceTests().setup(envs or [chance_tests.pending_fixture(training=True,face=1)])
        return before,handler,caps,expected

    def check(self,formatter,before,expected,capacity=262144,reuse=True):
        return source_identity_check(formatter,before,expected,byte_capacity=capacity,reuse=reuse)

    def same(self,left,right):
        for group in ("state_json","state_keys","engine_json","engine_keys"):
            a,b=getattr(left,group),getattr(right,group)
            for name in a.__dataclass_fields__:self.assertTrue(torch.equal(getattr(a,name),getattr(b,name)),str((group,name)))

    def test_exact_hit_is_device_read_free_and_reference_default_still_recomputes(self):
        before,handler,caps,expected=self.setup();formatter=handler.state_json
        self.assertFalse(handler.reuse_certified_source)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host copy")), \
             patch.object(torch.Tensor,"numpy",side_effect=AssertionError("Host array")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host list")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(torch.mps,"synchronize",side_effect=AssertionError("Hot fence")), \
             patch("studies.campaign.backends.resident_state_json._kernels",side_effect=AssertionError("Redundant serialization")):
            self.assertIs(self.check(formatter,before,expected),expected)
        recomputed=self.check(formatter,before,expected,reuse=False)
        self.assertIsNot(recomputed,expected);self.same(recomputed,expected)
        self.assertEqual(formatter._source_identity_certificates.hits,1)

    def test_manual_replaced_foreign_and_capacity_changed_results_fall_back(self):
        before,handler,caps,expected=self.setup();formatter=handler.state_json
        for altered in (replace(expected),replace(expected,engine_keys=replace(expected.engine_keys))):
            self.assertIsNot(self.check(formatter,before,altered),altered)
        foreign=ResidentStateJson(formatter.number_context)
        other=foreign.identities(before,byte_capacity=caps.json_byte_capacity)
        self.assertIsNot(self.check(formatter,before,other),other)
        # A shallow-copied formatter must not accidentally issue into the
        # original owner's registry, even though all tensors happen to match.
        copied=copy.copy(formatter);copied_result=copied.identities(before,byte_capacity=caps.json_byte_capacity)
        self.assertIsNot(copied._source_identity_certificates,formatter._source_identity_certificates)
        self.assertIsNot(self.check(formatter,before,copied_result),copied_result)
        for capacity in (0,caps.json_byte_capacity-1,caps.json_byte_capacity+1):
            got=self.check(formatter,before,expected,capacity)
            self.assertIsNot(got,expected)
            self.same(got,formatter.identities(before,byte_capacity=capacity))
        with self.assertRaises(TypeError):self.check(formatter,before,expected,reuse=1)

    def test_complete_source_context_number_rules_and_alias_versions_invalidate(self):
        before,handler,caps,_=self.setup();formatter=handler.state_json
        tensors=[getattr(before,name) for name in ("records","lengths","sections","string_bytes","string_offsets","errors","suffix_usage")]
        tensors.extend(getattr(before.context,name) for name in ("records","string_bytes","string_offsets"))
        tensors.extend(getattr(formatter.number_context,name) for name in ("words","offsets","bytes"));tensors.append(formatter.rules)
        for tensor in tensors:
            with self.subTest(shape=tuple(tensor.shape),dtype=tensor.dtype):
                expected=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
                tensor.view(-1).add_(0)  # supported alias mutation, same values
                got=self.check(formatter,before,expected)
                self.assertIsNot(got,expected);self.same(got,expected)
        expected=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
        old=before.context.rules_id
        try:
            before.context.rules_id=old+"+certificate_fixture"
            self.assertIsNot(self.check(formatter,before,expected),expected)
        finally:before.context.rules_id=old
        expected=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
        old=formatter.number_context
        try:
            formatter.number_context=copy.copy(old)
            self.assertIsNot(self.check(formatter,before,expected),expected)
        finally:formatter.number_context=old
        expected=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
        old=before.context._editor_implementation
        try:
            before.context._editor_implementation="parallel"
            actual=self.check(formatter,before,expected)
            self.assertIsNot(actual,expected);self.same(actual,expected)
        finally:before.context._editor_implementation=old

    def test_all_public_output_buffers_and_nested_replacements_are_stamped(self):
        before,handler,caps,_=self.setup();formatter=handler.state_json
        for group in ("state_json","state_keys","engine_json","engine_keys"):
            template=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
            for name in getattr(template,group).__dataclass_fields__:
                expected=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
                getattr(getattr(expected,group),name).view(-1).add_(0)
                self.assertIsNot(self.check(formatter,before,expected),expected,str((group,name)))
            expected=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
            object.__setattr__(expected,group,replace(getattr(expected,group)))
            self.assertIsNot(self.check(formatter,before,expected),expected)

    def test_inference_tensors_are_uncertifiable_and_failed_source_sizes_remain_exact(self):
        before,handler,caps,_=self.setup();formatter=handler.state_json
        with torch.inference_mode():
            inference=before.snapshot();expected=formatter.identities(inference,byte_capacity=caps.json_byte_capacity)
        self.assertIsNot(self.check(formatter,inference,expected),expected)
        for capacity in (0,1,262144):
            broken=replace(before,errors=before.errors+1)
            expected=formatter.identities(broken,byte_capacity=capacity)
            cached=self.check(formatter,broken,expected,capacity)
            self.assertIs(cached,expected)
            self.same(cached,formatter.identities(broken,byte_capacity=capacity))

    def test_registry_is_bounded_weak_and_retains_no_source_or_history_states(self):
        before,handler,caps,_=self.setup();formatter=handler.state_json;registry=formatter._source_identity_certificates
        owned=before.snapshot();identity=formatter.identities(owned,byte_capacity=caps.json_byte_capacity)
        source_ref=weakref.ref(owned);identity_ref=weakref.ref(identity);key=id(identity)
        del owned,identity;gc.collect()
        self.assertIsNone(source_ref());self.assertIsNone(identity_ref());self.assertNotIn(key,registry.entries)
        retained=[formatter.identities(before,byte_capacity=caps.json_byte_capacity) for _ in range(CAPACITY+2)]
        self.assertEqual(len(registry.entries),CAPACITY)
        self.assertIs(self.check(formatter,before,retained[-1]),retained[-1])
        self.assertIsNot(self.check(formatter,before,retained[0]),retained[0])
        del retained;gc.collect();self.assertLessEqual(len(registry.entries),1)

    def _same_result(self,reference,actual):
        for name in ("records","lengths","sections","string_bytes","string_offsets","errors","suffix_usage"):
            self.assertTrue(torch.equal(getattr(reference.state,name),getattr(actual.state,name)),name)
        for name in ("errors","accepted","committed","handled"):self.assertTrue(torch.equal(getattr(reference,name),getattr(actual,name)),name)
        for group in ("required","stage_errors","attempted"):
            self.assertEqual(set(getattr(reference,group)),set(getattr(actual,group)))
            for name,value in getattr(reference,group).items():self.assertTrue(torch.equal(value,getattr(actual,group)[name]),str((group,name)))
        self.same(reference.identities,actual.identities)

    def test_opt_in_chance_matches_complete_reference_success_failure_tamper_and_capacity(self):
        envs=[chance_tests.pending_fixture(training=True,active=active,face=face) for active in ("actual","search","training") for face in (1,12)]
        before,handler,caps,expected=self.setup(envs);helper=chance_tests.ResidentRecruitmentChanceTests()
        reference=handler.resolve(before,expected,capacities=caps)
        handler.reuse_certified_source=True;actual=handler.resolve(before,expected,capacities=caps)
        self._same_result(reference,actual);helper.assert_native(before,actual,envs)
        self.assertGreater(handler.state_json._source_identity_certificates.hits,0)
        for parameters in ({"capacities":replace(caps,payload_capacity=0)},
                           {"capacities":replace(caps,json_byte_capacity=0)}):
            handler.reuse_certified_source=False;reference=handler.resolve(before,expected,**parameters)
            handler.reuse_certified_source=True;actual=handler.resolve(before,expected,**parameters)
            self._same_result(reference,actual);helper.assert_rollback(before,actual)
        damaged=expected.engine_keys.hex_bytes.clone();damaged[0,0]^=1
        stale=replace(expected,engine_keys=replace(expected.engine_keys,hex_bytes=damaged))
        handler.reuse_certified_source=False;reference=handler.resolve(before,stale,capacities=caps)
        handler.reuse_certified_source=True;actual=handler.resolve(before,stale,capacities=caps)
        self._same_result(reference,actual);helper.assert_rollback(before,actual)
        # Public masked and successful Event/RNG publications are not certified.
        self.assertIsNot(self.check(handler.state_json,actual.state,actual.identities),actual.identities)
        self.assertIsNot(self.check(handler.state_json,reference.state,reference.identities),reference.identities)

    def test_opt_in_action_matches_complete_reference_and_failure_masks(self):
        from tests.test_campaign_resident_recruitment_action import ResidentRecruitmentActionTests
        from tests.test_campaign_resident_recruitment_start import start_fixture
        helper=ResidentRecruitmentActionTests();pairs=[start_fixture(training=True,active=active) for active in ("actual","search","training")]
        envs=[env for env,minor in pairs];setup=helper.setup(envs,[minor for env,minor in pairs]);before,handler,caps,expected,*_=setup
        reference=helper.apply(setup);handler.reuse_certified_source=True;actual=helper.apply(setup)
        self._same_result(reference,actual);helper.assert_native(setup,actual,envs)
        self.assertGreater(handler.state_json._source_identity_certificates.hits,0)
        handler.reuse_certified_source=False;reference=helper.apply(setup,capacities=replace(caps,payload_capacity=0))
        handler.reuse_certified_source=True;actual=helper.apply(setup,capacities=replace(caps,payload_capacity=0))
        self._same_result(reference,actual);helper.assert_rollback(before,actual)
        self.assertIsNot(self.check(handler.state_json,actual.state,actual.identities),actual.identities)

    def test_reviewed_parallel_formatter_has_own_certificates_and_unknown_subclasses_miss(self):
        from studies.campaign.backends.resident_state_json_parallel import ParallelUnitStateJson
        before,handler,caps,expected=self.setup();reference=handler.resolve(before,expected,capacities=caps)
        formatter=ParallelUnitStateJson(handler.state_json.number_context)
        key=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
        self.same(key,expected);self.assertIs(self.check(formatter,before,key),key)
        self.assertIsNot(self.check(handler.state_json,before,key),key)
        handler.state_json=formatter;handler.reuse_certified_source=True
        actual=handler.resolve(before,key,capacities=caps);self._same_result(reference,actual)
        chance_tests.ResidentRecruitmentChanceTests().assert_native(before,actual,[chance_tests.pending_fixture(training=True,face=1)])
        class Unknown(ParallelUnitStateJson):pass
        foreign=Unknown(formatter.number_context);manual=foreign.identities(before,byte_capacity=caps.json_byte_capacity)
        self.assertIsNot(self.check(foreign,before,manual),manual)

    def test_explicit_digest_options_preserve_native_identity_and_invalidate_configuration_changes(self):
        from studies.campaign.backends.resident_state_json_parallel import ParallelUnitStateJson
        before,handler,caps,expected=self.setup();reference=handler.resolve(before,expected,capacities=caps)
        formatter=ParallelUnitStateJson(handler.state_json.number_context,digest_implementation="unrolled",digest_group_size=32)
        key=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
        self.same(key,expected);self.assertIs(self.check(formatter,before,key),key)
        handler.state_json=formatter;handler.reuse_certified_source=True
        actual=handler.resolve(before,key,capacities=caps);self._same_result(reference,actual)
        formatter.digest_group_size=64
        changed=self.check(formatter,before,key);self.assertIsNot(changed,key);self.same(changed,key)
        formatter.digest_implementation="reference"
        changed_again=self.check(formatter,before,changed);self.assertIsNot(changed_again,changed);self.same(changed_again,key)
        for kwargs in ({"digest_implementation":"other"},{"digest_implementation":[]},{"digest_group_size":True},
                       {"digest_group_size":0},{"digest_group_size":1.5}):
            with self.assertRaises(ValueError):ResidentStateJson(formatter.number_context,**kwargs)


if __name__=="__main__":unittest.main()
