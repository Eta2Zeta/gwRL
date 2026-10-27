"""Original political movement helper versus selected-owner resident updates."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext,SECTION_NAMES
from studies.campaign.backends.device_state_edits import replace_subtrees
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_catalog_stats import ResidentCatalogStatsContext
from studies.campaign.backends.resident_political_units import ResidentPoliticalUnits
from studies.campaign.backends.resident_state_json import ResidentStateJson
from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
from tests.test_campaign_device_state import rich_fixture,real_states
from tests.test_campaign_device_map_edits import lookup,child,scalar
from tests.test_campaign_resident_catalog_stats import SCENARIO,changed

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def catalog_fixture(mutate):
    env=gwrl_cpp.CampaignEnv(str(SCENARIO),23)
    source=json.loads(gwrl_cpp.campaign_catalog_stats_context(env)._test_source_json);mutate(source)
    return gwrl_cpp._campaign_catalog_stats_test_fixture(env,json.dumps(source,separators=(",",":")))


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU execution unavailable")
class ResidentPoliticalUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs,owners):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        native=gwrl_cpp.capture_device_states(context.native,envs);state=DeviceStateBatch.from_native(native,context=context)
        stats=ResidentCatalogStatsContext(context,gwrl_cpp.campaign_catalog_stats_context(envs[0]))
        service=ResidentPoliticalUnits(context,stats)
        ids=torch.tensor(context.prefix_lookup_ids(owners),dtype=torch.int64,device="mps")
        formatter=ResidentStateJson(CanonicalJsonContext(native,context))
        return state,service,ids,formatter

    def assert_native(self,state,result,envs,owners,formatter,*,selected=None,overrides=None,valid_output=True):
        enabled=[True]*len(envs) if selected is None else selected
        oracle=(gwrl_cpp.campaign_refresh_political_unit_movement_oracle(state.context.native,envs,owners,enabled)
            if overrides is None else gwrl_cpp._campaign_political_unit_movement_test_oracle(state.context.native,envs,owners,enabled,overrides))
        self.assertEqual(result.errors.cpu().tolist(),[item["error"] for item in oracle]);self.assertTrue(result.committed.cpu().item())
        encoded=formatter.serialize(result.state,byte_capacity=262144)
        self.assertEqual(encoded.errors.cpu().tolist(),[0]*len(envs))
        actual=[json.loads(bytes(row[:length]).decode()) for row,length in zip(encoded.data.cpu().tolist(),encoded.lengths.cpu().tolist(),strict=True)]
        self.assertEqual(actual,[json.loads(item["planning_json"]) for item in oracle])
        if valid_output:
            got=result.state.restore_envs()
            self.assertEqual([json.loads(env.serialize())["state"] for env in got],[json.loads(item["state_json"]) for item in oracle])
            self.assertEqual([json.loads(env.serialize())["random"] for env in got],[json.loads(env.serialize())["random"] for env in envs])
        before,after=state.records.cpu(),result.state.records.cpu();a,b=state.sections.cpu(),result.state.sections.cpu()
        for column,name in enumerate(SECTION_NAMES):
            if name in {"state","state.units"}:continue
            for lane in range(len(envs)):
                x,y=int(a[lane,column]),int(b[lane,column]);old=before[lane,x:int(before[lane,x,4])].clone();new=after[lane,y:int(after[lane,y,4])].clone()
                old[:,4]-=x;new[:,4]-=y;self.assertTrue(torch.equal(old,new),name)
        # Inside Units only the two movement optionals may change.
        for lane in range(len(envs)):
            left,right=int(a[lane,4])+1,int(b[lane,4])+1;amount=int(before[lane,int(a[lane,4]),1])
            self.assertEqual(int(after[lane,int(b[lane,4]),1]),amount)
            for _ in range(amount):
                self.assertEqual(before[lane,left,1].item(),after[lane,right,1].item())
                u,v=left+1,right+1;x,y=u+1,v+1
                for field in range(14):
                    xe,ye=int(before[lane,x,4]),int(after[lane,y,4])
                    if field not in (4,5):
                        old,new=before[lane,x:xe].clone(),after[lane,y:ye].clone();old[:,4]-=x;new[:,4]-=y
                        self.assertTrue(torch.equal(old,new),str((lane,field)))
                    x,y=xe,ye
                left,right=int(before[lane,u,4]),int(after[lane,v,4])
        self.assertIs(result.state.string_bytes,state.string_bytes);self.assertIs(result.state.suffix_usage,state.suffix_usage)
        return actual

    def test_every_owner_and_pending_work_match_native_without_changing_unrelated_words(self):
        envs=[rich_fixture(),*real_states()];owners=["japan","ccp","kmt","mongolia"]
        state,service,ids,formatter=self.setup(envs,owners);original=[env.serialize() for env in envs]
        result=service.refresh_movement(state,ids,**service.reserve(state,unit_capacity=512))
        self.assert_native(state,result,envs,owners,formatter);self.assertEqual([env.serialize() for env in envs],original)
        count=result.count.cpu().item()
        self.assertEqual(count,sum(sum(unit["owner"]==owner for unit in json.loads(env.serialize())["state"]["units"].values()) for env,owner in zip(envs,owners,strict=True)))
        requests=result.requests[:count].cpu().tolist();tokens=ids.cpu().tolist()
        self.assertTrue(all(row[3]==tokens[row[0]] for row in requests))

    def test_new_major_home_context_used_movement_and_any_nonzero_placed_flag(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),23)
        def arrange(state):
            state["nations"]["ccp"]["power_status"]="major"
            unit=next(unit for unit in state["units"].values() if unit["owner"]=="ccp")
            unit.update(type="militia",movement_allowance=3,movement_remaining=1)
            copied=dict(unit);copied.update(id="political_placed_fixture",turn_flags={"placed_this_turn":-1},movement_allowance=3,movement_remaining=3)
            state["units"][copied["id"]]=copied
        env=changed(env,arrange);state,service,ids,formatter=self.setup([env],["ccp"])
        actual=self.assert_native(state,service.refresh_movement(state,ids,unit_capacity=128),[env],["ccp"],formatter)[0]
        self.assertEqual(actual["units"]["political_placed_fixture"]["movement_remaining"],0)
        for unit in actual["units"].values():
            if unit["owner"]=="ccp" and unit["type"]=="militia":self.assertEqual(unit["movement_allowance"],1)

    def test_optional_new_allowance_is_absent_but_remaining_is_retained_exactly(self):
        def missing(source):
            for document in source.values():
                for unit in document.get("units",[]):
                    if unit["id"]=="infantry":
                        for damage in unit["states"]:damage["movement"]=None
        env=catalog_fixture(missing);state,service,ids,formatter=self.setup([env],["japan"])
        result=service.refresh_movement(state,ids,unit_capacity=256)
        actual=self.assert_native(state,result,[env],["japan"],formatter,valid_output=False)[0]
        old=json.loads(env.serialize())["state"]["units"]
        for name,unit in actual["units"].items():
            if unit["owner"]=="japan" and unit["type"]=="infantry":
                self.assertIsNone(unit["movement_allowance"]);self.assertEqual(unit["movement_remaining"],old[name]["movement_remaining"])
        # This pure helper mirrors native output; outer Engine validation must
        # reject a catalog unit whose allowance is unresolved.
        with self.assertRaisesRegex(RuntimeError,"unresolved movement"):result.state.to_native()

    def temporary(self,state,name,allowance,remaining):
        units=state.section("state.units")[0].cpu().item();unit=lookup(state,units,name)
        for field,value in ((5,allowance),(4,remaining)):
            root=child(state,unit,field);present=value is not None;block=[[9,int(present),0,0,1+int(present)],scalar(2,0 if value is None else value)]
            block[1][4]=2
            state=replace_subtrees(state,torch.tensor([root],device="mps"),torch.tensor([block],device="mps"),
                torch.tensor([1+int(present)],device="mps"),torch.tensor([True],device="mps"),capacity=state.records.shape[1]).state
        return state

    def test_optional_old_inputs_use_zero_spent_when_either_optional_is_absent(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),31)
        name=next(name for name,unit in json.loads(env.serialize())["state"]["units"].items() if unit["owner"]=="japan" and unit["type"]=="infantry")
        original,service,ids,formatter=self.setup([env],["japan"])
        for allowance,remaining in ((None,None),(None,1),(3,None),(3,1),(0,3)):
            with self.subTest(allowance=allowance,remaining=remaining):
                state=self.temporary(original,name,allowance,remaining)
                result=service.refresh_movement(state,ids,unit_capacity=256)
                self.assert_native(state,result,[env],["japan"],formatter,overrides=[{name:(allowance,remaining)}])

    def test_lazy_catalog_errors_for_other_owners_and_unselected_lanes_stay_unqueried(self):
        def malformed(source):
            technology=next(t for t in source["technologies"]["technologies"] if t["id"]=="long_range_aircraft")
            technology["modifiers"]=[{"unit_types":["seaplane"],"classes":[],"requires_flags":[],"stat":"unrecognized_political_test_stat","add":1}]
        env=catalog_fixture(malformed)
        def arrange(state):
            state["nations"]["japan"]["technology_stages"]["long_range_aircraft"]=0
            state["nations"]["kmt"]["technology_stages"]["long_range_aircraft"]=4
            unit=dict(next(iter(state["units"].values())));unit.update(id="000_kmt_stats_error",type="seaplane",owner="kmt",zone="land_china_nanking",
                turn_origin="land_china_nanking",damage=0,cargo=[],carried_by=None,movement_allowance=3,movement_remaining=2)
            state["units"][unit["id"]]=unit
            for item in state["units"].values():
                if item["owner"]=="japan":item.update(movement_allowance=5,movement_remaining=4)
        env=changed(env,arrange);state,service,ids,formatter=self.setup([env,env.clone()],["japan","kmt"])
        selected=torch.tensor([True,False],device="mps")
        result=service.refresh_movement(state,ids,selected,unit_capacity=512)
        self.assert_native(state,result,[env,env],["japan","kmt"],formatter,selected=[True,False])
        result=service.refresh_movement(state,ids,unit_capacity=512)
        self.assertEqual(result.errors.cpu().tolist(),[0,2]);self.assertFalse(result.committed.cpu().item())
        self.assertEqual(result.accepted.cpu().tolist(),[False,False]);self.assertTrue(torch.equal(result.state.records,state.records))

    def test_unknown_owner_without_units_is_a_native_noop_even_with_tiny_allocations(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),23);state,service,ids,formatter=self.setup([env],["beneficiary"])
        result=service.refresh_movement(state,ids,unit_capacity=0,block_capacity=1)
        self.assert_native(state,result,[env],["beneficiary"],formatter)
        self.assertEqual(result.count.cpu().tolist(),[0]);self.assertEqual(result.required_block_capacity.cpu().tolist(),[0])

    def test_allocation_failures_report_complete_count_and_allow_exact_retry(self):
        env=rich_fixture();state,service,ids,formatter=self.setup([env],["japan"])
        actual=sum(unit["owner"]=="japan" for unit in json.loads(env.serialize())["state"]["units"].values())
        short=service.refresh_movement(state,ids,unit_capacity=actual-1)
        self.assertEqual(short.errors.cpu().tolist(),[5]);self.assertEqual(short.count.cpu().tolist(),[0]);self.assertEqual(short.required_count.cpu().tolist(),[actual])
        self.assertTrue(torch.equal(short.state.records,state.records))
        short=service.refresh_movement(state,ids,unit_capacity=actual,block_capacity=1)
        self.assertEqual(short.errors.cpu().tolist(),[5]);self.assertFalse(short.committed.cpu().item())
        result=service.refresh_movement(state,ids,unit_capacity=actual)
        self.assert_native(state,result,[env],["japan"],formatter)
        self.assertEqual(result.state.records.shape,state.records.shape)

    def test_optional_growth_has_state_capacity_rollback_and_metadata_only_headroom(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),31)
        name=next(name for name,unit in json.loads(env.serialize())["state"]["units"].items() if unit["owner"]=="japan" and unit["type"]=="infantry")
        before,service,ids,formatter=self.setup([env],["japan"]);temporary=self.temporary(before,name,None,None)
        length=temporary.lengths[0].cpu().item();temporary=replace(temporary,records=temporary.records[:,:length].contiguous())
        short=service.refresh_movement(temporary,ids,unit_capacity=256)
        self.assertEqual(short.errors.cpu().tolist(),[5]);self.assertFalse(short.committed.cpu().item());self.assertTrue(torch.equal(short.state.records,temporary.records))
        result=service.refresh_movement(temporary,ids,**service.reserve(temporary,unit_capacity=256))
        self.assert_native(temporary,result,[env],["japan"],formatter,overrides=[{name:(None,None)}])

    def test_no_host_native_or_all_inventory_queries_and_stale_layouts_empty_batch(self):
        env=rich_fixture();state,service,ids,formatter=self.setup([env],["japan"]);service.refresh_movement(state,ids,unit_capacity=256)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host values")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(json,"loads",side_effect=AssertionError("JSON hot path")), \
             patch.object(gwrl_cpp,"campaign_refresh_political_unit_movement_oracle",side_effect=AssertionError("CPU fallback")), \
             patch.object(service.catalog_stats,"all_units",side_effect=AssertionError("Unselected Catalog query")):
            result=service.refresh_movement(state,ids,unit_capacity=256)
        self.assert_native(state,result,[env],["japan"],formatter)
        with self.assertRaises(ValueError):service.refresh_movement(state,ids.cpu(),unit_capacity=256)
        foreign=DeviceStateBatch.capture([env],device="mps")
        with self.assertRaises(ValueError):service.refresh_movement(foreign,ids,unit_capacity=256)
        empty=DeviceStateBatch.capture([],context=state.context)
        result=service.refresh_movement(empty,torch.zeros(0,dtype=torch.int64,device="mps"),unit_capacity=0)
        self.assertTrue(result.committed.cpu().item());self.assertEqual(result.state.restore_envs(),[])


if __name__=="__main__":unittest.main()
