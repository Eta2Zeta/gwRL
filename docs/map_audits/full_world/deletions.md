# Deletions — complete finding register

**Implementation, 7 October:** approved work has been applied; uncertainties remain deferred. See [implementation status](implementation.md). The before/after proposals below retain the checkpoint baseline.

94 finding records. Group findings may contain multiple fields or nodes; these are not edit counts.

Historical proposals. Apply neither uncertain values nor incomplete new-node records automatically. Each confidence rating applies only to the described fields. Regional reports explain dependencies and unresolved source coverage.

See [overview](README.md), [mechanism proposals](mechanisms_and_schema.md), and [machine-readable register](data/all_findings.json).

**Naval facilities were rechecked on 6 October 2026.** Start with the [corrected current-to-proposed facility roster](naval_facility_reaudit.md) for ports, dockyards, shipyards and naval bases. Earlier conditional port-ID renaming examples must not be applied as a list of real facilities.

## WG-039 — Remove South Sakhalin from USSR Home Country

**Field:** `nations.USSR.home_country_land_zone_ids` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_usr_south_sakhalin`

**Current:**

land_usr_south_sakhalin is included

**Proposed:**

```json
{
  "remove_land_zone_ids": [
    "land_usr_south_sakhalin"
  ]
}
```

**Evidence:**

- game_content/rules/Global War 1936 v4.3 Rulebook.pdf p6
- game_content/maps/gw36_nation_home_country.json
- tools/build_nation_home_country_json.py
- game_content/maps/gw36map.png

**Scope / dependency:** AP-041 confirms the Japanese printed roundel. USSR Home Country follows Soviet original roundels, not current possession or the historical-looking node prefix. Japan Home Country is the explicit four-zone list, so do not automatically add South Sakhalin there.

## AM-034 — Remove unsupported direct land route

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_chicago`, `land_usa_new_york`

**Current:**

```json
{
  "land_usa_chicago": {
    "neighbor_id": "land_usa_new_york",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "land_usa_new_york": {
    "neighbor_id": "land_usa_chicago",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Great Lakes/The Northeast and other tiles intervene; railroad reachability is not direct adjacency.

## AM-035 — Remove unsupported direct land route

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_chicago`, `land_usa_san_francisco`

**Current:**

```json
{
  "land_usa_chicago": {
    "neighbor_id": "land_usa_san_francisco",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "land_usa_san_francisco": {
    "neighbor_id": "land_usa_chicago",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Multiple western and central US tiles intervene.

## AM-036 — Remove unsupported direct land route

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_york`, `land_usa_washington_dc`

**Current:**

```json
{
  "land_usa_new_york": {
    "neighbor_id": "land_usa_washington_dc",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "land_usa_washington_dc": {
    "neighbor_id": "land_usa_new_york",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [480, 1580, 980, 2140], "crop": "docs/map_audits/full_world/evidence/americas_usa_dc_coast.png"}

**Scope / dependency:** The Northeast separates the two circular city zones; the printed railway crosses that intervening tile.

## AM-037 — Remove unsupported direct land route

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_upper_midwest`, `land_usa_great_lakes`

**Current:**

```json
{
  "land_usa_upper_midwest": {
    "neighbor_id": "land_usa_great_lakes",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "land_usa_great_lakes": {
    "neighbor_id": "land_usa_upper_midwest",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Midwest lies between Upper Midwest at the seam and the Great Lakes tile.

## AM-038 — Remove unsupported direct land route

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_cuba`, `land_hispaniola`

**Current:**

```json
{
  "land_cuba": {
    "neighbor_id": "land_hispaniola",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "land_hispaniola": {
    "neighbor_id": "land_cuba",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Open water separates Cuba and Haiti; no printed narrow-crossing line or railroad.

## AM-039 — Remove unsupported direct land route

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_paraguay`, `land_buenos_aires`

**Current:**

```json
{
  "land_paraguay": {
    "neighbor_id": "land_buenos_aires",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": true,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "land_buenos_aires": {
    "neighbor_id": "land_paraguay",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** Norte Grande and Uruguay separate Paraguay from the Buenos Aires city zone.

## AM-040 — Remove unsupported direct land route

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_colombia`, `land_peru`

**Current:**

```json
{
  "land_colombia": {
    "neighbor_id": "land_peru",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "land_peru": {
    "neighbor_id": "land_colombia",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [280, 2900, 930, 3550], "crop": "docs/map_audits/full_world/evidence/americas_andes_amazon_detail.png"}

**Scope / dependency:** Ecuador and the hatched impassable Amazon area separate the roundel-bearing zones; no ordinary passable shared border.

## AM-084 — Replace artificial Hispaniola node with the two printed territories

**Field:** `node` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_hispaniola`

**Current:**

```json
{
  "id": "land_hispaniola",
  "name": "Hispaniola",
  "type": "land",
  "terrain": "normal",
  "ipp_value": 1,
  "original_owner": "Hispaniola",
  "current_owner": "Hispaniola",
  "is_city": false,
  "is_capital": false,
  "is_victory_city": false,
  "node_facilities": [],
  "node_facility_ids": [],
  "neighbors": [
    {
      "neighbor_id": "land_cuba",
      "border_terrain": "normal",
      "passable": true,
      "has_river": false,
      "river_crossing": false,
      "railway_connection": true,
      "gauge_change": false,
      "naval_facilities": [],
      "naval_facility_ids": [],
      "port_or_dock_connection": false,
      "canal_or_strait": null,
      "narrow_crossing": false,
      "narrow_crossings": 0,
      "special_fortification": null
    },
    {
      "neighbor_id": "sea_a36",
      "border_terrain": "coast",
      "passable": true,
      "has_river": false,
      "river_crossing": false,
      "railway_connection": false,
      "gauge_change": false,
      "naval_facilities": [
        "minor_port"
      ],
      "naval_facility_ids": [
        "facility_land_hispaniola_minor_port"
      ],
      "port_or_dock_connection": true,
      "canal_or_strait": null,
      "narrow_crossing": false,
      "narrow_crossings": 0,
      "special_fortification": null
    }
  ]
}
```

**Proposed:**

```json
{
  "replace_with": [
    "land_haiti",
    "land_dominican_republic"
  ],
  "preserve_migration_alias_if_needed": true
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Map labels separate Haiti and Dominican Republic with different roundels and a land border; neither has a red IPP value. Do not retain a third island-wide territory. Naval re-audit 2026-10-06 explicitly retires the aggregate facility claim: both replacement territories, Haiti and Dominican Republic, were independently scanned and have no printed naval glyph.

## AM-155 — Remove unsupported naval facility: Suriname

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_suriname`, `sea_a41`

**Current:**

