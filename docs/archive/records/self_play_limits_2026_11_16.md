# What limits self-play within nine cores — 16 November 2026

Since 15 November the Mac profile runs 6 game processes of 4 games and one
coordinator, within the owner's allowance of 9 cores
([record](nine_core_layouts_2026_11_15.md)). Two profiled training batches show
what limits it now. The training kept its 9 cores busy, and the game processes
did 90% of that work. In the game threads, 80% of the CPU time went to the
engine and its encoding of positions for the network. Listing a position's legal
moves is now the largest part, about a millisecond a call. Inside the engine,
59% of the time went to comparing names, allocating memory, looking up maps and
copying memory, and 41% to the rules' own logic. By rule check, enumerating and
checking naval routes took the most, then aircraft landing plans. The
coordinator was busy about 90% of the time, close to its own limit, so a faster
engine alone can buy only part of what it saves. The Mac's other work kept about
4 cores busy during both batches. The training then did not fit on the 10
performance cores, and macOS ran 27% to 29% of the game processes' CPU time on
the slower efficiency cores. The [design document](../../design/README.md#92-running-training-on-the-mac)
describes the training on the Mac; the [evidence file](self_play_limits_2026_11_16.json)
holds the exact values.

## Setup

- **Code:** `main` at `fade51b`; the engine and the trainer are as at `e62e01b`.
- **Batch:** the matched-batch command of the earlier speed records, with the Mac
  profile: 6 game processes of 4 games, the coordinator evaluating the 64×2
  network on the CPU, 24 eleven-round games, 64 simulations, depth 16, 5% of
  decisions kept, 50 training steps, seed 20261104. The evidence file gives the
  commands.
- **Two batches, one after the other.** The first ran under
  `tools/profile_game_process_cpu.py`, which charges each game thread's CPU time
  to the innermost engine or Python call it is in, and took 20 seconds of native
  call stacks (macOS's `/usr/bin/sample`, every millisecond) from one game
  process at 120, 240 and 360 seconds. The second ran under
  `tools/profile_coordinator.py`, which times each step of the coordinator's
  rounds, and sampled the coordinator at 150 and 330 seconds. The first batch's
  accounts cost about 1% of the game threads' CPU, and its game processes ran
  slower; its speed is not compared, only its shares.
- **Load:** `tools/log_process_load.py`, new with this record, sampled every
  process every 5 seconds. For the training's processes it also read macOS's own
  accounting (`proc_pid_rusage`): CPU time on all cores and on the performance
  cores, the time a process was ready to run but waiting for a core, and its
  instructions and cycles on each kind of core.
- **The Mac was not quiet.** Other work kept a median of 4.8 cores busy during
  the first batch and 4.0 during the second: another project's web development
  server, the window server, chat and browser apps, and updaters.

## The two batches

| | Game-process profile | Coordinator profile |
| --- | ---: | ---: |
| Decisions per hour while playing | 174,880 | 213,644 |
| Decisions; evaluations per decision | 26,339; 51.7 | 26,356; 51.7 |
| Positions per coordinator round | 4.09 | 4.44 |
| Coordinator busy | 87% | 90% |
| Training's load, cores, mean of half-minute windows | 7.7 | 9.1 |
| Other work, cores, median window | 4.8 | 4.0 |
| Game processes' CPU per decision | 141.1 ms | 133.0 ms |
| The same in performance-core time | 118.9 ms | 110.3 ms |
| Coordinator's CPU per decision | 16.2 ms | 14.4 ms |
| Game processes' CPU time on performance cores | 72.5% | 70.8% |
| Game processes' wait for a core, per second of CPU | 0.75 s | 0.51 s |
| Coordinator's CPU time on performance cores | 90.9% | 95.6% |
| Coordinator's wait for a core, per second of CPU | 0.21 s | 0.10 s |
| Instructions per decision: game processes, coordinator | 1,286 M, 191 M | 1,266 M, 190 M |
| Peak memory, sampled | 4.4 GB | 5.6 GB |

A second on an efficiency core did about 42% of the work of a second on a
performance core in the game processes: 2.6 GHz against 3.8 GHz, and 1.8
instructions per cycle against 2.8 to 3.0. The performance-core time row counts
efficiency-core seconds at that rate. Counted that way, the game processes did
110 ms of work per decision, against 117 ms of CPU per decision on a quiet Mac on
14 November ([record](supply_cache_2026_11_14.md#training-batches)): the engine
has not become noticeably slower since, and storing each nation's income after every move
(since commit `0a66178`) takes 0.4% of the engine's time.

## A game thread's time

In the game-process profile a game took 1,097 decisions and 56,779 network
evaluations, and its game thread 155.0 CPU-seconds, 141 ms per decision.

| Where | Share of game-thread CPU | Calls per game | Each call |
| --- | ---: | ---: | ---: |
| Engine: listing the legal moves (`legal_actions`) | 36.7% | 56,957 | 1,000 µs |
| Engine: playing a move (`apply_action`) | 22.5% | 55,904 | 623 µs |
| Engine: encoding a position for the network (`zone_input`, its arrays) | 9.7% | 56,999 | 255 µs |
| The search's own Python | 6.2% | 1,097 | 8.8 ms |
| The adapter's Python layer | 5.7% | | |
| Engine: copying the game for the search | 4.7% | 74,921 | 84 to 102 µs |
| The rest of the game loop | 4.5% | | |
| Readying, sending and receiving requests | 4.1% | 56,779 | |
| Engine: rolling dice (`resolve_chance`) | 3.9% | 19,339 | 310 µs |
| Other engine calls (planning keys, interrupts, decision kinds) | 1.9% | | |

A game thread spent 31% of its wall time on its own CPU, 52% waiting for the
coordinator's answers, and 17% otherwise, mostly waiting for Python's
interpreter lock or for a core. The native samples of the game threads split
the same way: 45% waiting for the coordinator, 12% waiting for the interpreter
lock, 34% in the engine and 8% in Python.

Of the evaluations, 9,692 per game (17.1%) were of positions inside a search with
one legal move, and 222 of the 1,097 decisions had one legal move and were played
without a search.

## Inside the engine

On-CPU native samples inside engine calls, 48,339 from three game processes, by
the kind of work in the innermost function:

| Kind of work | Share |
| --- | ---: |
| The rules' own logic | 40.8% |
| Comparing strings | 22.5% |
| Allocating and freeing memory | 18.9% |
| Looking up maps and hash tables | 9.2% |
| Copying and filling memory | 6.8% |
| Reading the scenario's JSON | 1.7% |

The position keeps its zones, units, facilities and nations in maps keyed by
name (`State` in `include/game/campaign.hpp`), and a move or a rule check names
them as strings. So comparing names and allocating strings, map nodes and copies
takes more of the engine's time than the rules themselves.

By rule check, counting a function's samples with everything it calls, so that
the rows overlap:

| Rule check | Share |
| --- | ---: |
| Naval routes: enumerating and validating them | 25.6% |
| Aircraft landing plans | 14.7% |
| Encoding positions for the network | 11.4% |
| Naval orders that can still be completed | 10.9% |
| The economy's menu | 10.7% |
| Movement allowances | 10.7% |
| Supply Paths | 9.3% |
| Copying the whole position | 9.0% |
| Factory capacity | 8.8% |
| The planning key | 8.5% |
| Checking the whole position | 6.0% |
| Political refresh | 1.9% |
| Combat dice | 1.3% |
| Stored income | 0.4% |

Three costs come from how a move is checked and recorded:

- **Playing an economy move** lists the whole economy menu again and compares
  every option with the move (`applyEconomyAction` in `src/economy.cpp`), though
  `Engine::step` (`src/campaign_runtime.cpp`) has already found the move in the
  position's menu. Listing the economy menu took 22% of the samples inside
  playing a move.
- **Checking a naval route** copies the whole position
  (`validateNavalRoute`). Of the samples copying whole positions, 63% were the
  search's own copies and 22% these.
- **Every move and every dice roll** ends by writing out the whole position to
  compute its planning key (`State::planningKey` in `src/campaign_state.cpp`) and
  by checking the whole position (`State::validate`, called from
  `RecordedHistory::validate`). The key took 20% of the samples inside playing a
  move and 41% inside rolling dice; the check 15% and 27%.

## The coordinator

In the coordinator profile the coordinator answered 1,363,143 requests in 307,266
rounds, 4.44 a round, and was busy 90% of its serving time.

| Step of a round | Share of serving time | Per request |
| --- | ---: | ---: |
| Waiting for a request | 9.7% | 32 µs |
| Reading the requests | 3.5% | 11 µs |
| Laying the positions out (`pack_zone_arrays`) | 14.4% | 47 µs |
| The network pass | 64.8% | 211 µs |
| Turning outputs into priors and values | 2.3% | 7 µs |
| Sending the replies | 2.4% | 8 µs |
| The rest | 1.6% | 5 µs |

A pass took 0.259 ms plus 0.153 ms per position, fitted over all passes; 18% of
the passes held one position. With the other steps' cost per request, a round
cost about 0.26 ms plus 0.23 ms per position: 1.29 ms for 4.44 positions, against
1.30 ms of busy time per round measured. The positions now cost four fifths of a
round. In the native samples of the coordinator's thread, PyTorch's own operators took
41% (the GELU curve 12%, the column lookups 7%), Python's interpreter 22%, numpy,
which lays the positions out, 9%, copying, allocating and returning memory about
12%, and the matrix products, in Apple's BLAS library, 5%.

## What limits self-play

These are inferred from the measurements above, not measured.

- **The 9 cores.** In the coordinator profile the training kept 9.1 cores busy
  and spent 148 ms of CPU per decision; at that load that is about 222,500
  decisions an hour, close to the 213,644 it played. More decisions an hour
  within the allowance need less CPU per decision, and 90% of it is the game
  processes'.
- **The coordinator, next.** Busy all the time, at 0.26 ms a round plus 0.23 ms
  a position, it answers about 240,000 decisions an hour with today's 4.4
  positions a round, 264,000 with 8, 275,000 with 12 and 301,000 with rounds of
  any size. A cheaper engine leaves more positions waiting for each round, so
  rounds grow. So a faster engine alone can raise decisions per hour by at most
  about 12% with today's rounds and 40% with rounds of any size; with rounds of 8
  to 12 positions, by about a quarter. Beyond that the coordinator's
  cost per position, mostly the network's arithmetic, must fall too, or a second
  core must share its work.
- **The Mac's other work.** The allowance leaves one of the 10 performance cores
  for everything else, but everything else used about 4 cores. The training's
  processes then ran partly on the efficiency cores and waited for cores, and
  the coordinator, which every game thread waits for, waited for a core for 10%
  to 21% of its CPU time.

## What this does and does not show

- **Measured:** the two batches' speed, load, performance-core shares, waits for
  a core and instruction counts; the CPU of every engine and Python call in the
  game threads; the steps of the coordinator's rounds; 60 seconds of native
  stacks of three game processes and 40 seconds of the coordinator.
- **Not comparable:** the speeds with earlier records. Other work used about 4
  cores here against 2.6 to 3.4 on 15 November, and the training's share of
  performance cores depends on it. Instructions per decision do not depend on
  the load; they are the measure to compare with later.
- **Inferred:** the two limits, the coordinator's capacity at larger rounds, and
  that a faster engine alone gains at most about 12% to 40%.
- **Open:** how much each saving would buy. Each change to the engine needs the
  checks that the play stays the same and matched batches; a higher priority for
  the coordinator, so that it keeps a performance core, has not been tried.
