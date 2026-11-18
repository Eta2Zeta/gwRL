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
| [Q-003](#q-003-one-list-of-marks-for-each-kind-of-thing) | Should the network's input ask about a mark only where the engine can put it, and learn the four marks it does not know? | The network's input | Yes, before the next long run |
| [Q-004](#q-004-features-whose-value-never-changes) | Should the input drop features whose value never changes? | The network's input | Yes, in the same change as Q-003 |
| [Q-005](#q-005-the-supervisors-count-of-cores) | Should the supervisor keep training within the 9 cores by measuring the load, not by counting game processes? | Running training | Yes: measure, warn, and stop a run that stays over |
| [Q-006](#q-006-the-kmt-after-the-ccp-comes-back) | Once the CCP has been eliminated, may the KMT attack warlords and Mongolia for good, or only while the CCP has no units? | A printed rule | For good, as the printed words say |
| [Q-010](#q-010-one-network-for-the-three-alliances-by-default) | Should training keep one network for all three alliances by default, although its action probabilities fit its searches slightly less well? | Training | Yes: 22% faster, with values and held-out games alike |

Q-001 to Q-004 were raised on 14 November 2026, while the global features
about nations were being pruned (commit `bce7a4c`). Their numbers are in the
[record of which features random games give values to](archive/records/answer_census_2026_11_15.md).
Q-005 was raised on 15 November 2026, when the allowance became 9 cores (commit
`e62e01b`). Its numbers are in the
[record of training within nine cores](archive/records/nine_core_layouts_2026_11_15.md).
Q-006 was raised on 15 November 2026, while the printed sources of Q-001 were
being looked up; its numbers are in the first record. Q-010 was raised on 18
November 2026, from the matched runs that the answer to Q-009 asked for; its
numbers are in the
[record of that comparison](archive/records/one_network_comparison_2026_11_17.md).

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

## Q-003: One list of marks for each kind of thing

**The question.** Should the network's input ask about a mark only where the
engine can put that mark, and should it learn the four marks it does not know?

**What happens now.** The engine puts *marks* on things to remember what has
happened to them: on a unit that has moved, on a nation that has finished its
research this turn, on a city that is damaged, on a facility built this turn.
The code calls a mark a flag; the engine's mark table, `GWRL_MARKS` in
`include/game/marks.hpp`, lists every mark a state may hold
([names held as numbers](engine/names.md#what-a-mark-is)). The network's input has one feature for each
pairing of a thing and a mark
([the network's input](design/network_input.md#3-features-and-feature-values)). But
it keeps only two lists of marks, `kActorFlags` and `kRecordFlags` in
`src/zone_encoding.cpp`: one of 119 for units and nations together, and one of
108 for territories, facilities, construction projects, battles and the game
as a whole. So it asks about every pairing, including those that cannot
happen. `nation_flag:japan:air_battle` asks whether Japan, the nation, carries
the mark of a unit that is in an air battle. Only a unit ever gets that mark.

Of the layout's 59,235 features, 8,902 are about marks: 5,660 of the 42,532
zone features, 1,890 of the 4,076 global features and 1,352 of the 12,627
action features. In 480 random games, 290 of them ever had a non-zero value; of
the 1,560 that ask a nation about a mark, 88 did
([record](archive/records/answer_census_2026_11_15.md#which-questions-were-answered)). The engine's code puts 43
of the 119 marks on a nation and 11 of the 108 on the game as a whole; the
record [lists them](archive/records/answer_census_2026_11_15.md#the-marks-the-engine-puts-on-a-nation) with the
source files that write each. A change would have to make such a list for
every kind of thing.

**Four marks are on no list.** With Improved Construction, a factory or a city
takes less damage from strategic bombing in each player turn: a minor factory
1 less, a medium factory 3, a major factory 5, a city 5 (rulebook 8.2.1,
page 46). The engine notes on the nation that holds the factory or the city
how much has been taken off this turn, in four marks: `bombing_reduction` and
`bombing_reduction_turn` (`applyFacilityBombDamage` in `src/air.cpp`), and
`city_bombing_reduction` and `city_bombing_reduction_turn`
(`applyCityBombDamage`, the same file). The input has no feature for any of
them. Put on Japan by hand, the first pair arrives as
`nation_flag:japan:other = 3` and the second as `nation_flag:japan:other = 5`,
which says only that Japan carries some unlisted mark, and the name check
reports them ([record](archive/records/answer_census_2026_11_15.md#four-marks-without-a-question)). No random
game has reached this: it needs a nation that has completed Improved
Construction to be bombed. The engine's mark table lists them, and the test
that checks every mark in it has a feature (`test_marks` in
`tests/test_campaign_zone_encoding.py`) names these four as the ones this
question leaves open.

**Why it matters.** Play is not affected: the rules are applied. For learning,
the features that can never have a non-zero value cost no time, because a
feature whose value is 0 is never read, but their embeddings never train and
they make the layout harder to read. The four missing marks mean the network cannot see how much of
a factory's or a city's protection is already used up, which matters to a
player choosing what to bomb next. That is rare.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Give each kind of thing its own list, and add the four marks | One layout change, so networks trained before it no longer load; those so far are experiments. Work of about the size of the pruning of 14 November (commit `bce7a4c`): each mark of the engine's table is given the kinds of thing it can be on, and a test keeps the lists in step with the table. Most of the 8,902 features go. |
| B. Only add the four marks | A small layout change. The features that can never have a non-zero value stay. |
| C. Leave it | Nothing changes. The name check reports the four marks if a game ever reaches them. |

**Recommendation: A, before the next long training run.** After a long run a
layout change costs the networks it trained.

**If answered.** The lists and the reason for each belong in
[the network's input, section 8](design/network_input.md#8-features-removed-as-impossible),
which now describes the gap.

## Q-004: Features whose value never changes

**The question.** Should the input drop features that have the same value in
every state, and features that always repeat another feature?

**What happens now.** The engine leaves 37 global features only one possible value:

| Features | How many | Always | Where that is settled |
| --- | ---: | --- | --- |
| `nation_present` for every nation but Dadao | 12 | 1 | `loadScenario` in `src/campaign_setup.cpp` creates these twelve nations, and no code removes a nation |
| `alliance` and `player` of Japan, the KMT, the CCP and Mongolia | 8 | 1 | `alliancePossible` in `src/politics.cpp`: each keeps its alliance and its player for good |
| `power_status` of Japan, Mongolia and the eight warlords | 10 | 1 | `powerStatusPossible`, the same file: Japan is always a major power, Mongolia a minor one, a warlord a warlord |
| `controller` of Japan, the KMT, the CCP and Mongolia | 4 | 1 | `controllerPossible`, the same file: the first three under themselves, Mongolia under nobody |
| `at_war` between the KMT and the CCP, both ways | 2 | 1 | They start at war (`china_minor_setup.json` of the scenario), and the engine ends a war only for a nation that is incorporated (`incorporateNation`), which these two never are. Under the Truce it treats them as friends while the war stays recorded (`politicallyFriendly`) |
| `state_flag:__campaign_started` | 1 | 1 | `Engine::start` in `src/campaign_runtime.cpp` sets it once |

The reasons for the middle three rows are in
[what the global features ask about a nation](design/network_input.md#what-the-global-features-ask-about-a-nation).

And every `player` feature always has the value of the `alliance` feature
for the same nation: a nation's player is the agent that decides for it, and in
this campaign each alliance is one agent
([approved scenario decisions](plans/japan_china_full_rules_plan.md#approved-scenario-decisions);
the rule `alliancePossible` covers both). In 710,254 encoded states none of
these ever differed ([record](archive/records/answer_census_2026_11_15.md#which-questions-were-answered)). At
decision 612, the example of the
[design document](design/README.md#52-three-parts-zone-features-global-features-and-action-features),
45 of its 176 non-zero global feature values are of these kinds; its feature
values are listed in the [record of that training sample](archive/records/training_sample_2026_11_05.md).

Sixteen features of this kind were removed on 14 November 2026: thirteen that
said a nation's income had been worked out (commit `c998709`), and three that
said Japan, the KMT and the CCP keep a treasury (commit `bce7a4c`).

**Why it matters.** Little. A feature with the same value everywhere cannot
tell two states apart, so the network learns nothing from it: its embedding is a
constant added to every state. Unlike a feature whose value is always 0, it is
read at every network evaluation: 45 of the 1,096 embeddings that decision 612
looks up
([its size](design/README.md#69-the-whole-network)). Whether that shows in
speed has not been measured.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Remove the 37 fixed features and the `player` family | 71 features go, leaving 4,005 global features. A layout change. The encoder reports any state that breaks one of these rules, as it does for a missing treasury. |
| B. Remove only the 37 fixed features | 4,039 global features remain. `player` stays, in case an alliance is ever given more than one player. |
| C. Keep them | Nothing changes. |

**Recommendation: A, in the same layout change as Q-003.** Nothing the network
can learn is lost either way, so this is tidiness. Keeping the features as a
plain record of who is who costs almost nothing, so C is a fair choice too.

**If answered.** The removed features join the list in
[the network's input, section 8](design/network_input.md#8-features-removed-as-impossible).

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

**Why it matters.** The allowance is there to keep one performance core free
for everything else. The count does not show whether it is free, and even a
layout chosen by measuring it goes over when the Mac is quiet. A different network, device,
number of games per process or search would change the load without the
supervisor noticing. The count can also be too strict: with the network on the
GPU, game threads wait more and use less than they count.

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

## Q-010: One network for the three alliances by default?

**The question.** Should training keep one network for all three alliances by
default (`--networks one`)? In matched runs it was 22% faster and as good in its
values and in held-out games, but its action probabilities fit its searches
slightly less well.

**What the program does now.** Training keeps a network for each alliance
unless the training command adds `--networks one` (`RunConfig.networks` in
`studies/campaign/run.py`, default `three`). The owner's answer to
[Q-009](#answered) was to compare the two in matched runs and keep one network
if it learns at least as well.

**A real case** (the night of 17 November, one run of each, 3.7 hours of
training each, fresh 64×2 networks, eleven-round games, the Mac profile;
[record](archive/records/one_network_comparison_2026_11_17.md)):

- **Speed.** One network played 395,060 decisions an hour, 21.6% more than
  three networks while the Mac's other work was as light. The inference server
  sets the pace of self-play on the Mac, and with one network its forward pass
  took 20% less time per network evaluation and a network update 61% less time.
- **Values.** On each game before training on it, the two runs' value heads
  explained about the same share of the variance of the final scores after the
  first hour: 15.4% with one network and 13.1% with three.
- **Action probabilities.** The one network's action probabilities lay further
  from its searches' visit shares: a KL divergence of 0.273 against 0.252 after
  the first hour, at Axis decisions 0.318 against 0.289, at Comintern decisions
  about equal. This is the one measure where one network learned less well. The
  visit shares themselves were spread alike in both runs.
- **Held-out games.** Against the scripted opponents on 16 seeds per alliance,
  the two runs' last networks scored alike: one network minus three, Axis
  +1.9 ± 3.5, Allies +14.2 ± 8.0, Comintern −1.1 ± 4.7 points. These games
  cannot yet tell the better learner: in both runs the trained Axis scored about
  33 points below the untrained one, which does almost nothing and scored best
  (see [the objective](design/README.md#is-the-final-wealth-gap-the-right-goal)).

**Why it matters.** The rule "at least as well" holds for the values and, as far
as 16 seeds can tell, for the held-out games, but not for the action
probabilities, which fit the searches 0.02 less well (8%). The cause is not
measured; one candidate is that one 64×2 network holds three alliances'
strategies in a third of the parameters of three networks. The speed is more
training in the same night: on the Mac, 22% more games and network updates. On
the Mac's GPU, where larger networks would run, one network's forward pass took
15% to 38% less time on saved inference batches
([record](archive/records/network_split_2026_11_17.md#inference-batches-on-the-gpu)),
and a compiled forward pass of one network needs fixed sizes only for the whole
inference batch
([section 9.3](design/README.md#93-what-a-larger-network-and-a-longer-search-cost)).
The GPU forward pass, the next piece of speed work, would be built for whichever
setup is the default.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. One network by default | Self-play about 22% faster on the Mac at 64×2, and the GPU forward pass built for one network. Its action probabilities fit the searches 0.02 less well at this size. Every run records that fit by alliance (`fresh_games` in `manifest.json`), so a gap at larger sizes would show, and `--networks three` stays available. |
| B. Three networks by default | No change; one network stays an option. The GPU forward pass is built for three networks, which needs a split by network or padding (section 9.3). |
| C. Compare once more first | Matched runs with one network given more parameters, at about the forward-pass cost of three 64×2 networks, to see whether the gap comes from size. One more night, and the GPU work waits for it. |

**Recommendation: A.** It departs from the rule as written, since one of the
three measures is slightly worse. But that shortfall is small, measured at the
smallest network size, and recorded by every run, while the speed is 22% more
training every night. If larger networks still show the gap, three networks are
one option away.

**If answered.** The default and the reason for it belong in
[one training step](design/README.md#84-one-training-step-and-one-network-update),
in the
[open question](design/README.md#one-network-per-alliance-or-one-shared-network)
of the design document, and in the campaign guide's paragraph on `--networks`
([campaign learning guide](../studies/campaign/README.md)).

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
  [the open question](design/README.md#one-network-per-alliance-or-one-shared-network)
  and [one training step](design/README.md#84-one-training-step-and-one-network-update).
