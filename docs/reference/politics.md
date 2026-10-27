# Politics, possession and national identity

For the approved campaign setup, use the scenario data linked from the
[project guide](../README.md). This reference describes the political service
boundaries. Official-source questions and adopted rulings belong in the
[clarification register](../../game_content/rules/clarifications.md).

## Interfaces and ownership

The [public interface](../../include/game/politics.hpp) separates permission,
possession, refresh and pending decisions:

| Interface | Responsibility |
| --- | --- |
| `mayDeclareWar`, `declareWar`, `recordLandAttack` | Declaration permissions and land-attack notifications |
| `changePossession`, `captureLand`, `incorporateNation` | Explicit territorial/identity changes after valid gameplay events |
| `refreshPoliticalState` | Ordered evolution, objectives, relationships and surrender effects |
| `queuePoliticalDecision`, `requestPoliticalRoll` | Entitled choices/chance with serialized continuations |
| `terminateChineseTruce` | End the treaty and queue mandatory shared-zone battles |

A political capture notification does not prove a movement route or resolve a
battle. Capture requires surviving attacking land units; liberation and Chinese
land gifts follow their own conditions. The [movement service](movement.md)
provides actual withdrawal eligibility, while [combat](combat.md) supplies the
resolved battle outcome. Possession and tracked land IPP change immediately;
income refresh and treasury collection are separate economy operations.

Nation, original nationality, current possessor, Home Country and alliance
controller are distinct. Current possession does not rewrite original identity.
Mongolia keeps its own homeland and identity under direct Comintern control in
the USSR calendar slot; it does not create Soviet possessions or abilities.
Dadao is a separate minor created during play, not Japanese ownership under
another label. Same-alliance membership alone does not grant every access or
joint-attack permission.

## Political event constraints

Whole warlords are the alignment unit. Foreign-invasion resolution snapshots
neighbor categories before applying any result and rolls once for each eligible
warlord. An earlier outcome cannot alter a later warlord's odds. Influence also
counts relevant zones across the whole warlord, enforces turn-start garrisons,
caps pre-roll spending and preserves the natural-12 KMT backfire. The source
profile identifies the narrow post-surrender KMT reactivation interpretation;
it restores only transferred surviving assets, not erased forces, cash or awards.

CCP recruitment and controlled-minor recruitment use distinct conditions and
choices. Controlled-minor rolls exclude offshore possessions; troop placement
uses continuous possession since turn start. Free construction work advances a
queue without increasing its actually-paid amount. Political recruitment does
not grant controlled minors ordinary income or research rights.

Chinese evolution occurs immediately at 13 possessed territorial IPP, including
during another nation's turn. Capital/factory choices belong to the evolving
Chinese player. The national objective is the same award, not an additional
factory. Minor-only abilities end immediately; the explicit same-own-turn
Decentralized Production exception is tracked separately.

The Chinese Truce has explicit offer/consent, access, defense and termination
states. It can end through voluntary action or evolution and cannot simply be
signed again afterward. Mandatory mixed-stack battles suspend discretionary
gameplay and use the [combat roles and retreat rules](combat.md). They retain the
current calendar clock and actual decision owners.

KMT's no-land surrender, CCP's no-unit elimination and Japan's end-of-own-turn
Tokyo check are separate triggers. Pending surrender ship rolls preserve damage,
construction progress and payments. CCP's surrender-time One China award retains
ordinary placement requirements. The closed-campaign fallback keeps surviving
Dadao under direct Axis-agent control if Japan has no other Axis controller;
this is a scenario choice, not a general publisher rule.

## Scheduling and persistence

Major-Power declaration interrupts are available at permitted boundaries,
including other national turns, with active-player/alliance priority. Minor-Power
declarations remain attached to land combat movement. Unresolved atomic choices,
chance and strategic naval movement restrict interruption.

Political continuations, alignment snapshots, capital choices, treaty status and
active/dormant identities are part of state, observations and planning identity.
Clone, checkpoint and replay preserve pending work without repeating an award
or advancing another turn. Missing continuation payloads are invalid state.

Sources and implementation:
[profile](../../game_content/rules/gw36_politics_v43.json),
[common events](../../src/politics.cpp),
[warlords/truce](../../src/politics_warlords.cpp),
[influence/recruitment](../../src/politics_influence.cpp), and
[archived source coverage](../archive/milestones/m4/source_coverage.md).
Behavioral fixtures are in [politics](../../tests/politics_tests.cpp),
[warlords](../../tests/politics_warlords_tests.cpp),
[influence](../../tests/politics_influence_tests.cpp) and
[truce combat](../../tests/land_truce_tests.cpp) tests.
