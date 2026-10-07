# Uncertain — complete finding register

24 finding records. Group findings may contain multiple fields or nodes; these are not edit counts.

Proposals only. Apply neither uncertain values nor incomplete new-node records automatically. Each confidence rating applies only to the described fields. Regional reports explain dependencies and unresolved source coverage.

See [overview](README.md), [mechanism proposals](mechanisms_and_schema.md), and [machine-readable register](data/all_findings.json).

**Naval facilities were rechecked on 6 October 2026.** Start with the [corrected current-to-proposed facility roster](naval_facility_reaudit.md) for ports, dockyards, shipyards and naval bases. Earlier conditional port-ID renaming examples must not be applied as a list of real facilities.

This register also needs to be read with [per-node review coverage](data/review_coverage.json) and [per-edge coverage](data/edge_review_coverage.json). Those ledgers explicitly retain unverified fields even where no single ambiguous feature has a separate finding ID.

## Naval-facility source conflicts and ownership ambiguities

The 6 October naval recheck retains these territory-level uncertainties. They supplement the finding register; the two Philippine rows concern the same single physical port, already discussed in WG-031/AP-095. See the [corrected facility roster](naval_facility_reaudit.md) for the proposed values.

### Cape Town

```json
[
  {
    "field": "map_vs_rule_example",
    "source": "game_content/rules/Global War 1936 v4.3 Rulebook.pdf",
    "printed_page": 16,
    "details": "The printed board clearly shows a white circled-anchor minor-dockyard symbol, while the supply-path example calls Cape Town a Minor Port. Expected facilities here transcribe the board symbol; reconcile edition/source precedence before applying a different type."
  }
]
```

### Luzon and the Visayas

```json
[
  {
    "facility_id": "facility_philippines_p50_major_port_unassigned",
    "issue": "land ownership of P50 major port",
    "candidate_land_ids": [
      "land_luzon_and_the_visayas",
      "land_mindanao"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "rectangle": [
          6810,
          2730,
          7500,
          3390
        ],
        "crop": "evidence/ap_philippines_edges.png"
      }
    ]
  }
]
```

### Mindanao

```json
[
  {
    "facility_id": "facility_philippines_p50_major_port_unassigned",
    "issue": "land ownership of P50 major port",
    "candidate_land_ids": [
      "land_luzon_and_the_visayas",
      "land_mindanao"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "rectangle": [
          6810,
          2730,
          7500,
          3390
        ],
        "crop": "evidence/ap_philippines_edges.png"
      }
    ]
  }
]
```

## WG-031 — Resolve Manila Line Philippine land endpoint

**Field:** `convoy_lines endpoints / ordered seas / beneficiary` · **Confidence:** high_sea_path_unresolved_land_endpoint · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_luzon_and_the_visayas`, `land_mindanao`, `land_usa_san_francisco`, `sea_p25`, `sea_p24`, `sea_p29`, `sea_p37`, `sea_p36`, `sea_p35`, `sea_p45`, `sea_p43`, `sea_p42`, `sea_p51`, `sea_p50`

**Current:**

No production convoy layer; observed label and cap in audit register

**Proposed:**

```json
{
  "printed_name": "Manila Line",
  "observed_loss_cap": 3,
  "printed_loss_cap_status": "numeric_cap_printed",
  "beneficiary_nation_id": "usa",
  "complete_path": [
    "sea_p25",
    "sea_p24",
    "sea_p29",
    "sea_p37",
    "sea_p36",
    "sea_p35",
    "sea_p45",
    "sea_p43",
    "sea_p42",
    "sea_p51",
    "sea_p50"
  ],
  "endpoints": [
    {
      "kind": "land",
      "node_id": "land_usa_san_francisco"
    },
    {
      "kind": "land",
      "node_id": null,
      "candidate_node_ids": [
        "land_luzon_and_the_visayas",
        "land_mindanao"
      ],
      "access_sea_id": "sea_p50",
      "facility_type": "major_port"
    }
  ]
}
```

**Evidence:**

- evidence/root_convoy_manila_sf.jpg
- evidence/root_convoy_western_pacific.jpg
- evidence/root_pacific_east.jpg
- evidence/root_convoy_manila_35_45_43.jpg
- evidence/root_convoy_far_east.jpg
- evidence/root_convoy_manila_west_end.jpg

**Scope / dependency:** Entire sea path is traced, including P45 and the P51→P50 Philippine bend. The white-anchor-on-blue terminal is a major port, not a dockyard. It is drawn on the western Visayas island cluster; assignment to Luzon and the Visayas versus Mindanao is unresolved in the source interpretation. Do not infer the endpoint from the Manila label or proximity to the Mindanao label. Do not import as a complete usable route until the endpoint is resolved.

## AM-033 — Baffin source conflict: blank glossary row versus earlier tundra assignment

**Field:** `terrain / directional border_terrain` · **Confidence:** medium · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_can_baffin_island`

