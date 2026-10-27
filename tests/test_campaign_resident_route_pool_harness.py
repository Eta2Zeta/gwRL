"""Persistent native pool is explicit and setup remains outside query calls."""
import copy
from types import SimpleNamespace
import unittest

from tools.benchmark_campaign_resident_routes import POSITIONS,RouteConfig,native_probe_runner,finalize


class RouteDiagnosticPoolHarnessTests(unittest.TestCase):
    def test_default_serial_has_no_pool_construction_or_pool_keyword(self):
        calls=[]
        def execute(*args,**kwargs):calls.append((args,kwargs));return SimpleNamespace(worker_count=1)
        native=SimpleNamespace(benchmark_campaign_route_oracle=execute)
        probe,telemetry=native_probe_runner(RouteConfig(),native)
        self.assertIs(probe,execute)
        probe("context",["env"],["request"])
        self.assertEqual(calls[0][1],{});self.assertEqual(telemetry["kind"],"serial_direct")
        self.assertEqual(telemetry["workers"],1);self.assertEqual(telemetry["startup_seconds"],0)

    def test_one_explicit_pool_is_reused_and_startup_is_separate(self):
        created=[];calls=[]
        class Pool:
            def __init__(self,workers):self.workers=workers;self.startup_seconds=.125;created.append(self)
        def execute(*args,**kwargs):calls.append(kwargs["pool"]);return SimpleNamespace(worker_count=kwargs["pool"].workers)
        native=SimpleNamespace(CampaignDiagnosticPool=Pool,benchmark_campaign_route_oracle=execute)
        probe,telemetry=native_probe_runner(RouteConfig(native_workers=10),native)
        self.assertEqual(len(created),1);self.assertEqual(calls,[])
        for _ in range(3):self.assertEqual(probe("context",["env"],["request"]).worker_count,10)
        self.assertTrue(all(item is created[0] for item in calls));self.assertEqual(len(created),1)
        self.assertEqual(telemetry["workers"],10);self.assertEqual(telemetry["startup_seconds"],.125)
        self.assertGreaterEqual(telemetry["constructor_wall_seconds"],0)
        self.assertIn("production CPU",telemetry["scope"])

    def test_worker_bounds_and_missing_pool_never_fall_back(self):
        for count in (0,11,True,1.5):
            with self.assertRaises(ValueError):RouteConfig(native_workers=count)
        with self.assertRaises(ValueError):RouteConfig(native_workers=4,cpu_budget=5)
        native=SimpleNamespace(benchmark_campaign_route_oracle=lambda *args:None)
        with self.assertRaisesRegex(ValueError,"no serial fallback"):native_probe_runner(RouteConfig(native_workers=2),native)

    def test_installed_native_pool_api_is_used_without_changing_results_or_rng(self):
        import gwrl_cpp
        from studies.campaign.curriculum import make_env
        raw=make_env(1951,calendar_rounds=3).raw;before=raw.serialize()
        context=gwrl_cpp.campaign_movement_context(raw)
        queries=[gwrl_cpp.CampaignMovementQuery(i,"unknown-unit",["unknown","elsewhere"]) for i in (0,1)]
        probe,telemetry=native_probe_runner(RouteConfig(native_workers=2),gwrl_cpp)
        expected=gwrl_cpp.benchmark_campaign_route_oracle(context,[raw,raw],queries)
        for _ in range(2):
            result=probe(context,[raw,raw],queries)
            self.assertEqual(result.worker_count,2);self.assertEqual(result.inspect(),expected.inspect())
        self.assertEqual(telemetry["workers"],2);self.assertEqual(raw.serialize(),before)

    def test_parallel_reports_require_actual_worker_count_and_pool_evidence(self):
        config=RouteConfig(native_workers=10,batch_sizes=(4,),repeats=1)
        cases=[{"position":position,"lanes":4,"queries_per_lane":3,"queries":12,"seed":config.seed,
                "request_sha256":"1"*64,"one_lane_requests_sha256":"2"*64,"native_checkpoint_sha256":"3"*64,
                "evidence":{"exact":True,"verified_queries":12},"resident_source_evidence":{"exact":True,"verified_lanes":4},
                "native_source_witnesses":{"full_native_state_and_all_rng_exact":True},"source_unchanged":True,
                "native_query_seconds":[.1],"native_wrapper_wall_seconds":[.12],"gpu_prepare_query_seconds":[.2],"gpu_prepared_query_seconds":[.02],
                "native_worker_count":10} for position in POSITIONS]
        valid={"status":"completed","sources_unchanged":True,"preparation_completed_three_round_games":1,"cases":cases,
               "workload_sha256":"4"*64,"terminal_checkpoint_sha256":"5"*64,
               "native_pool":{"kind":"persistent_diagnostic_pool","workers":10,"startup_seconds":.125}}
        self.assertTrue(finalize(copy.deepcopy(valid),config)["matched_complete_route_queries_and_sources"])
        for mutation in (lambda r:r.pop("native_pool"),lambda r:r["cases"][0].pop("native_worker_count"),
                         lambda r:r["native_pool"].update(workers=1),lambda r:r["native_pool"].update(startup_seconds=float("nan"))):
            bad=copy.deepcopy(valid);mutation(bad)
            self.assertFalse(finalize(bad,config)["matched_complete_route_queries_and_sources"])


if __name__=="__main__":unittest.main()
