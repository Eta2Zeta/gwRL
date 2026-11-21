# A fourth game process crash, survived by replacing the process — 21 November 2026

The long training run was started again on 20 November 2026 at 22:43, in
`tmp/training-2026-11-20c`, from generation 6 of the run before it, keeping 1%
of each game's decisions as training samples and a replay buffer of 25,000 of
them (Q-013, answered that evening). Its engine and search are those of commit
`1463ff4`, the same code as in the
[first](game_process_crash_2026_11_20.md),
[second](second_game_process_crash_2026_11_20.md) and
[third](third_game_process_crash_2026_11_20.md) crashes. It plays 252 concurrent
games, in six game processes of 42 game threads, against the 256×8 network on
the Mac's GPU, with self-play that never stops. The
[evidence file](fourth_game_process_crash_2026_11_21.json) holds the crash
report's stack, every game lost with the process and the run's first two
network updates.

- **The crash.** At 00:18:20 on 21 November, after 1.59 hours of play, game
  process 23525 aborted with the allocator message of the three earlier
  crashes (`___BUG_IN_CLIENT_OF_LIBMALLOC_POINTER_BEING_FREED_WAS_NOT_ALLOCATED`).
  The memory being freed was an entry of a game state's build projects
  (`State::construction`, a map from an id to a `BuildProject`, in
  `include/game/campaign.hpp`), in the game copy of a search tree node, while
  the search freed the nodes of a game's tree that the next search does not
  keep (`Searcher::retain` in `src/search.cpp`). The second and third crashes
  were in the same place, in a unit's state and in a whole game state.
- **No game had failed before it.** No game of the run had failed the engine's
  state check, and the run had kept no failed position.
- **The replacement.** The training process recorded the 42 games that process
  23525 had in play as failed games, and game process 36227 took its game
  slots, 210 to 251 (inferred from the order in which the six processes were
  started). The other five processes played on.
- **The cost: about 5 minutes of the run's play (inferred).** The 42 lost games
  had played 1,837 seconds on average (from 22 to 3,116): 77,161 seconds of
  play by single game slots, about 5.1 minutes of all 252. The second network
  update came 74.1 minutes after the first, at 322,646 decisions an hour. That
  interval overstates the cost: a network update waits for 252 finished games,
  and the 42 games that started at 00:18 had too little time to finish before
  it (inferred). At 00:47 the run had 8.19 cores over 10 seconds, the Mac was
  24% idle, and its swap held 7.96 GB.

## What this shows and does not show

It shows the defect again, 1.59 hours into a run whose learning settings differ
from the earlier runs' but whose engine and search are the same: four crashes in
28.1 hours of play of 252 games with the search in C++, about one every 7 hours.
Those hours are 18.44 to the third crash, 1.74 more in the run of the third
crash until it stopped, 6.31 in the run of 20 November from 16:22 to 22:42 (which
had no crash) and 1.59 in this run. All four crashes aborted while freeing the
game copies of search tree nodes, three of them in `Searcher::retain`, and the
memory being freed was each time in a different part of a game state: a
nation's state, a unit's state, a whole game state and now its build projects.
The allocator notices a bad free only when the memory is freed again, so the
place of the abort may say little about where the damage is done (inferred).

It does not show where the damage is done, nor whether damaged values went into
training samples unnoticed.
