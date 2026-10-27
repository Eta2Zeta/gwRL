"""Parallel source grammar checks retain complete container-builder semantics."""
from dataclasses import replace
import unittest
from unittest.mock import patch

import torch

import tests.test_campaign_device_map_edits as baseline
from studies.campaign.backends.device_state import DeviceStateContext
from studies.campaign.backends import device_map_edits as edits


@unittest.skipUnless(baseline.EXACT_MPS,"Lossless Apple GPU required")
class ParallelContainerTests(baseline.CampaignDeviceMapEditTests):
    def setUp(self):
        self.changes=[]
        for name in ("build_map_edits","build_set_edits","build_sequence_splices"):
            original=getattr(edits,name)
            def dispatch(state,*args,_original=original,**kwargs):
                if state.device.type=="mps":state.context._container_implementation="parallel"
                return _original(state,*args,**kwargs)
            self.changes.append(patch.object(baseline,name,side_effect=dispatch))
        for item in self.changes:item.start();self.addCleanup(item.stop)

    def same(self,state,operation):
        original=state.records.clone();old=state.context._container_implementation
        try:
            state.context._container_implementation="reference";expected=operation()
            state.context._container_implementation="parallel";actual=operation()
        finally:state.context._container_implementation=old
        for name in ("roots","selected","blocks","lengths","errors","required_capacity","changed"):
            self.assertTrue(torch.equal(getattr(expected,name),getattr(actual,name)),name)
        self.assertIs(actual.source,state);self.assertTrue(torch.equal(original,state.records))
        return actual

    def test_partial_blocks_capacity_failures_and_unused_values_match_every_bit(self):
        state,_=baseline.fixture("mps",count=2)
        state,ids=baseline.intern(state,[b"aaa_existing",b"new_parallel_key"])
        roots=state.section("state.flags").contiguous();keys=ids.contiguous()
        for mode in (0,1,2,3,99):
            for rows in ([baseline.scalar(2,-7)],[[99,0,0,0,17]],[]):
                values=baseline.tensor(state,[rows]*2).reshape(2,len(rows),5)
                sizes=baseline.tensor(state,[len(rows)]*2)
                for capacity in (1,state.records.shape[1]):
                    self.same(state,lambda:edits.build_map_edits(state,roots,keys,baseline.tensor(state,[mode]*2),
                        values,sizes,baseline.tensor(state,[True,True],torch.bool),capacity=capacity))

    def test_unrelated_malformed_source_nodes_lengths_and_usage_preserve_source_precedence(self):
        state,_=baseline.fixture("mps",count=2);state,ids=baseline.intern(state,[b"aaa_existing"])
        roots=state.section("state.flags").contiguous();key=ids.expand(2).contiguous()
        variants=[]
        data=state.records.clone();at=int(state.section("random.search")[0].cpu());data[0,at,0]=99
        variants.append(replace(state,records=data))
        for length in (-1,0,state.records.shape[1]+1):
            sizes=state.lengths.clone();sizes[0]=length;variants.append(replace(state,lengths=sizes))
        variants.extend((replace(state,suffix_usage=state.suffix_usage+2),replace(state,errors=state.errors+1)))
        for broken in variants:
            for selected in ([True,True],[False,True]):
                self.same(broken,lambda:edits.build_map_edits(broken,roots,key,baseline.tensor(state,[99,99]),
                    baseline.tensor(state,[[baseline.scalar(2,1)]]*2),baseline.tensor(state,[1,1]),
                    baseline.tensor(state,selected,torch.bool)))

    def test_explicit_execution_policy_is_readonly_and_not_a_rules_or_state_identity(self):
        state,_=baseline.fixture("mps")
        chosen=DeviceStateContext(state.context.native,"mps",container_implementation="parallel")
        self.assertEqual(chosen.identity,state.context.identity)
        with self.assertRaises(AttributeError):chosen.container_implementation="reference"
        for mode in ("bad",True,[],1):
            with self.assertRaises(ValueError):DeviceStateContext(state.context.native,"mps",container_implementation=mode)
        with self.assertRaises(ValueError):DeviceStateContext(state.context.native,"cpu",container_implementation="parallel")


if __name__=="__main__":unittest.main()
