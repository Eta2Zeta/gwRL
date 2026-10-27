"""The guarded hash probe reports only complete, exactly matched workloads."""
import copy
import hashlib
import time
import unittest

from tools.benchmark_campaign_content_digests import DigestConfig, ROLES, SCHEMA, finalize, identity_messages, selected_messages


class DigestBenchmarkTests(unittest.TestCase):
    def test_config_keeps_both_implementations_and_all_requested_messages(self):
        config = DigestConfig(batch_sizes=(1, 4, 16, 64), group_sizes=(None, 1, 4, 32))
        self.assertEqual(config.implementations, ("reference", "unrolled"))
        self.assertEqual(config.batch_sizes, (1, 4, 16, 64))
        self.assertEqual(config.group_sizes, (None, 1, 4, 32))
        self.assertEqual(config.message_kinds, ("state",))
        for values in ({"implementations": ()}, {"implementations": ("unknown",)},
                       {"implementations": ("unrolled", "unrolled")}, {"group_sizes": ()},
                       {"group_sizes": (True,)}, {"group_sizes": (1.5,)}, {"group_sizes": (0,)},
                       {"group_sizes": (None, None)}, {"families": ("unknown",)}, {"devices": ("cpu",)},
                       {"message_kinds": ()}, {"message_kinds": ("state", "state")}, {"message_kinds": ("unknown",)}):
            with self.assertRaises(ValueError): DigestConfig(**values)

    def report(self):
        config = DigestConfig(batch_sizes=(1,), families=("small_success",), group_sizes=(None, 4), repeats=2)
        cases = []
        for role in ROLES:
            cases.append({"family": "small_success", "role": role, "lanes": 1, "source_unchanged": True,
                "native_hashlib_exact": True, "bytes_per_message": 60_000,
                "native_rule_seconds": [.01, .01], "native_wrapper_seconds": [.02, .02],
                "measurements": [{"implementation": mode, "group_size": group,
                    "all_output_words_hex_counts_errors_exact": True, "warm_dispatch_seconds": [.01, .01]}
                    for mode in config.implementations for group in config.group_sizes]})
        return config, {"schema": SCHEMA, "status": "completed", "sources_unchanged": True, "cases": cases}

    def test_finalizer_requires_every_role_mode_group_and_exact_output(self):
        config, report = self.report()
        self.assertTrue(finalize(copy.deepcopy(report), config)["matched_native_hashlib_and_gpu_exact"])
        for mutate in (lambda row: row["cases"].pop(),
                       lambda row: row.update(sources_unchanged=False),
                       lambda row: row["cases"][0].update(source_unchanged=False),
                       lambda row: row["cases"][0].update(native_hashlib_exact=False),
                       lambda row: row["cases"][0]["measurements"].pop(),
                       lambda row: row["cases"][0]["measurements"][0].update(group_size=2),
                       lambda row: row["cases"][0]["measurements"][0].update(all_output_words_hex_counts_errors_exact=False),
                       lambda row: row["cases"][0]["measurements"][0].update(warm_dispatch_seconds=[.01]),
                       lambda row: row["cases"][0]["measurements"][0].update(warm_dispatch_seconds=[float("nan"), .01])):
            bad = copy.deepcopy(report); mutate(bad)
            result = finalize(bad, config)
            self.assertFalse(result["matched_native_hashlib_and_gpu_exact"])
            self.assertEqual(result["status"], "incomplete_or_mismatch")

    def test_guard_failure_cannot_be_promoted_to_complete(self):
        config, report = self.report(); report["status"] = "memory_limit"
        self.assertFalse(finalize(report, config)["matched_native_hashlib_and_gpu_exact"])
        self.assertEqual(report["status"], "memory_limit")

    def test_explicit_outer_selection_preserves_exact_bytes_and_default_state_cases(self):
        rows = [{"family": "small_success", "role": "source_preflight", "message": b"state\x00\xff",
                 "outer_engine_message": b"outer\x00\xff", "native_checkpoint_sha256": "3" * 64}]
        original = copy.deepcopy(rows)
        state_only = selected_messages(rows, ("state",))
        self.assertEqual(len(state_only), 1); self.assertIs(state_only[0]["message"], rows[0]["message"])
        both = selected_messages(rows, ("state", "outer_engine"))
        self.assertEqual([row["message_kind"] for row in both], ["state", "outer_engine"])
        self.assertIs(both[1]["message"], rows[0]["outer_engine_message"])
        self.assertEqual(rows, original)
        with self.assertRaisesRegex(ValueError, "message kinds"): selected_messages(rows, ("unknown",))

    def test_both_message_kinds_require_the_complete_independent_grid(self):
        original_config, report = self.report()
        config = DigestConfig(batch_sizes=(1,), families=("small_success",), group_sizes=(None, 4), repeats=2,
                              message_kinds=("state", "outer_engine"))
        self.assertFalse(finalize(copy.deepcopy(report), config)["matched_native_hashlib_and_gpu_exact"])
        expanded = copy.deepcopy(report)
        expanded["cases"] += [{**copy.deepcopy(row), "message_kind": "outer_engine", "bytes_per_message": 112}
                               for row in report["cases"]]
        self.assertTrue(finalize(copy.deepcopy(expanded), config)["matched_native_hashlib_and_gpu_exact"])
        expanded["cases"][-1]["message_kind"] = "state"
        self.assertFalse(finalize(expanded, config)["matched_native_hashlib_and_gpu_exact"])

    def test_real_native_identity_fixture_roles_retain_full_state_and_engine_messages(self):
        config = DigestConfig(batch_sizes=(1,), families=("small_success", "infrastructure_success"))
        rows = identity_messages(config, time.monotonic() + 30)
        self.assertEqual([(row["family"], row["role"]) for row in rows],
            [(family, role) for family in config.families for role in ROLES])
        self.assertTrue(all(len(row["message"]) > 50_000 for row in rows))
        for row in rows:
            self.assertEqual(hashlib.sha256(row["message"]).hexdigest(), row["state_key"])
            self.assertEqual(hashlib.sha256(row["outer_engine_message"]).hexdigest(), row["engine_key"])
            self.assertEqual(len(row["native_checkpoint_sha256"]), 64)
            self.assertTrue(row["draw_evidence"]["success"])


if __name__ == "__main__": unittest.main()
