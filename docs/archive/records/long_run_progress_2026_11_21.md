# What the training run of 19 to 21 November learned in 38 network updates — 21 November 2026

The long training run of 19 to 21 November 2026 played 252 concurrent
eleven-round games against one 256×8 network for the three alliances, on the
Mac's GPU, with self-play that never stops, 64 simulations to depth 16 per
decision. It ran as four runs, each starting from the previous run's newest
network with a new replay buffer and new Adam averages:

| Run | Folder, commit | From | To | Network updates | Games trained on |
| --- | --- | --- | --- | ---: | ---: |
| First night | `tmp/training-2026-11-19`, `999c90c` | 19 Nov 19:58 | 20 Nov 06:53 | 13 | 3,276 |
| Morning | `tmp/training-2026-11-20`, `7adac20` | 20 Nov 06:54 | 16:12 | 9 | 2,268 |
| Afternoon | `tmp/training-2026-11-20b`, `1463ff4` | 16:22 | 22:42 | 6 | 1,512 |
| Choice B of Q-013 | `tmp/training-2026-11-20c`, `1463ff4` | 22:43 | 21 Nov 07:40 | 10 | 2,520 |

The first three kept 5% of each game's decisions as training samples in a
replay buffer of 8,000; the last kept 1% in a buffer of 25,000 (Q-013, choice B).
In all, 38 network updates trained on 9,576 games. The
[evidence file](long_run_progress_2026_11_21.json) holds every number below,
made from each run's `manifest.json` and from the evaluations' reports.

## Value predictions on new games

How much of the variance of the final scores the network's value predictions
explain, on the games that ended before each network update, scored by the
networks that played them (`summarize_games` in
`tools/compare_training_runs.py`), pooled over three or four network updates
and split by the alliance deciding:

| Run, network updates | All decisions | Axis | Allies | Comintern | Typical miss, in points | Miss when guessing the average |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| First night, 2 to 4 | 3% | 2% | 6% | 2% | 13.1 | 13.3 |
| First night, 5 to 7 | 19% | 15% | 26% | 23% | 14.3 | 15.9 |
| First night, 8 to 10 | 14% | 11% | 17% | 16% | 13.2 | 14.2 |
| First night, 11 to 13 | 30% | 27% | 34% | 34% | 11.6 | 13.9 |
| Morning, 1 to 3 | 29% | 24% | 33% | 35% | 13.3 | 15.7 |
| Morning, 4 to 6 | 21% | 18% | 24% | 27% | 12.9 | 14.5 |
| Morning, 7 to 9 | 17% | 14% | 20% | 21% | 15.1 | 16.5 |
| Afternoon, 1 to 3 | 25% | 20% | 32% | 30% | 13.1 | 15.1 |
| Afternoon, 4 to 6 | 26% | 21% | 33% | 30% | 11.9 | 13.8 |
| Choice B, 1 to 3 | 30% | 26% | 35% | 32% | 12.1 | 14.4 |
| Choice B, 4 to 6 | 29% | 27% | 32% | 33% | 11.6 | 13.8 |
| Choice B, 7 to 10 | 36% | 34% | 39% | 39% | 11.6 | 14.5 |

The policy's KL divergence from the search's visit shares stayed between 0.239
and 0.253 in every block.

## The fit to the replay buffer

With 5% and 8,000, the games played after a network update were missed a median
of 3.3 times as much, by value loss, as the games in its replay buffer (22
pairs), and a network update's 525 training steps lowered the value loss on
their minibatches 2.6 times (median)
([record](replay_buffer_fit_2026_11_20.md)). With 1% and 25,000, once the replay
buffer was full, from network update 6 on, the ratio was a median of 1.3 (4
pairs), and the minibatches' value loss changed by a factor of 0.9 to 1.1 within
a network update.

## Play against the scripted opponents

Each network played one alliance against the scripted balanced policy in the
other two seats, on six held-out seeds (1009, 1013, 1019, 1021, 1031 and 1033),
searching 64 simulations to depth 16 without exploration noise
(`studies/campaign/run.py evaluate`). The control is the scripted balanced
policy itself in the same seat, against the same opponents and seeds
(`--target-script balanced`). Mean final score of the alliance played, with its
standard error over the six seeds:

| Network | Network updates | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: | ---: |
| Untrained (first night, generation 0) | 0 | +51.0 (5.8) | −75.2 (5.2) | −93.8 (1.0) |
| First night, generation 6 | 6 | +9.3 (5.7) | | |
| First night, generation 13 | 13 | +16.8 (7.3) | −73.5 (8.0) | −89.9 (7.7) |
| Morning, generation 5 | 18 | +15.5 (6.4) | | |
| Morning, generation 9 | 22 | +6.7 (6.1) | −59.2 (4.7) | −99.9 (1.1) |
| Afternoon, generation 5 | 27 | +23.9 (8.1) | | |
| Choice B, generation 0 | 28 | +15.9 (7.2) | | |
| Choice B, generation 7 | 35 | +5.7 (3.1) | | |
| Choice B, generation 10 | 38 | +14.4 (6.6) | −68.5 (9.1) | −92.9 (6.1) |
| The scripted balanced policy | | +21.2 (4.3) | −31.9 (7.1) | −92.4 (6.0) |

Seed by seed, the network after 38 network updates scored 6.8 points below the
scripted policy as the Axis (standard error 7.3, higher on 2 of 6 seeds), 36.6
below it as the Allies (8.2, higher on none) and 0.5 below it as the Comintern
(10.5, higher on 2). As the Axis it scored 36.5 points below the untrained
network (5.7, higher on none), which plays almost passively. As the Allies the
network after 22 network updates scored 16.0 points above the untrained network
(standard error 6.4), and the network after 38 scored 6.7 above it (11.8, higher
on 4 seeds) and 9.3 below the one after 22 (11.1).

## What this shows and does not show

It shows that the value predictions learned on the first night, then stayed
between 17% and 30% of the variance for about a day, from 05:00 on 20 November
through choice B's first six network updates, and reached 36% in the first
block after choice B's replay buffer filled: one block of four network updates,
which may yet fall back. It shows that after 38 network updates the network
plays no alliance better than the scripted balanced policy: as the Allies it
plays clearly worse, though it gained some 10 to 16 points on the untrained
network by the 22nd network update; as the Axis somewhat worse, and far below
the passive untrained network; and as the Comintern no differently, since the
Comintern's final score comes out between −90 and −100 whoever plays it.

It does not show whether the networks play better against each other, which
self-play trains for and no evaluation here measures, nor small differences
between networks: six seeds give standard errors of 3 to 10 points. The
evaluations of generations before 28 used the code of the run that trained
them, since a model export loads only with its own sources.
