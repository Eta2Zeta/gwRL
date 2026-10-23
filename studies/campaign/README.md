# Regional campaign learning

This study uses the approved 1936 China campaign and the shared C++ engine.
Three separate entity-graph policy/value networks guide vector MCTS. A rollout
batch freezes all three policies; training then updates all three together.
Each policy learns choices made by its actual alliance, including reactions and
controlled minors. Every value target retains `[Axis, Allies, Comintern]`.

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

## Bounded foreground run and resume

The defaults are a small operational smoke: one batch, two independent games,
six real transitions per game, two simulations per search, and a small CPU model.
The one-round curriculum keeps the complete approved starting position and
rules, while ending after four national turns. A transition limit is separate:
unfinished games produce explicitly marked bootstrap targets. Neither is a full
July 1941 campaign result.

```sh
./.venv/bin/python -m studies.campaign.run train
```

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
Periodic checkpoints default to every four waves and after each update. A crash
can resume the latest completed checkpoint. The manifest and checkpoint are
replaced atomically; the checkpoint is the authority if a crash occurs between
those two replacements. New runs refuse a nonempty directory and default to
unique ignored `runs/` directories.

Checkpoints contain the live and frozen models, optimizer moments, replay,
pending samples, all active game states, declaration scheduling, all random
generators, counters, configuration, scenario/rule/schema fingerprints and
runtime source hashes. Resume rejects configuration, source or schema changes;
a changed implementation needs an explicit migration or a new run. Only load
trusted local Torch checkpoints produced by this runner. CPU thread count and
software versions are part of exact continuation compatibility.

## Evaluation and profiling

Held-out evaluation keeps the target weights fixed, turns root noise off, and
uses the same versioned scripted opponents both inside search and during actual
play. The two baseline styles buy, move, attack and make reactions. They are
simple controls, with no claim of expert play. Each side is evaluated separately.
Seeds must differ from the base run seed and every logged training episode seed.

```sh
./.venv/bin/python -m studies.campaign.run evaluate \
  --checkpoint studies/campaign/runs/YOUR_RUN/checkpoint.pt \
  --output studies/campaign/runs/YOUR_RUN/evaluation.json \
  --target all --seeds 1009,1013 --max-transitions 40
./.venv/bin/python -m studies.campaign.run profile \
  --checkpoint studies/campaign/runs/YOUR_RUN/checkpoint.pt \
  --output studies/campaign/runs/YOUR_RUN/profile.json --repeats 3
```

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

## Starting a larger experiment

No large experiment runs automatically. The small two-batch smoke took 14.30
seconds across stop/resume; 100 similar batches would take roughly 12 minutes
if position costs stayed comparable. The default larger model measured 247ms
per same-actor batch of four inference requests, before rules/search/updates.
These are small-menu CPU measurements, not a full-game duration estimate.

First inspect the smoke profile and choose a run size that fits foreground time
and memory. For the larger settings below, initially use one batch and six
transitions per batch (`--batches 1 --transitions-per-batch 6`), inspect the timing, then scale up
with a fresh run. A manual experiment command, to adjust after that pilot, is:

```sh
./.venv/bin/python -m studies.campaign.run train --full-campaign \
  --batches 10 --transitions-per-batch 32 --parallel-envs 4 \
  --simulations 8 --max-depth 16 --hidden-dim 64 --message-layers 2 \
  --token-buckets 16384 --batch-size 32 --replay-capacity 4096
```

This uses the unchanged eleven-round target. It may require many batches to
finish an episode; bootstrap provenance remains visible until a true terminal.
Measure completed games across held-out dice and opponent combinations before
making strategic claims. Archived opponent leagues, broader starting-position
curricula, direct-policy/PPO comparison and stronger settings are future
experiments, not results established by this operational gate.

See [M12 verification](/Users/home/Desktop/gwRL/docs/m12/README.md) and the
[full plan](/Users/home/Desktop/gwRL/docs/plans/japan_china_full_rules_plan.md).
