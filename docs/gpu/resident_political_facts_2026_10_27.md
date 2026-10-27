# Exact resident political refresh facts

`ResidentPoliticalFacts` reproduces the native refresh blocks for possession IPP,
civil-war elimination, evolution marking, the One China objective and final ally
sets. Immutable geographic IPP/Home Country metadata and its lazy native errors
are prepared once. Changing ownership, city damage, units, status and relationships
are read from the complete resident State. Possession IPP is independent of income
collection and eligibility. Civil-war elimination counts every owned unit,
including carried units and crews. Promotion recomputes the threshold and retains
the original major/surrender skips, turn-counter checks and flags.

The CPU blocks were extracted into small helpers called in precisely their old
positions. Their formulas and downstream movement/truce/choice order are unchanged.
The GPU helpers do not independently run those downstream effects, surrender,
income, Events or randomness. Complete refresh is a separate composition.

All twelve focused cases passed on their first execution, comparing raw typed
native State and private RNG and preserving every namespace buffer. Coverage
includes 13-IPP/counter boundaries, lazy malformed-IPP messages, absent diagnostic
factions, the Home Country island exceptions, zero-IPP land, unrelated player
errors during ally rebuilding, explicit capacity retries and cohort rollback.
Hot-path host/native/JSON calls are trapped. Inputs outside native defined signed
integer arithmetic return an explicit overflow error; tests do not invoke C++
undefined arithmetic as an oracle.

The suite took 33.197 s (34.413 s guarded), using two CPU threads with a conservative
3,699,465,728-byte peak including a 3 GB MPS reservation. All 27 native suites passed
after the helper extraction and bindings in 39.84 s. These are correctness runs,
not throughput measurements. The native build records all source hashes before
and after compilation and installs atomically; its SHA-256 is
`61316df7ffdf4d94f0b6ccf1098092977ac9da45b3277218664f7cca18d4c2f7`.

Diagnostic IPP/absent-faction fixtures create fresh validated frozen definitions
and typed State while retaining original Rules and RNG. Production definitions
are untouched. Added handler strings participate in the wire fingerprint, so old
raw arenas cannot be retagged. The CPU remains the complete campaign reference.
