# M10: completed campaign integration

> Completed milestone reference. Test counts, timings and next steps below describe this delivery. Use the [project guide](../README.md) for current status and instructions.

**Status: complete for the frozen 37-node campaign, 23 October 2026.** Two games
start from the unchanged approved July 1936 setup and finish all 44 national
turns through July 1941. Their 2,847 transitions pass replay, resource/identity
checks and structural/domain invariants after every transition. This certifies
the selected campaign; it does not claim global-map support or a trained agent.

The [integration evidence report](../archive/milestones/m10/integration_evidence_2026_10_23.md)
and [machine-readable summary](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/integration_evidence_2026_10_23.json)
record policy seeds, source hashes, terminal wealth and verification limits.

| Complete campaign | Evidence exercised | Review |
| --- | --- | --- |
| Early invasion, seed 1936; 1,558 transitions | Warlord conversion, evolution, land/air/naval battles, amphibious assaults, research, purchases and placement | [Offline viewer](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/mixed_seed_1936/index.html), [replay evidence](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/mixed_seed_1936/trace.json) |
| Delayed Japanese war, seed 1941; 1,289 transitions | Warlord conversion, evolution, actual Japanese Major-war declaration and Surprise Attack, land/air/economy play and naval movement | [Offline viewer](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/delayed_seed_1941/index.html), [replay evidence](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/delayed_seed_1941/trace.json) |

The [runtime evidence ledger](/Users/home/Desktop/gwRL/docs/m10/runtime_coverage_ledger.md)
indexes all 143 M0 rows. Its [JSON evidence](/Users/home/Desktop/gwRL/docs/m10/runtime_coverage_ledger.json)
contains named runtime entry points, exact executable assertion text and evidence
hashes: 120 runtime/fixture rows, 21 inactive rows and two approved replacements.
Catalog entries alone are not accepted as runtime coverage. Ordinary diplomacy
has no eligible neutral Minor target in this profile; its absent roll handler is
explicitly outside this certification.

Conditional Chinese Truce, neutral relocation, third-party port evacuation and
carpet bombing use focused runtime fixtures. They are not attributed to the two
complete games. The Truce fixtures include a legal Japanese conquest and Chinese
land gift that triggers evolution; the carpet fixture requires immediate return
after round one, checkpoints during that choice, preserves ordinary aircraft for
round two and replays exactly. The recorded integration evidence predates the
RCL-014 role correction: evacuating ships now defend and the fleet already at
sea attacks, following the developer clarification. RCL-015 retains the user's
provisional adoption, with no publisher confirmation claimed.

The integration audit fixed actual source-backed failures: temporary independent
warlord defense and reciprocal war cleanup; nearest-Friendly neutral relocation;
Motorized towing; Rocket casualty restrictions; executable Chinese-gift withdrawal
with shared transport capacity; segmented movement past an unresolved hostile
battle; berthing before mandatory landing/withdrawal; actual naval-air declaration
context and combat commitments; combined adjacent/amphibious attacks; and immediate
carpet-bomber returns. These are implementation fixes, not invented rule questions.

Five integration fixture groups include 240 bounded random legal
choice/chance/interrupt transitions, explicit invalid-state diagnostics and exact
replay. Public tiny and composition environments call the same authoritative
`campaignRules()` factory, expose entitled choices and actual dice, and retain
explicit benchmark production/horizon/roster settings. Their nine boundary
regressions pass. Historical models/results retain their old schemas; no new
training result is claimed.

The [22 October partial checkpoint](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/checkpoint_2026_10_22.json)
and [RCL-015 source audit](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/rcl015_reachability_2026_10_23.json)
remain historical records. Earlier accounting-only calendar checks are not
presented as these completed combined campaign traces. M11 search/API validation
is recorded separately in [M11](/Users/home/Desktop/gwRL/docs/m11/README.md).
