# Numerical campaign inputs and reuse — 25 October 2026

Four matched three-round games plus a real learning update took **322.34s**, versus **542.17s**: **1.68× throughput**, or **40.5% less training wall time**. All search results, actions, final boards/history/RNG, targets, model weights, Adam state and replay features match. This is a performance and recovery check, not evidence of stronger play. The [evidence JSON](numeric_training_input_2026_10_25.json) contains timings, exact fingerprints, limits and artifact provenance.

## What changed

Training now compiles complete, immutable C++ public observation, context and action snapshots into contiguous numeric graph buffers. The engine keeps its authoritative typed state and a derived native `json::Value` snapshot. Neural input preparation bypasses JSON text and Python dictionaries/tuples containing the full state and graph scalars; public inspection and progress reporting retain their JSON interfaces. Every source field and legal choice remains, and every existing model-input node, token, numerical feature bit, edge, reference and action factor is preserved, including canonical numeric-zero handling. Unicode and numeric strings retain their prior meanings. Public JSON inspection remains available.

Fixed registries and complete action graphs are reused across game roots using bounded caches. Action keys include the full authoritative payload and wrapper identity; overlays and foreign payloads cannot borrow a stale cached graph. Numeric source caches contain no learned outputs. Frozen-policy context vectors require the matching model version and are bypassed during gradient computation.

The frozen map now has immutable indexed reachability data. State validation walks all five free-form JSON payload paths in place; structural checks remain. The engine reuses the final state key it has just computed, detaches on mutation and never trusts a key loaded from history. Authoritative external/stale action checks remain in force.

## Matched measurements

Both versions use four roots, 16 simulations/depth 16, hidden size 16, one message layer, 2,048 token buckets, four tensor threads and the same seeds/settings. The training batch uses 32 examples per sampled update, 16 Adam calls per actor, learning rate 0.001 and replay capacity 16,384. Actual training game seeds are recorded in the JSON; they come from the learner's environment RNG and are distinct from the fixed-position roots.

| Fixed-position Japan combat movement | Before | After | Ratio |
| --- | ---: | ---: | ---: |
| Opening | 7.275s | 5.260s | 1.38× |
| Later | 7.003s | 5.357s | 1.31× |

These fixed-position timings cover three search waves over four unchanged opening or later positions. Startup, scripted preparation and separate instrumented runs are excluded.

| Four complete games and one update | Before | After |
| --- | ---: | ---: |
| Collection and search | 505.205s | 289.755s |
| Finish batch and learning update | 14.620s | 10.666s |
| Full recovery saves | 5.552s | 4.035s |
| Small model exports | 0.026s | 0.026s |
| Progress reporting | 14.650s | 15.756s |
| Complete training wall | 542.173s | 322.343s |
| Checkpoint load, separate | 4.895s | 1.699s |
| Validated reconstruction, separate | 6.743s | 2.100s |
| Saved replay comparison, separate | 0.677s | 0.156s |

Training wall includes environment/model/learner construction, normal saves, exports, reporting and search fingerprints. Python imports/provenance work occur earlier. Full replay normalization and checkpoint load/restore checks occur afterward; guarded supervisor elapsed time includes them all. Final runner timing buckets exclude their own last report write and final progress output, which training wall includes.

Each run completed **4 genuine three-round terminals**, **1094 decision examples**, **159 chance resolutions** and **zero bootstrapped targets**. The learner generation/update counter advanced **once** for that completed self-play batch. That learning batch made **16 actual Adam calls per agent, 48 total**; the counter does not count individual Adam calls. Both saved checkpoints restore the exact state, optimizer/RNG and every replay input. Physical pickle formats differ, so whole-file hashes are provenance; complete normalized input graphs supply cross-format parity.

Sampled aggregate peak memory increased from **3.234 GB** to **5.805 GB**, below 30 GB. Full recovery files grew from **122.9 MB** to **935.9 MB**: the numerical graphs trade memory and storage for compute. Larger replay populations need memory measurement before a longer run. Runs were sequential within the 12-core allowance. This sample includes post-run verification/restore and uses a safety margin; it is not a kernel memory cap.

## Component results and earlier attempt

Isolated full state validation improved **8.8–13.0×** over 100 repetitions at each of three exact snapshots. Their serialized hashes and planning keys match. Indexed aircraft-menu checks improved only about **1.02–1.08×** on those snapshots. These component figures are separate from the measured complete-training ratio above.

The first candidate (`1f17393`) preserved parity but was not faster: opening search 7.135→7.438s; later 6.911→6.956s. Repeated action compilation across roots remained, motivating the source caches and measured native follow-up. Its interrupted baseline checkpoint is preserved separately at 47 decisions, 5 chance events, **0 completed games and 0 updates**; it was never adopted into the final pair.

## Verification and provenance

All **413 Python tests** and **26 CTest suites** passed. Tests cover full graph/policy/value/gradient parity, complete menus and pending choices, cache invalidation/ownership, concurrent access, rejected corrupted replay, exact save/restore and native numeric edge cases.

Baseline commit: `332866c4fe6bdcb8fe8281a979e096776457ced7`. Final implementation: `45682e1f4d3923494558b4e1343a5988196a7723`. Final native SHA-256: `6660551b3d125a6a2361194e48993808ff5b59dfa6aba20e9700b61203986bd2`. Every file in both frozen runtime manifests was verified. Canonical evidence payload SHA-256: `74ab2ebe0e9ab626cd1187185569ad72982c93b77f37a72d493698a2f7ec534a`.

This is one matched timed pair per workload, without variance estimates. It does not establish playing strength, eleven-round feasibility or an optimal learning algorithm. Raw artifacts remain ignored under `studies/campaign/runs/numeric-input-reuse-2026-10-25/`.
