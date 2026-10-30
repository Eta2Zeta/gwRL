"""The shared evaluator answers as NeuralEvaluator does, through real pipes and shared memory."""
from __future__ import annotations

from dataclasses import asdict
from multiprocessing import Pipe, shared_memory
import queue
import random
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np
import torch

from studies.campaign.curriculum import make_env
from studies.campaign.features import make_numeric_input
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
from studies.campaign.shared_evaluator import (EvaluatorClosed, RemoteEvaluator, SharedEvaluatorServer, _Contexts,
                                               _graph_arrays, evaluate_prepared, prepare, prepare_into, read_arrays)
from studies.shared.multiplayer_mcts import PLAYERS, MctsConfig, UniformEvaluator, VectorMCTS
from tools.benchmark_campaign_devices import Config, _shared_game_process

BUCKETS = 2048
SEED = 1951


def positions(count=5):
    """Decision positions with menus of several sizes and one chance position."""
    env = make_env(SEED, calendar_rounds=2)
    rng = random.Random(SEED)
    decisions, chance = [], None
    for _ in range(4000):
        if env.is_terminal() or (len(decisions) >= count and chance is not None):
            break
        if env.decision_kind() == "chance":
            chance = chance or env.serialize()
            env.resolve_chance()
            continue
        actions = list(env.legal_actions())
        if len(decisions) < count and len(actions) > 2 and rng.random() < .2:
            decisions.append(env.serialize())
        ending = [action for action in actions if action.id.endswith(":play:end_phase")]
        env.apply_action(ending[0] if ending and rng.random() < .1 else rng.choice(actions))
    return decisions, chance


def restore(serialized):
    env = make_env(SEED, calendar_rounds=2)
    env.restore(serialized)
    return env


def factor_levels(factors):
    """The four factor levels of CampaignPolicyValueNet._factor_layout, by Python's own sorting."""
    out, parent_counts = {}, []
    factors = [tuple(factor) for factor in factors]
    for level in range(1, 5):
        prefixes = sorted({factor[:level] for factor in factors})
        lookup = {prefix: index for index, prefix in enumerate(prefixes)}
        owners = np.fromiter((lookup[factor[:level]] for factor in factors), dtype=np.int32, count=len(factors))
        parents = {prefix: index for index, prefix in enumerate(sorted({prefix[:-1] for prefix in prefixes}))}
        out[f"f{level}_owners"] = owners
        out[f"f{level}_counts"] = np.bincount(owners, minlength=len(prefixes)).astype(np.int32)
        out[f"f{level}_parents"] = np.fromiter((parents[prefix[:-1]] for prefix in prefixes), dtype=np.int32,
                                               count=len(prefixes))
        parent_counts.append(len(parents))
    out["f_parent_counts"] = np.asarray(parent_counts, dtype=np.int32)
    return out


def reference_arrays(env, actions, buckets):
    """A position's arrays joined graph by graph in Python, which the native writer must equal."""
    packed = make_numeric_input(env, tuple(actions), buckets)["packed_graph"]
    context, observation, menu = packed["context"], packed["observation"], packed["actions"]
    arrays = _graph_arrays(observation, "obs_")
    destinations, indices = observation.external_references(context)
    arrays["obs_ref_dest"] = np.asarray(destinations, dtype=np.int32)
    arrays["obs_ref_index"] = np.asarray(indices, dtype=np.int32)
    parts = {name: [] for name in ("ids", "offsets", "types", "numbers", "sources", "targets", "relations",
                                   "obs_dest", "obs_index", "ctx_dest", "ctx_index")}
    nodes, node_start, token_start = [], 0, 0
    for graph in menu:
        block = _graph_arrays(graph, "")
        parts["ids"].append(block["ids"])
        parts["offsets"].append(block["offsets"][:-1] + token_start)
        for name in ("types", "numbers", "relations"):
            parts[name].append(block[name])
        parts["sources"].append(block["sources"] + node_start)
        parts["targets"].append(block["targets"] + node_start)
        for bank, other in (("obs", observation), ("ctx", context)):
            destination, index = graph.external_references(other)
            parts[bank + "_dest"].append(np.asarray(destination, dtype=np.int32) + node_start)
            parts[bank + "_index"].append(np.asarray(index, dtype=np.int32))
        nodes.append(graph.node_count)
        node_start += graph.node_count
        token_start += len(block["ids"])
    empty = {"numbers": np.zeros((0, arrays["obs_numbers"].shape[1]), dtype=np.float32)}
    for name, values in parts.items():
        arrays["act_" + name] = np.concatenate(values) if values else empty.get(name, np.zeros(0, dtype=np.int32))
    arrays["act_offsets"] = np.append(arrays["act_offsets"], np.int32(token_start)).astype(np.int32)
    arrays["act_nodes"] = np.asarray(nodes, dtype=np.int32)
    arrays.update(factor_levels(packed["action_factors"]) if menu else {})
    return arrays


