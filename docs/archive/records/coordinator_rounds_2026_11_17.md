# Where a coordinator round's time goes — 17 November 2026

The coordinator limits self-play on the Mac. These measurements are the
baseline for making it cheaper ([the coordinator's
levers](../../design/README.md#93-what-a-larger-network-and-a-longer-search-cost)).
A profiled training batch of the Mac profile showed where the coordinator's
time went and kept every 200th of its rounds. Replaying those 853 real rounds
through the coordinator's code showed how a round's time divides on one core and
on the Mac's GPU, with networks of 64×2, 256×8 and 512×16, as saved and merged
into larger passes. The batch also showed a tail: its longest game played alone
for the last tenth of the playing time. Two of the coordinator's levers were
tried on the same rounds and did not pay as they stand: half precision made
every round slower, and the pass compiled as written was never faster. The
[evidence file](coordinator_rounds_2026_11_17.json) holds every value.

## Setup

- **The batch.** `tools/profile_coordinator.py` ran one batch of the Mac
  profile at commit `9a88a57`, as the supervisor runs one, with the settings of
  the [16 November batches](engine_speed_in_training_2026_11_16.md): 6 game
  processes of 4 games, 24 eleven-round games, 64 simulations, depth 16, fresh
  64×2 networks evaluated on one core by one coordinator, seed 20261104. It
  timed each step of the coordinator's rounds, kept every 200th round's
  requests, and recorded the coordinator's native call stacks with macOS's
  `sample` for 20 seconds at 120 and 240 seconds into the run.
  `tools/log_process_load.py` measured the batch's processes and the Mac's
  other work. Timing the steps costs the coordinator a few percent, so the
  batch's speed is not compared with other batches; its shares are.
- **The replays.** `tools/replay_coordinator_rounds.py`, extended with this
  record, writes each saved round's requests into buffers as the game threads
  write them and answers them with the coordinator's own code
  (`SharedEvaluatorServer.answer` in `studies/campaign/shared_evaluator.py`),
  with the pipes replaced by stand-ins, so the pipes' own cost is left out. It
  times each round's steps: reading the requests' arrays, laying the positions
  out, making the pass's calls, collecting the outputs (on the GPU: waiting for
  it to finish, copying the outputs back, then the priors) and the rest of
  answering. Networks of 64×2, 256×8 and 512×16, their column tables filled with
  random numbers of spread 0.5; the rounds as saved, and merged 3, 8 or 16 at a
  time into one round, to see larger passes of real positions. One CPU thread,
  PyTorch 2.14 (`tmp/gpu-mps-env`), the best of 3 timed passes over all rounds
  after an untimed one, `MallocNanoZone` unset, nothing else running but the
  Mac's own background work. The same replay of unchanged code took 1,274 to
  1,441 µs a round on one core in three runs over 15 minutes, and 2,624 to
  2,753 µs on the GPU, so differences below about 13% on one core and 5% on the
  GPU are noise.
- **Half precision and compiling.** The same replays under PyTorch's automatic
  mixed precision (`torch.autocast`), float16 on the GPU and bfloat16 on one
  core, which does the matrix products in 16 bits and keeps sums and
  normalizations in 32; and with the pass (`neural._forward`) compiled by
  `torch.compile` with dynamic shapes, on the GPU under the coordinator's
  `torch.inference_mode` and on one core under `torch.no_grad`, against an
  uncompiled baseline under `no_grad` too. For these, the code changed in three
  places, each the same in 32 bits: the message sum and the
  policy's staged softmax add their terms in the terms' own type (`_forward` and
  `_conditional_log_softmax` in `studies/campaign/neural.py`), and the
  coordinator turns the outputs into 32-bit numbers before numpy reads them
  (`collect` in `studies/campaign/shared_evaluator.py`). Replayed after these
  changes, the 32-bit replies on one core were identical to those before; on the
  GPU priors were equal within $1.7 \times 10^{-7}$ and values within
  $2.1 \times 10^{-5}$. Each run's replies were compared with the
  32-bit, uncompiled replies of the same device and rounds.

## The training batch

The batch played 24 games, 24,792 decisions, in 333.0 seconds: 268,000
decisions an hour while playing, with its steps timed and about 2.8 cores of
other work on the Mac (the mean of half-minute windows; the batch itself kept
6.8 cores busy). The coordinator answered 1,274,778 requests in 170,712 rounds,
7.47 a round, in one pass each.

| Step of a round | Share of the coordinator's time | Per round |
| --- | ---: | ---: |
| Waiting for a request | 9.4% | 182 µs |
| Reading the requests' notes from the pipes | 1.8% | 34 µs |
| Reading each request's arrays in shared memory | 1.8% | 35 µs |
| Laying the positions out (`pack_zone_arrays`) | 13.0% | 253 µs |
| The pass (`neural._forward`) | 66.6% | 1,297 µs |
| Turning outputs into priors and values (`collect`) | 2.3% | 46 µs |
| Sending the replies | 2.8% | 54 µs |
| The rest: grouping, chance averages, statistics | 1.4% | 27 µs |

A pass of one position took 0.40 ms, and 16.7% of the passes held one. A pass
of 4 positions took 0.82 ms, of 8 1.41 ms, of 10 1.66 ms and of 12 1.87 ms. A
line through all of them, weighted by how many passes held each number of
positions, is 0.27 ms plus 0.137 ms a position.

**Native samples.** In the two 20-second samples the coordinator's main thread
was busy 99.5% of the time: its waiting fell at the start and the end of the
batch. Its busy samples, by the code at the top of the stack:

| Kind of work | At 120 s | At 240 s |
| --- | ---: | ---: |
| PyTorch's routines: arithmetic and copies | 38.1% | 38.1% |
| Matrix products (Apple's Accelerate) | 4.9% | 5.2% |
| Python's interpreter | 19.3% | 19.9% |
| numpy, laying the positions out | 10.3% | 10.0% |
| PyTorch's dispatch and bookkeeping | 8.8% | 8.4% |
| PyTorch's Python binding | 2.6% | 2.3% |
| Memory: allocating, clearing, returning to the system | 8.0% | 8.4% |
| Memory: copying | 4.2% | 4.0% |
| The pipes | 1.9% | 1.8% |
| Other | 1.9% | 2.0% |

The GELU curve alone took 14% of the busy samples at 120 seconds. So about 43%
of the coordinator's busy time was arithmetic, and about 31% was Python's and
PyTorch's own work around the calls; the samples do not say which call or step
a sample belongs to. The split is by library and routine
(`samples_by_kind` in the evidence file).

## The batch's tail

The 24 games started together, one on each game thread, and the batch ended
with the last of them. 23 games ended between 231 and 299 seconds; the longest,
1,445 decisions, played alone until 332 seconds. So for the last tenth of the
playing time the coordinator's rounds held one position each, and on average
20.1 of the 24 games were in flight. The saved rounds show the same: in the
first seven tenths of them a round held 7.7 to 10.4 requests on average, in the
last two tenths 1.8 and 1.0.

While the others played, each game played 3.4 to 4.0 decisions a second. At
their median, 3.67, the longest game had made about 1,097 decisions by
299 seconds and the other 348 alone. Without those 348 the batch would have
played 24,444 decisions in 299 seconds, about 294,000 an hour instead of
268,000: the tail cost about 9% (worked out from each game's decisions and
time, `worker_seconds` in the run's manifest).

## Replayed rounds on one core

| Network | Positions a round | Time a round | Time a position | Laying out | Making the calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| 64×2, as saved | 7.4 | 1,441 µs | 194 µs | 15% | 79% |
| 64×2, 3 merged | 22.3 | 3,434 µs | 154 µs | 13% | 80% |
| 64×2, 8 merged | 59.7 | 9,499 µs | 159 µs | 12% | 81% |
| 256×8, as saved (first 200) | 8.6 | 11,650 µs | 1,362 µs | 2% | 96% |
| 512×16, as saved (first 100) | 7.8 | 45,928 µs | 5,903 µs | 1% | 99% |

On one core the calls compute as they are made, so making them is the pass. At
64×2 a round as saved took 1,441 µs, 13% less than the coordinator's 1,658 µs
of answering a round in the batch, where the game processes shared the Mac's
caches and memory. A line through the rounds as saved
is 297 µs plus 154 µs a position. Beyond about 22 positions a round, a
position's time no longer falls.

## Replayed rounds on the GPU

| Network | Positions a round | Time a round | Time a position | Laying out | Making the calls | Waiting for the GPU and copying back |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 64×2 | 7.4 | 2,750 µs | 370 µs | 224 µs | 1,618 µs | 848 µs |
| 64×2 | 22.3 | 3,994 µs | 179 µs | 476 µs | 2,246 µs | 1,133 µs |
| 64×2 | 59.7 | 5,237 µs | 88 µs | 1,094 µs | 2,294 µs | 1,533 µs |
| 64×2 | 119.4 | 7,410 µs | 62 µs | 2,054 µs | 2,505 µs | 2,208 µs |
| 256×8 | 7.4 | 5,937 µs | 800 µs | 258 µs | 3,363 µs | 2,236 µs |
| 256×8 | 22.3 | 8,484 µs | 381 µs | 579 µs | 4,077 µs | 3,651 µs |
| 256×8 | 59.7 | 13,468 µs | 226 µs | 1,308 µs | 4,523 µs | 7,203 µs |
| 256×8 | 119.4 | 20,282 µs | 170 µs | 2,298 µs | 4,480 µs | 12,770 µs |
| 512×16 | 7.4 | 11,742 µs | 1,582 µs | 290 µs | 5,372 µs | 5,990 µs |
| 512×16 | 22.3 | 19,256 µs | 864 µs | 658 µs | 6,472 µs | 11,923 µs |
| 512×16 | 59.7 | 35,321 µs | 592 µs | 1,225 µs | 6,614 µs | 27,104 µs |
| 512×16 | 119.4 | 61,546 µs | 515 µs | 2,207 µs | 6,751 µs | 51,863 µs |

The rows of 7.4 positions are the rounds as saved; the others merge 3, 8 and 16
of them. "Waiting for the GPU and copying back" is the collecting step, whose
priors take about 36 µs a round on one core.

- **At today's round sizes** the GPU is slower than one core at 64×2, 2,750 µs
  a round against 1,441, and faster from 256×8 on: 1.7 times at 256×8 and 3.7
  times at 512×16.
- **Making the calls** takes 46% to 59% of a round as saved, 1.6 to 5.4 ms,
  more for networks with more layers, whose passes make more calls
  ([record](pass_calls_2026_11_17.md#how-many-calls-a-pass-makes)). It grows
  little with the positions.
- **Waiting for the GPU** grows with the positions. At 512×16 in rounds of 119
  positions it is 84% of the round, about 3 trillion operations a second (at the
  [14 November count](network_and_search_cost_2026_11_14.md#the-network) of
  1,320 million a position): there the GPU's arithmetic sets the pace. At 64×2
  it is never more than 2.2 ms, with at most about 400 million operations in a
  round, so there the GPU spends its time on the calls rather than on
  arithmetic (inferred).
- **Laying the positions out** costs 17 to 30 µs a position on the coordinator's
  core, whatever the network: at 64×2 in rounds of 119 it is 28% of the round.
- The rates agree with the
  [14 November benchmark](network_and_search_cost_2026_11_14.md#the-network)
  within 16%: in rounds of 59.7 positions 11,400, 4,430 and 1,690 positions a
  second, against its 9,840, 4,500 and 1,640 in passes of 64.

## Half precision

| Network | Positions a round | 32 bits | Half precision | Largest prior change | Most likely move changed | Largest value change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 64×2 | 7.4 | 2,750 µs | 3,247 µs | 0.00014 | 3 of 6,330 | 0.08 |
| 64×2 | 59.7 | 5,237 µs | 6,084 µs | 0.00016 | 4 of 6,325 | 0.09 |
| 256×8 | 7.4 | 5,937 µs | 7,296 µs | 0.00017 | 5 of 6,330 | 0.08 |
| 256×8 | 59.7 | 13,468 µs | 14,173 µs | 0.00017 | 3 of 6,325 | 0.08 |
| 512×16 | 7.4 | 11,742 µs | 14,053 µs | 0.00023 | 10 of 6,330 | 0.10 |
| 512×16 | 59.7 | 35,321 µs | 39,121 µs | 0.00022 | 10 of 6,325 | 0.10 |

On the GPU, half precision made every round slower: by 18% to 23% in the rounds
as saved and by 5% to 16% in rounds merged 8 at a time. It adds calls that turn
numbers between 16 and 32 bits, and both making the calls and waiting for the
GPU grew. The replies stayed close: priors moved by at most 0.00023, the most
likely move changed at up to 10 of the 6,330 positions, and values moved by at
most 0.10, that is 10 points of final score. On one core bfloat16 made a round
92% slower, 2,769 µs against 1,441, and changed the most likely move at 170
positions and values by up to 0.70.

## Compiling

| Device, network and rounds | Uncompiled | Compiled | Time to compile | Largest prior change |
| --- | ---: | ---: | ---: | ---: |
| GPU, 64×2, as saved | 2,750 µs | 2,943 µs | 44 s | $1.5 \times 10^{-7}$ |
| GPU, 256×8, as saved | 5,937 µs | 6,244 µs | 70 s | $1.8 \times 10^{-7}$ |
| One core, 64×2, as saved, `no_grad` | 1,348 µs | 1,638 µs | 18 s | $1.2 \times 10^{-7}$ |
| One core, 64×2, 3 merged, `no_grad` | 3,407 µs | 3,830 µs | 96 s | not compared |

Compiled as it is written, the pass was never faster: 5% and 7% slower on the
GPU and 12% and 21% slower on one core. In every run PyTorch compiled it again
for each new mix of positions until it reached its limit of 8 compilations of
one function, after which it ran the other mixes uncompiled (its log says it
hit `recompile_limit`). On the GPU the compiler also stopped at a numpy
conversion inside the pass, which split each compilation in two. Three runs
failed: on the GPU, rounds merged 8 at a time, at 64×2 and 256×8, made the
compiler write GPU code that did not build, in an atomic addition; and on one
core under the coordinator's `torch.inference_mode`, a check of PyTorch's own
failed on an array made from numpy inside the pass. A pass that compiles well
would have to be written for it: its arrays prepared before it, and a few fixed
sizes of pass.

## What this does and does not show

- **Measured:** where the coordinator's time went in one profiled batch, and
  what its native samples were doing; when each game of the batch ended; the
  time of each step of 853 saved rounds replayed on one core and on the GPU,
  with three network sizes, as saved and merged; the same rounds in half
  precision and with the pass compiled, and how far their replies moved.
- **Worked out:** the tail's cost, from each game's decisions and time; the
  split of busy time into arithmetic and the work around it, from the native
  samples' libraries.
- **Not measured:** the pipes' cost in replays, which use stand-ins; merged
  rounds in training, which need more games in flight; whether the tail is as
  long in other batches (the 16 November batches' run folders are gone); and
  anything on the Windows PC.
