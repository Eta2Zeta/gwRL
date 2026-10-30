from __future__ import annotations

import copy
import hashlib
import json
import random
import unittest
from dataclasses import replace

from studies.shared.campaign_adapter import CampaignAdapter, ScheduledAction
from studies.shared.multiplayer_mcts import (
    PLAYERS, Bounds, Edge, Evaluation, MctsConfig, NoLegalActionError, Node, OpponentPolicy,
    UniformEvaluator, VectorMCTS, action_key, apply_fixed_opponent, score_actions,
)


class TreeEnv:
    """Small fully enumerated games; RNG is absent from observations/state keys."""
    def __init__(self, graph, node="root", *, reverse=False, seed=17):
        self.graph, self.node, self.reverse = graph, node, reverse
        self.definition = hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()
        self.flags = {}
        self.actual_random = random.Random(seed)
        self.search_random = None
        self.actual_draws = 0

    def current_decision_player(self):
        return self.graph[self.node].get("player")

    def decision_kind(self):
        node = self.graph[self.node]
        return "terminal" if "returns" in node else "chance" if "outcomes" in node else node.get("kind", "choose")

    def legal_actions(self):
        actions = list(self.graph[self.node].get("actions", {}))
        return list(reversed(actions)) if self.reverse else actions

    def apply_action(self, action):
        self.node = self.graph[self.node]["actions"][action]

    def resolve_chance(self):
        if self.decision_kind() != "chance":
            raise ValueError("Not a chance node")
        rng = self.search_random if self.search_random is not None else self.actual_random
        threshold = rng.random()
        if self.search_random is None:
            self.actual_draws += 1
        for probability, node in self.graph[self.node]["outcomes"]:
            threshold -= probability
            if threshold < 0:
                self.node = node
                return
        raise AssertionError("Incomplete chance distribution")

    def is_terminal(self):
        return "returns" in self.graph[self.node]

    def returns(self):
        return self.graph[self.node].get("returns", [0.0, 0.0, 0.0])

    def observation(self):
        return {"node": self.node, "owner": self.current_decision_player(), "kind": self.decision_kind(), "flags": self.flags.copy()}

    def planning_key(self):
        return json.dumps([self.definition, self.node, self.flags], sort_keys=True)

    def clone(self):
        result = copy.copy(self)
        result.flags = self.flags.copy()
        result.actual_random = copy.deepcopy(self.actual_random)
        result.search_random = copy.deepcopy(self.search_random)
        return result

    def clone_for_search(self, seed):
        result = self.clone()
        result.search_random = random.Random(seed)
        return result

    def serialize(self):
        return json.dumps({"node": self.node, "flags": self.flags, "actual_draws": self.actual_draws,
                           "actual_random": repr(self.actual_random.getstate()),
                           "search_random": repr(self.search_random.getstate()) if self.search_random else None}, sort_keys=True)


def terminal(*values):
    return {"returns": values}


def deterministic_game():
    return {
        "root": {"player": "axis", "actions": {"allied_response": "allies", "comintern_response": "comintern", "own_followup": "axis_again"}},
        "allies": {"player": "allies", "kind": "defender_casualty", "actions": {"axis_favored": "a", "allies_favored": "b"}},
        "comintern": {"player": "comintern", "actions": {"comintern_favored": "c", "axis_favored": "d"}},
        "axis_again": {"player": "axis", "actions": {"smaller": "e", "larger": "f"}},
        "a": terminal(8, 5, 0), "b": terminal(1, 9, 0),
        "c": terminal(3, 0, 4), "d": terminal(7, 8, 1),
        "e": terminal(2, 8, 8), "f": terminal(6, 1, 0),
    }


def stochastic_game():
    return {"root": {"player": "axis", "actions": {"safe": "safe", "gamble": "coin"}},
            "safe": terminal(4, 4, 0), "coin": {"outcomes": [(0.5, "high"), (0.5, "low")]},
            "high": terminal(10, 1, 0), "low": terminal(2, 3, 4)}


def stochastic_three_owner_game():
    return {"root": {"player": "axis", "actions": {"safe": "safe", "enter": "coin"}},
            "safe": terminal(3, 0, 0), "coin": {"outcomes": [(0.5, "allies"), (0.5, "comintern")]},
            "allies": {"player": "allies", "kind": "defender_reaction", "actions": {"allow": "allow", "defend": "defend"}},
            "comintern": {"player": "comintern", "actions": {"axis_favored": "axis_favored", "own_favored": "own_favored"}},
            "allow": terminal(8, 0, 0), "defend": terminal(2, 7, 0),
            "axis_favored": terminal(9, 0, 1), "own_favored": terminal(6, 0, 8)}


