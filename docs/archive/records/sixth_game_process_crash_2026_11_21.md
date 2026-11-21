# A sixth game process crash, the first with the new diagnostics — 21 November 2026

The long training run was started again at 08:39 on 21 November 2026, in
`tmp/training-2026-11-21`, from commit `6f04943`: the engine and search of the
five earlier crashes, built with libc++'s fast hardening and the SlotMap check,
and a run that keeps each game's move log, a crashed process's crash report and
the allocator's message ([record of the look for the defect](crash_diagnosis_2026_11_21.md)).
It plays 252 concurrent games, in six game processes of 42 game threads. The
[evidence file](sixth_game_process_crash_2026_11_21.json) holds the crash
report's stack, the allocator's message, the crashing thread's Python stack,
the dead process's 42 games and their replays.

- **Three attempts.** The swap rule stopped the first attempt after 16 minutes
  and the second after 1.5 minutes: the swap in use grew by 4 GB, to 14.4 and
  then 17.7 GB, while other programs held about 20 GB of the Mac's 36 (Q-011's
  stop). The third attempt started at 09:00:29.
- **The crash.** At 09:04:12, 3.6 minutes after it started, game process 23464
  aborted. The allocator wrote "error for object 0x60000a0abff0: pointer being
  freed was not allocated" to the attempt's standard error, and the fault
  handler wrote every game thread's Python stack after it: the crashing thread
  was in the C++ search (`search_decision` in `studies/campaign/native_search.py`),
  as were the others. The crash report places it where the second and fifth
  crashes were: freeing a unit's state (`UnitState`) in the game copy of a
  search tree node, while the search freed the nodes the next search does not
  keep (`Searcher::retain` in `src/search.cpp`). Of the other 41 game threads,
  40 were waiting for the inference server and one was reading a unit through
  a SlotMap iterator.
- **The checks.** Neither libc++'s hardening nor the SlotMap check fired before
  the abort.
- **The run stopped.** No game had finished, so the death ended the play, as a
  game process that dies before reporting a game does, and with three stops in
  25 minutes the keeper wrote FAILED. The training process's copy of the crash
  report did not happen, because it exited at once; the report was copied by
  hand, and the training process now waits for the copy before it exits.
- **The replay.** The dead process's 42 games, slots 168 to 209, had played 41
  to 49 decisions each, and each move log ended with a decision's search under
  way. `tools/replay_game_moves.py` rebuilt every game from its seed and moves,
  in a build with AddressSanitizer, UBSan, libc++'s debug hardening and the
  SlotMap check, and searched each game's last three decisions and the one
  under way again with their logged seeds, in a kept tree, with the run's
  starting network on the CPU: 42 games, no report.

## What this shows and does not show

It shows the diagnostics working: the allocator's message, the Python stacks,
the crash report and the move logs all survived. It shows the defect again, in
a build whose checks would have stopped an out-of-bounds index into a standard
container or a stale SlotMap iterator on the paths they cover: six crashes in
about 35.8 hours of play of 252 games with the search in C++, about one every
6 hours. And it shows that the replayed searches do not reproduce it: their
network ran on the CPU, so its priors, and the trees the searches built,
differed in their last digits from those of the game process, whose inference
server answered on the GPU.

It does not show where the damage is done.
