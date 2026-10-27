# Parallel complete-arena copy for sampled RNG installation

`install_sampled_randomness` now offers `implementation="parallel"`, also selected
by a shared context's explicit parallel editor policy. The reference remains
available and the default context policy is unchanged. The parallel path clones
the complete output arena on device, including unused padding, then executes the
original per-lane validation and four RNG-field writes. Only the serial whole-arena
copy loop is removed from the audited shader. Its marker checks fail closed if
that original source changes.

Stale/double commits, modified Random subtrees, bad sampler results and divergent
string pools retain the same errors. Unselected lanes and global cohort rollback
retain every original output word. Neither input aliases the cloned candidate.
No host reads, dice resampling, new identity scheme or rule change is introduced.

All ten contract cases passed, including native completed-chance comparisons,
all three full-width random streams, tapes/rerolls, nonzero signed-64-bit padding,
selected lanes, malformed inputs, zero lanes, namespace changes and host-read
traps. They took 33.101 s (34.388 s guarded), with a 3,845,545,472-byte peak charge
including the full 3 GB MPS reservation. Six additional complete action/chance
comparisons passed with both editor/container policies, native state/history/RNG
gold, capacity failures and the existing unsupported naval hook rollback. Those
checks took 79.094 s (80.073 s guarded), peaking at 3,787,939,328 charged bytes.
Each job used two CPU threads; these concurrent correctness timings are not
throughput evidence. No speed claim is made before a separate matched benchmark.

The complete recruitment handler now accepts an independent explicit RNG-copy
policy, with `None` retaining the context default. Benchmark schema v6 records
that selection and rejects mismatched reports. A separate full-handler case
matched both policies against each other and native state/history/RNG while all
other policies stayed identical; option/finalizer checks also passed. This lets a
future timing isolate this copy from the earlier editor/container changes within
one frozen runtime. The first test command used two incorrect harness class
names; those two checks were rerun successfully under their actual class name.
