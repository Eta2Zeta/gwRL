#!/usr/bin/env python3
"""Play recorded games with trained networks, to watch in the Campaign Observatory.

Each game is a one-game run in its own process, starting from a model export's
weights, with the search and move sampling of self-play. The single learning
update that ends such a run is discarded. Every game is then replayed exactly
into OUTPUT/replays, which the viewer lists::

    tmp/gpu-mps-env/bin/python tools/record_campaign_games.py \\
      --models studies/campaign/runs/RUN/models/generation-000020.pt \\
      --output studies/campaign/runs/RUN/games --games 10 --workers 10 --seed 770000
    .venv/bin/python -m studies.campaign.viewer \\
      --directory studies/campaign/runs/RUN/games/replays
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]


def game_arguments(config: dict, models: Path, seed: int, run_dir: Path) -> list[str]:
    """One game in one batch, with the export's game, search and network."""
    arguments = ["-m", "studies.campaign.run", "train", "--run-dir", str(run_dir), "--record-replay",
                 "--initial-models", str(models), "--seed", str(seed), "--complete-episodes", "--batches", "1",
                 "--parallel-envs", "1", "--max-episodes", "1", "--transitions-per-batch", "20000"]
    for name in ("simulations", "max_depth", "hidden_dim", "message_layers", "token_buckets", "value_scale"):
        arguments += ["--" + name.replace("_", "-"), str(config[name])]
    if config["calendar_rounds"] is None:
        return [*arguments, "--full-campaign"]
    return [*arguments, "--calendar-rounds", str(config["calendar_rounds"])]


def play(index: int, config: dict, models: Path, seed: int, output: Path) -> dict:
    run_dir, replay = output / f"game-{index:02d}", output / "replays" / f"game-{index:02d}.json"
    environment = {**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                   "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}
    with (output / f"game-{index:02d}.log").open("w") as log:
        subprocess.run([sys.executable, *game_arguments(config, models, seed, run_dir)], cwd=ROOT, env=environment,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    exported = subprocess.run([sys.executable, "-m", "studies.campaign.replay", "--trace", str(run_dir / "replay.jsonl"),
                               "--output", str(replay)], cwd=ROOT, env=environment, capture_output=True, text=True,
                              check=True)
    return {"game": index, "seed": seed, **json.loads(exported.stdout)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", type=Path, required=True, help="Model export under a run's models/ folder")
    parser.add_argument("--output", type=Path, required=True, help="New folder for the games and their replays")
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--seed", type=int, required=True, help="First game's seed; choose one away from training seeds")
    args = parser.parse_args(argv)
    models, output = args.models.resolve(), args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Choose an empty output folder; existing games are preserved")
    config = torch.load(models, map_location="cpu", weights_only=False)["config"]
    (output / "replays").mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(args.workers) as pool:
        played = list(pool.map(lambda index: play(index, config, models, args.seed + index, output), range(args.games)))
    (output / "games.json").write_text(json.dumps({"models": str(models), "games": played}, indent=2) + "\n")
    print(json.dumps({"output": str(output / "replays"), "games": len(played),
                      "terminal": sum(game["terminal"] for game in played)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
