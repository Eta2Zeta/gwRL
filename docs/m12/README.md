# M12: campaign learning, evaluation and training operations

Status: implementation in progress, 23 October 2026. This final planned milestone
is delivered in three validated chunks: entity-graph models and batched search;
resumable parallel self-play; held-out evaluation, profiling and foreground smoke.
No large training experiment is started automatically.

The campaign neural model traverses every observation/context/action JSON field.
Its graph retains hierarchy, entity/registry references and map adjacency; finite
hashed lexical embeddings are an approximation, with no unknown-field or action
truncation. The policy readout factors families, sources/groups, paths and targets
while scoring the exact authoritative legal menu. It does not change movement
commitments or treat units with different statuses as interchangeable.

Each actor has a separate network with an unbounded three-component value head.
Network values use raw wealth-gap units divided by the configured positive scale
(default100); inference restores raw units before search. Chance cutoffs average
the three value heads, and true terminals use exact engine returns. Intermediate
rewards are zero, with gamma1 and no kill, purchase or phase-passing bonuses.

Independent search roots share actual neural inference batches. Each root retains
its own unchanged vector MCTS, explicit chance and entitled choices; results and
seeds remain associated with the correct root. Cancellation and evaluator/worker
errors release waiting roots. Static graph parsing can cache, while learned
context embeddings are recomputed on each forward and never survive an update.

`CampaignEnv.curriculum(path, calendar_rounds, seed)` uses the same rules and
approved 99-piece,37-node initial setup with an explicitly shorter real calendar.
The new definition fingerprint and context record the changed horizon. Those
short tasks are not July1941 campaign results. The normal constructor preserves
the original eleven-round target. An execution budget is a separate truncation,
with bootstrap provenance rather than an invented terminal outcome.

The initial correctness checks cover 11 neural tests, 11 batched-search tests,
two actual-engine curriculum tests and three existing C++ foundation suites.
Learning/resume and evaluation records will be added after their real foreground
smoke checks finish.
