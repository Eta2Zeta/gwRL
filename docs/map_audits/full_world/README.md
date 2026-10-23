# Full-world map audit

**5 October 2026 — proposals for the entire world map.**

**Implemented, 7 October:** approved findings have been applied to the production
map; uncertain items remain deferred. See [implementation status](implementation.md)
for the current counts, files, validation and precise remaining limits. Everything
below describes the original audit baseline unless stated otherwise.

**Naval-facility revision, 6 October:** [the corrected port and naval-facility
roster](naval_facility_reaudit.md) compares the current map with the proposed
printed facilities territory by territory. The original conditional port-ID
examples were insufficiently reconciled with facility existence, type and access.
The revised source review replaces those examples; French Morocco and Southwest
Africa have no printed ports.

The current map needs substantial geographic correction. Missing territories and
sea cells, incorrect ocean shortcuts, phantom railways/ports, and wrong terrain
and IPP values occur well beyond the campaign theatre. The reports below describe
proposed additions, changes, deletions and unresolved items with before/after
values and local source evidence. The before-values are preserved from checkpoint
`eeb5e90`; the [implementation report](implementation.md) describes the updated map.

Every stored node and directed edge has been inventoried: **407 nodes (303 land,
104 sea), 1,612 directed edges, 806 reciprocal pairs**. All 407 nodes have regional
review records, and all 806 stored physical pairs have explicit source-review
outcomes. Directional terrain, rail, facilities and other attributes retain their
own checked-field scopes. The ledgers distinguish actual source ambiguities from
unresolved rule/schema questions and any unverified detailed attributes; confirming
a physical border does not certify every attribute attached to it.

The physical-pair results are **640 confirmed relations, 159 proposed removals
and 7 source ambiguities**. The deletion register lists every proposed pair
removal, including those grouped under a coast-replacement finding.

## Read the proposed work

| Register | Contents |
|---|---|
| [Additions](additions.md) | Missing territories, islands and numbered sea zones; missing real borders, coasts, crossings and infrastructure |
| [Changes](changes.md) | Corrected terrain, printed IPP, ownership identity, city flags, facility types/accesses and connection attributes |
| [Deletions](deletions.md) | False land/sea shortcuts, invented railways/ports and incorrect aggregate territory records |
| [Uncertain items](uncertain.md) | Source conflicts, small unresolved contacts, candidate replacement sets and incomplete route traces |
| [Mechanisms and schema](mechanisms_and_schema.md) | Additional geographic information worth storing, and what belongs in rules/setup/runtime data |
| [Corrected naval-facility roster](naval_facility_reaudit.md) | Rechecked ports, dockyards, shipyards and naval bases, with actual territory/sea access and explicit no-facility decisions |
| [Reconciliation](reconciliation.md) | Duplicate observations, alternative suggested IDs and dependencies between overlapping proposals |

Each finding has an ID, category, current value, proposed value, evidence,
confidence and scope notes. Some records group multiple edits. The current
record counts are in [audit_summary.json](data/audit_summary.json); they are
not counts of independent defects or fully verified nodes.

## Current map and campaign file locations

| Purpose | Location |
|---|---|
| Whole-world map data | [gw36_manual_map.json](../../../game_content/maps/gw36_manual_map.json) |
| Authoritative map generator | [build_manual_map_json.py](../../../tools/build_manual_map_json.py) |
| Original board image | [gw36map.png](../../../game_content/maps/gw36map.png) |
| Separate Home Country data | [gw36_nation_home_country.json](../../../game_content/maps/gw36_nation_home_country.json) |
| Campaign map and selection | [map.json](../../../game_content/scenarios/japan_china_1936/map.json), [manifest.json](../../../game_content/scenarios/japan_china_1936/manifest.json) |
| Campaign setup, rules and prior audits | [scenario directory](../../../game_content/scenarios/japan_china_1936/), [M0 documentation](../../m0/README.md) |

