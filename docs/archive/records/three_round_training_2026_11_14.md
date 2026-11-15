# Does self-play learn three-round games? — 14 November 2026

On the night of 14 November the Windows PC trained fresh networks on 792
three-round games. Afterwards the first and the last networks each played every
alliance against the scripted opponents, on 24 held-out seeds. The value heads
learned each alliance's average final score. Play changed a great deal but got no
stronger than the scripted policy. The trained Allies beat the untrained ones but
stayed well below the scripted Allies. The trained Axis scored below the untrained
one, which, with the noise off, ends almost every phase at once: over three rounds
a Japan that does nothing scores best. The
[evidence file](three_round_training_2026_11_14.json) holds the exact values, for
every batch and every seed.

## How it was run

- **Code and machine:** commit `ce4b3c4`, with the windows profile: an Intel
  i7-9700K with 8 cores and 16 GB, and an NVIDIA RTX 3060 Ti. Six game processes
  ran four games each, and the coordinator and training used CUDA, with
  PyTorch 2.14.
- **Networks:** fresh 64×2 networks on the input layout
  `campaign-zone-v1-ed3184ce805f1af5`. Commit `bce7a4c` has since replaced that
  layout, so these networks no longer load.
- **Training settings:** three-round games, 64 simulations, depth 16. A quarter of
  each game's decisions were kept as samples. Each update ran 675 steps of 32
  samples, from a replay buffer of 8,000 samples, at learning rate 0.001, with
  seed 1936.
- **Time limits:** the supervisor started at 22:51 and started no new batch after
  07:00.

```
python tools/supervise_campaign_training.py --profile windows --control-dir CONTROL --run-dir RUN --seconds 32400 -- --calendar-rounds 3 --complete-episodes --batches 1000 --simulations 64 --max-depth 16 --hidden-dim 64 --message-layers 2 --batch-size 32 --epochs 675 --replay-capacity 8000 --sample-fraction 0.25 --transitions-per-batch 20000 --no-new-batch-after TIMESTAMP
```

Evaluation played one alliance at a time on seeds `7100001` to `7100024`; the
scripted balanced policy played the other two. The networks ran on the CPU, with a
64-simulation search, depth 16 and the noise off. Each alliance was played three
ways: by generation 0 (*first*), by generation 33 (*final*) and by the scripted
policy itself (*script*). Comparisons pair the games of each seed.

```
python -m studies.campaign.run evaluate --checkpoint RUN/models/generation-000033.pt --target axis --seeds 7100001,...,7100024 --simulations 64 --max-depth 16 --max-transitions 5000 --neural-device cpu --output final-axis.json
```

For *script*, the same command adds `--target-script balanced`.

## Training

All 33 batches finished, with no restart: 792 games and 390,483 decisions. They
took 8.0 hours of play and 19 minutes of updates. While playing, the run made
48,551 decisions an hour and kept 12,105 new samples an hour.

| | Batch 0 | Batches 29 to 32 |
| --- | ---: | ---: |
| Decisions per game | 325 | 511 |
| Axis decisions per game | 208 | 335 |
| Land battles per game | 14.9 | 23.1 |
| Self-play score, Axis | +32.0 | +35.2 |
| Self-play score, Allies | −46.9 | −50.9 |
| Self-play score, Comintern | −87.9 | −84.7 |

- **The networks moved more as they trained.** From batch 3 on, games ran to
  about 500 decisions, so a batch took about 15 minutes instead of 10.
