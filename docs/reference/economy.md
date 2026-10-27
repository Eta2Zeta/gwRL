# Income, production and construction

The [economy interface](../../include/game/economy.hpp) composes political
possession, [catalog](catalog.md) purchase rows and [logistics](movement.md)
proofs. Implementation lives in [economy.cpp](../../src/economy.cpp) and
[economy_lendlease.cpp](../../src/economy_lendlease.cpp), backed by the
[source profile](../../game_content/rules/gw36_economy_v43.json).

## Accounting and collection

`effectiveTerritorialIpp` evaluates current territorial value; `refreshIncome`
updates tracked rates. Treasury collection is a separate turn-boundary effect.
The regional rules retain Japanese China-control bonuses and capital conditions;
controlled minors receive no ordinary income. Absent nations supply no hidden
income or external events.

City bombing permanently removes territorial IPP in twenty-damage increments.
Repairing city damage does not restore lost IPP, and destroyed cities cannot be
repaired. Combat damage handlers share economy's construction/facility accounting.

Construction queues retain cumulative actually-paid IPP independently of
remaining payments. A national purchase pays its current stage, with at most one
stage per project per Player Turn. Opening queues retain their prior payments
without debiting opening cash again. Completion replaces the project with one
completed asset; scoring never counts both. Free recruitment work does not
invent a payment. Destroyed projects disappear without a refund.

The approved wealth objective uses current income rate, completed net assets,
treasury and paid unfinished construction. It is separate from income collection
and the publisher's global victory conditions; consult the scenario contract
linked from the [project guide](../README.md) for the exact formula.

## Purchase, capacity and placement

`economyActions`/`applyEconomyAction` enforce national rows, dates, technologies,
shared caps, cash and actual production capacity. Improved Construction's stage
discount and combined-first-two-stage alternatives do not stack.

Placement requires current supply and possession since turn start. Repairs or
upgrades cannot create same-turn factory/yard capacity. Current technology effects
apply immediately, but new facilities and captured factories cannot produce in
their placement/capture turn. Production and capital-ship repair share shipyard
slots. Chinese decentralized production follows immediate evolution and its
explicit same-own-turn grace; excluded Soviet/Burma prerequisites remain inactive.

Captured Medium/Major Factories downgrade while retaining original tier/damage
limits; repossession by the original owner restores the original tier. Ordinary
repairs charge per damage. Capital-ship repairs cost no IPP but consume repair
capacity and retain action restrictions. A rail repair targets one land side,
leaving the opposite side unchanged.

Unit/facility upgrades remain queued replacements until Place Units selects a
suitable current target. A previously used unit can be upgraded; a newly placed
unit cannot. Militia upgrades share their per-turn limit with received lend-lease
credits. New rail across another nation's border requires that owner's consent;
declining spends nothing. Invalid neutral/enemy endpoints are unavailable.
New coastal facilities explicitly select their served sea accesses.

## Research and lend-lease

Research selects an undamaged Major Factory. It supplies one die, each technology
is attempted at most once per calendar turn, and stage III has its date gate.
Completed effects and conversions apply immediately. Relocation cannot reuse a
factory already committed to research, repair or upgrade that turn.

Lend-lease validates sender/recipient permission, one item per recipient per sender
turn, actual delivery and blockades. Failed delivery retains a waiting queue.
Delivered base/militia-upgrade credits wait for the recipient's next placement;
funded repairs occur on its turn. The named Elite Airborne conversion exception
does not permit other technology-only units generally.

Japan-to-Dadao delivery uses the adopted destination exception in
[RCL-010](../../game_content/rules/clarifications.md), retaining ordinary supply and
delivery requirements. That eligible area also applies to delivered bases and
militia credits; it does not grant Dadao a general Home Country.

## Source and regression references

[Economy tests](../../tests/economy_tests.cpp) exercise income/collection, queues,
capacity, research, damage/setbacks, upgrades, delivery, consent and exact replay.
The [archived source coverage](../archive/milestones/m6/source_coverage.md) preserves
the rendered-page review and explicit construction/Elite Airborne source answers.
Use the [clarification register](../../game_content/rules/clarifications.md) for
current ruling status rather than treating historical verification as a new rule.
