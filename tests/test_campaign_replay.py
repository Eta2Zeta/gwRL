from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from studies.campaign.baselines import baseline_distribution
from studies.campaign.curriculum import make_env, task_manifest
from studies.campaign.replay import (LiveReplay, apply_changes, digest, export_report, export_trace, frame_at,
                                     snapshot, state_changes, write_replay)
from studies.campaign import replay as replay_module


class CampaignReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Real rules and dice produce the fixture; synthetic search statistics
        # let us test identity/selection integrity without any neural inference.
        env = make_env(9182, calendar_rounds=1)
        cls.initial = snapshot(env)
        prepared = digest(env.serialize())
        cls.events = []
        cls.chance_events = []
        transitions = 0
        while not env.is_terminal():
            if transitions > 400:
                raise AssertionError("Replay fixture failed to complete its actual one-round game")
            before = digest(env.serialize())
            if env.decision_kind() == "chance":
                raw = json.loads(env.raw.serialize())
                env.resolve_chance()
                events = json.loads(env.raw.serialize())["state"]["history"][len(raw["state"]["history"]):]
                cls.chance_events.append(events)
                cls.events.append({"kind": "chance", "root": 0, "before": before, "after": digest(env.serialize())})
            else:
                actions = env.legal_actions()
                weights = baseline_distribution(env, actions)
                selected = max(range(len(actions)), key=weights.__getitem__)
                features = [action.features() for action in actions]
                result = {"action_ids": [action.id for action in actions], "action_features_sha256": digest(features),
                          "visit_counts": [int(index == selected) for index in range(len(actions))],
                          "policy": weights, "priors": [1 / len(actions)] * len(actions),
                          "values": [0., 0., 0.], "action_values": [[0., 0., 0.] for _ in actions]}
                cls.events.append({"kind": "search", "roots": [0], "before": [before], "results": [result],
                                   "configs": [{"simulations": 1, "max_depth": 1}]})
                env.apply_action(actions[selected])
                cls.events.append({"kind": "action", "root": 0, "before": before, "after": digest(env.serialize()),
                                   "action_id": actions[selected].id, "action_features": features[selected]})
            transitions += 1
        cls.final = snapshot(env)
        cls.report = {"schema": "campaign-scaling-benchmark-v1", "status": "completed",
                      "config": {"mode": "episode", "seed": 9182, "roots": 1, "calendar_rounds": 1},
                      "runtime_source_sha256": {}, "task": task_manifest(env), "prepared_state_sha256": [prepared],
                      "preparation": {"roots": [{"transitions": 0}]}, "model": {"training_updates": 0, "frozen": True},
                      "roots": [{"index": 0, "transitions": transitions, "clock": cls.final["clock"], "terminal": True,
                                 "observed_terminal_returns": list(env.returns())}]}

    def fixture(self, directory: str, events=None, report=None) -> Path:
        path = Path(directory) / "report.json"
        trace = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                        for row in (self.events if events is None else events))
        value = copy.deepcopy(self.report if report is None else report)
        value["verification_trace"] = {"event_count": len(self.events if events is None else events),
                                        "events_sha256": hashlib.sha256(trace.encode()).hexdigest()}
        path.write_text(json.dumps(value))
        path.with_suffix(".trace.jsonl").write_text(trace)
        return path

    def test_roundtrip_preserves_all_decisions_chance_and_final_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            replay = export_report(self.fixture(directory))
        self.assertEqual(replay["initial"], self.initial)
        self.assertEqual(frame_at(replay, len(replay["steps"])), self.final)
        self.assertTrue(replay["metadata"]["terminal"])
        self.assertTrue(replay["metadata"]["exact_replay_verified"])
        self.assertEqual(replay["metadata"]["training_updates"], 0)
        self.assertEqual(len(replay["steps"]), sum(row["kind"] != "search" for row in self.events))
        self.assertEqual([step["chance"]["events"] for step in replay["steps"] if step["kind"] == "chance"], self.chance_events)
        self.assertTrue(self.chance_events, "Fixture must exercise real dice")
        for step in replay["steps"]:
            if step["kind"] == "action":
                chosen = next(row for row in step["search"]["actions"] if row["id"] == step["action"]["id"])
                self.assertEqual(chosen["visits"], 1)
        # Seeking backwards reconstructs from the initial state and does not
        # mutate that state or the previously viewed final frame.
        self.assertEqual(frame_at(replay, 0), self.initial)
        self.assertEqual(frame_at(replay, len(replay["steps"])), self.final)

    def test_tampered_after_rng_hash_rejects_before_output_is_published(self):
        events = copy.deepcopy(self.events)
        events[1]["after"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = self.fixture(directory, events)
            output = Path(directory) / "viewer.json"
            with self.assertRaisesRegex(ValueError, "after-state or execution RNG"):
                write_replay(output, export_report(path))
            self.assertFalse(output.exists())

    def test_tampered_search_menu_and_payload_rejected(self):
        for field, value, message in (("action_ids", ["forged"], "action menu"),
                                      ("action_features_sha256", "0" * 64, "payload hash")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                events = copy.deepcopy(self.events)
                events[0]["results"][0][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    export_report(self.fixture(directory, events))

    def test_trace_integrity_and_rule_compatibility_are_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.fixture(directory)
            with path.with_suffix(".trace.jsonl").open("a") as handle:
                handle.write('{"ignored_unpersisted_event":true}\n')
            # Complete but unpersisted suffix is outside the authenticated prefix.
            self.assertTrue(export_report(path)["metadata"]["terminal"])
            trace = path.with_suffix(".trace.jsonl")
            trace.write_text(trace.read_text().replace('"kind":"search"', '"kind":"forged"', 1))
            with self.assertRaisesRegex(ValueError, "SHA256"):
                export_report(path)
        with tempfile.TemporaryDirectory() as directory:
            report = copy.deepcopy(self.report)
            report["task"]["compatibility"]["rules"] = "old-rules"
            with self.assertRaisesRegex(ValueError, "task/rules"):
                export_report(self.fixture(directory, report=report), allow_source_drift=True)

    def test_source_drift_requires_explicit_opt_in_and_is_preserved(self):
        report = copy.deepcopy(self.report)
        report["runtime_source_sha256"] = {"studies/shared/campaign_adapter.py": "0" * 64,
                                          "studies/campaign/run.py": "1" * 64}
        with tempfile.TemporaryDirectory() as directory:
            path = self.fixture(directory, report=report)
            with self.assertRaisesRegex(ValueError, "Authoritative replay sources changed"):
                export_report(path)
            replay = export_report(path, allow_source_drift=True)
        self.assertEqual(len(replay["metadata"]["provenance"]["source_differences"]), 2)

    def test_map_deletion_and_nested_scalar_replacement_are_lossless(self):
        before = {"units": {"one": {"damage": 0}, "two": {"damage": 1}}, "politics": {"pending": [1]}, "terminal": False}
        after = {"units": {"one": {"damage": 1}, "three": {"damage": 0}}, "politics": {"pending": []}, "terminal": True}
        self.assertEqual(apply_changes(before, state_changes(before, after)), after)
        self.assertEqual(before["units"]["one"]["damage"], 0)

    def test_browser_seed_identifier_remains_exact_above_javascript_integer_limit(self):
        seed = 8734813948184186716
        env = make_env(seed, calendar_rounds=1)
        metadata = {"seed": seed}
        replay = replay_module._new_replay(env, metadata)
        self.assertEqual(json.loads(json.dumps(replay))["metadata"]["seed"], str(seed))
        self.assertEqual(metadata["seed"], seed)

    def test_existing_outputs_preserved_and_no_temporary_files_left(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "viewer.json"
            write_replay(output, {"schema": "fixture"})
            with self.assertRaisesRegex(ValueError, "preserved"):
                write_replay(output, {"schema": "overwrite"})
            self.assertEqual(json.loads(output.read_text()), {"schema": "fixture"})
            self.assertEqual([path.name for path in Path(directory).iterdir()], ["viewer.json"])

    def forced_position(self):
        """A real decision with one legal action, reached by seeded play."""
        env = make_env(9182, calendar_rounds=1)
        while True:
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            actions = env.legal_actions()
            if len(actions) == 1:
                return env, actions
            env.apply_action(actions[-1])

    def test_a_forced_move_replays_with_no_search_and_no_value(self):
        env, actions = self.forced_position()
        ids = [action.id for action in actions]
        played = {"action_ids": ids, "visit_counts": [0], "priors": [1.], "policy": [1.], "values": None,
                  "action_values": [None]}
        search = replay_module._search(env, played, {"simulations": 64, "max_depth": 16})
        self.assertEqual((search["simulations"], search["values"]), (0, None))
        self.assertEqual((search["actions"][0]["visits"], search["actions"][0]["policy"]), (0, 1.))
        for forged in ({"visit_counts": [64]}, {"action_values": [[0., 0., 0.]]}):
            with self.assertRaisesRegex(ValueError, "one-action root"):
                replay_module._search(env, {**played, **forged}, {"simulations": 64, "max_depth": 16})
        with self.assertRaisesRegex(ValueError, "simulation budget"):
            replay_module._search(env, {**played, "values": [0., 0., 0.]}, {"simulations": 64, "max_depth": 16})

    def test_only_a_one_action_root_may_omit_its_search(self):
        env = make_env(9182, calendar_rounds=1)
        actions = env.legal_actions()
        self.assertGreater(len(actions), 1)
        size = len(actions)
        with self.assertRaisesRegex(ValueError, "one-action root"):
            replay_module._search(env, {"action_ids": [action.id for action in actions], "visit_counts": [0] * size,
                                        "priors": [1 / size] * size, "policy": [1 / size] * size, "values": None,
                                        "action_values": [None] * size}, {"simulations": 64, "max_depth": 16})

    def test_training_stream_prefix_preserves_origin_search_and_observed_events(self):
        env = make_env(9182, calendar_rounds=1)
        context = env.context()
        records = [
            {"type": "run_start", "kind": "training", "config": {"calendar_rounds": 1}, "task": task_manifest(env)},
            {"type": "context", "context": context, "context_sha256": digest(context)},
            {"type": "episode_start", "root": 0, "episode_id": "0:0", "seed": 9182,
             "context_sha256": digest(context), "initial_state_sha256": digest(env.serialize()),
             "initial_planning_key": env.planning_key(), "initial_observation": env.observation()},
        ]
        recorded = self.events[1]
        features = recorded["action_features"]
        menu = [action.features() for action in env.legal_actions()]
        selected = next(index for index, action in enumerate(menu) if action == features)
        before = env.planning_key()
        env.apply_action(env.legal_actions()[selected])
        records.append({"type": "transition", "root": 0, "episode_id": "0:0", "sequence": 0,
                        "event": {"kind": "declaration_offer", "owner": features["player"], "action": features["id"],
                                  "before": before, "after": env.planning_key(), "terminal": False},
                        "decision_menu": menu, "selected_index": selected, "selected_action": features,
                        "search": {**self.events[0]["results"][0], "simulations": 1, "max_depth": 1},
                        "observed_events": json.loads(env.raw.serialize())["state"]["history"]})
        def save(path):
            path.write_text("".join(json.dumps({"schema": "campaign-self-play-trace-v1", **row}) + "\n"
                                    for row in records) + '{"incomplete":')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.jsonl"
            save(path)
            replay = export_trace(path)
            self.assertEqual(replay["metadata"]["origin"], "training self-play")
            self.assertFalse(replay["metadata"]["recording_complete"])
            self.assertFalse(replay["metadata"]["terminal"])
            self.assertEqual(frame_at(replay, 1), snapshot(env))
            records[-1]["observed_events"] = []
            save(path)
            with self.assertRaisesRegex(ValueError, "observed outcomes"):
                export_trace(path)


class LiveReplayTests(unittest.TestCase):
    def records(self):
        env = make_env(97, calendar_rounds=1)
        context = env.context()
        headers = [
            {"type": "run_start", "kind": "training", "config": {"calendar_rounds": 1}, "task": task_manifest(env)},
            {"type": "context", "context": context, "context_sha256": digest(context)},
            {"type": "episode_start", "root": 0, "episode_id": "0:0", "seed": 97,
             "context_sha256": digest(context), "initial_state_sha256": digest(env.serialize()),
             "initial_planning_key": env.planning_key(), "initial_observation": env.observation()},
        ]
        transitions = []
        for sequence in range(2):
            actions = env.legal_actions()
            menu = [action.features() for action in actions]
            before, kind, owner = env.planning_key(), env.decision_kind(), env.current_decision_player()
            cursor = len(json.loads(env.raw.serialize())["state"]["history"])
            env.apply_action(actions[0])
            transitions.append({"type": "transition", "root": 0, "episode_id": "0:0", "sequence": sequence,
                "event": {"kind": kind, "owner": owner, "action": menu[0]["id"], "before": before,
                          "after": env.planning_key(), "terminal": False},
                "decision_menu": menu, "selected_index": 0, "selected_action": menu[0],
                "search": {"visit_counts": [1] + [0] * (len(menu) - 1), "policy": [1.] + [0.] * (len(menu) - 1),
                           "priors": [1 / len(menu)] * len(menu), "values": [0., 0., 0.],
                           "action_values": [[0., 0., 0.]] + [None] * (len(menu) - 1), "simulations": 1, "max_depth": 1},
                "observed_events": json.loads(env.raw.serialize())["state"]["history"][cursor:]})
        return headers, transitions, snapshot(env)

    def line(self, row):
        return json.dumps({"schema": "campaign-self-play-trace-v1", **row}, separators=(",", ":")) + "\n"

    def append(self, path, text):
        with path.open("a") as handle:
            handle.write(text)

    def test_live_append_waits_for_newline_and_only_replays_new_actions(self):
        headers, transitions, final = self.records()
        with tempfile.TemporaryDirectory() as directory, patch(
                "studies.campaign.replay._stream_transition", wraps=replay_module._stream_transition) as apply:
            path = Path(directory) / "replay.jsonl"
            live = LiveReplay(path)
            self.assertIsNone(live.update())
            self.assertEqual(live.status, "waiting_for_file")
            path.write_text("")
            self.assertIsNone(live.update())
            self.assertEqual(live.revision, 0)
            first_line = self.line(transitions[0])
            self.append(path, "".join(self.line(row) for row in headers) + first_line[:100])
            initial = live.update()
            self.assertEqual(len(initial["steps"]), 0)
            self.assertEqual(live.revision, 1)
            self.assertIs(live.update(), initial)
            self.assertEqual(live.revision, 1)
            self.assertEqual(apply.call_count, 0)
            self.append(path, first_line[100:])
            first = live.update()
            self.assertEqual(len(first["steps"]), 1)
            self.assertEqual(len(initial["steps"]), 0)
            self.assertEqual(apply.call_count, 1)
            self.append(path, self.line(transitions[1]))
            second = live.update()
            self.assertEqual(len(second["steps"]), 2)
            self.assertEqual(apply.call_count, 2)
            self.assertEqual(frame_at(second, 2), final)
            self.assertIs(live.update(), second)
            self.assertEqual(apply.call_count, 2)
            self.append(path, self.line({"type": "run_end", "status": "budget_exhausted"}))
            ended = live.update()
            self.assertEqual(live.status, "ended")
            self.assertTrue(ended["metadata"]["recording_complete"])
            self.assertFalse(ended["metadata"]["live"])
            self.assertFalse(ended["metadata"]["terminal"])
            self.assertEqual(live.revision, 4)

    def test_rewrites_truncation_and_replacement_are_rejected(self):
        headers, transitions, _ = self.records()
        original = "".join(self.line(row) for row in [*headers, transitions[0]])
        for mutation in ("rewrite", "truncate", "replace", "partial_rewrite"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "replay.jsonl"
                path.write_text(original + ('{"partial":' if mutation == "partial_rewrite" else ""))
                live = LiveReplay(path)
                verified = live.update()
                offset, revision = live.offset, live.revision
                if mutation == "rewrite":
                    path.write_text(original.replace('"training"', '"traininG"', 1))
                elif mutation == "truncate":
                    path.write_text(original[:100])
                elif mutation == "replace":
                    replacement = path.with_suffix(".replacement")
                    replacement.write_text(original)
                    replacement.replace(path)
                else:
                    path.write_text(original + '{"Partial":')
                with self.assertRaisesRegex(ValueError, "edited|truncated|replaced"):
                    live.update()
                self.assertIs(live.replay, verified)
                self.assertEqual((live.offset, live.revision), (offset, revision))

    def test_invalid_new_transition_is_transactional_and_sequence_gaps_fail(self):
        headers, transitions, _ = self.records()
        for mutation in ("after", "sequence"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "replay.jsonl"
                path.write_text("".join(self.line(row) for row in [*headers, transitions[0]]))
                live = LiveReplay(path)
                verified = live.update()
                before_env = live._env.serialize()
                offset, revision = live.offset, live.revision
                broken = copy.deepcopy(transitions[1])
                if mutation == "after":
                    broken["event"]["after"] = "0" * 64
                else:
                    broken["sequence"] = 8
                self.append(path, self.line(broken))
                with self.assertRaisesRegex(ValueError, "after-state|sequence"):
                    live.update()
                self.assertIs(live.replay, verified)
                self.assertEqual(live._env.serialize(), before_env)
                self.assertEqual((live.offset, live.revision), (offset, revision))

    def test_waiting_for_selected_root_and_episode_does_not_choose_another(self):
        headers, transitions, _ = self.records()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.jsonl"
            path.write_text("".join(self.line(row) for row in [*headers, *transitions]))
            other_root = LiveReplay(path, root=1)
            self.assertIsNone(other_root.update())
            self.assertEqual(other_root.status, "waiting_for_episode")
            second_episode = LiveReplay(path, episode=1)
            self.assertIsNone(second_episode.update())
            self.assertEqual(second_episode.status, "waiting_for_episode")


if __name__ == "__main__":
    unittest.main()
