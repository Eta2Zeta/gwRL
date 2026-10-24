# Stage A: reuse unchanged decision data

24 October 2026. This performance pass removes repeated legal-action generation
and observation/input conversion. It preserves the search algorithm, policy
weights, legal choices, rules, dice distribution and game horizons. Measurements
use frozen policies and perform no learning updates.

## Results

Seven paired cases pass exact semantic comparison, including neural priors and
values, ordered actions, visit counts, visit-derived policies and actual state
and execution RNG. Completed cases have byte-identical semantic traces; the
guarded case has an identical completed prefix.

| Fixed Japan Combat Movement position | Concurrent roots | Simulations | Mean warm batch, before | After | Speedup |
| --- | ---: | ---: | ---: | ---: | ---: |
| Round 1, pilot model | 4 | 16 | 10.938 s | 3.999 s | 2.74× |
| Round 1, pilot model | 4 | 64 | 37.436 s | 13.437 s | 2.79× |
| Round 3, pilot model | 2 | 16 | 5.613 s | 1.560 s | 3.60× |
| Round 6, pilot model | 1 | 16 | 3.168 s | 0.935 s | 3.39× |
| Round 1, larger model | 4 | 16 | 11.693 s | 4.660 s | 2.51× |

Each fixed-position invocation repeats three searches; the table averages the
second and third waves. Search trees are fresh. Preparation and startup are
excluded from these warm-wave timings. The larger model has width 64, two
message-passing layers and 16,384 token buckets; the pilot uses 16/1/2,048.

One actual eleven-round game at four simulations/depth cap eight completes in
**112.723 seconds versus 198.420 seconds**, a 1.76× end-to-end speedup. Both
versions execute 560 choices and 71 chance events and reach the same terminal
scores. Invocation timing includes startup, preparation, reporting and trace
instrumentation.

The four-root, two-round batch at 16 simulations/depth cap 16 still reaches its
240-second wall guard with **0/4 games complete** in both versions. The optimized
version completes 370 choices and 50 chance events, versus 234 and 28. The shared
completed search prefix is 1.64× faster; this is not a whole-batch speedup or a
completed-game result. Unfinished games retain null terminal returns. Larger
learning remains on hold for the remaining performance work.

The largest sampled aggregate RSS is **2.764 GB**, within the 30 GB allowance.
Caching trades a modest increase in some cases for less computation; the full
game's sampled peak changes from 2.032 to 2.035 GB.

At the matched opening root, warmed pilot-model medians are:

| Operation | Before | After |
| --- | ---: | ---: |
| Retrieve the unchanged legal menu | 27.936 ms | 0.00225 ms |
| Detached public observation | 58.270 ms | 0.569 ms |
| Rule transition on a clone | 55.392 ms | 2.072 ms |
| Feature assembly plus scalar neural evaluation | 83.075 ms | 17.503 ms |

The legal-menu row measures reuse, not generation of a new state's menu. These
operation timers overlap and must not be added. Serial 16-simulation search
improves from 3.320 to 1.682 seconds with profiler overhead. Its cProfile
accounting remains partial; first-use observation-graph construction remains a
visible Python hotspot, but the profile does not establish total-cost shares.
That is the next optimization candidate before repeating stronger collection.

## Implementation

The C++ engine retains one legal-action menu and one interrupt menu for its
current state. Action application compares the complete proposed payload with
the retained canonical legal payload, rather than regenerating and serializing
the menu. Clones share synchronized immutable menus; successful actions,
interrupts and chance resolution detach the changed clone's cache before rule
execution. Rejected transactions leave the original state and cache intact.

`CampaignEnv` retains its current observation and planning identity. Its C++
observation reference is valid until the next successful mutation; Python
continues to receive detached mutable JSON from the public observation API.

The Python adapter retains the corresponding scheduled choices and immutable
observation. Its identity includes the raw planning key, declaration-offer order
and passed offers. Passing an offer refreshes the scheduled observation while
reusing unchanged raw data. Clone, restore, pending-choice, chance and external
raw-state changes preserve the appropriate isolation and invalidation behavior.
Public action features remain detached mutable copies; private authoritative
payloads cannot be changed through the shared source snapshots.

Neural-input construction reuses validated immutable observations, context and
action features. Ordinary mutable inputs still undergo full JSON validation and
detachment. Learned embeddings, predictions and gradients are recomputed on every
forward pass, including after model updates. No model-output cache was added.

## Verification

- All 24 C++ suites pass in the Release build (68.06 seconds).
- All 258 Python tests pass (98.462 seconds), including exact training resume,
  real gradient updates and batching.
- New regressions cover generation counts, stale/forged native payloads, caller
  mutation, declaration passes, pending choices, chance, phase transitions,
  restore, failures and concurrent clone readers.
- Both versions replay the same full-campaign trajectory exactly across 631
  actual transitions. Full observations, legal menus, acting factions, decision
  kinds and planning identities match before each transition; serialized state
  and execution RNG match before and after. Terminal returns also match.

## Measurement scope

The reference is commit `64c9864`, with its source, scenario and compiled native
module preserved before rebuilding. The pilot checkpoint is used for inference
weights only, with fresh current-rule game states. One additional fixed-position
pair uses freshly seeded width-64, two-layer models. Model and prepared-state
hashes must match within each pair.

An identical local verification wrapper streams completed search results and
actual actions/chance transitions for both versions. Its overhead is included
in both invocation times. Fixed-position searches leave the real state and dice
generator unchanged; whole-game cases actually apply actions and dice. Timings
from this paired experiment should not be mixed with the earlier uninstrumented
13-case scaling measurements.

The resource allowance remains 12 CPU cores and 30,000,000,000 bytes. RSS means
resident set size: physical memory currently occupied by a process. Reported
peak RSS is the highest sampled sum for supervisor and worker, sampled every
0.1 seconds. Shared pages can be counted more than once and brief peaks can be
missed; the 128 MiB guard margin is not a kernel allocation limit. Small build/test
jobs overlapped some baseline cases, and one-core observation replays overlapped
both guarded collection cases, within the combined CPU budget. These are single
paired measurements on one machine.

Frozen-policy collection excludes optimizer updates, replay accumulation and
training checkpoint writes. It measures implementation cost and completion, not
learned strategic strength.

The [curated measurements](decision_reuse_2026_10_24.json) record exact settings,
source/native/model/checkpoint hashes, all seven comparisons, operation profiles,
replay checks, reproduction commands and hashes for 50 raw artifacts. Large raw
traces and the local comparison helpers remain ignored under
`tmp/menu-reuse-2026-10-24/`; the checkpoint is preserved in the original ignored
run directory. The standard benchmark and profile tools remain tracked.

For a fresh, uninstrumented full-game measurement from the repository root:

```sh
./.venv/bin/python -m studies.campaign.scaling_benchmark \
  --output studies/campaign/runs/NEW-RUN/full11-s4.json \
  --checkpoint-weights studies/campaign/runs/stage-a-speedcheck-2026-10-23/checkpoint.pt \
  --mode episode --full-campaign --seed 1951 --roots 1 \
  --simulations 4 --max-depth 8 --max-transitions 2000 \
  --threads 4 --cpu-budget 12 --memory-bytes 30000000000 --seconds 240
```

Use a new output path. Exact instrumented reproduction uses the local wrapper
and commands identified by hash in the curated report. The command above omits
that verification overhead and must be reported separately.
