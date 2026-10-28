# CPU search scheduling and shared menus — 28 October 2026

This follow-up to the [CPU self-play profile](cpu_profile_2026_10_28.md) removes
two measured costs without changing rules, search budgets, models or dice. The
[evidence JSON](cpu_scheduling_2026_10_28.json) records settings, hashes, timings
and equality checks. Raw outputs and measurement scripts remain ignored under
`studies/campaign/runs/cpu-scheduling-2026-10-28/`.

**Result: the same four games now take 238–247 s instead of 304 s, and eight
games reach 65.4 completed games per hour versus 47.4.** Every game in every run
below matched its comparison exactly, including complete traces, final states
and execution RNG.

## Changes

- **Shared menus across clones (C++).** Engines cloned from one game share a
  bounded table of 64 immutable legal menus keyed by the complete planning key.
  A search clone reaching a state another clone expanded no longer regenerates
  its menu, including inside `step`'s legality check. Payload validation is
  unchanged, and restored or separately constructed engines get their own table.
- **Per-search evaluation (Python).** `search_many(evaluation="per_search")` lets
  each search thread evaluate its own positions one at a time, so no game waits
  for the slowest game or for a shared evaluation round. Batched evaluation
  remains the default and the only mode allowed for accelerators.

Batching was not worth keeping on CPU. One position costs 4.22 ms alone and
4.21 ms in batches of four with one tensor thread. Batch makeup also changes
float32 outputs slightly: 374 of 404 tested rows differed from their
single-position result, by at most 8.9e-8 in priors and 2.7e-5 in values.
Single-position evaluation makes each game independent of thread timing and of
how many games run together.

## Matched results

Four three-round games, seeds 1951–1954, 16 simulations, depth cap 16, fresh
fixed weights (hidden size 16, one message layer). Eight-game runs add seeds
1955–1958.

| Configuration | Games | Wall | Games/hour | Busy cores | Peak memory |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline (batched, 4 tensor threads) | 4 | 303.7 s | 47.4 | 1.64 | 1.09 GB |
| Batched with shared menus | 4 | 270.8 s | 53.2 | 1.58 | 0.96 GB |
| Per-search, 1 tensor thread, run A | 4 | 238.0 s | 60.5 | 2.04 | 1.02 GB |
| Per-search, 1 tensor thread, run B | 4 | 247.1 s | 58.3 | 2.03 | 0.91 GB |
| Per-search, 1 tensor thread | 8 | 440.2 s | 65.4 | 2.82 | 1.30 GB |

Exactness checks:
- Shared menus with batched evaluation reproduced all four baseline games.
- Per-search runs A and B were identical.
- The first four games of the eight-game run were identical to the four-game run.
- In this workload, per-search games were also identical to the batched baseline.
  Tiny float differences could change a near-tie in other games, but each
  per-search game is reproducible on its own.

## Negative result: Python-only menu reuse

A Python-side cache of menus across clones was tried first. It cut native legal
generation from 233 s to 139 s, but applying moves rose from 73 s to 135 s and
numerical observation from 18 s to 44 s. The engine's legality check simply
rebuilt each menu internally, so the four games took 309.3 s. Garbage collection
was about 5 s with or without the cache. The C++ table replaces that attempt.

## Remaining limits

With eight games only 2.8 cores were busy. Engine calls run in parallel, but
Python search, adapter and network-input work share one interpreter lock.
Per-search games are now independent and exactly reproducible however they are
grouped, so splitting them across processes keeps identical results. This is
the next throughput step. Training does not use per-search evaluation yet; it
needs a learning configuration option and checkpoint-compatibility handling.
Each configuration ran once or twice, without confidence intervals.

Reproduce from the repository root, one heavy job at a time:

```sh
.venv/bin/python tools/benchmark_campaign_devices.py --mode selfplay --devices cpu \
  --search-evaluation per_search --threads 1 --seconds 1500 \
  --output studies/campaign/runs/NEW-RUN/per-search.json
```
