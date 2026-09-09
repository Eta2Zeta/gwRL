from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
PYTHON_ROOT = WORKSPACE_ROOT / "python"
for import_root in (WORKSPACE_ROOT, PYTHON_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from japan_mcts import MctsConfig, run_mcts_with_debug
from policy_value_model import LegalActionPolicyValueNet, PolicyValueModelConfig

try:
    import gwrl_cpp
except ImportError as exc:  # pragma: no cover - import failure should be obvious to the user
    raise SystemExit(
        "Unable to import gwrl_cpp. Build/install the extension first with "
        "`./.venv/bin/python -m pip install -e .`."
    ) from exc


def build_model(env: gwrl_cpp.JapanTrainingEnv, checkpoint_path: Path | None) -> LegalActionPolicyValueNet:
    state_dim = len(env.state_feature_labels())
    action_dim = len(env.action_feature_labels())
    model = LegalActionPolicyValueNet(
        PolicyValueModelConfig(
            state_dim=state_dim,
            action_dim=action_dim,
        )
    )
    if checkpoint_path is not None and checkpoint_path.exists():
        state_dict = torch.load(checkpoint_path, map_location="cpu")
        model.load_state_dict(state_dict)
    model.eval()
    return model


def advance_to_purchase_phase_if_requested(
    env: gwrl_cpp.JapanTrainingEnv,
    advance_after_declaration: bool,
) -> list[str]:
    notes: list[str] = []
    env.reset()
    notes.append(f"reset -> {env.current_nation()} / {env.current_phase()}")
    if not advance_after_declaration:
        return notes

    legal_actions = env.legal_actions()
    declare_war = next(
        (action for action in legal_actions if action.kind == gwrl_cpp.ActionKind.DeclareWarOnChina),
        None,
    )
    if declare_war is None:
        notes.append("no declare_war_on_china action was available; staying at current root")
        return notes

    step_result = env.step(declare_war)
    notes.append(f"advance root with {declare_war.describe()}")
    for detail in step_result.detail_lines:
        notes.append(f"  {detail}")
    notes.append(f"new root -> {env.current_nation()} / {env.current_phase()}")
    return notes


def format_trace(
    env: gwrl_cpp.JapanTrainingEnv,
    checkpoint_path: Path | None,
    config: MctsConfig,
    root_notes: list[str],
    trace_result,
    debug_trace,
) -> str:
    lines: list[str] = []
    lines.append("MCTS debug trace")
    lines.append(
        "scenario="
        f"{env.scenario_path if hasattr(env, 'scenario_path') else 'game_content/scenarios/china_simplified_setup.json'}"
    )
    lines.append(f"checkpoint={checkpoint_path if checkpoint_path is not None else 'random_init'}")
    lines.append(f"root_current_nation={env.current_nation()}")
    lines.append(f"root_current_phase={env.current_phase()}")
    lines.append(f"root_value={debug_trace.root_value:.4f}")
    lines.append(f"search_simulations={config.simulations}")
    lines.append(f"c_puct={config.c_puct}")
    lines.append("root_setup:")
    for note in root_notes:
        lines.append(f"  {note}")
    lines.append("root_actions:")
    for index, action in enumerate(debug_trace.root_actions):
        lines.append(
            f"  [{index}] {action} prior={debug_trace.root_priors[index]:.4f} "
            f"selection_prior={debug_trace.root_selection_priors[index]:.4f}"
        )

    for simulation in debug_trace.simulations:
        lines.append("")
        lines.append(f"simulation {simulation.simulation_index}")
        if simulation.selected_path:
            lines.append("  selected_path:")
            for action in simulation.selected_path:
                lines.append(f"    {action}")
        else:
            lines.append("  selected_path: <empty>")

        for step in simulation.selection_steps:
            lines.append(
                f"  step depth={step.depth} state={step.current_nation} / {step.current_phase}"
            )
            for action_score in step.action_scores:
                raw_q = (
                    f"{action_score.raw_q_value:.4f}"
                    if action_score.raw_q_value is not None
                    else "unvisited"
                )
                lines.append(
                    "    "
                    f"{action_score.action_description}: "
                    f"prior={action_score.prior:.4f} "
                    f"selection_prior={action_score.selection_prior:.4f} "
                    f"visits={action_score.visit_count} "
                    f"raw_q={raw_q} "
                    f"norm_q={action_score.normalized_q_value:.4f} "
                    f"u={action_score.exploration:.4f} "
                    f"score={action_score.score:.4f}"
                )
            lines.append(
                f"    chosen=[{step.chosen_action_index}] {step.chosen_action_description}"
            )

        lines.append(
            f"  leaf source={simulation.leaf_source} value={simulation.leaf_value:.4f} "
            f"state={simulation.leaf_nation} / {simulation.leaf_phase}"
        )
        lines.append("  backup:")
        if not simulation.backup_steps:
            lines.append("    <no backup edges>")
        for backup_step in simulation.backup_steps:
            lines.append(
                "    "
                f"depth={backup_step.depth} "
                f"action={backup_step.action_description} "
                f"new_visits={backup_step.new_visit_count} "
                f"new_raw_q={backup_step.new_raw_q_value:.4f} "
                f"min_q={backup_step.min_q_value:.4f} "
                f"max_q={backup_step.max_q_value:.4f}"
            )

    lines.append("")
    lines.append("root_result:")
    for index, action in enumerate(trace_result.actions):
        lines.append(
            f"  [{index}] {action.describe()} "
            f"visits={trace_result.visit_counts[index]} "
            f"policy={trace_result.policy[index]:.4f} "
            f"raw_q={trace_result.action_values[index]:.4f}"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    mcts_defaults = MctsConfig()
    parser = argparse.ArgumentParser(description="Print a detailed trace of one MCTS root search.")
    parser.add_argument(
        "--scenario",
        type=Path,
        default=Path("game_content/scenarios/china_simplified_setup.json"),
        help="Scenario JSON used to build the C++ environment.",
    )
    parser.add_argument(
        "--tracked-nation",
        type=str,
        default="Japan",
        help="Nation controlled by the search/trainer.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("output/japan_torch_policy.pt"),
        help="Optional model checkpoint to load. If the file does not exist, random init is used.",
    )
    parser.add_argument(
        "--simulations",
        type=int,
        default=mcts_defaults.simulations,
        help="Number of MCTS simulations to print.",
    )
    parser.add_argument(
        "--c-puct",
        type=float,
        default=mcts_defaults.c_puct,
        help="PUCT exploration constant.",
    )
    parser.add_argument(
        "--after-declaration",
        action="store_true",
        help="Advance the root to the state immediately after Japan declares war.",
    )
    parser.add_argument(
        "--add-root-noise",
        action="store_true",
        help="Apply Dirichlet root noise before running the debug search.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/mcts_debug_trace.txt"),
        help="Optional file to write the trace to.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = gwrl_cpp.JapanTrainingEnv(str(args.scenario), args.tracked_nation)
    root_notes = advance_to_purchase_phase_if_requested(env, args.after_declaration)

    checkpoint_path = args.checkpoint if args.checkpoint.exists() else None
    model = build_model(env, checkpoint_path)
    config = MctsConfig(
        simulations=args.simulations,
        c_puct=args.c_puct,
    )
    result, debug_trace = run_mcts_with_debug(
        env,
        model,
        config,
        add_root_noise=args.add_root_noise,
    )
    output_text = format_trace(env, checkpoint_path, config, root_notes, result, debug_trace)
    args.output.write_text(output_text + "\n", encoding="utf-8")
    print(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
