# GPU implementation and measurements — 26 October 2026

The optional Apple GPU neural path now supports inference, learning updates,
evaluation and checkpoint recovery. The original CPU environment and CPU default
remain available. Two exact GPU rules components are implemented: dice result
processing and territorial IPP/income calculation. **The complete campaign rules
engine and Monte Carlo tree traversal still execute on CPU.**

The measurements below use `codex/gpu-selfplay`, implementation commit
`4d0c4395a2b1580453e048640966c2c733ac1ad0`. The accompanying
[machine-readable evidence](gpu_backend_2026_10_26_results.json) records settings,
source/native hashes, artifact hashes, timing samples and conservative memory
charges. Large fixtures, checkpoints and traces remain in ignored local run
storage; the report retains their witnesses rather than committing scratch data.

## Complete games

Both devices finished all four complete three-round games. The original CPU uses
PyTorch 2.11.0; the optional GPU environment uses 2.14.0. This compares the
practical runtime choices, including their library versions.

| Execution | Four-game self-play time | Completed games/hour | Conservative memory peak |
|---|---:|---:|---:|
| CPU rules/search/network | 294.951 s | 48.82 | 1.22 GB |
| CPU rules/search, Apple GPU network | 400.883 s | 35.92 | 1.30 GB |

The hybrid GPU path was **36% slower** in this workload. All four complete action
traces, final states and execution RNG states matched exactly, so this cohort also
provides a matched action workload. Including startup, the runs took 302.30 and
409.49 seconds, within one shared 1,800-second wall allowance.

The common configuration is four independent games, seeds 1951–1954, identical
fresh weights, a 16-dimensional one-layer network, 2,048 token buckets, 16 search
simulations per decision and a search depth cap of 16. Policies remain fixed
throughout this timing experiment: it measures self-play generation, with zero
learning updates. Every completed game must reach the genuine three-round
terminal; transition, wall, memory and repeated-state stops count as failures or
truncations. Float32 device differences can change selected actions and later
dice; the exact trace agreement observed here is not a general guarantee.

There were 10,906 actor-network calls; 5,719 contained only one position and just
579 contained four. Synchronized model preparation/transfer/forward time grew
from 69.70 seconds on CPU to 143.79 seconds on MPS; search outside the evaluator
took 187.16 versus 195.70 seconds. Cache clearing accounted for only 1.05 seconds.
The fixed-position inference wins below did not carry over to these small,
diverse actor batches. CPU remains the default. The next work moves complete
state and transitions onto the device and batches search without a host transfer
at every action, rather than treating GPU network placement as the finished port.

## Neural inference and learning

On PyTorch 2.14, all 16 paired inference cases passed the existing numerical
tolerances, including cold and warm checks. The cases cover opening, a chance
state and Japan's first- and second-round combat movement, at batches 1, 4, 16 and
64. At batch four, warm CPU/GPU time ratios were **1.41, 1.88, 1.67 and 1.46**.
Across all cases they ranged from **0.70 to 4.08**; the GPU was slower for the
single opening position. These batches repeat one fixed real position with ideal
cache reuse, so the result does not establish diverse self-play throughput.

The update benchmark uses the actual learner on 578 numerical positions from a
fresh completed three-round game, with terminal outcomes and zero bootstrapped
targets. Its policy targets are the balanced scripted baseline; this is a
supervised update workload, not a demonstration of search learning or strength.
All workers use the same fixture bytes, initial weights and sampled minibatch
orders: batch size 32, 16 epochs, 16 Adam steps per agent, 48 total.

| Runtime | Synchronized update time | Comparison |
|---|---:|---|
| Original CPU, PyTorch 2.11 | 8.687 s | Practical CPU reference |
| CPU, PyTorch 2.14 | 15.435 s | Same-version diagnostic |
| Apple GPU, PyTorch 2.14 | 7.429 s | 1.17× throughput versus original CPU; 14.5% less time |

The same-version CPU/GPU ratio is 2.08×, but quoting only that number would hide
the slower CPU execution in the newer library. CPU 2.11 and CPU 2.14 produced
identical final weight digests and update/loss records on this fixture.

The original strict parameter comparison remains **failed**, with maximum
difference 0.004841 in four scalar output biases. These add a common constant to
policy scores, which cancels mathematically during normalization; float32
gradient residue can nevertheless make Adam update them differently. Every
nonredundant parameter passes the original tolerance, with maximum difference
0.00002231. A separate check of 1,202 policy/value scalars across 32 sampled real
positions passes unchanged inference tolerances, with no top-action mismatches;
maximum policy error is 1.79e-7 and raw-value error is 8.77e-5. Replacing only
those biases leaves value outputs bit-identical. These are sampled functional
checks, not bitwise learning equivalence or evidence of better play.

