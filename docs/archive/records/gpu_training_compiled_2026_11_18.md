# Compiled zone and position layers in GPU training runs — 18 November 2026

On saved inference batches, one network's zone and position layers compiled for
fixed numbers of states (`--compiled-forward`) took 6% to 24% less time per
inference batch on the Mac's GPU than the same layers as written, for networks
of 256×8 and 512×16
([record](compiled_forward_2026_11_18.md#speed)). This record measures what the
compiled layers change in training: four runs of one training iteration each at
256×8, with the inference server and the network update on the Mac's GPU. Runs 1
and 4 used the compiled layers and runs 2 and 3 the layers as written; the *first
pair* is runs 1 and 2, the *second pair* runs 3 and 4. The
[evidence file](gpu_training_compiled_2026_11_18.json) holds every value.

- **The runs do not establish a gain.** With the compiled layers the runs played
  205,915 decisions an hour while playing on average, and with the layers as
  written 196,910: 4.6% more. But the two runs of one setting differed by 5.0%
  (compiled) and 6.3% (as written), and the first pair gave −1.0% and the second
  +10.5%. The runs fit no change as well as a gain of about 10%.
- **The inference server set the pace.** It was busy 98% of the playing time in
  every run, and its inference batches held 22.7 to 25.4 states on average. Its
  time per state was 4.9% shorter with the compiled layers on average, 0.2%
  longer in the first pair and 9.6% shorter in the second. Part of that comes
  from the compiled runs' larger inference batches, 24.7 states against 23.7,
  since a larger inference batch costs less per state.
- **The games' uneven ends cost 10% to 14% of the decisions an hour.** While all
  63 games played, the runs played about 221,000 to 235,000 decisions an hour;
  over the whole playing time, which ends with a training iteration's last game,
  190,888 to 210,920.

## How it was measured

- **Runs.** Commit `bb092ff`, PyTorch 2.14.0, on the Mac's Apple M4 Max, one run
  after another from 08:06 to 09:30, each started by
  `tools/supervise_campaign_training.py` with the Mac profile:

```
.venv/bin/python tools/supervise_campaign_training.py --profile mac --run-dir RUN --seconds 3600 --max-restarts 0 -- --calendar-rounds 11 --complete-episodes --batches 1 --transitions-per-batch 20000 --simulations 64 --max-depth 16 --hidden-dim 256 --message-layers 8 --batch-size 32 --epochs 525 --replay-capacity 8000 --sample-fraction 0.05 --seed 20261118 --neural-device mps --no-continuous --episode-workers 7 --games-per-process 9 --parallel-envs 63 --compiled-forward
```

Runs 2 and 3 had `--no-compiled-forward` instead. A run is one training
iteration: 63 complete games of 11 game rounds, 9 in each of 7 game processes,
with 64 simulations a decision and a fresh 256×8 network, then one network
update. Self-play stops for the network update (`--no-continuous`), since
self-play that never stops needs the inference server on the CPU
([design, section 9.1](../../design/README.md#91-the-training-loop)). All four
runs started from the same seed; the GPU's float rounding, which depends on
which states share an inference batch, made their games differ.

- **The allocator.** The agent's shell set `MallocNanoZone=0`, which turns off
  macOS's nano allocator for small allocations, but the supervisor starts the
  training process without the variables the Mac profile lists
  (`unset_environment` in `studies/campaign/profiles/mac.json`, applied by
  `supervise` in `tools/supervise_campaign_training.py`), and the game processes
  inherit the training process's environment. So all four runs trained with the
  variable unset, as training runs do; only the supervisor and the load logger,
  which do little work, kept it. This record first said that the runs had
  inherited it. A run started the same way on the same day, for the
  [record of concurrent games](concurrent_games_gpu_2026_11_18.md), showed the
  variable absent from its training process and its game processes.
- **Decisions per hour while playing** are a run's decisions divided by its
  playing time (`collection` in `timings_seconds_this_invocation` of the run's
  `manifest.json`), which ends with its last game. **While all 63 games played**
  is estimated from each game's decisions and its time from the start to its end
  (`worker_seconds` in the run's `progress.jsonl`): 63 times the games' mean
  decisions per hour. A game that ended late also played after others had ended,
  when its decisions came faster, so the estimate leans high; from the ten games
  that ended first alone, it came out 1.0% lower to 0.3% higher.
- **The inference server's time** is its time answering, from reading an
  inference batch's arrays to the outputs on the host, with the GPU cache clears
  (`forward_seconds` in the evaluator statistics of the run's `manifest.json`).
  Its busy share is the playing time less its time waiting for inference
  requests, as a share of the playing time. Every 2,048 forward passes the
  inference server empties PyTorch's GPU caches (`torch.mps.empty_cache` in
  `studies/campaign/device_runtime.py`): 67 to 80 times a run, 21 to 24 seconds
  in all.
- **Cores** come from `tools/log_process_load.py`, one log for each run, while
  game processes ran: the game processes kept 4.2 to 4.5 cores busy, the
  inference server 0.65 to 0.71, and the Mac's other work 0.9 to 2.5 on average,
  with bursts of 4 to 6 cores in run 3 and up to 4 in run 4, mostly a web server
  and macOS's media analysis.

## Results

| Run | Layers | Decisions per hour while playing | While all 63 games played | Decisions per game | States per inference batch | Server time per state | Server time per inference batch |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | compiled | 200,910 | 230,635 | 1,048 | 23.9 | 327 µs | 7,827 µs |
| 2 | as written | 202,932 | 230,517 | 1,094 | 24.8 | 327 µs | 8,102 µs |
| 3 | as written | 190,888 | 221,000 | 1,123 | 22.7 | 345 µs | 7,811 µs |
| 4 | compiled | 210,920 | 234,948 | 1,060 | 25.4 | 311 µs | 7,906 µs |

| Measure | As written, mean | Compiled, mean | Change | First pair | Second pair |
| --- | ---: | ---: | ---: | ---: | ---: |
| Decisions per hour while playing | 196,910 | 205,915 | +4.6% | −1.0% | +10.5% |
| Decisions per hour while all 63 games played | 225,759 | 232,792 | +3.1% | +0.1% | +6.3% |
| Server time per state | 335.6 µs | 319.3 µs | −4.9% | +0.2% | −9.6% |
| Server time per inference batch | 7,957 µs | 7,867 µs | −1.1% | −3.4% | +1.2% |
| States per inference batch | 23.7 | 24.7 | +3.9% | −3.6% | +12.0% |

Every run asked the network about 51 times a decision. The network update took
32 to 39 seconds, about 3% of a run. The run's processes held 8.9 to 11.1 GB
of memory together at their sampled peak.

## What the forward pass alone predicted

Inferred from the earlier record's timings, not measured in these runs: at 256×8
on the GPU, the forward pass as written, from laying out a saved inference batch
to the outputs on the host, took 3,825 µs with 9.1 states and 9,378 µs with
59.7, and the compiled layers saved 241 µs and 1,936 µs of it
([record](compiled_forward_2026_11_18.md#speed)). On a straight line between
those two points, an inference batch of 24 states takes about 5,460 µs as
written, and the compiled layers save about 740 µs of it. In these runs the
inference server took about 7,900 µs for an inference batch of about 24 states,
so the forward pass would be about 70% of its time, the rest reading the
inference requests' arrays, turning the outputs into priors and emptying the GPU
caches. The saving would be about 9% of the inference server's time, and so
about 10% more decisions an hour while the inference server sets the pace. The
second pair came near that, and the first pair not at all.

## The games' uneven ends

The 63 games started together, and the training iteration ended with the last of
them: the first game ended after 756 to 938 seconds, half of them by 1,033 to
1,159 seconds, and the last after 1,138 to 1,333. As games ended, fewer were left
to fill the inference batches, and a smaller inference batch costs more per
state. Over the whole playing time, decisions per hour were 12.9%, 12.0%, 13.6%
and 10.2% below the estimate while all 63 games played, in runs 1 to 4. With the
inference server on the CPU and 24 games, the same end cost about 9% on 17
November ([record](coordinator_rounds_2026_11_17.md#the-batchs-tail)).
Self-play that never stops has no such end, but it needs the inference server on
the CPU.

## What this does and does not show

- **Measured:** four training iterations at 256×8 on the Mac's GPU, two with the
  compiled layers and two with the layers as written, in the order compiled, as
  written, as written, compiled.
- **Compiling did not measurably change decisions per hour in these runs.** The
  4.6% gain on average is within the 5% to 6% between two runs of one setting.
  The gain of about 10% that the forward pass alone predicts (inferred above) is
  not ruled out, and neither is no gain.
- **Why two runs of one setting differ** is not measured. Their games differed,
  1,048 to 1,123 decisions a game on average and 1,269 to 1,521 in the longest,
  and so did the Mac's other work. Run 3, the slowest, had the longest games and
  two bursts of other work.
- **Not measured:** the inference server's time per inference batch by its
  number of states, which would compare the two settings at equal inference
  batch sizes whatever games were played (the run's manifest keeps only the
  inference server's totals); how long the
  compiled runs spent compiling as they started, with PyTorch's compile cache
  filled by earlier runs (in the earlier record a first run with the cache took 3
  to 33 seconds, running included); larger networks; more concurrent games; the
  Windows PC.
