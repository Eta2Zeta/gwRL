"""The shared evaluator answers as NeuralEvaluator does, through real pipes and shared memory."""
from __future__ import annotations

from dataclasses import asdict
from multiprocessing import Pipe, shared_memory
import random
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np
import torch

import gwrl_cpp

from studies.campaign.curriculum import make_env
from studies.campaign.features import make_zone_input
from studies.campaign.neural import CampaignModelConfig, CampaignPolicyValueNet, NeuralEvaluator
from studies.campaign.shared_evaluator import (BUFFER_BYTES, REQUEST, ZONE_FIELDS, EvaluatorClosed, RemoteEvaluator,
                                               SharedEvaluatorServer, evaluate_prepared, read_request, reply_bytes)
from studies.shared.multiplayer_mcts import PLAYERS, MctsConfig, UniformEvaluator, VectorMCTS
from tools.benchmark_campaign_devices import Config, _shared_game_process
from tests.machine import CPU_BUDGET

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


def exchange(zone, actor, size=BUFFER_BYTES):
    """One request as a game thread's native client sends it: the bytes the server
    receives, its arrays as the server reads them, and what the client returned."""
    server_end, client_end = Pipe()
    memory = shared_memory.SharedMemory(create=True, size=BUFFER_BYTES)
    try:
        client = gwrl_cpp.InferenceClient(client_end.fileno(), memory.name, size)
        returned = []
        asking = threading.Thread(target=lambda: returned.append(client.evaluate(zone, actor)), daemon=True)
        asking.start()
        message = server_end.recv_bytes()
        _, count, layout, arrays = read_request(memory.buf, message)
        copies = {name: array.copy() for name, array in arrays.items()}
        del arrays  # Views into the buffer, which closes below.
        server_end.send_bytes(reply_bytes([1.0] * count, (1.0, 2.0, 3.0), None))
        asking.join(timeout=60)
        client.close()
        return message, layout, copies, returned[0]
    finally:
        memory.close()
        memory.unlink()
        server_end.close()
        client_end.close()


