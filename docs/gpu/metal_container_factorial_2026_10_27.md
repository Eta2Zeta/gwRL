# Editor/container factorial comparison

Combining parallel arena copying and parallel container-source validation reduced
the measured GPU recruitment-chance transition from 82.58 to 43.43 ms at B1 and
149.90 to 54.17 ms at B64. GPU still loses to native execution at B64. These are
complete supported recruitment transitions, not full-game, MCTS or training
throughput. The default editor and container policies remain reference.

The [curated evidence](metal_container_factorial_2026_10_27.json) pins all four
raw artifacts, complete shared provenance, the clean native build, every policy
selection, native controls, source/output witnesses and resource bounds.

## Four matched policies

Editor policy controls full-arena copying/relocation. Container policy controls
source-tree validation and removal of duplicate serial zeroing; the caller
already allocates zeroed blocks. Original target/mode/value logic, error order,
required sizes and rollback remain. Both are explicit independent choices.
Unit-parallel JSON, unrolled SHA, default digest groups and certified immutable
source reuse are identical throughout.

Median GPU milliseconds across four families and three unfenced repetitions:

| Lanes | Reference / reference | Parallel editor / reference container | Reference editor / parallel container | Parallel / parallel |
|---|---:|---:|---:|---:|
| 1 | 82.577 | 64.934 | 63.813 | 43.432 |
| 4 | 93.271 | 68.422 | 76.419 | 45.173 |
| 16 | 109.436 | 74.399 | 86.536 | 47.378 |
| 64 | 149.895 | 88.783 | 114.327 | 54.165 |

Both parallel policies give the best observed result at every tested size:
1.90/2.06/2.31/2.77 times the throughput of both reference policies. Every run
also measures the original native serial path and persistent ten-worker pool.
Controls from the best-policy run are:

| Lanes | GPU | Native serial | Native ten-worker pool | GPU / serial | GPU / pool |
|---|---:|---:|---:|---:|---:|
| 1 | 43.432 ms | 0.786 ms | 0.821 ms | 55.23× | 52.88× |
| 4 | 45.173 ms | 3.241 ms | 1.899 ms | 13.94× | 23.78× |
| 16 | 47.378 ms | 12.390 ms | 6.840 ms | 3.82× | 6.93× |
| 64 | 54.165 ms | 44.952 ms | 23.714 ms | 1.20× | 2.28× |

The JSON retains all four runs' CPU controls, including ordinary timing
variation. Ratios are ratios of pooled medians within the corresponding run.
Native timing includes the original guarded `resolveChance`, its internal clone,
validation/history/RNG, output key and pool dispatch. External trial preparation,
locks/GIL, verification and boxing are excluded. GPU timing includes the complete
handler and final fence; setup/reserve, expected keys, warmup and verification
are excluded.

## Remaining costs and verification

Separately fenced best-policy stages at B1/B64 are effects 8.86/11.50 ms, Event
2.57/3.07 ms, reset 0.49/0.60 ms, identity 18.77/19.95 ms, income 8.14/11.47 ms
and RNG work 2.45/4.88 ms. Identity, income and RNG publication now remain
visible. Fenced stages are intrusive diagnostics and do not sum to unfenced
whole-step medians. A later RNG-copy prototype is absent from this frozen code.

All 64 cases passed full native State/history/RNG and Engine-key comparisons.
Every policy has identical source buffers, capacities, untaped draws, complete
output records and native keys. Certified checks yield five hits per case and
zero misses; this repeated immutable-source workload does not establish a
chronological-game hit rate. No unit, field, dice result or legal choice was
clipped. The seven independent source-validator checks and inherited container/
complete-transaction checks were validated before timing.

The runtime is clean detached `5032790`. Mutable primary native inputs no longer
matched build chronology, so a fresh two-core build was made inside the frozen
checkout. All 106 native/build inputs matched before and after; the resulting
native SHA starts `8bd4a446`. Build logs/flags/compiler/SDK/input/output manifests
are pinned separately from the measurements. Torch 2.14.0, disabled fallback/
fast math, two reserved tensor/coordinator threads and ten native workers stayed
inside the 12-core allowance.

The four exclusive runs took 24.33/20.49/22.07/18.00 seconds and charged
conservative peaks of 4.907/4.881/4.729/4.700 GB, including the full 3 GB MPS
reservation. Each remained below its 8 GB/180-second diagnostic guard and the
user's 30 GB allowance. Raw artifacts are under
`studies/campaign/runs/gpu-backend-2026-10-26/complete-chance-factorial-{editor}-{container}.json`.
Larger batches need their own guarded measurement; these grids establish no
amortization crossover or broader GPU campaign speed.
