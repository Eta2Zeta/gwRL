"""Byte identity, live counters, COW and rollback across complete state snapshots."""
from __future__ import annotations

import dataclasses
from contextlib import ExitStack
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.device_state import DeviceStateBatch
from studies.campaign.backends.device_strings import InternError, intern_bytes, pack_byte_requests
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported

SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"
EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def fixture(device="cpu"):
    env=gwrl_cpp.CampaignEnv(str(SCENARIO),71,training_actions=True)
    return DeviceStateBatch.capture([env],device=device),env


def run(state,values,**kwargs):
    requests,lengths=pack_byte_requests(values,device=state.device)
    kwargs.setdefault("string_capacity",state.string_offsets.numel()-1+len(values))
    kwargs.setdefault("byte_capacity",state.string_bytes.numel()+requests.numel())
    return intern_bytes(state,requests,lengths,**kwargs)


def strings(state):
    count,size=state.suffix_usage.cpu().tolist()
    offsets=state.string_offsets.cpu().tolist()[:count+1]
    values=bytes(state.string_bytes.cpu().tolist()[:size])
    return [values[a:b] for a,b in zip(offsets,offsets[1:])]


class CampaignDeviceStringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls): torch.set_num_threads(cls.old)

    def test_exact_prefix_suffix_duplicates_empty_nul_unicode_and_raw_bytes(self):
        state,env=fixture();before=env.serialize();old=strings(state)
        values=[b"search",old[0],b"new_gpu_identity\0suffix",b"new_gpu_identity\0suffix",b"", "蒙古🙂".encode(),b"\xff\x80"]
        result=run(state,values)
        self.assertTrue(result.committed.item());self.assertEqual(result.errors.tolist(),[0]*len(values))
        self.assertEqual(result.ids[0].item(),state.context.random_stream_ids[1])
        self.assertEqual(result.ids[1].item(),state.context.string_count)
        self.assertEqual(result.ids[2].item(),result.ids[3].item())
        self.assertIn(values[-1],strings(result.state))
        self.assertIn(values[2],strings(result.state))
        self.assertEqual(strings(state),old)
        self.assertEqual(result.state.restore_envs()[0].serialize(),before)
        self.assertEqual(env.serialize(),before)

    def test_capacity_error_preserves_pool_and_exact_metadata_retry(self):
        state,_=fixture();requests,lengths=pack_byte_requests([b"new_capacity_identity"])
        failed=intern_bytes(state,requests,lengths)
        self.assertFalse(failed.committed.item());self.assertEqual(failed.errors.tolist(),[int(InternError.CAPACITY)])
        self.assertTrue(torch.equal(failed.state.string_bytes,state.string_bytes))
        self.assertTrue(torch.equal(failed.state.string_offsets,state.string_offsets))
        self.assertTrue(torch.equal(failed.state.suffix_usage,state.suffix_usage))
        result=intern_bytes(state,requests,lengths,string_capacity=state.string_offsets.numel(),
            byte_capacity=state.string_bytes.numel()+requests.numel())
        self.assertTrue(result.committed.item())
        self.assertEqual(result.required_usage.tolist(),result.state.suffix_usage.tolist())
        self.assertEqual(result.ids.tolist(),[state.context.string_count+state.suffix_usage[0].item()])

    def test_explicit_utf8_constraint_is_atomic_and_core_default_preserves_arbitrary_bytes(self):
        state,_=fixture()
        values=["🙂".encode(),b"\xc0\x80",b"\xed\xa0\x80",b"\xf4\x90\x80\x80",b"\xe2\x82"]
        failed=run(state,values,validate_utf8=True)
        self.assertEqual(failed.errors.tolist(),[0,4,4,4,4]);self.assertFalse(failed.committed.item())
        self.assertEqual(failed.ids.tolist(),[-1]*len(values));self.assertTrue(torch.equal(failed.state.suffix_usage,state.suffix_usage))
        result=run(state,values)
        self.assertTrue(result.committed.item())
        self.assertEqual(result.errors.tolist(),[0]*len(values))
        self.assertTrue(set(values).issubset(set(strings(result.state))))

    def test_usage_is_not_capacity_and_native_export_trims_unused_slots(self):
        state,env=fixture();source=env.serialize()
        first=run(state,[b"new_one"],string_capacity=state.string_offsets.numel()+20,
                  byte_capacity=state.string_bytes.numel()+1024)
        used=first.state.suffix_usage.tolist()
        self.assertLess(used[0],first.state.string_offsets.numel()-1)
        self.assertLess(used[1],first.state.string_bytes.numel())
        native=first.state.to_native()
        self.assertEqual(native.string_offsets().shape[0],used[0]+1)
        self.assertEqual(native.string_bytes().shape[0],used[1])
        second=run(first.state,[b"new_two",b"new_one"])
        self.assertEqual(second.ids[1].item(),first.ids[0].item())
        self.assertEqual(second.state.restore_envs()[0].serialize(),source)
        self.assertEqual(first.state.restore_envs()[0].serialize(),source)
        self.assertEqual(first.state.fork([0,0]).suffix_usage.tolist(),used)

    def test_bad_request_lengths_and_source_usage_reject_without_truncation(self):
        state,_=fixture();requests,lengths=pack_byte_requests([b"valid",b"ignored"])
        lengths[1]=requests.shape[1]+1
        result=intern_bytes(state,requests,lengths,string_capacity=state.string_offsets.numel()+2,
            byte_capacity=state.string_bytes.numel()+requests.numel())
        self.assertEqual(result.errors.tolist(),[0,int(InternError.LENGTH)]);self.assertFalse(result.committed.item())
        bad=dataclasses.replace(state,suffix_usage=torch.tensor([state.string_offsets.numel()+2,0],dtype=torch.int64))
        result=run(bad,[b"new"])
        self.assertEqual(result.pool_error.item(),int(InternError.SOURCE))
        self.assertFalse(result.committed.item());self.assertEqual(result.errors.tolist(),[int(InternError.SOURCE)])
        with self.assertRaises(ValueError): result.state.to_native()

    def test_unselected_and_zero_request_batches_do_not_apply_strings(self):
        state,_=fixture();requests,lengths=pack_byte_requests([b"ignored"])
        lengths[0]=-1
        result=intern_bytes(state,requests,lengths,torch.tensor([False]))
        self.assertTrue(result.committed.item());self.assertEqual(result.errors.tolist(),[0]);self.assertEqual(result.ids.tolist(),[-1])
        empty=run(state,[])
        self.assertTrue(empty.committed.item());self.assertEqual(empty.ids.shape,(0,))
        self.assertTrue(torch.equal(empty.state.suffix_usage,state.suffix_usage))

    @unittest.skipUnless(EXACT_MPS,"Lossless MPS indexing unavailable")
    def test_mps_matches_cpu_all_byte_id_counters_and_no_hot_host_reads(self):
        cpu,env=fixture();mps=DeviceStateBatch.capture([env],device="mps")
        values=[b"new_1",b"new_1",b"search",b"",b"new\0\xff", "é".encode(), "é".encode()]
        expected=run(cpu,values)
        req,lengths=pack_byte_requests(values,device="mps")
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Hot host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Hot host values")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Hot host scalar")):
            actual=intern_bytes(mps,req,lengths,string_capacity=mps.string_offsets.numel()-1+len(values),
                byte_capacity=mps.string_bytes.numel()+req.numel())
        torch.mps.synchronize()
        for name in ("ids","errors","required_usage","accepted","committed","pool_error"):
            self.assertTrue(torch.equal(getattr(expected,name),getattr(actual,name).cpu()),name)
        for name in ("string_bytes","string_offsets","suffix_usage","records","lengths","sections"):
            self.assertTrue(torch.equal(getattr(expected.state,name),getattr(actual.state,name).cpu()),name)
        self.assertEqual(actual.state.restore_envs()[0].serialize(),env.serialize())

    def test_new_interned_key_is_consumed_by_resident_editor_without_host_id_read(self):
        from studies.campaign.backends.device_state_edits import replace_subtrees
        for device in (("cpu", "mps") if EXACT_MPS else ("cpu",)):
            with self.subTest(device=device):
                state,env=fixture(device)
                result=run(state,[b"gpu_generated_flag_key"],string_capacity=state.string_offsets.numel()+16,
                           byte_capacity=state.string_bytes.numel()+256)
                blocks=torch.zeros((1,3,5),dtype=torch.int64,device=state.device)
                blocks[0,0]=torch.tensor([7,1,0,0,3],dtype=torch.int64,device=state.device)
                blocks[0,1]=torch.tensor([5,0,0,0,2],dtype=torch.int64,device=state.device)
                blocks[0,1,1]=result.ids[0]
                blocks[0,2]=torch.tensor([2,0,42,0,3],dtype=torch.int64,device=state.device)
                roots=result.state.section("state.flags").contiguous()
                sizes=torch.tensor([3],dtype=torch.int64,device=state.device)
                chosen=torch.tensor([True],device=state.device)
                with ExitStack() as checks:
                    if device=="mps":
                        for name in ("cpu","tolist","item"):
                            checks.enter_context(patch.object(torch.Tensor,name,side_effect=AssertionError("Hot host read")))
                    edited=replace_subtrees(result.state,roots,blocks,sizes,chosen)
                self.assertEqual(edited.errors.cpu().tolist(),[0])
                expected=json.loads(env.serialize())
                expected["state"]["flags"]={"gpu_generated_flag_key":42}
                reference=env.clone();reference.restore(json.dumps(expected,separators=(",",":")))
                self.assertEqual(edited.state.restore_envs()[0].serialize(),reference.serialize())
                self.assertEqual(state.restore_envs()[0].serialize(),env.serialize())

    @unittest.skipUnless(EXACT_MPS,"Lossless MPS indexing unavailable")
    def test_actual_metal_rank_scan_preserves_wide_byte_offsets_without_large_allocations(self):
        from studies.campaign.backends.device_strings import _rank_probe
        values=torch.tensor([2**24-1,2,2**31,2**31-1],dtype=torch.int64)
        ranks,byte_ranks,required,errors,committed=_rank_probe(values.to("mps"))
        torch.mps.synchronize()
        self.assertEqual(ranks.cpu().tolist(),[1,2,3,4])
        self.assertTrue(torch.equal(byte_ranks.cpu(),values.cumsum(0)))
        self.assertEqual(required.cpu().tolist(),[4,sum(values.tolist())])
        self.assertEqual(errors.cpu().tolist(),[0,0,0,0]);self.assertTrue(committed.cpu().item())

    @unittest.skipUnless(EXACT_MPS,"Lossless MPS indexing unavailable")
    def test_mps_padded_usage_capacity_failure_utf8_and_multiple_cow_rounds(self):
        state,env=fixture("mps")
        requests,lengths=pack_byte_requests([b"new_capacity_identity"],device="mps")
        failed=intern_bytes(state,requests,lengths)
        self.assertFalse(failed.committed.cpu().item());self.assertEqual(failed.errors.cpu().tolist(),[8])
        first=run(state,[b"new_capacity_identity"],string_capacity=state.string_offsets.numel()+32,
                  byte_capacity=state.string_bytes.numel()+1024)
        self.assertTrue(first.committed.cpu().item())
        failed_utf8=run(first.state,[b"ok",b"\xed\xa0\x80"],validate_utf8=True)
        self.assertEqual(failed_utf8.errors.cpu().tolist(),[0,4]);self.assertFalse(failed_utf8.committed.cpu().item())
        self.assertTrue(torch.equal(failed_utf8.state.suffix_usage,first.state.suffix_usage))
        second=run(first.state,[b"new_after_padding",b"new_capacity_identity"])
        self.assertEqual(first.ids.cpu().item(),second.ids[1].cpu().item())
        self.assertEqual(second.state.restore_envs()[0].serialize(),env.serialize())
        self.assertEqual(state.restore_envs()[0].serialize(),env.serialize())


if __name__=="__main__":unittest.main()
