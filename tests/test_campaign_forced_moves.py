"""A forced move skips the work around it, never the game: moves, samples and random streams stay."""
from __future__ import annotations

import functools
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from studies.campaign import evaluation, learning, run
from studies.campaign.curriculum import make_env
from studies.campaign.evaluation import evaluate
from studies.campaign.learning import LearningConfig, ReplayTraceWriter, play_episode
from studies.campaign.replay import export_trace
from studies.shared.multiplayer_mcts import Evaluation, MctsConfig
from tools.benchmark_campaign_devices import Config, play_shared_game, selfplay, setup_models

SEED = 1951


class PositionEvaluator:
    """Priors and values that depend only on the position, as frozen weights do."""
    version = "position-hash-v1"

    def __init__(self):
        self.menus = []
        self.stats = SimpleNamespace(requests=0, prepare_seconds=0., wait_seconds=0.)

    def evaluate(self, env, actions):
        self.menus.append(len(actions))
        self.stats.requests += 1
        digest = hashlib.sha256(env.planning_key().encode()).digest()
        return Evaluation([1 + digest[index % 32] for index in range(len(actions))],
                          tuple(float(byte) for byte in digest[:3]))

    def evaluate_batch(self, requests):
        return [self.evaluate(env, actions) for env, actions in requests]


