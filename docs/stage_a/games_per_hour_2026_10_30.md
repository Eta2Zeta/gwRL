# Games per hour on the new code — 30 October 2026

This report measures how many complete eleven-round self-play games the Mac
plays per hour now that the one-move skip and the nine CPU savings are in. The
network and search are the same size as in the earlier runs. Only the new code
was run, in the near-best setup found for each of the two ways of playing. The
[evidence JSON](games_per_hour_2026_10_30.json) records settings, provenance and
results; raw outputs remain under `studies/campaign/runs/games-per-hour-2026-10-30/`.

Both setups now play about twice as many games per hour: **32.6 on the CPU
alone, up from 14.6, and 48.3 with the GPU, up from 24.2.** The all-CPU setup now
beats the old GPU setup.

## Results

All four columns use hidden size 64, two message layers, 16,384 token buckets,
64 simulations, depth cap 16, eleven rounds, one thread per game and no learning
updates. The earlier columns come from the
[shared GPU report](landing_plan_shared_gpu_2026_10_29.md).

| Eleven-round games | All CPU, 28 Oct | All CPU, now | CPU + GPU, 29 Oct | CPU + GPU, now |
| --- | ---: | ---: | ---: | ---: |
| Processes | 10, one game each | 10, one game each | 8 with four games each, and a coordinator | 8 with four games each, and a coordinator |
| Completed / failed | 10 / 0 | 10 / 0 | 32 / 0 | 32 / 0 |
| Batch wall time | 2,847 s | 1,333 s | 4,958 s | 2,484 s |
| Complete games per hour, one batch | 12.6 | 27.0 | 23.2 | 46.4 |
| **Games per hour, long run** | **14.6** | **32.6** | **24.2** | **48.3** |
| Seconds per game, mean | 2,461 | 1,105 | 4,562 | 2,266 |
| Evaluations per game, mean | 84,928 | 72,827 | 84,123 | 69,812 |
| Evaluations per second, long run | 345 | 659 | 566 | 937 |
| Peak charged memory | 9.14 GB | 11.7 GB | 10.0 GB | 10.8 GB |

A batch waits for its slowest game, so the long-run rate is the better guide to
a long campaign. The two columns of each setup use the same method. All-CPU
long-run rates are processes over mean game length. GPU rates are evaluations
per second while every game plays, over evaluations per game; by the all-CPU
method the GPU now gives 50.8.

## Choosing the setups

All-CPU runs report only complete games, so both candidates played them. Ten
processes gave 32.6 games per hour and eight gave 29.2, so ten is the choice. Ten
is the most the benchmark's 12-core accounting allows.

Five-minute GPU probes covered about the first tenth of each game:

| Processes × games | Games at once | Evaluations per second | Positions per GPU call | Milliseconds per GPU call |
| --- | ---: | ---: | ---: | ---: |
| 8 × 4 | 32 | 802 | 9.9 | 11.6 |
| 10 × 4 | 40 | 768 | 11.5 | 13.7 |
| 8 × 6 | 48 | 707 | 14.8 | 19.6 |
| 10 × 6 | 60 | 596 | 18.3 | 27.8 |
| 8 × 8 | 64 | 605 | 18.6 | 28.3 |

More games made every GPU call disproportionately slower, so the rate fell.
Later rounds spread their positions across more models and make smaller calls,
so the opening alone could not settle it, and the two best candidates by games
at once played complete games:

| Processes × games | Games per hour, one batch | Games per hour, long run | Peak charged memory |
| --- | ---: | ---: | ---: |
| 8 × 4 | 46.4 | 48.3 | 10.8 GB |
| 8 × 6 | 45.4 | 47.2 | 14.7 GB |

The two are within 2%, about as close as one run can tell apart. Eight processes
of four games is the choice because it uses less memory and each game takes 38
minutes instead of 59.

## What limits each setup now

The GPU setup is limited by the coordinator, not the game processes. It spent 94%
of the run in model calls, at about 1.05 ms per position in both complete runs,
which caps it near 950 evaluations per second however many games play. The games
spent 83% of their search time waiting for it, and the game processes used only
4.3 cores, with the coordinator using 0.7, out of the 12 allowed. Further CPU
savings in the game processes would therefore add little to this setup. Fewer
evaluations or cheaper GPU calls would.

The all-CPU setup is still limited by the cores themselves, with network math on
each process.

## What changed since the earlier runs

The one-move skip removes about 18% of evaluations, which the table shows as
about 70,000 evaluations per game instead of about 84,000. The nine savings cut
the game processes' CPU; at eight processes of four games they fell from 8.8
cores in the earlier five-minute probe to 4.3 in this one, while evaluating 26%
faster. These runs also use the Mac's default memory allocator. Agent sessions
otherwise set `MallocNanoZone=0`, which the earlier runs inherited.

The three effects were not measured one at a time. The only hint at the
allocator's share is that eight all-CPU games took 1,314 s with `MallocNanoZone=0`
and 1,191 s with the default allocator, about 9% less, in unmatched runs.

## Limits of these numbers

- The comparison across dates is not controlled. The earlier all-CPU run used
  PyTorch 2.11 and an engine from before the landing rule; the earlier GPU run
  used commit b89e86d, before later rule fixes. Both earlier evaluations-per-game
  figures include one-move searches.
- Each rate comes from one run of 10 or 32 games, with no repeats.
- The machine was in ordinary use, not quiet. The ten-process run shared it with
  review agents' single-core experiments, so its figure may be slightly low. The
  8 × 6 run saw a five-minute load spike after its all-games-playing window.
- The all-CPU runs used commit 3065230 and the GPU runs 61138ba. Those differ by
  a history check and an open-file limit, neither of which should change speed.
- These runs measure self-play only: no learning updates, and nothing about
  playing strength.

## Checks

Eight complete all-CPU games with each position evaluated alone came out
identical to the one-move skip run in trace, final state and random-number
digests, decisions, transitions and returns. That holds for one-at-a-time
evaluation; with shared GPU batches, positions can differ in the last digits of
their outputs, so the GPU games are a rate measurement, not the same games.

At 61138ba, all 26 C++ test programs pass. The Python suite ran 624 tests with 4
skipped and one error, the guardian test that times out under suite load, which
passes alone. Three read-only reviews of the combined change ran fuzz, sanitizer,
race and lockstep checks and found no wrong game result. They confirmed two
smaller problems, both fixed: a crash from the open-file limit at 8 × 6 and above
when started from a normal Terminal, and a history check that a rule rewriting
history could slip past on a search copy, which no current rule does.
