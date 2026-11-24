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
at war. A war begins in one of three ways:

- **On a major power: by declaring it**, with the action `politics_declare_war`.
  This can be done out of turn
  ([overview, section 6](README.md#6-actions-taken-out-of-turn)).
- **On a minor nation or a warlord: by attacking it.** Moving a land unit into
  its land during one's own Combat Movement declares the war.
- **On all of China outside the attacker's alliance: by attacking original
  Chinese land**, when the attacker is not Chinese. This is an invasion of
  China, set out [below](#invading-china).

`mayDeclareWar` decides who may start a war in the first two ways:

| Who | May start a war with |
| --- | --- |
| Japan | Any nation outside its alliance |
| The KMT or the CCP, while a minor power | Japan or Dadao, while that nation holds land or has units in the Chinese Home Country |
| The KMT or the CCP, as a major power | Japan or Dadao |
| The CCP | A warlord, by attacking it |
| The KMT | A warlord or Mongolia, by attacking it, from the CCP's first elimination to the end of the game |
| Dadao | A Chinese nation or a warlord, by attacking it |
| Mongolia | Nobody |

The rows for Japan, the KMT and the CCP follow the declaration-of-war table of
rulebook 5.1 (pages 35 and 36), which is repeated on the national reference
sheets of Japan (page 3), the CCP (page 2) and the KMT (page 2). Dadao's row
follows rulebook 15.4 (page 105). Mongolia starts no war in these two ways
because the power that controls a minor power may not declare war for it
(rulebook 4.5, page 27); its invasion of China, the third way, is one the
game's developers allow ([below](#invading-china)).

The KMT's row follows the printed condition "if CCP previously has been
eliminated" (rulebook 5.1, page 35; KMT sheet, page 2): once the CCP has been
left with no units, the KMT may make these attacks for the rest of the game,
even after the CCP has units again, as the owner confirmed on 21 November 2026.
The engine records the elimination in the mark `civil_war_eliminated` on the
CCP, which it sets the moment the CCP's last unit is removed
(`removePoliticalUnits`) and never clears, and `mayDeclareWar` asks that mark.
The KMT carries the same mark, set the same way.

No nation may declare war inside its own alliance (rulebook 5.1, page 35), and
while the Chinese Truce holds the KMT and the CCP cannot declare war on each
other; they break the Truce instead ([section 3](#3-the-chinese-truce)).

**The nation whose turn it is declares first.** When another alliance declares
a war out of turn, the alliance whose turn it is first gets a decision
(`politics_declaration_priority`): it may make declarations of its own
(`politics_priority_declare`) or decline (`politics_priority_decline`). The
out-of-turn declaration then takes effect.

**Becoming allies.** Two major powers of one alliance that are at war with the
same major power become allies, which lets them share zones and defend
together (`politicallyFriendly`). Being in the same alliance is not enough by
itself. In this campaign it never happens: the only possible major powers,
Japan, the KMT and the CCP, are in three different alliances. The only allies
are the KMT and the CCP under the Chinese Truce
([section 3](#3-the-chinese-truce)).

### One attacker for each land zone

A controlled minor power shares the Player Turn of the major power that
controls it, and the two "may not attack together" (rulebook 7.1, page 43). In
this campaign the pair is Japan and Dadao, a minor power that Japan controls
(rulebook 15.4, page 105; Japan sheet, page 1): Japan's player moves Dadao's
units in Japan's turn (`movementController` in `src/movement.cpp`). The owner
ruled on 24 November 2026 what the rule forbids
([RCL-024](../../game_content/rules/clarifications.md#rcl-024-two-attacks-on-one-land-zone-by-a-controlled-minor-power-and-its-controller)):
of the nations that share a Player Turn, only the first to attack a land zone
may attack it in that turn, in any way, and an aircraft supports only a battle
of its own nation.

**What the engine does.**

- `noteLandAttack` (`src/politics.cpp`) sees every attack on a land zone:
  `recordLandAttack` calls it for a move overland or across a strait, a blitz,
  an assault from the sea, an aircraft's attack and an air drop, and
  `registerAttritionBattle` (`src/land_combat.cpp`) for an attrition attack. It
  refuses an attack on a zone that another nation of the turn has attacked.
  When another nation shares the turn, it also gives the attacker the mark
  `land_attack` for that zone, such as `land_attack:land_manchuria_rehe` on
  Dadao.
- `landAttackedByPartner` (same file) says whether another nation has that
  mark for a zone. The lists of legal actions ask it before they offer an
  attack: a land move, a strait crossing or a blitz (`validateRoute` in
  `src/movement.cpp`), an assault from the sea (`src/naval_operations.cpp`), an
  aircraft's attack, an air drop or an air blitz (`src/air.cpp`), and an
  attrition attack (`src/land_combat.cpp`). An aircraft is offered support only
  for a battle of its own nation.
- The marks go when the Combat Phase ends (`PoliticsRules::finishPhase`), so
  the zone is open to both nations again in their next turn. A nation's own
  further attacks on a zone it has attacked are not affected, and a nation
  that shares its turn with no other nation gets no mark.
- The engine's test `japanAndDadaoNeverAttackOneZone`
  (`tests/naval_operations_tests.cpp`) starts from the position of game 5967
  of the training run under the land-weighted score, which failed when both
  nations had attacked Manchuria-Rehe
  ([record](../archive/records/japan_dadao_one_zone_2026_11_23.md)): the KMT
  holds Rehe, Japan has an Artillery aboard a Naval Transport in sea zone P14,
  and Dadao an Infantry in Suiyuan. The test adds units of both nations for
  the other kinds of attack. Once Japan has declared its assault on Rehe,
  Dadao's Infantry and Dadao's Fighter are offered no attack on Rehe, while
  Japan may still attack it overland. When Dadao attacks first, Japan is
  offered no attack on Rehe from the sea, overland, from the air, by air drop
  or by attrition, and may still assault Shantung. In
  `noBlitzIntoTheZoneTheOtherAttacked`, Japan's armour may not blitz into a
  zone that Dadao attacked earlier in the turn.

### Invading China

*Original Chinese land* is a land zone with a warlord's, the CCP's or the
KMT's roundel printed in it, whoever holds the zone now: the rulebook's
glossary (page 7) defines "originally" by the roundel printed on the map. Rule
4.9 (page 30) makes an attack by a foreign nation on original Chinese land a
declaration of war on all of China, that is on the KMT, the CCP and every
warlord at once. The game's developers answered that the attack spares a
Chinese nation of the attacker's own alliance, and that any foreign nation may
make it, Mongolia too
([RCL-022](../../game_content/rules/clarifications.md#rcl-022-an-attack-on-land-that-was-chinese-at-the-start),
reported by the owner on 22 November 2026). The engine counts every nation
except the KMT, the CCP, Dadao and the warlords as foreign (`invadesChina` in
`src/politics.cpp`). It does not count an attack on a zone that Dadao holds,
which rule 4.9 leaves out by pointing to rule 15.4 (page 105).

The two foreign nations of this campaign, one a major power and one a minor
power:

| | A foreign major power | A foreign minor power |
| --- | --- | --- |
| In this campaign | Japan | Mongolia |
| Which zones of original Chinese land it may attack | Any zone whose holder the declaration-of-war table of rulebook 5.1 (pages 35 and 36) lets it attack: for Japan, which may declare war on every nation outside the Axis, any zone held by such a nation or by nobody | A zone whose holder is already at war with it, or that nobody holds: the major power that controls a minor power may move its units in combat only against nations the minor power is already at war with (rulebook 4.5, page 27). This is the owner's reading; the developers' answer is about the wars the attack starts |
| The wars the attack starts | With the KMT, the CCP and every warlord still unaligned, except a nation of its own alliance: for Japan, with all of them | With the KMT and every warlord still unaligned, never with the CCP, which is in Mongolia's alliance (rule 4.3, page 26). Rule 4.5 forbids a controlled minor power any action that puts it at war with a nation it is not at war with yet; the developers allow these wars all the same |
| The warlords still unaligned | Each joins a side at the end of the attacker's Combat Phase ([section 2](#2-the-warlords)) | The same: rule 4.9 does not ask whether the attacker is a major power |
| The Chinese Truce | The CCP and the KMT may agree to it at the end of the attacker's Combat Phase (rule 6.6, page 42; rule 14.3, page 101; [section 3](#3-the-chinese-truce)) | Not offered: rules 6.6 and 14.3 name only a foreign major power |

Rule 14.3 (page 101) adds that no nation other than the KMT, the CCP and Dadao
may enter original Chinese land without a declaration of war, even where the
zone is friendly. So a foreign nation cannot move into original Chinese land as
a friend: Mongolia, whose invasion never makes it the CCP's enemy, never enters
land the CCP holds.

An attack by the KMT, the CCP or Dadao on original Chinese land is no invasion,
because those three are Chinese: it starts only the war that the attacker's row
allows in the table of who may start a war, near the top of this section. Rule
4.5 does not bind the KMT and the CCP, which have national reference sheets of
their own (page 27), and rule 15.4 (page 105) lets Dadao attack Chinese land
without the rest of China picking sides.

**Mongolia in the full game.** In this campaign Mongolia stays a nation of its
own when it is attacked. In the full game it would stay one only when the KMT
attacks it: an attack by anyone else makes it align with the USSR at the end of
the attacker's Combat Phase (rulebook 4.7, page 29), and a minor power that
aligns is incorporated into the major power (rulebook 4.6, page 28). This
campaign has no USSR and turns that alignment off (`mongolia_campaign_override`
in `game_content/rules/gw36_politics_v43.json`), so here Mongolia can be at war
with Japan, where in the full game it would by then be Soviet. The developers
named Mongolia and the Allies: an attack by a nation of the Allies spares the
KMT. Their rule, war with every Chinese nation outside the attacker's alliance,
would spare the CCP in a Soviet attack too.

**What the engine does.**

- `invadesChina` (`src/politics.cpp`) says whether an attack on a zone is an
  invasion of China, and `recordLandAttack` then puts the attacker at war with
  the KMT, the CCP and every warlord still in the game, except a nation of the
  attacker's own alliance (`chinaInvasionTarget`, same file).
- A land move (`landAccess` in `src/movement.cpp`), an air attack or airborne
  assault (`src/air.cpp`) and a landing from the sea
  (`src/naval_operations.cpp`) into original Chinese land are offered where the
  zone's holder allows an attack: for Mongolia, a holder already at war with
  it, or none.
- So Japan and Mongolia may each attack original Chinese land. In the engine's
  test `anInvasionOfChinaSparesTheInvadersAlliance`
  (`tests/politics_tests.cpp`), Mongolia is at war with the KMT and Japan, and
  a Mongolian cavalry in Central Mongolia may not attack Tsinghai while the Ma
  Clique, Tsinghai's warlord at the start, holds it. It may attack Tsinghai
  when the KMT or nobody holds it, Suiyuan, which was Mengjiang's and which
  Japan holds, and Kobdo, a Mongolian zone the KMT has taken. Its attack on
  Suiyuan puts Mongolia at war with every warlord and never with the CCP, and
  then it may attack the Ma Clique in Tsinghai.
- `beginCombatPoliticalResolution` (`src/politics_warlords.cpp`) offers the
  Truce only when the attacker is a major power and the attack started a new
  war with the KMT or the CCP.

## 2. The warlords

The eight warlords start unaligned: nobody plays them, they take no turn and
they have no money. If one is attacked, the Allies choose its casualties and
retreats for that battle.

A warlord that joins a nation stops existing as a nation of its own: its land,
its units and anything it was building become that nation's
(`incorporateNation`). Land gained this way may be entered the same turn, unlike
land that was captured. A warlord joins a side in one of four ways.

**A foreign power invades China.** An invasion of China
([section 1](#invading-china)) puts the invader at war with the KMT, the CCP
and every unaligned warlord at once, and every such warlord picks a side at the
end of that Combat Phase. All
the warlords' neighbours are noted first, so that one warlord's result cannot
change another's odds. Each warlord gets one roll of a twelve-sided die for all its land, since the
whole warlord joins one side, as the game's developers have clarified
([RCL-003](../../game_content/rules/clarifications.md#rcl-003-whole-warlord-alignment-after-foreign-invasion),
reported by the owner on 22 November 2026; the rulebook's table says "For each
land zone, roll a D12", section 4.9, page 30):

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
warlord only once the CCP has been eliminated ([section 1](#1-war)), so an
attack while the CCP has no units brings the CCP back.

**Influence.** In its Place Units Phase, Japan, or the CCP while it is a minor
power, may try once to win over an unaligned warlord (`influence_roll`): the
CCP by its Spreading Influence (rulebook section 15.2, page 104; CCP sheet,
page 3), Japan by its Dadao Government (section 15.4, page 105; Japan sheet,
page 4).

- **Who can be targeted:** a warlord whose land borders zones the nation
  controls, at least one of them holding a unit that has stood there since the
  turn began. The number of those bordering
  zones is the *threshold*.
- **The roll:** one twelve-sided die. Before rolling, the nation may pay IPP,
  at most the threshold and at most its treasury; each IPP lowers the roll by
  one. The action names the warlord and the amount.
- **The cap on the payment** is the threshold, the highest roll that succeeds
  without payment. The printed rules call it "the amount of its original
  influence roll"; the payment comes before the roll, so no die has been rolled
  and the words can only mean the number the roll is compared with
  ([RCL-002](../../game_content/rules/source_answered_questions.md#rcl-002-influence-spending-before-the-die-roll),
  closed after checking on 22 November 2026).
  Paying the most the cap allows doubles the rolls that succeed: with a
  threshold of 3, rolls of 1 to 3 succeed unpaid, and rolls of 1 to 6 after
  paying 3 IPP.
- **Success:** the lowered roll is at most the threshold. The warlord joins the
  CCP, or, for Japan, joins Dadao, which the first success creates.
- **A natural 12** always sends the warlord to the KMT instead, whatever was
  paid.

## 3. The Chinese Truce

The Truce is a ceasefire between the KMT and the CCP against an invader. In 240
random games it was never offered
([record](../archive/records/move_census_2026_11_14.md)), so the engine's tests
are the only evidence for this part.

- **When it can be signed.** A major power invades China
  ([section 1](#invading-china)), and the invasion starts a new war with the
  KMT or the CCP (rulebook 6.6, page 42). At the end of that Combat Phase, after the warlords have picked
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
13 IPP, even in the middle of another nation's turn. Its alliance then gets
one decision (`politics_evolution`): which of its zones becomes its capital,
and whether to take a free factory there (`politics_choose_capital`). A zone it
loses before choosing drops off the list of legal actions.

From then on the nation may move and attack outside the Chinese Home Country
and declare war on any major power. The CCP loses its minor-power recruitment
and influence, and the KMT loses its Low Morale
([land combat](land_combat.md)). An active Truce ends.

## 5. Capturing land

A battle that leaves a land unit of the attacker in the zone captures it
(rulebook 10.10, page 73; `captureLand`).

- **What is removed.** Fortifications and coastal artillery in the zone, and
  anything under construction there (10.10, page 73).
- **A capital.** If the zone was its holder's capital, the holder's treasury
  falls to zero (10.10.2, page 73).
- **Units of a third nation** that were in the zone as friends of the old
  holder must move to friendly land (`politics_relocate_neutral`), and are
  removed if there is none (RCL-015).

### Who gets the captured zone

Rule 10.10.1 (page 73) decides who holds the captured zone. It looks at the
attacker and at the zone's original owner, the nation whose roundel is printed
on the zone (glossary, page 7). The first row that fits applies:

| The attacker | The captured zone | Who holds the captured zone |
| --- | --- | --- |
| Any nation | Originally belonged to another major power of the attacker's alliance, which has not surrendered | That major power: the attacker must return the zone at once |
| A major power | Lies in the Chinese Home Country, and the attacker did not originally own it | The attacker decides at once: it keeps the zone (`politics_keep_capture`) or gives it to the KMT or the CCP (`politics_give_capture`) |
| Any nation | Any other zone | The attacker |

The Chinese Home Country is every land zone originally with a warlord's, the
KMT's, the CCP's, Manchukuo's or Mongolia's roundel, with Formosa and Hong Kong
(glossary, page 6). In this campaign it is 25 zones
([scenario](scenario.md#2-nations-and-alliances)): 10 of the warlords, 5 of the
KMT, 1 of the CCP, 4 of Mongolia, and 5 of Japan, which are Formosa and the
four Manchukuo zones. The campaign's map data (`map.json`) records Japan as the
original owner of those five, in line with the glossary's entry for Japan
(page 7), which takes in every zone marked with a Manchukuo roundel. Hong Kong
is not on the campaign's map.

**When the attacker may give the zone away.** Rule 10.10.1 allows the gift of
the table's second row only if the attacker and the receiving nation are
aligned, or if the attacker's units in the captured zone can move to friendly
land or aboard a naval transport in the Noncombat Movement Phase that follows.
Rule 11.1 (page 74) lets the attacker's units move in that Noncombat Movement
Phase although they moved in Combat Movement. Two nations of one alliance are aligned when they are at war
with the same major power (4.6, page 27), and the KMT and the CCP align with
nobody until they become major powers (14.3.1, page 101). The engine offers no
gift to a nation that has surrendered, since 10.10.1 lets no surrendered
nation have land liberated.

**In this campaign:**

- **Japan** is the only major power that is not Chinese
  ([scenario](scenario.md#2-nations-and-alliances)). Japan makes the second
  row's decision whenever it captures one of the 20 zones of the Chinese Home
  Country that it did not originally own, Mongolia's four included. Japan is
  never aligned with the KMT or the CCP, so a Japanese gift always needs the
  Japanese land units in the captured zone to leave it: `captureLand` offers
  `politics_give_capture` only when every one of those units can leave in that
  turn's Noncombat Movement, on foot or aboard a transport, and the Noncombat
  Movement Phase cannot end until they have left
  ([movement](movement.md#6-leaving-land-that-was-given-away)).
- **Dadao**, a minor power of Japan's alliance (4.3, page 26), must return to
  Japan any zone that was originally Japan's, such as Formosa or a Manchukuo
  zone, that Dadao captures: the table's first row.
- **A minor power** (the KMT or the CCP before it becomes a major power,
  Mongolia, Dadao) keeps every zone it captures that the table's first row
  does not return to a major power: the table's third row. During a Truce, the
  KMT or the CCP that retakes a zone of the Chinese Home Country from a foreign
  nation keeps that zone, even one that was originally the other's (6.6,
  page 42). In the engine that is the third row too, as the KMT and the CCP are
  both minor powers while a Truce lasts ([section 3](#3-the-chinese-truce)).

A Japanese gift can end a Truce. In the engine's test
`japaneseCaptureGiftCanEndAnExistingTruce` (`tests/land_truce_tests.cpp`),
Japanese armor in Beiping takes Hopeh from the CCP during a Truce and gives
Hopeh to the KMT, whose land was worth 12 IPP. With Hopeh the KMT's land is
worth 13 IPP, so the KMT becomes a major power (14.3.1, page 101), which ends
the Truce (6.6, page 42): a battle starts in Nanking, where KMT and CCP units
had stood together. In Noncombat Movement the armor goes back to Beiping.

**The KMT and the CCP as major powers keep what they capture.** Read
literally, the table's second row would also let a KMT or a CCP that has
become a major power give away Chinese Home Country land it captured, for
example the KMT giving a captured zone to the CCP, which it is at war with. On
the project owner's ruling of 28 October 2026, `captureLand` offers the
decision only to a major power that is neither the KMT nor the CCP, so neither
can hand its conquests to the other.

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

## 8. The kinds of action

| Kind of action | Phase | Chosen by | What it does |
| --- | --- | --- | --- |
| `politics_declare_war` | any, out of turn | the declaring alliance | Declares war on a major power |
| `politics_priority_declare`, `politics_priority_decline` | when another alliance declares | the alliance whose turn it is | Declares first, or lets the declaration through |
| `truce_offer`, `truce_decline_offer` | end of Combat | the Comintern, for the CCP | Offers the Truce or not |
| `truce_accept`, `truce_reject` | end of Combat | the Allies, for the KMT | Accepts or refuses the offer |
| `truce_break` | Combat | the Chinese nation whose turn it is | Ends the Truce and starts the battles |
| `politics_choose_capital` | at 13 IPP | the alliance of the new major power | Names the capital and takes the factory or not |
| `politics_keep_capture`, `politics_give_capture` | Combat | the Axis, for Japan | Keeps captured Chinese land or gives it away |
| `politics_relocate_neutral` | Combat | the owner of the units | Moves units out of a captured zone |
| `influence_roll` | Place Units | Japan's or the CCP's alliance | Tries to win over a warlord |
| `recruitment_roll` | Place Units | the alliance of the nation whose turn it is | Rolls to recruit |
| `recruitment_place_infantry`, `recruitment_place_militia`, `recruitment_advance_ship`, `recruitment_repair_facility` | Place Units | the same alliance | Takes what the roll gave |

## 9. What a nation can ever be

Whatever happens in a game, the rules above make only some things possible for
each nation: only some power statuses, alliances, controllers, wars and allies,
and only for some nations a promotion to major power, a surrender, an invasion
of China or a recorded attack on a warlord. Some facts never change at all:
which nations are in the game, and the war between the KMT and the CCP. The functions declared at the top of
`include/game/politics.hpp` state what is possible, and the reason for each is
beside its definition in `src/politics.cpp`. The network's input has only the
features they allow
([the network's input](../design/network_input.md#what-the-global-features-ask-about-a-nation)),
and leaves out a fact that can have only one value, so a rule change that makes
something new possible for a nation must change its function too.

| Function | What it states |
| --- | --- |
| `canEvolve`, `canBeMajorPower` | Only the KMT and the CCP are promoted. With Japan they are the only possible major powers. |
| `powerStatusPossible` | Japan is always a major power, Mongolia and Dadao are always minor powers, and a warlord is always a warlord. |
| `alliancePossible` | A nation keeps its alliance and its player for good. Only a warlord's change, to those of the nation that incorporates it. |
| `controllerPossible` | A warlord is under nobody, or under the nation that incorporated it: the KMT, the CCP, Dadao, or Japan once Dadao has joined Japan. Dadao is under Japan, or under nobody if Japan surrenders first. |
| `canSurrender` | Only the KMT and Japan surrender. |
| `canInvadeChina` | Japan and Mongolia, the nations that are not Chinese, are recorded as invading China ([invading China](#invading-china)). |
| `warPossible` | Japan and Dadao, both in the Axis for good, are never at war, nor are the CCP and Mongolia, both in the Comintern. A warlord is at war only with Japan, the CCP, Dadao or Mongolia: it declares no war, and one the KMT attacks joins the CCP at once. Mongolia is at war only with Japan or the KMT, the nations that may declare war on it, a warlord, by invading China, or Dadao, once Dadao has won over a warlord at war with Mongolia and taken over that war. |
| `alliesPossible` | Only the KMT and the CCP are ever allies. |
| `warlordAttackPossible` | A warlord is recorded as attacked by Japan, the CCP, Dadao or Mongolia, the nations that can be at war with it. The KMT's attack makes the warlord join the CCP at once and is not recorded. |
| `alwaysInGame` | Every nation but Dadao is in the game from setup to the end: setup creates them, and no code removes a nation, not even one incorporated. Dadao is created when Japan first wins over a warlord (`ensureDadao`). |
| `alwaysAtWar` | The KMT and the CCP are always at war: setup puts them at war, and only `incorporateNation` ends a war, never for either of them. Under the Chinese Truce they are friends while the war stays recorded. |

Tests: `tests/politics_tests.cpp`, `tests/politics_warlords_tests.cpp`,
`tests/politics_influence_tests.cpp` and `tests/land_truce_tests.cpp`; the
functions of section 9 are checked through the network's input, in
`tests/zone_encoding_tests.cpp`. The
printed page behind each rule is recorded beside the rule in the rules data
([where the numbers come from](../rules/README.md#where-the-scenarios-numbers-come-from)).
