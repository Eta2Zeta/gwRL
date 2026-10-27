# Training studies

The [project guide](../docs/README.md) is the main starting point. All current
public study environments use the shared campaign engine; historical result
bundles retain their original engine behavior and feature schemas.

| Study | Current workflow | Results |
| --- | --- | --- |
| Regional campaign | [Campaign workflow](campaign/README.md), `python -m studies.campaign.run` | [Current learning status](../docs/learning.md) |
| Army composition | [Composition](composition/README.md), `python -m studies.composition.train` | [Preserved results](composition/results/README.md) |
| Mini Japan, two turns | [Mini Japan](mini_japan_two_turn/README.md), `python -m studies.mini_japan_two_turn.train` | [Preserved results](mini_japan_two_turn/results/README.md) |

Run from the repository root with `./.venv/bin/python`. Campaign models/search live
in `campaign/`; shared adapter/search utilities live in `shared/`. Composition and
mini-Japan retain their own documented study interfaces and historical searches.
Their benchmark settings do not redefine the regional campaign's rules/objective.

New runs use fresh ignored `runs/` directories. Curated completed `results/`
bundles stay separate with their checksum manifests; organizing them does not
revalidate them against today's engine. Mini-Japan's text best-checkpoint trace
is not a saved model, and composition's historical result bundle contains no
trained model weights. Root `output/` is disposable simulator/debug output.

The [historical organization record](../docs/archive/studies/README.md) preserves
the original cleanup and result-retention details. For build and verification
commands, use the [development guide](../docs/development.md).
