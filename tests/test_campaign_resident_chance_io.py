"""Complete chance payload, RNG installation and native transaction parity."""
from dataclasses import replace
import json
import struct
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from tests.test_campaign_device_state import real_states
from tests.test_campaign_packed_chance import chance_env
from tests.test_campaign_random_metal import request, die, streams
from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.packed_chance_metal import sample_packed_chance
from studies.campaign.backends.resident_chance_io import (
    ChanceIOError, build_chance_payload, install_sampled_randomness,
)
from studies.campaign.backends.resident_events import EventKind, EventLabels, append_events
from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
from studies.campaign.backends.resident_state_json import ResidentStateJson
from studies.campaign.backends.device_strings import intern_bytes


EXACT_MPS = torch.backends.mps.is_available() and mps_int64_indexing_supported()
MASK64 = (1 << 64)-1


def decode_payloads(payloads):
    """Independent test-only generic JSON decoder, outside resident execution."""
    state=payloads.source
    used,byte_count=state.suffix_usage.cpu().tolist()
    strings=[]
    for data,offsets in ((bytes(state.context.native.string_bytes()),list(state.context.native.string_offsets())),
            (bytes(state.string_bytes[:byte_count].cpu().tolist()),state.string_offsets[:used+1].cpu().tolist())):
        strings.extend(data[a:b].decode('utf8') for a,b in zip(offsets,offsets[1:]))
    output=[]
    for rows,length,error in zip(payloads.records.cpu().tolist(),payloads.lengths.cpu().tolist(),payloads.errors.cpu().tolist(),strict=True):
        if error:
            output.append(None);continue
        def parse(at):
            tag,count,lo,hi,end=rows[at]
            if tag==5:return strings[count],end
            if tag==4:return struct.unpack('=d',struct.pack('=Q',lo|(hi<<32)))[0],end
            if tag==12:
                values=[];cursor=at+1
                for _ in range(count):
                    value,cursor=parse(cursor);values.append(value)
                assert cursor==end
                return values,end
            if tag==13:
                values={};cursor=at+1
                for _ in range(count):
                    key,cursor=parse(cursor);value,cursor=parse(cursor);values[key]=value
                assert cursor==end
                return values,end
            raise AssertionError(f'Unexpected generic JSON tag {tag}')
        value,end=parse(0);assert end==length;output.append(value)
    return output


