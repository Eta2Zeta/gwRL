# What a training run holds in memory — 18 November 2026

The owner allows training 30 GB of memory. This record measures what holds it
besides the search trees, whose size the
[record of 14 November](network_and_search_cost_2026_11_14.md) measured: the
parts of two runs' checkpoints, and the memory each concurrent game took in the
GPU runs of 18 November. From those it works out when memory would limit
training. The [evidence file](memory_in_training_2026_11_18.json) holds every
value and the script that measured the checkpoints.

- **The learner keeps an event for every transition of every game it has
  played, and never drops one** (`action_history` in
  `studies/campaign/learning.py`; it is saved in every checkpoint and restored
  on resume). After the 997 games of the night of 17 November it held 1,671,059
  events: about 2.04 GB of the main training process's memory, and 626 MB of
  its 815 MB checkpoint. That is about 1.2 KB of memory and 0.37 KB saved for
  each event, and 2.0 MB and 0.63 MB for each game. The training loop reads
  only the current training iteration's events, for its progress report
  (`train` in `studies/campaign/run.py`).
- **The replay buffer is small at its present size.** Its 8,000 training samples
  took 133 MB of the same checkpoint, about 16.7 KB each.
- **A concurrent game took about 70 to 85 MB at 64 simulations** in the GPU runs
  of 18 November at 256×8: 8.0 GB at the sampled peak with 63 concurrent games
  and 12.5 to 13.4 GB with 126
  ([concurrent games](concurrent_games_gpu_2026_11_18.md),
  [compiled layers](compiled_layers_126_games_2026_11_18.md)). Its search tree is
  about 11 MB of that.

## How it was measured

Each checkpoint was loaded with PyTorch 2.14 and each of its parts measured
twice. Its *saved size* is the length of the part written with Python's
`pickle`, as a checkpoint writes it. Its *size in memory* adds up
`sys.getsizeof` over its dictionaries, lists and their contents. That sum cannot
see inside the replay buffer's network inputs, which are native objects
(`CampaignZoneInput`), so for the replay buffer only the saved size is given.

| Checkpoint | Games | Transitions | Checkpoint | Events kept | Their memory | Their saved size | Training samples | Their saved size |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Night of 17 November, 64×2, one network | 997 | 1,671,059 | 815 MB | 1,671,059 | 2,041 MB | 626 MB | 8,000 | 133 MB |
| 18 November, 256×8, 126 concurrent games | 126 | 159,096 | 563 MB | 159,096 | 183 MB | 58 MB | 6,909 | 112 MB |

The night's run kept the most memory at its sampled peak, 9.98 GB for all its
processes, at its end, when its events held about 2 GB of it.

## When memory would limit

Inferred from the numbers above, not measured:

- **The events kept grow with every game.** At the Mac profile's rate of about
  270 games an hour, they take about 0.55 GB more memory an hour, about 4.4 GB in
  a night of eight hours, and each checkpoint grows by about 1.4 GB a night. A
  run resumed night after night would fill the 30 GB within about five nights,
  beside the 8 GB or so the rest of the run takes. At 256×8 on the GPU with 126
  concurrent games, whose games were shorter, about 1.5 MB a game, and whose
  other memory was about 13 GB, within five or six nights.
- **Longer searches fit fewer concurrent games.** A concurrent game holds its
  search tree and about 70 MB besides, and the processes take about 3 GB. With
  the search trees of the record of 14 November, 11 MB at 64 simulations, 56 MB
  at 256 and about 0.24 MB a simulation beyond, the 30 GB hold about 330
  concurrent games at 64 simulations, 215 at 256, 105 at 800 and 60 at 1,600.
  An inference batch holds about half the concurrent games
  ([design, section 9.3](../../design/README.md#93-what-a-larger-network-and-a-longer-search-cost)),
  so at 800 and 1,600 simulations about 50 and 30 states.
- **A larger replay buffer** would hold about 17 KB a training sample: a
  million training samples, about 17 GB.

## What this does and does not show

- **Measured:** the sizes of two checkpoints' parts, and the sampled peak memory
  of the runs they came from.
- **The events kept are the part that grows without end**; the others grow with
  the settings: the concurrent games, the search and the replay buffer's
  capacity.
- **Not measured:** a run resumed over several nights; the replay buffer's
  inputs in memory, rather than as saved; how much memory a game takes besides
  its search tree at more than 64 simulations; the Windows PC.
