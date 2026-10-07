# gwRL

`gwRL` is a C++20 Global War 1936 simulation core with Python bindings and reinforcement-learning studies. The current playable models are simplified; the larger full-rules China campaign is still being specified.

## Start here

- [Composition study](/Users/home/Desktop/gwRL/studies/composition/README.md): army-composition self-play, training code and its completed results.
- [Mini Japan, two turns](/Users/home/Desktop/gwRL/studies/mini_japan_two_turn/README.md): neural MCTS trainer, search diagnostic and completed results.
- [Full-campaign plan](/Users/home/Desktop/gwRL/docs/plans/japan_china_full_rules_plan.md) and [M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md): the future 1936–1941 campaign, not a runnable training environment yet.
- [Game content](/Users/home/Desktop/gwRL/game_content/README.md): maps, rules and canonical scenarios.
- [Rule clarifications](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md): unclear official rules and adopted project interpretations, separate from scenario choices.

## Repository layout

```text
game_content/
  maps/          Global map data and source map images
  rules/         Official PDFs and the project rule-clarification register
  scenarios/     Simulator setups and manual battle fixtures
include/game/    C++ public headers and game rules
src/             C++ implementation and Python bindings
studies/
  composition/   Trainer, search and preserved composition results
  mini_japan_two_turn/  Trainer, search, tools and results
  shared/        Shared neural model and path helpers
tests/           Data, search and organization checks; C++ combat regressions
docs/            Map audits, implementation plan and M0 specification
tools/           Game-content generation utilities
web/             Browser-based board visualization
output/          Disposable C++ simulator/debug exports only
```

Each study has a `README.md`, preserved `results/`, and a fresh `runs/` destination
for new output. See the [study index](/Users/home/Desktop/gwRL/studies/README.md)
for the cleanup record and result-retention conventions. Old results preserve
their original bytes and historical engine behavior; organizing them does not
revalidate those results against today's rules.

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

Training entry points (run from the repository root):

```sh
./.venv/bin/python -m studies.mini_japan_two_turn.train --help
./.venv/bin/python -m studies.composition.train --help
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

Run the focused C++ regressions and all Python data/search/organization checks:

```sh
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build --output-on-failure
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

After editing C++ headers, rebuild the Python bindings before training:

```sh
./.venv/bin/python setup.py build_ext --inplace --force
```

## Generated build files

Files ending in `.o` are compiler-generated object files. Each contains one compiled piece of the C++ source; the linker combines them into an executable or extension. They are safe to delete and regenerate.

The `build/` directory, `.so` Python extension modules, `.egg-info/` packaging metadata, and `.DS_Store` Finder metadata are generated locally as well. They are ignored by Git and should not be committed.
