# Project guide

This is the starting point for understanding `gwRL`. The pages linked below
summarize the current implementation; dated experiment reports live in the
[archive](archive/README.md).

## Where we are

The shared CPU engine implements the approved 37-zone China–Japan campaign,
including politics, movement, production, land/air/naval combat and explicit
player reactions and dice. M0–M12 implementation gates are complete for that
regional scenario. This does not establish support for every rule of the global
game; the [coverage ledger](reference/runtime-coverage.md) records the scope.

The learning pipeline runs three alliance networks, uses Monte Carlo tree search
to choose actions, learns from self-play, and supports checkpoint recovery and
held-out evaluation. The latest continued experiment reached **120 completed
three-round games and 30 learning batches**. Useful Japanese offensive play has
not been demonstrated. [Learning status](learning.md) explains the results,
measured throughput and limits.

Apple GPU work currently implements selected batched services and recruitment
transitions. The complete CPU backend remains the training engine. Some GPU
operations are faster at large batches; complete GPU games, GPU search and an
end-to-end training speedup are still unfinished or unverified.
[GPU status](gpu/README.md) distinguishes those capabilities.

## What to read next

| Your purpose | Read |
| --- | --- |
| Understand how the engine, search and learning fit together | [Architecture](architecture.md) |
| Understand what learning has achieved and what remains | [Learning status and results](learning.md) |
| Understand the Apple GPU implementation and measured gains | [GPU guide](gpu/README.md) |
| Run training, recover a run or evaluate a model | [Campaign workflow](../studies/campaign/README.md) |
| Build the code or run checks | [Development guide](development.md) |
| Inspect games visually | [Campaign Observatory](../web/campaign_viewer/README.md) |
| Find a game rule, scenario decision or milestone detail | [Reference index](reference.md) |

## Next gates

The GPU work needs complete legal transitions and matched whole-game/search
measurements before it can replace CPU self-play. The learning work needs
reliable resource use and measurable playing improvement against fixed opponents
under equal budgets. Completing games, predicting scores better or accelerating
one operation does not establish stronger play.

The current allowance is **12 CPU cores and 30,000,000,000 bytes of memory**,
including coordinator and worker overhead. Larger experiments need representative
completion and memory measurements first.

## Reading historical evidence

Use the [archive index](archive/README.md) when investigating an experiment or
past decision. Archived reports describe their original code, settings and paths;
their old “next steps” are historical. Current commands and status belong in the
guides above. Scenario data and rule clarifications retain their fingerprints. Current coverage
inputs and outputs live with the topic references, and their tools use those paths.
