# Sources, method and interpretation

Audit date: **5 October 2026**. Scope: the entire printed world, including all
continents, seas and edge-wrap areas; not the Japan–China campaign projection.

## Source hierarchy

1. `game_content/maps/gw36map.png`: original 9900 × 4888 board image. Crops are
   diagnostic views of these pixels; none are generated illustrations.
2. `game_content/rules/Global War 1936 v4.3 Rulebook.pdf`: mechanics and explicit
   lists, including victory cities, controlling canal zones and special routes.
3. `game_content/rules/GW1936_Terrain_Glossary_v1.pdf`: per-zone intrinsic and
   directed approach terrain. Where a spelling, diagram or entry disagrees with
   the board/rulebook, record the disagreement; do not silently “correct” the
   board from a guessed interpretation.
4. Local national reference sheets and neutral setup chart: distinguish national
   identity/control and setup pieces from printed map infrastructure. This audit
   is not a new global starting-unit transcription.
5. Earlier local audits and explicit project rulings: retain provenance and mark
   inherited decisions. In particular, preserve user-approved Canadian seam links
   and the user's warlord names. Campaign exclusions do not delete world tiles.

[input_manifest.json](data/input_manifest.json) records hashes and sizes of the
map, source image, generators, home-country file and local PDFs. The board's
printed version and v4.3 rules/glossary are not presumed perfectly identical.
No online map or generic real-world geography was substituted for the game board.

## Naval-facility revision, 6 October 2026

The initial audit's generic ID-collision examples did not reliably reconcile
which ports actually exist. The naval-facility review therefore rechecks the
printed symbols, the territory containing each symbol, the minor/major and
facility-type distinctions, and the accessible sea zones. It includes current
facility claims, proposed additions and explicit empty results. A coast, railway,
settlement name or convoy endpoint is not evidence of a naval facility.

[The corrected roster](naval_facility_reaudit.md) is generated from three
source-authored regional naval ledgers. Each facility is a physical instance;
multiple accesses do not create extra instances, and separate symbols are not
merged just because they share a type or territory. Ambiguous symbol ownership
or access remains explicit. The comparison script validates references and
coverage, but the source-image review establishes geographic correctness.

## Review dimensions

For each stored tile the audit inventory includes ID/name, type, terrain, IPP,
original/current owner, city/capital/victory flags, intrinsic facilities and both
land/sea neighbor lists. Every directed edge is inventoried with approach terrain,
passability, combat river crossing, river-route flag, rail/gauge, naval facilities,
canal/strait and narrow crossing information.

The regional reviews additionally examine the printed source for **missing**
tiles. An inventory of the existing JSON alone cannot establish completeness.
New tile IDs in proposals are suggestions, pending identity reconciliation.
A named settlement dot inside a territory is not automatically a new land zone.
Use printed zone boundaries and the rulebook's circular/semi-circular city-zone
definition; do not add a new tile merely for a label such as Nagasaki or Vladivostok.

The review files distinguish:

- **Add:** a source feature or field is missing. A confirmed new tile can still
  have unresolved borders; the row's notes state that dependency.
- **Change:** an existing fact differs from the cited source, or a schema change
  is proposed to express a rule-relevant physical feature.
- **Delete:** an invented/incorrect connection, duplicated identity or obsolete
  attribute should be removed. Removing a rail does not necessarily remove the
  physical land adjacency; removing a port does not remove the coast.
- **Uncertain:** the source is ambiguous, sources disagree, or the detailed
  feature has not yet been fully traced. The ledger distinguishes ambiguity
  from work still needing source verification. Neither is approved as a patch.

`high` confidence applies only to the particular stated fields. It never means
that all other fields of the affected tile are certified. A group finding can
contain many proposed field edits, so finding counts are not tile or edit counts.

## Coverage and limits

