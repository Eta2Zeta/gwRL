# Movement, supply and shared logistics

This reference covers the shared route service. [Combat](combat.md) resolves
battles and air/naval continuations; [economy](economy.md) uses route proofs for
production and delivery. The approved regional map remains closed: geographic
proximity never reconstructs an impassable or cropped edge.

## Route and state interfaces

[movement.hpp](../../include/game/movement.hpp) exposes typed movement modes,
route validation, directional approaches, access permissions, supply, blockade,
cargo linkage and withdrawal eligibility. The [implementation](../../src/movement.cpp)
uses the immutable [movement profile](../../game_content/rules/gw36_movement_v43.json)
with reviewed gauge, river and region overlays included in definition identity.

An executed move retains the unit ID, turn origin, traversed zones, remaining
movement and final attack approach. Contingents can join one battle while
retaining different river/terrain modifiers. Empty attacks still register battles
so applicable Low Morale resolves before capture. Cargo attachment maintains
reciprocal links; the calling air/naval service must establish transport legality.

Ordinary movement, blitz, strategic rail/river movement and narrow crossings
have separate rules. Destination and directional-border terrain can end movement;
one terrain exception does not erase another restriction. Hostile land stops
movement until its battle resolves. Repair, attrition, newly placed pieces,
militia limits and Chinese-gift withdrawal remain explicit state conditions.
Blitz companions must follow their named armor to the selected destination.

## Rail, infrastructure and turn snapshots

Strategic rail consumes capacity in every crossed region, including both regions
of a regional border. Improved Logistics affects capacity/range and permits gauge
changes. Factory relocation stays within Home Country, preserves damage and
consumes tier-specific rail capacity. Research/repair/upgrade commitments block
relocation, and a moved factory supplies no production.

Rail damage does not erase map artwork. Damage stamps
`logistics_damaged_turn:<id>` and construction stamps
`logistics_rail_created_turn:<id>` prevent same-turn repairs/new rail from passing
an undamaged-throughout-turn requirement. Source overlays distinguish river
supply routes from directional combat river penalties; those graphs cannot be
substituted for each other.

Supply uses the active Player Turn snapshot. `heldSinceNationTurnStart` separately
checks a defender's own last-turn timestamp where required, such as defensive
airbase age. These two time references must not be interchanged.

## Supply and delivery

`supplyRoute` starts in possessed Home Country and proves held, undamaged rail,
river and naval-facility continuity without consuming movement or rail capacity.
Minor/Major sea ranges and Improved Logistics apply to sea legs. Coastal
interfaces consume no sea range. A facility can refresh range once, cannot join
disconnected sea accesses by teleportation, and cannot reopen a sea leg after
inland landfall.

`seaBlockaded` and `facilityBlockaded` use surface-warship conditions. All sea
accesses must be blockaded to close a shared facility. A blocking-sea annotation
for a land narrow crossing does not by itself force a naval passage or Coastal
Artillery shot; see [naval combat/geography](combat.md).

`lendLeaseSupplyRoute` applies the final-recipient facility exception and stops
in the first eligible recipient destination. Naval deliveries cannot continue
through inland rail legs. Japan-to-Dadao destinations follow RCL-010 without
creating a general Dadao homeland or supply origin. Burma/Ledo and the exact CCP
Soviet rail route remain inactive when their external endpoints are absent.

Chinese gifts require an actual friendly withdrawal route or transport proof
with reserved real capacity. Generic adjacency or a policy assertion is
insufficient. Air and naval handlers establish the corresponding flight, landing,
transport route, pickup and unloading conditions.

## Source and regression references

The [archived source coverage](../archive/milestones/m5/source_coverage.md) records
page-level evidence and retained-map review. [Movement tests](../../tests/movement_tests.cpp)
cover routes, terrain, rail capacity, supply, delivery and pending-state round trips.
[Air logistics](../../tests/air_logistics_tests.cpp) and
[naval movement tests](../../tests/naval_movement_tests.cpp) exercise the composed
services. This regional overlay does not certify absent global routes.
