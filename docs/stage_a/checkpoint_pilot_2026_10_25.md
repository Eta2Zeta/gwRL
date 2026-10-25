# Checkpoint saving pilot — 25 October 2026

The two saving changes completed ten three-round self-play games in **30m 50.98s** of conservatively charged supervisor time. The exactly matched first eight games and two updates took **24m 58.95s**, versus 28m 00.12s previously: **1.12× throughput**, or 10.8% less elapsed time.

The [measurement data](checkpoint_pilot_2026_10_25.json) records timings, hashes, settings and
comparison checks. This is a performance and continuation check, **not a test of
playing-strength improvement**.

## Implemented changes

1. Export the three live networks after each completed learning batch, including
   their configuration, rule/task compatibility, version hashes and seed metadata.
   Evaluation loads these small exports without constructing Adam, restoring old
   examples or rebuilding unfinished games.
2. Save full recovery state every **1,800 seconds**, checked between completed
   collection waves, and at orderly shutdown. Normal learning updates no longer
   force full saves. The latest and previous valid recovery files remain available.

The implementation still writes full recovery files synchronously. Background
writing and incremental replay storage were **not implemented** in this change.
The original `initial.pt` compatibility archive is retained, alongside the initial
generation-zero model export and the initialized recovery checkpoint. An actual
crash can lose work since the latest successful recovery save; a model export
alone cannot resume Adam, replay or unfinished games.

## Workload and result

- **10** genuine three-round terminals, in batches **4 + 4 + 2**, with no unfinished
  games left at the end.
- **2,663** completed decision examples,
  all labeled by observed terminal outcomes; **zero** bootstrapped labels.
- **3,050** actual transitions: **2,663**
  decisions and **387** chance resolutions.
- **3** learning batches; 16 sampled Adam steps per agent per batch, at 32 examples
  per step. Collection records and optimizer steps are different quantities.
- Same seed 1951, scenario, terminal wealth-gap reward, search budget of 16
  simulations/depth 16, hidden size 16, one message layer, 2,048 token buckets,
  learning rate 0.001 and replay capacity 16,384 as the previous run.
- Four game roots and four tensor threads, plus runner/supervisor overhead, within
  the authorized **12 CPU cores**. Sampled aggregate peak resident memory was
  **5.369 GB**
  (5,368,938,496 bytes), below the **30 GB** user
  allowance. The supervisor's sampled stop threshold was **26 GB**, with a 1 GB
  early-stop margin; sampling is not a kernel allocation cap.

## Time and saved artifacts

The runner measured **30m 45.63s**,
or **19.51 completed games/hour**.
The supervisor charged **30m 50.98s**,
or **19.45 games/hour**,
including process startup, shutdown and a conservative polling reservation.
The runner timer starts after environment/model/learner construction and includes
initial saves and exports; it excludes that earlier process/constructor startup.
Its final manifest also excludes its own JSON write and the last progress line.

| Runner work | Time | Share of measured runner interval |
| --- | ---: | ---: |
| Game collection and search | 28m 55.20s | 94.02% |
| Learning updates | 45.491s | 2.46% |
| Full recovery snapshot preparation/saving | 26.968s | 1.46% |
| Small network exports | 0.063s | 0.00% |
| Progress reporting | 37.881s | 2.05% |

There were **4 full recovery/archive
writes** and **4 small network exports**.
The surviving artifacts are:

| Artifact | Logical file size |
| --- | ---: |
| Latest recovery checkpoint | 297.158 MB (297,158,277 bytes) |
| Previous recovery checkpoint | 296.621 MB (296,620,599 bytes) |
| Initial compatibility archive | 546.223 KB (546,223 bytes) |
| 4 model exports, generations 0–3 | 508.465 KB–508.529 KB each; 2.034 MB total |

Retained file sizes do not reconstruct the total bytes written over time, and
hard-linked files may share physical storage. Recovery timing includes snapshot
construction, serialization, writes and flushing; it does not isolate SSD speed.

## Matched comparison and limits

The first eight games match the previous run's complete ordered action/state-hash traces, environment seeds, counters, initial frozen-policy fingerprint and generation-two network weight versions. The speed comparison therefore uses the same actual games and learned weights, rather than different trajectories.
This is one timed before/after comparison, without repeated-run variance estimates.

- `first_eight_action_traces`: passed.
- `first_eight_counters`: passed.
- `first_eight_seeds`: passed.
- `generation_two_model_versions`: passed.
- `initial_frozen_rollout_version`: passed.

Only the **first eight** games support a matched historical comparison. This
pilot's final two games use two roots, whereas the original run's next batch used
four. That changes consumption of shared exploration/search random streams and
can change those tail trajectories. The ten-game elapsed time is a standalone
measurement, not a matched ten-game historical speedup.

This is a **fresh ten-game replay buffer**, with a final recovery file of
297.158 MB. The previous long run reached **1,864,875,191 bytes**
(1.865 GB), and checkpoint work grew with its accumulated data. The pilot does
not establish the cost of a thirty-minute recovery save at that mature size or
predict long-run throughput from the earlier run's overall 60% checkpoint share.
No playing-strength or eleven-round learning conclusion follows from these
results.

## Verification and provenance

The frozen implementation is commit `262aada7093f0410fad569a1262c16cef7018d0b`; its validation passed
**362 Python tests** before this pilot. No game-engine rules, legal choices,
search budget, model architecture or learning objective were reduced for speed.
Timer, export equivalence, compatibility rejection, random-state preservation
and interrupted-tail continuation were covered by the validated tests.

After training exited, the real evaluation helper loaded the generation-three
`campaign-evaluation-models-v1` export and completed one held-out network-only
three-round game (seed 40009), without a recovery checkpoint. This functional
check is outside the ten-game training timing and supplies no strength comparison.
Its contract and result hashes are included in the companion JSON.

The measurement helper independently read JSON progress/manifest records and
streamed artifact hashes without deserializing model or recovery archives.
All artifact hashes, first-eight fingerprints and generation-two versions are
in the companion JSON. The native extension SHA-256 is `05371fd29f42d4a7e4b444309785054b3b71da543430a0eef0854e7fe6dd8689`.
The canonical measurement payload SHA-256 is `91c34c32011e7505029e4462345108f14d8ef793f078c860ab017921b4f30cf1`.
Raw files remain ignored under
`studies/campaign/runs/checkpoint-pilot-10games-2026-10-25/`.
