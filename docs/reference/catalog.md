# Units, facilities and technology

This reference describes the shared catalog used by the regional campaign. Start
with the [project guide](../README.md) for progress and the
[architecture](../architecture.md) for how definitions connect to rules execution.

## Data and interfaces

The [v4.3 catalog](../../game_content/catalog/gw36_v43/) separates definitions
from scenario setup:

| File | Responsibility |
| --- | --- |
| `land_air.json` | Land/air/rocket types, classes, base statistics and special modes |
| `naval.json` | Naval types, surviving damage states, cargo, carrier and repair rules |
| `facilities.json` | Facilities, production/repair capacities, damage and upgrades |
| `technologies.json` | Research stages, unlocks, modifiers and automatic conversions |
| `build_charts.json` | National purchase/upgrade rows, dates, caps, prices and prerequisites |

Each definition has an internal ID, a display name and source references. A
registered foreign or setup-only type is not automatically purchasable. National
build rows and actual game context determine access.

The public [Catalog interface](../../include/game/catalog.hpp) supplies:

- `stats` and `modes` for current damage, technology and context;
- `purchaseEligibility`, `purchaseOptions` and `placementEligibility` for separate
  purchase and placement requirements;
- `priceOptions` for staged payments and construction alternatives;
- `automaticConversions`, `productionCapacity` and `repairCapacity` for current
  technology/facility effects.

`catalogContext` derives the nation, power status, date, technologies, caps and
zone conditions from authoritative state. Unknown prerequisites fail closed.
The loader attaches an immutable catalog to the shared definition and includes
its fingerprint in definition identity. State validation rejects unknown types,
invalid surviving damage and unknown technology stages.

## Conditions that execution must retain

Base statistics and conditional modes are separate. A special-fire mode does not
authorize skipping its targeting, timing, terrain or national prerequisites.
[Combat](combat.md) applies those conditions and resolves damage; [movement](movement.md)
proves routes; [economy](economy.md) spends cash and allocates sites/capacity.

Militia movement depends on Major-Power status and Home Country at both endpoints.
Turn preparation derives movement from current damage, technology and homeland
context; an unknown homeland does not grant an exception. Improved Factories
changes production capacity. Improved Construction offers a stage discount or
the full-price combination of the first two stages; those alternatives do not
stack and do not redefine completed asset value.

The naval data records the user's damaged-capital-ship ruling and its exact
interpretation. The printed movement penalty and carrier capacities remain
separate. Setup-only Torpedo Boat Destroyer and Coastal Submarine valuation comes
from the scenario contract rather than an invented purchase row. Opening ship
queue payments remain construction accounting, not another initial purchase.

CCP Soviet-rail production and KMT Burma-Road prerequisites remain in source data.
The closed campaign lacks their required external endpoints; a generic supply
flag or Mongolian control does not enable them. The
[clarification register](../../game_content/rules/clarifications.md) records adopted
rule interpretations separately from catalog implementation.

## Source and regression references

See [catalog implementation](../../src/catalog.cpp),
[catalog regressions](../../tests/catalog_tests.cpp),
[source/chart checks](../../tests/test_m3_catalog_sources.py) and the
[archived source coverage](../archive/milestones/m3/source_coverage.md).
Historical coverage reports describe their original runtime and do not certify
the complete global game.