class ForcedMoveGameTests(unittest.TestCase):
    def episode(self, searched):
        env, evaluator = make_env(SEED, calendar_rounds=1), PositionEvaluator()
        with patch.object(learning, "MctsConfig", functools.partial(MctsConfig, search_forced_root=searched)):
            played = play_episode(env, evaluator, config=LearningConfig(simulations=4, max_depth=4, seed=11),
                                  rules_version="forced-move-test", numeric=True, token_buckets=2048,
                                  batch_version="frozen", environment_seed=SEED, max_transitions=2000)
        return played, env.serialize(), evaluator

    def test_training_games_keep_every_move_sample_and_random_stream(self):
        (skipped, skipped_state, skipping), (searched, searched_state, searching) = self.episode(False), self.episode(True)
        self.assertTrue(skipped["terminal"])
        self.assertEqual(skipped["events"], searched["events"])
        self.assertEqual(skipped["counts"], searched["counts"])
        self.assertEqual(skipped["returns"], searched["returns"])
        self.assertEqual(skipped_state, searched_state)
        # Forced decisions stay in the data: they still teach the value head.
        self.assertEqual(len(skipped["records"]), skipped["counts"]["decisions"])
        self.assertEqual(skipped["records"], searched["records"])
        forced = sum(len(record["policy"]) == 1 for record in skipped["records"])
        self.assertGreater(forced, 0)
        self.assertLess(skipping.stats.requests, searching.stats.requests)

    def shared_game(self, searched):
        created = []
        def create(seed, **kwargs):
            created.append(make_env(seed, **kwargs))
            return created[-1]
        config = Config(mode="selfplay", devices=("cpu",), seeds=(SEED,), threads=1, cpu_budget=5, calendar_rounds=1,
                        simulations=4, max_depth=4, search_forced_roots=searched)
        evaluator = PositionEvaluator()
        with patch("studies.campaign.curriculum.make_env", side_effect=create):
            record = play_shared_game(config, SEED, evaluator, time.time() + 240)
        return record, created[0].serialize(), evaluator

    def test_shared_games_end_in_the_same_position_with_fewer_evaluations(self):
        (skipped, skipped_state, skipping), (searched, searched_state, searching) = self.shared_game(False), self.shared_game(True)
        self.assertTrue(skipped["terminal"])
        for name in ("transitions", "decisions", "chance_events", "terminal_returns", "clock"):
            self.assertEqual(skipped[name], searched[name], name)
        self.assertEqual(skipped_state, searched_state)
        self.assertLess(skipped["evaluations"], searched["evaluations"])
        self.assertLess(skipping.menus.count(1), searching.menus.count(1))

    def test_real_selfplay_reproduces_its_trace_and_final_state_and_rng_digests(self):
        reports = {}
        for searched in (False, True):
            config = Config(mode="selfplay", devices=("cpu",), threads=1, search_evaluation="per_search", seeds=(SEED, 1952),
                            calendar_rounds=1, simulations=2, max_depth=4, search_forced_roots=searched, seconds=240.)
            models, evaluator, forward_stats, _ = setup_models(config, "cpu")
            reports[searched] = selfplay(config, "cpu", models, evaluator, forward_stats, time.monotonic() + 240.,
                                         lambda result=None: None)
        skipped, searched = reports[False], reports[True]
        self.assertEqual((skipped["status"], searched["status"]), ("completed", "completed"))
        for name in ("trace_sha256", "final_state_and_rng_sha256", "terminal_returns", "decisions"):
            self.assertEqual([game[name] for game in skipped["games"]], [game[name] for game in searched["games"]], name)
        self.assertLess(skipped["inference_requests"], searched["inference_requests"])

    def collected(self, searched):
        config = run.RunConfig(calendar_rounds=1, simulations=2, max_depth=4)
        learner = run._learner(config, make_env(config.seed, calendar_rounds=1))
        roots = [make_env(seed, calendar_rounds=1) for seed in (SEED, 1952)]
        evaluator = PositionEvaluator()
        with patch.object(learner, "_evaluator", return_value=evaluator), \
             patch.object(learning, "MctsConfig", functools.partial(MctsConfig, search_forced_root=searched)):
            learner.begin_batch_many(roots)
            learner.collect_many(400)
        return learner, [env.serialize() for env in roots], evaluator

    def test_parallel_collection_keeps_every_move_and_sample_with_position_only_values(self):
        (skipped, skipped_states, skipping), (searched, searched_states, searching) = self.collected(False), self.collected(True)
        self.assertEqual(skipped.counters["episodes"], 2)
        self.assertEqual(skipped.action_history, searched.action_history)
        self.assertEqual(skipped.counters, searched.counters)
        self.assertEqual(skipped.batch_records, searched.batch_records)
        self.assertEqual(skipped_states, searched_states)
        self.assertGreater(sum(len(record["policy"]) == 1 for record in skipped.batch_records), 0)
        self.assertLess(skipping.stats.requests, searching.stats.requests)

    def test_held_out_games_end_the_same_and_keep_their_first_prediction(self):
        reports = {}
        for searched in (False, True):
            with patch.object(evaluation, "MctsConfig", functools.partial(MctsConfig, search_forced_root=searched)):
                reports[searched] = evaluate(lambda seed: make_env(seed, calendar_rounds=1), PositionEvaluator(),
                                             target_player="axis", seeds=[SEED, 1952], max_transitions=2000)
        names = ("seed", "terminal", "counts", "decisions_by_actor", "observed_terminal_returns",
                 "first_search_value_prediction", "first_search_prediction_point")
        for skipped, full in zip(reports[False]["games"], reports[True]["games"], strict=True):
            self.assertTrue(skipped["terminal"])
            self.assertEqual({name: skipped[name] for name in names}, {name: full[name] for name in names})
        self.assertLess(reports[False]["inference_batches"]["requests"], reports[True]["inference_batches"]["requests"])

    def test_training_replays_show_forced_moves_without_search_statistics(self):
        config = run.RunConfig(calendar_rounds=1, simulations=2, max_depth=4)
        learner = run._learner(config, make_env(config.seed, calendar_rounds=1))
        learner.env = make_env(config.seed, calendar_rounds=1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.jsonl"
            writer = ReplayTraceWriter(path, {"kind": "training", "config": {"calendar_rounds": 1},
                                              "task": run.task_manifest(learner.env)})
            learner.set_replay_observer(writer)
            learner.replay_capture.remember_seed(learner.env, config.seed)
            learner.collect(2000)
            writer.close()
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            replay = export_trace(path)
        transitions = [row for row in rows if row["type"] == "transition" and "search" in row]
        forced = [row["search"] for row in transitions if len(row["decision_menu"]) == 1]
        self.assertGreater(len(forced), 0)
        self.assertTrue(all((row["visit_counts"], row["values"], row["policy"]) == ([0], None, [1.0]) for row in forced))
        steps = [step["search"] for step in replay["steps"] if step.get("search")]
        self.assertEqual(sum(step["simulations"] == 0 for step in steps), len(forced))
        self.assertTrue(all(step["simulations"] == 2 for step in steps if len(step["actions"]) > 1))


if __name__ == "__main__":
    unittest.main()
