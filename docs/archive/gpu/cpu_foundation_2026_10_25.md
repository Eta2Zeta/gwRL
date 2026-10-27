# CPU backend foundation: initial evidence

The shared batch interface, CPU reference wrapper and guarded comparison harness
are implemented on `codex/gpu-selfplay`, commit
`a1f9c9d69915968f463f71452f546483fef479f7`. The existing scalar CPU training
path remains the default. **No GPU implementation or GPU speedup is claimed.**
See the [interface and commands](README.md) and [curated evidence](cpu_foundation_2026_10_25.json).

## Correctness

- All **26 C++ suites** passed.
- The broad Python run passed **496 tests**; a final **25-test parity/harness
  run** passed after RNG-audit and stale-chance-key hardening. These counts
  overlap and are not additive.
- Four complete sampled three-round games, seeds 1951–1954, matched the original
  CPU implementation across **2,737 transitions**. Selected actions, chance
  events, final rule state, history, execution RNG and returns matched exactly.
- The clean-commit harness matched **eight real fixed positions** and **two
  complete three-round scripted replays** between direct CPU and wrapped CPU.
  Ordered legal choices, decision owners, pending requests, full rule/history
  state, numerical inputs and explicit-outcome RNG preservation were checked.

The fixed positions are the opening, first actual chance request, Japan's first
combat movement and Japan's second-round combat movement, for each of two seeds.
The complete replay traces contain 687 and 663 transitions. Each was measured
once per implementation after one warmup; there are two distinct games, not four
different training games.

## Initial timings

| Audited workload | Direct CPU | Wrapped CPU |
| --- | ---: | ---: |
| Eight fixed-position steps, including numerical export | 0.654 s | 0.734 s |
| Two complete three-round rules replays | 15.107 s | 15.209 s |

These are single paired measurements without variance estimates. Audited replay
wall includes host witness checks and driver overhead; operation timings are
also recorded separately. Environment construction/restoration, policy/dice
preparation, warmup and final state audit are outside these timed loops.

The complete supervised invocations took **80.874 s** for fixed positions and
**100.310 s** for scripted games. Reported preparation took 24.230 / 24.248 s,
and warmup took 27.039 / 36.697 s, respectively. The difference from the table is
startup, repeated environment setup, verification and reporting—not extra
training. There is no MCTS, neural inference, optimizer update or learned policy
in this benchmark. Its throughput must not be compared with the earlier
60-game self-play experiment.

The two jobs ran sequentially with three reserved CPU process slots, one worker
thread and an 8 GB sampled aggregate guard that stops at 7 GB. Charged memory
peaked at **0.827 GB** and **0.601 GB**, including supervisor/worker descendants
and macOS compressed pages. Both finished without truncation or monitor failure.

## Provenance and next use

Both reports began from a clean working tree at the implementation commit and
verified that source/native hashes stayed unchanged. Raw reports and recorded
workloads remain ignored under
`studies/campaign/runs/backend-foundation-2026-10-25/`; the JSON here pins their
hashes, configurations, fixtures, complete lane witnesses and timings.

The CPU reference before this work is
`d1c672954d8e1bb24ca43cd98c0199f4daac81f7`. Its native SHA-256 was
`6b6718f2cc8d9e1ac77265b4b700935d554f38e5fd970417891199f04f461303`;
the new native SHA-256 is
`f27924cca2235c457932fa2dc3adb5a2968391c61b9b96fb861d22d7b63b96ae`.
The additive explicit-outcome API is separate from unchanged ordinary sampling.
Existing frozen training checkpoints and learned weights were not rewritten.

This establishes a tested CPU reference and a common correctness boundary for
future GPU work. Larger device batches, transfers, compilation, real batched
search and complete learning still require their own measurements.
