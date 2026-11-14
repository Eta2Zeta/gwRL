# Politics: wars, warlords, the Truce and surrender

This module decides who is at war with whom, which side a warlord joins, who
holds a zone after it is taken, when a Chinese nation becomes a major power and
when a nation gives up. It also holds the two rolls a nation makes in Place
Units: recruiting units, and winning over a warlord. It is one of the engine's
six rules modules ([overview](README.md#7-the-rules-by-subject)).

Code: `include/game/politics.hpp`; `src/politics.cpp` (wars, captures,
evolution, surrender), `src/politics_warlords.cpp` (warlords and the Truce),
`src/politics_influence.cpp` (influence and recruitment). Rules data:
`game_content/rules/gw36_politics_v43.json`.

## 1. War

At the start the KMT and the CCP are at war with each other, and nobody else is
at war. A war begins in one of two ways (`mayDeclareWar`):

- **On a major power: by declaring it**, with the move `politics_declare_war`.
  This can be done out of turn ([overview, section 6](README.md#6-moves-made-out-of-turn)).
- **On a minor nation or a warlord: by attacking it.** Moving a land unit into
  its land during one's own Combat Movement declares the war.

| Who | May start a war with |
| --- | --- |
| Japan | Any nation outside its alliance |
| The KMT or the CCP, while a minor power | Japan or Dadao, while that nation holds land or has units in the Chinese Home Country |
| The KMT or the CCP, as a major power | Japan or Dadao |
| The CCP | A warlord, by attacking it |
| The KMT | A warlord or Mongolia, by attacking it, but only once the CCP has no units left |
| Dadao | A Chinese nation or a warlord, by attacking it |
| Mongolia | Nobody |

Two nations of one alliance never go to war, and while the Chinese Truce holds
the KMT and the CCP cannot declare war on each other; they break the Truce
instead ([section 3](#3-the-chinese-truce)).

**The nation whose turn it is declares first.** When another alliance declares
a war out of turn, the alliance whose turn it is first gets a decision
(`politics_declaration_priority`): it may make declarations of its own
(`politics_priority_declare`) or decline (`politics_priority_decline`). The
out-of-turn declaration then takes effect.

**Becoming allies.** Two nations of one alliance that are at war with the same
major power become allies, which lets them share zones and defend together.
Being in the same alliance is not enough by itself.

## 2. The warlords

The eight warlords start unaligned: nobody plays them, they take no turn and
they have no money. If one is attacked, the Allies choose its casualties and
retreats for that battle.

A warlord that joins a nation stops existing as a nation of its own: its land,
its units and anything it was building become that nation's
(`incorporateNation`). Land gained this way may be entered the same turn, unlike
land that was captured. A warlord joins a side in one of four ways.

**A foreign power invades China.** The invasion is a land attack, by a nation
that is not Chinese, on a zone that was originally the KMT's, the CCP's or a
warlord's (`recordLandAttack`). In this campaign that means Japan. The attack
puts the invader at war with the KMT, the CCP and every unaligned warlord at
once, and every such warlord picks a side at the end of that Combat Phase. All
the warlords' neighbours are noted first, so that one warlord's result cannot
change another's odds. Each warlord gets one roll of a twelve-sided die for all
its land (RCL-003):

| The warlord's land borders | Roll | It joins |
| --- | --- | --- |
| neither the CCP nor Dadao | no roll | the KMT |
| the CCP only | 1–6 | the CCP |
| | 7–12 | the KMT |
| Dadao only | 1–6 | Dadao |
| | 7–12 | the KMT |
| both | 1–5 | the CCP |
| | 6–10 | the KMT |
| | 11–12 | Dadao |

**The CCP or Dadao attacks it.** With no foreign invasion that phase, a warlord
attacked by the CCP or Dadao joins the KMT at the end of Combat, unless the KMT
has surrendered.

**The KMT attacks it.** The warlord joins the CCP at once. The KMT may attack a
warlord only when the CCP has no units left, so this brings the CCP back.

**Influence.** In its Place Units Phase, Japan, or the CCP while it is a minor
power, may try once to win over an unaligned warlord (`influence_roll`).

- **Who can be targeted:** a warlord whose land borders zones the nation
  controls, at least one of them holding a unit that has stood there since the
  turn began. The number of those bordering
  zones is the *threshold*.
- **The roll:** one twelve-sided die. The nation may first pay IPP, at most the
  threshold and at most its treasury (RCL-002); each IPP lowers the roll by one.
  The move names the warlord and the amount.
- **Success:** the lowered roll is at most the threshold. The warlord joins the
  CCP, or, for Japan, joins Dadao, which the first success creates.
- **A natural 12** always sends the warlord to the KMT instead, whatever was
  paid.

## 3. The Chinese Truce

The Truce is a ceasefire between the KMT and the CCP against an invader. In 240
random games it was never offered
([record](../archive/records/move_census_2026_11_14.md)), so the engine's tests
are the only evidence for this part.

- **When it can be signed.** A major power invades China as described in
  [section 2](#2-the-warlords), and the invasion starts a new war with the KMT
  or the CCP. At the end of that Combat Phase, after the warlords have picked
  sides, the CCP may offer the Truce (`truce_offer`, or
  `truce_decline_offer`), and the KMT accepts or refuses (`truce_accept`,
  `truce_reject`). Both must still be minor powers, and the KMT must not have
  surrendered.
- **What it does.** The two stop fighting, may not declare war on each other
  and may share zones.
- **How it ends.** Either one may break it in its own Combat Phase
  (`truce_break`). Battles then start in every zone the two share, and the
  breaker attacks. It also ends when either becomes a major power. Once ended,
  it cannot be signed again.

## 4. Becoming a major power

The KMT or the CCP becomes a major power the moment the land it holds is worth
13 IPP, even in the middle of another nation's turn. Its alliance then answers
one decision (`politics_evolution`): which of its zones becomes its capital,
and whether to take a free factory there (`politics_choose_capital`). A zone it
loses before answering drops off the list.

From then on the nation may move and attack outside the Chinese Home Country
and declare war on any major power. The CCP loses its minor-power recruitment
and influence, and the KMT loses its Low Morale
([land combat](land_combat.md)). An active Truce ends.

## 5. Capturing land

A battle that leaves a land unit of the attacker in the zone captures it
(`captureLand`).

- **Who gets it.** The attacker, with one exception: if the zone originally
  belonged to a major power of the attacker's own alliance that has not
  surrendered, that nation gets it back.
- **A capital.** If the zone was its holder's capital, the holder's treasury
  falls to zero.
- **What is removed.** Fortifications and coastal artillery in the zone, and
  anything under construction there.
- **Chinese land taken by an outside major power.** Japan may keep it
  (`politics_keep_capture`) or give it to the KMT or the CCP
  (`politics_give_capture`). If it gives the zone to a nation it is not
  friendly with, its units there must leave in Noncombat Movement. The KMT and
  the CCP themselves always keep what they take.
- **Units of a third nation** that were in the zone as friends of the old
  holder must move to friendly land (`politics_relocate_neutral`), and are
  removed if there is none (RCL-015).

## 6. Surrender

| Nation | Surrenders when | Checked |
| --- | --- | --- |
| The KMT | It holds no land | At once |
| Japan | A nation at war with it holds Tokyo | At the end of Japan's own turn |
| The CCP | Never | |

A nation that surrenders loses all its units, and its land becomes nobody's.
Each ship it had under construction is rolled for: on 1 to 7 it is scuttled, on
8 to 12 the conqueror takes it over as it is.

## 7. Recruitment

In its Place Units Phase a nation may roll once to recruit (`recruitment_roll`):

- **the CCP**, for itself, while it is a minor power;
- **the Comintern, for Mongolia**, in Mongolia's turn;
- **Japan, for Dadao**, in Japan's turn.

The roll is one twelve-sided die against the number of land zones the nation
holds; for Mongolia and Dadao, offshore zones do not count. On a success the
alliance chooses what the nation gets (`recruitment_choice`): an infantry
placed in one of its zones, militia, the next stage of a ship it is building,
or the repair of a facility.

## 8. The moves

| Move | Phase | Chosen by | What it does |
| --- | --- | --- | --- |
| `politics_declare_war` | any, out of turn | the declaring alliance | Declares war on a major power |
| `politics_priority_declare`, `politics_priority_decline` | when another alliance declares | the alliance whose turn it is | Declares first, or lets the declaration through |
| `truce_offer`, `truce_decline_offer` | end of Combat | the Comintern, for the CCP | Offers the Truce or not |
| `truce_accept`, `truce_reject` | end of Combat | the Allies, for the KMT | Answers the offer |
| `truce_break` | Combat | the Chinese nation whose turn it is | Ends the Truce and starts the battles |
| `politics_choose_capital` | at 13 IPP | the alliance of the new major power | Names the capital and takes the factory or not |
| `politics_keep_capture`, `politics_give_capture` | Combat | the Axis, for Japan | Keeps captured Chinese land or gives it away |
| `politics_relocate_neutral` | Combat | the owner of the units | Moves units out of a captured zone |
| `influence_roll` | Place Units | Japan's or the CCP's alliance | Tries to win over a warlord |
| `recruitment_roll` | Place Units | the alliance of the nation whose turn it is | Rolls to recruit |
| `recruitment_place_infantry`, `recruitment_place_militia`, `recruitment_advance_ship`, `recruitment_repair_facility` | Place Units | the same alliance | Takes what the roll gave |

Tests: `tests/politics_tests.cpp`, `tests/politics_warlords_tests.cpp`,
`tests/politics_influence_tests.cpp` and `tests/land_truce_tests.cpp`. The
printed pages behind these rules are listed in
[Politics: source coverage](../rules/politics_sources.md).
