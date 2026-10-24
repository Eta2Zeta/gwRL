# Japan-China full-rules theatre: implementation and RL plan

Status: **M0 frozen; M1–M12 implementation gates complete, 23 October 2026. M9 naval source review, two full 44-turn M10 campaign replays and the M11 multi-agent API/vector-search checks pass. RCL-014 is closed following developer clarification; RCL-015 remains provisionally adopted pending developer clarification. RCL-010 remains an adopted campaign interpretation. M12 neural training, evaluation and interruptible operations pass their bounded operational gate; the first eight-game Stage A pilot is complete, with robust playing strength still unestablished.**

Prepared 11 September; synchronized 23 October 2026 against the current repository,
the local Global War 1936 v4.3 rulebook/national sheets, and the user's decisions.
The user has authorized continuing M0 through M12, including the map/closed-scenario extractor,
faction identity bridge, shared C++ foundation, catalog, politics, movement, economy,
land combat, air and naval operations, campaign integration and the following multi-agent/search milestone.
The [M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md) and source-linked setup
files record the audit results and approved decisions. The [M3 catalog](/Users/home/Desktop/gwRL/docs/m3/README.md) records definitions,
source coverage and availability checks. M5–M10 supply the integrated gameplay
layers; M11 supplies the explicit API, approved terminal wealth calculation and
vector search. M12 supplies the neural learning/evaluation pipeline and bounded
foreground smoke checks. No large or background training experiment was launched.

On 22 October the user authorized completing M5-M8 autonomously until a real
decision or blocker is encountered. Source audits and public module interfaces
have started. Battle continuation data is now serialized, cloned and included in
planning identity, with regression coverage. The user settled the Dadao lend-lease delivery conflict on 22 October:
Japan may deliver aid to any Dadao-possessed Chinese Home Country land, retaining
ordinary legal supply-route conditions. RCL-010 records the sources and adopted
project ruling pending developer clarification. This is a delivery exception,
not a general redefinition of Dadao Home Country. Record future rule conflicts
in the shared clarification register for the user's developer reports.

**21 October 2026 handoff:** the
[M0 campaign review](/Users/home/Desktop/gwRL/docs/m0/README.md) records completed
verification and the [frozen baseline](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/frozen_baseline.json).
Reusable official-rule decisions and source checks
live in the
[shared rule clarification register](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md),
with stable RCL IDs. RCL-013 is adopted; RCL-014 is closed after developer
clarification, and RCL-015 remains a provisional project interpretation pending
developer clarification. This plan defines
the regional implementation and its scoped verification gates. The M0 historical
review predates the implemented gameplay layers.

## 1. Target and boundaries

Build a rules-faithful regional campaign containing Japan, KMT, CCP, all eight
Chinese warlords, and the relevant Mongolian and coastal geography. Use the
existing global map JSON as the geography source, extracting a smaller scenario
through a lossless bridge. Implement all units, facilities and mechanics these
participants can legally use, including capabilities unlocked later by technology
or Chinese evolution to Major Power.

The same rules engine must serve small tests, the regional campaign, and a later
larger map. The small campaign is a smaller **scenario**, not a second simplified
set of combat, movement or production rules.

This is a deliberately **closed regional scenario using v4.3 mechanics**, not a
simulation of the complete global game. Select explicit tiles from the global
map and remove every neighbor outside that set. There are no outside interfaces,
off-map movement, invisible reinforcements, required historical event schedules,
or substitute routes. A rule whose necessary nation, location or route is absent
is explicitly inactive in this profile; its reusable engine handler can still be
implemented for larger scenarios. The authoritative global map retains its real
outside connections; only the extracted copy is closed.

### Approved scenario decisions

| Decision | Current contract | Consequence |
| --- | --- | --- |
| Start | **July 1936**, using the approved official setup projection | 99 deployed pieces: Japan 48, KMT 12, CCP 5, warlords 32, Mongolia 2; 3 setup factories and 19 static facilities. Both ordinary Japanese queue ships are retained with 5 IPP already paid each. |
| Finish | **After the complete July 1941 round** | Eleven half-year rounds: July 1936, January/July 1937-1940, January/July 1941. Finish all included nation turns, reactions and collection before scoring. |
| Learning agents | **Axis, Allies and Comintern** | Three alliance-level policies, not one policy per nation. Nation turns, treasuries, legal relationships and minor controllers remain separate game concepts. |
| Objective | Each alliance maximizes its wealth minus the other two alliances' combined wealth | This is a three-player general-sum benchmark, not territorial conquest or the official global victory condition. |
| Boundary | Closed induced subgraph with all excluded neighbors deleted | No external agents, boundary contracts, aid interfaces or fabricated connections are required. |
| Geography | China/Mongolia area **excluding Tannu Tuva and Hong Kong**, including Manchuria and Korea; Tokyo, Honshu, Hokkaido, Kyushu, Okinawa; P14, P15, P16, P32, P33, P41 | 37 nodes: 31 land and 6 sea; the explicit manifest is authoritative. No automatic addition of reachable global neighbors. |
| Excluded participants/mechanics | No FEC or USSR accounts; no convoy play, interdiction or Kido Butai | Mongolia retains direct Comintern control and the USSR turn position; normal MAP, blockades and independently applicable naval movement/combat remain. |
| Small benchmark | Keep the tiny two-round scenario's budget, target, horizon and reward configuration separate | Replace/update all reusable mechanics in the shared engine; do not preserve a second incomplete game implementation. |

The default decision mapping is Axis -> Japan, Allies -> KMT, Comintern -> CCP.
Other included national/minor decisions are routed to the alliance entitled to
control them **under the rules**. Mongolia is not a CCP province or a Chinese
warlord. Warlord alignment, national identity and treasury ownership are never
collapsed into the three learning-agent labels. Reward rivalry does not itself
declare war or override the Chinese Truce.

Mongolia is directly controlled by Comintern and takes its movement and
recruitment phases in the normal USSR turn position, as if USSR were present:
**CCP -> Mongolia (USSR slot) -> Japan -> KMT**. Its identity remains Mongolian;
this timing does not create a Soviet participant, account, possession or unlock.

### Wealth definition and approved accounting decisions

For alliance `i`, the approved income/asset weighting gives:

```text
W_i = current_income_rate_i
      + 0.1 * (completed_unit_value_i
               + completed_infrastructure_value_i
               + treasury_i
               + paid_unfinished_construction_i)

R_i = W_i - sum(W_j for the other two alliances j)

completed_asset_value = purchase_price - remaining_repair_price
```

The user confirmed income means the **current income-per-turn rate**, not
cumulative collections; one point of that rate has the weight of ten IPP of
assets. Damaged units/facilities use purchase price minus their remaining repair
price; undamaged assets have zero repair deduction. Official setup units and
facilities count even though the learner did not buy them. A destroyed piece is
absent, not a surviving asset. No extra depreciation/floor convention is assumed.

Treasury and paid unfinished construction remain included at the same 0.1 asset
weight in the approved contract. This keeps spending cash on a normally priced asset from
changing wealth merely because its category changed. Repairing an asset similarly
reduces cash while increasing its net value. Do not substitute historical income
or pay the full wealth score repeatedly every turn. The adopted construction
policy scores cumulative already-paid amounts while a project is unfinished.
At completion, replace that entry with the full completed catalog value; do not
count both. The [source reconciliation](/Users/home/Desktop/gwRL/docs/m0/source_reconciliation.md)
establishes 5 IPP already paid for each setup queue ship; do not debit these past
payments from initial cash. Shared facility IDs and rail borders are
valued once, not once per directed access edge. Purchase-price tables for setup-only
types/discounts remain in section 6 and the M0 review. The user approved controlled
minor assets going to their controlling alliance and uncontrolled unaligned
assets going to nobody, without granting extra collection rights. Starting cash
is theatre-adjusted: Japan 15, KMT 6, CCP 2; minors zero; no FEC/USSR accounts. The capped-local
formula is documented in M0 as a scenario derivation, not an official setup rule.

