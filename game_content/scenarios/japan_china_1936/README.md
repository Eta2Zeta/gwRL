# Japan–China 1936 campaign scenario

The scenario the campaign engine loads: a closed 37-node map projection, the
source-audited official setup in `m0/` and the faction index in `m1/`. The engine
plays it from July 1936 through the complete July 1941 round under the rules
profiles in `game_content/rules`. The [M0 review](../../../docs/archive/milestones/m0/README.md)
records the approved specification, and the milestone pages from
[M2](../../../docs/archive/milestones/m2/README.md) to [M11](../../../docs/archive/milestones/m11/README.md)
describe the engine modules. Mongolia remains distinct under direct Comintern
control and acts in the normal USSR turn position: CCP -> Mongolia -> Japan ->
KMT, with no Soviet participant or account. The
[shared rule register](../../rules/clarifications.md)
records the adopted readings of unclear rules.

Loading the scenario checks the recorded hashes of its map, its setup files, the
faction index, the scenario contract and every source file that the rules
profiles cite. Change those files only together with their recorded hashes.

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
  reconciliation and source provenance for later catalog implementation.
- [Frozen baseline](m0/frozen_baseline.json):
  records the specification freeze and verified artifacts.
- [M0 review](../../../docs/archive/milestones/m0/README.md): rules ledger, national
  audits, purchase-price tables, approved decisions and completed verification.
- [build_theatre_scenario.py](../../../tools/build_theatre_scenario.py)
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

## Approved campaign specification

- Start July 1936; score after the complete July 1941 round, 11 half-year rounds.
- Three learning sides: Axis, Allies, Comintern. Preserve separate national
  turns, accounts, political relations and rule-defined minor control.
- Each side maximizes its wealth minus both other sides' wealth combined.
  The initial weighting is `wealth = current income-per-turn rate + 0.1 × assets`.
  Assets include units and infrastructure (including setup assets), treasury and
  paid unfinished construction, all at the 0.1 asset weight.
  The construction accounting policy is adopted: score cumulative already-paid
  amounts until completion, then replace that entry with full completed catalog
  value. Source reconciliation establishes 5 IPP already paid for each retained
  ship: Heavy Cruiser #2 has 5 remaining; Fleet Carrier #3 has 10 remaining.
  Damaged units and facilities are valued at purchase price minus repair price.
- Starting pieces are only those in the official setup on included tiles;
  excluded-tile pieces are not relocated into this theatre. Theatre-adjusted
  starting cash is Japan 15, KMT 6 and CCP 2 IPP, using the smaller of
  official starting cash and retained directly possessed territory IPP. This
  formula is a documented scenario choice under the user's approval, not an
  official alternate setup. Controlled/unaligned minors start with no cash.
- Japan's P15 Fleet Carrier carries one Fighter and one Tactical Bomber; its
  Light Carrier carries one Fighter. Torpedo Boat Destroyers score 5 IPP each
  and Coastal Submarines 4; neither becomes purchasable. USA-triggered queue
  carriers are excluded. Ordinary queued ships use eligible supplied shipyards,
  with Major Shipyards required for the Fleet Carrier.
- City labels have no extra asset price. Each undirected railway border counts
  once and splits value equally between endpoint possessors. Same-alliance ends
  aggregate to full value; an uncontrolled minor's share counts toward nobody.
  This affects scoring only.
- Controlled/aligned minor assets count toward the legally controlling side;
  uncontrolled unaligned warlords count toward nobody. That does not create
  income collection where the minor rules forbid it.
- Convoys, interdiction and Kido Butai are disabled. Normal MAP, blockades and
  independently applicable naval movement/combat remain. There are no FEC or
  USSR accounts; Mongolia uses the USSR turn slot under direct Comintern control.
- Outside routes/resources/events are absent. Rules missing their outside
  prerequisites are inactive in this profile; no implicit aid or off-map income.

These manifest fields are specifications copied as provenance, not code that
implements calendars, factions or rewards. Tannu Tuva's unresolved political
identity is deferred and does not block this scenario because its node and all
incoming neighbor entries are excluded.

See the [full implementation plan](../../../docs/plans/japan_china_full_rules_plan.md)
and [Japan/sea audit](../../../docs/map_audits/japan_and_nearby_seas.md).

## Tests

```sh
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

The map tests cover master-map expectations, facility-instance identity, malformed
inputs, exact projection, boundary cuts, reciprocal infrastructure, directional
differences, narrow-crossing dependencies, hashes and byte-for-byte regeneration.
