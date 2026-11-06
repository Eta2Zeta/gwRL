# GW36 v4.3 rule clarifications and open questions

Updated: 5 November 2026.

This is the project's shared register of **unclear official rules**, including
interpretations adopted after discussion. It is **not publisher-issued errata**.
An adopted project clarification is not evidence that the publisher endorsed it.
Record each rule conflict with its source, decision and developer clarification
status. Implementation details and verification belong in milestone documents.

Campaign-specific exclusions, controllers, setup choices and reward definitions
belong in the [M0 campaign review](/Users/home/Desktop/gwRL/docs/m0/README.md),
not here. Map-reading uncertainties remain in the
[map notes](/Users/home/Desktop/gwRL/game_content/README.md) and map audits;
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

`RB` means [Global War 1936 v4.3 Rulebook](</Users/home/Desktop/gwRL/game_content/rules/Global War 1936 v4.3 Rulebook.pdf>);
its printed and PDF page numbers coincide. `Japan`, `CCP` and `KMT` mean their
v4.3 national reference sheets, using one-based PDF pages:
[Japan](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - Japan v4.3.pdf>),
[CCP](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - CCP v4.3.pdf>),
[KMT](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - KMT v4.3.pdf>).
Discord messages are community evidence unless publisher authority is verified.
A new entry requires a genuine omission or incompatible applicable rules after
checking definitions, examples, cross-references and national exceptions.
Source-answered questions are kept in the [archived checks](source_answered_questions.md),
including retired IDs RCL-006, RCL-007, RCL-008 and RCL-011.

## Issue index

| ID | Official-rule question | Status |
| --- | --- | --- |
| RCL-001 | Airborne assault: AAA appears in steps 4 and 5 | Closed: developer correction for v4.4; both sides fire in step 4 |
| RCL-002 | Influence: meaning of the pre-roll spending cap | Adopted: unmodified success threshold |
| RCL-003 | Foreign invasion: alignment of a whole warlord | Adopted: one roll per warlord |
| RCL-004 | CCP purchases: railroad versus supply-path wording | Closed: developer fix for next version, reported by user |
| RCL-005 | Blockade: enemy surface warships versus any enemy units | Closed: only enemy Surface Warships prevent a blockade; developer clarification reported by user |
| RCL-009 | Japan-Soviet border clashes: named zones or broader borders | Adopted: Japan reference-sheet target list |
| RCL-010 | Dadao lend-lease: recipient has no original Home Country | Adopted: Dadao-possessed Chinese Home Country destinations; pending developer clarification |
| RCL-012 | Chinese Truce combat and retreat | Closed: developer-confirmed roles; same KMT elimination after voluntary or automatic termination |
| RCL-013 | Does artillery city bombing use attrition's range and movement restrictions? | Adopted: use the same starting-adjacency and no-movement conditions |
| RCL-014 | Combat roles when ships evacuate into a third party's fleet | Closed: evacuating fleet defends; fleet already at sea attacks; developer clarification |
| RCL-015 | Neutral units required to relocate with no Friendly land remaining | Provisionally adopted: eliminate units with no Friendly relocation destination |
| RCL-016 | KMT Low Morale 10+ with no legal retreat, such as after an amphibious assault | Adopted: the unit is eliminated |
| RCL-017 | May a patrol plane that let ships pass still fight them later that turn? | Adopted, revised the same day: yes, if they attack it anew; it then chooses again whether to fight |
| RCL-018 | Amphibious assault whose sea zone is not cleared, or whose transports retreat | Adopted: the assault is called off; the cargo stays aboard |
| RCL-019 | Several railroads on one border; the damage limit and repair of each side | Adopted: one railroad per border; each side holds its own damage and is repaired by its possessor |
| RCL-020 | A patrol plane attacked in its own sea zone: the carrier choice or the patrol choice, before or after scrambles | Adopted: the patrol choice, made before any scramble; staying out costs nothing |
| RCL-021 | Upgrading a unit aboard a transport into one the transport may not carry | Adopted: not allowed; the upgrade waits on the build queue |

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

## RCL-002: influence spending before the die roll

**Status: adopted by the user, 5 October 2026.**

**Sources:** RB §§15.2 and 15.4, pp104-105; CCP p3; Japan p4.

**Problem:** both abilities require payment before rolling but describe the
spending cap by reference to the original influence roll, which has not happened.

**Adopted clarification:** the cap is the **unmodified success threshold** from
the qualifying adjacent land zones, not the eventual die result. If that
threshold is `t`, spend an integer `s` with `0 <= s <= t`, subject to available
treasury, before rolling. For raw D12 result `r`, success is `r - s <= t`, except
that **a natural 12 always backfires** to KMT. Eligibility, influencing-zone
requirements and the one-attempt-per-turn limit are unchanged.

Example: a base threshold of 3 allows spending up to 3 IPP. Spending 2 makes
raw rolls 1-5 successful, but a raw 12 still backfires.

## RCL-003: whole-warlord alignment after foreign invasion

**Status: adopted by the user, 5 October 2026.**

**Sources:** RB §4.9, pp30-31.

**Adopted clarification:** resolve foreign-invasion alignment for each **whole
warlord**, with one roll whenever the alignment table calls for a roll. Determine
the qualifying neighboring factions across all territories belonging to that
warlord, select the corresponding existing table category, and apply the single
result to the entire faction and its surviving forces. Preserve the table's
automatic KMT outcome where no qualifying CCP/Dadao neighbor exists.

