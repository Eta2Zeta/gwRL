# Europe, Africa, Middle East and western USSR map audit

**Proposal audit, 5–6 October 2026. Live map and generator unchanged.**

The ledger contains **169 existing nodes** (145 land zones, 24 seas), **244 addition proposals, 354 change proposals, 60 deletion proposals and 4 unresolved records**. These are proposal records, not counts of individual altered fields: one directional row may specify several incoming edges. Twenty-eight printed land zones are absent from the current JSON.

The map is substantially incomplete outside the previously audited theatres. The most urgent errors are movement shortcuts through the wrong sea zones, ordinary land edges across open water, whole missing territories, systematically guessed railways/ports, and terrain/income values that disagree with the printed roundels. Do not use the current world graph as a rules-complete movement network.

## Evidence and coverage

- Primary source: `game_content/maps/gw36map.png`, native size 9900 × 4888. Native-resolution crops are saved under `evidence/ea_*.png`; each finding carries exact source rectangles.
- Terrain and explicit directional crossings: `game_content/rules/GW1936_Terrain_Glossary_v1.pdf`, printed pp7–11. Pages 7–10 were also rendered and visually checked so column alignment does not depend on text extraction.
- Rules: v4.3 rulebook §§1.7–1.10, pp10–16: roundel terrain, shortest path through the two zones, directional river combat flags, narrow crossings and controlled passages.
- Existing adopted Abyssinia seven-neighbor/rail/river and combined-terrain rulings are preserved. Neither this report nor the older glossary overrides the project’s adopted source interpretations.
- **Coverage is explicit by field:** every listed regional land zone had terrain/income checked. The second pass records 357 stored physical pairs, including the regional sea network, with per-pair rail/river checks and genuine source uncertainties. The three Afghanistan/Punjab–Iran pairs are assigned to Asia/Pacific. Facility sharing, gauge and other fields are certified only where individually evidenced.
- The complete exact before/after register is [europe_africa_middle_east_findings.json](../data/europe_africa_middle_east_findings.json). [The review ledger](../data/europe_africa_middle_east_review.json) records scope for each existing node; [expected node values](../data/europe_africa_middle_east_expected_nodes.json) provide the compact terrain/income transcription and missing-node starters.

## Second-pass physical geography register

[Stored-pair review](../data/europe_africa_middle_east_edge_review.json) contains **357 existing physical pairs** with confirmation, proposed deletion, or a source-specific uncertainty. [New-node topology](../data/europe_africa_middle_east_new_node_topology.json) supplies all **28 missing land tiles** with definite neighbors and ambiguous contacts separated. Three additional findings complete A5/A8/A9 identities with inspected sea/coast endpoints; A9 reaches Samoyedia. Its printed P1 arrow denotes the restricted Northern Sea Route (§1.13 p17), modeled as an exceptional route rather than ordinary sea adjacency; A14 transit likewise requires the Baltic–White Canal.

The second pass removes additional shortcuts through Rome/Lazio, Berlin/Bohemia, Kaluga Oblast, Taurida and the White Sea. It adds missing ordinary borders in Europe, the Nile region and West Africa; corrects false cross-border rails; and supplies reciprocal river-route proposals where a continuous printed blue river was traced. Physical adjacency and legal ground passability remain separate where impassable shading reaches a border.

The key new deletion pairs are Northern Italy–Lazio, Rome–Southern Italy, Alsace-Lorraine–Western Germany, Bavaria–Eastern Germany, West Poland–Lithuania, Sudan–Eritrea, Tunisia–Tripoli, Kola–Northern Russia, Northern Russia–Western Russia, Moscow–Smolensk, Kiev–Taurida, Crimea–Southern Ukraine, Kalmytskaya–Saratov, North-Caucasia–Stalingrad and Gorky–Tula-Lipetsk. The exact records, including before values and evidence, are in the machine register; the first-pass tables below remain a readable selection rather than the full final register.

## Highest-priority topology repairs

