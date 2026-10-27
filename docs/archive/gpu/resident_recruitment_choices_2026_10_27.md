# Resident recruitment placement and free work

`ResidentRecruitmentChoice.apply` executes a stored recruitment decision option
against the complete current menu cached for that exact State. It does not
regenerate the menu for execution. It preserves the stored Action, continuation,
beneficiary and current eligibility checks before popping the decision and
erasing its continuation.

The four effects match the original helper: one infantry; two militia through
two ordered creation calls, including split zones; removal of one remaining ship
payment and one queue position; or zero facility damage and cancellation of all
repair jobs targeting it. Free ship work preserves paid IPP and treasury and
does not place a ship. Existing completion flags are retained. Full political
refresh then runs exactly once. Income, outer Engine validation, Events, training
hooks, calendar and RNG remain separate.

Explicit shared arenas cover every stage. Any selected failure restores the
complete original State and namespace, including failures after decision removal
or during the later refresh. The ephemeral cached menu is never substituted for
the original rollback namespace. Nonpolitical stored kinds return unhandled and
unchanged. Public roll-dispatch entries are explicitly unsupported by this choice
helper and are excluded from its native-oracle parity claim.

All twelve methods passed raw native State/RNG comparisons, generic-JSON mismatch
cases, stale menu/eligibility checks, paid amounts, repair cancellation, ordered
militia counter/Catalog behavior, allocation retries, late rollback and hot-path
host/native/menu-regeneration traps. An initial run found incomplete per-lane
error attribution when another lane failed earlier; read-only validation was
made lane-local when a complete cache exists, while all mutation stages retain
global rollback. A test's optional-interface inspection was also corrected.
All twelve methods then passed together in 27.675 s (28.716 s guarded).

The check used two CPU threads and peaked at 3,834,256,896 charged bytes including
a 3 GB MPS reservation. The diagnostic binding calls the unchanged original public
rule on a typed clone. No CPU rule formula changed. Native build inputs were
hashed before/after compilation and installed atomically; binary SHA-256 is
`46d02ca54855535cc9d21907c010d97f23de7f1534ab6b42b4cb16052c0f7659`.
These are correctness results, not complete-game or training speed measurements.
