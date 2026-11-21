# A fifth game process crash, survived by replacing the process — 21 November 2026

The run of the [fourth crash](fourth_game_process_crash_2026_11_21.md), started
on 20 November 2026 at 22:43 in `tmp/training-2026-11-20c` with the engine and
search of commit `1463ff4`, lost a second game process at 04:49 on 21 November.
It plays 252 concurrent games, in six game processes of 42 game threads, against
the 256×8 network on the Mac's GPU, keeping 1% of each game's decisions and a
replay buffer of 25,000 training samples (Q-013, answered). The
[evidence file](fifth_game_process_crash_2026_11_21.json) holds the crash
report's stack, every game lost with the process and the run's first nine
network updates.

- **The crash.** At 04:49:39, after 6.11 hours of play, game process 23524
  aborted with the allocator message of the four earlier crashes
  (`___BUG_IN_CLIENT_OF_LIBMALLOC_POINTER_BEING_FREED_WAS_NOT_ALLOCATED`). The
  memory being freed was a unit's state (`UnitState`, in the game state's
  `SlotMap` of units, `include/game/campaign.hpp`), in the game copy of a search
  tree node, while the search freed the nodes of a game's tree that the next
  search does not keep (`Searcher::retain` in `src/search.cpp`). The second
  crash was in a unit's state too.
- **No game had failed the state check.** The run's only other failed games are
  the 42 lost with game process 23525 in the fourth crash, at 00:18.
- **The replacement.** Game process 72892 took the dead process's game slots,
  168 to 209 (inferred from the order in which the six processes were started),
  and the other five processes played on.
- **The cost: about 4 minutes of the run's play (inferred).** The 42 lost games
  had played 1,336 seconds on average (from 24 to 3,131): 56,103 seconds of play
  by single game slots, about 3.7 minutes of all 252. The network update after
  the crash, number 7, came 50.1 minutes after number 6, at 461,051 decisions an
  hour, against 45 to 49 minutes for the run's other intervals from network
  update 4 to 9.

## What this shows and does not show

It shows the defect again, 4.52 hours after the fourth crash: five crashes in
32.6 hours of play of 252 games with the search in C++, about one every 6.5
hours. All five aborted while freeing the game copies of search tree nodes, four
of them in `Searcher::retain`, and the memory being freed was in a nation's
state, a unit's state twice, a whole game state and a game state's build
projects. The crash came 32 minutes into its update interval and delayed the
next network update little, most likely because the other 210 game slots had
already finished most of its 252 games (inferred).

It does not show where the damage is done, nor whether damaged values went into
training samples unnoticed.
