# Training studies

| Study | Entry point | Read |
| --- | --- | --- |
| [Regional campaign](campaign/README.md) | `python -m studies.campaign.run` | [How gwRL learns](../docs/design/README.md) |

Run commands from the repository root with `./.venv/bin/python`.

```text
studies/
  campaign/
    run.py                Training, resume, evaluation and profiling
    learning.py           Three frozen policies per batch, terminal targets, exact resume
    neural.py             Policy/value network over the zone encoding, batched evaluation
    features.py           The network's input: the engine's zone encoding
    episode_workers.py    Games played in separate processes
    shared_evaluator.py   One process evaluating positions for many game processes
    replay.py, viewer.py  Browser replays of recorded games
    runs/                 Ignored local checkpoints, progress and reports
  shared/
    campaign_adapter.py   Declaration offers around the native campaign environment
    multiplayer_mcts.py   Vector-valued search with explicit dice outcomes
    immutable_json.py     Frozen source snapshots shared by inference and replay
```

New training and diagnostic commands write into fresh, ignored `runs/` folders.
The composition and mini-Japan studies were removed on 2 November 2026; the
[project history](../docs/archive/README.md) records their results.