The update guard's conservative peaks were 2.14 GB for the original CPU and
14.62 GB for MPS. The latter includes the entire configured 11 GB allocator
reservation and can double-count unified memory; it is not live tensor usage.

## Exact rules components

The fused Metal dice kernel matches native integer results and validation masks,
including conditional rerolls. At 4,096 independent lanes its resident execution
was **74–76× faster** than the native primitive; at four lanes it was about
8–9× slower. Packing, transfers, compilation and host inspection are reported
separately and are excluded from that resident ratio. The kernel does not sample
randomness, apply casualties or complete a combat/game transition. The exclusive
run is used; an earlier timing that overlapped a test process is excluded.

The income port reads real native states through two contiguous numerical
buffers and reuses a shared static context. CPU and MPS results match native
integer oracles exactly through 1,024 lanes. At 1,024 lanes the existing C++
calculation took about **1.616 ms**, GPU resident calculation **1.276 ms**, and
capture/upload/GPU calculation together **4.455 ms**. At four lanes native C++
took about 6.67 microseconds versus 846 microseconds for resident GPU calculation.
There is no end-to-end gain in this benchmark, so current self-play continues
using CPU income. A possible benefit would require enough states already resident
on the device.
The component calculates income; treasury collection and phase changes remain
native CPU transitions.

## Memory retention diagnosed and mitigated

The first complete-game MPS attempt under PyTorch 2.11 hit the 24 GB guard before
any GPU game finished. It provides no completed-game GPU rate. A controlled
varied-position probe reproduced native MPS compilation-cache growth: physical
memory remained about 4.76 GB even after clearing Python, model and allocator
caches. Our bounded caches and live tensors did not explain that retention.

PyTorch 2.13 added graph-cache release to its public cache-clearing operation
([official release](https://github.com/pytorch/pytorch/releases/tag/v2.13.0),
[tagged implementation](https://raw.githubusercontent.com/pytorch/pytorch/v2.13.0/aten/src/ATen/mps/MPSHooks.mm)).
The isolated optional environment pins 2.14.0; `.venv` remains on 2.11.0. Long MPS
execution requires 2.13 or newer, rejects CPU fallback/fast math and shares one
resource policy across successive evaluators. It clears native caches at safe
completed boundaries, normally every 32 actor forwards. Weights, optimizer,
examples, unfinished games and random state are preserved.

The matched 96-call varied-position probe on 2.14 peaked below 1.4 GB physical
plus driver memory, with unchanged weights, fixture and RNG. Cache clearing has
small float32 output differences within the unchanged tolerances; it is not
claimed bit-exact. The final four-game MPS cohort completed with a 1.30 GB
conservative peak, providing the sustained check missing from the failed 2.11 run.

## Verification and next work

The validated implementation passed 27/27 native CTest suites, 136 focused Python
checks in the optional environment, 49 checks in the original environment (three
new-runtime MPS cases correctly skipped), and nine real CPU CLI recovery/signal
tests. These counts overlap. The native binary income probe also passed 26 exact
CPU/MPS cases. Earlier test-wrapper watermark settings caused 18 MPS setup errors;
after correcting that wrapper all 32 relevant GPU checks passed. An earlier CPU
CLI check overlapped source edits and was rerun successfully against frozen code.
The separate held-out evaluation helper also passed eight targeted checks after
adding persistent GPU cache policy and device/library identity to its cache and
paired-comparison contract. Legacy reports without that identity are preserved
and require a fresh evaluation directory.

Benchmarks run sequentially, under at most 12 CPU cores and 30,000,000,000 bytes
aggregate memory, with lower experiment-specific guards and no training job
alongside them. Each timing configuration has one invocation; these are not
confidence intervals or equal-compute learning-strength evaluations. CUDA API
selection exists, but execution has not been tested on NVIDIA hardware.

The user selected this Mac's Apple GPU for the continuing full rules/search port.
The requested roughly 90% GPU capacity is interpreted as utilization intent;
Metal does not expose an exact percentage-of-cores cap. The CPU and memory limits
remain unchanged. Shared data, interfaces, portable tensor components and CPU
conformance fixtures are retained. Movement, legal choices, combat, politics,
interrupts and tree state still need complete device execution before a full GPU
campaign backend can be registered.
