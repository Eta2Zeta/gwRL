# One call per layer for the three networks, tried and removed — 17 November 2026

The second part of the inference server work was to cut the PyTorch calls of a
forward pass. With states of all three alliances, each network's linear layers
are applied to its own states in turn, between a split and a join, which is 43%
to 50% of the calls ([record](pass_calls_2026_11_17.md#how-many-calls-a-pass-makes)).
A grouped matrix product made each such layer one call for all three networks.
It cut a three-alliance forward pass of the 64×2 network from 258 calls to 176,
with replies equal up to rounding, but on one core it was no faster, and on the
Mac's GPU the grouped product is slower than the split. It was removed again. The
[evidence file](grouped_layers_2026_11_17.json) holds every value.

## What was tried

Commit `4d1af03`, removed in the next, changed only `studies/campaign/neural.py`.
In a network stack on the CPU, without gradients, every kind of layer applied per
network became one call for all of them: linear layers, blocks, heads, and the
12 heads of the policy's staged softmax (4 levels for each of 3 networks).

- **Linear layers** used `torch._grouped_mm`, a private PyTorch function that
  multiplies each group of rows by its own matrix. Each layer's bias became one
  more input, which a column of ones multiplies. Because the product needs rows
  of a multiple of 16 bytes, inputs and outputs were padded to multiples of four
  numbers, with zeros.
- **Layer normalizations** became one call without scale and shift, then one
  call with each row's own.

The training path, with gradients, was unchanged.

## Results

| Network | States | Calls before | Calls after | Forward pass before | Forward pass after |
| --- | ---: | ---: | ---: | ---: | ---: |
| 64×2 | 1 | 146 | 138 | 0.386 ms | 0.414 ms |
| 64×2 | 8, three alliances | 258 | 176 | 1.415 ms | 1.361 ms |
| 64×2 | 64 | | | 9.06 ms | 9.59 ms |
| 256×8 | 1 | 266 | 258 | 2.18 ms | 1.80 ms |
| 256×8 | 8, three alliances | 510 | 350 | 10.85 ms | 10.80 ms |
| 256×8 | 64 | | | 88.4 ms | 87.3 ms |
| 512×16 | 8, three alliances | 846 | 582 | | |

The forward pass times are means of two alternated runs of
`tools/benchmark_network_sizes.py` on one core, whose 8 and 64 states are random
samples of all three alliances; the 64-state runs of the new code differed by
17%, 10.35 and 8.82 ms.

- **Replies.** On the 853 inference batches saved on 17 November, priors moved
  by at most $1.2 \times 10^{-7}$ and values by at most $3.8 \times 10^{-5}$,
  and the most likely action changed at none of the 6,330 states with actions.
- **Real inference batches.** Replayed three times each, alternately, the old
  code took 1,320, 1,382 and 1,351 µs per inference batch and the new 1,316,
  1,388 and 1,309: 1% less on average, within the replays' spread.
- **One layer alone.** On one core the grouped product was faster than the
  split: 7.6 against 19.5 µs for 296 rows from 64 to 64 numbers. On the Mac's
  GPU it was about twice as slow: 189 against 94 µs.

## What this does and does not show

- **Measured:** how many calls a forward pass makes, and how long it takes, with
  and without the grouped products on one core; their replies on real inference
  batches; one layer on the GPU.
- **Worked out:** cutting 82 calls from an 8-state forward pass saved about
  0.05 ms, about 0.7 µs a call, so on one core a call's overhead is well below
  the bound of about 2.1 µs that
  [the calls record](pass_calls_2026_11_17.md#what-the-calls-cost) gives. At
  about 24 billion operations a second, an 8-state forward pass of the 64×2
  network spends about 1.1 ms of its 1.4 ms on arithmetic. On one core,
  then, fewer calls cannot speed it up much.
- **Not measured:** a whole forward pass with grouped products on a GPU, and
  other ways to cut calls on a GPU, such as one padded product per layer
  (`torch.bmm`) or a compiled forward pass.
