# Regional campaign learning

This study uses the approved 1936 China campaign and the shared C++ engine.
Three separate entity-graph policy/value networks guide vector MCTS. A rollout
batch freezes all three policies; training then updates all three together.
Each policy learns choices made by its actual alliance, including reactions and
controlled minors. Every value target retains `[Axis, Allies, Comintern]`.

The approved objective is the terminal wealth-gap vector. Intermediate rewards
are zero, gamma is one, and the network divides values by a positive scale
(default 100) for training, restoring raw units for search and reports. There are
no kill/purchase bonuses, clipping or alternating-player sign inversions.

Run commands from the repository root with the project virtual environment.
Rebuild the extension after C++ changes:

```sh
./.venv/bin/python setup.py build_ext --inplace --force
./.venv/bin/python -m studies.campaign.run --help
```

## Bounded foreground run and resume

The defaults are a small operational smoke: one batch, two independent games,
six real transitions per game, two simulations per search, and a small CPU model.
The one-round curriculum keeps the complete approved starting position and
rules, while ending after four national turns. A transition limit is separate:
unfinished games produce explicitly marked bootstrap targets. Neither is a full
July 1941 campaign result.

```sh
./.venv/bin/python -m studies.campaign.run train
```

The final line prints the new run directory. `progress.jsonl` is flushed after
each completed search wave and update, with counters and each game's calendar
clock. In another terminal, use the actual printed path:

```sh
tail -f studies/campaign/runs/YOUR_RUN/progress.jsonl
```

Press Ctrl-C in the training terminal to finish the current search wave, save
`checkpoint.pt` and mark `manifest.json` interrupted. Resume in the foreground:

```sh
./.venv/bin/python -m studies.campaign.run train \
  --resume studies/campaign/runs/YOUR_RUN/checkpoint.pt
```

`--stop-after-waves 2` provides the same safe boundary for a bounded resume check.
An interrupted run exits with code 130; a completed run exits with code 0.
Full recovery checkpoints default to every 1,800 wall-clock seconds and orderly
shutdown. Learning updates publish small model exports, without forcing full
recovery writes. An explicit `--checkpoint-every-waves N` overrides the timer for
controlled comparisons and recovery tests. A crash can resume the latest
completed recovery checkpoint. The manifest and checkpoint are
replaced atomically; the checkpoint is the authority if a crash occurs between
those two replacements. New runs refuse a nonempty directory and default to
unique ignored `runs/` directories.

Checkpoint bytes are flushed before replacement, and `checkpoint.pt.previous`
keeps the preceding complete snapshot. If the newest file is damaged, explicitly
resume that backup; the first recovery save preserves it instead of backing up
the damaged file. Abrupt interruption can lose games and learning updates since
the latest recovery point. Saving models separately does not preserve Adam,
replay or in-progress games; that is the tradeoff for infrequent recovery saves.

Checkpoints contain the live and frozen models, optimizer moments, replay,
pending samples, all active game states, declaration scheduling, all random
generators, counters, configuration, scenario/rule/schema fingerprints and
runtime source hashes. Resume rejects configuration, source or schema changes;
a changed implementation needs an explicit migration or a new run. Only load
trusted local Torch checkpoints produced by this runner. CPU thread count and
software versions are part of exact continuation compatibility.

For the authorized [three-round experiment](/Users/home/Desktop/gwRL/docs/stage_a/three_round_2026_10_24.md),
`tools/run_three_round_experiment.py --plan PLAN.json` orchestrates initial
evaluation, resource-supervised training and paired final evaluation. Its fixed
deadline persists across restarts. The run uses a committed runtime snapshot,
so edits in the main checkout do not break continuation. The lighter standalone
`tools/supervise_campaign_training.py` also supports a fixed active-time budget,
bounded transient retries and graceful resource/deadline stops; it reserves its
coordinator within the configured twelve-core allowance.

Native campaign calls now release Python's interpreter lock while executing
pure C++ work. Each Python-facing environment protects its own operations with
an independent mutex; clones get separate mutexes, so different boards can run
native operations concurrently. Overlapping operations on one board remain
serialized. This is per-call protection, not a transaction across several calls
on a shared Python adapter; search workers continue owning independent adapters.
Python JSON conversion and graph-compiler callbacks still require the interpreter
lock. The four-game search structure and sequential simulations within each
individual MCTS search are unchanged. Rebuild the extension after pulling this
binding change, as shown above.

## Completed-episode Stage A pilot

