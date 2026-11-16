# Marks held as numbers — 16 November 2026

After zones, nations and unit types, marks: the engine now holds the base of
each mark as its place in its own sorted mark table, keeps a thing's marks in a
flat sorted list with their arguments in one buffer, and writes each mark by
its name as before ([names held as numbers](../../engine/names.md#what-a-mark-is)).
Play is the same at every step of 300 random games and 4 searched games, and the
engine runs fewer instructions than with the earlier changes alone. The
[evidence file](mark_numbers_2026_11_16.json) holds the exact values.

## Setup

`tools/compare_engine_builds.py` played the same seeded games, with the same
settings, as for the earlier changes on this page's day
([zones](zone_numbers_2026_11_16.md), [nations](nation_numbers_2026_11_16.md),
[unit types](unit_type_numbers_2026_11_16.md)), on this change. Its records were
compared with the commit before any of these changes (`9519ea7`), for the same
play, and with the unit types change (`004b028`), for the saving.

- **Random games:** seeds 7000 to 7299, eleven rounds each, four processes. The
  tool counts the instructions the process ran during each engine call.
- **Searched games:** seeds 41 to 44, eleven rounds, 64 simulations a decision
  and depth 16, with networks whose first-layer tables hold random numbers,
  evaluated one position at a time in each process.

Both ran on the M4 Max with the Mac's other work as it was; instructions do not
depend on that load, CPU time does.

## The same play

- **Random games:** the same legal moves, chosen moves and positions at all
  443,974 steps of the 300 games, compared with `9519ea7`.
- **Searched games:** the same 4,985 events and final positions in all 4 games.

A first build of this change failed this check in one random game (seed 7106):
clearing a set of marks left behind the count of the text its erased marks had
used, and a later erase then sized a new buffer from a negative length. The
build measured here has the fix, and a test for it.

## What it saves

| Workload | Unit types as numbers | Marks too | Change |
| --- | ---: | ---: | ---: |
| Random games: instructions to list the moves, per call | 7.77 M | 7.07 M | −9.0% |
| Random games: instructions to play a move, per call | 3.66 M | 3.24 M | −11.5% |
| Random games: instructions to roll the dice, per call | 2.88 M | 2.54 M | −11.8% |
| Four searched games: instructions | 5,845 G | 5,557 G | −4.9% |

Against the engine before any of these changes (`9519ea7`), listing the moves
now runs 29.5% fewer instructions (10.03 M to 7.07 M), playing a move 24.8%
fewer and a searched game 18.1% fewer (6,782 G to 5,557 G).

To compare CPU time under the same load, the unit types build's searched games
ran again between two runs of this change, back to back: the unit types build
took 458.2 s, this change 432.9 s and 438.6 s, 4.9% less. Their instruction
counts held steady: 5,848 G for the unit types build, 5,557 G and 5,559 G for
this change. CPU time varies with the Mac's other work (the load average was
about 9), instructions do not.

## What this does and does not show

- **Measured:** identical play in 300 random and 4 searched games; the
  instructions each engine call and each searched game ran.
- **Not measured:** decisions per hour in a training batch. The game processes'
  share of the work and the coordinator's limit
  ([record](self_play_limits_2026_11_16.md)) decide how much of the saving
  becomes throughput.
- **Not done yet:** facility types, technologies and the units themselves are
  still held by name, and so are the arguments of marks.
