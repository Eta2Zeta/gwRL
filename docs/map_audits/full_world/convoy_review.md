# Full-world convoy layer review

The current world JSON has no convoy records. This audit proposes **16 printed
routes**, including the two Japanese routes previously documented for M0.
Thirteen routes have now been traced end to end against the original image.
Manila's entire sea path is traced, with its Philippine land endpoint unresolved;
the Japanese pair retains the earlier complete audit's provenance. Production
map and campaign data are unchanged.

## Data proposal

One record per physical line: stable identity, printed label, beneficiary roundel,
printed maximum loss, typed land/sea endpoints, ordered sea path and source
references. A terminal arc is a **sea endpoint**, even if close to a port. Lines
meeting at adjacent arcs remain separate records. The machine-readable register
uses proposed lower-case beneficiary keys; map them to the eventual canonical
nation profiles rather than assuming they are existing engine IDs.

Do not make blue loss caps into income or duplicate a cap on every sea tile.
Land-endpoint closure and the shared per-Player-Turn loss account are rules/runtime
state (rulebook §1.5 p10; §10.9 pp71–72). Rectangular flags are wartime bonus
references, not additional route owners or cap values.

## Source-traced geographic proposals

Sea order follows the listed endpoints. Reversing the entire record describes
the same geographic route; this table does not impose one-way movement.

| Printed route | Beneficiary / printed cap | Endpoints | Ordered seas |
|---|---|---|---|

| Europe-America Line | britain / 5 | Nova Scotia ↔ Southern England | A18 → A19 → A20 → A21 |
| Atlantic Line | britain / 6 | Southern England ↔ A44 sea arc | A21 → A28 → A27 → A35 → A44 |
| Mediterranean Line | britain / 6 | A44 sea arc ↔ M8 sea arc | A44 → M2 → M4 → M8 |
| West African Line | britain / 3 | A44 sea arc ↔ A54 sea arc | A44 → A46 → A48 → A50 → A51 → A53 → A54 |
| East African Line | britain / 1 | A54 sea arc ↔ I4 sea arc | A54 → I1 → I3 → I4 |
| Indian Ocean Line | fec / 1 | I5 sea arc ↔ P50 sea arc | I5 → I4 → I7 → I12 → P50 |
| East Asian Line | anzac / 2 | P50 sea arc ↔ New South Wales | P50 → P59 → P60 → P62 → P63 → P64 → P71 → P72 |
| Caribbean Line | usa / 2 | Texas ↔ A37 sea arc | A36 → A37 |
| Lend Lease to Britain Line | usa / 3 | New York ↔ Rio de Janeiro | A25 → A30 → A37 → A41 → A42 → A45 → A47 |
| North Sea Line | germany / 2 | Western Germany ↔ Northern Norway (Narvik) | A11 → A10 → A7 → A5 → A8 |
| Baltic Line | germany / 3 | Eastern Germany ↔ Norrland | A12 → A13 |
| Liguria-Tripoli Line | italy / 1 | Lazio ↔ Tripoli | M3 → M2 → M4 |
| Soviet Arctic Line | ussr / no number printed | A20 sea arc ↔ Kola | A20 → A17 → A4 → A6 → A5 → A8 |
| Manila Line | usa / 3 | San Francisco ↔ Philippine major port (land assignment unresolved) | P25 → P24 → P29 → P37 → P36 → P35 → P45 → P43 → P42 → P51 → P50 |
| Nagasaki Line | japan / 5 | Rehe ↔ Kyushu | P14 → P15 |
| Tokyo Line | japan / 5 | Tokyo ↔ P50 sea arc | P16 → P34 → P33 → P32 → P41 → P50 |

## Details that prevent incorrect shortcuts

### CV-01 — Europe-America Line

Nova Scotia port to Southern England port; the land endpoints are not Canada/UK sea arcs.

Evidence: [root_convoy_canada_start.jpg](evidence/root_convoy_canada_start.jpg), [root_atlantic_north.jpg](evidence/root_atlantic_north.jpg).

