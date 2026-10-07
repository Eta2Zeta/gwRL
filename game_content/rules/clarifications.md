# GW36 v4.3 rule clarifications and open questions

Updated: 6 October 2026.

This is the project's shared register of **unclear official rules**, including
interpretations adopted after discussion. It is **not publisher-issued errata**.
An adopted project clarification is not evidence that the publisher endorsed it.
Source PDFs remain unchanged. This document does not implement any rule.

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

`RB` means [Global War 1936 v4.3 Rulebook](</Users/home/Desktop/gwRL/game_content/rules/Global War 1936 v4.3 Rulebook.pdf>);
its printed and PDF page numbers coincide. `Japan`, `CCP` and `KMT` mean their
v4.3 national reference sheets, using one-based PDF pages:
[Japan](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - Japan v4.3.pdf>),
[CCP](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - CCP v4.3.pdf>),
[KMT](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - KMT v4.3.pdf>).
Discord messages are community evidence unless publisher authority is verified.

This register supersedes the interpretation/status wording of the older M0
audits for the issues below. Those audits retain source inventories and future
fixture IDs. The JSON interpretation notes for RCL-003/004 are also corrected;
full scenario-data synchronization and engine implementation remain separate.

## Issue index

| ID | Official-rule question | Status |
| --- | --- | --- |
| RCL-001 | Airborne assault: AAA appears in steps 4 and 5 | Adopted: attacker in 4, defender in 5 |
| RCL-002 | Influence: meaning of the pre-roll spending cap | Adopted: unmodified success threshold |
| RCL-003 | Foreign invasion: alignment of a whole warlord | Adopted: one roll per warlord |
| RCL-004 | CCP purchases: railroad versus supply-path wording | Adopted: specific railroad requirement |
| RCL-005 | Blockade: enemy surface warships versus any enemy units | Proposed: detailed surface-warship rule |
| RCL-006 | Chinese major-power evolution: trigger timing | Closed after checking: immediate at 13+ possessed land IPP |
| RCL-007 | Chinese Truce: breaking it versus earlier separation moves | Open |
| RCL-008 | Ordinary diplomacy: do Chinese warlords qualify? | Proposed: not ordinary neutral-nation targets |
| RCL-009 | Japan-Soviet border clashes: named zones or broader borders | Open |

## RCL-001: AAA in the airborne-assault sequence

**Status: adopted by the user, 5 October 2026.**

**Sources:** RB §10.6.1, pp65-66; §10.2, pp61-62; §13.1.4, p87.
Related old fixture: R087.

**Problem:** the printed step 4 includes attacking and defending AAA, while
step 5 separately orders defending AAA to fire. Reading both literally would
give defending AAA two volleys.

**Adopted clarification, limited to the airborne sequence in §10.6.1:**

1. **Step 4:** attacking and defending fighters resolve air superiority;
   **attacking AAA** fires here. Defending AAA does not fire in this step.
2. **Step 5:** **defending AAA** fires here.
3. Each regular AAA unit fires its first-round volley once, with one shot per
   eligible opposing aircraft, up to three shots per AAA. It does not fire
   again in the later ordinary-unit steps or subsequent rounds.

This changes which side's AAA fires in each step, not the fighters' participation
or the printed first-strike sequence. Normal land combat still uses §10.5;
do not replace its step 5 with an airborne-specific defender-AAA step.

Keep three different defenses separate:

- **Movable AAA units** may attack or defend; base attack/defense is 3/3.
- **Inherent city AA** is a separate pre-first-round airborne defense: one die
  per attacking aircraft carrying airborne infantry, without the regular
  three-shot cap. A hit destroys the aircraft and cargo before combat. Airborne
  Doctrine disables this city defense, not regular AAA units.
- **Facility-inherent AA** does not fire merely because an airborne assault
  attacks a zone containing that facility. Its strategic-bombing/port-attack
  defenses are different rules, not extra airborne volleys.

Retain the transport/cargo casualty linkage and the printed step-5 permission
for eligible non-transport attacking casualties to make their attack before
removal. A destroyed transport and its airborne cargo do not get to land and
attack. This clarification does not turn ordinary AA into first strike or
resolve unrelated casualty-selection questions by implication.

