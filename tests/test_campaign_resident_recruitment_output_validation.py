"""Changed-footprint recruitment checks against actual native State validation."""
from dataclasses import replace
import copy
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.device_state import DeviceStateBatch
from studies.campaign.backends.device_state_edits import replace_subtrees
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_recruitment_output_validation import (
    ResidentRecruitmentOutputValidation, RecruitmentOutputError as E,
    RecruitmentOutputUnsupported as U)
from tests import test_campaign_resident_recruitment_choice as choice_tests
from tests.test_campaign_resident_recruitment_choice import fixture, changed, chosen
from tests.test_campaign_resident_recruitment_chance import pending_fixture

EXACT = torch.backends.mps.is_available() and mps_int64_indexing_supported()


def host(state):
    return state.records.cpu().tolist()


def child(rows, root, index):
    at = root+1
    for _ in range(index):
        at = rows[at][4]
    return at


def namespace(state):
    strings = {}
    count, size = state.suffix_usage.cpu().tolist()
    for data, offsets in ((state.context.string_bytes, state.context.string_offsets),
                          (state.string_bytes[:size], state.string_offsets[:count+1])):
        raw = bytes(data.cpu().tolist())
        positions = offsets.cpu().tolist()
        for start, end in zip(positions, positions[1:]):
            strings[raw[start:end].decode()] = len(strings)
    return strings


def lookup(state, lane, section, key):
    rows = host(state)[lane]
    root = int(state.section(section)[lane].cpu().item())
    at = root+1
    token = namespace(state)[key]
    for _ in range(rows[root][1]):
        value = rows[at][4]
        if rows[at][1] == token:
            return value
        at = rows[value][4]
    raise AssertionError((section, key))


def scalar(state, lane, root, value, *, string=False):
    records = state.records.clone()
    if string:
        records[lane, root, 1] = value
    else:
        bits = value & ((1 << 64)-1)
        records[lane, root, 2] = bits & 0xffffffff
        records[lane, root, 3] = bits >> 32
    return replace(state, records=records)


