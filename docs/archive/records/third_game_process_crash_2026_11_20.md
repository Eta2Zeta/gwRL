# A third game process crash, survived by replacing the process — 20 November 2026

The long training run started on 20 November 2026 at 06:54 from commit
`7adac20`, the run of the [second crash](second_game_process_crash_2026_11_20.md),
lost a second game process at 14:28. It plays 252 concurrent games, in six game
processes of 42 game threads, against the 256×8 network on the Mac's GPU, with
self-play that never stops; its engine and search are those of the
[first crash](game_process_crash_2026_11_20.md). The
[evidence file](third_game_process_crash_2026_11_20.json) holds the crash
report's stack, every game lost with the process and every network update's
time and counters.

- **The crash.** At 14:28:26, after 7.56 hours of play, game process 7799
  aborted with the allocator message of the two earlier crashes
  (`___BUG_IN_CLIENT_OF_LIBMALLOC_POINTER_BEING_FREED_WAS_NOT_ALLOCATED`). The
  memory was being freed by the destructor of a game state (`State` in
  `include/game/campaign.hpp`), in the game copy of a search tree node, while
  the search freed the nodes of a game's tree that the next search does not
  keep (`Searcher::retain` in `src/search.cpp`). The second crash was in the
  same place, in the destructor of a unit's state, which a game state holds.
- **No game of that process had failed.** The run's only games to fail the
  engine's state check were two games of process 7800, before the second crash.
  Process 7799 played game slots 126 to 167 for 7.56 hours and lost no game
  before it aborted.
- **The replacement.** The training process recorded the 42 games that process
  7799 had in play as failed games, and game process 6416 took its game slots
  at 14:28:26. The other five processes played on.
- **The cost: about 6 minutes of the run's play (inferred).** The 42 lost games
  had played 2,192 seconds on average (from 4 to 3,872): 92,068 seconds of play
  by single game slots, about 6.1 minutes of all 252. The eighth network update
  came 69.6 minutes after the seventh, against 51.6 and 50.9 minutes for the two
  before, which ran at 433,000 and 441,000 decisions an hour. That interval
  overstates the cost: a network update waits for 252 finished games, and the
  42 games that started at 14:28 had too little time to finish before it, so
  the other slots had to finish more (inferred). At 14:36 the run had 8.35
  cores over 30 seconds, and the Mac was 33% idle.

## What this shows and does not show

It shows that the defect strikes again within hours: three crashes in 18.4
hours of play of 252 games with the search in C++ (5.13 hours of the run of 19
November before its crash, 5.75 hours after its restart, and 7.56 hours of this
run to this crash), about one every 6 hours. All three aborted while freeing
the game copies of search tree nodes, two of them in `Searcher::retain`. The
allocator notices a bad free only when the memory is freed again, and the
search makes and frees most of a game process's game copies, so the place of
the abort may say little about where the damage is done (inferred).

It also shows that a crash need not follow a failed state check: the second
crash did, this one did not. If those failures came from the same defect, as
the [second record](second_game_process_crash_2026_11_20.md) infers, the check
catches its damage only sometimes (inferred).

It does not show where the damage is done, nor whether damaged values went
into training samples unnoticed.
