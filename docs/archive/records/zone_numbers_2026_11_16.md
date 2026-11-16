# Zones held as numbers — 16 November 2026

The morning's diagnosis found that 59% of the engine's time went to comparing
names, allocating memory, looking up maps and copying memory, because the
position kept its zones, units, facilities and nations keyed by name
([record](self_play_limits_2026_11_16.md#inside-the-engine)). This change holds
zones as numbers: a zone's place in the sorted list of the map's zone names
([names held as numbers](../../engine/names.md)). Play is the same at every step
of 300 random games and 4 searched games, and the engine runs fewer instructions.
The [evidence file](zone_numbers_2026_11_16.json) holds the exact values.

## Setup

`tools/compare_engine_builds.py` played the same seeded games on two builds:
the commit before this change (`9519ea7`) and this change.

- **Random games:** seeds 7000 to 7299, eleven rounds each, four processes. The
  tool times each engine call and counts the instructions the process ran
  during it.
- **Searched games:** seeds 41 to 44, eleven rounds, 64 simulations a decision
  and depth 16, with networks whose first-layer tables hold random numbers,
  evaluated one position at a time in each process.

Both ran on the M4 Max with the Mac's other work as it was; instructions do not
depend on that load, CPU time does.

## The same play

- **Random games:** the same legal moves, chosen moves and positions at all
  443,974 steps of the 300 games.
- **Searched games:** the same 4,985 events and final positions in all 4 games.
- The C++ suites (27 of 27, with a new one for the name tables) and the Python
  suite (467 tests, 6 skipped) pass.

## What it saves

| Workload | Before | Zones as numbers | Change |
| --- | ---: | ---: | ---: |
| Random games: instructions to list the moves, per call | 10.03 M | 8.73 M | −13.0% |
| Random games: instructions to play a move, per call | 4.31 M | 3.91 M | −9.3% |
| Random games: instructions to roll the dice, per call | 3.20 M | 3.04 M | −5.0% |
| Four searched games: instructions | 6,782 G | 6,292 G | −7.2% |

A first run of the same code gave 6,248 G (−7.9%) for the searched games; the
two runs played the same games, so the 0.7% between them is the spread of this
measure. The searched games' CPU time fell from 555 s to 487 s; CPU time varies
with the Mac's other work, instructions do not.

## What this does and does not show

- **Measured:** identical play in 300 random and 4 searched games; the
  instructions each engine call and each searched game ran.
- **Not measured:** decisions per hour in a training batch. The game processes'
  share of the work and the coordinator's limit
  ([record](self_play_limits_2026_11_16.md)) decide how much of the saving
  becomes throughput.
- **Not done yet:** nations, unit types, the marks on units and the units
  themselves are still held by name.
