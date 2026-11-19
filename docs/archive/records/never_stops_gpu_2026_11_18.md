# Self-play that never stops on the GPU — 18 November 2026

Self-play that never stops ran only with the inference server on the CPU
([record](self_play_never_stops_2026_11_17.md)). Commit `c2b1d20` lets it run
with the inference server on the GPU: the network update trains on the GPU
beside the inference server, which meanwhile runs the layers as written and
holds back the GPU's cache releases. This record gives the tests that showed why
those two must wait, and one run of each mode at 256×8 on the Mac's GPU: self-play
that never stops against alternating training iterations, both with 126
concurrent games in 6 game processes of 21 and the compiled layers. The
[evidence file](never_stops_gpu_2026_11_18.json) holds every value and the test
script.

- **Self-play that never stops answered 8.7% more network evaluations per
  wall-clock second**: 4,085 from its start to its second network update,
  against 3,759 over the alternating run's two training iterations, their
  uneven ends and network updates included. By part: 4,075 up to its first
  network update and 4,093 between the first and the second, against 3,928 and
  3,615 for the two alternating training iterations, which differed from each
  other by 8%. At the alternating run's 51.4 network evaluations per decision,
  that is about 286,000 decisions an hour against 263,318.
- **A network update beside self-play took three times as long**, 113.5 and
  115.2 seconds against 35.5 alone. While one ran, the inference server answered
  2,621 and 2,704 network evaluations a second, against 4,167 between them, 36%
  fewer; that cost about 2% of the network evaluations between two network
  updates (worked out).
- **What it removes**: the alternating training iterations lost 12.3% and 13.0%
  of their decisions an hour to the games' uneven ends, and stood still for each
  network update.
- **Memory**: the training process held about 5 GB, GPU memory included, between
  network updates, and 11.4 and 12.1 GB in the last seconds of each; the run's
  sampled peak was 20.0 GB against 15.2 GB for the alternating run.

## Training beside the inference server on the Mac's GPU

A test script, in the evidence file, ran two threads in one process on the Mac's
GPU with PyTorch 2.14: one repeating forward passes of a network of 256×8 with
message-passing layers and checking every output against one computed before,
the other training another such network with Adam and reading its loss back
every training step, as the learner does.

| Test | Result |
| --- | --- |
| Forward passes as written beside training, 60 s | 12,770 forward passes and 1,423 training steps; every output within 1.1e-6 of the one computed alone |
| The same, and every 50 forward passes a synchronize and a release of the GPU's caches | the process aborted: a failed assertion in Metal's `setCurrentCommandEncoder`, a command buffer already committed |
| The same with the synchronize alone | aborted the same way |
| Compiled forward passes alone, 30 s | 16,025 forward passes; outputs within 1.2e-6 |
| Compiled forward passes beside training | the process stopped doing anything as the threads started, twice |