On **21 October 2026**, the user approved the remaining city and railway scoring
choices. A city label has no additional asset price; its income and distinct
facilities still count. Count each undirected railway border once and split its
value 50/50 between the endpoint possessors. Endpoints credited to the same
alliance aggregate to the full value; an uncontrolled minor's share counts
toward nobody. This is scoring attribution only, with no change to railway
access, ownership or movement permissions.

These returns do **not** sum to zero: `sum(R_i) = -sum(W_i)`. Total wealth changes
with production, collection and destruction, so a three-value vector is required;
negating one opponent's value cannot reconstruct another alliance's objective.
This is a finite-horizon wealth benchmark, not a promise of historical strategy
or convergence to one globally best multiplayer policy.

## 2. What we have, and what cannot be reused unchanged

| Existing component | Useful foundation | Required change |
| --- | --- | --- |
| `game_content/maps/gw36_manual_map.json` and its generator | Authored global map, recent China/Canadian corrections, directional terrain and infrastructure | Audit the specified Japanese islands/seas; isolate remaining uncertainty. The scenario must be generated, never separately re-transcribed. |
| `src/setup_loader.cpp`, `include/game/types.hpp` | JSON loading and zone IDs | Current neighbors only retain ID and rail boolean. They discard terrain, passability, rivers, gauge, shared ports and crossing rules. |
| `GameState`, `Action`, `SimplifiedChinaMdp` | Clone, legal-action/step concepts, traces | Current implementation is a six-zone toy, not an extensible implementation of all five rulebook phases and reaction windows. |
| `BattleResolver` shared by map and composition environments | One shared combat implementation; artillery/TD regression coverage | Replace its fractional expected casualties and automatic decisions with authoritative dice/choice mechanics shared by both scenarios. Preserve relevant regression lessons, not an incomplete parallel resolver. |
| Units and encoders | Nine existing unit kinds and Python bindings | Only seven ground kinds fight; movement/purchases are restricted. Encoders cover only five types, omitting even existing armor. |
| Economy | Treasury, purchases, placement skeleton | No normal recurring income collection; cropping the map also changes computed income. Full production, queues, supply and repairs are missing. |
| Warlords | Some faction labels and a transfer helper | Current declaration shortcut transfers all warlords to KMT immediately. Replace it with rule-timed, conditional alignment. |
| `JapanTrainingEnv` | Python interaction and training examples | It auto-passes other nations. Its reward is income + 0.1 surviving unit value + 0.1 destroyed enemy value, not campaign victory. |
| Python MCTS and policy/value network | PUCT, optimistic first-play urgency, legal-action scoring, traces and replay concepts | Current search assumes one deterministic child per action; current scalar value conventions do not model a three-alliance stochastic campaign. |

Preserve the two-round learning problem and composition tasks as scenario
configuration: budgets, starting positions, targets, terminal conditions and
objectives. Their units, fighters, movement, production and combat migrate to the
same complete engine used by the campaign. Update or replace obsolete game code
and tests rather than keeping a parallel incomplete rules engine. Old saved
results may remain as historical artifacts with their original version metadata;
they are not directly comparable to new mechanics. Reject incompatible checkpoints.

## 3. Architecture we should build toward

Separate these responsibilities:

1. **Static definitions:** canonical geography, unit/facility catalogs, national
   rules and home-country definitions.
2. **Scenario manifest and bridge:** selected global IDs, initial forces, calendar
   horizon, closed boundary policy, three-agent mapping, objectives and rule profile.
3. **Mutable game state:** ownership/control, units, movement, damage, money,
   construction, research, diplomacy, pending battles, calendar and counters.
4. **Authoritative rules engine:** validates and applies decisions, resolves chance
   events, schedules reactions, and produces an auditable event log.
5. **Adapters:** human/debug interface, scripted agents, Python RL and MCTS. None
   of these reimplement combat or decide whether an action is legal.

Locations and responsibilities:

- `game_content/definitions/`: unit, facility and faction data with source citations.
- `game_content/scenarios/japan_china_1936/`: current manifest/extracted map;
  later initial setup and objective configuration. See its [scenario README](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/README.md).
- `tools/build_theatre_scenario.py`: implemented validated closed projection from
  the world map; it does not yet create a playable engine state.
- A separate small-scenario folder: the two-round budget, target, setup, horizon
  and reward only, not copied unit classes or a private battle resolver.
- `include/game/rules/` and `src/rules/`: phase, movement, combat, economy and political modules.
- Future `studies/japan_china_campaign/`: campaign adapters/search/training,
  using reusable learning components under `studies/shared/`. Existing
  composition and mini-Japan studies are already organized under `studies/`.
- `tests/`: source-linked rule fixtures, campaign traces and stochastic/search oracles.

Prefer explicit data and small rule handlers over adding a large collection of
nation-name conditions to `SimplifiedChinaMdp`. Unit identities may use a generated
registry or a consistently generated enum; the important requirement is one
complete catalog shared by loading, rules, encoders and tests.

## 4. Step-by-step implementation milestones

### M0. Freeze the scenario contract and rule checklist

Audit deliverables are now in [docs/m0](/Users/home/Desktop/gwRL/docs/m0/README.md).
They include source hashes, setup rows and totals, a core/national rules checklist,
price/repair tables and approved accounting decisions. The **decision review is
complete as of 21 October 2026**, including city and railway scoring. The **M0 exit
gate is closed**: the synchronized contract, setup, manifest, map, ledgers and
source checks passed final consistency review, and the full 106-test repository
suite passed. The specification is frozen in the baseline. Queue payments and
exact research thresholds are documented in the source reconciliation. No open
RCL applies to the current campaign.
Setup-only ship values, ordinary queue inclusion, paid construction scoring,
Mongolia timing, city/rail scoring and RCL-002–003/009 are adopted; RCL-001 and RCL-004–008 are closed. No audit data
is being presented as an executable initial state.

Depends on: the approved geography/calendar/agent and scoring decisions; verified
artifacts must precede those mechanics or training
targets.

- Create a rule ledger: source/version/page/section, applicability condition,
  required state, decision owner, timing, implementing module and acceptance test.
- Classify every relevant rule as required, conditionally reachable, explicitly
  inactive because its prerequisites are absent from the closed map, or unresolved.
  No silent omissions and no required outside input/event system.
- Compare the main rulebook with Japan/KMT/CCP national sheets. Record conflicts
  and interpretations rather than guessing a precedence rule.
- Inventory only official starting forces, facilities and construction queues
  on included tiles, including non-purchasable setup units. Omit off-map pieces
  and independently check the retained totals.
- Exclude Tannu Tuva by user decision. Its political identity and other outside
  ambiguities remain recorded on the global source but do not block this profile.
- Carry the resolved political rule decisions in section 6 into the synchronized
  specification and verification fixtures.

**Exit gate:** approved scenario contract and a traceable, complete rule checklist.
The output is a specification and test inventory, not a large training job.

### M1. Build the world-to-theatre bridge

**Complete and verified, 21 October 2026.** The
[M1 review](/Users/home/Desktop/gwRL/docs/m1/README.md) records the acceptance
evidence, outputs and regeneration commands. The existing map projection passes
its acceptance checks; the added faction identity index closes the remaining
name/ID normalization requirement. All 52 focused bridge/feature/identity tests
and all 119 repository Python tests pass. The
[M1 verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m1/verification.json)
records the checked artifacts. No user action remains for M1. The frozen M0
contract, setup data, manifest and map are unchanged; this plan's progress update
is subsequent to the historical M0 baseline.

