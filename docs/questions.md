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
| [Q-022](#q-022-several-simulations-in-one-inference-request) | Should self-play's search choose the paths of 8 simulations before it asks the network about the states where they stopped, all in one inference request, as AlphaGo Zero did? | Search | Yes, 8 a request: about two and a half times the network evaluations a second at 256×16 on the Mac |
| [Q-023](#q-023-counting-a-reused-trees-visits-toward-a-fast-search) | Should a fast search, the 150-simulation search at a decision not kept as a training sample, run only enough new simulations to bring its root to 150 visits, counting those the searches before it left there? | Search | Yes, for the fast searches only: about 18% fewer network evaluations, the full searches and the training targets unchanged |

Q-005 was raised on 15 November 2026, when the allowance became 9 cores (commit
`e62e01b`). Its numbers are in the
[record of training within nine cores](archive/records/nine_core_layouts_2026_11_15.md).

Q-022 and Q-023 were raised on 24 November 2026, by the speed work before
training at AlphaZero's and KataGo's scale. Their numbers are in the
[record of self-play speed at 256×16](archive/records/self_play_speed_256x16_2026_11_24.md).

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

## Q-022: Several simulations in one inference request

**The question.** Should self-play's search choose the paths of 8 simulations
before it asks the network about any of the states where they stopped, and then
ask about all 8 states at once, as AlphaGo Zero did, instead of asking after
each simulation and waiting for the answer before the next one starts?

**What the program does now.** At a decision, the search runs many
*simulations*, 800 or 150 at these sizes. Each one plays forward from the
current state on a copy of the game, choosing at every state the action with
the best PUCT score, which weighs what earlier simulations found against what
the network expected; it stops at the first state the network has not yet
rated, asks the network for that state's priors and values, and adds the values
it gets to every action it played on the way, its *path*
([design document, section 4.2](design/README.md#42-one-simulation)). The
network does not run inside the game: one process, the *inference server*,
runs it for the states of every game being played, and a game asks it about a
state with a message, an *inference request* (same section, and
[section 9.2](design/README.md#92-running-training-on-the-mac)). Now a search
sends one inference request after each simulation and waits for the reply,
because the next simulation's choices depend on that answer
(`--simulations-per-request 1`, the default). So each game has at most one state
waiting at the inference server at a time, and the inference server, whose work
per state falls the more states it evaluates together, gets at most one state
from each game at once. Since 24 November `--simulations-per-request N` lets the
search choose the paths of N simulations first and ask about all N states in
one inference request, so that each game can have N states waiting. To keep the
N from all taking the same path, each waiting simulation counts meanwhile on its
path as a visit that lost, a *virtual loss*, and a simulation that stops at a
state already in the request is dropped and tried again later
([design document, section 4.7](design/README.md#47-more-detail-on-the-search),
with a worked example). AlphaGo Zero's search ran its simulations on parallel threads with a virtual
loss and evaluated their states in mini-batches of 8 ([Silver et al.
2017](https://discovery.ucl.ac.uk/id/eprint/10045895/1/agz_unformatted_nature.pdf),
Methods, "Search Algorithm").

**A real case.** In self-play at 256×16 with 800 simulations on a quarter of the
decisions and 150 on the rest, 48 concurrent games, measured for 25 minutes
each ([record](archive/records/self_play_speed_256x16_2026_11_24.md)): with one
simulation a request the inference server answered 2,761 network evaluations a
second, in inference batches of 24 states, busy 95% of the time, while the game
processes kept about 4.5 CPU cores busy; with 8 a request, and inference batches
overlapped on the GPU, it answered about 6,100 a second, in inference batches of
about 125 states, busy about 73%, and the CPU cores, at a median of 9.4 busy,
set the pace instead. With 30 concurrent games instead of 48, and lighter
bookkeeping in the engine, 8 a request answered about 7,600 network evaluations
a second between network updates and 7,300 with them, in inference batches of
about 71 states, the inference server busy 94% of the time and the CPU cores a
median of 8.4, while the run's processes held about 7 GB by their physical
footprints. On 70 positions of scripted games searched with a
stand-in network, the most visited action after 800 simulations with
exploration noise, as at a kept decision, was the same with 8 a request as with
1 at 56 of them, and two searches of 1 a request with different seeds agreed at
52; the visit shares differed by a total variation distance of 0.05 on average
with 8 a request, and 0.17 with another seed: 5% and 17% of the visits would
have to move from some actions to others to turn one search's visit shares into
the other's. After 150 simulations without
noise, as at the other decisions, 8 a request kept the most visited action at
63 of the 70 and another seed at 66, with distances of 0.05 and 0.02.

**Why it matters.** A game at these sizes asks for about 217,000 network
evaluations once the network plays full games
([design document](design/README.md#how-big-should-the-network-and-the-search-be)):
about 1,100 games a day at 2,761 a second, and about 2,900 at 7,300. KataGo's
yardstick of about 145,000 games takes about 132 days at the first rate and
about 50 at the second (inferred). The simulations of one request choose
their paths without each other's results, so a search of 800 simulations
explores a little differently from one simulation at a time, as AlphaGo Zero's
did.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. One simulation a request | The search as in every run so far, simulation by simulation; the inference server limits self-play at about 2,800 network evaluations a second at 256×16. |
| B. 8 a request | AlphaGo Zero's size. About two and a half times the network evaluations a second with 30 concurrent games; the GPU and the CPU cores then limit together. |
| C. 16 a request | The same inference batches from half as many concurrent games, so about half the search trees' memory, which does not limit at 8 with 30 games, and no faster; a 150-simulation search then chooses its paths in groups of 16, a tenth of it at a time. |

**Recommendation: B.** It gives about two and a half times the network
evaluations a second, from 30 concurrent games where one a request needed 48 for
less, and it is the search AlphaGo Zero learned with.

**If answered.** The run's command takes `--simulations-per-request` with the
chosen number, and section 4.7 of the design document says that self-play
searches that way.

## Q-023: Counting a reused tree's visits toward a fast search

**The question.** A fast search, the search of 150 simulations at a decision
not kept as a training sample, often starts with many visits already at its
root, left there by the searches before it. Should it run only as many new
simulations as bring its root to 150 visits, and none if the root already holds
150, instead of always running 150 new ones?

**What the program does now.** Two parts of the design meet here.

- *Full and fast searches.* At the sizes planned for the training run, a random
  quarter of the decisions are kept as training samples, the *kept decisions*.
  A kept decision gets a *full search*: 800 simulations with exploration noise,
  whose visit shares become the training sample's policy target. Every other
  decision gets a *fast search*: 150 simulations without noise, only to choose
  the move
  ([design document, section 7.1](design/README.md#71-a-training-iterations-games)).
  KataGo searched this way, with 600 to 1,000 simulations and 100 to 200
  ([Wu 2019](https://arxiv.org/abs/1902.10565), section 3.1).
- *Tree reuse.* When the game has played a move, the next search does not start
  from an empty tree. It takes over the part of the last search's tree below the
  state the game reached, with all its visit counts, the *reused tree*, and
  drops the rest, as AlphaGo Zero did
  ([design document, section 4.7](design/README.md#47-more-detail-on-the-search)).
  So the new search's root, the decision now to be made, already holds a visit
  for every earlier simulation that took one of its actions.

Every search then runs its whole budget of new simulations, 800 or 150, on top
of the visits its root already holds (`SearchSettings::simulations` in
`include/game/search.hpp`).

**A worked example.** In the toy search of
[section 4.4 of the design document](design/README.md#44-a-toy-search), with a
budget of 4 simulations at the state R, simulation 4 went through RA on to RAx.
Say the game then plays A. The next search starts at RA, whose action x already
holds that 1 visit. With a budget of 4, the program now runs 4 new simulations,
and RA's actions end with 5 visits. Counting the reused visit, it would run 3,
and RA's actions would end with 4, the budget.

**A real case.** In two games played with the run's search settings, 8
simulations a request and a stand-in network that gives every state made-up
priors and values, 407 searches
([record](archive/records/self_play_speed_256x16_2026_11_24.md)): before its
first new simulation, a fast search's root already held 127 visits on average,
a median of 56, and 27% of the fast searches already held 150 or more. In one
of the two games, a full search at a decision with two legal actions sent most
of its 800 simulations through the action the game then played, and the fast
search at the next searched decision began with 709 of their visits at its
root; it then ran 150 new simulations on top. A full search's root already held
114 visits on average. Counting the reused visits toward the budget would have
run 17.7% fewer simulations in these 407 searches if only the fast searches
counted them, and 26.4% fewer if every search did. Counted in the fast searches,
a fast search's root would end with 150 visits at the median instead of 206,
and 206 on average instead of 277, and 27% of the fast searches would run no
new simulation and choose their move from the reused visits alone.

**Why it matters.** Each simulation asks for one network evaluation, and network
evaluations are the run's cost: 17.7% fewer a game is about a fifth more games a
day at the same speed, and KataGo's yardstick of 145,000 games in about 41 days
instead of about 50 (inferred, from the rates of
[Q-022](#q-022-several-simulations-in-one-inference-request)). A fast search
only chooses a move: no training sample stores its visit shares, so the training
targets stay as they are. The moves still shape the games, and with them the
final scores that every training sample of a game takes as its value target. A
fast search would choose from fewer visits than now, but never fewer than 150,
within the 100 to 200 of KataGo's fast searches. KataGo's self-play, moreover,
seems to have started each search with a fresh tree: its gating games, which
decide whether a new network replaces the old, turned tree reuse on as one of
their changes from self-play ([Wu 2019](https://arxiv.org/abs/1902.10565),
appendix E). Not measured: how many visits a trained network's searches leave
to the next decision; probably more (inferred), since a trained network's
priors send more of a search's simulations down the action the game then
plays.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. As now: every search runs its whole budget of new simulations | A fast search ends with its reused visits plus 150. |
| B. Count the reused visits toward every search's budget, full searches too | About 26% fewer network evaluations. A full search then runs fewer than 800 new simulations with its exploration noise, so its visit shares, the training target, rest more than now on reused visits, made before that noise was drawn. |
| C. Count them toward the fast searches' budget only | About 18% fewer network evaluations; the full searches, and so the training targets, unchanged. |

**Recommendation: C.** It takes two thirds of B's saving without touching the
searches the network learns from, and every fast search still chooses its move
from at least 150 visits.

**If answered.** The search takes a setting for which searches count the
reused visits toward their budget, and sections 4.7 and 7.1 of the design
document say how the budget counts.

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
