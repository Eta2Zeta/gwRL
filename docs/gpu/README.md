# Campaign execution backends

GPU development starts on `codex/gpu-selfplay`, from CPU reference commit
`d1c672954d8e1bb24ca43cd98c0199f4daac81f7`. Both implementations will live in the
same repository. The existing C++ rules engine, scenario data and scalar CPU
training path remain in place. The shared interface, CPU wrapper and rules-replay
harness are joined by optional GPU neural execution and a first exact tensor
rules primitive. **A full GPU campaign transition engine is not implemented.**

The [initial CPU conformance and timing evidence](cpu_foundation_2026_10_25.md)
records the validated foundation and its measurement limits.
The [GPU implementation and measured results](gpu_backend_2026_10_26_results.md)
separate completed self-play, neural updates and exact rules-component timings.

## Execution contract

`studies/campaign/backends/protocol.py` defines independent game lanes and bulk
decision, action, chance, numerical-input, clone/search-clone and snapshot operations. Execution
payloads are opaque: a future backend can retain arrays on its device. Explicit
inspection methods provide canonical host views for debugging and comparisons;
they are not required inputs to a future device search loop.

The CPU backend wraps `CampaignAdapter` and its existing C++ environment. It
dispatches lanes sequentially and reports that fact. It reuses complete decision
keys, ordered legal menus and numerical inputs. Selection validation checks all
lane keys and choices before executing any lane. Native rule failures remain
atomic per lane; ordinary batch execution does not promise an expensive rollback
across lanes. Snapshot restoration and explicit-outcome conformance batches stage
replacements before committing the selected lanes together.

Use `scalar(lane)` when an existing tool requires the scalar environment API. A
retained scalar view follows that lane after restoration. Existing MCTS can use
this view, but this does not make its Python search batched or GPU accelerated.

```python
from studies.campaign.backends import create_backend
from studies.campaign.curriculum import make_env

backend = create_backend([make_env(1951, calendar_rounds=3),
                          make_env(1952, calendar_rounds=3)])
decisions = backend.decision_batch()
rows = backend.inspect_decisions(decisions)  # Explicit host inspection
```

CPU is the only registered campaign transition backend. Selecting `gpu` raises an explicit error.
The CPU path imports no optional GPU framework. Future neural-device selection
is separate from engine-backend selection. Neither menus nor state are truncated
to arbitrary fixed capacities.

`clone_for_search(seeds, lanes=...)` can fork one source lane repeatedly with
independent search seeds, without consuming the source game's execution RNG.
Repeated source lanes are allowed for this read-only operation; mutating batches
still require unique lanes.

## Chance and compatibility

`chance_request()` exposes the current public dice specification, without future
random values. `apply_chance_outcome(expected_key, faces)` validates the complete
decision key and every die face and required reroll, then applies ordinary rules
and history without advancing execution RNG. Normal `resolve_chance()` retains
its existing sampling behavior. Invalid outcomes and stale keys leave the lane
unchanged.

Explicit-outcome comparisons feed both implementations identical moves and dice.
They compare complete rule state, history, scheduler state, ordered legal choices,
acting factions and numerical inputs. Execution RNG is compared separately for
sampled execution; a matching seed alone is not a cross-device conformance proof.
The historical `Engine::replay` service still re-samples its chance events; this
new explicit-outcome seam does not silently change that service.

Nested backend Python sources now participate in training source fingerprints.
Ignored run archives do not. Existing experiments retain their frozen runtimes
and checkpoints; this branch does not rewrite or relabel their saved learners.

## Initial benchmarks

Run from the repository root, with a fresh output path:

```sh
.venv/bin/python tools/benchmark_campaign_backends.py \
  --backend cpu --mode positions --seeds 1951 \
  --repetitions 1 --warmups 1 --seconds 180 \
  --cpu-budget 3 --memory-bytes 8000000000 \
  --output studies/campaign/runs/backend-foundation/positions.json

.venv/bin/python tools/benchmark_campaign_backends.py \
  --backend cpu --mode scripted_games --seeds 1951 \
  --repetitions 1 --warmups 1 --seconds 180 \
  --cpu-budget 3 --memory-bytes 8000000000 \
  --output studies/campaign/runs/backend-foundation/scripted-games.json
```

Preparation records complete, real three-round games using the unchanged balanced
scripted policy. Both measured paths then replay the same selected actions and
explicit chance outcomes. Fixed-position cases include the opening, the first
chance request, and Japan's first- and second-round combat movement. The candidate
really calls the new batch wrapper; the reference calls the scalar adapter.

