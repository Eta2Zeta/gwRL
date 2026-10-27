# Development

Start with the [project guide](README.md) for status and the
[architecture](architecture.md) for component boundaries. Commands below run from
the repository root.

## Build

The project uses C++20 and CMake. Python training needs an existing environment
with PyTorch and NumPy; supervised process/memory tooling also uses `psutil`.
[pyproject.toml](../pyproject.toml) declares build requirements, while
[setup.py](../setup.py) builds the native extension. Editable installation does
not install the training dependency stack. In the prepared project environment:

```sh
./.venv/bin/python -m pip install -e .
```

After changing C++ headers, implementation or binding includes, rebuild the
extension before Python checks or training:

```sh
./.venv/bin/python setup.py build_ext --inplace --force
```

Build and run the standalone simulator out of source:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build --parallel 10
./build/gw_simplified
```

Build products (`build/`, `.o`, `.so`, `.egg-info/`), caches, local images and
training scratch output follow the existing ignore policy. They are regenerated
locally rather than committed. Optional Apple GPU dependencies are described in
the [GPU guide](gpu/README.md); CPU operation does not require them.

## Verify a change

Run checks appropriate to the change. The complete native suites and ordinary
Python regressions are:

```sh
ctest --test-dir build --output-on-failure
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  ./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Metal-specific checks require the optional GPU environment; ordinary CPU test
discovery may skip them. Follow the selected component's instructions rather
than interpreting a skip as GPU verification. No training benchmark is part of
a documentation-only check.

For documentation changes:

```sh
./.venv/bin/python tools/check_documentation.py
```

This validates local links in maintained Markdown and archive indexes, and checks
every archived file against the recorded byte count and SHA-256. Missing ignored
local images are reported separately because a clean clone omits those assets;
add `--require-local-assets` to require them too. Historical prose is preserved
as originally written, including old paths and commands; its links are not treated
as current instructions. The checker tests local target existence, not external
websites or section-anchor spelling. Active input/tool dependencies must also be
checked before moving files.

Correctness and practical training efficiency are both requirements. Preserve all
legal choices, state, probability distributions and exact replay behavior during
optimization. Compare matched real workloads, completion, wall time and peak
memory; a small operation benchmark is not a whole-training result. Keep the
12-core/30,000,000,000-byte aggregate allowance unless the user changes it.

## Documentation conventions

- Keep the [project guide](README.md) current when implementation status changes.
  Update existing architecture, workflow and performance pages instead of adding
  another competing overview.
- Put durable rule questions and adopted rulings in the
  [clarification register](../game_content/rules/clarifications.md). Put scenario
  choices in the scenario contract/data. Implementation notes belong in developer
  references, not in the rule register.
- Put dated experiment reports and curated machine-readable evidence together in
  `docs/archive/`. An archive index identifies the scope and source version.
  Preserve original reports and measurements; add a new result or correction
  rather than rewriting historical evidence. Register retained files in the
  [archive manifest](archive/manifest.json).
- Keep scenario/catalog JSON, authored audit inputs and current generated coverage
  ledgers with their consumers. Raw checkpoints, traces, environments and build
  output stay in ignored run/artifact directories. Moving a report does not make
  its local raw artifacts part of Git.
- Use relative links inside repository documentation. Keep the front page short;
  maintained detail belongs in the topic [reference index](reference.md), and completed
  milestones belong in the archive.

## Reference regeneration and frozen sources

`./.venv/bin/python tools/build_campaign_coverage.py` regenerates
`docs/reference/runtime-coverage.{json,md}` from `rules-ledger.md`.
Add `--check` to verify both outputs against current handlers and fixtures.
The stable rule IDs and acceptance criteria retain their original meaning.

Frozen rule/scenario JSON and the checksum-pinned clarification register keep
original paths and bytes because they also affect model inputs and checkpoint
compatibility. The archive manifest resolves historical document locations for
reference tooling. The sole `docs/m0/README.md` compatibility pointer preserves the
register's literal link; it contains no milestone report. Change such aliases only
with their pinned consumers and explicit compatibility treatment.

## Version control

Follow [AGENTS.md](../AGENTS.md): inspect the working tree, stage explicit paths,
review the staged diff and commit completed validated work in coherent units.
Fetch and inspect divergence before pushing to the configured upstream. Preserve
unrelated work and historical evidence; do not force-push or rewrite shared history.
