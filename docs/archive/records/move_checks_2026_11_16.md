# Playing a move without checking it twice — 16 November 2026

The morning's profile found work repeated whenever a move is played
([record](self_play_limits_2026_11_16.md#inside-the-engine)). Playing an economy
move listed all of the economy's options again to check the move, though the
engine had already found it in the position's menu. And the check of the whole
position after every step built an error message for every name it checked,
whether or not the check failed. Two changes remove that work and leave play the
same: 300 random games reached the same positions at each of their 443,974
steps. In those games playing a move now takes 29% fewer instructions and
rolling dice 12% fewer, and the engine used 8.6% less CPU in all. In matched
training batches the game processes used 10.6% fewer instructions and 5.7% less
CPU per decision. Decisions per hour did not rise: the Mac was quieter than in
the morning, the training got about 10 cores, and the coordinator, not the
cores, set the pace. The [evidence file](move_checks_2026_11_16.json) holds the
exact values.

## What changed

- **The economy's check of a move.** `Engine::step` (`src/campaign_runtime.cpp`)
  looks the chosen move up in the position's menu, by its exact text, and refuses
  one that is not there. The economy module then listed all its options again
  and compared each with the move (`applyEconomyAction` in `src/economy.cpp`).
  Now `Engine::step` marks the move it has just found (`MenuCheckedAction` in
  `include/game/campaign.hpp`), and the economy module skips its own check for
  that very move. A move the module builds for itself, the purchase a railroad
  consent completes, is not marked and is checked as before.
- **The check of the whole position** (`State::validate` in
  `src/campaign_state.cpp`), which runs after every step. It now asks the map's
  frozen index whether a zone exists and is land, instead of the map's JSON, and
  builds an error message only for a check that fails. It no longer builds a set
  for every unit to look for cargo cycles, only for a unit that is carried. The
  same applies to the training rules' own checks of their records
  (`src/campaign_actions.cpp`). The map's index keeps, for each zone, whether it
  is land (`IndexedGeography` in `include/game/campaign.hpp`). It checks the
  same things in the same order, and fails with the same messages.

## The same play

300 seeded random eleven-round games, seeds 7000 to 7299, played through the
environment the search uses. Each move was drawn at random, and the phase ended
with a probability of 2%, 5% or 10% by seed. At every step a digest recorded the
list of legal moves, the chosen move and the position reached, by its planning
key. All 300 games gave the same digests at all 443,974 steps and the same final
position before and after the change. The C++ suites (26 of 26) and the Python
suite (467 tests, 6 skipped) pass.

## Random play

The same 300 games, the two versions at the same time, 4 processes each. Each
engine call's thread CPU time, and the instructions the process ran during it,
were measured around the call.

| Engine call | Calls | Before | After | Instructions per call, before and after | Change in instructions |
| --- | ---: | ---: | ---: | --- | ---: |
| Listing the legal moves | 391,840 | 719 µs | 726 µs | 10.29 M, 10.29 M | 0% |
| Playing a move | 391,840 | 461 µs | 353 µs | 6.18 M, 4.40 M | −28.8% |
| Rolling dice | 52,134 | 277 µs | 250 µs | 3.61 M, 3.19 M | −11.6% |

The engine's CPU in all 300 games fell from 476.7 to 435.9 seconds, by 8.6%.

## Training batches

Two matched pairs of the Mac profile's batch (6 game processes of 4 games, 24
eleven-round games, 64 simulations, the 64×2 network on the CPU, seed 20261104),
the code before and after alternating. `tools/log_process_load.py` measured each.

| Batch, in the order run | Before 1 | After 1 | Before 2 | After 2 |
| --- | ---: | ---: | ---: | ---: |
| Decisions per hour while playing | 265,368 | 236,816 | 252,887 | 244,993 |
| Game processes' instructions per decision | 1,226 M | 1,124 M | 1,265 M | 1,102 M |
| Game processes' CPU per decision | 121.8 ms | 117.3 ms | 124.7 ms | 115.2 ms |
| Coordinator's instructions per decision | 177 M | 179 M | 183 M | 175 M |
| Coordinator busy | 93% | 87% | 90% | 90% |
| Coordinator's busy time per evaluation | 231 µs | 242 µs | 234 µs | 241 µs |
| Training's load, cores, mean of half-minute windows | 10.4 | 9.1 | 10.1 | 9.8 |
| Other work, cores, median window | 1.6 | 2.2 | 1.7 | 2.0 |
| Peak memory, sampled | 4.6 GB | 4.6 GB | 4.3 GB | 4.5 GB |
| Failed games | 0 | 0 | 0 | 0 |

On average the game processes ran 10.6% fewer instructions per decision and used
5.7% less CPU per decision. Instructions do not depend on the Mac's other work,
so they show the saving best. The coordinator's work per decision did not change.

Decisions per hour fell by 7%, from 259,100 to 240,900 on average. The
coordinator was busy about 90% of the time in all four batches, and in the two
after batches it took 4% longer per evaluation. It ran the same code, but at
3.8 instructions per cycle instead of 3.9. To see whether the new game code
slowed it, the coordinator's saved rounds were replayed beside 8 processes
playing random games of each version, alternating:

| Replayed beside | Median time per round, each run |
| --- | --- |
| Nothing | 968 µs, 972 µs |
| Random games of the code before | 1,044 µs, 967 µs, 968 µs |
| Random games of this change | 973 µs, 1,013 µs, 965 µs |

The rounds took as long beside either version. The coordinator's slower after
batches therefore came from the Mac, whose other work was a little heavier
during them.

## What this does and does not show

- **Measured:** identical play in 300 random games; the instructions and CPU of
  each engine call in them; four training batches, with their instructions,
  CPU and load; the coordinator's replayed rounds beside each version.
- **Inferred:** with a quiet Mac the coordinator limits the Mac profile, so
  less CPU per decision does not raise decisions per hour. When the Mac's other
  work leaves the training fewer cores, as in the morning's profile, the cores
  limit, and less CPU per decision raises decisions per hour in proportion.
- **The 9-core allowance.** With about 2 cores of other work, the 6 game
  processes and the coordinator kept 9.1 to 10.4 cores busy on average, more
  than the allowance. The layout's load grows into whatever cores are free; the
  open question on the supervisor's count of cores
  ([Q-005](../../questions.md#answered)) covers it.
- **Not shown:** whether the 7% fall in decisions per hour is real. Two pairs
  under differing loads cannot separate it from the Mac; the replay found no
  effect of the change on the coordinator.
