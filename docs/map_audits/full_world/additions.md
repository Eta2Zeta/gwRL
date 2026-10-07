# Additions — complete finding register

397 finding records. Group findings may contain multiple fields or nodes; these are not edit counts.

Proposals only. Apply neither uncertain values nor incomplete new-node records automatically. Each confidence rating applies only to the described fields. Regional reports explain dependencies and unresolved source coverage.

See [overview](README.md), [mechanism proposals](mechanisms_and_schema.md), and [machine-readable register](data/all_findings.json).

**Naval facilities were rechecked on 6 October 2026.** Start with the [corrected current-to-proposed facility roster](naval_facility_reaudit.md) for ports, dockyards, shipyards and naval bases. Earlier conditional port-ID renaming examples must not be applied as a list of real facilities.

## WG-019 — Add source-traced Europe-America Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_can_nova_scotia`, `land_gbr_southern_england`, `sea_a18`, `sea_a19`, `sea_a20`, `sea_a21`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "Europe-America Line",
  "observed_loss_cap": 5,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "britain",
  "complete_path": [
    "sea_a18",
    "sea_a19",
    "sea_a20",
    "sea_a21"
  ],
  "endpoints": [
    {
      "kind": "land",
      "node_id": "land_can_nova_scotia"
    },
    {
      "kind": "land",
      "node_id": "land_gbr_southern_england"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_canada_start.jpg
- evidence/root_atlantic_north.jpg

**Scope / dependency:** Nova Scotia port to Southern England port; the land endpoints are not Canada/UK sea arcs. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-020 — Add source-traced Atlantic Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_gbr_southern_england`, `sea_a44`, `sea_a21`, `sea_a28`, `sea_a27`, `sea_a35`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "Atlantic Line",
  "observed_loss_cap": 6,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "britain",
  "complete_path": [
    "sea_a21",
    "sea_a28",
    "sea_a27",
    "sea_a35",
    "sea_a44"
  ],
  "endpoints": [
    {
      "kind": "land",
      "node_id": "land_gbr_southern_england"
    },
    {
      "kind": "sea",
      "node_id": "sea_a44"
    }
  ]
}
```

**Evidence:**

- evidence/root_atlantic_north.jpg
- evidence/root_convoy_atlantic_27_28.jpg
- evidence/root_atlantic_middle.jpg

**Scope / dependency:** The diagonal crosses A28 into the narrow southern extension of A27 before A35; do not shortcut A27. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-021 — Add source-traced Mediterranean Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_a44`, `sea_m8`, `sea_m2`, `sea_m4`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "Mediterranean Line",
  "observed_loss_cap": 6,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "britain",
  "complete_path": [
    "sea_a44",
    "sea_m2",
    "sea_m4",
    "sea_m8"
  ],
  "endpoints": [
    {
      "kind": "sea",
      "node_id": "sea_a44"
    },
    {
      "kind": "sea",
      "node_id": "sea_m8"
    }
  ]
}
```

**Evidence:**

- evidence/root_atlantic_middle.jpg
- evidence/root_convoy_med.jpg

**Scope / dependency:** Both ends have sea-terminal arcs. The M8 arc is just above the Lower Egypt dockyard; it does not make this a land endpoint. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-022 — Add source-traced West African Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_a44`, `sea_a54`, `sea_a46`, `sea_a48`, `sea_a50`, `sea_a51`, `sea_a53`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "West African Line",
  "observed_loss_cap": 3,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "britain",
  "complete_path": [
    "sea_a44",
    "sea_a46",
    "sea_a48",
    "sea_a50",
    "sea_a51",
    "sea_a53",
    "sea_a54"
  ],
  "endpoints": [
    {
      "kind": "sea",
      "node_id": "sea_a44"
    },
    {
      "kind": "sea",
      "node_id": "sea_a54"
    }
  ]
}
```

**Evidence:**

- evidence/root_atlantic_middle.jpg
- evidence/root_atlantic_south.jpg
- evidence/root_convoy_south_africa.jpg

**Scope / dependency:** Separate sea-terminal arcs at the Gibraltar-side junction and Cape Town-side junction. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-023 — Add source-traced East African Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_a54`, `sea_i4`, `sea_i1`, `sea_i3`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "East African Line",
  "observed_loss_cap": 1,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "britain",
  "complete_path": [
    "sea_a54",
    "sea_i1",
    "sea_i3",
    "sea_i4"
  ],
  "endpoints": [
    {
      "kind": "sea",
      "node_id": "sea_a54"
    },
    {
      "kind": "sea",
      "node_id": "sea_i4"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_south_africa.jpg
- evidence/root_indian_ocean.jpg
- evidence/root_convoy_aden_detail.jpg

**Scope / dependency:** Passes west of Madagascar through I1/I3. The I4 terminal arc adjoins the continuing Indian Ocean Line off Aden. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-024 — Add source-traced Indian Ocean Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_i5`, `sea_p50`, `sea_i4`, `sea_i7`, `sea_i12`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "Indian Ocean Line",
  "observed_loss_cap": 1,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "fec",
  "complete_path": [
    "sea_i5",
    "sea_i4",
    "sea_i7",
    "sea_i12",
    "sea_p50"
  ],
  "endpoints": [
    {
      "kind": "sea",
      "node_id": "sea_i5"
    },
    {
      "kind": "sea",
      "node_id": "sea_p50"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_suez_full.jpg
- evidence/root_convoy_aden_detail.jpg
- evidence/root_indian_ocean.jpg
- evidence/root_convoy_singapore.jpg

**Scope / dependency:** Starts at a Red Sea arc in I5 below Lower Egypt, continues past the East African terminal in I4, and ends at its own Singapore-side P50 arc. It does not enter I11. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-025 — Add source-traced East Asian Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_p50`, `land_aus_new_south_wales`, `sea_p59`, `sea_p60`, `sea_p62`, `sea_p63`, `sea_p64`, `sea_p71`, `sea_p72`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "East Asian Line",
  "observed_loss_cap": 2,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "anzac",
  "complete_path": [
    "sea_p50",
    "sea_p59",
    "sea_p60",
    "sea_p62",
    "sea_p63",
    "sea_p64",
    "sea_p71",
    "sea_p72"
  ],
  "endpoints": [
    {
      "kind": "sea",
      "node_id": "sea_p50"
    },
    {
      "kind": "land",
      "node_id": "land_aus_new_south_wales"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_singapore.jpg
- evidence/root_convoy_east_asian_java.jpg
- evidence/root_convoy_far_east.jpg
- evidence/root_convoy_australia_end.jpg
- evidence/root_convoy_sydney_end.jpg

**Scope / dependency:** Printed name East Asian Line. Southern land endpoint is the New South Wales shipyard north of the separate Sydney city boundary. UK rectangular flag is a separate bonus reference. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-026 — Add source-traced Lend Lease to Britain Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_usa_new_york`, `land_brazil_rio_de_janeiro`, `sea_a25`, `sea_a30`, `sea_a37`, `sea_a41`, `sea_a42`, `sea_a45`, `sea_a47`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "Lend Lease to Britain Line",
  "observed_loss_cap": 3,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "usa",
  "complete_path": [
    "sea_a25",
    "sea_a30",
    "sea_a37",
    "sea_a41",
    "sea_a42",
    "sea_a45",
    "sea_a47"
  ],
  "endpoints": [
    {
      "kind": "land",
      "node_id": "land_usa_new_york"
    },
    {
      "kind": "land",
      "node_id": "land_brazil_rio_de_janeiro"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_north_atlantic_start.jpg
- evidence/root_convoy_caribbean.jpg
- evidence/root_convoy_brazil.jpg

**Scope / dependency:** New York to Rio de Janeiro. The line begins in A25 and passes west of A38 in A37/A41; it does not traverse A38 or A49. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-027 — Add source-traced North Sea Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_ger_western_germany`, `land_nor_northern_norway`, `sea_a11`, `sea_a10`, `sea_a7`, `sea_a5`, `sea_a8`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "North Sea Line",
  "observed_loss_cap": 2,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "germany",
  "complete_path": [
    "sea_a11",
    "sea_a10",
    "sea_a7",
    "sea_a5",
    "sea_a8"
  ],
  "endpoints": [
    {
      "kind": "land",
      "node_id": "land_ger_western_germany"
    },
    {
      "kind": "land",
      "node_id": "land_nor_northern_norway"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_north_sea_full.jpg
- evidence/root_convoy_arctic.jpg
- evidence/ea_naval_germany_denmark_20261006.png

**Scope / dependency:** Western Germany A11 major shipyard to Narvik in Northern Norway. The northern stretch is A5/A8, not A6 or A9. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-028 — Add source-traced Baltic Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_ger_eastern_germany`, `land_swe_norrland`, `sea_a12`, `sea_a13`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "Baltic Line",
  "observed_loss_cap": 3,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "germany",
  "complete_path": [
    "sea_a12",
    "sea_a13"
  ],
  "endpoints": [
    {
      "kind": "land",
      "node_id": "land_ger_eastern_germany"
    },
    {
      "kind": "land",
      "node_id": "land_swe_norrland"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_baltic_full.jpg

**Scope / dependency:** The dashed line stays west of the curved A14 border throughout; A14 is not part of the Baltic Line. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-029 — Add source-traced Liguria-Tripoli Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_ita_lazio`, `land_tripoli`, `sea_m3`, `sea_m2`, `sea_m4`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "Liguria-Tripoli Line",
  "observed_loss_cap": 1,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "italy",
  "complete_path": [
    "sea_m3",
    "sea_m2",
    "sea_m4"
  ],
  "endpoints": [
    {
      "kind": "land",
      "node_id": "land_ita_lazio"
    },
    {
      "kind": "land",
      "node_id": "land_tripoli"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_italy_detail.jpg
- evidence/root_convoy_med.jpg

**Scope / dependency:** Despite its printed Liguria-Tripoli label, the northern facility lies on Lazio. The curve west of Sicily briefly crosses M2 between M3 and M4. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-030 — Add source-traced Soviet Arctic Line

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_a20`, `land_usr_kola`, `sea_a17`, `sea_a4`, `sea_a6`, `sea_a5`, `sea_a8`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "Soviet Arctic Line",
  "observed_loss_cap": null,
  "printed_loss_cap_status": "no_numeric_cap_printed",
  "beneficiary_nation_id": "ussr",
  "complete_path": [
    "sea_a20",
    "sea_a17",
    "sea_a4",
    "sea_a6",
    "sea_a5",
    "sea_a8"
  ],
  "endpoints": [
    {
      "kind": "sea",
      "node_id": "sea_a20"
    },
    {
      "kind": "land",
      "node_id": "land_usr_kola"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_soviet_start.jpg
- evidence/root_convoy_arctic.jpg
- evidence/root_convoy_north_sea_full.jpg
- evidence/root_convoy_kola_end.jpg

**Scope / dependency:** The sea arc is in A20; the curve west of Shetland passes through A6 before A5. Kola endpoint is its A8 minor shipyard. No numeric raid cap is printed. USSR NRS p2 separately gives a conditional +2 wartime bonus; do not use that as a raid cap. Geographic record is a proposal; validate against the corrected world roster and canonical nation IDs before implementation.

## WG-032 — Missing printed Atlantic/Arctic sea zone A5

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_a5`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Sea Zone A5",
  "type": "sea",
  "terrain": "sea",
  "ipp_value": null
}
```

**Evidence:**

- Original gw36map.png rectangle (1700, 0, 4600, 950); evidence/root_convoy_arctic.jpg

**Scope / dependency:** Printed zone identity is confirmed. Complete border ring still needs full native trace; EA/AP regional coast references require this missing node. Do not fill unspecified neighbors from a rectangular grid assumption.

## WG-033 — Missing printed Atlantic/Arctic sea zone A8

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_a8`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Sea Zone A8",
  "type": "sea",
  "terrain": "sea",
  "ipp_value": null
}
```

**Evidence:**

- Original gw36map.png rectangle (1700, 0, 4600, 950); evidence/root_convoy_arctic.jpg

**Scope / dependency:** Printed zone identity is confirmed. Complete border ring still needs full native trace; EA/AP regional coast references require this missing node. Do not fill unspecified neighbors from a rectangular grid assumption.

## WG-034 — Missing printed Atlantic/Arctic sea zone A9

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_a9`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Sea Zone A9",
  "type": "sea",
  "terrain": "sea",
  "ipp_value": null
}
```

**Evidence:**

- Original gw36map.png rectangle (1700, 0, 4600, 950); evidence/root_convoy_arctic.jpg
- A9 also expressly referenced by rulebook sections 1.8 p15 and 1.13 p17

**Scope / dependency:** Printed zone identity is confirmed. Complete border ring still needs full native trace; EA/AP regional coast references require this missing node. Do not fill unspecified neighbors from a rectangular grid assumption.

## WG-035 — Add Caribbean Line to the world convoy layer

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_for_printed_geography · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_usa_texas`, `sea_a37`, `sea_a36`

**Current:**

No production world convoy layer

**Proposed:**

```json
{
  "printed_name": "Caribbean Line",
  "observed_loss_cap": 2,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "usa",
  "complete_path": [
    "sea_a36",
    "sea_a37"
  ],
  "endpoints": [
    {
      "kind": "land",
      "node_id": "land_usa_texas"
    },
    {
      "kind": "sea",
      "node_id": "sea_a37"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_caribbean.jpg

**Scope / dependency:** Texas facility land endpoint; terminal arc in A37 southeast of Bahamas. A37 is absent from current JSON; this is not executable current-map data. See convoy_review.md; this is a proposal, not executable map data.

## WG-036 — Add Nagasaki Line to the world convoy layer

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** inherited_complete_source_audit · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_manchuria_rehe`, `land_jap_kyushu`, `sea_p14`, `sea_p15`

**Current:**

No production world convoy layer

**Proposed:**

```json
{
  "printed_name": "Nagasaki Line",
  "observed_loss_cap": 5,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "japan",
  "complete_path": [
    "sea_p14",
    "sea_p15"
  ],
  "endpoints": [
    {
      "node_id": "land_manchuria_rehe",
      "kind": "land"
    },
    {
      "node_id": "land_jap_kyushu",
      "kind": "land"
    }
  ]
}
```

**Evidence:**

- game_content/scenarios/japan_china_1936/m0/convoy_audit.json

**Scope / dependency:** Prior fully traced source record; still absent from production world map. See convoy_review.md; this is a proposal, not executable map data.

## WG-037 — Add Tokyo Line to the world convoy layer

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** inherited_complete_source_audit · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_jap_tokyo`, `sea_p50`, `sea_p16`, `sea_p34`, `sea_p33`, `sea_p32`, `sea_p41`

**Current:**

No production world convoy layer

**Proposed:**

```json
{
  "printed_name": "Tokyo Line",
  "observed_loss_cap": 5,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "japan",
  "complete_path": [
    "sea_p16",
    "sea_p34",
    "sea_p33",
    "sea_p32",
    "sea_p41",
    "sea_p50"
  ],
  "endpoints": [
    {
      "node_id": "land_jap_tokyo",
      "kind": "land"
    },
    {
      "node_id": "sea_p50",
      "marker": "terminal_arc_near_singapore",
      "kind": "sea"
    }
  ]
}
```

**Evidence:**

- game_content/scenarios/japan_china_1936/m0/convoy_audit.json

**Scope / dependency:** Prior fully traced source record; still absent from production world map. See convoy_review.md; this is a proposal, not executable map data.

## WG-040 — Include Northern Ireland in Great Britain Home Country

**Field:** `nations.Great Britain.home_country_land_zone_ids` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_gbr_northern_ireland`

**Current:**

```json
{
  "rulebook_definition": "Explicit nation list from Home Country Land Zones table.",
  "home_country_land_zone_ids": [
    "land_gbr_london",
    "land_gbr_northern_england",
    "land_gbr_scotland",
    "land_gbr_southern_england"
  ],
  "home_country_land_zone_names": [
    "London",
    "Northern England",
    "Scotland",
    "Southern England"
  ],
  "missing_named_zones_in_map": [
    "Northern Ireland"
  ]
}
```

**Proposed:**

```json
{
  "add_land_zone_ids": [
    "land_gbr_northern_ireland"
  ],
  "clear_missing_named_zones_after_resolution": [
    "Northern Ireland"
  ]
}
```

**Evidence:**

- game_content/rules/Global War 1936 v4.3 Rulebook.pdf p6
- game_content/maps/gw36_nation_home_country.json
- tools/build_nation_home_country_json.py
- game_content/maps/gw36map.png

**Scope / dependency:** Rulebook p6 explicitly lists Northern Ireland. The current sidecar reports it missing because the world node is absent; add the physical tile first and regenerate.

## WG-041 — Include Sydney in ANZAC Home Country

**Field:** `nations.ANZAC.home_country_land_zone_ids` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_aus_sydney`

**Current:**

Sydney is absent

**Proposed:**

```json
{
  "add_land_zone_ids": [
    "land_aus_sydney"
  ]
}
```

**Evidence:**

- game_content/rules/Global War 1936 v4.3 Rulebook.pdf p6
- game_content/maps/gw36_nation_home_country.json
- tools/build_nation_home_country_json.py
- game_content/maps/gw36map.png

**Scope / dependency:** Rulebook p6 includes all Australian/New Zealand land zones. Sydney is a distinct printed city zone (AP-036); it must remain separate from New South Wales.

## AM-041 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_england`, `land_usa_new_york`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [250, 1370, 1000, 1900], "crop": "docs/map_audits/full_world/evidence/americas_usa_northeast.png"}

**Scope / dependency:** Rail crosses the northwest city boundary.

## AM-042 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_england`, `land_usa_the_northeast`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [250, 1370, 1000, 1900], "crop": "docs/map_audits/full_world/evidence/americas_usa_northeast.png"}

**Scope / dependency:** Finite border west of New England; printed rail joins the two roundel regions.

## AM-043 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_great_lakes`, `land_usa_the_northeast`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [250, 1370, 1000, 1900], "crop": "docs/map_audits/full_world/evidence/americas_usa_northeast.png"}

**Scope / dependency:** Land/rail corridor south of the lakes.

## AM-044 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_midwest`, `land_usa_chicago`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Chicago city circle shares its northwest perimeter with Midwest and a rail crosses it.

## AM-045 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_orleans`, `land_usa_appalachia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Appalachia south tip reaches New Orleans northern boundary, with a rail crossing.

## AM-046 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** medium · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_alaska`, `land_usa_southeast_alaska`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": false,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [8500, 0, 9900, 1460], "crop": "docs/map_audits/full_world/evidence/americas_alaska.png"}

**Scope / dependency:** Finite US neck where the horizontal Canada boundary reaches the coast.

## AM-047 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_bolivia`, `land_rio_grande`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** Norte Grande borders Bolivia south and printed rail crosses.

## AM-048 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_chile`, `land_rio_grande`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** Norte Grande western mountain boundary with Chile has rail crossings.

## AM-049 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_rio_grande`, `land_patagonia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** Norte Grande–Patagonia border wraps the Buenos Aires circle; west rail crosses.

## AM-050 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_rio_grande`, `land_uruguay`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** Uruguay northwest border with Norte Grande has rail crossing.

## AM-051 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `land_bolivia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": false,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [280, 2900, 930, 3550], "crop": "docs/map_audits/full_world/evidence/americas_andes_amazon_detail.png"}

**Scope / dependency:** Long southeast Amazonas border touches Bolivia outside the hatched Amazon region.

## AM-052 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `land_brazil_pampas`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": false,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Amazonas south border joins Pampas; no printed railroad.

## AM-053 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_caatinga`, `land_brazil_pampas`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": false,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Caatinga wraps above Rio de Janeiro and touches Pampas west of the city circle.

## AM-054 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `land_guyana`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": false,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** British Guiana has a clear southern border with Amazonas.

## AM-055 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `land_suriname`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": false,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Suriname southern border abuts Amazonas.

## AM-056 — Add missing land border

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `land_french_guiana`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": false,
  "directional_terrain_and_river": "must be traced separately"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** French Guiana southern border abuts Amazonas.

## AM-085 — Missing printed land zone: Greenland

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_greenland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Greenland",
  "type": "land",
  "original_owner": "Denmark",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a2",
    "sea_a3"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 0, 2250, 1450], "crop": "docs/map_audits/full_world/evidence/americas_arctic.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-086 — Missing printed land zone: Iceland

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_iceland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Iceland",
  "type": "land",
  "original_owner": "Denmark",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a3",
    "sea_a4"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [
    {
      "id": "facility_iceland_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a3"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_iceland_20261006.png",
          "rectangle": [
            1780,
            285,
            2170,
            530
          ]
        }
      ],
      "notes": "Plain blue anchor on white square on Iceland southwest coast, northwest of the A3/A4 boundary line. Its square does not bridge the sea boundary; A3 access only."
    }
  ],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-087 — Missing printed land zone: Faroe Islands

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_faroe_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Faroe Islands",
  "type": "land",
  "original_owner": "Denmark",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a4"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-088 — Missing printed land zone: Shetland Islands

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_gbr_shetland_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Shetland Islands",
  "type": "land",
  "original_owner": "United Kingdom",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a6"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border. Regional prefixed land_gbr_shetland_islands is an alias of the root reconciliation canonical land_shetland_islands; create one physical tile only.

## AM-089 — Missing printed land zone: Azores

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_azores`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Azores",
  "type": "land",
  "original_owner": "Portugal",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a39"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-090 — Missing printed land zone: Bahamas

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_bahamas`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Bahamas",
  "type": "land",
  "original_owner": "United Kingdom",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a37"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-091 — Missing printed land zone: Jamaica

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_jamaica`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Jamaica",
  "type": "land",
  "original_owner": "United Kingdom",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a40"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-092 — Missing printed land zone: Haiti

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_haiti`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Haiti",
  "type": "land",
  "original_owner": "Haiti",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a37",
    "sea_a40"
  ],
  "confirmed_land_neighbors": [
    "land_dominican_republic"
  ],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_hispaniola_coasts.png", "rectangle": [640, 2490, 950, 2680]}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-093 — Missing printed land zone: Dominican Republic

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_dominican_republic`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Dominican Republic",
  "type": "land",
  "original_owner": "Dominican Republic",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a37",
    "sea_a41"
  ],
  "confirmed_land_neighbors": [
    "land_haiti"
  ],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_hispaniola_coasts.png", "rectangle": [640, 2490, 950, 2680]}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-094 — Missing printed land zone: Leeward Islands

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_leeward_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Leeward Islands",
  "type": "land",
  "original_owner": "United Kingdom",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a41"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-095 — Missing printed land zone: Windward Islands

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_windward_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Windward Islands",
  "type": "land",
  "original_owner": "United Kingdom",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a41"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-096 — Missing printed land zone: Trinidad

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_trinidad`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Trinidad",
  "type": "land",
  "original_owner": "United Kingdom",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a41"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-097 — Missing printed land zone: Netherlands Antilles

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_netherlands_antilles`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Netherlands Antilles",
  "type": "land",
  "original_owner": "Netherlands",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a41"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-098 — Missing printed land zone: Falkland Islands

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_falkland_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Falkland Islands",
  "type": "land",
  "original_owner": "United Kingdom",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_a49"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-099 — Missing printed land zone: Galapagos

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_galapagos`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Galapagos",
  "type": "land",
  "original_owner": "Ecuador",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_p76"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-100 — Missing printed land zone: Kodiak Island

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_kodiak_island`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Kodiak Island",
  "type": "land",
  "original_owner": "United States",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_p5"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [8500, 0, 9900, 1460], "crop": "docs/map_audits/full_world/evidence/americas_alaska.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-101 — Missing printed land zone: St. Lawrence Island

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_st_lawrence_island`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "St. Lawrence Island",
  "type": "land",
  "original_owner": "United States",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_p1"
  ],
  "confirmed_land_neighbors": [],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [8500, 0, 9900, 1460], "crop": "docs/map_audits/full_world/evidence/americas_alaska.png"}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-102 — Missing printed land zone: Aleutian Islands

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_aleutian_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Aleutian Islands",
  "type": "land",
  "original_owner": "United States",
  "ipp_value": 0,
  "remaining_fields": "National capital/victory flags need national-sheet policy; terrain in intrinsic ledger / Europe-Africa glossary; facilities only where separately observed.",
  "confirmed_coastal_seas": [
    "sea_p5"
  ],
  "confirmed_land_neighbors": [
    "land_usa_alaska"
  ],
  "uncertain_neighbors": [],
  "naval_facilities": [],
  "naval_review": "Rechecked from original board 2026-10-06; explicit empty list means no printed naval facility."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [8500, 0, 9900, 1460], "crop": "docs/map_audits/full_world/evidence/americas_alaska.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_alaska_coasts.png", "rectangle": [8680, 575, 9250, 930]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/ap_north_pacific_grid.png", "rectangle": [8080, 850, 9800, 2130]}

**Scope / dependency:** Printed territory/name/owner/IPP inspected. Second-pass physical trace completes the listed sea and land neighbor set; island group outlines do not grant direct land links to nearby islands. No rail is drawn across the Haiti/Dominican or Alaska/Aleutian border.

## AM-134 — Missing Great Lakes shoreline

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_midwest`, `sea_a24`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_to_sea_border_terrain": "coast",
  "sea_to_land_border_terrain": "trace landing approach",
  "naval_facilities": [
    "minor_port"
  ],
  "naval_facility_ids": [
    "facility_usa_midwest_minor_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_midwest_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a24"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png",
          "rectangle": [
            0,
            1200,
            1300,
            2420
          ]
        }
      ],
      "notes": "Plain blue anchor on white square on the western Great Lakes water shore; lies in Midwest, west of Great Lakes territory."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [250, 1370, 1000, 1900], "crop": "docs/map_audits/full_world/evidence/americas_usa_northeast.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Midwest has a printed white-anchor minor port on its A24 shore. Retain a separate physical facility from the Great Lakes port. Rechecked on 2026-10-06; see naval_reaudit_americas_atlantic.json.

## AM-135 — Missing Great Lakes shoreline

**Field:** `neighbors reciprocal entries` · **Confidence:** medium · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_the_northeast`, `sea_a24`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_to_sea_border_terrain": "coast",
  "sea_to_land_border_terrain": "trace landing approach",
  "naval_facilities": [],
  "naval_facility_ids": [],
  "physical_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [250, 1370, 1000, 1900], "crop": "docs/map_audits/full_world/evidence/americas_usa_northeast.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_interior_detail.png", "rectangle": [180, 1450, 850, 2070]}

**Scope / dependency:** Enlarged border trace places the white-anchor port in Great Lakes, west of The Northeast boundary. Add The Northeast A24 shore without a port. Retain one physical Great Lakes port; its old ID may be reconciled with the new source-instance ID, never duplicated. Rechecked 2026-10-06.

## AM-139 — Printed shore facilities: New England–sea_a25

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_england`, `sea_a25`

**Current:**

```json
[]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_shipyard"
  ],
  "naval_facility_ids": [
    "facility_usa_new_england_minor_shipyard_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_new_england_minor_shipyard_map_1",
      "type": "minor_shipyard",
      "sea_accesses": [
        "sea_a25"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_canada_east_20261006.png",
          "rectangle": [
            580,
            1180,
            1250,
            1640
          ]
        }
      ],
      "notes": "Blue crane on white square on New England coast north of the circular New York boundary."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_canada_east_20261006.png", "rectangle": [580, 1180, 1250, 1640]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Blue crane on white square on New England coast north of the circular New York boundary.

## AM-145 — Printed shore facilities: Texas–sea_a36

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_texas`, `sea_a36`

**Current:**

```json
[]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_shipyard",
    "major_port",
    "seaplane_base"
  ],
  "naval_facility_ids": [
    "facility_usa_texas_minor_shipyard_map_1",
    "facility_usa_texas_major_port_map_2",
    "facility_usa_texas_seaplane_base_map_3"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_texas_minor_shipyard_map_1",
      "type": "minor_shipyard",
      "sea_accesses": [
        "sea_a36"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_us_gulf_20261006.png",
          "rectangle": [
            20,
            2080,
            620,
            2460
          ]
        }
      ],
      "notes": "Blue crane on white square on northeastern Texas Gulf coast, west of the New Orleans city boundary."
    },
    {
      "id": "facility_usa_texas_major_port_map_2",
      "type": "major_port",
      "sea_accesses": [
        "sea_a36"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_us_gulf_20261006.png",
          "rectangle": [
            20,
            2080,
            620,
            2460
          ]
        }
      ],
      "notes": "Plain white anchor on blue square on the western Gulf coast, south of the Texas shipyard."
    },
    {
      "id": "facility_usa_texas_seaplane_base_map_3",
      "type": "seaplane_base",
      "sea_accesses": [
        "sea_a36"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_us_gulf_20261006.png",
          "rectangle": [
            20,
            2080,
            620,
            2460
          ]
        }
      ],
      "notes": "White seaplane on green square farther south on Texas coast; separate from the major port."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_us_gulf_20261006.png", "rectangle": [20, 2080, 620, 2460]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Blue crane on white square on northeastern Texas Gulf coast, west of the New Orleans city boundary. Plain white anchor on blue square on the western Gulf coast, south of the Texas shipyard. White seaplane on green square farther south on Texas coast; separate from the major port.

## AM-146 — Printed shore facilities: Eastern Mexico–sea_a36

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_mex_eastern_mexico`, `sea_a36`

**Current:**

```json
[]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_port"
  ],
  "naval_facility_ids": [
    "facility_mex_eastern_mexico_minor_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_mex_eastern_mexico_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a36"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_mexico_panama_20261006.png",
          "rectangle": [
            0,
            2370,
            580,
            2940
          ]
        }
      ],
      "notes": "Plain blue anchor on white square on northern Yucatan shore west of the A36/A40 line. No symbol on the Caribbean or Pacific shore."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_mexico_panama_20261006.png", "rectangle": [0, 2370, 580, 2940]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain blue anchor on white square on northern Yucatan shore west of the A36/A40 line. No symbol on the Caribbean or Pacific shore.

## AM-149 — Printed shore facilities: Ecuador–sea_p76

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_ecuador`, `sea_p76`

**Current:**

```json
[]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_port"
  ],
  "naval_facility_ids": [
    "facility_ecuador_minor_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_ecuador_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_p76"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_south_north.png",
          "rectangle": [
            0,
            2750,
            1500,
            3880
          ]
        }
      ],
      "notes": "Plain blue anchor on white square on northern Ecuador coast, south of Colombia border and north of the P76/P77 division."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_north.png", "rectangle": [0, 2750, 1500, 3880]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain blue anchor on white square on northern Ecuador coast, south of Colombia border and north of the P76/P77 division.

