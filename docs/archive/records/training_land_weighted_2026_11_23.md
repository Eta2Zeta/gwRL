# What the training run under the land-weighted score learned overnight — 23 November 2026

The training run under the land-weighted score
(`studies/campaign/runs/training-land-weighted-2026-11-22`, commit `1101c2e`)
started at 20:16 on 22 November 2026 from a fresh network of 256×8, one network
for the three alliances. Its final score is the one the owner set that evening:
an alliance's wealth counts every land zone it holds as 1 and its income on top,
and its units, infrastructure, treasury and paid construction at a twentieth of
their worth in IPP ([section 2.4 of the design document](../../design/README.md#24-the-final-score)).
It plays as the training run of 22 November did, under choice D of Q-016: a
decision kept as a training sample is searched with 256 simulations, any other
with 16, and moves are drawn from the visit shares in game round 1 only. Its
first part, `1-memory-checked`, plays 16 games at a time in one game process on
an engine built with AddressSanitizer ([the memory check of the training run of
22 November](memory_check_2026_11_22.md)), and each network update follows 16
games. By its 197th network update, at 05:57 on 23 November, after 9.69 hours of
play, it had played 3,152 complete games and 2,690,295 decisions. The owner
asked that morning how the run had gone. This record gives the self-play games'
final scores and land, the one game that failed, what the memory check found,
how well the network predicted each game before training on it, and games
against the scripted balanced policy, with what Japan did in them. The
[evidence file](training_land_weighted_2026_11_23.json) holds every number
below, read from the part's `manifest.json`, from
`tools/compare_training_runs.py` and from the reports and scripts in the run's
`evaluations` folder.

## Self-play

A final score is an alliance's wealth minus the other two alliances' wealth
combined. At the start of every game the wealth is 51.5 for the Axis, 14.2 for
the Allies and 8.2 for the Comintern, which would give final scores of +29.1,
−45.5 and −57.5. In self-play one network plays all three alliances. Means over
the games after each block of 20 network updates, with the standard error of
each mean in brackets:

| Network updates | Games | Decisions, median | Land battles begun a game | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | 320 | 699 | 7.5 | +18.6 (0.6) | −44.9 (0.5) | −76.2 (0.5) |
| 21 to 40 | 320 | 878 | 15.5 | +18.4 (0.6) | −44.6 (0.5) | −73.6 (0.5) |
| 41 to 60 | 320 | 797 | 19.0 | +18.7 (0.7) | −43.3 (0.7) | −73.4 (0.6) |
| 61 to 80 | 320 | 669 | 16.6 | +21.4 (0.5) | −44.2 (0.7) | −75.1 (0.6) |
| 81 to 100 | 320 | 652 | 17.5 | +22.6 (0.5) | −44.9 (0.7) | −74.5 (0.6) |
| 101 to 120 | 320 | 640 | 16.8 | +23.9 (0.4) | −44.5 (0.5) | −75.3 (0.5) |
| 121 to 140 | 320 | 708 | 19.6 | +22.6 (0.4) | −44.9 (0.6) | −73.3 (0.5) |
| 141 to 160 | 320 | 741 | 19.5 | +22.9 (0.5) | −43.7 (0.7) | −73.7 (0.5) |
| 161 to 180 | 320 | 923 | 22.4 | +22.4 (0.6) | −43.0 (0.8) | −75.0 (0.6) |
| 181 to 197 | 272 | 814 | 22.4 | +22.9 (0.5) | −44.1 (0.8) | −73.8 (0.7) |

The land zones each alliance held at the end of a game, means over the same
games. The warlords' 10 zones count for no alliance until a warlord joins one:

| Network updates | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: |
| At the start | 11 | 5 | 5 |
| 1 to 20 | 11.8 | 9.4 | 6.4 |
| 41 to 60 | 11.6 | 9.1 | 6.5 |
| 81 to 100 | 11.7 | 8.6 | 6.1 |
| 121 to 140 | 11.7 | 8.5 | 6.1 |
| 161 to 180 | 11.8 | 9.3 | 5.5 |
| 181 to 197 | 11.6 | 8.9 | 5.8 |

The alliances' wealth at the end of a game, in the first and the last block,
with units, infrastructure, treasury and paid construction at their price in
IPP, of which wealth counts a twentieth:

| Network updates | Alliance | Wealth | Land zones | Income | Units | Infrastructure | Treasury | Paid construction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | Axis | 60.5 | 11.8 | 15.4 | 382 | 161 | 72 | 51 |
| 181 to 197 | Axis | 58.9 | 11.6 | 15.2 | 372 | 161 | 65 | 45 |
| 1 to 20 | Allies | 28.8 | 9.4 | 9.3 | 136 | 39 | 23 | 4 |
| 181 to 197 | Allies | 25.4 | 8.9 | 9.5 | 90 | 39 | 10 | 0 |
| 1 to 20 | Comintern | 13.1 | 6.4 | 3.2 | 59 | 7 | 6 | 0 |
| 181 to 197 | Comintern | 10.6 | 5.8 | 2.4 | 40 | 6 | 3 | 0 |

The 16 games in play at 06:07 on 23 November, played by the networks of the
network updates up to the 199th, were rebuilt from their move logs, each to the
last game round it had reached, from 2 to 11 (`self_play_japan.py` and
`self_play_battles.py` in the run's `evaluations` folder). In them the KMT began
95 land battles, the CCP 46, Japan 15 and Mongolia 2. Most of the units that
the KMT and the CCP moved to attack went into Szechwan and Shensi, where the two
fought each other, into the warlords' Suiyuan, Hopeh and Beiping, and, the
KMT's, into Japan's Rehe. A warlord's zone passed 33 times to the KMT, 12 times
to the CCP and 8 times to Dadao, Japan's puppet government, and a zone passed 7
times from the KMT to the CCP and 7 times back. Japan began land battles in two
of the 16 games, 13 in one of them from game round 1 to game round 8, into
Beiping, western Manchuria and Mongolia, and 2 in the other, and held no zone of
China at the last game round any game had reached.

## The game that failed

One game failed, game 1316, at 00:19 on 23 November after 185 seconds of play.
In a line of play that its search imagined in game round 10, Japan's light
armour had blitzed from Central Mongolia into Ulyassutai, and its battle there
had been fought and won, so that Ulyassutai was Japan's.
The engine then offered the fighter paired with that armour a blitz into
Ulyassutai (`air_blitz`), and applying it failed with the error "Cannot attack
one's own possession". The game process kept the position and the move in the
part's `failed-positions/` folder, and `tools/replay_failed_move.py`, with the
run's code, played the move again in a fresh process and got the same failure:
a defect of the rules, not damaged memory. RB 10.5.1 (p64) forbids blitzing into
a land zone that a friendly nation possesses; the engine refused a land
companion's blitz there but offered the aircraft's. Commit `f7b7c2d` makes the
air module refuse it as well, and on that commit the kept position no longer
offers the move. The training run plays on with its own copy of the code, in
which the defect remains; it cost one game in 3,153.

## The memory check

AddressSanitizer wrote no report. By the 197th network update the inference
server had answered 38.3 million network evaluations for this part, about 3.95
million an hour. Before it, the memory check of 21 and 22 November had answered
66.4 million and the memory-checked part of the training run of 22 November
29.5 million, both without a report
([record](memory_check_2026_11_22.md#what-this-shows-and-does-not-show)). The training
run of 19 to 21 November crashed once in about 128 million network evaluations.
If AddressSanitizer caught the defect as often per network evaluation as that
run crashed, the three memory checks would have reported it by now with the
probability below, all counts in millions of network evaluations:

$$
1 - e^{-(66.4 + 29.5 + 38.3)/128} \approx 0.65
$$

At this part's pace the probability would reach 0.75 after 10.9 more hours of
play, 0.87 after 32.1, 0.9 after 40.6 and 0.94 after 57.2.

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
| 0 to 1 | 21 | 13.0 | 10.5 | −52% | 0.37 |
| 1 to 2 | 20 | 9.1 | 10.3 | 22% | 0.36 |
| 2 to 3 | 18 | 11.2 | 12.8 | 23% | 0.33 |
| 3 to 4 | 22 | 9.7 | 12.1 | 36% | 0.30 |
| 4 to 5 | 23 | 10.2 | 11.9 | 26% | 0.26 |
| 5 to 6 | 25 | 8.4 | 10.3 | 35% | 0.25 |
| 6 to 7 | 21 | 7.7 | 9.7 | 37% | 0.27 |
| 7 to 8 | 16 | 10.6 | 13.5 | 38% | 0.31 |
| 8 to 9 | 17 | 10.2 | 13.8 | 45% | 0.29 |
| 9 to 9.7 | 14 | 9.4 | 12.9 | 47% | 0.27 |

After the first hour the KL divergence was 0.37 for the Axis's decisions, 0.32
for the Allies' and 0.14 for the Comintern's.

## Play against the scripted balanced policy

Each player took one alliance at a time against the scripted balanced policy in
the other two seats, on the six held-out seeds of the evaluations of 21 and 22
November (1009, 1013, 1019, 1021, 1031 and 1033), a network searching 64
simulations to depth 16 without exploration noise and playing the most visited
action, each player on one CPU core, from 06:00 to 07:11 on 23 November. The
Axis's games were played by `watch_japan.py`, which also logs Japan's actions,
and the other alliances' by `studies.campaign.run evaluate` (`evaluate.sh` and
`axis_again.sh` in the run's `evaluations` folder). All 54 games reached their
end. The scripted policy played exactly the games it played on 22 November
([record](training_progress_2026_11_22.md#play-against-the-scripted-balanced-policy)),
with the same decisions, battles and losses, which the new weights score
differently. Mean final score of the alliance played, with its standard error
over the six seeds, and that alliance's decisions a game:

| Player | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: |
| The scripted balanced policy | −2.7 (9.4), 1,129 decisions | −9.6 (10.7), 506 decisions | −88.4 (6.8), 257 decisions |
| The network after 197 network updates | +14.8 (3.5), 872 decisions | −44.1 (14.9), 355 decisions | −89.0 (5.8), 229 decisions |
| The untrained network | +7.4 (5.0), 71 decisions | −65.6 (4.4), 73 decisions | −88.7 (0.8), 121 decisions |

Under the earlier weights, on 22 November, the scripted policy's same games had
scored +22.7, −31.5 and −96.4. Seed by seed, the mean difference, its standard
error and the seeds on which the first player scored higher:

| Comparison | Axis | Allies | Comintern |
| --- | --- | --- | --- |
| After 197 network updates, against the scripted policy | +17.5 (9.6), 5 of 6 | −34.4 (19.2), 1 of 6 | −0.7 (4.9), 2 of 6 |
| After 197 network updates, against the untrained network | +7.4 (5.8), 3 of 6 | +21.5 (11.5), 5 of 6 | −0.3 (6.4), 3 of 6 |
| The untrained network, against the scripted policy | +10.1 (10.0), 5 of 6 | −56.0 (11.1), 0 of 6 | −0.4 (7.0), 4 of 6 |

## What Japan does in China

Japan starts with Formosa and the four zones of Manchuria. China's 13 land zones
in the game are Beiping, Hopeh, Hunan, Kweichow, Nanking, Shantung, Shensi,
Sikang, Sinkiang, Suiyuan, Szechwan, Tsinghai and Yunnan, held at the start by
the KMT, the CCP and the warlords. In the six Axis games of each player above,
means a game over the six games, or counts of games:

| Japan played by | Japan's decisions | Land battles Japan began | Japan's land-unit moves | Japan's purchases | Japanese units lost | KMT, CCP and warlord units lost | Games ending with Japan holding a zone of China | Games in which Japan lost a zone of Manchuria |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 1,129 | 48.5 | 77.5 | 66.0 | 47.3 | 57.3 | 4 of 6 | 5 of 6 |
| The network after 197 network updates | 872 | 4.0 | 75.0 | 33.0 | 6.7 | 59.0 | 3 of 6 | 4 of 6 |
| The untrained network | 71 | 0 | 0 | 0 | 3.7 | 65.0 | 0 of 6 | 3 of 6 |

The network's Japan began all its 24 land battles in game rounds 8 to 11: 1 in
game round 8, 6 in game round 9, 12 in game round 10 and 5 in game round 11. The
scripted Japan began 8 in game round 1 of every game and between 1 and 7 in each
later game round. The network took zones of China only in game rounds 9 to 11,
and kept them to the end in three games: on seed 1009 it took Hopeh from the
KMT in game round 9, and in game round 11 lost it and took Beiping and Hunan; on
seed 1013 Suiyuan from Dadao in game round 10; on seed 1031, after the KMT had
taken Rehe and western Manchuria from it in game rounds 7 and 8, Nanking from
the CCP and Beiping from the KMT in game round 10. On seed 1021 it began no land
battle; from game round 6 on it made 7 to 20 land-unit moves a game round, none
of them an attack, and many ship moves, and lost no zone. Before its first land
battle the network's Japan bought and placed units, researched, asked for
railroads and moved ships, as the network of the training run of 22 November did
under the earlier weights; that network,
after 141 network updates, began 0.8 land battles a game and ended one game of
six holding zones of China
([record](training_progress_2026_11_22.md#what-japan-does-in-china)).

The alliances' wealth at the games' end shows where the scores part. Means over
the six Axis games:

| Japan played by | Axis land zones | Axis income | Axis units, IPP | Axis wealth | Allies' land zones | Allies' income | Allies' units, IPP | Allies' wealth | Comintern's wealth | Axis final score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 9.7 | 14.7 | 340 | 49.0 | 18.7 | 16.8 | 120 | 45.5 | 6.1 | −2.7 |
| The network after 197 network updates | 11.2 | 16.2 | 360 | 58.5 | 15.0 | 10.8 | 68 | 31.8 | 11.9 | +14.8 |
| The untrained network | 9.5 | 13.3 | 319 | 55.1 | 14.8 | 13.8 | 68 | 35.2 | 12.5 | +7.4 |

Against the scripted policy the network's Axis ended 9.5 points richer, 6.5 of
them in units, infrastructure, treasury and paid construction (the scripted
Japan lost 47.3 units a game in its attacks), and 3.0 in land and income; the Allies
ended 13.7 points poorer, with 3.7 fewer land zones and 6.0 less income, and the
Comintern 5.8 points richer. Against its untrained network the network's Axis
ended 3.4 points richer, 4.5 of them in land and income, and the Allies 3.4
points poorer. The untrained network's Japan bought nothing, and its Axis
ended with 173 IPP in its treasury.

## What this shows and does not show

It shows that the self-play games changed less in 197 network updates under
these weights than in 141 under the earlier ones: the Axis's mean final score
rose by 4.3 points, from +18.6 to +22.9, almost all of it in the first 120
network updates, and the Allies' and the Comintern's moved by less than 3. Land
battles tripled, from 7.5 to 22.4 a game, but the Axis ended games holding 11.6
to 11.8 land zones in every block, about the 11 it starts with. In the 16
self-play games rebuilt at 06:07, the KMT and the CCP began nearly all land
battles, most of them for the warlords' zones, and Japan fought in two.

It shows that the network learned to predict the games' final scores: worse
than always predicting the mean in the first hour, then 22% to 47% of their
variance explained, rising to 45% and 47% in the last two hours, with a typical
miss of 8 to 11 points. Its action probabilities came closer to the search's
visit shares in the first five hours, from a KL divergence of 0.37 to 0.25, and
no closer after.

It shows that against the scripted balanced policy, on six held-out seeds, the
network after 197 network updates plays the Axis better than the scripted
policy, by 17.5 ± 9.6 points, higher on 5 of 6 seeds, and the Allies better than
its untrained network, by 21.5 ± 11.5, higher on 5 of 6, though far below the
scripted Allies. Its Axis scored 7.4 ± 5.8 above its untrained network's, which
six seeds do not establish. As the Comintern all three players score the same.

It shows that the network's Japan now acts where its untrained network does
nothing, and that it fights for land only at the end: all its land battles came
in game rounds 8 to 11, and the zones of China it ended with were all taken in
game rounds 9 to 11. A zone taken then is held after the last game round, when
the final score counts it, while an invasion earlier in the game would first
give the warlords to China (RCL-003) and leave the KMT and the CCP time to take
land back; that this is the reason is inferred, not measured. Its Axis ended
with more land than the scripted Axis and
the untrained Axis, 11.2 zones against 9.7 and 9.5: at the end of the six games
the scripted Japan had lost 17 of its starting zones of Manchuria, the untrained
Japan 8 and the network's Japan 6, and the network's Japan held 5 zones of
China. It lost a seventh of the units that the scripted Japan lost.

It does not show small gains: six seeds give standard errors of 3.5 to 19
points. It does not show whether the self-play changes are better play, since
one network plays every alliance, nor whether the network plays better against
itself, which self-play trains for and no evaluation here measures. Under these
weights, as under the earlier ones, the scripted Japan, which attacks from the
first game round, scores below the untrained network's Japan, which never moves,
by 10.1 ± 10.0 points, on 5 of 6 seeds
([open design question](../../design/README.md#is-the-final-wealth-gap-the-right-goal)).
