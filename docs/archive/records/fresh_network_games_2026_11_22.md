# The first games of a fresh network under choice D — 22 November 2026

The training run started on 22 November 2026 (`studies/campaign/runs/training-2026-11-22`,
commit `3153079`) began from a fresh network and played as the owner chose in
Q-016 (choice D): a decision kept as a training sample is searched with 256
simulations and exploration noise, any other with 16, and self-play draws its
move from the visit shares in game round 1 only, playing the most visited
action after it. Its first five network updates followed 80 games. This record
compares them with the first two network updates of the long run of 19 November
2026, 504 games, which also began from a fresh network but searched every
decision with 64 simulations and drew every move from the visit shares. The
[evidence file](fresh_network_games_2026_11_22.json) holds the counts, read from
each run's `manifest.json`.

| Per game | Choice D, fresh network | The long run's first games |
| --- | ---: | ---: |
| Decisions, median (quartiles) | 502 (411 to 607) | 1,048 (968 to 1,128) |
| Share of actions that end a phase | 39% | 18% |
| Movement routes | 53.5 | 160.2 |
| Land battles begun | 7.8 | 44.2 |
| Purchases | 49.7 | 72.7 |
| Mean final scores: Axis, Allies, Comintern | 37.2, −59.5, −105.0 | 35.5, −56.8, −96.3 |

## What this shows and does not show

It shows that a fresh network under choice D plays games half as long as the
long run's first games, with twice the share of actions that end a phase, a
third of the movement routes and a sixth of the land battles, for about the
same final scores.

Why, inferred and not tested: at the decisions searched with 16 simulations,
which are 99 of every 100, the simulations mostly visit 16 legal actions once
each, so the most visited action is chosen by the rule for ties: the best
average result for the alliance choosing (`most_visited_index` in
`studies/shared/multiplayer_mcts.py`). For a fresh network that result comes
from its value function as initialized, a fixed function of the position, the
same in every game, and it often favours ending the phase.

It does not show whether training moves the network off these games: five
network updates is the start of a run. Nor does it show how often a game
process would crash in such games; the six crashes all happened while the
search freed its tree's game copies in the long run's longer games (inferred to
matter, not measured).
