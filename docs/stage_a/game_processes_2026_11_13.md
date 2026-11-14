# Where the game processes' time goes — 13 November 2026

Since the fused column lookup, training on the Mac uses nearly all of its 11
cores, and the game processes do about 90% of the CPU work
([record](coordinator_lookups_2026_11_12.md)). This profile of a real training
batch shows where that work goes. Two engine calls take about a millisecond each:
playing a move and listing a position's legal moves. Together they are two thirds
of the game threads' CPU. Inside the engine, a few rule checks dominate: tracing
supply paths, enumerating naval routes, the economy's options and aircraft landing
plans. Playing a move also redoes much of what the position's move list already
worked out, and without its cache. The
[evidence file](game_processes_2026_11_13.json) holds the exact values.

## How it was measured

`tools/profile_game_process_cpu.py`, rewritten for this measurement, runs a
training batch through the supervisor exactly as a training run does. In every
game process, each game thread charges its own CPU time (`time.thread_time_ns`) to
the innermost instrumented call it is in: an engine call, the engine's encoding of
a position, the adapter's Python layer, the search's own Python, readying and
sending a request to the coordinator, or the rest of the game loop. Each game also
records its wall time and how long its thread waited for the coordinator's
answers. macOS's `/usr/bin/sample` recorded the native call stacks of one game
process for 20 seconds at 150 seconds into the batch, and of another at 360
seconds.

Settings as in the 12 November matched batches: commit `bb350e5`, `--profile mac`
(8 game processes of 4 games, coordinator on the CPU, PyTorch 2.14), 32 eleven-round
games, fresh 64×2 networks, 64 simulations, depth 16, seed 20261104. The batch
played 197.5 games per hour while playing, against 207.6 and 214.9 without the
accounts. The accounts' own cost, estimated from their 0.63 µs per instrumented
call, was 1.6 of 161 CPU-seconds per game.

## The game threads' CPU

All 32 games finished. Per game: 1,070 decisions, 160 dice rolls and 54,812
network evaluations, and 161.3 CPU-seconds in its game thread, 151 ms per decision.
The game processes' own CPU totals were 161.5 seconds per game, so their other
threads used almost nothing.

| Where | CPU per game | Share | Calls per game | Each call |
| --- | ---: | ---: | ---: | ---: |
| Engine: playing a move (`apply_action`) | 52.7 s | 32.7% | 53,275 | 989 µs |
| Engine: listing the legal moves (`legal_actions`) | 51.3 s | 31.8% | 54,781 | 937 µs |
| Engine: encoding a position for the network (`zone_input`, its arrays) | 13.3 s | 8.2% | 55,032 | 233 µs |
| The search's own Python | 8.5 s | 5.2% | 1,070 | 7.9 ms |
| The adapter's Python layer | 7.8 s | 4.8% | | |
| Engine: rolling dice (`resolve_chance`) | 6.4 s | 4.0% | 22,148 | 289 µs |
| Engine: copying the game for the search | 7.0 s | 4.3% | 75,270 | 77 to 98 µs |
| The rest of the game loop, creating the game 1.5 s | 5.9 s | 3.7% | | |
| Readying, sending and receiving requests | 5.8 s | 3.6% | 54,812 | |
| Other engine calls (planning keys, decision kinds, interrupts) | 2.7 s | 1.7% | | |

Of the evaluations, 10,689 per game (19.5%) were of positions inside a search with
only one legal move. A search whose own position has one legal move plays it
without evaluating, but positions it reaches are evaluated whatever their menu.

## A game thread's wall time

A game thread took 509 seconds per game: 32% running on its own CPU, 58% waiting
for the coordinator's answers and 11% neither, mostly waiting for the Python
interpreter lock its process's four game threads share. A request waited 5.4 ms on
average, while the coordinator spent 0.30 ms of work per evaluation; it was busy
89% of the time.

## Inside the engine

In the two native samples, 84% and 88% of the time a game process ran on a CPU was
inside the engine, including freeing engine objects. Shares of that engine time:

