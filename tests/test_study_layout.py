"""Check study organization and preserved results without running training."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from studies.shared import paths
from studies.shared.policy_value_model import LegalActionPolicyValueNet, PolicyValueModelConfig


STUDY_NAMES = ("composition", "mini_japan_two_turn")


class StudyLayoutTests(unittest.TestCase):
    def test_default_run_paths_are_absolute_and_separate_from_preserved_results(self):
        for study_name in STUDY_NAMES:
            with self.subTest(study=study_name):
                run_path = paths.default_run_dir(study_name)
                self.assertTrue(run_path.is_absolute())
                self.assertEqual(run_path.parent, paths.REPO_ROOT / "studies" / study_name / "runs")
                self.assertNotIn("results", run_path.relative_to(paths.STUDIES_ROOT).parts)

    def test_choosing_fresh_run_paths_does_not_create_directories(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory).resolve()
            with patch.object(paths, "STUDIES_ROOT", temporary_root):
                chosen_paths = [
                    paths.default_run_dir(study_name)
                    for study_name in STUDY_NAMES
                    for _ in range(2)
                ]
            self.assertEqual(len(chosen_paths), len(set(chosen_paths)))
            self.assertEqual(list(temporary_root.iterdir()), [])
            for run_path in chosen_paths:
                self.assertFalse(run_path.exists())

    def test_unknown_or_escaping_study_names_are_rejected(self):
        for study_name in ("unknown", "../results", "/tmp", "composition/results"):
            with self.subTest(study=study_name), self.assertRaises(ValueError):
                paths.default_run_dir(study_name)

    def test_mini_japan_scenario_still_has_two_turn_horizon(self):
        self.assertTrue(paths.MINI_JAPAN_SCENARIO.is_absolute())
        self.assertTrue(paths.MINI_JAPAN_SCENARIO.is_file())
        scenario = json.loads(paths.MINI_JAPAN_SCENARIO.read_text(encoding="utf-8"))
        self.assertEqual(scenario["turn_limit_per_nation"], 2)
        self.assertIn("Japan", scenario["turn_order"])

    def test_trainers_and_debug_tool_import_the_same_shared_model(self):
        module_names = (
            "studies.composition.train",
            "studies.mini_japan_two_turn.train",
            "studies.mini_japan_two_turn.tools.debug_mcts_trace",
        )
        for module_name in module_names:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertIs(module.LegalActionPolicyValueNet, LegalActionPolicyValueNet)
                self.assertIs(module.PolicyValueModelConfig, PolicyValueModelConfig)
                self.assertTrue(callable(module.main))

    def test_each_trainer_imports_its_own_search_implementation(self):
        composition_train = importlib.import_module("studies.composition.train")
        composition_search = importlib.import_module("studies.composition.mcts")
        japan_train = importlib.import_module("studies.mini_japan_two_turn.train")
        japan_search = importlib.import_module("studies.mini_japan_two_turn.mcts")
        self.assertIs(composition_train.run_mcts, composition_search.run_mcts)
        self.assertIs(japan_train.run_mcts, japan_search.run_mcts)
        self.assertIsNot(composition_train.run_mcts, japan_train.run_mcts)

    def assert_preserved_results(self, study_name, original_directory, expected_file_count):
        results_directory = paths.STUDIES_ROOT / study_name / "results"
        manifest = json.loads(
            (results_directory / "final_run_sha256.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["algorithm"], "sha256")
        self.assertEqual(manifest["original_directory"], original_directory)
        self.assertEqual(manifest["preserved_directory"], "final_run")
        self.assertEqual(len(manifest["files"]), expected_file_count)
        preserved_directory = results_directory / manifest["preserved_directory"]
        actual_files = {
            file_path.relative_to(preserved_directory).as_posix()
            for file_path in preserved_directory.rglob("*")
            if file_path.is_file()
        }
        self.assertEqual(actual_files, set(manifest["files"]))
        for filename, expected_digest in manifest["files"].items():
            with self.subTest(study=study_name, file=filename):
                relative_path = Path(filename)
                self.assertFalse(relative_path.is_absolute())
                self.assertNotIn("..", relative_path.parts)
                self.assertRegex(expected_digest, r"^[0-9a-f]{64}$")
                actual_digest = hashlib.sha256(
                    (preserved_directory / relative_path).read_bytes()
                ).hexdigest()
                self.assertEqual(actual_digest, expected_digest)

    def test_composition_final_result_files_match_original_hashes(self):
        self.assert_preserved_results("composition", "output/composition_alpha_zero", 7)

    def test_mini_japan_final_result_files_match_original_hashes(self):
        self.assert_preserved_results("mini_japan_two_turn", "output/japan_fpu_optimistic", 8)


if __name__ == "__main__":
    unittest.main()