```json
[
  {
    "sea_id": "sea_a38",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_suriname_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [],
  "naval_facility_ids": [],
  "physical_facilities": [],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}

**Scope / dependency:** Fresh 2026-10-06 full-coast check finds no printed naval symbol in this territory. Remove all listed current facility claims/IDs, including those on the old wrong sea edge. Coast adjacency itself is handled separately.

## AM-159 — Remove unsupported naval facility: Bermuda

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_bermuda`, `sea_a31`

**Current:**

```json
[
  {
    "sea_id": "sea_a31",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_bermuda_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [],
  "naval_facility_ids": [],
  "physical_facilities": [],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}

**Scope / dependency:** Fresh 2026-10-06 full-coast check finds no printed naval symbol in this territory. Remove all listed current facility claims/IDs, including those on the old wrong sea edge. Coast adjacency itself is handled separately.

## AM-162 — Remove unsupported naval facility: Pampas

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_pampas`, `sea_a47`

**Current:**

```json
[
  {
    "sea_id": "sea_a39",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_pampas_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [],
  "naval_facility_ids": [],
  "physical_facilities": [],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_north.png", "rectangle": [0, 2750, 1500, 3880]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}

**Scope / dependency:** Fresh 2026-10-06 full-coast check finds no printed naval symbol in this territory. Remove all listed current facility claims/IDs, including those on the old wrong sea edge. Coast adjacency itself is handled separately.

## AM-204 — Remove non-neighbor Atlantic shortcut

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a31`, `sea_a36`

**Current:**

```json
{
  "sea_a31": {
    "neighbor_id": "sea_a36",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "sea_a36": {
    "neighbor_id": "sea_a31",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.

## AM-205 — Remove non-neighbor Atlantic shortcut

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a33`, `sea_a36`

**Current:**

```json
{
  "sea_a33": {
    "neighbor_id": "sea_a36",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "sea_a36": {
    "neighbor_id": "sea_a33",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.

## AM-206 — Remove non-neighbor Atlantic shortcut

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a35`, `sea_a38`

**Current:**

```json
{
  "sea_a35": {
    "neighbor_id": "sea_a38",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "sea_a38": {
    "neighbor_id": "sea_a35",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.

## AM-207 — Remove non-neighbor Atlantic shortcut

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a39`, `sea_a40`

**Current:**

```json
{
  "sea_a39": {
    "neighbor_id": "sea_a40",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "sea_a40": {
    "neighbor_id": "sea_a39",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.

## AM-208 — Remove non-neighbor Atlantic shortcut

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a21`, `sea_a23`

**Current:**

```json
{
  "sea_a21": {
    "neighbor_id": "sea_a23",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "sea_a23": {
    "neighbor_id": "sea_a21",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.

## AM-209 — Remove non-neighbor Atlantic shortcut

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a22`, `sea_a28`

**Current:**

```json
{
  "sea_a22": {
    "neighbor_id": "sea_a28",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "sea_a28": {
    "neighbor_id": "sea_a22",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1300, 0, 2700, 2070], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_north.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.

## AM-236 — Remove Appalachia–The Northeast shortcut

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_appalachia`, `land_usa_the_northeast`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_usa_the_northeast",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_usa_appalachia",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_interior_detail.png", "rectangle": [180, 1450, 850, 2070]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_dc_ne_boundaries.png", "rectangle": [500, 1620, 850, 1900]}

**Scope / dependency:** Great Lakes occupies the finite strip between Appalachia and The Northeast; both separately meet Washington. The printed route passes through Great Lakes.

## AM-237 — Remove Southwest US–Texas shortcut

**Field:** `neighbors reciprocal entries` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_southwest_united_states`, `land_usa_texas`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_usa_texas",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_usa_southwest_united_states",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
null
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_southwest_junction.png", "rectangle": [9550, 1720, 9900, 2140]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_us_seam_full_detail.png", "source_rectangles": [[9650, 1260, 9900, 2240], [0, 1260, 310, 2240]], "scale": 2}

**Scope / dependency:** Great Plains forms a continuous strip between Southwest US and the eastern map cut. Southwest US does not reach Texas across the seam.

## AM-244 — Remove Western Mexico phantom minor-port claim

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_mex_western_mexico`

**Current:**

```json
[
  {
    "sea_id": "sea_p30",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_western_mexico_minor_port"
    ]
  },
  {
    "sea_id": "sea_p31",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_western_mexico_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [],
  "physical_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_mexico_seam.png", "rectangle": [9680, 2110, 9900, 2500]}

**Scope / dependency:** Fresh full Western Mexico coast inspection shows no anchor, crane, dockyard, seaplane or submarine-base glyph. The current same-ID entries on P30/P31 are one unsupported physical claim. Prior AM-108 coast migration did not explicitly remove it; this omission is now corrected.

## EA-172 — Eastern Germany ↔ Konigsberg: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_eastern_germany`, `land_ger_konigsberg`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_ger_konigsberg",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_ger_eastern_germany",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** West Poland lies between them; a railway passing through a third land zone cannot be a direct edge.

## EA-173 — West Poland ↔ Bohemia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_west_poland`, `land_cze_bohemia`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_cze_bohemia",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_pol_west_poland",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** Eastern Germany and Dolnoslaske separate the zones; no shared land boundary.

## EA-174 — Warsaw ↔ Podlachia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_warsaw`, `land_pol_podlachia`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_pol_podlachia",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_pol_warsaw",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** Lubelskie/West Poland lie between Podlachia and the circular Warsaw zone.

## EA-175 — Southern Norway ↔ Denmark: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_southern_norway`, `land_denmark`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_denmark",
    "border_terrain": "coast",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": true,
    "narrow_crossings": 1,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_nor_southern_norway",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": true,
    "narrow_crossings": 1,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** No printed narrow crossing between Norway and Denmark; ordinary open water is not a land edge.

## EA-176 — Norrland ↔ Southern Finland: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_swe_norrland`, `land_fin_southern_finland`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_fin_southern_finland",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_swe_norrland",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** The Gulf of Bothnia separates these zones; the rail route goes through Lapland.

## EA-177 — Southern Iraq ↔ Transjordan: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southern_iraq`, `land_transjordan`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_transjordan",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_southern_iraq",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Northern Iraq and Saudi Arabia separate Southern Iraq from Transjordan.

## EA-178 — Saudi Arabia ↔ Oman: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_saudi_arabia`, `land_oman`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_oman",
    "border_terrain": "desert",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_saudi_arabia",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Aden separates Saudi Arabia from Oman.

## EA-179 — Qatar ↔ Oman: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_qatar`, `land_oman`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_oman",
    "border_terrain": "desert",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_qatar",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Aden separates Qatar from Oman.

## EA-180 — Northern Iraq ↔ Northern Iran: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_iraq`, `land_iran_northern_iran`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_iran_northern_iran",
    "border_terrain": "mountain",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_northern_iraq",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Azerbaijan separates Northern Iraq from Northern Iran.

