# gwRL

`gwRL` is a C++20 Global War 1936 simulation core with Python bindings and reinforcement-learning studies. The 1936–1941 China campaign has completed its M0–M12 implementation gates, including two full campaign traces, vector search, neural self-play, exact checkpoint resume and held-out evaluation. The latest Stage A run completed sixty three-round self-play games and paired held-out evaluation; Japanese expansion was not demonstrated and robust playing strength remains unestablished. Public tiny/composition study environments use the same campaign engine; their historical result archives predate that migration.

## Start here

- [Stage A learning results](/Users/home/Desktop/gwRL/docs/stage_a/README.md): completed-episode training, paired held-out results and earlier pilots.
- [Native neural-input compiler](/Users/home/Desktop/gwRL/docs/stage_a/neural_input_2026_10_24.md): complete feature graphs in C++, exact numerical parity and matched performance checks.
- [AI order construction](/Users/home/Desktop/gwRL/docs/stage_a/action_interface_2026_10_24.md): forward-only naval orders and bounded configuration/permission choices, with separate replay compatibility.
- [Three-round learning results](/Users/home/Desktop/gwRL/docs/stage_a/three_round_2026_10_25_results.md): sixty completed games, no held-out Japanese expansion, saved continuation and measured checkpoint overhead.
- [Campaign learning](/Users/home/Desktop/gwRL/studies/campaign/README.md): foreground training, interrupt/resume, evaluation and profiling; [M12 verification](/Users/home/Desktop/gwRL/docs/m12/README.md).
- [Campaign Observatory](/Users/home/Desktop/gwRL/web/campaign_viewer/README.md): local map viewer, self-play replay, optional live following and recorded MCTS decisions.
- [Composition study](/Users/home/Desktop/gwRL/studies/composition/README.md): army-composition self-play, training code and its completed results.
- [Mini Japan, two turns](/Users/home/Desktop/gwRL/studies/mini_japan_two_turn/README.md): neural MCTS trainer, search diagnostic and completed results.
- [Full-campaign plan](/Users/home/Desktop/gwRL/docs/plans/japan_china_full_rules_plan.md) and [M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md): the approved 1936–1941 campaign and milestone gates.
- [M2 engine foundation](/Users/home/Desktop/gwRL/docs/m2/README.md): actual campaign setup loading, shared state, validated actions, turn/reaction timing, dice, replay and verification.
- [M3 catalog](/Users/home/Desktop/gwRL/docs/m3/README.md): unit/facility values, technologies, national build charts, availability and source verification.
- [M4 politics](/Users/home/Desktop/gwRL/docs/m4/README.md): warlords, influence/recruitment, truce, evolution, timed declarations, capture notifications and surrender.
- [M5 movement and logistics](/Users/home/Desktop/gwRL/docs/m5/README.md) and [M6 economy](/Users/home/Desktop/gwRL/docs/m6/README.md): routes, supply, production, income, construction, research and lend-lease.
- [M7 land combat](/Users/home/Desktop/gwRL/docs/m7/README.md) and [M8 air operations](/Users/home/Desktop/gwRL/docs/m8/README.md): component gates complete, including adopted artillery city bombardment.
- [M9 naval operations](/Users/home/Desktop/gwRL/docs/m9/README.md) and [M10 campaign integration](/Users/home/Desktop/gwRL/docs/m10/README.md): source review, complete campaign replays and the 143-row coverage ledger. RCL-014 and RCL-015 are provisionally adopted.
- [M11 multi-agent API and search](/Users/home/Desktop/gwRL/docs/m11/README.md): explicit decision owners and chance, entity observations, wealth vectors and exact-oracle search checks.
- [Game content](/Users/home/Desktop/gwRL/game_content/README.md): maps, rules and canonical scenarios.
- [Rule clarifications](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md): unclear official rules and adopted project interpretations, separate from scenario choices.

## Repository layout

```text
game_content/
  catalog/       Shared unit, facility, technology and national build definitions
  maps/          Global map data and source map images
  rules/         Official PDFs and the project rule-clarification register
  scenarios/     Simulator setups and manual battle fixtures
include/game/    C++ public headers and game rules
src/             C++ implementation and Python bindings
studies/
  campaign/      Entity-graph models, batched search, self-play and evaluation
  composition/   Trainer, search and preserved composition results
  mini_japan_two_turn/  Trainer, search, tools and results
  shared/        Neural helpers, explicit campaign adapter and vector MCTS
tests/           Data/search checks and C++ engine/combat regressions
docs/            Map audits, implementation plan and milestone/checkpoint records
tools/           Game-content generation utilities
web/             Browser-based board visualization
output/          Disposable C++ simulator/debug exports only
```

Each study has a `README.md` and a fresh ignored `runs/` destination. Historical
composition/mini-Japan results remain in their preserved `results/` directories;
current campaign verification records live in `docs/m12/`. See the [study index](/Users/home/Desktop/gwRL/studies/README.md)
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
./.venv/bin/python -m studies.campaign.run --help
./.venv/bin/python -m studies.mini_japan_two_turn.train --help
./.venv/bin/python -m studies.composition.train --help
```

## Campaign model and checks

`gwrl_cpp.CampaignEnv` uses the shared political, movement, economy, land, air and
naval rules. Dice, defender casualties, retreat and other reactions remain explicit
choices of their entitled player. The campaign adapter also exposes declaration
offers and passes. See M11 for a small executable search example.

The frozen regional profile excludes outside nations and named campaign-disabled
mechanics; its coverage ledger records those exclusions. The old deterministic
`BattleResolver` remains for historical prototype regressions. Current public study
environments use the campaign engine, and archived models/results retain their
original feature schemas and historical meaning.

Run the focused C++ regressions and all Python data/search/organization checks:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
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
