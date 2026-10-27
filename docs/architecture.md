# Architecture

For current progress and reading paths, start with the [project guide](README.md).
This page describes the stable boundaries between the game and the learner.

## Game data and rules

`game_content/` contains the authored world map, shared catalog, official sources,
rule clarifications and scenario definitions. The approved regional scenario is
an explicit projection of that map: 31 land zones and six sea zones. Its ordinary
horizon is eleven complete rounds, July 1936 through July 1941. Short training
curricula use the same setup and rules with an explicit shorter endpoint.

`include/game/` declares public C++ types and interfaces; `src/` supplies their
implementation and Python bindings. The complete CPU engine owns authoritative
state, legal choices, rule transitions, dice distributions, reactions, accounting
and replay. A nation and its units keep their identities even when an alliance
agent controls their choices. Mongolia retains its own identity and uses the
USSR calendar slot under direct Comintern control.

Player choices and chance are separate transitions. Casualties, retreat and other
reactions belong to the entitled player; the current calendar player does not
automatically choose for everyone. The engine validates external or stale actions.
The training path reuses authoritative choices for an unchanged complete decision
state instead of regenerating them for selection, observation and execution.

## Search and neural input

The [campaign adapter](../studies/shared/campaign_adapter.py) adds explicit
opportunities to declare war and pass. Its pending offers are part of the planning
state, along with the board, phase, acting faction, reactions and rules. A board
picture alone is insufficient to identify a cached decision.

The input compiler turns the observable state, scenario context and legal actions
into numerical entity graphs. Native C++ exports supply the training path;
immutable map/catalog features and unchanged decision inputs are reused in bounded
caches. External or unsupported snapshots retain a Python/JSON fallback. Exact
recovery state also contains execution history and random state that the network
does not receive as predictive features.

Three policy/value networks represent Axis, Allies and Comintern. The policy
scores the actual legal menu. Each value head predicts all three wealth-gap
returns. The approved return is an alliance's wealth minus the other two
alliances' combined wealth; intermediate rewards are zero. The
[scenario contract](reference/scenario.md) identifies the authoritative
scoring definitions. This objective is not the official global victory condition.

The stochastic [vector MCTS](../studies/shared/multiplayer_mcts.py) lets each
decision owner optimize its own value component. Dice follow the engine's
probabilities. A simulation explores a cloned position, stopping at a leaf,
terminal, cycle or depth cap; it is usually shorter than a whole game. Depth
counts simulated action or chance transitions. Nonterminal leaves use a network
estimate; actual endings use the engine's exact terminal return.

Independent game searches run in separate workers. Simulations inside each search
are sequential; ready roots share neural inference batches. Independent C++
environments execute native work concurrently, while overlapping operations on
one environment are protected. Python conversion and callbacks still require
Python's interpreter lock.

## Collection, learning and recovery

A collection batch freezes all three networks so that its games use consistent
policies. In complete-episode mode, all games in that batch reach their configured
real endpoint before their samples enter replay and Adam updates the networks.
An execution cutoff saves unfinished work without inventing terminal results.
The separate bounded-segment mode allows explicitly marked bootstrap targets.
CLI defaults select a short smoke, not complete-episode training.

Replay retains positions, choices, search policy targets and observed or explicitly
marked estimated returns. Recovery snapshots also retain optimizer moments,
live/frozen weights, unfinished boards and pending samples, replay, counters,
random generators and compatibility fingerprints. Model-only exports are smaller
and sufficient for evaluation; they do not restore the complete learning process.
Learned caches require a matching frozen model version and are bypassed during
training. See the [workflow](../studies/campaign/README.md) for exact resume rules.

## CPU and GPU boundary

The [backend interface](../studies/campaign/backends/protocol.py) separates decision
inspection, state transfer, choices, chance, cloning and terminal scoring. The
[registry](../studies/campaign/backends/__init__.py) currently registers the complete
CPU backend only. Resident Apple Metal components are experimental implementations
of selected services and transitions, with explicit unsupported cases.

`--neural-device mps` moves neural tensor work to the Apple GPU independently of
engine execution. It does not select a GPU game engine or GPU MCTS. The
[GPU architecture](gpu/architecture.md) describes implemented components, conformance
contracts and remaining integration work. Operation timings and whole-game
throughput must be measured separately.