def fixed_opponent_game():
    return {"root": {"player": "axis", "actions": {"safe": "safe", "enter": "opponent"}},
            "safe": terminal(5, 0, 0), "opponent": {"player": "allies", "actions": {"donate": "donate", "selfish": "selfish"}},
            "donate": terminal(10, 0, 0), "selfish": terminal(0, 10, 0)}


def exact_oracle(env, *, policy=None, target=None):
    """Independent finite-tree enumeration; production MCTS never calls this."""
    if env.is_terminal():
        return tuple(env.returns()), {}
    if env.decision_kind() == "chance":
        values = [0.0] * 3
        for probability, child in env.graph[env.node]["outcomes"]:
            successor = env.clone()
            successor.node = child
            child_value, _ = exact_oracle(successor, policy=policy, target=target)
            for component in range(3):
                values[component] += probability * child_value[component]
        return tuple(values), {}
    actions = env.legal_actions()
    values = {}
    for action in actions:
        successor = env.clone()
        successor.apply_action(action)
        values[action] = exact_oracle(successor, policy=policy, target=target)[0]
    if policy is not None and env.current_decision_player() != target:
        weights = list(policy.distribution(env, actions))
        total = sum(weights)
        return tuple(sum(weights[i] * values[action][component] / total for i, action in enumerate(actions))
                     for component in range(3)), values
    component = PLAYERS.index(env.current_decision_player())
    best = min(actions, key=lambda action: (-values[action][component], action_key(action)))
    return values[best], values


