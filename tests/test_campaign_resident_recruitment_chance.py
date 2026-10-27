"""Native Engine.resolveChance parity for the complete resident recruitment seam."""
from dataclasses import replace
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from tests.test_campaign_resident_relations import set_turn
from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
from studies.campaign.backends.content_digest_metal import inspect_digests
from studies.campaign.backends.resident_state_json import ResidentStateJson
from studies.campaign.backends.resident_relations import ResidentPoliticalRelations
from studies.campaign.backends.resident_recruitment import ResidentRecruitment
from studies.campaign.backends.resident_recruitment_effects import ResidentRecruitmentEffects
from studies.campaign.backends.resident_state_income import ResidentIncomeContext
from studies.campaign.backends.resident_recruitment_chance import (
    ResidentRecruitmentChance, RecruitmentChanceCapacities, RecruitmentChanceError,
    POLITICS_RULES_COMPONENT, ECONOMY_RULES_COMPONENT,
    RecruitmentForwardError, RecruitmentPostconditionError,
)


SCENARIO=Path(__file__).resolve().parents[1]/"game_content/scenarios/japan_china_1936"
EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()
MASK64=(1 << 64)-1


def pending_fixture(*,training=False,active="actual",face=1,seed=41,empty=False,mutate=None):
    env=gwrl_cpp.CampaignEnv(str(SCENARIO),seed,training_actions=training)
    doc=json.loads(env.serialize());state=doc["state"]
    minor=next(name for name in state["nations"] if name.startswith("warlord_"))
    set_turn(state,"japan");state["clock"].update(phase="place_units")
    state["nations"][minor].update(controller_nation="japan",player=None,power_status="minor")
    env.restore(json.dumps(doc))
    action=next(a for a in env.legal_actions() if a.kind=="recruitment_roll" and a.parameters["beneficiary"]==minor)
    env.apply_action(action)
    doc=json.loads(env.serialize());state=doc["state"]
    doc["random"].update(active=active,actual=str(MASK64),search=str(1 << 63),training=str((1 << 63)+17),
                         test_tape=[] if face is None else [face],tape_position="0")
    # Preserve opaque generic JSON binary64 values and arbitrary history too.
    state["politics"]["pending"]["unrelated_chance_fixture"]={"exact":1.0000000000000002,"negative_zero":-0.0,
                                                               "opaque":[None,True,"蒙古\u0000"]}
    if training:
        # The empty interface is a valid native import. The chance hook must
        # replace it with the complete canonical order metadata after effects.
        state["action_interface"]={}
    if empty:
        for territory in state["territories"].values():
            if territory["possessor"]==minor:territory["possessor"]="japan"
        state["construction"]={}
        for facility in state["facilities"].values():facility["damage"]=0
    if mutate:mutate(doc,minor)
    env.restore(json.dumps(doc,ensure_ascii=False));return env


def retained_political_fixture(case,*,training=False):
    """Native accepts these sources, then commitChance must reject its result."""
    env=pending_fixture(training=training,face=1);future=env.clone();future.resolve_chance()
    prior=copy.deepcopy(json.loads(future.serialize())["state"]["decisions"][-1])
    doc=json.loads(env.serialize())
    if case=="duplicate_id":
        prior["continuation"]="retained_existing_continuation"
        doc["state"]["politics"]["pending"][prior["continuation"]]={}
    elif case=="erased_continuation":
        doc["random"]["test_tape"]=[12]
        prior["id"]="retained_prior_decision";prior["continuation"]=doc["state"]["chance"]["continuation"]
        for action in prior["options"]:action["decision"]=prior["id"]
    else:raise ValueError(case)
    doc["state"]["decisions"]=[prior]
    env.restore(json.dumps(doc));env.serialize();return env


