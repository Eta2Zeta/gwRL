# A fixed zone encoding of campaign decisions — 2 November 2026

The network has so far read each position as a graph built from the game's JSON
text. Every JSON value became a node. Every name was cut into word pieces, and
each piece was hashed into one of 16,384 slots. The slots were averaged per
node, and the nodes were averaged and maximized per position. Names could share
a slot, and the input's size grew with the board. A typical decision took 650 to
790 KB to store, and the largest met 5.1 MB.

This change adds the replacement: a fixed encoding built in C++ directly from
the engine state. Every zone answers the same fixed list of questions. So do
the position as a whole and each legal option. Every answer is an integer,
and no text reaches the network.

The network and the training pipeline still read the old graph input. The next
change switches them over and deletes the old input. The
[evidence file](zone_encoding_2026_11_02.json) holds the exact values.

## What the encoding is

The map has 37 zones: 31 land zones and 6 sea zones. The encoding has three
parts:

- **Zones.** Every zone answers the same 59,322 questions. For example: how
  many Japanese infantry are here, who possesses this land, and is a battle
  in its second round here.
- **The position.** It answers 6,763 questions. For example: the round, the
  phase, whose turn it is, each nation's money, research, alliances and wars,
  and the decision being taken.
- **Each legal option.** It answers 13,031 questions about itself. For
  example: which kind of order it is, which unit it moves (by type and
  condition), and where it moves from, through and to.

Every question has one fixed meaning. Column `units:japan:infantry` in zone 15
always means "Japanese infantry in Hokkaido". Most answers are zero, so only
the nonzero ones are stored, as (zone, question, answer) triples.

Facts that never change come with the layout once, not with every position:

- terrain, production value, capitals, victory cities, original owners and
  home countries (39 facts per zone);
- the 160 directed borders, with their rivers, narrow crossings, railway
  connections and terrain (22 facts per border).

Hokkaido at the start of the game, as stored:

| Question | Answer |
| --- | ---: |
| `possessor:japan` | 1 |
| `turn_start_possessor:japan` | 1 |
| `units:japan:infantry` | 1 |
| `unit_stat:axis:infantry:count` | 1 |
| `unit_stat:axis:infantry:move_1` | 1 |

Tokyo adds its capital, its fighter and two tactical bombers, its airbase,
factory and shipyard, and its railway to Honshu: 16 answers.

The first Combat Movement option of the game moves the CCP cavalry from Shensi
to Hopeh. It is stored as 21 answers:

- it is a played movement route by the Comintern player for the CCP;
- the unit is a CCP cavalry, one unit with movement left at 2, in Shensi,
  which it started the turn in;
- it is the first of the identical cavalry there, and after it in unit order
  come 2 militia and 2 mountain infantry;
- the route passes Shensi and Hopeh, has length 2, uses ordinary movement and
  starts a combat.

The option also names Shensi as its source zone, Hopeh as its target and both
as its path. The network will read those zones' own answers through these
links.

Most columns belong to a few combinations. Among zone columns:

- unit statistics by player, unit type and condition: 15,688;
- carried units by player, carrier type and cargo type: 11,236;
- units in a port or other facility, by the zone the facility opens onto: 7,844.

The layout is as large as the rules allow, not as large as one game uses. The
game's first decision, a declaration offer with 2 options, stores 326 zone
answers, 116 position answers and 8 option answers: 4,996 bytes.

## Rules the encoding follows

**Units are counted, not named.** A unit's ID, such as
`setup_ccp_land_china_shensi_cavalry_1`, appears nowhere. A zone stores how
many units of each nation and type it holds, and how many are damaged, have
moved, are aboard, carry cargo, or have each amount of movement left.

**Identical units still differ in one way.** The engine builds ship and
transport orders by adding units in ID order, so which units can still be added
depends on which unit was taken first. Each option therefore records two
things:

- the chosen unit's rank among identical units in its zone;
- how many units of each type come after it in ID order.

Two options that differ only in which of two identical units they move encode
differently, but only in this rank and count.

**Names come from fixed lists.** Nations, unit types, facilities,
technologies, projects, decision kinds, flags and parameter names each have a
fixed list taken from the rules and the engine. A name not on its list goes to
that list's "other" column. `gwrl_cpp.zone_encoding_unknowns()` counts such
names, so a new rule cannot be dropped silently. The checks below met none.