| Feature | Proposed board connection | Incorrect current connection |
| --- | --- | --- |
| Gibraltar | A44 ↔ M2, controlled by Gibraltar | A44 ↔ M1 |
| Turkish Straits | M7 ↔ M10, controlled canal through Istanbul | M5 ↔ M10 and M9 ↔ M10 |
| Suez | M8 ↔ I5, controlled by Lower Egypt | M9 ↔ I5 and M9 ↔ I3 |
| Caspian | M12 is an inland basin, with its own printed shores | M11 ↔ M12 is an ocean shortcut |
| Danish Straits | A10 ↔ A12, controlled by Denmark | Missing; A11 ↔ A12 is not this strait |
| Kaiser-Wilhelm Kanal | A11 ↔ A12, controlled by Western Germany | Present as an unrestricted sea edge |
| Red Sea | I5, with I4 at its southern exit | I3 is incorrectly labeled Red Sea |
| Mozambique/East African seas | I1–I3 around Madagascar and the East African coast | Most shores assigned wholesale to I4 |

Proposed positive-length Mediterranean sea borders, including controlled passages, are:

`M1–M2, M1–M3, M2–M3, M2–M4, A44–M2, M3–M6, M4–M6, M4–M8, M5–M6, M6–M7, M6–M8, M7–M8, M7–M9, M7–M10 [Turkish], M8–M9, M8–I5 [Suez], M10–M11`.

M3–M6 is the water gap between Sicily and Southern Italy. Do not infer a free land connection from that sea boundary or automatically close it because a land narrow crossing exists. Tiny triple contacts are excluded from this proposed sea graph.

## Missing printed land zones

These are certain missing identities. The second-pass [new-node topology ledger](../data/europe_africa_middle_east_new_node_topology.json) supplies definite land, narrow-crossing and sea neighbors for all 28, with ambiguous contacts kept separate. Directional effects and facilities remain separate proposals.

| Zone | Terrain | IPP | Original national identity |
| --- | --- | --- | --- |
| Northern Ireland | normal | 0 | United Kingdom |
| Shetland Islands | mountain | 0 | United Kingdom |
| Iceland | mountain, tundra | 0 | Denmark |
| Faroe Islands | mountain | 0 | Denmark |
| Svalbard | mountain | 0 | Norway |
| Northern Norway | mountain | 1 | Norway |
| Helsinki | normal | 1 | Finland |
| Sicily | mountain | 0 | Italy |
| Malta | normal | 0 | United Kingdom |
| Rhodes | mountain | 0 | Italy |
| Peloponnese | mountain | 0 | Greece |
| Crete | mountain | 0 | Greece |
| Ifni | mountain | 0 | Spain |
| Rio de Oro | desert | 0 | Spain |
| Canary Islands | mountain | 0 | Spain |
| Cape Verde | mountain | 0 | Portugal |
| Mauritania | normal | 0 | France |
| Portuguese Guinea | normal | 0 | Portugal |
| French Guinea | normal | 0 | France |
| Sierra Leone | normal | 0 | United Kingdom |
| Liberia | normal | 0 | Liberia |
| Ivory Coast | normal | 0 | France |
| Gold Coast | normal | 1 | United Kingdom |
| São Tomé and Príncipe | normal | 0 | Portugal |
| Ascension | normal | 0 | United Kingdom |
| Réunion | mountain | 0 | France |
| Yemen | mountain, desert | 0 | Yemen |
| Saint Helena | mountain | 0 | United Kingdom |

Greenland and Azores are coordinated with the Atlantic audit; omitted western/eastern Soviet regions are coordinated with the Asia audit. Missing minor cities/islands are not merely labels for the nearest existing land zone.

## Existing node changes

### Terrain and income

The following are exact proposed corrections. Income changes on existing regional nodes net **−17 IPP** before adding the missing zones. That is a transcription comparison, not a campaign income adjustment. Mixed Northern Algeria terrain, like mixed Iceland/Yemen on new nodes, must remain representable without collapsing an all-combat terrain into only a first-round border penalty.

