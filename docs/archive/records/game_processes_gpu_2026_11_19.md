# Where the game processes' time goes at 256×8 on the GPU — 19 November 2026

Since 18 November, training at 256×8 on the Mac's GPU with 126 concurrent games
keeps a median of about 9.5 CPU cores busy, and the inference server and the CPU
cores limit it together
([record](readout_without_repeat_2026_11_18.md)). This record profiles one
training iteration of that setup on main at commit `673076c`, to show where the
game processes' CPU time goes and what their game threads wait for. The
[evidence file](game_processes_gpu_2026_11_19.json) holds every value.

- **A network evaluation costs a game thread 1.71 ms of CPU.** The engine's
  calls take 0.89 ms of it, encoding the state for the network 0.22 ms, and
  Python 0.59 ms: the search, the adapter around the engine, the game loop and
  the inference requests.
- **Listing a state's legal actions is the largest engine call**, 0.46 ms, 27%
  of the CPU. Playing an action takes 0.19 ms and copying the game for the
  search 0.10 ms.
- **Each network evaluation makes 27 engine calls**, 12.5 of them for the
  state's planning key and 5.7 asking whether the game has ended. Every engine
  call gives up Python's lock while the engine works and takes it back to
  return.
- **A game thread computes about a tenth of its time.** In native stack samples
  taken while all the games played, it waited for Python's lock 56% of its time
  and for the inference server's reply 33%. The 18 game threads of a process
  held the lock for their Python work about 56% of the time.
- **Inside the engine, 30% of the time is the rules' own code.** Allocating and
  freeing memory took 22%, building, copying and comparing strings 28%, copying
  memory 8% and looking up maps 7%.

## How it was measured

- **Run.** Commit `673076c`, from a copy made with `git archive`, with its
  compiled engine module; PyTorch 2.14.0, on the Mac's Apple M4 Max; the
  allocator variable `MallocNanoZone` unset in the training processes. One
  training iteration of 126 eleven-round games, 18 in each of 7 game processes,
  a fresh 256×8 network, 64 simulations a decision, simulation depth 16, the
  compiled layers, seed 20261119, from 06:31 to 06:54 on 19 November. The Mac's
  other work kept a median of 0.65 CPU cores busy.
- **Accounts.** `tools/profile_game_process_cpu.py` ran the training iteration
  as the supervisor does. In every game process each game thread charges its
  own CPU time, user and system, to the innermost instrumented call it is in:
  an engine call, the encoding, the adapter's Python layer
  (`studies/shared/campaign_adapter.py`), the search's own Python
  (`VectorMCTS.search` in `studies/shared/multiplayer_mcts.py`), preparing an
  inference request, the pipe, or the rest of the game loop. The accounts' own
  cost, about 0.63 µs a wrapped call, came to an estimated 1.6 of the 90.9 CPU
  seconds of a game.
- **Stack samples.** macOS's `/usr/bin/sample` recorded the native call stacks
  of one game process for 20 seconds at 180, 420, 660 and 900 seconds into the
  run, a different process each time, while all 126 games played. A script in
  the evidence file sorts each game thread's samples by their innermost frames:
  computing in the engine, computing in Python, blocked reading its pipe, or
  waiting to take Python's lock (CPython's `take_gil`).
- **Load.** `tools/log_process_load.py` logged every process's CPU counters
  every 5 seconds.

The command, run from the copy:

```
.venv/bin/python tools/profile_game_process_cpu.py --output OUT/game.json --profile mac --control-dir OUT/game-control --run-dir OUT/game-run --seconds 3600 --sample-at 180,420,660,900 --sample-seconds 20 -- --calendar-rounds 11 --complete-episodes --batches 1 --transitions-per-batch 20000 --simulations 64 --max-depth 16 --hidden-dim 256 --message-layers 8 --batch-size 32 --epochs 525 --replay-capacity 8000 --sample-fraction 0.05 --seed 20261119 --neural-device mps --no-continuous --compiled-forward --episode-workers 7 --games-per-process 18 --parallel-envs 126
```

## Results

### The run

| Measure | Value |
| --- | ---: |
| Decisions per hour while playing | 349,594 |
| Decisions per game | 1,042 |
| Network evaluations per game | 53,152 |
| Inference batches | 154,807 |
| States per inference batch, mean | 43.3 |
| Half of all states answered in inference batches of at least | 55 states |
| Serving an inference batch, mean | 8.44 ms |
| Inference server waiting for inference requests, share of the playing time | 3.1% |
| The run's CPU cores, median half-minute window | 9.85 |
| The run's CPU cores, mean and highest half-minute window | 9.33 and 11.09 |
| Game processes' CPU cores, mean | 8.57 |
| Game processes' CPU on performance cores | 80% |
| Game processes' wait for a core, per CPU second | 1.26 s |
| Game processes' CPU in the operating system's kernel | 11.9% |
| Game processes' instructions per network evaluation | 13.9 million |

