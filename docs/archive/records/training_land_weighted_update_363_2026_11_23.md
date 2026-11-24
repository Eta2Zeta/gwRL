# The training run under the land-weighted score at its 363rd network update — 23 November 2026

The training run under the land-weighted score
(`studies/campaign/runs/training-land-weighted-2026-11-22`, commit `1101c2e`)
reached its 363rd network update at 19:30 on 23 November 2026, after 23.23
hours of play, 5,809 complete self-play games and 5,674,175 decisions, all in
its first part, `1-memory-checked`. The owner asked then, as at the 288th
network update six hours earlier, how it was going. This record measures the
363rd network update as the [record of the
288th](training_land_weighted_update_288_2026_11_23.md) measured that one, with
the same scripts: the self-play games' final scores and land, which nations
began the land battles of the self-play games that finished from 19:31 to
19:46, the run's speed, how well the network predicted each game before
training on it, the memory check, and games against the scripted balanced
policy, with what Japan did in them. The [record of that
morning](training_land_weighted_2026_11_23.md) describes the run and its final
score. The [evidence file](training_land_weighted_update_363_2026_11_23.json)
holds every number below, read from the part's `manifest.json`, from
`tools/compare_training_runs.py` and from the reports and scripts in the run's
`evaluations` folder (`make_record_363.py` writes it).

Later the same evening the Axis games of the other 18 held-out seeds put the
networks of the 288th and 363rd network updates level, +15.7 each on all 24
seeds: the fall of 10.2 points on the six seeds below was the luck of those six
([record of the 24 seeds](training_land_weighted_24_seeds_2026_11_23.md)).

## Self-play

An alliance's final score is its wealth minus the other two alliances' wealth
combined; at the start of every game the wealth would give +29.1 to the Axis,
−45.5 to the Allies and −57.5 to the Comintern. One network plays all three
alliances. Means over the games of each block of 20 network updates since the
280th, the last block running to the 363rd, beside the first block and the
blocks around the two earlier evaluations, with the standard error of each mean
in brackets:

| Network updates | Games | Decisions, median | The Axis's decisions | Land battles begun a game | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | 320 | 699 | 258 | 7.5 | +18.6 (0.6) | −44.9 (0.5) | −76.2 (0.5) |
| 181 to 200 | 320 | 853 | 440 | 22.9 | +22.8 (0.5) | −44.0 (0.7) | −73.6 (0.6) |
| 261 to 280 | 320 | 1,151 | 702 | 18.6 | +23.8 (0.4) | −47.5 (0.5) | −69.0 (0.4) |
| 281 to 300 | 320 | 1,139 | 715 | 16.6 | +23.6 (0.3) | −48.2 (0.5) | −68.5 (0.4) |
| 301 to 320 | 320 | 1,206 | 776 | 16.7 | +23.7 (0.4) | −48.4 (0.5) | −68.4 (0.4) |
| 321 to 340 | 320 | 906 | 555 | 18.0 | +24.3 (0.4) | −48.7 (0.5) | −69.0 (0.4) |
| 341 to 363 | 368 | 872 | 531 | 16.7 | +24.6 (0.3) | −50.1 (0.4) | −68.3 (0.4) |

The land zones each alliance held at the end of a game, means over the same
games:

| Network updates | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: |
| At the start | 11 | 5 | 5 |
| 1 to 20 | 11.8 | 9.4 | 6.4 |
| 181 to 200 | 11.5 | 8.9 | 5.8 |
| 261 to 280 | 11.6 | 7.7 | 6.2 |
| 281 to 300 | 11.5 | 7.5 | 6.2 |
| 301 to 320 | 11.5 | 7.4 | 6.3 |
| 321 to 340 | 11.6 | 7.5 | 6.3 |
| 341 to 363 | 11.7 | 7.3 | 6.4 |

