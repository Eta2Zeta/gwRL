# Self-play that never stops, against alternating training iterations — 17 November 2026

On 17 November the owner chose self-play that never stops: the game threads play
one game after another, a network update runs beside them after every 24 games
that end, and every game takes up the new networks between two inference batches
([Q-007 and Q-008](../../questions.md#answered)). Two matched pairs of runs of
the Mac profile, four network updates each, compared it with alternating
training iterations. Self-play that never stops played 6.5% and 12.5% more
decisions per wall-clock hour between its first and fourth network updates. Its
network updates took about 35 to 48 seconds beside self-play, against about 22
alone, and while one ran, the inference server answered about 29% fewer
evaluations a second, because the trainer thread shares its process. The
[evidence file](self_play_never_stops_2026_11_17.json) holds every value.

## Setup

- **Runs.** `tools/supervise_campaign_training.py --profile mac`: 6 game
  processes of 4 games, eleven-round games, 64 simulations, depth 16, fresh 64×2
  networks on one CPU core, and the Mac training command's learning settings,
  525 training steps of minibatches of 32 per network update, a replay buffer of
  8,000 and 5% of decisions kept, seed 20261104, `--batches 4`. The continuous
  runs added `--continuous`. Each pair ran the alternating run first: pair 1 from
  12:32 to 13:23, pair 2 from 13:25 to 14:16. `tools/log_process_load.py`
  measured each run's processes and the Mac's other work, about 1.5 cores in all
  four (median of half-minute windows).
- **Code.** The same in all four runs (`runtime_source_sha256` in the evidence
  file), the code of this record's commit, except that pair 1's continuous run
  did not yet record the inference server's work during and between network
  updates.
- **Measure.** Decisions per wall-clock hour in steady play: the decisions of the
  games that ended between the first and the fourth network update, divided by
  the time between them, from each run's progress events. For an alternating run
  that is three whole training iterations, games and network updates. It leaves
  out the start, and in a continuous run the games still in play when the run
  stopped after its fourth network update, which are lost. Counting whole games
  makes it noisy: a game counts in full when it ends.

## Results

| Run | Steady decisions per hour | Network update | States per inference batch | Inference server busy | Cores the run kept busy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pair 1, alternating | 285,580 | 22 s | 8.3 | 96.8% | 6.4 |
| Pair 1, never stops | 304,176 | 37 to 48 s | 10.5 | 98.1% | 6.7 |
| Pair 2, alternating | 284,641 | 22 s | 8.7 | 95.2% | 6.3 |
| Pair 2, never stops | 320,269 | 34 to 37 s | 10.4 | 98.2% | 6.9 |

The network update times are each run's own: for an alternating run the mean
of its four, for a continuous run the range. The states per inference batch and
the inference server's busy share are from the last network update's report,
which for a continuous run covers the whole run.

- **Gain.** 6.5% in pair 1 and 12.5% in pair 2, about 9.5% on average.
- **No standstill.** In the alternating runs the cores the run kept busy fell to
  1.7 to 2.6 in the half-minute windows at each training iteration's end; in the
  continuous runs no window fell below 5.7, except pair 1's last, at 5.1.
- **Fuller inference batches.** About 10.5 states against 8.3 to 8.7, since no
  training iteration ends with a few games alone.
- **Every network update's games** were 24, and from the second on they were
  answered by two versions of the networks: games that began before a network
  update ended after it.

## The inference server while a network update runs

Pair 2's continuous run recorded the inference server's work during each network
update and between them:

| Network update | During it: seconds | Evaluations a second | Time per inference batch | Before it: seconds | Evaluations a second | Time per inference batch |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 34.0 | 3,524 | 2,903 µs | | | |
| 2 | 35.6 | 3,518 | 2,903 µs | 340.4 | 4,924 | 1,934 µs |
| 3 | 36.3 | 3,512 | 2,914 µs | 284.2 | 4,873 | 1,992 µs |
| 4 | 37.0 | 3,615 | 2,839 µs | 313.8 | 5,069 | 1,904 µs |

"Before it" runs from the previous network update's end to this one's start.
While a network update ran, the inference server answered about 29% fewer
evaluations a second, about 3,540 against 4,950, and took about 50% longer per
inference batch, though it was busy as much of the time, about 98%. The trainer
thread runs in the inference server's process, and the two take turns at
Python's lock. Network updates ran about a tenth of the time, so this cost about
3% of the decisions an hour (worked out); the same network update alone took
about 22 seconds.

## What this does and does not show

- **Measured:** decisions per wall-clock hour in steady play, in two matched
  pairs; the length of the network updates; the inference batches' size and the
  inference server's busy share; in pair 2, the inference server's rate during
  and between network updates; the cores the runs kept busy.
- **Worked out:** the 3% that the trainer thread's share of Python's lock costs,
  and so what a trainer process of its own would win, which is not tried.
- **Not measured:** whether self-play that never stops learns as well per
  decision, now that a game can be played by two versions of the networks and
  the networks change after every 24 games that end rather than after a
  training iteration's games; longer runs; and other network sizes or the GPU,
  where it does not run yet.
