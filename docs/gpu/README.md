# Campaign CPU and Apple GPU execution

Current as of 27 October 2026. Start with the [project overview](../../README.md)
for the campaign and learning status.

**The C++ CPU engine is the only complete campaign backend.** Apple GPU neural
execution works alongside CPU rules and search. The resident Metal rules port
has several exact components and supported recruitment transitions, but cannot
yet execute complete games or Monte Carlo tree search on the GPU.

| Area | Current capability |
| --- | --- |
| CPU campaign | Complete rules, legal choices, chance, search, training and recovery; default/reference path. |
| Apple GPU neural execution | Inference, learner updates, evaluation and recovery through PyTorch MPS. Small actor batches have not improved completed-game throughput. |
| Resident state | Lossless State, history, decisions, continuations and RNG; device edits, identities, snapshots and search clones. These privileged buffers are excluded from neural inputs. |
| Resident rule services | Political permissions, catalog statistics, supplied-route validation, income/accounting, terminal scores and dice/RNG processing. |
| Resident political refresh | Connected internal refresh, including evolution, truce termination, surrender and their ordered choices/queues. Battle resolution is still separate. |
| Resident recruitment | Ordered menus; roll/start, sampled-roll and stored-choice Engine transactions, including placement, free ship work and repairs for supported cases. |
| Complete GPU games/search | Unfinished. General movement execution, broad legal-menu generation, combat resolution and a device search loop still require work. |

Supported recruitment operations return an explicit capability error and preserve
their input when they reach an unported service. Examples include naval-force
selection/completion and some unwrapped CoreRules diagnostic configurations.
They never remove a legal option or silently substitute a CPU handler.

Read only the guide relevant to your purpose:

- [Architecture and use](architecture.md): interfaces, correctness contracts,
  environment setup and bounded benchmark commands.
- [Performance](performance.md): the current measured conclusion and its limits.
- [Historical evidence](../archive/gpu/README.md): dated reports, paired JSON,
  source hashes and earlier experiments.

Further work should connect complete chronological transitions and search batches,
then compare completed self-play under equal models, budgets and resource limits.
Component throughput does not establish a game or training speedup.
