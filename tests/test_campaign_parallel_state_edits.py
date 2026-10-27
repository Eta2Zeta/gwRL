"""Parallel record copies preserve original validation/rollback bit-for-bit."""
from dataclasses import replace
import unittest
from unittest.mock import patch

import torch

import tests.test_campaign_device_state_edits as baseline
from studies.campaign.backends.device_state import DeviceStateContext,DeviceStateBatch
from studies.campaign.backends.device_state_edits import replace_subtrees


@unittest.skipUnless(baseline.EXACT_MPS,"Lossless Apple GPU required")
class ParallelStateEditTests(baseline.CampaignDeviceStateEditTests):
    def setUp(self):
        def dispatch(state,*args,**kwargs):
            kwargs.setdefault("implementation","parallel" if state.device.type=="mps" else "reference")
            return replace_subtrees(state,*args,**kwargs)
        self.switch=patch.object(baseline,"replace_subtrees",side_effect=dispatch);self.switch.start()
        self.addCleanup(self.switch.stop)

    def same(self,state,args,**kwargs):
        original=state.records.clone()
        reference=replace_subtrees(state,*args,implementation="reference",**kwargs)
        parallel=replace_subtrees(state,*args,implementation="parallel",**kwargs)
        for name in ("records","lengths","sections","string_bytes","string_offsets","errors","suffix_usage"):
            self.assertTrue(torch.equal(getattr(reference.state,name),getattr(parallel.state,name)),name)
        for name in ("errors","required_capacity","accepted","committed"):
            self.assertTrue(torch.equal(getattr(reference,name),getattr(parallel,name)),name)
        self.assertTrue(torch.equal(original,state.records))
        return parallel

    def test_all_malformed_blocks_source_errors_and_section_failures_match_reference(self):
        state,_=baseline.fixture("mps",count=2)
        cases=([[99,0,0,0,1]],[[3,1,0,0,1]],[[3,0,1<<32,0,1]],
            [[6,1,0,0,1]],[[5,1<<30,0,0,1]],baseline.tape([2,3]),[baseline.scalar(3,(1<<64)-1)])
        for rows in cases:
            args=baseline.arguments(state,"random.search",rows)
            for selected in (torch.tensor([True,True],device="mps"),torch.tensor([True,False],device="mps")):
                values=(*args[:3],selected)
                for change in (False,True):
                    self.same(state,values,allow_type_change=change,capacity=state.records.shape[1]+len(rows))
        args=baseline.arguments(state,"random.search",[baseline.scalar(3,7)])
        for source in (replace(state,errors=state.errors+1),replace(state,suffix_usage=state.suffix_usage+2)):
            self.same(source,args)
        roots=args[0].clone();roots[1]=-1;self.same(state,(roots,*args[1:]))
        data=state.records.clone();data[:,0,1]=3
        self.same(replace(state,records=data),args)

    def test_execution_context_selects_parallel_without_changing_state_or_default(self):
        state,envs=baseline.fixture("mps")
        self.assertEqual(state.context.editor_implementation,"reference")
        native=baseline.gwrl_cpp.capture_device_states(state.context.native,envs)
        context=DeviceStateContext(state.context.native,"mps",editor_implementation="parallel")
        chosen=DeviceStateBatch.from_native(native,context=context)
        args=baseline.arguments(chosen,"random.test_tape",baseline.tape([1,2,12]))
        actual=replace_subtrees(chosen,*args,capacity=chosen.records.shape[1]+4)
        expected=replace_subtrees(chosen,*args,capacity=chosen.records.shape[1]+4,implementation="reference")
        self.assertTrue(torch.equal(actual.state.records,expected.state.records))
        self.assertEqual(context.identity,state.context.identity)
        with self.assertRaises(AttributeError):context.editor_implementation="reference"
        for value in ("unknown",True,[],1):
            with self.assertRaises(ValueError):DeviceStateContext(state.context.native,"mps",editor_implementation=value)
        with self.assertRaises(ValueError):DeviceStateContext(state.context.native,"cpu",editor_implementation="parallel")

    def test_zero_batch_and_unselected_nonzero_padding_preserve_original_allocations(self):
        state,_=baseline.fixture("mps",count=2)
        records=torch.cat((state.records,torch.full((2,7,5),123,dtype=torch.int64,device="mps")),dim=1)
        padded=replace(state,records=records)
        args=baseline.arguments(padded,"random.search",[[99,0,0,0,1]],torch.zeros(2,dtype=torch.bool,device="mps"))
        self.same(padded,args,capacity=records.shape[1]+3)
        empty=state.fork([])
        args=(torch.empty(0,dtype=torch.int64,device="mps"),torch.empty((0,1,5),dtype=torch.int64,device="mps"),
            torch.empty(0,dtype=torch.int64,device="mps"),torch.empty(0,dtype=torch.bool,device="mps"))
        self.same(empty,args)


if __name__=="__main__":unittest.main()