Beiping/Hopeh form one warlord for this procedure, as do Kwangtung/Hainan.
Foreign-invasion alignment and ordinary CCP/Japanese influence retain their
distinct triggers, eligibility, probabilities and timing; both keep the warlord
intact. This is the adopted shared rule, not a campaign-only exception.

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

**Sources:** Japan p4, Dadao Government; RB §15.4 p105; §12.4 p80;
Home Country and Originally Possessed definitions, pp6-7.

**Problem:** Japan's Dadao ability explicitly permits lend-lease to its controlled
Dadao Government. The ordinary delivery rule requires the recipient's possessed
Home Country as the destination. Dadao forms during play and has no originally
possessed territories, so the ordinary Home Country definition supplies no
destination. The aid permission itself is settled; the missing destination is
the issue to report to the developers.

**Adopted project ruling:** Japan may deliver lend-lease to **any land zone
currently possessed by Dadao within Chinese Home Country**. Retain the ordinary
supply-route, possession-timing, blockade, item and per-recipient limits. This
settles delivery and subsequent placement of that aid; it does not redefine
Dadao's Home Country for unrelated rules or permit aid without a real route.
The user will report this issue to the developers. This is a user-approved
campaign interpretation, not a reported developer ruling.

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

**Sources:** RB §0.3 p8; §4.5 p27; §5.1 p35; §6.6 p42; §15.4 p105; CCP reference sheet p1.

**Question:** CCP has surviving units but no possessed land. Its units share KMT
land under the Chinese Truce. KMT previously attacked Dadao; CCP did not join
that war. Dadao later captures KMT's last land. The neutral CCP units must
relocate to the nearest Friendly land, but none remains. CCP never surrenders. What happens to these units?

**Adopted ruling:** eliminate the nonparticipating units only when no Friendly
relocation destination exists. Otherwise use the printed nearest-Friendly-land
relocation rule. The elimination consequence is a provisional project
interpretation, not a developer-confirmed rule.

## RCL-016: KMT Low Morale with no legal retreat

**Status: adopted by the user, 2 November 2026.**

**Sources:** RB §15.7 p107 and KMT reference sheet p3 (Low Morale); §10.3 p62
and §10.8.3 p71 (no retreat from an amphibious assault); §§1.7.5 and 1.7.7
pp12-13 (city and tundra/ice round limits); §6.6 p42.

**Problem:** an attacking minor-KMT regular Infantry or Cavalry unit that rolls
10+ must retreat to the zone it attacked from. A unit that landed in an
amphibious assault attacked from a sea zone, and land units cannot retreat from
an amphibious assault. The Low Morale text does not say what happens when that
retreat is impossible.

**Adopted ruling:** the unit is eliminated. This follows the city and
tundra/ice rules, which eliminate attackers that must retreat but cannot, and
matches the 10+ elimination under the Chinese Truce (RCL-012). A unit that can
retreat to the zone it attacked from still does so, it still cannot be taken as
a casualty, and Major-Power KMT remains exempt.

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

**Status: adopted by the user, 5 November 2026.**

**Sources:** RB §8.4 p51 (upgrades); §10.6.5 pp68-69 (carpet bombing); §11.3.1
pp75-76 and §11.4.1 pp76-77 (air and naval cargo); §12.3 p80 (placing
upgrades); §13.1.5 pp89-92 and §13.1.6 p92 (what each transport carries).

**Question:** a unit can still be aboard a transport when its owner places
upgrades in the Place Units Phase: on a ship at sea or in port, or, as an
ally's unit, on an air transport, which it boards on its own turn and leaves on
its next (§§11.3.1 and 11.4.1). An upgrade can turn it into a unit the
transport may not carry. An air transport carries one infantry-class unit, a
Heavy Air Transport also artillery, so an infantry aboard may not become
motorized infantry, which is vehicle-class. A naval transport carries two
infantry-class units or one and another land unit, so of two infantry aboard
only one may. The rulebook does not say whether such an upgrade may be placed.

**The engine before this ruling** offered an upgrade on any unit of the right
type that a Supply Path reaches, carried or not. In random play it made an air
transport carry motorized infantry.

**Adopted ruling:**

- An upgrade may not be placed on a unit aboard a transport if the transport
  could not carry its cargo afterwards. The upgrade stays on the build queue
  until it can reach a suitable unit, as §12.3 provides when it cannot reach
  one.
- Other upgrades of carried units are unchanged: an infantry aboard a naval
  transport may become motorized infantry when nothing else aboard is outside
  the infantry class, and a militia aboard an air transport may become infantry.
- Cargo may still stay aboard. Making every unit leave its transport before the
  Place Units Phase was considered and not adopted, because staying aboard can
  be better: carpet bombing attacks only land units (§10.6.5).

**Not settled here:** whether a unit aboard a ship at sea may be upgraded at
all. §12.3 requires a Supply Path to the land zone the unit is in, and a unit
at sea is in none. The engine still offers such upgrades.

**Authority:** the user in chat on 5 November 2026: "if there are cases where
not unloading is better we then should keep the option of having them loaded,
lets just make it not allowed to upgrade a loaded unit to something not
carry-able then".

**Example:** a KMT air transport landed in Sikang still carries an infantry in
the KMT's Place Units Phase, and the KMT has bought an upgrade to motorized
infantry. Before this ruling the upgrade could be placed on that infantry. Now
it is offered only on an infantry not aboard a transport, or aboard one that
could carry the result.

## Maintenance

Keep issue IDs stable. Record sources, the rule question, resolution or remaining
question, and the authority for any ruling. Keep implementation history and
checks in the milestone documents. Do not promote community discussion to a
publisher ruling without verifying its authority.
