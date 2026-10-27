# M11: multi-agent environment and stochastic vector search

> Completed milestone reference. Test counts, timings and next steps below describe this delivery. Use the [project guide](../README.md) for current status and instructions.

**Status: correctness exit complete, 23 October 2026.** The adapter, wealth and
search checks pass alongside M10's two full campaign replays. Search correctness
on small exact fixtures does not establish full campaign playing strength.

`gwrl_cpp.CampaignEnv` exposes the complete shared engine. The actual decision
owner, decision kind, legal actions, declaration interrupts, explicit chance,
three-component terminal returns, cloning and checkpoints remain separate.
`apply_action` never rolls dice or automatically plays another nation's turn.
Use `resolve_chance` only at a chance node.

Observations retain dynamic unit/facility/rail/project entities, national
relationships and accounts, routes, origins, damage, commitments and pending
reactions. `context()` supplies the geography graph, canonical factions,
Home Country membership and complete catalog/rule registries. There is no fixed
five-unit encoding, execution RNG, future dice tape or history in model features.

`studies.shared.campaign_adapter.CampaignAdapter` adds explicit declaration
offers and passes around ordinary decisions. Its versioned offer order is an
engine convention; the C++ engine still applies the printed declaration-priority
reaction. Offered and passed opportunities are checkpointed and included in
planning identity. Search rejects a raw environment that would hide an available
interrupt.

`VectorMCTS` backs up `[Axis, Allies, Comintern]` values. Each player selects its
own component, with optimistic first-play urgency and inspectable PUCT terms.
Chance samples independent search streams and stores multiple successor states.
Root reuse requires the exact observed planning state and matching rules,
evaluator, opponent mode/version and rollout depth. Training root noise is
explicitly opt-in and remains local to that root.

Fixed-opponent search uses a versioned `OpponentPolicy`; actual play uses the
same sampler through `apply_fixed_opponent`. Multiplayer self-play instead lets
each entitled player optimize its own component. The existing scalar study
models, searches and historical weights are preserved.

The approved M0 wealth calculation supplies terminal returns: current legally
collectable income plus 0.1 times completed assets, treasury and paid queued
construction. City labels add zero; physical facilities and undirected rail
borders count once; rail ownership splits 50/50. Uncontrolled minors receive no
alliance attribution. Free ship repairs cause no invented damage discount,
negative facility values are retained, and prepaid repair credit requires the
asset's current owner. Intermediate returns are zero.

## Verification and use

The [search verification](../archive/milestones/m11/search_verification.json) records 16 exact-oracle,
stochastic, reaction, action-order, cache, RNG and interrupt-scheduler tests with
stated budgets and tolerances. Additional C++ and Python binding checks exercise
the actual 99-piece campaign and wealth accounting. The
[integrated verification](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m11/verification_2026_10_23.json)
records all 23 passing C++ suites and 156 Python tests. Both M10 traces restore
their initial and terminal checkpoints exactly through the Python API; terminal
wealth and all three returns match the exported results and approved formula.

Batched neural inference, model/action-generation profiling, further factorization
of large action menus and learned policy/value heads remain follow-ups with M12.
This milestone supplies the synchronous,
versioned evaluator interface, complete-state transpositions and exact observed
root reuse required to test those optimizations against a correct search.

```sh
./.venv/bin/python -m unittest discover -s tests -p 'test_multiplayer_mcts.py' -v
./.venv/bin/python -m unittest discover -s tests -p 'test_campaign_env.py' -v
```

```python
import gwrl_cpp
from studies.shared.campaign_adapter import CampaignAdapter
from studies.shared.multiplayer_mcts import MctsConfig, VectorMCTS

env = CampaignAdapter(gwrl_cpp.CampaignEnv("game_content/scenarios/japan_china_1936", 1936))
search = VectorMCTS(config=MctsConfig(simulations=4, max_depth=4, seed=7))
result = search.search(env)  # Default evaluator is untrained and returns zero values.
env.apply_action(result.best_action())
```

This example checks API wiring. Neural learning, held-out policy evaluation and
interruptible training operations belong to M12; no training run is launched.
