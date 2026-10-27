"""Native Engine.step parity for the complete resident recruitment-roll action."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
from studies.campaign.backends.content_digest_metal import inspect_digests
from studies.campaign.backends.resident_state_json import ResidentStateJson
from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
from studies.campaign.backends.resident_recruitment import ResidentRecruitment
from studies.campaign.backends.resident_recruitment_start import ResidentRecruitmentStart
from studies.campaign.backends.resident_recruitment_action import ResidentRecruitmentAction,RecruitmentActionCapacities,RecruitmentActionError
from studies.campaign.backends.resident_recruitment_effects import ResidentRecruitmentEffects
from studies.campaign.backends.resident_recruitment_chance import ResidentRecruitmentChance,RecruitmentChanceCapacities
from studies.campaign.backends.resident_state_income import ResidentIncomeContext
from tests.test_campaign_resident_recruitment_start import start_fixture
from tests.test_campaign_resident_relations import changed,set_turn

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU execution unavailable")
class ResidentRecruitmentActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs,beneficiaries):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        native=gwrl_cpp.capture_device_states(context.native,envs);before=DeviceStateBatch.from_native(native,context=context)
        relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
        queries=ResidentRecruitment(relations,gwrl_cpp.campaign_recruitment_context(envs[0]))
        P=len(envs)*len(relations.nation_ids)
        menu=queries.rolls(before,capacity=P,**queries.reserve(before,capacity=P))
        actions=queries.inspect(menu);lanes=[]
        for request,meta in zip(menu.queries.requests.cpu().tolist(),menu.queries.metadata.cpu().tolist(),strict=True):lanes.extend([request[0]]*meta[7])
        selected=[next(row for row,action in enumerate(actions) if lanes[row]==lane and json.loads(action)["parameters"]["beneficiary"]==minor)
                  for lane,minor in enumerate(beneficiaries)]
        selections=torch.tensor(selected,dtype=torch.int64,device="mps")
        formatter=ResidentStateJson(CanonicalJsonContext(native,context))
        income=ResidentIncomeContext(context,gwrl_cpp.campaign_income_context(envs[0]))
        handler=ResidentRecruitmentAction(context,ResidentRecruitmentStart(queries),income,formatter)
        S=before.records.shape[1]+2048
        capacities=RecruitmentActionCapacities(S,S,menu.arena.string_offsets.numel()-1+256,
            menu.arena.string_bytes.numel()+65536,32,262144)
        expected=formatter.identities(before,byte_capacity=capacities.json_byte_capacity)
        return before,handler,capacities,expected,menu,selections,[actions[row] for row in selected]

    def apply(self,setup,*,selected=None,capacities=None,menu=None,expected=None,selections=None):
        before,handler,caps,key,cached,chosen,_=setup
        return handler.apply(before,key if expected is None else expected,cached if menu is None else menu,
            chosen if selections is None else selections,capacities=caps if capacities is None else capacities,selected=selected)

    def assert_native(self,setup,result,envs,selected=None):
        source,handler,caps,key,menu,selections,actions=setup
        self.assertTrue(result.committed.cpu().item(),{name:value.cpu().tolist() for name,value in result.stage_errors.items()})
        enabled=[True]*len(envs) if selected is None else selected
        expected=[]
        for env,active,text in zip(envs,enabled,actions,strict=True):
            candidate=env.clone()
            if active:
                wanted=json.loads(text);action=next(action for action in candidate.legal_actions() if action.id==wanted["id"])
                self.assertEqual({"id":action.id,"kind":action.kind,"player":action.player,"nation":action.nation,
                    "decision":action.decision,"parameters":action.parameters},wanted)
                candidate.apply_action(action)
            expected.append(candidate)
        actual=result.state.restore_envs()
        self.assertEqual([env.serialize() for env in actual],[env.serialize() for env in expected])
        for got,wanted in zip(actual,expected,strict=True):
            packed=gwrl_cpp.capture_device_states(source.context.native,[got,wanted]);rows=np.asarray(packed.record_array());offsets=np.asarray(packed.lane_offsets())
            np.testing.assert_array_equal(rows[offsets[0]:offsets[1]],rows[offsets[1]:offsets[2]])
        self.assertEqual(inspect_digests(result.identities.engine_keys),tuple(env.planning_key() for env in expected))
        self.assertIs(result.identities.source,result.state)
        self.assertEqual([json.loads(env.serialize())["random"] for env in actual],[json.loads(env.serialize())["random"] for env in envs])
        return actual,expected

    def assert_rollback(self,before,result):
        self.assertFalse(result.committed.cpu().item());self.assertEqual(result.accepted.cpu().tolist(),[False]*before.lane_count)
        for name in ("records","string_bytes","string_offsets"):
            original=getattr(before,name);after=getattr(result.state,name)
            slices=tuple(slice(0,n) for n in original.shape);self.assertTrue(torch.equal(after[slices],original),name)
        for name in ("lengths","sections","errors","suffix_usage"):self.assertTrue(torch.equal(getattr(before,name),getattr(result.state,name)),name)
        self.assertTrue(all(result.identities.engine_keys.errors.cpu().tolist()))
        self.assertEqual([env.serialize() for env in result.state.restore_envs()],[env.serialize() for env in before.restore_envs()])

    def test_full_native_state_history_and_rng_all_streams_base_and_training(self):
        for training in (False,True):
            with self.subTest(training=training):
                pairs=[start_fixture(training=training,active=active) for active in ("actual","search","training")]
                envs=[env for env,minor in pairs];setup=self.setup(envs,[minor for env,minor in pairs]);original=[env.serialize() for env in envs]
                actual,_=self.assert_native(setup,self.apply(setup),envs)
                self.assertEqual([env.serialize() for env in envs],original)
                for env,text in zip(actual,setup[-1],strict=True):
                    state=json.loads(env.serialize())["state"];event=state["history"][-1]
                    self.assertEqual(event["kind"],"action");self.assertEqual(event["payload"],json.loads(text))
                    self.assertEqual(event["payload"]["nation"],"japan")
                    self.assertNotEqual(state["chance"]["nation"],event["payload"]["nation"])

    def test_ccp_mongolia_and_zero_treasury_need_no_ipp_payment(self):
        env,minor=start_fixture();ccp=changed(env,lambda s:set_turn(s,"ccp"));mongolia=changed(env,lambda s:set_turn(s,"mongolia"))
        poor=changed(env,lambda s:s["nations"]["japan"].update(treasury=0))
        envs=[ccp,mongolia,poor];setup=self.setup(envs,["ccp","mongolia",minor]);actual,_=self.assert_native(setup,self.apply(setup),envs)
        self.assertEqual(json.loads(actual[2].serialize())["state"]["nations"]["japan"]["treasury"],0)

    def test_existing_continuation_collision_and_opaque_payloads_follow_native_upsert(self):
        env,minor=start_fixture(sequence=-2)
        env=changed(env,lambda s:s["politics"]["pending"].update({"recruitment_roll_-1":{"old":[None,-0.0,1.0000000000000002]}}))
        setup=self.setup([env],[minor]);actual,_=self.assert_native(setup,self.apply(setup),[env])
        state=json.loads(actual[0].serialize())["state"]
        self.assertEqual(state["chance"]["id"],"recruitment_roll_-1")
        self.assertEqual(set(state["politics"]["pending"]["recruitment_roll_-1"]),{"beneficiary","threshold"})

    def test_outer_refresh_overwrites_stale_components_and_training_reset_without_clock_advance(self):
        env,minor=start_fixture(training=True)
        def stale(state):
            for nation in state["nations"].values():nation.update(income_components={"obsolete":123},income_known=False)
        env=changed(env,stale);setup=self.setup([env],[minor]);actual,_=self.assert_native(setup,self.apply(setup),[env])
        old=json.loads(env.serialize())["state"];new=json.loads(actual[0].serialize())["state"]
        self.assertEqual(new["clock"],old["clock"])
        self.assertTrue(all(nation["income_known"] and "obsolete" not in nation["income_components"] for nation in new["nations"].values()))
        self.assertEqual(new["action_interface"],{"schema":"campaign-orders-v1","visited_configurations":[],"declined_rail_requests":[]})

    def test_cached_before_key_and_source_binding_reject_stale_or_foreign_inputs(self):
        env,minor=start_fixture();setup=self.setup([env],[minor]);before,handler,caps,expected,menu,selections,_=setup
        damaged=expected.engine_keys.hex_bytes.clone();damaged[0,0]^=1
        stale=replace(expected,engine_keys=replace(expected.engine_keys,hex_bytes=damaged))
        result=self.apply(setup,expected=stale);self.assertTrue(result.errors[0].cpu().item()&RecruitmentActionError.PREFLIGHT);self.assert_rollback(before,result)
        with self.assertRaises(ValueError):handler.apply(before.snapshot(),expected,menu,selections,capacities=caps)
        with self.assertRaises(ValueError):handler.apply(before,expected,replace(menu,source=before.snapshot()),selections,capacities=caps)
        with self.assertRaises(ValueError):handler.apply(before,expected,menu,selections.to("cpu"),capacities=caps)

    def test_native_engine_immediate_land_filter_is_stricter_than_raw_recruitment_menu(self):
        base,minor=start_fixture();old_action=next(action for action in base.legal_actions() if action.kind=="recruitment_roll" and action.parameters["beneficiary"]==minor)
        env=changed(base,lambda s:s["flags"].update(immediate_land_battles=1));self.assertFalse(env.legal_actions())
        with self.assertRaises(RuntimeError):env.clone().apply_action(old_action)
        setup=self.setup([env],[minor]);result=self.apply(setup)
        self.assertTrue(result.errors[0].cpu().item()&RecruitmentActionError.PREFLIGHT);self.assert_rollback(setup[0],result)

    def test_selected_cohort_rolls_back_together_and_skips_unselected_overflow(self):
        good,minor=start_fixture();bad,_=start_fixture(sequence=2**31-1);setup=self.setup([good,bad],[minor,minor])
        result=self.apply(setup)
        self.assertEqual(result.stage_errors["effects"].cpu().tolist(),[0,2])
        self.assertEqual(result.errors.cpu().tolist(),[int(RecruitmentActionError.EFFECTS)]*2)
        self.assert_rollback(setup[0],result)
        selected=torch.tensor([True,False],dtype=torch.bool,device="mps")
        result=self.apply(setup,selected=selected);self.assert_native(setup,result,[good,bad],[True,False])
        idle=self.apply(setup,selected=torch.zeros(2,dtype=torch.bool,device="mps"))
        self.assertTrue(idle.committed.cpu().item());self.assertTrue(torch.equal(idle.state.suffix_usage,setup[0].suffix_usage))
        self.assertEqual([env.serialize() for env in idle.state.restore_envs()],[good.serialize(),bad.serialize()])

    def test_effect_payload_and_hash_capacities_rollback_and_retry(self):
        env,minor=start_fixture();setup=self.setup([env],[minor]);before,handler,caps,expected,menu,selections,_=setup
        variants=[replace(caps,state_capacity=before.records.shape[1]),replace(caps,block_capacity=1),
                  replace(caps,payload_capacity=14),replace(caps,json_byte_capacity=0)]
        for capacities in variants:
            with self.subTest(capacities=capacities):self.assert_rollback(before,self.apply(setup,capacities=capacities))
        complete=self.apply(setup);self.assert_native(setup,complete,[env])
        before_size=complete.required["before_json_bytes"][0].cpu().item();after_size=complete.required["after_json_bytes"][0].cpu().item()
        self.assertGreater(after_size,before_size)
        too_small=self.apply(setup,capacities=replace(caps,json_byte_capacity=after_size-1))
        self.assertTrue(too_small.errors[0].cpu().item()&RecruitmentActionError.IDENTITY);self.assert_rollback(before,too_small)

    def test_late_event_block_and_string_capacities_never_publish_partial_action(self):
        env,minor=start_fixture()
        def history(state):state["history"].extend({"kind":"fixture","payload":{"i":i},"after_state_key":"old"} for i in range(100))
        long=changed(env,history);setup=self.setup([long],[minor]);caps=replace(setup[2],block_capacity=256)
        result=self.apply(setup,capacities=caps);self.assertTrue(result.errors[0].cpu().item()&RecruitmentActionError.EVENT);self.assert_rollback(setup[0],result)
        setup=self.setup([env],[minor]);before,handler,caps,expected,menu,selections,_=setup
        used,size=menu.arena.suffix_usage.cpu().tolist()
        tight=replace(menu,arena=replace(menu.arena,string_offsets=menu.arena.string_offsets[:used+1].contiguous(),string_bytes=menu.arena.string_bytes[:size].contiguous()))
        limited=replace(caps,string_capacity=used+1,byte_capacity=size+28)
        result=self.apply(setup,menu=tight,capacities=limited)
        self.assertTrue(result.errors[0].cpu().item()&RecruitmentActionError.EVENT);self.assert_rollback(before,result)
        self.assertGreater(result.required["event_strings"][1].cpu().item(),limited.byte_capacity)
        self.assert_native(setup,self.apply(setup),[env])

    def test_postflight_rejects_changed_clock_random_and_invalid_new_chance(self):
        env,minor=start_fixture();setup=self.setup([env],[minor]);before,handler,caps,expected,menu,selections,_=setup
        original=handler.effects.apply
        for fault,bit in (("clock",RecruitmentActionError.CLOCK),("random",RecruitmentActionError.RANDOM),("chance",RecruitmentActionError.STATE)):
            with self.subTest(fault=fault):
                def broken(*args,**kwargs):
                    result=original(*args,**kwargs);rows=result.state.records.clone()
                    if fault=="clock":root=result.state.section("state.clock")[0].cpu().item();rows[0,root+3,2]=0
                    elif fault=="random":root=result.state.section("random.actual")[0].cpu().item();rows[0,root,2]^=1
                    else:root=result.state.section("state.chance")[0].cpu().item();rows[0,root+4,1]=int(before.context.prefix_lookup_ids(("beneficiary",))[0])
                    return replace(result,state=replace(result.state,records=rows))
                with patch.object(handler.effects,"apply",side_effect=broken):result=self.apply(setup)
                self.assertTrue(result.errors[0].cpu().item()&bit);self.assert_rollback(before,result)

    def test_complete_action_then_existing_chance_handler_matches_two_native_steps(self):
        env,minor=start_fixture(training=True);setup=self.setup([env],[minor]);started=self.apply(setup)
        actual,native=self.assert_native(setup,started,[env]);before,handler,caps,*_=setup
        chance=ResidentRecruitmentChance(before.context,ResidentRecruitmentEffects(handler.effects.recruitment),handler.income,handler.state_json)
        S=started.state.records.shape[1]+4096
        chance_caps=RecruitmentChanceCapacities(S,S,128,1024,started.state.string_offsets.numel()-1+256,
            started.state.string_bytes.numel()+65536,32,262144,1,1)
        resolved=chance.resolve(started.state,started.identities,capacities=chance_caps)
        self.assertTrue(resolved.committed.cpu().item(),{k:v.cpu().tolist() for k,v in resolved.stage_errors.items()})
        native[0].resolve_chance();self.assertEqual(resolved.state.restore_envs()[0].serialize(),native[0].serialize())
        self.assertEqual(inspect_digests(resolved.identities.engine_keys),(native[0].planning_key(),))

    def test_no_hot_host_native_json_or_menu_regeneration_and_empty_batch(self):
        env,minor=start_fixture();setup=self.setup([env],[minor]);self.apply(setup)
        before,handler,caps,expected,menu,selections,_=setup;query=handler.effects.recruitment
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host values")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(json,"loads",side_effect=AssertionError("JSON hot path")), \
             patch.object(gwrl_cpp.CampaignEnv,"apply_action",side_effect=AssertionError("Native fallback")), \
             patch.object(query,"rolls",side_effect=AssertionError("Legal menu regeneration")), \
             patch.object(query,"choices",side_effect=AssertionError("Choice regeneration")), \
             patch.object(query.relations_context,"compute",side_effect=AssertionError("Relation regeneration")):
            result=self.apply(setup)
        self.assert_native(setup,result,[env])
        empty=DeviceStateBatch.capture([],context=before.context);empty_menu=query.rolls(empty,capacity=0)
        empty_key=handler.state_json.identities(empty,byte_capacity=caps.json_byte_capacity)
        result=handler.apply(empty,empty_key,empty_menu,torch.zeros(0,dtype=torch.int64,device="mps"),capacities=caps)
        self.assertTrue(result.committed.cpu().item());self.assertEqual(result.state.restore_envs(),[])


if __name__=="__main__":unittest.main()
