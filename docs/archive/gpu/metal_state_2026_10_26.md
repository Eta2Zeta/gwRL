# Apple GPU state foundation — 26 October 2026

Commit `519ae61` adds lossless device state copies, exact chance sampling, income
ledger accounting and declaration-offer passing. CPU remains the default. These
are working components; the complete GPU campaign transition backend and GPU tree
search are still being implemented. The user selected this Mac's Apple GPU;
12 CPU cores and 30,000,000,000 bytes remain the resource limits.

The [evidence](metal_state_2026_10_26.json) preserves complete benchmark settings,
native/runtime/tool hashes and artifact witnesses. Both benchmarks ran alone,
sequentially, on the optional PyTorch 2.14 environment. They measure components,
not completed games or learning strength. The earlier full-game comparison remains
[recorded separately](gpu_backend_2026_10_26_results.md).

## Exact sampling

One Metal dispatch implements native SplitMix64 arithmetic, unbiased rejection
sampling, three independent streams, conditional rerolls and test-tape cursors.
Failures preserve input randomness and clear partial outputs. Every sampled face,
effective result and final RNG bit matched native C++ in these workloads.

| Independent lanes, 16 dice each | Native time/batch | Warm GPU time/batch | Native/GPU ratio |
|---|---:|---:|---:|
| 4 | 19.2 microseconds | 324.1 microseconds | 0.059× |
| 256 | 1.848 ms | 0.682 ms | 2.71× |
| 4,096 | 30.906 ms | 1.250 ms | 24.72× |

Each configuration repeats 20 times from identical snapshots. Packing, upload,
cold compilation and inspection are outside the warm ratio and reported
separately. At 4,096 lanes, host packing took 0.589 s, upload 0.00452 s and explicit
inspection/verification 0.141 s. Keeping requests/state resident is essential.
The entire benchmark took 2.82 s, with a conservative 2.43 GB guard charge that
includes a full 2 GB GPU allocator reservation.

## Complete state copies

Direct native field visitors preserve all mutable fields, opaque rule payloads,
pending decisions, battle continuations, history and all random state. Immutable
definition/catalog data and exact interned strings are shared. Floating values
are transported as integer bit words, avoiding unsupported MPS float64. GPU forks
copy complete records and metadata without a host state read.

The benchmark compares the existing Python loop over native `raw.clone()` with a
resident batched gather, using opening, first-chance and second-round Japanese
combat-movement positions. Each case repeats one real source position. It is an
ordinary independent clone: search reseeding/tape removal are a subsequent unit.

| 256 copies of position | Native clone loop | Warm GPU gather | Native/GPU ratio |
|---|---:|---:|---:|
| Opening | 6.090 ms | 1.210 ms | 5.03× |
| First chance | 7.210 ms | 1.224 ms | 5.89× |
| Round-two Japanese combat movement | 25.821 ms | 2.650 ms | 9.74× |

One/four-lane cases often favor native C++; all 1/4/16/64/256 sizes, cold timings,
initial native capture, upload and inspection are retained in the evidence. The
CPU baseline includes one Python/native call per clone, while the candidate is a
bulk device operation. Every copied record/length/section was checked, with full
native state/RNG/history restoration witnesses. The benchmark took 41.68 s and
stayed inside its 8 GB envelope, including a full 3 GB GPU reservation.

## Correctness guard and continuing work

The original PyTorch 2.11 MPS implementation corrupts large int64 payloads in
`index_select`: for example 4,294,967,295 becomes 4,294,967,296. The new full-state
tests caught two failures before this path was enabled for training. CPU remains
supported in that environment. GPU state/scheduler initialization now probes
exact sentinel bits once and rejects an unsuitable runtime with guidance to the
tested isolated environment; it never substitutes CPU or casts away bits.

The current implementation passed 58 distinct focused checks across overlapping
runs on 2.14, and 27/27 native suites. In the original environment the same 58
checks passed with nine unsupported MPS cases skipped (49 executed successfully).
This includes rich pending-state round trips, raw double/uint64 extremes,
declaration menus/offer order, stale selections, payment-once/overflow behavior,
conditional dice/tape failures and source-provenance coverage.

Next work connects packed-state edits, exact search reseeding and direct
state-to-ledger/sampling kernels. General movement, legal menu construction,
combat, politics, hooks, observation construction and tree traversal still need
device implementations before the GPU backend can execute complete campaigns.
