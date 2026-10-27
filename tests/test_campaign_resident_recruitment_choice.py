"""Stored choice/current eligibility cache, exact original effects and rollback."""
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
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_catalog_stats import ResidentCatalogStatsContext
from studies.campaign.backends.resident_chinese_truce import ResidentChineseTruce
from studies.campaign.backends.resident_evolution_choices import ResidentEvolutionChoice
from studies.campaign.backends.resident_political_decisions import ResidentPoliticalDecisionQueue
from studies.campaign.backends.resident_political_facts import ResidentPoliticalFacts
from studies.campaign.backends.resident_political_refresh import ResidentPoliticalRefresh
from studies.campaign.backends.resident_political_units import ResidentPoliticalUnits
from studies.campaign.backends.resident_political_unit_creation import ResidentPoliticalUnitCreation
from studies.campaign.backends.resident_political_unit_removal import ResidentPoliticalUnitRemoval
from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
from studies.campaign.backends.resident_recruitment import ResidentRecruitment
from studies.campaign.backends.resident_recruitment_choice import ResidentRecruitmentChoice,UNSUPPORTED_ENTRY
from studies.campaign.backends.resident_surrender import ResidentSurrender
from tests.test_campaign_resident_recruitment_chance import pending_fixture
from tests.test_campaign_resident_political_refresh import give
from tools.benchmark_campaign_resident_recruitment_chance import canonical_native,require_exact

EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def changed(env,mutate):
    doc=json.loads(env.serialize());mutate(doc["state"])
    doc["state"]["politics"]["pending"]["choice_opaque"]={"zero":-0.0,"precise":1.0000000000000002,"unknown":[None,True,"蒙古\u0000"]}
    out=env.clone();out.restore(json.dumps(doc,ensure_ascii=False));return out


def fixture(*,work=False,mutate=None):
    def author(doc,minor):
        if work:
            s=doc["state"];zone=next(z for z,t in s["territories"].items() if t["possessor"]==minor)
            for id,position,payments,paid,flags in (("choice_ship_final",3,[6],0,{"opaque":-3}),
                    ("choice_ship_more",3,[2,7],11,{"completed":-7,"opaque":9})):
                s["construction"][id]={"id":id,"owner":minor,"type":"destroyer","site":None,"queue_position":position,
                    "paid_ipp":paid,"remaining_payments":payments,"flags":flags}
            s["facilities"]["choice_facility"]={"id":"choice_facility","type":"airbase","zone":zone,"damage":1,"flags":{"opaque":7}}
            for owner in ("japan","ccp","kmt",minor):
                id="job_"+owner;s["repairs"][id]={"id":id,"owner":owner,"target":"choice_facility","remaining_damage":1,
                    "remaining_cost":4,"restricts_action":True,"endpoint":None}
    env=pending_fixture(face=1,mutate=author);env.resolve_chance()
    return changed(env,mutate or (lambda s:None))


def chosen(env,kind,*,different=False,project=None):
    options=json.loads(env.serialize())["state"]["decisions"][-1]["options"]
    return next(i for i,a in enumerate(options) if a["kind"]==kind and (not different or len(set(a["parameters"].get("zones",[])))==2)
                and (project is None or a["parameters"].get("project")==project))


