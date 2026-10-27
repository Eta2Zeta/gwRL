# Stage A: bounded order construction for self-play

24 October 2026. This pass changes the AI action interface. The preceding native
input pass improved the cost of an unchanged search; this pass changes which
steps constitute a search decision. Its trajectories, training targets and
effective lookahead can therefore differ from the old interface.

## Naval orders

The training profile, `campaign-orders-v1`, builds a fleet in ascending unit-ID
order. A start chooses the smallest ID in the eventual fleet; later choices
can add larger IDs or commit a legal route/engagement. Removing ships and
cancelling an unfinished selection are absent from this profile. Every offered
start/add has a legal completion, including groups whose aircraft landing
requirements make individual carrier moves invalid.

For any nonempty fleet, start with its smallest ID, add the remaining IDs in
order, and select its route. This gives each fleet one construction path,
without putting every possible fleet subset in the initial menu. A local
completion oracle first looks for a valid order for the selected ships, then
lazily checks additional carriers or aircraft cargo if joint landing capacity
is the obstruction. It never draws dice or executes a movement to find a
witness, and it imposes no arbitrary cap on feasible fleet subsets.

Screening-force selection follows the same ordered, add-only construction.
Real decisions during movement remain: declarations, blocked-port screening,
submarine/MAP reactions, battle choices and stopping or continuing after a
screening battle. The ordinary game API retains editable selections.

Two related correctness fixes apply to both profiles: a joint-landing failure
at an intermediate destination no longer hides legal longer routes, and a new
screening encounter starts a fresh selection instead of inheriting ships left
behind at the previous encounter.

## Other reversible choices

Raider designations and zero-distance carrier/deck assignments are real
configuration choices. The training profile retains distinct configurations
and suppresses returns to an already visited configuration while the rest of
the position remains unchanged. This preserves useful carrier-capacity
rearrangements, including temporary assignments. A real action, dice event or
phase boundary opens a new context for reconsideration.

An identical railroad-permission request is not offered again after rejection
in the same unchanged context. Different requests and reconsideration after
real progress remain available. Research, purchases, cargo operations, actual
retreat/stop choices and legitimate repeated dice results retain their rules.
Port-entry menus also omit a duplicate unload option when none of the cargo
belongs to the ship owner and that option would unload nothing.
Ordinary cargo loading/unloading already changes real assignments and consumes
movement or unloading commitments that prevent an unchanged reload cycle;
carrier aircraft reassignment was the reversible exception addressed here.

Visited configurations and refusals are readable source JSON in
`State.actionInterface`. The model observes the construction state that governs
its legal choices; that state is also cloned, keyed and saved with the position.
Execution RNG remains private. Invalid metadata is rejected during transactional
restore.

## Compatibility

`make_env` selects the training profile by default. The native `CampaignEnv`
constructor and curriculum API retain the ordinary game profile by default,
with an explicit `training_actions=True` option. Context and compatibility
metadata identify the training action version, and its engine rules ID differs
from the ordinary profile. Old learner/replay state cannot silently resume into
the new action contract. Historical recordings explicitly select their recorded
profile, and still require per-transition verification when sources differ.

The neural model architecture, terminal scoring, dice distributions, scenario
setup and MCTS implementation remain unchanged. Equal numerical simulation and
depth budgets now cover different decision sequences. Before/after timings are
operational completion measurements, not exact-trajectory speedups or evidence
of improved strategic strength.

## Measurements

The frozen-policy checks transfer the same saved neural weights into fresh
games. They use seed 1951, a 16-wide model with one message layer and 2,048 token
buckets. The earlier comparison is the native-input version at `ad6eec2`.

| Workload | Earlier interface | New interface |
| --- | --- | --- |
| Japan opening, 4 roots, 16 simulations, depth 16: mean warm search wave | 3.747 s | 4.227 s |
| One complete 11-round game, 4 simulations, depth 8 | 104.580 s | 107.835 s |
| Four two-round games, 16 simulations, depth 16, 240-second guard | 0/4 completed | 0/4 completed |
| Eight one-round training episodes, 4 simulations, depth 8 | 87.107 s; 386 decision records | 107.602 s; 434 decision records |

