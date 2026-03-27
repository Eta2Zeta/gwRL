from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch.distributions import Categorical

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import gwrl_cpp
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Unable to import gwrl_cpp. Build/install the extension first with "
        "`./.venv/bin/python -m pip install -e .`."
    ) from exc

from composition_mcts import MctsConfig, run_mcts, select_action_index_from_policy
from policy_value_model import LegalActionPolicyValueNet, PolicyValueModelConfig


@dataclass(slots=True)
class ReplayExample:
    state_features: list[float]
    legal_action_features: list[list[float]]
    target_policy: list[float]
    target_value: float


@dataclass(slots=True)
class TrainingConfig:
    episodes: int = 200
    eval_every: int = 10
    learning_rate: float = 0.001
    state_hidden_dim: int = 128
    action_hidden_dim: int = 64
    joint_hidden_dim: int = 128
    search_simulations: int = 128
    c_puct: float = 1.5
    root_dirichlet_alpha: float = 0.3
    root_dirichlet_epsilon: float = 0.25
    self_play_temperature: float = 1.0
    value_loss_coef: float = 0.25
    entropy_coef: float = 0.001
    grad_clip_norm: float = 5.0
    attacker_budget: int = 10
    defender_budget: int = 10
    terrain: str = "normal"
    is_city: bool = False
    seed: int = 1936


class LightweightAdam:
    def __init__(self, parameters: list[torch.nn.Parameter] | Any, lr: float, eps: float = 1e-8) -> None:
        self.parameters = [parameter for parameter in parameters if parameter.requires_grad]
        self.lr = lr
        self.eps = eps
        self.step_count = 0
        self.first_moments = [torch.zeros_like(parameter) for parameter in self.parameters]
        self.second_moments = [torch.zeros_like(parameter) for parameter in self.parameters]
        self.beta1 = 0.9
        self.beta2 = 0.999

    def zero_grad(self) -> None:
        for parameter in self.parameters:
            if parameter.grad is not None:
                parameter.grad.zero_()

    def step(self) -> None:
        self.step_count += 1
        beta1_correction = 1.0 - self.beta1 ** self.step_count
        beta2_correction = 1.0 - self.beta2 ** self.step_count
        with torch.no_grad():
            for parameter, first_moment, second_moment in zip(
                self.parameters,
                self.first_moments,
                self.second_moments,
            ):
                if parameter.grad is None:
                    continue
                gradient = parameter.grad
                first_moment.mul_(self.beta1).add_(gradient, alpha=1.0 - self.beta1)
                second_moment.mul_(self.beta2).addcmul_(gradient, gradient, value=1.0 - self.beta2)
                first_unbiased = first_moment / beta1_correction
                second_unbiased = second_moment / beta2_correction
                parameter.addcdiv_(first_unbiased, second_unbiased.sqrt().add_(self.eps), value=-self.lr)


def build_env(config: TrainingConfig) -> gwrl_cpp.CompositionBattleEnv:
    return gwrl_cpp.CompositionBattleEnv(
        attacker_budget=config.attacker_budget,
        defender_budget=config.defender_budget,
        terrain=config.terrain,
        is_city=config.is_city,
    )


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


