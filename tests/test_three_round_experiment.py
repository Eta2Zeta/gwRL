"""The long-run pipeline tested with tiny child programs, never game training."""
from __future__ import annotations

import json
import copy
import os
from pathlib import Path
import signal
import shutil
import sys
import tempfile
import time
import unittest

from tools.run_three_round_experiment import (
    Experiment, STAGES, digest, fingerprint, freeze_checkpoint, validate_plan,
    verify_runtime_manifest, training_completion_contract, evaluation_completion_contract,
)


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

    def strict_plan(self):
        self.plan.update(expected_training_episodes=60, require_terminal_evaluation=True)
        self.plan["training_arguments"] = ["--calendar-rounds", "3", "--complete-episodes",
            "--batches", "15", "--max-episodes", "60", "--parallel-envs", "4", "--threads", "4", "--cpu-budget", "11"]
        return self.plan

    @staticmethod
    def terminal_clock():
        return {"completed_rounds": 3, "round_index": 2, "nation_index": 3,
                "phase": "place_units", "income_collected": True}

    def training_fixture(self, episodes=60):
        batches = episodes // 4
        return {"counters": {"episodes": episodes, "updates": batches, "batches": batches},
                "runner": {"updates": [{"rollout": {"bootstrap_samples": 0},
                    "episodes": [{"terminal": True, "clock": self.terminal_clock()} for _ in range(4)]}
                    for _ in range(batches)]}}

    def evaluation_fixture(self, *, final=False):
        plan = {"evaluation": {"seeds": self.plan["heldout_seeds"], "modes": ["network_only", "search"]}}
        key = fingerprint(plan)
        records = []
        for mode in plan["evaluation"]["modes"]:
            for seed in self.plan["heldout_seeds"]:
                records.append({"mode": mode, "seed": seed, "contract_sha256": key,
                    "result": {"territorial_tracking_schema": "campaign-national-chinese-possession-tracking-v2",
                        "terminal_games": 1, "truncated_games": 0,
                        "games": [{"seed": seed, "terminal": True, "truncated": False, "stop_reason": "terminal",
                            "clock": self.terminal_clock(), "observed_terminal_returns": [1., 2., 3.],
                            "completed_turns_at_stop": {"ccp": 3, "mongolia": 3, "japan": 3, "kmt": 3},
                            "dadao_chinese_home_country": {"nation": "dadao", "terminal": True,
                                "at_stop": {}, "newly_held": {}, "events": []}}]}})
        report = {"status": "completed", "contract_sha256": key, "records": records,
            "by_mode": {mode: {"terminal_games": len(self.plan["heldout_seeds"]), "truncated_games": 0}
                        for mode in plan["evaluation"]["modes"]}}
        if final:
            report["paired_comparison"] = {"by_mode": {mode: {"complete_pairs": len(self.plan["heldout_seeds"])}
                for mode in plan["evaluation"]["modes"]}}
        return plan, report

    def write_evaluation_fixture(self, directory, plan, report):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "plan.json").write_text(json.dumps(plan))
        (directory / "report.json").write_text(json.dumps(report))

    def install_strict_worker(self, *, episodes=60, initial_terminal=True, final_terminal=True):
        self.strict_plan()
        (self.directory / "training-fixture.json").write_text(json.dumps(self.training_fixture(episodes)))
        for name, terminal in (("initial", initial_terminal), ("final", final_terminal)):
            plan, report = self.evaluation_fixture(final=name == "final")
            if not terminal:
                report["records"][0]["result"]["games"][0]["terminal"] = False
            self.write_evaluation_fixture(self.directory / ("fixture-" + name), plan, report)
        self.worker.write_text(self.worker.read_text() +
            "\nif stage == 'training':\n"
            "    (training / 'manifest.json').write_text((root.parent / 'training-fixture.json').read_text())\n"
            "if stage in ('initial_evaluation', 'final_evaluation'):\n"
            "    name = 'initial' if stage == 'initial_evaluation' else 'final'\n"
            "    fixture = root.parent / ('fixture-' + name)\n"
            "    output = root / ('evaluation-' + name)\n"
            "    for name in ('plan.json', 'report.json'): (output / name).write_text((fixture / name).read_text())\n")

    def test_strict_plan_requires_matching_count_and_boolean_evaluation_flag(self):
        self.strict_plan()
        validate_plan(self.plan)
        for invalid in (True, 0, -1, 60.0):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_plan({**self.plan, "expected_training_episodes": invalid})
        with self.assertRaisesRegex(ValueError, "match --max-episodes"):
            validate_plan({**self.plan, "expected_training_episodes": 64})
        with self.assertRaisesRegex(ValueError, "boolean"):
            validate_plan({**self.plan, "require_terminal_evaluation": 1})
        bad = self.plan["training_arguments"].copy()
        bad[bad.index("--batches") + 1] = "14"
        with self.assertRaisesRegex(ValueError, "batch allowance"):
            validate_plan({**self.plan, "training_arguments": bad})

    def test_training_completion_requires_exact_terminals_updates_and_zero_bootstraps(self):
        self.strict_plan()
        fixture = self.training_fixture()
        self.assertTrue(training_completion_contract(self.plan, fixture)["complete"])
        changes = [lambda value: value["counters"].update(episodes=56),
            lambda value: value["counters"].update(updates=14),
            lambda value: value["runner"]["updates"][0]["rollout"].update(bootstrap_samples=1),
            lambda value: value["runner"]["updates"][0]["episodes"][0].update(terminal=False),
            lambda value: value["runner"]["updates"][0]["episodes"][0]["clock"].update(completed_rounds=2)]
        for change in changes:
            value = copy.deepcopy(fixture)
            change(value)
            self.assertFalse(training_completion_contract(self.plan, value)["complete"])

    def test_strict_evaluation_rejects_complete_record_lists_with_invalid_terminal_proof(self):
        self.strict_plan()
        directory = self.root / "evaluation-final"
        plan, fixture = self.evaluation_fixture(final=True)
        self.write_evaluation_fixture(directory, plan, fixture)
        self.assertTrue(evaluation_completion_contract(self.plan, directory, final=True)["complete"])
        changes = [lambda value: value["records"][0]["result"]["games"][0].update(terminal=False),
            lambda value: value["records"][0]["result"]["games"][0]["clock"].update(completed_rounds=2),
            lambda value: value["records"][0]["result"]["games"][0].update(observed_terminal_returns=[None] * 3),
            lambda value: value["records"].append(copy.deepcopy(value["records"][0])),
            lambda value: value["records"][0].update(contract_sha256="different"),
            lambda value: value["records"][0]["result"].update(territorial_tracking_schema="old"),
            lambda value: value["paired_comparison"]["by_mode"]["search"].update(complete_pairs=0)]
        for change in changes:
            value = copy.deepcopy(fixture)
            change(value)
            self.write_evaluation_fixture(directory, plan, value)
            self.assertFalse(evaluation_completion_contract(self.plan, directory, final=True)["complete"])

    def test_strict_success_requires_all_sixty_games_and_both_terminal_evaluations(self):
        self.install_strict_worker()
        state = self.experiment().run()
        self.assertEqual(state["status"], "completed")
        self.assertTrue(state["goal_achieved"])
        self.assertTrue(all(value["complete"] for value in state["completion_contracts"].values()))

    def test_strict_partial_training_is_evaluated_but_never_reported_as_goal_complete(self):
        self.install_strict_worker(episodes=4)
        state = self.experiment().run()
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertFalse(state["goal_achieved"])
        self.assertFalse(state["completion_contracts"]["training"]["complete"])
        self.assertTrue((self.root / "evaluation-final/report.json").exists())
        self.assertTrue((self.root / "training/checkpoint.pt").exists())

    def test_strict_nonterminal_initial_evaluation_blocks_training_with_concrete_reason(self):
        self.install_strict_worker(initial_terminal=False)
        state = self.experiment().run()
        self.assertEqual(state["status"], "attention_required")
        self.assertEqual(state["stage"], "initial_evaluation")
        self.assertFalse((self.root / "training-control").exists())
        self.assertIn("genuine three-round terminal", state["events"][-1]["reason"])

    def test_strict_nonterminal_final_evaluation_cannot_mark_completed(self):
        self.install_strict_worker(final_terminal=False)
        state = self.experiment().run()
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertFalse(state["goal_achieved"])
        self.assertFalse(state["completion_contracts"]["final_evaluation"]["complete"])


if __name__ == "__main__":
    unittest.main()