**Research provenance:** the previously reviewed
[18 January 2023 Discord discussion](https://discord.com/channels/876158750870863964/959237427149537311/1065244552912449536)
addresses an older airborne casualty sequence. It does not independently prove
the correction to the current v4.3 duplicate AAA wording. Authority for the
step-4/step-5 split above is the user's explicit ruling.

**Future checks:** both sides have AAA and aircraft; each AAA fires once at its
assigned step; zero aircraft gives zero AAA shots; surviving AAA cannot fire
next round; city AA is separate and disabled only by the relevant doctrine;
a facility alone adds no airborne AA; a destroyed transport loses its cargo.

## RCL-002: influence spending before the die roll

**Status: adopted by the user, 5 October 2026.**

**Sources:** RB §§15.2 and 15.4, pp104-105; CCP p3; Japan p4.
Related old fixtures: R133, R136.

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

**Future checks:** spend at the cap; reject cap+1 or insufficient funds; pay
before seeing the roll; preserve natural-12 backfire even at a high threshold.

## RCL-003: whole-warlord alignment after foreign invasion

**Status: adopted by the user, 5 October 2026.**

**Sources:** RB §4.9, pp30-31. Related old fixture: R030.

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

**Future checks:** one roll for Beiping/Hopeh even when the two territories have
different neighbors; one result for Kwangtung/Hainan even if the island lacks a
qualifying border; a CCP neighbor at one territory and Dadao neighbor at another
select the both-neighbor category for the whole warlord; automatic KMT alignment
where applicable; all surviving territories and forces receive the same result.

## RCL-004: CCP Comintern Brothers, rail versus supply

**Status: adopted by the user, 5 October 2026.**

**Sources:** RB §15.2, p103; CCP p3 ability text and minor build chart.
Related old fixture: R134.

**Problem:** the full ability requires an undamaged railroad from CCP-possessed
land to Soviet-possessed land during Production; the same national sheet's
purchase notes say supply path.

**Adopted clarification:** use the specific railroad condition and its placement
restriction; a sea-only or river-only supply path does not unlock Artillery/AAA
purchases.
Do not confuse this Soviet-**possessed** land requirement with the separate
income bonus's Soviet **Home Country** requirement (CCP p2).

**Future checks:** qualifying rail, damaged rail, supply without rail, correct
placement zone, and a Soviet-possessed zone that is not Soviet Home Country.
The clarification applies to the shared rules. The ability is inactive in the
current campaign because the USSR is excluded; directly Comintern-controlled
Mongolia taking the USSR turn position does not supply Soviet-possessed land.

## RCL-005: what prevents a blockade?

**Status: proposed reading; no new approval claimed.**

**Sources:** RB §9.4.6, p60 versus §13.1.6, p89.
Related old fixture: R076.

**Problem:** the detailed blockade rule excludes enemy Surface Warships from
the sea zone; the naval-unit summary instead excludes any enemy units.

**Proposal:** follow the detailed §9.4.6 condition. Enemy submarines alone do
not prevent a qualifying surface fleet from blockading. Preserve the fleet
size/alliance requirements and coverage of every sea access of a shared facility.

**Future checks:** enemy submarine only, enemy surface warship, and a facility
with two sea accesses where only one is blockaded. Campaign inclusion of
blockades is a separate decision from resolving this wording difference.

## RCL-006: when does Chinese major-power evolution trigger?

**Status: closed after checking, 6 October 2026. The earlier note overstated an
implementation detail as a rule ambiguity.**

**Sources:** RB §14.3.1, p101; KMT/CCP p1; RB §10.10, p73 (possession and IPP
chart updates), §12.9, p82 (income collection). Related old fixture: R132.

**Source-backed conclusion:** KMT or CCP evolves immediately once the IPP values
of its possessed land zones total **13 or more**. A legal capture, alignment or
influence transfer updates possession at that event's specified time; evaluate
the threshold as that transfer resolves, including during another nation's turn.
The trigger does not wait for income collection, the end of the current turn or
the start of the faction's next turn. Treasury and income bonuses do not count
toward this possessed-land threshold.

No contradictory rule has been identified. Evolution changes the faction's
abilities and automatically terminates a Chinese Truce as specified by the
rules. The explicit exception preserves decentralized production for the
remainder of its own turn if it evolves during that turn. Neither consequence
delays evolution or repeats a phase already completed.

Applying the ownership transfer, updating the land total, resolving evolution
and then continuing play is implementation sequencing, not an outstanding
user ruling. Retain this entry to prevent the false timing question recurring.

**Future checks:** crossing 12 to 13 by capture and by influence; capital choice
and factory award occur once; abilities and Chinese Truce change consistently;
the printed same-turn production exception is preserved.

## RCL-007: breaking the Chinese Truce

**Status: open timing detail.**

**Source:** RB §6.6, p42. Related old fixture: R041.

**Problem:** the truce is broken during Combat, but the breaking player is
allowed to move units out of shared land zones during the preceding Combat
Movement phase. An executable sequence needs to say when the intention to break
is committed and which separation moves are then legal.

The older ledger suggests declaring the intent during Combat Movement and
resolving the break in Combat; that remains a proposal, not a published timing
rule or an adopted clarification. Preserve the special co-location combat and
KMT Low Morale consequences while resolving this question.

**Future checks after resolution:** separation versus a shared stack left to
fight; the agreed declaration/commitment timing; the printed
no-truce-after-evolution restriction.

## RCL-008: ordinary diplomacy with Chinese warlords

**Status: proposed exclusion; eligibility question, not a proven contradiction.**

**Sources:** RB §8.8, p53; §§4.8-4.9, p30.
Related old fixture: R064.

**Question:** ordinary diplomacy targets neutral nations, whereas outsiders
treat the warlord provinces as part of KMT. The Sinkiang example in §4.8 also
distinguishes warlord territory from territory originally possessed by a neutral
Minor Power.

**Proposal:** independent Chinese warlords are not ordinary neutral-nation
diplomacy targets. Their specifically defined influence/alignment mechanics
remain available when legal. This is supported by their classification, rather
than a newly discovered sentence explicitly banning diplomacy with warlords.

**Future checks:** reject a generic diplomacy marker for a Chinese warlord;
allow eligible ordinary neutral nations; keep CCP/Japanese influence separate.

## RCL-009: Japan-Soviet border-clash geography

**Status: open for a larger map.**

**Sources:** Japan p1; RB §10.5.2, pp64-65.
Related old fixture: R084.

**Problem:** Japan's sheet names Chita, Amur and Primorsky Krai. The main rule
describes Japan (Manchukuo) and USSR attacking across a jointly held land border.
Would an additional Soviet-possessed border, such as incorporated Mongolia,
qualify, or is the national sheet's list exhaustive?

Do not grant clashes at extra borders from the general sentence alone while
this is unresolved. A campaign without a USSR participant cannot answer the
general question merely by disabling the event.

**Future checks after resolution:** named Soviet zones, additional Soviet-owned
border zones, and the non-aggression-pact restriction.

## Closed after checking: not new official errata

These notes prevent earlier misunderstandings from returning as open questions.

| Topic | Source-backed conclusion |
| --- | --- |
| AAA attack and facility/city distinction | Movable AAA attacks and defends (RB §13.1.4 p87). Facility AA is not an airborne defense; city AA is expressly separate (RB §10.6.1 p66, §§10.6.2/10.6.4, §13.2). The remaining duplicate-step issue is resolved for the project in RCL-001. |
| Chinese Major strategic naval capacity | KMT/CCP p1 explicitly grant capacity 1 after evolution; this is a national exception to the generic table in RB §11.4.2 p76, not an unknown zero-versus-one choice. |
| Japan lending to Dadao | The explicit permission in Japan p4 and RB §8.7 p52 must not be suppressed by the condensed Japan p3 table. |
| Several tracks on one border | RB §10.6.2 p67 applies bombing damage to all railroads on the selected border. The boolean border connection does not need separately named tracks; live damage/repair state remains separate. |
| Parenthesized Japanese Light Carriers | Japan p9's parenthesized footnote explains the `(1)` and `(2)` build-queue entries: available once at war with USA. Our earlier claim that no explanatory key existed was wrong. Whether that trigger can occur in a campaign is a scenario question. |
| Ship queues without a starting tile | Units enter the national build queue and are placed at eligible locations; fixed construction-site markers apply to facilities (RB §§8.3.1-8.3.2 pp50-51, §12.1 p79). Ships need an eligible, supplied, beginning-of-turn-owned shipyard and capacity; Capital Ships require a Major Shipyard. No printed starting tile is needed to interpret a national ship queue, and placement is not literally unrestricted. |
| Supposed Kamikaze trigger conflict | RB §15.4 p105 and Japan p4 use USA reaching Wartime Income. Japan p9's parenthesized build-queue footnote belongs to the Light Carrier entries, not the unparenthesized six off-board Kamikaze counters. Our earlier war-with-USA alternative for Kamikaze was a misattribution, not a genuine source conflict. |
| One China objective versus troop award | RB §3.3 p23 has different explicit conditions for the objective and the material award at KMT surrender. Meeting the objective does not by itself award the troops. These are separate clauses, not contradictory triggers. |
| CCP elimination versus surrender | CCP's never-surrender rule (CCP p1), the no-surviving-units end of the civil war (RB §14.3 p101), and possible revival after a KMT attack on a warlord (§4.9 p30) are distinct concepts; do not collapse them into an irreversible removed-player flag. |

## What is deliberately elsewhere

- **Campaign rules:** retained tiles/nations, Mongolia's controller, convoy and
  interdiction exclusions, MAP/blockade inclusion, Kido Butai exclusion, dates,
  starting cash and carrier assignments. Whole-warlord alignment is the shared
  adopted clarification RCL-003 above.
  See the M0 campaign review.
- **Training/accounting choices:** wealth weights, setup-only reference prices,
  damaged/completed asset valuation, paid construction, cities and rail ownership.
  These are not official game-rule corrections.
- **Map-source work:** tiny corner contacts, land-map wraparound and unresolved
  named borders, river tracing, and Tannu Tuva's ownership/control/home-country
  treatment. See the map notes; do not call an unverified map interpretation an
  official erratum. Excluding a tile does not certify its global-map data.
- **Missing transcription:** exact research-chart/damaged-ship data and further
  rail repair/ownership checks remain audit work until an actual source ambiguity
  is demonstrated.

## Maintenance

Keep the IDs stable. For a new issue, record the exact source/version, question,
status, adopted wording (if any), authority, and a small distinguishing test case.
Do not silently promote a proposal or a Discord answer into an official ruling.
If a publisher clarification is verified later, link it and explain whether it
supersedes a project interpretation. Future rule handlers/tests should cite the
relevant RCL ID; a Markdown entry alone is not a passing implementation test.
