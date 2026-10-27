"""Original native recruitment start versus cached-menu resident effects."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext,SECTION_NAMES
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
from studies.campaign.backends.resident_recruitment import ResidentRecruitment
from studies.campaign.backends.resident_recruitment_start import ResidentRecruitmentStart
from tests.test_campaign_resident_recruitment import controlled_fixture,SCENARIO
from tests.test_campaign_resident_relations import changed,set_turn

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def start_fixture(*,training=False,sequence=None,active="actual"):
    if training:
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),41,training_actions=True)
        doc=json.loads(env.serialize());minor=next(name for name in doc["state"]["nations"] if name.startswith("warlord_"))
        set_turn(doc["state"],"japan");doc["state"]["clock"]["phase"]="place_units"
        doc["state"]["nations"][minor].update(controller_nation="japan",player=None,power_status="minor")
        env.restore(json.dumps(doc))
    else:env,minor=controlled_fixture()
    doc=json.loads(env.serialize());state=doc["state"]
    doc["random"].update(active=active,actual=str(2**64-1),search=str(2**63+1),training=str(2**32+3),test_tape=[12,1],tape_position="0")
    state["politics"]["pending"]["unrelated_start_fixture"]={"exact":1.0000000000000002,"negative_zero":-0.0,
        "opaque":[None,True,"蒙古\u0000",{"nested":[1,2]}]}
    if sequence is not None:state["flags"]["politics_sequence"]=sequence
    if training:state["action_interface"]={}
    env.restore(json.dumps(doc,ensure_ascii=False));return env,minor


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU execution unavailable")
class ResidentRecruitmentStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        before=DeviceStateBatch.capture(envs,context=context)
        relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
        native=gwrl_cpp.campaign_recruitment_context(envs[0]);query=ResidentRecruitment(relations,native)
        P=len(envs)*len(relations.nation_ids)
        menu=query.rolls(before,capacity=P,**query.reserve(before,capacity=P))
        return before,ResidentRecruitmentStart(query),native,menu

    def selections(self,start,menu,beneficiaries):
        actions=start.recruitment.inspect(menu);selections=[]
        requests=menu.queries.requests.cpu().tolist();metadata=menu.queries.metadata.cpu().tolist();first=0;lanes=[]
        for request,data in zip(requests,metadata,strict=True):lanes.extend([request[0]]*data[7])
        for lane,minor in enumerate(beneficiaries):
            selections.append(next(row for row,action in enumerate(actions) if lanes[row]==lane and json.loads(action)["parameters"]["beneficiary"]==minor))
        return torch.tensor(selections,dtype=torch.int64,device="mps"),[actions[i].decode() for i in selections]

    def assert_native(self,before,result,envs,native,actions):
        wanted=gwrl_cpp.campaign_recruitment_start_oracle(native,envs,actions)
        self.assertEqual(result.errors.cpu().tolist(),[v["error"] for v in wanted])
        actual=[json.loads(env.serialize()) for env in result.state.restore_envs()]
        self.assertEqual([doc["state"] for doc in actual],[json.loads(v["state_json"]) for v in wanted])
        self.assertEqual([doc["random"] for doc in actual],[json.loads(env.serialize())["random"] for env in envs])
        old,new=before.records.cpu(),result.state.records.cpu();a,b=before.sections.cpu(),result.state.sections.cpu()
        for column,name in enumerate(SECTION_NAMES):
            if name in {"state","state.nations","state.politics","state.chance","state.flags"}:continue
            for lane in range(len(envs)):
                left,right=int(a[lane,column]),int(b[lane,column])
                x,y=old[lane,left:int(old[lane,left,4])].clone(),new[lane,right:int(new[lane,right,4])].clone()
                x[:,4]-=left;y[:,4]-=right;self.assertTrue(torch.equal(x,y),name)
        return actual

    def test_controlled_minor_ccp_and_mongolia_use_exact_cached_actions(self):
        env,minor=start_fixture();ccp=changed(env,lambda s:set_turn(s,"ccp"));mongolia=changed(env,lambda s:set_turn(s,"mongolia"))
        envs=[env,ccp,mongolia];before,start,native,menu=self.setup(envs)
        selections,actions=self.selections(start,menu,[minor,"ccp","mongolia"])
        originals=[env.serialize() for env in envs]
        result=start.apply(before,menu,selections,**start.reserve(before,menu))
        self.assertTrue(result.committed.cpu().item());actual=self.assert_native(before,result,envs,native,actions)
        self.assertEqual([env.serialize() for env in envs],originals)
        for doc,minor in zip(actual,[minor,"ccp","mongolia"],strict=True):
            state=doc["state"];self.assertEqual(state["nations"][minor]["turn_flags"]["recruitment_attempted"],1)
            request=state["chance"];self.assertEqual(request["nation"],minor);self.assertEqual(request["purpose"],"recruitment_roll")
            self.assertEqual(request["dice"],[{"sides":12,"modifier":0,"reroll_faces":[],"max_rerolls":0}])

    def test_base_and_training_profiles_leave_all_outer_hooks_and_cash_untouched(self):
        for training in (False,True):
            with self.subTest(training=training):
                env,minor=start_fixture(training=training);before,start,native,menu=self.setup([env])
                selections,actions=self.selections(start,menu,[minor]);old=json.loads(env.serialize())["state"]
                result=start.apply(before,menu,selections,**start.reserve(before,menu))
                actual=self.assert_native(before,result,[env],native,actions)[0]["state"]
                for key in ("clock","history","action_interface","units","construction","facilities","decisions"):
                    self.assertEqual(actual.get(key),old.get(key),key)
                for nation in old["nations"]:
                    for key in ("treasury","income_components","income_known"):
                        self.assertEqual(actual["nations"][nation][key],old["nations"][nation][key])

    def test_signed_counter_boundaries_and_exact_positive_threshold_numberbits(self):
        values=[None,-2,-1,-2**31,2**31-2]
        pairs=[start_fixture(sequence=value) for value in values];envs=[p[0] for p in pairs]
        before,start,native,menu=self.setup(envs);selections,actions=self.selections(start,menu,[p[1] for p in pairs])
        result=start.apply(before,menu,selections,**start.reserve(before,menu));actual=self.assert_native(before,result,envs,native,actions)
        for doc,old in zip(actual,values,strict=True):
            new=(0 if old is None else old)+1;state=doc["state"]
            self.assertEqual(state["flags"]["politics_sequence"],new)
            self.assertEqual(state["chance"]["id"],"recruitment_roll_"+str(new))
            saved=state["politics"]["pending"][state["chance"]["continuation"]]
            self.assertIsInstance(saved["threshold"],(int,float));self.assertGreater(saved["threshold"],0)

    def test_overflow_rolls_back_attempt_counter_pending_chance_and_namespace(self):
        env,minor=start_fixture(sequence=2**31-1);before,start,native,menu=self.setup([env]);selections,actions=self.selections(start,menu,[minor])
        result=start.apply(before,menu,selections,**start.reserve(before,menu))
        self.assertEqual(result.errors.cpu().tolist(),[2]);self.assertFalse(result.committed.cpu().item())
        self.assert_native(before,result,[env],native,actions)
        self.assertTrue(torch.equal(result.state.suffix_usage,before.suffix_usage))

    def test_selected_cohort_is_atomic_and_unselected_invalid_selection_is_lazy(self):
        good,minor=start_fixture();bad,_=start_fixture(sequence=2**31-1);before,start,native,menu=self.setup([good,bad])
        selections,actions=self.selections(start,menu,[minor,minor]);caps=start.reserve(before,menu)
        failed=start.apply(before,menu,selections,**caps)
        self.assertEqual(failed.errors.cpu().tolist(),[0,2]);self.assertEqual(failed.accepted.cpu().tolist(),[False,False])
        self.assertEqual([env.serialize() for env in failed.state.restore_envs()],[good.serialize(),bad.serialize()])
        partial=start.apply(before,menu,torch.tensor([selections[0].cpu().item(),-999],device="mps"),
            torch.tensor([True,False],device="mps"),**caps)
        self.assertEqual(partial.errors.cpu().tolist(),[0,0]);self.assertEqual(partial.accepted.cpu().tolist(),[True,False])
        self.assertEqual(partial.state.restore_envs()[1].serialize(),bad.serialize())
        idle=start.apply(before,menu,selections,torch.zeros(2,dtype=torch.bool,device="mps"),**caps)
        self.assertTrue(idle.committed.cpu().item());self.assertTrue(torch.equal(idle.state.suffix_usage,before.suffix_usage))
        self.assertEqual([env.serialize() for env in idle.state.restore_envs()],[good.serialize(),bad.serialize()])

    def test_wrong_lane_out_of_range_and_full_action_tampering_are_rejected(self):
        env,minor=start_fixture();before,start,native,menu=self.setup([env,env.clone()]);selections,actions=self.selections(start,menu,[minor,minor])
        swapped=selections.flip(0).contiguous();result=start.apply(before,menu,swapped,**start.reserve(before,menu))
        self.assertEqual(result.errors.cpu().tolist(),[2,2])
        short=start.apply(before,menu,torch.full((2,),-1,dtype=torch.int64,device="mps"),**start.reserve(before,menu))
        self.assertEqual(short.errors.cpu().tolist(),[2,2])
        for field,token in ((1,"beneficiary"),(2,"recruitment_choice"),(3,"japan"),(4,"ccp"),(8,"ccp")):
            with self.subTest(field=field):
                rows=menu.actions.clone();row=selections[0].cpu().item();rows[row,field,1]=int(before.context.prefix_lookup_ids((token,))[0])
                altered=replace(menu,actions=rows);result=start.apply(before,altered,selections,**start.reserve(before,altered))
                self.assertEqual(result.errors[0].cpu().item(),2);self.assertFalse(result.committed.cpu().item())
                self.assertEqual([v.serialize() for v in result.state.restore_envs()],[env.serialize(),env.serialize()])

    def test_all_allocation_errors_return_sizes_and_retry_without_partial_state(self):
        env,minor=start_fixture();before,start,native,menu=self.setup([env]);selections,actions=self.selections(start,menu,[minor]);caps=start.reserve(before,menu)
        cases=[dict(caps,state_capacity=before.records.shape[1]),dict(caps,block_capacity=1)]
        for capacities in cases:
            with self.subTest(capacities=capacities):
                result=start.apply(before,menu,selections,**capacities)
                self.assertEqual(result.errors.cpu().tolist(),[5]);self.assertFalse(result.committed.cpu().item())
                self.assertEqual(result.state.restore_envs()[0].serialize(),env.serialize())
                self.assertTrue(torch.equal(result.state.suffix_usage,before.suffix_usage))
        used,size=menu.arena.suffix_usage.cpu().tolist()
        tight=replace(menu,arena=replace(menu.arena,string_offsets=menu.arena.string_offsets[:used+1].contiguous(),
            string_bytes=menu.arena.string_bytes[:size].contiguous()))
        failed=start.apply(before,tight,selections,**dict(start.reserve(before,tight),string_capacity=used,byte_capacity=size))
        self.assertEqual(failed.errors.cpu().tolist(),[5]);self.assertFalse(failed.committed.cpu().item())
        self.assertGreater(failed.required_string_usage.cpu().tolist()[0],used)
        self.assertEqual(failed.state.restore_envs()[0].serialize(),env.serialize())
        self.assertTrue(torch.equal(failed.state.suffix_usage,before.suffix_usage))
        result=start.apply(before,menu,selections,**caps)
        self.assertTrue(result.committed.cpu().item());self.assert_native(before,result,[env],native,actions)

    def test_source_binding_layout_and_empty_lane_batch(self):
        env,minor=start_fixture();before,start,native,menu=self.setup([env]);selections,actions=self.selections(start,menu,[minor])
        with self.assertRaises(ValueError):start.apply(before.snapshot(),menu,selections)
        with self.assertRaises(ValueError):start.apply(before,replace(menu,arena=before.snapshot()),selections)
        with self.assertRaises(ValueError):start.apply(before,menu,selections.to("cpu"))
        with self.assertRaises(ValueError):start.apply(before,replace(menu,queries=replace(menu.queries,rolls=False)),selections)
        empty=DeviceStateBatch.capture([],context=before.context)
        empty_menu=start.recruitment.rolls(empty,capacity=0)
        result=start.apply(empty,empty_menu,torch.zeros(0,dtype=torch.int64,device="mps"))
        self.assertTrue(result.committed.cpu().item());self.assertEqual(result.state.restore_envs(),[])

    def test_no_hot_host_reads_json_native_or_legal_menu_regeneration(self):
        env,minor=start_fixture();before,start,native,menu=self.setup([env]);selections,actions=self.selections(start,menu,[minor]);caps=start.reserve(before,menu)
        start.apply(before,menu,selections,**caps)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host values")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(json,"loads",side_effect=AssertionError("JSON hot path")), \
             patch.object(gwrl_cpp,"campaign_recruitment_start_oracle",side_effect=AssertionError("CPU fallback")), \
             patch.object(start.recruitment,"rolls",side_effect=AssertionError("Legal menu regeneration")), \
             patch.object(start.recruitment,"choices",side_effect=AssertionError("Choice regeneration")), \
             patch.object(start.recruitment.relations_context,"compute",side_effect=AssertionError("Relation regeneration")):
            result=start.apply(before,menu,selections,**caps)
        self.assertTrue(result.committed.cpu().item());self.assert_native(before,result,[env],native,actions)


if __name__=="__main__":unittest.main()
