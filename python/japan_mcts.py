from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import torch
from torch.distributions import Categorical, Dirichlet


@dataclass(slots=True)
class MctsConfig:
    simulations: int = 64
    c_puct: float = 1.5
    root_dirichlet_alpha: float = 0.3
    root_dirichlet_epsilon: float = 0.25
    self_play_temperature: float = 1.0


@dataclass(slots=True)
class MctsNode:
    actions: list[Any] = field(default_factory=list)
    priors: list[float] = field(default_factory=list)
    selection_priors: list[float] = field(default_factory=list)
    children: list["MctsNode | None"] = field(default_factory=list)
    visit_counts: list[int] = field(default_factory=list)
    value_sums: list[float] = field(default_factory=list)
    expanded: bool = False


@dataclass(slots=True)
class MinMaxStats:
    minimum: float = float("inf")
    maximum: float = -float("inf")

    def update(self, value: float) -> None:
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

    def normalize(self, value: float) -> float:
        if self.maximum > self.minimum:
            return (value - self.minimum) / (self.maximum - self.minimum)
        return 0.5


@dataclass(slots=True)
class MctsSearchResult:
    state_features: list[float]
    legal_action_features: list[list[float]]
    actions: list[Any]
    visit_counts: list[int]
    policy: list[float]
    priors: list[float]
    root_value: float
    action_values: list[float]


@dataclass(slots=True)
class MctsActionScoreDebug:
    action_description: str
    prior: float
    selection_prior: float
    visit_count: int
    raw_q_value: float | None
    normalized_q_value: float
    exploration: float
    score: float


@dataclass(slots=True)
class MctsSelectionStepDebug:
    depth: int
    current_nation: str
    current_phase: str
    action_scores: list[MctsActionScoreDebug]
    chosen_action_index: int
    chosen_action_description: str


@dataclass(slots=True)
class MctsBackupStepDebug:
    depth: int
    action_description: str
    new_visit_count: int
    new_raw_q_value: float
    min_q_value: float
    max_q_value: float


@dataclass(slots=True)
class MctsSimulationDebug:
    simulation_index: int
    selection_steps: list[MctsSelectionStepDebug]
    selected_path: list[str]
    leaf_source: str
    leaf_value: float
    leaf_nation: str
    leaf_phase: str
    backup_steps: list[MctsBackupStepDebug]


@dataclass(slots=True)
class MctsDebugTrace:
    root_value: float
    root_actions: list[str]
    root_priors: list[float]
    root_selection_priors: list[float]
    simulations: list[MctsSimulationDebug]


def tensorize_state_and_actions(
    state_features: list[float],
    legal_action_features: list[list[float]],
) -> tuple[torch.Tensor, torch.Tensor]:
    state_tensor = torch.tensor(state_features, dtype=torch.float32).unsqueeze(0)
    action_tensor = torch.tensor(legal_action_features, dtype=torch.float32).unsqueeze(0)
    return state_tensor, action_tensor


def _expand_node(
    node: MctsNode,
    env: Any,
    model: torch.nn.Module,
    *,
    state_features: list[float] | None = None,
    legal_action_features: list[list[float]] | None = None,
    actions: list[Any] | None = None,
) -> float:
    if env.is_terminal():
        node.expanded = True
        node.actions = []
        node.priors = []
        node.selection_priors = []
        node.children = []
        node.visit_counts = []
        node.value_sums = []
        return float(env.final_reward())

    state_features = env.encode_state() if state_features is None else state_features
    legal_action_features = (
        env.encode_legal_actions() if legal_action_features is None else legal_action_features
    )
    actions = env.legal_actions() if actions is None else actions

    state_tensor, action_tensor = tensorize_state_and_actions(state_features, legal_action_features)
    with torch.no_grad():
        logits, value = model(state_tensor, action_tensor)
        priors_tensor = torch.softmax(logits.squeeze(0), dim=0)

    priors = [float(item) for item in priors_tensor.tolist()]
    node.actions = actions
    node.priors = priors
    node.selection_priors = priors.copy()
    node.children = [None] * len(actions)
    node.visit_counts = [0] * len(actions)
    node.value_sums = [0.0] * len(actions)
    node.expanded = True
    return float(value.item())


def _apply_root_dirichlet_noise(node: MctsNode, config: MctsConfig) -> None:
    if not node.priors:
        return
    concentration = torch.full((len(node.priors),), config.root_dirichlet_alpha, dtype=torch.float32)
    noise = Dirichlet(concentration).sample().tolist()
    node.selection_priors = [
        (1.0 - config.root_dirichlet_epsilon) * prior + config.root_dirichlet_epsilon * float(noise_value)
        for prior, noise_value in zip(node.priors, noise)
    ]


