# M12: campaign learning, evaluation and training operations

Status: operational exit gate complete, 23 October 2026. The final planned
milestone is delivered in three validated chunks: entity-graph models and batched
search; resumable parallel self-play; held-out evaluation, profiling and
foreground smoke. All 212 Python tests and 24 C++ suites pass. No new rule decision
was needed, and no large or background training experiment was launched.

The campaign neural model traverses every observation/context/action JSON field.
Its graph retains hierarchy, entity/registry references and map adjacency; finite
hashed lexical embeddings are an approximation, with no unknown-field or action
truncation. The policy readout factors families, sources/groups, paths and targets
while scoring the exact authoritative legal menu. It does not change movement
commitments or treat units with different statuses as interchangeable.

Each actor has a separate network with an unbounded three-component value head.
Network values use raw wealth-gap units divided by the configured positive scale
(default 100); inference restores raw units before search. Chance cutoffs average
the three value heads, and true terminals use exact engine returns. Intermediate
rewards are zero, with gamma 1 and no kill, purchase or phase-passing bonuses.

Independent search roots share actual neural inference batches. Each root retains
its own unchanged vector MCTS, explicit chance and entitled choices; results and
seeds remain associated with the correct root. Cancellation and evaluator/worker
errors release waiting roots. Static graph parsing can cache, while learned
context embeddings are recomputed on each forward and never survive an update.

`CampaignEnv.curriculum(path, calendar_rounds, seed)` uses the same rules and
approved 99-piece, 37-node initial setup with an explicitly shorter real calendar.
The new definition fingerprint and context record the changed horizon. Those
short tasks are not July 1941 campaign results. The normal constructor preserves
the original eleven-round target. An execution budget is a separate truncation,
with bootstrap provenance rather than an invented terminal outcome.

The initial correctness checks cover 11 neural tests, 11 batched-search tests,
two actual-engine curriculum tests and three existing C++ foundation suites.
The learner adds 15 tests for raw terminal/bootstrap targets, actor routing,
real graph gradients and exact multi-root continuation with populated optimizer
state, replay and random generators. Six action-driven C++ accounting groups
cover paid queues, opening ships, bombing/repair, capture, recruitment/alignment
and phase passing. See `learning_verification_2026_10_23.json`. The actual CLI tests deliver SIGINT
after flushed progress and stop after an update with populated Adam state. Both continuations match an uninterrupted
run exactly: weights, optimizer, replay, pending samples, both game states,
scheduler, all RNG and runner metadata. Source/configuration changes and occupied
output directories reject without changing existing files.

The retained foreground smoke uses two games and two small-model training
batches: 24 real transitions, 21 decisions, three dice events and two updates in
14.30 seconds across stop/resume. All three networks change. Its 21 training
samples are explicitly bootstrap targets; no learned episode reached terminal.
Policy samples belong to Allies/Comintern in this short opening segment; the
three-actor routing checks and complete scripted games cover Axis choices too.
Actual inference batches include 27 batches of two requests and nine singletons.

Held-out seeds 1009/1013 are disjoint from the base seed and both logged training
episode seeds. Each learned actor is searched against the same deployed fixed
opponent version; all six games stop at their explicit 40-transition budget.
They have no observed terminal return or calibration claim. Two scripted control
games genuinely finish the one-round task in 254/250 transitions. The reports
retain raw wealth components, territory, casualties, actor counts and completed
versus truncated statistics; small approximate intervals do not establish strength.

The retained-state CPU profile (one thread, two distinct entitled actors, menus
of two) measures clone about 1.48ms, legal actions 1.51ms, observation 5.42ms,
context 8.16ms and a cloned rule transition 4.63ms on average. Two-actor batched
inference does not show a speed gain here. A separate default 1,137,928-parameter
model profile with one common actor measures median inference batches of
1/2/4/8 at 136/175/247/403ms, about 136/88/62/50ms per request. Source parsing and
warm samples are retained. Both profiles verify unchanged live state and RNG;
large menus, later phases and accelerator behavior need separate measurement.

At the small smoke settings, 100 otherwise comparable batches would take roughly
12 minutes; changing positions, model size or search budget can change that
substantially. Measure a short pilot with the intended settings before a larger
foreground experiment. The initial curriculum varies real duration while keeping
the approved starting setup. Broader starting-position curricula, opponent
leagues and direct-policy/PPO comparison remain experimental follow-ups. This
operational gate does not establish a strong or converged policy.

- [Operations verification](operations_verification_2026_10_23.json)
- [Learned-policy held-out smoke](evaluation_smoke_2026_10_23.json)
- [Completed scripted controls](scripted_control_2026_10_23.json)
- [Retained-state profile](operation_profile_2026_10_23.json)
- [Default-model batch profile](default_model_profile_2026_10_23.json)
- [Foreground run, resume and monitoring commands](/Users/home/Desktop/gwRL/studies/campaign/README.md)
