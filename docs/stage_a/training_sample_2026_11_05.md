# One real training sample — 5 November 2026

The [design document](../design/README.md#72-what-a-sample-stores) explains what
a training sample stores by showing one real sample. This record says how that
sample was made and gives its exact values; the
[evidence file](training_sample_2026_11_05.json) holds them in full, with every
answer the network read. It also records why the example does not come from a
run's first batch: a fresh network gives every position the same values. Two
later sections record what the update after the batch did with its samples, and
how often recorded runs drew each kept sample.

## How it was made

**The networks.** At commit `d64117d`, one training batch with the Mac settings,
starting from fresh 64×2 networks (run seed 1936): 32 eleven-round games, all
finished, with 33,062 decisions. It kept 1,611 samples (4.9%) and then took 700
training steps. The batch played for 851 seconds, while another session's test
suite ran beside it.

```sh
env -u MallocNanoZone ./.venv/bin/python -m studies.campaign.run train \
  --run-dir studies/campaign/runs/sample-example-2026-11-05 --seed 1936 \
  --calendar-rounds 11 --complete-episodes --batches 1 --simulations 64 --max-depth 16 \
  --hidden-dim 64 --message-layers 2 --batch-size 32 --epochs 700 --replay-capacity 8000 \
  --sample-fraction 0.05 --transitions-per-batch 20000 --episode-workers 8 \
  --games-per-process 4 --parallel-envs 32 --neural-device cpu --threads 1 --cpu-budget 11
```

**The game.** The networks after that update (generation 1) played one more
game in one process through `play_episode` (`studies/campaign/learning.py`),
exactly as a training game process plays: 64 simulations, depth 16, exploration
noise, temperature 1, run seed 1936 and environment seed 1105.

- **Every decision kept.** The sample fraction was 1, so that a readable
  decision could be chosen. The share kept does not change what a sample holds.
- **What a sample lacks, noted on the side.** `_decide` was wrapped to also note
  the moves' names, the raw visit counts, the priors with noise and each move's
  average values.
- **The result.** The game ended after 1,349 decisions and 183 dice rolls, with
  Axis +49.0, Allies −63.8 and Comintern −106.2. It took 218 seconds.
- **A replay.** Playing it again gave the same visits and moves at every
  decision.

**Checks.** The probabilities the network gives for the stored input equal the
priors the search received. The stored policy equals the visit counts divided
by 64.

## The sample: decision 612

Round 5, the CCP's Combat Movement, chosen by the Comintern. The CCP's mountain
infantry in Shensi, with one move left, may attack one of four neighbouring KMT
zones, or the CCP may end the phase.

| Move | Visits | Share (stored) | Network's probability | Prior with noise | Average value for the Comintern |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shensi → Hopeh (played) | 36 | 0.5625 | 0.1025 | 0.0848 | −101.63 |
| Shensi → Suiyuan | 2 | 0.0313 | 0.0957 | 0.0718 | −102.40 |
| Shensi → Szechwan | 5 | 0.0781 | 0.0861 | 0.1765 | −102.50 |
| Shensi → Tsinghai | 9 | 0.1406 | 0.1847 | 0.2679 | −102.27 |
| End Combat Movement | 12 | 0.1875 | 0.5311 | 0.3990 | −102.36 |

A move's average value is the mean, over the simulations that began with it, of
the network's predicted final score where each stopped. The best average drew
most simulations, although the noise had lowered that move's prior.

## How the 64 simulations were spent

Replaying the game to decision 612 with the search's trace on (`record_trace`,
which only records) gave the same visits. The Comintern's results of the
simulations that began with each move:

| Move | Simulations | Worst | Best | Average |
| --- | ---: | ---: | ---: | ---: |
| Shensi → Hopeh | 36 | −106.02 | −101.16 | −101.63 |
| Shensi → Suiyuan | 2 | −102.41 | −102.40 | −102.40 |
| Shensi → Szechwan | 5 | −102.64 | −102.37 | −102.50 |
| Shensi → Tsinghai | 9 | −102.36 | −102.16 | −102.27 |
| End Combat Movement | 12 | −102.46 | −102.20 | −102.36 |

- **Simulations 1 to 14** tried every move: Tsinghai 7 times, ending the phase
  3, Hopeh 2, Szechwan and Suiyuan once each. Hopeh's two, simulations 6 and 11,
  stopped one and two steps after the attack, before its battle, with Hopeh
  still the KMT's: −102.22 and −102.23.
- **Simulation 15** was the first to play on through the end of Combat Movement
  and the battle for Hopeh, with its dice roll. The CCP held Hopeh at its end,
  rated −101.42. The 33 later simulations of the attack all passed through the
  CCP's capture, and 23 of them scored between −101.43 and −101.16.
- **Simulations 15 to 51** chose the attack 32 times out of 37. Before
  simulation 33, the attack's rescaled first term was 0.77 and the other
  moves' 0 to 0.25.