def _describe_action(action: Any) -> str:
    if hasattr(action, "describe"):
        return str(action.describe())
    return str(action)


def _score_actions(
    node: MctsNode,
    config: MctsConfig,
    min_max_stats: MinMaxStats,
) -> tuple[list[MctsActionScoreDebug], int]:
    total_visits = sum(node.visit_counts)
    action_scores: list[MctsActionScoreDebug] = []

    for index, prior in enumerate(node.selection_priors):
        visit_count = node.visit_counts[index]
        if visit_count > 0:
            q_value = node.value_sums[index] / visit_count
            normalized_q_value = min_max_stats.normalize(q_value)
        else:
            q_value = None
            # Optimistic first-play urgency: an unvisited action is unknown,
            # rather than the worst action observed by the search.
            normalized_q_value = 1.0
        exploration = config.c_puct * prior * math.sqrt(total_visits + 1.0) / (visit_count + 1.0)
        score = normalized_q_value + exploration
        action_scores.append(
            MctsActionScoreDebug(
                action_description=_describe_action(node.actions[index]),
                prior=node.priors[index] if index < len(node.priors) else prior,
                selection_prior=prior,
                visit_count=visit_count,
                raw_q_value=q_value,
                normalized_q_value=normalized_q_value,
                exploration=exploration,
                score=score,
            )
        )
    best_index = max(range(len(action_scores)), key=lambda index: action_scores[index].score)
    return action_scores, best_index


def _select_child_index(node: MctsNode, config: MctsConfig, min_max_stats: MinMaxStats) -> int:
    _, best_index = _score_actions(node, config, min_max_stats)
    return best_index


def backup_value(
    search_path: list[tuple[MctsNode, int]],
    leaf_value: float,
    min_max_stats: MinMaxStats,
) -> None:
    for node, action_index in search_path:
        node.visit_counts[action_index] += 1
        node.value_sums[action_index] += leaf_value
        q_value = node.value_sums[action_index] / node.visit_counts[action_index]
        min_max_stats.update(q_value)


def backup_value_with_debug(
    search_path: list[tuple[MctsNode, int]],
    leaf_value: float,
    min_max_stats: MinMaxStats,
) -> list[MctsBackupStepDebug]:
    backup_steps: list[MctsBackupStepDebug] = []
    for depth, (node, action_index) in enumerate(search_path):
        node.visit_counts[action_index] += 1
        node.value_sums[action_index] += leaf_value
        q_value = node.value_sums[action_index] / node.visit_counts[action_index]
        min_max_stats.update(q_value)
        backup_steps.append(
            MctsBackupStepDebug(
                depth=depth,
                action_description=_describe_action(node.actions[action_index]),
                new_visit_count=node.visit_counts[action_index],
                new_raw_q_value=q_value,
                min_q_value=min_max_stats.minimum,
                max_q_value=min_max_stats.maximum,
            )
        )
    return backup_steps


def run_mcts(
    env: Any,
    model: torch.nn.Module,
    config: MctsConfig,
    *,
    add_root_noise: bool,
) -> MctsSearchResult:
    if config.simulations <= 0:
        raise ValueError("MCTS simulations must be positive")

    root_state_features = env.encode_state()
    root_legal_action_features = env.encode_legal_actions()
    root_actions = env.legal_actions()

    root = MctsNode()
    min_max_stats = MinMaxStats()
    root_value = _expand_node(
        root,
        env,
        model,
        state_features=root_state_features,
        legal_action_features=root_legal_action_features,
        actions=root_actions,
    )
    if add_root_noise:
        _apply_root_dirichlet_noise(root, config)

    for _ in range(config.simulations):
        simulation_env = env.clone()
        node = root
        search_path: list[tuple[MctsNode, int]] = []

        while True:
            if simulation_env.is_terminal():
                leaf_value = float(simulation_env.final_reward())
                break
            if not node.expanded:
                leaf_value = _expand_node(node, simulation_env, model)
                break
            if not node.actions:
                leaf_value = float(simulation_env.final_reward())
                break

            action_index = _select_child_index(node, config, min_max_stats)
            search_path.append((node, action_index))
            simulation_env.step(node.actions[action_index])

            child = node.children[action_index]
            if child is None:
                child = MctsNode()
                node.children[action_index] = child
            node = child

        backup_value(search_path, leaf_value, min_max_stats)

    total_visits = sum(root.visit_counts)
    if total_visits == 0:
        policy = root.priors.copy()
    else:
        policy = [visit_count / total_visits for visit_count in root.visit_counts]
    action_values = [
        value_sum / visit_count if visit_count > 0 else 0.0
        for value_sum, visit_count in zip(root.value_sums, root.visit_counts)
    ]
    return MctsSearchResult(
        state_features=root_state_features,
        legal_action_features=root_legal_action_features,
        actions=root_actions,
        visit_counts=root.visit_counts,
        policy=policy,
        priors=root.priors,
        root_value=root_value,
        action_values=action_values,
    )


