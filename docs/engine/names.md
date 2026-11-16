# Names held as numbers

The scenario names everything with strings: zones such as `land_china_hopeh`,
nations such as `japan`, unit types such as `cavalry`. Inside the engine zones,
nations, unit types and unit classes are held as numbers instead, a few bytes
that compare, copy and look up as fast as any integer. This page says which names the engine holds as
numbers, where each number comes from, where the engine turns names into numbers
and back, and how to look a number up.

Zones, nations, unit types and unit classes are numbers so far. Facility types,
technologies, the marks on units and the units themselves are still held by
name; [what is still a name](#what-is-still-a-name) lists them.

## 1. Why numbers

Before zones were numbered, 59% of the engine's time went to comparing names,
allocating memory, looking up maps and copying memory, against 41% to the rules'
own logic ([record](../archive/records/self_play_limits_2026_11_16.md#inside-the-engine)).
The position kept its zones, units, facilities and nations in maps keyed by
name, and every rule check named them as strings. Holding zones as numbers took
13.0% of the instructions out of listing a position's moves and 7.2% to 7.9%
out of a searched game, with play unchanged
([record](../archive/records/zone_numbers_2026_11_16.md)). Holding nations as
numbers as well took a further 6.6% out of listing the moves and 3.9% to 4.7%
out of a searched game: 11.6% fewer instructions than before either change
([record](../archive/records/nation_numbers_2026_11_16.md)). Holding unit types
and classes as numbers took a further 4.7% out of listing the moves and 2.5% out
of a searched game: 13.8% fewer instructions than before any of these changes
([record](../archive/records/unit_type_numbers_2026_11_16.md)).

## 2. Where the numbers come from

Each kind of name has a table: its names sorted bytewise, a name's number
being its place in that list, counted from 0 (`NameTable` in
`include/game/names.hpp`). `freezeDefinition` builds the tables of zones and
nations from the definition's own data (`Names` in `include/game/campaign.hpp`),
and `Catalog::fromJson` the tables of unit types and unit classes from the
catalog's (`include/game/catalog.hpp`). No table is saved, since the names they
are made from are part of the definition and of the catalog.

| Kind | Type | Its names | In the campaign |
| --- | --- | --- | ---: |
| Zones | `ZoneId` | The keys of the map's `nodes` | 37 |
| Nations | `NationId` | The keys of the definition's `factions`, dormant ones included | 13 |
| Unit types | `UnitTypeId` | The catalog's units (`land_air.json` and `naval.json` in `game_content/catalog/gw36_v43`) | 53 |
| Unit classes | `UnitClassId` | Every class some unit of the catalog has | 17 |

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
  [unit types](../archive/records/unit_type_numbers_2026_11_16.md)).
- **A number belongs to its definition or catalog.** Adding a zone to the map,
  a nation to the factions or a unit type to the catalog renumbers those after
  it. Saved games, planning keys and
  moves hold names, so they are unaffected; only the engine's memory holds
  numbers.

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
definition has a catalog; `State::validate` refuses a unit otherwise.

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

## 4. Where names become numbers

The engine holds numbers in its memory and names everywhere else:

| Where | Holds | How it converts |
| --- | --- | --- |
| The position (`State`) | Numbers. Zones: each unit's zone, the zone it began its turn in and its route; each facility's zone; the territories, keyed by zone; a railroad's two ends and the damage on each side; a battle's zone; the side of a railroad a repair mends; the zones held at the start of the turn; capitals. Nations: the nations' records, keyed by nation, with each one's wars, allies and controller; the owner of each unit, construction project and repair job; each territory's possessor, now and at the start of the turn; a battle's attacker and defender; each nation's completed turns; the capitals, surrenders, evolutions, alignment queue, attacked warlords and China's invader. Unit types: each unit's type | — |
| The catalog (`Catalog`) | Numbers: the unit definitions, kept in unit type order, and each one's classes | Built by `Catalog::fromJson` |
| The map index (`IndexedGeography`) | Numbers: each zone's JSON, its neighbors in source order, its first edge to each neighbor, the hops between zones | Built by `freezeDefinition` |
| Saved positions, planning keys and observations | Names | `State::toJson` and the planning-key writer name the zones, nations and unit types; `State::fromJson` numbers them again |
| Moves, decisions and dice requests | Names: a move's details, such as `zone` and `path`, name zones, and the `nation` of a move, a decision or a dice request names the nation that acts | A rule numbers the names as it reads them, such as `nationNumber(state, move.nation)`, and names them as it writes a move |
| Build-chart rows, upgrades and construction projects | Names: a row's and a project's type may be a unit type or a facility type | `catalog.unit(name)` and `catalog.isUnitType(name)` read a unit type by name where one is read |
| Marks on units, nations and territories, and battle notes | Names: such as `surprise_attack_zone:sea_p15` or `last_conqueror_kmt` | A rule names the zone or nation as it writes the mark |
| The network input | Zone, nation and unit type columns in name order, so a number is its column | `Vocabulary::numberBy` in `src/zone_encoding.cpp` checks the order when the encoder is built |
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

## 5. Containers keyed by numbers

- **`NumberMap<Key, Value>`** keeps one slot per number in a vector. It has the
  parts of `std::map`'s interface the engine uses and lists its entries in
  number order, which is name order, but copies without allocating a node per
  entry. The territories, the zones held at the start of the turn, the nations'
  records, their completed turns and the capitals use it.
- **`NumberSet<Key>`** keeps one bit per number, with no allocation. A nation's
  wars and allies, the surrendered nations, the nations that have evolved and
  a unit type's classes use it; so do the searches, for the zones they have
  seen, and the position's fact cache (`PositionFacts`), for the zone sets it
  keeps.

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
- **Name a unit type or class through its known member,** such as
  `knownUnitTypes(state).militia`, never by comparing a string; add the name to
  its list in `include/game/catalog.hpp` when a rule starts to name it.
- **Ask about a possessor with `isNation`.** A possessor may be empty, and so
  may a known nation the scenario lacks; comparing the two would match
  ([the nations the rules name](#the-nations-the-rules-name)).

## What is still a name

Alliances and players; facility types, technologies, and the types of
build-chart rows, upgrades and construction projects, which may be a unit or a
facility; units, facilities, railroads, construction projects, repair jobs and
battles; the marks on units, nations, territories and battles; a move's details
and a battle's notes. Each is held as a string.
