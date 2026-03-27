from __future__ import annotations

import argparse
import json
import random
import sys
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch.distributions import Categorical

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from japan_mcts import MctsConfig, run_mcts, select_action_index_from_policy, tensorize_state_and_actions
from policy_value_model import LegalActionPolicyValueNet, PolicyValueModelConfig

try:
    import gwrl_cpp
except ImportError as exc:  # pragma: no cover - import failure should be obvious to the user
    raise SystemExit(
        "Unable to import gwrl_cpp. Build/install the extension first with "
        "`./.venv/bin/python -m pip install -e .`."
    ) from exc


@dataclass(slots=True)
class TrainingConfig:
    episodes: int = 800
    eval_every: int = 5
    learning_rate: float = 0.001
    state_hidden_dim: int = 128
    action_hidden_dim: int = 64
    joint_hidden_dim: int = 128
    search_simulations: int = 64
    c_puct: float = 1.5
    root_dirichlet_alpha: float = 0.3
    root_dirichlet_epsilon: float = 0.25
    self_play_temperature: float = 0.75
    value_loss_coef: float = 0.25
    entropy_coef: float = 0.001
    grad_clip_norm: float = 5.0
    replay_buffer_capacity: int = 4096
    replay_batch_size: int = 64
    replay_updates_per_episode: int = 4
    min_replay_size: int = 32
    seed: int = 1936


@dataclass(slots=True)
class ReplayExample:
    state_features: list[float]
    legal_action_features: list[list[float]]
    target_policy: list[float]
    target_value: float


def evaluation_checkpoint_payload(episode: int, evaluation: dict[str, Any]) -> dict[str, float]:
    return {
        "episode": float(episode),
        "final_reward": float(evaluation["final_reward"]),
        "japan_income": float(evaluation["japan_income"]),
        "japan_units": float(evaluation["japan_units"]),
        "japan_unit_value": float(evaluation["japan_unit_value"]),
        "destroyed_enemy_unit_value": float(evaluation["destroyed_enemy_unit_value"]),
    }


def build_first_decision_after_declaration_snapshot(
    env: gwrl_cpp.JapanTrainingEnv,
) -> tuple[list[float], list[list[float]], list[gwrl_cpp.Action]]:
    env.reset()
    legal_actions = env.legal_actions()
    declare_war = next(
        action for action in legal_actions if action.kind == gwrl_cpp.ActionKind.DeclareWarOnChina
    )
    env.step(declare_war)
    if env.is_terminal():
        raise RuntimeError("Game ended before Japan combat state")
    return env.encode_state(), env.encode_legal_actions(), env.legal_actions()


def verify_against_cpp_example(env: gwrl_cpp.JapanTrainingEnv, example_path: Path) -> dict[str, Any]:
    with example_path.open("r", encoding="utf-8") as handle:
        exported = json.load(handle)

    state_features, legal_action_features, legal_actions = build_first_decision_after_declaration_snapshot(env)
    state_labels = env.state_feature_labels()
    action_labels = env.action_feature_labels()

    ok = True
    messages: list[str] = []
    if exported.get("state_feature_labels") != state_labels:
        ok = False
        messages.append("state feature labels do not match C++ export")
    if exported.get("action_feature_labels") != action_labels:
        ok = False
        messages.append("action feature labels do not match C++ export")
    if exported.get("state_features") != state_features:
        ok = False
        messages.append("state feature values do not match C++ export")

    exported_action_map = {
        entry["description"]: entry["action_features"] for entry in exported.get("legal_actions", [])
    }
    python_action_map = {
        action.describe(): legal_action_features[index] for index, action in enumerate(legal_actions)
    }
    if exported_action_map != python_action_map:
        ok = False
        messages.append("legal action encodings do not match C++ export")

    return {
        "ok": ok,
        "messages": messages,
        "checked_file": str(example_path),
    }


def run_search_episode(
    env: gwrl_cpp.JapanTrainingEnv,
    model: LegalActionPolicyValueNet,
    mcts_config: MctsConfig,
) -> dict[str, Any]:
    env.reset()
    trace: list[str] = []
    search_tables: list[dict[str, Any]] = []

    while not env.is_terminal():
        search = run_mcts(env, model, mcts_config, add_root_noise=False)
        action_index = select_action_index_from_policy(search.policy, temperature=0.0)
        action = search.actions[action_index]
        acting_turn = env.completed_turns_for("Japan") + 1
        decision_label = f"Japan turn {acting_turn} / {env.current_phase()}"
        action_summary = summarize_search_root(search)
        chosen_entry = next(entry for entry in action_summary if entry["action"] == action.describe())
        search_tables.append(
            {
                "decision": decision_label,
                "chosen_action": action.describe(),
                "chosen_search_probability": chosen_entry["search_probability"],
                "chosen_prior_probability": chosen_entry["prior_probability"],
                "chosen_visits": chosen_entry["visits"],
                "chosen_action_value": chosen_entry["action_value"],
                "actions": action_summary,
            }
        )
        action_visits = search.visit_counts[action_index]
        action_value = search.action_values[action_index]
        trace.append(
            f"{decision_label} -> "
            f"{action.describe()} (search_value={action_value:.4f}, visits={action_visits})"
        )
        step_result = env.step(action)
        for detail in step_result.detail_lines:
            trace.append(f"    {detail}")

    return {
        "final_reward": env.final_reward(),
        "japan_income": env.nation_income("Japan"),
        "japan_units": env.unit_count_for("Japan"),
        "japan_unit_value": env.unit_value_for("Japan"),
        "destroyed_enemy_unit_value": env.enemy_unit_value_destroyed_by_nation("Japan"),
        "trace": trace,
        "search_tables": search_tables,
    }


