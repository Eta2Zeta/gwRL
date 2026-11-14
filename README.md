# gwRL

`gwRL` is a C++20 Global War 1936 simulation core with Python bindings, and
reinforcement learning for the 1936–1941 Japan–China campaign. The engine
implements the campaign's rules. Training is by self-play: each of the three
alliances chooses its moves by a search guided by its own network, which reads
a fixed [encoding of the position](docs/design/README.md#5-how-a-decision-becomes-numbers).
No run has yet shown robust playing strength.

## Start here

The [documentation guide](docs/README.md) says what to read for each purpose.
The main pages:

- [How gwRL learns](docs/design/README.md): the search, the network's input,
  the networks and training, built up from their parts.
- [The rules engine](docs/engine/README.md): how the game is played in code.
- [Rules and data](docs/rules/README.md): which printed rules are implemented,
  and where the scenario's numbers come from.
- [Campaign learning guide](studies/campaign/README.md): training, resuming,
  evaluation and the measured settings.
- [Campaign Observatory](web/campaign_viewer/README.md): a local map viewer for
  recorded games and search decisions.
- [Game content](game_content/README.md): maps, the catalog, the rules profiles
  and the scenario.

History is kept apart in the [archive](docs/archive/README.md): dated records of
measurements and rule changes, the engine's build-stage reports, and what the
earlier, removed work found.

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
| `docs/` | The documentation: its guide, the learning design, the engine, rules and data, and the archive |
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
offers and passes.

The frozen regional profile excludes outside nations and named campaign-disabled
mechanics; the [rules ledger](docs/rules/core_rules_ledger.md) records which rules
apply.

## Generated build files

Files ending in `.o` are compiler-generated object files. Each contains one compiled piece of the C++ source; the linker combines them into an executable or extension. They are safe to delete and regenerate.

The `build/` directory, `.so` Python extension modules, `.egg-info/` packaging metadata, and `.DS_Store` Finder metadata are generated locally as well. They are ignored by Git and should not be committed.
