# Exact arena copy: effects profile and complete-step comparison

Parallel arena copying reduced the complete supported GPU recruitment-chance
transition from 83.51 to 64.38 ms at one lane and from 139.63 to 87.07 ms at 64
lanes. GPU still loses to native execution. The new editor remains explicitly
selected; its default is reference. The [curated evidence](metal_editor_copy_2026_10_26.json) keeps the
effects diagnostic and full-step comparison separate, with all three raw hashes,
source/native/environment provenance, exact layout proofs and resource guards.

## Intrusive effects diagnostic

Scoped wrappers measured the original `effects.apply` and its existing helpers;
no apply/menu implementation was replaced. Explicit fences and retention of
returned objects extend synchronization/allocation lifetimes, so these are
diagnostics, not throughput estimates. Every returned tensor value, dtype,
device, shape, stride, storage offset, layout and grad flag was compared outside
timing, together with all dataclass metadata and complete native State/history/
RNG/keys. Source and static buffers stayed unchanged.

Four families at B1/B64, three captures each, yielded these median milliseconds:

| Effects work | B1 | B64 |
|---|---:|---:|
| Four container builders | 21.757 | 29.650 |
| Chance-clear and four editor commits | 13.939 | 34.419 |
| Complete choice construction | 3.527 | 4.037 |
| Decision-name interning | 0.964 | 1.034 |
| Four direct effects kernels | 0.602 | 0.811 |
| Setup/publication gaps | 3.007 | 3.506 |
| Complete intrusive effects call | 43.950 | 72.614 |

Each category is summed within a capture before taking its median; category
medians need not sum to the final row. Choice construction includes nested query,
relations, parameter JSON/hash, action-ID creation and interning. Its action-ID
intern costs about 1.00/1.16 ms and relations about 0.34/0.37 ms. These nested
times must not be added again to the choice total.

Builders cost roughly 5.3–5.6 ms each at B1 and 7.2–7.7 ms at B64. The reference
kernel serially zeroes the complete output allocation and validates the complete
source tree before each small target edit. Editor commits also serially copy and
relocate the full arena. This measurement motivated copy parallelism; builder
validation/initialization remains a separate target.

## Matched complete transition

Both runs use unit-parallel JSON, unrolled SHA, default digest groups and
certified reuse of the unchanged source. Only the explicit editor selection
changes. The parallel editor retains the original validation/error ordering and
cohort rollback, distributes record copying, then discovers sections. Native
serial and persistent ten-worker execution are measured in both runs.

Median milliseconds across four families and three unfenced repetitions:

| Lanes | GPU reference editor | GPU parallel editor | Native serial | Native ten-worker pool | GPU / pool |
|---|---:|---:|---:|---:|---:|
| 1 | 83.507 | 64.382 | 0.810 | 0.952 | 67.7× |
| 4 | 93.176 | 68.356 | 2.974 | 1.553 | 44.0× |
| 16 | 107.402 | 73.497 | 11.833 | 6.266 | 11.7× |
| 64 | 139.625 | 87.066 | 48.000 | 20.986 | 4.15× |

Native columns/ratios use the parallel-editor run; both runs' native values are
retained in the JSON. GPU improvement is 1.30/1.36/1.46/1.60 times, respectively.
At B64 GPU still takes 1.81 times the serial-native latency. Native timing
includes the cached key guard, original `resolveChance` with its internal clone,
validation/Event/RNG, output key and pool dispatch. External trial preparation,
locks/GIL, full verification and boxing are excluded. GPU timing includes the
complete handler and final fence; reserve, expected-key preparation, warmup and
verification are outside timing.

Separately fenced stages show effects dropping from 36.44/69.37 to
25.73/36.47 ms at B1/B64, reset from 2.92/7.22 to 0.58/0.81 ms, and income from
10.61/18.98 to 8.24/11.90 ms. Event falls from 9.47/16.78 to 7.28/9.91 ms.
Final identity remains around 18.9–20.0 ms and RNG work around 2.5–5.1 ms.
Builders remain substantial. Fenced stages cannot be summed into an unfenced
throughput estimate.

All eight effects cases/24 captures and both 16-case complete-step grids matched
native outputs. Source buffers, capacities, untaped draws, output records and
Engine keys agree across runs, including the effects profile's overlapping
fixtures. Certified checks were exactly five hits per complete case, zero misses;
this repeated immutable-source workload does not establish a chronological-game
hit rate. No field, unit, dice outcome or legal choice was dropped.

The clean detached runtime was `45c5de8`, newly built native `9f702cf0…`, with
all 104 native/build inputs verified before atomic installation. Torch 2.14.0,
disabled fallback/fast math, two reserved tensor/coordinator threads and a 3 GB
MPS reservation were used. Effects/reference-editor/parallel-editor runs took
16.68/23.67/19.94 seconds and charged conservative peaks of
4.902/4.802/4.791 GB. Each stayed below the 8 GB/180-second diagnostic guard and
the user's 12-core/30 GB allowance; complete-step native pools used ten workers.

Raw artifacts are `studies/campaign/runs/gpu-backend-2026-10-26/effects-subprofile.json`
and `complete-chance-editor-{reference,parallel}.json`. These controlled-minor
fixtures measure one supported transition, not full GPU games, MCTS, self-play,
training throughput or playing strength. The later parallel-builder prototype
is not included in these copy-only measurements.
