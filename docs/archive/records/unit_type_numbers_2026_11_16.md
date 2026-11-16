# Unit types held as numbers — 16 November 2026

After zones and nations, unit types and unit classes: the engine now holds each
unit's type as its place in the sorted list of the catalog's unit types, keeps
the catalog's unit definitions in that order, and holds each unit type's
classes as a set of class numbers
([names held as numbers](../../engine/names.md)). Play is the same at every
step of 300 random games and 4 searched games, and the engine runs fewer
instructions than with zones and nations alone. The
[evidence file](unit_type_numbers_2026_11_16.json) holds the exact values.

## Setup

`tools/compare_engine_builds.py` played the same seeded games, with the same
settings, as for [zones held as numbers](zone_numbers_2026_11_16.md) and
[nations held as numbers](nation_numbers_2026_11_16.md), on this change. Its
records were compared with the commit before any of these changes (`9519ea7`),
for the same play, and with the nations change (`57d50f9`), for the saving.

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

## What it saves

| Workload | Nations as numbers | Unit types too | Change |
| --- | ---: | ---: | ---: |
| Random games: instructions to list the moves, per call | 8.15 M | 7.77 M | −4.7% |
| Random games: instructions to play a move, per call | 3.72 M | 3.66 M | −1.6% |
| Random games: instructions to roll the dice, per call | 2.89 M | 2.88 M | −0.3% |
| Four searched games: instructions | 5,996 G | 5,845 G | −2.5% |

Against the engine before any of these changes (`9519ea7`), listing the moves
now runs 22.5% fewer instructions (10.03 M to 7.77 M) and a searched game 13.8%
fewer (6,782 G to 5,845 G).

To compare CPU time under the same load, the nations build's searched games ran
again between two runs of this change, back to back: the nations build took
462.0 s, this change 443.0 s and 445.5 s, 3.8% less. Their instruction counts
held steady: 5,994 G for the nations build, 5,845 G and 5,848 G for this
change. CPU time varies with the Mac's other work, instructions do not.

## What this does and does not show

- **Measured:** identical play in 300 random and 4 searched games; the
  instructions each engine call and each searched game ran.
- **Not measured:** decisions per hour in a training batch. The game processes'
  share of the work and the coordinator's limit
  ([record](self_play_limits_2026_11_16.md)) decide how much of the saving
  becomes throughput.
- **Not done yet:** facility types, technologies, the marks on units, nations
  and territories, and the units themselves are still held by name.
