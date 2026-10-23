# M2: shared engine state and execution foundation

Status: **complete and verified on 21 October 2026**. All six CTest suites and
all 119 repository Python tests pass. No user decision remains for M2.

M2 implements the C++ foundation for the approved Japan–China campaign. It loads
the actual starting setup, represents mutable game state, validates actions at
the execution boundary, schedules turns and reactions, and saves/restores/replays
execution. Movement, purchase, politics and combat rules remain the later
milestones listed in the implementation plan.

## What is implemented

- One shared C++ engine library, `gw_engine`, containing the campaign foundation
  and the prototype code during migration. The new API is
  [campaign.hpp](/Users/home/Desktop/gwRL/include/game/campaign.hpp).
- A shared immutable definition retaining the complete extracted geography,
  source warnings, campaign contract and faction identities. Clones copy mutable
  state in memory; they do not reload files or duplicate the map.
- Separate national identity, territory possession, unit ownership, player
  control, alliance, power status and home-country membership. A missing account
  remains distinct from an account holding zero IPP.
- Stable unit identities, movement allowance/remaining movement, routes, origins,
  damage, commitments, owned cargo and reciprocal carrier links. Construction,
  repair jobs, technology stages, income components, diplomatic relationships,
  turn/game flags and beginning-of-turn snapshots are represented and serialized.
- Five phases and the approved CCP → Mongolia → Japan → KMT order. The horizon
  is eleven complete half-year rounds: 44 national turns through July 1941.
  A defender's pending decision pauses the active turn. Final collection and
  all pending reactions, chance events and battles must finish before termination.
- One authoritative legal-action check used by direct `step` calls. An altered
  payload, wrong player or wrong decision cannot bypass the offered choices.
  Failed transitions roll back both mutable state and execution randomness.
- D6/D12 requests, explicit raw faces, conditional rerolls, modifiers and outcome
  probabilities. Actual-game, search and training random streams are separate.
  Execution RNG state and future test tapes are absent from policy observations
  and planning keys.
- Exact checkpoint restore and deterministic event replay, including pending
  decisions/battles and exact 64-bit execution counters. Planning keys include
  the complete decision state, immutable definition identity and rules-module ID;
  audit history and execution RNG are excluded. Rules modules must keep all
  decision-relevant state in the explicit state fields and flags.

The loader preserves **99 deployed units, 22 facilities** (19 map facilities plus
three setup factories), two national ship queues with **10 IPP already paid**,
and **23 IPP opening cash**. Carrier assignments and Mongolia's separate identity
are unchanged. No USSR or FEC participant is created.

## Initialization and later rule modules

```cpp
auto initial = game::campaign::loadScenario(scenarioDirectory);
auto engine = game::campaign::Engine::start(std::move(initial), rulesModule, seed);
```

`Engine::start` captures the initial snapshot and invokes the first CCP
`beginTurn` hook once. Later turns receive the same initialization boundary.
Clone, restore and replay preserve the prepared state without re-running it.
The reserved `__campaign_started` flag rejects a second fresh start. The ordinary
constructor is a lower-level wrapper for an already prepared state.

The `Rules` interface supplies game choices, phase-completion conditions, action
effects, chance continuations and turn accounting. There is no permissive
production/combat implementation. A turn-end hook must explicitly complete
collection/accounting; the clock cannot silently assume it happened.

Untranscribed catalog movement is stored as unresolved. The national income
evaluator belongs to M6; an unevaluated rate has an explicit status. The existing
home-country table supplies Japan/KMT/CCP membership independently of current
possession. Unlisted nations' membership remains explicitly unresolved until the
source predicate is encoded, rather than being inferred from graph reachability
or current control. These representations permit later rule modules to require
the relevant definition before offering actions.

The runtime tests use explicitly named synthetic rule modules to verify these
protocols. Their phase advances are not evidence of implemented campaign
production, movement or combat. The benchmark uses the real 99-unit setup with
a synthetic control-flow module for the same reason.

## Verification

```sh
cmake -S . -B build/m2 -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/m2 -j 4
ctest --test-dir build/m2 --output-on-failure
./.venv/bin/python setup.py build_ext --inplace
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
build/m2/campaign_benchmark
git diff --check
```

| Exit criterion | Verification |
| --- | --- |
| Clone isolation and shared definitions | Nested-state mutations leave originals unchanged; cloning and restore work after source files are deleted. |
| Complete serialization | Full-state round trips include cargo ownership, damage, routes, builds/repairs, technology, snapshots, flags, pending choices/battles/chance and 64-bit counters. |
| Legal-action/application agreement | Every offered fixture action applies; wrong actors, changed payloads, premature phase ends and invalid direct calls fail without mutation. |
| Deterministic replay | Checkpoint plus recorded actions/chance events reproduces state and RNG exactly; mismatched rules and divergent events fail. |
| Decision ownership | Defender reactions route to the defender's player while preserving the active national turn; Mongolia routes directly to Comintern. |
| Complete deadline | All four nations receive eleven start hooks and finish eleven turns. Final collection can queue work without collecting twice or ending early. |
| Throughput baseline | Real setup clone, legal-action, planning-key and synthetic-transition rates are recorded in the benchmark artifact. |

The six CTest suites cover campaign state, campaign runtime, actual setup loading,
JSON integrity, prototype API boundaries and existing combat regressions. The
Python suite retains 119 tests. The prototype's clone now avoids disk reads, and
its public action execution rejects choices absent from its legal-action list.
The existing Python API and encoder shapes are preserved during migration.

See the [verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m2/verification.json)
and [benchmark results](/Users/home/Desktop/gwRL/docs/m2/benchmark.json).
The historical M0/M1 records remain intact; this implementation does not change
the approved scenario data. M3 adds the executable unit/facility catalog, and
subsequent milestones implement the game-rule modules on this foundation.
