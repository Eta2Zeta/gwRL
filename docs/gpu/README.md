# Campaign execution backends

GPU development starts on `codex/gpu-selfplay`, from CPU reference commit
`d1c672954d8e1bb24ca43cd98c0199f4daac81f7`. Both implementations will live in the
same repository. The existing C++ rules engine, scenario data and scalar CPU
training path remain in place. The shared interface, CPU wrapper and rules-replay
harness are joined by optional GPU neural execution, complete resident state/RNG
transport and several exact rules components.
**A full GPU campaign transition engine is not implemented.**

The [initial CPU conformance and timing evidence](cpu_foundation_2026_10_25.md)
records the validated foundation and its measurement limits.
The [GPU implementation and measured results](gpu_backend_2026_10_26_results.md)
separate completed self-play, neural updates and exact rules-component timings.
The [Apple state/sampling foundation results](metal_state_2026_10_26.md) record
the next complete-state and exact-RNG component measurements.
The [connected search-clone comparison](metal_connected_clone_2026_10_26.md)
records the exact generic and fused Metal paths, including their scope limits.
The [resident political-query results](metal_political_queries_2026_10_26.md)
compare the complete native and GPU permission matrices at several batch sizes.
The [cooperative-query follow-up](metal_political_queries_parallel_2026_10_26.md)
records the later parallel kernel and its remaining small-batch limits.
The [supplied-route measurements](metal_routes_2026_10_26.md) include fresh
preparation, reused views and the actual legal/rejected-path coverage.
The [combined-preparation comparison](metal_route_preparation_2026_10_26.md)
records the later one-dispatch implementation and its small-batch limits.
The separate [income-rate correction](income_refresh_correction_2026_10_26.md)
versions a CPU correctness fix discovered while connecting GPU chance effects;
it is not counted as an optimization or applied to historical checkpoints.
The [terminal-score arithmetic checks](metal_score_arithmetic_2026_10_26.md)
cover native binary64 score bits and once-rounded training targets on Metal.
The [indexed-preparation measurements](metal_indexed_preparation_2026_10_26.md)
record the later parallel presence/declaration path and its remaining limits.
The [recruitment Engine transactions](resident_recruitment_transactions_2026_10_26.md)
connect action, chance, history and RNG while documenting the unported naval hook.
The [complete-step smoke measurements](metal_recruitment_smoke_2026_10_26.md)
expose identity/bookkeeping overhead and introduce parallel CPU diagnostic probes.
The [identity substage profile](metal_identity_profile_2026_10_26.md) separates
the measured State formatting and hashing costs inside those complete operations.
The [exact identity optimization measurements](metal_identity_optimizations_2026_10_26.md)
compare parallel unit formatting and scalar SHA kernels, including group sizing.
The [whole-field formatting experiment](metal_field_json_experiment_2026_10_26.md)
records a later correct alternative that did not demonstrate an additional gain.
The [complete-step comparison](metal_recruitment_step_optimizations_2026_10_26.md)
records both identity gains and the remaining losses against a parallel CPU.
The [political unit effects](resident_political_unit_effects_2026_10_26.md) cover
movement refresh, cargo removal and creation with direct raw native oracles.
The [surrender effects](resident_political_surrender_2026_10_26.md) retain complete
controller, cargo, naval-queue and objective-award behavior.
The [parallel arena-copy comparison](metal_editor_copy_2026_10_26.md) separates
remaining builder costs from measured complete-step improvements and CPU losses.
The [combined copy/validation comparison](metal_container_factorial_2026_10_27.md)
measures both improvements independently and together against serial and parallel
native execution on complete supported recruitment steps.
The [political queue and truce checks](resident_political_queues_2026_10_27.md)
cover exact evolution choices, controlling-player lookup and mandatory battle
queuing, without claiming complete political refresh or combat resolution.
The [political facts checks](resident_political_facts_2026_10_27.md) cover possession
IPP, civil flags, promotion, objectives and final alliances as separate seams.
The [sampled-RNG copy checks](resident_chance_random_copy_2026_10_27.md) retain
the full dice-commit contract while distributing its complete arena copy.
The [complete internal political refresh](resident_political_refresh_2026_10_27.md)
connects those political helpers in the original single-pass order, including
simultaneous evolution and surrender effects.

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

Resident Metal rules components now include source-bound political relation
matrices and the complete `mayDeclareWar(LandAttack)` predicate. Static faction,
map and Home Country metadata is uploaded once; changing control, truce, wars,
unit presence and permissions are read from the resident state. Native directed
queries, short-circuit errors and optional-player semantics are preserved.
Neither component applies a declaration or moves units.

Internal map/set/sequence builders preserve byte-ordered keys, unknown nested
payloads, optional absence and complete transaction rollback. Capacity failures
report required allocation sizes for retry. These are structural building blocks;
game-action legality still belongs to the actual rule handler.

