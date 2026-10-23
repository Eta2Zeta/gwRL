# Closed Japan–China campaign map

Status: **map and campaign specification only**. No initial units, starting
treasuries, construction queues, full-rules environment or new training run are
created by this extractor. The separate `m0/` source audit now inventories the
official setup and local cash. The **M0 specification was verified and frozen on
21 October 2026**, with 106 repository tests passing. This is not a playable
full-rules engine. Do not feed this map to the old six-zone setup loader
as if their schemas and mechanics were interchangeable.

The [M2 foundation](/Users/home/Desktop/gwRL/docs/m2/README.md) now loads these
setup files into shared C++ campaign state, including the 99 deployed pieces,
22 facilities and two national queues. It supplies validated action execution,
turn/reaction timing, randomness and replay. Gameplay rule modules remain later
milestones. See its verification record for the six CTest suites and 119 passing
Python tests; the M0 freeze result above remains historical.

The [M3 catalog](/Users/home/Desktop/gwRL/docs/m3/README.md) now supplies shared
unit, facility and technology definitions and every national chart row. Setup
movement is known, and purchase eligibility remains separate from ownership or
existence. Its seven CTest suites and 128 Python tests include the catalog
acceptance checks; earlier milestone results above remain historical.

The [M4 political layer](/Users/home/Desktop/gwRL/docs/m4/README.md) now handles
warlords, influence/recruitment, truce/evolution, declaration timing and surrender.
Mongolia and every warlord have source-backed Home Country membership. Dadao
remains separate under direct Axis control if Japan surrenders, as approved by
the user. Ten CTest suites and 128 Python tests pass; movement/logistics is next.
The full campaign still needs its later gameplay and accounting modules.

The [current M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md) supersedes the
inventory and scope below. Mongolia remains distinct under direct
Comintern control and acts in the normal USSR turn position: CCP -> Mongolia ->
Japan -> KMT, with no Soviet participant or account. The
[shared rule register](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md)
adopts one result per whole warlord (RCL-003). RCL-004 is closed after the user
reported on 17 October 2026 that the developers fixed the wording for the next
version; no publication or version number has been independently checked. Its
Comintern Brothers undamaged-railroad/placement requirement is unchanged and
stays inactive without USSR.

The [M5 movement/logistics](/Users/home/Desktop/gwRL/docs/m5/README.md) and
[M6 economy/production](/Users/home/Desktop/gwRL/docs/m6/README.md) modules are
complete as of 22 October, including regional routes, supply, actual income,
staged construction, placement, repairs, research and RCL-010 Dadao aid.
M7 land combat is complete, including shared-zone truce resolution under
RCL-012. M8 air operations are complete, including adopted RCL-013 artillery city
bombardment. M9 naval operations and M10 integration completed their gates on
23 October, including two exact-replay full 44-turn campaign traces. M11 exposes
the campaign API and tested stochastic vector search. RCL-014 and RCL-015 are
provisionally adopted pending developer clarification. These source profiles are
fingerprinted with the scenario definition; earlier verification files remain
historical snapshots. Full-campaign neural training and evaluation remain M12 work.

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
- [Frozen baseline](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/frozen_baseline.json):
  records the specification freeze and verified artifacts.
- [M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md): rules ledger, national
  audits, purchase-price tables, approved decisions and completed verification.
- [M9 naval exit](/Users/home/Desktop/gwRL/docs/m9/source_exit_2026_10_23.json):
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
The full command passed **106 tests** for the 21 October 2026 M0 freeze; it does
not establish that future full-rules combat/economy handlers are implemented.
