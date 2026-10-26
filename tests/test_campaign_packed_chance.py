"""Pending dice and raw RNG are read directly from the resident state arena."""
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from tests.test_campaign_device_state import real_states, SCENARIO
from tests.test_campaign_random_metal import request, die, streams
from studies.campaign.backends.device_state import DeviceStateBatch
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.packed_chance_metal import sample_packed_chance, NO_CHANCE, CAPACITY

EXACT_MPS = torch.backends.mps.is_available() and mps_int64_indexing_supported()


def chance_env(spec, random):
    env=gwrl_cpp.CampaignEnv(str(SCENARIO),17,training_actions=True)
    value=json.loads(env.serialize())
    value['state']['chance']=spec
    value['random']=random
    env.restore(json.dumps(value))
    return env


def inspected(result):
    rows=[]
    for lane,error in enumerate(result.errors.cpu().tolist()):
        n=int(result.dice_counts[lane].cpu())
        paths=result.faces[lane].cpu().tolist();counts=result.face_counts[lane].cpu().tolist()
        rows.append({'error':error,'faces':[path[:count] for path,count in zip(paths[:n],counts[:n])],
                     'effective':result.effective[lane,:n].cpu().tolist(),
                     'streams':[str(v & ((1<<64)-1)) for v in result.next_streams[lane].cpu().tolist()],
                     'position':str(result.next_tape_positions[lane].cpu().item())})
    return rows


@unittest.skipUnless(EXACT_MPS,'Exact Apple GPU integer indexing unavailable')
class PackedChanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def test_real_native_pending_chance_outcome_and_rng(self):
        native=real_states()[1]
        before=native.serialize()
        expected=native.clone();expected.resolve_chance()
        after=json.loads(expected.serialize())
        chance_events=[event for event in after['state']['history'] if event['kind']=='chance']
        source=DeviceStateBatch.capture([native],device='mps')
        snapshot=source.records.clone()
        # These patches make accidental CPU state decoding fail inside sampling.
        with patch.object(torch.Tensor,'cpu',side_effect=AssertionError('host read')), \
             patch.object(torch.Tensor,'tolist',side_effect=AssertionError('host list')), \
             patch.object(torch.Tensor,'item',side_effect=AssertionError('host scalar')), \
             patch.object(json,'loads',side_effect=AssertionError('JSON parse')):
            result=sample_packed_chance(source,dice_capacity=8,roll_capacity=4)
        row=inspected(result)[0]
        self.assertEqual(row['error'],0)
        self.assertEqual(row['faces'],chance_events[-1]['payload']['outcome']['faces'])
        self.assertEqual(row['streams'],[after['random'][name] for name in ('actual','search','training')])
        self.assertEqual(row['position'],after['random']['tape_position'])
        self.assertTrue(torch.equal(source.records.cpu(),snapshot.cpu()))
        self.assertEqual(native.serialize(),before)

    def test_all_streams_rerolls_tapes_and_no_chance(self):
        qs=[request([die(3),die(12,maximum=3,rerolls=[1,2])]),request([die(6,maximum=2,rerolls=[1,2]),die(12)]),request([die(20)])]
        rs=[streams(actual=(-0x9e3779b97f4a7c15)&((1<<64)-1)),
            streams(actual=(1<<64)-1,active='search',tape=[6,1,2,5,12],position=1),
            streams(training=(1<<63)+17,active='training')]
        envs=[chance_env(q,r) for q,r in zip(qs,rs)]+[real_states()[0]]
        native=gwrl_cpp.campaign_sample_chance_probe([json.dumps(q) for q in qs],[json.dumps(r) for r in rs])['rows']
        state=DeviceStateBatch.capture(envs,device='mps')
        result=sample_packed_chance(state,dice_capacity=2,roll_capacity=4)
        for got,expected in zip(inspected(result),native):
            self.assertEqual(got['error'],0)
            self.assertEqual(got['faces'],expected['faces'])
            self.assertEqual(got['effective'],expected['effective'])
            random=json.loads(expected['random'])
            self.assertEqual(got['streams'],[random[name] for name in ('actual','search','training')])
            self.assertEqual(got['position'],random['tape_position'])
        self.assertEqual(inspected(result)[-1]['error'],NO_CHANCE)

    def test_capacity_failure_retains_required_sizes_and_retry_is_exact(self):
        q=request([die(12,maximum=2,rerolls=[1,2]),die(6)])
        r=streams(tape=[1,2,12,6])
        state=DeviceStateBatch.capture([chance_env(q,r)],device='mps')
        before=state.records.cpu().clone()
        for D,R in [(0,0),(1,3),(2,1)]:
            failed=sample_packed_chance(state,dice_capacity=D,roll_capacity=R)
            self.assertEqual(failed.errors.cpu().item(),CAPACITY)
            self.assertEqual(failed.required.cpu().tolist(),[[2,3]])
            self.assertEqual(failed.next_streams.cpu().tolist(),[[0,1,2]])
            self.assertEqual(failed.next_tape_positions.cpu().tolist(),[0])
            self.assertTrue(torch.equal(state.records.cpu(),before))
        success=sample_packed_chance(state,dice_capacity=2,roll_capacity=3)
        self.assertEqual(inspected(success)[0]['faces'],[[1,2,12],[6]])

    def test_tape_failure_rolls_back_all_streams_and_partial_results(self):
        q=request([die(),die()]);r=streams(actual=(1<<64)-1,tape=[12])
        state=DeviceStateBatch.capture([chance_env(q,r)],device='mps')
        result=sample_packed_chance(state,dice_capacity=2,roll_capacity=1)
        row=inspected(result)[0]
        self.assertNotEqual(row['error'],0)
        self.assertEqual(row['streams'],[r[name] for name in ('actual','search','training')])
        self.assertEqual(row['position'],'0')
        self.assertEqual(row['effective'],[0,0])
        self.assertEqual(row['faces'],[[],[]])

    def test_empty_and_non_gpu_rejection(self):
        root=DeviceStateBatch.capture([real_states()[0]],device='mps')
        empty=root.fork([])
        result=sample_packed_chance(empty,dice_capacity=0,roll_capacity=0)
        self.assertEqual(tuple(result.faces.shape),(0,0,0))
        with self.assertRaisesRegex(ValueError,'Apple GPU'):
            sample_packed_chance(DeviceStateBatch.capture([real_states()[0]]),dice_capacity=1,roll_capacity=1)


if __name__=='__main__':unittest.main()
