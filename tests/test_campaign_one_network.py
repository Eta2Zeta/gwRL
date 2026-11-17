"""One network for all three alliances, told by its input which alliance chooses (Q-009)."""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from studies.campaign import run
from studies.campaign.curriculum import make_env
from studies.campaign.episode_workers import SharedEpisodeWorkers
from studies.campaign.learning import LearningConfig, fresh_game_losses
from studies.campaign.model_export import load_evaluation_models
from studies.campaign.neural import distinct_networks
from studies.shared.multiplayer_mcts import PLAYERS

TINY = dict(calendar_rounds=1, simulations=2, max_depth=2, hidden_dim=16, complete_episodes=True,
            parallel_envs=2, episode_workers=2, batch_size=8)


def tiny_learner(networks):
    config = run.RunConfig(**TINY, networks=networks)
    learner = run._learner(config, make_env(config.seed, calendar_rounds=1))
    learner.env = make_env(config.seed, calendar_rounds=1)
    return learner


def play(learner, games=3):
    """Real games of the tiny curriculum, their samples kept in the learner's replay buffer."""
    workers = SharedEpisodeWorkers(1, 2, device=torch.device("cpu"), calendar_rounds=1,
                                   model_config=learner.model_config, learning_config=asdict(learner.config),
                                   rules_version=learner.compatibility["rules"])
    collection = learner.collect_episodes(workers, games, 2000)
    learner.finish_batch()
    return collection


def weights_of(model):
    return {name: tensor.clone() for name, tensor in model.state_dict().items()}


class OneNetworkTests(unittest.TestCase):
    def test_the_settings_name_three_networks_or_one(self):
        self.assertEqual(run.RunConfig().networks, "three")
        self.assertEqual(LearningConfig().networks, "three")
        with self.assertRaisesRegex(ValueError, "three or one"):
            run.RunConfig(networks="two")
        with self.assertRaisesRegex(ValueError, "three or one"):
            LearningConfig(networks="two")

    def test_the_learner_holds_one_network_and_one_optimizer(self):
        learner = tiny_learner("one")
        self.assertEqual(len(distinct_networks(learner.models)), 1)
        self.assertEqual(len({id(optimizer) for optimizer in learner.optimizers.values()}), 1)
        digests = {version.rsplit(":", 1)[-1] for version in learner.model_versions().values()}
        self.assertEqual(len(digests), 1)
        three = tiny_learner("three")
        self.assertEqual(len(distinct_networks(three.models)), 3)
        model_config = three.models[PLAYERS[0]].config
        with self.assertRaisesRegex(ValueError, "One network must serve"):
            type(learner)(three.models, model_config, replace(three.config, networks="one"),
                          compatibility=three.compatibility)
        with self.assertRaisesRegex(ValueError, "separate model instances"):
            type(learner)(learner.models, model_config, replace(learner.config, networks="three"),
                          compatibility=learner.compatibility)

    def test_its_policy_learns_from_every_alliance_and_it_resumes_exactly(self):
        learner = tiny_learner("one")
        play(learner)
        owners = {sample["owner"] for sample in learner.replay}
        self.assertGreater(len(owners), 1)  # The games' decisions belong to more than one alliance.
        saved = learner.checkpoint()
        before = weights_of(learner.models[PLAYERS[0]])
        update = learner.update()
        self.assertEqual(set(update["losses"]), {"all"})
        drawn = min(learner.config.batch_size, len(learner.replay))
        # Every drawn decision trains the one policy, whichever alliance made it.
        self.assertTrue(all(step["policy_samples"] == drawn for step in update["losses"]["all"]))
        after = weights_of(learner.models[PLAYERS[0]])
        self.assertTrue(any(not torch.equal(before[name], after[name]) for name in before))
        # A checkpoint restores one network shared by the alliances, and the next
        # network update repeats exactly.
        resumed = tiny_learner("one")
        resumed.restore(saved, env_template=make_env(TINY_SEED(), calendar_rounds=1))
        self.assertEqual(len(distinct_networks(resumed.models)), 1)
        self.assertEqual(len({id(optimizer) for optimizer in resumed.optimizers.values()}), 1)
        again = resumed.update()
        self.assertEqual(again["losses"], update["losses"])
        for name, tensor in weights_of(resumed.models[PLAYERS[0]]).items():
            self.assertTrue(torch.equal(tensor, after[name]), name)
        # Three networks' learner refuses one network's checkpoint, and back.
        with self.assertRaisesRegex(ValueError, "Incompatible"):
            tiny_learner("three").restore(saved, env_template=make_env(TINY_SEED(), calendar_rounds=1))

    def test_three_networks_still_train_each_policy_on_its_own_alliance(self):
        learner = tiny_learner("three")
        play(learner)
        update = learner.update()
        self.assertEqual(set(update["losses"]), set(PLAYERS))
        drawn = min(learner.config.batch_size, len(learner.replay))
        for step in range(learner.config.epochs):
            self.assertEqual(sum(update["losses"][player][step]["policy_samples"] for player in PLAYERS), drawn)

    def test_fresh_game_losses_rate_each_decision_with_its_alliances_network(self):
        for networks in ("three", "one"):
            with self.subTest(networks=networks):
                learner = tiny_learner(networks)
                collection = play(learner, games=2)
                records = [record for result in collection["results"] for record in result["records"]]
                losses = fresh_game_losses(learner.models, records, learner.config.value_scale)
                self.assertEqual(set(losses), {record["owner"] for record in records})
                self.assertEqual(sum(total["samples"] for total in losses.values()), len(records))
                for total in losses.values():
                    self.assertGreater(total["value_squared_error"], 0)
                    self.assertGreaterEqual(total["policy_kl"], -1e-9)
                    self.assertGreaterEqual(total["policy_cross_entropy"], total["policy_kl"] - 1e-9)


def TINY_SEED():
    return run.RunConfig().seed


class OneNetworkRunTests(unittest.TestCase):
    ARGUMENTS = ["--calendar-rounds", "1", "--complete-episodes", "--batches", "2", "--parallel-envs", "4",
                 "--episode-workers", "2", "--games-per-process", "2", "--transitions-per-batch", "2000",
                 "--simulations", "2", "--max-depth", "2", "--hidden-dim", "16",
                 "--batch-size", "4", "--epochs", "2", "--continuous", "--networks", "one"]

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="campaign-one-network-")
        self.addCleanup(temporary.cleanup)
        self.run_dir = Path(temporary.name) / "run"

    def train(self, *extra):
        with patch("builtins.print"), patch("torch.set_num_interop_threads"):
            return run.main(["train", "--run-dir", str(self.run_dir), *extra])

    def test_one_network_trains_beside_its_games_and_resumes(self):
        self.assertEqual(self.train(*self.ARGUMENTS, "--stop-after-waves", "1"), 130)
        self.assertEqual(self.train("--resume", str(self.run_dir / "checkpoint.pt")), 0)
        manifest = json.loads((self.run_dir / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["counters"]["updates"], 2)
        updates = manifest["runner"]["updates"]
        for update in updates:
            self.assertEqual(set(update["update"]["losses"]), {"all"})
            # Each finished game was measured before it trained the network.
            fresh = update["fresh_games"]
            self.assertEqual(sum(total["samples"] for total in fresh.values()), update["rollout"]["samples"])
        loaded = load_evaluation_models(self.run_dir / "models" / "generation-000002.pt")
        self.assertEqual(len(distinct_networks(loaded["models"])), 1)


if __name__ == "__main__":
    unittest.main()
