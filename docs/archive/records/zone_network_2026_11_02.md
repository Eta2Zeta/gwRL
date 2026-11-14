# The network reads the zone encoding — 2 November 2026

The [zone encoding](zone_encoding_2026_11_02.md) is now the network's only
input. The JSON graph it replaces is gone: its two C++ compilers, the word-piece
hashing, the graph caches, the compressed graph storage, and the tests and
benchmark that only checked them. The [evidence file](zone_network_2026_11_02.json)
holds the exact values. Nothing here was trained: these are checks that the
input reaches the network intact, and measurements of size and speed.

## The network

Each alliance has its own network. With hidden size 64 and two message layers:

1. **One vector per zone.** Every stored answer adds its column's own learned
   vector, weighted by sign(answer) × log(1 + |answer|). The zone's vector also
   gets a learned vector for the zone itself and a projection of its fixed map
   facts.
2. **One vector for the position**, built the same way from the position's own
   answers.
3. **Messages along the borders.** Twice, every zone sends a message along each
   of the 160 directed borders. The message depends on the sender's vector and
   on the border's fixed facts, such as a river or a railway. Each zone averages
   what it receives and updates its vector from that and the position vector.
   The position vector then updates from the mean zone vector.
4. **Value.** The position vector, the zones' mean and their maximum give the
   three alliance values.
5. **Options.** Each legal option gets a vector from its own answers and from
   the zone vectors of the zones it acts from, travels through (averaged) and
   acts on. The policy scores every listed option: none is padded, merged or
   dropped.
6. **Policy groups.** As before, the menu is normalized in steps: the option's
   kind, then what acts, how it travels, what it acts on, and finally the exact
   option. The encoder now numbers these groups with integers, so no text
   reaches the network at all.

The layout's map facts and borders belong to the layout version
(`campaign-zone-v1-11dda95a8ed9de22`), not to the weights. The network refuses
inputs of another layout, and the run's compatibility record now names the
layout, so a checkpoint of another layout cannot be resumed.

## What the pipeline does with it

- **Search.** The adapter encodes each decision once. Search copies of the same
  position share that encoding, and a subset of the menu is a selection from it.
- **Replay.** A stored sample keeps the decision's encoding, about 11 KB,
  instead of the old 750 KB graph. Restoring a checkpoint checks every row:
  - it is a zone input of the run's layout;
  - it lists as many options as its search policy;
  - it names the row's owner as the deciding player.
- **Training.** Each alliance's network reads its own rows in full and the
  other alliances' rows without their options, since values do not read them.
- **Shared GPU evaluation.** A game thread writes the decision's 13 integer
  arrays into its shared memory. The server lays out all waiting positions and
  runs the same forward pass as the in-process evaluator. Context graphs,
  external references and their transfer code are gone.
- **Removed:** `CampaignNumericGraph`, `compile_campaign_graph`,
  `numeric_storage.py`, the `token_buckets` setting, model inference caches and
  the old GPU layout code. The adapter's JSON snapshots, which replays still
  use, are renamed `frozen_observation`, `frozen_context` and
  `frozen_features`.

## Size and speed on the same positions

Both networks have hidden size 64 and two message layers; the graph input
used 16,384 token buckets, as in the production-like benchmark. Both read the
same 316 positions: every twelfth decision of two scripted 11-round games
(seeds 3101 and 3102), identical by their planning keys. They have 13 options
at the median, and 321 at most. Every pass reads fresh inputs from new copies
of the positions, after a warm-up. Training steps run as
`CampaignLearner.update` runs them: 32 rows, each network reading its own rows
in full and the others' without options, then the backward pass and one Adam
step. One measurement ran at a time on the 4-vCPU container.

| Median, 316 positions | Graph input | Zone input | Times faster |
| --- | ---: | ---: | ---: |
| Forward pass, one position at a time, one thread | 17.9 ms | 2.43 ms | 7.4 |
| Forward pass per position, batches of 16, one thread | 36.5 ms | 0.62 ms | 58.7 |
| Training step per network, 32 rows, one thread | 3.25 s | 75.4 ms | 43.1 |
| Forward pass, one position at a time, four threads | 13.0 ms | 2.56 ms | 5.1 |
| Forward pass per position, batches of 16, four threads | 19.5 ms | 0.42 ms | 46.0 |
| Training step per network, 32 rows, four threads | 1.58 s | 40.7 ms | 38.8 |
| Building a decision's input, first time | 2.76 ms | 0.40 ms | 7.0 |

| Stored per decision | Graph input | Zone input |
| --- | ---: | ---: |
| Median | 748 KB | 11.4 KB |
| Mean | 919 KB | 14.1 KB |
| Largest | 3,490 KB | 55.4 KB |

A replay of 4,096 such decisions takes about 58 MB instead of about 3.8 GB.