class MultiplayerMctsTests(unittest.TestCase):
    def test_three_players_consecutive_turns_and_defender_reactions(self):
        env = TreeEnv(deterministic_game())
        exact, action_values = exact_oracle(env)
        self.assertEqual(exact, (6, 1, 0))
        self.assertEqual(action_values["allied_response"], (1, 9, 0))
        self.assertEqual(action_values["comintern_response"], (3, 0, 4))
        search = VectorMCTS(config=MctsConfig(simulations=3072, seed=43, record_trace=True))
        result = search.search(env)
        self.assertEqual(result.best_action(), "own_followup")
        self.assertAlmostEqual(result.values[0], exact[0], delta=0.35)
        actors = {choice.player for trace in result.simulations for choice in trace.selections}
        self.assertEqual(actors, set(PLAYERS))
        allied = next(node for node in search.nodes.values() if node.player == "allies")
        self.assertGreater(next(edge.visits for edge in allied.edges if edge.action == "allies_favored"),
                           next(edge.visits for edge in allied.edges if edge.action == "axis_favored"))
        own = next(node for node in search.nodes.values() if node.state_key == TreeEnv(env.graph, "axis_again").planning_key())
        self.assertGreater(next(edge.visits for edge in own.edges if edge.action == "larger"),
                           next(edge.visits for edge in own.edges if edge.action == "smaller"))

    def test_stochastic_action_has_multiple_outcomes_and_vector_expectation(self):
        env = TreeEnv(stochastic_game())
        expected, _ = exact_oracle(env)
        result = VectorMCTS(config=MctsConfig(simulations=4096, seed=7, record_trace=True)).search(env)
        self.assertEqual(result.best_action(), "gamble")
        gamble = next(edge for edge in result.root.edges if edge.action == "gamble")
        self.assertEqual(len(gamble.successors), 1)  # Explicit pending chance state.
        chance = next(iter(gamble.successors.values()))
        self.assertEqual(chance.kind, "chance")
        self.assertIsNone(chance.player)
        self.assertEqual(len(chance.chance_successors), 2)
        for component in range(3):
            self.assertAlmostEqual(gamble.values[component], expected[component], delta=0.25)
        self.assertGreater(len({after for trace in result.simulations for _, after in trace.chance_outcomes}), 1)

    def test_exact_oracle_regret_across_budgets_seeds_and_action_order(self):
        for budget, tolerance, value_tolerance, root_tolerance in ((64, 0.8, 1.6, 2.0), (256, 0.4, 0.85, 1.2), (1536, 0.15, 0.4, 0.5)):
            for seed in (11, 29, 101):
                for graph in (deterministic_game(), stochastic_game()):
                    env = TreeEnv(graph)
                    exact, actions = exact_oracle(env)
                    results = []
                    for reverse in (False, True):
                        result = VectorMCTS(config=MctsConfig(simulations=budget, seed=seed)).search(TreeEnv(graph, reverse=reverse))
                        chosen = result.best_action()
                        regret = exact[0] - actions[chosen][0]
                        self.assertLessEqual(regret, tolerance, (budget, seed, chosen, regret))
                        estimates = result.action_values[result.actions.index(chosen)]
                        self.assertLessEqual(max(abs(estimates[i] - actions[chosen][i]) for i in range(3)), value_tolerance)
                        self.assertLessEqual(max(abs(result.values[i] - exact[i]) for i in range(3)), root_tolerance)
                        results.append({action: (count, values) for action, count, values in
                                        zip(result.actions, result.visit_counts, result.action_values)})
                    self.assertEqual(results[0], results[1], "Action enumeration order changed sampled search")

    def test_chance_branches_route_to_the_actual_reaction_owners(self):
        env = TreeEnv(stochastic_three_owner_game())
        expected, _ = exact_oracle(env)
        result = VectorMCTS(config=MctsConfig(simulations=4096, seed=73, record_trace=True)).search(env)
        self.assertEqual(expected, (4, 3.5, 4))
        self.assertEqual(result.best_action(), "enter")
        enter = next(edge for edge in result.root.edges if edge.action == "enter")
        for component in range(3):
            self.assertAlmostEqual(enter.values[component], expected[component], delta=0.4)
        owners = {choice.player for trace in result.simulations for choice in trace.selections}
        self.assertEqual(owners, set(PLAYERS))

    def test_depth_cutoff_is_an_approximation_and_terminal_vector_is_exact(self):
        class ConstantEvaluator:
            version = "constant-vector-v1"
            def evaluate(self, env, actions):
                return Evaluation([1] * len(actions), (2, 3, 4))
        result = VectorMCTS(ConstantEvaluator(), MctsConfig(simulations=8, max_depth=1, record_trace=True)).search(TreeEnv(deterministic_game()))
        self.assertTrue(all(trace.leaf_source == "depth_limit" for trace in result.simulations))
        self.assertEqual(result.values, (2, 3, 4))
        terminal_result = VectorMCTS(config=MctsConfig(simulations=2)).search(TreeEnv(deterministic_game(), "f"))
        self.assertEqual(terminal_result.values, (6, 1, 0))
        self.assertEqual(terminal_result.actions, [])
        with self.assertRaises(ValueError):
            terminal_result.best_action()

    def test_search_rng_is_isolated_and_every_simulation_has_its_own_stream(self):
        env = TreeEnv(stochastic_game(), "coin", seed=998)
        actual_before = env.serialize()
        baseline = env.clone()
        result = VectorMCTS(config=MctsConfig(simulations=256, seed=91, record_trace=True)).search(env)
        self.assertEqual(env.serialize(), actual_before)
        self.assertEqual(len({trace.seed for trace in result.simulations}), 256)
        self.assertEqual(env.actual_draws, 0)
        env.resolve_chance()
        baseline.resolve_chance()
        self.assertEqual(env.serialize(), baseline.serialize())
        self.assertIsNone(env.current_decision_player())
        self.assertEqual(result.actions, [])

    def test_fixed_opponent_search_matches_the_explicit_actual_policy(self):
        policy = OpponentPolicy("donation-policy-v1", lambda env, actions: [0.8 if action == "donate" else 0.2 for action in actions])
        env = TreeEnv(fixed_opponent_game())
        expected, _ = exact_oracle(env, policy=policy, target="axis")
        fixed = VectorMCTS(config=MctsConfig(simulations=4096, seed=4, mode="fixed_opponents", target_player="axis", record_trace=True),
                           opponent_policy=policy).search(env)
        multiplayer = VectorMCTS(config=MctsConfig(simulations=2048, seed=4)).search(env)
        self.assertEqual(expected, (8, 2, 0))
        self.assertEqual(fixed.best_action(), "enter")
        self.assertEqual(multiplayer.best_action(), "safe")
        enter = next(edge for edge in fixed.root.edges if edge.action == "enter")
        self.assertAlmostEqual(enter.values[0], expected[0], delta=0.3)
        self.assertTrue(any(choice.mode == "opponent_policy" for trace in fixed.simulations for choice in trace.selections))
        rng = random.Random(512)
        actual = []
        for _ in range(2000):
            opponent = TreeEnv(env.graph, "opponent")
            apply_fixed_opponent(opponent, "axis", policy, rng)
            actual.append(opponent.returns()[0])
            self.assertEqual(opponent.actual_draws, 0)
        self.assertAlmostEqual(sum(actual) / len(actual), expected[0], delta=0.35)
        with self.assertRaises(ValueError):
            apply_fixed_opponent(TreeEnv(env.graph), "axis", policy, rng)

    def test_cache_versions_and_exact_observed_state_control_reuse(self):
        env = TreeEnv(deterministic_game())
        evaluator = UniformEvaluator()
        search = VectorMCTS(evaluator, MctsConfig(simulations=64, seed=5))
        first = search.search(env)
        again = search.search(env)
        self.assertFalse(first.reused_root)
        self.assertTrue(again.reused_root)
        env.apply_action(again.best_action())
        observed = search.search(env)
        self.assertTrue(observed.reused_root)
        self.assertEqual(observed.root.state_key, env.planning_key())
        env.flags["pending_reaction"] = True
        self.assertFalse(search.search(env).reused_root)
        evaluator.version = "uniform-zero-vector-v2"
        self.assertFalse(search.search(env).reused_root)
        search.config = replace(search.config, rules_version="rules-v2")
        self.assertFalse(search.search(env).reused_root)
        self.assertFalse(search.search(env, reuse_root=False).reused_root)
        policy = OpponentPolicy("opponent-v1", lambda env, actions: [1] * len(actions))
        fixed = VectorMCTS(config=MctsConfig(simulations=32, mode="fixed_opponents", target_player="axis"), opponent_policy=policy)
        fixed.search(TreeEnv(fixed_opponent_game()))
        fixed.opponent_policy = OpponentPolicy("opponent-v2", policy.distribution)
        self.assertFalse(fixed.search(TreeEnv(fixed_opponent_game())).reused_root)

    def test_optimistic_fpu_and_diagnostics_do_not_force_each_child_once(self):
        bounds = [Bounds() for _ in PLAYERS]
        bounds[0].update(7)
        node = Node("fixture", "axis", "choose", expanded=True,
                    edges=[Edge("visited", "visited", 0.5, 0.5, visits=1, value_sum=[7, 2, 1]),
                           Edge("unknown", "unknown", 0.5, 0.5)])
        scores = score_actions(node, MctsConfig(c_puct=0), bounds)
        self.assertEqual(scores[0].normalized_q, 0.5)
        self.assertEqual(scores[1].normalized_q, 1.0)
        self.assertIsNone(scores[1].values)
        bounds[0].update(0)
        node.edges[0].prior = node.edges[0].selection_prior = 1
        node.edges[1].prior = node.edges[1].selection_prior = 0
        scores = score_actions(node, MctsConfig(c_puct=2), bounds)
        self.assertGreater(scores[0].score, scores[1].score)
        self.assertGreater(scores[0].exploration, 0)
        self.assertEqual(scores[0].player_q, 7)

    def test_depth_limit_change_does_not_reuse_shallow_values(self):
        class PessimisticIntermediateEvaluator:
            version = "pessimistic-intermediate-v1"

            def evaluate(self, env, actions):
                values = (-100, 0, 0) if env.node == "intermediate" else (0, 0, 0)
                return Evaluation([1] * len(actions), values)

        graph = {
            "root": {"player": "axis", "actions": {"short": "short", "long": "intermediate"}},
            "intermediate": {"player": "axis", "actions": {"finish": "long"}},
            "short": terminal(1, 0, 0),
            "long": terminal(10, 0, 0),
        }
        env = TreeEnv(graph)
        evaluator = PessimisticIntermediateEvaluator()
        search = VectorMCTS(evaluator, MctsConfig(simulations=512, max_depth=1, seed=1))
        shallow = search.search(env)
        self.assertEqual(shallow.best_action(), "short")
        search.config = replace(search.config, max_depth=8, simulations=128)
        deeper = search.search(env)
        fresh = VectorMCTS(evaluator, search.config).search(env)
        self.assertFalse(deeper.reused_root)
        self.assertNotEqual(shallow.cache_identity, deeper.cache_identity)
        self.assertEqual(sum(deeper.visit_counts), 128)
        self.assertEqual(deeper.best_action(), fresh.best_action())
        self.assertEqual(deeper.best_action(), "long")
        long_edge = next(edge for edge in deeper.root.edges if edge.action == "long")
        self.assertGreater(long_edge.values[0], 8)

    def test_cycle_cutoff_preserves_one_root_visit_per_simulation(self):
        graph = {"root": {"player": "axis", "actions": {"loop": "root", "finish": "done"}},
                 "done": terminal(0, 0, 0)}
        policies = []
        for depth in (2, 8, 32):
            result = VectorMCTS(config=MctsConfig(simulations=16, max_depth=depth, seed=13,
                                                  record_trace=True)).search(TreeEnv(graph))
            self.assertEqual(result.root.visits, 16)
            self.assertEqual(sum(result.visit_counts), 16)
            self.assertTrue(any(trace.leaf_source == "cycle_cutoff" for trace in result.simulations))
            self.assertTrue(all(len({choice.state_key for choice in trace.selections}) == len(trace.selections)
                                for trace in result.simulations))
            policies.append(dict(zip(result.actions, result.visit_counts)))
        self.assertTrue(all(policy == policies[0] for policy in policies))

    def test_cycle_cutoff_bootstraps_vector_without_a_terminal_or_reward(self):
        class ConstantEvaluator:
            version = "cycle-vector-v1"

            def evaluate(self, env, actions):
                return Evaluation([1] * len(actions), (7, -3, 2))

        graph = {"root": {"player": "axis", "actions": {"loop": "root"}}}
        for depth in (1, 2, 32):
            env = TreeEnv(graph)
            before = env.serialize()
            result = VectorMCTS(ConstantEvaluator(), MctsConfig(simulations=16, max_depth=depth, record_trace=True,
                                                                search_forced_root=True)).search(env)
            self.assertFalse(env.is_terminal())
            self.assertEqual(env.serialize(), before)
            self.assertEqual(result.root.visits, 16)
            self.assertEqual(result.visit_counts, [16])
            self.assertEqual(result.values, (7, -3, 2))
            self.assertEqual(result.action_values, [(7, -3, 2)])
            self.assertTrue(all(trace.leaf_source == "cycle_cutoff" for trace in result.simulations))

    def test_cycle_cutoff_through_other_players_and_chance_backs_up_unique_path(self):
        class ConstantEvaluator:
            version = "cycle-vector-v1"

            def evaluate(self, env, actions):
                return Evaluation([1] * len(actions), (2, 3, 4))

        graph = {"root": {"player": "axis", "actions": {"enter": "allies"}},
                 "allies": {"player": "allies", "kind": "defender_reaction", "actions": {"roll": "chance"}},
                 "chance": {"outcomes": [(1.0, "comintern")]},
                 "comintern": {"player": "comintern", "actions": {"return": "root"}}}
        env = TreeEnv(graph)
        before = env.serialize()
        search = VectorMCTS(ConstantEvaluator(), MctsConfig(simulations=16, max_depth=32, record_trace=True,
                                                            search_forced_root=True))
        result = search.search(env)
        self.assertEqual(result.root.visits, 16)
        self.assertEqual(result.visit_counts, [16])
        self.assertEqual(result.values, (2, 3, 4))
        self.assertEqual(env.serialize(), before)
        self.assertEqual({choice.player for trace in result.simulations for choice in trace.selections}, set(PLAYERS))
        self.assertTrue(any(trace.leaf_source == "cycle_cutoff" for trace in result.simulations))
        for node in search.nodes.values():
            self.assertLessEqual(node.visits, 16)
            self.assertTrue(all(edge.visits <= node.visits for edge in node.edges))
        self.assertTrue(all(len(trace.chance_outcomes) <= 1 for trace in result.simulations))

    def test_chance_self_cycle_uses_evaluator_and_keeps_actual_rng_untouched(self):
        class ChanceEvaluator:
            version = "chance-cycle-vector-v1"

            def evaluate(self, env, actions):
                self.assertion = (env.decision_kind(), list(actions))
                return Evaluation([], (6, 7, 8))

        env = TreeEnv({"root": {"outcomes": [(1.0, "root")]}})
        before = env.serialize()
        evaluator = ChanceEvaluator()
        result = VectorMCTS(evaluator, MctsConfig(simulations=16, max_depth=32,
                                                  record_trace=True)).search(env)
        self.assertEqual(env.serialize(), before)
        self.assertEqual(result.root.visits, 16)
        self.assertEqual(result.values, (6, 7, 8))
        self.assertEqual(evaluator.assertion, ("chance", []))
        self.assertTrue(all(trace.leaf_source == "cycle_cutoff" and len(trace.chance_outcomes) == 1
                            for trace in result.simulations))

    def test_root_noise_is_order_stable_and_does_not_replace_base_priors(self):
        results = []
        for reverse in (False, True):
            result = VectorMCTS(config=MctsConfig(simulations=128, seed=71)).search(TreeEnv(stochastic_game(), reverse=reverse), add_root_noise=True)
            self.assertAlmostEqual(sum(edge.selection_prior for edge in result.root.edges), 1)
            self.assertEqual(result.priors, [0.5, 0.5])
            results.append({edge.key: (edge.selection_prior, edge.visits) for edge in result.root.edges})
        self.assertEqual(results[0], results[1])

    def test_root_noise_does_not_leak_into_reused_internal_nodes_or_cycles(self):
        graph = deterministic_game()
        search = VectorMCTS(config=MctsConfig(simulations=96, seed=71, record_trace=True))
        noised = search.search(TreeEnv(graph, "axis_again"), add_root_noise=True)
        self.assertTrue(any(edge.selection_prior != edge.prior for edge in noised.root.edges))
        continued = search.search(TreeEnv(graph), add_root_noise=False)
        self.assertTrue(all(edge.selection_prior == edge.prior for node in search.nodes.values() for edge in node.edges))
        internal = [selection for trace in continued.simulations for selection in trace.selections[1:]
                    if selection.state_key == noised.root.state_key]
        self.assertTrue(internal)
        self.assertTrue(all(score.selection_prior == score.prior for selection in internal for score in selection.scores))
        graph = {"root": {"player": "axis", "actions": {"loop": "root", "finish": "done"}}, "done": terminal(1, 0, 0)}
        cycled = VectorMCTS(config=MctsConfig(simulations=96, max_depth=8, seed=13, record_trace=True)).search(TreeEnv(graph), add_root_noise=True)
        internal = [selection for trace in cycled.simulations for selection in trace.selections[1:] if selection.state_key == cycled.root.state_key]
        self.assertFalse(internal, "A repeated planning state must cut off before another selection")
        self.assertTrue(any(trace.leaf_source == "cycle_cutoff" for trace in cycled.simulations))
        self.assertEqual(sum(cycled.visit_counts), 96)

    def test_dead_end_keeps_the_imagined_position(self):
        graph = {"root": {"player": "axis", "actions": {"stuck": "dead"}},
                 "dead": {"player": "allies", "actions": {}}}
        with self.assertRaises(NoLegalActionError) as raised:
            VectorMCTS(config=MctsConfig(simulations=4, seed=3, search_forced_root=True)).search(TreeEnv(graph))
        self.assertIsInstance(raised.exception, ValueError)
        self.assertEqual(json.loads(raised.exception.state)["node"], "dead")

    def test_invalid_versions_values_and_opponent_modes_are_rejected(self):
        for kwargs in ({"simulations": 0}, {"max_depth": 0}, {"c_puct": float("nan")}, {"rules_version": ""},
                       {"mode": "fixed_opponents"}, {"root_dirichlet_alpha": 0}):
            with self.assertRaises(ValueError):
                MctsConfig(**kwargs)
        with self.assertRaises(ValueError):
            VectorMCTS(config=MctsConfig(mode="fixed_opponents", target_player="axis"))
        class InvalidEvaluator:
            version = "invalid-v1"
            def evaluate(self, env, actions):
                return Evaluation([1] * len(actions), [0, 0])
        with self.assertRaises(ValueError):
            VectorMCTS(InvalidEvaluator()).search(TreeEnv(stochastic_game()))
        class PolicyOwnedChance(TreeEnv):
            def current_decision_player(self):
                return "axis"
        with self.assertRaisesRegex(ValueError, "policy decision owner"):
            VectorMCTS().search(PolicyOwnedChance(stochastic_game(), "coin"))


