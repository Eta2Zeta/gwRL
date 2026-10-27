"""Complete native audit Event parity and atomic record/string rollback."""
from dataclasses import replace
import json
import struct
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from tests.test_campaign_device_state import SCENARIO,rich_fixture
from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
from studies.campaign.backends.resident_state_json import ResidentStateJson
from studies.campaign.backends.content_digest_metal import inspect_digests
from studies.campaign.backends.resident_events import (
    EventKind,EventError,EventPayloads,prepare_event_labels,append_events)

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()
KINDS=('action','interrupt','chance')


def fixture(payload,rich=False):
    env=rich_fixture() if rich else gwrl_cpp.CampaignEnv(str(SCENARIO),17,training_actions=True)
    doc=json.loads(env.serialize())
    # Ensure the current State hash is a new string rather than an existing
    # start-event key, so hash-pool capacity failure is actually exercised.
    doc['state']['flags']['event_append_fixture']=17
    doc['state']['history'].insert(0,{'kind':'event_payload_source','payload':payload,'after_state_key':'preserved'})
    env.restore(json.dumps(doc,ensure_ascii=False));return env


def payloads_from_first_history(state):
    # A resident fixture extractor, using the actual native subtree ends rather
    # than converting the payload back through JSON. Production rule builders
    # already possess their generic payload forest.
    B,C=state.records.shape[:2];device=state.device
    roots=state.section('state.history')+3
    lane=torch.arange(B,dtype=torch.int64,device=device)
    flat=state.records.view(-1,5)
    headers=flat.index_select(0,lane*C+roots)
    lengths=headers[:,4]-roots
    position=torch.arange(C,dtype=torch.int64,device=device)[None,:]
    index=(roots[:,None]+position).clamp(0,max(C-1,0))+lane[:,None]*C
    records=flat.index_select(0,index.flatten()).view(B,C,5)
    records=records.clone();records[:,:,4]-=roots[:,None]
    records=torch.where((position<lengths[:,None])[:,:,None],records,0)
    return EventPayloads(state,records,lengths,torch.zeros(B,dtype=torch.int64,device=device))


