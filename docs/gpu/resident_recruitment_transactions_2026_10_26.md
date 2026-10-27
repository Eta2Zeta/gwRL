# Resident recruitment Engine transactions

The Apple implementation now connects recruitment-roll start actions and sampled
recruitment results through their complete Engine transaction stages: rule
effects, corrected income-rate refresh, training metadata, unchanged calendar,
planning identities, exact Event payload/history and RNG preservation or commit.
It uses explicit fixed capacities and publishes all selected lanes and their
shared string namespace together. Failed attempts preserve their original
records, pool usage, pending draws and RNG for an exact retry.

Start actions reuse a complete source-bound legal recruitment menu and verify
its selected Action fields. They do not regenerate menus for execution. The
sampled-result handler uses the saved roll threshold, removes its continuation
before regenerating successful choices, and follows native ordering for IDs and
pending decisions. Successful and failed rolls retain all three random streams
and test-tape semantics. No hot-path JSON, CPU reads or native rule fallback is
used by either handler.

Both require the corrected income-refresh execution contract. Historical
checkpoints are not relabeled. Their input is a native-validated canonical State
or a resident State whose invariants have been preserved by checked writers;
these are not arbitrary-byte import validators.

## Validation boundaries

Native `Engine.commitChance` validates resulting State relationships before
history/RNG commit. Two valid restored sources exposed omissions in the first
GPU composition: a queued decision duplicated an existing ID, and a retained
political decision referenced the continuation erased by a failed roll. Both now
produce error/rollback on GPU as they do natively. New postconditions check the
touched continuation, decision, controller and option-entitlement invariants.
Unchanged inventories, units, facilities, rails, battles and turn snapshots retain
their validated input invariants.

Training rules also filter a retained naval screening decision after chance.
That filter now preserves the exact native source order and failure behavior.
A retained naval force picker can require the unported naval-order-completion
service. If execution actually reaches that hook, the handler returns the
distinct `UNSUPPORTED_NAVAL_FORCE` capability result and rolls the transaction
back. It does not label the legal action illegal or remove it from a menu. An
older picker hidden below a newly queued recruitment choice is accepted, matching
native control flow. Removing this boundary requires the naval service port.

Recruitment placement/ship-work/repair choice execution and the CampaignAdapter
interrupt scheduler are separate work. CPU is still the only registered complete
campaign backend. These handlers are explicitly named Engine components, not a
claim of complete GPU games or a general resident State validator.

## Checks

The sampled-result transaction passed all 13 methods in one 90.80-second run,
including the original nine plus the restored-source and naval-hook cases. Its
guarded peak was 4.039 GB, including the entire 3 GB MPS reserve.

All 12 distinct start-action transaction methods passed: 11 passed in the first
run; one cohort-veto expectation was corrected and passed in a focused rerun.
The integrated start-to-chance case was also repeated against the exact current
chance-module source hash. The two focused methods took 6.09 seconds, with a
guarded peak of 3.729 GB. No production action code changed after its first run.

Comparisons include full State/history/RNG and every packed record bit, exact
Engine keys, zero treasury, CCP/Mongolia/controlled minors, signed sequence
boundaries, selected-lane failures, all capacity stages, late Event failure and
exact retries. Traps reject host reads, JSON, native effects and menu regeneration
inside the resident hot paths. Runs used two CPU threads, a 3 GB MPS allocation
limit, no fallback/fast math, and aggregate process-tree guards within the
12-core/30 GB user allowance. These are correctness results; warm complete-step
timings remain to be measured.
