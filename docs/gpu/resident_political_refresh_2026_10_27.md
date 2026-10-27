# Complete resident internal political refresh

`ResidentPoliticalRefresh.refresh` now composes the complete native
`refreshPoliticalState` helper on Apple GPU State: all possession flags; CCP then
KMT civil flags and conditional promotion/movement/truce/evolution choices; KMT
surrender; the One China objective and award; final ally rebuilding. Absent
Chinese factions skip their blocks. Surrender's last-conqueror value is read only
when KMT has actually lost all land and has not already surrendered.

The original single pass is preserved. If CCP evolves first, a resulting battle
can use KMT's still-minor status before KMT's own promotion. If KMT surrender later
removes CCP cargo, the earlier CCP civil flag is not recomputed. Movement Catalog
queries see the already-promoted State and its new evolution flags. No extra
fixed-point pass, income collection, calendar change, combat resolution, Engine
validation, audit Event or random draw is added.

Allocation sizes are explicit, with device-resident stage selection, first-error
diagnostics and required capacities. One final commit publishes records and pools
together. Any selected failure preserves every source State/history/RNG word;
capacity failures support an exact explicit retry without truncating choices.

Ten distinct methods passed direct raw native-helper comparisons. They cover
simultaneous evolution, absent factions, carried-unit surrender, pending/awarded
choices, lazy malformed continuations, errors at different stages, Catalog
failures, exact allocation retries and hot-path host/native/JSON traps. Nine
methods passed in the full 44.956 s run; the remaining method had already passed
raw parity but its extra serialized-field inspection assumed an optional field
was present. That inspection was corrected to compare presence and value and
passed separately in 3.745 s. An earlier fixture also attempted to add unsupported
action-interface fields and was corrected before exercising the helper. No
resident rule implementation needed a runtime correction.

The full valid-fixture guard took 45.86 s and peaked below 3.79 GB including a
3 GB MPS reservation; the focused guard took 4.723 s and peaked below 3.67 GB.
Each used two CPU threads. These are correctness timings with concurrent checks,
not throughput evidence. The [facts/native checks](resident_political_facts_2026_10_27.md)
record the shared build and all 27 passing native suites. A complete registered
GPU campaign backend and GPU search remain unfinished.
