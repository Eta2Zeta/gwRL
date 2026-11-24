# Self-play speed at 256×16 with KataGo's search — 24 November 2026

On 24 November 2026 the owner chose to train on the Mac at the sizes the design
document takes from AlphaZero and KataGo (Q-021), and asked first for "a few more
rounds of optimization of the runs so that things are going as fast as it gets
with limited compute we have here". This record measures self-play at those
sizes: a fresh 256×16 network on the Mac's GPU, 800 simulations with exploration
noise on a quarter of the decisions, which are kept as training samples, and 150
on the rest, and no depth limit
([design document](../../design/README.md#how-big-should-the-network-and-the-search-be)).
It measures the program as it was, then three changes: several simulations in
one inference request, overlapped inference batches on the GPU, and two cuts in
the engine's bookkeeping; then how many concurrent games suit them, and what a
network update's training does to the memory, before and after a fourth change,
which releases the GPU's caches during a network update. The
[evidence file](self_play_speed_256x16_2026_11_24.json) holds every number
below.

- **As the program was, the inference server limited self-play.** With 48
  concurrent games it answered 2,761 network evaluations a second, in inference
  batches of 24 states, about half the games, busy 95% of the time, while the
  game threads waited for it 81% of their time and the run kept about 4.5 CPU
  cores busy. At 217,000 network evaluations a game that is about 1,100 games a
  day, and 145,000 games take about 132 days.
- **Several simulations in one inference request and overlapped inference
  batches about doubled it.** With 8 simulations a request the same 48 games
  filled inference batches of about 125 states, and the inference server hands
  each one to the GPU while it sends the replies of the one before. It answered
  6,091 network evaluations a second over the part, between 4,700 and 7,500 in
  single minutes, busy about 73% of the time, and the run kept a median of 9.4
  CPU cores busy: the allowance of 9 now sets the pace. A network evaluation
  cost the game processes about the same CPU as before, 1.50 ms against 1.51 ms;
  they simply waited less.
- **Memory, not speed, stopped the second part.** The supervisor stopped it
  after 22 minutes, when the Mac's swap had grown by 4.2 GB since the start, to
  15.0 GB, with macOS's memory pressure at "warning"; the run's processes had
  peaked at 20.0 GB, against 17.0 GB in the first part, whose swap grew by
  1.1 GB. The
  Mac's other programs held about 24 GB of its 36 GB, and its swap was already
  at 9.3 GB before the first part.
- **The lighter bookkeeping played the same and costs less.** With menus no
  longer writing every listed action as canonical JSON, and search copies
  leaving the game's history behind but for its last event, 40 random
  eleven-round games played identically, 59,822 steps, with 8.2% fewer
  instructions in listing a state's legal actions (6.01 million a call against
  5.52) and the same in playing an action; and 4 eleven-round games searched as
  in training, with 64 simulations and a 64×2 network evaluated in the same
  process, played identically, 4,167 steps, with 3.6% fewer instructions in all
  (4,194 billion against 4,042) and 3.6% less CPU time.
- **24 concurrent games played as fast as 48, at a quarter of the memory, until
  a network update.** In the third part, with the lighter bookkeeping and 8
  simulations a request, 6 game processes of 4 games answered between 6,400 and
  7,300 network evaluations a second in each minute before the part's first
  network update, 6,717 on average, in inference batches of about 54 states,
  the inference server busy 94% of the time and a median of 7.7 CPU cores busy.
  A network evaluation cost the game processes 1.13 ms of CPU, a quarter less
  than with 48 games: their threads ran 91% of their time on performance cores,
  against 79%, and waited for a core 0.03 seconds a CPU second, against 0.33.
  The run's processes held 4.2 to 5.5 GB in all by their physical footprints,
  the training process 2.1 GB of it.
- **A network update's training on the GPU filled the memory.** The third
  part's network update after its first 24 finished games, 300 training steps
  of 256 training samples, took 117 seconds, 0.39 seconds a step, while the
  inference server answered 3,440 network evaluations a second, half its rate.
  Over it the training process's footprint grew from 2.1 GB to 15.4 GB, about
  45 MB a training step, and the supervisor stopped the part after 8.4 minutes
  when the Mac's swap had grown by 4.0 GB. While a network update trained
  beside self-play, nothing released the GPU's caches then (section 9.2 of the
  design document), and the GPU keeps a compiled graph for every shape of
  minibatch it meets
  (`studies/campaign/device_runtime.py`). Alone on the GPU
  (`benchmarks/train_memory.py`), 120 such training steps grew a process's
  footprint from 1.6 GB to 11.4 GB with the caches held, about 52 MB a step
  after the first 20, and kept it between 4.0 and 5.1 GB with the caches
  released every 20 steps, the steps as fast, 174 ms against 170.
