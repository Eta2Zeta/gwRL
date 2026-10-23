from __future__ import annotations

import copy
import json
import queue
import random
import threading
import time
import unittest
from concurrent.futures import CancelledError

from studies.campaign.batching import BatchStats, search_many
from studies.shared.multiplayer_mcts import Evaluation, MctsConfig, OpponentPolicy, PLAYERS, VectorMCTS


class TinyEnv:
    """Owner-changing, stochastic finite tree with separately serialized RNG."""

    def __init__(self, actor=0, tag=0, node="root", seed=17):
        self.actor, self.tag, self.node = actor, tag, node
        self.actual_random = random.Random(seed)
        self.search_random = None

    def current_decision_player(self):
        if self.node in ("coin", "a", "b", "c", "d"):
            return None
        return PLAYERS[(self.actor + (self.node == "response")) % 3]

    def decision_kind(self):
        return "terminal" if self.is_terminal() else "chance" if self.node == "coin" else "defender_choice"

    def legal_actions(self):
        return {"root": ["reply", "gamble"], "response": ["selfish", "generous"]}.get(self.node, [])

    def apply_action(self, action):
        self.node = {("root", "reply"): "response", ("root", "gamble"): "coin",
                     ("response", "selfish"): "a", ("response", "generous"): "b"}[self.node, action]

    def resolve_chance(self):
        rng = self.search_random if self.search_random is not None else self.actual_random
        self.node = "c" if rng.random() < 0.5 else "d"

    def is_terminal(self):
        return self.node in ("a", "b", "c", "d")

    def returns(self):
        return {"a": (21, 80, -5), "b": (90, 3, 8), "c": (70, 2, 13), "d": (15, 15, 60)}.get(self.node, (0, 0, 0))

    def observation(self):
        return {"node": self.node, "owner": self.current_decision_player(), "tag": self.tag}

    def context(self):
        return {"players": list(PLAYERS), "fixture": "tiny-batching-v1"}

    def planning_key(self):
        return json.dumps([self.actor, self.tag, self.node])

    def clone_for_search(self, seed):
        result = copy.copy(self)
        result.actual_random = copy.deepcopy(self.actual_random)
        result.search_random = random.Random(seed)
        return result

    def serialize(self):
        return json.dumps([self.actor, self.tag, self.node, repr(self.actual_random.getstate()),
                           repr(self.search_random.getstate()) if self.search_random is not None else None])


class RecordingEvaluator:
    version = "actor-raw-vector-v3"

    def __init__(self):
        self.batches = []
        self.threads = []

    def evaluate_batch(self, requests):
        self.batches.append([(env.tag, env.node, env.current_decision_player(), len(actions)) for env, actions in requests])
        self.threads.append(threading.get_ident())
        result = []
        for env, actions in requests:
            actor = env.current_decision_player()
            index = PLAYERS.index(actor) if actor is not None else 3
            # Deliberately unequal raw values detect reassociation, accidental
            # player-component reordering, or an extra value-scale conversion.
            values = (17.25 + env.tag, -900.5 - index, 3020.75 + index * env.tag)
            result.append(Evaluation([i + 1 + env.tag % 3 for i in range(len(actions))], values))
        return result

    def evaluate(self, env, actions):
        return self.evaluate_batch([(env, actions)])[0]


