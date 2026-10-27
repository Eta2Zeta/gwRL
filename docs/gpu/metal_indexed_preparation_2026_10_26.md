# Indexed Apple GPU route preparation

All three preparation implementations matched every native route result and retained every source State/history/RNG word in all 16 cases. Indexed preparation reduced the fresh four-position GPU workload from roughly 3.2–3.8 ms to 1.85–1.95 ms. CPU still wins at four positions. At 64 positions, the indexed workload takes 3.42–3.68 ms versus 5.18–6.13 ms for reference preparation.

The new explicit `fused_indexed` strategy reuses the existing unit/territory index, computes presence and declaration pairs across a threadgroup, and avoids a repeated land-map search for every unit. If structural/cardinality/owner/zone checks cannot prove the indexed path safe, that lane executes the full audited serial GPU declaration body. It does not drop entries or use a CPU fallback.

## Matched timing

Median milliseconds of five repetitions; fresh GPU columns include all preparation and queries. CPU is the complete native supplied-route calculation inside its C++ timer, executed serially.

| Position | Positions | CPU | GPU reference | GPU combined | GPU indexed |
|---|---:|---:|---:|---:|---:|
| R1 combat | 1 | 0.459 | 3.559 | 3.672 | 2.286 |
| R1 combat | 4 | 1.654 | 3.760 | 3.690 | 1.853 |
| R1 combat | 16 | 7.454 | 4.613 | 4.172 | 2.178 |
| R1 combat | 64 | 26.705 | 6.130 | 4.356 | 3.684 |
| R1 noncombat | 1 | 0.191 | 3.245 | 3.340 | 1.956 |
| R1 noncombat | 4 | 0.731 | 3.463 | 3.344 | 1.872 |
| R1 noncombat | 16 | 2.623 | 4.127 | 3.840 | 2.435 |
| R1 noncombat | 64 | 11.248 | 5.296 | 4.072 | 3.510 |
| R2 combat | 1 | 0.501 | 3.289 | 3.243 | 3.092 |
| R2 combat | 4 | 1.305 | 3.373 | 3.217 | 1.949 |
| R2 combat | 16 | 5.163 | 4.252 | 3.841 | 2.523 |
| R2 combat | 64 | 20.346 | 5.181 | 4.127 | 3.593 |
| R2 noncombat | 1 | 0.136 | 3.130 | 3.135 | 1.883 |
| R2 noncombat | 4 | 0.597 | 3.223 | 3.129 | 1.896 |
| R2 noncombat | 16 | 2.195 | 4.022 | 3.655 | 2.544 |
| R2 noncombat | 64 | 10.041 | 5.245 | 4.126 | 3.422 |

These are route components, not completed-game throughput. All lanes in each batch are copies of one snapshot; they do not measure the larger shared string namespace created by distinct histories. The noncombat query sets contain no accepted routes and primarily measure rejection. Separate correctness cases include legal routes. Reference remains the default while these limits are measured.

## Correctness and provenance

All 39 indexed cases are covered and passing: 38 passed in the first run, and a history fixture passed after adding its missing required audit field. No shader comparison failed. The focused rerun also passed the old combined implementation’s boundary checks and all six harness checks. History growth, unused allocated string capacity, malformed map cardinality, duplicate keys, invalid owners/zones, small workgroups and complete source/context checks are included.

Current code commit: `79f54dc2629f49a5c07e76963cacfe0c1dbb5675`. All query sets, phases, seeds, source checkpoints and completed scripted-game hashes match across the three runs. [Tracked data](metal_indexed_preparation_2026_10_26.json) records repetitions, native/GPU field evidence, source hashes, artifact digests, guards and dirty-tree disclosure. Two unrelated untracked recruitment-transaction files remained outside the route execution path. Sources stayed frozen during each run.

The three runs were sequential with no other agent compute, used two Torch threads each, disabled MPS fallback/fast math and reserved 3 GB for MPS. Guarded elapsed times were 28.93s, 28.68s, 28.50s. Peaks including the reserve were 4.932GB, 4.935GB, 4.935GB. The supervisor’s 8 GB/180-second diagnostic bounds remained inside the user’s 12-core/30 GB allowance. Each run prepared one genuinely completed three-round scripted game outside timing. No game horizon, candidate set, model or search budget changed.

Reproduce with `tools/benchmark_campaign_resident_routes.py`, a fresh output per run, and `--preparation-implementation reference`, `fused` or `fused_indexed` in the isolated GPU environment. This is not a complete GPU campaign backend or evidence of stronger play.
