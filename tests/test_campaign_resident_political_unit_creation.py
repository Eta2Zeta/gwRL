"""Original addPoliticalUnit versus exact raw resident creation and rollback."""
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
from studies.campaign.backends.device_strings import pack_byte_requests,intern_bytes
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_catalog_stats import ResidentCatalogStatsContext
from studies.campaign.backends.resident_political_unit_creation import ResidentPoliticalUnitCreation
from tools.benchmark_campaign_resident_recruitment_chance import canonical_native,require_exact

SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"
EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def fixture(*,sequence=None,mutate=None,catalog=None):
    env=gwrl_cpp.CampaignEnv(str(SCENARIO),51)
    if catalog:
        source=json.loads(gwrl_cpp.campaign_catalog_stats_context(env)._test_source_json);catalog(source)
        env=gwrl_cpp._campaign_catalog_stats_test_fixture(env,json.dumps(source))
    doc=json.loads(env.serialize());state=doc["state"]
    if sequence is None:state["flags"].pop("politics_sequence",None)
    else:state["flags"]["politics_sequence"]=sequence
    if mutate:mutate(state)
    # Insert opaque signed zero only after every JSON fixture-authoring pass.
    state["politics"]["pending"]["creation_opaque"]={"negative_zero":-0.0,"precise":1.0000000000000002,"unknown":[None,True,"蒙古\u0000"]}
    doc["random"].update(actual=str(2**64-1),search=str(2**63+3),training=str(2**63+17),active="search",test_tape=[1,12],tape_position="1")
    env.restore(json.dumps(doc,ensure_ascii=False));return env


def conditional_catalog(source,*,invalid=False,absent=False):
    for document in source.values():
        for unit in document.get("units",[]):
            if unit["id"]=="infantry":
                if absent:
                    for row in unit["states"]:row["movement"]=None
                else:unit["rules"]=[{"id":"militia_conditional_movement","parameters":{
                    "requires_flags":["politics_sequence"],"conditional_movement":"invalid" if invalid else 7}}]
    # A freshly inserted unit has placed_this_turn in its own turnFlags, which
    # is deliberately NOT a CatalogContext input. Reading new Unit state here
    # would turn this harmless modifier into a native error after insertion.
    tech=next(t for t in source["technologies"]["technologies"] if t["id"]=="long_range_aircraft")
    tech["modifiers"]=[{"unit_types":["infantry"],"classes":[],"requires_flags":["placed_this_turn"],"stat":"must_stay_unreached","add":1}]


