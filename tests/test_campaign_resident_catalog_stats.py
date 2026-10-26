"""Primary native Catalog parity, lazy exceptions and complete resident queries."""
from dataclasses import replace
from pathlib import Path
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.device_map_edits import MapMode,build_map_edits,commit_container_edits
from studies.campaign.backends.device_strings import intern_bytes,pack_byte_requests
from studies.campaign.backends.resident_catalog_stats import (
    STAT_NAMES,CAPACITY_ERROR,PACKED_ERROR,INT_OVERFLOW,ResidentCatalogStatsContext)
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from tests.test_campaign_device_state import rich_fixture,real_states
from tests.test_campaign_device_map_edits import lookup,child,scalar

SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"
EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def changed(env,mutate):
    doc=json.loads(env.serialize());mutate(doc["state"])
    result=env.clone();result.restore(json.dumps(doc,separators=(",",":")));return result


@unittest.skipUnless(EXACT_MPS,"Lossless MPS indexing unavailable")
class ResidentCatalogStatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads=torch.get_num_threads();torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old_threads)

    def setup(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        state=DeviceStateBatch.capture(envs,context=context)
        native=gwrl_cpp.campaign_catalog_stats_context(envs[0])
        return state,ResidentCatalogStatsContext(context,native),native

    def query(self,state,context,queries,*,guards=False):
        names=tuple(dict.fromkeys(text for _,type,_,owner,zone in queries for text in (type,owner,zone) if text is not None))
        data,lengths=pack_byte_requests([text.encode() for text in names],device="mps")
        interned=intern_bytes(state,data,lengths,string_capacity=state.string_offsets.numel()-1+len(names),
            byte_capacity=state.string_bytes.numel()+data.numel())
        # Test authoring may inspect IDs; the execution below uses no host data.
        ids=dict(zip(names,interned.ids.cpu().tolist(),strict=True))
        requests=torch.tensor([[lane,ids[type],damage,ids[owner],-1 if zone is None else ids[zone]]
            for lane,type,damage,owner,zone in queries],dtype=torch.int64,device="mps").reshape(len(queries),5)
        if not guards:return context.query(interned.state,requests)
        context.query(interned.state,requests)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host tensor transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host tensor values")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host tensor scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(json,"loads",side_effect=AssertionError("JSON hot path")), \
             patch.object(gwrl_cpp,"campaign_catalog_stats_oracle",side_effect=AssertionError("Native fallback")), \
             patch.object(gwrl_cpp,"capture_device_states",side_effect=AssertionError("Native recapture")):
            return context.query(interned.state,requests)

    def assert_oracle(self,result,native,envs,queries,*,overrides=None):
        oracle=(gwrl_cpp.campaign_catalog_stats_oracle(native,envs,queries) if overrides is None else
                gwrl_cpp._campaign_catalog_stats_test_oracle(native,envs,queries,overrides))
        n=len(queries)
        self.assertEqual(result.batch_error.cpu().tolist(),[0])
        np.testing.assert_array_equal(result.errors[:n].cpu().numpy(),oracle.error_array())
        np.testing.assert_array_equal(result.stats[:n].cpu().numpy(),oracle.stat_array())
        for error,message_id,message in zip(result.errors[:n].cpu().tolist(),result.message_ids[:n].cpu().tolist(),oracle.messages,strict=True):
            if error in (1,2):self.assertEqual(native.messages[message_id],message)
        return oracle

    def test_all_primary_types_and_surviving_damage_states_keep_every_optional_field(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),91)
        state,context,native=self.setup([env])
        meta,states=native.unit_array(),native.state_array()
        queries=[]
        for name,row in zip(native.unit_types,meta,strict=True):
            for damage in states[row[0]:row[0]+row[1],0]:queries.append((0,name,int(damage),"japan","land_jap_tokyo"))
        before=state.records.clone();source=env.serialize()
        result=self.query(state,context,queries,guards=True)
        self.assert_oracle(result,native,[env],queries)
        output=context.inspect(result)
        self.assertTrue(any(value["attack"] is None for value in output))
        self.assertTrue(any(value["bombardment"] is not None for value in output))
        self.assertTrue(all(value[name] is not None for value in output for name in ("attack_dice","defense_dice","bombardment_dice")))
        self.assertTrue(torch.equal(before,state.records));self.assertEqual(env.serialize(),source)

    def test_stage_four_and_flag_override_order_match_native(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),5)
        def configured(state):
            state["nations"]["japan"]["technology_stages"].update(anti_submarine_warfare=4,long_range_aircraft=4)
            state["flags"].update(on_maritime_air_patrol=1,target_is_submarine=-1)
        ready=changed(first,configured)
        envs=[ready,changed(ready,lambda s:s["nations"]["japan"]["game_flags"].update(on_maritime_air_patrol=0)),
              changed(ready,lambda s:s["nations"]["japan"].update(technology_stages={"anti_submarine_warfare":3,"long_range_aircraft":3}))]
        envs.append(changed(envs[1],lambda s:s["nations"]["japan"]["turn_flags"].update(on_maritime_air_patrol=1)))
        envs.append(changed(ready,lambda s:s["nations"]["japan"]["turn_flags"].update(on_maritime_air_patrol=0)))
        state,context,native=self.setup(envs)
        queries=[(lane,"seaplane",0,"japan","land_jap_tokyo") for lane in range(len(envs))]
        result=self.query(state,context,queries);self.assert_oracle(result,native,envs,queries)
        values=context.inspect(result)
        self.assertEqual(values[0]["attack"],values[1]["attack"]+2)
        self.assertEqual(values[0]["attack"],values[3]["attack"])
        self.assertEqual(values[1]["attack"],values[4]["attack"])
        self.assertEqual(values[0]["movement"],values[2]["movement"]+1)

    def test_derived_major_home_flags_override_explicit_flags_and_optional_zone(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),11)
        def forged(state):
            state["flags"].update(owner_is_major_power=1,movement_starts_in_owner_home_country=1,movement_ends_in_owner_home_country=1)
            state["nations"]["japan"]["turn_flags"].update(owner_is_major_power=0,movement_starts_in_owner_home_country=0)
        env=changed(first,forged);state,context,native=self.setup([env])
        queries=[(0,"militia",0,"japan","land_jap_tokyo"),(0,"militia",0,"japan","land_china_shensi"),
                 (0,"militia",0,"japan",None),(0,"militia",0,"kmt","land_china_shensi"),
                 (0,"militia",0,"japan","unknown_zone_is_not_home")]
        result=self.query(state,context,queries);self.assert_oracle(result,native,[env],queries)
        values=context.inspect(result)
        self.assertEqual(values[0]["movement"],1)
        self.assertNotEqual(values[1]["movement"],1)
        self.assertNotEqual(values[3]["movement"],1)
        self.assertEqual(values[1]["movement"],values[4]["movement"])

    def test_every_current_unit_variable_inventory_capacity_retry_and_empty_batch(self):
        envs=[*real_states(),rich_fixture()]
        state,context,native=self.setup(envs)
        queries=[(lane,unit["type"],unit["damage"],unit["owner"],unit["zone"]) for lane,env in enumerate(envs)
                 for _,unit in sorted(json.loads(env.serialize())["state"]["units"].items())]
        before=state.records.clone();result=context.all_units(state)
        self.assertEqual(result.count.cpu().item(),len(queries));self.assertEqual(result.required_count.cpu().item(),len(queries))
        self.assert_oracle(result,native,envs,queries)
        self.assertTrue(torch.equal(before,state.records))
        short=context.all_units(state,capacity=len(queries)-1)
        self.assertEqual(short.batch_error.cpu().tolist(),[CAPACITY_ERROR]);self.assertEqual(short.count.cpu().tolist(),[0])
        self.assertEqual(short.required_count.cpu().tolist(),[len(queries)])
        with self.assertRaises(BufferError):context.inspect(short)
        exact=context.all_units(state,capacity=len(queries));self.assert_oracle(exact,native,envs,queries)
        empty=DeviceStateBatch.capture([],context=state.context)
        result=context.all_units(empty);self.assertEqual(context.inspect(result),[]);self.assertEqual(result.count.cpu().tolist(),[0])

    def test_unknown_type_damage_and_owner_errors_match_native(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),17);state,context,native=self.setup([env])
        queries=[(0,"missing_unit",0,"japan",None),(0,"militia",-1,"japan",None),(0,"militia",99,"japan",None),
                 (0,"militia",0,"missing_owner",None)]
        result=self.query(state,context,queries);self.assert_oracle(result,native,[env],queries)
        self.assertEqual(result.errors.cpu().tolist(),[1]*len(queries))
        with self.assertRaises(IndexError):context.inspect(result)
        with self.assertRaises(ValueError):gwrl_cpp.campaign_catalog_stats_oracle(None,[env],queries)

    def fixture_catalog(self,mutate):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),23)
        native=gwrl_cpp.campaign_catalog_stats_context(env);source=json.loads(native._test_source_json)
        mutate(source)
        result=gwrl_cpp._campaign_catalog_stats_test_fixture(env,json.dumps(source,separators=(",",":")))
        self.assertNotEqual(json.loads(env.serialize())["state"]["definition_fingerprint"],json.loads(result.serialize())["state"]["definition_fingerprint"])
        self.assertEqual(json.loads(env.serialize())["random"],json.loads(result.serialize())["random"])
        return result

    def test_lazy_modifier_flags_unknown_stat_and_disabled_closed_theatre_flags(self):
        def custom(source):
            tech=next(t for t in source["technologies"]["technologies"] if t["id"]=="long_range_aircraft")
            tech["modifiers"]=[
                {"unit_types":["seaplane"],"classes":[],"requires_flags":["ccp_soviet_rail_production"],"add":100,"stat":"attack"},
                {"unit_types":["seaplane"],"classes":[],"requires_flags":["kmt_burma_road"],"add":100,"stat":"attack"},
                {"unit_types":["seaplane"],"classes":[],"requires_flags":["gate",None],"add":1,"stat":"missing_stat"},
            ]
        original=self.fixture_catalog(custom)
        def ready(state):
            state["nations"]["japan"]["technology_stages"]["long_range_aircraft"]=4
            state["flags"].update(ccp_soviet_rail_production=1,kmt_burma_road=1,gate=0)
        first=changed(original,ready);second=changed(first,lambda state:state["flags"].update(gate=1))
        state,context,native=self.setup([first,second])
        queries=[(0,"seaplane",0,"japan",None),(1,"seaplane",0,"japan",None),(1,"militia",0,"japan",None)]
        result=self.query(state,context,queries);self.assert_oracle(result,native,[first,second],queries)
        self.assertEqual(result.errors.cpu().tolist(),[0,2,0])
        # A false first flag must hide the malformed later flag. Matching unit
        # types also hide add/stat reads until all flags have succeeded.
        def unknown_stat(source):
            tech=next(t for t in source["technologies"]["technologies"] if t["id"]=="long_range_aircraft")
            tech["modifiers"]=[{"unit_types":["seaplane"],"classes":[],"requires_flags":["gate"],"add":1,"stat":"missing_stat"}]
        original=self.fixture_catalog(unknown_stat)
        first=changed(original,ready);second=changed(first,lambda state:state["flags"].update(gate=1))
        state,context,native=self.setup([first,second]);result=self.query(state,context,queries)
        self.assert_oracle(result,native,[first,second],queries);self.assertEqual(result.errors.cpu().tolist(),[0,2,0])

    def test_lazy_malformed_unit_rules_modifiers_and_unknown_technology_order(self):
        def malformed(source):
            tech=next(t for t in source["technologies"]["technologies"] if t["id"]=="long_range_aircraft")
            tech["modifiers"]=[{"unit_types":["seaplane","seaplane"],"classes":[],"stat":"attack","add":1}]
        first=self.fixture_catalog(malformed)
        second=changed(first,lambda state:state["nations"]["japan"]["technology_stages"].update(long_range_aircraft=4))
        state,context,native=self.setup([first,second])
        queries=[(0,"militia",0,"japan",None),(1,"militia",0,"japan",None),(1,"militia",99,"japan",None)]
        result=self.query(state,context,queries);self.assert_oracle(result,native,[first,second],queries)
        self.assertEqual(result.errors.cpu().tolist(),[0,2,1])
        # The completed unknown technology is an invalid temporary State that
        # normal ingress rejects. Construct it through the internal structural
        # editor and compare the explicit diagnostic clone-override oracle.
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),31);state,context,native=self.setup([first])
        data,lengths=pack_byte_requests([b"000_unknown_technology"],device="mps")
        pool=intern_bytes(state,data,lengths,string_capacity=state.string_offsets.numel(),byte_capacity=state.string_bytes.numel()+data.numel())
        state=pool.state;nations=state.section("state.nations")[0].cpu().item()
        japan=lookup(state,nations,"japan");technology=child(state,japan,7)
        query=[(0,"militia",0,"japan",None),(0,"militia",99,"japan",None)]
        for stage,error in ((3,0),(4,1)):
            build=build_map_edits(state,torch.tensor([technology],device="mps"),pool.ids,torch.tensor([MapMode.UPSERT],device="mps"),
                torch.tensor([[scalar(2,stage)]],device="mps"),torch.tensor([1],device="mps"),torch.tensor([True],device="mps"))
            temporary=commit_container_edits(build,capacity=state.records.shape[1]+2).state
            result=self.query(temporary,context,query)
            self.assert_oracle(result,native,[first],query,overrides={"000_unknown_technology":stage})
            self.assertEqual(result.errors.cpu().tolist(),[error,1])

    def test_completed_inventory_path_has_no_host_reads_and_rejects_stale_or_corrupt_layouts(self):
        env=rich_fixture();state,context,native=self.setup([env]);context.all_units(state)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host values")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")):
            result=context.all_units(state)
        self.assertEqual(result.batch_error.cpu().tolist(),[0])
        bad=replace(state,errors=torch.ones_like(state.errors));result=context.all_units(bad)
        self.assertEqual(result.batch_error.cpu().tolist(),[PACKED_ERROR]);self.assertEqual(result.count.cpu().tolist(),[0])
        different=gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO),9,1)
        with self.assertRaises(ValueError):context.all_units(DeviceStateBatch.capture([different],device="mps"))
        requests=torch.zeros((2,10),dtype=torch.int64,device="mps")[:,::2]
        with self.assertRaises(ValueError):context.query(state,requests)
        requests=torch.zeros((1,5),dtype=torch.int64,device="mps")
        invalid=context.query(state,requests,count=torch.tensor([2],dtype=torch.int64,device="mps"))
        self.assertEqual(invalid.batch_error.cpu().tolist(),[PACKED_ERROR])

    def test_lazy_unit_rule_and_modifier_container_errors_keep_original_order(self):
        def broken_rules(source):
            unit=next(u for u in source["land_air"]["units"] if u["id"]=="militia")
            unit["rules"]={"not":"an array"}
        env=self.fixture_catalog(broken_rules);state,context,native=self.setup([env])
        queries=[(0,"militia",0,"japan",None),(0,"militia",99,"japan",None),(0,"seaplane",0,"japan",None)]
        result=self.query(state,context,queries);self.assert_oracle(result,native,[env],queries)
        self.assertEqual(result.errors.cpu().tolist(),[2,1,0])
        def conditional(source):
            unit=next(u for u in source["land_air"]["units"] if u["id"]=="militia")
            unit["rules"]=[{"id":"militia_conditional_movement","parameters":{
                "requires_flags":["gate"],"conditional_movement":"not an integer"}}]
        original=self.fixture_catalog(conditional)
        first=changed(original,lambda state:state["flags"].update(gate=0))
        second=changed(original,lambda state:state["flags"].update(gate=1))
        state,context,native=self.setup([first,second])
        queries=[(0,"militia",0,"japan",None),(1,"militia",0,"japan",None)]
        result=self.query(state,context,queries);self.assert_oracle(result,native,[first,second],queries)
        self.assertEqual(result.errors.cpu().tolist(),[0,2])
        def wrong_modifier_container(source):
            tech=next(t for t in source["technologies"]["technologies"] if t["id"]=="long_range_aircraft")
            tech["modifiers"]={"not":"an array"}
        original=self.fixture_catalog(wrong_modifier_container)
        first=changed(original,lambda state:state["nations"]["japan"]["technology_stages"].update(long_range_aircraft=3))
        second=changed(original,lambda state:state["nations"]["japan"]["technology_stages"].update(long_range_aircraft=4))
        state,context,native=self.setup([first,second])
        result=self.query(state,context,queries);self.assert_oracle(result,native,[first,second],queries)
        self.assertEqual(result.errors.cpu().tolist(),[0,2])

    def test_overflow_is_explicit_but_absent_optional_stat_does_not_add(self):
        def overflowing(source):
            tech=next(t for t in source["technologies"]["technologies"] if t["id"]=="long_range_aircraft")
            tech["modifiers"]=[{"unit_types":["seaplane","militia"],"classes":[],"requires_flags":[],"stat":"attack","add":2**31-1}]
        original=self.fixture_catalog(overflowing)
        env=changed(original,lambda state:state["nations"]["japan"]["technology_stages"].update(long_range_aircraft=4))
        state,context,native=self.setup([env]);before=state.records.clone()
        result=self.query(state,context,[(0,"seaplane",0,"japan",None)])
        self.assertEqual(result.errors.cpu().tolist(),[INT_OVERFLOW])
        with self.assertRaises(OverflowError):context.inspect(result)
        # The original C++ would have undefined signed overflow above, so never
        # call that oracle. Its optional-absent branch below is fully defined.
        queries=[(0,"militia",0,"japan",None)]
        result=self.query(state,context,queries);self.assert_oracle(result,native,[env],queries)
        self.assertIsNone(context.inspect(result)[0]["attack"])
        self.assertTrue(torch.equal(state.records,before))


if __name__=="__main__":unittest.main()
