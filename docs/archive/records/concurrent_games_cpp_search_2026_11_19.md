# Concurrent games at 256×8 on the GPU with the C++ search — 19 November 2026

Since the search runs in C++, a training iteration at 256×8 on the Mac's GPU
with 126 concurrent games keeps a median of about 6.5 CPU cores busy, and the
inference server, busy about 97% of the time, sets the pace alone
([record](search_in_cpp_2026_11_19.md)). An inference batch holds at most about
half the concurrent games' states, and a larger one costs the inference server
less a state
([design, section 9.3](../../design/README.md#93-what-a-larger-network-and-a-longer-search-cost)).
This record measures 189, 252 and 378 concurrent games, in 7 game processes of
27, 36 and 54, against the two 126-game runs of that record. The
[evidence file](concurrent_games_cpp_search_2026_11_19.json) holds every value.

- **More concurrent games played more decisions an hour, with shrinking gains,
  up to 252.** While all the games played: about 470,000 with 126 games
  (472,626 and 467,418), 527,401 with 189 and 556,581 with 252, 12% and then
  5.5% more. Over the whole training iteration, whose last games play nearly alone:
  406,191 and 410,731, then 461,996 and 493,878.
- **The inference server stayed the limit.** It waited for inference requests
  2.5% to 3.2% of the playing time in every run. Its inference batches grew
  from 46 and 48 states on average to 68 and 95, and its time answering fell
  from 156 and 155 µs a network evaluation to 136 and 126 µs: serving an
  inference batch takes about 2.5 ms plus about 0.1 ms for each state.
- **The CPU cores were not the limit**: a median of 6.5 and 6.6 busy with 126
  games, 7.4 with 189 and 7.85 with 252, of the allowance's 9. A network
  evaluation cost the game processes 0.97 and 0.98 ms of CPU with 126 games,
  1.01 ms with 189 and 1.02 ms with 252, at the same 10.5 to 10.6 million
  instructions.
- **378 games did not fit beside the Mac's other programs.** Both runs stopped
  before their end, the first when another program's workers filled the Mac's
  memory, the second by a watchdog when swap had grown by 4.1 GB in 38 minutes,
  with macOS's memory pressure at "warning" nearly throughout. While all the
  games played they ran 5% and 10% fewer instructions a second than the
  252-game run, so about 527,000 and 496,000 decisions an hour (inferred).
- **Memory**, the supervisor's sampled peak of the run: 9.5 and 11.0 GB with
  126 games, 12.2 GB with 189, 13.5 GB with 252, and 15.0 and 15.3 GB with
  378.

## How it was measured

- **Code.** The C++ search on commit `2a90d89`, from the copy made with
  `git archive` for the [matched runs](search_in_cpp_2026_11_19.md), with its
  compiled engine module; main holds the C++ search as commit `cd09de0`.
  PyTorch 2.14.0, on the Mac's Apple M4 Max; the allocator variable
  `MallocNanoZone` unset in the training processes.
- **Runs.** One training iteration each: the concurrent games' eleven-round
  games in 7 game processes, a fresh 256×8 network, 64 simulations a decision,
  simulation depth 16, the compiled layers, seed 20261119, self-play stopping
  for the network update (`--no-continuous`). The 126-game runs are the two
  runs with the C++ search in the matched runs, from 12:09 to 12:29 and from
  12:51 to 13:11. Then, all on 19 November: 189 games from 14:19 to 14:45, 252
  from 14:45 to 15:18, 378 from 15:18, stopped by hand at 15:50, and 378 again
  from 17:19, stopped by the watchdog at 17:57. The Mac's other work kept a
  median of 0.4 CPU cores busy during the 189- and 252-game runs.
- **Throughput and the inference server** as in the
  [earlier record of concurrent games](concurrent_games_gpu_2026_11_18.md#how-it-was-measured):
  decisions per hour while playing are a run's decisions over its playing time
  (`collection` in its `manifest.json`); while all the games played, the
  number of games times the games' mean decisions per hour, each game's own
  decisions over its own time (`worker_seconds` in `progress.jsonl`). **Load**
  and **instructions** come from `tools/log_process_load.py`, every 5 seconds;
  **memory** is the supervisor's sampled peak (`state.json`).
- **The stopped runs report no counts:** a training iteration writes its
  games' and the inference server's counts only at its end. Their rates are
  worked out from the instructions their processes ran a second over a stretch
  while all the games played. In the four runs that finished, the decisions an
  hour while all the games played, divided by that rate, came to 6,703 to 6,933
  decisions an hour for each billion instructions a second, within 2% of 6,850.
- **The watchdog** of the second 378-game run, a script beside the supervisor,
  read macOS's memory pressure level (`kern.memorystatus_vm_pressure_level`),
  the swap in use and the kernel's share of the CPU every 11 seconds, and would
  stop the run safely, as a requested stop, at critical pressure, at 4 GB more
  swap than at the start, or at a kernel share above 35% three checks running.

The command, run from the copy, with `--games-per-process` 27, 36 or 54 and
`--parallel-envs` 189, 252 or 378:

```
.venv/bin/python tools/supervise_campaign_training.py --profile mac --control-dir OUT/NAME-control --run-dir OUT/NAME --seconds 5400 --max-restarts 0 -- --calendar-rounds 11 --complete-episodes --batches 1 --transitions-per-batch 20000 --simulations 64 --max-depth 16 --hidden-dim 256 --message-layers 8 --batch-size 32 --epochs 525 --replay-capacity 8000 --sample-fraction 0.05 --seed 20261119 --neural-device mps --no-continuous --compiled-forward --episode-workers 7 --games-per-process 36 --parallel-envs 252
```

## Results

| Measure | 126 games, 1 | 126 games, 2 | 189 games | 252 games |
| --- | ---: | ---: | ---: | ---: |
| Decisions per hour while all the games played | 472,626 | 467,418 | 527,401 | 556,581 |
| Decisions per hour while playing | 406,191 | 410,731 | 461,996 | 493,878 |
| Network evaluations a second while playing | 5,750 | 5,833 | 6,530 | 6,985 |
| States per inference batch, mean | 46.3 | 47.7 | 68.4 | 94.7 |
| The middle state's inference batch | 64 | 64 | 96 | 128 |
| Inference server answering, per network evaluation | 156 µs | 155 µs | 136 µs | 126 µs |
| Inference server waiting for inference requests | 2.9% | 2.5% | 3.1% | 3.2% |
| The run's CPU cores, median half-minute window | 6.50 | 6.62 | 7.41 | 7.85 |
| The run's CPU cores, highest half-minute window | 9.48 | 9.50 | 11.02 | 12.14 |
| Game processes' CPU per network evaluation | 0.97 ms | 0.98 ms | 1.01 ms | 1.02 ms |
| Game processes' wait for a core, per CPU second | 1.92 s | 1.92 s | 3.16 s | 4.37 s |
| The run's instructions a second while all the games played | 68.2 billion | 69.7 billion | 77.0 billion | 80.6 billion |
| Peak memory, sampled | 9.5 GB | 11.0 GB | 12.2 GB | 13.5 GB |

| Measure | 126 games, 1 | 126 games, 2 | 189 games | 252 games |
| --- | ---: | ---: | ---: | ---: |
| Decisions per game, mean | 1,040 | 1,049 | 1,037 | 1,040 |
| Network evaluations per decision | 51.0 | 51.1 | 50.9 | 50.9 |
| Playing time | 1,162 s | 1,158 s | 1,527 s | 1,911 s |
| First game ended | 720 s | 813 s | 974 s | 1,121 s |
| Last game ended | 1,160 s | 1,156 s | 1,526 s | 1,909 s |
| Inference batches | 144,397 | 141,512 | 145,935 | 140,984 |

Mean serving time of an inference batch, from reading its inference requests to
sending the replies, by its number of states, where a run had at least 200
inference batches of that size:

| States | 126 games, 1 | 189 games | 252 games |
| ---: | ---: | ---: | ---: |
| 1 | 2,533 µs | 2,428 µs | 2,734 µs |
| 16 | 5,432 µs | 5,457 µs | 6,082 µs |
| 32 | 7,352 µs | 6,812 µs | 7,684 µs |
| 64 | 9,296 µs | 9,991 µs | 10,190 µs |
| 96 | | 12,292 µs | 13,340 µs |
| 128 | | 14,860 µs | 15,780 µs |
| 160 | | | 17,970 µs |

- **The gain follows the inference server's cost a state.** With 126, 189 and
  252 games it answered 5,790, 6,530 and 6,985 network evaluations a second
  while playing, as its inference batches grew. From 64 to 128 states, an
  inference batch's serving time grows by 0.08 to 0.09 ms for each state, so
  each further state takes a smaller share of the fixed 2.5 ms off the others.
- **The uneven ends.** Over the whole training iteration the decisions an hour
  were 14% and 12% below the rate while all the games played with 126 games,
  12% with 189 and 11% with 252, as fewer games were left to fill the inference
  batches.
- **Waiting for a core.** The game processes' runnable time grew from 1.9 to
  4.4 seconds per CPU second while the CPU cores in use stayed under the
  allowance: an inference batch's replies wake its games' threads together, and
  they queue for the cores until the next inference batch.

## The 378-game runs

| Measure | 378 games, first run | 378 games, second run | 252 games |
| --- | ---: | ---: | ---: |
| Stretch while all the games played | 15:24 to 15:40 | 17:24 to 17:41 | 14:50 to 15:04 |
| The run's instructions a second | 76.9 billion | 72.4 billion | 80.6 billion |
| The run's CPU cores | 7.54 | 7.12 | 7.83 |
| Decisions per hour while all the games played | about 527,000 (inferred) | about 496,000 (inferred) | 556,581 |
| Peak memory, sampled | 15.0 GB | 15.3 GB | 13.5 GB |

- **The first run.** At 15:43 another program started 12 worker processes of
  about 1.1 GB each. The run's processes, which had run on about 7.5 CPU
  cores, ran on 4.1 and then 3.7 from 15:42. At 15:49 the Mac's memory was
  full: 35 GB in use with 17 GB in the memory compressor, 10.2 GB of 11.3 GB of
  swap in use, and the kernel taking 48% of the CPU, against about 9% on the
  quiet Mac. The supervisor saw nothing wrong, since the run's own memory stayed
  near 15 GB of its 30 GB allowance, and the run was stopped by hand at 15:50.
- **The second run**, with nothing else large running, started at 12.4 GB of
  swap in use. macOS reported warning-level memory pressure in 189 of the
  watchdog's 195 checks and never critical. The kernel's share of the CPU was
  under 16% in 170 checks and above 35% in 2, never three running. Swap grew to
  13.3 GB by 17:48 and to 16.5 GB by 17:57, when the watchdog stopped the run.
  Its rate stayed below the 252-game run's throughout the stretch while all the
  games played.
- **The rest of the Mac** held 11 to 17 GB of resident memory during the 189-
  and 252-game runs, among it a browser, a web development server and Claude's
  apps, and the operating system kept 5 to 6 GB for itself. During the second
  378-game run its resident memory fell to 7 to 13 GB, as macOS compressed and
  swapped its pages.

## What this does and does not show

- **Measured:** one training iteration each with 189 and 252 concurrent games,
  and two 126-game iterations from the matched runs, at 256×8 on the Mac's GPU
  with the C++ search; two 378-game iterations stopped before their end.
- **On this Mac, 252 concurrent games play the most decisions an hour**: 18%
  more than 126 while all the games played and 21% more over the whole training
  iteration, within the allowance of 9 CPU cores and in about 13.5 GB.
- **The inference server limits at every layout**, so a cheaper inference server
  would pay at each; the game processes' CPU would limit at about 8,600 network
  evaluations a second (inferred in the [matched runs' record](search_in_cpp_2026_11_19.md#what-this-does-and-does-not-show)),
  not reached here.
- **378 games are not measured.** The rates of the stopped runs are inferred
  from their instructions, and they show that the Mac's memory, not the
  supervisor's allowance, ends the gains here: whether 378 games would play
  more than 252 on a Mac with nothing else open is not known. That the
  supervisor watches only the run's own memory is
  [Q-011 in the questions page](../../questions.md#q-011-the-memory-the-rest-of-the-mac-uses).
- **Not shown:** self-play that never stops, which has no uneven ends and so
  would play near the rate while all the games played; and learning. More
  concurrent games give each training iteration more games, and in self-play
  that never stops each game would span more network updates; how either
  changes what the networks learn was not measured.
