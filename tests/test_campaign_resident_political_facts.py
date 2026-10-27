"""Exact original refresh blocks, independently checked through typed oracles."""
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
from studies.campaign.backends.resident_political_facts import ResidentPoliticalFacts
from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
from tests.test_campaign_device_state import rich_fixture
from tests.test_campaign_resident_relations import set_turn
from tools.benchmark_campaign_resident_recruitment_chance import canonical_native,require_exact

EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()
TOKYO="land_jap_tokyo";SHENSI="land_china_shensi"


def changed(env,mutate):
    doc=json.loads(env.serialize());mutate(doc["state"])
    doc["state"]["politics"]["pending"]["facts_raw_bits"]={"zero":-0.0,"precise":1.0000000000000002,"unknown":[None,True,"蒙古\u0000"]}
    out=env.clone();out.restore(json.dumps(doc,ensure_ascii=False));return out


def fixture(mutate=None):return changed(rich_fixture(),mutate or (lambda s:None))


def set_owned(s,owner,zones):
    for territory in s["territories"].values():
        if territory["possessor"]==owner:territory["possessor"]=None
    for zone in zones:s["territories"][zone]["possessor"]=owner


def threshold_base():
    def arrange(s):
        set_owned(s,"ccp",[TOKYO]);s["nations"]["ccp"].update(power_status="minor");set_turn(s,"ccp")
        for key in ("evolved_turn_serial","evolved_during_own_turn","objective_evolution"):
            s["nations"]["ccp"]["game_flags"].pop(key,None)
    env=fixture(arrange)
    return gwrl_cpp._campaign_political_facts_ipp_test_fixture(env,TOKYO,"13")


