# Exact resident surrender effects

`ResidentSurrender.surrender` and `queue_bonus` now reproduce the complete native
internal helpers on Apple GPU state. They preserve map-order controller handoffs,
optional alliance/player/treasury fields, the closed-campaign Dadao fallback,
cargo removal, queued ship ownership and the complete variable-count D12 request.
Objective awards create five completed construction projects. Counter increments,
pending/request order and construction-ID collisions follow the native helper.

This completes the internal effects, not the Engine's surrender action, the
queued naval-dice resolver or full political refresh. Income, clock, audit Events,
actual random draws and subsequent choices remain their separate native hooks.

Ten distinct cases passed direct raw native-oracle comparisons, including 131
queued D12s, numeric sentinels, controller ordering, unresolved optionals, bonus
collisions/negative counters, preexisting chance, selected-lane laziness, exact
allocation retries, full cohort rollback and no host/native/JSON hot-path calls.
Every State/history/RNG word is retained. The final full run passed nine cases;
its allocation fixture freed enough units that growth still fit, so that fixture
was corrected and its single case passed separately (3.539 seconds). No resident
rule implementation changed during those fixture repairs. Peak guarded charge
stayed below 3.80 GB including the full 3 GB MPS reservation; two CPU threads were
used. All 27 native suites passed after the shared wrapper/prefix additions.

The [political unit effect report](resident_political_unit_effects_2026_10_26.md)
documents the raw oracle and wire-fingerprint boundary. These are correctness
results; no surrender throughput or learning-strength claim has been measured.
