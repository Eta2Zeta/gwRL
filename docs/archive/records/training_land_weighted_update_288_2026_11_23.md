# The training run under the land-weighted score at its 288th network update — 23 November 2026

The training run under the land-weighted score
(`studies/campaign/runs/training-land-weighted-2026-11-22`, commit `1101c2e`)
reached its 288th network update at 13:38 on 23 November 2026, after 17.37
hours of play, 4,608 complete self-play games and 4,345,022 decisions, all in
its first part, `1-memory-checked`. The owner asked then how it was going. The
[record of that morning](training_land_weighted_2026_11_23.md) describes the
run, its final score and its 197th network update; this record measures the
288th the same way: the self-play games' final scores and land, which nations
began the land battles of the self-play games that finished from 13:42 to
13:57, the run's speed, how well the network predicted each game before
training on it, the memory check, and games against the scripted balanced
policy, with what Japan did in them. The [evidence
file](training_land_weighted_update_288_2026_11_23.json) holds every number
below, read from the part's `manifest.json`, from
`tools/compare_training_runs.py` and from the reports and scripts in the run's
`evaluations` folder (`make_record_288.py` writes it).

## Self-play

An alliance's final score is its wealth minus the other two alliances' wealth
combined; at the start of every game the wealth would give +29.1 to the Axis,
−45.5 to the Allies and −57.5 to the Comintern. One network plays all three
alliances. Means over the games after each block of 20 network updates, with
the standard error of each mean in brackets, beside the first block for
comparison:

| Network updates | Games | Decisions, median | The Axis's decisions | Land battles begun a game | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | 320 | 699 | 258 | 7.5 | +18.6 (0.6) | −44.9 (0.5) | −76.2 (0.5) |
| 181 to 200 | 320 | 853 | 440 | 22.9 | +22.8 (0.5) | −44.0 (0.7) | −73.6 (0.6) |
| 201 to 220 | 320 | 1,051 | 629 | 23.2 | +21.2 (0.5) | −43.0 (0.8) | −72.9 (0.6) |
| 221 to 240 | 320 | 1,073 | 630 | 23.1 | +21.9 (0.6) | −42.8 (0.8) | −73.3 (0.5) |
| 241 to 260 | 320 | 1,041 | 626 | 19.1 | +22.6 (0.4) | −46.0 (0.5) | −69.8 (0.4) |
| 261 to 280 | 320 | 1,151 | 702 | 18.6 | +23.8 (0.4) | −47.5 (0.5) | −69.0 (0.4) |
| 281 to 288 | 128 | 1,004 | 562 | 17.8 | +23.4 (0.5) | −46.5 (0.8) | −69.7 (0.6) |

The land zones each alliance held at the end of a game, means over the same
games:

| Network updates | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: |
| At the start | 11 | 5 | 5 |
| 1 to 20 | 11.8 | 9.4 | 6.4 |
| 181 to 200 | 11.5 | 8.9 | 5.8 |
| 201 to 220 | 11.2 | 9.0 | 5.9 |
| 221 to 240 | 11.3 | 8.9 | 5.8 |
| 241 to 260 | 11.3 | 8.1 | 6.1 |
| 261 to 280 | 11.6 | 7.7 | 6.2 |
| 281 to 288 | 11.3 | 7.8 | 6.1 |

