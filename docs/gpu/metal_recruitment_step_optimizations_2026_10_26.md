# Complete recruitment chance: identity optimizations

Unit-parallel JSON, unrolled SHA and certified reuse of an unchanged source
reduced complete GPU recruitment-chance latency by about 27–36%. GPU remains
slower than both serial native execution and the persistent ten-worker native
pool at every measured batch. The [curated evidence](metal_recruitment_step_optimizations_2026_10_26.json)
records both raw artifacts, all source/native/environment fingerprints, exact
outputs, guards and timer scopes.

Both runs cover four controlled-minor recruitment families at batches
1/4/16/64, three unfenced repetitions and one separate stage profile per case.
Each starts from the same legal pending roll and consumes identical untaped
native dice. Median milliseconds across 12 samples per batch:

| Lanes | GPU original | GPU optimized | Native serial, first / second run | Native ten-worker pool, first / second run |
|---|---:|---:|---:|---:|
| 1 | 128.202 | 82.507 | 0.787 / 0.744 | 0.876 / 0.815 |
| 4 | 139.051 | 93.553 | 3.104 / 3.157 | 1.499 / 1.369 |
| 16 | 154.109 | 108.056 | 11.849 / 11.825 | 6.857 / 6.245 |
| 64 | 190.024 | 139.117 | 47.611 / 47.261 | 22.964 / 25.438 |

The optimized GPU is 110.8/29.6/9.1/2.9 times the serial-native latency, and
101.3/68.3/17.3/5.5 times the pool latency, respectively. These ratios use pooled
medians within the optimized run. Native code did not change between runs;
its small timing differences are not an optimization result.

Native timing includes the cached Engine-key guard, original `resolveChance`
(including its internal clone, validation, Event and RNG work), output key and
pool dispatch. External trial clones, wrapper locks/GIL, pool startup, full
verification and Python boxing are outside that timer. GPU timing includes the
complete handler call and final fence. Fixed reserve, expected-key preparation,
warmup and host verification are outside GPU timing.

## What remains expensive

Separately fenced stage medians across four diagnostic profiles per batch:

| Stage | Original, B1 / B64 | Optimized, B1 / B64 |
|---|---:|---:|
| Source preflight | 33.095 / 35.420 ms | 0.430 / 0.559 ms |
| Final identity | 33.021 / 35.626 ms | 18.827 / 19.923 ms |
| Recruitment effects | 36.285 / 67.978 ms | 36.074 / 67.663 ms |
| Income | 10.358 / 18.842 ms | 10.301 / 19.076 ms |
| Event | 9.318 / 16.199 ms | 9.192 / 16.801 ms |

Effects are the largest measured remaining cost. Reset, forward-capability and
RNG publication also remain visible. The next diagnostic separates effects
edits, relation/query/menu work, string interning and final publication. Fenced
profiles change synchronization and do not sum to unfenced step timings.

## Correctness and reuse scope

All 16 cases in each run passed full State/history/RNG and native Engine-key
comparisons. Source buffers, capacities, fixture draws, complete output record
hashes and all native keys match between variants. No unit, state field, dice
outcome or legal option was removed. The optimized run recorded exactly five
certified-source hits per case and zero misses; the original run recorded zero
hits and misses.

The measured reuse checks a repeated immutable source with an exact expected
identity prepared outside timing. It establishes neither a chronological-game
hit rate nor free identity construction after arbitrary state changes. Mutation,
foreign ownership and unsupported certification still require the authoritative
path. The earlier [standalone identity](metal_identity_optimizations_2026_10_26.md)
and [field-parallel experiment](metal_field_json_experiment_2026_10_26.md) remain
separate measurements; field parallelism was not selected here.

Both exclusive runs used clean detached `7d0c1b0`, native `b061ab73…`, Torch
2.14.0, two reserved tensor/coordinator threads plus the ten-worker native pool,
disabled MPS fallback/fast math and a 3 GB MPS reservation. They took
27.32/22.43 seconds and charged conservative peaks of 4.708/4.783 GB, below each
8 GB/180-second diagnostic guard and the user's 12-core/30 GB allowance. Raw
artifacts are `studies/campaign/runs/gpu-backend-2026-10-26/complete-chance-{baseline,optimized}.json`.

These restored fixtures measure one supported complete transition, not a
campaign-position distribution, full GPU game backend, MCTS, self-play,
training throughput or playing strength. No learning update or game/search
budget change occurred.
