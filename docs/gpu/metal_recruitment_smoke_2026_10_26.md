# Complete recruitment diagnostic harness

The connected handler is exact in the first end-to-end harness invocation, but
its GPU latency is poor. At batch one, four fixture families took 111–136 ms per
warm complete GPU call versus approximately 0.7–0.9 ms for native CPU execution.
This is one measured repetition per family, an operational smoke check rather
than a throughput or learning-strength conclusion.

The synchronized diagnostic breakdown attributes about 33 ms to each of two
complete State/Engine identity computations, 19–38 ms to rule effects, 10–11 ms
to income refresh and 9–10 ms to Event work. These intrusive fenced stage timings
must not be added and represented as the unfenced end-to-end measurement. The
next profile separates serialization from hashing before optimizing those paths.

All four cases matched full State, history, every RNG word, pending choices and
Engine keys, with unchanged source buffers and stable source provenance. The
supervisor completed in 6.15 s; peak charged memory was 3.724 GB, including the
entire 3 GB MPS reserve. [The tracked artifact](metal_recruitment_smoke_2026_10_26.json)
records the single repetitions, fixtures, capacities, source hashes and native
binary hash. The dirty tree included the independently developed movement helper;
this is not presented as a clean whole-repository build.

The native probe checks the actual warm source-key cache, calls original
`Engine.resolveChance` (including its internal transactional clone, rule hooks,
validation, Event and RNG), and obtains the output key inside timing. Preparation
clones, owner locks, input conversion and full output inspection are separate.
The GPU timing includes the current full resolver without CPU rule effects or
result reuse. Inputs are valid restored controlled-minor fixtures followed by a
real legal recruitment-roll action; they are not claimed to be naturally reached
competitive-game positions.

`CampaignDiagnosticPool` adds an explicit persistent native CPU service for these
comparisons. It supports one to ten workers, leaving room for the coordinator
within the 12-core allowance. Source owners are pinned and route states locked
before parallel read-only calculation; outputs retain original ordering/errors.
Pool dispatch and result work are timed, startup is recorded separately. It does
not change the registered CPU backend, which remains the sequential reference.

The five direct pool checks passed, including exact ordered route results,
shared owners/concurrent callers, bounds, stale-key worker exception and recovery.
Seventeen route/stress/pool harness checks and seven recruitment diagnostic
checks also passed. The default resolver has no profiling fences or timers;
explicit diagnostics alone synchronize stages. No source game, checkpoint,
learning method, model, search budget or horizon was changed for the measurement.

The harness supports the full batch grid, but that grid is not reported as run
here. CPU remains the only complete registered game backend. This result exposes
an implementation bottleneck to fix; it does not establish a useful GPU speedup.
