# World-map implementation — 7 October 2026

The approved map changes are implemented. The checkpoint before implementation
is [`eeb5e90`](https://github.com/Eta2Zeta/gwRL/commit/eeb5e9028d0f9efde087b3009d7f9613ce92f958).
Images are ignored by Git and remain local. The original proposal registers and
their before-values are retained for review; they describe that checkpoint.

## What changed

| Data | Implemented result |
|---|---|
| Tiles | 539: 381 land and 158 sea. Added 79 land identities and 54 seas; retired the incorrect Hispaniola aggregate in favor of Haiti and Dominican Republic. |
| Connections | 1,400 reciprocal physical connections, with no isolated tiles. Removed reviewed shortcuts, restored borders and coasts, and retained seven uncertain existing pairs. |
| Terrain and income | Applied the reviewed intrinsic and directional corrections, including simultaneous terrains, IPP values and the ten victory cities. Previously adopted Canadian and China-theatre directions remain explicit. |
| Facilities | Canonical registry of 207 resolved naval facilities and 36 airfields. Each physical facility has its own identity and verified accesses; edge arrays project the registry. |
| Convoys | 15 complete routes with ordered seas, resolved endpoints, beneficiary and one line-level loss cap. The unresolved Manila line is withheld. |
| Passages and special routes | Eight typed canals/straits and four exceptional routes. Northern Sea Route and Baltic–White Sea transit do not become ordinary sea adjacencies. |
| Narrow crossings | 23 complete crossing records with unit capacity and blocking seas. Two Northern Ireland crossings retain their reviewed physical connection/capacity but lack a certified blocker list. |
| Restrictions | Queensland approaches from P64, P71 and P72 prohibit amphibious assault while retaining the coasts. |
| Rail gauges | Removed the original-owner heuristic. Transitions use reviewed gauges on both sides; unreviewed gauges are `null`. Sweden–Finland is a transition; the actual Viipuri–Leningrad railway is broad on both sides. |
| Home Country and campaign | Corrected mainland USA membership and regenerated the nation index and existing 38-tile campaign projection. Geographic data does not activate new campaign gameplay. |

Lower Egypt now has a major dockyard on M8 and a separate major port on I5.
Western Egypt has its own M8 major port; Upper Egypt, French Morocco and
Southwest Africa have none. Nanking remains one physical port with two accesses,
while Honshu's two shipyards remain separate. Redundant IDs such as Cuba's
`facility_cuba_major_port_map_1` are simplified to `facility_cuba_major_port`.

## Files to use

- [World map](../../../game_content/maps/gw36_manual_map.json): generated schema 2 geography and feature layers.
- [Authoring inputs](../../../game_content/maps/authoring/README.md): editable, explicit reviewed facts and their sources.
- [Review sidecar](../../../game_content/maps/gw36_manual_map_review.json): field-level sources, retained project decisions, unresolved facility alternatives and the disposition of every finding.
- [Geographic rules profile](../../../game_content/rules/map_geography_rules.json): rule definitions, capacities and fortification coverage, separate from static tiles. Kamikaze rules stay outside the core map.
- [Home Country index](../../../game_content/maps/gw36_nation_home_country.json) and [campaign projection](../../../game_content/scenarios/japan_china_1936/map.json).

The 1,051 finding records overlap: **862 implemented, 164 superseded by reconciled
records, and 25 deferred**. These are finding statuses, not independent edit
counts. Some implemented findings contain smaller deferred fields; the following
limits and the source ledgers remain applicable.

## What remains for your review

The [uncertain register](uncertain.md) remains open. No alternative was selected
for unresolved ownership, seam contacts, river-network interpretation, Cape Town's
facility type, or the Philippine port's territory. The Cape Town and Philippine
coasts expose a partial inventory; a `null` facility-presence flag means unknown,
not a confirmed absence. The raw claims and alternatives remain in the sidecar.

Nested uncertainties are also withheld: Saratov–Ural rail, Peloponnese–Thessaly
rail, Ivory Coast–French Sudan rail, the Turkmenistan–Sinkiang impassable-contact
representation, and proposed unconfirmed point contacts. Four new British Pacific
islands retain unknown player allocation rather than an inferred FEC owner.
Azores and Greenland retain unknown intrinsic terrain because the approved
addition records did not certify that field. Other unreviewed new attributes,
including directional approaches, likewise remain `null`.

Complete rail-region memberships, navigable river segments/bank control, exact
naval paths intersecting narrow-crossing artillery, and the two Northern Ireland
blocker lists remain unpopulated. Legacy coast `railway_connection` values are
preserved pending AM-229; they grant no movement into a sea. Positive land-border
rail coverage can be derived, while missing evidence remains unknown.

Existing `current_owner` and `is_capital` fields remain compatibility setup hints,
not authoritative runtime state. Original nationality is separate, and sea zones
have no owner. No starting pieces, national income, combat engine or runtime
permissions are implemented by these geographic records.

## Regeneration and validation

```sh
./.venv/bin/python tools/build_manual_map_json.py
./.venv/bin/python tools/build_nation_home_country_json.py
./.venv/bin/python tools/build_theatre_scenario.py
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

All 100 Python tests pass, including independent map examples, unique facility
identity/access checks, directed terrain, uncertainty preservation, convoy and
special-route invariants, Home Country membership, and campaign projection.
Builders reproduce their generated files deterministically. Tests validate local
image hashes when those optional, Git-ignored sources are available.

`consolidate.py`, `audit_structure.py` and `rebuild_naval_reaudit.py` now replay
the checkpoint map, so regenerating historical reports cannot reinterpret the
implemented map as the original baseline. The production builder reads the
authoring inputs directly and does not interpret audit prose.