def prepared(env, actions):
    """A decision's arrays as a game thread's client writes them and the server reads them."""
    actor = env.current_decision_player()
    _, layout, arrays, _ = exchange(make_zone_input(env, actions), actor)
    return layout, arrays


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
            # The first decision with over 20 choices at or after every 150th step,
            # so searches meet large menus whichever path random play takes.
            if step >= next_search and len(actions) > 20:
                VectorMCTS(Checking(), MctsConfig(simulations=8, max_depth=8, seed=step)).search(env)
                searches, next_search = searches + 1, next_search + 150
            env.apply_action(rng.choice(actions))
        self.assertGreater(searches, 2)
        self.assertGreater(max(sizes), 20)

    def test_the_request_names_each_field_and_a_short_buffer_is_refused(self):
        env = make_env(SEED, calendar_rounds=2)
        actions = tuple(env.legal_actions())
        zone = make_zone_input(env, actions)
        arrays = zone.arrays()
        message, layout, read, (priors, values) = exchange(zone, env.current_decision_player(), size=zone.nbytes)
        kind, actor, layout_length, count, *lengths = REQUEST.unpack_from(message)
        self.assertEqual((kind, actor, count), (1, PLAYERS.index(env.current_decision_player()), len(actions)))
        self.assertEqual(lengths, [len(arrays[name]) for name in ZONE_FIELDS])
        self.assertEqual((layout, layout_length, len(message)), (zone.version, len(zone.version), REQUEST.size + layout_length))
        self.assertEqual(sum(lengths) * 4, zone.nbytes)
        self.assertEqual((priors, values), ([1.0] * len(actions), (1.0, 2.0, 3.0)))
        self.assertSameArrays(read, arrays)
        server_end, client_end = Pipe()
        memory = shared_memory.SharedMemory(create=True, size=BUFFER_BYTES)
        try:
            client = gwrl_cpp.InferenceClient(client_end.fileno(), memory.name, zone.nbytes - 1)
            with self.assertRaisesRegex(ValueError, "does not fit"):
                client.evaluate(zone, env.current_decision_player())
            self.assertFalse(server_end.poll(0.1))  # Nothing was sent.
            client.close()
        finally:
            memory.close()
            memory.unlink()
            server_end.close()
            client_end.close()


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
        # Three decisions take one position each in a pass; the chance cutoff one per network.
        self.assertServesFourRequests(self.models, self.reference, positions=6)

    def test_one_network_for_all_three_alliances_is_one_network_in_a_pass(self):
        one = self.models[PLAYERS[1]]
        models = {player: one for player in PLAYERS}
        # The chance cutoff, too, takes one position: the one network rates it once.
        server = self.assertServesFourRequests(models, NeuralEvaluator(models, version="test"), positions=4)
        self.assertEqual(len(server.stack.models), 1)

    def test_a_compiled_forward_pass_answers_as_written(self):
        one = self.models[PLAYERS[2]]
        models = {player: one for player in PLAYERS}
        server = self.assertServesFourRequests(models, NeuralEvaluator(models, version="test"), positions=4,
                                               compiled_forward=True)
        self.assertTrue(server.stack.compiled)
        # While a network update trains beside the games, the layers as written answer.
        server.answer_as_written(True)
        written = server.stack
        self.assertFalse(written.compiled)
        server.answer_as_written(True)
        self.assertIs(server.stack, written)  # Asked again: the same stack.
        server.answer_as_written(False)
        self.assertTrue(server.stack.compiled)

    def assertServesFourRequests(self, models, reference, *, positions, compiled_forward=False):
        memories = [shared_memory.SharedMemory(create=True, size=BUFFER_BYTES) for _ in range(2)]
        pipes = [Pipe() for _ in memories]
        try:
            server = SharedEvaluatorServer(models, torch.device("cpu"), [parent for parent, _ in pipes],
                                           [memory.name for memory in memories], compiled_forward=compiled_forward)
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
                self.assertMatches(evaluation.priors, evaluation.values, reference.evaluate_batch([(env, menu)])[0])
            stats = server.stats
            self.assertEqual(stats.requests, 4)
            self.assertEqual(sum(size * count for size, count in stats.requests_per_round.items()), 4)
            self.assertEqual(sum(size * count for size, count in stats.positions_per_pass.items()), positions)
            self.assertEqual(stats.passes, stats.rounds)
            self.assertEqual(stats.passes, sum(stats.positions_per_pass.values()))
            server.close()
            return server
        finally:
            for memory in memories:
                memory.close()
                memory.unlink()

    def test_a_request_of_another_layout_is_refused(self):
        memory = shared_memory.SharedMemory(create=True, size=BUFFER_BYTES)
        server_end, client_end = Pipe()
        try:
            env = restore(self.decisions[0])
            arrays = make_zone_input(env, tuple(env.legal_actions())).arrays()
            other = b"campaign-zone-v0-other"
            message = REQUEST.pack(1, PLAYERS.index(env.current_decision_player()), len(other),
                                   len(arrays["action_source"]), *(len(arrays[name]) for name in ZONE_FIELDS)) + other
            server = SharedEvaluatorServer(self.models, torch.device("cpu"), [server_end], [memory.name])
            request = read_request(memory.buf, message)
            with self.assertRaisesRegex(ValueError, "layout"):
                server.answer([(server_end, request)])
            del request  # Its arrays are views into the buffer, which closes below.
            server.close()
        finally:
            server_end.close()
            client_end.close()
            memory.close()
            memory.unlink()

    def test_a_reply_to_a_game_process_that_ended_is_dropped(self):
        # A game process that dies after sending a request leaves a pipe that
        # cannot take the reply: the server stops serving it and answers the rest.
        memory = shared_memory.SharedMemory(create=True, size=BUFFER_BYTES)
        server_end, client_end = Pipe()
        try:
            env = restore(self.decisions[0])
            layout, arrays = prepared(env, tuple(env.legal_actions()))
            server = SharedEvaluatorServer(self.models, torch.device("cpu"), [server_end], [memory.name])
            client_end.close()  # The game process has gone.
            server.answer([(server_end, (env.current_decision_player(), len(arrays["action_source"]), layout, arrays))])
            self.assertEqual(server.connections, [])
            self.assertTrue(server_end.closed)
            self.assertEqual(server.stats.requests, 1)
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
        def closed(evaluator):
            try:
                evaluator.evaluate(env, menu)
            except EvaluatorClosed:
                return True
            return False
        def read_then_close(connection):
            connection.recv_bytes()
            connection.close()
        try:
            # A request read but never answered: reading the reply meets the end of the pipe.
            server_end, client_end = Pipe()
            evaluator = RemoteEvaluator(client_end, memory.name, "test")
            threading.Thread(target=read_then_close, args=(server_end,), daemon=True).start()
            self.assertTrue(closed(evaluator))
            evaluator.close()
            # A stopped server closes the pipes still open, so a thread waiting
            # on its request stops, and nothing more can be sent.
            server_end, client_end = Pipe()
            server = SharedEvaluatorServer(self.models, torch.device("cpu"), [server_end], [memory.name])
            evaluator = RemoteEvaluator(client_end, memory.name, "test")
            outcomes = []
            waiting = threading.Thread(target=lambda: outcomes.append(closed(evaluator)), daemon=True)
            waiting.start()
            self.assertTrue(server_end.poll(120), "The request never arrived")
            server.serve(lambda: False)
            waiting.join(timeout=30)
            self.assertTrue(server_end.closed)
            self.assertEqual(outcomes, [True])
            self.assertTrue(closed(evaluator))  # Sending to the closed pipe fails too.
            self.assertEqual((evaluator.stats.requests, server.stats.requests), (0, 0))
            evaluator.close()
            server.close()
        finally:
            memory.close()
            memory.unlink()