class ForcedRootTests(unittest.TestCase):
    """A root with one legal action is played without evaluating or simulating it."""
    GAME = {"root": {"player": "axis", "actions": {"only": "choice"}},
            "choice": {"player": "allies", "actions": {"left": "coin", "right": "forced"}},
            "coin": {"outcomes": [(0.5, "forced"), (0.5, "end")]},
            "forced": {"player": "comintern", "actions": {"last": "end"}},
            "end": {"returns": [1.0, 0.0, -1.0]}}

    class Evaluator:
        version = "counting-v1"

        def __init__(self):
            self.calls = 0

        def evaluate(self, env, actions):
            self.calls += 1
            return Evaluation([1.0] * len(actions), (1.0, 2.0, 3.0))

    def test_one_action_root_costs_no_evaluation_or_simulation(self):
        class NoCopies(TreeEnv):
            def clone_for_search(self, seed):
                raise AssertionError("A forced move needs no simulation")

        env, evaluator = NoCopies(self.GAME), self.Evaluator()
        before = env.serialize()
        result = VectorMCTS(evaluator, MctsConfig(simulations=16, seed=3)).search(env, add_root_noise=True)
        self.assertEqual(evaluator.calls, 0)
        self.assertEqual((result.actions, result.visit_counts, result.policy, result.priors),
                         (["only"], [0], [1.0], [1.0]))
        # No search ran, so no value is claimed; zero would look like an estimate.
        self.assertIsNone(result.values)
        self.assertEqual((result.action_values, result.simulations), ([None], []))
        self.assertEqual(result.best_action(), "only")
        self.assertEqual(env.serialize(), before)

    def test_a_search_can_still_be_asked_for(self):
        evaluator = self.Evaluator()
        result = VectorMCTS(evaluator, MctsConfig(simulations=16, seed=3, search_forced_root=True)).search(TreeEnv(self.GAME))
        self.assertGreater(evaluator.calls, 0)
        self.assertEqual((result.visit_counts, result.policy, result.priors), ([16], [1.0], [1.0]))
        self.assertIsNotNone(result.values)

    def test_skipping_changes_no_move_or_random_stream_of_a_game(self):
        def play(seed, search_forced_root):
            env, search_rng, policy_rng = TreeEnv(self.GAME, seed=seed), random.Random(seed), random.Random(seed + 1)
            moves = []
            while not env.is_terminal():
                if env.decision_kind() == "chance":
                    env.resolve_chance()
                    continue
                config = MctsConfig(simulations=32, seed=search_rng.getrandbits(64), search_forced_root=search_forced_root)
                result = VectorMCTS(self.Evaluator(), config).search(env, add_root_noise=True)
                moves.append(policy_rng.choices(result.actions, weights=result.policy, k=1)[0])
                env.apply_action(moves[-1])
            return moves, env.serialize(), search_rng.getstate(), policy_rng.getstate()

        games = [play(seed, False) for seed in range(40)]
        self.assertEqual(games, [play(seed, True) for seed in range(40)])
        self.assertEqual({len(game[0]) for game in games}, {2, 3})

    def test_roots_with_a_choice_dice_or_an_ending_search_as_before(self):
        evaluator = self.Evaluator()
        choice = VectorMCTS(evaluator, MctsConfig(simulations=16, seed=3)).search(TreeEnv(self.GAME, "choice"))
        self.assertEqual(sum(choice.visit_counts), 16)
        self.assertIsNotNone(choice.values)
        dice = VectorMCTS(evaluator, MctsConfig(simulations=16, seed=3)).search(TreeEnv(self.GAME, "coin"))
        self.assertEqual(dice.actions, [])
        self.assertIsNotNone(dice.values)
        ending = VectorMCTS(evaluator, MctsConfig(simulations=2)).search(TreeEnv(self.GAME, "end"))
        self.assertEqual((ending.actions, ending.values), ([], (1.0, 0.0, -1.0)))

    def test_a_forced_root_passes_the_same_checks_as_any_other(self):
        ownerless = {"root": {"actions": {"only": "end"}}, "end": {"returns": [0.0, 0.0, 0.0]}}
        with self.assertRaisesRegex(ValueError, "entitled player"):
            VectorMCTS().search(TreeEnv(ownerless))
        dead = {"root": {"player": "axis", "actions": {}}}
        with self.assertRaises(NoLegalActionError):
            VectorMCTS().search(TreeEnv(dead))

    def test_a_dead_end_behind_a_forced_move_is_found_at_the_next_root(self):
        graph = {"root": {"player": "axis", "actions": {"stuck": "dead"}},
                 "dead": {"player": "allies", "actions": {}}}
        env = TreeEnv(graph)
        env.apply_action(VectorMCTS().search(env).best_action())
        with self.assertRaises(NoLegalActionError) as raised:
            VectorMCTS().search(env)
        self.assertEqual(json.loads(raised.exception.state)["node"], "dead")

    def test_a_reused_tree_keeps_its_statistics_across_a_forced_root(self):
        search = VectorMCTS(self.Evaluator(), MctsConfig(simulations=32, seed=3))
        first = search.search(TreeEnv(self.GAME, "choice"))
        forced = search.search(TreeEnv(self.GAME, "forced"))
        self.assertEqual((forced.visit_counts, forced.values), ([0], None))
        self.assertTrue(forced.reused_root)
        again = search.search(TreeEnv(self.GAME, "choice"))
        self.assertEqual(sum(again.visit_counts), sum(first.visit_counts) + 32)

    def test_fixed_opponent_search_does_not_ask_the_opponent_policy(self):
        def refuse(env, actions):
            raise AssertionError("A forced move needs no opponent model")

        policy = OpponentPolicy("refuses-v1", refuse)
        config = MctsConfig(simulations=8, mode="fixed_opponents", target_player="axis")
        result = VectorMCTS(self.Evaluator(), config, opponent_policy=policy).search(TreeEnv(self.GAME))
        self.assertEqual(result.best_action(), "only")


