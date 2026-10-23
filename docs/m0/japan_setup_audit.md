# M0: Japan official setup audit

Status: **M0 specification verified and frozen on 21 October 2026**; not a playable full-rules state. Scope: the July 1936 Japan setup projected onto the approved 37-node China/Japan theatre. No game engine or training behavior is changed by this audit.

**21 October 2026 synchronization:** see the [M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md)
for approved setup/scope decisions and the
[shared rule register](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md)
for the adopted/closed rule interpretations. The carrier-footnote, ship-placement
and Kamikaze misreadings below have been corrected. The M0 review records the
completed verification and freeze.

## Sources and method

The primary source is [Japan NRS v4.3](../../game_content/rules/GW36%20-%20NRS%20-%20Japan%20v4.3.pdf), PDF pages 1-9. All nine pages were rendered and visually inspected. The setup on page 9 is an image: ordinary PDF text extraction returns only its heading and misses every unit. Page numbers below are one-based PDF page numbers; the NRS has no printed page numbers.

The [v4.3 rulebook](../../game_content/rules/Global%20War%201936%20v4.3%20Rulebook.pdf) uses matching printed/PDF page numbers. Sections 2.3-2.4, page 18, require setup-sheet units/facilities and national starting IPPs. Sections 8.3 (page 50), 8.6 (page 51), 12.1 (page 79), and 13.1.6 (pages 89-91) explain construction, repairs, placement and naval prices/capacities. The setup and relevant naval tables were also visually inspected.

Source SHA-256 values:

- Japan NRS: `832ca2e38968fd469bdf33dd2b415cd36b236d0f314ce7615137e489949935fa`.
- Rulebook: `240d04e5bb9d20928f375ce115836c360ad614fc6215da8b901d7a1806eef11d`.
- Original September audit's global map JSON: `97061d40dacc5a23c570d063f21279c9aef24cd3f4533c166bb04fa241b61e24` (historical provenance; current generated-map hashes are recorded in the artifacts).

Machine-readable transcription, citations and approved setup choices: [japan_setup.json](../../game_content/scenarios/japan_china_1936/m0/japan_setup.json).

## Retained official pieces

All entries in this table are from Japan NRS page 9. Mixed land/sea rows are split by their printed land/sea designation: the Korean Infantry is in Korea while that row's ships are in P14, not moved into port. The analogous Formosa row splits into Formosa and P32.

| Location | Military units | Setup factories |
| --- | --- | --- |
| Hokkaido | 1 Infantry | None |
| Honshu | 1 Motorized Infantry | None |
| Tokyo | 1 Infantry, 1 Fighter, 2 Tactical Bombers | 1 Major Factory |
| Kyushu | 1 Infantry | 1 Medium Factory |
| Northern Manchuria | 1 Militia, 1 Mountain Infantry | None |
| Eastern Manchuria | 1 Militia, 2 Infantry, 1 Cavalry | None |
| Korea | 1 Infantry | None |
| Rehe | 1 Militia, 2 Infantry | 1 Minor Factory |
| Okinawa | 1 Militia, 1 Seaplane | None |
| Formosa | 1 Militia, 1 Fighter | None |
| P14 | 1 Light Cruiser, 1 Heavy Cruiser, 1 Coastal Submarine | None |
| P32 | 1 Naval Transport, 1 Destroyer | None |
| P15 | 2 Fighters, 1 Tactical Bomber; 3 Naval Transports, 1 Torpedo Boat Destroyer, 2 Destroyers, 1 Light Cruiser, 1 Heavy Cruiser, 1 Battlecruiser, 2 Battleships, 2 Submarines, 1 Light Carrier, 1 Fleet Carrier | None |
| P16 | 1 Naval Transport, 1 Torpedo Boat Destroyer, 1 Heavy Cruiser, 1 Coastal Submarine | None |

Western Manchuria, P33 and P41 have no Japanese pieces listed. There are **48 deployed military units: 24 land/air and 24 naval**, plus **3 factories**. The approved P15 setup assigns **one Fighter and one Tactical Bomber to the Fleet Carrier, and one Fighter to the Light Carrier**. This user choice fills the printed capacities 2 and 1; it is recorded separately from the chart's sea-zone aircraft counts.

The setup marks no deployed damage. Ships are transcribed into named sea zones without inventing in-port, escort, raider, cargo or MAP status.

### Existing map facilities

The extracted map already contains **14 distinct Japanese facility IDs** in scope: 3 airfields (rulebook Airbases), 4 major shipyards, 4 major ports, 2 minor ports and 1 seaplane base. These are the underlying map infrastructure, not a second set of setup pieces. The three NRS factories are additional physical facilities with their own setup IDs. Hokkaido's port is exclusively on the removed P7 edge and is absent under the agreed extraction policy.

Rail connections are not included in the count of 14 facilities; their value must be accounted separately once per undirected retained rail border. Multi-access physical facilities likewise count once by facility ID.

## Excluded official pieces

The following page-9 entries stay outside the theatre; none is relocated:

