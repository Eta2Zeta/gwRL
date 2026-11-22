# The training process's memory in the training run of 19 to 21 November — 20 November 2026

The long training run started on 19 November 2026 from commit `999c90c` plays
252 concurrent games, in six game processes of 42 game threads, against the
256×8 network on the Mac's GPU, with self-play that never stops. It was
restarted at 01:08 on 20 November after a game process crashed
([record](game_process_crash_2026_11_20.md)), from the checkpoint of its sixth
network update. From 00:42 a script outside the repository logged, every
minute, the run's highest memory total of that minute, measured as the
supervisor measures it: for each process the larger of its resident size and
its physical footprint (`process_memory_charge` in
`tools/supervise_campaign_training.py`), split into the training process (the
inference server, the learner and its replay buffer) and the game processes.
`vmmap -summary` on the training process gave its memory by kind three times.
The [evidence file](training_process_memory_2026_11_20.json) holds the minutes,
the `vmmap` rows and the network updates' times and counters.

## Results

- **The training process grew by about 1.25 GB an hour.** Its lowest minute in
  each 20 minutes after the restart, in GB:

  | From | 01:20 | 01:40 | 02:00 | 02:20 | 02:40 | 03:00 | 03:20 | 03:40 | 04:00 | 04:20 | 04:40 |
  | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
  | Training process | 2.23 | 2.26 | 3.04 | 4.74 | 5.20 | 5.79 | 5.91 | 6.63 | 6.91 | 7.49 | 7.88 |

  From 03:00 to 04:40 it grew by 2.09 GB, 1.25 GB an hour. Before the crash it
  had reached 8.0 to 8.4 GB between 00:43 and 01:03.
- **The run's highest minutes came during network updates:** 21.18 GB at 03:44
  and 23.18 GB at 04:29. The training process then held 11.16 and 12.41 GB,
  about 4.6 to 4.9 GB above its level between network updates, and the game
  processes 10.0 and 10.8 GB.
- **The growth was in Python's objects.** From 04:43:29 to 04:56:55 the
  training process's physical footprint rose from 7.3 to 7.6 GB. Python's
  memory for small objects, which `vmmap` lists as untagged regions of 1 MiB,
  rose from 2,542 to 2,779 regions, 1.03 GB an hour, and 2.3 to 2.5 GB of it
  was compressed or swapped out: memory that nothing was reading. The GPU's
  memory stayed at 2.1 GB; the allocator's zone for larger blocks went from
  1.6 to 1.7 GB in use.
- **The cause.** `play_shared_games` in `studies/campaign/shared_evaluator.py`
  added each finished game's result, with its training samples and its events,
  to a list that lived as long as the run played, and `keep_playing` in
  `studies/campaign/run.py` read that list by position and removed nothing. A
  reading of the training process's code found nothing else that grows by
  megabytes with every game. The run's manifest keeps a summary of every game,
  about 5 KB a game in `manifest.json` (12.7 MB after 2,533 games).
- **About 4 MB a game (inferred):** 1.25 GB an hour at 317.5 games an hour. A
  game had about 1,550 transitions, and its result held an event for each and
  about 73 training samples.

## What this shows and does not show

It shows that in self-play that never stops the training process kept every
finished game's result in memory, about 1.25 GB more an hour in this run. That
the results account for all of the growth is inferred: the regions that grew
hold Python objects, and the list of results is the only thing found that grew
by megabytes with every game. The fix, in the commit that added this record,
takes each result off the list as it is read and counts the games that
reported apart from the list. Whether the training process then stays level is
for the next run to show.

Projected, without the fix (inferred): the run's highest minute, at a network
update, reaches the supervisor's graceful stop at 29 GB (its 30 GB limit less a
margin of 1 GB) at about 09:00 to 10:00. The run then saves a checkpoint, which
keeps the games finished since the last network update, and loses the games in
play, about 25 minutes of play; the shell loop starts it again, and the
training process starts again from about 2.2 GB.
