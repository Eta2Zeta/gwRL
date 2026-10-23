# M10 integration evidence, 23 October 2026

M10 verification of the approved 37-node Japan/China July1936–July1941 campaign; not a global-map certification or learning result.

Both generated games start through `Engine::start(loadScenario(...))` from the unchanged approved 99-piece July 1936 setup. They finish all 44 national turns, eleven each for CCP, Mongolia, Japan and KMT, at the full July 1941 endpoint. The combined evidence contains 2,847 action/chance/interrupt transitions and 2,849 initial/transition invariant checks. Authoritative C++ replay is exact for both games; the saved deltas, event batches, terminal unit boards and current source hashes also pass the independent verifier.

Definition fingerprint: `7167b2570851dfe260f2a094a737d9ccd0da76ccdf16b10d7e70952bdec1472e`.

| Policy / seed | Transitions | Chance transitions | Reviewable artifact |
| --- | ---: | ---: | --- |
| Early invasion / 1936 | 1,558 | 258 | [Offline viewer](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/mixed_seed_1936/index.html); [replay evidence](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/mixed_seed_1936/trace.json) |
| Delayed Major war / 1941 | 1,289 | 161 | [Offline viewer](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/delayed_seed_1941/index.html); [replay evidence](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/delayed_seed_1941/trace.json) |

The early-invasion game includes 80 land-battle starts, nine actual naval-air declarations and nine naval-battle starts, ten amphibious preparation resolutions, 22 research attempts, 74 purchases and 75 placement actions. Both games contain legal warlord ownership changes and immediate Chinese evolution. The delayed-war game contains Japan’s actual declaration against evolved KMT and the selected Beiping Surprise Attack in January 1940. These are deliberately non-optimal integration policies; they are not trained agents or gameplay recommendations.

The complete games do not claim to exercise Chinese Truce, carpet bombing, or every technology branch. The focused runtime suites cover conditional cases, including source-valid capture → Chinese gift → evolution → shared Truce combat, developer-reported third-party combat roles, user-adopted Low Morale and no-destination relocation consequences, third-party port evacuation, and immediate first-round carpet-bomber return. The carpet fixture checks clone/checkpoint identity during the return decision, preserves ordinary aircraft for round two, and replays exactly.

The [runtime evidence index](/Users/home/Desktop/gwRL/docs/m10/runtime_coverage_ledger.md) maps all 143 M0 IDs to named handlers plus executable behavior assertions, or a frozen-profile inactive/replacement reason. Its [JSON](/Users/home/Desktop/gwRL/docs/m10/runtime_coverage_ledger.json) records exact assertion text and source hashes: 120 runtime/fixture rows, 21 inactive rows, and two approved policy replacements. Ordinary diplomacy has no eligible neutral Minor target in this profile; its absent roll handler is not represented as implemented.

The five new integration fixture groups verify domain diagnostics, an actual first national turn with replay, immediate carpet bombing return, rejected unsupported creation, and 240 bounded random legal action/chance/interrupt transitions. Nine public benchmark boundary regressions pass after tiny/composition environments were changed to call the same authoritative `campaignRules()` factory. Six focused air/land/integration CTest suites passed; the root completion record contains the broader final C++/Python run.

The standalone viewer controls and final unit-board reconstruction passed a Node smoke check. This checks controls/data consistency; it does not claim screenshot-based visual verification.

## Invariants checked

- State structural validation after every transition.
- symmetric wars.
- one unresolved land attack per attacking unit.
- transport type/cargo eligibility and capacity; weighted carrier slots.
- land units at sea must be carried; ships on land require a matching berth.
- facility usage cannot exceed beginning-of-turn capacity, including technology.
- no unlanded active aircraft past Noncombat or at terminal.
- new IDs never reused and every created unit has completed placement, recruitment, or ship-crew source.
- construction payments conserve treasury against paid work.
- financial and roll-declaration actions cannot remove deployed units.

## Reproduce evidence checks

```sh
python3 tools/build_campaign_coverage.py --check
python3 tools/verify_campaign_trace.py --current game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/mixed_seed_1936/trace.json game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/delayed_seed_1941/trace.json
node tools/verify_campaign_trace_viewer.mjs game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/mixed_seed_1936/index.html game_content/scenarios/japan_china_1936/m10/traces/2026_10_23/delayed_seed_1941/index.html
```

The [machine-readable summary](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/integration_evidence_2026_10_23.json) includes trace/viewer SHA256 values, policy seeds, terminal wealth, counts, and the precise limits of this evidence. Every complete trace embeds its original/final engine checkpoints and recorded history; the generator verifies authoritative replay before marking the export complete.
