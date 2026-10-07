# What belongs in the world-map data

Audit date: 5 October 2026. These are proposals, not an applied schema migration.
The scope is the full Global War 1936 board. Campaign exclusions do not remove
features from this world dataset.

Source: [v4.3 rulebook](../../../game_content/rules/Global%20War%201936%20v4.3%20Rulebook.pdf).
Page numbers below are both PDF and printed pages. The original board image and
terrain glossary provide the geographic evidence; the rulebook determines how
that geography is used. A field being present does not mean the engine implements it.

## Recommended separation

| Store | Include | Keep elsewhere |
|---|---|---|
| Static world map | Printed zones, original roundel identity, printed IPP, intrinsic terrain, directed approach terrain, physical borders, coasts, rivers, printed rail, printed facility instances and their accesses | Current possession, units, damage, construction, active blockades, permissions, expenditure counters |
| Static geographic feature layers | Named canals/straits, narrow crossings, convoy lines, exceptional route endpoints, geographic rail-region membership, Great Barrier Reef coast restriction | Rules determining who may use a route, when it opens, costs, combat modifiers and turn limits |
| Rules / nation profiles | Home-country definitions, rail capacities, special-fortification coverage rule, national abilities, wartime income and objective predicates | Duplicate copies of ordinary terrain or adjacency |
| Scenario / initial state | Start date, starting ownership/control, capital assignment, setup pieces, setup-only factories and queues, selected map subset | Reinterpretations of the world map's printed geography |
| Runtime state | Captures, relocated capitals, destroyed cities, rail/facility damage, built infrastructure, convoy losses, permission decisions | Changes to immutable printed facts |
| Optional display/evidence sidecar | Board pixel coordinates, label positions, source rectangles, citations, review status | Movement decisions based on display coordinates alone |

Separate files are acceptable. A small `map_bundle` manifest can reference these
layers instead of making one JSON file enormous. Cross-file IDs must validate
against one canonical node roster.

## Add or strengthen static geographic information

### MS-01 — Convoy routes: include, once per physical line

**Current:** the production JSON has only `_meta` and `nodes`. There is no convoy
layer. The existing `japan_china_1936/m0/convoy_audit.json` is an audit specification,
not an implemented map layer. This distinction matters even though convoys are
excluded from the latest regional campaign.

**Propose:** `convoy_lines` records with stable ID, printed name, beneficiary
nation ID, printed maximum IPP loss, typed land/sea endpoints, ordered traversed
sea zones, and source evidence. Some lines have no printed numeric cap; preserve
that as unresolved/rule-defined rather than inventing zero or infinity.

Do not store a separate loss allowance on every sea tile. Multiple sea zones on
the same line share one line-level limit per Player Turn. The cap is **not income**.
Closure, raiding eligibility, actual losses, escorts and resets belong to rules
and runtime state. References: §1.5 p10; §10.9 pp71–72.

The retained Japan audit provides complete Nagasaki/Tokyo geographic proposals.
[Convoy review](convoy_review.md) adds thirteen complete traces and the Manila line's
complete sea path with its Philippine land endpoint explicitly unresolved.
Brief intermediate sea-zone crossings are preserved.

### MS-02 — Canals and straits: give each passage a typed identity

**Current:** strings are repeated on coast, land and sea edges without canonical
controlling-zone references. Seven distinct names are represented; Baltic–White Sea
Canal is absent. Some endpoints are geographically wrong; see regional findings.

**Propose:** a `passages` layer containing `id`, `kind` (`canal` / `strait`),
`controlling_land_ids`, sea endpoints/access path and a `rule_id`. A passage can
have more than one controller. Preserve ordinary coasts separately from the
special naval transit. A named geographic strait is not automatically a
rule-controlled strait: do not grant Hormuz, for example, an invented closure rule.

