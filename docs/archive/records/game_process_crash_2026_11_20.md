# A game process that crashed in the training run of 19 to 21 November — 20 November 2026

The long training run started on 19 November 2026 at 19:58 from commit
`999c90c` plays 252 concurrent games, in six game processes of 42 game threads,
against the 256×8 network on the Mac's GPU, with self-play that never stops. It
runs under `tools/supervise_campaign_training.py`, and a shell loop outside the
repository starts the supervisor again whenever it exits. After 5.13 hours of
play one game process aborted, and the whole run stopped with it. The
[evidence file](game_process_crash_2026_11_20.json) holds the crash report's
stack, the supervisor's events and every network update's time and counters.

- **The crash.** At 01:06:28 on 20 November, game process 24917 aborted.
  macOS's memory allocator stopped it because a pointer being freed had not
  been allocated, in the frame
  `___BUG_IN_CLIENT_OF_LIBMALLOC_POINTER_BEING_FREED_WAS_NOT_ALLOCATED`. The
  memory was being freed by the destructor of a nation's state (`NationState`
  in `include/game/campaign.hpp`). That state belonged to the game copy of a
  node in a game's kept search tree (`SearchTree` in `src/search.cpp`), and
  the whole tree was being freed.
- **What freed the tree.** The game thread was handling an error that its game
  had raised: `_play_game` in `studies/campaign/episode_workers.py` turns an
  error into a failed game's record. Freeing the error's traceback freed the
  frame that held the game's tree. The failed game's record died with the
  process, so what the error said is not known.
- **How the run stopped.** Three seconds later the inference server's next
  reply to that process failed with `BrokenPipeError`, in
  `SharedEvaluatorServer.answer` (`studies/campaign/shared_evaluator.py`). The
  training process exited with code 1. The supervisor retries a run only after
  a kill, a segmentation fault, a bus error or exit code 75
  (`RETRYABLE_RETURNCODES`), so it recorded a worker error and exited.
- **The restart.** The shell loop started the supervisor again at 01:08:15. It
  resumed the run from `checkpoint.pt`, written at the sixth network update at
  00:28:04. The games then in play were lost.
- **The cost: about 51 minutes of training (inferred).** The seventh network
  update came at 02:06:14. The five intervals between updates before the crash
  were 33.5, 41.1, 42.2, 49.4 and 46.7 minutes, so without the crash it would
  have come at about 01:15.

## What this shows and does not show

It shows that a game process can damage memory that its game's search tree
owns, in a run of the current code. It does not show where the damage was
done. The allocator noticed it only when the tree was freed, so any native code
of that process could have done it: the engine or the search. It does not
show whether the game's error came from the same damage. One crash in 5.13
hours does not give its rate.

Two game-process crashes of the same kind were noted on 2 November 2026, with
an older build and the search still in Python. One was an abort with the same
allocator message, in the destructor of a catalog context. The other was a
segmentation fault reading freed memory while listing a nation's turn marks.
They were not written into a record, and their crash reports are gone.
