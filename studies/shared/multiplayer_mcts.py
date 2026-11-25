"""Vector-valued PUCT with explicit stochastic successors.

The three components always mean Axis, Allies, Comintern. Decision owners choose
their own component; chance samples the rules environment and never becomes a
policy decision. This is finite-budget Max-N search, not an equilibrium solver.

A root with one legal action has nothing to decide, so a search returns it at
once: no evaluation, no simulations and no value estimate. The caller's random
draws are outside the search, so a game evaluated one position at a time plays
exactly as if it had searched. With batched evaluation the skipped positions
leave their batches, which can change other positions' network outputs in the
last digits. Inside a search, a new state with one legal action is not asked
about either: the simulation plays its action and goes on, and the network
rates such a state only when a simulation has to stop there.

A search object kept from one decision to the next keeps its tree: the next
search starts from the node of the state it is asked about, with everything
below it, and drops the rest; a state the tree never reached starts a new tree.
The C++ search (src/search.cpp) is the same search, checked against this one.
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
    # A copy of this position whose dice continue source's search stream.
    def clone_for_search_continuing(self, source: SearchEnv) -> SearchEnv: ...
    def planning_key(self) -> str: ...


class NoLegalActionError(ValueError):
    """A nonterminal decision without legal actions, which is a rules defect.

    Keeps the position's serialized state when the environment offers one, so an
    imagined search position can be reproduced as well as an actual one.
    """

    def __init__(self, env: Any):
        super().__init__("Nonterminal decision has no legal action")
        serialize = getattr(env, "serialize", None)
        self.state = serialize() if callable(serialize) else None


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
    search_forced_root: bool = False  # Simulate a one-action root anyway.
    # Simulations whose positions the C++ search asks about in one request
    # (game/search.hpp, SearchSettings::simulationsPerRequest); this search plays
    # one at a time and refuses any other number.
    simulations_per_request: int = 1
    # Whether the budget counts the visits the root's actions already hold from
    # a reused tree: the search then runs only as many new simulations as bring
    # them to `simulations`, and none when they hold that many (self-play's fast
    # searches; SearchSettings::countReusedVisits in the C++ search).
    count_reused_visits: bool = False

    def __post_init__(self) -> None:
        if self.simulations <= 0 or self.max_depth <= 0:
            raise ValueError("Simulation budget and maximum depth must be positive")
        if type(self.simulations_per_request) is not int or self.simulations_per_request <= 0:
            raise ValueError("Simulations per request must be a positive integer")
        if type(self.count_reused_visits) is not bool:
            raise ValueError("count_reused_visits must be true or false")
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
    # Whether evaluation holds the network's value (or a terminal state's
    # returns): a state with one legal action is expanded without one.
    evaluated: bool = False
    # A copy of the game at this position. Simulations only copy it again, to
    # play one move or roll dice there; nothing plays on it.
    game: Any = None


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


def selection_scores(node: Node, config: MctsConfig, bounds: Sequence[Bounds], *, use_selection_priors: bool = True) -> list[float]:
    """The scores of score_actions, without a record per edge.

    A search calls this at every step of every simulation; traces use
    score_actions. Each value that reaches an edge has already passed vector().
    """
    if node.player not in PLAYERS:
        raise ValueError("Only an entitled player decision has PUCT action scores")
    component = PLAYERS.index(node.player)
    normalize = bounds[component].normalize
    c_puct = config.c_puct
    scale = math.sqrt(sum([edge.visits for edge in node.edges]) + 1.0)
    scores = []
    for edge in node.edges:
        visits = edge.visits
        normalized = normalize(edge.value_sum[component] / visits) if visits else 1.0
        prior = edge.selection_prior if use_selection_priors else edge.prior
        scores.append(normalized + c_puct * prior * scale / (visits + 1.0))
    return scores


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
    values: Vector | None  # None when a one-action root was not searched.
    action_values: list[Vector | None]
    root: Node | None  # None from the C++ search, which keeps no Python tree.
    cache_identity: tuple[str, ...]
    reused_root: bool
    simulations: list[Simulation]
    # The root's zone input as the network read it, when the search kept it.
    zone_input: Any = None
    # The alliance choosing at the root, when the search's caller named it; the
    # Python search's root node names it too.
    player: str | None = None

    def best_action(self) -> Any:
        """The most visited action (most_visited_index)."""
        if not self.actions:
            raise ValueError("Chance and terminal roots have no policy action")
        player = self.player if self.player is not None else getattr(self.root, "player", None)
        return self.actions[most_visited_index(self.visit_counts, self.action_values, self.priors, self.actions,
                                               player)]


def most_visited_index(visit_counts: Sequence[int], action_values: Sequence[Vector | None],
                       priors: Sequence[float], actions: Sequence[Any], player: str | None,
                       rng: random.Random | None = None) -> int:
    """The position of the most visited action among a search's root actions.

    Among actions with equally many visits, the one whose simulations' average
    result is best for the alliance choosing comes first, then the one with the
    higher prior. With few simulations among many legal actions most visited
    actions are often tied, at one visit each; the average result is then what
    the search found about them. Actions tied on all three are taken in the
    order of their action keys: the first, or with `rng` one at random, so that
    a network whose values and priors are all equal, as a fresh one's are,
    plays no action for its name.
    """
    column = PLAYERS.index(player) if player in PLAYERS else None

    def result(index: int) -> float:
        values = action_values[index]
        return -math.inf if column is None or values is None else float(values[column])

    def rank(index: int) -> tuple[float, float, float]:
        return (-visit_counts[index], -result(index), -priors[index])

    best = min(rank(index) for index in range(len(actions)))
    tied = sorted((index for index in range(len(actions)) if rank(index) == best),
                  key=lambda index: action_key(actions[index]))
    return tied[0] if rng is None or len(tied) == 1 else tied[rng.randrange(len(tied))]


class VectorMCTS:
    def __init__(self, evaluator: Evaluator | None = None, config: MctsConfig | None = None,
                 opponent_policy: OpponentPolicy | None = None):
        self.evaluator = evaluator or UniformEvaluator()
        self.config = config or MctsConfig()
        self.opponent_policy = opponent_policy
        if self.config.simulations_per_request != 1:
            raise ValueError("The Python search plays one simulation at a time; only the C++ search asks for several")
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
        kind, player = env.decision_kind(), env.current_decision_player()
        if kind in {"chance", "terminal"} and player is not None:
            raise ValueError("Chance and terminal states cannot have a policy decision owner")
        if env.is_terminal() != (kind == "terminal"):
            raise ValueError("Terminal status and decision kind disagree")
        identity = self.cache_identity(env)
        reused = identity in self.nodes
        if not reused:
            self.nodes[identity] = Node(identity[-1], player, kind)
        node = self.nodes[identity]
        if node.player != player or node.kind != kind:
            raise ValueError("Planning key merges different decision owners or kinds")
        return node, reused

    def _legal(self, node: Node, env: SearchEnv) -> tuple[list[Any], list[str]]:
        """A policy decision's legal actions and their stable identities."""
        if node.player not in PLAYERS:
            raise ValueError("A policy decision must name its entitled player")
        actions = list(env.legal_actions())
        if not actions:
            raise NoLegalActionError(env)
        keys = [action_key(action) for action in actions]
        if len(set(keys)) != len(keys):
            raise ValueError("Legal actions need unique stable identities")
        return actions, keys

    def _expand(self, node: Node, env: SearchEnv, *, root: bool = False) -> Vector | None:
        """Ask the network about a new state; None for a forced state inside the tree.

        A state with one legal action, other than the root, gets its one edge
        without an evaluation: a simulation plays the action and goes on.
        """
        if env.is_terminal():
            node.evaluation, node.evaluated = vector(env.returns()), True
        elif node.kind == "chance":
            node.evaluation = ZERO
        else:
            actions, keys = self._legal(node, env)
            if len(actions) == 1 and not root:
                node.edges = [Edge(actions[0], keys[0], 1.0, 1.0)]
                node.expanded = True
                return None
            evaluation = self.evaluator.evaluate(env, actions)
            priors = probabilities(evaluation.priors, len(actions))
            node.evaluation, node.evaluated = vector(evaluation.values), True
            node.edges = [Edge(action, key, p, p) for action, key, p in zip(actions, keys, priors)]
        node.expanded = True
        return node.evaluation

    @staticmethod
    def _copy(node: Node, seed: int, stream: SearchEnv | None) -> SearchEnv:
        """A copy of node's position to play on, continuing the simulation's dice."""
        return node.game.clone_for_search(seed) if stream is None else node.game.clone_for_search_continuing(stream)

    def _reach(self, game: SearchEnv) -> Node:
        """The node of the position a copy has reached; a new node keeps the copy."""
        node, _ = self._node(game)
        if node.game is None:
            node.game = game
        return node

    def _bootstrap_value(self, node: Node, env: SearchEnv) -> Vector:
        """Approximate a nonterminal cutoff with the frozen evaluator value.

        Chance nodes have no policy expansion and their stored evaluation is
        only a placeholder. They need an explicit value-only evaluation rather
        than a zero return or an extra sampled outcome.
        """
        if node.kind == "chance":
            return vector(self.evaluator.evaluate(env, []).values)
        if not node.expanded:
            value = self._expand(node, env)
            if value is not None:
                return value
        if not node.evaluated:
            # A forced state, rated only now that a simulation stops at it.
            node.evaluation = vector(self.evaluator.evaluate(env, [edge.action for edge in node.edges]).values)
            node.evaluated = True
        return node.evaluation

    def _retain(self, root: Node) -> None:
        """Keep root and every node below it; drop the rest of the tree."""
        kept, stack = set(), [root]
        while stack:
            node = stack.pop()
            if id(node) in kept:
                continue
            kept.add(id(node))
            for edge in node.edges:
                stack.extend(edge.successors.values())
            stack.extend(node.chance_successors.values())
        self.nodes = {identity: node for identity, node in self.nodes.items() if id(node) in kept}

    def search(self, env: SearchEnv, *, add_root_noise: bool = False, reuse_root: bool = True,
               seed: int | None = None) -> SearchResult:
        """Search env's decision. With reuse_root the tree keeps the subtree of
        env's state from earlier searches and drops the rest; `seed`, when
        given, starts this search's random stream instead of the next draws of
        the config's seed."""
        if seed is not None:
            self._random = random.Random(seed)
        identity = self.cache_identity(env)
        if reuse_root and identity in self.nodes:
            self._retain(self.nodes[identity])
        else:
            self.nodes.clear()
        self._bounds.clear()
        root, reused = self._node(env)
        if root.kind not in {"chance", "terminal"} and not self.config.search_forced_root:
            actions, _ = self._legal(root, env)
            if len(actions) == 1:
                return SearchResult(actions, [0], [1.0], [1.0], None, [None], root, identity, reused, [])
        if not root.expanded:
            self._expand(root, env, root=True)
        # The value bounds start from the kept tree's actions, as the search
        # that made them left them, and widen as this search backs up values.
        bounds = self._bounds.setdefault(identity[:-1], [Bounds() for _ in PLAYERS])
        for cached in self.nodes.values():
            for edge in cached.edges:
                if edge.visits:
                    for component in range(3):
                        bounds[component].update(edge.value_sum[component] / edge.visits)
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
        if root.game is None:
            # Never the game itself: it moves on after the search.
            root.game = env.clone_for_search(0)
        # The new simulations: the whole budget, or, when the budget counts the
        # visits the root's actions hold from a reused tree, what they lack of it.
        budget = self.config.simulations
        if self.config.count_reused_visits:
            budget = max(0, budget - sum(edge.visits for edge in root.edges))
        for _ in range(budget):
            seed = self._random.getrandbits(64)
            policy_random = random.Random(seed ^ 0xD1B54A32D192ED03)
            # Walk the tree on its saved positions. Only playing a new move or
            # rolling dice copies one; each copy continues the last, so the
            # simulation's dice come from one stream started from its seed,
            # exactly as if it had played its whole path on one copy.
            stream: SearchEnv | None = None
            node = root
            nodes_path = [root]
            path_keys = {root.state_key}
            edges_path = []
            selections = []
            outcomes = []
            source = "depth_limit"
            for _depth in range(self.config.max_depth):
                if node.kind == "terminal":
                    values, source = vector(node.game.returns()), "terminal"
                    break
                if node.kind == "chance":
                    stream = self._copy(node, seed, stream)
                    stream.resolve_chance()
                    successor = self._reach(stream)
                    node.chance_successors.setdefault(successor.state_key, successor)
                    outcomes.append((node.state_key, successor.state_key))
                    if successor.state_key in path_keys:
                        values, source = self._bootstrap_value(successor, successor.game), "cycle_cutoff"
                        break
                    node = successor
                    nodes_path.append(node)
                    path_keys.add(node.state_key)
                    continue
                if not node.expanded:
                    value = self._expand(node, node.game)
                    if value is not None:
                        values, source = value, "evaluator"
                        break
                    # A forced state: its one action is played below, unasked.
                fixed = self.config.mode == "fixed_opponents" and node.player != self.config.target_player
                if fixed:
                    assert self.opponent_policy is not None
                    selected = self.opponent_policy.sample(node.game, [edge.action for edge in node.edges], policy_random)
                else:
                    scores = selection_scores(node, self.config, bounds, use_selection_priors=_depth == 0)
                    maximum = max(scores)
                    tied = sorted((i for i, score in enumerate(scores) if score == maximum),
                                  key=lambda i: node.edges[i].key)
                    selected = tied[policy_random.randrange(len(tied))]
                edge = node.edges[selected]
                if self.config.record_trace:
                    records = [] if fixed else score_actions(node, self.config, bounds, use_selection_priors=_depth == 0)
                    selections.append(Selection(node.state_key, str(node.player), edge.key,
                                                "opponent_policy" if fixed else "puct", tuple(records)))
                edges_path.append(edge)
                if edge.successors:
                    # The engine rolls no dice inside a move, so a move played
                    # once from a position leads to the same position every time.
                    (successor,) = edge.successors.values()
                else:
                    stream = self._copy(node, seed, stream)
                    stream.apply_action(edge.action)
                    successor = self._reach(stream)
                    edge.successors[successor.state_key] = successor
                # A reversible planning sequence can return to an exact state.
                # Stop at its first repetition and bootstrap; revisiting it
                # inside this rollout would count one simulation repeatedly in
                # the same node/action and inflate the cycle's policy target.
                if successor.state_key in path_keys:
                    values, source = self._bootstrap_value(successor, successor.game), "cycle_cutoff"
                    break
                node = successor
                nodes_path.append(node)
                path_keys.add(node.state_key)
            else:
                if node.kind == "terminal":
                    values, source = vector(node.game.returns()), "terminal"
                else:
                    # A cutoff is an explicit approximation, never a fake
                    # terminal return or a policy-selected die outcome.
                    values = self._bootstrap_value(node, node.game)

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
