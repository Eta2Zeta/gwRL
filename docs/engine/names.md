# Names held as numbers

The scenario names everything with strings: zones such as `land_china_hopeh`,
nations such as `japan`, unit types such as `cavalry`. Inside the engine zones
and nations are held as numbers instead, a few bytes that compare, copy and look
up as fast as any integer. This page says which names the engine holds as
numbers, where each number comes from, where the engine turns names into numbers
and back, and how to look a number up.

Zones and nations are numbers so far. Unit types, the marks on units and the
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
([record](../archive/records/zone_numbers_2026_11_16.md)). Holding nations as
numbers as well took a further 6.6% out of listing the moves and 3.9% to 4.7%
out of a searched game: 11.6% fewer instructions than before either change
([record](../archive/records/nation_numbers_2026_11_16.md)).

## 2. Where the numbers come from

Each kind of name has a table: the definition's names of that kind, sorted
bytewise, a name's number being its place in that list, counted from 0
(`NameTable` in `include/game/names.hpp`). `freezeDefinition` builds the tables
from the definition's own data (`Names` in `include/game/campaign.hpp`); no
table is saved, since the names they are made from are part of the definition.

| Kind | Type | Its names | In the campaign |
| --- | --- | --- | ---: |
| Zones | `ZoneId` | The keys of the map's `nodes` | 37 |
| Nations | `NationId` | The keys of the definition's `factions`, dormant ones included | 13 |

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
  moves and positions at every step of 300 random games and 4 searched games,
  once zones were numbers and again once nations were
  ([zones](../archive/records/zone_numbers_2026_11_16.md),
  [nations](../archive/records/nation_numbers_2026_11_16.md)).
- **A number belongs to its definition.** Adding a zone to the map, or a nation
  to the factions, renumbers those after it. Saved games, planning keys and
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

## 3. The campaign's tables

The campaign, `game_content/scenarios/japan_china_1936`, numbers its names as
follows. `tools/print_name_tables.py` prints these tables from the engine, and
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

## 4. Where names become numbers

The engine holds numbers in its memory and names everywhere else:

| Where | Holds | How it converts |
| --- | --- | --- |
| The position (`State`) | Numbers. Zones: each unit's zone, the zone it began its turn in and its route; each facility's zone; the territories, keyed by zone; a railroad's two ends and the damage on each side; a battle's zone; the side of a railroad a repair mends; the zones held at the start of the turn; capitals. Nations: the nations' records, keyed by nation, with each one's wars, allies and controller; the owner of each unit, construction project and repair job; each territory's possessor, now and at the start of the turn; a battle's attacker and defender; each nation's completed turns; the capitals, surrenders, evolutions, alignment queue, attacked warlords and China's invader | — |
| The map index (`IndexedGeography`) | Numbers: each zone's JSON, its neighbors in source order, its first edge to each neighbor, the hops between zones | Built by `freezeDefinition` |
| Saved positions, planning keys and observations | Names | `State::toJson` and the planning-key writer name the zones and nations; `State::fromJson` numbers them again |
| Moves, decisions and dice requests | Names: a move's details, such as `zone` and `path`, name zones, and the `nation` of a move, a decision or a dice request names the nation that acts | A rule numbers the names as it reads them, such as `nationNumber(state, move.nation)`, and names them as it writes a move |
| Marks on units, nations and territories, and battle notes | Names: such as `surprise_attack_zone:sea_p15` or `last_conqueror_kmt` | A rule names the zone or nation as it writes the mark |
| The network input | Zone and nation columns in name order, so a number is its column | `Vocabulary::numberBy` in `src/zone_encoding.cpp` checks the order when the encoder is built |
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

## 5. Containers keyed by numbers

- **`NumberMap<Key, Value>`** keeps one slot per number in a vector. It has the
  parts of `std::map`'s interface the engine uses and lists its entries in
  number order, which is name order, but copies without allocating a node per
  entry. The territories, the zones held at the start of the turn, the nations'
  records, their completed turns and the capitals use it.
- **`NumberSet<Key>`** keeps one bit per number, with no allocation. A nation's
  wars and allies, the surrendered nations and the nations that have evolved
  use it; so do the searches, for the zones they have seen, and the position's
  fact cache (`PositionFacts`), for the zone sets it keeps.

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
- **Ask about a possessor with `isNation`.** A possessor may be empty, and so
  may a known nation the scenario lacks; comparing the two would match
  ([the nations the rules name](#the-nations-the-rules-name)).

## What is still a name

Alliances and players; unit, facility and technology types; units,
facilities, railroads, construction projects, repair jobs and battles; the
marks on units, nations, territories and battles; a move's details and a
battle's notes. Each is held as a string.
