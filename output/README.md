# Temporary simulator output

This directory is for disposable exports from the C++ debug program:

- `snapshots/` and `session_actions.txt`: simulator inspection output.
- `japan_training_example.json`: optional C++/Python encoding comparison.
- `manual_battle_trace.txt`: manual battle debug output.

These are generated on demand and ignored by Git. Training code and preserved
completed results now live under [studies/](/Users/home/Desktop/gwRL/studies/README.md).
New training runs write into each study's `runs/` directory instead of mixing
files into this folder.
