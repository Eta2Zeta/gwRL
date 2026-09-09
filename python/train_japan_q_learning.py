from __future__ import annotations

import argparse
import json
import random
import sys
from array import array
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import gwrl_cpp
except ImportError as exc:  # pragma: no cover - import failure should be obvious to the user
    raise SystemExit(
        "Unable to import gwrl_cpp. Build/install the extension first with "
        "`./.venv/bin/python -m pip install -e .`."
    ) from exc


@dataclass(slots=True)
class QLearningConfig:
    episodes: int = 5000
    eval_every: int = 100
    alpha: float = 0.2
    use_visit_based_alpha: bool = False
    gamma: float = 1.0
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay_episodes: int = 4000
    seed: int = 1936


def evaluation_checkpoint_payload(episode: int, evaluation: dict[str, Any]) -> dict[str, float]:
    return {
        "episode": float(episode),
        "final_reward": float(evaluation["final_reward"]),
        "japan_income": float(evaluation["japan_income"]),
        "japan_units": float(evaluation["japan_units"]),
        "japan_unit_value": float(evaluation["japan_unit_value"]),
        "destroyed_enemy_unit_value": float(evaluation["destroyed_enemy_unit_value"]),
    }


def write_reward_svg(evaluations: list[dict[str, float]], output_path: Path, title: str) -> None:
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
        f'font-size="24" font-weight="700" fill="#2b2b2b">{title}</text>',
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


def epsilon_for_episode(config: QLearningConfig, episode_index: int) -> float:
    if config.epsilon_decay_episodes <= 0:
        return config.epsilon_end
    progress = min(1.0, episode_index / config.epsilon_decay_episodes)
    return config.epsilon_start + (config.epsilon_end - config.epsilon_start) * progress


def state_key_from_features(state_features: list[float]) -> bytes:
    int_values = [int(round(value)) for value in state_features]
    return array("i", int_values).tobytes()


def legal_action_descriptions(actions: list[gwrl_cpp.Action]) -> list[str]:
    return [action.describe() for action in actions]


def choose_epsilon_greedy_action_index(
    state_key: bytes,
    legal_actions: list[gwrl_cpp.Action],
    q_table: dict[bytes, dict[str, float]],
    rng: random.Random,
    epsilon: float,
) -> int:
    if rng.random() < epsilon:
        return rng.randrange(len(legal_actions))

    state_qs = q_table[state_key]
    action_descriptions = legal_action_descriptions(legal_actions)
    q_values = [state_qs.get(description, 0.0) for description in action_descriptions]
    best_value = max(q_values)
    best_indices = [index for index, value in enumerate(q_values) if value == best_value]
    return rng.choice(best_indices)


def greedy_action_index(
    state_key: bytes,
    legal_actions: list[gwrl_cpp.Action],
    q_table: dict[bytes, dict[str, float]],
) -> int:
    state_qs = q_table[state_key]
    best_index = 0
    best_value = float("-inf")
    for index, action in enumerate(legal_actions):
        value = state_qs.get(action.describe(), 0.0)
        if value > best_value:
            best_value = value
            best_index = index
    return best_index


def snapshot_first_purchase_q_values(
    env: gwrl_cpp.JapanTrainingEnv,
    q_table: dict[bytes, dict[str, float]],
) -> list[dict[str, Any]]:
    env.reset()
    declare_war = next(
        action for action in env.legal_actions() if action.kind == gwrl_cpp.ActionKind.DeclareWarOnChina
    )
    env.step(declare_war)
    legal_actions = env.legal_actions()
    state_key = state_key_from_features(env.encode_state())
    state_qs = q_table[state_key]
    entries = [
        {
            "action": action.describe(),
            "q_value": float(state_qs.get(action.describe(), 0.0)),
        }
        for action in legal_actions
    ]
    entries.sort(key=lambda item: item["q_value"], reverse=True)
    return entries


