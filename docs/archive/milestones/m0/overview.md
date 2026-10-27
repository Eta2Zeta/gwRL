# M0 review: July 1936–July 1941 closed China campaign

Updated: 21 October 2026. **M0 complete: specification frozen and verified as
`M0-2026-10-21`.** This is a scenario specification, not an implemented
full-rules game. No campaign choices or rule-clarification questions remain open
for M0.

**Revision scope:** this README records the approved campaign decisions; the shared
[rule clarification register](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md)
records adopted and closed official-rule interpretations. The setup inventories,
scenario contract, manifest, extracted map, detailed audits, milestone plan and
data tests now agree with these decisions. Excluded FEC and convoy records remain
as clearly labeled source evidence. The
[frozen baseline](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/frozen_baseline.json)
records the verified files and their SHA-256 hashes. Later changes to the approved
specification should explicitly revise this baseline. No full-rules engine or
training was implemented in this work.

## Confirmed campaign decisions

- **Calendar:** start July 1936; finish after the complete July 1941 round,
  including all national turns and income collection: 11 calendar rounds.
- **Three learning agents:** Axis, Allies and Comintern. Japan, KMT and CCP
  remain the respective main nations, with separate national rules and money.
  The retained turn order is **CCP → Mongolia (USSR slot) → Japan → KMT**.
  Mongolia takes its normal turn, including movement and recruitment, as if the
  USSR were present, at the usual USSR position. The Comintern player controls
  it directly, with Mongolia's separate minor identity preserved. There is no
  FEC/Commonwealth turn slot.
- **Closed map:** retain the reviewed Chinese theatre, Manchuria and Korea,
  Japan's four home-country tiles plus Okinawa, Formosa, and sea zones
  **P14/P15/P16/P32/P33/P41**. Tannu Tuva remains excluded. Remove outside
  neighbors when extracting; no movement or supply through missing tiles.
- **Remove Hong Kong and FEC from this campaign.** Omit Hong Kong's Infantry
  and its two map facilities, and FEC's Fighter, Light Carrier and Coastal
  Submarine in P41. **P41 itself stays.** No FEC treasury, income, production,
  diplomacy or Commonwealth turn slot is needed. This is a scenario exclusion,
  not a request to delete Hong Kong from the full-world map.
- **Remove the USSR as a participant/controller.** No Soviet treasury, forces,
  border-conflict events, CCP Soviet-connection income bonus or Soviet-dependent
  artillery/AAA purchase unlock. Comintern and CCP remain in the game; normal
  CCP major-power evolution is not removed. **Retain Mongolia's four tiles and
  two official starting pieces, controlled directly by the Comintern player.**
  Retaining its normal USSR-position timing does not restore Soviet ownership
  or any Soviet-dependent abilities.
- **Exclude convoys and interdiction.** No convoy routes, raiding, convoy-loss
  accounting, convoy escort missions, or interdiction rolls against supply,
  lend-lease or strategic movement. Their dedicated effects and test requirements
  are out of this campaign. A convoy map layer is **not** an M0/M1 dependency.
  Ordinary naval combat, transports, amphibious assaults, supply-path legality,
  strategic bombing and anti-aircraft defenses are not removed by this decision.
- **Include ordinary blockades and Maritime Air Patrol (MAP).** Their retained
  mechanics do not re-enable convoy or interdiction effects.
- **Disable Kido Butai for this campaign.** This is an explicit scope choice,
  not a claim that its full-game prerequisites can never be met.
- **Keep the Heavy Cruiser in queue #2 and Fleet Carrier in queue #3.** They
  may complete at any eligible retained shipyard under the normal placement
  rules; do not invent a starting tile for national queue entries. Capital
  Ships still require a Major Shipyard, with supply, age and capacity checks.
- **Score unfinished ships by the cumulative IPP already paid into them.**
  Apply the 0.1 asset coefficient to that amount. On completion, replace it
  with the completed ship's full catalog value; never count both. Source
  reconciliation confirms **5 IPP already paid into each starting ship**, with
  no additional debit from the opening treasury.
- **Use full catalog value for completed assets**, including setup/recruited
  assets. The already-agreed damage deduction remains; this is not permission
  to score a damaged asset as undamaged.
