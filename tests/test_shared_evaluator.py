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
from studies.campaign.features import make_zone_input
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
from studies.campaign.shared_evaluator import (BUFFER_BYTES, EvaluatorClosed, RemoteEvaluator, SharedEvaluatorServer,
                                               evaluate_prepared, prepare_into, read_arrays)
from studies.shared.multiplayer_mcts import PLAYERS, MctsConfig, UniformEvaluator, VectorMCTS
from tools.benchmark_campaign_devices import Config, _shared_game_process

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


def prepared(env, actions):
    """A decision's arrays as a game thread writes them and the server reads them."""
    buffer = memoryview(bytearray(BUFFER_BYTES))
    layout, header = prepare_into(buffer, env, actions)
    return layout, {name: array.copy() for name, array in read_arrays(buffer, header).items()}


class SharedBufferTests(unittest.TestCase):
    def assertSameArrays(self, got, expected):
        self.assertEqual(sorted(got), sorted(expected))
        for name, value in expected.items():
            self.assertEqual((got[name].dtype, got[name].shape), (value.dtype, value.shape), name)
            self.assertEqual(got[name].tobytes(), value.tobytes(), name)

    def assertTravelsExactly(self, env, actions):
        layout, arrays = prepared(env, actions)
        zone = make_zone_input(env, actions)
        self.assertEqual(layout, zone.version)
        self.assertSameArrays(arrays, zone.arrays())

    def test_random_play_and_search_positions_travel_exactly(self):
        checked = self
        sizes = []

        class Checking(UniformEvaluator):
            def evaluate(self, env, actions):
                checked.assertTravelsExactly(env, actions)
                sizes.append(len(actions))
                return super().evaluate(env, actions)

        env = make_env(SEED, calendar_rounds=2)
        rng = random.Random(SEED)
        searches, next_search = 0, 0
        for step in range(600):
            if env.is_terminal():
                break
            if env.decision_kind() == "chance":
                self.assertTravelsExactly(env, ())
                env.resolve_chance()
                continue
            actions = tuple(env.legal_actions())
            if step % 40 == 0:
                for menu in (actions, (), tuple(reversed(actions[::2])), tuple(reversed(actions))):
                    self.assertTravelsExactly(env, menu)
            if step >= next_search:  # The first decision at or after every 150th step.
                VectorMCTS(Checking(), MctsConfig(simulations=8, max_depth=8, seed=step)).search(env)
                searches, next_search = searches + 1, next_search + 150
            env.apply_action(rng.choice(actions))
        self.assertGreater(searches, 2)
        self.assertGreater(max(sizes), 20)

    def test_the_header_packs_arrays_and_a_short_buffer_is_refused(self):
        env = make_env(SEED, calendar_rounds=2)
        actions = tuple(env.legal_actions())
        buffer = memoryview(bytearray(BUFFER_BYTES))
        _, header = prepare_into(buffer, env, actions)
        end = 0
        for name, dtype, shape, offset in header:
            self.assertEqual(offset, end, name)
            end = offset + int(np.prod(shape)) * np.dtype(dtype).itemsize
        self.assertEqual(end, make_zone_input(env, actions).nbytes)
        with self.assertRaisesRegex(ValueError, "does not fit"):
            prepare_into(memoryview(bytearray(end - 1)), env, actions)
        self.assertEqual(len(prepare_into(memoryview(bytearray(end)), env, actions)[1]), len(header))


class SharedEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(SEED)
        config = CampaignModelConfig(hidden_dim=16, message_layers=1)
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
        items = [prepared(env, menu)[1] for env, menu in zip(envs, menus)]
        cpu = torch.device("cpu")
        with torch.inference_mode():
            for row, (env, arrays) in enumerate(zip(envs, items)):
                priors, values = evaluate_prepared(self.models[env.current_decision_player()], [arrays], cpu)
                self.assertMatches(priors[0], values[0], expected[row])
            # Every position through one model, alone and merged, exercises each offset.
            model = self.models[PLAYERS[0]]
            alone = [evaluate_prepared(model, [arrays], cpu) for arrays in items]
            priors, values = evaluate_prepared(model, items, cpu)
            for (one_priors, one_values), prior, value in zip(alone, priors, values, strict=True):
                for got, want in zip(prior, one_priors[0], strict=True):
                    self.assertAlmostEqual(got, want, delta=1e-6)
                for got, want in zip(value, one_values[0], strict=True):
                    self.assertAlmostEqual(got, want, delta=1e-4)
            # A depth cutoff evaluates a decision position without its menu.
            env = envs[0]
            priors, values = evaluate_prepared(self.models[env.current_decision_player()], [prepared(env, ())[1]], cpu)
            self.assertMatches(priors[0], values[0], self.reference.evaluate_batch([(env, ())])[0])

    def test_server_answers_decisions_and_chance_cutoffs_through_pipes(self):
        memories = [shared_memory.SharedMemory(create=True, size=BUFFER_BYTES) for _ in range(2)]
        pipes = [Pipe() for _ in memories]
        try:
            server = SharedEvaluatorServer(self.models, torch.device("cpu"), [parent for parent, _ in pipes],
                                           [memory.name for memory in memories])
            serving = threading.Thread(target=server.serve, args=(lambda: True,), daemon=True)
            serving.start()
            results = {}
            def client(index, serialized_states):
                evaluator = RemoteEvaluator(pipes[index][1], memories[index].name, "test")
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

    def test_a_request_of_another_layout_is_refused(self):
        memory = shared_memory.SharedMemory(create=True, size=BUFFER_BYTES)
        server_end, client_end = Pipe()
        try:
            env = restore(self.decisions[0])
            _, header = prepare_into(memory.buf, env, tuple(env.legal_actions()))
            server = SharedEvaluatorServer(self.models, torch.device("cpu"), [server_end], [memory.name])
            with self.assertRaisesRegex(ValueError, "layout"):
                server.answer([(server_end, (env.current_decision_player(), 1, "campaign-zone-v0-other", header))])
            server.close()
        finally:
            server_end.close()
            client_end.close()
            memory.close()
            memory.unlink()

    def test_a_closed_pipe_raises_evaluator_closed(self):
        memory = shared_memory.SharedMemory(create=True, size=BUFFER_BYTES)
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
            evaluator = RemoteEvaluator(client_end, memory.name, "test")
            threading.Thread(target=read_then_close, args=(server_end,), daemon=True).start()
            self.assertIs(cause(evaluator), EOFError)
            evaluator.close()
            # A stopped server closes the pipes still open, so a thread waiting
            # on its request stops, and nothing more can be sent.
            server_end, client_end = Pipe()
            server = SharedEvaluatorServer(self.models, torch.device("cpu"), [server_end], [memory.name])
            evaluator = RemoteEvaluator(client_end, memory.name, "test")
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
