"""Complete native State bytes and both planning identities from packed MPS."""
from dataclasses import replace
import copy
import hashlib
import json
import struct
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from tests.test_campaign_device_state import real_states,rich_fixture,SCENARIO
from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext,SECTION_NAMES
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext,inspect_canonical_json
from studies.campaign.backends.content_digest_metal import inspect_digests
from studies.campaign.backends.resident_state_json import ResidentStateJson

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def changed(env,mutate):
    document=json.loads(env.serialize());mutate(document)
    out=env.clone();out.restore(json.dumps(document,ensure_ascii=False));return out


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class ResidentStateJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(2)

    def setup_batch(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),'mps')
        native=gwrl_cpp.capture_device_states(context.native,envs)
        state=DeviceStateBatch.from_native(native,context=context)
        return state,ResidentStateJson(CanonicalJsonContext(native,context))

    def assert_native(self,envs,capacity=262144):
        state,kernel=self.setup_batch(envs);before=[env.serialize() for env in envs]
        native=gwrl_cpp.campaign_state_json_oracle(envs)
        result=kernel.identities(state,byte_capacity=capacity)
        self.assertEqual(inspect_canonical_json(result.state_json),tuple(row['json'] for row in native))
        self.assertEqual(inspect_digests(result.state_keys),tuple(row['state_key'] for row in native))
        self.assertEqual(inspect_digests(result.engine_keys),tuple(row['engine_key'] for row in native))
        self.assertEqual(kernel.rules_literal,native[0]['rules_json'])
        for row,value in zip(native,inspect_canonical_json(result.engine_json),strict=True):
            expected=b'{"rules_id":'+row['rules_json']+b',"state_key":"'+row['state_key'].encode('ascii')+b'"}'
            self.assertEqual(value,expected)
        self.assertEqual([env.serialize() for env in envs],before)
        return state,kernel,result

    def test_complete_real_and_rich_states_pending_choices_chance_battles_and_repairs(self):
        self.assert_native(real_states()+[rich_fixture()])

    def test_all_phase_names_optional_null_zero_and_maximum_turn_serial(self):
        root=gwrl_cpp.CampaignEnv(str(SCENARIO),17)
        envs=[changed(root,lambda d,p=p:d['state']['clock'].update(phase=p)) for p in
              ('production','combat_movement','combat','non_combat_movement','place_units')]
        def edge(d):
            s=d['state'];s['clock']['player_turn_serial']=str(2**64-1)
            s['nations']['japan']['treasury']=0;s['nations']['mongolia']['treasury']=None
            s['nations']['mongolia']['alliance']=None;s['nations']['mongolia']['controller_nation']=None
            s['flags'].update({'min':-(2**31),'max':2**31-1,'蒙古\u0000':0})
        envs.append(changed(root,edge));self.assert_native(envs)

    def test_action_interface_is_included_only_when_nonempty(self):
        root=gwrl_cpp.CampaignEnv(str(SCENARIO),17,training_actions=True)
        root=changed(root,lambda d:d['state'].update(action_interface={}))
        second=changed(root,lambda d:d['state'].update(action_interface={
            'schema':'campaign-orders-v1','visited_configurations':[],'declined_rail_requests':[]}))
        _,_,result=self.assert_native([root,second])
        plain,nonempty=inspect_canonical_json(result.state_json)
        self.assertFalse(b'"action_interface"' in plain);self.assertTrue(b'"action_interface"' in nonempty)
        self.assertNotEqual(inspect_digests(result.state_keys)[0],inspect_digests(result.state_keys)[1])

    def test_history_and_every_rng_bit_are_excluded_from_both_keys(self):
        root=rich_fixture()
        def change(d):
            d['random'].update(actual='0',search=str(2**64-1),training=str(2**63),active='training',test_tape=[],tape_position='0')
            d['state']['history'].append({'kind':'more history','payload':{'unknown':0.123456789},'after_state_key':'ignored'})
        second=changed(root,change)
        _,_,result=self.assert_native([root,second])
        self.assertEqual(*inspect_canonical_json(result.state_json));self.assertEqual(*inspect_digests(result.state_keys))
        self.assertEqual(*inspect_digests(result.engine_keys))

    def test_capacity_failure_exact_requirement_and_retry_no_partial_identity(self):
        env=rich_fixture();state,kernel=self.setup_batch([env])
        failed=kernel.identities(state,byte_capacity=3)
        expected=gwrl_cpp.campaign_state_json_oracle([env])[0]
        self.assertEqual(failed.state_json.errors.cpu().tolist(),[2])
        self.assertEqual(failed.state_json.lengths.cpu().tolist(),[0])
        self.assertEqual(failed.state_json.required_bytes.cpu().tolist(),[len(expected['json'])])
        with self.assertRaises(ValueError):inspect_digests(failed.state_keys)
        with self.assertRaises(ValueError):inspect_digests(failed.engine_keys)
        retry=kernel.identities(state,byte_capacity=len(expected['json']))
        self.assertEqual(inspect_canonical_json(retry.state_json),(expected['json'],))
        self.assertEqual(inspect_digests(retry.engine_keys),(expected['engine_key'],))

    def test_arbitrarily_nested_generic_payload_uses_complete_stack(self):
        root=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        deep='leaf'
        for _ in range(180):deep={'deep':[deep]}
        env=changed(root,lambda d:d['state']['politics']['pending'].update({'deep-state':deep}))
        self.assert_native([env])

    def test_new_integer_number_bits_exact_unknown_noninteger_is_explicit(self):
        root=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        root=changed(root,lambda d:d['state']['politics']['pending'].update({'writer_probe':{'number':0.1}}))
        state,kernel=self.setup_batch([root]);rows=state.records[0].cpu().tolist()
        bits=struct.unpack('Q',struct.pack('d',0.1))[0]
        target=next(i for i,row in enumerate(rows) if row[0]==4 and row[2]|row[3]<<32==bits)
        def substitute(value):
            records=state.records.clone();raw=struct.unpack('Q',struct.pack('d',value))[0]
            records[0,target,2]=raw&0xffffffff;records[0,target,3]=raw>>32
            return replace(state,records=records)
        native=changed(root,lambda d:d['state']['politics']['pending']['writer_probe'].update(number=-(2**31)))
        result=kernel.identities(substitute(-(2**31)),byte_capacity=262144)
        expected=gwrl_cpp.campaign_state_json_oracle([native])[0]
        self.assertEqual(inspect_canonical_json(result.state_json),(expected['json'],))
        self.assertEqual(inspect_digests(result.engine_keys),(expected['engine_key'],))
        unknown=kernel.identities(substitute(0.123456789),byte_capacity=262144)
        self.assertEqual(unknown.state_json.errors.cpu().tolist(),[4])
        with self.assertRaises(ValueError):inspect_digests(unknown.engine_keys)

    def test_no_host_reads_or_native_calls_in_serialization_and_digest(self):
        env=rich_fixture();state,kernel=self.setup_batch([env]);kernel.identities(state,byte_capacity=262144);torch.mps.synchronize()
        fail=AssertionError('Host read/CPU serializer forbidden on resident State identity path')
        with patch.object(torch.Tensor,'cpu',side_effect=fail),patch.object(torch.Tensor,'tolist',side_effect=fail),\
             patch.object(torch.Tensor,'item',side_effect=fail),patch.object(json,'loads',side_effect=fail),\
             patch.object(json,'dumps',side_effect=fail),patch.object(gwrl_cpp,'capture_device_states',side_effect=fail),\
             patch.object(gwrl_cpp,'campaign_state_json_oracle',side_effect=fail):
            result=kernel.identities(state,byte_capacity=262144)
        self.assertIs(result.source,state);self.assertEqual(result.engine_keys.errors.cpu().tolist(),[0])

    def test_empty_source_errors_typed_corruption_foreign_and_strided_buffers(self):
        root=gwrl_cpp.CampaignEnv(str(SCENARIO),1);state,kernel=self.setup_batch([root])
        empty=state.fork([]);result=kernel.identities(empty,byte_capacity=0)
        self.assertEqual(inspect_canonical_json(result.state_json),());self.assertEqual(inspect_digests(result.engine_keys),())
        invalid=kernel.identities(replace(state,errors=torch.ones_like(state.errors)),byte_capacity=262144)
        self.assertEqual(invalid.state_json.errors.cpu().tolist(),[8])
        with self.assertRaises(ValueError):inspect_digests(invalid.engine_keys)
        records=state.records.clone();root_index=state.sections[0,SECTION_NAMES.index('state')].item();records[0,root_index,1]=20
        invalid=kernel.serialize(replace(state,records=records),byte_capacity=262144)
        self.assertEqual(invalid.errors.cpu().tolist(),[1])
        foreign=copy.copy(state.context)
        with self.assertRaises(ValueError):kernel.serialize(replace(state,context=foreign),byte_capacity=10)
        padded=torch.empty((*state.records.shape[:2],10),dtype=torch.int64,device='mps');padded[:,:,::2]=state.records
        with self.assertRaisesRegex(ValueError,'contiguous'):kernel.serialize(replace(state,records=padded[:,:,::2]),byte_capacity=10)


if __name__=='__main__':unittest.main()
