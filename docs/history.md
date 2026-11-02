# Project history

What the earlier work found, for the pieces removed from the working tree on
2 November 2026. Every removed file is kept in commit `037cb60`, the last commit
before that cleanup. Read one with `git show 037cb60:PATH`, or restore a folder
with `git checkout 037cb60 -- PATH`.

## The prototype engine and two early studies

The first engine (`src/game_state.cpp`, `src/simulator.cpp`, the state and action
encoders and the `gw_simplified` program in `src/main.cpp`) played a simplified
six-zone China scenario (`game_content/scenarios/china_simplified_setup.json`).
Two small studies trained on it, and were later moved onto the campaign engine
through adapters (`src/campaign_benchmarks.cpp`, `JapanTrainingEnv`,
`CompositionBattleEnv`):

- **Composition** (`studies/composition`): an attacker and a defender chose army
  compositions within budgets of 50 and 30, then fought one battle. After 1,000
  episodes at 1,000 simulations per decision, the attacker's final reward was 2.40;
  the best were 3.09 for the attacker (episode 300) and −0.97 for the defender
  (episode 40). The run saved no network weights.
- **Mini Japan, two turns** (`studies/mini_japan_two_turn`): Japan alone learned
  on the six-zone scenario. After 500 episodes at 500 simulations, it scored 9.0,
  first reached in evaluation at episode 55.

Both runs predate later combat-rule corrections, so neither score says anything
about today's engine. The prototype's board page (`web/initial_board.html`),
manual battle (`game_content/scenarios/manual_battles/`) and `output/` notes went
with it.

## Milestone evidence, M1 to M12

Each milestone saved machine-readable records next to its page: source and
artifact hashes, test counts and checks, dated corrections and checkpoints
(`game_content/scenarios/japan_china_1936/m1` to `m11`, `docs/m9/evidence`,
`docs/m11/search_verification.json`, `docs/m12/*.json`, `docs/m2/benchmark.json`).
They certified each milestone at the time and went stale as the engine changed.
The milestone pages remain, trimmed to what is still true.

M10 also saved two complete campaigns from the approved July 1936 setup through
July 1941, all 44 national turns each: seed 1936 (1,558 transitions) and seed 1941
(1,289 transitions), with offline viewers, the exporter `tools/campaign_trace.cpp`
and the checkers `tools/verify_campaign_trace.py` and
`tools/verify_campaign_trace_viewer.mjs`. The current engine refuses their
checkpoints because the rules changed since. The M10 integration report went
with them.

The M12 records verified the first campaign network, which read a graph of the
position. The [zone encoding](stage_a/zone_encoding_2026_11_02.md) and its
[network](stage_a/zone_network_2026_11_02.md) replaced it on 2 November 2026.

## Stage A: learning and speed on the old pipeline

Stage A ran the first learning experiments and the performance work, mostly on
the graph input that is now gone. One line per record, all under `docs/stage_a`:

- **23 Oct, first pilots** (`training`, `performance`, `comparison`,
  `evaluation_*`, `preflight`, `position_profile`): eight one-round games trained
  in 346.6 s, then 118.7 s after reusing parsed inputs, with identical games.
  The trained Axis model finished both held-out games where the initial one
  looped; Allies and Comintern scores did not improve.
- **23 Oct, scaling** (`scaling`): thirteen bounded cases; one small-budget
  eleven-round game completed; stronger search needed speed work first.
- **24 Oct, decision reuse** (`decision_reuse`): one full game fell from 198.4 s
  to 112.7 s with the same 560 choices and results.
- **24 Oct, native graph input** (`neural_input`): the eleven-round game fell
  from 113.3 s to 104.6 s.
- **25 Oct, numeric training input** (`numeric_input_plan`,
  `numeric_training_input`): graph inputs compiled into numeric buffers in C++;
  four three-round games plus a learning update took 322 s instead of 542 s.
- **25 Oct, native concurrency** (`native_concurrency`): independent games run
  C++ work at once; four three-round games took 8 m 46 s instead of 11 m 38 s.
