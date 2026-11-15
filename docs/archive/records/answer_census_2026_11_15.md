# Which questions random games answer — 15 November 2026

The network's input asks 59,235 fixed questions
([the network's input](../../design/network_input.md)). This record counts
which of them random games ever answer, how often Mongolia is recorded as the
invader of China, and what the input does with two marks it does not list. The
numbers are the evidence for the
[questions waiting for a decision](../../questions.md) that were raised on
14 November 2026. The [data file](answer_census_2026_11_15.json) holds every
count.

## Setup

Commit `bce7a4c`, layout `campaign-zone-v1-9e192fe5c085f13e`.
`tools/answer_census.py` played 480 eleven-round games, seeds 7000 to 7239 and
9000 to 9239, through the environment training uses (`make_env`), on 8 worker
processes of the M4 Max, in 3 minutes 38 seconds. The games are those of
`tools/check_zone_names.py`: every move is drawn uniformly at random, except
that where the phase can end it is ended with probability 2%, 5% or 10%,
depending on the seed. Every decision and every dice position was encoded:
627,342 decisions and 82,912 dice positions, 710,254 encoded positions in all.
No name was reported as unknown.

```sh
./.venv/bin/python tools/answer_census.py OUT.json --first-seed 7000 9000 --games 240 --workers 8 --detail position
```

## Which questions were answered

A question counts as answered if at least one encoded position gave it an
answer other than 0. A *mark question* is one of a family that asks about
marks, listed in the second table.

| Part | Questions | Answered | Mark questions | Mark questions answered |
| --- | ---: | ---: | ---: | ---: |
| The board, for each zone | 42,532 | 3,158 | 5,660 | 106 |
| The position | 4,076 | 843 | 1,890 | 124 |
| A move | 12,627 | 1,810 | 1,352 | 60 |
| All three | 59,235 | 5,811 | 8,902 | 290 |

| Part | Family of mark questions | Questions | Answered |
| --- | --- | ---: | ---: |
| Board | `unit_flag` | 1,920 | 30 |
| Board | `facility_flag` | 1,744 | 33 |
| Board | `nation_flag_here` | 1,560 | 16 |
| Board | `project_flag` | 218 | 10 |
| Board | `battle_flag` | 109 | 16 |
| Board | `territory_flag` | 109 | 1 |
| Position | `nation_flag` | 1,560 | 88 |
| Position | `unsited_project_flag` | 218 | 26 |
| Position | `state_flag` | 109 | 8 |
| Position | `state_flag_nation` | 3 | 2 |
| Move | `unit_cargo_flag` | 480 | 19 |
| Move | `project_flag` | 436 | 25 |
| Move | `facility_flag` | 436 | 16 |

The data file lists every answered position question with the number of
positions and games that answered it and its smallest and largest answer, and
for the board and the moves the count of each family.

**Answered alike everywhere.** 41 position questions were answered in every one
of the 710,254 positions, always with the same answer:

| Questions | How many | Can the rules give another answer? |
| --- | ---: | --- |
| `nation_present` for every nation but Dadao | 12 | No: these nations are in the game from the start and never leave it |
| `alliance` and `player` of Japan, the KMT, the CCP and Mongolia | 8 | No ([what the position asks about a nation](../../design/network_input.md#what-the-position-asks-about-a-nation)) |
| `power_status` of Japan, Mongolia and the eight warlords | 10 | No |
| `controller` of Japan, the KMT, the CCP and Mongolia | 4 | No |
| `at_war` between the KMT and the CCP, both ways | 2 | Not in the engine: they start at war and it never ends that war; under the Truce it treats them as friends while the war stays recorded |
| `state_flag:__campaign_started` | 1 | No: the engine sets it when the campaign starts |
| `interrupt_order`: Axis first, Allies second, Comintern third | 3 | Not as the scheduler is written: it offers out-of-turn moves in a fixed order |
| `nation_flag:ccp:economy_research_finished` | 1 | Yes: it is 0 while a CCP that has become a major power still has research to do, which never happened |

Every `player` answer was the same as the `alliance` answer for the same
nation and side, in every position.

## Mongolia as the invader of China

The engine records an invasion of China when a nation that is not Chinese
attacks a land zone that was originally a warlord's, the CCP's or the KMT's
(rulebook 4.9; `recordLandAttack` in `src/politics.cpp`). In 70 of the 480
games that nation was Mongolia, 109 times in all. The first time in each game:

| | Games of 70 |
| --- | ---: |
| The attacked zone was held by the KMT | 45 |
| The attacked zone was held by Japan | 25 |
| Mongolia came to be at war with the CCP | 70 |
| Mongolia also came to be at war with the KMT | 23 |
| A warlord had not yet joined a side | 1 |
| The CCP still had units | 27 |

Before the attack Mongolia was at war with Japan and the KMT in 32 games, with
Japan alone in 23 and with the KMT alone in 15. Of the 109 attacked zones, 106
were originally a warlord's and 3 the CCP's. Three of the later attacks were on
zones the CCP itself held: once at war, the two Comintern nations fought.

Two of the games, move by move:

- **Seed 7155, a zone held by the KMT.** In round 1 the CCP attacks the Ma
  Clique in Tsinghai, which therefore joins the KMT with its land at the end of
  that Combat Phase. Later in the round the KMT destroys the CCP's last units.
  In round 2 a KMT infantry attacks Ulyassutai, which the rules allow once the
  CCP has been eliminated, so the KMT and Mongolia are at war. In round 3 a
  Mongolian cavalry moves from Kerulen through Central Mongolia into Tsinghai
  to attack (decision 342). From that move on Mongolia is at war with the CCP.
- **Seed 7024, a zone held by Japan.** In round 1 the CCP attacks Mengjiang in
  Suiyuan, which joins the KMT. In round 2 Japan attacks Suiyuan and takes it,
  and a Japanese infantry attacks Kerulen, so Japan and Mongolia are at war. In
  round 3 a Mongolian cavalry moves from Kobdo through Central Mongolia into
  Suiyuan to attack the Japanese there (decision 379). From that move on
  Mongolia is at war with the KMT and the CCP as well.

These events were found by playing the same games again and reading the state
after each move made on Mongolia's turn. The script is not kept; the data file
lists the first event of each game with its seed and decision number, so each
can be checked by replaying the seed with the policy above.

## Two marks without a question

`applyFacilityBombDamage` in `src/air.cpp` writes two marks on a nation whose
factory absorbs bombing damage under Improved Construction: `bombing_reduction`
and `bombing_reduction_turn`, each followed by the facility's name. Neither is
on the input's list of marks. No game above reached them. To see what the input
does with them, an opening position was given both on Japan, with the values 2
and the current turn, and encoded: the input reported
`actor_flag:bombing_reduction` and `actor_flag:bombing_reduction_turn` as
unknown names and answered `nation_flag:japan:other = 3`.

## What this shows and what it does not

- **Not answered is not impossible.** Random games never signed the Chinese
  Truce and never saw a surrender, and both are in the rules. Only the rules
  can show that a question cannot be answered.
- **Random play is not trained play.** How often trained agents would meet
  Mongolia's invasions is not measured. Random play meets them in one game in
  seven, from round 3 on, so they are not a corner that play never reaches.
- **Answered alike in 710,254 positions is not proof either.** The table says
  for each group whether the rules allow another answer; that part is read
  from the code, not measured.
