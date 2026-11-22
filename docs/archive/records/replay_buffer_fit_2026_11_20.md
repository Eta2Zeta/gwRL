# How the network of the training run of 19 to 21 November fits its replay buffer and new games — 20 November 2026

The long training run of 19 and 20 November 2026 played 252 concurrent
eleven-round games against one 256×8 network for the three alliances, on the
Mac's GPU, with self-play that never stops. It ran as three runs, each starting
from the previous run's newest network with a new replay buffer and new Adam
averages: the first night, from commit `999c90c` (19 November 19:58 to
20 November 06:53); the morning, from `7adac20` (06:54 to 16:12); and the current
run, from `1463ff4` (from 16:22). All three searched 64 simulations to depth 16,
kept a random 5% of each game's decisions as training samples, and ran a network
update after every 252 finished games: 525 training steps, each on a minibatch
of 32 training samples drawn from a replay buffer of the latest 8,000, with Adam
at a learning rate of 0.001 and no weight decay (`runner.config` in each run's
`manifest.json`). The [evidence file](replay_buffer_fit_2026_11_20.json) holds
the numbers of every network update up to 20:07 on 20 November, made from each
run's `manifest.json` with `summarize_games` in `tools/compare_training_runs.py`
and from the losses that each training step records (`CampaignLearner.update` in
`studies/campaign/learning.py`).

Every network update records two value losses:

- **On its minibatches:** the value loss of each training step on its minibatch,
  before that step's Adam step. This is the error on games in the replay buffer,
  which the network has been training on.
- **On fresh games:** the value loss on the 252 games that finished before the
  network update, scored by the networks that played them, before any training
  step drew their training samples (section 10 of the
  [design document](../../design/README.md#10-measuring-strength)).

| Run, network updates | Times of the network updates | Fresh games: value loss | Fresh games: variance explained | Minibatches: value loss in the first 50 training steps | Minibatches: value loss in the last 50 training steps |
| --- | --- | ---: | ---: | ---: | ---: |
| First night, 2 to 4 | 19 Nov 21:28 to 22:52 | 0.0171 | 3% | 0.0145 | 0.0073 |
| First night, 5 to 7 | 23:41 to 02:06 | 0.0204 | 19% | 0.0156 | 0.0065 |
| First night, 8 to 10 | 02:55 to 04:29 | 0.0174 | 14% | 0.0126 | 0.0048 |
| First night, 11 to 13 | 05:16 to 06:52 | 0.0135 | 30% | 0.0116 | 0.0047 |
| Morning, 1 to 3 | 08:16 to 10:08 | 0.0176 | 29% | 0.0133 | 0.0046 |
| Morning, 4 to 6 | 11:32 to 13:18 | 0.0166 | 21% | 0.0131 | 0.0049 |
| Morning, 7 to 9 | 14:08 to 16:12 | 0.0227 | 17% | 0.0192 | 0.0057 |
| Current, 1 to 4 | 17:34 to 20:07 | 0.0168 | 25% | 0.0130 | 0.0049 |

The fresh-game columns pool the games of the row's network updates; the
minibatch columns average the row's network updates.

- **The first network update.** The untrained network missed the final scores
  of its games by 51 points (value loss 0.262). The games scored by the network
  of the first network update were missed by 13 points (0.0169).
- **Since then.** The share of the final scores' variance that the value loss on
  fresh games explains rose from 3% to 30% during the first night. From the
  first night's eleventh network update, at 05:16 on 20 November, it has stayed
  between 17% and 30%, with no trend. The policy's KL divergence from the
  search's visit shares stayed between 0.239 and 0.253.
- **The fit to the replay buffer.** In each of the 25 network updates after the
  first, the value loss on its minibatches fell 1.9 to 3.7 times (median 2.6)
  within its 525 training steps, to between 0.0039 and 0.0087 in the last 50.
  The games that then finished before the next network update, which the
  network had not trained on, had a value loss of 0.011 to 0.026: 1.9 to 4.8
  times (median 3.3) the value loss of the last 50 training steps before them,
  in the 22 such pairs within one run. In points of final score, the medians
  over all 25 network updates are a miss of 7.1 points on the games in the
  replay buffer and 13.1 points on fresh games.
- **Training samples that are never drawn.** The 252 games before a network
  update kept 18,276 training samples on average (13,781 to 19,355, the first
  network update left out), more than twice the replay buffer's 8,000. A game's
  training samples join the replay buffer when it ends (`accept_episode` in
  `studies/campaign/learning.py`) and the replay buffer keeps the latest 8,000,
  those of about the latest 110 games. So more than half of the training samples
  kept leave the replay buffer before a training step can draw them (inferred
  from the counts). A network update's 525 training steps draw 16,800 times:
  about 67 times for each of its 252 games, and about 2.1 times for each training
  sample in the replay buffer.
- **The policy.** Averaged over the same 25 network updates, the policy's
  cross-entropy on the minibatches fell from 2.183 in the first 50 training
  steps to 2.118 in the last 50, and was 2.173 on fresh games.
- **Held-out evaluation.** The Axis against the scripted balanced opponents on
  six seeds (1009, 1013, 1019, 1021, 1031 and 1033), searching 64 simulations to
  depth 16 without exploration noise, scored on average +51.0 (standard error
  5.8) with the untrained, nearly passive network; +9.3 (5.7) after the first
  night's 6 network updates; +16.8 (7.3) after its 13; +15.5 (6.4) after 5 more
  in the morning run; and +6.7 (6.1) after the morning run's 9.

## What this shows and does not show

It shows that the network's value on new games has not improved since about
05:00 on 20 November, and that within each network update the network fits the
games in its replay buffer, the latest 110 or so, about 3.3 times better than
the games it plays next. Each game's training samples share that game's final scores, so a
network can lower its error on them by learning which game a position comes from
instead of how positions lead to final scores. Against that overfitting,
AlphaGo's value network was trained on 30 million positions, each from a
different self-play game (Sutton and Barto, *Reinforcement Learning: An
Introduction*, 2nd edition, section 16.6.1, page 446), and AlphaGo Zero drew its
minibatches from all the positions of its latest 500,000 games, with
regularization (section 16.6.2, page 449).

It does not show that this gap is what keeps the network from improving: that
is inferred. No run has yet trained with fewer training samples from each game,
more games in the replay buffer or weight decay, which the code does not offer.
The policy's cross-entropy fell less within a network update than the value
loss, and its value on fresh games stayed near the minibatches', so the policy
shows less sign of the same overfitting. The held-out evaluations use six games
each, too few to show a change of a few points. Whether the network would
improve with more games of the same settings is not measured.
