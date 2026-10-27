"""Native set/closure semantics, exact untouched fields and resident rollback."""
from dataclasses import replace
import copy
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext,SECTION_NAMES
from studies.campaign.backends.device_state_edits import replace_subtrees
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_political_unit_removal import ResidentPoliticalUnitRemoval
from studies.campaign.backends.resident_state_json import ResidentStateJson
from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
from tests.test_campaign_device_state import rich_fixture

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def removal_fixture(depth=3):
    env=rich_fixture();doc=json.loads(env.serialize());state=doc["state"]
    template=copy.deepcopy(next(iter(state["units"].values())))
    names=["zz_cargo_root",*[f"cargo_{n:03d}" for n in reversed(range(depth))]]
    for i,name in enumerate(names):
        unit=copy.deepcopy(template);unit.update(id=name,type="infantry",owner=("japan","ccp","kmt","mongolia")[i%4],
            zone="land_jap_tokyo",turn_origin="land_jap_tokyo",route=["land_jap_tokyo"],damage=0,
            movement_allowance=2,movement_remaining=1,carried_by=None if not i else names[i-1],
            cargo=names[i+1:i+2],turn_flags={"untouched_negative":-3},game_flags={"untouched":17})
        state["units"][name]=unit
    survivor=next(name for name in state["units"] if name not in names)
    for job,target,owner in (("repair_root",names[0],"ccp"),("repair_leaf",names[-1],"kmt"),
                             ("repair_survivor",survivor,"japan"),("repair_city_seed","land_jap_tokyo","mongolia")):
        state["repairs"][job]={"id":job,"owner":owner,"target":target,"remaining_damage":1,"remaining_cost":2,"restricts_action":True,"endpoint":None}
    state["repairs"]["repair_rail_seed"]={"id":"repair_rail_seed","owner":"japan","target":"device_rail", "remaining_damage":1,
        "remaining_cost":2,"restricts_action":False,"endpoint":"land_china_shensi"}
    # A different entity with the same spelling is deliberately retained.
    state["construction"][names[0]]={"id":names[0],"owner":"japan","type":"infantry","site":"land_jap_tokyo",
        "queue_position":2,"paid_ipp":7,"remaining_payments":[1],"flags":{"opaque":-3}}
    battle={"id":"removal_battle","zone":"land_jap_tokyo","attacker":"japan","defender":"kmt","stage":"fixture",
        "attackers":[names[0],survivor],"defenders":[names[-1]] if depth else [],"pending_hits":{names[0]:2},
        "flags":{"unknown":-3},"data":{"unit_snapshots":names,"negative_zero":-0.0,"opaque":[None,True,1.0000000000000002]}}
    state["battles"][battle["id"]]=battle;state["battle_order"].append(battle["id"])
    state["nations"]["ccp"]["game_flags"]["civil_war_eliminated"]=0
    env.restore(json.dumps(doc,ensure_ascii=False));return env,names


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU execution unavailable")
class ResidentPoliticalRemovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        native=gwrl_cpp.capture_device_states(context.native,envs);state=DeviceStateBatch.from_native(native,context=context)
        return state,ResidentPoliticalUnitRemoval(context),ResidentStateJson(CanonicalJsonContext(native,context))

    def tokens(self,state):
        used,size=state.suffix_usage.cpu().tolist();values=[]
        for data,offsets in ((state.context.string_bytes,state.context.string_offsets),(state.string_bytes[:size],state.string_offsets[:used+1])):
            raw=bytes(data.cpu().tolist());positions=offsets.cpu().tolist();values.extend(raw[a:b] for a,b in zip(positions,positions[1:]))
        result={text:index for index,text in enumerate(values)}
        self.assertEqual(len(result),len(values),"Noncanonical duplicate string identities")
        return result

    def requests(self,state,names,capacity=None):
        R=max(map(len,names),default=0) if capacity is None else capacity;tokens=self.tokens(state)
        ids=torch.full((state.lane_count,R),-999,dtype=torch.int64,device="mps")
        for lane,items in enumerate(names):
            for col,text in enumerate(items[:R]):ids[lane,col]=tokens[text.encode()]
        return ids,torch.tensor([len(items) for items in names],dtype=torch.int64,device="mps")

    def assert_native(self,before,result,envs,names,formatter,*,selected=None,links=None,valid_output=True):
        enabled=[True]*len(envs) if selected is None else selected
        oracle=(gwrl_cpp.campaign_remove_political_units_oracle(before.context.native,envs,names,enabled) if links is None else
            gwrl_cpp._campaign_remove_political_units_test_oracle(before.context.native,envs,names,enabled,links))
        self.assertEqual(result.errors.cpu().tolist(),[item["error"] for item in oracle]);self.assertTrue(result.committed.cpu().item())
        encoded=formatter.serialize(result.state,byte_capacity=524288);self.assertEqual(encoded.errors.cpu().tolist(),[0]*len(envs))
        actual=[json.loads(bytes(row[:length])) for row,length in zip(encoded.data.cpu().tolist(),encoded.lengths.cpu().tolist(),strict=True)]
        self.assertEqual(actual,[json.loads(item["planning_json"]) for item in oracle])
        if valid_output:
            got=result.state.restore_envs()
            self.assertEqual([json.loads(env.serialize())["state"] for env in got],[json.loads(item["state_json"]) for item in oracle])
            self.assertEqual([json.loads(env.serialize())["random"] for env in got],[json.loads(env.serialize())["random"] for env in envs])
        # Compare direct native helper captures, including invalid helper-only
        # cycles. A JSON roundtrip would turn native '-0' into Python int0.
        # String pool IDs alone are normalized by EXACT raw bytes; every other
        # record word, section and RNG field remains a strict integer comparison.
        actual_tokens=self.tokens(result.state);actual_rows=result.state.records.cpu().numpy();lengths=result.state.lengths.cpu().tolist()
        for lane,item in enumerate(oracle):
            packed=item["packed_state"];expected=np.array(packed.record_array(),copy=True);strings=[]
            for data,offsets in ((packed.context.string_bytes(),packed.context.string_offsets()),(packed.string_bytes(),packed.string_offsets())):
                raw=bytes(np.asarray(data));positions=np.asarray(offsets).tolist()
                strings.extend(raw[a:b] for a,b in zip(positions,positions[1:]))
            self.assertEqual(len(set(strings)),len(strings))
            for row in expected:
                if row[0]==5:row[1]=actual_tokens[strings[row[1]]]
            self.assertTrue(np.any((expected[:,0]==4)&(expected[:,2]==0)&(expected[:,3]==0x80000000)),"Lost negative-zero sentinel")
            self.assertTrue(np.any((expected[:,0]==4)&(expected[:,2]==1)&(expected[:,3]==0x3ff00000)),"Lost noninteger sentinel")
            np.testing.assert_array_equal(actual_rows[lane,:lengths[lane]],expected)
            np.testing.assert_array_equal(result.state.sections[lane].cpu().numpy(),np.asarray(packed.section_array())[0])
        old,new=before.records.cpu(),result.state.records.cpu();a,b=before.sections.cpu(),result.state.sections.cpu()
        for column,name in enumerate(SECTION_NAMES):
            if name in {"state","state.units","state.repairs","state.battles"}:continue
            for lane in range(before.lane_count):
                x,y=int(a[lane,column]),int(b[lane,column]);left,right=old[lane,x:int(old[lane,x,4])].clone(),new[lane,y:int(new[lane,y,4])].clone()
                left[:,4]-=x;right[:,4]-=y;self.assertTrue(torch.equal(left,right),name)
        self.assertIs(result.state.string_bytes,before.string_bytes);self.assertIs(result.state.suffix_usage,before.suffix_usage)
        return actual

    def assert_rollback(self,state,result):
        self.assertFalse(result.committed.cpu().item());self.assertEqual(result.accepted.cpu().tolist(),[False]*state.lane_count)
        self.assertTrue(torch.equal(result.state.records,state.records));self.assertTrue(torch.equal(result.state.sections,state.sections))
        self.assertTrue(torch.equal(result.state.suffix_usage,state.suffix_usage))

    def test_carrier_seed_removes_every_owner_descendant_and_only_native_references(self):
        env,chain=removal_fixture();before,service,formatter=self.setup([env]);ids,counts=self.requests(before,[[chain[0]]])
        original=env.serialize();result=service.remove(before,ids,counts,unit_capacity=512)
        actual=self.assert_native(before,result,[env],[[chain[0]]],formatter)[0]
        self.assertEqual(env.serialize(),original);self.assertEqual(result.removed_counts.cpu().tolist(),[len(chain)])
        self.assertTrue(all(name not in actual["units"] for name in chain))
        self.assertNotIn("repair_root",actual["repairs"]);self.assertNotIn("repair_leaf",actual["repairs"])
        self.assertIn("repair_survivor",actual["repairs"]);self.assertIn(chain[0],actual["construction"])
        old=json.loads(original)["state"]
        self.assertEqual(actual["battles"]["removal_battle"]["pending_hits"],old["battles"]["removal_battle"]["pending_hits"])
        self.assertEqual(actual["battles"]["removal_battle"]["data"],old["battles"]["removal_battle"]["data"])

    def test_child_seed_keeps_parent_but_filters_its_cargo_and_both_battle_sides(self):
        env,chain=removal_fixture(4);before,service,formatter=self.setup([env]);wanted=[[chain[1]]];ids,counts=self.requests(before,wanted)
        actual=self.assert_native(before,service.remove(before,ids,counts,unit_capacity=512),[env],wanted,formatter)[0]
        self.assertIn(chain[0],actual["units"]);self.assertEqual(actual["units"][chain[0]]["cargo"],[])
        self.assertTrue(all(name not in actual["units"] for name in chain[1:]));self.assertEqual(actual["battles"]["removal_battle"]["defenders"],[])
        self.assertIn(chain[0],actual["battles"]["removal_battle"]["attackers"])

    def test_missing_nonunit_seed_ids_still_cancel_repairs_without_deleting_assets(self):
        env,chain=removal_fixture();before,service,formatter=self.setup([env]);wanted=[["land_jap_tokyo","device_rail","beneficiary"]]
        ids,counts=self.requests(before,wanted);result=service.remove(before,ids,counts,unit_capacity=512)
        actual=self.assert_native(before,result,[env],wanted,formatter)[0];old=json.loads(env.serialize())["state"]
        self.assertEqual(actual["units"],old["units"]);self.assertNotIn("repair_city_seed",actual["repairs"]);self.assertNotIn("repair_rail_seed",actual["repairs"])
        self.assertEqual(actual["territories"],old["territories"]);self.assertEqual(actual["rails"],old["rails"]);self.assertEqual(result.removed_counts.cpu().tolist(),[0])

    def test_duplicate_seeds_and_reverse_lexical_chain_deeper_than_128_are_complete(self):
        env,chain=removal_fixture(130);before,service,formatter=self.setup([env]);wanted=[[chain[0],chain[0],"beneficiary"]]
        ids,counts=self.requests(before,wanted);result=service.remove(before,ids,counts,unit_capacity=512)
        self.assert_native(before,result,[env],wanted,formatter);self.assertEqual(result.removed_counts.cpu().tolist(),[131])

    def temporary_links(self,state,overrides,lane=0):
        tokens=self.tokens(state);capacity=state.records.shape[1]+sum((parent is not None)+len(cargo) for parent,cargo in overrides.values())
        for name,(parent,cargo) in overrides.items():
            for field,values in ((9,cargo),(8,[] if parent is None else [parent])):
                rows=state.records[lane].cpu().tolist();cursor=state.section("state.units")[lane].cpu().item()+1
                while rows[cursor][1]!=tokens[name.encode()]:cursor=rows[cursor+1][4]
                unit=cursor+1;root=unit+1
                for _ in range(field):root=rows[root][4]
                block=[[9 if field==8 else 6,len(values),0,0,len(values)+1]]+[[5,tokens[value.encode()],0,0,i+2] for i,value in enumerate(values)]
                roots=torch.full((state.lane_count,),-1,dtype=torch.int64,device="mps");roots[lane]=root
                blocks=torch.zeros((state.lane_count,len(block),5),dtype=torch.int64,device="mps");blocks[lane]=torch.tensor(block,device="mps")
                lengths=torch.zeros(state.lane_count,dtype=torch.int64,device="mps");lengths[lane]=len(block)
                selected=torch.zeros(state.lane_count,dtype=torch.bool,device="mps");selected[lane]=True
                state=replace_subtrees(state,roots,blocks,lengths,selected,capacity=capacity).state
        return state

    def test_seeded_cycles_close_and_unconnected_cycles_are_not_silently_repaired(self):
        env,chain=removal_fixture(1);links={chain[0]:(chain[1],[chain[1]]),chain[1]:(chain[0],[chain[0]])}
        original,service,formatter=self.setup([env]);state=self.temporary_links(original,links)
        for seed,valid in ((chain[0],True),("beneficiary",False)):
            with self.subTest(seed=seed):
                wanted=[[seed]];ids,counts=self.requests(state,wanted);result=service.remove(state,ids,counts,unit_capacity=512)
                self.assert_native(state,result,[env],wanted,formatter,links=[links],valid_output=valid)
                self.assertEqual(result.removed_counts.cpu().tolist(),[2 if valid else 0])

    def test_selected_laziness_and_whole_cohort_rollback_on_invalid_requests(self):
        env,chain=removal_fixture();before,service,formatter=self.setup([env,env.clone()]);wanted=[[chain[0]],[chain[0]]]
        ids,counts=self.requests(before,wanted);bad=ids.clone();bad[1,0]=-999;badcounts=counts.clone();badcounts[1]=-1
        selected=torch.tensor([True,False],device="mps")
        result=service.remove(before,bad,badcounts,selected,unit_capacity=512)
        self.assert_native(before,result,[env,env],wanted,formatter,selected=[True,False])
        failed=service.remove(before,bad,badcounts,unit_capacity=512)
        self.assertEqual(failed.errors.cpu().tolist(),[0,3]);self.assert_rollback(before,failed)

    def test_request_index_and_block_capacities_report_sizes_and_retry(self):
        env,chain=removal_fixture();before,service,formatter=self.setup([env]);wanted=[[chain[0],chain[1]]]
        ids,counts=self.requests(before,wanted,capacity=1)
        failed=service.remove(before,ids,counts,unit_capacity=512);self.assertEqual(failed.errors.cpu().tolist(),[5])
        self.assertEqual(failed.required_request_capacity.cpu().tolist(),[2]);self.assert_rollback(before,failed)
        ids,counts=self.requests(before,wanted)
        n=len(json.loads(env.serialize())["state"]["units"])
        failed=service.remove(before,ids,counts,unit_capacity=n-1);self.assertEqual(failed.errors.cpu().tolist(),[5])
        self.assertEqual(failed.required_unit_capacity.cpu().tolist(),[n]);self.assert_rollback(before,failed)
        failed=service.remove(before,ids,counts,unit_capacity=n,block_capacity=1)
        self.assertEqual(failed.errors.cpu().tolist(),[5]);self.assert_rollback(before,failed)
        result=service.remove(before,ids,counts,unit_capacity=n,block_capacity=failed.required_block_capacity[0].cpu().item())
        self.assert_native(before,result,[env],wanted,formatter);self.assertEqual(result.state.records.shape,before.records.shape)

    def test_empty_and_irrelevant_sets_are_noops_and_padded_ids_are_ignored(self):
        env,chain=removal_fixture();before,service,formatter=self.setup([env]);ids,counts=self.requests(before,[[]])
        result=service.remove(before,ids,counts,unit_capacity=0,block_capacity=1)
        self.assert_native(before,result,[env],[[]],formatter);self.assertEqual(result.required_unit_capacity.cpu().tolist(),[0])
        wanted=[["beneficiary"]];ids,counts=self.requests(before,wanted,capacity=4)
        result=service.remove(before,ids,counts,unit_capacity=512,block_capacity=1)
        self.assert_native(before,result,[env],wanted,formatter);self.assertEqual(result.removed_counts.cpu().tolist(),[0])

    def test_remove_all_units_preserves_empty_battles_snapshots_and_stale_political_flags(self):
        env,chain=removal_fixture();old=json.loads(env.serialize())["state"];before,service,formatter=self.setup([env]);wanted=[list(old["units"])]
        ids,counts=self.requests(before,wanted);result=service.remove(before,ids,counts,unit_capacity=len(wanted[0]))
        actual=self.assert_native(before,result,[env],wanted,formatter)[0]
        self.assertEqual(actual["units"],{});self.assertEqual(actual["battle_order"],old["battle_order"])
        self.assertTrue(all(not battle["attackers"] and not battle["defenders"] for battle in actual["battles"].values()))
        self.assertEqual(actual["turn_start"],old["turn_start"]);self.assertEqual(actual["nations"]["ccp"]["game_flags"]["civil_war_eliminated"],0)

    def test_no_hot_host_native_json_or_catalog_and_complete_layout_checks_empty_batch(self):
        env,chain=removal_fixture();before,service,formatter=self.setup([env]);wanted=[[chain[0]]];ids,counts=self.requests(before,wanted)
        service.remove(before,ids,counts,unit_capacity=512)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host values")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(json,"loads",side_effect=AssertionError("JSON hot path")), \
             patch.object(gwrl_cpp,"campaign_remove_political_units_oracle",side_effect=AssertionError("CPU fallback")), \
             patch.object(gwrl_cpp,"campaign_catalog_stats_oracle",side_effect=AssertionError("Catalog call")), \
             patch.object(gwrl_cpp,"capture_device_states",side_effect=AssertionError("Native transfer")):
            result=service.remove(before,ids,counts,unit_capacity=512)
        self.assert_native(before,result,[env],wanted,formatter)
        with self.assertRaises(ValueError):service.remove(before,ids.cpu(),counts,unit_capacity=512)
        with self.assertRaises(ValueError):service.remove(DeviceStateBatch.capture([env],device="mps"),ids,counts,unit_capacity=512)
        with self.assertRaises(OverflowError):service.remove(before,ids,counts,unit_capacity=2**63)
        empty=DeviceStateBatch.capture([],context=before.context)
        result=service.remove(empty,torch.zeros((0,0),dtype=torch.int64,device="mps"),torch.zeros(0,dtype=torch.int64,device="mps"),unit_capacity=0)
        self.assertTrue(result.committed.cpu().item());self.assertEqual(result.state.restore_envs(),[])


if __name__=="__main__":unittest.main()