| ID | Territory | Field | Current | Proposed |
| --- | --- | --- | --- | --- |
| EA-001 | Scotland | terrain | mountain_border | mountain |
| EA-002 | Scotland | ipp_value | 2 | 1 |
| EA-003 | Southern England | ipp_value | 2 | 3 |
| EA-004 | Ireland | ipp_value | 2 | 1 |
| EA-005 | Galicia and Leon | terrain | normal | mountain |
| EA-006 | Basque Country | ipp_value | 1 | 0 |
| EA-007 | Madrid | terrain | normal | mountain |
| EA-008 | Western Andalucia | ipp_value | 1 | 0 |
| EA-009 | Eastern Andalucia | ipp_value | 1 | 0 |
| EA-010 | Picardy | ipp_value | 2 | 1 |
| EA-011 | Southern France | ipp_value | 2 | 1 |
| EA-012 | Alsace-Lorraine | ipp_value | 2 | 3 |
| EA-013 | Eastern Germany | ipp_value | 2 | 4 |
| EA-014 | Northern Italy | ipp_value | 4 | 3 |
| EA-015 | Rome | terrain | normal | mountain |
| EA-016 | Lazio | terrain | normal | mountain |
| EA-017 | Lazio | ipp_value | 1 | 0 |
| EA-018 | Southern Italy | ipp_value | 2 | 1 |
| EA-019 | Corsica | ipp_value | 1 | 0 |
| EA-020 | Trondelag | ipp_value | 1 | 0 |
| EA-021 | Lapland | terrain | tundra | normal |
| EA-022 | Southern Finland | terrain | forest | normal |
| EA-023 | Viipuri Province | terrain | forest | marsh |
| EA-024 | Viipuri Province | ipp_value | 1 | 0 |
| EA-025 | Estonia | ipp_value | 1 | 0 |
| EA-026 | Latvia | ipp_value | 1 | 0 |
| EA-027 | Podlachia | ipp_value | 1 | 0 |
| EA-028 | Lubelskie | ipp_value | 1 | 0 |
| EA-029 | Dolnoslaskie | ipp_value | 1 | 0 |
| EA-030 | Albania | ipp_value | 1 | 0 |
| EA-031 | Macedonia | terrain | mountain | normal |
| EA-032 | Macedonia | ipp_value | 1 | 0 |
| EA-033 | Istanbul | terrain | normal | mountain |
| EA-034 | Eastern Anatolia | ipp_value | 1 | 0 |
| EA-035 | Northern Iran | ipp_value | 1 | 0 |
| EA-036 | Syria | terrain | normal | desert |
| EA-037 | Transjordan | ipp_value | 0 | 1 |
| EA-038 | Northern Algeria | terrain | mountain | mountain, desert |
| EA-039 | Northern Algeria | ipp_value | 0 | 1 |
| EA-040 | French Sudan | terrain | desert | normal |
| EA-041 | Niger | terrain | desert | normal |
| EA-042 | Chad | terrain | desert | normal |
| EA-043 | Oubangui-Chari | terrain | jungle | normal |
| EA-044 | Southwest Africa | terrain | desert | normal |
| EA-045 | Madagascar | terrain | jungle | mountain |
| EA-046 | Mauritius | terrain | normal | mountain |
| EA-047 | Seychelles | terrain | normal | mountain |
| EA-048 | Karelia | terrain | forest | normal |
| EA-049 | Northern Russia | terrain | tundra | normal |
| EA-050 | Yaroslavl | ipp_value | 1 | 0 |
| EA-051 | Northern Belorussia | ipp_value | 1 | 0 |
| EA-052 | Kiev | ipp_value | 0 | 3 |
| EA-053 | Southern Ukraine | ipp_value | 1 | 0 |
| EA-054 | Donets-Kuban | ipp_value | 1 | 0 |
| EA-055 | Azerbaijan | original_owner | Azerbaijan | Iran |
| EA-056 | Syria | original_owner | Syria | France |
| EA-057 | Transjordan | original_owner | Transjordan | United Kingdom |
| EA-058 | Kuwait | original_owner | Kuwait | United Kingdom |
| EA-059 | Qatar | original_owner | Qatar | United Kingdom |

Original nationality is separate from scenario control. In particular, Azerbaijan is an Iranian territory; Syria is French, and Transjordan/Kuwait/Qatar carry British roundels. The current owner fields should be initialized from dated setup, not blindly overwritten in a running game. Spain’s mixed `Spain`/`Nationalist Spain`/`Republican Spain` original-owner convention is left unresolved pending setup reconciliation.

### Delete false physical connections

Each listed deletion means both directions. These are direct-graph edges, not claims that no multi-zone path exists.

