"""Repository-relative data paths and separate destinations for new runs."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
STUDIES_ROOT = REPO_ROOT / "studies"
MINI_JAPAN_SCENARIO = REPO_ROOT / "game_content/scenarios/china_simplified_setup.json"


def default_run_dir(study_name: str) -> Path:
    """Return a fresh output path without creating files or overwriting results."""
    if study_name not in {"composition", "mini_japan_two_turn"}:
        raise ValueError(f"Unknown study: {study_name}")
    run_name = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}"
    return STUDIES_ROOT / study_name / "runs" / run_name
