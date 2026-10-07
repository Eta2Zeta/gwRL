# Reconcile overlapping proposals before applying them

The register preserves each regional review's source evidence. Its findings are
not independent JSON patches and must not be applied blindly in ID order.

## Duplicate missing-zone observations

| Physical zone | Findings | Canonical proposal |
|---|---|---|
| Iceland | AM-086, EA-062 | One `land_iceland` node; merge the complementary terrain/identity evidence. The second pass confirms A3/A4 coasts; EA-427 now records that resolution. |
| Faroe Islands | AM-087, EA-063 | One `land_faroe_islands` node, with the source-supported terrain and A4 coast. |
| Shetland Islands | AM-088, EA-061 | One node. Prefer `land_shetland_islands`; treat EA's suggested `land_gbr_shetland_islands` as an alias during review, not another tile. |

New IDs are suggestions. Existing IDs are preserved unless a source identity
requires a split or explicit rename migration. `land_hispaniola` is an example of
an incorrect aggregate that should be replaced by Haiti and Dominican Republic;
that replacement must update every old reference.

## Precedence between related edits

1. **Identity/topology first.** A proposed edge deletion takes precedence over a
   terrain, port or rail correction on that false edge. Do not normalize a false
   sea shortcut to `border_terrain: sea` and retain it.
2. **Exact fields only.** A proposal confirming an island's existence, roundel and
   IPP does not approve default terrain, railways, coasts or facilities. Preserve
   the explicitly unverified fields from its review row.
3. **One physical facility per instance.** After correcting actual type and access,
   repair colliding IDs. Do not rename phantom ports into apparently validated
   facilities. Multiple accesses can reference one physical port; two same-type
   shipyards can be genuinely separate instances.
4. **Candidate sets stay candidates.** Where a complete coast/sea-neighbor set is
   marked uncertain, do not apply it as a replacement and delete other shores.
   A confirmed individual contact can be added independently if its other fields
   are also justified.
5. **Directional glossary entries do not create generic terrain rules.** Preserve
   explicit source→destination direction and mixed terrain. Do not infer river
   transport continuity from a combat penalty or overwrite the reverse direction.
6. **Preserve adopted rulings.** User-approved Canadian edge-wrap links, warlord
   names and the separately reviewed Abyssinia approaches remain explicit project
   constraints. New source disagreements are uncertainties for review.
7. **Full world versus scenario.** Retain Hong Kong, FEC-related geography, Soviet
   territory and world convoy features here. The current campaign's exclusions
   belong in its manifest/profile and do not delete world-map facts.
8. **Sea names use printed IDs.** AP-082 and WG-013 propose canonical names such
   as `Sea Zone I1`. EA's geographic descriptions of I1–I5 are useful optional
   aliases, not competing replacements for the printed zone identities.

## Scope references

- Global victory-city flag changes are in WG-006–WG-012. Sydney's new node is
  AP-036. Do not add Sydney merely as a city flag on New South Wales.
- A5/A8/A9 missing sea identities are WG-032–WG-034; regional coast proposals
  reference those nodes before they currently exist.
- WG-001's 93 terrain normalizations are a representation cleanup conditional on
  final topology. They overlap many regional sea repairs.
- Source-derived river/terrain tables supplement the broad regional records;
  every row needs to be read with its field scope, missing-edge status and source
  ambiguity. Tables do not certify all nonlisted approaches as normal/false.
- Convoy labels and complete paths have separate confidence. The printed ANZAC
  route is **East Asian Line**; the old campaign audit called it East Indies Line.
  The new register corrects the label without modifying that historical artifact.

## Port clarification — 6 October 2026

WG-003 and WG-004 now reconcile the original ID-collision diagnostics with actual
facility existence, type and access. Their previous territory-to-minor-port-ID
examples must not be applied. The user confirmed that French Morocco has no port;
the map crop agrees. Remove its fictitious port rather than rename it. EA-328–331
already distinguish the three printed Egyptian facilities and remove the Upper
Egypt port claim. WG-004 repeats that final roster for clarity, not as extra
additions. In particular, the two Lower Egypt facilities have separate IDs.

The subsequent full naval recheck also replaces WG-002 and WG-005 with concrete
facility/type/access proposals. Southwest Africa has no printed port; South Africa
has a major port on I1. The [corrected naval roster](naval_facility_reaudit.md)
covers all current and proposed facility-bearing territories and supplies explicit
empty inventories. Its physical IDs and accesses were cross-checked against the
revised finding records. The Philippine port's territory assignment and the Cape
Town board-versus-rulebook type conflict remain explicit uncertainties; they must
not be resolved by falling back to the old map's generic minor-port entries.

## Remaining full-detail verification

The whole world is covered by geographic review regions, every stored record
has an inventory row, and every stored physical pair has a source-review outcome.
The second pass also provides neighbor proposals for newly discovered land zones.
Remaining small junction ambiguities, directional-attribute limitations and
river-bank transport modeling are explicit in `review_coverage.json`,
`edge_review_coverage.json`, the regional new-node tables and the uncertain
register. Treat missing verification as unknown rather than as evidence that
the current value is correct.
