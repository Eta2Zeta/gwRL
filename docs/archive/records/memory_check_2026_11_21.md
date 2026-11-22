# A training run with memory-checked game processes — 21 and 22 November 2026

After six game process crashes in the long training run, the owner stopped
training on 21 November 2026 to look for their cause (Q-012, choice A) and gave
the look 8 cores and 16 GB. This run played training games as the long run did,
but its game processes ran an engine built with AddressSanitizer, which stops a
process at its first bad memory access and names the code that made it. It
played for 21.2 hours and found nothing. The
[evidence file](memory_check_2026_11_21.json) holds the settings, every attempt's
layout, cores and memory, and the counts behind the numbers below. Its files are
in `studies/campaign/runs/memory-check-2026-11-21`.

## Setup

- **Code.** Commit `c876716`: the engine, rules and search of the six crashes,
  and `GWRL_GAME_PYTHON`, which names the interpreter the game processes start
  with. The training process and the inference server ran the ordinary build on
  the Mac's GPU; AddressSanitizer in the inference server's process stalls
  PyTorch's work on the GPU.
- **The checked engine.** The same sources built with AddressSanitizer and
  UndefinedBehaviorSanitizer at `-O1`, with libc++'s debug hardening and the
  SlotMap check (`GWRL_CHECK_SLOT_MAPS` in `include/game/slot_map.hpp`). The
  checker stopped a game process at its first error. Its quarantine kept freed
  memory unusable until 1 GB of later frees had pushed it out, about the last
  17 seconds of this run's frees (inferred from the 2 GB attempt, which filled
  in about 35 seconds), so a use of freed memory or a second free within that
  time would be caught.
- **Learning settings.** The long run's network of 256×8, one network for the
  three alliances, 64 simulations to depth 16 at every decision, moves drawn
  from the visit shares, 1% of each game's decisions kept, a replay buffer of
  8,000 training samples, 525 training steps per network update, self-play that
  never stops and the compiled layers. It started from the long run's newest
  network, generation 10 of choice B, after 38 network updates.
- **Layout.** One game process of 14 games. Under the checker the cores in use
  grew with the number of games in play, so the layout was chosen by the cores
  and memory it used, in the attempts below; each but the last was stopped by
  hand after a few minutes.

| Attempt | Game processes × games | Quarantine | Minutes | Median cores | Peak memory |
| --- | --- | ---: | ---: | ---: | ---: |
| `run` | 2 × 42 | 256 MB | 4 | 12.6 | 10.5 GB |
| `run-one-process` | 1 × 42 | 256 MB | 3 | 12.7 | 6.6 GB |
| `run-seven-games` | 1 × 7 | 256 MB | 2 | 4.8 | 3.9 GB |
| `run-fourteen-games` | 1 × 14 | 256 MB | 9 | 7.8 | 4.7 GB |
| `run-large-quarantine` | 1 × 14 | 4 GB | 4 | 7.7 | 14.0 GB, rising |
| `run-quarantine-2gb` | 1 × 14 | 2 GB | 26 | 7.7 | 14.0 GB at the first network update |
| `run-quarantine-1gb` | 1 × 14 | 1 GB | 1,270 | 8.0 | 13.4 GB at a network update |

## Numbers

The run `run-quarantine-1gb` played from 13:56:53 on 21 November to 11:24:49 on
22 November, paused from 17:53:46 to 18:11:16 at the owner's request: 21.2 hours
of play. It counted 1,276,928 decisions, 866 complete games and 61 network
updates, about 60,000 decisions an hour; the pause lost 11,707 more decisions of
the games then in play, which were checked too. Its cores, counted each minute,
had a median of 8.0 after the pause and 7.7 before it; its memory a median of
8.9 GB after the pause and 7.9 GB before it, and a peak of 13.4 GB, during a
network update. Neither checker wrote a report, and neither libc++'s hardening
nor the SlotMap check fired.

## What this shows and does not show

It shows no write to freed memory, second free, out-of-bounds access, undefined
behaviour or stale SlotMap iterator on the paths that 1.28 million decisions of
training play reached, with the network choosing the moves and the inference
server answering, as in training.

It does not show that the defect is gone or where it is. The long run's five
parts counted 14,224,222 decisions and crashed six times, once in about 2.37
million decisions; the fifth part, which crashed after 3.6 minutes, counted
none. If the defect made an error this checker sees as often per decision as
the long run crashed, a run of 1.28 million decisions would have seen one with
the probability below, both counts in millions of decisions:

$$
1 - e^{-1.277/2.371} \approx 0.42
$$

The run also differed from training in ways that may make the defect rarer:
one process of 14 game threads instead of six of 42, and a much slower engine,
about 60,000 decisions an hour on about 8 cores against the long run's average
of about 400,000 over its 35.5 hours of play, so the threads' timing differs. A
use of freed memory more than about 17 seconds of frees later falls outside the
quarantine.

The run was stopped on 22 November 2026, to look on with a lighter checked
engine and 16 games in one game process, in the run that starts the training
of the newest rules and search (`studies/campaign/runs/training-2026-11-22`).