**Turn numbers become ages.** A flag that stores the turn when something
happened becomes "turns since", counted 1 + min(now − then, 30). Equal
situations in different turns then look alike.

**The layout has a version.** It is `campaign-zone-v1-11dda95a8ed9de22`, made
from a hash of every column name and every fixed map fact. A model built for one
layout can refuse another.

## Is anything lost?

`tools/check_zone_encoding.py` plays complete games and encodes every decision.
It checks two things:

1. **Look-alike positions.** Two positions with the same encoding must offer
   the same options, compared by their encodings. Otherwise the network cannot
   tell apart positions whose legal moves differ.
2. **Look-alike options.** Two options of one position with the same encoding
   must lead to positions with the same encoding. Otherwise two different moves
   look alike. The check plays both options on copies of the game and compares
   the results.

| Games | Positions | Distinct encodings | Look-alike positions with different options | Look-alike option groups played out | Leading to different positions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Random, 3 rounds, seeds 1951–1952 | 1,336 | 1,335 | 0 | 18 | 0 |
| Scripted, 3 rounds, seed 1951 | 640 | 640 | 0 | 8 | 0 |
| Random, 11 rounds, seed 1953 | 1,702 | 1,702 | 0 | 22 | 0 |
| Scripted, 11 rounds, seed 1953 | 2,240 | 2,240 | 0 | 64 | 0 |
| Random, 11 rounds, seeds 2101–2103, dense | 5,362 | 5,353 | 0 | 324 | 0 |
| Random, 11 rounds, seeds 2104–2106, dense | 5,401 | 5,393 | 0 | 276 | 0 |
| Scripted, 11 rounds, seeds 2101–2103, dense | 6,585 | 6,554 | 0 | 583 | 0 |
| Scripted, 11 rounds, seeds 2104–2106, dense | 6,993 | 6,854 | 0 | 676 | 0 |
| **All** | **30,259** | | **0** | **1,971** | **0** |

Positions include 4,244 chance positions, encoded without options. Where a
position's encoding repeated an earlier one, it also offered the same options.
No name fell into an "other" column. All runs used layout
`campaign-zone-v1-11dda95a8ed9de22`.

Random games choose uniformly among the legal options. Scripted games use the
repository's baseline policy, which reaches longer wars and fuller boards. In
the dense runs, every second decision had up to three groups of look-alike
options played out; in the others, every fifth decision had up to two. The
checks read each decision's encoding through the same per-decision cache the
pipeline will use.

The same checks found these gaps while the encoder was being written, and each
is closed:

- the zone of a loaded unit;
- the ID order in which ship orders are built, now recorded by rank and later
  units;
- which port a ship sits in, and the borders of ports and other facilities;
- where cargo started the turn, and the flags of cargo;
- project progress and payment turns;
- railway permission and Chinese liberation decisions waiting to be answered.

One gap remains. Reversible orders cannot return to an arrangement already
visited in the same decision: raider designations and zero-distance carrier
landings. The engine keeps a log of visited arrangements to enforce this. The
encoding stores only the log's length, not its contents. Two positions that
differ only in which arrangements were visited would encode alike; their
options would still differ, and the network would see that. The checks met no
such pair.

## Size and speed

Sizes are the bytes kept for one decision with all its options. For the zone
encoding that is every array plus the four policy-group labels per option. For
the graph input it is the compacted observation plus every option graph, as
replay stored them. Build times are first builds of a decision, from Python,
on the same container.

| Games | Zone encoding, median | largest | Graph input, median | largest | Zone build, median ms | Graph build, median ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Random, 3 rounds, seeds 1951–1952 | 12.8 KB | 48.7 KB | 713 KB | 2.43 MB | 0.48 | 2.95 |
| Scripted, 3 rounds, seed 1951 | 10.6 KB | 49.7 KB | 649 KB | 2.30 MB | 0.50 | 2.70 |
| Random, 11 rounds, seed 1953 | 16.2 KB | 86.3 KB | 785 KB | 3.59 MB | 0.64 | 3.66 |
| Scripted, 11 rounds, seed 1953 | 12.6 KB | 61.2 KB | 765 KB | 3.16 MB | 0.59 | 3.20 |
| Random, 11 rounds, seeds 2101–2103, dense | 14.5 KB | 86.9 KB | 747 KB | 3.24 MB | 0.59 | 3.45 |
| Random, 11 rounds, seeds 2104–2106, dense | 13.8 KB | 128.2 KB | 720 KB | 4.45 MB | 0.55 | 3.29 |
| Scripted, 11 rounds, seeds 2101–2103, dense | 11.3 KB | 144.9 KB | 713 KB | 5.12 MB | 0.61 | 3.27 |
| Scripted, 11 rounds, seeds 2104–2106, dense | 11.5 KB | 88.9 KB | 734 KB | 3.71 MB | 0.64 | 3.52 |

