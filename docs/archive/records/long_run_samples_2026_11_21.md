# What the long run's training samples show about its values and search targets — 21 November 2026

The long training run of 19 to 21 November 2026 played 9,576 eleven-round games
in four runs and 38 network updates, with one 256×8 network for the three
alliances, 64 simulations to depth 16 per decision
([record of its progress](long_run_progress_2026_11_21.md)). It saved, for
every game, how many actions of each kind were played and the final scores
(`runner.updates[].episodes[]` in each run's `manifest.json`), and its last run,
choice B of Q-013 (`tmp/training-2026-11-20c`), saved its replay buffer in
`run/checkpoint.pt` at 07:40 on 21 November: 25,000 training samples, 1% of the
decisions of its latest 1,654 games. This record reads them for what limits the
learning. Nothing was played again: the only new computation is network forward
passes on the saved training samples. The
[evidence file](long_run_samples_2026_11_21.json) holds every number below.

How the numbers were made:

- **Decisions and final scores:** summed over each game's `action_counts` and
  `observed_terminal_returns`, in the four runs' `manifest.json`.
- **The training samples:** `tools/rate_replay_samples.py
  tmp/training-2026-11-20c`, run with that run's own copy of the code. It rates
  each training sample with the network generation that played the decision.
  That generation was exported before the decision's game ended, so the game had
  not trained it. 24,112 of the samples come from games played by generations 3
  to 9, 866 by generation 2 and 22 by generation 10. The same tool measures the
  two losses' gradients in generation 10.
- **The held-out games:** the evaluation reports in
  `tmp/training-2026-11-20c/evaluations-alliances/` of generation 10 and of the
  scripted balanced policy, each playing one alliance against the scripted
  balanced policy in the other two seats on the six seeds of
  [the progress record](long_run_progress_2026_11_21.md#play-against-the-scripted-opponents).
- **The inference server:** the counters that each network update records
  under `evaluator` in `manifest.json`, taken between consecutive network
  updates of one invocation.

## Where a game's decisions go

The kinds of action, grouped by the first word of their names, as shares of a
game's decisions (chance events left out):

| Kind of action | Choice B's 2,520 games | The first network update's 252 games |
| --- | ---: | ---: |
| Naval (starting a fleet's move, its route, entering a port and others) | 38.4% | 29.6% |
| Moving land units (`movement_route`) | 17.3% | 13.1% |
| Ending a phase (`end_phase`) | 14.4% | 22.0% |
| Economy (purchases, placing units, research) | 13.1% | 15.2% |
| Land combat | 11.5% | 12.4% |
| Air | 3.3% | 5.5% |
| Recruitment, politics and the rest | 1.9% | 2.2% |
| **Decisions a game** | **1,532** | **1,004** |

A fleet's move is two decisions, its start (`naval_start_move`) and its route
(`naval_route`): 212.6 of each a game in choice B, 425 of the 1,532 decisions.
`movement_route` was 265.7 a game, `end_phase` 221.0, `economy_purchase` 94.9.

## What the search leaves as policy targets

4,445 of the 25,000 training samples (17.8%) are decisions with one legal
action, played without a search. The other 20,555 were searched; their visit
shares are the policy targets. By the number of legal actions:

| Legal actions | Share of the training samples | Visit share of the most visited action | Actions visited | Move played was not a most visited action | KL divergence of the network's probabilities from the visit shares |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 17.8% | 1.00 | 1.0 | 0% | 0 |
| 2 to 4 | 15.9% | 0.64 | 2.6 | 36% | 0.098 |
| 5 to 16 | 25.6% | 0.35 | 10.4 | 63% | 0.271 |
| 17 to 63 | 28.8% | 0.23 | 31.4 | 76% | 0.360 |
| 64 or more (median 128) | 12.0% | 0.03 | 68.7 | 71% | 0.383 |
| **All searched** | **82.2%** | **0.32** | **24.7** | **63%** | **0.285** |

- **Actions visited** counts the actions at the root with any visit, the
  simulations of the decision's own search and those its kept search tree
  already held, which is how a decision can show more than 64.
- **Move played was not a most visited action** is the chance that the move,
  drawn from the visit shares at temperature 1 (`_decide` in
  `studies/campaign/learning.py`), is none of the actions that tied for the most
  visits. Ties make it smaller where most actions were visited once.

By the kind of decision, the commonest kind among its legal actions other than
ending the phase:

| Kind of decision | Share of the searched samples | Mean legal actions | Visit share of the most visited action | Move played was not a most visited action | KL divergence | Share of all the KL divergence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Naval | 48.9% | 22.1 | 0.29 | 69% | 0.297 | 51% |
| Moving land units | 22.1% | 54.1 | 0.24 | 67% | 0.310 | 24% |
| Economy | 15.8% | 75.6 | 0.31 | 58% | 0.331 | 18% |
| Land combat | 8.6% | 2.6 | 0.64 | 35% | 0.100 | 3% |
| Air | 2.3% | 72.2 | 0.22 | 66% | 0.317 | 3% |
| Recruitment, politics and influence | 2.1% | 5.7 | 0.61 | 38% | 0.110 | 1% |

Within land combat, deciding whether a battle goes on
(`land_continue_fighting`, two legal actions) gave the most visited action 0.73
of the visits, and the move played was the other one 27% of the time. Among the
alliances, the Axis made 62% of the searched samples, with 33.9 legal actions on
average, the Allies 26% with 56.7, and the Comintern 12% with 8.8.

### At decisions with many legal actions

Counted on 22 November from the same training samples, with each action's visits
taken as its visit share divided by the decision's smallest visit share, one
visit. At the 7,197 kept decisions with 17 to 63 legal actions, 31 on average,
the search tried every legal action, and 62% of them only once; the most
visited action had a median of 15 visits and was among the network's three
likeliest actions at 47% of these decisions. At the 2,988 with 64 or more, it
tried 56% of the legal actions, 98% of those once, and the most visited action
had a median of 2 visits.

A decision of the first kind, training sample 21,691 of the replay buffer: the
KMT's Combat Movement in game round 11 of a game that generation 9 played, which
ended Axis +28.4, Allies −43.8 and Comintern −97.8. Its 28 legal actions were 27
attacks, each moving one unit into an enemy zone, and ending Combat Movement:

| Legal action | Visits | Visit share | The network's probability |
| --- | ---: | ---: | ---: |
| The cavalry in Kweichow attacks Hopeh, through Szechwan | 16 | 0.25 | 0.046 |
| The infantry in Beiping attacks Manchuria-Rehe | 10 | 0.16 | 0.049 |
| The cavalry in Szechwan attacks Hopeh | 4 | 0.06 | 0.058 |
| The infantry in Sikang attacks Tsinghai | 3 | 0.05 | 0.029 |
| Seven more, among them the infantry in Beiping attacking Hopeh, the network's likeliest action, and ending Combat Movement | 2 each | 0.03 each | 0.023 to 0.077 |
| The other 17 attacks | 1 each | 0.016 each | 0.011 to 0.046 |

## The values, game round by game round, beside a linear model

For each game round, the share of the variance of each alliance's final score
that the values explain at the decisions of that game round. *Network* is the
values of the network generation that played the decision. *Linear model* is ridge
regression on the same input's global feature values and its zone feature
values summed over the 37 zones, fitted for each game round on four fifths of
the 1,654 games and tested on the other fifth, five times over, each game's
samples kept together, with its ridge penalty chosen within the four fifths.

| Game round | Samples | Axis: network | Axis: linear model | Allies: network | Allies: linear model | Comintern: network | Comintern: linear model |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3,063 | −6.1% | 1.3% | −4.1% | 3.0% | 3.5% | 6.7% |
| 2 | 2,549 | −9.4% | 8.4% | −0.8% | 11.5% | 32.3% | 32.4% |
| 3 | 2,401 | −0.6% | 19.5% | 9.3% | 24.6% | 40.2% | 40.8% |
| 4 | 2,231 | 8.7% | 19.4% | 18.2% | 26.4% | 41.6% | 45.1% |
| 5 | 2,164 | 6.1% | 18.1% | 17.6% | 26.5% | 49.5% | 48.6% |
| 6 | 2,169 | 18.9% | 33.4% | 27.9% | 37.5% | 56.7% | 57.7% |
| 7 | 2,119 | 24.9% | 37.9% | 34.9% | 45.8% | 64.4% | 67.8% |
| 8 | 2,115 | 38.8% | 45.6% | 46.6% | 52.9% | 67.6% | 71.5% |
| 9 | 2,095 | 50.5% | 58.9% | 54.6% | 62.5% | 71.5% | 79.9% |
| 10 | 2,045 | 55.0% | 69.3% | 60.1% | 72.5% | 76.5% | 84.1% |
| 11 | 2,049 | 68.1% | 82.9% | 70.7% | 84.3% | 79.6% | 91.7% |

A negative share means a miss larger than always predicting the game round's
average final score. Each alliance's final scores have a standard deviation of
13 to 16 points at every game round. In the eleventh game round the network
missed the Axis's final score by a typical 7.6 points, the linear model by
about 5.5.

The later generations did better early in the game: on the samples of games
played by generations 6 to 10 the network explained 15.0% of the Axis's
variance in game round 5, against −5.5% for generations 2 to 5, but 67.8%
against 68.3% in game round 11.

## The two losses' gradients

Over 20 minibatches of 32 training samples drawn from the replay buffer, with the
network of the run's last network update, generation 10, the value loss averaged
0.0093 and the policy loss 2.088. On each group of the network's parameters, the
size of each loss's gradient is the square root of its entries' squares added up
over the 20 minibatches, and the cosine is the two gradients' entries multiplied
pairwise, added up and divided by both sizes:

| Parameters | Value loss's gradient | Policy loss's gradient | Value loss's over the policy loss's | Cosine of the angle between the two |
| --- | ---: | ---: | ---: | ---: |
| The value head | 0.367 | 0 | | |
| The layers only the action probabilities read | 0 | 1.082 | | |
| The embedding tables and the map-facts layer | 0.049 | 0.280 | 0.17 | −0.04 |
| The message-passing layers | 0.050 | 0.452 | 0.11 | −0.01 |
| The layer that makes the summary vector | 0.047 | 0.078 | 0.60 | −0.03 |

The last three groups are read by both heads. In the embedding tables and the
message-passing layers the value loss's gradient was a sixth to a ninth the size
of the policy loss's, and the two were almost at right angles. A training step
moves the parameters against the gradient of the sum of the two losses, so it
moves those layers almost only where the policy loss points.

## Final scores in self-play

Over the 38 network updates the mean final scores of each network update's 252
games stayed between +24.9 and +35.5 for the Axis, −60.2 and −50.5 for the
Allies, and −98.2 and −83.6 for the Comintern. Within one network update's
games each alliance's final scores had a standard deviation of 10.6 to 20.5
points.

## The network as the Allies against the scripted policy

Means over the six held-out games of each, the Allies played by generation 10
of choice B or by the scripted balanced policy, against the scripted balanced
policy as the Axis and the Comintern:

| | Generation 10 as the Allies | The scripted policy as the Allies |
| --- | ---: | ---: |
| The Allies' final score | −68.5 | −31.9 |
| The Allies' decisions a game | 249 | 483 |
| Land territories the KMT possesses at the end | 8.5 | 18.5 |
| Land territories Japan possesses at the end | 16.2 | 8.8 |
| The Allies' income at the end | 7.2 | 17.2 |
| KMT units lost | 23.5 | 40.3 |
| Japanese units lost | 45.7 | 48.0 |

As the Axis, generation 10 made 846 Axis decisions a game against the scripted
Axis's 1,120, lost 27.0 Japanese units against 48.0, and Japan possessed 7.5
land territories at the end against 8.8.

## What a game and a training sample cost

Between network updates the inference server answered a median of 51 to 54
network evaluations per decision in the four runs, 5,900 to 7,000 a second, in
forward passes of about 129 states. Its forward passes took 85% to 88% of its
time and it waited 2% of it. A game of choice B, 1,532 decisions, thus took about
80,000 network evaluations, and with 1% of the decisions kept, one training
sample about 5,300. The network updates took 1,618 seconds of choice B's 32,229
(5%).

## What this shows and does not show

It shows:

- **The values read less from the input than a linear model does.** In every
  game round the linear model, fitted on about 1,300 games, explained more of
  the Axis's and the Allies' final scores than the network, by 6 to 20
  percentage points, and in the last game round 83% to 92% against the network's
  68% to 80%. So the input holds more about the final scores than the network's
  values use.
- **Early in the game the values say nothing about the Axis.** In game rounds 1
  to 3 they explain less than predicting the average.
- **The layers below the two heads learn almost only from the policy loss.**
  There the value loss's gradient is a sixth to a ninth the size of the policy
  loss's.
- **At half of the searched decisions the policy targets mostly record which
  actions were tried.** 41% of the kept decisions, half of the searched ones,
  have 17 or more legal actions; there the search's 64 simulations visit 31 to
  69 of them, mostly once, giving the most visited action 3% to 23% of the
  visits.
- **Self-play mostly does not play the search's choice.** At 63% of searched
  decisions the move played is not a most visited action: about 800 of a
  game's 1,260 searched decisions.
- **Half of the search goes to fleets.** Naval decisions are 49% of the searched
  samples and carry 51% of the policy's KL divergence from the visit shares.
- **Against the scripted Japan, the network's KMT holds less of China.** It
  makes half the scripted KMT's decisions and possesses less than half its land
  territories at the end.

It does not show:

- **Why the values fall short.** That the policy loss's hold on the shared
  layers is what holds the values back is inferred, not tested. Two other
  causes are possible: too few training steps per training sample, and the
  restarts with new Adam averages. Training on these saved samples with the
  value loss weighted more would tell; it was done the same day, and no weight
  above 1 predicted held-out games better
  ([record](value_loss_weights_2026_11_21.md)).
- **How much of a final score is predictable at all.** The linear model shows
  what the input holds at least, not at most.
- **Whether fleets matter less than armies** for the final scores, or whether
  the scripted KMT plays well: only that it scores higher against the scripted
  Japan than the network's KMT does.
- **Whether any change helps.** That needs training runs or, for the values,
  training on these saved samples.