Reports separate preparation, warmup, operation timing and host audit/driver
overhead, and pin source/native hashes, settings and fixture witnesses. Completed
game throughput is reported only for genuine three-round terminals. Time,
transition, repeated-state and memory limits remain truncations or failures, with
no completed-throughput claim. The supervisor charges the complete owned process
tree using the larger of RSS and macOS physical footprint where available.

These are **audited rules-replay benchmarks**, not neural self-play, training,
playing strength or GPU measurements. They are an initial conformance baseline.
GPU measurements separately include device transfers/synchronization, cold
preparation, larger batch sizes and complete self-play under matched models and search budgets.
Component speedups will remain separate from complete-game training throughput.

## GPU neural execution

Long Apple GPU runs require PyTorch 2.13 or newer; the tested optional environment
pins 2.14.0. Keep it separate from the existing CPU environment:

```sh
.venv/bin/python -m venv tmp/gpu-mps-env
tmp/gpu-mps-env/bin/python -m pip install -r requirements-gpu-mps.txt
```

The native extension is shared and contains no Torch dependency. Build it with
the usual repository instructions. Use `tmp/gpu-mps-env/bin/python` for long MPS
commands; `.venv/bin/python` remains the CPU reference. Existing frozen training
experiments and their environment are not migrated.

Our varied-position probe reproduced native cache growth under 2.11 even after
clearing tensors and Python caches. PyTorch 2.13 added compilation-graph release
to public `torch.mps.empty_cache()` ([release notes](https://github.com/pytorch/pytorch/releases/tag/v2.13.0)).
The MPS runtime policy clears at completed inference/update boundaries, normally
every 32 actor forwards, without resetting weights, optimizer state, examples,
games or RNG. A learner shares one policy across successive evaluators. Its
resource counters are derived process state and reset their pending count after
restore; they are not learning checkpoint data. CPU and CUDA use no MPS policy.
Fast math and CPU fallback are rejected for long MPS execution.

`CampaignPolicyValueNet(config, device="mps")` executes the unchanged network on
the Apple GPU. `device="cuda"` or `"cuda:0"` selects an available NVIDIA/PyTorch
CUDA device; CUDA execution cannot be verified on the development Mac. The
default is `"cpu"`. All devices initialize their weights on CPU first, consuming
the same CPU random sequence, then move those weights. Menus, model dimensions,
precision, search budgets and game horizons are unchanged. Unavailable devices
and enabled MPS CPU fallback are errors; no device is silently substituted.

The training CLI accepts `--neural-device mps`; the saved configuration pins
that choice for recovery. Full recovery includes optimizer moments, frozen
policies, unfinished games and GPU random state. A CPU-storage round trip
restores optimizer moments to the model device. Changing devices is not an exact
learning resume. Weight-only exports are CPU tensors and can be evaluated on an
explicit different device with `evaluate --neural-device cpu`. Fully validating
a legacy recovery archive still requires its original device, even if its
policies are subsequently moved for evaluation.

Rules, interrupt scheduling and tree traversal remain on CPU in this hybrid
path. The neural evaluator batches each actor's network separately and returns
its policy/value outputs to CPU search. CPU/MPS float32 results require numerical
tolerances; matching initial weights and seeds alone do not guarantee identical
search choices near ties. Tests compare forward outputs, gradients, Adam updates,
actor routing, frozen-policy caches and real recovery behavior.

`tools/benchmark_campaign_devices.py` compares matched CPU/MPS neural inference
and completed hybrid self-play. Its reports distinguish preparation, cold and
warm execution, numerical differences, actual inference batch sizes, synchronized
network time and the remaining search/rules time. Fresh identical current
weights are used, with no relabeling of historical learned checkpoints.

The GPU path packs complete graph topology on CPU and uploads combined arrays,
then gathers external learned vectors in one indexed operation. It preserves
distinct encoded objects even when they share source graphs. Its four policy
factor heads operate on disjoint groups across all rows of an actor batch.
CPU execution retains its original operation order. These are execution changes,
not smaller legal menus or a different network architecture.

`tools/benchmark_campaign_device_updates.py` measures the actual three-policy
learning update with unchanged minibatch size 32, 16 epochs, and the 16-dimensional
one-layer model. It prepares a fresh genuine three-round game outside the timer,
retains every numerical menu, and labels positions only from its terminal result.
Policy targets come from the unchanged balanced baseline, so this measures a
supervised update workload rather than MCTS learning strength. CPU/MPS workers
use identical initial weights, fixture bytes and observed sampled minibatch order.

## First tensor rules component

`studies/campaign/backends/tensor_rules.py` implements the native dice
`effectiveResults` contract with integer tensors on CPU/MPS/CUDA. It validates
complete explicit face paths, conditional rerolls, ranges/counts and modified
result overflow. Device error masks remain on device until explicitly inspected.
Padding follows the actual batch maxima and counts; no die, reroll or lane is
silently truncated. Packing and host inspection are explicit separate operations.

This primitive samples no randomness and does not mutate a game. Full native
chance handlers still commit casualties, retreats, political effects and pending
decisions on CPU. The primitive is tested against authoritative native C++ and
bit-exact CPU/MPS output; it is not inserted into the CPU trainer merely to count
a GPU call. A separately named native benchmark probe times the existing C++
primitive after parsing, allowing an honest component comparison.

`effective_results_metal(batch)` is an explicit, fused Apple Metal implementation
of the same integer contract. It uses one dispatch, caches only compiled code and
small shape buffers, and requires contiguous MPS input. Portable CPU/CUDA/MPS
tensor execution remains the default. The benchmark compares both implementations
and reports Metal compilation/first-call costs separately from resident execution.

## State-backed income calculation

`backends/income_kernel.py` also ports the complete territorial-IPP and income
calculation to integer tensors. `gwrl_cpp.capture_campaign_income(...)` exports
two contiguous native buffers with a shared, immutable indexed context; no
game-state JSON or per-field Python parsing is involved. The context transfers
once, and changing ownership, city damage, treasury presence, power status,
surrender and capital control transfer in bulk. National identities remain
distinct, including Mongolia and Dadao.

Tests cover zero versus absent treasury, empty versus populated component maps,
capital loss, the six exact Japan bonus zones, signed division, lazy errors,
read-only capture and full state/RNG preservation. Native signed-int overflow is
reported explicitly rather than assigned a wrapping rule. Low-level tensor
computation consumes the native int32 input domain represented in int64 buffers;
it does not promise arithmetic on arbitrary fabricated int64 extremes.

The income benchmark separates existing C++ calculation, native capture,
upload, resident calculation and inspection. This component calculates income;
collecting treasury, advancing phases and other transitions remain in the CPU
engine.

## Remaining transition work

The Apple port now has a privileged lossless resident state substrate in
`backends/device_state.py`. Direct C++ field visitors export every mutable
native state field and all RNG/tape data into tagged integer records, preserving
double/uint64 bits without MPS float64. Frozen definition/catalog data and interned
strings are shared. Device gathers and snapshots retain complete histories,
decisions and continuations; they are ordinary clones, not yet search reseeds.
These buffers must never be passed to policy/observation encoders.

`backends/random_metal.py` samples native SplitMix64 streams on device, preserving
rejection sampling, die/reroll order, all three streams, test-tape behavior and
failure rollback. It returns the full outcome and next RNG state; combat/political
effects still require their handlers. `backends/income_ledger.py` performs exact
out-of-place income refresh/collection accounting, including payment-once and
overflow checks. It does not run placement, surrender hooks or advance the clock.
`backends/device_scheduler.py` performs the adapter's declaration-offer pass
entirely on resident metadata, retaining every ordered raw menu choice; declaration
execution is not yet ported. None is registered as a complete campaign backend.

Lossless integer transport has a measured startup gate: the original PyTorch 2.11
MPS `index_select` rounds large int64 words, including RNG/hash bits. CPU remains
supported there; the tested isolated 2.14 GPU environment passes exact sentinel
checks. Unsupported GPU integer runtimes fail explicitly. The cached probe runs
at initialization, never inside each fork. Included native binding sources also
participate in source fingerprints and extension rebuild dependencies. Bulk
capture pins Python owners before releasing the GIL and locking each environment.

Further engine ports must retain complete state, legal menus, pending choices,
interrupt ownership and chance distributions on device, using this CPU reference
and explicit outcomes for conformance. A kernel-level speedup alone does not
establish a complete-game speedup. Device search also needs to avoid a host trip
for every lane and every tree step.

The CPU implementation remains the default, reference and fallback as GPU support
is added. Share scenario/catalog data and conformance fixtures rather than keeping
independent copies of the campaign rules data.