@unittest.skipUnless(EXACT, "Lossless Apple GPU required")
class ResidentRecruitmentOutputValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = torch.get_num_threads()
        torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old)
        torch.mps.empty_cache()

    def setup(self, envs, indices=None):
        driver = choice_tests.ResidentRecruitmentChoiceTests()
        indices = indices or [chosen(env, "recruitment_place_infantry") for env in envs]
        case = driver.setup(envs, indices)
        source, service, _, _ = case
        validator = ResidentRecruitmentOutputValidation(source.context, service.creation.catalog_stats,
                                                       service.recruitment.relations_context)
        result = driver.call(case)
        self.assertTrue(result.committed.item(), result.errors.cpu().tolist())
        return source, result.state, validator

    def assert_valid(self, before, after, validator, *, reset=False, selected=None):
        result = validator.validate(before, after, selected, training_reset_applied=reset)
        self.assertEqual(result.errors.cpu().tolist(), [0]*before.lane_count)
        self.assertEqual(result.unsupported.cpu().tolist(), [0]*before.lane_count)
        # Explicit diagnostic boundary invokes the original native State::validate.
        after.restore_envs()
        return result

    def assert_invalid(self, before, after, validator, category):
        result = validator.validate(before, after, training_reset_applied=False)
        self.assertTrue(result.errors[0].item() & int(category), result.errors.cpu().tolist())
        with self.assertRaises((RuntimeError, ValueError, IndexError)):
            after.restore_envs()
        return result

    def test_all_native_placement_free_work_outputs_and_raw_state_are_read_only(self):
        base = fixture(work=True)
        kinds = ("recruitment_place_infantry", "recruitment_place_militia", "recruitment_advance_ship",
                 "recruitment_repair_facility")
        indices = [chosen(base, kind) for kind in kinds]
        before, after, validator = self.setup([base.clone() for _ in kinds], indices)
        saved = {name:getattr(after, name).clone() for name in
                 ("records", "lengths", "sections", "string_bytes", "string_offsets", "suffix_usage")}
        self.assert_valid(before, after, validator)
        for name, value in saved.items():
            self.assertTrue(torch.equal(value, getattr(after, name)), name)

    def test_negative_movement_and_remaining_over_allowance_match_native_rejection(self):
        before, after, validator = self.setup([fixture()])
        rows = host(after)[0]
        units = int(after.section("state.units")[0].item())
        unit = rows[units+1][4]
        remaining = child(rows, child(rows, unit, 4), 0)
        allowance = child(rows, child(rows, unit, 5), 0)
        for root, value in ((remaining, -1), (allowance, -1), (remaining, 999)):
            self.assert_invalid(before, scalar(after, 0, root, value), validator, E.UNIT)

    def test_absent_catalog_movement_and_unknown_damage_are_not_recomputed(self):
        before, after, validator = self.setup([fixture()])
        rows = host(after)[0]
        root = rows[int(after.section("state.units")[0].item())+1][4]
        allowance = child(rows, root, 5)
        absent = torch.tensor([[[9,0,0,0,1]]], dtype=torch.int64, device="mps")
        edited = replace_subtrees(after, torch.tensor([allowance], dtype=torch.int64, device="mps"), absent,
                                  torch.tensor([1], dtype=torch.int64, device="mps"),
                                  torch.ones(1,dtype=torch.bool,device="mps"),capacity=after.records.shape[1])
        self.assertTrue(edited.committed.item())
        self.assert_invalid(before, edited.state, validator, E.UNIT)
        bad = scalar(after, 0, child(rows, root, 10), 99)
        self.assert_invalid(before, bad, validator, E.UNIT)

    def test_created_unit_facility_collision_is_a_late_native_validation_error(self):
        base = fixture()
        def collide(state):
            state["flags"]["politics_sequence"] = 1000
            zone = next(iter(state["territories"]))
            identity = "political_infantry_1001"
            state["facilities"][identity] = dict(id=identity, type="airbase", zone=zone, damage=0, flags={})
        env = changed(base, collide)
        before, after, validator = self.setup([env])
        self.assert_invalid(before, after, validator, E.UNIT)

    def test_shared_erased_political_continuation_in_retained_decision_is_checked(self):
        def retained(state):
            prior = copy.deepcopy(state["decisions"][-1])
            prior["id"] = "retained_shared_decision"
            for action in prior["options"]:
                action["decision"] = prior["id"]
            state["decisions"].insert(0, prior)
        before, after, validator = self.setup([fixture(mutate=retained)])
        self.assert_invalid(before, after, validator, E.CONTINUATION)

    def test_duplicate_options_and_entitlements_are_validated_against_final_player(self):
        def retained(state):
            prior = copy.deepcopy(state["decisions"][-1])
            prior.update(id="retained_independent", continuation="retained_independent")
            state["politics"]["pending"][prior["continuation"]] = {}
            for action in prior["options"]:
                action["decision"] = prior["id"]
            state["decisions"].insert(0, prior)
        before, after, validator = self.setup([fixture(mutate=retained)])
        self.assert_valid(before, after, validator)
        rows = host(after)[0]
        decisions = int(after.section("state.decisions")[0].item())
        decision = decisions+1
        options = child(rows, decision, 5)
        first, second = options+1, rows[options+1][4]
        aid = child(rows, first, 0)
        duplicate = scalar(after, 0, child(rows, second, 0), rows[aid][1], string=True)
        self.assert_invalid(before, duplicate, validator, E.OPTION)
        wrong = scalar(after, 0, child(rows, first, 2), namespace(after)["allies"], string=True)
        self.assert_invalid(before, wrong, validator, E.ENTITLEMENT)

    def test_new_construction_accepts_facility_types_and_old_project_collisions(self):
        # The native invariant accepts unit OR facility types; source-emplace
        # collisions preserve the old project's already validated type.
        base = fixture(work=True)
        before, after, validator = self.setup([base])
        env = after.restore_envs()[0]
        def award(state):
            state["construction"]["diagnostic_new_award"] = dict(id="diagnostic_new_award", owner="ccp", type="airbase",
                site=None, queue_position=1, paid_ipp=0, remaining_payments=[], flags={})
        with_award = changed(env, award)
        grown = DeviceStateBatch.capture([with_award], context=before.context)
        # The freshly captured pool is independently ordered; use this valid
        # after snapshot as both proof source and destination for the membership
        # acceptance, then inject an invalid freshly inserted unit type below.
        self.assert_valid(grown, grown, validator)
        project = lookup(grown, 0, "state.construction", "diagnostic_new_award")
        rows = host(grown)[0]
        bad = scalar(grown, 0, child(rows, project, 2), namespace(grown)["politics_sequence"], string=True)
        # Build an old-state key set without this award while retaining the
        # append-only namespace, so the validator actually tests a new key.
        from studies.campaign.backends.device_map_edits import build_map_edits,commit_container_edits,MapMode
        roots = grown.section("state.construction").contiguous()
        keys = torch.tensor([namespace(grown)["diagnostic_new_award"]], dtype=torch.int64, device="mps")
        dummy = torch.zeros((1,1,5), dtype=torch.int64, device="mps")
        edit = build_map_edits(grown, roots, keys, torch.full((1,),int(MapMode.ERASE),dtype=torch.int64,device="mps"),
            dummy, torch.zeros(1,dtype=torch.int64,device="mps"),torch.ones(1,dtype=torch.bool,device="mps"),
            capacity=grown.records.shape[1])
        old = commit_container_edits(edit, capacity=grown.records.shape[1]).state
        self.assert_valid(old, grown, validator)
        self.assert_invalid(old, bad, validator, E.CONSTRUCTION)

    def test_surrender_removal_can_orphan_another_nations_repair(self):
        def author(state):
            for territory in state["territories"].values():
                if territory["possessor"] == "kmt":
                    territory["possessor"] = "japan"
            state["construction"]["removed_kmt_project"] = dict(id="removed_kmt_project", owner="kmt", type="infantry",
                site=None, queue_position=1, paid_ipp=0, remaining_payments=[], flags={})
            state["repairs"]["foreign_project_job"] = dict(id="foreign_project_job", owner="japan", target="removed_kmt_project",
                remaining_damage=1, remaining_cost=1, restricts_action=False, endpoint=None)
        before, after, validator = self.setup([fixture(mutate=author)])
        self.assert_invalid(before, after, validator, E.REPAIR)

    def test_surrender_erased_then_reinserted_award_key_revalidates_its_changed_type(self):
        def author(state):
            state["flags"]["politics_sequence"] = 1000
            for territory in state["territories"].values():
                if territory["possessor"] == "kmt":
                    territory["possessor"] = "japan"
            # The selected infantry consumes1001. These old infantry projects
            # are erased by KMT surrender before cavalry awards reuse the IDs.
            for serial in (1002,1003,1004):
                identity = "one_china_award_"+str(serial)
                state["construction"][identity] = dict(id=identity,owner="kmt",type="infantry",site=None,
                    queue_position=1,paid_ipp=0,remaining_payments=[],flags={})
            for unit in state["units"].values():
                if unit["type"] == "cavalry":
                    unit["type"] = "infantry"
            for project in state["construction"].values():
                if project["type"] == "cavalry":
                    project["type"] = "infantry"
        base = fixture(mutate=author)
        source = json.loads(gwrl_cpp.campaign_catalog_stats_context(base)._test_source_json)
        def rename(value):
            if isinstance(value,str):
                return "diagnostic_replaced_cavalry" if value == "cavalry" else value
            if isinstance(value,list):
                return [rename(item) for item in value]
            if isinstance(value,dict):
                return {key:rename(item) for key,item in value.items()}
            return value
        env = gwrl_cpp._campaign_catalog_stats_test_fixture(base,json.dumps(rename(source)))
        before, after, validator = self.setup([env])
        self.assert_invalid(before,after,validator,E.CONSTRUCTION)

    def test_surrender_chance_unknown_attacker_is_a_native_late_error(self):
        def author(state):
            for territory in state["territories"].values():
                if territory["possessor"] == "kmt":
                    territory["possessor"] = "japan"
            state["politics"]["pending"]["last_conqueror_kmt"] = "unknown_surrender_attacker"
            state["construction"]["retained_kmt_ship"] = dict(id="retained_kmt_ship", owner="kmt", type="destroyer",
                site=None, queue_position=1, paid_ipp=0, remaining_payments=[1], flags={})
        before, after, validator = self.setup([fixture(mutate=author)])
        self.assert_invalid(before, after, validator, E.CHANCE)

    def test_core_nonempty_visited_configuration_is_explicit_unsupported(self):
        base = fixture()
        classes = {u["id"]:set(u["classes"]) for doc in json.loads(gwrl_cpp.campaign_catalog_stats_context(base)._test_source_json).values()
                   for u in doc.get("units", [])}
        def author(state):
            removed = {id for id,unit in state["units"].items() if classes[unit["type"]] & {"naval","aircraft","carrier"}}
            state["units"] = {id:unit for id,unit in state["units"].items() if id not in removed}
            for unit in state["units"].values():
                unit.update(cargo=[], carried_by=None)
            state["repairs"] = {id:r for id,r in state["repairs"].items() if r["target"] not in removed}
            state["action_interface"] = {"schema":"campaign-orders-v1", "declined_rail_requests":[],
                "visited_configurations":[{"raiders":{},"aircraft":{},"carriers":{}}]}
        before, after, validator = self.setup([changed(base, author)])
        result = validator.validate(before, after, training_reset_applied=False)
        self.assertEqual(result.errors.item(), 0)
        self.assertEqual(result.unsupported.item(), int(U.VISITED_CONFIGURATION))
        self.assertFalse(result.valid.item())
        after.restore_envs()  # Unsupported does not mean the source is invalid.

    def test_decline_only_request_rechecks_a_removed_project(self):
        def author(state):
            minor = state["decisions"][-1]["nation"]
            border = next(zone for zone,t in state["territories"].items() if t["possessor"] == minor)
            for territory in state["territories"].values():
                if territory["possessor"] == "kmt":
                    territory["possessor"] = "japan"
            state["construction"]["declined_removed_project"] = dict(id="declined_removed_project", owner="kmt", type="infantry",
                site=None, queue_position=1, paid_ipp=0, remaining_payments=[], flags={})
            state["action_interface"] = dict(schema="campaign-orders-v1", visited_configurations=[], declined_rail_requests=[
                dict(sender="japan",recipient=minor,parameters=dict(project="declined_removed_project",zone=border,border=border))])
        before, after, validator = self.setup([fixture(mutate=author)])
        self.assert_invalid(before, after, validator, E.INTERFACE)

    def test_training_reset_profile_has_the_exact_empty_interface(self):
        env = pending_fixture(training=True, face=1)
        env.resolve_chance()
        before, after, validator = self.setup([env])
        self.assert_valid(before, after, validator, reset=True)
        # An empty imported object is valid for CoreRules but is not the
        # mandatory reset output when the caller says its hook was applied.
        blocks = torch.tensor([[[13,0,0,0,1]]], dtype=torch.int64, device="mps")
        changed_state = replace_subtrees(after, after.section("state.action_interface").contiguous(), blocks,
            torch.ones(1,dtype=torch.int64,device="mps"),torch.ones(1,dtype=torch.bool,device="mps"),capacity=after.records.shape[1]).state
        result = validator.validate(before, changed_state, training_reset_applied=True)
        self.assertTrue(result.errors.item() & int(E.INTERFACE))

    def test_actual_pending_decision_controller_cycle_is_explicit_unsupported_without_native_recursion(self):
        def retained(state):
            prior = copy.deepcopy(state["decisions"][-1])
            prior.update(id="retained_cycle_probe", continuation="retained_cycle_probe")
            state["politics"]["pending"][prior["continuation"]] = {}
            for action in prior["options"]:
                action["decision"] = prior["id"]
            state["decisions"].insert(0, prior)
        env = fixture(mutate=retained)
        minor = json.loads(env.serialize())["state"]["decisions"][-1]["nation"]
        before, after, validator = self.setup([env])
        japan = lookup(after,0,"state.nations","japan")
        rows = host(after)[0]
        no_player = torch.tensor([[[9,0,0,0,1]]],dtype=torch.int64,device="mps")
        edited = replace_subtrees(after,torch.tensor([child(rows,japan,1)],dtype=torch.int64,device="mps"),
            no_player,torch.ones(1,dtype=torch.int64,device="mps"),torch.ones(1,dtype=torch.bool,device="mps"),capacity=after.records.shape[1]).state
        japan = lookup(edited,0,"state.nations","japan")
        rows = host(edited)[0]
        controller = torch.tensor([[[9,1,0,0,2],[5,namespace(edited)[minor],0,0,2]]],dtype=torch.int64,device="mps")
        edited = replace_subtrees(edited,torch.tensor([child(rows,japan,0)],dtype=torch.int64,device="mps"),
            controller,torch.full((1,),2,dtype=torch.int64,device="mps"),torch.ones(1,dtype=torch.bool,device="mps"),capacity=edited.records.shape[1]).state
        result = validator.validate(before,edited,training_reset_applied=False)
        self.assertEqual(result.errors.item(),0)
        self.assertEqual(result.unsupported.item(),int(U.CONTROLLER_CYCLE))
        # Deliberately do not invoke recursive native politicalPlayer on this
        # unsupported cyclic graph: native has no defined error for that case.

    def test_selected_laziness_and_no_hot_host_catalog_or_native_calls(self):
        base = fixture()
        before, after, validator = self.setup([base, base.clone()])
        rows = host(after)[1]
        units = int(after.section("state.units")[1].item())
        unit = rows[units+1][4]
        root = child(rows, child(rows, unit, 4), 0)
        bad = scalar(after, 1, root, -1)
        selection = torch.tensor([True,False], dtype=torch.bool, device="mps")
        # Compile/warm before installing traps; metadata only on the timed path.
        validator.validate(before, bad, selection, training_reset_applied=False)
        with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("host transfer")), \
             patch.object(torch.Tensor, "item", side_effect=AssertionError("host scalar")), \
             patch.object(torch.Tensor, "tolist", side_effect=AssertionError("host list")), \
             patch.object(validator.catalog_stats, "query", side_effect=AssertionError("catalog regenerated")), \
             patch.object(gwrl_cpp, "restore_device_states", side_effect=AssertionError("native fallback")), \
             patch.object(json, "loads", side_effect=AssertionError("JSON parse")):
            result = validator.validate(before, bad, selection, training_reset_applied=False)
        self.assertEqual(result.errors.cpu().tolist(), [0,0])
        self.assertEqual(result.valid.cpu().tolist(), [True,False])
        with self.assertRaises(ValueError):
            validator.validate(before, after, torch.ones((2,2),device="mps",dtype=torch.bool)[:,0],training_reset_applied=False)
        with self.assertRaises(ValueError):
            validator.validate(before,after,training_reset_applied=1)


if __name__ == "__main__":
    unittest.main()
