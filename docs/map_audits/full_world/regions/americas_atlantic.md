# Americas and Atlantic source audit — proposals only

Date: 5 October 2026. Scope: the Americas on both sides of the map seam; Greenland and the northern/central Atlantic islands; western/central Atlantic ocean grid through A54; South American Pacific coastal seas P76–P78. Eastern Atlantic land shores and African islands are shared with the Europe/Africa report; open Pacific cells and islands beyond the Alaskan/continental coast are owned by the Asia/Pacific report.

**No live map, generator, scenario, or tests were changed.** Findings compare the existing JSON and generator against the original 9900 × 4888 board image, using native-resolution crops. The complete Americas terrain-glossary tables on PDF pp5–6 were subsequently rendered, visually checked column by column, and transcribed. Existing IDs are kept in proposals unless the printed territory itself is missing or incorrectly aggregated. These are proposed corrections, not a certified replacement map.

- [Machine-readable findings](../data/americas_atlantic_findings.json): **244** records with exact current data, proposed changes, source rectangles and confidence.
- [Existing-node review ledger](../data/americas_atlantic_review.json): **93** existing node records, including shared sea endpoints. The field-by-field review entries explicitly distinguish checked artwork, partial review, and unresolved interpretation.
- [Intrinsic terrain transcription](../data/americas_atlantic_intrinsic_terrain.json): every one of the **75 Americas glossary rows** on PDF pp5–6, including blank intrinsic columns.
- [Directed terrain/river transcription](../data/americas_atlantic_directional_terrain.json): **59 records** (58 explicit comparisons plus the preserved Amazonas quantifier), with 15 differing existing directions, 30 absent edges, and 13 matching directions. Absent-edge entries require topology reconciliation.
- [Stored physical-pair review](../data/americas_atlantic_edge_review.json): **174** pairs, including confirmed relations, proposed deletions and actual source ambiguities.
- [New land neighbor sets](../data/americas_atlantic_new_node_neighbors.json): **18** complete physical sets.
- [Crop coordinates](../data/americas_atlantic_evidence_rectangles.json): original image coordinates. The `usa_seam` composite uses `(9400,1150,9900,2550)` and `(0,1150,1250,2550)` at unchanged vertical scale; the original black gutter is retained. The Andes/Amazon detail is enlarged 2× from its stated native rectangle.

| Proposal category | Records |
| --- | ---: |
| add | 83 |
| change | 133 |
| delete | 20 |
| uncertain | 8 |

Record counts are not counts of independent game defects: some linked issues describe a node addition, its shoreline and its facilities separately. The sea-grid proposals contain **79 missing reciprocal pairs**: 63 in AM-203 and 16 short offset contacts resolved by enlarged source traces in AM-227. Missing-node proposals give the fields actually supported by the crop and leave other fields unfilled; they must not be applied using blanket defaults.

## Most consequential findings

1. **The ocean graph is not a faithful transcription of the board.** The existing Atlantic is a sparse chain. A38 and A39 are central North Atlantic cells, yet the JSON attaches South America and West Africa to them. A40 is the western Caribbean, yet Buenos Aires/Patagonia/Cape Town are attached there. Missing ocean nodes include A3/A4/A16/A17/A27/A30/A32/A34/A37/A41–A43/A45–A54, plus P76/P77/P78. Both long and short shared sea borders were traced; the previously uncertain Atlantic grid offsets are now concrete additions.
2. **Several direct land routes cross intervening tiles or open water.** Delete San Francisco–Chicago, Chicago–New York, New York–Washington, Upper Midwest–Great Lakes, Appalachia–The Northeast, Southwest US–Texas, Cuba–Hispaniola, Paraguay–Buenos Aires, and the normal Colombia–Peru link. The latter meets the hatched Amazon region rather than an ordinary shared border. Printed rail connectivity through several tiles cannot be represented by a direct adjacency.
3. **Western Amazonas is explicitly impassable.** The crop spells out `AMAZON (IMPASSABLE)`. Peru–Amazonas is currently passable and railway-connected. Propose `passable: false` and no rail for that border; carefully trace northern/southern tips before adding Colombia/Ecuador/Venezuela/Bolivia approaches. Rulebook §1.7 p11 prohibits land entry and railway construction in impassable terrain. This does not by itself settle air, river, or supply interpretation.
4. **The US economic values are materially understated.** Chicago, New York, Washington and San Francisco differ from the printed map; Southwest and Great Plains are also wrong. Chicago and New Orleans have circular/semi-circular zone borders and need `is_city: true`. Printed green airfield icons are missing from Pacific Northwest, San Francisco, New York and Washington.
5. **The Caribbean includes missing and merged territories.** Replace the fictitious unified Hispaniola node with separately printed Haiti and Dominican Republic. Add the listed islands. Panama is US-owned on the board, British Guiana is UK-owned, and Suriname is Netherlands-owned.
6. **The generator invents railways and ports.** Northern South America and Central America contain numerous `link_rail` calls with no printed track. Many `port=True` defaults become minor ports even where there is no port or the printed facility is a major port, shipyard or seaplane base. Bermuda, Suriname, Pampas and Western Mexico have phantom minor-port entries.
7. **Panama Canal endpoints are wrong.** Replace A36↔P31 with A40↔P76 and retain Panama as controlling territory (rulebook §1.8 p15). An incorrect sea shortcut can bypass or misplace canal control even when its label looks correct.

