"""Parallel unit fragments preserve native bytes, capacity and diagnostics."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

import tests.test_campaign_resident_state_json as baseline
from studies.campaign.backends.resident_state_json_parallel import ParallelUnitStateJson
from studies.campaign.backends.resident_state_json import ResidentStateJson
from studies.campaign.backends.device_state import DeviceStateBatch


@unittest.skipUnless(baseline.EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class ParallelUnitStateJsonTests(baseline.ResidentStateJsonTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())

    def setup_batch(self,envs):
        state,reference=super().setup_batch(envs)
        return state,ParallelUnitStateJson(reference.number_context)

    def compare(self,state,parallel,capacity):
        expected=ResidentStateJson(parallel.number_context).serialize(state,byte_capacity=capacity)
        result=parallel.serialize(state,byte_capacity=capacity)
        for name in ("data","lengths","required_bytes","errors","count","batch_error"):
            self.assertTrue(torch.equal(getattr(result,name),getattr(expected,name)),name)
        return result

    def test_every_partial_output_byte_and_capacity_boundary_matches_reference(self):
        raw=gwrl_cpp.CampaignEnv(str(baseline.SCENARIO),19)
        state,parallel=self.setup_batch([raw])
        result=parallel.serialize(state,byte_capacity=262144);needed=int(result.required_bytes[0].cpu())
        for capacity in (0,1,7,needed//3,needed-1,needed,needed+17):
            with self.subTest(capacity=capacity):self.compare(state,parallel,capacity)
        empty=baseline.changed(raw,lambda document:document['state'].update(units={}))
        other,formatter=self.setup_batch([empty]);self.compare(other,formatter,262144)

    def test_invalid_unit_order_shape_and_scalar_use_exact_serial_gpu_diagnostics(self):
        raw=gwrl_cpp.CampaignEnv(str(baseline.SCENARIO),19)
        state,parallel=self.setup_batch([raw]);rows=state.records[0].cpu().tolist()
        root=int(state.section("state.units")[0].cpu());key=root+1;unit=rows[key][4];second=rows[unit][4]
        cases=[]
        data=state.records.clone();data[0,unit,1]-=1;cases.append(replace(state,records=data))
        data=state.records.clone();data[0,second,1]=data[0,key,1];cases.append(replace(state,records=data))
        data=state.records.clone();data[0,root,1]+=1;cases.append(replace(state,records=data))
        # A scalar with the wrong typed tag remains a diagnostic error, not a
        # dropped unit or a partially published alternative JSON representation.
        child=unit+1
        for _ in range(10):child=rows[child][4]
        data=state.records.clone();data[0,child,0]=5;cases.append(replace(state,records=data))
        for malformed in cases:
            for capacity in (0,97,262144):
                with self.subTest(capacity=capacity):self.compare(malformed,parallel,capacity)

    def test_long_escaped_unit_ids_and_full_source_bits_survive(self):
        raw=gwrl_cpp.CampaignEnv(str(baseline.SCENARIO),19)
        def rename(document):
            units=document['state']['units'];old=next(iter(units));unit=units.pop(old)
            new='parallel-蒙古-"\\\x00'*64;unit['id']=new;units[new]=unit
            for value in units.values():
                value['cargo']=[new if item==old else item for item in value['cargo']]
                if value['carried_by']==old:value['carried_by']=new
        rich=baseline.changed(raw,rename)
        state,parallel=self.setup_batch([raw,rich]);before=state.records.clone()
        self.compare(state,parallel,262144)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host read")), \
                patch.object(torch.Tensor,"item",side_effect=AssertionError("Host read")), \
                patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host read")), \
                patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host read")), \
                patch.object(json,"loads",side_effect=AssertionError("JSON fallback")), \
                patch.object(gwrl_cpp,"campaign_state_json_oracle",side_effect=AssertionError("Native fallback")):
            parallel.serialize(state,byte_capacity=262144)
        self.assertTrue(torch.equal(before,state.records))


if __name__=="__main__":
    unittest.main()
