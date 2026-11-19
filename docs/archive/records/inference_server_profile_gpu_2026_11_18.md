# Where the inference server's time goes at 256×8 on the GPU — 18 November 2026

In training at 256×8 on the Mac's GPU with 126 concurrent games and the compiled
layers, an inference batch of 60 states took the inference server about 12.5 ms,
while the forward pass alone, replayed from saved inference batches, took 7.4 ms,
and reading the inference requests, replying and the GPU cache clears about 1 ms
more ([record](compiled_layers_126_games_2026_11_18.md#results)). This record
profiles a training iteration of that setup to find the rest, and replays its
own inference batches alone to compare step by step. The
[evidence file](inference_server_profile_gpu_2026_11_18.json) holds every value
and the scripts that read the stack samples.

- **The GPU's graph framework compiled new graphs during serving: about 23% of
  the inference server's time.** On the Mac's GPU many PyTorch operations run as
  MPSGraph graphs, which Apple's framework compiles for each new shape of their
  arrays. In two samples of the serving thread, compiling took 22.5% and 23.6%
  of its time, about 2.6 ms of an inference batch.
- **One operation caused most of it**: `Tensor.repeat` in the policy readout of
  the hierarchical softmax, `latent.repeat(GROUP_LEVELS, 1)` in `_readout` of
  `studies/campaign/neural.py`, with 71% and 79% of the compiling. Its array has
  a row for each legal action of the inference batch, a number that changes with
  nearly every inference batch. The matrix products of the layers that read the
  actions' vectors caused most of the rest, 21%: their arrays too have a row for
  each legal action.
- **Replayed alone, the same inference batches took 6.7 ms instead of 11.2 ms**,
  at 45 states on average. The replay times passes whose graphs an earlier pass
  has already compiled. Compiling accounts for about 2.6 ms of the difference,
  the pipes to the game processes, which the replay leaves out, 0.6 ms, and
  slower work in training about 1.3 ms: collating, reading and the priors on
  busy CPU cores, and the wait for the GPU.

## How it was measured

- **Run.** Commit `9fd0fc6`, whose code is that of `c2b1d20`, from a copy of it
  with its compiled engine module; PyTorch 2.14.0, on the Mac's Apple M4 Max; the
  allocator variable `MallocNanoZone` unset in the training processes. One
  training iteration of 126 eleven-round games, 18 in each of 7 game processes, a
  fresh 256×8 network for the three alliances, 64 simulations a decision, the
  compiled layers, from 19:06 to 19:36. `tools/profile_coordinator.py` ran it as
  the supervisor does, timed every step of the inference server's inference
  batches, kept every 400th inference batch and recorded the training process's
  native call stacks with macOS's `sample` for 20 seconds at 700 and 1,000
  seconds, while all 126 games played:

```
.venv/bin/python tools/profile_coordinator.py --output OUT/profile.json --profile mac --control-dir OUT/run-control --run-dir OUT/run --seconds 3600 --save-every 400 --sample-at 700,1000 --sample-seconds 20 -- --calendar-rounds 11 --complete-episodes --batches 1 --transitions-per-batch 20000 --simulations 64 --max-depth 16 --hidden-dim 256 --message-layers 8 --batch-size 32 --epochs 525 --replay-capacity 8000 --sample-fraction 0.05 --seed 20261118 --neural-device mps --no-continuous --compiled-forward --episode-workers 7 --games-per-process 18 --parallel-envs 126
```

- **Replay.** `tools/replay_coordinator_rounds.py` answered the 375 kept
  inference batches through the inference server's own code on the GPU, alone,
  with one network of 256×8 whose embedding tables it filled with random
  numbers, the compiled layers or the layers as written, and reports the best
  of several passes after one untimed pass.
- **Samples.** Two short scripts, in the evidence file, read the serving thread's
  call graph in each sample: its share of samples under given frames, and, for
  the compiling (frames of MLIR, the compiler inside MPSGraph, and of
  `MPSGraphExecutable` being initialized), the PyTorch operation that called it.
- **CPU.** `tools/log_process_load.py` logged every process's CPU counters
  during the run, and the replay process's during one replay.

## Results

The playing went at 276,582 decisions an hour, a little below the 285,875 of the
same setup without the profiler's timers
([record](compiled_layers_126_games_2026_11_18.md)). The inference server
answered 150,320 inference batches of 44.9 states on average and was busy 97.8%
of its time.

| Step of an inference batch | In training | Replayed alone, compiled layers | Replayed alone, as written |
| --- | ---: | ---: | ---: |
| Reading the requests from the pipes | 0.29 ms | | |
| Reading the requests' arrays | 0.22 ms | 0.17 ms | 0.15 ms |
| Collating | 1.13 ms | 0.84 ms | 0.76 ms |
| Making the forward pass's PyTorch calls | 4.78 ms | 2.03 ms | 2.03 ms |
| Waiting for the GPU, copying back, priors | 4.06 ms | 3.52 ms | 5.07 ms |
| Replying | 0.32 ms | | |
| The rest | 0.30 ms | 0.11 ms | 0.09 ms |
| In all | 11.2 ms | 6.7 ms | 8.1 ms |

- **The serving thread computed 62% of the time it served**, 1,062 CPU seconds in
  1,722: its other time it waited for the GPU or for inference requests. Its
  steps on the CPU add up to about its CPU seconds, so it was seldom kept off a
  core while it had work.
- **Making the forward pass's PyTorch calls took 2.4 times as long in training**:
  4.78 ms against 2.03 ms replayed. The compiling, about 2.6 ms an inference
  batch, happens inside that step, as PyTorch builds an operation's graph when it
  is called.

The serving thread in the two samples:

| Share of the serving thread's samples | At 700 seconds | At 1,000 seconds |
| --- | ---: | ---: |
| Compiling graphs (MLIR and initializing MPSGraph executables) | 22.5% | 23.6% |
| All of MPSGraph, compiling and running graphs | 28.6% | 30.8% |
| Waiting for the GPU to finish (`waitUntilCompleted`) | 30.7% | 29.5% |

| PyTorch operation behind the compiling | At 700 seconds | At 1,000 seconds |
| --- | ---: | ---: |
| `Tensor.repeat` | 78.5% | 71.4% |
| Matrix products: `mm`, `bmm`, `addmm` | 21.4% | 21.4% |
| Freeing a cached graph | | 7.2% |

- **New shapes, not only cache releases.** The run released the GPU's caches 75
  times, every 2,048 forward passes and training steps, 30.5 seconds in all, and
  a release drops every compiled graph. But `repeat`'s graph follows the number of
  legal actions in an inference batch, which almost never repeats from one
  inference batch to the next, so it compiles with or without releases.
- **CPU work ran slower in training.** On performance cores the training
  process did 2.30 instructions a cycle at 3.87 GHz, and the replay process alone
  3.23 at 4.17 GHz. The two did different mixes of work, compiling in particular,
  so this is not a like-for-like measure, but collating, which compiles nothing,
  also took a third longer in training, 1.13 ms against 0.84. The game processes
  kept about 6.4 CPU cores busy beside it.
- **The replay's first pass hides the compiling.** Its untimed first pass sees
  each saved inference batch's shapes for the first time. As written it took
  9.3 ms an inference batch against 8.1 in the timed passes, only 1.2 ms more,
  because MPSGraph also keeps compiled graphs on disk, and the training run had
  compiled these very shapes; in its samples, initializing an executable checked
  and created directories of that disk cache.

## What this does and does not show

- **Measured:** one profiled training iteration at 256×8 on the Mac's GPU with
  126 concurrent games and the compiled layers, two 20-second samples of its
  native call stacks, and replays of 375 of its inference batches.
- **About a quarter of the inference server's time in training went to
  compiling graphs for shapes that change with each inference batch**, three
  quarters of it for one `repeat`. That is the largest part of the gap between
  the inference server in training and the forward pass replayed alone.
- **Not measured:** the inference server without those compiles. Replacing
  `repeat` by an operation whose graph does not follow the number of legal actions
  (an index into the same rows, prepared with the other indices), and padding the
  actions' arrays to fixed sizes for the matrix products, are inferred to remove
  most of them, which would make an inference batch about a fifth cheaper in
  training; the CPU cores, about an eighth behind, would then set the pace.
  PyTorch's operations on an NVIDIA GPU are not graphs compiled per shape, so
  the Windows PC is not expected to pay this, which is not measured.