The [convoy audit](/Users/home/Desktop/gwRL/docs/m0/convoy_audit.md) preserves the
printed Nagasaki and Tokyo routes as source reference only. The global map and
general extractor support convoy data, but this campaign disables that layer
by explicit choice. Do not activate Nagasaki merely because its route is local.

- Select explicit canonical IDs, not names or rectangular image coordinates.
  Include the existing Chinese theatre/warlords, Mongolia **without Tannu Tuva**, Manchuria,
  Korea, Formosa and Hainan; Tokyo, Honshu, Hokkaido, Kyushu, Okinawa; and
  only P14, P15, P16, P32, P33, P41. The manifest records the exact selected IDs.
  Hong Kong and all FEC forces are excluded.
- Do not add outside support nodes or interfaces. Retain nationality/control
  metadata; Mongolia remains distinct from the Chinese warlords.
- Copy every selected node and internal directed edge without re-transcription.
  Preserve `border_terrain` lists, passability, combat river crossing, river-route
  connectivity, railway presence, gauge, narrow-crossing capacity and facility IDs.
- Preserve facility IDs and all references to one physical facility. For
  example, Nanking's P14/P32 access points must not create two ports, repair pools
  or build capacities.
- Produce a **cut-edge report** for every excluded neighbor and delete all those
  entries from the extracted graph. The report is provenance, never a traversable
  route. Closed boundaries intentionally change the available geography; future
  movement, supply and blockade code must use the extracted graph, not consult
  the global map to restore shortcuts. Never invent a new sea or land connection.
- Keep scenario setup/control separate from static `original_owner` and terrain.
  Normalize faction IDs once, including `Zhili Clique` versus `ZhiliClique`.
  The generated `m1/faction_index.json` derives canonical IDs and aliases from
  approved setup data, preserving the user's display names and recording all
  31 retained land identities. Its shared resolver rejects unknown and ambiguous
  aliases; a valid starting-owner override does not rewrite original nationality.
- Save deterministic map/manifest hashes, source metadata, exact manifest and
  boundary cuts with the generated theatre. Preserve source warnings. Keep
  political/initial-state overrides out of the static projection.

**Exit gate met:** projection tests prove field parity, reciprocal infrastructure,
directional differences, shared-facility identity, valid references and explicit
handling of every cut; output reproduction must be byte-stable. The current
artifact is map data only. M0 now inventories forces/queues as specifications;
passing projection tests must not be presented as a playable full-rules scenario.

### M2. Define complete state, actions, time and randomness

**Exit gate met, 21 October 2026.** The
[M2 review](/Users/home/Desktop/gwRL/docs/m2/README.md) and
[verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m2/verification.json)
document the shared `gw_engine` library, actual setup loader, state/serialization,
authoritative action validation, five-phase clock, defender decisions, pending
battles/chance, separate RNG streams, exact replay and measured throughput.
`Engine::start` initializes the first CCP turn once; clone/restore do not repeat
the hook. The explicit synthetic rules used in protocol tests do not implement
campaign gameplay. M3 now supplies source-backed catalog movement; national
income evaluation remains explicitly unresolved until M6. M4 now resolves
unlisted-nation Home Country memberships from original mainland possessions.

Depends on: M0-M1; can start alongside catalog transcription in M3.

- Share immutable map/rules data; clone only mutable state in memory. Do not read
  the scenario from disk during each MCTS simulation.
- Separate original national identity, territory possessor, unit owner,
  controlling player, alliance, minor/major status and home-country membership.
- Route each legal decision to Axis, Allies or Comintern through the entitled
  nation/controller. Keep nation-specific turn order and accounts; do not merge
  national treasuries or give an alliance agent extra transfer permissions.
- Add stable unit IDs, exact movement remaining, routes/origins, cargo ownership,
  damage, pending commitments, build stages, repair jobs, technology stages,
  treasury/income components, diplomatic relationships and once-per-turn/game flags.
- Store beginning-of-turn possession and unit-presence snapshots. Many production,
  influence, supply, attrition and movement permissions depend on them.
- Model calendar turns, player turns, the five rulebook phases, pending decisions,
  reaction windows and resumable battles. The decision maker may be a defender
  rather than the nation whose player turn is running.
- Start July 1936 and end only after every included player has completed July
  1941, including end-of-turn collection and pending reactions: eleven full
  half-year rounds, not eleven individual nation turns.
- Provide validated actions for choices and explicit chance requests for dice.
  `step` must reject illegal direct calls too; a legal-action list alone is not
  protection against bypassing placement, purchase or phase-end restrictions.
- Represent the specified dice and distributions for each event: D12 combat and
  political rolls, D6 bombing where specified, and conditional rerolls/modifiers.
- Serialize state and event history for exact replay. Use separate actual-game,
  search and training RNG streams; future dice and hidden RNG state are never
  policy inputs. Controlled dice tapes are a test facility only.
- Distinguish exact replay identity from a planning transposition key. The latter
  includes every variable affecting decisions/outcome distributions, not a
  partially encoded observation or a future random sequence.
- Establish clone/transition/legal-action throughput baselines now; extend them
  with pathfinding and casualty-choice branching as modules arrive. Do not wait
  until the completed campaign to discover an unusable action representation.

**Exit gate met:** clone isolation, serialization round-trip, legal-action/application
agreement, invalid-action rejection, deterministic replay and decision-owner tests.

### M3. Implement complete unit and facility definitions

Depends on: M0; integrates with M2.

For every relevant type, record classes, attack/defense/movement, purchase and
construction costs, hit points, transport/carrier capacity, eligible targets,
first strike/support, terrain exceptions, technology/date/national availability,
purchase caps, placement rules, upgrade paths and rule provenance.

Coverage must include:

- Infantry classes: militia, regular infantry, airborne/elite airborne, marines
  and mountain infantry.
- Vehicles: cavalry, motorized/mechanized/advanced mechanized infantry, tank
  destroyers and light/medium/heavy armor. Cavalry is not ordinary infantry.
- Artillery: ordinary/self-propelled/advanced variants and anti-aircraft artillery.
- Aircraft: fighters, jet fighters, tactical/medium/strategic/heavy strategic
  bombers, seaplanes, air transports and heavy air transports.
- Naval units: submarines, advanced submarines, destroyers, light/heavy cruisers,
  battlecruisers, battleships/heavy battleships, light/fleet/heavy fleet carriers,
  naval transports and attack naval transports. Include setup-only torpedo boat
  destroyers and coastal submarines. No Coastal Defense Ship enters this closed
  scenario; broader source-only types may be supported by the shared catalog.
