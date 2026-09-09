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
    player_to_move: str = ""
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
    player_to_move: str
    state_features: list[float]
    legal_action_features: list[list[float]]
    actions: list[Any]
    visit_counts: list[int]
    policy: list[float]
    priors: list[float]
    root_value: float
    action_values: list[float]
    normalized_q_values: list[float]
    exploration_terms: list[float]
    action_scores: list[float]
    q_min: float
    q_max: float


def _model_for_player(player_to_move: str, attacker_model: torch.nn.Module, defender_model: torch.nn.Module) -> torch.nn.Module:
    if player_to_move == "Attacker":
        return attacker_model
    if player_to_move == "Defender":
        return defender_model
    raise ValueError(f"Unknown player_to_move: {player_to_move}")


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
    attacker_model: torch.nn.Module,
    defender_model: torch.nn.Module,
    *,
    state_features: list[float] | None = None,
    legal_action_features: list[list[float]] | None = None,
    actions: list[Any] | None = None,
) -> float:
    if env.is_terminal():
        raise ValueError("_expand_node should not be called on a terminal state")

    player_to_move = env.current_nation()
    model = _model_for_player(player_to_move, attacker_model, defender_model)
    state_features = env.encode_state() if state_features is None else state_features
    legal_action_features = env.encode_legal_actions() if legal_action_features is None else legal_action_features
    actions = env.legal_actions() if actions is None else actions

    state_tensor, action_tensor = tensorize_state_and_actions(state_features, legal_action_features)
    with torch.no_grad():
        logits, value = model(state_tensor, action_tensor)
        priors_tensor = torch.softmax(logits.squeeze(0), dim=0)

    priors = [float(item) for item in priors_tensor.tolist()]
    node.player_to_move = player_to_move
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


def _select_child_index(node: MctsNode, config: MctsConfig, min_max_stats: MinMaxStats) -> int:
    total_visits = sum(node.visit_counts)
    best_index = 0
    best_score = -float("inf")
    for index, prior in enumerate(node.selection_priors):
        visit_count = node.visit_counts[index]
        if visit_count > 0:
            q_value = node.value_sums[index] / visit_count
            normalized_q_value = min_max_stats.normalize(q_value)
        else:
            normalized_q_value = 1.0
        exploration = config.c_puct * prior * math.sqrt(total_visits + 1.0) / (visit_count + 1.0)
        score = normalized_q_value + exploration
        if score > best_score:
            best_score = score
            best_index = index
    return best_index


def _backup_zero_sum(
    search_path: list[tuple[MctsNode, int]],
    path_players: list[str],
    leaf_value: float,
    leaf_player: str,
    min_max_stats: MinMaxStats,
) -> None:
    downstream_player = leaf_player
    value = leaf_value
    for (node, action_index), node_player in zip(reversed(search_path), reversed(path_players)):
        if node_player != downstream_player:
            value = -value
        node.visit_counts[action_index] += 1
        node.value_sums[action_index] += value
        q_value = node.value_sums[action_index] / node.visit_counts[action_index]
        min_max_stats.update(q_value)
        downstream_player = node_player


def run_mcts(
    env: Any,
    attacker_model: torch.nn.Module,
    defender_model: torch.nn.Module,
    config: MctsConfig,
    *,
    add_root_noise: bool,
) -> MctsSearchResult:
    if config.simulations <= 0:
        raise ValueError("MCTS simulations must be positive")
    if env.is_terminal():
        raise ValueError("run_mcts cannot start from a terminal state")

    root_state_features = env.encode_state()
    root_legal_action_features = env.encode_legal_actions()
    root_actions = env.legal_actions()
    root_player = env.current_nation()

    root = MctsNode(player_to_move=root_player)
    min_max_stats = MinMaxStats()
    root_value = _expand_node(
        root,
        env,
        attacker_model,
        defender_model,
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
        path_players: list[str] = []

        while True:
            if simulation_env.is_terminal():
                if not search_path:
                    raise ValueError("Encountered terminal root in MCTS simulation")
                leaf_player = path_players[-1]
                leaf_value = float(simulation_env.terminal_reward_for(leaf_player))
                break
            if not node.expanded:
                leaf_player = simulation_env.current_nation()
                leaf_value = _expand_node(node, simulation_env, attacker_model, defender_model)
                break
            if not node.actions:
                if not search_path:
                    raise ValueError("Expanded root had no actions")
                leaf_player = path_players[-1]
                leaf_value = float(simulation_env.terminal_reward_for(leaf_player))
                break

            action_index = _select_child_index(node, config, min_max_stats)
            search_path.append((node, action_index))
            path_players.append(node.player_to_move)
            simulation_env.step(node.actions[action_index])

            child = node.children[action_index]
            if child is None:
                child = MctsNode()
                node.children[action_index] = child
            node = child

        _backup_zero_sum(search_path, path_players, leaf_value, leaf_player, min_max_stats)

    total_visits = sum(root.visit_counts)
    if total_visits == 0:
        policy = root.priors.copy()
    else:
        policy = [visit_count / total_visits for visit_count in root.visit_counts]
    action_values = [
        value_sum / visit_count if visit_count > 0 else 0.0
        for value_sum, visit_count in zip(root.value_sums, root.visit_counts)
    ]
    normalized_q_values: list[float] = []
    exploration_terms: list[float] = []
    action_scores: list[float] = []
    for index, prior in enumerate(root.selection_priors):
        visit_count = root.visit_counts[index]
        if visit_count > 0:
            normalized_q_value = min_max_stats.normalize(action_values[index])
        else:
            normalized_q_value = 1.0
        exploration = config.c_puct * prior * math.sqrt(total_visits + 1.0) / (visit_count + 1.0)
        normalized_q_values.append(normalized_q_value)
        exploration_terms.append(exploration)
        action_scores.append(normalized_q_value + exploration)
    q_min = min_max_stats.minimum if math.isfinite(min_max_stats.minimum) else 0.0
    q_max = min_max_stats.maximum if math.isfinite(min_max_stats.maximum) else 0.0
    return MctsSearchResult(
        player_to_move=root_player,
        state_features=root_state_features,
        legal_action_features=root_legal_action_features,
        actions=root_actions,
        visit_counts=root.visit_counts,
        policy=policy,
        priors=root.priors,
        root_value=root_value,
        action_values=action_values,
        normalized_q_values=normalized_q_values,
        exploration_terms=exploration_terms,
        action_scores=action_scores,
        q_min=q_min,
        q_max=q_max,
    )


def select_action_index_from_policy(policy: list[float], temperature: float) -> int:
    if not policy:
        raise ValueError("Cannot select from an empty policy")
    if temperature <= 0.0:
        return max(range(len(policy)), key=lambda index: policy[index])

    policy_tensor = torch.tensor(policy, dtype=torch.float32)
    powered = torch.pow(policy_tensor.clamp_min(1e-8), 1.0 / temperature)
    probabilities = powered / powered.sum()
    return int(Categorical(probs=probabilities).sample().item())
