"""Direct packed Apple GPU accounting, without recapturing CPU state."""
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.metal_validation import mps_int64_indexing_supported

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()

from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext, SECTION_NAMES
from studies.campaign.backends.resident_state_income import (
    ACCOUNTING_INPUT, PACKED_INPUT, WRONG_PHASE, ResidentIncomeContext,
)
from studies.campaign.backends.device_state_edits import EditError, replace_subtrees

SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"


def changed(env,mutate):
    document=json.loads(env.serialize());mutate(document["state"])
    out=env.clone();out.restore(json.dumps(document));return out


def placement(env):
    return changed(env,lambda state:state["clock"].update(phase="place_units"))


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class ResidentIncomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def setup_batch(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        batch=DeviceStateBatch.capture(envs,context=context)
        income=gwrl_cpp.campaign_income_context(envs[0])
        return batch,ResidentIncomeContext(context,income),income

    def expected(self,envs,income):
        oracle=gwrl_cpp.campaign_income_ledger_oracle(income,envs)
        self.assertFalse(np.any(oracle.error_array()))
        ledger,components=oracle.after.ledger_array(),oracle.after.component_array()
        output=[]
        for lane,env in enumerate(envs):
            document=json.loads(env.serialize());state=document["state"]
            for n,name in enumerate(income.nation_ids):
                if name not in state["nations"]:continue
                nation=state["nations"][name]
                if nation["treasury"] is not None:nation["treasury"]=int(ledger[lane,n,0])
                nation["income_known"]=bool(ledger[lane,n,1])
                nation["income_components"]={name:int(value) for name,(present,value) in
                    zip(oracle.after.component_ids,components[lane,n],strict=True) if present}
            state["clock"]["income_collected"]=True
            expected=env.clone();expected.restore(json.dumps(document));output.append(expected.serialize())
        return output

    def test_extraction_matches_direct_native_inputs_from_current_resident_records(self):
        first=placement(gwrl_cpp.CampaignEnv(str(SCENARIO),91))
        current=first.current_nation()
        def edge(state):
            land=next(value for value in state["territories"].values() if value["possessor"]==current)
            land["flags"].update(city_damage=-(2**31),city_ipp_lost=-(2**31))
            state["nations"][current]["treasury"]=0
        second=changed(first,edge)
        batch,kernel,income=self.setup_batch([first,second])
        native=gwrl_cpp.capture_campaign_income_ledger(income,[first,second])
        actual=kernel.extract(batch)
        self.assertEqual(actual.errors.cpu().tolist(),[0,0])
        for result,expected in ((actual.territories,native.income_inputs.territory_array()),
                                (actual.nations,native.income_inputs.nation_array()),
                                (actual.ledger,native.ledger_array()),(actual.clock,native.clock_array())):
            np.testing.assert_array_equal(result.cpu().numpy(),expected)

    def test_full_state_commit_matches_native_accounting_and_preserves_all_other_sections(self):
        first=placement(gwrl_cpp.CampaignEnv(str(SCENARIO),7))
        def custom(state):
            for nation in state["nations"].values():
                nation["income_known"]=False;nation["income_components"]={"old_custom":-19}
        second=changed(first,custom)
        envs=[first,second];batch,kernel,income=self.setup_batch(envs)
        expected=self.expected(envs,income);source=[env.serialize() for env in envs]
        result=kernel.apply(batch)
        self.assertEqual(result.errors.cpu().tolist(),[0,0])
        self.assertEqual(result.accepted.cpu().tolist(),[True,True])
        self.assertEqual([env.serialize() for env in result.state.restore_envs()],expected)
        self.assertEqual([env.serialize() for env in envs],source)
        # Every unrelated subtree, including all64 RNG bits and arbitrary JSON
        # number bits, retains exact records after relocating subtree ends.
        old,new=batch.records.cpu(),result.state.records.cpu()
        old_sections,new_sections=batch.sections.cpu(),result.state.sections.cpu()
        for section in (*SECTION_NAMES[3:9],*SECTION_NAMES[10:]):
            index=SECTION_NAMES.index(section)
            for lane in range(2):
                a,b=int(old_sections[lane,index]),int(new_sections[lane,index])
                left,right=old[lane,a:int(old[lane,a,4])].clone(),new[lane,b:int(new[lane,b,4])].clone()
                left[:,4]-=a;right[:,4]-=b
                self.assertTrue(torch.equal(left,right),section)
        again=kernel.apply(result.state)
        self.assertEqual([env.serialize() for env in again.state.restore_envs()],expected)

    def test_selected_cohort_failure_rolls_back_all_and_unselected_error_does_not_veto(self):
        first=placement(gwrl_cpp.CampaignEnv(str(SCENARIO),1));current=first.current_nation()
        bad=changed(first,lambda state:state["nations"][current].update(treasury=2**31-1,
            income_components={"retained_on_error":37}))
        batch,kernel,income=self.setup_batch([first,bad]);source=[first.serialize(),bad.serialize()]
        result=kernel.apply(batch)
        self.assertEqual(result.accepted.cpu().tolist(),[False,False])
        self.assertTrue(result.errors.cpu().tolist()[1]&ACCOUNTING_INPUT)
        self.assertEqual([env.serialize() for env in result.state.restore_envs()],source)
        selected=torch.tensor([True,False],dtype=torch.bool,device="mps")
        result=kernel.apply(batch,selected)
        self.assertEqual(result.accepted.cpu().tolist(),[True,False])
        self.assertEqual([env.serialize() for env in result.state.restore_envs()],[self.expected([first],income)[0],bad.serialize()])

    def test_compute_and_commit_have_no_cpu_tensor_reads_json_or_native_recapture(self):
        first=placement(gwrl_cpp.CampaignEnv(str(SCENARIO),1));batch,kernel,_=self.setup_batch([first])
        # Compile once before instrumenting PyTorch's compilation machinery.
        kernel.apply(batch)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("CPU transfer")), \
                patch.object(torch.Tensor,"item",side_effect=AssertionError("CPU scalar")), \
                patch.object(torch.Tensor,"tolist",side_effect=AssertionError("CPU list")), \
                patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("CPU scalar bool")), \
                patch.object(json,"loads",side_effect=AssertionError("JSON route")), \
                patch.object(gwrl_cpp,"capture_campaign_income_ledger",side_effect=AssertionError("Native recapture")), \
                patch.object(gwrl_cpp,"capture_device_states",side_effect=AssertionError("Native recapture")):
            result=kernel.apply(batch)
        self.assertEqual(result.errors.cpu().tolist(),[0])

    def test_wrong_phase_and_corrupt_records_are_explicit_and_preserve_inputs(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1);batch,kernel,_=self.setup_batch([first])
        output=kernel.apply(batch)
        self.assertTrue(output.errors.cpu().tolist()[0]&WRONG_PHASE)
        self.assertEqual(output.state.restore_envs()[0].serialize(),first.serialize())
        broken=replace(batch,records=batch.records.clone());broken.records[0,0,4]=0
        output=kernel.apply(broken)
        self.assertTrue(output.errors.cpu().tolist()[0]&PACKED_INPUT)
        self.assertTrue(torch.equal(output.state.records[:,:broken.records.shape[1]].cpu(),broken.records.cpu()))

    def test_empty_batch_and_foreign_context(self):
        first=placement(gwrl_cpp.CampaignEnv(str(SCENARIO),1));batch,kernel,_=self.setup_batch([first])
        empty=DeviceStateBatch.capture([],context=batch.context)
        result=kernel.apply(empty)
        self.assertEqual(result.errors.cpu().tolist(),[])
        self.assertEqual(result.state.restore_envs(),[])
        other=gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO),3,1)
        different=DeviceStateBatch.capture([other],device="mps")
        with self.assertRaises(ValueError):kernel.extract(different)

    def assert_refresh_matches_native(self,batch,result,envs):
        oracle=gwrl_cpp.campaign_refresh_income_oracle(envs)
        self.assertEqual(oracle.error_array().tolist(),[0]*len(envs))
        self.assertEqual(result.errors.cpu().tolist(),[0]*len(envs))
        actual=[json.loads(env.serialize()) for env in result.state.restore_envs()]
        self.assertEqual([value["state"] for value in actual],[json.loads(text) for text in oracle.state_jsons])
        self.assertEqual([value["random"] for value in actual],[json.loads(env.serialize())["random"] for env in envs])
        # Native serialization canonicalizes negative zero. Verify the complete
        # original opaque payload/RNG words as well, without losing those bits.
        old,new=batch.records.cpu(),result.state.records.cpu()
        before,after=batch.sections.cpu(),result.state.sections.cpu()
        for index,name in enumerate(SECTION_NAMES):
            if name in {"state","state.nations"}:continue
            for lane in range(len(envs)):
                a,b=int(before[lane,index]),int(after[lane,index])
                left,right=old[lane,a:int(old[lane,a,4])].clone(),new[lane,b:int(new[lane,b,4])].clone()
                left[:,4]-=a;right[:,4]-=b
                self.assertTrue(torch.equal(left,right),name)

    def test_refresh_matches_exact_native_function_in_every_phase_without_collecting(self):
        from tests.test_campaign_device_state import rich_fixture
        original=rich_fixture()
        envs=[]
        for phase in ("production","combat_movement","combat","non_combat_movement","place_units"):
            def stale(state):
                state["clock"].update(phase=phase,income_collected=False)
                for nation in state["nations"].values():
                    nation.update(income_known=False,income_components={"old_custom_component":-19})
                state["nations"]["japan"]["treasury"]=2**31-1
            envs.append(changed(original,stale))
        # Already-collected accounting remains true and cash remains untouched.
        envs.append(changed(envs[-1],lambda state:state["clock"].update(income_collected=True)))
        batch,kernel,_=self.setup_batch(envs)
        source=[env.serialize() for env in envs]
        result=kernel.refresh(batch)
        self.assert_refresh_matches_native(batch,result,envs)
        self.assertEqual([env.serialize() for env in envs],source)
        again=kernel.refresh(result.state)
        self.assertEqual(again.errors.cpu().tolist(),[0]*len(envs))
        self.assertEqual(again.state.records.shape,result.state.records.shape)
        self.assertEqual([env.serialize() for env in again.state.restore_envs()],[env.serialize() for env in result.state.restore_envs()])

    def test_refresh_eligibility_capital_control_and_custom_maps_match_native(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),111)
        def special(state):
            for nation in state["nations"].values():
                nation.update(income_known=False,income_components={"custom_key_must_be_erased":71})
            state["nations"]["japan"]["treasury"]=0
            japan_cap=state["politics"]["capitals"]["japan"]
            state["territories"][japan_cap]["possessor"]="kmt"
            # Absent capital map is collectable-false with component entries;
            # zero cash is an account, absent cash is a different early-out.
            state["politics"]["capitals"].pop("kmt",None)
            state["nations"]["ccp"]["treasury"]=None
            state["politics"]["surrendered"]=["japan"]
        second=changed(first,special)
        # One lane isolates lost-capital components from surrender's empty map.
        third=changed(second,lambda state:state["politics"].update(surrendered=[]))
        batch,kernel,_=self.setup_batch([first,second,third])
        result=kernel.refresh(batch,capacity=batch.records.shape[1]+4*len(kernel.ledger_context.nation_ids))
        self.assert_refresh_matches_native(batch,result,[first,second,third])
        values=[json.loads(env.serialize())["state"]["nations"] for env in result.state.restore_envs()]
        self.assertEqual(values[1]["japan"]["income_components"],{})
        self.assertIn("territorial",values[2]["japan"]["income_components"])
        self.assertEqual(values[1]["ccp"]["income_components"],{})

    def test_refresh_reads_changed_resident_possession_without_json_native_recapture_or_host_reads(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),5)
        original=first.serialize()
        batch,kernel,_=self.setup_batch([first])
        doc=json.loads(first.serialize())
        zone=next(key for key,value in doc["state"]["territories"].items() if value["possessor"]=="kmt")
        # Explicit test authoring lookup. The actual mutation and refresh consume
        # resident indices/IDs and never recapture the unchanged native source.
        from tests.test_campaign_device_map_edits import lookup
        territories=batch.section("state.territories")[0].cpu().item()
        territory=lookup(batch,territories,zone)
        owner=territory+1
        japan=int(batch.context.prefix_lookup_ids(["japan"])[0])
        blocks=torch.tensor([[[9,1,0,0,2],[5,japan,0,0,2]]],dtype=torch.int64,device="mps")
        resident=replace_subtrees(batch,torch.tensor([owner],dtype=torch.int64,device="mps"),blocks,
            torch.tensor([2],dtype=torch.int64,device="mps"),torch.tensor([True],device="mps")).state
        reference=changed(first,lambda state:state["territories"][zone].update(possessor="japan"))
        # Compile before the guards; no native oracle is consulted by execution.
        kernel.refresh(resident)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("CPU transfer")), \
                patch.object(torch.Tensor,"item",side_effect=AssertionError("CPU scalar")), \
                patch.object(torch.Tensor,"tolist",side_effect=AssertionError("CPU list")), \
                patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("CPU bool")), \
                patch.object(json,"loads",side_effect=AssertionError("JSON route")), \
                patch.object(gwrl_cpp,"capture_campaign_income_ledger",side_effect=AssertionError("Native recapture")), \
                patch.object(gwrl_cpp,"capture_device_states",side_effect=AssertionError("Native recapture")), \
                patch.object(gwrl_cpp,"campaign_refresh_income_oracle",side_effect=AssertionError("Native oracle fallback")):
            result=kernel.refresh(resident)
        self.assert_refresh_matches_native(resident,result,[reference])
        self.assertEqual(first.serialize(),original)

    def test_refresh_capacity_retry_is_explicit_and_repeated_calls_keep_fixed_allocation(self):
        original=gwrl_cpp.CampaignEnv(str(SCENARIO),17)
        def empty_rates(state):
            for nation in state["nations"].values():nation.update(income_components={},income_known=False)
        first=changed(original,empty_rates)
        batch,kernel,_=self.setup_batch([first])
        failed=kernel.refresh(batch)
        self.assertFalse(failed.accepted.cpu().item())
        self.assertTrue(failed.errors.cpu().item()&int(EditError.CAPACITY))
        self.assertGreater(failed.required_capacity.cpu().item(),batch.records.shape[1])
        self.assertTrue(torch.equal(failed.state.records,batch.records))
        capacity=batch.records.shape[1]+4*len(kernel.ledger_context.nation_ids)
        result=kernel.refresh(batch,capacity=capacity)
        self.assert_refresh_matches_native(batch,result,[first])
        for _ in range(3):
            again=kernel.refresh(result.state)
            self.assertEqual(again.errors.cpu().tolist(),[0]);self.assertEqual(again.state.records.shape[1],capacity)
            self.assertTrue(torch.equal(again.state.records,result.state.records));result=again

    def test_refresh_errors_roll_back_selected_cohort_and_do_not_invent_overflow_results(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),19)
        batch,kernel,_=self.setup_batch([first,first.clone()])
        broken=replace(batch,records=batch.records.clone());broken.records[1,0,4]=0
        result=kernel.refresh(broken)
        self.assertEqual(result.accepted.cpu().tolist(),[False,False]);self.assertTrue(result.errors.cpu().tolist()[1]&PACKED_INPUT)
        self.assertTrue(torch.equal(result.state.records,broken.records))
        result=kernel.refresh(broken,torch.tensor([True,False],device="mps"))
        self.assertEqual(result.accepted.cpu().tolist(),[True,False]);self.assertEqual(result.errors.cpu().tolist(),[0,0])
        def excessive(state):
            for land in state["territories"].values():
                land["possessor"]="japan";land["flags"].update(city_damage=-(2**31),city_ipp_lost=-(2**31))
        overflow=changed(first,excessive)
        packed,kernel,_=self.setup_batch([overflow])
        result=kernel.refresh(packed)
        self.assertTrue(result.errors.cpu().item()&ACCOUNTING_INPUT)
        self.assertTrue(torch.equal(result.state.records,packed.records))
        # Native signed-int sum would be undefined here. Do not run that oracle
        # or assert a wrapped income; the checkpoint remains unchanged.
        empty=DeviceStateBatch.capture([],context=batch.context)
        result=ResidentIncomeContext(batch.context,gwrl_cpp.campaign_income_context(first)).refresh(empty)
        self.assertEqual(result.errors.cpu().tolist(),[]);self.assertEqual(result.state.restore_envs(),[])


if __name__=="__main__":unittest.main()
