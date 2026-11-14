# Archive

History, kept for looking things up. Nothing here is needed to understand the
program as it is now; for that, start at the [documentation guide](../README.md).
Every page describes the code, settings and paths of its own date, and its open
questions and next steps are those of that date.

| Part | What it holds |
| --- | --- |
| [Dated records](#dated-records) | One page per measurement, experiment or rule change since 24 October 2026, each with its data file. |
| [Milestone pages](#milestone-pages) | The delivery reports of the engine's twelve build stages, M0 to M11, from October 2026. |
| [Removed on 2 November 2026](#removed-on-2-november-2026) | What the earlier work found, for the files no longer in the tree, and where git keeps them. |

An earlier archive, made on 27 October 2026 on a branch that was retired four
days later, is kept under the git tag `archive/gpu-rules-port-2026-10-27`.

## Dated records

All are in [`records/`](records/). A record's data file has the same name ending
in `.json`. Until 14 November 2026 this folder was `docs/stage_a`, after Stage A,
the first learning stage.

### Learning and search

| Date | Record | What it found |
| --- | --- | --- |
| 31 Oct | [Decision, rules and training review](records/decision_review_2026_10_31.md) | The objective rewards a passive Japan; decisions that could be removed, search evaluations and flat targets. |
| 5 Nov | [One real training sample](records/training_sample_2026_11_05.md) | What a sample stores, shown with a real decision; a fresh network gives every position the same values. |
| 9 Nov | [How often the depth limit stops a simulation](records/depth_limit_2026_11_09.md) | 18 of 68,800 simulations reached the limit of 16 steps; without it no most-visited move changed. |
| 9 Nov | [What Adam did in one real update](records/adam_steps_2026_11_09.md) | Re-running the 5 November update gave generation 1 exactly; how the steps shrink. |

### The network's input

| Date | Record | What it found |
| --- | --- | --- |
| 2 Nov | [A fixed zone encoding of campaign decisions](records/zone_encoding_2026_11_02.md) | 37 zones answer fixed questions; 49 to 64 times smaller and 5 to 6 times faster to build than the graph input it replaced. |
| 2 Nov | [The network reads the zone encoding](records/zone_network_2026_11_02.md) | A forward pass 7.4 times faster and a training step 43 times faster on the same positions. |
| 4 Nov | [Railroads named by their border, and repairs encoded](records/rail_repair_encoding_2026_11_04.md) | One railroad per border (RCL-019), so a railroad is named by its two zones. |
| 4 Nov | [Every name the engine writes gets a question](records/zone_names_2026_11_04.md) | The names missing from the input's lists, found and fixed. |
| 5 Nov | [The name check's early phase ends](records/zone_name_check_early_end_2026_11_05.md) | The check never ended a phase early; fixed, and the more varied games found upgrades aboard transports. |

### Speed

| Date | Record | What it found |
| --- | --- | --- |
| 4 Nov | [Where self-play time goes](records/search_replays_2026_11_04.md) | The coordinator was busy 92% of the time; a search played 75 to 133 moves again on copies. |
| 4 Nov | [The search keeps a copy of the game at every tree position](records/search_copies_2026_11_04.md) | Identical results with 59% fewer moves played; 184 games per hour instead of 152. |
| 4 Nov | [The coordinator's column lookups](records/coordinator_lookups_2026_11_04.md) | The lookups were 22% to 49% of the network's forward pass; a fused replacement measured. |
| 12 Nov | [The fused column lookup, in the code](records/coordinator_lookups_2026_11_12.md) | Identical outputs; decisions per hour rose 17.6% in matched batches. |
| 13 Nov | [Where the game processes' time goes](records/game_processes_2026_11_13.md) | Playing a move and listing the legal moves cost about a millisecond each, two thirds of the game threads' CPU. |

### The engine

| Date | Record | What it found |
| --- | --- | --- |
| 14 Nov | [Where each kind of move is offered](records/move_census_2026_11_14.md) | 240 random games met 93 of the engine's 141 kinds of move, each in the phase the engine pages name; the Chinese Truce never came up. |

### Rule changes

| Date | Record | What changed |
| --- | --- | --- |
| 24 Oct | [Bounded AI orders](records/action_interface_2026_10_24.md) | Forward-only naval orders and bounded configuration and permission choices. |
| 31 Oct | [Finished battles clear themselves](records/battle_clearing_2026_10_31.md) | 5.2% fewer decisions in the same games. |
| 1 Nov | [Aircraft move once per turn](records/aircraft_single_move_2026_11_01.md) | A plane that flew in Combat Movement no longer flies again in Noncombat Movement. |
| 1 Nov | [Combat Movement lists only moves that start a combat](records/combat_movement_combats_only_2026_11_01.md) | Combat Movement lists fell to about a third of their size. |
| 4 Nov | [A patrol plane's second chance](records/patrol_second_chance_2026_11_04.md) | Ships a patrol plane let pass may attack it anew (RCL-017). |
| 4 Nov | [A patrol plane's own choice in a sea battle](records/patrol_choice_2026_11_04.md) | It chooses by the patrol rule, before any scramble (RCL-020). |
| 4 Nov | [A patrol fighter bars the way on](records/patrol_fighter_screen_2026_11_04.md) | Ships need a screening force to sail on past a patrol Fighter (RB 9.3.1). |
| 5 Nov | [Choices that are never better](records/never_better_choices_2026_11_05.md) | Cargo may stay aboard; an upgrade may not leave a transport with cargo it cannot carry. |
| 6 Nov | [Upgrades wait while their unit is at sea](records/upgrades_at_sea_2026_11_06.md) | A unit aboard a ship at sea is not offered an upgrade (RCL-021). |

## Milestone pages

The engine was built in twelve stages in October 2026. Each page is that
stage's delivery report: what it added, its exit checks and what it left for
later stages. The [engine documentation](../engine/README.md) describes the
same modules as they are now.

| Stage | Subject | Date on the page |
| --- | --- | --- |
| [M0](milestones/m0/README.md) | The approved campaign: scope, setup and scoring decisions | 21 Oct |
| [M1](milestones/m1/README.md) | The theatre map cut from the world map, and faction identities | 21 Oct |
| [M2](milestones/m2/README.md) | Engine state and execution foundation | 21 Oct |
| [M3](milestones/m3/README.md) | Unit, facility and technology catalog | 21 Oct |
| [M4](milestones/m4/README.md) | Politics, warlords and national turns | 21 Oct |
| [M5](milestones/m5/README.md) | Movement and shared logistics | none |
| [M6](milestones/m6/README.md) | Economy, production, construction and research | 22 Oct |
| [M7](milestones/m7/README.md) | Land combat | 22 Oct |
| [M8](milestones/m8/README.md) | Air operations, bombing and defensive reactions | 22 Oct |
| [M9](milestones/m9/README.md) | Naval, carrier and amphibious operations | 23 Oct |
| [M10](milestones/m10/README.md) | The complete campaign, integrated | 23 Oct |
| [M11](milestones/m11/README.md) | The environment for agents, and the search | 23 Oct |

The ledgers and source audits these stages produced are still current and live
in [`docs/rules`](../rules/README.md).

## Removed on 2 November 2026

What the earlier work found, for the pieces removed from the working tree on
2 November 2026. Every removed file is kept in commit `037cb60`, the last commit
before that cleanup. Read one with `git show 037cb60:PATH`, or restore a folder
with `git checkout 037cb60 -- PATH`. Paths in this part are those of that commit.

### The prototype engine and two early studies

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

### Milestone evidence, M1 to M12

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
position. The [zone encoding](records/zone_encoding_2026_11_02.md) and its
[network](records/zone_network_2026_11_02.md) replaced it on 2 November 2026.

### Stage A: learning and speed on the old pipeline

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

### GPU and batched-rules work

On 26 October the network on the Apple GPU (MPS) was 36% slower than on the CPU:
each call carried 1.7 positions on average. The batched-rules backend in
`studies/campaign/backends` gave games a bulk interface for a GPU rules engine;
only its CPU reference was written, and nothing adopted it. A separate port of
the rules to Metal was abandoned and its branch deleted on 31 October. The shared
GPU evaluator, which batches many games' positions, is what training uses.

### One-off measurements

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

### Full-world map audit

From 5 to 7 October 2026 every stored node and border of the world map was
checked against the printed map: 407 nodes (303 land, 104 sea) and 1,612
directed edges. Approved findings were applied to the map, which is built from
`game_content/maps/authoring`. The registers, data and scripts were removed;
they describe the map before the corrections, as of commit `eeb5e90`.
[Implementation status](../map_audits/full_world/implementation.md), the
[source method](../map_audits/full_world/source_method.md) and the
[open items](../map_audits/full_world/uncertain.md) remain.
