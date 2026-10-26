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


if __name__=="__main__":unittest.main()
