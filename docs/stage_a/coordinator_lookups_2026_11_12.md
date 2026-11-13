# The fused column lookup, in the code — 12 November 2026

On 4 November one PyTorch operation, `embedding_bag`, was measured as a faster
way to do the network's column lookups
([record](coordinator_lookups_2026_11_04.md)). It is now the network's lookup.
On 540 real positions the network's outputs are identical to the last bit. In
two matched pairs of training batches on the Mac profile, the coordinator's time
per evaluation fell by 18% and the games searched 17.6% more decisions per hour.
The coordinator is still busy 87% to 88% of the time, but the training now uses
9.5 to 10.5 of its 11 cores, so a faster coordinator alone could add at most 4% to
15% more (inferred).
The [design document](../design/README.md#92-running-training-on-the-mac) explains
the coordinator; the [evidence file](coordinator_lookups_2026_11_12.json) holds the
exact values.

## What changed

- **The lookup** (`_bag` in `studies/campaign/neural.py`). A zone's, position's or
  move's vector starts as the sum of the rows of its answers, each multiplied by
  its answer's weight
  ([section 6.3](../design/README.md#63-from-answers-to-a-vector-a-weighted-sum-of-rows)).
  The old lookup copied every answer's row into one temporary array, multiplied
  each row by its weight and added the products into their sums: three
  operations, each over all the answers of a network call. Now
  `torch.nn.functional.embedding_bag`, in sum mode with one weight per answer,
  does all three in one pass without the temporary array.
- **The packing** (`pack_zone_arrays` in `studies/campaign/features.py`).
  `embedding_bag` needs each sum's answers to be consecutive, and where each sum's
  answers start. The packing now gives those starts (`zone_bags`, `global_bags`
  and `action_bags`) instead of each answer's sum number. The engine already lists
  a position's board answers zone by zone; answers in another order are sorted
  first.
- **Precision.** The answer weights are converted to the table's precision. That
  matters only when the network runs in double precision, as one test does; the
  old lookup converted them implicitly.

## The same outputs

**Positions:** from three random-play eleven-round games (seeds 5000, 5001 and
5002, moves drawn with `random.Random(seed)`), every 7th decision with more than
one legal move, 525, and every 50th chance position, 15.

**Networks:** the three networks after one update from the 5 November run, whose
zone tables have 1,840 rows that are not zero, and a fresh 64×2 network whose
three tables were filled with random numbers. A fresh network's rows are all
zero. The 4 November check used fresh networks, so it compared sums of zeros
and showed nothing about the sums; this check does.

- **Outputs.** In 60 batches each of 1, 4, 16 and 64 positions, the logits and
  values of both lookups were identical to the last bit for all four networks, in
  PyTorch 2.14, the training's Python, and in 2.11, the tests' Python. A search
  reads only these outputs, so its results are unchanged too: inferred from the
  outputs, not from rerun searches.
- **Answers out of order.** One position with its board answers shuffled gave the
  same outputs to within $7.5 \times 10^{-8}$, float rounding: the packing sorts
  them.
- **Training.** For five training-like losses on batches of 32 decisions, every
  gradient agreed to within $1.3 \times 10^{-6}$ times that parameter's largest
  gradient, float rounding from adding in another order.
- **On the GPU** (MPS, PyTorch 2.14), the forward pass matched the CPU's to within
  $10^{-6}$, and the backward pass ran.

## The forward pass

Trained Comintern network, one CPU thread, 280 timed batches per size drawn from
the 525 decisions, the best of three repetitions:

| Positions per call | Answers looked up | PyTorch 2.14, old | PyTorch 2.14, fused | PyTorch 2.11, old | PyTorch 2.11, fused |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1,571 | 0.492 ms | 0.443 ms | 0.622 ms | 0.483 ms |
| 4 | 6,311 | 1.009 ms | 0.730 ms | 1.534 ms | 0.972 ms |
| 16 | 24,930 | 3.304 ms | 1.965 ms | 4.812 ms | 2.470 ms |

In the training's PyTorch the pass is 10%, 28% and 41% faster. That is less than
the 4 November estimate, made with PyTorch 2.11, because 2.14's old lookup was
already faster.

## Where a coordinator call's time goes now

One coordinator call with four positions, trained Comintern network, PyTorch
2.14, 400 calls: 1.02 ms in all. Laying the positions out (`pack_zone_arrays`)
took 0.135 ms (13%), the forward pass 0.860 ms (84%) and turning the outputs into
priors and values (`collect`) 0.028 ms (3%). Under PyTorch's profiler a forward
pass made 898 operator calls. The largest shares of their time:

| Operator | Share of operator time | Calls per pass |
| --- | ---: | ---: |
| The GELU curve (`gelu`) | 21% | 14 |
| Learned layers' multiplications (`addmm`) | 15% | 23 |
| The fused lookups (`_embedding_bag`) | 9% | 3 |
| Sums into zones and groups (`scatter_add_`) | 5% | 7 |
| Additions (`add`) | 5% | 20 |
| Copies (`copy_`) | 5% | 43 |
| Layer normalization | 5% | 9 |
| Joining vectors (`cat`) | 5% | 17 |

GELU, the fixed curve of the learned layers, now costs the most, mostly in the
border messages: with four positions, 40,960 numbers go through it in each message
layer, 64 for each of the 160 directed borders of each position. Its cost belongs
to the network's design. On those 40,960 numbers the exact GELU took 36 µs, its
tanh approximation 108 µs and SiLU 31 µs. ReLU took 3 µs, but a different curve
would change the network, not only its speed.

## Matched training batches

Settings as in the
[4 November batches](search_copies_2026_11_04.md#a-matched-training-batch):
`--profile mac` (8 game processes of 4 games, coordinator on the CPU, PyTorch
2.14), 32 eleven-round games, fresh 64×2 networks, 64 simulations, depth 16, seed
20261104, 50 epochs and a sample share of 0.05. The four batches ran one after
another with nothing else running, alternating old and new. The old lookup ran
from a clean copy of commit `5bf6c44`; the fused lookup first from the working
repository, then from a clean copy of the change.

| | Old, run 1 | Fused, run 1 | Old, run 2 | Fused, run 2 |
| --- | ---: | ---: | ---: | ---: |
| Games per hour while playing | 177.6 | 207.6 | 186.6 | 214.9 |
| Decisions per game | 1,056 | 1,062 | 1,061 | 1,082 |
| Decisions per hour while playing | 187,543 | 220,511 | 197,889 | 232,618 |
| Network evaluations per game | 53,675 | 54,086 | 54,160 | 55,081 |
| Coordinator busy | 90% | 87% | 92% | 88% |
| Positions per network call | 3.95 | 3.45 | 4.06 | 3.49 |
| Coordinator time per network call | 1.34 ms | 0.96 ms | 1.33 ms | 0.93 ms |
| Coordinator time per evaluation | 0.340 ms | 0.279 ms | 0.327 ms | 0.267 ms |
| Coordinator CPU per game | 18.4 s | 15.5 s | 18.3 s | 15.3 s |
| Game-process CPU per game | 150 s | 150 s | 155 s | 161 s |
| Cores in use, game processes and coordinator | 8.3 | 9.5 | 9.0 | 10.5 |
| Peak memory, sampled every 5 s | 5.20 GB | 6.10 GB | 7.46 GB | 6.17 GB |
| Median memory after the first minute | 3.62 GB | 3.79 GB | 3.61 GB | 4.00 GB |
| Failed games | 0 | 0 | 0 | 0 |

"Coordinator busy" is the share of the playing time the coordinator spent
answering: reading the requests' inputs, laying them out, the forward passes and
turning outputs into priors and values.

Averaged over the two runs of each, decisions per hour rose by 17.6%, from about
192,700 to 226,600, and games per hour by 16.0%, from 182.1 to 211.3. Runs of the
same code differed by 5.5%. The coordinator's time per network call fell by 29%.
But a faster coordinator finds fewer requests waiting, so its calls carried 3.5
positions instead of 4.0, and its time per evaluation fell by 18%.

**Memory.** The peaks came from the game processes, which do not run the network,
and differed by 2.3 GB between the two runs of the old code. In the first old run
the peak came in the first half minute, while the game processes started; in the
second, all eight game processes held 0.74 GB to 0.93 GB each two minutes into
the games. The coordinator's own process, the one that runs the lookups, stayed
under 0.75 GB in every run. The fused runs' median memory was 0.2 GB to 0.4 GB
higher; why is not measured.

## What this does and does not show

- **Measured:** identical outputs, the gradient agreement, the times and the batch
  figures above.
- **Inferred:** searches are unchanged, since they read only the outputs. The
  training is now close to two limits at once. The coordinator is busy 87% to 88%
  of the time. The game processes and the coordinator together used 9.5 and 10.5
  of the 11 training cores. At the fused runs' CPU per decision, 11 fully busy
  cores would search about 243,000 to 254,000 decisions per hour, 4% to 15% above
  what they did. A second coordinator or a still faster one could therefore add
  at most about that. The larger lever is now the game processes' own work, about
  90% of the CPU: 0.14 to 0.15 CPU-seconds per decision.
- **Open:** where the game processes' time goes since the search began keeping
  copies of its positions; the last profile is from 2 November
  ([record](search_replays_2026_11_04.md#2-november-one-profiled-training-batch)).
