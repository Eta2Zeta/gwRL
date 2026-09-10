# gwRL

`gwRL` is a C++20 Global War 1936 simulation core with Python bindings and reinforcement-learning experiments. The current playable model focuses on a simplified China theater, while the repository also contains a larger manually transcribed world map for future expansion.

## Repository layout

```text
game_content/
  maps/          Global map data and source map images
  rules/         Rulebooks and extracted rule text
  scenarios/     Simulator setups and manual battle fixtures
include/game/    C++ public headers and game rules
src/             C++ implementation and Python bindings
python/          Training, MCTS, policy models, and analysis tools
tools/           Game-content generation utilities
web/             Browser-based board visualization
output/          Training summaries, traces, metrics, and checkpoints
```

See [game_content/README.md](game_content/README.md) for details about the maps, rules, and scenarios.

## Build and run

Build the standalone simulator out of source:

```sh
cmake -S . -B build
cmake --build build
./build/gw_simplified
```

Build the Python extension in the project virtual environment:

```sh
./.venv/bin/python -m pip install -e .
```

Example training commands:

```sh
./.venv/bin/python python/train_japan_policy_torch.py
./.venv/bin/python python/train_japan_q_learning.py
./.venv/bin/python python/train_composition_alpha_zero.py
```

## Combat model and checks

The Japan map MDP and composition environment both use `BattleResolver` in
`include/game/battle_resolver.hpp`. Combat remains deterministic: strength divided
by 12 produces fractional casualties, with integer survivors assigned at the end
for the map. Composition rewards use the fractional surviving force.

Artillery fires first in the opening round. Pairing gives infantry-class units
(Infantry and Marines) +1 attack only; infantry or vehicles can prevent the
artillery's unpaired -1 attack/defense penalty. Pairing is recalculated from
survivors, with infantry paired first. Mechanized Infantry is a vehicle with base
attack 3, so it prevents the artillery penalty without receiving a support bonus.

Tank Destroyer target-selection hits choose vehicles; any excess becomes ordinary
hits after eligible vehicles run out. Targeted and ordinary casualties still fire
in that round. Casualty choices remain automatic: ordinary hits remove units with
the lowest adjusted base combat value first, while targeted hits remove eligible
vehicles with the highest value first (unit reward value breaks ties).

These are still simplified battles, not a complete rulebook implementation:
terrain/city rules, retreat decisions, and scenario purchase/availability limits
remain simplified. Saved training results from before combat-rule changes describe
the earlier environment and need reevaluation under the current rules.

Run the focused C++ regressions and existing Python search tests:

```sh
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build --output-on-failure
PYTHONPATH=python ./.venv/bin/python -m unittest discover -s python/tests
```

After editing C++ headers, rebuild the Python bindings before training:

```sh
./.venv/bin/python setup.py build_ext --inplace --force
```

## Generated build files

Files ending in `.o` are compiler-generated object files. Each contains one compiled piece of the C++ source; the linker combines them into an executable or extension. They are safe to delete and regenerate.

The `build/` directory, `.so` Python extension modules, `.egg-info/` packaging metadata, and `.DS_Store` Finder metadata are generated locally as well. They are ignored by Git and should not be committed.
