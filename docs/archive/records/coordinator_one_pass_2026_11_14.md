# One network pass per coordinator round — 14 November 2026

On the Mac the coordinator, the process that evaluates every game's positions,
limited self-play: it was busy about 90% of the time
([record](supply_cache_2026_11_14.md#training-batches)). A profile of a training
batch shows why. Each round of waiting requests took one network pass per
alliance with positions waiting, 2.3 passes on average, and a pass cost about
0.4 ms before any position was added, more than two positions' worth of
arithmetic. Now the coordinator answers each round with one pass of the three
networks, in which each network's layers read only its own alliance's positions.
On 860 rounds saved from a real batch, a round takes 32% less time, and the
replies are the same up to float rounding. In matched training batches the
coordinator used 16% less CPU per decision, the training used 9.9 of its 11
cores instead of 8.9, and decisions per hour while playing rose by 13%, from
about 222,500 to 252,200. The [design document](../../design/README.md#92-running-training-on-the-mac)
describes the coordinator; the [evidence file](coordinator_one_pass_2026_11_14.json)
holds the exact values.

## Where the coordinator's time went

**Setup.** `tools/profile_coordinator.py`, new with this record, runs a training
batch exactly as the supervisor does, but its coordinator times each step of
every round and keeps every 200th round's requests for replaying them later.
macOS's `sample` recorded the coordinator's native call stacks for 20 seconds at
150 and at 330 seconds. One batch of the Mac profile at commit `0060135`: 8 game
processes of 4 games, 32 eleven-round games, fresh 64×2 networks, 64 simulations,
depth 16, seed 20261104. Other work used about 4 cores of the Mac during this
batch, so its speed is not compared with other batches; its shares are.

| Step of a round | Share of the coordinator's time | Per request |
| --- | ---: | ---: |
| Waiting for a request | 5.8% | 21 µs |
| Reading the requests from the pipes | 1.7% | 6 µs |
| Mapping each request's arrays in shared memory | 1.6% | 6 µs |
| Laying the positions out (`pack_zone_arrays`) | 12.5% | 45 µs |
| Network passes | 71.2% | 258 µs |
| Turning outputs into priors and values (`collect`) | 2.0% | 7 µs |
| Sending the replies | 2.5% | 9 µs |
| The rest: grouping, chance averages, statistics | 1.4% | 5 µs |

A round answered 8.85 requests in 2.26 passes, 3.9 positions per pass; 28% of
the passes held a single position.

| Positions in a pass | Share of passes | Time per pass |
| ---: | ---: | ---: |
| 1 | 28% | 0.57 ms |
| 2 | 19% | 0.71 ms |
| 3 | 14% | 0.86 ms |
| 4 | 9% | 1.02 ms |
| 8 | 4% | 1.68 ms |
| 16 | 0.3% | 2.53 ms |

So a pass cost about 0.42 ms plus 0.15 ms per position. In the native samples
of the coordinator's thread, Python's interpreter took about a fifth of its
time, PyTorch's per-operation dispatch an eighth, and allocating and freeing
memory, with the system returning freed pages, a seventh. The arithmetic itself
(the GELU curve, the other element-wise operations, the column lookups and the
matrix products) took about two fifths.

## What changed

- **One pass for the three networks** (`NetworkStack` in
  `studies/campaign/neural.py`). The coordinator builds it once per batch, when
  it first answers, from the three alliances' networks. Their three column
  tables are laid end to end, and each answer's column is shifted to its own
  network's part (`pack_zone_arrays` in `studies/campaign/features.py`, given
  how many positions each network has). The positions come grouped by network,
  so each network's rows of every kind (zones, positions, moves and policy
  groups) are consecutive, and each learned layer and layer normalization runs
  once per network on its own rows. The fixed terms that are the same for every
  position, the zones' identity vectors and fixed facts and each message
  layer's border facts, are worked out once per batch. A chance position, which
  all three networks rate, appears once for each, as before.
- **The server** (`SharedEvaluatorServer.answer` in
  `studies/campaign/shared_evaluator.py`) lays a round's positions out once and
  makes one pass. Its statistics count passes (`network_passes` in a run's
  manifest), one per round.
- **The policy readout** (`_readout` in `neural.py`). The probability of a move
  is built in stages ([section 6.8](../../design/README.md#68-the-action-probabilities)).
  Each stage used to take its own softmax, ten operations each, five times in
  all. Now the groups of all four levels and the moves are scored together and
  one softmax pass normalizes each among those sharing its parent.
- **Layers called as functions.** The pass applies each layer with its own
  parameters (`F.linear`, `F.layer_norm`, `F.gelu`) instead of calling the layer
  as a module, which adds Python work to every call. Training and
  `NeuralEvaluator` use the same pass, with one network.

## The same outputs

**Networks.** Three fresh 64×2 networks, one per alliance, whose three column
tables were filled with random numbers (normal, standard deviation 0.5, seed
20261114): a fresh network's rows are all zero, and a check with them would
compare sums of zeros.

**The coordinator's replies.** `tools/replay_coordinator_rounds.py`, new with
this record, replays saved rounds through a checkout's own
`SharedEvaluatorServer.answer`: each request's arrays are written into a buffer
as a game process writes them, and the replies are kept instead of sent. On the
860 rounds saved by the profile, 7,774 requests, 7,764 replies of the new
coordinator were identical to the old one's to the last bit. In the other ten,
a move's probability differed by at most $3.9 \times 10^{-8}$; every value was
identical.

**One network, as in training.** For the first 300 saved rounds, each
alliance's positions went through its network alone, as training and
`NeuralEvaluator` run it: 682 of 688 passes gave identical outputs, and the
others' logits differed by at most $4.8 \times 10^{-7}$, float rounding from
adding the stages' log-probabilities in another order; values were identical.
In 20 training-like steps on 8 positions each, every gradient agreed to within
$1.7 \times 10^{-6}$ of its parameter's largest gradient.

**Tests.** A stacked pass gives each network the outputs of its own pass
(`test_a_stack_gives_each_network_its_own_outputs_in_one_pass`), and with the
heads' last layers at zero, a move's probability is the product of $1 / n$ along
its branch of the group tree, $n$ being the number of siblings at each stage
(`test_the_readout_multiplies_the_probabilities_along_each_branch`, both in
`tests/test_campaign_neural.py`).

## Time per round, replayed

The same 860 rounds, one tensor thread, the training's PyTorch 2.14, the best
of three passes over all rounds after one warm-up pass:

| | Before | After |
| --- | ---: | ---: |
| Time per round | 2,348 µs | 1,603 µs |
| Time per request | 260 µs | 177 µs |

After the change, a round took 233 µs to lay its positions out, 1,279 µs for
the pass and 34 µs for turning outputs into priors and values. In the pass, the
GELU curve now takes about 30% of the operators' time, mostly in the border
messages ([section 6.6](../../design/README.md#66-message-passing-layers-messages-along-the-borders)): it
belongs to the network's design. Running each round's positions through one
network in one pass with the old code, an upper bound for merging the passes
without separate layers per network, took 1,638 µs per round; the stacked pass
is faster still because the readout and the layer calls take fewer operations.

## Matched training batches

**Setup.** As in the [12 November batches](coordinator_lookups_2026_11_12.md#matched-training-batches):
`--profile mac` (8 game processes of 4 games, coordinator on the CPU, PyTorch
2.14), 32 eleven-round games with learning, fresh 64×2 networks, 64 simulations,
depth 16, seed 20261104. The code before ran from a clean copy of commit
`0060135`, the code after from a clean copy of this change. The six batches ran
one after another in the order of the table. `ps` logged every process's CPU
time and memory every 5 seconds.

The Mac was not quiet. In five batches, other work (the window server, the
Claude and Chrome apps, iCloud, updaters) used 2.1 to 2.6 cores on average; in
After 2, Spotlight indexing, Chrome and FaceTime raised it to 3.5 cores, and that
batch is shown but not compared. With 11 of the 14 cores for training, that
load leaves little to spare, so these rates are lower than in the
[batches earlier the same day](supply_cache_2026_11_14.md#training-batches) and
are compared only with each other.

| Batch, in the order run | Before 1 | After 1 | Before 2 | After 2 | After 3 | Before 3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Other work, cores | 2.55 | 2.28 | 2.29 | 3.50 | 2.53 | 2.11 |
| Decisions per hour while playing | 210,222 | 241,918 | 220,195 | 216,579 | 262,391 | 237,071 |
| Decisions per game | 944 | 958 | 927 | 956 | 930 | 927 |
| Coordinator busy | 89% | 85% | 89% | 83% | 86% | 88% |
| Requests per round | 8.15 | 5.98 | 8.66 | 5.81 | 6.40 | 8.54 |
| Coordinator time per evaluation | 303 µs | 248 µs | 290 µs | 274 µs | 233 µs | 267 µs |
| Coordinator CPU per decision | 15.4 ms | 12.8 ms | 15.0 ms | 13.7 ms | 12.1 ms | 14.2 ms |
| Game-process CPU per decision | 131.6 ms | 131.1 ms | 129.8 ms | 130.0 ms | 123.8 ms | 125.5 ms |
| Cores in use, game processes and coordinator | 8.62 | 9.72 | 8.86 | 8.69 | 9.99 | 9.20 |
| Peak memory, sampled every 5 s | 5.72 GB | 5.79 GB | 6.03 GB | 6.26 GB | 6.20 GB | 5.62 GB |
| Failed games | 0 | 0 | 0 | 0 | 0 | 0 |

Averaged over the three batches before and the two comparable ones after,
decisions per hour while playing rose by 13.3%, from about 222,500 to 252,200.
Every after batch beat the before batches run next to it, by 10% to 15%. But the
before batches themselves spread by 13%, faster as the session went on and as
the other work eased, against 5.5% between runs of the same code on 12 November.

The coordinator's CPU per decision fell by 16%, from 14.9 ms to 12.5 ms, less
than the 32% a replayed round lost: a faster coordinator finds fewer requests
waiting, 6.2 instead of 8.5 per round, and a smaller round costs more per
request. The coordinator was still busy 85% of the time instead of 89%. The game
processes did the same work per decision as before, about 128 ms, and used more
cores: the training as a whole used 9.9 cores instead of 8.9. An after batch run
just before the alternation, under 2.3 cores of other work, played 257,826
decisions per hour; it is in the evidence file but not in the averages.

## Other ways considered

- **A second coordinator**, serving half the game processes. Not built. It adds
  capacity without making a round cheaper: each coordinator would find about
  half as many requests waiting, and smaller passes cost more per position, so
  the coordinators would use more CPU where little is spare. One pass per round
  makes the one coordinator cheaper instead.
- **TorchScript**, to run the pass without Python's interpreter. It still works
  in PyTorch 2.14 but warns that it is deprecated.
- **One matrix product for the three networks' rows** (`torch._grouped_mm`). It
  runs on the CPU in PyTorch 2.11 and 2.14 and gave the same products, but it is
  a private function. Separate products on each network's rows are slower by a
  few operations per layer only.
- **The GELU curve** takes about 30% of a pass's operators. A cheaper curve would
  change the network, an algorithm change that needs a learning comparison.
- **Laying the positions out** takes 233 µs of a 1,603 µs round in Python and
  numpy. Doing it in the engine's C++ would save most of that; not tried here.

## What this does and does not show

- **Measured:** where the coordinator's time went in one batch, with its native
  samples; the replies and gradients before and after on saved real rounds and
  their positions; the time per replayed round; six training batches, of which
  three before and two after had comparable loads.
- **Inferred:** answering a round in one pass made the coordinator about a
  third cheaper per round, and the training turned that into more decisions per
  hour by using more of its cores. The training now runs close to both limits:
  the coordinator is busy 85% of the time, and the game processes and the
  coordinator use 9.9 of the 11 cores, on a Mac whose other work took 2 to 3
  more. The game processes do 90% of the CPU work, so less engine work per move
  would free the most CPU, and the coordinator would have to keep up with it.
- **Open:** the size of the gain on a quiet machine. The direction held in every
  comparison, but the day's before batches spread as widely as the gain, so 13%
  is less certain than that it is positive. The coordinator's next candidates
  are laying the positions out, a seventh of its time per round, which C++ could
  do in a fraction of that, and the requests' and replies' format; neither was
  tried.
