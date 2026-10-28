# Production-like benchmark — 28 October 2026

Earlier speed work used a 16-wide, one-layer network and 16 simulations. This
sets a production-like baseline with the project's larger default network and a
four times larger search. The [evidence JSON](production_benchmark_2026_10_28.json)
records settings, timings and provenance. Raw outputs and the network script
remain under `studies/campaign/runs/production-benchmark-2026-10-28/`.

**Baseline: 32.0 completed three-round games per hour on eight processes, with
the network taking 45% of the time and the engine and search 55%.**

## Settings

Hidden size 64, two message layers, 16,384 token buckets (about 1.14 million
parameters per alliance), 64 simulations, depth cap 16, three-round games,
per-search evaluation with one tensor thread per process, seeds 1951–1958 on
eight processes. The benchmark tool now accepts any simulation count, depth
and horizon from one to eleven rounds.

## Network cost by size

Milliseconds per position on 64 real positions, mean menu 73 actions:

| Network | Parameters per alliance | CPU, 1 thread | Apple GPU, batch 1 | Apple GPU, batch 8 | Apple GPU, batch 32 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 16 wide, 1 layer, 2,048 buckets | 38 k | 5.0 | 11.1 | 5.5 | 4.7 |
| 64 wide, 2 layers, 16,384 buckets | 1.14 M | 13.0 | 12.0 | 6.4 | 5.5 |
| 128 wide, 3 layers, 16,384 buckets | 2.50 M | 29.8 | 13.3 | 7.9 | 7.1 |

Batching never helps on CPU. On the GPU it helps substantially, and at batch 32
the larger networks cost 2.2 and 4.1 times less per position than one CPU
core. Roughly 4.5 ms per position is CPU-side input preparation that neither
the GPU nor batching removes.

## Production-like self-play

| Measure | Value |
| --- | ---: |
| Eight games, wall | 900.3 s |
| Completed games per hour | 32.0 |
| Game times | 538–900 s |
| Average busy cores | 6.68 |
| Peak memory, whole process tree | 7.47 GB |
| Network per evaluated position, including preparation | 14.4 ms |
| Engine and search per evaluated position | 17.4 ms |

The spread in game times leaves about a sixth of worker time idle while the
longest game finishes. Each configuration ran once. A sample of full-length
eleven-round games is still needed to measure later-phase costs.

## Where speed can improve next

Ordered by expected gain for the effort at these settings:

1. **Use all ten performance cores.** Ten workers instead of eight fit in memory
   at about 0.95 GB each: roughly 20–25% more games per hour.
2. **Queue more games than workers.** Starting a new game as each one ends
   recovers most of the one-sixth tail idle in training batches.
3. **Reuse the search tree between moves.** Each decision now starts a fresh
   tree. Keeping the chosen move's subtree carries its simulations forward.
4. **Batch network work on the GPU.** Workers would keep input preparation and
   send prepared positions to one GPU process. At this size the arithmetic is
   about 8 of the 14.4 ms per position; at 128 wide it is about 25 ms.
5. **Cut input preparation.** The 4.5 ms per position applies at every size and
   device.
6. **Rebuild the engine's hot data structures.** Legal-move generation is
   mostly allocation and text comparison, and engine work grows with the
   simulation count.
7. **Need fewer simulations.** Gumbel-style root search is designed for small
   budgets. Equal learning at a quarter of the simulations would beat any
   implementation speedup, but it must be shown by learning comparisons.

A cheaper state fingerprint would add a few percent. Production searches and
networks are not settled; 64 simulations and the 64-wide default are a
measurement baseline, not a recommendation.