The profiled run of 18 November, at commit `fa45792` and with the inference
server profiled instead of the game processes, played 357,981 decisions an hour
while playing ([record](readout_without_repeat_2026_11_18.md)). This run's
network reads the input layout of `673076c`, and its accounts cost about 2% of
the game threads' CPU.

### A game thread's CPU per network evaluation

Every game finished. A game made 1,042 decisions, 145 chance events and 53,152
network evaluations, 51 a decision, and its game thread used 90.9 CPU seconds.
Per network evaluation:

| Where | CPU | Share | Calls |
| --- | ---: | ---: | ---: |
| Engine: listing legal actions (`legal_actions`) | 460 µs | 26.9% | 1.00 |
| Engine: encoding the state for the network (`zone_input`, its arrays) | 222 µs | 13.0% | 2.00 |
| Engine: playing an action (`apply_action`) | 192 µs | 11.2% | 0.98 |
| Engine: copying the game for the search (`clone_for_search`, `clone_for_search_continuing`) | 102 µs | 5.9% | 1.33 |
| Engine: the planning key (`planning_key`) | 53 µs | 3.1% | 12.49 |
| Engine: rolling dice (`resolve_chance`) | 49 µs | 2.9% | 0.35 |
| Engine: other calls (`legal_interrupts`, `is_terminal`, `decision_kind`, `current_decision_player`) | 37 µs | 2.2% | 9.20 |
| Python: the search's own code | 190 µs | 11.1% | |
| Python: the adapter around the engine | 168 µs | 9.8% | |
| Python: the game loop, with creating the game from the scenario (30 µs) | 108 µs | 6.3% | |
| Python: sending inference requests and reading the replies through the pipe | 94 µs | 5.5% | 1.00 |
| Python: writing a request's arrays into shared memory | 34 µs | 2.0% | 1.00 |
| All | 1,710 µs | 100% | 27.36 engine calls |

- **The small calls are many.** The adapter asks the engine for the planning
  key in nearly every one of its methods, to notice a change of state
  (`_sync`), so a network evaluation makes 12.5 planning-key calls, each 4.2 µs
  of CPU, though the engine keeps the key after working it out once.
- **Creating a game** from the scenario took 1.6 seconds, 1.8% of a game's CPU.
- **A game thread's wall time** was 1,195 seconds, by the accounts' timers: 7.6%
  on its own CPU, 75.7% from sending an inference request until it held the
  reply, and 16.7% the rest.
- **One legal action.** 8,290 of the 53,152 network evaluations (15.6%) were of
  states with one legal action, reached inside a search; 223 of the 1,042
  decisions had one legal action and were played without a search.

### A game thread's time

The four stack samples hold 438,642 samples of game threads. By what each
sample's innermost frames show:

| A game thread was | Share | At 180 s | At 420 s | At 660 s | At 900 s |
| --- | ---: | ---: | ---: | ---: | ---: |
| Computing in the engine | 7.4% | 8.5% | 6.6% | 7.0% | 7.2% |
| Computing in Python and its libraries | 3.1% | 3.0% | 3.2% | 3.4% | 3.1% |
| Blocked reading its pipe, waiting for the inference server's reply | 33.0% | 39.6% | 30.9% | 27.7% | 33.3% |
| Waiting to take back Python's lock at the end of an engine call | 38.7% | 30.9% | 40.5% | 44.2% | 40.1% |
| Waiting for Python's lock elsewhere | 17.3% | 17.6% | 18.3% | 17.3% | 15.8% |
| Other waits | 0.5% | 0.5% | 0.5% | 0.4% | 0.6% |

- **Computing** includes time a thread was ready to run and waited for a free
  CPU core: the game processes waited 1.26 seconds for a core per second they
  ran.
- **Python's lock** lets one thread of a process run Python at a time. An engine
  call gives it up while the engine works (`NativeCampaignEnv::call` in
  `src/python_bindings.cpp`) and must take it back to return its result. Of the
  waits elsewhere, 88% followed a reply read from the pipe, 4% a request
  written to it and 6% a copy of arrays in NumPy, which also gives up the lock.
- **The lock was held for Python's work about 56% of the time** in a sampled
  process, 54% to 61% in the four samples: 18 game threads, each computing in
  Python 3.1% of its time. A thread that holds the lock and waits for a free
  CPU core holds it all the while.
