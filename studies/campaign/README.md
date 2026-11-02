# Regional campaign learning

This study uses the approved 1936 China campaign and the shared C++ engine.
Three separate policy/value networks guide vector MCTS. Each reads the engine's
fixed [zone encoding](../../docs/stage_a/zone_encoding_2026_11_02.md) of a
decision: the 37 map zones answer fixed questions, and messages pass along the
map's borders ([network](../../docs/stage_a/zone_network_2026_11_02.md)). A rollout
batch freezes all three policies; training then updates all three together.
Each policy learns choices made by its actual alliance, including reactions and
controlled minors. Every value target retains `[Axis, Allies, Comintern]`.
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

The defaults are a small operational smoke: one batch, two independent games,
six real transitions per game, two simulations per search, and a small CPU model.
The one-round curriculum keeps the complete approved starting position and
rules, while ending after four national turns. A transition limit is separate:
unfinished games produce explicitly marked bootstrap targets. Neither is a full
July 1941 campaign result.

```sh
./.venv/bin/python -m studies.campaign.run train
```

Add `--complete-episodes` to freeze a batch until each game reaches its true
endpoint. Each new batch creates fresh games, and every row receives an observed
terminal target. A transition guard saves frozen pending work without
bootstrapping or updating and exits with code 2; increase only that guard when
resuming, with `--extend-episode-budget N`. `--calendar-rounds N` shortens the
game to N rounds and `--full-campaign` plays all eleven. Small model exports live
in `models/generation-000000.pt` and later generation files, starting before any
action or update. `--max-episodes 10` with at least three batches of four games
finishes exactly ten games, in batches of four, four and two.

The final line prints the new run directory. `progress.jsonl` is flushed after
each completed search wave and update, with counters and each game's calendar
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
shutdown. Learning updates publish small model exports, without forcing full
recovery writes. An explicit `--checkpoint-every-waves N` overrides the timer for
controlled comparisons and recovery tests. A crash can resume the latest
completed recovery checkpoint. The manifest and checkpoint are
replaced atomically; the checkpoint is the authority if a crash occurs between
those two replacements. New runs refuse a nonempty directory and default to
unique ignored `runs/` directories.

Checkpoint bytes are flushed before replacement, and `checkpoint.pt.previous`
keeps the preceding complete snapshot. If the newest file is damaged, explicitly
resume that backup; the first recovery save preserves it instead of backing up
the damaged file. Abrupt interruption can lose games and learning updates since
the latest recovery point. Saving models separately does not preserve Adam,
replay or in-progress games; that is the tradeoff for infrequent recovery saves.

Checkpoints contain the live and frozen models, optimizer moments, replay,
pending samples, all active game states, declaration scheduling, all random
generators, counters, configuration, scenario/rule/schema fingerprints and
runtime source hashes. Resume rejects configuration, source or schema changes;
a changed implementation needs an explicit migration or a new run. Only load
trusted local Torch checkpoints produced by this runner. CPU thread count and
software versions are part of exact continuation compatibility.

## Game processes and the GPU

`--episode-workers P` plays each complete game in one of P processes, each with
its own interpreter lock; the main process keeps learning updates, model exports
and checkpoints. `--games-per-process N` with `--episode-workers P` plays N games
in each of P processes for one batch and evaluates all their positions together
in the main process on `--neural-device` (`mps` for the Apple GPU). A position's
batch changes its outputs in the last digits, so unlike one-position evaluation
a game need not repeat exactly from its seed. In either mode a game that fails
costs only that game, recorded with its seed in `failed_games`.

`--cpu-budget N` checks the run's busy cores against the allowance: one per game
process plus the coordinator, or tensor threads plus parallel search workers
plus one coordinator without worker processes.

Native campaign calls release Python's interpreter lock while executing pure C++
work. Each Python-facing environment protects its own operations with an
independent mutex; clones get separate mutexes, so different boards can run
native operations concurrently. Overlapping operations on one board remain
serialized. This is per-call protection, not a transaction across several calls
on a shared Python adapter; search workers own independent adapters.

