"""All current ID formulas plus original native and scheduler menu identities."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from tests.test_campaign_device_state import SCENARIO,real_states
from tests.test_campaign_action_interface import ship_fixture
from studies.campaign.curriculum import make_env
from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext,canonical_json_subtrees,canonical_json_digests
from studies.campaign.backends.content_digest_metal import pack_messages,content_digests_metal
from studies.campaign.backends.resident_action_ids import (
    ActionIdFamily as F,ActionIdStrings,construct_action_ids,action_id_strings,inspect_action_ids)

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def packed_fields(rows):
    data=bytearray();ranges=[]
    for row in rows:
        fields=[]
        for value in row:
            if value is None:fields.append((-1,-1));continue
            start=len(data);data.extend(value);fields.append((start,len(data)))
        ranges.append(fields)
    return ActionIdStrings(torch.tensor(data,dtype=torch.uint8,device='mps'),
        torch.tensor(ranges,dtype=torch.int64,device='mps').reshape(len(rows),4,2))


def digests_for(parameters):
    # Explicit oracle/initialization boundary. Runtime construction receives the
    # resulting already-resident canonical digests, never these Python objects.
    canonical=gwrl_cpp.campaign_canonical_json_probe([json.dumps(value,ensure_ascii=False) for value in parameters])
    return content_digests_metal(pack_messages(tuple(value.encode('utf8') for value in canonical),device='mps'))


@unittest.skipUnless(EXACT_MPS,'Lossless Apple GPU runtime unavailable')
class ResidentActionIdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(2)

    def assert_formula(self,families,fields,parameters,capacity=1024):
        expected=tuple(gwrl_cpp.campaign_action_id_formula_probe([int(x) for x in families],fields,
            [json.dumps(p,ensure_ascii=False) for p in parameters]))
        result=construct_action_ids(torch.tensor(families,dtype=torch.int64,device='mps'),packed_fields(fields),
            digests_for(parameters),byte_capacity=capacity)
        self.assertEqual(inspect_action_ids(result),expected)
        return result

    def test_all_twelve_families_exact_utf8_nul_and_arbitrary_native_bytes(self):
        fields=[(b'kind_\x00_\xff','蒙古'.encode(),b'active_\xff',b'air_decision_99') for _ in F]
        parameters=[{'nested':[True,None,0.1,1e200],'control':'\u0000\\"','unicode':'蒙古'} for _ in F]
        self.assert_formula(list(F),fields,parameters)
        self.assert_formula(list(F),[(b'',b'',b'',b'') for _ in F],[{} for _ in F])

    def test_actual_original_factory_menus_keep_every_ordered_id(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),17)
        actions=list(env.legal_actions())+list(real_states()[2].legal_actions())
        political=env.clone()
        for _ in range(4):political.apply_action(next(a for a in political.legal_actions() if a.kind=='end_phase'))
        actions.extend(political.legal_actions())
        ships=ship_fixture().raw
        actions.extend(ships.legal_actions())
        ships.apply_action(next(a for a in ships.legal_actions() if a.kind=='naval_start_move'))
        actions.extend(ships.legal_actions())
        # Include the public major-alignment interrupt menu. The outer
        # PoliticsRules currently exposes political interrupts only; its unused
        # movement grant-rail constructor is covered by the formula corpus.
        document=json.loads(env.serialize());state=document['state'];state['clock']['phase']='non_combat_movement'
        for name in ('ccp','kmt'):
            state['nations'][name].update(power_status='major',alliance='same-explicit-alliance',at_war_with=['japan'])
        grants=env.clone();grants.restore(json.dumps(document));actions.extend(grants.legal_interrupts())
        families=[];fields=[];parameters=[];expected=[]
        for action in actions:
            args=action.parameters
            row=(action.kind.encode(),action.nation.encode(),str(args.get('requester','')).encode(),
                 (action.decision or '').encode())
            candidates=list(range(9))
            if action.decision is None:candidates.remove(int(F.AIR_DECISION))
            found=gwrl_cpp.campaign_action_id_formula_probe(candidates,[row]*len(candidates),[json.dumps(args)]*len(candidates))
            matching=[family for family,value in zip(candidates,found,strict=True) if value==action.id.encode()]
            self.assertEqual(len(matching),1,(action.kind,action.id,matching))
            families.append(matching[0]);fields.append(row);parameters.append(args);expected.append(action.id.encode())
        self.assertTrue({int(F.END_PHASE),int(F.POLITICAL),int(F.KIND_COLON64),int(F.KIND_UNDERSCORE20)}<=set(families),set(families))
        result=self.assert_formula(families,fields,parameters)
        self.assertEqual(inspect_action_ids(result),tuple(expected))

    def test_actual_scheduled_offer_pass_and_play_ids(self):
        env=make_env(17,calendar_rounds=2)
        scheduled=list(env.legal_actions())
        while env.decision_kind()=='declaration_offer':
            env.apply_action(next(a for a in env.legal_actions() if a.kind=='pass_interrupt'))
        scheduled.extend(env.legal_actions())
        families=[];fields=[]
        for action in scheduled:
            if action.kind=='pass_interrupt':families.append(F.SCHEDULED_PASS);fields.append((b'',action.player.encode(),b'',b''))
            else:
                families.append(F.SCHEDULED_INTERRUPT if action.kind=='interrupt' else F.SCHEDULED_PLAY)
                fields.append((action.raw['id'].encode(),b'',b'',b''))
        result=self.assert_formula(families,fields,[{} for _ in scheduled])
        self.assertEqual(inspect_action_ids(result),tuple(action.id.encode() for action in scheduled))

    def test_canonical_parameter_json_to_ids_stays_resident(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),17);parameters=[{'z':'蒙古','a':[0.1,False,None]},{}]
        envs=[]
        for params in parameters:
            doc=json.loads(env.serialize());doc['state']['history']=[{'kind':'id_probe','payload':params,'after_state_key':'ignored'}]
            current=env.clone();current.restore(json.dumps(doc));envs.append(current)
        context=DeviceStateContext(gwrl_cpp.device_state_context(env),'mps')
        native=gwrl_cpp.capture_device_states(context.native,envs);state=DeviceStateBatch.from_native(native,context=context)
        formatter=CanonicalJsonContext(native,context)
        requests=torch.stack((torch.arange(2,dtype=torch.int64,device='mps'),state.section('state.history')+3),dim=1)
        fields=[(b'politics_declare_war',b'japan',None,None),(b'economy_finish_research',None,None,None)]
        strings=packed_fields(fields);families=torch.tensor([F.POLITICAL,F.KIND_COLON64],dtype=torch.int64,device='mps')
        # Compile/warm outside the no-host-read witness.
        encoded=canonical_json_subtrees(state,requests,formatter,byte_capacity=512)
        construct_action_ids(families,strings,canonical_json_digests(encoded),byte_capacity=256);torch.mps.synchronize()
        fail=AssertionError('Host serialization/read forbidden in action ID construction')
        with patch.object(torch.Tensor,'cpu',side_effect=fail),patch.object(torch.Tensor,'item',side_effect=fail),\
             patch.object(torch.Tensor,'tolist',side_effect=fail),patch.object(json,'loads',side_effect=fail),\
             patch.object(json,'dumps',side_effect=fail):
            encoded=canonical_json_subtrees(state,requests,formatter,byte_capacity=512)
            result=construct_action_ids(families,strings,canonical_json_digests(encoded),byte_capacity=256)
        oracle_fields=[tuple(b'' if value is None else value for value in row) for row in fields]
        expected=gwrl_cpp.campaign_action_id_formula_probe([1,5],oracle_fields,[json.dumps(x) for x in parameters])
        self.assertEqual(inspect_action_ids(result),tuple(expected))

    def test_native_string_ids_resolve_without_download_and_cow_suffix_works(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),17);state=DeviceStateBatch.capture([env],device='mps')
        ids=state.context.prefix_lookup_ids(('infantry','japan','kmt','ccp'))
        values=torch.tensor([list(map(int,ids)),[-1,-1,-1,-1]],dtype=torch.int64,device='mps')
        strings=action_id_strings(state,values);digests=digests_for([{},{}])
        result=construct_action_ids(torch.tensor([F.POLITICAL,F.END_PHASE],dtype=torch.int64,device='mps'),strings,digests,byte_capacity=256)
        expected=gwrl_cpp.campaign_action_id_formula_probe([1,0],[(b'infantry',b'japan',b'kmt',b'ccp'),(b'',)*4],['{}','{}'])
        self.assertEqual(inspect_action_ids(result),tuple(expected))
        from studies.campaign.backends.device_strings import intern_bytes
        # Explicit new descriptor input; interning and subsequent use remain resident.
        raw=torch.tensor([list(b'new_kind')],dtype=torch.uint8,device='mps')
        length=torch.tensor([8],dtype=torch.int64,device='mps')
        added=intern_bytes(state,raw,length,string_capacity=state.string_offsets.numel()+1,byte_capacity=state.string_bytes.numel()+8)
        updated=values.clone();updated[0,0]=added.ids[0]
        strings=action_id_strings(added.state,updated)
        result=construct_action_ids(torch.tensor([F.POLITICAL,F.END_PHASE],dtype=torch.int64,device='mps'),strings,digests,byte_capacity=256)
        expected=gwrl_cpp.campaign_action_id_formula_probe([1,0],[(b'new_kind',b'japan',b'kmt',b'ccp'),(b'',)*4],['{}','{}'])
        self.assertEqual(inspect_action_ids(result),tuple(expected))

    def test_capacity_failure_exact_requirement_retry_and_no_truncation(self):
        rows=[(b'long_'*30,b'japan',b'ccp',b'decision')]
        families=torch.tensor([F.KIND_COLON64],dtype=torch.int64,device='mps');strings=packed_fields(rows);digests=digests_for([{}])
        expected=gwrl_cpp.campaign_action_id_formula_probe([5],rows,['{}'])[0]
        for capacity in (0,3,len(expected)-1):
            result=construct_action_ids(families,strings,digests,byte_capacity=capacity)
            self.assertEqual(result.errors.cpu().tolist(),[2]);self.assertEqual(result.lengths.cpu().tolist(),[0])
            self.assertEqual(result.required_bytes.cpu().tolist(),[len(expected)])
            with self.assertRaises(ValueError):inspect_action_ids(result)
        result=construct_action_ids(families,strings,digests,byte_capacity=len(expected))
        self.assertEqual(inspect_action_ids(result),(expected,))

    def test_missing_bad_fields_digest_errors_and_unused_rows_are_explicit(self):
        families=torch.tensor([F.END_PHASE,F.POLITICAL,F.KIND_COLON64,F.RAIL_PERMISSION],dtype=torch.int64,device='mps')
        strings=packed_fields([(None,)*4,(None,b'japan',None,None),(b'kind',None,None,None),(None,b'japan',b'ccp',None)])
        digests=digests_for([{}]*4);bad=replace(digests,errors=torch.tensor([99,0,1,99],dtype=torch.int32,device='mps'))
        result=construct_action_ids(families,strings,bad,byte_capacity=256)
        self.assertEqual(result.errors.cpu().tolist(),[0,1,4,0])
        self.assertEqual(result.lengths.cpu().tolist()[0],9)
        short=replace(digests,count=torch.tensor([1],dtype=torch.int64,device='mps'))
        result=construct_action_ids(families,strings,short,byte_capacity=256)
        self.assertEqual(inspect_action_ids(result),(b'end_phase',));self.assertEqual(result.lengths.cpu().tolist()[1:],[0,0,0])
        for count in (-1,5):
            result=construct_action_ids(families,strings,replace(digests,count=torch.tensor([count],dtype=torch.int64,device='mps')),byte_capacity=256)
            with self.assertRaises(ValueError):inspect_action_ids(result)
        corrupt=digests.hex_bytes.clone();corrupt[2,0]=ord('G')
        result=construct_action_ids(families,strings,replace(digests,hex_bytes=corrupt),byte_capacity=256)
        self.assertEqual(result.errors.cpu().tolist()[2],4)

    def test_empty_device_and_strided_metadata_guards(self):
        digests=content_digests_metal(pack_messages((),device='mps'))
        empty=construct_action_ids(torch.empty(0,dtype=torch.int64,device='mps'),packed_fields([]),digests,byte_capacity=0)
        self.assertEqual(inspect_action_ids(empty),())
        families=torch.tensor([F.END_PHASE],dtype=torch.int64,device='mps');strings=packed_fields([(None,)*4]);digests=digests_for([{}])
        with self.assertRaises(ValueError):construct_action_ids(families.cpu(),strings,digests,byte_capacity=10)
        with self.assertRaises(ValueError):construct_action_ids(families,strings,digests,byte_capacity=-1)
        padded=torch.empty((1,4,4),dtype=torch.int64,device='mps');padded[:,:,::2]=strings.ranges
        with self.assertRaises(ValueError):construct_action_ids(families,replace(strings,ranges=padded[:,:,::2]),digests,byte_capacity=10)


if __name__=='__main__':unittest.main()
