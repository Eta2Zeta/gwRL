# CPU self-play profile — 28 October 2026

This profile locates where CPU time goes in matched self-play collection before
any optimization. Rules, search budgets, model and dice were unchanged. The
[evidence JSON](cpu_profile_2026_10_28.json) records settings, provenance,
timings, histograms and sample shares. Raw outputs and the measurement scripts
remain ignored under `studies/campaign/runs/cpu-profile-2026-10-28/`.

**Conclusion: the machine is mostly idle, and engine time is mostly memory
management.** Four "parallel" games kept 1.6 cores busy on a 10-performance-core
M4 Max. When game threads did work, 70% of it was legal-move generation, and
about two thirds of that time was allocation and text-key comparison rather
than rule logic.

## Workload

Four complete three-round games, seeds 1951–1954, 16 simulations, depth cap 16,
fresh fixed weights (hidden size 16, one message layer, 2,048 token buckets) and
four tensor threads, at commit `7692851`. This is the 26 October matched CPU
workload. All four games reproduced its decision, chance and transition counts
exactly.

| Run | Four games | Network preparation and forward | Search outside the evaluator |
| --- | ---: | ---: | ---: |
| 26 October reference | 295.0 s | 69.7 s | 187.2 s |
| Uninstrumented rerun | 303.7 s | 73.2 s | 191.1 s |
| Boundary timers | 316.4 s | 75.5 s | 193.9 s |

The whole uninstrumented process used 511.8 CPU-seconds in 311.8 s, an average of
**1.64 busy cores**. Peak resident memory was 1.09 GB.

## Where the time goes

Each game's search runs in its own thread. A round ends only when every live
game has requested one network evaluation, and the calling thread then evaluates
the batch while all game threads wait.

| Wall-clock share of the 302.6 s search | Seconds | Share |
| --- | ---: | ---: |
| Evaluator on the calling thread, all game threads waiting | 108.7 | 36% |
| Game threads working, calling thread waiting for the slowest game | 193.9 | 64% |

Game threads spent 1,006 thread-seconds in search, and **682 of them (68%) waiting**
for the slowest game or for the evaluator. During game-thread phases only 1.7 of
the 4 threads were busy on average. Their 325 working thread-seconds divide as:

| Work | Seconds | Share | Mean per call |
| --- | ---: | ---: | ---: |
| Legal-move generation (native) | 227.3 | 70% | 6.4 ms |
| Applying moves (native) | 69.5 | 21% | 2.0 ms |
| Search clones (native) | 9.0 | 3% | 0.5 ms |
| Dice resolution (native) | 7.9 | 2% | 1.3 ms |
| Python search and adapter work | ~11 | 3% | — |

About **30% of legal-move generation repeats work**: 66 s was spent regenerating
menus for positions the tree had already expanded. Each simulation starts from a
fresh clone, and `CampaignAdapter.apply_action` validates every edge against a
newly generated menu. Copying states, Python canonicalization (`_canonical_raw`,
`action_key`) and repeated planning-key reads are each below 3%.

The evaluator's 108.7 s comprised 75.5 s of tensor preparation and forward
passes and 31.2 s of numerical input assembly (`numeric_input`), all on the one
calling thread.

## Thread scaling

Independent copies of one midgame position (Axis combat movement, 302 legal
actions) were exercised on 1–10 threads for 8 s each:

| Threads | Clone, apply, new legal menu | Clone and apply only |
| ---: | ---: | ---: |
| 1 | 1.00× (26.5/s) | 1.00× (821/s) |
| 4 | 4.06× | 3.50× |
| 8 | 7.66× | 4.66× |
| 10 | 9.36× | 3.89× |

Legal-move generation scales almost linearly, so it does not explain the idle
cores. Short calls scale poorly because per-call Python and conversion work holds
the interpreter lock. At this position one new legal menu took 34.9 ms, a search
clone 0.13 ms and clone plus apply 0.97 ms.

## Inside the engine

macOS `sample` profiled single-thread loops at the same position, 15 s at 1 ms:

| Self-time share | Legal-move generation (39.6 ms) | Clone and apply (1.44 ms) |
| --- | ---: | ---: |
| Memory allocation and freeing | 48.7% | 47.6% |
| String comparison | 17.0% | 8.2% |
| Memory copying, map and set operations | 11.9% | 14.5% |
| JSON building and lookup | 3.2% | 11.3% |
| SHA-256 state fingerprint | 0.8% | 11.0% |
| Game rule code | 14.8% | 5.3% |

Generation time sits under the movement, naval and land-combat action generators.
Hot rule functions include `aircraftFlightAccess`, `enemyFighter`, `seaBlockaded`,
`occupiedCarrierSlots` and `validateNavalRoute`. Text identifiers in
`std::map`/`std::set` containers create many temporary strings and lookups.
`State::planningKey` (canonical JSON plus SHA-256) accounted for 22.7% of move
application, about 5% of game-thread work.

## Optimization targets

Ordered by expected gain for the effort:

1. **Remove the round barrier.** Let each search continue while others are
   evaluated, and evaluate whatever requests are pending. Overlapping engine and
   network work could roughly halve this workload. The algorithm is unchanged,
   but batch composition can change float32 results near ties, so verify with
   matched statistics rather than exact traces.
2. **Run more games at once with fewer tensor threads.** The 16-wide network does
   not need four threads. Legal generation scales nearly linearly to ten threads,
   and more games also give larger network calls.
3. **Reuse menus for expanded positions** within a search, keyed by the complete
   planning key, or apply tree edges by index. This removes about 30% of
   legal-generation time with identical results.
4. **Assemble numerical inputs in the game threads** instead of on the calling
   thread, taking 31 s off the serial path.
5. **Replace text-keyed engine structures** in the hot generators with integer
   identifiers, flat arrays and precomputed tables. About two thirds of generation
   is allocation and string handling. This is the largest engine project; exact
   trace matching remains the right check.
6. **Use a cheaper state fingerprint** than canonical JSON plus SHA-256 (about 5%
   of game-thread work). It changes the stored history-key format.

## Limits

Each configuration ran once, without confidence intervals. Boundary timers add
about 4% overhead and include reacquiring the interpreter lock after native
calls. The scaling and sampling loops use one heavy position, not a whole-game
mix. Weights were fixed and no learning occurred. The current network is tiny.
None of these numbers establish learning speed or playing strength.

Reproduce from the repository root, one heavy job at a time:

```sh
.venv/bin/python tools/benchmark_campaign_devices.py --mode selfplay --devices cpu \
  --seconds 1200 --output studies/campaign/runs/NEW-RUN/baseline.json
PYTHONPATH=. .venv/bin/python studies/campaign/runs/cpu-profile-2026-10-28/scripts/time_selfplay.py \
  --out studies/campaign/runs/NEW-RUN/timers
PYTHONPATH=. .venv/bin/python studies/campaign/runs/cpu-profile-2026-10-28/scripts/scale_native.py
```
