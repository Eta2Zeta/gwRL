# GW36 v4.3 rule clarifications and open questions

Updated: 23 October 2026.

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

## Maintenance

Keep issue IDs stable. Record sources, the rule question, resolution or remaining
question, and the authority for any ruling. Keep implementation history and
checks in the milestone documents. Do not promote community discussion to a
publisher ruling without verifying its authority.
