# Engine, scenario loading and identity

The [architecture](../architecture.md) explains the complete system. This reference
covers the shared CPU state and execution contracts; the [scenario contract](scenario.md)
defines the approved regional setup. The implementation is in
[campaign.hpp](../../include/game/campaign.hpp),
[scenario loading](../../src/campaign_setup.cpp),
[state](../../src/campaign_state.cpp) and
[execution](../../src/campaign_runtime.cpp).

## Static geography and faction identities

[The theatre builder](../../tools/build_theatre_scenario.py) projects the explicit
[manifest](../../game_content/scenarios/japan_china_1936/manifest.json) from the world
map. Retained node and internal-edge fields stay equal to their source, including
directional terrain, rivers, infrastructure and unknown values. Removed neighbors
are recorded as boundary cuts and cannot be traversed. Facilities retain physical
identity across multiple access points; incomplete outside routes are cut rather
than reconstructed. Regeneration must not change the source map or manifest.

[The faction bridge](../../tools/scenario_factions.py) resolves declared map/setup
names and their case/whitespace equivalents to stable faction IDs. Display names
are preserved; unknown or ambiguous aliases are errors. For example, `Zhili Clique`
and `ZhiliClique` identify `warlord_beiping_hopeh`. Original nationality, initial
possession, national controller and alliance agent are distinct. A starting-owner
override does not rewrite nationality; Mongolia's Comintern control does not make
it Soviet or Chinese.

The immutable `Definition` holds geography, indexed relationships, catalog,
factions, Home Country membership and the campaign contract. Clones share this
definition and copy mutable state without reloading files. Unknown source facts
remain explicit; a missing treasury account differs from an account with zero IPP,
and an unevaluated income rate differs from an established zero rate.

## State and execution boundaries

`State` retains stable piece identities, possession, national relationships,
accounts, movement/routes/origins, damage, commitments, cargo/carrier links,
construction and repairs, technology, turn snapshots, political continuations,
pending decisions, battles and chance. The last pending decision owns the next
choice, even when its player differs from the active calendar nation.

Start a fresh game with `Engine::start(initial, rules, seed)`. It invokes the first
`beginTurn` hook exactly once. The lower-level constructor wraps prepared state;
clone, restore and replay do not restart a turn. The `Rules` interface supplies
choices, effects, chance continuations and phase/turn accounting. Final collection
and all pending work finish before the campaign becomes terminal.

| Operation | Contract |
| --- | --- |
| `legalActions()`, `legalInterrupts()` | Authoritative ordered choices for the complete decision state; immutable menus are reused while that state is unchanged. |
| `step(action)`, `interrupt(action)` | Validate the entitled actor and complete offered payload; failures preserve state and execution randomness. |
| `resolveChance()` | Sample the pending rule-defined chance request, including required rerolls; dice are not a policy action. |
| `applyChanceOutcome(key, outcome)` | Validate the complete current key and supplied faces/rerolls, apply normal effects/history, and preserve execution RNG. |
| `clone()`, `cloneForSearch(seed)` | Copy mutable state while sharing the definition; search clones reseed the search stream and remove test tape. |
| `serialize()`, `restore()`, `replay()` | Preserve exact execution state, counters, RNG and pending work; incompatible rules or divergent replay events fail. |

Actual, search and training random streams are separate. A planning key covers
the complete decision state, definition and rules identity; it excludes audit
history and execution randomness. `exactReplayIdentity()` instead identifies the
full serialized execution. Every decision-relevant condition must be explicit in
state; hidden mutable rule-module state cannot safely participate in caching.

The Python [CampaignEnv interface](../../include/game/campaign_env.hpp) exposes
these contracts through [bindings](../../src/python_bindings.cpp). Its observable
state and numerical training exports exclude future dice, execution RNG and audit
history. The [search reference](search.md) explains declaration scheduling and
why search uses the adapter rather than skipping raw interrupts.

## Verification references

- [State round trips and clone isolation](../../tests/campaign_state_tests.cpp)
- [Turn, reaction, chance, rollback and replay protocols](../../tests/campaign_runtime_tests.cpp)
- [Python environment boundary](../../tests/test_campaign_env.py)
- [Lossless theatre extraction](../../tests/test_theatre_extractor.py) and
  [faction identity](../../tests/test_scenario_factions.py)

Historical delivery measurements remain in the
[milestone archive](../archive/milestones/README.md). Use the
[development guide](../development.md) for build and check commands.
