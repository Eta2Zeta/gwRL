# Names held as numbers

The scenario names everything with strings: zones such as `land_china_hopeh`,
nations such as `japan`, unit types such as `cavalry`, facility types such as
`major_port`, technologies such as `radar`, marks such as `placed_this_turn`.
Inside the engine zones, nations, unit types, unit classes, facility types,
technologies and the bases of marks are held as numbers instead, a few bytes
that compare, copy and look up as fast as any integer. This page says which
names the engine holds as numbers, where each number comes from, where the
engine turns names into numbers and back, and how to look a number up.

The units, facilities and other things themselves are still held by name;
[what is still a name](#what-is-still-a-name) lists them.

## 1. Why numbers

Before zones were numbered, 59% of the engine's time went to comparing names,
allocating memory, looking up maps and copying memory, against 41% to the rules'
own logic ([record](../archive/records/self_play_limits_2026_11_16.md#inside-the-engine)).
The position kept its zones, units, facilities and nations in maps keyed by
name, and every rule check named them as strings. Holding names as numbers took
that work out kind by kind, with play unchanged at every step of the same 300
random games and 4 searched games each time
(`tools/compare_engine_builds.py`):

| Held as numbers | Instructions to list a position's moves, per call | Instructions in four searched games | Record |
| --- | ---: | ---: | --- |
| None (commit `9519ea7`) | 10.03 million | 6,782 billion | — |
| Zones | 8.73 million | 6,292 billion | [zones](../archive/records/zone_numbers_2026_11_16.md) |
| Nations as well | 8.15 million | 5,996 billion | [nations](../archive/records/nation_numbers_2026_11_16.md) |
| Unit types and classes as well | 7.77 million | 5,845 billion | [unit types](../archive/records/unit_type_numbers_2026_11_16.md) |
| The bases of marks as well | 7.07 million | 5,557 billion | [marks](../archive/records/mark_numbers_2026_11_16.md) |
| Facility types and technologies as well | 6.08 million | 5,334 billion | [facility types](../archive/records/facility_type_numbers_2026_11_16.md) |
| Units and facilities kept in slot maps | 5.74 million | 5,164 billion | [slot maps](../archive/records/slot_maps_2026_11_16.md) |

So listing a position's moves runs 42.8% fewer instructions than before any of
these changes, and a searched game 23.9% fewer. Part of the last step is a
check that numbers made cheap: a factory's production capacity, which the build
menu asks for each row of the build chart, reads the nation's completed
technologies as a set of bits (`completedTechnologies`) instead of a catalog
context that copied every mark of the nation by name.

## 2. Where the numbers come from

Each kind of name has a table: its names sorted bytewise, a name's number
being its place in that list, counted from 0 (`NameTable` in
`include/game/names.hpp`). `freezeDefinition` builds the tables of zones and
nations from the definition's own data (`Names` in `include/game/campaign.hpp`),
and `Catalog::fromJson` the tables of unit types, unit classes, facility types
and technologies from the catalog's (`include/game/catalog.hpp`), before it
reads the catalog's definitions, so that each definition can hold the names it
cites as numbers. No table is saved, since the names they are made from are
part of the definition and of the catalog.

| Kind | Type | Its names | In the campaign |
| --- | --- | --- | ---: |
| Zones | `ZoneId` | The keys of the map's `nodes` | 37 |
| Nations | `NationId` | The keys of the definition's `factions`, dormant ones included | 13 |
| Unit types | `UnitTypeId` | The catalog's units (`land_air.json` and `naval.json` in `game_content/catalog/gw36_v43`) | 53 |
| Unit classes | `UnitClassId` | Every class some unit of the catalog has | 17 |
| Facility types | `FacilityTypeId` | The catalog's facilities (`facilities.json`) | 15 |
| Technologies | `TechnologyId` | The catalog's technologies (`technologies.json`) | 16 |
| Marks | `MarkId` | The bases in the engine's mark table, `GWRL_MARKS` in `include/game/marks.hpp` | 218 |

The campaign's 13 nations are the 12 of its faction index
(`game_content/scenarios/japan_china_1936/faction_index.json`) and Dadao, which
`loadScenario` adds as a dormant faction (`src/campaign_setup.cpp`). So Dadao
has a number from the start, though it enters the position only when
`ensureDadao` creates it (`src/politics.cpp`).

Because a number is a place in a sorted list:

- **Numbers compare as their names do.** Zone 0, `land_china_beiping`, comes
  before zone 1, `land_china_hopeh`, and nation 2, `japan`, before nation 3,
  `kmt`, as the names do.
- **Play is unchanged.** A container keyed by numbers lists its entries in the
  order the same container keyed by names did, so every list of moves comes out
  in the same order as before. `tools/compare_engine_builds.py` found the same
  moves and positions at every step of 300 random games and 4 searched games
  after each kind was numbered
  ([zones](../archive/records/zone_numbers_2026_11_16.md),
  [nations](../archive/records/nation_numbers_2026_11_16.md),
  [unit types](../archive/records/unit_type_numbers_2026_11_16.md),
  [marks](../archive/records/mark_numbers_2026_11_16.md)).
- **A number belongs to its definition or catalog.** Adding a zone to the map,
  a nation to the factions or a unit type, facility type or technology to the
  catalog renumbers those after it. Saved games and moves hold names, so they
  are unaffected. The planning key digests a binary writing of the position
  that holds numbers ([keys](README.md#8-copies-saved-games-and-replays)), but
  it also digests the definition's fingerprint, so any change to the
  definition changes it anyway.

### The nations the rules name

The rules name six nations in their code: Japan, the KMT, the CCP, Dadao, the
USSR and Mongolia. `freezeDefinition` looks their numbers up once
(`KnownNations` in `include/game/campaign.hpp`), so a rule asks whether a unit
is Japanese with `owner == known.japan`, an integer compare. A scenario may lack
one of them, and the campaign has no USSR, so each is optional: empty for a
nation the definition lacks. A nation number never equals an empty one, just as
no nation's name ever equalled the name of a nation the scenario lacks.

Two optionals are another matter: a territory nobody holds has an empty
possessor, and it would equal the USSR's empty number. So no rule compares a
possessor with a known nation; `isNation(state, possessor, "kmt")` asks the
question instead, and is false for an empty possessor.

### The unit types and classes the rules name

The rules name 40 unit types and 16 unit classes in their code. Two lists in
`include/game/catalog.hpp`, `GWRL_KNOWN_UNIT_TYPES` and `GWRL_UNIT_CLASSES`,
hold their names, and each list makes a structure with one member per name,
spelled as the catalog's string: `KnownUnitTypes::militia` holds the number of
`militia`. So a rule asks whether a unit is militia with
`u.type == known.militia`, an integer compare, and a misspelled name does not
compile, where a misspelled string would have been a comparison that is never
true. Loading a catalog that lacks one of the names fails, so every member
holds a number.

A unit's type comes from the catalog, so a position holds units only if its
definition has a catalog; `State::validate` refuses a unit otherwise. The same
holds for facilities, construction projects and technology stages below.

### The facility types and technologies the rules name

The rules name every facility type of the catalog and 9 of its 16
technologies in their code. Two more lists in `include/game/catalog.hpp`,
`GWRL_KNOWN_FACILITY_TYPES` and `GWRL_KNOWN_TECHNOLOGIES`, hold their names,
as for unit types: a rule asks whether a facility is a fortification with
`f.type == known.fortification`, and whether a nation has completed Radar with
`hasTechnology(state, nation, knownTechnologies(state).radar)`.

Some rules treat several facility types alike. `KnownFacilityTypes` names
those groups, each by its members:

| Group | Facility types |
| --- | --- |
| `factory` | The minor, medium and major factory |
| `naval` | The minor and major port, dockyard and shipyard |
| `shipyard` | The minor and major shipyard |
| `major` | The major factory, port, dockyard and shipyard |
| `base` | The airbase, seaplane base and submarine base |

Before facility types were numbered, the rules found these groups by searching
a type's name, for `shipyard` say, or by its `major_` prefix. Each group holds
exactly the types those searches found, and `tests/names_tests.cpp` checks it
against the names.

The map calls three facilities by a label of its own, `airfield`. The scenario
contract says an airfield is the catalog's airbase (`facility_type_aliases` in
`game_content/scenarios/japan_china_1936/scenario_contract.json`), and
`loadScenario` reads those facilities as airbases (`src/campaign_setup.cpp`), so
no position holds a facility type the catalog lacks.

### What a build type is

A build-chart row and a construction project build either a unit or a
facility, so their type is a `BuildType` (`include/game/campaign.hpp`): a unit
type number or a facility type number, of which `isUnit()` and `isFacility()`
say which. The catalog gives no unit type and facility type the same name, so a
name says which of the two it is: `buildTypeNumber(state, name)` reads it and
`buildTypeName(state, type)` names it. The target of an upgrade, the type a row
upgrades from and the types a technology unlocks are build types too.

### Units and facilities: slots

Units and facilities enter and leave a game: a purchase places a unit, a
battle destroys one, a factory is built. A new unit's name, such as
`economy_unit_12`, may sort anywhere among the others, so these names cannot be
numbered once for the whole game, as zones are. The position keeps them in
`SlotMap`s instead (`include/game/slot_map.hpp`). Each unit and facility gets a
*slot* when it enters the position: a number of its own type (`UnitSlot`,
`FacilitySlot`), fixed while the thing exists and never given to another, which
`units.at(slot)` follows without comparing names. The map writes it into the
thing as well (`u.slot`).

A slot is not a place in name order. Slots follow the order things entered the
position, so two copies of a game that reached the same position by different
moves may give its units different slots, and a position read back from its
saved form gives them slots in name order. A slot therefore has no order: no
set or map can be keyed by slots, and anything listed in order is listed in
name order, as a `SlotMap` lists its things. Saved positions, planning keys and
moves name units and facilities as before, never by slot.

A `SlotMap` is also searched by name, through a hash table of its slots, so a
lookup compares one name or two where a search in name order compared seven or
eight. Everything that refers to a unit or facility still names it.

### What a mark is

A *mark* is a small fact a rule notes, with a whole number, on a unit, a
nation, a territory, a facility, a construction project, a battle or the
position itself: `placed_this_turn` = 1, `naval_movement_spent` = 2,
`economy_production_cap:facility_honshu_airfield` = 3. A unit's commitments,
such as `combat_move`, are marks without numbers. A mark's name has a *base*,
which says what it records, and for some bases an *argument*, which says what
it is about: a zone, a nation, a facility, a unit and so on.

The engine numbers the bases. `GWRL_MARKS` in `include/game/marks.hpp` lists
every base a position may hold, in name order, with what its argument names;
a base's number is its place in that list, and `mark::placed_this_turn` names
that number in code. The argument stays text: the name of the zone, nation,
facility or other thing the mark is about. A mark is written base, `:`,
argument, except `evolution_pending`, whose argument follows an underscore, as
in `evolution_pending_ccp`.

The list is the whole set: reading a saved position refuses a mark it lacks,
and setting a mark checks that its argument fits its base, so a misspelled
mark cannot slip in. `fixture:<name>` is the one base no rule of the game
notes: test rules and tools use it for their own bookkeeping. Static checks in
the header keep the list sorted and keep each argument from moving a mark away
from its number's place in name order, so a set of marks lists them in the
order of their names.

## 3. The campaign's tables

The campaign, `game_content/scenarios/japan_china_1936`, and its catalog,
`game_content/catalog/gw36_v43`, number their names as follows. `tools/print_name_tables.py` prints these tables from the engine, and
`tests/test_name_tables.py` checks that they match.

### Zones

| Number | Name |
| ---: | --- |
| 0 | `land_china_beiping` |
| 1 | `land_china_hopeh` |
| 2 | `land_china_hunan` |
| 3 | `land_china_kweichow` |
| 4 | `land_china_nanking` |
| 5 | `land_china_shantung` |
| 6 | `land_china_shensi` |
| 7 | `land_china_sikang` |
| 8 | `land_china_sinkiang` |
| 9 | `land_china_suiyuan` |
| 10 | `land_china_szechwan` |
| 11 | `land_china_tsinghai` |
| 12 | `land_china_yunnan` |
| 13 | `land_formosa` |
| 14 | `land_hainan` |
| 15 | `land_jap_hokkaido` |
| 16 | `land_jap_honshu` |
| 17 | `land_jap_kyushu` |
| 18 | `land_jap_okinawa` |
| 19 | `land_jap_tokyo` |
| 20 | `land_korea` |
| 21 | `land_kwangtung` |
| 22 | `land_manchuria_eastern` |
| 23 | `land_manchuria_northern` |
| 24 | `land_manchuria_rehe` |
| 25 | `land_manchuria_western` |
| 26 | `land_mongolia_central_mongolia` |
| 27 | `land_mongolia_kerulen` |
| 28 | `land_mongolia_kobdo` |
| 29 | `land_mongolia_ulyassutai` |
| 30 | `land_tibet` |
| 31 | `sea_p14` |
| 32 | `sea_p15` |
| 33 | `sea_p16` |
| 34 | `sea_p32` |
| 35 | `sea_p33` |
| 36 | `sea_p41` |

### Nations

| Number | Name |
| ---: | --- |
| 0 | `ccp` |
| 1 | `dadao` |
| 2 | `japan` |
| 3 | `kmt` |
| 4 | `mongolia` |
| 5 | `warlord_beiping_hopeh` |
| 6 | `warlord_kwangtung_hainan` |
| 7 | `warlord_sikang` |
| 8 | `warlord_sinkiang` |
| 9 | `warlord_suiyuan` |
| 10 | `warlord_tibet` |
| 11 | `warlord_tsinghai` |
| 12 | `warlord_yunnan` |

### Unit types

| Number | Name |
| ---: | --- |
| 0 | `advanced_artillery` |
| 1 | `advanced_mechanized_infantry` |
| 2 | `advanced_self_propelled_artillery` |
| 3 | `advanced_submarine` |
| 4 | `air_transport` |
| 5 | `airborne_infantry` |
| 6 | `anti_aircraft_artillery` |
| 7 | `artillery` |
| 8 | `attack_naval_transport` |
| 9 | `b_29` |
| 10 | `battlecruiser` |
| 11 | `battleship` |
| 12 | `cavalry` |
| 13 | `coastal_defense_ship` |
| 14 | `coastal_submarine` |
| 15 | `colonial_infantry` |
| 16 | `destroyer` |
| 17 | `elite_airborne_infantry` |
| 18 | `fighter` |
| 19 | `fleet_carrier` |
| 20 | `foreign_legion` |
| 21 | `gurkha` |
| 22 | `heavy_air_transport` |
| 23 | `heavy_armor` |
| 24 | `heavy_battleship` |
| 25 | `heavy_cruiser` |
| 26 | `heavy_fleet_carrier` |
| 27 | `heavy_strategic_bomber` |
| 28 | `infantry` |
| 29 | `jet_fighter` |
| 30 | `katyusha_rocket_artillery` |
| 31 | `light_armor` |
| 32 | `light_carrier` |
| 33 | `light_cruiser` |
| 34 | `marine` |
| 35 | `mechanized_infantry` |
| 36 | `medium_armor` |
| 37 | `medium_bomber` |
| 38 | `militia` |
| 39 | `motorized_infantry` |
| 40 | `mountain_infantry` |
| 41 | `naval_transport` |
| 42 | `panzergrenadier` |
| 43 | `seaplane` |
| 44 | `self_propelled_artillery` |
| 45 | `strategic_bomber` |
| 46 | `strategic_rocket` |
| 47 | `submarine` |
| 48 | `t_34` |
| 49 | `tactical_bomber` |
| 50 | `tank_destroyer` |
| 51 | `tiger_i` |
| 52 | `torpedo_boat_destroyer` |

### Unit classes

| Number | Name |
| ---: | --- |
| 0 | `air_transport` |
| 1 | `aircraft` |
| 2 | `anti_aircraft_artillery_class` |
| 3 | `artillery_class` |
| 4 | `capital_ship` |
| 5 | `carrier` |
| 6 | `fighter` |
| 7 | `infantry_class` |
| 8 | `land` |
| 9 | `naval` |
| 10 | `naval_transport` |
| 11 | `rocket` |
| 12 | `strategic_bomber` |
| 13 | `submarine` |
| 14 | `surface_ship` |
| 15 | `surface_warship` |
| 16 | `vehicle_class` |

### Facility types

| Number | Name |
| ---: | --- |
| 0 | `airbase` |
| 1 | `coastal_artillery` |
| 2 | `fortification` |
| 3 | `major_dockyard` |
| 4 | `major_factory` |
| 5 | `major_port` |
| 6 | `major_shipyard` |
| 7 | `medium_factory` |
| 8 | `minor_dockyard` |
| 9 | `minor_factory` |
| 10 | `minor_port` |
| 11 | `minor_shipyard` |
| 12 | `railroad` |
| 13 | `seaplane_base` |
| 14 | `submarine_base` |

### Technologies

| Number | Name |
| ---: | --- |
| 0 | `advanced_artillery` |
| 1 | `advanced_mechanized_infantry` |
| 2 | `advanced_submarines` |
| 3 | `airborne_doctrine` |
| 4 | `amphibious_doctrine` |
| 5 | `anti_submarine_warfare` |
| 6 | `heavy_armor` |
| 7 | `heavy_strategic_bombers` |
| 8 | `improved_construction` |
| 9 | `improved_factories` |
| 10 | `improved_logistics` |
| 11 | `jet_fighters` |
| 12 | `large_ship_construction` |
| 13 | `long_range_aircraft` |
| 14 | `radar` |
| 15 | `strategic_rockets` |

### Marks

| Number | Name | Argument |
| ---: | --- | --- |
| 0 | `__campaign_started` | — |
| 1 | `access_to_resources_completed` | — |
| 2 | `air_allied_loaded_turn` | — |
| 3 | `air_battle` | battle |
| 4 | `air_battle_turn` | — |
| 5 | `air_combat` | — |
| 6 | `air_decision_sequence` | — |
| 7 | `air_defending_carrier` | unit |
| 8 | `air_in_flight` | — |
| 9 | `air_landed_after_combat` | — |
| 10 | `air_mission` | — |
| 11 | `air_mission_sequence` | — |
| 12 | `air_roll_sequence` | — |
| 13 | `air_scramble_origin` | zone |
| 14 | `air_scramble_source` | scramble source |
| 15 | `air_scramble_turn` | — |
| 16 | `air_scramble_used` | — |
| 17 | `air_screening_continued` | — |
| 18 | `air_screening_ready` | — |
| 19 | `air_screening_wait` | — |
| 20 | `air_transport_unloaded` | — |
| 21 | `air_waiting_port_evacuation` | — |
| 22 | `airborne_assault` | — |
| 23 | `aligned_turn` | — |
| 24 | `amphibious_assault` | — |
| 25 | `amphibious_preparation` | — |
| 26 | `amphibious_sequence` | — |
| 27 | `amphibious_transport` | unit |
| 28 | `artillery_city_bombing` | — |
| 29 | `assault_declared` | — |
| 30 | `assault_zone` | zone |
| 31 | `attack_rolled` | — |
| 32 | `attrition` | — |
| 33 | `blitz_eligible` | — |
| 34 | `blitz_from` | zone |
| 35 | `blitz_pairing_done` | — |
| 36 | `blitz_to` | zone |
| 37 | `blitz_with` | unit |
| 38 | `bomb_damage` | — |
| 39 | `bombing_reduction` | facility |
| 40 | `bombing_reduction_turn` | facility |
| 41 | `border` | zone |
| 42 | `capture_done` | — |
| 43 | `captured_max_damage` | — |
| 44 | `captured_port_pending` | nation |
| 45 | `carpet_return_started` | — |
| 46 | `casualty_dispute_decided` | — |
| 47 | `chinese_truce_termination` | — |
| 48 | `city_bombing_reduction` | zone |
| 49 | `city_bombing_reduction_turn` | zone |
| 50 | `city_damage` | — |
| 51 | `city_destroyed` | — |
| 52 | `city_ipp_lost` | — |
| 53 | `civil_war_eliminated` | — |
| 54 | `coastal_fire_turn` | — |
| 55 | `coastal_shots_used` | — |
| 56 | `combat` | — |
| 57 | `combat_move` | — |
| 58 | `completed` | — |
| 59 | `controller_unresolved` | — |
| 60 | `crossed_enemy_fortification` | — |
| 61 | `crossing_used` | crossing |
| 62 | `damage` | — |
| 63 | `direct_axis_control_after_japan_surrender` | — |
| 64 | `economy_last_paid_turn` | — |
| 65 | `economy_militia_placed` | zone |
| 66 | `economy_militia_upgrades` | — |
| 67 | `economy_production_cap` | facility |
| 68 | `economy_purchased` | — |
| 69 | `economy_repair_cap` | facility |
| 70 | `economy_repairs_finished` | — |
| 71 | `economy_research_capacity` | — |
| 72 | `economy_research_finished` | — |
| 73 | `economy_research_used` | — |
| 74 | `economy_researched_round` | technology |
| 75 | `economy_sequence` | — |
| 76 | `economy_start_damage` | facility |
| 77 | `economy_start_type` | facility:type |
| 78 | `economy_used` | facility |
| 79 | `escort` | — |
| 80 | `evolution_pending` | nation |
| 81 | `evolved_during_own_turn` | — |
| 82 | `evolved_turn_serial` | — |
| 83 | `facility_upgrade` | — |
| 84 | `finished` | — |
| 85 | `first_allies_major_war_declared` | — |
| 86 | `fixture` | name |
| 87 | `foreign_consent` | nation |
| 88 | `from_attack_naval_transport` | — |
| 89 | `ignore_fortification` | — |
| 90 | `immediate` | — |
| 91 | `immediate_land_battles` | — |
| 92 | `immediate_naval_battles` | — |
| 93 | `in_port` | facility |
| 94 | `incorporated` | — |
| 95 | `influence_attempted` | — |
| 96 | `japanese_surprise_attack` | — |
| 97 | `land_battle_sequence` | — |
| 98 | `land_decision_sequence` | — |
| 99 | `land_retreating` | — |
| 100 | `land_roll_sequence` | — |
| 101 | `last_possession_change_turn` | — |
| 102 | `launched_from_carrier` | — |
| 103 | `lease_available_after_turns` | — |
| 104 | `lease_declared` | nation |
| 105 | `lease_delivered` | nation |
| 106 | `lease_militia_upgrade` | — |
| 107 | `lease_received` | — |
| 108 | `lease_repair` | — |
| 109 | `lease_repair_target` | repair target |
| 110 | `lease_repair_wait` | repair target |
| 111 | `lease_sender` | nation |
| 112 | `lease_wait_controller` | nation |
| 113 | `lend_to` | nation |
| 114 | `logistics_damaged_turn` | facility or railroad |
| 115 | `logistics_last_turn_start` | — |
| 116 | `logistics_rail_created_turn` | railroad |
| 117 | `logistics_start_damaged` | facility |
| 118 | `map_declined_combat` | — |
| 119 | `map_range` | — |
| 120 | `maritime_air_patrol` | — |
| 121 | `moved_this_turn` | — |
| 122 | `must_withdraw_from_chinese_gift` | — |
| 123 | `national_objective_award` | — |
| 124 | `naval_battle` | — |
| 125 | `naval_battle_sequence` | — |
| 126 | `naval_berthing` | — |
| 127 | `naval_casualty_dispute_decided` | — |
| 128 | `naval_combat` | — |
| 129 | `naval_combat_turn` | — |
| 130 | `naval_combat_unloaded` | — |
| 131 | `naval_decision_sequence` | — |
| 132 | `naval_escort` | — |
| 133 | `naval_last_origin` | zone |
| 134 | `naval_loaded_completed_turns` | — |
| 135 | `naval_move_decisions` | — |
| 136 | `naval_move_sequence` | — |
| 137 | `naval_movement_immediate` | — |
| 138 | `naval_movement_plan` | — |
| 139 | `naval_movement_spent` | — |
| 140 | `naval_operation_decision_sequence` | — |
| 141 | `naval_raider` | — |
| 142 | `naval_retreated` | — |
| 143 | `naval_roll_sequence` | — |
| 144 | `naval_scramble_origin` | facility |
| 145 | `naval_scramble_turn` | — |
| 146 | `naval_scramble_used` | — |
| 147 | `naval_scrambled` | — |
| 148 | `naval_screening_continuing` | — |
| 149 | `naval_start_sea` | zone |
| 150 | `naval_strategic_destination` | facility |
| 151 | `naval_strategic_moved` | — |
| 152 | `naval_unloaded` | — |
| 153 | `newly_placed` | — |
| 154 | `objective_evolution` | — |
| 155 | `objective_one_china` | — |
| 156 | `on_map` | — |
| 157 | `one_china_bonus_awarded` | — |
| 158 | `one_china_bonus_eligible_at_surrender` | — |
| 159 | `original_owner` | nation |
| 160 | `original_type` | type |
| 161 | `payment` | payment number |
| 162 | `placed_this_turn` | — |
| 163 | `politics_combat_finished` | — |
| 164 | `politics_sequence` | — |
| 165 | `port_aa_done` | — |
| 166 | `port_crew_prepared` | — |
| 167 | `port_unloaded_round` | — |
| 168 | `possessed_land_ipp` | — |
| 169 | `price` | price method |
| 170 | `purchased` | row or cap group |
| 171 | `raider` | — |
| 172 | `rail_build_permission` | nation:zone:zone |
| 173 | `rail_declined` | project |
| 174 | `rail_permission` | nation |
| 175 | `rail_used` | player:region |
| 176 | `recruitment_attempted` | — |
| 177 | `repair` | — |
| 178 | `repair_at` | facility |
| 179 | `repairing` | — |
| 180 | `researched_this_turn` | — |
| 181 | `retreated` | — |
| 182 | `rocket_launched` | — |
| 183 | `rocket_mission` | — |
| 184 | `row` | build-chart row |
| 185 | `scrambled` | — |
| 186 | `ship_crew` | unit |
| 187 | `shore_bombardment` | — |
| 188 | `shore_dispute_decided` | — |
| 189 | `shore_resolved` | — |
| 190 | `skeleton_crew` | — |
| 191 | `skeleton_crew_until_own_turn` | — |
| 192 | `slip_attempted` | — |
| 193 | `stages_paid` | — |
| 194 | `stages_total` | — |
| 195 | `stranded_aircraft_lost` | — |
| 196 | `strategic_moved` | — |
| 197 | `strategic_naval_movement_in_progress` | — |
| 198 | `strategic_naval_used` | — |
| 199 | `submerged` | — |
| 200 | `surprise_attack_available` | — |
| 201 | `surprise_attack_linked_land` | zone |
| 202 | `surprise_attack_naval_sea` | zone |
| 203 | `surprise_attack_target` | nation |
| 204 | `surprise_attack_used` | — |
| 205 | `surprise_attack_zone` | zone |
| 206 | `surrendered` | — |
| 207 | `target` | repair target |
| 208 | `towed_by` | unit |
| 209 | `towing` | unit |
| 210 | `transport_unloaded` | — |
| 211 | `truce_low_morale_eliminates` | — |
| 212 | `uncontested` | — |
| 213 | `under_construction` | — |
| 214 | `unit_upgrade` | — |
| 215 | `unloaded_combat` | — |
| 216 | `unloaded_noncombat` | — |
| 217 | `upgraded_this_turn` | — |

## 4. Where names become numbers

The engine holds numbers in its memory and names everywhere else:

| Where | Holds | How it converts |
| --- | --- | --- |
| The position (`State`) | Numbers. Zones: each unit's zone, the zone it began its turn in and its route; each facility's zone; the territories, keyed by zone; a railroad's two ends and the damage on each side; a battle's zone; the side of a railroad a repair mends; the zones held at the start of the turn; capitals. Nations: the nations' records, keyed by nation, with each one's wars, allies and controller; the owner of each unit, construction project and repair job; each territory's possessor, now and at the start of the turn; a battle's attacker and defender; each nation's completed turns; the capitals, surrenders, evolutions, alignment queue, attacked warlords and China's invader. Unit types: each unit's type. Facility types: each facility's type. Build types: each construction project's type. Technologies: each nation's research stages, keyed by technology. Marks: the base of each mark on a unit, a nation, a territory, a facility, a construction project, a battle or the position, and of each unit's commitments; the argument stays text | — |
| The catalog (`Catalog`) | Numbers: the definitions of unit types, facility types and technologies, each kept in number order; each unit's classes; the type and upgrade source of each build-chart row and the technologies it requires or forbids; each upgrade's target and required technologies; each unit mode's required technologies; the types a technology unlocks; the capacities Improved Factories gives each facility type, read from that technology's rule once | Built by `Catalog::fromJson` |
| The map index (`IndexedGeography`) | Numbers: each zone's JSON, its neighbors in source order, its first edge to each neighbor, the hops between zones | Built by `freezeDefinition` |
| Saved positions, canonical keys and observations | Names | `State::toJson` and the canonical text's writer name the zones, nations, unit types, facility types, build types, technologies and marks; `State::fromJson` numbers them again and refuses a name its table lacks |
| Planning keys | Numbers: the binary writing the planning key digests holds the numbers of zones, nations, unit types, facility types, technologies and mark bases, and names units, facilities and the rest | The same walk as the canonical text (`writeState`), with a binary writer |
| Moves, decisions and dice requests | Names: a move's details, such as `zone` and `path`, name zones, and the `nation` of a move, a decision or a dice request names the nation that acts | A rule numbers the names as it reads them, such as `nationNumber(state, move.nation)`, and names them as it writes a move |
| The scenario's setup | Names, and the map's own label `airfield` | `loadScenario` numbers each facility's and starting project's type, reading `airfield` as the airbase the scenario contract names |
| A mark's argument | Text: the name of the zone, nation, facility, facility type or other thing the mark is about, as in `surprise_attack_zone:sea_p15` or `original_type:major_factory` | A rule names the zone, nation or type as it sets the mark, such as `MarkKey(mark::surprise_attack_zone, zoneName(state, zone))`, and numbers it as it reads the mark, such as `facilityTypeNumber(state, argument)` |
| Battle notes and political records | Names: such as a battle's `origins` or `last_conqueror_kmt` | A rule names the zone or nation as it writes the note |
| The network input | Zone, nation, unit type, facility type and technology columns in name order, so a number is its column; a project's column through a list by build type; marks through the encoder's own lists of their bases | `Vocabulary::numberBy` in `src/zone_encoding.cpp` checks the order when the encoder is built, and `projectColumn` reads a project's column by its build type; `baseName` gives a mark's base and argument without reading its name |
| Python | Names only | `CampaignEnv.name_tables()` returns the tables |

The functions that convert, declared in `include/game/campaign.hpp`:

| Function | Gives |
| --- | --- |
| `zoneNumber(state, name)` | A zone's number; throws `Unknown zone: <name>` for a name that is no zone |
| `findZone(state, name)` | A zone's number, or nothing, for a name read from data that may be something else, such as a construction site, which is a zone or a facility, or a repair target |
| `zoneName(state, zone)` | A zone's name |
| `zoneNumbers(state, names)`, `zoneNames(state, zones)` | The same for lists |
| `isZone(state, zone)` | Whether a number names one of the definition's zones |
| `nationNumber(state, name)` | A nation's number; throws `Unknown nation: <name>` for a name that is no nation |
| `findNation(state, name)` | A nation's number, or nothing, for a name that may be no nation |
| `nationName(state, nation)` | A nation's name |
| `nationFaction(state, nation)` | A nation's faction definition, such as its home zones, without a name lookup (`Definition::nationFactions`) |
| `knownNations(state)` | The numbers of [the nations the rules name](#the-nations-the-rules-name) |
| `isNation(state, nation, name)` | Whether a nation, or a possessor that may be empty, is the nation of this name; false for an empty possessor and for a name the definition lacks |
| `hasNation(state, name)` | Whether the position holds a nation of this name: Dadao has a number before it is in play |
| `state.currentNation()`, `state.currentNationName()` | The nation whose turn it is, as a number and as a name |
| `definition.turnNations` | The turn order as numbers; `definition.turnOrder` names it |
| `unitTypeNumber(state, name)`, `unitTypeName(state, type)` | A unit type's number, which throws `Unknown unit type: <name>` for a name that is no unit type, and a number's name, from the catalog's table |
| `knownUnitTypes(state)`, `knownUnitClasses(state)` | The numbers of [the unit types and classes the rules name](#the-unit-types-and-classes-the-rules-name) |
| `catalog.unit(type)` | A unit type's definition, by number |
| `catalog.unitHasClass(type, name)` | Whether a unit type has the class a name read from data names, such as a hit's target classes |
| `facilityTypeNumber(state, name)`, `facilityTypeName(state, type)` | A facility type's number, which throws `Unknown facility type: <name>` for a name that is no facility type, and a number's name |
| `technologyNumber(state, name)`, `technologyName(state, technology)` | The same for technologies: `Unknown technology: <name>` |
| `knownFacilityTypes(state)`, `knownTechnologies(state)` | The numbers of [the facility types and technologies the rules name](#the-facility-types-and-technologies-the-rules-name), and the groups of facility types |
| `buildTypeNumber(state, name)`, `buildTypeName(state, type)` | [A build type](#what-a-build-type-is) from the name of a unit type or a facility type, which throws `Unknown build type: <name>` for a name that is neither, and a build type's name |
| `catalog.facility(type)`, `catalog.technology(technology)` | A facility type's or a technology's definition, by number |
| `hasTechnology(state, nation, technology)`, `completedTechnologies(state, nation)` | Whether a nation has completed a technology, which is stage 4 of 4, and the set of all it has completed |

The marks' own, declared in `include/game/marks.hpp`:

| Function | Gives |
| --- | --- |
| `mark::<name>` | A base's number, such as `mark::placed_this_turn` |
| `MarkKey(mark, argument)` | A mark to look up or set; `MarkKey(mark::in_port, facility)` for one with an argument |
| `key.name()` | The mark's name, as saved positions write it |
| `markName(mark)`, `markNumber(name)`, `findMark(name)` | A base's name and number |
| `markArgument(mark)`, `markSeparator(mark)` | What a base's argument names, and the character before it |
| `parseMark(name)`, `findMarkKey(name)` | A mark read from its name; the first throws `Unknown mark: <name>`, the second gives nothing |

## 5. Containers keyed by numbers

- **`NumberMap<Key, Value>`** keeps one slot per number in a vector. It has the
  parts of `std::map`'s interface the engine uses and lists its entries in
  number order, which is name order, but copies without allocating a node per
  entry. The territories, the zones held at the start of the turn, the nations'
  records, their completed turns, their technology stages and the capitals use
  it.
- **`NumberSet<Key>`** keeps one bit per number, with no allocation. A nation's
  wars and allies, the surrendered nations, the nations that have evolved and
  a unit type's classes use it, as do a nation's completed technologies and
  the technologies a build-chart row, a unit mode or an upgrade requires or
  forbids, which `includes` compares in one step; so do the searches, for the
  zones they have seen, and the position's fact cache (`PositionFacts`), for
  the zone sets it keeps.
- **`Marks`** keeps one thing's marks as a sorted vector of small slots (the
  base's number, where its argument lies, the value) and all their arguments
  in one string, so copying a set of marks allocates twice, however many marks
  it holds. It offers the parts of `std::map`'s interface the rules use, an
  entry showing as `{first: key, second: value}`, and `argumentAfter(base,
  prefix)` for the argument of the first mark of a base. **`MarkSet`** is the
  same without values, for a unit's commitments.
- **`SlotMap<Kind, Value>`** keeps the position's units and facilities
  ([slots](#units-and-facilities-slots)). It has the parts of `std::map`'s
  interface the engine uses, by name. It lists its entries in name order
  through a vector of slots sorted by name, and finds a name through a hash
  table of slots, rebuilt when a thing enters or leaves. The things themselves
  live in a `std::deque` that only grows, so a reference to a thing stays valid
  while others enter and leave, and copying the map allocates a few blocks
  instead of a node per thing. It has no `operator[]`: `insert_or_assign`
  replaces a thing and keeps its slot.

## 6. Rules for code

- **A number comes from a table.** `zoneNumber`, `nationNumber`, `findZone`,
  `findNation` and a table's `numbers()` give numbers; only the tables and the
  containers make one from a place (`ZoneId::fromIndex`). There is no
  conversion from an integer, a string or a number of another kind, not even an
  explicit one, so a string can never become a number by accident: a list of
  two string literals would otherwise become a list of zones through
  `std::vector`'s constructor from a pair of iterators. `NumberSet`'s
  constructor from two iterators takes only iterators over numbers, for the
  same reason. `tests/names_tests.cpp` checks at compile time that no string,
  integer or number of another kind becomes a number, and that two names in
  braces do not make a set of numbers.
- **A default number names nothing.** `State::validate` refuses a position
  holding a default `ZoneId` or `NationId`, as it refuses a number beyond its
  table.
- **Convert at the edge.** A rule reads a move's names once, with `zoneNumber`
  or `nationNumber`, and works with numbers from there on.
- **Name a unit type, unit class, facility type or technology through its
  known member,** such as `knownUnitTypes(state).militia`, never by comparing a
  string; add the name to its list in `include/game/catalog.hpp` when a rule
  starts to name it. Ask whether a facility type is in a group, such as the
  naval facilities, with the group's test in `KnownFacilityTypes`, never by
  searching its name.
- **Name a mark through `mark::<name>`,** never by a string. A key with an
  argument refers to the argument's text, so that text must outlive the key: a
  key cannot be made from a temporary string, and an argument built from parts
  goes in a local variable first. Add a row to `GWRL_MARKS`, in name order,
  when a rule starts to note a new mark; tests note their own bookkeeping as
  `fixture:<name>` marks.
- **Ask about a possessor with `isNation`.** A possessor may be empty, and so
  may a known nation the scenario lacks; comparing the two would match
  ([the nations the rules name](#the-nations-the-rules-name)).
- **Never let units or facilities enter or leave while iterating over them.**
  A `SlotMap`'s iterators are places in name order, so an entering or leaving
  thing moves the places after it, where a `std::map`'s iterators kept their
  element. Collect the names first, or erase through the iterator `erase`
  returns. A build with `GWRL_CHECK_SLOT_MAPS` defined throws when an iterator
  is used after its map changed; the C++ suites and 300 random games ran
  without one when units and facilities moved to `SlotMap`s.

## What is still a name

Alliances and players; power statuses; the build-chart rows themselves and the
nation each one names; units, facilities, railroads, construction projects,
repair jobs and battles; the arguments of marks; a move's details, a battle's
notes and the political records; and the rule data the catalog keeps as JSON,
such as a technology's modifiers and conversions, which name unit types and
classes. Each is held as a string.
