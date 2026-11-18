# Concurrent games at 256×8 on the GPU — 18 November 2026

In training at 256×8 on the Mac's GPU earlier the same day, with 63 concurrent
games, the inference server was busy 98% of the time with inference batches of
about 24 states, while the game processes kept only about 4.4 CPU cores busy
([record](gpu_training_compiled_2026_11_18.md)). An inference batch holds at
most one state for each concurrent game
([design, section 9.3](../../design/README.md#93-what-a-larger-network-and-a-longer-search-cost)),
and a larger one costs less per state. This record measures what twice as many
concurrent games change: one training iteration with 63 games, 9 in each of 7
game processes, then one with 126, 18 in each. The
[evidence file](concurrent_games_gpu_2026_11_18.json) holds every value.

- **126 concurrent games played 33% more decisions an hour than 63**: 272,568
  against 205,064 while playing, and 301,969 against 227,561 while all the
  games played. Two runs of one setting differed by 5% to 6% in the earlier
  record, so the gain is far outside the spread of a single run.
- **The inference batches doubled, and each state cost the inference server a
  quarter less**: 48.1 states on average against 25.5, and 239 µs of its time a
  state against 323. The inference server was still busy 98% of the playing
  time, so it still set the pace.
- **The CPU cores came close to their limit.** The game processes kept 6.2 CPU
  cores busy instead of 4.4, and waited for a free core about as long as they
  computed, 1.0 second per CPU second against 0.5. Each network evaluation cost
  them 8% more CPU time, 1.60 ms against 1.48 ms.
- **Memory** rose from 8.0 GB to 12.5 GB at the sampled peak.

## How it was measured

- **Runs.** Commit `0faad2b`, run from a copy of that commit with its compiled
  engine module, so that changes to the checkout could not reach the runs;
  PyTorch 2.14.0, on the Mac's Apple M4 Max. The 63-game run went from 11:24 to
  11:45 and the 126-game run from 11:45 to 12:17. Each was started by
  `tools/supervise_campaign_training.py` with the Mac profile:

```
.venv/bin/python tools/supervise_campaign_training.py --profile mac --working-directory RUNTIME --control-dir OUT/NAME-control --run-dir OUT/NAME --seconds 5400 --max-restarts 0 -- --calendar-rounds 11 --complete-episodes --batches 1 --transitions-per-batch 20000 --simulations 64 --max-depth 16 --hidden-dim 256 --message-layers 8 --batch-size 32 --epochs 525 --replay-capacity 8000 --sample-fraction 0.05 --seed 20261118 --neural-device mps --no-continuous --no-compiled-forward --episode-workers 7 --games-per-process 9 --parallel-envs 63
```

The 126-game run had `--games-per-process 18 --parallel-envs 126` instead. A
run is one training iteration: complete games of 11 game rounds, 64 simulations
a decision, one fresh 256×8 network for the three alliances, the layers as
written, then one network update. Self-play stops for the network update
(`--no-continuous`), since self-play that never stops needs the inference server
on the CPU ([design, section 9.1](../../design/README.md#91-the-training-loop)).
Both runs started from the seed of the earlier record's runs. The learning
settings were the same, so the 126-game run's network update trained on twice
as many new training samples; this record measures speed only.

- **The allocator.** `ps eww` showed `MallocNanoZone` absent from the training
  process and its game processes: the supervisor removes the variables the Mac
  profile lists, although the agent's shell sets it.
- **Decisions per hour while playing** are a run's decisions divided by its
  playing time (`collection` in `timings_seconds_this_invocation` of the run's
  `manifest.json`), which ends with its last game. **While all the games played**
  is the number of games times the games' mean decisions per hour, each game's
  rate being its decisions over its time from the start to its end
  (`worker_seconds` in the run's `progress.jsonl`), as in the earlier record.
  From the ten games that ended first alone it came out 0.4% and 1.5% lower.
- **The inference server's time.** *Answering* is its time from reading an
  inference batch's arrays to the outputs on the host, with the GPU cache
  clears (`forward_seconds` of the evaluator report in the run's
  `manifest.json`). *Serving* adds reading the inference requests from the pipes
  and sending the replies; it is counted for each inference batch size since
  `0faad2b` (`inference_batches` of the same report). The busy share is the
  playing time less the time waiting for inference requests, as a share of the
  playing time.
- **CPU cores** come from `tools/log_process_load.py`, one log for each run,
  over the time game processes ran, as CPU seconds per second.

## Results

| Measure | 63 games | 126 games | Change |
| --- | ---: | ---: | ---: |
| Decisions per hour while playing | 205,064 | 272,568 | +32.9% |
| Decisions per hour while all the games played | 227,561 | 301,969 | +32.7% |
| Network evaluations a second while playing | 2,910 | 3,882 | +33.4% |
| States per inference batch | 25.5 | 48.1 | +88.6% |
| Inference server answering per state | 322.5 µs | 238.6 µs | −26.0% |
| Inference server serving per state | 337.0 µs | 252.6 µs | −25.0% |
| Inference server busy | 98.3% | 98.2% | |
| Game processes' CPU cores | 4.38 | 6.20 | +41.6% |
| Game processes' wait for a core, per CPU second | 0.51 s | 1.02 s | |
| Game processes' CPU per network evaluation | 1.48 ms | 1.60 ms | +7.8% |
| Game processes' instructions per network evaluation | 12.88 million | 13.34 million | +3.6% |
| Inference server process's CPU cores | 0.65 | 0.59 | |
| The run's processes, mean of half-minute windows | 5.03 | 6.84 | |
| Other work on the Mac, mean of half-minute windows | 1.78 | 0.81 | |
| Peak memory, sampled | 8.0 GB | 12.5 GB | +57% |

| Measure | 63 games | 126 games |
| --- | ---: | ---: |
| Games | 63 | 126 |
| Decisions | 69,387 | 139,298 |
| Decisions per game, mean | 1,101 | 1,106 |
| Network evaluations per decision | 51.1 | 51.3 |
| Playing time | 1,218 s | 1,840 s |
| First game ended | 830 s | 1,172 s |
| Last game ended | 1,217 s | 1,838 s |
| Network update | 30.9 s | 30.9 s |
| Inference batches | 139,285 | 148,612 |
| State at the middle of all states, in an inference batch of | 31 | 60 |
| Inference server answering | 1,143 s | 1,705 s |
| Inference server reading requests and replying | 51 s | 99 s |
| Inference server waiting for requests | 21 s | 33 s |
| GPU cache clears | 70, 22.4 s | 74, 27.8 s |

- **The decisions an hour rose as much as the inference server's rate.** With
  the inference server busy 98% of the time in both runs, what it answered a
  second set the pace: 33.4% more network evaluations a second, from a quarter
  less time a state.
- **The games' uneven ends cost the same share.** Over the whole playing time
  decisions per hour were 9.9% and 9.7% below the rate while all the games
  played: as the games ended, fewer were left to fill the inference batches.
- **The other work differed.** In the 63-game run the Mac's other work kept 1.78
  CPU cores busy on average, one half-minute window 5.55, and in the 126-game
  run 0.81. The 63-game run's 205,064 decisions an hour lies between the
  earlier record's two runs with the same settings, 202,932 and 190,888, which
  had 0.9 and 1.9 CPU cores of other work.

## The inference server's time by inference batch size

Mean serving time of an inference batch, by its number of states, where a run
had at least 200 inference batches of that size:

| States | Inference batches, 63 games | Time, 63 games | Inference batches, 126 games | Time, 126 games |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 5,016 | 2,990 µs | 1,962 | 3,691 µs |
| 4 | 2,044 | 4,319 µs | 2,224 | 4,005 µs |
| 8 | 1,255 | 5,566 µs | 1,372 | 5,215 µs |
| 16 | 1,672 | 7,735 µs | 856 | 6,897 µs |
| 24 | 4,443 | 8,620 µs | 522 | 8,725 µs |
| 32 | 6,251 | 9,458 µs | 778 | 10,426 µs |
| 40 | 2,153 | 10,631 µs | 1,312 | 11,804 µs |
| 48 | 248 | 11,944 µs | 2,443 | 12,894 µs |
| 56 | | | 3,928 | 13,628 µs |
| 64 | | | 3,543 | 14,447 µs |
| 72 | | | 2,000 | 15,464 µs |
| 80 | | | 641 | 16,555 µs |

- **An inference batch has a large fixed cost on the GPU.** One state took 3.0
  to 3.7 ms. Each further state added about 210 to 320 µs up to 16 states, and
  about 130 to 150 µs from 16 states on. A straight line through the sizes with
  at least 100 inference batches gives about 4.1 ms plus 176 µs a state with 63
  games, and 4.6 ms plus 158 µs a state with 126.
- **Inference batches of the same size did not cost the same in both runs.**
  From 26 to 48 states the 126-game run took about 10% longer for most sizes
  (from 4% less at 46 states to 19% more at 34); from 21 to 25 states the two
  runs were within 3%, and below 21 the 126-game run was mostly faster. Why is
  not measured. The CPU cores were busier in the 126-game run, and inference
  batches of one size need not hold alike states in the two runs: in the
  126-game run those of 26 to 48 states were smaller than most, some of them
  from its end, as games ended.
- **Training costs more than the forward pass alone.** An inference batch of
  about 60 states took about 14.0 ms of serving here. The forward pass of 59.7
  states as written, replayed alone from saved inference batches, took 9.4 ms
  ([record](compiled_forward_2026_11_18.md#speed)). Reading the requests and
  replying took about 0.8 ms of the 14.0 here, and the GPU cache clears about
  0.2 ms on average. The remaining 3.6 ms are not broken down.

## What limits next

Inferred from the numbers above, not measured:

- **The inference server.** In inference batches of about 60 states it answers
  about 4,300 network evaluations a second while all 126 games play.
- **The CPU cores.** At 1.60 ms of a CPU core per network evaluation, the 8.4 CPU
  cores of the 9-core allowance not used by the inference server's process could
  feed about 5,250 network evaluations a second, 22% more, about 369,000
  decisions an hour. That is an upper bound: the game processes already waited
  for a core as long as they computed, and their CPU per network evaluation rose
  with the load.
- So more concurrent games, or a cheaper inference server, would gain at most
  about a fifth before the CPU cores limit; past that the engine's CPU per
  network evaluation sets the pace.

## What this does and does not show

- **Measured:** one training iteration at 256×8 on the Mac's GPU with 63
  concurrent games and one with 126, the layers as written, one after the
  other, with the allocator unset.
- **126 concurrent games played a third more decisions an hour** in these runs,
  through inference batches twice as large; one run of each setting, so the
  33% is known to about the 5% to 6% between two runs of one setting.
- **Not measured:** self-play that never stops on the GPU; the compiled layers
  with 126 games; numbers of concurrent games other than 63 and 126; other
  network sizes; where the inference server's time goes in training beyond
  reading, answering and replying; whether more concurrent games change what
  the network learns, which depends on the learning settings.
