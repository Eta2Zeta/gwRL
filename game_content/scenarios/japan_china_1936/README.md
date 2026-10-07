# Closed Japan–China campaign map

Status: **map and campaign specification only**. No initial units, starting
treasuries, construction queues, full-rules environment or new training run are
created by this extractor. The separate `m0/` source audit now inventories the
official setup and local cash; unresolved choices prevent playable-state
certification. Do not feed this map to the old six-zone setup loader
as if their schemas and mechanics were interchangeable.

The [current M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md) supersedes the
historical inventory and scope below. Mongolia remains distinct under direct
Comintern control and acts in the normal USSR turn position: CCP -> Mongolia ->
Japan -> KMT, with no Soviet participant or account. The
[shared rule register](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md)
adopts one result per whole warlord (RCL-003) and the Comintern Brothers undamaged
railroad/placement requirement (RCL-004); the latter stays inactive without USSR.

## Files and rebuilding

- `manifest.json`: explicit tile selection and approved/proposed campaign choices.
- `map.json`: generated, lossless projection of `../../maps/gw36_manual_map.json`.
- `m0/scenario_contract.json`: source-audit contract, local accounts, wealth
  conventions and explicit pending decisions; not an executable rules profile.
- `m0/japan_setup.json`, `m0/china_minor_setup.json`: source-linked setup rows,
  original PDF hashes and excluded/unresolved entries. Together: 103 units,
  three new factories and references to 21 existing physical map facilities.
- `m0/convoy_audit.json`: source evidence for the fully local Nagasaki Line and
  cut Tokyo Line. The current map/extractor does not yet project convoy records;
  this audit identifies a required extension, not implemented raiding mechanics.
- [M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md): rules ledger, national
  audits, purchase-price tables and user decisions needed before certification.
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

There are **38 nodes: 32 land + 6 sea**:

- Thirteen `land_china_*` tiles; the four Manchurian tiles; Tibet, Kwangtung,
  Hainan, Formosa, Hong Kong and Korea.
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
The **45 excluded neighbor entries are removed**, not converted into external
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

## Planned campaign contract

- Start July 1936; score after the complete July 1941 round, 11 half-year rounds.
- Three learning sides: Axis, Allies, Comintern. Preserve separate national
  turns, accounts, political relations and rule-defined minor control.
- Each side maximizes its wealth minus both other sides' wealth combined.
  The initial weighting is `wealth = current income-per-turn rate + 0.1 × assets`.
  Assets include units and infrastructure (including setup assets), treasury and
  paid unfinished construction. Applying the same 0.1 asset weight to treasury
  and paid construction is the current interpretation, pending confirmation.
  The construction accounting policy is adopted: score cumulative already-paid
  amounts until completion, then replace that entry with full completed catalog
  value. Reconcile initial queue payments from source stages.
  Damaged units and facilities are valued at purchase price minus repair price.
- Starting pieces are only those in the official setup on included tiles;
  excluded-tile pieces are not relocated into this theatre. Theatre-adjusted
  starting cash is Japan 15, KMT 6, CCP 2 and FEC 2 IPP, using the smaller of
  official starting cash and retained directly possessed territory IPP. This
  formula is a documented scenario choice under the user's approval, not an
  official alternate setup. Controlled/unaligned minors start with no cash.
- Controlled/aligned minor assets count toward the legally controlling side;
  uncontrolled unaligned warlords count toward nobody. That does not create
  income collection where the minor rules forbid it.
- Outside routes/resources/events are absent. Rules missing their outside
  prerequisites are inactive in this profile; no implicit aid or off-map income.
- The two-round learning task remains a separate scenario using the same
  progressively upgraded engine, not a preserved incomplete engine fork.

These manifest fields are specifications copied as provenance, not code that
implements calendars, factions or rewards. Tannu Tuva's unresolved political
identity is deferred and does not block this scenario because its node and all
incoming neighbor entries are excluded.

See the [full implementation plan](/Users/home/Desktop/gwRL/docs/plans/japan_china_full_rules_plan.md)
and [Japan/sea audit](/Users/home/Desktop/gwRL/docs/map_audits/japan_and_nearby_seas.md).

## Tests (no training)

```sh
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Tests cover master-map expectations, facility-instance identity, malformed
inputs, exact projection, boundary cuts, reciprocal infrastructure, directional
differences, narrow-crossing dependencies, hashes and byte-for-byte regeneration.