The Axis's added decisions are mostly fleet moves and flights: the table below
counts all nations' actions, and only the Axis's decisions grew (inferred). A
fleet move takes at least two decisions, the first ship (`naval_start_move`)
and the route (`naval_route`), and one more for each ship added
([naval](../../engine/naval.md)); a flight in Noncombat Movement takes two,
`air_fly` and `air_land_noncombat` ([air](../../engine/air.md#7-the-kinds-of-action)).
Actions a game, all nations together:

| Network updates | Fleet moves | Land-unit moves | Flights in Noncombat Movement | Landings in Noncombat Movement | Purchases |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | 23.0 | 172.3 | 3.5 | 3.9 | 68.8 |
| 181 to 200 | 75.4 | 138.6 | 10.3 | 13.8 | 75.0 |
| 201 to 220 | 143.0 | 122.4 | 11.1 | 16.8 | 80.0 |
| 221 to 240 | 135.8 | 142.4 | 17.8 | 26.4 | 79.8 |
| 241 to 260 | 121.7 | 135.7 | 30.5 | 35.2 | 83.7 |
| 261 to 280 | 139.4 | 135.6 | 34.1 | 46.8 | 84.7 |
| 281 to 288 | 99.9 | 119.6 | 25.8 | 37.1 | 81.9 |

The alliances' wealth at the end of a game, in the block after the morning's
evaluation and the last full block, with units, infrastructure, treasury and
paid construction at their price in IPP, of which wealth counts a twentieth:

| Network updates | Alliance | Wealth | Land zones | Income | Units | Infrastructure | Treasury | Paid construction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 181 to 200 | Axis | 58.8 | 11.5 | 15.2 | 370 | 162 | 66 | 45 |
| 261 to 280 | Axis | 58.3 | 11.6 | 15.0 | 376 | 163 | 37 | 58 |
| 181 to 200 | Allies | 25.4 | 8.9 | 9.5 | 89 | 39 | 10 | 0 |
| 261 to 280 | Allies | 22.6 | 7.7 | 8.6 | 81 | 36 | 9 | 0 |
| 181 to 200 | Comintern | 10.6 | 5.8 | 2.5 | 40 | 6 | 3 | 0 |
| 261 to 280 | Comintern | 11.9 | 6.2 | 2.8 | 50 | 5 | 3 | 0 |

## Who fought in the self-play games that finished from 13:42 to 13:57

A self-play game's move log stays in the part's `game-moves/` folder only while
the game is played. From 13:42 to 13:57 `collect_finished_games.sh` copied
every log there each 10 seconds and kept those of the 36 games that finished
meanwhile, whose training samples went into network updates 289 to 291; each
copy ends at most 10 seconds before its game did. `self_play_finished.py`
replayed them without searching. The copies hold 522 of the 555 land battles
that the part's manifest counts for these games; the missing ones fell in the
last game round, of which the copies hold only a part. Means a game:

| Nation | Land battles begun | Units lost |
| --- | ---: | ---: |
| KMT | 12.2 | 13.8 |
| CCP | 2.3 | 5.6 |
| Japan | 0 | 5.2 |
| Dadao | 0 | 0.3 |
| Mongolia | 0 | 0 |
| The warlords | 0 | 0.1 |

The KMT began 1.1 to 1.4 land battles in each game round from 2 to 10, the CCP
about half of its 2.3 in game rounds 1 and 2. A land zone passed from a warlord to the
KMT 1.83 times a game, from a warlord to the CCP 1.58 times, from a warlord to
Dadao, Japan's puppet government and a minor power of the Axis
([politics](../../engine/politics.md)), 0.81 times, from the CCP to the KMT 0.39
times, from the KMT to the CCP 0.22 times and from Japan to the KMT 0.11 times.
Japan took no zone of China in any of the 36 games. In the 16 games in play at
06:07 that morning, rebuilt to the last game round each had reached, Japan had
begun land battles in two
([record](training_land_weighted_2026_11_23.md#self-play)).

## Speed

Before and after the 197th network update, at which the morning's record
stopped:

| Network updates | Hours of play | Games an hour | Decisions an hour | Network updates an hour | Network evaluations an hour | Forward-pass time per network evaluation | Network evaluations an inference batch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 197 | 9.69 | 325 | 277,624 | 20.3 | 3.95 million | 877 µs | 5.85 |
| 198 to 288 | 7.68 | 190 | 215,540 | 11.9 | 3.23 million | 1,064 µs | 5.60 |

The games got longer: the median game had 640 to 923 decisions in the blocks
of 20 network updates up to the 200th and 1,004 to 1,151 since. And the
inference server, which spent 96% of the time in forward passes in both
periods, spent 21% more time on each network evaluation. Why each evaluation
took longer is not measured.

## Predicting each game before training on it

As in the [morning's record](training_land_weighted_2026_11_23.md#predicting-each-game-before-training-on-it):
the typical miss of the network's values, in points of final score, against
the miss of always predicting the mean final score, and the KL divergence
between the network's action probabilities and the visit shares of the search,
all three alliances together, by hour of play:

| Hours of play | Network updates | Typical miss, points | Miss of the mean, points | Share of the variance explained | KL divergence |
| --- | ---: | ---: | ---: | ---: | ---: |
| 9 to 10 | 17 | 9.2 | 12.7 | 47% | 0.28 |
| 10 to 11 | 10 | 9.4 | 13.1 | 48% | 0.25 |
| 11 to 12 | 11 | 7.9 | 11.0 | 48% | 0.23 |
| 12 to 13 | 11 | 9.4 | 12.2 | 40% | 0.27 |
| 13 to 14 | 14 | 8.1 | 11.5 | 50% | 0.27 |
| 14 to 15 | 13 | 6.4 | 8.6 | 44% | 0.28 |
| 15 to 16 | 11 | 6.1 | 8.1 | 44% | 0.28 |
| 16 to 17 | 13 | 6.0 | 7.6 | 36% | 0.26 |
| 17 to 17.4 | 5 | 5.3 | 6.7 | 38% | 0.23 |

The final scores of the self-play games came closer together after 14 hours of
play, and the typical miss shrank with them; the share explained did not rise.

## The memory check

AddressSanitizer wrote no report, and no game failed after game 1316, the one
the morning's record describes. By the 288th network update the inference
server had answered 63.1 million network evaluations for this part. With the
66.4 million of the memory check of 21 and 22 November and the 29.5 million of
the memory-checked part of the training run of 22 November, and the training
run of 19 to 21 November's one crash in about 128 million network evaluations
([record](training_land_weighted_2026_11_23.md#the-memory-check)), the chance
that AddressSanitizer would have reported the defect by now, if it caught it as
often as that run crashed, is, in millions of network evaluations:

$$
1 - e^{-(66.4 + 29.5 + 63.1)/128} \approx 0.71
$$

At the 3.23 million network evaluations an hour played since the 197th network
update, the chance would reach 0.75 after 5.7 more hours of play, 0.87 after
31.6, 0.9 after 42.0 and 0.94 after 62.3.

## Play against the scripted balanced policy

The network of the 288th network update played as the morning's networks did:
one alliance at a time against the scripted balanced policy in the other two
seats, on the six held-out seeds 1009, 1013, 1019, 1021, 1031 and 1033,
searching 64 simulations to depth 16 without exploration noise and playing the
most visited action, on one CPU core, from 13:40 to 14:34 on 23 November
(`evaluate_newest.sh` in the run's `evaluations` folder). All 18 games reached
their end. The other three rows are the morning's games: the scripted policy
replays exactly the same games, and the untrained network does not change.
Mean final score of the alliance played, with its standard error over the six
seeds, and that alliance's decisions a game:

| Player | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: |
| The scripted balanced policy | −2.7 (9.4), 1,129 decisions | −9.6 (10.7), 506 decisions | −88.4 (6.8), 257 decisions |
| The network after 288 network updates | +19.0 (3.9), 1,170 decisions | −66.3 (8.8), 218 decisions | −82.3 (5.3), 216 decisions |
| The network after 197 network updates | +14.8 (3.5), 872 decisions | −44.1 (14.9), 355 decisions | −89.0 (5.8), 229 decisions |
| The untrained network | +7.4 (5.0), 71 decisions | −65.6 (4.4), 73 decisions | −88.7 (0.8), 121 decisions |

Seed by seed, the mean difference, its standard error and the seeds on which
the network after 288 network updates scored higher:

| Comparison | Axis | Allies | Comintern |
| --- | --- | --- | --- |
| Against the scripted policy | +21.7 (12.2), 5 of 6 | −56.7 (13.5), 0 of 6 | +6.1 (10.4), 4 of 6 |
| Against the network after 197 network updates | +4.2 (3.7), 3 of 6 | −22.3 (20.0), 4 of 6 | +6.8 (10.4), 4 of 6 |
| Against the untrained network | +11.6 (5.1), 5 of 6 | −0.7 (10.6), 3 of 6 | +6.5 (5.0), 4 of 6 |

As the Allies, the network after 197 network updates had scored +1.6 and −3.9
on seeds 1009 and 1031, with 511 and 580 decisions; the network after 288
scored −76.8 and −94.5 there, with 239 and 188.

## What Japan does in China

Japan starts with Formosa and the four zones of Manchuria; China's 13 land
zones are held at the start by the KMT, the CCP and the warlords
([morning's record](training_land_weighted_2026_11_23.md#what-japan-does-in-china)).
In the six Axis games of each player, means a game over the six games, or
counts of games:

| Japan played by | Japan's decisions | Land battles Japan began | Japan's land-unit moves | Japan's fleet moves | Japan's purchases | Japanese units lost | KMT, CCP and warlord units lost | Games in which Japan lost a zone of Manchuria | Starting zones of Manchuria lost, all six games |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 1,129 | 48.5 | 77.5 | 288 | 66.0 | 47.3 | 57.3 | 5 of 6 | 17 |
| The network after 288 network updates | 1,170 | 3.2 | 93.0 | 280 | 32.3 | 8.0 | 63.5 | 1 of 6 | 2 |
| The network after 197 network updates | 872 | 4.0 | 75.0 | 198 | 33.0 | 6.7 | 59.0 | 4 of 6 | 6 |
| The untrained network | 71 | 0 | 0 | 0 | 0 | 3.7 | 65.0 | 3 of 6 | 8 |

The network after 288 network updates began 19 land battles in the six games:
5 in game round 7, 3 in game round 8, 1 in game round 9 and 10 in game round
11, against the earlier network's 24 in game rounds 8 to 11. The three games in
which it ended holding zones of China:

- **Seed 1013.** It took Nanking from the KMT in game round 7 and held it to the
  end; it took Shantung from the KMT in game round 8 and lost it the same game
  round, and in game round 11 took it again from the CCP and Beiping from the
  KMT. It ended with three zones of China, 14 Axis land zones and an Axis final
  score of +36.0, its best of the six games.
- **Seed 1021.** It took Beiping from the KMT in game round 11, and Hainan,
  which is not one of China's 13 land zones, from the CCP.
- **Seed 1033.** Suiyuan and Tsinghai passed to Japan from Dadao in game round
  10, with no land battle of Japan's in the game, and the KMT took Tsinghai in
  game round 11. A zone that passes from Dadao to Japan stays the Axis's.

So at the end of the six games Japan held four zones of China taken from the KMT
or the CCP, in two games, as the network after 197 network updates did, on
seeds 1009 and 1031. That network's four had all been taken in game rounds 10
and 11; Nanking on seed 1013 was taken in game round 7. On seeds 1019, 1031 and
1033 Japan began no land battle, and on seed 1009 one, in game round 8; there it
lost Rehe and western Manchuria, the only starting zones of Manchuria it lost in
the six games.

The alliances' wealth at the games' end, means over the six Axis games:

| Japan played by | Axis land zones | Axis income | Axis units, IPP | Axis wealth | Allies' land zones | Allies' wealth | Comintern's land zones | Comintern's wealth | Axis final score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 9.7 | 14.7 | 340 | 49.0 | 18.7 | 45.5 | 2.7 | 6.1 | −2.7 |
| The network after 288 network updates | 11.8 | 17.0 | 364 | 59.7 | 9.8 | 22.8 | 8.5 | 18.0 | +19.0 |
| The network after 197 network updates | 11.2 | 16.2 | 360 | 58.5 | 15.0 | 31.8 | 4.7 | 11.9 | +14.8 |
| The untrained network | 9.5 | 13.3 | 319 | 55.1 | 14.8 | 35.2 | 6.0 | 12.5 | +7.4 |

Against the earlier network's games, the Axis ended 1.2 points richer, the
scripted Allies 9.0 points poorer, with 5.2 fewer land zones, and the scripted
Comintern 6.1 points richer, with 3.8 more. Why Japan's different play changed
the KMT's and the CCP's land is not measured.

## What this shows and does not show

It shows that the run goes on without a fault: 91 more network updates and
1,456 more games with no memory-checker report and no failed game. It plays 190
games an hour against 325 before the 197th network update, because the games
are longer, by fleet moves and flights more than by battles, and each network
evaluation takes 21% longer for a reason not measured.

It shows that the self-play games changed little in the Axis's final score, from
+21.2 to +23.8 in every block since the 200th network update. From the 241st
on, the Allies' fell from between −42.8 and −44.0 to between −46.0 and −47.5,
the Comintern's rose from between −72.9 and −73.6 to between −69.0 and −69.8,
land battles fell from about 23 a game to 17.8 to 19.1, and the Allies ended
with 7.7 to 8.1 land zones instead of about 9. In the 36 self-play games that
finished from 13:42 to 13:57 Japan began no land battle: the KMT began five in
six, and Dadao took warlord land for the Axis. Whether the Axis's added fleet
moves and flights help its score is not measured.

It shows that against the scripted balanced policy the network's Axis scores a
mean of +19.0, 21.7 ± 12.2 points above the scripted Axis on 5 of 6 seeds and
11.6 ± 5.1 above the untrained network, also on 5 of 6, and 4.2 ± 3.7 above the
network after 197 network updates, which six seeds do not establish. Its Allies
lost what they had gained by the 197th network update: they score 22.3 ± 20.0
points below that network's Allies, at −66.3 against the untrained network's
−65.6. Its Comintern scores 6.8 ± 10.4 above that network's, which six seeds do
not establish.

It shows that the network's Japan keeps more of its own land than at the
197th network update, losing 2 starting zones of Manchuria in six games against
6, and that it takes about as much of China, four zones taken from the KMT or
the CCP and held at the end, in two games, as before; one of them, Nanking on
seed 1013, was taken in game round 7 and held for five game rounds. So the
question the open design question on the final score asks, whether the
network's Japan goes on to take and keep more land
([design document](../../design/README.md#is-the-final-wealth-gap-the-right-goal)),
has no clear answer yet: one earlier conquest in six games, and in self-play
none.

It does not show small gains: six seeds give standard errors of 3.7 to 20
points. It does not show whether the network plays better against itself,
which self-play trains for and no evaluation here measures.
