"""Complete native political refresh ordering, raw bits and cohort rollback."""
from dataclasses import replace
import copy
import json
from pathlib import Path
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
from studies.campaign.backends.resident_political_unit_removal import ResidentPoliticalUnitRemoval
from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
from studies.campaign.backends.resident_surrender import ResidentSurrender
from tests import test_campaign_resident_political_unit_creation as creation_tests
from tests.test_campaign_resident_relations import set_turn
from tools.benchmark_campaign_resident_recruitment_chance import canonical_native,require_exact

EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()
SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"
NODES=json.loads((SCENARIO/"map.json").read_text())["nodes"]
HOPEH="land_china_hopeh"


def total(state,nation):
    return sum(max(0,int(NODES[z]["ipp_value"])-max(t["flags"].get("city_ipp_lost",0),int(t["flags"].get("city_damage",0)/20)))
               for z,t in state["territories"].items() if t["possessor"]==nation)


def give(state,nation,minimum=13,*,protect=()):
    for zone,territory in sorted(state["territories"].items()):
        if total(state,nation)>=minimum:return
        if territory["possessor"]!=nation and territory["possessor"] not in protect and NODES[zone]["ipp_value"]>0:
            territory["possessor"]=nation
    if total(state,nation)<minimum:raise AssertionError("Fixture lacks the required possessed land IPP")


def fixture(mutate=None,*,sequence=None,catalog=None):
    def author(state):
        state["history"].append(dict(kind="refresh_opaque",payload={"zero":-0.0,"exact":1.0000000000000002,"utf8":"蒙古\u0000"},after_state_key="retained-not-rehashed"))
        if mutate:mutate(state)
    return creation_tests.fixture(sequence=sequence,mutate=author,catalog=catalog)


def mixed_promotions(state):
    set_turn(state,"kmt");state["clock"].update(phase="combat",income_collected=False)
    state["territories"][HOPEH]["possessor"]="ccp"
    give(state,"ccp");give(state,"kmt",protect=("ccp",))
    for nation in ("ccp","kmt"):state["nations"][nation]["power_status"]="minor"
    state["politics"].update(chinese_truce=True,truce_permanently_ended=False,truce_offer_pending=True)
    template=copy.deepcopy(next(u for u in state["units"].values() if u["type"]=="infantry" and not u["cargo"] and u["carried_by"] is None))
    for nation in ("ccp","kmt"):
        unit=copy.deepcopy(template);name="refresh_mixed_"+nation
        unit.update(id=name,owner=nation,zone=HOPEH,turn_origin=HOPEH,route=[],cargo=[],carried_by=None,
                    commitments=[],movement_allowance=3,movement_remaining=1,turn_flags={"placed_this_turn":1})
        state["units"][name]=unit


def no_kmt_land(state):
    for territory in state["territories"].values():
        if territory["possessor"]=="kmt":territory["possessor"]="japan"


