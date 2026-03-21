from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch.distributions import Categorical

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    learning_rate: float = 0.001
    state_hidden_dim: int = 128
    action_hidden_dim: int = 64
    joint_hidden_dim: int = 128
    value_loss_coef: float = 0.25
    entropy_coef: float = 0.01
    grad_clip_norm: float = 5.0
    seed: int = 1936


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


def tensorize_state_and_actions(
    state_features: list[float],
    legal_action_features: list[list[float]],
) -> tuple[torch.Tensor, torch.Tensor]:
    state_tensor = torch.tensor(state_features, dtype=torch.float32).unsqueeze(0)
    action_tensor = torch.tensor(legal_action_features, dtype=torch.float32).unsqueeze(0)
    return state_tensor, action_tensor


def run_greedy_episode(env: gwrl_cpp.JapanTrainingEnv, model: LegalActionPolicyValueNet) -> dict[str, Any]:
    env.reset()
    trace: list[str] = []

    while not env.is_terminal():
        state_tensor, action_tensor = tensorize_state_and_actions(
            env.encode_state(),
            env.encode_legal_actions(),
        )
        with torch.no_grad():
            logits, value = model(state_tensor, action_tensor)
        action_index = int(torch.argmax(logits.squeeze(0)).item())
        action = env.legal_actions()[action_index]
        acting_turn = env.completed_turns_for("Japan") + 1
        trace.append(
            f"Japan turn {acting_turn} / {env.current_phase()} -> "
            f"{action.describe()} (value={float(value.item()):.4f})"
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
    }


