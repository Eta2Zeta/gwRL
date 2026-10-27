# Regional campaign contract

For current development and learning status, start with the [project guide](../README.md).
This reference describes the approved scenario and scoring choices. It is a closed
regional use of the shared v4.3 rules, not the full global game.

## Scope and calendar

| Choice | Approved contract |
| --- | --- |
| Map | 37 retained nodes: 31 land zones and P14/P15/P16/P32/P33/P41; every outside neighbor is removed |
| Start | Official July 1936 pieces on included zones; no relocation of excluded forces or invisible outside reinforcements |
| Full endpoint | After the complete July 1941 round, including national turns, reactions and income collection: eleven rounds |
| Policies | Axis, Allies and Comintern; national identities, treasuries and permissions stay separate |
| Turn order | CCP → Mongolia in the USSR slot → Japan → KMT |
| Mongolia | Separate minor identity, controlled directly by Comintern; this creates no Soviet participant, account or ownership |
| Exclusions | Tannu Tuva, Hong Kong and FEC/USSR participation; convoys, interdiction and Kido Butai |
| Retained naval rules | Ordinary blockades, Maritime Air Patrol, transport, supply and amphibious operations remain applicable |
| Short curricula | Same approved starting setup/rules and an explicit shorter calendar endpoint; execution cutoffs remain separate |

The [manifest](../../game_content/scenarios/japan_china_1936/manifest.json) selects
the actual zones; the [scenario data guide](../../game_content/scenarios/japan_china_1936/README.md)
explains extraction and file layout. Original map labels and original nationality
are preserved independently of later possession, alignment and policy control.

## Setup and accounts

The retained setup contains 99 deployed pieces: Japan 48, KMT 12, CCP 5, eight
unaligned warlords 32 and Mongolia 2. It includes three setup factories and 19
other physical facilities. The user's warlord names are preserved; initial Ma
Clique possession of Tsinghai can change through legal play.

Japan starts with 15 IPP, KMT 6, CCP 2 and uncontrolled minors zero. The local
cash derivation caps official starting cash by retained directly possessed original
land income. These are approved theatre accounts, not an official alternate setup.

Japan also retains a Heavy Cruiser in queue #2 (5 IPP paid, 5 remaining) and a
Fleet Carrier in queue #3 (5 paid, 10 remaining), with no invented starting tile.
Past payments are separate from opening cash. Completion requires an eligible
retained shipyard; Capital Ships require a Major Shipyard. USA-triggered Light
Carrier reinforcements are excluded. P15's deployed Fleet Carrier carries one
Fighter and one Tactical Bomber; its Light Carrier carries one Fighter.

Setup-only Torpedo Boat Destroyers and Coastal Submarines use approved wealth
values of 5 and 4 IPP respectively. Those values do not make them buildable.
Excluded FEC units and facilities remain source evidence only.

## Objective

For alliance `i`:

```text
W_i = current legally collectable income-per-turn rate
      + 0.1 × (completed net assets + treasury + paid unfinished construction)
R_i = W_i - W_other_1 - W_other_2
completed net asset value = purchase price - remaining repair price
```

Income is the current rate, not cumulative collections. Setup/recruited assets
count. Controlled-minor assets belong to their controlling alliance for scoring;
uncontrolled assets receive no alliance credit. This does not pool national cash
or grant military permissions. Intermediate reward is zero, gamma is one, and
terminal returns retain all three components; the objective is general-sum.

Unfinished construction counts only cumulative paid amounts. On completion,
replace that entry with the completed asset value without double counting.
There is no added depreciation or zero floor: zero-cost Capital Ship repairs
create no monetary deduction, and a facility can have negative net asset value.
A city label has no extra asset price. Count each physical facility once and each
undirected railway border once, dividing railway value equally between endpoint
possessors. This attribution changes score, not movement or repair permissions.

## Rules, evidence and compatibility

Reusable rule interpretations live in the [clarification register](../../game_content/rules/clarifications.md).
The [applicability ledger](rules-ledger.md) defines the regional requirements;
[runtime coverage](runtime-coverage.md) locates current implementation evidence.
The [engine](engine.md), [politics](politics.md), [movement](movement.md),
[economy](economy.md) and [combat](combat.md) references explain their interfaces.

The original [specification review](../archive/milestones/m0/overview.md),
[setup audits](../archive/milestones/m0/japan_setup_audit.md),
[China/minor audit](../archive/milestones/m0/china_minor_setup_audit.md),
[asset prices](../archive/milestones/m0/asset_price_audit.md) and
[source reconciliation](../archive/milestones/m0/source_reconciliation.md)
preserve the decision and source evidence. The
[frozen baseline](../../game_content/scenarios/japan_china_1936/m0/frozen_baseline.json)
records its original version. Source-audit labels such as “not playable” describe
those data artifacts at their creation, not today's complete CPU engine.

Frozen JSON records retain original document paths and checksums because they
also affect rule and neural-input fingerprints. The archive manifest resolves
historical document locations; current guides use topic paths. One small
`docs/m0/README.md` compatibility pointer keeps the checksum-pinned register's
literal link valid. No milestone report remains there.