| ID | Connection to delete | Reason |
| --- | --- | --- |
| EA-172 | Eastern Germany ↔ Konigsberg | West Poland lies between them; a railway passing through a third land zone cannot be a direct edge. |
| EA-173 | West Poland ↔ Bohemia | Eastern Germany and Dolnoslaske separate the zones; no shared land boundary. |
| EA-174 | Warsaw ↔ Podlachia | Lubelskie/West Poland lie between Podlachia and the circular Warsaw zone. |
| EA-175 | Southern Norway ↔ Denmark | No printed narrow crossing between Norway and Denmark; ordinary open water is not a land edge. |
| EA-176 | Norrland ↔ Southern Finland | The Gulf of Bothnia separates these zones; the rail route goes through Lapland. |
| EA-177 | Southern Iraq ↔ Transjordan | Northern Iraq and Saudi Arabia separate Southern Iraq from Transjordan. |
| EA-178 | Saudi Arabia ↔ Oman | Aden separates Saudi Arabia from Oman. |
| EA-179 | Qatar ↔ Oman | Aden separates Qatar from Oman. |
| EA-180 | Northern Iraq ↔ Northern Iran | Azerbaijan separates Northern Iraq from Northern Iran. |
| EA-244 | North Western Mediterranean ↔ Strait of Gibraltar (Atlantic) | No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report. |
| EA-245 | Tyrrhenian Sea ↔ Adriatic Sea | No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report. |
| EA-246 | Central Mediterranean Sea ↔ Adriatic Sea | No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report. |
| EA-247 | Adriatic Sea ↔ Western Black Sea | No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report. |
| EA-248 | Eastern Mediterranean ↔ Red Sea | No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report. |
| EA-249 | Eastern Mediterranean ↔ Red Sea South | No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report. |
| EA-250 | Eastern Mediterranean ↔ Western Black Sea | No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report. |
| EA-251 | Eastern Black Sea ↔ Caspian Sea | No printed shared sea boundary. Caspian M12 is inland; Suez is M8–I5; Turkish Straits M7–M10; Gibraltar A44–M2. See complete proposed network in report. |
| EA-367 | Istanbul ↔ Ankara | Akdeniz and Karadeniz lie between these two roundel zones; printed railway crosses them rather than connecting Istanbul directly to Ankara. |
| EA-387 | Red Sea ↔ Red Sea South | The printed zones are separated by I4; prior descriptive sea names misplaced I3 into the Red Sea. |
| EA-388 | Red Sea ↔ Strait of Hormuz | The printed zones are separated by I4; prior descriptive sea names misplaced I3 into the Red Sea. |

### Printed narrow land crossings

These require actual direct crossing edges with the yellow-diamond unit capacity, explicit blocking seas and no invented railway. Existing Crimea–Donets-Kuban must cease being an unrestricted ordinary railway border.

| ID | Crossing | Capacity | Blocking seas proposed |
| --- | --- | --- | --- |
| EA-252 | London ↔ Picardy | 3 | sea_a22, sea_a23 |
| EA-253 | Denmark ↔ Gotaland | 2 | sea_a11, sea_a12 |
| EA-254 | Corsica ↔ Sardinia | 2 | sea_m1, sea_m3 |
| EA-255 | Southern Italy ↔ ita sicily | 2 | sea_m3, sea_m6 |
| EA-256 | Gibraltar ↔ Spanish Morocco | 2 | sea_a44, sea_m2 |
| EA-257 | ita rhodes ↔ Akdeniz | 2 | sea_m7, sea_m9 |
| EA-258 | Eritrea ↔ yemen | 1 | sea_i5 |
| EA-259 | Crimea ↔ Donets-Kuban | 1 | sea_m11 |

Northern Ireland’s printed two-unit crossings to Scotland and Northern England must also be authored when its missing node is added. Precise blocking-sea membership should be checked at the adjacent A4/A17/A6 shore junctions.

### Remove guessed railway flags

The following physical borders remain, but the printed shared border shows no crossing railway. The audit retains boolean rail presence; two drawn tracks do not become two facilities. Several draft negatives were withdrawn after closer tracing (including French Morocco–Spanish Morocco and Ankara–Akdeniz).

