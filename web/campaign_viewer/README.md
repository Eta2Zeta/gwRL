# Campaign Observatory

A local browser view of the 1936–1941 China campaign. It displays the actual
recorded game: territory possession, units, facilities, construction, battles,
dice, cash and wealth. The decision panel separately shows the alternatives
considered by stochastic MCTS. Network value estimates are score predictions,
not measured win rates.

The map is a geographic schematic of all 37 scenario locations, with optional
connections taken from scenario data. It is not a tracing of the printed board.
Click a location to inspect it; use +/− to zoom and drag the zoomed map to pan.
The reset button restores the whole map. Use the timeline, arrows, play button
and speed selector to browse events. Home/End jump to the first/last position.

## Watch a recorded run

Add `--record-replay` to a **fresh** foreground training command:

```sh
./.venv/bin/python -m studies.campaign.run train \
  --run-dir studies/campaign/runs/YOUR_NEW_RUN --record-replay
```

In a second terminal, start the viewer after `replay.jsonl` exists:

```sh
./.venv/bin/python -m studies.campaign.viewer \
  --live-trace studies/campaign/runs/YOUR_NEW_RUN/replay.jsonl
```

Open the printed local URL and enable **Follow latest**. The viewer checks for
new complete records every two seconds; unchecking it lets you inspect an older
position. Refresh preserves your current position. `--root 1` selects the second
parallel game; `--episode 1` selects that root's second episode. These indices
start at zero. The viewer follows the selected episode, rather than silently
jumping into another game.

Recording is optional and disabled by default. It captures only actual-game
transitions, selected actions, root search statistics and already resolved dice.
It does not serialize every imagined search branch or expose future dice. The
live viewer maintains its own replay environment and applies newly recorded
transitions once; it never searches or updates networks. Normal unrecorded
training does no replay serialization or inspection-history work. Recording
adds disk writes and recorded search menus; use it on a sample of training runs.

`--resume --record-replay` is currently rejected to preserve existing trace
prefixes. Ordinary checkpoint resume is unchanged. Start a fresh recorded run
when inspecting a new game. An interrupted trace remains inspectable through
its last complete record, with its incomplete status visible.

## Save and reopen a game

Export an opt-in stream without rerunning search or training:

```sh
./.venv/bin/python -m studies.campaign.replay \
  --trace studies/campaign/runs/YOUR_RUN/replay.jsonl \
  --root 0 --episode 0 --output output/campaign_viewer/replays/game.json
./.venv/bin/python -m studies.campaign.viewer \
  --replay output/campaign_viewer/replays/game.json
```

The exporter also accepts `--report` for a scaling benchmark's report plus its
adjacent `.trace.jsonl`. Fixed-position search reports are not game replays and
are rejected. Frozen-policy benchmarks are labeled separately from training.
Historical training checkpoints cannot reconstruct missing choices/search
statistics; the viewer does not invent them.

Exports verify compatible task/rules and static context, legal menus and chosen
actions, each recorded state identity, the initial execution RNG, and recorded
past dice when available. Benchmark exports verify the complete serialized
state/RNG hash at every transition. Source changes are rejected when they affect
authoritative replay files, unless explicitly allowed with
`--allow-source-drift`; that flag records differences and still requires exact
transition replay and compatible rules. It does not migrate old rules.

To create a portable page that works without a server:

```sh
./.venv/bin/python -m studies.campaign.viewer \
  --replay output/campaign_viewer/replays/game.json \
  --export-html output/campaign_viewer/game.html
```

Open that HTML in a browser. CSS, JavaScript and the recording are embedded;
there are no CDN dependencies. Open recording also imports exported JSON locally
in the browser. Exported files preserve existing destinations rather than
overwriting them. Generated replay files stay under ignored local output paths.

The server listens only on `127.0.0.1`, serves fixed viewer assets and explicitly
selected recordings, and exposes no editing or shell endpoint. Ctrl-C stops it.

## Checks

```sh
./.venv/bin/python -m unittest tests.test_campaign_env tests.test_campaign_replay tests.test_campaign_viewer
node tools/verify_campaign_replay_viewer.mjs output/campaign_viewer/replays/game.json
node tools/verify_campaign_viewer_interactions.mjs
```

Capture tests also compare recorded and unrecorded learning runs, including
network/optimizer state and RNG, to ensure inspection does not change play.
