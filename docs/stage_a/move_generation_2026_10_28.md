# Faster move generation with identical move lists — 28 October 2026

Legal-move generation was the largest engine cost: 30% of a production-like
self-play search thread, and more in later rounds. Most of it was not rule
logic but repeated work: rereading the scenario's map JSON, rescanning every
unit on the board for each question, and copying the whole position to test a
single candidate move. This removes that repetition without changing a single
legal choice. The [evidence JSON](move_generation_2026_10_28.json) records the
workloads, per-round timings, self-play comparison and provenance; raw outputs
remain under `studies/campaign/runs/move-generation-2026-10-28/`.

**Result: move lists are generated 7.3 times faster (16.5 to 2.25 ms per
position) on 11,161 positions from eight seeded games, every list identical in
content and order. Production-like self-play games run 1.39 times faster and
are move-for-move identical.**

## How identity was checked

`tools/check_move_generation.py` plays seeded random games and records a digest
of every decision position's complete menu: each legal action and interrupt,
with its identifier and parameters, in order. The games choose by menu index,
so any difference changes the game from that point on. A check replays the same
games, compares every digest and saves the first differing position.

The reference used the unchanged engine: eight games, seeds 1951–1958, up to
eleven rounds and 3,000 decisions each, ending a phase 5% more often than
uniform choice so games reach later rounds. Each of the three rounds of changes
reproduced all 11,161 positions. New C++ tests also compare the map table with
the map JSON, SHA-256 with padding-boundary vectors, and the directly written
state text with the JSON-tree text on 400 positions of a random game.

## What was slow

Sampled profiles of the unchanged engine:

| Inside move-list generation, random games | Share |
| --- | ---: |
| Naval-order completion checks (`validateNavalRoute`) | 52% |
| Copying positions for one-move probes, then destroying them | 26% + 27% |
| of which copying and destroying the event history | 19% + 19% |
| Joint aircraft landing plan | 16% |
| Naval movement allowance | 14% |
| Supply tracing | 12.5% |
| Naval operations: air, port and amphibious attacks | 12% |

About half of all samples were memory allocation and freeing, and 11% string
comparison. In production-like self-play, move generation took 30% of the
search thread and stepping the engine another 14%, of which 9% was the
position fingerprint (canonical JSON of the whole state, hashed).

## Changes

- **Map table.** Each frozen scenario keeps its nodes, source-order neighbor
  lists and first edge to each neighbor. Map reads that parsed JSON and copied
  neighbor names now borrow those lists. Fixtures without a complete map keep
  reading the JSON.
- **Per-position answers.** While the engine generates a position's menus, or a
  rule check reads a fixed copy of it, helpers remember answers for that exact
  state object: enemy fighter zones per nation, blockades, supply, naval
  movement allowance and the joint landing plan. Any other state is computed
  directly, so nothing is reused after a change.
- **Shared event history.** Copies of a position share its recorded events
  instead of copying them, which every engine step, search clone and rule
  probe did.
- **Fewer probes.** A naval force without carriers, aircraft or aircraft cargo
  cannot change any input of the landing plan, so its routes check the plan on
  the position itself rather than on a copy. One breadth-first search per
  aircraft finds the path to every naval air-attack target; it reproduces what
  one search per target found.
- **Cheaper checks.** Loading tests run only for ships that can carry cargo
  (about 99 × 99 calls before). Deck capacity is computed only when an aircraft
  has no land spot, and the search for land spots stops at the first one. An
  aircraft's patrol range is computed once per menu. Hot catalog stats read the
  state's flags in place instead of copying all of them.
- **Allocation hygiene.** Saves and planning keys write the canonical text
  directly instead of building a JSON tree first, SHA-256 reads its input
  without copying it, the current nation is returned without a copy, and
  `require` helpers build their message only on failure.

## Measurements

Move-list time per position on the eight reference games (eight processes):

| Decision | Positions | Unchanged | Round 1 | Round 2 | Round 3 | Speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Combat movement | 3,922 | 37.3 ms | 9.66 ms | 5.65 ms | 4.69 ms | 8.0× |
| Non-combat movement | 1,910 | 17.5 ms | 6.38 ms | 2.64 ms | 2.41 ms | 7.3× |
| Production | 1,161 | 2.22 ms | 1.53 ms | 1.26 ms | 1.30 ms | 1.7× |
| Combat | 1,079 | 1.63 ms | 1.81 ms | 0.19 ms | 0.19 ms | 8.6× |
| All positions | 11,161 | 16.5 ms | 4.87 ms | 2.63 ms | 2.25 ms | 7.3× |

Round 1 added the map table, per-position answers, shared history and fewer
probes; round 2 the cheaper checks, direct state text and allocation hygiene;
round 3 in-place catalog stats. Combat positions include fingerprints of
positions reached after dice, which explains their round-2 gain.

Production-like self-play, ten processes, seeds 1951–1960, hidden size 64,
two message layers, 16,384 token buckets, 64 simulations, depth cap 16,
three-round games. The unchanged engine's times for the same seeds come from
the [ten-worker queue run](worker_queue_2026_10_28.md).

| Same ten games | Unchanged | Faster engine | Change |
| --- | ---: | ---: | ---: |
| Summed game time | 8,636 s | 6,223 s | 1.39× faster |
| Engine and search outside the network | 4,668 s | 1,791 s | 2.61× faster |
| Network evaluation, including input preparation | 3,908 s | 4,376 s | 12% slower |
| Engine share of search time | 54% | 29% | |
| Identical games (actions, final state and dice) | | 10 of 10 | |

Per game the gain ranged from 1.26 to 1.50 times. The ten games finished in
726.9 s, 49.5 games per hour, though one game per process leaves a long tail;
the thirty-game queue run gave 34.9 at the old speed. Peak charged memory was
8.49 GB.

Network evaluation did the same work but took 12% longer. With the engine
faster, more processes run network arithmetic at the same moment, and each
five-core cluster shares its cache and, likely, its matrix unit. The network is
now 71% of search time.

## A rules defect found by the check

Seed 1955 stops at position 561 with the engine error "Landing beyond range",
with and without these changes. After a naval battle, a Japanese Fighter on
maritime air patrol (patrol range 1, no movement left) is offered landing in
Korea and on a carrier one zone away. The offered spots use the patrol range;
applying the landing measures reach with the aircraft's remaining movement, so
any landing outside its own zone throws. An ordinary end of patrol instead
raises movement to the patrol range and clears the patrol flags. Either the
post-battle landing should do the same, or the menu should offer only spots
within remaining movement. Which one is a rules decision; until it is made, a
long game that reaches this position fails.

## Still slow

Inside move-list generation, round 3 profiles show:

- **Copies for one-move probes, about 40%** (20.7% to create, 20.1% to
  destroy). Naval air attacks, air moves, carrier routes and landing-plan
  preservation each copy the whole position to test one move. A landing plan
  that accepts one hypothetical aircraft move, or positions that share
  unchanged parts between copies, would remove most of it.
- **Naval air attacks, 27%**, mostly those copies and their landing plans.
- **Naval-order completion, 17%**, which still validates each route from its
  start rather than extending a valid prefix.

In self-play the network is now the largest cost. Batching evaluations from
all game processes on the otherwise idle GPU is the next large lever. At this
network size the [production benchmark](production_benchmark_2026_10_28.md)
measured 13.0 ms per position on one CPU core and 5.5 ms at batch 32 on the
GPU, both including about 4.5 ms of CPU input preparation, and before the
contention above.
