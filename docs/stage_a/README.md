# Campaign learning: current status

Stage A tests whether the complete campaign engine can support useful learning.
The latest continued experiment reached **120 completed three-round games and
30 learning batches**. It demonstrated resumable training at a measured scale;
**useful Japanese offensive play has not been demonstrated**. In the latest
held-out tests, Japan gained no new Chinese territory with either the network
alone or network-guided search. Losses and terminal wealth changed in mixed
directions. See the [latest results](../archive/stage_a/sixty_more_2026_10_25_results.md).

## What is implemented

- Three alliance policy/value networks guide Monte Carlo tree search. Each
  collection batch freezes all three policies while independent games run;
  learning updates follow the completed batch.
- The measured three-round setup used four concurrent games, 16 search
  simulations per decision, depth cap 16, and a small graph network with width
  16 and one message layer. These are experimental settings, not established
  optimal choices.
- Complete-episode training retains actual terminal results. A three-round game
  finishes after three full CCP–Mongolia–Japan–KMT rounds; the full campaign
  has eleven rounds. Search depth counts simulated transitions, not complete
  games. An execution cutoff leaves work unfinished rather than fabricating a
  terminal score.
- Native numerical inputs, decision reuse and independent C++ game execution
  are implemented. The CPU engine remains the complete self-play backend.
  [Apple GPU work](../gpu/README.md) currently covers selected services; full
  GPU game simulation and search remain unfinished.

## Performance and limits

The latest continuation retained **60 additional games and 15 updates** in
**1 h 57 min** of charged training, including recovery overhead: **30.74 retained
games per training hour**. The whole pipeline, including evaluation and downtime,
took **2 h 17 min**. This is one small-model, three-round experiment, not an
eleven-round or larger-search throughput estimate.

A memory-triggered rollback required recomputing 15 completed game executions
and four updates. Sampled peak charged memory was **26.01 GB**; live memory
growth remains a concern. The allowance is **12 CPU cores and 30,000,000,000
bytes**, including overhead. Current GPU component timings do not establish a
full-training speedup.

Eight held-out seeds and one continued initialization provide limited evidence.
Completion, faster generation and better score prediction do not by themselves
demonstrate stronger play. The next learning gate is reliable completion and
measurable behavior improvement under matched opponent, horizon, search and
compute budgets.

## Run, resume and evaluate

Use the [campaign workflow](../../studies/campaign/README.md) for current commands
and the [runner](../../studies/campaign/run.py) for CLI options. The plain runner's
default is a short bounded smoke; use `--complete-episodes` explicitly when
terminal-only learning is intended.

Small `models/generation-*.pt` exports support evaluation without loading the
optimizer, replay or unfinished games. Full recovery snapshots preserve all of
those continuation states, default to 30-minute intervals plus orderly shutdown,
and retain the preceding complete snapshot. Resume checks source, schema and
configuration compatibility; a model export alone cannot resume learning.

For an existing supervised experiment, use its saved `resume.sh` and immutable
plan. The [pipeline controller](../../tools/run_three_round_experiment.py) preserves
the run's deadline and resource accounting. Reusing an old command with a new
deadline would create a different experiment. Raw checkpoints and traces remain
in ignored `studies/campaign/runs/` directories.

Evaluate saved generations against the same fixed opponents and held-out seeds,
separately for network-only selection and search. Report actual new territory/IPP,
unit losses, terminal wealth and completion, including unfinished cases. The
[evaluation implementation](../../studies/campaign/evaluation.py) and
[supervised pipeline](../../tools/run_three_round_experiment.py) define the
current contracts. The [Campaign Observatory](../../web/campaign_viewer/README.md)
can show recorded play.

## Evidence

The [Stage A archive](../archive/stage_a/README.md) contains every earlier report,
launch record and curated JSON measurement. It is historical evidence; this page
and the workflow describe current status and operation.

Selected evidence:

- [Latest 60-game continuation and held-out results](../archive/stage_a/sixty_more_2026_10_25_results.md)
- [Original 60-game three-round experiment](../archive/stage_a/three_round_2026_10_25_results.md)
- [Matched complete-training numerical-input optimization](../archive/stage_a/numeric_training_input_2026_10_25.md)
