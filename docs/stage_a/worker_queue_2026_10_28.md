# Ten workers and a game queue — 28 October 2026

The [production-like benchmark](production_benchmark_2026_10_28.md) named two
quick wins: run ten game processes instead of eight, and start a new game as
each one ends. This measures both together at the same settings. The
[evidence JSON](worker_queue_2026_10_28.json) records settings, per-game times
and provenance; raw outputs remain under
`studies/campaign/runs/worker-queue-2026-10-28/`.

**Result: 34.9 completed three-round games per hour, against 32.0 on eight
processes, a 9% gain rather than the expected 40%.**

## What changed

Training already handed each game to whichever worker was free, so a batch
with more games than workers needed only a setting. The self-play benchmark
instead dealt games into one fixed group per process. It now queues one game
per task, as training does, counts busy cores by process rather than by game,
gives queued games the cohort's absolute deadline, and reports which process
played each game and how busy the processes were.

## Measurement

Thirty games (seeds 1951–1980) on ten processes, hidden size 64, two message
layers, 16,384 token buckets, 64 simulations, depth cap 16, three-round games,
per-search evaluation with one tensor thread per process.

| Measure | Eight processes, eight games | Ten processes, thirty games |
| --- | ---: | ---: |
| Wall time | 900.3 s | 3,090.2 s |
| Completed games per hour | 32.0 | 34.9 |
| Process utilization | 83.2% | 86.5% |
| Mean game time, same eight seeds | 749.5 s | 858.0 s |
| Peak charged memory, process tree | 7.47 GB | 10.17 GB |

The eight seeds common to both runs produced identical games, so the
comparison is exact. Two effects explain the shortfall:

1. **More busy cores run each game slower.** The Apple M4 Max has ten
   performance cores in two clusters of five that share a 16 MB L2 cache, and
   all-core clocks are lower than few-core clocks. The same eight games took
   14.3% longer with ten processes busy, so two more processes add about 9% of
   capacity, not 25%.
2. **A cohort still ends with a tail.** All ten processes stayed busy for 36
   minutes; the last game started at 2,148 s and the final fifteen minutes ran
   with fewer and fewer processes busy, leaving 14% of process time idle. Three
   games per worker is too few to hide the spread of game lengths.

## Consequences

- Ten workers remain the better setting: 10 / 858.0 s against 8 / 749.5 s per
  game is 9% more throughput on identical games.
- Training batches carry the same tail at every update. More games per batch
  shrink it; overlapping the next batch with the tail would remove it but
  changes the learning algorithm, because those games would use the previous
  weights.
- Faster rules and search are the larger lever. Engine and search work were
  55% of time at these settings.
