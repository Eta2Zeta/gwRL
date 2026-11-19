# The policy readout without a repeat, in training at 256×8 on the GPU — 18 November 2026

In training at 256×8 on the Mac's GPU, about 23% of the inference server's time
went to the GPU's graph framework compiling graphs, 71% to 79% of it for one
`Tensor.repeat` in the policy readout of the hierarchical softmax, whose array
has a row for each legal action of the inference batch
([record](inference_server_profile_gpu_2026_11_18.md)). Commit `fa45792`
replaces the repeat: `_readout` in `studies/campaign/neural.py` adds the
actions' vectors to their groups with one `index_add_` for each level of the
hierarchical softmax, since the groups are already listed level by level. This
record checks the replies and measures the change in training. The
[evidence file](readout_without_repeat_2026_11_18.json) holds every value.

- **The replies are the same.** On one CPU core all 3,681 replies of 60 saved
  inference batches were identical. On the GPU, with the compiled layers, all
  375 saved inference batches gave identical values and priors within 1.6e-7,
  and no reply's most likely action changed.
- **An inference batch took about a quarter less time in training**: 21.5% to
  28.8% less at the same number of states, 22.9% less at the 40 to 80 states of
  steady play, in profiled training iterations with 126 concurrent games. Its
  graph compiling fell from 22.5% and 23.6% of the serving thread's time to
  5.8% and 6.5%, all of it now from matrix products.
- **The profiled training iteration played 29.4% more decisions an hour while
  playing**: 357,981 against 276,582.
- **The CPU cores now set the limit.** With the faster inference server, the
  game processes kept 8.2 CPU cores busy instead of 6.5, and the run a median
  of 9.46 in its half-minute windows, over the owner's allowance of 9. A run of
  6 game processes of 21 games did the same, a median of 9.5 in its first nine
  minutes. Two unprofiled runs of the new code were stopped for that reason, so
  this record has no unprofiled pair.

## How it was measured

- **Replies.** `tools/replay_coordinator_rounds.py` answered the 375 inference
  batches kept from the profiled training iteration of the earlier record with
  the old code (`9fd0fc6`) and the new (`fa45792`), one network of 256×8 with
  random embedding tables, on one CPU core for the first 60 and on the GPU with
  the compiled layers for all 375, saving every reply, and compared them
  (`--compare`). Replayed with every graph already compiled, an inference batch
  took 6.95 ms with the old code and 6.89 with the new.
- **Training.** One training iteration each at 256×8 on the Mac's GPU: 126
  eleven-round games in 7 game processes of 18, 64 simulations a decision, the
  compiled layers, a fresh network, seed 20261118, each from a copy of its
  commit with its compiled engine module, the allocator variable `MallocNanoZone`
  unset. Both were run by `tools/profile_coordinator.py`, which times every step
  of the inference server's inference batches and sampled the training
  process's native stacks for 20 seconds at 700 and 1,000 seconds: the old code
  from 19:06 to 19:36, the new from 21:39 to 22:02. The command is that of the
  [earlier record](inference_server_profile_gpu_2026_11_18.md#how-it-was-measured).
  An unprofiled run of the old code, from 21:10 to 21:39, played 278,505
  decisions an hour while playing, within 1% of its profiled run.
- **CPU cores** come from `tools/log_process_load.py`, one log for each run.

## Results

| Measure | Old code | New code |
| --- | ---: | ---: |
| Decisions per hour while playing | 276,582 | 357,981 |
| States per inference batch | 44.9 | 44.7 |
| Serving an inference batch | 11.2 ms | 8.6 ms |
| Making the forward pass's PyTorch calls | 4.78 ms | 2.68 ms |
| Waiting for the GPU, copying back, priors | 4.06 ms | 3.77 ms |
| Collating | 1.13 ms | 1.11 ms |
| Reading, receiving, replying and the rest | 1.13 ms | 0.88 ms |
| Inference server busy | 97.8% | 97.4% |
| Compiling graphs, share of the serving thread's samples | 22.5%, 23.6% | 5.8%, 6.5% |
| Game processes' CPU cores | 6.45 | 8.20 |
| The run's CPU cores, median half-minute window | 7.74 | 9.46 |
| The run's CPU cores, highest half-minute window | 9.54 | 10.97 |
| Game processes' wait for a core, per CPU second | 1.21 s | 1.17 s |

Mean serving time of an inference batch, by its number of states:

| States | Old code | New code |
| ---: | ---: | ---: |
| 1 | 3,144 µs | 2,717 µs |
| 8 | 6,695 µs | 4,266 µs |
| 16 | 8,242 µs | 5,790 µs |
| 24 | 9,459 µs | 6,849 µs |
| 32 | 10,650 µs | 7,649 µs |
| 40 | 11,633 µs | 8,416 µs |
| 48 | 12,074 µs | 8,992 µs |
| 56 | 12,601 µs | 9,815 µs |
| 64 | 12,726 µs | 10,135 µs |
| 72 | 13,838 µs | 11,066 µs |

- **Making the calls lost the compiling.** That step fell by 2.1 ms an
  inference batch, close to the 2.6 ms that compiling took in the old code. The
  remaining compiling is the matrix products of the layers that read the
  actions' vectors: `mm`, `bmm` and `addmm`, whose arrays too have a row for
  each legal action.
- **The decisions an hour rose more than the inference batch got cheaper**,
  29.4% against about 23%. Both runs played different games, and single runs of
  one setting differed by 5% to 6% on 18 November
  ([record](gpu_training_compiled_2026_11_18.md)).
- **The game processes took the freed time as CPU.** A game thread computes about
  1.6 ms of engine work for each network evaluation, so a faster inference
  server makes the game processes compute more each second. With the new code
  they kept 8.2 CPU cores busy with 7 processes and 8.9 with 6, and the run
  about 9.5, where the old code's runs had kept about 7.7.

## What this does and does not show

- **Measured:** identical replies on one CPU core and replies within float
  rounding on the GPU; one profiled training iteration each of the old and the
  new code at 256×8 on the GPU with 126 concurrent games in 7 game processes of
  18; the CPU load of the new code with 6 game processes of 21 for nine minutes.
- **The repeat was the largest share of the inference server's training-time
  overhead**: without it an inference batch of steady play costs about 23% less,
  and the profiled run played about 29% more decisions an hour.
- **With the new code, 126 concurrent games keep more CPU cores busy than the
  allowance of 9.** The supervisor's count, one core for each game process, the
  inference server and itself, accepted both layouts
  ([Q-005](../../questions.md#q-005-the-supervisors-count-of-cores)).
- **Not measured:** the decisions an hour of a layout that stays within the
  allowance, such as fewer game processes or fewer concurrent games; an
  unprofiled matched pair; padding the actions' arrays to fixed lengths, which
  would remove most of the remaining compiling.