class NativeEvaluationArraysTests(unittest.TestCase):
    def assertSameArrays(self, got, expected):
        self.assertEqual(list(got), list(expected))
        for name, value in expected.items():
            self.assertEqual((got[name].dtype, got[name].shape), (value.dtype, value.shape), name)
            self.assertEqual(got[name].tobytes(), value.tobytes(), name)

    def assertMatchesReference(self, env, actions):
        self.assertSameArrays(prepare(env, actions, BUCKETS)[1], reference_arrays(env, actions, BUCKETS))

    def test_random_play_and_search_positions_match_the_reference_exactly(self):
        checked = self
        positions_checked = []

        class Checking(UniformEvaluator):
            def evaluate(self, env, actions):
                checked.assertMatchesReference(env, actions)
                positions_checked.append(len(actions))
                return super().evaluate(env, actions)

        env = make_env(SEED, calendar_rounds=2)
        rng = random.Random(SEED)
        searches = 0
        for step in range(600):
            if env.is_terminal():
                break
            if env.decision_kind() == "chance":
                self.assertMatchesReference(env, ())
                env.resolve_chance()
                continue
            actions = tuple(env.legal_actions())
            if step % 40 == 0:
                self.assertMatchesReference(env, actions)
                self.assertMatchesReference(env, ())
                self.assertMatchesReference(env, tuple(reversed(actions[::2])))
            if step % 150 == 0:
                VectorMCTS(Checking(), MctsConfig(simulations=8, max_depth=8, seed=step)).search(env)
                searches += 1
            env.apply_action(rng.choice(actions))
        self.assertGreater(searches, 2)
        self.assertGreater(max(positions_checked), 20)

    def test_the_header_lays_arrays_out_as_shared_memory_needs(self):
        env = make_env(SEED, calendar_rounds=2)
        actions = tuple(env.legal_actions())
        buffer = memoryview(bytearray(1 << 23))
        key, header, context = prepare_into(buffer, env, actions, BUCKETS)
        self.assertEqual(key, make_numeric_input(env, actions, BUCKETS)["context_key"])
        self.assertIs(context, make_numeric_input(env, actions, BUCKETS)["packed_graph"]["context"])
        end = 0
        for name, dtype, shape, offset in header:
            self.assertEqual(offset, (end + 15) & ~15, name)
            end = offset + int(np.prod(shape)) * np.dtype(dtype).itemsize
        self.assertSameArrays(read_arrays(buffer, header), reference_arrays(env, actions, BUCKETS))
        with self.assertRaisesRegex(ValueError, "exceeds its shared-memory buffer"):
            prepare_into(memoryview(bytearray(end - 1)), env, actions, BUCKETS)
        self.assertEqual(len(prepare_into(memoryview(bytearray(end)), env, actions, BUCKETS)[1]), len(header))

    def test_factor_levels_sort_strings_by_code_point_as_python_does(self):
        env = make_env(SEED, calendar_rounds=2)
        packed = make_numeric_input(env, tuple(env.legal_actions()), BUCKETS)["packed_graph"]
        factors = (("b", "\U00010000", "a", "z"), ("b", "\uffff", "a", "z"), ("a", "", "é", "z"),
                   ("b", "\uffff", "a", "y"), ("b", "\uffff", "a", "z"), ("", "", "", ""), ("海軍", "", "", ""))
        expected = factor_levels(factors)
        graphs = (packed["actions"][0],) * len(factors)
        buffer = memoryview(bytearray(1 << 23))
        arrays = read_arrays(buffer, packed["observation"].write_evaluation(buffer, packed["context"], graphs, factors))
        self.assertSameArrays({name: arrays[name] for name in expected}, expected)

    def test_a_bad_menu_is_refused(self):
        env = make_env(SEED, calendar_rounds=2)
        packed = make_numeric_input(env, tuple(env.legal_actions()), BUCKETS)["packed_graph"]
        buffer = memoryview(bytearray(1 << 23))
        observation, context, graph = packed["observation"], packed["context"], packed["actions"][0]
        with self.assertRaisesRegex(ValueError, "menu and factors disagree"):
            observation.write_evaluation(buffer, context, (graph,), ())
        with self.assertRaises(TypeError):
            observation.write_evaluation(buffer, context, (None,), (("a", "b", "c", "d"),))
        with self.assertRaises(TypeError):
            observation.write_evaluation(buffer, context, (graph,), (("a", "b", "c"),))
        with self.assertRaises(BufferError):
            observation.write_evaluation(bytes(1 << 23), context, (graph,), (("a", "b", "c", "d"),))


class SharedEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(SEED)
        config = CampaignModelConfig(hidden_dim=16, message_layers=1, token_buckets=BUCKETS)
        cls.models = {player: CampaignPolicyValueNet(config).eval() for player in PLAYERS}
        cls.reference = NeuralEvaluator(cls.models, version="test")
        cls.decisions, cls.chance = positions()
        assert len(cls.decisions) >= 3 and cls.chance is not None

    def assertMatches(self, got_priors, got_values, expected):
        self.assertEqual(len(got_priors), len(expected.priors))
        for got, want in zip(got_priors, expected.priors):
            self.assertAlmostEqual(got, want, delta=1e-5)
        for got, want in zip(got_values, expected.values):
            self.assertAlmostEqual(got, want, delta=1e-3)

    def test_prepared_forward_matches_one_position_and_a_merged_batch(self):
        envs = [restore(text) for text in self.decisions]
        menus = [tuple(env.legal_actions()) for env in envs]
        expected = [self.reference.evaluate_batch([(env, menu)])[0] for env, menu in zip(envs, menus)]
        prepared = [prepare(env, menu, BUCKETS) for env, menu in zip(envs, menus)]
        contexts = _Contexts()
        for key, _, context in prepared:
            contexts.arrays.setdefault(key, {**_graph_arrays(context, "ctx_"),
                                             "ctx_nodes": torch.tensor([context.node_count]).numpy()})
        with torch.inference_mode():
            for row, (env, (key, arrays, _)) in enumerate(zip(envs, prepared)):
                priors, values = evaluate_prepared(self.models[env.current_decision_player()], [(key, arrays)],
                                                   contexts, torch.device("cpu"))
                self.assertMatches(priors[0], values[0], expected[row])
            # Every position through one model, alone and merged, exercises each offset.
            model = self.models[PLAYERS[0]]
            alone = [evaluate_prepared(model, [item[:2]], contexts, torch.device("cpu")) for item in prepared]
            priors, values = evaluate_prepared(model, [item[:2] for item in prepared], contexts, torch.device("cpu"))
            for (one_priors, one_values), prior, value in zip(alone, priors, values, strict=True):
                for got, want in zip(prior, one_priors[0], strict=True):
                    self.assertAlmostEqual(got, want, delta=1e-6)
                for got, want in zip(value, one_values[0], strict=True):
                    self.assertAlmostEqual(got, want, delta=1e-4)
            # A depth cutoff evaluates a decision position without its menu.
            env = envs[0]
            key, arrays, _ = prepare(env, (), BUCKETS)
            priors, values = evaluate_prepared(self.models[env.current_decision_player()], [(key, arrays)],
                                               contexts, torch.device("cpu"))
            self.assertMatches(priors[0], values[0], self.reference.evaluate_batch([(env, ())])[0])

    def test_server_answers_decisions_and_chance_cutoffs_through_pipes(self):
        memories = [shared_memory.SharedMemory(create=True, size=8 << 20) for _ in range(2)]
        pipes = [Pipe() for _ in memories]
        try:
            server = SharedEvaluatorServer(self.models, torch.device("cpu"), [parent for parent, _ in pipes],
                                           [memory.name for memory in memories])
            serving = threading.Thread(target=server.serve, args=(lambda: True,), daemon=True)
            serving.start()
            results = {}
            def client(index, serialized_states):
                evaluator = RemoteEvaluator(pipes[index][1], memories[index].name, BUCKETS, "test")
                try:
                    for serialized in serialized_states:
                        env = restore(serialized)
                        menu = () if env.decision_kind() == "chance" else tuple(env.legal_actions())
                        results[serialized] = (evaluator.evaluate(env, menu), env, menu)
                finally:
                    evaluator.close()
            clients = [threading.Thread(target=client, args=(0, self.decisions[:2])),
                       threading.Thread(target=client, args=(1, [self.chance, self.decisions[2]]))]
            for thread in clients:
                thread.start()
            for thread in clients:
                thread.join(timeout=120)
            serving.join(timeout=30)
            self.assertFalse(serving.is_alive(), "The server did not stop after every client closed")
            self.assertEqual(len(results), 4)
            for evaluation, env, menu in results.values():
                self.assertMatches(evaluation.priors, evaluation.values, self.reference.evaluate_batch([(env, menu)])[0])
            stats = server.stats
            self.assertEqual(stats.requests, 4)
            self.assertEqual(sum(size * count for size, count in stats.requests_per_round.items()), 4)
            # Three decisions take one model forward each; the chance cutoff takes all three.
            self.assertEqual(sum(size * count for size, count in stats.positions_per_forward.items()), 6)
            self.assertEqual(stats.forwards, sum(stats.positions_per_forward.values()))
            server.close()
        finally:
            for memory in memories:
                memory.close()
                memory.unlink()

    def test_a_closed_pipe_raises_evaluator_closed(self):
        memory = shared_memory.SharedMemory(create=True, size=8 << 20)
        env = restore(self.decisions[0])
        menu = tuple(env.legal_actions())
        def cause(evaluator):
            # Only the type is kept: a stored exception would hold a failed
            # send's buffers in a reference cycle, freed out of order later.
            try:
                evaluator.evaluate(env, menu)
            except EvaluatorClosed as error:
                return type(error.__cause__)
            return None
        def read_then_close(connection):
            connection.recv()
            connection.close()
        try:
            # A request read but never answered: the reply's recv meets EOF.
            server_end, client_end = Pipe()
            evaluator = RemoteEvaluator(client_end, memory.name, BUCKETS, "test")
            threading.Thread(target=read_then_close, args=(server_end,), daemon=True).start()
            self.assertIs(cause(evaluator), EOFError)
            evaluator.close()
            # A stopped server closes the pipes still open, so a thread waiting
            # on its request stops, and nothing more can be sent.
            server_end, client_end = Pipe()
            server = SharedEvaluatorServer(self.models, torch.device("cpu"), [server_end], [memory.name])
            evaluator = RemoteEvaluator(client_end, memory.name, BUCKETS, "test")
            causes = []
            waiting = threading.Thread(target=lambda: causes.append(cause(evaluator)), daemon=True)
            waiting.start()
            self.assertTrue(server_end.poll(120), "The request never arrived")
            server.serve(lambda: False)
            waiting.join(timeout=30)
            self.assertTrue(server_end.closed)
            self.assertEqual(len(causes), 1)
            self.assertTrue(causes[0] is not None and issubclass(causes[0], (EOFError, OSError)), causes[0])
            self.assertIs(cause(evaluator), BrokenPipeError)
            self.assertEqual((evaluator.stats.requests, server.stats.requests), (0, 0))
            evaluator.close()
            server.close()
        finally:
            memory.close()
            memory.unlink()


