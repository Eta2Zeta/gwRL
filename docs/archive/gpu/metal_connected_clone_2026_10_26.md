# Connected Metal search-clone measurements, 2026-10-26

The fused resident search clone now beats the sequential native clone loop at
four lanes in all three measured positions. It copies the complete game state,
reseeds only the search stream with the native SplitMix64 sequence, clears the
search test tape, and preserves execution/training randomness and history.
**This is a component result; a complete GPU rules/search backend is still unfinished.**

The generic implementation was correct but slow: at four lanes it took about
3.4–9.1 ms. One specialized Metal dispatch now takes about 0.19–0.28 ms. Both paths
remain available (`implementation="reference"` or `"fused"`) for comparisons.
The general subtree editor remains available for actual rule mutations.

## Matched timings

Median milliseconds per operation, five repetitions. Source snapshots, destination
counts, full-width uint64 seeds and every resulting native clone match between
the reference and fused runs. Fixtures are the actual opening, first pending
chance request and second-round Japan combat movement from the unchanged
three-round scripted campaign. No state field or history is dropped.

| Position | Lanes | Native CPU loop | Generic GPU | Fused GPU | CPU / fused |
| --- | ---: | ---: | ---: | ---: | ---: |
| opening | 1 | 0.0736 | 2.9756 | 0.1812 | 0.41× |
| opening | 4 | 0.2932 | 3.4086 | 0.1907 | 1.54× |
| opening | 64 | 4.5710 | 6.1791 | 0.7105 | 6.43× |
| opening | 256 | 17.3021 | 9.1083 | 0.9959 | 17.37× |
| first_chance | 1 | 0.1058 | 2.8487 | 0.2243 | 0.47× |
| first_chance | 4 | 0.3016 | 3.7073 | 0.2038 | 1.48× |
| first_chance | 64 | 5.2051 | 8.5774 | 0.6771 | 7.69× |
| first_chance | 256 | 21.6130 | 11.9877 | 0.8845 | 24.43× |
| round2_japan_combat_movement | 1 | 0.3075 | 7.2286 | 0.2722 | 1.13× |
| round2_japan_combat_movement | 4 | 1.1228 | 9.1378 | 0.2772 | 4.05× |
| round2_japan_combat_movement | 64 | 19.2260 | 20.1667 | 0.8638 | 22.26× |
| round2_japan_combat_movement | 256 | 78.7743 | 25.0550 | 1.1596 | 67.93× |

GPU timings include dispatch and synchronization over already resident state and
seeds. Initial native capture, upload, shader setup, seed preparation and complete
host conformance inspection are separately recorded in the JSON evidence. The CPU
baseline includes one Python/native call per clone and native copied-state
construction. It is a sequential component baseline, not an optimized 12-core
CPU clone service. These ratios are not completed-game or learning throughput.

The fused path also avoids the earlier generic editor's per-lane validation/copy
loops. One workgroup handles each destination: a leader checks the fixed header
and computes the native search seed, then threads copy records in parallel while
rewriting the final random-state subtree. Capacity failures and malformed headers
remain explicit errors. Ordinary clone and search clone remain distinct.

## Exactness, resource use and provenance

All 12 cases pass every-record comparison against actual native `clone_for_search`
outputs, including lengths, section indices, padding, shared strings and all RNG
bits. Representative full native restores also include history. Every source
remains unchanged. The paired JSON records seed and native-checkpoint digests,
complete native-clone digests, source/native binary hashes and raw timings.

The fused run uses clean committed source
`d68f250fc76bbdb36d94714c8558e8ef3006bc96`. The generic reference was measured at
parent `0e17eb8` with the native binary built from `5d24f12`. Its worktree contained
in-progress, unrelated wealth-context/helper files; those were not linked into
that binary or used by this clone component. That baseline is preserved with its
dirty paths and separate compiled-binary provenance, not presented as a clean
whole-tree measurement. Later diplomacy edits were not present in the fused run.

Each run was supervised alone with two Torch threads, no MPS CPU fallback, an
8 GB envelope and a 180-second shared deadline. The fused worker took 22.12 s
(23.18 s supervisor); sampled charged memory peaked at **4,635,567,344 bytes**,
including the full 3 GB MPS allocator reservation and conservative accounting.
The generic run took 23.48 s (24.12 s supervisor), peak 4,612,695,376 bytes.
Both stayed within the user's 12 CPU / 30 GB aggregate allowance. Metal does not
provide a precise “90% of GPU cores” limit.

Validation of the implementation revision included 27/27 native CTest cases and
80 focused Python checks across state, editing, strings, clone, wealth, income,
packed chance, hashing, exact indexing and scheduler behavior. The first combined
run had eight wealth shader compilation errors from using Metal's reserved word
`half` as an identifier; renaming that local variable fixed them and all nine
wealth tests then passed. The clone suites also cover malformed tiny descriptors,
fused/reference equality, boundary seeds and preserving future actual dice.
The additional benchmark harness checks passed 8/8. Overlapping suites are not
added as if they were distinct tests.

The previously measured complete-game hybrid (GPU neural evaluation with CPU
rules/search) remains **slower** than the original CPU path. These clone results
do not supersede that result. Diplomacy, movement, battle effects, full legal-menu
construction and resident search still need porting and conformance before a
complete GPU game can be timed or used for training.

[Raw paired evidence](metal_connected_clone_2026_10_26.json) includes the complete
reference/fused reports. Reproduce with `tools/benchmark_campaign_search_clone.py`
and an explicit `--implementation reference` or `--implementation fused` in the
isolated GPU environment. Keep the existing CPU environment unchanged.