class SharedGameSlotTests(unittest.TestCase):
    def test_an_unexpected_exception_fails_only_its_game(self):
        config = Config(mode="selfplay", search_evaluation="per_search", threads=1, devices=("mps",), processes=2,
                        games_per_process=2, seeds=(1, 2, 3, 4), cpu_budget=CPU_BUDGET)
        memory = shared_memory.SharedMemory(create=True, size=1 << 20)
        parent, child = Pipe()
        tasks, task_writer = Pipe(duplex=False)
        result_reader, results = Pipe(duplex=False)
        for number, seed in enumerate((1, 2)):
            task_writer.send((number, seed))
        task_writer.close()  # The task pipe ends after the two games.
        def play(config, seed, evaluator, deadline_epoch):
            if seed == 1:
                raise KeyError("boom")
            return {"seed": seed, "terminal": True, "failure": None}
        try:
            with patch("tools.benchmark_campaign_devices.play_shared_game", side_effect=play):
                _shared_game_process(asdict(config), [5], [child], [memory.name], tasks, results, time.time() + 60,
                                     "test")
            (first, failed), (second, played) = result_reader.recv(), result_reader.recv()
            self.assertFalse(result_reader.poll())
        finally:
            for connection in (parent, tasks, results, result_reader):
                connection.close()
            memory.close()
            memory.unlink()
        self.assertEqual((first, second), (0, 1))  # Each record comes back with its task's number.
        self.assertEqual((failed["seed"], failed["terminal"], failed["stop_reason"], failed["slot"]),
                         (1, False, "game_exception", 5))
        self.assertEqual(failed["failure"]["error"], "KeyError: 'boom'")
        self.assertIn('raise KeyError("boom")', failed["failure"]["traceback"])
        self.assertLessEqual(failed["started_at_epoch"], failed["ended_at_epoch"])
        self.assertEqual((failed["evaluations"], failed["timing_seconds"]), (0, {}))
        self.assertEqual((played["seed"], played["slot"]), (2, 5))  # The slot played on.


class SharedModeConfigTests(unittest.TestCase):
    def test_several_games_per_process_need_process_parallel_mps_self_play(self):
        common = dict(mode="selfplay", search_evaluation="per_search", threads=1, seeds=(1, 2, 3, 4),
                      cpu_budget=CPU_BUDGET)
        Config(**common, devices=("mps",), processes=2, games_per_process=2)
        for bad in (dict(devices=("mps",), processes=1), dict(devices=("cpu",), processes=2),
                    dict(devices=("cpu", "mps"), processes=2)):
            with self.subTest(**bad), self.assertRaises(ValueError):
                Config(**{**common, **bad}, games_per_process=2)
        with self.assertRaises(ValueError):
            Config(**common, devices=("mps",), processes=2, games_per_process=0)

    def test_shared_self_play_needs_a_game_for_every_slot(self):
        common = dict(mode="selfplay", search_evaluation="per_search", threads=1, devices=("mps",), processes=2,
                      games_per_process=2, cpu_budget=CPU_BUDGET)
        Config(**common, seeds=(1, 2, 3, 4))
        with self.assertRaisesRegex(ValueError, "every game slot"):
            Config(**common, seeds=(1, 2, 3))

    def test_paired_runs_need_one_process_for_trace_comparison(self):
        # Three games, so that one process searching each on its own core fits a 7-core budget.
        common = dict(mode="selfplay", search_evaluation="per_search", threads=1, seeds=(1, 2, 3),
                      cpu_budget=CPU_BUDGET)
        Config(**common, devices=("cpu", "mps"))
        for devices in (("cpu",), ("mps",)):
            Config(**common, devices=devices, processes=2)
        with self.assertRaisesRegex(ValueError, "per-game traces"):
            Config(**common, devices=("cpu", "mps"), processes=2)


if __name__ == "__main__":
    unittest.main()
