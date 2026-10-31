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

The **Combat & dice** panel under the timeline explains fighting at the selected
position. At a dice event it names the battle type and location, the combat
round and stage, both sides' units by nation, and every die: the unit that fired
it, the numbers that hit (a die hits when it rolls at or under its unit's hit
number), the face rolled and whether it hit. Shore bombardment dice belong to
the bombarding ships, and coastal artillery fires at the landing ships; before
landing, an amphibious assault's sides are its landing force and bombarding
ships against the defending units. Rolls outside battles, such as
research or recruitment, show their purpose, roller and faces. Between dice
events the panel lists the battles in progress, and the map marks their
locations with ⚔. Battle dice are requested by the nation whose turn it is, so
the panel names the side whose units actually fired.

Map labels show current possession and retain the original nation when it
differs. The location inspector lists possession changes with links to their
events, and the event journal names transfers that happen while finishing a
phase. For example, Tsinghai starts under Ma Clique; in the seed-1951 replay,
CCP attacks it and the surviving Ma Clique joins KMT at event 12 (RB §4.9).
Later KMT possession does not change Tsinghai's original nationality.

The map's arrow for a move follows every zone of its recorded route, up to where
the unit actually stopped, so a flight or fleet route shows each zone it crossed.

The **Political status** panel above it follows the selected position. It lists
each alliance's nations with their standing, wars, capital and controller, the
warlords still unaligned or already absorbed, every war in progress, and the
Chinese Truce, foreign invasion of China, evolution to Major power, surrenders
and warlord alignment. A war declared at the selected event is marked new. It
reads only the recorded state, so existing recordings show it without re-export.

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