## AM-150 — Printed shore facilities: Peru–sea_p77

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_peru`, `sea_p77`

**Current:**

```json
[]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_shipyard",
    "major_port"
  ],
  "naval_facility_ids": [
    "facility_peru_minor_shipyard_map_1",
    "facility_peru_major_port_map_2"
  ],
  "physical_facilities": [
    {
      "id": "facility_peru_minor_shipyard_map_1",
      "type": "minor_shipyard",
      "sea_accesses": [
        "sea_p77"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_south_north.png",
          "rectangle": [
            0,
            2750,
            1500,
            3880
          ]
        }
      ],
      "notes": "Blue crane on white square on northern/central Peru coast, far north of its distinct major port."
    },
    {
      "id": "facility_peru_major_port_map_2",
      "type": "major_port",
      "sea_accesses": [
        "sea_p77"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_south_north.png",
          "rectangle": [
            0,
            2750,
            1500,
            3880
          ]
        }
      ],
      "notes": "Plain white anchor on blue square farther south on Peru coast; the railway starts inland from it."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_north.png", "rectangle": [0, 2750, 1500, 3880]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Blue crane on white square on northern/central Peru coast, far north of its distinct major port. Plain white anchor on blue square farther south on Peru coast; the railway starts inland from it.

## AM-178 — Missing printed Atlantic sea zone A3

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a3`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a3",
  "name": "A3",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-179 — Missing printed Atlantic sea zone A4

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a4`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a4",
  "name": "A4",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-180 — Missing printed Atlantic sea zone A16

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a16`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a16",
  "name": "A16",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-181 — Missing printed Atlantic sea zone A17

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a17`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a17",
  "name": "A17",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-182 — Missing printed Atlantic sea zone A27

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a27`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a27",
  "name": "A27",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-183 — Missing printed Atlantic sea zone A30

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a30`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a30",
  "name": "A30",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-184 — Missing printed Atlantic sea zone A32

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a32`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a32",
  "name": "A32",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-185 — Missing printed Atlantic sea zone A34

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a34`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a34",
  "name": "A34",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-186 — Missing printed Atlantic sea zone A37

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a37`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a37",
  "name": "A37",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-187 — Missing printed Atlantic sea zone A41

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a41`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a41",
  "name": "A41",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-188 — Missing printed Atlantic sea zone A42

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a42`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a42",
  "name": "A42",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-189 — Missing printed Atlantic sea zone A43

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a43`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a43",
  "name": "A43",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-190 — Missing printed Atlantic sea zone A45

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a45`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a45",
  "name": "A45",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-191 — Missing printed Atlantic sea zone A46

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a46`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a46",
  "name": "A46",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-192 — Missing printed Atlantic sea zone A47

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a47`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a47",
  "name": "A47",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-193 — Missing printed Atlantic sea zone A48

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a48`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a48",
  "name": "A48",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-194 — Missing printed Atlantic sea zone A49

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a49`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a49",
  "name": "A49",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-195 — Missing printed Atlantic sea zone A50

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a50`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a50",
  "name": "A50",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-196 — Missing printed Atlantic sea zone A51

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a51`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a51",
  "name": "A51",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-197 — Missing printed Atlantic sea zone A52

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a52`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a52",
  "name": "A52",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-198 — Missing printed Atlantic sea zone A53

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a53`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a53",
  "name": "A53",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-199 — Missing printed Atlantic sea zone A54

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a54`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_a54",
  "name": "A54",
  "type": "sea",
  "terrain": "sea",
  "neighbors": "see grid edge proposal and region-specific coast review"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-200 — Missing South American Pacific sea zone P76

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p76`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_p76",
  "name": "P76",
  "type": "sea",
  "terrain": "sea"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-201 — Missing South American Pacific sea zone P77

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p77`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_p77",
  "name": "P77",
  "type": "sea",
  "terrain": "sea"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-202 — Missing South American Pacific sea zone P78

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p78`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "sea_p78",
  "name": "P78",
  "type": "sea",
  "terrain": "sea"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}

**Scope / dependency:** Printed sea cell is absent from the current graph. Adjacency proposals are in AM-203/AM-227 and regional sea matrices; do not fill arbitrary chain defaults.

## AM-203 — Rebuild missing Atlantic sea-grid links

**Field:** `reciprocal sea-to-sea adjacency` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a15`, `sea_a16`, `sea_a17`, `sea_a18`, `sea_a19`, `sea_a2`, `sea_a20`, `sea_a21`, `sea_a22`, `sea_a25`, `sea_a26`, `sea_a27`, `sea_a28`, `sea_a29`, `sea_a3`, `sea_a30`, `sea_a31`, `sea_a32`, `sea_a33`, `sea_a34`, `sea_a35`, `sea_a36`, `sea_a37`, `sea_a38`, `sea_a39`, `sea_a4`, `sea_a40`, `sea_a41`, `sea_a42`, `sea_a43`, `sea_a44`, `sea_a45`, `sea_a46`, `sea_a47`, `sea_a48`, `sea_a49`, `sea_a50`, `sea_a51`, `sea_a52`, `sea_a53`, `sea_a54`, `sea_a6`