| Engine work | Share at 150 s | Share at 360 s |
| --- | ---: | ---: |
| Listing the legal moves (`Engine::actionMenu`) | 33.9% | 45.3% |
| Playing a move (`Engine::step`) | 35.2% | 32.2% |
| Encoding positions (`encodeZoneInput`) | 9.7% | 9.1% |
| Rolling dice (`Engine::resolveChance`) | 7.6% | 3.6% |
| Copying the game for the search | 7.2% | 4.9% |

Across those calls, these functions took the most, each counted with everything it
calls, so the rows overlap:

| Function | What it does | At 150 s | At 360 s | Of it, while playing a move |
| --- | --- | ---: | ---: | ---: |
| `traceSupply`, through `inSupply` | Searches the map for a nation's Supply Path to a zone | 16.1% | 22.9% | 83%, 65% |
| `visitNavalRoutes`, `validateNavalRoute` | Enumerates and checks every route a naval force could sail | 12.3% | 24.3% | 63%, 50% |
| `economyActions` | Lists the economy's options, with each factory's capacity | 19.5% | 9.7% | 64%, 68% |
| `solveReachablePlan` | Finds a landing plan for every aircraft in flight | 3.6% | 10.0% | 3%, 6% |
| `State::State` | Copies a whole position | 7.0% | 8.0% | 3%, 7% |
| `State::planningKey` | Writes the position out and hashes it | 8.4% | 6.3% | 60%, 76%; the rest rolling dice |
| `State::validate` | Checks the position's consistency after a change | 5.7% | 4.2% | 64%, 75%; the rest rolling dice |
| `memcmp` | Compares strings: names used as keys | 19.3% | 21.6% | 44%, 35% |
| `operator new` | Allocates memory | 13.4% | 12.6% | 26%, 26% |

**Why playing a move costs as much as listing the moves.** Listing a position's
moves runs with a cache of facts about that position open (`PositionScope` in
`Engine::actionMenu`), so each supply question is answered once per nation and
zone. Playing a move runs without one. `allowanceNow`, which works out how far a
ship may sail, loops over every naval facility and asks `inSupply` for each one
near the ship's start; in the 360-second sample 82% of the supply searches came from
it. Applying a naval move also enumerates the routes again (`routeChoices` calls
`visitNavalRoutes`), and applying an economy action rebuilds the economy's whole
list of options (`applyEconomyAction` calls `economyActions`): work the position's
move list has already done.

**Names as keys.** The engine keys units, zones, facilities and marks by name and
looks catalog entries up by name, so comparing strings and allocating memory run
through almost every function. The largest named callers of `memcmp` were JSON
lookups (`json::Value::find`), state validation, catalog lookups (`Catalog::unit`),
`buildContext` and `blockadedNow`.

## What this does and does not show

- **Measured:** the CPU accounts of 32 complete games and two 20-second native
  samples, at the settings above.
- **Inferred:** at 161 CPU-seconds per game in the game processes and about 15 in
  the coordinator, 11 fully used cores would play about 225 games per hour; the
  unprofiled batches played 207 to 215. Large gains therefore need less engine work
  per move. Three changes would keep every legal move and every resulting position
  the same:
  1. answer supply questions from a cache while a move is played, before the
     position changes, or find all of a nation's supplied zones in one search per
     position;
  2. let playing a naval or economy move reuse what the position's move list
     worked out, instead of enumerating routes and the economy's options again;
  3. compare numbers instead of names, by numbering zones, units and types: the
     broadest of the three.

  Supply tracing alone was a sixth to a quarter of engine time in the samples, and
  most of it happened while playing moves; how much each change saves is not
  measured. Once the game processes are faster, the coordinator would have to keep
  up too: its calls would carry more positions, which costs less per position.
- **Not an optimization:** not evaluating positions with one legal move inside a
  search would cut 19.5% of the evaluations, but it changes what the search does,
  so it needs a strength check.
- **Open:** the native samples cover two game processes for 20 seconds each, at
  two moments of the games; other phases may weigh differently. The profiled batch
  played 5% to 8% fewer games per hour than the unprofiled ones, more than the
  estimated 1% cost of the accounts; runs of the same code differ by 5.5%.
