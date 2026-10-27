"""Synthetic mixed audit histories retain every state/RNG/query bit."""
import copy
from dataclasses import replace
import hashlib
import json
import unittest

from tools.benchmark_campaign_resident_routes import (
    POSITIONS,RouteConfig,synthetic_history_lane,exact_mixed_resident,mixed_native_witnesses,
    candidate_requests,finalize,
)


class RouteHistoryStressTests(unittest.TestCase):
    def native(self):
        from studies.campaign.curriculum import make_env
        return make_env(1951,calendar_rounds=3).raw

    def test_annotations_are_append_only_schema_valid_and_preserve_all_board_and_rng_fields(self):
        raw=self.native();before=raw.serialize();base=json.loads(before)
        lanes=[synthetic_history_lane(raw,i,256,"opening-proof") for i in range(4)]
        all_strings=set()
        for i,(lane,proof) in enumerate(lanes):
            value=json.loads(lane.serialize());event=value["state"]["history"][-1]
            self.assertEqual(value["random"],base["random"])
            self.assertEqual({k:v for k,v in value["state"].items() if k!="history"},
                             {k:v for k,v in base["state"].items() if k!="history"})
            self.assertEqual(value["state"]["history"][:-1],base["state"]["history"])
            self.assertEqual(event["after_state_key"],raw.planning_key())
            self.assertTrue(event["payload"]["synthetic_benchmark_annotation"])
            self.assertEqual(event["payload"]["lane"],i)
            strings=event["payload"]["unique_strings"]
            self.assertEqual(len(strings),256);self.assertEqual(len(set(strings)),256)
            self.assertTrue(all_strings.isdisjoint(strings));all_strings.update(strings)
            self.assertTrue(proof["boards_and_random_unchanged"] and proof["original_history_prefix_preserved"])
        self.assertEqual(len(all_strings),1024);self.assertEqual(raw.serialize(),before)
        default,proof=synthetic_history_lane(raw,0,0,"unused")
        self.assertEqual(default.serialize(),before);self.assertEqual(proof["added_history_events"],0)

    def test_every_independent_mixed_capture_bit_and_native_witness_is_checked(self):
        from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
        import gwrl_cpp
        raw=self.native();envs=[synthetic_history_lane(raw,i,16,"mixed-proof")[0] for i in range(4)]
        context=DeviceStateContext(gwrl_cpp.device_state_context(raw),"cpu")
        actual=DeviceStateBatch.capture(envs,context=context);reference=DeviceStateBatch.capture(envs,context=context)
        evidence=exact_mixed_resident(actual,reference,inspection_chunk_bytes=1)
        self.assertTrue(evidence["exact"]);self.assertEqual(evidence["verified_lanes"],4)
        witness=mixed_native_witnesses(actual,[env.serialize() for env in envs])
        self.assertTrue(witness["full_native_state_and_all_rng_exact"])
        # One changed high-width RNG word in a non-first lane is a mismatch.
        row=int(actual.section("random.search")[2]);actual.records[2,row,2]^=1
        with self.assertRaises(AssertionError):exact_mixed_resident(actual,reference)
        with self.assertRaises(ValueError):mixed_native_witnesses(actual,[env.serialize() for env in envs])

    def test_identical_boards_retain_identical_complete_ordered_candidates(self):
        import gwrl_cpp
        raw=self.native();native=gwrl_cpp.campaign_movement_context(raw)
        state=json.loads(raw.serialize())["state"]
        controlled={name for name in state["nations"]}  # stress workload, not a legal-action filter
        expected=candidate_requests(state,native.zones,native.node_array(),native.edge_array(),controlled)
        for i in range(3):
            lane,_=synthetic_history_lane(raw,i,64,"query-proof")
            actual=candidate_requests(json.loads(lane.serialize())["state"],native.zones,native.node_array(),native.edge_array(),controlled)
            self.assertEqual(actual,expected)

    def test_explicit_uncapped_history_option_and_collision_rejection(self):
        self.assertEqual(RouteConfig().synthetic_history_strings_per_lane,0)
        self.assertEqual(RouteConfig(synthetic_history_strings_per_lane=256).synthetic_history_strings_per_lane,256)
        # A large request remains explicit; the existing resource/wall guard,
        # rather than silent history truncation, controls whether it can run.
        self.assertEqual(RouteConfig(synthetic_history_strings_per_lane=1_000_000).synthetic_history_strings_per_lane,1_000_000)
        for value in (-1,True,1.5):
            with self.assertRaises(ValueError):RouteConfig(synthetic_history_strings_per_lane=value)
        raw=self.native();before=raw.serialize()
        text="__gwrl_synthetic_route_history__/collision/lane-00000000/entry-00000000"
        with self.assertRaises(ValueError):synthetic_history_lane(raw,0,1,"collision",forbidden_strings={text})
        self.assertEqual(raw.serialize(),before)
        for lane,count,namespace in ((True,1,"x"),(-1,1,"x"),(0,True,"x"),(0,1,"")):
            with self.assertRaises(ValueError):synthetic_history_lane(raw,lane,count,namespace)

    def test_report_needs_complete_synthetic_source_and_history_evidence(self):
        config=RouteConfig(batch_sizes=(4,),repeats=1,synthetic_history_strings_per_lane=256)
        hashes=["3"*64]+[f"{i:064x}" for i in range(1,4)]
        cases=[]
        for position in POSITIONS:
            cases.append({"position":position,"lanes":4,"queries_per_lane":3,"queries":12,"seed":config.seed,
                "request_sha256":"1"*64,"one_lane_requests_sha256":"2"*64,"native_checkpoint_sha256":hashes[0],
                "evidence":{"exact":True,"verified_queries":12},"resident_source_evidence":{"exact":True,"verified_lanes":4},
                "native_source_witnesses":{"full_native_state_and_all_rng_exact":True},"source_unchanged":True,
                "native_query_seconds":[.1],"native_wrapper_wall_seconds":[.12],"gpu_prepare_query_seconds":[.2],"gpu_prepared_query_seconds":[.02],
                "synthetic_history":{"enabled":True,"schema_valid_synthetic_annotations":True,"strings_per_lane":256,
                    "added_events_per_lane":1,"distinct_synthetic_strings":1024,"active_global_sid_growth":1024,
                    "original_history_prefix_preserved":True,"boards_and_random_unchanged":True,
                    "state_without_history_sha256":"6"*64,"random_sha256":"7"*64,"base_native_checkpoint_sha256":"8"*64,
                    "native_lane_checkpoint_sha256":hashes[:]}})
        valid={"status":"completed","sources_unchanged":True,"preparation_completed_three_round_games":1,"cases":cases,
               "workload_sha256":"4"*64,"terminal_checkpoint_sha256":"5"*64}
        self.assertTrue(finalize(copy.deepcopy(valid),config)["matched_complete_route_queries_and_sources"])
        mutations=(lambda r:r["cases"][0].pop("synthetic_history"),
                   lambda r:r["cases"][0]["synthetic_history"].update(boards_and_random_unchanged=False),
                   lambda r:r["cases"][0]["synthetic_history"].update(original_history_prefix_preserved=False),
                   lambda r:r["cases"][0]["synthetic_history"].update(active_global_sid_growth=1000),
                   lambda r:r["cases"][0]["synthetic_history"].update(native_lane_checkpoint_sha256=hashes[:3]),
                   lambda r:r["cases"][0]["synthetic_history"].update(native_lane_checkpoint_sha256=[hashes[0]]*4),
                   lambda r:r["cases"][0].update(native_checkpoint_sha256="9"*64))
        for mutation in mutations:
            bad=copy.deepcopy(valid);mutation(bad)
            self.assertFalse(finalize(bad,config)["matched_complete_route_queries_and_sources"])