- **Foreign-invasion alignment: one roll for each whole warlord.** RCL-003
  adopts this as the shared rule. Determine qualifying neighbors across the
  warlord's territories, apply the existing alignment table once, and apply
  that single result to the entire faction.
- **Starting pieces:** use official July 1936 pieces located on included tiles;
  do not relocate excluded pieces into the theatre. Setup units and facilities
  count as assets. Unlocated national construction queues are addressed below.

### Preserve the user's warlord owner names

Use these existing map names, including their spelling, for starting ownership
and faction display. Do not replace them with generic labels such as “Tsinghai
warlord.” Internal IDs and printed setup-row labels can remain provenance, but
must not overwrite the user's owner names.

| Owner name | Starting tiles |
| --- | --- |
| Sinkiang Clique | Sinkiang |
| Ma Clique | Tsinghai |
| Mengjiang | Suiyuan |
| Zhili Clique | Beiping, Hopeh |
| Tibet | Tibet |
| Szechwan Clique | Sikang |
| Yunnan Clique | Yunnan |
| Guangxi Clique | Kwangtung, Hainan |

The full-world map already preserves these names; none was renamed in this
revision. Ownership, diplomatic control and alliance attribution are different
fields. Warlords start unaligned/uncontrolled, not automatically KMT-owned.
Later legal conquest or alignment can change ownership/control as the rules
require; preserving the original labels does not freeze gameplay ownership.

### Ship values and carrier setup — settled

| Setup-only type | Reference asset value per piece | Retained Japanese pieces |
| --- | ---: | --- |
| Torpedo Boat Destroyer | **5 IPP** | P15 ×1, P16 ×1 |
| Coastal Submarine | **4 IPP** | P14 ×1, P16 ×1 |

These are user-assigned wealth values, not new purchase options. Both types
remain unbuildable. FEC's excluded Coastal Submarine is not counted. There are
**no remaining missing-price questions for the retained deployed unit types**.

Japan's P15 carrier aircraft start attached as follows:

- **Fleet Carrier:** one Fighter and one Tactical Bomber.
- **Light Carrier:** one Fighter.

This allocates the existing three aircraft; it creates no extra planes or setup
action. Per the user's clarification, the parenthesized Light Carrier `(1)` and
`(2)` entries become available after war with the USA. They are **excluded** in
this no-USA campaign, and their meaning is no longer an open review question.
The ordinary deployed P15 Light Carrier stays. The two different national queue
ships discussed below are not those parenthesized reinforcements.

## Starting money and wealth

The approved theatre-adjusted starting treasury uses this documented local
derivation, not an official alternate setup rule:

```text
starting_cash = min(official_starting_IPP,
                    retained_directly_possessed_original_land_printed_IPP)
```

Japan starts with **15 IPP**, KMT **6**, and CCP **2**: **23 IPP total**.
Unaligned warlords have no starting treasury. There is no FEC or USSR account.

```text
W(side) = current legally collectable income-per-turn rate
        + 0.1 × (units + infrastructure + treasury + paid construction)
R(side) = W(side) - W(other side 1) - W(other side 2)
surviving asset value = purchase price - remaining repair price
```

Income means the current rate, not cumulative collections. Setup assets count.
Controlled/aligned minor assets count toward their controlling alliance;
uncontrolled, unaligned assets count toward nobody. This does not pool cash or
grant joint attacks. Mongolia's controlled assets count toward Comintern wealth
under the explicit direct-controller choice; no Soviet account is restored.

Treasury and paid construction use the same 0.1 coefficient as other assets.
Paid construction is the cumulative amount already paid, as confirmed by the
user. Count each physical facility or
undirected rail border once. Replace paid construction value with the completed
asset's value on completion; never count both. Score at the campaign deadline;
no extra early-ending rule or dense reward shaping is added at this stage.
The three-sided objective is general-sum, not two-player zero-sum.

Under the literal damage formula, zero-IPP capital-ship repairs mean no monetary
damage deduction. A Major Factory costing 18 with 20 IPP remaining repairs would
be worth **−2**; no zero floor has been added. These are disclosed consequences
of the selected formula, not new unanswered price questions. Changing them would
be a separate scoring adjustment.

## Verified retained inventory

These counts agree across the setup data, contract, manifest and extracted map.