## EA-244 — North Western Mediterranean ↔ Strait of Gibraltar (Atlantic): adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m1`, `sea_a44`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_a44",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": "Strait of Gibraltar",
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_m1",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": "Strait of Gibraltar",
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report.

## EA-245 — Tyrrhenian Sea ↔ Adriatic Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m3`, `sea_m5`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_m5",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_m3",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report.

## EA-246 — Central Mediterranean Sea ↔ Adriatic Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m4`, `sea_m5`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_m5",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_m4",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report.

## EA-247 — Adriatic Sea ↔ Western Black Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m5`, `sea_m10`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_m10",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_m5",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report.

## EA-248 — Eastern Mediterranean ↔ Red Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m9`, `sea_i3`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_i3",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_m9",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report.

## EA-249 — Eastern Mediterranean ↔ Red Sea South: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m9`, `sea_i5`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_i5",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": "Suez Canal",
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_m9",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": "Suez Canal",
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report.

## EA-250 — Eastern Mediterranean ↔ Western Black Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m9`, `sea_m10`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_m10",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_m9",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report.

## EA-251 — Eastern Black Sea ↔ Caspian Sea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_m11`, `sea_m12`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_m12",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_m11",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report.

## EA-300 — Corsica: remove unsupported naval facility claims

**Field:** `unsupported_naval_facility_claims` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_corsica`, `sea_m1`

**Current:**

```json
[
  {
    "sea_id": "sea_m3",
    "types": [
      "minor_port"
    ],
    "ids": [
      "facility_corsica_minor_port"
    ]
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-301 — Corsica / M3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_corsica`, `sea_m3`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-302 — Sardinia: remove unsupported naval facility claims

**Field:** `unsupported_naval_facility_claims` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_sardinia`, `sea_m1`

**Current:**

```json
[
  {
    "sea_id": "sea_m3",
    "types": [
      "minor_port"
    ],
    "ids": [
      "facility_sardinia_minor_port"
    ]
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-303 — Sardinia / M3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_sardinia`, `sea_m3`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-322 — Qatar: remove unsupported naval facility claims

**Field:** `unsupported_naval_facility_claims` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_qatar`, `sea_i6`

**Current:**

```json
[
  {
    "sea_id": "sea_i7",
    "types": [
      "minor_port"
    ],
    "ids": [
      "facility_land_qatar_minor_port"
    ]
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-323 — Oman / I6: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_oman`, `sea_i6`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-331 — Upper Egypt / I5: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_upper_egypt`, `sea_i5`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. No naval facility printed on its I5 shore; the major anchor at the northern end belongs to Lower Egypt. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-335 — Italian Somaliland / I4: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_italian_somaliland`, `sea_i4`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-337 — Portuguese East Africa: remove unsupported naval facility claims

**Field:** `unsupported_naval_facility_claims` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_portuguese_east_africa`, `sea_i1`

**Current:**

```json
[
  {
    "sea_id": "sea_i4",
    "types": [
      "minor_port"
    ],
    "ids": [
      "facility_east_africa_minor_port"
    ]
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-367 — Istanbul ↔ Ankara: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_istanbul`, `land_tur_ankara`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "land_tur_ankara",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "land_tur_istanbul",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": true,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Akdeniz and Karadeniz lie between these two roundel zones; printed railway crosses them rather than connecting Istanbul directly to Ankara.

## EA-387 — Red Sea ↔ Red Sea South: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i3`, `sea_i5`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_i5",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_i3",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** The printed zones are separated by I4; prior descriptive sea names misplaced I3 into the Red Sea.

## EA-388 — Red Sea ↔ Strait of Hormuz: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i3`, `sea_i6`

**Current:**

```json
{
  "forward": {
    "neighbor_id": "sea_i6",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "reverse": {
    "neighbor_id": "sea_i3",
    "border_terrain": "normal",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": null,
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** The printed zones are separated by I4; prior descriptive sea names misplaced I3 into the Red Sea.

## EA-414 — Trondelag: remove unsupported naval facility claims

**Field:** `unsupported_naval_facility_claims` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_trondelag`, `sea_a5`

**Current:**

```json
[
  {
    "sea_id": "sea_a6",
    "types": [
      "minor_port"
    ],
    "ids": [
      "facility_trondelag_minor_port"
    ]
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_norway_finland_20261006.png", "rectangle": [2890, 0, 4520, 690]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-429 — Northern Italy ↔ Lazio: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_northern_italy`, `land_ita_lazio`

**Current:**

```json
{
  "neighbor_id": "land_ita_lazio",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_italy_balkans.png", "rectangle": [2790, 1710, 3940, 2620]}

**Scope / dependency:** Rome occupies the full width of the peninsula between these zones.

## EA-430 — Rome ↔ Southern Italy: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rome`, `land_ita_southern_italy`

**Current:**

```json
{
  "neighbor_id": "land_ita_southern_italy",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_italy_balkans.png", "rectangle": [2790, 1710, 3940, 2620]}

**Scope / dependency:** Lazio separates the Rome circle from Southern Italy.

## EA-431 — Alsace-Lorraine ↔ Western Germany: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_alsace_lorraine`, `land_ger_western_germany`

**Current:**

```json
{
  "neighbor_id": "land_ger_western_germany",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": true,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_france_germany.png", "rectangle": [2520, 1100, 3420, 1900]}

**Scope / dependency:** Bavaria and Picardy separate the printed boundaries.

## EA-432 — Sudan ↔ Eritrea: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sudan`, `land_eritrea`

**Current:**

```json
{
  "neighbor_id": "land_eritrea",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Nubia lies between these zones; Eritrea borders Nubia and Abyssinia.

## EA-433 — Tunisia ↔ Tripoli: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tunisia`, `land_tripoli`

**Current:**

```json
{
  "neighbor_id": "land_tripoli",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sahara.png", "rectangle": [1730, 2990, 3940, 3890]}

**Scope / dependency:** The Tripoli city circle is wholly within the Tripolitania shore and never reaches Tunisia.

## EA-434 — Baltic Sea ↔ English Channel: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a12`, `sea_a23`

**Current:**

```json
{
  "neighbor_id": "sea_a23",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": false,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": "Kaiser-Wilhelm Kanal",
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_north_seas.png", "rectangle": [2100, 0, 4570, 1550]}

**Scope / dependency:** The printed canal joins A11 and A12. A11 lies between A23 and A12.

## EA-435 — Kola ↔ Northern Russia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kola`, `land_usr_northern_russia`

**Current:**

```json
{
  "neighbor_id": "land_usr_northern_russia",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_north.png", "rectangle": [3775, 350, 5230, 1600]}

**Scope / dependency:** White Sea water separates these shores; the only southern Kola land connection is Karelia.

## EA-436 — Northern Russia ↔ Western Russia: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_northern_russia`, `land_usr_western_russia`

**Current:**

```json
{
  "neighbor_id": "land_usr_western_russia",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_north.png", "rectangle": [3775, 350, 5230, 1600]}

**Scope / dependency:** Karelia and Yaroslavl intervene; this is a four-region point, not a shared positive-length boundary.

## EA-437 — Moscow ↔ Smolensk: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_moscow`, `land_usr_smolensk`

**Current:**

```json
{
  "neighbor_id": "land_usr_smolensk",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_north.png", "rectangle": [3775, 350, 5230, 1600]}

**Scope / dependency:** Kaluga Oblast separates the two city circles.

## EA-438 — Kiev ↔ Taurida: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kiev`, `land_usr_taurida`

**Current:**

```json
{
  "neighbor_id": "land_usr_taurida",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": true,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Southern Ukraine and Eastern Ukraine separate these zones.

## EA-439 — Crimea ↔ Southern Ukraine: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_crimea`, `land_usr_southern_ukraine`

**Current:**

```json
{
  "neighbor_id": "land_usr_southern_ukraine",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Taurida owns the entire land approach to the Crimean isthmus.

## EA-440 — Kalmytskaya ↔ Saratov: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kalmytskaya`, `land_usr_saratov`

**Current:**

```json
{
  "neighbor_id": "land_usr_saratov",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Stalingrad and intervening zones separate these territories.

## EA-441 — North-Caucasia ↔ Stalingrad: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_north_caucasia`, `land_usr_stalingrad`

**Current:**

```json
{
  "neighbor_id": "land_usr_stalingrad",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Kalmytskaya lies between the Stalingrad circle and North-Caucasia.

## EA-442 — Gorky ↔ Tula-Lipetsk: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_gorky`, `land_usr_tula_lipetsk`

**Current:**

```json
{
  "neighbor_id": "land_usr_tula_lipetsk",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_north.png", "rectangle": [3775, 350, 5230, 1600]}

**Scope / dependency:** Saratov extends to the Moscow circle and separates Gorky from Tula-Lipetsk.

## EA-547 — Bavaria ↔ Eastern Germany: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_bavaria`, `land_ger_eastern_germany`

**Current:**

```json
{
  "neighbor_id": "land_ger_eastern_germany",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_france_germany.png", "rectangle": [2520, 1100, 3420, 1900]}

**Scope / dependency:** Berlin and Bohemia separate the named territories. Bavaria meets Berlin at the southern circle arc; Eastern Germany is on the far side of Berlin.

## EA-548 — West Poland ↔ Lithuania: adjacency

**Field:** `adjacency` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_west_poland`, `land_lithuania`

**Current:**

```json
{
  "neighbor_id": "land_lithuania",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": null,
  "narrow_crossing": false,
  "narrow_crossings": 0,
  "special_fortification": null
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_poland.png", "rectangle": [3210, 850, 4170, 1780]}

**Scope / dependency:** Konigsberg and Podlachia intervene. West Poland reaches Podlachia at the Konigsberg southeast junction, not Lithuania.

## EA-571 — Corsica: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_corsica`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_corsica_minor_port",
    "sea_id": "sea_m3"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-572 — Sardinia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_sardinia`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_sardinia_minor_port",
    "sea_id": "sea_m3"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-582 — Trondelag: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_trondelag`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_trondelag_minor_port",
    "sea_id": "sea_a6"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_norway_finland_20261006.png", "rectangle": [2890, 0, 4520, 690]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-592 — Basque Country: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_basque_country`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_basque_country_minor_port",
    "sea_id": "sea_a28"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-606 — Macedonia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_macedonia`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_macedonia_minor_port",
    "sea_id": "sea_m5"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-613 — Bessarabia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rom_bessarabia`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_bessarabia_minor_port",
    "sea_id": "sea_m10"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-626 — Southern Iraq: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southern_iraq`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_iraq_minor_port",
    "sea_id": "sea_i7"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-628 — Qatar: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_qatar`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_qatar_minor_port",
    "sea_id": "sea_i7"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-629 — Oman: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_oman`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_oman_minor_port",
    "sea_id": "sea_i6"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-633 — Upper Egypt: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_upper_egypt`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_egypt_minor_port",
    "sea_id": "sea_i5"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** No naval facility printed on its I5 shore; the major anchor at the northern end belongs to Lower Egypt. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-641 — French Morocco: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_morocco`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_morocco_minor_port",
    "sea_id": "sea_a28"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_north_africa_west_detail.png", "rectangle": [1730, 2890, 3030, 3850]}

**Scope / dependency:** No printed naval facility. The user explicitly corrected this phantom-port claim; remove it, not rename it. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-650 — Angola: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_angola`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_angola_minor_port",
    "sea_id": "sea_a39"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** No printed naval facility anywhere on the inspected Atlantic coast; a railway reaching the coast is not a port symbol. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-651 — Southwest Africa: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southwest_africa`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_africa_minor_port",
    "sea_id": "sea_a39"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** No printed naval facility on either Atlantic coast. User correction preserved; the South Africa blue anchor is a different territory and physical symbol. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-654 — Portuguese East Africa: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_portuguese_east_africa`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_east_africa_minor_port",
    "sea_id": "sea_i4"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## AP-047 — Remove four nonexistent Indian land shortcuts

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_burma`, `land_india_benares`, `land_india_calcutta`, `land_india_maharashtra`, `land_kashmir`, `land_nepal`

**Current:**

```json
{
  "pairs": [
    [
      "land_india_benares",
      "land_burma"
    ],
    [
      "land_india_calcutta",
      "land_burma"
    ],
    [
      "land_india_benares",
      "land_india_maharashtra"
    ],
    [
      "land_kashmir",
      "land_nepal"
    ]
  ]
}
```

**Proposed:**

```json
{
  "remove_pairs": [
    [
      "land_india_benares",
      "land_burma"
    ],
    [
      "land_india_calcutta",
      "land_burma"
    ],
    [
      "land_india_benares",
      "land_india_maharashtra"
    ],
    [
      "land_kashmir",
      "land_nepal"
    ]
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (5450, 2450, 6320, 3320); evidence/ap_india_borders.png
- evidence/ap_india.png
- game_content/maps/gw36map.png rect (5740, 2300, 6320, 2800); evidence/ap_nepal_kashmir.png

**Scope / dependency:** Native junction review resolves all four: Bengal intervenes between Burma and Benares/Calcutta; Delhi/Southern India intervene between Benares and Maharashtra; a finite Punjab strip reaches the Himalayas between Kashmir and Nepal.

## AP-048 — Remove rail service fabricated in Afghanistan/Kashmir/Nepal

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_afghanistan`, `land_india_punjab`, `land_iran_northern_iran`, `land_iran_southern_iran`, `land_kashmir`, `land_nepal`

**Current:**

```json
{
  "true_pairs": [
    [
      "land_afghanistan",
      "land_india_punjab"
    ],
    [
      "land_afghanistan",
      "land_iran_northern_iran"
    ],
    [
      "land_afghanistan",
      "land_iran_southern_iran"
    ],
    [
      "land_afghanistan",
      "land_kashmir"
    ],
    [
      "land_india_punjab",
      "land_kashmir"
    ],
    [
      "land_kashmir",
      "land_nepal"
    ]
  ]
}
```

**Proposed:**

```json
{
  "false_pairs": [
    [
      "land_afghanistan",
      "land_india_punjab"
    ],
    [
      "land_afghanistan",
      "land_iran_northern_iran"
    ],
    [
      "land_afghanistan",
      "land_iran_southern_iran"
    ],
    [
      "land_afghanistan",
      "land_kashmir"
    ],
    [
      "land_india_punjab",
      "land_kashmir"
    ],
    [
      "land_kashmir",
      "land_nepal"
    ]
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png

**Scope / dependency:** Rail visible in Southern Iran ends before the Punjab frontier, and no tracks enter Afghanistan, Kashmir or Nepal. Removing railway flags is distinct from removing legitimate political borders.

## AP-055 — Remove invented rail network north of the Trans-Siberian route

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_amur`, `land_usr_angara`, `land_usr_buryatia`, `land_usr_irkutsk`, `land_usr_kamchatka`, `land_usr_magadan`, `land_usr_north_sakhalin`, `land_usr_south_sakhalin`, `land_usr_southern_yakutia`, `land_usr_stalino`, `land_usr_vanavara`, `land_usr_yakutsk`

**Current:**

```json
{
  "true_pairs": [
    [
      "land_usr_stalino",
      "land_usr_vanavara"
    ],
    [
      "land_usr_vanavara",
      "land_usr_irkutsk"
    ],
    [
      "land_usr_irkutsk",
      "land_usr_angara"
    ],
    [
      "land_usr_irkutsk",
      "land_usr_buryatia"
    ],
    [
      "land_usr_amur",
      "land_usr_yakutsk"
    ],
    [
      "land_usr_yakutsk",
      "land_usr_magadan"
    ],
    [
      "land_usr_yakutsk",
      "land_usr_southern_yakutia"
    ],
    [
      "land_usr_magadan",
      "land_usr_kamchatka"
    ],
    [
      "land_usr_north_sakhalin",
      "land_usr_south_sakhalin"
    ]
  ]
}
```

**Proposed:**

```json
{
  "false_pairs": [
    [
      "land_usr_stalino",
      "land_usr_vanavara"
    ],
    [
      "land_usr_vanavara",
      "land_usr_irkutsk"
    ],
    [
      "land_usr_irkutsk",
      "land_usr_angara"
    ],
    [
      "land_usr_irkutsk",
      "land_usr_buryatia"
    ],
    [
      "land_usr_amur",
      "land_usr_yakutsk"
    ],
    [
      "land_usr_yakutsk",
      "land_usr_magadan"
    ],
    [
      "land_usr_yakutsk",
      "land_usr_southern_yakutia"
    ],
    [
      "land_usr_magadan",
      "land_usr_kamchatka"
    ],
    [
      "land_usr_north_sakhalin",
      "land_usr_south_sakhalin"
    ]
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- evidence/ap_siberia_central.png; evidence/ap_sakhalin.png

**Scope / dependency:** No track symbols cross these borders. Northern graph adjacency does not imply a railway.

## AP-056 — Remove long-distance Soviet adjacency shortcuts

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_angara`, `land_usr_buryatia`, `land_usr_chita`, `land_usr_primorsky_krai`

**Current:**

```json
{
  "pairs": [
    [
      "land_usr_angara",
      "land_usr_chita"
    ],
    [
      "land_usr_buryatia",
      "land_usr_primorsky_krai"
    ]
  ]
}
```

**Proposed:**

```json
null
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png

**Scope / dependency:** Buryatia lies between Angara and Chita; Chita/Amur lie between Buryatia and Primorsky Krai. These are not adjacent borders or rail shortcuts.

## AP-059 — South Sakhalin has no printed minor port

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_south_sakhalin`, `sea_p8`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- game_content/maps/gw36map.png rect (7270, 1320, 8170, 2100); evidence/ap_sakhalin.png

**Scope / dependency:** Fresh coast scan confirms no South Sakhalin naval facility. The nearby mainland minor shipyard belongs to Primorsky Krai, not Amur; the island strategic-objective emblem is not a port.

## AP-062 — Remove fabricated inter-island land/rail links

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_aus_new_south_wales`, `land_aus_northern_territory`, `land_aus_tasmania`, `land_borneo`, `land_celebes`, `land_java`, `land_new_britain`, `land_new_guinea`, `land_timor`

**Current:**

```json
{
  "pairs": [
    [
      "land_borneo",
      "land_java"
    ],
    [
      "land_borneo",
      "land_celebes"
    ],
    [
      "land_timor",
      "land_aus_northern_territory"
    ],
    [
      "land_new_guinea",
      "land_new_britain"
    ],
    [
      "land_aus_new_south_wales",
      "land_aus_tasmania"
    ]
  ]
}
```

**Proposed:**

```json
null
```

**Evidence:**

- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- evidence/ap_australia.png

**Scope / dependency:** These pairs have neither an ordinary land border nor a printed narrow-crossing line. All currently carry railway_connection:true.

## AP-072 — Clear invented Australian/Papuan rail connections

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_aus_northern_territory`, `land_aus_western_australia`, `land_dutch_new_guinea`, `land_new_guinea`

**Current:**

```json
{
  "pairs": [
    [
      "land_aus_northern_territory",
      "land_aus_western_australia"
    ],
    [
      "land_dutch_new_guinea",
      "land_new_guinea"
    ]
  ]
}
```

**Proposed:**

```json
false
```

**Evidence:**

- game_content/maps/gw36map.png rect (6100, 3750, 8650, 4888); evidence/ap_australia.png
- evidence/ap_indonesia.png

## AP-074 — Remove unsupported Pacific island ports

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_fiji`, `land_new_hebrides`, `land_usa_wake_island`, `land_aus_tasmania`, `land_nz_south_island`

**Current:**

minor_port on each

**Proposed:**

```json
[]
```

**Evidence:**

- game_content/maps/gw36map.png rect (8000, 2750, 9900, 4888); evidence/ap_pacific_south.png
- evidence/ap_pacific_north.png; evidence/ap_australia.png

**Scope / dependency:** No port facility symbols on these island outlines. Ownership and victory markers must not be treated as infrastructure.

## AP-077 — Remove I6 long-range adjacency to Western Australia/Ceylon

**Field:** `neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_i6`, `land_aus_western_australia`, `land_india_ceylon`

**Current:**

I6 reaches Australia and Ceylon

**Proposed:**

```json
null
```

**Evidence:**

- game_content/maps/gw36map.png rect (4200, 2950, 6350, 4888); evidence/ap_indian_ocean.png
- evidence/ap_australia.png

**Scope / dependency:** I6 is the northern Arabian Sea/Persian Gulf polygon. These edges bypass several sea zones.

## AP-081 — Remove seven confirmed Pacific sea shortcuts

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_p11`, `sea_p25`, `sea_p28`, `sea_p30`, `sea_p50`, `sea_p52`, `sea_p6`, `sea_p61`, `sea_p62`, `sea_p65`, `sea_p68`, `sea_p69`

**Current:**

```json
{
  "pairs": [
    [
      "sea_p11",
      "sea_p6"
    ],
    [
      "sea_p25",
      "sea_p28"
    ],
    [
      "sea_p28",
      "sea_p30"
    ],
    [
      "sea_p50",
      "sea_p52"
    ],
    [
      "sea_p61",
      "sea_p62"
    ],
    [
      "sea_p65",
      "sea_p68"
    ],
    [
      "sea_p68",
      "sea_p69"
    ]
  ]
}
```

**Proposed:**

```json
{
  "remove_pairs": [
    [
      "sea_p11",
      "sea_p6"
    ],
    [
      "sea_p25",
      "sea_p28"
    ],
    [
      "sea_p28",
      "sea_p30"
    ],
    [
      "sea_p50",
      "sea_p52"
    ],
    [
      "sea_p61",
      "sea_p62"
    ],
    [
      "sea_p65",
      "sea_p68"
    ],
    [
      "sea_p68",
      "sea_p69"
    ]
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7900, 1000, 9900, 2850); evidence/ap_pacific_north.png
- evidence/ap_se_asia.png; evidence/ap_australia.png; evidence/ap_pacific_south.png

**Scope / dependency:** All seven pairs lack a finite common boundary. P11/P6 have P5 between; P50/P52 have P51 between; P61/P62 are separated by islands and P60/P63. P65/P68 skip P66/P67; P68/P69 cross the Pacific. Native second pass specifically confirms that P34–P45 and P60–P61 are real short contacts and excludes them from deletion.

## AP-100 — Remove nonexistent naval facilities from Celebes, Portuguese Timor and both New Guinea territories

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_celebes`, `land_timor`, `land_dutch_new_guinea`, `land_new_guinea`

**Current:**

```json
{
  "land_celebes": [
    {
      "id": "facility_land_celebes_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_p60"
      ],
      "storage": "coastal_edges"
    }
  ],
  "land_timor": [
    {
      "id": "facility_land_timor_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_p61"
      ],
      "storage": "coastal_edges"
    }
  ],
  "land_dutch_new_guinea": [
    {
      "id": "facility_new_guinea_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_p61"
      ],
      "storage": "coastal_edges"
    }
  ],
  "land_new_guinea": [
    {
      "id": "facility_guinea_minor_port",
      "type": "minor_port",
      "sea_accesses": [
        "sea_p63"
      ],
      "storage": "coastal_edges"
    }
  ]
}
```

**Proposed:**

```json
{
  "land_celebes": [],
  "land_timor": [],
  "land_dutch_new_guinea": [],
  "land_new_guinea": []
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- game_content/maps/gw36map.png rect (6250, 2600, 8250, 4030); evidence/ap_se_asia.png

**Scope / dependency:** Fresh full-coast source scan finds no naval facility symbols on these four territories. Delete the physical minor-port claims, not merely their wrong sea accesses. The New Britain major port is a separate neighboring island facility.

## AP-101 — Delete Western Australia’s unsupported minor port

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_aus_western_australia`

**Current:**

```json
[
  {
    "id": "facility_western_australia_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_i6"
    ],
    "storage": "coastal_edges"
  }
]
```

**Proposed:**

```json
[]
```

**Evidence:**

- game_content/maps/gw36map.png rect (6100, 3750, 8650, 4888); evidence/ap_australia.png
- game_content/maps/gw36map.png rect (7180, 3890, 7850, 4230); evidence/ap_naval_australia_north.png

**Scope / dependency:** Fresh source scan covers the complete P61/P63/P69/P70 coastline. No naval symbol is printed; the NT seaplane base and South Australia major port lie across distinct land borders.

## AP-103 — Delete fabricated Philippine minor-port instances

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_luzon_and_the_visayas`, `land_mindanao`

**Current:**

```json
{
  "remove_ids": [
    "facility_and_the_visayas_minor_port",
    "facility_land_mindanao_minor_port"
  ]
}
```

**Proposed:**

```json
{
  "remove_ids": [
    "facility_and_the_visayas_minor_port",
    "facility_land_mindanao_minor_port"
  ],
  "retain_luzon_submarine_base": true,
  "retain_unassigned_p50_major_port": "AP-095"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6810, 2730, 7500, 3390); evidence/ap_philippines_edges.png

**Scope / dependency:** Fresh icon review finds no plain-anchor minor port in either Philippine territory. The Luzon blue vertical symbol is its submarine base. The separate blue plain anchor is a real major port whose owner remains unresolved; this deletion does not remove that physical port.


## Complete stored-connection deletion index

The source pair review proposes removing 159 stored physical relations. Some are already grouped in the findings above or in coast-replacement changes. This index exposes each individual pair; it does not add independent finding counts. Both stored directions and their attached attributes would be removed.

- `land_aden` ↔ `sea_i3`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_angola` ↔ `sea_a39`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_aus_new_south_wales` ↔ `land_aus_tasmania`. Open water and no printed narrow-crossing line; current ordinary land/rail adjacency is unsupported.
- `land_aus_new_south_wales` ↔ `sea_p68`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_aus_northern_territory` ↔ `land_timor`. Open water and no printed narrow-crossing line; current ordinary land/rail adjacency is unsupported.
- `land_aus_northern_territory` ↔ `sea_p61`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_aus_queensland` ↔ `sea_p62`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_aus_tasmania` ↔ `sea_p68`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_aus_western_australia` ↔ `sea_i6`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_borneo` ↔ `land_celebes`. Open water and no printed narrow-crossing line; current ordinary land/rail adjacency is unsupported.
- `land_borneo` ↔ `land_java`. Open water and no printed narrow-crossing line; current ordinary land/rail adjacency is unsupported.
- `land_brazil_caatinga` ↔ `sea_a38`. Printed coast set is sea_a45, sea_a47; sea_a38 does not meet this land zone.
- `land_brazil_pampas` ↔ `sea_a39`. Printed coast set is sea_a47; sea_a39 does not meet this land zone.
- `land_brazil_rio_de_janeiro` ↔ `sea_a39`. Printed coast set is sea_a47; sea_a39 does not meet this land zone.
- `land_buenos_aires` ↔ `land_paraguay`. Norte Grande and Uruguay separate Paraguay from the Buenos Aires city zone.
- `land_buenos_aires` ↔ `sea_a40`. Printed coast set is sea_a49; sea_a40 does not meet this land zone.
- `land_burma` ↔ `land_india_benares`. Bengal intervenes.
- `land_burma` ↔ `land_india_calcutta`. Bengal reaches the coast between these territories.
- `land_cameroon` ↔ `sea_a38`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_cape_town` ↔ `sea_a40`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_chile` ↔ `sea_p31`. Printed coast set is sea_p77, sea_p78, sea_a49; sea_p31 does not meet this land zone. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur. American land-side details are owned by Americas audit; this row checks the Pacific polygon relation and uses shared source review, without recertifying all land-side attributes.
- `land_colombia` ↔ `land_peru`. Ecuador and the hatched impassable Amazon area separate the roundel-bearing zones; no ordinary passable shared border.
- `land_colombia` ↔ `sea_a36`. Printed coast set is sea_a40, sea_p76; sea_a36 does not meet this land zone.
- `land_cuba` ↔ `land_hispaniola`. Open water separates Cuba and Haiti; no printed narrow-crossing line or railroad.
- `land_cze_bohemia` ↔ `land_pol_west_poland`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_dahomey` ↔ `sea_a38`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_denmark` ↔ `land_nor_southern_norway`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_denmark` ↔ `sea_a23`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_dutch_new_guinea` ↔ `sea_p61`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_eritrea` ↔ `land_sudan`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_estonia` ↔ `sea_a12`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_estonia` ↔ `sea_a13`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_fin_lapland` ↔ `sea_a14`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_fin_southern_finland` ↔ `land_swe_norrland`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_fra_alsace_lorraine` ↔ `land_ger_western_germany`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_fra_aquitaine` ↔ `sea_a28`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_fra_normandy` ↔ `sea_a23`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_fra_picardy` ↔ `sea_a23`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_fra_southern_france` ↔ `sea_a28`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_french_guiana` ↔ `sea_a38`. Printed coast set is sea_a41; sea_a38 does not meet this land zone.
- `land_french_morocco` ↔ `sea_a28`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_french_somaliland` ↔ `sea_i5`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_gbr_northern_england` ↔ `sea_a21`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_gbr_scotland` ↔ `sea_a10`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_ger_bavaria` ↔ `land_ger_eastern_germany`. Berlin and Bohemia separate the named territories. Bavaria meets Berlin at the southern circle arc; Eastern Germany is on the far side of Berlin. Source graph shortcut proposed for deletion.
- `land_ger_eastern_germany` ↔ `land_ger_konigsberg`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_ger_western_germany` ↔ `sea_a23`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_gre_macedonia` ↔ `sea_m5`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_guyana` ↔ `sea_a38`. Printed coast set is sea_a41; sea_a38 does not meet this land zone.
- `land_hispaniola` ↔ `sea_a36`. The aggregate Hispaniola node must be replaced by Haiti and Dominican Republic; neither a single political node nor this A36 attachment is printed.
- `land_india_benares` ↔ `land_india_maharashtra`. Delhi and Southern India intervene; no finite common border.
- `land_india_ceylon` ↔ `sea_i6`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_india_southern_india` ↔ `sea_i6`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_iran_northern_iran` ↔ `land_northern_iraq`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_iran_southern_iran` ↔ `sea_i7`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_ireland` ↔ `sea_a21`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_ireland` ↔ `sea_a22`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_ita_lazio` ↔ `land_ita_northern_italy`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_ita_lazio` ↔ `sea_m4`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_ita_rome` ↔ `land_ita_southern_italy`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_ita_southern_italy` ↔ `sea_m4`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_kashmir` ↔ `land_nepal`. A finite Punjab strip reaches the Himalayas between these tiles.
- `land_kuwait` ↔ `sea_i7`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_lithuania` ↔ `land_pol_west_poland`. Konigsberg and Podlachia intervene. West Poland reaches Podlachia at the Konigsberg southeast junction, not Lithuania. Source graph shortcut proposed for deletion.
- `land_lower_egypt` ↔ `sea_m9`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_madagascar` ↔ `sea_i4`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_mauritius` ↔ `sea_i4`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_mex_western_mexico` ↔ `sea_p30`. Printed coast set is sea_p31; sea_p30 does not meet this land zone. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur. American land-side details are owned by Americas audit; this row checks the Pacific polygon relation and uses shared source review, without recertifying all land-side attributes.
- `land_mindanao` ↔ `sea_p52`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_new_britain` ↔ `land_new_guinea`. Open water and no printed narrow-crossing line; current ordinary land/rail adjacency is unsupported.
- `land_new_britain` ↔ `sea_p63`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_new_caledonia` ↔ `sea_p65`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_new_guinea` ↔ `sea_p63`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_nigeria` ↔ `sea_a38`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_nor_southern_norway` ↔ `sea_a6`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_nor_trondelag` ↔ `sea_a6`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_nz_north_island` ↔ `sea_p69`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_nz_south_island` ↔ `sea_p69`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_oman` ↔ `land_qatar`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_oman` ↔ `land_saudi_arabia`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_panama` ↔ `sea_a36`. Printed coast set is sea_a40, sea_p76; sea_a36 does not meet this land zone.
- `land_panama` ↔ `sea_p31`. Printed coast set is sea_a40, sea_p76; sea_p31 does not meet this land zone. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur. American land-side details are owned by Americas audit; this row checks the Pacific polygon relation and uses shared source review, without recertifying all land-side attributes.
- `land_patagonia` ↔ `sea_a40`. Printed coast set is sea_a49; sea_a40 does not meet this land zone.
- `land_pol_podlachia` ↔ `land_pol_warsaw`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_portuguese_east_africa` ↔ `sea_i4`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_puerto_rico` ↔ `sea_a36`. Printed coast set is sea_a41; sea_a36 does not meet this land zone.
- `land_qatar` ↔ `sea_i7`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_saudi_arabia` ↔ `sea_i3`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_seychelles` ↔ `sea_i4`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_south_africa` ↔ `sea_a40`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_southern_iraq` ↔ `land_transjordan`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_southern_iraq` ↔ `sea_i7`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_southwest_africa` ↔ `sea_a39`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_spanish_morocco` ↔ `sea_a28`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_suriname` ↔ `sea_a38`. Printed coast set is sea_a41; sea_a38 does not meet this land zone.
- `land_swe_norrland` ↔ `sea_a14`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_tanganyika` ↔ `sea_i4`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_timor` ↔ `sea_p61`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_tobruk` ↔ `sea_m9`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_transjordan` ↔ `sea_m9`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_tripoli` ↔ `land_tunisia`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_tur_akdeniz` ↔ `sea_m11`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_tur_ankara` ↔ `land_tur_istanbul`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_uruguay` ↔ `sea_a39`. Printed coast set is sea_a47; sea_a39 does not meet this land zone.
- `land_usa_appalachia` ↔ `land_usa_the_northeast`. Great Lakes occupies the finite strip between Appalachia and The Northeast; both separately meet Washington. The printed route passes through Great Lakes.
- `land_usa_chicago` ↔ `land_usa_new_york`. Great Lakes/The Northeast and other tiles intervene; railroad reachability is not direct adjacency.
- `land_usa_chicago` ↔ `land_usa_san_francisco`. Multiple western and central US tiles intervene.
- `land_usa_great_lakes` ↔ `land_usa_upper_midwest`. Midwest lies between Upper Midwest at the seam and the Great Lakes tile.
- `land_usa_new_york` ↔ `land_usa_washington_dc`. The Northeast separates the two circular city zones; the printed railway crosses that intervening tile.
- `land_usa_pacific_northwest` ↔ `sea_p6`. Printed coast set is sea_p13; sea_p6 does not meet this land zone. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur. American land-side details are owned by Americas audit; this row checks the Pacific polygon relation and uses shared source review, without recertifying all land-side attributes.
- `land_usa_san_francisco` ↔ `sea_p28`. Printed coast set is sea_p25; sea_p28 does not meet this land zone. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur. American land-side details are owned by Americas audit; this row checks the Pacific polygon relation and uses shared source review, without recertifying all land-side attributes.
- `land_usa_southeastern_united_states` ↔ `sea_a31`. Printed coast set is sea_a30, sea_a36, sea_a37; sea_a31 does not meet this land zone.
- `land_usa_southwest_united_states` ↔ `land_usa_texas`. Great Plains forms a continuous strip between Southwest US and the eastern map cut. Southwest US does not reach Texas across the seam.
- `land_usa_southwest_united_states` ↔ `sea_p30`. Printed coast set is sea_p25; sea_p30 does not meet this land zone. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur. American land-side details are owned by Americas audit; this row checks the Pacific polygon relation and uses shared source review, without recertifying all land-side attributes.
- `land_usa_the_carolinas` ↔ `sea_a26`. Printed coast set is sea_a30; sea_a26 does not meet this land zone.
- `land_usa_washington_dc` ↔ `sea_a26`. Printed coast set is sea_a30; sea_a26 does not meet this land zone.
- `land_usr_angara` ↔ `land_usr_chita`. Buryatia intervenes.
- `land_usr_buryatia` ↔ `land_usr_primorsky_krai`. Chita and Amur intervene.
- `land_usr_crimea` ↔ `land_usr_southern_ukraine`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_usr_crimea` ↔ `sea_m10`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_usr_gorky` ↔ `land_usr_tula_lipetsk`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_usr_kalmytskaya` ↔ `land_usr_saratov`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_usr_kiev` ↔ `land_usr_taurida`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_usr_kola` ↔ `land_usr_northern_russia`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation. White Sea separates the coasts; Karelia intervenes on land.
- `land_usr_kola` ↔ `sea_a13`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_usr_kola` ↔ `sea_a14`. Printed sea ID at this coast is different; the named polygon does not share the coastline. See regional coast replacement findings and sea matrix. Railway access is governed by whole-zone coverage (§13.2.8); this coast does not require a separately drawn rail spur.
- `land_usr_leningrad` ↔ `sea_a12`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_usr_moscow` ↔ `land_usr_smolensk`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_usr_north_caucasia` ↔ `land_usr_stalingrad`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_usr_northern_russia` ↔ `land_usr_western_russia`. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_venezuela` ↔ `sea_a36`. Printed coast set is sea_a40, sea_a41; sea_a36 does not meet this land zone.
- `land_western_egypt` ↔ `sea_m9`. No positive coastline in this sea zone; corrected complete coast set recorded separately. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `sea_a12` ↔ `sea_a23`. A11 intervenes between the North Sea A23 and the Kaiser-Wilhelm canal; the actual canal endpoints are A11 and A12. Printed source has no matching direct adjacency; see linked deletion proposal. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `sea_a21` ↔ `sea_a23`. One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.
- `sea_a22` ↔ `sea_a28`. One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.
- `sea_a31` ↔ `sea_a36`. One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.
- `sea_a33` ↔ `sea_a36`. One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.
- `sea_a35` ↔ `sea_a38`. One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.
- `sea_a36` ↔ `sea_p31`. Panama Canal is printed between A40 and P76, not Gulf of Mexico A36 and P31. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_a39` ↔ `sea_a40`. One or more printed sea zones intervene. Do not infer adjacency from similar names, convoy routes or sequential numbers.
- `sea_a44` ↔ `sea_m1`. The Mediterranean cell adjoining Gibraltar is M2; M1 lies farther north.
- `sea_i11` ↔ `sea_i6`. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_i3` ↔ `sea_i5`. Printed sea boundary traced. No source connection; use corrected endpoint proposal.
- `sea_i3` ↔ `sea_i6`. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_i3` ↔ `sea_m9`. Printed sea boundary traced. No source connection; use corrected endpoint proposal.
- `sea_i4` ↔ `sea_i6`. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_i5` ↔ `sea_m9`. Printed sea boundary traced. No source connection; use corrected endpoint proposal.
- `sea_m10` ↔ `sea_m5`. Printed sea boundary traced. No source connection; use corrected endpoint proposal.
- `sea_m10` ↔ `sea_m9`. Printed sea boundary traced. No source connection; use corrected endpoint proposal.
- `sea_m11` ↔ `sea_m12`. Printed sea boundary traced. No source connection; use corrected endpoint proposal.
- `sea_m3` ↔ `sea_m5`. Printed sea boundary traced. No source connection; use corrected endpoint proposal.
- `sea_m4` ↔ `sea_m5`. Printed sea boundary traced. No source connection; use corrected endpoint proposal.
- `sea_p11` ↔ `sea_p6`. P5 intervenes. Native Pacific grid cross-checked with Asia/Pacific evidence. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_p25` ↔ `sea_p28`. P24/P29 intervene. Native Pacific grid cross-checked with Asia/Pacific evidence. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_p28` ↔ `sea_p30`. P29 intervenes. Native Pacific grid cross-checked with Asia/Pacific evidence. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_p50` ↔ `sea_p52`. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_p61` ↔ `sea_p62`. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_p65` ↔ `sea_p68`. P66 and P67 intervene. Native Pacific grid cross-checked with Asia/Pacific evidence. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
- `sea_p68` ↔ `sea_p69`. P69 is by Australia, separated by multiple sea cells. Native Pacific grid cross-checked with Asia/Pacific evidence. No finite shared sea boundary; intervening printed polygons/land are visible. Direct graph link skips zones. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
