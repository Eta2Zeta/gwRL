# Process-parallel self-play — 28 October 2026

This follow-up to [search scheduling and shared menus](cpu_scheduling_2026_10_28.md)
splits self-play games across processes so each has its own Python interpreter
lock. Rules, search budgets, models and dice are unchanged. The
[evidence JSON](cpu_processes_2026_10_28.json) records settings, hashes and
timings. Raw outputs remain ignored under
`studies/campaign/runs/cpu-processes-2026-10-28/`.

**Result: eight games on eight processes complete in 102 s, 282 games per hour,
six times the original 47.4. Every game matched its single-process result
exactly.**

## Method

`tools/benchmark_campaign_devices.py --processes N` deals the cohort's seeds
round-robin to N spawned processes. Each process builds the same fresh weights
and the coordinator checks their digests. Games use per-search evaluation with
one tensor thread, so a game's result does not depend on which games share its
process. Cohort wall time runs from the first process's start to the last one's
end.

## Scaling

Seeds 1951–1958, 16 simulations, depth cap 16, hidden size 16 and one message
layer. The ten-process run adds seeds 1959–1960.

| Configuration | Games | Wall | Games/hour | Busy cores | Peak memory |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original batched baseline | 4 | 303.7 s | 47.4 | 1.64 | 1.09 GB |
| One process, per-search | 8 | 440.2 s | 65.4 | 2.82 | 1.33 GB |
| Two processes | 8 | 226.2 s | 127.3 | 3.69 | 2.60 GB |
| Four processes | 8 | 153.8 s | 187.3 | 4.62 | 4.03 GB |
| Eight processes | 8 | 102.0 s | 282.4 | 6.45 | 5.94 GB |
| Ten processes | 10 | 119.5 s | 301.4 | 7.50 | 7.71 GB |

Every game in every multi-process run had the same trace, final state and
execution RNG as the one-process run. Memory costs about 0.75 GB per game
process, well inside the 30 GB allowance.

With one game per process, the cohort waits for its longest game, and finished
processes sit idle. Eight processes therefore averaged 6.45 busy cores, not
eight. Ten processes added little over eight on this 10-performance-core
machine.

## Training integration plan

Training does not use this yet. `CampaignLearner.collect_many` advances its
games together, and all of them draw search seeds and action samples from the
learner's two shared random streams. Each game's randomness therefore depends
on the others, so they cannot simply be split.

1. **Per-game random streams.** Give each game slot its own search and sampling
   streams, derived from the learner seed and the slot's episode count, and
   save them in checkpoints. This changes rollout randomness, not the method,
   so it applies to new runs. Existing checkpoints keep the current collector.
2. **Game worker processes.** Each worker holds one game and runs per-search
   evaluation with the batch's frozen weights, sent once per batch. Between
   checkpoint boundaries it returns training samples, events and its serialized
   game state.
3. **Coordinator responsibilities.** The main process labels terminal values,
   starts replacement games so no worker idles, writes recovery checkpoints and
   runs learning updates.
4. **Configuration.** A run option such as `collection_processes` defaults to
   the current collector and is recorded in run manifests. A resume refuses a
   different collector mode.
5. **Verification.** One worker must match N workers exactly, and a resumed
   batch must match an uninterrupted one. Then measure complete training runs,
   including updates and checkpoints, for completed games per hour and
   aggregate peak memory.

Numerical replay inputs must cross processes without duplicating the large
shared context, and replay viewer events must come back with each chunk.
Continuous game replacement should also raise utilization above the 6.45 cores
measured here.

Each configuration ran once, without confidence intervals.
