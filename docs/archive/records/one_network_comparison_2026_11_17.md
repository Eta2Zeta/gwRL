# One network for the three alliances, against three — 17 November 2026

The owner answered [Q-009](../../questions.md#answered) by asking for one
network for all three alliances (`--networks one`) to be compared with a network
for each alliance (`--networks three`, the default) in matched runs, and kept if
it learns at least as well. On the night of 17 November the Mac trained fresh
64×2 networks both ways, 3.7 hours each, and then played each
run's last networks against the scripted opponents on 16 held-out seeds per
alliance. The [evidence file](one_network_comparison_2026_11_17.json) holds every
value.

- **Speed.** One network played 21.6% more decisions an hour than three networks
  with the Mac as quiet. Its forward pass took 20% less time per network
  evaluation, and its network updates 61% less time.
- **Values.** On each game before training on it, the two runs' value heads
  explained about the same share of the variance of the final scores after the
  first hour: 15.4% with one network, 13.1% with three.
- **Action probabilities.** The one network's action probabilities lay further
  from its searches' visit shares: a KL divergence of 0.273 against 0.252 after
  the first hour, most of the gap at Axis decisions.
- **Held-out evaluation.** The two runs' last networks scored alike against the
  scripted opponents. Neither played better than the scripted policy, and in
  both runs the trained Axis scored about 33 points below the untrained Axis,
  which does almost nothing, so these games cannot yet tell the better learner.

## How it was run

- **Code and machine.** Commit `9634d40`, run from a copy of that commit made
  before the night, with its compiled engine module, so that changes to the
  checkout during the night could not reach the runs. The Mac's Apple M4 Max,
  PyTorch 2.14.0, `MallocNanoZone` unset.
- **Profile.** The Mac profile of `tools/supervise_campaign_training.py`: six
  game processes of four games each, and the inference server on one CPU core
  in the main training process. Self-play never stops: after every 24 games that
  end, a network update runs beside the games
  ([the training loop](../../design/README.md#91-the-training-loop)).
- **Training settings.** Eleven-round games, 64 simulations, simulation depth
  up to 16, 64×2 networks, 5% of decisions kept as training samples, a replay
  buffer of 8,000 training samples, 525 training steps of minibatches of 32 per
  network update, seed 20261104 for both runs. Only `--networks` differed:

```
python tools/supervise_campaign_training.py --profile mac --working-directory RUNTIME --control-dir CONTROL --run-dir RUN --seconds 13350 --max-restarts 0 -- --calendar-rounds 11 --complete-episodes --batches 1000 --simulations 64 --max-depth 16 --hidden-dim 64 --message-layers 2 --batch-size 32 --epochs 525 --replay-capacity 8000 --sample-fraction 0.05 --transitions-per-batch 20000 --seed 20261104 --networks three
```

- **Schedule.** A driver script ran the runs one after the other and split the
  three-network run around the one-network run, so that both runs were centred
  on the same time of night, about 00:42, and a steady change in the Mac's other
  work through the night would weigh on both alike. Three networks ran from
  21:00 to 22:51, when the driver stopped the run and it saved a checkpoint;
  one network ran from 22:52 to 02:34; three networks resumed from the
  checkpoint and ran from 02:34 to 04:24. Each run had a budget of 13,350 seconds (`--seconds`); the supervisor
  charged 13,308 seconds to the three-network run and 13,312 to the one-network
  run. A run's *active time* below is the seconds its main training process ran,
  added over its parts: 3.69 hours with three networks and 3.70 with one.
- **Held-out evaluation.** Each run's networks after its last network update
  (generation 32 with three networks, generation 41 with one) and its fresh
  networks (generation 0) played each alliance in turn against the balanced
  scripted opponents, on seeds 3001 to 3016, which training never used: 64
  simulations, simulation depth up to 16, no exploration noise, one CPU thread
  for each process, at most 20,000 transitions a game. As a reference, the
  balanced scripted policy also played in each alliance's place on the same
  seeds. The Axis's 16 seeds were split over two processes; up to eight
  processes ran at a time.

```
python -m studies.campaign.run evaluate --checkpoint RUN/models/generation-000032.pt --target axis --seeds 3001,3002,3003,3004,3005,3006,3007,3008 --simulations 64 --max-depth 16 --max-transitions 20000 --output three-axis-first.json
```

For the scripted reference the same command adds `--target-script balanced`.

- **Analysis.** `tools/compare_training_runs.py`, added with this record, read
  the two runs' `progress.jsonl` and `manifest.json` and the evaluation bundles.
  `tools/log_process_load.py` sampled every process's CPU time every 5 seconds
  through the night, and summarized each part of the night with its `--from`
  and `--to`, also added with this record.

## Speed

| Part | Clock time | Active seconds | Network updates | Games | Decisions | Decisions per hour | Decisions per game |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Three networks, first part | 21:00 to 22:51 | 6,693 | 16 | 395 | 565,637 | 304,221 | 1,432 |
| One network | 22:52 to 02:34 | 13,307 | 41 | 997 | 1,460,330 | 395,060 | 1,465 |
| Three networks, resumed | 02:34 to 04:24 | 6,600 | 16 | 403 | 595,648 | 324,907 | 1,478 |

A game and its decisions count when the game ends, also after a part's last
network update. Over both parts the three networks played 314,496 decisions an
hour.

Where the processes' time went, from the CPU log and the inference server's
counters (`evaluator` in each network update's entry of `manifest.json`):

| Part | Main training process | Six game processes | The Mac's other work | Forward pass per network evaluation | Network evaluations per inference batch | Inference server waiting | Network update |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Three networks, first part | 1.06 cores | 5.44 cores | 1.48 cores | 198 µs | 10.6 | 1.6% | 36.6 s |
| One network | 1.03 cores | 6.66 cores | 0.52 cores | 154 µs | 9.7 | 1.9% | 13.7 s |
| Three networks, resumed | 1.06 cores | 5.47 cores | 0.49 cores | 187 µs | 10.8 | 1.5% | 34.3 s |

- **One network played 395,060 decisions an hour**: 21.6% more than the resumed
  three-network part, when the Mac's other work was as light (0.49 cores
  against 0.52), and 29.9% more than the first part, when the Mac's other work
  kept 1.48 cores busy. The searches were the same size: 53.9 and 53.2 network
  evaluations a decision.
- **The inference server set the pace in both runs.** It waited for inference
  requests less than 2% of the time. With one network, a forward pass took 154
  µs per network evaluation against 192 µs over both three-network parts, 20%
  less, as the replayed inference batches of the
  [record of 17 November](network_split_2026_11_17.md#inference-batches-on-one-core)
  had shown (17% to 19% less per forward pass). A network update took 13.7
  seconds against 34 to 37, since it trains one network instead of three, and
  while it runs beside the games the inference server answers about 29% fewer
  network evaluations a second
  ([record](self_play_never_stops_2026_11_17.md)). The game processes waited
  less for answers and kept 6.66 cores busy instead of 5.44 and 5.47.
- **The three-network run paid for its stop.** The games in play when the
  driver stopped it at 22:51 were abandoned, as a stop does, and the resumed
  part started new ones. Up to 24 games, about half played, would be about 1.5%
  of its decisions; this is an estimate, not measured.

## Learning, on each game before training on it

In self-play that never stops, each game that ends is scored by the networks
then serving self-play, before its training samples join the replay buffer
(`fresh_game_losses` in `studies/campaign/learning.py`). At each kept decision
it measures the value loss of [the loss](../../design/README.md#81-the-loss), the
mean over the three alliances of the squared difference between the network's
value and the final score, both divided by 100; and the KL divergence of the
network's action probabilities from the search's visit shares. These are losses
on games the networks have not trained on.

The two runs played different games, and how far a game's final scores can be
predicted differs between games. So beside each value loss the tables give the
variance of the final scores over the same kept decisions, each final score
divided by 100 as in the value loss, averaged over the three alliances. That
variance is the value loss of a network that always predicted the mean final
scores. The *explained variance*, one minus
the value loss divided by that variance, is the share of the spread the value
heads account for: 0 for the mean, 1 for exact values, and negative for values
worse than the mean.

| Active hours | Networks | Network updates | Games | Value loss | Variance of the final scores | Explained variance | KL divergence |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 to 1 | three | 8 | 192 | 0.0697 | 0.0148 | −370% | 0.281 |
| 0 to 1 | one | 11 | 264 | 0.0603 | 0.0281 | −115% | 0.285 |
| 1 to 2 | three | 9 | 216 | 0.0195 | 0.0210 | 6.8% | 0.255 |
| 1 to 2 | one | 11 | 264 | 0.0230 | 0.0265 | 13.4% | 0.276 |
| 2 to 3 | three | 9 | 216 | 0.0197 | 0.0233 | 15.5% | 0.251 |
| 2 to 3 | one | 11 | 264 | 0.0238 | 0.0270 | 12.1% | 0.271 |
| 3 to 3.7 | three | 6 | 144 | 0.0219 | 0.0261 | 16.4% | 0.250 |
| 3 to 3.7 | one | 8 | 192 | 0.0253 | 0.0321 | 21.2% | 0.271 |
| 1 to 3.7 | three | 24 | 576 | 0.0202 | 0.0233 | 13.1% | 0.252 |
| 1 to 3.7 | one | 30 | 720 | 0.0239 | 0.0282 | 15.4% | 0.273 |

The first hour holds the games that generation 0 scored: a fresh network gives
every state the same values, which missed by a value loss of 0.567 with three
networks and 0.501 with one, in the first network update's games.

After the first hour, by the alliance deciding at the kept decision:

| Alliance | Share of kept decisions, three networks | Share of kept decisions, one network | Explained variance, three | Explained variance, one | KL divergence, three | KL divergence, one | Visit shares' entropy, three | Visit shares' entropy, one |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Axis | 58% | 57% | 10.0% | 12.3% | 0.289 | 0.318 | 2.13 | 2.12 |
| Allies | 26% | 28% | 16.8% | 20.1% | 0.264 | 0.280 | 2.17 | 2.19 |
| Comintern | 16% | 15% | 17.5% | 15.8% | 0.094 | 0.097 | 0.60 | 0.56 |

- **The value heads did about equally well.** The value loss was higher with
  one network, 0.0239 against 0.0202 after the first hour, but so was the
  variance of its games' final scores, 0.0282 against 0.0233. Measured against
  that variance, one network explained 15.4% and three networks 13.1%, and hour
  by hour the two runs crossed. Why the one-network run's games ended with more
  varied final scores is not measured.
- **The one network's action probabilities fit its searches less well.** Its
  KL divergence was about 0.02 higher in every hour after the first: 0.273
  against 0.252, at Axis decisions 0.318 against 0.289, at Allies decisions
  0.280 against 0.264, and at Comintern decisions within 0.003. The visit
  shares' own entropy was about the same in both runs for each alliance, so the
  two runs' searches spread their visits alike; the gap is in the action
  probabilities, which lay further from where the one network's searches put
  their visits.
- **Both runs' KL divergence fell over the first eight to ten network
  updates**, from 0.30 with three networks and 0.32 with one in the second
  network update's games, and then stayed level, at about 0.25 and 0.27. The
  evidence file lists each network update's values.

## Held-out evaluation

All 240 games reached the end of the eleventh game round. The final score of the
alliance played, mean ± standard error over the 16 seeds, and that alliance's
decisions a game:

| Alliance | Three networks, generation 0 | One network, generation 0 | Three networks, generation 32 | One network, generation 41 | Scripted policy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Axis | +39.7 ± 3.4 | +42.2 ± 2.8 | +6.5 ± 2.4 | +8.3 ± 3.4 | +26.0 ± 5.6 |
| Allies | −75.3 ± 2.4 | −76.6 ± 2.3 | −79.9 ± 5.1 | −65.7 ± 6.0 | −31.6 ± 6.8 |
| Comintern | −98.9 ± 1.5 | −93.2 ± 2.0 | −95.7 ± 3.2 | −96.8 ± 2.8 | −97.3 ± 2.7 |
| Decisions a game: Axis, Allies, Comintern | 86, 80, 126 | 73, 80, 123 | 856, 345, 194 | 780, 303, 179 | 1,118, 492, 238 |

Paired differences of final score over the 16 seeds, mean ± standard error, and
in how many seeds the first-named scored higher:

| Alliance | One network minus three, last networks | Three networks, last minus generation 0 | One network, last minus generation 0 | Three networks' last minus the scripted policy | One network's last minus the scripted policy |
| --- | --- | --- | --- | --- | --- |
| Axis | +1.9 ± 3.5, 7 seeds | −33.2 ± 5.2, 2 seeds | −33.9 ± 4.1, 0 seeds | −19.5 ± 5.0, 4 seeds | −17.7 ± 5.8, 3 seeds |
| Allies | +14.2 ± 8.0, 11 seeds | −4.6 ± 4.2, 6 seeds | +10.9 ± 5.8, 10 seeds | −48.4 ± 7.9, 1 seed | −34.1 ± 8.3, 3 seeds |
| Comintern | −1.1 ± 4.7, 8 seeds | +3.2 ± 3.4, 9 seeds | −3.6 ± 3.2, 6 seeds | +1.6 ± 4.7, 7 seeds | +0.5 ± 3.5, 8 seeds |

- **The two runs' last networks scored alike**: one network minus three, Axis
  +1.9 ± 3.5 and Comintern −1.1 ± 4.7; the Allies' +14.2 ± 8.0 is less than
  two standard errors.
- **Neither run learned to play better than the scripted policy in 3.7 hours.**
  Their Allies scored 48.4 and 34.1 points below the scripted Allies; their
  Comintern scored about as the scripted Comintern, as the untrained networks
  did.
- **In both runs the trained Axis scored about 33 points below the untrained
  Axis.** With the noise off, an untrained network ends almost every phase at
  once, 86 and 73 decisions a game here, and keeps its units and its money; the
  trained Axis networks made 856 and 780 decisions a game and lost wealth doing
  so. The untrained Axis also scored above the scripted Axis, by 13.7 ± 7.5 and
  16.2 ± 6.1. The record of 14 November found the same over three game rounds
  ([record](three_round_training_2026_11_14.md#held-out-evaluation)); the final
  wealth gap rewards an Axis that does nothing
  ([the objective](../../design/README.md#is-the-final-wealth-gap-the-right-goal)).
- **Only the one-network run's Allies scored above their untrained start**, by
  10.9 ± 5.8, higher in 10 of 16 seeds; the three-network run's Allies did not,
  −4.6 ± 4.2. One run of each, with these spreads, makes this weak evidence.

## What this does and does not show

- **Measured:** one pair of runs, 3.7 hours of active time each, of 64×2
  networks on eleven-round games, with the Mac profile and its inference server
  on one CPU core; 16 held-out seeds per alliance.
- **One network is faster at this size on the Mac**, by about 22% in decisions
  an hour with the Mac equally quiet, because the inference server limits
  self-play here and one network makes both its forward passes and its network
  updates cheaper. On the Mac's GPU the replayed inference batches gave one
  network 15% to 38% less time
  ([record](network_split_2026_11_17.md#inference-batches-on-the-gpu)); training
  with the inference server on the GPU was not run.
- **The value heads learned equally well**, measured against the variance of
  the final scores of each run's own games.
- **The one network's action probabilities fit its searches 0.02 less well** in
  KL divergence, most at Axis decisions, 57% of the kept ones. The cause is not
  measured. One candidate is size: the one network holds the three alliances'
  strategies in the parameters of one 64×2 network, where three networks have
  three times as many. Another is chance: this is one run of each, and how much
  two runs of the same setting differ was not measured.
- **The held-out games could not decide it.** The two runs' last networks
  scored alike, but in 3.7 hours neither learned to beat the scripted policy,
  and in both runs the Axis learned to score less than the untrained Axis, which
  the objective rewards for doing almost nothing.
- **Not shown:** longer training; larger networks, where the one network's
  share of parameters per alliance may matter less; the two setups' networks
  playing against each other; training with the inference server on the GPU.
