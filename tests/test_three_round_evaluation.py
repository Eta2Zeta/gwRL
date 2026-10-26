"""Paired outcomes and durable per-game evaluation reuse without training."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import torch

from test_campaign_evaluation import CountingEvaluator, EvaluationEnv
from tools.evaluate_three_round_campaign import execution_runtime, main, paired_comparison, summarize
from studies.campaign.evaluation import evaluate
from studies.campaign.run import RunConfig


class ExpansionEnv(EvaluationEnv):
    def context(self):
        value = super().context()
        value["factions"] = {"kmt": {"home_country_known": True, "home_country": ["land_a", "land_b"]}}
        return value


class ThreeRoundEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.checkpoint = self.directory / "checkpoint.pt"
        self.checkpoint.write_bytes(b"test-only trusted checkpoint stub")
        self.output = self.directory / "evaluation"
        self.loaded = {"config": asdict(RunConfig(calendar_rounds=3)),
                                  "training_environment_seeds": [1936, 1937],
                                  "runtime_source_sha256": {"fixture": "frozen"},
                       "models": {player: torch.nn.Linear(1, 1) for player in ("axis", "allies", "comintern")},
                       "generation": 0, "source_schema": "campaign-evaluation-models-v1"}
        self.versions = {"axis": "initial-axis", "allies": "initial-allies", "comintern": "initial-comintern"}
        self.stack = ExitStack()
        self.stack.enter_context(patch("torch.set_num_interop_threads"))
        self.stack.enter_context(patch("torch.set_num_threads"))
        self.stack.enter_context(patch("studies.campaign.model_export.load_evaluation_models",
            side_effect=lambda _path: {**self.loaded, "model_versions": self.versions}))
        self.stack.enter_context(patch("studies.campaign.curriculum.make_env", side_effect=lambda seed, **kw: ExpansionEnv(seed)))
        self.stack.enter_context(patch("studies.campaign.curriculum.task_manifest", return_value={"calendar_rounds": 3}))
        self.policy_factory = self.stack.enter_context(patch("studies.campaign.device_runtime.runtime_policy_for_device", return_value=None))
        self.evaluator_factory = self.stack.enter_context(patch("studies.campaign.neural.NeuralEvaluator", side_effect=lambda *args, **kw: CountingEvaluator()))

    def tearDown(self):
        self.stack.close()
        self.temporary.cleanup()

    def arguments(self, output=None):
        return ["--checkpoint", str(self.checkpoint), "--output-dir", str(output or self.output),
                "--seeds", "1009,1013", "--modes", "network_only", "--max-transitions", "5"]

    def test_completed_seed_results_are_reused_and_weight_mismatch_is_rejected(self):
        self.assertEqual(main(self.arguments()), 0)
        report = json.loads((self.output / "report.json").read_text())
        self.assertEqual(report["by_mode"]["network_only"]["terminal_games"], 2)
        self.assertEqual(report["by_mode"]["network_only"]["newly_held_chinese_land"]["mean"], 1)
        first = (self.output / "network_only-1009.json").read_bytes()
        with patch("studies.campaign.evaluation.evaluate", side_effect=AssertionError("No completed game rerun")):
            self.assertEqual(main(self.arguments()), 0)
        self.assertEqual((self.output / "network_only-1009.json").read_bytes(), first)
        self.checkpoint.write_bytes(b"different weights")
        with self.assertRaisesRegex(ValueError, "different weights"):
            main(self.arguments())

    def test_interrupt_diagnostics_are_not_scored_or_mistaken_for_completed_work(self):
        def interrupt(*args, **kwargs):
            kwargs["stop_requested"] = lambda: True
            return evaluate(*args, **kwargs)

        with patch("studies.campaign.evaluation.evaluate", side_effect=interrupt):
            self.assertEqual(main(self.arguments()), 130)
        report = json.loads((self.output / "report.json").read_text())
        self.assertEqual(report["status"], "interrupted")
        self.assertEqual(report["by_mode"]["network_only"]["terminal_games"], 0)
        self.assertFalse((self.output / "network_only-1009.json").exists())
        partial = json.loads((self.output / "interrupted-network_only-1009.json").read_text())
        self.assertIsNone(partial["result"]["games"][0]["observed_terminal_returns"])
        self.assertEqual(main(self.arguments()), 0)
        self.assertTrue((self.output / "network_only-1009.json").exists())

    def test_paired_model_changes_allowed_but_different_evaluation_budget_rejected(self):
        self.assertEqual(main(self.arguments()), 0)
        self.versions = {player: value + "-trained" for player, value in self.versions.items()}
        self.checkpoint.write_bytes(b"trained checkpoint")
        final = self.directory / "final"
        self.assertEqual(main([*self.arguments(final), "--compare-to", str(self.output)]), 0)
        report = json.loads((final / "report.json").read_text())
        paired = report["paired_comparison"]["by_mode"]["network_only"]
        self.assertEqual(paired["complete_pairs"], 2)
        self.assertEqual(paired["delta_statistics"]["newly_held_chinese_ipp"]["mean"], 0)
        different = [*self.arguments(self.directory / "different"), "--compare-to", str(self.output),
                     "--simulations", "17"]
        with self.assertRaisesRegex(ValueError, "identical task"):
            main(different)

    def test_training_seed_overlap_is_rejected_before_any_evaluation(self):
        self.loaded["training_environment_seeds"].append(1009)
        with self.assertRaisesRegex(ValueError, "overlap training"):
            main(self.arguments())
        self.assertFalse(self.output.exists())

    def test_actual_model_device_selects_one_persistent_policy_for_all_games(self):
        class Model:
            def parameters(self):
                return iter((SimpleNamespace(device=torch.device("mps"), dtype=torch.float32),))
        self.loaded["models"] = {player: Model() for player in self.versions}
        # Config deliberately remains CPU: placement must come from the model.
        policy = Mock()
        self.policy_factory.return_value = policy
        self.assertEqual(main(self.arguments()), 0)
        self.policy_factory.assert_called_once_with("mps")
        self.evaluator_factory.assert_called_once()
        self.assertIs(self.evaluator_factory.call_args.kwargs["runtime_policy"], policy)
        plan = json.loads((self.output / "plan.json").read_text())
        runtime = plan["evaluation"]["execution_runtime"]
        self.assertEqual(runtime["neural_device"], "mps")
        self.assertEqual(runtime["torch_version"], str(torch.__version__))
        self.assertEqual(set(runtime["model_devices"].values()), {"mps"})

    def test_changed_device_or_torch_runtime_cannot_reuse_or_pair_results(self):
        self.assertEqual(main(self.arguments()), 0)
        first = (self.output / "network_only-1009.json").read_bytes()
        runtime = execution_runtime(self.loaded["models"])
        for index, (field, value) in enumerate((("neural_device", "mps"), ("torch_version", "different-torch"))):
            changed = {**runtime, field: value}
            with self.subTest(field=field), patch("tools.evaluate_three_round_campaign.execution_runtime", return_value=changed):
                with self.assertRaisesRegex(ValueError, "execution runtime"):
                    main(self.arguments())
                with self.assertRaisesRegex(ValueError, "execution runtime"):
                    main([*self.arguments(self.directory / f"different-runtime-{index}"), "--compare-to", str(self.output)])
            self.assertEqual((self.output / "network_only-1009.json").read_bytes(), first)

    def test_legacy_runtime_unknown_plans_are_explicitly_rejected_and_preserved(self):
        self.assertEqual(main(self.arguments()), 0)
        path = self.output / "plan.json"
        old = json.loads(path.read_text())
        del old["evaluation"]["execution_runtime"]
        path.write_text(json.dumps(old))
        original = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Legacy.*execution runtime identity"):
            main(self.arguments())
        with self.assertRaisesRegex(ValueError, "Legacy.*execution runtime identity"):
            main([*self.arguments(self.directory / "legacy-pair"), "--compare-to", str(self.output)])
        self.assertEqual(path.read_bytes(), original)

    def test_unfinished_pair_has_no_delta_or_summary_terminal_metric(self):
        result = evaluate(ExpansionEnv, CountingEvaluator(), target_player="axis", seeds=[1009],
                          selection_mode="network_only", track_japan=True, max_transitions=5)
        initial = {"mode": "network_only", "seed": 1009, "result": result}
        final = copy.deepcopy(initial)
        game = final["result"]["games"][0]
        game.update(terminal=False, stop_reason="transition_budget", observed_terminal_returns=None)
        pair = paired_comparison([final], [initial])
        self.assertIsNone(pair["pairs"][0]["delta"])
        self.assertEqual(pair["by_mode"]["network_only"]["complete_pairs"], 0)
        summary = summarize([final])
        self.assertEqual(summary["terminal_games"], 0)
        self.assertEqual(summary["newly_held_chinese_ipp"]["n"], 0)


if __name__ == "__main__":
    unittest.main()