### CV-02 — Atlantic Line

The diagonal crosses A28 into the narrow southern extension of A27 before A35; do not shortcut A27.

Evidence: [root_atlantic_north.jpg](evidence/root_atlantic_north.jpg), [root_convoy_atlantic_27_28.jpg](evidence/root_convoy_atlantic_27_28.jpg), [root_atlantic_middle.jpg](evidence/root_atlantic_middle.jpg).

### CV-03 — Mediterranean Line

Both ends have sea-terminal arcs. The M8 arc is just above the Lower Egypt dockyard; it does not make this a land endpoint.

Evidence: [root_atlantic_middle.jpg](evidence/root_atlantic_middle.jpg), [root_convoy_med.jpg](evidence/root_convoy_med.jpg).

### CV-04 — West African Line

Separate sea-terminal arcs at the Gibraltar-side junction and Cape Town-side junction.

Evidence: [root_atlantic_middle.jpg](evidence/root_atlantic_middle.jpg), [root_atlantic_south.jpg](evidence/root_atlantic_south.jpg), [root_convoy_south_africa.jpg](evidence/root_convoy_south_africa.jpg).

### CV-05 — East African Line

Passes west of Madagascar through I1/I3. The I4 terminal arc adjoins the continuing Indian Ocean Line off Aden.

Evidence: [root_convoy_south_africa.jpg](evidence/root_convoy_south_africa.jpg), [root_indian_ocean.jpg](evidence/root_indian_ocean.jpg), [root_convoy_aden_detail.jpg](evidence/root_convoy_aden_detail.jpg).

### CV-06 — Indian Ocean Line

Starts at a Red Sea arc in I5 below Lower Egypt, continues past the East African terminal in I4, and ends at its own Singapore-side P50 arc. It does not enter I11.

Evidence: [root_convoy_suez_full.jpg](evidence/root_convoy_suez_full.jpg), [root_convoy_aden_detail.jpg](evidence/root_convoy_aden_detail.jpg), [root_indian_ocean.jpg](evidence/root_indian_ocean.jpg), [root_convoy_singapore.jpg](evidence/root_convoy_singapore.jpg).

### CV-07 — East Asian Line

Printed name East Asian Line. Southern land endpoint is the New South Wales shipyard north of the separate Sydney city boundary. UK rectangular flag is a separate bonus reference.

Evidence: [root_convoy_singapore.jpg](evidence/root_convoy_singapore.jpg), [root_convoy_east_asian_java.jpg](evidence/root_convoy_east_asian_java.jpg), [root_convoy_far_east.jpg](evidence/root_convoy_far_east.jpg), [root_convoy_australia_end.jpg](evidence/root_convoy_australia_end.jpg), [root_convoy_sydney_end.jpg](evidence/root_convoy_sydney_end.jpg).

### CV-08 — Caribbean Line

Texas facility land endpoint; terminal arc in A37 southeast of Bahamas. A37 is absent from current JSON; this is not executable current-map data.

Evidence: [root_convoy_caribbean.jpg](evidence/root_convoy_caribbean.jpg).

### CV-09 — Lend Lease to Britain Line

New York to Rio de Janeiro. The line begins in A25 and passes west of A38 in A37/A41; it does not traverse A38 or A49.

Evidence: [root_convoy_north_atlantic_start.jpg](evidence/root_convoy_north_atlantic_start.jpg), [root_convoy_caribbean.jpg](evidence/root_convoy_caribbean.jpg), [root_convoy_brazil.jpg](evidence/root_convoy_brazil.jpg).

### CV-10 — North Sea Line

Western Germany's A11 major shipyard to Narvik in Northern Norway. The northern stretch is A5/A8, not A6 or A9. The 6 October facility recheck corrects the earlier “major port” wording: the German endpoint symbol is a crane.

Evidence: [root_convoy_north_sea_full.jpg](evidence/root_convoy_north_sea_full.jpg), [root_convoy_arctic.jpg](evidence/root_convoy_arctic.jpg).

