# The search in C++ in training at 256×8 on the GPU — 19 November 2026

Self-play now runs each decision's search in C++
([design, section 4.7](../../design/README.md#47-more-detail-on-the-search)).
This record compares training iterations of the code before and after that
change, in the setup the [19 November profile](game_processes_gpu_2026_11_19.md)
measured: 256×8 on the Mac's GPU with 126 concurrent games. Two pairs of runs,
the code before and after taking turns, and one profiled run of the code after,
which shows where the game processes' time goes now. The
[evidence file](search_in_cpp_2026_11_19.json) holds every value.

- **Decisions per hour while playing rose 16.8% and 12.5%** in the two pairs:
  from 347,846 to 406,191 and from 364,941 to 410,731. Network evaluations a
  second rose as much, from 4,921 and 5,174 to 5,750 and 5,833.
- **A network evaluation cost the game processes 0.97 ms of CPU instead of
  1.62 ms**, 40% less, and a decision 50 ms instead of 82 ms. They ran 21% fewer
  instructions for each network evaluation, and their time in the operating
  system's kernel fell from 11.9% of their CPU to 2.3%. The 19 November profile
  had estimated about 0.7 ms less.
- **The runs kept a median of 6.5 and 6.6 CPU cores busy instead of 9.3 and
  9.5**, within the allowance of 9.
- **The inference server now sets the pace alone.** It waited for inference
  requests 2.5% to 2.9% of the playing time in all four runs. Its inference
  batches grew from 42.6 and 44.1 states on average to 46.3 and 47.7, and its
  time answering fell from 182 and 173 µs a network evaluation to 156 and
  155 µs.
- **A game thread computed 9% of its time and waited for the inference server's
  reply 91%.** It no longer waited for Python's lock. Inside the engine, listing
  legal actions took 39% of the time, encoding the state 18%, playing an action
  17%, copying the game 10% and rolling dice 7%; the search's own work on its
  tree took 3% and the inference requests 1%.

## How it was measured

- **Code.** Before: commit `2a90d89`. After: the C++ search on the same code,
  which main holds as commit `cd09de0`, after the rules change `dc3084a`.
  Each from a copy made with `git archive`, with its own compiled engine module;
  PyTorch 2.14.0, on the Mac's Apple M4 Max; the allocator variable
  `MallocNanoZone` unset in the training processes.
- **Runs.** One training iteration each of 126 eleven-round games, 18 in each of
  7 game processes, a fresh 256×8 network, 64 simulations a decision,
  simulation depth 16, the compiled layers, seed 20261119. In order: before
  from 11:46 to 12:09, after from 12:09 to 12:29, before from 12:29 to 12:51,
  after from 12:51 to 13:11, and the profiled run of the code after from 13:11
  to 13:32, all on 19 November. The Mac's other work kept a median of 0.7 to
  1.1 CPU cores busy.
- **Throughput** comes from each run's `manifest.json`: its playing time, the
  decisions and games, and the inference server's counters (network
  evaluations, inference batches, time answering, time waiting). **Memory** is
  the supervisor's sampled peak of the whole run (`state.json`). **Load**:
  `tools/log_process_load.py` logged every process's CPU counters every
  5 seconds.
- **The profiled run** ran `tools/profile_game_process_cpu.py`, which charges
  each game thread's CPU time to the innermost instrumented call it is in; with
  the C++ search, nearly all of it is one call a decision
  (`search_decision` in `studies/campaign/native_search.py`). macOS's
  `/usr/bin/sample` recorded the native call stacks of one game process for
  20 seconds at 180, 420, 660 and 900 seconds, a different process each time,
  while all the games played. A script in the evidence file sorts each game
  thread's samples by their innermost frames, and the engine's samples by the
  outermost part of the search they are in.

The commands, run from each copy (the profiled run with
`tools/profile_game_process_cpu.py --output OUT/profile-new.json`, its sample
times, and the same training options):

```
.venv/bin/python tools/supervise_campaign_training.py --profile mac --control-dir OUT/NAME-control --run-dir OUT/NAME --seconds 3600 --max-restarts 0 -- --calendar-rounds 11 --complete-episodes --batches 1 --transitions-per-batch 20000 --simulations 64 --max-depth 16 --hidden-dim 256 --message-layers 8 --batch-size 32 --epochs 525 --replay-capacity 8000 --sample-fraction 0.05 --seed 20261119 --neural-device mps --no-continuous --compiled-forward --episode-workers 7 --games-per-process 18 --parallel-envs 126
.venv/bin/python tools/log_process_load.py record --pid SUPERVISOR --output OUT/NAME-load.jsonl
```

## Results

### The matched runs

| Measure | Before, 1 | After, 1 | Before, 2 | After, 2 |
| --- | ---: | ---: | ---: | ---: |
| Decisions per hour while playing | 347,846 | 406,191 | 364,941 | 410,731 |
| Games per hour while playing | 335.5 | 390.4 | 350.7 | 391.7 |
| Playing time | 1,352 s | 1,162 s | 1,294 s | 1,158 s |
| Network evaluations a second | 4,921 | 5,750 | 5,174 | 5,833 |
| States per inference batch, mean | 42.6 | 46.3 | 44.1 | 47.7 |
| Inference server waiting for inference requests, share of the playing time | 2.8% | 2.9% | 2.7% | 2.5% |
| Inference server answering, per network evaluation | 182 µs | 156 µs | 173 µs | 155 µs |
| Game processes' CPU per network evaluation | 1.62 ms | 0.97 ms | 1.61 ms | 0.98 ms |
| Game processes' CPU per decision | 82.6 ms | 49.5 ms | 82.0 ms | 50.0 ms |
| Game processes' instructions per network evaluation | 13.4 million | 10.5 million | 13.4 million | 10.5 million |
| The run's CPU cores, median half-minute window | 9.32 | 6.50 | 9.54 | 6.62 |
| The run's CPU cores, mean half-minute window | 8.80 | 6.39 | 9.15 | 6.35 |
| The Mac's other work, median half-minute window | 1.10 | 1.10 | 0.69 | 0.85 |
| Game processes' CPU on performance cores | 81% | 75% | 80% | 75% |
| Peak memory, sampled | 11.0 GB | 9.5 GB | 12.0 GB | 11.0 GB |

- **The same code differs by 5% between runs.** The two runs before the change
  played 347,846 and 364,941 decisions an hour; the two after 406,191 and
  410,731. Each run after played more than either run before.
- **Every game finished** in all five runs. With the same seed the games begin
  alike, and they drift apart as the inference batches' makeup changes the
  networks' outputs in the last digits.
- **Answering** is the inference server's time from reading the inference
  requests' arrays to the outputs; with the code after, the arrays are mapped
  while the requests are read, a little earlier than before. The inference
  server's whole process used 0.64 and 0.63 CPU cores before and 0.56 in both
  runs after; the rest of its time it waited for the GPU.

### Where a game thread's time goes now

The profiled run of the code after played 405,289 decisions an hour while
playing. A game made 1,054 decisions, 145 chance events and 53,859 network
evaluations, and its game thread used 53.7 CPU seconds, 51 ms a decision and
1.00 ms a network evaluation, against 90.9 seconds and 1.71 ms in the
19 November profile of the code before. Of the game thread's CPU, 96.5% was
the C++ search; creating the game from the scenario took 2.6% (1.4 seconds a
game), and the rest of the game loop's Python, choosing and playing each action
and keeping its sample, 0.9%. The game processes' CPU was 2.3% in the kernel,
against 11.9% before.

The four stack samples hold 810,349 samples of game threads:

| A game thread was | Share |
| --- | ---: |
| Blocked reading its pipe, waiting for the inference server's reply | 91.0% |
| Computing in the engine | 8.9% |
| Waiting for Python's lock | 0.0% |
| Computing in Python and its libraries, or other waits | 0.1% |

The game threads' engine samples, by the part of the search they are in, and
each part's CPU per network evaluation worked out from that share and the
search's 0.96 ms:

| Part of the search | Share | CPU per network evaluation |
| --- | ---: | ---: |
| Listing legal actions (`Engine::actionMenu`) | 39.1% | 379 µs |
| Encoding the state for the network (`encodeZoneInput`) | 18.0% | 174 µs |
| Playing an action (`Engine::step`) | 17.4% | 169 µs |
| Copying the game (`Engine::cloneForSearchFrom`) | 10.2% | 99 µs |
| Rolling dice (`Engine::resolveChance`) | 6.6% | 64 µs |
| Destroying the copies when a search ends | 3.6% | 34 µs |
| The search's own work: its tree, selection and backing up values | 2.8% | 27 µs |
| Writing inference requests and reading replies (`InferenceClient::evaluate`) | 1.2% | 11 µs |
| Listing declarations (`Engine::interruptMenu`) | 0.5% | 4 µs |
| Engine calls from the game loop's Python | 0.7% | |

A sample also counts a thread that was ready to run and waiting for a free CPU
core, so the shares assume such waits fall evenly on the parts. The 19 November
profile of the code before measured listing legal actions at 460 µs, with the
conversion of every legal action into a Python object, encoding at 222 µs, with
copies of its arrays into Python, playing an action at 192 µs and copying the
game at 102 µs; its Python part was 590 µs.

By the kind of work of the innermost function, the engine's samples were the
rules' own code 30.6%, allocating and freeing memory 23.3%, building and copying
strings 20.0%, comparing strings 8.0%, copying and filling memory 7.8% and
looking up maps and hash tables 6.3%: as before (29.8%, 21.7%, 19.6%, 8.3%,
8.2% and 7.0%), about 65% of the engine's time goes to memory, strings and
maps. By rule check, counting a function's samples with everything it calls so
that the rows overlap: copying whole states 12.8%, enumerating and validating
naval routes 9.2%, movement allowances 7.1%, Supply Paths 6.6%, naval orders
that can still be completed 6.5%, destroying whole states 4.6%, the planning key
4.6%, aircraft landing plans 4.2% and writing actions as canonical JSON 3.8%.
Within listing legal actions: naval orders that can still be completed 14.9%,
naval routes 14.4%, movement allowances 11.8%, Supply Paths 11.0%, aircraft
landing plans 9.0%, the economy's menu 8.8% and writing the actions as
canonical JSON 8.0%. Within playing an action: naval routes 20.2%, the planning
key of the state it reaches 17.7%, movement allowances 14.2%, Supply Paths
13.2% and checking the whole state 11.6%.

## What this does and does not show

- **Measured:** two matched pairs of training iterations at 256×8 on the Mac's
  GPU with 126 concurrent games in 7 game processes of 18, and one profiled
  training iteration of the code after, with four 20-second stack samples.
- **The search in C++ takes out what the 19 November profile said it would.**
  The game processes' CPU per network evaluation fell by 0.65 and 0.63 ms, 40%
  and 39%, against an estimate of about 0.7 ms, and the waits for Python's lock
  are gone.
- **At this layout the inference server limits alone.** It was busy about 97% of
  the playing time before and after, and the gain in network evaluations a
  second came only as it answered each one more cheaply, in larger inference
  batches. The CPU cores, at the median 6.5 of the allowance's 9, could feed
  about 1.5 times as many network evaluations a second: the allowance less the
  inference server's process, 8.4 CPU cores, divided by 0.98 ms (inferred).
- **Not shown:** how the change pays with more concurrent games, which would fill
  larger inference batches, or in the Mac profile, whose inference server runs
  the 64×2 network on one CPU core; neither was run. The C++ search makes the
  same choices as the Python search for the same network outputs
  (`tests/test_campaign_native_search.py`), so learning is unchanged; no network
  was trained to compare.
- **Not separated:** how much of the inference server's cheaper answering comes
  from the larger inference batches, and how much from its process running more
  of its time on performance cores (96% before, 98% after) with less contention
  from the game processes.