| Printed rule feature | Type | Controlling land | Source |
|---|---|---|---|
| Strait of Gibraltar | Strait | Gibraltar | §1.8 p14 |
| Danish Straits | Strait | Denmark | §1.8 p14 |
| Panama Canal | Canal | Panama | §1.8 p15 |
| Suez Canal | Canal | Lower Egypt | §1.8 p15 |
| Kaiser-Wilhelm Kanal | Canal | Western Germany | §1.8 p15 |
| Baltic–White Sea Canal | Canal / restricted special transit | Leningrad and Karelia | §1.8 p15 |
| Turkish Straits | **Canal for game rules** | Istanbul | §1.8 p15 |
| St. Lawrence Seaway | Canal | Ottawa | §1.8 p15 |

These are eight rule features. The current seven-name set omits Baltic–White Sea
Canal. Its restricted transit needs an explicit representation in addition to
correcting the other passages' endpoint and controller records.

Neutral permissions, submarine exceptions, forcing a strait, Turkish restrictions,
and current control belong in rules/state. A generic `passable: true` cannot express
them. Review the complete table and footnotes, not only its headings.

### MS-03 — Exceptional routes: include geography without normal adjacency

Add typed references to three kinds of special route:

| Feature | Geographic record | Rule behavior kept outside normal neighbor traversal |
|---|---|---|
| Northern Sea Route | A9 ↔ P1 | USSR/permission; one naval unit per Player Turn; must start at an endpoint; uses full movement (§1.13 p17) |
| Baltic–White Sea Canal | A14 ↔ A9; Leningrad/Karelia | One submarine in non-combat, full movement, specific permission and lend-lease conditions (§1.8 p15) |
| Burma and Ledo Roads | Burma–Yunnan; Bengal extension | Supply/lend-lease exception across impassable terrain; opening conditions and purchase permissions; not ordinary road movement and not bombable (§1.12 p17) |

A9 is absent from the current node roster. Do not create an ordinary, unlimited
A9–P1 sea edge or remove the Himalayan land restriction to make a route work.

### MS-04 — Narrow crossings: consolidate complete crossing records

Keep land endpoints, printed unit capacity and **every sea touching the crossing
line**. The present `narrow_crossings` field means capacity, despite its plural
name. Rename to `unit_capacity` in a deliberate migration, with compatibility
handling if a consumer already uses the old name.

The audit finds five stored land crossings without blocking seas, and two
land–sea pairs carrying legacy narrow-crossing capacity. Do not treat these as
certified crossings. Source §1.9 p16 distinguishes amphibious Marine combat moves
from infantry-class non-combat moves; strategic rail movement is prohibited.

Also encode which naval transit/access paths cross the line. Coastal Artillery can
fire at ships crossing it, including ships scrambling out of a facility. Knowing
only that two lands share a sea is insufficient for this. The London/Picardy
example explicitly requires this distinction (§13.2.7 p98).

### MS-05 — Great Barrier Reef and mode-specific restrictions

Record the Queensland approaches from **P64, P71 and P72** as prohibiting
amphibious assault (§1.14 p17). These seas are not interchangeable with an
invented generic Coral Sea label. P71/P72 currently do not exist in the JSON.

Do not set the entire coast to `passable: false`: that would also suppress other
coast uses not forbidden by this rule. Recommend edge capabilities or a specific
`amphibious_assault_allowed: false` geographic restriction with a rule reference.
Likewise, impassable land terrain blocks land movement and rail construction but
does not prohibit aircraft flying over it (§1.7 p11).

### MS-06 — Multiple intrinsic terrains and directional approaches

Nodes need to support multiple simultaneous terrains, as edges already do. For
example, the terrain glossary marks several Indonesian territories and New Guinea
as both mountain and jungle. Do not pick one arbitrarily or invent a `forest`
movement rule. The current node vocabulary includes four `forest` entries and
one `mountain_border`; neither is a normal intrinsic terrain category in §1.7.

