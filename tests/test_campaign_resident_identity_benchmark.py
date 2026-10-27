"""Standalone combinations keep complete native identity bytes and labels."""
import copy
import json
import time
import unittest
from unittest.mock import patch

from tools.benchmark_campaign_resident_identities import (
    DEFAULT_SERIALIZERS, DIGESTS, SERIALIZERS, IdentityConfig, ROLES, SCHEMA, STAGES, check_identity, digest_json, finalize, fixtures, identities,
)


class IdentityCombinationHarnessTests(unittest.TestCase):
    def test_configuration_keeps_all_requested_combinations_and_capacities(self):
        config = IdentityConfig()
        self.assertEqual(config.batch_sizes, (1, 4, 16, 64))
        self.assertEqual(config.serializers, DEFAULT_SERIALIZERS); self.assertEqual(config.digests, DIGESTS)
        self.assertEqual(config.field_group_size, 1)
        explicit = IdentityConfig(serializers=SERIALIZERS, field_group_size=32)
        self.assertEqual(explicit.serializers, ("reference", "parallel_units", "parallel_fields"))
        self.assertEqual(explicit.field_group_size, 32)
        self.assertIsNone(config.digest_group_size)
        for values in ({"serializers": ()}, {"serializers": ("bad",)}, {"digests": ("reference", "reference")},
                       {"digests": ()}, {"families": ("bad",)}, {"digest_group_size": True},
                       {"digest_group_size": 1.5}, {"digest_group_size": 0}, {"byte_capacity": 0},
                       {"byte_capacity": True}, {"devices": ("cpu",)}, {"field_group_size": True},
                       {"field_group_size": 0}, {"field_group_size": 1.5}):
            with self.assertRaises(ValueError): IdentityConfig(**values)

    def test_pipeline_uses_exact_four_operations_and_only_explicit_stage_fences(self):
        actions = []; fences = []; source = object()
        class Formatter:
            def serialize(self, state, *, byte_capacity): actions.append(("serialize", state, byte_capacity)); return "state"
            def outer_engine_json(self, keys): actions.append(("outer", keys)); return "outer"
            def identities(self, *args, **kwargs): raise AssertionError("Certificate/default shortcut")
        def digest(value, **kwargs): actions.append(("digest", value, kwargs)); return "key:" + value
        kwargs = {"byte_capacity": 123, "digest_implementation": "unrolled", "digest_group_size": 4}
        with patch("tools.benchmark_campaign_resident_identities.digest_json", side_effect=digest):
            ordinary = identities(Formatter(), source, **kwargs)
            self.assertEqual(fences, [])
            stages = {}; ticks = iter(range(5))
            sampled = identities(Formatter(), source, stages=stages, synchronize=lambda: fences.append(True), clock=lambda: next(ticks), **kwargs)
        expected = [("serialize", source, 123), ("digest", "state", {"implementation": "unrolled", "group_size": 4}),
                    ("outer", "key:state"), ("digest", "outer", {"implementation": "unrolled", "group_size": 4})]
        self.assertEqual(actions, expected * 2); self.assertEqual(len(fences), 5)
        self.assertEqual(stages, dict.fromkeys(STAGES, 1)); self.assertEqual(ordinary, sampled)
        with self.assertRaisesRegex(ValueError, "fence and clock"):
            identities(Formatter(), source, stages={}, **kwargs)

    def report(self):
        config = IdentityConfig(batch_sizes=(1,), families=("small_success",), repeats=2)
        cases = [{"family": "small_success", "role": role, "lanes": 1, "source_unchanged": True,
            "state_key": "1" * 64, "engine_key": "2" * 64, "native_checkpoint_sha256": "3" * 64, "message_bytes": 60_000,
            "measurements": [{"serializer": serializer, "digest": digest,
                "all_native_bytes_words_keys_counts_errors_and_padding_exact": True,
                "warm_pipeline_seconds": [.01, .01], "fenced_substage_seconds": [dict.fromkeys(STAGES, .001)] * 2}
                for serializer in config.serializers for digest in DIGESTS]} for role in ROLES]
        return config, {"schema": SCHEMA, "status": "completed", "sources_unchanged": True,
                        "source_identity_certificate_used": False, "cases": cases}

    def test_finalizer_needs_complete_roles_modes_stages_and_native_bytes(self):
        config, report = self.report()
        self.assertTrue(finalize(copy.deepcopy(report), config)["matched_complete_native_identity_pipeline"])
        for mutate in (lambda r: r["cases"].pop(), lambda r: r.update(sources_unchanged=False),
                       lambda r: r.update(source_identity_certificate_used=True),
                       lambda r: r["cases"][0].update(source_unchanged=False),
                       lambda r: r["cases"][0].update(state_key="bad"),
                       lambda r: r["cases"][0]["measurements"].pop(),
                       lambda r: r["cases"][0]["measurements"][0].update(serializer="bad"),
                       lambda r: r["cases"][0]["measurements"][0].update(all_native_bytes_words_keys_counts_errors_and_padding_exact=False),
                       lambda r: r["cases"][0]["measurements"][0].update(warm_pipeline_seconds=[.01]),
                       lambda r: r["cases"][0]["measurements"][0].update(fenced_substage_seconds=[dict.fromkeys(STAGES, .001)]),
                       lambda r: r["cases"][0]["measurements"][0].update(fenced_substage_seconds=[dict.fromkeys(STAGES, float("nan"))] * 2)):
            bad = copy.deepcopy(report); mutate(bad)
            self.assertFalse(finalize(bad, config)["matched_complete_native_identity_pipeline"])
        config = IdentityConfig(batch_sizes=(1, 4), families=("small_success",), repeats=2)
        changed = copy.deepcopy(report)
        changed["cases"] += [{**copy.deepcopy(row), "lanes": 4} for row in report["cases"]]
        self.assertTrue(finalize(copy.deepcopy(changed), config)["matched_complete_native_identity_pipeline"])
        changed["cases"][-1]["native_checkpoint_sha256"] = "4" * 64
        self.assertFalse(finalize(changed, config)["matched_complete_native_identity_pipeline"])
        field_config = IdentityConfig(batch_sizes=(1,), families=("small_success",), repeats=2, serializers=SERIALIZERS)
        fields = copy.deepcopy(report)
        for row in fields["cases"]:
            row["measurements"] += [{**copy.deepcopy(item), "serializer": "parallel_fields"}
                                    for item in row["measurements"] if item["serializer"] == "parallel_units"]
        fields["parallel_field_threadgroup_size"] = 1
        self.assertTrue(finalize(copy.deepcopy(fields), field_config)["matched_complete_native_identity_pipeline"])
        for mismatch in (None, 4, True, "1"):
            bad = copy.deepcopy(fields); bad["parallel_field_threadgroup_size"] = mismatch
            self.assertFalse(finalize(bad, field_config)["matched_complete_native_identity_pipeline"])
        unused = copy.deepcopy(report); unused["parallel_field_threadgroup_size"] = 1
        self.assertFalse(finalize(unused, IdentityConfig(batch_sizes=(1,), families=("small_success",), repeats=2))
                         ["matched_complete_native_identity_pipeline"])

    def test_guard_failure_stays_failed(self):
        config, report = self.report(); report["status"] = "memory_limit"
        self.assertFalse(finalize(report, config)["matched_complete_native_identity_pipeline"])
        self.assertEqual(report["status"], "memory_limit")


class IdentityCombinationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
        if not torch.backends.mps.is_available() or not mps_int64_indexing_supported():
            raise unittest.SkipTest("Lossless Apple GPU runtime unavailable")
        cls.old_threads = torch.get_num_threads(); torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000 / torch.mps.recommended_max_memory())

    @classmethod
    def tearDownClass(cls):
        import torch
        if hasattr(cls, "old_threads"): torch.set_num_threads(cls.old_threads)

    def test_digest_envelope_preserves_exact_ranges_counts_and_serialization_error_bits(self):
        import torch
        from studies.campaign.backends.canonical_json_metal import CanonicalJsonBatch, canonical_json_digests
        data = torch.tensor([list(b"abc\x00junk"), list(b"\x00xy\xffgap!")], dtype=torch.uint8, device="mps")
        for actual in (0, 1, 2, 3):
            encoded = CanonicalJsonBatch(data, torch.tensor([3, 4], dtype=torch.int64, device="mps"),
                torch.tensor([3, 4], dtype=torch.int64, device="mps"), torch.tensor([4, 8], dtype=torch.int32, device="mps"),
                torch.tensor([actual], dtype=torch.int64, device="mps"), torch.tensor([2], dtype=torch.int32, device="mps"))
            expected = canonical_json_digests(encoded)
            for implementation in DIGESTS:
                result = digest_json(encoded, implementation=implementation, group_size=4)
                for field in result.__dataclass_fields__:
                    self.assertTrue(torch.equal(getattr(result, field), getattr(expected, field)), field)

    def test_all_four_complete_pipelines_preserve_native_source_after_effects_and_no_host_reads(self):
        import torch, gwrl_cpp
        from studies.campaign.backends.device_state import DeviceStateBatch, DeviceStateContext
        from studies.campaign.backends.canonical_json_metal import CanonicalJsonContext
        from studies.campaign.backends.resident_state_json import ResidentStateJson
        from studies.campaign.backends.resident_state_json_parallel import ParallelUnitStateJson
        from studies.campaign.backends.resident_state_json_fields import ParallelFieldStateJson
        config = IdentityConfig(batch_sizes=(2,), families=("small_success",), repeats=1, serializers=SERIALIZERS, field_group_size=1)
        for row in fixtures(config, time.monotonic() + 30):
            raw = row["env"]; native = gwrl_cpp.capture_device_states(gwrl_cpp.device_state_context(raw), [raw, raw])
            context = DeviceStateContext(native.context, "mps")
            source = DeviceStateBatch.from_native(native, context=context); before = source.records.clone()
            numbers = CanonicalJsonContext(native, context)
            baseline = ResidentStateJson(numbers); expected = baseline.identities(source, byte_capacity=config.byte_capacity)
            for formatter in (baseline, ParallelUnitStateJson(numbers),
                              ParallelFieldStateJson(numbers, fragment_group_size=config.field_group_size)):
                for implementation in DIGESTS:
                    with patch.object(torch.Tensor, "cpu", side_effect=AssertionError("Hot host read")), \
                         patch.object(torch.Tensor, "tolist", side_effect=AssertionError("Hot host list")), \
                         patch.object(torch.Tensor, "item", side_effect=AssertionError("Hot host scalar")), \
                         patch.object(torch.Tensor, "__bool__", side_effect=AssertionError("Hot host truth")), \
                         patch.object(json, "loads", side_effect=AssertionError("Hot JSON")), \
                         patch.object(gwrl_cpp, "campaign_state_json_oracle", side_effect=AssertionError("CPU fallback")):
                        result = identities(formatter, source, byte_capacity=config.byte_capacity,
                            digest_implementation=implementation, digest_group_size=4)
                    check_identity(result, expected, row["native"], row["outer"], 2)
            self.assertTrue(torch.equal(source.records, before)); self.assertEqual(raw.serialize(), row["serialized"])


if __name__ == "__main__": unittest.main()
