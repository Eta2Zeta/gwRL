# Nations held as numbers — 16 November 2026

After zones, nations: the engine now holds each nation as its place in the
sorted list of the definition's faction names
([names held as numbers](../../engine/names.md)). Play is the same at every step
of 300 random games and 4 searched games, and the engine runs fewer instructions
than with zones alone. The [evidence file](nation_numbers_2026_11_16.json) holds
the exact values.

## Setup

`tools/compare_engine_builds.py` played the same seeded games, with the same
settings, as for [zones held as numbers](zone_numbers_2026_11_16.md), on this
change. Its records were compared with two earlier ones: the commit before
either change (`9519ea7`), for the same play, and the zones change (`b6667b4`),
for the saving.

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

| Workload | Zones as numbers | Nations too | Change |
| --- | ---: | ---: | ---: |
| Random games: instructions to list the moves, per call | 8.73 M | 8.15 M | −6.6% |
| Random games: instructions to play a move, per call | 3.91 M | 3.72 M | −4.9% |
| Random games: instructions to roll the dice, per call | 3.04 M | 2.89 M | −4.9% |
| Four searched games: instructions | 6,292 G | 5,996 G | −4.7% |

Against the engine before either change (`9519ea7`), listing the moves now runs
18.7% fewer instructions (10.03 M to 8.15 M) and a searched game 11.6% fewer
(6,782 G to 5,996 G).

The zones build's count for the searched games varies a little from run to run:
6,292 G, 6,248 G and 6,240 G in three runs, while this change ran 5,996 G and
5,994 G. So the searched games' saving over zones is 3.9% to 4.7%. The last of
those zones runs was made between this change's two, back to back, to compare
CPU time under the same load: the zones build took 509.6 s, this change 485.3 s
and 491.0 s, 4.2% less. CPU time varies with the Mac's other work (the load
average was about 9), instructions do not.

## What this does and does not show

- **Measured:** identical play in 300 random and 4 searched games; the
  instructions each engine call and each searched game ran.
- **Not measured:** decisions per hour in a training batch. The game processes'
  share of the work and the coordinator's limit
  ([record](self_play_limits_2026_11_16.md)) decide how much of the saving
  becomes throughput.
- **Not done yet:** unit types, the marks on units, nations and territories, and
  the units themselves are still held by name.
