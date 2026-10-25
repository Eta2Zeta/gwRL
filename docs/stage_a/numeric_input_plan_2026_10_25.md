# Numerical training input and simulation speed plan

The current graph model and game rules remain the reference. This work changes
how their existing information reaches the model, without reducing legal menus,
search simulations, network size, dice fidelity or campaign length.

1. Export immutable native observation, context and scheduled-action snapshots.
   Compile them directly into contiguous numerical graph buffers, preserving
   every field and exact node/edge/token ordering. Retain public JSON inspection.
2. Share fixed scenario graphs and bounded scalar/topology preparation caches.
   Reuse learned fixed-context vectors only during explicitly versioned frozen
   inference; gradient training always recomputes learned values.
3. Store numerical replay inputs directly, with validated binary checkpoint
   serialization and support for existing JSON replay inputs. Preserve exact
   continuation, optimizer state and unfinished-game recovery.
4. Build a shared dense geography index and geometry-only distance table. Use it
   where repeated aircraft route calculations currently rebuild the same data;
   preserve permission-sensitive rules and source ordering.
5. Check numerical fields, model outputs/gradients, cache invalidation, complete
   legal menus, search outcomes, RNG and checkpoint continuation against the
   reference. Run the full applicable Python and C++ suites.
6. Measure matched opening/later searches and completed three-round games with
   the existing 16-simulation, depth-16, hidden-16 benchmark. Measure actual
   learning and memory before considering a larger training run. Keep total
   use within 12 CPU cores and 30,000,000,000 bytes of RAM.

Commit validated pieces with their tests, then record and commit measured results.
The previous native-concurrency runtime is the preserved before-change baseline.