class SharedGameSlotTests(unittest.TestCase):
    def test_an_unexpected_exception_fails_only_its_game(self):
        config = Config(mode="selfplay", search_evaluation="per_search", threads=1, devices=("mps",), processes=2,
                        games_per_process=2, seeds=(1, 2, 3, 4))
        memory = shared_memory.SharedMemory(create=True, size=1 << 20)
        parent, child = Pipe()
        tasks, results = queue.Queue(), queue.Queue()
        for seed in (1, 2, None):
            tasks.put(seed)
        def play(config, seed, evaluator, deadline_epoch):
            if seed == 1:
                raise KeyError("boom")
            return {"seed": seed, "terminal": True, "failure": None}
        try:
            with patch("tools.benchmark_campaign_devices.play_shared_game", side_effect=play):
                _shared_game_process(asdict(config), [5], [child], [memory.name], tasks, results, time.time() + 60,
                                     "test")
        finally:
            parent.close()
            memory.close()
            memory.unlink()
        failed, played = results.get_nowait(), results.get_nowait()
        self.assertTrue(results.empty())
        self.assertEqual((failed["seed"], failed["terminal"], failed["stop_reason"], failed["slot"]),
                         (1, False, "game_exception", 5))
        self.assertEqual(failed["failure"]["error"], "KeyError: 'boom'")
        self.assertIn('raise KeyError("boom")', failed["failure"]["traceback"])
        self.assertLessEqual(failed["started_at_epoch"], failed["ended_at_epoch"])
        self.assertEqual((failed["evaluations"], failed["timing_seconds"]), (0, {}))
        self.assertEqual((played["seed"], played["slot"]), (2, 5))  # The slot played on.


