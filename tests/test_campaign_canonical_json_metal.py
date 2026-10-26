"""Native canonical byte/hash parity from complete resident JSON payloads."""
from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path
import random
import struct
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.metal_validation import mps_int64_indexing_supported

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()
from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.canonical_json_metal import (
    CanonicalJsonContext,canonical_json_subtrees,inspect_canonical_json,canonical_json_digests)
from studies.campaign.backends.content_digest_metal import inspect_digests

SCENARIO=Path(__file__).resolve().parents[1]/'game_content/scenarios/japan_china_1936'


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class CanonicalJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(2)

    def setup_batch(self,payloads):
        original=gwrl_cpp.CampaignEnv(str(SCENARIO),123)
        envs=[]
        for payload in payloads:
            doc=json.loads(original.serialize());doc['state']['history']=[
                {'kind':'canonical_probe','payload':{'test':payload},'after_state_key':'preserved'}]
            env=original.clone();env.restore(json.dumps(doc));envs.append(env)
        native_context=gwrl_cpp.device_state_context(original)
        context=DeviceStateContext(native_context,'mps')
        native=gwrl_cpp.capture_device_states(native_context,envs)
        state=DeviceStateBatch.from_native(native,context=context)
        formatter=CanonicalJsonContext(native,context)
        requests=torch.stack((torch.arange(len(envs),dtype=torch.int64,device='mps'),state.sections[:,18]+3),dim=1)
        expected=gwrl_cpp.campaign_canonical_json_probe([json.dumps({'test':p}) for p in payloads])
        return state,requests,formatter,tuple(s.encode() for s in expected)

    def test_native_strings_control_bytes_utf8_nesting_and_doubles(self):
        deep='leaf'
        for _ in range(130):deep=[deep]
        values=[None,True,False,'',{'z':[],'a':{}},'蒙古 / "+\\\n\t\r\u0000\u001f',
                [0,-0.0,1,-1,2147483647,-2147483648,2147483648,1.0000000000000002,
                 1e200,1e-200,0.1,9007199254740991,9007199254740992],deep]
        state,requests,formatter,expected=self.setup_batch(values)
        before=state.records.clone()
        with patch.object(torch.Tensor,'cpu',side_effect=AssertionError('host read')), \
             patch.object(torch.Tensor,'tolist',side_effect=AssertionError('host list')), \
             patch.object(torch.Tensor,'item',side_effect=AssertionError('host scalar')):
            result=canonical_json_subtrees(state,requests,formatter,byte_capacity=2048)
            hashes=canonical_json_digests(result)
        self.assertEqual(inspect_canonical_json(result),expected)
        self.assertEqual(inspect_digests(hashes),tuple(hashlib.sha256(s).hexdigest() for s in expected))
        self.assertTrue(torch.equal(before,state.records))

    def test_arbitrary_finite_bit_patterns_use_native_spelling_once(self):
        rng=random.Random(19);values=[]
        while len(values)<100:
            bits=rng.getrandbits(64)
            if ((bits>>52)&2047)==2047:continue
            value=struct.unpack('d',bits.to_bytes(8,'little'))[0]
            # Native parser correctly rejects underflowing decimal source. Keep
            # corpus normal here; no GPU value is rounded for this selection.
            if 0<abs(value)<2.2250738585072014e-308:continue
            values.append(value)
        state,requests,formatter,expected=self.setup_batch([values])
        result=canonical_json_subtrees(state,requests,formatter,byte_capacity=8192)
        self.assertEqual(inspect_canonical_json(result),expected)

    def test_capacity_failure_reports_full_requirement_and_retry(self):
        state,requests,formatter,expected=self.setup_batch([{'x':'long '+('"\\\u0000'*40)}])
        small=canonical_json_subtrees(state,requests,formatter,byte_capacity=3)
        self.assertEqual(small.errors.cpu().tolist(),[2])
        self.assertEqual(small.lengths.cpu().tolist(),[0])
        self.assertEqual(small.required_bytes.cpu().tolist(),[len(expected[0])])
        with self.assertRaises(ValueError):inspect_canonical_json(small)
        with self.assertRaises(ValueError):inspect_digests(canonical_json_digests(small))
        retry=canonical_json_subtrees(state,requests,formatter,byte_capacity=len(expected[0]))
        self.assertEqual(inspect_canonical_json(retry),expected)

    def test_new_exact_integer_bits_and_unknown_noninteger_are_distinct(self):
        state,requests,formatter,_=self.setup_batch([[0.1]])
        # Replace the already resident 0.1 node, preserving all record tags/ends.
        records=state.records.clone();rows=records[0]
        target=next(i for i,row in enumerate(rows.cpu().tolist()) if row[0]==4 and
                    (row[2]|(row[3]<<32))==struct.unpack('Q',struct.pack('d',0.1))[0])
        def with_number(value):
            changed=records.clone();bits=struct.unpack('Q',struct.pack('d',value))[0]
            changed[0,target,2]=bits&0xffffffff;changed[0,target,3]=bits>>32
            return replace(state,records=changed)
        integer=canonical_json_subtrees(with_number(-2147483648),requests,formatter,byte_capacity=100)
        self.assertEqual(inspect_canonical_json(integer),(b'{"test":[-2147483648]}',))
        unknown=canonical_json_subtrees(with_number(0.123456789),requests,formatter,byte_capacity=100)
        self.assertEqual(unknown.errors.cpu().tolist(),[4])
        with self.assertRaises(ValueError):inspect_digests(canonical_json_digests(unknown))

    def test_invalid_nodes_order_count_source_and_unused_capacity(self):
        state,requests,formatter,expected=self.setup_batch([{'a':1,'b':2},True])
        count=torch.tensor([1],dtype=torch.int64,device='mps')
        result=canonical_json_subtrees(state,requests,formatter,byte_capacity=100,count=count)
        self.assertEqual(inspect_canonical_json(result),expected[:1])
        self.assertEqual(result.lengths.cpu().tolist()[1],0)
        bad=canonical_json_subtrees(state,requests,formatter,byte_capacity=100,
                                   count=torch.tensor([3],dtype=torch.int64,device='mps'))
        with self.assertRaisesRegex(ValueError,'count'):inspect_canonical_json(bad)
        for root in (-1,state.records.shape[1]):
            forged=requests.clone();forged[0,1]=root
            bad=canonical_json_subtrees(state,forged,formatter,byte_capacity=100)
            self.assertEqual(bad.errors.cpu().tolist()[0],1)
        errors=state.errors.clone();errors[0]=99
        bad=canonical_json_subtrees(replace(state,errors=errors),requests,formatter,byte_capacity=100)
        self.assertEqual(bad.errors.cpu().tolist()[0],8)
        records=state.records.clone();root=requests[0,1].item();records[0,root,1]=2**60
        bad=canonical_json_subtrees(replace(state,records=records),requests,formatter,byte_capacity=100)
        self.assertEqual(bad.errors.cpu().tolist()[0],1)

    def test_empty_requests_and_explicit_device_layout(self):
        state,requests,formatter,_=self.setup_batch([{}])
        empty=requests[:0]
        result=canonical_json_subtrees(state,empty,formatter,byte_capacity=0)
        self.assertEqual(inspect_canonical_json(result),())
        self.assertEqual(inspect_digests(canonical_json_digests(result)),())
        with self.assertRaisesRegex(ValueError,'contiguous'):
            canonical_json_subtrees(state,requests.cpu(),formatter,byte_capacity=100)
        with self.assertRaises(ValueError):canonical_json_subtrees(state,requests,formatter,byte_capacity=-1)

    def test_strided_state_buffers_are_rejected_before_native_pointer_use(self):
        state,requests,formatter,_=self.setup_batch([{},{}])
        def strided(value):
            larger=torch.empty((*value.shape,2),dtype=value.dtype,device=value.device)
            larger[...,0]=value
            return larger[...,0]
        for field in ('records','lengths','sections','errors','string_bytes','string_offsets','suffix_usage'):
            value=getattr(state,field)
            if value.numel()<2:continue
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'contiguous'):
                canonical_json_subtrees(replace(state,**{field:strided(value)}),requests,formatter,byte_capacity=100)
        for field in ('string_bytes','string_offsets'):
            previous=getattr(state.context,field)
            setattr(state.context,field,strided(previous))
            try:
                with self.assertRaisesRegex(ValueError,'contiguous'):
                    canonical_json_subtrees(state,requests,formatter,byte_capacity=100)
            finally:setattr(state.context,field,previous)


if __name__=='__main__':unittest.main()