def train(config: TrainingConfig, scenario_path: Path) -> dict[str, Any]:
    torch.manual_seed(config.seed)
    env = gwrl_cpp.JapanTrainingEnv(str(scenario_path), "Japan")
    state_dim = len(env.state_feature_labels())
    action_dim = len(env.action_feature_labels())

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

    for episode_index in range(config.episodes):
        env.reset()
        log_probs: list[torch.Tensor] = []
        values: list[torch.Tensor] = []
        entropies: list[torch.Tensor] = []

        while not env.is_terminal():
            state_tensor, action_tensor = tensorize_state_and_actions(
                env.encode_state(),
                env.encode_legal_actions(),
            )
            logits, value = model(state_tensor, action_tensor)
            distribution = Categorical(logits=logits.squeeze(0))
            action_index = distribution.sample()
            action = env.legal_actions()[int(action_index.item())]
            env.step(action)

            log_probs.append(distribution.log_prob(action_index))
            values.append(value.squeeze(0))
            entropies.append(distribution.entropy())

            if env.is_terminal():
                final_reward = float(env.final_reward())
                break
        else:
            final_reward = float(env.final_reward())

        returns = torch.full((len(values),), final_reward, dtype=torch.float32)
        value_tensor = torch.stack(values)
        log_prob_tensor = torch.stack(log_probs)
        entropy_tensor = torch.stack(entropies)
        advantages = returns - value_tensor.detach()

        policy_loss = -(log_prob_tensor * advantages).mean()
        value_loss = F.mse_loss(value_tensor, returns)
        entropy_bonus = entropy_tensor.mean()
        loss = policy_loss + config.value_loss_coef * value_loss - config.entropy_coef * entropy_bonus

        optimizer.zero_grad()
        loss.backward()
        grad_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip_norm))
        optimizer.step()

        history.append(
            {
                "episode": float(episode_index),
                "reward": final_reward,
                "japan_income": float(env.nation_income("Japan")),
                "japan_units": float(env.unit_count_for("Japan")),
                "japan_unit_value": float(env.unit_value_for("Japan")),
                "destroyed_enemy_unit_value": float(env.enemy_unit_value_destroyed_by_nation("Japan")),
                "japan_decisions": float(len(values)),
                "loss": float(loss.item()),
                "policy_loss": float(policy_loss.item()),
                "value_loss": float(value_loss.item()),
                "entropy": float(entropy_bonus.item()),
                "gradient_norm": grad_norm,
            }
        )

    verification: dict[str, Any] | None = None
    cpp_example_path = Path("output/japan_training_example.json")
    if cpp_example_path.exists():
        verification = verify_against_cpp_example(env, cpp_example_path)

    state_features, legal_action_features, legal_actions = build_first_decision_after_declaration_snapshot(env)
    state_tensor, action_tensor = tensorize_state_and_actions(state_features, legal_action_features)
    with torch.no_grad():
        logits, value = model(state_tensor, action_tensor)
        probabilities = torch.softmax(logits.squeeze(0), dim=0)
    first_decision_policy = [
        {
            "action": action.describe(),
            "probability": float(probabilities[index].item()),
            "logit": float(logits.squeeze(0)[index].item()),
        }
        for index, action in enumerate(legal_actions)
    ]
    first_decision_policy.sort(key=lambda item: item["probability"], reverse=True)

    greedy_evaluation = run_greedy_episode(env, model)
    return {
        "config": asdict(config),
        "state_dim": state_dim,
        "action_dim": action_dim,
        "history": history,
        "first_decision_policy": first_decision_policy,
        "greedy_evaluation": greedy_evaluation,
        "verification": verification,
        "model": model,
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    history = result["history"]
    recent_window = history[-20:] if len(history) >= 20 else history
    recent_average_reward = (
        sum(item["reward"] for item in recent_window) / len(recent_window)
        if recent_window
        else 0.0
    )

    lines = [
        "Japan Torch training summary",
        f"episodes={int(result['config']['episodes'])}",
        f"state_dim={result['state_dim']}",
        f"action_dim={result['action_dim']}",
        f"recent_average_reward={recent_average_reward:.4f}",
    ]
    if history:
        last = history[-1]
        lines.extend(
            [
                f"last_reward={last['reward']:.4f}",
                f"last_japan_income={int(last['japan_income'])}",
                f"last_japan_units={int(last['japan_units'])}",
                f"last_japan_unit_value={int(last['japan_unit_value'])}",
                f"last_destroyed_enemy_unit_value={int(last['destroyed_enemy_unit_value'])}",
                f"last_loss={last['loss']:.4f}",
                f"last_gradient_norm={last['gradient_norm']:.4f}",
            ]
        )

    verification = result.get("verification")
    if verification is not None:
        lines.append(
            f"encoder_match_with_cpp_export={'yes' if verification['ok'] else 'no'}"
        )
        for message in verification["messages"]:
            lines.append(f"verification_note={message}")

    lines.append("")
    lines.append("First decision after declaration")
    for entry in result["first_decision_policy"]:
        lines.append(
            f"- {entry['action']}: prob={entry['probability']:.4f} logit={entry['logit']:.4f}"
        )

    lines.append("")
    lines.append("Greedy evaluation")
    lines.append(f"- reward={result['greedy_evaluation']['final_reward']:.4f}")
    lines.append(f"- japan_income={result['greedy_evaluation']['japan_income']}")
    lines.append(f"- japan_units={result['greedy_evaluation']['japan_units']}")
    lines.append(f"- japan_unit_value={result['greedy_evaluation']['japan_unit_value']}")
    lines.append(
        f"- destroyed_enemy_unit_value={result['greedy_evaluation']['destroyed_enemy_unit_value']}"
    )
    lines.extend(result["greedy_evaluation"]["trace"])

    (output_dir / "japan_torch_training_summary.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    metrics_payload = {
        "config": result["config"],
        "state_dim": result["state_dim"],
        "action_dim": result["action_dim"],
        "history": result["history"],
        "first_decision_policy": result["first_decision_policy"],
        "greedy_evaluation": result["greedy_evaluation"],
        "verification": result["verification"],
    }
    (output_dir / "japan_torch_training_metrics.json").write_text(
        json.dumps(metrics_payload, indent=2),
        encoding="utf-8",
    )

    model: LegalActionPolicyValueNet = result["model"]
    torch.save(model.state_dict(), output_dir / "japan_torch_policy.pt")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Japan policy with PyTorch")
    parser.add_argument("--episodes", type=int, default=800)
    parser.add_argument("--scenario", type=Path, default=Path("data/china_simplified_setup.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=1936)
    args = parser.parse_args()

    config = TrainingConfig(
        episodes=args.episodes,
        learning_rate=args.learning_rate,
        seed=args.seed,
    )
    result = train(config, args.scenario)
    write_outputs(result, args.output_dir)

    history = result["history"]
    recent_window = history[-20:] if len(history) >= 20 else history
    recent_average_reward = (
        sum(item["reward"] for item in recent_window) / len(recent_window)
        if recent_window
        else 0.0
    )
    print("Japan Torch training complete")
    print(f"episodes={config.episodes}")
    print(f"state_dim={result['state_dim']}")
    print(f"action_dim={result['action_dim']}")
    print(f"recent_average_reward={recent_average_reward:.4f}")
    if result["first_decision_policy"]:
        best = result["first_decision_policy"][0]
        print(f"best_first_decision_action={best['action']} prob={best['probability']:.4f}")


if __name__ == "__main__":
    main()