The automated pass exhaustively covers the **stored** graph. The geographic
passes cover all world regions, give every stored pair a source-review outcome,
and provide neighbor proposals for the missing land identities. Existing-node
review scope is listed separately. Some directional attributes, dense railway
junctions, river-bank routes and small border contacts remain unresolved where
recorded. These are explicit limitations, not default-false geography or an
endorsement of current values. Printed exceptional-route arrows such as A9–P1
do not create unrestricted ordinary sea adjacency.

Neither a successful regeneration nor an old regression test demonstrates that
a printed boundary is correct. A pair of reciprocal wrong edges still passes
symmetry checks. No new map/engine/campaign data is applied by these reports.

## Root-review crop rectangles

Coordinates are `(left, top, right, bottom)` in the original PNG. Regional review
files record their own rectangles. Crops are saved without geometric modification;
some root crops use high-quality JPEG for manageable report size. Re-crop from
the original PNG for a pixel-level ambiguity.

| Evidence filename | Rectangle |
|---|---|
| `root_atlantic_north.jpg` | (1050, 500, 2700, 2100) |
| `root_atlantic_middle.jpg` | (1050, 2050, 2850, 3600) |
| `root_atlantic_south.jpg` | (1050, 3550, 3300, 4888) |
| `root_indian_ocean.jpg` | (4600, 2800, 6500, 4650) |
| `root_pacific_east.jpg` | (8050, 2050, 9850, 3550) |
| `root_legend.jpg` | (8650, 4500, 9900, 4888) |
| `root_convoy_caribbean.jpg` | (0, 1700, 1300, 3500) |
| `root_convoy_arctic.jpg` | (1700, 0, 4600, 950) |
| `root_convoy_med.jpg` | (2650, 2150, 4750, 3250) |
| `root_convoy_far_east.jpg` | (6450, 2550, 8400, 3850) |
| `root_convoy_south_africa.jpg` | (3100, 3650, 5150, 4888) |
| `root_convoy_brazil.jpg` | (350, 2900, 1800, 4450) |
| `root_convoy_baltic.jpg` | (3500, 400, 4500, 1650) |
| `root_convoy_baltic_line.jpg` | (2950, 600, 3950, 1900) |
| `root_convoy_western_pacific.jpg` | (7200, 800, 9650, 2850) |
| `root_convoy_north_sea_full.jpg` | (2450, 0, 3650, 1900) |
| `root_convoy_baltic_full.jpg` | (3000, 350, 4070, 1530) |
| `root_convoy_italy_detail.jpg` | (3000, 1870, 3520, 2800) |
| `root_convoy_canada_start.jpg` | (850, 1190, 1460, 1670) |
| `root_convoy_aden_detail.jpg` | (4800, 3500, 5360, 3890) |
| `root_convoy_suez_full.jpg` | (4450, 3000, 5100, 3920) |
| `root_convoy_singapore.jpg` | (6320, 2800, 6920, 3500) |
| `root_convoy_australia_end.jpg` | (7470, 3590, 8390, 4320) |
| `root_convoy_kola_end.jpg` | (3740, 0, 4560, 380) |
| `root_convoy_atlantic_27_28.jpg` | (1590, 1560, 1940, 2060) |
| `root_convoy_sydney_end.jpg` | (7790, 4100, 8630, 4888) |
| `root_convoy_soviet_start.jpg` | (1680, 0, 2780, 1520) |
| `root_convoy_north_atlantic_start.jpg` | (600, 1360, 1390, 2160) |
| `root_convoy_manila_west_end.jpg` | (6840, 2950, 7350, 3330) |
| `root_convoy_manila_35_45_43.jpg` | (7100, 2490, 8490, 3170) |
| `root_convoy_manila_sf.jpg` | (9130, 1690, 9900, 2250) |
| `root_convoy_east_asian_java.jpg` | (6500, 3350, 7590, 3860) |

Rulebook pages 8, 15, 20, 74 and 98 were rendered for visual inspection in the
temporary audit directory; other relevant pages were searched/extracted from
the same local PDF. Terrain-table visual interpretation is documented regionally.
