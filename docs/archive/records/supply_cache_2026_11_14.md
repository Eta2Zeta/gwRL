# Supply answers cached while a move is played — 14 November 2026

The 13 November profile found that searching the map for Supply Paths took a sixth
to a quarter of the engine's time, two thirds of it while a move was played,
because playing a move kept no cache of facts about the position
([record](game_processes_2026_11_13.md)). Two changes keep every legal move and
every resulting position the same. Playing a move now keeps the position's cache
open while it only reads the position. And the supply search works out once per
search which naval facilities it may use, instead of at every sea zone it
reaches. In random play the engine spends 42% less CPU playing a move and 3% less
listing the moves. In training batches the game processes used 16% less CPU per
decision, but decisions per hour rose only about 3%: the coordinator that
evaluates the network now limits self-play on the Mac.
The [design document](../../design/README.md#92-running-training-on-the-mac)
describes the game processes; the [evidence file](supply_cache_2026_11_14.json)
holds the exact values.

## What changed

- **The position's cache while a move is played.** Listing a position's legal
  moves keeps a cache of facts about that position open (`PositionScope` in
  `include/game/position_facts.hpp`), such as whether a zone is in supply for a
  nation, how far a ship may sail, or whether a sea zone is blockaded. Each is
  worked out once. Playing a move now opens the same cache for four checks
  that read the position before anything changes, and closes it before the
  position changes:
  - listing a fleet's choices when its order starts or changes (`routeChoices`
    in `src/naval_movement.cpp`);
  - checking the chosen route before the fleet sails (`execute`);
  - keeping only the naval-order choices that can still be completed
    (`forwardNavalOrderDecision`);
  - checking that an economy action is legal (`applyEconomyAction` in
    `src/economy.cpp`).

  Before, a fleet's list of routes asked again, for every route it checked,
  whether each port near the fleet was in supply. The economy's check traced
  each factory's supply once for every kind of unit it listed.
- **The supply search** (`traceSupply` in `src/movement.cpp`). At every sea zone
  it reached, it asked every naval facility whether it was usable and which sea
  zones it opens onto. Neither answer changes during a search, so it now works
  both out once, when it first reaches a sea zone, and keeps the facilities by
  sea zone in their usual order. It also searches inland from a landfall zone
  at most once per search. It visits the same zones in the same order as
  before.

The two versions play the same moves and reach the same positions; the commit
message lists the checks.

## Random play

**Setup.** 60 eleven-round games, seeds 7000 to 7059. Each move was drawn at
random from the legal moves, except that ending the phase was chosen with a
probability of 2%, 5% or 10%, by seed, so that games reach their later rounds.
Four versions ran at the same time, 3 processes each, on the Mac. Each engine
call's CPU time was measured on its own thread.

| Version | Listing the moves, per call | Playing a move, per call | Engine CPU, 60 games |
| --- | ---: | ---: | ---: |
| Before (commit `82859a2`) | 971 µs | 1,058 µs | 162.8 s |
| Cache open while a move is played | 989 µs | 637 µs | 131.4 s |
| Both changes, as kept | 941 µs | 609 µs | 125.3 s |
| Both, plus one supply search per nation (not kept) | 887 µs | 611 µs | 121.3 s |

Rolling dice took about 360 µs per call in every version.

**Native samples.** macOS's `sample` recorded one process playing random games
for 40 seconds, at 1 ms intervals. Of the samples inside the two engine calls,
the supply search held 31.6% before, 13.4% with the cache open while a move is
played, and 9.7% with both changes. Enumerating naval routes held 27.8%, 17.1%
and 15.7%, and listing the economy's options 18.6%, 14.9% and 15.1%.

**Search-driven games.** Five complete games (seeds 41 to 45) with 64
simulations per decision and networks given small random weights, evaluated one
position at a time on one thread, used 1,206 CPU-seconds before and 994 after,
18% less, network included.

## Training batches

