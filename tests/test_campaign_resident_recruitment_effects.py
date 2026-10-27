"""Exact native recruitment branch, transaction rollback and all saved inputs."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext,SECTION_NAMES
from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
from studies.campaign.backends.resident_recruitment import ResidentRecruitment
from studies.campaign.backends.resident_recruitment_effects import ResidentRecruitmentEffects
from studies.campaign.backends.packed_chance_metal import sample_packed_chance
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from tests.test_campaign_resident_recruitment_chance import pending_fixture

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU execution unavailable")
class ResidentRecruitmentEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=torch.get_num_threads();torch.set_num_threads(2)
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old)

    def setup(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        before=DeviceStateBatch.capture(envs,context=context)
        relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
        native=gwrl_cpp.campaign_recruitment_context(envs[0])
        recruitment=ResidentRecruitment(relations,native)
        effects=ResidentRecruitmentEffects(recruitment)
        sampled=sample_packed_chance(before,dice_capacity=1,roll_capacity=1)
        return before,effects,native,sampled

    def assert_native(self,before,result,envs,native,sampled):
        faces=sampled.faces.cpu().tolist()
        oracle=gwrl_cpp.campaign_recruitment_effects_oracle(native,envs,faces)
        self.assertEqual(result.errors.cpu().tolist(),[item["error"] for item in oracle])
        actual=[json.loads(env.serialize()) for env in result.state.restore_envs()]
        self.assertEqual([doc["state"] for doc in actual],[json.loads(item["state_json"]) for item in oracle])
        self.assertEqual(result.handled.cpu().tolist(),[item["handled"] for item in oracle])
        self.assertEqual([doc["random"] for doc in actual],[json.loads(env.serialize())["random"] for env in envs])
        old,new=before.records.cpu(),result.state.records.cpu()
        original,after=before.sections.cpu(),result.state.sections.cpu()
        for index,name in enumerate(SECTION_NAMES):
            if name in {"state","state.politics","state.decisions","state.chance","state.flags"}:continue
            for lane in range(len(envs)):
                a,b=int(original[lane,index]),int(after[lane,index])
                left,right=old[lane,a:int(old[lane,a,4])].clone(),new[lane,b:int(new[lane,b,4])].clone()
                left[:,4]-=a;right[:,4]-=b;self.assertTrue(torch.equal(left,right),name)
        return actual,oracle

    def test_all_d12_outcomes_match_original_rule_without_outer_hooks_or_rng_consumption(self):
        envs=[pending_fixture(face=face,training=False) for face in range(1,13)]
        before,effects,native,sampled=self.setup(envs)
        source=[env.serialize() for env in envs]
        result=effects.apply(before,sampled,**effects.reserve(before,choice_capacity=128))
        self.assertTrue(result.committed.cpu().item())
        actual,_=self.assert_native(before,result,envs,native,sampled)
        self.assertEqual([env.serialize() for env in envs],source)
        self.assertTrue(actual[0]["state"]["decisions"])
        self.assertFalse(actual[-1]["state"]["decisions"])
        self.assertTrue(all(doc["state"]["chance"] is None for doc in actual))

    def test_saved_threshold_controls_success_and_empty_current_choices_do_not_increment(self):
        def high(doc,minor):
            key=doc["state"]["chance"]["continuation"]
            doc["state"]["politics"]["pending"][key]["threshold"]=2**31-1
        success=pending_fixture(face=12,mutate=high)
        empty=pending_fixture(face=1,empty=True)
        before,effects,native,sampled=self.setup([success,empty])
        result=effects.apply(before,sampled,**effects.reserve(before,choice_capacity=64))
        self.assertTrue(result.committed.cpu().item());actual,_=self.assert_native(before,result,[success,empty],native,sampled)
        self.assertTrue(actual[0]["state"]["decisions"])
        self.assertFalse(actual[1]["state"]["decisions"])
        prior=json.loads(empty.serialize())["state"]
        self.assertEqual(actual[1]["state"]["flags"].get("politics_sequence"),prior["flags"].get("politics_sequence"))

    def test_negative_zero_fractional_threshold_missing_beneficiary_and_mismatch_rollback(self):
        cases=[]
        for threshold in (-0.0,0,-1,1.0000000000000002,1e200,"wrong"):
            def mutate(doc,minor,value=threshold):
                key=doc["state"]["chance"]["continuation"]
                doc["state"]["politics"]["pending"][key]["threshold"]=value
            cases.append(pending_fixture(face=12,mutate=mutate))
        def missing(doc,minor):doc["state"]["politics"]["pending"][doc["state"]["chance"]["continuation"]].pop("beneficiary")
        def different(doc,minor):doc["state"]["politics"]["pending"][doc["state"]["chance"]["continuation"]]["beneficiary"]="japan"
        cases.extend([pending_fixture(face=12,mutate=missing),pending_fixture(face=12,mutate=different)])
        for env in cases:
            with self.subTest(source=json.loads(env.serialize())["state"]["chance"]["id"]):
                before,effects,native,sampled=self.setup([env])
                result=effects.apply(before,sampled,**effects.reserve(before,choice_capacity=32))
                self.assertEqual(result.errors.cpu().tolist(),[2]);self.assertFalse(result.committed.cpu().item())
                self.assert_native(before,result,[env],native,sampled)
                self.assertTrue(torch.equal(result.state.records[:,:before.records.shape[1]],before.records))
                self.assertTrue(torch.equal(result.state.suffix_usage,before.suffix_usage))

    def test_nonempty_reroll_faces_with_zero_maximum_are_allowed(self):
        def faces(doc,minor):doc["state"]["chance"]["dice"][0]["reroll_faces"]=[1,12]
        env=pending_fixture(face=1,mutate=faces)
        before,effects,native,sampled=self.setup([env])
        result=effects.apply(before,sampled,**effects.reserve(before,choice_capacity=32))
        self.assertTrue(result.committed.cpu().item());self.assert_native(before,result,[env],native,sampled)

    def test_signed_sequence_names_and_overflow_are_lazy_until_a_decision_exists(self):
        for value in (-2**31,-2,-1,0,2**31-2):
            env=pending_fixture(face=1,mutate=lambda doc,minor,number=value:doc["state"]["flags"].update(politics_sequence=number))
            before,effects,native,sampled=self.setup([env])
            result=effects.apply(before,sampled,**effects.reserve(before,choice_capacity=32))
            self.assertTrue(result.committed.cpu().item());actual,_=self.assert_native(before,result,[env],native,sampled)
            decision=actual[0]["state"]["decisions"][-1]
            self.assertEqual(decision["id"],"recruitment_choice_"+str(value+1))
            self.assertEqual(decision["continuation"],decision["id"])
            self.assertTrue(all(option["decision"]==decision["id"] for option in decision["options"]))
        failed=pending_fixture(face=12,mutate=lambda doc,minor:doc["state"]["flags"].update(politics_sequence=2**31-1))
        before,effects,native,sampled=self.setup([failed]);result=effects.apply(before,sampled,**effects.reserve(before,choice_capacity=32))
        self.assertTrue(result.committed.cpu().item());self.assert_native(before,result,[failed],native,sampled)
        overflow=pending_fixture(face=1,mutate=lambda doc,minor:doc["state"]["flags"].update(politics_sequence=2**31-1))
        before,effects,native,sampled=self.setup([overflow]);result=effects.apply(before,sampled,**effects.reserve(before,choice_capacity=32))
        self.assertEqual(result.errors.cpu().tolist(),[2]);self.assertFalse(result.committed.cpu().item())
        self.assert_native(before,result,[overflow],native,sampled)

    def test_pending_erasure_precedes_player_resolution_and_choice_regeneration(self):
        env=pending_fixture(face=1)
        doc=json.loads(env.serialize());state=doc["state"];minor=state["chance"]["nation"]
        old=state["chance"]["continuation"];key="warlord_defense_player:"+minor
        # A generic pending object is not a valid temporary defense-player
        # override. Native erasure must happen before politicalPlayer is read.
        state["politics"]["pending"][key]=state["politics"]["pending"].pop(old)
        state["chance"]["continuation"]=key
        # Remove ordinary controller/player so the erased override now makes
        # politicalPlayer fail, matching the original lazy recruitment branch.
        state["nations"][minor].update(controller_nation=None,player=None)
        env.restore(json.dumps(doc))
        before,effects,native,sampled=self.setup([env])
        result=effects.apply(before,sampled,**effects.reserve(before,choice_capacity=32))
        self.assertEqual(result.errors.cpu().tolist(),[2]);self.assert_native(before,result,[env],native,sampled)
        self.assertEqual(result.state.restore_envs()[0].serialize(),env.serialize())

    def test_selected_cohort_rollback_and_unselected_lazy_errors(self):
        good=pending_fixture(face=1)
        bad=pending_fixture(face=1,mutate=lambda doc,minor:doc["state"]["flags"].update(politics_sequence=2**31-1))
        before,effects,native,sampled=self.setup([good,bad])
        result=effects.apply(before,sampled,**effects.reserve(before,choice_capacity=64))
        self.assertEqual(result.errors.cpu().tolist(),[0,2]);self.assertEqual(result.accepted.cpu().tolist(),[False,False])
        self.assertEqual([env.serialize() for env in result.state.restore_envs()],[good.serialize(),bad.serialize()])
        self.assertTrue(torch.equal(result.state.suffix_usage,before.suffix_usage))
        selected=torch.tensor([True,False],dtype=torch.bool,device="mps")
        result=effects.apply(before,sampled,selected,**effects.reserve(before,choice_capacity=64))
        self.assertEqual(result.errors.cpu().tolist(),[0,0]);self.assertEqual(result.accepted.cpu().tolist(),[True,False])
        self.assertEqual(result.state.restore_envs()[1].serialize(),bad.serialize())

    def test_all_capacities_are_retryable_and_never_publish_partial_records_or_strings(self):
        env=pending_fixture(face=1);before,effects,native,sampled=self.setup([env])
        enough=effects.reserve(before,choice_capacity=32)
        variants=[dict(enough,choice_capacity=0),dict(enough,parameter_byte_capacity=0),
                  dict(enough,state_capacity=before.records.shape[1]),dict(enough,block_capacity=1),
                  dict(enough,string_capacity=before.string_offsets.numel()-1,byte_capacity=before.string_bytes.numel())]
        for capacities in variants:
            with self.subTest(capacities=capacities):
                failed=effects.apply(before,sampled,**capacities)
                self.assertFalse(failed.committed.cpu().item());self.assertEqual(failed.errors.cpu().tolist(),[5])
                self.assertEqual(failed.state.restore_envs()[0].serialize(),env.serialize())
                self.assertTrue(torch.equal(failed.state.suffix_usage,before.suffix_usage))
        result=effects.apply(before,sampled,**enough)
        self.assertTrue(result.committed.cpu().item());self.assert_native(before,result,[env],native,sampled)

    def test_no_hot_host_reads_and_stale_sample_or_foreign_buffers_rejected(self):
        env=pending_fixture(face=1,training=True);before,effects,native,sampled=self.setup([env]);capacities=effects.reserve(before,choice_capacity=32)
        effects.apply(before,sampled,**capacities)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host values")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(json,"loads",side_effect=AssertionError("JSON hot path")), \
             patch.object(gwrl_cpp,"campaign_recruitment_effects_oracle",side_effect=AssertionError("CPU fallback")):
            result=effects.apply(before,sampled,**capacities)
        self.assertTrue(result.committed.cpu().item());self.assert_native(before,result,[env],native,sampled)
        with self.assertRaises(ValueError):effects.apply(before.snapshot(),sampled,**capacities)
        corrupted=replace(sampled,effective=sampled.effective+1)
        result=effects.apply(before,corrupted,**capacities)
        self.assertEqual(result.errors.cpu().tolist(),[4]);self.assertEqual(result.state.restore_envs()[0].serialize(),env.serialize())
        empty=DeviceStateBatch.capture([],context=before.context);draw=sample_packed_chance(empty,dice_capacity=1,roll_capacity=1)
        result=effects.apply(empty,draw);self.assertTrue(result.committed.cpu().item());self.assertEqual(result.state.restore_envs(),[])


if __name__=="__main__":unittest.main()
