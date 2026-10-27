"""Original mixed-stack queuing, lazy border reads and exact State/RNG bits."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_chinese_truce import ResidentChineseTruce
from tests.test_campaign_device_state import rich_fixture
from tests.test_campaign_resident_relations import set_turn
from tools.benchmark_campaign_resident_recruitment_chance import canonical_native,require_exact

EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()
HOPEH="land_china_hopeh";BEIPING="land_china_beiping";SHANTUNG="land_china_shantung"


def fixture(actor="ccp",phase="combat",*,possessor="kmt",serial=None,mutate=None):
    env=rich_fixture();doc=json.loads(env.serialize());s=doc["state"]
    template=copy.deepcopy(next(iter(s["units"].values())));s["units"]={}
    set_turn(s,actor);s["clock"].update(phase=phase,income_collected=False)
    if serial is not None:s["clock"]["player_turn_serial"]=str(serial)
    s["politics"].update(chinese_truce=True,truce_permanently_ended=False,truce_offer_pending=True)
    s["territories"][HOPEH]["possessor"]=possessor
    def add(id,owner,zone=HOPEH,kind="infantry",**overrides):
        unit=copy.deepcopy(template);unit.update(id=id,type=kind,owner=owner,zone=zone,turn_origin=zone,route=[],
            movement_allowance=6,movement_remaining=6,damage=0,commitments=[],carried_by=None,cargo=[],turn_flags={"opaque":-7},game_flags={"opaque":4})
        unit.update(overrides);s["units"][id]=unit;return unit
    add("c","ccp");add("k","kmt")
    if mutate:mutate(s,add)
    s["politics"]["pending"]["truce_opaque"]={"negative_zero":-0.0,"precise":1.0000000000000002,"utf8":"蒙古\u0000","nested":[None,True,{"n":-123.5}]}
    env.restore(json.dumps(doc,ensure_ascii=False));return env


@unittest.skipUnless(EXACT,"Lossless MPS required")
class ResidentChineseTruceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs,breakers,evolution):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps");state=DeviceStateBatch.capture(envs,context=context)
        service=ResidentChineseTruce(context,gwrl_cpp.campaign_movement_context(envs[0]))
        ids=torch.tensor(context.prefix_lookup_ids(breakers),dtype=torch.int64,device="mps")
        return state,service,ids,torch.tensor(evolution,dtype=torch.bool,device="mps")

    def raw(self,state,lane):
        length=state.lengths[lane].cpu().item();used,size=state.suffix_usage.cpu().tolist()
        rows=state.records[lane,:length].cpu().numpy().copy();data=state.string_bytes[:size].cpu().numpy().copy();offsets=state.string_offsets[:used+1].cpu().numpy().copy()
        return SimpleNamespace(context=state.context.native,record_array=lambda:rows,lane_offsets=lambda:np.array([0,length],dtype=np.int64),
            string_bytes=lambda:data,string_offsets=lambda:offsets)

    def oracle(self,before,result,envs,breakers,evolution,selected=None):
        enabled=[True]*len(envs) if selected is None else selected
        rows=gwrl_cpp.campaign_terminate_chinese_truce_oracle(before.context.native,envs,breakers,evolution,enabled)
        self.assertEqual(result.errors.cpu().tolist(),[row["error"] for row in rows]);failed=any(row["error"] for row in rows)
        self.assertEqual(result.committed.item(),not failed)
        for lane,row in enumerate(rows):
            gold=gwrl_cpp.capture_device_states(before.context.native,[envs[lane]]) if failed else row["packed_state"]
            require_exact(self.raw(result.state,lane),canonical_native(gold))
        numbers=result.state.records.cpu().numpy()
        self.assertTrue(np.any((numbers[:,:,0]==4)&(numbers[:,:,2]==0)&(numbers[:,:,3]==0x80000000)))
        self.assertTrue(np.any((numbers[:,:,0]==4)&(numbers[:,:,2]==1)&(numbers[:,:,3]==0x3ff00000)))
        return [json.loads(row["state_json"]) for row in rows],rows

    def call(self,setup,*,selected=None,caps=None):
        state,service,breakers,evolution=setup
        return service.terminate(state,breakers,evolution,None if selected is None else torch.tensor(selected,dtype=torch.bool,device="mps"),
            **(service.reserve(state,battle_capacity=8) if caps is None else caps))

    def queued(self,state):return [b for b in state["battles"].values() if b["flags"].get("chinese_truce_termination")]

    def rollback(self,state,result):
        self.assertFalse(result.committed.item());self.assertFalse(result.accepted.any().item())
        for name in ("records","string_bytes","string_offsets"):
            old,new=getattr(state,name),getattr(result.state,name)
            self.assertTrue(torch.equal(new[tuple(slice(0,n) for n in old.shape)],old),name)
        for name in ("lengths","sections","errors","suffix_usage"):self.assertTrue(torch.equal(getattr(state,name),getattr(result.state,name)),name)

    def test_voluntary_roles_follow_active_breaker_for_both_possessors(self):
        envs=[fixture(actor,possessor=owner) for actor in ("ccp","kmt") for owner in ("ccp","kmt")]
        breakers=["ccp","ccp","kmt","kmt"];automatic=[False]*4;setup=self.setup(envs,breakers,automatic)
        original=[env.serialize() for env in envs];result=self.call(setup);actual,_=self.oracle(setup[0],result,envs,breakers,automatic)
        for state,actor in zip(actual,breakers,strict=True):
            battle,=self.queued(state);self.assertEqual(battle["attacker"],actor);self.assertNotEqual(battle["defender"],actor)
            self.assertEqual(battle["data"]["origins"],{});self.assertNotIn("retreat_mode",battle["data"])
        self.assertEqual([env.serialize() for env in envs],original)

    def test_automatic_roles_all_phases_chinese_active_and_third_party_owner_defends(self):
        cases=[(actor,owner,breaker,phase) for actor in ("ccp","kmt","japan","mongolia") for owner in ("ccp","kmt")
               for breaker,phase in (("ccp","production"),("kmt","place_units"))]
        envs=[fixture(actor,phase,possessor=owner) for actor,owner,_,phase in cases];breakers=[c[2] for c in cases];automatic=[True]*len(cases)
        setup=self.setup(envs,breakers,automatic);result=self.call(setup);actual,_=self.oracle(setup[0],result,envs,breakers,automatic)
        for state,(actor,owner,_,phase) in zip(actual,cases,strict=True):
            battle,=self.queued(state);attacker=actor if actor in ("ccp","kmt") else ("kmt" if owner=="ccp" else "ccp")
            self.assertEqual(battle["attacker"],attacker);self.assertEqual(state["clock"]["phase"],phase)
            self.assertEqual(battle["data"]["origins"],{});self.assertFalse(state["politics"]["truce_offer_pending"])

    def test_land_membership_aircraft_carried_units_and_third_nations(self):
        native=gwrl_cpp.campaign_movement_context(rich_fixture())
        sea=next(zone for zone,row in zip(native.zones,np.asarray(native.node_array()),strict=True) if not row[0])
        def arrange(s,add):
            add("plane","ccp",kind="fighter");add("naval_on_land","ccp",kind="destroyer")
            add("cargo_ccp","ccp",carried_by="carrier_japan");add("carrier_japan","japan",cargo=["cargo_ccp"])
            add("third_party","japan")
            add("sea_ccp","ccp",sea);add("sea_kmt","kmt",sea)
        env=fixture(mutate=arrange);setup=self.setup([env],["ccp"],[False]);result=self.call(setup)
        actual,_=self.oracle(setup[0],result,[env],["ccp"],[False]);battle,=self.queued(actual[0])
        self.assertEqual(battle["attackers"],["c","naval_on_land","plane"]);self.assertEqual(battle["defenders"],["k"])
        self.assertIn("cargo_ccp",actual[0]["units"])
        # No Chinese uncarried pair remains: the carried CCP Unit must not count.
        other=fixture(mutate=lambda s,add:(s["units"].pop("c"),add("carried","ccp",carried_by="carrier"),add("carrier","japan",cargo=["carried"])))
        case=self.setup([other],["kmt"],[True]);out=self.call(case);states,_=self.oracle(case[0],out,[other],["kmt"],[True]);self.assertEqual(self.queued(states[0]),[])

    def test_genuine_origin_rules_and_duplicate_land_entry_origins(self):
        def arrange(s,add):
            add("entered_1","ccp",turn_origin=SHANTUNG,route=[HOPEH],commitments=["combat_move"])
            add("entered_2","ccp",turn_origin=BEIPING,route=[SHANTUNG,HOPEH],commitments=["combat_move"])
            add("plane","ccp",kind="fighter",route=[BEIPING,HOPEH],commitments=["combat_move"])
            add("airborne","ccp",route=[BEIPING,HOPEH],commitments=["combat_move","airborne_assault"])
            add("amphibious","ccp",route=[BEIPING,HOPEH],commitments=["combat_move","amphibious_assault"])
            add("no_commitment","ccp",route=[BEIPING,HOPEH]);add("wrong_last","ccp",route=[HOPEH,BEIPING],commitments=["combat_move"])
            s["units"]["k"].update(route=[BEIPING,HOPEH],commitments=["combat_move"])
        env=fixture(mutate=arrange);setup=self.setup([env],["ccp"],[False]);out=self.call(setup)
        states,_=self.oracle(setup[0],out,[env],["ccp"],[False]);data=self.queued(states[0])[0]["data"]
        self.assertEqual(data["land_entry_origins"],[SHANTUNG,SHANTUNG]);self.assertEqual(len(data["origins"]),5)
        self.assertEqual(data["origins"]["plane"],BEIPING);self.assertNotIn("wrong_last",data["origins"])

    def test_exact_minor_status_controls_flag_not_militia_type_or_evolution_breaker(self):
        statuses=("minor","major","minorish")
        envs=[fixture("kmt",mutate=lambda s,add,status=status:(s["nations"]["kmt"].update(power_status=status),s["units"]["k"].update(type="militia"))) for status in statuses]
        setup=self.setup(envs,["ccp"]*3,[True]*3);out=self.call(setup);states,_=self.oracle(setup[0],out,envs,["ccp"]*3,[True]*3)
        self.assertEqual([bool(self.queued(s)[0]["flags"].get("truce_low_morale_eliminates")) for s in states],[True,False,False])

    def test_truce_false_noop_before_breaker_phase_border_or_capacity_reads(self):
        env=fixture("japan","production",mutate=lambda s,add:s["politics"].update(chinese_truce=False))
        setup=self.setup([env],["japan"],[False]);setup[2][0]=-999
        state,service,_,_=setup;caps=dict(battle_capacity=0,state_capacity=state.records.shape[1],block_capacity=1,
            string_capacity=state.string_offsets.numel()-1,byte_capacity=state.string_bytes.numel())
        out=self.call(setup,caps=caps);self.assertTrue(out.committed.item());self.oracle(state,out,[env],["japan"],[False])

    def test_no_mixed_zones_only_flips_three_truce_fields_and_retains_immediate_flag(self):
        env=fixture(mutate=lambda s,add:(s["units"].pop("k"),s["flags"].update(immediate_land_battles=-7)))
        setup=self.setup([env],["ccp"],[False]);state,service,_,_=setup
        caps=dict(battle_capacity=0,state_capacity=state.records.shape[1],block_capacity=state.records.shape[1],
            string_capacity=state.string_offsets.numel()-1,byte_capacity=state.string_bytes.numel())
        out=self.call(setup,caps=caps);states,_=self.oracle(state,out,[env],["ccp"],[False])
        self.assertEqual(out.battle_counts.item(),0);self.assertEqual(states[0]["flags"]["immediate_land_battles"],-7)

    def test_full_uint64_ids_zone_and_unit_order_and_all_opaque_fields(self):
        def arrange(s,add):
            s["flags"]["politics_sequence"]=2**31-1
            s["territories"][BEIPING]["possessor"]="ccp";add("z_two","ccp",BEIPING);add("a_two","kmt",BEIPING)
            add("蒙古\u0000","ccp");add("z_first","kmt");s["flags"]["immediate_land_battles"]=-3
        env=fixture("japan",serial=2**64-1,mutate=arrange);setup=self.setup([env],["kmt"],[True]);out=self.call(setup)
        states,_=self.oracle(setup[0],out,[env],["kmt"],[True]);s=states[0]
        ids=[f"truce_shared_{2**64-1}_{zone}" for zone in sorted((HOPEH,BEIPING))]
        self.assertEqual(s["battle_order"][-2:],ids);self.assertEqual(s["flags"]["politics_sequence"],2**31-1)
        self.assertEqual(s["battles"][ids[1]]["attackers"],["c","蒙古\u0000"])

    def test_native_errors_collision_order_and_selected_cohort_rollback(self):
        cases=[(fixture(),"japan",False),(fixture("japan"),"ccp",False),(fixture("ccp","production"),"ccp",False),
               (fixture(possessor=None),"ccp",False),(fixture(possessor="japan"),"kmt",True)]
        for env,breaker,automatic in cases:
            setup=self.setup([env],[breaker],[automatic]);out=self.call(setup);self.oracle(setup[0],out,[env],[breaker],[automatic]);self.rollback(setup[0],out)
        def duplicate(s,add):
            name="truce_shared_0_"+HOPEH;old=copy.deepcopy(s["battles"]["device_battle"]);old.update(id=name,zone=HOPEH)
            s["battles"][name]=old;s["battle_order"].append(name)
        env=fixture(mutate=duplicate);setup=self.setup([env],["ccp"],[False]);out=self.call(setup);self.oracle(setup[0],out,[env],["ccp"],[False]);self.rollback(setup[0],out)
        valid=fixture();bad=fixture(possessor=None);setup=self.setup([valid,bad],["ccp","kmt"],[False,True]);out=self.call(setup)
        self.oracle(setup[0],out,[valid,bad],["ccp","kmt"],[False,True]);self.rollback(setup[0],out)
        setup[2][1]=-999;out=self.call(setup,selected=[True,False]);self.oracle(setup[0],out,[valid,bad],["ccp","kmt"],[False,True],[True,False]);self.assertTrue(out.committed.item())

    def test_all_capacity_stages_require_retry_and_rollback_every_raw_buffer(self):
        env=fixture();setup=self.setup([env],["ccp"],[False]);state,service,_,_=setup;caps=service.reserve(state,battle_capacity=8)
        for change in (dict(battle_capacity=0),dict(state_capacity=state.records.shape[1]),dict(block_capacity=1),
                       dict(string_capacity=state.string_offsets.numel()-1),dict(byte_capacity=state.string_bytes.numel())):
            limited={**caps,**change};out=self.call(setup,caps=limited);self.assertEqual(out.errors.item(),5,str(change));self.rollback(state,out)
            if "battle_capacity" in change:self.assertEqual(out.required_battle_capacity.item(),1)
            if "state_capacity" in change:self.assertGreater(out.required_state_capacity.item(),state.records.shape[1])
        out=self.call(setup,caps=caps);self.oracle(state,out,[env],["ccp"],[False])

    def test_complete_large_stack_and_no_hot_host_json_route_or_catalog_calls(self):
        def arrange(s,add):
            for i in range(140):add(f"c_{i:03d}","ccp",route=[BEIPING,HOPEH],commitments=["combat_move"])
        env=fixture(mutate=arrange);setup=self.setup([env],["ccp"],[False]);caps=setup[1].reserve(setup[0],battle_capacity=8)
        self.assertTrue(self.call(setup,caps=caps).committed.item())
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("host copy")),patch.object(torch.Tensor,"item",side_effect=AssertionError("host scalar")),\
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("host list")),patch.object(json,"loads",side_effect=AssertionError("JSON read")),\
             patch.object(json,"dumps",side_effect=AssertionError("JSON write")),patch.object(gwrl_cpp,"campaign_terminate_chinese_truce_oracle",side_effect=AssertionError("native fallback")):
            out=self.call(setup,caps=caps)
        states,_=self.oracle(setup[0],out,[env],["ccp"],[False]);battle,=self.queued(states[0]);self.assertEqual(len(battle["attackers"]),141)
        self.assertEqual(len(battle["data"]["land_entry_origins"]),140)

    def test_malformed_border_metadata_errors_only_when_the_original_helper_reads_it(self):
        def entered(s,add):s["units"]["c"].update(route=[BEIPING,HOPEH],commitments=["combat_move"])
        original=fixture(mutate=entered)
        failing=gwrl_cpp._campaign_chinese_truce_border_test_fixture(original,BEIPING,HOPEH,"[false]")
        self.assertNotEqual(json.loads(original.serialize())["state"]["definition_fingerprint"],
                            json.loads(failing.serialize())["state"]["definition_fingerprint"])
        self.assertEqual(json.loads(original.serialize())["random"],json.loads(failing.serialize())["random"])
        # Fresh typed-definition fixtures preserve raw State/RNG, never pass
        # State through JSON just to alter immutable edge metadata.
        other=gwrl_cpp._campaign_chinese_truce_border_test_fixture(fixture("japan",mutate=entered),BEIPING,HOPEH,"[false]")
        quiet=gwrl_cpp._campaign_chinese_truce_border_test_fixture(fixture(),BEIPING,HOPEH,"[false]")
        setup=self.setup([failing,other,quiet],["ccp"]*3,[True]*3)
        out=self.call(setup);_,rows=self.oracle(setup[0],out,[failing,other,quiet],["ccp"]*3,[True]*3)
        self.assertEqual(out.errors.cpu().tolist(),[2,0,0]);self.rollback(setup[0],out)
        message=out.message_ids[0].item();self.assertGreaterEqual(message,0)
        self.assertEqual(setup[1].exception_messages[message],rows[0]["message"])
        selected=[False,True,True];out=self.call(setup,selected=selected)
        self.oracle(setup[0],out,[failing,other,quiet],["ccp"]*3,[True]*3,selected);self.assertTrue(out.committed.item())


if __name__=="__main__":unittest.main()
