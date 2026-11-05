# gwRL

`gwRL` is a C++20 Global War 1936 simulation core with Python bindings, and
reinforcement learning for the 1936–1941 Japan–China campaign. The campaign's
rules are implemented (milestones M0–M11). It trains by self-play: a search for
each of the three alliances, guided by a network that reads a fixed
[zone encoding](docs/stage_a/zone_encoding_2026_11_02.md) of the position. No run
has yet shown robust playing strength.

## Start here

- [How gwRL learns](docs/design/README.md): the central design document, from
  the big picture down to the network's input, in plain words.
- [Campaign learning](studies/campaign/README.md): training, resume, evaluation,
  recorded games and the measured settings.
- [Campaign Observatory](web/campaign_viewer/README.md): local map viewer for
  self-play replays and recorded search decisions.
- [Zone encoding](docs/stage_a/zone_encoding_2026_11_02.md) and
  [zone network](docs/stage_a/zone_network_2026_11_02.md): the network's fixed
  input, 37 zones answering fixed questions, its completeness checks and the
  network that reads it.
- [Decision, rules and training review](docs/stage_a/decision_review_2026_10_31.md):
  the objective rewards a passive Japan; removable decisions; flat search targets
  on large menus.
- Rule changes for training: [finished battles clear themselves](docs/stage_a/battle_clearing_2026_10_31.md),
  [aircraft move once per turn](docs/stage_a/aircraft_single_move_2026_11_01.md)
  and [Combat Movement lists only moves that start a combat](docs/stage_a/combat_movement_combats_only_2026_11_01.md).
- [AI order construction](docs/stage_a/action_interface_2026_10_24.md):
  forward-only naval orders and bounded configuration and permission choices.
- [Project history](docs/history.md): what the removed prototype, studies,
  experiments and audits found, and the commit that keeps them.
- [Full-campaign plan](docs/plans/japan_china_full_rules_plan.md) and
  [M0 review](docs/m0/README.md): the approved 1936–1941 campaign.
- Engine modules: [M2 foundation](docs/m2/README.md), [M3 catalog](docs/m3/README.md),
  [M4 politics](docs/m4/README.md), [M5 movement](docs/m5/README.md),
  [M6 economy](docs/m6/README.md), [M7 land combat](docs/m7/README.md),
  [M8 air](docs/m8/README.md), [M9 naval](docs/m9/README.md),
  [M10 integration](docs/m10/README.md) and [M11 decisions and search](docs/m11/README.md).
- [Game content](game_content/README.md): maps, rules and the campaign scenario;
  [rule clarifications](game_content/rules/clarifications.md): unclear official
  rules and the project's adopted readings.

## Repository layout

| Folder | Contents |
| --- | --- |
| `game_content/catalog/` | Shared unit, facility, technology and national build definitions |
| `game_content/maps/` | Global map data and its authoring files |
| `game_content/rules/` | Official PDFs, rules profiles and the clarification register |
| `game_content/scenarios/` | The Japan–China 1936 campaign scenario |
| `include/game/` | C++ public headers and game rules |
| `src/` | C++ implementation and Python bindings |
| `studies/campaign/` | Zone network, search, self-play, training and evaluation |
| `studies/shared/` | Campaign adapter, multi-player search and frozen JSON |
| `tests/` | C++ engine suites and Python checks |
| `docs/` | Design document, rules ledger, engine module pages, Stage A records and history |
| `tools/` | Training supervisor, recording, checks, benchmarks and map builders |
| `web/` | Campaign Observatory |

New runs write into ignored `runs/` folders.

## Build and run

Build the engine and its C++ test suites:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

Build the Python extension in the project virtual environment, then run the
Python checks:

```sh
./.venv/bin/python -m pip install -e .
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

After editing C++ headers, rebuild the Python bindings before training:

```sh
./.venv/bin/python setup.py build_ext --inplace --force
```

Training entry point, from the repository root:

```sh
./.venv/bin/python -m studies.campaign.run --help
```

## Campaign model

`gwrl_cpp.CampaignEnv` uses the shared political, movement, economy, land, air and
naval rules. Dice, defender casualties, retreat and other reactions remain explicit
choices of their entitled player. The campaign adapter also exposes declaration
offers and passes. See M11 for a small executable search example.

The frozen regional profile excludes outside nations and named campaign-disabled
mechanics; the [rules ledger](docs/m0/core_rules_ledger.md) records which rules
apply.

## Generated build files

Files ending in `.o` are compiler-generated object files. Each contains one compiled piece of the C++ source; the linker combines them into an executable or extension. They are safe to delete and regenerate.

The `build/` directory, `.so` Python extension modules, `.egg-info/` packaging metadata, and `.DS_Store` Finder metadata are generated locally as well. They are ignored by Git and should not be committed.
