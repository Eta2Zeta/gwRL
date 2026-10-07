# Changes — complete finding register

536 finding records. Group findings may contain multiple fields or nodes; these are not edit counts.

Proposals only. Apply neither uncertain values nor incomplete new-node records automatically. Each confidence rating applies only to the described fields. Regional reports explain dependencies and unresolved source coverage.

See [overview](README.md), [mechanism proposals](mechanisms_and_schema.md), and [machine-readable register](data/all_findings.json).

**Naval facilities were rechecked on 6 October 2026.** Start with the [corrected current-to-proposed facility roster](naval_facility_reaudit.md) for ports, dockyards, shipyards and naval bases. Earlier conditional port-ID renaming examples must not be applied as a list of real facilities.

## WG-001 — Normalize terrain on 93 stored sea-to-sea directions after topology correction

**Field:** `neighbors[].border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_a1`, `sea_a10`, `sea_a11`, `sea_a12`, `sea_a13`, `sea_a14`, `sea_a15`, `sea_a18`, `sea_a19`, `sea_a2`, `sea_a20`, `sea_a21`, `sea_a22`, `sea_a23`, `sea_a25`, `sea_a26`, `sea_a28`, `sea_a29`, `sea_a31`, `sea_a33`, `sea_a35`, `sea_a36`, `sea_a38`, `sea_a39`, `sea_a40`, `sea_a44`, `sea_a6`, `sea_a7`, `sea_i11`, `sea_i12`, `sea_i3`, `sea_i4`, `sea_i5`, `sea_i6`, `sea_i7`, `sea_m1`, `sea_m10`, `sea_m11`, `sea_m12`, `sea_m2`, `sea_m3`, `sea_m4`, `sea_m5`, `sea_m9`, `sea_p10`, `sea_p11`, `sea_p12`, `sea_p13`, `sea_p17`, `sea_p2`, `sea_p24`, `sea_p25`, `sea_p28`, `sea_p3`, `sea_p30`, `sea_p31`, `sea_p34`, `sea_p35`, `sea_p42`, `sea_p43`, `sea_p44`, `sea_p45`, `sea_p46`, `sea_p47`, `sea_p5`, `sea_p50`, `sea_p51`, `sea_p52`, `sea_p53`, `sea_p54`, `sea_p59`, `sea_p6`, `sea_p60`, `sea_p61`, `sea_p62`, `sea_p63`, `sea_p64`, `sea_p65`, `sea_p68`, `sea_p69`, `sea_p8`, `sea_p9`

**Current:**

```json
[
  {
    "source_id": "sea_a10",
    "target_id": "sea_a7",
    "current": "normal"
  },
  {
    "source_id": "sea_a11",
    "target_id": "sea_a10",
    "current": "normal"
  },
  {
    "source_id": "sea_a12",
    "target_id": "sea_a11",
    "current": "normal"
  },
  {
    "source_id": "sea_a12",
    "target_id": "sea_a23",
    "current": "normal"
  },
  {
    "source_id": "sea_a13",
    "target_id": "sea_a12",
    "current": "normal"
  },
  {
    "source_id": "sea_a14",
    "target_id": "sea_a13",
    "current": "normal"
  },
  {
    "source_id": "sea_a15",
    "target_id": "sea_a2",
    "current": "normal"
  },
  {
    "source_id": "sea_a18",
    "target_id": "sea_a15",
    "current": "normal"
  },
  {
    "source_id": "sea_a19",
    "target_id": "sea_a18",
    "current": "normal"
  },
  {
    "source_id": "sea_a2",
    "target_id": "sea_a1",
    "current": "normal"
  },
  {
    "source_id": "sea_a21",
    "target_id": "sea_a20",
    "current": "normal"
  },
  {
    "source_id": "sea_a23",
    "target_id": "sea_a21",
    "current": "normal"
  },
  {
    "source_id": "sea_a23",
    "target_id": "sea_a22",
    "current": "normal"
  },
  {
    "source_id": "sea_a25",
    "target_id": "sea_a18",
    "current": "normal"
  },
  {
    "source_id": "sea_a26",
    "target_id": "sea_a25",
    "current": "normal"
  },
  {
    "source_id": "sea_a28",
    "target_id": "sea_a22",
    "current": "normal"
  },
  {
    "source_id": "sea_a29",
    "target_id": "sea_a28",
    "current": "normal"
  },
  {
    "source_id": "sea_a31",
    "target_id": "sea_a26",
    "current": "normal"
  },
  {
    "source_id": "sea_a31",
    "target_id": "sea_a36",
    "current": "normal"
  },
  {
    "source_id": "sea_a33",
    "target_id": "sea_a31",
    "current": "normal"
  },
  {
    "source_id": "sea_a33",
    "target_id": "sea_a36",
    "current": "normal"
  },
  {
    "source_id": "sea_a35",
    "target_id": "sea_a33",
    "current": "normal"
  },
  {
    "source_id": "sea_a38",
    "target_id": "sea_a35",
    "current": "normal"
  },
  {
    "source_id": "sea_a39",
    "target_id": "sea_a38",
    "current": "normal"
  },
  {
    "source_id": "sea_a40",
    "target_id": "sea_a39",
    "current": "normal"
  },
  {
    "source_id": "sea_a44",
    "target_id": "sea_m1",
    "current": "normal"
  },
  {
    "source_id": "sea_a7",
    "target_id": "sea_a6",
    "current": "normal"
  },
  {
    "source_id": "sea_i11",
    "target_id": "sea_i6",
    "current": "normal"
  },
  {
    "source_id": "sea_i12",
    "target_id": "sea_i11",
    "current": "normal"
  },
  {
    "source_id": "sea_i3",
    "target_id": "sea_m9",
    "current": "normal"
  },
  {
    "source_id": "sea_i4",
    "target_id": "sea_i5",
    "current": "normal"
  },
  {
    "source_id": "sea_i5",
    "target_id": "sea_i3",
    "current": "normal"
  },
  {
    "source_id": "sea_i5",
    "target_id": "sea_m9",
    "current": "normal"
  },
  {
    "source_id": "sea_i6",
    "target_id": "sea_i3",
    "current": "normal"
  },
  {
    "source_id": "sea_i6",
    "target_id": "sea_i4",
    "current": "normal"
  },
  {
    "source_id": "sea_i7",
    "target_id": "sea_i6",
    "current": "normal"
  },
  {
    "source_id": "sea_m10",
    "target_id": "sea_m5",
    "current": "normal"
  },
  {
    "source_id": "sea_m11",
    "target_id": "sea_m10",
    "current": "normal"
  },
  {
    "source_id": "sea_m12",
    "target_id": "sea_m11",
    "current": "normal"
  },
  {
    "source_id": "sea_m2",
    "target_id": "sea_m1",
    "current": "normal"
  },
  {
    "source_id": "sea_m3",
    "target_id": "sea_m2",
    "current": "normal"
  },
  {
    "source_id": "sea_m4",
    "target_id": "sea_m2",
    "current": "normal"
  },
  {
    "source_id": "sea_m5",
    "target_id": "sea_m3",
    "current": "normal"
  },
  {
    "source_id": "sea_m5",
    "target_id": "sea_m4",
    "current": "normal"
  },
  {
    "source_id": "sea_m9",
    "target_id": "sea_m10",
    "current": "normal"
  },
  {
    "source_id": "sea_p10",
    "target_id": "sea_p9",
    "current": "normal"
  },
  {
    "source_id": "sea_p11",
    "target_id": "sea_p6",
    "current": "normal"
  },
  {
    "source_id": "sea_p12",
    "target_id": "sea_p11",
    "current": "normal"
  },
  {
    "source_id": "sea_p12",
    "target_id": "sea_p6",
    "current": "normal"
  },
  {
    "source_id": "sea_p13",
    "target_id": "sea_p12",
    "current": "normal"
  },
  {
    "source_id": "sea_p17",
    "target_id": "sea_p9",
    "current": "normal"
  },
  {
    "source_id": "sea_p24",
    "target_id": "sea_p12",
    "current": "normal"
  },
  {
    "source_id": "sea_p25",
    "target_id": "sea_p13",
    "current": "normal"
  },
  {
    "source_id": "sea_p25",
    "target_id": "sea_p24",
    "current": "normal"
  },
  {
    "source_id": "sea_p28",
    "target_id": "sea_p25",
    "current": "normal"
  },
  {
    "source_id": "sea_p30",
    "target_id": "sea_p28",
    "current": "normal"
  },
  {
    "source_id": "sea_p31",
    "target_id": "sea_a36",
    "current": "normal"
  },
  {
    "source_id": "sea_p31",
    "target_id": "sea_p30",
    "current": "normal"
  },
  {
    "source_id": "sea_p35",
    "target_id": "sea_p34",
    "current": "normal"
  },
  {
    "source_id": "sea_p43",
    "target_id": "sea_p34",
    "current": "normal"
  },
  {
    "source_id": "sea_p43",
    "target_id": "sea_p42",
    "current": "normal"
  },
  {
    "source_id": "sea_p44",
    "target_id": "sea_p42",
    "current": "normal"
  },
  {
    "source_id": "sea_p44",
    "target_id": "sea_p43",
    "current": "normal"
  },
  {
    "source_id": "sea_p45",
    "target_id": "sea_p34",
    "current": "normal"
  },
  {
    "source_id": "sea_p45",
    "target_id": "sea_p43",
    "current": "normal"
  },
  {
    "source_id": "sea_p46",
    "target_id": "sea_p43",
    "current": "normal"
  },
  {
    "source_id": "sea_p46",
    "target_id": "sea_p44",
    "current": "normal"
  },
  {
    "source_id": "sea_p46",
    "target_id": "sea_p45",
    "current": "normal"
  },
  {
    "source_id": "sea_p47",
    "target_id": "sea_p46",
    "current": "normal"
  },
  {
    "source_id": "sea_p50",
    "target_id": "sea_i12",
    "current": "normal"
  },
  {
    "source_id": "sea_p50",
    "target_id": "sea_p42",
    "current": "normal"
  },
  {
    "source_id": "sea_p51",
    "target_id": "sea_p42",
    "current": "normal"
  },
  {
    "source_id": "sea_p51",
    "target_id": "sea_p44",
    "current": "normal"
  },
  {
    "source_id": "sea_p51",
    "target_id": "sea_p50",
    "current": "normal"
  },
  {
    "source_id": "sea_p52",
    "target_id": "sea_p44",
    "current": "normal"
  },
  {
    "source_id": "sea_p52",
    "target_id": "sea_p50",
    "current": "normal"
  },
  {
    "source_id": "sea_p53",
    "target_id": "sea_p44",
    "current": "normal"
  },
  {
    "source_id": "sea_p53",
    "target_id": "sea_p46",
    "current": "normal"
  },
  {
    "source_id": "sea_p54",
    "target_id": "sea_p46",
    "current": "normal"
  },
  {
    "source_id": "sea_p59",
    "target_id": "sea_p50",
    "current": "normal"
  },
  {
    "source_id": "sea_p6",
    "target_id": "sea_p5",
    "current": "normal"
  },
  {
    "source_id": "sea_p60",
    "target_id": "sea_p59",
    "current": "normal"
  },
  {
    "source_id": "sea_p61",
    "target_id": "sea_p60",
    "current": "normal"
  },
  {
    "source_id": "sea_p62",
    "target_id": "sea_p61",
    "current": "normal"
  },
  {
    "source_id": "sea_p63",
    "target_id": "sea_p62",
    "current": "normal"
  },
  {
    "source_id": "sea_p64",
    "target_id": "sea_p63",
    "current": "normal"
  },
  {
    "source_id": "sea_p65",
    "target_id": "sea_p64",
    "current": "normal"
  },
  {
    "source_id": "sea_p68",
    "target_id": "sea_p65",
    "current": "normal"
  },
  {
    "source_id": "sea_p69",
    "target_id": "sea_p68",
    "current": "normal"
  },
  {
    "source_id": "sea_p8",
    "target_id": "sea_p2",
    "current": "normal"
  },
  {
    "source_id": "sea_p9",
    "target_id": "sea_p2",
    "current": "normal"
  },
  {
    "source_id": "sea_p9",
    "target_id": "sea_p3",
    "current": "normal"
  },
  {
    "source_id": "sea_p9",
    "target_id": "sea_p8",
    "current": "normal"
  }
]
```

**Proposed:**

sea on every retained ordinary sea-to-sea transition

**Evidence:**

- data/structural_findings.json checks sea_edge_land_terrain
- Current JSON schema uses terrain=sea for sea nodes and reviewed sea-to-sea approaches

**Scope / dependency:** This is representation consistency. Regional deletion proposals take precedence: do not preserve a false adjacency to normalize it. No claim that these 93 physical connections all exist.

## WG-002 — Give the three printed Somaliland minor ports distinct IDs and their correct sea accesses

**Field:** `naval_facilities / naval_facility_ids` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_british_somaliland`, `land_french_somaliland`, `land_italian_somaliland`

**Current:**

```json
{
  "id": "facility_somaliland_minor_port",
  "records": [
    {
      "land": "land_british_somaliland",
      "kind": "minor_port",
      "sea": "sea_i4",
      "source": "edge"
    },
    {
      "land": "land_french_somaliland",
      "kind": "minor_port",
      "sea": "sea_i5",
      "source": "edge"
    },
    {
      "land": "land_italian_somaliland",
      "kind": "minor_port",
      "sea": "sea_i4",
      "source": "edge"
    }
  ]
}
```

**Proposed:**

```json
{
  "retire_shared_id": "facility_somaliland_minor_port",
  "verified_facilities": [
    {
      "id": "facility_british_somaliland_minor_port",
      "land_id": "land_british_somaliland",
      "type": "minor_port",
      "sea_accesses": [
        "sea_i4"
      ]
    },
    {
      "id": "facility_french_somaliland_minor_port",
      "land_id": "land_french_somaliland",
      "type": "minor_port",
      "sea_accesses": [
        "sea_i4"
      ]
    },
    {
      "id": "facility_italian_somaliland_minor_port",
      "land_id": "land_italian_somaliland",
      "type": "minor_port",
      "sea_accesses": [
        "sea_i3"
      ]
    }
  ]
}
```

**Evidence:**

- data/structural_findings.json ST-0117
- evidence/ea_east_africa.png: three separate white-anchor symbols; French and British Somaliland face I4, Italian Somaliland faces I3.
- data/europe_africa_middle_east_findings.json EA-333, EA-334, EA-335

**Scope / dependency:** These are three separately printed physical facilities, not just renamed old claims. Move the French port access from the old I5 claim to I4 and Italian port access from the old I4 claim to I3; each valid coast direction references the same physical ID. No extra port is implied on another coast of the same territory.

## WG-003 — Remove the nonexistent French Morocco port and give the Spanish Morocco port its own ID

**Field:** `naval_facilities / naval_facility_ids` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_french_morocco`, `land_spanish_morocco`

**Current:**

```json
{
  "id": "facility_morocco_minor_port",
  "records": [
    {
      "land": "land_french_morocco",
      "kind": "minor_port",
      "sea": "sea_a28",
      "source": "edge"
    },
    {
      "land": "land_spanish_morocco",
      "kind": "minor_port",
      "sea": "sea_a28",
      "source": "edge"
    }
  ]
}
```

**Proposed:**

```json
{
  "remove_facilities_from": [
    "land_french_morocco"
  ],
  "rename_surviving_facility": {
    "land_id": "land_spanish_morocco",
    "type": "minor_port",
    "old_id": "facility_morocco_minor_port",
    "new_id": "facility_spanish_morocco_minor_port",
    "sea_accesses": [
      "sea_a44"
    ]
  },
  "coast_corrections": "Apply EA-369 and EA-370 separately; do not carry the nonexistent French Morocco port onto its corrected A44 coast."
}
```

**Evidence:**

- data/structural_findings.json ST-0118
- tools/build_manual_map_json.py zone_name_part() and normalize_naval_facility_instances()
- User correction, 6 October 2026: there is no port in French Morocco.
- evidence/ea_north_africa.png: no French Morocco port; white minor-port anchor on Spanish Morocco.

**Scope / dependency:** The old proposal was a conditional naming example, but misleadingly listed a new French Morocco port ID. That example is withdrawn. French Morocco has no printed port to rename. Only the real Spanish Morocco minor port receives its own ID. This is a proposal in the audit, not a production map edit. The Spanish Morocco minor port faces A44 only; its separate M2 coastline does not imply another port or another access of this port.

## WG-004 — Replace the shared Egypt port ID with the actual printed facilities

**Field:** `naval_facilities / naval_facility_ids` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_lower_egypt`, `land_upper_egypt`, `land_western_egypt`

**Current:**

```json
{
  "id": "facility_egypt_minor_port",
  "records": [
    {
      "land": "land_lower_egypt",
      "kind": "minor_port",
      "sea": "sea_i5",
      "source": "edge"
    },
    {
      "land": "land_lower_egypt",
      "kind": "minor_port",
      "sea": "sea_m9",
      "source": "edge"
    },
    {
      "land": "land_upper_egypt",
      "kind": "minor_port",
      "sea": "sea_i5",
      "source": "edge"
    },
    {
      "land": "land_western_egypt",
      "kind": "minor_port",
      "sea": "sea_m9",
      "source": "edge"
    }
  ]
}
```

**Proposed:**

```json
{
  "retire_shared_id": "facility_egypt_minor_port",
  "verified_facilities": [
    {
      "id": "facility_western_egypt_major_port",
      "land_id": "land_western_egypt",
      "type": "major_port",
      "sea_accesses": [
        "sea_m8"
      ],
      "source_finding": "EA-328"
    },
    {
      "id": "facility_lower_egypt_major_dockyard",
      "land_id": "land_lower_egypt",
      "type": "major_dockyard",
      "sea_accesses": [
        "sea_m8"
      ],
      "source_finding": "EA-329"
    },
    {
      "id": "facility_lower_egypt_major_port",
      "land_id": "land_lower_egypt",
      "type": "major_port",
      "sea_accesses": [
        "sea_i5"
      ],
      "source_finding": "EA-330"
    }
  ],
  "remove_unprinted_facilities": [
    {
      "land_id": "land_upper_egypt",
      "old_type": "minor_port",
      "old_sea_access": "sea_i5",
      "source_finding": "EA-331"
    }
  ]
}
```

**Evidence:**

- data/structural_findings.json ST-0119
- tools/build_manual_map_json.py zone_name_part() and normalize_naval_facility_instances()
- data/europe_africa_middle_east_findings.json EA-328, EA-329, EA-330 and EA-331
- evidence/ea_north_africa.png and evidence/ea_arabia.png: printed naval symbols and their territory/coast positions.

**Scope / dependency:** The earlier territory-to-minor-port-ID dictionary was a naming illustration, not a verified facility roster; it is withdrawn. Correct facility existence, type and coast first, then give each physical instance its own ID. Lower Egypt has two different printed facilities, so those two records also need different IDs. Upper Egypt has no printed port. Update references on both directions of each valid coast edge, remove old facility attributes from replaced M9 edges, and do not create an Upper Egypt port. This reconciles WG-004 with EA-328–331; it adds no independent facilities beyond those regional proposals.

## WG-005 — Remove the nonexistent Southwest Africa port and correct South Africa’s printed major port

**Field:** `naval_facilities / naval_facility_ids` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_south_africa`, `land_southwest_africa`

**Current:**

```json
{
  "id": "facility_africa_minor_port",
  "records": [
    {
      "land": "land_south_africa",
      "kind": "minor_port",
      "sea": "sea_a40",
      "source": "edge"
    },
    {
      "land": "land_southwest_africa",
      "kind": "minor_port",
      "sea": "sea_a39",
      "source": "edge"
    }
  ]
}
```

**Proposed:**

```json
{
  "retire_shared_id": "facility_africa_minor_port",
  "remove_facilities_from": [
    "land_southwest_africa"
  ],
  "verified_facilities": [
    {
      "id": "facility_south_africa_major_port",
      "land_id": "land_south_africa",
      "type": "major_port",
      "sea_accesses": [
        "sea_i1"
      ],
      "source_finding": "EA-338"
    }
  ]
}
```

**Evidence:**

- data/structural_findings.json ST-0120
- User correction, 6 October 2026: there is no port in Southwest Africa.
- evidence/ea_south_africa.png: Southwest Africa has no naval symbol; South Africa has a blue major-port anchor on its I1 coast.
- data/europe_africa_middle_east_findings.json EA-338

**Scope / dependency:** Withdraw the earlier conditional ID-renaming example: it would retain a phantom Southwest Africa facility and the wrong South Africa type. Delete the Southwest Africa naval-facility claim; keep its real coast. Replace the South Africa minor-port claim with the actual major port on I1. Reconcile old A39/A40 coast corrections separately, and apply the same facility ID to both directions of its valid I1 coast. These are audit proposals only.

## WG-006 — Remove spurious victory-city status from Denmark

**Field:** `is_victory_city` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_denmark`

**Current:**

```json
true
```

**Proposed:**

```json
false
```

**Evidence:**

- Global War 1936 v4.3 Rulebook.pdf, section 3.2, PDF/printed p20

**Scope / dependency:** Keep ordinary city/capital identity separate; this is only the victory-city flag.

## WG-007 — Remove spurious victory-city status from Southern Finland

**Field:** `is_victory_city` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_fin_southern_finland`

**Current:**

```json
true
```

**Proposed:**

```json
false
```

**Evidence:**

- Global War 1936 v4.3 Rulebook.pdf, section 3.2, PDF/printed p20

**Scope / dependency:** Keep ordinary city/capital identity separate; this is only the victory-city flag.

## WG-008 — Remove spurious victory-city status from Warsaw

**Field:** `is_victory_city` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_pol_warsaw`

**Current:**

```json
true
```

**Proposed:**

```json
false
```

**Evidence:**

- Global War 1936 v4.3 Rulebook.pdf, section 3.2, PDF/printed p20

**Scope / dependency:** Keep ordinary city/capital identity separate; this is only the victory-city flag.

## WG-009 — Remove spurious victory-city status from Istanbul

**Field:** `is_victory_city` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_tur_istanbul`

**Current:**

```json
true
```

**Proposed:**

```json
false
```

**Evidence:**

- Global War 1936 v4.3 Rulebook.pdf, section 3.2, PDF/printed p20

**Scope / dependency:** Keep ordinary city/capital identity separate; this is only the victory-city flag.

## WG-010 — Remove spurious victory-city status from Kiev

**Field:** `is_victory_city` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_usr_kiev`

**Current:**

```json
true
```

**Proposed:**

```json
false
```

**Evidence:**

- Global War 1936 v4.3 Rulebook.pdf, section 3.2, PDF/printed p20

**Scope / dependency:** Keep ordinary city/capital identity separate; this is only the victory-city flag.

## WG-011 — Remove spurious victory-city status from Leningrad

**Field:** `is_victory_city` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_usr_leningrad`

**Current:**

```json
true
```

**Proposed:**

```json
false
```

**Evidence:**

- Global War 1936 v4.3 Rulebook.pdf, section 3.2, PDF/printed p20

**Scope / dependency:** Keep ordinary city/capital identity separate; this is only the victory-city flag.

## WG-012 — Mark Calcutta as a victory city

**Field:** `is_victory_city` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_india_calcutta`

**Current:**

```json
false
```

**Proposed:**

```json
true
```

**Evidence:**

- Global War 1936 v4.3 Rulebook.pdf, section 3.2, PDF/printed p20

**Scope / dependency:** Sydney is also required but its missing-node proposal is tracked in the Asia/Pacific report.

## WG-013 — Use printed sea-zone codes as canonical sea labels

**Field:** `name` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `sea_a1`, `sea_a10`, `sea_a11`, `sea_a12`, `sea_a13`, `sea_a14`, `sea_a15`, `sea_a18`, `sea_a19`, `sea_a2`, `sea_a20`, `sea_a21`, `sea_a22`, `sea_a23`, `sea_a24`, `sea_a25`, `sea_a26`, `sea_a28`, `sea_a29`, `sea_a31`, `sea_a33`, `sea_a35`, `sea_a36`, `sea_a38`, `sea_a39`, `sea_a40`, `sea_a44`, `sea_a6`, `sea_a7`, `sea_i1`, `sea_i10`, `sea_i11`, `sea_i12`, `sea_i13`, `sea_i14`, `sea_i2`, `sea_i3`, `sea_i4`, `sea_i5`, `sea_i6`, `sea_i7`, `sea_i8`, `sea_i9`, `sea_m1`, `sea_m10`, `sea_m11`, `sea_m12`, `sea_m2`, `sea_m3`, `sea_m4`, `sea_m5`, `sea_m6`, `sea_m7`, `sea_m8`, `sea_m9`, `sea_p1`, `sea_p10`, `sea_p11`, `sea_p12`, `sea_p13`, `sea_p14`, `sea_p15`, `sea_p16`, `sea_p17`, `sea_p18`, `sea_p2`, `sea_p24`, `sea_p25`, `sea_p26`, `sea_p28`, `sea_p3`, `sea_p30`, `sea_p31`, `sea_p32`, `sea_p33`, `sea_p34`, `sea_p35`, `sea_p36`, `sea_p41`, `sea_p42`, `sea_p43`, `sea_p44`, `sea_p45`, `sea_p46`, `sea_p47`, `sea_p5`, `sea_p50`, `sea_p51`, `sea_p52`, `sea_p53`, `sea_p54`, `sea_p59`, `sea_p6`, `sea_p60`, `sea_p61`, `sea_p62`, `sea_p63`, `sea_p64`, `sea_p65`, `sea_p68`, `sea_p69`, `sea_p7`, `sea_p8`, `sea_p9`

**Current:**

104 hand-authored descriptive sea names

**Proposed:**

Display printed A#/M#/I#/P# code; retain only verified geographic aliases

**Evidence:**

- Global War 1936 v4.3 Rulebook.pdf section 1.2 p10
- Original map image and regional sea-number corrections

**Scope / dependency:** Stable node IDs remain unchanged. This removes unsupported geographic implications from labels, not seas from the map.

## WG-014 — Preserve source review information in the map authoring pipeline

**Field:** `generator confidence/source metadata` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** Global authoring/schema

**Current:**

confidence parameters accepted and discarded; reverse terrain/crossing defaulted

**Proposed:**

Require separate directional source/review state; retain explicit unknown until verified

**Evidence:**

- tools/build_manual_map_json.py link(), link_rail(), link_land(), link_land_sea(), symmetric closure pass

**Scope / dependency:** Authoring proposal. Do not convert unknown terrain/crossings to false/normal or infer source confidence from graph symmetry.

## WG-015 — Replace the Soviet-only rail-gauge heuristic

**Field:** `gauge_change generation` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** Global authoring/schema

**Current:**

True iff exactly one originally Soviet endpoint, for every stored rail

**Proposed:**

Use independently verified printed gauges; compare gauges only on verified rails

**Evidence:**

- Rulebook section 1.6 p10, 11.2.1 p75 and 13.2.8 p98
- tools/build_manual_map_json.py final gauge-change loop

**Scope / dependency:** Brazil/Spain/Finland/Mongolia/Tannu Tuva also appear in broad-gauge construction rules. Existing rail gauges must be checked from the printed board; do not silently apply construction defaults to unaudited rails.

## WG-016 — Add blocking sea references for land_can_baffin_island ↔ land_can_district_of_keewatin

**Field:** `narrow_crossing_sea_zones (both directed land entries)` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_can_baffin_island`, `land_can_district_of_keewatin`, `sea_a1`

**Current:**

```json
null
```

**Proposed:**

```json
[
  "sea_a1"
]
```

**Evidence:**

- Original gw36map.png crop (0, 0, 2250, 1450); evidence/americas_arctic.png
- Rulebook section 1.9 p16
- Americas regional audit narrow-crossing inspection

**Scope / dependency:** Keep existing capacity 1. Labrador–Newfoundland line lies on the A15/A18 boundary; both seas can block it. This does not add or remove ordinary coastal access.

## WG-017 — Add blocking sea references for land_can_labrador ↔ land_can_newfoundland

**Field:** `narrow_crossing_sea_zones (both directed land entries)` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_can_labrador`, `land_can_newfoundland`, `sea_a15`, `sea_a18`

**Current:**

```json
null
```

**Proposed:**

```json
[
  "sea_a15",
  "sea_a18"
]
```

**Evidence:**

- Original gw36map.png crop (0, 0, 2250, 1450); evidence/americas_arctic.png
- Rulebook section 1.9 p16
- Americas regional audit narrow-crossing inspection

**Scope / dependency:** Keep existing capacity 1. Labrador–Newfoundland line lies on the A15/A18 boundary; both seas can block it. This does not add or remove ordinary coastal access.

## WG-018 — Add blocking sea references for land_can_newfoundland ↔ land_can_st_pierre_island

**Field:** `narrow_crossing_sea_zones (both directed land entries)` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_can_newfoundland`, `land_can_st_pierre_island`, `sea_a18`

**Current:**

```json
null
```

**Proposed:**

```json
[
  "sea_a18"
]
```

**Evidence:**

- Original gw36map.png crop (0, 0, 2250, 1450); evidence/americas_arctic.png
- Rulebook section 1.9 p16
- Americas regional audit narrow-crossing inspection

**Scope / dependency:** Keep existing capacity 1. Labrador–Newfoundland line lies on the A15/A18 boundary; both seas can block it. This does not add or remove ordinary coastal access.

## WG-038 — Restore New England to the USA Home Country sidecar

