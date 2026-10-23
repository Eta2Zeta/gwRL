# Stage A: completed-episode campaign learning

Status: first completed-episode pilot complete, 23 October 2026. Stage A remains
an early learning experiment; it is not a completed playing-strength gate.

Eight real one-round self-play games finished in 346.62 seconds, with 386 decisions
and 52 chance events. All 386 training rows have observed terminal targets; none
are bootstrapped or dropped. Policy samples: Axis 90, Allies 96, Comintern 200
(the latter controls both CCP and Mongolia turns). Two frozen-policy generations
performed 32 sampled Adam steps per agent.

One calendar round finishes the CCP, Mongolia, Japan and KMT national turns.
These practice games deliberately end there; the full July 1941 campaign has
eleven rounds. A policy sample is one saved position with the search's preferred
probabilities over all its legal choices. For example, one actual Japan research
position has 17 choices: finish research 50%, airborne doctrine 25%, heavy armor
25%, and the other choices 0%. That entire position/distribution is one sample.
The percentages are action preferences from the small search, not measured win
rates. The 90 Axis samples are 90 recorded decisions across eight games.

The original 346.62-second run is the pre-optimization baseline. Its progress log
attributes 117.56 seconds to the two learning/update intervals, including their
checkpoint writes; the remaining 229.06 seconds includes search/play, reporting,
other saves and setup. It is not a measurement of rules execution alone.

The performance follow-up repeats the identical eight-game configuration in
**118.68 seconds, down from 346.62 seconds (2.92 times faster)**. All 386 policy
targets, terminal targets, actual actions and eight final game states match the
original run. The search budget remains four simulations at depth eight, and
each alliance still receives 32 learning steps. No larger training run was
launched. The optimized repeat spends 82.09 seconds in collection/search, 26.88
in learning, 6.90 saving checkpoints and 2.81 reporting. These new buckets are
separate invocation measurements, outside deterministic checkpoint state.

The fix shares immutable static context, reuses complete parsed feature graphs
and constant tensors, caches planning keys until state changes, and skips the
unused action graphs of other alliances during learning. It retains every state
field and legal choice; learned embeddings and predictions still recompute.
The tensor-data cache has a 32 MiB payload limit; source-graph caches are bounded
separately by entry count. Floating-point accumulation order changes weights,
so old and optimized training are not bitwise identical. Across all 386 saved
positions, the final models' largest action-probability difference is 1.20e-7
and raw score-prediction difference is 3.58e-5. Exact interrupt/resume under the
optimized runtime passes. All 241 Python tests and 24 C++ suites pass.
See [the performance measurements](performance_2026_10_23.json). This single
repeat measures the pilot, not full-campaign or deeper-search throughput.

Held-out comparison uses the same scripted opponents, two unseen dice seeds
(40009/40013), 4 simulations, depth 8, no root noise and identical initial states:

| Alliance | Completed games: initial → trained | Mean own terminal gap: initial → trained | Own value MSE: initial → trained |
| --- | --- | --- | --- |
| Axis | 0/2 → 2/2 | unavailable → 44.95 | unavailable → 7.60 |
| Allies | 2/2 → 2/2 | -55.85 → -55.85 | 3948.43 → 22.06 |
| Comintern | 2/2 → 2/2 | -84.15 → -84.15 | 10548.18 → 50.48 |

The initial Axis policy toggles one battlecruiser's raider status repeatedly.
A diagnostic evaluation guard stops collection after 20 occurrences of a full
planning state. Those two games remain unfinished: they receive no terminal
score, loss or calibration error. The trained model completes all six games
without triggering the guard, with the same terminal states and scores as evaluation
before the guard was added. Per-simulation search cycle handling corrects visit
counts; it does not prevent an actual policy from repeating legal actions.

The observed improvement is completion behavior and outcome prediction. Allies/
Comintern scores did not improve on these two dice seeds. Eight training games
and one training seed do not establish robust strategic strength. The next
step is to measure representative deeper-search and longer-horizon throughput
before larger training. Then expand one-round learning and evaluation across
several seeds before claiming strategic strength.

The completed run includes 19 purchases, 35 land moves and 12 land-battle starts,
but demonstrates no naval movement/combat learning. All 230 Python tests and 24 C++
suites pass after the preparation/diagnostic fixes.

The user authorized actual Stage A
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
verification and pilot results are saved here; the original checkpoints are
preserved. A reviewed evaluation-only source-hash migration created separate
checkpoint copies without changing any learner, optimizer, replay, game or RNG
state.

- [Training and per-episode results](training_2026_10_23.json)
- [Performance follow-up and identical-workload repeat](performance_2026_10_23.json)
- [Paired comparison and limits](comparison_2026_10_23.json)
- [Initial-model evaluation](evaluation_initial_2026_10_23.json)
- [Trained-model evaluation](evaluation_final_2026_10_23.json)
- [Evaluation-only checkpoint migration](evaluation_guard_migration_2026_10_23.json)
- [Preflight validation and resource plan](preflight_2026_10_23.json)
