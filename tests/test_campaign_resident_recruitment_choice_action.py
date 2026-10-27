"""Actual Engine.step oracle for complete resident recruitment-choice actions."""
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
from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
from studies.campaign.backends.content_digest_metal import inspect_digests
from studies.campaign.backends.resident_state_json import ResidentStateJson
from studies.campaign.backends.resident_state_income import ResidentIncomeContext
from studies.campaign.backends.resident_recruitment_choice_action import (ResidentRecruitmentChoiceAction,RecruitmentChoiceActionError)
from studies.campaign.backends.resident_recruitment_output_validation import ResidentRecruitmentOutputValidation
from studies.campaign.backends.resident_recruitment_chance import ResidentRecruitmentChance,RecruitmentChanceCapacities
from studies.campaign.backends.resident_recruitment_effects import ResidentRecruitmentEffects
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from tests import test_campaign_resident_recruitment_choice as choice_tests
from tests import test_campaign_resident_recruitment_chance as chance_tests
from tests import test_campaign_resident_political_unit_creation as creation_tests
from tests.test_campaign_resident_political_refresh import give,no_kmt_land
from tools.benchmark_campaign_resident_recruitment_chance import canonical_native,require_exact

EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def training_fixture():
    env=chance_tests.pending_fixture(training=True,face=1);env.resolve_chance();return env


def with_catalog(env,mode):
    source=json.loads(gwrl_cpp.campaign_catalog_stats_context(env)._test_source_json)
    creation_tests.conditional_catalog(source,absent=mode=="absent")
    if mode=="negative":
        for document in source.values():
            for unit in document.get("units",[]):
                if unit["id"]=="infantry":unit["rules"][0]["parameters"]["conditional_movement"]=-1
    changed=gwrl_cpp._campaign_catalog_stats_test_fixture(env,json.dumps(source))
    # The catalog diagnostic's fixture authoring may normalize native '-0'.
    # Reinsert the opaque binary64 sentinel before either execution starts.
    return choice_tests.changed(changed,lambda state:None)


def retained(state,*,id="retained_choice",nation="japan",kind="fixture_choice",continuation="retained_context",player="axis"):
    action=dict(id=id+"_option",kind="fixture_option",nation=nation,player=player,decision=id,parameters={})
    state["decisions"].insert(0,dict(id=id,kind=kind,nation=nation,reaction=True,continuation=continuation,options=[action]))
    state["politics"]["pending"].setdefault(continuation,{})


