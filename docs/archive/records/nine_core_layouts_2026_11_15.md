# Training within nine cores — 15 November 2026

On 15 November the owner lowered the core allowance from 12 cores to 9: the
Mac's M4 Max has 10 performance cores, and one stays free for everything else.
The supervisor counts one core for each game process, one for the coordinator
and one for itself, so 7 game processes of 4 games fit its count of 9. But a
game process keeps more than one core busy, because its four game threads can
compute at once, and 7 processes kept about 10 cores busy. One training batch
each of 7, 6 and 5 game processes measured the real load and the speed. The Mac
profile now runs 6 game processes of 4 games, which kept about 9 cores busy.
The [design document](../../design/README.md#92-running-training-on-the-mac)
describes the layout; the [evidence file](nine_core_layouts_2026_11_15.json)
holds the exact values, every half-minute window included.

## Setup

- **Code:** `main` at `5eda50f`, with the 9-core profile and supervisor
  allowance of this change. The engine and the trainer are the same as at
  `5eda50f`.
- **Batch:** the matched-batch command of the earlier speed records: one batch
  of eleven-round games, 64 simulations, depth 16, the 64×2 network evaluated on
  the CPU, 5% of decisions kept, 50 training steps, seed 20261104. The layouts
  differ only in `--episode-workers` and `--parallel-envs`, four games per
  process.
- **Load:** `ps` every 5 seconds, adding up the CPU time of the trainer, which
  is the coordinator while games play, and of its game processes, in
  half-minute windows from the first to the last sample with game processes.
  Other work on the Mac used a median of 2.6 to 3.4 cores meanwhile.

## Results

| Game processes | Games | Decisions an hour while playing | Games an hour | Real load, cores: mean, median window, highest | Coordinator busy | Positions per round | Peak memory |
| ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 7 | 28 | 229,000 | 218 | 9.0, 9.9, 11.1 | 90% | 5.6 | 4.7 GB |
| 6 | 24 | 192,000 | 173 | 8.2, 8.9, 10.3 | 90% | 4.9 | 4.0 GB |
| 5 | 20 | 201,000 | 184 | 8.5, 8.9, 10.2 | 88% | 3.9 | 3.6 GB |

For comparison, the 14 November batches of 8 game processes of 4 games, on code
without the later changes to the stored income and the network's input, played
about 252,200 decisions an hour while playing, kept about 9.9 cores busy, and
their coordinator was busy 85% of the time
([record](coordinator_one_pass_2026_11_14.md#matched-training-batches)).

## What this does and does not show

- **The supervisor's count is not the load.** Seven processes fit its count of
  9 cores but kept 9.5 to 11 cores busy in most windows. Six and five kept 8.6
  to 9.7 in most windows: fewer processes each use more CPU, because their
  threads wait less.
- **The coordinator limits all three layouts.** It was busy about 90% of the
  time. A round costs about the same whatever it holds, so fewer games in
  flight mean fewer positions a round.
- **Six against five is not settled.** One batch each, with matched batches of
  the same code differing by about 5.5% and other work differing by up to a
  core, cannot separate 192,000 from 201,000. Six processes were kept for the
  same load, 24 games a batch, as on the Windows PC, and more positions a round.
- **Against eight processes** the 9-core layout plays about a quarter fewer
  decisions an hour, on slightly different code and not in matched batches.
- **Learning** was not measured. The Mac command now takes 525 training steps
  an update instead of 700, so that each kept sample is drawn as often with 24
  games a batch as before with 32.
- **Section 9.3's worked-out table** for larger networks and searches now
  assumes 7 cores for games instead of 10; `capacity_with_7_cores_for_games` in
  the evidence file holds it. It is worked out from the 14 November
  measurements, not measured.