class InterruptRawEnv:
    def __init__(self):
        self.state, self.declared = "ready", []

    def current_decision_player(self):
        return None if self.is_terminal() else "axis"

    def decision_kind(self):
        return "terminal" if self.is_terminal() else "politics_declaration_priority" if self.state == "priority" else "production"

    def legal_actions(self):
        if self.is_terminal():
            return []
        return [{"id": "priority" if self.state == "priority" else "finish", "player": "axis", "kind": "choice"}]

    def legal_interrupts(self):
        return [{"id": f"declare-{player}", "player": player, "kind": "declare"} for player in ("allies", "comintern")] if self.state == "ready" else []

    def apply_action(self, action):
        self.state = "after_priority" if self.state == "priority" else "terminal"

    def apply_interrupt(self, action):
        self.declared.append(action["player"])
        self.state = "priority"

    def is_terminal(self):
        return self.state == "terminal"

    def returns(self):
        return (1, 2, 3) if self.is_terminal() else (0, 0, 0)

    def observation(self):
        return {"state": {"phase": self.state, "declared": self.declared.copy()}, "legal_interrupts": self.legal_interrupts()}

    def context(self):
        return {"players": list(PLAYERS)}

    def clone(self):
        return copy.deepcopy(self)

    def clone_for_search(self, seed):
        return self.clone()

    def planning_key(self):
        return self.serialize()

    def serialize(self):
        return json.dumps({"state": self.state, "declared": self.declared}, sort_keys=True)

    def restore(self, serialized):
        value = json.loads(serialized)
        self.state, self.declared = value["state"], value["declared"]


