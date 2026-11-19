"""The C++ search makes the Python search's choices: same draws, same sums, same results."""
from __future__ import annotations

import hashlib
from multiprocessing import Pipe, shared_memory
import random
import threading
import unittest

import torch

import gwrl_cpp

from studies.campaign.curriculum import make_env
from studies.campaign.features import make_zone_input
from studies.campaign.native_search import search_decision
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
from studies.campaign.shared_evaluator import BUFFER_BYTES, RemoteEvaluator, SharedEvaluatorServer
from studies.shared.multiplayer_mcts import (PLAYERS, Evaluation, MctsConfig, NoLegalActionError, UniformEvaluator,
                                             VectorMCTS, vector)

SEED = 1951


class HashEvaluator:
    """Priors and values that depend only on the position's zone input, as frozen weights do."""
    version = "zone-hash-v1"

    def __init__(self):
        self.requests = 0

    def evaluate(self, env, actions):  # The Python search's way in.
        if env.is_terminal():
            return Evaluation([], vector(env.returns()))
        actor = env.current_decision_player()
        return self.evaluate_zone(make_zone_input(env, actions if actor is not None else ()), actor)

    def evaluate_zone(self, zone, actor):  # The C++ search's way in.
        self.requests += 1
        arrays = zone.arrays()
        digest = hashlib.sha256(b"".join(arrays[name].tobytes() for name in sorted(arrays)) + str(actor).encode()).digest()
        rng = random.Random(digest)
        return Evaluation([rng.random() + 0.01 for _ in range(zone.action_count)],
                          (rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(-50, 50)))


class PythonDrawTests(unittest.TestCase):
    def test_the_generator_draws_what_python_draws(self):
        for seed in (0, 1, 2**32 - 1, 2**32, 2**63 + 12345, 2**64 - 1):
            python, native = random.Random(seed), gwrl_cpp.PythonRandom(seed)
            for step in range(700):
                kind = step % 6
                if kind == 0:
                    self.assertEqual(python.random(), native.random())
                elif kind == 1:
                    self.assertEqual(python.getrandbits(64), native.getrandbits64())
                elif kind == 2:
                    bound = 1 + step % 13
                    self.assertEqual(python.randrange(bound), native.randbelow(bound))
                else:
                    alpha = (0.3, 1.0, 2.5)[kind - 3]
                    self.assertEqual(python.gammavariate(alpha, 1.0), native.gammavariate(alpha, 1.0))

    def test_sums_round_as_python_sums(self):
        rng = random.Random(SEED)
        for _ in range(3000):
            values = [rng.choice((rng.random(), -rng.random() * 1e6, rng.random() * 1e-12, 1e16, -1e16, 0.1))
                      for _ in range(rng.randrange(60))]
            self.assertEqual(gwrl_cpp.python_sum(values), sum(values))


