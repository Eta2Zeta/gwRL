"""Training episodes in worker processes: any worker count gives the same batch, resume is exact."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import tempfile
import unittest
from dataclasses import asdict, fields
from pathlib import Path

import torch

from studies.campaign import run
from studies.campaign.curriculum import make_env
from studies.campaign.episode_workers import EpisodeWorkers

TINY = {"calendar_rounds": 1, "simulations": 2, "max_depth": 4, "complete_episodes": True, "parallel_envs": 2}


def tiny_learner():
    config = run.RunConfig(**TINY)
    learner = run._learner(config, make_env(config.seed, calendar_rounds=1))
    learner.env = make_env(config.seed, calendar_rounds=1)
    return learner


def workers_for(learner, processes):
    return EpisodeWorkers(processes, calendar_rounds=1, model_config=learner.model_config,
                          learning_config=asdict(learner.config), rules_version=learner.compatibility["rules"],
                          numeric=learner._numeric_models())


def outcome(learner):
    return (json.dumps(learner.action_history, sort_keys=True, default=str),
            [(row["owner"], row["policy"], row["values"], row["target_source"]) for row in learner.replay],
            learner.counters.copy(), learner.model_versions())


class EpisodeWorkerTests(unittest.TestCase):
    def batch(self, processes):
        learner = tiny_learner()
        workers = workers_for(learner, processes)
        try:
            collection = learner.collect_episodes(workers, 2, 2000)
        finally:
            workers.close()
        learner.finish_batch()
        learner.update()
        return learner, collection

    def test_one_worker_and_two_workers_produce_the_same_batch_and_update(self):
        one, first = self.batch(1)
        two, second = self.batch(2)
        self.assertEqual(first["seeds"], second["seeds"])
        self.assertEqual(len({result["process"] for result in second["results"]}), 2)
        self.assertEqual(outcome(one), outcome(two))
        self.assertEqual(one.counters["episodes"], 2)
        self.assertTrue(one.replay and all(row["target_source"] == "terminal" for row in one.replay))

    def test_stop_and_transition_guard_discard_the_batch_and_rewind_its_seeds(self):
        learner = tiny_learner()
        start = learner.environment_random.getstate()
        workers = workers_for(learner, 2)
        try:
            self.assertIsNone(learner.collect_episodes(workers, 2, 2000, stop=lambda: True))
        finally:
            workers.terminate()
        self.assertIsNone(learner.frozen_models)
        self.assertEqual(learner.environment_random.getstate(), start)
        workers = workers_for(learner, 1)
        try:
            guarded = learner.collect_episodes(workers, 1, 3)
        finally:
            workers.close()
        self.assertTrue(guarded["exhausted"])
        self.assertEqual(guarded["results"][0]["records"], [])
        self.assertIsNone(learner.frozen_models)
        self.assertEqual(learner.environment_random.getstate(), start)
        self.assertEqual((learner.counters["transitions"], learner.counters["episodes"]), (0, 0))

    def test_configuration_requires_complete_episodes_and_enough_games(self):
        for values in ({"episode_workers": 2, "complete_episodes": False, "parallel_envs": 2},
                       {"episode_workers": 3, "complete_episodes": True, "parallel_envs": 2},
                       {"episode_workers": -1}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                run.RunConfig(**values)
        config = run.RunConfig(episode_workers=8, complete_episodes=True, parallel_envs=8, threads=4, cpu_budget=9)
        self.assertEqual(run.busy_cores(config), 9)

    def train(self, directory, *, resume=False, stop_after_waves=None):
        values = {field.name: None for field in fields(run.RunConfig)}
        if not resume:
            values.update(TINY, episode_workers=2, batches=2, transitions_per_batch=500)
        args = argparse.Namespace(**values, run_dir=None if resume else directory,
            resume=directory / "checkpoint.pt" if resume else None, full_campaign=False, record_replay=False,
            stop_after_waves=stop_after_waves, extend_episode_budget=None)
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.train(args)
        return code, torch.load(directory / "checkpoint.pt", map_location="cpu", weights_only=False)

    def test_resuming_after_a_batch_matches_an_uninterrupted_run(self):
        with tempfile.TemporaryDirectory() as directory:
            whole_code, whole = self.train(Path(directory) / "whole")
            stop_code, _ = self.train(Path(directory) / "split", stop_after_waves=1)
            resume_code, split = self.train(Path(directory) / "split", resume=True)
        self.assertEqual((whole_code, stop_code, resume_code), (0, 130, 0))
        self.assertEqual(whole["runner"]["training_environment_seeds"], split["runner"]["training_environment_seeds"])
        for name in ("counters", "model_versions", "action_history"):
            self.assertEqual(whole["learner"][name], split["learner"][name], name)
        self.assertEqual([(row["owner"], row["policy"], row["values"]) for row in whole["learner"]["replay"]],
                         [(row["owner"], row["policy"], row["values"]) for row in split["learner"]["replay"]])
        self.assertEqual(whole["learner"]["counters"]["episodes"], 4)


if __name__ == "__main__":
    unittest.main()