For one position, more threads do not help the new network. Its pass is over
100 small operations (23 linear layers, 27 gathers and 15 scatter-adds among
them), and their per-call overhead dominates: about 0.3 ms laying the arrays
out and 2 ms in PyTorch. Batching is where it gains: 16
positions together cost 0.62 ms each. The old network was slower per position
in batches than alone.

## Costs and open questions

- **Parameters.** One vector per column makes the column tables 97% of the
  network:

  | Network | Parameters | Saved size |
  | --- | ---: | ---: |
  | New, hidden 64, two layers | 5.20 M | 20.8 MB |
  | Old, hidden 64, two layers, 16,384 buckets | 1.14 M | 4.6 MB |
  | New, hidden 16, one layer | 1.27 M | 5.1 MB |
  | Old, hidden 16, one layer, 2,048 buckets | 0.04 M | 0.15 MB |

  Rows that no stored answer uses take no part in forward passes, and Adam
  leaves a row that never received a gradient unchanged. A training step still
  clears and steps every row; the measured training step includes that. The
  rows also fill saved files. A run saves its three
  networks after every update, so each generation's file grows from 13.7 MB to
  62 MB at hidden size 64, and from 0.46 MB to 15 MB at hidden size 16.
- **Most columns never occur.** Four complete 11-round games (7,008 positions,
  two random and two scripted) used 1,312 of 59,322 zone columns (2.2%), 508
  of 6,763 position columns (7.5%) and 1,149 of 13,031 option columns (8.8%).
  The layout is the full product of its name lists, such as every cargo type on
  every unit type. Restricting each family to the combinations the rules allow
  would shrink the tables many times over. It needs a new layout version and a
  new completeness check, so it is left for a separate change.
- **Learning is unmeasured.** Nothing here shows that the new network learns
  faster or better. That needs matched training runs on the user's hardware.
- **GPU paths are untested here.** This machine has no CUDA or MPS device. The
  network uses gathers, scatter-adds, one scatter-maximum, layer norms, GELU
  and linear layers, all of which the old network also used on MPS.
- **Old checkpoints and exports cannot be loaded.** Their networks read the
  graph input. This is intended: runs so far are experiments.

## Checks

The network's own tests check, on real decisions from complete games:

- every listed option gets one finite logit, and a menu's probabilities sum to
  one;
- a position's outputs do not depend on the other positions in its batch;
- reordering the options reorders their logits, and the values do not read the
  options at all;
- changing one stored answer changes the outputs;
- training reaches every parameter;
- the network runs in double precision;
- inputs of another layout, or with an index outside the layout, are refused;
- pickled inputs give the same outputs.

The pipeline's tests then cover:

- the evaluator's routing to the three networks, value scaling and chance
  averaging;
- that search copies evaluate exactly as the original;
- exact checkpoint resume with zone replay;
- the refusal of replay rows with another layout, menu or owner;
- that a decision's arrays arrive unchanged through shared memory, for random
  play and for positions inside searches;
- that merged server batches match single positions;
- real self-play that reproduces its trace and final state.

`tools/check_zone_encoding.py` was rerun after the policy-group change: 626
positions, no look-alike positions or options, no unknown names.

| Suite | Tests | Result |
| --- | ---: | --- |
| C++ (`ctest`) | 28 | 27 pass. `campaign_env` passes but takes 33 to 35 s against its 30 s limit, as it does on `d411d24` on this container. |
| Python, every process told there are 12 cores | 574 | 572 pass, 7 skipped (GPU only) |
| Python, the container's real 4 cores | 574 | 538 pass, 7 skipped |

The two failures of the 12-core run:

- One episode-run test still read the removed JSON observation. It now tags
  each toy episode in its zone input, and its module passes, 11 of 11.
- `test_campaign_deadline_guardian` expects macOS's physical-footprint memory
  measure. It fails the same way on `d411d24`.

The 4-core run has those two, plus 34 tests that stop at a configuration check
needing more cores than the container has:

- 12 scaling-benchmark tests;
- 10 device-benchmark tests;
- 5 device-update tests;
- 4 shared-evaluator tests;
- 2 forced-move tests;
- 1 episode-worker test.

The forced-move and episode-worker ones fail the same way on `d411d24`.

## Reproduce

```sh
./.venv/bin/python setup.py build_ext --inplace
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build && ctest --test-dir build --output-on-failure
```

The matched measurements use `tools/benchmark_campaign_network.py`, which
measures whichever checkout it is given. For the graph input, use a checkout of
`d411d24` with its own extension built:

```sh
git worktree add ../gwrl-graph-input d411d24
(cd ../gwrl-graph-input && ../gwRL/.venv/bin/python setup.py build_ext --inplace)
./.venv/bin/python tools/benchmark_campaign_network.py ../gwrl-graph-input graph.json --threads 1
./.venv/bin/python tools/benchmark_campaign_network.py . zone.json --threads 1
```
