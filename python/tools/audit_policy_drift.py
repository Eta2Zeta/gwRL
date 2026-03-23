from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch.distributions import Categorical

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
PYTHON_ROOT = WORKSPACE_ROOT / "python"
for import_root in (WORKSPACE_ROOT, PYTHON_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from japan_mcts import MctsConfig, run_mcts, select_action_index_from_policy, tensorize_state_and_actions
from policy_value_model import LegalActionPolicyValueNet, PolicyValueModelConfig
from train_japan_policy_torch import TrainingConfig, run_search_episode, summarize_search_root

try:
    import gwrl_cpp
except ImportError as exc:  # pragma: no cover - import failure should be obvious to the user
    raise SystemExit(
        "Unable to import gwrl_cpp. Build/install the extension first with "
        "`./.venv/bin/python -m pip install -e .`."
    ) from exc


def format_episode_trace(header: str, episode: int, evaluation: dict[str, Any]) -> list[str]:
    lines = [
        f"Episode {episode} {header}",
        f"- reward={evaluation['final_reward']:.4f}",
        f"- japan_income={evaluation['japan_income']}",
        f"- japan_units={evaluation['japan_units']}",
        f"- japan_unit_value={evaluation['japan_unit_value']}",
        f"- destroyed_enemy_unit_value={evaluation['destroyed_enemy_unit_value']}",
        "",
        "Decision trace",
    ]
    lines.extend(evaluation["trace"])
    lines.append("")
    lines.append("Root search tables")
    for decision in evaluation["search_tables"]:
        lines.append("")
        lines.append(
            f"{decision['decision']} -> chosen={decision['chosen_action']} "
            f"(search_prob={decision['chosen_search_probability']:.4f}, "
            f"prior={decision['chosen_prior_probability']:.4f}, "
            f"visits={decision['chosen_visits']}, "
            f"action_value={decision['chosen_action_value']:.4f})"
        )
        for action_entry in decision["actions"]:
            lines.append(
                f"  - {action_entry['action']}: "
                f"search_prob={action_entry['search_probability']:.4f} "
                f"prior={action_entry['prior_probability']:.4f} "
                f"visits={action_entry['visits']} "
                f"action_value={action_entry['action_value']:.4f}"
            )
    return lines


def audit_training(config: TrainingConfig, scenario_path: Path) -> dict[str, Any]:
    torch.manual_seed(config.seed)
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

    checkpoint_evaluations: list[dict[str, Any]] = []
    evaluation_by_episode: dict[int, dict[str, Any]] = {}
    self_play_by_episode: dict[int, dict[str, Any]] = {}

    for episode_index in range(config.episodes):
        env.reset()
        search_examples: list[tuple[list[float], list[list[float]], list[float]]] = []
        self_play_trace: list[str] = []
        self_play_search_tables: list[dict[str, Any]] = []

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
            self_play_search_tables.append(
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
            self_play_trace.append(
                f"{decision_label} -> {action.describe()} "
                f"(search_prob={chosen_entry['search_probability']:.4f}, "
                f"prior={chosen_entry['prior_probability']:.4f}, "
                f"visits={chosen_entry['visits']}, "
                f"action_value={chosen_entry['action_value']:.4f})"
            )
            step_result = env.step(action)
            for detail in step_result.detail_lines:
                self_play_trace.append(f"    {detail}")
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

        policy_losses: list[torch.Tensor] = []
        value_losses: list[torch.Tensor] = []
        entropies: list[torch.Tensor] = []
        target_value = torch.tensor([final_reward], dtype=torch.float32)

        for state_features, legal_action_features, target_policy in search_examples:
            state_tensor, action_tensor = tensorize_state_and_actions(
                state_features,
                legal_action_features,
            )
            target_policy_tensor = torch.tensor(target_policy, dtype=torch.float32).unsqueeze(0)
            logits, value = model(state_tensor, action_tensor)
            log_probs = torch.log_softmax(logits, dim=-1)
            policy_losses.append(-(target_policy_tensor * log_probs).sum(dim=-1).mean())
            value_losses.append(F.mse_loss(value, target_value))
            entropies.append(Categorical(logits=logits.squeeze(0)).entropy())

        policy_loss = torch.stack(policy_losses).mean()
        value_loss = torch.stack(value_losses).mean()
        entropy_bonus = torch.stack(entropies).mean()
        loss = policy_loss + config.value_loss_coef * value_loss - config.entropy_coef * entropy_bonus

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip_norm)
        optimizer.step()

        episode_number = episode_index + 1
        self_play_by_episode[episode_number] = {
            "final_reward": final_reward,
            "japan_income": int(env.nation_income("Japan")),
            "japan_units": int(env.unit_count_for("Japan")),
            "japan_unit_value": int(env.unit_value_for("Japan")),
            "destroyed_enemy_unit_value": int(env.enemy_unit_value_destroyed_by_nation("Japan")),
            "trace": list(self_play_trace),
            "search_tables": list(self_play_search_tables),
        }
        evaluation = run_search_episode(env, model, mcts_config)
        evaluation_by_episode[episode_number] = {
            "final_reward": float(evaluation["final_reward"]),
            "japan_income": int(evaluation["japan_income"]),
            "japan_units": int(evaluation["japan_units"]),
            "japan_unit_value": int(evaluation["japan_unit_value"]),
            "destroyed_enemy_unit_value": int(evaluation["destroyed_enemy_unit_value"]),
            "trace": list(evaluation["trace"]),
            "search_tables": list(evaluation["search_tables"]),
        }
        if episode_number % config.eval_every == 0 or episode_index == config.episodes - 1:
            checkpoint_evaluations.append(
                {
                    "episode": episode_number,
                    "final_reward": float(evaluation["final_reward"]),
                }
            )

    best_checkpoint = max(checkpoint_evaluations, key=lambda item: item["final_reward"])
    best_episode = int(best_checkpoint["episode"])
    audited_episodes = [episode for episode in range(best_episode, min(config.episodes, best_episode + 3) + 1)]
    audited_evaluations = {
        episode: evaluation_by_episode[episode]
        for episode in audited_episodes
        if episode in evaluation_by_episode
    }

    return {
        "best_checkpoint": best_checkpoint,
        "audited_episodes": audited_episodes,
        "audited_evaluations": audited_evaluations,
        "audited_self_play": {
            episode: self_play_by_episode[episode]
            for episode in audited_episodes
            if episode in self_play_by_episode
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit policy drift after the best deterministic checkpoint.")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--scenario", type=Path, default=Path("data/china_simplified_setup.json"))
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--state-hidden-dim", type=int, default=128)
    parser.add_argument("--action-hidden-dim", type=int, default=64)
    parser.add_argument("--joint-hidden-dim", type=int, default=128)
    parser.add_argument("--search-simulations", type=int, default=200)
    parser.add_argument("--eval-every", type=int, default=5)
    parser.add_argument("--c-puct", type=float, default=1.5)
    parser.add_argument("--root-dirichlet-alpha", type=float, default=0.3)
    parser.add_argument("--root-dirichlet-epsilon", type=float, default=0.25)
    parser.add_argument("--self-play-temperature", type=float, default=1.0)
    parser.add_argument("--value-loss-coef", type=float, default=0.25)
    parser.add_argument("--entropy-coef", type=float, default=0.001)
    parser.add_argument("--grad-clip-norm", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=1936)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/policy_drift_audit.txt"),
        help="Optional file to write the audit report to.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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
        seed=args.seed,
    )
    audit = audit_training(config, args.scenario)

    lines = [
        "Policy drift audit",
        f"best_deterministic_checkpoint_episode={audit['best_checkpoint']['episode']}",
        f"best_deterministic_checkpoint_reward={audit['best_checkpoint']['final_reward']:.4f}",
        "",
        "Audited actual self-play episodes",
    ]
    for episode in audit["audited_episodes"]:
        lines.append("")
        evaluation = audit["audited_self_play"].get(episode)
        if evaluation is None:
            lines.append(f"Episode {episode} self-play trace missing")
            continue
        lines.extend(format_episode_trace("self-play", episode, evaluation))

    lines.append("")
    lines.append("Audited deterministic checkpoint-style evaluations")
    for episode in audit["audited_episodes"]:
        lines.append("")
        evaluation = audit["audited_evaluations"].get(episode)
        if evaluation is None:
            lines.append(f"Episode {episode} deterministic evaluation missing")
            continue
        lines.extend(format_episode_trace("deterministic evaluation", episode, evaluation))

    output_text = "\n".join(lines)
    args.output.write_text(output_text + "\n", encoding="utf-8")
    print(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