| Group | Deployed pieces |
| --- | ---: |
| Japan | 48 |
| KMT | 12 |
| CCP | 5 |
| Eight unaligned warlords | 32 |
| Mongolia | 2 |
| **Total retained deployed pieces** | **99** |

Removing Hong Kong and retaining Mongolia gives **37 nodes** (31 land + 6 sea)
and **99 deployed pieces**.

The retained inventory includes Japan's **three setup factories** (Tokyo Major, Kyushu
Medium, Rehe Minor) plus **19 distinct existing map facilities**. The factories
are additional to those 19; rail borders are counted separately. Aircraft count
separately from carriers. Unlocated queue ships and off-board ability markers
are not included in these deployed-piece totals.

## Approved city and railway scoring

**Approved by the user, 21 October 2026.** These settle the final two campaign
choices in this review. Completed units already use full catalog value.

- **Cities:** the city label has no extra standalone asset price. Its income
  still contributes to wealth, and factories, ports and other facilities in it
  still count separately. For example, a city territory with a legally
  collectable 2-IPP income rate and a factory contributes 2 plus 0.1 times the
  factory's asset value, with no additional price for the city label.
- **Railways joining differently owned territories:** count each physical border
  connection once and divide its asset value equally between the two endpoint
  possessors. For example, an undamaged 2-IPP connection between Japanese and
  KMT territory would assign 1 IPP of assets to each, contributing 0.1 to each
  side's wealth. If both ends belong to one side, it receives the full value.
  An uncontrolled, unaligned minor's endpoint share counts toward nobody.
  This approved attribution assigns score; movement, supply and repair
  permissions still follow their own rules.

Mongolia scheduling, paid-construction scoring and whole-warlord alignment are
settled above. **The decision-review checklist item is complete.** The
[source reconciliation](/Users/home/Desktop/gwRL/docs/m0/source_reconciliation.md)
confirms the initial queue amounts: Heavy Cruiser **5 IPP paid / 5 remaining**;
Fleet Carrier **5 paid / 10 remaining**. Both are national queues with no initial
tile. Their already-paid total is **10 IPP**, separate from the **23 IPP** opening
cash. Placement still requires an eligible retained shipyard.

## Shared official-rule clarifications

The canonical list is now
[Rule clarifications and open questions](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md),
not a second set of rulings embedded in this scenario README.

- **RCL-001 adopted:** airborne step 4 fires attacking AAA (with both sides'
  fighters); step 5 fires defending AAA. One volley per regular AAA; city AA is
  separate, and facility AA is not an airborne-assault defense.
- **RCL-002 adopted:** the influence-spending cap is the unmodified success
  threshold, with payment before rolling and natural-12 backfire preserved.
- **RCL-003 adopted:** one alignment roll and one result for each whole warlord,
  using the faction's qualifying neighbors across all its territories.
- **RCL-004 closed:** on 17 October 2026, the user reported that the developers
  fixed the wording for the next version. The recorded rule requires the
  specified undamaged railroad to Soviet-possessed land, with the stated
  placement restriction; generic supply is insufficient. It remains inactive in
  this USSR-excluded campaign, including when Mongolia acts at the USSR turn
  position.
- **RCL-009 adopted:** follow Japan's national reference sheet. Japanese
  border-clash attacks may target Soviet units only in Chita, Amur and Primorsky
  Krai; Soviet possession of Mongolian territory adds no Japanese target. Normal
  clash and pact restrictions still apply. This campaign removes the mechanic's
  prerequisites by excluding USSR.
- **RCL-006 closed after checking:** evolution is immediate when possessed land
  totals 13+ IPP, including during another nation's turn. Income collection is
  separate; implementation sequencing is not an additional ruling to approve.
- **RCL-005 closed:** on 18 October 2026, the user reported the developers'
  clarification that only enemy Surface Warships prevent a blockade under the
  enemy-presence condition. Enemy submarines alone do not prevent one; all other
  blockade requirements still apply.
- **RCL-008 closed after checking:** the rulebook's nation/warlord classifications
  exclude Chinese warlords from ordinary neutral-nation diplomacy. No new ruling
  is needed; their special influence/alignment mechanics remain available.
