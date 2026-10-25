# Three-round experiment results — 25 October 2026

The run completed, but **Japan did not learn the requested territorial
expansion**. Across eight held-out seeds, neither the network alone nor
16-simulation search acquired any Chinese Home Country possession before or
after training. Search with the trained network preserved more units and wealth
than search with the initial network; the network alone showed no clear
playing-strength improvement.

The [verified result data](three_round_2026_10_25_results.json) includes individual
seed results, paired statistics, settings, timing scopes and checkpoint hashes.
The [experiment specification](three_round_2026_10_24.md) records both preflight
corrections and the explicit fresh start before any learning update.

## What ran

- 60 completed three-round self-play games across 15 collection/update batches.
- 16,175 terminal-labeled decision records: Axis 8,422; Allies 3,394; Comintern
  4,359. No unfinished-game predictions were used as terminal labels.
- 240 sampled Adam steps per agent, at 32 records per step. Collected records
  are not gradient steps, and every record was not necessarily sampled.
- Four search roots, four tensor threads and coordinator allowance within
  twelve CPU cores. Peak sampled aggregate resident memory was **17.11 GB**,
  below the authorized 30 GB; monitoring is not a kernel memory allocation cap.
- Search remained at 16 simulations/depth 16. Architecture, reward, scenario
  and three-round horizon remained fixed throughout the valid run.

Training's measured interval was **7h 17m 45s**. The full experiment completed
at **6:33:03 a.m. Chicago time**, before the original 7:27:28 a.m. deadline.
The training stop was scheduled, with a complete checkpoint saved; there was
no engine failure, forced kill or worker retry during this valid training run.

## Before/after evaluation

Each cell is the mean over the same eight held-out seeds against unchanged
balanced scripted opponents. All 32 initial/final evaluation games reached
their genuine three-round ending; none was truncated or assigned a fake score.

| Metric per game | Network alone: initial → trained | With search: initial → trained |
| --- | ---: | ---: |
| New Chinese possessions acquired | 0 → 0 | 0 → 0 |
| Newly held Chinese land at ending | 0 → 0 | 0 → 0 |
| Newly held Chinese IPP | 0 → 0 | 0 → 0 |
| Initially Japanese Chinese land lost | 0.125 → 0.125 | 0.125 → 0 |
| Japanese units removed | 0.50 → 0.75 | 2.75 → 0.625 |
| Axis terminal wealth score | 70.000 → 69.925 | 67.750 → 70.375 |
| Axis terminal wealth-gap return | 46.900 → 45.3125 | 33.350 → 43.225 |

There were **zero gross possession acquisitions**, so these results do not
hide temporary captures that were subsequently lost. The search result is a
limited improvement in force/wealth preservation, not offensive expansion.
Its trained wealth score of 70.375 is also close to the initial network-alone
score of 70.000; the experiment does not establish a compute-efficient benefit
from adding search.

Unit removals include combat, surrender and other forced removal. Territory
uses the authoritative KMT Chinese Home Country, including its defined land
outside mainland China; Dadao possessions are separate. Equal seeds do not
guarantee equal later dice events after policies choose different actions.
One initialization and eight seeds per mode do not establish general playing
strength, an optimal learning method or eleven-round competence.

## Measured performance problem

| Training interval | Time | Share |
| --- | ---: | ---: |
| Checkpoint construction and saving | 4h 24m 06s | 60.33% |
| Collection and search | 2h 46m 36s | 38.06% |
| Learning updates | 3m 08s | 0.72% |
| Progress reporting | 3m 55s | 0.89% |

Checkpointing is the largest measured operational bottleneck. Its bucket
includes copying, serialization, writing and flushing, so this measurement
does not identify the SSD as the cause. Checkpoints reached **1.865 GB** and
were saved every sixteen waves, at batch ends and at the safe stop. Overall throughput was **8.22 completed
games/hour**, including updates and checkpointing; collection itself measured
1.913 transitions/second. These scopes cannot be substituted for each other or
treated as a measured checkpoint-free speedup.

Before another long run, profile and reduce checkpoint cost while preserving
exact continuation and backup safety. Then inspect Japan's choices on
profitable attack positions to distinguish learning, exploration, search and
objective limitations before choosing further training changes.

## Saved continuation and verification

Four unfinished games remain saved in the second round, with 665 pending,
unlabeled decision records. Models, Adam state, replay, frozen batch policies,
unfinished positions and random states remain in the checkpoint. The completed
pipeline will not replenish its budget; future training continuation requires
a newly authorized allocation. The final evaluator successfully restored the
full checkpoint before evaluating the saved generation-15 weights.

The latest, previous and immutable evaluation checkpoints match SHA-256
`3fa2022a1e894c9a44937399584600d87d9c308553be561492a951e44eaf5ebd`.
The frozen runtime is commit `88981035ec1d80ff73f5b1d4e3b4c5ec3fd2580d`.
Independent audits matched all 418 frozen files, production source/native
hashes, evaluation contracts, held-out seed separation and paired aggregate
statistics. Final audits used JSON/logs and streaming hashes; individual replay
rows and optimizer tensors were not independently deserialized again.

The last code validation passed all 346 Python tests and 26 CTest suites.
This result publication changes documentation only; its verification checks
counts, contracts, hashes and recomputed statistics rather than repeating code
tests. Raw artifacts remain ignored under
`studies/campaign/runs/three-round-10h-2026-10-24-r3/`.
