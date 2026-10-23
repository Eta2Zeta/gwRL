"""Vector-valued PUCT with explicit stochastic successors.

The three components always mean Axis, Allies, Comintern. Decision owners choose
their own component; chance samples the rules environment and never becomes a
policy decision. This is finite-budget Max-N search, not an equilibrium solver.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Sequence

PLAYERS = ("axis", "allies", "comintern")
Vector = tuple[float, float, float]
ZERO: Vector = (0.0, 0.0, 0.0)


class SearchEnv(Protocol):
    def current_decision_player(self) -> str | None: ...
    def decision_kind(self) -> str: ...
    def legal_actions(self) -> Sequence[Any]: ...
    def apply_action(self, action: Any) -> None: ...
    def resolve_chance(self) -> None: ...
    def is_terminal(self) -> bool: ...
    def returns(self) -> Sequence[float]: ...
    def observation(self) -> Any: ...
    def clone_for_search(self, seed: int) -> SearchEnv: ...
    def planning_key(self) -> str: ...


def action_key(action: Any) -> str:
    """Stable legal-action identity, independent of list position."""
    if isinstance(action, dict) and "id" in action:
        return str(action["id"])
    if hasattr(action, "id"):
        return str(action.id)
    if hasattr(action, "describe"):
        return str(action.describe())
    return json.dumps(action, sort_keys=True, separators=(",", ":"), allow_nan=False)


def vector(values: Sequence[float]) -> Vector:
    result = tuple(float(value) for value in values)
    if len(result) != 3 or not all(math.isfinite(value) for value in result):
        raise ValueError("Value must have three finite Axis/Allies/Comintern components")
    return result  # type: ignore[return-value]


def probabilities(weights: Sequence[float], size: int) -> list[float]:
    values = [float(weight) for weight in weights]
    if len(values) != size or any(not math.isfinite(p) or p < 0 for p in values):
        raise ValueError("Policy must provide one finite nonnegative weight per legal action")
    total = sum(values)
    if size and (not math.isfinite(total) or total <= 0):
        raise ValueError("Policy must have positive finite total weight")
    return [p / total for p in values] if size else []


@dataclass(frozen=True, slots=True)
class Evaluation:
    priors: Sequence[float]
    values: Sequence[float]


class Evaluator(Protocol):
    version: str
    def evaluate(self, env: SearchEnv, actions: Sequence[Any]) -> Evaluation: ...


class UniformEvaluator:
    """Untrained baseline. Complete observations remain available to evaluators."""
    version = "uniform-zero-vector-v1"

    def evaluate(self, env: SearchEnv, actions: Sequence[Any]) -> Evaluation:
        return Evaluation([1.0] * len(actions), ZERO)


@dataclass(frozen=True, slots=True)
class OpponentPolicy:
    """The same explicit policy object is usable in search and actual play."""
    version: str
    distribution: Callable[[SearchEnv, Sequence[Any]], Sequence[float]]

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("Opponent policy needs a nonempty version")

    def sample(self, env: SearchEnv, actions: Sequence[Any], rng: random.Random) -> int:
        weights = probabilities(self.distribution(env, actions), len(actions))
        if not actions:
            raise ValueError("Cannot sample a policy without legal actions")
        # Stable key order keeps sampling unchanged when the API reorders actions.
        threshold = rng.random()
        order = sorted(range(len(actions)), key=lambda i: action_key(actions[i]))
        for index in order:
            threshold -= weights[index]
            if threshold < 0:
                return index
        return order[-1]


def apply_fixed_opponent(env: SearchEnv, target_player: str, policy: OpponentPolicy,
                         rng: random.Random) -> Any:
    """Apply one explicit opponent choice; never consume a chance roll."""
    owner = env.current_decision_player()
    if owner not in PLAYERS or owner == target_player or env.is_terminal():
        raise ValueError("There is no entitled fixed-opponent decision")
    actions = list(env.legal_actions())
    action = actions[policy.sample(env, actions, rng)]
    env.apply_action(action)
    return action


@dataclass(frozen=True, slots=True)
class MctsConfig:
    simulations: int = 128
    c_puct: float = 1.5
    max_depth: int = 256
    seed: int = 1
    rules_version: str = "gw36-v43-campaign-v1"
    mode: str = "multiplayer"
    target_player: str | None = None
    root_dirichlet_alpha: float = 0.3
    root_dirichlet_epsilon: float = 0.25
    record_trace: bool = False

    def __post_init__(self) -> None:
        if self.simulations <= 0 or self.max_depth <= 0:
            raise ValueError("Simulation budget and maximum depth must be positive")
        if not math.isfinite(self.c_puct) or self.c_puct < 0:
            raise ValueError("PUCT constant must be finite and nonnegative")
        if not self.rules_version or self.mode not in {"multiplayer", "fixed_opponents"}:
            raise ValueError("Search needs versioned rules and a supported opponent mode")
        if self.mode == "fixed_opponents" and self.target_player not in PLAYERS:
            raise ValueError("Fixed-opponent mode needs an explicit target player")
        if not math.isfinite(self.root_dirichlet_alpha) or self.root_dirichlet_alpha <= 0:
            raise ValueError("Dirichlet concentration must be positive and finite")
        if not 0 <= self.root_dirichlet_epsilon <= 1:
            raise ValueError("Dirichlet mixture must be between zero and one")


@dataclass(slots=True)
class Bounds:
    minimum: float = math.inf
    maximum: float = -math.inf

    def update(self, value: float) -> None:
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

    def normalize(self, value: float) -> float:
        return (value - self.minimum) / (self.maximum - self.minimum) if self.maximum > self.minimum else 0.5


@dataclass(slots=True)
class Edge:
    action: Any
    key: str
    prior: float
    selection_prior: float
    visits: int = 0
    value_sum: list[float] = field(default_factory=lambda: [0.0] * 3)
    successors: dict[str, Node] = field(default_factory=dict)

    @property
    def values(self) -> Vector | None:
        return vector([value / self.visits for value in self.value_sum]) if self.visits else None


@dataclass(slots=True)
class Node:
    state_key: str
    player: str | None
    kind: str
    expanded: bool = False
    edges: list[Edge] = field(default_factory=list)
    chance_successors: dict[str, Node] = field(default_factory=dict)
    visits: int = 0
    value_sum: list[float] = field(default_factory=lambda: [0.0] * 3)
    evaluation: Vector = ZERO


@dataclass(frozen=True, slots=True)
class ActionScore:
    action_key: str
    prior: float
    selection_prior: float
    visits: int
    values: Vector | None
    player_q: float | None
    normalized_q: float
    exploration: float
    score: float


def score_actions(node: Node, config: MctsConfig, bounds: Sequence[Bounds], *, use_selection_priors: bool = True) -> list[ActionScore]:
    if node.player not in PLAYERS:
        raise ValueError("Only an entitled player decision has PUCT action scores")
    component = PLAYERS.index(node.player)
    total = sum(edge.visits for edge in node.edges)
    result = []
    for edge in node.edges:
        selection_prior = edge.selection_prior if use_selection_priors else edge.prior
        values = edge.values
        q = values[component] if values is not None else None
        # Preserve optimistic FPU. There is no mandatory one-visit-per-child pass.
        normalized = bounds[component].normalize(q) if q is not None else 1.0
        exploration = config.c_puct * selection_prior * math.sqrt(total + 1.0) / (edge.visits + 1.0)
        result.append(ActionScore(edge.key, edge.prior, selection_prior, edge.visits,
                                  values, q, normalized, exploration, normalized + exploration))
    return result


@dataclass(frozen=True, slots=True)
class Selection:
    state_key: str
    player: str
    chosen_key: str
    mode: str
    scores: tuple[ActionScore, ...]


@dataclass(frozen=True, slots=True)
class Simulation:
    seed: int
    selections: tuple[Selection, ...]
    chance_outcomes: tuple[tuple[str, str], ...]
    values: Vector
    leaf_source: str


@dataclass(slots=True)
class SearchResult:
    actions: list[Any]
    visit_counts: list[int]
    policy: list[float]
    priors: list[float]
    values: Vector
    action_values: list[Vector | None]
    root: Node
    cache_identity: tuple[str, ...]
    reused_root: bool
    simulations: list[Simulation]

    def best_action(self) -> Any:
        if not self.actions:
            raise ValueError("Chance and terminal roots have no policy action")
        index = min(range(len(self.actions)), key=lambda i: (-self.visit_counts[i], action_key(self.actions[i])))
        return self.actions[index]


class VectorMCTS:
    def __init__(self, evaluator: Evaluator | None = None, config: MctsConfig | None = None,
                 opponent_policy: OpponentPolicy | None = None):
        self.evaluator = evaluator or UniformEvaluator()
        self.config = config or MctsConfig()
        self.opponent_policy = opponent_policy
        if not getattr(self.evaluator, "version", ""):
            raise ValueError("Evaluator needs a nonempty version")
        if (self.config.mode == "fixed_opponents") != (opponent_policy is not None):
            raise ValueError("Fixed-opponent mode and its versioned policy must be specified together")
        self.nodes: dict[tuple[str, ...], Node] = {}
        self._bounds: dict[tuple[str, ...], list[Bounds]] = {}
        self._random = random.Random(self.config.seed)

    def cache_identity(self, env: SearchEnv) -> tuple[str, ...]:
        return (self.config.rules_version, self.evaluator.version, self.config.mode,
                self.config.target_player or "", self.opponent_policy.version if self.opponent_policy else "",
                f"max_depth={self.config.max_depth}",
                env.planning_key())

    def _node(self, env: SearchEnv) -> tuple[Node, bool]:
        interrupts = getattr(env, "legal_interrupts", None)
        if callable(interrupts) and interrupts():
            raise ValueError("Wrap raw campaign interrupts in CampaignAdapter; search cannot silently skip an opponent's opportunity")
        if env.decision_kind() in {"chance", "terminal"} and env.current_decision_player() is not None:
            raise ValueError("Chance and terminal states cannot have a policy decision owner")
        if env.is_terminal() != (env.decision_kind() == "terminal"):
            raise ValueError("Terminal status and decision kind disagree")
        identity = self.cache_identity(env)
        reused = identity in self.nodes
        if not reused:
            self.nodes[identity] = Node(env.planning_key(), env.current_decision_player(), env.decision_kind())
        node = self.nodes[identity]
        if node.player != env.current_decision_player() or node.kind != env.decision_kind():
            raise ValueError("Planning key merges different decision owners or kinds")
        return node, reused

    def _expand(self, node: Node, env: SearchEnv) -> Vector:
        if env.is_terminal():
            node.evaluation = vector(env.returns())
        elif node.kind == "chance":
            node.evaluation = ZERO
        else:
            if node.player not in PLAYERS:
                raise ValueError("A policy decision must name its entitled player")
            actions = list(env.legal_actions())
            if not actions:
                raise ValueError("Nonterminal decision has no legal action")
            keys = [action_key(action) for action in actions]
            if len(set(keys)) != len(keys):
                raise ValueError("Legal actions need unique stable identities")
            evaluation = self.evaluator.evaluate(env, actions)
            priors = probabilities(evaluation.priors, len(actions))
            node.evaluation = vector(evaluation.values)
            node.edges = [Edge(action, key, p, p) for action, key, p in zip(actions, keys, priors)]
        node.expanded = True
        return node.evaluation

    def _bootstrap_value(self, node: Node, env: SearchEnv) -> Vector:
        """Approximate a nonterminal cutoff with the frozen evaluator value.

        Chance nodes have no policy expansion and their stored evaluation is
        only a placeholder. They need an explicit value-only evaluation rather
        than a zero return or an extra sampled outcome.
        """
        if node.kind == "chance":
            return vector(self.evaluator.evaluate(env, []).values)
        return node.evaluation if node.expanded else self._expand(node, env)

    def search(self, env: SearchEnv, *, add_root_noise: bool = False, reuse_root: bool = True) -> SearchResult:
        if not reuse_root:
            self.nodes.clear()
            self._bounds.clear()
        identity = self.cache_identity(env)
        root, reused = self._node(env)
        if not root.expanded:
            self._expand(root, env)
        bounds = self._bounds.setdefault(identity[:-1], [Bounds() for _ in PLAYERS])
        # A previously noised root may now be an internal transposition. Noise
        # is local to this search's root opportunity, never cached as a policy.
        for cached in self.nodes.values():
            for edge in cached.edges:
                edge.selection_prior = edge.prior
        if add_root_noise and root.edges:
            order = sorted(root.edges, key=lambda edge: edge.key)
            noise = [self._random.gammavariate(self.config.root_dirichlet_alpha, 1.0) for _ in order]
            total = sum(noise)
            for edge, value in zip(order, noise):
                epsilon = self.config.root_dirichlet_epsilon
                edge.selection_prior = (1 - epsilon) * edge.prior + epsilon * (value / total if total else 1 / len(order))

        traces = []
        for _ in range(self.config.simulations):
            seed = self._random.getrandbits(64)
            simulation = env.clone_for_search(seed)
            policy_random = random.Random(seed ^ 0xD1B54A32D192ED03)
            node = root
            nodes_path = [root]
            path_keys = {root.state_key}
            edges_path = []
            selections = []
            outcomes = []
            source = "depth_limit"
            for _depth in range(self.config.max_depth):
                if simulation.is_terminal():
                    values, source = vector(simulation.returns()), "terminal"
                    break
                if simulation.decision_kind() == "chance":
                    before = simulation.planning_key()
                    simulation.resolve_chance()
                    successor, _ = self._node(simulation)
                    node.chance_successors[successor.state_key] = successor
                    outcomes.append((before, successor.state_key))
                    if successor.state_key in path_keys:
                        values, source = self._bootstrap_value(successor, simulation), "cycle_cutoff"
                        break
                    node = successor
                    nodes_path.append(node)
                    path_keys.add(node.state_key)
                    continue
                if not node.expanded:
                    values, source = self._expand(node, simulation), "evaluator"
                    break
                actions = [edge.action for edge in node.edges]
                fixed = self.config.mode == "fixed_opponents" and node.player != self.config.target_player
                if fixed:
                    assert self.opponent_policy is not None
                    selected = self.opponent_policy.sample(simulation, actions, policy_random)
                    scores = []
                else:
                    scores = score_actions(node, self.config, bounds, use_selection_priors=_depth == 0)
                    maximum = max(score.score for score in scores)
                    tied = sorted((i for i, score in enumerate(scores) if score.score == maximum),
                                  key=lambda i: node.edges[i].key)
                    selected = tied[policy_random.randrange(len(tied))]
                edge = node.edges[selected]
                if self.config.record_trace:
                    selections.append(Selection(node.state_key, str(node.player), edge.key,
                                                "opponent_policy" if fixed else "puct", tuple(scores)))
                simulation.apply_action(edge.action)
                edges_path.append(edge)
                successor, _ = self._node(simulation)
                edge.successors[successor.state_key] = successor
                # A reversible planning sequence can return to an exact state.
                # Stop at its first repetition and bootstrap; revisiting it
                # inside this rollout would count one simulation repeatedly in
                # the same node/action and inflate the cycle's policy target.
                if successor.state_key in path_keys:
                    values, source = self._bootstrap_value(successor, simulation), "cycle_cutoff"
                    break
                node = successor
                nodes_path.append(node)
                path_keys.add(node.state_key)
            else:
                if simulation.is_terminal():
                    values, source = vector(simulation.returns()), "terminal"
                else:
                    # A cutoff is an explicit approximation, never a fake
                    # terminal return or a policy-selected die outcome.
                    values = self._bootstrap_value(node, simulation)

            for visited in nodes_path:
                visited.visits += 1
                for component, value in enumerate(values):
                    visited.value_sum[component] += value
            for edge in edges_path:
                edge.visits += 1
                for component, value in enumerate(values):
                    edge.value_sum[component] += value
                    bounds[component].update(edge.value_sum[component] / edge.visits)
            if self.config.record_trace:
                traces.append(Simulation(seed, tuple(selections), tuple(outcomes), values, source))

        total = sum(edge.visits for edge in root.edges)
        return SearchResult([edge.action for edge in root.edges], [edge.visits for edge in root.edges],
                            [edge.visits / total for edge in root.edges] if total else [edge.prior for edge in root.edges],
                            [edge.prior for edge in root.edges],
                            vector([value / root.visits for value in root.value_sum]),
                            [edge.values for edge in root.edges], root, identity, reused, traces)