From about the 321st network update the games got shorter again, by fleet
moves, land-unit moves and flights. A fleet move takes at least two decisions
and a flight in Noncombat Movement two, as the [record of the 288th network
update](training_land_weighted_update_288_2026_11_23.md#self-play) explains.
Actions a game, all nations together:

| Network updates | Fleet moves | Land-unit moves | Flights in Noncombat Movement | Landings in Noncombat Movement | Purchases |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 to 20 | 23.0 | 172.3 | 3.5 | 3.9 | 68.8 |
| 181 to 200 | 75.4 | 138.6 | 10.3 | 13.8 | 75.0 |
| 261 to 280 | 139.4 | 135.6 | 34.1 | 46.8 | 84.7 |
| 281 to 300 | 140.6 | 137.0 | 35.7 | 43.3 | 83.9 |
| 301 to 320 | 145.4 | 156.6 | 41.8 | 45.3 | 86.3 |
| 321 to 340 | 95.8 | 117.2 | 26.4 | 34.5 | 81.7 |
| 341 to 363 | 92.1 | 108.7 | 22.6 | 27.5 | 83.0 |

The alliances' wealth at the end of a game, in the last full block before the
288th network update and the last block, with units, infrastructure, treasury
and paid construction at their price in IPP, of which wealth counts a
twentieth:

| Network updates | Alliance | Wealth | Land zones | Income | Units | Infrastructure | Treasury | Paid construction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 261 to 280 | Axis | 58.3 | 11.6 | 15.0 | 376 | 163 | 37 | 58 |
| 341 to 363 | Axis | 59.2 | 11.7 | 15.0 | 386 | 166 | 46 | 52 |
| 261 to 280 | Allies | 22.6 | 7.7 | 8.6 | 81 | 36 | 9 | 0 |
| 341 to 363 | Allies | 21.9 | 7.3 | 8.2 | 84 | 33 | 9 | 0 |
| 261 to 280 | Comintern | 11.9 | 6.2 | 2.8 | 50 | 5 | 3 | 0 |
| 341 to 363 | Comintern | 12.8 | 6.4 | 3.1 | 55 | 7 | 3 | 0 |

## Who fought in the self-play games that finished from 19:31 to 19:46

As at the 288th network update, `collect_finished_games.sh` kept the move logs
of the self-play games that finished while it ran, from 19:31 to 19:46: 66
games, whose training samples went into network updates 364 to 368.
`self_play_finished.py` replayed them without searching. It now also names
each land battle's attacker, from the state's list of battles, because a minor
power attacks in its major power's turn: Dadao in Japan's. The copies hold 897
of the 939 land battles that the part's manifest counts for these games; the
missing ones fell in the last game round, of which the copies hold only a part.
Means a game, by the nation that began the battles or lost the units:

| Nation | Land battles begun | Units lost |
| --- | ---: | ---: |
| KMT | 9.36 | 11.02 |
| CCP | 3.24 | 6.05 |
| Japan | 0.83 | 3.56 |
| Dadao | 0.12 | 0.61 |
| Mongolia | 0.03 | 0.05 |
| The warlords | 0 | 0.20 |

A land zone passed from a warlord to the KMT 2.29 times a game, from a warlord
to the CCP 1.12 times, from a warlord to Dadao 0.73 times, from the CCP to the
KMT 0.58 times, from the KMT to the CCP 0.45 times, from Dadao to the KMT 0.14
times, from the KMT to Japan 0.11 times and from Japan to the KMT 0.08 times.

Japan began its 55 land battles in 6 of the 66 games, and Dadao its 8 in 5
games, all of Dadao's against Hopeh, held by the KMT, which Dadao took once. In
three games Japan attacked China in game round 1, whose moves self-play draws
at random from the visit shares, and went on attacking in later game rounds,
where self-play plays the most visited action:

- In one game it began 15 land battles. It took Beiping from the KMT in game
  round 2, took Hopeh in game round 3 and lost it in the same game round, and
  took Suiyuan in game round 10; it held Beiping and Suiyuan in the last game
  round the copy reached.
- In another it began 24. It took Kerulen from Mongolia in game round 3 and lost
  it in game round 4, and took Nanking from the KMT in game round 10 and held
  it.
- In the third it began 8, one in game round 1 and seven in game round 6, and
  took no zone.

In three more games the KMT had taken Rehe, one of Japan's starting zones of
Manchuria, and Japan attacked it once, twice and five times; it took Rehe back
in the last two games. Of Japan's 55 land battles, 47 ended their game round
with the zone still held by the nation that held it when the battle began.

Replayed the same way, the 36 games that finished just after the 288th network
update confirm the count of the record of that network update: the KMT and the
CCP began all of their 522 land battles, Japan and Dadao none.

## Speed

Before and after the 197th network update, at which the morning's record
stopped, and in two parts since the 288th: up to the 320th, while the games
were long, and after it:

| Network updates | Hours of play | Games an hour | Decisions an hour | Network updates an hour | Network evaluations an hour | Forward-pass time per network evaluation | Network evaluations an inference batch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 to 197 | 9.69 | 325 | 277,624 | 20.3 | 3.95 million | 877 µs | 5.85 |
| 198 to 288 | 7.68 | 190 | 215,540 | 11.9 | 3.23 million | 1,064 µs | 5.60 |
| 289 to 320 | 3.09 | 166 | 207,824 | 10.4 | 3.17 million | 1,091 µs | 5.34 |
| 321 to 363 | 2.77 | 249 | 248,005 | 15.5 | 3.61 million | 961 µs | 5.50 |

With the shorter games the run plays 249 games an hour instead of 166. The
forward-pass time per network evaluation rose and fell with the games' length:
877 µs while the median game had at most 923 decisions, 1,064 and 1,091 µs while
it had 1,004 to 1,206, and 961 µs since it fell to 872 and 906. Why is not
measured.

## Predicting each game before training on it

As in the [record of the 288th network
update](training_land_weighted_update_288_2026_11_23.md#predicting-each-game-before-training-on-it),
which gives the earlier hours: the typical miss of the network's values, in
points of final score, against the miss of always predicting the mean final
score, and the KL divergence between the network's action probabilities and
the visit shares of the search, all three alliances together, by hour of play:

| Hours of play | Network updates | Typical miss, points | Miss of the mean, points | Share of the variance explained | KL divergence |
| --- | ---: | ---: | ---: | ---: | ---: |
| 17 to 18 | 10 | 5.4 | 7.0 | 40% | 0.25 |
| 18 to 19 | 11 | 6.1 | 7.6 | 36% | 0.27 |
| 19 to 20 | 11 | 5.1 | 7.8 | 56% | 0.25 |
| 20 to 21 | 12 | 5.6 | 7.3 | 41% | 0.25 |
| 21 to 22 | 16 | 6.4 | 8.4 | 41% | 0.23 |
| 22 to 23 | 15 | 5.2 | 6.8 | 42% | 0.24 |
| 23 to 23.2 | 5 | 5.9 | 7.8 | 43% | 0.22 |

In these six hours the typical miss stayed between 5.1 and 6.4 points, as in the
three hours before, and the network explained 36% to 56% of the variance of the
final scores before it trained on the games.

## The memory check

AddressSanitizer wrote no report, and between game 1316, the one the morning's
record describes, and the 363rd network update no game failed. At 20:07, after
this record's measurements, game 5967 failed on a defect of the rules: Japan and
Dadao had both attacked Rehe, held by the KMT, in one Combat Movement Phase
([record](japan_dadao_one_zone_2026_11_23.md)). By
the 363rd network update the inference
server had answered 82.9 million network evaluations for this part. With the
66.4 million of the memory check of 21 and 22 November and the 29.5 million of
the memory-checked part of the training run of 22 November, and the training
run of 19 to 21 November's one crash in about 128 million network evaluations
([record](training_land_weighted_2026_11_23.md#the-memory-check)), the chance
that AddressSanitizer would have reported the defect by now, if it caught it as
often as that run crashed, is, in millions of network evaluations:

$$
1 - e^{-(66.4 + 29.5 + 82.9)/128} \approx 0.75
$$

At the 3.61 million network evaluations an hour played since the 320th network
update, the chance would reach 0.8 after 7.5 more hours of play, 0.87 after
22.8, 0.9 after 32.1 and 0.94 after 50.2.

## Play against the scripted balanced policy

The network of the 363rd network update played as the earlier networks did:
one alliance at a time against the scripted balanced policy in the other two
seats, on the six held-out seeds 1009, 1013, 1019, 1021, 1031 and 1033,
searching 64 simulations to depth 16 without exploration noise and playing the
most visited action, on one CPU core, from 19:30 to 20:16 on 23 November
(`evaluate_newest.sh` in the run's `evaluations` folder). All 18 games reached
their end. The other rows are the games of the two earlier records: the
scripted policy replays exactly the same games, and the untrained network does
not change. Mean final score of the alliance played, with its standard error
over the six seeds, and that alliance's decisions a game:

| Player | Axis | Allies | Comintern |
| --- | ---: | ---: | ---: |
| The scripted balanced policy | −2.7 (9.4), 1,129 decisions | −9.6 (10.7), 506 decisions | −88.4 (6.8), 257 decisions |
| The network after 363 network updates | +8.8 (5.1), 475 decisions | −49.8 (13.0), 326 decisions | −94.9 (2.4), 190 decisions |
| The network after 288 network updates | +19.0 (3.9), 1,170 decisions | −66.3 (8.8), 218 decisions | −82.3 (5.3), 216 decisions |
| The network after 197 network updates | +14.8 (3.5), 872 decisions | −44.1 (14.9), 355 decisions | −89.0 (5.8), 229 decisions |
| The untrained network | +7.4 (5.0), 71 decisions | −65.6 (4.4), 73 decisions | −88.7 (0.8), 121 decisions |

Seed by seed, the mean difference, its standard error and the seeds on which
the network after 363 network updates scored higher:

| Comparison | Axis | Allies | Comintern |
| --- | --- | --- | --- |
| Against the scripted policy | +11.5 (13.6), 5 of 6 | −40.2 (12.6), 0 of 6 | −6.5 (5.4), 2 of 6 |
| Against the network after 288 network updates | −10.2 (5.6), 2 of 6 | +16.5 (19.6), 4 of 6 | −12.6 (6.0), 1 of 6 |
| Against the network after 197 network updates | −6.0 (6.5), 2 of 6 | −5.7 (13.6), 4 of 6 | −5.8 (5.8), 2 of 6 |
| Against the untrained network | +1.4 (8.4), 2 of 6 | +15.8 (10.9), 4 of 6 | −6.1 (2.3), 1 of 6 |

As the Axis, the network scored 22.5 points less than the network after 288
network updates on seed 1009, 21.2 less on seed 1013 and 23.9 less on seed
1021, and 2.5 less to 4.8 more on the other three.

## What Japan does in China

Japan starts with Formosa and the four zones of Manchuria; China's 13 land
zones are held at the start by the KMT, the CCP and the warlords
([morning's record](training_land_weighted_2026_11_23.md#what-japan-does-in-china)).
`watch_japan.py` logs the actions taken in Japan's turns, in which Dadao,
Japan's minor power, acts too, so the land battles that the earlier records say
Japan began are all those begun in Japan's turns, any of Dadao's among them.
For the network after 363 network updates `watch_japan.py` was run a second time, changed to name each land battle's attacker,
defender and zone, and played the same six games
(`japan-generation-000363-attackers.json`). In the six Axis games of each
player, the actions in Japan's turns and the units lost, means a game over the
six games, or counts of games:

| Japan played by | The Axis's decisions | Land battles begun | Land-unit moves | Fleet moves | Purchases | Japanese units lost | KMT, CCP and warlord units lost | Games in which Japan lost a zone of Manchuria | Starting zones of Manchuria lost, all six games |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 1,129 | 48.5 | 77.5 | 288 | 66.0 | 47.3 | 57.3 | 5 of 6 | 17 |
| The network after 363 network updates | 475 | 4.8 | 48.8 | 69 | 34.0 | 9.2 | 63.2 | 2 of 6 | 5 |
| The network after 288 network updates | 1,170 | 3.2 | 93.0 | 280 | 32.3 | 8.0 | 63.5 | 1 of 6 | 2 |
| The network after 197 network updates | 872 | 4.0 | 75.0 | 198 | 33.0 | 6.7 | 59.0 | 4 of 6 | 6 |
| The untrained network | 71 | 0 | 0 | 0 | 0 | 3.7 | 65.0 | 3 of 6 | 8 |

The network after 363 network updates began 29 land battles in Japan's turns,
25 of them Japan's and 4 Dadao's, in three of the six games:

- **Seed 1009.** The CCP took Rehe in game round 3, and western, northern and
  eastern Manchuria in game rounds 4, 6 and 9. From game round 5 on Japan
  attacked Rehe five times and western Manchuria once; it took Rehe back in
  game round 8 and lost it to the KMT in the same game round. The Axis ended
  with 7 land zones and a final score of −11.5.
- **Seed 1021.** Japan invaded from game round 7: 17 land battles to game round
  11, against the KMT in Beiping, Hopeh, Shantung, Suiyuan, Tsinghai,
  Szechwan, Shensi, Kwangtung and Kobdo, and against Mongolia in Kerulen and
  central Mongolia. It took Kerulen from Mongolia in game round 7 and lost it
  to the KMT in game round 10, took no zone of China, and lost western
  Manchuria in game round 11. The Axis's final score was −1.4.
- **Seed 1031.** The KMT took Rehe in game round 1 and western Manchuria in
  game round 2. Japan attacked both in game round 6 and took back western
  Manchuria, by then the CCP's; Rehe passed back to Japan in game round 7,
  after a land battle of Dadao's. Dadao also attacked Szechwan once and Shensi
  twice, taking neither. Sinkiang
  and Suiyuan, which Dadao had taken from their warlords without a land
  battle, passed from Dadao to Japan in game round 11. With 13 land zones this
  was the Axis's best game, +22.1.

On seeds 1013, 1019 and 1033 the Axis began no land battle and made 284 to 516
decisions a game. So at the end of the six games Japan held no zone of China
taken from the KMT or the CCP, against four zones in two games for the
networks after 197 and 288 network updates.

The alliances' wealth at the games' end, means over the six Axis games:

| Japan played by | Axis land zones | Axis income | Axis units, IPP | Axis wealth | Allies' land zones | Allies' wealth | Comintern's land zones | Comintern's wealth | Axis final score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| The scripted balanced policy | 9.7 | 14.7 | 340 | 49.0 | 18.7 | 45.5 | 2.7 | 6.1 | −2.7 |
| The network after 363 network updates | 10.5 | 14.3 | 403 | 55.4 | 16.2 | 37.1 | 4.3 | 9.6 | +8.8 |
| The network after 288 network updates | 11.8 | 17.0 | 364 | 59.7 | 9.8 | 22.8 | 8.5 | 18.0 | +19.0 |
| The network after 197 network updates | 11.2 | 16.2 | 360 | 58.5 | 15.0 | 31.8 | 4.7 | 11.9 | +14.8 |
| The untrained network | 9.5 | 13.3 | 319 | 55.1 | 14.8 | 35.2 | 6.0 | 12.5 | +7.4 |

Against the games of the network after 288 network updates, the Axis ended 4.3
points poorer, with 1.3 fewer land zones, the scripted Allies 14.3 points
richer, with 6.3 more, and the scripted Comintern 8.4 points poorer, with 4.2
fewer. Why Japan's different play changed the KMT's and the CCP's land is not
measured.

## What this shows and does not show

It shows that the run went on without a fault for 75 more network updates and
1,201 more games, with no memory-checker report and no failed game; at 20:07 a
second game failed, on a defect of the rules
([record](japan_dadao_one_zone_2026_11_23.md)). Since about
the 321st network update its games are about a quarter shorter, by fleet moves,
land-unit moves and flights, and it plays 249 games an hour instead of 166.

It shows that in self-play the Axis's final score rose a little, from +23.6 to
+24.6 over the four blocks since the 280th network update, while the Allies'
fell from −48.2 to −50.1 and the Comintern's stayed between −68.3 and −69.0. In
the 66 self-play games that finished from 19:31 to 19:46 Japan began land
battles in 6, where in the 36 that finished after the 288th network update it
began none: three times it invaded China from game round 1, whose moves
self-play draws from the visit shares, and in two of those games it held zones
of China at the end; three times it fought to take back Rehe.

It shows that against the scripted balanced policy the network's Axis did worse
than at the 288th network update: a mean of +8.8, 10.2 ± 5.6 points lower,
lower on four of six seeds, and only 1.4 ± 8.4 above the untrained network. Its
Japan made 475 decisions a game instead of 1,170, with a quarter of the fleet
moves; it took and kept no zone of China, and lost 5 starting zones of
Manchuria in the six games instead of 2. As the Allies the network scored
16.5 ± 19.6 higher than at the 288th network update, and as the Comintern
12.6 ± 6.0 lower. In all three alliances its mean is 5.7 to 6.0 points below
that of the network after 197 network updates, none of the three established.

So the question that the open design question on the final score asks, whether
the network's Japan goes on to take and keep more land
([design document](../../design/README.md#is-the-final-wealth-gap-the-right-goal)),
has no answer yet: on the same six seeds the network's Axis scored +14.8, +19.0
and +8.8 after 197, 288 and 363 network updates, and its Japan kept four, four
and no zones of China taken from the KMT or the CCP.

It does not show whether these swings between evaluations are real: six seeds
give standard errors of 2.4 to 19.6 points, as large as the swings. It does not
show whether the network plays better against itself, which self-play trains
for and no evaluation here measures.