## Naval-facility re-audit — 6 October 2026

The [fresh naval ledger](../data/naval_reaudit_americas_atlantic.json) is the authority for facility existence, type, territory, accessible seas and physical identity. It covers **80 territories**: all 62 existing American land nodes and all 18 proposed land additions, including Greenland, Iceland, Faroe, Shetland and Azores. Every current facility claim and every prior AM facility proposal was compared to newly viewed original-board crops; printed coasts were also scanned for omissions. The result is **44 distinct facility icons on 33 territories**, with **47 explicit empty inventories**. Row evidence supports negative findings as well as positive icons. No dockyard or submarine-base glyph was found in this assigned region; inland airfields are outside this naval inventory.

The fresh review corrects two substantive omissions in the prior proposals. **Western Mexico has no printed port:** the old same-ID minor-port claims on P30/P31 must be removed (AM-244), rather than carried along with the P31 coast correction. **Iceland has one minor port with A3 access only** (AM-243); it was omitted from the earlier new-node facility proposals. Bermuda, Suriname and Pampas empty-facility records are now explicit **deletions**, correcting their misleading prior add/change categories (AM-155/159/162). The retired Hispaniola node and both printed replacement territories were checked separately; Haiti and Dominican Republic have no naval symbols.

The other proposed American facility types and territories survived the fresh glyph/boundary check. A blue crane on a white square marks a minor shipyard; a white crane on a blue square marks a major shipyard. Plain anchor symbols are ports, not dockyards. Notable boundary checks retain the Great Lakes A24 minor port in Great Lakes (not The Northeast), the New England A25 minor shipyard north of the New York circle, and the Buenos Aires A49 minor shipyard inside its city zone (not Patagonia). Canada’s eight printed naval facilities were independently rechecked. Panama’s single minor port is on A40; Chile’s southern major port is P78-only even though Chile also touches A49. A facility is never copied to every sea adjacent to its land territory.

Every positive ledger item now has a distinct proposed physical-instance ID, exact type, explicit sea-access list and source evidence. These IDs identify printed icons; implementation must reconcile them with existing IDs instead of adding duplicate physical facilities. Production map/generator files remain unchanged.

## Printed IPP corrections

| Existing node ID | Current | Proposed | Finding |
| --- | ---: | ---: | --- |
| `land_usa_chicago` | 2 | 3 | AM-001 |
| `land_usa_new_york` | 4 | 5 | AM-002 |
| `land_usa_washington_dc` | 5 | 8 | AM-003 |
| `land_usa_san_francisco` | 4 | 6 | AM-004 |
| `land_usa_southwest_united_states` | 2 | 3 | AM-005 |
| `land_usa_great_plains` | 3 | 2 | AM-006 |
| `land_puerto_rico` | 0 | 1 | AM-007 |
| `land_cuba` | 1 | 0 | AM-008 |
| `land_suriname` | 0 | 1 | AM-009 |
| `land_brazil_pampas` | 1 | 0 | AM-010 |

Other American printed values were visually compared; this table lists differences, not all correct values. Blue numbers beside convoy roundels are not territorial IPP values.

## Missing printed land zones

The following IDs are proposals; existing conventions should be used consistently before implementing them. Root reconciliation uses `land_shetland_islands` as canonical and the regional `land_gbr_shetland_islands` spelling as its alias; these are one tile. All listed islands have zero printed territorial IPP. Owner text follows the printed roundel. The second pass completes the physical neighbor sets for all 18 missing land zones in the linked ledger, including Haiti/Dominican Republic/Aleutians.