- **30 concurrent games answered about an eighth more than 24.** With 6 game
  processes of 5 games and the code of the third part, the inference server
  answered 7,570 network evaluations a second on average in the minutes without
  a network update, between 6,900 and 8,200, and 7,335 over the part's last 14
  minutes with its two network updates, in inference batches of about 71
  states, busy 94% of the time. The run kept a median of 8.4 CPU cores busy, and
  a network evaluation cost the game processes 1.06 ms of CPU, their threads on
  performance cores 89% of their time. Each network update, 50 training steps of
  256 training samples after 30 finished games, took about 24 seconds, while
  the inference server answered about 2,300 network evaluations a second, under
  a third of its rate. The training process's footprint grew from 2.0 GB to
  4.3 GB over the first network update, reached 7.2 GB during the second and was
  back at 4.4 GB after it, once the GPU's caches were released again; the run's
  processes held about 7 GB in all, 11.5 GB at that peak.
- **Released every 20 training steps, the GPU's caches kept a long network
  update within memory.** With the layout and the network update of the third
  part, 300 training steps after 24 finished games, the inference server's
  thread released the GPU's caches every 20 training steps while the training
  thread waited for it, 15 times in the network update
  (`release_between_steps` of `SharedEvaluatorServer` in
  `studies/campaign/shared_evaluator.py`). The training process's footprint
  grew from 1.9 GB to between 5.2 and 6.4 GB during the network update, against
  15.4 GB in the third part, and stayed at about 5.3 GB after it; the run's
  processes held at most 9.0 GB in all. The network update took 124 seconds,
  against 117 in the third part, and the inference server answered 2,126
  network evaluations a second during it, against about 3,440 in the third part
  and about 2,300 in the fourth part's network updates. Between network updates
  it answered 7,000 to 7,500 network evaluations a second in each minute, about
  as in the third part, 6,400 to 7,300. No process stopped, and the part played
  its 15 minutes out.
- **The GPU alone.** A compiled forward pass of 256×16 over an inference batch
  of real positions took 4.3 ms for 8 states, 7.1 ms for 32, 11.3 ms for 64,
  18.1 ms for 128 and 32.3 ms for 256, laying out and reading back included:
  about 4.3 ms plus 0.11 ms a state from 64 states up. Handing each inference
  batch to the GPU before reading the last one back took 3.5 ms a batch of 24
  states instead of 6.6, 5.4 instead of 9.2 at 48 and 9.5 instead of 14.5 at
  96, with the same outputs up to rounding.
- **Where the game processes' time went.** With one simulation a request a game
  thread waited for the inference server 81% of its time and spent 19% in the
  engine; with 8 a request, 57% and 42%. Of the engine's time in the three
  samples, listing legal actions took 48% to 66%, encoding the state 12% to 14%,
  playing actions 9% to 17% and copying and destroying games 7% to 13%; writing
  every listed action as canonical JSON, which the lighter bookkeeping takes
  out, took 5% to 7%.
