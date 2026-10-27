# Combined Apple GPU route preparation

Both implementations matched the complete native route results and preserved State, history and all RNG words in all 16 measured cases. At 64 positions, combined preparation reduced fresh GPU preparation plus query time by 22–34%. At four positions it did not produce a consistent material improvement; CPU remains faster for these small batches. The combined implementation remains explicitly selectable, with reference preparation the default.

The optimization uses one contiguous output allocation and one Metal dispatch for the existing political-relation, LandAttack-declaration and route-index work, including index initialization. It preserves every result field, error and source check. It does not reduce the candidates or change movement rules.

## Matched timings

Median milliseconds of five repetitions. “Fresh” includes preparation for each immutable source; it does not reuse preparation from an earlier state. Native CPU calls execute serially inside C++ and exclude Python result boxing.

| Position | Positions | CPU | GPU reference, fresh | GPU combined, fresh | CPU / combined |
|---|---:|---:|---:|---:|---:|
| R1 combat | 1 | 0.452 | 3.620 | 3.607 | 0.13× |
| R1 combat | 4 | 1.635 | 3.732 | 3.572 | 0.46× |
| R1 combat | 16 | 6.634 | 4.402 | 3.801 | 1.75× |
| R1 combat | 64 | 26.441 | 6.023 | 3.996 | 6.62× |
| R1 noncombat | 1 | 0.179 | 3.277 | 3.392 | 0.05× |
| R1 noncombat | 4 | 0.728 | 3.370 | 3.396 | 0.21× |
| R1 noncombat | 16 | 2.716 | 4.181 | 3.808 | 0.71× |
| R1 noncombat | 64 | 10.688 | 5.163 | 4.054 | 2.64× |
| R2 combat | 1 | 0.331 | 3.581 | 3.300 | 0.10× |
| R2 combat | 4 | 1.444 | 3.371 | 3.414 | 0.42× |
| R2 combat | 16 | 5.099 | 4.223 | 3.417 | 1.49× |
| R2 combat | 64 | 21.392 | 5.063 | 3.966 | 5.39× |
| R2 noncombat | 1 | 0.136 | 3.261 | 3.150 | 0.04× |
| R2 noncombat | 4 | 0.608 | 3.290 | 3.239 | 0.19× |
| R2 noncombat | 16 | 2.444 | 4.058 | 3.617 | 0.68× |
| R2 noncombat | 64 | 8.715 | 5.212 | 3.936 | 2.21× |

These are supplied-route checks, not games per hour. The noncombat corpus has no accepted routes; it primarily measures rejection work. Separate correctness tests include legal routes. This CPU baseline is a serial component, not an optimized 12-core simulation service.

## Preparation profile and validation

The earlier profile measured relations, declarations and indexes separately, with a device fence around each stage. Declarations were the largest component: roughly 1.6–2.1 ms at four positions and 2.35–3.18 ms at 64. Fenced stages must not be added and represented as an unfenced complete-step measurement. This profile predates the separately documented income-rate fix; the paired timings above use the corrected CPU contract on both sides.

The combined implementation passed 35 route, political, declaration and allocation checks. Two additional constructor/static-context checks passed after review, and all six benchmark-contract checks passed. The native 27-suite run and three income-contract regressions passed for the separate CPU correction.

## Provenance and resource limits

Code commit: `69ccf0a516371afaa824d9d85c9334503e634197`. Source hashes, dirty-tree disclosure, native binary hash, all repetitions, complete field comparisons and raw artifact digests are recorded in [the tracked data](metal_route_preparation_2026_10_26.json). Two unrelated untracked recruitment-transaction files existed during measurement; they are outside the route execution path. Sources remained unchanged within each run.

Each timing process used two Torch CPU threads, disabled MPS fallback/fast math and reserved 3 GB of GPU allocation capacity. The reference and combined runs were sequential, with no other agent compute running. Their guarded elapsed times were 28.27 s and 28.25 s; peak charged memory was 4.938 GB and 4.927 GB, including the full 3 GB reserve.
Each run prepared one genuinely completed three-round scripted game outside the route timer, with the same seed, policy, complete query sets and safety limits. No learning, model or search budget was changed.

```sh
PYTORCH_ENABLE_MPS_FALLBACK=0 PYTORCH_MPS_FAST_MATH=0 \
  tmp/gpu-mps-env/bin/python tools/benchmark_campaign_resident_routes.py \
  --output <fresh-output.json> --preparation-implementation reference \
  --seconds 180 --repeats 5
```

Repeat with `--preparation-implementation fused` and a second fresh output. The supervisor enforces its own 8 GB and 180-second diagnostic limits within the user’s 12-core/30 GB allowance. The optional GPU environment remains isolated from the original CPU environment.
