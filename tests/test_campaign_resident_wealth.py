"""Native double wealth oracles versus exact packed Apple GPU components."""
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
from studies.campaign.backends.resident_wealth import PLAYERS,ResidentWealthContext,_component_sum_probe

SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"


def changed(env,mutate):
    document=json.loads(env.serialize());mutate(document["state"])
    result=env.clone();result.restore(json.dumps(document));return result


def bare(env):
    def clear(state):
        for field in ("units","facilities","rails","construction","repairs"):state[field]={}
    return changed(env,clear)


def repair(owner,target,damage,endpoint=None):
    return dict(id="paid",owner=owner,target=target,remaining_damage=damage,remaining_cost=0,
                restricts_action=False,endpoint=endpoint)


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class ResidentWealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(2)

    def setup(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        batch=DeviceStateBatch.capture(envs,context=context)
        native=gwrl_cpp.campaign_wealth_context(envs[0])
        return batch,ResidentWealthContext(context,native),native

    def assert_native(self,envs):
        batch,kernel,native=self.setup(envs);before=[env.serialize() for env in envs]
        oracle=gwrl_cpp.campaign_wealth_oracle(native,envs)
        result=kernel.evaluate(batch)
        classes=np.array([0,1,2,3,3],dtype=np.int64)
        np.testing.assert_array_equal(classes[result.errors.cpu().numpy()],oracle.error_array()[:,0])
        np.testing.assert_array_equal(classes[result.terminal_errors.cpu().numpy()],oracle.error_array()[:,1])
        good=oracle.error_array()[:,0]==0
        np.testing.assert_array_equal(result.components_twice.cpu().numpy()[good]/2,oracle.component_array()[good])
        if good.all():
            actual=kernel.inspect(result)
            values=np.asarray([[row[name]["wealth"] for name in PLAYERS] for row in actual],dtype=np.float64)
            self.assertEqual(values.tobytes(),oracle.wealth_array().tobytes())
            self.assertEqual(np.asarray(kernel.inspect(result,"gaps"),dtype=np.float64).tobytes(),oracle.gap_array().tobytes())
        self.assertEqual(np.asarray(kernel.inspect(result,"terminal"),dtype=np.float64).tobytes(),oracle.terminal_array().tobytes())
        self.assertEqual([env.serialize() for env in envs],before)
        return batch,kernel,native,result

    def test_complete_setup_queue_prices_and_unpriced_setup_ship(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),91)
        def remove(state):
            target=next(key for key,value in state["units"].items() if value["type"]=="torpedo_boat_destroyer")
            del state["units"][target]
        second=changed(first,remove)
        _,kernel,_,result=self.assert_native([first,second])
        values=kernel.inspect(result)
        self.assertEqual(values[0]["axis"]["paid_construction"],10)
        self.assertEqual(values[0]["axis"]["units"]-values[1]["axis"]["units"],5)

    def test_crews_free_ship_repairs_and_paid_only_queue_values(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),2)
        def crew(state):
            exemplar=copy.deepcopy(next(iter(state["units"].values())))
            exemplar.update(id="crew-only",type="militia",owner="japan",zone="land_jap_honshu",turn_origin="land_jap_honshu",
                            movement_remaining=0,movement_allowance=0,route=[],carried_by=None,cargo=[],damage=0,
                            commitments=[],turn_flags={},game_flags={"ship_crew:unresolved":-1})
            state["units"]["crew-only"]=exemplar
            for unit in state["units"].values():
                if unit["owner"]=="japan" and unit["type"]=="battleship":unit["damage"]=1;break
        second=changed(first,crew)
        def paid(state):
            project=next(iter(state["construction"].values()));project["paid_ipp"]+=7
        third=changed(second,paid)
        _,kernel,_,result=self.assert_native([first,second,third]);values=kernel.inspect(result)
        self.assertEqual(values[0]["axis"]["units"],values[1]["axis"]["units"])
        self.assertEqual(values[2]["axis"]["paid_construction"]-values[1]["axis"]["paid_construction"],7)

    def test_negative_facility_value_and_prepaid_repair_ownership(self):
        first=bare(gwrl_cpp.CampaignEnv(str(SCENARIO),1))
        def factory(state):
            state["facilities"]["factory"]={"id":"factory","type":"major_factory","zone":"land_jap_honshu","damage":20,"flags":{}}
        damaged=changed(first,factory)
        def prepaid(state):
            state["nations"]["japan"]["treasury"]-=3
            state["repairs"]["paid"]=repair("japan","factory",3)
        paid=changed(damaged,prepaid)
        captured=changed(paid,lambda state:state["territories"]["land_jap_honshu"].update(possessor="kmt"))
        _,kernel,_,result=self.assert_native([damaged,paid,captured]);values=kernel.inspect(result)
        self.assertEqual(values[0]["axis"]["infrastructure"],-2)
        self.assertEqual(values[1]["axis"]["infrastructure"],1)
        self.assertEqual(values[1]["axis"]["wealth"],values[0]["axis"]["wealth"])
        self.assertEqual(values[2]["allies"]["infrastructure"],-2)

    def test_rail_halves_cross_owner_prepaid_and_neutral_endpoint(self):
        original=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        rail=copy.deepcopy(next(iter(json.loads(original.serialize())["state"]["rails"].values())))
        first=bare(original);a,b=rail["endpoint_a"],rail["endpoint_b"]
        def setup(state):
            state["rails"][rail["id"]]=copy.deepcopy(rail)
            state["rails"][rail["id"]]["damage_by_endpoint"]={a:1}
            state["territories"][a]["possessor"]="japan";state["territories"][b]["possessor"]="kmt"
        split=changed(first,setup)
        def prepaid(state):state["repairs"]["paid"]=repair("japan",rail["id"],1,a)
        paid=changed(split,prepaid)
        def neutral(state):
            nation=next(key for key,value in state["nations"].items() if key.startswith("warlord_") and value["player"] is None)
            state["territories"][b]["possessor"]=nation
        neutral_endpoint=changed(split,neutral)
        captured=changed(paid,lambda state:state["territories"][a].update(possessor="kmt"))
        _,kernel,_,result=self.assert_native([split,paid,neutral_endpoint,captured]);values=kernel.inspect(result)
        self.assertEqual(values[0]["axis"]["infrastructure"],values[0]["allies"]["infrastructure"])
        self.assertEqual(values[1]["axis"]["infrastructure"]-values[0]["axis"]["infrastructure"],.5)
        self.assertEqual(values[2]["allies"]["infrastructure"],0)
        self.assertEqual(values[3]["allies"]["infrastructure"],2*values[0]["allies"]["infrastructure"])

    def test_duplicate_rail_throws_wealth_but_nonterminal_returns_are_zero(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1)
        def duplicate(state):
            value=copy.deepcopy(next(iter(state["rails"].values())));value["id"]="duplicate-physical"
            state["rails"][value["id"]]=value
        second=changed(first,duplicate)
        _,kernel,_,result=self.assert_native([second])
        self.assertEqual(result.errors.cpu().tolist(),[2])
        self.assertEqual(kernel.inspect(result,"terminal"),[(0.,0.,0.)])
        with self.assertRaises(RuntimeError):kernel.inspect(result)

    def test_terminal_general_sum_vector_uses_native_double_order(self):
        first=bare(gwrl_cpp.CampaignEnv(str(SCENARIO),1))
        def finish(state):
            state.update(terminal=True,decisions=[],chance=None,battles={},battle_order=[])
            state["clock"].update(round_index=10,nation_index=3,phase="place_units",completed_rounds=11,
                                  player_turn_serial="44",income_collected=True)
            state["completed_turns"]={key:11 for key in state["completed_turns"]}
        terminal=changed(first,finish)
        _,kernel,_,result=self.assert_native([terminal])
        self.assertEqual(kernel.inspect(result,"terminal"),kernel.inspect(result,"gaps"))
        self.assertEqual(result.rational_terminal_twentieths.cpu().tolist(),result.rational_gaps_twentieths.cpu().tolist())

    def test_actual_cpp_binary64_half_unit_rounding_at_2pow53(self):
        terms=[[2**53,1,1],[2**53,3,0],[-2**53,-1,-1],[-2**53,-3,0],[2**54,2,-2**54],
               [2**53-1,1,-2**53]]
        expected=gwrl_cpp.campaign_wealth_component_sum_probe(terms)
        values,errors=_component_sum_probe(torch.tensor(terms,dtype=torch.int64,device="mps"))
        self.assertEqual(errors.cpu().tolist(),[0]*len(terms))
        self.assertEqual([float(value)/2 for value in values.cpu().tolist()],expected)
        self.assertEqual(values.cpu().tolist()[0],2**53)

    def test_resident_work_has_no_cpu_reads_native_recapture_or_json(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1);batch,kernel,_=self.setup([first]);kernel.evaluate(batch)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("CPU read")), \
                patch.object(torch.Tensor,"tolist",side_effect=AssertionError("CPU read")), \
                patch.object(torch.Tensor,"item",side_effect=AssertionError("CPU read")), \
                patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("CPU read")), \
                patch.object(json,"loads",side_effect=AssertionError("JSON")), \
                patch.object(gwrl_cpp,"capture_device_states",side_effect=AssertionError("Native recapture")):
            result=kernel.evaluate(batch)
        self.assertEqual(result.errors.cpu().tolist(),[0])

    def test_empty_batch_and_foreign_definition(self):
        first=gwrl_cpp.CampaignEnv(str(SCENARIO),1);batch,kernel,_=self.setup([first])
        result=kernel.evaluate(DeviceStateBatch.capture([],context=batch.context))
        self.assertEqual(kernel.inspect(result),[])
        other=gwrl_cpp.CampaignEnv.curriculum(str(SCENARIO),3,1)
        with self.assertRaises(ValueError):kernel.evaluate(DeviceStateBatch.capture([other],device="mps"))


if __name__=="__main__":unittest.main()
