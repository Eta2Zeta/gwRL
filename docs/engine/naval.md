# Naval operations

This module moves the ships and fights at sea: fleets and their routes,
meetings with the enemy on the way, sea battles, transports and landings, and
ports. It is the largest of the engine's six rules modules, with 62 of its 141
kinds of move ([overview](README.md#7-the-rules-by-subject)). At the start only
Japan has ships.

Code: `include/game/naval.hpp`; `src/naval.cpp`, `src/naval_movement.cpp`
(orders, routes and what happens on the way), `src/naval_combat.cpp` (sea
battles), `src/naval_operations.cpp` (landings, ports, attacks from the air).
Rules data: `game_content/rules/gw36_naval_v43.json`.

## 1. Where a ship is

A ship is in a sea zone, either at sea or in port at a naval facility: a port,
a shipyard or a dockyard. A facility opens onto one or two sea zones. Ships at
sea meet the enemy; ships in port do not fight at sea, but can be attacked
there from the air and are at risk if the land is taken
([section 7](#7-ports)).

## 2. Moving a fleet: an order in steps

Ships move as a *force*: one or more ships of one nation, from one sea zone,
along one route. In training an order is built in steps, each a decision with a
bounded list ([overview, section 3](README.md#3-positions-and-moves)):

1. **Start** with one ship that can still move (`naval_start_move`).
2. **Add** ships from the same sea zone, one at a time (`naval_force_add`).
3. **Choose the route** (`naval_route`): the path of sea zones, and the port to
   leave or to enter if any. The engine lists every route the force as chosen
   can sail. In Combat Movement, a force in a sea zone with enemy units may
   instead attack them where it is (`naval_engage_force`).

An order can only go forward: a ship added stays added. The interface for
people can also take a ship out again or cancel the order
(`naval_force_remove`, `naval_cancel_move`); training does not offer those.

How far a ship sails depends on its type, its damage and whether it is in
[supply](movement.md#5-supply) (`validateNavalRoute`). As with flights, no
route is offered that would leave an aircraft in the air without a landing
([air](air.md#1-one-flight-per-turn-and-it-must-end-on-the-ground)): a carrier
may not sail away from the aircraft that count on it.

**Ships of the KMT and the CCP** stay in the sea zones next to the Chinese Home
Country until their nation is a major power. **Militia** carried by sea must be
put ashore in their Home Country in the same phase, so a ship may not take them
where that is no longer possible.

## 3. Meeting the enemy on the way

A force that enters a sea zone holding another nation's units may be stopped
there. Each case is a decision for the side it concerns.

| What the force meets | Who decides | Moves |
| --- | --- | --- |
| Ships of a nation it is not at war with, where war could be declared | The mover: declare war, or enter in peace | `naval_entry_declare`, `naval_entry_peaceful` |
| | Then the other nation: declare war, or let it pass | `naval_entry_defender_declare`, `naval_entry_neutral` |
| Enemy submarines or a patrol plane | Their owner: fight, or let the force pass | `naval_reaction_engage`, `naval_reaction_decline` |
| Enemy ships, or a patrol Fighter, it wants to sail past | The mover: leave some ships behind as a screening force to hold them | `naval_screen_add`, `naval_screen_confirm` |
| | Then, once the screening fight is won: the rest sails on, or stops | `naval_screen_continue_route`, `naval_screen_stop_route` |

A fight that starts on the way is fought at once, in Combat Movement, and the
order then carries on from where it stood.

**Raiders.** In Combat Movement a Battlecruiser may be named a raider
(`naval_designate_raider`, undone by `naval_remove_raider`). A raider attacks
alone (RB 9.4.4): it cannot join a force or a battle with other ships.

## 4. Sea battles

A sea battle is a record in the state, like a land battle
([land combat](land_combat.md#1-what-a-battle-is)). It is registered when a
force ends its combat move in a sea zone with enemy units, or attacks them
where it is, and it is fought in the Combat Phase when the attacker begins it
(`naval_begin_battle`).

Before the first round the defender's side answers:

- **Aircraft at a base next to the sea zone** may scramble into the battle
  (`naval_scramble`, `naval_decline_scramble`).
- **Each submarine** takes part or stays out (`naval_sub_protected`,
  `naval_sub_unprotected`, `naval_sub_decline`).
- **A patrol plane** takes part or stays out ([section 5](#5-patrol-planes-and-ships)).
- **Destroyers** may be paired with a patrol plane of their side
  (`naval_pair_destroyer`, `naval_decline_pair`).

Then the battle is fought in rounds, as on land: both sides roll twelve-sided
dice, a shot hits when the die shows at most the unit's value, each side chooses
its casualties (`naval_take_casualty`), and after each round the attacker goes
on or retreats (`naval_continue_fighting`, `naval_retreat_begin`,
`naval_retreat_unit`). Three things differ from land:

- **Big ships take more than one hit.** A capital ship is damaged before it is
  sunk, and a damaged ship fights and sails worse.
- **Cargo goes down with its transport.**
- **Aircraft need a deck.** When a carrier is sunk, its aircraft get one short
  move to land elsewhere (`naval_carrier_land`), and are lost if they cannot.

Two nations defending together agree on their casualties or roll for it
(`naval_casualty_accept`, `naval_casualty_dispute`), as on land.

## 5. Patrol planes and ships

An aircraft on Maritime Air Patrol watches one sea zone
([air](air.md#5-maritime-air-patrol)). Four rules decide what happens between
it and enemy ships.

- **Ships that enter its zone.** The plane fights them for one round (RB 9.3.1),
  or lets them pass. It may let them pass only if they have no aircraft with an
  attack value with them.
- **Sailing on.** After that round the surviving ships may continue their
  move. Past a Fighter they may not: they must leave a screening force to hold
  it, or end their move there (RB 9.4.2).
- **A plane that let ships pass** takes no part in their battles in its zone
  for the rest of the turn, and does not count against their landings. If they
  attack it anew, it chooses again (RCL-017).
- **A plane attacked in its own zone** by ships already there
  (`naval_patrol_attack`) chooses whether to fight before anyone scrambles
  (`naval_patrol_engage`, `naval_patrol_decline`), and staying out costs it
  nothing (RCL-020). An aircraft aboard a carrier is not on patrol: it flies
  into the battle or stays on deck, and on deck it is lost if its side loses.

## 6. Transports and landings

**Cargo.** A Naval Transport carries two land units, at most one of them not
infantry-class. A Japanese destroyer carries one Marine. Units go aboard from
a land zone next to the ship's sea zone (`naval_load`) and ashore the same way
(`naval_unload`, in Noncombat Movement). Cargo may stay aboard from turn to
turn.

**An amphibious assault** is a landing against enemy land.

1. **Declared** in Combat Movement (`naval_declare_assault`): the transport,
   its cargo and the land zone.
2. **The sea must be clear.** Any sea battle in the transport's zone is fought
   first.
3. **Begun** in the Combat Phase (`naval_begin_assault`). The attacker picks
   the warships that bombard the shore (`naval_select_bombardment`,
   `naval_finish_shore_selection`).
4. **Shore fire.** The bombarding ships and the defender's Coastal Artillery
   fire first. Casualties are chosen by the side that was hit
   (`naval_shore_casualty`).
5. **The land battle** follows ([land combat](land_combat.md)), together with
   any units attacking the same zone overland. Units that landed cannot
   retreat.

An assault is called off when Combat comes and enemy surface ships or aircraft
still hold its sea zone, or no cargo is left aboard: the units stay on their
transport (RCL-018). Neither the end of the phase nor a land battle in the same
zone waits for it.

## 7. Ports

- **Entering port.** At the end of its Noncombat Movement a ship may berth at a
  friendly facility on its sea zone (`naval_enter_port`). The move says whether
  its cargo goes ashore.
- **Blockade.** A blockaded facility cannot be used
  ([movement](movement.md#5-supply)).
- **Attack from the air.** Aircraft may attack ships in a port
  (`naval_port_attack`), and ships or aircraft at sea (`naval_air_attack`). In
  Japan's Surprise Attack, the zone is named first
  (`naval_select_surprise_zone`).
- **A damaged port must be left.** When a facility is damaged, the ships in it
  put to sea at once (`naval_evacuate_port`, `naval_decline_evacuation`,
  `naval_finish_evacuation`). If enemy ships are waiting outside, the ships
  coming out defend and the ones at sea attack (RCL-014).
- **A captured port.** Ships still in a port when its land is taken are rolled
  for in the captor's Place Units Phase, one twelve-sided die each
  (`naval_roll_capture`): the ship is captured or scuttled.
- **Coastal Artillery** fires at most three times in a turn.

**Strategic naval movement.** In Noncombat Movement, transports may carry units
a long way through friendly waters, picking more up on the way
(`naval_strategic_pickup`, `naval_strategic_continue`).

## 8. Left out of this campaign

Convoys, convoy raiding and escorts, interdiction and Japan's Kido Butai are
switched off ([the campaign](scenario.md#4-what-is-left-out)). The two narrow
crossings on the map, Hainan–Kwangtung and Honshu–Hokkaido, do not force ships
through a passage
([Narrow crossings and naval passage](../rules/naval_geography.md)).

## 9. The moves

| Moves | Phase | Chosen by |
| --- | --- | --- |
| `naval_start_move`, `naval_force_add`, `naval_route`, `naval_engage_force` | Combat Movement, Noncombat Movement | the alliance of the nation whose turn it is |
| `naval_force_remove`, `naval_cancel_move` | the same | the same, in the interface for people only |
| `naval_entry_declare`, `naval_entry_peaceful` | while moving | the mover |
| `naval_entry_defender_declare`, `naval_entry_neutral` | while moving | the nation met |
| `naval_reaction_engage`, `naval_reaction_decline` | while moving | the owner of the submarines or patrol plane |
| `naval_screen_add`, `naval_screen_remove`, `naval_screen_confirm`, `naval_screen_continue_route`, `naval_screen_stop_route` | while moving | the mover |
| `naval_designate_raider`, `naval_remove_raider` | Combat Movement | the alliance of the nation whose turn it is |
| `naval_load` | Combat Movement, Noncombat Movement | the same alliance |
| `naval_unload`, `naval_enter_port`, `naval_strategic_pickup`, `naval_strategic_continue` | Noncombat Movement | the same alliance |
| `naval_declare_assault`, `naval_air_attack`, `naval_port_attack`, `naval_select_surprise_zone` | Combat Movement | the same alliance |
| `naval_begin_battle`, `naval_begin_assault`, `naval_patrol_attack`, `naval_progress_battle`, `naval_finish_battle` | Combat | the attacker |
| `naval_scramble`, `naval_decline_scramble`, `naval_sub_protected`, `naval_sub_unprotected`, `naval_sub_decline`, `naval_patrol_engage`, `naval_patrol_decline` | Combat | the owner of the units |
| `naval_pair_destroyer`, `naval_decline_pair` | Combat | the owner of the destroyer |
| `naval_discover_raider`, `naval_ignore_raider`, `naval_raider_slip`, `naval_raider_stay` | Combat | the two sides of a battle with a raider |
| `naval_take_casualty`, `naval_casualty_accept`, `naval_casualty_dispute` | Combat | the side that was hit |
| `naval_continue_fighting`, `naval_retreat_begin`, `naval_retreat_unit` | Combat | the attacker |
| `naval_carrier_land` | Combat | the owner of the aircraft |
| `naval_select_bombardment`, `naval_finish_shore_selection` | Combat | the attacker |
| `naval_shore_casualty`, `naval_shore_accept`, `naval_shore_dispute` | Combat | the side that was hit |
| `naval_evacuate_port`, `naval_decline_evacuation`, `naval_finish_evacuation` | when a port is damaged | the owner of the ships |
| `naval_roll_capture` | Place Units | the captor |

In 240 random games 39 of the 62 naval moves came up
([record](../archive/records/move_census_2026_11_14.md)). Among those that did
not: peaceful entry, port evacuation, destroyer pairing, joint casualties and a
raider slipping away. The tests cover them.

Tests: `tests/naval_movement_tests.cpp`, `tests/naval_combat_tests.cpp`,
`tests/naval_operations_tests.cpp`, `tests/campaign_action_interface_tests.cpp`
and `tests/training_action_progress_tests.cpp`.
