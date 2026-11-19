# The network's input

This page explains, layer by layer, how one decision of the game becomes the
numbers a network reads. It belongs to the [design document](README.md), whose
section 5 summarizes it and whose [glossary](README.md#12-glossary) defines its
terms. The encoder is C++ (`src/zone_encoding.cpp`);
`studies/campaign/features.py` turns its output into arrays and
`studies/campaign/neural.py` reads them. Measurements and the reasons for the
design are in the [zone encoding record](../archive/records/zone_encoding_2026_11_02.md).

## 1. When and how the input is built

Whenever the search reaches a decision it has not seen, it asks the deciding
alliance's network about it (see [search](README.md#4-choosing-an-action-search)).
Before that, the engine encodes the state once. Search copies of the same
state share that encoding, and a kept training sample stores it. The input
describes one decision: both the state of the game and the legal actions.

**The encoder reads the engine's memory directly.** It is C++ code inside the
engine. It reads the live game state and receives the legal actions as the
engine's own action objects. Nothing is written out as text or parsed on the way.

**But the engine identifies most things by name.** Only zones, nations,
unit types, facility types, technologies and the bases of marks are numbers:
each one's place in the sorted list of the names of its kind ([names held as
numbers](../engine/names.md)). For zones, nations, unit types, facility types
and technologies that number is also its index in the encoder's list of that
kind, and a construction project's type, a unit type or a facility type
number, finds its index through a list kept for each. The rest the encoder
reads as names:

- a unit's marks are a base and a whole number, such as `repairing` → 1, and
  the encoder asks about them through the engine's own mark table, which also
  says what kinds of thing each base can be on;
- a battle's notes, and a legal action's details, are small trees of named
  entries, such as `target` → `rail_land_manchuria_northern__land_manchuria_western`
  and `damage` → 1.

