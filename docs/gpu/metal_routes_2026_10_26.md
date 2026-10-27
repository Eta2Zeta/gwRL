# Supplied-route validation on Metal, 2026-10-26

Every supplied route and complete result matches the original native validator.
Including fresh dynamic preparation, GPU remains slower at four positions. At
64 positions the combat snapshots are about 4–4.7× faster than the serial native
loop; reusing prepared indexes is substantially cheaper than preparing again.
**This is path validation, not complete menu generation, game execution, MCTS or training throughput.**

The port covers ordinary movement, blitz, strategic rail/river, narrow crossings
and towing, including all native result fields, ordered paths, terrain/region
sets, costs, exhaustion and exception messages. Thirteen focused oracle tests
also cover successful blitz and every catalog unit type. State/history/RNG and
all resident source buffers remain unchanged.

## Workload and timing

One unchanged balanced scripted game completed all three rounds. Four real Japan
snapshots (rounds one/two, combat/noncombat movement) supply every controlled unit
on retained land, every simple one/two-hop geometric or constructed-rail path
across five modes, ordinary wrong-phase checks, co-located tow pairs, and every
complete movement-route path already in the actual legal menu. No candidate is
silently capped or shortened. This supplied-path corpus deliberately includes
illegal paths and modes; it is not an enumeration of only legal moves.

Median milliseconds per batch, five repetitions:

| Position | Lanes | Queries/lane | Native CPU | GPU fresh prepare + query | GPU reuse + query | CPU / fresh GPU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| japan_round1_combat_movement | 1 | 948 | 0.4147 | 3.5999 | 0.2982 | 0.12× |
| japan_round1_combat_movement | 4 | 948 | 1.8196 | 3.7256 | 0.2919 | 0.49× |
| japan_round1_combat_movement | 16 | 948 | 7.0968 | 4.7280 | 0.3267 | 1.50× |
| japan_round1_combat_movement | 64 | 948 | 28.9911 | 6.1450 | 0.5715 | 4.72× |
| japan_round1_non_combat_movement | 1 | 738 | 0.1680 | 3.4043 | 0.2825 | 0.05× |
| japan_round1_non_combat_movement | 4 | 738 | 0.6954 | 3.4738 | 0.2783 | 0.20× |
| japan_round1_non_combat_movement | 16 | 738 | 2.6197 | 4.2542 | 0.2930 | 0.62× |
| japan_round1_non_combat_movement | 64 | 738 | 11.3948 | 5.1943 | 0.4802 | 2.19× |
| japan_round2_combat_movement | 1 | 774 | 0.3271 | 3.3208 | 0.2965 | 0.10× |
| japan_round2_combat_movement | 4 | 774 | 1.1928 | 3.3508 | 0.2919 | 0.36× |
| japan_round2_combat_movement | 16 | 774 | 5.4272 | 4.1160 | 0.3002 | 1.32× |
| japan_round2_combat_movement | 64 | 774 | 20.7666 | 5.2115 | 0.5068 | 3.98× |
| japan_round2_non_combat_movement | 1 | 642 | 0.1597 | 3.1245 | 0.2625 | 0.05× |
| japan_round2_non_combat_movement | 4 | 642 | 0.5882 | 3.1970 | 0.2682 | 0.18× |
| japan_round2_non_combat_movement | 16 | 642 | 2.2385 | 4.0873 | 0.2977 | 0.55× |
| japan_round2_non_combat_movement | 64 | 642 | 8.8210 | 5.3193 | 0.4968 | 1.66× |

The native timer calls original `validateRoute` on one C++ thread. Requests,
strong owners, unique mutexes, source pointers and result-vector storage are
prepared before that timer; construction of every owned result/set/string is
inside it. Python dictionary/set conversion happens only during explicit
inspection. Full native wrapper wall times are also recorded. This is a serial
component baseline, not a twelve-core optimized CPU route service.

The fresh GPU measurement includes political relations, declaration permissions,
source-bound unit/territory/nation indexes and the path query. The reused number
uses preparation from the same complete immutable source; it cannot be applied
to unrelated or changed states. Allocation, dispatch and synchronization are
inside GPU timers. Initial native capture, static/dynamic uploads, candidate
construction, cold reset/compilation and result inspection are reported
separately. Every lane repeats one source position, so diversity and concurrent
independent-game behavior remain unmeasured.

## Legal-path coverage and limits

| Snapshot | Allowed/lane | Rejected/lane |
| --- | ---: | ---: |
| Round 1 combat movement | 39 | 909 |
| Round 1 noncombat movement | 0 | 738 |
| Round 2 combat movement | 20 | 754 |
| Round 2 noncombat movement | 0 | 642 |

The scripted noncombat snapshots have **no legal supplied paths**. Their timings
mostly measure rejection, and a full legal-menu generator could prune many of
those candidates before asking the validator. They do not establish performance
for legal noncombat movement. Positive noncombat, rail/river/narrow and towing
cases are covered by correctness fixtures; representative positive performance
coverage remains future work. The combat corpus is also mostly rejected paths,
so neither its throughput nor the reuse-only ratios can be treated as a game
speedup. Preparing new positions remains the main small-batch cost.

## Resources, provenance and verification

The run completed all 16 cases with exact complete native result/source witnesses
and an unchanged source fingerprint. It took **29.30 s** under the supervisor
(28.36 s worker); scripted preparation took 12.50 s. Peak conservative memory
charge was **4,928,333,208 bytes**, including the full 3 GB MPS reservation, within
an 8 GB guard and 180-second deadline. Two Torch threads and one exclusive
benchmark job stayed within the user's 12 CPU / 30 GB allowance. GPU allocation
and operating-system accounting can conservatively overlap.

Measured parent is `ad82f21`. The worktree had unrelated recruitment-effects
preparation (`python_recruitment.inc`, a selected-query hook, and an untracked
orchestrator). These were frozen, recorded in provenance and not used by this
route component. The uncompiled effects-oracle addition was not linked into the
measured native binary. Native binary and runtime/tool hashes are recorded
separately; this is not presented as a clean whole-tree build.

Validation for the connected revision includes all 27 native suites; 33 joint
state/search-clone/event/reset/numeric checks; thirteen route cases; ten
recruitment query cases; eight chance-I/O cases; and six benchmark/native-probe
checks. These are overlapping scopes, not additive unique totals. In the
original CPU environment, a selected 52-check suite passed with 44 unsupported
state-GPU cases skipped and eight CPU cases executed successfully. The CPU
training environment, saved experiments and learning settings were unchanged.

The [raw evidence](metal_routes_2026_10_26.json) retains every timing, outcome
histogram, complete input/result digest and capacity/resource setting.

```sh
tmp/gpu-mps-env/bin/python tools/benchmark_campaign_resident_routes.py \
  --batch-sizes 1 4 16 64 --repeats 5 --seconds 180 \
  --output studies/campaign/runs/another-fresh-route-result.json
```

CPU is still the only registered complete campaign backend. Recruitment effects,
other action/chance handlers, phase hooks, resident neural inputs and search
still need completion and complete-game measurements before a GPU training
throughput or playing-strength claim can be made.