- **RCL-007 closed after checking:** §6.6 already permits separation during
  Combat Movement, followed by breaking the truce during Combat and fighting
  in remaining shared zones. No declaration or prior commitment to breaking the
  truce is required during Combat Movement; the decision may be made in Combat.
  No retroactive movement is granted. Preserve normal movement/combat rules and the special
  KMT Low Morale consequence.
- **The current shared-rule register has no remaining open questions.**
  City/rail scoring is approved. Source reconciliation, scenario-data
  synchronization, verification and the M0 freeze are complete.

Future acceptance tests must check legal actions, prohibited actions and phase
ordering against the adopted interpretation. These are implementation tasks,
not additional tests the user must write. Documentation does not claim that
those handlers or tests already exist.

## Final deliverables and verification

The following artifacts reflect the frozen campaign. Original source
transcriptions for excluded factions and systems remain separately labeled;
they do not activate those mechanics in this scenario.

| File | Purpose / revision status |
| --- | --- |
| [Scenario contract](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/scenario_contract.json) | Frozen machine-readable scope, scoring, accounts and decisions; no pending decisions |
| [Japan setup data](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/japan_setup.json) / [audit](/Users/home/Desktop/gwRL/docs/m0/japan_setup_audit.md) | 48 deployed units, three factories, carrier assignments, setup-only values and two reconciled national queues |
| [China/minor setup data](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/china_minor_setup.json) / [audit](/Users/home/Desktop/gwRL/docs/m0/china_minor_setup_audit.md) | 51 retained units, direct Comintern control of Mongolia, preserved owner names and separately excluded FEC records |
| [Core rules ledger](/Users/home/Desktop/gwRL/docs/m0/core_rules_ledger.md) | Source-linked coverage and campaign applicability, including the settled clarification register |
| [Asset price audit](/Users/home/Desktop/gwRL/docs/m0/asset_price_audit.md) | Published catalog/repair costs, confirmed setup-only values and city/rail scoring |
| [Convoy audit](/Users/home/Desktop/gwRL/docs/m0/convoy_audit.md) / [data](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/convoy_audit.json) | Reference only for a future expanded profile; no longer required for this campaign |
| [Manifest](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/manifest.json) / [extracted map](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/map.json) | 37 nodes, 19 static facilities, no active convoy lines; deterministic extraction from the reviewed world map |
| [Source reconciliation](/Users/home/Desktop/gwRL/docs/m0/source_reconciliation.md) / [catalog source checks](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/catalog_source_checks.json) | Queue payments, research chart and rule/price source checks, with later catalog work identified |
| [M0 data tests](/Users/home/Desktop/gwRL/tests/test_m0_spec.py) | Verified setup, scope, provenance, accounts, queues, carrier assignments, scoring and exclusions |
| [Full milestone plan](/Users/home/Desktop/gwRL/docs/plans/japan_china_full_rules_plan.md) | M0 closed; subsequent state, catalog and rule implementation work remains |
| [Frozen baseline](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/frozen_baseline.json) | Versioned file hashes and verification record for this completed M0 specification |

The original setup audit inspected embedded setup-table images as well as text;
row-level citations and PDF hashes are in the JSON. It inherited geography from
the earlier map audit rather than independently re-tracing every border.

The final verification passes **all 106 Python tests**, including the revised
M0 and map-extraction checks:

```sh
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

The extracted map is reproducible, source hashes match, and `git diff --check`
passes. This verifies the data and specification boundary. Shared engine state,
the complete executable unit/damage catalog and rule handlers remain later
milestone work; these checks do not certify full-game play or training readiness.

- [x] Source setup and rule/price audits delivered.
- [x] Latest exclusions, preserved owner names, ship values, carrier setup,
  Mongolia timing, paid-construction scoring, adopted RCL-003 and closed RCL-004
  recorded.
- [x] Answered questions replaced with decisions and source reconciliation completed.
- [x] Settle the remaining campaign choices and affected rule interpretations
  (completed 21 October 2026, including city and railway scoring).
- [x] Synchronize the contract, setup data, manifest, extracted map, ledgers, plan
  and data tests; pass the complete Python verification suite.
- [x] Freeze the approved M0 contract as `M0-2026-10-21` with a hashed baseline.
  No additional user action is needed to finish M0.