Add `--complete-episodes` to freeze a batch until each independent short game
reaches its true endpoint. Each new batch creates fresh games. Every row in this
mode receives an observed terminal target; a transition guard saves frozen pending
work without bootstrapping or updating and exits with code 2. Increase only that
execution guard explicitly when resuming with `--extend-episode-budget N`.
Small model exports live in `models/generation-000000.pt` and subsequent
generation files, starting before any action or update. `initial.pt` remains an
archive of the empty initial learner for compatibility. Add `--max-episodes 10`
with at least three batches and four parallel games to finish exactly ten games
in batches of four, four and two. The shorter tail batch changes random-stream
interleaving relative to four-root collection.

`--cpu-budget N` conservatively checks tensor threads plus parallel search workers
plus one coordinator against the available core budget. Set BLAS environment
limits as shown in the [Stage A pilot](/Users/home/Desktop/gwRL/docs/stage_a/README.md).
That page records the authorized core limit, exact foreground command and results.
The first eight-game pilot completed in 346.62 seconds with 386 genuine terminal
training rows. Complete-episode timing includes full games and optimizer steps;
the short six-transition default smoke is not a full-game runtime estimate.
Progress now also includes action kinds/parameters, terminal flags and real final
return vectors for each completed root.

The performance follow-up repeats that same pilot in 118.68 seconds (2.92 times
faster) with identical actions, policy targets and final game states. It reuses
immutable source features and skips unused policy work without reducing search.
Manifests now separate invocation time into collection/search, learning updates,
checkpoint saves, small model exports and reporting, and report collection transitions per second.
Timing stays outside deterministic checkpoint state. Full results and numerical
limits are in the [Stage A report](/Users/home/Desktop/gwRL/docs/stage_a/README.md).
The [scaling follow-up](/Users/home/Desktop/gwRL/docs/stage_a/scaling_2026_10_23.md)
now records 13 bounded cases: later positions, stronger search, a larger model,
parallelism comparisons and actual one/two/eleven-round collection. A small-budget
full campaign completes, but the 16-simulation two-round batch reaches its wall
limit before completing. The
[24 October decision-reuse pass](/Users/home/Desktop/gwRL/docs/stage_a/decision_reuse_2026_10_24.md)
removes repeated legal-menu and observation work. A matched full-game invocation
improves from 198.42 to 112.72 seconds with identical search results, choices,
dice and scores. These are frozen-policy collection timings, excluding learning
updates. Stronger collection still reaches its 240-second guard: 370 choices
completed versus 234 before the fix, with no completed two-round games.

`python -m studies.campaign.scaling_benchmark --help` describes the supervised
CPU-only benchmark. Its current resource envelope is 12 cores and 30 GB, with
separate wall/RSS guards and preserved progress on cutoff. It supports exact
round/nation/phase/decision-kind targeting, repeated searches on unchanged roots,
actual episodes, and explicit inference-only model-weight transfer from a
trusted local checkpoint. It never resumes old game/replay state or updates
weights. Fixed-root queries are not executed moves or training rows. See the
scaling report for measured results and reproduction commands.

The [native input compiler](/Users/home/Desktop/gwRL/docs/stage_a/neural_input_2026_10_24.md)
now constructs the same complete source graph in C++, retaining Python's exact
Unicode tokenization and numerical features. Reports identify the backend in
`software.graph_compiler`. Rebuild the extension after pulling this change;
the model architecture, input schema and learned-gradient behavior are unchanged.

Self-play now uses the versioned [AI order interface](/Users/home/Desktop/gwRL/docs/stage_a/action_interface_2026_10_24.md)
by default. Fleet and screening selection make forward progress; undo/cancel
editing is kept in the ordinary game API. Unchanged role/deck configuration
cycles and repeated declined railway requests are also bounded. Context and
checkpoint compatibility identify `campaign-orders-v1`; old replay/optimizer
state is not implicitly migrated. Explicit frozen model-weight transfers remain
available for comparisons, and historical recordings select their original
action interface for exact verification. Rebuild the native extension first.

RSS means **resident set size**: the physical memory currently occupied by a
process. The benchmark samples and sums the supervisor and worker RSS, reporting
the highest sampled total in bytes. For example, 2.58 GB means roughly that much
RAM was resident while the benchmark ran. Shared pages can be counted more than
once, and sampling can miss a brief peak; this is a memory estimate, not an
instantaneous allocation limit.

## Watch self-play

