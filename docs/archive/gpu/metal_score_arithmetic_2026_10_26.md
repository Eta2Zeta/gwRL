# Exact Apple GPU terminal-score arithmetic

`ResidentWealthContext.scores(result)` now returns native binary64 wealth, gaps
and terminal-return bit patterns on the GPU, plus float32 training targets rounded
once from the native binary64 returns. It consumes the existing exact, rounded
half-unit components. It does not replace native scores with rational twentieths
or use float32 intermediate score arithmetic.

Apple Metal lacks the native binary64 arithmetic used by the CPU objective.
The new kernel implements the needed operations with integer significands,
exponents, a two-word product and round-to-nearest/ties-to-even. It retains the
CPU's component addition order, fused tenth-times-assets-plus-income expression,
ordered three-side sum and final gap calculation. This is a bounded scoring
implementation, not a general-purpose IEEE arithmetic library.

Inspection of the existing Apple CPU object code confirmed that
`WealthComponents::total()` already used `fmadd`. C++ now spells that operation
explicitly as `std::fma`, retaining this CPU's results and making the intended
rounding explicit across compilers. The old diagnostic Python inspector used
an unfused expression, which could disagree by one rounding unit: income 1 and
assets 7 give 1.7 fused versus 1.7000000000000002 unfused. Its inspector now uses
the fused operation too. Historical training used the native CPU score, not
this diagnostic inspector; no historical data is rewritten.

Validation included 12,337 three-player component sets against both the original
native `WealthComponents::total()` path and an independent Python binary64/FMA
calculation. Cases cover signed int64 extremes, component rounding near 2^53,
cancellation, negative asset values, zeros, fused/unfused witnesses and float32
rounding boundaries. Every wealth, gap, terminal-return and training-target bit
matched. Additional real campaign states compare the full native wealth oracle,
and hot-path checks prohibit CPU reads, JSON and native-rule fallback.

The combined run of four new arithmetic tests, the existing wealth tests and
lossless state tests passed all 24 checks in 41.01 seconds. Its guarded peak was
3.764 GB including the entire 3 GB MPS reserve. All 27 native suites passed after
the explicit FMA and wire-prefix changes. Sources and all three RNG streams are
read-only in this scoring operation. These are correctness results, not a claim
of faster complete games, completed GPU gameplay or stronger learning.

The earlier explicitly named rational fields remain available for diagnostics.
Callers must use the new native scores/targets and honor their error masks when
connecting a future complete GPU learner. A full GPU campaign backend is still
unregistered.
