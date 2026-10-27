# Income-rate correction before connected GPU chance execution

This is a CPU correctness correction, separate from GPU timing optimizations.
It changes observable cached rates and therefore has a new execution contract.

The outer politics layer looked for `m6_economy` in its inner rule composition.
The economy layer actually identifies itself as `gw36_economy_v43`. Consequently
the outer action and chance hooks skipped their intended income-rate refresh.
Inner economy hooks still ran, but could not cover effects handled by outer
politics, movement or combat layers.

A legal reproduction uses the unchanged balanced baseline, seed 1951 and the
three-round curriculum. Transition 14 is a CCP `land_take_casualty` choice that
finishes the battle in Hopeh. Possession changes from the Beiping/Hopeh warlord
to CCP. CCP's stored territorial rate remained 2; the native `evaluateIncome`
and `refreshIncome` calculation gave 3 immediately. The calendar was still in
Combat, with income uncollected. No manually edited ownership was required.

The politics constructor now recognizes the exact economy composition token
using the same constant as `EconomyRules::id`, once at construction. Its action
and chance hooks refresh rates after their effects. This does not collect cash
or advance the calendar. Standalone politics without an economy module retains
its existing unknown-accounting behavior.

The politics component identifier is now
`gw36_v43_m4_politics_income_refresh_v1`. Engine restoration rejects checkpoints
with the old identifier before changing the environment. Historical training
runtimes, checkpoints and reports remain preserved; they are not migrated or
retagged. Future CPU/GPU comparisons must use the same corrected contract on
both sides. Earlier measurements remain measurements of their recorded commits.

The connected GPU recruitment-chance handler requires the corrected politics
component and the economy component explicitly. Core recruitment effects remain
separately checked against the original native effect function.

Validation: three Python regressions cover the real capture, the chance refresh
without cash collection, and atomic rejection of an old-contract checkpoint.
The native suite also checks standalone unknown accounting and exact replay.
