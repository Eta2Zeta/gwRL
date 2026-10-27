# Exact resident political queues and Chinese Truce termination

The Apple GPU now reproduces the native internal helpers for generic political
decision queues, evolution capital/factory choices, and Chinese Truce termination.
The queue preserves supplied action IDs and parameter bits, updates pending work
before resolving its controlling player, and retains native counter and option
ordering. Evolution queues all possessed-land choices in the original order.
Truce termination assigns battle roles using the active Chinese nation or, during
a third-party turn, the land possessor as defender. It retains the original
movement-origin checks, minor-status flag and full unsigned turn-serial IDs.

These helpers do not resolve battles, advance the calendar, draw dice or publish
Engine Events. Promotion, the 13-IPP trigger and complete political refresh remain
separate work. The CPU is still the only complete registered campaign backend.

All 22 distinct GPU cases passed comparisons against raw typed native State and
private RNG: ten decision/evolution cases and twelve truce cases. Coverage includes
numeric sentinels, pending-key collisions, controlling players, duplicate IDs,
large stacks, carried units, automatic and voluntary termination, deferred border
errors, allocation retries, selected-lane laziness and complete cohort rollback.
The checks also reject host/native/JSON calls in the resident transition path.

The first decision run exposed a lifetime bug in the diagnostic C++ oracle: its
range loop referenced an array inside a temporary parsed JSON value. Naming that
parsed value fixed the oracle; the five affected cases then passed in 20.175 s.
The other five had already passed. No resident rule code changed for this repair.
The twelve truce cases passed in 75.880 s. All 27 native suites subsequently passed
in 37.94 s. GPU checks used two CPU threads and stayed below a 3.80 GB conservative
charge, including the full 3 GB MPS reservation.

Diagnostic fixtures replace typed State/definition data through normal Engine
validation while retaining the source Rules and private RNG. They do not retag
old device arenas or round-trip State through JSON. New fixed strings extend the
wire fingerprint; older raw arenas must keep their matching runtime/context.
These are correctness results, with no throughput or learning-strength claim.
