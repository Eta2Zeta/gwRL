"""Independent deadline, orphan, memory-escalation and signal-target checks."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from tools.campaign_deadline_guardian import Process, SCHEMA, guard, process_table


class Clock:
    def __init__(self):
        self.value = 100.

    def now(self):
        return self.value

    def sleep(self, amount):
        self.value += amount


class CampaignGuardianTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.plan_path = self.root / "pipeline-plan.json"
        self.plan = {"run_root": str(self.root), "deadline_epoch": 102., "shutdown_seconds": .5,
                     "poll_seconds": .1, "memory_bytes": 26_000_000_000,
                     "memory_soft_bytes": 25_000_000_000}
        self.write(self.plan_path, self.plan)
        self.write(self.root / "pipeline-state.json", {"status": "running", "pipeline_pid": None,
                                                      "known_process_groups": []})
        self.signals = []

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def process(self, pid, parent=1, group=None, rss=1_000_000, birth="original", command=None):
        return Process(pid, parent, group or pid, rss, birth,
                       command or f"python -m studies.campaign.run train --run-dir {self.root}/training")

    def test_graceful_deadline_discovers_reparented_training_group_from_control_state(self):
        clock, live = Clock(), [self.process(987651)]
        self.write(self.root / "training-control" / "state.json", {"child_process_group": 987651})

        def signal_group(group, number):
            self.signals.append((group, number, clock.now()))
            live.clear()

        result = guard(self.plan_path, sampler=lambda: live.copy(), now=clock.now, sleep=clock.sleep,
                       send_group=signal_group, send_process=lambda *args: self.fail("No pipeline is live"))
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertEqual(len(self.signals), 1)
        self.assertEqual(self.signals[0][:2], (987651, signal.SIGTERM))
        self.assertGreaterEqual(self.signals[0][2], 101.5)
        self.assertLess(self.signals[0][2], 102.)
        self.assertEqual(result["known_process_groups"], [])

    def test_memory_is_rechecked_during_term_grace_and_hard_limit_kills_immediately(self):
        clock, live = Clock(), [self.process(987652, rss=25_100_000_000)]
        self.write(self.root / "pipeline-state.json", {"status": "running", "known_process_groups": [987652]})

        def signal_group(group, number):
            self.signals.append((group, number, clock.now()))
            if number == signal.SIGTERM:
                live[:] = [self.process(987652, rss=26_100_000_000)]
            else:
                live.clear()

        result = guard(self.plan_path, sampler=lambda: live.copy(), now=clock.now, sleep=clock.sleep,
                       send_group=signal_group, send_process=lambda *args: self.fail("No pipeline is live"))
        self.assertEqual([number for _, number, _ in self.signals], [signal.SIGTERM, signal.SIGKILL])
        self.assertLess(self.signals[1][2], 100.5)
        self.assertEqual(result["peak_rss_bytes"], 26_100_000_000)
        self.assertEqual(result["status"], "stopped")

    def test_reused_pid_and_unrelated_registered_group_are_never_signaled(self):
        self.write(self.root / "guardian-state.json", {"schema": SCHEMA, "deadline_epoch": 102.,
            "known_process_groups": [987653], "group_leaders": {"987653": "old birth"},
            "group_members": {"987653": {"987653": "old birth"}}})
        self.write(self.root / "pipeline-state.json", {"status": "completed", "known_process_groups": [987653, 987654, os.getpgrp()]})
        unrelated = [self.process(987653, birth="new birth", command="zsh -l"),
                     self.process(987654, command="python unrelated.py"),
                     self.process(987655, group=os.getpgrp(), command="zsh")]
        result = guard(self.plan_path, sampler=lambda: unrelated, now=lambda: 100., sleep=lambda _: self.fail("Should exit"),
                       send_group=lambda *args: self.fail("Unrelated group was signaled"),
                       send_process=lambda *args: self.fail("Unrelated process was signaled"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["known_process_groups"], [])

    def test_restarted_pipeline_matching_original_plan_is_stopped_individually(self):
        original = self.root / "plan.json"
        self.write(original, self.plan)
        clock, live = Clock(), [self.process(987656, group=os.getpgrp(), command=(
            f"python tools/run_three_round_experiment.py --plan {original}"))]
        self.write(self.root / "pipeline-state.json", {"status": "running", "pipeline_pid": 987656,
                                                       "known_process_groups": [os.getpgrp()]})

        def signal_process(pid, number):
            self.signals.append((pid, number))
            live.clear()

        result = guard(self.plan_path, sampler=lambda: live.copy(), now=clock.now, sleep=clock.sleep,
                       send_group=lambda *args: self.fail("Pipeline shell group must never be signaled"),
                       send_process=signal_process)
        self.assertEqual(self.signals, [(987656, signal.SIGTERM)])
        self.assertEqual(result["status"], "budget_exhausted")

    def test_duplicate_guardian_does_not_overwrite_state_or_own_lock(self):
        with (self.root / "guardian.lock").open("a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = guard(self.plan_path, sampler=lambda: self.fail("Duplicate must not sample"))
        self.assertEqual(result["status"], "already_running")
        self.assertFalse((self.root / "guardian-state.json").exists())

    def test_real_orphan_group_ignoring_term_is_killed_at_absolute_deadline(self):
        self.plan.update(deadline_epoch=time.time() + 1.2, shutdown_seconds=.4, poll_seconds=.05)
        self.write(self.plan_path, self.plan)
        child = subprocess.Popen([sys.executable, "-c",
            "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)",
            "-m studies.campaign.run", "--run-dir", str(self.root / "training")], start_new_session=True)
        self.write(self.root / "training-control" / "state.json", {"child_process_group": child.pid})
        try:
            result = guard(self.plan_path)
            child.wait(timeout=3)
            self.assertEqual(child.returncode, -signal.SIGKILL)
            self.assertGreaterEqual(time.time(), self.plan["deadline_epoch"])
            self.assertEqual(result["status"], "budget_exhausted")
            self.assertTrue(any(event.get("signal") == "SIGTERM" for event in result["events"]))
            self.assertTrue(any(event.get("signal") == "SIGKILL" for event in result["events"]))
            self.assertNotIn(child.pid, {row.pid for row in process_table()})
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
