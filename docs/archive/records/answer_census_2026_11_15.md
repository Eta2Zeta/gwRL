# Which questions random games answer — 15 November 2026

The network's input asks 59,235 fixed questions
([the network's input](../../design/network_input.md)). This record counts
which of them random games ever answer, which marks the engine puts on a
nation, what the input does with four marks it does not list, how often
Mongolia is recorded as the invader of China, and when the KMT is offered an
attack on Mongolia. The numbers are the evidence for the
[questions waiting for a decision](../../questions.md) Q-001 to Q-004 and
Q-006. The [data file](answer_census_2026_11_15.json) holds every
count.

## Setup

Commit `bce7a4c`, layout `campaign-zone-v1-9e192fe5c085f13e`.
`tools/answer_census.py` played 480 eleven-round games, seeds 7000 to 7239 and
9000 to 9239, through the environment training uses (`make_env`), on 8 worker
processes of the M4 Max, in 3 minutes 38 seconds. The games are those of
`tools/check_zone_names.py`: every move is drawn uniformly at random, except
that where the phase can end it is ended with probability 2%, 5% or 10%,
depending on the seed. Every decision and every dice position was encoded:
627,342 decisions and 82,912 dice positions, 710,254 encoded positions in all.
No name was reported as unknown.

```sh
./.venv/bin/python tools/answer_census.py OUT.json --first-seed 7000 9000 --games 240 --workers 8 --detail position
```

## Which questions were answered

A question counts as answered if at least one encoded position gave it an
answer other than 0. A *mark question* is one of a family that asks about
marks, listed in the second table.

| Part | Questions | Answered | Mark questions | Mark questions answered |
| --- | ---: | ---: | ---: | ---: |
| The board, for each zone | 42,532 | 3,158 | 5,660 | 106 |
| The position | 4,076 | 843 | 1,890 | 124 |
| A move | 12,627 | 1,810 | 1,352 | 60 |
| All three | 59,235 | 5,811 | 8,902 | 290 |

| Part | Family of mark questions | Questions | Answered |
| --- | --- | ---: | ---: |
| Board | `unit_flag` | 1,920 | 30 |
| Board | `facility_flag` | 1,744 | 33 |
| Board | `nation_flag_here` | 1,560 | 16 |
| Board | `project_flag` | 218 | 10 |
| Board | `battle_flag` | 109 | 16 |
| Board | `territory_flag` | 109 | 1 |
| Position | `nation_flag` | 1,560 | 88 |
| Position | `unsited_project_flag` | 218 | 26 |
| Position | `state_flag` | 109 | 8 |
| Position | `state_flag_nation` | 3 | 2 |
| Move | `unit_cargo_flag` | 480 | 19 |
| Move | `project_flag` | 436 | 25 |
| Move | `facility_flag` | 436 | 16 |

The data file lists every answered position question with the number of
positions and games that answered it and its smallest and largest answer, and
for the board and the moves the count of each family.

**Answered alike everywhere.** 41 position questions were answered in every one
of the 710,254 positions, always with the same answer:

| Questions | How many | Can the rules give another answer? |
| --- | ---: | --- |
| `nation_present` for every nation but Dadao | 12 | No: these nations are in the game from the start and never leave it |
| `alliance` and `player` of Japan, the KMT, the CCP and Mongolia | 8 | No ([what the position asks about a nation](../../design/network_input.md#what-the-position-asks-about-a-nation)) |
| `power_status` of Japan, Mongolia and the eight warlords | 10 | No |
| `controller` of Japan, the KMT, the CCP and Mongolia | 4 | No |
| `at_war` between the KMT and the CCP, both ways | 2 | Not in the engine: they start at war and it never ends that war; under the Truce it treats them as friends while the war stays recorded |
| `state_flag:__campaign_started` | 1 | No: the engine sets it when the campaign starts |
| `interrupt_order`: Axis first, Allies second, Comintern third | 3 | Not as the scheduler is written: it offers out-of-turn moves in a fixed order |
| `nation_flag:ccp:economy_research_finished` | 1 | Yes: it is 0 while a CCP that has become a major power still has research to do, which never happened |

Every `player` answer was the same as the `alliance` answer for the same
nation and side, in every position.

## Mongolia as the invader of China

The engine records an invasion of China when a nation that is not Chinese
attacks a land zone that was originally a warlord's, the CCP's or the KMT's
(rulebook 4.9, page 30; `recordLandAttack` in `src/politics.cpp`). In 70 of the 480
games that nation was Mongolia, 109 times in all. The first time in each game:

| | Games of 70 |
| --- | ---: |
| The attacked zone was held by the KMT | 45 |
| The attacked zone was held by Japan | 25 |
| Mongolia came to be at war with the CCP | 70 |
| Mongolia also came to be at war with the KMT | 23 |
| A warlord had not yet joined a side | 1 |
| The CCP still had units | 27 |

Before the attack Mongolia was at war with Japan and the KMT in 32 games, with
Japan alone in 23 and with the KMT alone in 15. Of the 109 attacked zones, 106
were originally a warlord's and 3 the CCP's. Three of the later attacks were on
zones the CCP itself held: once at war, the two Comintern nations fought.

Two of the games, move by move:

- **Seed 7155, a zone held by the KMT.** In round 1 the CCP attacks the Ma
  Clique in Tsinghai, which therefore joins the KMT with its land at the end of
  that Combat Phase (rulebook 4.9, page 30: a warlord attacked by the CCP
  aligns with the KMT). Later in the round the KMT destroys the CCP's last
  units. In round 2 a KMT infantry attacks Ulyassutai. The declaration-of-war
  table lets the KMT attack Mongolia by a combat move once the CCP has been
  eliminated (rulebook 5.1, page 35, the KMT's rows; KMT national reference
  sheet, page 2), so the KMT and Mongolia are at war. In round 3 a Mongolian
  cavalry moves from Kerulen through Central Mongolia into Tsinghai as an
  attack (decision 342). From that move on Mongolia is at war with the CCP.
- **Seed 7024, a zone held by Japan.** In round 1 the CCP attacks Mengjiang in
  Suiyuan, which joins the KMT (rulebook 4.9, page 30). In round 2 Japan
  attacks Suiyuan and takes it, and a Japanese infantry attacks Kerulen: an
  Axis major power may declare war on any nation outside the Axis, on a minor
  power by a land unit's combat move (rulebook 5.1, page 35), so Japan and
  Mongolia are at war. In round 3 a Mongolian cavalry moves from Kobdo through
  Central Mongolia into Suiyuan as an attack (decision 379). From that move on
  Mongolia is at war with the KMT and the CCP as well.

Rulebook 4.5 (page 27) does not let the controller of a minor power take an
action that puts it at war with a power it is not already at war with. The
engine checks that Mongolia is at war with the holder of the zone it attacks
(`landAccess` in `src/movement.cpp`), not that the attack starts no other war.

These events were found by playing the same games again and reading the state
after each move made on Mongolia's turn. The script is not kept; the data file
lists the first event of each game with its seed and decision number, so each
can be checked by replaying the seed with the policy above.

## The marks the engine puts on a nation

The input lists 119 marks for units and nations together (`kActorFlags` in
`src/zone_encoding.cpp`) and asks every nation about each of them. Read from
the source, the engine writes 43 of them on a nation: every write to a
nation's `turnFlags` or `gameFlags` in `src/` was listed, including writes
through another name for the same table and names put together in a variable.
One more, `economy_researched_round`, is written on a nation too, but the
input asks about it in a family of its own, `researched_round`.

| Source file | Marks it writes on a nation |
| --- | --- |
| `src/politics.cpp` | `civil_war_eliminated`, `controller_unresolved`, `direct_axis_control_after_japan_surrender`, `evolved_during_own_turn`, `evolved_turn_serial`, `first_allies_major_war_declared`, `incorporated`, `objective_evolution`, `objective_one_china`, `one_china_bonus_awarded`, `one_china_bonus_eligible_at_surrender`, `politics_combat_finished`, `possessed_land_ipp`, `surprise_attack_available`, `surprise_attack_target`, `surrendered` |
| `src/politics_influence.cpp` | `influence_attempted`, `recruitment_attempted`, `surrendered` |
| `src/economy.cpp` | `economy_militia_placed`, `economy_militia_upgrades`, `economy_production_cap`, `economy_repair_cap`, `economy_repairs_finished`, `economy_research_capacity`, `economy_research_finished`, `economy_research_used`, `economy_start_damage`, `economy_start_type`, `economy_used`, `purchased`, `rail_build_permission`, `rail_declined` |
| `src/economy_lendlease.cpp` | `economy_militia_upgrades`, `economy_used`, `lease_declared`, `lease_delivered`, `lease_repair_wait` |
| `src/movement.cpp` | `logistics_last_turn_start`, `rail_permission`, `rail_used` |
| `src/land_combat.cpp` | `surprise_attack_used`, `surprise_attack_zone` |
| `src/naval_combat.cpp` | `surprise_attack_naval_sea`, `surprise_attack_used` |
| `src/naval_movement.cpp` | `strategic_naval_used` |
| `src/naval_operations.cpp` | `surprise_attack_linked_land`, `surprise_attack_used`, `surprise_attack_zone` |
| `src/air.cpp` | `surprise_attack_used` |

The input lists 108 marks for territories, facilities, construction projects,
battles and the game as a whole (`kRecordFlags`) and asks the game as a whole
about each of them. The engine writes 11 of them on the game as a whole,
besides the counters whose names end in `_sequence`, which the input skips:

| Source file | Marks it writes on the game as a whole |
| --- | --- |
| `src/campaign_runtime.cpp` | `__campaign_started` |
| `src/air.cpp` | `logistics_damaged_turn`, `stranded_aircraft_lost` |
| `src/economy.cpp` | `logistics_damaged_turn`, `logistics_rail_created_turn` |
| `src/movement.cpp` | `crossing_used`, `logistics_start_damaged` |
| `src/land_combat.cpp` | `immediate_land_battles` |
| `src/politics_warlords.cpp` | `immediate_land_battles` |
| `src/naval_combat.cpp` | `immediate_naval_battles` |
| `src/naval_movement.cpp` | `immediate_naval_battles`, `naval_move_decisions` |
| `src/naval_operations.cpp` | `immediate_naval_battles`, `naval_berthing` |
| `src/politics.cpp` | `evolution_pending` |

This is a reading of the code, not a test: no check yet fails when a rule
starts writing another mark on a nation.

## Four marks without a question

With Improved Construction, a factory or a city takes less damage from
strategic bombing in each player turn: a minor factory 1 less, a medium
factory 3, a major factory 5, a city 5 (rulebook 8.2.1, page 46). The engine
notes on the nation that holds it how much has been taken off this turn:
`applyFacilityBombDamage` in `src/air.cpp` writes `bombing_reduction` and
`bombing_reduction_turn`, and `applyCityBombDamage` in the same file writes
`city_bombing_reduction` and `city_bombing_reduction_turn`, each followed by
the name of the facility or the zone. None of the four is on the input's list
of marks. The test that reads the source for marks (`test_marks` in
`tests/test_campaign_zone_encoding.py`) looks for names written out between
the brackets, and these are put together in a variable first. No game above
reached them.

To see what the input does with them, an opening position was given each pair
on Japan and encoded:

| Marks put on Japan | Reported as unknown | Answer in the input |
| --- | --- | --- |
| `bombing_reduction` = 2 and `bombing_reduction_turn` = this turn, for a facility | `actor_flag:bombing_reduction`, `actor_flag:bombing_reduction_turn` | `nation_flag:japan:other = 3` |
| `city_bombing_reduction` = 4 and `city_bombing_reduction_turn` = this turn, for Tokyo | `actor_flag:city_bombing_reduction`, `actor_flag:city_bombing_reduction_turn` | `nation_flag:japan:other = 5`, and on Tokyo's line of the board `nation_flag_here:japan:other = 5` |

A first version of this record named only the first pair.

## The KMT and Mongolia after the CCP comes back

The declaration-of-war table lets the KMT attack Chinese warlords or Mongolia
once the CCP has been eliminated (rulebook 5.1, page 35; KMT national
reference sheet, page 2), and the Chinese Civil War ends when one faction has
no surviving units (rulebook 14.3, page 101). The engine allows the attack
only while the CCP has no units at that moment (`mayDeclareWar` in
`src/politics.cpp`). A CCP without units keeps its land and its treasury and
can buy units again.

| In the 480 games | Games | Decisions |
| --- | ---: | ---: |
| The CCP had no units at some decision | 154 | |
| ... and had units again later | 57 | |
| The KMT, not at war with Mongolia, stood next to it in Combat Movement while the CCP had no units, and the attack was offered | 124 | 244 |
| The same, after the CCP had units again: no attack offered | 43 | 600 |
| The same, while the CCP had no units, but no attack offered | 8 | 48 |

The last row was not looked into; in the one example read, the KMT units next
to Mongolia were militia.

One of the games, move by move (seed 9105):

1. Round 2, the CCP's Combat Phase: the CCP loses its last two units in
   battles on its own turn (decisions 218 and 220). It has no units and still
   holds Shensi.
2. Its Place Units Phase: it places an infantry it had bought (decision 223).
   It has one unit again.
3. The KMT's Combat Movement in the same round (decision 355): KMT units in
   Tsinghai stand next to Central Mongolia and Ulyassutai. The engine offers
   seven combat moves, into Shensi and Rehe, and none into Mongolian land.

These counts were made by playing the same games again and reading the state
at the KMT's Combat Movement decisions. The script is not kept; the data file
holds the counts and one example of each kind with its seed and decision
number.

## What this shows and what it does not

- **Not answered is not impossible.** Random games never signed the Chinese
  Truce and never saw a surrender, and both are in the rules. Only the rules
  can show that a question cannot be answered.
- **Random play is not trained play.** How often trained agents would meet
  Mongolia's invasions is not measured. Random play meets them in one game in
  seven, from round 3 on, so they are not a corner that play never reaches.
- **Answered alike in 710,254 positions is not proof either.** The table says
  for each group whether the rules allow another answer; that part is read
  from the code, not measured.
