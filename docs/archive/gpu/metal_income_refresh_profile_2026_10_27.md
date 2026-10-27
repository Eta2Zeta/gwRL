# Income refresh subprofile

The editor is the largest measured part of the resident income refresh, followed
by its complete-State writer. At 64 lanes these stages take 7.03 and 2.62 ms;
the extractor and numerical rate calculation take 1.44 and 0.95 ms. This points
to replacement validation/copying before extractor tuning.

The [curated evidence](metal_income_refresh_profile_2026_10_27.json) pins the
raw artifact, source/environment/native provenance, capacities, complete
intermediate/output checks and guard. This is a scoped intrusive profile inside
the complete recruitment handler. Every original implementation is delegated
unchanged; production methods have no timers or implicit fences.

Median milliseconds across four fixture families and three captures:

| Lanes | Full refresh | Extract | Income rates | State writer | Editor |
|---|---:|---:|---:|---:|---:|
| 1 | 9.206 | 0.982 | 0.821 | 1.791 | 4.900 |
| 64 | 12.872 | 1.436 | 0.954 | 2.618 | 7.029 |

Setup, work between calls and publication account for separately measured gaps
of roughly 0.70/0.82 ms. Stage medians do not sum to median full refresh. Fences
and retained intermediate allocations change execution scheduling and memory
lifetimes, so these timings do not estimate self-play or whole-step throughput.

This service refreshes `incomeComponents` and `incomeKnown` while preserving
cash, complete clock and every unrelated field. It does not collect income.
The writer reconstructs the complete State subtree; the editor then validates
and publishes that replacement. The explicit parallel editor/container policies,
unit-parallel JSON, unrolled SHA and certified-source reuse match the selected
complete-handler configuration. The default editor/container policies remain
reference.

Seven focused checks passed before timing, including exact-instance scoping,
inactive delegation, exception/overlap restoration, complete tensor layout/
storage/version metadata, writer buffers and hot host-read traps. All eight
cases and 24 timed captures matched the original complete handler and every
native State/history/RNG/Engine key. Extractor/rate/editor returns, writer
blocks/lengths/errors and full intermediate inputs matched in bits and metadata.
Source buffers, static context and original native environments stayed intact.

The clean frozen runtime is `0371943`. All 109 tracked native/build inputs
exactly match the saved build proof for native SHA `61316df7…`; the verified
binary was installed atomically. Assets, actual import paths and Torch 2.14.0
GPU environment are pinned. The exclusive run took 12.85 seconds and charged
4.910 GB including the full 3 GB MPS reservation, below the 7 GB stop threshold
inside its 8 GB/180-second guard. It used two CPU tensor threads, disabled fallback
and fast math, and preserved every field and choice.

The next concrete candidate is the editor's serial `edit_tree` over the whole
replacement. Its benefit still needs exact validation tests and matched complete
transition timing. This profile establishes neither a new implementation speedup
nor full-game/search/training feasibility.
