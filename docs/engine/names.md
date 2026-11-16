# Names held as numbers

The scenario names everything with strings: zones such as `land_china_hopeh`,
nations such as `japan`, unit types such as `cavalry`. Inside the engine a
zone is held as a number instead, a few bytes that compare, copy and look up as
fast as any integer. This page says which names the engine holds as numbers,
where each number comes from, where the engine turns names into numbers and
back, and how to look a number up.

Only zones are numbers so far. Nations, unit types, the marks on units and the
units themselves are still held by name; [what is still a name](#what-is-still-a-name)
lists them.

## 1. Why numbers

Before zones were numbered, 59% of the engine's time went to comparing names,
allocating memory, looking up maps and copying memory, against 41% to the rules'
own logic ([record](../archive/records/self_play_limits_2026_11_16.md#inside-the-engine)).
The position kept its zones, units, facilities and nations in maps keyed by
name, and every rule check named them as strings. Holding zones as numbers took
13.0% of the instructions out of listing a position's moves and 7.2% to 7.9%
out of a searched game, with play unchanged
([record](../archive/records/zone_numbers_2026_11_16.md)).

## 2. Where the numbers come from

Each kind of name has a table: the definition's names of that kind, sorted
bytewise, a name's number being its place in that list, counted from 0
(`NameTable` in `include/game/names.hpp`). `freezeDefinition` builds the tables
from the definition's own data (`Names` in `include/game/campaign.hpp`); no
table is saved, since the names they are made from are part of the definition.

| Kind | Type | Its names | In the campaign |
| --- | --- | --- | ---: |
| Zones | `ZoneId` | The keys of the map's `nodes` | 37 |

Because a number is a place in a sorted list:

- **Numbers compare as their names do.** Zone 0, `land_china_beiping`, comes
  before zone 1, `land_china_hopeh`, as the names do.
- **Play is unchanged.** A container keyed by numbers lists its entries in the
  order the same container keyed by names did, so every list of moves comes out
  in the same order as before. `tools/compare_engine_builds.py` found the same
  moves and positions at every step of 300 random games and 4 searched games
  ([record](../archive/records/zone_numbers_2026_11_16.md)).
- **A number belongs to its definition.** Adding a zone to the map renumbers the
  zones after it. Saved games, planning keys and moves hold names, so they are
  unaffected; only the engine's memory holds numbers.

## 3. The zones of the campaign

The campaign's map, `game_content/scenarios/japan_china_1936`, numbers its
zones as follows. `tools/print_name_tables.py` prints this table from the
engine, and `tests/test_name_tables.py` checks that it matches.

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

## 4. Where names become numbers

The engine holds numbers in its memory and names everywhere else:

| Where | Holds | How it converts |
| --- | --- | --- |
| The position (`State`) | Numbers: each unit's zone, the zone it began its turn in and its route; each facility's zone; the territories, keyed by zone; a railroad's two ends and the damage on each side; a battle's zone; the side of a railroad a repair mends; the zones held at the start of the turn; capitals | — |
| The map index (`IndexedGeography`) | Numbers: each zone's JSON, its neighbors in source order, its first edge to each neighbor, the hops between zones | Built by `freezeDefinition` |
| Saved positions, planning keys and observations | Names | `State::toJson` and the planning-key writer name the zones; `State::fromJson` numbers them again |
| Moves | Names: a move's details, such as `zone` and `path`, name zones | A rule numbers a move's zones as it reads them and names them as it writes a move |
| Marks on units, nations and territories, and battle notes | Names: such as `surprise_attack_zone:sea_p15` | A rule names the zone as it writes the mark |
| The network input | Zone columns in name order, so a zone's number is its column | `numberByZones` in `src/zone_encoding.cpp` checks the order when the encoder is built |
| Python | Names only | `CampaignEnv.name_tables()` returns the tables |

The functions that convert, declared in `include/game/campaign.hpp`:

| Function | Gives |
| --- | --- |
| `zoneNumber(state, name)` | A zone's number; throws `Unknown zone: <name>` for a name that is no zone |
| `findZone(state, name)` | A zone's number, or nothing, for a name read from data that may be something else, such as a construction site, which is a zone or a facility, or a repair target |
| `zoneName(state, zone)` | A zone's name |
| `zoneNumbers(state, names)`, `zoneNames(state, zones)` | The same for lists |
| `isZone(state, zone)` | Whether a number names one of the definition's zones |

## 5. Containers keyed by numbers

- **`NumberMap<Key, Value>`** keeps one slot per number in a vector. It has the
  parts of `std::map`'s interface the engine uses and lists its entries in
  number order, which is name order, but copies without allocating a node per
  entry. The territories and the zones held at the start of the turn use it.
- **`NumberSet<Key>`** keeps one bit per number, with no allocation. The
  searches use it for the zones they have seen, and the position's fact cache
  (`PositionFacts`) for the zone sets it keeps.

## 6. Rules for code

- **A number comes from a table.** `zoneNumber`, `findZone` and a table's
  `numbers()` give numbers; only the tables and the containers make one from a
  place (`ZoneId::fromIndex`). There is no conversion from an integer or a
  string, not even an explicit one, so a string can never become a number by
  accident: a list of two string literals would otherwise become a list of
  zones through `std::vector`'s constructor from a pair of iterators.
- **A default `ZoneId` names no zone.** `State::validate` refuses a position
  holding one, as it refuses a number beyond the table.
- **Convert at the edge.** A rule reads a move's zone names once, with
  `zoneNumber`, and works with numbers from there on.

## What is still a name

Nations, alliances and players; unit, facility and technology types; units,
facilities, railroads, construction projects, repair jobs and battles; the
marks on units, nations, territories and battles; a move's details and a
battle's notes. Each is held as a string.
