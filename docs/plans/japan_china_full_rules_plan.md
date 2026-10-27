# Regional campaign contract and milestone map

For current progress and next work, start with the [project guide](../README.md).
This page locates the approved campaign contract and its implementation records.
The original detailed implementation plan is preserved in the
[planning archive](../archive/planning/README.md).

## Approved campaign

The [scenario manifest](../../game_content/scenarios/japan_china_1936/manifest.json),
[scenario guide](../../game_content/scenarios/japan_china_1936/README.md) and
[M0 review](../m0/README.md) define the approved setup and accounting. The
[frozen baseline](../../game_content/scenarios/japan_china_1936/m0/frozen_baseline.json)
records its original verification. These files remain at their established paths.

| Choice | Contract |
| --- | --- |
| Geography | Closed 37-node projection: 31 land zones and six sea zones; no off-map agents, routes or reinforcements |
| Start | Approved July 1936 setup, including 99 deployed pieces and the retained Japanese construction queues |
| Full endpoint | After the complete July 1941 round: eleven rounds, including all national turns and reactions |
| Agents | Axis, Allies and Comintern; nations, accounts, controllers and minor identities stay separate |
| Calendar | CCP → Mongolia in the USSR slot → Japan → KMT |
| Outside scope | No FEC/USSR accounts; no convoy play, interdiction or Kido Butai |
| Short curricula | Same starting setup and rules, explicitly shorter real endpoint; execution cutoffs are separate |

Each alliance maximizes its own terminal wealth minus the other two alliances'
combined wealth. Intermediate rewards are zero. Wealth is current income rate
plus 0.1 times completed net assets, treasury and already-paid unfinished
construction. Completed asset value deducts remaining repair price. City labels
add no asset price; physical facilities count once; each undirected railway border
counts once, split equally between its endpoint possessors. Controlled-minor
assets are attributed to their controlling alliance; uncontrolled assets have no
alliance credit. The M0 sources specify exceptions and exact setup payments.
This is the approved learning objective, not the official global victory condition.

Reusable unclear rules and rulings belong in the
[clarification register](../../game_content/rules/clarifications.md). The register
is the place to check their current status; this page does not duplicate an RCL
status list. Scenario-specific decisions remain in the M0/scenario records.

## Delivered implementation gates

M0–M12 are complete for this regional profile. The dependency order was frozen
contract → identities/state/catalog → politics/movement/economy → land/air/naval
combat → campaign integration → search → learning operations. The
[reference index](../reference.md) links each milestone and its source coverage.

Two M10 traces completed all 44 national turns. M11 checked explicit player and
chance ownership, three-component returns and stochastic search against small
oracles. M12 checked neural learning, held-out evaluation and exact interruption/
resume. These are scoped implementation and operational checks, not evidence of
strong play. Dated measurements retain their original code versions in the archive.

## Current development gates

The [learning guide](../stage_a/README.md) records actual training/evaluation
results. The [GPU guide](../gpu/README.md) records supported components and what
remains before whole-game replacement. The shared CPU engine remains the complete
baseline while GPU work proceeds.

Rule correctness, exact state/replay behavior and practical training efficiency
remain joint requirements. Preserve all legal choices and dice distributions;
compare matched completed workloads and peak memory. Changes to code, rules,
scenario, input schema or learning settings require compatibility checks before
continuing saved training. See the [development guide](../development.md).
