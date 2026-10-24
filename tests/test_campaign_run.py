from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
import torch

from studies.shared.multiplayer_mcts import PLAYERS

ROOT = Path(__file__).resolve().parents[1]


class CampaignRunTests(unittest.TestCase):
    """Real two-root runner continuations, including a delivered OS signal."""

    flags = ["--batches", "2", "--transitions-per-batch", "2", "--parallel-envs", "2",
             "--simulations", "1", "--max-depth", "2", "--hidden-dim", "8",
             "--message-layers", "1", "--token-buckets", "128", "--batch-size", "4",
             "--epochs", "1", "--replay-capacity", "32", "--threads", "1",
             "--seed", "1947", "--checkpoint-every-waves", "1", "--calendar-rounds", "1"]

    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        cls.old_random = (random.getstate(), np.random.get_state(), torch.get_rng_state())
        cls.temporary = tempfile.TemporaryDirectory(prefix="campaign-cli-tests-")
        cls.directory = Path(cls.temporary.name)
        cls.reference_dir = cls.directory / "uninterrupted"
        result = cls.command(["--run-dir", str(cls.reference_dir), *cls.flags])
        if result.returncode != 0:
            cls.temporary.cleanup()
            raise AssertionError(f"Real CLI reference run failed: {result.stdout[-3000:]} {result.stderr[-1000:]}")
        cls.reference = cls.read(cls.reference_dir / "checkpoint.pt")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()
        random.setstate(cls.old_random[0])
        np.random.set_state(cls.old_random[1])
        torch.set_rng_state(cls.old_random[2])
        torch.set_num_threads(cls.old_threads)

    @staticmethod
    def environment():
        return {**os.environ, "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1"}

    @classmethod
    def command(cls, args):
        return subprocess.run([sys.executable, "-m", "studies.campaign.run", "train", *args],
                              cwd=ROOT, env=cls.environment(), capture_output=True, text=True, timeout=60)

    @staticmethod
    def read(path):
        return torch.load(path, map_location="cpu", weights_only=False)

    @staticmethod
    def files(directory):
        return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in directory.rglob("*") if path.is_file()}

    def assert_tree_equal(self, expected, actual, path="learner"):
        if isinstance(expected, torch.Tensor):
            self.assertTrue(torch.equal(expected, actual), f"Tensor differs at {path}")
        elif isinstance(expected, np.ndarray):
            self.assertTrue(np.array_equal(expected, actual), f"Array differs at {path}")
        elif isinstance(expected, dict):
            self.assertEqual(set(expected), set(actual), f"Keys differ at {path}")
            for key in expected:
                self.assert_tree_equal(expected[key], actual[key], f"{path}.{key}")
        elif isinstance(expected, (list, tuple)):
            self.assertEqual(type(expected), type(actual), f"Sequence type differs at {path}")
            self.assertEqual(len(expected), len(actual), f"Length differs at {path}")
            for index, (first, second) in enumerate(zip(expected, actual, strict=True)):
                self.assert_tree_equal(first, second, f"{path}[{index}]")
        else:
            self.assertTrue(expected == actual, f"Value differs at {path}")

    def assert_completed_matches_reference(self, directory):
        actual = self.read(directory / "checkpoint.pt")
        # Wall timing belongs to invocation reports/progress, outside the full
        # learner checkpoint. Every learner field, including execution RNG,
        # optimizer moments and active CampaignAdapters, must match exactly.
        self.assert_tree_equal(self.reference["learner"], actual["learner"])
        self.assert_tree_equal(self.reference["runner"], actual["runner"], "runner")
        manifest = json.loads((directory / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "completed")
        self.assert_invocation_timings(manifest)

    def assert_invocation_timings(self, manifest):
        timings = manifest["timings_seconds_this_invocation"]
        self.assertEqual(set(timings), {"collection", "learning_updates", "checkpoint_save", "progress_reporting"})
        self.assertTrue(all(math.isfinite(value) and value >= 0 for value in timings.values()))
        for name in ("collection", "learning_updates", "checkpoint_save"):
            self.assertGreater(timings[name], 0)
        self.assertLessEqual(sum(timings.values()), manifest["elapsed_seconds_this_invocation"])
        self.assertGreater(manifest["collection_transitions_per_second_this_invocation"], 0)
        self.assertNotIn("timings_seconds_this_invocation", manifest["runner"])

    def test_record_replay_is_opt_in_and_preserves_training_and_resume_files(self):
        self.assertFalse((self.reference_dir / "replay.jsonl").exists())
        directory = self.directory / "recorded"
        result = self.command(["--run-dir", str(directory), *self.flags, "--record-replay"])
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        actual = self.read(directory / "checkpoint.pt")
        self.assert_tree_equal(self.reference["learner"], actual["learner"])
        records = [json.loads(line) for line in (directory / "replay.jsonl").read_text().splitlines()]
        self.assertEqual(records[0]["type"], "run_start")
        self.assertEqual(records[-1]["type"], "run_end")
        self.assertEqual(records[-1]["status"], "completed")
        self.assertEqual(records[0]["verification"], "initial_serialized_sha256_then_planning_keys_and_seed")
        transitions = [record for record in records if record["type"] == "transition"]
        self.assertEqual([record["event"] for record in transitions], actual["learner"]["action_history"])
        self.assertEqual(len(transitions), actual["learner"]["counters"]["transitions"])
        starts = [record for record in records if record["type"] == "episode_start"]
        self.assertEqual([record["seed"] for record in starts], actual["runner"]["training_environment_seeds"])
        manifest = json.loads((directory / "manifest.json").read_text())
        self.assertEqual(manifest["replay_trace"], "replay.jsonl")
        before = self.files(directory)
        rejected = self.command(["--resume", str(directory / "checkpoint.pt"), "--record-replay"])
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("requires a fresh run", rejected.stderr)
        self.assertEqual(before, self.files(directory))

    def test_completed_manifest_reports_wall_time_outside_deterministic_checkpoint(self):
        manifest = json.loads((self.reference_dir / "manifest.json").read_text())
        self.assert_invocation_timings(manifest)
        self.assertIn("studies/shared/immutable_json.py", self.reference["runner"]["runtime_source_sha256"])
        self.assertAlmostEqual(manifest["collection_transitions_per_second_this_invocation"],
                               self.reference["learner"]["counters"]["transitions"] /
                               manifest["timings_seconds_this_invocation"]["collection"])
        self.assertNotIn("timings_seconds_this_invocation", self.reference["runner"])
        self.assertNotIn("timings_seconds_this_invocation", self.reference["learner"])

    def test_real_two_root_cli_updates_all_actors_and_resume_matches_uninterrupted(self):
        directory = self.directory / "bounded-resume"
        stopped = self.command(["--run-dir", str(directory), *self.flags, "--stop-after-waves", "3"])
        self.assertEqual(stopped.returncode, 130, stopped.stderr[-3000:])
        checkpoint = self.read(directory / "checkpoint.pt")
        self.assertEqual(checkpoint["runner"]["batch_index"], 1)
        self.assertEqual(checkpoint["runner"]["wave_index"], 1)
        self.assertEqual(checkpoint["learner"]["generation"], 1)
        self.assertIsNotNone(checkpoint["learner"]["frozen_models"])
        self.assertEqual(len(checkpoint["learner"]["parallel_envs"]), 2)
        for player in PLAYERS:
            self.assertTrue(checkpoint["learner"]["optimizers"][player]["state"], "Adam state was not populated")
        resumed = self.command(["--resume", str(directory / "checkpoint.pt")])
        self.assertEqual(resumed.returncode, 0, resumed.stderr[-3000:])
        self.assert_completed_matches_reference(directory)
        self.assertTrue(any(size > 1 for size in self.reference["runner"]["batch_sizes"]))
        self.assertEqual(self.reference["learner"]["generation"], 2)
        self.assertEqual(len(self.reference["runner"]["updates"]), 2)
        # Compare against the actual seeded initial graph models, not merely a
        # generation counter which could advance without any parameter update.
        from studies.campaign.run import RunConfig, _learner
        from studies.campaign.curriculum import make_env
        config = RunConfig(**self.reference["runner"]["config"])
        initial = _learner(config, make_env(config.seed, calendar_rounds=config.calendar_rounds))
        for player in PLAYERS:
            trained = self.reference["learner"]["models"][player]
            self.assertTrue(any(not torch.equal(tensor, trained[name])
                                for name, tensor in initial.models[player].state_dict().items()),
                            f"Real training left {player} unchanged")

    def test_sigint_after_first_flushed_rollout_saves_then_resumes_exactly(self):
        directory = self.directory / "signal-resume"
        command = [sys.executable, "-m", "studies.campaign.run", "train", "--run-dir", str(directory), *self.flags]
        process = subprocess.Popen(command, cwd=ROOT, env=self.environment(), stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        output, sent = [], False
        deadline = time.monotonic() + 60
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while time.monotonic() < deadline:
                    if not selector.select(timeout=min(0.1, max(0, deadline - time.monotonic()))):
                        if process.poll() is not None:
                            break
                        continue
                    line = process.stdout.readline()
                    if not line:
                        break
                    output.append(line)
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if item.get("event") == "rollout":
                        process.send_signal(signal.SIGINT)
                        sent = True
                        break
            tail, _ = process.communicate(timeout=max(0.1, deadline - time.monotonic()))
            output.append(tail)
            self.assertTrue(sent, "No flushed rollout was observed before the bounded signal deadline")
            self.assertEqual(process.returncode, 130, "".join(output)[-3000:])
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)
            if process.stdout is not None:
                process.stdout.close()
        manifest = json.loads((directory / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "interrupted")
        checkpoint = self.read(directory / "checkpoint.pt")
        self.assertIsNotNone(checkpoint["learner"]["frozen_models"])
        self.assertGreater(checkpoint["learner"]["counters"]["transitions"], 0)
        self.assertTrue(any(json.loads(line).get("stop_reason") == "SIGINT"
                            for line in "".join(output).splitlines() if line.startswith("{")))
        resumed = self.command(["--resume", str(directory / "checkpoint.pt")])
        self.assertEqual(resumed.returncode, 0, resumed.stderr[-3000:])
        self.assert_completed_matches_reference(directory)

    def test_source_config_and_nonempty_directory_rejection_preserve_files(self):
        expected = self.files(self.reference_dir)
        mismatch = self.command(["--resume", str(self.reference_dir / "checkpoint.pt"), "--learning-rate", "0.002"])
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("Resume configuration differs: learning_rate", mismatch.stderr)
        self.assertEqual(self.files(self.reference_dir), expected)
        directory = self.directory / "incompatible-source"
        directory.mkdir()
        source_checkpoint = copy.deepcopy(self.reference)
        source_checkpoint["runner"]["runtime_source_sha256"]["studies/campaign/run.py"] = "0" * 64
        path = directory / "checkpoint.pt"
        torch.save(source_checkpoint, path)
        before = self.files(directory)
        source_mismatch = self.command(["--resume", str(path)])
        self.assertNotEqual(source_mismatch.returncode, 0)
        self.assertIn("Runtime sources changed", source_mismatch.stderr)
        self.assertEqual(self.files(directory), before)
        occupied = self.directory / "occupied"
        occupied.mkdir()
        (occupied / "keep.txt").write_text("Existing experiment and personal notes must survive.\n")
        before = self.files(occupied)
        rejection = self.command(["--run-dir", str(occupied), *self.flags])
        self.assertNotEqual(rejection.returncode, 0)
        self.assertIn("Choose an empty run directory", rejection.stderr)
        self.assertEqual(self.files(occupied), before)
        redirected_resume = self.command(["--resume", str(self.reference_dir / "checkpoint.pt"),
                                          "--run-dir", str(occupied)])
        self.assertNotEqual(redirected_resume.returncode, 0)
        self.assertIn("Choose an empty run directory", redirected_resume.stderr)
        self.assertEqual(self.files(occupied), before)
        self.assertEqual(self.files(self.reference_dir), expected)


if __name__ == "__main__":
    unittest.main()