**Field:** `nations.USA.home_country_land_zone_ids` · **Confidence:** high · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_usa_new_england`

**Current:**

```json
[
  "land_usa_appalachia",
  "land_usa_chicago",
  "land_usa_great_lakes",
  "land_usa_great_plains",
  "land_usa_heartlands",
  "land_usa_midwest",
  "land_usa_new_orleans",
  "land_usa_new_york",
  "land_usa_pacific_northwest",
  "land_usa_san_francisco",
  "land_usa_southeastern_united_states",
  "land_usa_southwest_united_states",
  "land_usa_texas",
  "land_usa_the_carolinas",
  "land_usa_the_northeast",
  "land_usa_upper_midwest",
  "land_usa_washington_dc",
  "land_usa_western_united_states"
]
```

**Proposed:**

```json
{
  "add_land_zone_ids": [
    "land_usa_new_england"
  ]
}
```

**Evidence:**

- game_content/rules/Global War 1936 v4.3 Rulebook.pdf p6
- game_content/maps/gw36_nation_home_country.json
- tools/build_nation_home_country_json.py
- game_content/maps/gw36map.png

**Scope / dependency:** New England is contiguous mainland USA on the printed board. Its missing mainland connections cause contiguous_us_home() to omit it. Repair those borders before regenerating; do not let a broken graph define national Home Country.

## WG-042 — Rebuild Soviet Home Country from the repaired printed Soviet roster

**Field:** `nations.USSR.home_country_land_zone_ids` · **Confidence:** high_for_selection_rule · **Severity:** major

**Regional context:** [global](generation_and_integrity.md)

**Nodes:** `land_usr_zuryenia`, `land_usr_ural`, `land_usr_orenburg`, `land_usr_western_kazakhstan`, `land_usr_central_kazakhstan`, `land_usr_turkmenistan`, `land_usr_vyatka`, `land_usr_yugria`, `land_usr_samoyedia`, `land_usr_lower_tunguska`, `land_usr_sibir`, `land_usr_tobolsk`, `land_usr_yenisei`, `land_usr_evenkiland`, `land_usr_western_yakutia`, `land_usr_northern_yakutia`, `land_usr_eastern_yakutia`, `land_usr_chukotka`, `land_usr_big_diomede_island`

**Current:**

The sidecar inherits the incomplete 43-node Soviet owner selection from the current world map

**Proposed:**

```json
{
  "selection": "All originally Soviet-roundel land zones in the corrected complete world roster",
  "include_missing_zones_from": "AP-001–AP-019",
  "exclude_wrong_roundel": "land_usr_south_sakhalin"
}
```

**Evidence:**

- game_content/rules/Global War 1936 v4.3 Rulebook.pdf p6
- game_content/maps/gw36_nation_home_country.json
- tools/build_nation_home_country_json.py
- regions/asia_pacific.md

**Scope / dependency:** Do not hard-code the current list as complete. Keep Home Country in its existing rules-geography sidecar, with references validated after missing Siberian zones are added. Prefixes and current controller alone do not prove a printed Soviet roundel.

## AM-001 — Chicago ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_chicago`

**Current:**

```json
2
```

**Proposed:**

```json
3
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-002 — New York ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_york`

**Current:**

```json
4
```

**Proposed:**

```json
5
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-003 — Washington, D.C. ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_washington_dc`

**Current:**

```json
5
```

**Proposed:**

```json
8
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-004 — San Francisco ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_san_francisco`

**Current:**

```json
4
```

**Proposed:**

```json
6
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-005 — Southwest United States ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_southwest_united_states`

**Current:**

```json
2
```

**Proposed:**

```json
3
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-006 — Great Plains ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_great_plains`

**Current:**

```json
3
```

**Proposed:**

```json
2
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-007 — Puerto Rico ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_puerto_rico`

**Current:**

```json
0
```

**Proposed:**

```json
1
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-008 — Cuba ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_cuba`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-009 — Suriname ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_suriname`

**Current:**

```json
0
```

**Proposed:**

```json
1
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-010 — Pampas ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_pampas`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Printed red IPP square; absence of a red value is zero for Cuba/Pampas. Great Plains value is at the right map edge.

## AM-011 — Guyana name

**Field:** `name` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_guyana`

**Current:**

Guyana

**Proposed:**

British Guiana

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

## AM-012 — Guyana original_owner

**Field:** `original_owner` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_guyana`

**Current:**

Guyana

**Proposed:**

United Kingdom

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** British roundel printed; preserve or migrate existing ID deliberately.

## AM-013 — Suriname original_owner

**Field:** `original_owner` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_suriname`

**Current:**

Suriname

**Proposed:**

Netherlands

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Dutch tricolor/roundel is printed; the current sovereign owner string is incorrect for this map.

## AM-014 — Panama original_owner

**Field:** `original_owner` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_panama`

**Current:**

Panama

**Proposed:**

United States

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** US roundel printed in Panama; the current Panama owner is incorrect for July 1936 map.

## AM-015 — Rio Grande name

**Field:** `name` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_rio_grande`

**Current:**

Rio Grande

**Proposed:**

Norte Grande

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** The printed Argentina tile is NORTE GRANDE, not Rio Grande; retain ID with alias or perform an explicit migration.

## AM-016 — Amazon Jungle name

**Field:** `name` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`

**Current:**

Amazon Jungle

**Proposed:**

Amazonas

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** AMAZONAS is the playable tile label; AMAZON (IMPASSABLE) is a distinct internal artwork region.

## AM-017 — Chicago is_city

**Field:** `is_city` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_chicago`

**Current:**

```json
false
```

**Proposed:**

```json
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Circular/semi-circular land-zone border; rulebook §1.7.7, p12–13 distinguishes city zones from city dots.

## AM-018 — New Orleans is_city

**Field:** `is_city` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_orleans`

**Current:**

```json
false
```

**Proposed:**

```json
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Circular/semi-circular land-zone border; rulebook §1.7.7, p12–13 distinguishes city zones from city dots.

## AM-019 — Pacific Northwest terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_pacific_northwest`

**Current:**

forest

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}

**Scope / dependency:** Distinct ridge artwork surrounds the roundel. The Pacific Northwest green ridges are not the discrete tree symbol used for forest/jungle. Confirmed by full visual check of the corresponding glossary terrain column.

## AM-020 — Southwest United States terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_southwest_united_states`

**Current:**

desert

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}

**Scope / dependency:** Distinct ridge artwork surrounds the roundel. The Pacific Northwest green ridges are not the discrete tree symbol used for forest/jungle. Confirmed by full visual check of the corresponding glossary terrain column.

## AM-021 — San Francisco terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_san_francisco`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}

**Scope / dependency:** Distinct ridge artwork surrounds the roundel. The Pacific Northwest green ridges are not the discrete tree symbol used for forest/jungle. Confirmed by full visual check of the corresponding glossary terrain column.

## AM-022 — The Northeast terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_the_northeast`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [250, 1370, 1000, 1900], "crop": "docs/map_audits/full_world/evidence/americas_usa_northeast.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}

**Scope / dependency:** Ridge artwork covers the roundel and interior. All directional approaches need individual tracing. Confirmed by full visual check of the corresponding glossary terrain column.

## AM-023 — Caatinga terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_caatinga`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [850, 2890, 1750, 3770], "crop": "docs/map_audits/full_world/evidence/americas_brazil_coasts.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** The roundel lies in ridge artwork, continuous with the ridge-filled interior; city status remains independent. Confirmed by full visual check of the corresponding glossary terrain column.

## AM-024 — Rio de Janeiro terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_rio_de_janeiro`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [850, 2890, 1750, 3770], "crop": "docs/map_audits/full_world/evidence/americas_brazil_coasts.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** The roundel lies in ridge artwork, continuous with the ridge-filled interior; city status remains independent. Confirmed by full visual check of the corresponding glossary terrain column.

## AM-025 — Resolve intrinsic terrain from complete glossary: Colombia

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_colombia`

**Current:**

mountain

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Original board-only uncertainty resolved by complete glossary p6 transcription. This individual record overlaps the grouped AM-230 patch; apply once. Explicit directional modifiers remain in directional_terrain.json.

## AM-026 — Resolve intrinsic terrain from complete glossary: Ecuador

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_ecuador`

**Current:**

mountain

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Original board-only uncertainty resolved by complete glossary p6 transcription. This individual record overlaps the grouped AM-230 patch; apply once. Explicit directional modifiers remain in directional_terrain.json.

## AM-027 — Resolve intrinsic terrain from complete glossary: Bolivia

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_bolivia`

**Current:**

mountain

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [280, 2900, 930, 3550], "crop": "docs/map_audits/full_world/evidence/americas_andes_amazon_detail.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Original board-only uncertainty resolved by complete glossary p6 transcription. This individual record overlaps the grouped AM-230 patch; apply once. Explicit directional modifiers remain in directional_terrain.json.

## AM-028 — Resolve intrinsic terrain from complete glossary: Pampas

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_pampas`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Original board-only uncertainty resolved by complete glossary p6 transcription. This individual record overlaps the grouped AM-230 patch; apply once. Explicit directional modifiers remain in directional_terrain.json.

## AM-029 — Resolve glossary-directed approach: Chile to Patagonia

**Field:** `border_terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_chile`, `land_patagonia`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Former generic terrain uncertainty is resolved by glossary p6: intrinsic terrain is normal and this explicit incoming modifier applies. Overlaps grouped AM-233; apply once.

## AM-030 — Resolve glossary-directed approach: Pampas to Rio Grande

**Field:** `border_terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_pampas`, `land_rio_grande`

**Current:**

normal

**Proposed:**

jungle

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Former generic terrain uncertainty is resolved by glossary p6: intrinsic terrain is normal and this explicit incoming modifier applies. Overlaps grouped AM-233; apply once.

## AM-031 — Resolve glossary-directed approach: Central America to Eastern Mexico

**Field:** `border_terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_central_america`, `land_mex_eastern_mexico`

**Current:**

normal

**Proposed:**

jungle

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Former generic terrain uncertainty is resolved by glossary p6: intrinsic terrain is normal and this explicit incoming modifier applies. Overlaps grouped AM-233; apply once.

## AM-032 — Resolve intrinsic terrain from complete glossary: Central America

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_central_america`

**Current:**

jungle

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Original board-only uncertainty resolved by complete glossary p6 transcription. This individual record overlaps the grouped AM-230 patch; apply once. Explicit directional modifiers remain in directional_terrain.json.

## AM-057 — land_mex_eastern_mexico ↔ land_central_america

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_mex_eastern_mexico`, `land_central_america`

**Current:**

```json
{
  "land_mex_eastern_mexico -> land_central_america": true,
  "land_central_america -> land_mex_eastern_mexico": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-058 — land_central_america ↔ land_panama

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_central_america`, `land_panama`

**Current:**

```json
{
  "land_central_america -> land_panama": true,
  "land_panama -> land_central_america": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-059 — land_colombia ↔ land_panama

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_colombia`, `land_panama`

**Current:**

```json
{
  "land_colombia -> land_panama": true,
  "land_panama -> land_colombia": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-060 — land_colombia ↔ land_venezuela

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_colombia`, `land_venezuela`

**Current:**

```json
{
  "land_colombia -> land_venezuela": true,
  "land_venezuela -> land_colombia": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-061 — land_colombia ↔ land_ecuador

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_colombia`, `land_ecuador`

**Current:**

```json
{
  "land_colombia -> land_ecuador": true,
  "land_ecuador -> land_colombia": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-062 — land_venezuela ↔ land_guyana

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_venezuela`, `land_guyana`

**Current:**

```json
{
  "land_venezuela -> land_guyana": true,
  "land_guyana -> land_venezuela": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-063 — land_guyana ↔ land_suriname

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_guyana`, `land_suriname`

**Current:**

```json
{
  "land_guyana -> land_suriname": true,
  "land_suriname -> land_guyana": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-064 — land_suriname ↔ land_french_guiana

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_suriname`, `land_french_guiana`

**Current:**

```json
{
  "land_suriname -> land_french_guiana": true,
  "land_french_guiana -> land_suriname": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-065 — land_venezuela ↔ land_brazil_amazon_jungle

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_venezuela`, `land_brazil_amazon_jungle`

**Current:**

```json
{
  "land_venezuela -> land_brazil_amazon_jungle": true,
  "land_brazil_amazon_jungle -> land_venezuela": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-066 — land_ecuador ↔ land_peru

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_ecuador`, `land_peru`

**Current:**

```json
{
  "land_ecuador -> land_peru": true,
  "land_peru -> land_ecuador": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-067 — land_peru ↔ land_brazil_amazon_jungle

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_peru`, `land_brazil_amazon_jungle`

**Current:**

```json
{
  "land_peru -> land_brazil_amazon_jungle": true,
  "land_brazil_amazon_jungle -> land_peru": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-068 — land_bolivia ↔ land_paraguay

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_bolivia`, `land_paraguay`

**Current:**

```json
{
  "land_bolivia -> land_paraguay": true,
  "land_paraguay -> land_bolivia": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-069 — land_bolivia ↔ land_brazil_pampas

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_bolivia`, `land_brazil_pampas`

**Current:**

