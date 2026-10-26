"""CPU oracle preparation for exact resident event-history commits."""
import json
from pathlib import Path
import unittest
import gwrl_cpp

SCENARIO=Path(__file__).resolve().parents[1]/'game_content/scenarios/japan_china_1936'


class NativeEventAppendProbeTests(unittest.TestCase):
    def test_original_state_key_payload_and_complete_history(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),7,training_actions=True)
        before=env.serialize();state=json.loads(before)['state']
        key=gwrl_cpp.campaign_state_json_oracle([env])[0]['state_key']
        payload={'x':[None,-0.0,1.0000000000000002,'蒙古\u0000'],'empty':{}}
        for kind in ('action','interrupt','chance'):
            result=gwrl_cpp.campaign_event_append_probe([env],[kind],[json.dumps(payload)])
            actual=json.loads(result[0]);expected=json.loads(before)['state']
            expected['history'].append(dict(kind=kind,payload=payload,after_state_key=key))
            self.assertEqual(actual,expected)
            self.assertEqual(env.serialize(),before)
        self.assertEqual(json.loads(before)['state'],state)

    def test_invalid_input_and_empty_batch_preserve_source(self):
        env=gwrl_cpp.CampaignEnv(str(SCENARIO),7);before=env.serialize()
        self.assertEqual(gwrl_cpp.campaign_event_append_probe([],[],[]),[])
        for kinds,payloads in (([],[]),(['unknown'],['{}']),(['action'],['not JSON'])):
            with self.subTest(kinds=kinds,payloads=payloads),self.assertRaises((ValueError,RuntimeError)):
                gwrl_cpp.campaign_event_append_probe([env],kinds,payloads)
            self.assertEqual(env.serialize(),before)