| ID | Border: set railway_connection = false in both directions |
| --- | --- |
| EA-198 | Trondelag ↔ Norrland |
| EA-199 | West Poland ↔ Podlachia |
| EA-200 | Warsaw ↔ East Poland |
| EA-201 | Dolnoslaskie ↔ Bohemia |
| EA-202 | Western Algeria ↔ Southern Algeria |
| EA-203 | Northern Algeria ↔ Southern Algeria |
| EA-204 | Tunisia ↔ Tripoli |
| EA-205 | Tripoli ↔ Tripolitania |
| EA-206 | Tripolitania ↔ Cyrenaica |
| EA-207 | Cyrenaica ↔ Tobruk |
| EA-208 | French Sudan ↔ Niger |
| EA-209 | Niger ↔ Chad |
| EA-210 | Chad ↔ Sudan |
| EA-211 | Niger ↔ Nigeria |
| EA-212 | Dahomey ↔ Nigeria |
| EA-213 | Nigeria ↔ Cameroon |
| EA-214 | Cameroon ↔ Oubangui-Chari |
| EA-215 | Oubangui-Chari ↔ Chad |
| EA-216 | Oubangui-Chari ↔ Sudan |
| EA-217 | Cameroon ↔ Belgian Congo |
| EA-218 | Belgian Congo ↔ Oubangui-Chari |
| EA-219 | Belgian Congo ↔ Tanganyika |
| EA-220 | Angola ↔ Southwest Africa |
| EA-221 | Rhodesia ↔ Tanganyika |
| EA-222 | Rhodesia ↔ South Africa |
| EA-223 | Southwest Africa ↔ Bechuanaland |
| EA-224 | Tanganyika ↔ Portuguese East Africa |
| EA-225 | Saudi Arabia ↔ Aden |
| EA-226 | Saudi Arabia ↔ Qatar |
| EA-227 | Southern Iraq ↔ Kuwait |
| EA-228 | Syria ↔ Northern Iraq |
| EA-229 | Eastern Anatolia ↔ Northern Iraq |
| EA-230 | Eastern Anatolia ↔ Azerbaijan |

### Coasts and facilities

The JSON register gives complete replacement coast sets for the specifically reviewed rows, with each set independent from facilities. Major examples: Cyprus belongs to M9; Lazio’s west coast is M3; Akdeniz faces M7/M9 rather than the Black Sea; Transjordan faces M8; Madagascar faces I1/I2/I3; Gulf of Guinea coasts face A51, not A38. Source details and uncertainty records take precedence over a starter coast list.

The **6 October fresh naval re-audit supersedes every earlier facility proposal**. Its [source-verified naval ledger](../data/naval_reaudit_europe_africa_middle_east.json) covers **127 territories, 110 distinct physical symbols and 39 inspected empty rosters**. It checks ports, dockyards, shipyards, seaplane bases and submarine bases independently from coast membership; every row has source evidence, including empty rosters. Iceland/Faroe/Shetland are covered by Americas/Atlantic and Kola/eastern Soviet territories by Asia/Pacific.

French Morocco and Southwest Africa have **no port**. Angola, Basque Country, Macedonia, Bessarabia, Southern Iraq, Upper Egypt, Corsica, Sardinia, Qatar and Oman also have no printed naval facility. Their unsupported stored claims must be deleted, not assigned new IDs. A railway reaching a coast and a territory having sea access do not establish a naval facility.

Key corrected assignments are the North-Caucasia M11 seaplane base (previously assigned to Donets-Kuban), the Transcaucasia M11 minor port, and the Karelia A9 minor port west of the Northern Russia boundary. Kalmytskaya has an omitted M12 minor port. Western Germany has two major shipyards plus separate seaplane and submarine bases; Eastern Germany’s A12 symbol is a major shipyard. Cape Town and Ascension show white circled-anchor **minor dockyards**; the Cape Town map symbol conflicts with the rulebook p16 supply example’s wording, which is documented in the ledger rather than concealed.

One physical instance retains one ID across its verified sea accesses: Scotland’s northern major port A4/A6, London’s major shipyard A22/A23, Helsinki’s minor shipyard A13/A14, Gibraltar’s major dockyard A44/M2, Peloponnese’s minor port M6/M7 and Tobruk’s minor port M4/M8. Separate icons in Northern Italy, Scotland, Southern England, Western Germany, Istanbul and Transcaucasia have separate IDs. Southern Italy’s minor shipyard faces M3; no additional M5/M6 facility is printed.

