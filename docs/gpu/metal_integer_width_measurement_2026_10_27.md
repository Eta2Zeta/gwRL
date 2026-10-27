# Integer-width measurement

The narrowed magnitude is exactly correct, but the paired identity probe does
not establish a material speed benefit. Within-pair median changes were under
1% and the observed direction varied. The lower sequential complete-transition
medians cannot be attributed to this one-line change.

The [curated evidence](metal_integer_width_measurement_2026_10_27.json) pins both
fresh complete-step grids, the separate paired probe, native/source/environment
proofs, exact witnesses and guards. It includes the reproducible diagnostic
probe/guard sources. Earlier `0371943`/`ea82d1f` runs are not these baselines.

The helper already checks `INT_MIN..INT_MAX`. Negation still happens on guarded
`long`, so `-INT_MIN` is safely 2^31. Its nonnegative magnitude fits `uint`
exactly; only that magnitude and its casts changed. Separate UInt64 formatting,
including the full `playerTurnSerial` range, stays unchanged. Existing policies
and their selections did not change.

## Complete supported transitions

Milliseconds, pooled medians of four families and three unfenced trials:

| Lanes | Original `ulong` magnitude | `uint` magnitude | Candidate native serial | Candidate ten-worker pool |
|---|---:|---:|---:|---:|
| 1 | 41.019 | 40.111 | 0.866 | 0.968 |
| 64 | 48.186 | 47.051 | 49.986 | 22.919 |
| 512 | 89.756 | 85.010 | 384.685 | 151.800 |

These sequential changes are about 2.2/2.4/5.3%. The fenced identity stage,
however, changes only 18.887→18.764, 20.105→19.978 and 25.589→25.393 ms.
Unrelated stages and CPU controls also vary. Fenced effects at B512 fluctuate
strongly, so neither stage sums nor these sequential medians isolate integer
formatting. Full-game, MCTS, training throughput and playing strength are outside
this operation-level scope.

## Paired identity attribution

A separate bounded probe uses the same resident inputs and unit serializer,
compiled twice with only the integer magnitude line differing. It alternates
which implementation runs first for six pairs per family/role/batch. Four
families and both source/after-effects roles give 48 samples per implementation
at each batch. Existing identity/digest/check helpers retain the complete byte,
metadata and native-key contract. No production timer or fallback was added.

| Lanes | Original identity pipeline | Narrowed pipeline | Median within-pair narrowed / original |
|---|---:|---:|---:|
| 1 | 18.125 ms | 18.155 ms | 0.9975× |
| 64 | 19.376 ms | 19.257 ms | 0.9941× |

A ratio of pooled medians differs from the median of individual paired ratios.
Separately fenced serialization was 9.378/9.505 ms at B1 and 10.446/10.324 ms at
B64, original/narrowed. These mixed near-flat results support no useful formatter
speedup claim. No compiler intermediate representation or disassembly was
inspected; compiler narrowing of the old expression is not established.

## Verification and resources

All 46 checks passed: old/new GPU bytes, dense signed/decimal boundaries, every
output capacity and partial byte, guard/error/required-size behavior, negative
zero, cached/unknown nonintegers, and native UInt64MAX counters through all three
State serializers. Both complete grids passed every paired source, capacity,
draw, complete State/history/RNG output and native key. The paired probe passed
all 16 cases/96 pairs with unchanged sources and exact native identity bytes,
metadata and keys. No field, unit, choice, lane or dice result was reduced.

Fresh frozen commits are `a465e1a` and `7ca048a`. All 110 native/build inputs
match the saved build proof and both use native `46d02ca5…`. The only executed
source difference is the magnitude line; other commit changes are its test and
document. Both actual import/asset/runtime manifests pin the same Torch 2.14.0
environment, disabled fallback/fast math and unchanged complete-step selections:
parallel editor/container/RNG copy, unit-parallel JSON, unrolled SHA, certified
source reuse, native serial and ten-worker controls. Repeated-source certificate
hits do not predict chronological-game cache reuse.

Complete baseline/candidate runs took 67.97/67.54 seconds and charged peaks of
6.355/6.350 GB including the full 3 GB MPS reservation. The paired probe took
12.17 seconds and charged 4.595 GB. Every run stayed below the 7 GB stop threshold
inside the 8 GB/180-second envelope and within 12 CPU cores. The 46-check run
was separately bounded at 240 seconds. Raw near-null and variable evidence is
preserved; no training-speed claim follows from source syntax.
