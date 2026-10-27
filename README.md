# gwRL

`gwRL` is a C++20 Global War 1936 rules engine with Python reinforcement-learning
studies. The implemented regional campaign covers China, Mongolia and Japan
from July 1936 through July 1941.

**Start reading: [Project guide](docs/README.md).** It explains where the project
stands, what works, and what to read next.

The CPU campaign and learning pipeline are implemented. The latest continued
experiment reached 120 completed three-round games; useful Japanese offensive
play has not been demonstrated. Apple GPU components are under development;
complete GPU games and training speedups remain unverified.

## Run or contribute

- [Build, checks and documentation conventions](docs/development.md)
- [Run, resume and evaluate campaign learning](studies/campaign/README.md)
- [Watch recorded games](web/campaign_viewer/README.md)

Commands run from the repository root. Build the native Python extension in an
existing project environment with:

```sh
./.venv/bin/python -m pip install -e .
./.venv/bin/python -m studies.campaign.run --help
```

The [reference index](docs/reference.md) locates the approved scenario, rules,
completed milestone records and map audits. The [archive](docs/archive/README.md)
preserves past reports and their evidence separately from current instructions.