@unittest.skipUnless(EXACT_MPS,'Lossless Apple GPU runtime unavailable')
class ResidentEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(2)

    def setup_batch(self,payloads,rich=False):
        envs=[fixture(value,rich) for value in payloads]
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),'mps')
        native=gwrl_cpp.capture_device_states(context.native,envs)
        source=DeviceStateBatch.from_native(native,context=context)
        formatter=ResidentStateJson(CanonicalJsonContext(native,context))
        prepared=prepare_event_labels(source,string_capacity=source.string_offsets.numel()+2,
                                      byte_capacity=source.string_bytes.numel()+21)
        self.assertTrue(prepared.committed.item())
        state=prepared.state;identities=formatter.identities(state,byte_capacity=262144)
        forest=payloads_from_first_history(state)
        return envs,state,identities,forest,prepared.labels

    def capacities(self,state,forest):
        return dict(state_capacity=state.records.shape[1]+forest.records.shape[1]+3,
                    block_capacity=state.records.shape[1]+forest.records.shape[1]+3,
                    string_capacity=state.string_offsets.numel()-1+state.lane_count,
                    byte_capacity=state.string_bytes.numel()+64*state.lane_count)

    def restored_state_json(self,state):
        return tuple(gwrl_cpp.campaign_canonical_json_probe([json.dumps(json.loads(env.serialize())['state'],ensure_ascii=False)])[0]
                     for env in state.restore_envs())

    def assert_rollback(self,source,result):
        self.assertFalse(result.committed.item())
        self.assertEqual([env.serialize() for env in source.restore_envs()],[env.serialize() for env in result.state.restore_envs()])
        self.assertTrue(torch.equal(result.state.suffix_usage,source.suffix_usage))
        self.assertTrue(torch.equal(result.state.string_bytes[:source.string_bytes.numel()],source.string_bytes))
        self.assertTrue(torch.equal(result.state.string_offsets[:source.string_offsets.numel()],source.string_offsets))

    def test_all_event_kinds_complete_rich_history_and_rng_match_native(self):
        payloads=[{'id':'chosen','parameters':{'zone':'蒙古','empty':None}}, {'offer':'axis'}, {'faces':[[1,2],[12]]}]
        deep='leaf'
        for _ in range(140):deep=[deep]
        payloads.extend((None,True,'蒙古\u0000',[-0.0,1.0000000000000002],deep))
        envs,state,ids,forest,labels=self.setup_batch(payloads,rich=True)
        before=[env.serialize() for env in envs]
        expected=gwrl_cpp.campaign_event_append_probe(envs,[KINDS[i%3] for i in range(len(payloads))],[json.dumps(p,ensure_ascii=False) for p in payloads])
        result=append_events(state,ids,forest,torch.arange(len(payloads),dtype=torch.int64,device='mps')%3,labels,**self.capacities(state,forest))
        self.assertTrue(result.committed.item());self.assertEqual(result.errors.cpu().tolist(),[0]*len(payloads))
        self.assertEqual(self.restored_state_json(result.state),tuple(expected))
        self.assertEqual([env.serialize() for env in envs],before)
        self.assertIs(result.identities.source,result.state)
        self.assertEqual(inspect_digests(result.identities.state_keys),inspect_digests(ids.state_keys))
        for initial,restored in zip(state.restore_envs(),result.state.restore_envs(),strict=True):
            self.assertEqual(json.loads(initial.serialize())['random'],json.loads(restored.serialize())['random'])
        for row,key in zip(result.state.restore_envs(),inspect_digests(ids.state_keys),strict=True):
            self.assertEqual(json.loads(row.serialize())['state']['history'][-1]['after_state_key'],key)
        self.assertNotEqual(inspect_digests(ids.state_keys),inspect_digests(ids.engine_keys))
        # Canonical JSON normalizes -0. Check original payload/history IEEE bits
        # and all three RNG uint64 words directly in the packed representation.
        old,new=state.records.cpu(),result.state.records.cpu()
        old_sections,new_sections=state.sections.cpu(),result.state.sections.cpu()
        from studies.campaign.backends.device_state import SECTION_NAMES
        for lane in range(len(payloads)):
            hs=old_sections[lane,SECTION_NAMES.index('state.history')].item()
            hn=new_sections[lane,SECTION_NAMES.index('state.history')].item();he=old[lane,hs,4].item()
            before=old[lane,hs+1:he].clone();after=new[lane,hn+1:hn+he-hs].clone()
            before[:,4]-=hs;after[:,4]-=hn;self.assertTrue(torch.equal(before,after))
            event=hn+he-hs;payload=event+2;end=new[lane,payload,4].item()
            actual=new[lane,payload:end].clone();actual[:,4]-=payload
            expected=forest.records[lane,:forest.lengths[lane].item()].cpu()
            self.assertTrue(torch.equal(actual,expected))
            rs=old_sections[lane,SECTION_NAMES.index('random')].item()
            rn=new_sections[lane,SECTION_NAMES.index('random')].item()
            before=old[lane,rs:old[lane,rs,4].item()].clone()
            after=new[lane,rn:new[lane,rn,4].item()].clone()
            before[:,4]-=rs;after[:,4]-=rn;self.assertTrue(torch.equal(before,after))

    def test_selected_cohort_ignores_unselected_bad_payload_and_preserves_order(self):
        values=[{'x':0},{'x':1},{'x':2}];envs,state,ids,forest,labels=self.setup_batch(values)
        bad=forest.records.clone();bad[1,0,0]=10
        forest=replace(forest,records=bad)
        selected=torch.tensor([True,False,True],dtype=torch.bool,device='mps')
        result=append_events(state,ids,forest,torch.zeros(3,dtype=torch.int64,device='mps'),labels,
                             selected=selected,**self.capacities(state,forest))
        self.assertTrue(result.committed.item());self.assertEqual(result.accepted.cpu().tolist(),[True,False,True])
        expected=gwrl_cpp.campaign_event_append_probe(envs,['action']*3,[json.dumps(p) for p in values])
        actual=self.restored_state_json(result.state)
        self.assertEqual(actual[0],expected[0]);self.assertEqual(actual[2],expected[2])
        self.assertEqual(json.loads(actual[1]),json.loads(envs[1].serialize())['state'])

    def test_invalid_payload_rolls_back_every_selected_record_and_new_hash_string(self):
        _,state,ids,forest,labels=self.setup_batch([{'x':0.1},{'x':0.2}])
        records=forest.records.clone();rows=records[0].cpu().tolist()
        target=next(i for i,row in enumerate(rows) if row[0]==4)
        records[0,target,2]=0;records[0,target,3]=0x7ff00000
        result=append_events(state,ids,replace(forest,records=records),torch.zeros(2,dtype=torch.int64,device='mps'),labels,
                             **self.capacities(state,forest))
        self.assert_rollback(state,result)
        self.assertTrue(result.errors[0].item()&EventError.PAYLOAD)

    def test_all_capacities_fail_safely_report_exact_sizes_and_retry(self):
        values=[{'long':'text '*15}];envs,state,ids,forest,labels=self.setup_batch(values)
        capacities=self.capacities(state,forest);kinds=torch.zeros(1,dtype=torch.int64,device='mps')
        for override in ({'state_capacity':state.records.shape[1]}, {'block_capacity':1},
                         {'string_capacity':state.string_offsets.numel()-1,'byte_capacity':state.string_bytes.numel()}):
            failed=append_events(state,ids,forest,kinds,labels,**(capacities|override))
            self.assert_rollback(state,failed)
            self.assertEqual(failed.required_state_capacity.cpu().tolist(),(state.lengths+forest.lengths+3).cpu().tolist())
            retry=dict(state_capacity=max(state.records.shape[1],failed.required_state_capacity.max().item()),
                       block_capacity=max(1,failed.required_block_capacity.max().item()),
                       string_capacity=max(state.string_offsets.numel()-1,failed.required_string_usage[0].item()),
                       byte_capacity=max(state.string_bytes.numel(),failed.required_string_usage[1].item()))
            passed=append_events(state,ids,forest,kinds,labels,**retry)
            self.assertTrue(passed.committed.item());self.assertEqual(passed.errors.cpu().tolist(),[0])
            expected=gwrl_cpp.campaign_event_append_probe(envs,['action'],[json.dumps(values[0])])
            self.assertEqual(self.restored_state_json(passed.state),tuple(expected))

    def test_unknown_finite_payload_number_is_preserved_without_spelling_cache(self):
        envs,state,ids,forest,labels=self.setup_batch([{'number':0.1}])
        records=forest.records.clone();target=next(i for i,row in enumerate(records[0].cpu().tolist()) if row[0]==4)
        value=0.123456789012345;bits=struct.unpack('Q',struct.pack('d',value))[0]
        records[0,target,2]=bits&0xffffffff;records[0,target,3]=bits>>32
        result=append_events(state,ids,replace(forest,records=records),torch.zeros(1,dtype=torch.int64,device='mps'),labels,
                             **self.capacities(state,forest))
        self.assertTrue(result.committed.item())
        expected=gwrl_cpp.campaign_event_append_probe(envs,['action'],[json.dumps({'number':value})])
        self.assertEqual(self.restored_state_json(result.state),tuple(expected))

    def test_kind_hash_errors_stale_sources_and_labels_are_explicit(self):
        _,state,ids,forest,labels=self.setup_batch([{}]);capacities=self.capacities(state,forest)
        result=append_events(state,ids,forest,torch.tensor([3],dtype=torch.int64,device='mps'),labels,**capacities)
        self.assert_rollback(state,result);self.assertTrue(result.errors[0].item()&EventError.KIND)
        corrupt=ids.state_keys.hex_bytes.clone();corrupt[0,0]=ord('G')
        result=append_events(state,replace(ids,state_keys=replace(ids.state_keys,hex_bytes=corrupt)),forest,
                             torch.zeros(1,dtype=torch.int64,device='mps'),labels,**capacities)
        self.assert_rollback(state,result);self.assertTrue(result.errors[0].item()&EventError.HASH)
        with self.assertRaises(ValueError):append_events(state.snapshot(),ids,forest,torch.zeros(1,dtype=torch.int64,device='mps'),labels)
        with self.assertRaises(ValueError):append_events(state,ids,replace(forest,source=state.snapshot()),
                                                         torch.zeros(1,dtype=torch.int64,device='mps'),labels)

    def test_rebound_identity_reuses_same_key_for_second_append_without_rehash(self):
        _,state,ids,forest,labels=self.setup_batch([{'x':1}]);kinds=torch.zeros(1,dtype=torch.int64,device='mps')
        first=append_events(state,ids,forest,kinds,labels,**self.capacities(state,forest))
        self.assertTrue(first.committed.item())
        with patch.object(ResidentStateJson,'identities',side_effect=AssertionError('Redundant State hash forbidden')):
            second=append_events(first.state,first.identities,replace(forest,source=first.state),kinds,labels)
        self.assertTrue(second.committed.item())
        history=json.loads(second.state.restore_envs()[0].serialize())['state']['history']
        self.assertEqual(history[-1],history[-2])
        self.assertIs(second.identities.source,second.state)

    def test_no_host_reads_or_native_serialization_in_append(self):
        _,state,ids,forest,labels=self.setup_batch([{'x':[False,None,1]}]);capacities=self.capacities(state,forest)
        kinds=torch.zeros(1,dtype=torch.int64,device='mps');append_events(state,ids,forest,kinds,labels,**capacities);torch.mps.synchronize()
        fail=AssertionError('Host read/serializer forbidden in resident Event commit')
        with patch.object(torch.Tensor,'cpu',side_effect=fail),patch.object(torch.Tensor,'tolist',side_effect=fail),\
             patch.object(torch.Tensor,'item',side_effect=fail),patch.object(json,'loads',side_effect=fail),\
             patch.object(json,'dumps',side_effect=fail),patch.object(gwrl_cpp,'campaign_event_append_probe',side_effect=fail):
            result=append_events(state,ids,forest,kinds,labels,**capacities)
        self.assertTrue(result.committed.item());self.assertEqual(result.errors.cpu().tolist(),[0])

    def test_empty_selection_and_empty_batch(self):
        _,state,ids,forest,labels=self.setup_batch([{}]);kinds=torch.zeros(1,dtype=torch.int64,device='mps')
        result=append_events(state,ids,forest,kinds,labels,selected=torch.zeros(1,dtype=torch.bool,device='mps'))
        self.assertTrue(result.committed.item());self.assertEqual(result.accepted.cpu().tolist(),[False])
        self.assertEqual([e.serialize() for e in state.restore_envs()],[e.serialize() for e in result.state.restore_envs()])
        empty=state.fork([]);empty_ids=replace(ids,source=empty,state_keys=replace(ids.state_keys,
            words=ids.state_keys.words[:0],hex_bytes=ids.state_keys.hex_bytes[:0],errors=ids.state_keys.errors[:0],
            count=torch.tensor([0],dtype=torch.int64,device='mps')))
        payload=EventPayloads(empty,forest.records[:0],forest.lengths[:0],forest.errors[:0])
        result=append_events(empty,empty_ids,payload,kinds[:0],labels)
        self.assertTrue(result.committed.item());self.assertEqual(result.state.lane_count,0)


if __name__=='__main__':unittest.main()
