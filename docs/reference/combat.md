# Land, air and naval operations

The shared campaign resolves combat through explicit player decisions and chance.
Its approved scope is the regional scenario, not every rule of the global game.
For official-source questions and adopted changes, use the
[clarification register](../../game_content/rules/clarifications.md).

## Interfaces and persistent battle state

| Service | Public interface | Implementation |
| --- | --- | --- |
| Land combat | [land_combat.hpp](../../include/game/land_combat.hpp) | [land_combat.cpp](../../src/land_combat.cpp) |
| Air operations | [air.hpp](../../include/game/air.hpp) | [air.cpp](../../src/air.cpp) |
| Naval movement/combat/ports | [naval.hpp](../../include/game/naval.hpp) | [movement](../../src/naval_movement.cpp), [combat](../../src/naval_combat.cpp), [operations](../../src/naval_operations.cpp) |

`registerLandBattle` and `registerNavalBattle` consume already validated
participants/routes. Registration does not itself roll dice or capture territory.
`registerAttritionBattle` records the separate stationary artillery attack.
Battle selection, rolls, first strike, return fire, casualty choices, pairings,
retreats, landings and suspended operations are serialized continuations.
`BattleState.data` is authoritative; module objects hold no hidden mutable battle.
Checkpoint, clone, planning identity, observation and replay retain pending work.

Casualties are entitled choices. Target Selection belongs to the firing player;
ordinary casualties belong to the casualty side. Joint defenders can consent to
a proposal or invoke the printed highest-die dispute and tie rerolls. The engine
does not choose casualties using a built-in ranking policy. Ordinary casualties
retain return fire; first-strike losses are removed before ordinary fire.

## Land combat and retreats

Each contingent keeps its own final approach. The module combines destination
and approach terrain, applicable modifier limits, national effects, artillery
pairing, fortification directions and round durations using catalog statistics.
Empty attacks remain battles so minor KMT Low Morale resolves before capture.

Ordinary retreats use actual eligible land-entry origins. Current-turn movement
routes can establish an approach; stale off-turn or aircraft-only routes cannot.
The entry snapshot survives loss of the entrant. There is no arbitrary adjacent-
friendly escape. Without an eligible origin, ordinary ground forces keep
fighting; printed city/tundra limits still force retreat and eliminate units
unable to retreat. Airborne/amphibious commitments retain their restrictions.

Ordinary attacking KMT Low Morale sends eligible units to their own origins and
removes them from casualty eligibility. Shared-zone truce-ending combat uses the
specified elimination consequence instead. Defending KMT, Major-Power KMT and
other exempt types do not receive the attacking minor-unit penalty.

In voluntary truce termination, the active Chinese faction attacks. A third-party
evolution trigger uses the developer ruling that the possessor defends. Mandatory
battles resolve immediately in the existing phase, with actual Chinese decision
owners and a fixed calendar clock. Stable queue order for multiple automatic
battles is an engine convention, not a discretionary choice of the third party.
Applicable attacking minor KMT units have the same shared-zone elimination rule.

Winning within the permitted rounds can allow armor blitz. Explicit companion
pairings and [movement proofs](movement.md) preserve capacity and destination
constraints. Strategic Rockets neither roll ordinary attacks nor absorb
casualties; unsupported Rockets are destroyed by surviving enemy land units,
while aircraft-only raids/remote attrition preserve them.

## Air missions and landing

Aircraft flight/access, Airbase bonuses, carrier independence and return planning
are separate from ordinary land movement. Joint landing plans reserve real seats
for surviving scrambled/defending carrier aircraft; one seat cannot be promised
to several aircraft. Screening keeps a serialized continuing force: success can
permit further attacks with remaining flight, failure requires return, and
continuing aircraft cannot conduct an airborne assault.

Airborne transport/cargo casualties remain linked through the developer-corrected
Fighter/AAA step, followed by surviving transport landing. Bombing resolves
interception, damage/AAA, construction setbacks, permanent city IPP loss,
technology loss and selected-border rail damage through shared services.
Rocket range/overflight and single-use restrictions remain explicit. Adopted
artillery city bombardment uses its stationary/starting-adjacency conditions and
separate city-damage roll, without a bomber interception/AAA sequence. Surprise
Attack exceptions retain their specific mission scope.

## Naval, amphibious and port operations

Naval movement selects fleets and real sea paths, enforcing supply/damage,
transport pickup/unloading, strategic capacity and political entry windows.
Submarine/MAP reactions, screening and raider discovery can suspend movement;
waiting ships remain in their original port until its exit is cleared. The AI
order interface makes forward progress while the ordinary game API retains its
human editing/replay behavior.

Combat retains first strike, air superiority, return fire, casualty ownership,
multi-hit damage, cargo losses, submarine protection/submerging, MAP/Destroyer
pairing and retreat. Lost defending carriers trigger the printed immediate
one-movement landing attempt; surviving aircraft do not receive a fresh normal
flight allowance afterward.

Amphibious assaults require sea clearance, eligible shore bombardment and Coastal
Artillery resolution before the shared land battle. Normal-transport reserves
wait for a surviving first-wave foothold; named transport/Marine/technology
exceptions remain distinct. Same-target land attacks wait for that preparation.

Ports support berthing, blockade/assault restrictions, damaged-port evacuation,
temporary/skeleton crews and capture/scuttling with damage retained. Evacuation
can suspend bombing. Evacuating ships defend and the fleet already at sea attacks,
including on another nation's turn; the suspended operation resumes afterward.
An attack on ships in port does not let them scramble into that port attack.

Coastal Artillery passage fire requires crossing an actual printed narrow line,
not merely entering its sea zone. The retained Hainan–Kwangtung and Honshu–Hokkaido
geography has bypasses, so its mandatory-passage overlay is empty. The shared
three-shots-per-Player-Turn counter still applies to eligible fire, including
other operations. See the [naval geography reference](naval-geography.md).
Convoy raiding, interdiction and Kido Butai remain disabled in this scenario.

## Source and regression references

Source profiles: [land](../../game_content/rules/gw36_land_combat_v43.json),
[air](../../game_content/rules/gw36_air_v43.json), and
[naval](../../game_content/rules/gw36_naval_v43.json).
Focused fixtures cover [land combat](../../tests/land_combat_tests.cpp),
[truce](../../tests/land_truce_tests.cpp), [air logistics](../../tests/air_logistics_tests.cpp),
[air integration](../../tests/air_integration_tests.cpp),
[air missions](../../tests/air_mission_tests.cpp),
[naval movement](../../tests/naval_movement_tests.cpp),
[naval combat](../../tests/naval_combat_tests.cpp) and
[naval operations](../../tests/naval_operations_tests.cpp).
Historical delivery reports and replay evidence are indexed in the
[milestone archive](../archive/milestones/README.md).
