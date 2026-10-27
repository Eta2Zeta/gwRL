# CPU and Apple GPU performance

Current assessment as of 27 October 2026: **no end-to-end GPU self-play or training
speedup has been demonstrated.** CPU remains the default. Some resident rules
operations become faster at hundreds of simultaneous positions, while small
batches strongly favor CPU. See [capabilities](README.md) before interpreting
these measurements.

## Completed self-play

The measured hybrid uses GPU neural execution with CPU rules and tree search.
Both runs completed the same four three-round games with fresh fixed weights,
16-dimensional one-layer networks, 16 search simulations and depth cap 16.

| Execution | Four completed games | Games/hour |
| --- | ---: | ---: |
| CPU rules, search and network | 294.951 s | 48.82 |
| CPU rules/search, Apple GPU network | 400.883 s | 35.92 |

The hybrid was 36% slower. Actor inference batches were predominantly small;
fixed-position neural batch wins did not carry over to self-play. CPU used
PyTorch 2.11 and MPS used the isolated 2.14 environment, so this compares the
practical runtime choices, including library differences. Policies did not learn
during this timing run. Matching action traces in this cohort does not guarantee
identical float32 search behavior generally. The
[complete report and JSON](../archive/gpu/gpu_backend_2026_10_26_results.md)
retain settings, failures, memory accounting and provenance.

## Supported resident recruitment steps

A later matched operation comparison tested complete supported recruitment-roll
transactions with four fixture families and three unfenced repetitions. Times
below are milliseconds per batch of positions, using the candidate's CPU controls.

| Positions together | GPU | Native serial CPU | Native ten-worker CPU |
| --- | ---: | ---: | ---: |
| 1 | 40.805 | 0.856 | 0.949 |
| 64 | 47.496 | 49.105 | 24.860 |
| 512 | 87.099 | 383.727 | 153.669 |

At 512 positions the GPU was about 1.76 times faster than the ten-worker control;
CPU won at 1 and 64. GPU timing included complete supported handling and a final
fence, with preparation and verification separate. The explicit configuration
used parallel editor/container/RNG policies, unit-parallel canonical JSON,
unrolled SHA and certified repeated-source reuse. It is not a claim about all
default policies or chronological-game cache hit rates.

Runs were sequential with no confidence interval. These are repeated-source
operations, not complete GPU games or MCTS. The
[measurement and evidence](../archive/gpu/metal_replacement_validation_measurement_2026_10_27.md)
preserve exact capacities, full State/history/RNG/key comparisons, native controls
and source/environment identities. A subsequent
[integer-width experiment](../archive/gpu/metal_integer_width_measurement_2026_10_27.md)
found no material isolated benefit despite lower sequential whole-step medians.
That negative result remains part of the evidence.

## What is still unmeasured

The resident port needs complete chronological transitions and device search
before it can supply a full-game GPU comparison. Existing learning uses four
parallel games; a 512-position operation result does not establish that its
actual search will sustain such batches. Larger kernels or high utilization do
not establish useful learning strength.

The native ten-worker control scaled only about 2.5 times over serial execution
at 512 positions in the operation measurements. The cause remains unproven. A
[prepared worker diagnostic](../archive/gpu/native_worker_diagnostic_2026_10_27.md)
has harness validation, but its full sweep has not run. Scheduling, allocation
and memory contention remain hypotheses rather than measured diagnoses.

Further comparisons must keep complete choices, state, dice distributions,
models, search budgets and horizons unchanged, report completed-game throughput
and aggregate peak memory, and evaluate playing strength separately under equal
compute budgets. Historical component and neural-update reports are available
in the [evidence archive](../archive/gpu/README.md).