Sizes were compared at every tenth decision; zone build times cover every
decision. Four checks ran at once on the 4-vCPU container, so the times are
comparable with each other but not a clean benchmark.

Per run, the median decision is 49 to 64 times smaller and builds 5.3 to 6.1
times faster. The largest decision met is 145 KB, against 5.1 MB for the
largest graph input. The first decision of a process also builds the layout
once: 28 to 33 ms in five fresh processes. Later first builds take about 0.25
ms.

## What follows

The next change replaces the network and the pipeline's input. The network will:

- build 37 zone vectors from the stored answers and the fixed map facts;
- pass messages along the 160 borders;
- read the position's value from all zones and the position's own answers;
- score each option from its own answers and the vectors of its source, path
  and target zones.

The old graph input, its C++ builders and its hashing are then deleted. Its
measurements here stay as the comparison.

## Reproduce

```sh
./.venv/bin/python setup.py build_ext --inplace
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build && ctest --test-dir build -R zone_encoding --output-on-failure
./.venv/bin/python -m unittest tests.test_campaign_zone_encoding
./.venv/bin/python tools/check_zone_encoding.py out.json --rounds 11 --seeds 2101 2102 2103 \
    --policy balanced --successor-stride 2 --groups-per-position 3
```

## Update, 3 November 2026: impossible columns removed, rows start at zero

**Impossible columns.** A column is kept unless the rules of the whole game rule
it out; a rare situation keeps its column. Three rules remove 24,974 columns:
zone columns fall from 59,322 to 35,407, position columns from 6,763 to 6,621,
and option columns from 13,031 to 12,114. The layout is now
`campaign-zone-v1-edcfe0583896a5da`.

- **Other nations' special units.** A type the rulebook reserves for some nations
  (its catalog `national_exclusive_type` rule) belongs to them alone. Tiger I and
  Panzergrenadier are German, T-34 and Katyusha Soviet, B-29 American, Gurkha
  FEC; Foreign Legion and colonial infantry belong to the French and Commonwealth
  nations and Italy. No nation of this scenario may own one, so their columns go.
  A scenario with Germany would keep Germany's. The coastal defense ship is
  reserved for nobody and ships change hands by capture, so it stays.
- **Carried units.** Only pairs the rules allow remain: naval transports carry
  land units, a Japanese destroyer one Marine, carriers fighters and tactical
  bombers (medium bombers on heavy fleet carriers), and air transports and
  strategic bombers the cargo their catalog rules accept. 69 of 2,809 pairs.
- **Units in facilities.** Only ships and aircraft point at facilities, and only
  naval facilities, which face the sea, have borders a unit sees. Land units
  leave the facility columns, and land zones the facility-border columns.

Each family with removed columns keeps one `~impossible` column. A removed
combination that occurs anyway is counted there and reported by
`gwrl_cpp.zone_encoding_unknowns()`, never dropped. Encoding every decision of
240 random 11-round games (372,935 decisions) met none, and the look-alike
check above found no collisions in three 3-round games. The network shrinks
from 5.20 M to 3.60 M parameters at width 64 with 2 layers, and from 24.67 M to
18.27 M at width 256 with 8 layers.

That longer random check found 31 names missing from the fixed lists, which
still fall into "other" columns: battle-data fields such as `map_attack` and
`naval_submarine_choices`, rail identifiers passed as option values, a `damage`
parameter and a zone named as a repair target. The short checks above meet none.

**Rows start at zero.** The zone, position and option rows now start at zero,
so a question no training has reached adds nothing; before, every row started
as a random vector as large as a trained one. On fixed data (32 training and 8
held-out three-round games played by search with a uniform prior, width 128
with 4 layers, 600 steps of 64 positions), the held-out value error over the
last 300 steps averaged 0.0076 against 0.0081 with random rows, and the policy
loss was the same (1.779). One seed on small data: no harm shown, not a
strength result.
