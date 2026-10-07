# Composition study

Train an attacker and defender to choose army compositions within their budgets,
then resolve the battle with the shared C++ engine. This is the current
composition self-play code, not an intermediate trainer.

| Read | Purpose |
| --- | --- |
| [train.py](/Users/home/Desktop/gwRL/studies/composition/train.py) | Training configuration, two policy/value networks, self-play, updates and reports |
| [mcts.py](/Users/home/Desktop/gwRL/studies/composition/mcts.py) | Alternating-player MCTS and optimistic first-play urgency |
| [Results guide](/Users/home/Desktop/gwRL/studies/composition/results/README.md) | The preserved 1,000-episode completed run and what each output means |

## Commands

From `/Users/home/Desktop/gwRL`:

```sh
./.venv/bin/python -m studies.composition.train --help
```

To start a new run using the saved run's principal settings:

```sh
./.venv/bin/python -m studies.composition.train \
  --episodes 1000 \
  --search-simulations 1000 \
  --eval-every 10 \
  --attacker-budget 50 \
  --defender-budget 30 \
  --terrain normal \
  --seed 1936
```

This is a substantial run; the cleanup did **not** execute it. New output goes
to a fresh `studies/composition/runs/<timestamp>-<id>/` folder by default.
An explicit `--output-dir` overrides that destination.

The preserved result predates combat-rule corrections. The command uses today's
shared engine, so it is not a promise to reproduce the archived score. The
current trainer still saves metrics, plots and traces but **no model weights**;
organizing it did not add checkpointing or change its algorithm.
