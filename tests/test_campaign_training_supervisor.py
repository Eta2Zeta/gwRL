"""Durable supervisor behavior using tiny sleeping children, never real training."""
from __future__ import annotations

from dataclasses import replace
import ctypes
import errno
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.supervise_campaign_training import (
    SupervisorConfig, aggregate_rss, exclusive_lock, supervise, training_command,
    validate_training_arguments, process_group_alive,
    process_memory_charge, _darwin_physical_footprint, monitor_error_details,
)


ARGUMENTS = ["--threads", "1", "--parallel-envs", "1", "--cpu-budget", "3"]


class CampaignTrainingSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="campaign-supervisor-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.control, self.run = self.directory / "control", self.directory / "training"
        self.config = SupervisorConfig(seconds=2, cpu_budget=4, poll_seconds=0.02,
                                       shutdown_seconds=0.15, max_restarts=1)

    def factory(self, body):
        script = self.directory / "tiny_worker.py"
        script.write_text("import json, os, pathlib, signal, sys, time\n"
                          "run = pathlib.Path(sys.argv[1])\n"
                          "run.mkdir(parents=True, exist_ok=True)\n"
                          + body)

        def command(python, run_dir, arguments, resume, extension):
            return [python, str(script), str(run_dir), str(resume), str(extension)]
        return command

    def run_supervisor(self, body, **kwargs):
        return supervise(self.control, self.run, self.config, ARGUMENTS,
                         command_factory=self.factory(body), rss_sampler=lambda _pid: 1_000_000, **kwargs)

    def test_completion_is_durable_and_does_not_launch_again(self):
        state = self.run_supervisor("(run / 'manifest.json').write_text(json.dumps({'status':'completed'}))\n")
        self.assertEqual(state["status"], "completed")
        self.assertEqual(len(state["attempts"]), 1)
        self.assertLessEqual(state["charged_seconds"], self.config.seconds)
        again = self.run_supervisor("raise RuntimeError('must never run')\n")
        self.assertEqual(again, state)
        self.assertEqual(json.loads((self.control / "state.json").read_text()), state)

    def test_interrupted_active_games_resume_under_same_nonresetting_budget(self):
        body = ("def stop(number, frame):\n"
                "    (run / 'checkpoint.pt').write_text('unfinished games and optimizer')\n"
                "    (run / 'manifest.json').write_text(json.dumps({'status':'interrupted'}))\n"
                "    sys.exit(130)\n"
                "signal.signal(signal.SIGTERM, stop)\n"
                "while True: time.sleep(0.01)\n")
        state = self.run_supervisor(body)
        self.assertEqual(state["status"], "time_budget_exhausted")
        self.assertEqual(state["attempts"][0]["runner_status"], "interrupted")
        self.assertNotIn("forced_kill", state["attempts"][0])
        self.assertTrue((self.run / "checkpoint.pt").exists())
        charged = state["charged_seconds"]
        again = self.run_supervisor(body)
        self.assertEqual(len(again["attempts"]), 1)
        self.assertGreaterEqual(again["charged_seconds"], charged)

    def test_transient_error_retries_checkpoint_once_and_never_starts_fresh(self):
        body = ("marker = run / 'checkpoint.pt'\n"
                "if not marker.exists():\n"
                "    marker.write_text('saved unfinished game')\n"
                "    (run / 'manifest.json').write_text(json.dumps({'status':'running'}))\n"
                "    sys.exit(75)\n"
                "assert sys.argv[2] == str(marker)\n"
                "(run / 'manifest.json').write_text(json.dumps({'status':'completed'}))\n")
        state = self.run_supervisor(body)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["error_restarts"], 1)
        self.assertEqual([attempt["returncode"] for attempt in state["attempts"]], [75, 0])

    def test_source_mismatch_style_errors_stop_without_automatic_retry(self):
        state = self.run_supervisor("(run / 'checkpoint.pt').write_text('saved')\nraise ValueError('Runtime sources changed')\n")
        self.assertEqual(state["status"], "worker_error")
        self.assertEqual(state["error_restarts"], 0)
        self.assertEqual(len(state["attempts"]), 1)

    def test_retry_count_is_lifetime_bounded(self):
        body = "(run / 'checkpoint.pt').write_text('saved')\nsys.exit(75)\n"
        state = self.run_supervisor(body)
        self.assertEqual(state["status"], "worker_error")
        self.assertEqual(len(state["attempts"]), 2)
        self.assertEqual(state["error_restarts"], 1)
        again = self.run_supervisor(body)
        self.assertEqual(len(again["attempts"]), 3)
        self.assertEqual(again["error_restarts"], 1)

    def test_episode_guard_needs_explicit_monotonic_runner_extension(self):
        state = self.run_supervisor("(run / 'checkpoint.pt').write_text('saved')\n"
                                    "(run / 'manifest.json').write_text(json.dumps({'status':'episode_budget_exhausted'}))\n"
                                    "sys.exit(2)\n")
        self.assertEqual(state["status"], "episode_budget_exhausted")
        self.assertEqual(state["error_restarts"], 0)
        next_state = self.run_supervisor("assert sys.argv[3] == '2000'\n"
                                         "(run / 'manifest.json').write_text(json.dumps({'status':'completed'}))\n",
                                         extension=2000)
        self.assertEqual(next_state["status"], "completed")
        self.assertTrue(any(event["kind"] == "explicit_episode_budget_extension" for event in next_state["events"]))

    def test_memory_guard_samples_aggregate_and_requests_safe_stop(self):
        factory = self.factory("def stop(number, frame):\n"
                               "    (run / 'checkpoint.pt').write_text('safe')\n"
                               "    (run / 'manifest.json').write_text(json.dumps({'status':'interrupted'}))\n"
                               "    sys.exit(130)\n"
                               "signal.signal(signal.SIGTERM, stop)\n"
                               "(run / 'ready').write_text('ready')\n"
                               "while True: time.sleep(0.01)\n")
        def resident(_pid):
            return 29_500_000_000 if (self.run / "ready").exists() else 1_000_000
        state = supervise(self.control, self.run, self.config, ARGUMENTS,
                          command_factory=factory, rss_sampler=resident)
        self.assertEqual(state["status"], "memory_limit")
        self.assertTrue((self.run / "checkpoint.pt").exists())
        self.assertEqual(state["aggregate_sampled_peak_rss_bytes"], 29_500_000_000)

    def test_monitor_failures_preserve_worker_and_orphan_diagnostics_without_retry(self):
        for phase in ("worker", "orphan_cleanup"):
            with self.subTest(phase=phase):
                control, run = self.directory / phase, self.directory / (phase + "-training")
                exited = [phase == "orphan_cleanup"]
                process = Mock(pid=987651, returncode=0)
                process.poll.side_effect = lambda: 0 if exited[0] else None
                failure = OSError(errno.EPERM, "Cannot read live footprint")
                failure.monitor_pid = 987652
                groups = [True, True, False, False] if exited[0] else [False]
                signals = []

                def send(_process, number):
                    signals.append(number)
                    exited[0] = True

                with patch("tools.supervise_campaign_training.subprocess.Popen", return_value=process), \
                     patch("tools.supervise_campaign_training.process_group_alive", side_effect=groups), \
                     patch("tools.supervise_campaign_training._send", side_effect=send), \
                     patch("tools.supervise_campaign_training.time.sleep"):
                    state = supervise(control, run, self.config, ARGUMENTS,
                                      command_factory=lambda *_args: ["tiny-mocked-worker"],
                                      rss_sampler=Mock(side_effect=failure))
                event = next(value for value in state["events"] if value["kind"] == "memory_monitor_error")
                self.assertEqual(event["phase"], phase)
                self.assertEqual(event["operation"], "aggregate_memory_sample")
                self.assertEqual(event["exception_type"], "PermissionError")
                self.assertEqual(event["errno"], errno.EPERM)
                self.assertEqual(event["root_pid"], process.pid)
                self.assertEqual(event["sampled_pid"], 987652)
                self.assertEqual(state["status"], "memory_monitor_failure")
                self.assertEqual(state["error_restarts"], 0)
                self.assertEqual(signals, [signal.SIGTERM] if phase == "worker"
                                 else [signal.SIGTERM, signal.SIGKILL])

    def test_monitor_diagnostics_are_bounded_and_retain_exception_context(self):
        try:
            physical = OSError(errno.ESRCH, "Footprint PID disappeared")
            physical.monitor_pid = 987651
            raise physical
        except OSError:
            try:
                raise subprocess.TimeoutExpired(["ps", "-axo", "pid=,stat="], 5,
                                                output="x" * 4000, stderr="y" * 4000)
            except subprocess.TimeoutExpired as failure:
                details = monitor_error_details(failure, "aggregate_memory_sample", root_pid=987650)
        saved = json.loads(json.dumps(details, allow_nan=False))
        self.assertEqual(saved["exception_type"], "TimeoutExpired")
        self.assertEqual(saved["command"], ["ps", "-axo", "pid=,stat="])
        self.assertEqual(saved["timeout"], 5)
        self.assertEqual(len(saved["stdout"]), 2000)
        self.assertEqual(len(saved["stderr"]), 2000)
        self.assertEqual(saved["exception_context"][0]["errno"], errno.ESRCH)
        self.assertEqual(saved["exception_context"][0]["sampled_pid"], 987651)

    def test_memory_is_sampled_during_grace_and_absolute_limit_kills_immediately(self):
        factory = self.factory("signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                               "(run / 'ready').write_text('ready')\n"
                               "while True: time.sleep(0.01)\n")
        samples = []
        def resident(_pid):
            if not (self.run / "ready").exists():
                return 1_000_000
            samples.append(len(samples))
            return 29_500_000_000 if len(samples) == 1 else 30_000_000_000
        state = supervise(self.control, self.run, self.config, ARGUMENTS,
                          command_factory=factory, rss_sampler=resident)
        self.assertGreaterEqual(len(samples), 2)
        self.assertEqual(state["status"], "memory_limit")
        self.assertTrue(state["attempts"][0]["forced_kill"])
        self.assertEqual(state["attempts"][0]["returncode"], -signal.SIGKILL)

    def test_checkpoint_adoption_is_explicit_and_still_resumes_that_checkpoint(self):
        self.run.mkdir()
        checkpoint = self.run / "checkpoint.pt"
        checkpoint.write_text("existing initialized learner")
        with self.assertRaisesRegex(ValueError, "explicit checkpoint adoption"):
            self.run_supervisor("pass\n")
        state = self.run_supervisor("assert sys.argv[2] == str(run / 'checkpoint.pt')\n"
                                    "(run / 'manifest.json').write_text(json.dumps({'status':'completed'}))\n",
                                    adopt_checkpoint=True)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["attempts"][0]["resume"], str(checkpoint.resolve()))

    def test_same_run_cannot_be_owned_by_a_different_control_directory(self):
        location_lock = self.run.parent / ("." + self.run.name + ".training.lock")
        with exclusive_lock(location_lock):
            with self.assertRaisesRegex(RuntimeError, "already owns"):
                self.run_supervisor("raise RuntimeError('must not launch')\n")

    def test_orphan_group_is_stopped_before_retry(self):
        body = ("marker = run / 'checkpoint.pt'\n"
                "if not marker.exists():\n"
                "    import subprocess\n"
                "    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])\n"
                "    (run / 'orphan_group').write_text(str(os.getpgrp()))\n"
                "    marker.write_text('saved unfinished game')\n"
                "    sys.exit(75)\n"
                "assert sys.argv[2] == str(marker)\n"
                "(run / 'manifest.json').write_text(json.dumps({'status':'completed'}))\n")
        state = self.run_supervisor(body)
        self.assertEqual(state["status"], "completed")
        group = int((self.run / "orphan_group").read_text())
        self.assertFalse(process_group_alive(group))
        self.assertTrue(any(event["kind"] == "orphan_group_stop" for event in state["events"]))

    def test_existing_outputs_and_changed_identity_are_preserved(self):
        self.run.mkdir()
        marker = self.run / "personal-note"
        marker.write_text("preserve")
        with self.assertRaisesRegex(ValueError, "existing output"):
            self.run_supervisor("pass\n")
        self.assertEqual(marker.read_text(), "preserve")
        marker.unlink()
        self.run_supervisor("(run / 'manifest.json').write_text(json.dumps({'status':'completed'}))\n")
        with self.assertRaisesRegex(ValueError, "identity or budget changed"):
            supervise(self.control, self.run, replace(self.config, seconds=3), ARGUMENTS)

    def test_launch_failure_leaves_an_explicit_durable_error(self):
        def unavailable(*_args):
            return [str(self.directory / "missing-interpreter")]
        with self.assertRaises(FileNotFoundError):
            supervise(self.control, self.run, self.config, ARGUMENTS,
                      command_factory=unavailable, rss_sampler=lambda _pid: 1_000_000)
        state = json.loads((self.control / "state.json").read_text())
        self.assertEqual(state["status"], "supervisor_error")
        self.assertEqual(state["events"][-1]["error_type"], "FileNotFoundError")

    def test_duplicate_lock_is_rejected_and_inherited_by_running_child(self):
        lock = self.directory / "run.lock"
        with exclusive_lock(lock) as handle:
            with self.assertRaisesRegex(RuntimeError, "already owns"):
                with exclusive_lock(lock):
                    self.fail("duplicate lock acquired")
            process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)"],
                                       pass_fds=(handle.fileno(),))
            try:
                self.assertGreater(aggregate_rss(process.pid), 0)
            finally:
                process.terminate()
                process.wait(timeout=5)

    def test_crashed_supervisor_cannot_release_a_live_childs_lock(self):
        lock, marker = self.directory / "crash.lock", self.directory / "child.pid"
        body = ("import os, pathlib, subprocess, sys\n"
                "from tools.supervise_campaign_training import exclusive_lock\n"
                f"with exclusive_lock(pathlib.Path({str(lock)!r})) as handle:\n"
                "    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'], pass_fds=(handle.fileno(),))\n"
                f"    pathlib.Path({str(marker)!r}).write_text(str(child.pid))\n"
                "    os._exit(0)\n")
        result = subprocess.run([sys.executable, "-c", body], check=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        child_pid = int(marker.read_text())
        try:
            with self.assertRaisesRegex(RuntimeError, "already owns"):
                with exclusive_lock(lock):
                    self.fail("inherited live-child lock was lost")
        finally:
            os.kill(child_pid, signal.SIGTERM)

    def test_parent_context_exit_preserves_inherited_live_child_lock(self):
        lock = self.directory / "inherited-exit.lock"
        with exclusive_lock(lock) as handle:
            process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"],
                                       pass_fds=(handle.fileno(),))
        try:
            with self.assertRaisesRegex(RuntimeError, "already owns"):
                with exclusive_lock(lock):
                    self.fail("parent context released the surviving worker's lock")
        finally:
            process.terminate()
            process.wait(timeout=5)
        with exclusive_lock(lock):
            pass

    def test_unresponsive_worker_is_killed_after_save_grace_within_budget(self):
        self.config = replace(self.config, seconds=0.5, shutdown_seconds=0.1)
        state = self.run_supervisor("signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                                    "while True: time.sleep(0.01)\n")
        self.assertEqual(state["status"], "time_budget_exhausted")
        self.assertTrue(state["attempts"][0]["forced_kill"])
        self.assertEqual(state["attempts"][0]["returncode"], -signal.SIGKILL)
        self.assertLessEqual(state["charged_seconds"], self.config.seconds)

    def test_cpu_envelope_and_manual_checkpoint_recovery_are_explicit(self):
        validate_training_arguments(ARGUMENTS, self.config)
        for values in (["--threads", "1", "--parallel-envs", "2", "--cpu-budget", "4"],
                       [*ARGUMENTS, "--resume", "other.pt"], ["--threads", "1"]):
            with self.assertRaises(ValueError):
                validate_training_arguments(values, self.config)
        previous = self.run / "checkpoint.pt.previous"
        command = training_command(sys.executable, self.run, ARGUMENTS, previous, 2000)
        self.assertIn(str(previous), command)
        self.assertEqual(command[-2:], ["--extend-episode-budget", "2000"])
        with self.assertRaises(ValueError):
            SupervisorConfig(seconds=float("nan"))
        with self.assertRaises(ValueError):
            SupervisorConfig(seconds=10, cpu_budget=13)

    def test_darwin_charge_includes_compressed_footprint_and_keeps_larger_resident_count(self):
        with patch("tools.supervise_campaign_training.sys.platform", "darwin"), \
             patch("tools.supervise_campaign_training._darwin_physical_footprint", return_value=5_000_000_000):
            self.assertEqual(process_memory_charge(123, 1_000_000_000), 5_000_000_000)
            self.assertEqual(process_memory_charge(123, 6_000_000_000), 6_000_000_000)
        with patch("tools.supervise_campaign_training.sys.platform", "linux"), \
             patch("tools.supervise_campaign_training._darwin_physical_footprint", side_effect=AssertionError("No macOS API")):
            self.assertEqual(process_memory_charge(123, 10), 10)
        for pid, resident in ((0, 1), (-1, 1), (True, 1), (2**31, 1), (123, -1), (123, True)):
            with self.subTest(pid=pid, resident=resident), self.assertRaises(ValueError):
                process_memory_charge(pid, resident)

    def test_rusage_v4_reads_verified_sdk_offset_and_reports_api_errno(self):
        def function(pid, flavor, buffer):
            self.assertEqual((pid, flavor, len(buffer)), (123, 4, 296))
            ctypes.memmove(ctypes.addressof(buffer) + 64, struct.pack("=QQ", 987654, 27_000_000_000), 16)
            return 0
        with patch("tools.supervise_campaign_training._darwin_rusage_function", return_value=function):
            self.assertEqual(_darwin_physical_footprint(123), 27_000_000_000)

        def failure(*_args):
            ctypes.set_errno(errno.EPERM)
            return -1
        with patch("tools.supervise_campaign_training._darwin_rusage_function", return_value=failure):
            with self.assertRaises(OSError) as captured:
                _darwin_physical_footprint(123)
            self.assertEqual(captured.exception.errno, errno.EPERM)

    def test_darwin_live_failures_fail_closed_but_finished_or_zombie_races_are_ignored(self):
        prefix = "tools.supervise_campaign_training."
        with patch(prefix + "sys.platform", "darwin"), \
             patch(prefix + "_darwin_physical_footprint", side_effect=OSError(errno.EPERM, "live query failed")), \
             patch(prefix + "os.kill") as alive, patch(prefix + "_process_table", return_value=[(123, 1, 123, 10)]):
            with self.assertRaises(OSError) as captured:
                process_memory_charge(123, 10240)
            self.assertEqual(captured.exception.monitor_pid, 123)
            alive.side_effect = ProcessLookupError()
            self.assertEqual(process_memory_charge(123, 10240), 0)
            alive.side_effect = None
            with patch(prefix + "_process_table", return_value=[]):
                self.assertEqual(process_memory_charge(123, 10240), 0)

    def test_darwin_transient_privileged_process_exit_is_confirmed_on_retry(self):
        prefix = "tools.supervise_campaign_training."
        with patch(prefix + "sys.platform", "darwin"), \
             patch(prefix + "_darwin_physical_footprint", side_effect=[OSError(errno.EPERM, "privileged ps"),
                                                                      OSError(errno.ESRCH, "ps exited")]) as sample, \
             patch(prefix + "_process_disappeared", side_effect=[False, True]) as disappeared, \
             patch(prefix + "time.sleep") as sleep:
            self.assertEqual(process_memory_charge(123, 10240), 0)
        self.assertEqual(sample.call_count, 2)
        self.assertEqual(disappeared.call_count, 2)
        sleep.assert_called_once_with(0.02)

    def test_darwin_successful_retry_charges_footprint_without_rss_fallback(self):
        prefix = "tools.supervise_campaign_training."
        with patch(prefix + "sys.platform", "darwin"), \
             patch(prefix + "_darwin_physical_footprint", side_effect=[OSError(errno.ESRCH, "exit race"),
                                                                      5_000_000_000]) as sample, \
             patch(prefix + "_process_disappeared", return_value=False), \
             patch(prefix + "time.sleep") as sleep:
            self.assertEqual(process_memory_charge(123, 10240), 5_000_000_000)
        self.assertEqual(sample.call_count, 2)
        sleep.assert_called_once_with(0.02)

    def test_darwin_persistent_live_permission_failure_remains_fail_closed(self):
        prefix = "tools.supervise_campaign_training."
        failure = OSError(errno.EPERM, "live privileged process")
        with patch(prefix + "sys.platform", "darwin"), \
             patch(prefix + "_darwin_physical_footprint", side_effect=failure) as sample, \
             patch(prefix + "_process_disappeared", return_value=False) as disappeared, \
             patch(prefix + "time.sleep") as sleep:
            with self.assertRaises(OSError) as caught:
                process_memory_charge(123, 10240)
        self.assertIs(caught.exception, failure)
        self.assertEqual(caught.exception.monitor_pid, 123)
        self.assertEqual(sample.call_count, 3)
        self.assertEqual(disappeared.call_count, 3)
        self.assertEqual(sleep.call_args_list, [unittest.mock.call(0.02), unittest.mock.call(0.02)])

    def test_darwin_nontransient_io_failure_has_no_retry(self):
        prefix = "tools.supervise_campaign_training."
        failure = OSError(errno.EIO, "physical API failure")
        with patch(prefix + "sys.platform", "darwin"), \
             patch(prefix + "_darwin_physical_footprint", side_effect=failure) as sample, \
             patch(prefix + "_process_disappeared", return_value=False), \
             patch(prefix + "time.sleep") as sleep:
            with self.assertRaises(OSError) as caught:
                process_memory_charge(123, 10240)
        self.assertIs(caught.exception, failure)
        sample.assert_called_once_with(123)
        sleep.assert_not_called()

    def test_aggregate_charges_each_owned_process_once_and_excludes_unrelated_processes(self):
        parent = os.getpid()
        rows = [(parent, 1, parent, 10), (123, parent, 123, 20), (124, 123, 123, 30),
                (125, 124, 125, 40), (126, 1, 126, 1000)]
        with patch("tools.supervise_campaign_training._process_table", return_value=rows), \
             patch("tools.supervise_campaign_training.process_memory_charge", side_effect=lambda _pid, rss: rss + 1) as charge:
            self.assertEqual(aggregate_rss(123), 100 * 1024 + 4)
            self.assertEqual(charge.call_count, 4)
            self.assertEqual({call.args[0] for call in charge.call_args_list}, {parent, 123, 124, 125})


if __name__ == "__main__":
    unittest.main()
