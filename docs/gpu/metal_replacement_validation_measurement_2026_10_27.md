# Parallel replacement validation measurement

Parallel grammar validation reduced the income editor from 4.90 to 0.86 ms at
one lane and 7.03 to 1.14 ms at 64 lanes. Complete recruitment transitions showed
smaller improvements: roughly 5.5%, 7.9% and 3.3% lower sequential median times
at 1, 64 and 512 lanes. The default editor/container policies remain reference.

The [curated evidence](metal_replacement_validation_measurement_2026_10_27.json)
pins all four raw artifacts, both frozen runtimes, complete unchanged native
build proof, source/capacity/output comparisons and resource guards. This
measurement follows the [income subprofile](metal_income_refresh_profile_2026_10_27.md).
It preserves the distinction between unfenced whole-transition timings and
intrusive attribution inside income refresh.

## Complete transitions

Pooled medians over four families and three unfenced repetitions, milliseconds:

| Lanes | Before | Parallel replacement validation | After / before | Candidate native serial | Candidate native ten-worker pool |
|---|---:|---:|---:|---:|---:|
| 1 | 43.200 | 40.805 | 0.945× | 0.856 | 0.949 |
| 64 | 51.555 | 47.496 | 0.921× | 49.105 | 24.860 |
| 512 | 90.099 | 87.099 | 0.967× | 383.727 | 153.669 |

The GPU remains much slower at B1 and slower than the ten-worker control at
B64; it beats that control at B512 in this repeated-source operation. This
establishes no full-game, MCTS or training throughput. Both original CPU controls
and their setup/verification timings remain pinned. Runs were sequential rather
than interleaved, with no confidence interval; small differences include ordinary
timing variation.

## Income attribution

Fenced medians across four families and three captures, before → after:

| Lanes | Full refresh | Extract | Income rates | State writer | Editor |
|---|---:|---:|---:|---:|---:|
| 1 | 9.206 → 5.230 | 0.982 → 0.995 | 0.821 → 0.870 | 1.791 → 1.803 | 4.900 → 0.859 |
| 64 | 12.872 → 6.778 | 1.436 → 1.421 | 0.954 → 0.916 | 2.618 → 2.583 | 7.029 → 1.142 |

The unchanged extractor, numerical rates and writer stay near their earlier
costs. The editor falls about 5.7/6.2 times, making the complete-State writer
larger than the editor in the new income refresh. Treasury and collection clock
are still preserved: this service refreshes rates, it does not collect income.

Fences and retained intermediate buffers are intrusive; their medians do not
sum to full-step medians. Unrelated B512 effects profiles vary from 37 to 201 ms
between runs despite 90/87 ms unfenced transitions. That fluctuation is not a
replacement-validation speedup or regression claim.

## Contract and verification

Only parallel editor plus parallel container chooses the new predicate. It
recomputes full grammar each call using the original context/string pools and
zero inherited replacement errors. The generated plan changes one grammar
predicate and adds a boolean buffer; source/target/length/type/arity checks,
combined error bits, required capacity, copying, sections and cohort publication
retain their original order and behavior. Container-reference, missing legacy
policy and the original serial editor keep their previous implementations.

All 25 correctness checks passed, including original editor contracts, rich,
random, deep and malformed trees, lazy offsets, zero capacities, masks, exact
flags/sizes/padding and full native transactions with no hot host reads. Both
whole-transition grids passed all 12 cases with identical paired fixtures,
source buffers, capacities, draws, complete output records and native keys.
Both income profiles passed eight cases/24 captures, including all intermediate
input/return/writer tensors and their layout/storage/version metadata. Every
native State/history/RNG/key and original source stayed exact; no field, legal
choice, lane or dice result was clipped.

Before/after frozen commits are `0371943` and `ea82d1f`. All 109 native/build
inputs and native binary `61316df7…` are identical. The only executed production
changes are the parallel editor and its new validation helper; other commit
changes are tests, documentation and reports. Both runtimes pin actual imports,
86 assets and the same Torch 2.14.0 environment. Unit-parallel JSON, unrolled SHA,
parallel editor/container, explicit parallel RNG copy and certified immutable-
source reuse are unchanged. Certificate hits do not predict chronological-game
hit rates.

The candidate complete-step grid took 67.43 seconds and charged 6.318 GB; the
income profile took 12.46 seconds and charged 4.761 GB. Both include the full
3 GB MPS reservation, stayed below the 7 GB stop threshold inside the unchanged
8 GB/180-second guard, and used at most 12 CPU cores. The correctness guard
recorded 4,781,188,264 bytes. Raw negative and variable timing evidence is retained.
