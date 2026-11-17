# What evaluating three networks costs, and a padded product — 17 November 2026

Each alliance has its own network, and an inference batch holds states of all
three. Its forward pass calls each network's linear layers on that network's
own states, between a split and a join (`_by_network` in
`studies/campaign/neural.py`). After [one grouped call per
layer](grouped_layers_2026_11_17.md) gained nothing on one core, the next
proposal for the GPU was a *padded product*: each network's states padded with
empty ones to the largest network's count, so that each linear layer is one
batched matrix product of the three networks (`torch.baddbmm`). Before building
it, this record measured on the inference batches saved on 17 November how
unequal the three networks' shares are, which sets how much the padding adds,
and how long an inference batch takes in three forms: split by network as now;
every state through one network, which is what one network shared by the three
alliances would cost; and one network over as many states as the padded layout
would hold, a stand-in for the padded product. It also timed each operation of
a forward pass on the Mac's GPU. The [evidence file](network_split_2026_11_17.json)
holds every value.

## Setup

- **Inference batches.** The 853 that `tools/profile_coordinator.py` saved from
  one training iteration of the Mac profile on 17 November, every 200th of the
  run ([record](coordinator_rounds_2026_11_17.md#setup)): 6,331 inference
  requests from eleven-round games, 7.4 states an inference batch, as saved,
  and merged 3, 8 or 16 at a time into one inference batch of 22, 60 or 119
  states, to see the larger inference batches that more concurrent games would
  bring.
- **Three forms of each inference batch**, made by the option `--networks` of
  `tools/replay_coordinator_rounds.py`, added with this record: *three
  networks* (`three`), as saved; *one network* (`one`), every state given to the
  Axis network, so that one network evaluates the same states; and the *padded
  stand-in* (`padded`), one network over the inference batch's states followed by
  copies of them, in order, up to three times as many as its largest network
  has, which is how many states the padded layout would hold. The stand-in has
  one network's PyTorch calls, as the padded product would, and about its
  arithmetic, but its added states are real ones with legal actions, where the
  padded layout's would be empty.
- **Replays.** `tools/replay_coordinator_rounds.py` at commit `86c6d6b`, which
  answers each inference batch with the inference server's own code
  (`SharedEvaluatorServer.answer` in `studies/campaign/shared_evaluator.py`),
  with the 64×2, 256×8 and 512×16 weights of that record, one CPU thread,
  PyTorch 2.14, `MallocNanoZone` unset. On the Mac's GPU, the best of 2 timed
  passes over the inference batches after an untimed one, and as saved only the
  first 300 inference batches (9.1 states each); the three forms alternated,
  three networks, one network, padded stand-in, then the reverse, and the better
  of each form's two runs is kept. On one core, 64×2 only, all 853 inference
  batches as saved and the 284 merged 3, the best of 3 timed passes, three
  alternations of three networks and one network. The Mac's own background
  work, photo analysis and indexing, kept about 2 cores busy throughout.
- **Operations.** `tools/time_forward_operations.py`, added with this record,
  collates a saved inference batch as the inference server does and runs the
  three networks' forward pass (`NetworkStack.forward_packed`) on the GPU, timing
  each operation that PyTorch's dispatcher runs: it waits for the GPU, runs the
  operation 20 times, waits again and divides. It sorts each operation into one
  of three parts of the forward pass: the linear layers; the *per-border work*,
  operations on one row per border of each state (gathering each border's
  source zone and the border's own terms, adding them, GELU, and summing the
  messages into their target zones); and the rest. Three inference batches per
  setting, spread over the run. The operations' times add up to between 3% and
  23% more than the forward pass timed without the waits, most at 64×2.

## The three networks' shares

Counted over the 853 inference batches as saved (a chance state, 1 of the
6,331, counts for each network):

| Network | Share of the states | Share of the legal actions | Inference batches where it had the most states |
| --- | ---: | ---: | ---: |
| Axis | 66.3% | 64.1% | 753 |
| Allies | 20.6% | 34.2% | 82 |
| Comintern | 13.1% | 1.7% | 18 |

In half the inference batches one network had 73% of the states or more
(quartiles 58% and 100%). A padded layout holds, for every network, as many
states as the largest network has, and as many legal actions:

| Inference batches | States each | Padded states | Padded legal actions | Padded policy groups, one product | Padded policy groups, one product per level |
| --- | ---: | ---: | ---: | ---: | ---: |
| As saved | 7.4 | 2.07 times | 2.37 times | 4.37 times | 2.37 times |
| Merged 3 | 22.3 | 2.04 times | 2.19 times | 4.05 times | 2.22 times |
| Merged 8 | 59.7 | 2.03 times | 2.11 times | 3.89 times | 2.15 times |
| Merged 16 | 119.4 | 1.99 times | 2.06 times | 3.80 times | 2.10 times |

The padding does not shrink in larger inference batches: it comes from the Axis
deciding at two thirds of the states in these games, not from chance in small
inference batches. A padded layout would therefore do about twice the
arithmetic of today's forward pass.

## Inference batches on the GPU

Time per inference batch, and its change from the three networks:

| Network | Inference batches | States each | Three networks | One network | Padded stand-in |
| --- | --- | ---: | ---: | ---: | ---: |
| 64×2 | as saved | 9.1 | 2,681 µs | 1,781 µs (−34%) | 2,152 µs (−20%) |
| 64×2 | merged 3 | 22.3 | 3,539 µs | 2,250 µs (−36%) | 3,082 µs (−13%) |
| 64×2 | merged 8 | 59.7 | 4,724 µs | 3,367 µs (−29%) | 5,289 µs (+12%) |
| 64×2 | merged 16 | 119.4 | 6,432 µs | 5,262 µs (−18%) | 9,131 µs (+42%) |
| 256×8 | as saved | 9.1 | 5,843 µs | 3,615 µs (−38%) | 4,610 µs (−21%) |
| 256×8 | merged 3 | 22.3 | 7,532 µs | 4,958 µs (−34%) | 7,682 µs (+2%) |
| 256×8 | merged 8 | 59.7 | 12,046 µs | 8,801 µs (−27%) | 15,438 µs (+28%) |
| 256×8 | merged 16 | 119.4 | 18,449 µs | 15,291 µs (−17%) | 28,797 µs (+56%) |
| 512×16 | as saved | 9.1 | 11,906 µs | 7,727 µs (−35%) | 12,115 µs (+2%) |
| 512×16 | merged 3 | 22.3 | 18,440 µs | 13,099 µs (−29%) | 22,344 µs (+21%) |
| 512×16 | merged 8 | 59.7 | 34,747 µs | 27,576 µs (−21%) | 52,576 µs (+51%) |
| 512×16 | merged 16 | 119.4 | 61,762 µs | 52,332 µs (−15%) | 102,797 µs (+66%) |

The two runs of a form differed by up to 11%, so changes of a few percent are
noise. Where the time went, as the replay divides it: making the PyTorch calls,
and waiting for the GPU to finish and copying the outputs back, with the priors:

| Network | Inference batches | Making the calls, three networks | Making the calls, one network | Waiting for the GPU, three networks | Waiting for the GPU, one network |
| --- | --- | ---: | ---: | ---: | ---: |
| 64×2 | as saved | 1,551 µs | 911 µs | 866 µs | 615 µs |
| 64×2 | merged 16 | 2,004 µs | 1,103 µs | 2,026 µs | 1,779 µs |
| 256×8 | as saved | 3,107 µs | 1,687 µs | 2,474 µs | 1,641 µs |
| 256×8 | merged 16 | 3,520 µs | 1,952 µs | 12,476 µs | 10,913 µs |
| 512×16 | as saved | 4,817 µs | 2,737 µs | 6,793 µs | 4,681 µs |
| 512×16 | merged 16 | 6,807 µs | 3,352 µs | 52,175 µs | 46,318 µs |

- **One network over the same states** was faster than the three networks at
  every size and inference batch size: by 34% to 38% in the inference batches
  as saved, and still by 15% to 18% merged 16 at a time. Making the PyTorch
  calls took 41% to 54% less time in every setting: one network's forward pass
  makes 171 to 451 PyTorch calls on the GPU, against 283 to 871 for the three
  networks ([record](pass_calls_2026_11_17.md#how-many-calls-a-pass-makes)).
  Waiting for the GPU shrank too, by 11% to 34%: the three networks' forward
  pass gives the GPU more and smaller pieces of work, and its splits and joins
  copy the vectors.
- **The padded stand-in** was faster than the three networks only in small
  inference batches: by 20% at 64×2 and 21% at 256×8 as saved, where it held
  19.8 states, and by 13% at 64×2 merged 3. At 512×16 it was 2% slower even as
  saved, and in every larger inference batch it was slower, by up to 42% at
  64×2, 56% at 256×8 and 66% at 512×16, at 119 states. It makes about as few
  PyTorch calls as one network, but the GPU does about twice the arithmetic.

## Inference batches on one core

The same 64×2 inference batches on one core, the inference server's device in
the Mac profile; each form's three runs, the best first:

| Inference batches | States each | Three networks | One network | Forward pass, three networks | Forward pass, one network |
| --- | ---: | ---: | ---: | ---: | ---: |
| As saved, all 853 | 7.4 | 1,278 µs (1,280, 1,321) | 1,081 µs (1,089, 1,123), −15% | 1,016 µs | 818 µs |
| Merged 3 | 22.3 | 3,060 µs (3,128, 3,146) | 2,617 µs (2,662, 2,673), −14% | 2,449 µs | 2,028 µs |

One network took 15% less time per inference batch, as saved and merged; its
forward pass ("making the calls", which on one core is the whole forward pass)
took 19% and 17% less. That is more than the PyTorch calls it saves: one
network makes at most 112 fewer, 146 against 258 when all three alliances have
states in the inference batch
([record](pass_calls_2026_11_17.md#how-many-calls-a-pass-makes)), which at about
0.7 µs each
([record](grouped_layers_2026_11_17.md#what-this-does-and-does-not-show)) come
to at most 0.08 ms of the 0.2 ms. The
three networks' forward pass also copies each state's zone identities, map
facts and border terms out of its network's (`zone_terms` and `border_terms` in
`NetworkStack`), which one network reads in place, and it multiplies smaller
matrices, which one core does less efficiently. Which of these takes the rest
was not measured.

## Where the GPU's time goes

Share of the GPU's time in each part of the three networks' forward pass:

| Network | States | Forward pass | Linear layers | Per-border work | The rest |
| --- | ---: | ---: | ---: | ---: | ---: |
| 64×2 | 10.7 (as saved) | 2.6 ms | 42% | 4% | 54% |
| 64×2 | 87.0 (merged 8) | 3.9 ms | 42% | 6% | 51% |
| 256×8 | 87.0 (merged 8) | 12.5 ms | 41% | 21% | 38% |
| 512×16 | 87.0 (merged 8) | 43.4 ms | 45% | 28% | 28% |
| 512×16 | 170.3 (merged 16) | 79.0 ms | 42% | 32% | 26% |

The states are those of the three inference batches timed, larger than the
averages above. At 512×16, 87 states, the operations were:

| Operation | Share of the GPU's time | Operations per forward pass |
| --- | ---: | ---: |
| Linear layers (`linear`) | 44.8% | 186 |
| Additions (`add`) | 10.2% | 50 |
| GELU (`gelu`) | 8.7% | 136 |
| Joins of vectors side by side (`cat`) | 8.6% | 94 |
| Message sums (`index_add_`) | 7.5% | 19 |
| Gathers (`index_select`) | 6.8% | 42 |
| Layer normalizations (`layer_norm`) | 3.8% | 111 |
| Divisions by the in-degree and others (`div`) | 3.5% | 17 |
| Embedding lookups (`embedding_bag`) | 1.6% | 3 |
| Repeats of the global vector for each zone (`repeat_interleave`) | 1.3% | 16 |
| Others | 3.2% | |

- **The matrix products are less than half of the GPU's time,** 41% to 45% at
  every size. The rest is operations that each read and write whole arrays and
  do little arithmetic with them.
- **The per-border work grows with the network**: 4% to 6% at 64×2, 21% at
  256×8 and 28% to 32% at 512×16. A state has 160 borders and 37 zones, so each
  message-passing layer's per-border arrays are about four times as long as its
  zone arrays, and at 512×16 each of them holds 160 × 512 numbers per state.
- **At 64×2** most of the GPU's time is the rest, about half: there an
  operation's own fixed cost on the GPU outweighs its work.

## What this does and does not show

- **Measured:** each network's share of the states and legal actions in 853
  inference batches saved from one training iteration of eleven-round games,
  and how many states and legal actions a padded layout would hold; on the
  Mac's GPU, the time per inference batch of the three networks, of one
  network over the same states and of one network over the padded count, at
  three network sizes, as saved and merged; on one core, the three networks
  against one network at 64×2; the GPU's time in each operation of the three
  networks' forward pass, in three inference batches per setting.
- **Worked out:** that a padded product would cost about what the stand-in
  costs. It would make about one network's PyTorch calls; its padded states
  would be empty, with no legal actions, but it would pad the legal actions and
  the policy groups as well (above), so its arithmetic is about the stand-in's.
- **Not measured:** a padded product itself; whether one network shared by the
  three alliances learns as well as three (the design document's
  [open question](../../design/README.md#one-network-per-alliance-or-one-shared-network));
  the shares in games of other lengths or later in training; the Windows PC's
  NVIDIA GPU; a compiled forward pass of one network; the operations' times on
  one core.
