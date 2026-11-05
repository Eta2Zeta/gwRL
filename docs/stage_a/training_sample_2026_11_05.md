# One real training sample — 5 November 2026

The [design document](../design/README.md#6-how-the-networks-learn) explains what
a training sample stores by showing one real sample. This record says how that
sample was made and gives its exact values; the
[evidence file](training_sample_2026_11_05.json) holds them in full, with every
answer the network read. It also records why the example does not come from a
run's first batch: a fresh network gives every position the same values.

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

## What this does and does not show

- **Measured:** the values above, for this game and these networks.
- **Not shown:** that the search's favourite was a good move. After one batch the
  networks are weak, and one sample says nothing about playing strength.
- **Not shown:** how much a first-batch split depends on the noise. That follows
  from the search's formula, and was not measured.
