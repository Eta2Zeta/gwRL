"""Route timing excludes Python result boxing and never accepts partial evidence."""
import copy
from dataclasses import replace
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.benchmark_campaign_resident_routes import (
    MODES, POSITIONS, RouteConfig, candidate_requests, exact_results,
    finalize, fixture_label, run,
)


class ResidentRouteBenchmarkContractTests(unittest.TestCase):
    def test_explicit_device_shared_resource_limits_and_true_phase_labels(self):
        config = RouteConfig()
        self.assertEqual(config.batch_sizes, (1, 4, 16, 64))
        for changes in ({"devices": ("cpu",)}, {"devices": ("mps", "cpu")}, {"threads": 3},
                        {"memory_bytes": 8_000_000_001}, {"seconds": 181}, {"batch_sizes": (4, 4)}, {"repeats": 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(config, **changes)
        self.assertEqual(fixture_label({"nation_index": 2, "round_index": 1}, "non_combat_movement"),
                         "japan_round2_non_combat_movement")
        self.assertIsNone(fixture_label({"nation_index": 0, "round_index": 1}, "combat_movement"))
        self.assertIsNone(fixture_label({"nation_index": 2, "round_index": 1}, "interrupt"))

    def test_candidate_paths_modes_towing_and_long_menu_paths_are_never_capped(self):
        zones = ("a", "b", "c", "d")
        nodes = [[1] for _ in zones]
        edges = [[[0] for _ in zones] for _ in zones]
        for a, b in ((0, 1), (1, 2), (2, 3)):
            edges[a][b][0] = 1
        state = {"clock": {"phase": "combat_movement"}, "rails": {
            "dynamic": {"endpoint_a": "a", "endpoint_b": "d"}}, "units": {
            "motor": {"owner": "japan", "zone": "a", "type": "motorized_infantry"},
            "gun": {"owner": "japan", "zone": "a", "type": "artillery"},
            "foreign": {"owner": "kmt", "zone": "a", "type": "infantry"}}}
        long = {"unit": "motor", "path": ["a", "b", "c", "d"], "mode": "ordinary", "combat": True, "towed": "gun"}
        rows = candidate_requests(state, zones, nodes, edges, {"japan"}, [long, long])
        self.assertEqual(sum(row == long for row in rows), 1)
        self.assertTrue(all(row["unit"] != "foreign" for row in rows))
        for path in (["a", "b"], ["a", "d"], ["a", "b", "c"]):
            self.assertEqual({row["mode"] for row in rows if row["unit"] == "motor" and row["path"] == path and row["combat"]}, set(MODES))
            self.assertTrue(any(row["unit"] == "motor" and row["path"] == path and row["combat"] is False for row in rows))
            self.assertTrue(any(row["unit"] == "motor" and row["path"] == path and row.get("towed") == "gun" for row in rows))
        self.assertEqual(rows, candidate_requests(state, zones, nodes, edges, {"japan"}, [long, long]))
        with self.assertRaises(ValueError):
            candidate_requests(state, zones, nodes, edges, {"japan"}, [{**long, "mode": "unimplemented"}])

    def test_every_route_result_field_and_error_is_required(self):
        request = {"unit": "u", "path": ["a", "b"], "mode": "ordinary", "combat": True}
        row = {"allowed": True, "reason": "", "cost": 1, "exhausts_movement": False, "regions": {"asia"},
               "approach": {"from": "a", "to": "b", "node_terrain": {"mountain"}, "border_terrain": set(), "river": False, "river_known": True},
               "exception": 0, "message": ""}
        actual = {**row, "supported": True}
        self.assertTrue(exact_results([row], [actual], [actual], [request])["exact"])
        for changes in ({"cost": 2}, {"regions": set()}, {"exception": 2, "message": "wrong"}, {"supported": False}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                exact_results([row], [{**actual, **changes}], [actual], [request])
        with self.assertRaises(ValueError):
            exact_results([row], [], [actual], [request])

    def test_reports_require_full_grid_all_queries_both_gpu_paths_and_terminal_preparation(self):
        config = RouteConfig(batch_sizes=(4,), repeats=1)
        cases = [{"position": position, "lanes": 4, "queries_per_lane": 3, "queries": 12, "seed": config.seed,
                  "request_sha256": "1"*64, "one_lane_requests_sha256": "2"*64, "native_checkpoint_sha256": "3"*64,
                  "evidence": {"exact": True, "verified_queries": 12, "allowed_queries": 4, "disallowed_queries": 8},
                  "resident_source_evidence": {"exact": True, "verified_lanes": 4},
                  "native_source_witnesses": {"full_native_state_and_all_rng_exact": True}, "source_unchanged": True,
                  "native_query_seconds": [.1], "native_wrapper_wall_seconds": [.12],
                  "gpu_prepare_query_seconds": [.2], "gpu_prepared_query_seconds": [.02]} for position in POSITIONS]
        valid = {"status": "completed", "sources_unchanged": True, "preparation_completed_three_round_games": 1, "cases": cases,
                 "workload_sha256": "4"*64, "terminal_checkpoint_sha256": "5"*64}
        self.assertTrue(finalize(copy.deepcopy(valid), config)["matched_complete_route_queries_and_sources"])
        for mutation in (lambda r:r["cases"].pop(), lambda r:r["cases"].__setitem__(-1, r["cases"][0]),
                         lambda r:r["cases"][0]["evidence"].update(verified_queries=11),
                         lambda r:r["cases"][0].update(gpu_prepared_query_seconds=[]),
                         lambda r:r["cases"][0].update(gpu_prepare_query_seconds=[float("nan")]),
                         lambda r:r["cases"][0]["resident_source_evidence"].update(verified_lanes=3),
                         lambda r:r["cases"][0].update(request_sha256="broken"),
                         lambda r:r["cases"][0].update(seed=17),
                         lambda r:r.update(preparation_completed_three_round_games=0),
                         lambda r:r.update(sources_unchanged=False)):
            report = copy.deepcopy(valid); mutation(report)
            self.assertFalse(finalize(report, config)["matched_complete_route_queries_and_sources"])
            self.assertEqual(report["status"], "incomplete_or_mismatch")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.json"
            with patch("tools.benchmark_campaign_resident_routes.supervise", return_value=copy.deepcopy(valid)) as supervise:
                self.assertTrue(run(config, output)["matched_complete_route_queries_and_sources"])
            self.assertEqual(supervise.call_args.kwargs["worker_script"].name, "benchmark_campaign_resident_routes.py")
            with self.assertRaises(ValueError):
                run(config, output)


class ResidentRouteNativeTimingTests(unittest.TestCase):
    def test_opaque_native_results_match_original_oracle_with_duplicate_owner_lanes(self):
        import gwrl_cpp
        from studies.campaign.curriculum import make_env
        raw = make_env(1951, calendar_rounds=3).raw
        before = raw.serialize(); context = gwrl_cpp.campaign_movement_context(raw)
        queries = [gwrl_cpp.CampaignMovementQuery(lane, "missing", ["unknown", "elsewhere"]) for lane in (0, 1)]
        result = gwrl_cpp.benchmark_campaign_route_oracle(context, [raw, raw], queries, repeats=3)
        self.assertEqual(result.calls, 6); self.assertEqual(result.query_count, 2)
        self.assertTrue(math.isfinite(result.seconds) and result.seconds >= 0)
        self.assertEqual(result.inspect(), gwrl_cpp.campaign_route_oracle(context, [raw, raw], queries))
        self.assertEqual(raw.serialize(), before, "Native timer must preserve complete State/history/all random streams")
        # Inspection owns detached Python containers, never the native results.
        displayed = result.inspect(); displayed[0]["reason"] = "changed display"
        self.assertEqual(result.inspect()[0]["reason"], "Unknown moving unit")

    def test_native_probe_rejects_invalid_requests_before_timing_and_handles_empty_batch(self):
        import gwrl_cpp
        from studies.campaign.curriculum import make_env
        raw = make_env(17, calendar_rounds=3).raw
        context = gwrl_cpp.campaign_movement_context(raw)
        query = gwrl_cpp.CampaignMovementQuery(1, "missing", [])
        with self.assertRaises(ValueError):
            gwrl_cpp.benchmark_campaign_route_oracle(context, [raw], [query])
        with self.assertRaises(ValueError):
            gwrl_cpp.benchmark_campaign_route_oracle(context, [raw], [], repeats=0)
        empty = gwrl_cpp.benchmark_campaign_route_oracle(context, [], [])
        self.assertEqual(empty.calls, 0); self.assertEqual(empty.query_count, 0); self.assertEqual(empty.inspect(), [])


if __name__ == "__main__":
    unittest.main()
