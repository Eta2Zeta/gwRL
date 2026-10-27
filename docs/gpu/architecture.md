# Execution architecture and use

For current capability status, read the [GPU overview](README.md). The source is
in [campaign backends](../../studies/campaign/backends/).

## CPU interface and selection

[`protocol.py`](../../studies/campaign/backends/protocol.py) defines independent
game lanes and bulk decision, action, chance, numerical-input, clone and snapshot
operations. A lane is one independent game state. Execution buffers are opaque;
explicit inspection creates host views for debugging and conformance.

```python
from studies.campaign.backends import create_backend
from studies.campaign.curriculum import make_env

backend = create_backend([make_env(1951, calendar_rounds=3),
                          make_env(1952, calendar_rounds=3)])
decisions = backend.decision_batch()
rows = backend.inspect_decisions(decisions)
```

Only `backend="cpu"` is registered. It wraps the existing CampaignAdapter/C++
engine and executes its lanes sequentially. `scalar(lane)` supplies the existing
scalar API, following that lane after restoration; using it in MCTS does not
create batched or GPU search. Neural-device selection is independent of engine
selection. CPU imports require no optional GPU framework.

The wrapper reuses complete decision keys, ordered legal menus and numerical
inputs for an unchanged decision. Batch selection checks all keys and options
before execution. Ordinary execution is atomic per lane; restoration and explicit
outcome conformance batches stage replacements before publishing selected lanes
together. No arbitrary fixed capacity truncates a menu or state.

## Resident Metal services

[`device_state.py`](../../studies/campaign/backends/device_state.py) captures all
mutable native fields and RNG/tape data into tagged integer records. Shared
scenario/catalog metadata and strings are prepared once. Binary64 and uint64
bits, complete histories, pending decisions and continuations remain lossless.
These buffers contain private execution data and must never become policy input.
Numerical observations use the separate public training interface.

Rule services compose checked edits, canonical State/Engine identities and Event
logging. Context fingerprints prevent mixing incompatible arenas or string
tables. Capacity errors report required sizes for an exact retry; failed
transactions preserve the source. Uncached noninteger canonical spellings and
unported rule services fail explicitly. Reference and parallel kernel variants
remain available for conformance and measured experiments; the policies selected
by a benchmark must be recorded rather than inferred from current defaults.

Current connected recruitment handlers are
[`ResidentRecruitmentAction`](../../studies/campaign/backends/resident_recruitment_action.py),
[`ResidentRecruitmentChance`](../../studies/campaign/backends/resident_recruitment_chance.py)
and [`ResidentRecruitmentChoiceAction`](../../studies/campaign/backends/resident_recruitment_choice_action.py).
Stored-choice execution reuses the original menu and Action parameters. Its
effects include complete internal political refresh, income refresh, optional
training screening, changed-output validation, identities and full Action Event
publication. Refresh updates tracked rates; treasury collection is a distinct
operation. Political queues retain actual decision owners and native ordering.
These handlers remain component APIs outside the full-backend registry.

## Chance, identity and compatibility

`chance_request()` exposes dice specifications without future random values.
`apply_chance_outcome(expected_key, faces)` validates the full key, faces and
required rerolls, applies ordinary rules/history and preserves execution RNG.
Normal sampled resolution retains its existing RNG behavior. Search clones reseed
only the search stream and remove test tape as native `cloneForSearch` does.

Conformance compares complete State, history, scheduler state, ordered choices,
acting factions, numerical inputs and identities. Sampled execution additionally
compares every RNG stream. Identical seeds alone do not prove equivalence.
Existing `Engine::replay` still re-samples its events.

Backend Python and native binding sources participate in training fingerprints.
Historical experiments retain frozen runtimes and checkpoints. A new wire context,
rule contract or neural device does not authorize retagging an existing arena or
claiming an exact learning resume. Training recovery includes optimizer, frozen
policies, unfinished games and random state; weight-only exports are a separate
operation. Backend snapshots preserve their selected game lanes.

## Apple GPU environment

Run from the repository root. Keep the optional pinned environment separate from
the CPU environment and build the native extension using the
[development instructions](../development.md).

```sh
.venv/bin/python -m venv tmp/gpu-mps-env
tmp/gpu-mps-env/bin/python -m pip install -r requirements-gpu-mps.txt
```

The tested optional runtime is PyTorch 2.14.0. Long MPS neural execution requires
2.13 or newer for graph-cache release; lossless integer transport also runs a
startup sentinel check. Unsupported runtimes, fast math and MPS CPU fallback are
explicit errors. The shared resource policy clears caches at completed inference
or update boundaries, normally every 32 actor forwards, preserving learning and
game state. CPU execution uses no MPS policy.

`CampaignPolicyValueNet(config, device="mps")` and CLI `--neural-device mps`
select Apple GPU neural work while rules and tree traversal stay on CPU. Weights
initialize on CPU before transfer. CUDA can be selected on available hardware,
but has not been verified on this Mac. Default execution is CPU. Float32 device
differences require numerical tolerances and can change search choices near ties.

## Bounded comparisons

Use fresh output paths under ignored run storage. These commands compare the
CPU scalar adapter and batch wrapper on audited rules replays, without MCTS or
learning; their results are distinct from self-play throughput.

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

The neural/device comparisons use
[`benchmark_campaign_devices.py`](../../tools/benchmark_campaign_devices.py)
and [`benchmark_campaign_device_updates.py`](../../tools/benchmark_campaign_device_updates.py).
Each tool's `--help` lists its current options. Reports must separate preparation,
compilation, transfers, synchronized execution and host auditing, and pin fixture,
source, native, environment and policy identities. Apply the repository's 12-core
and 30,000,000,000-byte aggregate limits, with one heavy job at a time. Completed
throughput requires genuine terminal games; guard stops remain truncations.
