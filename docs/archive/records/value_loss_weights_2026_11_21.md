# Training on the long run's saved samples at four weights of the value loss — 21 November 2026

Q-015 asked whether the value loss should count for more in a training step,
since a linear model of the network's input had predicted the long run's final
scores better than the network's values
([record](long_run_samples_2026_11_21.md)). The owner chose to test it first on
the training samples the long run had saved. The
[evidence file](value_loss_weights_2026_11_21.json) holds every number below.

**Setup.** `tools/train_on_saved_samples.py tmp/training-2026-11-20c --start 3
--weights 1 10 50 200 --steps 6000 --check-every 500`, run with that run's own
copy of the code on one CPU core, 67 minutes in all:

- **The games.** The 1,654 games of the replay buffer that the long run's last
  run, choice B of Q-013, saved at 07:40 on 21 November. Each has a training
  sample from generation 3 or later, so all of them ended after generation 3 was
  exported, and generation 3 had trained on none of them. 1,324 games, with
  19,943 training samples, trained; 330 games, with 5,057, were held out (fold 0
  of the folds `tools/rate_replay_samples.py` uses).
- **The training.** For each weight w a fresh copy of generation 3 took 6,000
  training steps as a network update takes them (`CampaignLearner.update` in
  `studies/campaign/learning.py`): Adam at a learning rate of 0.001, minibatches
  of 32 training samples drawn at random, and the loss w times the value loss
  plus the policy loss. Every weight drew the same minibatches. 6,000 training
  steps draw 192,000 times, about 9.6 times each training sample.
- **The ratings.** At the start and every 500 training steps the copy rated the
  held-out samples, and a fixed fifth of the training samples for its value loss
  on them.
- **Two yardsticks** on the same held-out samples: the networks that played the
  decisions, generations 2 to 10, and a linear model of the same input fitted
  game round by game round on the 1,324 training games, as in
  [the earlier record](long_run_samples_2026_11_21.md#the-values-game-round-by-game-round-beside-a-linear-model).

## Held-out games

The value loss on the held-out samples, the share of each alliance's
final-score variance the values explain there, and the value loss on the
training samples. *Best* is the rating with the lowest held-out value loss.

| | Held-out value loss | Axis | Allies | Comintern | Value loss on training samples |
| --- | ---: | ---: | ---: | ---: | ---: |
| The networks that played the decisions | 0.0136 | 19.3% | 29.0% | 47.4% | |
| The linear model | 0.0119 | 33.0% | 38.4% | 51.4% | |
| Generation 3, before training | 0.0145 | 13.3% | 25.4% | 44.9% | 0.0149 |
| Weight 1, best, after 500 training steps | 0.0122 | 31.6% | 38.9% | 46.8% | 0.0115 |
| Weight 1, after 6,000 | 0.0142 | 18.3% | 22.0% | 47.8% | 0.0068 |
| Weight 10, best, after 1,500 | 0.0126 | 26.0% | 33.5% | 51.3% | 0.0066 |
| Weight 10, after 6,000 | 0.0138 | 20.5% | 25.6% | 48.2% | 0.0021 |
| Weight 50, best, after 1,000 | 0.0126 | 25.4% | 33.8% | 52.4% | 0.0071 |
| Weight 50, after 6,000 | 0.0136 | 23.0% | 27.5% | 46.0% | 0.0014 |
| Weight 200, best, after 1,000 | 0.0125 | 27.4% | 33.6% | 51.9% | 0.0068 |
| Weight 200, after 6,000 | 0.0132 | 26.3% | 30.4% | 45.7% | 0.0015 |

Between consecutive ratings of one copy the held-out value loss swung by up to
about 0.001: for weight 1, 0.0122, 0.0132 and 0.0123 after 500, 1,000 and 1,500
training steps.

The policy's KL divergence from the visit shares on the held-out searched
decisions was 0.326 before training, 0.30 at its lowest for every weight, and
after 6,000 training steps 0.327 for weight 1, 0.328 for 10, 0.340 for 50 and
0.343 for 200.

## By game round

The share of the Axis's final-score variance explained on the held-out samples
of each game round, for each weight at its best rating:

| Game round | Linear model | Networks that played | Generation 3 | Weight 1 | Weight 10 | Weight 50 | Weight 200 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1.9% | −3.4% | −7.5% | 0.4% | −12.0% | −4.3% | −4.1% |
| 2 | 8.9% | −12.8% | −19.1% | 8.1% | 1.2% | −7.6% | −9.9% |
| 3 | 23.5% | −1.6% | −6.1% | 23.2% | 13.3% | 11.2% | 17.4% |
| 4 | 19.0% | 4.9% | −21.0% | 23.4% | 19.6% | 13.9% | 17.9% |
| 5 | 23.3% | 8.0% | −6.5% | 26.8% | 16.9% | 11.7% | 22.1% |
| 6 | 36.1% | 18.9% | 15.2% | 32.9% | 33.0% | 35.4% | 35.3% |
| 7 | 35.5% | 26.5% | 22.6% | 39.5% | 35.8% | 32.3% | 33.6% |
| 8 | 39.2% | 34.4% | 29.1% | 39.9% | 40.1% | 40.3% | 40.0% |
| 9 | 55.8% | 51.1% | 47.8% | 52.6% | 50.5% | 50.5% | 52.6% |
| 10 | 70.8% | 47.8% | 48.5% | 58.5% | 54.6% | 58.7% | 62.3% |
| 11 | 80.3% | 65.4% | 68.2% | 71.1% | 67.8% | 70.0% | 68.0% |

For the Allies in game round 11 the linear model explained 82.1%, the copies at
their best 68.9% to 72.6%; for the Comintern 91.9% against 79.0% to 85.6%.

## What this shows and does not show

It shows:

- **No weight above 1 predicted the held-out games better.** All four weights
  reached about the same lowest held-out value loss, 0.0122 to 0.0126, within
  the swings between ratings, after 500 to 1,500 training steps, when each
  training sample had been drawn about once or twice.
- **After that the copies fit the games they trained on, not the others.** The
  value loss on the training samples kept falling while the held-out value loss
  rose. A higher weight fit the training games faster and further, to 0.0014
  instead of 0.0068 after 6,000 training steps, without predicting the
  held-out games better, and cost the policy a little: its KL divergence ended
  at 0.343 for weight 200 against 0.327 for weight 1.
- **The values are limited by the number of games.** A network that has seen
  these 1,324 games once or twice predicts the other 330 about as well as the
  linear model over all game rounds, 0.0122 against 0.0119, and better than
  the networks that played them, 0.0136; more passes over the same games make
  it worse.
- **Late in the game the linear model stays ahead.** In game round 11 it
  explained 80% of the Axis's variance, the copies at their best 68% to 71%.

It does not show:

- **Why the network falls behind the linear model late in the game.** One
  candidate, inferred and not tested: each zone's vector is layer-normalized
  before the values read the zones' average and maximum
  ([section 6.4 of the design document](../../design/README.md#64-a-zones-vector)),
  so how much a zone holds reaches the values only through the direction of its
  vector, while the linear model adds up what every zone holds.
- **Whether weight decay or fewer draws per training sample** would keep a
  network from fitting its training games; neither was tried.
- **How this carries over to a training run,** where new games keep arriving
  and each training sample is drawn about 4.6 times
  ([section 8.7 of the design document](../../design/README.md#87-how-often-a-training-sample-is-drawn)).
