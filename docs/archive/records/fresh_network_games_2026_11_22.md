# The first games of a fresh network under choice D — 22 November 2026

The training run started on 22 November 2026 (`studies/campaign/runs/training-2026-11-22`,
commit `3153079`) began from a fresh network, its weights as initialized, before
any network update, and played as the owner chose in Q-016 (choice D): a
decision kept as a training sample is searched with 256 simulations and
exploration noise, any other with 16, and self-play draws its move from the
visit shares in game round 1 only, playing the most visited action after it.
Its first five network updates followed 80 games. This record compares them
with the first two network updates of the training run of 19 to 21 November
2026 (`studies/campaign/runs/training-2026-11-19`), 504 games, which also began
from a fresh network but searched every decision with 64 simulations and drew
every move from the visit shares. It then follows the run of 22 November
through its first 69 network updates, 1,104 games in 2.9 hours of play. The
[evidence file](fresh_network_games_2026_11_22.json) holds the counts, read
from each run's `manifest.json`.

## The first games

| Per game | Choice D, fresh network | First games of the training run of 19 to 21 November |
| --- | ---: | ---: |
| Decisions, median (quartiles) | 502 (411 to 607) | 1,048 (968 to 1,128) |
| Share of actions that end a phase | 39% | 18% |
| Land-unit moves (`movement_route`) | 53.5 | 160.2 |
| Land battles begun | 7.8 | 44.2 |
| Purchases | 49.7 | 72.7 |
| Mean final scores: Axis, Allies, Comintern | 37.2, −59.5, −105.0 | 35.5, −56.8, −96.3 |

## As the network trained

The run of 22 November, in blocks of its network updates; each network update
followed 16 games:

| Network updates | Games | Decisions, median | Share of actions that end a phase | Land-unit moves | Land battles begun | Mean final scores: Axis, Allies, Comintern |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 5 | 80 | 502 | 39% | 53.5 | 7.8 | 37.2, −59.5, −105.0 |
| 6 to 20 | 240 | 616 | 32% | 89.4 | 7.9 | 40.4, −60.3, −103.1 |
| 21 to 40 | 320 | 617 | 29% | 157.9 | 10.1 | 42.5, −60.9, −102.0 |
| 41 to 55 | 240 | 708 | 27% | 215.9 | 10.8 | 45.7, −62.9, −100.6 |
| 56 to 69 | 224 | 694 | 28% | 201.0 | 10.3 | 47.5, −64.1, −100.1 |

The training run of 19 to 21 November, which drew every move, for comparison;
each of its network updates followed 252 games:

| Network updates | Games | Decisions, median | Share of actions that end a phase | Land-unit moves | Land battles begun | Mean final scores: Axis, Allies, Comintern |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 2, in its first part | 504 | 1,048 | 18% | 160.2 | 44.2 | 35.5, −56.8, −96.3 |
| 11 to 13, in its first part | 756 | 1,442 | 13% | 265.3 | 52.1 | 29.4, −55.8, −87.3 |
| 36 to 38, the last of its fourth part | 756 | 1,475 | 13% | 261.1 | 55.0 | 31.3, −55.6, −88.4 |

## What this shows and does not show

It shows that a fresh network under choice D first played games half as long as
the first games of the training run of 19 to 21 November, with twice the share
of actions that end a phase, a third of the land-unit moves and a sixth of the
land battles, for about the same final scores. And it shows that the run's play
widened as its network trained: in network updates 56 to 69 its games had a
median of 694 decisions, 38% more than at first; 28% of their actions ended a
phase, against 39%; and they moved a land unit 201 times a game, nearly four times as often as at first and more than the 160 of the first games of the training
run of 19 to 21 November. Their land battles rose only from 7.8 to about 10 a
game, against 44 to 55 in the games of the training run of 19 to 21 November
shown above. The Axis's mean final score rose from 37.2 to 47.5 and the
Allies' fell from −59.5 to −64.1.

Why the first games were narrow, inferred and not tested: at the decisions
searched with 16 simulations, which are 99 of every 100, the simulations mostly
visit 16 legal actions once each, so the move is chosen by the rules for ties
(`most_visited_index` in `studies/shared/multiplayer_mcts.py`): the action with
the best average result for the alliance choosing, then the one with the higher
prior. A fresh network gives every state the same values, and each action the
same prior in every game
([section 6.9 of the design document](../../design/README.md#69-the-whole-network)),
so its choices repeat from game to game, and they often ended the phase. As the
network trains, its values and priors come to differ between states, and its
priors steer the 16 simulations toward the actions its policy has learned
(inferred).

It does not show whether the network will learn to fight more, or whether
fewer battles are worse play: the training run of 19 to 21 November drew every
move from the visit shares, which also plays actions the search valued little,
attacks among them. Nor does it show how often a game process would crash in
these games; the six crashes all happened while the search freed its tree's
game copies in the longer games of the training run of 19 to 21 November
(inferred to matter, not measured).

These first games raised the question whether the run should start instead
from the newest network of the training run of 19 to 21 November (Q-017). It
was withdrawn on 22 November 2026, after the run's play had widened
([answered](../../questions.md#answered)).
