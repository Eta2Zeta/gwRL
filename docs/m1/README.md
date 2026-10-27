# M1: world-to-theatre bridge

> Completed milestone reference. Test counts, timings and next steps below describe this delivery. Use the [project guide](../README.md) for current status and instructions.

Status: **complete and verified on 21 October 2026**. All **119 repository Python
tests pass**, including **52 bridge, geographic-feature and faction tests**.

The bridge extracts the approved closed Japan–China theatre from the world map
and supplies canonical faction identities for later state loading. It preserves
the M0 scenario decisions. No user decision is required for this milestone.

## Outputs

- [Map builder](/Users/home/Desktop/gwRL/tools/build_theatre_scenario.py),
  [manifest](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/manifest.json)
  and [generated map](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/map.json).
- [Faction identity bridge](/Users/home/Desktop/gwRL/tools/scenario_factions.py)
  and [generated faction index](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m1/faction_index.json).
- [Verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m1/verification.json),
  including artifact hashes and checks against the historical M0 baseline.

The map contains **37 nodes** (31 land and 6 sea), **160 directed internal
edges**, **19 physical map facilities** and **47 recorded boundary cuts**.
The three additional setup factories remain in the M0 setup specification.
No active convoy line is exported. Excluded world nodes and source routes
remain in the original world map.

The identity bridge resolves retained map labels, printed setup labels and
canonical IDs to the same faction. For example, `Zhili Clique` and
`ZhiliClique` resolve to `warlord_beiping_hopeh`. It preserves the user's display
names. Unknown or ambiguous identities are errors; they do not silently become
KMT or another nation. Mongolia retains its own identity, with direct Comintern
control recorded separately in the M0 specification.
An explicit starting-owner override does not rewrite original nationality.

## Acceptance evidence

| Requirement | Evidence |
| --- | --- |
| Explicit approved geography | Exact canonical-ID fixture covers all 37 selected nodes, excludes Hong Kong and Tannu Tuva, and retains P41. |
| Lossless node and internal-edge projection | Every retained field equals the world source, including directional terrain/river differences, reciprocal infrastructure and unknown source values. |
| Physical facilities retain identity | Nanking's P14/P32 access points share one port ID; Honshu's two shipyards remain distinct; removed coast accesses do not create facilities. |
| Closed boundaries | Every removed neighbor appears in the cut report; no cut remains traversable. Retained crossings must include their required blocking seas. |
| Valid geographic features | Facility and route references are validated; incomplete outside routes are cut rather than reconstructed. Convoys are disabled by the approved profile. |
| Stable provenance and reproduction | Source/manifest hashes, source warnings and the exact manifest are embedded. Temporary regeneration produces byte-identical output without changing inputs. |
| Canonical faction identities | All 31 land owners map to the approved canonical factions. Compact legacy names resolve consistently; unknown and conflicting aliases fail. |

The existing bridge checks are in
[test_theatre_extractor.py](/Users/home/Desktop/gwRL/tests/test_theatre_extractor.py),
[test_theatre_scenario.py](/Users/home/Desktop/gwRL/tests/test_theatre_scenario.py)
and [test_world_map_features.py](/Users/home/Desktop/gwRL/tests/test_world_map_features.py).
The identity checks are in
[test_scenario_factions.py](/Users/home/Desktop/gwRL/tests/test_scenario_factions.py).

## Verification and scope

From the repository root:

```sh
./.venv/bin/python tools/build_theatre_scenario.py
./.venv/bin/python tools/scenario_factions.py
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

The [M0 baseline](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/frozen_baseline.json)
remains the historical freeze record. M1 adds an identity sidecar and updates
milestone progress in the implementation plan. It does not change the frozen
scenario contract, setup, manifest or map. The M1 verification record distinguishes
these progress notes from a change to the approved M0 specification.

This milestone establishes the static map and identity bridge. Source-unknown
rail-region membership and navigable river routes remain explicitly marked as
unknown. It does not implement movement, supply, production, combat, mutable
game state or training. Those belong to M2 and later milestones in the
[implementation plan](/Users/home/Desktop/gwRL/docs/plans/japan_china_full_rules_plan.md).