- **25 Oct, checkpoint pilot** (`checkpoint_pilot`): small model exports apart
  from full recovery saves, which run every thirty minutes. Checkpoint work had
  taken 60% of the three-round experiment's training time; in the pilot it took
  1.5%.
- **24–25 Oct, three-round experiment** (`three_round_*`): 60 complete games and
  15 learning batches within a ten-hour budget. In held-out games Japan took no
  Chinese Home Country territory; trained search kept more units and wealth than
  the initial search; the network alone showed no clear gain. A continuation
  (`sixty_more_*`) played 60 more games, 120 in all; Japan still took no new
  Chinese territory in held-out games.
  The experiment runner, its evaluator and its deadline guardian were removed
  with the records.
- **28 Oct, CPU profile and scheduling** (`cpu_profile`, `cpu_scheduling`):
  idle cores and legal-move generation were the costs; scheduling changes and
  shared menus raised self-play from 47.4 to 65.4 three-round games per hour,
  at 16 simulations with a small network.
- **28 Oct, game processes** (`cpu_processes`, `training_workers`,
  `worker_queue`): games split across processes reached 282 three-round games
  per hour at those settings; training with worker processes went from 53.3 to
  218.7 completed three-round games per hour. At the production settings below,
  ten workers and a game queue went from 32.0 to 34.9 three-round games per hour.
- **28 Oct, production benchmark** (`production_benchmark`): 64 simulations and
  a 64-wide network, the settings used since.
- **28 Oct, move generation** (`move_generation`): move lists 7.3 times faster,
  self-play 1.39 times, identical games.
- **28 Oct, dead ends** (`dead_ends`): random play found three engine defects
  that left a game with no legal action; fixed. Eleven-round self-play ran at
  12.6 to 14.6 games per hour.
- **29 Oct, landing plans and shared GPU** (`landing_plan_shared_gpu`): landing
  plans that can always be completed; one GPU process evaluating for many games,
  23.2 to 24.2 games per hour.
- **29 Oct, game-process profile** (`game_process_cpu_profile`): rules 50%,
  network inputs 36%, search 7% of a game process's CPU.
- **30 Oct, games per hour** (`games_per_hour`): eleven-round games at the
  production settings, 32.6 all-CPU and 48.3 with the GPU while playing; with
  learning, the 31 October training measured 20.2 and 31.0.

## GPU and batched-rules work

On 26 October the network on the Apple GPU (MPS) was 36% slower than on the CPU:
each call carried 1.7 positions on average. The batched-rules backend in
`studies/campaign/backends` gave games a bulk interface for a GPU rules engine;
only its CPU reference was written, and nothing adopted it. A separate port of
the rules to Metal was abandoned and its branch deleted on 31 October. The shared
GPU evaluator, which batches many games' positions, is what training uses.

## One-off measurements

Each answered one question, and the answer is in the code:

- `tools/benchmark_campaign_native_concurrency.py`: the native-concurrency
  comparison above.
- `studies/campaign/scaling_benchmark.py`: bounded CPU search cases, the scaling
  record above.
- `tools/benchmark_campaign_device_updates.py`: CPU against GPU for one learning
  update.
- `tools/benchmark_campaign_indexed_geography.cpp`: aircraft menus with and
  without a derived geometry view.
- `tools/benchmark_campaign_state_costs.cpp`: single-thread timings of engine
  primitives.
- `tools/profile_campaign_position.py`: one Japan Combat Movement search, step
  by step.
- `tools/profile_shared_coordinator.py`: each stage of the shared GPU
  evaluator's network call.
- `tools/verify_campaign_continuation.py`: proof that an old checkpoint could be
  carried over; old checkpoints are no longer kept.

## Full-world map audit

From 5 to 7 October 2026 every stored node and border of the world map was
checked against the printed map: 407 nodes (303 land, 104 sea) and 1,612
directed edges. Approved findings were applied to the map, which is built from
`game_content/maps/authoring`. The registers, data and scripts were removed;
they describe the map before the corrections, as of commit `eeb5e90`.
[Implementation status](map_audits/full_world/implementation.md), the
[source method](map_audits/full_world/source_method.md) and the
[open items](map_audits/full_world/uncertain.md) remain.
