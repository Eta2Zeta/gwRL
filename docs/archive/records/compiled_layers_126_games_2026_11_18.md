# Compiled layers with 126 concurrent games at 256×8 — 18 November 2026

With one network's zone and position layers compiled (`--compiled-forward`), a
forward pass of 256×8 over about 60 states took 21% less time on the Mac's GPU in
replays of saved inference batches, but in training with 63 concurrent games,
whose inference batches held about 24 states, no gain was established
([record](gpu_training_compiled_2026_11_18.md)). With 126 concurrent games the
inference batches hold about 60 states in steady play
([record](concurrent_games_gpu_2026_11_18.md)). This record measures the
compiled layers there: one training iteration with them, between two with the
layers as written. The [evidence file](compiled_layers_126_games_2026_11_18.json)
holds every value.

- **Inference batches of the same size took 8% to 12% less time with the
  compiled layers** at 40 to 80 states, the sizes of steady play: 8.4% less than
  in the earlier run with the layers as written and 11.9% less than in the later
  one, while those two runs differed by 4.0% at the same sizes.
- **The compiled run played 7.9% more decisions an hour while playing than the
  two runs as written on average**: 285,875 against 272,568 and 257,270. While
  all the games played it played 11.2% more: 326,248 against 301,969 and
  284,598. The two runs as written differed by 5.8% and 6.1%.
- **The inference server still set the pace**, busy 97.8% of the playing time.
  While all the games played it answered about 4,620 network evaluations a
  second, against 4,300 and 4,050 with the layers as written; the CPU cores
  could feed about 5,200 (inferred), about an eighth more.

## How it was measured

- **Runs.** Commit `0faad2b`, from the same copy of it as the
  [record of concurrent games](concurrent_games_gpu_2026_11_18.md), with its
  compiled engine module; PyTorch 2.14.0, on the Mac's Apple M4 Max; the
  allocator variable `MallocNanoZone` unset in the training processes. The runs,
  in order: the first run as written, from 11:45 to 12:17, which is that record's
  126-game run; the compiled run, from 14:08 to 14:36; the second run as written,
  from 14:36 to 15:10. Each was started by `tools/supervise_campaign_training.py`
  with the Mac profile:

```
.venv/bin/python tools/supervise_campaign_training.py --profile mac --working-directory RUNTIME --control-dir OUT/NAME-control --run-dir OUT/NAME --seconds 5400 --max-restarts 0 -- --calendar-rounds 11 --complete-episodes --batches 1 --transitions-per-batch 20000 --simulations 64 --max-depth 16 --hidden-dim 256 --message-layers 8 --batch-size 32 --epochs 525 --replay-capacity 8000 --sample-fraction 0.05 --seed 20261118 --neural-device mps --no-continuous --episode-workers 7 --games-per-process 18 --parallel-envs 126 --compiled-forward
```

The runs as written had `--no-compiled-forward` instead. A run is one training
iteration: 126 complete games of 11 game rounds, 18 in each of 7 game processes,
64 simulations a decision, one fresh 256×8 network for the three alliances, then
one network update.

