# The rules engine

The engine plays the 1936–1941 Japan–China campaign of Global War 1936 by the
printed rules. It is written in C++ (`include/game/`, `src/`), and Python reaches
it as `gwrl_cpp.CampaignEnv`. It offers every decision to the alliance entitled
to it, rolls the dice itself and never chooses for a player.

**These pages are being rewritten by subject.** Until a subject has its page,
its row links the delivery report of the build stage that produced the module.
Those reports date from October 2026. Rule changes since then are in the
[rule clarifications](../../game_content/rules/clarifications.md).

| Subject | Interface | Described so far in |
| --- | --- | --- |
| The campaign: scope, map, nations, setup and scoring | `game_content/scenarios/japan_china_1936` | [Approved scenario decisions](../plans/japan_china_full_rules_plan.md#approved-scenario-decisions), [M0 report](../archive/milestones/m0/README.md), [M1 report](../archive/milestones/m1/README.md) |
| The engine's state, decisions, dice, turns and saved games | `include/game/campaign.hpp` | [M2 report](../archive/milestones/m2/README.md), [M10 report](../archive/milestones/m10/README.md) |
| Unit, facility and technology catalog | `include/game/catalog.hpp` | [M3 report](../archive/milestones/m3/README.md) |
| Politics, warlords and national turns | `include/game/politics.hpp` | [M4 report](../archive/milestones/m4/README.md) |
| Movement and supply | `include/game/movement.hpp` | [M5 report](../archive/milestones/m5/README.md) |
| Economy, production, construction and research | `include/game/economy.hpp` | [M6 report](../archive/milestones/m6/README.md) |
| Land combat | `include/game/land_combat.hpp` | [M7 report](../archive/milestones/m7/README.md) |
| Air operations | `include/game/air.hpp` | [M8 report](../archive/milestones/m8/README.md) |
| Naval operations | `include/game/naval.hpp` | [M9 report](../archive/milestones/m9/README.md) |
| The environment the agents play in | `include/game/campaign_env.hpp`, `studies/shared/campaign_adapter.py` | [M11 report](../archive/milestones/m11/README.md), [How gwRL learns, section 2](../design/README.md#2-the-game-as-the-learner-sees-it) |

Which printed rules apply, and where the scenario's numbers come from, is in
[Rules and data](../rules/README.md).