- **A search tree takes less memory.** In twelve searches of 800 simulations at
  positions of a scripted game, a tree held about 1,000 nodes and took 132.8 KB
  a node with the lighter bookkeeping, against 162.9 KB before, 18% less; the
  searches cost 0.57 ms of CPU a network evaluation against 0.60, on one core
  with a stand-in evaluator.
- **Gathering simulations changed a full search less than its exploration
  noise's seed did.** On 70 positions of three scripted games with a stand-in
  network, after 800 simulations with exploration noise the root's visit shares
  with 8 simulations a request differed from 1 a request by a total variation
  distance of 0.050 on average, and with 16 by 0.064, while two searches of 1 a
  request with different seeds, and so different noise, differed by 0.173; the
  most visited action was the same at 56, 52 and 52 of the 70. After 150
  simulations without noise, where a seed changes only the dice and the
  tie-breaks, 8 a request differed by 0.053 and 16 by 0.075, another seed by
  0.020, and the most visited action stayed the same at 63, 60 and 66.
- **A kept tree brings many of a search's visits.** In two games played with the
  run's search settings, 8 simulations a request and the stand-in network, 407
  searches: a fast search's root already held 126.6 visits from its kept tree on
  average, a median of 56, and 27% of the fast searches held 150 or more; a full
  search's root held 113.6, a median of 59. Counting those visits toward the
  budget, as KataGo's caps count a tree's nodes, would have run 26.4% fewer
  simulations, and counting them in the fast searches alone 17.7% fewer (Q-023).
- **A 256×16 training step** of 256 training samples took 161 ms alone on the
  GPU, and 390 ms beside self-play in the third part's network update.

## How it was measured

- **Runs.** Each part of the run `studies/campaign/runs/speed-256x16-2026-11-24`
  is a training run of self-play that never stops, started by `run_part.sh`
  from its own copy of the code (`code/`, with `COMMIT` naming the commit and
  the changes on it) and stopped by the supervisor after 25 minutes, 20 for the
  fourth and 15 for the fifth, or sooner by its memory guard. Eleven-round
  games, a fresh 256×16 network, one network for the three alliances, compiled
  layers, the GPU (`--neural-device mps`), seed 20261124, 6 game processes. A
  network update followed as many finished games as there were concurrent
  games: 4 training steps of 256 training samples, 300 in the third and fifth
  parts and 50 in the fourth. PyTorch 2.14.0 on the Mac's Apple M4 Max;
  `MallocNanoZone` unset in the training processes, as the supervisor's Mac
  profile does.
- **Rates** come from `serving.jsonl`, which the run writes once a minute since
  this work (`log_serving` in `studies/campaign/run.py`): the inference
  server's network evaluations, inference requests and inference batches so far
  and its time answering them. A rate is a difference between two lines over
  the seconds between them; the first three minutes, in which the GPU's graphs
  compile, are left out. **Load** comes from `tools/log_process_load.py`, every
  5 seconds, as half-minute windows, and **CPU per network evaluation** is the
  game processes' CPU seconds over the whole part divided by its network
  evaluations. **Memory** is the supervisor's sampled peak of the run's
  processes (`supervisor.log`), which counts the memory the processes share in
  each of them, and from the third part on the physical footprints that `top`
  shows, read by hand in the third part and every 15 seconds in the fourth and
  fifth (`footprints.py`, written to each part's `footprints.jsonl`).
- **The forward pass alone** was timed by `benchmarks/bench_forward.py`: real
  positions of two scripted eleven-round games, packed and evaluated through the
  inference server's own functions, compiled layers, the median of 25 passes
  of each size. `benchmarks/bench_pipeline.py` times the same inference batches
  of 256×16 one after another and overlapped, the next laid out and handed to the
  GPU before the last one's outputs are read.
- **Where the game processes' time goes** comes from `/usr/bin/sample`, 10
  seconds of one game process, classified by `benchmarks/search_samples.py`:
  in the first part's fourth minute, and in the second part's fifth and tenth.
- **Identical play** was checked with `tools/compare_engine_builds.py` against
  the second part's build, which has the same search: random games (`random`,
  seeds 7000 to 7039) and searched games (`search`, seeds 41 to 44, with
  `benchmarks/weights_64x2.pt`), their records in `benchmarks/`.
