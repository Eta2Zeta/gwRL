# Exact Apple GPU identity optimizations

Parallel unit-entry formatting and the unrolled SHA kernel reduced the measured
standalone identity pipeline from 32.71 to 18.34 ms at one lane, and from 35.26 to
19.49 ms at 64 lanes. These are State/Engine identity operations, not complete
game transitions, self-play throughput or evidence of stronger play. The
[curated evidence](metal_identity_optimizations_2026_10_26.json) retains source,
native, environment, fixture and raw-artifact fingerprints.

The [earlier profile](metal_identity_profile_2026_10_26.md) identified State
formatting and SHA as the main identity costs. The original paths remain the
defaults. Both alternatives are explicit: unit entries are measured and written
independently into their exact native positions; SHA uses sixteen scalar schedule
words and 64 unrolled compression rounds. Neither alternative removes bytes,
fields, diagnostics or legal choices. Malformed serializer inputs retain the
original serial GPU diagnostic path.

## Complete identity pipeline

Each batch uses identical copies of one exact native snapshot. Four recruitment
families supply both the pending source and native after-effects position:
eight snapshots, four batch sizes, three warm repetitions, all four combinations.
The timer includes State JSON, State SHA, outer Engine JSON and Engine SHA, with
one final device fence. Setup/upload, first calls and inspection are separate.
No identity certificate or source-cache shortcut is used.

Median milliseconds across all 24 warm samples per batch size and combination:

| Lanes | Reference | Parallel units only | Unrolled SHA only | Both |
|---|---:|---:|---:|---:|
| 1 | 32.707 | 22.490 | 28.407 | 18.343 |
| 4 | 33.242 | 22.710 | 28.996 | 18.638 |
| 16 | 33.923 | 23.069 | 29.723 | 18.900 |
| 64 | 35.262 | 23.464 | 31.160 | 19.487 |

Separately fenced diagnostic stages place State formatting at 19.72–22.04 ms
for reference and 9.55–10.36 ms for parallel units. State SHA takes
13.02–13.12 ms for reference and 8.99–9.27 ms for unrolled. Fenced components do
not sum exactly to the unfenced pipeline timer. Remaining serial State fields
are still a measured cost; the newer field-parallel implementation is separate
work and is not included in this table.

## SHA group sizing

A second run tested tightly packed State and 244-byte outer Engine messages with
both kernels and default/1/4/32 threadgroup sizes. It completed all 64 cases and
512 mode/group rows exactly. Groups schedule independent complete-message
threads; they do not parallelize a message's sequential compression chain.

| Lanes | State reference, default | State unrolled, default | Unrolled groups 1 / 4 / 32 |
|---|---:|---:|---:|
| 1 | 13.034 ms | 8.969 ms | 8.970 / 8.954 / 8.942 ms |
| 4 | 13.294 ms | 9.677 ms | 9.782 / 9.766 / 9.715 ms |
| 16 | 13.956 ms | 11.301 ms | 11.198 / 11.276 / 11.229 ms |
| 64 | 13.776 ms | 11.353 ms | 12.038 / 12.105 / 11.926 ms |

Keep default group sizing: explicit groups show no consistent advantage. Short
outer-message times stay around 0.17–0.20 ms, with inconsistent small differences.
Do not combine this run's SHA times with the first table. Direct SHA receives
tightly packed bytes; identity SHA receives ranged slices of 262,144-byte slabs
and includes canonical range/error wrappers. The runs also have distinct timing
and synchronization contexts. Each comparison uses its own paired measurements.

## Verification and provenance

All 32 identity cases and 64 SHA cases matched complete native bytes, keys, raw
digest words, counts, error flags, output metadata and padding. SHA also matched
`hashlib`. All source State/history/RNG buffers remained unchanged, and native
checkpoint fingerprints agree between the two runs. State messages contain
58,576–61,584 bytes. Native State identity excludes history/RNG by definition;
the complete resident source retains and verifies them. No training games or
learning updates occurred.

Both runs used the clean detached benchmark checkout, Torch 2.14.0, two CPU
threads, disabled MPS fallback/fast math and a 3 GB MPS reservation. The identity
run at `fc20538` took 39.91 s and charged a conservative peak of 4.615 GB. The SHA
run at `805b498` took 25.17 s and charged 3.524 GB. Both stayed within the 8 GB/
180-second diagnostic guard and the user's 12-core/30 GB allowance. Their native
binary SHA begins `b061ab73`; all 101 native inputs match the compiled-source
proof, with no C++ change between these snapshots.

Raw ignored artifacts are
`studies/campaign/runs/gpu-backend-2026-10-26/identity-combinations.json` and
`sha256-unrolled-groups.json`. The tracked JSON pins their complete SHA-256
digests, all source maps, environment manifests, settings and guard results.
Fifteen SHA correctness checks, six explicit message-kind harness checks and six
standalone identity harness checks passed before these measurements. Replicated
fixtures and component results do not establish full GPU campaign performance.
