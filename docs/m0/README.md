# M0 review: July 1936–July 1941 closed China campaign

Updated: 6 October 2026. **User decisions recorded; M0 still has open review
items.** This is a scenario specification, not an implemented full-rules game.

**Revision scope:** this README records the latest campaign decisions; the shared
[rule clarification register](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md)
separately records unclear official rules. Together they
supersede conflicting recommendations in the earlier M0 audit. Related rule
notes, including the JSON interpretation notes for RCL-003/004, have been
corrected. The setup inventories, scenario contract, manifest and extracted map
have **not yet been fully synchronized** with this revision. They still describe the
earlier 38-node, 103-piece scope, including FEC and Soviet control of Mongolia.
Do not treat those older counts or pending-price fields as the approved new setup.
The detailed audits/plan now link to the rule register but otherwise retain
historical scope unless explicitly corrected. No engine changes or training were
performed in this revision.

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
  with the completed ship's full catalog value; never count both. Determining
  each starting queue's numeric paid amount is source reconciliation, not an
  outstanding choice of scoring method.
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

## Projected inventory after the exclusions

These are reconciled projections from the earlier source audit, **not a claim
that the JSON or extracted map has already changed**.

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

## Remaining campaign-specific details

**City and cross-owner rail assets** remain a scoring choice. Completed units
already use full catalog value. The two recommendations awaiting a decision are:

- **Cities:** give the city itself no extra standalone asset price. Its income
  still contributes to wealth, and factories, ports and other facilities in it
  still count separately. For example, a city territory with a legally
  collectable 2-IPP income rate and a factory contributes 2 plus 0.1 times the
  factory's asset value, with no additional price for the city label.
- **Railways joining differently owned territories:** count each physical border
  connection once and divide its asset value equally between the two endpoint
  possessors. For example, an undamaged 2-IPP connection between Japanese and
  KMT territory would assign 1 IPP of assets to each, contributing 0.1 to each
  side's wealth. If both ends belong to one side, it receives the full value.
  This proposal assigns score; movement, supply and repair permissions still
  follow their own rules.

Mongolia scheduling, paid-construction scoring and whole-warlord alignment are
settled above. The exact starting paid-stage amounts still need source
reconciliation before initializing the queues; the earlier 5-IPP-per-ship
figures remain candidates, not newly approved numeric setup values.

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
- **RCL-004 adopted:** CCP Comintern Brothers requires the specified undamaged
  railroad to Soviet-possessed land, with the stated placement restriction;
  generic supply is insufficient. It remains inactive in this USSR-excluded
  campaign, including when Mongolia acts at the USSR turn position.
- **RCL-009:** Soviet border-clash geography remains open for larger scenarios;
  this campaign removes its prerequisites.
- **RCL-006 closed after checking:** evolution is immediate when possessed land
  totals 13+ IPP, including during another nation's turn. Income collection is
  separate; implementation sequencing is not an additional ruling to approve.
- **RCL-005, RCL-007 and RCL-008:** blockade wording, Chinese Truce
  breaking/separation timing and ordinary warlord diplomacy remain proposed/open.

Future acceptance tests must check legal actions, prohibited actions and phase
ordering against the adopted interpretation. These are implementation tasks,
not additional tests the user must write. Documentation does not claim that
those handlers or tests already exist.

## Earlier audit deliverables and verification status

These remain useful source evidence, but **their campaign applicability and
pending decisions must be updated to match this README before M0 is frozen**.
Their original source transcriptions should not be destroyed just because this
smaller scenario excludes a faction or system.

| File | Purpose / revision status |
| --- | --- |
| [Scenario contract](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/scenario_contract.json) | Earlier machine-readable contract; exclusions, values, carrier allocation and pending items need synchronization |
| [Japan setup data](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/japan_setup.json) / [audit](/Users/home/Desktop/gwRL/docs/m0/japan_setup_audit.md) | Source units, factories and queues; the missing-price, USA-carrier and attachment questions are resolved above |
| [China/minor setup data](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/china_minor_setup.json) / [audit](/Users/home/Desktop/gwRL/docs/m0/china_minor_setup_audit.md) | Earlier inventory includes FEC and Soviet-controlled Mongolia; preserve the user owner-name mappings |
| [Core rules ledger](/Users/home/Desktop/gwRL/docs/m0/core_rules_ledger.md) | Source-linked rule coverage; disable excluded-system requirements for this profile |
| [Asset price audit](/Users/home/Desktop/gwRL/docs/m0/asset_price_audit.md) | Published catalog/repair costs; the two user-supplied reference values are recorded above |
| [Convoy audit](/Users/home/Desktop/gwRL/docs/m0/convoy_audit.md) / [data](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/convoy_audit.json) | Reference only for a future expanded profile; no longer required for this campaign |
| [Manifest](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/manifest.json) / [M0 data tests](/Users/home/Desktop/gwRL/tests/test_m0_spec.py) | Still target the earlier scope; update and regenerate before claiming the revised setup is verified |
| [Full milestone plan](/Users/home/Desktop/gwRL/docs/plans/japan_china_full_rules_plan.md) | Earlier dependency plan; convoy/Soviet/FEC requirements are superseded here |

The original setup audit inspected embedded setup-table images as well as text;
row-level citations and PDF hashes are in the JSON. It inherited geography from
the earlier map audit rather than independently re-tracing every border.

The original M0 batch passed **72 Python tests, including 15 M0 data tests**.
That historical result validates the earlier data snapshot, not the new scope
or future game mechanics. This documentation-only revision does not certify the
unsynchronized scenario files or execute training.

- [x] Source setup and rule/price audits delivered.
- [x] Latest exclusions, preserved owner names, ship values, carrier setup,
  Mongolia timing, paid-construction scoring and adopted RCL-003/004 recorded.
- [x] Answered questions replaced with decisions; remaining choices explained above.
- [ ] Settle the remaining campaign choices and affected rule interpretations.
- [ ] Synchronize the contract, setup data, manifest, extracted map, ledgers, plan
  and data tests; then re-run the short verification suite.
- [ ] Freeze the approved M0 contract before proceeding to the affected shared
  state/catalog and rule implementations. No full-rules training is ready yet.