Keep `is_city` separate from terrain. Maintain direction-specific
`border_terrain` and `river_crossing`; their reverse values need not match.
For sea→land approaches, inspect the shortest path from the printed sea-zone
number to the destination roundel, staying within those two zones (§1.7 p11).
Terrain elsewhere in the originating land is not automatically applied.
References: §1.7 pp10–14; terrain glossary pp2–10.

### MS-07 — Rail gauge and strategic movement regions

**Current generator defect:** the final pass derives gauge change solely from
whether exactly one endpoint's `original_owner` equals `Soviet Union`
(`tools/build_manual_map_json.py`, final gauge loop). This erases any independently
authored gauge annotation.

**Propose:** retain boolean rail presence per border, but record the printed gauge
on each side/segment; derive a gauge transition from those verified values. This
does not require one rail record per drawn track. The map uses white versus yellow
checkered lines (§1.6 p10). The construction table also assigns broad gauge to
Brazil, Spain, Finland, Mongolia and Tannu Tuva, as well as USSR (§13.2.8 p98).
That construction default is supporting evidence, not a substitute for inspecting
an existing printed railway. A missing railway cannot be fixed by only changing
its gauge.

Add `strategic_rail_region_id` or a separate geographic membership table. The
seven capacity regions are North America, South America, Europe, Soviet Union,
Africa, Middle East and Asia (§11.2 p74). Capacity values and usage counters belong
to rules/state. Borderline membership needs explicit source review; changing a
territory's owner must not silently move it to another rail region.

### MS-08 — Rivers: separate crossings, navigable routes and river banks

`river_crossing` and `has_river` already express different concepts and must stay
separate. The global file contains only 16 reciprocal river-route pairs versus
87 directional combat crossing flags. This count is evidence of limited authored
coverage, not a rule that the two sets must be equal.

For supply/strategic movement, identify route segments and any bordering land
zones whose enemy possession blocks use (§1.7.6 p12; §1.11 p16; §11.2 p74).
An adjacency boolean alone may not identify which bank controls a route or whether
an interior river actually connects the relevant access points. Recommend a
`river_routes`/segment layer, with bank references only where the printed geography
and rules require them. Do not add all neighboring lands as river-connected just
because one river is drawn somewhere in each tile.

### MS-09 — Printed facility identity and access

The [6 October naval recheck](naval_facility_reaudit.md) supplies the revised
physical roster. Establish facility existence, type, territory and sea access
before assigning an ID. The earlier conditional naming examples were not an
adequate basis for retaining ports from the current map.

The audit detects four IDs reused across unrelated territories. The default ID
helper drops the first word after `land_`, so different Somalilands, Egypts,
Moroccos and African territories can collapse into one physical facility.
Assign stable IDs from the full land ID plus a local instance suffix. Preserve
already valid IDs; distinguish multiple shipyards in one tile.

Recommend a canonical facility-instance registry and explicit access records.
Nanking's shared physical port should be one instance with two sea accesses;
Honshu's two P15 shipyards should remain two instances. Access routes may encounter
narrow-crossing artillery; facility location also matters for blockade and
scrambling (§1.4 p10; §9.4.6; §10.4 p63).

Only seven intrinsic facility instances are currently stored on six nodes. This
is clearly incomplete against the many printed airbase symbols across the board.
The Caroline Islands' intrinsic `major_port` has no access sea in that record.
Regional reports identify actual printed facilities; do not assume every coast
has a minor port. Keep setup-chart factories and later built facilities in initial
or runtime state so they are not counted twice.

Do **not** make a separate drawn rail spur to each port a new movement requirement.
Under §13.2.8 p98, a land zone with a border-crossing railroad is covered with rail.
Derive usable zone coverage from rail infrastructure and the relevant rules/state.
Current coast-edge `railway_connection` flags need a semantic migration decision;
they must not authorize rail travel into a sea or imply that an otherwise covered
zone's facility is unusable because no spur was transcribed. Detailed facility
position is still needed for the expressly location-dependent rules above.

