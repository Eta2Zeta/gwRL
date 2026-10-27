"""Native recruitment predicates, complete ordered options and political IDs."""
from dataclasses import replace
from pathlib import Path
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
from studies.campaign.backends.resident_recruitment import ResidentRecruitment
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from tests.test_campaign_resident_relations import changed,set_turn

SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"
EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def controlled_fixture():
    env=gwrl_cpp.CampaignEnv(str(SCENARIO),41)
    doc=json.loads(env.serialize());minor=next(name for name in doc["state"]["nations"] if name.startswith("warlord_"))
    def arrange(state):
        set_turn(state,"japan");state["clock"].update(phase="place_units")
        state["nations"][minor].update(controller_nation="japan",player=None,power_status="minor")
    return changed(env,arrange),minor


@unittest.skipUnless(EXACT_MPS,"Lossless MPS indexing unavailable")
class ResidentRecruitmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=torch.get_num_threads();torch.set_num_threads(2)
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old)

    def setup(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        state=DeviceStateBatch.capture(envs,context=context)
        relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
        native=gwrl_cpp.campaign_recruitment_context(envs[0])
        return state,ResidentRecruitment(relations,native),native

    def requests(self,state,queries):
        values=state.context.prefix_lookup_ids([minor for lane,minor in queries])
        return torch.tensor([[lane,int(token)] for (lane,minor),token in zip(queries,values,strict=True)],dtype=torch.int64,device="mps").reshape(len(queries),2)

    def assert_queries(self,state,context,native,envs,queries):
        requests=self.requests(state,queries);result=context.query(state,requests)
        expected=gwrl_cpp.campaign_recruitment_oracle(native,envs,queries)
        data=result.metadata.cpu().tolist();errors=result.errors.cpu().tolist();zones=result.zones.cpu().tolist()
        from studies.campaign.backends.device_state_edits import _strings
        cpu=DeviceStateBatch.from_native(state.to_native(),device="cpu");names=_strings(cpu)
        for row,error,places,want in zip(data,errors,zones,expected,strict=True):
            self.assertEqual(error[:4],want["errors"][:4])
            if not error[0]:self.assertEqual(bool(row[0]),want["available"])
            if not error[1]:self.assertEqual(row[1],want["threshold"])
            self.assertEqual(bool(row[2]),want["quiet_placement"])
            if not error[2]:self.assertEqual([names[i].decode() for i in places[:row[3]]],want["zones"])
            if not error[3]:self.assertEqual(row[6],len(want["choices"]))
        return requests,result,expected

    def assert_choices(self,envs,queries,*,capacity=128):
        state,context,native=self.setup(envs);original=[env.serialize() for env in envs];before=state.records.clone()
        requests,result,expected=self.assert_queries(state,context,native,envs,queries)
        menu=context.choices(state,requests,capacity=capacity,**context.reserve(state,capacity=capacity))
        self.assertEqual(menu.batch_error.cpu().tolist(),[0])
        self.assertEqual(context.inspect(menu),tuple(action.encode() for item in expected for action in item["choices"]))
        self.assertTrue(torch.equal(state.records,before));self.assertEqual([env.serialize() for env in envs],original)
        self.assertEqual([env.serialize() for env in menu.arena.restore_envs()],original)
        return state,context,menu,expected

    def test_ccp_controlled_minors_and_direct_mongolia_match_every_ordered_choice(self):
        controlled,minor=controlled_fixture()
        ccp=changed(controlled,lambda state:set_turn(state,"ccp"))
        mongolia=changed(controlled,lambda state:set_turn(state,"mongolia"))
        self.assert_choices([controlled,ccp,mongolia],[(0,minor),(1,"ccp"),(2,"mongolia")],capacity=256)

    def test_recruitment_has_no_influence_garrison_requirement(self):
        original,minor=controlled_fixture()
        def empty_units(state):state["units"]={};state["repairs"]={}
        without=changed(original,empty_units)
        _,_,menu,expected=self.assert_choices([original,without],[(0,minor),(1,minor)])
        self.assertEqual(expected[0]["choices"],expected[1]["choices"])
        self.assertTrue(expected[1]["available"])

    def test_attempt_minor_control_surrender_incorporation_and_dadao_special_cases(self):
        original,minor=controlled_fixture()
        envs=[original,
            changed(original,lambda s:s["nations"][minor]["turn_flags"].update(recruitment_attempted=-1)),
            changed(original,lambda s:s["nations"][minor].update(power_status="major")),
            changed(original,lambda s:s["nations"][minor]["game_flags"].update(incorporated=1)),
            changed(original,lambda s:s["politics"]["surrendered"].append(minor)),
            changed(original,lambda s:s["nations"][minor].update(controller_nation=None,player="axis"))]
        state,context,native=self.setup(envs)
        _,result,_=self.assert_queries(state,context,native,envs,[(i,minor) for i in range(len(envs))])
        self.assertEqual(result.metadata[:,0].cpu().tolist(),[1,0,0,0,0,0])
        # Dadao exists as a separate minor controlled directly by the Axis agent
        # after Japan's surrender; a shared player alone is insufficient.
        def dadao(state):
            state["nations"]["dadao"]={"controller_nation":None,"player":"axis","alliance":"axis","power_status":"minor",
                "treasury":None,"income_components":{},"income_known":True,"technology_stages":{},"at_war_with":[],"allies":[],
                "turn_flags":{},"game_flags":{"direct_axis_control_after_japan_surrender":1}}
            state["politics"]["surrendered"].append("japan")
        first=changed(original,dadao);second=changed(first,lambda s:s["nations"]["dadao"]["game_flags"].clear())
        state,context,native=self.setup([first,second]);_,result,_=self.assert_queries(state,context,native,[first,second],[(0,"dadao"),(1,"dadao")])
        self.assertEqual(result.metadata[:,0].cpu().tolist(),[1,0])

    def test_offshore_threshold_and_start_snapshot_reacquisition_gates_are_distinct(self):
        original,minor=controlled_fixture();native=gwrl_cpp.campaign_recruitment_context(original)
        offshore=next(zone for zone in native.offshore_ids if zone in json.loads(original.serialize())["state"]["territories"])
        def add_offshore(state):
            state["territories"][offshore]["possessor"]=minor;state["turn_start"]["possessions"][offshore]=minor
        first=changed(original,add_offshore)
        owned=next(zone for zone,t in json.loads(first.serialize())["state"]["territories"].items() if t["possessor"]==minor and zone!=offshore)
        absent_start=changed(first,lambda state:state["turn_start"]["possessions"].__setitem__(owned,None))
        serial=int(json.loads(first.serialize())["state"]["clock"]["player_turn_serial"])
        reacquired=changed(first,lambda state:state["territories"][owned]["flags"].update(last_possession_change_turn=serial))
        wide=changed(reacquired,lambda state:state["clock"].update(player_turn_serial=str(2**63+11)))
        state,context,native=self.setup([original,first,absent_start,reacquired,wide])
        _,result,expected=self.assert_queries(state,context,native,[original,first,absent_start,reacquired,wide],[(i,minor) for i in range(5)])
        self.assertEqual(result.metadata[0,1].item(),result.metadata[1,1].item())
        self.assertIn(offshore,expected[1]["zones"])
        self.assertNotIn(owned,expected[2]["zones"]);self.assertNotIn(owned,expected[3]["zones"])
        self.assertIn(owned,expected[4]["zones"])

    def test_unordered_militia_pairs_all_ships_and_damaged_facilities_preserve_native_order(self):
        original,minor=controlled_fixture()
        owner_zone=next(zone for zone,t in json.loads(original.serialize())["state"]["territories"].items() if t["possessor"]==minor)
        def work(state):
            projects={
                "aaa_eligible_ship":("battleship",2,[3],7),"bbb_queue_one":("battleship",1,[3],8),
                "ccc_complete":("battleship",3,[],9),"ddd_land_piece":("infantry",2,[3],10),
                "zzz_eligible_ship":("battleship",3,[3,4],11)}
            for name,(type,queue,payments,paid) in projects.items():
                state["construction"][name]={"id":name,"owner":minor,"type":type,"site":None,"queue_position":queue,
                    "paid_ipp":paid,"remaining_payments":payments,"flags":{}}
            for name,damage in (("aaa_recruit_facility",1),("bbb_undamaged",0),("zzz_recruit_facility",1)):
                state["facilities"][name]={"id":name,"type":"airbase","zone":owner_zone,"damage":damage,"flags":{}}
        env=changed(original,work);_,_,menu,expected=self.assert_choices([env],[(0,minor)],capacity=256)
        options=[json.loads(value) for value in expected[0]["choices"]]
        zones=expected[0]["zones"]
        pairs=[value["parameters"]["zones"] for value in options if value["kind"]=="recruitment_place_militia"]
        self.assertEqual(pairs,[[zones[first],zones[second]] for first in range(len(zones)) for second in range(first,len(zones))])
        self.assertEqual([v["parameters"]["project"] for v in options if v["kind"]=="recruitment_advance_ship"],
                         ["aaa_eligible_ship","zzz_eligible_ship"])
        self.assertEqual([v["parameters"]["facility"] for v in options if v["kind"]=="recruitment_repair_facility"],
                         ["aaa_recruit_facility","zzz_recruit_facility"])
        self.assertEqual(menu.arena.restore_envs()[0].serialize(),env.serialize())

    def test_legal_rolls_quiet_placement_and_attempt_gates_match_native(self):
        original,minor=controlled_fixture()
        envs=[original,changed(original,lambda state:state["clock"].update(phase="production")),
            changed(original,lambda state:state["clock"].update(income_collected=True)),
            changed(original,lambda state:state["nations"][minor]["turn_flags"].update(recruitment_attempted=1))]
        state,context,native=self.setup(envs)
        menu=context.rolls(state,**context.reserve(state,capacity=len(envs)*len(context.relations_context.nation_ids)))
        expected=[]
        for lane,env in enumerate(envs):
            queries=[(lane,name) for name in context.relations_context.nation_ids]
            expected.extend(action.encode() for item in gwrl_cpp.campaign_recruitment_oracle(native,envs,queries) for action in item["rolls"])
        self.assertEqual(context.inspect(menu),tuple(expected))
        self.assertTrue(any(json.loads(action)["parameters"]["beneficiary"]==minor for action in context.inspect(menu)))

    def test_capacity_retry_namespace_failure_and_repeated_queries_do_not_grow_padding(self):
        env,minor=controlled_fixture();state,context,native=self.setup([env]);requests=self.requests(state,[(0,minor)])
        count=len(gwrl_cpp.campaign_recruitment_oracle(native,[env],[(0,minor)])[0]["choices"])
        short=context.choices(state,requests,capacity=max(0,count-1))
        self.assertEqual(short.batch_error.cpu().tolist(),[5]);self.assertEqual(short.count.cpu().tolist(),[0])
        self.assertEqual(short.required_count.cpu().tolist(),[count])
        failed=context.choices(state,requests,capacity=count)
        self.assertTrue(any(failed.errors.cpu().tolist()));self.assertTrue(torch.equal(failed.arena.suffix_usage,state.suffix_usage))
        result=context.choices(state,requests,capacity=count,**context.reserve(state,capacity=count))
        expected=context.inspect(result)
        repeated=context.choices(result.arena,requests,capacity=count)
        self.assertEqual(context.inspect(repeated),expected)
        self.assertEqual(result.arena.string_offsets.shape,repeated.arena.string_offsets.shape)
        self.assertEqual(result.arena.string_bytes.shape,repeated.arena.string_bytes.shape)

    def test_hot_query_encoding_and_complete_actions_have_no_host_or_native_fallback(self):
        env,minor=controlled_fixture();state,context,native=self.setup([env]);requests=self.requests(state,[(0,minor)])
        relations=context.relations_context.compute(state);reserve=context.reserve(state,capacity=128)
        context.choices(state,requests,relations=relations,capacity=128,**reserve)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host values")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(json,"loads",side_effect=AssertionError("JSON hot path")), \
             patch.object(gwrl_cpp,"campaign_recruitment_oracle",side_effect=AssertionError("CPU fallback")):
            menu=context.choices(state,requests,relations=relations,capacity=128,**reserve)
        self.assertEqual(menu.batch_error.cpu().tolist(),[0]);self.assertFalse(any(menu.errors.cpu().tolist()))
        with self.assertRaises(ValueError):context.query(state.snapshot(),requests,relations=relations)
        empty=DeviceStateBatch.capture([],context=state.context)
        menu=context.rolls(empty);self.assertEqual(context.inspect(menu),())

    def test_long_escaped_project_identity_reports_complete_parameter_capacity_and_retries(self):
        original,minor=controlled_fixture()
        identity='long_"\\\x00é_'+('x'*700)
        def add(state):
            state["construction"][identity]={"id":identity,"owner":minor,"type":"battleship","site":None,
                "queue_position":2,"paid_ipp":7,"remaining_payments":[3],"flags":{}}
        env=changed(original,add);state,context,native=self.setup([env]);requests=self.requests(state,[(0,minor)])
        expected=gwrl_cpp.campaign_recruitment_oracle(native,[env],[(0,minor)])[0]["choices"]
        capacity=len(expected);before=state.records.clone();reserve=context.reserve(state,capacity=capacity)
        failed=context.choices(state,requests,capacity=capacity,**reserve)
        self.assertEqual(failed.batch_error.cpu().tolist(),[0])
        self.assertTrue(any(failed.errors[:capacity].cpu().tolist()))
        needed=int(failed.parameter_json.required_bytes[:capacity].max().cpu().item())
        self.assertGreater(needed,512)
        self.assertTrue(torch.equal(failed.arena.suffix_usage,state.suffix_usage))
        with self.assertRaises(ValueError):context.inspect(failed)
        result=context.choices(state,requests,capacity=capacity,parameter_byte_capacity=needed,**reserve)
        self.assertEqual(context.inspect(result),tuple(action.encode() for action in expected))
        self.assertTrue(torch.equal(state.records,before))
        self.assertEqual(result.arena.restore_envs()[0].serialize(),env.serialize())

    def test_default_menu_allocation_does_not_scale_with_state_history_capacity(self):
        env,minor=controlled_fixture();state,context,native=self.setup([env]);requests=self.requests(state,[(0,minor)])
        count=len(gwrl_cpp.campaign_recruitment_oracle(native,[env],[(0,minor)])[0]["choices"])
        first=context.choices(state,requests,**context.reserve(state,capacity=count))
        # A larger complete-state arena may reserve space for later history.
        # This must not multiply the independent action-menu allocation.
        padded=replace(state,records=torch.cat((state.records,torch.zeros((1,4000,5),dtype=torch.int64,device="mps")),1))
        second=context.choices(padded,requests,**context.reserve(padded,capacity=count))
        self.assertEqual(first.actions.shape,second.actions.shape)
        self.assertEqual(first.parameter_json.data.shape,second.parameter_json.data.shape)
        self.assertEqual(context.inspect(first),context.inspect(second))
        self.assertEqual(first.required_count.cpu().tolist(),[count]);self.assertEqual(second.required_count.cpu().tolist(),[count])

    def test_unselected_raw_choice_does_not_evaluate_player_or_produce_lazy_errors(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),53)
        minor=next(name for name in json.loads(env.serialize())["state"]["nations"] if name.startswith("warlord_"))
        state,context,native=self.setup([env]);requests=self.requests(state,[(0,"ccp"),(0,minor)])
        raw=context.query(state,requests)
        self.assertEqual(raw.errors[1,3].cpu().item(),2)
        selected=torch.tensor([True,False],dtype=torch.bool,device="mps")
        result=context.choices(state,requests,selected=selected,capacity=128,**context.reserve(state,capacity=128))
        expected=gwrl_cpp.campaign_recruitment_oracle(native,[env],[(0,"ccp")])[0]["choices"]
        self.assertEqual(context.inspect(result),tuple(action.encode() for action in expected))
        self.assertEqual(result.queries.errors[1].cpu().tolist(),[0]*5)
        self.assertEqual(result.queries.metadata[1,7].cpu().item(),0)


if __name__=="__main__":unittest.main()