def summarize_search_root(search: Any) -> list[dict[str, Any]]:
    entries = [
        {
            "action": action.describe(),
            "search_probability": float(search.policy[index]),
            "prior_probability": float(search.priors[index]),
            "visits": int(search.visit_counts[index]),
            "action_value": float(search.action_values[index]),
        }
        for index, action in enumerate(search.actions)
    ]
    entries.sort(key=lambda item: item["search_probability"], reverse=True)
    return entries


def compute_replay_batch_losses(
    model: LegalActionPolicyValueNet,
    batch: list[ReplayExample],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    policy_losses: list[torch.Tensor] = []
    value_losses: list[torch.Tensor] = []
    entropies: list[torch.Tensor] = []

    for example in batch:
        state_tensor, action_tensor = tensorize_state_and_actions(
            example.state_features,
            example.legal_action_features,
        )
        target_policy_tensor = torch.tensor(example.target_policy, dtype=torch.float32).unsqueeze(0)
        target_value_tensor = torch.tensor([example.target_value], dtype=torch.float32)
        logits, value = model(state_tensor, action_tensor)
        log_probs = torch.log_softmax(logits, dim=-1)
        policy_losses.append(-(target_policy_tensor * log_probs).sum(dim=-1).mean())
        value_losses.append(F.mse_loss(value, target_value_tensor))
        entropies.append(Categorical(logits=logits.squeeze(0)).entropy())

    return (
        torch.stack(policy_losses).mean(),
        torch.stack(value_losses).mean(),
        torch.stack(entropies).mean(),
    )


def snapshot_first_decision_policy(
    env: gwrl_cpp.JapanTrainingEnv,
    model: LegalActionPolicyValueNet,
    mcts_config: MctsConfig,
) -> list[dict[str, Any]]:
    env.reset()
    declare_war = next(
        action for action in env.legal_actions() if action.kind == gwrl_cpp.ActionKind.DeclareWarOnChina
    )
    env.step(declare_war)
    search = run_mcts(env, model, mcts_config, add_root_noise=False)
    return summarize_search_root(search)


def write_search_evaluation_svg(evaluations: list[dict[str, float]], output_path: Path) -> None:
    width = 960
    height = 540
    margin_left = 70
    margin_right = 30
    margin_top = 40
    margin_bottom = 60

    if not evaluations:
        output_path.write_text(
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
                '<rect width="100%" height="100%" fill="#fffaf2"/>'
                '<text x="50%" y="50%" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
                'font-size="22" fill="#444">No evaluation points recorded</text>'
                "</svg>"
            ),
            encoding="utf-8",
        )
        return

    episodes = [entry["episode"] for entry in evaluations]
    rewards = [entry["final_reward"] for entry in evaluations]
    min_episode = min(episodes)
    max_episode = max(episodes)
    min_reward = min(rewards)
    max_reward = max(rewards)

    if max_episode == min_episode:
        max_episode += 1
    if max_reward == min_reward:
        min_reward -= 1.0
        max_reward += 1.0

    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    def x_pos(episode: float) -> float:
        return margin_left + (episode - min_episode) / (max_episode - min_episode) * plot_width

    def y_pos(reward: float) -> float:
        return margin_top + (max_reward - reward) / (max_reward - min_reward) * plot_height

    polyline_points = " ".join(
        f"{x_pos(entry['episode']):.1f},{y_pos(entry['final_reward']):.1f}"
        for entry in evaluations
    )

    y_ticks = 5
    x_ticks = min(6, len(evaluations))
    x_tick_values = [
        min_episode + (max_episode - min_episode) * tick / max(1, x_ticks - 1)
        for tick in range(x_ticks)
    ]
    y_tick_values = [
        min_reward + (max_reward - min_reward) * tick / max(1, y_ticks - 1)
        for tick in range(y_ticks)
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#fffaf2"/>',
        '<text x="50%" y="28" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
        'font-size="24" font-weight="700" fill="#2b2b2b">Deterministic Search Reward Over Training</text>',
        f'<line x1="{margin_left}" y1="{height - margin_bottom}" '
        f'x2="{width - margin_right}" y2="{height - margin_bottom}" stroke="#666" stroke-width="2"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" '
        f'x2="{margin_left}" y2="{height - margin_bottom}" stroke="#666" stroke-width="2"/>',
    ]

    for tick_value in x_tick_values:
        x = x_pos(tick_value)
        parts.append(
            f'<line x1="{x:.1f}" y1="{margin_top}" x2="{x:.1f}" y2="{height - margin_bottom}" '
            'stroke="#e6dccb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{height - margin_bottom + 22}" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#555">'
            f'{int(round(tick_value))}</text>'
        )

    for tick_value in y_tick_values:
        y = y_pos(tick_value)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" '
            'stroke="#e6dccb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin_left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            'font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#555">'
            f'{tick_value:.2f}</text>'
        )

    parts.append(
        f'<polyline fill="none" stroke="#0f766e" stroke-width="3" points="{polyline_points}"/>'
    )
    for entry in evaluations:
        x = x_pos(entry["episode"])
        y = y_pos(entry["final_reward"])
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#115e59" stroke="#ffffff" stroke-width="1.5"/>'
        )

    parts.extend(
        [
            f'<text x="{margin_left + plot_width / 2:.1f}" y="{height - 15}" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#444">Episode</text>',
            f'<text x="18" y="{margin_top + plot_height / 2:.1f}" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#444" '
            f'transform="rotate(-90 18 {margin_top + plot_height / 2:.1f})">Final reward</text>',
            "</svg>",
        ]
    )
    output_path.write_text("\n".join(parts), encoding="utf-8")


