"""Exact public order-metadata reset, bounded allocation and full-state identity."""
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch
from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.resident_training_reset import ResidentTrainingReset
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from tests.test_campaign_action_interface import ship_fixture

SCENARIO=Path(__file__).resolve().parents[1]/'game_content/scenarios/japan_china_1936'
EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def with_visited_configuration():
    env=ship_fixture().raw
    doc=json.loads(env.serialize());next(iter(doc['state']['units'].values()))['type']='battlecruiser'
    env.restore(json.dumps(doc))
    action=next(a for a in env.legal_actions() if a.kind=='naval_designate_raider')
    env.apply_action(action)
    assert json.loads(env.serialize())['state']['action_interface']['visited_configurations']
    return env


@unittest.skipUnless(EXACT_MPS,'Lossless Apple GPU runtime unavailable')
class ResidentTrainingResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(2)

    def setup_batch(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),'mps')
        return DeviceStateBatch.capture(envs,context=context),ResidentTrainingReset(context)

    def test_exact_native_reset_preserves_every_other_field_and_random_bit(self):
        env=with_visited_configuration();envs=[env,env.clone()]
        before=[e.serialize() for e in envs];state,reset=self.setup_batch(envs)
        expected=gwrl_cpp.campaign_training_reset_probe(envs)
        with patch.object(torch.Tensor,'cpu',side_effect=AssertionError('host read')), \
             patch.object(torch.Tensor,'tolist',side_effect=AssertionError('host list')), \
             patch.object(torch.Tensor,'item',side_effect=AssertionError('host scalar')):
            result=reset.reset(state)
        self.assertEqual(result.errors.cpu().tolist(),[0,0])
        for original,actual,wanted in zip(before,result.state.restore_envs(),expected,strict=True):
            doc=json.loads(actual.serialize());self.assertEqual(doc['state'],json.loads(wanted))
            self.assertEqual(doc['random'],json.loads(original)['random'])
        self.assertEqual([e.serialize() for e in envs],before)
        self.assertEqual(result.state.records.shape,state.records.shape)
        second=reset.reset(result.state)
        self.assertEqual(second.state.records.shape,state.records.shape)
        self.assertEqual(second.state.restore_envs()[0].serialize(),result.state.restore_envs()[0].serialize())

    def test_empty_metadata_capacity_retry_and_selected_cohort_rollback(self):
        env=with_visited_configuration();doc=json.loads(env.serialize());doc['state']['action_interface']={}
        env.restore(json.dumps(doc));state,reset=self.setup_batch([env,env.clone()])
        small=reset.reset(state)
        self.assertFalse(small.committed.item())
        self.assertEqual(small.state.restore_envs()[0].serialize(),env.serialize())
        retry=reset.reset(state,capacity=state.records.shape[1]+6)
        self.assertTrue(retry.committed.item())
        self.assertEqual(json.loads(retry.state.restore_envs()[0].serialize())['state'],
                         json.loads(gwrl_cpp.campaign_training_reset_probe([env])[0]))
        errors=state.errors.clone();errors[1]=1
        failed=reset.reset(replace(state,errors=errors),capacity=state.records.shape[1]+6)
        self.assertFalse(failed.committed.item())
        selected=torch.tensor([True,False],dtype=torch.bool,device='mps')
        result=reset.reset(replace(state,errors=errors),selected,capacity=state.records.shape[1]+6)
        self.assertTrue(result.committed.item())
        self.assertEqual(result.accepted.cpu().tolist(),[True,False])

    def test_profile_context_and_layout_are_explicit(self):
        env=with_visited_configuration();state,reset=self.setup_batch([env])
        plain=gwrl_cpp.CampaignEnv(str(SCENARIO),3,training_actions=False)
        context=DeviceStateContext(gwrl_cpp.device_state_context(plain),'mps')
        with self.assertRaisesRegex(ValueError,'rules profile'):ResidentTrainingReset(context)
        with self.assertRaisesRegex(ValueError,'exact resident'):
            reset.reset(DeviceStateBatch.capture([plain],context=context))
        with self.assertRaises(ValueError):reset.reset(state,torch.ones(1,device='mps'))
        empty=state.fork(torch.empty(0,dtype=torch.int64,device='mps'))
        result=reset.reset(empty)
        self.assertEqual(result.state.lane_count,0)
        self.assertTrue(result.committed.item())
