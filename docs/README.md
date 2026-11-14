# gwRL documentation

gwRL teaches three agents, one per alliance, to play the 1936–1941 Japan–China
campaign of the board game Global War 1936. It has three parts:

- **A rules engine**, written in C++, plays the campaign by the printed rules. It
  offers every decision to the alliance entitled to it and rolls the dice.
- **A search**, guided by neural networks, chooses each move.
- **Training** lets the agents play each other and improves the networks from
  those games.

No run has yet shown robust playing strength.

## What to read

| To understand | Read |
| --- | --- |
| How the agents learn: the search, the network's input, the networks and training | [How gwRL learns](design/README.md) |
| How the rules engine works | [The rules engine](engine/README.md) |
| What the campaign is, what the agents play for and what work is open | [Objective, decisions and open work](plans/japan_china_full_rules_plan.md) |
| Which printed rules are implemented, how unclear ones were settled and where the scenario's numbers come from | [Rules and data](rules/README.md) |
| How to train, resume a run and evaluate networks | [Campaign learning guide](../studies/campaign/README.md) |
| How to watch a recorded game | [Campaign Observatory](../web/campaign_viewer/README.md) |
| How to build the code and run its checks | [Build and run](../README.md#build-and-run) |
| What the data files are: maps, catalog, rules profiles and the scenario | [Game content](../game_content/README.md) |
| How the world map was built and what on it is uncertain | [Status](map_audits/full_world/implementation.md), [method](map_audits/full_world/source_method.md), [open items](map_audits/full_world/uncertain.md), [Japan and nearby seas](map_audits/japan_and_nearby_seas.md) |

## How these pages are kept

- **They describe the program as it is now.** A change to the program changes
  the page that describes it, in the same commit.
- **History is kept apart**, in git and in the [archive](archive/README.md): dated
  records of measurements and rule changes, and the delivery reports of the
  engine's build stages. A page here may cite a record as evidence for a number.
  No page here needs the archive to be understood.
- **A test keeps them navigable.** `tests/test_documentation.py` fails when a
  link leads nowhere, when the data or the code cites a missing document, or
  when a dated record sits outside the archive.