These runs do not establish a speedup. Even the opening query searches different
descendant menus, and complete games follow different actions and dice draws.
The training repeat also learns from different samples. The whole invocation
times include initialization, collection, learning and checkpoint/report work.

The primary stronger-search test stopped at 240.097 seconds with 380 decisions
and 60 dice events. Its unfinished scores remain null. It executed five naval
order starts, five ordered ship additions and four routes, with one unfinished
order at the wall-time cutoff. There were no cancel/remove actions or repeated
remembered configurations.

A separately recorded run changed only the wall-time guard to 600 seconds. All
four two-round games then completed in **310.088 seconds**, with 507 decisions
and 84 dice events. The primary run's first 550 semantic trace records match
that longer run byte for byte. It executed six naval starts and six routes,
with seven ship additions. This proves completion for this seed batch and
budget; it does not establish reliable completion across seeds or strategic
strength. The original four-minute failure remains part of the result.

The eight-episode training repeat completed both four-game batches. Collection
took 65.011 seconds and learning took 26.542 seconds; there were 32 Adam steps
per alliance. All 434 saved decision records use scores actually observed at
the end of their one-round episode, with no predicted replacement targets and
no discarded records. The actual games executed 12 naval starts and 12 routes.
Their 494 total transitions, stored inputs, action menus and ending scores were
independently replayed and checked. Initial neural parameters match the earlier
pilot; final parameters and optimizer state are not claimed to match it.

Sampled aggregate peak memory was 2.600 GB for the training repeat and 2.005 GB
for the longer stronger-search test. Measurements stayed within 12 CPU cores
and 30 GB, including coordinators and auxiliary validation. RSS sampling can
miss short peaks and can count shared pages twice. These are single runs,
without confidence intervals; a one-core diagnostic/replay overlapped some
collection measurements within the total allowance.

Raw artifact hashes, settings, terminal results and replay evidence are recorded
in [the machine-readable report](action_interface_2026_10_24.json). Remaining
work is to measure the cost of real rules/search and tensor preparation and
establish completion across seeds before increasing learning scale.

## Verification

All 297 Python tests and 26 C++ suites pass. New regressions cover every fleet
subset and route in small ordinary, strategic and engagement examples; every
branch of the corresponding construction trees terminates. They also cover
multi-carrier-only completions, zero-cost legal port sorties, separate later
screening encounters and unchanged declaration/submarine state and randomness.

Additional regressions cover raider outcomes, carrier swaps with zero movement
remaining, deck/land assignment at a port, refusal by another agent or an aligned
minor, reconsideration after real progress, and phase resets. Pending orders and
configuration records survive observation, clones, search reseeding and exact
checkpoint/replay round trips. Stale actions and invalid restores are rejected.

The previous 631-event, 11-round recording replays exactly in its recorded
ordinary profile, using explicit source-drift verification. All 560 search
menus/payloads, all actual observations and planning keys, and all serialized
state/execution-RNG hashes match. Its final state hash remains
`bbee2703a3170c75523add962be25a30d0ca9355c61d75be13898d408fc232cc`.

The new 11-round game's 633 transitions, the primary stronger-search prefixes'
440 transitions and the longer run's 591 transitions also replay exactly,
including menus, complete saved state and execution randomness. Fleet additions
are ordered, no removed editor choices appear, and no remembered configuration
is revisited. The small-budget 11-round game did not execute a naval order;
actual naval execution is covered by the stronger runs, training repeat and
native regressions above.

Rebuild and run the checks with:

```sh
./.venv/bin/python setup.py build_ext --inplace --force
cmake -S . -B build/action-interface -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/action-interface -j 3
ctest --test-dir build/action-interface --output-on-failure -j 1
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 ./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

These commands are sequential. During the measurements, the total allowance is
12 CPU cores and 30,000,000,000 bytes including workers and coordinators. Raw
traces, checkpoints, build/test logs and local instrumentation stay ignored in
`tmp/action-interface-2026-10-24/`.