@unittest.skipUnless(EXACT,"Exact MPS required")
class ResidentPoliticalCreationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs,nations,types,zones):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        before=DeviceStateBatch.capture(envs,context=context)
        catalog=ResidentCatalogStatsContext(context,gwrl_cpp.campaign_catalog_stats_context(envs[0]))
        service=ResidentPoliticalUnitCreation(context,catalog)
        names=tuple(dict.fromkeys((*nations,*types,*zones)));tokens={};missing=[]
        for name in names:
            try:tokens[name]=int(context.prefix_lookup_ids((name,))[0])
            except IndexError:missing.append(name)
        if missing:
            data,lengths=pack_byte_requests([name.encode() for name in missing],device="mps")
            added=intern_bytes(before,data,lengths,string_capacity=before.string_offsets.numel()-1+len(missing),
                byte_capacity=before.string_bytes.numel()+data.numel())
            self.assertTrue(added.committed.item());before=added.state
            tokens.update(zip(missing,added.ids.cpu().tolist(),strict=True))
        vectors=[torch.tensor([tokens[name] for name in values],dtype=torch.int64,device="mps") for values in (nations,types,zones)]
        return before,service,vectors

    def raw(self,state,lane):
        length=state.lengths[lane].cpu().item();used,size=state.suffix_usage.cpu().tolist()
        rows=state.records[lane,:length].cpu().numpy().copy();data=state.string_bytes[:size].cpu().numpy().copy()
        offsets=state.string_offsets[:used+1].cpu().numpy().copy()
        return SimpleNamespace(context=state.context.native,record_array=lambda:rows,lane_offsets=lambda:np.array([0,length],dtype=np.int64),
            string_bytes=lambda:data,string_offsets=lambda:offsets)

    def assert_oracle(self,before,result,envs,nations,types,zones,counts,selected=None):
        enabled=[True]*len(envs) if selected is None else selected
        oracle=gwrl_cpp.campaign_add_political_unit_oracle(before.context.native,envs,nations,types,zones,counts,enabled)
        self.assertEqual(result.errors.cpu().tolist(),[row["error"] for row in oracle])
        failed=any(row["error"] for row in oracle)
        self.assertEqual(result.committed.item(),not failed)
        self.assertEqual(result.first_failure_ordinal.cpu().tolist(),[row["first_failure_ordinal"] for row in oracle])
        for lane,row in enumerate(oracle):
            golden=(gwrl_cpp.capture_device_states(before.context.native,[envs[lane]]) if failed else row["packed_state"])
            require_exact(self.raw(result.state,lane),canonical_native(golden))
        # No JSON roundtrip can erase this otherwise-hidden bit mismatch.
        rows=result.state.records.cpu().numpy()
        self.assertTrue(np.any((rows[:,:,0]==4)&(rows[:,:,2]==0)&(rows[:,:,3]==0x80000000)))
        return oracle

    def rollback(self,before,result):
        self.assertFalse(result.committed.item());self.assertFalse(result.accepted.any().item())
        for name in ("records","string_bytes","string_offsets"):
            old,new=getattr(before,name),getattr(result.state,name)
            slices=tuple(slice(0,n) for n in old.shape);self.assertTrue(torch.equal(new[slices],old),name)
            if name=="records":self.assertEqual(new[:,old.shape[1]:].count_nonzero().item(),0)
            else:self.assertEqual(new[old.shape[0]:].count_nonzero().item(),0)
        for name in ("lengths","sections","errors","suffix_usage"):self.assertTrue(torch.equal(getattr(before,name),getattr(result.state,name)),name)

    def call(self,setup,counts,*,selected=None,capacities=None):
        before,service,vectors=setup
        capacity=service.reserve(before,creation_capacity=max(counts,default=0)) if capacities is None else capacities
        return service.add(before,*vectors,torch.tensor(counts,dtype=torch.int64,device="mps"),
            None if selected is None else torch.tensor(selected,dtype=torch.bool,device="mps"),**capacity)

    def test_primary_types_multiple_owners_status_and_every_untouched_raw_word(self):
        first=fixture()
        major=fixture(mutate=lambda s:s["nations"]["ccp"].update(power_status="major"))
        initial=json.loads(first.serialize())["state"]
        minor=next(name for name in initial["nations"] if name.startswith("warlord_"))
        minor_zone=next(name for name,t in initial["territories"].items() if t["possessor"]==minor)
        envs=[first,first.clone(),major,first.clone()]
        nations=["japan","japan","ccp",minor];types=["infantry","cavalry","militia","militia"]
        zones=["land_jap_tokyo","land_jap_tokyo","land_china_shensi",minor_zone];counts=[3,2,2,2]
        setup=self.setup(envs,nations,types,zones);source=[env.serialize() for env in envs]
        result=self.call(setup,counts);self.assert_oracle(setup[0],result,envs,nations,types,zones,counts)
        self.assertEqual(result.inserted_counts.cpu().tolist(),counts);self.assertEqual([env.serialize() for env in envs],source)
        actual=[json.loads(env.serialize())["state"] for env in result.state.restore_envs()]
        self.assertEqual(actual[0]["flags"]["politics_sequence"],3)
        for lane in range(len(envs)):
            new=[u for name,u in actual[lane]["units"].items() if name.startswith("political_")]
            self.assertEqual(len(new),counts[lane]);self.assertTrue(all(u["movement_remaining"]==0 and u["turn_flags"]=={"placed_this_turn":1} for u in new))

    def test_count_possession_lookup_guards_and_unselected_lazy_inputs(self):
        env=fixture();envs=[env]*5;nations=["japan"]*5;types=["missing_type"]*5
        zones=["missing_zone","missing_zone","land_china_shensi","land_jap_tokyo","missing_zone"];counts=[0,1,1,1,-1]
        setup=self.setup(envs,nations,types,zones);result=self.call(setup,counts,selected=[True,True,True,True,False])
        self.assert_oracle(setup[0],result,envs,nations,types,zones,counts,[True,True,True,True,False]);self.rollback(setup[0],result)
        self.assertEqual(result.errors.cpu().tolist(),[2,1,2,1,0])
        self.assertEqual(result.query_errors[-1].cpu().tolist(),[0,0])

    def test_signed_sequence_crossings_overflow_order_and_emplace_collisions(self):
        def collision(s):
            unit=copy.deepcopy(next(u for u in s["units"].values() if u["type"]=="infantry" and not u["cargo"] and u["carried_by"] is None))
            unit.update(id="political_infantry_1",turn_flags={"collision_preserved":17})
            s["units"][unit["id"]]=unit
        first=fixture(mutate=collision);envs=[first,fixture(sequence=-3),fixture(sequence=-(2**31))]
        nations=["japan"]*3;types=["infantry"]*3;zones=["land_jap_tokyo"]*3;counts=[3,5,2]
        setup=self.setup(envs,nations,types,zones);result=self.call(setup,counts)
        self.assert_oracle(setup[0],result,envs,nations,types,zones,counts)
        self.assertEqual(result.collision_mask[0,:3].cpu().tolist(),[True,False,False]);self.assertEqual(result.inserted_counts.cpu().tolist(),[2,5,2])
        envs=[fixture(sequence=2**31-2),fixture(sequence=2**31-1),fixture(sequence=2**31-2)]
        types=["infantry","missing_type","missing_type"];counts=[2,1,3]
        setup=self.setup(envs,nations,types,zones);result=self.call(setup,counts)
        self.assert_oracle(setup[0],result,envs,nations,types,zones,counts);self.rollback(setup[0],result)
        self.assertEqual(result.errors.cpu().tolist(),[2,2,1]);self.assertEqual(result.first_failure_ordinal.cpu().tolist(),[2,1,1])
        self.assertEqual(result.query_errors[1].cpu().tolist(),[0,0])
        def unknown_collision(s):
            unit=copy.deepcopy(next(u for u in s["units"].values() if u["type"]=="infantry" and not u["cargo"] and u["carried_by"] is None))
            unit["id"]="political_missing_type_1"
            s["units"][unit["id"]]=unit
        existing=fixture(mutate=unknown_collision)
        setup=self.setup([existing],["japan"],["missing_type"],["land_jap_tokyo"]);result=self.call(setup,[1])
        self.assert_oracle(setup[0],result,[existing],["japan"],["missing_type"],["land_jap_tokyo"],[1])
        self.assertEqual(result.query_errors.cpu().tolist(),[[1,0]],"An emplace collision must not bypass the preceding Catalog lookup")

    def test_counter_context_categories_use_actual_flags_not_inserted_unit_flags(self):
        def ready(s):s["nations"]["japan"]["technology_stages"]["long_range_aircraft"]=4
        base=fixture(sequence=-2,mutate=ready,catalog=conditional_catalog)
        # Keep one frozen Catalog/definition while changing only original State
        # flags; these override the global counter according to native order.
        envs=[base]
        for game,turn in ((0,None),(0,1)):
            doc=json.loads(base.serialize());s=doc["state"];s["nations"]["japan"]["game_flags"]["politics_sequence"]=game
            if turn is not None:s["nations"]["japan"]["turn_flags"]["politics_sequence"]=turn
            s["politics"]["pending"]["creation_opaque"]["negative_zero"]=-0.0
            child=base.clone();child.restore(json.dumps(doc));envs.append(child)
        nations=["japan"]*3;types=["infantry"]*3;zones=["land_jap_tokyo"]*3;counts=[4]*3
        setup=self.setup(envs,nations,types,zones);result=self.call(setup,counts)
        self.assert_oracle(setup[0],result,envs,nations,types,zones,counts)
        actual=[json.loads(env.serialize())["state"] for env in result.state.restore_envs()]
        names=["political_infantry_-1","political_infantry_0","political_infantry_1","political_infantry_2"]
        self.assertEqual([[s["units"][name]["movement_allowance"] for name in names] for s in actual],[[7,1,7,7],[1,1,1,1],[7,7,7,7]])

    def test_lazy_first_catalog_failure_and_opposite_category_failure_order(self):
        base=fixture(sequence=-1,catalog=lambda source:conditional_catalog(source,invalid=True))
        doc=json.loads(base.serialize());doc["state"]["flags"]["politics_sequence"]=-2
        doc["state"]["politics"]["pending"]["creation_opaque"]["negative_zero"]=-0.0
        second=base.clone();second.restore(json.dumps(doc));envs=[base,second]
        nations=["japan"]*2;types=["infantry"]*2;zones=["land_jap_tokyo"]*2;counts=[3,3]
        setup=self.setup(envs,nations,types,zones);result=self.call(setup,counts)
        self.assert_oracle(setup[0],result,envs,nations,types,zones,counts);self.rollback(setup[0],result)
        self.assertEqual(result.first_failure_ordinal.cpu().tolist(),[2,1])
        self.assertEqual(result.query_errors[1].cpu().tolist(),[2,0],"Later category must not be queried after the first native failure")

    def test_absent_allowance_matches_raw_native_helper_without_outer_engine_validation(self):
        env=fixture(catalog=lambda source:conditional_catalog(source,absent=True))
        nations=["japan"];types=["infantry"];zones=["land_jap_tokyo"];counts=[2]
        setup=self.setup([env],nations,types,zones);result=self.call(setup,counts)
        self.assert_oracle(setup[0],result,[env],nations,types,zones,counts)
        with self.assertRaisesRegex(RuntimeError,"Catalog unit has unresolved movement"):result.state.to_native()

    def test_every_explicit_capacity_rolls_back_and_reports_exact_retry_sizes(self):
        env=fixture();setup=self.setup([env],["japan"],["infantry"],["land_jap_tokyo"])
        before,service,_=setup;fixed=service.reserve(before,creation_capacity=3);good=self.call(setup,[3],capacities=fixed)
        self.assertTrue(good.committed.item())
        state=good.required_state_capacity.item();block=good.required_block_capacity.item();strings,bytes_=good.required_string_usage.cpu().tolist()
        L=good.required_id_bytes.item()
        shortages=({"creation_capacity":2},{"id_byte_capacity":L-1},{"state_capacity":max(before.records.shape[1],state-1)},
                   {"block_capacity":block-1},{"string_capacity":max(before.string_offsets.numel()-1,strings-1)},
                   {"byte_capacity":max(before.string_bytes.numel(),bytes_-1)})
        for short in shortages:
            with self.subTest(short=short):
                options={**fixed,**short};failed=self.call(setup,[3],capacities=options);self.rollback(before,failed)
                self.assertEqual(failed.errors.cpu().tolist(),[5]);self.assertEqual(failed.required_creation_capacity.cpu().tolist(),[3])
        exact={**fixed,"id_byte_capacity":L,"state_capacity":max(before.records.shape[1],state),"block_capacity":block,
               "string_capacity":strings,"byte_capacity":bytes_}
        result=self.call(setup,[3],capacities=exact);self.assert_oracle(before,result,[env],["japan"],["infantry"],["land_jap_tokyo"],[3])

    def test_no_hot_host_json_or_native_calls_and_selected_false_empty_inputs(self):
        env=fixture(sequence=-2);setup=self.setup([env],["japan"],["infantry"],["land_jap_tokyo"])
        before,service,vectors=setup;fixed=service.reserve(before,creation_capacity=4);self.call(setup,[4],capacities=fixed)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host list")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(json,"loads",side_effect=AssertionError("JSON hot path")), \
             patch.object(gwrl_cpp,"campaign_add_political_unit_oracle",side_effect=AssertionError("Native fallback")), \
             patch.object(service.catalog_stats,"all_units",side_effect=AssertionError("Inserted inventory is not a CatalogContext input")):
            result=self.call(setup,[4],capacities=fixed)
        self.assert_oracle(before,result,[env],["japan"],["infantry"],["land_jap_tokyo"],[4])
        invalid=torch.full((1,),-1,dtype=torch.int64,device="mps")
        idle=service.add(before,invalid,invalid,invalid,torch.full((1,),2**40,dtype=torch.int64,device="mps"),
            torch.zeros(1,dtype=torch.bool,device="mps"),**fixed)
        self.assertTrue(idle.committed.item());require_exact(self.raw(idle.state,0),canonical_native(self.raw(before,0)))
        empty=DeviceStateBatch.capture([],context=before.context);zero=torch.zeros(0,dtype=torch.int64,device="mps")
        result=service.add(empty,zero,zero,zero,zero,**service.reserve(empty,creation_capacity=0))
        self.assertTrue(result.committed.item());self.assertEqual(result.state.lane_count,0)


if __name__=="__main__":unittest.main()
