"""Fused allocation/scheduling retains native route/political/declaration oracles."""
from dataclasses import replace
import copy
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_routes import ResidentRoutes
from studies.campaign.backends.route_preparation import FusedRoutePreparation,build_source
from studies.campaign.backends.resident_declarations import ResidentLandAttackDeclarations
import tests.test_campaign_resident_routes as route_oracles
import tests.test_campaign_resident_relations as relation_oracles
import tests.test_campaign_resident_declarations as declaration_oracles

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()
RELATION_FIELDS=("pairs","pair_errors","nations","nation_errors","present","metadata")
DECLARATION_FIELDS=("allowed","errors","presence")


class _BoundedMPS:
    @classmethod
    def setUpClass(cls):
        cls.previous_threads=torch.get_num_threads()
        super().setUpClass()
        torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass();torch.mps.empty_cache();torch.set_num_threads(cls.previous_threads)


class _PreparedAssertions:
    def prepared_equal(self,a,b):
        self.assertIs(a.source,b.source)
        self.assertIs(a.relations.source,a.source)
        self.assertIs(a.declarations.source,a.source)
        self.assertIs(a.declarations.relations,a.relations)
        for name in RELATION_FIELDS:self.assertTrue(torch.equal(getattr(a.relations,name),getattr(b.relations,name)),name)
        for name in DECLARATION_FIELDS:self.assertTrue(torch.equal(getattr(a.declarations,name),getattr(b.declarations,name)),name)
        self.assertTrue(torch.equal(a.indexes,b.indexes),"indexes")

    def instrument_relations(self,envs,state,relations):
        """Every original political test still runs its native reference checks.

        Additionally compare every fused table/index with the exact same-source
        reference preparation. Construction is outside the hot no-host witness.
        """
        routes=ResidentRoutes(state.context,gwrl_cpp.campaign_movement_context(envs[0]),relations_context=relations)
        original=relations.compute
        def audited(source,*args,**kwargs):
            expected=original(source,*args,**kwargs)
            fused=routes.prepare(source,implementation="fused")
            declaration=routes.declaration_context.compute(source,expected)
            reference=routes.prepare(source,relations=expected,declarations=declaration,implementation="reference")
            self.prepared_equal(fused,reference)
            return expected
        relations.compute=audited
        return routes


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class FusedRouteOracleTests(_BoundedMPS,route_oracles.CampaignResidentRoutesTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.kernel=ResidentRoutes(cls.context,cls.native,preparation_implementation="fused")


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class FusedPoliticalOracleTests(_BoundedMPS,_PreparedAssertions,relation_oracles.ResidentRelationsTests):
    def setup_batch(self,envs):
        state,relations,native=super().setup_batch(envs)
        self.instrument_relations(envs,state,relations)
        return state,relations,native


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class FusedDeclarationOracleTests(_BoundedMPS,_PreparedAssertions,declaration_oracles.ResidentDeclarationTests):
    def setup_batch(self,envs):
        state,relations,declarations,native=super().setup_batch(envs)
        self.instrument_relations(envs,state,relations)
        return state,relations,declarations,native


@unittest.skipUnless(EXACT_MPS,"Lossless Apple GPU runtime unavailable")
class FusedPreparationBoundaryTests(_BoundedMPS,_PreparedAssertions,unittest.TestCase):
    def setup(self):
        from studies.campaign.curriculum import make_env
        raw=make_env(1951,calendar_rounds=3).raw
        context=DeviceStateContext(gwrl_cpp.device_state_context(raw),"mps")
        state=DeviceStateBatch.capture([raw,raw.clone(),raw.clone(),raw.clone()],context=context)
        routes=ResidentRoutes(context,gwrl_cpp.campaign_movement_context(raw))
        return state,routes

    def test_single_disjoint_contiguous_slab_complete_fields_and_small_groups(self):
        state,routes=self.setup();expected=routes.prepare(state,implementation="reference")
        preparer=FusedRoutePreparation(routes)
        for size in (1,7,128):
            actual=preparer.prepare(routes,state,group_size=size);self.prepared_equal(actual,expected)
            values=([getattr(actual.relations,name) for name in RELATION_FIELDS]+
                    [getattr(actual.declarations,name) for name in DECLARATION_FIELDS]+[actual.indexes])
            self.assertEqual(len({value.untyped_storage().data_ptr() for value in values}),1)
            spans=sorted((value.storage_offset(),value.storage_offset()+value.numel()) for value in values)
            self.assertTrue(all(left[1]<=right[0] for left,right in zip(spans,spans[1:])))
            self.assertTrue(all(value.is_contiguous() for value in values))
        for invalid in (0,True,1.5):
            with self.assertRaises(ValueError):preparer.prepare(routes,state,group_size=invalid)

    def test_source_wire_binding_empty_batches_cache_selection_and_caller_reuse(self):
        state,routes=self.setup()
        reference=routes.prepare(state,implementation="reference")
        fused=routes.prepare(state,implementation="fused")
        self.assertIsNot(reference,fused);self.prepared_equal(fused,reference)
        self.assertIs(routes.prepare(state,implementation="fused"),fused)
        reused=routes.prepare(state,relations=reference.relations,declarations=reference.declarations,implementation="fused")
        self.assertIs(reused.relations,reference.relations);self.assertIs(reused.declarations,reference.declarations)
        with self.assertRaises(ValueError):routes.prepare(state.snapshot(),relations=reference.relations,implementation="fused")
        with self.assertRaises(ValueError):routes.prepare(state,implementation="unknown")
        empty=DeviceStateBatch.capture([],context=state.context)
        self.prepared_equal(routes.prepare(empty,implementation="fused"),routes.prepare(empty,implementation="reference"))
        foreign=copy.copy(state.context);foreign.wire_context_fingerprint+="-foreign"
        with self.assertRaises(ValueError):routes.prepare(replace(state,context=foreign),implementation="fused")

    def test_injected_services_reject_foreign_wire_device_and_native_definition(self):
        state,routes=self.setup()
        for field,value in (("wire_context_fingerprint",state.context.wire_context_fingerprint+"-foreign"),("device",torch.device("cpu"))):
            context=copy.copy(state.context);setattr(context,field,value)
            service=copy.copy(routes.relations_context);service.state_context=context
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"Injected political service"):
                ResidentRoutes(state.context,routes.native_context,relations_context=service,preparation_implementation="fused")
        from studies.campaign.curriculum import make_env
        other=make_env(1951,calendar_rounds=11).raw
        service=copy.copy(routes.relations_context);service.native_context=gwrl_cpp.campaign_relations_context(other)
        with self.assertRaisesRegex(ValueError,"Injected political service"):
            ResidentRoutes(state.context,routes.native_context,relations_context=service,preparation_implementation="fused")
        matching=ResidentRoutes(state.context,routes.native_context,relations_context=routes.relations_context,preparation_implementation="fused")
        self.assertIs(matching.relations_context,routes.relations_context)

    def test_fused_preparer_cannot_rebind_to_foreign_static_route_context(self):
        state,routes=self.setup();preparer=FusedRoutePreparation(routes)
        other=ResidentRoutes(state.context,routes.native_context)
        with self.assertRaisesRegex(ValueError,"different static route context"):preparer.prepare(other,state)
        service=routes.relations_context;foreign=copy.copy(state.context);foreign.wire_context_fingerprint+="-foreign"
        previous=service.state_context
        try:
            service.state_context=foreign
            with self.assertRaisesRegex(ValueError,"exact wire context/device"):preparer.prepare(routes,state)
        finally:service.state_context=previous
        self.prepared_equal(preparer.prepare(routes,state),routes.prepare(state,implementation="reference"))

    def test_fused_hot_path_has_one_allocation_no_host_reads_or_reference_dispatch(self):
        state,routes=self.setup();expected=routes.prepare(state,implementation="reference")
        routes.prepare(state,implementation="fused");torch.mps.synchronize()
        original_empty=torch.empty;calls=[]
        def allocate(*args,**kwargs):calls.append(args);return original_empty(*args,**kwargs)
        fail=AssertionError("Host read or reference preparation dispatch forbidden")
        with patch.object(torch,"empty",side_effect=allocate),patch.object(torch.Tensor,"cpu",side_effect=fail),\
             patch.object(torch.Tensor,"item",side_effect=fail),patch.object(torch.Tensor,"tolist",side_effect=fail),\
             patch.object(torch.Tensor,"__bool__",side_effect=fail),patch.object(routes.relations_context,"compute",side_effect=fail),\
             patch.object(routes.declaration_context,"compute",side_effect=fail):
            actual=routes.prepare(replace(state),implementation="fused")
        self.assertEqual(len(calls),1,"One contiguous result allocation, without intermediate table allocations")
        reference=routes.prepare(actual.source,implementation="reference");self.prepared_equal(actual,reference)


class FusedPreparationSourceContractTests(unittest.TestCase):
    def test_audited_source_markers_and_explicit_strategy_are_checked(self):
        from studies.campaign.backends.resident_routes import SOURCE
        source=build_source(SOURCE)
        self.assertIn("kernel void fused_route_preparation",source)
        self.assertIn("inline void route_prepare_declarations",source)
        with self.assertRaises(RuntimeError):build_source(SOURCE.replace("kernel void prepare_route_indexes(","kernel void unexpected_indexes("))
        from studies.campaign.curriculum import make_env
        raw=make_env(17,calendar_rounds=3).raw
        context=DeviceStateContext(gwrl_cpp.device_state_context(raw),"cpu")
        with self.assertRaisesRegex(ValueError,"explicit Apple MPS"):
            ResidentRoutes(context,gwrl_cpp.campaign_movement_context(raw),preparation_implementation="fused")


if __name__=="__main__":unittest.main()
