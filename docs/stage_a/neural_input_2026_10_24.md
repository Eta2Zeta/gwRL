# Stage A: compile complete neural input graphs

24 October 2026. This pass moves new-position graph construction into the C++
extension. It preserves the model architecture, input schema, complete rules and
state fields, every legal action, search settings and random streams. It does
not change the learning algorithm or claim improved playing strength.

## Implementation

`src/neural_graph.cpp` traverses public JSON directly, constructs the same
ordered hierarchy/reference/geography edges and returns the existing `Graph`
fields. It does not read the engine, checkpoints, execution randomness or model
parameters. Python's existing lexical hashing and Unicode numeric-string rules
remain authoritative through cached callbacks. Numeric source constants retain
the exact Python results, including the sign of negative zero.

One Python integer per node is shared across edge endpoints, identity indices
and references. Temporary lookup caches last only for one compilation; source
string descriptors and numeric constants have separate bounded caches. The
existing context/observation/action graph and 32 MiB tensor-data caches remain.
Learned embeddings, predictions and training gradients still recompute.

`compile_graph_python` retains the original implementation as an exact oracle
and portable fallback. Reports now identify `software.graph_compiler` as
`native` or `python_reference`. An extension without the new binding reports
`python_reference`; the backend name alone does not verify a binary's version.
The measurements below also record its SHA-256. Rebuild after pulling:

```sh
./.venv/bin/python setup.py build_ext --inplace --force
```

Existing model/input/checkpoint formats are unchanged. The normal runner still
checks exact runtime sources before resume; no source-guard bypass or implicit
checkpoint migration was added.

## Matched search and play

The four-root Japan combat-movement test uses 16 simulations, depth 16 and
three fresh-tree waves. The warm number averages waves two and three. The
complete 11-round game uses four simulations and depth eight. Both retain the
same pilot model, legal menus, seeds and weights throughout; neither trains.

| Workload | Python graph traversal | Native graph traversal | Result |
| --- | ---: | ---: | --- |
| Four-root search, warm wave | 4.086 s | 3.747 s | 8.3% less time |
| Complete 11-round game, whole process | 113.274 s | 104.580 s | 7.7% less time |
| Four-root search, sampled peak memory | 1.762 GB | 1.459 GB | 17.2% lower |
| Complete game, sampled peak memory | 2.016 GB | 1.559 GB | 22.6% lower |

The opening search's entire 170-record trace is byte-identical. The complete
game's entire 1,191-record trace also matches: search priors, values and visits,
560 executed choices, 71 chance events, states, execution randomness and final
returns. Trace records include search results as well as executed transitions.

An isolated warm opening-observation compilation falls from 2.402 ms to
0.570 ms, a 4.22× graph-building speedup. This is one part of neural evaluation;
it is not a 4.22× game or learning speedup.

At the stronger budget, four two-round games with 16 simulations/depth 16
still reach the 240-second wall guard with no completed games. The optimized
run executes 398 choices and 50 chance events, versus 370 and 50 before.
Only their common completed prefix is compared; unfinished outcomes remain
null and these counts are not completed-game throughput.

## Matched learning repeat

Repeating the existing eight one-round training games, including both learning
batches and checkpoint writes, takes 93.202 seconds before and 87.107 seconds
after: **6.5% less total time** in this pair. Sampled peak process memory falls
from 2.584 GB to 2.196 GB. Collection accounts for 56.484 → 52.031 seconds;
learning updates account for 24.112 → 22.821 seconds. Small differences in the
other buckets include system timing noise, rather than new changes to saving
or reporting.

Both runs start from the same initialization and finish eight games with
386 decisions, 52 chance events, 386 terminal-target training rows and two
learning updates. Each alliance performs 32 sampled Adam steps. This repeats
the existing pilot to check implementation cost and correctness; it is not a
larger learning experiment. The model has hidden dimension 16, one message
layer and 2,048 token buckets; searches use four simulations and depth eight.
Four games collect in parallel, with four tensor threads. The full command and
checkpoint comparison are retained in the machine-readable evidence.

The final learner checkpoints match bit for bit across every learner field,
including replay observations, legal actions, policy and terminal targets,
model/optimizer tensors, actual games and all random states. The comparison
covers 541 tensors (1,379,068 bytes); runner metadata also matches except the
intentionally different runtime-source hashes. Checkpoint container files
therefore have different file hashes, despite identical learning state.

## Remaining limit

A separate reference-only diagnostic, one two-round game with 16 simulations,
reaches a 600-second guard after 888 choices and 15 chance events. It is still
in Japan's second-round combat movement: 122 naval plans were started and 114
cancelled, with 467 force additions/removals and 68 raider toggles. These are
actual selected actions, rather than hypothetical search branches.

New plan IDs and decision serials distinguish repeated planning sequences in
the full state. Faster encoding does not resolve that policy/search behavior.
The diagnostic was not repeated as a speed comparison, no legal choices were
removed to shorten it, and no unfinished game was assigned a terminal score.
Larger training remains gated on reliable completion at the stronger budget,
and on measuring the remaining rules execution, source-copy and tensor costs.

## Verification

- All 294 Python tests and 24 C++ suites pass.
- Reference/native comparisons cover every graph field and packed double bits,
  Unicode and numeric strings, negative zero, empty/unknown fields, array
  positions, identity duplicates and ordered geography edges.
- Model outputs and every training gradient match with zero tolerance.
- Mutable source/callback lifetime regressions and deep recursion checks pass.
- One complete 11-round trajectory checks 1,193 graphs and their numeric bits:
  the context, 631 observations, 560 played actions and the final observation.
  All 1,262 before/after state and execution-RNG hashes also match.
- A matched 16-simulation serial diagnostic retains identical neural priors,
  values and visit counts. Its wall time includes profiler overhead; it is not
  a substitute for unprofiled self-play throughput.

## Scope

The reference is commit `a03437f`, archived with its original native module
before editing. Frozen-policy comparisons use the same pilot weights in fresh
current-rule games; they do not restore historical game state or perform
optimizer updates. The matched learning repeat starts both versions from the
same initialization and compares actual samples, outcomes, model/optimizer
state and random state.

The resource allowance remains 12 CPU cores and 30,000,000,000 bytes, including
coordinators. Raw traces, checkpoint files, build logs and local comparison
helpers remain ignored under `tmp/encoder-pass-2026-10-24/`.

Cases run sequentially with at most ten configured worker/tensor/coordinator
cores, leaving two for other validation work. Aggregate memory is sampled
resident RAM; it can double-count shared pages and miss brief peaks, rather
than imposing a kernel allocation cap. These are single paired invocations on
one machine, with small auxiliary validation work within the total core cap;
they are operational measurements, without confidence intervals or a playing-
strength claim.

The [machine-readable report](neural_input_2026_10_24.json) records the exact
settings, source/binary/checkpoint hashes, comparisons and raw artifact/helper
hashes. The tracked `studies.campaign.scaling_benchmark` and
`studies.campaign.run` entry points reproduce the workloads; the ignored local
wrappers add detailed traces and aggregate memory monitoring.
