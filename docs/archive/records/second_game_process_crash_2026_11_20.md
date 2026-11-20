# A second game process crash, survived by replacing the process — 20 November 2026

The long training run started on 20 November 2026 at 06:54 from commit
`7adac20` plays 252 concurrent games, in six game processes of 42 game threads,
against the 256×8 network on the Mac's GPU, with self-play that never stops. It
starts from generation 13 of the run of the
[first crash](game_process_crash_2026_11_20.md), and its engine and search are
the same code: no file under `src/` or `include/`, nor `setup.py`, changed
between `999c90c` and `7adac20`. What changed is that a game process that dies
is replaced, and only the games it had not finished fail (`play_shared_games`
in `studies/campaign/shared_evaluator.py`). The
[evidence file](second_game_process_crash_2026_11_20.json) holds the crash
report's stack, every failed game and every network update's time and counters.

- **Two games failed the engine's state check.** Between the third network
  update at 10:08:12 and 10:46, two games of game process 7800 failed with
  `RuntimeError: A zone number names no zone`. The engine checks the state
  after every move (`RecordedHistory::validate` in `src/campaign_runtime.cpp`),
  and `State::validate` in `src/campaign_state.cpp` raises this error when
  something in the state that names a zone (a unit's zone, turn origin or
  route, a territory, a facility, a railroad, a capital, a battle, or the
  record of the turn's start) holds a zone number that no zone has. The two
  games had played 3,162 and 891 seconds. They were in game slots 182 and 206,
  two of the slots 168 to 209 that process 7800 played: each process plays 42
  slots in a row, and the six processes were started in order.
- **The crash.** At 10:46:18, after 3.86 hours of play, game process 7800
  aborted with the same allocator message as in the first crash
  (`___BUG_IN_CLIENT_OF_LIBMALLOC_POINTER_BEING_FREED_WAS_NOT_ALLOCATED`).
  This time the memory was being freed by the destructor of a unit's state
  (`UnitState` in `include/game/campaign.hpp`), in the game copy of a search
  tree node. The search had chosen a move and was freeing the nodes of the
  game's tree that the next search does not keep (`Searcher::retain` in
  `src/search.cpp`).
- **The replacement.** The training process recorded the 42 games that process
  7800 had in play as failed games, and game process 68542 took its game slots
  at 10:46:18. The other five processes played on, and the run did not stop.
- **The cost: about 7 minutes of the run's play (inferred).** The 42 lost games
  had played 2,432 seconds on average (from 3 to 4,359), and the two games
  that failed the check 4,053 seconds together: 106,202 seconds of play by
  single game slots, which is about 7 minutes of all 252. The first crash cost
  about 51 minutes. The fourth network update came 83.9 minutes after the third;
  the intervals before and after were 54.3, 57.9 and 54.3 minutes. That
  interval does not measure the crash alone. At 10:40 the run had 6.95 cores,
  while three development servers of another project took 1.87; the run had
  about 8.8 cores the day before, and 8.0 at 12:36.

## What this shows and does not show

It shows that the defect strikes in the current engine and search, in a
different object than the first time: a unit's state, where the first crash
found a nation's. The only two games of this run to fail the state check were
in the process that aborted, in the 38 minutes before it did, so the damage
most likely reached their states first (inferred, not proven). In the first
crash, too, a game had raised an error just before the abort, but that error's
text was lost with the process.

It does not show where the damage is done, nor whether damage that leaves a
real zone number in place, or changes a number the check does not read, went
into training samples unnoticed. That the check caught a zone number with no
zone suggests that other damaged values may pass it (inferred).

This is the second crash in 16.6 hours of play of 252 games with the search in
C++: 5.13 hours of the run of 19 November before its crash, 5.75 hours after
its restart, and 5.69 hours of this run to 12:35. That is about one crash
every 8 hours, but two crashes do not measure a rate well.
