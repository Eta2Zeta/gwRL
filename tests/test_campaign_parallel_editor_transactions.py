"""Parallel editor composition keeps complete Engine transaction results exact."""
from dataclasses import replace
import unittest
from unittest.mock import patch

import torch

from studies.campaign.backends.device_state import DeviceStateContext
from tests import test_campaign_resident_recruitment_action as action_tests
from tests import test_campaign_resident_recruitment_chance as chance_tests
from tests import test_campaign_resident_recruitment_start as start_tests
from tests import test_campaign_resident_identity_certificates as certificate_tests


@unittest.skipUnless(chance_tests.EXACT_MPS,"Lossless Apple GPU required")
class ParallelEditorTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,module,helper,*args):
        def context(native,device):return DeviceStateContext(native,device,editor_implementation="parallel")
        with patch.object(module,"DeviceStateContext",side_effect=context):return helper.setup(*args)

    def same(self,reference,parallel):
        certificate_tests.ResidentIdentityCertificateTests()._same_result(reference,parallel)

    def test_complete_success_failure_and_retained_screening_all_execution_streams(self):
        helper=chance_tests.ResidentRecruitmentChanceTests()
        envs=[chance_tests.pending_fixture(training=True,active=stream,face=face)
            for stream in ("actual","search","training") for face in (1,12)]
        envs.append(chance_tests.retained_naval_fixture(face=12))
        before,reference,caps,key=helper.setup(envs)
        source,parallel,other,expected=self.setup(chance_tests,helper,envs)
        self.assertEqual(other,caps)
        for selected in (None,torch.tensor([True,False,True,False,True,False,True],device="mps")):
            actual=parallel.resolve(source,expected,capacities=caps,selected=selected)
            original=reference.resolve(before,key,capacities=caps,selected=selected)
            self.same(original,actual)
            helper.assert_native(source,actual,envs,None if selected is None else selected.cpu().tolist())

    def test_capacity_and_unsupported_hook_rollbacks_keep_all_stage_errors_and_requirements(self):
        helper=chance_tests.ResidentRecruitmentChanceTests()
        envs=[chance_tests.pending_fixture(training=True,face=1),chance_tests.retained_naval_fixture(kind="force",face=12)]
        before,reference,caps,key=helper.setup(envs)
        source,parallel,_,expected=self.setup(chance_tests,helper,envs)
        for fixed in (caps,replace(caps,payload_capacity=0),replace(caps,json_byte_capacity=0)):
            original=reference.resolve(before,key,capacities=fixed)
            actual=parallel.resolve(source,expected,capacities=fixed)
            self.same(original,actual);helper.assert_rollback(source,actual)

    def test_full_recruitment_start_action_and_failed_payload_publication_match_native(self):
        helper=action_tests.ResidentRecruitmentActionTests()
        pairs=[start_tests.start_fixture(training=True,active=stream) for stream in ("actual","search","training")]
        envs=[env for env,_ in pairs];minors=[minor for _,minor in pairs]
        reference=helper.setup(envs,minors);parallel=self.setup(action_tests,helper,envs,minors)
        original=helper.apply(reference);actual=helper.apply(parallel)
        self.same(original,actual);helper.assert_native(parallel,actual,envs)
        original=helper.apply(reference,capacities=replace(reference[2],payload_capacity=0))
        actual=helper.apply(parallel,capacities=replace(parallel[2],payload_capacity=0))
        self.same(original,actual)
        self.assertEqual([env.serialize() for env in actual.state.restore_envs()],[env.serialize() for env in envs])


if __name__=="__main__":unittest.main()
