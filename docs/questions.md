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
| [Q-001](#q-001-mongolia-at-war-with-the-ccp) | May Mongolia attack land that was Chinese at the start, which now puts it at war with the CCP? | A printed rule | No: rule 4.5 does not allow the attack |
| [Q-002](#q-002-chinese-land-that-japan-holds) | Is an attack on Chinese land that Japan now holds an attack on China? | A printed rule | Yes, as now; it cannot arise if Q-001 is answered as recommended |
| [Q-005](#q-005-the-supervisors-count-of-cores) | Should the supervisor keep training within the 9 cores by measuring the load, not by counting game processes? | Running training | Yes: measure, warn, and stop a run that stays over |
| [Q-006](#q-006-the-kmt-after-the-ccp-comes-back) | Once the CCP has been eliminated, may the KMT attack warlords and Mongolia for good, or only while the CCP has no units? | A printed rule | For good, as the printed words say |

Q-001 and Q-002 were raised on 14 November 2026, while the global features
about nations were being pruned (commit `bce7a4c`). Their numbers are in the
[record of which features random games give values to](archive/records/answer_census_2026_11_15.md).
Q-005 was raised on 15 November 2026, when the allowance became 9 cores (commit
`e62e01b`). Its numbers are in the
[record of training within nine cores](archive/records/nine_core_layouts_2026_11_15.md).
Q-006 was raised on 15 November 2026, while the printed sources of Q-001 were
being looked up; its numbers are in the first record.

## Q-001: Mongolia at war with the CCP

**The question.** When Mongolia attacks land that was Chinese at the start of
the game, the engine puts it at war with the CCP, which belongs to its own
alliance and is played by the same player. Should Mongolia be able to make that
attack at all?

**What the engine does now.**

- An attack by a nation that is not Chinese on a land zone that was originally
  a warlord's, the CCP's or the KMT's is recorded as an invasion of China. The
  attacker is put at war with the KMT, the CCP and every warlord that has not
  yet joined a side, and those warlords pick a side at the end of that Combat
  Phase (`recordLandAttack` in `src/politics.cpp`, following rulebook 4.9,
  page 30; [politics](engine/politics.md#2-the-warlords)).
- Mongolia may never declare war (`mayDeclareWar` in `src/politics.cpp`). It
  may make a combat move only into a zone whose holder is already at war with
  it, or that nobody holds (`landAccess` in `src/movement.cpp`).
- The second check looks only at the holder of the zone. It does not look at
  the wars the first rule then adds.

**A real case** (random game, seed 7155;
[record](archive/records/answer_census_2026_11_15.md#mongolia-as-the-invader-of-china)).

1. Game round 1: the CCP attacks the Ma Clique in Tsinghai and Mengjiang in
   Suiyuan, so both join the KMT with their land at the end of that Combat
   Phase (rulebook 4.9, page 30: a warlord attacked by the CCP aligns with the
   KMT). Japan then attacks Nanking, and at the end of Japan's Combat Phase the
   six other warlords join the KMT too (rulebook 4.9, page 30: an attack by a
   foreign nation on Chinese land makes every warlord align with the CCP or
   the KMT). Later in that game round the KMT destroys the CCP's last units.
2. Game round 2: the KMT attacks Mongolia. The declaration-of-war table lets the
   KMT attack Chinese warlords or Mongolia, by a combat move, once the CCP has
   been eliminated (rulebook 5.1, page 35, the KMT's rows; the same rows are on
   the KMT's national reference sheet, page 2; [Q-006](#q-006-the-kmt-after-the-ccp-comes-back)
   is about their exact words). The KMT and Mongolia are now at war.
3. Game round 3: a Mongolian cavalry moves into Tsinghai, which the KMT holds, as an
   attack. The engine records Mongolia as invading China. No warlord is left
   to join a side, and Mongolia was already at war with the KMT, so the attack
   changes one thing: from that move on Mongolia and the CCP are at war.

**How often.** In 480 random games Mongolia was recorded as the invader in 70,
from game round 3 on, and in all 70 it came to be at war with the CCP. In 69 of them
no warlord was left to join a side; the new enemies were the CCP alone in 46
games and the CCP and the KMT in 23. Three times Mongolia then attacked land
the CCP held ([record](archive/records/answer_census_2026_11_15.md#mongolia-as-the-invader-of-china)).

**The printed rules.**

| Rule | What it says |
| --- | --- |
| 4.9, page 30 | A foreign nation that attacks land which was originally a warlord's, the CCP's or the KMT's has thereby declared war on the whole of China, and every warlord aligns with the CCP or the KMT (or the Dadao Government) at the end of the attacker's Combat Phase. |
| 4.5, page 27 | Whoever controls a minor power may move its units in combat only against nations it is already at war with, and may not declare war for it or take any action that puts it at war with a power it is not already at war with. |
| 4.3, page 26, and 4.7, page 29 | Mongolia is a minor power of the Comintern, controlled by the USSR. The CCP is in the Comintern too. |
| 4.7, page 29, and 4.6, page 28 | Attacked by the KMT, Mongolia stays a nation of its own. Attacked by anyone else, it aligns with the USSR at the end of the attacker's Combat Phase, and at once if the USSR is at war with a major power. A minor power that aligns is incorporated into the major power and ceases to exist; its land and units become the major power's. |
| 5.1, page 35 | Nobody may declare war inside their own alliance; the table answers "No" for the USSR and for the CCP against other Comintern nations. |
| 14.3, page 101 | Without a declaration of war no other nation may enter land that was originally the KMT's, the CCP's or a warlord's; that the land is friendly makes no difference. |

This campaign leaves the USSR out and lets the Comintern player move Mongolia
with the rights of a controlled minor power
([approved scenario decisions](plans/japan_china_full_rules_plan.md#approved-scenario-decisions);
`mongolia_campaign_override` in `game_content/rules/gw36_politics_v43.json`,
which also turns off Mongolia's alignment with the USSR). In the full game,
then, the only nation a Mongolia of its own can be at war with is the KMT, and
the only Chinese land it can attack is land the KMT holds, as in the case
above. Here it can also be at war with Japan; that case is
[Q-002](#q-002-chinese-land-that-japan-holds).

Read together, the rules do not allow this attack: by 4.9 it would be a
declaration of war on all of China, which 4.5 forbids for a controlled minor
power and 5.1 forbids against the CCP. The engine applies 4.5 to the holder of
the zone only.

**Why it matters.** Two nations of one alliance, moved by one player, become
enemies (rulebook glossary, page 6: nations at war with each other are
enemies), so their units may attack each other, and the Comintern's network is
trained on such states. Random play reaches this in one game in seven.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Keep it | Nothing. The engine stays against rules 4.5 and 5.1. |
| B. Allow the attack, but never put a nation at war with its own alliance | Mongolia's attack still counts as an invasion and puts it at war with the KMT and with warlords that have not joined a side, but not with the CCP. No printed rule says this; it follows 5.1 and sets 4.5 aside. A small change in `recordLandAttack` with a test. |
| C. Do not allow the attack | Mongolia is offered no combat move into a zone that was originally a warlord's, the CCP's or the KMT's. It can still defend itself, retake its own land and attack zones that were never Chinese. A check in `landAccess` with a test; `china_invader:mongolia` and the `at_war` questions that only this attack can answer may then leave the network's input. |

**Recommendation: C.** It is what rules 4.9, 4.5 and 5.1 give when read
together, and it treats Mongolia as the same rules treat the USSR, which they
keep out of every zone that was originally a warlord's, the CCP's or the KMT's
([Q-002](#q-002-chinese-land-that-japan-holds)). What C costs Mongolia: once the KMT has attacked it, Mongolia can
fight on its own land but cannot strike back into China. If that seems wrong
for the game, it is a question for the game's developers.

**If answered.** The ruling becomes the next rule clarification, with the
engine, its test and the politics page changed in the same commit.

## Q-002: Chinese land that Japan holds

**The question.** Is an attack on a zone that was Chinese at the start, but
that a nation outside China now holds, an attack on China?

**What the engine does now.** It goes by who possessed the zone at the start,
not by who holds it now (`recordLandAttack` in `src/politics.cpp` asks
`originalNation` for the zone's first owner). It makes one exception, for a
zone that Dadao holds: an attack there is an attack on Dadao only.

**A real case** (random game, seed 7024;
[record](archive/records/answer_census_2026_11_15.md#mongolia-as-the-invader-of-china)).

1. Game round 1: the CCP attacks Mengjiang in Suiyuan, so Mengjiang joins the KMT
   with its land (rulebook 4.9, page 30).
2. Game round 2: Japan takes Suiyuan from the KMT. A Japanese infantry also attacks
   Kerulen, which puts Japan and Mongolia at war: an Axis major power may
   declare war on any nation outside the Axis, and on a minor power it does so
   by a land unit's combat move against it (rulebook 5.1, page 35).
3. Game round 3: a Mongolian cavalry moves into Suiyuan, now Japan's, as an attack.
   The engine treats that as Mongolia invading China: Mongolia is now also at
   war with the KMT and the CCP, neither of which had any part in the fight.

In the full game Mongolia would no longer exist at step 3. Japan's attack in
step 2 makes it align with the USSR at the end of Japan's Combat Phase, and it
is incorporated into the USSR (rulebook 4.7, page 29; 4.6, page 28). The attack
in step 3 would be the USSR's. Rule 4.5, which binds a controlled minor power,
would not apply to it; rule 5.1 forbids the USSR, too, to declare war on the
CCP. This campaign has no USSR and keeps Mongolia a nation of its own
(`mongolia_campaign_override` in `game_content/rules/gw36_politics_v43.json`),
so the case arises only here.

Read literally, the same rules keep the USSR out of every zone that was
originally a warlord's, the CCP's or the KMT's, including those Japan has
taken: it may not enter one without a declaration of war (rulebook 14.3,
page 101), an attack on one is a declaration of war on all of China (4.9,
page 30), and it may not declare war on the CCP (5.1, page 35). It can still
fight Japan in Manchukuo and Korea, which 4.9 does not name; holding all of
Manchukuo is one of its strategic objectives (page 23). The rules look built
for this: the USSR helps the CCP by rail (Comintern Brothers, 15.2, page 103)
and by an air transport that must land back in Soviet land (International Red
Aid, 15.3, page 105), and neither puts a Soviet unit in China.

**How often.** In 25 of the 70 games of Q-001 the zone Mongolia first attacked
was held by Japan; in the other 45 the KMT held it
([record](archive/records/answer_census_2026_11_15.md#mongolia-as-the-invader-of-china)).

**The printed rules.**

| Rule | What it says |
| --- | --- |
| 4.9, page 30 | It names the zones as those originally possessed by a warlord, the CCP or the KMT, and leaves out the Dadao Government, pointing to 15.4. |
| Glossary, page 7 | It defines "originally" by the roundel printed in the land zone on the map. |
| 14.3, page 101 | Without a declaration of war no other nation may enter land that was originally the KMT's, the CCP's or a warlord's; that the land is friendly makes no difference. |
| 15.4, page 105, and 4.7, page 29 | Dadao may attack Chinese land without the rest of China picking sides; if a nation that is not Chinese attacks Dadao, Dadao aligns with Japan. |
| 10.10.1, page 73 | A major power that conquers a zone of the Chinese Home Country it did not originally own keeps it or gives it to a Chinese faction. |

Rules 4.9 and 14.3 both name the zones by their printed owner, and 14.3 adds
that even a friendly zone counts. So the printed words agree with the engine.
Rule 10.10.1 shows that taking Chinese land can end with China getting it
back, but it does not say that attacking it is no attack on China.

**Why it matters.** A nation that fights Japan on land Japan has conquered ends
up at war with China as well.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Keep it: the printed owner decides, whoever holds the zone | Nothing. |
| B. Only a zone that the KMT, the CCP or a warlord holds counts | An attack on land held by a nation that is not Chinese is an attack on that nation only. No printed rule says this. A small change in `recordLandAttack` with a test. |

**Recommendation: A.** Two printed rules say it.

**This depends on Q-001.** If Q-001 is answered C, the case cannot arise in
this campaign: Mongolia then never attacks such a zone, and the only other
nation that is not Chinese is Japan, which is the holder here. But C rests on
rule 4.5, which binds Mongolia here only because this campaign keeps it a
minor power after Japan's attack; in the full game the same attack is the
USSR's, and 4.5 does not bind the USSR. Read literally, rules 14.3, 4.9 and
5.1 forbid the attack to the USSR all the same (above), so C agrees with the
full game. Only if the developers allow the USSR to attack Chinese land that
Japan holds is the recommendation to allow it to this campaign's Mongolia too,
once Japan has attacked it, and to apply C only to land a Chinese nation holds.

**If answered.** As for Q-001.

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
accepted both; two runs were stopped by hand.

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
