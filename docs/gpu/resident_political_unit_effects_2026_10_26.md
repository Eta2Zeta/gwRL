# Exact resident political unit effects

Three internal political effects now operate on complete resident Apple GPU
state. They are building blocks, not complete Engine actions or a GPU campaign
backend. Their native oracle calls the original C++ helpers on clones.

* Movement refresh updates only the selected owner, after the caller's status
  changes. It preserves spent movement and native absent-allowance behavior.
* Removal follows the complete transitive `carried_by` closure, including foreign
  cargo, filters surviving cargo and both battle lists, and cancels repairs by
  target. Requested missing/nonunit IDs remain relevant to repair cancellation.
  Battle completion, political flags and income remain separate native hooks.
* Creation preserves possession checks, sequential IDs, signed counter overflow,
  Catalog error ordering, `emplace` collisions, optional allowance and placement
  flags. Catalog's zero/nonzero counter contexts are queried lazily in native
  order; newly inserted units change no CatalogContext input. Source data and
  complete cohort state/pool are retained on errors or insufficient allocation.

Nine movement, ten removal and eight creation cases passed. Coverage includes
all selected owners/streams, deep cargo chains, cycles at the explicit diagnostic
boundary, collisions, unknown Catalog types, flag precedence, zero crossings,
every allocation retry, no-host-read traps and empty/unselected inputs. The
removal export also passed eleven shared transport round-trip cases. All 27
native regression suites passed after the latest native wrapper/prefix additions
(39.68 seconds). Correctness does not establish useful training throughput.

The raw diagnostic export traverses typed State and original execution RNG
directly. It preserves negative zero and unknown noninteger payload bits that a
JSON-restored oracle would normalize. Tests compare all record/section/RNG words,
normalizing only equivalent string-ID namespaces by exact referenced bytes.

Creation and the upcoming surrender helper need additional fixed protocol
spellings. They were appended after existing prefix entries; native interning
deduplicates existing spellings. The wire fingerprint changes, so old raw arenas
must retain their old runtime/context or be freshly captured from a validated
State. They cannot be retagged. CPU saved-game values, rules identities and model
inputs are unchanged. Historical training checkpoints were not migrated.

The native objective-bonus/surrender probes are prepared for the next resident
port. Objective awards are completed construction projects, not immediate unit
creation. Neither this report nor those probes claim a completed GPU surrender
or political-refresh implementation.
