# Multi-agent API and stochastic search

The [architecture](../architecture.md) describes how search feeds self-play and
learning. The authoritative implementation is
[VectorMCTS](../../studies/shared/multiplayer_mcts.py), with declaration scheduling
in [CampaignAdapter](../../studies/shared/campaign_adapter.py). This is finite-budget
three-player search; its correctness checks do not establish strategic strength
or an equilibrium solution.

## Player choices, chance and observations

`CampaignEnv` exposes the actual decision owner, decision kind, legal actions,
explicit chance, terminal returns, clones and checkpoints separately.
`apply_action` does not roll dice or automatically play another nation.
`resolve_chance` is valid only at a chance node. Reaction owners can differ from
the nation whose calendar turn is active. Chance and terminal states have no
policy decision owner.

`CampaignAdapter` adds explicit declaration offers and passes around ordinary
decisions. The offer order is a versioned engine convention; printed declaration
priority still applies in the native rules. Passed/offered opportunities are
checkpointed and included in planning identity. Search rejects a raw environment
that would hide an available declaration interrupt.

Observations retain units, facilities, rails and projects; relationships and
accounts; routes, origins, damage and commitments; and pending reactions.
`context()` supplies geography, faction identities, Home Country membership and
catalog/rule registries. Complete numerical inputs reuse native exports and
bounded immutable/decision caches. Neither input path gives the model execution
RNG, future test dice or audit history. See the [engine reference](engine.md) for
the distinction between observable, planning and exact recovery state.

## Search contract

An evaluator supplies one finite nonnegative prior per legal action and a finite
three-component value vector in **Axis, Allies, Comintern** order. Action identities
are stable and unique; menu order is not an action's identity. The default
`UniformEvaluator` is untrained and returns uniform priors and zero values.

The owner of a choice maximizes its own component using PUCT, with optimistic
first-play urgency and inspectable action scores. Values stay as vectors during
backup; they are not negated as though this were alternating two-player zero-sum
play. Rule-defined chance samples independent search streams and retains multiple
possible successor states.

Each simulation starts from a search clone. Depth counts action or chance
transitions, not rounds or complete games. Search can stop at a new leaf, terminal,
cycle or depth limit. A nonterminal cutoff uses the frozen evaluator estimate;
it is never reported as an observed terminal result. Chance cutoffs require a
value evaluation rather than treating their placeholder value as a true zero.

Transpositions/root reuse require the exact planning state plus matching rules,
evaluator version, opponent mode/version, target player and depth cap. Root
Dirichlet noise is opt-in and local to that search opportunity; it is not retained
as an internal node's policy. Model updates require a new evaluator identity or
invalidated search state.

In multiplayer self-play each entitled player optimizes its own component.
Fixed-opponent mode instead uses one versioned `OpponentPolicy` in both search and
actual opponent play through `apply_fixed_opponent`; it does not select chance
outcomes. Evaluation comparisons must keep that deployed opponent behavior fixed.

The [approved scenario objective](scenario.md) supplies terminal wealth-gap
returns, with zero intermediate rewards. Network scaling is reversed before
search uses values. Snapshot wealth at a runtime truncation remains separate from
an actual terminal return.

## Batching and operational use

[Batched inference](../../studies/campaign/batching.py) coordinates independent
game searches. Each worker owns its tree and random state; simulations inside one
search stay sequential. Ready roots share inference requests, and only the
calling thread invokes the evaluator. Errors/cancellation release waiting roots.
Selecting an MPS neural device does not move the rules engine or tree traversal
to the GPU; see the [GPU guide](../gpu/README.md).

For training, resume and evaluation commands use the
[campaign workflow](../../studies/campaign/README.md). For current measurements and
learning limits use [learning status](../learning.md).

Verification covers [exact/stochastic search oracles](../../tests/test_multiplayer_mcts.py),
[declaration scheduling](../../tests/test_campaign_adapter.py),
[batch coordination](../../tests/test_campaign_batching.py) and
[actual environment behavior](../../tests/test_campaign_env.py). Original delivery
results are indexed in the [milestone archive](../archive/milestones/README.md).
