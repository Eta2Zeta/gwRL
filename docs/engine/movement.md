# Movement and supply

This module moves land units and answers the questions every other module asks
about the map: may this nation enter this zone, is this railroad usable, is
this zone in supply, is this port blockaded. Ships and aircraft have their own
moves ([naval](naval.md), [air](air.md)), but use these answers. It is one of
the engine's six rules modules ([overview](README.md#7-the-rules-by-subject)).

Code: `include/game/movement.hpp`, `src/movement.cpp`. Rules data:
`game_content/rules/gw36_movement_v43.json`.

## 1. A land move

A land move names a unit, the path it takes zone by zone, and the way it moves
(`movement_route`). The engine lists every legal path for every unit that can
still move, so a unit with several places to go appears in several moves.

| Detail | Meaning |
| --- | --- |
| `unit` | The unit that moves |
| `path` | The zones it passes, from where it stands to where it ends |
| `mode` | `ordinary`, `blitz`, `strategic_rail` or `narrow_crossing` |
| `combat` | Whether the move is an attack |
| `towed` | A second unit a Motorized Infantry pulls along, if any |

Each unit type has a movement allowance from the [catalog](scenario.md#5-the-catalog),
and a unit spends it as it goes (`validateRoute`):

- **Terrain can end a move.** Entering some terrain, or crossing some borders,
  uses up whatever movement the unit had left. Terrain belongs to a zone, and
  also to a border in one direction: crossing from A to B can differ from
  crossing from B to A.
- **Enemy land ends a move.** A unit that enters land held by a nation it is at
  war with stops there, and a battle is registered for the Combat Phase.

## 2. The ways to move

| Way | Phase | What it is |
| --- | --- | --- |
| Ordinary | Combat Movement, Noncombat Movement | The unit walks, spending its movement allowance |
| Narrow crossing | Combat Movement, Noncombat Movement | Across a strait between two land zones. It carries a limited number of units and can be closed by enemy ships in the sea it crosses. Only infantry-class units cross outside combat, and only Marines attack across one. |
| Blitz | Combat | Armour that won its battle within two rounds moves on, with the companions paired to it ([land combat](land_combat.md)) |
| Strategic rail | Noncombat Movement | The unit rides the railroads as far as they are connected and usable, and then cannot move again |

The engine also knows a fifth way, strategic movement by river, but never
offers it: no river on this map is confirmed as navigable.

## 3. Combat Movement and Noncombat Movement

**Combat Movement lists only attacks.** A land move is offered there only if it
ends in land held by an enemy, or by a nation the mover may attack. Moves into
one's own or friendly land wait for Noncombat Movement. Attacking land of a
nation one is not yet at war with declares that war ([politics](politics.md)).

**An attack registers a battle.** Units that enter the same enemy zone join one
battle. The engine remembers, for each unit, the zone it came from. That zone
decides which border terrain and river crossing count against that unit, and
where it may retreat to ([land combat](land_combat.md)). An attack on an empty
zone also registers a battle.

**Noncombat Movement lists everything else.** A unit may enter land its nation
has held since the turn began, friendly land, and land a warlord handed over
this turn by joining. It may not enter land captured this turn.

**A rail move is offered only where walking does not reach.** Where an ordinary
move ends in the same zone, the rail move would only use up rail capacity, so it
is left off the list.

**The KMT and the CCP stay in China** until they become major powers: they may
enter only the Chinese Home Country and the seas next to it
(`chineseMovementAllowed`).

## 4. Railroads

A border between two land zones holds at most one railroad (RCL-019), and the
state keeps the damage on each of its two sides separately. Bombing damages one
side, and the nation holding that side repairs it ([economy](economy.md)).

A strategic rail move needs, along its whole path:

- **Usable track.** The railroad is undamaged and has been since the turn
  began. A railroad built or repaired this turn does not count.
- **Land held since the turn began**, one's own or a friend's. Through a
  friend's land played by another alliance, the friend must first give leave
  (`movement_grant_rail`, an [out-of-turn move](README.md#6-moves-made-out-of-turn)).
- **Capacity.** Each region of the world carries a fixed number of units by
  rail per turn. All 31 land zones of this map are in the region Asia, whose
  capacity is 1; the technology Improved Logistics adds 1.

All 17 railroads at the start have the same gauge, so the rule that a change of
gauge needs Improved Logistics does not come up unless new track is built.

**Factories by rail.** A nation with Improved Logistics may move a factory
along its railroads inside its Home Country (`movement_factory_rail`). The
factory keeps its damage and produces nothing that turn.

## 5. Supply

A zone is *in supply* for a nation when a path joins it to that nation's Home
Country (`supplyRoute`, `inSupply`). Placing new units, some purchases and the
range of ships depend on it.

- **Where it starts.** In Home Country land the nation holds.
- **Over land.** Along railroads that are undamaged and have been held since
  the turn began.
- **Over sea.** From a port or other naval facility, 2 sea zones for a minor
  power and 4 for a major power, more with Improved Logistics. A facility
  reached on the way renews the range once.
- **Blockade.** Three enemy surface warships in a sea zone, with no surface
  warship of the facility's side there, blockade it (RCL-005). A facility is
  closed only when every sea zone it opens onto is blockaded.

Asking whether a zone is in supply moves nothing and uses up no capacity.

## 6. Leaving land that was given away

When Japan gives a captured Chinese zone to a Chinese nation it is not friendly
with ([politics](politics.md#5-capturing-land)), its units must leave that zone
in the same turn's Noncombat Movement. The gift is offered only if every unit
can leave, on foot or aboard a transport. Until they have left, the list holds
only their moves and aircraft landings, and the phase cannot end.

## 7. The moves

| Move | Phase | Chosen by | What it does |
| --- | --- | --- | --- |
| `movement_route` | Combat Movement, Combat, Noncombat Movement | the alliance of the nation whose turn it is | Moves one land unit along a path |
| `movement_factory_rail` | Noncombat Movement | the same alliance | Moves a factory by rail |
| `movement_grant_rail` | Noncombat Movement, out of turn | a friendly nation's alliance | Lets the nation whose turn it is ride through its land |

In 240 random games `movement_route` was on the list at 102,194 of 312,365
decisions, more than any other move except `end_phase`
([record](../archive/records/move_census_2026_11_14.md)). The other two never
came up in those games.

Tests: `tests/movement_tests.cpp`. The printed pages behind these rules are
listed in [Movement: source coverage](../rules/movement_sources.md).
