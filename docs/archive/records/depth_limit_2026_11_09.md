# How often the depth limit stops a simulation — 9 November 2026

The [design document](../../design/README.md#47-more-detail-on-the-search) explains the
search's depth limit: a simulation stops after 16 steps, moves and dice rolls,
wherever it is. This record measures how often that happened in one real
training game, what the stopped simulations used instead, and what the searches
concerned did without the limit. It also corrects the account of simulation 53
in the [training sample record](training_sample_2026_11_05.md). The
[evidence file](depth_limit_2026_11_09.json) holds the numbers.

## How it was made

**The game.** The sources of commit `d64117d`, the commit of the 5 November
sample run, were extracted and built apart from the working tree. With
generation 1 of that run, `play_episode` replayed the game of the training
sample record exactly as it was played: 64 simulations, depth 16, exploration
noise, temperature 1, run seed 1936, environment seed 1105. It gave the same
1,349 decisions and 183 dice rolls, the same final scores (Axis +49.0, Allies
−63.8, Comintern −106.2) and the same visits at decision 612. Of the 1,349
decisions, 1,075 had more than one legal move and were searched.

**What was recorded.** Every search kept its trace (`record_trace`, which only
records). The search's functions that value a stopped simulation
(`_bootstrap_value`) and ask a network about a new position (`_expand`) were
wrapped to note what the simulation had reached and which alliance's network
rated it. At a chance event each network's value was also computed on its own.
At each decision where a simulation stopped at the limit, a second search of a
copy of the position ran with the same seed and a limit of 256, which no
simulation reached, and was then discarded; the game went on with the first
search's move. A second replay, needed to note the rating network, again gave
the same game.

## How deep the simulations went

The 1,075 searches ran 68,800 simulations. 68,765 stopped at a position no
simulation had evaluated, 17 at the end of the game and 18 at the depth limit.
None returned to a position already on its path. The mean depth was 2.57 steps.

| Depth (steps) | Simulations | Share | Share this deep or less |
| ---: | ---: | ---: | ---: |
| 1 | 28,170 | 40.9% | 40.9% |
| 2 | 18,270 | 26.6% | 67.5% |
| 3 | 7,263 | 10.6% | 78.1% |
| 4 | 4,418 | 6.4% | 84.5% |
| 5 | 3,538 | 5.1% | 89.6% |
| 6–10 | 6,452 | 9.4% | 99.0% |
| 11–15 | 671 | 1.0% | 99.97% |
| 16, the limit | 18 | 0.03% | 100% |

## The 18 stops at the limit

They came from 10 of the 1,075 searches, all at decisions with two to five legal
moves, where the simulations concentrate on few lines. What the 16th step had
reached:

| Position reached | Stops | What the simulation used | Would it have gone on without the limit? |
| --- | ---: | --- | --- |
| A decision no simulation had evaluated | 9 | The deciding alliance's network's value, as at any new position | No: it would have stopped there anyway |
| A chance event | 8 | The average of the three networks' values | Yes: it would have rolled the dice |
| A decision evaluated before | 1 | The value stored for it | Yes: it would have chosen a move |

So 9 of the game's 68,800 simulations were cut short.

**At a chance event the networks disagree.** Each network gives its own value
for the alliance choosing at the search's start:

| Decision | Choosing | Axis network | Allies network | Comintern network | Average used |
| ---: | --- | ---: | ---: | ---: | ---: |
| 12 | Comintern | −105.99 | −96.25 | −101.74 | −101.33 |
| 567 | Axis | +42.68 | +34.06 | +26.97 | +34.57 |
| 568 | Axis | +43.54 | +33.04 | +26.51 | +34.36 |
| 612 | Comintern | −106.11 | −98.06 | −101.19 | −101.79 |
| 612 | Comintern | −106.50 | −97.77 | −101.33 | −101.87 |
| 679 | Axis | +36.68 | +27.42 | +26.60 | +30.23 |
| 840 | Comintern | −105.61 | −102.94 | −99.46 | −102.67 |
| 940 | Comintern | −106.01 | −104.21 | −103.50 | −104.58 |

The three values for one position differ by 2.5 to 17.0 points. The moves'
average results within one search usually differ by less: over the game's 1,075
searches, the best and worst move's averages lay a median 1.45 points apart
(quartiles 0.78 and 2.70), and 0.87 points at decision 612.

## The 10 searches without the limit

| Decision | Choosing | Legal moves | Stops at the limit | Visits, limit 16 | Visits, no limit | Deepest, no limit |
| ---: | --- | ---: | ---: | --- | --- | ---: |
| 12 | Comintern | 2 | 1 | 52, 12 | 51, 13 | 18 |
| 563 | Axis | 3 | 2 | 16, 34, 14 | 16, 34, 14 | 16 |
| 567 | Axis | 2 | 1 | 47, 17 | 50, 14 | 19 |
| 568 | Axis | 3 | 1 | 6, 12, 46 | 6, 12, 46 | 19 |
| 612 | Comintern | 5 | 5 | 36, 2, 5, 9, 12 | 36, 2, 5, 9, 12 | 18 |
| 679 | Axis | 2 | 1 | 30, 34 | 27, 37 | 17 |
| 840 | Comintern | 5 | 1 | 5, 10, 7, 15, 27 | 5, 9, 9, 10, 31 | 18 |
| 847 | Comintern | 3 | 1 | 6, 35, 23 | 6, 35, 23 | 16 |
| 940 | Comintern | 2 | 1 | 22, 42 | 25, 39 | 17 |
| 1063 | Comintern | 2 | 4 | 11, 53 | 11, 53 | 17 |

Without the limit the deepest simulation took 19 steps. The visits were
identical at five decisions; at the other five, 1 to 6 of the 64 visits moved
between moves. The most-visited move was the same at all ten. Each search took
0.10 to 0.22 seconds either way.

## Simulation 53 at decision 612

The [training sample record](training_sample_2026_11_05.md) says simulation 53
stopped at the depth limit at a position rated −106.02, an outlier that widened
the search's scale. The replay shows why it was low. Simulation 53 took 14 moves
and 2 dice rolls and reached a new position where Japan decides, so the Axis
network rated it, the only one of the search's 64 stops that this network rated.
61 stopped at positions where the Comintern decides, rated by the Comintern's own
network between −102.64 and −101.16, and 2 at chance events (simulations 49 and
50). At those two chance events the Axis network gave −106.11 and −106.50, the
Comintern network −101.19 and −101.33. So the outlier reflects the Axis network
rating the Comintern lower than the Comintern network does, not the position or
the limit: the position was new, so the simulation would have stopped there
without the limit too.

## Positions rated by another alliance's network

Every new position is rated by the network of the alliance that decides there,
so a search compares results that different networks gave. Of the game's 68,800
simulations, 62,410 stopped at positions rated by the choosing alliance's
network and 6,364 (9.3%) at positions rated by another alliance's network; 504 of
the 1,075 searches had at least one such stop.

## What this does and does not show

- **Measured:** one game, with networks after a single update. The limit
  stopped 18 simulations of 68,800, cut 9 of them short, and removing it never
  changed the most-visited move.
- **Inferred:** better-trained networks may concentrate simulations on fewer
  moves and build deeper lines, which would meet the limit more often. This has
  not been measured.
- **Open:** whether the networks' disagreement about one position, 2.5 to 17
  points here, distorts searches that mix their values; the design document
  lists it under one network per alliance or one shared network.
