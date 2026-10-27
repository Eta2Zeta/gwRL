# Closed Japan–China campaign data

These files define the approved 37-node regional scenario, its 99-piece July1936
setup, national accounts and construction queues. The shared CPU engine loads
this data into the complete regional campaign. The extractor itself only rebuilds
the map projection; it does not launch a game or training.

Read the [scenario contract](../../../docs/reference/scenario.md) for campaign
boundaries and scoring, the [engine reference](../../../docs/reference/engine.md)
for loading/state/replay, and the [project guide](../../../docs/README.md) for
current progress. The [clarification register](../../rules/clarifications.md)
records adopted interpretations. Short curricula use the same setup and rules
with explicit shorter real endpoints; the full campaign retains eleven rounds.

The `m0/` setup inventories and later verification directories retain their
original filenames, source hashes and historical status labels. They are data and
provenance consumed by the engine/checks, not the current documentation layout.
Historical delivery reports are in the [milestone archive](../../../docs/archive/milestones/README.md).

## Files and rebuilding

- `manifest.json`: explicit tile selection and approved campaign choices.
- `map.json`: generated, lossless projection of `../../maps/gw36_manual_map.json`.
- `m0/scenario_contract.json`: source-audit contract, local accounts, wealth
  conventions and reconciliation status; not an executable rules profile.
- `m0/japan_setup.json`, `m0/china_minor_setup.json`: source-linked setup rows,
  original PDF hashes and excluded source entries. Together: **99 deployed units**
  (Japan 48, KMT 12, CCP 5, warlords 32, Mongolia 2), three setup factories and
  references to 19 existing physical map facilities. Japan also retains two
  ordinary construction-queue ships, each with 5 IPP already paid.
- `m0/convoy_audit.json`: source evidence for the fully local Nagasaki Line and
  cut Tokyo Line. Convoy play is excluded by campaign choice; this is reference
  evidence only. The global map preserves its convoy layer.
- `m0/catalog_source_checks.json`: exact research thresholds, queue-payment
  reconciliation and source provenance for catalog verification.
- [Frozen baseline](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/frozen_baseline.json):
  records the specification freeze and verified artifacts.
- [Scenario contract](../../../docs/reference/scenario.md): approved decisions, scoring and source-audit references.
- [M9 naval exit](../../../docs/archive/milestones/m9/source_exit_2026_10_23.json):
  reviewed sources and four combined voyage/landing/retreat traces.
- [M10 integration evidence](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m10/integration_evidence_2026_10_23.json):
  two complete campaign replays and the source-linked runtime ledger.
- [M11 verification](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m11/verification_2026_10_23.json):
  final C++/Python results, actual campaign checkpoint restores and vector search.
- [build_theatre_scenario.py](/Users/home/Desktop/gwRL/tools/build_theatre_scenario.py)
  is the builder. Run the command below from the repository root.

```sh
./.venv/bin/python tools/build_theatre_scenario.py
```

After editing the authoritative map generator, rebuild both artifacts:

```sh
./.venv/bin/python tools/build_manual_map_json.py
./.venv/bin/python tools/build_theatre_scenario.py
```

Other scenarios use the same extractor:

```sh
./.venv/bin/python tools/build_theatre_scenario.py \
  --map game_content/maps/gw36_manual_map.json \
  --manifest path/to/manifest.json \
  --output path/to/map.json
```

If `--output` is omitted it becomes `map.json` beside the selected manifest.
Output cannot overwrite the source map or manifest, including through aliases.
Validation completes before atomic output replacement; invalid inputs do not
overwrite an existing artifact. Use a different output path to retain an older
generated version.

## Selected geography

There are **37 nodes: 31 land + 6 sea**:

- Thirteen `land_china_*` tiles; the four Manchurian tiles; Tibet, Kwangtung,
  Hainan, Formosa and Korea. Hong Kong and all FEC forces are excluded.
- Kobdo, Ulyassutai, Central Mongolia and Kerulen. Tannu Tuva is excluded by
  user decision; it remains in the global map.
- Tokyo, Honshu, Hokkaido, Kyushu and Okinawa. No other Japanese islands.
- P14, P15, P16, P32, P33 and P41 only.

`included_node_ids` is authoritative, not current owner, a bounding rectangle or
a flood-fill. All eight Chinese warlords' territories are represented; this does
not automatically align them or grant an alliance control of neutral pieces.

Every retained node field and internal directed edge is copied unchanged,
including combined border terrain, rivers flowing between tiles versus combat
river crossings, boolean rail, gauge, facilities/IDs and narrow-crossing capacity.
Excluded neighbor entries are removed, not converted into external
interfaces. The non-navigable `_meta.boundary_cuts` report records their IDs.
Source/manifest SHA256 hashes and copies of source warnings/configuration make
the result reproducible. The source global map is never cropped or mutated.

Facilities carried only on deleted coast edges disappear from this scenario:
in particular, Hokkaido's P7 port is not available. Shared facilities still have
one identity (Nanking's P14/P32 port); distinct facilities of the same type remain
distinct (Honshu's two P15 shipyards). Do not deduplicate by facility type.

Annotated direct land narrow crossings carry `narrow_crossing_sea_zones`. Every
such sea must be selected when both crossing endpoints are retained; otherwise
the builder reports an error rather than silently changing the retained rule
data. Both retained crossings here satisfy this dependency (P16 and P41).

Campaign timing, controllers, exclusions, wealth, setup-queue values and railway
attribution are maintained in the [scenario contract](../../../docs/reference/scenario.md).
The [Japan/sea audit](../../../docs/map_audits/japan_and_nearby_seas.md) records map
source qualifications. The two-round study uses the same shared rules engine
with separate benchmark configuration.

## Tests (no training)

```sh
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Tests cover master-map expectations, facility-instance identity, malformed
inputs, exact projection, boundary cuts, reciprocal infrastructure, directional
differences, narrow-crossing dependencies, hashes and byte-for-byte regeneration.
Current executable rule evidence is indexed in the
[runtime coverage](../../../docs/reference/runtime-coverage.md); original test-run
results remain in the milestone archive.