## Highest-impact findings

1. **The printed node roster is incomplete.** The proposals identify 54 missing
   sea IDs and 79 distinct missing land-zone identities after merging the
   Iceland/Faroe/Shetland overlaps. Examples include Sydney, Helsinki, Northern
   Ireland, large parts of Siberia, numerous Pacific islands and Atlantic/Indian
   coast islands. These are identified additions, not a claim that every new
   node's full border and infrastructure record is ready to import.
2. **Controlled sea passages are misplaced.** Proposed corrections include
   Gibraltar A44–M2, Panama A40–P76, Suez M8–I5, Turkish Straits M7–M10,
   Danish Straits A10–A12 and Kaiser-Wilhelm Kanal A11–A12. The current graph
   uses incorrect seas for several of them. The Caspian's false M11–M12 ocean
   connection should be removed.
3. **There are impossible land/rail shortcuts.** Examples include San
   Francisco–Chicago, Chicago–New York, Cuba–Hispaniola, Borneo–Java and
   Portuguese Timor–Northern Territory. Actual multi-tile routes and narrow
   crossings require their own proper representation.
4. **Terrain is systematically under-specified.** Four tiles use `forest` and
   Scotland uses `mountain_border` as intrinsic terrain. Several cities need
   underlying mountain terrain; many Indonesian and other tiles have simultaneous
   mountain/jungle terrain. The glossary supplies numerous missing directional
   mountain, desert, marsh and river approaches.
5. **Printed economic values need correction.** Examples: Washington **5→8**,
   San Francisco **4→6**, New York **4→5**, Eastern Germany **2→4**, Kiev **0→3**,
   Novosibirsk **1→3**, Scotland **2→1**. Regional tables list the complete
   proposed differences. These are printed territorial IPPs, not scenario cash
   or convoy loss limits.
6. **Facilities are incomplete and sometimes fictitious.** The world file has
   only seven intrinsic facility instances, despite many printed airbases. Four
   facility IDs also merge unrelated ports across ten territories. Actual
   physical instances and sea accesses must be preserved when correcting this.
7. **The victory-city set is wrong.** Six current flags are spurious. Calcutta
   lacks its flag and Sydney lacks its tile. Rulebook §3.2 p20 gives the exact
   ten-city set; the proposed changes preserve ordinary city status separately.
8. **Graph consistency hides source errors.** Every stored edge has a reverse
   and no references dangle, yet ten nodes are isolated; Wake/P36 form another
   isolated component; and 93 sea→sea directions use `normal` terrain. The
   generator's guessed reverse values and ownership-based gauge heuristic need
   correction in the authoring process.

## Additional information to include

The detailed schema report proposes:

- **Convoy lines** as single physical route records with endpoints, ordered seas,
  beneficiary and a shared printed loss cap. The current world JSON contains
  none; the earlier campaign convoy audit is a separate specification.
- **Typed canals, straits and exceptional routes**, including controllers,
  Baltic–White Sea Canal, Northern Sea Route and Burma/Ledo supply geography.
- **Complete narrow crossings**, including printed capacity, blocker seas and
  relevant facility/naval transit relationships.
- **Mode-specific geographic restrictions**, including Queensland's Great
  Barrier Reef approaches and impassable land borders that aircraft can fly over.
- **Actual rail gauge, rail-region membership, river-route/bank information,
  mixed terrain and source-linked review status.**

Keep **kamikaze zones/activation**, national abilities, conditional income and
objectives in rules profiles. Keep units, captures, damage, blockade state,
construction, convoy losses and relocated capitals in setup/runtime state.
Special-fortification coverage can remain a rules lookup using map IDs; it does
not imply a fortification starts on the printed board. Whole-zone rail coverage
under §13.2.8 should not acquire an invented requirement for a drawn spur to each port.

