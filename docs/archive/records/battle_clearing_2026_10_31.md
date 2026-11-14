# Automatic clearing of finished battles — 31 October 2026

The training action profile, now `campaign-orders-v2`, no longer asks a player
to click "progress battle" only to delete a battle that has already ended. This
is P2 of the [decision review](decision_review_2026_10_31.md). Games do not
change: in matched scripted games the same choices give the same dice and final
scores, with **5.2%** fewer decisions. In a matched 64-simulation search run,
network evaluations fell **3.8%**. The ordinary game profile keeps the click.
The [evidence file](battle_clearing_2026_10_31.json) holds the exact values.

## What changed

A finished battle stays in `State.battles` until its follow-ups are done:
aircraft landings, blitz pairing and capture choices. The combat menu then
offered `land_progress_battle` (`naval_finish_battle` at sea), which deletes the
record. Like every ordinary action it also ran the political refresh, but it
uses no dice, removes no other option, and finished battles can be cleared in
any order. Combat cannot end while any record remains, so the player whose turn
it is had to click once per battle.

Every rules profile now has a `settle` step that runs at the end of each action,
declaration and dice transition, before the new position is recorded. The
training profile uses it to apply each clearing the combat menu offers, through
the same `apply` as a chosen action, until none is left. The clearing becomes
part of the transition that finished the battle's last follow-up.
`landBattleClearing` in `src/land_combat.cpp` defines a clearable land battle
for both the menu and this step.

That refresh exposed a separate gap. Breaking the KMT–CCP truce
(`truce_break`) and accepting it (`truce_accept`) did not recompute the nations'
allies lists, which stayed wrong until the next ordinary action. Breaking the
truce and then clearing a battle therefore gave a different position from
clearing first and then breaking the truce. No rule reads these lists, but the
network sees them and they are part of each position's identity. Both truce
changes now update the lists at once, in both profiles.

Steps of battles that are still being fought stay decisions, including
"begin battle" and "progress battle" when they are the only action. The
review's P2 estimate (6.4–6.7% of scripted decisions) counted those too. A
declaration can still be made at such a position, so applying the step
automatically could remove that opportunity; they belong with the general
single-option change (P1). Clearing never removes one: in every test below, the
declarations offered before a clearing were still offered after it.

## Results

Before is `d93e85b`, whose engine matches the review's `6522736`; after is this
change. Each pair uses the same seed and the same scripted choices. The search
uses a uniform evaluator.

| Matched run | Before | After | Change |
| --- | ---: | ---: | ---: |
| Decisions, 3 rounds, seed 1951 | 579 | 549 | −5.2% |
| Decisions, 11 rounds, seed 1953 | 2,080 | 1,971 | −5.2% |
| Searched decisions (two or more options), 3 rounds, 64 simulations | 472 | 454 | −3.8% |
| Network evaluations, same search run | 30,620 | 29,450 | −3.8% |
| Search time, same run | 208.8 s | 205.3 s | −1.7% |

- Final scores (28.1, −36.9, −88.3 and 51.3, −52.3, −100.7) and dice events
  (116 and 418) are identical. The removed decisions are exactly the 30 and
  109 clearing clicks; every other choice is the same, in the same order.
- Evaluations fall less than decisions because 16 of the 30 removed clicks were
  single-option positions, which search already skipped. The other 14, and 4
  positions left with one option once their clearing was gone, are the 18 fewer
  searched decisions. Each searched decision still costs about 65 evaluations.
- The two search runs ran side by side on a 4-vCPU Linux container; their time
  difference is within noise.
- The after runs were repeated on the final code, including the truce fix, with
  the same choices, dice, scores and 29,450 evaluations.
- These are workload measurements with scripted moves. Completed-game
  throughput in the Mac training setup has not been measured. While games are
  limited by network evaluations, the saving should be close to the 3.8%
  reduction in evaluations.

## Verification

- **Lockstep with the old behaviour.** A reference copy of the training profile
  without the settle step plays the same random games and clicks every clearing
  as soon as it is offered. At every decision both engines have identical
  positions, menus, declarations and execution randomness: 20 three-round games
  (10,777 decisions, 1,101 dice events, 326 clearings) and 4 eleven-round games
  (6,660 decisions, 652 dice events, 206 clearings).
- **Clearing later.** The reference also plays games in which, while a clearing
  is offered, it prefers any other choice, declarations included. Every such
  choice stays legal for the training profile, and once the reference clears
  the same battles, positions, menus, declarations and randomness agree again.
  20 three-round and 4 eleven-round games made 232 choices and 7 declarations
  with a clearing left for later (17,005 shared decisions, 18,268 position
  comparisons). This check found the truce gap above; before the fix it failed
  in the sixth three-round game.
- A finished naval battle in a fixture clears itself, consuming no randomness.
- Training games with automatic clearings replay exactly from their history.
- The truce test now checks the allies lists right after `truce_accept` and
  `truce_break`; that check fails on the code before the fix.
- C++: all 27 suites pass. `campaign_env` needs about 32 s in this container,
  over its 30-second limit, with or without the change (31.7 s before).
- Python: 464 tests ran, with the same 7 failures and 48 errors as on the
  unchanged code, none involving this change. 33 need PyTorch, which this
  container cannot install; 21 configure more CPU cores than its 4; one checks a
  macOS-only memory measure.

## Compatibility

The action version is now `campaign-orders-v2`. Checkpoints, replays and
recordings made with `campaign-orders-v1` are rejected, not migrated. Rebuild
the native extension after pulling.

## Reproduce

From the repository root, after building the C++ tests and the extension:

```sh
TRAINING_CLEARING_SEEDS=20 TRAINING_CLEARING_ROUNDS=3 build/<dir>/training_battle_clearing_tests
TRAINING_CLEARING_SEEDS=4 TRAINING_CLEARING_ROUNDS=11 build/<dir>/training_battle_clearing_tests
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 3 --seeds 1951
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 11 --seeds 1953
./.venv/bin/python tools/decision_census.py search OUT.jsonl --seed 1951 --rounds 3 --simulations 64 --policy balanced
```

Run the census and search commands on both commits to compare them.
