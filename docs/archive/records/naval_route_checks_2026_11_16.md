# The naval-route and landing checks — 16 November 2026

The morning's profile found that enumerating and checking naval routes took a
quarter of the engine's time in a training batch, and aircraft landing plans a
seventh ([record](self_play_limits_2026_11_16.md#inside-the-engine)). A profile
of a searched game shows what those checks do. Most of their time goes to work
done afresh for each new position, and for each copy of it a landing check makes:
the copy, its own landing plan, and the supply and movement questions that the
copy answers again without any cache. One exact saving was found and kept. A
ship's movement allowance is now worked out once per position and starting zone,
for all its destinations. Play is the same in 300 random games and four searched
games. It saves 1.0% of a searched game's instructions; one other change was
tried and saved little. The [evidence file](naval_route_checks_2026_11_16.json)
holds the exact values.

## Where the checks spend their time

**Setup.** One process played searched game 41 to its end: eleven rounds, 64
simulations a decision, depth 16, the 64×2 network with random-filled first-layer
tables evaluated one position at a time in the same process. macOS's `sample`
recorded its stacks for 50 seconds. The network's own work is part of these
samples, unlike in a training batch's game processes.

Checking naval routes (`validateNavalRoute` in `src/naval_movement.cpp`) took
9.8% of the samples, about a sixth of the engine's. It is called for every route
a force could sail, mostly by `forwardNavalOrderActions` (6.8%), which offers a
ship as the start of an order only if some route for it can be completed, and by
`routeChoices`, which lists a force's routes. Inside the route checks, counting
each function with everything it calls, so that the rows overlap:

| Inside the route checks | Share |
| --- | ---: |
| The landing check at each stop: a copy of the position with the force moved there, and its landing plan | 56% |
| Movement allowances, on the position and on the copies | 56% |
| Supply searches | 44% |
| The landing plan on the copies (`airLandingsKept`) | 33% |
| Where each carrier could still end its move, on the copies (`navalEndZones`) | 22% |
| Making and freeing the copies | 23% |

A copy is a new position, so the cache of facts kept while a position's moves are
listed (`PositionScope`) does not cover it. Each copy works out again every
carrier's reach, its allowance and the supply it depends on.

## What changed

A ship's movement allowance (`allowance` in `src/naval_movement.cpp`) was kept in
the position's cache by ship, destination, starting zone and kind of movement.
Only one part of it depends on the destination: the zone that a Japanese
Surprise Attack names gains one point of movement in Combat Movement. The rest,
the ship's type and damage, a friendly major port at its starting zone, and
supply there, is now worked out once per ship and starting zone
(`allowanceBeforeSurprise`). The destination's point is then added
(`surpriseBonus`). The allowance is the same number as before.

## The same play

`tools/compare_engine_builds.py`, new with this record, plays the same seeded
games on two builds and compares them step by step.

- **Random games:** 300 eleven-round games, seeds 7000 to 7299, gave the same
  legal moves, chosen moves and positions at all 443,974 steps as the code before
  this morning's changes (`557b03e`).
- **Searched games:** games 41 to 44, eleven rounds, 64 simulations, with the
  same random-filled networks evaluated one position at a time, gave the same
  4,985 events and final positions as the previous commit (`61c8e31`).
- The C++ suites (26 of 26) and the Python suite (467 tests, 6 skipped) pass.

## What it saves

| Workload | Previous commit | This change | Change |
| --- | ---: | ---: | ---: |
| Random games: instructions to list the moves, per call | 10.29 M | 10.02 M | −2.6% |
| Random games: instructions to play a move, per call | 4.40 M | 4.31 M | −2.0% |
| Four searched games: instructions | 6,863 G | 6,793 G | −1.0% |

One training batch of the Mac profile ran a variant with both changes tried
here. Its game processes ran 1,106 million instructions per decision, against
1,124 and 1,102 in the previous commit's batches, a difference smaller than
that between those two.

## Tried and not kept

- **Remembering the landing answer.** Two routes that stop in the same zone
  after the same number of zones leave the same copy, so the copy's answer could
  be kept for the rest of the position. It saved 0.24% of the searched games'
  instructions beyond the allowance change: a force seldom reaches a zone by two
  routes of the same length within its few points of movement.

## What this does and does not show

- **Measured:** where the route checks spend their time in one searched game;
  identical play in 300 random and 4 searched games; the instructions saved.
- **Inferred:** exact savings inside these checks are used up. What they still
  cost is work done again for every new position the search reaches, and for
  every copy a landing check makes. Larger cuts need another design: answers about
  supply kept across positions whose supply cannot differ, a landing check that
  needs no copy of the whole position, or names held as numbers rather than
  strings throughout the engine
  ([record](self_play_limits_2026_11_16.md#inside-the-engine)).
- **Not shown:** how much each of those designs would save; each is a larger
  change to the engine.
