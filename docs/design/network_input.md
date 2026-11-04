# The network's input

This page explains, layer by layer, how one decision of the game becomes the
numbers a network reads. It belongs to the [design document](README.md), whose
section 4 summarizes it. The encoder is C++ (`src/zone_encoding.cpp`);
`studies/campaign/features.py` turns its output into arrays and
`studies/campaign/neural.py` reads them. Measurements and the reasons for the
design are in the [zone encoding record](../stage_a/zone_encoding_2026_11_02.md).

## 1. When and how the input is built

Whenever the search reaches a decision it has not seen, it asks the deciding
alliance's network about it (see [search](README.md#3-choosing-a-move-search)).
Before that, the engine encodes the position once. Search copies of the same
position share that encoding, and a kept training sample stores it. The input
describes one decision: both the state of the game and the moves on offer.

**The encoder reads the engine's memory directly.** It is C++ code inside the
engine. It reads the live game state and receives the legal moves as the
engine's own move objects. Nothing is written out as text or parsed on the way.

**But the engine identifies everything by name.** Its state is not stored as
numbers:

- a unit's type, owner and zone are names: `cavalry`, `ccp`, `land_china_shensi`;
- a unit's marks are a table of names and numbers, such as `repairing` → 1;
- a battle's notes, and a legal move's details, are small trees of named
  entries, such as `target` → `rail_land_manchuria_northern__land_manchuria_western`
  and `damage` → 1.

