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

It does not show small gains: six seeds give standard errors of 4 to 13 points.
It does not show whether the self-play changes are better play, since one
network plays every alliance, nor whether the network plays better against
itself, which self-play trains for and no evaluation here measures. That the
untrained network's nearly passive Axis scores so well is the question whether
the final wealth gap is the right goal
([open design question](../../design/README.md#is-the-final-wealth-gap-the-right-goal)).
