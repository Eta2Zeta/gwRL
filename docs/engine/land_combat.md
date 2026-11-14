# Land combat

This module fights the battles on land: the dice, the casualties both sides
choose, retreats, and what the attacker may do after winning. Entering the zone
is [movement](movement.md); who holds the zone afterwards is
[politics](politics.md#5-capturing-land). It is one of the engine's six rules
modules ([overview](README.md#7-the-rules-by-subject)).

Code: `include/game/land_combat.hpp`, `src/land_combat.cpp`. Rules data:
`game_content/rules/gw36_land_combat_v43.json`.

## 1. What a battle is

A battle is a record in the game's state (`BattleState`): the zone, the
attacker and the defender, the units on each side, the stage it has reached and
everything still to be decided in it. Nothing about a battle is kept anywhere
else, so a copy of the game can carry on any battle from where it stands.

A land battle is *registered* in Combat Movement, when land units enter enemy
land (`registerLandBattle`). Each attacking unit's record keeps the zone it came
from. It is *fought* in the Combat Phase: the attacker chooses which of its
registered battles to begin next (`land_begin_battle`), and one battle runs to
its end before the next begins.

## 2. A battle, round by round

Before the first round, the defender may bring aircraft into the battle or get
them out of it ([air](air.md)), and a landing from the sea is prepared by shore
bombardment ([naval](naval.md)). Then the battle is fought in rounds.

1. **Pairing.** Each side pairs its artillery with the units it supports
   (`land_pair_artillery`).
2. **First strike.** Units with a first strike fire. Their casualties are
   removed at once and do not fire back.
3. **Fire.** Both sides fire. Every shot is one twelve-sided die, and it hits
   when the die shows at most the unit's attack value, for an attacker, or its
   defence value, for a defender, after modifiers. All the dice of one volley
   are one chance event.
4. **Casualties.** For each hit, a unit is removed. The side that was hit
   chooses which (`land_take_casualty`), except for hits by a unit with *Target
   Selection*, whose owner chooses. A defender hit in this step has already
   fired.
5. **Continue or retreat.** If both sides still have units, the attacker
   decides: another round (`land_continue_fighting`) or retreat
   (`land_retreat_begin`).

The battle ends when one side has no units left, or the attacker retreats. If
an attacking land unit is left alone in the zone, the zone is captured.

**Who chooses.** Each choice goes to the alliance entitled to it, also during
another alliance's turn. Two nations defending one zone together agree on their
casualties (`land_casualty_accept`) or settle it by the rulebook's dice-off
(`land_casualty_dispute`). The engine has no rule of its own for which unit
dies.

## 3. What changes the dice

A unit's values come from the [catalog](scenario.md#5-the-catalog). The battle
applies (`landCombatStats`):

- **the zone's terrain**, for the whole battle;
- **the border each attacker crossed**, for that unit only: its terrain and
  whether it crossed a river. Two units that entered from different zones can
  therefore fight the same battle with different values;
- **fortifications**, against the approaches they cover;
- **artillery pairing**, national modifiers such as Japan's, and technologies.

A value never falls below 1.

## 4. Retreat

Only the attacker retreats.

- **Where to.** Each retreating unit goes back to a zone it or another attacker
  came from, if that zone is still friendly (`land_retreat_unit`). Units may
  retreat to different zones.
- **Who cannot.** Units that arrived by air drop or from the sea cannot
  retreat.
- **Forced retreat.** In a city the attacker must retreat after three rounds,
  except in Japan's Surprise Attack, and in tundra or ice after one. Units that
  then cannot retreat are eliminated.

## 5. Special cases

**KMT Low Morale.** While the KMT is a minor power, its attacking Infantry and
Cavalry lose heart: a unit whose attack die shows 10 or more goes back to the
zone it came from and is out of the battle. If it has nowhere to go back to,
for example after a landing, it is eliminated (RCL-016). Defending KMT units
and a KMT that has become a major power are not affected.

**Attacking an empty zone.** A battle is still registered and begun, so that
Low Morale is rolled before the zone is taken.

**Breaking the Chinese Truce.** The battles in the zones the KMT and the CCP
share are fought at once, with the breaker attacking
([politics](politics.md#3-the-chinese-truce)). A KMT unit that rolls 10 or more
in them is eliminated (RCL-012).

**Blitz.** If the attacker wins within two rounds, its armour may move on. The
attacker pairs companions with each armour unit (`land_pair_blitz`,
`land_finish_blitz_pairing`), and they follow it in a
[blitz move](movement.md#2-the-ways-to-move).

**Attrition.** Advanced Artillery that has not moved may bombard a neighbouring
enemy zone without entering it (`land_declare_attrition`, in Combat Movement).

**Japan's Surprise Attack.** In the turn Japan first declares war on a major
power of the Allies, it names one zone for its Surprise Attack
(`land_select_surprise_zone`), which changes first strikes and scrambling
there.

**Strategic Rockets** in a battle neither fire nor take hits. If enemy land
units survive in the zone, the rockets are destroyed.

## 6. Finished battles

A finished battle stays in the state until its follow-ups are done: aircraft
landing, blitz pairing, the choice to keep or give a captured zone. In the
interface for people a move then clears it (`land_progress_battle`). In
training the engine clears it without a move, so that the learner is not asked
to click through battles that offer no choice
([overview, section 3](README.md#3-positions-and-moves)). `land_progress_battle`
remains for a battle that is waiting to go on, for instance after the defender's
aircraft are settled.

## 7. The moves

| Move | Phase | Chosen by | What it does |
| --- | --- | --- | --- |
| `land_begin_battle` | Combat | the attacker | Begins one registered battle |
| `land_progress_battle` | Combat | the attacker | Carries a waiting battle on |
| `land_pair_artillery` | Combat | the owner of the artillery, attacker or defender | Pairs artillery with a unit |
| `land_take_casualty` | Combat | the side that was hit, or the firer with Target Selection | Names the unit removed by one hit |
| `land_casualty_accept`, `land_casualty_dispute` | Combat | joint defenders | Agree on shared casualties, or roll for it |
| `land_continue_fighting`, `land_retreat_begin` | Combat | the attacker | Another round, or retreat |
| `land_retreat_unit` | Combat | the attacker | Sends one retreating unit to a zone |
| `land_pair_blitz`, `land_finish_blitz_pairing` | Combat | the attacker | Pairs companions with armour for a blitz |
| `land_declare_attrition` | Combat Movement | the alliance of the nation whose turn it is | Declares an artillery bombardment |
| `land_select_surprise_zone` | Combat Movement | the Axis, for Japan | Names the zone of the Surprise Attack |

In 240 random games there were 34,633 volleys of land combat dice and 12,046
casualty choices. Joint defence, blitz, attrition and the Surprise Attack never
came up ([record](../archive/records/move_census_2026_11_14.md)); the tests
cover them.

Tests: `tests/land_combat_tests.cpp`, `tests/land_truce_tests.cpp` and
`tests/training_battle_clearing_tests.cpp`.