**Current:**

```json
{
  "terrain": "tundra",
  "edges": {
    "land_can_district_of_keewatin": "tundra",
    "sea_a1": "coast",
    "sea_a2": "coast"
  }
}
```

**Proposed:**

Reconcile blank intrinsic glossary row with current tundra and board ice artwork; see AM-232.

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 0, 2250, 1450], "crop": "docs/map_audits/full_world/evidence/americas_arctic.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}

**Scope / dependency:** This is an actual source disagreement after visual glossary check, not an uninspected approach. It duplicates the more explicit AM-232 issue.

## AM-073 — Impassable Amazon needs explicit non-normal adjacency treatment

**Field:** `impassable subregion / directional passage` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_colombia`, `land_ecuador`, `land_venezuela`, `land_peru`, `land_bolivia`, `land_brazil_amazon_jungle`

**Current:**

```json
{
  "amazon_peru": {
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
  "amazon_venezuela": {
    "neighbor_id": "land_brazil_amazon_jungle",
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
}
```

**Proposed:**

Trace Colombia/Ecuador/Venezuela approaches against the hatched border; do not add ordinary passable neighbors through the impassable artwork. Keep air, supply, and river legality distinct.

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [280, 2900, 930, 3550], "crop": "docs/map_audits/full_world/evidence/americas_andes_amazon_detail.png"}

**Scope / dependency:** Entire western Amazonas boundary and both impassable-region tips were inspected. Venezuela and Bolivia have finite unhatched geographic contacts (current edge / AM-051 respectively); Colombia/Ecuador contacts and movement across the hatched tip remain source/model questions. Peru approach remains explicitly blocked by AM-072.

## AM-175 — US–Canada map-seam contacts

**Field:** `directional topology / field attribution` · **Confidence:** medium · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_upper_midwest`, `land_can_manitoba`, `land_can_alberta_saskatchewan`

**Current:**

See current node/edge records

**Proposed:**

Alberta–Pacific Northwest and Alberta–Upper Midwest finite same-image borders are resolved by AM-241. Manitoba–Upper Midwest across opposite map cuts remains an uncertain candidate because the cut fragments do not align. Retain user-approved Alberta–Manitoba and Mackenzie–Keewatin.

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Both seam fragments inspected; source-registration ambiguity is explicit. This no longer withholds the Alberta borders that can be seen on the same source fragment.

## AM-176 — Mississippi river-route and directional crossing audit

**Field:** `directional topology / field attribution` · **Confidence:** medium · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_heartlands`, `land_usa_new_orleans`, `land_usa_midwest`, `land_usa_appalachia`, `land_usa_chicago`

**Current:**

See current node/edge records

**Proposed:**

Printed Mississippi network is present through Midwest, Chicago, Heartlands, Appalachia, New Orleans and Texas; explicit combat directions have now been compared against glossary pp5–6. A rules-backed river-transport layer must represent channel continuity separately from river_crossing; see root mechanisms proposal.

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** River artwork and all explicit glossary directions were inspected. Residual uncertainty is the legal/channel encoding into has_river, not an unperformed visual search for blue lines. Canal/seaway routes and navigability are separate from merely sharing a river border.

## AM-228 — Remaining US opposite-map-edge land borders

**Field:** `seam land adjacency and railway` · **Confidence:** medium · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_upper_midwest`, `land_usa_midwest`, `land_usa_great_plains`, `land_usa_heartlands`, `land_usa_texas`

**Current:**

```json
{
  "land_usa_upper_midwest": [
    "land_usa_great_lakes",
    "land_usa_great_plains",
    "land_usa_midwest",
    "land_usa_pacific_northwest"
  ],
  "land_usa_great_plains": [
    "land_usa_texas",
    "land_usa_upper_midwest",
    "land_usa_western_united_states"
  ]
}
```

**Proposed:**

```json
{
  "candidate_missing_pairs": [
    [
      "land_usa_great_plains",
      "land_usa_heartlands"
    ],
    [
      "land_usa_upper_midwest",
      "land_usa_heartlands"
    ]
  ],
  "railway": "trace each track across matched seam rows, do not infer from adjacent rails"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1150, 9900, 2550], "crop": "docs/map_audits/full_world/evidence/americas_usa_seam.png", "source_rectangles": [[9400, 1150, 9900, 2550], [0, 1150, 1250, 2550]], "scale": 1}
- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1150, 1250, 2550], "crop": "docs/map_audits/full_world/evidence/americas_usa_seam.png", "source_rectangles": [[9400, 1150, 9900, 2550], [0, 1150, 1250, 2550]], "scale": 1}

**Scope / dependency:** Composite places opposite image edges side by side at unchanged vertical coordinate. User-approved Canadian seam decisions are not superseded. Finite row overlap suggests missing US edges, but unequal map art and gutter must be reconciled before creating links.

## AM-229 — Clarify shore railway fields against whole-zone rail coverage

**Field:** `railway_connection semantics on land-sea entries` · **Confidence:** medium · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_pacific_northwest`, `land_usa_san_francisco`, `land_usa_southwest_united_states`, `land_usa_new_england`, `land_usa_new_york`, `land_usa_washington_dc`, `land_usa_the_carolinas`, `land_usa_texas`, `land_usa_new_orleans`, `land_peru`, `land_chile`, `land_brazil_rio_de_janeiro`, `land_uruguay`, `land_buenos_aires`, `land_patagonia`

**Current:**

Mostly false on existing legacy coast entries; several ports are attached to wrong seas

**Proposed:**

Retain observed track/access artwork as evidence, but derive legal zone railway coverage using rulebook §13.2.8: a land zone with a border-crossing railway is covered by rail. Decide whether land-sea railway_connection stores artwork, legal access, or should be retired.

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}
- {"source": "game_content/rules/Global War 1936 v4.3 Rulebook.pdf", "pdf_page": 98, "section": "13.2.8"}

**Scope / dependency:** Corrected after rules QA: a dedicated spur to each naval facility must not be invented as an extra prerequisite. Visible tracks may document geography, but the game rule covers the entire zone.

## AM-232 — Baffin Island glossary blank row versus ice artwork

**Field:** `terrain` · **Confidence:** medium · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_can_baffin_island`

**Current:**

tundra

**Proposed:**

```json
{
  "glossary_blank_columns": "normal",
  "board_artwork": "white ice/glacier-looking interior; no printed tundra tree field"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** The earlier Canadian audit assigns tundra. Glossary p5 has no X for Baffin whereas Keewatin explicitly has tundra. Resolve source mismatch before changing a previously authored territory.

## AM-235 — Interpret the Amazonas all-adjacent-territories river requirement

**Field:** `river_crossing scope` · **Confidence:** medium · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `sea_a41`, `land_colombia`, `land_ecuador`, `land_peru`

**Current:**

Partial incoming river flags

**Proposed:**

Apply to every legal incoming approach after determining whether the source wording includes sea landings and whether a proposed land edge is actually passable.

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Literal glossary p6 quantifier is preserved in the directional table. Hatched Amazon impassable artwork takes precedence over any assumption that a listed river penalty creates legal movement.

## EA-363 — Remaining field-specific interpretation limits

**Field:** `coverage` · **Confidence:** explicit_limit · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_scotland`, `land_gbr_northern_england`, `land_gbr_southern_england`, `land_gbr_london`, `land_ireland`, `land_esp_galicia_and_leon`, `land_esp_basque_country`, `land_esp_catalonia`, `land_esp_madrid`, `land_esp_western_andalucia`, `land_esp_eastern_andalucia`, `land_esp_balearic_islands`, `land_gibraltar`, `land_portugal`, `land_fra_normandy`, `land_fra_picardy`, `land_fra_paris`, `land_fra_aquitaine`, `land_fra_southern_france`, `land_fra_alsace_lorraine`, `land_neu_belgium`, `land_neu_netherlands`, `land_ger_western_germany`, `land_ger_eastern_germany`, `land_ger_bavaria`, `land_ger_berlin`, `land_aut_austria`, `land_cze_bohemia`, `land_switzerland`, `land_ita_northern_italy`, `land_ita_rome`, `land_ita_lazio`, `land_ita_southern_italy`, `land_fra_corsica`, `land_ita_sardinia`, `land_denmark`, `land_nor_southern_norway`, `land_nor_trondelag`, `land_swe_norrland`, `land_swe_gotaland`, `land_fin_lapland`, `land_fin_southern_finland`, `land_fin_viipuri_province`, `land_estonia`, `land_latvia`, `land_lithuania`, `land_ger_konigsberg`, `land_pol_west_poland`, `land_pol_podlachia`, `land_pol_lubelskie`, `land_pol_warsaw`, `land_pol_dolnoslaskie`, `land_pol_east_poland`, `land_cze_slovakia`, `land_hun_hungary`, `land_rom_central_romania`, `land_rom_bessarabia`, `land_bulgaria`, `land_yug_western_yugoslavia`, `land_yug_eastern_yugoslavia`, `land_albania`, `land_gre_macedonia`, `land_gre_thessaly`, `land_tur_istanbul`, `land_tur_karadeniz`, `land_tur_ankara`, `land_tur_akdeniz`, `land_tur_eastern_anatolia`, `land_azerbaijan`, `land_iran_northern_iran`, `land_iran_southern_iran`, `land_northern_iraq`, `land_syria`, `land_southern_iraq`, `land_transjordan`, `land_kuwait`, `land_qatar`, `land_oman`, `land_aden`, `land_saudi_arabia`, `land_spanish_morocco`, `land_french_morocco`, `land_northern_algeria`, `land_western_algeria`, `land_southern_algeria`, `land_tunisia`, `land_tripoli`, `land_tripolitania`, `land_cyrenaica`, `land_tobruk`, `land_western_egypt`, `land_lower_egypt`, `land_upper_egypt`, `land_nubia`, `land_cyprus`, `land_french_sudan`, `land_niger`, `land_dahomey`, `land_nigeria`, `land_cameroon`, `land_chad`, `land_oubangui_chari`, `land_belgian_congo`, `land_sudan`, `land_eritrea`, `land_abyssinia`, `land_french_somaliland`, `land_british_somaliland`, `land_italian_somaliland`, `land_tanganyika`, `land_angola`, `land_rhodesia`, `land_portuguese_east_africa`, `land_southwest_africa`, `land_bechuanaland`, `land_cape_town`, `land_south_africa`, `land_madagascar`, `land_mauritius`, `land_seychelles`, `land_usr_karelia`, `land_usr_northern_russia`, `land_usr_yaroslavl`, `land_usr_leningrad`, `land_usr_western_russia`, `land_usr_northern_belorussia`, `land_usr_southern_belorussia`, `land_usr_smolensk`, `land_usr_kaluga_oblast`, `land_usr_moscow`, `land_usr_gorky`, `land_usr_orel_kursk`, `land_usr_tula_lipetsk`, `land_usr_saratov`, `land_usr_kiev`, `land_usr_western_ukraine`, `land_usr_eastern_ukraine`, `land_usr_southern_ukraine`, `land_usr_taurida`, `land_usr_crimea`, `land_usr_donets_kuban`, `land_usr_stalingrad`, `land_usr_kalmytskaya`, `land_usr_north_caucasia`, `land_usr_transcaucasia`

**Current:**

```json
{
  "regional_nodes": 145
}
```

**Proposed:**

Every stored physical pair touching the reviewed regional land nodes was examined (three Iranian external borders are covered by AP), and the additional 19 regional sea pairs were examined. See the explicit pair ledger. Remaining unresolved fields are listed per pair; river-route and facility/gauge scope is not implied by physical-adjacency confirmation.

**Evidence:**

- {"source": "game_content/maps/gw36map.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_pages": [7, 8, 9, 10, 11]}

**Scope / dependency:** Second source pass replaced the first-pass blanket topology deferral. This is a proposal audit with field-scoped coverage, not full-field certification.

## EA-364 — Impassable Sahara and Pripet boundary routing

**Field:** `passable` · **Confidence:** medium · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_western_algeria`, `land_southern_algeria`, `land_french_sudan`, `land_niger`, `land_chad`, `land_cyrenaica`, `land_western_egypt`, `land_nubia`, `land_usr_southern_belorussia`, `land_usr_western_ukraine`, `land_pol_east_poland`

**Current:**

```json
null
```

**Proposed:**

Author map-relative passability per crossing, preserving the distinction between physical adjacency and legal ground traversal. Do not delete all touching territories or set entire mixed zones impassable.

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** Shaded Sahara/Pripet areas cover parts of multiple named territories. Shortest within-two-zones route must be checked for each candidate border; rail lines across Pripet require explicit source/rules reconciliation, not automatic assumption.

## EA-365 — Spain original nationality versus civil-war setup

**Field:** `original_owner/current_owner` · **Confidence:** medium · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_madrid`, `land_esp_galicia_and_leon`, `land_esp_basque_country`, `land_esp_catalonia`, `land_esp_western_andalucia`, `land_esp_eastern_andalucia`, `land_esp_balearic_islands`, `land_spanish_morocco`

**Current:**

```json
{
  "land_esp_madrid": "Nationalist Spain",
  "land_esp_galicia_and_leon": "Spain",
  "land_esp_basque_country": "Spain",
  "land_esp_catalonia": "Spain",
  "land_esp_western_andalucia": "Spain",
  "land_esp_eastern_andalucia": "Republican Spain",
  "land_esp_balearic_islands": "Republican Spain",
  "land_spanish_morocco": "Spain"
}
```

**Proposed:**

Use a consistent static Spanish identity and dated Nationalist/Republican setup allocation; verify setup sheet before changing faction ownership.

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Current mix of Spain, Nationalist Spain and Republican Spain is inconsistent. Printed flags and the 1936 civil-war setup are not interchangeable with national identity.

## EA-366 — Karelia river-table wording

**Field:** `river_crossing` · **Confidence:** medium · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_karelia`

**Current:**

```json
null
```

**Proposed:**

```json
{
  "incoming_true_from": [
    "Northern Russia",
    "Western Russia",
    "Leningrad"
  ],
  "reverse_edges": "verify map"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Glossary says River Border with, whereas most rows say from. Trace both sides of each river; do not mechanically set both directions.

## AP-049 — Southern Iran–Punjab printed rail gap

**Field:** `railway_connection` · **Confidence:** medium · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_iran_southern_iran`, `land_india_punjab`

**Current:**

```json
true
```

**Proposed:**

Likely false; verify high-resolution endpoints and whether special rule joins them.

**Evidence:**

- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png

**Scope / dependency:** Iranian line stops west of frontier and Punjab line begins inland east of it. No continuous crossing is visible.

## AP-083 — South China/India/Himalayan impassable boundary treatment

**Field:** `passable/border_terrain` · **Confidence:** medium · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_china_sinkiang`, `land_tibet`, `land_kashmir`, `land_nepal`, `land_india_bengal`

**Current:**

Existing true defaults or incomplete endpoint edges

**Proposed:**

```json
{
  "confirmed_existing_impassable_pairs": [
    [
      "land_kashmir",
      "land_tibet"
    ],
    [
      "land_nepal",
      "land_tibet"
    ],
    [
      "land_india_bengal",
      "land_tibet"
    ],
    [
      "land_india_bengal",
      "land_china_sikang"
    ],
    [
      "land_india_bengal",
      "land_china_yunnan"
    ]
  ],
  "new_physical_impassable_contact": [
    "land_usr_turkmenistan",
    "land_china_sinkiang"
  ],
  "uncertainty": "Whether to encode physical contacts hidden inside the broad impassable mountain band as geography-only edges or use a barrier-area layer. Kashmir/Sinkiang and Afghanistan/Sinkiang contact interpretation should not create passable moves."
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png
- evidence/ap_central_asia.png
- game_content/maps/gw36map.png rect (5500, 2030, 6120, 2480); evidence/ap_turkestan_himalaya.png
- game_content/maps/gw36map.png rect (5740, 2300, 6320, 2800); evidence/ap_nepal_kashmir.png

**Scope / dependency:** The native second pass checks every stored Himalayan pair. Confirmed passable:false borders remain geographically present. The residual uncertainty is representation of the broad black barrier area and its hidden political contact lines, not an uninspected stored edge.

## AP-084 — Kobdo–Novosibirsk tiny border and Tannu Tuva state identity

**Field:** `neighbors/original_owner` · **Confidence:** medium · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_mongolia_kobdo`, `land_usr_novosibirsk`, `land_mongolia_tannu_tuva`

**Current:**

Kobdo–Novosibirsk present; Tannu Tuva owned by Mongolia

**Proposed:**

Confirm the narrow boundary junction and distinguish printed Tannu Tuva roundel from Mongolia setup affiliation.

**Evidence:**

- game_content/maps/gw36map.png rect (4300, 1200, 6400, 2500); evidence/ap_central_asia.png
- evidence/ap_siberia_east.png
- game_content/maps/gw36map.png rect (6040, 1330, 6500, 1680); evidence/ap_kobdo_junction.png
- game_content/maps/gw36map.png rect (6250, 1300, 6890, 2040); evidence/ap_mongolia_north_edges.png

**Scope / dependency:** Fresh native crop still leaves Kobdo–Novosibirsk tiny city-arc contact visually ambiguous. Tannu Tuva has a distinct red outer/blue inner emblem roundel, unlike Mongolia's white circle with upright emblem; original political identity versus player/home-country affiliation needs source reconciliation.

## AP-085 — Glossary/map ambiguity: Vyatka self-reference and omitted Yugria

**Field:** `river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_vyatka`, `land_usr_yugria`

**Current:**

Missing nodes; glossary says Vyatka river border from Vyatka

**Proposed:**

Preserve raw citation; resolve which neighboring approach was intended by map trace or official errata.

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- Terrain Glossary p12.

**Scope / dependency:** Do not turn the apparent glossary typo into a self-loop or silently substitute Yugria.

## AP-086 — Represent river transport separately from combat river crossings

**Field:** `has_river/river_crossing and named river network` · **Confidence:** high · **Severity:** moderate

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_aus_new_south_wales`, `land_aus_northern_territory`, `land_aus_queensland`, `land_aus_south_australia`, `land_aus_tasmania`, `land_aus_western_australia`, `land_india_benares`, `land_india_bengal`, `land_india_calcutta`, `land_india_ceylon`, `land_india_delhi`, `land_india_maharashtra`, `land_india_punjab`, `land_india_southern_india`, `land_nz_north_island`, `land_nz_south_island`, `land_usr_amur`, `land_usr_angara`, `land_usr_buryatia`, `land_usr_chita`, `land_usr_crimea`, `land_usr_donets_kuban`, `land_usr_eastern_kazakhstan`, `land_usr_eastern_ukraine`, `land_usr_gorky`, `land_usr_irkutsk`, `land_usr_kalmytskaya`, `land_usr_kaluga_oblast`, `land_usr_kamchatka`, `land_usr_karelia`, `land_usr_kiev`, `land_usr_kola`, `land_usr_leningrad`, `land_usr_magadan`, `land_usr_moscow`, `land_usr_north_caucasia`, `land_usr_north_sakhalin`, `land_usr_northern_belorussia`, `land_usr_northern_russia`, `land_usr_novosibirsk`, `land_usr_orel_kursk`, `land_usr_primorsky_krai`, `land_usr_saratov`, `land_usr_smolensk`, `land_usr_south_sakhalin`, `land_usr_southern_belorussia`, `land_usr_southern_ukraine`, `land_usr_southern_yakutia`, `land_usr_stalingrad`, `land_usr_stalino`, `land_usr_taurida`, `land_usr_transcaucasia`, `land_usr_tula_lipetsk`, `land_usr_turkestan`, `land_usr_vanavara`, `land_usr_western_russia`, `land_usr_western_ukraine`, `land_usr_yakutsk`, `land_usr_yaroslavl`

**Current:**

Many defaults; many uniform rail=true flags

**Proposed:**

Use the complete physical, railway/gauge and directional glossary ledgers. Model named river transport as a continuous network with banks and route permissions; a combat river-crossing requirement is not sufficient to infer that network.

**Evidence:**

- game_content/maps/gw36map.png rect (4250, 0, 6250, 1500); evidence/ap_siberia_west.png
- evidence/ap_siberia_east.png; evidence/ap_india.png; evidence/ap_australia.png

**Scope / dependency:** All 310 stored physical pairs and 64 proposed land/narrow pairs touching 36 new land tiles have now been source-checked for the relevant physical and railway/gauge questions. The remaining river transport item is a schema/representation decision, not a deferred physical-neighbor or railway review. Under §13.2.8 p98, any printed border-crossing railway gives whole-zone rail coverage; individual port spurs are not prerequisites.

## AP-092 — Unlabeled USA roundel inside P27 has no identified land outline

**Field:** `printed symbol interpretation` · **Confidence:** high · **Severity:** moderate

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_p27`

**Current:**

```json
null
```

**Proposed:**

Retain the crop/provenance and resolve the symbol; do not invent a named island or ownership of the sea zone.

**Evidence:**

- game_content/maps/gw36map.png rect (8260,2240,8630,2510); evidence/ap_p27_roundel.png

**Scope / dependency:** The USA roundel is clear, but no island outline, name, IPP or facility accompanies it. The terrain glossary does not supply a matching named tile. This is a real source ambiguity, distinct from an edge we have not yet traced.

## AP-093 — Manchurian printed original identity is different from Japan control

**Field:** `original_owner versus controller` · **Confidence:** high · **Severity:** moderate

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_manchuria_northern`, `land_manchuria_western`, `land_manchuria_eastern`, `land_manchuria_rehe`

**Current:**

original_owner and current_owner both Japan

**Proposed:**

Preserve the Manchukuo printed roundel as original national identity; represent Japanese control separately according to rules/setup rather than silently replacing one field.

**Evidence:**

- evidence/ap_east_asia.png; Rulebook §0.2 Home Country table includes Manchukuo roundels separately.

**Scope / dependency:** Roundels are legible. Remaining question is the intended schema meaning of original_owner and scenario controller, not uncertainty about which symbol is printed. Coordinate with global identity/setup proposal.

## AP-094 — Remote British Pacific ownership allocation requires explicit reconciliation

**Field:** `original_owner` · **Confidence:** high · **Severity:** moderate

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_fiji`, `land_new_hebrides`, `land_solomon_islands`, `land_gilbert_islands`, `land_line_islands`, `land_pitcairn_island`

**Current:**

Existing Fiji/New Hebrides United Kingdom; added remote islands proposed FEC from terrain-table grouping

**Proposed:**

Retain printed roundel and resolve Great Britain versus FEC player allocation using national setup; do not treat a terrain-table section heading as sufficient political state.

**Evidence:**

- evidence/ap_pacific_south.png; game_content/rules/GW1936_Terrain_Glossary_v1.pdf p3 groups these under FEC.

**Scope / dependency:** This is an allocation/model decision needing source reconciliation. Zero-IPP islands still matter to control, basing, home country and capture rules.

## AP-095 — Philippine major-port owner and Manila convoy endpoint land node

**Field:** `physical_facility_owner/convoy_endpoint` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_luzon_and_the_visayas`, `land_mindanao`, `sea_p50`

**Current:**

P50 western Philippine major-port symbol; earlier draft forced it into Luzon/Visayas

**Proposed:**

```json
{
  "id": "facility_philippines_p50_major_port_unassigned",
  "type": "major_port",
  "sea_accesses": [
    "sea_p50"
  ],
  "candidate_land_ids": [
    "land_luzon_and_the_visayas",
    "land_mindanao"
  ],
  "evidence": [
    {
      "source": "game_content/maps/gw36map.png",
      "rectangle": [
        6810,
        2730,
        7500,
        3390
      ],
      "crop": "evidence/ap_philippines_edges.png"
    }
  ],
  "notes": "The blue-square plain-anchor major port is definitely in P50. Raster island-group ownership is unresolved between Luzon/Visayas and Mindanao; do not silently assign it to either or count it twice.",
  "convoy": "Manila Line endpoint uses this physical facility; its sea path is independently verified."
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6810, 2730, 7500, 3390); evidence/ap_philippines_edges.png
- data/convoy_register.json; root WG-031/CV-14

**Scope / dependency:** Fresh 2026-10-06 review confirms major_port type and P50 access but retains island-group ownership uncertainty. The naval ledger records one unassigned physical facility with two candidate land nodes, never one duplicate in each territory. No dockyard symbol is present.

## AP-098 — P42–P50 open-water contact at the Philippine island-group divide

**Field:** `sea_neighbors` · **Confidence:** medium · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_p42`, `sea_p50`

**Current:**

Stored reciprocal pair

**Proposed:**

```json
{
  "retain_pending_source_clarification": true,
  "confirmed_matrix_excludes_this_pair": true
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6810, 2730, 7500, 3390); evidence/ap_philippines_edges.png

**Scope / dependency:** Native inspection resolves the neighboring P41, P42, P50 and P51 polygons but does not expose a finite P42/P50 open-water segment distinct from island outlines and the implicit Luzon/Visayas–Mindanao grouping. This is one of two unresolved stored physical pairs, with Kobdo–Novosibirsk.

## AP-099 — Direct Saratov–Ural railway connection at the dense Volga junction

**Field:** `railway_connection/gauge_change` · **Confidence:** medium · **Severity:** moderate

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_saratov`, `land_usr_ural`

**Current:**

Ural node absent; the newly proposed physical land border is real

**Proposed:**

```json
{
  "railway_connection": null,
  "gauge_change": null,
  "nearby_track_gauge": "broad",
  "physical_adjacency": "confirmed"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4910,1160,5220,1460); evidence/ea_sov_new_rail_volga.png
- data/europe_soviet_new_edge_rail_review.json; merged data/asia_pacific_new_edge_rail_review.json

**Scope / dependency:** The original artwork superimposes the Saratov/Gorky/Ural/Orenburg political boundaries, Volga tributaries and railway junction. Saratov-to-Ural direct passage versus an intervening short Gorky or Orenburg segment cannot be assigned confidently at native resolution. Nearby tracks have yellow broad-gauge checkers, but the direct edge remains unresolved. This is one source ambiguity among 64 reviewed new-node border rail cases, not uninspected work. Ural whole-zone railway coverage is independently established by its other confirmed rail borders.


## Stored physical connections with unresolved review status

These are pair-level review outcomes, supplementary to the finding register above. They are not extra finding IDs. Directional attributes may have their own uncertainties even when the physical relation is confirmed.

- `land_can_alberta_saskatchewan` ↔ `land_can_manitoba`: **uncertain**. Previously user-approved opposite-map-edge adjacency. The two cropped halves have unequal art alignment; this pass preserves authorization but cannot source-certify the finite border/rail transition.
- `land_can_district_of_keewatin` ↔ `land_can_district_of_mackenzie`: **uncertain**. Previously user-approved map-seam adjacency. The matching territory continuation is plausible but exact border projection is not aligned in the static image.
- `land_mongolia_kobdo` ↔ `land_usr_novosibirsk`: **uncertain**. Close native crop ap_kobdo_junction still leaves the three-way corner/contact at the city arc visually ambiguous; do not assume a border from river/rail proximity.
- `land_pol_lubelskie` ↔ `land_usr_western_ukraine`: **uncertain**. The Lubelskie/East Poland boundary reaches the Soviet boundary within the Pripet marsh junction; native line width does not establish a positive-length Lubelskie/Western Ukraine boundary. Directional combat terrain and river flags are covered only by the explicitly linked findings/glossary comparison, not by adjacency confirmation.
- `land_usa_great_plains` ↔ `land_usa_texas`: **uncertain**. Both printed territories reach opposite map cuts. A finite contact is plausible; unequal boundary row positions prevent certifying exact segment and rail transition from this raster alone.
- `land_usa_midwest` ↔ `land_usa_upper_midwest`: **uncertain**. Current seam link is plausible from territory rows and rail continuation. Opposite edge terrain/boundary rows are visibly offset; retain as uncertain source registration rather than pretending same-row matching proves it.
- `sea_p42` ↔ `sea_p50`: **uncertain**. Philippine inter-island division: no clear open-water boundary segment is separable from island-group outlines in the current raster. This is a grouping/junction interpretation, not an omitted image review. Complete revised sea sets are in data/asia_pacific_sea_neighbors.json; restricted Arctic route is separate.
