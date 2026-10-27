"""Native route timing keeps conversion outside its original-rules timer."""
import json
from pathlib import Path
import unittest
import gwrl_cpp

SCENARIO=Path(__file__).resolve().parents[1]/'game_content/scenarios/japan_china_1936'


class NativeRouteProbeTests(unittest.TestCase):
    def test_exact_result_order_and_source_identity(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),1951);before=env.serialize()
        context=gwrl_cpp.campaign_movement_context(env)
        unit=next(iter(json.loads(before)['state']['units'].values()))
        queries=[gwrl_cpp.CampaignMovementQuery(0,unit['id'],[unit['zone']]),
                 gwrl_cpp.CampaignMovementQuery(1,'missing-unit',[],mode='strategic_rail')]
        envs=[env,env]  # Duplicate references must acquire only one native lock.
        expected=gwrl_cpp.campaign_route_oracle(context,envs,queries)
        result=gwrl_cpp.benchmark_campaign_route_oracle(context,envs,queries,repeats=3)
        self.assertEqual(result.query_count,2);self.assertEqual(result.calls,6)
        self.assertGreaterEqual(result.seconds,0)
        self.assertEqual(result.inspect(),expected)
        self.assertEqual(result.inspect(),expected)
        self.assertEqual(env.serialize(),before)

    def test_invalid_or_empty_workload_keeps_complete_source(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),1951);before=env.serialize()
        context=gwrl_cpp.campaign_movement_context(env)
        empty=gwrl_cpp.benchmark_campaign_route_oracle(context,[env],[],repeats=1)
        self.assertEqual((empty.query_count,empty.calls,empty.inspect()),(0,0,[]))
        q=gwrl_cpp.CampaignMovementQuery(1,'missing',[])
        with self.assertRaises(ValueError):gwrl_cpp.benchmark_campaign_route_oracle(context,[env],[q])
        with self.assertRaises(ValueError):gwrl_cpp.benchmark_campaign_route_oracle(context,[env],[],repeats=0)
        self.assertEqual(env.serialize(),before)