Existing facility findings retain their IDs with corrected values/categories. Empty-coast confirmations are explicitly marked as confirmations, never facility additions. New complete physical-instance inventories EA-561–EA-662 make old invalid type/access claims and their replacements reviewable.

| ID | Territory | Current seas | Proposed seas |
| --- | --- | --- | --- |
| EA-260 | Corsica | sea_m3 | sea_m1, sea_m3 |
| EA-261 | Sardinia | sea_m3 | sea_m1, sea_m3 |
| EA-262 | Northern Italy | sea_m3 | sea_m3, sea_m5 |
| EA-263 | Rome | sea_m3 | sea_m3, sea_m5 |
| EA-264 | Lazio | sea_m4 | sea_m3, sea_m5 |
| EA-265 | Southern Italy | sea_m4, sea_m5 | sea_m3, sea_m5, sea_m6 |
| EA-266 | Macedonia | sea_m5 | sea_m7 |
| EA-267 | Thessaly | none | sea_m6, sea_m7 |
| EA-268 | Istanbul | sea_m10 | sea_m10, sea_m7 |
| EA-269 | Akdeniz | sea_m11 | sea_m7, sea_m9 |
| EA-270 | Eastern Anatolia | none | sea_m11 |
| EA-271 | Cyprus | none | sea_m9 |
| EA-272 | Transjordan | sea_m9 | sea_m8 |
| EA-273 | Central Romania | none | sea_m10 |
| EA-274 | Southern Ukraine | none | sea_m10 |
| EA-275 | Crimea | sea_m10, sea_m11 | sea_m11 |
| EA-276 | Donets-Kuban | none | sea_m11 |
| EA-277 | North-Caucasia | sea_m11 | sea_m11, sea_m12 |
| EA-278 | Northern Iran | none | sea_m12 |
| EA-279 | Tripolitania | none | sea_m4 |
| EA-280 | Cyrenaica | none | sea_m4 |
| EA-281 | Tobruk | sea_m8, sea_m9 | sea_m4, sea_m8 |
| EA-282 | Western Egypt | sea_m9 | sea_m8 |
| EA-283 | Lower Egypt | sea_i5, sea_m9 | sea_i5, sea_m8 |
| EA-284 | Nubia | none | sea_i5 |
| EA-285 | French Somaliland | sea_i5 | sea_i4 |
| EA-286 | Italian Somaliland | sea_i4 | sea_i3, sea_i4 |
| EA-287 | Tanganyika | sea_i4 | sea_i3 |
| EA-288 | Portuguese East Africa | sea_i4 | sea_i1 |
| EA-289 | South Africa | sea_a40 | sea_i1 |
| EA-290 | Madagascar | sea_i4 | sea_i1, sea_i2, sea_i3 |
| EA-291 | Mauritius | sea_i4 | sea_i2 |
| EA-292 | Seychelles | sea_i4 | sea_i3 |
| EA-293 | Saudi Arabia | sea_i3, sea_i6 | sea_i5, sea_i6 |
| EA-294 | Aden | sea_i3 | sea_i4 |
| EA-295 | Qatar | sea_i7 | sea_i6 |
| EA-296 | Kuwait | sea_i7 | sea_i6 |
| EA-297 | Southern Iraq | sea_i7 | sea_i6 |
| EA-298 | Southern Iran | sea_i6, sea_i7 | sea_i6 |
| EA-369 | French Morocco | sea_a28 | sea_a44 |
| EA-370 | Spanish Morocco | sea_a28 | sea_a44, sea_m2 |
| EA-371 | Dahomey | sea_a38 | sea_a51 |
| EA-372 | Nigeria | sea_a38 | sea_a51 |
| EA-373 | Cameroon | sea_a38 | sea_a51 |
| EA-374 | Southwest Africa | sea_a39 | sea_a53, sea_a54 |
| EA-375 | Cape Town | sea_a40 | sea_a54, sea_i1 |
| EA-376 | Aquitaine | sea_a28 | sea_a29 |
| EA-377 | Southern France | sea_a28, sea_m1 | sea_m1 |
| EA-398 | Southern Norway | sea_a10, sea_a6 | sea_a10, sea_a7 |
| EA-399 | Trondelag | sea_a6 | sea_a5, sea_a7 |
| EA-400 | Norrland | sea_a14 | sea_a13 |
| EA-401 | Gotaland | sea_a12, sea_a13 | sea_a10, sea_a12, sea_a13 |
| EA-402 | Southern Finland | sea_a13 | sea_a13, sea_a14 |
| EA-403 | Viipuri Province | none | sea_a14 |
| EA-404 | Estonia | sea_a12, sea_a13 | sea_a14 |
| EA-405 | Latvia | none | sea_a12, sea_a14 |
| EA-406 | Lithuania | none | sea_a12 |
| EA-407 | West Poland | none | sea_a12 |
| EA-408 | Denmark | sea_a10, sea_a12, sea_a23 | sea_a10, sea_a11, sea_a12 |
| EA-409 | Western Germany | sea_a12, sea_a23 | sea_a11, sea_a12 |
| EA-410 | Netherlands | sea_a23 | sea_a11, sea_a23 |
| EA-411 | Leningrad | sea_a12 | sea_a14 |
| EA-428 | Oman | sea_i6 | sea_i4, sea_i6, sea_i7 |

