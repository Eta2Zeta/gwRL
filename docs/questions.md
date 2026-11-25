# Questions waiting for a decision

Some things found while working on gwRL can only be settled by the project's
owner: a printed rule that can be read two ways, a choice between two designs,
a problem that was found and left alone on purpose. Each is written here as a
question, in full, so that it can be answered from this page without reading
code.

## How this page is kept

- **A question is written here in the commit of the work that found it.** A
  chat reply, a commit message or a file outside the repository is not enough.
- **Each entry says** what the program does now, with a real case; why it
  matters; the choices and what each would change; and a recommendation, marked
  as one.
- **An answer is carried out and then recorded where it belongs:** in the page
  that describes the thing it changes, and, for a ruling on a printed rule, as
  a numbered entry in the
  [rule clarifications](../game_content/rules/clarifications.md). The entry
  here then shrinks to one line under [Answered](#answered).
- **A number is never used twice,** so that a reply, a commit or a comment in
  the code can name a question.
- **Every statement names its source:** a printed rule by its section and
  page, the engine by its function and file, a scenario choice by the page that
  records it, and a number by the dated record in the
  [archive](archive/README.md) that says how it was measured.

Other open things stay in the pages that own them, and
[Open elsewhere](#open-elsewhere) lists them.

## Open questions

No question waits for an answer now.

## Open elsewhere

These are open too, and stay in the pages that own them:

- **Printed rules waiting for the game's developers:**
  [RCL-010](../game_content/rules/clarifications.md#rcl-010-dadao-home-country-destination-for-japanese-lend-lease),
  where Japanese lend-lease to Dadao may be delivered, and
  [RCL-015](../game_content/rules/clarifications.md#rcl-015-neutral-relocation-with-no-friendly-destination),
  what happens to neutral units with no friendly land to go to. Both have a
  reading adopted for now.
- **What is not built or not measured yet:**
  [open work](plans/japan_china_full_rules_plan.md#5-open-work) on the campaign
  and [known gaps](design/README.md#known-gaps) of the learning system.
- **Design choices that need an experiment, not a ruling:** the
  [open design questions](design/README.md#open-design-questions), such as
  whether the final wealth gap is the right goal.
- **What on the world map is uncertain:**
  [open items](map_audits/full_world/uncertain.md).

## Answered

An answered question is listed here with its number, the answer, the date and
the page that now states it.

- **Q-001**, Mongolia at war with the CCP. Answered on 22 November 2026 by the
  game's developers, as the owner reported: Mongolia may attack land that was
  originally a warlord's, the CCP's or the KMT's, and the attack puts it at war
  with every Chinese nation outside its own alliance, so never with the CCP; a
  nation of the Allies that attacks such land in the full game is never put at
  war with the KMT. It replaces the owner's answer of 19 November 2026, to
  follow the printed rules for now, under which Mongolia could never make the
  attack. Stated in
  [rule clarification RCL-022](../game_content/rules/clarifications.md#rcl-022-an-attack-on-land-that-was-chinese-at-the-start)
  and [the politics page](engine/politics.md#invading-china).
- **Q-002**, Chinese land that Japan holds. Answered on 19 November 2026, and
  kept by the developers' answer of 22 November: the printed owner decides, so
  an attack on such land is an attack on China whoever holds it. Stated in the
  same two places.
- **Q-003**, one list of marks for each kind of thing. Answered on 18 November
  2026: yes, with the four bombing-reduction marks added. The engine's mark
  table now says which kinds of thing the rules put each mark on, and the input
  asks about a mark only there. Stated in
  [the network's input, section 8](design/network_input.md#8-features-removed-as-impossible)
  and [names held as numbers](engine/names.md#what-a-mark-is).
- **Q-004**, features whose value never changes. Answered on 18 November 2026:
  remove them, and the `player` family with them; the encoder reports a
  position that breaks one. Stated in
  [what the global features ask about a nation](design/network_input.md#what-the-global-features-ask-about-a-nation).

- **Q-006**, the KMT after the CCP comes back. Answered on 21 November 2026:
  the printed words decide, so once the CCP has been eliminated the KMT may
  attack warlords and Mongolia for the rest of the game, even after the CCP
  has units again. Stated in [the politics page](engine/politics.md#1-war)
  and [the archived source checks](../game_content/rules/source_answered_questions.md).
- **Q-007**, self-play stopping at each training iteration's end. Answered on
  17 November 2026: self-play never stops; network updates run beside the games.
  Stated in [the training loop](design/README.md#91-the-training-loop) and
  [running training on the Mac](design/README.md#92-running-training-on-the-mac).
- **Q-008**, when self-play takes up new networks. Answered on 17 November 2026:
  every game at once, between two inference batches. Stated in
  [the training loop](design/README.md#91-the-training-loop).
- **Q-009**, one network for the three alliances. Answered on 17 November 2026:
  build it as a mode and compare it with three networks in matched runs, then
  keep it if it learns at least as well. Stated in
  [one training step](design/README.md#84-one-training-step-and-one-network-update);
  the runs are in the
  [record of the comparison](archive/records/one_network_comparison_2026_11_17.md).
- **Q-010**, one network for the three alliances by default. Answered on 18
  November 2026: yes, although its action probabilities fit its searches
  slightly less well; `--networks three` keeps a network for each alliance.
  Stated in
  [one training step](design/README.md#84-one-training-step-and-one-network-update)
  and [known gaps](design/README.md#known-gaps).
- **Q-011**, the memory the rest of the Mac uses. Answered on 20 November
  2026: on macOS the supervisor also asks a run to stop safely when the Mac's
  memory pressure stays critical for 10 seconds or the swap in use grows by
  4 GB after the training process starts, and it keeps the run's own limit of
  30 GB. Stated in
  [long unattended runs](../studies/campaign/README.md#long-unattended-runs)
  and [running training on the Mac](design/README.md#92-running-training-on-the-mac).
- **Q-012, first part**, a game process that crashes. Answered on 20 November
  2026: training loses only the games that process had not finished and goes
  on, with a new game process in its game slots; whether to pause training to
  look for the defect stays open as Q-012. Stated in
  [running training on the Mac](design/README.md#92-running-training-on-the-mac)
  and [long unattended runs](../studies/campaign/README.md#long-unattended-runs).
- **Q-012, keeping a failed position**. Answered on 20 November 2026: a move
  that the engine accepted and then failed on, in the game or in the search,
  keeps the position before it and the move, which the game process writes at
  once, and `tools/replay_failed_move.py` replays it. Stated in
  [running training on the Mac](design/README.md#92-running-training-on-the-mac).
- **Q-012**, looking for the defect behind the game process crashes. Answered on
  21 November 2026: yes. Training stopped from 07:40 that day; the five crash
  reports, the code and about 29,000 decisions under ThreadSanitizer and
  AddressSanitizer found no defect
  ([record](archive/records/crash_diagnosis_2026_11_21.md)). The training build
  now keeps two checks that stop an out-of-bounds index or a stale SlotMap
  iterator where it happens, and a run keeps each game's move log, the crash
  report and the allocator's message for the next crash. Stated in
  [running training on the Mac](design/README.md#92-running-training-on-the-mac)
  and [known gaps](design/README.md#known-gaps).
- **Q-013**, how many games a network update learns from. Answered on 20
  November 2026: choice B, so training keeps 1% of each game's decisions as training samples and 25,000 in its replay buffer, those of about 1,700 games,
  instead of 5% and 8,000, those of about 110
  ([record](archive/records/replay_buffer_fit_2026_11_20.md)). Stated in
  [how often a training sample is drawn](design/README.md#87-how-often-a-training-sample-is-drawn)
  and [training on the Mac](../studies/campaign/README.md#training-on-the-mac).
- **Q-014**, a land battle that no unit can end. Answered on 22 November
  2026: when no unit of either side could roll a die in the next combat round,
  the attacker retreats as its only action, and its units with nowhere to go,
  those that came from the sea or by air drop and land units with no Friendly
  zone to go back to, are eliminated; a retreat by choice that leaves only such
  units eliminates them at once. In the case that raised it, Japan's
  Anti-aircraft Artillery landed from the sea is eliminated when Japan's
  Self-propelled Artillery retreats, and the KMT keeps Manchuria-Rehe
  ([record](archive/records/land_battle_without_end_2026_11_20.md)). Stated in
  [rule clarification RCL-023](../game_content/rules/clarifications.md#rcl-023-a-land-battle-that-no-unit-can-end)
  and [the land combat page](engine/land_combat.md#2-a-battle-one-combat-round-at-a-time).
- **Q-015**, the weight of the value loss. Answered on 21 November 2026: test it
  first on the training samples saved by the training run of 19 to 21 November. Trained from generation 3 on
  1,324 saved games at weights 1, 10, 50 and 200, no weight above 1 predicted 330
  held-out games better; every copy did best after drawing each training sample
  once or twice and then fit its training games instead
  ([record](archive/records/value_loss_weights_2026_11_21.md)). So the loss stays
  as it is. Stated in [the loss](design/README.md#81-the-loss).
- **Q-016**, how self-play spends its searches and plays its moves. Answered on
  22 November 2026: choice D. Whether a decision is kept as a training sample is
  drawn before its search; a kept decision is searched with 256 simulations and
  exploration noise, any other with 16 and none; self-play draws its move from
  the visit shares in game round 1 and plays the most visited action after it;
  and held-out evaluation plays 24 seeds instead of 6. In the training run of 19 to 21 November, which drew every move, 63% of the searched decisions played an action other than
  the most visited one, and 99 of every 100 searches kept no training sample
  ([record](archive/records/long_run_samples_2026_11_21.md)). Stated in
  [the move played](design/README.md#45-after-the-simulations-visit-shares-and-the-move-played),
  [which decisions are kept](design/README.md#71-a-training-iterations-games),
  [measuring strength](design/README.md#10-measuring-strength) and
  [training on the Mac](../studies/campaign/README.md#training-on-the-mac).
- **Q-017**, which network the training run started on 22 November 2026 begins
  from. Raised and withdrawn on 22 November 2026, before an answer. The run's
  first 80 games, from a fresh network playing as choice D of Q-016 says, were
  narrow: a median of 502 decisions a game against 1,048 in the first games of
  the training run of 19 to 21 November, 39% of the actions ending a phase
  against 18%, and 7.8 land battles a game against 44.2; starting the run
  instead from the newest network of the training run of 19 to 21 November was
  recommended. By its network updates 56 to 69 the run's games had widened by
  themselves: a median of 694 decisions, 28% of the actions ending a phase, and 201 moves of a land unit a game against 54 at first, though still about 10 land
  battles a game ([record](archive/records/fresh_network_games_2026_11_22.md)).
  So the run goes on from the fresh network, as the owner chose.
- **Q-021**, where to run training at AlphaZero's and KataGo's scale. Answered
  on 24 November 2026: on the Mac (choice A), after "a few more rounds of
  optimization of the runs so that things are going as fast as it gets with
  limited compute we have here". Stated in the design document's
  [open question on sizes](design/README.md#how-big-should-the-network-and-the-search-be).
- **Q-020**, what to change in training first. Answered on 24 November 2026:
  none of the proposed checks. The owner holds that "coordinated attacks
  against china with no consequence is obvious going to get japan more reward",
  and that the small networks and searches of the runs so far could never learn
  them: training is to be sized to AlphaZero's and KataGo's scale, from a
  comparison of this game with theirs, and judged by steady gains over
  continuous training rather than by speed. Stated in the design document's
  [open questions](design/README.md#how-big-should-the-network-and-the-search-be);
  where to run it is Q-021, above.
- **Q-018**, how to go on looking for the game process crash. Answered on 24
  November 2026: stop looking, and train at full speed, crashes and all
  (choice C). The memory-checked part of the training run under the
  land-weighted score stopped at 10:40 after 637 network updates and 38.4 hours
  with no memory-checker report, where at the crash rate of the training run of
  19 to 21 November a report had a chance of 0.82 by its 595th network update
  ([record](archive/records/training_land_weighted_update_595_2026_11_24.md#the-memory-check)). The full-speed part, started at 10:42, was
  stopped at 11:01 at the owner's word, before its first network update, for
  the training itself to be looked at first (Q-020). Stated in the
  [known gaps](design/README.md#known-gaps) of the design document and the
  [list of runs](archive/runs.md).
- **Q-019**, two attacks on one land zone by Japan and Dadao. Answered on 24
  November 2026: no. Of the nations that share a Player Turn, a controlled
  minor power and the major power that controls it, only the first to attack
  a land zone may attack it in that turn, in any way, and an aircraft supports
  only a battle of its own nation. In the case that raised it, game 5967 of
  the training run under the land-weighted score, once Japan had declared its
  assault on Manchuria-Rehe, Dadao could no longer attack Rehe that turn
  ([record](archive/records/japan_dadao_one_zone_2026_11_23.md)). Stated in
  [rule clarification RCL-024](../game_content/rules/clarifications.md#rcl-024-two-attacks-on-one-land-zone-by-a-controlled-minor-power-and-its-controller)
  and [the politics page](engine/politics.md#one-attacker-for-each-land-zone).
- **Q-022**, whether self-play's search chooses the paths of 8 simulations
  before it asks the inference server about the states where they stopped, all
  in one inference request. Answered on 25 November 2026: yes, 8 (choice B),
  AlphaGo Zero's size. With inference batches overlapped on the GPU and 30
  concurrent games, it took self-play at 256×16 with KataGo's search from 2,761
  to about 7,600 network evaluations a second between network updates
  ([record](archive/records/self_play_speed_256x16_2026_11_24.md)). Stated in
  [section 4.7 of the design document](design/README.md#47-more-detail-on-the-search);
  training runs take `--simulations-per-request 8`.
- **Q-023**, whether a fast search, at a decision not kept as a training
  sample, counts the visits its root holds from the reused tree toward its 150
  simulations. Answered on 25 November 2026: yes, the fast searches only
  (choice C); a full search, whose visit shares are the training target, still
  runs its 800 new simulations. Along two games with a stand-in network the fast
  searches then asked for 82 network evaluations on average instead of 150, and
  the searches together for about 14% fewer
  ([record](archive/records/reused_visits_counted_2026_11_25.md)). Stated in
  [section 4.7 of the design document](design/README.md#47-more-detail-on-the-search).
- **Q-005**, the supervisor's count of cores. Answered on 25 November 2026:
  choice D, measure and warn. While a run plays, the supervisor measures the CPU
  cores its processes use in each minute, keeps the median of the last ten
  minutes in its status file and warns when that median reaches 9 cores, the
  allowance of 8 since 21 November and the bit over it the owner accepts ("a bit
  over 8 is fine, as along as it doesn't go to 9", 25 November), without
  stopping the run; a layout that goes over is changed by hand. Before a run
  starts it still counts a core for each game process, the inference server,
  the network updates and itself. Raised on 15
  November, when six game processes of four games, which counted 9 cores, kept
  about 9 busy and seven about 10
  ([record](archive/records/nine_core_layouts_2026_11_15.md)); on 25 November
  six of five games at 256×16 kept a median of 8.3 busy under the allowance of 8
  ([list of runs](archive/runs.md), `training-256x16-2026-11-25`). Stated in
  the campaign learning guide's
  [long unattended runs](../studies/campaign/README.md#long-unattended-runs)
  and in [section 9.2 of the design document](design/README.md#92-running-training-on-the-mac).