def run_greedy_episode(
    env: gwrl_cpp.JapanTrainingEnv,
    q_table: dict[bytes, dict[str, float]],
) -> dict[str, Any]:
    env.reset()
    trace: list[str] = []
    q_tables: list[dict[str, Any]] = []

    while not env.is_terminal():
        state_key = state_key_from_features(env.encode_state())
        legal_actions = env.legal_actions()
        action_descriptions = legal_action_descriptions(legal_actions)
        state_qs = q_table[state_key]
        chosen_index = greedy_action_index(state_key, legal_actions, q_table)
        chosen_action = legal_actions[chosen_index]
        acting_turn = env.completed_turns_for("Japan") + 1
        decision_label = f"Japan turn {acting_turn} / {env.current_phase()}"
        action_entries = [
            {
                "action": description,
                "q_value": float(state_qs.get(description, 0.0)),
            }
            for description in action_descriptions
        ]
        action_entries.sort(key=lambda item: item["q_value"], reverse=True)
        chosen_q_value = float(state_qs.get(chosen_action.describe(), 0.0))
        q_tables.append(
            {
                "decision": decision_label,
                "chosen_action": chosen_action.describe(),
                "chosen_q_value": chosen_q_value,
                "actions": action_entries,
            }
        )
        trace.append(
            f"{decision_label} -> {chosen_action.describe()} "
            f"(q_value={chosen_q_value:.4f})"
        )
        step_result = env.step(chosen_action)
        for detail in step_result.detail_lines:
            trace.append(f"    {detail}")

    return {
        "final_reward": env.final_reward(),
        "japan_income": env.nation_income("Japan"),
        "japan_units": env.unit_count_for("Japan"),
        "japan_unit_value": env.unit_value_for("Japan"),
        "destroyed_enemy_unit_value": env.enemy_unit_value_destroyed_by_nation("Japan"),
        "trace": trace,
        "q_tables": q_tables,
    }


