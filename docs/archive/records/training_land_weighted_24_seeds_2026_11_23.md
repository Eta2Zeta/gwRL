# The networks of the 288th and 363rd network updates on all 24 held-out seeds — 23 November 2026

On the six held-out seeds 1009, 1013, 1019, 1021, 1031 and 1033, the Axis
network of the training run under the land-weighted score
(`studies/campaign/runs/training-land-weighted-2026-11-22`, commit `1101c2e`)
had scored +19.0 after 288 network updates and +8.8 after 363: 10.2 points less,
with a standard error of 5.6, and its Japan had kept no zone of China
([record of the 363rd network
update](training_land_weighted_update_363_2026_11_23.md#play-against-the-scripted-balanced-policy)).
At 20:45 on 23 November 2026 the owner asked for the Axis games of the other
18 held-out seeds, the rest of the 24 of `HELDOUT_SEEDS` in
`studies/campaign/evaluation.py`: the primes from 1039 to 1163. This record
gives both networks' Axis games on all 24 seeds, beside the scripted balanced
policy's and the untrained network's on the same seeds. The [evidence
file](training_land_weighted_24_seeds_2026_11_23.json) holds every number
below; `make_record_24_seeds.py` in the run's `evaluations` folder writes it
from the reports there.

## Setup

The games were played as on the first six seeds: `watch_japan.py` plays the
Axis with the network or the scripted policy named, the scripted balanced
policy holds the Allies' and the Comintern's seats, and the network searches 64
simulations to depth 16 without exploration noise and plays the most visited
action. `evaluate_more_seeds.sh` played the 18 seeds on two lines of one-core
processes beside the training run, from 20:52 to 22:41: one line for the network
of the 288th network update, the other for the network of the 363rd, then the
scripted balanced policy and the untrained network. All 72 games reached their
end. For each player the 24 games are the six of the earlier records and these
18; for the network of the 363rd network update, the six are those of its
second play, which names each land battle's attacker.

## The Axis's final scores

Mean final score of the Axis, with its standard error:

| Player of the Axis | All 24 seeds | The first 6 seeds | The other 18 seeds |
| --- | ---: | ---: | ---: |
| The scripted balanced policy | −6.7 (4.7) | −2.7 (9.4) | −8.1 (5.6) |
| The network after 363 network updates | +15.7 (2.6) | +8.8 (5.1) | +18.0 (2.9) |
| The network after 288 network updates | +15.7 (1.7) | +19.0 (3.9) | +14.6 (1.8) |
| The untrained network | +8.8 (2.3) | +7.4 (5.0) | +9.3 (2.7) |

Seed by seed, the mean difference, its standard error and the seeds on which
the first player scored higher:

| Comparison | All 24 seeds | The first 6 seeds | The other 18 seeds |
| --- | --- | --- | --- |
| The network after 363 network updates against the network after 288 | 0.0 (3.3), 12 of 24 | −10.2 (5.6), 2 of 6 | +3.3 (3.7), 10 of 18 |
| The network after 363 network updates against the untrained network | +6.9 (3.5), 14 of 24 | +1.4 (8.4), 2 of 6 | +8.7 (3.9), 12 of 18 |
| The network after 288 network updates against the untrained network | +6.9 (2.9), 17 of 24 | +11.6 (5.1), 5 of 6 | +5.3 (3.5), 12 of 18 |
| The network after 363 network updates against the scripted policy | +22.4 (5.8), 21 of 24 | +11.5 (13.6), 5 of 6 | +26.0 (6.3), 16 of 18 |
| The network after 288 network updates against the scripted policy | +22.4 (5.7), 20 of 24 | +21.7 (12.2), 5 of 6 | +22.7 (6.7), 15 of 18 |
| The scripted policy against the untrained network | −15.5 (4.9), 4 of 24 | −10.1 (10.0), 1 of 6 | −17.3 (5.6), 3 of 18 |

On all 24 seeds the two networks scored the same. The 10.2 points between them
on the first six seeds were the luck of those six: on the other 18 the newer
network scored 3.3 points more, which 18 seeds do not establish either.

## What Japan does in China and Manchuria

As in the earlier records, the actions counted are those of Japan's turns, in
which Dadao, Japan's minor power, acts too. Means a game over the 24 Axis games
of each player, or counts over them:

| Japan played by | The Axis's decisions | Fleet moves | Land battles begun | Games with a land battle | Zones of China taken from the KMT or the CCP and held at the end | Games ending with such a zone | Zones of China passed from Dadao to Japan and held | Starting zones of Manchuria lost | Games in which Japan lost one | Axis land zones at the end |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 1,106 | 288 | 44.5 | 24 | 24 | 9 | 0 | 80 | 22 | 8.9 |
| The network after 363 network updates | 451 | 64 | 3.9 | 12 | 5 | 3 | 6 | 16 | 11 | 11.1 |
| The network after 288 network updates | 1,177 | 282 | 5.6 | 16 | 14 | 9 | 4 | 16 | 8 | 11.4 |
| The untrained network | 70 | 0 | 0 | 0 | 0 | 0 | 0 | 31 | 13 | 9.6 |

The newer network's land battles in Japan's turns were Japan's 85 times and
Dadao's 8. In the older network's 18 new games they were Japan's 113 times and
Dadao's 3; its first six games' reports do not say who attacked. Most of both
networks' land battles came late: the newer network began 69 of its 93 in game
rounds 8 to 11, the older 111 of its 135.

The zones of China that the older network's Japan held at the end had been
taken in game round 5 once, 7, 8 and 9 once each, 10 three times and 11 seven
times; the newer network's in game rounds 7, 8 and 10, 10 and 10. The best
game of each shows what a conquest is worth under the land-weighted score: on
seed 1061 the newer network took Hunan and Nanking from the KMT in game round
10, ended with 15 Axis land zones and scored +48.5; on seed 1163 the older one
took Beiping from the KMT in game round 5 and held it to the end, with 14 Axis
land zones and +31.25.

The alliances' wealth at the games' end, means over the 24 Axis games:

| Japan played by | Axis land zones | Axis income | Axis units, IPP | Axis wealth | Allies' land zones | Allies' wealth | Comintern's land zones | Comintern's wealth | Axis final score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 8.9 | 13.5 | 336 | 46.6 | 20.3 | 48.9 | 1.8 | 4.4 | −6.7 |
| The network after 363 network updates | 11.1 | 15.2 | 406 | 57.9 | 13.0 | 29.4 | 6.2 | 12.8 | +15.7 |
| The network after 288 network updates | 11.4 | 16.2 | 364 | 58.1 | 11.9 | 27.1 | 7.1 | 15.3 | +15.7 |
| The untrained network | 9.6 | 13.5 | 321 | 55.5 | 12.8 | 29.6 | 7.8 | 17.0 | +8.8 |

The newer network's Axis ended with 43 more IPP of units, 1.0 less income and
0.3 fewer land zones than the older one's; the scripted Allies ended 2.3 points
richer and the scripted Comintern 2.5 poorer. The parts balance to the same
final score.

## What this shows and does not show

It shows that the networks of the 288th and 363rd network updates play the Axis
equally well against the scripted balanced policy: +15.7 each on 24 seeds, 6.9
points above the untrained network, about two standard errors, and 22.4 above
the scripted Axis. The fall that the first six seeds showed was not real.

It shows that the newer network's Japan does less with the same result: 451
decisions a game against 1,177, a quarter of the fleet moves, fewer land
battles, and 5 zones of China taken and held at the end, in 3 of 24 games,
against 14 in 9. So between the two network updates the network's Japan did not
go on to take and keep more land; it kept less, although 24 games do not
establish a difference of 14 zones against 5 by themselves.

It does not show how the network after 197 network updates, played on the
first six seeds only, compares on the 24. It does not show differences smaller
than about 7 points: 24 seeds give the mean of a network a standard error of
1.7 to 2.6 points and the difference of two networks one of 3.3. Six seeds,
with standard errors of 3.5 to 5.1 for a mean and 5.6 for a difference, can
show a difference of about 11 points or more.