- **Compiling.** The compiled layers are compiled for fixed numbers of states,
  the state buckets, when an inference batch first needs one
  ([design, section 9.3](../../design/README.md#93-what-a-larger-network-and-a-longer-search-cost)).
  A warm-up run with the compiled layers, from 14:02 to 14:08 and stopped by its
  time budget, came first, so that PyTorch's compile cache would hold every
  state bucket. It held them already, from the morning's work: no file of the
  cache changed during the warm-up or the runs, and its entries were read at
  14:08. So the compiled run compiled nothing anew beyond reading the cache.
- **Measures** are those of the record of concurrent games: decisions per hour
  while playing and while all the games played, the inference server's time
  answering and serving, by inference batch size, and the CPU cores from
  `tools/log_process_load.py`. The *same-size change* compares two runs'
  inference batches of each number of states: the ratio of their mean serving
  times, averaged over the sizes with at least 200 inference batches in both
  runs, weighted by the two runs' inference batches of that size.

## Results

| Measure | As written, first | Compiled | As written, second |
| --- | ---: | ---: | ---: |
| Decisions per hour while playing | 272,568 | 285,875 | 257,270 |
| Decisions per hour while all the games played | 301,969 | 326,248 | 284,598 |
| Network evaluations a second while all the games played | 4,300 | 4,620 | 4,050 |
| States per inference batch | 48.1 | 44.2 | 48.1 |
| State at the middle of all states, in an inference batch of | 60 | 59 | 59 |
| Inference server answering per state | 238.6 µs | 225.8 µs | 251.6 µs |
| Inference server serving per state | 252.6 µs | 241.1 µs | 267.5 µs |
| Inference server busy | 98.2% | 97.8% | 98.1% |
| Line through the serving times, per inference batch | 4.56 ms | 4.48 ms | 5.63 ms |
| Line through the serving times, per state | 158 µs | 140 µs | 150 µs |
| Game processes' CPU cores | 6.20 | 6.49 | 6.05 |
| Game processes' CPU per network evaluation | 1.60 ms | 1.60 ms | 1.65 ms |
| Game processes' wait for a core, per CPU second | 1.02 s | 1.12 s | 1.41 s |
| Inference server process's CPU cores | 0.59 | 0.67 | 0.57 |
| Other work on the Mac, median half-minute window | 0.77 | 0.82 | 1.59 |
| Decisions per game, mean | 1,106 | 1,048 | 1,103 |
| Games ended: first, middle, last | 1,172 s, 1,669 s, 1,838 s | 1,154 s, 1,457 s, 1,661 s | 1,406 s, 1,780 s, 1,942 s |
| Lost to the games' uneven ends | 9.7% | 12.4% | 9.6% |
| Network update | 30.9 s | 31.3 s | 36.9 s |
| Peak memory, sampled | 12.5 GB | 13.4 GB | 13.3 GB |

Mean serving time of an inference batch, by its number of states:

| States | As written, first | Compiled | As written, second |
| ---: | ---: | ---: | ---: |
| 1 | 3,691 µs | 2,834 µs | 3,575 µs |
| 8 | 5,215 µs | 6,002 µs | 6,069 µs |
| 16 | 6,897 µs | 6,998 µs | 9,006 µs |
| 24 | 8,725 µs | 9,578 µs | 10,688 µs |
| 32 | 10,426 µs | 9,942 µs | 11,623 µs |
| 40 | 11,804 µs | 10,780 µs | 12,769 µs |
| 48 | 12,894 µs | 12,001 µs | 13,235 µs |
| 56 | 13,628 µs | 12,345 µs | 13,997 µs |
| 64 | 14,447 µs | 13,260 µs | 14,481 µs |
| 72 | 15,464 µs | 14,096 µs | 15,454 µs |
| 80 | 16,555 µs | 14,301 µs | 18,164 µs |

| States | Compiled against the first as written | Compiled against the second | Second as written against the first |
| --- | ---: | ---: | ---: |
| 1 to 16 | +1.2% | −12.7% | +15.1% |
| 17 to 32 | +1.9% | −12.4% | +16.7% |
| 33 to 48 | −6.4% | −13.4% | +8.2% |
| 49 to 64 | −8.3% | −11.6% | +3.7% |
| 65 to 80 | −9.6% | −11.6% | +2.3% |
| 40 to 80 | −8.4% | −11.9% | +4.0% |

- **The compiled layers pay in the inference batches of steady play.** An
  inference batch of 64 states, for one, took 13.26 ms with them against 14.45
  and 14.48 ms as written, about 1.2 ms less. The replays had them save about
  1.9 ms of a forward pass of 59.7 states
  ([record](compiled_forward_2026_11_18.md#speed)).
- **In inference batches of up to 32 states they did not pay** against the first
  run as written, as in the earlier record's training runs, whose inference
  batches held about 24 states. Against the second they did, but that run's
  small inference batches were 15% to 17% slower than the first's: the two runs
  as written differed most there. Small inference batches come mostly from a
  training iteration's end, as games end, and their times varied with the run.
- **The second run as written was the slowest.** The Mac's other work was
  heaviest then, with a median half-minute window of 1.59 CPU cores against 0.77
  and 0.82, and its game processes waited longest for a core, 1.41 seconds per
  CPU second. Its load log also holds one half-minute window of 57 CPU cores for
  the run's processes, impossible on 14: a sampling artifact, so this record
  gives medians of the windows, and the CPU cores from the processes' CPU
  seconds.
- **The compiled run's games were shorter**, 1,048 decisions a game against
  1,106 and 1,103, and its last games played longer alone: it lost 12.4% to the
  games' uneven ends against 9.6% and 9.7%, which held its gain while playing
  below its gain while all the games played.

## What this does and does not show

- **Measured:** one training iteration at 256×8 on the Mac's GPU with 126
  concurrent games and the compiled layers, between two with the layers as
  written, the earlier of them two hours before.
- **The compiled layers make the inference batches of steady play about a tenth
  cheaper** with 126 concurrent games: 8% to 12% less time at the same sizes,
  against 4% between the two runs as written. Decisions per hour rose about as
  much, 7.9% while playing and 11.2% while all the games played, against a 6%
  spread between the runs as written.
- **What limits next** is still the inference server, with the CPU cores about
  an eighth behind (inferred as in the record of concurrent games: the 9 CPU
  cores of the allowance, less the inference server's process, over 1.60 ms of
  CPU per network evaluation).
- **Not measured:** a second compiled run; the time a cold compile cache costs
  as a run starts (in the earlier record, 17 to 36 seconds on the GPU); the
  compiled layers with other numbers of concurrent games than 63 and 126, or
  other network sizes, in training; self-play that never stops on the GPU.
