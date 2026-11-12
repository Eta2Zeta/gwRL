# Where self-play time goes, and the moves each search plays again — 2 and 4 November 2026

Two measurements of the Mac setup with the 64-wide, two-layer zone network and 64
simulations per decision. On 2 November a whole training batch was profiled:
the one process that evaluates every game's positions (the coordinator) was busy
92% of the time, the game threads waited for it 63% of the time, and the engine
work the game processes did while not waiting was about half applying moves.
On 4 November six single searches were counted: each copies the game 64 times
and plays 75 to 133 moves and up to 38 dice rolls on those copies. The
[design document](../design/README.md#47-more-detail-on-the-search) explains why a
search plays moves again. The [evidence file](search_replays_2026_11_04.json)
holds the exact values.

## 2 November: one profiled training batch

Commit `f41dba6`, `--profile mac` (8 game processes of 4 games, coordinator on
the CPU), 32 eleven-round games, fresh networks, 64 simulations, depth 16.
A sampler recorded every thread's Python stack every 10 ms in every process,
and `ps` read each process's CPU time every 5 s. The batch played 129 games per
hour while playing, against 131 in an unprofiled run of the same settings, so
the sampler cost about 1%.

**CPU.** The game processes used 1.16 cores each, 9.3 in all: their four game
threads run engine code at the same time. The coordinator used 0.84 cores;
together 10.15 of the 11 training cores. That is about 260 CPU-seconds of game
process work per game.

**Game threads** (2,008,785 samples):

| Where | Share of game-thread time |
| --- | ---: |
| Waiting for the coordinator's answer | 62.7% |
| Engine: applying moves (`_apply_native_play`) | 19.1% |
| Engine: listing legal moves | 9.4% |
| Building the network's input | 3.2% |
| Engine: copying the game for a search | 2.6% |
| Engine: dice | 1.0% |
| Engine: decision kinds and keys | 0.6% |
| The search's own Python code | 0.05% |

Applying moves is therefore about half of the time the game threads spent not
waiting. A thread waiting for Python's interpreter lock after an engine call is
counted at that call, so the engine shares are upper bounds of CPU time.

**Coordinator main thread** (69,565 samples): idle 7.5%; the network's forward
pass about 77%, of which the column lookups (`_bag` in
`studies/campaign/neural.py`) were 25.8% of all samples, linear layers 11.3%,
the grouped policy 8.5% and the per-border message line 8.4%; merging positions
into a batch 6.5%; receiving and replying 3.2%.

Both limits are close: at 100% busy the coordinator would answer for about 140
games per hour, and 11 cores give the game processes room for about 141. A
faster coordinator alone would therefore gain little before the cores run out.

## 4 November: what one search plays again

Commit `1396518`, PyTorch 2.11 on the CPU with one thread, a fresh 64×2 network
evaluated in the same thread (no coordinator), 64 simulations, depth 16, search
seed 11. The positions come from one seeded random game (seed 1951, moves drawn
with `random.Random(7)`): every 40th decision from round 2 on with more than
three legal moves. Each count includes every call the search made.

| Round, nation | Decision | Legal moves | Search | Copies | Moves played | Dice rolled | Legal-move lists | Network calls | Playing moves and dice | Share of search | Share without the network |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2, Japan | naval force selection | 14 | 357 ms | 64 | 133 | 0 | 66 | 65 | 189 ms | 53% | 70% |
| 2, KMT | Noncombat Movement | 104 | 195 ms | 64 | 75 | 4 | 66 | 65 | 16 ms | 8% | 19% |
| 3, Japan | Noncombat Movement | 51 | 234 ms | 64 | 78 | 0 | 66 | 65 | 64 ms | 27% | 40% |
| 4, Japan | Combat Movement | 32 | 191 ms | 64 | 105 | 13 | 66 | 65 | 50 ms | 26% | 43% |
| 4, KMT | Noncombat Movement | 74 | 141 ms | 64 | 102 | 0 | 66 | 65 | 18 ms | 13% | 29% |
| 5, Japan | Combat Movement | 24 | 185 ms | 64 | 123 | 38 | 66 | 65 | 82 ms | 44% | 78% |

Copying the game cost 3 to 4 ms for all 64 copies of a search. Playing a move
cost 0.2 to 1.4 ms on average, depending on the move. The trees stayed shallow:
1.2 to 2.5 steps per simulation on average, at most 9.

How deep the simulations went, counting moves and dice rolls:

| Search | Simulations by depth | First moves tried | Visits of the most-visited first moves |
| --- | --- | ---: | --- |
| Round 5, Japan, Combat Movement, 24 legal moves | 1 step: 24; 2: 21; 3: 1; 4: 6; 5: 7; 6: 4; 9: 1 | 24 of 24 | 27, 12, 2, 2, 2, then 1 each |
| Round 2, KMT, Noncombat Movement, 104 legal moves | 1 step: 55; 2: 5; 3: 2; 4: 2 | 55 of 104 | 10, then 1 each |

In the first of these, the 24 one-step simulations were all among the first 31,
and 37 of the 40 deeper simulations started with one of the two most-visited
moves. A move no simulation has tried scores as well as the best result so far,
so untried moves usually come first.

The deepest simulation of the last search copied the game and played five moves,
Japan's `end_phase`, a `land_begin_battle`, a `land_retreat_begin`, a
`land_retreat_unit` and another `land_begin_battle`, with four dice rolls along
the way, before it reached a position the tree had not seen. Every later
simulation that followed the same branch played them all again.

## What this does and does not show

- **Measured:** the counts and times above, for these positions and fresh
  networks.
- **Inferred:** trained networks prefer fewer moves, so their trees go deeper
  and each simulation plays more moves again. Keeping a copy of the game at
  each tree position would let a simulation, choosing its path by the same
  scores, start from the copy saved at the last known position of that path
  instead of the current position. That would save most of this work for the
  cost of the copies' memory; dice on the path would still be rolled.
- **Followed up the same day:** the search now keeps those copies, with
  identical results; see [the search keeps a copy of the game at every tree
  position](search_copies_2026_11_04.md).
