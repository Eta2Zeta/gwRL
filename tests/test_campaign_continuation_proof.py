"""Compatibility proof helpers inspect saved states without executing a game."""
from __future__ import annotations

import copy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from studies.campaign.curriculum import make_env
from studies.campaign.features import make_input
from studies.campaign.run import RunConfig
from tools.verify_campaign_continuation import (FEATURE_FUNCTIONS, ast_functions, canonical,
    audit_legacy_runtime_manifest, core_digest, digest_file, migrated_payload, rehydrate_public_state,
    sample_groups, validate_output_paths)


class ContinuationProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = make_env(17, calendar_rounds=3)

    def test_rehydration_matches_full_public_input_and_scheduler_without_borrowing_execution_rng(self):
        env = make_env(1951, calendar_rounds=3)
        actions = env.legal_actions()
        passes = [action for action in actions if action.kind == "pass_interrupt"]
        self.assertTrue(passes)
        env.apply_action(passes[0])
        features = make_input(env, env.legal_actions())
        original = env.serialize()
        base = json.loads(self.template.raw.serialize())
        synthetic = rehydrate_public_state(self.template, features["observation"], {}, base_engine=base)
        self.assertEqual(make_input(synthetic, synthetic.legal_actions()), features)
        self.assertEqual(synthetic.planning_key(), env.planning_key())
        self.assertNotEqual(json.loads(synthetic.raw.serialize())["random"],
                            json.loads(env.raw.serialize())["random"])
        self.assertEqual(env.serialize(), original)
        self.assertEqual(base, json.loads(self.template.raw.serialize()))

    def test_rehydration_rejects_stale_scheduler_and_execution_fields(self):
        observation = make_input(self.template, self.template.legal_actions())["observation"]
        for mutation in (
            lambda value: value["interrupt_scheduler"].update(passed=["axis", "axis"]),
            lambda value: value["interrupt_scheduler"].update(order=["axis"] * 3),
            lambda value: value["state"].update(history=[]),
            lambda value: value["state"].update(definition_fingerprint="borrowed"),
        ):
            value = json.loads(canonical(observation)); mutation(value)
            with self.assertRaises(ValueError):
                rehydrate_public_state(self.template, value, {})

    def test_operational_migration_preserves_learner_and_every_nonoperational_runner_field(self):
        config = asdict(RunConfig(seed=1951, calendar_rounds=3, batches=10000, complete_episodes=True,
                                  checkpoint_every_waves=16, parallel_envs=4))
        config.pop("max_episodes"); config.pop("checkpoint_interval_seconds")
        learner = {"generation": 15, "counters": {"episodes": 60, "updates": 15},
                   "optimizers": {"axis": {"step": 240}}, "pending": [],
                   "parallel_pending": [[{"policy": [.2, .8]}]], "rng": {"environment": [1, 2, 3]}}
        payload = {"schema": "campaign-foreground-run-v1", "learner": learner,
                   "runner": {"config": config, "runtime_source_sha256": {"old": "hash"},
                              "batch_index": 15, "wave_index": 192, "active_episode_seeds": [9, 10, 11, 12],
                              "updates": [{"kept": True}], "total_waves": 6000}}
        before = copy.deepcopy(payload)
        hashes = {"new": "hash"}
        proof = {"status": "verified", "saved_input_sha256": "same", "regenerated_input_sha256": "same",
                 "audit": {"current_runtime_source_sha256": hashes}}
        migrated = migrated_payload(payload, proof, hashes)
        self.assertIs(migrated["learner"], learner)
        self.assertEqual(payload, before)
        self.assertEqual(migrated["runner"]["config"]["batches"], 30)
        self.assertEqual(migrated["runner"]["config"]["max_episodes"], 120)
        self.assertIsNone(migrated["runner"]["config"]["checkpoint_every_waves"])
        self.assertEqual(migrated["runner"]["config"]["checkpoint_interval_seconds"], 1800.)
        for name in set(payload["runner"]) - {"config", "runtime_source_sha256"}:
            self.assertEqual(migrated["runner"][name], payload["runner"][name])
        for invalid in ({**proof, "status": "partial"}, {**proof, "regenerated_input_sha256": "changed"}):
            with self.assertRaises(ValueError): migrated_payload(payload, invalid, hashes)
        with self.assertRaises(ValueError): migrated_payload(payload, proof, {"new": "changed"})

    def test_row_groups_include_all_completed_and_unfinished_sources(self):
        groups = list(sample_groups({"replay": [1], "pending": [2], "batch_records": [3],
                                     "parallel_pending": [[4], [5]]}))
        self.assertEqual(groups, [("replay", [1]), ("pending", [2]), ("batch_records", [3]),
                                  ("parallel_pending[0]", [4]), ("parallel_pending[1]", [5])])
        self.assertNotEqual(core_digest({"zero": -0.0}), core_digest({"zero": 0.0}))

    def test_publication_paths_cannot_overwrite_original_experiment_or_each_other(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "original/runtime"
            source = root / "original/training/checkpoint.pt"
            report, target = root / "new/proof.json", root / "new/training/checkpoint.pt"
            validate_output_paths(source, legacy, report, target)
            for output in (source, root / "original/manifest.json", root / "original/runtime/source.py"):
                with self.assertRaises(ValueError):
                    validate_output_paths(source, legacy, output, target)
            with self.assertRaises(ValueError):
                validate_output_paths(source, legacy, report, report)

    def test_legacy_runtime_manifest_pins_native_bytes_and_complete_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime"; runtime.mkdir()
            native, code = runtime / "engine.so", runtime / "source.py"
            native.write_bytes(b"pinned native"); code.write_text("# pinned source\n")
            manifest = root / "runtime-manifest.json"
            files = {path.name: digest_file(path) for path in (native, code)}
            manifest.write_text(json.dumps({"source_commit": "revision", "files": files}))
            (root / "pipeline-plan.json").write_text(json.dumps({"source_commit": "revision",
                "runtime_manifest_path": str(manifest), "runtime_manifest_sha256": digest_file(manifest)}))
            self.assertEqual(audit_legacy_runtime_manifest(runtime)["native_files"], {"engine.so": files["engine.so"]})
            native.write_bytes(b"wrong native")
            with self.assertRaisesRegex(ValueError, "byte changed"):
                audit_legacy_runtime_manifest(runtime)
            native.write_bytes(b"pinned native")
            (runtime / "untracked.py").write_text("# unexpected code\n")
            with self.assertRaisesRegex(ValueError, "inventory"):
                audit_legacy_runtime_manifest(runtime)

    def test_feature_ast_audit_catches_changed_semantics_but_ignores_formatting(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "features.py"
            path.write_text("\n".join(f"def {name}(x): return x + 1" for name in FEATURE_FUNCTIONS))
            first = ast_functions(path, FEATURE_FUNCTIONS)
            path.write_text("\n\n".join(f"def {name}(x):\n    # comment\n    return x + 1\n" for name in FEATURE_FUNCTIONS))
            self.assertEqual(first, ast_functions(path, FEATURE_FUNCTIONS))
            path.write_text(path.read_text().replace("return x + 1", "return x + 2", 1))
            self.assertNotEqual(first, ast_functions(path, FEATURE_FUNCTIONS))


if __name__ == "__main__":
    unittest.main()