class CampaignBatchingTests(unittest.TestCase):
    def bounded(self, operation, timeout=5):
        """A barrier regression must fail rather than hang the whole suite."""
        outcome = queue.Queue()

        def run():
            try:
                outcome.put((True, operation()))
            except BaseException as error:
                outcome.put((False, error))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(timeout)
        self.assertFalse(thread.is_alive(), "Independent-root coordinator failed to release its workers")
        success, value = outcome.get_nowait()
        if not success:
            raise value
        return value

    def assert_same_result(self, actual, expected):
        for name in ("actions", "visit_counts", "policy", "priors", "values", "action_values", "cache_identity", "simulations"):
            self.assertEqual(getattr(actual, name), getattr(expected, name), name)

    def test_real_batches_match_sequential_search_for_all_actors_and_noise(self):
        for noise in (False, True):
            envs = [TinyEnv(actor=i % 3, tag=i * 11) for i in range(6)]
            before = [env.serialize() for env in envs]
            configs = [MctsConfig(simulations=96, max_depth=4, seed=31 + i, record_trace=True) for i in range(6)]
            expected = [VectorMCTS(RecordingEvaluator(), config).search(env, add_root_noise=noise)
                        for env, config in zip(envs, configs)]
            evaluator, stats = RecordingEvaluator(), BatchStats()
            actual = self.bounded(lambda: search_many(envs, evaluator, configs=configs, add_root_noise=noise, stats=stats))
            self.assertEqual([env.serialize() for env in envs], before)
            for result, reference in zip(actual, expected):
                self.assert_same_result(result, reference)
                self.assertEqual(result.cache_identity[1], evaluator.version)
            self.assertEqual(evaluator.batches[0], [(env.tag, "root", PLAYERS[i % 3], 2) for i, env in enumerate(envs)])
            self.assertGreater(max(stats.batch_sizes), 1)
            self.assertEqual(stats.requests, sum(map(len, evaluator.batches)))
            self.assertEqual(stats.batches, len(evaluator.batches))
            self.assertEqual(stats.roots, 6)
            self.assertGreaterEqual(stats.elapsed_seconds, stats.inference_seconds)
            self.assertEqual(len(set(evaluator.threads)), 1, "Evaluator must run only on its coordinator thread")

    def test_terminal_and_short_roots_leave_dynamic_barrier(self):
        envs = [TinyEnv(node="a"), TinyEnv(tag=1), TinyEnv(tag=2), TinyEnv(node="coin", tag=3)]
        settings = [MctsConfig(simulations=1), MctsConfig(simulations=1), MctsConfig(simulations=60),
                    MctsConfig(simulations=40, max_depth=1)]
        evaluator = RecordingEvaluator()
        actual = self.bounded(lambda: search_many(envs, evaluator, configs=settings))
        self.assertEqual(actual[0].values, (21, 80, -5))
        self.assertFalse(any(row[0] == 0 for batch in evaluator.batches for row in batch))
        self.assertTrue(any(len(batch) > 1 for batch in evaluator.batches))
        for env, config, result in zip(envs, settings, actual):
            self.assert_same_result(result, VectorMCTS(RecordingEvaluator(), config).search(env))

    def test_ownerless_chance_cutoffs_keep_raw_values_and_rng(self):
        envs = [TinyEnv(actor=i, tag=i + 7) for i in range(3)]
        before = [env.serialize() for env in envs]
        config = MctsConfig(simulations=12, max_depth=1, record_trace=True)
        evaluator = RecordingEvaluator()
        actual = search_many(envs, evaluator, config)
        self.assertTrue(any(owner is None and size == 0 for batch in evaluator.batches for _, _, owner, size in batch))
        for env, result in zip(envs, actual):
            self.assert_same_result(result, VectorMCTS(RecordingEvaluator(), config).search(env))
        self.assertEqual(before, [env.serialize() for env in envs])

    def test_per_root_fixed_policies_are_not_shared_or_replaced(self):
        policies = [OpponentPolicy("selfish-v1", lambda env, actions: [1 if action == "selfish" else 0 for action in actions]),
                    OpponentPolicy("generous-v2", lambda env, actions: [1 if action == "generous" else 0 for action in actions])]
        envs = [TinyEnv(tag=1), TinyEnv(tag=2)]
        config = MctsConfig(simulations=64, mode="fixed_opponents", target_player="axis", record_trace=True)
        actual = search_many(envs, RecordingEvaluator(), config, opponent_policies=policies)
        for env, policy, result in zip(envs, policies, actual):
            expected = VectorMCTS(RecordingEvaluator(), config, opponent_policy=policy).search(env)
            self.assert_same_result(result, expected)

    def test_batch_cap_is_observed_without_reordering_results(self):
        envs = [TinyEnv(actor=i % 3, tag=i) for i in range(7)]
        evaluator, stats = RecordingEvaluator(), BatchStats()
        config = MctsConfig(simulations=6)
        actual = search_many(envs, evaluator, config, max_batch_size=3, stats=stats)
        self.assertEqual(stats.batch_sizes[:3], [3, 3, 1])
        self.assertLessEqual(max(stats.batch_sizes), 3)
        for env, result in zip(envs, actual):
            self.assert_same_result(result, VectorMCTS(RecordingEvaluator(), config).search(env))

    def test_evaluator_exception_releases_all_pending_roots(self):
        class Broken(RecordingEvaluator):
            def evaluate_batch(self, requests):
                if len(self.batches) >= 1:
                    raise RuntimeError("deliberate inference failure")
                return super().evaluate_batch(requests)

        with self.assertRaisesRegex(RuntimeError, "deliberate inference failure"):
            self.bounded(lambda: search_many([TinyEnv(tag=i) for i in range(5)], Broken()))

    def test_worker_exception_releases_other_waiting_roots(self):
        class BrokenEnv(TinyEnv):
            def legal_actions(self):
                raise LookupError("deliberate rules failure")

        with self.assertRaisesRegex(LookupError, "deliberate rules failure"):
            self.bounded(lambda: search_many([TinyEnv(), BrokenEnv(), TinyEnv(tag=2)], RecordingEvaluator()))
        with self.assertRaisesRegex(ValueError, "versioned policy must be specified together"):
            self.bounded(lambda: search_many([TinyEnv(), TinyEnv()], RecordingEvaluator(),
                                            MctsConfig(mode="fixed_opponents", target_player="axis")))

    def test_invalid_batch_and_version_mutation_are_rejected_without_hanging(self):
        class ShortBatch(RecordingEvaluator):
            def evaluate_batch(self, requests):
                return super().evaluate_batch(requests)[:-1]

        class InvalidValue(RecordingEvaluator):
            def evaluate_batch(self, requests):
                return [Evaluation([1] * len(actions), (1, float("nan"), 3)) for _, actions in requests]

        class ChangedVersion(RecordingEvaluator):
            def evaluate_batch(self, requests):
                self.version = "updated-model"
                return super().evaluate_batch(requests)

        for evaluator, message in ((ShortBatch(), "one Evaluation per request"), (InvalidValue(), "three finite"),
                                   (ChangedVersion(), "version changed")):
            with self.assertRaisesRegex(ValueError, message):
                self.bounded(lambda: search_many([TinyEnv(), TinyEnv(tag=1)], evaluator))

    def test_external_cancellation_and_keyboard_interrupt_release_workers(self):
        cancel = threading.Event()

        class CancelAtInference(RecordingEvaluator):
            def evaluate_batch(self, requests):
                cancel.set()
                return super().evaluate_batch(requests)

        started = time.monotonic()
        with self.assertRaises(CancelledError):
            self.bounded(lambda: search_many([TinyEnv(), TinyEnv(tag=2)], CancelAtInference(), cancel_event=cancel))
        self.assertLess(time.monotonic() - started, 2)
        with self.assertRaises(CancelledError):
            search_many([TinyEnv()], RecordingEvaluator(), cancel_event=cancel)

        class Interrupted(RecordingEvaluator):
            def evaluate_batch(self, requests):
                raise KeyboardInterrupt()

        with self.assertRaises(KeyboardInterrupt):
            self.bounded(lambda: search_many([TinyEnv(), TinyEnv(tag=1)], Interrupted()))

    def test_empty_roots_and_configuration_validation(self):
        self.assertEqual(search_many([], RecordingEvaluator()), [])
        for kwargs in ({"configs": []}, {"max_batch_size": 0}, {"opponent_policies": []},
                       {"config": MctsConfig(), "configs": [MctsConfig()]}):
            with self.assertRaises(ValueError):
                search_many([TinyEnv()], RecordingEvaluator(), **kwargs)

    def test_real_neural_models_batch_multiple_roots_per_actor_in_raw_units(self):
        import torch
        from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator

        class NeuralEnv(TinyEnv):
            def legal_actions(self):
                return [{"id": action, "kind": "choose", "parameters": {"target": action}}
                        for action in super().legal_actions()]

            def apply_action(self, action):
                super().apply_action(action["id"])

        class CountedModel(CampaignPolicyValueNet):
            def __init__(self, config):
                super().__init__(config)
                self.batch_sizes = []

            def forward_batch(self, inputs):
                self.batch_sizes.append(len(inputs))
                return super().forward_batch(inputs)

        threads = torch.get_num_threads()
        torch.set_num_threads(1)
        try:
            with torch.random.fork_rng():
                torch.manual_seed(83)
                models = {actor: CountedModel(CampaignModelConfig(hidden_dim=8, message_layers=1,
                                                                 token_buckets=128, value_scale=scale))
                          for actor, scale in zip(PLAYERS, (10.0, 100.0, 1000.0))}
                with torch.no_grad():
                    for model in models.values():
                        for parameter in model.parameters():
                            parameter.zero_()
                        model.value_head[-1].bias.copy_(torch.tensor((1.25, -2.5, 3.75)))
                evaluator = NeuralEvaluator(models, version="three-scaled-frozen-models-v1")
                envs = [NeuralEnv(actor=i % 3, tag=i) for i in range(6)]
                before = [env.serialize() for env in envs]
                config = MctsConfig(simulations=8, max_depth=1, record_trace=True)
                expected = [VectorMCTS(evaluator, config).search(env) for env in envs]
                for model in models.values():
                    model.batch_sizes.clear()
                stats = BatchStats()
                actual = search_many(envs, evaluator, config, stats=stats)
                for index, (result, reference) in enumerate(zip(actual, expected)):
                    self.assert_same_result(result, reference)
                    scale = models[PLAYERS[index % 3]].config.value_scale
                    self.assertEqual(result.root.evaluation, (1.25 * scale, -2.5 * scale, 3.75 * scale))
                self.assertTrue(all(model.batch_sizes[0] == 2 for model in models.values()),
                                "Each actor model must really process two independent roots in one forward")
                self.assertEqual(stats.batch_sizes[0], 6)
                self.assertEqual([env.serialize() for env in envs], before)
        finally:
            torch.set_num_threads(threads)


if __name__ == "__main__":
    unittest.main()
