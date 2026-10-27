# Recruitment identity overhead

The complete recruitment smoke test exposed a slow resident path. This follow-up
locates its identity cost; it does not measure self-play or learning strength.
The [machine-readable evidence](metal_identity_profile_2026_10_26.json) pins every
source, native binary and fixture hash used in the measurement.

Four recruitment families were measured at one lane, three repetitions each.
Each handler computes a source identity for stale-action validation and an
after-effects identity for the native Event. The expected source key is prepared
outside timing. Median fenced component times across the four families were:

| Identity operation | Source validation | After effects |
|---|---:|---:|
| Complete canonical State bytes | 19.93–20.58 ms | 20.05–21.57 ms |
| State SHA-256 | 12.98–13.25 ms | 13.04–14.00 ms |
| Outer Engine bytes | 0.23–0.29 ms | 0.24–0.30 ms |
| Outer Engine SHA-256 | 0.28–0.34 ms | 0.29–0.41 ms |

All eight identities, every output byte and metadata tensor, complete resulting
State/history/RNG, and native Engine keys matched. Source buffers remained
unchanged. State messages were 58,576–61,584 bytes; allocated byte capacity was
262,144. No fields or legal choices were dropped. These intrusive fences locate
costs; their sum is not a replacement for an unfenced complete-step benchmark.

The guarded run took 8.70 seconds and charged a conservative peak of 3.724 GB,
including the entire 3 GB MPS reservation. It used two CPU threads. Six profiler
checks passed, including an exact complete-handler integration comparison.

The measured priorities are parallel State formatting, a more efficient exact
SHA-256 kernel, and safe reuse of already computed identities for an unchanged
complete source. They remain separately selectable until matched measurements
establish their benefit. Source certificates alone do not demonstrate reuse
across successive changed game positions.