```json
{
  "land_bolivia -> land_brazil_pampas": true,
  "land_brazil_pampas -> land_bolivia": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-070 — land_brazil_amazon_jungle ↔ land_brazil_caatinga

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `land_brazil_caatinga`

**Current:**

```json
{
  "land_brazil_amazon_jungle -> land_brazil_caatinga": true,
  "land_brazil_caatinga -> land_brazil_amazon_jungle": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-071 — land_brazil_caatinga ↔ land_brazil_rio_de_janeiro

**Field:** `railway_connection` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_caatinga`, `land_brazil_rio_de_janeiro`

**Current:**

```json
{
  "land_brazil_caatinga -> land_brazil_rio_de_janeiro": true,
  "land_brazil_rio_de_janeiro -> land_brazil_caatinga": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** No dashed railroad joins these territories in the native map. Any river-route connectivity must remain a separate has_river fact.

## AM-072 — land_peru ↔ land_brazil_amazon_jungle

**Field:** `passable` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_peru`, `land_brazil_amazon_jungle`

**Current:**

```json
{
  "land_peru -> land_brazil_amazon_jungle": true,
  "land_brazil_amazon_jungle -> land_peru": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [280, 2900, 930, 3550], "crop": "docs/map_audits/full_world/evidence/americas_andes_amazon_detail.png"}

**Scope / dependency:** The border enters the hatched AMAZON (IMPASSABLE) region. Rulebook §1.7 p11 forbids land entry; air transit and special river handling must not be conflated with a normal land edge.

## AM-074 — land_colombia ↔ land_venezuela

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_colombia`, `land_venezuela`

**Current:**

```json
{
  "land_colombia -> land_venezuela": true,
  "land_venezuela -> land_colombia": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-075 — land_venezuela ↔ land_guyana

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_venezuela`, `land_guyana`

**Current:**

```json
{
  "land_venezuela -> land_guyana": true,
  "land_guyana -> land_venezuela": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-076 — land_guyana ↔ land_suriname

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_guyana`, `land_suriname`

**Current:**

```json
{
  "land_guyana -> land_suriname": true,
  "land_suriname -> land_guyana": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-077 — land_suriname ↔ land_french_guiana

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_suriname`, `land_french_guiana`

**Current:**

```json
{
  "land_suriname -> land_french_guiana": true,
  "land_french_guiana -> land_suriname": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-078 — land_paraguay ↔ land_brazil_pampas

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_paraguay`, `land_brazil_pampas`

**Current:**

```json
{
  "land_paraguay -> land_brazil_pampas": true,
  "land_brazil_pampas -> land_paraguay": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-079 — land_paraguay ↔ land_rio_grande

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_paraguay`, `land_rio_grande`

**Current:**

```json
{
  "land_paraguay -> land_rio_grande": true,
  "land_rio_grande -> land_paraguay": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-080 — land_brazil_pampas ↔ land_rio_grande

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_pampas`, `land_rio_grande`

**Current:**

```json
{
  "land_brazil_pampas -> land_rio_grande": true,
  "land_rio_grande -> land_brazil_pampas": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-081 — land_brazil_pampas ↔ land_uruguay

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_pampas`, `land_uruguay`

**Current:**

```json
{
  "land_brazil_pampas -> land_uruguay": true,
  "land_uruguay -> land_brazil_pampas": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-082 — land_uruguay ↔ land_buenos_aires

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_uruguay`, `land_buenos_aires`

**Current:**

```json
{
  "land_uruguay -> land_buenos_aires": true,
  "land_buenos_aires -> land_uruguay": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-083 — land_buenos_aires ↔ land_rio_grande

**Field:** `river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_buenos_aires`, `land_rio_grande`

**Current:**

```json
{
  "land_buenos_aires -> land_rio_grande": true,
  "land_rio_grande -> land_buenos_aires": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** No blue river artwork on these directed routes. Coastlines and ordinary borders are not river-crossing penalties.

## AM-103 — Correct coastal sea IDs: Alaska

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_alaska`, `sea_p1`, `sea_p5`, `sea_p6`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_p1",
  "sea_p5",
  "sea_p6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [8500, 0, 9900, 1460], "crop": "docs/map_audits/full_world/evidence/americas_alaska.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_alaska_coasts.png", "rectangle": [8680, 575, 9250, 930]}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: no printed naval facilities. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-104 — Correct coastal sea IDs: Southeast Alaska

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_southeast_alaska`, `sea_p6`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_p6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [8500, 0, 9900, 1460], "crop": "docs/map_audits/full_world/evidence/americas_alaska.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: no printed naval facilities. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-105 — Correct coastal sea IDs: Pacific Northwest

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_pacific_northwest`, `sea_p13`, `sea_p6`

**Current:**

```json
[
  "sea_p6"
]
```

**Proposed:**

```json
[
  "sea_p13"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_shipyard. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-106 — Correct coastal sea IDs: San Francisco

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_san_francisco`, `sea_p25`, `sea_p28`

**Current:**

```json
[
  "sea_p28"
]
```

**Proposed:**

```json
[
  "sea_p25"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: major_shipyard. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-107 — Correct coastal sea IDs: Southwest United States

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_southwest_united_states`, `sea_p25`, `sea_p30`

**Current:**

```json
[
  "sea_p30"
]
```

**Proposed:**

```json
[
  "sea_p25"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: major_shipyard, seaplane_base. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-108 — Correct coastal sea IDs: Western Mexico

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_mex_western_mexico`, `sea_p30`, `sea_p31`

**Current:**

```json
[
  "sea_p30",
  "sea_p31"
]
```

**Proposed:**

```json
[
  "sea_p31"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: no printed naval facilities. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-109 — Correct coastal sea IDs: Eastern Mexico

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_mex_eastern_mexico`, `sea_a36`, `sea_a40`, `sea_p76`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_a36",
  "sea_a40",
  "sea_p76"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-110 — Correct coastal sea IDs: Central America

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_central_america`, `sea_a40`, `sea_p76`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_a40",
  "sea_p76"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: no printed naval facilities. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-111 — Correct coastal sea IDs: Panama

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_panama`, `sea_a36`, `sea_a40`, `sea_p31`, `sea_p76`

**Current:**

```json
[
  "sea_a36",
  "sea_p31"
]
```

**Proposed:**

```json
[
  "sea_a40",
  "sea_p76"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-112 — Correct coastal sea IDs: New England

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_england`, `sea_a25`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_a25"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_shipyard. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-113 — Correct coastal sea IDs: Washington, D.C.

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_washington_dc`, `sea_a25`, `sea_a26`, `sea_a30`

**Current:**

```json
[
  "sea_a26"
]
```

**Proposed:**

```json
[
  "sea_a30"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [480, 1580, 980, 2140], "crop": "docs/map_audits/full_world/evidence/americas_usa_dc_coast.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_dc_ne_boundaries.png", "rectangle": [500, 1620, 850, 1900]}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: major_shipyard. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-114 — Correct coastal sea IDs: The Carolinas

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_the_carolinas`, `sea_a26`, `sea_a30`

**Current:**

```json
[
  "sea_a26"
]
```

**Proposed:**

```json
[
  "sea_a30"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: major_shipyard, seaplane_base. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-115 — Correct coastal sea IDs: Southeastern United States

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_southeastern_united_states`, `sea_a30`, `sea_a31`, `sea_a36`, `sea_a37`

**Current:**

```json
[
  "sea_a31"
]
```

**Proposed:**

```json
[
  "sea_a30",
  "sea_a36",
  "sea_a37"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_florida_cuba.png", "rectangle": [400, 2110, 890, 2610]}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: seaplane_base. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-116 — Correct coastal sea IDs: Texas

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_texas`, `sea_a36`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_a36"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_shipyard, major_port, seaplane_base. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-117 — Correct coastal sea IDs: Cuba

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_cuba`, `sea_a36`, `sea_a37`, `sea_a40`

**Current:**

```json
[
  "sea_a36"
]
```

**Proposed:**

```json
[
  "sea_a36",
  "sea_a37",
  "sea_a40"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_florida_cuba.png", "rectangle": [400, 2110, 890, 2610]}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: major_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-118 — Correct coastal sea IDs: Puerto Rico

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_puerto_rico`, `sea_a36`, `sea_a41`

**Current:**

```json
[
  "sea_a36"
]
```

**Proposed:**

```json
[
  "sea_a41"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: seaplane_base. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-119 — Correct coastal sea IDs: Colombia

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_colombia`, `sea_a36`, `sea_a40`, `sea_p76`

**Current:**

```json
[
  "sea_a36"
]
```

**Proposed:**

```json
[
  "sea_a40",
  "sea_p76"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-120 — Correct coastal sea IDs: Venezuela

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_venezuela`, `sea_a36`, `sea_a40`, `sea_a41`

**Current:**

```json
[
  "sea_a36"
]
```

**Proposed:**

```json
[
  "sea_a40",
  "sea_a41"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: major_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-121 — Correct coastal sea IDs: Guyana

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_guyana`, `sea_a38`, `sea_a41`

**Current:**

```json
[
  "sea_a38"
]
```

**Proposed:**

```json
[
  "sea_a41"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-122 — Correct coastal sea IDs: Suriname

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_suriname`, `sea_a38`, `sea_a41`

**Current:**

```json
[
  "sea_a38"
]
```

**Proposed:**

```json
[
  "sea_a41"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: no printed naval facilities. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-123 — Correct coastal sea IDs: French Guiana

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_french_guiana`, `sea_a38`, `sea_a41`

**Current:**

```json
[
  "sea_a38"
]
```

**Proposed:**

```json
[
  "sea_a41"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-124 — Correct coastal sea IDs: Amazon Jungle

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `sea_a41`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_a41"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [850, 2890, 1750, 3770], "crop": "docs/map_audits/full_world/evidence/americas_brazil_coasts.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_amazon_coast.png", "rectangle": [790, 2940, 1110, 3260]}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: no printed naval facilities. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-125 — Correct coastal sea IDs: Caatinga

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_caatinga`, `sea_a38`, `sea_a45`, `sea_a47`

**Current:**

```json
[
  "sea_a38"
]
```

**Proposed:**

```json
[
  "sea_a45",
  "sea_a47"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [850, 2890, 1750, 3770], "crop": "docs/map_audits/full_world/evidence/americas_brazil_coasts.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_port, seaplane_base. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-126 — Correct coastal sea IDs: Rio de Janeiro

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_rio_de_janeiro`, `sea_a39`, `sea_a47`

**Current:**

```json
[
  "sea_a39"
]
```

**Proposed:**

```json
[
  "sea_a47"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [850, 2890, 1750, 3770], "crop": "docs/map_audits/full_world/evidence/americas_brazil_coasts.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: major_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-127 — Correct coastal sea IDs: Pampas

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_pampas`, `sea_a39`, `sea_a47`

**Current:**

```json
[
  "sea_a39"
]
```

**Proposed:**

```json
[
  "sea_a47"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: no printed naval facilities. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-128 — Correct coastal sea IDs: Uruguay

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_uruguay`, `sea_a39`, `sea_a47`

**Current:**

```json
[
  "sea_a39"
]
```

**Proposed:**

```json
[
  "sea_a47"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: major_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-129 — Correct coastal sea IDs: Buenos Aires

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_buenos_aires`, `sea_a40`, `sea_a49`

**Current:**

```json
[
  "sea_a40"
]
```

**Proposed:**

```json
[
  "sea_a49"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [430, 3380, 1140, 4090], "crop": "docs/map_audits/full_world/evidence/americas_america_south_borders.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_shipyard. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-130 — Correct coastal sea IDs: Patagonia

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_patagonia`, `sea_a40`, `sea_a49`

**Current:**

```json
[
  "sea_a40"
]
```

**Proposed:**

```json
[
  "sea_a49"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: major_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-131 — Correct coastal sea IDs: Ecuador

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_ecuador`, `sea_p76`, `sea_p77`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_p76",
  "sea_p77"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-132 — Correct coastal sea IDs: Peru

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_peru`, `sea_p77`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_p77"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2750, 1500, 3880], "crop": "docs/map_audits/full_world/evidence/americas_south_north.png"}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_shipyard, major_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-133 — Correct coastal sea IDs: Chile

**Field:** `coastal neighbor IDs` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_chile`, `sea_p31`, `sea_p77`, `sea_p78`

**Current:**

```json
[
  "sea_p31"
]
```

**Proposed:**

```json
[
  "sea_p77",
  "sea_p78",
  "sea_a49"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_chile_tip.png", "rectangle": [280, 4180, 620, 4410]}

**Scope / dependency:** Coastal adjacency proposal is separate from naval facilities. Fresh 2026-10-06 naval re-audit is authoritative for actual physical icons and their sea access: minor_shipyard, major_port. Do not retain, migrate or duplicate a generic old port merely because a new coast edge is added.

## AM-136 — Printed shore facilities: Pacific Northwest–sea_p13

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_pacific_northwest`, `sea_p13`

**Current:**

```json
[
  {
    "sea_id": "sea_p6",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_pacific_northwest_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_shipyard"
  ],
  "naval_facility_ids": [
    "facility_usa_pacific_northwest_minor_shipyard_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_pacific_northwest_minor_shipyard_map_1",
      "type": "minor_shipyard",
      "sea_accesses": [
        "sea_p13"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_british_columbia_20261006.png",
          "rectangle": [
            9470,
            1190,
            9750,
            1530
          ]
        }
      ],
      "notes": "Blue crane on white square, south of the British Columbia boundary and north of Western US. The inland green airfield is excluded from naval inventory."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_british_columbia_20261006.png", "rectangle": [9470, 1190, 9750, 1530]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Blue crane on white square, south of the British Columbia boundary and north of Western US. The inland green airfield is excluded from naval inventory.

## AM-137 — Printed shore facilities: San Francisco–sea_p25

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_san_francisco`, `sea_p25`

**Current:**

```json
[
  {
    "sea_id": "sea_p28",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_san_francisco_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_shipyard"
  ],
  "naval_facility_ids": [
    "facility_usa_san_francisco_major_shipyard_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_san_francisco_major_shipyard_map_1",
      "type": "major_shipyard",
      "sea_accesses": [
        "sea_p25"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png",
          "rectangle": [
            9400,
            1180,
            9900,
            2350
          ]
        }
      ],
      "notes": "White crane on blue square on the San Francisco city-zone coast. A crane is a shipyard, not an anchor port."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. White crane on blue square on the San Francisco city-zone coast. A crane is a shipyard, not an anchor port.

## AM-138 — Printed shore facilities: Southwest United States–sea_p25

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_southwest_united_states`, `sea_p25`

**Current:**

```json
[
  {
    "sea_id": "sea_p30",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_southwest_united_states_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_shipyard",
    "seaplane_base"
  ],
  "naval_facility_ids": [
    "facility_usa_southwest_united_states_major_shipyard_map_1",
    "facility_usa_southwest_united_states_seaplane_base_map_2"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_southwest_united_states_major_shipyard_map_1",
      "type": "major_shipyard",
      "sea_accesses": [
        "sea_p25"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png",
          "rectangle": [
            9400,
            1180,
            9900,
            2350
          ]
        }
      ],
      "notes": "White crane on blue square immediately north of the Mexican border; the P25/P31 sea line meets the coast south of this facility."
    },
    {
      "id": "facility_usa_southwest_united_states_seaplane_base_map_2",
      "type": "seaplane_base",
      "sea_accesses": [
        "sea_p25"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png",
          "rectangle": [
            9400,
            1180,
            9900,
            2350
          ]
        }
      ],
      "notes": "White seaplane on green square on Southwest US coast north of its major shipyard; a separate physical icon."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. White crane on blue square immediately north of the Mexican border; the P25/P31 sea line meets the coast south of this facility. White seaplane on green square on Southwest US coast north of its major shipyard; a separate physical icon.

## AM-140 — Printed shore facilities: New York–sea_a25

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_york`, `sea_a25`

**Current:**

```json
[
  {
    "sea_id": "sea_a25",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_new_york_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_shipyard"
  ],
  "naval_facility_ids": [
    "facility_usa_new_york_major_shipyard_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_new_york_major_shipyard_map_1",
      "type": "major_shipyard",
      "sea_accesses": [
        "sea_a25"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_us_northeast_20261006.png",
          "rectangle": [
            430,
            1490,
            915,
            1930
          ]
        }
      ],
      "notes": "White crane on blue square at the New York coast, north of the city-zone boundary ending at the coast/river strip toward Washington."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_us_northeast_20261006.png", "rectangle": [430, 1490, 915, 1930]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. White crane on blue square at the New York coast, north of the city-zone boundary ending at the coast/river strip toward Washington.

## AM-141 — Printed shore facilities: Washington, D.C.–sea_a30

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_washington_dc`, `sea_a30`

**Current:**

```json
[
  {
    "sea_id": "sea_a26",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_washington_dc_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_shipyard"
  ],
  "naval_facility_ids": [
    "facility_usa_washington_dc_major_shipyard_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_washington_dc_major_shipyard_map_1",
      "type": "major_shipyard",
      "sea_accesses": [
        "sea_a30"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_us_northeast_20261006.png",
          "rectangle": [
            430,
            1490,
            915,
            1930
          ]
        }
      ],
      "notes": "White crane on blue square on Washington city coast, south of the A25/A30 line. No additional A25 facility access is drawn."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_us_northeast_20261006.png", "rectangle": [430, 1490, 915, 1930]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. White crane on blue square on Washington city coast, south of the A25/A30 line. No additional A25 facility access is drawn.

## AM-142 — Printed shore facilities: The Carolinas–sea_a30

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_the_carolinas`, `sea_a30`

**Current:**

```json
[
  {
    "sea_id": "sea_a26",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_the_carolinas_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_shipyard",
    "seaplane_base"
  ],
  "naval_facility_ids": [
    "facility_usa_the_carolinas_major_shipyard_map_1",
    "facility_usa_the_carolinas_seaplane_base_map_2"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_the_carolinas_major_shipyard_map_1",
      "type": "major_shipyard",
      "sea_accesses": [
        "sea_a30"
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
      "notes": "White crane on blue square on Carolinas coast, south of Washington circular border."
    },
    {
      "id": "facility_usa_the_carolinas_seaplane_base_map_2",
      "type": "seaplane_base",
      "sea_accesses": [
        "sea_a30"
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
      "notes": "White seaplane on green square on northern Carolinas coast; separate from the shipyard."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. White crane on blue square on Carolinas coast, south of Washington circular border. White seaplane on green square on northern Carolinas coast; separate from the shipyard.

## AM-143 — Printed shore facilities: Southeastern United States–sea_a36

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_southeastern_united_states`, `sea_a36`

**Current:**

```json
[
  {
    "sea_id": "sea_a31",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_southeastern_united_states_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "seaplane_base"
  ],
  "naval_facility_ids": [
    "facility_usa_southeastern_united_states_seaplane_base_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_southeastern_united_states_seaplane_base_map_1",
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
      "notes": "White seaplane on green square on west Florida/Gulf shore. Neither a port nor an east-coast A30/A37 facility."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_us_gulf_20261006.png", "rectangle": [20, 2080, 620, 2460]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. White seaplane on green square on west Florida/Gulf shore. Neither a port nor an east-coast A30/A37 facility.

## AM-144 — Printed shore facilities: New Orleans–sea_a36

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_orleans`, `sea_a36`

**Current:**

```json
[
  {
    "sea_id": "sea_a36",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_new_orleans_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_shipyard"
  ],
  "naval_facility_ids": [
    "facility_usa_new_orleans_major_shipyard_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_usa_new_orleans_major_shipyard_map_1",
      "type": "major_shipyard",
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
      "notes": "White crane on blue square on the New Orleans city-zone Gulf coast, east of the Mississippi mouth."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png", "rectangle": [9400, 1180, 9900, 2350]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_us_gulf_20261006.png", "rectangle": [20, 2080, 620, 2460]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. White crane on blue square on the New Orleans city-zone Gulf coast, east of the Mississippi mouth.

## AM-147 — Printed shore facilities: Panama–sea_a40

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_panama`, `sea_a40`

**Current:**

```json
[
  {
    "sea_id": "sea_a36",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_panama_minor_port"
    ]
  },
  {
    "sea_id": "sea_p31",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_panama_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_port"
  ],
  "naval_facility_ids": [
    "facility_panama_minor_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_panama_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a40"
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
      "notes": "Plain blue anchor on white square northeast of the canal symbol on the A40 coast. Canal parallel bars are not another facility; no P76 access icon is printed."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_mexico_panama_20261006.png", "rectangle": [0, 2370, 580, 2940]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain blue anchor on white square northeast of the canal symbol on the A40 coast. Canal parallel bars are not another facility; no P76 access icon is printed.

## AM-148 — Printed shore facilities: Colombia–sea_a40

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_colombia`, `sea_a40`

**Current:**

```json
[
  {
    "sea_id": "sea_a36",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_colombia_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_port"
  ],
  "naval_facility_ids": [
    "facility_colombia_minor_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_colombia_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a40"
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
      "notes": "Separate plain blue anchor on white square on northern Colombia east of Panama. No facility symbol on its Pacific coast."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_mexico_panama_20261006.png", "rectangle": [0, 2370, 580, 2940]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Separate plain blue anchor on white square on northern Colombia east of Panama. No facility symbol on its Pacific coast.

## AM-151 — Printed shore facilities: Chile–sea_p77

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_chile`, `sea_p77`

**Current:**

```json
[
  {
    "sea_id": "sea_p31",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_chile_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_shipyard"
  ],
  "naval_facility_ids": [
    "facility_chile_minor_shipyard_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_chile_minor_shipyard_map_1",
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
      "notes": "Blue crane on white square on northern Chile coastline west of Bolivia, north of the P77/P78 line."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_south_atlantic_20261006.png", "rectangle": [290, 3710, 1000, 4410]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_north.png", "rectangle": [0, 2750, 1500, 3880]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Blue crane on white square on northern Chile coastline west of Bolivia, north of the P77/P78 line.

## AM-152 — Printed shore facilities: Chile–sea_p78

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_chile`, `sea_p78`

**Current:**

```json
[
  {
    "sea_id": "sea_p31",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_chile_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_port"
  ],
  "naval_facility_ids": [
    "facility_chile_major_port_map_2"
  ],
  "physical_facilities": [
    {
      "id": "facility_chile_major_port_map_2",
      "type": "major_port",
      "sea_accesses": [
        "sea_p78"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_south_atlantic_20261006.png",
          "rectangle": [
            290,
            3710,
            1000,
            4410
          ]
        }
      ],
      "notes": "Plain white anchor on blue square on southern western Chile shore, well west of the later P78/A49 boundary; do not duplicate onto A49."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_south_atlantic_20261006.png", "rectangle": [290, 3710, 1000, 4410]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_north.png", "rectangle": [0, 2750, 1500, 3880]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain white anchor on blue square on southern western Chile shore, well west of the later P78/A49 boundary; do not duplicate onto A49.

## AM-153 — Printed shore facilities: Venezuela–sea_a41

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_venezuela`, `sea_a41`

**Current:**

```json
[
  {
    "sea_id": "sea_a36",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_venezuela_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_port"
  ],
  "naval_facility_ids": [
    "facility_venezuela_major_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_venezuela_major_port_map_1",
      "type": "major_port",
      "sea_accesses": [
        "sea_a41"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_central.png",
          "rectangle": [
            0,
            2260,
            1470,
            3150
          ]
        }
      ],
      "notes": "Plain white anchor on blue square on northern Venezuela coast, east of the A40/A41 line ending near Colombia/Venezuela; no facility at A40."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain white anchor on blue square on northern Venezuela coast, east of the A40/A41 line ending near Colombia/Venezuela; no facility at A40.

## AM-154 — Printed shore facilities: Guyana–sea_a41

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_guyana`, `sea_a41`

**Current:**

```json
[
  {
    "sea_id": "sea_a38",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_guyana_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_port"
  ],
  "naval_facility_ids": [
    "facility_guyana_minor_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_guyana_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a41"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_guianas_20261006.png",
          "rectangle": [
            630,
            2810,
            985,
            3080
          ]
        }
      ],
      "notes": "Plain blue anchor on white square on British Guiana northern coast, east of the Venezuela border."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_guianas_20261006.png", "rectangle": [630, 2810, 985, 3080]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain blue anchor on white square on British Guiana northern coast, east of the Venezuela border.

## AM-156 — Printed shore facilities: French Guiana–sea_a41

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_french_guiana`, `sea_a41`

**Current:**

```json
[
  {
    "sea_id": "sea_a38",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_guiana_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_port"
  ],
  "naval_facility_ids": [
    "facility_french_guiana_minor_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_french_guiana_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a41"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_guianas_20261006.png",
          "rectangle": [
            630,
            2810,
            985,
            3080
          ]
        }
      ],
      "notes": "Plain blue anchor on white square on French Guiana coast. The symbol is east of the Suriname boundary; Suriname has none."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_guianas_20261006.png", "rectangle": [630, 2810, 985, 3080]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain blue anchor on white square on French Guiana coast. The symbol is east of the Suriname boundary; Suriname has none.

## AM-157 — Printed shore facilities: Cuba–sea_a36

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_cuba`, `sea_a36`

**Current:**

```json
[
  {
    "sea_id": "sea_a36",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_cuba_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_port"
  ],
  "naval_facility_ids": [
    "facility_cuba_major_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_cuba_major_port_map_1",
      "type": "major_port",
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
      "notes": "Plain white anchor on blue square on northwestern Cuba shore. It lies north of the A36/A40 line and west of A36/A37 coast junction; A36 only."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_mexico_panama_20261006.png", "rectangle": [0, 2370, 580, 2940]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain white anchor on blue square on northwestern Cuba shore. It lies north of the A36/A40 line and west of A36/A37 coast junction; A36 only.

## AM-158 — Printed shore facilities: Puerto Rico–sea_a41

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_puerto_rico`, `sea_a41`

**Current:**

```json
[
  {
    "sea_id": "sea_a36",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_rico_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "seaplane_base"
  ],
  "naval_facility_ids": [
    "facility_puerto_rico_seaplane_base_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_puerto_rico_seaplane_base_map_1",
      "type": "seaplane_base",
      "sea_accesses": [
        "sea_a41"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_central.png",
          "rectangle": [
            0,
            2260,
            1470,
            3150
          ]
        }
      ],
      "notes": "White seaplane on green square beside Puerto Rico south shore; no anchor port symbol."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_central.png", "rectangle": [0, 2260, 1470, 3150]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. White seaplane on green square beside Puerto Rico south shore; no anchor port symbol.

## AM-160 — Printed shore facilities: Caatinga–sea_a45

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_caatinga`, `sea_a45`

**Current:**

```json
[
  {
    "sea_id": "sea_a38",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_caatinga_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_port",
    "seaplane_base"
  ],
  "naval_facility_ids": [
    "facility_brazil_caatinga_minor_port_map_1",
    "facility_brazil_caatinga_seaplane_base_map_2"
  ],
  "physical_facilities": [
    {
      "id": "facility_brazil_caatinga_minor_port_map_1",
      "type": "minor_port",
      "sea_accesses": [
        "sea_a45"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_brazil_20261006.png",
          "rectangle": [
            815,
            3050,
            1380,
            3780
          ]
        }
      ],
      "notes": "Plain blue anchor on white square on Caatinga east coast north of the A45/A47 sea boundary."
    },
    {
      "id": "facility_brazil_caatinga_seaplane_base_map_2",
      "type": "seaplane_base",
      "sea_accesses": [
        "sea_a45"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_brazil_20261006.png",
          "rectangle": [
            815,
            3050,
            1380,
            3780
          ]
        }
      ],
      "notes": "White seaplane on green square farther north on Caatinga east coast; physically separate from the port."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_north.png", "rectangle": [0, 2750, 1500, 3880]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_brazil_20261006.png", "rectangle": [815, 3050, 1380, 3780]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain blue anchor on white square on Caatinga east coast north of the A45/A47 sea boundary. White seaplane on green square farther north on Caatinga east coast; physically separate from the port.

## AM-161 — Printed shore facilities: Rio de Janeiro–sea_a47

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_rio_de_janeiro`, `sea_a47`

**Current:**

```json
[
  {
    "sea_id": "sea_a39",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_rio_de_janeiro_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_port"
  ],
  "naval_facility_ids": [
    "facility_brazil_rio_de_janeiro_major_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_brazil_rio_de_janeiro_major_port_map_1",
      "type": "major_port",
      "sea_accesses": [
        "sea_a47"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_brazil_20261006.png",
          "rectangle": [
            815,
            3050,
            1380,
            3780
          ]
        }
      ],
      "notes": "Plain white anchor on blue square on Rio de Janeiro coast east of the Pampas land boundary. It does not belong to Pampas."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_north.png", "rectangle": [0, 2750, 1500, 3880]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_brazil_20261006.png", "rectangle": [815, 3050, 1380, 3780]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain white anchor on blue square on Rio de Janeiro coast east of the Pampas land boundary. It does not belong to Pampas.

## AM-163 — Printed shore facilities: Uruguay–sea_a47

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_uruguay`, `sea_a47`

**Current:**

```json
[
  {
    "sea_id": "sea_a39",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_uruguay_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_port"
  ],
  "naval_facility_ids": [
    "facility_uruguay_major_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_uruguay_major_port_map_1",
      "type": "major_port",
      "sea_accesses": [
        "sea_a47"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_south_atlantic_20261006.png",
          "rectangle": [
            290,
            3710,
            1000,
            4410
          ]
        }
      ],
      "notes": "Plain white anchor on blue square on Uruguay southern coast, northeast of the A47/A49 boundary starting by Buenos Aires."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_south_atlantic_20261006.png", "rectangle": [290, 3710, 1000, 4410]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain white anchor on blue square on Uruguay southern coast, northeast of the A47/A49 boundary starting by Buenos Aires.

## AM-164 — Printed shore facilities: Buenos Aires–sea_a49

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_buenos_aires`, `sea_a49`

**Current:**

```json
[
  {
    "sea_id": "sea_a40",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_aires_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "minor_shipyard"
  ],
  "naval_facility_ids": [
    "facility_buenos_aires_minor_shipyard_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_buenos_aires_minor_shipyard_map_1",
      "type": "minor_shipyard",
      "sea_accesses": [
        "sea_a49"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_south_atlantic_20261006.png",
          "rectangle": [
            290,
            3710,
            1000,
            4410
          ]
        }
      ],
      "notes": "Blue crane on white square on the southern Buenos Aires city-zone coast. The circular city boundary reaches coast west of the icon, so it is not Patagonia."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_south_atlantic_20261006.png", "rectangle": [290, 3710, 1000, 4410]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Blue crane on white square on the southern Buenos Aires city-zone coast. The circular city boundary reaches coast west of the icon, so it is not Patagonia.

## AM-165 — Printed shore facilities: Patagonia–sea_a49

**Field:** `naval_facilities + distinct physical IDs` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_patagonia`, `sea_a49`

**Current:**

```json
[
  {
    "sea_id": "sea_a40",
    "naval_facilities": [
      "minor_port"
    ],
    "naval_facility_ids": [
      "facility_land_patagonia_minor_port"
    ]
  }
]
```

**Proposed:**

```json
{
  "naval_facilities": [
    "major_port"
  ],
  "naval_facility_ids": [
    "facility_patagonia_major_port_map_1"
  ],
  "physical_facilities": [
    {
      "id": "facility_patagonia_major_port_map_1",
      "type": "major_port",
      "sea_accesses": [
        "sea_a49"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "crop": "docs/map_audits/full_world/evidence/americas_naval_south_atlantic_20261006.png",
          "rectangle": [
            290,
            3710,
            1000,
            4410
          ]
        }
      ],
      "notes": "Plain white anchor on blue square on Patagonia east coast south of the Buenos Aires circle. Distinct from the Buenos Aires crane."
    }
  ],
  "physical_ID_policy": "One ID for each independently visible glyph; no copied facilities on other coasts."
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_south_south.png", "rectangle": [0, 3500, 1500, 4600]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_naval_south_atlantic_20261006.png", "rectangle": [290, 3710, 1000, 4410]}

**Scope / dependency:** Fresh 2026-10-06 re-audit confirms the exact physical symbols below. Replace the old generic minor-port interpretation and wrong sea attachment where listed; do not retain it as an additional facility. Plain white anchor on blue square on Patagonia east coast south of the Buenos Aires circle. Distinct from the Buenos Aires crane.

## AM-166 — Pacific Northwest node_facilities

**Field:** `node_facilities` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_pacific_northwest`

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

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Printed green aircraft icon; allocate a stable intrinsic facility ID.

## AM-167 — San Francisco node_facilities

**Field:** `node_facilities` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_san_francisco`

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

- {"source": "game_content/maps/gw36map.png", "rectangle": [9400, 1180, 9900, 2350], "crop": "docs/map_audits/full_world/evidence/americas_usa_west.png"}

**Scope / dependency:** Printed green aircraft icon; allocate a stable intrinsic facility ID.

## AM-168 — New York node_facilities

**Field:** `node_facilities` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_new_york`

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

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Printed green aircraft icon; allocate a stable intrinsic facility ID.

## AM-169 — Washington, D.C. node_facilities

**Field:** `node_facilities` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_washington_dc`

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

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 1200, 1300, 2420], "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png"}

**Scope / dependency:** Printed green aircraft icon; allocate a stable intrinsic facility ID.

## AM-170 — A25/A30 coastal junction

**Field:** `directional topology / field attribution` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_washington_dc`, `land_usa_the_northeast`, `sea_a25`, `sea_a30`

**Current:**

See current node/edge records

**Proposed:**

```json
{
  "land_usa_washington_dc": [
    "sea_a30"
  ],
  "land_usa_the_northeast": [
    "sea_a24",
    "sea_a25"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [480, 1580, 980, 2140], "crop": "docs/map_audits/full_world/evidence/americas_usa_dc_coast.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_dc_ne_boundaries.png", "rectangle": [500, 1620, 850, 1900]}

**Scope / dependency:** Resolved enlarged boundary trace: The Northeast coastal strip lies between New York and Washington; Washington northern arc meets the sea-zone boundary. Great Lakes retains its own A24 port.

## AM-171 — Cuba sea split and major-port access

**Field:** `directional topology / field attribution` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_cuba`, `sea_a36`, `sea_a37`, `sea_a40`

**Current:**

See current node/edge records

**Proposed:**

```json
{
  "coasts": [
    "sea_a36",
    "sea_a37",
    "sea_a40"
  ],
  "major_port_access": [
    "sea_a36"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_florida_cuba.png", "rectangle": [400, 2110, 890, 2610]}

**Scope / dependency:** All three shores are finite. Major-port icon is unambiguously northwestern, north of the A36/A40 termination; no symbol straddling or duplicate facility is justified.

## AM-172 — Panama minor port has A40 shore access

**Field:** `naval_facility sea access` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_panama`, `sea_a40`, `sea_p76`

**Current:**

See current node/edge records

**Proposed:**

```json
{
  "physical_facility": "Panama printed minor port",
  "accessible_seas": [
    "sea_a40"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}
- {"source": "game_content/rules/Global War 1936 v4.3 Rulebook.pdf", "printed_page": 94, "section": "13.2.3"}

**Scope / dependency:** Printed white-anchor icon is on the northeastern/A40 shore. No second port or boundary-mounted icon appears on P76. Rulebook facility placement permits one or two bordering sea zones; canal presence does not automatically duplicate the facility onto the opposite shore.

## AM-173 — Amazonas/Caatinga coastal junction

**Field:** `directional topology / field attribution` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `land_brazil_caatinga`, `sea_a41`, `sea_a45`

**Current:**

See current node/edge records

**Proposed:**

```json
{
  "land_brazil_amazon_jungle": [
    "sea_a41"
  ],
  "land_brazil_caatinga": [
    "sea_a45",
    "sea_a47"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [850, 2890, 1750, 3770], "crop": "docs/map_audits/full_world/evidence/americas_brazil_coasts.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_amazon_coast.png", "rectangle": [790, 2940, 1110, 3260]}

**Scope / dependency:** Enlarged coast junction aligns land boundary with A41/A45 sea boundary. A42 ends offshore. No extra corner-only shore links.

## AM-174 — Southern Chile / Drake Passage edge

**Field:** `directional topology / field attribution` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_chile`, `land_patagonia`, `sea_p78`, `sea_a49`

**Current:**

See current node/edge records

**Proposed:**

```json
{
  "land_chile": [
    "sea_p77",
    "sea_p78",
    "sea_a49"
  ],
  "land_patagonia": [
    "sea_a49"
  ]
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 3500, 1500, 4600], "crop": "docs/map_audits/full_world/evidence/americas_south_south.png"}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_chile_tip.png", "rectangle": [280, 4180, 620, 4410]}

**Scope / dependency:** Tan Chilean islands continue east of the P78/A49 line. Patagonia remains east of that sea boundary. Neither has a printed narrow crossing to Falklands.

## AM-177 — Panama Canal joins A40 and P76

**Field:** `canal sea link` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_panama`, `sea_a36`, `sea_p31`, `sea_a40`, `sea_p76`

**Current:**

```json
{
  "sea_a36_to_sea_p31": {
    "neighbor_id": "sea_p31",
    "border_terrain": "sea",
    "passable": true,
    "has_river": false,
    "river_crossing": false,
    "railway_connection": false,
    "gauge_change": false,
    "naval_facilities": [],
    "naval_facility_ids": [],
    "port_or_dock_connection": false,
    "canal_or_strait": "Panama Canal",
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  },
  "panama_to_p31": {
    "neighbor_id": "sea_p31",
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
      "facility_land_panama_minor_port"
    ],
    "port_or_dock_connection": true,
    "canal_or_strait": "Panama Canal",
    "narrow_crossing": false,
    "narrow_crossings": 0,
    "special_fortification": null
  }
}
```

**Proposed:**

```json
{
  "remove_sea_link": [
    "sea_a36",
    "sea_p31"
  ],
  "add_sea_link": [
    "sea_a40",
    "sea_p76"
  ],
  "canal_or_strait": "Panama Canal",
  "controlling_land_zone": "land_panama"
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Current A36↔P31 sea edge crosses the wrong map regions. Rulebook §1.8 p15 explicitly gives control to Panama; ordinary open-ocean sea links must not bypass canal control.

## AM-220 — Use printed zone label for sea_a36

**Field:** `name` · **Confidence:** high · **Severity:** low

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a36`

**Current:**

Caribbean Sea North

**Proposed:**

A36

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Current invented geographic descriptor is misleading: A36 is Gulf of Mexico; A38/A39 are central North Atlantic (Azores in A39); A40 is western Caribbean. Geographic names may be retained only as separately sourced optional aliases.

## AM-221 — Use printed zone label for sea_a38

**Field:** `name` · **Confidence:** high · **Severity:** low

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a38`

**Current:**

Central Atlantic Equatorial

**Proposed:**

A38

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Current invented geographic descriptor is misleading: A36 is Gulf of Mexico; A38/A39 are central North Atlantic (Azores in A39); A40 is western Caribbean. Geographic names may be retained only as separately sourced optional aliases.

## AM-222 — Use printed zone label for sea_a39

**Field:** `name` · **Confidence:** high · **Severity:** low

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a39`

**Current:**

South Atlantic North

**Proposed:**

A39

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Current invented geographic descriptor is misleading: A36 is Gulf of Mexico; A38/A39 are central North Atlantic (Azores in A39); A40 is western Caribbean. Geographic names may be retained only as separately sourced optional aliases.

## AM-223 — Use printed zone label for sea_a40

**Field:** `name` · **Confidence:** high · **Severity:** low

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a40`

**Current:**

South Atlantic South

**Proposed:**

A40

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [0, 2260, 1470, 3150], "crop": "docs/map_audits/full_world/evidence/americas_central.png"}

**Scope / dependency:** Current invented geographic descriptor is misleading: A36 is Gulf of Mexico; A38/A39 are central North Atlantic (Azores in A39); A40 is western Caribbean. Geographic names may be retained only as separately sourced optional aliases.

## AM-224 — Use printed zone label for sea_a26

**Field:** `name` · **Confidence:** high · **Severity:** low

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a26`

**Current:**

North Atlantic Central West

**Proposed:**

A26

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Current invented geographic descriptor is misleading: A36 is Gulf of Mexico; A38/A39 are central North Atlantic (Azores in A39); A40 is western Caribbean. Geographic names may be retained only as separately sourced optional aliases.

## AM-225 — Use printed zone label for sea_a28

**Field:** `name` · **Confidence:** high · **Severity:** low

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a28`

**Current:**

Western Mediterranean Approaches

**Proposed:**

A28

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Current invented geographic descriptor is misleading: A36 is Gulf of Mexico; A38/A39 are central North Atlantic (Azores in A39); A40 is western Caribbean. Geographic names may be retained only as separately sourced optional aliases.

## AM-226 — Use printed zone label for sea_a29

**Field:** `name` · **Confidence:** high · **Severity:** low

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `sea_a29`

**Current:**

Mid-Atlantic East

**Proposed:**

A29

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1080, 1700, 2500, 3400], "crop": "docs/map_audits/full_world/evidence/americas_atlantic_mid.png"}

**Scope / dependency:** Current invented geographic descriptor is misleading: A36 is Gulf of Mexico; A38/A39 are central North Atlantic (Azores in A39); A40 is western Caribbean. Geographic names may be retained only as separately sourced optional aliases.

## AM-230 — Apply complete Americas glossary intrinsic terrain transcription

**Field:** `terrain` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_the_northeast`, `land_usa_upper_midwest`, `land_usa_great_plains`, `land_usa_pacific_northwest`, `land_usa_southwest_united_states`, `land_usa_san_francisco`, `land_panama`, `land_french_guiana`, `land_central_america`, `land_cuba`, `land_suriname`, `land_colombia`, `land_ecuador`, `land_brazil_caatinga`, `land_brazil_rio_de_janeiro`, `land_brazil_pampas`, `land_bolivia`

**Current:**

```json
{
  "land_usa_the_northeast": "normal",
  "land_usa_upper_midwest": "normal",
  "land_usa_great_plains": "normal",
  "land_usa_pacific_northwest": "forest",
  "land_usa_southwest_united_states": "desert",
  "land_usa_san_francisco": "normal",
  "land_panama": "jungle",
  "land_french_guiana": "jungle",
  "land_central_america": "jungle",
  "land_cuba": "normal",
  "land_suriname": "jungle",
  "land_colombia": "mountain",
  "land_ecuador": "mountain",
  "land_brazil_caatinga": "normal",
  "land_brazil_rio_de_janeiro": "normal",
  "land_brazil_pampas": "normal",
  "land_bolivia": "mountain"
}
```

**Proposed:**

```json
{
  "land_usa_the_northeast": "mountain",
  "land_usa_upper_midwest": "mountain",
  "land_usa_great_plains": "mountain",
  "land_usa_pacific_northwest": "mountain",
  "land_usa_southwest_united_states": "mountain",
  "land_usa_san_francisco": "mountain",
  "land_panama": "normal",
  "land_french_guiana": "normal",
  "land_central_america": "normal",
  "land_cuba": "mountain",
  "land_suriname": "normal",
  "land_colombia": "normal",
  "land_ecuador": "normal",
  "land_brazil_caatinga": "mountain",
  "land_brazil_rio_de_janeiro": "mountain",
  "land_brazil_pampas": "mountain",
  "land_bolivia": "normal"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Every Americas row on pp5–6 was visually checked, including blank columns. Some rows confirm earlier board proposals. This supplements rather than replaces the directed approach transcription. Baffin is deliberately excluded from the concrete changes.

## AM-233 — Apply explicit Americas glossary directed terrain and river requirements

**Field:** `directional border_terrain / river_crossing` · **Confidence:** high · **Severity:** medium

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_brazil_amazon_jungle`, `land_brazil_caatinga`, `land_brazil_pampas`, `land_central_america`, `land_chile`, `land_colombia`, `land_mex_eastern_mexico`, `land_panama`, `land_patagonia`, `land_rio_grande`, `land_uruguay`, `land_usa_appalachia`, `land_usa_chicago`, `land_usa_heartlands`, `land_usa_new_orleans`, `land_usa_new_york`, `land_usa_southeastern_united_states`, `land_usa_texas`, `land_usa_the_northeast`

**Current:**

```json
[
  {
    "source": "land_usa_new_york",
    "destination": "land_usa_the_northeast",
    "field": "river_crossing",
    "current": false
  },
  {
    "source": "land_usa_chicago",
    "destination": "land_usa_appalachia",
    "field": "river_crossing",
    "current": false
  },
  {
    "source": "land_usa_new_orleans",
    "destination": "land_usa_southeastern_united_states",
    "field": "border_terrain",
    "current": "normal"
  },
  {
    "source": "land_usa_new_orleans",
    "destination": "land_usa_texas",
    "field": "river_crossing",
    "current": false
  },
  {
    "source": "land_usa_new_orleans",
    "destination": "land_usa_heartlands",
    "field": "river_crossing",
    "current": false
  },
  {
    "source": "land_usa_appalachia",
    "destination": "land_usa_heartlands",
    "field": "river_crossing",
    "current": false
  },
  {
    "source": "land_colombia",
    "destination": "land_panama",
    "field": "river_crossing",
    "current": false
  },
  {
    "source": "land_central_america",
    "destination": "land_mex_eastern_mexico",
    "field": "border_terrain",
    "current": "normal"
  },
  {
    "source": "land_mex_eastern_mexico",
    "destination": "land_central_america",
    "field": "border_terrain",
    "current": "normal"
  },
  {
    "source": "land_panama",
    "destination": "land_colombia",
    "field": "border_terrain",
    "current": "normal"
  },
  {
    "source": "land_brazil_caatinga",
    "destination": "land_brazil_amazon_jungle",
    "field": "river_crossing",
    "current": false
  },
  {
    "source": "land_uruguay",
    "destination": "land_brazil_pampas",
    "field": "border_terrain",
    "current": "normal"
  },
  {
    "source": "land_rio_grande",
    "destination": "land_brazil_pampas",
    "field": "border_terrain",
    "current": "normal"
  },
  {
    "source": "land_brazil_pampas",
    "destination": "land_rio_grande",
    "field": "border_terrain",
    "current": "normal"
  },
  {
    "source": "land_chile",
    "destination": "land_patagonia",
    "field": "border_terrain",
    "current": "normal"
  }
]
```

**Proposed:**

```json
[
  {
    "source": "land_usa_new_york",
    "destination": "land_usa_the_northeast",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_chicago",
    "destination": "land_usa_appalachia",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_new_orleans",
    "destination": "land_usa_southeastern_united_states",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "land_usa_new_orleans",
    "destination": "land_usa_texas",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_new_orleans",
    "destination": "land_usa_heartlands",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_usa_appalachia",
    "destination": "land_usa_heartlands",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_colombia",
    "destination": "land_panama",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_central_america",
    "destination": "land_mex_eastern_mexico",
    "field": "border_terrain",
    "proposed": "jungle"
  },
  {
    "source": "land_mex_eastern_mexico",
    "destination": "land_central_america",
    "field": "border_terrain",
    "proposed": "jungle"
  },
  {
    "source": "land_panama",
    "destination": "land_colombia",
    "field": "border_terrain",
    "proposed": "mountain"
  },
  {
    "source": "land_brazil_caatinga",
    "destination": "land_brazil_amazon_jungle",
    "field": "river_crossing",
    "proposed": true
  },
  {
    "source": "land_uruguay",
    "destination": "land_brazil_pampas",
    "field": "border_terrain",
    "proposed": [
      "mountain",
      "jungle"
    ]
  },
  {
    "source": "land_rio_grande",
    "destination": "land_brazil_pampas",
    "field": "border_terrain",
    "proposed": [
      "mountain",
      "jungle"
    ]
  },
  {
    "source": "land_brazil_pampas",
    "destination": "land_rio_grande",
    "field": "border_terrain",
    "proposed": "jungle"
  },
  {
    "source": "land_chile",
    "destination": "land_patagonia",
    "field": "border_terrain",
    "proposed": "mountain"
  }
]
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 5, "render": "docs/map_audits/full_world/evidence/americas_glossary-05.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "pdf_page": 6, "render": "docs/map_audits/full_world/evidence/americas_glossary-06.png"}

**Scope / dependency:** Concrete changes concern existing directed entries. Reciprocal values are not copied automatically. The full transcription records matches, absent edges, and the Amazonas quantifier separately; changing a combat flag never grants passage across an impassable border.

## AM-238 — Remove five US rail crossings absent from the actual shared borders

**Field:** `railway_connection` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_appalachia`, `land_usa_great_plains`, `land_usa_southwest_united_states`, `land_usa_the_carolinas`, `land_usa_upper_midwest`, `land_usa_washington_dc`, `land_usa_western_united_states`

**Current:**

```json
[
  {
    "pair": [
      "land_usa_great_plains",
      "land_usa_upper_midwest"
    ],
    "forward": true,
    "reverse": true
  },
  {
    "pair": [
      "land_usa_great_plains",
      "land_usa_western_united_states"
    ],
    "forward": true,
    "reverse": true
  },
  {
    "pair": [
      "land_usa_southwest_united_states",
      "land_usa_western_united_states"
    ],
    "forward": true,
    "reverse": true
  },
  {
    "pair": [
      "land_usa_appalachia",
      "land_usa_washington_dc"
    ],
    "forward": true,
    "reverse": true
  },
  {
    "pair": [
      "land_usa_appalachia",
      "land_usa_the_carolinas"
    ],
    "forward": true,
    "reverse": true
  }
]
```

**Proposed:**

```json
[
  {
    "pair": [
      "land_usa_great_plains",
      "land_usa_upper_midwest"
    ],
    "both_directions": false
  },
  {
    "pair": [
      "land_usa_great_plains",
      "land_usa_western_united_states"
    ],
    "both_directions": false
  },
  {
    "pair": [
      "land_usa_southwest_united_states",
      "land_usa_western_united_states"
    ],
    "both_directions": false
  },
  {
    "pair": [
      "land_usa_appalachia",
      "land_usa_washington_dc"
    ],
    "both_directions": false
  },
  {
    "pair": [
      "land_usa_appalachia",
      "land_usa_the_carolinas"
    ],
    "both_directions": false
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_southwest_junction.png", "rectangle": [9550, 1720, 9900, 2140]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_us_seam_full_detail.png", "source_rectangles": [[9650, 1260, 9900, 2240], [0, 1260, 310, 2240]], "scale": 2}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_interior_detail.png", "rectangle": [180, 1450, 850, 2070]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_usa_east.png", "rectangle": [0, 1200, 1300, 2420]}

**Scope / dependency:** Shared land borders are retained. The eastward SF railway crosses Southwest–Great Plains below the Western US junction; no track crosses Great Plains–Upper Midwest. Appalachia rail reaches Washington through Great Lakes and reaches Carolinas through Southeastern US/Washington, not by a direct mountain-border crossing.

## AM-240 — Remove unsupported river penalty between Great Plains and Upper Midwest

**Field:** `river_crossing` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_usa_great_plains`, `land_usa_upper_midwest`

**Current:**

```json
{
  "forward": true,
  "reverse": false
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_us_seam_full_detail.png", "source_rectangles": [[9650, 1260, 9900, 2240], [0, 1260, 310, 2240]], "scale": 2}

**Scope / dependency:** Shared horizontal black border contains no blue river and neither glossary row specifies a river approach.

## AM-242 — Remove two South American rail flags where tracks reach the neighbor through another zone

**Field:** `railway_connection` · **Confidence:** high · **Severity:** high

**Regional context:** [americas_atlantic](regions/americas_atlantic.md)

**Nodes:** `land_buenos_aires`, `land_chile`, `land_peru`, `land_uruguay`

**Current:**

```json
[
  {
    "pair": [
      "land_chile",
      "land_peru"
    ],
    "forward": true,
    "reverse": true
  },
  {
    "pair": [
      "land_buenos_aires",
      "land_uruguay"
    ],
    "forward": true,
    "reverse": true
  }
]
```

**Proposed:**

```json
[
  {
    "pair": [
      "land_chile",
      "land_peru"
    ],
    "both_directions": false
  },
  {
    "pair": [
      "land_buenos_aires",
      "land_uruguay"
    ],
    "both_directions": false
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_bolivia_rail.png", "rectangle": [440, 3300, 670, 3590]}
- {"source": "game_content/maps/gw36map.png", "crop": "docs/map_audits/full_world/evidence/americas_buenos_aires_rail.png", "rectangle": [500, 3730, 815, 3970]}

**Scope / dependency:** Peru rail enters Bolivia before the branch crosses Bolivia–Chile; no track crosses the direct Peru–Chile border. Buenos Aires rail joins the northern network in Norte Grande; no track crosses its short Uruguay land boundary. Keep both physical adjacencies.

## EA-001 — Scotland: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_scotland`

**Current:**

mountain_border

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-002 — Scotland: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_scotland`

**Current:**

```json
2
```

**Proposed:**

```json
1
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-003 — Southern England: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_southern_england`

**Current:**

```json
2
```

**Proposed:**

```json
3
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-004 — Ireland: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ireland`

**Current:**

```json
2
```

**Proposed:**

```json
1
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-005 — Galicia and Leon: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_galicia_and_leon`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-006 — Basque Country: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_basque_country`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-007 — Madrid: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_madrid`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-008 — Western Andalucia: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_western_andalucia`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-009 — Eastern Andalucia: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_eastern_andalucia`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-010 — Picardy: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_picardy`

**Current:**

```json
2
```

**Proposed:**

```json
1
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2220, 1180, 3070, 2110], "crop": "evidence/ea_france.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-011 — Southern France: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_southern_france`

**Current:**

```json
2
```

**Proposed:**

```json
1
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2220, 1180, 3070, 2110], "crop": "evidence/ea_france.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-012 — Alsace-Lorraine: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_alsace_lorraine`

**Current:**

```json
2
```

**Proposed:**

```json
3
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2220, 1180, 3070, 2110], "crop": "evidence/ea_france.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-013 — Eastern Germany: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_eastern_germany`

**Current:**

```json
2
```

**Proposed:**

```json
4
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-014 — Northern Italy: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_northern_italy`

**Current:**

```json
4
```

**Proposed:**

```json
3
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-015 — Rome: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rome`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-016 — Lazio: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_lazio`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-017 — Lazio: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_lazio`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-018 — Southern Italy: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_southern_italy`

**Current:**

```json
2
```

**Proposed:**

```json
1
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-019 — Corsica: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_corsica`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2500, 1000, 3500, 2700], "crop": "evidence/ea_west_europe.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-020 — Trondelag: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_trondelag`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-021 — Lapland: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_lapland`

**Current:**

tundra

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-022 — Southern Finland: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_southern_finland`

**Current:**

forest

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-023 — Viipuri Province: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_viipuri_province`

**Current:**

forest

**Proposed:**

marsh

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-024 — Viipuri Province: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_viipuri_province`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-025 — Estonia: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_estonia`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-026 — Latvia: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_latvia`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-027 — Podlachia: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_podlachia`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-028 — Lubelskie: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_lubelskie`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-029 — Dolnoslaskie: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_dolnoslaskie`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-030 — Albania: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_albania`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3250, 1050, 4900, 2400], "crop": "evidence/ea_east_europe.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-031 — Macedonia: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_macedonia`

**Current:**

mountain

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3250, 1050, 4900, 2400], "crop": "evidence/ea_east_europe.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-032 — Macedonia: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_macedonia`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3250, 1050, 4900, 2400], "crop": "evidence/ea_east_europe.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-033 — Istanbul: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_istanbul`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-034 — Eastern Anatolia: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_eastern_anatolia`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-035 — Northern Iran: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_iran_northern_iran`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-036 — Syria: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_syria`

**Current:**

normal

**Proposed:**

desert

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-037 — Transjordan: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_transjordan`

**Current:**

```json
0
```

**Proposed:**

```json
1
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-038 — Northern Algeria: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_algeria`

**Current:**

mountain

**Proposed:**

```json
[
  "mountain",
  "desert"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Roundel-wide combined terrain needs schema support; do not flatten into a border-only penalty.

## EA-039 — Northern Algeria: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_algeria`

**Current:**

```json
0
```

**Proposed:**

```json
1
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-040 — French Sudan: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_sudan`

**Current:**

desert

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-041 — Niger: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_niger`

**Current:**

desert

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-042 — Chad: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_chad`

**Current:**

desert

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-043 — Oubangui-Chari: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_oubangui_chari`

**Current:**

jungle

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-044 — Southwest Africa: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southwest_africa`

**Current:**

desert

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-045 — Madagascar: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_madagascar`

**Current:**

jungle

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-046 — Mauritius: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_mauritius`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-047 — Seychelles: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_seychelles`

**Current:**

normal

**Proposed:**

mountain

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-048 — Karelia: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_karelia`

**Current:**

forest

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-049 — Northern Russia: terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_northern_russia`

**Current:**

tundra

**Proposed:**

normal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}
- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Roundel terrain, separate from first-round directional border terrain.

## EA-050 — Yaroslavl: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_yaroslavl`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-051 — Northern Belorussia: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_northern_belorussia`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-052 — Kiev: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kiev`

**Current:**

```json
0
```

**Proposed:**

```json
3
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3775, 350, 5230, 1600], "crop": "evidence/ea_western_ussr_north.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-053 — Southern Ukraine: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_southern_ukraine`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3980, 1375, 5380, 2300], "crop": "evidence/ea_western_ussr_south.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-054 — Donets-Kuban: ipp_value

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_donets_kuban`

**Current:**

```json
1
```

**Proposed:**

```json
0
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3980, 1375, 5380, 2300], "crop": "evidence/ea_western_ussr_south.png"}

**Scope / dependency:** Red IPP numeral transcribed; no red income box means 0.

## EA-055 — Azerbaijan: original owner

**Field:** `original_owner` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_azerbaijan`

**Current:**

Azerbaijan

**Proposed:**

Iran

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Printed national roundel/grouping, also terrain-glossary nation grouping. Initial controller must be chosen by scenario/setup; do not overwrite later live game state.

## EA-056 — Syria: original owner

**Field:** `original_owner` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_syria`

**Current:**

Syria

**Proposed:**

France

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Printed national roundel/grouping, also terrain-glossary nation grouping. Initial controller must be chosen by scenario/setup; do not overwrite later live game state.

## EA-057 — Transjordan: original owner

**Field:** `original_owner` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_transjordan`

**Current:**

Transjordan

**Proposed:**

United Kingdom

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Printed national roundel/grouping, also terrain-glossary nation grouping. Initial controller must be chosen by scenario/setup; do not overwrite later live game state.

## EA-058 — Kuwait: original owner

**Field:** `original_owner` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_kuwait`

**Current:**

Kuwait

**Proposed:**

United Kingdom

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Printed national roundel/grouping, also terrain-glossary nation grouping. Initial controller must be chosen by scenario/setup; do not overwrite later live game state.

## EA-059 — Qatar: original owner

**Field:** `original_owner` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_qatar`

**Current:**

Qatar

**Proposed:**

United Kingdom

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Printed national roundel/grouping, also terrain-glossary nation grouping. Initial controller must be chosen by scenario/setup; do not overwrite later live game state.

## EA-088 — Bavaria: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_bavaria`, `land_cze_bohemia`, `land_aut_austria`, `land_switzerland`

**Current:**

```json
{
  "land_cze_bohemia": "normal",
  "land_aut_austria": "normal",
  "land_switzerland": "normal"
}
```

**Proposed:**

```json
{
  "land_cze_bohemia": "mountain",
  "land_aut_austria": "mountain",
  "land_switzerland": "mountain"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-090 — Northern England: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_northern_england`, `land_gbr_scotland`

**Current:**

```json
{
  "land_gbr_scotland": "normal"
}
```

**Proposed:**

```json
{
  "land_gbr_scotland": "mountain"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-091 — Southern France: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_southern_france`, `land_ita_northern_italy`

**Current:**

```json
{
  "land_ita_northern_italy": "normal"
}
```

**Proposed:**

```json
{
  "land_ita_northern_italy": "mountain"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-092 — Northern Italy: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_northern_italy`, `land_ita_rome`, `sea_m3`

**Current:**

```json
{
  "land_ita_rome": "normal",
  "sea_m3": "normal"
}
```

**Proposed:**

```json
{
  "land_ita_rome": "mountain",
  "sea_m3": "mountain"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-095 — Belgium: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_neu_belgium`, `land_fra_picardy`

**Current:**

```json
{
  "land_fra_picardy": "normal"
}
```

**Proposed:**

```json
{
  "land_fra_picardy": "mountain"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-097 — Norrland: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_swe_norrland`, `land_nor_trondelag`

**Current:**

```json
{
  "land_nor_trondelag": "tundra"
}
```

**Proposed:**

```json
{
  "land_nor_trondelag": "mountain"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-099 — Southern Finland: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_southern_finland`, `land_fin_viipuri_province`

**Current:**

```json
{
  "land_fin_viipuri_province": "normal"
}
```

**Proposed:**

```json
{
  "land_fin_viipuri_province": "marsh"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-101 — Bulgaria: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_bulgaria`, `land_yug_eastern_yugoslavia`, `land_rom_central_romania`

**Current:**

```json
{
  "land_yug_eastern_yugoslavia": "normal",
  "land_rom_central_romania": "normal"
}
```

**Proposed:**

```json
{
  "land_yug_eastern_yugoslavia": "mountain",
  "land_rom_central_romania": "mountain"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-103 — Macedonia: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_macedonia`, `land_gre_thessaly`

**Current:**

```json
{
  "land_gre_thessaly": "normal"
}
```

**Proposed:**

```json
{
  "land_gre_thessaly": "mountain"
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-108 — Tunisia: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tunisia`, `land_northern_algeria`

**Current:**

```json
{
  "land_northern_algeria": "normal"
}
```

**Proposed:**

```json
{
  "land_northern_algeria": [
    "desert",
    "mountain"
  ]
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-112 — Abyssinia: directional border terrain

**Field:** `incoming_edges.border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_abyssinia`, `land_french_somaliland`, `land_italian_somaliland`

**Current:**

```json
{
  "land_french_somaliland": [
    "desert",
    "mountain"
  ],
  "land_italian_somaliland": [
    "desert",
    "mountain"
  ]
}
```

**Proposed:**

```json
{
  "land_french_somaliland": [
    "mountain",
    "desert"
  ],
  "land_italian_somaliland": [
    "mountain",
    "desert"
  ]
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Full destination terrain combined with extra first-round crossing terrain. This does not change rail or river flags, or certify topology of other edges.

## EA-113 — Berlin: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_berlin`, `land_ger_eastern_germany`

**Current:**

```json
{
  "land_ger_eastern_germany": false
}
```

**Proposed:**

```json
{
  "land_ger_eastern_germany": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-114 — Western Germany: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_western_germany`, `land_ger_eastern_germany`, `land_neu_belgium`

**Current:**

```json
{
  "land_ger_eastern_germany": false,
  "land_neu_belgium": false
}
```

**Proposed:**

```json
{
  "land_ger_eastern_germany": true,
  "land_neu_belgium": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-116 — Bavaria: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_bavaria`, `land_aut_austria`, `land_switzerland`, `land_fra_alsace_lorraine`

**Current:**

```json
{
  "land_aut_austria": false,
  "land_switzerland": false,
  "land_fra_alsace_lorraine": false
}
```

**Proposed:**

```json
{
  "land_aut_austria": true,
  "land_switzerland": true,
  "land_fra_alsace_lorraine": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-118 — Paris: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_paris`, `land_fra_picardy`

**Current:**

```json
{
  "land_fra_picardy": false
}
```

**Proposed:**

```json
{
  "land_fra_picardy": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-119 — Normandy: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_normandy`, `land_fra_picardy`

**Current:**

```json
{
  "land_fra_picardy": false
}
```

**Proposed:**

```json
{
  "land_fra_picardy": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-121 — Aquitaine: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_aquitaine`, `land_fra_paris`

**Current:**

```json
{
  "land_fra_paris": false
}
```

**Proposed:**

```json
{
  "land_fra_paris": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-122 — Southern France: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_southern_france`, `land_fra_paris`, `land_ita_northern_italy`

**Current:**

```json
{
  "land_fra_paris": false,
  "land_ita_northern_italy": false
}
```

**Proposed:**

```json
{
  "land_fra_paris": true,
  "land_ita_northern_italy": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-123 — Rome: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rome`, `sea_m3`

**Current:**

```json
{
  "sea_m3": false
}
```

**Proposed:**

```json
{
  "sea_m3": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 7}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-124 — Netherlands: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_neu_netherlands`, `land_neu_belgium`

**Current:**

```json
{
  "land_neu_belgium": false
}
```

**Proposed:**

```json
{
  "land_neu_belgium": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-125 — West Poland: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_west_poland`, `land_pol_warsaw`

**Current:**

```json
{
  "land_pol_warsaw": false
}
```

**Proposed:**

```json
{
  "land_pol_warsaw": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-127 — Dolnoslaskie: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_dolnoslaskie`, `land_pol_west_poland`, `land_cze_bohemia`

**Current:**

```json
{
  "land_pol_west_poland": false,
  "land_cze_bohemia": false
}
```

**Proposed:**

```json
{
  "land_pol_west_poland": true,
  "land_cze_bohemia": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-129 — Austria: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_aut_austria`, `land_cze_bohemia`, `land_cze_slovakia`

**Current:**

```json
{
  "land_cze_bohemia": false,
  "land_cze_slovakia": false
}
```

**Proposed:**

```json
{
  "land_cze_bohemia": true,
  "land_cze_slovakia": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-130 — Hungary: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_hun_hungary`, `land_aut_austria`, `land_yug_western_yugoslavia`

**Current:**

```json
{
  "land_aut_austria": false,
  "land_yug_western_yugoslavia": false
}
```

**Proposed:**

```json
{
  "land_aut_austria": true,
  "land_yug_western_yugoslavia": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-131 — Central Romania: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rom_central_romania`, `land_bulgaria`, `land_yug_eastern_yugoslavia`

**Current:**

```json
{
  "land_bulgaria": false,
  "land_yug_eastern_yugoslavia": false
}
```

**Proposed:**

```json
{
  "land_bulgaria": true,
  "land_yug_eastern_yugoslavia": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-133 — Eastern Yugoslavia: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_yug_eastern_yugoslavia`, `land_hun_hungary`, `land_rom_central_romania`

**Current:**

```json
{
  "land_hun_hungary": false,
  "land_rom_central_romania": false
}
```

**Proposed:**

```json
{
  "land_hun_hungary": true,
  "land_rom_central_romania": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 8}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-135 — Nubia: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nubia`, `land_sudan`

**Current:**

```json
{
  "land_sudan": false
}
```

**Proposed:**

```json
{
  "land_sudan": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-137 — Rhodesia: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rhodesia`, `land_south_africa`, `land_bechuanaland`

**Current:**

```json
{
  "land_south_africa": false,
  "land_bechuanaland": false
}
```

**Proposed:**

```json
{
  "land_south_africa": true,
  "land_bechuanaland": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-138 — Nigeria: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nigeria`, `land_cameroon`, `land_dahomey`

**Current:**

```json
{
  "land_cameroon": false,
  "land_dahomey": false
}
```

**Proposed:**

```json
{
  "land_cameroon": true,
  "land_dahomey": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-140 — Syria: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_syria`, `land_northern_iraq`, `land_tur_eastern_anatolia`

**Current:**

```json
{
  "land_northern_iraq": false,
  "land_tur_eastern_anatolia": false
}
```

**Proposed:**

```json
{
  "land_northern_iraq": true,
  "land_tur_eastern_anatolia": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 9}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-141 — Oubangui-Chari: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_oubangui_chari`, `land_sudan`

**Current:**

```json
{
  "land_sudan": false
}
```

**Proposed:**

```json
{
  "land_sudan": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-142 — Cameroon: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cameroon`, `land_oubangui_chari`, `land_belgian_congo`

**Current:**

```json
{
  "land_oubangui_chari": false,
  "land_belgian_congo": false
}
```

**Proposed:**

```json
{
  "land_oubangui_chari": true,
  "land_belgian_congo": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-146 — French Sudan: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_sudan`, `land_niger`

**Current:**

```json
{
  "land_niger": false
}
```

**Proposed:**

```json
{
  "land_niger": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-148 — Istanbul: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_istanbul`, `land_bulgaria`, `land_gre_macedonia`

**Current:**

```json
{
  "land_bulgaria": false,
  "land_gre_macedonia": false
}
```

**Proposed:**

```json
{
  "land_bulgaria": true,
  "land_gre_macedonia": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-149 — Eastern Anatolia: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_eastern_anatolia`, `land_usr_transcaucasia`, `land_northern_iraq`, `land_syria`, `land_tur_akdeniz`, `land_tur_ankara`

**Current:**

```json
{
  "land_usr_transcaucasia": false,
  "land_northern_iraq": false,
  "land_syria": false,
  "land_tur_akdeniz": false,
  "land_tur_ankara": false
}
```

**Proposed:**

```json
{
  "land_usr_transcaucasia": true,
  "land_northern_iraq": true,
  "land_syria": true,
  "land_tur_akdeniz": true,
  "land_tur_ankara": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-151 — Northern Iraq: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_iraq`, `land_southern_iraq`

**Current:**

```json
{
  "land_southern_iraq": false
}
```

**Proposed:**

```json
{
  "land_southern_iraq": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-152 — Southern Iraq: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southern_iraq`, `land_iran_southern_iran`

**Current:**

```json
{
  "land_iran_southern_iran": false
}
```

**Proposed:**

```json
{
  "land_iran_southern_iran": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-153 — Belgian Congo: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_belgian_congo`, `land_oubangui_chari`, `land_tanganyika`, `land_rhodesia`, `land_angola`, `land_cameroon`

**Current:**

```json
{
  "land_oubangui_chari": false,
  "land_tanganyika": false,
  "land_rhodesia": false,
  "land_angola": false,
  "land_cameroon": false
}
```

**Proposed:**

```json
{
  "land_oubangui_chari": true,
  "land_tanganyika": true,
  "land_rhodesia": true,
  "land_angola": true,
  "land_cameroon": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 10}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-157 — Moscow: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_moscow`, `land_usr_yaroslavl`, `land_usr_kaluga_oblast`

**Current:**

```json
{
  "land_usr_yaroslavl": false,
  "land_usr_kaluga_oblast": false
}
```

**Proposed:**

```json
{
  "land_usr_yaroslavl": true,
  "land_usr_kaluga_oblast": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-160 — Tula-Lipetsk: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_tula_lipetsk`, `land_usr_orel_kursk`, `land_usr_stalingrad`

**Current:**

```json
{
  "land_usr_orel_kursk": false,
  "land_usr_stalingrad": false
}
```

**Proposed:**

```json
{
  "land_usr_orel_kursk": true,
  "land_usr_stalingrad": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-163 — Eastern Ukraine: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_eastern_ukraine`, `land_usr_southern_ukraine`

**Current:**

```json
{
  "land_usr_southern_ukraine": false
}
```

**Proposed:**

```json
{
  "land_usr_southern_ukraine": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-164 — Kiev: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kiev`, `land_usr_eastern_ukraine`

**Current:**

```json
{
  "land_usr_eastern_ukraine": false
}
```

**Proposed:**

```json
{
  "land_usr_eastern_ukraine": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-165 — Taurida: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_taurida`, `land_usr_southern_ukraine`

**Current:**

```json
{
  "land_usr_southern_ukraine": false
}
```

**Proposed:**

```json
{
  "land_usr_southern_ukraine": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-166 — Donets-Kuban: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_donets_kuban`, `land_usr_north_caucasia`, `land_usr_kalmytskaya`

**Current:**

```json
{
  "land_usr_north_caucasia": false,
  "land_usr_kalmytskaya": false
}
```

**Proposed:**

```json
{
  "land_usr_north_caucasia": true,
  "land_usr_kalmytskaya": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-170 — Gorky: incoming river combat crossing

**Field:** `incoming_edges.river_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_gorky`, `land_usr_saratov`

**Current:**

```json
{
  "land_usr_saratov": false
}
```

**Proposed:**

```json
{
  "land_usr_saratov": true
}
```

**Evidence:**

- {"source": "game_content/rules/GW1936_Terrain_Glossary_v1.pdf", "printed_page": 11}

**Scope / dependency:** Directional combat flag only. A river route (has_river) cannot be inferred from this table.

## EA-198 — Trondelag ↔ Norrland: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_trondelag`, `land_swe_norrland`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-199 — West Poland ↔ Podlachia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_west_poland`, `land_pol_podlachia`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-200 — Warsaw ↔ East Poland: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_warsaw`, `land_pol_east_poland`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-201 — Dolnoslaskie ↔ Bohemia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_dolnoslaskie`, `land_cze_bohemia`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3210, 850, 4170, 1780], "crop": "evidence/ea_poland.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-202 — Western Algeria ↔ Southern Algeria: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_western_algeria`, `land_southern_algeria`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-203 — Northern Algeria ↔ Southern Algeria: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_algeria`, `land_southern_algeria`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-204 — Tunisia ↔ Tripoli: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tunisia`, `land_tripoli`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-205 — Tripoli ↔ Tripolitania: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tripoli`, `land_tripolitania`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-206 — Tripolitania ↔ Cyrenaica: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tripolitania`, `land_cyrenaica`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-207 — Cyrenaica ↔ Tobruk: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cyrenaica`, `land_tobruk`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-208 — French Sudan ↔ Niger: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_sudan`, `land_niger`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-209 — Niger ↔ Chad: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_niger`, `land_chad`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-210 — Chad ↔ Sudan: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_chad`, `land_sudan`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-211 — Niger ↔ Nigeria: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_niger`, `land_nigeria`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-212 — Dahomey ↔ Nigeria: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_dahomey`, `land_nigeria`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-213 — Nigeria ↔ Cameroon: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nigeria`, `land_cameroon`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-214 — Cameroon ↔ Oubangui-Chari: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cameroon`, `land_oubangui_chari`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-215 — Oubangui-Chari ↔ Chad: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_oubangui_chari`, `land_chad`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-216 — Oubangui-Chari ↔ Sudan: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_oubangui_chari`, `land_sudan`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-217 — Cameroon ↔ Belgian Congo: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cameroon`, `land_belgian_congo`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-218 — Belgian Congo ↔ Oubangui-Chari: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_belgian_congo`, `land_oubangui_chari`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1600, 3500, 4450, 4888], "crop": "evidence/ea_africa_west_south.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-219 — Belgian Congo ↔ Tanganyika: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_belgian_congo`, `land_tanganyika`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-220 — Angola ↔ Southwest Africa: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_angola`, `land_southwest_africa`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-221 — Rhodesia ↔ Tanganyika: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rhodesia`, `land_tanganyika`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-222 — Rhodesia ↔ South Africa: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rhodesia`, `land_south_africa`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-223 — Southwest Africa ↔ Bechuanaland: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southwest_africa`, `land_bechuanaland`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-224 — Tanganyika ↔ Portuguese East Africa: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tanganyika`, `land_portuguese_east_africa`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-225 — Saudi Arabia ↔ Aden: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_saudi_arabia`, `land_aden`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-226 — Saudi Arabia ↔ Qatar: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_saudi_arabia`, `land_qatar`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-227 — Southern Iraq ↔ Kuwait: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southern_iraq`, `land_kuwait`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-228 — Syria ↔ Northern Iraq: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_syria`, `land_northern_iraq`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-229 — Eastern Anatolia ↔ Northern Iraq: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_eastern_anatolia`, `land_northern_iraq`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-230 — Eastern Anatolia ↔ Azerbaijan: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_eastern_anatolia`, `land_azerbaijan`

**Current:**

```json
{
  "forward": true,
  "reverse": true
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** The audited printed shared border has no black/white railway crossing. Ordinary adjacency remains; this is not a route via intermediate zones.

## EA-253 — Denmark ↔ Gotaland: printed narrow crossing

**Field:** `narrow_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_denmark`, `land_swe_gotaland`

**Current:**

```json
{
  "neighbor_id": "land_swe_gotaland",
  "border_terrain": "coast",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": false,
  "gauge_change": false,
  "naval_facilities": [],
  "naval_facility_ids": [],
  "port_or_dock_connection": false,
  "canal_or_strait": "Danish Straits",
  "narrow_crossing": true,
  "narrow_crossings": 1,
  "special_fortification": null
}
```

**Proposed:**

```json
{
  "both_directions": true,
  "narrow_crossings": 2,
  "narrow_crossing_sea_zones": [
    "sea_a11",
    "sea_a12"
  ],
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2450, 0, 4200, 1200], "crop": "evidence/ea_scandinavia.png"}

**Scope / dependency:** Capacity is the printed yellow diamond numeral. Blocking-sea assignment at two-sea boundary should be kept explicit. Preserve independent destination terrain and directional river rules.

## EA-259 — Crimea ↔ Donets-Kuban: printed narrow crossing

**Field:** `narrow_crossing` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_crimea`, `land_usr_donets_kuban`

**Current:**

```json
{
  "neighbor_id": "land_usr_donets_kuban",
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
{
  "both_directions": true,
  "narrow_crossings": 1,
  "narrow_crossing_sea_zones": [
    "sea_m11"
  ],
  "railway_connection": false
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3980, 1375, 5380, 2300], "crop": "evidence/ea_western_ussr_south.png"}

**Scope / dependency:** Capacity is the printed yellow diamond numeral. Blocking-sea assignment at two-sea boundary should be kept explicit. Preserve independent destination terrain and directional river rules.

## EA-260 — Corsica: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_corsica`, `sea_m3`, `sea_m1`, `sea_m3`

**Current:**

```json
[
  "sea_m3"
]
```

**Proposed:**

```json
[
  "sea_m1",
  "sea_m3"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-261 — Sardinia: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_sardinia`, `sea_m3`, `sea_m1`, `sea_m3`

**Current:**

```json
[
  "sea_m3"
]
```

**Proposed:**

```json
[
  "sea_m1",
  "sea_m3"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-262 — Northern Italy: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_northern_italy`, `sea_m3`, `sea_m3`, `sea_m5`

**Current:**

```json
[
  "sea_m3"
]
```

**Proposed:**

```json
[
  "sea_m3",
  "sea_m5"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-263 — Rome: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rome`, `sea_m3`, `sea_m3`, `sea_m5`

**Current:**

```json
[
  "sea_m3"
]
```

**Proposed:**

```json
[
  "sea_m3",
  "sea_m5"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-264 — Lazio: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_lazio`, `sea_m4`, `sea_m3`, `sea_m5`

**Current:**

```json
[
  "sea_m4"
]
```

**Proposed:**

```json
[
  "sea_m3",
  "sea_m5"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-265 — Southern Italy: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_southern_italy`, `sea_m4`, `sea_m5`, `sea_m3`, `sea_m5`, `sea_m6`

**Current:**

```json
[
  "sea_m4",
  "sea_m5"
]
```

**Proposed:**

```json
[
  "sea_m3",
  "sea_m5",
  "sea_m6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-266 — Macedonia: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_macedonia`, `sea_m5`, `sea_m6`, `sea_m7`

**Current:**

```json
[
  "sea_m5"
]
```

**Proposed:**

```json
[
  "sea_m7"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Complete coast set traced in the second pass; only positive shoreline segments are included.

## EA-267 — Thessaly: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gre_thessaly`, `sea_m6`, `sea_m7`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_m6",
  "sea_m7"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-268 — Istanbul: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_istanbul`, `sea_m10`, `sea_m10`, `sea_m7`

**Current:**

```json
[
  "sea_m10"
]
```

**Proposed:**

```json
[
  "sea_m10",
  "sea_m7"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-269 — Akdeniz: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_akdeniz`, `sea_m11`, `sea_m7`, `sea_m9`

**Current:**

```json
[
  "sea_m11"
]
```

**Proposed:**

```json
[
  "sea_m7",
  "sea_m9"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-270 — Eastern Anatolia: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_eastern_anatolia`, `sea_m11`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_m11"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-271 — Cyprus: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cyprus`, `sea_m9`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_m9"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-272 — Transjordan: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_transjordan`, `sea_m9`, `sea_m8`

**Current:**

```json
[
  "sea_m9"
]
```

**Proposed:**

```json
[
  "sea_m8"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-273 — Central Romania: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rom_central_romania`, `sea_m10`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_m10"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3980, 1375, 5380, 2300], "crop": "evidence/ea_western_ussr_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-274 — Southern Ukraine: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_southern_ukraine`, `sea_m10`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_m10"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3980, 1375, 5380, 2300], "crop": "evidence/ea_western_ussr_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately. The M10–M11 line starts at the Southern Ukraine/Taurida river mouth, not midway through Southern Ukraine coast.

## EA-275 — Crimea: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_crimea`, `sea_m10`, `sea_m11`, `sea_m11`

**Current:**

```json
[
  "sea_m10",
  "sea_m11"
]
```

**Proposed:**

```json
[
  "sea_m11"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3980, 1375, 5380, 2300], "crop": "evidence/ea_western_ussr_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-276 — Donets-Kuban: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_donets_kuban`, `sea_m11`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_m11"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3980, 1375, 5380, 2300], "crop": "evidence/ea_western_ussr_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-277 — North-Caucasia: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_north_caucasia`, `sea_m11`, `sea_m11`, `sea_m12`

**Current:**

```json
[
  "sea_m11"
]
```

**Proposed:**

```json
[
  "sea_m11",
  "sea_m12"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3980, 1375, 5380, 2300], "crop": "evidence/ea_western_ussr_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-278 — Northern Iran: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_iran_northern_iran`, `sea_m12`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_m12"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3850, 2050, 5580, 2980], "crop": "evidence/ea_turkey_iran.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-279 — Tripolitania: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tripolitania`, `sea_m4`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_m4"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-280 — Cyrenaica: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cyrenaica`, `sea_m4`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_m4"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-281 — Tobruk: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tobruk`, `sea_m8`, `sea_m9`, `sea_m4`, `sea_m8`

**Current:**

```json
[
  "sea_m8",
  "sea_m9"
]
```

**Proposed:**

```json
[
  "sea_m4",
  "sea_m8"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-282 — Western Egypt: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_western_egypt`, `sea_m9`, `sea_m8`

**Current:**

```json
[
  "sea_m9"
]
```

**Proposed:**

```json
[
  "sea_m8"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-283 — Lower Egypt: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_lower_egypt`, `sea_i5`, `sea_m9`, `sea_i5`, `sea_m8`

**Current:**

```json
[
  "sea_i5",
  "sea_m9"
]
```

**Proposed:**

```json
[
  "sea_i5",
  "sea_m8"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-284 — Nubia: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nubia`, `sea_i5`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_i5"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1650, 2700, 4550, 3800], "crop": "evidence/ea_north_africa.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-285 — French Somaliland: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_somaliland`, `sea_i5`, `sea_i4`

**Current:**

```json
[
  "sea_i5"
]
```

**Proposed:**

```json
[
  "sea_i4"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3990, 3480, 5190, 4540], "crop": "evidence/ea_east_africa.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-286 — Italian Somaliland: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_italian_somaliland`, `sea_i4`, `sea_i3`, `sea_i4`

**Current:**

```json
[
  "sea_i4"
]
```

**Proposed:**

```json
[
  "sea_i3",
  "sea_i4"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-287 — Tanganyika: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tanganyika`, `sea_i4`, `sea_i3`

**Current:**

```json
[
  "sea_i4"
]
```

**Proposed:**

```json
[
  "sea_i3"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-288 — Portuguese East Africa: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_portuguese_east_africa`, `sea_i4`, `sea_i1`

**Current:**

```json
[
  "sea_i4"
]
```

**Proposed:**

```json
[
  "sea_i1"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-289 — South Africa: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_south_africa`, `sea_a40`, `sea_i1`

**Current:**

```json
[
  "sea_a40"
]
```

**Proposed:**

```json
[
  "sea_i1"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-290 — Madagascar: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_madagascar`, `sea_i4`, `sea_i1`, `sea_i2`, `sea_i3`

**Current:**

```json
[
  "sea_i4"
]
```

**Proposed:**

```json
[
  "sea_i1",
  "sea_i2",
  "sea_i3"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-291 — Mauritius: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_mauritius`, `sea_i4`, `sea_i2`

**Current:**

```json
[
  "sea_i4"
]
```

**Proposed:**

```json
[
  "sea_i2"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-292 — Seychelles: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_seychelles`, `sea_i4`, `sea_i3`

**Current:**

```json
[
  "sea_i4"
]
```

**Proposed:**

```json
[
  "sea_i3"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-293 — Saudi Arabia: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_saudi_arabia`, `sea_i3`, `sea_i6`, `sea_i5`, `sea_i6`

**Current:**

```json
[
  "sea_i3",
  "sea_i6"
]
```

**Proposed:**

```json
[
  "sea_i5",
  "sea_i6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-294 — Aden: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_aden`, `sea_i3`, `sea_i4`

**Current:**

```json
[
  "sea_i3"
]
```

**Proposed:**

```json
[
  "sea_i4"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-295 — Qatar: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_qatar`, `sea_i7`, `sea_i6`

**Current:**

```json
[
  "sea_i7"
]
```

**Proposed:**

```json
[
  "sea_i6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-296 — Kuwait: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_kuwait`, `sea_i7`, `sea_i6`

**Current:**

```json
[
  "sea_i7"
]
```

**Proposed:**

```json
[
  "sea_i6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-297 — Southern Iraq: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southern_iraq`, `sea_i7`, `sea_i6`

**Current:**

```json
[
  "sea_i7"
]
```

**Proposed:**

```json
[
  "sea_i6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-298 — Southern Iran: sea access set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_iran_southern_iran`, `sea_i6`, `sea_i7`, `sea_i6`

**Current:**

```json
[
  "sea_i6",
  "sea_i7"
]
```

**Proposed:**

```json
[
  "sea_i6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Reciprocal physical coast edges. Re-transcribe facilities onto the correct access; moving an edge does not justify carrying an invented port with it. Preserve shore terrain separately.

## EA-304 — Northern Italy / M3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_northern_italy`, `sea_m3`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[
  "major_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-305 — Northern Italy / M5: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_northern_italy`, `sea_m5`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "major_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-306 — Rome / M3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rome`, `sea_m3`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[
  "seaplane_base"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-307 — Rome / M5: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rome`, `sea_m5`

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

## EA-308 — Lazio / M3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_lazio`, `sea_m3`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "major_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-309 — Southern Italy / M3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_southern_italy`, `sea_m3`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_southern_italy_20261006.png", "rectangle": [3050, 2270, 3560, 2840]}

**Scope / dependency:** Fresh re-audit: single white crane accesses M3. Replace old minor-port claims on M4/M5 using complete inventory.

## EA-310 — Western Yugoslavia / M5: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_yug_western_yugoslavia`, `sea_m5`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[
  "major_port",
  "minor_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-313 — Taurida / M11: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_taurida`, `sea_m11`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[
  "minor_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-314 — Crimea / M11: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_crimea`, `sea_m11`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[
  "major_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-316 — Transcaucasia / M12: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_transcaucasia`, `sea_m12`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_south.png", "rectangle": [3980, 1375, 5380, 2300]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Distinct white anchors on Black Sea and Caspian shores; two physical minor ports, not one two-sea port. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-317 — Northern Iran: inspected coast has no naval facility (sea_m12)

**Field:** `naval_facility_absence_confirmation` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_iran_northern_iran`, `sea_m12`

**Current:**

```json
{
  "coast_sea_id": "sea_m12",
  "previous_facility_proposal": []
}
```

**Proposed:**

```json
{
  "sea_id": "sea_m12",
  "expected_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_turkey_iran.png", "rectangle": [3850, 2050, 5580, 2980]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json. Confirmation of absence; this record does not add a facility.

## EA-319 — Syria / M9: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_syria`, `sea_m9`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[
  "major_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_turkey_iran.png", "rectangle": [3850, 2050, 5580, 2980]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-320 — Transjordan / M8: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_transjordan`, `sea_m8`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-321 — Kuwait / I6: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_kuwait`, `sea_i6`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-324 — Aden / I4: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_aden`, `sea_i4`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-325 — Tripoli / M4: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tripoli`, `sea_m4`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[
  "major_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_mediterranean_west.png", "rectangle": [2050, 1900, 3950, 3300]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-327 — Tobruk / M4: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tobruk`, `sea_m4`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. White-anchor symbol sits on the M4/M8 sea divider; one minor port with two accesses, correcting the earlier M4-only facility proposal. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-328 — Western Egypt / M8: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_western_egypt`, `sea_m8`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-329 — Lower Egypt / M8: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_lower_egypt`, `sea_m8`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "major_dockyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-330 — Lower Egypt / I5: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_lower_egypt`, `sea_i5`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[
  "major_port"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-332 — Nubia: inspected coast has no naval facility (sea_i5)

**Field:** `naval_facility_absence_confirmation` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nubia`, `sea_i5`

**Current:**

```json
{
  "coast_sea_id": "sea_i5",
  "previous_facility_proposal": []
}
```

**Proposed:**

```json
{
  "sea_id": "sea_i5",
  "expected_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json. Confirmation of absence; this record does not add a facility.

## EA-333 — French Somaliland / I4: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_somaliland`, `sea_i4`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-334 — Italian Somaliland / I3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_italian_somaliland`, `sea_i3`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-336 — Tanganyika / I3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tanganyika`, `sea_i3`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-338 — South Africa / I1: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_south_africa`, `sea_i1`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-339 — Madagascar / I3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_madagascar`, `sea_i3`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-340 — Madagascar: inspected coast has no naval facility (sea_i1)

**Field:** `naval_facility_absence_confirmation` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_madagascar`, `sea_i1`

**Current:**

```json
{
  "coast_sea_id": "sea_i1",
  "previous_facility_proposal": []
}
```

**Proposed:**

```json
{
  "sea_id": "sea_i1",
  "expected_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json. Confirmation of absence; this record does not add a facility.

## EA-341 — Madagascar: inspected coast has no naval facility (sea_i2)

**Field:** `naval_facility_absence_confirmation` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_madagascar`, `sea_i2`

**Current:**

```json
{
  "coast_sea_id": "sea_i2",
  "previous_facility_proposal": []
}
```

**Proposed:**

```json
{
  "sea_id": "sea_i2",
  "expected_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json. Confirmation of absence; this record does not add a facility.

## EA-342 — Mauritius / I2: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_mauritius`, `sea_i2`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-343 — Seychelles / I3: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_seychelles`, `sea_i3`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-369 — French Morocco: corrected Atlantic-facing coast

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_morocco`, `sea_a28`, `sea_a44`

**Current:**

```json
[
  "sea_a28"
]
```

**Proposed:**

```json
[
  "sea_a44"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1730, 2890, 3030, 3850], "crop": "evidence/ea_north_africa_west_detail.png"}

**Scope / dependency:** Sea numbering read from printed board and coordinated with Atlantic audit; not from geographic place-name guesses. Audit matching port/facility types before migrating old coastal infrastructure.

## EA-370 — Spanish Morocco: corrected Atlantic-facing coast

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_spanish_morocco`, `sea_a28`, `sea_a44`, `sea_m2`

**Current:**

```json
[
  "sea_a28"
]
```

**Proposed:**

```json
[
  "sea_a44",
  "sea_m2"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Sea numbering read from printed board and coordinated with Atlantic audit; not from geographic place-name guesses. Audit matching port/facility types before migrating old coastal infrastructure.

## EA-371 — Dahomey: corrected Atlantic-facing coast

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_dahomey`, `sea_a38`, `sea_a51`

**Current:**

```json
[
  "sea_a38"
]
```

**Proposed:**

```json
[
  "sea_a51"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}

**Scope / dependency:** Sea numbering read from printed board and coordinated with Atlantic audit; not from geographic place-name guesses. Audit matching port/facility types before migrating old coastal infrastructure.

## EA-372 — Nigeria: corrected Atlantic-facing coast

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nigeria`, `sea_a38`, `sea_a51`

**Current:**

```json
[
  "sea_a38"
]
```

**Proposed:**

```json
[
  "sea_a51"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}

**Scope / dependency:** Sea numbering read from printed board and coordinated with Atlantic audit; not from geographic place-name guesses. Audit matching port/facility types before migrating old coastal infrastructure.

## EA-373 — Cameroon: corrected Atlantic-facing coast

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cameroon`, `sea_a38`, `sea_a51`

**Current:**

```json
[
  "sea_a38"
]
```

**Proposed:**

```json
[
  "sea_a51"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1530, 3480, 3380, 4310], "crop": "evidence/ea_west_africa.png"}

**Scope / dependency:** Sea numbering read from printed board and coordinated with Atlantic audit; not from geographic place-name guesses. Audit matching port/facility types before migrating old coastal infrastructure.

## EA-374 — Southwest Africa: corrected Atlantic-facing coast

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_southwest_africa`, `sea_a39`, `sea_a53`, `sea_a54`

**Current:**

```json
[
  "sea_a39"
]
```

**Proposed:**

```json
[
  "sea_a53",
  "sea_a54"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}

**Scope / dependency:** Sea numbering read from printed board and coordinated with Atlantic audit; not from geographic place-name guesses. Audit matching port/facility types before migrating old coastal infrastructure.

## EA-375 — Cape Town: corrected Atlantic-facing coast

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cape_town`, `sea_a40`, `sea_a54`, `sea_i1`

**Current:**

```json
[
  "sea_a40"
]
```

**Proposed:**

```json
[
  "sea_a54",
  "sea_i1"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3180, 4120, 5330, 4840], "crop": "evidence/ea_south_africa.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [3480, 4540, 3910, 4888], "crop": "evidence/ea_cape_detail.png"}

**Scope / dependency:** Sea numbering read from printed board and coordinated with Atlantic audit; not from geographic place-name guesses. Audit matching port/facility types before migrating old coastal infrastructure. The A54/I1 sea seam meets Cape Town coast west of the Cape Town/South Africa land border; both sea accesses are real.

## EA-376 — Aquitaine: corrected Atlantic-facing coast

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_aquitaine`, `sea_a28`, `sea_a29`

**Current:**

```json
[
  "sea_a28"
]
```

**Proposed:**

```json
[
  "sea_a29"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Sea numbering read from printed board and coordinated with Atlantic audit; not from geographic place-name guesses. Audit matching port/facility types before migrating old coastal infrastructure.

## EA-377 — Southern France: corrected Atlantic-facing coast

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_southern_france`, `sea_a28`, `sea_m1`, `sea_m1`

**Current:**

```json
[
  "sea_a28",
  "sea_m1"
]
```

**Proposed:**

```json
[
  "sea_m1"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2050, 1900, 3950, 3300], "crop": "evidence/ea_mediterranean_west.png"}

**Scope / dependency:** Sea numbering read from printed board and coordinated with Atlantic audit; not from geographic place-name guesses. Audit matching port/facility types before migrating old coastal infrastructure.

## EA-378 — I1: descriptive sea label

**Field:** `name` · **Confidence:** high · **Severity:** minor

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i1`

**Current:**

Mozambique Channel

**Proposed:**

Mozambique Channel and southwest Indian Ocean

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Descriptive names are conveniences; the printed I-number is authoritative.

## EA-379 — I2: descriptive sea label

**Field:** `name` · **Confidence:** high · **Severity:** minor

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i2`

**Current:**

Sea Zone I2

**Proposed:**

Southwest Indian Ocean east of Madagascar

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Descriptive names are conveniences; the printed I-number is authoritative.

## EA-380 — I3: descriptive sea label

**Field:** `name` · **Confidence:** high · **Severity:** minor

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i3`

**Current:**

Red Sea

**Proposed:**

East African coast and Seychelles

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [3840, 3770, 5360, 4888], "crop": "evidence/ea_seas_south.png"}

**Scope / dependency:** Descriptive names are conveniences; the printed I-number is authoritative.

## EA-381 — I5: descriptive sea label

**Field:** `name` · **Confidence:** high · **Severity:** minor

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_i5`

**Current:**

Red Sea South

**Proposed:**

Red Sea

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [4230, 2760, 5460, 3910], "crop": "evidence/ea_arabia.png"}

**Scope / dependency:** Descriptive names are conveniences; the printed I-number is authoritative.

## EA-397 — A11 ↔ A12: Kaiser-Wilhelm Kanal

**Field:** `canal_or_strait` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `sea_a11`, `sea_a12`, `land_ger_western_germany`

**Current:**

Danish Straits

**Proposed:**

Kaiser-Wilhelm Kanal

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}
- {"source": "game_content/rules/Global War 1936 v4.3 Rulebook.pdf", "printed_page": 15}

**Scope / dependency:** The naval route crosses Western Germany. It is not an unconditionally open sea edge and is distinct from A10–A12 Danish Straits controlled by Denmark.

## EA-398 — Southern Norway: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_southern_norway`, `sea_a10`, `sea_a6`, `sea_a10`, `sea_a7`

**Current:**

```json
[
  "sea_a10",
  "sea_a6"
]
```

**Proposed:**

```json
[
  "sea_a10",
  "sea_a7"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-399 — Trondelag: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_trondelag`, `sea_a6`, `sea_a5`, `sea_a7`

**Current:**

```json
[
  "sea_a6"
]
```

**Proposed:**

```json
[
  "sea_a5",
  "sea_a7"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-400 — Norrland: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_swe_norrland`, `sea_a14`, `sea_a13`

**Current:**

```json
[
  "sea_a14"
]
```

**Proposed:**

```json
[
  "sea_a13"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-401 — Gotaland: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_swe_gotaland`, `sea_a12`, `sea_a13`, `sea_a10`, `sea_a12`, `sea_a13`

**Current:**

```json
[
  "sea_a12",
  "sea_a13"
]
```

**Proposed:**

```json
[
  "sea_a10",
  "sea_a12",
  "sea_a13"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-402 — Southern Finland: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_southern_finland`, `sea_a13`, `sea_a13`, `sea_a14`

**Current:**

```json
[
  "sea_a13"
]
```

**Proposed:**

```json
[
  "sea_a13",
  "sea_a14"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-403 — Viipuri Province: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_viipuri_province`, `sea_a14`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_a14"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-404 — Estonia: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_estonia`, `sea_a12`, `sea_a13`, `sea_a14`

**Current:**

```json
[
  "sea_a12",
  "sea_a13"
]
```

**Proposed:**

```json
[
  "sea_a14"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-405 — Latvia: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_latvia`, `sea_a12`, `sea_a14`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_a12",
  "sea_a14"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-406 — Lithuania: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_lithuania`, `sea_a12`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_a12"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-407 — West Poland: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_west_poland`, `sea_a12`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "sea_a12"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-408 — Denmark: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_denmark`, `sea_a10`, `sea_a12`, `sea_a23`, `sea_a10`, `sea_a11`, `sea_a12`

**Current:**

```json
[
  "sea_a10",
  "sea_a12",
  "sea_a23"
]
```

**Proposed:**

```json
[
  "sea_a10",
  "sea_a11",
  "sea_a12"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-409 — Western Germany: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_western_germany`, `sea_a12`, `sea_a23`, `sea_a11`, `sea_a12`

**Current:**

```json
[
  "sea_a12",
  "sea_a23"
]
```

**Proposed:**

```json
[
  "sea_a11",
  "sea_a12"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-410 — Netherlands: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_neu_netherlands`, `sea_a23`, `sea_a11`, `sea_a23`

**Current:**

```json
[
  "sea_a23"
]
```

**Proposed:**

```json
[
  "sea_a11",
  "sea_a23"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-411 — Leningrad: North Sea/Baltic coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_leningrad`, `sea_a12`, `sea_a14`

**Current:**

```json
[
  "sea_a12"
]
```

**Proposed:**

```json
[
  "sea_a14"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}

**Scope / dependency:** Physical sea coast membership only. Re-transcribe naval facilities, because current inferred ports use many wrong access zones.

## EA-412 — Southern Norway / A7: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_southern_norway`, `sea_a7`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_north_seas.png", "rectangle": [2100, 0, 4570, 1550]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-413 — Southern Norway / A10: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_southern_norway`, `sea_a10`

**Current:**

```json
[
  "minor_port"
]
```

**Proposed:**

```json
[
  "minor_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_north_seas.png", "rectangle": [2100, 0, 4570, 1550]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-415 — Trondelag: inspected coast has no naval facility (sea_a7)

**Field:** `naval_facility_absence_confirmation` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_trondelag`, `sea_a7`

**Current:**

```json
{
  "coast_sea_id": "sea_a7",
  "previous_facility_proposal": []
}
```

**Proposed:**

```json
{
  "sea_id": "sea_a7",
  "expected_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_norway_finland_20261006.png", "rectangle": [2890, 0, 4520, 690]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json. Confirmation of absence; this record does not add a facility.

## EA-417 — Gotaland / A10: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_swe_gotaland`, `sea_a10`

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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_germany_denmark_20261006.png", "rectangle": [2640, 740, 3650, 1330]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-418 — Southern Finland: inspected coast has no naval facility (sea_a14)

**Field:** `naval_facility_absence_confirmation` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_southern_finland`, `sea_a14`

**Current:**

```json
{
  "coast_sea_id": "sea_a14",
  "previous_facility_proposal": []
}
```

**Proposed:**

```json
{
  "sea_id": "sea_a14",
  "expected_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json. Confirmation of absence; this record does not add a facility.

## EA-419 — Viipuri Province: inspected coast has no naval facility (sea_a14)

**Field:** `naval_facility_absence_confirmation` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_viipuri_province`, `sea_a14`

**Current:**

```json
{
  "coast_sea_id": "sea_a14",
  "previous_facility_proposal": []
}
```

**Proposed:**

```json
{
  "sea_id": "sea_a14",
  "expected_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json. Confirmation of absence; this record does not add a facility.

## EA-420 — Estonia / A14: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_estonia`, `sea_a14`

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

## EA-422 — Latvia: inspected coast has no naval facility (sea_a12)

**Field:** `naval_facility_absence_confirmation` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_latvia`, `sea_a12`

**Current:**

```json
{
  "coast_sea_id": "sea_a12",
  "previous_facility_proposal": []
}
```

**Proposed:**

```json
{
  "sea_id": "sea_a12",
  "expected_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json. Confirmation of absence; this record does not add a facility.

## EA-423 — Lithuania: inspected coast has no naval facility (sea_a12)

**Field:** `naval_facility_absence_confirmation` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_lithuania`, `sea_a12`

**Current:**

```json
{
  "coast_sea_id": "sea_a12",
  "previous_facility_proposal": []
}
```

**Proposed:**

```json
{
  "sea_id": "sea_a12",
  "expected_facilities": []
}
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. No such symbol is printed; an available coast does not imply a facility. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json. Confirmation of absence; this record does not add a facility.

## EA-425 — Leningrad / A14: printed naval facilities

**Field:** `naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_leningrad`, `sea_a14`

**Current:**

```json
[]
```

**Proposed:**

```json
[
  "major_shipyard"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_baltic_20261006.png", "rectangle": [3340, 430, 4300, 1130]}

**Scope / dependency:** Fresh source-image naval re-audit 2026-10-06. Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Full physical facility roster and identity/access mapping: data/naval_reaudit_europe_africa_middle_east.json.

## EA-426 — Precise Arctic and Britain coast endpoints

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_scotland`, `land_gbr_northern_england`, `land_gbr_southern_england`, `land_gbr_london`, `land_fin_lapland`

**Current:**

```json
null
```

**Proposed:**

Resolved by second pass coast-set proposals: Scotland A4/A6/A17; Northern England A6/A17; Southern England A17/A21/A22/A23; London A22/A23; Lapland A8/A13.

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [2100, 0, 4570, 1550], "crop": "evidence/ea_north_seas.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [1700, 400, 2800, 3000], "crop": "evidence/ea_britain_iberia.png"}

**Scope / dependency:** Initial candidate A20 was rejected by tracing the sea boundary west of England.

## EA-427 — Missing islands at sea-border junctions

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_iceland`, `land_fin_helsinki`, `land_gre_crete`, `land_ita_rhodes`, `land_ita_sicily`

**Current:**

```json
null
```

**Proposed:**

Resolved: Helsinki A13/A14; Crete M7/M8; Rhodes M7; Sicily M3/M4/M6; Iceland A3/A4. Detailed neighbor_candidates findings supersede first-pass starter lists.

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [1400, 0, 2480, 1100], "crop": "evidence/ea_atlantic_islands.png"}
- {"source": "game_content/maps/gw36map.png", "rectangle": [2800, 1850, 4470, 3200], "crop": "evidence/ea_greece_mediterranean.png"}

**Scope / dependency:** No Crete–M6, Rhodes–M9 or Sicily–M2 contact was established. Positive coast segments, not point junctions, control access.

## EA-428 — Oman: three printed sea coasts

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_oman`, `sea_i4`, `sea_i6`, `sea_i7`

**Current:**

```json
[
  "sea_i6"
]
```

**Proposed:**

```json
[
  "sea_i4",
  "sea_i6",
  "sea_i7"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "rectangle": [5110, 3260, 5490, 3620], "crop": "evidence/ea_oman_detail.png"}

**Scope / dependency:** The I6/I7 diagonal reaches the northeastern headland; the I4/I7 vertical reaches the southeastern coast below the Oman roundel. A positive-length southwestern shore faces I4 before the Aden border. This refines AP-078's two-sea list.

## EA-443 — Ireland: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ireland`

**Current:**

```json
[
  "sea_a21",
  "sea_a22"
]
```

**Proposed:**

```json
[
  "sea_a17"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_britain_channels.png", "rectangle": [1690, 680, 2720, 1770]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-444 — Scotland: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_scotland`

**Current:**

```json
[
  "sea_a10",
  "sea_a6"
]
```

**Proposed:**

```json
[
  "sea_a17",
  "sea_a4",
  "sea_a6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_britain_channels.png", "rectangle": [1690, 680, 2720, 1770]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-445 — Northern England: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_northern_england`

**Current:**

```json
[
  "sea_a21"
]
```

**Proposed:**

```json
[
  "sea_a17",
  "sea_a6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_britain_channels.png", "rectangle": [1690, 680, 2720, 1770]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-446 — Southern England: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_southern_england`

**Current:**

```json
[
  "sea_a21",
  "sea_a23"
]
```

**Proposed:**

```json
[
  "sea_a17",
  "sea_a21",
  "sea_a22",
  "sea_a23"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_britain_channels.png", "rectangle": [1690, 680, 2720, 1770]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-447 — London: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_london`

**Current:**

```json
[
  "sea_a23"
]
```

**Proposed:**

```json
[
  "sea_a22",
  "sea_a23"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_britain_channels.png", "rectangle": [1690, 680, 2720, 1770]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-448 — Normandy: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_normandy`

**Current:**

```json
[
  "sea_a22",
  "sea_a23"
]
```

**Proposed:**

```json
[
  "sea_a21",
  "sea_a22",
  "sea_a29"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_britain_channels.png", "rectangle": [1690, 680, 2720, 1770]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-449 — Picardy: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_picardy`

**Current:**

```json
[
  "sea_a22",
  "sea_a23"
]
```

**Proposed:**

```json
[
  "sea_a22"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_britain_channels.png", "rectangle": [1690, 680, 2720, 1770]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-450 — Lapland: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_lapland`

**Current:**

```json
[
  "sea_a14"
]
```

**Proposed:**

```json
[
  "sea_a13",
  "sea_a8"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_finland_baltic.png", "rectangle": [3550, 0, 4380, 1550]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-451 — Albania: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_albania`

**Current:**

```json
[
  "sea_m5"
]
```

**Proposed:**

```json
[
  "sea_m5",
  "sea_m6"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-452 — Tunisia: second-pass complete coast set

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tunisia`

**Current:**

```json
[
  "sea_m2"
]
```

**Proposed:**

```json
[
  "sea_m2",
  "sea_m4"
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_greece_mediterranean.png", "rectangle": [2800, 1850, 4470, 3200]}

**Scope / dependency:** Positive shoreline segments traced; sea labels in existing JSON are misleading.

## EA-453 — Albania ↔ Eastern Yugoslavia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_albania`, `land_yug_eastern_yugoslavia`

**Current:**

```json
{
  "neighbor_id": "land_yug_eastern_yugoslavia",
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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_europe.png", "rectangle": [3250, 1050, 4900, 2400]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-454 — Albania ↔ Western Yugoslavia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_albania`, `land_yug_western_yugoslavia`

**Current:**

```json
{
  "neighbor_id": "land_yug_western_yugoslavia",
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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_europe.png", "rectangle": [3250, 1050, 4900, 2400]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-455 — Austria ↔ Slovakia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_aut_austria`, `land_cze_slovakia`

**Current:**

```json
{
  "neighbor_id": "land_cze_slovakia",
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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_west_europe.png", "rectangle": [2500, 1000, 3500, 2700]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-456 — Slovakia ↔ East Poland: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cze_slovakia`, `land_pol_east_poland`

**Current:**

```json
{
  "neighbor_id": "land_pol_east_poland",
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

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-457 — Slovakia ↔ Central Romania: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cze_slovakia`, `land_rom_central_romania`

**Current:**

```json
{
  "neighbor_id": "land_rom_central_romania",
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
}
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_poland.png", "rectangle": [3210, 850, 4170, 1780]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-458 — Viipuri Province ↔ Karelia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_viipuri_province`, `land_usr_karelia`

**Current:**

```json
{
  "neighbor_id": "land_usr_karelia",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": true,
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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_scandinavia.png", "rectangle": [2450, 0, 4200, 1200]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-459 — Lithuania ↔ West Poland: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_lithuania`, `land_pol_west_poland`

**Current:**

```json
{
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
```

**Proposed:**

```json
false
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_scandinavia.png", "rectangle": [2450, 0, 4200, 1200]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-460 — Southern Norway ↔ Trondelag: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_southern_norway`, `land_nor_trondelag`

**Current:**

```json
{
  "neighbor_id": "land_nor_trondelag",
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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_scandinavia.png", "rectangle": [2450, 0, 4200, 1200]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-461 — Podlachia ↔ Northern Belorussia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_podlachia`, `land_usr_northern_belorussia`

**Current:**

```json
{
  "neighbor_id": "land_usr_northern_belorussia",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": true,
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

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-462 — Bessarabia ↔ Western Ukraine: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_rom_bessarabia`, `land_usr_western_ukraine`

**Current:**

```json
{
  "neighbor_id": "land_usr_western_ukraine",
  "border_terrain": "normal",
  "passable": true,
  "has_river": false,
  "river_crossing": false,
  "railway_connection": true,
  "gauge_change": true,
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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_europe.png", "rectangle": [3250, 1050, 4900, 2400]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-463 — Ankara ↔ Karadeniz: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_ankara`, `land_tur_karadeniz`

**Current:**

```json
{
  "neighbor_id": "land_tur_karadeniz",
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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_turkey_iran.png", "rectangle": [3850, 2050, 5580, 2980]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-464 — Donets-Kuban ↔ Kalmytskaya: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_donets_kuban`, `land_usr_kalmytskaya`

**Current:**

```json
{
  "neighbor_id": "land_usr_kalmytskaya",
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

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-465 — Kaluga Oblast ↔ Western Russia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kaluga_oblast`, `land_usr_western_russia`

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

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-466 — Kiev ↔ Southern Ukraine: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_kiev`, `land_usr_southern_ukraine`

**Current:**

```json
{
  "neighbor_id": "land_usr_southern_ukraine",
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

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_western_ussr_north.png", "rectangle": [3775, 350, 5230, 1600]}

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-467 — Northern Belorussia ↔ Western Russia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_northern_belorussia`, `land_usr_western_russia`

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

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-468 — Orel-Kursk ↔ Tula-Lipetsk: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_orel_kursk`, `land_usr_tula_lipetsk`

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

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-469 — Saratov ↔ Tula-Lipetsk: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_saratov`, `land_usr_tula_lipetsk`

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

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-470 — Smolensk ↔ Western Russia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_smolensk`, `land_usr_western_russia`

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

**Scope / dependency:** Native second-pass track trace: there is a physical border, but no black-and-white railway crossing it. A track through a third territory is not a direct edge.

## EA-511 — Basque Country ↔ Madrid: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_basque_country`, `land_esp_madrid`

**Current:**

```json
{
  "neighbor_id": "land_esp_madrid",
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
```

**Proposed:**

```json
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** The printed black-and-white track crosses the shared territory boundary.

## EA-512 — Galicia and Leon ↔ Madrid: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_galicia_and_leon`, `land_esp_madrid`

**Current:**

```json
{
  "neighbor_id": "land_esp_madrid",
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
```

**Proposed:**

```json
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** The printed black-and-white track crosses the shared territory boundary.

## EA-513 — Eastern Andalucia ↔ Madrid: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_eastern_andalucia`, `land_esp_madrid`

**Current:**

```json
{
  "neighbor_id": "land_esp_madrid",
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
```

**Proposed:**

```json
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** The printed black-and-white track crosses the shared territory boundary.

## EA-514 — Western Andalucia ↔ Madrid: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_western_andalucia`, `land_esp_madrid`

**Current:**

```json
{
  "neighbor_id": "land_esp_madrid",
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
```

**Proposed:**

```json
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** The printed black-and-white track crosses the shared territory boundary.

## EA-515 — Eastern Andalucia ↔ Western Andalucia: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_eastern_andalucia`, `land_esp_western_andalucia`

**Current:**

```json
{
  "neighbor_id": "land_esp_western_andalucia",
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
```

**Proposed:**

```json
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_iberia.png", "rectangle": [1700, 2000, 2850, 2800]}

**Scope / dependency:** The printed black-and-white track crosses the shared territory boundary.

## EA-549 — Bohemia ↔ Bavaria: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cze_bohemia`, `land_ger_bavaria`

**Current:**

```json
{
  "neighbor_id": "land_ger_bavaria",
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

**Scope / dependency:** Native rail trace shows no railway across this direct boundary; routes enter a third territory.

## EA-550 — East Poland ↔ Lubelskie: railway_connection

**Field:** `railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_pol_east_poland`, `land_pol_lubelskie`

**Current:**

```json
{
  "neighbor_id": "land_pol_lubelskie",
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

**Scope / dependency:** Native rail trace shows no railway across this direct boundary; routes enter a third territory.

## EA-552 — Dahomey ↔ Nigeria: has_river

**Field:** `has_river` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_dahomey`, `land_nigeria`

**Current:**

```json
{
  "neighbor_id": "land_nigeria",
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
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sudan_west.png", "rectangle": [2600, 3470, 4480, 4460]}

**Scope / dependency:** A continuous printed blue river crosses or follows the shared territory boundary. This is a reciprocal geographic waterway-route proposal; directional river combat penalties remain controlled by the glossary and are not inferred here.

## EA-553 — Cameroon ↔ Nigeria: has_river

**Field:** `has_river` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cameroon`, `land_nigeria`

**Current:**

```json
{
  "neighbor_id": "land_nigeria",
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
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sudan_west.png", "rectangle": [2600, 3470, 4480, 4460]}

**Scope / dependency:** A continuous printed blue river crosses or follows the shared territory boundary. This is a reciprocal geographic waterway-route proposal; directional river combat penalties remain controlled by the glossary and are not inferred here.

## EA-554 — Chad ↔ Sudan: has_river

**Field:** `has_river` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_chad`, `land_sudan`

**Current:**

```json
{
  "neighbor_id": "land_sudan",
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
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sudan_west.png", "rectangle": [2600, 3470, 4480, 4460]}

**Scope / dependency:** A continuous printed blue river crosses or follows the shared territory boundary. This is a reciprocal geographic waterway-route proposal; directional river combat penalties remain controlled by the glossary and are not inferred here.

## EA-555 — Belgian Congo ↔ Oubangui-Chari: has_river

**Field:** `has_river` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_belgian_congo`, `land_oubangui_chari`

**Current:**

```json
{
  "neighbor_id": "land_oubangui_chari",
  "border_terrain": "jungle",
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
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sudan_west.png", "rectangle": [2600, 3470, 4480, 4460]}

**Scope / dependency:** A continuous printed blue river crosses or follows the shared territory boundary. This is a reciprocal geographic waterway-route proposal; directional river combat penalties remain controlled by the glossary and are not inferred here.

## EA-556 — Belgian Congo ↔ Cameroon: has_river

**Field:** `has_river` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_belgian_congo`, `land_cameroon`

**Current:**

```json
{
  "neighbor_id": "land_cameroon",
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
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sudan_west.png", "rectangle": [2600, 3470, 4480, 4460]}

**Scope / dependency:** A continuous printed blue river crosses or follows the shared territory boundary. This is a reciprocal geographic waterway-route proposal; directional river combat penalties remain controlled by the glossary and are not inferred here.

## EA-557 — Upper Egypt ↔ Nubia: has_river

**Field:** `has_river` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_upper_egypt`, `land_nubia`

**Current:**

```json
{
  "neighbor_id": "land_nubia",
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
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** A continuous printed blue river crosses or follows the shared territory boundary. This is a reciprocal geographic waterway-route proposal; directional river combat penalties remain controlled by the glossary and are not inferred here.

## EA-558 — Lower Egypt ↔ Upper Egypt: has_river

**Field:** `has_river` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_lower_egypt`, `land_upper_egypt`

**Current:**

```json
{
  "neighbor_id": "land_upper_egypt",
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
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** A continuous printed blue river crosses or follows the shared territory boundary. This is a reciprocal geographic waterway-route proposal; directional river combat penalties remain controlled by the glossary and are not inferred here.

## EA-559 — Sudan ↔ Nubia: has_river

**Field:** `has_river` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_sudan`, `land_nubia`

**Current:**

```json
{
  "neighbor_id": "land_nubia",
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
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** A continuous printed blue river crosses or follows the shared territory boundary. This is a reciprocal geographic waterway-route proposal; directional river combat penalties remain controlled by the glossary and are not inferred here.

## EA-560 — Niger ↔ Dahomey: has_river

**Field:** `has_river` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_niger`, `land_dahomey`

**Current:**

```json
null
```

**Proposed:**

```json
true
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_sudan_west.png", "rectangle": [2600, 3470, 4480, 4460]}

**Scope / dependency:** A continuous printed blue river crosses or follows the shared territory boundary. This is a reciprocal geographic waterway-route proposal; directional river combat penalties remain controlled by the glossary and are not inferred here.

## EA-561 — Scotland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_scotland`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_scotland_minor_port",
    "sea_id": "sea_a10"
  },
  {
    "type": "minor_port",
    "id": "facility_scotland_minor_port",
    "sea_id": "sea_a6"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_scotland_major_port_north",
    "type": "major_port",
    "sea_accesses": [
      "sea_a4",
      "sea_a6"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_scotland_20261006.png",
        "rectangle": [
          2090,
          550,
          2520,
          1070
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_scotland_major_shipyard_west",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a4"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_scotland_20261006.png",
        "rectangle": [
          2090,
          550,
          2520,
          1070
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_scotland_major_shipyard_east",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a6"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_scotland_20261006.png",
        "rectangle": [
          2090,
          550,
          2520,
          1070
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_scotland_20261006.png", "rectangle": [2090, 550, 2520, 1070]}

**Scope / dependency:** Northern blue-anchor port lies on the A4/A6 sea divider, one physical port with two accesses. West/east blue cranes are separate shipyards. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-562 — Northern England: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_northern_england`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_northern_england_minor_port",
    "sea_id": "sea_a21"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_northern_england_major_shipyard_east",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a6"
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
  },
  {
    "id": "facility_northern_england_major_shipyard_west",
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

## EA-563 — Southern England: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_southern_england`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_southern_england_minor_port",
    "sea_id": "sea_a21"
  },
  {
    "type": "minor_port",
    "id": "facility_southern_england_minor_port",
    "sea_id": "sea_a23"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_southern_england_minor_dockyard",
    "type": "minor_dockyard",
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
  },
  {
    "id": "facility_southern_england_major_shipyard_southwest",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a21"
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
  },
  {
    "id": "facility_southern_england_major_shipyard_south",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a22"
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
  },
  {
    "id": "facility_southern_england_seaplane_base_west",
    "type": "seaplane_base",
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
  },
  {
    "id": "facility_southern_england_seaplane_base_east",
    "type": "seaplane_base",
    "sea_accesses": [
      "sea_a23"
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

**Scope / dependency:** Two separate blue cranes, two separate green airplane-over-waves bases and one white circled-anchor dockyard. Do not merge symbols or infer further facilities from coastline. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-564 — London: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_gbr_london`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_london_minor_port",
    "sea_id": "sea_a23"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_london_major_shipyard",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a22",
      "sea_a23"
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

**Scope / dependency:** The single blue crane sits at the A22/A23 sea divider; both accesses refer to one physical shipyard. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-566 — Ireland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ireland`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_ireland_minor_port",
    "sea_id": "sea_a21"
  },
  {
    "type": "minor_port",
    "id": "facility_land_ireland_minor_port",
    "sea_id": "sea_a22"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_ireland_major_dockyard",
    "type": "major_dockyard",
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

## EA-567 — Normandy: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_normandy`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_normandy_minor_port",
    "sea_id": "sea_a23"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_normandy_major_shipyard_west",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a21"
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
  },
  {
    "id": "facility_normandy_major_shipyard_north",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a22"
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

## EA-568 — Picardy: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_picardy`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_picardy_minor_port",
    "sea_id": "sea_a22"
  },
  {
    "type": "minor_port",
    "id": "facility_picardy_minor_port",
    "sea_id": "sea_a23"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_picardy_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a22"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_france.png",
        "rectangle": [
          2220,
          1180,
          3070,
          2110
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_france.png", "rectangle": [2220, 1180, 3070, 2110]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-569 — Aquitaine: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_aquitaine`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_aquitaine_minor_port",
    "sea_id": "sea_a28"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_aquitaine_major_shipyard",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a29"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_france.png",
        "rectangle": [
          2220,
          1180,
          3070,
          2110
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_aquitaine_seaplane_base",
    "type": "seaplane_base",
    "sea_accesses": [
      "sea_a29"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_france.png",
        "rectangle": [
          2220,
          1180,
          3070,
          2110
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_france.png", "rectangle": [2220, 1180, 3070, 2110]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-570 — Southern France: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fra_southern_france`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_southern_france_minor_port",
    "sea_id": "sea_a28"
  },
  {
    "type": "minor_port",
    "id": "facility_southern_france_minor_port",
    "sea_id": "sea_m1"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_southern_france_major_shipyard",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_m1"
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

## EA-573 — Belgium: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_neu_belgium`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_belgium_minor_port",
    "sea_id": "sea_a23"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_belgium_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a23"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_france.png",
        "rectangle": [
          2220,
          1180,
          3070,
          2110
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_france.png", "rectangle": [2220, 1180, 3070, 2110]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-574 — Netherlands: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_neu_netherlands`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_netherlands_minor_port",
    "sea_id": "sea_a23"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_netherlands_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_a23"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_germany_denmark_20261006.png",
        "rectangle": [
          2640,
          740,
          3650,
          1330
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_germany_denmark_20261006.png", "rectangle": [2640, 740, 3650, 1330]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-575 — Western Germany: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_western_germany`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_western_germany_minor_port",
    "sea_id": "sea_a12"
  },
  {
    "type": "minor_port",
    "id": "facility_western_germany_minor_port",
    "sea_id": "sea_a23"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_western_germany_major_shipyard_west",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a11"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_germany_denmark_20261006.png",
        "rectangle": [
          2640,
          740,
          3650,
          1330
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_western_germany_major_shipyard_east",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a12"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_germany_denmark_20261006.png",
        "rectangle": [
          2640,
          740,
          3650,
          1330
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_western_germany_seaplane_base",
    "type": "seaplane_base",
    "sea_accesses": [
      "sea_a11"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_germany_denmark_20261006.png",
        "rectangle": [
          2640,
          740,
          3650,
          1330
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_western_germany_submarine_base",
    "type": "submarine_base",
    "sea_accesses": [
      "sea_a11"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_germany_denmark_20261006.png",
        "rectangle": [
          2640,
          740,
          3650,
          1330
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_germany_denmark_20261006.png", "rectangle": [2640, 740, 3650, 1330]}

**Scope / dependency:** Two separate blue cranes (A11 and A12); green airplane-over-waves base and blue vertical-submarine silhouette on A11. None is a generic minor port. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-576 — Eastern Germany: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_eastern_germany`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_eastern_germany_minor_port",
    "sea_id": "sea_a12"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_eastern_germany_major_shipyard",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_a12"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_germany_denmark_20261006.png",
        "rectangle": [
          2640,
          740,
          3650,
          1330
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_germany_denmark_20261006.png", "rectangle": [2640, 740, 3650, 1330]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-577 — Konigsberg: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ger_konigsberg`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_konigsberg_minor_port",
    "sea_id": "sea_a12"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_konigsberg_major_shipyard",
    "type": "major_shipyard",
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

## EA-578 — Denmark: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_denmark`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_denmark_minor_port",
    "sea_id": "sea_a10"
  },
  {
    "type": "minor_port",
    "id": "facility_land_denmark_minor_port",
    "sea_id": "sea_a12"
  },
  {
    "type": "minor_port",
    "id": "facility_land_denmark_minor_port",
    "sea_id": "sea_a23"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_denmark_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a10"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_germany_denmark_20261006.png",
        "rectangle": [
          2640,
          740,
          3650,
          1330
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_denmark_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_a12"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_germany_denmark_20261006.png",
        "rectangle": [
          2640,
          740,
          3650,
          1330
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_germany_denmark_20261006.png", "rectangle": [2640, 740, 3650, 1330]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-579 — Gotaland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_swe_gotaland`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_gotaland_minor_port",
    "sea_id": "sea_a12"
  },
  {
    "type": "minor_port",
    "id": "facility_gotaland_minor_port",
    "sea_id": "sea_a13"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_gotaland_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_a10"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_germany_denmark_20261006.png",
        "rectangle": [
          2640,
          740,
          3650,
          1330
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_germany_denmark_20261006.png", "rectangle": [2640, 740, 3650, 1330]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-581 — Southern Norway: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nor_southern_norway`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_southern_norway_minor_port",
    "sea_id": "sea_a10"
  },
  {
    "type": "minor_port",
    "id": "facility_southern_norway_minor_port",
    "sea_id": "sea_a6"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_southern_norway_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a7"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_north_seas.png",
        "rectangle": [
          2100,
          0,
          4570,
          1550
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_southern_norway_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_a10"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_north_seas.png",
        "rectangle": [
          2100,
          0,
          4570,
          1550
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_north_seas.png", "rectangle": [2100, 0, 4570, 1550]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-584 — Southern Finland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_fin_southern_finland`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_southern_finland_minor_port",
    "sea_id": "sea_a13"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_southern_finland_minor_port",
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

## EA-586 — Estonia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_estonia`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_estonia_minor_port",
    "sea_id": "sea_a12"
  },
  {
    "type": "minor_port",
    "id": "facility_land_estonia_minor_port",
    "sea_id": "sea_a13"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_estonia_minor_shipyard",
    "type": "minor_shipyard",
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

## EA-589 — Leningrad: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_leningrad`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_leningrad_minor_port",
    "sea_id": "sea_a12"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_leningrad_major_shipyard",
    "type": "major_shipyard",
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

## EA-593 — Catalonia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_catalonia`

**Current:**

```json
[
  {
    "type": "major_port",
    "id": "facility_catalonia_major_port",
    "sea_id": "sea_m1"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_catalonia_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_m1"
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

## EA-594 — Eastern Andalucia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_eastern_andalucia`

**Current:**

```json
[
  {
    "type": "minor_shipyard",
    "id": "facility_eastern_andalucia_minor_shipyard",
    "sea_id": "sea_m2"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_eastern_andalucia_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_m2"
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

## EA-595 — Western Andalucia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_esp_western_andalucia`

**Current:**

```json
[
  {
    "type": "major_port",
    "id": "facility_western_andalucia_major_port",
    "sea_id": "sea_a44"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_western_andalucia_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_a44"
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

## EA-598 — Northern Italy: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_northern_italy`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_northern_italy_minor_port",
    "sea_id": "sea_m3"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_northern_italy_major_shipyard_west",
    "type": "major_shipyard",
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
  },
  {
    "id": "facility_northern_italy_major_shipyard_east",
    "type": "major_shipyard",
    "sea_accesses": [
      "sea_m5"
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

## EA-599 — Rome: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_rome`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_rome_minor_port",
    "sea_id": "sea_m3"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_rome_seaplane_base",
    "type": "seaplane_base",
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
  },
  {
    "id": "facility_rome_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_m5"
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

## EA-600 — Lazio: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_lazio`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_lazio_minor_port",
    "sea_id": "sea_m4"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_lazio_major_shipyard",
    "type": "major_shipyard",
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

## EA-601 — Southern Italy: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_ita_southern_italy`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_southern_italy_minor_port",
    "sea_id": "sea_m4"
  },
  {
    "type": "minor_port",
    "id": "facility_southern_italy_minor_port",
    "sea_id": "sea_m5"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_southern_italy_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_m3"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_naval_southern_italy_20261006.png",
        "rectangle": [
          3050,
          2270,
          3560,
          2840
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_naval_southern_italy_20261006.png", "rectangle": [3050, 2270, 3560, 2840]}

**Scope / dependency:** Single white-crane minor shipyard on the Tyrrhenian (M3) coast well north of the Sicily/Southern Italy narrow crossing. No additional facility on M5/M6.

## EA-604 — Western Yugoslavia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_yug_western_yugoslavia`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_western_yugoslavia_minor_port",
    "sea_id": "sea_m5"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_western_yugoslavia_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_m5"
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
  },
  {
    "id": "facility_western_yugoslavia_minor_shipyard",
    "type": "minor_shipyard",
    "sea_accesses": [
      "sea_m5"
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

## EA-605 — Albania: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_albania`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_albania_minor_port",
    "sea_id": "sea_m5"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_albania_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m5"
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

## EA-611 — Bulgaria: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_bulgaria`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_bulgaria_minor_port",
    "sea_id": "sea_m10"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_bulgaria_minor_port",
    "type": "minor_port",
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

## EA-615 — Taurida: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_taurida`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_taurida_minor_port",
    "sea_id": "sea_m11"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_taurida_minor_shipyard",
    "type": "minor_shipyard",
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

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-616 — Crimea: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_crimea`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_crimea_minor_port",
    "sea_id": "sea_m10"
  },
  {
    "type": "minor_port",
    "id": "facility_crimea_minor_port",
    "sea_id": "sea_m11"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_crimea_major_shipyard",
    "type": "major_shipyard",
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

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-618 — North-Caucasia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_north_caucasia`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_north_caucasia_minor_port",
    "sea_id": "sea_m11"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_north_caucasia_seaplane_base",
    "type": "seaplane_base",
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

**Scope / dependency:** Airplane-over-waves symbol is on North-Caucasia M11 coast. The white-anchor port farther south belongs to Transcaucasia; remove the current generic minor-port claim. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-620 — Transcaucasia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_usr_transcaucasia`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_transcaucasia_minor_port",
    "sea_id": "sea_m11"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_transcaucasia_minor_port_black_sea",
    "type": "minor_port",
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
  },
  {
    "id": "facility_transcaucasia_minor_port_caspian",
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

**Scope / dependency:** Distinct white anchors on Black Sea and Caspian shores; two physical minor ports, not one two-sea port. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-621 — Istanbul: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_istanbul`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_istanbul_minor_port",
    "sea_id": "sea_m10"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_istanbul_major_port_aegean",
    "type": "major_port",
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
  },
  {
    "id": "facility_istanbul_major_port_black_sea",
    "type": "major_port",
    "sea_accesses": [
      "sea_m10"
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
  },
  {
    "id": "facility_istanbul_minor_shipyard",
    "type": "minor_shipyard",
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

## EA-622 — Karadeniz: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tur_karadeniz`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_karadeniz_minor_port",
    "sea_id": "sea_m11"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_karadeniz_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m11"
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

## EA-624 — Syria: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_syria`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_syria_minor_port",
    "sea_id": "sea_m9"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_syria_major_port",
    "type": "major_port",
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

## EA-625 — Southern Iran: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_iran_southern_iran`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_southern_iran_minor_port",
    "sea_id": "sea_i6"
  },
  {
    "type": "minor_port",
    "id": "facility_southern_iran_minor_port",
    "sea_id": "sea_i7"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_southern_iran_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_i6"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_arabia.png",
        "rectangle": [
          4230,
          2760,
          5460,
          3910
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** White ordinary anchor is on I6; no facility is shown on the erroneous old I7 access. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-627 — Kuwait: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_kuwait`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_kuwait_minor_port",
    "sea_id": "sea_i7"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_kuwait_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_i6"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_arabia.png",
        "rectangle": [
          4230,
          2760,
          5460,
          3910
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-630 — Aden: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_aden`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_aden_minor_port",
    "sea_id": "sea_i3"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_aden_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_i4"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_arabia.png",
        "rectangle": [
          4230,
          2760,
          5460,
          3910
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-631 — Transjordan: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_transjordan`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_transjordan_minor_port",
    "sea_id": "sea_m9"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_transjordan_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m8"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_arabia.png",
        "rectangle": [
          4230,
          2760,
          5460,
          3910
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_arabia.png", "rectangle": [4230, 2760, 5460, 3910]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-632 — Lower Egypt: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_lower_egypt`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_egypt_minor_port",
    "sea_id": "sea_i5"
  },
  {
    "type": "minor_port",
    "id": "facility_egypt_minor_port",
    "sea_id": "sea_m9"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_lower_egypt_major_dockyard",
    "type": "major_dockyard",
    "sea_accesses": [
      "sea_m8"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_round2_nile.png",
        "rectangle": [
          3800,
          2990,
          4790,
          4000
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  },
  {
    "id": "facility_lower_egypt_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_i5"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_round2_nile.png",
        "rectangle": [
          3800,
          2990,
          4790,
          4000
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-634 — Western Egypt: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_western_egypt`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_egypt_minor_port",
    "sea_id": "sea_m9"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_western_egypt_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_m8"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_round2_nile.png",
        "rectangle": [
          3800,
          2990,
          4790,
          4000
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-635 — Tobruk: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tobruk`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_tobruk_minor_port",
    "sea_id": "sea_m8"
  },
  {
    "type": "minor_port",
    "id": "facility_land_tobruk_minor_port",
    "sea_id": "sea_m9"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_tobruk_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_m4",
      "sea_m8"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_round2_nile.png",
        "rectangle": [
          3800,
          2990,
          4790,
          4000
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_round2_nile.png", "rectangle": [3800, 2990, 4790, 4000]}

**Scope / dependency:** White-anchor symbol sits on the M4/M8 sea divider; one minor port with two accesses, correcting the earlier M4-only facility proposal. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-637 — Tripoli: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tripoli`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_tripoli_minor_port",
    "sea_id": "sea_m4"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_tripoli_major_port",
    "type": "major_port",
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

## EA-638 — Tunisia: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tunisia`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_tunisia_minor_port",
    "sea_id": "sea_m2"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_tunisia_minor_port",
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

**Scope / dependency:** White anchor is on the M4-facing eastern coast below the M2/M4 dividing-line endpoint. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-639 — Northern Algeria: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_northern_algeria`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_algeria_minor_port",
    "sea_id": "sea_m2"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_northern_algeria_major_port",
    "type": "major_port",
    "sea_accesses": [
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

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-640 — Spanish Morocco: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_spanish_morocco`

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
[
  {
    "id": "facility_spanish_morocco_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_a44"
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

**Scope / dependency:** White-anchor minor port faces A44 only, west of the A44/M2 dividing line. The separate M2 coast does not share that facility. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-645 — Dahomey: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_dahomey`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_dahomey_minor_port",
    "sea_id": "sea_a38"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_dahomey_minor_port",
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

## EA-646 — Nigeria: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_nigeria`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_nigeria_minor_port",
    "sea_id": "sea_a38"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_nigeria_minor_port",
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

## EA-647 — Cameroon: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cameroon`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_cameroon_minor_port",
    "sea_id": "sea_a38"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_cameroon_minor_port",
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

## EA-652 — Cape Town: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_cape_town`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_town_minor_port",
    "sea_id": "sea_a40"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_cape_town_minor_dockyard",
    "type": "minor_dockyard",
    "sea_accesses": [
      "sea_a54"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_south_africa.png",
        "rectangle": [
          3180,
          4120,
          5330,
          4840
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** White circled-anchor symbol is a minor dockyard on A54, west of the A54/I1 divider. Rulebook p16 supply example calls Cape Town a minor port, but the printed board symbol differs; this roster records the board symbol and retains that source-version discrepancy in notes. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-653 — South Africa: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_south_africa`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_africa_minor_port",
    "sea_id": "sea_a40"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_south_africa_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_i1"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_south_africa.png",
        "rectangle": [
          3180,
          4120,
          5330,
          4840
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-655 — Tanganyika: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_tanganyika`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_tanganyika_minor_port",
    "sea_id": "sea_i4"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_tanganyika_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_i3"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_east_africa.png",
        "rectangle": [
          3990,
          3480,
          5190,
          4540
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-656 — Italian Somaliland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_italian_somaliland`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_somaliland_minor_port",
    "sea_id": "sea_i4"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_italian_somaliland_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_i3"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_east_africa.png",
        "rectangle": [
          3990,
          3480,
          5190,
          4540
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-657 — British Somaliland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_british_somaliland`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_somaliland_minor_port",
    "sea_id": "sea_i4"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_british_somaliland_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_i4"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_east_africa.png",
        "rectangle": [
          3990,
          3480,
          5190,
          4540
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-658 — French Somaliland: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_french_somaliland`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_somaliland_minor_port",
    "sea_id": "sea_i5"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_french_somaliland_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_i4"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_east_africa.png",
        "rectangle": [
          3990,
          3480,
          5190,
          4540
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-659 — Eritrea: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_eritrea`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_eritrea_minor_port",
    "sea_id": "sea_i5"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_eritrea_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_i5"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_east_africa.png",
        "rectangle": [
          3990,
          3480,
          5190,
          4540
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_east_africa.png", "rectangle": [3990, 3480, 5190, 4540]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-660 — Madagascar: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_madagascar`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_madagascar_minor_port",
    "sea_id": "sea_i4"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_madagascar_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_i3"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_south_africa.png",
        "rectangle": [
          3180,
          4120,
          5330,
          4840
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-661 — Mauritius: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_mauritius`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_mauritius_minor_port",
    "sea_id": "sea_i4"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_mauritius_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_i2"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_south_africa.png",
        "rectangle": [
          3180,
          4120,
          5330,
          4840
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## EA-662 — Seychelles: source-verified complete naval facility roster

**Field:** `naval_facility_inventory` · **Confidence:** high · **Severity:** major

**Regional context:** [europe_africa_middle_east](regions/europe_africa_middle_east.md)

**Nodes:** `land_seychelles`

**Current:**

```json
[
  {
    "type": "minor_port",
    "id": "facility_land_seychelles_minor_port",
    "sea_id": "sea_i4"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_seychelles_minor_port",
    "type": "minor_port",
    "sea_accesses": [
      "sea_i3"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "crop": "evidence/ea_south_africa.png",
        "rectangle": [
          3180,
          4120,
          5330,
          4840
        ]
      }
    ],
    "notes": "Printed symbol; facility identity is independent of sea-access edges."
  }
]
```

**Evidence:**

- {"source": "game_content/maps/gw36map.png", "crop": "evidence/ea_south_africa.png", "rectangle": [3180, 4120, 5330, 4840]}

**Scope / dependency:** Full printed coast scanned for port, dockyard, shipyard, seaplane-base and submarine-base symbols. Distinct symbols remain separate physical facilities. Replace old facility claims with this complete physical-instance roster; retain a single ID for a verified multi-sea facility.

## AP-037 — Replace tundra/normal/jungle assignments with printed mountain terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_irkutsk`, `land_usr_angara`, `land_usr_yakutsk`, `land_usr_magadan`, `land_usr_kamchatka`, `land_usr_amur`, `land_usr_chita`, `land_usr_buryatia`, `land_usr_primorsky_krai`, `land_usr_north_sakhalin`, `land_usr_south_sakhalin`, `land_jap_kurile_islands`, `land_jap_volcanic_islands`, `land_nz_north_island`, `land_nz_south_island`, `land_aus_tasmania`, `land_luzon_and_the_visayas`, `land_mindanao`

**Current:**

```json
{
  "land_usr_irkutsk": {
    "terrain": "tundra"
  },
  "land_usr_angara": {
    "terrain": "tundra"
  },
  "land_usr_yakutsk": {
    "terrain": "tundra"
  },
  "land_usr_magadan": {
    "terrain": "tundra"
  },
  "land_usr_kamchatka": {
    "terrain": "tundra"
  },
  "land_usr_amur": {
    "terrain": "tundra"
  },
  "land_usr_chita": {
    "terrain": "tundra"
  },
  "land_usr_buryatia": {
    "terrain": "tundra"
  },
  "land_usr_primorsky_krai": {
    "terrain": "tundra"
  },
  "land_usr_north_sakhalin": {
    "terrain": "tundra"
  },
  "land_usr_south_sakhalin": {
    "terrain": "tundra"
  },
  "land_jap_kurile_islands": {
    "terrain": "normal"
  },
  "land_jap_volcanic_islands": {
    "terrain": "normal"
  },
  "land_nz_north_island": {
    "terrain": "normal"
  },
  "land_nz_south_island": {
    "terrain": "normal"
  },
  "land_aus_tasmania": {
    "terrain": "normal"
  },
  "land_luzon_and_the_visayas": {
    "terrain": "jungle"
  },
  "land_mindanao": {
    "terrain": "jungle"
  }
}
```

**Proposed:**

```json
{
  "land_usr_irkutsk": "mountain",
  "land_usr_angara": "mountain",
  "land_usr_yakutsk": "mountain",
  "land_usr_magadan": "mountain",
  "land_usr_kamchatka": "mountain",
  "land_usr_amur": "mountain",
  "land_usr_chita": "mountain",
  "land_usr_buryatia": "mountain",
  "land_usr_primorsky_krai": "mountain",
  "land_usr_north_sakhalin": "mountain",
  "land_usr_south_sakhalin": "mountain",
  "land_jap_kurile_islands": "mountain",
  "land_jap_volcanic_islands": "mountain",
  "land_nz_north_island": "mountain",
  "land_nz_south_island": "mountain",
  "land_aus_tasmania": "mountain",
  "land_luzon_and_the_visayas": "mountain",
  "land_mindanao": "mountain"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- evidence/ap_sakhalin.png; evidence/ap_se_asia.png; evidence/ap_australia.png; Terrain Glossary pp2–4,12.

**Scope / dependency:** Philippine landing terrain needs the same correction on sea→land edges, including previously reviewed P41→Luzon. Do not infer jungle from green ownership fill. South Sakhalin also needs ownership correction below.

## AP-038 — Local mountain/desert graphics do not make these entire land zones mountain/desert/tundra

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_stalino`, `land_usr_vanavara`, `land_usr_southern_yakutia`, `land_aus_western_australia`, `land_aus_northern_territory`, `land_aus_south_australia`

**Current:**

```json
{
  "land_usr_stalino": {
    "terrain": "tundra"
  },
  "land_usr_vanavara": {
    "terrain": "tundra"
  },
  "land_usr_southern_yakutia": {
    "terrain": "tundra"
  },
  "land_aus_western_australia": {
    "terrain": "desert"
  },
  "land_aus_northern_territory": {
    "terrain": "desert"
  },
  "land_aus_south_australia": {
    "terrain": "desert"
  }
}
```

**Proposed:**

```json
{
  "land_usr_stalino": "normal",
  "land_usr_vanavara": "normal",
  "land_usr_southern_yakutia": "normal",
  "land_aus_western_australia": "normal",
  "land_aus_northern_territory": "normal",
  "land_aus_south_australia": "normal"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- evidence/ap_australia.png; Terrain Glossary pp3,12.

**Scope / dependency:** Keep directional border mountains and impassable Outback segments separately. Northern Territory and Western Australia still have specific mountain approaches.

## AP-039 — Land zones with simultaneous mountain and jungle terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_hainan`, `land_annam_tonkin`, `land_british_malaya`, `land_sarawak`, `land_java`, `land_celebes`, `land_timor`, `land_dutch_new_guinea`, `land_new_guinea`

**Current:**

```json
{
  "land_hainan": {
    "terrain": "mountain"
  },
  "land_annam_tonkin": {
    "terrain": "jungle"
  },
  "land_british_malaya": {
    "terrain": "jungle"
  },
  "land_sarawak": {
    "terrain": "jungle"
  },
  "land_java": {
    "terrain": "jungle"
  },
  "land_celebes": {
    "terrain": "jungle"
  },
  "land_timor": {
    "terrain": "normal"
  },
  "land_dutch_new_guinea": {
    "terrain": "jungle"
  },
  "land_new_guinea": {
    "terrain": "jungle"
  }
}
```

**Proposed:**

```json
{
  "land_hainan": [
    "mountain",
    "jungle"
  ],
  "land_annam_tonkin": [
    "mountain",
    "jungle"
  ],
  "land_british_malaya": [
    "mountain",
    "jungle"
  ],
  "land_sarawak": [
    "mountain",
    "jungle"
  ],
  "land_java": [
    "mountain",
    "jungle"
  ],
  "land_celebes": [
    "mountain",
    "jungle"
  ],
  "land_timor": [
    "mountain",
    "jungle"
  ],
  "land_dutch_new_guinea": [
    "mountain",
    "jungle"
  ],
  "land_new_guinea": [
    "mountain",
    "jungle"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6250, 2600, 8250, 4030); evidence/ap_se_asia.png
- Terrain Glossary pp2–4.

**Scope / dependency:** Current scalar node terrain cannot represent this faithfully. Use root schema proposal; preserve combined sea landing/border terrain rather than selecting one effect. Hainan presently only mountain; all others omit at least one printed terrain.

## AP-040 — Ceylon is jungle terrain

**Field:** `terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_india_ceylon`

**Current:**

normal

**Proposed:**

jungle

**Evidence:**

- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png
- Terrain Glossary p3.

## AP-041 — South Sakhalin is Japanese territory

**Field:** `original_owner/current_owner` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_south_sakhalin`

**Current:**

```json
{
  "land_usr_south_sakhalin": {
    "original_owner": "Soviet Union",
    "current_owner": "Soviet Union"
  }
}
```

**Proposed:**

```json
{
  "original_owner": "Japan",
  "current_owner": "scenario setup"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7270, 1320, 8170, 2100); evidence/ap_sakhalin.png

**Scope / dependency:** Printed Japanese roundel is unambiguous. Prefix land_usr_ is misleading; if renamed, supply an alias/migration. Mutable current owner belongs to setup/state.

## AP-042 — Kashmir uses the FEC roundel

**Field:** `original_owner` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_kashmir`

**Current:**

Kashmir

**Proposed:**

FEC

**Evidence:**

- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png
- Terrain Glossary p3 lists Kashmir under Far East Command.

## AP-043 — Novosibirsk is a mountain city worth 3 IPP

**Field:** `terrain/ipp_value/is_city` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_novosibirsk`

**Current:**

```json
{
  "land_usr_novosibirsk": {
    "terrain": "normal",
    "ipp_value": 1,
    "is_city": true
  }
}
```

**Proposed:**

```json
{
  "terrain": "mountain",
  "ipp_value": 3,
  "is_city": true
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4300, 1200, 6400, 2500); evidence/ap_central_asia.png
- Terrain Glossary p12; source roundel shows 3. Circular land boundary preserves city status under Rulebook §1.7.7 p13.

## AP-044 — Printed IPP corrections across Soviet East, Malaya and Oceania

**Field:** `ipp_value` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_amur`, `land_usr_chita`, `land_usr_buryatia`, `land_british_malaya`, `land_sarawak`, `land_aus_new_south_wales`, `land_nz_south_island`, `land_new_britain`, `land_timor`

**Current:**

```json
{
  "land_usr_amur": {
    "ipp_value": 0
  },
  "land_usr_chita": {
    "ipp_value": 0
  },
  "land_usr_buryatia": {
    "ipp_value": 0
  },
  "land_british_malaya": {
    "ipp_value": 1
  },
  "land_sarawak": {
    "ipp_value": 0
  },
  "land_aus_new_south_wales": {
    "ipp_value": 2
  },
  "land_nz_south_island": {
    "ipp_value": 0
  },
  "land_new_britain": {
    "ipp_value": 1
  },
  "land_timor": {
    "ipp_value": 1
  }
}
```

**Proposed:**

```json
{
  "land_usr_amur": 1,
  "land_usr_chita": 1,
  "land_usr_buryatia": 1,
  "land_british_malaya": 2,
  "land_sarawak": 1,
  "land_aus_new_south_wales": 1,
  "land_nz_south_island": 1,
  "land_new_britain": 0,
  "land_timor": 0
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6150, 0, 8600, 1600); evidence/ap_siberia_east.png
- evidence/ap_se_asia.png; evidence/ap_australia.png; evidence/ap_indonesia.png.

## AP-045 — Use the printed Volcano Islands label

**Field:** `name` · **Confidence:** high · **Severity:** minor

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_jap_volcanic_islands`

**Current:**

Volcanic Islands

**Proposed:**

Volcano Islands

**Evidence:**

- game_content/maps/gw36map.png rect (6250, 2600, 8250, 4030); evidence/ap_se_asia.png

## AP-050 — Southern India–Ceylon is a capacity-1 narrow crossing without rail

**Field:** `edge` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_india_southern_india`, `land_india_ceylon`

**Current:**

```json
{
  "neighbor_id": "land_india_ceylon",
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
{
  "narrow_crossing": true,
  "narrow_crossings": 1,
  "railway_connection": false,
  "narrow_crossing_sea_zones": [
    "sea_i11"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png

**Scope / dependency:** Dotted crossing is wholly north of the I11/I12 boundary in evidence/ap_ceylon_andamans.png; use I11 blocker. Boundary traverses Ceylon farther south.

## AP-051 — Correct Indian coastal sea IDs

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_india_ceylon`, `land_india_southern_india`, `land_india_maharashtra`

**Current:**

```json
{
  "land_india_ceylon": {
    "neighbors": [
      {
        "neighbor_id": "land_india_southern_india",
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
        "neighbor_id": "sea_i11",
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
          "facility_ceylon_minor_port"
        ],
        "port_or_dock_connection": true,
        "canal_or_strait": null,
        "narrow_crossing": false,
        "narrow_crossings": 0,
        "special_fortification": null
      },
      {
        "neighbor_id": "sea_i6",
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
          "facility_ceylon_minor_port"
        ],
        "port_or_dock_connection": true,
        "canal_or_strait": null,
        "narrow_crossing": false,
        "narrow_crossings": 0,
        "special_fortification": null
      }
    ]
  },
  "land_india_southern_india": {
    "neighbors": [
      {
        "neighbor_id": "land_india_calcutta",
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
      {
        "neighbor_id": "land_india_ceylon",
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
        "neighbor_id": "land_india_maharashtra",
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
        "neighbor_id": "sea_i11",
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
          "facility_southern_india_minor_port"
        ],
        "port_or_dock_connection": true,
        "canal_or_strait": null,
        "narrow_crossing": false,
        "narrow_crossings": 0,
        "special_fortification": null
      },
      {
        "neighbor_id": "sea_i6",
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
          "facility_southern_india_minor_port"
        ],
        "port_or_dock_connection": true,
        "canal_or_strait": null,
        "narrow_crossing": false,
        "narrow_crossings": 0,
        "special_fortification": null
      }
    ]
  },
  "land_india_maharashtra": {
    "neighbors": [
      {
        "neighbor_id": "land_india_benares",
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
      {
        "neighbor_id": "land_india_delhi",
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
        "neighbor_id": "land_india_southern_india",
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
        "neighbor_id": "sea_i6",
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
          "facility_maharashtra_minor_port"
        ],
        "port_or_dock_connection": true,
        "canal_or_strait": null,
        "narrow_crossing": false,
        "narrow_crossings": 0,
        "special_fortification": null
      }
    ]
  }
}
```

**Proposed:**

```json
{
  "land_india_ceylon": [
    "sea_i11",
    "sea_i12"
  ],
  "land_india_southern_india": [
    "sea_i7",
    "sea_i11",
    "sea_i12"
  ],
  "land_india_maharashtra": [
    "sea_i6",
    "sea_i7"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png

**Scope / dependency:** Ceylon crosses the I11/I12 boundary: small northern coast in I11, main island in I12. Its dockyard is on I11. Narrow crossing blockers are distinct from coast adjacency. Southern India has the west I7 coast, east I11 coast and southern I12 coast. Maharashtra straddles the I6/I7 boundary.

## AP-052 — Indian printed facilities need physical-instance records

**Field:** `facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_india_maharashtra`, `land_india_southern_india`, `land_india_calcutta`, `land_india_ceylon`

**Current:**

Generic minor ports; no intrinsic airfields

**Proposed:**

```json
{
  "Maharashtra": {
    "airfield": 1,
    "I6": [
      "minor_port",
      "major_port"
    ],
    "I7": [
      "major_dockyard"
    ]
  },
  "Southern India": {
    "I11": [
      "minor_port"
    ]
  },
  "Calcutta": {
    "I11": [
      "minor_shipyard",
      "major_port"
    ]
  },
  "Ceylon": {
    "airfield": 1,
    "I11": [
      "major_dockyard"
    ]
  },
  "physical_instances": {
    "land_india_maharashtra": [
      {
        "id": "facility_maharashtra_minor_port",
        "type": "minor_port",
        "sea_accesses": [
          "sea_i6"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              5480,
              2700,
              6020,
              3230
            ],
            "crop": "evidence/ap_naval_india_west.png"
          }
        ],
        "notes": "White-square plain anchor on the northwest Maharashtra coast."
      },
      {
        "id": "facility_maharashtra_major_port",
        "type": "major_port",
        "sea_accesses": [
          "sea_i6"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              5480,
              2700,
              6020,
              3230
            ],
            "crop": "evidence/ap_naval_india_west.png"
          }
        ],
        "notes": "Blue-square plain anchor lies north/west of the I6/I7 separator, inside Maharashtra. It is a separate physical port from the white-square minor port."
      },
      {
        "id": "facility_maharashtra_major_dockyard",
        "type": "major_dockyard",
        "sea_accesses": [
          "sea_i7"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              5480,
              2700,
              6020,
              3230
            ],
            "crop": "evidence/ap_naval_india_west.png"
          },
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              4850,
              2150,
              6650,
              3700
            ],
            "crop": "evidence/ap_india.png"
          }
        ],
        "notes": "Blue-square circular-anchor symbol is west of the Maharashtra/Southern India political border. Earlier AP-052 wrongly assigned it to Southern India."
      }
    ],
    "land_india_southern_india": [
      {
        "id": "facility_southern_india_minor_port",
        "type": "minor_port",
        "sea_accesses": [
          "sea_i11"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              4850,
              2150,
              6650,
              3700
            ],
            "crop": "evidence/ap_india.png"
          }
        ],
        "notes": "White-square anchor on the east coast; the west-coast major dockyard belongs to Maharashtra."
      }
    ],
    "land_india_calcutta": [
      {
        "id": "facility_calcutta_minor_shipyard",
        "type": "minor_shipyard",
        "sea_accesses": [
          "sea_i11"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              5940,
              2680,
              6360,
              3160
            ],
            "crop": "evidence/ap_naval_calcutta.png"
          }
        ],
        "notes": "White-square crane is inside the Calcutta city polygon; the rail line reaching it is not the city border."
      },
      {
        "id": "facility_calcutta_major_port",
        "type": "major_port",
        "sea_accesses": [
          "sea_i11"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              5940,
              2680,
              6360,
              3160
            ],
            "crop": "evidence/ap_naval_calcutta.png"
          }
        ],
        "notes": "Blue-square plain anchor is north of the city polygon southern coastal endpoint, so belongs to Calcutta, not Southern India."
      }
    ],
    "land_india_ceylon": [
      {
        "id": "facility_ceylon_major_dockyard",
        "type": "major_dockyard",
        "sea_accesses": [
          "sea_i11"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              6020,
              3270,
              6330,
              3510
            ],
            "crop": "evidence/ap_naval_ceylon.png"
          }
        ],
        "notes": "Blue-square circular anchor is north of the I11/I12 sea seam; single physical dockyard, with no I12 access."
      }
    ]
  }
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (5480, 2700, 6020, 3230); evidence/ap_naval_india_west.png
- game_content/maps/gw36map.png rect (4850, 2150, 6650, 3700); evidence/ap_india.png
- game_content/maps/gw36map.png rect (5940, 2680, 6360, 3160); evidence/ap_naval_calcutta.png
- game_content/maps/gw36map.png rect (6020, 3270, 6330, 3510); evidence/ap_naval_ceylon.png

**Scope / dependency:** Fresh 2026-10-06 political-border and sea-seam trace corrects the previous proposal: the west-coast major dockyard is in Maharashtra, not Southern India; the separate Maharashtra major port is in I6, not I7. Calcutta has two distinct facilities inside its city polygon. Ceylon dockyard only accesses I11. Under §13.2.8 rail access derives from whole-zone coverage, not an independently required port spur.

## AP-060 — Primorsky Krai major port and separate northern minor shipyard

**Field:** `facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_primorsky_krai`, `sea_p2`, `sea_p7`

**Current:**

```json
{
  "P7": [
    "minor_port"
  ],
  "node": []
}
```

**Proposed:**

```json
{
  "coastal_seas": [
    "sea_p2",
    "sea_p7"
  ],
  "naval_facilities": [
    {
      "id": "facility_primorsky_north_minor_shipyard",
      "type": "minor_shipyard",
      "sea_accesses": [
        "sea_p2",
        "sea_p7"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "rectangle": [
            7150,
            1000,
            7640,
            1740
          ],
          "crop": "evidence/ap_naval_amur_primorsky_boundary.png"
        },
        {
          "source": "game_content/maps/gw36map.png",
          "rectangle": [
            7360,
            1430,
            7570,
            1700
          ],
          "crop": "evidence/ap_naval_amur_yard.png"
        }
      ],
      "notes": "White-square crane is east of the Amur river political boundary, on Primorsky Krai. P2/P7 separator meets its coastal location; one physical yard with both accesses, not an Amur facility."
    },
    {
      "id": "facility_primorsky_krai_major_port",
      "type": "major_port",
      "sea_accesses": [
        "sea_p7"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "rectangle": [
            7270,
            1320,
            8170,
            2100
          ],
          "crop": "evidence/ap_sakhalin.png"
        },
        {
          "source": "game_content/maps/gw36map.png",
          "rectangle": [
            7180,
            1870,
            8110,
            2630
          ],
          "crop": "evidence/ap_naval_japan.png"
        }
      ],
      "notes": "Vladivostok plain anchor in blue square."
    }
  ],
  "node": [
    "airfield"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7150, 1000, 7640, 1740); evidence/ap_naval_amur_primorsky_boundary.png
- game_content/maps/gw36map.png rect (7360, 1430, 7570, 1700); evidence/ap_naval_amur_yard.png
- game_content/maps/gw36map.png rect (7270, 1320, 8170, 2100); evidence/ap_sakhalin.png

**Scope / dependency:** Fresh political-boundary tracing places the northern white-square crane on Primorsky Krai, east of the Amur river border. The P2/P7 sea divider meets this one physical shipyard; share one ID across both access edges. Vladivostok is a separate P7 major port. The old Amur attribution is withdrawn.

## AP-063 — Actual narrow island pairs require capacity, sea blockers and no rail

**Field:** `edges` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_sumatra`, `land_java`, `land_luzon_and_the_visayas`, `land_mindanao`, `land_nz_north_island`, `land_nz_south_island`

**Current:**

Plain reciprocal land links with railway_connection:true

**Proposed:**

```json
{
  "pairs": [
    {
      "nodes": [
        "land_sumatra",
        "land_java"
      ],
      "capacity": 1,
      "blocking_seas": [
        "sea_i13",
        "sea_p59"
      ]
    },
    {
      "nodes": [
        "land_luzon_and_the_visayas",
        "land_mindanao"
      ],
      "capacity": 1,
      "blocking_seas": [
        "sea_p42"
      ]
    },
    {
      "nodes": [
        "land_nz_north_island",
        "land_nz_south_island"
      ],
      "capacity": 2,
      "blocking_seas": [
        "sea_p73"
      ]
    }
  ],
  "railway_connection": false
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- evidence/ap_se_asia.png; evidence/ap_australia.png
- game_content/maps/gw36map.png rect (6620, 3640, 7030, 3830); evidence/ap_narrow_sunda.png
- game_content/maps/gw36map.png rect (6810, 2730, 7500, 3390); evidence/ap_philippines_edges.png

**Scope / dependency:** Native dotted-line trace resolves blockers: Sunda crosses I13/P59, the Philippine crossing is P42, and Cook Strait is P73. These do not gain railway connections.

## AP-065 — Timor node conflates Portuguese Timor and Dutch West Timor

**Field:** `identity/ipp/coasts` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_timor`, `land_lesser_sunda_islands`

**Current:**

```json
{
  "land_timor": {
    "name": "Timor",
    "terrain": "normal",
    "ipp_value": 1,
    "original_owner": "Portugal"
  }
}
```

**Proposed:**

```json
{
  "land_timor": {
    "name": "Portuguese Timor",
    "terrain": [
      "mountain",
      "jungle"
    ],
    "ipp_value": 0,
    "owner": "Portugal",
    "coasts": [
      "sea_p63"
    ]
  },
  "new_dutch_tile": {
    "name": "West Timor / Lesser Sunda Islands",
    "ipp_value": 1,
    "owner": "Netherlands"
  }
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- Terrain Glossary p4 names Lesser Sunda Islands and Portuguese Timor separately.

**Scope / dependency:** The map labels the Dutch archipelago WEST TIMOR while glossary uses Lesser Sunda Islands. Preserve both names via alias until rules terminology is chosen. Portuguese/Dutch land boundary on Timor also must be added.

## AP-066 — Philippine coasts and facilities need reassignment

**Field:** `sea_neighbors/facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_luzon_and_the_visayas`, `land_mindanao`

**Current:**

Luzon P42 minor port; Mindanao P42/P50/P52 minor/major ports

**Proposed:**

```json
{
  "Luzon": [
    "sea_p41",
    "sea_p42",
    "sea_p50"
  ],
  "Mindanao": [
    "sea_p42",
    "sea_p50",
    "sea_p51"
  ],
  "Luzon_P50": [
    "submarine_base"
  ],
  "P50_major_port_owner": "unresolved between Luzon/Visayas and Mindanao; AP-095"
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6250, 2600, 8250, 4030); evidence/ap_se_asia.png
- game_content/maps/gw36map.png rect (6810, 2730, 7500, 3390); evidence/ap_philippines_edges.png

**Scope / dependency:** Mindanao has a finite P42 northeast coast and P51 south coast; P52 is separated by P51. The Luzon submarine base accesses P50. The separate major-port symbol in the western Philippine island group cannot be assigned to a land node confidently from this raster; AP-095 preserves that uncertainty. Fresh naval ledger separately deletes the fabricated Luzon and Mindanao minor-port instances (AP-103), retains the actual Luzon submarine base, and leaves the real P50 major port unassigned (AP-095).

## AP-067 — Correct Borneo and eastern Indies coast IDs

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_borneo`, `land_sarawak`, `land_java`, `land_celebes`, `land_dutch_new_guinea`, `land_new_guinea`, `land_new_britain`

**Current:**

```json
{
  "source": "current JSON coast lists"
}
```

**Proposed:**

```json
{
  "Borneo": [
    "sea_p50",
    "sea_p59",
    "sea_p60"
  ],
  "Sarawak": [
    "sea_p50",
    "sea_p51"
  ],
  "Java": [
    "sea_i13",
    "sea_p59",
    "sea_p60",
    "sea_p61"
  ],
  "Celebes": [
    "sea_p51",
    "sea_p60",
    "sea_p62"
  ],
  "Dutch New Guinea": [
    "sea_p52",
    "sea_p62"
  ],
  "New Guinea": [
    "sea_p53",
    "sea_p64"
  ],
  "New Britain": [
    "sea_p53"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- evidence/ap_se_asia.png
- game_content/maps/gw36map.png rect (6680, 3230, 7080, 3510); evidence/ap_sarawak_junction.png
- game_content/maps/gw36map.png rect (6060, 3480, 7530, 4410); evidence/ap_java_indian_grid.png

**Scope / dependency:** Native coast trace confirms all listed sets. Borneo has a short gray northwest coast in P50 before the Sarawak land boundary; Sarawak P51 is a short northeast coast. Java has southwestern I13 and a small eastern P60 coast. Papua sea splits meet the political border on both coasts; do not add corner-only seas.

## AP-068 — Indonesian/Papuan facilities are not generic minor ports

**Field:** `facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_sumatra`, `land_java`, `land_borneo`, `land_new_britain`

**Current:**

Generic minor ports on almost every island

**Proposed:**

```json
{
  "Sumatra": {
    "P50": [
      "minor_port"
    ],
    "node": [
      "airfield"
    ]
  },
  "Java": {
    "P59": [
      "minor_dockyard"
    ]
  },
  "Borneo": {
    "P60": [
      "minor_port",
      "seaplane_base"
    ]
  },
  "New Britain": {
    "P53": [
      "major_port"
    ]
  },
  "physical_instances": {
    "land_sumatra": [
      {
        "id": "facility_land_sumatra_minor_port",
        "type": "minor_port",
        "sea_accesses": [
          "sea_p50"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              6450,
              3330,
              6840,
              3720
            ],
            "crop": "evidence/ap_naval_malaya_sumatra.png"
          }
        ],
        "notes": "One white-square anchor north of the P50/P59 separator, not a port shared across P50/P59."
      }
    ],
    "land_java": [
      {
        "id": "facility_java_minor_dockyard",
        "type": "minor_dockyard",
        "sea_accesses": [
          "sea_p59"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              6650,
              3210,
              7380,
              3950
            ],
            "crop": "evidence/ap_borneo_java.png"
          }
        ],
        "notes": "White-square circular anchor, not plain-anchor minor port."
      }
    ],
    "land_borneo": [
      {
        "id": "facility_land_borneo_minor_port",
        "type": "minor_port",
        "sea_accesses": [
          "sea_p60"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              6700,
              3230,
              7110,
              3640
            ],
            "crop": "evidence/ap_naval_borneo.png"
          }
        ],
        "notes": "White-square anchor is east of the P59/P60 seam endpoint; only P60 access."
      },
      {
        "id": "facility_borneo_seaplane_base",
        "type": "seaplane_base",
        "sea_accesses": [
          "sea_p60"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              6700,
              3230,
              7110,
              3640
            ],
            "crop": "evidence/ap_naval_borneo.png"
          }
        ],
        "notes": "Green seaplane symbol lies on gray Dutch Borneo, south of the Sarawak boundary and the P51/P60 sea separator."
      }
    ],
    "land_new_britain": [
      {
        "id": "facility_new_britain_major_port",
        "type": "major_port",
        "sea_accesses": [
          "sea_p53"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              6250,
              2600,
              8250,
              4030
            ],
            "crop": "evidence/ap_se_asia.png"
          }
        ],
        "notes": "Blue-square plain anchor inside the New Britain island outline, not P63."
      }
    ]
  }
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6450, 3330, 6840, 3720); evidence/ap_naval_malaya_sumatra.png
- game_content/maps/gw36map.png rect (6470, 3160, 7850, 4030); evidence/ap_indonesia.png
- game_content/maps/gw36map.png rect (6650, 3210, 7380, 3950); evidence/ap_borneo_java.png
- game_content/maps/gw36map.png rect (6060, 3480, 7530, 4410); evidence/ap_java_indian_grid.png
- game_content/maps/gw36map.png rect (6700, 3230, 7110, 3640); evidence/ap_naval_borneo.png
- game_content/maps/gw36map.png rect (6250, 2600, 8250, 4030); evidence/ap_se_asia.png

**Scope / dependency:** Fresh native symbol/boundary review confirms the Borneo seaplane base on gray Dutch Borneo with P60 access, and its separate minor port also in P60. Sumatra has one minor port solely in P50, not shared with P59. Java is a circular-anchor minor dockyard. Facility-only removals for Celebes, Portuguese Timor and both New Guinea tiles are in AP-100.

## AP-069 — Australian coastal sea IDs and facilities

**Field:** `sea_neighbors/facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_aus_western_australia`, `land_aus_northern_territory`, `land_aus_south_australia`, `land_aus_queensland`, `land_aus_new_south_wales`, `land_aus_tasmania`

**Current:**

Current coast uses I6/P61/P62/P68; South Australia lacks sea access

**Proposed:**

```json
{
  "Western Australia": [
    "sea_p61",
    "sea_p63",
    "sea_p69",
    "sea_p70"
  ],
  "Northern Territory": [
    "sea_p63"
  ],
  "South Australia": [
    "sea_p70"
  ],
  "Queensland": [
    "sea_p63",
    "sea_p64",
    "sea_p71",
    "sea_p72"
  ],
  "New South Wales": [
    "sea_p70",
    "sea_p72"
  ],
  "Tasmania": [
    "sea_p72"
  ],
  "facilities": {
    "Northern Territory_P63": [
      "seaplane_base"
    ],
    "Queensland_P63": [
      "minor_port"
    ],
    "New South Wales_P72": [
      "minor_shipyard"
    ],
    "South Australia_P70": [
      "major_port"
    ]
  },
  "physical_instances": {
    "land_aus_northern_territory": [
      {
        "id": "facility_northern_territory_seaplane_base",
        "type": "seaplane_base",
        "sea_accesses": [
          "sea_p63"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              7180,
              3890,
              7850,
              4230
            ],
            "crop": "evidence/ap_naval_australia_north.png"
          }
        ],
        "notes": "Green seaplane silhouette; no anchor/minor port at this location."
      }
    ],
    "land_aus_queensland": [
      {
        "id": "facility_queensland_minor_port",
        "type": "minor_port",
        "sea_accesses": [
          "sea_p63"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              7180,
              3890,
              7850,
              4230
            ],
            "crop": "evidence/ap_naval_australia_north.png"
          }
        ],
        "notes": "Printed symbol class and its side of the political/coastal boundary independently checked in the native source."
      }
    ],
    "land_aus_south_australia": [
      {
        "id": "facility_south_australia_major_port",
        "type": "major_port",
        "sea_accesses": [
          "sea_p70"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              7660,
              4250,
              8110,
              4700
            ],
            "crop": "evidence/ap_naval_sydney_nsw.png"
          }
        ],
        "notes": "Blue-square anchor lies west of the straight SA/NSW political border. The prior NSW assignment was wrong."
      }
    ],
    "land_aus_new_south_wales": [
      {
        "id": "facility_new_south_wales_minor_shipyard",
        "type": "minor_shipyard",
        "sea_accesses": [
          "sea_p72"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              7660,
              4250,
              8110,
              4700
            ],
            "crop": "evidence/ap_naval_sydney_nsw.png"
          }
        ],
        "notes": "Northern white-square crane lies north of the circular Sydney boundary, within NSW."
      }
    ]
  }
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6100, 3750, 8650, 4888); evidence/ap_australia.png
- game_content/maps/gw36map.png rect (7180, 3890, 7850, 4230); evidence/ap_naval_australia_north.png
- game_content/maps/gw36map.png rect (7660, 4250, 8110, 4700); evidence/ap_naval_sydney_nsw.png

**Scope / dependency:** Fresh naval trace corrects the P70 major port to South Australia: the blue anchor is west of the straight SA/NSW border. NSW has the northern P72 minor shipyard; Sydney has the separate southern one. NT has a seaplane base, not a minor port. Western Australia has no printed naval facility (AP-101). Other coast/reef findings are retained.

## AP-070 — Outback blocks the whole Northern Territory–South Australia border

**Field:** `passable/railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_aus_northern_territory`, `land_aus_south_australia`

**Current:**

```json
{
  "neighbor_id": "land_aus_south_australia",
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
{
  "passable": false,
  "railway_connection": false
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6100, 3750, 8650, 4888); evidence/ap_australia.png

**Scope / dependency:** Entire shared east–west boundary is inside the explicitly impassable Outback Desert. Do not set the entire three Australian territories impassable; other traversable borders remain.

## AP-073 — New Zealand and New Caledonia are in P73

**Field:** `sea_neighbors/naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_nz_north_island`, `land_nz_south_island`, `land_new_caledonia`

**Current:**

```json
{
  "NZ": "P69",
  "New Caledonia": "P65"
}
```

**Proposed:**

```json
{
  "land_nz_north_island": [
    "sea_p73"
  ],
  "land_nz_south_island": [
    "sea_p73"
  ],
  "land_new_caledonia": [
    "sea_p73"
  ],
  "naval_facilities": {
    "land_nz_north_island": [
      {
        "id": "facility_north_island_major_port",
        "type": "major_port",
        "sea_accesses": [
          "sea_p73"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              6100,
              3750,
              8650,
              4888
            ],
            "crop": "evidence/ap_australia.png"
          },
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              8000,
              2750,
              9900,
              4888
            ],
            "crop": "evidence/ap_pacific_south.png"
          }
        ],
        "notes": "Blue-square plain anchor, not minor-port white square."
      }
    ],
    "land_nz_south_island": [],
    "land_new_caledonia": [
      {
        "id": "facility_caledonia_minor_port",
        "type": "minor_port",
        "sea_accesses": [
          "sea_p73"
        ],
        "evidence": [
          {
            "source": "game_content/maps/gw36map.png",
            "rectangle": [
              8000,
              2750,
              9900,
              4888
            ],
            "crop": "evidence/ap_pacific_south.png"
          }
        ],
        "notes": "Printed symbol class and its side of the political/coastal boundary independently checked in the native source."
      }
    ]
  }
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (8000, 2750, 9900, 4888); evidence/ap_pacific_south.png

**Scope / dependency:** Fresh native symbols confirm North Island major port (blue-square anchor) and New Caledonia minor port (white-square anchor), both P73. South Island has no facility (AP-074). One physical facility each, not generic minor ports.

## AP-076 — Replace I6–I14 Indian Ocean sea-neighbor sets from native perimeter trace

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_i6`, `sea_i7`, `sea_i8`, `sea_i9`, `sea_i10`, `sea_i11`, `sea_i12`, `sea_i13`, `sea_i14`

**Current:**

```json
{
  "sea_i6": [
    "sea_i11",
    "sea_i3",
    "sea_i4",
    "sea_i7"
  ],
  "sea_i7": [
    "sea_i6"
  ],
  "sea_i8": [],
  "sea_i9": [],
  "sea_i10": [],
  "sea_i11": [
    "sea_i12",
    "sea_i6"
  ],
  "sea_i12": [
    "sea_i11",
    "sea_p50"
  ],
  "sea_i13": [],
  "sea_i14": []
}
```

**Proposed:**

```json
{
  "sea_i6": [
    "sea_i7"
  ],
  "sea_i7": [
    "sea_i4",
    "sea_i6",
    "sea_i8",
    "sea_i10",
    "sea_i12"
  ],
  "sea_i8": [
    "sea_i2",
    "sea_i3",
    "sea_i4",
    "sea_i7",
    "sea_i9",
    "sea_i10"
  ],
  "sea_i9": [
    "sea_i2",
    "sea_i8",
    "sea_i10",
    "sea_i14"
  ],
  "sea_i10": [
    "sea_i7",
    "sea_i8",
    "sea_i9",
    "sea_i12",
    "sea_i13",
    "sea_i14"
  ],
  "sea_i11": [
    "sea_i12"
  ],
  "sea_i12": [
    "sea_i7",
    "sea_i10",
    "sea_i11",
    "sea_i13",
    "sea_p50"
  ],
  "sea_i13": [
    "sea_i10",
    "sea_i12",
    "sea_i14",
    "sea_p59",
    "sea_p61"
  ],
  "sea_i14": [
    "sea_i9",
    "sea_i10",
    "sea_i13",
    "sea_p61",
    "sea_p69"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4200, 2950, 6350, 4888); evidence/ap_indian_ocean.png
- evidence/ap_india.png; evidence/ap_australia.png
- data/asia_pacific_sea_neighbors.json: each row identifies native source rectangles.

**Scope / dependency:** Complete sea-to-sea perimeter sets are in data/asia_pacific_sea_neighbors.json. Native second pass resolves offsets and coasts, with reciprocal within-domain validation. I7 does not touch I11; I9 does not touch I13; I10 touches I14. Indian/Pacific seams are included.

## AP-078 — Persian Gulf coastal endpoints belong to I6, not I7

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_i6`, `sea_i7`, `land_kuwait`, `land_qatar`, `land_southern_iraq`, `land_iran_southern_iran`, `land_oman`

**Current:**

Kuwait/Qatar/Southern Iraq on I7

**Proposed:**

```json
{
  "I6": [
    "land_kuwait",
    "land_qatar",
    "land_southern_iraq",
    "land_iran_southern_iran",
    "land_oman",
    "land_saudi_arabia",
    "land_india_maharashtra"
  ],
  "I7_remove": [
    "land_kuwait",
    "land_qatar",
    "land_southern_iraq",
    "land_iran_southern_iran"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (4200, 2950, 6350, 4888); evidence/ap_indian_ocean.png
- evidence/ap_india.png

**Scope / dependency:** Oman has I4, I6 and I7 coasts (I4 short southwestern coast independently resolved by Europe/Africa agent); Gulf terminals are all northwest of I6/I7 boundary. I6→Maharashtra already present; I7→Southern India missing. Gulf coast facility identities handled by Europe/Middle East audit.

## AP-080 — Replace P1–P75 Pacific sea-neighbor sets from native perimeter trace

**Field:** `sea_neighbors` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_p1`, `sea_p2`, `sea_p3`, `sea_p4`, `sea_p5`, `sea_p6`, `sea_p7`, `sea_p8`, `sea_p9`, `sea_p10`, `sea_p11`, `sea_p12`, `sea_p13`, `sea_p14`, `sea_p15`, `sea_p16`, `sea_p17`, `sea_p18`, `sea_p19`, `sea_p20`, `sea_p21`, `sea_p22`, `sea_p23`, `sea_p24`, `sea_p25`, `sea_p26`, `sea_p27`, `sea_p28`, `sea_p29`, `sea_p30`, `sea_p31`, `sea_p32`, `sea_p33`, `sea_p34`, `sea_p35`, `sea_p36`, `sea_p37`, `sea_p38`, `sea_p39`, `sea_p40`, `sea_p41`, `sea_p42`, `sea_p43`, `sea_p44`, `sea_p45`, `sea_p46`, `sea_p47`, `sea_p48`, `sea_p49`, `sea_p50`, `sea_p51`, `sea_p52`, `sea_p53`, `sea_p54`, `sea_p55`, `sea_p56`, `sea_p57`, `sea_p58`, `sea_p59`, `sea_p60`, `sea_p61`, `sea_p62`, `sea_p63`, `sea_p64`, `sea_p65`, `sea_p66`, `sea_p67`, `sea_p68`, `sea_p69`, `sea_p70`, `sea_p71`, `sea_p72`, `sea_p73`, `sea_p74`, `sea_p75`

**Current:**

Many missing nodes; surviving nodes have partial or geographically wrong neighbor sets

**Proposed:**

```json
{
  "sea_p1": [
    "sea_p3",
    "sea_p4",
    "sea_p5"
  ],
  "sea_p2": [
    "sea_p7",
    "sea_p8",
    "sea_p9"
  ],
  "sea_p3": [
    "sea_p1",
    "sea_p4",
    "sea_p9",
    "sea_p10"
  ],
  "sea_p4": [
    "sea_p1",
    "sea_p3",
    "sea_p5",
    "sea_p10",
    "sea_p11"
  ],
  "sea_p5": [
    "sea_p1",
    "sea_p4",
    "sea_p6",
    "sea_p11",
    "sea_p12"
  ],
  "sea_p6": [
    "sea_p5",
    "sea_p12",
    "sea_p13"
  ],
  "sea_p7": [
    "sea_p2",
    "sea_p8",
    "sea_p15",
    "sea_p16"
  ],
  "sea_p8": [
    "sea_p2",
    "sea_p7",
    "sea_p9",
    "sea_p16"
  ],
  "sea_p9": [
    "sea_p2",
    "sea_p3",
    "sea_p8",
    "sea_p10",
    "sea_p16",
    "sea_p17"
  ],
  "sea_p10": [
    "sea_p3",
    "sea_p4",
    "sea_p9",
    "sea_p11",
    "sea_p17",
    "sea_p19"
  ],
  "sea_p11": [
    "sea_p4",
    "sea_p5",
    "sea_p10",
    "sea_p12",
    "sea_p19",
    "sea_p21",
    "sea_p23"
  ],
  "sea_p12": [
    "sea_p5",
    "sea_p6",
    "sea_p11",
    "sea_p13",
    "sea_p23",
    "sea_p24"
  ],
  "sea_p13": [
    "sea_p6",
    "sea_p12",
    "sea_p24",
    "sea_p25"
  ],
  "sea_p14": [
    "sea_p15",
    "sea_p32"
  ],
  "sea_p15": [
    "sea_p7",
    "sea_p14",
    "sea_p16",
    "sea_p32",
    "sea_p33",
    "sea_p34"
  ],
  "sea_p16": [
    "sea_p7",
    "sea_p8",
    "sea_p9",
    "sea_p15",
    "sea_p17",
    "sea_p18",
    "sea_p26",
    "sea_p34",
    "sea_p35"
  ],
  "sea_p17": [
    "sea_p9",
    "sea_p10",
    "sea_p16",
    "sea_p18",
    "sea_p19",
    "sea_p20"
  ],
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
  "sea_p22": [
    "sea_p19",
    "sea_p20",
    "sea_p21",
    "sea_p23",
    "sea_p27",
    "sea_p28",
    "sea_p29"
  ],
  "sea_p23": [
    "sea_p11",
    "sea_p12",
    "sea_p21",
    "sea_p22",
    "sea_p24",
    "sea_p29"
  ],
  "sea_p24": [
    "sea_p12",
    "sea_p13",
    "sea_p23",
    "sea_p25",
    "sea_p29",
    "sea_p30"
  ],
  "sea_p25": [
    "sea_p13",
    "sea_p24",
    "sea_p30",
    "sea_p31"
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
  ],
  "sea_p28": [
    "sea_p22",
    "sea_p27",
    "sea_p29",
    "sea_p37"
  ],
  "sea_p29": [
    "sea_p22",
    "sea_p23",
    "sea_p24",
    "sea_p28",
    "sea_p30",
    "sea_p37",
    "sea_p38",
    "sea_p39"
  ],
  "sea_p30": [
    "sea_p24",
    "sea_p25",
    "sea_p29",
    "sea_p31",
    "sea_p39"
  ],
  "sea_p31": [
    "sea_p25",
    "sea_p30",
    "sea_p39",
    "sea_p40",
    "sea_p76"
  ],
  "sea_p32": [
    "sea_p14",
    "sea_p15",
    "sea_p33",
    "sea_p41",
    "sea_p42",
    "sea_p43"
  ],
  "sea_p33": [
    "sea_p15",
    "sea_p32",
    "sea_p34",
    "sea_p43"
  ],
  "sea_p34": [
    "sea_p15",
    "sea_p16",
    "sea_p33",
    "sea_p35",
    "sea_p43",
    "sea_p45"
  ],
  "sea_p35": [
    "sea_p16",
    "sea_p26",
    "sea_p34",
    "sea_p36",
    "sea_p45"
  ],
  "sea_p36": [
    "sea_p26",
    "sea_p27",
    "sea_p35",
    "sea_p37",
    "sea_p45",
    "sea_p47"
  ],
  "sea_p37": [
    "sea_p27",
    "sea_p28",
    "sea_p29",
    "sea_p36",
    "sea_p38",
    "sea_p47"
  ],
  "sea_p38": [
    "sea_p29",
    "sea_p37",
    "sea_p39",
    "sea_p47",
    "sea_p48",
    "sea_p56"
  ],
  "sea_p39": [
    "sea_p29",
    "sea_p30",
    "sea_p31",
    "sea_p38",
    "sea_p40",
    "sea_p48",
    "sea_p49"
  ],
  "sea_p40": [
    "sea_p31",
    "sea_p39",
    "sea_p49",
    "sea_p76"
  ],
  "sea_p41": [
    "sea_p32",
    "sea_p42",
    "sea_p50"
  ],
  "sea_p42": [
    "sea_p32",
    "sea_p41",
    "sea_p43",
    "sea_p44",
    "sea_p51"
  ],
  "sea_p43": [
    "sea_p32",
    "sea_p33",
    "sea_p34",
    "sea_p42",
    "sea_p44",
    "sea_p45",
    "sea_p46"
  ],
  "sea_p44": [
    "sea_p42",
    "sea_p43",
    "sea_p46",
    "sea_p51",
    "sea_p52",
    "sea_p53"
  ],
  "sea_p45": [
    "sea_p34",
    "sea_p35",
    "sea_p36",
    "sea_p43",
    "sea_p46",
    "sea_p47"
  ],
  "sea_p46": [
    "sea_p43",
    "sea_p44",
    "sea_p45",
    "sea_p47",
    "sea_p53",
    "sea_p54"
  ],
  "sea_p47": [
    "sea_p36",
    "sea_p37",
    "sea_p38",
    "sea_p45",
    "sea_p46",
    "sea_p54",
    "sea_p55",
    "sea_p56"
  ],
  "sea_p48": [
    "sea_p38",
    "sea_p39",
    "sea_p49",
    "sea_p56",
    "sea_p57"
  ],
  "sea_p49": [
    "sea_p39",
    "sea_p40",
    "sea_p48",
    "sea_p57",
    "sea_p58",
    "sea_p76"
  ],
  "sea_p50": [
    "sea_i12",
    "sea_p41",
    "sea_p51",
    "sea_p59"
  ],
  "sea_p51": [
    "sea_p42",
    "sea_p44",
    "sea_p50",
    "sea_p52",
    "sea_p60",
    "sea_p62"
  ],
  "sea_p52": [
    "sea_p44",
    "sea_p51",
    "sea_p53",
    "sea_p62"
  ],
  "sea_p53": [
    "sea_p44",
    "sea_p46",
    "sea_p52",
    "sea_p54",
    "sea_p64"
  ],
  "sea_p54": [
    "sea_p46",
    "sea_p47",
    "sea_p53",
    "sea_p55",
    "sea_p64",
    "sea_p65"
  ],
  "sea_p55": [
    "sea_p47",
    "sea_p54",
    "sea_p56",
    "sea_p65",
    "sea_p66"
  ],
  "sea_p56": [
    "sea_p38",
    "sea_p47",
    "sea_p48",
    "sea_p55",
    "sea_p57",
    "sea_p66",
    "sea_p67"
  ],
  "sea_p57": [
    "sea_p48",
    "sea_p49",
    "sea_p56",
    "sea_p58",
    "sea_p67",
    "sea_p68"
  ],
  "sea_p58": [
    "sea_p49",
    "sea_p57",
    "sea_p68",
    "sea_p77"
  ],
  "sea_p59": [
    "sea_i13",
    "sea_p50",
    "sea_p60",
    "sea_p61"
  ],
  "sea_p60": [
    "sea_p51",
    "sea_p59",
    "sea_p61",
    "sea_p62",
    "sea_p63"
  ],
  "sea_p61": [
    "sea_i13",
    "sea_i14",
    "sea_p59",
    "sea_p60",
    "sea_p63",
    "sea_p69"
  ],
  "sea_p62": [
    "sea_p51",
    "sea_p52",
    "sea_p60",
    "sea_p63",
    "sea_p64"
  ],
  "sea_p63": [
    "sea_p60",
    "sea_p61",
    "sea_p62",
    "sea_p64"
  ],
  "sea_p64": [
    "sea_p53",
    "sea_p54",
    "sea_p62",
    "sea_p63",
    "sea_p65",
    "sea_p71"
  ],
  "sea_p65": [
    "sea_p54",
    "sea_p55",
    "sea_p64",
    "sea_p66",
    "sea_p71",
    "sea_p73"
  ],
  "sea_p66": [
    "sea_p55",
    "sea_p56",
    "sea_p65",
    "sea_p67",
    "sea_p73",
    "sea_p74"
  ],
  "sea_p67": [
    "sea_p56",
    "sea_p57",
    "sea_p66",
    "sea_p68",
    "sea_p74",
    "sea_p75"
  ],
  "sea_p68": [
    "sea_p57",
    "sea_p58",
    "sea_p67",
    "sea_p75",
    "sea_p77",
    "sea_p78"
  ],
  "sea_p69": [
    "sea_i14",
    "sea_p61",
    "sea_p70"
  ],
  "sea_p70": [
    "sea_p69",
    "sea_p72"
  ],
  "sea_p71": [
    "sea_p64",
    "sea_p65",
    "sea_p72",
    "sea_p73"
  ],
  "sea_p72": [
    "sea_p70",
    "sea_p71",
    "sea_p73"
  ],
  "sea_p73": [
    "sea_p65",
    "sea_p66",
    "sea_p71",
    "sea_p72",
    "sea_p74"
  ],
  "sea_p74": [
    "sea_p66",
    "sea_p67",
    "sea_p73",
    "sea_p75"
  ],
  "sea_p75": [
    "sea_p67",
    "sea_p68",
    "sea_p74",
    "sea_p78"
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (7900, 1000, 9900, 2850); evidence/ap_pacific_north.png
- evidence/ap_pacific_south.png; evidence/ap_australia.png
- data/asia_pacific_sea_neighbors.json: each row identifies native source rectangles.

**Scope / dependency:** Complete sea-to-sea perimeter sets are in data/asia_pacific_sea_neighbors.json. Native second pass resolves offsets and coasts, with reciprocal within-domain validation. P42–P50 is the sole unresolved open-water island-group junction (AP-098); it is omitted from confirmed sets. P34–P45 and P60–P61 have finite short boundaries and must be retained. P35 does not touch P43. Americas P76–P78 wraps are included from the shared source trace. A9–P1 is a restricted route, modeled separately (MS-03).

## AP-082 — Replace misleading sea-zone descriptions with printed IDs

**Field:** `name` · **Confidence:** high · **Severity:** minor

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `sea_i1`, `sea_i10`, `sea_i11`, `sea_i12`, `sea_i13`, `sea_i14`, `sea_i2`, `sea_i3`, `sea_i4`, `sea_i5`, `sea_i6`, `sea_i7`, `sea_i8`, `sea_i9`, `sea_p1`, `sea_p10`, `sea_p11`, `sea_p12`, `sea_p13`, `sea_p14`, `sea_p15`, `sea_p16`, `sea_p17`, `sea_p18`, `sea_p2`, `sea_p24`, `sea_p25`, `sea_p26`, `sea_p28`, `sea_p3`, `sea_p30`, `sea_p31`, `sea_p32`, `sea_p33`, `sea_p34`, `sea_p35`, `sea_p36`, `sea_p41`, `sea_p42`, `sea_p43`, `sea_p44`, `sea_p45`, `sea_p46`, `sea_p47`, `sea_p5`, `sea_p50`, `sea_p51`, `sea_p52`, `sea_p53`, `sea_p54`, `sea_p59`, `sea_p6`, `sea_p60`, `sea_p61`, `sea_p62`, `sea_p63`, `sea_p64`, `sea_p65`, `sea_p68`, `sea_p69`, `sea_p7`, `sea_p8`, `sea_p9`

**Current:**

Descriptions such as P61 Arafura, P62 Coral, P63 Bismarck, P69 NZ Approaches, I3 Red Sea

**Proposed:**

Use Sea Zone <ID> as canonical label; optional geographic aliases only after polygon check

**Evidence:**

- game_content/maps/gw36map.png rect (6100, 3750, 8650, 4888); evidence/ap_australia.png
- evidence/ap_se_asia.png; evidence/ap_indian_ocean.png

**Scope / dependency:** Current descriptions encode wrong geography, encouraging further incorrect connections. P61 lies west of Australia, P62 Banda Sea, P63 Timor Sea, P69 southwest Australia; NZ is P73.

## AP-089 — Apply source-enumerated directional river and mountain/desert approaches

**Field:** `river_crossing / border_terrain` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_annam_tonkin`, `land_aus_new_south_wales`, `land_aus_northern_territory`, `land_aus_queensland`, `land_aus_south_australia`, `land_aus_western_australia`, `land_borneo`, `land_burma`, `land_china_hopeh`, `land_cochinchina`, `land_india_benares`, `land_india_calcutta`, `land_india_maharashtra`, `land_india_southern_india`, `land_manchuria_eastern`, `land_manchuria_northern`, `land_siam`, `land_usr_amur`, `land_usr_angara`, `land_usr_central_kazakhstan`, `land_usr_chita`, `land_usr_chukotka`, `land_usr_donets_kuban`, `land_usr_eastern_kazakhstan`, `land_usr_eastern_ukraine`, `land_usr_eastern_yakutia`, `land_usr_evenkiland`, `land_usr_gorky`, `land_usr_karelia`, `land_usr_kiev`, `land_usr_leningrad`, `land_usr_lower_tunguska`, `land_usr_moscow`, `land_usr_northern_russia`, `land_usr_northern_yakutia`, `land_usr_orenburg`, `land_usr_primorsky_krai`, `land_usr_samoyedia`, `land_usr_saratov`, `land_usr_sibir`, `land_usr_southern_belorussia`, `land_usr_stalingrad`, `land_usr_stalino`, `land_usr_taurida`, `land_usr_tobolsk`, `land_usr_tula_lipetsk`, `land_usr_turkestan`, `land_usr_turkmenistan`, `land_usr_ural`, `land_usr_vanavara`, `land_usr_vyatka`, `land_usr_western_kazakhstan`, `land_usr_western_ukraine`, `land_usr_yakutsk`, `land_usr_yenisei`, `land_usr_zuryenia`

**Current:**

```json
{
  "reviewed_directed_requirements": 173,
  "source_ambiguity_rows": 1,
  "mismatches_or_absent_edges": 119
}
```

**Proposed:**

Apply the explicit from→to rows in data/asia_pacific_directional_terrain.json; add real missing border pairs before decorating them. Preserve simultaneous terrain and use separate river boolean.

**Evidence:**

- game_content/rules/GW1936_Terrain_Glossary_v1.pdf pp3–4,11–12

**Scope / dependency:** Complete transcription of express directional approach statements in glossary pp2–4 and11–12, including already-matching rows. Named approaches are source-backed; source with wording is retained as a direction ambiguity. Vyatka self-reference is a source_ambiguity row, not a self-edge. Additive border_terrain_contains must preserve intrinsic/composite terrains. Reef rows constrain amphibious assault only. River penalties do not establish has_river transport continuity.

## AP-091 — Kola coast IDs and printed naval facilities

**Field:** `neighbors / naval_facilities` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_usr_kola`, `sea_a8`, `sea_a9`

**Current:**

```json
{
  "sea_neighbors": [
    "sea_a13",
    "sea_a14"
  ]
}
```

**Proposed:**

```json
{
  "sea_neighbors": [
    "sea_a8",
    "sea_a9"
  ],
  "A8_facilities": [
    "minor_shipyard",
    "major_port"
  ],
  "A8_railway_connection": true,
  "physical_instances": [
    {
      "id": "facility_kola_minor_shipyard",
      "type": "minor_shipyard",
      "sea_accesses": [
        "sea_a8"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "rectangle": [
            3970,
            0,
            4740,
            620
          ],
          "crop": "evidence/ap_kola.png"
        }
      ],
      "notes": "White-square crane by Murmansk. Distinct from the blue-square anchor farther east."
    },
    {
      "id": "facility_kola_major_port",
      "type": "major_port",
      "sea_accesses": [
        "sea_a8"
      ],
      "evidence": [
        {
          "source": "game_content/maps/gw36map.png",
          "rectangle": [
            3970,
            0,
            4740,
            620
          ],
          "crop": "evidence/ap_kola.png"
        }
      ],
      "notes": "Blue-square plain anchor entirely west of the A8/A9 divider."
    }
  ]
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (3970,0,4740,620); evidence/ap_kola.png

**Scope / dependency:** Fresh naval review confirms two distinct A8 facilities: Murmansk white-square minor shipyard and blue-square major port farther east. Neither has A9 access; both lie west of the sea divider. Retain the prior physical coast/terrain findings.

## AP-096 — Queensland–South Australia shared border is entirely inside the Outback

**Field:** `passable/railway_connection` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_aus_queensland`, `land_aus_south_australia`

**Current:**

```json
{
  "passable": true,
  "railway_connection": true
}
```

**Proposed:**

```json
{
  "passable": false,
  "railway_connection": false
}
```

**Evidence:**

- game_content/maps/gw36map.png rect (6100, 3750, 8650, 4888); evidence/ap_australia.png

**Scope / dependency:** The short shared segment is wholly covered by the printed impassable desert area. Physical adjacency can remain with passable:false. NSW–Queensland and NSW–South Australia have real railway borders outside this barrier.

## AP-102 — Give the existing Caroline Islands major port explicit P46 access

**Field:** `naval_facility_storage/sea_accesses` · **Confidence:** high · **Severity:** major

**Regional context:** [asia_pacific](regions/asia_pacific.md)

**Nodes:** `land_jap_caroline_islands`

**Current:**

```json
[
  {
    "id": "facility_caroline_islands_major_port",
    "type": "major_port",
    "sea_accesses": [],
    "storage": "node_facilities"
  }
]
```

**Proposed:**

```json
[
  {
    "id": "facility_caroline_islands_major_port",
    "type": "major_port",
    "sea_accesses": [
      "sea_p46"
    ],
    "evidence": [
      {
        "source": "game_content/maps/gw36map.png",
        "rectangle": [
          7730,
          3010,
          8250,
          3260
        ],
        "crop": "evidence/ap_naval_caroline.png"
      }
    ],
    "notes": "Existing intrinsic major-port type is correct, but the physical port must have explicit P46 access."
  }
]
```

**Evidence:**

- game_content/maps/gw36map.png rect (7730, 3010, 8250, 3260); evidence/ap_naval_caroline.png
- game_content/maps/gw36map.png rect (6250, 2600, 8250, 4030); evidence/ap_se_asia.png

**Scope / dependency:** The printed blue-square plain anchor is a major port in P46. Preserve one physical instance; migrate the intrinsic-only naval storage to explicit sea access rather than adding a second port.
