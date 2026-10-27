# Native campaign concurrency — 25 October 2026

Independent game-engine calls can now run concurrently. Four matched, complete
three-round frozen-policy games took **8m 45.60s**, versus
**11m 38.13s** before, including worker startup and supervision:
**1.33× throughput** (24.7% less elapsed time). This measures game collection; it does not include optimizer updates
or recovery saves and is **not a measured full-training speedup**.

The [evidence JSON](native_concurrency_2026_10_25.json) records settings, hashes, individual timings,
resource monitoring and diagnostic accounting. The implementation is frozen at
commit `332866c4fe6bdcb8fe8281a979e096776457ced7`.

## Correction and related safety work

The Python/C++ campaign boundary releases Python's interpreter lock for pure
native work. Every bound environment has its own operation mutex. Independent
games and clones have separate mutexes, so they can run native operations at the
same time; overlapping operations on the same native environment remain protected.
Multi-call sequences are not made transactional: callers still control their
ordering and authoritative action validation remains in force.

The GIL is released **before** waiting for the environment mutex, and the mutex
is released before Python's lock is reacquired. Native results are owned snapshots
before conversion back to Python. JSON conversion and graph-compiler callbacks
that use Python still hold the GIL. These details preserve same-environment safety
and avoid lock-order deadlocks rather than replacing one global lock with another.

No rules, legal choices, random distributions, horizon, model architecture,
search budget or learning objective were reduced. The search remains 16
simulations/depth 16 with four roots and four tensor threads. No subtree reuse,
policy changes or broader search redesign was introduced.

## Matched fixed-position search

Each case searches four unchanged real Japan combat-movement positions for three
waves. These timings exclude model/worker startup, scripted preparation and the
separate native probe. Actual states and execution RNG remain unchanged.

| Workload | Before search time | After search time | Throughput ratio |
| --- | ---: | ---: | ---: |
| Round-one Japan combat movement | 11.932s | 7.197s | 1.66× |
| Round-two Japan combat movement | 13.120s | 6.996s | 1.88× |

The separate native probe repeats restore, legal-action generation, one rule
action/chance operation and serialization twenty times per root, first serially
and then on four independent threads. Every outcome hash matches.

| Native workload | Before serial/threaded ratio | After serial/threaded ratio |
| --- | ---: | ---: |
| Round one | 0.97× | 3.72× |
| Round two | 0.99× | 3.37× |

These native ratios demonstrate useful parallel execution for that restricted
workload. They are not estimates of whole-game or whole-training acceleration.

## Four completed games

Both versions start from the same four three-round environments (seeds
1951–1954) and fresh, identical frozen alliance networks. All four games reach
their genuine three-round endpoint and have observed terminal returns.

| Scope | Before | After |
| --- | ---: | ---: |
| Supervised end-to-end elapsed time | 11m 38.13s | 8m 45.60s |
| Search plus actual action/chance execution | 11m 05.49s | 8m 13.67s |
| Search time | 11m 00.71s | 8m 08.94s |
| Evaluator time within search | 5m 02.24s | 4m 46.59s |

Each version executes **1,101 actual decisions** and
**136 actual chance resolutions**. Complete search-result
fingerprints match, including policy probabilities, values and visit counts.
Final serialized states include complete event history and execution RNG, so
the equality check covers more than just terminal scores.

- `opening`: exact task, model, configuration, prepared state, search-result fingerprint and final serialized engine/RNG/history hashes match.
- `later`: exact task, model, configuration, prepared state, search-result fingerprint and final serialized engine/RNG/history hashes match.
- `episodes`: exact task, model, configuration, prepared state, search-result fingerprint and final serialized engine/RNG/history hashes match.

The largest sampled aggregate memory across measured cases was
**1.556 GB** (1,556,152,320 bytes),
below the authorized 30 GB. The conservative allowance includes four search
workers, four tensor threads and two coordinators within twelve CPU cores.
The watchdog samples its worker and direct supervisor; the small sequential
launcher and sleep-prevention process are outside that RSS sample and fit the
remaining coordinator allowance. RSS sampling with a safety margin is not a
kernel allocation cap.

## Remaining costs

Separate instrumented runs preserve the plain runs' exact search outputs. They
have instrumentation overhead and are diagnostics, not the source of the speed
ratios above.

| Diagnostic | Search wall time | Evaluator wall time | Evaluator/search | Input assembly, inclusive | Model forward with graph work, inclusive |
| --- | ---: | ---: | ---: | ---: | ---: |
| Round one | 7.521s | 5.213s | 69.3% | 1.035s | 4.160s |
| Round two | 7.596s | 4.361s | 57.4% | 0.814s | 3.530s |

Input assembly includes native observation extraction. Model forward includes
graph compilation, graph-to-tensor preparation and remaining Python/tensor work.
The nested values are not independent costs and must not be added again to their
parent. Remaining forward time is not pure matrix arithmetic; it also includes
canonicalization, cache lookup and action-factor work. Both fixed-position
diagnostics use 51 model batches of four, which does not establish the batch
distribution for whole-game self-play.

Legal-action generation is the largest measured native worker CPU category:
opening: 205 calls, 6.179 aggregate calling-thread CPU-seconds (30.14 ms/call); later: 205 calls, 8.506 aggregate calling-thread CPU-seconds (41.49 ms/call). Those sums cover concurrent workers and cannot be divided by elapsed
time to claim wall-time percentages. Calling-thread CPU also excludes separate
internal PyTorch worker threads. These API-call timers include binding conversion
and do not isolate the C++ rule generator internally. The next targets are expensive legal generation
and evaluator/input processing, with further separation of Python preparation
from numerical model work before selecting another optimization.

In the uninstrumented completed-game case, evaluator work accounted for 286.59
of 488.94 search seconds (58.6%). This includes input preparation, not only
numerical neural-network operations.

## Verification and limits

All **372 Python tests** and **26 CTest suites** passed. Concurrency tests cover
serial/threaded equality, clone independence, same-native-environment overlap,
exceptions and continued Python heartbeat during native work. The heartbeat
negative control fails against the old binary with the expected assertion
`Python heartbeat could not run during the native engine call`; the corrected six-test native suite passes.
The control's binary hashes match the before/after benchmark binaries.

The summary verifies every file in the frozen new runtime. Old native SHA-256:
`05371fd29f42d4a7e4b444309785054b3b71da543430a0eef0854e7fe6dd8689`. New native SHA-256:
`1b52106f80e55afcf73b60e3b93c5adcc1aa8f80685ace5acca5adcb19803746`.
The canonical summary payload SHA-256 is `6f392923f69a7d923f3670701fbcacb71b6b4bc76b574052b773c8b596d20d94`.

Each case is one matched timed comparison without repeated-run variance
estimates. Fixed-root searches, native probes and complete-game collection have
different scopes. No optimizer update or checkpoint-write speed is inferred from
this frozen-policy collection benchmark, and no playing-strength, eleven-round
or optimal-learning-method conclusion follows from its completion or timings.
Raw artifacts remain ignored under
`studies/campaign/runs/native-concurrency-2026-10-25/`.