### Directional terrain and rivers

The machine register includes the glossary’s exact incoming boundary corrections. Examples: Picardy → Belgium is a mountain border; Belgium → Netherlands crosses a river; Northern England has mountain entry from Scotland/A17 despite normal roundel terrain; Southern Finland has marsh entry from Viipuri/A14; Lower Egypt has river entry from Transjordan, Western Egypt and M8; Eastern Anatolia has river entry from its listed neighbors and M11. These should not be mirrored automatically.

For missing physical boundaries identified by the glossary, `incoming_edges` specifies only the expressly supported incoming effect. Add reciprocal physical adjacency after validating the endpoints, then author reverse terrain, reverse combat crossing, rail and river route separately. A combat crossing does not establish `has_river`, and the inverse is also false.

## Uncertain / still requiring decisions

- **EA-363 — Field-specific limits after second pass.** The blanket fine-topology deferral has been replaced by the explicit pair ledger. Field coverage follows each pair’s checked_fields; river-route, facility and gauge coverage is never implied by physical adjacency.
- **EA-364 — Impassable Sahara and Pripet boundary routing.** Author map-relative passability per crossing, preserving the distinction between physical adjacency and legal ground traversal. Do not delete all touching territories or set entire mixed zones impassable. Shaded Sahara/Pripet areas cover parts of multiple named territories. Shortest within-two-zones route must be checked for each candidate border; rail lines across Pripet require explicit source/rules reconciliation, not automatic assumption.
- **EA-365 — Spain original nationality versus civil-war setup.** Use a consistent static Spanish identity and dated Nationalist/Republican setup allocation; verify setup sheet before changing faction ownership. Current mix of Spain, Nationalist Spain and Republican Spain is inconsistent. Printed flags and the 1936 civil-war setup are not interchangeable with national identity.
- **EA-366 — Karelia river-table wording.** incoming_true_from: Northern Russia, Western Russia, Leningrad; reverse_edges: verify map Glossary says River Border with, whereas most rows say from. Trace both sides of each river; do not mechanically set both directions.
- **EA-426/427 resolved in the second pass.** Scotland A4/A6/A17; Northern England A6/A17; Southern England A17/A21/A22/A23; London A22/A23; Ireland A17; Lapland A8/A13. Helsinki A13/A14; Crete M7/M8; Rhodes M7; Sicily M3/M4/M6; Iceland A3/A4; Faroe A4; Shetland A6. Positive shoreline segments determine access.

Remaining interpretive limits are explicit per pair: the Lubelskie–Western Ukraine junction, dense railway junctions, and mixed-zone impassable routes. Reciprocal navigable river semantics and gauge attributes must follow the source-backed schema proposals rather than inheriting the old heuristic defaults. Naval facility identities and sea access now have a fresh, separate source-verified roster.

## Mechanism placement

This region especially needs static map geography for controlled sea passages, printed crossing capacity/blocking seas, combined roundel terrain, separate physical port instances and river routes. It also exposes the need for named strategic rail regions and printed gauge boundaries. Those schema proposals are centralized in [mechanisms_and_schema.md](../mechanisms_and_schema.md). Current owners, rail/port damage, current canal permission, temporary movement restrictions, Spanish civil-war assignment and nation-specific abilities belong in scenario/rules/state layers. Kamikaze eligibility is not proposed as a generic tile field.