| Proposed ID | Printed label | Owner | Confirmed sea access |
| --- | --- | --- | --- |
| `land_greenland` | Greenland | Denmark | sea_a2, sea_a3 |
| `land_iceland` | Iceland | Denmark | sea_a3, sea_a4 |
| `land_faroe_islands` | Faroe Islands | Denmark | sea_a4 |
| `land_gbr_shetland_islands` | Shetland Islands | United Kingdom | sea_a6 |
| `land_azores` | Azores | Portugal | sea_a39 |
| `land_bahamas` | Bahamas | United Kingdom | sea_a37 |
| `land_jamaica` | Jamaica | United Kingdom | sea_a40 |
| `land_haiti` | Haiti | Haiti | sea_a37, sea_a40 |
| `land_dominican_republic` | Dominican Republic | Dominican Republic | sea_a37, sea_a41 |
| `land_leeward_islands` | Leeward Islands | United Kingdom | sea_a41 |
| `land_windward_islands` | Windward Islands | United Kingdom | sea_a41 |
| `land_trinidad` | Trinidad | United Kingdom | sea_a41 |
| `land_netherlands_antilles` | Netherlands Antilles | Netherlands | sea_a41 |
| `land_falkland_islands` | Falkland Islands | United Kingdom | sea_a49 |
| `land_galapagos` | Galapagos | Ecuador | sea_p76 |
| `land_usa_kodiak_island` | Kodiak Island | United States | sea_p5 |
| `land_usa_st_lawrence_island` | St. Lawrence Island | United States | sea_p1 |
| `land_usa_aleutian_islands` | Aleutian Islands | United States | sea_p5; land border with Alaska |

The Aleutian Islands tile includes a sizable part of the Alaska peninsula. Treating it as only an offshore island group would still leave the US land topology wrong. Cape Verde, Canary Islands, Ascension, Saint Helena and São Tomé and Príncipe are visible in the saved Atlantic crops and delegated to the Africa report to avoid duplicate ownership.

## Mainland and shore correction map

The detailed JSON carries exact old values and facility lists. Principal replacements/additions are:

- **Pacific North America:** Pacific Northwest → P13; San Francisco and Southwest US → P25. Western US already uses P25. Western Mexico uses P31, with P30 removed. Alaska/Southeast Alaska currently lack their sea coasts; Southeast Alaska → P6 is clear, and enlarged tracing confirms Alaska → P1/P5/P6 (including Cook Inlet in P5). Kodiak → P5 and St. Lawrence Island → P1.
- **Eastern US:** New England → A25 is missing, together with its connections to New York and The Northeast. Carolinas → A30 replaces A26. Texas → A36 is missing. Washington has A30 coast only, with its major shipyard there; The Northeast has the A25 strip between New York and Washington. Florida's endpoints confirm Southeastern US → A30/A36/A37. The existing Great Lakes A24 minor port remains in Great Lakes; the added Northeast A24 shore has no port.
- **Central America:** Central America and Panama touch A40 and P76. Colombia touches A40 and P76. Ecuador spans P76/P77; Peru uses P77. Chile spans P77/P78, and the southern Chilean islands also have A49 shoreline.
- **Northern South America:** Venezuela's major port is on A41, with western coastline into A40. British Guiana, Suriname and French Guiana use A41. Enlarged source confirms Amazonas/A41 and Caatinga/A45 meet exactly at the coast junction; A42 stops offshore, so no extra corner-only coast is added.
- **Eastern South America:** Caatinga spans A45 and A47; its printed minor port and seaplane base lie in A45. Rio de Janeiro, Pampas and Uruguay use A47. Buenos Aires and Patagonia use A49. The existing A38/A39/A40 attachments are geographically wrong.
- **Facility types:** New York/Washington/Carolinas/New Orleans/San Francisco/Southwest US show major shipyards; Pacific Northwest/New England/Texas/Buenos Aires show minor shipyards at the specified shores. Peru has a minor shipyard and major port; Chile has a northern minor shipyard and southern major port. Rio de Janeiro/Uruguay/Patagonia show major ports. Cuba's port is major, Puerto Rico's facility is a seaplane base. Preserve one stable ID per physical icon and do not copy each facility to every sea touched by its territory.

## Rail, river, terrain and crossings