def write_first_purchase_series_svg(
    snapshots: list[dict[str, Any]],
    output_path: Path,
    value_key: str,
    title: str,
    y_label: str,
) -> None:
    width = 1100
    height = 620
    margin_left = 80
    margin_right = 170
    margin_top = 50
    margin_bottom = 70

    if not snapshots:
        output_path.write_text(
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
                '<rect width="100%" height="100%" fill="#fffaf2"/>'
                '<text x="50%" y="50%" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
                f'font-size="22" fill="#444">No data recorded for {title}</text>'
                "</svg>"
            ),
            encoding="utf-8",
        )
        return

    series_order = [
        ("purchase_unit(count=1, unit=Infantry)", "Infantry", "#2563eb"),
        ("purchase_unit(count=1, unit=Artillery)", "Artillery", "#dc2626"),
        ("purchase_unit(count=1, unit=Fighter)", "Fighter", "#16a34a"),
        ("end_phase", "End phase", "#7c3aed"),
    ]
    snapshots_by_episode = {int(snapshot["episode"]): snapshot for snapshot in snapshots}
    episodes = sorted(snapshots_by_episode)
    action_series: dict[str, list[tuple[int, float]]] = {key: [] for key, _, _ in series_order}
    all_values: list[float] = []

    for episode in episodes:
        action_map = {
            entry["action"]: float(entry[value_key])
            for entry in snapshots_by_episode[episode]["actions"]
        }
        for action_key, _, _ in series_order:
            value = action_map.get(action_key, 0.0)
            action_series[action_key].append((episode, value))
            all_values.append(value)

    min_episode = min(episodes)
    max_episode = max(episodes)
    min_value = min(all_values)
    max_value = max(all_values)

    if max_episode == min_episode:
        max_episode += 1
    if max_value == min_value:
        min_value -= 1.0
        max_value += 1.0

    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    def x_pos(episode: int) -> float:
        return margin_left + (episode - min_episode) / (max_episode - min_episode) * plot_width

    def y_pos(value: float) -> float:
        return margin_top + (max_value - value) / (max_value - min_value) * plot_height

    x_ticks = min(6, len(episodes))
    y_ticks = 6
    x_tick_values = [
        min_episode + (max_episode - min_episode) * tick / max(1, x_ticks - 1)
        for tick in range(x_ticks)
    ]
    y_tick_values = [
        min_value + (max_value - min_value) * tick / max(1, y_ticks - 1)
        for tick in range(y_ticks)
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#fffaf2"/>',
        '<text x="50%" y="30" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="24" font-weight="700" fill="#2b2b2b">{title}</text>',
        f'<line x1="{margin_left}" y1="{height - margin_bottom}" '
        f'x2="{width - margin_right}" y2="{height - margin_bottom}" stroke="#666" stroke-width="2"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" '
        f'x2="{margin_left}" y2="{height - margin_bottom}" stroke="#666" stroke-width="2"/>',
    ]

    for tick_value in x_tick_values:
        x = x_pos(int(round(tick_value)))
        parts.append(
            f'<line x1="{x:.1f}" y1="{margin_top}" x2="{x:.1f}" y2="{height - margin_bottom}" '
            'stroke="#e6dccb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{height - margin_bottom + 22}" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#555">'
            f'{int(round(tick_value))}</text>'
        )

    for tick_value in y_tick_values:
        y = y_pos(tick_value)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" '
            'stroke="#e6dccb" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{margin_left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            'font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#555">'
            f'{tick_value:.2f}</text>'
        )

    legend_x = width - margin_right + 25
    legend_y = margin_top + 20
    for index, (action_key, label, color) in enumerate(series_order):
        points = action_series[action_key]
        polyline_points = " ".join(f"{x_pos(ep):.1f},{y_pos(val):.1f}" for ep, val in points)
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{polyline_points}"/>'
        )
        for episode, value in points:
            parts.append(
                f'<circle cx="{x_pos(episode):.1f}" cy="{y_pos(value):.1f}" r="3.5" '
                f'fill="{color}" stroke="#ffffff" stroke-width="1"/>'
            )
        legend_entry_y = legend_y + index * 28
        parts.append(
            f'<line x1="{legend_x}" y1="{legend_entry_y}" x2="{legend_x + 20}" y2="{legend_entry_y}" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        parts.append(
            f'<text x="{legend_x + 28}" y="{legend_entry_y + 4}" '
            'font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#333">'
            f'{label}</text>'
        )

    parts.extend(
        [
            f'<text x="{margin_left + plot_width / 2:.1f}" y="{height - 18}" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#444">Episode</text>',
            f'<text x="24" y="{margin_top + plot_height / 2:.1f}" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#444" '
            f'transform="rotate(-90 24 {margin_top + plot_height / 2:.1f})">{y_label}</text>',
            "</svg>",
        ]
    )
    output_path.write_text("\n".join(parts), encoding="utf-8")