def compute_player_losses(
    model: LegalActionPolicyValueNet,
    examples: list[ReplayExample],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    if not examples:
        zero = next(model.parameters()).new_tensor(0.0)
        return zero, zero, zero

    policy_losses: list[torch.Tensor] = []
    value_losses: list[torch.Tensor] = []
    entropies: list[torch.Tensor] = []
    for example in examples:
        state_tensor = torch.tensor(example.state_features, dtype=torch.float32).unsqueeze(0)
        action_tensor = torch.tensor(example.legal_action_features, dtype=torch.float32).unsqueeze(0)
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


def snapshot_first_attacker_purchase(
    env: gwrl_cpp.CompositionBattleEnv,
    attacker_model: LegalActionPolicyValueNet,
    defender_model: LegalActionPolicyValueNet,
    mcts_config: MctsConfig,
) -> list[dict[str, Any]]:
    env.reset()
    search = run_mcts(env, attacker_model, defender_model, mcts_config, add_root_noise=False)
    return summarize_search_root(search)


def run_deterministic_episode(
    env: gwrl_cpp.CompositionBattleEnv,
    attacker_model: LegalActionPolicyValueNet,
    defender_model: LegalActionPolicyValueNet,
    mcts_config: MctsConfig,
) -> dict[str, Any]:
    env.reset()
    trace: list[str] = []
    search_tables: list[dict[str, Any]] = []
    while not env.is_terminal():
        search = run_mcts(env, attacker_model, defender_model, mcts_config, add_root_noise=False)
        action_index = select_action_index_from_policy(search.policy, temperature=0.0)
        action = search.actions[action_index]
        decision_label = f"{env.current_nation()} / {env.current_phase()}"
        search_tables.append(
            {
                "decision": decision_label,
                "chosen_action": action.describe(),
                "actions": summarize_search_root(search),
            }
        )
        trace.append(
            f"{decision_label} -> {action.describe()} "
            f"(search_value={search.action_values[action_index]:.4f}, visits={search.visit_counts[action_index]})"
        )
        step_result = env.step(action)
        for detail in step_result.detail_lines:
            trace.append(f"    {detail}")
    return {
        "final_reward": float(env.final_reward()),
        "winner_id": env.winner_id(),
        "trace": trace,
        "search_tables": search_tables,
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
                '</svg>'
            ),
            encoding='utf-8',
        )
        return

    episodes = [entry['episode'] for entry in evaluations]
    rewards = [entry['final_reward'] for entry in evaluations]
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

    polyline_points = ' '.join(
        f"{x_pos(entry['episode']):.1f},{y_pos(entry['final_reward']):.1f}"
        for entry in evaluations
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#fffaf2"/>',
        '<text x="50%" y="28" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="24" font-weight="700" fill="#2b2b2b">{title}</text>',
        f'<line x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}" stroke="#666" stroke-width="2"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}" stroke="#666" stroke-width="2"/>',
        f'<polyline fill="none" stroke="#0f766e" stroke-width="3" points="{polyline_points}"/>',
    ]
    for entry in evaluations:
        parts.append(
            f'<circle cx="{x_pos(entry["episode"]):.1f}" cy="{y_pos(entry["final_reward"]):.1f}" r="4" fill="#115e59" stroke="#ffffff" stroke-width="1.5"/>'
        )
    parts.extend([
        f'<text x="{margin_left + plot_width / 2:.1f}" y="{height - 15}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#444">Episode</text>',
        f'<text x="18" y="{margin_top + plot_height / 2:.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#444" transform="rotate(-90 18 {margin_top + plot_height / 2:.1f})">Attacker reward</text>',
        '</svg>',
    ])
    output_path.write_text('\n'.join(parts), encoding='utf-8')


