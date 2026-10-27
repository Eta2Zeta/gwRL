# M6 — economy, production, construction and research

> Completed milestone reference. Test counts, timings and next steps below describe this delivery. Use the [project guide](../README.md) for current status and instructions.

Implemented on 2026-10-22. The milestone's accounting and production gate is covered by fourteen behavioral fixture groups in `tests/economy_tests.cpp`; the root milestone verification record captures the final integrated checks. M0–M4 frozen records are preserved.

The implementation uses `include/game/economy.hpp`, `src/economy.cpp` and `src/economy_lendlease.cpp`, backed by `game_content/rules/gw36_economy_v43.json`. The source profile contains 22 rules and six sources. Catalog national rows remain the authority for prices, dates, technologies and purchase limits. M5 supplies typed supply routes, held-since-start checks, blockades, facility coasts and the special final-recipient lend-lease route.

## Behavior

- Japan, KMT and CCP collect their current territorial income from retained possessions. Japan also gets one IPP for each of the six specified Chinese territories; these bonuses do not require war against a Major Power. Controlled minors collect no ordinary income, and absent countries supply no hidden income or events. A Major Power without its capital cannot collect.
- City bombing permanently removes territorial IPP in twenty-damage increments. Repairing city damage does not restore those IPP. A destroyed city cannot be repaired.
- National purchases charge the actual current stage and keep cumulative paid IPP separately from remaining payments. At most one stage is paid per project in a Player Turn. The opening Heavy Cruiser and Fleet Carrier each retain five already-paid IPP; opening cash is not charged again. Completion replaces the queue project with one asset.
- Purchases enforce national build charts, calendar and technology gates, specialty caps, cash and available production. Improved Construction offers separate printed, per-stage discount and first-two-stages-combined prices; the two technology benefits do not stack.
- Placement uses current supply and possession since the beginning of the turn. Factories and yards cannot gain same-turn capacity from repairs or upgrades. Current technology benefits apply immediately. Production and repair share shipyard slots. New facilities cannot produce on the turn they are placed; captured factories cannot produce on the capture turn.
- Minor Chinese factions retain decentralized production for infantry-class units and cavalry. M4's immediate evolution and same-own-turn grace determine when that ability ends. Burma Road and Soviet rail production remain inactive under the frozen closed profile.
- Factory capture downgrades Medium/Major Factories while preserving their original tier and damage cap; the original owner recovers the original tier on repossession. Repairs cost one IPP per damage, except capital-ship repairs, which cost no IPP and consume repair slots. Railroad repairs select a particular land side and leave the other side's damage unchanged.
- Research uses an explicitly selected undamaged Major Factory. That factory supplies one die, each technology is attempted at most once per calendar turn, stage III is locked before July 1939, and completed technology/conversions apply immediately. Factory relocation cannot reuse a factory that researched, repaired or upgraded that turn.
- Ordinary unit and facility upgrades remain queue replacements until a suitable target is selected in Place Units. A target used earlier in the turn may be upgraded; a newly placed unit may not. Militia upgrades share their two-per-turn limit with received lend-lease upgrade credits.
- New railroad construction across a foreign border requires a decision from its owner. Declining costs nothing. Construction into a non-controlled neutral or an enemy endpoint is unavailable. New coastal facilities can explicitly serve one or two adjacent sea zones.
- Local lend-lease enforces sender/recipient permission, one item per recipient per sender turn, actual supplied delivery, final-recipient facilities, blockades, no naval delivery via inland land legs, and waiting queues when delivery fails. A delivered base or militia upgrade waits for the recipient's next placement phase. Funded facility repairs are performed on the recipient's turn.

## RCL-010 campaign decision

The user resolved the missing Dadao delivery destination on 2026-10-22: Japan may deliver to any Dadao-possessed Chinese Home Country land zone. The same eligible area applies when placing delivered lend-lease bases or militia upgrade credits. All other delivery and supply constraints remain. This does not give Dadao a general Home Country or an independent supply origin. The clarification register records this as an adopted campaign ruling pending developer clarification.

## Source checks

Two apparent conflicts have explicit source answers and do not need invented campaign rules:

- Rulebook p. 51's construction examples determine the exact setback boundary: five damage to the illustrated stage-2 Major Factory leaves it at stage 3 with two damage; six damage removes it. Each complete three damage causes a setback. The cumulative paid ledger is retained under the frozen M0 policy; destroyed projects disappear without refunds.
- Rulebook p. 47 explicitly permits Elite Airborne lend-lease and states its receiving conversion. This named exception applies despite the general technology-only-unit prohibition on p. 52. A receiver without Airborne Doctrine gets ordinary Airborne Infantry; a receiver with the doctrine gets Elite Airborne Infantry. Other technology-only units remain prohibited.

See `source_coverage.md` for page-level coverage and the remaining milestone boundaries.

## Verification

`cmake --build build/m5-m8 -j4` and `build/m5-m8/economy_tests` pass. The fourteen fixture groups cover current income and capital loss; two-turn opening-queue accounting; repaired factory capacity; decentralized production and finite militia purchases; research date/attempt/conversion rules; construction setbacks and factory recapture; permanent city loss and selected-side rail repairs; supplied Dadao delivery; shared shipyard repair slots; upgrades and discount alternatives; foreign rail consent; recipient upgrade/repair timing; exact checkpoint/replay; the explicit Elite Airborne exception; and replacement targeting after the originally available unit is lost.

An accounting-only fixture advances all 44 national turns with unchanged territory, ending with Japan 180 IPP, KMT 72 IPP and CCP 24 IPP, while the unadvanced opening queues retain ten paid IPP. This verifies collection and the full final round. It does not claim naval combat, transport/amphibious operations or training have been implemented by M6.

The dated [M6 verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m6/verification.json)
records source/artifact hashes, completed fixtures and the integrated test results.
Earlier milestone records remain unchanged historical snapshots.
