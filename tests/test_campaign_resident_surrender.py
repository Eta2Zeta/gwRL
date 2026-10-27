"""Original surrender/objective helpers versus complete raw resident State."""
from dataclasses import replace
import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.device_strings import pack_byte_requests,intern_bytes
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_surrender import ResidentSurrender
from studies.campaign.backends.resident_political_unit_removal import ResidentPoliticalUnitRemoval
from tests.test_campaign_device_state import rich_fixture
from tests.test_campaign_resident_political_unit_removal import removal_fixture
from tools.benchmark_campaign_resident_recruitment_chance import canonical_native,require_exact

EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def fixture(mutate=None):
    env=rich_fixture();doc=json.loads(env.serialize())
    if mutate:mutate(doc["state"])
    # The raw gold must retain both binary64 sentinels, not roundtrip through a
    # Python parse of the native spelling '-0' (which would become integer zero).
    doc["state"]["politics"]["pending"]["surrender_opaque"]={"zero":-0.0,"precise":1.0000000000000002,
        "unknown":[None,True,{"utf8":"蒙古\u0000"}]}
    env.restore(json.dumps(doc,ensure_ascii=False));return env


def project(name,owner="japan",kind="destroyer",**updates):
    value=dict(id=name,owner=owner,type=kind,site=None,queue_position=2,paid_ipp=3,remaining_payments=[7],flags={"unknown":-3})
    value.update(updates);return value


def ships(state,count=2):
    # The printed scenario already contains two Japanese naval queue entries;
    # make this fixture's exact die count independent of those setup entries.
    state["construction"].clear()
    for i in range(count):state["construction"][f"surrender_ship_{i:03d}"]=project(f"surrender_ship_{i:03d}")
    state["construction"]["surrender_ship_completed"]=project("surrender_ship_completed",queue_position=1,paid_ipp=0,remaining_payments=[],flags={"completed":1})
    state["construction"]["surrender_facility"]=project("surrender_facility",kind="airbase")
    state["construction"]["other_owner_project"]=project("other_owner_project",owner="ccp")


def existing_chance(state):
    state["chance"]={"id":"retained_request","purpose":"fixture","nation":"japan","continuation":"retained_pending",
        "dice":[{"sides":12,"modifier":0,"reroll_faces":[],"max_rerolls":0}]}
    state["politics"]["pending"]["retained_pending"]={"opaque":-0.0}


