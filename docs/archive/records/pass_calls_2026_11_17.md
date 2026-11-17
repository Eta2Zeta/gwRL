# The PyTorch calls of a network pass — 17 November 2026

A pass of the network is not computed number by number: the coordinator's code
makes a list of calls to PyTorch, each applying one function to whole arrays,
such as one matrix product or the GELU curve over every number of an array.
These measurements count the calls of one pass and time how long the
coordinator's code takes to make them, on one CPU core and on the Mac's GPU. A
pass of the 64×2 network is 146 calls on one core when its positions belong to
one alliance and 258 when they belong to all three; a message layer is 20
calls for each network in the pass. On the GPU, making the calls takes the
coordinator's core about 5.6 µs a call, and laying the positions out and making
the calls take about 70% of a 64×2 pass. The
[design document](../../design/README.md#92-running-training-on-the-mac)
explains what a pass is made of; the [evidence file](pass_calls_2026_11_17.json)
holds every value.

## Setup

`tools/benchmark_network_sizes.py`, extended with this record, on the network
code of `50aaa92`: the 624 positions of [the 14 November
measurements](network_and_search_cost_2026_11_14.md#the-network), every sixth
decision of two scripted eleven-round games, and the three alliance networks
with random column tables, stacked as the coordinator stacks them. It counts the
calls that reach PyTorch's dispatcher during one pass, after a first, uncounted
pass has filled the stack's caches as in training, and separates the calls that
only give another view of an array's numbers, without arithmetic or copying. It
times each pass as before and, beside it, the time until
`shared_evaluator.forward_prepared` returns: the positions laid out, copied and
every call made. On one core the calls compute in that time; on the GPU they
are only handed to it, and the pass ends when the GPU has finished and the
outputs are copied back. PyTorch 2.14 (`tmp/gpu-mps-env`), `MallocNanoZone`
unset, one CPU thread, the Mac's load average 1.7 to 2.8 before the runs.

## How many calls a pass makes

| Network | One alliance, one core | One alliance, GPU | Three alliances, one core | Three alliances, GPU |
| --- | ---: | ---: | ---: | ---: |
| 64×2 | 146 | 171 | 258 | 283 |
| 256×8 | 266 | 291 | 510 | 535 |
| 512×16 | 426 | 451 | 846 | 871 |

- The count does not depend on the number of positions: one position and 8
  positions of one alliance make the same calls.
- One more message layer adds 20 calls for one network: 3 `linear`, 3 `gelu`,
  3 `add`, 2 `layer_norm`, 2 `cat`, and one each of `index_select`,
  `new_zeros`, `index_add_`, `div`, `repeat_interleave`, `view` and `mean`. The
  rest of a pass is 106 calls on one core: 146 = 2 × 20 + 106 at 64×2.
- With positions of all three alliances each network's learned layers are
  called on its own positions, with a split before and a join after: 22 calls
  more per message layer and 68 more elsewhere, 43% to 50% of the pass's calls.
- On the GPU a pass makes 25 calls more: the positions' arrays travel to the GPU
  in two copies and are then cut into views (`batch_tensors` in
  `studies/campaign/neural.py`).
- Of the calls, 41 to 149 only give a view of an array: 41 of 146 on one core
  at 64×2 for one alliance, 149 of 871 on the GPU at 512×16 for three.

## What the calls cost

| Network | Positions per pass | One core: pass | GPU: calls made | GPU: pass | Calls made, share of the GPU's pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| 64×2 | 1 | 0.45 ms | 0.95 ms | 1.48 ms | 64% |
| 64×2 | 8 | 1.67 ms | 2.11 ms | 3.02 ms | 70% |
| 64×2 | 64 | 9.73 ms | 3.30 ms | 4.79 ms | 69% |
| 64×2 | 256 | 36.5 ms | 7.54 ms | 11.2 ms | 67% |
| 256×8 | 1 | 1.85 ms | 1.65 ms | 2.70 ms | 61% |
| 256×8 | 8 | 11.7 ms | 3.35 ms | 5.37 ms | 62% |
| 256×8 | 64 | 85.3 ms | 5.37 ms | 12.9 ms | 42% |
| 256×8 | 256 | 330 ms | 8.77 ms | 34.3 ms | 26% |
| 512×16 | 1 | 10.4 ms | 2.49 ms | 4.66 ms | 53% |
| 512×16 | 8 | 53.5 ms | 5.57 ms | 12.5 ms | 44% |
| 512×16 | 64 | 323 ms | 7.51 ms | 36.3 ms | 21% |
| 512×16 | 256 | 1,213 ms | 12.2 ms | 121 ms | 10% |

- **On one core**, a pass of the 64×2 network over one position takes 0.45 ms
  for 146 calls, 3.1 µs a call. In passes of 256 the same core does that
  network's arithmetic at about 24 billion operations a second, so one
  position's 3.4 million would take about 0.14 ms there. Small arrays compute
  less efficiently, so the remaining 0.31 ms, at most about 2.1 µs a call, is an
  upper bound on what starting the calls costs (worked out, not measured).
- **On the GPU**, making the calls of a one-position pass takes the
  coordinator's core 5.5 to 5.7 µs a call at every size. The time grows with
  the positions, which have to be laid out and copied: 7.5 ms at 64×2 with 256
  positions. For 64×2 the coordinator's own work is about two thirds of every
  pass; for 512×16 it falls to a tenth in passes of 256, where the GPU's
  arithmetic takes the rest.

## What this does and does not show

- **Measured:** how many calls a pass makes, by network size, device and the
  alliances of its positions; how long passes take, and how long the
  coordinator's code takes to make their calls, on one core and on the GPU.
- **Worked out:** the upper bound of about 2 µs to start a call on one core.
- **Not measured:** how a call's start divides between Python, PyTorch's
  dispatcher and memory, which [a 14 November profile of a training
  batch](coordinator_one_pass_2026_11_14.md#where-the-coordinators-time-went)
  divided for a whole pass; how much of the GPU's time between its arithmetic is
  spent waiting for calls; and anything in training runs.
