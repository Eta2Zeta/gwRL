"""The long-run pipeline tested with tiny child programs, never game training."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import shutil
import sys
import tempfile
import time
import unittest

from tools.run_three_round_experiment import Experiment, STAGES, digest, freeze_checkpoint, validate_plan, verify_runtime_manifest


class ThreeRoundExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="three-round-pipeline-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "experiment"
        self.plan = {"run_root": str(self.root), "working_directory": str(self.directory),
                     "python": sys.executable, "deadline_epoch": time.time() + 30,
                     "training_arguments": ["--calendar-rounds", "3", "--complete-episodes",
                         "--batches", "10000", "--threads", "1", "--parallel-envs", "1", "--cpu-budget", "3"],
                     "heldout_seeds": [40009], "final_eval_reserve_seconds": 5,
                     "initial_eval_seconds": 5, "shutdown_seconds": 0.1,
                     "initialize_seconds": 5, "poll_seconds": 0.02, "prevent_sleep": False}
        self.worker = self.directory / "worker.py"
        self.worker.write_text(
            "import json, pathlib, sys\n"
            "root, stage = pathlib.Path(sys.argv[1]), sys.argv[2]\n"
            "training = root / 'training'\n"
            "training.mkdir(exist_ok=True)\n"
            "with (root / 'executed.jsonl').open('a') as log: log.write(stage+'\\n')\n"
            "if stage == 'initialize':\n"
            "    (training / 'initial.pt').write_text('initial weights')\n"
            "    (training / 'checkpoint.pt').write_text('unfinished games')\n"
            "    sys.exit(130)\n"
            "if stage in ('initial_evaluation','final_evaluation'):\n"
            "    output = root / ('evaluation-initial' if stage == 'initial_evaluation' else 'evaluation-final')\n"
            "    output.mkdir(exist_ok=True)\n"
            "    (output / 'plan.json').write_text('{}')\n"
            "    if stage == 'final_evaluation':\n"
            "        assert (root / 'evaluation-checkpoint.pt').read_text() == 'trained weights'\n"
            "        assert (training / 'initial.pt').read_text() == 'initial weights'\n"
            "    (output / 'report.json').write_text(json.dumps({'status':'completed'}))\n"
            "if stage == 'training':\n"
            "    (training / 'checkpoint.pt').write_text('trained weights')\n"
            "    control = root / 'training-control'\n"
            "    control.mkdir(exist_ok=True)\n"
            "    (control / 'state.json').write_text(json.dumps({'status':'time_budget_exhausted'}))\n")

    def command(self, stage, _deadline, _experiment):
        return [sys.executable, str(self.worker), str(self.root), stage]

    def experiment(self, **kwargs):
        return Experiment(self.plan, command_builder=self.command,
                          rss_sampler=kwargs.get("rss_sampler", lambda _pid: 1_000_000),
                          guardian_starter=lambda _experiment: None)

    def test_all_stages_run_automatically_then_finished_run_is_reused(self):
        state = self.experiment().run()
        self.assertEqual(state["status"], "completed")
        self.assertEqual((self.root / "executed.jsonl").read_text().splitlines(),
                         [stage for stage in STAGES if stage != "freeze_checkpoint"])
        self.assertEqual((self.root / "evaluation-checkpoint.pt").read_text(), "trained weights")
        self.assertGreater(state["training_seconds"], 0)
        count = len(state["attempts"])
        again = self.experiment().run()
        self.assertEqual(len(again["attempts"]), count)
        self.assertEqual(again["plan_sha256"], state["plan_sha256"])

    def test_failed_worker_stops_for_attention_then_exact_stage_resumes(self):
        original = self.worker.read_text()
        self.worker.write_text(original.replace("if stage in ('initial_evaluation','final_evaluation'):",
            "if stage == 'initial_evaluation': raise ValueError('check source/config')\n"
            "if stage in ('initial_evaluation','final_evaluation'):"))
        state = self.experiment().run()
        self.assertEqual(state["status"], "attention_required")
        self.assertEqual(state["stage"], "initial_evaluation")
        self.assertFalse((self.root / "training-control").exists())
        old_deadline = state["stage_deadlines"]["initial_evaluation"]
        self.worker.write_text(original)
        again = self.experiment().run()
        self.assertEqual(again["status"], "completed")
        self.assertEqual(again["stage_deadlines"]["initial_evaluation"], old_deadline)
        self.assertEqual((self.root / "executed.jsonl").read_text().splitlines().count("initialize"), 1)

    def test_expired_absolute_deadline_never_launches_work(self):
        self.plan["deadline_epoch"] = time.time() - 1
        state = self.experiment().run()
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertFalse((self.root / "executed.jsonl").exists())
        self.assertEqual(state["attempts"], [])

    def test_changed_plan_cannot_reset_deadline_or_hyperparameters(self):
        self.experiment().run()
        self.plan["deadline_epoch"] += 1
        with self.assertRaisesRegex(ValueError, "plan changed"):
            self.experiment().run()

    def test_partial_evaluation_is_not_reported_as_complete(self):
        original = self.worker.read_text()
        self.worker.write_text(original.replace(
            "(output / 'report.json').write_text(json.dumps({'status':'completed'}))",
            "(output / 'report.json').write_text(json.dumps({'status':'interrupted'}))\n"
            "    sys.exit(130)"))
        state = self.experiment().run()
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertTrue((self.root / "evaluation-checkpoint.pt").exists())
        self.assertEqual((self.root / "executed.jsonl").read_text().splitlines()[-1], "final_evaluation")

    def test_memory_is_still_monitored_after_graceful_stop_request(self):
        self.worker.write_text("import pathlib, signal, sys, time\n"
                               "root = pathlib.Path(sys.argv[1])\n"
                               "signal.signal(signal.SIGTERM, lambda *args: (root / 'stop-requested').write_text('yes'))\n"
                               "(root / 'ready').write_text('yes')\n"
                               "while True: time.sleep(0.01)\n")
        def memory(_pid):
            if (self.root / "stop-requested").exists():
                return 26_000_000_000
            return 25_000_000_000 if (self.root / "ready").exists() else 1_000_000
        state = self.experiment(rss_sampler=memory).run()
        self.assertEqual(state["status"], "attention_required")
        self.assertEqual(state["attempts"][0]["stop_reason"], "memory_limit")
        self.assertTrue(state["attempts"][0]["forced_kill"])
        self.assertEqual(state["aggregate_sampled_peak_rss_bytes"], 26_000_000_000)

    def test_final_checkpoint_stays_immutable_after_later_training_replace(self):
        self.root.mkdir()
        source, target = self.root / "checkpoint.pt", self.root / "evaluation.pt"
        source.write_text("old trained weights")
        saved = freeze_checkpoint(source, target)
        replacement = self.root / "next.pt"
        replacement.write_text("new trained weights")
        os.replace(replacement, source)
        self.assertEqual(target.read_text(), "old trained weights")
        self.assertEqual(freeze_checkpoint(source, target), saved)

    def test_command_keeps_explicit_training_and_evaluation_contracts(self):
        experiment = Experiment(self.plan)
        experiment.state = {"training_seconds": 500}
        command = experiment.command("training", time.time() + 500)
        self.assertIn("--adopt-checkpoint", command)
        self.assertIn("26000000000", command)
        self.assertEqual(command[-len(self.plan["training_arguments"]):], self.plan["training_arguments"])
        final = experiment.command("final_evaluation", self.plan["deadline_epoch"])
        self.assertIn("network_only,search", final)
        self.assertIn("--compare-to", final)
        with self.assertRaises(ValueError):
            validate_plan({**self.plan, "training_arguments": [*self.plan["training_arguments"], "--full-campaign"]})
        with self.assertRaises(ValueError):
            validate_plan({**self.plan, "deadline_epoch": time.time() + 11 * 3600})

    def test_model_exports_are_selected_without_loading_full_recovery_files(self):
        experiment = Experiment(self.plan)
        models = self.root / "training/models"
        models.mkdir(parents=True, exist_ok=True)
        initial, final = models / "generation-000000.pt", models / "generation-000003.pt"
        initial.write_bytes(b"initial small policies")
        final.write_bytes(b"latest small policies")
        (models.parent / "manifest.json").write_text(json.dumps({"latest_model_export": {
            "path": "models/generation-000003.pt", "bytes": final.stat().st_size, "generation": 3}}))
        command = experiment.command("initial_evaluation", self.plan["deadline_epoch"])
        self.assertEqual(command[command.index("--checkpoint") + 1], str(initial))
        self.assertEqual(experiment.evaluation_source(initial=False), final)
        # No initial.pt or checkpoint.pt is needed merely to select evaluation weights.
        self.assertFalse((models.parent / "checkpoint.pt").exists())
        final.unlink()
        with self.assertRaisesRegex(ValueError, "Declared model export is missing"):
            experiment.evaluation_source(initial=False)

    def test_final_freeze_uses_independently_valid_latest_model_export(self):
        script = self.worker.read_text().replace(
            "assert (root / 'evaluation-checkpoint.pt').read_text() == 'trained weights'",
            "assert (root / 'evaluation-checkpoint.pt').read_text() == 'trained small policies'")
        script = script.replace("    (training / 'checkpoint.pt').write_text('trained weights')",
            "    (training / 'checkpoint.pt').write_text('older recovery weights')\n"
            "    models = training / 'models'\n"
            "    models.mkdir(exist_ok=True)\n"
            "    target = models / 'generation-000001.pt'\n"
            "    target.write_text('trained small policies')\n"
            "    (training / 'manifest.json').write_text(json.dumps({'latest_model_export': "
            "{'path': 'models/generation-000001.pt', 'bytes': target.stat().st_size, 'generation': 1}}))")
        self.worker.write_text(script)
        state = self.experiment().run()
        self.assertEqual(state["status"], "completed")
        self.assertEqual((self.root / "evaluation-checkpoint.pt").read_text(), "trained small policies")
        self.assertEqual(state["evaluation_model_source"], "training/models/generation-000001.pt")

    def test_frozen_runtime_inventory_and_native_binary_are_verified(self):
        runtime = self.directory / "frozen-runtime"
        runtime.mkdir()
        (runtime / "runner.py").write_text("print('frozen source')\n")
        (runtime / "gwrl_cpp.so").write_text("frozen native binary")
        manifest = self.directory / "runtime-manifest.json"
        manifest.write_text(json.dumps({"files": {path.name: digest(path) for path in runtime.iterdir()}}))
        plan = {**self.plan, "working_directory": str(runtime), "runtime_manifest_path": str(manifest),
                "runtime_manifest_sha256": digest(manifest)}
        self.assertEqual(verify_runtime_manifest(plan), digest(manifest))
        (runtime / "gwrl_cpp.so").write_text("changed binary")
        with self.assertRaisesRegex(ValueError, "file changed"):
            verify_runtime_manifest(plan)
        (runtime / "unexpected.py").write_text("changed import inventory")
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            verify_runtime_manifest(plan)

    def test_expired_initial_evaluation_without_contract_stops_before_training(self):
        experiment = self.experiment()
        original = self.worker.read_text()
        self.worker.write_text(original.replace("if stage in ('initial_evaluation','final_evaluation'):",
            "if stage == 'initial_evaluation': raise ValueError('interrupted before evaluation plan')\n"
            "if stage in ('initial_evaluation','final_evaluation'):"))
        state = experiment.run()
        self.assertEqual(state["status"], "attention_required")
        path = self.root / "pipeline-state.json"
        saved = json.loads(path.read_text())
        saved["stage_deadlines"]["initial_evaluation"] = time.time() - 1
        path.write_text(json.dumps(saved))
        self.worker.write_text(original)
        again = self.experiment().run()
        self.assertEqual(again["status"], "attention_required")
        self.assertFalse((self.root / "training-control").exists())

    def test_forced_training_deadline_uses_last_atomic_checkpoint_for_final_evaluation(self):
        original = self.worker.read_text()
        self.worker.write_text(original.replace(
            "(control / 'state.json').write_text(json.dumps({'status':'time_budget_exhausted'}))",
            "(control / 'state.json').write_text(json.dumps({'status':'running'}))\n"
            "    import signal, time\n"
            "    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "    while True: time.sleep(0.01)"))
        self.plan["shutdown_seconds"] = 0.03
        experiment = self.experiment()
        original_deadline = experiment.stage_deadline
        def deadline(stage):
            if stage == "training":
                experiment.state["training_seconds"] = 0.15
                experiment.state["stage_deadlines"][stage] = time.time() + 0.15
                return experiment.state["stage_deadlines"][stage]
            return original_deadline(stage)
        experiment.stage_deadline = deadline
        state = experiment.run()
        self.assertEqual(state["status"], "completed")
        self.assertTrue(any(event["kind"] == "training_shutdown_cut_off" for event in state["events"]))
        self.assertEqual((self.root / "evaluation-checkpoint.pt").read_text(), "trained weights")

    def test_requested_pause_preserves_initial_checkpoint_and_resumes_next_stage(self):
        original = self.worker.read_text()
        self.worker.write_text("import json, pathlib, signal, sys, time\n"
                               "root = pathlib.Path(sys.argv[1])\n"
                               "training = root / 'training'\n"
                               "training.mkdir()\n"
                               "def stop(*args):\n"
                               "    (training / 'initial.pt').write_text('initial weights')\n"
                               "    (training / 'checkpoint.pt').write_text('unfinished games')\n"
                               "    sys.exit(130)\n"
                               "signal.signal(signal.SIGTERM, stop)\n"
                               "(root / 'ready').write_text('yes')\n"
                               "while True: time.sleep(0.01)\n")
        experiment = None
        def memory(_pid):
            if (self.root / "ready").exists():
                experiment.request_stop(signal.SIGTERM, None)
            return 1_000_000
        experiment = self.experiment(rss_sampler=memory)
        state = experiment.run()
        self.assertEqual(state["status"], "interrupted")
        self.assertTrue((self.root / "training/checkpoint.pt").is_file())
        self.worker.write_text(original)
        again = self.experiment().run()
        self.assertEqual(again["status"], "completed")
        self.assertEqual(sum(attempt["stage"] == "initialize" for attempt in again["attempts"]), 1)

    def test_real_independent_guardian_starts_before_stages_and_finishes_with_pipeline(self):
        tools = self.directory / "tools"
        tools.mkdir()
        source = Path(__file__).resolve().parents[1] / "tools/campaign_deadline_guardian.py"
        shutil.copyfile(source, tools / source.name)
        experiment = Experiment(self.plan, command_builder=self.command, rss_sampler=lambda _pid: 1_000_000)
        try:
            state = experiment.run()
            self.assertEqual(state["status"], "completed")
            self.assertTrue(any(event["kind"] == "deadline_guardian_started" for event in state["events"]))
            experiment.guardian_process.wait(timeout=5)
            guardian = json.loads((self.root / "guardian-state.json").read_text())
            self.assertEqual(guardian["status"], "completed")
            self.assertEqual(guardian["deadline_epoch"], self.plan["deadline_epoch"])
        finally:
            if experiment.guardian_process is not None and experiment.guardian_process.poll() is None:
                experiment.guardian_process.kill()
                experiment.guardian_process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