@unittest.skipUnless(EXACT,"Exact MPS required")
class ResidentRecruitmentChoiceActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs,indices,*,before=None,formatter=None,expected=None):
        if before is None:
            context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps");before=DeviceStateBatch.capture(envs,context=context)
        else:context=before.context
        relations=choice_tests.ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
        native=gwrl_cpp.campaign_recruitment_context(envs[0]);recruitment=choice_tests.ResidentRecruitment(relations,native)
        stats=choice_tests.ResidentCatalogStatsContext(context,gwrl_cpp.campaign_catalog_stats_context(envs[0]))
        facts=choice_tests.ResidentPoliticalFacts(context,gwrl_cpp.campaign_political_facts_context(envs[0]),relations)
        movement=choice_tests.ResidentPoliticalUnits(context,stats);truce=choice_tests.ResidentChineseTruce(context,gwrl_cpp.campaign_movement_context(envs[0]))
        evolution=choice_tests.ResidentEvolutionChoice(context,choice_tests.ResidentPoliticalDecisionQueue(context))
        surrender=choice_tests.ResidentSurrender(context,choice_tests.ResidentPoliticalUnitRemoval(context),native)
        refresh=choice_tests.ResidentPoliticalRefresh(context,facts,movement,truce,evolution,surrender)
        effects=choice_tests.ResidentRecruitmentChoice(context,recruitment,choice_tests.ResidentPoliticalUnitCreation(context,stats),refresh)
        source_native=gwrl_cpp.capture_device_states(context.native,envs)
        if formatter is None:formatter=ResidentStateJson(CanonicalJsonContext(source_native,context))
        income=ResidentIncomeContext(context,gwrl_cpp.campaign_income_context(envs[0]))
        validator=ResidentRecruitmentOutputValidation(context,stats,relations)
        handler=ResidentRecruitmentChoiceAction(context,effects,income,formatter,validator)
        names=[]
        for env in envs:
            state=json.loads(env.serialize())["state"];last=state["decisions"][-1]
            saved=state["politics"]["pending"].get(last["continuation"],{})
            name=saved.get("beneficiary") if isinstance(saved,dict) else None
            names.append(name if isinstance(name,str) else last["nation"])
        all_strings={};used,size=before.suffix_usage.cpu().tolist()
        for data,offsets in ((context.string_bytes,context.string_offsets),(before.string_bytes[:size],before.string_offsets[:used+1])):
            raw=bytes(data.cpu().tolist());positions=offsets.cpu().tolist()
            for a,b in zip(positions,positions[1:]):all_strings[raw[a:b].decode()]=len(all_strings)
        requests=torch.tensor([[lane,all_strings[name]] for lane,name in enumerate(names)],dtype=torch.int64,device="mps")
        menu=recruitment.choices(before,requests,capacity=512,parameter_byte_capacity=512)
        U=before.records.shape[1]//16
        caps=handler.capacities(before,menu,json_byte_capacity=1_048_576,payload_capacity=64,movement_unit_capacity=len(envs)*U,
            surrender_unit_capacity=U,surrender_project_capacity=32,truce_battle_capacity=8,evolution_option_capacity=128)
        key=formatter.identities(before,byte_capacity=caps.json_byte_capacity) if expected is None else expected
        return before,handler,caps,key,menu,torch.tensor(indices,dtype=torch.int64,device="mps")

    def call(self,setup,*,selected=None,caps=None,expected=None,menu=None,indices=None):
        before,handler,capacity,key,cached,selection=setup
        return handler.apply(before,key if expected is None else expected,cached if menu is None else menu,selection if indices is None else indices,
            None if selected is None else torch.tensor(selected,dtype=torch.bool,device="mps"),capacities=capacity if caps is None else caps)

    def raw(self,state,lane):
        length=state.lengths[lane].cpu().item();used,size=state.suffix_usage.cpu().tolist()
        rows=state.records[lane,:length].cpu().numpy().copy();data=state.string_bytes[:size].cpu().numpy().copy();offsets=state.string_offsets[:used+1].cpu().numpy().copy()
        return SimpleNamespace(context=state.context.native,record_array=lambda:rows,lane_offsets=lambda:np.array([0,length],dtype=np.int64),
            string_bytes=lambda:data,string_offsets=lambda:offsets)

    def native(self,setup,result,envs,selected=None):
        before,_,_,_,_,indices=setup;enabled=[True]*len(envs) if selected is None else selected
        source=[env.serialize() for env in envs]
        rows=gwrl_cpp.campaign_apply_recruitment_choice_action_oracle(before.context.native,envs,indices.cpu().tolist(),enabled)
        failed=any(row["error"] for row in rows)
        self.assertEqual(result.committed.item(),not failed,{name:value.cpu().tolist() for name,value in result.stage_errors.items()})
        self.assertEqual((result.errors==0).all().item(),not failed)
        for lane,row in enumerate(rows):
            gold=gwrl_cpp.capture_device_states(before.context.native,[envs[lane]]) if failed else row["packed_state"]
            require_exact(self.raw(result.state,lane),canonical_native(gold))
        if not failed:
            self.assertEqual(inspect_digests(result.identities.engine_keys),tuple(row["engine_key"] for row in rows))
            self.assertEqual(inspect_digests(result.identities.state_keys),tuple(row["state_key"] for row in rows))
            self.assertIs(result.identities.source,result.state)
        self.assertEqual([env.serialize() for env in envs],source)
        records=result.state.records.cpu().numpy()
        self.assertTrue(np.any((records[:,:,0]==4)&(records[:,:,2]==0)&(records[:,:,3]==0x80000000)))
        return rows

    def rollback(self,before,result):
        self.assertFalse(result.committed.item());self.assertFalse(result.accepted.any().item())
        for name in ("records","string_bytes","string_offsets"):
            old,new=getattr(before,name),getattr(result.state,name);self.assertTrue(torch.equal(old,new[tuple(slice(0,n) for n in old.shape)]),name)
            tail=new[:,old.shape[1]:] if name=="records" else new[old.shape[0]:]
            self.assertEqual(tail.count_nonzero().item(),0,name)
        for name in ("lengths","sections","errors","suffix_usage"):
            self.assertTrue(torch.equal(getattr(before,name),getattr(result.state,name)),name)
        self.assertTrue((result.identities.engine_keys.errors!=0).all().item())
        self.assertTrue((result.identities.state_keys.errors!=0).all().item())

    def test_all_four_effects_and_both_militia_sequences_keep_original_action_event(self):
        base=choice_tests.fixture(work=True)
        wanted=[("recruitment_place_infantry",{}),("recruitment_place_militia",{}),("recruitment_place_militia",{"different":True}),
                ("recruitment_advance_ship",{"project":"choice_ship_final"}),("recruitment_advance_ship",{"project":"choice_ship_more"}),
                ("recruitment_repair_facility",{})]
        envs=[base.clone() for _ in wanted];indices=[choice_tests.chosen(base,kind,**kwargs) for kind,kwargs in wanted]
        # Stored IDs are opaque Engine identities. Eligibility intentionally
        # compares the rule fields, while the audit Event retains this ID.
        envs[0]=choice_tests.changed(envs[0],lambda s:s["decisions"][-1]["options"][indices[0]].update(id="opaque/蒙古/action-id"))
        setup=self.setup(envs,indices);result=self.call(setup);self.native(setup,result,envs)
        for lane,env in enumerate(result.state.restore_envs()):
            actual=json.loads(env.serialize())["state"];prior=json.loads(envs[lane].serialize())["state"]
            self.assertEqual(actual["history"][-1]["kind"],"action")
            self.assertEqual(actual["history"][-1]["payload"],prior["decisions"][-1]["options"][indices[lane]])
            self.assertEqual(actual["clock"],prior["clock"])

    def test_training_reset_and_chronological_resident_chance_to_choice(self):
        env=chance_tests.pending_fixture(training=True,face=1,active="training")
        context=DeviceStateContext(gwrl_cpp.device_state_context(env),"mps");native=gwrl_cpp.capture_device_states(context.native,[env])
        before=DeviceStateBatch.from_native(native,context=context)
        relations=choice_tests.ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(env))
        recruitment=choice_tests.ResidentRecruitment(relations,gwrl_cpp.campaign_recruitment_context(env))
        formatter=ResidentStateJson(CanonicalJsonContext(native,context));income=ResidentIncomeContext(context,gwrl_cpp.campaign_income_context(env))
        chance=ResidentRecruitmentChance(context,ResidentRecruitmentEffects(recruitment),income,formatter)
        S=before.records.shape[1]+6000
        caps=RecruitmentChanceCapacities(S,S,512,2048,before.string_offsets.numel()-1+2048,before.string_bytes.numel()+262144,32,1_048_576,1,1)
        resolved=chance.resolve(before,formatter.identities(before,byte_capacity=caps.json_byte_capacity),capacities=caps)
        self.assertTrue(resolved.committed.item());env.resolve_chance()
        index=choice_tests.chosen(env,"recruitment_place_infantry")
        setup=self.setup([env],[index],before=resolved.state,formatter=formatter,expected=resolved.identities)
        result=self.call(setup);self.native(setup,result,[env])
        actual=json.loads(result.state.restore_envs()[0].serialize())["state"]
        self.assertEqual(actual["action_interface"],dict(schema="campaign-orders-v1",visited_configurations=[],declined_rail_requests=[]))
        self.assertEqual(actual["history"][-2]["kind"],"chance");self.assertEqual(actual["history"][-1]["kind"],"action")

    def test_all_private_streams_are_unchanged_for_choice_actions(self):
        base=choice_tests.fixture();index=choice_tests.chosen(base,"recruitment_place_infantry");envs=[]
        for stream in ("actual","search","training"):
            doc=json.loads(base.serialize());doc["random"].update(actual=str(2**64-1),search=str(2**63+17),training=str(2**63+31),active=stream,test_tape=[1,12],tape_position="1")
            doc["state"]["politics"]["pending"]["choice_opaque"]["zero"]=-0.0
            env=base.clone();env.restore(json.dumps(doc,ensure_ascii=False));envs.append(env)
        setup=self.setup(envs,[index]*3);self.native(setup,self.call(setup),envs)

    def test_current_refresh_can_queue_evolution_surrender_awards_and_new_chance(self):
        def source(s):
            minor=s["decisions"][-1]["nation"];give(s,"ccp",protect=(minor,));no_kmt_land(s)
            s["construction"]["kmt_ship"]=dict(id="kmt_ship",owner="kmt",type="destroyer",site=None,queue_position=2,paid_ipp=1,remaining_payments=[3],flags={})
            s["politics"]["pending"]["last_conqueror_kmt"]="japan"
        env=choice_tests.fixture(mutate=source);index=choice_tests.chosen(env,"recruitment_place_infantry")
        setup=self.setup([env],[index]);result=self.call(setup);self.native(setup,result,[env])
        actual=json.loads(result.state.restore_envs()[0].serialize())["state"]
        self.assertEqual(actual["decisions"][-1]["kind"],"politics_evolution");self.assertEqual(actual["chance"]["purpose"],"politics_surrender_queues")
        self.assertIn("kmt",actual["politics"]["surrendered"])
        self.assertEqual(sum(bool(p["flags"].get("national_objective_award")) for p in actual["construction"].values()),5)

    def test_native_outer_validation_rejects_unresolved_negative_and_colliding_units(self):
        base=choice_tests.fixture();index=choice_tests.chosen(base,"recruitment_place_infantry")
        envs=[with_catalog(base,"absent"),with_catalog(base,"negative")]
        def collision(s,rail):
            name="political_infantry_"+str(s["flags"]["politics_sequence"]+1)
            if rail:
                zones=list(s["territories"]);s["rails"][name]=dict(id=name,endpoint_a=zones[0],endpoint_b=zones[1],damage_by_endpoint={})
            else:
                facility=copy.deepcopy(next(iter(s["facilities"].values())));facility["id"]=name;s["facilities"][name]=facility
        envs.extend(choice_tests.changed(base,lambda s,rail=rail:collision(s,rail)) for rail in (False,True))
        for env in envs:
            with self.subTest(definition=env.planning_key()):
                setup=self.setup([env],[index]);result=self.call(setup);rows=self.native(setup,result,[env]);self.rollback(setup[0],result)
                self.assertEqual(rows[0]["error"],2);self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.VALIDATION)
                self.assertFalse(result.attempted["event"].any().item())

    def test_duplicate_new_decision_and_erased_retained_continuation_fail_native_validation(self):
        base=choice_tests.fixture();index=choice_tests.chosen(base,"recruitment_place_infantry")
        def duplicate(s):
            minor=s["decisions"][-1]["nation"];give(s,"ccp",protect=(minor,))
            retained(s,id="politics_evolution_"+str(s["flags"]["politics_sequence"]+2))
        def erased(s):retained(s,kind="politics_retained",continuation=s["decisions"][-1]["continuation"])
        for env,phrase in ((choice_tests.changed(base,duplicate),"Invalid/duplicate pending decision"),
                           (choice_tests.changed(base,erased),"Missing political decision continuation")):
            setup=self.setup([env],[index]);result=self.call(setup);rows=self.native(setup,result,[env]);self.rollback(setup[0],result)
            self.assertIn(phrase,rows[0]["message"]);self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.VALIDATION)

    def test_surrender_changed_controller_and_unknown_chance_nation_are_rejected(self):
        base=choice_tests.fixture();index=choice_tests.chosen(base,"recruitment_place_infantry")
        def controller(s):
            no_kmt_land(s);minor=s["decisions"][-1]["nation"];victim=next(n for n in s["nations"] if n.startswith("warlord_") and n!=minor)
            s["nations"][victim].update(controller_nation="kmt",player=None)
            retained(s,nation=victim,player="allies")
        def unknown(s):
            no_kmt_land(s);s["construction"]["kmt_ship"]=dict(id="kmt_ship",owner="kmt",type="destroyer",site=None,queue_position=2,paid_ipp=0,remaining_payments=[1],flags={})
            s["politics"]["pending"]["last_conqueror_kmt"]="not_a_nation"
        for env in (choice_tests.changed(base,controller),choice_tests.changed(base,unknown)):
            setup=self.setup([env],[index]);result=self.call(setup);self.native(setup,result,[env]);self.rollback(setup[0],result)
            self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.VALIDATION)

    def test_training_screening_forward_and_reached_force_capability(self):
        for mode in ("normal","empty_selected","absent_selected","unsorted_selected"):
            env=chance_tests.retained_naval_fixture(training=True,kind="screen",mode=mode,face=1);env.resolve_chance()
            env=choice_tests.changed(env,lambda state:None)
            index=choice_tests.chosen(env,"recruitment_place_infantry");setup=self.setup([env],[index])
            self.native(setup,self.call(setup),[env])
        env=chance_tests.retained_naval_fixture(training=True,kind="force",face=1);env.resolve_chance()
        index=choice_tests.chosen(env,"recruitment_place_infantry");setup=self.setup([env],[index]);result=self.call(setup);self.rollback(setup[0],result)
        self.assertTrue(result.unsupported.item());self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.FORWARD_CAPABILITY)
        def promote(s):give(s,"ccp",protect=(s["decisions"][-1]["nation"],))
        covered=choice_tests.changed(env,promote);setup=self.setup([covered],[index]);result=self.call(setup);self.native(setup,result,[covered])
        self.assertFalse(result.unsupported.item())

    def test_source_pending_priority_reserved_unselected_option_and_chance_gate(self):
        base=choice_tests.fixture();index=choice_tests.chosen(base,"recruitment_place_infantry")
        priority=choice_tests.changed(base,lambda s:s["flags"].update(immediate_land_battles=1,immediate_naval_battles=1))
        setup=self.setup([priority],[index]);self.native(setup,self.call(setup),[priority])
        def reserved(s):s["decisions"][-1]["options"][-1]["kind"]="end_phase"
        def chance(s):s["chance"]=dict(id="blocked",purpose="fixture",nation="japan",continuation="none",dice=[dict(sides=12,modifier=0,reroll_faces=[],max_rerolls=0)])
        for env in (choice_tests.changed(base,reserved),choice_tests.changed(base,chance)):
            setup=self.setup([env],[index]);result=self.call(setup);self.native(setup,result,[env]);self.rollback(setup[0],result)
            self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.PREFLIGHT)
        bad=choice_tests.changed(base,lambda s:s["decisions"][-1]["options"][index]["parameters"].update(beneficiary=False))
        setup=self.setup([base,bad],[index,-999]);result=self.call(setup,selected=[True,False]);self.native(setup,result,[base,bad],[True,False])

    def test_public_roll_and_foreign_dispatch_are_explicit_capabilities(self):
        base=choice_tests.fixture();index=choice_tests.chosen(base,"recruitment_place_infantry")
        for kind in ("recruitment_roll","unported_foreign_dispatch"):
            env=choice_tests.changed(base,lambda s,kind=kind:s["decisions"][-1]["options"][index].update(kind=kind))
            setup=self.setup([env],[index]);result=self.call(setup);self.rollback(setup[0],result)
            self.assertTrue(result.unsupported.item());self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.CAPABILITY)
            self.assertFalse(result.attempted["income"].any().item())
        # An unknown prefixed choice is handled by the original recruitment
        # dispatch and is an actual eligibility error, not an unported handler.
        env=choice_tests.changed(base,lambda s:s["decisions"][-1]["options"][index].update(kind="recruitment_unknown_choice"))
        setup=self.setup([env],[index]);result=self.call(setup);self.native(setup,result,[env]);self.rollback(setup[0],result)
        self.assertFalse(result.unsupported.item())

    def test_training_interface_reset_and_core_registry_capability_or_context_rejection(self):
        def visited(s):
            s["units"]={}
            s["action_interface"]=dict(schema="campaign-orders-v1",visited_configurations=[dict(raiders={},aircraft={},carriers={})],declined_rail_requests=[])
        core=choice_tests.changed(choice_tests.fixture(),visited);index=choice_tests.chosen(core,"recruitment_place_infantry")
        setup=self.setup([core],[index]);result=self.call(setup);self.rollback(setup[0],result)
        # Native can accept this unchanged empty configuration; its complete
        # naval-configuration validation is an explicit remaining capability.
        rows=gwrl_cpp.campaign_apply_recruitment_choice_action_oracle(setup[0].context.native,[core],[index],[True])
        self.assertEqual(rows[0]["error"],0);self.assertTrue(result.unsupported.item())
        self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.VALIDATION_CAPABILITY)
        wrapped=choice_tests.changed(training_fixture(),visited);index=choice_tests.chosen(wrapped,"recruitment_place_infantry")
        setup=self.setup([wrapped],[index]);self.native(setup,self.call(setup),[wrapped])
        def decline(s):
            minor=s["decisions"][-1]["nation"];border=next(z for z,t in s["territories"].items() if t["possessor"]==minor)
            no_kmt_land(s)
            s["construction"]["decline_project"]=dict(id="decline_project",owner="kmt",type="infantry",site=None,queue_position=2,paid_ipp=0,remaining_payments=[1],flags={})
            s["action_interface"]=dict(schema="campaign-orders-v1",visited_configurations=[],declined_rail_requests=[dict(sender="japan",recipient=minor,
                parameters=dict(project="decline_project",zone="land_jap_tokyo",border=border))])
        env=choice_tests.fixture(mutate=decline);index=choice_tests.chosen(env,"recruitment_place_infantry")
        setup=self.setup([env],[index]);result=self.call(setup);rows=self.native(setup,result,[env]);self.rollback(setup[0],result)
        self.assertIn("Unknown railroad request project",rows[0]["message"])
        self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.VALIDATION)

    def test_stale_expected_keys_and_foreign_source_are_checked_authoritatively(self):
        env=choice_tests.fixture();index=choice_tests.chosen(env,"recruitment_place_infantry");setup=self.setup([env],[index]);before,handler,_,key,menu,_=setup
        changed=key.engine_keys.hex_bytes.clone();changed[0,0]^=1
        bad=replace(key,engine_keys=replace(key.engine_keys,hex_bytes=changed));result=self.call(setup,expected=bad);self.rollback(before,result)
        self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.PREFLIGHT)
        with self.assertRaisesRegex(ValueError,"stale or foreign"):self.call(setup,expected=replace(key,source=replace(before)))
        with self.assertRaisesRegex(ValueError,"exact immutable source"):self.call(setup,menu=replace(menu,source=replace(before)))
        with self.assertRaisesRegex(ValueError,"resident contiguous"):self.call(setup,indices=torch.ones(1,dtype=torch.int32,device="mps"))
        self.assertIs(handler.state_context,before.context)

    def test_fixed_payload_json_event_and_rule_capacity_failures_are_atomic(self):
        env=choice_tests.fixture();index=choice_tests.chosen(env,"recruitment_place_militia",different=True);setup=self.setup([env],[index]);before,_,caps,_,_,_=setup
        good=self.call(setup);self.native(setup,good,[env]);R=good.required["payload"].item()
        for failed_caps in (replace(caps,payload_capacity=R-1),replace(caps,json_byte_capacity=0),
                            replace(caps,choice=replace(caps.choice,creation_capacity=0))):
            result=self.call(setup,caps=failed_caps);self.rollback(before,result)
        needed=good.required["event_state"].max().item();previous=max(good.required[key].max().item() for key in ("effects_state","income_state","reset_state","forward_state"))
        # Popping a large stored menu can make the final State smaller than
        # its original/intermediate arena. The Event still needs one genuinely
        # new 64-byte State key after all rule/validation work has succeeded.
        event_bytes=good.required["event_strings"][1].item();effect_bytes=good.required["effects_strings"][1].item()
        self.assertGreater(event_bytes,effect_bytes)
        late=replace(caps,choice=replace(caps.choice,political_refresh=replace(caps.choice.political_refresh,byte_capacity=event_bytes-1)))
        result=self.call(setup,caps=late);self.rollback(before,result)
        self.assertTrue(result.attempted["event"].all().item());self.assertTrue(result.errors.item()&RecruitmentChoiceActionError.EVENT)
        exact=replace(caps,payload_capacity=R,json_byte_capacity=max(good.required["before_json_bytes"].max().item(),good.required["after_json_bytes"].max().item()),
            choice=replace(caps.choice,political_refresh=replace(caps.choice.political_refresh,state_capacity=max(before.records.shape[1],needed,previous))))
        self.native(setup,self.call(setup,caps=exact),[env])

    def test_no_hot_menu_regeneration_host_reads_or_native_fallback(self):
        env=choice_tests.fixture();index=choice_tests.chosen(env,"recruitment_place_infantry");setup=self.setup([env],[index]);before,handler,_,_,_,_=setup
        self.call(setup)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("hot host read")),patch.object(torch.Tensor,"item",side_effect=AssertionError("hot scalar")),\
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("hot list")),patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("hot bool")),\
             patch.object(json,"loads",side_effect=AssertionError("hot JSON")),patch.object(json,"dumps",side_effect=AssertionError("hot JSON")),\
             patch.object(handler.effects.recruitment,"choices",side_effect=AssertionError("menu regeneration")),\
             patch.object(gwrl_cpp,"campaign_apply_recruitment_choice_action_oracle",side_effect=AssertionError("native fallback")):
            result=self.call(setup)
        self.native(setup,result,[env]);self.assertTrue(result.committed.item())
        disabled=self.call(setup,selected=[False]);self.native(setup,disabled,[env],[False])
        empty=DeviceStateBatch.capture([],context=before.context);empty_menu=handler.effects.recruitment.choices(empty,
            torch.empty((0,2),dtype=torch.int64,device="mps"),capacity=0)
        caps=handler.capacities(empty,empty_menu,json_byte_capacity=0,payload_capacity=0,movement_unit_capacity=0,surrender_unit_capacity=0,
            surrender_project_capacity=0,truce_battle_capacity=0,evolution_option_capacity=0)
        key=handler.state_json.identities(empty,byte_capacity=0)
        result=handler.apply(empty,key,empty_menu,torch.empty(0,dtype=torch.int64,device="mps"),capacities=caps)
        self.assertTrue(result.committed.item());self.assertEqual(result.state.lane_count,0)
