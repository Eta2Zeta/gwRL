# Air operations

This module flies the aircraft: their missions in Combat Movement, their part
in battles, strategic bombing, patrols over the sea, air transport and, above
all, landing. It is one of the engine's six rules modules
([overview](README.md#7-the-rules-by-subject)).

Code: `include/game/air.hpp`, `src/air.cpp`. Rules data:
`game_content/rules/gw36_air_v43.json`.

## 1. One flight per turn, and it must end on the ground

An aircraft flies once in its nation's turn (RB 11.1):

- **in Combat Movement**, on a mission. It then fights in the Combat Phase and
  lands when its battle is over; or
- **in Noncombat Movement**, from one base to another.

An aircraft that flew a mission does not fly again in Noncombat Movement. It
only lands, if it is still in the air then.

A flight is a path of zones, over land and sea, within the aircraft's range
(`validateFlight`). An aircraft on a carrier takes off from the carrier's sea
zone.

**Where an aircraft may land** (`airLandingSpots`): in land its side has held
since the turn began, or on a carrier with a free place. A carrier has a fixed
number of places, and a place promised to one aircraft cannot be promised to
another.

**No flight may leave an aircraft without a landing.** A flight is offered only
if, after it, every aircraft the nation has in the air can still land
(`airLandingPlanReachable`). The plan is worked out for all of them together:
carriers that can still sail may go where they are needed, and aircraft that
can land ashore free their places. Moves of ships are held to the same rule
([naval](naval.md)).

**When an aircraft still cannot land.** Dice, or another nation's turn, can
leave an aircraft with nowhere to go. Its owner then gives it up
(`air_failed_landing`), choosing which aircraft where there is a choice.
Combat Movement cannot end while an aircraft in the air has no landing; if
nothing else is legal, the phase ends and those aircraft are lost.

## 2. Missions

All are declared in Combat Movement, as a flight to the target.

| Move | Who flies it | What it is |
| --- | --- | --- |
| `air_support` | fighters and bombers | Joins a land battle its nation has already registered in that zone |
| `air_ground_attack` | fighters and bombers | Attacks an enemy zone where its nation has no battle yet. Aircraft alone cannot capture land. |
| `air_bomb` | bombers | Strategic bombing of one target: a facility, a project under construction, a city or a railroad |
| `air_escort` | fighters | Joins a bombing mission to fight interceptors |
| `air_start_patrol` | any aircraft | A Maritime Air Patrol over a sea zone ([section 5](#5-maritime-air-patrol)) |
| `air_assault` | transports and strategic bombers | Drops Airborne Infantry into a battle |
| `air_screen_continue` | fighters and bombers | Fights the enemy fighters in a zone on the way to a battle there; an aircraft that wins may fly on to further attacks with the range it has left, and one that loses must turn back |
| `air_rocket_attack` | Strategic Rockets | A rocket strike, once per rocket |
| `air_artillery_city_bomb` | Advanced Artillery | Bombards a neighbouring city without moving (RCL-013) |

Strategic bombers join land battles only with the technology Heavy Strategic
Bombers. Seaplanes and transports do not attack.

## 3. Aircraft in a land battle

The attacker's aircraft arrive with the mission they declared. The defender
answers before the first round:

- **Aircraft in the zone** either take part or stay on the ground, one decision
  for each (`air_defend`, `air_ground`).
- **Fighters at an airbase nearby** may scramble into the battle
  (`air_scramble`, or `air_decline_scramble`). A scramble uses the defender's
  holdings as of its own last turn, not the attacker's.

In the battle, fighters and anti-aircraft artillery fire first in the opening
round ([land combat](land_combat.md)). Carpet bombers fly home after the first
round. When the battle is over, every surviving aircraft lands: its owner
chooses where (`air_land`).

**Airborne assault.** The transports fly in with their Airborne Infantry. Both
sides' fighters and anti-aircraft artillery fire first, and a transport that is
shot down takes its cargo with it. The surviving transports then land their
infantry, which fights the land battle and cannot retreat (RCL-001).

## 4. Strategic bombing

1. **Declared** in Combat Movement (`air_bomb`), with escorts if any
   (`air_escort`).
2. **Begun** in the Combat Phase by the attacker (`air_begin_bombing`).
3. **Interception.** The defender's fighters may intercept (`air_intercept`,
   `air_decline_intercept`). Interceptors and escorts fight, and each side
   chooses its casualties (`air_choose_casualty`).
4. **Damage.** Each bomber that got through rolls a six-sided die.
5. **Anti-aircraft fire.** The target's own guns then fire at the bombers, on
   twelve-sided dice.

| Target | Effect of the damage |
| --- | --- |
| A facility | Damage on the facility, up to its limit; a damaged factory produces less or nothing |
| A project under construction | Every three points undo one paid stage ([economy](economy.md#5-repairs)) |
| A city | City damage; every 20 points remove one IPP of the zone's value for good |
| A railroad | Damage on one side of one border; the attacker picks the border (`air_choose_rail_border`) |

A raid can also cost the defender a technology in progress; the attacker
picks which (`air_choose_technology_loss`). If bombing damages a port, the
ships in it must leave at once, and the raid resumes afterwards
(`air_resume_bombing`, [naval](naval.md)).

## 5. Maritime Air Patrol

A patrol is an aircraft's whole combat move: it flies to a sea zone within
patrol range of the land zone or carrier it takes off from (RB 9.3.1) and stays
over it until Noncombat Movement, when it must land (`air_end_patrol`).

A patrol plane fights enemy ships that enter its sea zone, for one round, and
may be attacked by ships already there. Those choices are made in the naval
module's moves and are described with it ([naval](naval.md#5-patrol-planes-and-ships)).

## 6. Air transport

- **What fits** (`airCargoTypeFits`): an Air Transport carries one
  infantry-class unit; a Heavy Air Transport may carry one artillery or
  anti-aircraft artillery unit instead; a strategic bomber carries only
  Airborne Infantry.
- **Loading** (`air_load`) is offered in both movement phases, **unloading**
  (`air_unload`) in Noncombat Movement. Cargo may stay aboard; nothing makes a
  transport unload.
- **An ally's units** load in their own nation's turn and unload in its next
  (`air_allied_load`, `air_allied_unload`).
- **Militia** carried by air must be set down in their Home Country in the same
  phase.

## 7. The moves

| Move | Phase | Chosen by |
| --- | --- | --- |
| The missions of [section 2](#2-missions) | Combat Movement | the alliance of the nation whose turn it is |
| `air_begin_bombing`, `air_resume_bombing` | Combat | the attacker |
| `air_defend`, `air_ground` | Combat | the defender, for each aircraft in the zone |
| `air_scramble`, `air_decline_scramble` | Combat | the defender |
| `air_intercept`, `air_decline_intercept` | Combat | the defender |
| `air_choose_casualty` | Combat | the side that was hit |
| `air_choose_rail_border`, `air_choose_technology_loss` | Combat | see [section 4](#4-strategic-bombing) |
| `air_land` | Combat | the owner of the aircraft |
| `air_blitz` | Combat | the attacker: a fighter or tactical bomber flies on with a [blitz](land_combat.md#5-special-cases) |
| `air_fly`, `air_land_noncombat`, `air_end_patrol` | Noncombat Movement | the alliance of the nation whose turn it is |
| `air_load`, `air_unload`, `air_allied_load`, `air_allied_unload` | Combat Movement, Noncombat Movement | the same alliance |
| `air_failed_landing` | Combat Movement, Noncombat Movement | the owner of the aircraft |

In 240 random games 22 of the 30 air moves came up. Airborne assaults, rockets,
artillery bombardment of cities, allied cargo, the blitz and the loss of a
technology did not ([record](../archive/records/move_census_2026_11_14.md)); the
tests cover them.

Tests: `tests/air_tests.cpp`, `tests/air_logistics_tests.cpp`,
`tests/air_integration_tests.cpp` and `tests/air_mission_tests.cpp`.
