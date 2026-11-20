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
| [Q-011](#q-011-the-memory-the-rest-of-the-mac-uses) | Should the supervisor also stop a run when the whole Mac runs short of memory, not only when the run itself nears 30 GB? | Running training | Yes: watch the Mac's memory pressure and swap too |
| [Q-012](#q-012-a-game-process-that-crashes) | When a game process crashes, should training lose only that process's games, and should it pause for some hours to find the defect behind the crash? | Running training | Lose only that process's games now; look for the defect when the Mac can spare the hours |

Q-005 was raised on 15 November 2026, when the allowance became 9 cores (commit
`e62e01b`). Its numbers are in the
[record of training within nine cores](archive/records/nine_core_layouts_2026_11_15.md).
Q-006 was raised on 15 November 2026, while the printed rules on Mongolia's
attacks on Chinese land (Q-001, since answered) were being looked up. Its
numbers are in the
[record of which features random games give values to](archive/records/answer_census_2026_11_15.md).
Q-011 was raised on 19 November 2026, when a training run with 378 concurrent
games filled the Mac's memory. Its numbers are in the
[record of concurrent games with the C++ search](archive/records/concurrent_games_cpp_search_2026_11_19.md).
Q-012 was raised on 20 November 2026, when a game process of the long training
run started the day before crashed. Its numbers are in the
[record of that crash](archive/records/game_process_crash_2026_11_20.md) and
the [record of the training process's memory](archive/records/training_process_memory_2026_11_20.md).

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

## Q-011: The memory the rest of the Mac uses

**The question.** Should the supervisor also stop a training run when the Mac
as a whole runs short of memory, not only when the run's own processes come
near the owner's allowance of 30 GB?

**What the supervisor does now.** Every second it adds up the memory of the
run's processes, for each process its resident memory or macOS's physical
footprint with its compressed pages, whichever is larger
(`process_memory_charge` in `tools/supervise_campaign_training.py`). It asks the
run to stop when that sum comes within 1 GB of 30 GB, and kills the run at
30 GB. The Mac has 36 GB, so the allowance leaves about 6 GB for everything
else, and nothing checks what everything else uses.

**A real case** (19 November 2026, the 256×8 network on the GPU, 378 concurrent
games in 7 game processes of 54). The run held about 15 GB at its sampled
peak, half the allowance. The Mac's other programs, a browser, a web
development server and Claude's apps among them, held 11 to 17 GB of resident
memory, and the operating system kept 5 to 6 GB for itself. At 15:43 another
program started 12 worker processes of about 1.1 GB each. By 15:49 the Mac's
memory was full: 17 GB in the memory compressor, 10.2 GB of the 11.3 GB of
swap in use and the kernel taking 48% of the CPU, compressing and swapping
pages, against about 9% when the Mac is quiet. The run's own CPU use had
fallen from about 7.5 cores to under 4 from about 15:40, as its pages were
compressed. The supervisor saw nothing wrong, since the run stayed far under
30 GB, and the run was stopped by hand at 15:50. The same layout run again at
17:19, with nothing else large running, kept macOS's memory pressure at
"warning", grew swap by 4.1 GB in 38 minutes and played about 10% fewer
decisions an hour than 252 games
([record](archive/records/concurrent_games_cpp_search_2026_11_19.md#the-378-game-runs)).

**Why it matters.** A run within its allowance can still make the whole Mac
unusable, for the owner's other work as much as for training, and its
measurements are then worthless. The 30 GB fit only while the rest of the Mac
uses about 6 GB, and with a browser and other sessions open it uses more than
twice that.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Watch the Mac's memory too | The supervisor also reads macOS's memory pressure level (the `kern.memorystatus_vm_pressure_level` system value) and the swap in use, and stops the run safely, as a requested stop, when the pressure turns critical or swap grows by a few GB during the run. It protects the Mac whatever else runs; a run may stop because of other programs, which the status file would say. |
| B. A smaller allowance | Lower the run's limit to what fits beside the usual programs, such as 18 GB. Simple, but the right number changes with what else is open, and a quiet Mac would leave memory unused. |
| C. Leave it | Keep the 30 GB and keep other large programs closed while training runs. |

**Recommendation: A, with the 30 GB check kept.** It guards against what went
wrong, whatever its cause, and the supervisor already samples memory every
second. The 19 November rerun of the 378-game layout ran with such a check in
a separate script: the pressure never turned critical, and the growth of swap
was what stopped it.

**If answered.** What the supervisor watches and when it stops a run belong in
the [campaign learning guide](../studies/campaign/README.md#long-unattended-runs)
and in [section 9.2 of the design document](design/README.md#92-running-training-on-the-mac).

## Q-012: A game process that crashes

**The question.** When a game process crashes, should the run lose only that
process's games instead of stopping? And should training pause for some hours
so that the defect behind the crash can be looked for?

**What the program does now.** A game process plays its games in threads, and
each game thread sends its states to the inference server through a pipe of
its own. The inference server runs in the training process (`game_process` and
`SharedEvaluatorServer` in `studies/campaign/shared_evaluator.py`). When a game
process dies, the inference server's next reply to it fails, and the training
process exits with code 1. The supervisor does not retry a run after that exit
(`RETRYABLE_RETURNCODES` in `tools/supervise_campaign_training.py`), so the run
stops. Started again, the supervisor resumes the run from its checkpoint, which
is written at each network update. The games in play and all the play since
that update are lost.

**A real case** (20 November 2026, the long run of 252 concurrent games from
commit `999c90c`). After 5.13 hours of play, at 01:06, a game process aborted.
macOS's memory allocator found that memory being freed had not been allocated.
The process was freeing a game's kept search tree
([section 4.7 of the design document](design/README.md#47-more-detail-on-the-search)),
and the bad memory was in the state of a nation, in the game copy of one of
the tree's nodes. The game had just raised an error, and the record of that
error died with the process. A shell loop outside the repository started the
supervisor again two minutes later. The next network update came about 51
minutes later than it would have without the crash
([record](archive/records/game_process_crash_2026_11_20.md)). Two crashes of
the same kind were noted on 2 November 2026, before the search ran in C++.

**Why it matters.** At one crash in about five hours of play, a run would lose
about 14% of its time (inferred from this one crash). And the defect damages
memory before anything notices it: a game's state could be wrong without any
crash, and its training samples with it.

**A second fix waits for a new run.** The same run's training process kept
every finished game's result, about 1.25 GB more an hour
([record](archive/records/training_process_memory_2026_11_20.md)). The fix is in
the repository since 20 November, but the current run plays its own copy of the
code. Until a new run, the supervisor will stop the current run when its memory
reaches 29 GB, during a network update, about every eight to nine hours (the
first at about 09:00 to 10:00 on 20 November), and the shell loop will start it
again; each stop loses the games in play, about 25 minutes of play (inferred).
A new run for choice A would take up this fix too.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Survive a crash | The inference server takes a closed pipe as the end of its game process, records that process's games in play as failed games, and starts a new game process for the same game slots; the run goes on. A crash then costs one process's games in play, 42 of the 252 in this run, instead of all the play since the last network update. It is a code change, so the running run would go on as a new run from its newest networks (`--initial-models`), with a new replay buffer. |
| B. Look for the defect | Build the engine with AddressSanitizer, which stops a process at the first write to freed memory and names the code that made it, and play training games with the newest networks for some hours. The sanitized games need the cores, so training pauses meanwhile. It finds the defect only if the defect strikes during those hours, and one crash in 5.13 hours of 252 games suggests that may take many hours. |
| C. Leave it | The shell loop restarts the run after each crash, at a cost of about 51 minutes each time, and after each memory stop (above). |

**Recommendation: A now, and B when the Mac can spare some hours.** A removes
most of the cost at once. Only B can find the defect, which may damage games
without crashing them.

**If answered.** What happens when a game process dies belongs in the
[campaign learning guide](../studies/campaign/README.md#long-unattended-runs)
and in [section 9.2 of the design document](design/README.md#92-running-training-on-the-mac).

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
