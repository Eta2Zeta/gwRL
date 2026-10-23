# M5: movement and shared logistics

M5 implements land movement and the reusable logistics queries needed by economy,
air operations and the later naval module. Movement decisions carry a stable unit
ID and an explicit route. The engine retains the turn origin, each traversed zone,
remaining movement, and each attacking unit's final approach independently.
Different contingents join one pending battle without sharing a river penalty.
Empty attacks register a battle so KMT Low Morale still resolves before capture.

The implementation distinguishes ordinary movement, post-battle blitz, strategic
rail/river movement and narrow crossings. Entered node and directional border
terrain can end movement; cavalry's mountain exception does not erase a second
terrain's restriction. Enemy land stops movement until combat resolves. Repair,
attrition, newly placed units, militia attack restrictions and required Chinese
gift withdrawal remain explicit state conditions. Paired blitz companions must
follow their chosen armor to the same target.

Strategic rail uses regional capacity, including both regions on a crossing and
the Improved Logistics bonus. Gauge changes require that technology. Damaged
rail and hostile river banks cut routes; the static rail artwork is never erased
to represent damage. Improved Logistics also enables factory relocation within
Home Country, preserving damage and consuming one rail capacity for a Minor or
Medium Factory or two for a Major Factory. Research, upgrade and repair
commitments prevent a factory from moving; a moved factory supplies no production.

Supply starts in possessed Home Country. It follows continuously held, undamaged
rail/river infrastructure and naval facilities. Minor/major naval ranges are 2/4,
extended by Improved Logistics. The departure and arrival coastal interfaces cost
no sea range. A facility can refresh range once, cannot teleport supply between
its disconnected sea accesses, and cannot reopen a sea leg after inland landfall.
The route query consumes no movement or rail capacity. Only enemy surface
warships prevent a three-surface-warship blockade, following closed RCL-005.
All access seas must be blockaded to close a shared facility.

The lend-lease route query implements the recipient's final facility exception
and stops in the first qualifying recipient Home Country. Naval deliveries cannot
travel over inland rails. Japan's Dadao delivery endpoint follows RCL-010 while
keeping ordinary supply requirements. Burma/Ledo and CCP's exact Soviet rail
connection stay inactive because their required external endpoints are absent.
The engine does not restore cropped routes or open impassable Himalayan borders.

The immutable M5 source profile overlays individually reviewed gauge, river and
region values on the retained map. It is included in the definition fingerprint;
the frozen M0 map and older verification records are unchanged. See
[source coverage](source_coverage.md).

`movement_tests` contains 14 fixture groups covering the M5 exit cases, both
Improved Logistics bonuses, factory relocation, cargo/withdrawal capacity, the
lend-lease destination exception, and checkpoint preservation of pending routes
and battles. The module composes with M4 politics, M6 economy, M7 combat and M8 air.

## Interfaces and later milestones

`movement.hpp` exposes typed route validation, directional approaches, supply
paths, facility access, blockade, cargo linkage and withdrawal proof. Supply uses
the active Player Turn snapshot. Defensive airbase age uses the defender's own
last-turn timestamp through `heldSinceNationTurnStart`.

Air operations supply aircraft flight and landing decisions. M9 will supply naval
movement, loading and interception decisions. The present Chinese gift proof
reserves actual adjacent transport capacity; M9 can additionally prove transport
routes to reach withdrawing forces. Cargo attachment itself only preserves
reciprocal links; the calling air/naval rules validate transport eligibility.

Whenever infrastructure is damaged, the damage handler stamps
`State.flags["logistics_damaged_turn:" + id] = playerTurnSerial + 1`.
New rail construction stamps `logistics_rail_created_turn:<id>` the same way.
These stamps prevent a repair or new construction from satisfying a requirement
that the infrastructure was undamaged throughout the active turn.

The dated [M5 verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m5/verification.json)
records source/artifact hashes, completed fixtures and the integrated test results.
Earlier milestone records remain unchanged historical snapshots.