class SharedModeConfigTests(unittest.TestCase):
    def test_several_games_per_process_need_process_parallel_mps_self_play(self):
        common = dict(mode="selfplay", search_evaluation="per_search", threads=1, seeds=(1, 2, 3, 4))
        Config(**common, devices=("mps",), processes=2, games_per_process=2)
        for bad in (dict(devices=("mps",), processes=1), dict(devices=("cpu",), processes=2),
                    dict(devices=("cpu", "mps"), processes=2)):
            with self.subTest(**bad), self.assertRaises(ValueError):
                Config(**{**common, **bad}, games_per_process=2)
        with self.assertRaises(ValueError):
            Config(**common, devices=("mps",), processes=2, games_per_process=0)

    def test_shared_self_play_needs_a_game_for_every_slot(self):
        common = dict(mode="selfplay", search_evaluation="per_search", threads=1, devices=("mps",), processes=2,
                      games_per_process=2)
        Config(**common, seeds=(1, 2, 3, 4))
        with self.assertRaisesRegex(ValueError, "every game slot"):
            Config(**common, seeds=(1, 2, 3))

    def test_paired_runs_need_one_process_for_trace_comparison(self):
        common = dict(mode="selfplay", search_evaluation="per_search", threads=1, seeds=(1, 2, 3, 4))
        Config(**common, devices=("cpu", "mps"))
        for devices in (("cpu",), ("mps",)):
            Config(**common, devices=devices, processes=2)
        with self.assertRaisesRegex(ValueError, "per-game traces"):
            Config(**common, devices=("cpu", "mps"), processes=2)


if __name__ == "__main__":
    unittest.main()