def run_mcts_with_debug(
    env: Any,
    model: torch.nn.Module,
    config: MctsConfig,
    *,
    add_root_noise: bool,
) -> tuple[MctsSearchResult, MctsDebugTrace]:
    if config.simulations <= 0:
        raise ValueError("MCTS simulations must be positive")

    root_state_features = env.encode_state()
    root_legal_action_features = env.encode_legal_actions()
    root_actions = env.legal_actions()

    root = MctsNode()
    min_max_stats = MinMaxStats()
    root_value = _expand_node(
        root,
        env,
        model,
        state_features=root_state_features,
        legal_action_features=root_legal_action_features,
        actions=root_actions,
    )
    if add_root_noise:
        _apply_root_dirichlet_noise(root, config)

    simulation_traces: list[MctsSimulationDebug] = []

    for simulation_index in range(config.simulations):
        simulation_env = env.clone()
        node = root
        search_path: list[tuple[MctsNode, int]] = []
        selected_path: list[str] = []
        selection_steps: list[MctsSelectionStepDebug] = []

        while True:
            if simulation_env.is_terminal():
                leaf_source = "terminal"
                leaf_value = float(simulation_env.final_reward())
                leaf_nation = simulation_env.current_nation()
                leaf_phase = simulation_env.current_phase()
                break
            if not node.expanded:
                leaf_source = "network"
                leaf_value = _expand_node(node, simulation_env, model)
                leaf_nation = simulation_env.current_nation()
                leaf_phase = simulation_env.current_phase()
                break
            if not node.actions:
                leaf_source = "terminal"
                leaf_value = float(simulation_env.final_reward())
                leaf_nation = simulation_env.current_nation()
                leaf_phase = simulation_env.current_phase()
                break

            action_scores, action_index = _score_actions(node, config, min_max_stats)
            chosen_action = node.actions[action_index]
            selection_steps.append(
                MctsSelectionStepDebug(
                    depth=len(search_path),
                    current_nation=simulation_env.current_nation(),
                    current_phase=simulation_env.current_phase(),
                    action_scores=action_scores,
                    chosen_action_index=action_index,
                    chosen_action_description=_describe_action(chosen_action),
                )
            )
            search_path.append((node, action_index))
            selected_path.append(_describe_action(chosen_action))
            simulation_env.step(chosen_action)

            child = node.children[action_index]
            if child is None:
                child = MctsNode()
                node.children[action_index] = child
            node = child

        backup_steps = backup_value_with_debug(search_path, leaf_value, min_max_stats)
        simulation_traces.append(
            MctsSimulationDebug(
                simulation_index=simulation_index + 1,
                selection_steps=selection_steps,
                selected_path=selected_path,
                leaf_source=leaf_source,
                leaf_value=leaf_value,
                leaf_nation=leaf_nation,
                leaf_phase=leaf_phase,
                backup_steps=backup_steps,
            )
        )

    total_visits = sum(root.visit_counts)
    if total_visits == 0:
        policy = root.priors.copy()
    else:
        policy = [visit_count / total_visits for visit_count in root.visit_counts]
    action_values = [
        value_sum / visit_count if visit_count > 0 else 0.0
        for value_sum, visit_count in zip(root.value_sums, root.visit_counts)
    ]
    result = MctsSearchResult(
        state_features=root_state_features,
        legal_action_features=root_legal_action_features,
        actions=root_actions,
        visit_counts=root.visit_counts,
        policy=policy,
        priors=root.priors,
        root_value=root_value,
        action_values=action_values,
    )
    debug_trace = MctsDebugTrace(
        root_value=root_value,
        root_actions=[_describe_action(action) for action in root_actions],
        root_priors=root.priors.copy(),
        root_selection_priors=root.selection_priors.copy(),
        simulations=simulation_traces,
    )
    return result, debug_trace


def select_action_index_from_policy(policy: list[float], temperature: float) -> int:
    if not policy:
        raise ValueError("Cannot select from an empty policy")
    if temperature <= 0.0:
        return max(range(len(policy)), key=lambda index: policy[index])

    policy_tensor = torch.tensor(policy, dtype=torch.float32)
    powered = torch.pow(policy_tensor.clamp_min(1e-8), 1.0 / temperature)
    probabilities = powered / powered.sum()
    return int(Categorical(probs=probabilities).sample().item())
