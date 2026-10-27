# Recruitment transition scaling

The supported GPU recruitment-chance transition beat the ten-worker native
control at 512 lanes: 97.93 versus 151.92 ms. It remained slower at 128 lanes
and was near parity at 256. This is a measured operation-level crossover on
repeated immutable sources; full-game, MCTS and training throughput remain
unmeasured by this experiment.

The [curated evidence](metal_recruitment_scaling_2026_10_27.json) pins the three
raw artifacts, clean native build, complete source/environment provenance,
all controls, full-state/RNG witnesses and resource guards. It extends the
[editor/container factorial](metal_container_factorial_2026_10_27.md) using its
best explicit selection: parallel editor and container, unit-parallel JSON,
unrolled SHA and certified-source reuse. The default editor/container policies
remain reference.

Median milliseconds across four families and three unfenced repetitions:

| Lanes | GPU | Native serial | Native ten-worker pool | GPU / serial | GPU / pool |
|---|---:|---:|---:|---:|---:|
| 128 | 60.548 | 96.557 | 43.318 | 0.627× | 1.398× |
| 256 | 73.377 | 191.038 | 75.233 | 0.384× | 0.975× |
| 512 | 97.929 | 395.680 | 151.924 | 0.247× | 0.645× |

At 512 lanes the GPU took 1/4.04 of serial-native time and 1/1.55 of pool time.
Ratios are ratios of pooled medians within each run. Native timing includes the
original guarded `resolveChance`, internal clone, validation/history/RNG,
output key and pool dispatch. External trial clones, locks/GIL, verification,
Python boxing and pool startup are separate. GPU timing covers the complete
handler and final fence; upload/reserve, expected keys, warmup and verification
are outside. The native pool is a diagnostic control and does not automatically
parallelize production CPU search.

All 12 cases passed complete native State/history/RNG and Engine-key checks.
All source buffers stayed unchanged. Each case had five certified-source hits
and zero misses; this reuse pattern does not establish a chronological-game
hit rate. No unit, field, legal choice, lane or dice result was clipped. All
three runs used identical frozen code and native inputs; only batch size and
its resulting capacities changed. Full per-family timings and capacity/hash
witnesses remain in the evidence JSON and pinned raw artifacts.

The clean detached runtime was `5032790`, native SHA `8bd4a446…`, built and
verified inside the fixed checkout. Torch 2.14.0, disabled fallback/fast math,
two tensor/coordinator threads and ten native workers fit the 12-core allowance.
The existing 8 GB/180-second guard and 3 GB MPS allocator reservation were kept:

| Lanes | Run elapsed | Peak conservative charged memory |
|---|---:|---:|
| 128 | 17.80 s | 4.666 GB |
| 256 | 32.03 s | 4.693 GB |
| 512 | 57.10 s | 5.970 GB |

Memory charges include process physical footprint, compressed pages and the
full fixed MPS reservation, with possible conservative double counting. Every
run stayed below the 7 GB stop threshold, leaving the 1 GB guard margin. Neither
physical-memory guard nor MPS allocator failed. The sequential follow-up ended
at 512 lanes.

Separately fenced stages remain intrusive diagnostics and do not sum to whole
transition medians. At 128 lanes they exposed effects 13.57, identity 20.47 and
income refresh 12.67 ms. Income refresh now needs its own extractor/rate/writer/
editor subprofile before selecting another implementation change. These data
provide no evidence about playing strength or the number of useful concurrent
positions available in actual search.
