import copy
import unittest
from tools.benchmark_campaign_resident_queries import QueryConfig,finalize,POSITIONS


class QueryBenchmarkContractTests(unittest.TestCase):
    def test_resource_and_explicit_device_limits(self):
        self.assertEqual(QueryConfig().devices,('mps',))
        for kwargs in ({'devices':('cpu',)},{'threads':12},{'memory_bytes':30_000_000_001},
                       {'seconds':181},{'batch_sizes':(4,4)}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):QueryConfig(**kwargs)

    def test_incomplete_or_duplicate_workloads_cannot_claim_exact_comparison(self):
        config=QueryConfig(batch_sizes=(4,),repeats=1)
        rows=[dict(position=p,lanes=4,evidence={'exact':True},source_unchanged=True,
                   native_query_seconds=[.1],gpu_query_seconds=[.2]) for p in POSITIONS]
        valid=dict(status='completed',sources_unchanged=True,cases=rows)
        self.assertTrue(finalize(copy.deepcopy(valid),config)['matched_complete_queries'])
        invalids=[]
        value=copy.deepcopy(valid);value['cases'].pop();invalids.append(value)
        value=copy.deepcopy(valid);value['cases'][-1]=value['cases'][0];invalids.append(value)
        value=copy.deepcopy(valid);value['cases'][0]['evidence']['exact']=False;invalids.append(value)
        value=copy.deepcopy(valid);value['cases'][0]['gpu_query_seconds']=[];invalids.append(value)
        value=copy.deepcopy(valid);value['sources_unchanged']=False;invalids.append(value)
        for value in invalids:
            self.assertEqual(finalize(value,config)['status'],'incomplete_or_mismatch')
            self.assertFalse(value['matched_complete_queries'])
