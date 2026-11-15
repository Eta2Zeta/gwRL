# What a larger network and a longer search cost — 14 November 2026

Training had used a 64×2 network and 64 simulations per decision. These
measurements give the cost of larger ones on the Mac (Apple M4 Max, 14 cores,
32-core GPU), part by part: the network's passes on the CPU and on the GPU, the
game process's CPU for each simulation, and the memory a search tree holds.
On the GPU, passes of the larger networks run 7 to 15 times as fast as on one
core, but only with many positions per pass; a simulation costs about 1.25 ms
of a core alone and about twice that under a training batch's load, whatever
the network; and a tree holds about 0.17 to 0.25 MB per simulation. Worked out
from these, not measured in training runs: up to about 256×8 with 256
simulations the cores limit self-play on the Mac, and beyond it the GPU; with the
search held fixed, the cores limit up to 256×8 whatever the budget. The
[design document](../../design/README.md#93-what-a-larger-network-and-a-longer-search-cost)
describes the costs; the [evidence file](network_and_search_cost_2026_11_14.json)
holds every value.

## The network

**Setup.** `tools/benchmark_network_sizes.py`, new with this record, took every
sixth decision of two scripted eleven-round games, seeds 3101 and 3102: 624
positions, with a median of 14 legal moves and a 90th percentile of 118. For each
size it built the three alliance networks with their column tables filled with
small random numbers, stacked them as the coordinator does (`NetworkStack`), and
timed the coordinator's own code, `forward_prepared` and `collect`: laying the
positions out, one pass, and the outputs' copy to the host with the softmax
there. A pass's positions are a random sample, grouped by the alliance that
decides. Each cell is the median pass over 2 seconds or 400 passes, after two
passes of warm-up. Commit `c4e9260`, PyTorch 2.14 (`tmp/gpu-mps-env`),
`MallocNanoZone` unset, one run per device, one after another. The Mac's load
average was 4 to 8 during the runs, the benchmark included, so absolute numbers
may be a little low; the ratios between cells are the point.

Arithmetic per position counts two operations per multiply-add of the learned
layers: four products per zone in each message layer (the message and the zone
update), the position, summary and value layers, and six products per move and
two per policy group, for a 14-move menu with 14 groups. Lookups, index
operations and element-wise curves are left out.

| Network | Parameters | Of them in the three tables | Arithmetic per position |
| --- | ---: | ---: | ---: |
| 64×2 | 4,081,096 | 3,947,712 | 3.4 million operations |
| 128×4 | 8,612,232 | 7,895,424 | 23 million |
| 256×8 | 20,204,296 | 15,790,848 | 173 million |
| 384×12 | 37,135,496 | 23,686,272 | 565 million |
| 512×16 | 61,765,128 | 31,581,696 | 1,319 million |

Positions per second, by positions per pass:

| Network | Device | 1 | 4 | 16 | 64 | 256 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 64×2 | one CPU core | 2,198 | 4,154 | 5,850 | 6,243 | 6,082 |
| 64×2 | four CPU threads | 932 | 1,830 | 3,533 | 6,285 | 8,661 |
| 64×2 | GPU | 485 | 1,085 | 3,422 | 9,835 | 20,916 |
| 128×4 | one CPU core | 1,246 | 2,015 | 2,213 | 2,183 | 2,109 |
| 128×4 | four CPU threads | 507 | 1,098 | 1,609 | 2,869 | 3,754 |
| 128×4 | GPU | 392 | 1,007 | 2,896 | 7,974 | 13,500 |
| 256×8 | one CPU core | 360 | 505 | 577 | 600 | 658 |
| 256×8 | four CPU threads | 179 | 315 | 550 | 880 | 1,116 |
| 256×8 | GPU | 217 | 637 | 1,940 | 4,503 | 6,552 |
| 384×12 | one CPU core | 184 | 237 | 267 | 319 | 316 |
| 384×12 | four CPU threads | 93 | 145 | 265 | 444 | 534 |
| 384×12 | GPU | 212 | 487 | 1,265 | 2,616 | 3,353 |
| 512×16 | one CPU core | 87 | 117 | 125 | 175 | 166 |
| 512×16 | four CPU threads | 79 | 107 | 178 | 289 | 323 |
| 512×16 | GPU | 178 | 405 | 920 | 1,641 | 1,903 |

A pass of one position takes the GPU 2.1 ms for 64×2 and 5.6 ms for 512×16, one
core 0.46 ms and 11.5 ms. One core's time per pass of 16 positions, 2.7 ms for
64×2, matches the coordinator profile's 0.42 ms plus 0.15 ms per position
([record](coordinator_one_pass_2026_11_14.md#where-the-coordinators-time-went)).
At 512×16 and 256 positions per pass the GPU does about 2.5 trillion operations
a second, one core about 0.2 trillion.

Training steps of one network on 128 decisions (forward, backward and Adam, with
the squared outputs as a stand-in loss), decisions per second:

| Network | One CPU core | Four CPU threads | GPU |
| --- | ---: | ---: | ---: |
| 64×2 | 2,259 | 3,139 | 2,429 |
| 128×4 | 884 | 1,606 | 1,820 |
| 256×8 | 296 | 558 | 1,338 |
| 384×12 | 144 | 262 | 865 |
| 512×16 | 79 | 142 | 586 |

## The search

**Setup.** `tools/benchmark_search_budgets.py`, new with this record, searched
every 40th decision of the same two games that had more than one legal move, 77
positions, with the training's search: depth 16, root noise, no tree reuse. Its
evaluator builds each evaluated position's zone input, as a game thread does
before asking the coordinator, and returns equal priors and zero values, so the
CPU time is the engine's, the search's and the encoder's. One process per
budget. Memory is the growth of the process's resident size while the first 8
trees are alive, divided by their nodes, measured before the process frees any
tree.

| Simulations | CPU per search, mean | Per simulation | Evaluations per search | Nodes per tree | Memory per node | Memory per tree |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 64 | 79 ms | 1.23 ms | 65 | 69 | 162 KB | 11 MB |
| 256 | 323 ms | 1.26 ms | 256 | 274 | 205 KB | 56 MB |
| 1,024 | 1,324 ms | 1.29 ms | 1,018 | 1,081 | 234 KB | 254 MB |

Of the two games' 3,744 decisions, 629 (17%) had one legal move; training does
not search those. In the 14 November training batches a game process used about
120 ms of CPU per decision at 64 simulations, with about 50 evaluations per
decision: about 2.4 ms per evaluation, twice the cost measured here alone
([record](coordinator_one_pass_2026_11_14.md#matched-training-batches),
[record](supply_cache_2026_11_14.md#training-batches)). There every core is busy,
each process runs four games and sends its requests through the coordinator;
the gap has not been broken down.

## Which part limits, worked out

Each evaluation needs engine work on the cores and a share of a network pass, so

$$\text{decisions per hour} = 3600 \times \min\left(\frac{\text{cores for games}}{\text{core seconds per decision}}, \frac{\text{positions the network evaluates per second}}{\text{evaluations per decision}}\right)$$

with these assumptions: core seconds per decision 0.120 at 64 simulations,
scaled by the CPU per search above (interpolated in the number of simulations);
evaluations per decision 50 at 64 simulations, scaled the same way; 10 cores for
games and one for the coordinator; the network on one core at 16 positions per
pass or on the GPU at 64, whichever is faster; 64 positions per pass need 128
games in flight, and 30 GB less 8 GB for the processes, trainer and buffers must
hold their trees (at 800 simulations only 115 fit, so 57 per pass).

| Network and search | Evaluations per decision | Core seconds per decision | Tree | Engine limit, decisions per hour | GPU limit | Decisions per hour | Core hours per 100 million decisions | GPU hours, 256 per pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 64×2, 64 | 50 | 0.120 | 11 MB | 300,000 | 708,000 | 300,000 | 3,333 | 66 |
| 128×4, 128 | 99 | 0.244 | 24 MB | 148,000 | 290,000 | 148,000 | 6,778 | 204 |
| 256×8, 256 | 197 | 0.492 | 56 MB | 73,000 | 82,000 | 73,000 | 13,668 | 836 |
| 384×12, 400 | 307 | 0.778 | 89 MB | 46,000 | 31,000 | 31,000 | 21,616 | 2,543 |
| 512×16, 800 | 612 | 1.573 | 191 MB | 23,000 | 9,200 | 9,200 | 43,693 | 8,934 |

For today's setup the formula gives 300,000 decisions per hour; the batches
measured about 252,000. The coordinator's own work besides passes, about 30% of
its time, and the waits between rounds are not in it.

With the search held fixed, the same assumptions give these decisions per hour
for every network. The cores' limit depends only on the search: about
4,167, 4,008 and 3,890 evaluations a second at 64, 256 and 800
simulations. The network's depends on its size and its device, and at 800
simulations on the 57 positions per pass that memory allows. At 256×8 the
network's limit is 8% to 12% above the cores'. Every value, both limits
included, is under `worked_out.by_network_and_search` in the evidence file.

| Network | 64 simulations | 256 simulations | 800 simulations | Limited by |
| --- | ---: | ---: | ---: | --- |
| 64×2 | 300,000 | 73,164 | 22,887 | the cores |
| 128×4 | 300,000 | 73,164 | 22,887 | the cores |
| 256×8 | 300,000 | 73,164 | 22,887 | the cores |
| 384×12 | 188,359 | 47,751 | 14,484 | the GPU |
| 512×16 | 118,138 | 29,949 | 9,197 | the GPU |

## What this does and does not show

- **Shows:** the cost of a pass at each size, on one core, four threads and the
  GPU, and that the GPU needs many positions per pass; that a simulation costs
  the game process the same CPU at 64 and at 1,024 simulations; and how much
  memory a tree holds.
- **Does not show:** throughput in training runs at these sizes, which is worked
  out, not measured, and for today's setup comes out about a fifth too high;
  whether a larger network or a longer search learns faster at equal compute;
  how a trained network's priors change a tree's shape and memory, since these
  trees used equal priors; or why the same search work costs twice as much
  under a training batch's load.
- The positions come from scripted games, not from self-play.
