# Complete resident recruitment-choice Engine actions

`ResidentRecruitmentChoiceAction.apply` now connects stored recruitment options
to the complete supported Engine action: authoritative source identity and
pending-option checks, cached-menu rule effects, income refresh, optional
TrainingRules reset/screening, output validation, exact State/Engine identities
and the original full Action Event. Records and the shared string pool publish
together. Every failed selected operation preserves the source for an exact retry.
Menus are not regenerated inside execution; action IDs, decision references and
parameter words come from the original stored Action.

The new output validator checks the exact changed footprint from a validated
source. It covers movement, identity collisions, construction, repair targets,
controllers, pending decisions/options, battles and surrender chance. Catalog
inventory is prepared once; statistics are not recomputed. Checked rule writers
preserve unrelated history and snapshots, avoiding another full history scan.
The outer action checks unchanged Clock, terminal and private RNG. The shared
screening hook was mechanically extracted with its previous method retained as
a thin delegation; its shader and behavior are unchanged.

Known unsupported cases return explicit capability rollback: actually reached
naval-force completion, preserved nonempty visited configurations in unwrapped
CoreRules, undefined native recursive controller cycles, and roll entries routed
to this choice-specific service. None is silently removed from the legal menu
or accepted as a complete transition. The CPU remains the only registered full
campaign backend; full GPU games and GPU MCTS are unfinished.

All fifteen output-validator methods passed together in 34.236 s (35.736 s
guarded), peaking at 3,798,900,224 charged bytes. Review caught an erased project
key reinserted as an award with a different type; its catalog type is now checked.
Controller-cycle diagnostics also distinguish cycles from ordinary playerless
states using existing relationship metadata, without calling undefined native
recursion. Initial fixture calls missing a selected mask were corrected.

All fourteen distinct outer-action methods passed: nine unaffected methods in
the first run and five final-validator methods in a focused 28.273 s rerun
(29.596 s guarded; peak 3,852,344,832 bytes). The existing chance-screening case
also passed after extraction. Initial extra assertions assumed a negative-zero
sentinel survived fixture serialization and that final Event storage must exceed
peak intermediate storage. Those fixtures/assertions were corrected after raw
native comparisons had already passed; transaction behavior did not change.

Comparisons include full native State/history/Event/RNG/keys, chronological
resident chance-to-choice, evolution/surrender, all four work types, stale keys,
late validation failures, exact allocation retries and no hot host/native/menu
fallback. GPU checks used two CPU threads and include a full 3 GB MPS reservation
in their memory charge; correctness timings are not throughput measurements.
The diagnostic Engine oracle calls the original Engine.step on a typed clone.
Native SHA-256 is `8419a7614b06cc9df155b236906418f7adef64f069f09e1d4fc6a2d032d3fa15`,
with before/after build-input hashes and atomic installation recorded.

Twenty-eight existing CPU backend, native parity and source-provenance checks
also passed in 32.241 s, using two CPU threads and 693,944,320 peak bytes without
GPU allocation. No learning run, model, search budget, game horizon or historical
checkpoint was changed.
