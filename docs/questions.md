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

| Number | Question | About | Recommended |
| --- | --- | --- | --- |
| [Q-005](#q-005-the-supervisors-count-of-cores) | Should the supervisor keep training within the 9 cores by measuring the load, not by counting game processes? | Running training | Yes: measure, warn, and stop a run that stays over |
| [Q-018](#q-018-how-to-go-on-looking-for-the-game-process-crash) | The memory-checked training has found nothing: go on as it is, look with ThreadSanitizer for a while first, or start the full-speed part now? | Running training | ThreadSanitizer for about 12 hours of play, then go on as now |

Q-005 was raised on 15 November 2026, when the allowance became 9 cores (commit
`e62e01b`). Its numbers are in the
[record of training within nine cores](archive/records/nine_core_layouts_2026_11_15.md).

Q-018 was raised on 22 November 2026, after the memory-checked first part of
the training run of 22 November had found nothing in 5.6 hours. Its numbers are
in the [record of that part](archive/records/memory_check_2026_11_22.md).

## Q-005: The supervisor's count of cores

**The question.** Should the supervisor keep a training run within the owner's
allowance of 9 cores by measuring the CPU its processes use, instead of
counting one core for each game process?

**What the supervisor does now.** Before it starts a run,
`tools/supervise_campaign_training.py` checks that the run fits the allowance by
counting: one core for each game process, one for the inference server and one for
itself (`validate_training_arguments`, and `busy_cores` in
`studies/campaign/run.py`). While the run plays it measures only memory: every
second it reads the process table and stops the run if the memory used comes
within 1 GB of 30 GB. But a game process plays four games, one on each of its
threads, and the engine releases Python's lock while it works, so the four
threads compute at the same time. A process keeps 1.2 to 1.5 cores busy, not
one ([running training on the Mac](design/README.md#92-running-training-on-the-mac)).

**A real case** (15 November 2026, one training iteration each, eleven-round games,
64 simulations, the 64×2 network on the CPU). Seven game processes of four
games count 7 + 1 + 1 = 9 cores, which the supervisor accepts. Measured every
five seconds, they kept 9.9 cores busy in a typical half minute and up to 11.1,
all ten of the Mac's performance cores. The Mac profile now runs six processes,
chosen by hand from these measurements, which kept about 8.9 cores busy that
day ([record](archive/records/nine_core_layouts_2026_11_15.md)). On 16 November,
with less other work on the Mac, about 2 cores instead of 3, the same six
processes kept 9.1 to 10.4 cores busy on average in four training iterations
([record](archive/records/move_checks_2026_11_16.md#training-batches)). The
layout's load grows into whatever cores are free. It also shrinks when the
engine gets faster: after the engine work later that day the same six
processes kept about 6.8 cores busy, the inference server setting the pace
([record](archive/records/engine_speed_in_training_2026_11_16.md)). A count sees neither. A command line that adds
`--episode-workers 7` overrides the profile, and the supervisor would accept it.

**A second case** (18 November 2026, the 256×8 network on the GPU, 126
concurrent games). Seven game processes of 18 games count 9 cores and kept a
median of about 7.7 busy in their half-minute windows. Once the inference server
had stopped making the GPU compile a graph for nearly every inference batch,
the same layout kept a median of 9.46 busy, and six processes of 21 games, which
count 9 with self-play that never stops, 9.5: the game processes did more
engine work each second because the inference server answered them sooner
([record](archive/records/readout_without_repeat_2026_11_18.md)). The supervisor
accepted both; two runs were stopped by hand. On 19 November the owner said that
going a little over the allowance, as these runs did, is fine, so this layout
stays and no smaller one is being sought. How far over is still a little is not
set, and a stop under choice A below would need that number.

**Why it matters.** The allowance is there to keep one performance core free
for everything else. The count does not show whether it is free, and even a
layout chosen by measuring it goes over when the Mac is quiet. A different network, device,
number of games per process or search would change the load without the
supervisor noticing, and so would a faster inference server, as in the second
case. The count can also be too strict: with the network on the GPU and a slow
inference server, game threads wait more and use less than they count.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Measure the load | The supervisor adds the processes' CPU time to the process table it already reads every second, and records the load over the last minute in its status file. A run that stays over the allowance, for example for five minutes, is stopped safely, as a requested stop is. Short peaks, such as starting up, stop nothing. The count stays as the check before a run starts. |
| B. Count better | Count a game process of four games as 1.5 cores instead of one. Checked before the run starts and simple, but the factor depends on the network, the device, the games per process and the Mac's other work, so it would need measuring again whenever those change. |
| C. Leave it | The count stays a rough check before a run starts, and layouts are chosen by measuring them, as on 15 November. A layout chosen by hand can pass the allowance unnoticed. |

**Recommendation: A.** It holds training to what the allowance means, whatever
the layout, and the supervisor already samples every process once a second.
Stopping only a run that stays over keeps a brief peak from costing a training iteration.

**If answered.** What the supervisor measures and when it stops a run belong in
the [campaign learning guide](../studies/campaign/README.md#long-unattended-runs)
and in [section 9.2 of the design document](design/README.md#92-running-training-on-the-mac).

## Q-018: How to go on looking for the game process crash

**The question.** Training plays with its game process on an engine built with
AddressSanitizer, to find the defect behind the game process crashes, and it has
found nothing. Should it go on as it is until AddressSanitizer reports, look
with ThreadSanitizer for a while first, or give way now to a full-speed part,
which would crash now and then?

**What the program does now.** The training run under the land-weighted score,
started on the evening of 22 November 2026, plays its first part,
`studies/campaign/runs/training-land-weighted-2026-11-22/1-memory-checked`, as
the training run of 22 November played its own: one game process of 16 games on
that engine built with AddressSanitizer, the checked engine, within the 8 CPU
cores and 16 GB
that the owner gave to looking for the defect on 21 November; the training
process and the inference server run the ordinary build on the GPU.
AddressSanitizer, the memory checker built into the checked engine, stops the game
process at the first write to freed memory, second free or out-of-bounds
access, and names the code that made it. The part also trains: once the defect
is found, its newest network is to start the full-speed part, six game
processes of 42 games on the ordinary engine, as the owner planned on 22
November. The part plays its own copy of the code, from 22 November. Since
RCL-024 (commit `c07d0f2`, 24 November) the network input of the current code
has 26 more features, and the part's networks do not load in it: the
full-speed part can start from the part's newest network only on the part's own
copy of the code, which keeps the two defects of the rules that each failed
one of its games (games 1316 and 5967, both fixed in the current code), or from
a fresh network on the current code.

**A real case.** By its 134th network update, at 17:35 on 22 November, the
memory-checked first part of the training run of 22 November had played 5.6
hours: 1,513,584 decisions and 2,144 games, about 270,000
decisions an hour, and the inference server had answered 20.7 million network
evaluations for it. AddressSanitizer wrote no report. Nor did it in the memory check
of 21 and 22 November, in 21.2 hours and 66.4 million network evaluations. The
training run of 19 to 21 November crashed once in about 128 million network
evaluations, all six times while the search freed the game copies that its
tree's nodes hold, work that grows with the network evaluations (inferred). So
if AddressSanitizer caught the defect as often as that run crashed, a report by
then was about as likely as not: 0.49
([record](archive/records/memory_check_2026_11_22.md)). That part stopped at
20:04, when the owner changed the final score, after 187 network updates with
no report, 0.53 by the same count. The memory-checked first part of the training
run under the land-weighted score then played 35.38 hours to its 595th network
update, at 07:39 on 24 November: 8,724,175 decisions, 9,520 games and 126.1
million network evaluations, with no report. With the 66.4 and 29.5 million
before it, that brings the chance of a report by then to 0.82; put the other
way, if AddressSanitizer caught the defect as often as that run crashed, seeing
no report by then had a chance of 0.18
([record](archive/records/training_land_weighted_update_595_2026_11_24.md#the-memory-check)).
Two games of that part failed, at 00:19 and at 20:07 on 23 November, each on a
defect of the rules, not on damaged memory; both defects are now fixed, the
second by the answer to Q-019 ([answered](#answered)), though the part runs
on with its own copy of the code.

**Why it matters.** The full-speed part waits until the defect is found, and it would play
several times as fast as this part: the training run of 19 to 21 November did
about 21.6 million network evaluations an hour, 5.5 to 7.5 times this part's
2.87 to 3.95 million in the stretches between its records, and 6.1 times its
3.55 million since its 363rd network update (same records; not measured for
choice D's searches). And the longer AddressSanitizer finds nothing, the likelier
it is that the defect is one it cannot see, such as one that needs the timing
of 42 game threads on the fast engine.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Go on as now until AddressSanitizer reports | Nothing changes. At about 3.55 million network evaluations an hour, the chance of a report reaches 0.87 after 11 more hours of play, 0.9 after 20.5 and 0.94 after 39, counted from 07:39 on 24 November, if AddressSanitizer sees the defect at all. The network goes on training at this part's pace. |
| B. ThreadSanitizer for about 12 hours of play, then A | ThreadSanitizer looks for a data race: two game threads of one process touching the same memory, at least one of them writing, with no lock between them. No data race has been found; one is a suspected cause of the crashes, and one that AddressSanitizer would see only on the rare occasion when the two touches damage memory. ThreadSanitizer reports the two touches as soon as it sees them, whether or not anything is damaged that time, and names the two places in the code that made them. A data race found that way is fixed by a lock around that memory, or by not sharing it between the threads; the full-speed part could then run without the crashes. The part stops, keeping its checkpoint and losing only the games in play; its game process then runs the part's own sources built with ThreadSanitizer, in the same layout, and the part resumes from the checkpoint. It has run only in a test script, with three or four game threads and no inference server, for about 8,000 decisions ([record](archive/records/crash_diagnosis_2026_11_21.md)). The damage has crossed games: before the second crash of 20 November, two other games of that process failed the state check ([record](archive/records/second_game_process_crash_2026_11_20.md)), which a data race between game threads would explain, as would a second free. In the test script it played 1.54 decisions a thread-second against 3.27 for that day's AddressSanitizer build, so training would go at roughly a third of this part's pace (inferred). Its memory in this layout is not measured; a few minutes would measure it before it replaces the checked engine. It finds nothing if the defect is not a data race. |
| C. Start the full-speed part now | Six game processes of 42 games on the ordinary engine, from this part's newest network on its own copy of the code, or from a fresh network on the current code. The crashes come back, about one every six hours if they keep their rate per network evaluation (inferred). Each costs the dead process's unfinished games, a few minutes of play, and leaves their move logs, the crash report and the allocator's message ([running training on the Mac](design/README.md#92-running-training-on-the-mac)). The defect stays unfound, and its damage can reach a game's state, as it did twice on 20 November. |

**Recommendation: B, then A.** ThreadSanitizer is the one check not yet made
where the crashes happen, with the inference server and many game threads, and
each hour in which AddressSanitizer finds nothing makes a defect it cannot see
more likely. Twelve hours of B cost about eight hours of this part's training
(inferred), and A goes on from the same checkpoint if B finds nothing. If A then
passes a chance of about 0.9 with no report, after about 20 more hours of play
from 07:39 on 24 November, C is what remains.

**If answered.** How the defect is looked for, and what that finds, belong in the
[known gaps](design/README.md#known-gaps) of the design document, and the run's
parts in the [list of runs](archive/runs.md).

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