- **Simulations 54 to 64** all went to the other moves. Simulation 53, one of
  the attack's, stopped at the depth limit at a position rated −106.02. That
  widened the range the results are rescaled to, from about −102.6 to −101.2
  before, to −106.0 to −101.2. The first terms then lay close together: at
  the end, 0.90 for the attack and 0.72 to 0.77 for the others. So the second
  term, larger for the moves tried less, drew the last simulations to them.
- **The other 28 simulations** went roughly in proportion to the priors after
  noise: 2, 5, 9 and 12, where an exact split by those priors gives 2.2, 5.4,
  8.2 and 12.2.

**Inferred:** without simulation 53's outlier, the attack would have drawn more
of the last simulations. One extreme result anywhere in the tree changes how a
search spends its remaining simulations, because the range is set by the worst
and best averages seen.

**Found on 9 November** ([depth limit record](depth_limit_2026_11_09.md#simulation-53-at-decision-612)):
simulation 53 reached a new position where Japan decides, so the Axis network
rated it, the only stop of this search that network rated. At the two chance
events of this search, the Axis network gave the Comintern about 5 points less
than the Comintern's own network did. The outlier therefore comes from which
network rated the position; the depth limit did not cause it.

**Which move each simulation began with**, as the design document's
[figure](../design/figures/sample_simulations.svg) draws it from this trace:

| Move | Simulations | Count |
| --- | --- | ---: |
| Shensi → Hopeh | 6, 11, 15, 17–31, 33–37, 39–41, 43–50, 52, 53 | 36 |
| Shensi → Suiyuan | 7, 60 | 2 |
| Shensi → Szechwan | 3, 38, 54, 57, 63 | 5 |
| Shensi → Tsinghai | 2, 4, 5, 9, 10, 12, 14, 61, 64 | 9 |
| End Combat Movement | 1, 8, 13, 16, 32, 42, 51, 55, 56, 58, 59, 62 | 12 |

**The scores, rebuilt from the trace** on 5 November. The trace records, for
each simulation, its first move, its result and every move's rescaled first
term before it. Adding the second term, computed from the priors after noise,
gives the highest score to the move the simulation chose in all 64 simulations.
The range the first terms were rescaled to follows from them:

| Before simulations | Lowest average | Highest average | Set by |
| --- | ---: | ---: | --- |
| 4–15 | −102.63 | −102.16 | simulation 3 (Szechwan) and simulation 2 (Tsinghai) |
| 16–18 | −102.63 | −101.42 | simulation 15, the first through the battle |
| 19–20 | −102.63 | −101.38 | simulation 18 |
| 21–38 | −102.63 | −101.16 | simulation 20 |
| 39–53 | −102.64 | −101.16 | simulation 38 (Szechwan) |
| 54–64 | −106.02 | −101.16 | simulation 53, stopped at the depth limit |

A move that only one simulation has tried has that simulation's result as its
average, so the deepest moves of a path set the extremes. The scores before
simulation 33 (it began with the attack) and before simulation 54 (it began
with the attack on Szechwan):

| Before | Move | Simulations so far | Average | First term | Second term | Score |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 33 | Shensi → Hopeh | 18 | −101.50 | 0.768 | 0.038 | 0.806 |
| 33 | Shensi → Suiyuan | 1 | −102.40 | 0.161 | 0.309 | 0.470 |
| 33 | Shensi → Szechwan | 1 | −102.63 | 0.000 | 0.761 | 0.761 |
| 33 | Shensi → Tsinghai | 7 | −102.26 | 0.253 | 0.289 | 0.541 |
| 33 | End Combat Movement | 5 | −102.39 | 0.166 | 0.573 | 0.739 |
| 54 | Shensi → Hopeh | 36 | −101.63 | 0.902 | 0.025 | 0.927 |
| 54 | Shensi → Suiyuan | 1 | −102.40 | 0.745 | 0.396 | 1.141 |
| 54 | Shensi → Szechwan | 2 | −102.64 | 0.695 | 0.649 | 1.344 |
| 54 | Shensi → Tsinghai | 7 | −102.26 | 0.773 | 0.369 | 1.142 |
| 54 | End Combat Movement | 7 | −102.36 | 0.753 | 0.550 | 1.303 |

**What the network read** (part 1 of the sample): 840 answers about the board,
from all 37 zones; 191 about the position as a whole; 80 about the five moves;
and 8 zones named by the moves' paths. The arrays take 12,448 bytes. Some of the
board answers:

| Zone | Answers |
| --- | --- |
| Shensi (9 answers) | held by the CCP; one CCP militia with no move left and one mountain infantry with one; a railroad to Hopeh |
| Hopeh (28) | held by the KMT; a fortification and a major shipyard under construction, 5 IPP paid into each; no units |
| Suiyuan (12) | held by the KMT; 3 KMT militia |
| Szechwan (2) | held by the KMT; no units |
| Tsinghai (13) | held by the KMT; 2 KMT infantry and 1 militia |

**How the game ended** (part 4), against the Comintern network's prediction at
this decision:

| Alliance | Final score (stored) | Value target (score ÷ 100) | Network's value |
| --- | ---: | ---: | ---: |
| Axis | +49.0 | 0.490 | 0.251 |
| Allies | −63.8 | −0.638 | −0.424 |
| Comintern | −106.2 | −1.062 | −1.024 |

On this sample alone, the Comintern network's policy loss (cross-entropy
against the shares) is 1.903, and its value loss (mean squared error over the
three values) is 0.035.

## A fresh network gives every position the same values

At the same commit, a fresh 64×2 network (`torch.manual_seed(1936)`) read four
decisions of a random game: decisions 0, 100, 200 and 300 of environment seed 5,
with moves drawn by `random.Random(5)`.

- **Values.** At all four it gave Axis −0.4212, Allies 0.2407 and Comintern
  −0.2264.
- **Priors.** These still differ between moves: from 0.017 to 0.270 at the
  decision with 18 moves. A move's vector also carries its zones' fixed map
  facts, which the network reads through layers that start random.
- **Why.** Every row starts at zero, so nothing a position answers reaches the
  network until training changes the rows.

**Inferred:** in a run's first batch, a search sees different values only at
game ends. Its split therefore follows the network's arbitrary priors, the noise
and the rare game ends it reaches.

## The update after the batch

Read on 5 November from the run's manifest
(`studies/campaign/runs/sample-example-2026-11-05/manifest.json`, not tracked)
and checked against `CampaignLearner.update` in `studies/campaign/learning.py`.

- **The buffer.** The update began with the batch's 1,611 samples as the whole
  replay buffer: a run's first update has no older samples.
- **The draws.** Each of the 700 steps drew 32 different samples from the whole
  buffer (`random.Random.sample`), 22,400 draws in all, about 14 per sample.
- **Time.** The games played for 851 seconds, and the update took 48.7 seconds
  (the run's `learning_updates` timing, which also counts adding the samples to
  the buffer), 70 ms per step. Another session's test suite ran beside both. On
  2 November, with no other load, the speed test's batch with the same settings
  (`zone-speed-2026-11-02/cpuserver`) played for 881 seconds and updated for 45.5.

**Each network's own samples.** The alliance to move in a step's 32 samples, over
the 700 steps:

| Alliance | Decisions in the batch | Share | Per step, on average | Fewest | Most |
| --- | ---: | ---: | ---: | ---: | ---: |
| Axis | 17,560 | 53% | 16.1 | 7 | 25 |
| Allies | 8,068 | 24% | 8.1 | 2 | 17 |
| Comintern | 7,434 | 22% | 7.8 | 1 | 17 |

Every step held decisions of all three alliances, so each network's policy loss
had samples to average in every step.

**One step on 1 sample or on 32.** Later on 5 November, steps that repeat
`CampaignLearner.update`'s step for all three networks, with this run's networks
and samples, one thread and fresh Adam optimizers, were timed in six interleaved
rounds of 40 steps on 1 sample and 8 steps on 32. The medians were 21.3 ms per
step on 1 sample and 78.2 ms on 32: 3.7 times the time for 32 times the samples.
Other programs kept the machine's load average at 12 to 15 on its 14 cores.

## Draws per kept sample in recorded runs

Once the buffer is full, every sample in it has the same chance at each draw, and
a sample stays until as many newer ones have joined as the buffer holds. On
average a kept sample is therefore drawn

$$
\text{draws per sample} \approx \frac{\text{steps per update} \times \text{samples per step}}{\text{samples kept per batch}}
$$

times before it leaves. From the runs' manifests:

| Run | Network | Samples per step | Steps per update | Games per batch | Samples kept per batch | Draws per sample |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 31 October, GPU training (`gpu-training-2026-10-31`, 2 batches) | graph input, 64×2 | 32 | 700 | 32 | 2,754 | 8.1 |
| 2 November, CPU speed test (`zone-speed-2026-11-02/cpuserver`) | zone input, 64×2 | 32 | 700 | 32 | 1,887 | 11.9 |
| Night of 2 November, batches 1–2 (`night-2026-11-02/training`) | zone input, 256×8 | 128 | 700 | 117 | 8,415 | 10.6 |
| 5 November, this record (`sample-example-2026-11-05`) | zone input, 64×2 | 32 | 700 | 32 | 1,611 | 13.9 |

The first three are the runs whose throughput the design document compares. The
games of 31 October were the longest, about 1,730 decisions each, against about
1,160 in the 2 November speed test and 1,030 here, so its batches kept the most
samples per game, and each was drawn least often. The night run's games averaged
about 1,450 decisions; it drew 128 samples per step for its 117 games per batch.
Every run kept 4.9 to 5.1% of its decisions.

## What this does and does not show

- **Measured:** the values above, for this game and these networks.
- **Not shown:** that the search's favourite was a good move. After one batch the
  networks are weak, and one sample says nothing about playing strength.
- **Not shown:** how much a first-batch split depends on the noise. That follows
  from the search's formula, and was not measured.
