# M3: unit, facility and technology catalog

Status: **complete and verified on 21 October 2026**. All seven CTest suites and
all 128 repository Python tests pass. No M3 user decision remains.

M3 supplies the definitions used by the shared campaign engine: what each piece
is, its values and abilities, and which printed purchase options apply to each
nation. The catalog is shared game data; the closed campaign adds its approved
setup and exclusions.

The public interface is [catalog.hpp](/Users/home/Desktop/gwRL/include/game/catalog.hpp).
The source data lives in [gw36_v43](/Users/home/Desktop/gwRL/game_content/catalog/gw36_v43):

| File | Coverage |
| --- | --- |
| `land_air.json` | 37 land, air and rocket types, including source-only foreign types. |
| `naval.json` | 16 naval types and every surviving damage state. |
| `facilities.json` | 15 factory, base, port, dockyard, shipyard, defense and railway definitions. |
| `technologies.json` | All 16 technologies, research thresholds, unlocks, modifiers and conversions. |
| `build_charts.json` | All 181 printed purchase rows across the Japanese major and both Chinese minor/major charts; three railway terrain-price alternatives and 23 upgrade rows. |

Each definition has one internal `id` and one human-readable `name`. Source
references record the rulebook or national-sheet page. These are not extra names
for the player to manage. The existing faction bridge remains separate.

## What the engine can now query

- Base and damaged unit values, classes, targets, carrying capacities, repairs,
  upgrades and structured abilities. Special fire such as AAA and carpet bombing
  remains a distinct mode with its own dice, targets and conditions.
- Purchase eligibility by nation, minor/major status, date, completed technology,
  national prerequisites and shared per-turn caps. Registering a type does not
  make it purchasable. Upgrade rows identify their source type and delivery rules.
- Placement prerequisites separately from purchase eligibility. Unsatisfied or
  unknown predicates fail closed. The later movement, supply and production
  modules will evaluate paths, capacity use and selected sites.
- Printed payment stages and Improved Construction alternatives. A quote can
  reduce each stage by one IPP or combine the first two stages at their full
  combined price. The two benefits do not stack. Improved Factories changes
  production capacity; it does not discount prices or completed asset values.
- Completed technology effects, automatic Airborne Doctrine conversion,
  facility production/repair capacity, including partial Major Factory damage,
  and base asset values.

The scenario loader attaches an immutable catalog to the shared definition and
includes its fingerprint in definition identity. All 99 setup units now receive
known movement allowances. The map's approved `airfield` spelling becomes
`airbase` in mutable facility state while the original map data stays intact.
State validation rejects unknown types, impossible surviving unit damage and
unknown technology stages. Every registered unit damage state is covered by
state and observation round-trip checks. Turn preparation refreshes movement
from the current damage, technology and home-country context.

Militia's potential movement allowance is one only for a Major Power in its
Home Country. The catalog retains the requirement that both start and destination
are in Home Country; evaluating a legal destination belongs to movement rules.
An unknown home-country membership grants no movement exception.

## Approved campaign details

The user's naval ruling supplies the damaged battleship values: attack, defense
and bombardment fall by two per damage. Damaged fleet carriers lose one defense.
The separate printed movement penalty and aircraft capacities are retained.
The exact ruling and its applied interpretation are recorded in `naval.json`.

Torpedo Boat Destroyers and Coastal Submarines remain unbuildable, with no generic
purchase price. Their campaign asset values of five and four IPP come from the
frozen M0 contract. Japanese opening ship queues retain the ten IPP already paid;
loading the catalog does not buy those ships again.

CCP's actual Soviet-rail production prerequisite and KMT's Burma Road prerequisite
are retained as source rules. The closed scenario cannot satisfy them. A generic
supply flag, Mongolian control or a manually asserted prerequisite cannot enable
the excluded routes through a context derived from this campaign state.

National conditional abilities, terrain exceptions, special combat sequences and
placement details retain typed parameters and source references. M3 does not
execute battles, trace supply paths or spend production cash. Those handlers
follow the implementation plan; the campaign is not yet playable.

## Verification

```sh
cmake -S . -B build/m3 -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/m3 -j 4
ctest --test-dir build/m3 --output-on-failure
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

The acceptance checks cover every printed row, setup type and surviving unit
state, alongside independent source-hash, source-page and chart-coverage checks.
See [source coverage](/Users/home/Desktop/gwRL/docs/m3/source_coverage.md) and the
[M3 verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m3/verification.json)
for final results. Historical M0, M1 and M2 verification records are preserved;
M3 records the later changes to the implementation and progress documents.