@unittest.skipUnless(EXACT,"Lossless MPS required")
class ResidentRecruitmentChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs,indices,*,menu_capacity=256,menu_parameter_capacity=512,menu_selected=None):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps");before=DeviceStateBatch.capture(envs,context=context)
        relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]));native=gwrl_cpp.campaign_recruitment_context(envs[0])
        recruitment=ResidentRecruitment(relations,native);stats=ResidentCatalogStatsContext(context,gwrl_cpp.campaign_catalog_stats_context(envs[0]))
        facts=ResidentPoliticalFacts(context,gwrl_cpp.campaign_political_facts_context(envs[0]),relations)
        movement=ResidentPoliticalUnits(context,stats);truce=ResidentChineseTruce(context,gwrl_cpp.campaign_movement_context(envs[0]))
        evolution=ResidentEvolutionChoice(context,ResidentPoliticalDecisionQueue(context))
        surrender=ResidentSurrender(context,ResidentPoliticalUnitRemoval(context),native)
        refresh=ResidentPoliticalRefresh(context,facts,movement,truce,evolution,surrender)
        service=ResidentRecruitmentChoice(context,recruitment,ResidentPoliticalUnitCreation(context,stats),refresh)
        names=[]
        for env in envs:
            state=json.loads(env.serialize())["state"]
            if not state["decisions"]:names.append("ccp");continue
            decision=state["decisions"][-1];saved=state["politics"]["pending"].get(decision["continuation"],{})
            minor=saved.get("beneficiary") if isinstance(saved,dict) else None
            names.append(minor if isinstance(minor,str) else decision["nation"])
        all_strings={};used,size=before.suffix_usage.cpu().tolist()
        for data,offsets in ((before.context.string_bytes,before.context.string_offsets),(before.string_bytes[:size],before.string_offsets[:used+1])):
            raw=bytes(data.cpu().tolist());positions=offsets.cpu().tolist()
            for a,b in zip(positions,positions[1:]):all_strings[raw[a:b].decode()]=len(all_strings)
        requests=torch.tensor([[i,all_strings[name]] for i,name in enumerate(names)],dtype=torch.int64,device="mps")
        selection=None if menu_selected is None else torch.tensor(menu_selected,dtype=torch.bool,device="mps")
        # Stored choices already reference all current generated IDs. Keep the
        # exact captured pool allocation so namespace-capacity failures are real,
        # rather than hidden by unrelated menu padding.
        menu=recruitment.choices(before,requests,capacity=menu_capacity,parameter_byte_capacity=menu_parameter_capacity,selected=selection)
        return before,service,menu,torch.tensor(indices,dtype=torch.int64,device="mps")

    def capacities(self,setup):
        before,service,menu,_=setup;U=before.records.shape[1]//16
        return service.reserve(before,menu,movement_unit_capacity=before.lane_count*U,surrender_unit_capacity=U,
            surrender_project_capacity=32,truce_battle_capacity=8,evolution_option_capacity=128)

    def call(self,setup,*,selected=None,caps=None):
        before,service,menu,indices=setup
        return service.apply(before,menu,indices,None if selected is None else torch.tensor(selected,dtype=torch.bool,device="mps"),
            capacities=self.capacities(setup) if caps is None else caps)

    def raw(self,state,lane):
        length=state.lengths[lane].cpu().item();used,size=state.suffix_usage.cpu().tolist()
        rows=state.records[lane,:length].cpu().numpy().copy();data=state.string_bytes[:size].cpu().numpy().copy();offsets=state.string_offsets[:used+1].cpu().numpy().copy()
        return SimpleNamespace(context=state.context.native,record_array=lambda:rows,lane_offsets=lambda:np.array([0,length],dtype=np.int64),
            string_bytes=lambda:data,string_offsets=lambda:offsets)

    def oracle(self,setup,result,envs,selected=None):
        before,_,_,indices=setup;enabled=[True]*len(envs) if selected is None else selected
        rows=gwrl_cpp.campaign_apply_recruitment_choice_oracle(before.context.native,envs,indices.cpu().tolist(),enabled)
        self.assertEqual(result.errors.cpu().tolist(),[row["error"] for row in rows]);failed=any(row["error"] for row in rows)
        self.assertEqual(result.committed.item(),not failed)
        for lane,row in enumerate(rows):
            gold=gwrl_cpp.capture_device_states(before.context.native,[envs[lane]]) if failed else row["packed_state"]
            require_exact(self.raw(result.state,lane),canonical_native(gold))
            if not row["error"]:self.assertEqual(result.handled[lane].item(),row["handled"])
        bits=result.state.records.cpu().numpy()
        self.assertTrue(np.any((bits[:,:,0]==4)&(bits[:,:,2]==0)&(bits[:,:,3]==0x80000000)))
        self.assertTrue(np.any((bits[:,:,0]==4)&(bits[:,:,2]==1)&(bits[:,:,3]==0x3ff00000)))
        return rows

    def states(self,result):return [json.loads(env.serialize())["state"] for env in result.state.restore_envs()]

    def rollback(self,before,result):
        self.assertFalse(result.committed.item());self.assertFalse(result.accepted.any().item())
        for name in ("records","string_bytes","string_offsets"):
            old,new=getattr(before,name),getattr(result.state,name);self.assertTrue(torch.equal(new[tuple(slice(0,n) for n in old.shape)],old),name)
        for name in ("lengths","sections","errors","suffix_usage"):self.assertTrue(torch.equal(getattr(before,name),getattr(result.state,name)),name)

    def test_infantry_same_zone_and_split_militia_all_native_actions_exact(self):
        base=fixture();kinds=("recruitment_place_infantry","recruitment_place_militia","recruitment_place_militia")
        indices=[chosen(base,kinds[0]),chosen(base,kinds[1]),chosen(base,kinds[2],different=True)]
        envs=[base,base.clone(),base.clone()];setup=self.setup(envs,indices);out=self.call(setup);self.oracle(setup,out,envs)
        original=json.loads(base.serialize())["state"];states=self.states(out)
        self.assertEqual([len(s["units"])-len(original["units"]) for s in states],[1,2,2])
        for s in states:
            self.assertEqual(len(s["decisions"]),len(original["decisions"])-1)
            for name in ("history","clock"):self.assertEqual(s[name],original[name])
            self.assertEqual(s.get("action_interface",{}),original.get("action_interface",{}))
            self.assertEqual({n:x["income_components"] for n,x in s["nations"].items()},
                {n:x["income_components"] for n,x in original["nations"].items()})

    def test_free_ship_work_preserves_paid_ipp_and_existing_completed_flags(self):
        base=fixture(work=True);indices=[chosen(base,"recruitment_advance_ship",project=p) for p in ("choice_ship_final","choice_ship_more")]
        envs=[base,base.clone()];setup=self.setup(envs,indices);out=self.call(setup);self.oracle(setup,out,envs);states=self.states(out)
        final=states[0]["construction"]["choice_ship_final"];more=states[1]["construction"]["choice_ship_more"]
        self.assertEqual((final["queue_position"],final["remaining_payments"],final["paid_ipp"],final["flags"]["completed"]),(2,[],0,1))
        self.assertEqual((more["queue_position"],more["remaining_payments"],more["paid_ipp"],more["flags"]["completed"]),(2,[7],11,-7))
        self.assertEqual(len(states[0]["units"]),len(json.loads(base.serialize())["state"]["units"]))

    def test_facility_repair_cancels_every_owners_job_and_no_other_work(self):
        base=fixture(work=True);index=chosen(base,"recruitment_repair_facility");setup=self.setup([base],[index]);out=self.call(setup)
        self.oracle(setup,out,[base]);state=self.states(out)[0];self.assertEqual(state["facilities"]["choice_facility"]["damage"],0)
        self.assertTrue(all(job["target"]!="choice_facility" for job in state["repairs"].values()))
        original=json.loads(base.serialize())["state"];self.assertEqual(state["construction"],original["construction"])

    def test_extra_valid_generic_json_and_wrong_beneficiary_remain_native_mismatch2(self):
        base=fixture();index=chosen(base,"recruitment_place_infantry")
        values=(False,1.0000000000000002,{"nested":[None,-0.0,{"x":True}]})
        envs=[changed(base,lambda s,value=value:s["decisions"][-1]["options"][index]["parameters"].update(extra=value)) for value in values]
        envs.append(changed(base,lambda s:s["decisions"][-1]["options"][index]["parameters"].update(beneficiary=False)))
        envs.append(changed(base,lambda s:s["decisions"][-1]["options"][index]["parameters"].update(beneficiary="ccp")))
        setup=self.setup(envs,[index]*len(envs));out=self.call(setup);self.oracle(setup,out,envs);self.assertEqual(out.errors.cpu().tolist(),[2]*len(envs));self.rollback(setup[0],out)

    def test_current_complete_menu_rejects_stale_eligibility_without_regeneration(self):
        base=fixture();index=chosen(base,"recruitment_place_infantry");a=json.loads(base.serialize())["state"]["decisions"][-1]["options"][index]
        zone=a["parameters"]["zone"]
        env=changed(base,lambda s:s["territories"][zone].update(possessor="japan"));setup=self.setup([env],[index]);out=self.call(setup)
        self.oracle(setup,out,[env]);self.assertEqual(out.errors.item(),2);self.rollback(setup[0],out)

    def test_saved_continuation_types_and_wrong_decision_kind_error_before_eligibility(self):
        base=fixture();index=chosen(base,"recruitment_place_infantry")
        def bad_saved(s):s["politics"]["pending"][s["decisions"][-1]["continuation"]]["beneficiary"]=False
        envs=[changed(base,bad_saved),changed(base,lambda s:s["decisions"][-1].update(kind="device_fixture")),
              changed(base,lambda s:s["decisions"][-1]["options"][index].update(kind="recruitment_unknown"))]
        setup=self.setup(envs,[index]*3);out=self.call(setup);self.oracle(setup,out,envs);self.assertEqual(out.errors.cpu().tolist(),[2,2,2])

    def test_unhandled_kind_is_noop_and_roll_entry_is_explicit_unimplemented_capability(self):
        base=fixture();index=chosen(base,"recruitment_place_infantry")
        other=changed(base,lambda s:s["decisions"][-1]["options"][index].update(kind="unrelated_option"))
        setup=self.setup([other],[index]);out=self.call(setup);self.oracle(setup,out,[other]);self.assertFalse(out.handled.item())
        self.assertTrue(torch.equal(out.state.suffix_usage,setup[0].suffix_usage))
        roll=changed(base,lambda s:s["decisions"][-1]["options"][index].update(kind="recruitment_roll"))
        case=self.setup([roll],[index]);out=self.call(case);self.assertEqual(out.errors.item(),UNSUPPORTED_ENTRY);self.assertTrue(out.unsupported_entry.item());self.rollback(case[0],out)
        # This explicitly unsupported public-roll dispatch is outside the pure
        # choice oracle-parity domain; the roll service owns its native error.

    def test_two_militia_calls_preserve_counter_zero_crossing_and_second_failure(self):
        base=fixture();index=chosen(base,"recruitment_place_militia")
        def conditional(source):
            for doc in source.values():
                for unit in doc.get("units",[]):
                    if unit["id"]=="militia":unit["rules"]=[{"id":"militia_conditional_movement","parameters":{"requires_flags":["politics_sequence"],"conditional_movement":7}}]
        source=json.loads(gwrl_cpp.campaign_catalog_stats_context(base)._test_source_json);conditional(source)
        altered=gwrl_cpp._campaign_catalog_stats_test_fixture(base,json.dumps(source));altered=changed(altered,lambda s:s["flags"].update(politics_sequence=-2))
        setup=self.setup([altered],[index]);out=self.call(setup);self.oracle(setup,out,[altered]);state=self.states(out)[0]
        ids=[id for id in state["units"] if id not in json.loads(altered.serialize())["state"]["units"]]
        self.assertEqual(len(ids),2);self.assertEqual(state["units"]["political_militia_-1"]["movement_allowance"],7)
        self.assertEqual(state["flags"]["politics_sequence"],0)
        overflow=changed(base,lambda s:s["flags"].update(politics_sequence=2**31-2));case=self.setup([overflow],[index]);out=self.call(case)
        self.oracle(case,out,[overflow]);self.assertEqual(out.stage_errors["create_1"].item(),2);self.rollback(case[0],out)

    def test_native_eligible_query_error_is_attributed_before_global_menu_failure(self):
        base=fixture();index=chosen(base,"recruitment_place_infantry")
        state=json.loads(base.serialize())["state"];current=state["decisions"][-1]["nation"]
        neutral=next(id for id,n in state["nations"].items() if id.startswith("warlord_") and id!=current and n["player"] is None and n["controller_nation"] is None)
        def mismatch(s):
            d=s["decisions"][-1];s["politics"]["pending"][d["continuation"]]["beneficiary"]=neutral;d["options"][index]["parameters"]["beneficiary"]=neutral
        bad=changed(base,mismatch);setup=self.setup([base,bad],[index,index]);out=self.call(setup);self.oracle(setup,out,[base,bad])
        self.assertEqual(out.errors.cpu().tolist(),[0,2]);self.assertEqual(out.stage_errors["query"].cpu().tolist(),[0,2]);self.rollback(setup[0],out)

    def test_stale_or_replaced_cache_is_rejected_and_no_hot_menu_or_host_paths(self):
        base=fixture();index=chosen(base,"recruitment_place_infantry");setup=self.setup([base],[index]);before,service,menu,indices=setup;caps=self.capacities(setup)
        self.assertTrue(self.call(setup,caps=caps).committed.item())
        with self.assertRaises(ValueError):service.apply(before.snapshot(),menu,indices,capacities=caps)
        broken=replace(menu,arena=replace(menu.arena,records=menu.arena.records.clone()))
        with self.assertRaises(ValueError):service.apply(before,broken,indices,capacities=caps)
        with patch.object(service.recruitment,"choices",side_effect=AssertionError("regenerated menu")),patch.object(service.recruitment,"query",side_effect=AssertionError("regenerated choices")),\
             patch.object(torch.Tensor,"cpu",side_effect=AssertionError("host copy")),patch.object(torch.Tensor,"item",side_effect=AssertionError("host scalar")),\
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("host list")),patch.object(json,"loads",side_effect=AssertionError("JSON parse")),\
             patch.object(json,"dumps",side_effect=AssertionError("JSON serialize")),patch.object(gwrl_cpp,"campaign_apply_recruitment_choice_oracle",side_effect=AssertionError("native fallback")):
            out=self.call(setup,caps=caps)
        self.oracle(setup,out,[base])

    def test_capacity_failures_after_pop_and_late_refresh_restore_original_namespace(self):
        base=fixture();index=chosen(base,"recruitment_place_infantry");setup=self.setup([base],[index]);before,_,menu,_=setup;caps=self.capacities(setup)
        failures=[replace(caps,creation_capacity=0),replace(caps,creation_id_byte_capacity=0),
            replace(caps,political_refresh=replace(caps.political_refresh,block_capacity=1)),
            replace(caps,political_refresh=replace(caps.political_refresh,string_capacity=menu.arena.string_offsets.numel()-1)),
            replace(caps,political_refresh=replace(caps.political_refresh,byte_capacity=menu.arena.string_bytes.numel()))]
        for cap in failures:
            out=self.call(setup,caps=cap);self.assertEqual(out.errors.item(),5);self.rollback(before,out)
        # Even an unchanged eligibility menu can be externally too small; fail
        # closed and report its exact retry count, without regenerating it.
        short=self.setup([base],[index],menu_capacity=0);out=self.call(short);self.assertEqual(out.errors.item(),5);self.rollback(short[0],out)
        def late(s):
            minor=s["decisions"][-1]["nation"];give(s,"ccp",protect=(minor,))
            s["nations"]["ccp"]["power_status"]="minor";s["clock"]["player_turn_serial"]=str(2**64-1)
        late_source=changed(base,late);late_case=self.setup([late_source],[index]);out=self.call(late_case)
        self.oracle(late_case,out,[late_source]);self.assertEqual(out.stage_errors["refresh"].item(),2);self.rollback(late_case[0],out)

    def test_selected_cohort_error_and_unselected_invalid_index_remain_atomic(self):
        base=fixture();index=chosen(base,"recruitment_place_infantry")
        bad=changed(base,lambda s:s["decisions"][-1]["options"][index]["parameters"].update(extra=True))
        setup=self.setup([base,bad],[index,index]);out=self.call(setup);self.oracle(setup,out,[base,bad]);self.rollback(setup[0],out)
        setup[3][1]=-999;out=self.call(setup,selected=[True,False]);self.oracle(setup,out,[base,bad],[True,False]);self.assertTrue(out.committed.item())


if __name__=="__main__":unittest.main()