@unittest.skipUnless(EXACT,"Exact MPS required")
class ResidentPoliticalRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps");state=DeviceStateBatch.capture(envs,context=context)
        relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
        facts=ResidentPoliticalFacts(context,gwrl_cpp.campaign_political_facts_context(envs[0]),relations)
        movement=ResidentPoliticalUnits(context,ResidentCatalogStatsContext(context,gwrl_cpp.campaign_catalog_stats_context(envs[0])))
        truce=ResidentChineseTruce(context,gwrl_cpp.campaign_movement_context(envs[0]))
        evolution=ResidentEvolutionChoice(context,ResidentPoliticalDecisionQueue(context))
        surrender=ResidentSurrender(context,ResidentPoliticalUnitRemoval(context),gwrl_cpp.campaign_recruitment_context(envs[0]))
        return state,ResidentPoliticalRefresh(context,facts,movement,truce,evolution,surrender)

    def capacities(self,setup):
        state,service=setup;units=state.records.shape[1]//16
        return service.reserve(state,movement_unit_capacity=state.lane_count*units,surrender_unit_capacity=units,
            surrender_project_capacity=64,truce_battle_capacity=16,evolution_option_capacity=256)

    def call(self,setup,*,selected=None,capacities=None):
        state,service=setup
        return service.refresh(state,None if selected is None else torch.tensor(selected,dtype=torch.bool,device="mps"),
            capacities=self.capacities(setup) if capacities is None else capacities)

    def raw(self,state,lane):
        length=state.lengths[lane].cpu().item();used,size=state.suffix_usage.cpu().tolist()
        rows=state.records[lane,:length].cpu().numpy().copy();data=state.string_bytes[:size].cpu().numpy().copy();offsets=state.string_offsets[:used+1].cpu().numpy().copy()
        return SimpleNamespace(context=state.context.native,record_array=lambda:rows,lane_offsets=lambda:np.array([0,length],dtype=np.int64),
            string_bytes=lambda:data,string_offsets=lambda:offsets)

    def compare(self,setup,result,envs,selected=None):
        before,_=setup;enabled=[True]*len(envs) if selected is None else selected
        source=[env.serialize() for env in envs]
        oracle=gwrl_cpp.campaign_political_facts_oracle(before.context.native,envs,[],enabled,5)
        self.assertEqual(result.errors.cpu().tolist(),[row["error"] for row in oracle]);failed=any(row["error"] for row in oracle)
        self.assertEqual(result.committed.item(),not failed)
        for lane,row in enumerate(oracle):
            gold=gwrl_cpp.capture_device_states(before.context.native,[envs[lane]]) if failed else row["packed_state"]
            require_exact(self.raw(result.state,lane),canonical_native(gold))
        self.assertEqual([env.serialize() for env in envs],source)
        records=result.state.records.cpu().numpy()
        self.assertTrue(np.any((records[:,:,0]==4)&(records[:,:,2]==0)&(records[:,:,3]==0x80000000)))
        self.assertTrue(np.any((records[:,:,0]==4)&(records[:,:,2]==1)&(records[:,:,3]==0x3ff00000)))
        self.assertEqual(result.state.records.shape[1],self.capacities(setup).state_capacity)
        return oracle

    def rollback(self,before,result):
        self.assertFalse(result.committed.item());self.assertFalse(result.accepted.any().item());self.assertFalse(result.promoted.any().item())
        for name in ("records","string_bytes","string_offsets"):
            old,new=getattr(before,name),getattr(result.state,name);self.assertTrue(torch.equal(old,new[tuple(slice(0,n) for n in old.shape)]),name)
            if name=="records":self.assertEqual(new[:,old.shape[1]:].count_nonzero().item(),0)
            else:self.assertEqual(new[old.shape[0]:].count_nonzero().item(),0)
        for name in ("lengths","sections","errors","suffix_usage"):
            self.assertTrue(torch.equal(getattr(before,name),getattr(result.state,name)),name)

    def test_initial_opaque_state_and_later_major_surrendered_flags(self):
        def later(s):
            s["nations"]["ccp"].update(power_status="major");s["nations"]["kmt"].update(power_status="major")
            s["politics"]["surrendered"].append("kmt")
            s["nations"]["kmt"]["game_flags"]["surrendered"]=1
            s["territories"]["land_jap_tokyo"]["flags"].update(city_damage=39,city_ipp_lost=2)
        envs=[fixture(),fixture(mutate=later)];setup=self.setup(envs);result=self.call(setup);self.compare(setup,result,envs)
        self.assertEqual(result.promoted.cpu().tolist(),[[False,False],[False,False]])
        actual=[json.loads(env.serialize())["state"] for env in result.state.restore_envs()]
        for state,old in zip(actual,envs,strict=True):
            prior=json.loads(old.serialize())["state"]
            for name in ("history","clock","action_interface","turn_start","completed_turns"):
                self.assertEqual(name in state,name in prior,name)
                if name in prior:self.assertEqual(state[name],prior[name],name)
            for nation in state["nations"]:self.assertEqual(state["nations"][nation]["game_flags"]["possessed_land_ipp"],total(state,nation))

    def test_simultaneous_promotions_keep_first_truce_minor_flag_and_choice_order(self):
        env=fixture(mutate=mixed_promotions);setup=self.setup([env]);result=self.call(setup);self.compare(setup,result,[env])
        self.assertEqual(result.promoted.cpu().tolist(),[[True,True]])
        state=json.loads(result.state.restore_envs()[0].serialize())["state"]
        self.assertEqual([decision["nation"] for decision in state["decisions"]],["ccp","kmt"])
        battles=[b for b in state["battles"].values() if b["flags"].get("chinese_truce_termination")]
        self.assertEqual(len(battles),1);self.assertEqual(battles[0]["attacker"],"kmt")
        self.assertEqual(battles[0]["flags"]["truce_low_morale_eliminates"],1)
        self.assertTrue(all(state["nations"][nation]["power_status"]=="major" for nation in ("ccp","kmt")))
        self.assertTrue(all(state["units"]["refresh_mixed_"+nation]["movement_remaining"]==0 for nation in ("ccp","kmt")))
        self.assertFalse(state["politics"]["chinese_truce"]);self.assertTrue(state["politics"]["truce_permanently_ended"])

    def test_surrender_cargo_removal_does_not_revisit_earlier_civil_flag(self):
        def source(s):
            no_kmt_land(s)
            carrier=copy.deepcopy(next(u for u in s["units"].values() if u["type"]=="naval_transport"))
            cargo=copy.deepcopy(next(u for u in s["units"].values() if u["type"]=="infantry"))
            carrier.update(id="refresh_carrier",owner="kmt",cargo=["refresh_cargo"],carried_by=None)
            cargo.update(id="refresh_cargo",owner="ccp",zone=carrier["zone"],turn_origin=carrier["zone"],route=[],cargo=[],carried_by="refresh_carrier")
            s["units"]={carrier["id"]:carrier,cargo["id"]:cargo}
        env=fixture(mutate=source);setup=self.setup([env]);result=self.call(setup);self.compare(setup,result,[env])
        state=json.loads(result.state.restore_envs()[0].serialize())["state"]
        self.assertEqual(state["units"],{});self.assertEqual(state["nations"]["ccp"]["game_flags"]["civil_war_eliminated"],0)
        self.assertEqual(state["nations"]["kmt"]["game_flags"]["civil_war_eliminated"],0)
        self.assertIn("kmt",state["politics"]["surrendered"]);self.assertEqual(state["nations"]["ccp"]["game_flags"]["one_china_bonus_awarded"],1)
        awards=[p for p in state["construction"].values() if p["flags"].get("national_objective_award")]
        self.assertEqual([p["type"] for p in awards],["cavalry"]*3+["infantry"]*2)

    def test_pending_or_awarded_choice_skips_counter_but_does_not_skip_promotion(self):
        def awarded(s):give(s,"ccp");s["politics"]["evolution_awarded"].append("ccp")
        def pending(s):give(s,"ccp");s["flags"]["evolution_pending_ccp"]=-7
        envs=[fixture(mutate=awarded,sequence=2**31-1),fixture(mutate=pending,sequence=2**31-1)]
        setup=self.setup(envs);result=self.call(setup);self.compare(setup,result,envs)
        self.assertEqual(result.promoted.cpu().tolist(),[[True,False],[True,False]])
        for env in result.state.restore_envs():
            state=json.loads(env.serialize())["state"];self.assertEqual(state["decisions"],[])
            self.assertEqual(state["flags"]["politics_sequence"],2**31-1)

    def test_absent_dormant_chinese_nations_skip_tiny_fact_queries(self):
        for nation in ("ccp","kmt"):
            with self.subTest(nation=nation):
                env=gwrl_cpp._campaign_political_facts_absent_test_fixture(fixture(),nation)
                setup=self.setup([env]);result=self.call(setup);self.compare(setup,result,[env])
                self.assertFalse(result.attempted[nation+"_civil"].any().item())
                self.assertFalse(result.attempted[nation+"_promotion"].any().item())
                self.assertFalse(result.promoted[0,("ccp","kmt").index(nation)].item())

    def test_lazy_last_conqueror_only_read_when_kmt_really_surrenders(self):
        def retained(s):s["politics"]["pending"]["last_conqueror_kmt"]={"invalid_if_reached":True}
        env=fixture(mutate=retained);setup=self.setup([env]);self.compare(setup,self.call(setup),[env])
        def invalid(s):retained(s);no_kmt_land(s)
        env=fixture(mutate=invalid);setup=self.setup([env]);result=self.call(setup);self.compare(setup,result,[env]);self.rollback(setup[0],result)
        self.assertEqual(result.stage_errors["surrender_plan"].cpu().tolist(),[2])
        self.assertFalse(result.attempted["kmt_surrender"].any().item());self.assertFalse(result.attempted["allies"].any().item())
        def valid(s):no_kmt_land(s);s["politics"]["pending"]["last_conqueror_kmt"]="japan"
        env=fixture(mutate=valid);setup=self.setup([env]);self.compare(setup,self.call(setup),[env])

    def test_failures_at_promotion_truce_choice_and_surrender_rollback_every_word(self):
        def serial(s):give(s,"ccp");s["clock"]["player_turn_serial"]=str(2**31)
        def duplicate(s):
            mixed_promotions(s);name="truce_shared_"+s["clock"]["player_turn_serial"]+"_"+HOPEH
            s["battles"][name]=dict(id=name,zone=HOPEH,attacker="ccp",defender="kmt",stage="retained",attackers=[],defenders=[],pending_hits={},flags={},data={})
            s["battle_order"].append(name)
        def chance(s):
            no_kmt_land(s);s["construction"]["kmt_ship"]=dict(id="kmt_ship",owner="kmt",type="destroyer",site=None,queue_position=2,paid_ipp=1,remaining_payments=[1],flags={})
            s["chance"]=dict(id="retained",purpose="fixture",nation="japan",continuation="retained",dice=[dict(sides=12,modifier=0,reroll_faces=[],max_rerolls=0)])
        cases=((fixture(mutate=serial),"ccp_promotion"),(fixture(mutate=duplicate),"ccp_truce"),
               (fixture(mutate=lambda s:give(s,"ccp"),sequence=2**31-1),"ccp_choice"),(fixture(mutate=chance),"kmt_surrender"))
        for env,stage in cases:
            with self.subTest(stage=stage):
                setup=self.setup([env]);result=self.call(setup);self.compare(setup,result,[env]);self.rollback(setup[0],result)
                self.assertEqual(result.stage_errors[stage].cpu().tolist(),[2]);self.assertGreater(result.first_failure_stage.item(),0)
                self.assertFalse(result.attempted["allies"].any().item())

    def test_catalog_after_promotion_and_absent_allowance_are_native_helper_semantics(self):
        def due(s):
            give(s,"ccp");unit=next(u for u in s["units"].values() if u["owner"]=="ccp");unit["type"]="infantry"
        def conditional(source):
            creation_tests.conditional_catalog(source,invalid=True)
            for document in source.values():
                for unit in document.get("units",[]):
                    if unit["id"]=="infantry":unit["rules"][0]["parameters"]["requires_flags"]=["objective_evolution"]
        # The fresh promotion flag, rather than an original-source flag, must
        # already be visible to the immediately following CatalogContext.
        env=fixture(mutate=due,catalog=conditional)
        setup=self.setup([env]);result=self.call(setup);self.compare(setup,result,[env]);self.rollback(setup[0],result)
        self.assertEqual(result.stage_errors["ccp_movement"].cpu().tolist(),[2])
        env=fixture(mutate=due,catalog=lambda source:creation_tests.conditional_catalog(source,absent=True))
        setup=self.setup([env]);result=self.call(setup);self.compare(setup,result,[env])
        with self.assertRaisesRegex(RuntimeError,"Catalog unit has unresolved movement"):result.state.to_native()

    def test_full_cohort_rollback_and_explicit_capacities_exact_retry(self):
        def bad(s):give(s,"ccp");s["clock"]["player_turn_serial"]=str(2**31)
        envs=[fixture(mutate=bad),fixture()];setup=self.setup(envs);result=self.call(setup)
        self.compare(setup,result,envs);self.rollback(setup[0],result)
        self.assertEqual(result.errors.cpu().tolist(),[2,0])
        env=fixture(mutate=mixed_promotions);setup=self.setup([env]);before,_=setup;caps=self.capacities(setup);good=self.call(setup,capacities=caps)
        self.compare(setup,good,[env])
        T,A=good.required_string_usage.cpu().tolist();S=good.required_state_capacity.max().item();K=good.required_block_capacity.max().item()
        for change in (dict(state_capacity=max(before.records.shape[1],S-1)),dict(block_capacity=K-1),
                       dict(string_capacity=max(before.string_offsets.numel()-1,T-1)),dict(byte_capacity=max(before.string_bytes.numel(),A-1)),
                       dict(movement_unit_capacity=0),dict(truce_battle_capacity=0),dict(evolution_option_capacity=0)):
            with self.subTest(change=change):
                failed=self.call(setup,capacities=replace(caps,**change));self.rollback(before,failed);self.assertIn(5,failed.errors.cpu().tolist())
        exact=replace(caps,state_capacity=max(before.records.shape[1],S),block_capacity=K,string_capacity=T,byte_capacity=A)
        result=self.call(setup,capacities=exact)
        # This retry uses a smaller explicitly requested arena, never growth or
        # an altered action/state subset. Raw native equality is unchanged.
        oracle=gwrl_cpp.campaign_political_facts_oracle(before.context.native,[env],[],[True],5)
        self.assertTrue(result.committed.item());require_exact(self.raw(result.state,0),canonical_native(oracle[0]["packed_state"]))

    def test_no_hot_host_reads_source_binding_unselected_and_empty_batches(self):
        env=fixture(mutate=mixed_promotions);setup=self.setup([env]);before,service=setup;caps=self.capacities(setup);self.call(setup,capacities=caps)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("hot transfer")),patch.object(torch.Tensor,"item",side_effect=AssertionError("hot scalar")),\
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("hot list")),patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("hot bool")),\
             patch.object(json,"loads",side_effect=AssertionError("hot JSON")),patch.object(json,"dumps",side_effect=AssertionError("hot JSON")),\
             patch.object(gwrl_cpp,"campaign_political_facts_oracle",side_effect=AssertionError("CPU fallback")):
            result=self.call(setup,capacities=caps)
        self.compare(setup,result,[env]);self.assertTrue(result.committed.item())
        disabled=self.call(setup,selected=[False],capacities=caps);self.compare(setup,disabled,[env],selected=[False])
        self.assertFalse(disabled.promoted.any().item());self.assertFalse(disabled.surrender_due.any().item())
        foreign=replace(before,context=DeviceStateContext(gwrl_cpp.device_state_context(env),"mps"))
        with self.assertRaisesRegex(ValueError,"source context differs"):service.refresh(foreign,capacities=caps)
        with self.assertRaisesRegex(ValueError,"contiguous resident bool"):service.refresh(before,torch.ones(1,dtype=torch.int64,device="mps"),capacities=caps)
        empty=DeviceStateBatch.capture([],context=before.context);empty_caps=service.reserve(empty,movement_unit_capacity=0,surrender_unit_capacity=0,
            surrender_project_capacity=0,truce_battle_capacity=0,evolution_option_capacity=0)
        result=service.refresh(empty,capacities=empty_caps);self.assertTrue(result.committed.item());self.assertEqual(result.state.lane_count,0)
