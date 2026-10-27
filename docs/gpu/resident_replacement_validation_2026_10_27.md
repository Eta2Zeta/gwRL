# Parallel replacement-tree validation

The explicit parallel editor/container combination now distributes replacement
grammar validation over nodes, using the existing exact per-node validator.
The original serial plan remains available with the reference container policy.
Both retain the same source, target, length, type, arity, capacity and section
checks. The new plan consults its validity result only where the original called
the serial tree validator, preserving lazy and combined error bits and required
allocation sizes. Copying and cohort publication are unchanged.

Validation is recomputed on every call. This introduces no trusted-producer
shortcut, cached result, host read or State-schema assumption. The temporary
replacement frame borrows the exact source context/pools and carries zero inherited
errors; source errors are still checked separately in their original position.
The generated plan differs only in its name, one read-only boolean input and the
tree predicate. A reversible source comparison checks that boundary. Its unused
scratch-stack inputs use fixed dummy buffers.

All 25 checks passed: eighteen inherited/new editor cases and seven independent
tree-validator cases. They compare rich, deep, random and malformed replacements,
lazy bad offsets/usage, zero capacities and batches, selected masks, raw padding,
all errors/required sizes and complete native action/chance transactions. Source
words remain unchanged and hot-path host reads are trapped. The suite took
40.674 s (41.617 s guarded), peaking at 4,781,188,264 charged bytes including a
3 GB MPS reservation, with two CPU threads. These are correctness results; a
matched whole-operation benchmark is still required before claiming a gain.