**Current:**

```json
{
  "missing_pairs": 63
}
```

**Proposed:**

```json
{
  "pairs": [
    [
      "sea_a2",
      "sea_a3"
    ],
    [
      "sea_a3",
      "sea_a16"
    ],
    [
      "sea_a4",
      "sea_a17"
    ],
    [
      "sea_a15",
      "sea_a16"
    ],
    [
      "sea_a16",
      "sea_a17"
    ],
    [
      "sea_a17",
      "sea_a20"
    ],
    [
      "sea_a18",
      "sea_a26"
    ],
    [
      "sea_a19",
      "sea_a27"
    ],
    [
      "sea_a20",
      "sea_a27"
    ],
    [
      "sea_a20",
      "sea_a28"
    ],
    [
      "sea_a21",
      "sea_a28"
    ],
    [
      "sea_a22",
      "sea_a29"
    ],
    [
      "sea_a26",
      "sea_a27"
    ],
    [
      "sea_a25",
      "sea_a30"
    ],
    [
      "sea_a26",
      "sea_a33"
    ],
    [
      "sea_a27",
      "sea_a33"
    ],
    [
      "sea_a27",
      "sea_a35"
    ],
    [
      "sea_a27",
      "sea_a28"
    ],
    [
      "sea_a28",
      "sea_a35"
    ],
    [
      "sea_a30",
      "sea_a31"
    ],
    [
      "sea_a30",
      "sea_a32"
    ],
    [
      "sea_a30",
      "sea_a37"
    ],
    [
      "sea_a31",
      "sea_a32"
    ],
    [
      "sea_a32",
      "sea_a34"
    ],
    [
      "sea_a33",
      "sea_a34"
    ],
    [
      "sea_a34",
      "sea_a35"
    ],
    [
      "sea_a34",
      "sea_a39"
    ],
    [
      "sea_a32",
      "sea_a37"
    ],
    [
      "sea_a32",
      "sea_a38"
    ],
    [
      "sea_a35",
      "sea_a39"
    ],
    [
      "sea_a35",
      "sea_a43"
    ],
    [
      "sea_a35",
      "sea_a44"
    ],
    [
      "sea_a36",
      "sea_a37"
    ],
    [
      "sea_a36",
      "sea_a40"
    ],
    [
      "sea_a37",
      "sea_a38"
    ],
    [
      "sea_a37",
      "sea_a40"
    ],
    [
      "sea_a37",
      "sea_a41"
    ],
    [
      "sea_a39",
      "sea_a42"
    ],
    [
      "sea_a39",
      "sea_a43"
    ],
    [
      "sea_a40",
      "sea_a41"
    ],
    [
      "sea_a41",
      "sea_a42"
    ],
    [
      "sea_a42",
      "sea_a43"
    ],
    [
      "sea_a42",
      "sea_a45"
    ],
    [
      "sea_a43",
      "sea_a44"
    ],
    [
      "sea_a43",
      "sea_a46"
    ],
    [
      "sea_a44",
      "sea_a46"
    ],
    [
      "sea_a45",
      "sea_a46"
    ],
    [
      "sea_a45",
      "sea_a47"
    ],
    [
      "sea_a46",
      "sea_a47"
    ],
    [
      "sea_a46",
      "sea_a48"
    ],
    [
      "sea_a47",
      "sea_a48"
    ],
    [
      "sea_a47",
      "sea_a49"
    ],
    [
      "sea_a48",
      "sea_a50"
    ],
    [
      "sea_a49",
      "sea_a50"
    ],
    [
      "sea_a49",
      "sea_a52"
    ],
    [
      "sea_a50",
      "sea_a51"
    ],
    [
      "sea_a50",
      "sea_a52"
    ],
    [
      "sea_a51",
      "sea_a53"
    ],
    [
      "sea_a52",
      "sea_a53"
    ],
    [
      "sea_a52",
      "sea_a54"
    ],
    [
      "sea_a53",
      "sea_a54"
    ],
    [
      "sea_a3",
      "sea_a4"
    ],
    [
      "sea_a4",
      "sea_a6"
    ]
  ],
  "edge_fields": {
    "border_terrain": "sea",
    "passable": true
  }
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 0, 2250, 1450], "crop": "docs/map_audits/full_world/evidence/americas_arctic.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [250, 3780, 2300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_bottom.png"}

**Scope / dependency:** Long finite boundaries traced across the saved grid crops. Add reciprocal sea-to-sea entries with the listed fields; short offset junctions are separated into an uncertain finding. Eastern A5–A14 grid/coasts belong to Europe. Dashed white convoy lines are not sea boundaries.

## AM-210 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p76`, `sea_p31`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-211 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p76`, `sea_p40`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-212 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p76`, `sea_p49`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-213 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p77`, `sea_p58`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-214 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p77`, `sea_p68`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-215 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p78`, `sea_p68`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-216 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p78`, `sea_p75`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-217 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p76`, `sea_p77`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-218 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p77`, `sea_p78`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-219 — Pacific map-edge / South American sea connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_p78`, `sea_a49`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "sea",
  "passable": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}

**Scope / dependency:** Red printed seam arrows identify the opposite-edge neighbors; P76/P77 and P77/P78 share horizontal borders, P78/A49 share the Drake Passage vertical sea boundary.

## AM-227 — Add 16 resolved short Atlantic grid offset contacts

**Field:** `sea-to-sea adjacency` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a15`, `sea_a16`, `sea_a17`, `sea_a19`, `sea_a20`, `sea_a25`, `sea_a26`, `sea_a3`, `sea_a31`, `sea_a32`, `sea_a33`, `sea_a38`, `sea_a39`, `sea_a41`, `sea_a42`, `sea_a43`, `sea_a45`, `sea_a47`, `sea_a48`, `sea_a50`, `sea_a51`, `sea_a53`

**Current:**

These candidate pairs are absent

**Proposed:**

```json
[
  [
    "sea_a3",
    "sea_a15"
  ],
  [
    "sea_a3",
    "sea_a17"
  ],
  [
    "sea_a15",
    "sea_a19"
  ],
  [
    "sea_a16",
    "sea_a19"
  ],
  [
    "sea_a19",
    "sea_a26"
  ],
  [
    "sea_a25",
    "sea_a31"
  ],
  [
    "sea_a32",
    "sea_a33"
  ],
  [
    "sea_a32",
    "sea_a39"
  ],
  [
    "sea_a38",
    "sea_a41"
  ],
  [
    "sea_a38",
    "sea_a42"
  ],
  [
    "sea_a41",
    "sea_a45"
  ],
  [
    "sea_a43",
    "sea_a45"
  ],
  [
    "sea_a47",
    "sea_a50"
  ],
  [
    "sea_a48",
    "sea_a51"
  ],
  [
    "sea_a50",
    "sea_a53"
  ],
  [
    "sea_a16",
    "sea_a20"
  ]
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 0, 2250, 1450], "crop": "docs/map_audits/full_world/evidence/americas_arctic.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 3250, 3300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_south.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [250, 3780, 2300, 4888], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_bottom.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_grid_north_detail.png", "rectangle": [1080, 790, 1940, 1690]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_grid_mid_detail.png", "rectangle": [790, 1770, 1630, 2660]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_grid_south_detail.png", "rectangle": [1000, 3000, 2290, 4490]}

**Scope / dependency:** All 16 former candidates have finite shared boundary segments on native enlarged crops; short staggered contacts are real, not corner-only. Add reciprocal sea edges with border_terrain sea/passable true.

## AM-231 — Intrinsic terrain for missing American territories

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_aleutian_islands`, `land_usa_kodiak_island`, `land_usa_attu_and_kiska`, `land_usa_st_lawrence_island`, `land_bahamas`, `land_jamaica`, `land_leeward_islands`, `land_windward_islands`, `land_trinidad`, `land_falkland_islands`, `land_galapagos`, `land_haiti`, `land_dominican_republic`, `land_netherlands_antilles`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_usa_aleutian_islands": "mountain",
  "land_usa_kodiak_island": "mountain",
  "land_usa_attu_and_kiska": "mountain",
  "land_usa_st_lawrence_island": "normal",
  "land_bahamas": "normal",
  "land_jamaica": "normal",
  "land_leeward_islands": "normal",
  "land_windward_islands": "normal",
  "land_trinidad": "normal",
  "land_falkland_islands": "normal",
  "land_galapagos": "normal",
  "land_haiti": "mountain",
  "land_dominican_republic": "mountain",
  "land_netherlands_antilles": "normal"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Attach these exact source terrain values when creating the already-proposed missing nodes. Attu/Kiska belongs to the Asia/Pacific node-addition proposal; do not add a duplicate.

## AM-234 — Restore glossary-supported American approaches missing from graph

**Field:** `directional approaches` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_bolivia`, `land_brazil_amazon_jungle`, `land_brazil_pampas`, `land_can_alberta_saskatchewan`, `land_can_yukon_territory`, `land_chile`, `land_colombia`, `land_ecuador`, `land_french_guiana`, `land_guyana`, `land_mex_eastern_mexico`, `land_panama`, `land_rio_grande`, `land_suriname`, `land_usa_alaska`, `land_usa_appalachia`, `land_usa_chicago`, `land_usa_great_lakes`, `land_usa_midwest`, `land_usa_new_england`, `land_usa_pacific_northwest`, `land_usa_southeast_alaska`, `land_usa_southeastern_united_states`, `land_usa_the_northeast`, `land_usa_upper_midwest`, `land_usa_washington_dc`, `sea_a24`, `sea_a25`, `sea_a40`, `sea_a47`, `sea_p1`, `sea_p76`, `sea_p77`

**Current:**

```json
null
```

**Proposed:**

```json
[
  {
    "source": "land_usa_great_lakes",
    "destination": "land_usa_washington_dc",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_new_england",
    "destination": "land_usa_the_northeast",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_great_lakes",
    "destination": "land_usa_the_northeast",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "sea_a25",
    "destination": "land_usa_the_northeast",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_the_northeast",
    "destination": "land_usa_great_lakes",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "land_usa_washington_dc",
    "destination": "land_usa_great_lakes",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "land_usa_appalachia",
    "destination": "land_usa_great_lakes",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "land_usa_great_lakes",
    "destination": "land_usa_appalachia",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_appalachia",
    "destination": "land_usa_southeastern_united_states",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "land_usa_chicago",
    "destination": "land_usa_midwest",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "sea_a24",
    "destination": "land_usa_midwest",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "sea_p1",
    "destination": "land_usa_alaska",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "sea_p1",
    "destination": "land_usa_alaska",
    "field": "border_terrain",
    "proposed": [
      "mountain",
      "tundra"
    ]
  },
  {
    "source": "sea_a40",
    "destination": "land_panama",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_southeast_alaska",
    "destination": "land_can_yukon_territory",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_pacific_northwest",
    "destination": "land_can_alberta_saskatchewan",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "land_usa_upper_midwest",
    "destination": "land_can_alberta_saskatchewan",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "sea_a40",
    "destination": "land_mex_eastern_mexico",
    "field": "border_terrain",
    "proposed": "jungle"
  },
  {
    "source": "sea_a40",
    "destination": "land_colombia",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "sea_p76",
    "destination": "land_colombia",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "sea_p76",
    "destination": "land_ecuador",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "sea_p77",
    "destination": "land_ecuador",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "land_bolivia",
    "destination": "land_brazil_amazon_jungle",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_brazil_pampas",
    "destination": "land_brazil_amazon_jungle",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_guyana",
    "destination": "land_brazil_amazon_jungle",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_suriname",
    "destination": "land_brazil_amazon_jungle",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_french_guiana",
    "destination": "land_brazil_amazon_jungle",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "sea_a47",
    "destination": "land_brazil_pampas",
    "field": "border_terrain",
    "proposed": [
      "mountain",
      "jungle"
    ]
  },
  {
    "source": "land_rio_grande",
    "destination": "land_bolivia",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "land_chile",
    "destination": "land_rio_grande",
    "field": "border_terrain",
    "proposed": "mountain"
  }
]
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** The glossary explicitly names these source/destination approaches. Add only after reconciling physical topology and blocked boundaries; other attributes are not implied. New important pairs include Great Lakes–Washington, Great Lakes–Appalachia, Appalachia–Southeastern US, Yukon–Southeast Alaska, Alberta–Pacific Northwest/Upper Midwest, and The Northeast–A25. The board seam ambiguity remains documented; source support is now stronger.

## AM-239 — Add visible Southwest US–Great Plains land and railway connection

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_southwest_united_states`, `land_usa_great_plains`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "adjacency": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_southwest_junction.png", "rectangle": [9550, 1720, 9900, 2140]}

**Scope / dependency:** The eastward dashed SF line crosses the Southwest/Great Plains vertical border below the Western US junction. Terrain directions must use the glossary intrinsic/approach model.

## AM-241 — Restore six visibly shared land borders supported by glossary

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_can_alberta_saskatchewan`, `land_can_yukon_territory`, `land_usa_appalachia`, `land_usa_great_lakes`, `land_usa_pacific_northwest`, `land_usa_southeast_alaska`, `land_usa_southeastern_united_states`, `land_usa_washington_dc`, `land_usa_upper_midwest`