@unittest.skipUnless(EXACT_MPS,'Exact Apple GPU integer execution unavailable')
class ResidentChanceIOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads);torch.mps.empty_cache()

    def capture(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),'mps')
        native=gwrl_cpp.capture_device_states(context.native,envs)
        return DeviceStateBatch.from_native(native,context=context),native

    def assert_same(self,source,output):
        self.assertTrue(torch.equal(source.records,output.records))
        self.assertTrue(torch.equal(source.lengths,output.lengths))
        self.assertTrue(torch.equal(source.sections,output.sections))
        self.assertTrue(torch.equal(source.suffix_usage,output.suffix_usage))
        self.assertTrue(torch.equal(source.string_bytes,output.string_bytes))
        self.assertTrue(torch.equal(source.string_offsets,output.string_offsets))

    def test_all_streams_full_unsigned_words_tapes_rerolls_and_number_bits(self):
        specs=[request([die(3),die(12,maximum=3,rerolls=[1,2])]),
               request([die(6,maximum=2,rerolls=[1,2]),die(12)]),request([die(20)]),
               request([die((1<<31)-1,maximum=33,rerolls=[1]),die(12)])]
        specs[0]['id']='chance/request/蒙古\u0000';specs[-1]['id']='fullwidth_faces'
        initial=[streams(actual=MASK64,search=1<<63,training=(1<<63)+17),
                 streams(actual=MASK64,search=1<<63,active='search',tape=[6,1,2,5,12],position=1),
                 streams(actual=MASK64,training=(1<<63)+17,active='training'),
                 streams(actual=MASK64,search=1<<63,training=MASK64,active='training',tape=[1]*33+[(1<<31)-1,12])]
        envs=[chance_env(q,r) for q,r in zip(specs,initial,strict=True)]
        expected=gwrl_cpp.campaign_sample_chance_probe([json.dumps(q) for q in specs],[json.dumps(r) for r in initial])['rows']
        before,_=self.capture(envs);after=before.snapshot()
        sample=sample_packed_chance(before,dice_capacity=2,roll_capacity=34)
        payload=build_chance_payload(before,after,sample,capacity=80)
        self.assertIs(payload.payloads.source,after)
        self.assertEqual(payload.errors.cpu().tolist(),[0]*4)
        self.assertEqual(decode_payloads(payload.payloads),[
            {'outcome':{'faces':row['faces']},'request_id':spec['id']} for row,spec in zip(expected,specs,strict=True)])
        self.assertEqual(payload.required_capacity.cpu().tolist(),[7+len(row['faces'])+sum(map(len,row['faces'])) for row in expected])
        committed=install_sampled_randomness(before,after,sample)
        self.assertTrue(committed.committed.item());self.assertEqual(committed.errors.cpu().tolist(),[0]*4)
        for original,restored,oracle in zip(envs,committed.state.restore_envs(),expected,strict=True):
            value=json.loads(restored.serialize());self.assertEqual(value['random'],json.loads(oracle['random']))
            self.assertEqual(value['state'],json.loads(original.serialize())['state'])
        # Faces are NumberBits, including INT_MAX; no float32 intermediate.
        for lane,oracle in enumerate(expected):
            actual=[lo|(hi<<32) for tag,_,lo,hi,_ in payload.payloads.records[lane].cpu().tolist() if tag==4]
            wanted=[struct.unpack('=Q',struct.pack('=d',float(face)))[0] for path in oracle['faces'] for face in path]
            self.assertEqual(actual,wanted)

    def test_actual_native_resolve_chance_event_effects_and_rng_match(self):
        for active in ('actual','search','training'):
            with self.subTest(active=active):
                native=real_states()[1]
                doc=json.loads(native.serialize());doc['random'].update(
                    actual=str(MASK64),search=str(1<<63),training=str((1<<63)+17),active=active)
                native.restore(json.dumps(doc));expected=native.clone();expected.resolve_chance()
                final=json.loads(expected.serialize());event=final['state']['history'][-1]
                self.assertEqual(event['kind'],'chance')
                # Test oracle supplies the already-completed rule effects. The
                # implementation under test supplies payload/Event/RNG only.
                proposal=json.loads(expected.serialize());proposal['state']['history'].pop();proposal['random']=doc['random']
                proposed=native.clone();proposed.restore(json.dumps(proposal))
                cohort,native_batch=self.capture([native,proposed])
                before=cohort.fork([0]);after=cohort.fork([1])
                sampled=sample_packed_chance(before,dice_capacity=8,roll_capacity=4)
                payload=build_chance_payload(before,after,sampled,capacity=128)
                self.assertEqual(decode_payloads(payload.payloads),[event['payload']])
                formatter=ResidentStateJson(CanonicalJsonContext(native_batch,after.context))
                identities=formatter.identities(after,byte_capacity=262144)
                labels=EventLabels(after.context,torch.tensor(after.context.prefix_lookup_ids(('action','interrupt','chance')),
                    dtype=torch.int64,device='mps'))
                appended=append_events(after,identities,payload.payloads,torch.full((1,),EventKind.CHANCE,dtype=torch.int64,device='mps'),labels,
                    state_capacity=after.records.shape[1]+131,block_capacity=after.records.shape[1]+131,
                    string_capacity=after.string_offsets.numel(),byte_capacity=after.string_bytes.numel()+64)
                self.assertTrue(appended.committed.item(),appended.errors.cpu().tolist())
                result=install_sampled_randomness(before,appended.state,sampled)
                self.assertTrue(result.committed.item(),result.errors.cpu().tolist())
                restored=result.state.restore_envs()[0]
                self.assertEqual(restored.serialize(),expected.serialize())

    def test_capacity_reports_exact_size_and_retry_loses_no_face_path(self):
        spec=request([die(12,maximum=2,rerolls=[1,2]),die(6)])
        before,_=self.capture([chance_env(spec,streams(tape=[1,2,12,6]))]);after=before.snapshot()
        sampled=sample_packed_chance(before,dice_capacity=2,roll_capacity=3)
        old=before.records.clone()
        for capacity in (0,12):
            failed=build_chance_payload(before,after,sampled,capacity=capacity)
            self.assertEqual(failed.errors.cpu().tolist(),[ChanceIOError.CAPACITY])
            self.assertEqual(failed.required_capacity.cpu().tolist(),[13])
            self.assertEqual(failed.payloads.lengths.cpu().tolist(),[0])
            self.assertEqual(torch.count_nonzero(failed.payloads.records).item(),0)
            self.assert_same(before,after)
        retried=build_chance_payload(before,after,sampled,capacity=13)
        self.assertEqual(decode_payloads(retried.payloads),[{'outcome':{'faces':[[1,2,12],[6]]},'request_id':'sample'}])
        self.assertTrue(torch.equal(before.records,old))

    def test_sampler_errors_roll_back_cohort_and_unselected_errors_do_not_veto(self):
        good=chance_env(request([die()]),streams())
        bad=chance_env(request([die(),die()]),streams(tape=[12]))
        before,_=self.capture([good,bad]);after=before.snapshot()
        sampled=sample_packed_chance(before,dice_capacity=2,roll_capacity=1)
        payload=build_chance_payload(before,after,sampled,capacity=32)
        self.assertTrue(payload.errors[1].item()&ChanceIOError.SAMPLER)
        failed=install_sampled_randomness(before,after,sampled)
        self.assertFalse(failed.committed.item());self.assert_same(after,failed.state)
        self.assertTrue(failed.errors[1].item()&ChanceIOError.SAMPLER)
        selected=torch.tensor([True,False],dtype=torch.bool,device='mps')
        result=install_sampled_randomness(before,after,sampled,selected)
        self.assertTrue(result.committed.item());self.assertEqual(result.accepted.cpu().tolist(),[True,False])
        self.assertTrue(torch.equal(result.state.records[1],after.records[1]))
        # A pure allocation failure is also a failed, non-consumed sample.
        capacity_sample=sample_packed_chance(before,dice_capacity=0,roll_capacity=0)
        failed=install_sampled_randomness(before,after,capacity_sample,selected)
        self.assertFalse(failed.committed.item());self.assert_same(after,failed.state)

    def test_random_stale_and_double_commits_never_change_after(self):
        before,_=self.capture([chance_env(request([die()]),streams(actual=MASK64))]);after=before.snapshot()
        sample=sample_packed_chance(before,dice_capacity=1,roll_capacity=1)
        once=install_sampled_randomness(before,after,sample)
        self.assertTrue(once.committed.item())
        twice=install_sampled_randomness(before,once.state,sample)
        self.assertFalse(twice.committed.item());self.assert_same(once.state,twice.state)
        self.assertTrue(twice.errors.item()&ChanceIOError.RANDOM_CHANGED)
        for section in ('random.actual','random.search','random.training','random.tape_position','random.active'):
            changed=after.records.clone();root=after.section(section).item()
            if section=='random.active':changed[0,root,1]=after.context.random_stream_ids[1]
            else:changed[0,root,2]^=1
            proposal=replace(after,records=changed)
            result=install_sampled_randomness(before,proposal,sample)
            self.assertFalse(result.committed.item());self.assert_same(proposal,result.state)
        taped,_=self.capture([chance_env(request([die()]),streams(tape=[12]))])
        sample=sample_packed_chance(taped,dice_capacity=1,roll_capacity=1)
        records=taped.records.clone();root=taped.section('random.test_tape').item()
        records[0,root+1,2]=11
        proposal=replace(taped,records=records)
        result=install_sampled_randomness(taped,proposal,sample)
        self.assertFalse(result.committed.item());self.assert_same(proposal,result.state)
        self.assertTrue(result.errors.item()&ChanceIOError.RANDOM_CHANGED)

    def test_append_only_pool_extensions_are_valid_but_rewrites_roll_back(self):
        before,_=self.capture([chance_env(request([die()]),streams())])
        sample=sample_packed_chance(before,dice_capacity=1,roll_capacity=1)
        extra=intern_bytes(before,torch.tensor([list(b'new chance field')],dtype=torch.uint8,device='mps'),
            torch.tensor([16],dtype=torch.int64,device='mps'),
            string_capacity=before.string_offsets.numel(),byte_capacity=before.string_bytes.numel()+16)
        self.assertTrue(extra.committed.item())
        payload=build_chance_payload(before,extra.state,sample,capacity=16)
        self.assertEqual(payload.errors.cpu().tolist(),[0])
        self.assertTrue(install_sampled_randomness(before,extra.state,sample).committed.item())
        self.assertGreater(before.string_bytes.numel(),0)
        changed=extra.state.string_bytes.clone();changed[0]^=1
        bad=replace(extra.state,string_bytes=changed)
        failed=install_sampled_randomness(before,bad,sample)
        self.assertFalse(failed.committed.item());self.assert_same(bad,failed.state)
        self.assertTrue(failed.errors.item()&ChanceIOError.STRING_POOL)
        self.assertTrue(build_chance_payload(before,bad,sample,capacity=16).errors.item()&ChanceIOError.STRING_POOL)

    def test_source_binding_metadata_and_hot_path_have_no_host_reads(self):
        before,_=self.capture([chance_env(request([die()]),streams())]);after=before.snapshot()
        sampled=sample_packed_chance(before,dice_capacity=1,roll_capacity=1)
        for stale in (replace(sampled,source=before.snapshot()),):
            with self.assertRaisesRegex(ValueError,'complete source'):build_chance_payload(before,after,stale,capacity=16)
            with self.assertRaisesRegex(ValueError,'complete source'):install_sampled_randomness(before,after,stale)
        with self.assertRaises(ValueError):install_sampled_randomness(before,after,sampled,torch.ones(1,dtype=torch.int64,device='mps'))
        with self.assertRaises(ValueError):build_chance_payload(before,after,replace(sampled,faces=sampled.faces.float()),capacity=16)
        with self.assertRaises(ValueError):build_chance_payload(before,after,sampled,capacity=-1)
        old_before,old_after=before.records.clone(),after.records.clone()
        with patch.object(torch.Tensor,'cpu',side_effect=AssertionError('host read')), \
             patch.object(torch.Tensor,'tolist',side_effect=AssertionError('host list')), \
             patch.object(torch.Tensor,'item',side_effect=AssertionError('host scalar')), \
             patch.object(torch.Tensor,'numpy',side_effect=AssertionError('host numpy')), \
             patch.object(torch.Tensor,'__bool__',side_effect=AssertionError('host boolean')), \
             patch.object(json,'loads',side_effect=AssertionError('JSON parse')), \
             patch.object(json,'dumps',side_effect=AssertionError('JSON serialization')):
            payload=build_chance_payload(before,after,sampled,capacity=16)
            result=install_sampled_randomness(before,after,sampled)
        self.assertTrue(result.committed.item());self.assertEqual(payload.errors.item(),0)
        self.assertTrue(torch.equal(before.records,old_before));self.assertTrue(torch.equal(after.records,old_after))

    def test_empty_batch_retains_shapes_and_source_errors_are_atomic(self):
        before,_=self.capture([chance_env(request([die()]),streams())]);empty=before.fork([])
        sampled=sample_packed_chance(empty,dice_capacity=0,roll_capacity=0)
        payload=build_chance_payload(empty,empty,sampled,capacity=0)
        result=install_sampled_randomness(empty,empty,sampled)
        self.assertEqual(tuple(payload.payloads.records.shape),(0,0,5));self.assertTrue(result.committed.item())
        before=before.fork([0,0]);after=replace(before,errors=torch.tensor([0,1],dtype=torch.int64,device='mps'))
        sampled=sample_packed_chance(before,dice_capacity=1,roll_capacity=1)
        failed=install_sampled_randomness(before,after,sampled)
        self.assertFalse(failed.committed.item());self.assertEqual(failed.errors.cpu().tolist(),[0,ChanceIOError.SOURCE])
        self.assert_same(after,failed.state)


if __name__=='__main__':unittest.main()
