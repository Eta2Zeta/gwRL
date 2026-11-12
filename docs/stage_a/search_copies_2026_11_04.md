# The search keeps a copy of the game at every tree position — 4 November 2026

Until this change, every simulation of a search copied the current position and
played every move of its path again
([earlier record](search_replays_2026_11_04.md)). Now the tree keeps a copy of
the game at each position it holds, and a simulation follows moves already
played by the tree alone. It copies a saved position only to play a new move or
to roll dice there. The search's results are identical to before. In a matched
training batch on the Mac profile, games per hour while playing rose from 152 to
184 and the game processes' CPU per game fell from 217 to 149 seconds, for
0.5 GB more peak memory. The [design document](../design/README.md#47-more-detail-on-the-search)
explains how the search works now; the [evidence file](search_copies_2026_11_04.json)
holds the exact values.

## What changed

- **The search** (`studies/shared/multiplayer_mcts.py`): every `Node` keeps a copy
  of the game (`game`). At a decision, a move that already has a successor leads
  there in the tree, with no engine call: the engine rolls no dice inside a move,
  so a move from a position always reaches the same position. Playing a new move
  or rolling dice copies the saved position first (`_copy`), and a new position
  keeps the copy that reached it (`_reach`). The root keeps a copy of the real
  game, which itself is never played on.
- **The dice.** The engine rolls dice only in `Engine::resolveChance`, from the
  copy's search stream. A new engine call, `cloneForSearchContinuing(source)`
  (`clone_for_search_continuing` in Python and in the campaign adapter), copies a
  position with the dice stream of another copy. A simulation's first copy starts
  its stream from the simulation's seed and every later copy continues the last
  one, so its dice come out exactly as if it had played its whole path on one
  copy.
- **Tests.** Every test environment that searches gained the continuing copy. The
  adapter test that counted legal-move lists spared while replaying now checks
  that each move is played at most once, when it first reaches a position.

## Same results

Commit `0f442f9`'s search (replaying) and this one searched the same 151
positions: every 25th decision with at least two legal moves in three random
eleven-round games (seeds 1951, 1952 and 1953), each with a fresh 64×2 network on
the CPU, 64 simulations, depth 16, root noise and a per-position search seed.
For all 151, the legal moves, visit counts, policy, priors, values, move values
and every simulation's choices, dice outcomes, value and stopping reason were
identical. The trees of 62 of the searches contained dice.

Engine calls over those 151 searches (the counts include one copy per position
that the comparison made itself):

| | Replaying | Saved copies |
| --- | ---: | ---: |
| Moves played | 22,942 | 9,393 |
| Dice rolled | 4,717 | 4,717 |
| Fresh copies (`clone_for_search`) | 9,815 | 9,966 |
| Continuing copies | 0 | 4,446 |
| Search time, network in the same thread | 43.3 s | 29.1 s |

In the round-5 Japanese Combat Movement search of the earlier record, the 64
simulations now play 57 moves instead of 123, with the same 38 dice rolls, and
its tree keeps 77 positions. A saved copy took about 144 KB at a round-6
position, so that tree holds about 11 MB of copies; each tree is dropped after
its decision.

## A matched training batch

Both batches: `--profile mac` (8 game processes of 4 games, coordinator on the
CPU), 32 eleven-round games, fresh networks, 64 simulations, depth 16, 64×2
network, seed 20261104, 50 epochs and a sample share of 0.05. The old batch ran
commit `0f442f9` in a separate checkout, the new one this change.

| | Replaying | Saved copies |
| --- | ---: | ---: |
| Games per hour while playing | 152.3 | 183.5 |
| Decisions per game | 1,066 | 1,022 |
| Decisions per hour | about 162,000 | about 188,000 |
| Network evaluations per game | 54,694 | 52,257 |
| Coordinator busy | 90% | 90% |
| Game-process CPU per game | 217 s | 149 s |
| Coordinator CPU per game | 21 s | 18 s |
| Peak memory | 5.21 GB | 5.71 GB |
| Failed games | 0 | 0 |

The two batches' games are not move for move the same: the shared evaluator's
batches change outputs in the last digits, so games with the same seed drift
apart. Decisions per hour, up 15%, is the fairer rate.

## What this does and does not show

- **Measured:** identical search results on 151 positions; the engine calls,
  times and batch figures above.
- **Inferred:** the coordinator, busy 90% in both batches, now limits this layout;
  further savings in the game processes gain little until it is faster.
- **Open:** memory per copy was measured at one position only; the batch's
  0.5 GB rise fits about 15 MB of copies per game.