- Facilities: minor/medium/major factories; ports, dockyards, shipyards; airbases
  (the map's `airfield` alias); seaplane/submarine bases; fortifications, coastal artillery and
  rail infrastructure. Add strategic rockets and other chart-listed unlocks.

The national build charts are the exhaustive acceptance inventory; the list above
is organizational, not permission to omit an unlisted chart entry. Distinguish
"may exist through setup/capture/lend-lease" from "may currently be purchased".
Foreign-exclusive units need not become purchase options for Japan or China.

**Exit gate met (21 October 2026):** every setup type loads, all 181 printed
chart rows have availability tests, and every registered surviving unit damage
state can be represented in state and observations. See the
[M3 catalog record](/Users/home/Desktop/gwRL/docs/m3/README.md).

### M4. Implement the turn scheduler, politics and warlords

**Complete and verified, 21 October 2026.** The
[M4 record](/Users/home/Desktop/gwRL/docs/m4/README.md) covers political
transitions, timed declarations, pending end-of-phase work, Home Country
membership, warlord/influence/recruitment rules, truce/evolution and surrender.
It also records the user-approved direct Axis control of separate Dadao after
Japan surrenders. Capture callbacks consume results of later movement/combat
modules; income collection requires an evaluated rate or later accounting module.

Depends on: M2-M3.

- Implement Production -> Combat Movement -> Combat -> Non-combat Movement ->
  Place Units, including end-of-turn income and calendar advancement. Preserve
  permitted ordering within phases; do not force an arbitrary order where the
  rulebook allows choices. Declarations of war are timed rule events, not simply
  a mandatory standalone opening phase.
- Use the M2 clock and reaction machinery. Resolve the rulebook's unlisted-nation
  home-country predicate from source geography before any action relies on those
  memberships; an explicitly unknown membership does not grant permission.
- Use the adopted order CCP -> Mongolia (normal USSR slot) -> Japan -> KMT,
  including Mongolia's movement and recruitment phases as if USSR were present.
  The three agents receive those decisions without turning the calendar into
  three simultaneous alliance turns. Do not insert required outside-player events.
- Keep all eight warlords separate, including the two multi-zone factions.
  Implement attacks, control/alignment, recruitment where applicable, unit and
  territory transfers, influence, and faction revival at the specified time.
- Implement foreign attacks on China and the adopted RCL-003 end-of-combat
  alignment process: evaluate relevant neighbors across each warlord's
  territories, apply the existing table once per whole warlord, and transfer its
  territories and units together. Include optional Chinese Truce, shared
  defense/access and truce breaking.
- Add Dadao creation, influence spending/backfire, recruitment and later alignment.
  A controlled minor is not automatically incorporated into its controller.
- Implement controlled-minor recruitment choices: troops, eligible ship-build
  advancement or full facility repair. Controlled minors generally collect no
  ordinary IPP income. CCP's special recruitment is a separate national rule.
- Implement KMT/CCP evolution at 13+ territorial IPP, capital choice, one free
  appropriate factory, changed abilities/roster, and same-turn exceptions.
  The evolution factory and the national objective's factory are the same award,
  not two separate free factories.
- Keep war with a Minor Power distinct from war with a Major Power. Handle
  surrender, loss of forces, revival, capture/liberation and national objectives
  with their distinct triggers; zero units is not a universal terminal condition.

**Exit gate met:** scripted political timelines cover ordinary and exceptional
alignment, two-zone warlords, truce formation/breaking, evolution, and Dadao,
including pending-decision serialization/replay and the direct Axis fallback.

### M5. Implement movement and shared logistics services

Status: complete, 22 October 2026; 14 movement fixture groups and a dated verification record.

Depends on: M1-M4. Complete this before final production legality in M6.

- Land path validation, friendly/neutral access, movement exhaustion, terrain and
  combined terrain, impassable boundaries and special unit exceptions.
- Preserve each attacking contingent's origin and approach edge; allow the same
  unit type to join one battle from multiple sources. Do not apply one border's
  river penalty to every attacking unit.
- Distinguish ordinary movement, blitz, narrow crossings, strategic rail/river
  movement and supply paths. They have different eligibility and capacity rules.
- Implement regional rail capacities, gauge changes, rail damage and river-bank
  restrictions. The map's rail boolean remains infrastructure presence, not damage.
- Build reusable route queries for supply, naval-facility range refresh, blockade
  and required possession timing. Interdiction is disabled; named straits/canals
  absent from the selected map remain inactive.
- Implement reusable Burma/Ledo and Soviet-connectivity predicates with their
  specific conditions. Burma and Soviet Home Country endpoints are absent, so
  those bonuses are inactive. The purchase rule retained in closed RCL-004 requires an
  undamaged railroad from CCP-possessed to Soviet-possessed land during Production,
  with placement in connected CCP-possessed territory. It is also inactive here
  because USSR is excluded. Mongolia's turn timing does not change possession.
  Never reconstruct cropped paths or make the Himalaya traversable.
- Establish movement/cargo/landing interfaces needed by the air/naval milestones.

**Exit gate:** small route puzzles cover asymmetric river penalties, gauge change,
bombed rail, hostile river banks, shared ports, cut boundaries and supply-only roads.

### M6. Implement economy, production, construction and research

Status: complete, 22 October 2026; 14 economy fixture groups and a dated verification record.

Depends on: M3-M5.

- Explicitly approved local starting treasury/queues, normal collection,
  territorial income, reachable national bonuses and losses. No automatic
  off-map income ledger or full-global treasury assumption.
- Purchases, date/technology/national caps, staged build queues, uncompleted builds,
  facilities and upgrades, research limits/stages and calendar gates.
- Production and repair capacity, beginning-of-turn possession, supply checks,
  placement restrictions and newly upgraded-facility timing; no interdiction.
- Chinese decentralized production and CCP recruitment; correct changes on
  evolution to Major Power. KMT Burma Road and CCP Soviet-Home-Country income
  bonuses are inactive here. CCP artillery/AAA rail access has the distinct
  RCL-004 condition and placement restriction; it is inactive here because no
  Soviet-possessed land can exist in this USSR-excluded campaign.
- Japanese Chinese-territory bonuses: do not gate the six China-control bonuses
  on a Major-Power war when the Japan sheet exempts them. U.S. oil trade and other
  absent-nation benefits are inactive in this profile, not supplied by hidden events.
- Capture/liberation effects, treasury capture where applicable, facilities,
  destroyed cities, construction damage, repairs and capital-dependent income.
- Track cumulative already-paid construction separately from completed assets.
  At completion, replace it with full catalog value so the later wealth objective
  can count treasury and work in progress without double counting.

**Exit gate:** accounting tests reconcile every IPP and construction item across
several turns. Captured-on-this-turn and repaired-on-this-turn examples match sources.

### M7. Implement the authoritative land-battle state machine

Status: complete, 22 October 2026; 32 land-combat and 15 shared-zone truce fixture groups, including developer-confirmed third-party roles, corrected voluntary truce roles, attack-roll Low Morale, ordinary retreat origins and exact replay.

Depends on: M2-M6.

- Rulebook D12 rolls and integer units; event-by-event battle progression rather
  than a single opaque "resolve entire battle" operation.
- First-strike timing, air-superiority/AAA integration points, simultaneous return
  fire, artillery pairing recalculated from survivors, target selection and fallback.
- Give normal casualty selection to the entitled player and targeted selection to
  the firing player, with eligibility constraints. Heuristic selections are agent
  policies, not fixed game rules.
- Apply approach-side terrain and rivers versus whole-territory terrain, duration
  of first-round effects, combined modifier rules, cities/surrounded cities,
  fortifications and national/unit exceptions.
- Retreat choices and legal origins, city three-round limits, airborne/amphibious
  exceptions, capture, blitz and attrition attacks.
- KMT low morale, including empty-territory attacks and origin-specific retreat.
  Retreating low-morale units cannot be chosen as casualties. The separate KMT
  truce-breaking rule eliminates affected units in shared territory on 10-12;
  it must not be treated as an ordinary retreat to an origin.

**Exit gate:** rule-linked battle fixtures, exact small-battle probability checks,
casualty/retreat choice tests and a replayable ground campaign. This milestone alone
is **not** completion of the Japan-China theatre.

### M8. Implement air operations, bombing and defensive reactions

Status: complete, 22 October 2026; 40 air fixture groups. RCL-013 is adopted and implemented. See docs/m8/README.md and its verification record.

Depends on: M5-M7.

- Aircraft movement/range, flight permissions, legal landing plans and remaining
  movement; distinguish aircraft capture limitations from land occupation.
- Air superiority, tactical bombing, strategic bombing, interception, scrambling,
  Airbase behavior (the current map calls these `airfield`), facility AAA and
  technology modifiers. Do not invent a separate unpriced Airfield facility.
- Air transport, airborne assault, cargo limits, first-round rules and retreat.
- Bombing cities, facilities and railroad borders; damage caps, repair costs,
  inoperability and special construction/city effects.
- Railroad bombing affects **all tracks on the selected border**, so no named
  track IDs return. Key infrastructure by border endpoints; explicitly settle
  targeted-side ownership/damage/repair semantics from the source before encoding
  damage state. Do not infer the bombing cap from a unit's combat entry penalty.

**Exit gate:** bomber/AAA/interception, border-rail bombing/repair, airlift, airborne
and failed-landing scenarios with full decision/replay traces.

### M9. Implement naval, carrier and amphibious operations

Status: complete, 23 October 2026; source exit verified with four combined naval/landing traces. RCL-014 now follows the developer clarification: evacuating ships defend and the fleet already at sea attacks. Earlier source-exit evidence retains the superseded provisional roles. See docs/m9/README.md.

Depends on: M3, M5-M8.

- Naval movement, transport loading/unloading, capacity, multi-hit ships, carrier
  aircraft, naval combat, screening/continuing forces and retreat.
- Submarines/submerging, normal maritime air patrol and blockade. Preserve
  independently applicable Battlecruiser raider/slip movement and combat rules.
  Convoy raiding, interdiction and their dependent escort responses are disabled;
  do not create missions from the reference-only convoy layer.
- In-port operations, scrambling, port attacks, capture/scuttling, skeleton crews,
  dockyard repairs and strategic naval movement.
- Complete amphibious sequence: naval clearance, shore bombardment, coastal
  artillery, first-round casualty rules, transports and withdrawal restrictions.
- Japanese destroyer transports, relevant national naval/air abilities and
  technology variants. Abilities requiring an absent outside nation/event, such
  as the relevant U.S.-war conditions, remain inactive here. Keep the reusable
  predicates for future larger maps rather than granting them for fighting China.

**Exit gate:** scripted Japan-to-China reinforcement voyage and amphibious landing,
including contested movement and retreat variants, reproduce expected rules;
convoy/interdiction exclusions are enforced.

### M10. Integrate a complete regional campaign and certify coverage

Status: complete, 23 October 2026; two full 44-turn campaign traces, exact replay, transition invariants and all 143 M0 ledger rows indexed to executable evidence or profile exclusions. RCL-015 is provisionally adopted. See docs/m10/README.md.

Depends on: M0-M9.

- Run the approved local July 1936 setup through full calendar rounds with all
  three alliance agents making their nations' and legally controlled minors'
  decisions. Finish a trace through the end of July 1941.
- Exercise warlord conversion, evolution, contested in-map supply, mixed
  land/air/sea combat and reachable once-per-game abilities together. Verify
  outside-dependent benefits remain unavailable rather than leaking into play.
- Add human-readable snapshots, action explanations and replay navigation early
  enough that the user can verify concrete turns, not just read aggregate scores.
- Test invariants after every transition: no duplicate/lost units except logged
  creation/destruction, legal cargo and landing, valid owners, nonnegative money,
  bounded capacities and no stale pending battles or decisions.
- Every rule in the ledger needs a passing test or an explicit profile-based
  inactive reason. Unimplemented reachable mechanics block "full theatre" status.
- Migrate the tiny two-round and composition scenarios to this same engine.
  Preserve their scenario-specific learning tasks while replacing incomplete
  reusable mechanics; no separate legacy combat/movement/unit implementation.

**Exit gate:** reviewable end-to-end traces and completed rule ledger. The global
map's existing structural tests are useful but are not proof of gameplay fidelity.

### M11. Expose the multi-agent environment and upgrade MCTS

Status: correctness exit complete, 23 October 2026; actual campaign API and wealth checks pass, with 16 exact-oracle/search tests and six Python binding tests. See docs/m11/README.md. Batched neural inference and performance profiling are completed under M12; the M11 verification record remains a historical snapshot.

Depends on: M2; tactical integration can begin at M7; campaign use requires M10.

- Expose `current_decision_player`, decision kind, legal actions, observations,
  apply-action, chance handling, returns, clone and serialization. Do not hide
  defender choices or auto-pass opponents in the authoritative API.
- Use registry-driven entity/graph observations with all rule-relevant statuses,
  not a fixed five-unit flat vector. Keep ownership, controller, relationships,
  time, origin, supply/damage and pending reactions distinguishable.
- Continue scoring a variable legal-action set. Factor very large choices into
  source/group/path/target/count decisions without exposing future information or
  illegally changing commitment order. Canonicalize interchangeable units only
  when their movement, cargo, origins and other statuses really match.
- Model chance outcomes explicitly or sample them with separate successor-state
  nodes. One action can lead to multiple states. The policy does not choose dice.
- Use a consistently ordered `[Axis, Allies, Comintern]` return/value vector.
  Each decision optimizes the entitled controlling alliance's component; neither
  same-scalar backup nor automatic sign-flipping is correct for this wealth game.
  Political access/truce rules remain independent of the reward vector.
- Distinguish multiplayer self-play from a best response to fixed opponents.
  In the latter, search must use/sample the same versioned scripted opponent
  policy used by the environment, rather than assume every opponent optimizes
  a different policy during search. Record this search assumption in run metadata.
- Keep tested optimistic first-play urgency and PUCT diagnostics; **do not force
  every legal child to be visited once**. Training-only root noise and evaluation
  settings must be separate. Tune exploration only against measured tests.
- Root reuse and complete-state transpositions are implemented. Do not retain a
  subtree for a different observed dice outcome, rule profile or opponent-policy
  version. Batched model inference and action-generation profiling are explicitly
  carried into M12's performance work before expensive training.

**Exit gate:** compare MCTS with checked-in exact solvers on tiny deterministic and
stochastic games using stated value-error/regret tolerances and confidence across
seeds. Handle consecutive same-player decisions/reactions; test action-order
robustness and convergence as search budget increases. Tied optimal actions need
not have identical visit counts. This is empirical validation, not proof of a
globally optimal full-campaign strategy.

### M12. Add rewards, evaluation, curriculum and training operations

Status: operational exit gate complete, 23 October 2026. Delivered in three chunks:
entity-graph models and batched inference; resumable parallel training; held-out
evaluation, profiling and bounded foreground smoke. All 212 Python tests and 24
C++ suites pass. See docs/m12/README.md. The approved terminal wealth evaluator
remains unchanged. No large training run or playing-strength result is claimed.
The initial executable curriculum varies the real calendar horizon; broader
starting-position curricula and opponent leagues remain subsequent experiments.

Depends on: finalized wealth valuation/local setup in M0; M10-M11 for training.

- Implement the section 1 terminal wealth-gap vector at the end of the full July
  1941 round. Use current income rate plus 0.1 times completed assets, treasury and
  paid construction. Value units/facilities at purchase price minus remaining
  repair price, including official setup assets. Do not silently
  replace it with territorial conquest, zero-sum faction rewards, or toy rewards.
  If the value head needs numeric scaling, use a documented positive scale and
  report the original IPP-like units; arbitrary clipping changes the objective.
- Start without arbitrary kill/purchase bonuses. If dense shaping is needed,
  consider documented potential-based shaping and test for capture/recapture,
  purchase, unit-transfer, self-destruction and phase-passing reward exploits.
- Discount by consistent game time, not arbitrarily by every UI-like micro-action.
  Distinguish true terminal states from training truncation for value targets.
- Build active scripted baselines for all three sides, then train all three
  alliance policies between self-play batches as described in section 5. Warlords
  are controlled only when the rules grant control. Keep independent allied
  nation accounts and rules even though they share one policy/reward component.
- Test wealth accounting around purchasing, completion, damage, capture,
  recruitment and alignment. Asset transfers must not leave value on both sides;
  unchanged wealth cannot earn repeated rewards merely by passing phases.
- Curriculum: individual rule puzzles -> exact tiny dice battles -> one-turn
  combined-arms tasks -> short campaigns -> full regional campaigns -> opponent
  league. Vary initial positions, unit availability, map extent and duration while
  keeping the same authoritative rule implementation.
- Use held-out starting states, dice seeds and opponent versions. Report all three
  raw wealth values/gaps and their components with uncertainty, territorial
  control, economy, casualties, game length, illegal actions, value calibration
  and decision throughput. A high score
  against passive China or one lucky seed is not evidence of a strong strategy.
- Provide flushed live progress, per-phase/debug traces, periodic resumable
  checkpoints including optimizer/replay/RNG/configuration, graceful interrupt,
  run manifests and schema/hash compatibility checks.
- Complete batched neural inference and further factorization of large action
  menus; profile clone, rules, action generation and network inference. Estimate runtime
  from a short foreground smoke run before proposing expensive settings.

**Exit gate:** a reproducible smoke run can be interrupted/resumed and evaluated
against fixed baselines. Supply commands for the user to start and monitor large
runs in the foreground. Do not launch large or background runs automatically.

## 5. Training candidates: search-guided self-play and direct policy learning

No learning algorithm has yet been established as best for the full campaign.
The user discussion on 21 October keeps two serious candidates: modern
AlphaZero-style neural-guided stochastic search, and a masked/factorized PPO
policy trained against the same opponent pool without search at every training
decision. Compare strength under equal hardware, training time and decision-time
budgets, using held-out positions, opponents and dice seeds. PPO is a competing
baseline, not merely a fallback. See the [PPO paper](https://arxiv.org/abs/1707.06347).

Three sides do not make search-guided self-play unusable. Its candidate branch
keeps neural policy/value guidance, search-improved move targets and self-play,
with three alliance returns and explicit dice. Consider limited-budget search
and sampled-action improvements after the exact tiny search tests pass; neither
newer algorithms nor existing prototype results establish a winner for GW36.
The following stages describe that search-guided candidate and its opponent
pool; comparable direct-policy training uses the same authoritative engine,
objectives and evaluation conditions.

Training efficiency is a standing implementation requirement in
[AGENTS.md](/Users/home/Desktop/gwRL/AGENTS.md), alongside rule correctness.
The current prototype has neural policy/value guidance, search visit targets,
batched inference and self-play, adapted to three alliances and explicit dice;
this does not establish production-level efficiency. Reference implementations
demonstrate batching, inference caches and compiled execution:
[OpenSpiel AlphaZero](https://github.com/google-deepmind/open_spiel/blob/master/docs/alpha_zero.md)
and [DeepMind Mctx](https://github.com/google-deepmind/mctx). These are engineering
references; the campaign's tested multiplayer values and dice semantics must
remain intact. Reuse unchanged decision data, reduce repeated data conversion
and measure complete-game costs before expanding training within the current
12-core/30 GB allowance.

AlphaZero did not permanently assign a frozen policy to one color while training
the other. One network played both sides, guided by MCTS. Search produced policy
targets; completed games supplied outcome targets; training updated the network
and later self-play used its latest parameters. The older **AlphaGo Zero** used a
best-player promotion gate: a candidate replaced the incumbent after winning at
least 55% of their evaluation games. AlphaZero removed that gate and continuously
updated a single network. These are distinct procedures. See the [original
AlphaZero paper, page 3](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphazero-shedding-new-light-on-chess-shogi-and-go/alphazero_preprint.pdf).

Multiplayer AlphaZero has been demonstrated in two small three-player games;
that establishes feasibility, not a convergence guarantee for this campaign.
[Petosa and Balch, 2019](https://arxiv.org/abs/1910.13012). OpenSpiel provides an
independent implementation reference for n-player, general-sum MCTS with chance
nodes and decision-maker-indexed returns. Borrow those conventions, not its
unrelated exploration defaults: retain our tested FPU/PUCT behavior.
[OpenSpiel MCTS](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/algorithms/mcts.h).

### Stage A: validate multiplayer search and latest-policy self-play

Status, 23 October 2026: search and training checks pass; the first pilot finished
eight genuine one-round self-play episodes and 32 sampled optimizer steps for
each alliance. All 386 labels use terminal outcomes. Paired held-out evaluation
finds better Axis completion and much smaller value error, with unchanged Allies/
Comintern scores on two dice seeds. This is an early Stage A result, not a
completed strength/generalization gate. See [the pilot report](/Users/home/Desktop/gwRL/docs/stage_a/README.md).

The first performance follow-up repeats the same eight games in 118.68 seconds,
compared with 346.62 seconds originally, with identical actions, policy targets
and final game states. At that revision, all 241 Python tests and 24 C++ suites
pass. The subsequent scaling follow-up completes 13 bounded cases covering
deeper search, later positions, larger models and longer horizons. One
small-budget full campaign completes, while the 16-simulation two-round batch
reaches its time guard without a completed game. Larger training remains on hold
for the measured legal-menu/observation and input-construction performance work,
followed by matched benchmarks and a completed stronger-search collection batch.
See [the scaling report](/Users/home/Desktop/gwRL/docs/stage_a/scaling_2026_10_23.md);
the pilot repeat alone does not establish scalability.

Before campaign learning, check the shared search against exact tiny deterministic
and stochastic three-side fixtures. Then start with this synchronized loop:

1. Keep one policy for each of Axis, Allies and Comintern, with compatible action
   encoding and three-component value predictions.
2. Freeze a snapshot of **all three** policies for a rollout batch. Their legal
   nation/minor decisions produce complete self-play episodes, MCTS visit targets
   and terminal wealth-gap vectors. No policy changes halfway through that batch.
3. Train all three policies from the batch/replay data, routing policy-loss samples
   to the alliance that made each decision. Value targets retain all three sides.
4. Publish the three updated snapshots together and generate the next batch.
   Thus opponents improve between batches; none is the permanently frozen side.
5. Archive checkpoints from the start and evaluate separately against fixed
   scripted and historical **pairs** of opponents, with held-out dice. Compare
   each side's expected wealth gap under the same opponent combinations, not
   scores against opponents that change between evaluations.

At each ordinary search decision, choose using the acting alliance's component
of the value vector (a Max-n-style convention). The two other alliances each
optimize their own wealth gap; do not combine them into a single opponent that
jointly minimizes Japan's reward. This also handles defender choices and multiple
consecutive decisions by the same alliance. At chance nodes, sample the actual
rule-defined dice distribution rather than select favorable outcomes. Keep value
outputs in a fixed alliance order and fixed positive scale; no zero-sum sign flip
or clipping that changes the wealth objective.

### Stage B: add archived opponents when evaluation shows overfitting

Latest-only co-training can learn to exploit a narrow set of current opponents,
then forget earlier counterstrategies. A small opponent pool is the next planned
robustness layer, not a second unrelated learning algorithm:

- Retain a bounded, diverse set of checkpoints for each side plus simple scripted
  baselines. Mix some historical-opponent games into current self-play; select
  the mix using measured forgetting/cross-play results, not an assumed optimal
  percentage or a huge default training job.
- Rotate the current learner: one game may train Axis against a frozen Allies/
  Comintern pair; another trains Allies; another Comintern. All sides improve
  across training batches; none stays the fixed opponent indefinitely.
- In these fixed-opponent best-response games, the learner's search must sample
  the frozen opponents' **actual deployed action distributions**. Do not secretly
  re-optimize an old opponent with current Max-n search. If a deployed opponent
  includes MCTS, its model/version, search settings and budget are part of the
  opponent policy; a raw neural prior is not an equivalent replacement.
- Record both opponent identities and search modes with experience. Keep recent
  replay for latest-self-play targets; use profile-conditioned value estimates
  or explicitly separated training data/value models for fixed-opponent tasks.
  A board state alone does not determine its value under different continuation
  policies; do not silently mix incompatible targets or reuse their search trees.

This borrows the opponent-mixture motivation of Policy-Space Response Oracles
(PSRO), not its full empirical-game/meta-strategy machinery. Full PSRO would add
payoff estimation across many policy combinations and a meta-solver; that is
unnecessary for the first local implementation. [Lanctot et al., NeurIPS 2017](https://papers.nips.cc/paper_files/paper/2017/hash/3323fe11e9595c09af38fe67567a9394-Abstract.html).

### What success means, and the compute comparison

- First learn the small two-round task and short shared-engine tactical/campaign
  fixtures, then increase horizon to the full July 1941 scenario. Do not substitute
  simplified combat or transfer old incompatible value targets/checkpoints blindly.
- Evaluate each side across fixed opponent pairs, several dice seeds and training
  seeds. Report raw wealth components, mean gap, uncertainty, weaker matchups and
  performance with and without search. In a general-sum multiplayer game, a single
  aggregate win rate or rising co-training reward is not sufficient evidence.
- Periodically test an approximate best response: hold two opponents fixed and
  see how much a fresh/improved policy for the third can gain. Repeat for all
  sides. This measures discovered exploitability, not an exact equilibrium proof.
- Start with terminal wealth targets and no arbitrary kill/purchase bonus. Any
  later dense shaping must preserve the stated terminal objective. Test accounting
  for repair, construction completion, setup pieces and captured facilities.
- Compare search-guided training against masked PPO with side-specific
  policies/value estimates and the same opponent pool and objectives. Measure
  strength per training time and decision cost; also test search added to a
  directly learned policy. No candidate is assumed to win beforehand.
  A cooperative shared-reward algorithm is not a drop-in fit for these rival sides.

The aim is **robust performance against a stated, measured opponent distribution**.
There is no promised uniquely best strategy independent of the other two players,
nor a practical guarantee that this self-play procedure converges to equilibrium.

Freezing rollout snapshots is an engineering choice for reproducibility and
consistent search targets. Later asynchronous collection can be considered after
correctness and profiling. Policy parameter sharing across alliances is optional
future experimentation; three decision-making sides are the fixed contract.

### Closed-map applicability policy

The map is deliberately local. No external-world interface is a prerequisite for
this campaign. Missing Burma/Ledo/USSR rail paths, absent aid senders, U.S. trade
conditions, excluded holdings and global event prerequisites do not create
resources, routes or active abilities. Record the corresponding rule as inactive
with its missing prerequisite. The shared engine may implement/test such handlers
on separate complete fixtures for future expanded maps.

Included Formosa and Mongolia retain their source national
identity; Chinese home-country membership alone does not transfer ownership or
give permission to attack. Setup/political interpretation must be resolved where
needed, rather than answered by expanding the map or inventing an outside turn.
Tannu Tuva is not included and its political ambiguity is deferred.

## 6. Recorded rule decisions and later implementation responsibilities

1. **Remaining valuation-table details:** current income rate, asset weight 0.1,
   purchase-price-minus-repair valuation and inclusion of setup assets are decided.
   Transcribe prices/repair costs and reconcile non-purchasable setup types,
   discounts and upgrades without assigning setup assets zero merely
   because they were initially free. Cash and paid construction use the same 0.1
   coefficient as the explicit interpretation in section 1. Unpaid future
   construction obligations are not completed assets.
   Minor attribution is now approved: controlled/aligned assets go to the legal
   controller's alliance; uncontrolled unaligned assets go to nobody. Setup-only
   values are adopted: Torpedo Boat Destroyer 5 IPP and Coastal Submarine 4 IPP.
   City and railway scoring were approved on 21 October 2026: city labels have no
   additional asset price; each undirected railway border counts once, split
   50/50 between endpoint possessors. Same-alliance endpoints aggregate to full
   value, and an uncontrolled minor's share counts toward nobody. The railway
   split affects scoring only.
2. **Initial local accounts/setup:** theatre-adjusted cash is authorized and M0
   uses Japan 15, KMT 6 and CCP 2; FEC is excluded. Both ordinary Japanese national
   queue ships are retained and score their cumulative already-paid amounts.
   Source reconciliation establishes 5 IPP paid for each ship, with 5 remaining
   for the Heavy Cruiser and 10 for the Fleet Carrier. USA-triggered Light Carrier
   entries are excluded and carrier attachments are recorded in M0.
   The user chose official pieces on included tiles only; do not import outside
   forces or an assumed full-global budget.
   Use the fixed July 1941 full-round deadline; no extra early terminal rule is
   introduced. Both ships use eligible supplied shipyards; Fleet Carrier placement
   requires a Major Shipyard. P15's Fleet Carrier carries one Fighter and one
   Tactical Bomber; the Light Carrier carries one Fighter.
3. **Warlord foreign-war rolls, adopted RCL-003:** always resolve each whole
   warlord once. Evaluate relevant neighbors across its territories and apply the
   existing alignment table once; the result covers all its territories and units.
4. **Influence spending, adopted RCL-002:** pre-roll spending is capped by the
   unmodified success threshold. Preserve the natural-12 backfire and
   beginning-of-turn influencing-zone requirement.
5. **CCP Soviet route, closed RCL-004:** the user reported on 17 October 2026 that
   the developers fixed the wording for the next version; no publication or version
   number has been independently checked. The mechanic remains unchanged:
   during Production require an undamaged
   railroad from CCP-possessed to Soviet-possessed land, and place qualifying
   purchases in connected CCP-possessed territory. Generic river/sea supply is
   insufficient. The separate **income bonus** requires Soviet Home Country.
   Both abilities are inactive in this USSR-excluded campaign; Mongolia's
   identity and USSR-slot turn do not create Soviet possession.
6. **Map/political uncertainties:** Kobdo-Novosibirsk, southern Sinkiang/Himalayan contacts,
   Sinkiang-to-Eastern Kazakhstan's river penalty, and Tannu Tuva identity remain
   unresolved in the source map. Excluded external edges are cut away, not
   certified by copying. Tannu Tuva is explicitly excluded; defer its national
   identity/home-country/controller interpretation to a future expanded profile.
7. **Rail damage implementation:** all drawn tracks on the chosen border are
   affected. Implement targeted-side ownership, repair responsibility and terrain
   caps from the reconciled sources in the later catalog/movement/economy/combat
   milestones, without bringing back named railroad segments.
8. **In-scope Japanese setup:** preserve the audited starting forces and queue
   stages; no unprinted in-port, damage, cargo or MAP status is invented.
   Printed setup totals include queued ships; do not also instantiate them on-map.
9. **Choice explosion:** player-selected casualties, paths and grouped attacks can
   dominate search. Use equivalent-unit grouping and staged choices, never illegal
   pruning disguised as a game rule.
10. **Stochastic learning:** use exact probability fixtures and held-out evaluations;
   neither deterministic fractional combat nor memorized dice seeds proves robust play.
11. **Version conflicts:** retain source versions and documented interpretations;
    changes invalidate affected rule fixtures and training/checkpoint compatibility.
12. **Kamikaze source check closed:** the ability activates when USA reaches
    Wartime Income. The supposed alternative trigger was our misreading of the
    parenthesized Light Carrier build-queue footnote, not conflicting Kamikaze
    rules. See the shared register's closed-source-check section. No outside
    U.S. event is fabricated for this campaign.

## 7. Verification policy and implementation order

The main dependency chain is:

**Contract -> bridge/state/catalog -> politics/movement/logistics -> economy ->
land/air/naval mechanics -> complete campaign -> validated search -> training.**

The map/extractor and M0 audit data are verified and the specification is frozen.
M2 now loads the actual initial state and supplies the shared execution contracts.
M3 now supplies the shared unit/facility/technology catalog, complete national
build-chart coverage and verified availability queries. The shared interfaces
support later rule modules and their tests developed in parallel. Integration follows the dependencies above. RL adapters and tiny
oracle tests may be prepared early, but a partial land-only milestone must not be
presented as completed full-rule training.

Use these layers of verification throughout:

- **Data:** duplicate IDs/keys, valid references, field-preserving projection,
  faction identity, setup totals and national availability.
- **Rules:** a positive case, prohibited case and timing/exception case for each
  applicable clause; explicitly scripted dice for branch coverage.
- **Probability:** exact enumeration for tiny chance events and statistical checks
  for samplers. The test oracle must not simply call the implementation it tests.
- **State:** clone/replay/hash integrity, no accidental hidden information, and
  identical decisions through C++ and Python interfaces.
- **Campaign:** reviewed full-turn traces, random-legal-action stress tests,
  adversarial direct invalid actions, accounting and conservation invariants.
- **Learning:** known-answer puzzles, held-out opponents/seeds, reward-hacking
  checks, training resumption and throughput measurements.

Existing graph, MCTS and combat regressions remain valuable, but their coverage
must be labeled correctly. Replace obsolete deterministic-combat expectations
as the shared engine is upgraded; keep the tiny scenario, not a legacy resolver.
Port the underlying artillery/TD timing lessons into new dice-based fixtures.

## 8. Current deliverables, sources and next work

The map bridge and M0 specification deliverables comprise:

- The updated authoritative global JSON/generator for the selected Japanese
  islands and nearby seas; existing global outside neighbors are not cropped.
- [Japan/nearby-seas audit](/Users/home/Desktop/gwRL/docs/map_audits/japan_and_nearby_seas.md),
  documenting inspected changes and qualifications rather than claiming every
  historic global boundary has been certified.
- [Scenario manifest](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/manifest.json)
  selecting 37 nodes: 31 land tiles and the six requested sea zones, without
  Tannu Tuva or Hong Kong.
- [Extractor](/Users/home/Desktop/gwRL/tools/build_theatre_scenario.py),
  [extracted map](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/map.json)
  and [usage/scope notes](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/README.md).
  The extractor preserves retained node/edge data, removes excluded neighbors,
  reports cuts and records deterministic hashes. It validates inputs before
  writing and never overwrites the source or manifest.
- [Extractor tests](/Users/home/Desktop/gwRL/tests/test_theatre_extractor.py)
  and main-map regressions. These test projection/topology/data, not combat,
  runtime combat or reward evaluation. M0 specification tests separately check
  the approved setup, source reconciliation and campaign decisions.

Rebuild the map projection only:

```bash
./.venv/bin/python tools/build_theatre_scenario.py
```

The tool also supports `--map`, `--manifest` and `--output`; with no `--output`,
it writes `map.json` beside the manifest. This command does not launch training
or construct a playable full-rules initial game state.

### Sources

Repository review focused on `src/setup_loader.cpp`, `src/game_state.cpp`,
`src/japan_training_env.cpp`, both encoders, `include/game/mdp.hpp`,
`include/game/battle_resolver.hpp`, unit/action/state definitions, Python MCTS and
training code, the world-map generators and existing tests.

Rule sources in `game_content/rules/`:

- [Global War 1936 v4.3 Rulebook](</Users/home/Desktop/gwRL/game_content/rules/Global War 1936 v4.3 Rulebook.pdf>): pp. 5-7 definitions/home country; pp. 10-17
  geography, movement and supply; pp. 18-19 setup and July 1936 start; pp. 26-31
  relations/warlords; pp. 35-44 war, truce and sequence; pp. 45-82 production,
  combat, movement and placement; pp. 83-99 units/facilities; p. 101 Chinese Civil
  War/evolution; national special abilities in chapter 15.
- [Japan national sheet](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - Japan v4.3.pdf>): overview, income, objectives, national abilities,
  build charts and setup.
- [KMT national sheet](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - KMT v4.3.pdf>): evolution, Burma/Ledo roads, low morale, production,
  minor/major build charts and setup.
- [CCP national sheet](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - CCP v4.3.pdf>): evolution, recruitment, influence, Soviet connection,
  minor/major build charts and setup.
- [Neutrals setup chart](</Users/home/Desktop/gwRL/game_content/rules/Global War 1936 v4.3 Neutrals setup chart.pdf>): neutral/Mongolian setup details
  where applicable; cross-check against the Chinese national setup sheets.
- FEC/USSR national sheets where relevant to included territory identity/minor
  control or the applicability ledger, not to create outside interfaces or agents.
- [Original AlphaZero paper](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphazero-shedding-new-light-on-chess-shogi-and-go/alphazero_preprint.pdf),
  page 3, for the continuous latest-network self-play versus AlphaGo Zero
  promotion-gate distinction. The three-policy batch scheme here is our proposed
  adaptation, not a claim about the original implementation.
- [Multiplayer AlphaZero](https://arxiv.org/abs/1910.13012), for limited empirical
  evidence of three-player adaptation; [OpenSpiel MCTS](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/algorithms/mcts.h),
  for concrete multiplayer/chance search conventions; and [PSRO](https://papers.nips.cc/paper_files/paper/2017/hash/3323fe11e9595c09af38fe67567a9394-Abstract.html),
  for opponent-mixture training and overfitting motivation, not a claim that we
  have implemented a league or a game-theoretic solver.

This planning review is not a completed line-by-line rules certification; M0
exists to make completeness testable before implementation.

**Current learning work:** the first Stage A pilot has completed eight one-round
self-play games with terminal-only labels and a paired initial-versus-trained
comparison. Broader strategic strength is unestablished.

**Scaling follow-up:** 13 bounded cases now cover deeper search, later positions,
larger models and longer horizons within the user's 12-core/30 GB allowance.
One small-budget eleven-round game completes in 187.56 seconds; the stronger
16-simulation two-round batch reaches its 240-second guard without a completed
game. See [the scaling report](/Users/home/Desktop/gwRL/docs/stage_a/scaling_2026_10_23.md).

**Next work:** reduce repeated legal-menu/observation generation and graph
construction, then verify stronger-search collection before larger training.
Expand one-round learning/evaluation across several training and dice seeds,
followed by starting positions, horizon and opponent pairs.
M12 closes the final planned implementation gate with reproducible training,
exact interrupt/resume, evaluation and profiling. Its six learned-policy smoke
games are explicitly truncated; two scripted controls reach a real one-round
terminal. These checks do not establish playing strength. M9–M11 records retain
the full campaign traces and exact-oracle search checks.
M0 is verified and frozen; source
reconciliation records numeric queue payments and research thresholds. Ship values, queue
scope and scoring, Mongolia timing, starting-cash adjustment, controlled-minor
attribution, city/rail scoring and RCL-002–003/009 are recorded decisions;
RCL-001 now follows the developer’s corrected airborne sequence;
RCL-004–008 and RCL-011 are closed after source/developer checks. RCL-010
remains a campaign interpretation pending developer clarification. RCL-012 is closed: combat roles follow the reported developer ruling, and the
user clarified that attacking KMT has the same elimination consequence after
automatic termination.
RCL-013 is adopted and implemented. RCL-014 now follows the developer clarification
supplied on 23 October 2026: evacuating ships defend and the fleet already at sea
attacks. RCL-015 remains provisionally adopted pending developer clarification.
Tannu Tuva is excluded and is not a blocker.
The M2-M4 deliveries do not implement a reward evaluator, full gameplay handlers,
training agent or large training run.
