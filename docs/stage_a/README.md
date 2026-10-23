# Stage A: completed-episode campaign learning

Status: pilot preparation, 23 October 2026. The user authorized actual Stage A
learning and up to 80% of available compute cores. This Apple M4 Max exposes 14
CPU cores; the configured CPU budget is 11, rounded down from 80%. Four search
workers, four tensor threads and one coordinator fit a conservative 9-thread
budget. BLAS/tensor environment limits are explicit; accelerator training is
not used in this pilot.

The first experiment uses the unchanged approved 99-piece/37-node setup and rules,
with an explicit one-round calendar (four national turns). Four independent
games form one frozen-policy batch. All three alliance policies remain frozen
until every game finishes; then 16 sampled optimizer steps train all three models.
Two batches target eight completed self-play games. This is a first learning
pilot, not a playing-strength or full July 1941 result.

`--complete-episodes` adds the episode-complete mode. Its transition guard saves
all frozen policies, pending rows, already-completed rows and game/RNG state
without an update or bootstrap label. It exits 2 with `episode_budget_exhausted`.
An explicit monotonic `--extend-episode-budget` can increase only this execution
guard on resume. It does not change the game horizon or objective. The existing
bounded-segment mode remains available for explicitly bootstrapped experiments.

Every fresh run archives `initial.pt` before any action/update for paired held-out
evaluation. Progress includes actual action kinds/parameters, entitled actors,
per-root clocks/completion and real terminal returns. Updates report per-actor
policy samples, so a changed value head alone cannot stand for policy learning.
Full static rules context is shared as immutable source JSON across replay rows;
all observations/actions/fields remain intact.

Pilot command from the repository root:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 VECLIB_MAXIMUM_THREADS=4 PYTHONHASHSEED=0 \
./.venv/bin/python -m studies.campaign.run train \
  --run-dir studies/campaign/runs/stage-a-one-round-2026-10-23 \
  --seed 1951 --complete-episodes --calendar-rounds 1 --batches 2 \
  --transitions-per-batch 1500 --parallel-envs 4 \
  --simulations 4 --max-depth 8 --hidden-dim 16 --message-layers 1 \
  --token-buckets 2048 --batch-size 32 --epochs 16 --replay-capacity 16384 \
  --threads 4 --cpu-budget 11 --checkpoint-every-waves 32
```

The small model/search settings are measured pilot choices, not tuned strengths.
Keep real terminal outcomes, retained samples by alliance, observed losses,
completion/stall rates and execution cost separate from strategic improvement.
Compare the final and initial checkpoints with identical frozen opponents,
search budgets and unseen dice before drawing any learning conclusion.

Preparation fixes, with regressions:

- MCTS stops at the first repeated planning state within one simulation and
  bootstraps the frozen value. A cycle cannot count that simulation repeatedly
  in root visit targets. Legal choices and chance probabilities are unchanged.
- Landing actions omit already-grounded identity actions while preserving
  in-flight returns, screening status and transfers to other carriers.
- Replay shares immutable complete context; Torch/deepcopy/restore retain the
  sharing and caller mutation cannot change a stored sample.

Large checkpoints and raw progress remain in ignored local `runs/`. Curated
verification and pilot results are saved here after the foreground run.
