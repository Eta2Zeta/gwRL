"""Read the immutable pre-implementation map for historical audit reports."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
CHECKPOINT = "eeb5e9028d0f9efde087b3009d7f9613ce92f958"
MAP_PATH = "game_content/maps/gw36_manual_map.json"
MAP_SHA256 = "97061d40dacc5a23c570d063f21279c9aef24cd3f4533c166bb04fa241b61e24"


def read_baseline_map():
    result = subprocess.run(
        ["git", "show", f"{CHECKPOINT}:{MAP_PATH}"], cwd=ROOT,
        capture_output=True, check=False,
    )
    if result.returncode:
        raise RuntimeError("Historical audit requires checkpoint eeb5e90 in Git history; fetch that history before regenerating reports.")
    if hashlib.sha256(result.stdout).hexdigest() != MAP_SHA256:
        raise RuntimeError("Audit baseline hash mismatch")
    return json.loads(result.stdout)
