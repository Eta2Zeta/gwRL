# Campaign execution backends

GPU development starts on `codex/gpu-selfplay`, from CPU reference commit
`d1c672954d8e1bb24ca43cd98c0199f4daac81f7`. Both implementations will live in the
same repository. The existing C++ rules engine, scenario data and scalar CPU
training path remain in place. This first step implements the shared interface,
CPU wrapper and correctness/benchmark harness. **No GPU backend is implemented.**

The [initial CPU conformance and timing evidence](cpu_foundation_2026_10_25.md)
records the validated foundation and its measurement limits.

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

CPU is the only registered backend. Selecting `gpu` raises an explicit error.
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
Future GPU work must also measure device transfers/synchronization, compilation,
larger batch sizes and complete self-play under matched models and search budgets.
Component speedups will remain separate from complete-game training throughput.

## Next additions

1. Measure GPU neural evaluation separately with the CPU engine retained.
2. Add a GPU backend behind this contract, including device execution of pending
   choices and interrupts; avoid a Python round trip for each individual lane.
3. Run common conformance fixtures with explicit outcomes before speed comparisons.
4. Extend the harness to real batched search and complete learning, recording
   engine, search and neural-device choices independently.

The CPU implementation remains the default, reference and fallback as GPU support
is added. Share scenario/catalog data and conformance fixtures rather than keeping
independent copies of the campaign rules data.