@unittest.skipUnless(EXACT,"Lossless Apple GPU required")
class ResidentPoliticalFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps");state=DeviceStateBatch.capture(envs,context=context)
        relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
        return state,ResidentPoliticalFacts(context,gwrl_cpp.campaign_political_facts_context(envs[0]),relations)

    def raw(self,state,lane):
        length=state.lengths[lane].cpu().item();used,size=state.suffix_usage.cpu().tolist()
        rows=state.records[lane,:length].cpu().numpy().copy();data=state.string_bytes[:size].cpu().numpy().copy();offsets=state.string_offsets[:used+1].cpu().numpy().copy()
        return SimpleNamespace(context=state.context.native,record_array=lambda:rows,lane_offsets=lambda:np.array([0,length],dtype=np.int64),
            string_bytes=lambda:data,string_offsets=lambda:offsets)

    def owners(self,state,names):return torch.tensor(state.context.prefix_lookup_ids(names),dtype=torch.int64,device="mps")

    def call(self,setup,mode,owners=None,selected=None,caps=None,relations=None):
        state,service=setup;caps=service.reserve(state) if caps is None else caps
        chosen=None if selected is None else torch.tensor(selected,dtype=torch.bool,device="mps")
        if mode==0:return service.refresh_possessions(state,chosen,**caps)
        if mode==1:return service.refresh_civil_flag(state,self.owners(state,owners),chosen,**caps)
        if mode==2:return service.mark_evolution_if_due(state,self.owners(state,owners),chosen,**caps)
        if mode==3:return service.refresh_one_china_objective(state,chosen,**caps)
        return service.rebuild_allies(state,chosen,relations=relations,**caps)

    def oracle(self,before,result,envs,mode,owners=None,selected=None):
        enabled=[True]*len(envs) if selected is None else selected
        rows=gwrl_cpp.campaign_political_facts_oracle(before.context.native,envs,owners or [],enabled,mode)
        self.assertEqual(result.errors.cpu().tolist(),[row["error"] for row in rows]);failed=any(row["error"] for row in rows)
        self.assertEqual(result.committed.item(),not failed)
        self.assertEqual(result.promoted.cpu().tolist(),[bool(row["promoted"]) and not failed for row in rows])
        for lane,row in enumerate(rows):
            golden=gwrl_cpp.capture_device_states(before.context.native,[envs[lane]]) if failed else row["packed_state"]
            require_exact(self.raw(result.state,lane),canonical_native(golden))
        numbers=result.state.records.cpu().numpy()
        self.assertTrue(np.any((numbers[:,:,0]==4)&(numbers[:,:,2]==0)&(numbers[:,:,3]==0x80000000)))
        self.assertTrue(np.any((numbers[:,:,0]==4)&(numbers[:,:,2]==1)&(numbers[:,:,3]==0x3ff00000)))
        self.assertIs(result.state.string_bytes,before.string_bytes);self.assertIs(result.state.string_offsets,before.string_offsets)
        self.assertIs(result.state.suffix_usage,before.suffix_usage)
        return rows

    def states(self,result):return [json.loads(env.serialize())["state"] for env in result.state.restore_envs()]

    def rollback(self,before,result):
        self.assertFalse(result.committed.item());self.assertFalse(result.accepted.any().item())
        self.assertTrue(torch.equal(result.state.records[:,:before.records.shape[1]],before.records))
        for name in ("lengths","sections","errors","suffix_usage"):self.assertTrue(torch.equal(getattr(result.state,name),getattr(before,name)),name)

    def test_possession_flags_ignore_income_eligibility_and_preserve_every_other_field(self):
        def arrange(s):
            for nation in s["nations"].values():nation["treasury"]=None;nation["game_flags"]["possessed_land_ipp"]=-17
            s["politics"]["surrendered"]=["kmt"]
            s["nations"]["japan"].update(power_status="major")
            s["territories"][TOKYO]["possessor"]="ccp"
            s["territories"][TOKYO]["flags"].update(city_damage=-39,city_ipp_lost=-3)
        env=fixture(arrange);setup=self.setup([env]);out=self.call(setup,0);self.oracle(setup[0],out,[env],0)
        native=gwrl_cpp.campaign_income_context(env);base=dict(zip(native.territory_ids,np.asarray(native.territory_array())[:,0],strict=True))
        source=json.loads(env.serialize())["state"];actual=self.states(out)[0]
        for nation in source["nations"]:
            total=0
            for zone,t in source["territories"].items():
                if t["possessor"]!=nation:continue
                flags=t["flags"];damage=flags.get("city_damage",0);div=abs(damage)//20*(-1 if damage<0 else 1)
                total+=max(0,int(base[zone])-max(flags.get("city_ipp_lost",0),div))
            self.assertEqual(actual["nations"][nation]["game_flags"]["possessed_land_ipp"],total)
        self.assertEqual(actual["nations"]["ccp"]["power_status"],source["nations"]["ccp"]["power_status"])

    def test_zero_ipp_owned_land_is_still_counted_and_only_possessions_are_touched(self):
        env=threshold_base();env=changed(env,lambda s:s["territories"][TOKYO]["flags"].update(city_ipp_lost=13))
        setup=self.setup([env]);out=self.call(setup,0);self.oracle(setup[0],out,[env],0);n=setup[1].nation_ids.index("ccp")
        self.assertEqual(out.possessed_ipp[0,n].item(),0);self.assertEqual(out.land_counts[0,n].item(),1)
        self.assertEqual(out.has_units[0,n].item(),-1)

    def test_civil_elimination_counts_carried_units_and_crews_without_catalog_or_land_filters(self):
        def arrange(s):
            template=copy.deepcopy(next(iter(s["units"].values())));s["units"]={}
            for name,owner,parent,cargo in (("carrier","japan",None,["ccp_crew"]),("ccp_crew","ccp","carrier",[])):
                u=copy.deepcopy(template);u.update(id=name,type="infantry",owner=owner,zone=TOKYO,turn_origin=TOKYO,
                    route=[],carried_by=parent,cargo=cargo,damage=0,movement_allowance=2,movement_remaining=1);s["units"][name]=u
        first=fixture(arrange);second=changed(first,lambda s:(s["units"].clear(),s["nations"]["ccp"]["game_flags"].update(civil_war_eliminated=0)))
        setup=self.setup([first,second]);out=self.call(setup,1,["ccp","ccp"]);self.oracle(setup[0],out,[first,second],1,["ccp","ccp"])
        states=self.states(out);self.assertEqual([s["nations"]["ccp"]["game_flags"]["civil_war_eliminated"] for s in states],[0,1])
        self.assertTrue((out.possessed_ipp==-1).all().item())

    def test_promotion_exact_threshold_status_flags_and_no_downstream_effects(self):
        base=threshold_base()
        below=changed(base,lambda s:s["territories"][TOKYO]["flags"].update(city_ipp_lost=1))
        during=changed(base,lambda s:s["politics"].update(chinese_truce=True,truce_permanently_ended=False))
        outside=changed(base,lambda s:set_turn(s,"japan"))
        setup=self.setup([below,during,outside]);out=self.call(setup,2,["ccp"]*3);self.oracle(setup[0],out,[below,during,outside],2,["ccp"]*3)
        states=self.states(out);self.assertEqual(out.promoted.cpu().tolist(),[False,True,True])
        self.assertEqual([s["nations"]["ccp"]["power_status"] for s in states],["minor","major","major"])
        self.assertEqual(states[1]["nations"]["ccp"]["game_flags"]["evolved_during_own_turn"],1)
        self.assertEqual(states[2]["nations"]["ccp"]["game_flags"]["evolved_during_own_turn"],0)
        self.assertTrue(states[1]["politics"]["chinese_truce"])
        for source,state in zip((below,during,outside),states,strict=True):
            previous=json.loads(source.serialize())["state"]
            for field in ("units","decisions","construction","clock","history"):self.assertEqual(state[field],previous[field])

    def test_promotion_major_surrender_and_below13_skip_large_counter_and_bad_ipp(self):
        base=threshold_base()
        major=changed(base,lambda s:(s["nations"]["ccp"].update(power_status="major"),s["clock"].update(player_turn_serial=str(2**64-1))))
        bad=gwrl_cpp._campaign_political_facts_ipp_test_fixture(major,TOKYO,"null")
        case=self.setup([bad]);out=self.call(case,2,["ccp"]);self.oracle(case[0],out,[bad],2,["ccp"])
        self.assertEqual(out.possessed_ipp[0,case[1].nation_ids.index("ccp")].item(),-1)
        kmt=fixture(lambda s:(s["politics"].update(surrendered=["kmt"]),s["clock"].update(player_turn_serial=str(2**64-1))))
        case=self.setup([kmt]);out=self.call(case,2,["kmt"]);self.oracle(case[0],out,[kmt],2,["kmt"])
        below=changed(base,lambda s:(s["territories"][TOKYO]["flags"].update(city_ipp_lost=1),s["clock"].update(player_turn_serial=str(2**64-1))))
        case=self.setup([below]);out=self.call(case,2,["ccp"]);self.oracle(case[0],out,[below],2,["ccp"]);self.assertFalse(out.promoted.item())

    def test_promotion_counter_intmax_success_and_overflow_atomic_failure(self):
        base=threshold_base();good=changed(base,lambda s:s["clock"].update(player_turn_serial=str(2**31-1)))
        bad=changed(base,lambda s:s["clock"].update(player_turn_serial=str(2**64-1)))
        case=self.setup([good]);out=self.call(case,2,["ccp"]);self.oracle(case[0],out,[good],2,["ccp"])
        self.assertEqual(self.states(out)[0]["nations"]["ccp"]["game_flags"]["evolved_turn_serial"],2**31-1)
        case=self.setup([bad]);out=self.call(case,2,["ccp"]);self.oracle(case[0],out,[bad],2,["ccp"]);self.rollback(case[0],out)

    def test_one_china_home_land_island_exceptions_and_zero_ipp_independence(self):
        zones=("land_hainan","land_formosa",TOKYO,SHENSI)
        envs=[fixture(lambda s,z=z:(set_owned(s,"kmt",[z]),s["territories"][z]["flags"].update(city_ipp_lost=2**31-1))) for z in zones]
        setup=self.setup(envs);out=self.call(setup,3);self.oracle(setup[0],out,envs,3)
        self.assertEqual([s["nations"]["ccp"]["game_flags"]["objective_one_china"] for s in self.states(out)],[1,1,1,0])
        self.assertTrue((out.possessed_ipp==-1).all().item())

    def test_allies_rebuild_exact_friendly_sets_ignores_unrelated_player_errors(self):
        def align(s):
            s["nations"]["ccp"].update(power_status="major",alliance="allies",allies=[])
            s["nations"]["kmt"].update(power_status="major",alliance="allies",allies=[])
            s["nations"]["ccp"]["at_war_with"]=["japan"];s["nations"]["kmt"]["at_war_with"]=["japan"]
            s["nations"]["japan"]["at_war_with"]=["ccp","kmt"]
        first=fixture(align);second=changed(first,lambda s:s["nations"]["kmt"].update(alliance=None))
        third=changed(second,lambda s:s["politics"].update(chinese_truce=True,truce_permanently_ended=False))
        setup=self.setup([first,second,third]);relations=setup[1].relations_context.compute(setup[0]);self.assertTrue((relations.player_errors!=0).any().item())
        out=self.call(setup,4,relations=relations);self.oracle(setup[0],out,[first,second,third],4)
        self.assertEqual([s["nations"]["ccp"]["allies"] for s in self.states(out)],[["kmt"],[],["kmt"]])
        with self.assertRaises(ValueError):setup[1].rebuild_allies(out.state,relations=relations,**setup[1].reserve(out.state))

    def test_bad_ipp_messages_are_lazy_owned_errors_and_other_seams_do_not_read_them(self):
        base=threshold_base();bad=gwrl_cpp._campaign_political_facts_ipp_test_fixture(base,TOKYO,"null")
        setup=self.setup([bad]);out=self.call(setup,0);rows=self.oracle(setup[0],out,[bad],0);self.rollback(setup[0],out)
        self.assertEqual(setup[1].messages[out.message_ids.item()],rows[0]["message"])
        out=self.call(setup,2,["ccp"]);self.oracle(setup[0],out,[bad],2,["ccp"]);self.rollback(setup[0],out)
        for mode,names in ((1,["ccp"]),(3,None),(4,None)):
            out=self.call(setup,mode,names);self.oracle(setup[0],out,[bad],mode,names);self.assertTrue(out.committed.item())
        unowned=changed(bad,lambda s:s["territories"][TOKYO].update(possessor=None));case=self.setup([unowned]);out=self.call(case,0)
        self.oracle(case[0],out,[unowned],0);self.assertTrue(out.committed.item())

    def test_absent_faction_full_presence_and_direct_owner_lookup_contract(self):
        for nation in ("ccp","kmt"):
            original=fixture();env=gwrl_cpp._campaign_political_facts_absent_test_fixture(original,nation)
            self.assertEqual(json.loads(original.serialize())["random"],json.loads(env.serialize())["random"])
            setup=self.setup([env]);out=self.call(setup,0);self.oracle(setup[0],out,[env],0)
            self.assertEqual(out.possessed_ipp[0,setup[1].nation_ids.index(nation)].item(),-1)
            for mode in (1,2):
                out=self.call(setup,mode,[nation]);self.oracle(setup[0],out,[env],mode,[nation]);self.rollback(setup[0],out)
            for mode in (3,4):out=self.call(setup,mode);self.oracle(setup[0],out,[env],mode)

    def test_native_int_undefined_ranges_are_explicit_not_silent_wrapping(self):
        env=threshold_base();env=gwrl_cpp._campaign_political_facts_ipp_test_fixture(env,TOKYO,str(2**31-1))
        env=changed(env,lambda s:s["territories"][TOKYO]["flags"].update(city_ipp_lost=-1,city_damage=-20))
        setup=self.setup([env]);out=self.call(setup,0);self.assertEqual(out.errors.item(),4);self.rollback(setup[0],out)
        # Never invoke the C++ oracle on signed-overflow arithmetic (undefined
        # native behavior); this is an explicit unsupported-state boundary.

    def test_capacity_retry_selected_cohort_rollback_and_no_hot_host_or_native_calls(self):
        base=threshold_base();setup=self.setup([base]);state,service=setup
        for change in (dict(state_capacity=state.records.shape[1]),dict(block_capacity=1)):
            out=self.call(setup,2,["ccp"],caps={**service.reserve(state),**change});self.assertEqual(out.errors.item(),5);self.rollback(state,out)
        good=self.call(setup,2,["ccp"]);self.oracle(state,good,[base],2,["ccp"])
        source=fixture();case=self.setup([base,base.clone()]);out=self.call(case,2,["ccp","dadao"])
        self.oracle(case[0],out,[base,base.clone()],2,["ccp","dadao"]);self.rollback(case[0],out)
        owners=self.owners(case[0],["ccp","dadao"]);owners[1]=-999;mask=torch.tensor([True,False],dtype=torch.bool,device="mps")
        out=case[1].mark_evolution_if_due(case[0],owners,mask,**case[1].reserve(case[0]));self.oracle(case[0],out,[base,base.clone()],2,["ccp","dadao"],[True,False])
        for mode,names in ((0,None),(1,["ccp"]),(2,["ccp"]),(3,None),(4,None)):
            target=self.setup([source]);self.call(target,mode,names)
            with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("host copy")),patch.object(torch.Tensor,"item",side_effect=AssertionError("host scalar")),\
                 patch.object(torch.Tensor,"tolist",side_effect=AssertionError("host list")),patch.object(json,"loads",side_effect=AssertionError("JSON parse")),\
                 patch.object(json,"dumps",side_effect=AssertionError("JSON serialize")),patch.object(gwrl_cpp,"campaign_political_facts_oracle",side_effect=AssertionError("native fallback")):
                out=self.call(target,mode,names)
            self.oracle(target[0],out,[source],mode,names)


if __name__=="__main__":unittest.main()