# The mixed whole-batch reference must also verify real device buffers. Original
# CPU environments keep the exact-integer gate and skip only this GPU case.
import torch
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class MixedRouteHistoryDeviceTests(unittest.TestCase):
    def test_mixed_history_pool_native_gpu_queries_and_every_source_bit_match(self):
        import gwrl_cpp
        from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
        from studies.campaign.backends.resident_routes import ResidentRoutes
        from studies.campaign.curriculum import make_env
        previous=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
        try:
            raw=make_env(1951,calendar_rounds=3).raw
            envs=[synthetic_history_lane(raw,i,256,"device-proof")[0] for i in range(4)]
            serialized=[env.serialize() for env in envs]
            native=gwrl_cpp.device_state_context(raw);context=DeviceStateContext(native,"mps")
            actual=DeviceStateBatch.capture(envs,context=context)
            reference=DeviceStateBatch.capture(envs,context=DeviceStateContext(native,"cpu"))
            baseline=DeviceStateBatch.capture([raw],context=reference.context)
            self.assertGreaterEqual(int(reference.suffix_usage[0]-baseline.suffix_usage[0]),1024)
            route_context=gwrl_cpp.campaign_movement_context(raw);kernel=ResidentRoutes(context,route_context)
            state=json.loads(raw.serialize())["state"]
            rows=candidate_requests(state,route_context.zones,route_context.node_array(),route_context.edge_array(),set(state["nations"]))
            expanded=[{**row,"lane":lane} for lane in range(4) for row in rows]
            packed=kernel.pack_requests(actual,expanded)
            oracle=gwrl_cpp.campaign_route_oracle(route_context,envs,[gwrl_cpp.CampaignMovementQuery(row["lane"],row["unit"],
                row["path"],row["mode"],row["combat"],row.get("towed")) for row in expanded])
            for mode in ("reference","fused","fused_indexed"):
                prepared=kernel.prepare(actual,implementation=mode)
                result=kernel.inspect(kernel.query(actual,packed,prepared=prepared))
                self.assertEqual([{key:value for key,value in row.items() if key!="supported"} for row in result],oracle)
                self.assertTrue(all(row["supported"] for row in result))
            self.assertTrue(exact_mixed_resident(actual,reference)["exact"])
            self.assertTrue(mixed_native_witnesses(actual,serialized)["full_native_state_and_all_rng_exact"])
            self.assertEqual([env.serialize() for env in envs],serialized)
        finally:
            torch.mps.empty_cache();torch.set_num_threads(previous)


if __name__=="__main__":unittest.main()
