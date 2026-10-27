# Historical evidence archive

For current status and instructions, start with the [project guide](../README.md).
This archive preserves reports as originally written. Old paths, commands, test
counts and “next steps” describe the original runtime; use the indexes below for
navigation and the maintained guides for current operation.

| Collection | Contents |
| --- | --- |
| [Campaign learning](stage_a/README.md) | Pilots, continued training, evaluations, performance changes and launch records |
| [Apple GPU experiments](gpu/README.md) | Component implementations, conformance evidence and CPU/GPU comparisons |
| [Milestone verification](milestones/README.md) | Original delivery results and dated integration reports |
| [Original planning](planning/README.md) | Detailed approved implementation plan before consolidation |
| [Study organization](studies/README.md) | Historical trainer/result organization and retention record |

The [preservation manifest](manifest.json) records each original path, archive
path, byte count and SHA-256, anchored to the source Git commit (per entry when versions differ). All registered
files were copied or moved byte-for-byte, including their original provenance.
Historical prose links may name an old checkout or report location; they are
preserved evidence rather than maintained navigation. The manifest maps relocated
paths, and the collection indexes link the files at their current locations.

Run `./.venv/bin/python tools/check_documentation.py` from the repository root
to verify those bytes and maintained links. Local checkpoints, raw runs, binaries
and environments remain in their original ignored artifact locations; this archive
does not imply those files are included in a clean clone. Existing curated study
results and interconnected map audits keep their established retention layouts.