class CampaignInterruptAdapterTests(unittest.TestCase):
    def test_explicit_passes_owner_routing_clone_and_checkpoint(self):
        env = CampaignAdapter(InterruptRawEnv())
        original_key = env.planning_key()
        self.assertEqual(env.current_decision_player(), "allies")
        self.assertEqual(env.decision_kind(), "declaration_offer")
        env.apply_action(next(action for action in env.legal_actions() if action.kind == "pass_interrupt"))
        self.assertEqual(env.current_decision_player(), "comintern")
        self.assertNotEqual(original_key, env.planning_key())
        checkpoint = env.serialize()
        clone = env.clone_for_search(9)
        self.assertEqual(env.planning_key(), clone.planning_key())
        clone.apply_action(next(action for action in clone.legal_actions() if action.kind == "pass_interrupt"))
        self.assertEqual(clone.current_decision_player(), "axis")
        self.assertEqual(env.current_decision_player(), "comintern")
        clone.restore(checkpoint)
        self.assertEqual(clone.serialize(), checkpoint)
        self.assertEqual(clone.observation()["interrupt_scheduler"]["passed"], ["allies"])
        self.assertNotIn("anchor", clone.observation()["interrupt_scheduler"])

    def test_real_interrupt_retains_engine_priority_and_rejects_forgery(self):
        env = CampaignAdapter(InterruptRawEnv())
        interrupt = next(action for action in env.legal_actions() if action.kind == "interrupt")
        with self.assertRaises(ValueError):
            env.apply_action(ScheduledAction(interrupt.id, interrupt.kind, "axis"))
        env.apply_action(interrupt)
        self.assertEqual(env.raw.declared, ["allies"])
        self.assertEqual(env.current_decision_player(), "axis")
        self.assertEqual(env.decision_kind(), "politics_declaration_priority")
        self.assertTrue(all(action.kind == "play" for action in env.legal_actions()))
        env.apply_action(env.legal_actions()[0])
        self.assertEqual(env.decision_kind(), "production")
        self.assertEqual(env.observation()["interrupt_scheduler"]["passed"], [])

    def test_search_cannot_hide_raw_interrupts_and_schedules_reaction_owners(self):
        with self.assertRaisesRegex(ValueError, "CampaignAdapter"):
            VectorMCTS(config=MctsConfig(simulations=8)).search(InterruptRawEnv())
        env = CampaignAdapter(InterruptRawEnv())
        before = env.serialize()
        result = VectorMCTS(config=MctsConfig(simulations=96, record_trace=True)).search(env)
        self.assertEqual(env.serialize(), before)
        self.assertEqual(result.root.player, "allies")
        owners = {selection.player for trace in result.simulations for selection in trace.selections}
        self.assertEqual(owners, set(PLAYERS))


if __name__ == "__main__":
    unittest.main()
