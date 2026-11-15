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
- **Numbers cited here come from a dated record** in the
  [archive](archive/README.md), which says how they were measured.

Other open things stay in the pages that own them, and
[Open elsewhere](#open-elsewhere) lists them.

## Open questions

| Number | Question | About | Recommended |
| --- | --- | --- | --- |
| [Q-001](#q-001-mongolia-at-war-with-the-ccp) | When Mongolia attacks land that was Chinese at the start, is it then at war with the CCP? | A printed rule | No |
| [Q-002](#q-002-chinese-land-that-japan-holds) | Is an attack on Chinese land that Japan now holds an attack on China? | A printed rule | No |
| [Q-003](#q-003-one-list-of-marks-for-each-kind-of-thing) | Should the network's input ask about a mark only where the engine can put it, and learn the two marks it does not know? | The network's input | Yes, before the next long run |
| [Q-004](#q-004-questions-whose-answer-never-changes) | Should the input stop asking questions whose answer never changes? | The network's input | Yes, in the same change as Q-003 |

All four were raised on 14 November 2026, while the position questions about
nations were being pruned (commit `bce7a4c`). Their numbers are in the
[record of 15 November](archive/records/answer_census_2026_11_15.md).

## Q-001: Mongolia at war with the CCP

**The question.** When Mongolia attacks land that was Chinese at the start of
the game, should it come to be at war with the CCP, which belongs to its own
alliance and is played by the same player?

**What the engine does now.** Rulebook 4.9 (page 30) says that an attack by a
foreign nation on a land zone that was originally a warlord's, the CCP's or
the KMT's counts as a declaration of war on all of China. The engine applies
this to every attacker that is not Chinese, so to Japan and to Mongolia. It
puts the attacker at war with the KMT, the CCP and every warlord that has not
yet joined a side, and those warlords then pick a side at the end of that
Combat Phase (`recordLandAttack` in `src/politics.cpp`;
[politics](engine/politics.md#2-the-warlords)). Mongolia cannot declare war
itself, so it attacks such a zone only when the nation holding it is already at
war with Mongolia, or when nobody holds it.

**A real case** (random game, seed 7155). In round 1 the CCP attacks the Ma
Clique in Tsinghai, which therefore joins the KMT with its land. Later in the
round the KMT destroys the CCP's last units. In round 2 the KMT attacks
Mongolia, which the rules allow once the CCP has been eliminated, so the KMT
and Mongolia are at war. In round 3 a Mongolian cavalry moves into Tsinghai,
which the KMT holds, as an attack. The engine records Mongolia as invading
China, and from that move on Mongolia and the CCP are at war. Both are Comintern nations, and
the Comintern player decides for both.

**How often.** In 480 random games Mongolia was recorded as the invader in 70,
from round 3 on, and in all 70 it came to be at war with the CCP. Three times
Mongolia then attacked land the CCP held.

**Why it matters.** Two nations of one alliance, moved by one player, become
enemies: their units may attack each other and neither may enter the other's
land in peace. No player of the board game would expect that, and the
Comintern's network is trained on such positions. It is also against another
printed rule: rulebook 5.1 (page 35) says a nation may not declare war on a
member of its own alliance, and its table answers "No" for the USSR and for
the CCP against other Comintern nations. Rule 4.7 (page 29) makes Mongolia a
Comintern minor power controlled by the USSR; this campaign leaves the USSR
out and lets the Comintern player move Mongolia
([approved scenario decisions](plans/japan_china_full_rules_plan.md#approved-scenario-decisions)).
So 4.9 and 5.1 give different answers. The full game would have the same
conflict if the USSR attacked such a zone.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Keep it: rule 4.9 is followed to the letter | Nothing. |
| B. Rule 5.1 wins: an attack never puts a nation at war with its own alliance | Mongolia's attack still counts as an invasion and puts it at war with the KMT and with warlords that have not joined a side, but not with the CCP. A small change in `recordLandAttack` with a test; the two `at_war` questions between Mongolia and the CCP can then leave the network's input. |
| C. Such an attack is not allowed | Mongolia may not attack land that was originally Chinese at all, because that would declare war on its own alliance. Stricter than B, and it needs a check where moves are listed. |

**Recommendation: B.** Rule 5.1 is the rule about who may be at war with whom,
and nothing in the rules suggests that the Comintern's nations should fight
each other. This is a reading, not something the rulebook says outright; it is
the kind of question that has been put to the game's developers before.

**If answered.** The ruling becomes the next rule clarification, with the
engine, its test and the politics page changed in the same commit.

## Q-002: Chinese land that Japan holds

**The question.** Is an attack on a zone that was Chinese at the start, but
that a nation outside China now holds, an attack on China?

**What the engine does now.** The same rule, 4.9, names the zones by who
*originally* possessed them, and the rulebook's glossary (page 7) defines
"originally" as the nation whose roundel is printed in the zone. The engine
follows that: what counts is whose zone it was at the start, not who holds it
now. Only zones held by Dadao are left out, as the rule says.

**A real case** (random game, seed 7024). In round 1 the CCP attacks Mengjiang
in Suiyuan, which therefore joins the KMT. In round 2 Japan takes Suiyuan from
the KMT and also attacks Mongolia, so Japan and Mongolia are at war. In round 3
a Mongolian cavalry moves into Suiyuan, now Japan's, as an attack. The engine
treats that as Mongolia invading China: Mongolia is now also at war with the
KMT and the CCP, neither of which had any part in the fight.

**How often.** In 25 of the 70 games of Q-001 the zone Mongolia first attacked
was held by Japan; in the other 45 the KMT held it.

**Why it matters.** A nation that fights Japan on land Japan has conquered ends
up at war with China as well. The rule would work the
same way against Japan: attacking a Chinese zone that Mongolia had taken would
count as a new attack on China.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Keep it: the printed roundel decides, whoever holds the zone | Nothing. |
| B. Only a zone that the KMT, the CCP or a warlord holds counts | An attack on land held by a nation that is not Chinese is an attack on that nation only. A small change in `recordLandAttack` with a test. |

**Recommendation: B**, but with less confidence than for Q-001. The purpose of
the rule is that invading any part of China brings war with all of China, and
attacking Japan's troops is not invading China. Rulebook 10.10.1 (page 73) even
lets a major power that conquers Chinese land give it to the KMT or the CCP.
But the printed words support A, so this too is one to ask the developers.

**If answered.** As for Q-001. The two can be answered separately: with B
here and A for Q-001, Mongolia would still come to be at war with the CCP by
attacking a zone the KMT holds.

## Q-003: One list of marks for each kind of thing

**The question.** Should the network's input ask about a mark only where the
engine can put that mark, and should it learn the two marks it does not know?

**What happens now.** The engine puts *marks* on things to remember what has
happened to them: on a unit that has moved, on a nation that has finished its
research this turn, on a city that is damaged, on a facility built this turn.
The code calls a mark a flag. The network's input asks one question for each
pairing of a thing and a mark
([the network's input](design/network_input.md#3-questions-and-answers)). But
it keeps only two lists of marks: one of 119 for units and nations together,
and one of 108 for territories, facilities, construction projects, battles and
the game as a whole. So it asks about every pairing, including those that
cannot happen. `nation_flag:japan:air_battle` asks whether Japan, the nation,
carries the mark of a unit that is in an air battle. Only a unit ever gets
that mark.

Of the layout's 59,235 questions, 8,902 are about marks: 5,660 of the 42,532 a
zone answers, 1,890 of the position's 4,076 and 1,352 of a move's 12,627. In
480 random games, 290 of them were ever answered. Of the 1,560 that ask a
nation about a mark, 88 were. By a reading of the code, 43 of the 119 marks
are ever put on a nation and 11 of the 108 on the game as a whole; a change
would have to confirm such a count for every list.

**Two marks are on no list.** With Improved Construction a factory absorbs the
first points of bombing damage in a turn: 1 for a minor factory, 3 for a medium
one, 5 for a major one. The engine notes on the factory's nation how much the
factory has absorbed this turn, in two marks, `bombing_reduction` and
`bombing_reduction_turn` (`applyFacilityBombDamage` in `src/air.cpp`). The
input has no question for either. Put on Japan by hand, they arrive as
`nation_flag:japan:other = 3`, which says only that Japan carries some unlisted
mark, and the name check reports them. No random game has reached this: it
needs a nation that has completed Improved Construction to have a factory
bombed. The test that reads the engine's source for marks missed them because
the engine builds their names in a variable.

**Why it matters.** Play is not affected: the rules are right. For learning,
the questions that can never be answered cost no time, because an unanswered
question is never read, but their rows never train and they make the layout
harder to read. The two missing marks mean the network cannot see how much of a
factory's protection is already used up, which matters to a player choosing
what to bomb next. That is rare.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Give each kind of thing its own list, and add the two marks | One layout change, so networks trained before it no longer load; those so far are experiments. Work of about the size of the pruning of 14 November: every place where the engine writes a mark is listed, and a test keeps the lists in step with the source. Most of the 8,902 questions go. |
| B. Only add the two marks | A small layout change. The questions that cannot be answered stay. |
| C. Leave it | Nothing changes. The name check reports the two marks if a game ever reaches them. |

**Recommendation: A, before the next long training run.** After a long run a
layout change costs the networks it trained.

**If answered.** The lists and the reason for each belong in
[the network's input, section 8](design/network_input.md#8-questions-removed-as-impossible),
which now describes the gap.

## Q-004: Questions whose answer never changes

**The question.** Should the input stop asking questions that every position
answers alike, and questions that always repeat another question?

**What happens now.** The rules leave 37 position questions only one answer:

| Questions | How many | Always |
| --- | ---: | --- |
| `nation_present` for every nation but Dadao | 12 | 1: they are in the game from the start and never leave it |
| `alliance` and `player` of Japan, the KMT, the CCP and Mongolia | 8 | 1: each keeps its alliance and its player for good |
| `power_status` of Japan, Mongolia and the eight warlords | 10 | 1: Japan is always a major power, Mongolia a minor one, a warlord a warlord |
| `controller` of Japan, the KMT, the CCP and Mongolia | 4 | 1: the first three under themselves, Mongolia under nobody |
| `at_war` between the KMT and the CCP, both ways | 2 | 1: they start at war and the engine never ends that war, even under the Truce |
| `state_flag:__campaign_started` | 1 | 1 |

And every `player` question always has the answer of the `alliance` question
for the same nation: a nation's player is the agent that decides for it, and in
this campaign each alliance is one agent. In 710,254 encoded positions none of
these ever differed. At decision 612, the example of the
[design document](design/README.md#52-three-parts-the-board-the-position-and-the-moves),
45 of the position's 176 answers are of these kinds.

Sixteen questions of this kind were removed on 14 November 2026: thirteen that
said a nation's income had been worked out, and three that said Japan, the KMT
and the CCP keep a treasury.

**Why it matters.** Little. A question answered alike everywhere cannot tell
two positions apart, so the network learns nothing from it: its row is a
constant added to every position. Unlike a question that is never answered, it
is read at every evaluation: 45 of the 1,096 rows that decision 612 looks up.
Whether that shows in speed has not been measured.

**The choices.**

| Choice | What it changes |
| --- | --- |
| A. Remove the 37 fixed questions and the `player` family | 71 questions go, and the position part has 4,005. A layout change. The encoder reports any position that breaks one of these rules, as it does for a missing treasury. |
| B. Remove only the 37 fixed questions | The position part has 4,039. `player` stays, in case an alliance is ever given more than one player. |
| C. Keep them | Nothing changes. |

**Recommendation: A, in the same layout change as Q-003.** Nothing the network
can learn is lost either way, so this is tidiness. Keeping the questions as a
plain record of who is who costs almost nothing, so C is a fair choice too.

**If answered.** The removed questions join the list in
[the network's input, section 8](design/network_input.md#8-questions-removed-as-impossible).

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

None yet. An answered question is listed here with its number, the answer, the
date and the page that now states it.
