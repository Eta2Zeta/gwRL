# Field-parallel State JSON experiment

Parallelizing whole State fields did not improve upon the earlier unit-entry
formatter result. Keep the unit-only formatter and unrolled SHA as the candidate
for the complete-step comparison; field parallelism remains experimental and
optional. The [curated evidence](metal_field_json_experiment_2026_10_26.json)
preserves all three raw hashes, complete provenance and guard results. The
[earlier identity report](metal_identity_optimizations_2026_10_26.md) is unchanged.

The experiment gives each lexical State field an independent measure/write
task, plus separate unit-entry tasks. It preserves exact native ordering and
uses the original serial GPU diagnostics on malformed input. Three exclusive
runs tested fragment groups 1, 4 and 32. Each used the same eight native source
and after-effects snapshots, batches 1/4/16/64, three repetitions, unrolled SHA
with default digest groups, and a paired fully serial formatter. Certificates
and source-cache shortcuts were disabled.

Median milliseconds across 24 warm samples per row. Serialization is a
separately fenced diagnostic; complete identity includes State JSON/SHA and
outer Engine JSON/SHA with one final fence.

| Field group | Lanes | Serial JSON | Field JSON | Serial full identity | Field full identity |
|---|---:|---:|---:|---:|---:|
| 1 | 1 | 19.741 | 14.757 | 28.583 | 23.664 |
| 1 | 4 | 20.194 | 14.105 | 28.996 | 23.028 |
| 1 | 16 | 20.886 | 14.292 | 29.766 | 23.017 |
| 1 | 64 | 22.047 | 14.562 | 31.388 | 23.612 |
| 4 | 1 | 19.732 | 14.720 | 28.423 | 23.674 |
| 4 | 4 | 20.214 | 14.124 | 29.033 | 22.922 |
| 4 | 16 | 20.855 | 14.396 | 29.868 | 23.274 |
| 4 | 64 | 22.028 | 14.595 | 31.179 | 23.517 |
| 32 | 1 | 19.755 | 14.776 | 28.436 | 23.527 |
| 32 | 4 | 20.189 | 14.094 | 29.030 | 22.858 |
| 32 | 16 | 20.962 | 14.220 | 30.011 | 23.151 |
| 32 | 64 | 22.059 | 14.601 | 31.228 | 23.686 |

Field parallelism beats the fully serial formatter within these paired runs,
but the previous unit-only experiment measured roughly 9.5–10.4 ms for JSON and
18.3–19.5 ms for the full identity on identical native checkpoints. That was a
separate run, not a direct paired unit-versus-field measurement. The intended
additional improvement was not demonstrated. Group sizes show no useful stable
difference, so the proposed divergence explanation alone is insufficient.
Counting and then writing the largest remaining fields repeats work that the
unit-only prefix performs once; this is a profiling hypothesis, not a measured
cause.

All 96 cases and 192 mode rows matched every native byte, State/Engine key,
digest word, count, error, metadata value and padding byte. Source State/history/
RNG remained unchanged. The three runs have identical provenance and full
native checkpoint, key, byte-count, unit-count and record-capacity witnesses;
those witnesses also match the earlier unit experiment. No field, unit, choice
or message was truncated. Native State identity excludes history/RNG by
definition while the complete resident source retains and verifies both.

The clean detached runtime was `7d0c1b0`, using native binary `b061ab73…` with all
101 native inputs unchanged from its compiled-source proof. Torch 2.14.0 used
two CPU threads, disabled fallback/fast math and a 3 GB MPS reservation. Runs
took 23.46/23.48/24.76 s and charged conservative peaks of
4.609/4.606/4.604 GB, within each 8 GB/180-second diagnostic guard and the user's
12-core/30 GB allowance. Raw artifacts are
`studies/campaign/runs/gpu-backend-2026-10-26/identity-fields-group-{1,4,32}.json`.

These are replicated-snapshot identity components. They do not measure complete
chance transitions, campaign games, MCTS, training throughput or playing strength.
