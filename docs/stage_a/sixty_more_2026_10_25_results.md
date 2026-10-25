# Sixty additional three-round games: results

The continuation finished **60 additional games and 15 retained learning updates**, reaching **120 total games / generation 30**. Active training, including recovery overhead, took **1 h 57 min**; the complete pipeline took **2 h 17 min**. Japan acquired **no new Chinese territory** in either held-out evaluation mode. This run establishes completed, resumable training at the measured throughput; it does not demonstrate improved offensive play.

[Curated evidence](sixty_more_2026_10_25_results.json) contains exact counts, timings, paired statistics, recovery details and artifact hashes. [The launch record](sixty_more_2026_10_25.md) describes the fixed experiment.

## Work completed

Generation 15 continued with its networks, Adam state, replay, frozen policies and random state. The first four completions finished saved games; the other **56 games started fresh**. Every game ended after three complete rounds. The three-round horizon, terminal wealth-gap reward, four concurrent games, 16 search simulations, depth cap 16 and model/training settings stayed fixed.

The 15 retained updates performed **240 sampled Adam steps per agent**, with **zero bootstrapped targets**. They labeled **15,182 terminal training rows**: **14,517 retained new decisions plus 665 pending rows carried from the original checkpoint**. Minibatches also draw from retained historical replay; 240 steps are not 240 passes through the dataset.

A memory-triggered rollback discarded 15 completed game executions and four updates. Recomputing that work means the processors actually executed **75 completion events, 19 updates and 304 Adam steps per agent** to retain the additional 60 games and 15 updates. These are not 75 additional unique games.

## Time and memory

| Measurement | Result |
| --- | ---: |
| Supervisor-charged training, including startup, restores and shutdown | 7,027.64 s |
| Retained completions per charged training hour | 30.74 |
| Complete pipeline, including evaluations and downtime | 8,223.71 s |
| Initial / final evaluation loop | 276.95 / 276.98 s |
| Four-game cycle median; observed range | 348.95 s; 305.29–461.69 s |
| Sampled peak charged memory | 26,007,771,096 bytes |

The cycle measurements are **17 physical update-to-update intervals within individual invocations**, excluding their first partial batches. They include saves, updates, reporting and repeated work; they are not 17 unique batches. Preflight verification and bootstrap are excluded from training throughput.

Progress timers sum to **at least 6,819.47 s**. The killed invocation never printed a final timer, and the first invocation's detailed buckets were overwritten. Known checkpoint-save time is therefore only a lower bound, **277.86 s**; exact available buckets are preserved in the JSON. Supervisor-charged time supplies the inclusive training measurement.

The allowance remained **12 CPU cores / 30 GB**, counting process overhead and compressed pages. Two transient monitoring failures caused clean stops. Separately, the guardian requested shutdown at 25 GB and killed an unfinished checkpoint write at its 26 GB threshold. Recovery used the preceding complete checkpoint; the empty temporary write was preserved. Live memory exceeded the synthetic preflight envelope, so memory scaling remains unresolved although the sampled peak stayed below 30 GB. Deadlines and charged compute budgets were retained. The pipeline and guardian finished; no training jobs remain.

## Held-out Japan behavior

Generation 15 and generation 30 each played the same eight held-out seeds against unchanged balanced scripted opponents, separately using network-only selection and 16-simulation search. **All 32 evaluation games reached genuine three-round endings.** Values below are means per game.

| Outcome | Network: G15 → G30 | Search: G15 → G30 |
| --- | ---: | ---: |
| Newly held Japanese Chinese zones / IPP | 0 / 0 → 0 / 0 | 0 / 0 → 0 / 0 |
| Japanese acquisition events, excluding original zones | 0 → 0 | 0 → 0 |
| Initially Japanese zones lost | 0.125 → 0 | 0 → 0 |
| Japanese units removed | 0.750 → 0.625 | 0.625 → 0.875 |
| Axis terminal wealth | 69.925 → 70.325 | 70.375 → 69.9875 |
| Axis wealth-gap return | 45.3125 → 46.3875 | 43.225 → 46.575 |

The territorial result is unchanged, and losses/wealth move in mixed directions. Improved wealth-gap return alone does not show better play. Dadao is separate: its mean newly held Chinese zones/IPP in search fell from **0.125 / 0.125 to zero**; the initial gain was Suiyuan in one seed. Network-only Dadao gains were zero throughout.

Eight seeds and one continued initialization provide limited evidence. Different actions can consume different later dice despite matching seeds. Unit removals include combat, surrender and forced removal. None of these results establishes competence in the full eleven-round campaign.

## Continuation and artifact checks

The original checkpoint remains unchanged: `3fa2022a1e894c9a44937399584600d87d9c308553be561492a951e44eaf5ebd`. Exhaustive continuation proof checked all **16,840 saved inputs**, their ordered menus and active serialized games/RNG. **451 tests** passed before launch. The operational monitoring fix passed **64 control tests** and a live proof; its migration preserved all **83 engine/learner source files**, native code and saved learner/evaluation bytes.

Replayed overlap matched **1,208 emitted records / 4,221 action events** exactly, excluding elapsed time. Existing generation 26–29 exports also matched recomputed weights exactly. These checks do not inspect unlogged search internals. Original training source `cafbd91` and operational monitor source `6d89b2e` are recorded separately in the evidence.

A final read-only restore validated all **16,384 replay rows as terminal**, no pending examples or frozen rollout, four saved terminal games and exact generation-30 export weights. It preserved learner bits, executed no actions/dice and rewrote no checkpoint. Its separate 24 GB guard measured **17.962 GB** peak. The final runtime manifest also verified.

The final **510,513-byte generation-30 policy** has SHA-256 `e1d6b6508ab304fa0e6fbb209861ba53a512d48f0d7f6fdd18ed348c4cf638d6`; the final **1,436,717,127-byte recovery checkpoint** has SHA-256 `37e71823f499b8fee11eb0fa3f062b6fc4290f358ed11408936cfe73be65b312`. Raw artifacts remain ignored under `studies/campaign/runs/three-round-60more-2026-10-25/`.
