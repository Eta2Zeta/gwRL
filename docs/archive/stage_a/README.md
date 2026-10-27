# Stage A historical evidence

Start with [current campaign learning status](../../stage_a/README.md) or the
[campaign workflow](../../../studies/campaign/README.md). These archived records
describe the implementation and conclusions at their recorded dates. Statements
such as “next” or “not yet implemented” are historical, not current instructions.

The reports and JSON were moved together without changing their bytes. Recorded
runtime paths, source hashes, settings and artifact hashes retain their original
meaning. Raw runs and checkpoints remain in ignored local storage; their hashes
and provenance are recorded here. The pre-consolidation overview is preserved
as [the historical overview](overview_2026_10_25.md).

## Learning experiments

| Experiment | Reports | Curated evidence |
| --- | --- | --- |
| Initial one-round pilot, 23 October | [Historical overview](overview_2026_10_25.md) | [Training](training_2026_10_23.json), [preflight](preflight_2026_10_23.json), [comparison](comparison_2026_10_23.json), [initial evaluation](evaluation_initial_2026_10_23.json), [final evaluation](evaluation_final_2026_10_23.json), [evaluation migration](evaluation_guard_migration_2026_10_23.json) |
| First 60 three-round games, 24–25 October | [Plan and recovery history](three_round_2026_10_24.md), [results](three_round_2026_10_25_results.md) | [Launch](three_round_2026_10_24_launch.json), [interruption](three_round_2026_10_25_interruption.json), [relaunch](three_round_2026_10_25_relaunch.json), [results](three_round_2026_10_25_results.json) |
| 60 additional three-round games, 25 October | [Launch and continuation](sixty_more_2026_10_25.md), [results](sixty_more_2026_10_25_results.md) | [Launch](sixty_more_2026_10_25_launch.json), [results](sixty_more_2026_10_25_results.json) |

## Performance and interface changes

| Work | Report | Curated evidence |
| --- | --- | --- |
| Initial matched performance repeat | [Historical overview](overview_2026_10_25.md) | [Performance](performance_2026_10_23.json) |
| Search and campaign scaling | [Report](scaling_2026_10_23.md) | [Cases](scaling_2026_10_23.json), [position profile](position_profile_2026_10_23.json) |
| Decision reuse | [Report](decision_reuse_2026_10_24.md) | [Measurements](decision_reuse_2026_10_24.json) |
| Native neural-input compilation | [Report](neural_input_2026_10_24.md) | [Measurements](neural_input_2026_10_24.json) |
| Forward-progress AI order interface | [Report](action_interface_2026_10_24.md) | [Measurements](action_interface_2026_10_24.json) |
| Checkpoint saving pilot | [Report](checkpoint_pilot_2026_10_25.md) | [Measurements](checkpoint_pilot_2026_10_25.json) |
| Independent native game concurrency | [Report](native_concurrency_2026_10_25.md) | [Measurements](native_concurrency_2026_10_25.json) |
| Direct numerical training input | [Plan](numeric_input_plan_2026_10_25.md), [report](numeric_training_input_2026_10_25.md) | [Measurements](numeric_training_input_2026_10_25.json) |

Compare matched workloads and their full settings. Component improvements and
short pilots do not establish full-campaign throughput or playing strength.

- [Campaign workflow before consolidation](workflow_before_consolidation_2026_10_27.md): original operational guide and performance chronology.
