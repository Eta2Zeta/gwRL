# GW36 v4.3 rule clarifications and open questions

Updated: 23 November 2026.

This is the project's shared register of **unclear official rules**, including
interpretations adopted after discussion. It is **not publisher-issued errata**.
An adopted project clarification is not evidence that the publisher endorsed it.
Record each rule conflict with its source, decision and developer clarification
status. Implementation details belong in the
[engine documentation](../../docs/engine/README.md).

Campaign-specific exclusions, controllers, setup choices and reward definitions
belong in the
[approved scenario decisions](../../docs/plans/japan_china_full_rules_plan.md#approved-scenario-decisions),
not here. Map-reading uncertainties remain in the
[map notes](../README.md) and map audits;
uncertain artwork is not automatically an error in the official rules.

## Status and source conventions

- **Adopted:** the user has settled an interpretation for the project.
- **Proposed:** the audit recommends a reading, but it has not been approved as
  a shared rule clarification.
- **Open:** the official question remains unresolved here. A scenario may have
  its own explicit convention without settling the general rule.
- **Closed after checking:** the source already answers the question, or the
  supposed conflict was an error in our earlier audit.
- **Closed — developer fix reported:** the user reports that the developers
  resolved the issue for the next version. Record the report and date separately
  from any subsequently published correction.
- **Closed — developer clarification reported:** the user reports that the
  developers clarified the rule. Record the clarified rule and report date.

`RB` means [Global War 1936 v4.3 Rulebook](<Global War 1936 v4.3 Rulebook.pdf>);
its printed and PDF page numbers coincide. `Japan`, `CCP` and `KMT` mean their
v4.3 national reference sheets, using one-based PDF pages:
[Japan](<GW36 - NRS - Japan v4.3.pdf>),
[CCP](<GW36 - NRS - CCP v4.3.pdf>),
[KMT](<GW36 - NRS - KMT v4.3.pdf>).
Discord messages are community evidence unless publisher authority is verified.
A new entry requires a genuine omission or incompatible applicable rules after
checking definitions, examples, cross-references and national exceptions.
Source-answered questions are kept in the [archived checks](source_answered_questions.md),
including retired IDs RCL-002, RCL-006, RCL-007, RCL-008 and RCL-011.

## Issue index

| ID | Official-rule question | Status |
| --- | --- | --- |
| RCL-001 | Airborne assault: AAA appears in steps 4 and 5 | Closed: developer correction for v4.4; both sides fire in step 4 |
| RCL-003 | Foreign invasion: alignment of a whole warlord | Closed: the whole warlord aligns, one roll per warlord; developer clarification reported by user |
| RCL-004 | CCP purchases: railroad versus supply-path wording | Closed: developer fix for next version, reported by user |
| RCL-005 | Blockade: enemy surface warships versus any enemy units | Closed: only enemy Surface Warships prevent a blockade; developer clarification reported by user |
| RCL-009 | Japan-Soviet border clashes: named zones or broader borders | Adopted: Japan reference-sheet target list |
| RCL-010 | Dadao lend-lease: recipient has no original Home Country | Adopted: Dadao-possessed Chinese Home Country destinations; pending developer clarification |
| RCL-012 | Chinese Truce combat and retreat | Closed: developer-confirmed roles; same KMT elimination after voluntary or automatic termination |
| RCL-013 | Does artillery city bombing use attrition's range and movement restrictions? | Adopted: use the same starting-adjacency and no-movement conditions |
| RCL-014 | Combat roles when ships evacuate into a third party's fleet | Closed: evacuating fleet defends; fleet already at sea attacks; developer clarification |
| RCL-015 | Neutral units required to relocate with no Friendly land remaining | Provisionally adopted: eliminate units with no Friendly relocation destination |
| RCL-016 | KMT Low Morale 10+ with no legal retreat, such as after an amphibious assault | Closed: the unit is eliminated; developer clarification reported by user |
| RCL-017 | May a patrol plane that let ships pass still fight them later that turn? | Adopted, revised the same day: yes, if they attack it anew; it then chooses again whether to fight |
| RCL-018 | Amphibious assault whose sea zone is not cleared, or whose transports retreat | Adopted: the assault is called off; the cargo stays aboard |
| RCL-019 | Several railroads on one border; the damage limit and repair of each side | Adopted: one railroad per border; each side holds its own damage and is repaired by its possessor |
| RCL-020 | A patrol plane attacked in its own sea zone: the carrier choice or the patrol choice, before or after scrambles | Adopted: the patrol choice, made before any scramble; staying out costs nothing |
| RCL-021 | Upgrading a unit aboard a transport into one the transport may not carry, or aboard a ship at sea | Adopted: neither allowed; the upgrade waits on the build queue |
| RCL-022 | An attack on land that was Chinese at the start: when a nation outside China holds it, and when the attacker may not go to war with all of China | Closed: the printed owner decides; the attack puts the attacker at war with every Chinese nation outside its own alliance, and Mongolia may make it; developer clarification reported by user |
| RCL-023 | A land battle that no unit can end: the attacker's remaining units can neither fire nor retreat, and the defender's cannot fire | Adopted: the attacker retreats, and its units with nowhere to go are eliminated |

## Pilot discussion review

The [26 August–26 September 2025 audit](discord_audits/2025-08-26_2025-09-26/README.md)
reviewed all 1,129 visible messages and their attachment context. No additional
genuine missing rule, verified fix or confirmed unresolved conflict qualified.
The entries below come from the earlier register, outside those pilot dates.
The [HTML rules reader](html/index.html) places these notes beside the source rules,
with separate colors and explicit authority labels.

## RCL-001: AAA in the airborne-assault sequence

**Status: closed — developer correction for v4.4, posted 6 October 2026; applied to this project at the user's request, 23 October 2026.**

**Sources:** RB §10.6.1 pp65–66; [developer's corrected sequence](https://discord.com/channels/876158750870863964/1409991574292795392/1557027622016516186).

**Correction:** both sides' Fighters and AAA resolve in step 4; each AAA fires
once. Step 5 moves the surviving transporting aircraft to a suitable landing
spot. It does not give defending AAA another volley.

In steps 3 and 4, airborne infantry and its transporting aircraft are linked:
selecting that casualty destroys both and counts as one casualty. Destroyed cargo
does not land or attack.

## RCL-003: whole-warlord alignment after foreign invasion

**Status: closed — developer clarification reported by the user, 22 November
2026.** The user had adopted the same reading on 5 October 2026.

**Sources:** RB §4.9, pp30-31.

**Problem:** RB §4.9 p30 says that an attack by a foreign nation causes all
warlords to Align, each with the CCP, the KMT or the Dadao Government according
to the factions it borders, and then introduces the table with "For each land
zone, roll a D12", as if each land zone of a warlord could go its own way.

**Clarified rule:** the user reported on 22 November 2026 that the game's
developers have closed this question: the entire warlord aligns. Resolve
foreign-invasion alignment for each **whole warlord**, with one roll whenever
the alignment table calls for a roll. Determine the qualifying neighboring
factions across all territories belonging to that warlord, select the
corresponding existing table category, and apply the single result to the
entire faction and its surviving forces. Preserve the table's automatic KMT
outcome where no qualifying CCP/Dadao neighbor exists.

Beiping/Hopeh form one warlord for this procedure, as do Kwangtung/Hainan.
Foreign-invasion alignment and ordinary CCP/Japanese influence retain their
distinct triggers, eligibility, probabilities and timing; both keep the warlord
intact. This is the shared rule, not a campaign-only exception.

## RCL-004: CCP Comintern Brothers, rail versus supply

**Status: closed, 17 October 2026.**

**Resolution:** the user spoke with the developers and reports that they have
fixed the wording for the next version. This closes the issue; it is no longer
classified as an adopted project interpretation.

**Sources:** RB §15.2, p103; CCP p3 ability text and minor build chart.

**Problem:** the full ability requires an undamaged railroad from CCP-possessed
land to Soviet-possessed land during Production; the same national sheet's
purchase notes say supply path.

**Recorded rule:** use the specific railroad condition and its placement
restriction; a sea-only or river-only supply path does not unlock Artillery/AAA
purchases.
Do not confuse this Soviet-**possessed** land requirement with the separate
income bonus's Soviet **Home Country** requirement (CCP p2).

## RCL-005: what prevents a blockade?

**Status: closed, 18 October 2026.**

**Resolution:** the user clarified this with the developers and reports that
only enemy **Surface Warships** prevent a blockade under the enemy-presence
condition. The broader naval-unit summary wording does not expand that condition
to every enemy unit type.

**Sources:** RB §9.4.6, p60 versus §13.1.6, p89.

**Problem:** the detailed blockade rule excludes enemy Surface Warships from
the sea zone; the naval-unit summary instead excludes any enemy units.

**Clarified rule:** follow the detailed §9.4.6 condition. Enemy submarines alone do
not prevent a qualifying surface fleet from blockading. Preserve the fleet
size/alliance requirements and coverage of every sea access of a shared facility.

## RCL-009: Japan-Soviet border-clash geography

**Status: adopted by the user, 21 October 2026. The geography question is
resolved by following Japan's national reference sheet.**

**Sources:** Japan p1; RB §10.5.2, pp64-65.

**Adopted resolution:** treat Japan's printed border-clash target list as
exhaustive. Japanese border-clash attacks may target Soviet units only in
**Chita, Amur and Primorsky Krai**. Soviet possession of another territory,
including incorporated Mongolian territory, does not add that territory to
Japan's permitted target list.

Retain the shared-border, unit-eligibility, single-round, no-conquest and
Japanese-Soviet Non-Aggression Pact restrictions in §10.5.2. This resolution
follows Japan's attack permissions; it does not create a new list of permitted
USSR attack origins. The mechanic remains inactive in the current campaign
because USSR is excluded.

## RCL-010: Dadao Home Country destination for Japanese lend-lease

**Status: adopted by the user, 22 October 2026; pending developer clarification.**

**The question.** The rules let Japan send lend-lease to the Dadao Government,
but they deliver lend-lease only into the receiving nation's Home Country, and
Dadao has none. Where does Japan's lend-lease to Dadao arrive, and where does
Dadao place a lend-leased base or Militia upgrade?

**What the rules say.**

1. **The gift is allowed.** RB §8.7 (p52) gives each sender's lend-lease
   conditions in a table. For Japan it lists the Dadao Government with a plain
   "Yes", while any other recipient must be at war with a Major Power. Japan p4
   and RB §15.4 (p105), under Dadao Government, say the same in words: as long as
   Japan controls Dadao, Dadao may receive lend-lease from Japan. Japan's own
   lend-lease table (Japan p3) has a single row, any nation at war with a Major
   Power, and does not name Dadao; the Dadao Government ability on the next page
   adds it.
2. **Lend-lease arrives only in the receiving nation's Home Country.** RB §12.4
   (p80): the delivery starts in the sender's Home Country and moves along a
   Supply Path to a land zone in the receiving nation's Home Country, and it
   stops in the first land zone of that Home Country which the receiver
   possesses. A lend-leased base or Militia upgrade goes to the receiver's build
   queue and is placed anywhere in the receiver's Home Country in its next Place
   Units Phase. Lend-lease that cannot be delivered waits on the build queue and
   is tried again the next Player Turn.
3. **Dadao has no Home Country.** RB p6 (Home Country) lists the Home Country of
   each nation it names; Dadao is not among them. A nation not listed has as its
   Home Country all its Originally possessed land zones except offshore ones.
   RB p7 (Originally) means since the start of the game: the nation whose roundel
   is printed in the land zone on the map. No land zone carries a Dadao roundel.
   Dadao comes into being during play, when Japan's influence roll succeeds on a
   Chinese warlord and that warlord's land zones and units become or join the
   Dadao Government (Japan p4; RB §15.4, p105). After a foreign invasion of
   China, a warlord bordering Dadao's land may also align with Dadao (RB §4.9,
   pp30-31). So Dadao originally possesses no land zone, and its Home Country is
   empty.
4. **The land zones Dadao holds belong to China's Home Country.** RB p6 gives
   the CCP and the KMT one Home Country: every land zone originally with a
   Chinese warlord, KMT, CCP, Manchukuo or Mongolian roundel, with Formosa and
   Hong Kong. Every land zone that Dadao gets from a warlord, or takes from the
   KMT or the CCP, is therefore in Chinese Home Country.

Read literally, these rules let Japan declare lend-lease to Dadao but give the
delivery no land zone to arrive in, so it would wait on Japan's build queue for
the rest of the game. Dadao's recruitment has no such gap: a recruited unit is
placed in a land zone that Dadao has possessed since the beginning of the Player
Turn, with no mention of a Home Country (RB §12.7, p82).

**Another reading the developers might give.** The Dadao ability says that the
first warlord's land zones become the Dadao Government. If Dadao took over that
warlord's roundel, it would originally possess that warlord's printed land
zones, and its Home Country would be those zones, less any offshore one, and no
others: not the land zones of warlords that join it later, nor those it takes
in battle.

**Adopted project ruling.** Japan's lend-lease to Dadao may be delivered to any
land zone that Dadao possesses within Chinese Home Country, and a delivered base
or Militia upgrade is placed in such a land zone. Everything else in RB §12.4
still applies: the delivery starts in Japan's Home Country and needs a real
Supply Path, the naval facilities it uses must be undamaged and possessed since
the beginning of the Player Turn, blockades and interdiction apply, and Japan
sends Dadao at most one lend-lease a Player Turn (RB §8.7, p52). The ruling does
not give Dadao a Home Country for any other rule. The user will report the
question to the developers; this is a user-approved campaign interpretation,
not a reported developer ruling.

**What the program does.** `lendLeasePermitted` (`src/economy_lendlease.cpp`)
allows Japan's lend-lease to Dadao while Japan controls Dadao.
`lendLeaseSupplyRoute` (`src/movement.cpp`) and `recipientHome`
(`src/economy_lendlease.cpp`) accept as the destination a land zone that Dadao
possesses in Chinese Home Country, while Dadao's own Home Country stays empty
(`src/campaign_setup.cpp`). For example, once a successful influence roll has
brought the warlord of Beiping and Hopeh over to Dadao, Japan's lend-lease to
Dadao may arrive in Beiping or Hopeh, by a Supply Path from Japan's Home
Country.

**The question for the developers.** The Dadao Government has no printed roundel
and so no Home Country. Where is lend-lease from Japan to Dadao delivered, and
where does Dadao place a lend-leased base or Militia upgrade?

## RCL-012: Chinese Truce combat and retreat

**Status: closed, 22 October 2026. Third-party roles are developer-confirmed as
reported by the user; applying the same Low Morale consequence after automatic
termination is the user's clarification.**

**Sources:** RB §0.2 p5; §6.6 p42; §10.3 p62; §10.10.1 p73; §15.7 p107;
city/tundra limits, pp12-13.

**Resolved rules:**

- On CCP's or KMT's turn, the active faction attacks and the other defends,
  regardless of land possession.
- **Developer clarification:** when a third party triggers evolution, the
  possessor of the shared land defends and the other Chinese faction attacks.
- Eligible attacking minor-KMT regular Infantry and Cavalry in shared zones
  are eliminated on their attack rolls of 10+. This applies after both voluntary
  and automatic termination. There is no additional preliminary roll.
  Defending KMT does not suffer Low Morale; Major-Power KMT is exempt.

**Related clarification:** the
[26 February Discord announcement](https://discord.com/channels/876158750870863964/1409991574292795392/1476578711062057104)
reports a v4.4 amendment granting possession to the surviving faction, including
a victorious defender. The
[22 June discussion](https://discord.com/channels/876158750870863964/1409991574292795392/1518702751113150535)
also identifies the voluntary breaker as attacker.

## RCL-013: Applying attrition restrictions to artillery city bombing

**Status: adopted by the user, 22 October 2026.**

**Sources:** RB §10.5.3 p65; §10.6.2 pp66-67; §13.1.3 p86.

**Already explicit:** attrition attacks require adjacency since the start of the
Player Turn, last one combat round, allow no defending return fire, ignore terrain
modifiers, and prohibit movement that turn. Their attack value is 2, reduced by
fortifications. Ordinary attrition needs no clarification.

**Adopted rule:** Advanced Artillery's city bombardment uses the same
starting-adjacency and no-movement conditions as attrition: remain in the original
zone and fire at a city adjacent since the Player Turn began. City bombardment
still deals 1D6 strategic damage under §10.6.2 and §13.1.3; it does not use the
attrition hit-at-2 roll against units.

## RCL-014: Third-party combat after damaged-port evacuation

**Status: closed — developer clarification supplied by the user, 23 October 2026.**

**Sources:** RB §0.2 p5; §11.5 p78; user-provided screenshot of The Warden's
Discord explanation, 23 October 2026 (direct message link not supplied).

**Clarified rule:** when damaged-port evacuation forces combat, the evacuating
fleet defends and the enemy fleet already at sea attacks, including during a
third nation's turn. This replaces the earlier provisional ruling.

The developer's example is German bombing that forces Commonwealth ships to
fight Italian ships outside the port. Applying the same roles to KMT evacuation
into CCP ships during Japan's turn extends that principle to three alliances;
that exact example was not in the developer's message.

## RCL-015: Neutral relocation with no Friendly destination

**Status: provisionally adopted by the user, 23 October 2026; pending developer clarification.**

**The question.** When an attacker takes a land zone, units in it that did not
take part in the battle are moved to the nearest Friendly-possessed land zone
(RB §0.3, p8). What happens to them when no such land zone exists anywhere?

**How the case comes about.** Units of two nations share a land zone only when
the two are Aligned, or when the CCP and the KMT have signed the Chinese Truce
(RB §0.3, p8). On this campaign's map only the Truce brings it about: until it
becomes a Major Power the CCP aligns with no one (CCP p1), and the program
merges a minor power that aligns with another nation into that nation
(`incorporateNation` in `src/politics.cpp`), so no other two nations share a
land zone. The case needs every step below.

1. **A foreign Major Power declares war on China, and the CCP and the KMT sign
   the Chinese Truce** (RB §6.6, p42). Under the Truce each may move freely in
   the other's land zones, so CCP units may stand in KMT land.
2. **The CCP loses all its own land but keeps units** in KMT land. The CCP
   never surrenders (CCP p1), so it stays in the game with units and no land.
3. **A nation at war with the KMT but not with the CCP attacks the KMT land
   zone where those CCP units stand.** Dadao can be that nation: its attacks on
   Chinese land are not a declaration of war on all of China (RB §4.9, p30;
   RB §15.4, p105), so if the KMT has attacked Dadao and the CCP has not, Dadao
   is at war with the KMT alone. Mongolia can be another: an attack of its own
   on Chinese land puts it at war only with the Chinese nations outside the
   Comintern, its alliance and the CCP's (RCL-022). The CCP units sit out the
   battle unless the CCP or the attacker declares war (RB §0.3), and neither can
   then. Against Dadao, Japan may not put Dadao into a war it is not already in
   (RB §4.5, p27), and the CCP declares war on a Minor Power only by moving land
   units to attack it (RB §5.1, p35), which it cannot do in another nation's
   turn. Against Mongolia, no nation may declare war on a member of its own
   alliance (RB §5.1).

   In this campaign the attacker cannot be a Major Power. Japan is the only one
   while the Truce lasts, since a Chinese faction that becomes one ends the
   Truce (RB §6.6), and the program offers the Truce only after Japan has
   attacked a land zone Originally possessed by the CCP, the KMT or a warlord,
   which RB §4.9 (p30) counts as a declaration of war on all of China, the CCP
   included (`recordLandAttack` in `src/politics.cpp`,
   `beginCombatPoliticalResolution` in `src/politics_warlords.cpp`). CCP units
   in a KMT land zone that Japan attacks therefore defend with the KMT's units
   and are eliminated with them if Japan takes the zone. The campaign has no
   USSR: the Comintern plays Mongolia alone (`china_minor_setup.json`).

   In the full game the USSR can be the nation of this step, and the outcome
   could then differ. A Major Power of the Comintern, the CCP's alliance, it
   goes to war with the KMT but not with the CCP when it attacks KMT land
   (RCL-022), and neither it nor the CCP may declare war on the other
   (RB §5.1). A Major Power that conquers a land zone of Chinese Home Country
   it did not Originally possess must at once keep the zone or give it to a
   Chinese faction (RB §10.10.1, p73). The USSR may give it to the CCP if its
   conquering units can move to a Friendly land zone or naval transport in the
   following Noncombat Movement Phase, since the two are not Aligned (CCP p1).
   Given to the CCP, the zone is Friendly-possessed land for the CCP units
   standing in it, and they would need to move nowhere, if the gift comes
   before the move that RB §0.3 orders. The rules do not say which comes
   first.
4. **The attacker takes the zone.** The units that sat out must move to the
   nearest Friendly-possessed land zone, regardless of distance (RB §0.3). A
   land zone is Friendly to a nation that possesses it or is Aligned with its
   possessor (RB p6); the program counts KMT land as Friendly to the CCP while
   the Truce lasts, since the two move and defend together as if Aligned
   (RB §6.6).
5. **No Friendly land is left.** If the zone was the KMT's last, the KMT
   surrenders, as it does when it possesses no land zone (KMT p1). The CCP
   possesses none either, and no nation is Aligned with it. Mongolia's land
   does not count: Mongolia shares the Comintern with the CCP, but members of
   one Alliance are not Aligned by that alone (RB p5; RB p6 gives London, not
   Friendly to the USA until the two are Aligned), Mongolia Aligns only with
   the USSR (RB §4.7, p29), and the CCP Aligns with no one until it becomes a
   Major Power (CCP p1), which ends the Truce (RB §6.6). The program agrees
   (`politicallyFriendly` in `src/politics.cpp`). RB §0.3 names no other
   destination and no other outcome, and the CCP cannot surrender.

**Adopted ruling.** Units that RB §0.3 must relocate are eliminated, with any
units they carry, only when no Friendly-possessed land zone exists. Otherwise
the printed rule applies: they move to the nearest Friendly-possessed land zone,
and their owner chooses among equally near ones. The elimination is a
provisional project interpretation, not a developer-confirmed rule.

**What the program does.** `captureLand` (`src/politics.cpp`) sends the units
that sat out to `queueNeutralRelocation`, which looks for the nearest Friendly
land zones (`nearestFriendlyLand`). It moves a unit at once when one land zone
is nearest, lets the owner choose with `politics_relocate_neutral` when several
are, and with none eliminates the unit and its cargo and records the
elimination under RCL-015 (`destroyUnrelocatableNeutralUnit`). When a
conquest also gives a Major Power the choice of RB §10.10.1, `captureLand`
moves or eliminates these units before the Major Power answers it; in this
campaign only Japan has that choice, and its conquests leave no unit that sat
out. The test
`neutralRelocationWithoutFriendlyLandUsesAdoptedElimination`
(`tests/politics_warlords_tests.cpp`) plays the case above: under the Truce,
with the CCP's land in Japan's hands, Dadao takes the KMT's last land zone, in
which three CCP units stand, one of them an air transport carrying a fourth, and
all four are eliminated. In the 240 random games of 14 November neither the Truce
nor a relocation came up ([record](../../docs/archive/records/move_census_2026_11_14.md)).

**The question for the developers.** After a conquest, RB §0.3 moves units that
did not take part to the nearest Friendly-possessed land zone. When none exists,
as for CCP units in the KMT's last land zone, taken by Dadao while the CCP is
not at war with Dadao, what happens to those units? And when the conqueror is a
Major Power that may give the zone to a Chinese faction under RB §10.10.1, as
the USSR may give the KMT's last land zone to the CCP, does that choice come
before the move, so that CCP units in a zone given to the CCP stay where they
are?

## RCL-016: KMT Low Morale with no legal retreat

**Status: closed — developer clarification reported by the user, 21 November
2026.** The user had adopted the same ruling on 2 November 2026.

**Sources:** RB §15.7 p107 and KMT reference sheet p3 (Low Morale); §10.3 p62
and §10.8.3 p71 (no retreat from an amphibious assault); §§1.7.5 and 1.7.7
pp12-13 (city and tundra/ice round limits); §6.6 p42; the user's report of the
developers' clarification, 21 November 2026 (no message link supplied).

**Problem:** an attacking minor-KMT regular Infantry or Cavalry unit that rolls
10+ must retreat to the zone it attacked from. A unit that landed in an
amphibious assault attacked from a sea zone, and land units cannot retreat from
an amphibious assault. The Low Morale text does not say what happens when that
retreat is impossible.

**Clarified rule:** the unit is eliminated. The rest of Low Morale is
unchanged: a unit that can retreat to the zone it attacked from still does so,
it still cannot be taken as a casualty, and Major-Power KMT remains exempt.
When the user adopted the ruling on 2 November 2026, it followed the city and
tundra/ice rules, which eliminate attackers that must retreat but cannot, and
matched the 10+ elimination under the Chinese Truce (RCL-012).

## RCL-017: A patrol plane's second chance against ships it let pass

**Status: adopted by the user, 4 November 2026; found in random-play seed 9487
on 2 November. The user first adopted one decision per turn and reversed it
later that day, after weighing §0.3.**

**Sources:** RB §0.3 p9 (zone sharing); §9.3.1 pp55-56; §9.4 p57; §9.4.2 p58;
§10.4 p63; §10.8.1 p70.

**Question:** surface ships with no attacking aircraft enter a sea zone where an
enemy aircraft is on Maritime Air Patrol. The plane may fight them or let them
pass, and it lets them pass. Later in the same Combat Movement, may those ships
still offer the plane a battle, which it may then accept with scrambled support?

**Readings:**

- **One decision per turn (adopted first, then reversed):** the refusal
  settles combat with those ships for the turn. Ships without aircraft that can
  attack cannot force combat on a patrol plane (§§9.3.1 and 9.4), and §§9.4.2
  and 10.8.1 treat an aircraft on MAP "which declined combat" as out of the
  fight.
- **Two chances (adopted):** §0.3 lists a patrol plane's refusal among the ways
  units at war come to share a sea zone, and such units take no part in combat
  until one power makes a new combat move against the others there. The ships
  may make one; the plane, attacked again, may again decline or accept, and if
  it accepts its side may scramble units under §10.4. The engine allowed this
  second battle before the first ruling.

**Example:** in seed 9487 a captured KMT transport entered P16, where a Japanese
tactical bomber on patrol let it pass. Random play then engaged the bomber;
Japan accepted and scrambled a destroyer from Honshu's port, both missed, and
the transport retreated to P15.

**Adopted ruling (revised):** two chances.

- A patrol plane that lets ships pass shares its sea zone with them (§0.3). It
  takes no part in their screening battle there or the battle where their route
  ends, and it does not count against their screening (§9.4.2) or their
  amphibious assault (§10.8.1).
- The ships may still attack it in Combat Movement, a new combat move (§0.3).
  The battle is fought in the Combat Phase, where the plane chooses again by
  the patrol rule (RCL-020): it may stay out unless the Attacker has aircraft
  with an attack value present, and it chooses before any scramble.
- If it stays out, it has declined combat again. If it fights, it is no longer
  an aircraft on MAP which declined combat: if it survives, it stops an
  amphibious assault from its sea zone, which is then called off (RCL-018).
- Ships it has not let pass, such as ships that started the turn beside it,
  may engage it as before, and ships entering its zone later get a fresh choice.

In seed 9487 the second battle at P16 can therefore happen, with the bomber now
choosing before the Honshu destroyer may scramble.

**Authority:** the user in chat on 4 November 2026, first for one decision per
turn ("Refusal settles it"), then, after the conflict with §0.3 was raised:
"RCL 017 is wrong, it can accept later after it passed".

## RCL-018: An amphibious assault whose sea zone is not cleared

**Status: adopted by the user, 3 November 2026; found in self-play on the night
of 2 November (seed 4238465544019468396).**

**Sources:** RB §10.8.1 p70 (naval combat by the screening force); §10.4 p63
(scrambling); §10.8.3 pp70-71.

**Problem:** all Enemy Surface Ships and aircraft (except aircraft on MAP that
declined combat) in the sea zone an amphibious assault starts from must first be
eliminated, and defending players may scramble units into that sea zone. The
rules do not say what happens when they are not eliminated, for example when
the screening force retreats or ships scrambled into the sea zone survive.

**Adopted ruling:** the amphibious assault is called off. Its land units stay
aboard their transports for the rest of the turn. A transport that retreats
takes its cargo out of the assault, which still goes ahead with any cargo whose
transports remain in the cleared sea zone.

**Example:** a captured KMT transport carrying one Infantry sailed from P41 into
P32, where only Japanese submarines were, and declared an assault on Formosa.
In the naval battle in P32 Japan scrambled a light carrier and a destroyer from
Formosa's port, and the transport retreated to P41. Before this ruling the
engine could neither start nor drop the assault, and KMT had no legal move.

## RCL-019: One railroad per border, damaged and repaired by side

**Status: adopted by the user, 3 and 4 November 2026.**

**Sources:** RB §13.2.8 pp98-99 (railroads: placement, price, maximum damage,
repair cost); §10.6.2 p67 (strategic bombing of railroads); §1.6 p10.

**Problem:** a railroad is placed on a land-zone border and takes at most 1
damage in normal terrain or 2 in desert, jungle, marsh, mountain or tundra,
repaired at 1 IPP per point. The rules do not say whether a second railroad may
be built on a border that already has one; §10.6.2's "all railroads on that
border" suggests several are possible. Nor do they say whether the maximum
damage applies to each side of the border, or who repairs a damaged side.

**Adopted ruling:**

- A border has at most one railroad. Building a railroad is not offered on a
  border that already has one, damaged or not, or that has one under
  construction. A railroad is therefore named by the two land zones it connects.
- Each side of the border holds its own damage, up to the border terrain's
  maximum. A railroad with damage on either side cannot be used.
- The nation possessing the zone on a damaged side may repair that side, at
  1 IPP per point.

**Why one railroad per border changes no outcome:** a second railroad on a
border would give nothing that the first, repaired, does not. Bombing damages
every railroad on the border together (§10.6.2), so a second one gives no
protection, and repairing both sides at their maximum damage costs exactly the
building price: 2 IPP in normal terrain, 4 in difficult terrain. The one
difference is who pays: when the damaged side belongs to a friendly nation,
repairing it is that nation's decision and cost, while a new railroad would be
paid for by its builder. Building toward another nation needs that nation's
permission anyway.

The user's statement of 3 November gave the normal-terrain numbers: two damage,
one on each side. On 4 November the user confirmed the difficult-terrain case:
such a border takes up to 2 damage on each side.

**Example:** the railroad between Manchuria Northern and Manchuria Western is
`rail_land_manchuria_northern__land_manchuria_western`. In random-play seed 7004
it has 1 damage on the Manchuria Northern side, and Japan, possessing Manchuria
Northern, repairs that side for 1 IPP.

## RCL-020: A patrol plane attacked in its own sea zone

**Status: adopted by the user, 4 November 2026.**

**Sources:** RB §0.3 p9 (zone sharing); §9.3.1 pp55-56; §9.4 p57; §9.4.2 p58;
§10.1 pp61-62; §10.4 pp63-64 (scrambling); §10.7 p70 (naval combat sequence).

**Question:** ships already in a patrol plane's sea zone, such as ships that
started the turn there or survived its single round as they entered, may
attack it: the attack is declared in Combat Movement (§0.3) and fought in the
Combat Phase. The rulebook describes the plane's choice to fight only for ships
entering its zone. In this battle, does the plane choose as a patrol plane or
as an aircraft on a carrier (§10.7, step 2), and before or after its side
scrambles units into the battle (§10.4)?

**The engine before this ruling** gave the plane the carrier choice, after the
scrambles. Ships in port could scramble in, the plane could then stay out, and
a plane that stayed out was destroyed when its side lost, as a lone plane
always did. It offered that choice even against aircraft that could attack it.

**Adopted ruling:**

- The plane chooses by the patrol rule (§§9.3.1 and 9.4), not the carrier rule.
  It may stay out unless the Attacker has aircraft with an attack value
  present, and staying out costs it nothing: it stays in its sea zone, on
  patrol. Aircraft on carriers keep the choice of §10.7, step 2.
- It chooses before any scramble. If it stays out and no other unit of its side
  defends, there is no battle and nothing to scramble into, since §10.4 sends
  units into combat where their side has a defending unit. If other units
  defend, the battle goes on without the plane, and units may scramble to join
  them.
- A plane that stays out has declined combat again: it does not count against
  those ships' screening (§9.4.2) or their amphibious assault (§10.8.1).
- Nothing scrambles into the single round a patrol plane fights against
  entering units during Combat Movement, where other units may not take part
  except paired destroyers (§9.3.1). The engine already worked this way.
- A plane that fought that single round may fight the same ships again in the
  Combat Phase, since §10.1 exempts single rounds at sea from its one-battle
  limit, and it chooses again by the same rule.

**Authority:** the user in chat on 4 November 2026: "of course we need to fix
the MAP and the aircraft on a carrier difference, they are not the same", and
for the order, "the MAP plane can choose to fight again, or not. Only then the
ships can scramble into this [sea zone] because this is combat phase."

**Related fix, from the rulebook alone:** when ships enter a patrol plane's sea
zone, the plane may let them pass only if the Attacker has no aircraft with an
attack value present (§9.4). The engine had offered the choice regardless.

**Example:** a KMT fighter patrols P14, where a Japanese destroyer has been since
before Japan's turn, and a KMT destroyer is in port at Shantung. Japan's
destroyer attacks the fighter. Before this ruling, KMT was first asked whether
to scramble the Shantung destroyer, and the fighter, if it stayed out, was
destroyed when Japan won. Now the fighter is asked first. If it stays out, there
is no battle and nothing is lost; if it fights, the Shantung destroyer may
scramble to join it.

## RCL-021: Upgrading a unit aboard a transport

**Status: adopted by the user, 5 November 2026; the part on ships at sea on
6 November 2026.**

**Sources:** RB §8.4 p51 (upgrades); §10.6.5 pp68-69 (carpet bombing); §11.3.1
pp75-76 and §11.4.1 pp76-77 (air and naval cargo); §11.5 pp77-78 (ships in
port); §12.3 p80 (placing upgrades); §13.1.5 pp89-92 and §13.1.6 p92 (what each
transport carries).

**Question:** a unit can still be aboard a transport when its owner places
upgrades in the Place Units Phase: on a ship at sea or in port, or on an air
transport. §11.3.1 does not require an air transport to unload its cargo, and
an ally's unit boards on its own turn and leaves on its next (§§11.3.1 and
11.4.1). Two questions follow.

- An upgrade can turn it into a unit the transport may not carry. An air
  transport carries one infantry-class unit, a Heavy Air Transport also
  artillery, so an infantry aboard may not become motorized infantry, which is
  vehicle-class. A naval transport carries two infantry-class units or one and
  another land unit, so of two infantry aboard only one may. The rulebook does
  not say whether such an upgrade may be placed.
- §12.3 requires a Supply Path to the land zone the unit is in. A unit aboard a
  ship at sea is in no land zone, while a ship in port is located in the land
  zone of its Naval Facility (§11.5). The rulebook does not apply this to
  carried units in particular.

**The engine before this ruling** offered an upgrade on any unit of the right
type that a Supply Path reaches, carried or not, and its Supply Path search
also ends in sea zones. In random play it made an air transport carry motorized
infantry, and it upgraded infantry aboard ships at sea.

**Adopted ruling:**

- An upgrade may not be placed on a unit aboard a transport if the transport
  could not carry its cargo afterwards.
- An upgrade may not be placed on a unit aboard a ship at sea. Aboard a ship in
  port it may, within the first point.
- In both cases the upgrade stays on the build queue until it can reach a
  suitable unit, as §12.3 provides when it cannot reach one.
- Other upgrades of carried units are unchanged: an infantry aboard a naval
  transport in port may become motorized infantry when nothing else aboard is
  outside the infantry class, and a militia aboard an air transport may become
  infantry.
- Cargo may still stay aboard. Making every unit leave its transport before the
  Place Units Phase was considered and not adopted, because staying aboard can
  be better: carpet bombing attacks only land units (§10.6.5).

**Authority:** the user in chat on 5 November 2026: "if there are cases where
not unloading is better we then should keep the option of having them loaded,
lets just make it not allowed to upgrade a loaded unit to something not
carry-able then". On 6 November 2026, asked whether to bar upgrades of units
aboard ships at sea as §12.3's wording implies, the user answered "Yes, bar
them".

**Examples:** a KMT air transport landed in Sikang still carries an infantry in
the KMT's Place Units Phase, and the KMT has bought an upgrade to motorized
infantry. Before this ruling the upgrade could be placed on that infantry. Now
it is offered only on an infantry not aboard a transport, or aboard one that
could carry the result. A Japanese naval transport at sea off Tokyo carries an
infantry and a militia, and Japan has bought an upgrade for each. Neither is
offered for them until the ship is in port or the units are ashore.

## RCL-022: An attack on land that was Chinese at the start

**Status: closed — developer clarification reported by the user, 22 November
2026.** It replaces the reading the user had adopted for now on 19 November
2026, under which no nation could make an attack that put it at war with its
own alliance, so Mongolia never could.

**Sources:** RB glossary p7 (originally); §4.3 p26 (alliances); §4.5 p27
(controlled minor powers); §4.7 p29 (Mongolia); §4.9 p30 (an attack on China);
§5.1 p35 (declarations of war); §14.3 p101 (entering Chinese land); §15.4 p105
(the Dadao Government); the user's report of the developers' clarification, 22
November 2026 (no message link supplied).

**Question:** §4.9 makes an attack by a foreign nation on a land zone that was
originally a warlord's, the CCP's or the KMT's a declaration of war on all of
China. Two questions follow, written up as Q-001 and Q-002 in the project's
list of questions.

- Does the zone's printed owner decide, when a nation outside China, such as
  Japan, now holds the zone?
- May an attacker make that attack if it may not go to war with every Chinese
  nation? §4.5 forbids a controlled minor power to declare war or take any
  action that puts it at war with a nation it is not at war with yet, and
  §5.1 lets nobody declare war inside its own alliance. Mongolia, a controlled
  minor power of the Comintern, shares its alliance with the CCP (§4.3), and in
  the full game so does the USSR; the KMT is in the Allies.

**The case.** Before 19 November the engine let Mongolia attack such a zone
whenever the nation holding it was already at war with Mongolia, or nobody held
it, and the attack then put Mongolia at war with the CCP, the KMT and every
warlord that had not joined a side. In 70 of 480 random games Mongolia came to
be at war with the CCP this way: once the KMT or Japan had attacked Mongolia, a
Mongolian unit attacked a zone that had been a warlord's and that the KMT (45
games) or Japan (25 games) held
([record](../../docs/archive/records/answer_census_2026_11_15.md#mongolia-as-the-invader-of-china)).

**Ruling:**

- The printed owner decides: an attack by a nation that is not Chinese on a
  land zone that was originally a warlord's, the CCP's or the KMT's is an
  invasion of China whoever holds the zone now, or if nobody does. A zone the
  Dadao Government holds is the one exception (§4.9, §15.4).
- The invasion puts the attacker at war with every Chinese nation outside its
  own alliance: the KMT, the CCP and every warlord that has not joined a side,
  except a nation of the attacker's alliance. So Mongolia's invasion puts it at
  war with the KMT and those warlords, never with the CCP; in the full game, a
  nation of the Allies that invades China is put at war with the CCP and those
  warlords, never with the KMT.
- Any nation that is not Chinese may make the attack, Mongolia too, although
  the wars it starts are wars that §4.5 would not let Mongolia start otherwise.
- Read here, not stated by the developers: Mongolia still attacks only a zone
  whose holder it is already at war with, or one that nobody holds (§4.5). The
  developers' answer is about the wars the attack starts with the rest of
  China, not about which zones Mongolia may attack.

**Authority:** the user in chat on 22 November 2026: "I got developer
confirmation that Mongolia can attack any land originally chinese and the rule
will be it making mongolia at war with all of chinese except the ones in its
own alliance, same for the other side if allies want to take chiense land and
it will not put it at war with kmt".

**Examples:** the KMT has attacked Mongolia and holds Tsinghai, which was the
Ma Clique's. A Mongolian cavalry in Central Mongolia may attack Tsinghai, and
Mongolia is then at war with the KMT and every warlord that has not joined a
side, never with the CCP. Japan holds Suiyuan, which was Mengjiang's, and is at
war with Mongolia; the cavalry may attack Suiyuan, which is an invasion of
China too. While the Ma Clique holds Tsinghai and Mongolia is not at war with
it, the cavalry may not attack Tsinghai; after Mongolia's invasion of China it
may.

## RCL-023: A land battle that no unit can end

**Status: adopted by the user, 22 November 2026.** It answers Q-014 of the
project's list of questions, raised on 21 November 2026 after a training game
failed on such a battle.

**Sources:** RB §1.7.5 p12 and §1.7.7 p13 (tundra or ice and city round
limits); §10.3 p62 (retreating from combat); §10.5 p64, steps 9 and 10 (the
attacker may retreat if possible; the rounds repeat until the battle is over);
§10.8.3 p71 (no retreat from an amphibious assault); RCL-016.

**Question:** how does a land battle end when the attacker's remaining units
can neither fire nor retreat, and the defender's units cannot fire either?
§10.5 repeats the combat rounds "until the battle is over" (p64, step 10).
Aircraft and land units that attacked from neighbouring land zones may retreat,
while units that came from the sea or by air drop must stay (§10.3 p62) and
"must continue the attack until combat is resolved" (§10.8.3 p71). Only a city
battle, after three rounds, and a tundra or ice battle, after one, have a
printed end for units that must retreat and cannot: they are eliminated (§1.7.7
p13, §1.7.5 p12).

**The case.** On 20 November 2026 Japan attacked the KMT in Manchuria-Rehe, a
zone of normal terrain with no city, with a Self-propelled Artillery that came
overland from Korea and an Anti-aircraft Artillery landed from sea zone P14;
the KMT defended with one Anti-aircraft Artillery. Japan retreated after the
first round: the Self-propelled Artillery went back to Korea, and the
Anti-aircraft Artillery, having come from the sea, had to stay. Neither
Anti-aircraft Artillery fires at land units, so no unit could roll a die again,
and the engine stopped the game
([record](../../docs/archive/records/land_battle_without_end_2026_11_20.md)).

**Ruling:**

- When no unit of either side could roll a die in the next combat round, the
  battle could never end by fighting, and the attacker retreats: retreating is
  its only action. Its units that may retreat go back as in any retreat, each
  to a zone it may retreat to (§10.3 p62). Its units with nowhere to go are
  eliminated: those that came from the sea or by air drop, and land units with
  no Friendly zone to go back to. The defender keeps the zone.
- The same holds when the attacker retreats by choice and leaves behind units
  that came from the sea or by air drop: if no unit of either side could roll a
  die in the next round, those units are eliminated at once.
- Read here, not stated by the user: every other battle keeps the printed
  rules. Units that came from the sea or by air drop stay and fight on after a
  retreat whenever some unit of either side can still roll, and the attacker
  may fight another round instead of retreating.

**Authority:** the user in chat on 22 November 2026: "Let's say the player is
allowed to retreat as an action and if the unit has nowhere to go that unit
dies."

**Examples:** in the case above, Japan's retreat takes the Self-propelled
Artillery back to Korea and eliminates the Anti-aircraft Artillery, and the KMT
keeps Manchuria-Rehe. Had Japan attacked with the Anti-aircraft Artillery
alone, overland from Korea, the first round would roll no die, and Japan's only
action would be to retreat it to Korea. Had it landed from the sea, it would be
eliminated after the first round.

## Maintenance

Keep issue IDs stable. Record sources, the rule question, resolution or remaining
question, and the authority for any ruling. How a ruling is implemented belongs
in the engine page of the rule it changes (`docs/engine`); the history of the
change and its check results belong in the commit message. Do not promote
community discussion to a publisher ruling without verifying its authority.