- **Samples were drawn less often than intended.** Each update draws
  675 × 32 = 21,600 times. Longer games kept about 2,950 samples per batch, so
  once the buffer was full each sample was drawn about 7 times during its stay,
  not the 12 intended
  ([how the count works](../../design/README.md#87-how-often-a-sample-is-drawn)).
- **The value loss** fell from about 0.017 to 0.001 within the first update.
  After that, each update began at 0.0017 to 0.0027 in batches 1 to 3, and at
  about 0.0045 in the last batches. Each update lowered it by about half: by
  28% to 72%.
- **The policy losses** showed no clear trend across updates: Axis 2.2 to 2.4,
  Allies 1.8 to 2.5, Comintern 0.65 to 0.95.
- **The coordinator** answered 10.1 positions per network pass on average, at
  7.6 ms per pass, including laying them out. Answering took 55% of the play time,
  and it waited for requests only 5.6% of the time.

## Held-out evaluation

All 216 games reached the end of round three.

| Alliance | Score, first | Score, final | Score, script | Decisions per game: first, final, script |
| --- | ---: | ---: | ---: | ---: |
| Axis | +41.2 | +28.3 | +30.7 | 23, 404, 338 |
| Allies | −56.8 | −51.4 | −38.4 | 29, 80, 139 |
| Comintern | −86.3 | −84.9 | −87.4 | 40, 90, 81 |

Paired differences of score: mean ± standard error over the 24 seeds, then in how
many seeds the first-named policy scored higher.

| Alliance | Final minus first | Final minus script | First minus script |
| --- | --- | --- | --- |
| Axis | −12.9 ± 2.2, 1 seed | −2.4 ± 2.6, 9 seeds | +10.5 ± 2.3, 19 seeds |
| Allies | +5.4 ± 2.2, 15 seeds | −13.0 ± 2.6, 3 seeds | −18.4 ± 2.1, 0 seeds |
| Comintern | +1.4 ± 1.6, 14 seeds | +2.4 ± 1.4, 17 seeds | +1.0 ± 1.3, 12 seeds |

**Generation 0 is nearly passive with the noise off.** Played that way, it ended
almost every phase at once. In self-play the search adds noise and draws its move
from the visit shares, and there the same networks made 208 Axis decisions a game
in batch 0, against 23 here. So *first* is a player that does almost nothing, not a
random one.

**Doing nothing is the best Axis play measured over three rounds.** The nearly
passive Axis kept its units and its money:

- Japan lost 1.8 units a game, against 13.3 for the trained Axis and 18.5 for the
  scripted one.
- It ended with a treasury of 59.8, against 17.5 and 19.2.
- The warlords stayed neutral, holding 4.3 zones a game. So the KMT held 10.7
  zones instead of 15.1 and 15.8, and the Allies' wealth was 24.1 instead of 29.6
  and 28.3.

This repeats on 24 seeds what the
[decision review](decision_review_2026_10_31.md#the-objective-rewards-a-passive-japan)
found on 4.

**Values.** The evaluation compares one prediction per game with the game's score:
the search's value at the alliance's first searched decision.

| Alliance | Predicted, first | Predicted, final | Final's last self-play batches | Mean squared error, first | Mean squared error, final | Spread of final's scores |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Axis | −35.0 | +38.6 | +35.2 | 5,903 | 176 | 8.2 |
| Allies | −6.3 | −43.8 | −50.9 | 2,629 | 227 | 13.2 |
| Comintern | +12.7 | −86.5 | −84.7 | 9,831 | 22 | 4.5 |

The spread is the standard deviation of the scores across seeds. Most of what
remains of the final networks' error is that spread, plus the gap between
self-play and the scripted opponents. For example, the trained Axis predicted
+38.6 and scored +28.3.

## What this does and does not show

- **Measured:** 33 updates and 216 held-out games, at the settings above, on one
  PC.
- **The value heads learned the average final score of self-play.** The
  evaluation makes one prediction per game, at nearly the same opening position,
  so it cannot show whether they tell a better position from a worse one.
- **The policies changed how much each alliance does, but none played clearly
  better than the scripted policy in its place.** The Comintern's +2.4 ± 1.4 is
  the only margin in the trained network's favour, and a weak one. The Allies
  improved on the passive start, by 5.4 ± 2.2, and stayed 13.0 ± 2.6 below the
  scripted Allies.
- **Training moved the Axis away from the play that scores best here.** Its
  self-play decisions rose from 208 a game to about 335. Why is not measured. The
  design document's open questions on the objective and on flat search targets
  are candidates.
- **Not shown:**
  - whether more games, eleven-round games or another network size would do
    better;
  - whether the final networks beat the first in self-play itself, against
    learning opponents.
- **Inferred, about speed:** the coordinator waited for requests only 5.6% of the
  time, so it, not the game processes, probably set the pace of self-play on this
  PC. A matched batch with the coordinator on the CPU, or with more games per
  pass, would tell.