So the encoder translates each name into a feature number, using fixed lists of
the names it knows ([section 7](#7-names-the-encoder-doesnt-know)). That
translation is where "names" and "missing names" come from.
[Section 10](#10-why-the-encoder-translates-names) explains why the engine works
with names and what the alternatives are.

**Encoding is cheap.** In three random eleven-round games (4,786 decisions,
measured on 3 November 2026 on the M4 Max), encoding a decision took 0.17 ms on
average, against 0.64 ms to list its legal actions and 0.80 ms to apply an
action. A self-play game encodes about 60,000 states, one per network
evaluation. That is about 10 seconds of the roughly 260 CPU-seconds a game
process spent per game in the 2 November profile: about 4%, a rough estimate.

## 2. Three parts

The input for one decision is one bundle with three parts:

1. **The zone features:** each of the 37 zones (31 land and 6 sea) has values for
   the same list of 35,329 zone features.
2. **The global features:** 2,784 features about the state as a whole: the game
   round, the phase, whose turn it is, treasuries, wars and so on.
3. **The action features:** every legal action has values for the same list of
   11,046 action features about itself.

**A real decision** (game seed 5): the CCP's first Combat Movement decision of
game round 1, chosen by the Comintern player. It has 13 legal actions, and its
input holds 326 non-zero zone feature values, 59 global ones and 244 across the
13 legal actions. Each earlier decision took the action that ends the phase, or
else the first listed action.

**Each part is filed differently:**

- **Zone features are filed by zone.** Every feature value is kept with its zone,
  as (zone, feature, value), such as (Formosa, `units:japan:fighter`, 1). The zone
  is not in the feature's name: it is the row of the zone feature matrix the value
  belongs to, and all 37 zones share the same features.
- **The global features** have one set of values, as (feature, value).
- **Action features are filed by action.** Every feature value is kept with its
  action, as (action, feature, value). An action is not in one zone: it can start
  in one, pass through others and end in another. So when an action's feature is
  about a zone, the zone is written into the feature's name, such as
  `unit_zone:0_source:land_formosa`, and the action names its source zone, its
  path zones and its target zone.
  [Section 6](#the-same-fighter-in-the-zone-features-and-in-an-action) shows one
  unit in both parts.

## 3. Features and feature values

**A feature** is a numbered input slot with one fixed meaning; the code calls it
a column. Its name, such as `units:ccp:cavalry`, is a readable label for that
meaning; the network only sees the number. A name is built as
`family:part:part`. The *feature family* says what kind of fact it is, and the
parts say which nation, which unit type, which zone and so on. The zone features
have 42 families, the global features 54 and the action features 45.

**A feature value** is a whole number: a count ("how many?"), 1 for "yes", or a
number such as the game round. Almost every feature value is 0, so only the
non-zero feature values are stored.

These are all the non-zero zone feature values of the zone Shensi in that
decision:

| Feature | Feature value | Meaning |
| --- | ---: | --- |
| `possessor:ccp` | 1 | the CCP possesses Shensi |
| `turn_start_possessor:ccp` | 1 | it did at the start of the turn too |
| `units:ccp:cavalry` | 1 | one CCP cavalry here |
| `units:ccp:militia` | 2 | two CCP militia |
| `units:ccp:mountain_infantry` | 2 | two CCP mountain infantry |
| `unit_stat:comintern:cavalry:count` | 1 | one Comintern cavalry |
| `unit_stat:comintern:cavalry:move_2` | 1 | ... with 2 movement points left |
| `unit_stat:comintern:militia:count` | 2 | two Comintern militia |
| `unit_stat:comintern:militia:move_0` | 2 | ... with no movement points left |
| `unit_stat:comintern:mountain_infantry:count` | 2 | two Comintern mountain infantry |
| `unit_stat:comintern:mountain_infantry:move_1` | 2 | ... with 1 movement point left |
| `rail_to:land_china_hopeh` | 1 | a railroad runs from here to Hopeh |

The network's embedding layer keeps a learned embedding for every feature and
adds up the embeddings of the features with non-zero values, each times
$\operatorname{sign}(a)\ln(1 + |a|)$ for its feature value $a$: see
[the embedding layer](README.md#63-the-embedding-layer-embeddings-and-embedding-tables).

## 4. The zone features

The largest zone feature families:

| Feature family | Features | Asks, for one zone |
| --- | ---: | --- |
| `unit_stat` | 11,881 | how many units of an alliance and type have a condition: damaged, moved, movement points left, landed after combat, ... |
| `battle_data_unit`, `battle_data_zone` | 8,365 | what a battle's notes say about unit types and zones |
| `unit_reference_here` | 3,781 | how many units, by alliance and type, point at this zone, and why: a blitz destination, an assault target, a route, ... |
| `battle_data_word` | 3,706 | which words a battle's notes hold, such as the battle's next step or its situation |
| `unit_facility` | 1,601 | units inside a facility, by type and facility type |
| `units` | 586 | how many units of each nation and type are here |
| `carried` | 277 | carried units, by carrier type and cargo type |
| `unit_flag` | 205 | how many units of an alliance and class carry each of the other unit marks, such as "repairing" |
| `facility_flag` | 177 | marks on a facility here |
| `possessor`, `capital_of` | 27 | who holds the zone, whose capital it is |
| `rail_to`, `rail_damage_toward`, `rail_repair_toward` | 106 | railroads to each neighbour, the damage on this side, and repairs under way |

**Units are counted, not named.** The engine gives every unit a unique name.
Units on the board from the start are named like `setup_japan_sea_p15_destroyer_2`:
on the board from the start, owned by Japan, started in sea zone P15, a
destroyer, the second of its kind there. Things created during play get counter
names, such as `economy_unit_112` for a unit bought during the game. Railroads
are the exception: a border holds at most one, so each is named by the two zones
it joins, such as `rail_land_china_hopeh__land_china_shensi`, whether it was on
the map from the start or built during play
([RCL-019](../../game_content/rules/clarifications.md#rcl-019-one-railroad-per-border-damaged-and-repaired-by-side)).
The network never reads these names. It sees counts and conditions, such as "one
Japanese destroyer here, undamaged, already moved".

**Battle notes.** While a battle is being fought, the engine keeps notes on it:
the combat round, the defenders, where the attackers came from, the battle's next
step and so on. They become the `battle_data` families: a note's units are
counted by type, its zones by zone, its words, such as `movement_map` or
`attacker_wins`, by word, and its numbers are added up.
[Section 7](#a-battle-note-word-by-word) shows a real example.

**Turn numbers become ages.** A mark that stores the turn when something happened
is turned into "turns since", so equal situations in different turns look alike.

## 5. The global features

The global features include `round` (the game round), `rounds_left`,
`phase:<phase>`, `turn_nation:<nation>`, `treasury:<nation>`,
`income:<nation>:<part>`, `at_war:<nation>:<nation>`,
`technology_stage:<nation>:<technology>`, the kind of decision being taken
(`decision:<kind>`) and the purpose of a pending dice roll. In the seed-5 decision
their values include:

| Feature | Feature value | Meaning |
| --- | ---: | --- |
| `round` | 1 | the game round |
| `rounds_left` | 11 | game rounds still to play |
| `phase:combat_movement` | 1 | the Combat Movement phase |
| `turn_nation:ccp` | 1 | the CCP's turn |
| `treasury:japan` | 15 | Japan's money: 15 IPP, the game's unit of money |
| `income:japan:territorial` | 15 | the income Japan's land gives it each turn |
| `alliance:warlord_tibet:~none` | 1 | the warlord of Tibet has joined no side yet |

A feature about a nation exists only where the rules can ever give it a non-zero
value: there is no `treasury:mongolia`, because Mongolia keeps no treasury. Nor
is there one whose value can never change: Japan is a major power in every
state, so there is no `power_status:japan:major`
([section 8](#what-the-global-features-ask-about-a-nation)).

An income feature's value is the nation's income as the state stands, not what it
last collected. The engine brings it up to date at the end of every action, so
land taken in a battle counts at the next decision
([economy](../engine/economy.md#1-money)).

## 6. The action features

### Every legal action has the same features

Every legal action has values for the same fixed list of 11,046 action features.
So every legal action is a feature vector of the same length, a row of the
action feature matrix, almost all zeros, and only its non-zero feature values are
stored. An action has non-zero values only for the features that apply to it: the
fighter attacking Hunan has 17, the airbase purchase 10.

**A toy version.** Suppose the game had two unit types, infantry and tank, and
three zones, a, b and c. Part of an action's feature vector would be these eight
features:

![Two toy actions as feature vectors of the same features: the infantry moving a to b to c has the value 1 for unit:0_source:infantry, unit_zone:0_source:a and zone:1_path a, b and c, and 3 for list_length:path, and its source zone is a and its target zone c; the tank moving b to c has 1 for unit:0_source:tank, unit_zone:0_source:b and zone:1_path b and c, and 2 for list_length:path, with source zone b and target zone c.](figures/action_feature_vectors.svg)

The real features work the same way, with three differences from a plain
"which unit, which zones" feature vector:

- **Zones come with roles.** There is one feature per zone and role, not one
  per zone. A feature vector with just "infantry, a, c" could not tell "a to c"
  from "c to a". Here `unit_zone` says where the unit stands, so where the action
  starts, and the target zone says which zone it acts on. Between the start and
  the end, the path's zones are marked as a set, not in order.
- **Units are described, not numbered.** A feature says "an infantry", with
  its condition (movement points left, damage, ...) and its rank among identical
  units there, never "unit 1".
- **An action's feature vector says more than units and zones:** the kind of
  action (a movement, an air attack, a purchase, ...), who chooses, which labels
  the action has, and its plain values, such as `true:combat = 1` or
  `number:range = 2`. Feature values can be counts, not only 0 or 1.

### How the engine writes an action

A legal action is a kind plus labelled details. Each detail has a label on the
left and a value on the right. The engine's rule code chose the labels:

| Label | Value |
| --- | --- |
| `kind` | `economy_repair` |
| `target` | `rail_land_manchuria_northern__land_manchuria_western` |
| `endpoint` | `land_manchuria_northern` |
| `damage` | `1` |

### How each detail becomes feature values

Every action first says who chooses and what kind of action it is, for example
`schedule:play = 1`, `player:axis = 1`, `nation:japan = 1` and
`kind:air_start_patrol = 1`. Then, for each detail, the encoder records that a
detail with this label exists, such as `parameter:range = 1`, and then the
detail's value. How it records the value depends on what the value is.

All the examples below are details of real legal actions from random games: seed
7001, except the railroad repair (seed 7004).

**Plain values:**

| Value | Real example | Feature values |
| --- | --- | --- |
| A number | A Japanese seaplane in Okinawa starts a patrol over sea zone P33: `range = 2` | `number:range = 2` |
| True | A Japanese infantry moves from Rehe into Beiping to attack: `combat = true` | `true:combat = 1` |
| False | A Japanese transport enters Formosa's port without unloading: `unload = false` | `false:unload = 1` |
| Nothing | A Japanese heavy cruiser moves from sea zone P16 to P15, starting and ending at sea, not in a port: `origin_facility = null`, `destination_facility = null` | `null:origin_facility = 1`, `null:destination_facility = 1` |
| A list | A Japanese fighter flies from Formosa over P32 to attack Hunan: `path = [land_formosa, sea_p32, land_china_hunan]` | `list_length:path = 3`, then each item as its own value: `zone:1_path:land_formosa = 1`, `zone:1_path:sea_p32 = 1`, `zone:1_path:land_china_hunan = 1` |
| A group of details | The cruiser's movement keeps its details in one group: `request = {combat = true, strategic = false, path = [sea_p16, sea_p15], units = [setup_japan_sea_p16_heavy_cruiser_1], ...}` | `parameter:request = 1`, then each inner detail as if it stood alone: `true:combat = 1`, `false:strategic = 1`, `list_length:path = 2`, `zone:1_path:sea_p16 = 1`, ..., `unit:0_source:japan:heavy_cruiser = 1`, ... |

**Names of things.** A name is replaced by what the thing is; the name itself
never reaches the network.

| Value | Real example | Feature values |
| --- | --- | --- |
| A unit's name | The fighter attacking Hunan: `unit = setup_japan_land_formosa_fighter_1` | `unit:0_source:japan:fighter = 1` (a Japanese fighter), `unit_stat:0_source:count = 1`, `unit_stat:0_source:move_4 = 1` (4 movement points left), `unit_zone:0_source:land_formosa = 1` (it is in Formosa), `unit_turn_origin:0_source:land_formosa = 1` (it started the turn there), `unit_rank:0_source:0 = 1` (the first Japanese fighter there), `unit_later_peers:0_source:militia = 1` (one militia comes after it in unit order) |
| A zone's name | Japan buys an airbase to build in Formosa: `zone = land_formosa` | `zone:2_target:land_formosa = 1` |
| A facility's name | The transport entering port: `facility = facility_land_formosa_major_port` | `facility:0_source:major_port = 1` |
| A battle's name | The CCP starts its battle in Hopeh: `battle = land_battle_2` | `battle_stage:0_source:awaiting_combat_rules = 1`, `battle_attacker:0_source:ccp = 1`, `battle_defender:0_source:warlord_beiping_hopeh = 1`, `battle_units:0_source:cavalry = 1`, `battle_units:0_source:militia = 1`, `battle_place:0_source:land_china_shensi = 2` (the battle's notes name Shensi twice) |
| A construction project's name | Japan pays the next instalment on a fleet carrier it is building: `project = japan_queue_fleet_carrier` | `project:0_source:fleet_carrier = 1`, `project_owner:0_source:japan = 1`, `project_stat:0_source:paid_ipp = 5` (5 IPP paid), `project_stat:0_source:payments_left = 2`, `project_stat:0_source:remaining_payments = 10` (two payments, 10 IPP, to go), `project_stat:0_source:queue_position = 3`, `project_stat:0_source:count = 1` |
| A railroad's name | Japan repairs the railroad between Manchuria Northern and Manchuria Western ([example 2](#example-2-a-railroad-repair)): `target = rail_land_manchuria_northern__land_manchuria_western` | `rail_endpoint:2_target:land_manchuria_northern = 1` and `rail_endpoint:2_target:land_manchuria_western = 1` (its two endpoints, the zones it joins), `rail_damage:2_target:land_manchuria_northern = 1` (1 damage on the Manchuria Northern side) |
| A build-chart row | The airbase purchase: `row = japan_major_airbase` | `row:japan_major_airbase = 1` |
| A nation's name | The KMT declares war on Japan: `target = japan` | `nation_named:2_target:japan = 1` |
| A technology | Japan starts research at its Tokyo factory: `technology = advanced_artillery` | `technology:advanced_artillery = 1` |
| Any other name, on the list of known values | The airbase purchase, at the printed price: `price = printed` | `value:price:printed = 1` |
| Any other name, not on the list | None occurs in 480 random games since 4 November. A name a rule adds later would be counted and reported ([section 7](#keeping-the-lists-complete)) | `value:<label>:other = 1` |

The `0_source`, `1_path` and `2_target` parts of these names are roles, explained
below.

### The same fighter in the zone features and in an action

Zone features are filed by zone, but action features by action. The fighter
attacking Hunan shows the difference. This is decision 41 of game seed 7001:
Japan's Combat Movement in game round 1, with 106 legal actions.

**In the zone features**, Formosa's feature vector lists everything in Formosa,
counted by nation, alliance and type. These are all 9 of its non-zero feature
values:

| Feature | Feature value | Meaning |
| --- | ---: | --- |
| `possessor:japan` | 1 | Japan holds Formosa |
| `turn_start_possessor:japan` | 1 | and held it when the turn began |
| `units:japan:fighter` | 1 | one Japanese fighter |
| `units:japan:militia` | 1 | one Japanese militia |
| `unit_stat:axis:fighter:count` | 1 | one Axis fighter |
| `unit_stat:axis:fighter:move_4` | 1 | the fighter has 4 movement points left |
| `unit_stat:axis:militia:count` | 1 | one Axis militia |
| `unit_stat:axis:militia:move_0` | 1 | the militia has none |
| `facility:major_port:count` | 1 | a major port |

Hunan's feature vector says that the KMT holds it with two infantry, and P32's
lists a Japanese destroyer, light cruiser and transport.

**In the action**, the feature values describe the one unit the action uses and
its route. The zones appear inside the names, because one action involves several
zones:

| Feature | Feature value | Meaning |
| --- | ---: | --- |
| `unit:0_source:japan:fighter` | 1 | the unit that acts is a Japanese fighter |
| `unit_stat:0_source:count` | 1 | one unit |
| `unit_stat:0_source:move_4` | 1 | with 4 movement points left |
| `unit_zone:0_source:land_formosa` | 1 | standing in Formosa |
| `unit_turn_origin:0_source:land_formosa` | 1 | where it started the turn |
| `unit_rank:0_source:0` | 1 | the first Japanese fighter there |
| `unit_later_peers:0_source:militia` | 1 | a militia comes after it in unit order |
| `zone:1_path:land_formosa` | 1 | the route: Formosa, |
| `zone:1_path:sea_p32` | 1 | sea zone P32, |
| `zone:1_path:land_china_hunan` | 1 | Hunan |
| `list_length:path` | 3 | the route has 3 zones |

Plus the feature values every action has: `schedule:play`, `player:axis`,
`nation:japan`, `kind:air_ground_attack`, `parameter:unit` and `parameter:path`.

**The action's zones join the two.** The action's source zone is Formosa, its
target zone Hunan and its path zones Formosa, P32 and Hunan, so the network reads
those zones' vectors with the action's own feature values. Together they say:
this fighter, with 4 movement points left, flies from Japanese Formosa, which also
holds a militia and a major port, over P32 to attack Hunan, held by two KMT
infantry.

Actions are not filed under zones for three reasons:

- one action involves several zones;
- many actions share a zone: of these 106 legal actions, 58 start in sea zone
  P15, 18 in Tokyo and 7 in Formosa, and filed under their zones they would blur
  together;
- the network must score each action separately, so each action needs its own
  feature values.

### Roles

**Reading an action feature's name.** Most action features have three parts:

![The three parts of unit_stat:0_source:move_4: unit_stat is the feature family, what kind of fact (a named unit's condition); 0_source is the role, through which detail the action names the unit (a source detail); move_4 is which fact (4 movement points left).](figures/feature_name.svg)

- **The feature family** says what kind of fact it is: `unit` is a named unit's
  nation and type, `unit_stat` its condition, `unit_zone` where it stands, `zone`
  a named zone, and so on.
- **The role** says through which detail the action names that unit or zone. It
  comes from that detail's label, and every feature written about the detail's
  value carries it.
- **The rest** says which fact: `count` is how many units, `move_4` "4 movement
  points left".

So `unit_stat:0_source:count = 1` reads: "the unit named by a source detail is
one unit". In the fighter's attack above, that detail is `unit = ...`, and its
label `unit` is a source label. `unit_stat` is not a label; it is the feature
family.

**The four roles** say how the action relates to the unit or zone a detail names:

- `0_source`: what acts, or where the action starts;
- `1_path`: the route the action travels;
- `2_target`: what the action acts on, or where it goes;
- `3_other`: the action mentions it, but the encoder cannot say how.

**One action, two units, two roles.** A Japanese tactical bomber lands on a light
carrier (game seed 7004):

| Kind | Label | Value |
| --- | --- | --- |
| `air_land_noncombat` | `unit` | `japan_tactical_bomber_p15_fleet_carrier_1` |
| | `destination` | `japan_light_carrier_p15_setup_1` |

Both details name a unit, so both produce the same feature families, each with
its own detail's role:

| Detail | Label and role | Some of its feature values |
| --- | --- | --- |
| `unit = japan_tactical_bomber_p15_fleet_carrier_1` | `unit`: `0_source` | `unit:0_source:japan:tactical_bomber = 1`, `unit_stat:0_source:count = 1`, `unit_stat:0_source:move_4 = 1`, `unit_stat:0_source:aboard = 1`, `unit_zone:0_source:sea_p41 = 1` |
| `destination = japan_light_carrier_p15_setup_1` | `destination`: `2_target` | `unit:2_target:japan:light_carrier = 1`, `unit_stat:2_target:count = 1`, `unit_stat:2_target:move_3 = 1`, `unit_zone:2_target:sea_p14 = 1` |

Without roles, the bomber's and the carrier's facts would land in the same
features, and the network could not tell which unit has 4 movement points left or
which one is in P41.

**How the role is chosen.** The encoder cannot understand what a label means: to
it, `endpoint` is just a string of letters. So the role comes from a fixed table
in `src/zone_encoding.cpp` that pairs labels with roles. The table lists labels,
the words on the left of an action's details, not feature families:

| Label | Role |
| --- | --- |
| artillery, battle, facility, factory, origin_facility, plan, project, row, source, transport, unit, units | `0_source` |
| path | `1_path` |
| beneficiary, border, border2, declaring_nation, destination, destination_facility, endpoint, neighbor, recipient, sea, target, technology, zone, zones | `2_target` |
| any label not in the table | `3_other` |

Some labels that name units are missing from the table. When a Japanese air
transport loads a mountain infantry (`air_load`, game seed 7006), the infantry is
named by `cargo = setup_japan_land_manchuria_northern_mountain_infantry_1`.
`cargo` is not in the table, so the infantry's feature values read
`unit:3_other:japan:mountain_infantry = 1`, `unit_stat:3_other:count = 1` and so
on. `towed` (a unit towed along a movement) is another such label.

**A route's last zone is a path zone.** The fighter attacking Hunan has no
detail labelled `target`. The engine writes its whole route as one detail,
`path = [land_formosa, sea_p32, land_china_hunan]`, and the attacked zone is
simply the route's last zone. Roles come from labels, one per detail, so all
three zones get the role of `path`: `zone:1_path:land_china_hunan = 1`, the
same kind of feature as for Formosa and P32. Movement actions that attack, such
as the cavalry in [example 1](#example-1-a-cavalry-attack), are written the same
way.

The network still learns where such an action ends in two ways:

- **The target zone.** For an action with a path, the target zone is the path's
  last zone. So the network reads Hunan's zone vector in the target-zone slot,
  just as it reads a `2_target` zone for an action without a path.
- **The kind.** `kind:air_ground_attack = 1`, or `true:combat = 1` for a
  movement action, says that the action is an attack.

What is lost is narrower: among the action's own feature values, "passes through
Hunan" and "ends in Hunan" look the same, and the "what it acts on" level of the
hierarchical softmax has nothing for such actions; their destinations separate
them only at the "how it travels" level, which lists the path zones in order.
Also writing the last path zone as a `2_target` zone would make the destination
explicit there. That is an untested idea, not a known fault.

The role changes three things:

1. **The feature.** `zone:2_target:land_china_beiping` and
   `zone:3_other:land_china_beiping` are different features with different
   learned embeddings.
2. **The action's zones.** The network reads three zones' vectors with each
   action: its source zone (the first `0_source` zone, or else the first
   `3_other` zone), its target zone (the last path zone, or else the first
   `2_target` zone) and the average of its path zones.
3. **The levels of the hierarchical softmax.** "What acts" is built from the
   `0_source` details, "how it travels" from the `1_path` details and path zones,
   and "what it acts on" from the `2_target` details. `3_other` details belong to
   no level.

The encoder keeps two separate lists of labels. The list of known labels (93 of
them) decides features like `parameter:cargo`. The role table (27 labels)
decides roles. A label can be on the first and missing from the second, as
`cargo` is.

### Example 1: a cavalry attack

The CCP cavalry in Shensi attacks Hopeh. In the engine's form:

| Kind | Label | Value |
| --- | --- | --- |
| `movement_route` | `unit` | `setup_ccp_land_china_shensi_cavalry_1` |
| | `path` | `[land_china_shensi, land_china_hopeh]` |
| | `combat` | `true` |
| | `mode` | `ordinary` |

It becomes 21 non-zero feature values:

| Feature | Feature value | Meaning |
| --- | ---: | --- |
| `schedule:play` | 1 | an ordinary action in play |
| `player:comintern` | 1 | the Comintern player chooses |
| `kind:movement_route` | 1 | a movement |
| `nation:ccp` | 1 | for the CCP |
| `parameter:unit`, `parameter:path`, `parameter:combat`, `parameter:mode` | 1 each | it has these four details |
| `unit:0_source:ccp:cavalry` | 1 | the unit that acts is a CCP cavalry |
| `unit_stat:0_source:count` | 1 | one unit |
| `unit_stat:0_source:move_2` | 1 | with 2 movement points left |
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

The action's zones: its source zone is Shensi (the unit's zone, role
`0_source`), its target zone Hopeh (the last path zone) and its path zones
Shensi and Hopeh. So the network combines this action's feature values with what
it knows about Shensi and Hopeh from the zone features.

### Example 2: a railroad repair

**What the action means in the game** (game seed 7004): Japan repairs 1 point of
damage on the railroad between Manchuria Northern and Manchuria Western, on the
Manchuria Northern side of the border.

- Railroads sit on the borders between land zones, at most one per border. The
  starting map has one on each border with a railway. Building one is not
  offered where one stands, damaged or not, or is being built.
- Bombing a zone's railroads damages the railroad on one chosen border of that
  zone, on the bombed zone's side (rulebook 10.6.2). Each side holds its own
  damage, up to the border terrain's limit: 1 in normal terrain, 2 in desert,
  jungle, marsh, mountain or tundra (rulebook 13.2.8). A railroad with damage on
  either side cannot be used.
- The nation that holds the zone on a damaged side may repair that side, at 1 IPP
  per point. It pays in the Production Phase, and the repair is done in the Place
  Units Phase if it still holds the zone.
- The rulebook leaves some of this open. The user settled it on 3 and 4 November
  2026, as rule
  [RCL-019](../../game_content/rules/clarifications.md#rcl-019-one-railroad-per-border-damaged-and-repaired-by-side):
  one railroad per border, because a second would give nothing that a repair
  does not, and damage and repair by side, each side's limit set by the border's
  terrain.

Because a border holds one railroad, a railroad is named by the two zones it
joins, in alphabetical order:
`rail_land_manchuria_northern__land_manchuria_western`. The engine calls each
side of the border an `endpoint`, and the features about a railroad's two zones
are named after it. The action's details mean:

- `target`: the railroad;
- `endpoint`: the side being repaired;
- `damage`: how many points.

**What the network receives:**

| Feature | Feature value | Meaning |
| --- | ---: | --- |
| `schedule:play`, `player:axis`, `nation:japan` | 1 each | an ordinary action, the Axis player choosing for Japan |
| `kind:economy_repair` | 1 | a repair |
| `parameter:damage`, `parameter:endpoint`, `parameter:target` | 1 each | it has these three details |
| `zone:2_target:land_manchuria_northern` | 1 | it acts on Manchuria Northern, the side being repaired |
| `rail_endpoint:2_target:land_manchuria_northern` | 1 | the railroad it acts on has one endpoint in Manchuria Northern ... |
| `rail_endpoint:2_target:land_manchuria_western` | 1 | ... and the other in Manchuria Western |
| `rail_damage:2_target:land_manchuria_northern` | 1 | that railroad has 1 damage on the Manchuria Northern side; the other side has none, so its feature value is 0 |
| `number:damage` | 1 | it repairs 1 point |

**Detail by detail:**

- `endpoint = land_manchuria_northern` is a zone, and `endpoint` is a `2_target`
  label, so it becomes `zone:2_target:land_manchuria_northern`.
- `target = rail_land_...` names a railroad. The encoder looks the railroad up
  in the game state and writes its two endpoints (`rail_endpoint`) and the
  damage on each side (`rail_damage`), with the role of `target`, `2_target`.
  The name itself never reaches the network, so a railroad built during play is
  described the same way as one on the starting map.
- `damage = 1` is a number under a known label: `number:damage = 1`.

**Zones and levels.** The encoder reads an action's details in alphabetical order
of their labels, so `endpoint` comes before `target`, and the first `2_target`
zone is the side being repaired. So the action's target zone is Manchuria
Northern, and the network reads that zone's vector with it, built from zone
feature values that include `rail_damage_toward:land_manchuria_western = 1`. All
its zones are `2_target`, so repairs of different railroads, or of different
sides, fall into different "what it acts on" groups. Repairs of the same side that
differ only in how many points they mend are told apart at the last level.

**In the zone features.** Once bought, the repair is under way until the Place
Units Phase. Manchuria Northern's zone feature values then also include
`repair:japan:rail:count = 1`, `repair:japan:rail:remaining_damage = 1` and
`rail_repair_toward:land_manchuria_western = 1`: Japan is repairing 1 point on
its side of the railroad toward Manchuria Western.

Until 4 November 2026 this action reached the network as `value:target:other`,
with the zone's role unknown and the amount as an unknown number, so which
railroad it repaired was lost
([record](../archive/records/rail_repair_encoding_2026_11_04.md)).

## 7. Names the encoder doesn't know

### Fixed lists and "other" features

Names come from fixed lists: nations, unit types, facilities, technologies,
projects, decision kinds, battle notes, the words battle notes use, labels and
known values. A name not on its list goes into that list's one shared "other"
feature, so the network sees "some unlisted name is present" but not which one.
The encoder counts every such name, and `gwrl_cpp.zone_encoding_unknowns()`
reports them. Marks need no such list: the encoder takes them from the engine's
mark table, which holds every mark the code can name
([names held as numbers](../engine/names.md#what-a-mark-is)).

In a battle note, the encoder first tries a name as a unit, zone, facility,
construction project or railroad. A name ending in a number that is none of
these belongs to something no longer in the game, such as a unit lost earlier
this turn, and is skipped; words never contain digits. Any other name is a word.
Only some notes hold words, such as `context`, `result` or `rolling_phase`; a
word in another note goes to an "other" feature and is reported, like an unlisted
word.

### A battle note, word by word

A real naval battle in sea zone P33 (game seed 7019): an enemy submarine moved in
from P32, and a Japanese fighter on patrol, from a light carrier, attacked it. A
Japanese destroyer was also in P33. Some of the battle's notes, mid-way, and the
feature values they give in P33's feature vector:

| Note | Its feature values in P33's feature vector |
| --- | --- |
| `round = 1` | `battle_data:round = 2` |
| `defenders = [the Japanese fighter]` | `battle_data_unit:defenders:fighter = 1` |
| `origins = {the submarine: sea_p32}` | `battle_data_unit:origins:submarine = 1`, `battle_data_zone:origins:sea_p32 = 1` |
| `context = "movement_map"` | `battle_data_word:context:movement_map = 1` |
| `submarines_initiated = false` | `battle_data:submarines_initiated = 1` |
| `naval_pairing_done = {the destroyer: true}` | `battle_data:naval_pairing_done = 2`, `battle_data_unit:naval_pairing_done:destroyer = 1` |

- Every note gives `battle_data:<note> = 1` for being there, and its numbers
  and true values are added in: `round = 1`, the battle's combat round, gives 2;
  `false` adds nothing.
- `context = "movement_map"`: the battle is a patrol plane meeting moving ships.
- `submarines_initiated = false`: a sea battle can start while ships move through
  a zone in two ways. Either submarines already there attack the passing ships
  (`true`), or a patrol plane does, as here (`false`). A few rules change when
  submarines start the fight: they do not get their usual choice to stay
  submerged, and a submerged submarine's usual protection does not apply.
- `naval_pairing_done`: a submarine that stays submerged can only be hit by
  patrol planes or by a destroyer teamed with one, so before any shooting the
  engine asked the destroyer whether to team up with the fighter. This note says
  the destroyer has answered.

Until 4 November 2026 `naval_pairing_done` was missing from the list of notes and
arrived only as `battle_data:other`, and the word `movement_map` was dropped
without being counted.

### Keeping the lists complete

Encoding every decision of 240 random eleven-round games (seeds 7000 to 7239,
313,496 decisions) meets no unlisted name, and neither do 240 more (seeds 9000
to 9239, 314,594 decisions), measured on 5 November 2026. One of the latter,
seed 9239, reaches a feature removed as impossible (section 8): an air
transport carrying motorized infantry. The rules forbid that cargo, and the
engine made it by upgrading an infantry already aboard
([record](../archive/records/zone_name_check_early_end_2026_11_05.md)). Since
[RCL-021](../../game_content/rules/clarifications.md#rcl-021-upgrading-a-unit-aboard-a-transport)
the engine no longer offers that upgrade.

Before 4 November the lists lacked names in four groups. On 3 November the random
check found 31: 16 battle notes, 12 railroad names, the label `damage`, a city as
a repair target and the value `local`. Two prices that come with Improved
Construction turned up on 4 November. The engine's source named 20 more battle
notes that random games had not reached, such as those of a fleet slipping out
of a damaged port. And the words in battle notes were dropped without being
counted, so no check could see them. The
[record](../archive/records/zone_names_2026_11_04.md) lists them all. The lists had been
collected from the engine code and a few short games when the encoder was
written on 2 November.

Three checks keep the lists complete:

- **The engine's source.** Tests read the rule code for the usual ways it writes
  battle notes, the words in battle notes and actions, battle stages and prices,
  and fail on a name without a feature (`tests/test_campaign_zone_encoding.py`).
  For marks they check the mark table against `tools/mark_writes.py`, which
  finds every place the rule code gives a mark a value and the kind of thing it
  lands on (section 8).
- **Whole games.** The encoding test plays two whole random games and fails on
  any unlisted name.
- **Many games.** `tools/check_zone_names.py` plays hundreds of random games,
  240 in about 105 seconds on 8 workers. Run it before a long self-play run.

The random games choose uniformly random actions, but now and then end the phase
instead, so some phases do little and others much.

A name written another way, and met in no random game, can still slip into an
"other" feature, but it is counted and reported, never dropped.

Some details are summarized on purpose rather than named:

- a mark's argument, unless it is a place or a nation: which railroad or
  facility was damaged this turn, for example, is counted for the whole state;
- the numbers and true values in a battle note are added into one feature value;
- the field names inside a note, and things no longer in the game.

## 8. Features removed as impossible

On 3 November 2026 the layout dropped 24,974 features, following the user's rule:
remove a feature only when the rules of the whole game rule it out, judged per
nation; a rare situation keeps its feature.

| Part | Before | After (3 November) |
| --- | ---: | ---: |
| Zone features, per zone | 59,322 | 35,407 |
| Global features | 6,763 | 6,621 |
| Action features, per legal action | 13,031 | 12,114 |

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
- **Railroads at sea.** Railroads join land zones only, so the railroad features
  added on 4 November (`rail_repair_toward`, `rail_endpoint`, `rail_damage`) have
  no sea-zone versions.
- **Names no code writes.** The lists hold only names the engine's code can
  write. Ten names left over from a removed benchmark, two kinds of action and
  eight marks, came off them on 14 November 2026, and 364 features with them.
- **Incomes no nation can have.** Only Japan, the KMT and the CCP keep an income
  account, and only Japan has the bonus for the Chinese land it holds
  (`incomePartPossible` in `src/economy.cpp`). Four income features remain; the
  35 for other nations and parts went on 14 November 2026.
- **A feature with one possible value.** Thirteen features said whether a
  nation's income had been worked out. In a started game it always has been, so
  each only repeated that its nation is in the game (`nation_present`), and
  they went the same day. The encoder reports a state where an income has
  not been worked out. Thirteen more said whether a nation keeps a treasury,
  which never changes during a game. They went with the features
  [listed below](#what-the-global-features-ask-about-a-nation), and the encoder
  reports a treasury that is missing.
- **Marks on things they are never on.** The engine's mark table says which
  kinds of thing the rules put each mark on: a unit, a nation, a territory, a
  facility, a construction project, a battle or the game as a whole
  ([names held as numbers](../engine/names.md#what-a-mark-is)). Each family of
  marks asks about a mark only on its own kind: `nation_flag` asks a nation
  about the 48 marks a nation gets, but for its research rounds, which are
  `researched_round`, and not about a unit's `air_battle`; and
  `state_flag` asks about the 9 marks of the game as a whole that are not
  counters or features of their own. Until 18 November 2026 the input kept
  two shared lists, one for units and nations and one for everything else, and
  asked every kind about every mark of its list: 8,902 features, of which 290
  ever had a value in 480 random games
  ([record](../archive/records/answer_census_2026_11_15.md#which-questions-were-answered)).
  1,680 remain. The four marks a nation gets when Improved Construction spares
  one of its factories or cities from bombing (rulebook 8.2.1, page 46;
  `applyFacilityBombDamage` and `applyCityBombDamage` in `src/air.cpp`), which
  neither list had, have their features. Twelve marks are on nothing: the test
  rules' `fixture`, and eleven that some rule reads but none sets, such as
  `escort`. The same change took eight of these eleven out of `unit_stat`, in
  the zone and the action features, and three nation marks no unit carries, and
  an "other" column nothing wrote, out of `unit_reference_here` and
  `unit_reference_place`. And `unit_flag` now asks only about the three unit
  classes a unit type has, not about an "other" class.
- **Facts that never change.** A feature with one possible value tells no two
  states apart. Every nation but Dadao is in every game (`alwaysInGame` in
  `src/politics.cpp`); Japan, the KMT, the CCP and Mongolia each have one
  possible alliance and one possible controller, and Japan, Mongolia and the
  warlords one possible power status; the KMT and the CCP are always at war
  (`alwaysAtWar`); and the campaign has always started. Their 33 features went
  on 18 November 2026, with the 38 `player` features: a nation's player is the
  agent of its alliance, so each repeated an `alliance` feature. The encoder
  reports a state that breaks one of these facts (`encodeNations` in
  `src/zone_encoding.cpp`).
- **Kept on purpose:** the coastal defense ship, reserved for nobody and
  capturable; and "warlords never own ships or planes", which lend-lease and
  recruitment might break, so it could not be proved.

Each feature family that lost features keeps one `~impossible` feature. A removed
combination that occurs anyway is counted there and reported as unknown, never
dropped. Of 480 random games on 5 November, one met such a combination: an air
transport carrying motorized infantry, which the rules forbid too and the engine
no longer makes ([keeping the lists complete](#keeping-the-lists-complete)).

### What the global features ask about a nation

The global features ask about a nation only what the rules can ever make of it.
Each rule is a short function in the engine's politics or economy module
(`src/politics.cpp`, `src/economy.cpp`), with its reason beside it, and the
layout keeps the features the rule allows, unless it allows only one. On 14
November 2026 this took the global features from 6,477 to 2,784, and on 18
November 2026 the facts that never change and the marks a nation is never given
took them to 2,784.

| Features | Kept for | Why no other value can happen |
| --- | --- | --- |
| `treasury` | Japan, the KMT and the CCP | The scenario opens an account for these three. No rule opens or closes one later: a lost capital or a surrender only empties it. |
| `technology_stage`, `researched_round` | Japan, the KMT and the CCP, each with the 16 technologies | Only a major power researches. Japan is one from the start, and only the KMT and the CCP are promoted to one. |
| `nation_present` | Dadao | Setup creates every other nation, and no code removes one. Dadao is created when Japan first wins over a warlord. |
| `power_status` | the KMT and the CCP as minor or major; Dadao as minor | Setup gives every nation its status. The only later change is the promotion of the KMT or the CCP. So Japan is always a major power, Mongolia a minor one and each warlord a warlord, and they are not asked. |
| `alliance` | Dadao in the Axis; each warlord in any of the three or in none | Only incorporation changes an alliance. Only warlords are incorporated, and Dadao, which joins Japan and so stays in the Axis. So Japan, the KMT, the CCP and Mongolia keep the alliance setup gives them and are not asked. No nation is asked its player: the player is its alliance's agent. |
| `controller` | Dadao under Japan or nobody; each warlord under nobody, the KMT, the CCP, Dadao or Japan | A warlord comes under the nation that incorporates it. Dadao is created under Japan and is left under nobody if Japan surrenders. Nothing else changes a controller, so Japan, the KMT and the CCP, under themselves, and Mongolia, under nobody, are not asked. |
| `turn_nation`, `completed_turns` | the CCP, Mongolia, Japan and the KMT | The turn passes only along the scenario's turn order. |
| `surrendered` | Japan and the KMT | The KMT surrenders when it holds no land, Japan when an enemy holds Tokyo at the end of Japan's turn. The CCP never surrenders, and no rule makes any other nation surrender. |
| `evolution_awarded`, `state_flag_nation` | the KMT and the CCP | Only they evolve into major powers and then choose a capital. The mark that the choice is pending is the only game-wide mark that names a nation. |
| `china_invader` | Japan and Mongolia | The invader is recorded only when the attacker is not Chinese. |
| `attacked_warlord` | each warlord, attacked by the CCP, Japan, Dadao or Mongolia | A warlord never attacks. One the KMT attacks joins the CCP at once and is not recorded. |
| `alignment_queue` | the warlords | Only warlords wait to be aligned at the end of the Combat Phase. |
| `allied` | the KMT with the CCP | Nations are allies under the Chinese Truce, or as two major powers of one alliance. The only possible major powers, Japan, the KMT and the CCP, are in three different alliances. |
| `at_war` | every pair except a nation with itself, two warlords, Japan with Dadao, and the KMT with the CCP | One side of every war is Japan, the KMT, the CCP, Dadao or Mongolia: only they declare war, invade China or take over the wars of a nation they incorporate. Japan and Dadao are both in the Axis for good. The KMT and the CCP start at war, and only incorporation ends a war, so they are not asked. |

A rare value keeps its feature. Mongolia cannot declare war, so it is the
invader only when it attacks land that was Chinese at the start and is now held
by a nation already at war with it, or by nobody. A warlord comes under Japan
only if Japan wins it over after Dadao has joined Japan. Both have their
features.

`tests/zone_encoding_tests.cpp` checks which of these features exist, that the
allowed rare values are read, that a ruled-out value is counted in its
feature family's `~impossible` feature and reported, and that a state breaking
a fact that never changes is reported.

**Not judged nation by nation.** Three feature families that name nations have
not been judged nation by nation, because many rules write their values:
`pending_nation`, `chance_nation` and `unsited_project`.

## 9. Static features and the layout version

Facts that never change come with the layout, not with each state, as *static
features*:

- 39 static features per zone, such as terrain, production value, capitals,
  victory cities, original owners and home countries;
- the 160 directed borders, with 22 static features each, such as rivers, narrow
  crossings, railway connections and terrain.

The layout version, now `campaign-zone-v1-8cbe8cede50d5629`, is a hash of every
feature name and every static feature. A network refuses inputs of another
layout, and a training run cannot resume across a layout change. It last changed
on 18 November 2026, when the marks on things the rules never put them on and
the facts that never change were removed (section 8).

## 10. Why the encoder translates names

The engine came first. It was written to follow the
rulebook, and many parts of the project use it: the Python interface, the tests,
saved games and replays, the map viewer, and training checkpoints, which store
the whole game as JSON. Names keep all of these readable, let the engine load its
units, map and rules from JSON files, and let a rule add a new mark or battle
note without changing a shared format. The networks came later.

The first network input, used until 2 November 2026, really did read text: it
printed each state as JSON, cut every name into word pieces and hashed the
pieces into 16,384 slots. The zone encoding replaced it with a fixed list of
features built straight from the engine's memory: 49 to 64 times smaller and 5
to 6 times faster to build ([record](../archive/records/zone_encoding_2026_11_02.md)). It
left the engine's names as they were and translates them instead.

Reading an action's named details also lets one piece of code describe all 144
kinds of action, and kinds added later. Without it, every kind of action would
need its own encoder code, kept in step with its rule by hand.

**What names cost:**

- **Speed: little.** Encoding is about 4% of a game process's work (section 1),
  and the name lookups are only part of encoding.
- **Correctness: the real cost.** For everything still named, the engine and
  the encoder agree only through names. A rule can write a name the encoder's
  lists lack, and the name falls into an "other" feature and is only counted.
  That is how the missing names of [section 7](#keeping-the-lists-complete)
  arose; since 4 November tests check the names the engine's source writes.

**The alternatives:**

| Option | What it means | Assessment |
| --- | --- | --- |
| The engine writes the network's numbers itself | every rules module also fills input features as it plays | Spreads learning code through the rules: every rule change becomes an input change, and the rules get harder to check against the rulebook. Not recommended. |
| The engine holds numbers instead of names | inside the engine, zones, nations, unit types and classes, facility types, technologies and the bases of marks become numbers; saved games, actions, battle notes and the scenario's files keep names, which the engine converts where they enter and leave ([where names become numbers](../engine/names.md#4-where-names-become-numbers)) | Done on 16 November, for the engine's own speed rather than the encoder's: before it, comparing names, allocating memory, looking up maps and copying memory took 59% of the engine's time, and a searched game now runs 23.9% fewer instructions, with play unchanged ([why numbers](../engine/names.md#1-why-numbers)). For zones, nations, unit types, facility types and technologies the encoder translates nothing: each one's number is its index in the encoder's list (section 1). Units, facilities, railroads, battles, an action's details and a battle's notes are still names ([what is still a name](../engine/names.md#what-is-still-a-name)), so the encoder still translates those, and the check in the next row still guards them. |
| Keep the names, but check them | a test scans the engine's source for the names it writes and compares them with the encoder's lists, and full random games fail on any unknown name | Closes the missing-names gap without touching the rules. Built on 4 November for the usual ways the engine writes names ([section 7](#keeping-the-lists-complete)). |

A stricter form of the last option is one register of names, each declared once
with its meaning and used by both the engine and the encoder, so that the engine
cannot write an undeclared name. It is a larger change and has not been
designed.
