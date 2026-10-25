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
from unittest.mock import patch

from test_campaign_evaluation import CountingEvaluator, EvaluationEnv
from tools.evaluate_three_round_campaign import main, paired_comparison, summarize
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
        self.loaded = {"runner": {"config": asdict(RunConfig(calendar_rounds=3)),
                                  "training_environment_seeds": [1936, 1937],
                                  "runtime_source_sha256": {"fixture": "frozen"}},
                       "learner": {"fixture": "frozen"}}
        self.versions = {"axis": "initial-axis", "allies": "initial-allies", "comintern": "initial-comintern"}
        self.learner = SimpleNamespace(models={}, restore=lambda *args, **kwargs: None,
                                       model_versions=lambda: self.versions)
        self.stack = ExitStack()
        self.stack.enter_context(patch("torch.set_num_interop_threads"))
        self.stack.enter_context(patch("torch.set_num_threads"))
        self.stack.enter_context(patch("studies.campaign.run._read", return_value=self.loaded))
        self.stack.enter_context(patch("studies.campaign.run._learner", return_value=self.learner))
        self.stack.enter_context(patch("studies.campaign.curriculum.make_env", side_effect=lambda seed, **kw: ExpansionEnv(seed)))
        self.stack.enter_context(patch("studies.campaign.curriculum.task_manifest", return_value={"calendar_rounds": 3}))
        self.stack.enter_context(patch("studies.campaign.neural.NeuralEvaluator", side_effect=lambda *args, **kw: CountingEvaluator()))

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
        self.loaded["runner"]["training_environment_seeds"].append(1009)
        with self.assertRaisesRegex(ValueError, "overlap training"):
            main(self.arguments())
        self.assertFalse(self.output.exists())

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