def train(config: QLearningConfig, scenario_path: Path) -> dict[str, Any]:
    if config.episodes <= 0:
        raise ValueError("Episode count must be positive")

    rng = random.Random(config.seed)
    env = gwrl_cpp.JapanTrainingEnv(str(scenario_path), "Japan")
    state_dim = len(env.state_feature_labels())
    action_dim = len(env.action_feature_labels())
    q_table: defaultdict[bytes, dict[str, float]] = defaultdict(dict)
    visit_counts: defaultdict[bytes, dict[str, int]] = defaultdict(dict)

    history: list[dict[str, float]] = []
    evaluation_history: list[dict[str, float]] = []
    best_self_play_episode: dict[str, Any] | None = None
    best_self_play_episode_index: int | None = None
    best_greedy_evaluation: dict[str, Any] | None = None
    best_greedy_evaluation_episode: int | None = None

    for episode_index in range(config.episodes):
        env.reset()
        epsilon = epsilon_for_episode(config, episode_index)
        episode_trace: list[str] = []
        episode_q_tables: list[dict[str, Any]] = []

        while not env.is_terminal():
            state_features = env.encode_state()
            state_key = state_key_from_features(state_features)
            legal_actions = env.legal_actions()
            action_descriptions = legal_action_descriptions(legal_actions)
            state_qs = q_table[state_key]
            action_index = choose_epsilon_greedy_action_index(
                state_key,
                legal_actions,
                q_table,
                rng,
                epsilon,
            )
            action = legal_actions[action_index]
            action_description = action.describe()
            acting_turn = env.completed_turns_for("Japan") + 1
            decision_label = f"Japan turn {acting_turn} / {env.current_phase()}"
            action_entries = [
                {
                    "action": description,
                    "q_value": float(state_qs.get(description, 0.0)),
                }
                for description in action_descriptions
            ]
            action_entries.sort(key=lambda item: item["q_value"], reverse=True)
            episode_q_tables.append(
                {
                    "decision": decision_label,
                    "chosen_action": action_description,
                    "chosen_q_value": float(state_qs.get(action_description, 0.0)),
                    "actions": action_entries,
                }
            )

            previous_score = float(env.final_reward())
            step_result = env.step(action)
            next_score = float(env.final_reward())
            reward = next_score - previous_score
            if env.is_terminal():
                target = reward
            else:
                next_state_key = state_key_from_features(env.encode_state())
                next_legal_actions = env.legal_actions()
                next_state_qs = q_table[next_state_key]
                next_best_q = max(
                    (next_state_qs.get(next_action.describe(), 0.0) for next_action in next_legal_actions),
                    default=0.0,
                )
                target = reward + config.gamma * next_best_q

            old_q = state_qs.get(action_description, 0.0)
            state_visits = visit_counts[state_key]
            action_visits = state_visits.get(action_description, 0) + 1
            state_visits[action_description] = action_visits
            step_size = (1.0 / action_visits) if config.use_visit_based_alpha else config.alpha
            new_q = old_q + step_size * (target - old_q)
            state_qs[action_description] = new_q

            episode_trace.append(
                f"{decision_label} -> {action_description} "
                f"(epsilon={epsilon:.4f}, alpha={step_size:.4f}, reward_delta={reward:.4f}, "
                f"old_q={old_q:.4f}, new_q={new_q:.4f})"
            )
            for detail in step_result.detail_lines:
                episode_trace.append(f"    {detail}")

        final_reward = float(env.final_reward())
        history.append(
            {
                "episode": float(episode_index),
                "reward": final_reward,
                "epsilon": epsilon,
                "japan_income": float(env.nation_income("Japan")),
                "japan_units": float(env.unit_count_for("Japan")),
                "japan_unit_value": float(env.unit_value_for("Japan")),
                "destroyed_enemy_unit_value": float(env.enemy_unit_value_destroyed_by_nation("Japan")),
                "japan_decisions": float(len(episode_q_tables)),
                "known_states": float(len(q_table)),
                "known_state_actions": float(sum(len(action_map) for action_map in q_table.values())),
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
                "q_tables": list(episode_q_tables),
            }
            best_self_play_episode_index = episode_index + 1

        should_evaluate = (
            (episode_index + 1) % config.eval_every == 0
            or episode_index == config.episodes - 1
        )
        if should_evaluate:
            evaluation = run_greedy_episode(env, q_table)
            evaluation_history.append(evaluation_checkpoint_payload(episode_index + 1, evaluation))
            if (
                best_greedy_evaluation is None
                or float(evaluation["final_reward"]) > float(best_greedy_evaluation["final_reward"])
            ):
                best_greedy_evaluation = {
                    "final_reward": float(evaluation["final_reward"]),
                    "japan_income": int(evaluation["japan_income"]),
                    "japan_units": int(evaluation["japan_units"]),
                    "japan_unit_value": int(evaluation["japan_unit_value"]),
                    "destroyed_enemy_unit_value": int(evaluation["destroyed_enemy_unit_value"]),
                    "trace": list(evaluation["trace"]),
                    "q_tables": list(evaluation["q_tables"]),
                }
                best_greedy_evaluation_episode = episode_index + 1

    first_decision_q_values = snapshot_first_purchase_q_values(env, q_table)
    final_greedy_evaluation = run_greedy_episode(env, q_table)
    return {
        "config": asdict(config),
        "state_dim": state_dim,
        "action_dim": action_dim,
        "history": history,
        "evaluation_history": evaluation_history,
        "best_self_play_episode": best_self_play_episode,
        "best_self_play_episode_index": best_self_play_episode_index,
        "best_greedy_evaluation": best_greedy_evaluation,
        "best_greedy_evaluation_episode": best_greedy_evaluation_episode,
        "first_decision_q_values": first_decision_q_values,
        "final_greedy_evaluation": final_greedy_evaluation,
        "known_states": len(q_table),
        "known_state_actions": sum(len(action_map) for action_map in q_table.values()),
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
    best_self_play_episode = result.get("best_self_play_episode")
    best_self_play_episode_index = result.get("best_self_play_episode_index")
    best_greedy_evaluation = result.get("best_greedy_evaluation")
    best_greedy_evaluation_episode = result.get("best_greedy_evaluation_episode")

    lines = [
        "Japan Q-learning training summary",
        f"episodes={int(result['config']['episodes'])}",
        f"state_dim={result['state_dim']}",
        f"action_dim={result['action_dim']}",
        "note=self_play_rewards_are_epsilon_greedy_training_episodes; "
        "greedy_evaluation_uses_argmax_q",
        f"recent_average_self_play_reward={recent_average_self_play_reward:.4f}",
        f"known_states={int(result['known_states'])}",
        f"known_state_actions={int(result['known_state_actions'])}",
        "",
        "Training config",
    ]
    for key, value in result["config"].items():
        lines.append(f"- {key}={value}")
    if history:
        last = history[-1]
        lines.extend(
            [
                f"last_self_play_reward={last['reward']:.4f}",
                f"last_self_play_epsilon={last['epsilon']:.4f}",
                f"last_self_play_japan_income={int(last['japan_income'])}",
                f"last_self_play_japan_units={int(last['japan_units'])}",
                f"last_self_play_japan_unit_value={int(last['japan_unit_value'])}",
                f"last_self_play_destroyed_enemy_unit_value={int(last['destroyed_enemy_unit_value'])}",
            ]
        )
    if best_greedy_evaluation is not None and best_greedy_evaluation_episode is not None:
        lines.extend(
            [
                f"best_greedy_evaluation_reward={best_greedy_evaluation['final_reward']:.4f}",
                f"best_greedy_evaluation_episode={int(best_greedy_evaluation_episode)}",
            ]
        )
    if best_self_play_episode is not None and best_self_play_episode_index is not None:
        lines.extend(
            [
                f"best_self_play_reward={best_self_play_episode['final_reward']:.4f}",
                f"best_self_play_episode={int(best_self_play_episode_index)}",
            ]
        )

    if evaluation_history:
        lines.append("")
        lines.append("Greedy evaluation checkpoints")
        for entry in evaluation_history:
            lines.append(
                f"- episode={int(entry['episode'])} reward={entry['final_reward']:.4f} "
                f"income={int(entry['japan_income'])} units={int(entry['japan_units'])} "
                f"unit_value={int(entry['japan_unit_value'])} "
                f"destroyed_enemy_unit_value={int(entry['destroyed_enemy_unit_value'])}"
            )

    lines.append("")
    lines.append("First decision after declaration")
    for entry in result["first_decision_q_values"]:
        lines.append(
            f"- {entry['action']}: q_value={entry['q_value']:.4f}"
        )

    lines.append("")
    lines.append("Current greedy evaluation")
    lines.append(f"- reward={result['final_greedy_evaluation']['final_reward']:.4f}")
    lines.append(f"- japan_income={result['final_greedy_evaluation']['japan_income']}")
    lines.append(f"- japan_units={result['final_greedy_evaluation']['japan_units']}")
    lines.append(f"- japan_unit_value={result['final_greedy_evaluation']['japan_unit_value']}")
    lines.append(
        f"- destroyed_enemy_unit_value={result['final_greedy_evaluation']['destroyed_enemy_unit_value']}"
    )
    lines.extend(result["final_greedy_evaluation"]["trace"])

    detail_files: list[str] = []
    if best_self_play_episode is not None and best_self_play_episode_index is not None:
        detail_files.append("- best self-play episode trace: output/best_q_learning_self_play_trace.txt")
    if best_greedy_evaluation is not None and best_greedy_evaluation_episode is not None:
        detail_files.append("- best greedy evaluation trace: output/best_q_learning_greedy_trace.txt")
    if detail_files:
        lines.append("")
        lines.append("Detailed trace files")
        lines.extend(detail_files)

    (output_dir / "japan_q_learning_summary.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    metrics_payload = {
        "config": result["config"],
        "state_dim": result["state_dim"],
        "action_dim": result["action_dim"],
        "history": result["history"],
        "evaluation_history": result["evaluation_history"],
        "best_self_play_episode": result["best_self_play_episode"],
        "best_self_play_episode_index": result["best_self_play_episode_index"],
        "best_greedy_evaluation": result["best_greedy_evaluation"],
        "best_greedy_evaluation_episode": result["best_greedy_evaluation_episode"],
        "first_decision_q_values": result["first_decision_q_values"],
        "final_greedy_evaluation": result["final_greedy_evaluation"],
        "known_states": result["known_states"],
        "known_state_actions": result["known_state_actions"],
    }
    (output_dir / "japan_q_learning_metrics.json").write_text(
        json.dumps(metrics_payload, indent=2),
        encoding="utf-8",
    )

    write_reward_svg(
        evaluation_history,
        output_dir / "japan_q_learning_reward_over_time.svg",
        "Greedy Q-Learning Reward Over Training",
    )

    if best_greedy_evaluation is not None and best_greedy_evaluation_episode is not None:
        best_trace_lines = [
            "Best greedy evaluation",
            f"episode={int(best_greedy_evaluation_episode)}",
            f"reward={best_greedy_evaluation['final_reward']:.4f}",
            f"japan_income={best_greedy_evaluation['japan_income']}",
            f"japan_units={best_greedy_evaluation['japan_units']}",
            f"japan_unit_value={best_greedy_evaluation['japan_unit_value']}",
            f"destroyed_enemy_unit_value={best_greedy_evaluation['destroyed_enemy_unit_value']}",
            "",
        ]
        best_trace_lines.extend(best_greedy_evaluation["trace"])
        if best_greedy_evaluation.get("q_tables"):
            best_trace_lines.append("")
            best_trace_lines.append("Q tables")
            for decision in best_greedy_evaluation["q_tables"]:
                best_trace_lines.append("")
                best_trace_lines.append(
                    f"{decision['decision']} -> chosen={decision['chosen_action']} "
                    f"(q_value={decision['chosen_q_value']:.4f})"
                )
                for action_entry in decision["actions"]:
                    best_trace_lines.append(
                        f"  - {action_entry['action']}: q_value={action_entry['q_value']:.4f}"
                    )
        (output_dir / "best_q_learning_greedy_trace.txt").write_text(
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
        if best_self_play_episode.get("q_tables"):
            best_self_play_lines.append("")
            best_self_play_lines.append("Q tables")
            for decision in best_self_play_episode["q_tables"]:
                best_self_play_lines.append("")
                best_self_play_lines.append(
                    f"{decision['decision']} -> chosen={decision['chosen_action']} "
                    f"(q_value={decision['chosen_q_value']:.4f})"
                )
                for action_entry in decision["actions"]:
                    best_self_play_lines.append(
                        f"  - {action_entry['action']}: q_value={action_entry['q_value']:.4f}"
                    )
        (output_dir / "best_q_learning_self_play_trace.txt").write_text(
            "\n".join(best_self_play_lines) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    defaults = QLearningConfig()
    parser = argparse.ArgumentParser(description="Train a separate Japan tabular Q-learning baseline")
    parser.add_argument("--episodes", type=int, default=defaults.episodes)
    parser.add_argument(
        "--scenario",
        type=Path,
        default=Path("game_content/scenarios/china_simplified_setup.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/q_learning"))
    parser.add_argument("--eval-every", type=int, default=defaults.eval_every)
    parser.add_argument("--alpha", type=float, default=defaults.alpha)
    parser.add_argument(
        "--use-visit-based-alpha",
        action="store_true",
        help="Use alpha = 1 / N(s, a) instead of a fixed learning rate",
    )
    parser.add_argument("--gamma", type=float, default=defaults.gamma)
    parser.add_argument("--epsilon-start", type=float, default=defaults.epsilon_start)
    parser.add_argument("--epsilon-end", type=float, default=defaults.epsilon_end)
    parser.add_argument("--epsilon-decay-episodes", type=int, default=defaults.epsilon_decay_episodes)
    parser.add_argument("--seed", type=int, default=defaults.seed)
    args = parser.parse_args()

    config = QLearningConfig(
        episodes=args.episodes,
        eval_every=args.eval_every,
        alpha=args.alpha,
        use_visit_based_alpha=args.use_visit_based_alpha,
        gamma=args.gamma,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        epsilon_decay_episodes=args.epsilon_decay_episodes,
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
    print("Japan Q-learning training complete")
    print(f"episodes={config.episodes}")
    print(f"state_dim={result['state_dim']}")
    print(f"action_dim={result['action_dim']}")
    print(f"recent_average_self_play_reward={recent_average_self_play_reward:.4f}")
    print(f"current_greedy_evaluation_reward={result['final_greedy_evaluation']['final_reward']:.4f}")
    if result["first_decision_q_values"]:
        best = result["first_decision_q_values"][0]
        print(
            "best_first_decision_action="
            f"{best['action']} q_value={best['q_value']:.4f}"
        )


if __name__ == "__main__":
    main()
