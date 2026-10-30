from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from studies.campaign.scaling_benchmark import BenchmarkConfig, MEMORY_MARGIN_BYTES, supervise

ROOT = Path(__file__).resolve().parents[1]


class ScalingBenchmarkTests(unittest.TestCase):
    def test_record_replay_rejects_fixed_searches_and_preserves_existing_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            with self.assertRaisesRegex(ValueError, "episode mode"):
                supervise(BenchmarkConfig(roots=1, threads=1), output, record_replay=True)
            replay = output.with_suffix(".replay.jsonl")
            replay.write_text('{"type":"run_start"}\n')
            before = replay.read_bytes()
            with self.assertRaisesRegex(ValueError, "preserved"):
                supervise(BenchmarkConfig(mode="episode", roots=1, threads=1), output, record_replay=True)
            self.assertEqual(replay.read_bytes(), before)
            self.assertFalse(output.exists())

    def test_episode_replay_records_only_executed_choices_and_current_search_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            command = [sys.executable, "-m", "studies.campaign.scaling_benchmark", "--output", str(output),
                       "--mode", "episode", "--roots", "1", "--threads", "1", "--simulations", "1",
                       "--max-depth", "2", "--max-transitions", "2", "--seconds", "30",
                       "--hidden-dim", "8", "--message-layers", "1", "--token-buckets", "128", "--record-replay"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stderr[-3000:])
            report = json.loads(output.read_text())
            records = [json.loads(line) for line in output.with_suffix(".replay.jsonl").read_text().splitlines()]
            transitions = [record for record in records if record["type"] == "transition"]
            self.assertEqual(len(transitions), 2)
            self.assertEqual(report["executed_decisions"] + report["chance_events"], 2)
            self.assertEqual(records[-1]["type"], "run_end")
            self.assertEqual(records[-1]["status"], "collection_limit")
            self.assertTrue(all(record["terminal_returns"] is None for record in transitions))
            for record in transitions:
                if record["event"]["kind"] != "chance":
                    self.assertEqual(record["selected_action"], record["decision_menu"][record["selected_index"]])
                    self.assertEqual(record["search"]["simulations"], 1)

    def test_episodes_play_forced_moves_at_once_and_count_only_real_searches(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            command = [sys.executable, "-m", "studies.campaign.scaling_benchmark", "--output", str(output),
                       "--mode", "episode", "--roots", "1", "--threads", "1", "--simulations", "1",
                       "--max-depth", "2", "--max-transitions", "30", "--seconds", "60",
                       "--hidden-dim", "8", "--message-layers", "1", "--token-buckets", "128", "--record-replay"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=70)
            self.assertEqual(result.returncode, 0, result.stderr[-3000:])
            report = json.loads(output.read_text())
            records = [json.loads(line) for line in output.with_suffix(".replay.jsonl").read_text().splitlines()]
        self.assertFalse(report["waves"][0]["search_configs"][0]["search_forced_root"])
        played = [record for record in records if record["type"] == "transition" and record["event"]["kind"] != "chance"]
        forced = [record["search"] for record in played if len(record["decision_menu"]) == 1]
        self.assertGreater(len(forced), 0)
        self.assertTrue(all((row["visit_counts"], row["values"]) == ([0], None) for row in forced))
        self.assertEqual(report["executed_decisions"], len(played))
        self.assertEqual(report["decisions"], len(played) - len(forced))

    def test_authorized_resource_envelope_includes_both_coordinators(self):
        config = BenchmarkConfig(roots=6, threads=4)
        self.assertEqual(config.roots + config.threads + 2, 12)
        with self.assertRaisesRegex(ValueError, "coordinators"):
            replace(config, roots=7)
        with self.assertRaisesRegex(ValueError, "authorized 12"):
            replace(config, cpu_budget=13)
        with self.assertRaisesRegex(ValueError, "30 GB"):
            replace(config, memory_bytes=30_000_000_001)

    def test_task_and_collection_limits_are_distinct(self):
        config = BenchmarkConfig(calendar_rounds=2, start_round=2, max_transitions=1)
        self.assertEqual(config.calendar_rounds, 2)
        with self.assertRaisesRegex(ValueError, "Starting round"):
            replace(config, start_round=3)
        with self.assertRaisesRegex(ValueError, "nation index"):
            replace(config, start_nation_index=4)
        with self.assertRaisesRegex(ValueError, "nation index"):
            replace(config, start_nation_index=-1)
        with self.assertRaisesRegex(ValueError, "approved initial"):
            BenchmarkConfig(mode="episode", start_nation_index=2)
        with self.assertRaisesRegex(ValueError, "approved initial"):
            BenchmarkConfig(mode="episode", start_decision_kind="production")
        with self.assertRaisesRegex(ValueError, "approved initial"):
            replace(config, mode="episode")
        with self.assertRaisesRegex(ValueError, "Wall limit"):
            replace(config, seconds=float("nan"))
        with self.assertRaisesRegex(ValueError, "positive integer"):
            replace(config, max_state_visits=0)

    def test_external_watchdog_stops_worker_before_it_can_finish_initializing(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            result = supervise(BenchmarkConfig(seconds=0.001, roots=1, threads=1), output)
            self.assertEqual(result["status"], "wall_limit")
            self.assertLess(result["watchdog"]["elapsed_seconds"], 5)
            self.assertNotEqual(result["watchdog"]["worker_returncode"], 0)
            self.assertEqual(json.loads(output.read_text()), result)
            with self.assertRaisesRegex(ValueError, "preserved"):
                supervise(BenchmarkConfig(seconds=0.001), output)

    def test_memory_guard_checks_aggregate_rss_and_retains_result(self):
        config = BenchmarkConfig(roots=1, threads=1)
        with tempfile.TemporaryDirectory() as temporary, patch(
                "studies.campaign.scaling_benchmark._rss_bytes", return_value=config.memory_bytes // 2):
            result = supervise(config, Path(temporary) / "result.json")
        self.assertEqual(result["status"], "memory_limit")
        self.assertEqual(result["watchdog"]["aggregate_sampled_peak_rss_bytes"], config.memory_bytes)
        self.assertEqual(result["watchdog"]["memory_stop_threshold_bytes"],
                         config.memory_bytes - MEMORY_MARGIN_BYTES)

    def test_watchdog_retains_latest_per_root_progress_on_mid_search_cutoff(self):
        # A lightweight stalled worker isolates preservation of an already
        # completed wave from unpredictable torch/native startup duration.
        progress = [{"index": 0, "clock": {"round_index": 1, "phase": "combat"},
                     "terminal": False, "transitions": 7, "decisions": 5,
                     "chance_events": 2, "observed_terminal_returns": None},
                    {"index": 1, "clock": {"round_index": 1, "phase": "place_units"},
                     "terminal": True, "transitions": 12, "decisions": 9,
                     "chance_events": 3, "observed_terminal_returns": [1.0, 2.0, 3.0]}]
        saved = {"status": "running", "root_progress": progress,
                 "pending_wave": {"index": 4}, "decisions": 14}
        original = subprocess.Popen

        def worker_command(command, *args, **kwargs):
            if "--_worker" in command:
                destination = command[command.index("--output") + 1]
                script = ("import pathlib,sys,time; "
                          "pathlib.Path(sys.argv[1]).write_text(sys.argv[2]); time.sleep(60)")
                command = [sys.executable, "-c", script, destination, json.dumps(saved)]
            return original(command, *args, **kwargs)

        with tempfile.TemporaryDirectory() as temporary, patch(
                "studies.campaign.scaling_benchmark.subprocess.Popen", side_effect=worker_command):
            output = Path(temporary) / "result.json"
            result = supervise(BenchmarkConfig(seconds=0.5, roots=2, threads=1), output)
            self.assertEqual(json.loads(output.read_text()), result)
        self.assertEqual(result["status"], "wall_limit")
        self.assertEqual(result["root_progress"], progress)
        self.assertEqual(result["pending_wave"], {"index": 4})
        self.assertTrue(result["watchdog"]["last_progress_preserved"])

    def test_real_two_root_search_reports_actual_menus_clocks_and_frozen_models(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            command = [sys.executable, "-m", "studies.campaign.scaling_benchmark", "--output", str(output),
                       "--roots", "2", "--threads", "1", "--simulations", "1", "--max-depth", "2",
                       "--waves", "1", "--hidden-dim", "8", "--token-buckets", "128", "--seconds", "30"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text())
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(report["decisions"], 2)
        self.assertEqual(report["executed_decisions"], 0)
        self.assertTrue(report["actual_state_and_rng_unchanged"])
        self.assertEqual(report["root_progress"], [
            {key: value for key, value in root.items() if key != "stop_reason"}
            for root in report["roots"]])
        self.assertEqual(len(report["samples"]), 2)
        self.assertTrue(all(sample["menu_size"] > 0 for sample in report["samples"]))
        self.assertTrue(all(sample["clock"]["round_index"] == 0 for sample in report["samples"]))
        self.assertTrue(all(row["transitions"] == 0 and row["status"] == "reached"
                            for row in report["preparation"]["roots"]))
        self.assertEqual(report["waves"][0]["roots"], 2)
        self.assertTrue(all(row["search_forced_root"] for row in report["waves"][0]["search_configs"]))
        self.assertEqual(report["model"]["training_updates"], 0)
        self.assertTrue(report["model"]["frozen"])
        self.assertEqual(set(report["model"]["versions"]), {"axis", "allies", "comintern"})
        self.assertEqual(report["resources"]["conservative_thread_budget"], 5)
        self.assertGreater(report["timings_seconds"]["inference"], 0)
        self.assertLessEqual(report["timings_seconds"]["inference"], report["timings_seconds"]["search"])
        self.assertLess(report["watchdog"]["aggregate_sampled_peak_rss_bytes"], 30_000_000_000)

    def test_preparation_cutoff_does_not_claim_to_have_reached_a_later_round(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            command = [sys.executable, "-m", "studies.campaign.scaling_benchmark", "--output", str(output),
                       "--roots", "1", "--threads", "1", "--start-round", "2",
                       "--preparation-transitions", "1", "--seconds", "30"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text())
        self.assertEqual(report["status"], "preparation_limit")
        self.assertEqual(report["preparation"]["roots"][0]["clock"]["round_index"], 0)
        self.assertEqual(report["preparation"]["roots"][0]["transitions"], 1)
        self.assertEqual(report["decisions"], 0)

    def test_preparation_reaches_real_first_round_japan_phase(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            command = [sys.executable, "-m", "studies.campaign.scaling_benchmark", "--output", str(output),
                       "--roots", "1", "--threads", "1", "--start-nation-index", "2",
                       "--start-phase", "combat_movement", "--start-decision-kind", "combat_movement",
                       "--simulations", "1", "--max-depth", "1",
                       "--waves", "1", "--seconds", "30", "--hidden-dim", "8", "--token-buckets", "128"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text())
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(report["preparation"]["target"]["nation"], "japan")
        reached = report["preparation"]["roots"][0]
        self.assertEqual(reached["status"], "reached")
        self.assertGreater(reached["transitions"], 0)
        self.assertEqual(reached["clock"]["round_index"], 0)
        self.assertEqual(reached["clock"]["nation_index"], 2)
        self.assertEqual(reached["clock"]["phase"], "combat_movement")
        self.assertEqual(report["samples"][0]["clock"], reached["clock"])
        self.assertGreater(report["samples"][0]["menu_size"], 0)
        self.assertEqual(report["samples"][0]["decision_kind"], "combat_movement")
        self.assertEqual(report["samples"][0]["owner"], "axis")
        self.assertTrue(report["actual_state_and_rng_unchanged"])

    def test_weights_transfer_imports_only_models_and_preserves_checkpoint(self):
        import torch
        from studies.shared.multiplayer_mcts import PLAYERS
        from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet
        from dataclasses import asdict

        config = CampaignModelConfig(hidden_dim=8, message_layers=1, token_buckets=128)
        models = {player: CampaignPolicyValueNet(config).state_dict() for player in PLAYERS}
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "trusted.pt"
            # These deliberately invalid old learner fields prove that neither
            # restore nor its replay/RNG/state validation is used for transfer.
            torch.save({"schema": "campaign-foreground-run-v1", "learner": {
                "metadata": {"model_config": asdict(config), "compatibility": {"rules": "old-rule-revision"}},
                "models": models, "optimizers": "must not be restored", "rng": "must not be restored",
                "parallel_envs": "must not be restored"}}, checkpoint)
            before = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
            output = Path(temporary) / "result.json"
            command = [sys.executable, "-m", "studies.campaign.scaling_benchmark", "--output", str(output),
                       "--roots", "1", "--threads", "1", "--simulations", "1", "--max-depth", "1",
                       "--mode", "episode", "--max-transitions", "1", "--seconds", "30",
                       "--checkpoint-weights", str(checkpoint)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text())
            self.assertEqual(before, hashlib.sha256(checkpoint.read_bytes()).hexdigest())
        self.assertEqual(report["status"], "collection_limit", report)
        self.assertEqual(report["executed_decisions"], 1)
        self.assertEqual(report["root_progress"][0]["transitions"], 1)
        self.assertEqual(report["root_progress"][0]["decisions"], 1)
        self.assertIsNone(report["root_progress"][0]["observed_terminal_returns"])
        self.assertEqual(report["root_progress"], [
            {key: value for key, value in root.items() if key != "stop_reason"}
            for root in report["roots"]])
        self.assertEqual(report["model"]["config"], asdict(config))
        self.assertEqual(report["model"]["weights_transfer"]["sha256"], before)
        self.assertEqual(report["model"]["weights_transfer"]["source_compatibility"]["rules"], "old-rule-revision")
        self.assertEqual(report["model"]["training_updates"], 0)


if __name__ == "__main__":
    unittest.main()
