# Resident political queries, 2026-10-26

The complete political-query matrix matches native C++ for every measured lane,
including missing/playerless error results and LandAttack declaration permission.
**Four-position batches still favor CPU; batches of 64 and 256 favor Metal.**
This is a read-only rules component, not completed-game, MCTS or training speed.

Each lane computes seven directed pair queries (control, war, friendliness,
logistics, optional/shared alliance and railway permission), three nation queries
(player, major enemy, movement control), and LandAttack permission for all pairs.
The 13-faction context includes the dormant Dadao faction. Both implementations
return the same values and per-query errors; no missing query is discarded.

The GPU path includes full dynamic state extraction, source-bound relation
preparation and the declaration pass, their output allocation, dispatches and
synchronization. Immutable map, faction and Home Country data is prepared once.
The CPU baseline is one already-batched native oracle call invoking the original
predicates, including allocation and lazy exceptions. It has no per-query Python
call-loop penalty. Complete result inspection is outside both timers.

## Matched timings

Median milliseconds per complete query batch, five repetitions. Each case repeats
one actual complete state; it is not a diverse-position throughput workload.

| Position | Lanes | Native CPU | Resident GPU | CPU / GPU |
| --- | ---: | ---: | ---: | ---: |
| opening | 1 | 0.6525 | 2.9270 | 0.22× |
| opening | 4 | 2.4860 | 3.0832 | 0.81× |
| opening | 64 | 39.5177 | 4.9330 | 8.01× |
| opening | 256 | 159.7507 | 5.5478 | 28.80× |
| first_chance | 1 | 0.6424 | 2.9383 | 0.22× |
| first_chance | 4 | 2.5026 | 3.0705 | 0.82× |
| first_chance | 64 | 43.2718 | 5.1865 | 8.34× |
| first_chance | 256 | 165.3115 | 5.8098 | 28.45× |
| round2_japan_combat_movement | 1 | 0.6970 | 3.6692 | 0.19× |
| round2_japan_combat_movement | 4 | 2.6023 | 3.9015 | 0.67× |
| round2_japan_combat_movement | 64 | 40.1530 | 5.9541 | 6.74× |
| round2_japan_combat_movement | 256 | 166.1394 | 6.7659 | 24.56× |

Fixtures come from the unchanged opening, first pending chance request and
second-round Japanese combat movement in a completed three-round scripted game.
The tool checks every array value/error and confirms the original full State,
history and RNG are unchanged. Source/native/tool hashes, state witnesses, all
raw timings and output-array digests are in the [evidence](metal_political_queries_2026_10_26.json).

Native capture, uploads, population of the resident batch, cold reset/setup and
host comparison are recorded separately. Warm ratios require state to remain
resident and reuse static context. Small-batch GPU latency remains a real cost.
A full game need not query every pair eagerly, so these ratios cannot be applied
to CPU game time or added to unrelated clone/RNG speedups.

## Resources and provenance

The benchmark ran alone with two Torch threads, no CPU fallback/fast math, an
8 GB guard and a 180-second shared deadline. The worker took 23.43 s; the
supervisor took 24.35 s. The conservative memory charge peaked at
**4,534,854,632 bytes**, including a full 3 GB MPS allocator reservation. No
training run or earlier checkpoint was modified.

The measured committed parent is `90afa78`. One unfinished, untracked
`resident_routes.py` file was present but was neither imported nor used by this
component. Its bytes and the dirty path are preserved in provenance. All files
were frozen throughout timing and the source fingerprint remained unchanged.
Compiled native hashes are recorded separately; no whole-tree clean-build claim
is made. The optional GPU runtime is Torch 2.14; the original CPU environment is
unchanged. No learning-strength claim follows from these timings.

Relevant validation: 16 political/declaration checks, 10 container checks and
11 generic-JSON/digest checks passed across focused runs; all 27 native suites
also pass. The measured revision also passes nine complete State JSON/key checks
and five additional income-refresh cases (11 total income tests). The original
CPU environment ran eight CPU container tests successfully and skipped 40
unsupported state-GPU tests. Counts from overlapping suites are not added.

Reproduce in the isolated GPU environment:

```sh
tmp/gpu-mps-env/bin/python tools/benchmark_campaign_resident_queries.py \
  --batch-sizes 1 4 64 256 --repeats 5 \
  --output studies/campaign/runs/another-fresh-query-result.json
```

Full route evaluation, unit statistics, legal-menu construction, action/chance
effects and resident search remain under development. The earlier complete-game
hybrid benchmark remains slower than the original CPU path; this component result
does not supersede it.
