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
| [Q-006](#q-006-the-kmt-after-the-ccp-comes-back) | Once the CCP has been eliminated, may the KMT attack warlords and Mongolia for good, or only while the CCP has no units? | A printed rule | For good, as the printed words say |
| [Q-012](#q-012-a-game-process-that-crashes) | Should training pause for some hours to look for the defect behind a game process's crash? | Running training | Yes, when the Mac can spare the hours |

Q-005 was raised on 15 November 2026, when the allowance became 9 cores (commit
`e62e01b`). Its numbers are in the
[record of training within nine cores](archive/records/nine_core_layouts_2026_11_15.md).
Q-006 was raised on 15 November 2026, while the printed rules on Mongolia's
attacks on Chinese land (Q-001, since answered) were being looked up. Its
numbers are in the
[record of which features random games give values to](archive/records/answer_census_2026_11_15.md).
Q-012 was raised on 20 November 2026, when a game process of the long training
run started the day before crashed; its first part, whether training should
lose only that process's games, and its choice of keeping the position of a
game that fails the engine's check were answered the same day. Its numbers are in
the [record of that crash](archive/records/game_process_crash_2026_11_20.md),
the
[record of a second crash the same day](archive/records/second_game_process_crash_2026_11_20.md),
the
[record of a third](archive/records/third_game_process_crash_2026_11_20.md)
the
[record of a fourth, on 21 November](archive/records/fourth_game_process_crash_2026_11_21.md)
and the
[record of a fifth](archive/records/fifth_game_process_crash_2026_11_21.md).

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

## Q-006: The KMT after the CCP comes back

**The question.** Once the CCP has been eliminated, may the KMT attack Chinese
warlords and Mongolia for the rest of the game, or only while the CCP has no
units?

**What the engine does now.** It lets the KMT start a war with a warlord or
with Mongolia, by a land attack, only while the CCP has no units at that
moment (`mayDeclareWar` in `src/politics.cpp`;
[politics](engine/politics.md#1-war)). When the CCP has a unit again, the
permission is gone. A CCP without units still holds its land and its treasury,
so it can buy a unit in its next Production Phase.

**The printed rules.**

| Rule | What it says |
| --- | --- |
| 5.1, page 35, and the KMT's national reference sheet, page 2 | Can the KMT declare war on Chinese warlords or Mongolia? "Yes, if CCP previously has been eliminated. Via combat movement." |
| 4.9, page 30 | Before the CCP is eliminated the KMT may not attack a Chinese warlord. One it attacks afterwards aligns with the CCP, which brings the CCP back. |
| 14.3, page 101 | The Chinese Civil War ends when one faction no longer has any surviving units. |

The word is "previously", and 4.9 says "until": both speak of something that
has happened, not of how things stand now. No rule says that the permission
ends when the CCP has units again. The earlier check of this subject settled
only that an eliminated CCP has not surrendered and can come back
(`game_content/rules/source_answered_questions.md`, the row on CCP
elimination).

**A real case** (random game, seed 9105;
[record](archive/records/answer_census_2026_11_15.md#the-kmt-and-mongolia-after-the-ccp-comes-back)).

1. Game round 2, the CCP's Combat Phase: the CCP loses its last two units in
   battles on its own turn. It has no units.
2. Three decisions later, in its Place Units Phase, the CCP places an infantry
   it had bought. It has one unit again.
3. Later in game round 2, the KMT's Combat Movement: KMT units in Tsinghai stand
   next to Mongolian land. The engine offers the KMT seven combat moves, none
   into Mongolia, because the CCP has a unit.

Under the printed words the attack would be allowed: the CCP had been
eliminated before.

**How often.** In 480 random games the CCP was without units at some decision
in 154, and had units again later in 57. In 43 games the KMT then stood next
to Mongolia in its Combat Movement, not yet at war with it, and was not
offered the attack, at 600 decisions in all. While the CCP had no units, the
attack was offered in 124 games
([record](archive/records/answer_census_2026_11_15.md#the-kmt-and-mongolia-after-the-ccp-comes-back)).

**Why it matters.** It decides how free the KMT is once the CCP has been
without units for the first time: for good, or only in the short windows when
the CCP has nothing on the map. It also decides what the CCP's player has to prevent: ever
dropping to no units, or only being without units on the KMT's turn.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Keep it: only while the CCP has no units | Nothing. |
| B. For good, once the CCP has been without units | The engine remembers that the CCP has been eliminated, in a mark on the CCP, and `mayDeclareWar` asks that mark. The mark needs a question in the network's input, so it is a layout change. |

**Recommendation: B, with moderate confidence.** It is what the words say.
The engine's reading is not unreasonable, since 4.9 speaks of the CCP coming
back, but no rule states that the ban returns. This is a good one to put to
the game's developers.

**If answered.** A ruling becomes the next rule clarification, with
`mayDeclareWar`, its test and the politics page changed in the same commit.

## Q-012: A game process that crashes

**The question.** Should training pause for some hours so that the defect
behind a game process's crash can be looked for?

**What the program does now.** A game process plays its games in threads, and
its native code, the engine and the search, can crash it. When a game process
dies, the run loses only the games that process had not finished: they are
recorded as failed games, and a new game process takes its game slots while the
others play on (`play_shared_games` in `studies/campaign/shared_evaluator.py`;
[running training on the Mac](design/README.md#92-running-training-on-the-mac)).
A move that the engine accepted and then failed on, such as one after which the
state fails the check that the engine runs after every move (`State::validate`
in `src/campaign_state.cpp`), keeps the position before it and the move, and
`tools/replay_failed_move.py` replays it in a fresh process to tell a defect of
the rules from damaged memory. The defect that made a game process crash is not
found.

**A real case** (20 November 2026, the long run of 252 concurrent games from
commit `999c90c`). After 5.13 hours of play, at 01:06, a game process aborted.
macOS's memory allocator found that memory being freed had not been allocated.
The process was freeing a game's kept search tree
([section 4.7 of the design document](design/README.md#47-more-detail-on-the-search)),
and the bad memory was in the state of a nation, in the game copy of one of
the tree's nodes. The game had just raised an error, and the record of that
error died with the process. That run then stopped with the process, and the
next network update came about 51 minutes later than it would have without the
crash ([record](archive/records/game_process_crash_2026_11_20.md)). Two crashes
of the same kind were noted on 2 November 2026, before the search ran in C++.

**A second case** (the same day, the run of 252 concurrent games from commit
`7adac20`, whose engine and search are the same code). After 3.86 hours of
play, at 10:46, a game process aborted with the same allocator message. This
time the bad memory was in the state of a unit, in the game copy of a search
tree node, and the search was freeing the nodes of a game's tree that it did
not keep. Between the network update at 10:08 and the crash, two games of that
process had failed the check that the engine runs on the state after every
move (`State::validate` in `src/campaign_state.cpp`): something in each game's
state held a zone number that no zone has. A new game process took the dead
one's game slots, and the run lost 44 games, about 7 minutes of its play
(inferred), instead of stopping
([record](archive/records/second_game_process_crash_2026_11_20.md)).

**A third case** (the same run, at 14:28, after 7.56 hours of play). Another
game process aborted with the same allocator message, again while the search
freed the nodes of a game's tree that it did not keep, this time in the
destructor of a whole game state. No game of that process had failed the
engine's check. A new game process took its game slots, and the run lost 42
games, about 6 minutes of its play (inferred)
([record](archive/records/third_game_process_crash_2026_11_20.md)).

**A fourth case** (21 November 2026, at 00:18, the run started at 22:43 the evening
before with the same engine and search and new learning settings, after 1.59
hours of play). A game process aborted with the same allocator message, again
while the search freed the nodes of a game's tree that it did not keep, this
time in an entry of the game state's build projects (`State::construction` in
`include/game/campaign.hpp`). No game of the run had failed the engine's check.
A new game process took its game slots, and the run lost 42 games, about 5
minutes of its play (inferred)
([record](archive/records/fourth_game_process_crash_2026_11_21.md)).

**A fifth case** (the same run, at 04:49 on 21 November, after 6.11 hours of
play). Another game process aborted with the same allocator message, while the
search freed the nodes of a game's tree that it did not keep, in a unit's state
as in the second case. No game had failed the engine's check. A new game
process took its game slots, and the run lost 42 games, about 4 minutes of its
play (inferred)
([record](archive/records/fifth_game_process_crash_2026_11_21.md)).

The two games that failed the check between 10:08 and 10:46 left only their seeds
and their error's text, which cannot rebuild their states: the run did not yet
keep a failed move's position, and with the shared inference server a game's
seed need not replay it
([failures in training](design/README.md#92-running-training-on-the-mac)).

**Why it matters.** The defect most likely damages game states before anything
notices it (inferred): the only two games of the run to fail the engine's check
were in the process that aborted at 10:46, in the 38 minutes before it did,
although the process that aborted at 14:28 had no failed game. A damaged value
that the check does not catch, such as a zone number that names a real zone,
would go into the game's training samples. And each crash still costs the games
in play in one game process: 42 games in the long run's layout of six
processes, about 7, 6, 5 and 4 minutes of its play in the second to fifth
cases.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Look for the defect | Build the engine with AddressSanitizer, which stops a process at the first write to freed memory and names the code that made it, and play training games with the newest networks for some hours. The sanitized games need the cores, so training pauses meanwhile. It finds the defect only if the defect strikes during those hours, and five crashes in 32.6 hours of play of 252 games, about one every 6.5 hours, suggest that may take many hours. |
| B. Leave it | Training goes on, and each crash costs one game process's games in play, about 4 to 7 minutes of the run's play in the second to fifth cases. The defect stays, with whatever it does to games that neither fail the check nor crash. |

**Recommendation: A, when the Mac can spare some hours.** Only A can find the
memory defect behind the crashes, which has most likely damaged the states of
two games already. A kept failed move only shows whether a bad zone number came
from the rules or from damage, and only when a check fails: in 32.6 hours of
play of 252 games the only two failures came before the second crash, and none
before the third, the fourth or the fifth.

**If answered.** What was found, and the fix, belong in the engine page of the
code that held the defect, and in
[section 4.7 of the design document](design/README.md#47-more-detail-on-the-search)
if it was in the search.

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

- **Q-001**, Mongolia at war with the CCP. Answered on 19 November 2026:
  follow the printed rules for now, so Mongolia may not attack land that was
  originally a warlord's, the CCP's or the KMT's, which would put it at war
  with the CCP of its own alliance. Stated in
  [rule clarification RCL-022](../game_content/rules/clarifications.md#rcl-022-an-attack-on-land-that-was-chinese-at-the-start)
  and [the politics page](engine/politics.md#invading-china).
- **Q-002**, Chinese land that Japan holds. Answered on 19 November 2026: the
  printed owner decides, so an attack on such land is an attack on China
  whoever holds it, and no nation that may not go to war with all of China,
  such as the USSR or a nation of the Allies in the full game, may make it.
  Stated in the same two places.
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
- **Q-013**, how many games a network update learns from. Answered on 20
  November 2026: choice B, so the long run keeps 1% of each game's decisions as
  training samples and 25,000 in its replay buffer, those of about 1,700 games,
  instead of 5% and 8,000, those of about 110
  ([record](archive/records/replay_buffer_fit_2026_11_20.md)). Stated in
  [how often a training sample is drawn](design/README.md#87-how-often-a-training-sample-is-drawn)
  and [training on the Mac](../studies/campaign/README.md#training-on-the-mac).
