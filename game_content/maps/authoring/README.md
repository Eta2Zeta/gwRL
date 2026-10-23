# World-map authoring inputs

Edit reviewed facts here, then run `tools/build_manual_map_json.py`. The builder
starts from the legacy transcription, applies these explicit records, validates
the result, and writes `gw36_manual_map.json` plus `gw36_manual_map_review.json`.
It does not read the historical audit reports or require local image files.

| File | Purpose |
|---|---|
| `americas_atlantic.json`, `europe_africa_middle_east.json`, `asia_pacific.json` | Reviewed node and edge operations, field-specific evidence and finding dispositions. |
| `global_review.json` | Final physical deletions, global findings and deferred alternatives. |
| `naval_facilities.json` | Rechecked physical facility instances and accesses, including explicit empty or partial inventories. |
| `geographic_features.json` | Convoys, passages, exceptional routes, crossing blockers and coast restrictions. |
| `verified_existing_rail_gauges.json` | Individually verified printed track colors. Construction defaults and owners cannot supply these values. |
| `adopted_directional_values.json` | Existing Canadian and China-theatre decisions preserved from the checkpoint, explicitly labeled as adopted project values. |

Operation phases are node creation (10), node attributes (20), physical removals
(30), physical additions (40), adopted directions (45), border attributes (50/55)
and directed glossary attributes (60). A physical deletion takes precedence over
a field annotation. Attribute operations cannot create missing connections.
Reciprocal rail gauges swap their source and target sides; combat terrain and
river crossings are authored direction by direction.

New unreviewed attributes are `null`. Legacy values retained from the checkpoint
are not automatically certified: consult the generated review sidecar for exact
field scope. A confirmed physical adjacency does not certify its rail, terrain,
river or facility attributes. Preserve source references and finding IDs when
editing; mark deferred fields explicitly rather than choosing an alternative.

The canonical facility registry contains resolved physical instances only.
Unresolved Cape Town/Philippine details remain in the review sidecar, with partial
inventory status in the map so withheld details cannot be interpreted as absence.
Legacy node/coast arrays are compatibility projections of the registry.

See [implementation status](../../../docs/map_audits/full_world/implementation.md)
for the applied changes and remaining review items. Rule behavior belongs in
`game_content/rules/map_geography_rules.json`; setup, control, damage and use
counters belong to scenario or runtime state.
