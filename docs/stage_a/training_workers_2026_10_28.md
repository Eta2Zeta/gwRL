# Training with episode worker processes — 28 October 2026

This applies [process-parallel self-play](cpu_processes_2026_10_28.md) to real
training. `--episode-workers N` plays each complete game in one of N worker
processes. The main process keeps learning updates, model exports and
checkpoints. The [evidence JSON](training_workers_2026_10_28.json) records
settings, per-game times and provenance. Raw runs and the measurement script
remain under `studies/campaign/runs/training-workers-2026-10-28/`.

**Result: real three-round training reaches 127.9 completed games per hour with
four workers and 218.7 with eight, versus 53.3 for the in-process collector.**

## Design

- **Own random streams per game.** A game's search seeds and move samples come
  from streams keyed only to the run seed and its environment seed. Games no
  longer draw from shared learner streams, so where or beside what a game runs
  cannot change it. This changes rollout randomness relative to earlier runs,
  which do not need to be reproduced.
- **Whole games per worker.** Each worker loads the batch's frozen weights on
  CPU, plays one complete game with single-position evaluation and returns
  terminal-labelled samples, events and summaries.
- **Batch boundaries.** Updates, exports and recovery checkpoints happen between
  batches. A stop request or the per-game transition guard discards the
  unfinished batch, kills its workers and rewinds the environment-seed stream,
  so a resumed run replays that batch exactly.

Replay recording still requires the in-process collector. The CPU budget counts
the larger of workers and tensor threads, plus one coordinator.

## Verification

- One worker and two workers produced identical games, samples and updated
  weights.
- Stopping after one batch and resuming gave the same counters, model versions,
  environment seeds, move history and replay targets as an uninterrupted run.
- The full suite passed except one timing-sensitive pipeline test, which passed
  when rerun on its own.

## Measured training

Two batches of complete three-round games with 16 simulations, depth cap 16,
hidden size 16, one message layer, four tensor threads for updates and an
11-core budget.

| Collector | Games | Wall | Collection | Updates | Checkpoints | Games/hour | Peak memory |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| In-process, 4 games per batch | 8 | 540.1 s | 525.8 s | 0.8 s | 1.9 s | 53.3 | 2.75 GB |
| 4 workers, 4 games per batch | 8 | 225.1 s | 222.6 s | 0.5 s | 2.0 s | 127.9 | 5.09 GB |
| 8 workers, 8 games per batch | 16 | 263.3 s | 260.9 s | 0.5 s | 1.9 s | 218.7 | 7.83 GB |

Each batch waits for its longest game. In the eight-worker run, game times in a
batch ranged from 64 to 123 s, so roughly a fifth of worker time was idle at the
batch tail. Playing more games than workers per batch, or starting the next
batch's games while the last one finishes, would recover part of that.
Learning updates remain under a second because the model is small.

Each configuration ran once. These numbers measure collection speed, not
learning strength.