### MS-10 — Provenance, aliases and uncertainty

Add a schema version and field/feature-level source references in an audit sidecar:
source hash, printed/PDF page, original-image rectangle, reviewed fields,
confidence, unresolved alternative and date. `false` must not silently mean
“not inspected.” Existing global warnings cannot tell a consumer which individual
border or facility is trusted.

Keep stable node IDs and the user's existing warlord display names. Use aliases
for printed/glossary spelling variants. Avoid changing a territory's identity
just to match a fuzzy name. For seas, use their printed IDs as the primary labels;
unverified descriptive names such as “Mozambique Channel” on I1 can mislead a
reader into editing the wrong zone.

## Keep outside the core map

### MS-11 — Kamikaze zones: do not add a per-sea ability flag

Follow the user's requested separation. Keep Japan's kamikaze ability, activation,
range definition, explicit rule exceptions and use counters in the Japan rules
profile. §15.4 p105 defines the range in relation to Japanese Home Country and
prints symbols as a reference. If a printed-zone list is needed to test a rules
interpretation, place it in that profile or an audit fixture, not general sea-node
geography. Do not use a graph-distance computation until special passages and
the rule's interpretation have been validated.

### MS-12 — Special fortification coverage

All city land zones, Panama, British Malaya and Crimea have whole-zone coverage
under §1.10 p16. This does **not** mean a fortification starts there.
Keep the generic city rule and the three explicit geographic exceptions in the
fortification rules profile, referencing canonical nodes. The currently always-null
edge field `special_fortification` should be retired or precisely redefined; it
cannot substitute for coverage rules or actual placed pieces.

### MS-13 — Home countries, capitals, ownership and bonuses

The existing nation-home-country file is an appropriate separate rules-geography
index (§0.2 p6). Revalidate it after completing the node roster: USSR, ANZAC and USA
membership is currently derived from incomplete source data. USA's BFS can include
or exclude a territory merely because an erroneous edge exists. Tannu Tuva's
roundel/identity remains a specific unresolved source question.

Concrete sidecar corrections are WG-038–WG-042: restore New England to USA,
remove South Sakhalin from USSR, and include Northern Ireland, Sydney and the
missing Soviet zones once their world records exist.

Store printed/original roundel identity separately from scenario possession and
political control. Sea zones cannot be possessed (§1.2 p10); `Neutral` on sea
owner fields must not confer neutral-country movement restrictions. Recommend
null/absent owner fields for sea nodes in a versioned migration.

Starting capital locations belong to setup/nation profiles; relocation and city
destruction belong to runtime state. Printed city/victory-city designation is
static, but an active scoring city is not immutable (§3.2; §10.6.2; §10.10.3).
Wartime bonus flags, strategic-objective emblems, recruitment triggers and national
income gates belong in rules records referencing map IDs, not extra unconditional
`ipp_value` on a tile (§0.2 p8 and nation sheets).

## Acceptance conditions before applying a migration

1. Complete the source roster, then fix physical adjacency before derived ranges,
   home-country searches, supply or economic routes are trusted.
2. Every proposal identifies current and proposed values, source and uncertainty.
   Do not use uncertain records as automatic patches.
3. Every referenced node, passage, facility and route resolves; physical facility
   identity is unique while legitimate multi-access facilities stay shared.
4. Reciprocal physical infrastructure agrees; directional terrain/crossing values
   are checked independently. Separate ordinary adjacency from special transit.
5. Regenerate data from the authored builder and validate that a second build is
   identical. Re-extract scenario maps afterwards; campaign exclusions remain
   campaign-only.
6. Test meaningful behavior: a single convoy cap across multiple seas, no ordinary
   Northern Sea Route traversal, reef-blocked amphibious assault without deleting
   the coast, independent shipyards, and no rail across a narrow crossing.
