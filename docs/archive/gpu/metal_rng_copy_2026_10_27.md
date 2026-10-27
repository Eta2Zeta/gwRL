# Parallel RNG arena copying

The exact parallel RNG-copy path reduced its separately fenced stage at every
measured batch. Whole-transition medians showed no gain at one lane, about
5.1% lower time at 64 lanes and 8.8% lower at 512. These are two sequential
operation-level grids; small differences include timing variation and establish
no full-game, search or training throughput.

The [curated evidence](metal_rng_copy_2026_10_27.json) pins both raw artifacts,
complete runtime/native/environment provenance, all source/output/capacity
witnesses, CPU controls and guards. Both grids use parallel editor/container,
unit-parallel JSON, unrolled SHA and certified-source reuse. Only the explicit
`random_implementation` selection changes. The default remains the existing
editor-policy choice.

Pooled median milliseconds across four families and three unfenced repetitions:

| Lanes | GPU reference RNG copy | GPU parallel RNG copy | Parallel / reference |
|---|---:|---:|---:|
| 1 | 43.068 | 43.200 | 1.003× |
| 64 | 54.333 | 51.555 | 0.949× |
| 512 | 98.794 | 90.099 | 0.912× |

Separately fenced RNG-stage medians change from 2.398 to 1.007 ms at B1,
5.160 to 1.081 ms at B64 and 7.634 to 2.222 ms at B512. Fences are intrusive;
stage medians do not sum to the whole-transition median. In particular, the
unrelated B512 effects profile varied from 98 to 37 ms between grids, much more
than the whole-step difference. That change cannot be attributed to RNG copying.
The runs were sequential, with no interleaved order control or confidence interval.

Both grids measured original native serial and persistent ten-worker controls:

| Lanes | Native serial, reference / parallel grid | Native pool, reference / parallel grid |
|---|---:|---:|
| 1 | 0.809 / 0.858 ms | 0.902 / 0.895 ms |
| 64 | 52.369 / 49.158 ms | 21.551 / 24.647 ms |
| 512 | 399.656 / 388.469 ms | 151.577 / 155.878 ms |

At B512 the parallel-copy GPU handler takes 0.232 of its serial control time
and 0.578 of pool time. GPU still loses to both controls at B64. The pool is an
explicit diagnostic, not automatic parallelism in production CPU search. Timer
inclusions/exclusions match the earlier complete-transition reports; every raw
control and its separate setup/verification timings remain pinned.

All 24 cases passed full native State/history/RNG/Engine-key checks. Across
modes the same 12 source fixtures, capacities, source buffers, complete output
records and native serial/pool keys match exactly. Each case had five immutable-
source certificate hits and zero misses; this does not predict chronological
cache hit rates. No field, unit, legal choice, lane or dice result was dropped.

Both runs used clean frozen `0371943`, verified native `61316df7…` and the same
Torch 2.14.0 environment. All 109 frozen native/build inputs exactly match its
saved build proof. Runtime imports/assets/source hashes were verified; fallback
and fast math were disabled. The reference/parallel runs took 68.41/67.41 seconds
and charged peaks of 6.358/6.352 GB including the full 3 GB MPS reservation. Each
stayed below the 7 GB stop threshold inside its 8 GB/180-second guard and used
at most ten native workers plus two tensor/coordinator threads.
