# What Adam did in one real update — 9 November 2026

The [design document](../../design/README.md#82-the-gradient) explains a
training step's gradient and its Adam step with numbers from one real update:
the 700 steps that followed the first batch of the
[5 November sample run](training_sample_2026_11_05.md). This record says how
those numbers were obtained. The [evidence file](adam_steps_2026_11_09.json)
holds them, with the tracked number's gradient and Adam averages at all 700
steps.

## How it was made

**The update, run again.** The sources of commit `d64117d`, the commit of the
sample run, were extracted and built apart from the working tree. A learner was
built with `run._learner` from the run configuration stored in the run's
generation-0 export; its fresh networks equalled that export exactly. Its replay
buffer was set to the 1,611 samples stored in the run's checkpoint, in their
stored order, and `CampaignLearner.update()` ran: 700 steps of 32 samples, with
PyTorch 2.11 on one CPU thread.

**Instrumentation.** Each network's `optimizer.step()` was wrapped to read the
gradients before the step, the parameters before and after, and Adam's two
averages after it (`exp_avg` and `exp_avg_sq`). Nothing else changed.

**Check.** The three networks after the 700 steps equal generation 1 of the run
exactly, every number of every tensor. So the steps below are the run's own.

**Adam's settings** (`CampaignLearner._optimizer`): `torch.optim.Adam` with
learning rate 0.001 and PyTorch's defaults otherwise: averaging factors 0.9 and
0.999, $\epsilon = 10^{-8}$, no weight decay. One Adam per network.

## The first step

The Comintern network has 4,104,392 numbers. In the first step 221,675 of them
had a nonzero gradient: those of the learned layers and the rows of the
questions answered in the step's 32 samples, 1,087 zone questions among them.
Their gradients ranged from $4.3 \times 10^{-17}$ to 171 in size, with a median
of 0.0007.

- 211,741 of them moved by 0.001, to within 0.00001. No number moved more.
- The others had gradients below about $10^{-6}$. There $\epsilon = 10^{-8}$ is
  no longer small beside the gradient, and the step shrinks: the first number of
  the row of `unit_stat:axis:infantry:defender` had gradient
  $5.0 \times 10^{-8}$ and moved by 0.00083, as the formula gives:

  $$
  0.001 \times \frac{5.0 \times 10^{-8}}{5.0 \times 10^{-8} + 10^{-8}} \approx 0.00083
  $$

- Among the zone rows' first numbers, the largest gradient was that of
  `rail_to:land_manchuria_eastern`, 0.0133. It moved by 0.0010, as did the
  number with the largest gradient of all, 171, nearly 13,000 times larger.

This is what the formula predicts for a first step: both averages start at zero,
and after the correction the step is the learning rate times the gradient
divided by its own size.

## One number through the update

The tracked number is the Comintern network's value-head bias for the
Comintern's own value (`value_head.2.bias[2]`): it is added to every Comintern
score the network predicts. The network predicts scores divided by 100, so a
change of 0.001 in the bias moves every predicted Comintern score by 0.1 point.
The value loss is
the mean of 96 squared errors, 32 samples by three values, so this bias's
gradient is 2/96 times the sum of the 32 Comintern errors, and the mean error is
1.5 times the gradient. In the first step the gradient was 0.728: the fresh
network predicted the Comintern's final scores on that step's samples 109.3
points too high on average.

| Step | Gradient | Average gradient, corrected | Typical size, corrected | Change |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.728 | 0.728 | 0.728 | −0.001000 |
| 2 | 0.322 | 0.514 | 0.563 | −0.000914 |
| 3 | 0.099 | 0.361 | 0.463 | −0.000780 |
| 4 | −0.004 | 0.255 | 0.401 | −0.000635 |
| 5 | −0.066 | 0.176 | 0.360 | −0.000490 |
| 10 | 0.027 | 0.046 | 0.257 | −0.000178 |
| 50 | −0.00006 | 0.003 | 0.115 | −0.000026 |
| 700 | −0.016 | −0.0013 | 0.030 | +0.000044 |

Each change equals −0.001 times the corrected average divided by the corrected
typical size, to within $4 \times 10^{-9}$, at all 700 steps. The gradient was negative in
356 of the 700 steps. The bias fell at every step until step 39 and rose for the
first time at step 40; over the update it moved from 0.0908 to 0.0829, by 0.78
points of predicted score.

**The value loss.** The Comintern network's value loss on each step's samples
was 0.618 in the first step, then 0.095, 0.015, 0.0065 and 0.012, and 0.0005 to
0.0007 in the last five: a root-mean-square error of 79 points at first and
about 2.4 at the end. These are samples the network was trained on, about 14
draws each, so the last figure measures fit, not prediction of new games.

## What this does and does not show

- **Measured:** the steps above, for this run's first update.
- **Computed from the recorded gradients:** at step 700 the first step's
  gradient still made up 60% of the bias's average squared gradient, and the
  first three steps 73%, because each step keeps 99.9% of that average. Without
  them its typical size would have been 0.015 instead of 0.030, so the large
  gradients of a run's first steps halved this number's steps for the rest of
  the update.
- **Inferred:** the same continues into the next updates, since each network
  keeps its Adam, with its averages, for the whole run.
- **Not shown:** whether 0.001 suits this game; no other learning rate has been
  tried.
