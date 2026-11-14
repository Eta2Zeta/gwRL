# Rules and data

These pages say which printed rules the engine implements and where the
scenario's numbers come from. They are for looking things up. To learn how the
engine works, read the [engine documentation](../engine/README.md).

| To find | Read |
| --- | --- |
| Whether a printed rule applies in this campaign, and why not if it does not | [Core rules ledger](core_rules_ledger.md): 143 numbered rows, R000 to R142 |
| Which code and which test carry each of those rows | [Runtime evidence index](runtime_coverage_ledger.md), with its [data](runtime_coverage_ledger.json) |
| How an unclear rule was settled | [Rule clarifications](../../game_content/rules/clarifications.md): the numbered RCL entries |
| The printed rules themselves, with the project's notes | The annotated rules reader, `game_content/rules/html/index.html` ([about it](../../game_content/rules/html/README.md)) |
| Why ships need no forced passage at the two narrow crossings | [Narrow crossings and naval passage](naval_geography.md) |

## Where the scenario's numbers come from

Every number the engine loads sits in a data file, next to the printed page it
was read from. [The campaign](../engine/scenario.md) describes what those
files hold. This table says where each kind of number is and how its source is
written down. The scenario's files are in
`game_content/scenarios/japan_china_1936`.

| Numbers | Data file | How the source is recorded |
| --- | --- | --- |
| Japan's starting pieces, factories and ships under construction | `japan_setup.json` | Each row names the sheet, its PDF page and the printed row |
| The starting pieces of the KMT, the CCP, the warlords and Mongolia | `china_minor_setup.json` | Each land zone lists the sheet, page and section |
| Calendar, turn order, starting money, what is left out, how wealth is scored | `scenario_contract.json` | The campaign's approved choices, listed as resolved decisions; the turn order and the official starting money cite their printed pages |
| What every unit, facility and technology does and costs | The five files in `game_content/catalog/gw36_v43` | Each definition lists pages and sections |
| The research chart, and what was already paid for Japan's ships under construction | `catalog_source_checks.json` | Pages, and how each amount was worked out |
| The rules as the engine applies them | The six rules profiles, `game_content/rules/gw36_*_v43.json` | Each rule names its source and pages |
| The convoy lines, which this campaign leaves out | `convoy_audit.json` | Kept for reference only |

The setup files, the catalog and the rules profiles also record the SHA-256 of
each PDF they were read from.

These files were checked against the printed sheets, line by line, in October
2026. Those reviews are in the
[archive](../archive/README.md#milestone-pages).

## Keeping them current

- **The runtime evidence index is generated.** After changing a rule handler or
  a test fixture, rebuild it with `python3 tools/build_campaign_coverage.py`;
  `--check` says whether it is current.
- **The engine checks its sources.** The rules profiles in `game_content/rules`
  record the SHA-256 of the files they cite, the clarification register among
  them, and the engine refuses to start when one has changed. After editing a
  cited file, update the recorded hash in the same commit.
