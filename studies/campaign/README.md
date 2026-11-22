# Regional campaign learning

This study uses the approved 1936 China campaign and the shared C++ engine.
One policy/value network guides vector MCTS for all three alliances. It reads
the engine's fixed
[zone encoding](../../docs/design/README.md#5-how-a-decision-becomes-numbers) of a
decision, which names the alliance choosing: each of the 37 map zones has values
for fixed features, and messages travel along the map's borders
([network](../../docs/design/README.md#6-inside-a-network-brick-by-brick)). A
training iteration (a *batch* in the code and its flags) holds the network fixed
while its games play; a network update then trains it. Its policy learns every
alliance's choices, including reactions and controlled minors. Every value target
retains `[Axis, Allies, Comintern]`.
A decision with one legal action is played without a search or a network
evaluation, and still records its training sample.

The approved objective is the terminal wealth-gap vector. Intermediate rewards
are zero, gamma is one, and the network divides values by a positive scale
(default 100) for training, restoring raw units for search and reports. There are
no kill/purchase bonuses, clipping or alternating-player sign inversions.

Run commands from the repository root with the project virtual environment.
Rebuild the extension after C++ changes:

```sh
./.venv/bin/python setup.py build_ext --inplace --force
./.venv/bin/python -m studies.campaign.run --help
```

## Training runs and resume

The defaults are a small operational smoke: one training iteration, two independent games,
six real transitions per game, two simulations per search, and a small CPU model.
The one-round curriculum keeps the complete approved starting state and
rules, while ending after four national turns. A transition limit is separate:
unfinished games produce explicitly marked bootstrap targets. Neither is a full
July 1941 campaign result.

```sh
./.venv/bin/python -m studies.campaign.run train
```

Add `--complete-episodes` to play every game to its true end, with a training
iteration's networks held fixed until its last game ends (self-play that never
stops, below, changes them during the games instead). Each new training
iteration creates fresh games,
and every training sample receives an observed terminal target. A transition guard saves frozen pending work without
bootstrapping or updating and exits with code 2; increase only that guard when
resuming, with `--extend-episode-budget N`. `--calendar-rounds N` shortens the
game to N rounds and `--full-campaign` plays all eleven. Small model exports live
in `models/generation-000000.pt` and later generation files, starting before any
action or network update. `--max-episodes 10` with at least three training
iterations of four games finishes exactly ten games, in training iterations of
four, four and two.

The final line prints the new run directory. `progress.jsonl` is flushed after
each completed search wave and network update, with counters and each game's calendar
clock. In another terminal, use the actual printed path:

```sh
tail -f studies/campaign/runs/YOUR_RUN/progress.jsonl
```

Press Ctrl-C in the training terminal to finish the current search wave, save
`checkpoint.pt` and mark `manifest.json` interrupted. Resume in the foreground:

```sh
./.venv/bin/python -m studies.campaign.run train \
  --resume studies/campaign/runs/YOUR_RUN/checkpoint.pt
```

`--stop-after-waves 2` provides the same safe boundary for a bounded resume check.
An interrupted run exits with code 130; a completed run exits with code 0.
Full recovery checkpoints default to every 1,800 wall-clock seconds and orderly
shutdown. Network updates publish small model exports, without forcing full
recovery writes. An explicit `--checkpoint-every-waves N` overrides the timer for
controlled comparisons and recovery tests. A crash can resume the latest
completed recovery checkpoint. The manifest and checkpoint are
replaced atomically; the checkpoint is the authority if a crash occurs between
those two replacements. New runs refuse a nonempty directory and default to
unique ignored `runs/` directories.

Checkpoint bytes are flushed before replacement, and `checkpoint.pt.previous`
keeps the preceding complete snapshot. If the newest file is damaged, explicitly
resume that backup; the first recovery save preserves it instead of backing up
the damaged file. Abrupt interruption can lose games and network updates since
the latest recovery point. Saving models separately does not preserve Adam,
replay or in-progress games; that is the tradeoff for infrequent recovery saves.

Checkpoints contain the live and frozen models, optimizer moments, replay,
pending training samples, all active game states, declaration scheduling, all random
generators, counters, configuration, scenario/rule/schema fingerprints and
runtime source hashes. Resume rejects configuration, source or schema changes;
a changed implementation needs an explicit migration or a new run. Only load
trusted local Torch checkpoints produced by this runner. CPU thread count and
software versions are part of exact continuation compatibility. In self-play
that never stops a checkpoint is saved after a network update and holds no game
in play: those games are lost on a resume, which starts new ones.

## Game processes and the GPU

`--episode-workers P` plays each complete game in one of P processes, each with
its own interpreter lock; the main process keeps network updates, model exports
and checkpoints. `--games-per-process N` with `--episode-workers P` plays N games
in each of P processes for one training iteration, and an inference server in the
main process evaluates all their states together on `--neural-device` (`mps` for
the Apple GPU, `cuda` for an NVIDIA GPU). The inference batch a state lands in
changes its outputs in the last digits, so unlike one-state evaluation a game
need not repeat exactly from its seed. In either mode a game that fails
costs only that game, recorded with its seed in `failed_games`. A dead end or a
move that the engine accepted and then failed on also keeps its position in the
run's `failed-positions/` folder, and `tools/replay_failed_move.py` replays a
kept move in a fresh process
([running training on the Mac](../../docs/design/README.md#92-running-training-on-the-mac)).

An inference batch holds at most one state for each concurrent game, the
processes times the games in each, and on the GPU a larger inference batch costs
much less per state. At 256×8 on the Mac's GPU, 7 processes of 18 games, 126
concurrent games, played 33% more decisions an hour than 7 of 9, with 12.5 GB of
memory at the sampled peak instead of 8.0 GB
([record](../../docs/archive/records/concurrent_games_gpu_2026_11_18.md)).

`--compiled-forward` has the inference server run one network's zone and
position layers compiled by `torch.compile` for fixed numbers of states, each
inference batch padded with empty states to the next of them
([running training on the Mac](../../docs/design/README.md#92-running-training-on-the-mac)).
On saved inference batches it made the GPU forward pass of networks of 256×8
and larger 6% to 24% faster and the 64×2 network's slower. In training at 256×8
on the GPU it paid with 126 concurrent games, whose inference batches hold about
60 states: 7.9% more decisions an hour while playing than two runs without it,
which differed from each other by 6%
([record](../../docs/archive/records/compiled_layers_126_games_2026_11_18.md)).
With 63 concurrent games, about 24 states an inference batch, no gain was
established ([record](../../docs/archive/records/gpu_training_compiled_2026_11_18.md)).
Compiling costs up to a minute as a run starts, seconds once PyTorch has the
compiled code cached on disk; it is off unless given.

`--cpu-budget N` checks the run's busy cores against the allowance: one per game
process plus the inference server, or tensor threads plus parallel search
workers plus one inference server without worker processes. It counts and does not measure:
a game process of four games keeps more than one core busy
([Training on the Mac](#training-on-the-mac)).

Native campaign calls release Python's interpreter lock while executing pure C++
work. Each Python-facing environment protects its own operations with an
independent mutex; clones get separate mutexes, so different boards can run
native operations concurrently. Overlapping operations on one board remain
serialized. This is per-call protection, not a transaction across several calls
on a shared Python adapter; search workers own independent adapters. A
self-play decision's whole search is one such call
([native_search.py](native_search.py)): its simulations run on the search's own
copies of the board, and a game thread's native client
(`gwrl_cpp.InferenceClient`) writes each inference request into the thread's
shared memory and exchanges binary messages with the inference server through
the thread's pipe, as `include/game/inference_client.hpp` describes them. On
Windows, whose pipes are not file descriptors, `RemoteEvaluator` sends the same
messages from Python.

## Long unattended runs

Every run writes into its own folder under `studies/campaign/runs/`, which git
ignores. The folder is named by what the run is and the date it started, such
as `training-2026-11-22`; a training run that goes on in parts, each restarted
with new code or settings, keeps its parts inside, named by their order and
what they are, such as `training-2026-11-19/4-choice-b`. A run started by a
script keeps the script, the commit's files it ran (`code/`) and its logs in
that folder too, and nothing of it in `tmp/`. The
[list of runs](../../docs/archive/runs.md) says what each folder holds and
which record reports it, and gets a line when a run starts.

`tools/supervise_campaign_training.py` runs training under a fixed active-time
budget, with bounded retries and graceful memory and deadline stops. It reserves
its own core within the owner's allowance of nine cores (`CORE_ALLOWANCE`): the
Mac has ten performance cores, and one stays free for everything else.
`--all-cores` uses every core when the owner allows it.

Every second the supervisor adds up the memory of the run's processes
(`aggregate_rss`). It asks the run to stop safely when that sum comes within
1 GB of the run's allowance of 30 GB, and kills the run at 30 GB. On macOS it
also watches the memory of the whole Mac, which the run shares with every other
program (`machine_memory`). It asks the run to stop safely when macOS's memory
pressure stays critical for 10 seconds, or when the swap in use grows by 4 GB
above its level when the supervisor started the training process. The 4 GB are
the limit of the watchdog script that stopped the second 378-game run of 19
November 2026, whose swap had grown by 4.1 GB in 38 minutes; while all its games
played, that run played about 10% fewer decisions an hour than 252 games
(inferred;
[record](../../docs/archive/records/concurrent_games_cpp_search_2026_11_19.md#the-378-game-runs)).
A run stopped for the Mac's memory, whichever program used it, has the status
`machine_memory_short` in the supervisor's `state.json`. The stop's
`graceful_stop_requested` event there gives the cause (`critical_pressure` or
`swap_growth`), the pressure and the swap, and the same command resumes the run
from its checkpoint.

A game process that dies, for example in a crash of the engine or the search,
costs only its own games. The games it had not finished become failed games in
`manifest.json` (`failed_games`), each naming the dead process and the signal or
exit code that ended it, and a new game process takes its game slots while the
others play on; the training process's log says which process died and which
took its place. A game process that dies before it has finished any game stops
the run instead, since a new one would most likely die the same way
([running training on the Mac](../../docs/design/README.md#92-running-training-on-the-mac)).
For looking into a crash the run keeps, in its run folder:

- `game-moves/`: the move log of each game the dead process had in play, named
  in its failed game's record, which `tools/replay_game_moves.py` replays to the
  game's position and whose last searches it can run again;
- `crash-reports/`: macOS's crash report of the dead process, with every
  thread's native stack, as `game-process-PID.ips`;
- the attempt's standard error log: every game thread's Python stack at the
  crash, and macOS's allocator message with the address, which the supervisor
  has macOS write there (`MallocDebugReport=stderr`).

The defect behind the six game process crashes of 20 and 21 November 2026 is not found,
also not by the sanitizer runs of 21 November
([record](../../docs/archive/records/crash_diagnosis_2026_11_21.md)) nor by 21.2
hours of training play whose game processes ran under AddressSanitizer
([record](../../docs/archive/records/memory_check_2026_11_21.md)).

### Training on the Mac

`--profile mac` gives the supervisor the setup measured on this Mac, kept in
[profiles/mac.json](profiles/mac.json): PyTorch 2.14 from `tmp/gpu-mps-env`
(built from `requirements-gpu-mps.txt`), six game processes of four games
each, whose states one inference server evaluates on the CPU, the 30 GB
memory limit, the faster memory allocator and keeping the Mac awake. The
supervisor counts one core per game process, one for the inference server and one
for itself, but a process of four games keeps 1.2 to 1.5 cores busy. So the
layout was chosen by the load it puts on the Mac: on 15 November 2026 these six
processes kept about 9 cores busy, the allowance, and played about 192,000
decisions an hour while playing; seven, which also fit the count, kept about 10
busy ([record](../../docs/archive/records/nine_core_layouts_2026_11_15.md)).
Since the engine work of 16 November the six keep about 7 cores busy and play
about 301,000 decisions an hour while playing, the inference server setting the pace
([record](../../docs/archive/records/engine_speed_in_training_2026_11_16.md)).
Evaluating on the GPU instead played half as many games an hour on 2 November
2026, with the eight game processes of the 12-core allowance then (58.7
against 124): the zone network is so cheap per state that the GPU's cost per
forward pass outweighs its speed. Flags after `--` win over the profile, and the
learning settings stay there:

```sh
./.venv/bin/python tools/supervise_campaign_training.py --profile mac \
  --control-dir studies/campaign/runs/NAME-control --run-dir studies/campaign/runs/NAME \
  --seconds 28800 -- --calendar-rounds 11 --complete-episodes --batches 1000 \
  --simulations 16 --kept-simulations 256 --sampling-game-rounds 1 --max-depth 16 \
  --hidden-dim 64 --message-layers 2 --batch-size 32 --epochs 525 \
  --replay-capacity 8000 --sample-fraction 0.05 --transitions-per-batch 20000
```

A decision is kept as a training sample or not before its search: a kept
decision is searched with `--kept-simulations` 256 and exploration noise, any
other with `--simulations` 16 and none, only to choose the move. Self-play draws
its move from the visit shares in the first `--sampling-game-rounds` game
rounds, here 1, and plays the most visited action after them. This is the
owner's answer to Q-016 of 22 November 2026; the long run before it searched
every decision with 64 simulations and drew every move
([the move played](../../docs/design/README.md#45-after-the-simulations-visit-shares-and-the-move-played),
[which decisions are kept](../../docs/design/README.md#71-a-training-iterations-games)).
No run has used these settings yet.

These learning settings are the speed test's, not tuned values. A training
iteration plays the 24 games the profile plays at once (`--batches` counts
training iterations); with 525 training steps a network update draws each kept
training sample as often as the 700 training steps did with the 32 games of the
eight game processes before 15 November 2026. With more games at once, as the
252 of the long run on the GPU, a network update follows that many games. With
5% of decisions and 8,000 training samples its training steps then drew from
only the latest 110 games or so, which the network fit much better than new
games, so since 20 November 2026 the long run keeps 1% of each game's decisions
and 25,000 training samples, those of about 1,700 games
(`--sample-fraction 0.01 --replay-capacity 25000`;
[how often a training sample is drawn](../../docs/design/README.md#87-how-often-a-training-sample-is-drawn)). `--batch-size` is the minibatch
size and `--epochs` the number of training steps per network update. Repeat the same command to resume. Another
machine gets its own file beside `mac.json`.

The Mac profile runs *self-play that never stops* (`"continuous": true`, the flag
`--continuous`). Its 24 game threads play one game after another. After every 24
games that end, a network update runs beside them, on a thread of the inference
server's process, and when it is done every game takes up the new networks
between two inference batches
([the training loop](../../docs/design/README.md#91-the-training-loop)). A
training iteration is then those 24 games and their network update, and
`--batches` counts network updates. Stopping a run, by a signal,
`--stop-after-waves` or `--batches`, loses the games then in play. It needs
`--games-per-process`. With `--neural-device mps` or `cuda` the network update
trains on the GPU beside the inference server, which meanwhile runs the layers
as written instead of `--compiled-forward`'s
([running training on the Mac](../../docs/design/README.md#92-running-training-on-the-mac)).
The supervisor counts a core for the network updates, so the Mac's allowance
leaves six game processes. `--no-continuous` alternates instead, as the Windows
profile does. On 17 November 2026, in two
matched pairs of runs of four network updates, it played 6.5% and 12.5% more
decisions per wall-clock hour in steady play than alternating training
iterations ([record](../../docs/archive/records/self_play_never_stops_2026_11_17.md)).
On the Mac's GPU at 256×8, with 6 processes of 21 games and
`--compiled-forward`, it answered 8.7% more network evaluations per wall-clock
second than alternating training iterations at the same layout
([record](../../docs/archive/records/never_stops_gpu_2026_11_18.md)).

One network serves all three alliances by default (`--networks one`). The
input tells it which alliance is choosing; its policy learns from every
decision, the inference server evaluates every state with it in a forward pass
of one network, and checkpoints and model exports hold it once. `--networks
three` keeps a network for each alliance instead, each policy learning from its
own alliance's decisions
([one training step](../../docs/design/README.md#84-one-training-step-and-one-network-update)).
In self-play that never stops, each finished game is first scored by the
networks then serving, before its training samples join the replay buffer:
each network update's entry in `manifest.json` holds, under `fresh_games`, for
each alliance the training samples, the value loss summed over them, and the
policy's cross-entropy and KL divergence against the search's visit shares
(`fresh_game_losses` in `learning.py`), and each game's own sums under
`fresh_losses`. Divided by the training samples, these are the losses of
[the loss](../../docs/design/README.md#81-the-loss) on games the networks have
not trained on. `tools/compare_training_runs.py` compares runs by them, per hour
of active time, and puts each value loss beside the variance of the games'
final scores, which differs between runs whose games differ; it also compares
runs' decisions per hour and their held-out evaluation games.
`tools/rate_replay_samples.py RUN` rates the training samples in a run's last
checkpoint the same way, one by one, with the run's own copy of the code: each
alliance's values by game round, beside a linear model of the same input
fitted on other games, and the search's visit shares by number of legal actions
and kind of decision. `tools/train_on_saved_samples.py RUN --start N --weights
...` trains copies of generation N on four fifths of those games, at each weight
of the value loss, and rates the other fifth as it goes: a cheap test of a
training change on fixed data before a run.

`--sample-fraction F` keeps that share of a worker game's decisions as training
samples, from its own random stream, so the games play the same.
`--no-new-batch-after EPOCH` finishes the running training iteration and ends
the run as completed; in self-play that never stops it starts no game after that
time, and the run ends once the games in play have ended and a network update
has trained on them. `--initial-models EXPORT` starts a fresh run from an export's weights
and nothing else of that run, even if the sources have changed since, so a run
stopped by a bug continues from its latest networks after the fix.
`tools/record_campaign_games.py` plays recorded games from a model export, each in
its own process, for the Campaign Observatory.

### Training on Windows

`--profile windows` gives the supervisor the setup in
[profiles/windows.json](profiles/windows.json): an 8-core PC with an NVIDIA GPU,
six game processes of four games each, whose states the inference server
evaluates with CUDA, 7 cores for training and one for the supervisor, a 12 GB
memory limit and keeping the PC awake. Its software: Visual Studio 2022 Build
Tools with the C++ workload, and a Python 3.13 environment at `~/.venvs/gwrl`
built from `requirements-gpu-cuda.txt`, PyTorch 2.14 for CUDA 12.6. Build the extension with
`python setup.py build_ext --inplace`; MSVC reads the sources as UTF-8, and
`.gitattributes` keeps every text file's line endings LF, which the engine's
data fingerprints need. That checkout syncs through OneDrive, so the environment
and the run directories live outside it. Use the Mac's command with
`--profile windows`: both machines play 24 games a training iteration.

The supervisor holds the trainer and every process it starts in a Windows job
object. A safe stop is a Ctrl+Break to the trainer's console process group,
which Python receives as `SIGBREAK`, so start the supervisor from a console
window; Ctrl+Break or Ctrl+C there stops the supervisor and saves the run.

On the night of 14 November 2026 this PC trained on three-round games and made
48,551 decisions an hour while playing
([record](../../docs/archive/records/three_round_training_2026_11_14.md)). Its
inference server, on the GPU, evaluated inference batches of about ten states
and waited for inference requests only 5.6% of the time, so the inference
server probably set the pace. The
profile lists the earlier measurements.

## The network's input and the order interface

The network's input is built in C++ by the engine's zone encoder. Reports name
the input layout in `software.network_input`. Checkpoints and exports of the
earlier graph-input network cannot be loaded.

Self-play uses the versioned [AI order interface](../../docs/engine/README.md#3-states-and-actions)
by default. Fleet and screening selection make forward progress; undo/cancel
editing is kept in the ordinary game API. Unchanged role/deck configuration
cycles and repeated declined railway requests are also bounded. Finished
battles [clear themselves](../../docs/engine/land_combat.md#6-finished-battles)
instead of waiting for a click. Context and checkpoint compatibility identify
`campaign-orders-v2`; old replay/optimizer state is not implicitly migrated, and
`campaign-orders-v1` recordings are rejected. Recordings from before the
training interface select the ordinary game interface for exact verification.

## Watch self-play

The [Campaign Observatory](../../web/campaign_viewer/README.md)
shows the actual game on the printed China campaign map, with playback, location
inspection, dice, wealth and the search alternatives behind each choice.
Add `--record-replay` to a fresh training command, then run
`python -m studies.campaign.viewer --live-trace PATH_TO_RUN/replay.jsonl` and
enable **Follow latest**. Recording is optional and ordinary checkpoint resume
is unchanged; recording during resume is currently unsupported. Exported JSON
and standalone HTML can be reopened without running search or learning.

## Evaluation and profiling

Held-out evaluation keeps the target weights fixed, turns root noise off, and
uses the same versioned scripted opponents both inside search and during actual
play. The two baseline styles buy, move, attack and make reactions. They are
simple controls, with no claim of expert play. Each side is evaluated separately.
Seeds must differ from the base run seed and every logged training episode seed;
without `--seeds` the command plays the 24 held-out seeds of `HELDOUT_SEEDS` in
`evaluation.py`, the primes from 1009 to 1163. Each search plays its most
visited action: among actions with as many visits, the one whose simulations'
average result is best for the alliance choosing, then the one with the higher
prior, then the first by identifier (`most_visited_index` in
`studies/shared/multiplayer_mcts.py`; self-play draws among actions still tied).
Evaluation accepts small model exports directly, without constructing a learner
or restoring its optimizer, replay and active games. Profiling retained
states uses a full recovery checkpoint.

```sh
./.venv/bin/python -m studies.campaign.run evaluate \
  --checkpoint studies/campaign/runs/YOUR_RUN/models/generation-000001.pt \
  --output studies/campaign/runs/YOUR_RUN/evaluation.json \
  --target all --seeds 1009,1013 --max-transitions 40
./.venv/bin/python -m studies.campaign.run profile \
  --checkpoint studies/campaign/runs/YOUR_RUN/checkpoint.pt \
  --output studies/campaign/runs/YOUR_RUN/profile.json --repeats 3
```

The default evaluation also stops collection after 20 visits to one full planning
state. This is reported as `repeated_state_guard`, an unfinished game with no
terminal score; changing search seeds or future dice might still allow escape.
The Python evaluation API can disable it with `max_state_visits=None`.

The evaluation budget is per game. Increase it explicitly to reach real terminal
states. Truncated games report their snapshot wealth and calendar, but contribute
no observed terminal returns, terminal wealth intervals or value-calibration
errors. Reports include all wealth components, territorial control, removed-unit
casualties, decisions by actor, throughput, inference batches and approximate
uncertainty for completed games. A few games do not establish strength.
For baseline-versus-baseline controls add `--target-script balanced` or `cautious`.

Profiling measures cloning, rule transitions, legal actions, observation/context,
and scalar/batched inference on actual retained states. Rule transitions use
clones and the report checks that live state and execution RNG are unchanged.
It includes first-use parsing and warm calls; menu size and game phase matter.

The [project history](../../docs/archive/README.md) records the earlier pilots, the
three-round experiment and the performance work, and the
[full plan](../../docs/plans/japan_china_full_rules_plan.md) the approved campaign.