def retained_naval_fixture(*,training=True,kind="screen",mode="normal",face=12):
    env=pending_fixture(training=training,face=face);doc=json.loads(env.serialize());state=doc["state"]
    ships=sorted(identity for identity,unit in state["units"].items() if unit["owner"]=="japan" and unit["zone"] not in state["territories"])
    assert len(ships)>=3
    low,middle,high=ships[0],ships[len(ships)//2],ships[-1]
    plan="retained_naval_plan";decision="retained_naval_decision"
    data={"screening":[middle]} if kind=="screen" else {"selected":[middle]}
    state["battles"][plan]={"id":plan,"zone":state["units"][middle]["zone"],"attacker":"japan","defender":"japan",
        "stage":"naval_screen_selection" if kind=="screen" else "naval_force_selection","attackers":[],"defenders":[],
        "pending_hits":{},"flags":{"naval_movement_plan":1},"data":data}
    if kind=="screen":
        choices=[("naval_screen_remove",{"unit":middle}),("naval_screen_add",{"unit":low}),
                 ("naval_screen_add",{"unit":high}),("naval_screen_confirm",{"plan":plan})]
        if mode=="empty_selected":data["screening"]=[];choices[1]=("naval_screen_add",{})
        if mode=="absent_selected":data.pop("screening")
        if mode=="unsorted_selected":data["screening"]=[high,low]
        if mode=="no_completion":choices=choices[:2]
        if mode=="bad_parameters":choices[1]=("naval_screen_add",{})
        if mode=="bad_screening":data["screening"]=[1]
        if mode=="missing_plan":state["battles"].pop(plan)
    else:
        choices=[("naval_cancel_move",{"plan":plan}),("naval_force_remove",{"unit":middle}),
                 ("naval_route",{"plan":plan,"path":[state["units"][middle]["zone"]]})]
    options=[{"id":"retained_option_"+str(index),"kind":action,"nation":"japan","player":"axis",
              "decision":decision,"parameters":parameters} for index,(action,parameters) in enumerate(choices)]
    state["decisions"]=[{"id":decision,"kind":"naval_screening_force" if kind=="screen" else "naval_force_selection",
        "nation":"japan","reaction":False,"continuation":plan,"options":options}]
    env.restore(json.dumps(doc));env.serialize();return env


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU execution unavailable")
class ResidentRecruitmentChanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads);torch.mps.empty_cache()

    def setup(self,envs):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        native=gwrl_cpp.capture_device_states(context.native,envs)
        before=DeviceStateBatch.from_native(native,context=context)
        relations=ResidentPoliticalRelations(context,gwrl_cpp.campaign_relations_context(envs[0]))
        recruitment=ResidentRecruitment(relations,gwrl_cpp.campaign_recruitment_context(envs[0]))
        effects=ResidentRecruitmentEffects(recruitment)
        income=ResidentIncomeContext(context,gwrl_cpp.campaign_income_context(envs[0]))
        formatter=ResidentStateJson(CanonicalJsonContext(native,context))
        handler=ResidentRecruitmentChance(context,effects,income,formatter)
        capacity=before.records.shape[1]+6000
        caps=RecruitmentChanceCapacities(state_capacity=capacity,block_capacity=capacity,choice_capacity=512,
            parameter_byte_capacity=2048,string_capacity=before.string_offsets.numel()-1+2048,
            byte_capacity=before.string_bytes.numel()+262144,payload_capacity=32,json_byte_capacity=262144,
            dice_capacity=1,roll_capacity=1)
        expected=formatter.identities(before,byte_capacity=caps.json_byte_capacity)
        return before,handler,caps,expected

    def assert_native(self,source,result,envs,selected=None):
        self.assertTrue(result.committed.item(),{name:value.cpu().tolist() for name,value in result.stage_errors.items()})
        selected=[True]*len(envs) if selected is None else selected
        actual=result.state.restore_envs();expected=[]
        for original,enabled in zip(envs,selected,strict=True):
            candidate=original.clone()
            if enabled:candidate.resolve_chance()
            expected.append(candidate)
        self.assertEqual([env.serialize() for env in actual],[env.serialize() for env in expected])
        # Native recapture uses one common namespace, so every record word,
        # including negative-zero payloads/history and full RNG words, compares.
        for got,wanted in zip(actual,expected,strict=True):
            packed=gwrl_cpp.capture_device_states(source.context.native,[got,wanted])
            rows=np.asarray(packed.record_array());offsets=np.asarray(packed.lane_offsets())
            np.testing.assert_array_equal(rows[offsets[0]:offsets[1]],rows[offsets[1]:offsets[2]])
        self.assertEqual(inspect_digests(result.identities.engine_keys),tuple(env.planning_key() for env in expected))
        self.assertIs(result.identities.source,result.state)
        return actual,expected

    def assert_rollback(self,before,result):
        self.assertFalse(result.committed.item())
        self.assertEqual(result.accepted.cpu().tolist(),[False]*before.lane_count)
        self.assertTrue(torch.equal(result.state.records[:,:before.records.shape[1]],before.records))
        self.assertTrue(torch.equal(result.state.lengths,before.lengths))
        self.assertTrue(torch.equal(result.state.sections,before.sections))
        self.assertTrue(torch.equal(result.state.errors,before.errors))
        self.assertTrue(torch.equal(result.state.string_bytes[:before.string_bytes.numel()],before.string_bytes))
        self.assertTrue(torch.equal(result.state.string_offsets[:before.string_offsets.numel()],before.string_offsets))
        self.assertTrue(torch.equal(result.state.suffix_usage,before.suffix_usage))
        self.assertEqual(torch.count_nonzero(result.state.records[:,before.records.shape[1]:]).item(),0)
        self.assertEqual(torch.count_nonzero(result.state.string_bytes[before.string_bytes.numel():]).item(),0)
        self.assertEqual(torch.count_nonzero(result.state.string_offsets[before.string_offsets.numel():]).item(),0)
        self.assertTrue(all(result.identities.engine_keys.errors.cpu().tolist()))
        self.assertEqual([env.serialize() for env in before.restore_envs()],[env.serialize() for env in result.state.restore_envs()])

    def test_complete_success_and_failed_rolls_all_streams_base_and_training_rules(self):
        for training in (False,True):
            with self.subTest(training=training):
                envs=[pending_fixture(training=training,active=active,face=face)
                      for active in ("actual","search","training") for face in (1,12)]
                snapshots=[env.serialize() for env in envs]
                before,handler,caps,expected=self.setup(envs)
                result=handler.resolve(before,expected,capacities=caps)
                actual,_=self.assert_native(before,result,envs)
                self.assertTrue(json.loads(actual[0].serialize())["state"]["decisions"])
                self.assertFalse(json.loads(actual[1].serialize())["state"]["decisions"])
                self.assertEqual([env.serialize() for env in envs],snapshots)
                self.assertEqual(result.accepted.cpu().tolist(),[True]*6)

    def test_native_rng_draws_without_tape_and_empty_successful_choice_set(self):
        envs=[pending_fixture(active=active,face=None) for active in ("actual","search","training")]
        envs.append(pending_fixture(face=1,empty=True))
        before,handler,caps,expected=self.setup(envs)
        result=handler.resolve(before,expected,capacities=caps)
        actual,_=self.assert_native(before,result,envs)
        self.assertFalse(json.loads(actual[-1].serialize())["state"]["decisions"])

    def test_selected_lanes_leave_unselected_other_chance_and_rng_unchanged(self):
        envs=[pending_fixture(face=1),pending_fixture(face=12),pending_fixture(face=1,
            mutate=lambda doc,minor:doc["state"]["chance"].update(purpose="influence_roll"))]
        before,handler,caps,expected=self.setup(envs)
        selected=torch.tensor([True,False,False],dtype=torch.bool,device="mps")
        result=handler.resolve(before,expected,capacities=caps,selected=selected)
        self.assert_native(before,result,envs,[True,False,False])
        self.assertEqual(result.accepted.cpu().tolist(),[True,False,False])
        unsupported=handler.resolve(before,expected,capacities=caps)
        self.assert_rollback(before,unsupported)
        self.assertTrue(unsupported.stage_errors["preflight"][2].item()&2)
        self.assertFalse(unsupported.handled[2].item())

    def test_one_native_effect_error_rolls_back_other_lane_and_entire_pool(self):
        def threshold_zero(doc,minor):
            continuation=doc["state"]["chance"]["continuation"]
            doc["state"]["politics"]["pending"][continuation]["threshold"]=0
        envs=[pending_fixture(face=1),pending_fixture(face=1,mutate=threshold_zero)]
        old=envs[1].serialize()
        with self.assertRaises(RuntimeError):envs[1].resolve_chance()
        self.assertEqual(envs[1].serialize(),old)
        before,handler,caps,expected=self.setup(envs)
        result=handler.resolve(before,expected,capacities=caps)
        self.assert_rollback(before,result)
        self.assertTrue(result.errors[1].item()&RecruitmentChanceError.EFFECTS)

    def test_each_fixed_capacity_failure_preserves_source_and_exact_retry(self):
        envs=[pending_fixture(face=1)];before,handler,caps,expected=self.setup(envs)
        successful=handler.resolve(before,expected,capacities=caps)
        self.assert_native(before,successful,envs)
        cases=(
            ({"dice_capacity":0,"roll_capacity":0},RecruitmentChanceError.SAMPLE,"sample"),
            ({"choice_capacity":0},RecruitmentChanceError.EFFECTS,"effects_choices"),
            ({"parameter_byte_capacity":0},RecruitmentChanceError.EFFECTS,"effects_parameter_bytes"),
            ({"payload_capacity":0},RecruitmentChanceError.PAYLOAD,"payload"),
            ({"json_byte_capacity":0},RecruitmentChanceError.PREFLIGHT,"before_json_bytes"),
            ({"state_capacity":before.records.shape[1]},None,"effects_state"),
            ({"block_capacity":1},None,"effects_block"),
            ({"string_capacity":before.string_offsets.numel()-1,"byte_capacity":before.string_bytes.numel()},
             RecruitmentChanceError.EFFECTS,"effects_strings"),
        )
        for changed,flag,requirement in cases:
            with self.subTest(changed=changed):
                fixed=replace(caps,**changed)
                sample=None if "dice_capacity" in changed else successful.sampled
                result=handler.resolve(before,expected,capacities=fixed,sampled=sample)
                self.assert_rollback(before,result)
                self.assertTrue(torch.count_nonzero(result.required[requirement]).item())
                if flag:self.assertTrue(result.errors.item()&flag)
        # An allocation retry reuses the very same pending draw, without calling
        # the sampler or advancing a stream/test tape a second time.
        with patch("studies.campaign.backends.resident_recruitment_chance.sample_packed_chance",side_effect=AssertionError("Resampled")):
            retried=handler.resolve(before,expected,capacities=caps,sampled=successful.sampled)
        self.assert_native(before,retried,envs)

    def test_late_event_capacity_failure_undoes_completed_effects_income_reset_and_strings(self):
        envs=[pending_fixture(training=True,face=1)];before,handler,caps,expected=self.setup(envs)
        successful=handler.resolve(before,expected,capacities=caps)
        self.assert_native(before,successful,envs)
        strings,byte_count=successful.required["effects_strings"].cpu().tolist()
        shortages=(replace(caps,string_capacity=max(strings,before.string_offsets.numel()-1),
                            byte_capacity=max(byte_count,before.string_bytes.numel())),
                   replace(caps,state_capacity=successful.required["event_state"].item()-1))
        for fixed in shortages:
            result=handler.resolve(before,expected,capacities=fixed,sampled=successful.sampled)
            self.assert_rollback(before,result)
            self.assertTrue(result.attempted["event"].item())
            self.assertTrue(result.errors.item()&RecruitmentChanceError.EVENT)
            self.assertFalse(result.attempted["random"].item())

    def test_stale_full_engine_keys_and_failed_tapes_are_transactional(self):
        before,handler,caps,expected=self.setup([pending_fixture(face=1)])
        with self.assertRaisesRegex(ValueError,"stale or foreign"):
            handler.resolve(before.snapshot(),expected,capacities=caps)
        changed=expected.engine_keys.hex_bytes.clone();changed[0,0]^=1
        wrong=replace(expected,engine_keys=replace(expected.engine_keys,hex_bytes=changed))
        failed=handler.resolve(before,wrong,capacities=caps)
        self.assert_rollback(before,failed);self.assertTrue(failed.stage_errors["preflight"].item()&4)
        bad=pending_fixture(face=13);old=bad.serialize()
        with self.assertRaises(RuntimeError):bad.resolve_chance()
        self.assertEqual(bad.serialize(),old)
        before,handler,caps,expected=self.setup([bad])
        failed=handler.resolve(before,expected,capacities=caps)
        self.assert_rollback(before,failed);self.assertTrue(failed.errors.item()&RecruitmentChanceError.SAMPLE)

    def test_hot_complete_handler_has_no_host_reads_json_or_native_rule_fallback(self):
        envs=[pending_fixture(training=True,active="search",face=1)]
        before,handler,caps,expected=self.setup(envs)
        warm=handler.resolve(before,expected,capacities=caps)
        self.assert_native(before,warm,envs)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("Host transfer")), \
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("Host list")), \
             patch.object(torch.Tensor,"item",side_effect=AssertionError("Host scalar")), \
             patch.object(torch.Tensor,"numpy",side_effect=AssertionError("Host numpy")), \
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("Host bool")), \
             patch.object(torch.mps,"synchronize",side_effect=AssertionError("Default diagnostic fence")), \
             patch.object(json,"loads",side_effect=AssertionError("JSON parse")), \
             patch.object(json,"dumps",side_effect=AssertionError("JSON serialize")), \
             patch.object(gwrl_cpp,"campaign_recruitment_oracle",side_effect=AssertionError("CPU recruitment fallback")):
            result=handler.resolve(before,expected,capacities=caps)
        self.assert_native(before,result,envs)
        trace=[]
        traced=handler.resolve(before,expected,capacities=caps,profile=trace.append)
        self.assert_native(before,traced,envs)
        self.assertEqual(trace,["preflight","sample","effects","income","reset","forward_capability","forward",
                                "clock","validation","identity","payload","event","random","publish"])
        with self.assertRaises(TypeError):handler.resolve(before,expected,capacities=caps,profile=True)

    def test_explicit_reservation_reuses_allocations_empty_batch_and_shrink_rejection(self):
        envs=[pending_fixture(face=1)];before,handler,caps,expected=self.setup(envs)
        for component in (POLITICS_RULES_COMPONENT,ECONOMY_RULES_COMPONENT):
            legacy=copy.copy(before.context)
            legacy.rules_id="+".join(value for value in legacy.rules_id.split("+") if value!=component)
            with self.assertRaisesRegex(ValueError,"legacy rules are unsupported"):
                ResidentRecruitmentChance(legacy,handler.effects,handler.income,handler.state_json)
        reserved=handler.reserve(before,caps);again=handler.reserve(reserved,caps)
        self.assertIs(reserved.records,again.records);self.assertIs(reserved.string_bytes,again.string_bytes)
        self.assertIs(reserved.string_offsets,again.string_offsets)
        expected=handler.state_json.identities(reserved,byte_capacity=caps.json_byte_capacity)
        result=handler.resolve(reserved,expected,capacities=caps)
        self.assert_native(reserved,result,envs)
        self.assertEqual(result.state.records.shape,reserved.records.shape)
        self.assertEqual(result.state.string_offsets.shape,reserved.string_offsets.shape)
        self.assertEqual(result.state.string_bytes.shape,reserved.string_bytes.shape)
        with self.assertRaisesRegex(ValueError,"shrink"):
            handler.resolve(reserved,expected,capacities=replace(caps,state_capacity=reserved.records.shape[1]-1))
        empty=reserved.fork([]);identity=handler.state_json.identities(empty,byte_capacity=caps.json_byte_capacity)
        result=handler.resolve(empty,identity,capacities=caps)
        self.assertTrue(result.committed.item());self.assertEqual(result.errors.numel(),0)
        self.assertEqual(result.state.records.shape,empty.records.shape)

    def test_native_postvalidation_failures_from_valid_restored_sources_roll_back_whole_cohort(self):
        cases=(("duplicate_id","Invalid/duplicate pending decision",RecruitmentPostconditionError.DECISION_ID),
               ("erased_continuation","Missing political decision continuation",RecruitmentPostconditionError.POLITICAL_CONTINUATION))
        for training in (False,True):
            for case,message,flag in cases:
                with self.subTest(training=training,case=case):
                    bad=retained_political_fixture(case,training=training);original=bad.serialize()
                    with self.assertRaisesRegex(RuntimeError,message):bad.resolve_chance()
                    self.assertEqual(bad.serialize(),original)
                    envs=[pending_fixture(training=training,face=1),bad]
                    before,handler,caps,expected=self.setup(envs)
                    result=handler.resolve(before,expected,capacities=caps)
                    self.assert_rollback(before,result)
                    self.assertTrue(result.errors[1].item()&RecruitmentChanceError.VALIDATION)
                    self.assertTrue(result.stage_errors["validation"][1].item()&flag)
                    self.assertFalse(result.attempted["event"].any().item())

    def test_retained_training_screening_forwards_exactly_in_source_order(self):
        modes=("normal","empty_selected","absent_selected","unsorted_selected")
        envs=[retained_naval_fixture(mode=mode) for mode in modes]
        before,handler,caps,expected=self.setup(envs);result=handler.resolve(before,expected,capacities=caps)
        actual,_=self.assert_native(before,result,envs)
        counts=[len(json.loads(env.serialize())["state"]["decisions"][-1]["options"]) for env in actual]
        self.assertEqual(counts,[2,3,3,2])
        # The unwrapped human rules retain their editable picker unchanged.
        plain=retained_naval_fixture(training=False)
        before,handler,caps,expected=self.setup([plain]);self.assert_native(before,handler.resolve(before,expected,capacities=caps),[plain])

    def test_retained_screening_native_hook_rejections_are_atomic(self):
        for mode in ("no_completion","bad_parameters","bad_screening","missing_plan"):
            with self.subTest(mode=mode):
                bad=retained_naval_fixture(mode=mode);original=bad.serialize()
                with self.assertRaises((RuntimeError,IndexError)):bad.resolve_chance()
                self.assertEqual(bad.serialize(),original)
                before,handler,caps,expected=self.setup([pending_fixture(training=True),bad])
                result=handler.resolve(before,expected,capacities=caps)
                self.assert_rollback(before,result)
                self.assertTrue(result.errors[1].item()&RecruitmentChanceError.FORWARD)
                self.assertTrue(result.stage_errors["forward"][1].item()&
                                (RecruitmentForwardError.NATIVE_HOOK|RecruitmentForwardError.NO_COMPLETION))
                self.assertFalse(result.attempted["event"].any().item())

    def test_retained_force_is_explicit_capability_rollback_but_unreached_hook_is_allowed(self):
        force=retained_naval_fixture(kind="force");native=force.clone();native.resolve_chance()
        self.assertEqual([action["kind"] for action in json.loads(native.serialize())["state"]["decisions"][-1]["options"]],["naval_route"])
        before,handler,caps,expected=self.setup([force]);result=handler.resolve(before,expected,capacities=caps)
        self.assert_rollback(before,result)
        self.assertTrue(result.errors.item()&RecruitmentChanceError.FORWARD_CAPABILITY)
        self.assertEqual(result.stage_errors["forward_capability"].item(),RecruitmentForwardError.UNSUPPORTED_NAVAL_FORCE)
        self.assertEqual(result.stage_errors["forward"].item(),0)
        # A successful recruitment appends a different top decision, so native
        # forwarding never visits the older fleet picker. Do not over-prune it.
        reached=retained_naval_fixture(kind="force",face=1)
        before,handler,caps,expected=self.setup([reached]);self.assert_native(before,handler.resolve(before,expected,capacities=caps),[reached])


if __name__=="__main__":unittest.main()
