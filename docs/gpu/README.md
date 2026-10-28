# Campaign CPU and GPU execution

Current as of 28 October 2026.

**The C++ CPU engine runs all campaign rules and search.** The neural network can
optionally run on an Apple GPU through PyTorch MPS, while rules and tree search
stay on the CPU. CPU execution remains the default and the reference.

| Area | Status |
| --- | --- |
| CPU campaign | Complete rules, legal choices, chance, search, training and recovery. |
| GPU network | `--neural-device mps` for self-play, learner updates and evaluation, in an optional pinned environment. Slower than CPU at current batch sizes (below). |
| Multi-game interface | [`studies/campaign/backends/`](../../studies/campaign/backends/): independent game lanes with bulk decision, action, chance, numerical-input, clone and snapshot operations. Only the CPU backend exists, and self-play does not use it yet. |
| Explicit dice outcomes | `Engine::applyChanceOutcome` and backend `apply_chance_outcome(expected_key, faces)` apply chosen dice without consuming execution RNG, for conformance tests. |

## Measured result

The [26 October matched test](gpu_backend_2026_10_26_results.md) completed the same
four three-round games twice: seeds 1951–1954, 16 simulations, depth cap 16,
16-wide one-layer networks and fixed fresh weights.

| Execution | Four games | Network preparation and forward |
| --- | ---: | ---: |
| CPU rules, search and network | 295 s | 70 s |
| CPU rules and search, MPS network | 401 s | 144 s |

The GPU network was 36% slower. Network calls carried one to four positions,
1.7 on average, and 52% carried one. Four games run at once, each search asks
for one position at a time, and each alliance has its own network. Rules and
search outside the evaluator took 187 s on CPU, so even a network that cost
nothing would make this workload at most about 1.3 times faster.

A GPU network can pay off when the network is a large share of an all-CPU run,
as with a larger model, and each call carries many positions from more
simultaneous games. That comparison has not been measured.

## Archived Metal rules port

`codex/gpu-selfplay`, tagged `archive/gpu-rules-port-2026-10-27`, also ported
parts of the rules to Metal: politics, income, recruitment, scoring and dice,
plus byte-exact JSON and SHA-256 state identities. It cannot run complete games
or search, because movement, combat, legal-move generation and the search loop
were not ported. Its best result was one recruitment step at 512 simultaneous
positions: 87 ms versus 154 ms for ten native CPU workers. It was 48 times
slower than one CPU worker for a single position, and the CPU control scaled
only 2.5 times over serial. The port is not carried forward. Its code and dated
reports remain on that tag.

## GPU environment

Run from the repository root. Keep the optional environment separate from the
CPU `.venv`:

```sh
.venv/bin/python -m venv tmp/gpu-mps-env
tmp/gpu-mps-env/bin/python -m pip install -r requirements-gpu-mps.txt
tmp/gpu-mps-env/bin/python -m studies.campaign.run train --help
```

The tested runtime is PyTorch 2.14.0. Long MPS runs require 2.13 or newer for
graph-cache release. Unsupported runtimes, fast math and MPS CPU fallback are
explicit errors. Caches are cleared at completed inference or update
boundaries, normally every 32 actor forwards, without changing learning or game
state. CUDA can be selected but has not been tested. Float32 device differences
need numerical tolerances and can change search choices near ties.

## Multi-game interface

```python
from studies.campaign.backends import create_backend
from studies.campaign.curriculum import make_env

backend = create_backend([make_env(1951, calendar_rounds=3),
                          make_env(1952, calendar_rounds=3)])
decisions = backend.decision_batch()
rows = backend.inspect_decisions(decisions)  # Explicit host inspection
```

The CPU backend wraps `CampaignAdapter`, dispatches lanes sequentially and
reuses complete decision keys, ordered legal menus and numerical inputs.
Selection validation checks every lane before executing any. `scalar(lane)`
returns the scalar environment for existing tools; using it in MCTS does not
batch the search. `clone_for_search(seeds, lanes=...)` forks a lane with
independent search seeds without consuming its execution RNG.

`chance_request()` exposes the current dice specification without future random
values. `apply_chance_outcome(expected_key, faces)` validates the decision key,
faces and required rerolls, then applies ordinary rules and history. Invalid
outcomes and stale keys leave the lane unchanged. The
[initial conformance evidence](cpu_foundation_2026_10_25.md) records the
validated interface and its limits.

## Benchmarks

Use fresh output paths under ignored run storage:

```sh
.venv/bin/python tools/benchmark_campaign_backends.py \
  --backend cpu --mode positions --seeds 1951 \
  --repetitions 1 --warmups 1 --seconds 180 \
  --cpu-budget 3 --memory-bytes 8000000000 \
  --output studies/campaign/runs/backend-foundation/positions.json
```

Neural device comparisons use
[`benchmark_campaign_devices.py`](../../tools/benchmark_campaign_devices.py) and
[`benchmark_campaign_device_updates.py`](../../tools/benchmark_campaign_device_updates.py);
each tool's `--help` lists its options. Report preparation, transfers,
synchronized execution and auditing separately. Count only genuine terminal
games as completed throughput.

## Next work

- Profile CPU rules and search, the largest measured cost.
- Run more games at once so network calls carry more positions, after checking
  CPU scaling.
- Compare a larger model on CPU and MPS under equal games, search budgets and
  resource limits.