The northern South America rail removals are based on absence of printed dashed tracks across the entire relevant approach, not on modern geography. Examples: Colombia–Panama/Venezuela/Ecuador, the Guianas, Ecuador–Peru, Peru–Amazonas, Bolivia–Paraguay/Pampas, Amazonas–Caatinga, and Caatinga–Rio de Janeiro. Actual southern railways, including Peru–Bolivia and the Chile/Argentina/Brazil network, are retained where drawn. A further enlarged trace removes direct Peru–Chile and Buenos Aires–Uruguay rail flags: those drawn routes reach their neighbor through Bolivia or Norte Grande respectively. The Paraguay triple junction and Chile/Patagonia ridge retain exact rail attribution uncertainty. US corrections remove five unsupported shared-border rail flags and add the visible Southwest US–Great Plains railway (AM-238/239).

Several existing South American `river_crossing` penalties have no blue river artwork: Colombia–Venezuela, Venezuela–British Guiana, Guiana–Suriname, Suriname–French Guiana, and the listed Paraguay/Pampas/Uruguay/Argentina connections. The real Amazonas river network is visibly present; converting its channel continuity into legal `has_river` transport requires the distinct rules model described in the root mechanisms report. The US Mississippi/Great Lakes river network likewise remains only partially represented. Rivers usable for strategic movement are not equivalent to printed railroad tracks.

The complete glossary check resolves intrinsic terrain that the board crop alone left tentative. **Upper Midwest, Great Plains, Pacific Northwest, Southwest US, San Francisco, The Northeast, Cuba, Caatinga, Rio de Janeiro and Pampas are mountain. Colombia, Ecuador, Bolivia, Panama, Central America, Suriname and French Guiana have blank intrinsic columns (normal), with specific mountain/jungle approaches recorded separately.** Existing correct intrinsic entries were also compared; this is not a selection of only changed rows. Baffin Island is explicitly held uncertain: the glossary row is blank, unlike Keewatin’s marked tundra, while the board’s white interior and earlier Canadian audit suggest ice/tundra.

All named directional requirements in glossary pp5–6 are now transcribed. Examples include Great Lakes → Washington river; Washington/Appalachia/The Northeast → Great Lakes mountain; Chicago/Great Lakes → Appalachia river; New Orleans/Appalachia → Southeastern US mountain; New Orleans → Texas river; and P1 → Alaska mountain+tundra plus river. Entering Pampas from Uruguay/Norte Grande/A47 combines its intrinsic mountain with a jungle approach. The glossary explicitly supports missing Great Lakes–Washington, Great Lakes–Appalachia, Appalachia–Southeastern US, Yukon–Southeast Alaska, Alberta–Pacific Northwest/Upper Midwest and The Northeast–A25 approaches; the second pass physically confirms the six grouped borders and their rail values in AM-241, with the remaining seam questions preserved. Unlisted directional fields still require rules interpretation rather than copied reciprocal defaults.

The Amazonas row says river border from all adjacent territories. Its literal quantifier is preserved along with eight conditional land expansions. It must not create a legal crossing through the hatched impassable region or be mistaken for a complete navigable `has_river` network. Whether this wording includes the A41 landing approach remains explicit uncertainty. Unlisted directional paths are not treated as automatically false or normal.

The three visible Canadian narrow crossings retain their printed capacity 1. Proposed blocker seas, also communicated to the parent structural audit, are Keewatin–Baffin: A1; Labrador–Newfoundland: A15 and A18; Newfoundland–St. Pierre: A18. The Japan audit established the required distinction between capacity, direct land crossing and ordinary coastal access; it should be applied consistently here. Canada was previously audited and user-approved seam links were retained, not overruled by this pass.

## Generator locations and implementation implications

The existing source is `tools/build_manual_map_json.py`, particularly the sea declarations around lines 406–460, American node declarations around 647–705, initial Atlantic chain around 912–925, direct long railway links around 997–998, North American land routes around 1244–1284, and South American land routes around 1286–1318. Coastal `port=True` calls and final symmetric closure are later in the same generator. The generated `gw36_manual_map.json` matches these authored mistakes; a structural reciprocal-edge test cannot detect a fictitious geographic link.

A future implementation should edit the generator and regenerate the full map before generating scenarios. That work is **not performed or authorized by this proposal report**. Every endpoint migration must reconcile reverse edges and physical facility identity. Do not preserve arbitrary old sea names that misidentify where the printed numbered cell is.

## Second-pass physical coverage and remaining limits