def train(config: TrainingConfig) -> dict[str, Any]:
    random.seed(config.seed)
    torch.manual_seed(config.seed)

    env = build_env(config)
    state_dim = len(env.state_feature_labels())
    action_dim = len(env.action_feature_labels())
    model_config = PolicyValueModelConfig(
        state_dim=state_dim,
        action_dim=action_dim,
        state_hidden_dim=config.state_hidden_dim,
        action_hidden_dim=config.action_hidden_dim,
        joint_hidden_dim=config.joint_hidden_dim,
    )
    attacker_model = LegalActionPolicyValueNet(model_config)
    defender_model = LegalActionPolicyValueNet(model_config)
    attacker_optimizer = LightweightAdam(attacker_model.parameters(), lr=config.learning_rate)
    defender_optimizer = LightweightAdam(defender_model.parameters(), lr=config.learning_rate)

    mcts_config = MctsConfig(
        simulations=config.search_simulations,
        c_puct=config.c_puct,
        root_dirichlet_alpha=config.root_dirichlet_alpha,
        root_dirichlet_epsilon=config.root_dirichlet_epsilon,
        self_play_temperature=config.self_play_temperature,
    )

    history: list[dict[str, Any]] = []
    evaluation_history: list[dict[str, float]] = []
    best_self_play: dict[str, Any] | None = None
    best_self_play_episode: int | None = None
    best_eval: dict[str, Any] | None = None
    best_eval_episode: int | None = None
    last_attacker_losses: dict[str, float] = {}
    last_defender_losses: dict[str, float] = {}

    for episode_index in range(config.episodes):
        env.reset()
        episode_examples: dict[str, list[ReplayExample]] = {"Attacker": [], "Defender": []}
        episode_trace: list[str] = []
        episode_search_tables: list[dict[str, Any]] = []

        while not env.is_terminal():
            current_player = env.current_nation()
            search = run_mcts(env, attacker_model, defender_model, mcts_config, add_root_noise=True)
            action_index = select_action_index_from_policy(search.policy, temperature=config.self_play_temperature)
            action = search.actions[action_index]
            episode_examples[current_player].append(
                ReplayExample(
                    state_features=search.state_features,
                    legal_action_features=search.legal_action_features,
                    target_policy=search.policy,
                    target_value=0.0,
                )
            )
            episode_search_tables.append(
                {
                    "decision": f"{current_player} / {env.current_phase()}",
                    "chosen_action": action.describe(),
                    "actions": summarize_search_root(search),
                }
            )
            episode_trace.append(
                f"{current_player} / {env.current_phase()} -> {action.describe()} "
                f"(search_value={search.action_values[action_index]:.4f}, visits={search.visit_counts[action_index]})"
            )
            step_result = env.step(action)
            for detail in step_result.detail_lines:
                episode_trace.append(f"    {detail}")

        attacker_outcome = float(env.final_reward())
        defender_outcome = -attacker_outcome
        for example in episode_examples['Attacker']:
            example.target_value = attacker_outcome
        for example in episode_examples['Defender']:
            example.target_value = defender_outcome

        attacker_policy_loss, attacker_value_loss, attacker_entropy = compute_player_losses(attacker_model, episode_examples['Attacker'])
        attacker_loss = attacker_policy_loss + config.value_loss_coef * attacker_value_loss - config.entropy_coef * attacker_entropy
        attacker_optimizer.zero_grad()
        attacker_loss.backward()
        torch.nn.utils.clip_grad_norm_(attacker_model.parameters(), config.grad_clip_norm)
        attacker_optimizer.step()

        defender_policy_loss, defender_value_loss, defender_entropy = compute_player_losses(defender_model, episode_examples['Defender'])
        defender_loss = defender_policy_loss + config.value_loss_coef * defender_value_loss - config.entropy_coef * defender_entropy
        defender_optimizer.zero_grad()
        defender_loss.backward()
        torch.nn.utils.clip_grad_norm_(defender_model.parameters(), config.grad_clip_norm)
        defender_optimizer.step()

        last_attacker_losses = {
            'policy_loss': float(attacker_policy_loss.item()),
            'value_loss': float(attacker_value_loss.item()),
            'entropy_bonus': float(attacker_entropy.item()),
            'total_loss': float(attacker_loss.item()),
        }
        last_defender_losses = {
            'policy_loss': float(defender_policy_loss.item()),
            'value_loss': float(defender_value_loss.item()),
            'entropy_bonus': float(defender_entropy.item()),
            'total_loss': float(defender_loss.item()),
        }

        history.append({
            'episode': float(episode_index + 1),
            'attacker_reward': attacker_outcome,
            'winner': env.winner_id(),
        })

        if best_self_play is None or attacker_outcome > float(best_self_play['final_reward']):
            best_self_play = {
                'final_reward': attacker_outcome,
                'winner_id': env.winner_id(),
                'trace': list(episode_trace),
                'search_tables': list(episode_search_tables),
            }
            best_self_play_episode = episode_index + 1

        should_eval = ((episode_index + 1) % config.eval_every == 0) or episode_index == config.episodes - 1
        if should_eval:
            evaluation = run_deterministic_episode(build_env(config), attacker_model, defender_model, mcts_config)
            evaluation_history.append({
                'episode': float(episode_index + 1),
                'final_reward': float(evaluation['final_reward']),
            })
            if best_eval is None or float(evaluation['final_reward']) > float(best_eval['final_reward']):
                best_eval = evaluation
                best_eval_episode = episode_index + 1

    final_eval = run_deterministic_episode(build_env(config), attacker_model, defender_model, mcts_config)
    first_purchase = snapshot_first_attacker_purchase(build_env(config), attacker_model, defender_model, mcts_config)
    return {
        'config': asdict(config),
        'state_dim': state_dim,
        'action_dim': action_dim,
        'history': history,
        'evaluation_history': evaluation_history,
        'best_self_play': best_self_play,
        'best_self_play_episode': best_self_play_episode,
        'best_eval': best_eval,
        'best_eval_episode': best_eval_episode,
        'final_eval': final_eval,
        'first_purchase': first_purchase,
        'last_attacker_losses': last_attacker_losses,
        'last_defender_losses': last_defender_losses,
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    history = result['history']
    evaluation_history = result['evaluation_history']
    recent_window = history[-20:] if len(history) >= 20 else history
    recent_average_self_play_reward = sum(item['attacker_reward'] for item in recent_window) / len(recent_window) if recent_window else 0.0

    lines = [
        'Composition AlphaZero training summary',
        f"episodes={int(result['config']['episodes'])}",
        f"state_dim={result['state_dim']}",
        f"action_dim={result['action_dim']}",
        'note=two_model_self_play_attacker_vs_defender_zero_sum_battle_composition',
        f'recent_average_attacker_self_play_reward={recent_average_self_play_reward:.4f}',
        '',
        'Training config',
    ]
    for key, value in result['config'].items():
        lines.append(f'- {key}={value}')
    if history:
        last = history[-1]
        lines.extend([
            f"last_self_play_attacker_reward={last['attacker_reward']:.4f}",
            f"last_self_play_winner={last['winner']}",
        ])
    if result['last_attacker_losses']:
        lines.extend([
            f"last_attacker_total_loss={result['last_attacker_losses']['total_loss']:.4f}",
            f"last_defender_total_loss={result['last_defender_losses']['total_loss']:.4f}",
        ])
    if result['best_eval'] is not None and result['best_eval_episode'] is not None:
        lines.extend([
            f"best_deterministic_attacker_reward={result['best_eval']['final_reward']:.4f}",
            f"best_deterministic_episode={int(result['best_eval_episode'])}",
        ])
    if result['best_self_play'] is not None and result['best_self_play_episode'] is not None:
        lines.extend([
            f"best_self_play_attacker_reward={result['best_self_play']['final_reward']:.4f}",
            f"best_self_play_episode={int(result['best_self_play_episode'])}",
        ])

    if evaluation_history:
        lines.append('')
        lines.append('Deterministic evaluation checkpoints')
        for entry in evaluation_history:
            lines.append(
                f"- episode={int(entry['episode'])} attacker_reward={entry['final_reward']:.4f}"
            )

    lines.append('')
    lines.append('First attacker purchase root')
    for entry in result['first_purchase']:
        lines.append(
            f"- {entry['action']}: search_prob={entry['search_probability']:.4f} prior={entry['prior_probability']:.4f} visits={entry['visits']} action_value={entry['action_value']:.4f}"
        )

    lines.append('')
    lines.append('Current deterministic evaluation')
    lines.append(f"- attacker_reward={result['final_eval']['final_reward']:.4f}")
    lines.append(f"- winner_id={result['final_eval']['winner_id']}")
    lines.extend(result['final_eval']['trace'])

    lines.append('')
    lines.append('Detailed trace files')
    lines.append('- best self-play trace: output/best_composition_self_play_trace.txt')
    lines.append('- best deterministic trace: output/best_composition_deterministic_trace.txt')

    (output_dir / 'composition_alpha_zero_summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (output_dir / 'composition_alpha_zero_metrics.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    write_reward_svg(evaluation_history, output_dir / 'composition_alpha_zero_reward_over_time.svg', 'Composition AlphaZero Attacker Reward Over Training')

    if result['best_self_play'] is not None and result['best_self_play_episode'] is not None:
        trace_lines = [
            'Best self-play episode',
            f"episode={int(result['best_self_play_episode'])}",
            f"attacker_reward={result['best_self_play']['final_reward']:.4f}",
            f"winner_id={result['best_self_play']['winner_id']}",
            '',
            'Decision trace',
        ]
        trace_lines.extend(result['best_self_play']['trace'])
        trace_lines.append('')
        trace_lines.append('Root search tables')
        for decision in result['best_self_play']['search_tables']:
            trace_lines.append('')
            trace_lines.append(f"{decision['decision']} -> chosen={decision['chosen_action']}")
            for action in decision['actions']:
                trace_lines.append(
                    f"  - {action['action']}: search_prob={action['search_probability']:.4f} prior={action['prior_probability']:.4f} visits={action['visits']} action_value={action['action_value']:.4f}"
                )
        (output_dir / 'best_composition_self_play_trace.txt').write_text('\n'.join(trace_lines) + '\n', encoding='utf-8')

    if result['best_eval'] is not None and result['best_eval_episode'] is not None:
        trace_lines = [
            'Best deterministic evaluation',
            f"episode={int(result['best_eval_episode'])}",
            f"attacker_reward={result['best_eval']['final_reward']:.4f}",
            f"winner_id={result['best_eval']['winner_id']}",
            '',
        ]
        trace_lines.extend(result['best_eval']['trace'])
        trace_lines.append('')
        trace_lines.append('Root search tables')
        for decision in result['best_eval']['search_tables']:
            trace_lines.append('')
            trace_lines.append(f"{decision['decision']} -> chosen={decision['chosen_action']}")
            for action in decision['actions']:
                trace_lines.append(
                    f"  - {action['action']}: search_prob={action['search_probability']:.4f} prior={action['prior_probability']:.4f} visits={action['visits']} action_value={action['action_value']:.4f}"
                )
        (output_dir / 'best_composition_deterministic_trace.txt').write_text('\n'.join(trace_lines) + '\n', encoding='utf-8')


def main() -> None:
    defaults = TrainingConfig()
    parser = argparse.ArgumentParser(description='Train a separate attacker-vs-defender AlphaZero composition duel')
    parser.add_argument('--episodes', type=int, default=defaults.episodes)
    parser.add_argument('--eval-every', type=int, default=defaults.eval_every)
    parser.add_argument('--learning-rate', type=float, default=defaults.learning_rate)
    parser.add_argument('--state-hidden-dim', type=int, default=defaults.state_hidden_dim)
    parser.add_argument('--action-hidden-dim', type=int, default=defaults.action_hidden_dim)
    parser.add_argument('--joint-hidden-dim', type=int, default=defaults.joint_hidden_dim)
    parser.add_argument('--search-simulations', type=int, default=defaults.search_simulations)
    parser.add_argument('--c-puct', type=float, default=defaults.c_puct)
    parser.add_argument('--root-dirichlet-alpha', type=float, default=defaults.root_dirichlet_alpha)
    parser.add_argument('--root-dirichlet-epsilon', type=float, default=defaults.root_dirichlet_epsilon)
    parser.add_argument('--self-play-temperature', type=float, default=defaults.self_play_temperature)
    parser.add_argument('--value-loss-coef', type=float, default=defaults.value_loss_coef)
    parser.add_argument('--entropy-coef', type=float, default=defaults.entropy_coef)
    parser.add_argument('--grad-clip-norm', type=float, default=defaults.grad_clip_norm)
    parser.add_argument('--attacker-budget', type=int, default=defaults.attacker_budget)
    parser.add_argument('--defender-budget', type=int, default=defaults.defender_budget)
    parser.add_argument('--terrain', type=str, default=defaults.terrain)
    parser.add_argument('--is-city', action='store_true', default=defaults.is_city)
    parser.add_argument('--seed', type=int, default=defaults.seed)
    parser.add_argument('--output-dir', type=Path, default=Path('output/composition_alpha_zero'))
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
        attacker_budget=args.attacker_budget,
        defender_budget=args.defender_budget,
        terrain=args.terrain,
        is_city=args.is_city,
        seed=args.seed,
    )
    result = train(config)
    write_outputs(result, args.output_dir)
    print('Composition AlphaZero training complete')
    print(f"episodes={config.episodes}")
    print(f"state_dim={result['state_dim']}")
    print(f"action_dim={result['action_dim']}")
    print(f"current_deterministic_attacker_reward={result['final_eval']['final_reward']:.4f}")
    print(f"current_winner={result['final_eval']['winner_id']}")


if __name__ == '__main__':
    main()
