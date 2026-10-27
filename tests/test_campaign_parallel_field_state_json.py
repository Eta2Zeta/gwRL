"""Independent fields retain every native byte and serial diagnostic result."""
from dataclasses import replace
import unittest

import torch

import tests.test_campaign_parallel_unit_state_json as units
from studies.campaign.backends.resident_state_json_fields import ParallelFieldStateJson


@unittest.skipUnless(units.baseline.EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class ParallelFieldStateJsonTests(units.ParallelUnitStateJsonTests):
    def setup_batch(self,envs):
        state,formatter=super().setup_batch(envs)
        return state,ParallelFieldStateJson(formatter.number_context)

    def test_errors_in_independent_early_middle_and_last_fields_preserve_all_partial_bytes(self):
        raw=units.gwrl_cpp.CampaignEnv(str(units.baseline.SCENARIO),19)
        state,formatter=self.setup_batch([raw]);rows=state.records[0].cpu().tolist()
        root=int(state.section("state")[0].cpu());field=root+1
        roots=[]
        for _ in range(19):roots.append(field);field=rows[field][4]
        for index in (0,7,8,10,11,17,18):
            data=state.records.clone();data[0,roots[index],0]=12345
            broken=replace(state,records=data)
            for capacity in (0,1,100,262144):
                with self.subTest(field=index,capacity=capacity):self.compare(broken,formatter,capacity)

    def test_explicit_threadgroups_preserve_complete_rich_bytes_and_capacity_diagnostics(self):
        raw=units.baseline.rich_fixture()
        state,formatter=self.setup_batch([raw,raw])
        for group in (1,4,32):
            chosen=ParallelFieldStateJson(formatter.number_context,fragment_group_size=group)
            for capacity in (0,17,262144):
                with self.subTest(group=group,capacity=capacity):self.compare(state,chosen,capacity)
        for group in (True,0,-1,1.5):
            with self.assertRaises(ValueError):ParallelFieldStateJson(formatter.number_context,fragment_group_size=group)


if __name__=="__main__":unittest.main()
