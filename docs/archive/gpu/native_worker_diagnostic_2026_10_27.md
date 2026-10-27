# Prepared native worker diagnostic

The existing complete-step CPU control is genuinely parallel, but its roughly
2.5-times scaling at 512 lanes is not yet explained. Saved complete-grid probes
were unprofiled and have empty guard/resolve/output stage counters. Source review
found no shared Catalog lock or timed cross-lane Engine cache lock: fixture
Engines are independent, warm keys are cached, and mutation replaces the cache.
Allocation locality, memory contention and scheduling remain hypotheses. Worker
count also does not guarantee placement on particular performance cores.

`tools/profile_campaign_native_workers.py` prepares a bounded native-only sweep
using the original profiled API, serial execution and one pool at a time. It
preserves full native State/history/RNG/keys and labels stage counters as summed
lane-wall durations, including waits/preemption, rather than CPU time. Resource
bounds are twelve CPU cores and a 4 GB/240-second process-tree guard with no MPS
allocation. It imports package metadata without importing Torch.

All seven harness checks passed in 2.226 s (2.346 s guarded), peaking at
338,739,200 bytes. They include one-pool lifetime and exception cleanup, strict
profile/finalizer checks and a small real serial/pool native parity case.
The full 512-lane worker sweep was **not run**: work stopped at the user's update
request. No production engine, allocator, thread priority or learning method
changed, and no diagnosis of the CPU scaling follows from this prepared tool.
