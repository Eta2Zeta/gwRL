# Repository instructions

## Version control

- Commit completed, validated work in coherent units and push it to the current
  branch's configured upstream before reporting that repository work is finished.
  The user expects commits and pushes as part of the normal workflow.
- Keep dependent code, data and tests together. Use descriptive commit subjects;
  do not accumulate several completed milestones as one uncommitted backlog.
- Inspect the working tree before staging. Stage explicit paths, review the
  staged diff and run the checks appropriate to the change. Preserve unrelated
  user changes and personal notes.
- Respect the existing ignore policy for local images, build products, caches
  and training scratch output. Never commit credentials or temporary files.
- Fetch before pushing and inspect upstream divergence. Preserve remote work;
  do not force-push, rewrite shared history or discard changes without an explicit
  user request.
- Report the commits, push status and verification results concisely.

## Training efficiency

- Treat rule correctness and efficient training as joint design requirements.
  Design engine, search and neural-input interfaces for repeated self-play and
  simulated actions from the start; passing functional tests alone does not
  establish that an implementation is practical for reinforcement learning.
- Reuse legal actions and observations for an unchanged complete decision state
  instead of regenerating them separately for selection, neural input and action
  validation. Retain an authoritative legality check for external or stale
  actions. Bound caches and invalidate them when relevant state, pending choices,
  declaration offers, acting faction or rules change; board positions alone are
  not sufficient cache identities. Model-derived results also require a matching
  model version and invalidation after weight updates.
- Avoid repeated serialization, parsing, graph construction and Python/C++
  transfers in frequently executed search steps. Reuse immutable scenario data,
  batch neural evaluations where useful, and choose compact interfaces. Move
  measured bottlenecks into compiled code when justified; changing languages
  without measuring is not an optimization plan.
- Measure representative search positions and completed self-play games before
  larger runs, including intended search budgets, later phases and model sizes.
  Compare matched workloads, wall time, completed-game throughput and peak memory;
  evaluate learning strength under equal compute budgets. Do not infer training
  feasibility from a tiny smoke run or from CPU utilization alone.
- Preserve every legal choice, rule/state field, dice distribution and exact
  replay behavior when optimizing. Do not silently reduce search budgets, model
  size or game horizons to report a speedup, or score unfinished games as terminal.
  Distinguish algorithm changes from implementation optimizations and verify each
  with appropriate correctness checks and before/after measurements.
- Respect the current user allowance of at most 12 CPU cores and 30,000,000,000
  bytes of memory, including worker/coordinator overhead, until the user changes
  it. Efficient code does not by itself establish that AlphaZero-style search is
  the best learning method or that this campaign can train to useful strength on
  the available hardware; keep those claims subject to measured evaluation.

## Documentation

- Keep `docs/README.md` as the current project guide, with the root README
  pointing to it. Update existing architecture, workflow and performance guides
  instead of appending experiment history to current instructions.
- Keep dated reports and curated JSON evidence together in `docs/archive/`, with
  provenance and preservation hashes. Routine validation belongs in the commit;
  create a report when an experiment or decision needs durable evidence.
- Preserve active scenario/catalog data, rule clarifications and coverage inputs
  at their established paths unless their consumers change with them. Follow the
  retention conventions in `docs/development.md` and run
  `./.venv/bin/python tools/check_documentation.py` after documentation changes.

## References

For STEM questions, especially mathematics and physics, first look for references
in `/Users/home/Documents/Education/Books/Textbooks`. If those are insufficient,
then look online for papers and notes.