| Printed location | Excluded pieces |
| --- | --- |
| South Sakhalin | 1 Militia |
| Bonin | 1 Militia |
| Volcano Islands | 1 Militia |
| Palau | 1 Militia |
| Caroline Islands / P46 | 1 Militia, 1 Heavy Cruiser, 1 Submarine |
| Marshall Islands | 1 Militia |

This is **8 deployed military units** excluded. The off-board 6 Kamikaze counters are an ability quota, not six aircraft; they are neither deployed nor assigned asset value. The USA-dependent activation mechanism is inactive in this closed theatre.

## Construction: preserve evidence, do not invent placement

Japan NRS page 9 contains these national queue entries:

| Printed queue | Printed cell | Interpretation status |
| --- | --- | --- |
| #1 - Place Unit | Light Carrier `(1)` | Parenthesized USA-war build-queue entry, explained by p9 footnote |
| #2 | Heavy Cruiser `1` | One unambiguous queued Heavy Cruiser; location not printed |
| #2 | Light Carrier `(2)` | Parenthesized USA-war build-queue entry, explained by p9 footnote |
| #3 | Fleet Carrier `1` | One unambiguous queued Fleet Carrier; location not printed |

The Light Carrier total at setup is **1**, supplied by the unparenthesized P15
carrier. The parenthesized footnote immediately below the p9 table explains
that the `(1)` and `(2)` entries enter the build queue once at war with USA;
they are not extra deployed July 1936 carriers. The earlier assertion that the
source lacked an explanation was our reading error, not unclear official text.
The no-USA campaign excludes those conditional entries.

Every printed total reconciles as retained deployments + excluded deployments + the two unambiguous national queue ships + factories + six off-board counters, **without adding the parenthesized Light Carrier entries**.

The two ordinary national queue ships do not need an invented starting tile.
RB §§8.3.1-8.3.2 distinguishes queued units from site-bound facility construction;
§12.1 places ships at eligible supplied shipyards with capacity and the required
ownership age, with Major Shipyards required for Capital Ships. The user has
chosen to retain both ships with normal eligible-shipyard placement. The earlier
suggestion to exclude them for lacking a printed starting tile was an unnecessary
project restriction, not an official-rule requirement.

The Heavy Cruiser costs 5/5 IPP and Fleet Carrier 5/5/5 (NRS page 7). The user has adopted **cumulative already-paid amounts** as the unfinished ships' scoring value. Source reconciliation establishes **5 IPP already paid for each ship**: the Heavy Cruiser in #2 has one 5-IPP payment remaining; the Fleet Carrier in #3 has two 5-IPP payments remaining. The printed construction track advances #3 -> #2 -> #1 Place Unit, and these setup entries are already in their first paid stage (NRS pp7,9; RB §§2.3,7.3,8.3). Do not debit those historic payments from starting cash. On completion, remove the construction entry and use the full completed catalog value (10 and 15 IPP respectively), counting each ship once. See [source reconciliation](/Users/home/Desktop/gwRL/docs/m0/source_reconciliation.md) for the evidence chain. There is no executable queue in M0.

## Theatre-adjusted treasury and income

Japan's official starting income and treasury are **16 IPP** (NRS page 1; rulebook 2.4, page 18). The retained starting territory values sum to **15**:

| Retained starting possessions | Income per turn |
| --- | ---: |
| Tokyo, Honshu, Kyushu | 2 each |
| Hokkaido | 1 |
| Okinawa | 0 |
| Formosa, Korea | 2 each |
| Northern/Eastern/Western Manchuria and Rehe | 1 each |
| **Total** | **15** |

The campaign's operational definition for theatre-adjusted starting cash is **the smaller of official starting cash and the sum of retained directly possessed starting territory IPPs**, hence **min(16, 15) = 15 IPP for Japan**. This removes South Sakhalin's outside 1 IPP. The user authorized theatre adjustment; this precise capped-local-base formula is a documented scenario derivation, not an official alternate setup. No spending or engine state is created here.

U.S. oil-trade income is excluded under the closed-world profile. Japan initially owns none of its six Chinese occupation-bonus locations. NRS page 2 gives +1 each for Beiping, Hopeh, Shantung, Nanking, Hunan and Kwangtung even when Japan is not at war with a Major Power. These bonuses can therefore become active through local gameplay; they are not lost simply because external bonus locations are excluded.

## Approved setup-only values and damage accounting

Only two deployed Japanese types have no official purchase price:

| Type | Retained count and locations | Source and approved scoring value |
| --- | --- | --- |
| Torpedo Boat Destroyer | 2: P15 and P16, one each | Rulebook 13.1.6, page 89: N/A, cannot be built; **5 IPP each** for scoring |
| Coastal Submarine | 2: P14 and P16, one each | Rulebook 13.1.6, page 91: N/A, cannot be built; **4 IPP each** for scoring |

These approved **reference values** apply to scoring only and do not make the types purchasable. No Japanese Coastal Defense Ship appears in the setup chart.

All other deployed Japanese military units and the three factories have purchase prices in NRS pages 5-8. Existing `airfield` map metadata should map to the rulebook's `airbase` facility type (6 IPP total); it is not an additional unpriced asset unless a distinct game type is later established.

