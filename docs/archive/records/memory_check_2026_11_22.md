# The memory-checked first part of the training run of 22 November 2026 — 22 November 2026

The training run started on 22 November 2026
(`studies/campaign/runs/training-2026-11-22`, commit `3153079`) plays its first
part, `1-memory-checked`, with its game process on an engine built with
AddressSanitizer, which stops the process at the first write to freed memory,
second free or out-of-bounds access and names the code that made it. The part
looks for the defect behind the six game process crashes of the training run of
19 to 21 November 2026 (`studies/campaign/runs/training-2026-11-19`, Q-012),
while it trains the network that the run's full-speed part is to start from.
This record counts what the part had checked by its 134th network update, at
17:35 on 22 November, and how likely a report would have been by then. The
[evidence file](memory_check_2026_11_22.json) holds the settings and the
counts, read from the run folders' own files.

## Setup

- **The checked engine.** The sources of commit `3153079` built with
  AddressSanitizer at `-O2`, with libc++'s fast hardening and the SlotMap check
  (`GWRL_CHECK_SLOT_MAPS` in `include/game/slot_map.hpp`), but without the
  UndefinedBehaviorSanitizer and the debug hardening of the
  [memory check of 21 and 22 November](memory_check_2026_11_21.md), which was
  built at `-O1`. AddressSanitizer keeps freed memory unusable until 1 GB of later
  frees has pushed it out. Only the game process runs this engine; the training
  process and the inference server run the ordinary build of the same commit on
  the Mac's GPU.
- **Layout.** One game process of 16 games, within the 8 CPU cores and 16 GB
  that the owner gave to looking for the defect on 21 November.
- **Learning settings.** A fresh network of 256×8, one network for the three
  alliances. Choice D of Q-016: a decision kept as a training sample is searched
  with 256 simulations, any other with 16, and moves are drawn from the visit
  shares in game round 1 only. 1% of each game's decisions kept, a replay buffer
  of 25,000 training samples, 33 training steps per network update, self-play
  that never stops and the compiled layers.

## Numbers

From its start at 11:59:47 to its 134th network update at 17:35, 5.6 hours of
play, the part played 1,513,584 decisions and 2,144 complete games, and the
inference server answered 20,727,976 network evaluations for it: 13.7 for each
decision, and 270,000 decisions and 3.7 million network evaluations an hour.
Its CPU cores, counted each minute, had a median of 7.6, more than 8 in 16% of
the minutes and never more than 9; its memory had a median of 8.1 GB and a peak
of 9.1 GB. AddressSanitizer wrote no report, the game process started at 11:59:51
was never replaced, and no move failed.

The table compares the search work of the three runs. A run's network
evaluations count the states its searches asked the network about.

| Run | Decisions | Network evaluations | Network evaluations per decision | Crashes or reports |
| --- | ---: | ---: | ---: | --- |
| The training run of 19 to 21 November | 14,224,222 | about 768 million | 54.0 | 6 crashes |
| The memory check of 21 and 22 November | 1,276,928 | 66.4 million | 52.7 | no report |
| This part, to its 134th network update | 1,513,584 | 20.7 million | 13.7 | no report |

The inference server's count of network evaluations starts again each time the
program starts. The 54.0 network evaluations per decision of the training run
of 19 to 21 November were counted over 11.9 million of its decisions, those
between two network updates of the same start, and its total is its decisions
times that rate. The memory check's count is the one at its last network update
before its pause plus the one at its last before its stop, over 1,260,701 of
its decisions.

Two more numbers serve the comparisons below. The training run of 19 to 21
November, on the ordinary engine, played about 400,000 decisions an hour over
its 35.5 hours of play ([record](memory_check_2026_11_21.md)), so about 21.6
million network evaluations an hour, 5.8 times this part's. In the test script
of 21 November, side by side, the engine built with ThreadSanitizer played 1.54
decisions a thread-second and that day's engine built with AddressSanitizer
3.27 ([record](crash_diagnosis_2026_11_21.md), its evidence file).

## What this shows and does not show

It shows no write to freed memory, second free or out-of-bounds access on the
paths that 1.5 million decisions of training play under choice D reached, with
the network choosing the moves and the inference server answering, as in
training.

It does not show that the defect is gone. All six crashes came while the search
freed the game copies that its tree's nodes hold (`Node` in `src/search.cpp`).
The search makes a game copy for each node it adds and asks the network about
nearly every node it adds, so its work on game copies grows with its network
evaluations, not with its decisions (inferred). Choice D searches 99 of every
100 decisions with 16 simulations instead of 64, so a decision of this part
needs a quarter of the network evaluations of a decision of the training run of
19 to 21 November. That run crashed once in about 128 million network
evaluations. If AddressSanitizer caught the defect as often per network evaluation
as that run crashed, the two memory-checked runs would have reported it by now
with the probability below, all counts in millions of network evaluations:

$$
1 - e^{-(66.4 + 20.7)/128} \approx 0.49
$$

Counted by decisions instead, it would be 0.69, which overstates this part's
search work. At this part's pace, 3.7 million network evaluations an hour, the
probability would reach 0.75 after 24 more hours of play, 0.87 after 48 and
0.94 after 72.

AddressSanitizer may also see the defect less often than training crashed: the part
runs one process of 16 game threads instead of six of 42, on a much slower
engine, so the threads' timing differs, and a use of freed memory after more
than 1 GB of later frees falls outside the quarantine. If the defect is one
AddressSanitizer cannot see, no length of play finds it.

How to go on looking was put to the owner on 22 November 2026 as Q-018.
