# The faster engine in training batches — 16 November 2026

On 16 November the engine came to hold its names as numbers
([names held as numbers](../../engine/names.md)), to keep units and facilities
in slot maps, and to digest a binary writing of the position for its planning
key ([record](planning_key_2026_11_16.md)). In random and searched games it
played the same and ran fewer instructions. These batches measure what that
does to training: decisions per hour rose 26%, and the coordinator, not the
engine, now sets the pace. The [evidence file](engine_speed_in_training_2026_11_16.json)
holds every value.

## Setup

Two matched pairs of the Mac profile's batch: 6 game processes of 4 games, 24
eleven-round games, 64 simulations, the 64×2 network evaluated on the CPU by
one coordinator, seed 20261104, run by `tools/supervise_campaign_training.py`
with the command line in the evidence file. The engine before that work
(`9519ea7`) and after it (`c90f85b`) alternated, before first; the training code
was the same in both. `tools/log_process_load.py` measured each batch's
processes and the Mac's other work in half-minute windows. The coordinator's
busy time is its time answering rounds of requests: reading their arrays,
laying the positions out, the network pass and the outputs, without receiving
the requests or sending the replies (`forward_seconds` in
`studies/campaign/shared_evaluator.py`); it was busy for that share of its busy
and waiting time.

## The batches

| Batch, in the order run | Before 1 | After 1 | Before 2 | After 2 |
| --- | ---: | ---: | ---: | ---: |
| Decisions per hour while playing | 229,711 | 305,994 | 248,201 | 296,642 |
| Games per hour while playing | 214.3 | 291.6 | 230.1 | 284.4 |
| Game processes' CPU per decision | 117.3 ms | 65.0 ms | 110.2 ms | 65.5 ms |
| Game processes' instructions per decision | 1,085 M | 647 M | 1,052 M | 657 M |
| Game processes' CPU on performance cores | 76% | 90% | 79% | 88% |
| Coordinator busy | 91% | 96% | 92% | 95% |
| Positions per round | 4.81 | 8.25 | 5.47 | 7.62 |
| Coordinator's busy time per round | 1.26 ms | 1.71 ms | 1.32 ms | 1.60 ms |
| Coordinator's busy time per evaluation | 262 µs | 207 µs | 242 µs | 211 µs |
| Coordinator's instructions per decision | 183 M | 161 M | 177 M | 164 M |
| Training's load, cores, mean of half-minute windows | 8.6 | 6.8 | 8.8 | 6.8 |
| Other work, cores, median window | 2.3 | 2.9 | 3.0 | 2.1 |
| Peak memory, sampled | 4.5 GB | 4.3 GB | 4.9 GB | 4.8 GB |
| Failed games | 0 | 0 | 0 | 0 |

On average:

- **Decisions per hour while playing** rose 26.1%, from 238,956 to 301,318,
  and games per hour 29.6%, from 222 to 288. The two runs of each version
  differ by 8% before and 3% after, much less than the gain.
- **The game processes** used 42.7% less CPU per decision, from 113.8 ms to
  65.2 ms, and ran 39.0% fewer instructions, from 1,069 M to 652 M. An
  evaluation, about 51 to a decision, now costs them about 1.3 ms of CPU
  instead of about 2.2 ms.
- **The coordinator** was busy 95.6% of the time instead of 91.4%. With the
  game threads quicker to ask, more positions wait for each round, 7.9 instead
  of 5.1, so a round costs it less per position: 209 µs of busy time per
  evaluation instead of 252, and 10% fewer instructions per decision.
- **The training** kept about 6.8 cores busy instead of 8.7.

## What limits training now

The coordinator, busy 96% of the time, sets the pace; the game processes kept
about 6.8 cores busy, not the 9 of the allowance. The engine's saving reached
the coordinator only through its rounds: game threads that asked sooner left
more positions waiting for each round, and a bigger round cost the coordinator
less per position. A straight line through the four batches' rounds gives about
0.62 ms of busy time a round plus 0.13 ms a position, within 0.011 ms of each
batch. The coordinator's instructions follow the same pattern, about 4.8 M a
round plus 2.6 M a position, so a round's fixed cost is work it does, not only
time lost to busier cores. The before batches differ from the after ones in
more than their rounds, with about 2 more cores busy around the coordinator, so
the line is an estimate.

The 16 November study of self-play's limits had fitted 0.26 ms a round plus
0.23 ms a position on a profiled batch with rounds of 4.4, and worked out from
it a ceiling of about 301,000 decisions an hour however large the rounds
([record](self_play_limits_2026_11_16.md#the-coordinator)). These batches
reached that rate with rounds of about 8 while the coordinator still waited 4%
of the time, so that fit overstates what bigger rounds cost. It divided the
time of every step but the pass by the requests, as if all of it grew with the
positions, and gives 2.16 ms for a round of 8.25 positions where these batches
measured 1.71 ms; receiving the requests and sending the replies, which these
batches leave out, took about 6% of the coordinator's time in that profile.

By the line above, rounds of all 24 game threads would answer about 31% more
positions a second than rounds of 8.25. A cheaper engine fills rounds further
only as its game threads ask sooner, so in this layout it buys decisions per
hour only through that; the rest of its saving leaves cores idle, about 2 of
the 9. More games in flight would also fill rounds, and the coordinator's own
cost, each round's fixed part and the network's arithmetic, could fall.

## What this does and does not show

- **Measured:** decisions and games per hour while playing, CPU and
  instructions per decision, the coordinator's load and the training's cores, in
  two matched pairs of batches with the Mac's other work at 2 to 3 cores.
- **Inferred:** the coordinator's cost per round as a line through four
  batches that differ in more than their rounds, and what rounds of 24 would
  cost, beyond the measured 4.8 to 8.3 positions.
- **Not measured:** whether a seventh game process, now that the six leave
  cores idle, would raise decisions per hour by filling rounds further; how the
  CPU per decision holds when every core is busy; anything about learning. The
  engine plays the same games as before
  ([record](planning_key_2026_11_16.md#the-same-play)), so learning is unchanged
  for the same games.
