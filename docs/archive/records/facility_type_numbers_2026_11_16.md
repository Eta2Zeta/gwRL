# Facility types and technologies held as numbers — 16 November 2026

After zones, nations, unit types and marks, facility types and technologies:
the engine now holds a facility's type, a construction project's type (a unit
type or a facility type) and each nation's research stages as numbers from the
catalog's tables, and a factory's production and repair capacity read the
nation's completed technologies as a set of bits instead of a full catalog
context ([names held as numbers](../../engine/names.md#the-facility-types-and-technologies-the-rules-name)).
Play is the same at every step of 300 random games and 4 searched games, and
the engine runs fewer instructions than with the earlier changes alone. The
[evidence file](facility_type_numbers_2026_11_16.json) holds the exact values.

## Setup

`tools/compare_engine_builds.py` played the same seeded games, with the same
settings, as for the earlier changes on this page's day
([zones](zone_numbers_2026_11_16.md), [nations](nation_numbers_2026_11_16.md),
[unit types](unit_type_numbers_2026_11_16.md), [marks](mark_numbers_2026_11_16.md)),
on this change. Its records were compared with the commit before any of these
changes (`9519ea7`), for the same play, and with the marks change (`ac26249`),
for the saving.

- **Random games:** seeds 7000 to 7299, eleven rounds each, four processes. The
  tool counts the instructions the process ran during each engine call.
- **Searched games:** seeds 41 to 44, eleven rounds, 64 simulations a decision
  and depth 16, with networks whose first-layer tables hold random numbers,
  evaluated one position at a time in each process.

Both ran on the M4 Max with the Mac's other work as it was; instructions depend
little on that load, CPU time more.

## The same play

- **Random games:** the same legal moves, chosen moves and positions at all
  443,974 steps of the 300 games, compared with `9519ea7`.
- **Searched games:** the same 4,985 events and final positions in all 4 games.

## What it saves

| Workload | Marks as numbers | Facility types and technologies too | Change |
| --- | ---: | ---: | ---: |
| Random games: instructions to list the moves, per call | 7.07 M | 6.08 M | −14.0% |
| Random games: instructions to play a move, per call | 3.24 M | 3.18 M | −1.9% |
| Random games: instructions to roll the dice, per call | 2.54 M | 2.54 M | 0.0% |
| Four searched games: instructions | 5,557 G | 5,334 G | −4.0% |

Against the engine before any of these changes (`9519ea7`), listing the moves
now runs 39.4% fewer instructions (10.03 M to 6.08 M), playing a move 26.2%
fewer and a searched game 21.4% fewer (6,782 G to 5,334 G).

To compare CPU time under the same load, the marks build's searched games ran
again between two runs of this change, back to back, with nothing else of this
study running: the marks build took 407.0 s, this change 395.8 s and 404.0 s,
1.7% less. The two runs of this change differ by 2.1%, so the CPU time saved in
searched games is small and not well resolved: in the profiles below the engine
takes under half of a searched game's samples (48% and 47%), the rest going to
the search in Python and to evaluating the network. Their instruction counts were
5,601 G for the marks build and 5,386 G and 5,321 G for this change: runs of
one build differ by about 1% in instructions, much less than the saving. An
earlier pair, which overlapped a profiling run, gave 2.9% less CPU time. The
load average of the Mac's other work was about 6 to 7.

## Where it comes from

A profile of one searched game on each build (`/usr/bin/sample`, 60 seconds
from 25 seconds after the game began) shows where the saving lies. The build
menu asked each factory's capacity for each row of the build chart, and each
answer built a catalog context: a copy of every mark of the nation and of the
position, in a map keyed by name, only to learn whether the nation had
completed Improved Factories. The check now reads the nation's completed
technologies, a set of bits.

| Share of the engine's samples | Marks as numbers | Facility types and technologies too |
| --- | ---: | ---: |
| The build and research menu (`economyActions`) | 9.1% | 4.3% |
| The factory capacity check of each build-chart row (`canFactoryBuy`) | 5.0% | 0.4% |
| Making a catalog context (`buildContext`) | 5.9% | 1.5% |
| Comparing strings, allocating, copying memory and looking up maps, at the leaf | 45.4% | 43.0% |

A function's share counts every sample with it on the stack, so the rows
overlap; the last row counts the samples whose innermost function does such
work, wherever it was called from. Each profile covers 60 seconds of the same
game, and the faster build gets further in that time, so the positions sampled
differ a little.

## What this does and does not show

- **Measured:** identical play in 300 random and 4 searched games; the
  instructions each engine call and each searched game ran; the CPU time of
  the searched games in a bracketed pair; where a searched game's samples fell
  before and after the change.
- **Measured together:** numbering the names and reading capacity from the
  completed technologies are one change here, with one measurement; the
  profiles show where the samples moved.
- **Not measured:** decisions per hour in a training batch. The game processes'
  share of the work and the coordinator's limit
  ([record](self_play_limits_2026_11_16.md)) decide how much of the saving
  becomes throughput.
- **Not done yet:** the units, facilities and other things themselves are
  still held by name, and so are the arguments of marks.
