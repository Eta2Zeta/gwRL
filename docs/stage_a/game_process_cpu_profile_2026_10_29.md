# Where self-play game processes spend CPU — 29 October 2026

This profile measures where the shared-GPU self-play game processes spend CPU
time in each game, before any optimization. Rules, search, model and dice are
unchanged. `tools/profile_game_process_cpu.py` charges each game thread's CPU
time to the innermost engine, input, messaging or search call it is in, and
samples one game process's native call stacks three times. Four separate
analyses then broke down the largest costs, and a verifier re-derived each of
their numbers from the raw data; two more reviewers checked this report. The
[evidence JSON](game_process_cpu_profile_2026_10_29.json) records settings,
provenance, results and estimates; raw outputs remain under
`studies/campaign/runs/game-cpu-profile-2026-10-29/`.

**Result: half of the game processes' CPU goes to the rules engine, about a
third to preparing the network's inputs and 7% to the Python search. Most of
the engine's cost is bookkeeping around the rules: an integrity check that
rereads the whole game history after every move, a new fingerprint of the
position, and a copy of the whole state. One search in five has a single legal
move; skipping those searches would save about 21% and, if the skip still draws
the random numbers the search would have used, change no move. Changes that
keep every move, die roll and search result could remove roughly 40–50%, or
50–60% with the one-move skip. None has been made yet, and the estimates need a
matched run. The run was limited by the GPU coordinator, not by game CPU, so
these savings alone would raise games per hour little at four games per
process; they pay off by letting more games run at once, while the one-move
skip and reusing the previous search's evaluations also cut the coordinator's
work.**

## Workload

