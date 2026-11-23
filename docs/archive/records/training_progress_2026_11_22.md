# What the training run of 22 November 2026 learned in its first 141 network updates — 22 November 2026

The training run started on 22 November 2026
(`studies/campaign/runs/training-2026-11-22`, commit `3153079`) began from a
fresh network of 256×8, one network for the three alliances, and plays as the
owner chose in Q-016 (choice D): a decision kept as a training sample is searched
with 256 simulations, any other with 16, and moves are drawn from the visit
shares in game round 1 only. Its first part, `1-memory-checked`, plays 16 games
at a time in a game process checked by AddressSanitizer
([record](memory_check_2026_11_22.md)), and each network update follows 16
games. By its 141st network update, at 17:56 on 22 November, after 5.94 hours of
play, it had played 2,256 complete games and 1,597,750 decisions. The owner
asked that day whether the network updates showed in the score. This record
gives the self-play games' final scores, how well the network predicted each
game before training on it, and games against the scripted balanced policy. The
[evidence file](training_progress_2026_11_22.json) holds every number below,
read from the part's `manifest.json`, from `tools/compare_training_runs.py`
and from the evaluation reports in the run's `evaluations` folder.

## Self-play

A final score is an alliance's wealth minus the other two alliances' wealth
combined ([section 2.4 of the design document](../../design/README.md#24-the-final-score)).
In self-play one network plays all three alliances. Means over the games after
each block of 20 network updates, with the standard error of each mean in
brackets:

| Network updates | Games | Decisions, median | Land battles begun a game | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | 320 | 602 | 7.9 | +39.6 (0.6) | −60.1 (0.6) | −103.6 (0.5) |
| 21 to 40 | 320 | 617 | 10.1 | +42.5 (0.7) | −60.9 (0.7) | −102.0 (0.5) |
| 41 to 60 | 320 | 704 | 10.9 | +45.8 (0.6) | −63.1 (0.6) | −100.5 (0.4) |
| 61 to 80 | 320 | 709 | 12.3 | +46.6 (0.6) | −63.3 (0.7) | −99.4 (0.4) |
| 81 to 100 | 320 | 711 | 15.7 | +48.2 (0.5) | −64.8 (0.6) | −98.3 (0.4) |
| 101 to 120 | 320 | 710 | 18.3 | +48.0 (0.5) | −64.6 (0.6) | −96.8 (0.4) |
| 121 to 141 | 336 | 705 | 17.9 | +49.9 (0.4) | −66.3 (0.5) | −97.0 (0.3) |

The alliances' wealth at the end of a game, in the first and the last block. An
alliance's wealth is its income plus a tenth of what its units, its
infrastructure, its treasury and its paid construction are worth:

| Network updates | Alliance | Wealth | Income | Units | Infrastructure | Treasury | Paid construction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | Axis | 81.8 | 15.3 | 425.5 | 171.9 | 39.0 | 28.8 |
| 121 to 141 | Axis | 81.7 | 14.9 | 421.5 | 176.8 | 34.8 | 34.2 |
| 1 to 20 | Allies | 32.0 | 10.3 | 105.6 | 41.9 | 65.2 | 4.0 |
| 121 to 141 | Allies | 23.6 | 8.5 | 99.4 | 35.5 | 14.8 | 0.6 |
| 1 to 20 | Comintern | 10.3 | 3.0 | 59.2 | 6.3 | 6.8 | 0.0 |
| 121 to 141 | Comintern | 8.2 | 2.8 | 44.1 | 6.6 | 3.2 | 0.0 |

## Predicting each game before training on it

Each game that ends is first scored by the network then serving self-play, on
the game's training samples ([section 10 of the design document](../../design/README.md#10-measuring-strength)).
The typical miss of its values is a hundred times the square root of the value
loss, in points of final score; always predicting the mean final score would
miss by a hundred times the square root of the scores' variance. The KL
divergence says how far the network's action probabilities are from the visit
shares of the search, zero only when they are the same. All three alliances
together, by hour of play:

| Hours of play | Network updates | Typical miss, points | Miss of the mean, points | Share of the variance explained | KL divergence |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 to 1 | 25 | 14.5 | 10.8 | −79% | 0.23 |
| 1 to 2 | 23 | 7.4 | 12.2 | 63% | 0.25 |
| 2 to 3 | 23 | 6.7 | 9.9 | 54% | 0.27 |
| 3 to 4 | 22 | 7.0 | 10.8 | 58% | 0.25 |
| 4 to 5 | 26 | 6.2 | 8.9 | 52% | 0.24 |
| 5 to 6 | 22 | 5.9 | 8.2 | 49% | 0.26 |

After the first hour the KL divergence was 0.23 for the Axis's decisions, 0.37
for the Allies' and 0.10 for the Comintern's.

## Play against the scripted balanced policy

Each player took one alliance at a time against the scripted balanced policy in
the other two seats, on the six held-out seeds of the evaluations of the
training run of 19 to 21 November (1009, 1013, 1019, 1021, 1031 and 1033;
[record](long_run_progress_2026_11_21.md#play-against-the-scripted-opponents)),
a network searching 64 simulations to depth 16 without exploration noise and
playing the most visited action, on one CPU core, from 17:58 to 18:55 on 22
November. All 54 games reached their end. Mean final score of the alliance
played, with its standard error over the six seeds, and that alliance's
decisions a game:

| Player | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: |
| The scripted balanced policy | +22.7 (8.0), 1,129 decisions | −31.5 (8.2), 506 decisions | −96.4 (5.6), 257 decisions |
| The network after 141 network updates | +52.4 (5.2), 240 decisions | −81.7 (6.7), 216 decisions | −92.1 (3.7), 228 decisions |
| The untrained network | +48.2 (3.9), 72 decisions | −75.2 (3.8), 74 decisions | −93.2 (1.2), 120 decisions |

Seed by seed, the mean difference, its standard error and the seeds on which the
first player scored higher:

| Comparison | Axis | Allies | Comintern |
| --- | --- | --- | --- |
| After 141 network updates, against the scripted policy | +29.8 (10.1), 5 of 6 | −50.1 (13.2), 0 of 6 | +4.3 (6.5), 4 of 6 |
| After 141 network updates, against the untrained network | +4.3 (6.7), 5 of 6 | −6.4 (8.2), 3 of 6 | +1.1 (4.2), 4 of 6 |
| The untrained network, against the scripted policy | +25.5 (11.6), 5 of 6 | −43.7 (9.7), 0 of 6 | +3.2 (5.8), 5 of 6 |

The scripted policy's own scores are close to those it had on the same seeds
under the rules and code of 21 November: +21.2, −31.9 and −92.4.

## What Japan does in China

The owner asked the same day whether the Axis destroys China or does nothing.
The six Axis games of each player above were played again exactly, every final
score the same, with Japan's actions and its possessions logged
(`watch_japan.py` in the run's `evaluations` folder). Japan starts with Formosa
and the four zones of Manchuria; China's 13 land zones in the game are Beiping,
Hopeh, Hunan, Kweichow, Nanking, Shantung, Shensi, Sikang, Sinkiang, Suiyuan,
Szechwan, Tsinghai and Yunnan, held at the start by the KMT, the CCP and the
warlords. Means a game over the six games, or counts of games:

| Japan played by | Japan's decisions | Land battles Japan began | Japan's land-unit moves | Japan's purchases | Japanese units lost | KMT, CCP and warlord units lost | Games ending with Japan holding a zone of China | Games in which Japan lost a zone of Manchuria |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 1,129 | 48.5 | 77.5 | 66.0 | 47.3 | 57.3 | 4 of 6 | 5 of 6 |
| The network after 141 network updates | 240 | 0.8 | 21.3 | 31.3 | 3.2 | 60.0 | 1 of 6 | 3 of 6 |
| The untrained network | 72 | 0 | 0 | 0 | 2.3 | 62.3 | 0 of 6 | 3 of 6 |

The network after 141 network updates began no land battle in three of its six
games. Its game on seed 1021 is typical: in each of 11 game rounds Japan
bought and placed units, researched and asked for railroads, and in some it
moved ships into port; it made no combat move, held no zone of China and lost
one unit. In the one game that ended with Japan holding zones of China, seed
1031, which gave its best score, +74.3, Japan stood still for nine game rounds;
in game round 10 it moved 6 units into China and took Beiping and Suiyuan from
Dadao, Japan's puppet government, which then held them.
China attacked Japan instead: in seed 1009 the CCP took Rehe and western and
northern Manchuria from Japan in game rounds 3 to 5, and Japan won Rehe back in
game round 9, its one land battle of that game; the KMT took western Manchuria
in game round 11 of seed 1013 and in game round 10 of seed 1033. The KMT, the
CCP and the warlords lost about as many units whoever played Japan.

The alliances' wealth at the games' end shows where the scores part. Means over
the six games; units and infrastructure at their price in IPP, of which wealth
counts a tenth:

| Japan played by | Japan's income | Japan's units | Japan's infrastructure | Japan's wealth | The Allies' income | The Allies' units | The Allies' wealth | The Comintern's wealth | Axis final score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 14.7 | 340 | 135 | 64.0 | 16.8 | 120 | 36.9 | 4.5 | +22.7 |
| The network after 141 network updates | 15.0 | 418 | 183 | 80.8 | 9.3 | 52 | 19.1 | 9.3 | +52.4 |
| The untrained network | 13.8 | 322 | 149 | 79.3 | 6.2 | 43 | 14.4 | 16.8 | +48.2 |

Against the network's Japan, the scripted Japan ended with as much income from
land, 14.7 against 15.0, because what it took in China it lost in Manchuria,
and with 12.5 points less of units and infrastructure. The Allies ended 17.8
points richer, with 7.5 more income and 67 IPP more units: about the warlords'
8 IPP of land and 83 IPP of units, which join a side when Japan invades China
(RCL-003), most of them the Allies' in these games (inferred from the sizes).
The untrained network's Japan bought nothing and ended with 171.5 IPP in its
treasury.

In self-play, the 16 games in play at 19:10 on 22 November, played by the
networks of about network update 166, were rebuilt from their move logs
(`self_play_japan.py`). Japan held no zone of China and had no unit in China at
the last game round each had reached. Of the 13 that had reached game round 4,
8 had no land battle begun by Japan, and only 2 had one after game round 1, the
only game round whose moves are drawn from the search's visit shares. Japan's
combat moves went into Mongolia eight times, into Suiyuan three times, and into
Beiping and western Manchuria once each.

## What this shows and does not show

It shows that the self-play games changed steadily over 141 network updates,
far beyond the standard errors: the Axis's mean final score rose by 10.3
points, the Comintern's by 6.6, and the Allies' fell by 6.2, while land battles
more than doubled. The Axis's own wealth did not change; its score rose because
the Allies' wealth fell by 8.4, most of it because the Allies ended games with
50 fewer points of treasury, spent instead of kept, and 1.8 less income. It
shows that the network learned to predict the games' final scores: worse than
always predicting the mean in the first hour, then about half of their variance
explained, with a typical miss of about 6 points by the sixth hour. Its action
probabilities came no closer to the search's visit shares after the second hour.

It shows that against the scripted balanced policy, on six held-out seeds, the
network after 141 network updates plays no alliance measurably better than the
untrained network it started from. As the Axis both score well above the
scripted policy, which fights far more; as the Allies both score far below it,
on every seed; as the Comintern all three score about the same.

It shows that the network's Japan does not fight China: in the held-out games
it began fewer than one land battle a game and in self-play almost none after
game round 1; it took no zone of China from the KMT, the CCP or a warlord, while
in three of six held-out games the CCP or the KMT took zones of Manchuria from
it; and it lost a fifteenth of the units that the scripted Japan lost, which
fought about 48 land battles a game. Its score comes from keeping its own
wealth, which the final wealth gap rewards, and from leaving the warlords out of
the war: the attacking scripted Japan kept no more income from land and left
the Allies 17.8 points richer.

It does not show small gains: six seeds give standard errors of 4 to 13 points.
It does not show whether the self-play changes are better play, since one
network plays every alliance, nor whether the network plays better against
itself, which self-play trains for and no evaluation here measures. That the
untrained network's nearly passive Axis scores so well is the question whether
the final wealth gap is the right goal
([open design question](../../design/README.md#is-the-final-wealth-gap-the-right-goal)).