- **The timers and the samples divide the waiting differently.** The timers put
  76% of a thread's time between sending a request and holding its reply,
  which takes in the wait for the lock after the reply arrives; the samples,
  taken only while all 126 games played, put 50% there, 33% at the pipe and
  17% at the lock, and 39% at the lock after engine calls, which the timers
  count among the rest.

### Inside the engine

32,222 of the samples were computing in the engine. By the engine call they
were in:

| Engine call | Share of the engine's samples |
| --- | ---: |
| Listing legal actions | 42.4% |
| Encoding the state | 20.5% |
| Playing an action | 17.3% |
| Copying the game for the search | 5.8% |
| Destroying the search's copies of the game | 4.2% |
| Rolling dice | 3.3% |
| Destroying the actions' Python objects | 1.3% |
| Other calls | 5.2% |

By the kind of work of the innermost function:

| Kind of work | Share |
| --- | ---: |
| The rules' own code | 29.8% |
| Allocating and freeing memory | 21.7% |
| Building and copying strings | 19.6% |
| Comparing strings | 8.3% |
| Copying and filling memory | 8.2% |
| Looking up maps and hash tables | 7.0% |
| Other libraries | 3.6% |
| Reading and copying JSON values | 1.0% |
| Python's interpreter | 0.8% |

By rule check and other work, counting a function's samples with everything it
calls, so that the rows overlap:

| Work | Share |
| --- | ---: |
| Encoding the state (`encodeZoneInput`) | 19.8% |
| Naval routes: enumerating and validating them | 13.2% |
| Naval orders that can still be completed | 9.3% |
| Copying whole states | 9.2% |
| Converting actions and copies to and from Python objects | 8.9% |
| Movement allowances | 8.8% |
| Aircraft landing plans | 7.8% |
| Supply Paths | 7.7% |
| Destroying whole states | 7.2% |
| Writing actions as canonical JSON | 4.2% |
| The economy's menu | 3.6% |
| The planning key | 3.3% |
| Checking the whole state (`State::validate`) | 2.7% |
| Factory capacity | 0.7% |

- **Listing legal actions** spends 19% of its samples on naval orders that can
  still be completed (`forwardNavalOrderActions`), 18% enumerating naval routes
  (`visitNavalRoutes`), 13% on movement allowances and 11% tracing supply,
  each counted with what it calls, so these overlap. Each
  legal action is copied once more to return the list (`Engine::legalActions`
  in `src/campaign_runtime.cpp`), turned into a Python object, and written once
  as canonical JSON, which playing an action compares with the action played
  (`Engine::actionMenu`, `Engine::step`).
- **Playing an action** spends 28% of its samples validating naval routes, 16%
  on the planning key, 8% of it the SHA-256 digest, and 12% checking the whole
  state.
- **Encoding the state** spends 22% of its samples on hash tables keyed by
  strings and 11% building a text signature of every unit to rank units that
  look alike (`unitSignature` and `rankUnits` in `src/zone_encoding.cpp`),
  34% the two together, and about a fifth sorting.
- **Strings.** The engine still holds units, facilities, battles, railroads,
  construction projects, repair jobs and the details of actions by name and as
  JSON ([names](../../engine/names.md#what-is-still-a-name)). A unit's copy
  copies its name, its cargo's names and its marks' arguments.

## What this does and does not show

- **Measured:** one profiled training iteration at 256×8 on the Mac's GPU with
  126 concurrent games in 7 game processes of 18; the CPU of every game
  thread's instrumented calls; four 20-second stack samples, one of each of
  four game processes, while all the games played; the CPU load of every
  process.
- **The game processes' CPU is where the engine's levers act.** Of a network
  evaluation's 1.71 ms, 1.12 ms is the engine with the encoding and 0.59 ms
  Python. About 57% of the engine's samples are memory allocation, strings,
  memory copies and map lookups, not the rules' own code.
- **Python's lock is a second limit in waiting.** It was held about 56% of the
  time in a sampled process, so at the same Python work per network evaluation
  a process could answer at most about 1.8 times as many network evaluations a
  second before its game threads' Python kept the lock busy all the time
  (inferred). A faster engine raises the network evaluations a second and so
  brings a process nearer that ceiling; less Python per network evaluation, or
  fewer games per process, would raise it.
- **Not measured:** how much each lever would save; those numbers in the design
  document are worked out from these shares. One training iteration, one
  layout and one network; a run without the accounts; instructions per engine
  call in a replayed search, which would compare two builds independently of
  the Mac's other work.
