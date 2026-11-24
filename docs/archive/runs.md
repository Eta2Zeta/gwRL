# Runs

Every run of the campaign program, whether it trains networks, measures speed or
checks a change, keeps its files in its own folder under `studies/campaign/runs/`.
Git ignores that folder, so the files stay on the machine that made them; this
page lists them, oldest first, with what each run was and the record that
reports it. It is part of the [archive](README.md): each run is described as of
its own date.

## How a run folder is named and laid out

- **Name.** What the run is, then the date it started: `one-network-2026-11-17`.
  A training run that went on in parts, each restarted with new code or new
  settings, keeps its parts in one folder, each part named by its place in the
  order and by what it was: `training-2026-11-19/4-choice-b`. A run that was
  attempted more than once keeps its attempts the same way.
- **What the program writes.** A run folder made by `studies.campaign.run` holds
  `manifest.json` (the settings, counters and status), `progress.jsonl` (a line
  for each search wave and network update), `models/` (the model exports),
  `checkpoint.pt` (what a resume needs), and, in runs that keep them,
  `game-moves/` (each game's move log), `crash-reports/` and `failed-positions/`
  ([training runs and resume](../../studies/campaign/README.md#training-runs-and-resume)).
- **What a script keeps beside its run.** A run started by a script keeps, next to
  its run folder, the script, `code/` (the files of the commit it ran, with the
  engine build it used) and its logs. The scripts and logs name the paths of
  their own date.

Runs from before 22 November 2026 were moved here from `tmp/` or renamed;
[moved and renamed folders](#moved-and-renamed-folders) gives each earlier path,
which the records of their date still name.

## Training runs

| Folder | Started | What it was | Record |
| --- | --- | --- | --- |
| `smoke-test-2026-10-23` | 23 Oct | Two short checks of the training command: one-round games, a 16×1 network, 2 simulations; `1-interrupted` stopped by hand, `2-completed` made two network updates. | |
| `one-round-training-2026-10-23` | 23 Oct | One-round games, a 16×1 network, 4 simulations: 8 games, 2 network updates. | |
| `three-round-training-2026-10-24` | 24 Oct | Three-round games, 16×1, 16 simulations, 4 games at a time: two attempts stopped early (`1-first-attempt`, `2-second-attempt`), an overnight run of 60 games and 15 network updates (`3-first-60-games`), continued to 120 games and 30 network updates on 25 October (`4-sixty-more-games`). | |
| `training-2026-10-30` | 30 Oct | The first night of eleven-round training: 64×2 on the CPU, 11 or 13 games at a time, one per worker process, in four parts one after another: `1-thirteen-games`, stopped by the memory limit; `2-eleven-games`, stopped by a game worker's error; `3-eleven-games-again`, stopped to move to new code; and `4-raider-fix`, the rest of the night on the code with the raider fix, and recorded games of its networks (`games/`). | |
| `gpu-training-2026-10-31` | 31 Oct | Eleven-round training at 64×2 with the network on the GPU: 64 games, 2 network updates. | [One real training sample](records/training_sample_2026_11_05.md) |
| `training-2026-11-02` | 2 Nov | The night run at 256×8 on the GPU: 9 game processes of 13 games, 117 at a time; two game process crashes in its third training iteration, then replayed outside the supervisor (`LINEAGE.md`). | [One real training sample](records/training_sample_2026_11_05.md) |
| `training-2026-11-19` | 19 Nov | The longest training so far, 35.5 hours of play: a 256×8 network on the GPU, 252 games at a time in 6 game processes of 42, every decision searched with 64 simulations and every move drawn from the visit shares, self-play that never stops, in five parts: `1-first-night`, `2-morning`, `3-afternoon`, `4-choice-b` (1% of decisions kept, a replay buffer of 25,000) and `5-restart`, which crashed after 3.6 minutes; 9,576 games and 38 network updates in all. Its game processes crashed six times, and it was stopped on 21 November to look for the cause. | [What it learned in 38 network updates](records/long_run_progress_2026_11_21.md) |
| `memory-check-2026-11-21` | 21 Nov | Training games whose game processes ran an engine built with AddressSanitizer, to find the game process crashes: one process of 14 games, 21.2 hours, 1,276,928 decisions, no report; seven attempts, `1-two-processes` to `7-quarantine-1gb`, the last of which is the run. | [The memory-checked run](records/memory_check_2026_11_21.md) |
| `training-2026-11-22` | 22 Nov | The first training under the rules since RCL-022 and RCL-023 and choice D's searches, from a fresh network. Its first part, `1-memory-checked`, plays one game process of 16 games on an engine built with AddressSanitizer, to find the game process crashes within 8 CPU cores; launches with 42 and 24 games kept about 12 and 10 CPU cores busy and were stopped within minutes. It was stopped at 20:04 on 22 November, when the owner changed the final score, after 8.05 hours, 187 network updates and 2,992 games, with no report. | [A fresh network's first games](records/fresh_network_games_2026_11_22.md); [the memory-checked first part](records/memory_check_2026_11_22.md); [the first 141 network updates](records/training_progress_2026_11_22.md), with the held-out evaluation in its `evaluations` folder |
| `training-land-weighted-2026-11-22` | 22 Nov | The first training under the land-weighted score, from a fresh network, started on the evening of 22 November: every land zone held counts 1 besides its income, and units, infrastructure, treasury and paid construction a twentieth of their IPP. Its first part, `1-memory-checked`, plays as the training run of 22 November did, one game process of 16 games on an engine built with AddressSanitizer. By 19:30 on 23 November it had played 23.23 hours, 363 network updates and 5,809 games, with no report; one game had failed, at 00:19, on a defect of the rules, and a second failed at 20:07, on another, when Japan and Dadao had both attacked Manchuria-Rehe in one turn (Q-019). Its `evaluations` folder holds the held-out evaluations of its 197th, 288th and 363rd network updates, the last two of the Axis on all 24 held-out seeds, the self-play games rebuilt from their move logs, the replays of the second failed game, and the scripts that made them. | [What it learned overnight](records/training_land_weighted_2026_11_23.md); [at its 288th network update](records/training_land_weighted_update_288_2026_11_23.md); [at its 363rd](records/training_land_weighted_update_363_2026_11_23.md); [the second failed game](records/japan_dadao_one_zone_2026_11_23.md); [its 288th and 363rd network updates on 24 seeds](records/training_land_weighted_24_seeds_2026_11_23.md) |

## Measurements and checks

| Folder | Started | What it was | Record |
| --- | --- | --- | --- |
| `episode-guard-check-2026-10-23` | 23 Oct | A run stopped by its budget of moves per game (status `episode_budget_exhausted`). | |
| `episode-scaling-2026-10-23` | 23 Oct | Games of one, two and eleven rounds at several simulation counts and search depths (`episode-*.json`); the folder was first named after RCL-014. | |
| `one-round-speed-check-2026-10-23` | 23 Oct | The one-round run again, as a speed check. | [Bounded AI orders](records/action_interface_2026_10_24.md) |
| `performance-2026-10-23` | 23 Oct | Profiles of game collection and network updates before and after a speed change (`baseline`, `optimized_paired.json`). | |
| `action-interface-2026-10-24` | 24 Oct | The bounded AI orders: validation plan, behaviour cases, the baseline's code and a one-round run on the new interface. | [Bounded AI orders](records/action_interface_2026_10_24.md) |
| `encoder-pass-2026-10-24` | 24 Oct | One-round runs before and after a change to the input's encoding pass, with the baseline's code. | [Bounded AI orders](records/action_interface_2026_10_24.md) |
| `replay-capture-smoke-test-2026-10-24` | 24 Oct | A short run that captured its game for replay. | |
| `viewer-smoke-test-2026-10-24` | 24 Oct | A short run whose games the Campaign Observatory showed. | |
| `backend-foundation-2026-10-25` | 25 Oct | Positions and scripted games kept as benchmark workloads (`*.workload.json`). | |
| `checkpoint-pilot-10games-2026-10-25` | 25 Oct | Ten three-round games with recovery checkpoints. | |
| `native-concurrency-2026-10-25` | 25 Oct | Games with the engine's game threads running in parallel, old code against new. | |
| `numeric-input-2026-10-25` | 25 Oct | Runs before and after numeric network inputs. | |
| `numeric-input-reuse-2026-10-25` | 25 Oct | The same with the input reused; old and new code each played 1,094 decisions. | |
| `gpu-backend-2026-10-26` | 26 Oct | Measurements of the GPU rules backend, since removed. | |
| `cpu-processes-2026-10-28` | 28 Oct | Self-play with 2 and 10 processes. | |
| `cpu-profile-2026-10-28` | 28 Oct | CPU profiles of applying a move and listing legal moves. | |
| `cpu-scheduling-2026-10-28` | 28 Oct | Self-play timings of two ways to batch work (`batched_menu`, `batched_table`). | |
| `dead-ends-2026-10-28` | 28 Oct | Random games that look for dead ends, before and after a fix. | |
| `eleven-round-2026-10-28` | 28 Oct | The first eleven-round self-play, and two recorded games. | |
| `eleven-round-confirm-2026-10-28` | 28 Oct | Eleven-round self-play repeated (`selfplay_10x10`). | |
| `move-generation-2026-10-28` | 28 Oct | The legal moves checked game by game against the patrol rules (`patrolrules-*`). | |
| `production-benchmark-2026-10-28` | 28 Oct | The network's cost on one CPU core and on the GPU, and self-play at 64×2 with 64 simulations. | |
| `training-workers-2026-10-28` | 28 Oct | Three-round training with no worker processes, 4 and 8. | |
| `worker-queue-2026-10-28` | 28 Oct | Self-play from a queue of games (`queue_10x30`). | |
| `game-cpu-profile-2026-10-29` | 29 Oct | CPU profiles of a game process over 600 to 4,000 seconds. | |
| `landing-plan-2026-10-29` | 29 Oct | Random games that look for dead ends around the landing-plan rule. | |
| `shared-gpu-2026-10-29` | 29 Oct | Self-play of 8 processes of 4 games with one shared evaluator on the GPU. | |
| `games-per-hour-2026-10-30` | 30 Oct | Games an hour with 8 and 10 processes, the network on the CPU or the GPU. | |
| `nine-fixes-2026-10-30` | 30 Oct | An identity check of searches after nine fixes (`identity_all`). | |
| `one-move-skip-2026-10-30` | 30 Oct | Identity checks of searches with and without skipping decisions that have one legal move (`identity_search`, `identity_skip`). | |
| `profile-2026-11-02` | 2 Nov | A profiled training iteration of eleven-round games at 64×2. | |
| `profile-check-2026-11-02` | 2 Nov | A one-round check of the profiler. | |
| `zone-speed-2026-11-02` | 2 Nov | Training iterations with the zone encoding, the network on the CPU and on the GPU. | |
| `search-copies-2026-11-04` | 4 Nov | Matched training iterations before and after the search kept a game copy at every tree position. | [Search copies](records/search_copies_2026_11_04.md) |
| `sample-example-2026-11-05` | 5 Nov | The training iteration whose decision 612 is the design document's running example. | [One real training sample](records/training_sample_2026_11_05.md) |
| `coordinator-lookups-2026-11-12` | 12 Nov | Matched training iterations before and after the fused column lookup. | [The fused column lookup](records/coordinator_lookups_2026_11_12.md) |
| `game-process-profile-2026-11-13` | 13 Nov | A profiled training iteration: where the game processes' time goes. | [Game processes](records/game_processes_2026_11_13.md) |
| `supply-cache-2026-11-14` | 14 Nov | Matched training iterations before and after caching supply answers. | [Supply cache](records/supply_cache_2026_11_14.md) |
| `coordinator-rounds-2026-11-17` | 17 Nov | A profiled training iteration: where a coordinator round's time goes. | [Coordinator rounds](records/coordinator_rounds_2026_11_17.md) |
| `self-play-never-stops-2026-11-17` | 17 Nov | Two matched pairs, self-play that never stops against alternating training iterations. | [Self-play that never stops](records/self_play_never_stops_2026_11_17.md) |
| `one-network-2026-11-17` | 17 Nov | Matched runs of 3.7 hours, one network for the three alliances against three. | [One network](records/one_network_comparison_2026_11_17.md) |
| `compiled-forward-2026-11-18` | 18 Nov | The compiled zone and position layers against the layers as written. | [Compiled forward pass](records/compiled_forward_2026_11_18.md) |
| `gpu-training-2026-11-18` | 18 Nov | Two matched pairs at 256×8 on the GPU, with and without the compiled layers. | [Compiled layers in GPU training](records/gpu_training_compiled_2026_11_18.md) |
| `concurrent-games-2026-11-18` | 18 Nov | 63 and 126 concurrent games at 256×8 on the GPU. | [Concurrent games on the GPU](records/concurrent_games_gpu_2026_11_18.md) |
| `never-stops-gpu-2026-11-18` | 18 Nov | Self-play that never stops on the GPU against alternating training iterations. | [Never stops on the GPU](records/never_stops_gpu_2026_11_18.md) |
| `server-profile-2026-11-18` | 18 Nov | A profiled training iteration: where the inference server's time goes on the GPU. | [Inference server profile](records/inference_server_profile_gpu_2026_11_18.md) |
| `readout-fix-2026-11-18` | 18 Nov | The policy readout without a repeat, in profiled training iterations. | [Readout without a repeat](records/readout_without_repeat_2026_11_18.md) |
| `engine-profile-2026-11-19` | 19 Nov | A profiled training iteration: where the game processes' time goes on the GPU. | [Game processes on the GPU](records/game_processes_gpu_2026_11_19.md) |
| `search-cpp-2026-11-19` | 19 Nov | Two matched pairs before and after the search in C++. | [The search in C++](records/search_in_cpp_2026_11_19.md) |
| `concurrent-cpp-2026-11-19` | 19 Nov | 189, 252 and 378 concurrent games with the search in C++. | [Concurrent games with the C++ search](records/concurrent_games_cpp_search_2026_11_19.md) |

`retired-branch-bundle-2026-10-31` is no run: it keeps, as a git bundle, the
GPU self-play branch retired on 31 October 2026.

## Moved and renamed folders

| Earlier path | Folder now |
| --- | --- |
| `studies/campaign/runs/m12-smoke-2026-10-23` | `smoke-test-2026-10-23/1-interrupted` |
| `studies/campaign/runs/m12-final-smoke-2026-10-23` | `smoke-test-2026-10-23/2-completed` |
| `studies/campaign/runs/stage-a-guard-check-2026-10-23` | `episode-guard-check-2026-10-23` |
| `studies/campaign/runs/stage-a-one-round-2026-10-23` | `one-round-training-2026-10-23` |
| `studies/campaign/runs/stage-a-speedcheck-2026-10-23` | `one-round-speed-check-2026-10-23` |
| `studies/campaign/runs/scaling-2026-10-23-rcl014` | `episode-scaling-2026-10-23` |
| `studies/campaign/runs/replay-capture-smoke-20261024` | `replay-capture-smoke-test-2026-10-24` |
| `studies/campaign/runs/viewer-complete-smoke-20261024` | `viewer-smoke-test-2026-10-24` |
| `studies/campaign/runs/three-round-10h-2026-10-24` | `three-round-training-2026-10-24/1-first-attempt` |
| `studies/campaign/runs/three-round-10h-2026-10-24-r2` | `three-round-training-2026-10-24/2-second-attempt` |
| `studies/campaign/runs/three-round-10h-2026-10-24-r3` | `three-round-training-2026-10-24/3-first-60-games` |
| `studies/campaign/runs/three-round-60more-2026-10-25` | `three-round-training-2026-10-24/4-sixty-more-games` |
| `studies/campaign/runs/night-2026-10-30` | `training-2026-10-30` |
| `studies/campaign/runs/night-2026-10-30/training` | `training-2026-10-30/1-thirteen-games` |
| `studies/campaign/runs/night-2026-10-30/training-2` | `training-2026-10-30/2-eleven-games` |
| `studies/campaign/runs/night-2026-10-30/training-3` | `training-2026-10-30/3-eleven-games-again` |
| `studies/campaign/runs/night-2026-10-30/training-4` | `training-2026-10-30/4-raider-fix` |
| `studies/campaign/runs/night-2026-11-02` | `training-2026-11-02` |
| `studies/campaign/runs/archive` | `retired-branch-bundle-2026-10-31` |
| `tmp/action-interface-2026-10-24` | `action-interface-2026-10-24` |
| `tmp/encoder-pass-2026-10-24` | `encoder-pass-2026-10-24` |
| `tmp/self-play-never-stops-2026-11-17` | `self-play-never-stops-2026-11-17` |
| `tmp/coordinator-rounds-2026-11-17` | `coordinator-rounds-2026-11-17` |
| `tmp/one-network-2026-11-17` | `one-network-2026-11-17` |
| `tmp/compiled-forward-2026-11-18` | `compiled-forward-2026-11-18` |
| `tmp/server-profile-2026-11-18` | `server-profile-2026-11-18` |
| `tmp/readout-fix-2026-11-18` | `readout-fix-2026-11-18` |
| `tmp/never-stops-gpu-2026-11-18` | `never-stops-gpu-2026-11-18` |
| `tmp/concurrent-games-2026-11-18` | `concurrent-games-2026-11-18` |
| `tmp/gpu-training-2026-11-18` | `gpu-training-2026-11-18` |
| `tmp/engine-profile-2026-11-19` | `engine-profile-2026-11-19` |
| `tmp/concurrent-cpp-2026-11-19` | `concurrent-cpp-2026-11-19` |
| `tmp/search-cpp-2026-11-19` | `search-cpp-2026-11-19` |
| `tmp/training-2026-11-19` | `training-2026-11-19/1-first-night` |
| `tmp/training-2026-11-20` | `training-2026-11-19/2-morning` |
| `tmp/training-2026-11-20b` | `training-2026-11-19/3-afternoon` |
| `tmp/training-2026-11-20c` | `training-2026-11-19/4-choice-b` |
| `tmp/training-2026-11-21` | `training-2026-11-19/5-restart` |
| `tmp/diagnosis-2026-11-21` | `memory-check-2026-11-21` |
| `tmp/diagnosis-2026-11-21/run` | `memory-check-2026-11-21/1-two-processes` |
| `tmp/diagnosis-2026-11-21/run-one-process` | `memory-check-2026-11-21/2-one-process` |
| `tmp/diagnosis-2026-11-21/run-seven-games` | `memory-check-2026-11-21/3-seven-games` |
| `tmp/diagnosis-2026-11-21/run-fourteen-games` | `memory-check-2026-11-21/4-fourteen-games` |
| `tmp/diagnosis-2026-11-21/run-large-quarantine` | `memory-check-2026-11-21/5-quarantine-4gb` |
| `tmp/diagnosis-2026-11-21/run-quarantine-2gb` | `memory-check-2026-11-21/6-quarantine-2gb` |
| `tmp/diagnosis-2026-11-21/run-quarantine-1gb` | `memory-check-2026-11-21/7-quarantine-1gb` |