See [convoy review](convoy_review.md) for 16 geographic route proposals:
13 fully traced, one with a confirmed sea path and unresolved Philippine land
endpoint, and two inherited from the prior source audit. The register
preserves sea-terminal arcs, brief intermediate sea crossings and actual land
endpoints. The Soviet Arctic line has no printed numeric loss cap; its separate
conditional bonus belongs in the rules profile.

## Regional reports

- [Americas and Atlantic](regions/americas_atlantic.md)
- [Europe, Africa, Middle East and western USSR](regions/europe_africa_middle_east.md)
- [Asia, Siberia, Indian Ocean and Pacific](regions/asia_pacific.md)
- [Global structural and generator audit](generation_and_integrity.md)
- [Source hierarchy, crop coordinates and interpretation](source_method.md)

## Detailed inventories

| File | Purpose |
|---|---|
| [all_findings.json](data/all_findings.json) / [findings.csv](data/findings.csv) | Unified proposed-edit register with full values and evidence |
| [node_inventory.csv](data/node_inventory.csv) | All 407 current nodes and their stored attributes/neighbors |
| [identified_missing_nodes.json](data/identified_missing_nodes.json) | Explicit missing-node proposals, with the Shetland naming overlap merged |
| [proposed_sea_roster.json](data/proposed_sea_roster.json) | The 158 identified sea IDs: A1–A54, I1–I14, M1–M12 and P1–P78; current versus proposed status |
| [edge_inventory.csv](data/edge_inventory.csv) | All 1,612 current directed edges and their stored attributes |
| [review_coverage.json](data/review_coverage.json) / [CSV](data/review_coverage.csv) | Per-node regional evidence, reviewed fields, findings and explicit limits |
| [edge_review_coverage.json](data/edge_review_coverage.json) | Every stored direction; pointers to relevant endpoint findings without implied certification |
| [physical_connection_review.json](data/physical_connection_review.json) | Source review of each stored unordered pair, with overlapping regional conclusions retained |
| New-land neighbor tables: [Americas](data/americas_atlantic_new_node_neighbors.json), [Europe/Africa](data/europe_africa_middle_east_new_node_topology.json), [Asia/Pacific](data/asia_pacific_new_node_neighbors.json) | Source-reviewed contacts for the missing land identities, with explicit uncertain contacts |
| [Asia/Pacific sea matrix](data/asia_pacific_sea_neighbors.json) | Detailed sea-grid proposals; restricted routes remain separate from ordinary adjacency |
| [New Asia/Soviet land-edge rail ledger](data/asia_pacific_new_edge_rail_review.json) | All 64 proposed new land/narrow pairs: 16 rail crossings, 47 without rail and one source ambiguity; other regions include rail in their new-node tables |
| [structural_summary.json](data/structural_summary.json) / [diagnostics](data/structural_findings.json) | Reproducible graph checks; separate from source-backed geographic corrections |
| [input_manifest.json](data/input_manifest.json) | Source and production-file hashes |
| [rebuild_check.json](data/rebuild_check.json) | Both existing generators reproduce the current files byte-for-byte when redirected to temporary output |
| [validation_report.json](data/validation_report.json) | Final coverage, reference, reciprocal-proposal and source-preservation checks |
| [evidence/](evidence/) | Original-map diagnostic crops supporting the regional reports |

The glossary comparison tables and regional expected-node files are also in
`data/`. They record express source requirements, not default values for every
unlisted direction.

## Reproduce the audit reports

From the repository root:

```sh
./.venv/bin/python docs/map_audits/full_world/audit_structure.py
./.venv/bin/python docs/map_audits/full_world/consolidate.py
./.venv/bin/python docs/map_audits/full_world/rebuild_naval_reaudit.py
```

These commands update audit inventories/reports only. The source-authored regional
findings are inputs to consolidation. Resolve the uncertainties and reconcile
overlapping proposals before changing the authoritative map generator; regenerate
the world map and derived scenario maps only after those geographic edits are
deliberately applied.