class SameChoicesTests(unittest.TestCase):
    def assertSameSearches(self, evaluator, *, rounds, decisions, simulations, seed):
        """Both searches at each decision along a game, which plays the searched moves."""
        env = make_env(seed, calendar_rounds=rounds)
        rng = random.Random(seed)
        kinds, checked = set(), 0
        while not env.is_terminal() and checked < decisions:
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            config = MctsConfig(simulations=simulations, max_depth=16, seed=rng.getrandbits(64))
            expected = VectorMCTS(evaluator, config).search(env, add_root_noise=True, reuse_root=False)
            actual = search_decision(env, evaluator, config, add_root_noise=True)
            kind = env.decision_kind()
            for name in ("visit_counts", "policy", "priors", "values", "action_values"):
                self.assertEqual(getattr(actual, name), getattr(expected, name), f"{name} at decision {checked}, {kind}")
            self.assertEqual([action.id for action in actual.actions], [action.id for action in expected.actions])
            if actual.zone_input is not None:  # The root's input, as the adapter encodes it.
                self.assertEqual(actual.zone_input, make_zone_input(env, actual.actions))
            kinds.add(kind)
            checked += 1
            env.apply_action(expected.best_action() if rng.random() < 0.5 else rng.choice(expected.actions))
        self.assertEqual(checked, decisions)
        return kinds

    def test_network_outputs_give_the_same_choices(self):
        kinds = set()
        for seed in (11, 13):
            kinds |= self.assertSameSearches(HashEvaluator(), rounds=1, decisions=40, simulations=32, seed=seed)
        # Declaration offers come from the scheduling around the engine, which both apply.
        self.assertIn("declaration_offer", kinds)
        self.assertGreater(len(kinds), 6)

    def test_uniform_priors_break_ties_with_the_same_draws(self):
        self.assertSameSearches(UniformEvaluator(), rounds=2, decisions=60, simulations=48, seed=12)

    def test_a_forced_root_is_returned_or_searched_as_asked(self):
        env = make_env(SEED, calendar_rounds=1)
        rng = random.Random(SEED)
        while env.decision_kind() == "chance" or len(env.legal_actions()) != 1:
            env.resolve_chance() if env.decision_kind() == "chance" else env.apply_action(rng.choice(env.legal_actions()))
        evaluator = HashEvaluator()
        skipped = search_decision(env, evaluator, MctsConfig(simulations=8, seed=3), add_root_noise=True)
        self.assertEqual((skipped.visit_counts, skipped.policy, skipped.values, evaluator.requests), ([0], [1.0], None, 0))
        self.assertIsNone(skipped.zone_input)
        config = MctsConfig(simulations=8, seed=3, search_forced_root=True)
        searched = search_decision(env, evaluator, config, add_root_noise=True)
        expected = VectorMCTS(evaluator, config).search(env, add_root_noise=True, reuse_root=False)
        self.assertEqual((searched.visit_counts, searched.values), (expected.visit_counts, expected.values))
        self.assertEqual(searched.visit_counts, [8])

    def test_the_search_leaves_the_game_alone_and_refuses_other_modes(self):
        env = make_env(SEED, calendar_rounds=1)
        before = env.serialize()
        search_decision(env, HashEvaluator(), MctsConfig(simulations=16, seed=5), add_root_noise=True)
        self.assertEqual(env.serialize(), before)
        with self.assertRaises(ValueError):
            search_decision(env, HashEvaluator(), MctsConfig(simulations=4, record_trace=True), add_root_noise=False)
        with self.assertRaises(TypeError):
            search_decision(env, object(), MctsConfig(simulations=4), add_root_noise=False)

    def test_an_evaluator_failure_reaches_the_caller(self):
        class Failing(HashEvaluator):
            def evaluate_zone(self, zone, actor):
                raise KeyError("network unavailable")
        env = make_env(SEED, calendar_rounds=1)
        with self.assertRaisesRegex(KeyError, "network unavailable"):
            search_decision(env, Failing(), MctsConfig(simulations=4), add_root_noise=False)
        self.assertTrue(issubclass(gwrl_cpp.NoLegalSearchAction, ValueError))
        self.assertTrue(issubclass(NoLegalActionError, ValueError))


class InferenceServerTests(unittest.TestCase):
    def served_search(self, models, env, *, native):
        """A search whose evaluations an inference server answers, one at a time."""
        memory = shared_memory.SharedMemory(create=True, size=BUFFER_BYTES)
        server_end, client_end = Pipe()
        try:
            server = SharedEvaluatorServer(models, torch.device("cpu"), [server_end], [memory.name])
            serving = threading.Thread(target=server.serve, args=(lambda: True,), daemon=True)
            serving.start()
            evaluator = RemoteEvaluator(client_end, memory.name, "test", native=native)
            result = search_decision(env, evaluator, MctsConfig(simulations=24, seed=9), add_root_noise=True)
            requests = evaluator.stats.requests
            evaluator.close()
            serving.join(timeout=60)
            self.assertFalse(serving.is_alive())
            self.assertEqual(requests, server.stats.requests)
            server.close()
            return result, requests
        finally:
            memory.close()
            memory.unlink()
            server_end.close()
            client_end.close()

    def test_a_search_through_the_inference_server_asks_what_the_network_answers(self):
        torch.manual_seed(SEED)
        model = CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=16, message_layers=1)).eval()
        models = {player: model for player in PLAYERS}
        env = make_env(SEED, calendar_rounds=1)
        while env.decision_kind() == "chance" or len(env.legal_actions()) < 3:
            env.resolve_chance() if env.decision_kind() == "chance" else env.apply_action(env.legal_actions()[0])
        result, requests = self.served_search(models, env, native=True)
        self.assertEqual(sum(result.visit_counts), 24)
        self.assertGreater(requests, 1)
        # The root's priors are the network's, as an in-process evaluation gives them.
        reference = NeuralEvaluator(models, version="test").evaluate(env, result.actions)
        for got, want in zip(result.priors, reference.priors, strict=True):
            self.assertAlmostEqual(got, want, delta=1e-5)
        # Python's messages, as on Windows, carry the same numbers: the same search.
        python, python_requests = self.served_search(models, env, native=False)
        self.assertEqual(python_requests, requests)
        for name in ("visit_counts", "policy", "priors", "values", "action_values"):
            self.assertEqual(getattr(python, name), getattr(result, name), name)


if __name__ == "__main__":
    unittest.main()