Under the user's `purchase price - repair price` rule, damaged Capital Ships retain full monetary asset value because rulebook 8.6 (page 51) explicitly makes their repairs **0 IPP**, while consuming repair capacity and immobilizing the ship. Cities/facilities cost 1 IPP per damage repaired. Do not silently invent a cash repair cost to make damaged ships score less. Purchase discounts and paid-construction bookkeeping remain distinct from this literal damage rule.

## Japan-specific rule ledger candidates

These requirements belong in the shared engine, with closed-profile applicability explicit.

| Requirement | Source | Timing / decision owner | Minimum test |
| --- | --- | --- | --- |
| Home Country is only Honshu, Hokkaido, Kyushu, Tokyo; Okinawa excluded from home-country bonuses | NRS p1 | Setup; static nation metadata | Okinawa cannot gain a home-country-only bonus |
| Dug-in defense: infantry-class units get +1 defending Home Country | NRS p4 | Defense dice; Axis/Japan | Works on Tokyo and not Okinawa, stacks only with eligible modifiers |
| Japan may declare war on non-Axis nations except Nationalist Spain | NRS p3 | Declaration; Axis/Japan | No automatic war at July 1936; legal/illegal targets masked |
| Surrender when Tokyo is enemy-possessed at end of Japan's Player Turn | NRS p1 | End Japan turn; automatic | Temporary capture before recapture and held capture differ |
| Dadao influence; one eligible warlord attempt, impassable borders excluded; optional prior spending; natural 12 backfires to KMT | NRS p4; rulebook 15.4 | Place Units; Axis/Japan, then stochastic roll | Spending does not avoid natural-12 backfire; adjacency counts only qualifying zones |
| Dadao has recruitment and Japan lend-lease; local attacks do not trigger ordinary all-China alignment; joint Japan war conditions change Dadao alignment | NRS p4 | Diplomacy/combat/recruitment; Axis controlling minor | Controlled is not automatically aligned; wealth credit does not authorize joint combat |
| Chinese occupation bonuses +1 each at six named retained zones, without requiring war with a Major Power | NRS p2 | Income calculation/collection | Count owned qualifying tiles once, do not add their base income twice |
| Destroyer transports one Marine, movement -1 while carrying, stops after unloading; amphibious landing permitted | NRS p4 | Movement/amphibious declarations; Axis/Japan | Capacity and post-unload movement enforced |
| First declaration of war against an Allies Major Power can activate one surprise attack, possibly sea then adjacent amphibious assault | NRS p4 | Declaration and first combat round; Axis/Japan | One-use flag; aircraft first strike, defense -1, no scrambling, port-AA/city-round exceptions, ship/carrier-aircraft movement +1 |
| Build dates, specialty maxima, technology unlocks and home-country-only facilities | NRS pp5-8 | Production; Axis/Japan | January 1940 unlocks, cavalry unavailable after July 1939, factory/shipyard location legality |
| Kido Butai | NRS p3 | Inactive by approved campaign choice | No Kido Butai discount or local substitute fleet comparison; normal Improved Construction remains |
| Strategic naval capacity 3 | NRS p1 | Non-combat strategic movement; Axis/Japan | Shared per-turn capacity cannot be bypassed by multiple orders |
| Siam, Soviet-border clashes, external oil/territory bonuses, external-resource objectives and USA-triggered Kamikaze | NRS pp1-4, p9 | Inactive prerequisites in this closed profile | No fabricated off-map supply, income, units, war or activation events |

For RCL-009, the user chose on 21 October 2026 to follow Japan NRS: Japanese
border-clash attacks may target Soviet units only in Chita, Amur or Primorsky
Krai. Soviet ownership or incorporation of Mongolian territory does not add a
Japanese clash target. The shared-border, one-round/no-conquest and pact
restrictions remain; this interpretation does not impose symmetric restrictions
on Soviet attack origins or override USSR NRS. This is a user-adopted
interpretation, not a publisher-confirmed ruling, and remains inactive in this
USSR-excluded campaign.

Kido Butai is now disabled by explicit campaign choice; no outside fleet is
invented. Kamikaze unlocks when USA reaches Wartime Income (Japan p4; RB §15.4).
The supposed conflicting p9 trigger was our mistake: the parenthesized build-queue
footnote explains the Light Carriers, not the unparenthesized off-board Kamikaze
counters. With no USA participant, this campaign does not fabricate that trigger.

## Handoff to the current review

The M0 review records the approved setup-only prices (Torpedo Boat Destroyer 5,
Coastal Submarine 4), P15 carrier attachments, queue inclusion, USA-war-carrier
exclusion and Kido Butai exclusion. Those are no longer unanswered questions.
Paid-queue valuation is decided: score cumulative paid amounts until completion,
then substitute full completed catalog value. Source reconciliation establishes
the initial payments at 5 IPP each. The M0 specification is verified and frozen;
the [baseline](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/frozen_baseline.json)
records the frozen artifacts. Neither this audit nor the shared register
implements mechanics.
