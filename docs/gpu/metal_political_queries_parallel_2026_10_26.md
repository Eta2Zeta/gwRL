# Cooperative political-query implementation, 2026-10-26

Distributing a position's political work across GPU threads reduces latency in
all 12 measured cases. At four positions, opening/first-chance queries now slightly
beat the native matrix oracle; the second-round case is still about 9% slower.
At 64 positions the GPU is 9–11.5× faster, and at 256 it is 25–35× faster.
**These are complete political-query matrix timings, not game/search/training throughput.**

The earlier GPU kernel used one thread per game position. The cooperative kernel
uses one threadgroup per lane: parallel initialization, a shared header, faction
metadata extraction across threads, synchronization, then independent nation and
pair queries. Strided loops preserve arbitrary faction counts. A malformed input
uses the original serial body on one GPU thread, preserving exact diagnostic
outputs without CPU fallback. The reference implementation remains selectable.

## Matched comparison

Median milliseconds, five repetitions. The paired reports have identical complete
native snapshot digests and every result/error-array digest for all 12 cases.
The default group has 128 threads, subject only to the actual Metal kernel limit.

| Position | Lanes | Native CPU | Earlier GPU | Cooperative GPU | CPU / cooperative |
| --- | ---: | ---: | ---: | ---: | ---: |
| opening | 1 | 0.6444 | 2.9270 | 2.7446 | 0.23× |
| opening | 4 | 2.6320 | 3.0832 | 2.3242 | 1.13× |
| opening | 64 | 43.2499 | 4.9330 | 3.7641 | 11.49× |
| opening | 256 | 164.4535 | 5.5478 | 4.7429 | 34.67× |
| first_chance | 1 | 0.7073 | 2.9383 | 2.2075 | 0.32× |
| first_chance | 4 | 2.6179 | 3.0705 | 2.2960 | 1.14× |
| first_chance | 64 | 38.6032 | 5.1865 | 4.2024 | 9.19× |
| first_chance | 256 | 157.6162 | 5.8098 | 4.7507 | 33.18× |
| round2_japan_combat_movement | 1 | 0.6081 | 3.6692 | 2.5288 | 0.24× |
| round2_japan_combat_movement | 4 | 2.4291 | 3.9015 | 2.6398 | 0.92× |
| round2_japan_combat_movement | 64 | 41.0912 | 5.9541 | 3.9304 | 10.45× |
| round2_japan_combat_movement | 256 | 163.5644 | 6.7659 | 6.4469 | 25.37× |

Both GPU paths include allocation, extraction, relation matrices and the shared
LandAttack declaration pass, dispatches and synchronization. The native oracle
is one batched C++ call. Initial uploads, preparation, cold reset/compilation and
host conformance inspection are outside warm timing and recorded separately.
Each case repeats a real source position; this is not a diverse-position game
workload. Small timing differences remain subject to run-to-run noise.

The cooperative run used parent `ab13167` with one unfinished untracked route
module present but not imported. Files were frozen throughout and the source
fingerprint remained stable. All native, runtime and tool hashes are recorded.
It ran alone in 26.20 s (supervisor), with conservative peak memory
**4,533,298,200 bytes**, including the full 3 GB MPS reservation, under the same
8 GB guard, two Torch threads and 180-second deadline. No training data or
checkpoints were changed. The original CPU environment remains unchanged.

The component now selects the validated cooperative path by default; an explicit
`implementation="reference"` preserves the comparison implementation. This does
not change the registered campaign backend: CPU remains the only complete one.
The default-selection follow-up is a dispatch choice; the measured cooperative
kernel and rules are unchanged. Its verification includes 12 relation tests
(comparing both GPU paths to original native results), seven declaration tests,
arbitrary group sizes and exact malformed-input fallback. Tests select the
reference explicitly so changing the default cannot make a self-comparison.

[Earlier evidence](metal_political_queries_2026_10_26.json) and
[cooperative evidence](metal_political_queries_parallel_2026_10_26.json) retain raw
timings and complete settings. Reproduce with the same benchmark tool and an
explicit `--implementation reference` or `--implementation parallel`.
