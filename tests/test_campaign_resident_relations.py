"""Original native political predicates versus source-bound resident matrices."""
from dataclasses import replace
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.metal_validation import mps_int64_indexing_supported

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.resident_relations import ResidentPoliticalRelations

SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"
TURN_ORDER=json.loads((SCENARIO/"manifest.json").read_text())["campaign"]["national_turn_order"]


def changed(env,mutate):
    document=json.loads(env.serialize());mutate(document["state"])
    out=env.clone();out.restore(json.dumps(document));return out


def set_turn(state,nation):
    index=TURN_ORDER.index(nation);state["clock"]["nation_index"]=index
    state["clock"]["player_turn_serial"]=str(index)
    state["completed_turns"]={name:int(i<index) for i,name in enumerate(TURN_ORDER)}


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class ResidentRelationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(2)

    def setup_batch(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        state=DeviceStateBatch.capture(envs,context=context)
        native=gwrl_cpp.campaign_relations_context(envs[0])
        return state,ResidentPoliticalRelations(context,native),native

    def assert_native(self,envs):
        state,kernel,native=self.setup_batch(envs);before=[env.serialize() for env in envs]
        oracle=gwrl_cpp.campaign_relations_oracle(native,envs);result=kernel.compute(state)
        self.assertIs(result.source,state)
        for actual,expected in ((result.pairs,oracle.pair_array()),(result.pair_errors,oracle.pair_error_array()),
                                (result.nations,oracle.nation_array()),(result.nation_errors,oracle.nation_error_array()),
                                (result.present,oracle.present_array())):
            np.testing.assert_array_equal(actual.cpu().numpy(),expected)
        parallel=kernel.compute(state,implementation="parallel")
        for field in ("pairs","pair_errors","nations","nation_errors","present","metadata"):
            self.assertTrue(torch.equal(getattr(result,field),getattr(parallel,field)),field)
        self.assertIs(parallel.source,state)
        self.assertEqual([env.serialize() for env in envs],before)
        return state,kernel,result

    def test_complete_setup_dormant_and_playerless_queries(self):
        _,kernel,result=self.assert_native([gwrl_cpp.CampaignEnv(str(SCENARIO),17)])
        neutral=next(i for i,name in enumerate(kernel.nation_ids) if name.startswith("warlord_"))
        self.assertEqual(result.player_errors[0,neutral].item(),2)
        # A missing dormant Dadao does not invalidate all other pairs.
        dadao=kernel.nation_ids.index("dadao")
        self.assertEqual(result.present[0,dadao].item(),0)
        self.assertEqual(result.friendly[0,dadao,dadao].item(),1)
        self.assertEqual(result.pair_errors[0,dadao,dadao,2].item(),0)

    def test_truce_precedes_hostility_and_control(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        def modify(state):
            state["politics"]["chinese_truce"]=True
            state["nations"]["ccp"]["at_war_with"]=["kmt"]
            state["nations"]["kmt"]["at_war_with"]=[]
            state["nations"]["ccp"]["controller_nation"]="kmt"
        env=changed(env,modify);_,kernel,result=self.assert_native([env])
        a,b=map(kernel.nation_ids.index,("ccp","kmt"))
        self.assertEqual(result.friendly[0,a,b].item(),1)
        self.assertEqual(result.at_war[0,a,b].item(),1)
        self.assertEqual(result.at_war[0,b,a].item(),0)

    def test_common_major_enemy_alignment_and_optional_null_alliances(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        def setup(state):
            state["politics"]["chinese_truce"]=False
            for name in ("ccp","kmt"):
                n=state["nations"][name];n.update(alliance="shared-dynamic-name",power_status="major",controller_nation=None)
                n["at_war_with"]=["japan"]
        common=changed(first,setup)
        minor=changed(common,lambda s:s["nations"]["japan"].update(power_status="minor"))
        null=changed(common,lambda s:[s["nations"][n].update(alliance=None) for n in ("ccp","kmt")])
        _,kernel,result=self.assert_native([common,minor,null]);a,b=map(kernel.nation_ids.index,("ccp","kmt"))
        self.assertEqual(result.friendly[:,a,b].cpu().tolist(),[1,0,0])
        self.assertEqual(result.same_alliance[2,a,b].item(),1)
        self.assertEqual(result.shared_alliance[2,a,b].item(),0)

    def test_direct_control_surrender_incorporation_and_movement(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        def setup(s):
            set_turn(s,"japan")
            s["nations"]["mongolia"].update(controller_nation="japan",player=None)
            neutral=next(name for name in s["nations"] if name.startswith("warlord_"))
            s["nations"][neutral].update(controller_nation="mongolia",player=None)
        direct=changed(first,setup)
        surrendered=changed(direct,lambda s:s["politics"]["surrendered"].append("mongolia"))
        incorporated=changed(direct,lambda s:s["nations"]["mongolia"]["game_flags"].update(incorporated=-(2**31)))
        _,kernel,result=self.assert_native([direct,surrendered,incorporated]);m,j=map(kernel.nation_ids.index,("mongolia","japan"))
        self.assertEqual(result.controlled[:,m,j].cpu().tolist(),[1,0,0])
        self.assertEqual(result.logistics_friendly[:,j,m].cpu().tolist(),[1,0,0])
        neutral=next(i for i,name in enumerate(kernel.nation_ids) if name.startswith("warlord_") and result.controlled[0,i,m].item())
        self.assertEqual(result.controlled[0,neutral,j].item(),0)
        self.assertEqual(result.player[0,neutral].item(),kernel.player_ids.index("axis"))

    def test_player_precedence_temporary_defense_invalid_override_and_cycle(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        neutral=next(name for name in json.loads(first.serialize())["state"]["nations"] if name.startswith("warlord_"))
        key="warlord_defense_player:"+neutral
        temporary=changed(first,lambda s:s["politics"]["pending"].update({key:"allies"}))
        explicit=changed(temporary,lambda s:s["nations"][neutral].update(player="comintern",controller_nation="japan"))
        controller=changed(temporary,lambda s:s["nations"][neutral].update(controller_nation="japan"))
        invalid=changed(first,lambda s:s["politics"]["pending"].update({key:17}))
        other=next(name for name in json.loads(first.serialize())["state"]["nations"] if name.startswith("warlord_") and name!=neutral)
        def cycle(s):
            s["nations"][neutral].update(controller_nation=other)
            s["nations"][other].update(controller_nation=neutral)
        cyclic=changed(first,cycle)
        _,kernel,result=self.assert_native([temporary,explicit,controller,invalid,cyclic]);n=kernel.nation_ids.index(neutral)
        self.assertEqual(result.player[:3,n].cpu().tolist(),[kernel.player_ids.index(x) for x in ("allies","comintern","axis")])
        self.assertEqual(result.player_errors[:,n].cpu().tolist(),[0,0,0,2,2])

    def test_rail_permission_uses_raw_players_and_signed_owner_flag(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        def setup(s):
            s["politics"]["chinese_truce"]=True
            s["nations"]["ccp"]["player"]=None;s["nations"]["kmt"]["player"]=None
        absent=changed(first,setup)
        unequal=changed(absent,lambda s:s["nations"]["ccp"].update(player="comintern"))
        granted=changed(unequal,lambda s:s["nations"]["kmt"]["turn_flags"].update({"rail_permission:ccp":-1}))
        _,kernel,result=self.assert_native([absent,unequal,granted]);a,b=map(kernel.nation_ids.index,("ccp","kmt"))
        self.assertEqual(result.rail_permission[:,a,b].cpu().tolist(),[1,0,1])

    def test_dadao_axis_exception_is_separate_from_control(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        def setup(s):
            set_turn(s,"japan")
            nation=copy.deepcopy(s["nations"]["mongolia"])
            nation.update(controller_nation=None,player="axis",alliance="axis",at_war_with=[],allies=[])
            nation["game_flags"]={"direct_axis_control_after_japan_surrender":-1}
            s["nations"]["dadao"]=nation
        direct=changed(first,setup)
        _,kernel,result=self.assert_native([direct]);d,j=map(kernel.nation_ids.index,("dadao","japan"))
        self.assertEqual(result.controlled[0,d,j].item(),0)
        self.assertEqual(result.movement_controller[0,d].item(),1)

    def test_no_host_reads_or_recapture_and_reuse_only_matching_source(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),4);state,kernel,_=self.setup_batch([env])
        # Compile/warm outside the no-host-read witness.
        kernel.compute(state);torch.mps.synchronize()
        fail=AssertionError("Host state/read forbidden in resident political permissions")
        with patch.object(torch.Tensor,"cpu",side_effect=fail),patch.object(torch.Tensor,"item",side_effect=fail),\
             patch.object(torch.Tensor,"tolist",side_effect=fail),patch.object(gwrl_cpp,"capture_device_states",side_effect=fail):
            result=kernel.compute(state)
        self.assertIs(result.source,state)
        invalid=replace(state,errors=torch.ones_like(state.errors));rejected=kernel.compute(invalid)
        self.assertTrue(torch.all(rejected.pair_errors==3).item())
        self.assertTrue(torch.all(rejected.nation_errors==3).item())

    def test_empty_foreign_context_and_noncontiguous_rejected(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),4);state,kernel,_=self.setup_batch([env])
        empty=DeviceStateBatch.capture([],context=state.context);result=kernel.compute(empty)
        self.assertEqual(result.pairs.shape,(0,len(kernel.nation_ids),len(kernel.nation_ids),7))
        foreign=copy.copy(state.context);foreign.wire_context_fingerprint+="-different"
        with self.assertRaises(ValueError):kernel.compute(replace(state,context=foreign))
        # Same logical shape with a strided final axis must never hide a copy.
        padded=torch.empty((*state.records.shape[:2],10),dtype=torch.int64,device="mps")
        padded[:,:,::2]=state.records
        with self.assertRaises(ValueError):kernel.compute(replace(state,records=padded[:,:,::2]))

    def test_parallel_threadgroups_stride_over_all_factions_and_pairs(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),4);state,kernel,_=self.setup_batch([env,env.clone(),env.clone(),env.clone()])
        reference=kernel.compute(state)
        # 7 threads intentionally underfills the faction axis: all loops must
        # stride to completion, including every one of N squared pairs.
        for size in (1,7,32,64,128):
            result=kernel.compute(state,implementation="parallel",group_size=size)
            for field in ("pairs","pair_errors","nations","nation_errors","present","metadata"):
                self.assertTrue(torch.equal(getattr(reference,field),getattr(result,field)),(size,field))
        for kwargs in ({"implementation":"unknown"},{"group_size":32},{"implementation":"parallel","group_size":0},
                       {"implementation":"parallel","group_size":True}):
            with self.assertRaises(ValueError):kernel.compute(state,**kwargs)

    def test_parallel_invalid_diagnostics_match_full_serial_fallback(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),4);state,kernel,_=self.setup_batch([env])
        rows=state.records[0].cpu().tolist();root=state.section('state.nations').item();cursor=root+1
        target=int(state.context.prefix_lookup_ids(('mongolia',))[0]);nation=-1
        for _ in range(rows[root][1]):
            value=rows[cursor][4]
            if rows[cursor][1]==target:nation=value;break
            cursor=rows[value][4]
        self.assertGreaterEqual(nation,0)
        records=state.records.clone();records[0,nation,1]=13
        cases=[replace(state,records=records),replace(state,errors=torch.ones_like(state.errors))]
        for invalid in cases:
            reference=kernel.compute(invalid);parallel=kernel.compute(invalid,implementation='parallel',group_size=7)
            for field in ('pairs','pair_errors','nations','nation_errors','present','metadata'):
                self.assertTrue(torch.equal(getattr(reference,field),getattr(parallel,field)),field)

    def test_parallel_has_no_host_state_reads(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),4);state,kernel,_=self.setup_batch([env])
        expected=kernel.compute(state,implementation='parallel');torch.mps.synchronize()
        fail=AssertionError('Host state read forbidden in parallel permissions')
        with patch.object(torch.Tensor,'cpu',side_effect=fail),patch.object(torch.Tensor,'item',side_effect=fail),\
             patch.object(torch.Tensor,'tolist',side_effect=fail),patch.object(gwrl_cpp,'capture_device_states',side_effect=fail):
            result=kernel.compute(state,implementation='parallel')
        self.assertTrue(torch.equal(expected.pairs,result.pairs))


if __name__=="__main__":unittest.main()
