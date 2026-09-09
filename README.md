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

## Generated build files

Files ending in `.o` are compiler-generated object files. Each contains one compiled piece of the C++ source; the linker combines them into an executable or extension. They are safe to delete and regenerate.

The `build/` directory, `.so` Python extension modules, `.egg-info/` packaging metadata, and `.DS_Store` Finder metadata are generated locally as well. They are ignored by Git and should not be committed.
