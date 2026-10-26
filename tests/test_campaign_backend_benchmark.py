"""The backend scaffold measures actual wrapper calls and fails on lost parity."""
from __future__ import annotations

import copy
import errno
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.benchmark_campaign_backends import (Config, WorkloadLimit, compare_results, descriptor,
    numeric_digest, prepare, public_checkpoint, replay, run_case, sampled_step, supervise)


class BackendBenchmarkTests(unittest.TestCase):
    def test_configuration_rejects_unimplemented_backend_and_resource_overruns(self):
        for values in ({"backend": "cuda"}, {"backend": "metal"}, {"cpu_budget": 13},
                       {"cpu_budget": 2}, {"memory_bytes": 30_000_000_001},
                       {"warmups": 0}, {"seeds": (1, 1)}, {"seconds": float("inf")}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                Config(**values)

    def test_state_normalization_excludes_only_rng_and_preserves_full_history(self):
        raw = {"schema_version": 1, "rules_id": "rules", "state": {"history": [{"face": 3}]}, "random": {"next": 1}}
        value = {"schema": "scheduler", "raw": json.dumps(raw), "passed": ["axis"]}
        first = public_checkpoint(json.dumps(value))
        raw["random"] = {"next": 99}; value["raw"] = json.dumps(raw)
        self.assertEqual(first, public_checkpoint(json.dumps(value)))
        raw["state"]["history"][0]["face"] = 4; value["raw"] = json.dumps(raw)
        self.assertNotEqual(first, public_checkpoint(json.dumps(value)))

    def test_numeric_fingerprint_tracks_array_bits_shape_dtype_and_metadata(self):
        import numpy as np
        left = {"array": np.array([1, 2], dtype=np.int64), "references": ((0, "a"),)}
        self.assertEqual(numeric_digest(left), numeric_digest(copy.deepcopy(left)))
        for changed in ({**left, "array": np.array([1, 3], dtype=np.int64)},
                        {**left, "array": np.array([1, 2], dtype=np.int32)},
                        {**left, "array": left["array"].reshape(1, 2)},
                        {**left, "references": ((0, "b"),)}):
            self.assertNotEqual(numeric_digest(left), numeric_digest(changed))

    def test_empty_or_changed_measurements_never_establish_matched_throughput(self):
        self.assertFalse(compare_results({}, {})["matched"])
        good = {"lanes": [{"trace_sha256": "a", "numeric_input_sha256": ["b"]}], "completed_three_round_games": 0}
        self.assertTrue(compare_results(good, copy.deepcopy(good))["matched"])
        bad = copy.deepcopy(good); bad["lanes"][0]["numeric_input_sha256"] = ["c"]
        self.assertFalse(compare_results(good, bad)["matched"])

    @staticmethod
    def _one_step(*, chance=False):
        from studies.campaign.curriculum import make_env
        env = make_env(1951, calendar_rounds=3)
        for _ in range(64):
            if not chance or env.decision_kind() == "chance":
                initial = env.serialize(); row = sampled_step(env)
                return {"seed": 1951, "initial": initial, "steps": [row]}
            sampled_step(env)
        raise AssertionError("Real opening never reached its expected chance request")

    def test_actual_cpu_wrapper_is_used_and_opening_numerical_state_matches(self):
        from studies.campaign.backends import CPUBatchBackend
        calls = {"decision": 0, "numeric": 0, "apply": 0}
        class Counted(CPUBatchBackend):
            def decision_batch(self, lanes=None):
                calls["decision"] += 1; return super().decision_batch(lanes)
            def numeric_inputs(self, batch, buckets=2048):
                calls["numeric"] += 1; return super().numeric_inputs(batch, buckets)
            def apply_actions(self, batch, selections):
                calls["apply"] += 1; return super().apply_actions(batch, selections)
        case = self._one_step()
        reference = replay(Config(repetitions=1), [case], wrapped=False, whole_games=False)
        with patch("studies.campaign.backends.create_backend", side_effect=lambda envs, backend: Counted(envs)):
            actual = replay(Config(repetitions=1), [case], wrapped=True, whole_games=False)
        self.assertTrue(compare_results(reference, actual)["matched"])
        self.assertTrue(all(value > 0 for value in calls.values()))
        self.assertEqual(actual["completed_three_round_games"], 0)
        self.assertIsNone(actual["completed_rules_replay_games_per_hour"])

    def test_actual_chance_request_and_faces_are_checked_and_replay_preserves_rng(self):
        from studies.campaign.backends import create_backend
        case = self._one_step(chance=True)
        reference = replay(Config(repetitions=1), [case], wrapped=False, whole_games=False)
        captured = []
        def factory(envs, backend):
            value = create_backend(envs, backend=backend); captured.append(value); return value
        with patch("studies.campaign.backends.create_backend", side_effect=factory):
            actual = replay(Config(repetitions=1), [case], wrapped=True, whole_games=False)
        self.assertTrue(compare_results(reference, actual)["matched"])
        self.assertTrue(reference["lanes"][0]["execution_rng_unchanged"])
        self.assertTrue(actual["lanes"][0]["execution_rng_unchanged"])
        before = json.loads(json.loads(case["initial"])["raw"])["random"]
        self.assertEqual(before, json.loads(json.loads(captured[0].inspect_states()[0])["raw"])["random"])
        altered = copy.deepcopy(case); altered["steps"][0]["chance_request"]["purpose"] = "wrong distribution"
        with self.assertRaisesRegex(ValueError, "request metadata"):
            replay(Config(repetitions=1), [altered], wrapped=True, whole_games=False)

    def test_rng_only_fault_is_rejected_for_plain_and_wrapped_replay(self):
        from tools.benchmark_campaign_backends import PlainDriver, WrappedDriver
        case = self._one_step(chance=True)
        for wrapped, driver_type in ((False, PlainDriver), (True, WrappedDriver)):
            with self.subTest(wrapped=wrapped):
                original = driver_type.chance
                def corrupt(driver, lanes, batch, rows):
                    original(driver, lanes, batch, rows)
                    for lane in lanes:
                        env = driver.scalar(lane)
                        before = env.serialize()
                        value = json.loads(before); raw = json.loads(value["raw"])
                        raw["random"]["active"] = "training" if raw["random"]["active"] != "training" else "actual"
                        value["raw"] = json.dumps(raw)
                        changed = json.dumps(value)
                        self.assertEqual(public_checkpoint(before), public_checkpoint(changed))
                        env.restore(changed)
                with patch.object(driver_type, "chance", corrupt), self.assertRaisesRegex(
                        ValueError, "changed execution RNG"):
                    replay(Config(repetitions=1), [case], wrapped=wrapped, whole_games=False)

    def test_preparation_cap_is_truncation_and_never_shortens_the_game_horizon(self):
        with self.assertRaises(WorkloadLimit):
            prepare(Config(max_transitions=1))
        with tempfile.TemporaryDirectory() as directory, patch("tools.benchmark_campaign_backends.provenance", return_value={
                key: "fixed" for key in ("commit", "runtime_source_sha256", "backend_source_sha256", "harness_sha256", "native_sha256")}):
            report = run_case(Config(max_transitions=1), Path(directory) / "report.json", Path(directory) / "workload.json")
        self.assertEqual(report["status"], "truncated")
        self.assertEqual(report["measurements"], [])

    def test_guard_counts_supervisor_tree_and_fails_closed_on_monitor_errors(self):
        class Process:
            pid = 4242
            returncode = None
            def poll(self): return self.returncode
            def wait(self, timeout): return self.returncode
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as directory:
                process = Process(); sampled = []
                def sampler(pid):
                    sampled.append(pid)
                    if fail: raise OSError(errno.EPERM, "monitor denied")
                    return 1_500_000_000
                def kill(*_): process.returncode = -9
                with patch("tools.benchmark_campaign_backends.subprocess.Popen", return_value=process), \
                     patch("tools.benchmark_campaign_backends.os.killpg", side_effect=kill):
                    result = supervise(Config(memory_bytes=2_000_000_000), Path(directory) / "out.json", sampler=sampler)
                self.assertEqual(sampled, [4242])
                self.assertEqual(result["status"], "memory_monitor_failure" if fail else "memory_limit")
                self.assertFalse(result["complete_matched_throughput_claim_valid"])
                self.assertEqual(result["watchdog"]["reserved_processes"], 3)

    def test_guard_preserves_intentional_truncation_exit(self):
        class Process:
            pid, returncode = 4242, 2
            def poll(self): return self.returncode
            def wait(self, timeout): return self.returncode
        def launch(command, **_):
            progress = Path(command[command.index("--output") + 1])
            progress.write_text(json.dumps({"schema": "campaign-backend-benchmark-v1", "status": "truncated",
                                           "stop_reason": "preparation_transition_or_repetition_limit"}))
            return Process()
        with tempfile.TemporaryDirectory() as directory, patch(
                "tools.benchmark_campaign_backends.subprocess.Popen", side_effect=launch):
            result = supervise(Config(), Path(directory) / "out.json", sampler=lambda _: 0)
        self.assertEqual(result["status"], "truncated")
        self.assertFalse(result["complete_matched_throughput_claim_valid"])
        self.assertEqual(result["watchdog"]["worker_returncode"], 2)


if __name__ == "__main__":
    unittest.main()
