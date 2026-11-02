# M10: completed campaign integration

The frozen 37-node campaign plays from the approved July 1936 setup through all
44 national turns to July 1941, with replay, resource and identity checks and
structural and domain invariants after every transition. Two complete games
(seeds 1936 and 1941, 2,847 transitions) certified it on 23 October 2026; the
[project history](../history.md) describes them. This covers the selected
campaign; it does not claim global-map support or a trained agent.

The [runtime evidence ledger](runtime_coverage_ledger.md) indexes all 143 M0 rows.
Its [JSON evidence](runtime_coverage_ledger.json) contains named runtime entry
points, exact executable assertion text and evidence hashes: 120 runtime/fixture
rows, 21 inactive rows and two approved replacements. Catalog entries alone are
not accepted as runtime coverage. Ordinary diplomacy has no eligible neutral
Minor target in this profile; its absent roll handler is explicitly outside this
certification. Rebuild the ledger with `python3 tools/build_campaign_coverage.py`
after changing handlers or fixtures; `--check` reports whether it is current.

Conditional Chinese Truce, neutral relocation, third-party port evacuation and
carpet bombing use focused runtime fixtures. The Truce fixtures include a legal
Japanese conquest and Chinese land gift that triggers evolution; the carpet
fixture requires immediate return after round one, checkpoints during that
choice, preserves ordinary aircraft for round two and replays exactly. Following
the developer clarification (RCL-014), evacuating ships defend and the fleet
already at sea attacks. RCL-015 retains the user's provisional adoption, with no
publisher confirmation claimed.

The integration audit fixed actual source-backed failures: temporary independent
warlord defense and reciprocal war cleanup; nearest-Friendly neutral relocation;
Motorized towing; Rocket casualty restrictions; executable Chinese-gift withdrawal
with shared transport capacity; segmented movement past an unresolved hostile
battle; berthing before mandatory landing/withdrawal; actual naval-air declaration
context and combat commitments; combined adjacent/amphibious attacks; and immediate
carpet-bomber returns. These are implementation fixes, not invented rule questions.

Five integration fixture groups include 240 bounded random legal
choice/chance/interrupt transitions, explicit invalid-state diagnostics and exact
replay. M11 search and API validation is described in [M11](../m11/README.md).