So the encoder translates each name into a question number, using fixed lists of
the names it knows ([section 7](#7-names-the-encoder-doesnt-know)). That
translation is where "names" and "missing names" come from.
[Section 10](#10-why-the-encoder-translates-names) explains why the engine works
with names and what the alternatives are.

**Encoding is cheap.** In three random eleven-round games (4,786 decisions,
measured on 3 November 2026 on the M4 Max), encoding a decision took 0.17 ms on
average, against 0.64 ms to list its legal moves and 0.80 ms to play a move. A
self-play game encodes about 60,000 positions, one per network evaluation. That
is about 10 seconds of the roughly 260 CPU-seconds a game process spent per game
in the 2 November profile: about 4%, a rough estimate.

## 2. Three parts

The input for one decision is one bundle with three parts:

1. **The board:** each of the 37 zones (31 land and 6 sea) answers the same list
   of 35,407 zone questions.
2. **The position as a whole:** 6,621 questions about the round, the phase,
   whose turn it is, treasuries, wars and so on.
3. **Each legal move:** every move on the menu answers the same list of 12,114
   move questions about itself.

**A real decision** (game seed 5): the CCP's first Combat Movement decision of
round 1, chosen by the Comintern player. It has 13 legal moves, and its input
holds 326 board answers, 119 position answers and 244 answers across the 13
moves.

## 3. Questions and answers

**A question** is a numbered slot with one fixed meaning, also called a column.
Its name, such as `units:ccp:cavalry`, is a readable label for that meaning;
the network only sees the number. A name is built as `family:part:part`. The
family says what kind of question it is, and the parts say which nation, which
unit type, which zone and so on. The board has 40 families, the position 57 and
the moves 43.

**An answer** is a whole number: a count ("how many?"), 1 for "yes", or a value
such as the round. Almost every answer is 0, so only the non-zero answers are
stored.

These are all the non-zero board answers of the zone Shensi in that decision:

| Question | Answer | Meaning |
| --- | ---: | --- |
| `possessor:ccp` | 1 | the CCP possesses Shensi |
| `turn_start_possessor:ccp` | 1 | it did at the start of the turn too |
| `units:ccp:cavalry` | 1 | one CCP cavalry here |
| `units:ccp:militia` | 2 | two CCP militia |
| `units:ccp:mountain_infantry` | 2 | two CCP mountain infantry |
| `unit_stat:comintern:cavalry:count` | 1 | one Comintern cavalry |
| `unit_stat:comintern:cavalry:move_2` | 1 | ... with 2 moves left |
| `unit_stat:comintern:militia:count` | 2 | two Comintern militia |
| `unit_stat:comintern:militia:move_0` | 2 | ... with no moves left |
| `unit_stat:comintern:mountain_infantry:count` | 2 | two Comintern mountain infantry |
| `unit_stat:comintern:mountain_infantry:move_1` | 2 | ... with 1 move left |
| `rail_to:land_china_hopeh` | 1 | a railroad runs from here to Hopeh |

The network adds each answer in as sign(a) × log(1 + |a|): see
[what a network computes](README.md#5-what-a-network-computes).

## 4. The board part

The largest zone families:

| Family | Columns | Asks, for one zone |
| --- | ---: | --- |
| `unit_stat` | 13,321 | how many units of an alliance and type have a condition: damaged, moved, moves left, ... |
| `unit_reference_here` | 4,501 | how many units, by alliance and type, point at this zone, and why: a blitz destination, an assault target, a route, ... |
| `battle_data_unit`, `battle_data_zone` | 5,249 | what a battle's notes say about unit types and zones |
| `unit_flag` | 1,984 | how many units carry each mark, such as "landed after combat" |
| `facility_flag` | 1,792 | marks on a facility here |
| `unit_facility` | 1,601 | units inside a facility, by type and facility type |
| `units` | 586 | how many units of each nation and type are here |
| `carried` | 277 | carried units, by carrier type and cargo type |
| `possessor`, `capital_of` | 27 | who holds the zone, whose capital it is |
| `rail_to`, `rail_damage_toward` | 74 | railroads to each neighbour, and their damage |

**Units are counted, not named.** The engine gives every unit a unique name.
Units on the board from the start are named like `setup_japan_sea_p15_destroyer_2`:
on the board from the start, owned by Japan, started in sea zone P15, a
destroyer, the second of its kind there. Things created during play get counter
names: `economy_unit_112` is a unit bought during the game, and `economy_rail_8`
a railroad built during the game. The network never reads these names. It sees
counts and conditions, such as "one Japanese destroyer here, undamaged, already
moved".

**Battle notes.** While a battle is being fought, the engine keeps notes on it:
the round, the defenders, where the attackers came from and so on. They become
the `battle_data` families. Section 7 shows a real example.

**Turn numbers become ages.** A mark that stores the turn when something happened
is turned into "turns since", so equal situations in different turns look alike.

## 5. The position part

The position answers questions such as `round`, `rounds_left`, `phase:<phase>`,
`turn_nation:<nation>`, `treasury:<nation>`, `at_war:<nation>:<nation>`,
`technology_stage:<nation>:<technology>`, the kind of decision being taken
(`decision:<kind>`) and the purpose of a pending dice roll. In the seed-5 decision
these include:

```text
round = 1
rounds_left = 11
phase:combat_movement = 1
turn_nation:ccp = 1
nation_present:<nation> = 1     one answer per nation in the game
```

## 6. The move part

### How the engine writes a move

A legal move is a kind plus labelled details. Each detail has a label on the
left and a value on the right. The engine's rule code chose the labels:

```text
kind:     economy_repair
target:   rail_land_manchuria_northern__land_manchuria_western
endpoint: land_manchuria_northern
damage:   1
```

### How each detail becomes answers

Every move first says who chooses and what kind of move it is, for example
`schedule:play = 1`, `player:axis = 1`, `nation:japan = 1` and
`kind:air_start_patrol = 1`. Then, for each detail, the encoder records that a
detail with this label exists, such as `parameter:range = 1`, and then the
detail's value. How it records the value depends on what the value is.

All the examples below are details of real legal moves from a random game (seed
7001; the railroad repair is from seed 7004).

**Plain values:**

| Value | Real example | Answers |
| --- | --- | --- |
| A number | A Japanese seaplane in Okinawa starts a patrol over sea zone P33: `range = 2` | `number:range = 2` |
| True | A Japanese infantry moves from Rehe into Beiping to attack: `combat = true` | `true:combat = 1` |
| False | A Japanese transport enters Formosa's port without unloading: `unload = false` | `false:unload = 1` |
| Nothing | A Japanese heavy cruiser moves from sea zone P16 to P15, starting and ending at sea, not in a port: `origin_facility = null`, `destination_facility = null` | `null:origin_facility = 1`, `null:destination_facility = 1` |
| A list | A Japanese fighter flies from Formosa over P32 to attack Hunan: `path = [land_formosa, sea_p32, land_china_hunan]` | `list_length:path = 3`, then each item as its own value: `zone:1_path:land_formosa = 1`, `zone:1_path:sea_p32 = 1`, `zone:1_path:land_china_hunan = 1` |
| A group of details | The cruiser's move keeps its details in one group: `request = {combat = true, strategic = false, path = [sea_p16, sea_p15], units = [setup_japan_sea_p16_heavy_cruiser_1], ...}` | `parameter:request = 1`, then each inner detail as if it stood alone: `true:combat = 1`, `false:strategic = 1`, `list_length:path = 2`, `zone:1_path:sea_p16 = 1`, ..., `unit:0_source:japan:heavy_cruiser = 1`, ... |

**Names of things.** A name is replaced by what the thing is; the name itself
never reaches the network.

| Value | Real example | Answers |
| --- | --- | --- |
| A unit's name | The fighter attacking Hunan: `unit = setup_japan_land_formosa_fighter_1` | `unit:0_source:japan:fighter = 1` (a Japanese fighter), `unit_stat:0_source:count = 1`, `unit_stat:0_source:move_4 = 1` (4 moves left), `unit_zone:0_source:land_formosa = 1` (it is in Formosa), `unit_turn_origin:0_source:land_formosa = 1` (it started the turn there), `unit_rank:0_source:0 = 1` (the first Japanese fighter there), `unit_later_peers:0_source:militia = 1` (one militia comes after it in unit order) |
| A zone's name | Japan buys an airbase to build in Formosa: `zone = land_formosa` | `zone:2_target:land_formosa = 1` |
| A facility's name | The transport entering port: `facility = facility_land_formosa_major_port` | `facility:0_source:major_port = 1` |
| A battle's name | The CCP starts its battle in Hopeh: `battle = land_battle_2` | `battle_stage:0_source:awaiting_combat_rules = 1`, `battle_attacker:0_source:ccp = 1`, `battle_defender:0_source:warlord_beiping_hopeh = 1`, `battle_units:0_source:cavalry = 1`, `battle_units:0_source:militia = 1`, `battle_place:0_source:land_china_shensi = 2` (the battle's notes name Shensi twice) |
| A construction project's name | Japan pays the next instalment on a fleet carrier it is building: `project = japan_queue_fleet_carrier` | `project:0_source:fleet_carrier = 1`, `project_owner:0_source:japan = 1`, `project_stat:0_source:paid_ipp = 5` (5 IPP paid), `project_stat:0_source:payments_left = 2`, `project_stat:0_source:remaining_payments = 10` (two payments, 10 IPP, to go), `project_stat:0_source:queue_position = 3`, `project_stat:0_source:count = 1` |
| A build-chart row | The airbase purchase: `row = japan_major_airbase` | `row:japan_major_airbase = 1` |
| A nation's name | The KMT declares war on Japan: `target = japan` | `nation_named:2_target:japan = 1` |
| A technology | Japan starts research at its Tokyo factory: `technology = advanced_artillery` | `technology:advanced_artillery = 1` |
| Any other name, on the list of known values | The airbase purchase, at the printed price: `price = printed` | `value:price:printed = 1` |
| Any other name, not on the list | The railroad repair ([example 2](#example-2-a-railroad-repair)): `target = rail_land_manchuria_northern__land_manchuria_western` | `value:target:other = 1` |

The `0_source`, `1_path` and `2_target` parts of these names are roles, explained
next.

### Roles

Many questions carry a role, the `0_source`, `1_path`, `2_target` or `3_other` in
`zone:1_path:land_china_hopeh`. The role says how the move relates to the unit or
zone that a detail names:

- `0_source`: what acts, or where the move starts;
- `1_path`: the route the move travels;
- `2_target`: what the move acts on, or where it goes;
- `3_other`: the move mentions it, but the encoder cannot say how.

The encoder cannot understand what a label means: to it, `endpoint` is just a
string of letters. So the role comes from a fixed table in `src/zone_encoding.cpp`
that pairs labels with roles:

| Label | Role |
| --- | --- |
| artillery, battle, facility, factory, origin_facility, plan, project, row, source, transport, unit, units | `0_source` |
| path | `1_path` |
| beneficiary, border, border2, declaring_nation, destination, destination_facility, neighbor, recipient, sea, target, technology, zone, zones | `2_target` |
| any label not in the table | `3_other` |

The role changes three things:

1. **The question.** `zone:2_target:land_china_beiping` and
   `zone:3_other:land_china_beiping` are different questions with different
   learned rows.
2. **The links to zones.** The network reads three zones' board vectors with each
   move: the zone it starts from (the first `0_source` zone, or else the first
   `3_other` zone), the zone it acts on (the last path zone, or else the first
   `2_target` zone) and the average of its path zones.
3. **The probability stages.** "What acts" is built from the `0_source` details,
   "how it travels" from the `1_path` details and path zones, and "what it acts on"
   from the `2_target` details. `3_other` details belong to no stage.

The encoder keeps two separate lists of labels. The list of known labels (92 of
them) decides questions like `parameter:endpoint`. The role table (26 labels)
decides roles. A label can be on the first and missing from the second, as
`endpoint` is.

### Example 1: a cavalry attack

The CCP cavalry in Shensi attacks Hopeh. In the engine's form:

```text
movement_route   unit = setup_ccp_land_china_shensi_cavalry_1
                 path = [land_china_shensi, land_china_hopeh]
                 combat = true, mode = ordinary
```

It becomes 21 answers:

| Question | Answer | Meaning |
| --- | ---: | --- |
| `schedule:play` | 1 | an ordinary move in play |
| `player:comintern` | 1 | the Comintern player chooses |
| `kind:movement_route` | 1 | a movement move |
| `nation:ccp` | 1 | for the CCP |
| `parameter:unit`, `parameter:path`, `parameter:combat`, `parameter:mode` | 1 each | it has these four details |
| `unit:0_source:ccp:cavalry` | 1 | the unit that acts is a CCP cavalry |
| `unit_stat:0_source:count` | 1 | one unit |
| `unit_stat:0_source:move_2` | 1 | with 2 moves left |
| `unit_zone:0_source:land_china_shensi` | 1 | standing in Shensi |
| `unit_turn_origin:0_source:land_china_shensi` | 1 | where it started the turn |
| `unit_rank:0_source:0` | 1 | the first of the identical cavalry there |
| `unit_later_peers:0_source:militia` | 2 | after it in unit order come 2 militia |
| `unit_later_peers:0_source:mountain_infantry` | 2 | and 2 mountain infantry |
| `zone:1_path:land_china_shensi` | 1 | the path goes through Shensi |
| `zone:1_path:land_china_hopeh` | 1 | and Hopeh |
| `list_length:path` | 2 | the path has 2 zones |
| `value:mode:ordinary` | 1 | ordinary movement |
| `true:combat` | 1 | it starts a combat |

Links: it starts in Shensi (the unit's zone, role `0_source`), acts on Hopeh (the
last path zone) and its path is Shensi and Hopeh. So the network combines this
move's answers with what it knows about Shensi and Hopeh from the board part.

### Example 2: a railroad repair

**What the move means in the game** (game seed 7004): Japan repairs 1 point of
damage on the railroad between Manchuria Northern and Manchuria Western, on the
Manchuria Northern side of the border.

- Railroads sit on the borders between land zones, at most one per border. The
  starting map has one on each border with a railway, and the engine refuses to
  build one where one exists.
- Bombing a zone's railroads damages the railroad on one chosen border of that
  zone, on the bombed zone's side (rulebook 10.6.2). Each side holds its own
  damage, up to the border terrain's limit: 1 in normal terrain, 2 in desert,
  jungle, marsh, mountain or tundra (rulebook 13.2.8). A railroad with damage on
  either side cannot be used.
- The nation that holds the zone on a damaged side may repair that side, at 1 IPP
  per point. It pays in the Production Phase, and the repair is done in the Place
  Units Phase if it still holds the zone.
- The rulebook does not say who repairs a railroad or whether the limit applies
  to each side. On 3 November 2026 the user confirmed the engine's reading: one
  railroad per border, damage on each side, and each nation repairs the side it
  holds for 1 IPP per point. That confirmation spoke of 1 damage per side, the
  normal-terrain case; on difficult borders the engine allows 2 per side.

The engine calls each side of the border an `endpoint`. The move's details mean:

- `target`: the railroad;
- `endpoint`: the side being repaired;
- `damage`: how many points.

**What the network receives:**

| Question | Answer | Meaning |
| --- | ---: | --- |
| `schedule:play`, `player:axis`, `nation:japan` | 1 each | an ordinary move, the Axis player choosing for Japan |
| `kind:economy_repair` | 1 | a repair |
| `parameter:target` | 1 | it has a detail labelled `target` |
| `parameter:endpoint` | 1 | and one labelled `endpoint` |
| `parameter:other` | 1 | and one whose label, `damage`, is not on the list of known labels |
| `zone:3_other:land_manchuria_northern` | 1 | it mentions Manchuria Northern, in a way the encoder cannot classify |
| `value:target:other` | 1 | its target is a name the encoder does not recognise |
| `number:other` | 1 | a number, 1, under an unrecognised label |

**Line by line:**

- `zone:3_other:land_manchuria_northern = 1` reads "does this move mention
  Manchuria Northern, in a way the encoder can't classify? Yes." The value
  `land_manchuria_northern` is a zone, so the encoder records the zone and a role.
  The role comes from the label, `endpoint`, which is not in the role table, so
  it gets the leftover role `3_other`.
- `value:target:other = 1`: the railroad's name is not a unit, zone, facility or
  any other known thing, and no railroad name is on the list of known values. So
  it is filed as an unknown value, and which railroad the move repairs is lost.
- `number:other = 1`: every number in a move is filed under its label, so the
  amount should arrive as `number:damage = 1`. Because `damage` is not a known
  label, it is filed under `other`. The amount still arrives, under a heading that
  does not say what it is. Today only repair moves have an unknown numeric label,
  so in practice it means damage; any other would mix in.

**What this costs the network:**

- **Which railroad is lost.** Two damaged railroads that meet at Manchuria
  Northern would give two repair moves with exactly the same answers, and the
  network could not prefer one.
- **A different question for the same situation.** A city repair names its city
  under the label `target`, which is in the role table, so its zone gets
  `2_target`. Both moves mean "repair damage in this zone", but the network sees
  different questions, so what it learns about one carries over less to the
  other.
- **The zone link survives.** A move with no `0_source` zone starts from its first
  `3_other` zone, so this repair is still linked to Manchuria Northern's board
  answers. But the zone joins no probability stage: all rail repairs fall into
  the same groups, whatever their zone, until the last stage tells them apart.

If the encoder handled railroads properly, this move would describe the railroad
by its two end zones as targets, give `endpoint` the role `2_target` and say
`number:damage = 1`.

## 7. Names the encoder doesn't know

### Fixed lists and "other" questions

Names come from fixed lists: nations, unit types, facilities, technologies,
projects, decision kinds, marks, battle notes, labels and known values. A name not
on its list goes into that list's one shared "other" question, so the network sees
"some unlisted name is present" but not which one. The encoder counts every such
name, and `gwrl_cpp.zone_encoding_unknowns()` reports them, so a new name is never
dropped silently.

### A battle note the encoder misses

A real naval battle in sea zone P33 (game seed 7019): an enemy submarine moved in
from P32, and a Japanese fighter on patrol, from a light carrier, attacked it. A
Japanese destroyer was also in P33. The battle's notes, mid-way:

```text
listed   round = 1
listed   defenders = [the Japanese fighter on the light carrier]
listed   origins = {the attacker came from sea_p32}
listed   context = "movement_map"     a patrol plane meeting moving ships
listed   submarines_initiated = false
MISSING  naval_pairing_done = {setup_japan_sea_p15_destroyer_2: true}
```

- `submarines_initiated = false`: a sea battle can start while ships move through a
  zone in two ways. Either submarines already there attack the passing ships
  (`true`), or a patrol plane does, as here (`false`). A few rules change when
  submarines start the fight: they do not get their usual choice to stay
  submerged, and a submerged submarine's usual protection does not apply. It is
  on the list, so the network sees `battle_data:submarines_initiated`.
- `naval_pairing_done` is missing. A submarine that stays submerged can only be
  hit by patrol planes or by a destroyer teamed with one, so before any shooting
  the engine asked the destroyer whether to team up with the fighter. This note
  says the destroyer has answered. It reaches the network only as
  `battle_data:other` and `battle_data_unit:other:destroyer = 1`: "some unlisted
  note mentions a destroyer". All 16 missing battle notes share those same "other"
  questions.

### The 31 missing names

Found on 3 November 2026 by encoding every decision of 240 random eleven-round
games (372,935 decisions). The counts are times seen in those games.

| Group | Names (times seen) | What the network loses |
| --- | --- | --- |
| 16 battle notes, in the board part | `reaction_units` and `reaction_context` (91 each): ships that may react to an enemy fleet passing through, and the situation; `map_attack` (61): the battle is a patrol plane's attack; `naval_submarine_choices` (39): submarines' choices to stay submerged; `naval_excluded` (24): units left out of the battle; `naval_discovering_raider` (21) and `naval_raider_choices` (17): raider discovery and raiders' choices; `naval_carrier_landing_queue` (19): aircraft waiting to land on a carrier; `kind` (11): the kind of raid or movement battle; `naval_pairing_done` (10) and `naval_destroyer_pairs` (3): destroyers teaming with patrol planes; `naval_protected_submarines` (8); `air_hit_queue` (8): air hits not yet assigned; `air_pending_dead` (6): aircraft hit but not yet removed; `airborne_drop_ready` (4); `air_interception_choices` (3) | These details all look like one "other note" during naval and air battles |
| 12 railroad names, in moves | `economy_rail_8` (55), `economy_rail_69` (36), `rail_land_china_hopeh__land_china_shensi` (26), `rail_land_china_beiping__land_manchuria_rehe` (24), `rail_land_china_hunan__land_china_nanking` (20), `rail_land_china_beiping__land_china_hopeh` (18), `rail_land_china_hunan__land_china_shantung` (16), `rail_land_china_nanking__land_china_shantung` (15), `rail_land_china_hunan__land_kwangtung` (15), `rail_land_manchuria_northern__land_manchuria_western` (14), `rail_land_china_beiping__land_china_suiyuan` (10), `rail_land_manchuria_eastern__land_manchuria_western` (3) | Which railroad a repair move repairs (example 2 above) |
| The label `damage`, in moves | 691 | The repair amount arrives as an unknown number |
| A city as a repair target, in the board part | `land_china_beiping` (80): the CCP repairing bomb damage to Beiping | The encoder expects a repair's target to be a unit, facility or railroad, so it skips a city repair entirely: the network cannot see that one is under way |
| The value `local`, in moves | 1: intercepting with the fighters already in the zone rather than from a named airbase | Little: those moves still differ in other details |

These are rare, a few hundred occurrences against 372,935 decisions, but in the
decisions they touch the network misses things it should see.

### Why they were missed, and what a fix involves

The battle notes have been in the engine since 23 October; the encoder was written
on 2 November, with its lists collected from the engine code and a few short
games. Railroad names and city repairs are handled badly by design. The
automatic completeness test plays one short game, which never reaches these
situations, so only the large random check found them.

A fix would add the 16 battle notes, `damage` and `local` to their lists, describe
a railroad by its two end zones instead of its name (railroads built in play get
new names, so they cannot be listed in advance), show a city repair at its zone,
and make the test play several full games so that a future missing name fails it.

## 8. Questions removed as impossible

On 3 November 2026 the layout dropped 24,974 questions, following the user's rule:
remove a question only when the rules of the whole game rule it out, judged per
nation; a rare situation keeps its question.

| Part | Before | After |
| --- | ---: | ---: |
| Board, per zone | 59,322 | 35,407 |
| Position | 6,763 | 6,621 |
| Each move | 13,031 | 12,114 |

- **Other nations' special units.** A unit type the rulebook reserves for some
  nations belongs to them alone: Tiger I and Panzergrenadier are German, T-34 and
  Katyusha Soviet, B-29 American, Gurkha FEC; Foreign Legion and colonial
  infantry belong to the French and Commonwealth nations and Italy. No nation of
  this scenario may own one. A scenario with Germany would keep Germany's.
- **Carried units.** Only pairs the loading rules allow remain, 69 of 2,809:
  transports carry land units, a Japanese destroyer one marine, carriers fighters
  and tactical bombers (medium bombers only on heavy fleet carriers), and air
  transports and strategic bombers the cargo their rules accept.
- **Units in facilities.** Only ships and aircraft are ever inside a facility,
  and only naval facilities, which face the sea, have borders a unit can see.
- **Kept on purpose:** the coastal defense ship, reserved for nobody and
  capturable; and "warlords never own ships or planes", which lend-lease and
  recruitment might break, so it could not be proved.

Each family that lost questions keeps one `~impossible` question. A removed
combination that occurs anyway is counted there and reported as unknown, never
dropped; 240 random games met none.

## 9. Fixed facts and the layout version

Facts that never change come with the layout, not with each position:

- 39 facts per zone, such as terrain, production value, capitals, victory
  cities, original owners and home countries;
- the 160 directed borders, with 22 facts each, such as rivers, narrow crossings,
  railway connections and terrain.

The layout version, now `campaign-zone-v1-edcfe0583896a5da`, is a hash of every
question name and every fixed fact. A network refuses inputs of another layout,
and a run cannot resume across a layout change.

## 10. Why the encoder translates names

The engine came first. It was written (milestones M0 to M11) to follow the
rulebook, and many parts of the project use it: the Python interface, the tests,
saved games and replays, the map viewer, and training checkpoints, which store
the whole game as JSON. Names keep all of these readable, let the engine load its
units, map and rules from JSON files, and let a rule add a new mark or battle
note without changing a shared format. The networks came later.

The first network input, used until 2 November 2026, really did read text: it
printed each position as JSON, cut every name into word pieces and hashed the
pieces into 16,384 slots. The zone encoding replaced it with a fixed list of
questions built straight from the engine's memory: 49 to 64 times smaller and 5
to 6 times faster to build ([record](../stage_a/zone_encoding_2026_11_02.md)). It
left the engine's names as they were and translates them instead.

Reading a move's named details also lets one piece of code describe all 142
kinds of move, and kinds added later. Without it, every kind of move would need
its own encoder code, kept in step with its rule by hand.

**What names cost:**

- **Speed: little.** Encoding is about 4% of a game process's work (section 1),
  and the name lookups are only part of encoding.
- **Correctness: the real cost.** The engine and the encoder agree only through
  names. A rule can write a name the encoder's lists lack, and nothing fails: the
  name falls into an "other" question and is only counted. That is how the 31
  missing names arose.

**The alternatives:**

| Option | What it means | Assessment |
| --- | --- | --- |
| The engine writes the network's numbers itself | every rules module also fills input questions as it plays | Spreads learning code through the rules: every rule change becomes an input change, and the rules get harder to check against the rulebook. Not recommended. |
| The engine stores numbers instead of names | unit types, nations, zones and marks become numbered constants | A rewrite of every rules module, with risk to rule correctness, for at most the few percent of speed above. The measurements do not justify it. |
| Keep the names, but check them | a test scans the engine's source for the names it writes and compares them with the encoder's lists, and full random games fail on any unknown name | Closes the missing-names gap without touching the rules. Recommended; not built yet. |

A stricter form of the last option is one register of names, each declared once
with its meaning and used by both the engine and the encoder, so that the engine
cannot write an undeclared name. It is a larger change and has not been
designed.
