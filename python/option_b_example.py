from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_option_b_example(path: str | Path) -> dict[str, Any]:
    """Load a C++-exported Option-B training example JSON file."""

    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def summarize_option_b_example(path: str | Path) -> str:
    data = load_option_b_example(path)
    legal_actions = data.get("legal_actions", [])
    lines = [
        f"current_nation={data.get('current_nation')}",
        f"current_phase={data.get('current_phase')}",
        f"state_feature_count={data.get('state_feature_count')}",
        f"action_feature_count={data.get('action_feature_count')}",
        f"legal_action_count={len(legal_actions)}",
    ]

    for index, action in enumerate(legal_actions[:5]):
        lines.append(f"legal_action_{index}={action.get('description')}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    example_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/japan_option_b_example.json")
    print(summarize_option_b_example(example_path))
