"""Indexed presence scheduling reuses all original oracle and boundary cases."""
from dataclasses import replace
import json
import unittest

import gwrl_cpp
import torch

import tests.test_campaign_fused_route_preparation as base
from studies.campaign.backends.device_state import DeviceStateBatch


class IndexedRouteOracleTests(base.FusedRouteOracleTests):
    strategy="fused_indexed"


class IndexedPoliticalOracleTests(base.FusedPoliticalOracleTests):
    strategy="fused_indexed"


class IndexedDeclarationOracleTests(base.FusedDeclarationOracleTests):
    strategy="fused_indexed"


class IndexedPreparationBoundaryTests(base.FusedPreparationBoundaryTests):
    strategy="fused_indexed"

    def test_history_and_unused_suffix_capacity_preserve_every_presence_result(self):
        state,routes=self.setup()
        original=routes.prepare(state,implementation="reference")
        # Capacity is allocation, not the active string-ID range. Huge unused
        # sentinels must never turn into extra units or changing home presence.
        offsets=torch.full((state.string_offsets.numel()+4096,),-9223372036854775807,dtype=torch.int64,device=state.device)
        offsets[:state.string_offsets.numel()]=state.string_offsets
        padded=replace(state,string_offsets=offsets)
        expected=routes.prepare(padded,implementation="reference")
        actual=routes.prepare(padded,implementation=self.strategy);self.prepared_equal(actual,expected)
        for name in base.RELATION_FIELDS:self.assertTrue(torch.equal(getattr(original.relations,name),getattr(actual.relations,name)),name)
        for name in base.DECLARATION_FIELDS:self.assertTrue(torch.equal(getattr(original.declarations,name),getattr(actual.declarations,name)),name)
        raw=state.fork(torch.tensor([0],dtype=torch.int64,device=state.device)).restore_envs()[0]
        document=json.loads(raw.serialize())
        document["state"]["history"].append({"kind":"read_only_presence_history_probe","after_state_key":raw.planning_key(),"payload":
            {"history_strings":["presence-history-"+str(i) for i in range(1024)]}})
        raw.restore(json.dumps(document))
        historic=DeviceStateBatch.capture([raw],context=state.context)
        expected=routes.prepare(historic,implementation="reference")
        actual=routes.prepare(historic,implementation=self.strategy);self.prepared_equal(actual,expected)
        for name in base.RELATION_FIELDS:self.assertTrue(torch.equal(getattr(original.relations,name)[:1],getattr(actual.relations,name)),name)
        for name in base.DECLARATION_FIELDS:self.assertTrue(torch.equal(getattr(original.declarations,name)[:1],getattr(actual.declarations,name)),name)

    def test_invalid_unit_owner_zone_and_map_cardinality_use_exact_serial_gpu_diagnostics(self):
        state,routes=self.setup();rows=state.records[0].cpu().tolist()
        unit_map=int(state.section("state.units")[0]);cursor=unit_map+1
        first=rows[cursor][4];second_key=rows[first][4]
        self.assertLess(second_key,rows[unit_map][4])
        def child(root,index):
            value=root+1
            for _ in range(index):value=rows[value][4]
            return value
        # Valid arena string IDs which are not national/zone names respectively.
        invalid_name=int(state.context.prefix_lookup_ids(("infantry",))[0])
        cases=[]
        for field in (2,3):
            records=state.records.clone();records[0,child(first,field),1]=invalid_name
            cases.append(replace(state,records=records))
        # Duplicate keys overwrite a dense index; cardinality validation must
        # detect this and preserve the full reference's ordered diagnostics.
        records=state.records.clone();records[0,second_key,1]=records[0,cursor,1]
        records[0,child(first,2),1]=int(state.context.prefix_lookup_ids(("dadao",))[0])
        cases.append(replace(state,records=records))
        land=int(state.section("state.territories")[0])
        records=state.records.clone();records[0,land+1,1]=invalid_name
        cases.append(replace(state,records=records))
        records=state.records.clone();records[0,unit_map,1]+=1
        cases.append(replace(state,records=records))
        for invalid in cases:
            with self.subTest():
                expected=routes.prepare(invalid,implementation="reference")
                actual=routes.prepare(invalid,implementation=self.strategy);self.prepared_equal(actual,expected)


class IndexedSourceContractTests(base.FusedPreparationSourceContractTests):
    pass


if __name__=="__main__":unittest.main()
