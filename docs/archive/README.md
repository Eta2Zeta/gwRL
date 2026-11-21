# Archive

History, kept for looking things up. Nothing here is needed to understand the
program as it is now; for that, start at the [documentation guide](../README.md).
Every page describes the code, settings and paths of its own date, and its open
questions and next steps are those of that date.

| Part | What it holds |
| --- | --- |
| [Dated records](#dated-records) | One page per measurement, experiment or rule change since 24 October 2026, each with its data file. |
| [Milestone pages](#milestone-pages) | The delivery reports of the engine's twelve build stages, M0 to M11, from October 2026, and the source reviews made with them. |
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
| 14 Nov | [Does self-play learn three-round games?](records/three_round_training_2026_11_14.md) | 792 games on the PC taught the value heads the average scores, but no alliance played clearly better than the scripted policy; the untrained Axis, which with the noise off does almost nothing, scored best. |
| 17 Nov | [One network for the three alliances, against three](records/one_network_comparison_2026_11_17.md) | Matched Mac runs of 3.7 hours: one network played 21.6% more decisions an hour; its value head explained about as much of the final scores' variance on each new game, 15.4% against 13.1%, but its action probabilities fit its searches less well, a KL divergence of 0.273 against 0.252; the two runs' held-out games scored alike, and both trained Axis networks about 33 points below the untrained, nearly passive one. |
| 18 Nov | [Decision 612's path to its values](records/value_path_2026_11_18.md) | The 5 November game replayed to decision 612: the numbers of every step from the Comintern network's feature values to its three values, 0.251, −0.424 and −1.024. |

### The network's input

| Date | Record | What it found |
| --- | --- | --- |
| 2 Nov | [A fixed zone encoding of campaign decisions](records/zone_encoding_2026_11_02.md) | 37 zones answer fixed questions; 49 to 64 times smaller and 5 to 6 times faster to build than the graph input it replaced. |
| 2 Nov | [The network reads the zone encoding](records/zone_network_2026_11_02.md) | A forward pass 7.4 times faster and a training step 43 times faster on the same positions. |
| 4 Nov | [Railroads named by their border, and repairs encoded](records/rail_repair_encoding_2026_11_04.md) | One railroad per border (RCL-019), so a railroad is named by its two zones. |
| 4 Nov | [Every name the engine writes gets a question](records/zone_names_2026_11_04.md) | The names missing from the input's lists, found and fixed. |
| 5 Nov | [The name check's early phase ends](records/zone_name_check_early_end_2026_11_05.md) | The check never ended a phase early; fixed, and the more varied games found upgrades aboard transports. |
| 15 Nov | [Which questions random games answer](records/answer_census_2026_11_15.md) | 480 random games answered 5,811 of the input's 59,235 questions and 290 of its 8,902 questions about marks; the engine writes 43 of the input's 119 marks on a nation, and four that the input does not list; Mongolia was recorded as the invader of China in 70 games and each time came to be at war with the CCP; once the CCP had units again, the KMT was not offered an attack on Mongolia in 43. |

### Speed

| Date | Record | What it found |
| --- | --- | --- |
| 4 Nov | [Where self-play time goes](records/search_replays_2026_11_04.md) | The coordinator was busy 92% of the time; a search played 75 to 133 moves again on copies. |
| 4 Nov | [The search keeps a copy of the game at every tree position](records/search_copies_2026_11_04.md) | Identical results with 59% fewer moves played; 184 games per hour instead of 152. |
| 4 Nov | [The coordinator's column lookups](records/coordinator_lookups_2026_11_04.md) | The lookups were 22% to 49% of the network's forward pass; a fused replacement measured. |
| 12 Nov | [The fused column lookup, in the code](records/coordinator_lookups_2026_11_12.md) | Identical outputs; decisions per hour rose 17.6% in matched batches. |
| 13 Nov | [Where the game processes' time goes](records/game_processes_2026_11_13.md) | Playing a move and listing the legal moves cost about a millisecond each, two thirds of the game threads' CPU. |
| 14 Nov | [Supply answers cached while a move is played](records/supply_cache_2026_11_14.md) | Identical play; playing a move costs 42% less CPU and a game process 16% less per decision, but decisions per hour rose only about 3%: the coordinator now limits self-play. |
| 14 Nov | [One network pass per coordinator round](records/coordinator_one_pass_2026_11_14.md) | A pass cost about 0.4 ms whatever its size; one pass for all three networks makes a round 32% cheaper with the same replies, and decisions per hour rose 13% in matched batches. |
| 14 Nov | [What a larger network and a longer search cost](records/network_and_search_cost_2026_11_14.md) | Networks from 64×2 to 512×16 on one core, four threads and the GPU, and searches of 64 to 1,024 simulations: the GPU pays only with many positions per pass, a simulation costs about the same CPU at any budget, and a tree holds about 0.17 to 0.25 MB per simulation. |
| 15 Nov | [Training within nine cores](records/nine_core_layouts_2026_11_15.md) | Seven game processes fit the supervisor's count of 9 cores but kept about 10 busy; six kept about 9 and played about 192,000 decisions an hour, a quarter fewer than eight under the 12-core allowance. |
| 16 Nov | [What limits self-play within nine cores](records/self_play_limits_2026_11_16.md) | The 9 cores are full and the game processes do 90% of the work, 80% of it in the engine, where comparing names, allocating and copying take 59%; the coordinator, busy 90%, caps what a faster engine alone can add at 12% to 40%; the Mac's other work pushed 27% to 29% of the game processes' time onto efficiency cores. |
| 16 Nov | [Playing a move without checking it twice](records/move_checks_2026_11_16.md) | Identical play in 300 random games; playing a move takes 29% fewer instructions, and game processes 10.6% fewer per decision in training batches, but with a quiet Mac the coordinator set the pace and decisions per hour did not rise. |
| 16 Nov | [The naval-route and landing checks](records/naval_route_checks_2026_11_16.md) | They spend most of their time on copies of the position, each working out supply and the carriers' reach again; the one exact saving, a ship's allowance worked out once for all destinations, cuts 1% of a searched game's instructions. |
| 16 Nov | [Zones held as numbers](records/zone_numbers_2026_11_16.md) | Identical play in 300 random games and 4 searched games; listing a position's moves takes 13.0% fewer instructions and a searched game 7.2% to 7.9% fewer. |
| 16 Nov | [Nations held as numbers](records/nation_numbers_2026_11_16.md) | Identical play again; after zones, listing the moves takes a further 6.6% fewer instructions and a searched game 3.9% to 4.7% fewer, 11.6% fewer than before either change. |
| 16 Nov | [Unit types held as numbers](records/unit_type_numbers_2026_11_16.md) | Identical play again; after nations, listing the moves takes a further 4.7% fewer instructions and a searched game 2.5% fewer, 13.8% fewer than before any of the three changes. |
| 16 Nov | [Marks held as numbers](records/mark_numbers_2026_11_16.md) | Identical play again (after fixing a bug the check caught); after unit types, listing the moves takes a further 9.0% fewer instructions and a searched game 4.9% fewer, 18.1% fewer than before any of the four changes. |
| 16 Nov | [Facility types and technologies held as numbers](records/facility_type_numbers_2026_11_16.md) | Identical play again; after marks, listing the moves takes a further 14.0% fewer instructions and a searched game 4.0% fewer, 21.4% fewer than before any of the five changes; the build menu's factory capacity check, which copied every mark by name, fell from 5.0% to 0.4% of a searched game's engine samples. |
| 16 Nov | [Units and facilities in slot maps](records/slot_maps_2026_11_16.md) | Identical play again, also in a build that throws when a map changes while iterated; listing the moves takes a further 5.6% fewer instructions and a searched game 3.2% fewer, 23.9% fewer than before the names work. A first version that searched names in name order made listing the moves 6.7% dearer. |
| 16 Nov | [A planning key from a binary writing of the position](records/planning_key_2026_11_16.md) | Identical play with positions compared by canonical key; playing a move takes 31% fewer instructions and rolling dice 39% fewer, a searched game 5.5% fewer and 27.8% fewer than before the names work; the key was 15.6% of the engine's samples. |
| 16 Nov | [The faster engine in training batches](records/engine_speed_in_training_2026_11_16.md) | Two matched pairs against the engine before the names work: decisions per hour while playing up 26% (239,000 to 301,000), game processes' CPU per decision down 43%; the coordinator, busy 96%, now limits and the training keeps only about 7 cores busy. |
| 17 Nov | [The PyTorch calls of a network pass](records/pass_calls_2026_11_17.md) | A pass of the 64×2 network is 146 calls on one core for one alliance's positions and 258 for all three's, 426 to 871 at 512×16; a message layer is 20 calls for one alliance's positions and 42 for all three's. A call starts in at most about 2 µs on one core; on the GPU the coordinator takes about 5.6 µs to make each, about two thirds of a 64×2 pass. |
| 17 Nov | [Where a coordinator round's time goes](records/coordinator_rounds_2026_11_17.md) | A profiled Mac batch: passes two thirds of the coordinator's time, laying positions out 13%, waiting 9%; 43% of its busy time arithmetic, 31% Python's and PyTorch's own work. The batch's longest game played alone for the last tenth of its playing time, about 9% of decisions an hour. 853 saved rounds replayed on one core and the GPU at three sizes: making the calls is about half of a GPU round as saved; half precision was 5% to 23% slower and the pass compiled as written never faster. |
| 17 Nov | [Self-play that never stops](records/self_play_never_stops_2026_11_17.md) | Two matched pairs of Mac runs of four network updates: 6.5% and 12.5% more decisions per wall-clock hour in steady play than alternating training iterations; inference batches of 10.5 states against 8.5; while a network update runs beside the games the inference server answers about 29% fewer evaluations a second. |
| 17 Nov | [One call per layer for the three networks, tried and removed](records/grouped_layers_2026_11_17.md) | A grouped matrix product (`torch._grouped_mm`) cut a three-alliance forward pass of 64×2 from 258 PyTorch calls to 176 with equal replies, but real inference batches on one core were no faster (1%), and on the Mac's GPU the grouped product is twice as slow as the split; a call overhead on one core is about 0.7 µs. |
| 17 Nov | [What evaluating three networks costs, and a padded product](records/network_split_2026_11_17.md) | The Axis decides at 66% of the states, so padding the three networks to one product would double the states; a stand-in for it was faster than today's forward pass only in small inference batches and up to 66% slower at 119 states. The same states through one network took 15% less time on one core and 15% to 38% less on the Mac's GPU. On the GPU the matrix products are 41% to 45% of a forward pass's time; at 512×16 the per-border message work is 28% to 32%. |
| 18 Nov | [Compiling one network's zone and position layers](records/compiled_forward_2026_11_18.md) | A layout keeping each state's zone vectors together gives the earlier outputs, exactly on one core, at about the earlier speed; those layers compiled for fixed numbers of states (`--compiled-forward`) took 6% to 9% less time than as written on the Mac's GPU at 256×8 and 512×16 with about 9 states and 21% to 24% with about 60, but were 9% slower on the GPU at 64×2; compiled code slowed the GPU's other work in the same process; compiling took 17 to 36 seconds on the GPU with PyTorch's cache empty. |
| 18 Nov | [Compiled zone and position layers in GPU training runs](records/gpu_training_compiled_2026_11_18.md) | Two matched pairs of training iterations at 256×8 on the Mac's GPU: 4.6% more decisions an hour with `--compiled-forward` on average, within the 5% to 6% between two runs of one setting, so no gain established; the inference server was busy 98% with about 24 states an inference batch; the 63 games' uneven ends cost 10% to 14% of the decisions an hour. |
| 18 Nov | [Concurrent games at 256×8 on the GPU](records/concurrent_games_gpu_2026_11_18.md) | One training iteration each with 63 and 126 concurrent games on the Mac's GPU: 126 played 33% more decisions an hour, through inference batches of 48 states instead of 25.5 that cost the inference server 26% less time a state; it stayed busy 98%, the game processes kept 6.2 CPU cores busy instead of 4.4 and waited for a core as long as they computed, and memory rose from 8.0 GB to 12.5 GB; the inference server's time by inference batch size. |
| 18 Nov | [What a training run holds in memory](records/memory_in_training_2026_11_18.md) | Two checkpoints measured: the learner keeps an event for every transition of every game, about 2.0 GB of memory and 626 MB of the checkpoint after the 997 games of the night of 17 November, and never drops one; the replay buffer's 8,000 training samples took 133 MB; a concurrent game took about 70 to 85 MB at 64 simulations; worked out, 30 GB hold about 330 concurrent games at 64 simulations but 105 at 800 and 60 at 1,600. |
| 18 Nov | [Compiled layers with 126 concurrent games at 256×8](records/compiled_layers_126_games_2026_11_18.md) | One training iteration with `--compiled-forward` between two with the layers as written, 126 concurrent games on the Mac's GPU: inference batches of 40 to 80 states took 8% to 12% less time, where the two runs as written differed by 4%, and the compiled run played 7.9% more decisions an hour while playing than their mean and 11.2% more while all the games played, against a 6% spread between them; the inference server stayed busy 98%, with the CPU cores about an eighth behind. |
| 18 Nov | [Self-play that never stops on the GPU](records/never_stops_gpu_2026_11_18.md) | Tests on the Mac's GPU with PyTorch 2.14: a training thread beside forward passes is safe as written, but a synchronize or cache release beside it aborts the process and compiled forward passes beside it deadlock it. With those held back during network updates, one run at 256×8 with 126 concurrent games in 6 processes of 21 answered 8.7% more network evaluations per wall-clock second than alternating training iterations at the same layout, which differed by 8% between themselves; its network updates took about 115 seconds beside self-play against 35 alone. |
| 18 Nov | [Where the inference server's time goes at 256×8 on the GPU](records/inference_server_profile_gpu_2026_11_18.md) | A profiled training iteration with 126 concurrent games and the compiled layers: an inference batch of 45 states took 11.2 ms, against 6.7 ms replayed alone; about 23% of the inference server's time went to the GPU's graph framework compiling graphs for shapes that follow each inference batch's legal actions, 71% to 79% of it for one `Tensor.repeat` in the policy readout and about a fifth for matrix products on the actions' vectors. |
| 18 Nov | [The policy readout without a repeat, in training at 256×8 on the GPU](records/readout_without_repeat_2026_11_18.md) | Replacing the repeat by one `index_add_` a level gave identical replies on one CPU core and replies within float rounding on the GPU; in profiled training iterations with 126 concurrent games an inference batch of steady play took about 23% less time, compiling fell from about 23% to 6% of the inference server's time, and the run played 29.4% more decisions an hour while playing, but the game processes then kept about 8 to 9 CPU cores busy and the run a median of 9.5, over the 9-core allowance. |
| 19 Nov | [Where the game processes' time goes at 256×8 on the GPU](records/game_processes_gpu_2026_11_19.md) | A profiled training iteration with 126 concurrent games on `673076c`: a network evaluation costs a game thread 1.71 ms of CPU, 0.89 ms in engine calls (listing legal actions 0.46 ms), 0.22 ms encoding the state and 0.59 ms in Python, through 27 engine calls, 12.5 of them for the planning key; a game thread computes about a tenth of its time and waits for Python's lock about 56%; inside the engine 30% is the rules' own code and 65% allocation, strings, memory copies and map lookups. |
| 19 Nov | [The search in C++ in training at 256×8 on the GPU](records/search_in_cpp_2026_11_19.md) | Two matched pairs with 126 concurrent games, before and after the C++ search: 12.5% and 16.8% more decisions an hour while playing, the game processes' CPU per network evaluation 0.97 ms instead of 1.62 ms, a median of 6.5 CPU cores busy instead of 9.3 to 9.5, and the inference server, busy 97%, setting the pace alone; a profiled run splits the search's CPU into listing legal actions 0.38 ms, encoding 0.17 ms, playing an action 0.17 ms and copying 0.10 ms, and its game threads no longer wait for Python's lock. |
| 19 Nov | [Concurrent games at 256×8 on the GPU with the C++ search](records/concurrent_games_cpp_search_2026_11_19.md) | 189 and 252 concurrent games against 126: 527,401 and 556,581 decisions an hour while all the games played against about 470,000, the inference server busy about 97% throughout with inference batches of 68 and 95 states, a median of 7.4 and 7.85 CPU cores busy and 12.2 and 13.5 GB; 378 games did not fit beside the Mac's other programs: one run filled the Mac's memory together with another program, and a second swapped and played about 10% slower than 252 (inferred), so 252 played the most. |
| 20 Nov | [A game process that crashed in a long training run](records/game_process_crash_2026_11_20.md) | After 5.13 hours of the long run of 252 concurrent games from `999c90c`, a game process aborted when macOS's allocator found that memory being freed had not been allocated, while freeing a game's kept search tree just after the game raised an error; the training process then exited, the supervisor did not retry, a shell loop restarted the run from the checkpoint of the last network update, and the next update came about 51 minutes late (inferred). |
| 20 Nov | [A second game process crash, survived by replacing the process](records/second_game_process_crash_2026_11_20.md) | After 3.86 hours of play in the long run from `7adac20`, whose engine and search are those of `999c90c`, a game process aborted with the same allocator message while the search freed nodes of a game's tree it did not keep, in a unit's state; two of that process's games had just failed the engine's state check with a zone number that names no zone; a new process took its game slots, the run lost 44 games, about 7 minutes of its play (inferred), and did not stop; two crashes in 16.6 hours of 252 games with the search in C++. |
| 20 Nov | [A third game process crash, survived by replacing the process](records/third_game_process_crash_2026_11_20.md) | After 7.56 hours of play in the same run, a second game process aborted with the same allocator message while the search freed nodes of a game's tree it did not keep, in a game state; no game of that process had failed; a new process took its game slots and the run lost 42 games, about 6 minutes of its play (inferred); three crashes in 18.4 hours of 252 games with the search in C++, about one every 6 hours. |
| 20 Nov | [The training process's memory in a long training run](records/training_process_memory_2026_11_20.md) | In self-play that never stops the training process grew by about 1.25 GB an hour, in Python objects that nothing read: the shared game loop kept every finished game's result, about 4 MB a game (inferred), for as long as the run played; the run's highest minute, during network updates, rose to 23.18 GB, and without the fix it would reach the supervisor's 29 GB stop at about 09:00 to 10:00 (inferred). |
| 20 Nov | [How the long run's network fits its replay buffer and new games](records/replay_buffer_fit_2026_11_20.md) | Over the 26 network updates of the long run's three runs, 6,552 games: the value loss on new games explained 3% to 30% of the final scores' variance in the first night and 17% to 30% since 05:00 on 20 November, with no trend; within each network update the network fit the latest 110 or so games in its replay buffer a median of 3.3 times better, by value loss, than the games it played next; each network update's 252 games kept about 18,300 training samples for a replay buffer of 8,000, so more than half were never drawn (inferred). |
| 21 Nov | [A fourth game process crash, survived by replacing the process](records/fourth_game_process_crash_2026_11_21.md) | After 1.59 hours of play in the run with 1% of decisions kept and a replay buffer of 25,000 (Q-013), whose engine and search are those of the earlier crashes, a game process aborted with the same allocator message while the search freed nodes of a game's tree it did not keep, in a game state's build projects; no game had failed; a new process took its game slots and the run lost 42 games, about 5 minutes of its play (inferred); four crashes in 28.1 hours of 252 games with the search in C++, about one every 7 hours. |
| 21 Nov | [A fifth game process crash, survived by replacing the process](records/fifth_game_process_crash_2026_11_21.md) | After 6.11 hours of play in the same run, a second game process aborted with the same allocator message while the search freed nodes of a game's tree it did not keep, in a unit's state; no game had failed the state check; a new process took its game slots and the run lost 42 games, about 4 minutes of its play (inferred); five crashes in 32.6 hours of 252 games with the search in C++, about one every 6.5 hours. |

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

Some stages left reviews of the printed sources beside their report. They are
dated like the reports and are kept with them:

| Review | What it checked |
| --- | --- |
| [Japan setup audit](milestones/m0/japan_setup_audit.md) | Japan's starting pieces, read from its national sheet |
| [China and minor setup audit](milestones/m0/china_minor_setup_audit.md) | The starting pieces of the KMT, the CCP, the warlords and Mongolia |
| [Asset price audit](milestones/m0/asset_price_audit.md) | Purchase and repair prices of every type |
| [Source reconciliation](milestones/m0/source_reconciliation.md) | The payments on Japan's starting ship queues and the research chart |
| [Convoy audit](milestones/m0/convoy_audit.md) | The printed convoy lines in the six sea zones, which the campaign leaves out |
| Source coverage of the [catalog](milestones/m3/source_coverage.md), [politics](milestones/m4/source_coverage.md), [movement](milestones/m5/source_coverage.md) and the [economy](milestones/m6/source_coverage.md) | Which printed pages stand behind each module's rules |
| [Frozen baseline](milestones/m0/frozen_baseline.json) | The hashes of the campaign's files when its specification was frozen on 21 October 2026 |

The data these reviews checked is current and is described in
[Rules and data](../rules/README.md), as are the rules ledger and its evidence
index.

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