## Long unattended runs

`tools/supervise_campaign_training.py` runs training under a fixed active-time
budget, with bounded retries and graceful memory and deadline stops. It reserves
its own core within the twelve-core allowance; `--all-cores` uses every core
when the owner allows it.

### Training on the Mac

`--profile mac` gives the supervisor the setup measured on this Mac, kept in
[profiles/mac.json](profiles/mac.json): PyTorch 2.14 from `tmp/gpu-mps-env`
(built from `requirements-gpu-mps.txt`), eight game processes of four games
each, whose positions one coordinating process evaluates on the CPU, 11 of the
12 allowed cores for training and one for the supervisor, the 30 GB memory
limit, the faster memory allocator and keeping the Mac awake. On 2 November 2026
that played 124 eleven-round games per hour with learning, twice the same layout
evaluating on the GPU (58.7): the zone network is so cheap per position that the
GPU's cost per call outweighs its speed. Flags after `--` win over the profile,
and the learning settings stay there:

```sh
./.venv/bin/python tools/supervise_campaign_training.py --profile mac \
  --control-dir studies/campaign/runs/NAME-control --run-dir studies/campaign/runs/NAME \
  --seconds 28800 -- --calendar-rounds 11 --complete-episodes --batches 1000 \
  --simulations 64 --max-depth 16 --hidden-dim 64 --message-layers 2 \
  --batch-size 32 --epochs 700 --replay-capacity 8000 --sample-fraction 0.05 \
  --transitions-per-batch 20000
```

These learning settings are the speed test's, not tuned values. Repeat the same
command to resume. Another machine gets its own file beside `mac.json`.

`--sample-fraction F` keeps that share of a worker game's decisions as training
samples, from its own random stream, so the games play the same.
`--no-new-batch-after EPOCH` finishes the running batch and ends the run as
completed. `--initial-models EXPORT` starts a fresh run from an export's weights
and nothing else of that run, even if the sources have changed since, so a run
stopped by a bug continues from its latest networks after the fix.
`tools/record_campaign_games.py` plays recorded games from a model export, each in
its own process, for the Campaign Observatory.

## The network's input and the order interface

The network's input is built in C++ by the engine's zone encoder. Reports name
the input layout in `software.network_input`. Checkpoints and exports of the
earlier graph-input network cannot be loaded.

Self-play uses the versioned [AI order interface](../../docs/stage_a/action_interface_2026_10_24.md)
by default. Fleet and screening selection make forward progress; undo/cancel
editing is kept in the ordinary game API. Unchanged role/deck configuration
cycles and repeated declined railway requests are also bounded. Finished
battles [clear themselves](../../docs/stage_a/battle_clearing_2026_10_31.md)
instead of waiting for a click. Context and checkpoint compatibility identify
`campaign-orders-v2`; old replay/optimizer state is not implicitly migrated, and
`campaign-orders-v1` recordings are rejected. Recordings from before the
training interface select the ordinary game interface for exact verification.

## Watch self-play

The [Campaign Observatory](../../web/campaign_viewer/README.md)
shows the actual game on a geographic schematic, with playback, location
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
Seeds must differ from the base run seed and every logged training episode seed.
Evaluation accepts small model exports directly, without constructing a learner
or restoring its optimizer, replay and active games. Profiling retained
positions uses a full recovery checkpoint.

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
uncertainty for completed games. Very small samples do not establish strength.
For baseline-versus-baseline controls add `--target-script balanced` or `cautious`.

Profiling measures cloning, rule transitions, legal actions, observation/context,
and scalar/batched inference on actual retained states. Rule transitions use
clones and the report checks that live state and execution RNG are unchanged.
It includes first-use parsing and warm calls; menu size and game phase matter.

The [project history](../../docs/history.md) records the earlier pilots, the
three-round experiment and the performance work, and the
[full plan](../../docs/plans/japan_china_full_rules_plan.md) the approved campaign.
