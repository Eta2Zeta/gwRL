"""Compatibility proof helpers inspect saved states without executing a game."""
from __future__ import annotations

import copy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

import gwrl_cpp
from studies.campaign.curriculum import make_env
from studies.campaign.features import default_zone_spec, make_zone_input
from studies.campaign.run import RunConfig
from studies.shared.multiplayer_mcts import PLAYERS
from tools.verify_campaign_continuation import (FEATURE_FUNCTIONS, ROOT, ast_feature_bindings, ast_functions,
    canonical, audit_legacy_runtime_manifest, core_digest, digest_file, environment_record, migrated_payload,
    sample_groups, validate_output_paths, verify_sample, zone_digest)


class ContinuationProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = make_env(17, calendar_rounds=3)

    def test_active_record_digests_the_zone_input_without_changing_the_game(self):
        env = make_env(1951, calendar_rounds=3)
        passes = [action for action in env.legal_actions() if action.kind == "pass_interrupt"]
        self.assertTrue(passes)
        env.apply_action(passes[0])
        original = env.serialize()
        record = environment_record(env)
        self.assertEqual(env.serialize(), original)
        self.assertEqual(json.loads(canonical(record)), record)  # The legacy witness sends it as JSON.
        self.assertEqual(record["input_sha256"], zone_digest(make_zone_input(env, env.legal_actions())))
        restored = self.template.clone(); restored.restore(original)
        self.assertEqual(canonical(environment_record(restored)), canonical(record))
        opening = environment_record(make_env(1951, calendar_rounds=3))
        self.assertNotEqual(opening["input_sha256"], record["input_sha256"])
        self.assertNotEqual(opening["observation_sha256"], record["observation_sha256"])

    def test_saved_rows_are_read_against_the_current_layout_owner_and_menu(self):
        spec, env = default_zone_spec(), self.template.clone()
        actions = env.legal_actions()
        zone = make_zone_input(env, actions)
        sample = {"input": zone, "owner": env.current_decision_player(), "policy": [1 / len(actions)] * len(actions),
                  "rollout_version": "unit-test"}
        self.assertEqual(verify_sample(sample, spec, "replay[0]"), (zone_digest(zone), zone_digest(zone)))
        other = next(player for player in PLAYERS if player != sample["owner"])
        broken = zone.arrays(); broken["zone_column"][0] = spec.zone_columns
        for changed, message in (({**sample, "owner": other}, "ownership changed at replay"),
                                 ({**sample, "policy": sample["policy"][:-1]}, "complete legal menu"),
                                 ({**sample, "input": {"schema": "campaign-neural-input-v1"}}, "Unsupported"),
                                 ({**sample, "input": gwrl_cpp.campaign_zone_input("another-layout", zone.arrays())},
                                  "Unsupported"),
                                 ({**sample, "input": gwrl_cpp.campaign_zone_input(zone.version, broken)}, "out of range")):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                verify_sample(changed, spec, "replay[0]")

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
        proof = {"status": "verified", "saved_input_sha256": "same", "rebuilt_input_sha256": "same",
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
        for invalid in ({**proof, "status": "partial"}, {**proof, "rebuilt_input_sha256": "changed"}):
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

    def test_audit_pins_definitions_the_current_input_module_has(self):
        path = ROOT / "studies/campaign/features.py"
        self.assertEqual(set(ast_functions(path, FEATURE_FUNCTIONS)), set(FEATURE_FUNCTIONS))
        self.assertTrue(ast_feature_bindings(path))


if __name__ == "__main__":
    unittest.main()