The [stored-pair ledger](../data/americas_atlantic_edge_review.json) records all **174** unordered stored pairs touching the 93 assigned/shared nodes after excluding remote European/African land endpoints: **124 physically confirmed, 46 proposed deletions and 4 source-registration uncertainties**. Every pair has source evidence, checked fields, unresolved fields and linked findings. Shared Pacific pairs were checked against the native Pacific crops; canal endpoints were cross-checked with Europe/Africa evidence. The [new-land neighbor ledger](../data/americas_atlantic_new_node_neighbors.json) completes definite physical neighbor sets for all **18** added land territories.

The four unresolved physical pairs are Alberta–Manitoba, Mackenzie–Keewatin, Great Plains–Texas and Midwest–Upper Midwest. Both source fragments were inspected; the raster has unequal edge-art alignment, so a same-row overlap is insufficient proof. Previously user-approved Canadian links are retained. Great Lakes/Midwest, the Paraguay triple junction and Chile/Patagonia also retain rail attribution uncertainty after enlarged inspection. **A confirmed physical pair is not a claim that all directional fields are verified.** Other remaining questions concern directions not enumerated in the glossary and the Amazonas quantifier, shore railway-field semantics under whole-zone coverage, territory capital/victory flags against national sheets, and the conversion of printed river artwork into legal river supply paths. The root convoy register separately completes the route transcription. Rulebook §13.2.8 p98 states that a zone with a border-crossing railway is covered by rail. A dedicated physical spur to each port must not be imposed as an extra rules prerequisite; AM-229 now asks how the shore field should represent that rule. Root owns the global gauge/convoy/schema review. The saved static board image is evidence for printed geography and infrastructure, not a complete unit/factory/treasury setup.

## Evidence rectangles

All coordinates are `(left, top, right, bottom)` in the original image. Files contain source crops, not generated reconstructions.

| Crop | Source rectangle |
| --- | --- |
| [arctic](../evidence/americas_arctic.png) | `(0, 0, 2250, 1450)` |
| [usa_east](../evidence/americas_usa_east.png) | `(0, 1200, 1300, 2420)` |
| [usa_west](../evidence/americas_usa_west.png) | `(9400, 1180, 9900, 2350)` |
| [central](../evidence/americas_central.png) | `(0, 2260, 1470, 3150)` |
| [south_north](../evidence/americas_south_north.png) | `(0, 2750, 1500, 3880)` |
| [south_south](../evidence/americas_south_south.png) | `(0, 3500, 1500, 4600)` |
| [alaska](../evidence/americas_alaska.png) | `(8500, 0, 9900, 1460)` |
| [atlantic_south](../evidence/americas_atlantic_south.png) | `(1300, 3250, 3300, 4888)` |
| [atlantic_north](../evidence/americas_atlantic_north.png) | `(1300, 0, 2700, 2070)` |
| [atlantic_mid](../evidence/americas_atlantic_mid.png) | `(1080, 1700, 2500, 3400)` |
| [usa_dc_coast](../evidence/americas_usa_dc_coast.png) | `(480, 1580, 980, 2140)` |
| [usa_northeast](../evidence/americas_usa_northeast.png) | `(250, 1370, 1000, 1900)` |
| [america_south_borders](../evidence/americas_america_south_borders.png) | `(430, 3380, 1140, 4090)` |
| [atlantic_grid](../evidence/americas_atlantic_grid.png) | `(900, 650, 2200, 2870)` |
| [brazil_coasts](../evidence/americas_brazil_coasts.png) | `(850, 2890, 1750, 3770)` |
| [atlantic_bottom](../evidence/americas_atlantic_bottom.png) | `(250, 3780, 2300, 4888)` |
| [andes_amazon_detail](../evidence/americas_andes_amazon_detail.png) | `(280, 2900, 930, 3550)` |

## Glossary page evidence

- [Complete Americas page 5](../evidence/americas_glossary-05.png), rendered directly from PDF page 5.
- [Complete Americas page 6](../evidence/americas_glossary-06.png), rendered directly from PDF page 6.

The transcriptions preserve the printed meaning while mapping spellings such as Columbia/Colombia, Ottowa/Ottawa, and Alberta-Kaskatchewan to established canonical IDs. New IDs remain proposals; Attu/Kiska uses the Asia/Pacific proposal ID to avoid a duplicate.

The crop-coordinate JSON also indexes the enlarged second-pass US interior/seam, Alaskan coast, Florida/Cuba, Hispaniola, Amazon coast, Chile tip, southern railway junctions and Atlantic staggered-grid detail images. These crops retain the original raster content; enlargement does not invent resolution.