### CV-11 — Baltic Line

The dashed line stays west of the curved A14 border throughout; A14 is not part of the Baltic Line.

Evidence: [root_convoy_baltic_full.jpg](evidence/root_convoy_baltic_full.jpg).

### CV-12 — Liguria-Tripoli Line

Despite its printed Liguria-Tripoli label, the northern facility lies on Lazio. The curve west of Sicily briefly crosses M2 between M3 and M4.

Evidence: [root_convoy_italy_detail.jpg](evidence/root_convoy_italy_detail.jpg), [root_convoy_med.jpg](evidence/root_convoy_med.jpg).

### CV-13 — Soviet Arctic Line

The sea arc is in A20; the curve west of Shetland passes through A6 before A5. Kola endpoint is its A8 minor shipyard. No numeric raid cap is printed. USSR NRS p2 separately gives a conditional +2 wartime bonus; do not use that as a raid cap.

Evidence: [root_convoy_soviet_start.jpg](evidence/root_convoy_soviet_start.jpg), [root_convoy_arctic.jpg](evidence/root_convoy_arctic.jpg), [root_convoy_north_sea_full.jpg](evidence/root_convoy_north_sea_full.jpg), [root_convoy_kola_end.jpg](evidence/root_convoy_kola_end.jpg).

### CV-14 — Manila Line

Entire sea path is traced, including P45 and the P51→P50 Philippine bend. The white-anchor-on-blue terminal is a major port, not a dockyard. It is drawn on the western Visayas island cluster; assignment to Luzon and the Visayas versus Mindanao is unresolved in the source interpretation. Do not infer the endpoint from the Manila label or proximity to the Mindanao label. Do not import as a complete usable route until the endpoint is resolved.

Evidence: [root_convoy_manila_sf.jpg](evidence/root_convoy_manila_sf.jpg), [root_convoy_western_pacific.jpg](evidence/root_convoy_western_pacific.jpg), [root_pacific_east.jpg](evidence/root_pacific_east.jpg), [root_convoy_manila_35_45_43.jpg](evidence/root_convoy_manila_35_45_43.jpg), [root_convoy_far_east.jpg](evidence/root_convoy_far_east.jpg), [root_convoy_manila_west_end.jpg](evidence/root_convoy_manila_west_end.jpg).

### CV-15 — Nagasaki Line

Prior fully traced source record; still absent from production world map.

Evidence: [convoy_audit.json](../../../game_content/scenarios/japan_china_1936/m0/convoy_audit.json).

### CV-16 — Tokyo Line

Prior fully traced source record; still absent from production world map.

Evidence: [convoy_audit.json](../../../game_content/scenarios/japan_china_1936/m0/convoy_audit.json).

## Implementation and remaining rule work

The [machine-readable register](data/convoy_register.json) contains the full
geographic proposal for every row, retaining Manila's unresolved endpoint. Missing
sea IDs and corrected contacts must
be implemented before these routes can validate against the world graph. See
WG-019–WG-030 and WG-035–WG-037 in the additions register; WG-031 remains
in the uncertain register.

The Soviet Arctic line has **no printed numeric loss cap**. This is a source
observation, not a zero or an unlimited cap. USSR NRS p2 gives a separate
conditional **+2 wartime bonus** for a clear line and Soviet possession of Kola;
store that predicate in the USSR rules profile. Its raiding treatment should
follow the applicable rule profile rather than borrowing the bonus value.

Keep route closure, escorts, current losses, permissions and bonus activation
outside immutable geography. Apply campaign filtering deliberately and do not
join retained fragments across excluded seas.

As a cross-check, A44 contains the Atlantic, Mediterranean and West African
lines with caps **6 + 6 + 3 = 15**, matching the explicit A44 example in rulebook
§10.9 p72.

Evidence crops derive from the original 9900 × 4888 image; rectangles are in
[source_method.md](source_method.md). The route roster reflects this board source
and is not a claim about expansions or other map editions.