`canonical_json_metal.py` writes native canonical bytes directly from resident
generic JSON subtrees, with exact string escaping and no search-step JSON/Python
conversion. Native ingress prepares an immutable cache of arbitrary binary64
number spellings once. New exact int32 values are recognized bitwise and formatted
on device; an uncached noninteger is an explicit error, never rounded or sent to
a CPU fallback. Digest errors include serialization failures, so unusable output
cannot silently become an action identity. `resident_state_json.py` now projects
every typed State field into the same native bytes and computes both the State
and outer Engine planning keys on device. History and RNG are excluded from those
keys exactly as on CPU; neither operation retains historical State copies.

`ResidentIncomeContext.refresh` now updates income components in every phase
without collecting cash or changing the clock, history or RNG. Its returned
allocation stays fixed by default; insufficient capacity is an explicit retry,
so frequent refreshes do not accumulate padding. Placement accounting remains
a separate operation. These helpers do not advance phases or apply political
hooks. The static movement context and original route oracle prepare full map,
terrain, rail, crossing and unit-class data once for the resident route port.

Resident catalog-stat queries now cover every primary unit/damage state and all
nine optional/dice statistics. Static base values, technology modifiers and flag
requirements are prepared once. Current technology completion, flag precedence,
major-power status and Home Country predicates are resolved from resident state,
with original lazy errors and explicit inventory capacity retries.

`resident_action_ids.py` composes all native action-ID families and the scheduler
wrappers from resident bytes and canonical parameter digests. It preserves the
original family-specific digest lengths and action order; it does not generate
or validate a legal menu. Political queries additionally expose a cooperative
`implementation="parallel"` path, now selected by default after matched timings
and exact native/reference comparisons. The reference remains explicitly selectable.

The read-only resident route service now covers ordinary movement, blitz,
strategic rail/river, narrow crossings and towing. It retains every RouteResult
field and native failure order. Static map/catalog data is prepared once, and
unchanged-source indexes and political results can be reused across candidate
paths. Route validation is separate from enumerating a legal menu and executing
its movement, capture, battle and political effects.

Resident recruitment services produce the native ordered choices and full
Action records, including split militia pairs, ship work and facility repairs.
They preserve original eligibility/threshold/zone distinctions and do not add an
influence-garrison condition. Menu/parameter/string capacities are explicit and
retryable; default menu allocation depends on geography rather than accumulated
State/history padding. Separate recruitment-start and sampled-roll transactions
now connect rule effects, income refresh, exact Event/RNG and atomic publication.
Execution of recruitment placement, ship-work and repair choices remains separate;
the transaction report identifies the unported naval-completion hook explicitly.

Audit-event append now commits generic payloads, the native State hash and string
interning under one rollback flag. It preserves all history and raw binary64
payload bits, including negative zero, without retaining historical State copies.
Chance I/O builds the exact full face/reroll payload and installs sampled streams
only if the original random subtree is still unchanged. Native chance parity
tests currently supply rule effects on CPU, then compare GPU payload/history/RNG;
they are not a complete GPU chance-handler claim. The separate training-order
reset hook clears only its original public metadata, with fixed allocation and
explicit capacity retry.

Adding fixed handler strings changes the checked wire-context fingerprint.
Existing raw arenas cannot be retagged. CPU saved-game values and rule identities
are unchanged, and these privileged intern IDs remain excluded from model inputs.

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

The next connected layer uses `device_state_edits.py` for checked, out-of-place
record subtree changes, with explicit capacity errors and rollback. Shared wire
contexts carry their exact record/string fingerprint; mismatched prefixes are
rejected. `device_search_clone.py` preserves complete State bits, seeds only the
search stream and removes test tape exactly like native `cloneForSearch`.
`packed_chance_metal.py` reads the native pending dice/RNG directly on device and
returns an uncommitted outcome/next-RNG pair. `resident_state_income.py` reads and
updates the complete packed income ledger at its placement/accounting seam. It
does not apply placement, political hooks, phase advancement or action history.

Wire version 2 adds resident actual string/byte counts, separate from allocated
capacity. `device_strings.py` appends exact byte strings with deterministic
deduplication, copy-on-write pools, explicit capacity/overflow errors and optional
UTF8 validation. Integer prefix scans retain offsets above 2^24 exactly. Unused
pool storage and IDs are privileged transport data, never neural features.

The specialized search clone gathers state and replaces the final RNG record in
one element-parallel Metal dispatch; the tested generic composition remains
selectable as `implementation="reference"` for matched measurements.
`resident_wealth.py` calculates full asset/income components on device, including
native-order binary64 component rounding represented with integer half units.
Its rational twentieths are separately labeled; explicit host inspection applies
the original double-valued total/gap expression and is the native-value oracle.
`content_digest_metal.py` provides exact native SHA-256 action identity bytes
without decoding or normalizing strings on CPU.

Further engine ports must retain complete state, legal menus, pending choices,
interrupt ownership and chance distributions on device, using this CPU reference
and explicit outcomes for conformance. A kernel-level speedup alone does not
establish a complete-game speedup. Device search also needs to avoid a host trip
for every lane and every tree step.

The CPU implementation remains the default, reference and fallback as GPU support
is added. Share scenario/catalog data and conformance fixtures rather than keeping
independent copies of the campaign rules data.
