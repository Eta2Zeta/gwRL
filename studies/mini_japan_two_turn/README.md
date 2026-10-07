# Mini Japan: two-turn study

The small six-zone Japan scenario with two turns per nation. Japan learns while
the other nations use the existing passive behavior. This is separate from the
planned July 1936–1941 full-rules campaign in `game_content/scenarios/japan_china_1936/`.

| Read | Purpose |
| --- | --- |
| [train.py](/Users/home/Desktop/gwRL/studies/mini_japan_two_turn/train.py) | Main PyTorch policy/value trainer with MCTS targets and replay |
| [mcts.py](/Users/home/Desktop/gwRL/studies/mini_japan_two_turn/mcts.py) | Single-agent MCTS, including optimistic unvisited-action values |
| [Scenario JSON](/Users/home/Desktop/gwRL/game_content/scenarios/china_simplified_setup.json) | Shared setup, geography, treasury and two-turn limit |
| [Results guide](/Users/home/Desktop/gwRL/studies/mini_japan_two_turn/results/README.md) | Preserved 500-episode optimistic-FPU run, plots, traces and final weights |
| [MCTS diagnostic](/Users/home/Desktop/gwRL/studies/mini_japan_two_turn/tools/debug_mcts_trace.py) | Inspect one search without retraining |

## Main training command

From `/Users/home/Desktop/gwRL`:

```sh
./.venv/bin/python -m studies.mini_japan_two_turn.train \
  --episodes 500 \
  --search-simulations 500 \
  --eval-every 5 \
  --seed 1936
```

This is a substantial run; the cleanup did **not** execute it. Output defaults
to a fresh `studies/mini_japan_two_turn/runs/<timestamp>-<id>/` directory. Use
`--output-dir` to choose another destination. No `PYTHONPATH` setting is needed.
`--scenario` can select a compatible alternative; by default both Python and
the C++ debug program use the canonical scenario linked above.

The archived run reached reward 9.0 under its historical combat implementation.
Subsequent engine corrections mean a new run is not guaranteed to match it.
`japan_torch_policy.pt` holds the final model, not necessarily the best model;
the best-checkpoint `.txt` file contains a trajectory, not saved weights.

## Optional diagnostic

These commands only show options; they do not train or run a search:

```sh
./.venv/bin/python -m studies.mini_japan_two_turn.train --help
./.venv/bin/python -m studies.mini_japan_two_turn.tools.debug_mcts_trace --help
```

The diagnostic defaults to the preserved final model and writes to a new local
run folder when executed. Its output describes that model acting in today's
engine, not a replay of historical combat. The main trainer can still optionally
check a C++ encoding example from root `output/japan_training_example.json`;
that export is not required for training.

The Q-learning baseline and older 500-episode Japan comparison result (reward
7.5) were removed at the user's request. Their originals remain recoverable
from Git commit `2701c5530ab31251f5e4a3731f8494e288d9f47a`, at
`python/train_japan_q_learning.py` and `output/japan_old/`, respectively.