def write_first_purchase_action_value_svg(
    snapshots: list[dict[str, Any]],
    output_path: Path,
) -> None:
    write_first_purchase_series_svg(
        snapshots,
        output_path,
        value_key="action_value",
        title="First Purchase Action Values Over Training",
        y_label="Root action value",
    )


def write_first_purchase_prior_svg(
    snapshots: list[dict[str, Any]],
    output_path: Path,
) -> None:
    write_first_purchase_series_svg(
        snapshots,
        output_path,
        value_key="prior_probability",
        title="First Purchase Priors Over Training",
        y_label="Prior probability",
    )


def train(config: TrainingConfig, scenario_path: Path) -> dict[str, Any]:
    if config.replay_buffer_capacity <= 0:
        raise ValueError("Replay buffer capacity must be positive")
    if config.replay_batch_size <= 0:
        raise ValueError("Replay batch size must be positive")
    if config.replay_updates_per_episode <= 0:
        raise ValueError("Replay updates per episode must be positive")
    if config.min_replay_size <= 0:
        raise ValueError("Minimum replay size must be positive")

    torch.manual_seed(config.seed)
    random_generator = random.Random(config.seed)
    env = gwrl_cpp.JapanTrainingEnv(str(scenario_path), "Japan")
    state_dim = len(env.state_feature_labels())
    action_dim = len(env.action_feature_labels())
    mcts_config = MctsConfig(
        simulations=config.search_simulations,
        c_puct=config.c_puct,
        root_dirichlet_alpha=config.root_dirichlet_alpha,
        root_dirichlet_epsilon=config.root_dirichlet_epsilon,
        self_play_temperature=config.self_play_temperature,
    )

    model = LegalActionPolicyValueNet(
        PolicyValueModelConfig(
            state_dim=state_dim,
            action_dim=action_dim,
            state_hidden_dim=config.state_hidden_dim,
            action_hidden_dim=config.action_hidden_dim,
            joint_hidden_dim=config.joint_hidden_dim,
        )
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)

    history: list[dict[str, float]] = []
    evaluation_history: list[dict[str, float]] = []
    first_purchase_history: list[dict[str, Any]] = []
    replay_buffer: deque[ReplayExample] = deque(maxlen=config.replay_buffer_capacity)
    best_search_evaluation: dict[str, Any] | None = None
    best_search_evaluation_episode: int | None = None
    best_self_play_episode: dict[str, Any] | None = None
    best_self_play_episode_index: int | None = None

    for episode_index in range(config.episodes):
        env.reset()
        search_examples: list[tuple[list[float], list[list[float]], list[float]]] = []
        episode_trace: list[str] = []
        episode_search_tables: list[dict[str, Any]] = []

        while not env.is_terminal():
            search = run_mcts(env, model, mcts_config, add_root_noise=True)
            action_index = select_action_index_from_policy(
                search.policy,
                temperature=config.self_play_temperature,
            )
            action = search.actions[action_index]
            acting_turn = env.completed_turns_for("Japan") + 1
            decision_label = f"Japan turn {acting_turn} / {env.current_phase()}"
            action_summary = summarize_search_root(search)
            chosen_entry = next(entry for entry in action_summary if entry["action"] == action.describe())
            episode_search_tables.append(
                {
                    "decision": decision_label,
                    "chosen_action": action.describe(),
                    "chosen_search_probability": chosen_entry["search_probability"],
                    "chosen_prior_probability": chosen_entry["prior_probability"],
                    "chosen_visits": chosen_entry["visits"],
                    "chosen_action_value": chosen_entry["action_value"],
                    "actions": action_summary,
                }
            )
            episode_trace.append(
                f"{decision_label} -> {action.describe()} "
                f"(search_prob={chosen_entry['search_probability']:.4f}, "
                f"prior={chosen_entry['prior_probability']:.4f}, "
                f"visits={chosen_entry['visits']}, "
                f"action_value={chosen_entry['action_value']:.4f})"
            )
            step_result = env.step(action)
            for detail in step_result.detail_lines:
                episode_trace.append(f"    {detail}")
            search_examples.append(
                (
                    search.state_features,
                    search.legal_action_features,
                    search.policy,
                )
            )

            if env.is_terminal():
                final_reward = float(env.final_reward())
                break
        else:
            final_reward = float(env.final_reward())

        if not search_examples:
            raise RuntimeError("Encountered an episode with no tracked-nation decisions")

        for state_features, legal_action_features, target_policy in search_examples:
            replay_buffer.append(
                ReplayExample(
                    state_features=state_features,
                    legal_action_features=legal_action_features,
                    target_policy=target_policy,
                    target_value=final_reward,
                )
            )

        replay_batch_size = min(config.replay_batch_size, len(replay_buffer))
        updates_this_episode = (
            config.replay_updates_per_episode
            if len(replay_buffer) >= config.min_replay_size
            else 1
        )

        batch_loss_values: list[float] = []
        batch_policy_loss_values: list[float] = []
        batch_value_loss_values: list[float] = []
        batch_entropy_values: list[float] = []
        batch_grad_norm_values: list[float] = []

        for _ in range(updates_this_episode):
            sampled_batch = random_generator.sample(list(replay_buffer), replay_batch_size)
            policy_loss, value_loss, entropy_bonus = compute_replay_batch_losses(model, sampled_batch)
            loss = policy_loss + config.value_loss_coef * value_loss - config.entropy_coef * entropy_bonus

            optimizer.zero_grad()
            loss.backward()
            grad_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip_norm))
            optimizer.step()

            batch_loss_values.append(float(loss.item()))
            batch_policy_loss_values.append(float(policy_loss.item()))
            batch_value_loss_values.append(float(value_loss.item()))
            batch_entropy_values.append(float(entropy_bonus.item()))
            batch_grad_norm_values.append(grad_norm)

        loss_value = sum(batch_loss_values) / len(batch_loss_values)
        policy_loss_value = sum(batch_policy_loss_values) / len(batch_policy_loss_values)
        value_loss_value = sum(batch_value_loss_values) / len(batch_value_loss_values)
        entropy_value = sum(batch_entropy_values) / len(batch_entropy_values)
        grad_norm_value = sum(batch_grad_norm_values) / len(batch_grad_norm_values)

        history.append(
            {
                "episode": float(episode_index),
                "reward": final_reward,
                "japan_income": float(env.nation_income("Japan")),
                "japan_units": float(env.unit_count_for("Japan")),
                "japan_unit_value": float(env.unit_value_for("Japan")),
                "destroyed_enemy_unit_value": float(env.enemy_unit_value_destroyed_by_nation("Japan")),
                "japan_decisions": float(len(search_examples)),
                "loss": loss_value,
                "policy_loss": policy_loss_value,
                "value_loss": value_loss_value,
                "entropy": entropy_value,
                "gradient_norm": grad_norm_value,
                "replay_buffer_size": float(len(replay_buffer)),
                "replay_updates": float(updates_this_episode),
            }
        )
        if best_self_play_episode is None or final_reward > float(best_self_play_episode["final_reward"]):
            best_self_play_episode = {
                "final_reward": final_reward,
                "japan_income": int(env.nation_income("Japan")),
                "japan_units": int(env.unit_count_for("Japan")),
                "japan_unit_value": int(env.unit_value_for("Japan")),
                "destroyed_enemy_unit_value": int(env.enemy_unit_value_destroyed_by_nation("Japan")),
                "trace": list(episode_trace),
                "search_tables": list(episode_search_tables),
            }
            best_self_play_episode_index = episode_index + 1
        first_purchase_history.append(
            {
                "episode": episode_index + 1,
                "actions": snapshot_first_decision_policy(env, model, mcts_config),
            }
        )

        should_evaluate = (
            (episode_index + 1) % config.eval_every == 0
            or episode_index == config.episodes - 1
        )
        if should_evaluate:
            evaluation = run_search_episode(env, model, mcts_config)
            evaluation_history.append(evaluation_checkpoint_payload(episode_index + 1, evaluation))
            if (
                best_search_evaluation is None
                or float(evaluation["final_reward"]) > float(best_search_evaluation["final_reward"])
            ):
                best_search_evaluation = {
                    "final_reward": float(evaluation["final_reward"]),
                    "japan_income": int(evaluation["japan_income"]),
                    "japan_units": int(evaluation["japan_units"]),
                    "japan_unit_value": int(evaluation["japan_unit_value"]),
                    "destroyed_enemy_unit_value": int(evaluation["destroyed_enemy_unit_value"]),
                    "trace": list(evaluation["trace"]),
                    "search_tables": list(evaluation["search_tables"]),
                }
                best_search_evaluation_episode = episode_index + 1

    verification: dict[str, Any] | None = None
    cpp_example_path = Path("output/japan_training_example.json")
    if cpp_example_path.exists():
        verification = verify_against_cpp_example(env, cpp_example_path)

    state_features, legal_action_features, _ = build_first_decision_after_declaration_snapshot(env)
    env.reset()
    declare_war = next(
        action for action in env.legal_actions() if action.kind == gwrl_cpp.ActionKind.DeclareWarOnChina
    )
    env.step(declare_war)
    first_decision_search = run_mcts(env, model, mcts_config, add_root_noise=False)
    first_decision_policy = [
        {
            "action": action.describe(),
            "search_probability": float(first_decision_search.policy[index]),
            "prior_probability": float(first_decision_search.priors[index]),
            "visits": int(first_decision_search.visit_counts[index]),
            "action_value": float(first_decision_search.action_values[index]),
        }
        for index, action in enumerate(first_decision_search.actions)
    ]
    first_decision_policy.sort(key=lambda item: item["search_probability"], reverse=True)

    search_evaluation = run_search_episode(env, model, mcts_config)
    return {
        "config": asdict(config),
        "state_dim": state_dim,
        "action_dim": action_dim,
        "history": history,
        "evaluation_history": evaluation_history,
        "first_purchase_history": first_purchase_history,
        "best_self_play_episode": best_self_play_episode,
        "best_self_play_episode_index": best_self_play_episode_index,
        "best_search_evaluation": best_search_evaluation,
        "best_search_evaluation_episode": best_search_evaluation_episode,
        "first_decision_policy": first_decision_policy,
        "search_evaluation": search_evaluation,
        "verification": verification,
        "model": model,
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    history = result["history"]
    evaluation_history = result["evaluation_history"]
    recent_window = history[-20:] if len(history) >= 20 else history
    recent_average_self_play_reward = (
        sum(item["reward"] for item in recent_window) / len(recent_window)
        if recent_window
        else 0.0
    )
    best_search_evaluation = (
        max(evaluation_history, key=lambda entry: entry["final_reward"])
        if evaluation_history
        else None
    )
    best_self_play_episode = result.get("best_self_play_episode")
    best_self_play_episode_index = result.get("best_self_play_episode_index")
    best_search_trace = result.get("best_search_evaluation")
    best_search_trace_episode = result.get("best_search_evaluation_episode")

    lines = [
        "Japan Torch training summary",
        f"episodes={int(result['config']['episodes'])}",
        f"state_dim={result['state_dim']}",
        f"action_dim={result['action_dim']}",
        "note=self_play_rewards_are_stochastic_training_episodes; "
        "search_evaluation_is_the_current_deterministic_policy",
        f"recent_average_self_play_reward={recent_average_self_play_reward:.4f}",
    ]
    lines.append("")
    lines.append("Training config")
    for key, value in result["config"].items():
        lines.append(f"- {key}={value}")
    if history:
        last = history[-1]
        lines.extend(
            [
                f"last_self_play_reward={last['reward']:.4f}",
                f"last_self_play_japan_income={int(last['japan_income'])}",
                f"last_self_play_japan_units={int(last['japan_units'])}",
                f"last_self_play_japan_unit_value={int(last['japan_unit_value'])}",
                f"last_self_play_destroyed_enemy_unit_value={int(last['destroyed_enemy_unit_value'])}",
                f"last_training_loss={last['loss']:.4f}",
                f"last_gradient_norm={last['gradient_norm']:.4f}",
                f"last_replay_buffer_size={int(last['replay_buffer_size'])}",
                f"last_replay_updates={int(last['replay_updates'])}",
            ]
        )
    if best_search_evaluation is not None:
        lines.extend(
            [
                f"best_search_evaluation_reward={best_search_evaluation['final_reward']:.4f}",
                f"best_search_evaluation_episode={int(best_search_evaluation['episode'])}",
            ]
        )
    if best_self_play_episode is not None and best_self_play_episode_index is not None:
        lines.extend(
            [
                f"best_self_play_reward={best_self_play_episode['final_reward']:.4f}",
                f"best_self_play_episode={int(best_self_play_episode_index)}",
            ]
        )

    verification = result.get("verification")
    if verification is not None:
        lines.append(
            f"encoder_match_with_cpp_export={'yes' if verification['ok'] else 'no'}"
        )
        for message in verification["messages"]:
            lines.append(f"verification_note={message}")

    if evaluation_history:
        lines.append("")
        lines.append("Search evaluation checkpoints")
        for entry in evaluation_history:
            lines.append(
                f"- episode={int(entry['episode'])} reward={entry['final_reward']:.4f} "
                f"income={int(entry['japan_income'])} units={int(entry['japan_units'])} "
                f"unit_value={int(entry['japan_unit_value'])} "
                f"destroyed_enemy_unit_value={int(entry['destroyed_enemy_unit_value'])}"
            )

    lines.append("")
    lines.append("First decision after declaration")
    for entry in result["first_decision_policy"]:
        lines.append(
            f"- {entry['action']}: "
            f"search_prob={entry['search_probability']:.4f} "
            f"prior={entry['prior_probability']:.4f} "
            f"visits={entry['visits']} "
            f"action_value={entry['action_value']:.4f}"
        )

    lines.append("")
    lines.append("Current deterministic search evaluation")
    lines.append(f"- reward={result['search_evaluation']['final_reward']:.4f}")
    lines.append(f"- japan_income={result['search_evaluation']['japan_income']}")
    lines.append(f"- japan_units={result['search_evaluation']['japan_units']}")
    lines.append(f"- japan_unit_value={result['search_evaluation']['japan_unit_value']}")
    lines.append(
        f"- destroyed_enemy_unit_value={result['search_evaluation']['destroyed_enemy_unit_value']}"
    )
    lines.extend(result["search_evaluation"]["trace"])

    detail_files: list[str] = []
    if best_self_play_episode is not None and best_self_play_episode_index is not None:
        detail_files.append("- best self-play episode trace: output/best_self_play_episode_trace.txt")
    if best_search_trace is not None and best_search_trace_episode is not None:
        detail_files.append(
            "- best deterministic checkpoint trace: output/best_deterministic_checkpoint_trace.txt"
        )
    if detail_files:
        lines.append("")
        lines.append("Detailed trace files")
        lines.extend(detail_files)

    (output_dir / "japan_torch_training_summary.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    metrics_payload = {
        "config": result["config"],
        "state_dim": result["state_dim"],
        "action_dim": result["action_dim"],
        "history": result["history"],
        "evaluation_history": result["evaluation_history"],
        "first_purchase_history": result["first_purchase_history"],
        "best_self_play_episode": result["best_self_play_episode"],
        "best_self_play_episode_index": result["best_self_play_episode_index"],
        "best_search_evaluation": result["best_search_evaluation"],
        "best_search_evaluation_episode": result["best_search_evaluation_episode"],
        "first_decision_policy": result["first_decision_policy"],
        "search_evaluation": result["search_evaluation"],
        "verification": result["verification"],
    }
    (output_dir / "japan_torch_training_metrics.json").write_text(
        json.dumps(metrics_payload, indent=2),
        encoding="utf-8",
    )

    model: LegalActionPolicyValueNet = result["model"]
    torch.save(model.state_dict(), output_dir / "japan_torch_policy.pt")
    write_search_evaluation_svg(
        result["evaluation_history"],
        output_dir / "japan_search_reward_over_time.svg",
    )
    write_first_purchase_action_value_svg(
        result["first_purchase_history"],
        output_dir / "first_purchase_action_values_over_training.svg",
    )
    write_first_purchase_prior_svg(
        result["first_purchase_history"],
        output_dir / "first_purchase_priors_over_training.svg",
    )
    best_search_trace = result.get("best_search_evaluation")
    best_search_trace_episode = result.get("best_search_evaluation_episode")
    if best_search_trace is not None and best_search_trace_episode is not None:
        best_trace_lines = [
            "Best deterministic search evaluation",
            f"episode={int(best_search_trace_episode)}",
            f"reward={best_search_trace['final_reward']:.4f}",
            f"japan_income={best_search_trace['japan_income']}",
            f"japan_units={best_search_trace['japan_units']}",
            f"japan_unit_value={best_search_trace['japan_unit_value']}",
            f"destroyed_enemy_unit_value={best_search_trace['destroyed_enemy_unit_value']}",
            "",
        ]
        best_trace_lines.extend(best_search_trace["trace"])
        if best_search_trace.get("search_tables"):
            best_trace_lines.append("")
            best_trace_lines.append("Root search tables")
            for decision in best_search_trace["search_tables"]:
                best_trace_lines.append("")
                best_trace_lines.append(
                    f"{decision['decision']} -> chosen={decision['chosen_action']} "
                    f"(search_prob={decision['chosen_search_probability']:.4f}, "
                    f"prior={decision['chosen_prior_probability']:.4f}, "
                    f"visits={decision['chosen_visits']}, "
                    f"action_value={decision['chosen_action_value']:.4f})"
                )
                for action_entry in decision["actions"]:
                    best_trace_lines.append(
                        f"  - {action_entry['action']}: "
                        f"search_prob={action_entry['search_probability']:.4f} "
                        f"prior={action_entry['prior_probability']:.4f} "
                        f"visits={action_entry['visits']} "
                        f"action_value={action_entry['action_value']:.4f}"
                    )
        (output_dir / "best_deterministic_checkpoint_trace.txt").write_text(
            "\n".join(best_trace_lines) + "\n",
            encoding="utf-8",
        )
    if best_self_play_episode is not None and best_self_play_episode_index is not None:
        best_self_play_lines = [
            "Best self-play episode",
            f"episode={int(best_self_play_episode_index)}",
            f"reward={best_self_play_episode['final_reward']:.4f}",
            f"japan_income={best_self_play_episode['japan_income']}",
            f"japan_units={best_self_play_episode['japan_units']}",
            f"japan_unit_value={best_self_play_episode['japan_unit_value']}",
            f"destroyed_enemy_unit_value={best_self_play_episode['destroyed_enemy_unit_value']}",
            "",
            "Decision trace",
        ]
        best_self_play_lines.extend(best_self_play_episode["trace"])
        best_self_play_lines.append("")
        best_self_play_lines.append("Root search tables")
        for decision in best_self_play_episode["search_tables"]:
            best_self_play_lines.append("")
            best_self_play_lines.append(
                f"{decision['decision']} -> chosen={decision['chosen_action']} "
                f"(search_prob={decision['chosen_search_probability']:.4f}, "
                f"prior={decision['chosen_prior_probability']:.4f}, "
                f"visits={decision['chosen_visits']}, "
                f"action_value={decision['chosen_action_value']:.4f})"
            )
            for action_entry in decision["actions"]:
                best_self_play_lines.append(
                    f"  - {action_entry['action']}: "
                    f"search_prob={action_entry['search_probability']:.4f} "
                    f"prior={action_entry['prior_probability']:.4f} "
                    f"visits={action_entry['visits']} "
                    f"action_value={action_entry['action_value']:.4f}"
                )
        (output_dir / "best_self_play_episode_trace.txt").write_text(
            "\n".join(best_self_play_lines) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    defaults = TrainingConfig()
    parser = argparse.ArgumentParser(description="Train the Japan policy with PyTorch")
    parser.add_argument("--episodes", type=int, default=defaults.episodes)
    parser.add_argument("--scenario", type=Path, default=Path("data/china_simplified_setup.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--learning-rate", type=float, default=defaults.learning_rate)
    parser.add_argument("--state-hidden-dim", type=int, default=defaults.state_hidden_dim)
    parser.add_argument("--action-hidden-dim", type=int, default=defaults.action_hidden_dim)
    parser.add_argument("--joint-hidden-dim", type=int, default=defaults.joint_hidden_dim)
    parser.add_argument("--search-simulations", type=int, default=defaults.search_simulations)
    parser.add_argument("--eval-every", type=int, default=defaults.eval_every)
    parser.add_argument("--c-puct", type=float, default=defaults.c_puct)
    parser.add_argument("--root-dirichlet-alpha", type=float, default=defaults.root_dirichlet_alpha)
    parser.add_argument("--root-dirichlet-epsilon", type=float, default=defaults.root_dirichlet_epsilon)
    parser.add_argument("--self-play-temperature", type=float, default=defaults.self_play_temperature)
    parser.add_argument("--value-loss-coef", type=float, default=defaults.value_loss_coef)
    parser.add_argument("--entropy-coef", type=float, default=defaults.entropy_coef)
    parser.add_argument("--grad-clip-norm", type=float, default=defaults.grad_clip_norm)
    parser.add_argument("--replay-buffer-capacity", type=int, default=defaults.replay_buffer_capacity)
    parser.add_argument("--replay-batch-size", type=int, default=defaults.replay_batch_size)
    parser.add_argument(
        "--replay-updates-per-episode",
        type=int,
        default=defaults.replay_updates_per_episode,
    )
    parser.add_argument("--min-replay-size", type=int, default=defaults.min_replay_size)
    parser.add_argument("--seed", type=int, default=defaults.seed)
    args = parser.parse_args()

    config = TrainingConfig(
        episodes=args.episodes,
        eval_every=args.eval_every,
        learning_rate=args.learning_rate,
        state_hidden_dim=args.state_hidden_dim,
        action_hidden_dim=args.action_hidden_dim,
        joint_hidden_dim=args.joint_hidden_dim,
        search_simulations=args.search_simulations,
        c_puct=args.c_puct,
        root_dirichlet_alpha=args.root_dirichlet_alpha,
        root_dirichlet_epsilon=args.root_dirichlet_epsilon,
        self_play_temperature=args.self_play_temperature,
        value_loss_coef=args.value_loss_coef,
        entropy_coef=args.entropy_coef,
        grad_clip_norm=args.grad_clip_norm,
        replay_buffer_capacity=args.replay_buffer_capacity,
        replay_batch_size=args.replay_batch_size,
        replay_updates_per_episode=args.replay_updates_per_episode,
        min_replay_size=args.min_replay_size,
        seed=args.seed,
    )
    result = train(config, args.scenario)
    write_outputs(result, args.output_dir)

    history = result["history"]
    recent_window = history[-20:] if len(history) >= 20 else history
    recent_average_self_play_reward = (
        sum(item["reward"] for item in recent_window) / len(recent_window)
        if recent_window
        else 0.0
    )
    print("Japan Torch training complete")
    print(f"episodes={config.episodes}")
    print(f"state_dim={result['state_dim']}")
    print(f"action_dim={result['action_dim']}")
    print(f"recent_average_self_play_reward={recent_average_self_play_reward:.4f}")
    print(f"current_search_evaluation_reward={result['search_evaluation']['final_reward']:.4f}")
    if result["first_decision_policy"]:
        best = result["first_decision_policy"][0]
        print(
            "best_first_decision_action="
            f"{best['action']} search_prob={best['search_probability']:.4f}"
        )


if __name__ == "__main__":
    main()
