"""Persistent CPU probe workers preserve full route results and source state."""
from concurrent.futures import ThreadPoolExecutor
import gc
import json
from pathlib import Path
import unittest

import gwrl_cpp

SCENARIO = Path(__file__).resolve().parents[1] / "game_content/scenarios/japan_china_1936"


class NativeDiagnosticPoolTests(unittest.TestCase):
    def fixture(self):
        raw = gwrl_cpp.CampaignEnv(str(SCENARIO), 41)
        document = json.loads(raw.serialize())
        document["state"]["clock"].update(nation_index=2, player_turn_serial="2", phase="combat_movement")
        document["state"]["completed_turns"].update(ccp=1, mongolia=1)
        raw.restore(json.dumps(document))
        context = gwrl_cpp.campaign_movement_context(raw)
        envs = [raw, raw.clone(), raw.clone()]
        units = list(document["state"]["units"].items())[:8]
        queries = []
        for lane in range(3):
            for unit, value in units:
                for target in tuple(context.zones)[:8]:
                    queries.append(gwrl_cpp.CampaignMovementQuery(lane, unit, [value["zone"], target], "ordinary", True))
            queries.append(gwrl_cpp.CampaignMovementQuery(lane, "missing-unit", [], "blitz", True))
        return envs, context, queries

    def test_worker_bounds_empty_requests_and_default_serial_contract(self):
        for count in (0, 11, 128):
            with self.subTest(count=count), self.assertRaises(ValueError):gwrl_cpp.CampaignDiagnosticPool(count)
        envs, context, _ = self.fixture()
        serial = gwrl_cpp.benchmark_campaign_route_oracle(context, envs, [])
        self.assertEqual((serial.worker_count, serial.calls, serial.query_count), (1, 0, 0))
        pool = gwrl_cpp.CampaignDiagnosticPool(10)
        self.assertEqual(pool.workers, 10);self.assertGreaterEqual(pool.startup_seconds, 0.)
        parallel = gwrl_cpp.benchmark_campaign_route_oracle(context, envs, [], pool=pool)
        self.assertEqual((parallel.worker_count, parallel.calls, parallel.inspect()), (10, 0, []))

    def test_parallel_results_order_errors_and_all_source_bytes_match_native(self):
        envs, context, queries = self.fixture()
        source = [env.serialize() for env in envs]
        expected = gwrl_cpp.campaign_route_oracle(context, envs, queries)
        for count in (1, 2, 10):
            pool = gwrl_cpp.CampaignDiagnosticPool(count)
            for _ in range(3):
                result = gwrl_cpp.benchmark_campaign_route_oracle(context, envs, queries, repeats=2, pool=pool)
                self.assertEqual(result.inspect(), expected)
                self.assertEqual((result.worker_count, result.calls, result.query_count), (count, 2*len(queries), len(queries)))
                self.assertGreaterEqual(result.seconds, 0.)
            del pool;gc.collect()
        self.assertEqual([env.serialize() for env in envs], source)

    def test_shared_owner_lanes_and_concurrent_pool_callers_remain_read_only(self):
        envs, context, queries = self.fixture()
        envs = [envs[0]] * 3
        source = envs[0].serialize()
        expected = gwrl_cpp.campaign_route_oracle(context, envs, queries)
        pool = gwrl_cpp.CampaignDiagnosticPool(3)
        def compute(_):
            return gwrl_cpp.benchmark_campaign_route_oracle(context, envs, queries, pool=pool).inspect()
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(compute, i) for i in range(6)]
            for future in futures:self.assertEqual(future.result(timeout=15), expected)
        self.assertEqual(envs[0].serialize(), source)

    def test_input_failures_do_not_poison_pool_or_leave_owners_locked(self):
        envs, context, queries = self.fixture()
        pool = gwrl_cpp.CampaignDiagnosticPool(2)
        bad = [gwrl_cpp.CampaignMovementQuery(3, "bad", [], "ordinary", True)]
        with self.assertRaises(ValueError):gwrl_cpp.benchmark_campaign_route_oracle(context, envs, bad, pool=pool)
        with self.assertRaises(ValueError):gwrl_cpp.benchmark_campaign_route_oracle(context, envs, queries, repeats=0, pool=pool)
        expected = gwrl_cpp.campaign_route_oracle(context, envs, queries)
        self.assertEqual(gwrl_cpp.benchmark_campaign_route_oracle(context, envs, queries, pool=pool).inspect(), expected)

    def test_worker_exception_propagates_and_pool_recovers_without_source_mutation(self):
        envs, _, _ = self.fixture();raw = envs[0]
        document = json.loads(raw.serialize());state = document["state"]
        state["clock"]["phase"] = "place_units"
        minor = next(name for name in state["nations"] if name.startswith("warlord_"))
        state["nations"][minor].update(controller_nation="japan", player=None, power_status="minor")
        raw.restore(json.dumps(document))
        raw.apply_action(next(action for action in raw.legal_actions()
            if action.kind=="recruitment_roll" and action.parameters["beneficiary"]==minor))
        context = gwrl_cpp.device_state_context(raw);source = raw.serialize()
        pool = gwrl_cpp.CampaignDiagnosticPool(2)
        with self.assertRaisesRegex(RuntimeError, "Stale recruitment benchmark Engine key"):
            gwrl_cpp.campaign_recruitment_chance_benchmark(context, [raw], ["0"*64], 1, pool=pool)
        result = gwrl_cpp.campaign_recruitment_chance_benchmark(context, [raw], [raw.planning_key()], 1, pool=pool)
        self.assertTrue(result["source_unchanged"]);self.assertEqual(result["workers"], 2)
        self.assertEqual(raw.serialize(), source)


if __name__ == "__main__":
    unittest.main()