The run repeated the settings of the 24.2-games-per-hour shared GPU run
([report](landing_plan_shared_gpu_2026_10_29.md)): 32 eleven-round games, seeds
1951–1982, eight game processes with four games each and one thread per game,
one coordinating process that evaluates every position on the GPU, 64
simulations per search, depth cap 16, hidden size 64, two message layers,
16,384 token buckets and no learning updates. It used commit `e8de23e`,
PyTorch 2.14 and Python 3.13.5, and inherited `MallocNanoZone=0` from the agent
session (see [the memory allocator](#the-memory-allocator)).

All 32 games completed, in 100 minutes. A game averaged 1,320 decisions, 133
chance events and 85,623 network evaluations. Peak charged memory was 9.9 GB.
The game threads' own CPU, 1,250 s per game (973–1,592 s), matches the game
processes' total CPU reported by the operating system to within 0.02%. The
instrumentation's share of that is at least 18 s (659 ns per wrapped call, 27.9
million calls per game); from the in-run cost of clock reads it is plausibly
25–35 s, though that was not measured.

## Where the CPU goes

| Per game, mean of 32 | CPU-s | Share | Range over games |
| --- | ---: | ---: | ---: |
| **Rules engine** (C++) | 619.6 | **49.6%** | 45.0–53.5% |
| – applying moves | 418.5 | 33.5% | |
| – listing legal moves | 114.4 | 9.2% | |
| – copying positions for search | 38.8 | 3.1% | |
| – resolving chance events | 35.4 | 2.8% | |
| – position keys, interrupt menus, status queries | 12.6 | 1.0% | |
| **Preparing network inputs** | 452.5 | **36.2%** | 33.3–39.7% |
| – observation snapshots (C++) | 136.1 | 10.9% | |
| – graph compiles (C++) | 113.4 | 9.1% | |
| – Python assembly (`prepare`, `numeric_input`) | 103.7 | 8.3% | |
| – other C++ exports | 99.3 | 7.9% | |
| **Python search** (`VectorMCTS`) | 92.5 | **7.4%** | 6.6–7.9% |
| Python adapter around the engine | 47.0 | 3.8% | 3.4–4.1% |
| Messaging | 19.6 | 1.6% | 1.3–1.7% |
| Game loop | 18.8 | 1.5% | 1.3–1.8% |

Each simulation starts from a new copy of the search's root and replays its
path, so a game applies about 218,000 moves for its 1,320 real ones and
resolves about 31,000 chance events for its 133 real ones. A move cost 1.9 ms,
a search copy 0.46 ms, and one evaluation's inputs about 5.1 ms of game-thread
CPU.

## Inside a move

Native samples of one game process, playing seeds 1966, 1972, 1973 and 1975,
show what a move costs. Shares are of the busy samples under `apply_action` in
each 30-second window:

| Part of applying a move | 600 s | 2,400 s | 4,000 s |
| --- | ---: | ---: | ---: |
| Integrity check (`State::validate`) | 16% | 26% | 41% |
| – of which rereading the history | 8% | 20% | 36% |
| Position fingerprint (`planningKey`: text and SHA-256) | 23% | 15% | 22% |
| Copying the engine, then destroying the old one | 15% | 11% | 17% |
| Rules, including phase ends | 45% | 47% | 20% |
| – of which the economy rules re-checking legality | 15% | 34% | 1% |
| Legality check and history record | <1% | <1% | <1% |

Over a game the rules themselves are only about a third of a move's cost
(33–37%):

- **The integrity check rereads the whole history.** After every move,
  `State::validate` checks the state's structure and then walks the payload of
  every event recorded since the game began (`src/campaign_state.cpp:457`).
  Recorded events never change and were checked when they were added. The walk
  grows with the game, from 8% of a move at 600 s to 36% at 4,000 s, and costs
  97–121 s per game.
- **Every move computes a new fingerprint**: 59–95 KB of canonical text hashed
  by a portable SHA-256, about 20% of a move. The M4 Max has SHA-256
  instructions; a scratch build that used them produced identical digests 5.8
  times faster.
- **Every move copies the whole engine** and then destroys the old one
  (`src/campaign_runtime.cpp:380`, `:393`), so that a failed move leaves the
  position unchanged: 14–15% of a move. 99.4% of moves are applied to search
  copies that are thrown away.
- **The economy rules re-check legality.** They regenerate their whole menu to
  check an action the engine has just matched against the authoritative menu
  (`src/economy.cpp:682-687`): 15%, 34% and 1% of a move in the three windows,
  about 54 s per game.
- The engine's own legality check costs under 1%.

Resolving a chance event has the same structure: at 600 and 4,000 s the check,
fingerprint and copy took 84% and 92% of `resolve_chance`, the dice themselves
under 0.1%. `CampaignEnv::cloneForSearch` copies the engine twice and discards
one copy (`src/campaign_env.cpp:97-101`); the second copy and the discard are
55% of a search copy.

## Legal moves listed twice

Listing legal moves (114 s) is mostly real work: 90% of its time generates
menus for positions the search reaches for the first time. But 61% of the calls
(133,000 per game) and 47% of the action snapshots (3.4 million) exist only
because `CampaignAdapter.apply_action` rebuilds the full menu, wrapping every
action in Python, to check the move at each inner tree node
(`studies/shared/campaign_adapter.py:179`). `Engine::step` then checks the same
move against its cached menu. The duplicate check costs 36–42 s per game,
mostly Python wrapping and freeing.

## Preparing network inputs

Each evaluation costs about 5.1 ms of game-thread CPU before the position goes
to the coordinator (5.3 ms counting the action snapshots made only to check
moves):

- **Observation snapshots (136 s, 1.6 ms each).** About 80–88% is copying and
  destroying the position's tree of about 3,000 JSON nodes, which is copied
  three times. Two copies come from building objects with C++ initializer
  lists, which always copy their contents (`src/campaign_env.cpp:89-92`,
  `src/campaign_state.cpp:353`); the third is `State::observation` copying the
  tree out of a constant reference (`src/campaign_state.cpp:380`). Half the
  samples are inside the memory allocator.
- **Graph compiles (113 s).** There is one per evaluation, for the observation
  graph of about 3,500 nodes. Action graphs are cached; the 1.8% compiled are
  mostly payloads never seen before (a simulation of 30 decisions per game did
  not rule out evictions over whole games). The time is spread over per-node
  cache lookups, token appends and locking of a cache shared by the process's
  threads. The lock alone is 11–15%, and 16% even with one thread. Python
  callbacks are at most 2.3%.
- **`prepare` (142 s with its C++ calls).** `shared_evaluator.prepare` loops
  over the menu in Python and makes three C++ calls per action graph: 82 s of
  Python and 60 s of array and reference exports. The part that grows with the
  menu is about 32 µs per legal action, with 44 actions on average.
  `numeric_input` adds 21 s of per-action Python bookkeeping.
- **Repeated positions.** Each decision starts a new search, and 25–30% of its
  evaluations (21–27% of their CPU) repeat positions the previous search
  evaluated. This was measured with stand-in evaluators.

## The Python search

The search's 92.5 s is mostly freeing memory rather than tree code:

- 35–42 s destroys each simulation's engine copy, two thirds of it freeing the
  position tree cached for the evaluated leaf;
- about 11.5 s frees each leaf's compiled graph;
- 5–20 s is Python's garbage collector, triggered mostly by new tree edges;
- the tree code itself is about 30 s (17–42 s, 2.4%); its largest part, about
  9–15 s, scores edges at each selection step.

About 17 s of the game loop's 18.8 s frees the previous decision's search tree.
Rewriting the tree code in C++ would save roughly 30–65 s per game (2–5%): the
tree code, most garbage collection and the Python part of freeing trees.
Freeing engine copies and graphs, about 50 s, is C++ work already and would
stay. Porting the adapter (47 s) as well, and searching without holding Python's
interpreter lock, could gain more, partly in wall time. None of this was
measured. It is comparable to single items below, such as hardware SHA-256
(40–42 s) or copying once (21 s), but much smaller than the engine changes
together (about 225–255 s) or the input changes together (about 195–275 s).

## Decisions with one legal move

246 of each game's 1,320 searches (18.6%) had a single legal move. They cost
260 CPU-s per game, 20.8% of game-thread CPU (17.1–25.2% per game), and made
about 15,900 evaluations (18.6%). Playing such a move without a search changes
nothing in the game, provided the skip still draws that decision's search seed
and its move-sampling random number, so that later searches keep the same
random streams. A search with one move always picks it, the recorded training
target is that move with probability 1, and value targets come from game
results. Search copies never use the game's dice. Search traces would lose
their statistics for those moves. With the shared GPU coordinator, the mix of
positions in a batch changes floating-point results slightly, so only a
deterministic evaluator can confirm identical games bit for bit.

Letting searches pass through one-move positions inside the tree without
evaluating them is a different change, because it alters what the search
computes. It would spend those evaluations on positions with a choice but cost
about 85–90 s more per game at 64 simulations, and it needs a strength test at
equal compute.

## The memory allocator

This agent session's environment sets `MallocNanoZone=0`, and the benchmark
harness passes its environment to the game processes. This run, and very likely
every run started from an agent session, therefore used macOS's older allocator
for small objects; a run started from a normal Terminal uses the default one.
The allocator's own code was 25–29% of the game threads' busy samples. Whole
random games through the engine used 20–23% less CPU with the default allocator
and ended in identical positions (seed 7: 4.99 against 3.86 s; seed 8: 4.47
against 3.56 s). Input steps took 7–48% less time with one thread. The effect
with eight game processes and the coordinator is untested. The profiler now
records the setting.

## What could be saved

Estimates are CPU-seconds per game out of 1,250, from in-run costs and native
sample shares; verifiers re-derived each one and reran the scratch tests.

These changes keep every move, die roll and search result:

| Change | CPU-s per game | Share | Risk and checks |
| --- | ---: | ---: | --- |
| Check only the history events a move adds | 97–121 | 8–10% | Very low; keep the full check when restoring games and in tests |
| Assemble each evaluation's menu arrays in one C++ call | 90–120 | 7–10% | Low; arrays must stay identical |
| Build the observation tree by moving values, not copying | 80–110 | 6–9% | Low; identical JSON |
| Apply moves in place on search copies | 67–70 | 5–6% | A copy that fails mid-move must refuse every later call |
| Hardware SHA-256 for the fingerprint | 40–42 | 3% | Low; identical keys |
| Let the engine's legality check cover tree moves | 36–42 | 3% | Low; identical stub searches, same errors for stale moves |
| Cheaper graph compiles (no shared lock, fewer lookups) | 25–45 | 2–4% | Native features must match Python's bit for bit |
| Copy once when copying for search | 21 | 2% | Very low |
| Smaller items: fingerprint text, action snapshots, `numeric_input`, edge scoring | 30–65 | 2–5% | Low; partly unmeasured |

Together these come to roughly 40–50% of game-process CPU. Each was estimated
alone, and per-call costs in the loaded run were 1.5–3.6 times the
single-threaded ones for substantial calls and far more for tiny ones, so only
a measurement can confirm the total.

Two more changes keep play unchanged but carry more risk:

- Skipping the economy re-check for actions the engine has just matched
  (47–63 s, 4–5%) relies on a guarantee between rule modules that holds in the
  current code but that nothing enforces. The check must stay for actions the rules
  build themselves, such as the approved rail purchase
  (`src/economy.cpp:703-704`).
- Reusing the previous search's evaluations (95–119 s today, 8–10%) returns the
  same network outputs, but the cache must be cleared whenever the weights
  change. It also removes about 25–30% of the coordinator's work today, less
  after the one-move skip (see the next section).

These need the user's decision:

- **Skip one-move searches:** 255–260 s (21%) today and 18.6% fewer
  evaluations. These seconds do not add to the first table's: once the nine
  changes make each search cheaper, the skip removes about a fifth of what
  remains (about 130–160 s), for about 50–60% in all.
- **Skip the rest of the integrity check on search copies:** about 30 s (2.4%)
  on top of checking only new history events, or about 130–150 s instead of
  it. Real moves stay checked, but rules bugs would go unnoticed on 99.4% of
  transitions.
- **Use the default allocator:** perhaps a fifth less CPU today, unmeasured
  under load, and less after the copy-removing changes above, which remove much
  of the allocation it speeds up. The harness should set the allocator
  explicitly either way, so runs started from different places stay comparable.

Not estimated in depth: keeping an engine copy at each expanded tree node
instead of replaying each simulation's path (about 2.6 moves per simulation)
could avoid about 60% of move applications at a memory cost; menu generation
itself has hot spots in the naval rules; and compiling the observation graph
directly from the state would save perhaps 3–6% for much more work.

## What this means for games per hour

The coordinator spent 88% of the run in model calls and waited for requests
only 2% of it, so it had almost no spare capacity. Of a game's wall time, 58%
went to waiting for evaluations, 23% to CPU and about 20% to neither, much of
it, by the native samples, waiting for Python's interpreter lock, which a
process's four game threads share. The game processes used 6.7 cores on average
and the coordinator 0.6.

Cutting game-process CPU alone will therefore not raise games per hour much at
four games per process. It makes room to run more games at once, which gives
the coordinator bigger batches. Timed alone in the earlier report, a model call
cost about 3 ms however small plus about 0.9 ms per position; in this run calls
averaged 4.0 positions and took 7.7 ms each. The earlier probe at six games per
process was slower because the games and the coordinator competed for cores; at
half the CPU per game they may not. Fewer handoffs of the interpreter lock could
also shorten games by more than their CPU share. Skipping one-move searches and
reusing evaluations cut the coordinator's work directly, but they overlap. About half the evaluations in
one-move searches repeat the previous search's, against 20–25% elsewhere, so
after the skip, reuse would save at most about 65–80 s of game CPU. Together
the two would cut at most about 35–40% of evaluations, not the 44–49% their sum
suggests. Each change needs a matched games-per-hour run.

## Limits

- This is one instrumented run, and its 20.1 games per hour is not comparable
  with the earlier 24.2. Game CPU per evaluation was 7% higher (14.6 against
  13.6 ms, the latter from
  `studies/campaign/runs/shared-gpu-2026-10-29/selfplay_8x4.mps.json`), and
  instrumentation explains at least a fifth of that; the rules commits since
  `b89e86d` were not measured separately. But the coordinator sets the pace,
  and its model calls took 14% longer (7.7 against 6.7 ms) on slightly smaller
  batches, which accounts for the 16% lower evaluation rate. Why they were
  slower was not measured. Other applications were running on the machine,
  including one that started 25 minutes into the run and used about 1.2 cores
  when checked afterwards.
- The native samples come from one process in three 30-second windows. Busy
  samples were about twice the measured CPU rate, so they show the make-up of
  CPU, not seconds. Costs tied to game phases vary widely between windows, so
  combined figures are ranges.
- Single-threaded micro-benchmarks ran 1.5–3.6 times faster per call than the
  loaded run, and other applications kept the machine's load average near 7
  during the analysis.
- Repeated-evaluation rates come from stand-in evaluators; a real network's
  trees may differ.
- No learning updates ran, and nothing here measures playing strength.

Reproduce from the repository root, one heavy job at a time (about two hours).
`MallocNanoZone=0` matches this run; leave it unset to measure the default
allocator.

```sh
MallocNanoZone=0 tmp/gpu-mps-env/bin/python tools/profile_game_process_cpu.py \
  --output studies/campaign/runs/NEW-RUN/profile.json \
  --seeds "$(python3 -c 'print(",".join(map(str, range(1951, 1983))))')" \
  --sample-at 600,2400,4000
```
