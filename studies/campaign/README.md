# Campaign workflow

For project progress, start with the [project guide](../../docs/README.md).
For achieved results and limits, read [learning status](../../docs/learning.md).
This page covers current operation; dated measurements live in the
[Stage A archive](../../docs/archive/stage_a/README.md).

Run commands from the repository root with the project virtual environment.
Rebuild native bindings after C++ changes using the [development guide](../../docs/development.md).

## Configure a run

```sh
./.venv/bin/python -m studies.campaign.run train --help
```

The plain `train` default is a bounded smoke: one-round horizon, two independent
games, six real transitions per game, two simulations per search and a small CPU
model. Its unfinished segments use explicitly marked bootstrap targets. It is not
a completed-game runtime or learning-strength estimate.

Use `--complete-episodes` for terminal-only learning. Each collection batch freezes
all three policies and finishes its games before updating. An execution guard
saves pending work and exits with code 2 without bootstrapping or updating. Only
an explicit `--extend-episode-budget N` may enlarge that transition guard during
resume. `--max-episodes N` sets an exact completed-game target, with a smaller final
batch when necessary; that tail changes random-stream interleaving.

`--calendar-rounds 3` selects three full CCP–Mongolia–Japan–KMT rounds.
`--full-campaign` retains the eleven-round July 1941 endpoint. A search simulation
is a bounded exploration from a position; `--max-depth` counts simulated action
or chance transitions. It does not set the game's calendar length.

`--cpu-budget N` checks tensor threads, search workers and one coordinator.
Keep aggregate usage within **12 CPU cores and 30,000,000,000 bytes**, including
all processes. Limit BLAS threads in the shell, for example:

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
```

`--neural-device` chooses CPU/MPS/CUDA tensor evaluation independently of the game
engine. The complete self-play backend is currently CPU; Apple GPU components
and their requirements are documented in the [GPU guide](../../docs/gpu/README.md).
Measure representative games/search and peak memory before increasing a run.

## Run and observe

```sh
./.venv/bin/python -m studies.campaign.run train
```

The final line prints the new ignored run directory. New runs refuse nonempty
directories. Flushed `progress.jsonl` records each search wave/update, game clocks,
action summaries, terminal flags and final returns. Substitute the actual path:

```sh
tail -f studies/campaign/runs/YOUR_RUN/progress.jsonl
```

`manifest.json` separates collection/search, updates, recovery saves, model
exports and reporting time. RSS means resident set size: memory occupied by a
process. Supervisors sum sampled process RSS, sometimes counting shared pages
more than once and possibly missing brief peaks; it is an estimate.

For a previously supervised experiment, use its immutable `pipeline-plan.json`
and saved `resume.sh`, which select its frozen runtime and retain deadline/resource
accounting. [The pipeline controller](../../tools/run_three_round_experiment.py)
handles initial evaluation, supervised training and paired final evaluation.
[The standalone supervisor](../../tools/supervise_campaign_training.py) supports
bounded retries and graceful resource/deadline stops. Do not restart a historical
experiment with a fresh deadline or bypass compatibility checks.

## Save and resume

Press Ctrl-C to finish the current search wave, save `checkpoint.pt` and mark the
run interrupted (exit 130). `--stop-after-waves N` uses the same safe boundary.
An ordinary completed run exits 0.

```sh
./.venv/bin/python -m studies.campaign.run train \
  --resume studies/campaign/runs/YOUR_RUN/checkpoint.pt
```

Full recovery saves default to every 1,800 wall-clock seconds plus orderly
shutdown. `--checkpoint-every-waves N` explicitly overrides the timer for controlled
checks. Files are flushed and atomically replaced; the checkpoint is authoritative
if the manifest replacement is interrupted. `checkpoint.pt.previous` retains the
preceding complete snapshot. Explicitly resume it if the latest file is damaged;
the first new save preserves that valid backup. A crash can lose progress since
the last recovery save.

Recovery files contain live/frozen models, Adam optimizer moments, replay,
unfinished boards, pending samples, declaration scheduling, counters, all random
states and source/configuration/scenario/rule/schema fingerprints. Exact resume
rejects incompatible changes, including CPU thread/software compatibility.
Only load trusted local Torch files. A changed implementation requires a proved
migration or a new experiment, not retagging saved samples.

Small `models/generation-*.pt` exports are published after updates, starting at
generation zero before play. They preserve networks for evaluation, not optimizer,
replay or unfinished games. `initial.pt` retains the original empty learner.

## Evaluate and profile

Evaluation freezes the target model, disables root noise and uses versioned fixed
opponents inside search and actual play. Choose held-out seeds disjoint from the
base training seed and every logged episode seed. Evaluate network-only and
search separately; the supervised pipeline supports their paired comparison.

```sh
./.venv/bin/python -m studies.campaign.run evaluate \
  --checkpoint studies/campaign/runs/YOUR_RUN/models/generation-000001.pt \
  --output studies/campaign/runs/YOUR_RUN/evaluation.json \
  --target all --seeds 1009,1013 --max-transitions 40
./.venv/bin/python -m studies.campaign.run profile \
  --checkpoint studies/campaign/runs/YOUR_RUN/checkpoint.pt \
  --output studies/campaign/runs/YOUR_RUN/profile.json --repeats 3
```

The 40-transition example is bounded. Evaluation budgets are per game; increase
explicitly when actual completion is intended. The default repeated-state guard
stops after 20 visits to one complete planning state and reports an unfinished
game. Truncations retain snapshot wealth and clocks but have no observed terminal
return, terminal wealth interval or value-calibration error. Report completion,
new territory/IPP, unit losses and terminal wealth; small samples and better score
prediction alone do not establish playing improvement. `--target-script` runs
scripted controls. These opponents are baselines, not expert players.

Model exports evaluate without restoring the learner; legacy recovery files use
full compatibility-checked restoration. Profiling retained positions requires a
recovery checkpoint. It times clone, rules, legal menus, observations/context and
inference using retained states and verifies unchanged live state and RNG.

## Watch games

Add `--record-replay` to a fresh run, then use:

```sh
./.venv/bin/python -m studies.campaign.viewer \
  --live-trace studies/campaign/runs/YOUR_RUN/replay.jsonl
```

The [Campaign Observatory](../../web/campaign_viewer/README.md) displays the board,
dice, wealth and recorded search alternatives. Enable **Follow latest** for live
playback. Recording during resume is currently unsupported. Exported JSON and
standalone HTML can be reopened without running search or learning.
