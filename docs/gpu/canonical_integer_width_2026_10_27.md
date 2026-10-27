# Native-width integer formatting

The Metal canonical integer writer still accepts exactly native signed int32
values and rejects all others before writing. Its decimal magnitude now uses
`uint` instead of `ulong`. Negation remains on the already-guarded signed long,
so INT_MIN becomes the exactly representable unsigned magnitude 2^31. The digit
loop, bytes, partial output and error ordering are unchanged. Separate UInt64
serialization, including full-width player-turn counters, is untouched.

All 46 checks passed: four new width-focused cases and the existing generic,
State, unit-parallel and field-parallel formatter suites. Old and new GPU sources
match at dense decimal boundaries and every output capacity, including range
errors and partial bytes. Cached fractions, negative zero, missing number
spellings and native UInt64MAX State/Engine keys also match.

The suite took 176.027 s (177.296 s guarded), using two CPU threads with a
3,702,317,360-byte peak charge including the full 3 GB MPS reservation. This is
correctness evidence only. The compiler may already optimize the former wider
arithmetic; a frozen matched timing must establish any performance benefit.