A sample of the stopped process showed why. The thread of forward passes was
launching a compiled kernel (`MetalKernelFunction::runCommandBlock`, called
through pybind11, which keeps Python's lock) and waiting for the GPU's dispatch
queue. That queue was running the training thread's `index_select`, which waited
for Python's lock. So the inference server holds back the cache releases
(`hold` and `release` of `MPSGraphCachePolicy` in
`studies/campaign/device_runtime.py`) and runs the layers as written
(`answer_as_written` in `studies/campaign/shared_evaluator.py`) while a network
update trains.

The same change found that `fresh_game_losses` in
`studies/campaign/learning.py`, which rates each finished game, converted GPU
tensors to 64-bit numbers, which the Mac's GPU lacks; it now moves them to the
host first. A run of the training command then completed three network updates
of about 40 seconds beside self-play on the GPU, with a 256×8 network and the
compiled layers, in 2 processes of 4 games of 2 game rounds.

## How it was measured

- **Runs.** Commit `c2b1d20`, from a copy of it with its compiled engine module,
  PyTorch 2.14.0, on the Mac's Apple M4 Max, the allocator variable
  `MallocNanoZone` unset in the training processes. Self-play that never stops
  ran from 15:55 to 17:44 and was stopped by its time budget after its second
  network update, losing the games then in play; the alternating run ran from
  17:44 to 18:47, two training iterations. Each was started by
  `tools/supervise_campaign_training.py` with the Mac profile:

```
.venv/bin/python tools/supervise_campaign_training.py --profile mac --working-directory RUNTIME --control-dir OUT/NAME-control --run-dir OUT/NAME --seconds 6600 --max-restarts 0 -- --calendar-rounds 11 --complete-episodes --transitions-per-batch 20000 --simulations 64 --max-depth 16 --hidden-dim 256 --message-layers 8 --batch-size 32 --epochs 525 --replay-capacity 8000 --sample-fraction 0.05 --seed 20261118 --neural-device mps --compiled-forward --episode-workers 6 --games-per-process 21 --parallel-envs 126 --continuous --batches 3
```

The alternating run had `--no-continuous --batches 2` and `--seconds 5400`
instead. Both ran 126 concurrent games in 6 game processes of 21, because the
supervisor counts a core for the network updates of self-play that never stops
and so allows six game processes, not seven; a network update came after every
126 games that ended, with the same learning settings.

- **The measure** is network evaluations per wall-clock second, from the
  inference server's count of network evaluations at each network update
  (`evaluator` in the run's `manifest.json`) and the time of each network
  update's end. Each decision took 51.0 and 51.7 network evaluations in the two
  alternating training iterations, so a network evaluation is the same amount of
  self-play in both modes.
- **Why not the decisions of finished games.** The record of 17 November counted
  the decisions of the games that ended between two network updates. Here, with
  126 concurrent games of about 1,100 decisions, a network update came only every
  126 games that ended, and the run had time for two. All 126 games start
  together, so they end in waves, and the 126 games between the two network
  updates ended at a rate that had not settled: counted that way, 229,664
  decisions an hour, while the inference server's network evaluations over the
  same time come to about 287,000.
- **CPU cores** come from `tools/log_process_load.py`, and the memory from the
  physical footprint it samples for each process, which includes GPU memory.

## Results

| Measure | Never stops | Alternating, first training iteration | Alternating, second |
| --- | ---: | ---: | ---: |
| Network evaluations per wall-clock second | 4,075 up to the first network update, 4,093 from it to the second | 3,928 | 3,615 |
| Decisions per wall-clock hour | | 277,098 | 251,519 |
| Network evaluations per decision | | 51.0 | 51.7 |
| Network update | 113.5 s, 115.2 s | 35.5 s on average | |
| Lost to the games' uneven ends | | 12.3% | 13.0% |
| States per inference batch | 56.7 between network updates, 60 during them | 42.7 | 44.8 |
| Inference server answering per state | 220.9 µs between network updates | 229.4 µs | 251.0 µs |

| Measure | Never stops | Alternating |
| --- | ---: | ---: |
| Network evaluations per wall-clock second, whole run | 4,085 to the second network update | 3,759 |
| Game processes' CPU cores | 6.86 | 6.33 |
| Training process's CPU cores | 0.69 | 0.69 |
| Game processes' wait for a core, per CPU second | 1.10 s | 0.90 s |
| Other work on the Mac, median half-minute window | 1.73 | 0.71 |
| Training process's largest physical footprint | 12.1 GB | 8.0 GB |
| Peak memory of all processes, sampled by the supervisor | 20.0 GB | 15.2 GB |

The inference server during and between the network updates of self-play that
never stops:

| Network update | During it | Network evaluations a second | Inference batch | Between it and the one before | Network evaluations a second | Inference batch |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 117.4 s | 2,621 | 20.7 ms | | | |
| 2 | 118.8 s | 2,704 | 20.0 ms | 2,250.5 s | 4,167 | 12.5 ms |

- **The gain is about what removing the uneven ends predicts.** The alternating
  training iterations lost 12.3% and 13.0% to them and their network updates
  stopped self-play for about 2% of the time; self-play that never stops lost
  about 2% to its slower network updates. That leaves about 12%, and the run
  gave 8.7%, within the 8% by which the two alternating training iterations
  differed.
- **The second alternating training iteration was slower** than the first, with
  longer games, 1,125 decisions a game against 1,061, and 9% more time a state.
  The run of self-play that never stops had more of the Mac's other work, a
  median of 1.73 CPU cores against 0.71.
- **Memory rose through the run.** The training process's footprint had a
  median of 2.7 GB before the first network update, 4.9 GB between the first and
  the second, and 5.5 GB after the second, with peaks of 11 to 12 GB in the last
  seconds of each network update, while the cache releases were held; what
  filled the peaks is not measured. The learner keeps an event for every
  transition of every game and never drops one, about 2.0 GB after 997 games
  ([record](memory_in_training_2026_11_18.md)), which fits the rise between the
  network updates.

## What this does and does not show

- **Measured:** one run of self-play that never stops on the GPU, two network
  updates, and one alternating run of two training iterations, at 256×8 with
  126 concurrent games in 6 game processes of 21; the thread tests on the Mac's
  GPU with PyTorch 2.14.
- **Self-play that never stops works on the GPU** and did about 9% more self-play
  per wall-clock hour than alternating training iterations at the same layout.
  One run of each, with training iterations that differed by 8%, cannot fix the
  gain more closely.
- **Not measured:** a run of many network updates, which would show whether the
  training process's memory stops growing; against 7 game processes of 18, the
  layout alternating training iterations may use (one training iteration there,
  earlier the same day, answered about 3,976 network evaluations per wall-clock
  second, worked out from its decisions, network evaluations per decision and
  times: [record](compiled_layers_126_games_2026_11_18.md)); a trainer process
  of its own, which would need neither the layers as written nor held cache
  releases; the Windows PC's NVIDIA GPU; whether the learning differs between
  the two modes.
