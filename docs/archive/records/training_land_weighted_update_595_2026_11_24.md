# The training run under the land-weighted score at its 595th network update — 24 November 2026

The training run under the land-weighted score
(`studies/campaign/runs/training-land-weighted-2026-11-22`, commit `1101c2e`)
reached its 595th network update at 07:39 on 24 November 2026, after 35.38
hours of play, 9,520 complete self-play games and 8,724,175 decisions, all in
its first part, `1-memory-checked`. The owner asked then how it was going, how
likely it was that the memory check should have found the game process crash by
then, and how the networks and their scores were. This record measures the
595th network update as the [record of the
363rd](training_land_weighted_update_363_2026_11_23.md) measured that one, with
the same scripts, except that the network now plays all 24 held-out seeds: the
[record of the 24 seeds](training_land_weighted_24_seeds_2026_11_23.md) showed
that six seeds can make two networks that score the same look 10 points apart.
The [evidence file](training_land_weighted_update_595_2026_11_24.json) holds
every number below, read from the part's `manifest.json`, from
`tools/compare_training_runs.py` and from the reports and scripts in the run's
`evaluations` folder (`make_record_595.py` writes it).

## Self-play

An alliance's final score is its wealth minus the other two alliances' wealth
combined; at the start of every game the wealth would give +29.1 to the Axis,
−45.5 to the Allies and −57.5 to the Comintern. One network plays all three
alliances. Means over the games of each block of about 40 network updates since
the 363rd, beside the first block and the last block of the [record of the
363rd network update](training_land_weighted_update_363_2026_11_23.md#self-play),
with the standard error of each mean in brackets:

| Network updates | Games | Decisions, median | The Axis's decisions | Land battles begun a game | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | 320 | 699 | 258 | 7.5 | +18.6 (0.6) | −44.9 (0.5) | −76.2 (0.5) |
| 341 to 363 | 368 | 872 | 531 | 16.7 | +24.6 (0.3) | −50.1 (0.4) | −68.3 (0.4) |
| 364 to 400 | 592 | 761 | 389 | 13.4 | +25.1 (0.2) | −50.5 (0.3) | −68.9 (0.3) |
| 401 to 440 | 640 | 758 | 390 | 12.1 | +24.9 (0.2) | −50.6 (0.3) | −69.0 (0.3) |
| 441 to 480 | 640 | 777 | 404 | 11.7 | +24.8 (0.2) | −51.0 (0.3) | −68.7 (0.3) |
| 481 to 520 | 640 | 760 | 387 | 10.6 | +25.2 (0.2) | −51.6 (0.3) | −68.5 (0.3) |
| 521 to 560 | 640 | 723 | 354 | 11.6 | +25.2 (0.2) | −51.7 (0.3) | −68.4 (0.3) |
| 561 to 595 | 560 | 800 | 416 | 14.0 | +24.8 (0.2) | −50.2 (0.4) | −68.3 (0.3) |

The land zones each alliance held at the end of a game, means over the same
games:

| Network updates | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: |
| At the start | 11 | 5 | 5 |
| 1 to 20 | 11.8 | 9.4 | 6.4 |
| 341 to 363 | 11.7 | 7.3 | 6.4 |
| 364 to 400 | 11.8 | 7.2 | 6.3 |
| 401 to 440 | 11.7 | 7.1 | 6.5 |
| 441 to 480 | 11.7 | 7.0 | 6.6 |
| 481 to 520 | 11.7 | 6.8 | 6.7 |
| 521 to 560 | 11.7 | 6.9 | 6.6 |
| 561 to 595 | 11.7 | 7.1 | 6.5 |

Actions a game, all nations together; a fleet move takes at least two
decisions and a flight in Noncombat Movement two, as the [record of the 288th
network update](training_land_weighted_update_288_2026_11_23.md#self-play)
explains:

| Network updates | Fleet moves | Land-unit moves | Flights in Noncombat Movement | Landings in Noncombat Movement | Purchases |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | 23.0 | 172.3 | 3.5 | 3.9 | 68.8 |
| 341 to 363 | 92.1 | 108.7 | 22.6 | 27.5 | 83.0 |
| 364 to 400 | 50.3 | 94.8 | 15.5 | 18.0 | 82.3 |
| 401 to 440 | 54.9 | 96.3 | 12.7 | 14.7 | 82.0 |
| 441 to 480 | 61.4 | 109.8 | 9.6 | 13.6 | 83.2 |
| 481 to 520 | 54.1 | 106.7 | 9.4 | 13.4 | 84.1 |
| 521 to 560 | 45.9 | 97.8 | 8.4 | 12.3 | 81.6 |
| 561 to 595 | 60.2 | 109.2 | 16.5 | 18.9 | 81.2 |

The alliances' wealth at the end of a game, in the last block of the record of
the 363rd network update and the last block here, with units, infrastructure,
treasury and paid construction at their price in IPP, of which wealth counts a
twentieth:

| Network updates | Alliance | Wealth | Land zones | Income | Units | Infrastructure | Treasury | Paid construction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 341 to 363 | Axis | 59.2 | 11.7 | 15.0 | 386 | 166 | 46 | 52 |
| 561 to 595 | Axis | 59.3 | 11.7 | 15.0 | 395 | 176 | 22 | 57 |
| 341 to 363 | Allies | 21.9 | 7.3 | 8.2 | 84 | 33 | 9 | 0 |
| 561 to 595 | Allies | 21.8 | 7.1 | 8.0 | 91 | 31 | 12 | 0 |
| 341 to 363 | Comintern | 12.8 | 6.4 | 3.1 | 55 | 7 | 3 | 0 |
| 561 to 595 | Comintern | 12.7 | 6.5 | 3.2 | 50 | 7 | 4 | 0 |

In the 232 network updates since the 363rd the self-play final scores did not
move: the Axis's stayed between +24.8 and +25.2, the Allies' between −50.2 and
−51.7 and the Comintern's between −68.3 and −69.0, and each alliance ended its
games with the land zones it had ended them with before. The games got shorter
again: from a median of 872 decisions to 723 to 800, with about half the fleet
moves and fewer land battles, 10.6 to 14.0 a game instead of 16.7. The Axis
ended its games with half the treasury, 22 IPP instead of 46, and 10 IPP more
of infrastructure.

## Who fought in the self-play games that finished from 07:42 to 07:57

As at the 288th and 363rd network updates, `collect_finished_games.sh` kept the
move logs of the self-play games that finished while it ran, from 07:42 to
07:57: 31 games, whose training samples went into network updates 596 to 598.
They were fewer than the 66 of the evening before because the held-out games
of this record, started at 07:41, slowed the run (see [Speed](#speed)).
`self_play_finished.py` replayed them without searching. The copies hold 395 of
the 410 land battles that the part's manifest counts for these games; the
missing ones fell in the last game round, of which the copies hold only a part.
Means a game, by the nation that began the battles or lost the units:

| Nation | Land battles begun | Units lost |
| --- | ---: | ---: |
| KMT | 8.42 | 10.6 |
| CCP | 3.55 | 6.5 |
| Japan | 0.35 | 4.4 |
| Dadao | 0.29 | 0.9 |
| Mongolia | 0.13 | 0.4 |
| The warlords | 0 | 0.1 |

A land zone passed from a warlord to the KMT 2.10 times a game, from a warlord
to the CCP 1.00 times, from a warlord to Dadao 0.77 times, from the KMT to the
CCP 0.68 times, from the CCP to the KMT 0.39 times, from Mongolia to Japan 0.26
times and from Dadao to the KMT 0.19 times.

Japan began its 11 land battles in 3 of the 31 games, all against Mongolia, a
nation of the Comintern. Dadao began its 9 in 4 games, all against Hopeh, held
by the KMT or the CCP; in three of those games Dadao had won Hopeh from its
warlord without a land battle and then lost it to them. Three of Dadao's
battles took Hopeh, and each time Dadao lost it again in the same game round.
Japan's three games:

- In one it began 7 land battles from game round 4 on. It took Kerulen from
  Mongolia in game round 4 and Central Mongolia in game round 5, lost Central
  Mongolia to the KMT in game round 8 and took it back in game round 9, took
  Kobdo in game round 10, after attacks that failed in game rounds 7 and 8,
  and Ulyassutai in game round 11. It held all four zones of Mongolia in the
  last game round the copy reached.
- In another it took Kerulen in game round 9 and Central Mongolia in game round
  10, lost Central Mongolia to Mongolia and took it back in game round 11, and
  held both.
- In the third it took Kerulen in game round 11.

In none of the 31 games did Japan hold a zone of China in the last game round
the copy reached. Where Japan took land in these games, it took it from
Mongolia.

## Speed

In blocks of about 40 network updates since the 363rd, beside the last speed of
the record of the 363rd network update:

| Network updates | Hours of play | Games an hour | Decisions an hour | Network updates an hour | Network evaluations an hour | Forward-pass time per network evaluation | Network evaluations an inference batch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 321 to 363 | 2.77 | 249 | 248,005 | 15.5 | 3.61 million | 961 µs | 5.50 |
| 364 to 400 | 2.40 | 246 | 203,196 | 15.4 | 2.87 million | 1,192 µs | 5.74 |
| 401 to 440 | 2.13 | 301 | 246,879 | 18.8 | 3.50 million | 987 µs | 5.72 |
| 441 to 480 | 1.99 | 321 | 269,617 | 20.1 | 3.88 million | 894 µs | 5.70 |
| 481 to 520 | 1.95 | 328 | 266,677 | 20.5 | 3.74 million | 926 µs | 5.50 |
| 521 to 560 | 1.87 | 343 | 269,025 | 21.4 | 3.76 million | 922 µs | 5.56 |
| 561 to 595 | 1.81 | 308 | 262,621 | 19.3 | 3.75 million | 923 µs | 5.59 |
| 364 to 595 | 12.16 | 305 | 250,905 | 19.1 | 3.55 million | 972 µs | 5.63 |

From the 364th to the 400th network update, from 19:30 to 21:54 on 23 November,
the held-out games of the record of the 363rd network update and of the [record
of the 24 seeds](training_land_weighted_24_seeds_2026_11_23.md) ran beside the
training run on one or two CPU cores. The run then made 203,196 decisions an
hour and each network evaluation's forward pass took 1,192 µs, against 246,879
to 269,617 decisions and 894 to 987 µs in the blocks after; since the 400th
network update it has played 301 to 343 games an hour.

The held-out games of this record ran on two CPU cores from 07:41 to 09:52 on
24 November. From the 595th to the 624th network update, from 07:39 to 09:52,
the run made 189,883 decisions an hour, 210 games and 13.1 network updates,
against 261,933 decisions, 306 games and 19.1 network updates an hour from the
561st to the 595th, and its own processes used a median of 7.0 CPU cores
instead of 7.9 (the run's `watch.log`). So playing the 144 held-out games on
two CPU cores cost the run about 0.6 hours of play (inferred from these rates).

## Predicting each game before training on it

As in the [record of the 363rd network
update](training_land_weighted_update_363_2026_11_23.md#predicting-each-game-before-training-on-it):
the typical miss of the network's values, in points of final score, against the
miss of always predicting the mean final score, and the KL divergence between
the network's action probabilities and the visit shares of the search, all
three alliances together, by hour of play:

| Hours of play | Network updates | Typical miss, points | Miss of the mean, points | Share of the variance explained | KL divergence |
| --- | ---: | ---: | ---: | ---: | ---: |
| 22 to 23 | 15 | 5.2 | 6.8 | 42% | 0.24 |
| 23 to 24 | 17 | 5.2 | 7.1 | 48% | 0.23 |
| 24 to 25 | 17 | 5.1 | 6.9 | 46% | 0.21 |
| 25 to 26 | 13 | 4.3 | 6.1 | 49% | 0.25 |
| 26 to 27 | 18 | 5.0 | 7.5 | 56% | 0.23 |
| 27 to 28 | 22 | 5.3 | 7.3 | 49% | 0.22 |
| 28 to 29 | 20 | 5.4 | 7.9 | 53% | 0.23 |
| 29 to 30 | 21 | 4.8 | 7.3 | 57% | 0.22 |
| 30 to 31 | 21 | 4.9 | 7.1 | 53% | 0.23 |
| 31 to 32 | 19 | 5.3 | 8.5 | 61% | 0.23 |
| 32 to 33 | 22 | 5.5 | 8.4 | 56% | 0.24 |
| 33 to 34 | 21 | 5.4 | 8.5 | 60% | 0.24 |
| 34 to 35 | 19 | 5.3 | 7.5 | 50% | 0.26 |
| 35 to 35.4 | 7 | 6.1 | 9.1 | 55% | 0.25 |

In the twelve hours since the 363rd network update the typical miss stayed
between 4.3 and 5.5 points but for the last part-hour, as it had stayed between
5.1 and 6.4 in the six hours before, while the final scores of the games spread
more, so that the network explained 46% to 61% of their variance instead of 36%
to 56%. The KL divergence stayed between 0.21 and 0.26.

## The memory check

AddressSanitizer wrote no report, and no game has failed since game 5967 at
20:07 on 23 November, on a defect of the rules
([record](japan_dadao_one_zone_2026_11_23.md)). By the 595th network update the
inference server had answered 126.1 million network evaluations for this part.
With the 66.4 million of the memory check of 21 and 22 November and the 29.5
million of the memory-checked part of the training run of 22 November, the
engine built with AddressSanitizer has played through 222.0 million network
evaluations of training play without a report. The training run of 19 to 21
November crashed once in about 128 million network evaluations
([record](training_land_weighted_2026_11_23.md#the-memory-check)). If
AddressSanitizer caught the defect as often as that run crashed, the expected
number of reports by now would be 1.7, and the chance that it would have
reported the defect by now is, in millions of network evaluations:

$$
1 - e^{-(66.4 + 29.5 + 126.1)/128} \approx 0.82
$$

So seeing no report had a chance of 0.18. At the 3.55 million network
evaluations an hour played since the 363rd network update, the chance would
reach 0.87 after 11.0 more hours of play, 0.9 after 20.5, 0.94 after 38.9 and
0.95 after 45.5. Whether the defect comes as often in this layout, one game
process of 16 games on the engine built with AddressSanitizer, as in that run's
six game processes of 42 games on the ordinary engine, is not known.
[Q-018](../../questions.md#answered) asked how to go on looking; the owner
answered it later the same day: stop looking, and train at full speed.

## Play against the scripted balanced policy

The network of the 595th network update played as the earlier networks did:
one alliance at a time against the scripted balanced policy in the other two
seats, searching 64 simulations to depth 16 without exploration noise and
playing the most visited action, each game on one CPU core. It played all 24
held-out seeds, `HELDOUT_SEEDS` in `studies/campaign/evaluation.py`, the primes
from 1009 to 1163. `evaluate_newest_24_seeds.sh` in the run's `evaluations`
folder played them from 07:41 to 09:52 on two lines, the Axis on one and the
Allies and the Comintern on the other. The Axis's controls, the scripted
balanced policy and the untrained network, already had all 24 seeds ([record of
the 24 seeds](training_land_weighted_24_seeds_2026_11_23.md)); the script then
played the Allies' and the Comintern's controls on the 18 seeds after the first
six. All 144 games reached their end. Mean final score of the alliance played,
with its standard error, and that alliance's decisions a game, on all 24 seeds:

| Player | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: |
| The scripted balanced policy | −6.7 (4.7), 1,106 decisions | −2.2 (6.1), 519 decisions | −91.0 (3.0), 240 decisions |
| The network after 595 network updates | +14.3 (1.9), 768 decisions | −74.1 (2.9), 236 decisions | −89.7 (2.2), 215 decisions |
| The network after 363 network updates | +15.7 (2.6), 451 decisions | | |
| The network after 288 network updates | +15.7 (1.7), 1,177 decisions | | |
| The untrained network | +8.8 (2.3), 70 decisions | −67.2 (1.8), 76 decisions | −92.1 (1.3), 122 decisions |

The networks after 288 and 363 network updates played the Allies and the
Comintern on the first six seeds only. Seed by seed, the mean difference, its
standard error and the seeds on which the first player scored higher, on all 24
seeds but where a row says otherwise:

| Comparison | Axis | Allies | Comintern |
| --- | --- | --- | --- |
| The network after 595 network updates against the scripted policy | +21.0 (5.2), 20 of 24 | −72.0 (6.7), 2 of 24 | +1.3 (4.1), 14 of 24 |
| The network after 595 network updates against the untrained network | +5.4 (3.7), 16 of 24 | −6.9 (3.0), 8 of 24 | +2.3 (2.4), 13 of 24 |
| The scripted policy against the untrained network | −15.5 (4.9), 4 of 24 | +65.1 (6.6), 23 of 24 | +1.1 (3.2), 11 of 24 |
| The network after 595 network updates against the one after 363 | −1.4 (2.9), 13 of 24 | −19.6 (14.1), 2 of 6 seeds | +9.8 (6.8), 5 of 6 seeds |
| The network after 595 network updates against the one after 288 | −1.5 (2.6), 13 of 24 | −3.1 (14.6), 3 of 6 seeds | −2.8 (2.9), 2 of 6 seeds |

As the Axis the network after 595 network updates scored as the networks after
288 and 363 did. On the first six seeds alone it would have seemed better than
the one after 363 network updates, by 11.3 ± 4.4 points and higher on all six;
on the other 18 it scored 5.7 ± 3.1 less.

As the Allies it scored 72.0 points below the scripted Allies and 6.9 below the
untrained network, which ends almost every phase at once. In those games the
scripted Japan attacks China from game round 1
([design document](../../design/README.md#is-the-final-wealth-gap-the-right-goal)).
The alliances' wealth at the end of the Allies' games, means over the 24 games
of each player of the Allies:

| Allies played by | Allies' land zones | Allies' income | Allies' units, IPP | Allies' treasury | Allies' wealth | Axis land zones | Axis wealth | Comintern's wealth | Allies' final score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 20.3 | 17.8 | 132 | 18 | 48.9 | 8.9 | 46.6 | 4.4 | −2.2 |
| The network after 595 network updates | 7.5 | 2.8 | 41 | 4 | 13.6 | 15.8 | 69.0 | 18.7 | −74.1 |
| The untrained network | 7.5 | 4.3 | 61 | 64 | 19.1 | 15.4 | 68.8 | 17.5 | −67.2 |

With the network as the Allies, or the untrained network, the scripted Axis
ended with 15.8 and 15.4 land zones, against 8.9 when the scripted policy
played the Allies, which ended with 20.3 land zones. The network's Allies kept
no more land than the untrained network's, and ended with less: 4 IPP of
treasury against 64, and 41 IPP of units against 61. In the 31 self-play games
that finished from 07:42 to 07:57 Japan attacked no zone of China and Dadao
only Hopeh, so the network playing the Allies has rarely met a Japan that
invades China as the scripted one does (inferred).

As the Comintern all three players scored alike, from −89.7 to −92.1: with the
scripted Axis and Allies the Comintern ended its games with 1.3 to 1.9 of the 5
land zones it starts with.

## What Japan does in China, Manchuria and Mongolia

As in the earlier records, the actions counted are those of Japan's turns, in
which Dadao, Japan's minor power, acts too. Means a game over the 24 Axis games
of each player, or counts over them:

| Japan played by | The Axis's decisions | Fleet moves | Land battles begun | Games with a land battle | Zones of China taken from the KMT or the CCP and held at the end | Games ending with such a zone | Zones of China passed from Dadao to Japan and held | Zones of Mongolia held at the end | Starting zones of Manchuria lost | Games in which Japan lost one | Axis land zones at the end |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 1,106 | 288 | 44.5 | 24 | 24 | 9 | 0 | 7 | 80 | 22 | 8.9 |
| The network after 595 network updates | 768 | 143 | 0.8 | 10 | 1 | 1 | 5 | 0 | 9 | 4 | 11.2 |
| The network after 363 network updates | 451 | 64 | 3.9 | 12 | 5 | 3 | 6 | 1 | 16 | 11 | 11.1 |
| The network after 288 network updates | 1,177 | 282 | 5.6 | 16 | 14 | 9 | 4 | 0 | 16 | 8 | 11.4 |
| The untrained network | 70 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 31 | 13 | 9.6 |

The network after 595 network updates began 19 land battles in Japan's turns,
in 10 of the 24 games: 8 of them Japan's and 11 Dadao's. Japan attacked Kerulen,
a zone of Mongolia, five times, in game rounds 8 to 11, and held it at no
game's end. On seed 1013 it attacked Beiping, held by the KMT, Kerulen and
Hainan, held by the CCP, in game round 10, and took Beiping and held it: the
one zone of China it took in the 24 games. On seed 1063 it attacked Rehe, one
of its starting zones of Manchuria, which the KMT had taken, in game round 9.
Dadao attacked Beiping six times, Hopeh four times and Shensi once, all held by
the KMT. Beiping on seed 1019 and Suiyuan on four seeds passed to Japan from
Dadao and were Japan's at the end.

Japan lost 9 of its starting zones of Manchuria, in 4 games, against 16 for the
networks after 288 and 363 network updates. Those 4 games were the Axis's four
worst: −15.2 on seed 1063, where the Axis ended with 7 land zones, −2.0 on seed
1087, −0.3 on seed 1163 and +6.6 on seed 1103.

The alliances' wealth at the end of the Axis games, means over the 24 Axis
games of each player:

| Japan played by | Axis land zones | Axis income | Axis units, IPP | Axis wealth | Allies' land zones | Allies' wealth | Comintern's land zones | Comintern's wealth | Axis final score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 8.9 | 13.5 | 336 | 46.6 | 20.3 | 48.9 | 1.8 | 4.4 | −6.7 |
| The network after 595 network updates | 11.2 | 15.0 | 362 | 57.3 | 12.8 | 30.0 | 6.4 | 13.0 | +14.3 |
| The network after 363 network updates | 11.1 | 15.2 | 406 | 57.9 | 13.0 | 29.4 | 6.2 | 12.8 | +15.7 |
| The network after 288 network updates | 11.4 | 16.2 | 364 | 58.1 | 11.9 | 27.1 | 7.1 | 15.3 | +15.7 |
| The untrained network | 9.6 | 13.5 | 321 | 55.5 | 12.8 | 29.6 | 7.8 | 17.0 | +8.8 |

## What this shows and does not show

It shows that the run went on for 232 more network updates and 3,711 more games
with no memory-checker report, and with no failed game since game 5967 at
20:07 on 23 November. If AddressSanitizer caught the defect as often as the
training run of 19 to 21 November crashed, it would have reported it by now
with a chance of 0.82.

It shows that in self-play nothing moved in those 232 network updates: each
alliance's final score stayed within 1.6 points, and its land at the games'
end within about half a zone, of where they were at the 363rd network update,
while the games got shorter. The network predicts the games' final scores a
little better than before, explaining about half of their variance. In 3 of the 31 self-play
games that finished from 07:42 to 07:57 Japan attacked Mongolia and held one to
four of its zones in the last game round the copies reached; in none did it
hold a zone of China.

It shows that against the scripted balanced policy, on all 24 held-out seeds,
the network after 595 network updates plays the Axis as well as the networks
after 288 and 363 network updates, 21.0 ± 5.2 points above the scripted Axis and
5.4 ± 3.7 above the untrained network, and that its Japan took and kept less of
China as training went on: 14 zones in 9 games after 288 network updates, 5 in
3 after 363 and 1 in 1 after 595, while it lost fewer of its starting zones of
Manchuria, 9 against 16 for both earlier networks. As the Allies the network
scores 72.0 ± 6.7 points below the scripted Allies and 6.9 ± 3.0 below the
untrained network; as the Comintern it scores like both.

It does not show why the Axis's score against the scripted policy has not
risen since the 288th network update, nor whether the network plays better against itself, which self-play
trains for and no evaluation here measures. It does not show differences
smaller than about 7 points between two networks on the 24 seeds, nor, for the
Allies and the Comintern, any comparison with the networks after 288 and 363
network updates beyond their first six seeds.
