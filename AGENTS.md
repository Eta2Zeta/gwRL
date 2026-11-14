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
- Preserve every legal choice, game rule and dice distribution when optimizing.
  Do not silently reduce search budgets, model size or game horizons to report a
  speedup, or score unfinished games as terminal. Distinguish algorithm changes
  from implementation optimizations and verify each with appropriate correctness
  checks and before/after measurements.
- All runs so far are experiments, not production. New methods need not
  reproduce earlier runs, resume earlier checkpoints or keep superseded modes;
  replace them rather than maintaining compatibility. Match game behavior (legal
  choices and resulting states for the same position and dice), never internal
  byte formats. Identical results are a cheap check for speed-only changes, not
  a design constraint; a faster method may change float rounding or randomness.
- Respect the current user allowance of at most 12 CPU cores and 30,000,000,000
  bytes of memory, including worker/coordinator overhead, until the user changes
  it. Efficient code does not by itself establish that AlphaZero-style search is
  the best learning method or that this campaign can train to useful strength on
  the available hardware; keep those claims subject to measured evaluation.

## Documentation

- The documentation describes the program as it is now. `docs/README.md` is its
  starting point and says what to read for each purpose: `docs/design/` for how
  learning works, `docs/engine/` for how the rules engine works, by subject,
  `docs/rules/` for which rules are implemented and where the data comes from,
  and the guides beside the code they describe.
- When a change alters what a page describes, update that page in the same
  commit. Never describe a change in a new page instead. The reason for a
  choice that still holds belongs in the page that describes it; how the change
  came about belongs in the commit message.
- History lives in git and in `docs/archive/`. No current page may need the
  archive to be understood. Write a dated record in `docs/archive/records/` only
  for a measurement or an experiment someone may want to check again, such as a
  speed comparison or a training result: one short page with the setup, the
  numbers and what they do and do not show, beside its data file, plus a line in
  the archive's index. A current page cites a record as evidence for a number,
  never as the explanation of how something works.
- Test counts, random-game tallies and other check results go in the commit
  message, not in a document. A settled rules question goes in
  `game_content/rules/clarifications.md` and in the page of the rule it changes.
- Outside `docs/archive/`, name no file or folder after a date, a milestone or a
  stage. `tests/test_documentation.py` checks this, every relative link, and
  every document the data or the code cites.
- `docs/design/README.md` is the central design document of the learning
  system: the game interface, search, the network's input, the network,
  training, runs, evaluation and their data structures. It builds the design up
  from its bricks, in plain words for a reader who knows basic reinforcement
  learning but not this project: every part is defined, with a diagram or a real
  example from the engine (decision 612 is the running one), before any later
  part uses it, and the last sections assemble the whole training loop. A
  mention of a later part must point ahead explicitly. Details a first reading
  can skip go in a section's closing "More detail" part.
- When the user asks how or why something works, put the explanation in the
  page that covers it (the design document for learning, the engine pages for
  the rules engine), then answer in chat briefly with a link to the section. Do
  not leave an explanation only in chat.
- When a question digs into a detail of an existing explanation, revise that
  section in place: rewrite, merge or reorganize it so the document stays
  layered and readable, instead of appending another layer of explanation.
- Verify statements against the code and say what is measured, what is inferred
  and what is open.
- Never draw a diagram, table or formula in plain text, in any document. Draw
  diagrams as SVG figures in `docs/design/figures/` (tracked despite the image
  ignore rule), with a title, a description and alt text, and look at them
  rendered before committing. Write tables as Markdown tables and formulas as
  math. Code blocks are for commands and code only.
- GitHub reads Markdown before maths: `\,` and other backslash-punctuation lose
  their backslash, `&` is mangled, and a formula line starting with `+`, `-` or
  `=` becomes a list or heading. Avoid them, and check new formulas through
  GitHub's Markdown API (`gh api markdown`, mode `gfm`) before committing.

## References

For STEM questions, especially mathematics and physics, first look for references
in `/Users/home/Documents/Education/Library/Books/Textbooks`. If those are insufficient,
then look online for papers and notes.
