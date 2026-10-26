"""Complete mayDeclareWar(LandAttack) native parity and resident reuse."""
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
from studies.campaign.backends.resident_declarations import ResidentLandAttackDeclarations

SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"
TURN_ORDER=json.loads((SCENARIO/"manifest.json").read_text())["campaign"]["national_turn_order"]


def changed(env,mutate):
    document=json.loads(env.serialize());mutate(document["state"])
    out=env.clone();out.restore(json.dumps(document));return out


def set_turn(state,nation):
    index=TURN_ORDER.index(nation);state["clock"].update(nation_index=index,player_turn_serial=str(index))
    state["completed_turns"]={name:int(i<index) for i,name in enumerate(TURN_ORDER)}


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class ResidentDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(2)

    def setup_batch(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        state=DeviceStateBatch.capture(envs,context=context)
        native=gwrl_cpp.campaign_relations_context(envs[0]);relations=ResidentPoliticalRelations(context,native)
        return state,relations,ResidentLandAttackDeclarations(relations),native

    def assert_native(self,envs):
        state,relations,kernel,native=self.setup_batch(envs);before=[env.serialize() for env in envs]
        oracle=gwrl_cpp.campaign_relations_oracle(native,envs);shared=relations.compute(state)
        result=kernel.compute(state,shared)
        np.testing.assert_array_equal(result.allowed.cpu().numpy(),oracle.land_attack_array())
        np.testing.assert_array_equal(result.errors.cpu().numpy(),oracle.land_attack_error_array())
        self.assertIs(result.source,state);self.assertIs(result.relations,shared)
        self.assertEqual([env.serialize() for env in envs],before)
        return state,relations,kernel,result

    def test_all_phases_and_unknown_self_early_denials(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),4)
        envs=[changed(first,lambda s,p=p:s["clock"].update(phase=p)) for p in
              ("production","combat_movement","combat","non_combat_movement","place_units")]
        _,relations,_,result=self.assert_native(envs)
        self.assertFalse(result.allowed[[0,2,3,4]].any().item())
        d=relations.nation_ids.index("dadao")
        self.assertFalse(result.allowed[:,:,d].any().item())
        self.assertTrue(torch.all(result.errors==0).item())

    def test_existing_war_shared_alliance_inactive_and_truce_denials(self):
        first=changed(gwrl_cpp.CampaignEnv(str(SCENARIO),1),lambda s:s["clock"].update(phase="combat_movement"))
        def active(s):
            s["politics"]["chinese_truce"]=False;s["nations"]["ccp"].update(power_status="major",at_war_with=[])
            s["nations"]["japan"].update(alliance="different")
        allowed=changed(first,active)
        war=changed(allowed,lambda s:s["nations"]["ccp"]["at_war_with"].append("japan"))
        ally=changed(allowed,lambda s:s["nations"]["japan"].update(alliance=s["nations"]["ccp"]["alliance"]))
        surrender=changed(allowed,lambda s:s["politics"]["surrendered"].append("japan"))
        incorporate=changed(allowed,lambda s:s["nations"]["japan"]["game_flags"].update(incorporated=-1))
        truce=changed(allowed,lambda s:s["politics"].update(chinese_truce=True))
        _,relations,_,result=self.assert_native([allowed,war,ally,surrender,incorporate,truce]);a,b=map(relations.nation_ids.index,("ccp","japan"))
        self.assertEqual(result.allowed[:5,a,b].cpu().tolist(),[1,0,0,0,0])

    def test_chinese_minor_target_presence_from_land_or_land_units_not_sea_units(self):
        first=changed(gwrl_cpp.CampaignEnv(str(SCENARIO),1),lambda s:s["clock"].update(phase="combat_movement"))
        native=gwrl_cpp.campaign_relations_context(first)
        home=next(name for name,yes in zip(native.territories,native.chinese_home_array(),strict=True) if yes)
        sea=next(name for name in native.territories if name not in json.loads(first.serialize())["state"]["territories"])
        exemplar=copy.deepcopy(next(u for u in json.loads(first.serialize())["state"]["units"].values() if u["type"]=="infantry"))
        def clear(s):
            s["nations"]["ccp"].update(power_status="minor",at_war_with=[])
            s["units"]={k:u for k,u in s["units"].items() if u["owner"]!="japan"}
            for territory in s["territories"].values():
                if territory["possessor"]=="japan":territory["possessor"]=None
        absent=changed(first,clear)
        land=changed(absent,lambda s:s["territories"][home].update(possessor="japan"))
        def unit_at(s,zone):
            unit=copy.deepcopy(exemplar);unit.update(id="presence",owner="japan",zone=zone,turn_origin=zone,carried_by=None,cargo=[],route=[])
            s["units"]["presence"]=unit
        land_unit=changed(absent,lambda s:unit_at(s,home));sea_unit=changed(absent,lambda s:unit_at(s,sea))
        _,relations,_,result=self.assert_native([absent,land,land_unit,sea_unit]);a,b=map(relations.nation_ids.index,("ccp","japan"))
        self.assertEqual(result.allowed[:,a,b].cpu().tolist(),[0,1,1,0])

    def test_kmt_warlord_mongolia_gate_uses_all_ccp_units_and_ignores_major_status(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        def active(s):set_turn(s,"kmt");s["clock"]["phase"]="combat_movement";s["politics"]["chinese_truce"]=False
        alive=changed(first,active)
        eliminated=changed(alive,lambda s:s.update(units={k:u for k,u in s["units"].items() if u["owner"]!="ccp"}))
        major=changed(alive,lambda s:s["nations"]["kmt"].update(power_status="major"))
        _,relations,_,result=self.assert_native([alive,eliminated,major]);a=relations.nation_ids.index("kmt")
        targets=[relations.nation_ids.index("mongolia"),next(i for i,n in enumerate(relations.nation_ids) if n.startswith("warlord_"))]
        for b in targets:self.assertEqual(result.allowed[:,a,b].cpu().tolist(),[0,1,0])

    def test_direct_control_allows_actor_but_post_surrender_axis_flag_does_not(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        def active(s):
            set_turn(s,"japan");s["clock"]["phase"]="combat_movement";s["politics"]["chinese_truce"]=False
            nation=copy.deepcopy(s["nations"]["mongolia"])
            nation.update(controller_nation="japan",player="axis",alliance="axis",at_war_with=[],allies=[])
            nation["game_flags"]={};s["nations"]["dadao"]=nation
        controlled=changed(first,active)
        direct=changed(controlled,lambda s:(s["nations"]["dadao"].update(controller_nation=None),
                                           s["nations"]["dadao"]["game_flags"].update(direct_axis_control_after_japan_surrender=1)))
        _,relations,_,result=self.assert_native([controlled,direct]);a,b=map(relations.nation_ids.index,("dadao","kmt"))
        self.assertEqual(result.allowed[:,a,b].cpu().tolist(),[1,0])

    def test_no_host_reads_source_errors_and_stale_relation_rejection(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),1);state,relations,kernel,_=self.setup_batch([env])
        shared=relations.compute(state);kernel.compute(state,shared);torch.mps.synchronize()
        fail=AssertionError("Host read/recapture forbidden")
        with patch.object(torch.Tensor,"cpu",side_effect=fail),patch.object(torch.Tensor,"item",side_effect=fail),\
             patch.object(torch.Tensor,"tolist",side_effect=fail),patch.object(gwrl_cpp,"capture_device_states",side_effect=fail):
            result=kernel.compute(state,shared)
        self.assertIs(result.relations,shared)
        other=state.snapshot()
        with self.assertRaises(ValueError):kernel.compute(other,shared)
        invalid=replace(state,errors=torch.ones_like(state.errors));rejected=kernel.compute(invalid)
        self.assertTrue(torch.all(rejected.errors==3).item())

    def test_empty_batch_and_foreign_context(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),1);state,_,kernel,_=self.setup_batch([env])
        empty=DeviceStateBatch.capture([],context=state.context);result=kernel.compute(empty)
        self.assertEqual(result.allowed.shape,(0,len(kernel.relations_context.nation_ids),len(kernel.relations_context.nation_ids)))
        foreign=copy.copy(state.context);foreign.wire_context_fingerprint+="-different"
        with self.assertRaises(ValueError):kernel.compute(replace(state,context=foreign))


if __name__=="__main__":unittest.main()