@unittest.skipUnless(EXACT,"Lossless MPS required")
class ResidentSurrenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs,nations=None,attackers=None):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        state=DeviceStateBatch.capture(envs,context=context)
        service=ResidentSurrender(context,ResidentPoliticalUnitRemoval(context),gwrl_cpp.campaign_recruitment_context(envs[0]))
        if nations is None:return state,service,None
        names=tuple(dict.fromkeys((*nations,*attackers)));tokens={};missing=[]
        for name in names:
            try:tokens[name]=int(context.prefix_lookup_ids((name,))[0])
            except IndexError:missing.append(name)
        if missing:
            data,lengths=pack_byte_requests([s.encode() for s in missing],device="mps")
            added=intern_bytes(state,data,lengths,string_capacity=state.string_offsets.numel()-1+len(missing),byte_capacity=state.string_bytes.numel()+data.numel())
            self.assertTrue(added.committed.item());state=added.state;tokens.update(zip(missing,added.ids.cpu().tolist(),strict=True))
        vectors=[torch.tensor([tokens[name] for name in values],dtype=torch.int64,device="mps") for values in (nations,attackers)]
        return state,service,vectors

    def raw(self,state,lane):
        length=state.lengths[lane].cpu().item();used,size=state.suffix_usage.cpu().tolist()
        rows=state.records[lane,:length].cpu().numpy().copy();data=state.string_bytes[:size].cpu().numpy().copy();offsets=state.string_offsets[:used+1].cpu().numpy().copy()
        return SimpleNamespace(context=state.context.native,record_array=lambda:rows,lane_offsets=lambda:np.array([0,length],dtype=np.int64),
            string_bytes=lambda:data,string_offsets=lambda:offsets)

    def oracle(self,before,result,envs,nations=None,attackers=None,selected=None):
        enabled=[True]*len(envs) if selected is None else selected
        rows=(gwrl_cpp.campaign_queue_political_objective_bonus_oracle(before.context.native,envs,enabled) if nations is None else
            gwrl_cpp.campaign_surrender_nation_oracle(before.context.native,envs,nations,attackers,enabled))
        self.assertEqual(result.errors.cpu().tolist(),[row["error"] for row in rows]);failed=any(row["error"] for row in rows)
        self.assertEqual(result.committed.item(),not failed)
        for lane,row in enumerate(rows):
            gold=gwrl_cpp.capture_device_states(before.context.native,[envs[lane]]) if failed else row["packed_state"]
            require_exact(self.raw(result.state,lane),canonical_native(gold))
        actual=result.state.records.cpu().numpy()
        self.assertTrue(np.any((actual[:,:,0]==4)&(actual[:,:,2]==0)&(actual[:,:,3]==0x80000000)))
        self.assertTrue(np.any((actual[:,:,0]==4)&(actual[:,:,2]==1)&(actual[:,:,3]==0x3ff00000)))
        return [json.loads(row["state_json"]) for row in rows]

    def capacities(self,state,service,**overrides):
        value=service.reserve(state,unit_capacity=512,project_capacity=256);value.update(overrides);return value

    def call(self,setup,*,selected=None,caps=None):
        state,service,vectors=setup;return service.surrender(state,*vectors,
            None if selected is None else torch.tensor(selected,dtype=torch.bool,device="mps"),**(self.capacities(state,service) if caps is None else caps))

    def rollback(self,before,result):
        self.assertFalse(result.committed.item());self.assertFalse(result.accepted.any().item())
        for name in ("records","string_bytes","string_offsets"):
            old,new=getattr(before,name),getattr(result.state,name);self.assertTrue(torch.equal(new[tuple(slice(0,n) for n in old.shape)],old),name)
        for name in ("lengths","sections","errors","suffix_usage"):self.assertTrue(torch.equal(getattr(before,name),getattr(result.state,name)),name)

    def test_complete_surrender_cargo_repairs_projects_dice_and_unknown_payloads(self):
        env,chain=removal_fixture(4);doc=json.loads(env.serialize());ships(doc["state"])
        doc["state"]["nations"]["japan"]["treasury"]=0
        doc["state"]["politics"]["pending"]["surrender_raw_bits"]={"zero":-0.0,"precise":1.0000000000000002}
        env.restore(json.dumps(doc));setup=self.setup([env],["japan"],["ccp"]);original=env.serialize()
        result=self.call(setup);actual=self.oracle(setup[0],result,[env],["japan"],["ccp"])[0]
        self.assertEqual(result.queued_ship_counts.item(),3);self.assertEqual(len(actual["chance"]["dice"]),3)
        self.assertEqual(actual["chance"]["nation"],"ccp");self.assertEqual(actual["chance"]["id"],"politics_surrender_queues_1")
        self.assertTrue(all(name not in actual["units"] for name in chain));self.assertEqual(actual["nations"]["japan"]["treasury"],0)
        self.assertIn("other_owner_project",actual["construction"]);self.assertNotIn("surrender_facility",actual["construction"])
        self.assertEqual(env.serialize(),original)

    def test_kmt_surrender_uses_any_ccp_possession_and_queue_bonus_emplace_collisions(self):
        def arrange(s):
            s["flags"]["politics_sequence"]=-3
            for t in s["territories"].values():
                if t["possessor"]=="ccp":t["possessor"]=None
            s["territories"]["land_jap_tokyo"]["possessor"]="ccp"
            s["construction"]["one_china_award_-2"]=project("one_china_award_-2",owner="japan",kind="infantry")
            s["nations"]["kmt"]["treasury"]=None
        first=fixture(arrange);second=fixture(lambda s:s["territories"].update({k:{**v,"possessor":None if v["possessor"]=="ccp" else v["possessor"]} for k,v in s["territories"].items()}))
        setup=self.setup([first,second],["kmt","kmt"],["japan","japan"]);result=self.call(setup)
        actual=self.oracle(setup[0],result,[first,second],["kmt","kmt"],["japan","japan"])
        self.assertEqual(actual[0]["flags"]["politics_sequence"],2);self.assertIsNone(actual[0]["nations"]["kmt"]["treasury"])
        self.assertEqual(actual[0]["construction"]["one_china_award_-2"]["owner"],"japan")
        self.assertEqual(sum(p["owner"]=="ccp" and p["flags"].get("national_objective_award",0) for p in actual[0]["construction"].values()),4)
        self.assertEqual(actual[1]["nations"]["ccp"]["game_flags"]["one_china_bonus_eligible_at_surrender"],0)

    def test_objective_bonus_independent_eligibility_and_awarded_laziness(self):
        def eligible(s):s["nations"]["ccp"]["game_flags"].update(one_china_bonus_eligible_at_surrender=-7)
        a=fixture(eligible);b=fixture(lambda s:(eligible(s),s["nations"]["ccp"]["game_flags"].update(one_china_bonus_awarded=-2)))
        c=fixture(lambda s:s["nations"]["ccp"]["game_flags"].update(one_china_bonus_eligible_at_surrender=0))
        state,service,_=self.setup([a,b,c]);caps=service.reserve(state,unit_capacity=0,project_capacity=0)
        for key in ("unit_capacity","project_capacity","dice_capacity"):caps.pop(key)
        result=service.queue_bonus(state,**caps);actual=self.oracle(state,result,[a,b,c])
        self.assertEqual(actual[0]["flags"]["politics_sequence"],5);self.assertEqual(actual[0]["nations"]["ccp"]["game_flags"]["one_china_bonus_awarded"],1)
        self.assertNotIn("politics_sequence",actual[1]["flags"]);self.assertNotIn("politics_sequence",actual[2]["flags"])

    def test_controller_handoffs_use_current_map_order_and_direct_optional_player(self):
        def arrange(s):
            minor=next(k for k in s["nations"] if k.startswith("warlord_"));template=copy.deepcopy(s["nations"][minor])
            template.update(controller_nation="japan",player="comintern",alliance="comintern",power_status="major")
            template["game_flags"].pop("incorporated",None);s["nations"]["dadao"]=template
            s["nations"][minor].update(controller_nation="japan",player=None,alliance="allies")
        env=fixture(arrange);setup=self.setup([env],["japan"],["kmt"]);result=self.call(setup)
        actual=self.oracle(setup[0],result,[env],["japan"],["kmt"])[0]
        minor=next(k for k in actual["nations"] if k.startswith("warlord_"))
        self.assertEqual(actual["nations"]["dadao"]["player"],"axis");self.assertEqual(actual["nations"][minor]["controller_nation"],"dadao")
        self.assertEqual(actual["nations"][minor]["alliance"],"allies")

    def test_optional_alliance_equality_and_incorporated_minor_untouched(self):
        def arrange(s):
            for id in ("japan","kmt"):s["nations"][id]["alliance"]=None
            s["nations"]["kmt"].update(player=None,power_status="major")
            for i,(id,n) in enumerate((p for p in s["nations"].items() if p[0].startswith("warlord_"))):
                n.update(controller_nation="japan",player="axis")
                if i==0:n["game_flags"]["incorporated"]=-1
        env=fixture(arrange);setup=self.setup([env],["japan"],["ccp"]);result=self.call(setup)
        actual=self.oracle(setup[0],result,[env],["japan"],["ccp"])[0]
        minors=[n for id,n in actual["nations"].items() if id.startswith("warlord_")]
        self.assertEqual(minors[0]["controller_nation"],"japan");self.assertEqual(minors[1]["controller_nation"],"kmt");self.assertIsNone(minors[1]["player"])

    def test_already_surrendered_returns_before_attacker_lookup_and_bonus(self):
        def arrange(s):
            s["politics"]["surrendered"]=["kmt"]
            s["nations"]["ccp"]["game_flags"].update(one_china_bonus_eligible_at_surrender=1)
        env=fixture(arrange);setup=self.setup([env],["kmt"],["not_a_nation"])
        result=self.call(setup);actual=self.oracle(setup[0],result,[env],["kmt"],["not_a_nation"])[0]
        self.assertNotIn("one_china_bonus_awarded",actual["nations"]["ccp"]["game_flags"])

    def test_native_errors_and_complete_selected_cohort_rollback(self):
        first=fixture();second=fixture();setup=self.setup([first,second],["japan","ccp"],["ccp","japan"])
        result=self.call(setup);self.oracle(setup[0],result,[first,second],["japan","ccp"],["ccp","japan"]);self.rollback(setup[0],result)
        unknown=self.setup([first],["not_a_nation"],["ccp"]);bad=self.call(unknown);self.oracle(unknown[0],bad,[first],["not_a_nation"],["ccp"])
        for mutate in (lambda s:(ships(s),existing_chance(s)),lambda s:(ships(s),s["flags"].update(politics_sequence=2**31-1)),
                       lambda s:s["nations"]["ccp"]["game_flags"].update(one_china_bonus_eligible_at_surrender=1)):
            env=fixture(mutate)
            if not json.loads(env.serialize())["state"]["construction"].get("surrender_ship_000"):
                doc=json.loads(env.serialize());doc["state"]["flags"]["politics_sequence"]=2**31-5
                doc["state"]["politics"]["pending"]["surrender_raw_bits"]={"zero":-0.0,"precise":1.0000000000000002};env.restore(json.dumps(doc))
            case=self.setup([env],["japan"],["ccp"]);out=self.call(case);self.oracle(case[0],out,[env],["japan"],["ccp"]);self.rollback(case[0],out)

    def test_existing_chance_without_naval_projects_and_unselected_invalid_ids(self):
        env=fixture(lambda s:(s["construction"].clear(),existing_chance(s)))
        setup=self.setup([env,env.clone()],["japan","ccp"],["missing_attacker","japan"])
        setup[2][0][1]=-999;setup[2][1][1]=-999
        result=self.call(setup,selected=[True,False]);actual=self.oracle(setup[0],result,[env,env.clone()],["japan","ccp"],["missing_attacker","japan"],selected=[True,False])
        self.assertTrue(result.committed.item())
        self.assertEqual(actual[0]["chance"]["id"],"retained_request")

    def test_allocation_failures_exact_retry_sizes_and_no_partial_publication(self):
        env=fixture(lambda s:ships(s,130));setup=self.setup([env],["japan"],["ccp"]);state,service,_=setup
        for overrides in (dict(unit_capacity=0),dict(project_capacity=0),dict(dice_capacity=0),dict(block_capacity=1),
                          dict(string_capacity=state.string_offsets.numel()-1),dict(byte_capacity=state.string_bytes.numel())):
            caps=self.capacities(state,service,**overrides);result=self.call(setup,caps=caps)
            self.assertEqual(result.errors.item(),5,str(overrides));self.rollback(state,result)
            if "project_capacity" in overrides:self.assertEqual(result.required_project_capacity.item(),131)
            if "dice_capacity" in overrides:self.assertEqual(result.required_dice_capacity.item(),131)
            if "unit_capacity" in overrides:self.assertGreater(result.required_unit_capacity.item(),0)
        good=self.call(setup);self.oracle(state,good,[env],["japan"],["ccp"])
        # Deleting Japan's large setup army can free more space than the dice
        # request uses. Keep that army under KMT ownership to force actual growth.
        def growing(s):
            ships(s,130)
            for unit in s["units"].values():
                if unit["owner"]=="japan":unit["owner"]="kmt"
        other=fixture(growing);case=self.setup([other],["japan"],["ccp"]);old,handler,_=case
        failed=self.call(case,caps=self.capacities(old,handler,state_capacity=old.records.shape[1]))
        self.assertEqual(failed.errors.item(),5);self.assertGreater(failed.required_state_capacity.item(),old.records.shape[1]);self.rollback(old,failed)
        self.oracle(old,self.call(case),[other],["japan"],["ccp"])

    def test_more_than128_queued_dice_and_no_hot_host_or_native_roundtrip(self):
        env=fixture(lambda s:ships(s,130));setup=self.setup([env],["japan"],["ccp"]);state,service,_=setup;caps=self.capacities(state,service)
        warm=self.call(setup,caps=caps);self.assertTrue(warm.committed.item())
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("host copy")),patch.object(torch.Tensor,"item",side_effect=AssertionError("host scalar")),\
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("host list")),patch.object(json,"loads",side_effect=AssertionError("JSON input")),\
             patch.object(json,"dumps",side_effect=AssertionError("JSON output")),patch.object(gwrl_cpp,"campaign_surrender_nation_oracle",side_effect=AssertionError("native fallback")):
            result=self.call(setup,caps=caps)
        self.oracle(state,result,[env],["japan"],["ccp"]);self.assertEqual(result.queued_ship_counts.item(),131)


if __name__=="__main__":unittest.main()
