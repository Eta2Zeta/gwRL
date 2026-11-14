# Rules and data

These pages say which printed rules the engine implements and trace the
scenario's numbers back to their printed sources. They are for looking things
up. To learn how the engine works, read the
[engine documentation](../engine/README.md).

| To find | Read |
| --- | --- |
| Whether a printed rule applies in this campaign, and why not if it does not | [Core rules ledger](core_rules_ledger.md): 143 numbered rows, R000 to R142 |
| Which code and which test carry each of those rows | [Runtime evidence index](runtime_coverage_ledger.md), with its [data](runtime_coverage_ledger.json) |
| How an unclear rule was settled | [Rule clarifications](../../game_content/rules/clarifications.md): the numbered RCL entries |
| The printed rules themselves, with the project's notes | The annotated rules reader, `game_content/rules/html/index.html` ([about it](../../game_content/rules/html/README.md)) |
| Where Japan's starting pieces come from | [Japan setup audit](japan_setup_audit.md) |
| Where the Chinese and minor nations' starting pieces come from | [China and minor setup audit](china_minor_setup_audit.md) |
| Where prices and asset values come from | [Asset price audit](asset_price_audit.md) |
| The starting ship queues, the research chart and the catalog's source checks | [Source reconciliation](source_reconciliation.md) |
| The convoy lines, which this campaign leaves out | [Convoy audit](convoy_audit.md) |
| Which printed pages stand behind each rules module | [Catalog](catalog_sources.md), [politics](politics_sources.md), [movement](movement_sources.md), [economy](economy_sources.md) |
| Why ships need no forced passage at the two narrow crossings | [Narrow crossings and naval passage](naval_geography.md) |

## Keeping them current

- **The runtime evidence index is generated.** After changing a rule handler or
  a test fixture, rebuild it with `python3 tools/build_campaign_coverage.py`;
  `--check` says whether it is current.
- **The engine checks its sources.** The rules profiles in `game_content/rules`
  record the SHA-256 of the files they cite, the clarification register among
  them, and the engine refuses to start when one has changed. After editing a
  cited file, update the recorded hash in the same commit.

## Stage names in these pages

The engine was built in twelve stages, and these pages name them: M0 the
approved campaign, M1 the map, M2 the engine's state, M3 the catalog, M4
politics, M5 movement, M6 the economy, M7 land combat, M8 air, M9 naval, M10
the whole campaign and M11 the environment for agents. The stages' delivery
reports are in the [archive](../archive/README.md#milestone-pages).