**Current:**

```json
null
```

**Proposed:**

```json
[
  {
    "pair": [
      "land_usa_great_lakes",
      "land_usa_appalachia"
    ],
    "adjacency": true,
    "railway_connection": true
  },
  {
    "pair": [
      "land_usa_great_lakes",
      "land_usa_washington_dc"
    ],
    "adjacency": true,
    "railway_connection": true
  },
  {
    "pair": [
      "land_usa_appalachia",
      "land_usa_southeastern_united_states"
    ],
    "adjacency": true,
    "railway_connection": false
  },
  {
    "pair": [
      "land_can_yukon_territory",
      "land_usa_southeast_alaska"
    ],
    "adjacency": true,
    "railway_connection": false
  },
  {
    "pair": [
      "land_can_alberta_saskatchewan",
      "land_usa_pacific_northwest"
    ],
    "adjacency": true,
    "railway_connection": false
  },
  {
    "pair": [
      "land_can_alberta_saskatchewan",
      "land_usa_upper_midwest"
    ],
    "adjacency": true,
    "railway_connection": false
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_interior_detail.png", "rectangle": [180, 1450, 850, 2070]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_alaska_junction.png", "rectangle": [9100, 620, 9400, 870]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_alaska.png", "rectangle": [8500, 0, 9900, 1460]}

**Scope / dependency:** Second-pass physical trace confirms these approaches. Appalachia touches Southeastern US in the short segment between New Orleans and Carolinas; no track crosses that short segment. Alberta meets the top edge of Pacific Northwest east of British Columbia. Alberta also has a finite horizontal border with Upper Midwest on the same western image edge; no track crosses it. The separate Manitoba–Upper Midwest seam question remains uncertain.

## AM-243 — Add the printed Iceland minor port with A3 access

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_iceland`, `sea_a3`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_port"
  ],
  "physical_facilities": [
    {
      "id": "facility_iceland_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a3"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_iceland_20261006.png",
          "rectangle": [
            1780,
            285,
            2170,
            530
          ]
        }
      ],
      "notes": "Plain blue anchor on white square on Iceland southwest coast, northwest of the A3/A4 boundary line. Its square does not bridge the sea boundary; A3 access only."
    }
  ],
  "naval_facility_ids": [
    "facility_iceland_minor_port_map_1"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_iceland_20261006.png", "rectangle": [1780, 285, 2170, 530]}

**Scope / dependency:** The previous missing-node proposal omitted this visible white-square anchor. It is on the A3 side of the A3/A4 boundary; one physical minor port, not one per Iceland coast.

## EA-060 — Missing printed land zone: Northern Ireland

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_northern_ireland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_gbr_northern_ireland",
  "name": "Northern Ireland",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "United Kingdom",
  "sea_neighbors_proposed": [
    "sea_a17"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-061 — Missing printed land zone: Shetland Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_shetland_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_gbr_shetland_islands",
  "name": "Shetland Islands",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "United Kingdom",
  "sea_neighbors_proposed": [
    "sea_a6"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1400, 0, 2480, 1100], "crop": "evidence/ea_atlantic_islands.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-062 — Missing printed land zone: Iceland

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_iceland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_iceland",
  "name": "Iceland",
  "type": "land",
  "terrain": [
    "mountain",
    "tundra"
  ],
  "ipp_value": 0,
  "original_owner": "Denmark"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1400, 0, 2480, 1100], "crop": "evidence/ea_atlantic_islands.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup. Mixed terrain requires schema support.

## EA-063 — Missing printed land zone: Faroe Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_faroe_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_faroe_islands",
  "name": "Faroe Islands",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Denmark",
  "sea_neighbors_proposed": [
    "sea_a4"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1400, 0, 2480, 1100], "crop": "evidence/ea_atlantic_islands.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-064 — Missing printed land zone: Svalbard

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_svalbard`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_svalbard",
  "name": "Svalbard",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Norway",
  "sea_neighbors_proposed": [
    "sea_a5"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-065 — Missing printed land zone: Northern Norway

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_northern_norway`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_nor_northern_norway",
  "name": "Northern Norway",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 1,
  "original_owner": "Norway",
  "sea_neighbors_proposed": [
    "sea_a5",
    "sea_a8"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-066 — Missing printed land zone: Helsinki

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_helsinki`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_fin_helsinki",
  "name": "Helsinki",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 1,
  "original_owner": "Finland",
  "sea_neighbors_proposed": [
    "sea_a13",
    "sea_a14"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-067 — Missing printed land zone: Sicily

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_sicily`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_ita_sicily",
  "name": "Sicily",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Italy",
  "sea_neighbors_proposed": [
    "sea_m3",
    "sea_m4",
    "sea_m6"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-068 — Missing printed land zone: Malta

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_malta`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_malta",
  "name": "Malta",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "United Kingdom",
  "sea_neighbors_proposed": [
    "sea_m4"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-069 — Missing printed land zone: Rhodes

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rhodes`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_ita_rhodes",
  "name": "Rhodes",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Italy",
  "sea_neighbors_proposed": [
    "sea_m7"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-070 — Missing printed land zone: Peloponnese

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_peloponnese`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_gre_peloponnese",
  "name": "Peloponnese",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Greece",
  "sea_neighbors_proposed": [
    "sea_m6",
    "sea_m7"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-071 — Missing printed land zone: Crete

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_crete`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_gre_crete",
  "name": "Crete",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Greece",
  "sea_neighbors_proposed": [
    "sea_m6",
    "sea_m7",
    "sea_m8"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-072 — Missing printed land zone: Ifni

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ifni`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_ifni",
  "name": "Ifni",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Spain",
  "sea_neighbors_proposed": [
    "sea_a44"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1730, 2890, 3030, 3850], "crop": "evidence/ea_north_africa_west_detail.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-073 — Missing printed land zone: Rio de Oro

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rio_de_oro`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_rio_de_oro",
  "name": "Rio de Oro",
  "type": "land",
  "terrain": "desert",
  "ipp_value": 0,
  "original_owner": "Spain",
  "sea_neighbors_proposed": [
    "sea_a44",
    "sea_a46"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1730, 2890, 3030, 3850], "crop": "evidence/ea_north_africa_west_detail.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-074 — Missing printed land zone: Canary Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_canary_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_canary_islands",
  "name": "Canary Islands",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Spain",
  "sea_neighbors_proposed": [
    "sea_a44"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1730, 2890, 3030, 3850], "crop": "evidence/ea_north_africa_west_detail.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-075 — Missing printed land zone: Cape Verde

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cape_verde`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_cape_verde",
  "name": "Cape Verde",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Portugal",
  "sea_neighbors_proposed": [
    "sea_a46"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-076 — Missing printed land zone: Mauritania

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_mauritania`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_mauritania",
  "name": "Mauritania",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "France",
  "sea_neighbors_proposed": [
    "sea_a46",
    "sea_a48"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-077 — Missing printed land zone: Portuguese Guinea

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_portuguese_guinea`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_portuguese_guinea",
  "name": "Portuguese Guinea",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Portugal",
  "sea_neighbors_proposed": [
    "sea_a48"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-078 — Missing printed land zone: French Guinea

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_guinea`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_french_guinea",
  "name": "French Guinea",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "France",
  "sea_neighbors_proposed": [
    "sea_a48"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-079 — Missing printed land zone: Sierra Leone

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sierra_leone`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_sierra_leone",
  "name": "Sierra Leone",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "United Kingdom",
  "sea_neighbors_proposed": [
    "sea_a48"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-080 — Missing printed land zone: Liberia

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_liberia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_liberia",
  "name": "Liberia",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Liberia",
  "sea_neighbors_proposed": [
    "sea_a48"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-081 — Missing printed land zone: Ivory Coast

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ivory_coast`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_ivory_coast",
  "name": "Ivory Coast",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "France",
  "sea_neighbors_proposed": [
    "sea_a51"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-082 — Missing printed land zone: Gold Coast

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gold_coast`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_gold_coast",
  "name": "Gold Coast",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 1,
  "original_owner": "United Kingdom",
  "sea_neighbors_proposed": [
    "sea_a51"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-083 — Missing printed land zone: São Tomé and Príncipe

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sao_tome_and_principe`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_sao_tome_and_principe",
  "name": "São Tomé and Príncipe",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Portugal",
  "sea_neighbors_proposed": [
    "sea_a51"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-084 — Missing printed land zone: Ascension

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ascension`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_ascension",
  "name": "Ascension",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "United Kingdom",
  "sea_neighbors_proposed": [
    "sea_a50"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-085 — Missing printed land zone: Réunion

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_reunion`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_reunion",
  "name": "Réunion",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "France",
  "sea_neighbors_proposed": [
    "sea_i2"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup.

## EA-086 — Missing printed land zone: Yemen

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_yemen`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_yemen",
  "name": "Yemen",
  "type": "land",
  "terrain": [
    "mountain",
    "desert"
  ],
  "ipp_value": 0,
  "original_owner": "Yemen",
  "sea_neighbors_proposed": [
    "sea_i4",
    "sea_i5"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Minimum identity/terrain/income proposal only. Complete neighbors, directionality, sea accesses and printed facilities before making this a playable node. Spain faction/current-controller allocation belongs in dated setup. Mixed terrain requires schema support.

## EA-087 — Missing printed land zone: Saint Helena

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_saint_helena`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "id": "land_saint_helena",
  "name": "Saint Helena",
  "type": "land",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "United Kingdom",
  "sea_neighbors_proposed": [
    "sea_a53"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Complete Atlantic sea access and facility detail with Atlantic audit.

## EA-089 — A17 → Northern England: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a17`, `land_gbr_northern_england`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "mountain",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-093 — Sicily → Southern Italy: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_sicily`, `land_ita_southern_italy`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "mountain",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-094 — M3 → Southern Italy: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m3`, `land_ita_southern_italy`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "mountain",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-096 — Southern Norway → Norrland: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_southern_norway`, `land_swe_norrland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "mountain",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-098 — A14 → Southern Finland: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a14`, `land_fin_southern_finland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "marsh",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-100 — A8 → Lapland: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a8`, `land_fin_lapland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "tundra",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-102 — Albania → Macedonia: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_albania`, `land_gre_macedonia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "mountain",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-104 — Yemen → Aden: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_yemen`, `land_aden`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": [
    "desert",
    "mountain"
  ],
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-105 — I4 → Aden: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i4`, `land_aden`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": [
    "desert",
    "mountain"
  ],
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-106 — A53 → Southwest Africa: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a53`, `land_southwest_africa`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "desert",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-107 — A54 → Southwest Africa: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a54`, `land_southwest_africa`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "desert",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-109 — French Somaliland → Eritrea: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_somaliland`, `land_eritrea`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": [
    "mountain",
    "desert"
  ],
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-110 — M11 → Donets-Kuban: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m11`, `land_usr_donets_kuban`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "mountain",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-111 — A9 → Northern Russia: missing glossary-described entry

**Field:** `directed_border` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a9`, `land_usr_northern_russia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "border_terrain": "tundra",
  "adjacency_requires_pair": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Glossary expressly lists this incoming boundary. Add reciprocal physical adjacency only after confirming source node and boundary; this record sets only the destination entry terrain, not railways or reverse terrain.

## EA-115 — Western Germany: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_western_germany`, `land_denmark`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_denmark": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-117 — London: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_london`, `sea_a22`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "sea_a22": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-120 — Normandy: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_normandy`, `land_fra_aquitaine`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_fra_aquitaine": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-126 — West Poland: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_west_poland`, `land_pol_lubelskie`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_pol_lubelskie": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-128 — Dolnoslaskie: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_dolnoslaskie`, `land_ger_eastern_germany`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_ger_eastern_germany": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-132 — Central Romania: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rom_central_romania`, `sea_m10`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "sea_m10": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-134 — Lower Egypt: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_lower_egypt`, `land_transjordan`, `sea_m8`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_transjordan": {
    "river_crossing": true
  },
  "sea_m8": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-136 — Sudan: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sudan`, `land_tanganyika`, `land_belgian_congo`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_tanganyika": {
    "river_crossing": true
  },
  "land_belgian_congo": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-139 — Nigeria: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nigeria`, `sea_a51`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "sea_a51": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-143 — Cameroon: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cameroon`, `land_chad`, `sea_a51`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_chad": {
    "river_crossing": true
  },
  "sea_a51": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-144 — Niger: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_niger`, `land_ivory_coast`, `land_gold_coast`, `land_dahomey`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_ivory_coast": {
    "river_crossing": true
  },
  "land_gold_coast": {
    "river_crossing": true
  },
  "land_dahomey": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-145 — Dahomey: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_dahomey`, `land_niger`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_niger": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-147 — French Sudan: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_sudan`, `land_ivory_coast`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_ivory_coast": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-150 — Eastern Anatolia: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_eastern_anatolia`, `land_tur_karadeniz`, `sea_m11`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_tur_karadeniz": {
    "river_crossing": true
  },
  "sea_m11": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-154 — Belgian Congo: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_belgian_congo`, `land_sudan`, `sea_a51`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_sudan": {
    "river_crossing": true
  },
  "sea_a51": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-155 — Portuguese East Africa: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_portuguese_east_africa`, `land_south_africa`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_south_africa": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-156 — Leningrad: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_leningrad`, `land_fin_viipuri_province`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_fin_viipuri_province": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-158 — Moscow: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_moscow`, `land_usr_gorky`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_usr_gorky": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-159 — Southern Belorussia: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_southern_belorussia`, `land_usr_orel_kursk`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_usr_orel_kursk": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-161 — Tula-Lipetsk: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_tula_lipetsk`, `land_usr_donets_kuban`, `land_usr_kalmytskaya`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_usr_donets_kuban": {
    "river_crossing": true
  },
  "land_usr_kalmytskaya": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-162 — Western Ukraine: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_western_ukraine`, `land_usr_eastern_ukraine`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_usr_eastern_ukraine": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-167 — Donets-Kuban: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_donets_kuban`, `sea_m11`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "sea_m11": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-168 — Stalingrad: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_stalingrad`, `land_usr_western_kazakhstan`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_usr_western_kazakhstan": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-169 — Saratov: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_saratov`, `land_usr_orenburg`, `land_usr_ural`, `land_usr_western_kazakhstan`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_usr_orenburg": {
    "river_crossing": true
  },
  "land_usr_ural": {
    "river_crossing": true
  },
  "land_usr_western_kazakhstan": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-171 — Gorky: missing glossary-described river boundaries

**Field:** `incoming_edges` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_gorky`, `land_usr_moscow`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "land_usr_moscow": {
    "river_crossing": true
  }
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Add/reconcile physical boundary and reciprocal adjacency first. Only incoming combat crossing is specified; has_river, railway and reverse crossing remain independently authorable.

## EA-181 — Denmark ↔ Western Germany: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_denmark`, `land_ger_western_germany`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** Printed land border and north-south rail through Jutland.

## EA-182 — Southern Norway ↔ Norrland: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_southern_norway`, `land_swe_norrland`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** Broad shared border; railway to Sweden instead crosses farther south into Gotaland.

## EA-183 — Southern Norway ↔ Gotaland: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_southern_norway`, `land_swe_gotaland`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** Rail from Oslo crosses into Gotaland.

## EA-184 — Normandy ↔ Aquitaine: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_normandy`, `land_fra_aquitaine`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2220, 1180, 3070, 2110], "crop": "evidence/ea_france.png"}

**Scope / dependency:** Shared broad west-France border with north-south railway.

## EA-185 — Picardy ↔ Alsace-Lorraine: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_picardy`, `land_fra_alsace_lorraine`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2220, 1180, 3070, 2110], "crop": "evidence/ea_france.png"}

**Scope / dependency:** Shared border east of Paris, with rail shown.

## EA-186 — Alsace-Lorraine ↔ Switzerland: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_alsace_lorraine`, `land_switzerland`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2220, 1180, 3070, 2110], "crop": "evidence/ea_france.png"}

**Scope / dependency:** Visible shared boundary and railway southeast of Alsace-Lorraine.

## EA-187 — Northern Iraq ↔ Azerbaijan: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_iraq`, `land_azerbaijan`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Printed shared border; no cross-border track visible.

## EA-188 — Azerbaijan ↔ Southern Iran: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_azerbaijan`, `land_iran_southern_iran`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** North-south Iranian railway crosses their shared boundary.

## EA-189 — Northern Iraq ↔ Transjordan: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_iraq`, `land_transjordan`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Printed shared boundary near northwestern Saudi corner; no track crosses.

## EA-190 — Northern Iraq ↔ Saudi Arabia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_iraq`, `land_saudi_arabia`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Broad shared boundary; no rail.

## EA-191 — Southern Iraq ↔ Saudi Arabia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southern_iraq`, `land_saudi_arabia`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Broad shared boundary; no rail.

## EA-192 — Kuwait ↔ Saudi Arabia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_kuwait`, `land_saudi_arabia`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Kuwait directly borders Saudi Arabia; no track.

## EA-193 — Transjordan ↔ Saudi Arabia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_transjordan`, `land_saudi_arabia`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Broad shared boundary; no track.

## EA-194 — Aden ↔ Oman: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_aden`, `land_oman`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Broad shared boundary; no track.

## EA-195 — Aden ↔ Qatar: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_aden`, `land_qatar`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Broad shared boundary; no track.

## EA-196 — Southwest Africa ↔ Cape Town: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southwest_africa`, `land_cape_town`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}

**Scope / dependency:** Broad printed border, no track across it.

## EA-197 — South Africa ↔ Portuguese East Africa: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_south_africa`, `land_portuguese_east_africa`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}

**Scope / dependency:** Shared river boundary, no track.

## EA-231 — North Western Mediterranean ↔ Tyrrhenian Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m1`, `sea_m3`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-232 — Western Mediterranean ↔ Strait of Gibraltar (Atlantic): adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m2`, `sea_a44`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": "Strait of Gibraltar"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-233 — Tyrrhenian Sea ↔ Ionian Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m3`, `sea_m6`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-234 — Central Mediterranean Sea ↔ Ionian Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m4`, `sea_m6`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-235 — Central Mediterranean Sea ↔ Eastern Mediterranean: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m4`, `sea_m8`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-236 — Adriatic Sea ↔ Ionian Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m5`, `sea_m6`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-237 — Ionian Sea ↔ Aegean Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m6`, `sea_m7`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-238 — Ionian Sea ↔ Eastern Mediterranean: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m6`, `sea_m8`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-239 — Aegean Sea ↔ Eastern Mediterranean: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m7`, `sea_m8`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-240 — Aegean Sea ↔ Eastern Mediterranean: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m7`, `sea_m9`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-241 — Aegean Sea ↔ Western Black Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m7`, `sea_m10`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": "Turkish Straits"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-242 — Eastern Mediterranean ↔ Eastern Mediterranean: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m8`, `sea_m9`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-243 — Eastern Mediterranean ↔ Red Sea South: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m8`, `sea_i5`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": "Suez Canal"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Printed shared sea boundary or printed controlled passage. M3–M6 is the water gap between Sicily and Southern Italy; do not model the land narrow crossing as closing the naval border automatically.

## EA-252 — London ↔ Picardy: printed narrow crossing

**Field:** `narrow_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_london`, `land_fra_picardy`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "both_directions": true,
  "narrow_crossings": 3,
  "narrow_crossing_sea_zones": [
    "sea_a22",
    "sea_a23"
  ],
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Capacity is the printed yellow diamond numeral. Blocking-sea assignment at two-sea boundary should be kept explicit. Preserve independent destination terrain and directional river rules.

## EA-254 — Corsica ↔ Sardinia: printed narrow crossing

**Field:** `narrow_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_corsica`, `land_ita_sardinia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "both_directions": true,
  "narrow_crossings": 2,
  "narrow_crossing_sea_zones": [
    "sea_m1",
    "sea_m3"
  ],
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Capacity is the printed yellow diamond numeral. Blocking-sea assignment at two-sea boundary should be kept explicit. Preserve independent destination terrain and directional river rules.

## EA-255 — Southern Italy ↔ Sicily: printed narrow crossing

**Field:** `narrow_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_southern_italy`, `land_ita_sicily`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "both_directions": true,
  "narrow_crossings": 2,
  "narrow_crossing_sea_zones": [
    "sea_m3",
    "sea_m6"
  ],
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Capacity is the printed yellow diamond numeral. Blocking-sea assignment at two-sea boundary should be kept explicit. Preserve independent destination terrain and directional river rules.

## EA-256 — Gibraltar ↔ Spanish Morocco: printed narrow crossing

**Field:** `narrow_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gibraltar`, `land_spanish_morocco`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "both_directions": true,
  "narrow_crossings": 2,
  "narrow_crossing_sea_zones": [
    "sea_a44",
    "sea_m2"
  ],
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Capacity is the printed yellow diamond numeral. Blocking-sea assignment at two-sea boundary should be kept explicit. Preserve independent destination terrain and directional river rules.

## EA-257 — Rhodes ↔ Akdeniz: printed narrow crossing

**Field:** `narrow_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rhodes`, `land_tur_akdeniz`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "both_directions": true,
  "narrow_crossings": 2,
  "narrow_crossing_sea_zones": [
    "sea_m7",
    "sea_m9"
  ],
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Capacity is the printed yellow diamond numeral. Blocking-sea assignment at two-sea boundary should be kept explicit. Preserve independent destination terrain and directional river rules.

## EA-258 — Eritrea ↔ Yemen: printed narrow crossing

**Field:** `narrow_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_eritrea`, `land_yemen`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "both_directions": true,
  "narrow_crossings": 1,
  "narrow_crossing_sea_zones": [
    "sea_i5"
  ],
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Capacity is the printed yellow diamond numeral. Blocking-sea assignment at two-sea boundary should be kept explicit. Preserve independent destination terrain and directional river rules.

## EA-299 — Cyprus / M9: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cyprus`, `sea_m9`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "minor_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_turkey_iran.png", "rectangle": [3850, 2050, 5580, 2980]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-311 — Central Romania / M10: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rom_central_romania`, `sea_m10`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "minor_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-312 — Southern Ukraine / M10: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_southern_ukraine`, `sea_m10`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "major_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-315 — Donets-Kuban / M11: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_donets_kuban`, `sea_m11`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "major_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Blue anchor is the sole facility. The separate airplane-over-waves icon south of the territorial border belongs to North-Caucasia. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-318 — Akdeniz / M9: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_akdeniz`, `sea_m9`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "minor_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_turkey_iran.png", "rectangle": [3850, 2050, 5580, 2980]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-326 — Tripolitania / M4: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tripolitania`, `sea_m4`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "minor_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_mediterranean_west.png", "rectangle": [2050, 1900, 3950, 3300]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-344 — Northern England: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_northern_england`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-345 — Southern England: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_southern_england`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-346 — London: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_london`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-347 — Paris: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_paris`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2220, 1180, 3070, 2110], "crop": "evidence/ea_france.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-348 — Southern France: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_southern_france`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2220, 1180, 3070, 2110], "crop": "evidence/ea_france.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-349 — Western Germany: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_western_germany`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-350 — Berlin: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_berlin`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-351 — Bavaria: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_bavaria`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-352 — Northern Italy: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_northern_italy`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-353 — Sardinia: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_sardinia`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-354 — Galicia and Leon: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_galicia_and_leon`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-355 — Central Romania: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rom_central_romania`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-356 — Cyprus: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cyprus`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-357 — Northern Algeria: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_algeria`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-358 — Leningrad: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_leningrad`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-359 — Smolensk: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_smolensk`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-360 — Moscow: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_moscow`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-361 — Kiev: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kiev`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-362 — Crimea: printed airfield

**Field:** `node_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_crimea`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "airfield"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3980, 1375, 5380, 2300], "crop": "evidence/ea_western_ussr_south.png"}

**Scope / dependency:** Green runway symbol. Fixed printed initial infrastructure; later damage/building state separate.

## EA-368 — Karadeniz ↔ Eastern Anatolia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_karadeniz`, `land_tur_eastern_anatolia`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Printed shared boundary and railway northeast of Ankara.

## EA-382 — Mozambique Channel ↔ Sea Zone I2: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i1`, `sea_i2`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Positive-length printed boundary in southern Indian basin; ocean eastern boundary links are coordinated with Asia audit.

## EA-383 — Mozambique Channel ↔ Red Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i1`, `sea_i3`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Positive-length printed boundary in southern Indian basin; ocean eastern boundary links are coordinated with Asia audit.

## EA-384 — Mozambique Channel ↔ sea_a54: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i1`, `sea_a54`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Positive-length printed boundary in southern Indian basin; ocean eastern boundary links are coordinated with Asia audit.

## EA-385 — Sea Zone I2 ↔ Red Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i2`, `sea_i3`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Positive-length printed boundary in southern Indian basin; ocean eastern boundary links are coordinated with Asia audit.

## EA-386 — Red Sea ↔ Gulf of Aden: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i3`, `sea_i4`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Positive-length printed boundary in southern Indian basin; ocean eastern boundary links are coordinated with Asia audit.

## EA-389 — Norwegian Sea ↔ sea_a5: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a6`, `sea_a5`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Printed positive-length sea boundary. A10–A12 is the Danish Straits route; mainland canal A11–A12 is a distinct controlled passage.

## EA-390 — Norwegian Sea ↔ Skagerrak: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a6`, `sea_a10`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Printed positive-length sea boundary. A10–A12 is the Danish Straits route; mainland canal A11–A12 is a distinct controlled passage.

## EA-391 — Norwegian Sea ↔ Kattegat: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a6`, `sea_a11`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Printed positive-length sea boundary. A10–A12 is the Danish Straits route; mainland canal A11–A12 is a distinct controlled passage.

## EA-392 — Norwegian Sea ↔ English Channel: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a6`, `sea_a23`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Printed positive-length sea boundary. A10–A12 is the Danish Straits route; mainland canal A11–A12 is a distinct controlled passage.

## EA-393 — North Atlantic Approaches ↔ sea_a5: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a7`, `sea_a5`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Printed positive-length sea boundary. A10–A12 is the Danish Straits route; mainland canal A11–A12 is a distinct controlled passage.

## EA-394 — Skagerrak ↔ Baltic Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a10`, `sea_a12`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": "Danish Straits"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Printed positive-length sea boundary. A10–A12 is the Danish Straits route; mainland canal A11–A12 is a distinct controlled passage.

## EA-395 — Baltic Sea ↔ Baltic East: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a12`, `sea_a14`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Printed positive-length sea boundary. A10–A12 is the Danish Straits route; mainland canal A11–A12 is a distinct controlled passage.

## EA-396 — Kattegat ↔ English Channel: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a11`, `sea_a23`

**Current:**

```json
{
  "forward": null,
  "reverse": null
}
```

**Proposed:**

```json
{
  "exists": true,
  "border_terrain": "sea",
  "canal_or_strait": null
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Printed positive-length sea boundary. A10–A12 is the Danish Straits route; mainland canal A11–A12 is a distinct controlled passage.

## EA-416 — Norrland / A13: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_swe_norrland`, `sea_a13`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "minor_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-421 — Latvia / A14: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_latvia`, `sea_a14`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "major_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-424 — West Poland / A12: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_west_poland`, `sea_a12`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "minor_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-471 — Berlin ↔ Western Germany: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_berlin`, `land_ger_western_germany`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_france_germany.png", "rectangle": [2520, 1100, 3420, 1900]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-472 — Berlin ↔ Bavaria: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_berlin`, `land_ger_bavaria`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_france_germany.png", "rectangle": [2520, 1100, 3420, 1900]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-473 — Berlin ↔ Bohemia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_berlin`, `land_cze_bohemia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_france_germany.png", "rectangle": [2520, 1100, 3420, 1900]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-474 — Eastern Germany ↔ Bohemia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_eastern_germany`, `land_cze_bohemia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_france_germany.png", "rectangle": [2520, 1100, 3420, 1900]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-475 — Eastern Germany ↔ Dolnoslaskie: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_eastern_germany`, `land_pol_dolnoslaskie`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_poland_carpathians.png", "rectangle": [3450, 1120, 4300, 2000]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-476 — Picardy ↔ Bavaria: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_picardy`, `land_ger_bavaria`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_france_germany.png", "rectangle": [2520, 1100, 3420, 1900]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-477 — Switzerland ↔ Austria: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_switzerland`, `land_aut_austria`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_italy_balkans.png", "rectangle": [2790, 1710, 3940, 2620]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-478 — Northern Italy ↔ Western Yugoslavia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_northern_italy`, `land_yug_western_yugoslavia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_italy_balkans.png", "rectangle": [2790, 1710, 3940, 2620]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-479 — Macedonia ↔ Albania: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_macedonia`, `land_albania`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-480 — Lapland ↔ Viipuri Province: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_lapland`, `land_fin_viipuri_province`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_finland_baltic.png", "rectangle": [3550, 0, 4380, 1550]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-481 — Lapland ↔ Kola: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_lapland`, `land_usr_kola`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_finland_baltic.png", "rectangle": [3550, 0, 4380, 1550]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-482 — Viipuri Province ↔ Leningrad: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_viipuri_province`, `land_usr_leningrad`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_finland_baltic.png", "rectangle": [3550, 0, 4380, 1550]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-483 — Latvia ↔ Leningrad: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_latvia`, `land_usr_leningrad`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_finland_baltic.png", "rectangle": [3550, 0, 4380, 1550]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-484 — Latvia ↔ Podlachia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_latvia`, `land_pol_podlachia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_finland_baltic.png", "rectangle": [3550, 0, 4380, 1550]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-485 — West Poland ↔ Lubelskie: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_west_poland`, `land_pol_lubelskie`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_poland_carpathians.png", "rectangle": [3450, 1120, 4300, 2000]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-486 — East Poland ↔ Central Romania: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_east_poland`, `land_rom_central_romania`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_poland_carpathians.png", "rectangle": [3450, 1120, 4300, 2000]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-487 — East Poland ↔ Bessarabia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_east_poland`, `land_rom_bessarabia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_poland_carpathians.png", "rectangle": [3450, 1120, 4300, 2000]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-488 — Galicia and Leon ↔ Portugal: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_galicia_and_leon`, `land_portugal`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-489 — Galicia and Leon ↔ Basque Country: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_galicia_and_leon`, `land_esp_basque_country`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-490 — Aquitaine ↔ Basque Country: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_aquitaine`, `land_esp_basque_country`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-491 — Southern France ↔ Basque Country: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_southern_france`, `land_esp_basque_country`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-492 — Southern France ↔ Catalonia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_southern_france`, `land_esp_catalonia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-493 — French Morocco ↔ Western Algeria: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_morocco`, `land_western_algeria`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sahara.png", "rectangle": [1730, 2990, 3940, 3890]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-494 — Tunisia ↔ Tripolitania: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tunisia`, `land_tripolitania`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sahara.png", "rectangle": [1730, 2990, 3940, 3890]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-495 — Tunisia ↔ Southern Algeria: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tunisia`, `land_southern_algeria`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sahara.png", "rectangle": [1730, 2990, 3940, 3890]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-496 — Southern Algeria ↔ Tripolitania: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southern_algeria`, `land_tripolitania`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sahara.png", "rectangle": [1730, 2990, 3940, 3890]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-497 — Cyrenaica ↔ Western Egypt: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cyrenaica`, `land_western_egypt`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-498 — Nubia ↔ Eritrea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nubia`, `land_eritrea`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-499 — Sudan ↔ Tanganyika: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sudan`, `land_tanganyika`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-500 — Sudan ↔ Belgian Congo: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sudan`, `land_belgian_congo`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-501 — Cameroon ↔ Chad: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cameroon`, `land_chad`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sudan_west.png", "rectangle": [2600, 3470, 4480, 4460]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-502 — French Somaliland ↔ British Somaliland: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_somaliland`, `land_british_somaliland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-503 — French Somaliland ↔ Eritrea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_somaliland`, `land_eritrea`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-504 — British Somaliland ↔ Italian Somaliland: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_british_somaliland`, `land_italian_somaliland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-505 — Italian Somaliland ↔ Tanganyika: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_italian_somaliland`, `land_tanganyika`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-506 — Transjordan ↔ Lower Egypt: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_transjordan`, `land_lower_egypt`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-507 — Karelia ↔ Western Russia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_karelia`, `land_usr_western_russia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_north.png", "rectangle": [3775, 350, 5230, 1600]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-508 — Kaluga Oblast ↔ Orel-Kursk: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kaluga_oblast`, `land_usr_orel_kursk`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_north.png", "rectangle": [3775, 350, 5230, 1600]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-509 — Moscow ↔ Gorky: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_moscow`, `land_usr_gorky`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_north.png", "rectangle": [3775, 350, 5230, 1600]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-510 — Moscow ↔ Saratov: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_moscow`, `land_usr_saratov`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_north.png", "rectangle": [3775, 350, 5230, 1600]}

**Scope / dependency:** Positive printed border and crossing track traced in the second pass. Directional terrain, river combat crossing and movement-route flags remain separately authored.

## EA-516 — Northern Ireland: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_northern_ireland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_ireland",
      "kind": "land_border",
      "railway_connection": true,
      "passable": true
    },
    {
      "neighbor_id": "land_gbr_scotland",
      "kind": "narrow_crossing",
      "narrow_crossings": 2,
      "railway_connection": false
    },
    {
      "neighbor_id": "land_gbr_northern_england",
      "kind": "narrow_crossing",
      "narrow_crossings": 2,
      "railway_connection": false
    },
    {
      "neighbor_id": "sea_a17",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_northern_ireland_major_shipyard",
      "type": "major_shipyard",
      "sea_accesses": [
        "sea_a17"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_round2_britain_channels.png",
          "rectangle": [
            1690,
            680,
            2720,
            1770
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_britain_channels.png", "rectangle": [1690, 680, 2720, 1770]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-517 — Shetland Islands: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_shetland_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_a6",
      "kind": "coast"
    }
  ],
  "ambiguous": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_atlantic_islands.png", "rectangle": [1400, 0, 2480, 1100]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics.

## EA-518 — Iceland: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_iceland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_a3",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_a4",
      "kind": "coast"
    }
  ],
  "ambiguous": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_atlantic_islands.png", "rectangle": [1400, 0, 2480, 1100]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics.

## EA-519 — Faroe Islands: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_faroe_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_a4",
      "kind": "coast"
    }
  ],
  "ambiguous": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_atlantic_islands.png", "rectangle": [1400, 0, 2480, 1100]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics.

## EA-520 — Svalbard: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_svalbard`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_a5",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_arctic.png", "rectangle": [1840, 0, 4800, 690]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-521 — Northern Norway: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_northern_norway`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_nor_trondelag",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_swe_norrland",
      "kind": "land_border",
      "railway_connection": true,
      "passable": true
    },
    {
      "neighbor_id": "land_fin_lapland",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_a5",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_a8",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_northern_norway_major_port",
      "type": "major_port",
      "sea_accesses": [
        "sea_a8"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_naval_norway_finland_20261006.png",
          "rectangle": [
            2890,
            0,
            4520,
            690
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_arctic.png", "rectangle": [1840, 0, 4800, 690]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-522 — Helsinki: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_helsinki`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_fin_southern_finland",
      "kind": "land_border",
      "railway_connection": true,
      "passable": true
    },
    {
      "neighbor_id": "sea_a13",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_a14",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_helsinki_minor_shipyard",
      "type": "minor_shipyard",
      "sea_accesses": [
        "sea_a13",
        "sea_a14"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_naval_baltic_20261006.png",
          "rectangle": [
            3340,
            430,
            4300,
            1130
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_finland_baltic.png", "rectangle": [3550, 0, 4380, 1550]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-523 — Sicily: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_sicily`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_ita_southern_italy",
      "kind": "narrow_crossing",
      "narrow_crossings": 2,
      "railway_connection": false
    },
    {
      "neighbor_id": "sea_m3",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_m4",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_m6",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_sicily_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_m3"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_greece_mediterranean.png",
          "rectangle": [
            2800,
            1850,
            4470,
            3200
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-524 — Malta: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_malta`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_m4",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_malta_major_dockyard",
      "type": "major_dockyard",
      "sea_accesses": [
        "sea_m4"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_greece_mediterranean.png",
          "rectangle": [
            2800,
            1850,
            4470,
            3200
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-525 — Rhodes: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rhodes`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_tur_akdeniz",
      "kind": "narrow_crossing",
      "narrow_crossings": 2,
      "railway_connection": false
    },
    {
      "neighbor_id": "sea_m7",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_rhodes_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_m7"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_turkey_iran.png",
          "rectangle": [
            3850,
            2050,
            5580,
            2980
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-526 — Peloponnese: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_peloponnese`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_gre_thessaly",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_m6",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_m7",
      "kind": "coast"
    }
  ],
  "ambiguous": [
    {
      "field": "railway_connection",
      "neighbor_id": "land_gre_thessaly",
      "reason": "No clear rail crossing through the tiny isthmus is resolved at source resolution; do not infer rail from neighboring Greek network."
    }
  ],
  "expected_naval_facilities": [
    {
      "id": "facility_peloponnese_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_m6",
        "sea_m7"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_greece_mediterranean.png",
          "rectangle": [
            2800,
            1850,
            4470,
            3200
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-527 — Crete: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_crete`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_m7",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_m8",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-528 — Ifni: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ifni`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_french_morocco",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_a44",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_north_africa_west_detail.png", "rectangle": [1730, 2890, 3030, 3850]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-529 — Rio de Oro: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rio_de_oro`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_french_morocco",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_mauritania",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_a44",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_a46",
      "kind": "coast"
    }
  ],
  "ambiguous": [
    {
      "neighbor_id": "land_western_algeria",
      "reason": "Possible political-border point at the Sahara junction; no positive-length passable boundary is established."
    }
  ],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sahara.png", "rectangle": [1730, 2990, 3940, 3890]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-530 — Canary Islands: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_canary_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_a44",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_north_africa_west_detail.png", "rectangle": [1730, 2890, 3030, 3850]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-531 — Cape Verde: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cape_verde`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_a46",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_west_africa.png", "rectangle": [1530, 3480, 3380, 4310]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-532 — Mauritania: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_mauritania`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_rio_de_oro",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_portuguese_guinea",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_french_guinea",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_french_sudan",
      "kind": "land_border",
      "railway_connection": true,
      "passable": true
    },
    {
      "neighbor_id": "land_western_algeria",
      "kind": "land_border",
      "railway_connection": false,
      "passable": false
    },
    {
      "neighbor_id": "sea_a46",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_a48",
      "kind": "coast"
    }
  ],
  "ambiguous": [
    {
      "neighbor_id": "land_french_morocco",
      "reason": "Possible point-only contact at the Rio de Oro/Western Algeria junction; do not create a movement edge from a point."
    }
  ],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sahara.png", "rectangle": [1730, 2990, 3940, 3890]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-533 — Portuguese Guinea: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_portuguese_guinea`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_mauritania",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_french_guinea",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_a48",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_senegal_coast.png", "rectangle": [1700, 3500, 2440, 4080]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-534 — French Guinea: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_guinea`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_mauritania",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_portuguese_guinea",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_sierra_leone",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_liberia",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_ivory_coast",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_french_sudan",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_a48",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_senegal_coast.png", "rectangle": [1700, 3500, 2440, 4080]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-535 — Sierra Leone: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sierra_leone`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_french_guinea",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_liberia",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_a48",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_sierra_leone_major_port",
      "type": "major_port",
      "sea_accesses": [
        "sea_a48"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_west_africa.png",
          "rectangle": [
            1530,
            3480,
            3380,
            4310
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_senegal_coast.png", "rectangle": [1700, 3500, 2440, 4080]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-536 — Liberia: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_liberia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_sierra_leone",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_french_guinea",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_ivory_coast",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_a48",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_senegal_coast.png", "rectangle": [1700, 3500, 2440, 4080]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-537 — Ivory Coast: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ivory_coast`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_liberia",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_french_guinea",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_french_sudan",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_niger",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_gold_coast",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_a51",
      "kind": "coast"
    }
  ],
  "ambiguous": [
    {
      "field": "railway_connection",
      "neighbor_id": "land_french_sudan",
      "reason": "Rail spur enters the northern roundel boundary near the Guinea/Sudan/Ivory junction; exact border crossing needs finer source resolution."
    }
  ],
  "expected_naval_facilities": [
    {
      "id": "facility_ivory_coast_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a51"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_west_africa.png",
          "rectangle": [
            1530,
            3480,
            3380,
            4310
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sudan_west.png", "rectangle": [2600, 3470, 4480, 4460]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-538 — Gold Coast: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gold_coast`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_ivory_coast",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_niger",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_dahomey",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "sea_a51",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_gold_coast_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a51"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_west_africa.png",
          "rectangle": [
            1530,
            3480,
            3380,
            4310
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sudan_west.png", "rectangle": [2600, 3470, 4480, 4460]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-539 — São Tomé and Príncipe: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sao_tome_and_principe`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_a51",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_west_africa.png", "rectangle": [1530, 3480, 3380, 4310]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-540 — Ascension: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ascension`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_a50",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_ascension_minor_dockyard",
      "type": "minor_dockyard",
      "sea_accesses": [
        "sea_a50"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_west_africa.png",
          "rectangle": [
            1530,
            3480,
            3380,
            4310
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_africa_west_south.png", "rectangle": [1600, 3500, 4450, 4888]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-541 — Réunion: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_reunion`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_i2",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-542 — Yemen: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_yemen`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "land_saudi_arabia",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_aden",
      "kind": "land_border",
      "railway_connection": false,
      "passable": true
    },
    {
      "neighbor_id": "land_eritrea",
      "kind": "narrow_crossing",
      "narrow_crossings": 1,
      "railway_connection": false
    },
    {
      "neighbor_id": "sea_i4",
      "kind": "coast"
    },
    {
      "neighbor_id": "sea_i5",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-543 — Saint Helena: complete second-pass neighbor candidates

**Field:** `neighbor_candidates` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_saint_helena`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "definite": [
    {
      "neighbor_id": "sea_a53",
      "kind": "coast"
    }
  ],
  "ambiguous": [],
  "expected_naval_facilities": [
    {
      "id": "facility_saint_helena_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a53"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "evidence/ea_naval_atlantic_islands_20261006.png",
          "rectangle": [
            1650,
            3700,
            3050,
            4600
          ]
        }
      ],
      "notes": "Printed symbol; facility identity is independent of sea-access edges."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_africa_west_south.png", "rectangle": [1600, 3500, 4450, 4888]}

**Scope / dependency:** Physical and narrow contacts are separate; no adjacency is implied by an island group being nearby. Apply destination terrain and directional combat rivers from the glossary independently. The rail values concern printed border-crossing rail, not facility connection heuristics. Facility inventory superseded by fresh 2026-10-06 source-image naval review.

## EA-544 — A5: Arctic adjacency and coastline supplement

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a5`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "sea_neighbors": [
    "sea_a3",
    "sea_a4",
    "sea_a6",
    "sea_a7",
    "sea_a8"
  ],
  "coastal_land_nodes": [
    "land_svalbard",
    "land_nor_trondelag",
    "land_nor_northern_norway"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_arctic.png", "rectangle": [1840, 0, 4800, 690]}

**Scope / dependency:** Positive sea boundaries and coast segments inspected. Source label controls identity. A5–A4 shares a short positive vertical segment, not merely a corner.

## EA-545 — A8: Arctic adjacency and coastline supplement

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a8`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "sea_neighbors": [
    "sea_a5",
    "sea_a9"
  ],
  "coastal_land_nodes": [
    "land_nor_northern_norway",
    "land_fin_lapland",
    "land_usr_kola"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_arctic.png", "rectangle": [1840, 0, 4800, 690]}

**Scope / dependency:** Positive sea boundaries and coast segments inspected. Source label controls identity. A5–A4 shares a short positive vertical segment, not merely a corner.

## EA-546 — A9: Arctic adjacency and coastline supplement

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a9`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "sea_neighbors": [
    "sea_a8"
  ],
  "coastal_land_nodes": [
    "land_usr_kola",
    "land_usr_karelia",
    "land_usr_northern_russia",
    "land_usr_zuryenia",
    "land_usr_vyatka",
    "land_usr_yugria",
    "land_usr_samoyedia"
  ],
  "exceptional_route_references": [
    {
      "route": "Northern Sea Route",
      "other_sea_node_id": "sea_p1",
      "ordinary_adjacency": false,
      "rule_reference": "v4.3 rulebook §1.13, printed p17; mechanisms_and_schema.md MS-03",
      "notes": "The printed P1 arrow denotes restricted special-route transit; it must not grant ordinary sea movement."
    },
    {
      "route": "Baltic–White Canal",
      "other_sea_node_id": "sea_a14",
      "ordinary_adjacency": false,
      "rule_reference": "mechanisms_and_schema.md controlled passage proposals",
      "notes": "Conditional canal transit through the intervening land geography; do not add an unrestricted A9–A14 sea border."
    }
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_white_sea.png", "rectangle": [4300, 0, 5910, 620]}

**Scope / dependency:** A9 coasts Kola, Karelia, Northern Russia, Zuryenia, Vyatka, Yugria and Samoyedia. The coast continues through the Ob gulf without a divider. Its sole ordinary neighboring sea is A8. The printed P1 arrow is the restricted Northern Sea Route (§1.13 p17); A14 transit uses the Baltic–White Canal. Both are exceptional routes, not ordinary sea adjacency.

## EA-551 — Podlachia ↔ Southern Belorussia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_podlachia`, `land_usr_southern_belorussia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "exists": true,
  "railway_connection": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_poland.png", "rectangle": [3210, 850, 4170, 1780]}

**Scope / dependency:** The eastbound Podlachia rail crosses the short positive border south of the Northern/Southern Belorussia dividing line, before the Lubelskie junction.

## EA-565 — Northern Ireland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_northern_ireland`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_northern_ireland_major_shipyard",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a17"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_round2_britain_channels.png",
        "rectangle": [
          1690,
          680,
          2720,
          1770
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_britain_channels.png", "rectangle": [1690, 680, 2720, 1770]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-580 — Norrland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_swe_norrland`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_norrland_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a13"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_baltic_20261006.png",
        "rectangle": [
          3340,
          430,
          4300,
          1130
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-583 — Northern Norway: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_northern_norway`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_northern_norway_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_a8"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_norway_finland_20261006.png",
        "rectangle": [
          2890,
          0,
          4520,
          690
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_norway_finland_20261006.png", "rectangle": [2890, 0, 4520, 690]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-585 — Helsinki: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_helsinki`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_helsinki_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_a13",
      "sea_a14"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_baltic_20261006.png",
        "rectangle": [
          3340,
          430,
          4300,
          1130
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** White crane sits at the A13/A14 sea-divider endpoint. One physical minor shipyard with two sea accesses. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-587 — Latvia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_latvia`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_latvia_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_a14"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_baltic_20261006.png",
        "rectangle": [
          3340,
          430,
          4300,
          1130
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-588 — West Poland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_west_poland`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_west_poland_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_a12"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_baltic_20261006.png",
        "rectangle": [
          3340,
          430,
          4300,
          1130
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-590 — Karelia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_karelia`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_karelia_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a9"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_round2_white_sea.png",
        "rectangle": [
          4300,
          0,
          5910,
          620
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_white_sea.png", "rectangle": [4300, 0, 5910, 620]}

**Scope / dependency:** The White Sea white anchor is west of the Karelia/Northern Russia land border, on the Karelia side. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-591 — Galicia and Leon: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_galicia_and_leon`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_galicia_and_leon_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a28"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_round2_iberia.png",
        "rectangle": [
          1700,
          2000,
          2850,
          2800
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_galicia_and_leon_major_shipyard",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a35"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_round2_iberia.png",
        "rectangle": [
          1700,
          2000,
          2850,
          2800
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-596 — Portugal: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_portugal`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_portugal_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_a35"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_round2_iberia.png",
        "rectangle": [
          1700,
          2000,
          2850,
          2800
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-597 — Gibraltar: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gibraltar`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_gibraltar_major_dockyard",
    "type": "major_dockyard",
    "sea_accesses": [
      "sea_a44",
      "sea_m2"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_mediterranean_west.png",
        "rectangle": [
          2050,
          1900,
          3950,
          3300
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_mediterranean_west.png", "rectangle": [2050, 1900, 3950, 3300]}

**Scope / dependency:** Single blue circled anchor sits on the A44/M2 dividing line; one physical major dockyard with two accesses. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-602 — Sicily: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_sicily`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_sicily_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m3"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_greece_mediterranean.png",
        "rectangle": [
          2800,
          1850,
          4470,
          3200
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-603 — Malta: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_malta`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_malta_major_dockyard",
    "type": "major_dockyard",
    "sea_accesses": [
      "sea_m4"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_greece_mediterranean.png",
        "rectangle": [
          2800,
          1850,
          4470,
          3200
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-607 — Thessaly: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_thessaly`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_thessaly_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_m7"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_greece_mediterranean.png",
        "rectangle": [
          2800,
          1850,
          4470,
          3200
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-608 — Peloponnese: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_peloponnese`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_peloponnese_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m6",
      "sea_m7"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_greece_mediterranean.png",
        "rectangle": [
          2800,
          1850,
          4470,
          3200
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Single white anchor sits on the M6/M7 dividing line; one physical minor port with two accesses. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-609 — Rhodes: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rhodes`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_rhodes_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m7"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_turkey_iran.png",
        "rectangle": [
          3850,
          2050,
          5580,
          2980
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_turkey_iran.png", "rectangle": [3850, 2050, 5580, 2980]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-610 — Cyprus: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cyprus`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_cyprus_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m9"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_turkey_iran.png",
        "rectangle": [
          3850,
          2050,
          5580,
          2980
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_turkey_iran.png", "rectangle": [3850, 2050, 5580, 2980]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-612 — Central Romania: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rom_central_romania`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_central_romania_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_m10"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_greece_mediterranean.png",
        "rectangle": [
          2800,
          1850,
          4470,
          3200
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-614 — Southern Ukraine: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_southern_ukraine`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_southern_ukraine_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_m10"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_western_ussr_south.png",
        "rectangle": [
          3980,
          1375,
          5380,
          2300
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-617 — Donets-Kuban: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_donets_kuban`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_donets_kuban_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_m11"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_western_ussr_south.png",
        "rectangle": [
          3980,
          1375,
          5380,
          2300
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Blue anchor is the sole facility. The separate airplane-over-waves icon south of the territorial border belongs to North-Caucasia. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-619 — Kalmytskaya: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kalmytskaya`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_kalmytskaya_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m12"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_western_ussr_south.png",
        "rectangle": [
          3980,
          1375,
          5380,
          2300
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-623 — Akdeniz: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_akdeniz`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_akdeniz_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m9"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_turkey_iran.png",
        "rectangle": [
          3850,
          2050,
          5580,
          2980
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_turkey_iran.png", "rectangle": [3850, 2050, 5580, 2980]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-636 — Tripolitania: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tripolitania`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_tripolitania_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m4"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_mediterranean_west.png",
        "rectangle": [
          2050,
          1900,
          3950,
          3300
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_mediterranean_west.png", "rectangle": [2050, 1900, 3950, 3300]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-642 — Sierra Leone: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sierra_leone`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_sierra_leone_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_a48"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_west_africa.png",
        "rectangle": [
          1530,
          3480,
          3380,
          4310
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_west_africa.png", "rectangle": [1530, 3480, 3380, 4310]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-643 — Ivory Coast: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ivory_coast`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_ivory_coast_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a51"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_west_africa.png",
        "rectangle": [
          1530,
          3480,
          3380,
          4310
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_west_africa.png", "rectangle": [1530, 3480, 3380, 4310]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-644 — Gold Coast: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gold_coast`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_gold_coast_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a51"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_west_africa.png",
        "rectangle": [
          1530,
          3480,
          3380,
          4310
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_west_africa.png", "rectangle": [1530, 3480, 3380, 4310]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-648 — Ascension: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ascension`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_ascension_minor_dockyard",
    "type": "minor_dockyard",
    "sea_accesses": [
      "sea_a50"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_west_africa.png",
        "rectangle": [
          1530,
          3480,
          3380,
          4310
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_west_africa.png", "rectangle": [1530, 3480, 3380, 4310]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-649 — Saint Helena: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_saint_helena`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  {
    "id": "facility_saint_helena_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a53"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_atlantic_islands_20261006.png",
        "rectangle": [
          1650,
          3700,
          3050,
          4600
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_atlantic_islands_20261006.png", "rectangle": [1650, 3700, 3050, 4600]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## AP-001 — Missing Soviet land tile: Zuryenia

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_zuryenia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Zuryenia",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_zuryenia"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-002 — Missing Soviet land tile: Ural

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_ural`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Ural",
  "terrain": "normal",
  "ipp_value": 1,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_ural"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-003 — Missing Soviet land tile: Orenburg

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_orenburg`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Orenburg",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_orenburg"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4300, 1200, 6400, 2500); evidence/ap_central_asia.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-004 — Missing Soviet land tile: Western Kazakhstan

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_western_kazakhstan`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Western Kazakhstan",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_western_kazakhstan"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4300, 1200, 6400, 2500); evidence/ap_central_asia.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-005 — Missing Soviet land tile: Central Kazakhstan

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_central_kazakhstan`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Central Kazakhstan",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_central_kazakhstan"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4300, 1200, 6400, 2500); evidence/ap_central_asia.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-006 — Missing Soviet land tile: Turkmenistan

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_turkmenistan`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Turkmenistan",
  "terrain": "desert",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_turkmenistan",
  "coastal_facilities": {
    "sea_m12": [
      "minor_port"
    ]
  }
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4300, 1200, 6400, 2500); evidence/ap_central_asia.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).
- game_content/maps/gw36map.png rect (5050,1870,5940,2420); evidence/ap_rail_turkmenistan.png: Caspian minor-port symbol and broad-gauge rail.

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json. A minor port is printed on the M12 Caspian coast and is reached by a broad-gauge railway from Turkestan.

## AP-007 — Missing Soviet land tile: Vyatka

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_vyatka`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Vyatka",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_vyatka"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-008 — Missing Soviet land tile: Yugria

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_yugria`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Yugria",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_yugria"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-009 — Missing Soviet land tile: Samoyedia

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_samoyedia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Samoyedia",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_samoyedia"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-010 — Missing Soviet land tile: Lower Tunguska

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_lower_tunguska`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Lower Tunguska",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_lower_tunguska"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-011 — Missing Soviet land tile: Sibir

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_sibir`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Sibir",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_sibir"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-012 — Missing Soviet land tile: Tobolsk

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_tobolsk`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Tobolsk",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_tobolsk"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-013 — Missing Soviet land tile: Yenisei

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_yenisei`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Yenisei",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_yenisei"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-014 — Missing Soviet land tile: Evenkiland

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_evenkiland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Evenkiland",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_evenkiland"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-015 — Missing Soviet land tile: Western Yakutia

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_western_yakutia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Western Yakutia",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_western_yakutia"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-016 — Missing Soviet land tile: Northern Yakutia

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_northern_yakutia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Northern Yakutia",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_northern_yakutia"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-017 — Missing Soviet land tile: Eastern Yakutia

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_eastern_yakutia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Eastern Yakutia",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_eastern_yakutia"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-018 — Missing Soviet land tile: Chukotka

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_chukotka`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Chukotka",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_chukotka"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-019 — Missing Soviet land tile: Big Diomede Island

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_big_diomede_island`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Big Diomede Island",
  "terrain": "tundra",
  "ipp_value": 0,
  "original_owner": "Soviet Union",
  "is_city": false,
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usr_big_diomede_island"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- Terrain Glossary pp11–12 (Yugria omitted from glossary; map supports normal roundel terrain).

**Scope / dependency:** Complete physical neighbors are in data/asia_pacific_new_node_neighbors.json; all new land-border rail/gauge proposals are in data/asia_pacific_new_edge_rail_review.json. Express directional terrain/river combat requirements are in data/asia_pacific_directional_terrain.json. Named river transport is a separate proposed overlay.

## AP-020 — Missing island tile: Andaman Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_andaman_islands`, `sea_i12`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Andaman Islands",
  "terrain": "jungle",
  "ipp_value": 0,
  "original_owner": "FEC",
  "coastal_seas": [
    "sea_i12"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_andaman_islands"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-021 — Missing island tile: Maldive Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_maldive_islands`, `sea_i7`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Maldive Islands",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "FEC",
  "coastal_seas": [
    "sea_i7"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_maldive_islands"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-022 — Missing island tile: Bonin

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_jap_bonin`, `sea_p35`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Bonin",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "Japan",
  "coastal_seas": [
    "sea_p35"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_jap_bonin"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7900, 1000, 9900, 2850); evidence/ap_pacific_north.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-023 — Missing island tile: Midway

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usa_midway`, `sea_p22`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Midway",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "United States",
  "coastal_seas": [
    "sea_p22"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usa_midway"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7900, 1000, 9900, 2850); evidence/ap_pacific_north.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-024 — Missing island tile: Hawaii

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usa_hawaii`, `sea_p29`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Hawaii",
  "terrain": "mountain",
  "ipp_value": 2,
  "original_owner": "United States",
  "coastal_seas": [
    "sea_p29"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usa_hawaii"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7900, 1000, 9900, 2850); evidence/ap_pacific_north.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-025 — Missing island tile: Attu and Kiska

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usa_attu_and_kiska`, `sea_p4`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Attu and Kiska",
  "terrain": "mountain",
  "ipp_value": 0,
  "original_owner": "United States",
  "coastal_seas": [
    "sea_p4"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usa_attu_and_kiska"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-026 — Missing island tile: Marshall Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_jap_marshall_islands`, `sea_p47`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Marshall Islands",
  "terrain": "normal",
  "ipp_value": 1,
  "original_owner": "Japan",
  "coastal_seas": [
    "sea_p47"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_jap_marshall_islands"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (8000, 2750, 9900, 4888); evidence/ap_pacific_south.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-027 — Missing island tile: Line Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_line_islands`, `sea_p38`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Line Islands",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "FEC",
  "coastal_seas": [
    "sea_p38"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_line_islands"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7900, 1000, 9900, 2850); evidence/ap_pacific_north.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Great Britain versus FEC player allocation is separately uncertain in AP-094.

## AP-028 — Missing island tile: Solomon Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_solomon_islands`, `sea_p54`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Solomon Islands",
  "terrain": "jungle",
  "ipp_value": 0,
  "original_owner": "FEC",
  "coastal_seas": [
    "sea_p54"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_solomon_islands"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (8000, 2750, 9900, 4888); evidence/ap_pacific_south.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Great Britain versus FEC player allocation is separately uncertain in AP-094.

## AP-029 — Missing island tile: Gilbert Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_gilbert_islands`, `sea_p56`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Gilbert Islands",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "FEC",
  "coastal_seas": [
    "sea_p56"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_gilbert_islands"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (8000, 2750, 9900, 4888); evidence/ap_pacific_south.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Great Britain versus FEC player allocation is separately uncertain in AP-094.

## AP-030 — Missing island tile: Samoa

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usa_samoa`, `sea_p66`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Samoa",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "United States",
  "coastal_seas": [
    "sea_p66"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_usa_samoa"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (8000, 2750, 9900, 4888); evidence/ap_pacific_south.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-031 — Missing island tile: Gambier Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_gambier_islands`, `sea_p67`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Gambier Islands",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "France",
  "coastal_seas": [
    "sea_p67"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_gambier_islands"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (8000, 2750, 9900, 4888); evidence/ap_pacific_south.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-032 — Missing island tile: Pitcairn Island

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_pitcairn_island`, `sea_p68`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Pitcairn Island",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "FEC",
  "coastal_seas": [
    "sea_p68"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_pitcairn_island"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (8000, 2750, 9900, 4888); evidence/ap_pacific_south.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Great Britain versus FEC player allocation is separately uncertain in AP-094.

## AP-033 — Missing island tile: Easter Island

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_easter_island`, `sea_p68`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Easter Island",
  "terrain": "normal",
  "ipp_value": 0,
  "original_owner": "Chile",
  "coastal_seas": [
    "sea_p68"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_easter_island"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (8000, 2750, 9900, 4888); evidence/ap_pacific_south.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-034 — Missing island tile: Maluku Islands

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_maluku_islands`, `sea_p51`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Maluku Islands",
  "terrain": [
    "mountain",
    "jungle"
  ],
  "ipp_value": 0,
  "original_owner": "Netherlands",
  "coastal_seas": [
    "sea_p51",
    "sea_p52",
    "sea_p62"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_maluku_islands"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-035 — Missing island tile: Lesser Sunda Islands / West Timor

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_lesser_sunda_islands`, `sea_p63`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Lesser Sunda Islands / West Timor",
  "terrain": [
    "mountain",
    "jungle"
  ],
  "ipp_value": 1,
  "original_owner": "Netherlands",
  "coastal_seas": [
    "sea_p60",
    "sea_p61",
    "sea_p63"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_lesser_sunda_islands"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- Terrain Glossary pp2–4; ownership category follows printed roundel, with FEC allocation for UK Pacific possessions requiring setup confirmation.

**Scope / dependency:** Complete physical coastline and land/narrow neighbor set is source-traced in data/asia_pacific_new_node_neighbors.json. Use printed identity and facilities, with the full perimeter rather than the first listed coast alone.

## AP-036 — Sydney is a separate land zone, not a city inside New South Wales

**Field:** `node` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_aus_sydney`, `land_aus_new_south_wales`, `sea_p72`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "name": "Sydney",
  "terrain": "mountain",
  "ipp_value": 2,
  "original_owner": "ANZAC",
  "is_city": true,
  "is_capital": true,
  "is_victory_city": true,
  "land_neighbors": [
    "land_aus_new_south_wales"
  ],
  "sea_neighbors": [
    "sea_p72"
  ],
  "node_facilities": [
    "airfield"
  ],
  "neighbor_review": "data/asia_pacific_new_node_neighbors.json#land_aus_sydney",
  "coastal_facilities": {
    "sea_p72": [
      "minor_shipyard"
    ]
  }
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6100, 3750, 8650, 4888); evidence/ap_australia.png
- Terrain Glossary p3: Sydney mountain; map depicts separate outlined tile and red city/capital marker.

**Scope / dependency:** Sydney contains one southern P72 minor shipyard and an airfield. The northern P72 minor shipyard is in New South Wales, above the circular Sydney boundary. Complete physical neighbors are NSW and P72.

## AP-046 — Restore missing Indian/Bengal land borders

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_burma`, `land_india_benares`, `land_india_bengal`, `land_india_calcutta`, `land_india_delhi`, `land_india_maharashtra`, `land_india_punjab`, `land_india_southern_india`, `land_nepal`

**Current:**

```json
{
  "missing_pairs": [
    [
      "land_india_bengal",
      "land_india_benares"
    ],
    [
      "land_india_bengal",
      "land_india_calcutta"
    ],
    [
      "land_india_bengal",
      "land_burma"
    ],
    [
      "land_india_bengal",
      "land_nepal"
    ],
    [
      "land_india_benares",
      "land_nepal"
    ],
    [
      "land_india_benares",
      "land_india_punjab"
    ],
    [
      "land_india_benares",
      "land_india_southern_india"
    ],
    [
      "land_india_delhi",
      "land_india_southern_india"
    ],
    [
      "land_india_punjab",
      "land_india_maharashtra"
    ]
  ]
}
```

**Proposed:**

```json
{
  "reciprocal_pairs": [
    [
      "land_india_bengal",
      "land_india_benares"
    ],
    [
      "land_india_bengal",
      "land_india_calcutta"
    ],
    [
      "land_india_bengal",
      "land_burma"
    ],
    [
      "land_india_bengal",
      "land_nepal"
    ],
    [
      "land_india_benares",
      "land_nepal"
    ],
    [
      "land_india_benares",
      "land_india_punjab"
    ],
    [
      "land_india_benares",
      "land_india_southern_india"
    ],
    [
      "land_india_delhi",
      "land_india_southern_india"
    ],
    [
      "land_india_punjab",
      "land_india_maharashtra"
    ]
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (5450, 2450, 6320, 3320); evidence/ap_india_borders.png
- evidence/ap_india.png

**Scope / dependency:** Bengal was added as a China endpoint, leaving real India/Burma/Nepal borders absent. Benares–Bengal and Bengal–Burma show rail crossings; other rail booleans need line tracing. Glossary supplies directional rivers.

## AP-053 — Missing Burma–Annam-Tonkin / Siam–Annam-Tonkin borders

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_burma`, `land_annam_tonkin`, `land_siam`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "reciprocal_pairs": [
    [
      "land_burma",
      "land_annam_tonkin"
    ],
    [
      "land_siam",
      "land_annam_tonkin"
    ]
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6250, 2600, 8250, 4030); evidence/ap_se_asia.png
- Terrain Glossary p3 specifically lists these approach boundaries.

**Scope / dependency:** Apply directional mountain/river rules from glossary; both sides already have jungle/mountain terrain effects.

## AP-054 — Restore central Siberian links into isolated endpoints

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_novosibirsk`, `land_usr_eastern_kazakhstan`, `land_usr_stalino`, `land_usr_vanavara`, `land_usr_angara`, `land_usr_irkutsk`, `land_usr_turkestan`

**Current:**

Novosibirsk has only Kobdo/Tannu Tuva; Eastern Kazakhstan only Sinkiang/Kobdo; Turkestan only Sinkiang

**Proposed:**

```json
{
  "certain_existing_pairs": [
    [
      "land_usr_novosibirsk",
      "land_usr_eastern_kazakhstan"
    ],
    [
      "land_usr_novosibirsk",
      "land_usr_stalino"
    ],
    [
      "land_usr_novosibirsk",
      "land_usr_vanavara"
    ],
    [
      "land_usr_novosibirsk",
      "land_usr_angara"
    ],
    [
      "land_usr_vanavara",
      "land_usr_angara"
    ],
    [
      "land_usr_irkutsk",
      "land_usr_southern_yakutia"
    ],
    [
      "land_usr_irkutsk",
      "land_usr_yakutsk"
    ],
    [
      "land_usr_irkutsk",
      "land_usr_chita"
    ],
    [
      "land_usr_chita",
      "land_usr_yakutsk"
    ],
    [
      "land_usr_amur",
      "land_usr_magadan"
    ],
    [
      "land_usr_turkestan",
      "land_usr_eastern_kazakhstan"
    ]
  ],
  "new_node_perimeters": "data/asia_pacific_new_node_neighbors.json"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (5800, 350, 7200, 1570); evidence/ap_siberia_central.png
- evidence/ap_siberia_east.png; evidence/ap_central_asia.png

**Scope / dependency:** All new Soviet physical perimeters are separately complete in the new-node ledger. Turkestan does not border Afghanistan: Turkmenistan intervenes. Trans-Siberian railway visibly follows Novosibirsk–Angara–Buryatia–Chita–Amur–Primorsky Krai.

## AP-057 — Amur coastal access and mainland–North Sakhalin narrow crossing

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_amur`, `land_usr_north_sakhalin`, `sea_p2`

**Current:**

```json
{
  "Amur": "no sea access"
}
```

**Proposed:**

```json
{
  "coasts": [
    [
      "land_usr_amur",
      "sea_p2"
    ]
  ],
  "narrow_pair": [
    "land_usr_amur",
    "land_usr_north_sakhalin"
  ],
  "capacity": 1,
  "blocking_seas": [
    "sea_p2"
  ],
  "railway_connection": false
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- evidence/ap_sakhalin.png
- game_content/maps/gw36map.png rect (7150, 1000, 7640, 1740); evidence/ap_naval_amur_primorsky_boundary.png
- game_content/maps/gw36map.png rect (7200, 0, 8550, 1650); evidence/ap_sov_east_graph.png

**Scope / dependency:** Fresh naval review traces the Amur/Primorsky political boundary along the river to its mouth. Amur has only P2 coast. The minor shipyard and P7 coast belong to the Primorsky strip east of that boundary; corrected in AP-060. No Amur naval facility is printed.

## AP-058 — South Sakhalin western coast touches P7

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_south_sakhalin`, `sea_p7`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "reciprocal_pair": [
    "land_usr_south_sakhalin",
    "sea_p7"
  ],
  "sea_to_land_terrain": "mountain"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7270, 1320, 8170, 2100); evidence/ap_sakhalin.png

## AP-061 — Kamchatka–Kurile capacity-1 narrow crossing

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_kamchatka`, `land_jap_kurile_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "narrow_crossing": true,
  "narrow_crossings": 1,
  "railway_connection": false,
  "blocking_seas": [
    "sea_p9"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7270, 1320, 8170, 2100); evidence/ap_sakhalin.png
- game_content/maps/gw36map.png rect (7860, 1430, 8000, 1530); evidence/ap_narrow_kuriles.png

**Scope / dependency:** The white dotted crossing is east of the Kamchatka tip, wholly in P9. The west-facing P2/P8 boundary terminates on the other coast. Replace legacy land–sea narrow flags with the explicit land pair.

## AP-064 — Missing narrow land pairs at Malacca and Lesser Sunda chain

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_british_malaya`, `land_sumatra`, `land_java`, `land_lesser_sunda_islands`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "pairs": [
    {
      "nodes": [
        "land_british_malaya",
        "land_sumatra"
      ],
      "capacity": 1,
      "blocking_seas": [
        "sea_p50"
      ]
    },
    {
      "nodes": [
        "land_java",
        "land_lesser_sunda_islands"
      ],
      "capacity": 1,
      "blocking_seas": [
        "sea_p60",
        "sea_p61"
      ]
    }
  ],
  "railway_connection": false
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- evidence/ap_se_asia.png
- game_content/maps/gw36map.png rect (6500, 3350, 6740, 3510); evidence/ap_narrow_malacca.png
- game_content/maps/gw36map.png rect (6620, 3640, 7030, 3830); evidence/ap_narrow_sunda.png

**Scope / dependency:** Close native trace resolves Malacca in P50 only; the Java–Lesser Sunda dotted crossing bends across the P60/P61 boundary and touches both seas. Nearby I12/P59 are not blockers for the Malacca line.

## AP-071 — Northern Territory–Queensland ordinary border

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_aus_northern_territory`, `land_aus_queensland`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "passable": true,
  "railway_connection": false
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6100, 3750, 8650, 4888); evidence/ap_australia.png

**Scope / dependency:** Vertical border north of the Outback is finite and unobstructed. No railway into Northern Territory is printed.

## AP-075 — Missing printed Pacific island infrastructure

**Field:** `facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_jap_marshall_islands`, `land_usa_hawaii`, `land_usa_midway`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "Marshall Islands": {
    "airfield": 1,
    "P47": [
      "minor_port"
    ]
  },
  "Hawaii": {
    "airfield": 1,
    "P29": [
      "major_dockyard"
    ]
  },
  "Midway": {
    "P22": [
      "minor_port",
      "submarine_base"
    ]
  },
  "physical_instances": {
    "land_jap_marshall_islands": [
      {
        "id": "facility_marshall_minor_port",
        "type": "minor_port",
        "sea_accesses": [
          "sea_p47"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              8490,
              2820,
              8870,
              3110
            ],
            "crop": "evidence/ap_naval_marshall.png"
          }
        ],
        "notes": "Printed symbol class and its side of the political/coastal boundary independently checked in the native source."
      }
    ],
    "land_usa_hawaii": [
      {
        "id": "facility_hawaii_major_dockyard",
        "type": "major_dockyard",
        "sea_accesses": [
          "sea_p29"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              8430,
              1950,
              9200,
              2540
            ],
            "crop": "evidence/ap_naval_pacific_facilities.png"
          }
        ],
        "notes": "Blue-square circular anchor; one naval facility, plus a separately excluded airfield."
      }
    ],
    "land_usa_midway": [
      {
        "id": "facility_midway_minor_port",
        "type": "minor_port",
        "sea_accesses": [
          "sea_p22"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              8430,
              1950,
              9200,
              2540
            ],
            "crop": "evidence/ap_naval_pacific_facilities.png"
          }
        ],
        "notes": "Printed symbol class and its side of the political/coastal boundary independently checked in the native source."
      },
      {
        "id": "facility_midway_submarine_base",
        "type": "submarine_base",
        "sea_accesses": [
          "sea_p22"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              8430,
              1950,
              9200,
              2540
            ],
            "crop": "evidence/ap_naval_pacific_facilities.png"
          }
        ],
        "notes": "Blue-square vertical submarine silhouette, distinct from anchor or crane."
      }
    ]
  }
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (8490, 2820, 8870, 3110); evidence/ap_naval_marshall.png
- game_content/maps/gw36map.png rect (8430, 1950, 9200, 2540); evidence/ap_naval_pacific_facilities.png

**Scope / dependency:** Fresh native inspection confirms Hawaii circular-anchor major dockyard, Midway separate minor port and vertical-submarine base, and Marshall minor port. Airfields remain separate, non-naval facilities.

## AP-079 — Missing numbered Pacific sea zones

**Field:** `nodes` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_p4`, `sea_p19`, `sea_p20`, `sea_p21`, `sea_p22`, `sea_p23`, `sea_p27`, `sea_p29`, `sea_p37`, `sea_p38`, `sea_p39`, `sea_p40`, `sea_p48`, `sea_p49`, `sea_p55`, `sea_p56`, `sea_p57`, `sea_p58`, `sea_p66`, `sea_p67`, `sea_p70`, `sea_p71`, `sea_p72`, `sea_p73`, `sea_p74`, `sea_p75`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "sea_p4": {
    "type": "sea",
    "name": "Sea Zone P4"
  },
  "sea_p19": {
    "type": "sea",
    "name": "Sea Zone P19"
  },
  "sea_p20": {
    "type": "sea",
    "name": "Sea Zone P20"
  },
  "sea_p21": {
    "type": "sea",
    "name": "Sea Zone P21"
  },
  "sea_p22": {
    "type": "sea",
    "name": "Sea Zone P22"
  },
  "sea_p23": {
    "type": "sea",
    "name": "Sea Zone P23"
  },
  "sea_p27": {
    "type": "sea",
    "name": "Sea Zone P27"
  },
  "sea_p29": {
    "type": "sea",
    "name": "Sea Zone P29"
  },
  "sea_p37": {
    "type": "sea",
    "name": "Sea Zone P37"
  },
  "sea_p38": {
    "type": "sea",
    "name": "Sea Zone P38"
  },
  "sea_p39": {
    "type": "sea",
    "name": "Sea Zone P39"
  },
  "sea_p40": {
    "type": "sea",
    "name": "Sea Zone P40"
  },
  "sea_p48": {
    "type": "sea",
    "name": "Sea Zone P48"
  },
  "sea_p49": {
    "type": "sea",
    "name": "Sea Zone P49"
  },
  "sea_p55": {
    "type": "sea",
    "name": "Sea Zone P55"
  },
  "sea_p56": {
    "type": "sea",
    "name": "Sea Zone P56"
  },
  "sea_p57": {
    "type": "sea",
    "name": "Sea Zone P57"
  },
  "sea_p58": {
    "type": "sea",
    "name": "Sea Zone P58"
  },
  "sea_p66": {
    "type": "sea",
    "name": "Sea Zone P66"
  },
  "sea_p67": {
    "type": "sea",
    "name": "Sea Zone P67"
  },
  "sea_p70": {
    "type": "sea",
    "name": "Sea Zone P70"
  },
  "sea_p71": {
    "type": "sea",
    "name": "Sea Zone P71"
  },
  "sea_p72": {
    "type": "sea",
    "name": "Sea Zone P72"
  },
  "sea_p73": {
    "type": "sea",
    "name": "Sea Zone P73"
  },
  "sea_p74": {
    "type": "sea",
    "name": "Sea Zone P74"
  },
  "sea_p75": {
    "type": "sea",
    "name": "Sea Zone P75"
  }
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7900, 1000, 9900, 2850); evidence/ap_pacific_north.png
- evidence/ap_pacific_south.png; evidence/ap_australia.png; evidence/ap_siberia_east.png

**Scope / dependency:** Every listed number was seen on the map. This list is not generated by assuming all numbers must exist. P76–P78 belong to the Americas audit.

## AP-087 — Reconnect Wake/P36 to the six visible surrounding seas

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_p36`, `sea_p26`, `sea_p27`, `sea_p35`, `sea_p37`, `sea_p45`, `sea_p47`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_p26",
  "sea_p27",
  "sea_p35",
  "sea_p37",
  "sea_p45",
  "sea_p47"
]
```

**Evidence:**

- evidence/ap_pacific_grid.png source rect (7970,1500,8980,3000)

**Scope / dependency:** P36 currently has only Wake as neighbor, making a disconnected two-node component. P26 contact at northwestern edge and P47 contact at southeastern edge are short but finite; native crop resolves both. Add reciprocal sea edges.

## AP-088 — Restore P18/P19/P20/P21/P26/P27 Pacific grid boundaries

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_p18`, `sea_p19`, `sea_p20`, `sea_p21`, `sea_p26`, `sea_p27`

**Current:**

Partial endpoint nodes or absent nodes

**Proposed:**

```json
{
  "sea_p18": [
    "sea_p16",
    "sea_p17",
    "sea_p20",
    "sea_p26",
    "sea_p27"
  ],
  "sea_p19": [
    "sea_p10",
    "sea_p11",
    "sea_p17",
    "sea_p20",
    "sea_p21",
    "sea_p22"
  ],
  "sea_p20": [
    "sea_p17",
    "sea_p18",
    "sea_p19",
    "sea_p22",
    "sea_p27"
  ],
  "sea_p21": [
    "sea_p11",
    "sea_p19",
    "sea_p22",
    "sea_p23"
  ],
  "sea_p26": [
    "sea_p16",
    "sea_p18",
    "sea_p27",
    "sea_p35",
    "sea_p36"
  ],
  "sea_p27": [
    "sea_p18",
    "sea_p20",
    "sea_p22",
    "sea_p26",
    "sea_p28",
    "sea_p36",
    "sea_p37"
  ]
}
```

**Evidence:**

- evidence/ap_pacific_grid.png source rect (7970,1500,8980,3000); evidence/ap_pacific_north.png

**Scope / dependency:** Native crop resolves offset junctions: P27–P37 is a short finite border because P28/P37 horizontal split is north of P27/P36 split. Reciprocal additions required.

## AP-090 — Kamchatka and P3 are missing real Bering coasts and sea borders

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_kamchatka`, `sea_p1`, `sea_p3`, `sea_p4`, `sea_p9`, `sea_p10`

**Current:**

```json
{
  "Kamchatka_seas": [
    "sea_p2",
    "sea_p9"
  ],
  "P3_seas": [
    "sea_p9"
  ]
}
```

**Proposed:**

```json
{
  "Kamchatka_seas": [
    "sea_p1",
    "sea_p2",
    "sea_p3",
    "sea_p9"
  ],
  "P3_seas": [
    "sea_p1",
    "sea_p4",
    "sea_p9",
    "sea_p10"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7550,430,8680,1350); evidence/ap_bering.png

**Scope / dependency:** Kamchatka includes the northeastern mainland coast south of the Chukotka border. Its northern tip extends above the P1/P3 horizontal line. P3 has short southern contact with P9 and longer contact with P10. No rail follows any of these coasts.

## AP-097 — Restore Siam west coast and complete Sumatra coastal perimeter

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_siam`, `land_sumatra`, `sea_i11`, `sea_i12`, `sea_i13`, `sea_p50`, `sea_p59`

**Current:**

Siam I11 omitted; Sumatra coast perimeter incomplete

**Proposed:**

```json
{
  "Siam": [
    "sea_i11",
    "sea_p50"
  ],
  "Sumatra": [
    "sea_i12",
    "sea_i13",
    "sea_p50",
    "sea_p59"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6410, 3030, 6780, 3430); evidence/ap_malaya_coast.png
- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- game_content/maps/gw36map.png rect (6060, 3480, 7530, 4410); evidence/ap_java_indian_grid.png

**Scope / dependency:** The I11/I12 line reaches Siam west of the isthmus north of the Malaya border. Malaya itself has I12/P50, without I11. Sumatra southwest is I13 below the I12/I13 line.