The [Campaign Observatory](/Users/home/Desktop/gwRL/web/campaign_viewer/README.md)
shows the actual game on a geographic schematic, with playback, location
inspection, dice, wealth and the search alternatives behind each choice.
Add `--record-replay` to a fresh training command, then run
`python -m studies.campaign.viewer --live-trace PATH_TO_RUN/replay.jsonl` and
enable **Follow latest**. Recording is optional and ordinary checkpoint resume
is unchanged; recording during resume is currently unsupported. Exported JSON
and standalone HTML can be reopened without running search or learning.

## Evaluation and profiling

Held-out evaluation keeps the target weights fixed, turns root noise off, and
uses the same versioned scripted opponents both inside search and during actual
play. The two baseline styles buy, move, attack and make reactions. They are
simple controls, with no claim of expert play. Each side is evaluated separately.
Seeds must differ from the base run seed and every logged training episode seed.
Evaluation accepts small model exports directly, without constructing a learner
or restoring its optimizer, replay and active games. Legacy recovery files remain
supported through full compatibility-checked restoration. Profiling retained
positions still uses a full recovery checkpoint.

```sh
./.venv/bin/python -m studies.campaign.run evaluate \
  --checkpoint studies/campaign/runs/YOUR_RUN/models/generation-000001.pt \
  --output studies/campaign/runs/YOUR_RUN/evaluation.json \
  --target all --seeds 1009,1013 --max-transitions 40
./.venv/bin/python -m studies.campaign.run profile \
  --checkpoint studies/campaign/runs/YOUR_RUN/checkpoint.pt \
  --output studies/campaign/runs/YOUR_RUN/profile.json --repeats 3
```

The default evaluation also stops collection after 20 visits to one full planning
state. This is reported as `repeated_state_guard`, an unfinished game with no
terminal score; changing search seeds or future dice might still allow escape.
The Python evaluation API can disable it with `max_state_visits=None`.

The evaluation budget is per game. Increase it explicitly to reach real terminal
states. Truncated games report their snapshot wealth and calendar, but contribute
no observed terminal returns, terminal wealth intervals or value-calibration
errors. Reports include all wealth components, territorial control, removed-unit
casualties, decisions by actor, throughput, inference batches and approximate
uncertainty for completed games. Very small samples do not establish strength.
For baseline-versus-baseline controls add `--target-script balanced` or `cautious`.

Profiling measures cloning, rule transitions, legal actions, observation/context,
and scalar/batched inference on actual retained states. Rule transitions use
clones and the report checks that live state and execution RNG are unchanged.
It includes first-use parsing and warm calls; menu size and game phase matter.

## Starting a larger experiment

Decision reuse, native graph construction and bounded AI order construction are
implemented. Next measure remaining rules/tensor costs and verify completion
across seeds and search budgets before expanding learning. The four-minute
16-simulation batch still reaches its guard. The order-interface report records
4/4 two-round completions in 310.09 seconds under a longer execution guard and
separates frozen-policy collection from actual
eight-game learning repeats, which include network updates and checkpoint writes.

The original small two-batch smoke took 14.30
seconds across stop/resume; 100 similar batches would take roughly 12 minutes
if position costs stayed comparable. The default larger model measured 247ms
per same-actor batch of four inference requests, before rules/search/updates.
These historical small-menu CPU measurements predate the performance/scaling
follow-ups and are not a current full-game duration estimate.

First inspect the smoke profile and choose a run size that fits foreground time
and memory. For the larger settings below, initially use one batch and six
transitions per batch (`--batches 1 --transitions-per-batch 6`), inspect the timing, then scale up
with a fresh run. A manual experiment command, to adjust after that pilot, is:

```sh
./.venv/bin/python -m studies.campaign.run train --full-campaign \
  --batches 10 --transitions-per-batch 32 --parallel-envs 4 \
  --simulations 8 --max-depth 16 --hidden-dim 64 --message-layers 2 \
  --token-buckets 16384 --batch-size 32 --replay-capacity 4096
```

This uses the unchanged eleven-round target. It may require many batches to
finish an episode; bootstrap provenance remains visible until a true terminal.
Measure completed games across held-out dice and opponent combinations before
making strategic claims. Archived opponent leagues, broader starting-position
curricula, direct-policy/PPO comparison and stronger settings are future
experiments, not results established by this operational gate.

See [M12 verification](/Users/home/Desktop/gwRL/docs/m12/README.md) and the
[full plan](/Users/home/Desktop/gwRL/docs/plans/japan_china_full_rules_plan.md).