- **The searches compared** by `benchmarks/compare_requests.py`, the root visits
  a kept tree brings by `benchmarks/reused_visits.py`, a search tree's memory by
  `benchmarks/probe_tree_memory.py` (the growth of the process's peak resident
  memory over twelve searches of 800 simulations, before and after the lighter
  bookkeeping) and a 256×16 training step by `tools/benchmark_network_sizes.py`,
  all by `benchmarks/probes.sh`, one after another on a quiet Mac.

The command of a part, from its `code/` folder, with PROCESSES game processes of
GAMES games, SECONDS seconds, and the part's own options after it:
`--simulations-per-request 8` from the second part on, and `--epochs 300` in
the third and fifth parts and `--epochs 50` in the fourth, which replace the
`--epochs 4`:

```
.venv/bin/python tools/supervise_campaign_training.py --profile mac --control-dir PART/run-control --run-dir PART/run --seconds SECONDS --max-restarts 0 -- --calendar-rounds 11 --complete-episodes --batches 1000000 --simulations 150 --kept-simulations 800 --sample-fraction 0.25 --sampling-game-rounds 1 --max-depth 100000 --hidden-dim 256 --message-layers 16 --batch-size 256 --epochs 4 --replay-capacity 100000 --transitions-per-batch 20000 --seed 20261124 --neural-device mps --continuous --compiled-forward --episode-workers PROCESSES --games-per-process GAMES --parallel-envs PROCESSES*GAMES
```

## The settings it suggests for the training run

From these parts, a training run at these sizes on the Mac would play 30
concurrent games in 6 game processes of 5, with 8 simulations a request if
Q-022 is answered so: the inference server is then busy 94% of the time and the
CPU cores a median of 8.4 of the 9, so that neither more concurrent games nor
fewer would answer more network evaluations a second. At 7,335 network
evaluations a second, the fourth part's rate with its network updates, and
217,000 a game, that is about 2,900 games a day, and 145,000 games take about
50 days (inferred). With the GPU's caches
released every 20 training steps, a network update can be as long as the
training needs without filling the memory. While it runs, the inference server
answers about a third of its rate: the fourth part's network updates of 50
training steps cost about 3% of the network evaluations between two of them,
and the fifth part's 300 after 24 games about 15% (inferred from the rates
before and during them).

## What it shows and does not show

It shows that at the sizes taken from AlphaZero and KataGo the Mac's GPU was
not the limit: as the program was, the inference server's inference batches
were too small to keep it working, and once 8 simulations went in each
inference request, with the inference batches overlapped, the GPU had room
left and the 9 CPU cores of the allowance set the pace. With 24 and 30
concurrent games instead of 48, whose game threads stayed on the performance
cores, a network evaluation cost the game processes a quarter less CPU, and the
inference server limited again, busy 94%, with the CPU cores close behind: at 30
the GPU and the CPU cores of the allowance limit together, at about 7,600
network evaluations a second. More speed then needs a cheaper inference server
and a cheaper engine together, or fewer network evaluations a game.

It does not show the rates of a trained network. These games were a fresh
network's, about 313 decisions long; a trained network's games were about 880
([record](game_size_2026_11_24.md)), with more battles and more moves, whose
legal actions cost more to list, so the rate may differ. Each part ran once, on
a Mac whose other work kept about a core busy, and runs of the same code have
differed by about 5% before
([record](concurrent_games_cpp_search_2026_11_19.md)). Whether 8 simulations a
request change what training learns is not measured: only how much they change
a search's visit shares, with a stand-in network. Nor does it show what a long
run's replay buffer adds to memory.