**Setup.** Five batches of the Mac profile, alternating the code before and
after: 32 complete eleven-round games each with learning, 8 game processes of 4
games and one coordinator evaluating on the CPU, 64 simulations, depth 16, network
64×2, the settings of the [12 November batches](coordinator_lookups_2026_11_12.md).
Two before batches did not have the machine to themselves. Another session's test
suite ran during the first minutes of the first. The fifth ran an hour after the
others, while another project's web server, the window server and a macOS
malware scan were busy. In samples every 15 seconds of the six busiest processes,
those outside the batch used on average 108% of a core during the fifth, against
5% to 16% during the others. Those two batches are shown but not compared.

| Batch, in the order run | Before | After | Before | After | Before |
| --- | ---: | ---: | ---: | ---: | ---: |
| Machine | busy at first | quiet | quiet | quiet | busy |
| Decisions per hour while playing | 236,675 | 253,849 | 246,157 | 254,479 | 169,343 |
| Decisions per game | 1,104 | 1,054 | 1,088 | 1,050 | 1,054 |
| Game-process CPU per decision | 145.6 ms | 116.8 ms | 139.3 ms | 117.0 ms | 154.6 ms |
| Coordinator CPU per decision | 13.9 ms | 13.3 ms | 13.9 ms | 13.3 ms | 16.7 ms |
| Coordinator busy | 89% | 90% | 90% | 89% | 86% |
| Positions per network call | 3.51 | 4.09 | 3.55 | 4.11 | 3.54 |
| Cores in use, game processes and coordinator | 10.5 | 9.2 | 10.5 | 9.2 | 8.1 |
| Peak memory, sampled every 5 s | 5.91 GB | 5.61 GB | 6.66 GB | 7.42 GB | 5.22 GB |
| Failed games | 0 | 0 | 0 | 0 | 0 |

Against the one before batch on a quiet machine, the after batches used 16% less
game-process CPU per decision, 116.9 ms instead of 139.3 ms. Per game the saving
was 19%, but the number of decisions in a game varies from batch to batch: the
shared evaluator merges positions differently from run to run, which changes the
rounding of the network's outputs and so the games. Decisions per hour while
playing were 3.3% higher, 254,164 on average against 246,157. Runs of the same
code differed by 5.5% on 12 November, so that rise is not established.

The coordinator was busy about 90% of the time in all three. The faster game
processes left more positions waiting for each of its calls, 4.1 instead of 3.55,
and its busy time per position fell by 4%, from 260 µs to 250 µs. The game
processes and the coordinator together used 9.2 cores instead of 10.5.

## Not kept: one supply search per nation

Each destination's own search explores the map in the same order whatever the
destination is, and only stops when it finds it. So one search that does not
stop finds every zone in supply for a nation at once, with the same answers.
Used whenever the cache is open, it listed the moves 54 µs faster per call and
played them no faster (the last row of the table above), 3% of the engine's CPU
in all. It was not kept: it needs a second copy of the search that would have to
stay in step with the first. Without the facility table it was slower than the
per-zone searches it replaced, because it explores the whole map, while most
questions are answered close to home.

## What this does and does not show

- **Measured:** the engine CPU of the same random games on each version, their
  native samples, five search-driven games, and five training batches, of which
  one before and two after had the machine to themselves.
- **Inferred:** the coordinator now limits the Mac profile. It is busy about 90%
  of the time while about 1.8 of the 11 cores sit idle. Further engine work
  therefore saves CPU but adds little throughput until the coordinator answers
  faster, its calls grow, or a second coordinator shares the work. At the after
  batches' CPU per decision, 11 busy cores would carry about 20% more decisions
  per hour.
- **Open:** whether the 3% rise in decisions per hour is real; another before
  batch on a quiet machine would tell. The checks in the commit message found
  the play unchanged in random and search-driven games from the first round to
  the end of the eleventh, which need not reach every rule.
