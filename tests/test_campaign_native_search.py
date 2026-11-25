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
from studies.campaign.native_search import SearchTree, search_decision
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
from studies.campaign.shared_evaluator import (BUFFER_BYTES, RemoteEvaluator, SharedEvaluatorServer, read_positions,
                                               reply_bytes, several_reply_bytes)
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

    def test_kept_trees_give_the_same_choices(self):
        """Both searches keep their trees from decision to decision along a game."""
        evaluator = HashEvaluator()
        env = make_env(13, calendar_rounds=1)
        rng = random.Random(13)
        python = VectorMCTS(evaluator, MctsConfig(simulations=32, max_depth=16))
        tree = SearchTree()
        checked = reused = 0
        while not env.is_terminal() and checked < 40:
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            seed = rng.getrandbits(64)
            expected = python.search(env, add_root_noise=True, reuse_root=True, seed=seed)
            actual = search_decision(env, evaluator, MctsConfig(simulations=32, max_depth=16, seed=seed),
                                     add_root_noise=True, tree=tree)
            for name in ("visit_counts", "policy", "priors", "values", "action_values", "reused_root"):
                self.assertEqual(getattr(actual, name), getattr(expected, name), f"{name} at decision {checked}")
            self.assertEqual(tree.size, len(python.nodes))
            reused += actual.reused_root
            checked += 1
            env.apply_action(expected.best_action() if rng.random() < 0.5 else rng.choice(expected.actions))
        self.assertGreater(reused, checked * 3 // 4)

    def test_a_tree_starts_anew_when_other_networks_answer(self):
        class Versioned(HashEvaluator):
            network_version = "v1"
            switch_after = None

            def evaluate_zone(self, zone, actor):
                if self.switch_after is not None and self.requests >= self.switch_after:
                    self.network_version = "v3"
                return super().evaluate_zone(zone, actor)

        env = make_env(SEED, calendar_rounds=1)
        while env.decision_kind() == "chance" or len(env.legal_actions()) < 3:
            env.resolve_chance() if env.decision_kind() == "chance" else env.apply_action(env.legal_actions()[0])
        evaluator, tree = Versioned(), SearchTree()
        first = search_decision(env, evaluator, MctsConfig(simulations=16, seed=1), add_root_noise=False, tree=tree)
        self.assertFalse(first.reused_root)
        self.assertGreater(tree.size, 1)
        again = search_decision(env, evaluator, MctsConfig(simulations=16, seed=2), add_root_noise=False, tree=tree)
        self.assertTrue(again.reused_root)
        evaluator.network_version = "v2"  # Another network answers: the old outputs go.
        other = search_decision(env, evaluator, MctsConfig(simulations=16, seed=3), add_root_noise=False, tree=tree)
        self.assertFalse(other.reused_root)
        # A version change during a search leaves a tree built partly by each: dropped.
        evaluator.switch_after = evaluator.requests + 5
        search_decision(env, evaluator, MctsConfig(simulations=16, seed=4), add_root_noise=False, tree=tree)
        self.assertEqual(tree.size, 0)

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


def searched_decisions(seed, *, count, rounds=1):
    """Positions along a game with at least three options, played on at random."""
    env = make_env(seed, calendar_rounds=rounds)
    rng = random.Random(seed)
    found = []
    while not env.is_terminal() and len(found) < count:
        if env.decision_kind() == "chance":
            env.resolve_chance()
            continue
        actions = env.legal_actions()
        if len(actions) >= 3 and rng.random() < 0.3:
            found.append(env.serialize())
        env.apply_action(rng.choice(actions))
    return found


class SeveralSimulationsTests(unittest.TestCase):
    """Simulations gathered into requests of several positions (simulations_per_request)."""

    def at(self, serialized):
        env = make_env(SEED, calendar_rounds=1)
        env.restore(serialized)
        return env

    def test_one_simulation_a_request_is_the_plain_search(self):
        for serialized in searched_decisions(21, count=6):
            env = self.at(serialized)
            config = MctsConfig(simulations=40, max_depth=16, seed=5)
            plain = search_decision(env, HashEvaluator(), config, add_root_noise=True)
            one = search_decision(env, HashEvaluator(), MctsConfig(simulations=40, max_depth=16, seed=5,
                                                                    simulations_per_request=1), add_root_noise=True)
            expected = VectorMCTS(HashEvaluator(), config).search(env, add_root_noise=True, reuse_root=False)
            for name in ("visit_counts", "policy", "priors", "values", "action_values"):
                self.assertEqual(getattr(one, name), getattr(plain, name), name)
                self.assertEqual(getattr(one, name), getattr(expected, name), name)
        with self.assertRaises(ValueError):
            VectorMCTS(HashEvaluator(), MctsConfig(simulations=4, simulations_per_request=2))

    def test_gathered_simulations_spend_the_budget_and_repeat_with_the_seed(self):
        for per_request in (2, 8, 64):
            for serialized in searched_decisions(22, count=5):
                env = self.at(serialized)
                evaluator = HashEvaluator()
                config = MctsConfig(simulations=48, seed=7, max_depth=1000, simulations_per_request=per_request)
                result = search_decision(env, evaluator, config, add_root_noise=True)
                again = search_decision(env, HashEvaluator(), config, add_root_noise=True)
                self.assertEqual(sum(result.visit_counts), 48)
                for name in ("visit_counts", "policy", "values", "action_values"):
                    self.assertEqual(getattr(again, name), getattr(result, name), name)
                # Every question a new position's: nothing is asked twice in a request.
                self.assertLessEqual(evaluator.requests, 49)
                # The visits that lost while waiting spread the simulations over the root's options.
                self.assertGreater(sum(1 for visits in result.visit_counts if visits), 1)

    def test_gathered_simulations_keep_trees_along_a_game(self):
        env = make_env(13, calendar_rounds=1)
        rng = random.Random(13)
        tree, checked, reused = SearchTree(), 0, 0
        while not env.is_terminal() and checked < 30:
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            config = MctsConfig(simulations=32, max_depth=1000, seed=rng.getrandbits(64), simulations_per_request=8)
            result = search_decision(env, HashEvaluator(), config, add_root_noise=True, tree=tree)
            if result.values is not None:
                self.assertGreaterEqual(sum(result.visit_counts), 32)
            reused += result.reused_root
            checked += 1
            env.apply_action(result.best_action() if rng.random() < 0.5 else rng.choice(result.actions))
        self.assertGreater(reused, checked // 2)


class ReusedVisitsTests(unittest.TestCase):
    """A budget that counts the visits the root's actions hold from the reused tree (count_reused_visits)."""

    def test_a_search_runs_only_the_visits_its_root_lacks(self):
        for per_request in (1, 8):
            for serialized in searched_decisions(23, count=4):
                env = make_env(SEED, calendar_rounds=1)
                env.restore(serialized)
                tree, evaluator = SearchTree(), HashEvaluator()

                def search(simulations, seed, counted):
                    config = MctsConfig(simulations=simulations, max_depth=16, seed=seed,
                                        simulations_per_request=per_request, count_reused_visits=counted)
                    return search_decision(env, evaluator, config, add_root_noise=False, tree=tree)

                first = search(40, 3, True)  # A new tree: nothing to count.
                self.assertEqual(sum(first.visit_counts), 40)
                asked = evaluator.requests
                # The same decision again, its root holding the first search's 40 visits.
                same = search(40, 4, True)
                self.assertTrue(same.reused_root)
                self.assertEqual(evaluator.requests, asked)  # No new simulation, so no question.
                for name in ("visit_counts", "policy", "values", "action_values"):
                    self.assertEqual(getattr(same, name), getattr(first, name), name)
                self.assertEqual(sum(search(64, 5, True).visit_counts), 64)  # 24 new ones.
                self.assertEqual(sum(search(24, 6, False).visit_counts), 88)  # 24 on top, uncounted.

    def test_both_searches_count_reused_visits_alike(self):
        """Fast searches along a game, each keeping the tree of the one before."""
        evaluator = HashEvaluator()
        env = make_env(17, calendar_rounds=1)
        rng = random.Random(17)
        python = VectorMCTS(evaluator, MctsConfig(simulations=32, max_depth=16, count_reused_visits=True))
        tree = SearchTree()
        checked = reused = 0
        while not env.is_terminal() and checked < 40:
            if env.decision_kind() == "chance":
                env.resolve_chance()
                continue
            seed = rng.getrandbits(64)
            expected = python.search(env, add_root_noise=False, reuse_root=True, seed=seed)
            config = MctsConfig(simulations=32, max_depth=16, seed=seed, count_reused_visits=True)
            actual = search_decision(env, evaluator, config, add_root_noise=False, tree=tree)
            for name in ("visit_counts", "policy", "priors", "values", "action_values", "reused_root"):
                self.assertEqual(getattr(actual, name), getattr(expected, name), f"{name} at decision {checked}")
            self.assertEqual(tree.size, len(python.nodes))
            if actual.values is not None:
                self.assertGreaterEqual(sum(actual.visit_counts), 32)
            reused += actual.reused_root
            checked += 1
            env.apply_action(expected.best_action() if rng.random() < 0.5 else rng.choice(expected.actions))
        self.assertGreater(reused, checked * 3 // 4)


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

    def test_several_positions_in_one_request_reach_their_own_answers(self):
        """A stand-in server answers each position of a request of several with
        HashEvaluator's numbers for its arrays: the search through it is the search
        with HashEvaluator in the process, so each answer reached its own position."""
        class Zone:
            def __init__(self, arrays, count):
                self._arrays, self.action_count = arrays, count

            def arrays(self):
                return self._arrays

        for serialized in searched_decisions(23, count=4):
            env = make_env(SEED, calendar_rounds=1)
            env.restore(serialized)
            memory = shared_memory.SharedMemory(create=True, size=BUFFER_BYTES)
            server_end, client_end = Pipe()
            counts = {"requests": 0, "several": 0, "positions": 0}

            def answer():
                hashing = HashEvaluator()
                while True:
                    try:
                        message = server_end.recv_bytes()
                    except (EOFError, OSError):
                        return
                    positions, _, several = read_positions(memory.buf, message)
                    answers = []
                    for actor, count, arrays in positions:
                        evaluation = hashing.evaluate_zone(Zone({k: v.copy() for k, v in arrays.items()}, count), actor)
                        answers.append((evaluation.priors, evaluation.values))
                    del arrays
                    counts["requests"] += 1
                    counts["several"] += several
                    counts["positions"] += len(positions)
                    server_end.send_bytes(several_reply_bytes(answers, None) if several
                                          else reply_bytes(answers[0][0], answers[0][1], None))

            serving = threading.Thread(target=answer, daemon=True)
            serving.start()
            try:
                config = MctsConfig(simulations=40, max_depth=1000, seed=3, simulations_per_request=8)
                evaluator = RemoteEvaluator(client_end, memory.name, "test", native=True)
                served = search_decision(env, evaluator, config, add_root_noise=True)
                in_process = search_decision(env, HashEvaluator(), config, add_root_noise=True)
                for name in ("visit_counts", "policy", "priors", "values", "action_values"):
                    self.assertEqual(getattr(served, name), getattr(in_process, name), name)
                self.assertEqual(evaluator.client.evaluations, counts["positions"])
                self.assertEqual(evaluator.client.requests, counts["requests"])
                self.assertGreater(counts["several"], 0)
                self.assertLess(counts["requests"], counts["positions"])
                evaluator.client.close()
            finally:
                server_end.close()
                client_end.close()
                serving.join(timeout=10)
                memory.close()
                memory.unlink()

    def test_the_inference_server_answers_requests_of_several_positions(self):
        torch.manual_seed(SEED)
        model = CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=16, message_layers=1)).eval()
        models = {player: model for player in PLAYERS}
        env = make_env(SEED, calendar_rounds=1)
        while env.decision_kind() == "chance" or len(env.legal_actions()) < 3:
            env.resolve_chance() if env.decision_kind() == "chance" else env.apply_action(env.legal_actions()[0])
        memory = shared_memory.SharedMemory(create=True, size=BUFFER_BYTES)
        server_end, client_end = Pipe()
        try:
            server = SharedEvaluatorServer(models, torch.device("cpu"), [server_end], [memory.name])
            serving = threading.Thread(target=server.serve, args=(lambda: True,), daemon=True)
            serving.start()
            evaluator = RemoteEvaluator(client_end, memory.name, "test", native=True)
            config = MctsConfig(simulations=48, max_depth=1000, seed=9, simulations_per_request=8)
            result = search_decision(env, evaluator, config, add_root_noise=True)
            client = evaluator.client
            evaluations, requests = client.evaluations, client.requests
            evaluator.close()
            serving.join(timeout=60)
            self.assertFalse(serving.is_alive())
            self.assertEqual(sum(result.visit_counts), 48)
            self.assertEqual((server.stats.evaluations, server.stats.requests), (evaluations, requests))
            self.assertLess(requests, evaluations)
            self.assertEqual(sum(size * count for size, count in server.stats.positions_per_pass.items()), evaluations)
            reference = NeuralEvaluator(models, version="test").evaluate(env, result.actions)
            for got, want in zip(result.priors, reference.priors, strict=True):
                self.assertAlmostEqual(got, want, delta=1e-5)
            server.close()
        finally:
            memory.close()
            memory.unlink()
            server_end.close()
            client_end.close()


if __name__ == "__main__":
    unittest.main()
