# Training studies

Start with the study you want to read or run:

| Study | Main entry point | Preserved completed results |
| --- | --- | --- |
| [Regional campaign](/Users/home/Desktop/gwRL/studies/campaign/README.md) | `python -m studies.campaign.run` | [M12 operational checks](/Users/home/Desktop/gwRL/docs/m12/README.md), no trained-strength result |
| [Composition](/Users/home/Desktop/gwRL/studies/composition/README.md) | `python -m studies.composition.train` | [Results guide](/Users/home/Desktop/gwRL/studies/composition/results/README.md) |
| [Mini Japan, two turns](/Users/home/Desktop/gwRL/studies/mini_japan_two_turn/README.md) | `python -m studies.mini_japan_two_turn.train` | [Results guide](/Users/home/Desktop/gwRL/studies/mini_japan_two_turn/results/README.md) |

Run commands from the repository root using `./.venv/bin/python`. There is no
longer a flat `python/` script collection or a `PYTHONPATH=python` requirement.

```text
studies/
  campaign/
    run.py                   Foreground train, resume, evaluate and profile
    neural.py                Complete entity-graph policy and vector value heads
    learning.py              Frozen three-policy parallel batches and exact resume
    runs/                    Ignored local checkpoints, progress and reports
  composition/
    train.py                 Attacker/defender self-play trainer
    mcts.py                  Alternating-player search
    results/                 Preserved completed run and provenance
    runs/                    New local runs, created only when needed
  mini_japan_two_turn/
    train.py                 Main neural policy/value + MCTS trainer
    mcts.py                  Single-agent search with optimistic FPU
    tools/                   Reusable MCTS trace diagnostic
    results/                 Preserved completed optimistic-FPU run
    runs/                    New local runs, created only when needed
  shared/
    policy_value_model.py    Neural model used by both studies
    paths.py                 Shared data paths and fresh output destinations
```

The studies share the C++ engine in `src/` and `include/game/`. The mini-Japan
scenario stays in `game_content/scenarios/china_simplified_setup.json`, so the
Python trainer and C++ debug program use the same setup rather than copies.
Composition's budgets/terrain remain trainer options. Its alternating-player
MCTS and Japan's single-agent MCTS intentionally remain separate algorithms.

## Results versus scratch output

- `results/final_run/` preserves the latest completed run for that study,
  including metrics, learning curves and best-play traces. These are a coherent
  report of the run, not abandoned intermediate runs.
- The result guides explain historical engine differences and checkpoint limits.
  Japan saved final-episode weights; its best-checkpoint text file is only a
  trace. Composition saved no trained model weights.
- New training and diagnostic commands default to fresh timestamped/unique
  `runs/` directories, ignored by Git. They do not overwrite curated results.
  `--output-dir` can explicitly select another destination; avoid an existing
  `results/final_run` path unless overwriting it is intentional.
- Root `output/` is reserved for disposable C++ simulator/debug exports. It no
  longer stores the training study results.

## Cleanup record — 12 September 2026

Moved the usable trainers, search modules, shared model, trace diagnostic and
search regression into the structure above. All 15 retained final-run files were
checksum-verified before/after relocation; their original bytes were preserved.
Algorithms, model parameter names and training hyperparameters were not changed.
Verification: all 81 Python tests and the C++ combat regression pass. The two
main trainers and MCTS diagnostic pass CLI `--help` checks;
no training or diagnostic search was executed.

Removed one-off intermediates:

- `python/tools/audit_policy_drift.py`: superseded diagnostic training loop.
- `python/tools/training_example_summary.py`: unused C++ export-summary helper.
- `output/policy_drift_audit.txt` and `output/save.txt`: diagnostic report and its
  scratch episode trace, not a completed training result bundle.
- Obsolete `python/` bytecode caches and Finder metadata, then its empty folders.
- The Q-learning baseline (`python/train_japan_q_learning.py` originally) and
  older Japan comparison run (`output/japan_old/` originally), removed after
  the user explicitly approved both deletions.

The removed source/report files and older comparison run are recoverable from Git commit
`2701c5530ab31251f5e4a3731f8494e288d9f47a` under their original paths. Caches and
Finder metadata are regenerable. No commit, game-content deletion, environment
removal, engine change or training run was made as part of this cleanup.
