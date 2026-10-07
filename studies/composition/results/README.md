# Saved composition-study result

`final_run/` preserves the completed run originally stored in
`output/composition_alpha_zero/`. Its seven files were moved without changing
their contents. Checksums are recorded in `final_run_sha256.json`.

## Run settings and outcome

- 1,000 training episodes; 1,000 MCTS simulations per decision.
- Evaluation every 10 episodes; seed 1936.
- Two separately trained models: attacker versus defender.
- Attacker budget 50; defender budget 30; normal terrain; no city.
- Final deterministic attacker reward: **2.398148148148148**.
- Best recorded deterministic attacker reward: **3.0943**, at episode 300.
- Best recorded deterministic defender reward: **-0.9722**, at episode 40.

Start with `final_run/composition_alpha_zero_summary.txt` and
`final_run/composition_alpha_zero_reward_over_time.svg`. The metrics JSON retains
the full training and evaluation history, including the final deterministic
outcome and best observed episodes for each side.

## What the saved files mean

The four `best_composition_..._trace.txt` files record the best observed attacker
and defender episodes, separately for stochastic self-play and deterministic
evaluation. These are best-episode text records, **not model checkpoints**, and
they need not describe the final episode. The two sides' best evaluations were
observed at different training checkpoints against their then-current opponent;
they are not an independently certified optimal pair of compositions.

This version of the composition trainer **did not save either model's weights**.
There is no `.pt` checkpoint in the original bundle. The recorded results remain
inspectable, but the original trained policies cannot be loaded or resumed from
these files alone.

## Historical environment

This is the latest retained completed run for this study, **not a fresh result
under the current combat rules**. In particular, its battle traces contain the
older Tank Destroyer target-strike behavior from before the shared-resolver
corrections. Preserve the reported scores as historical evidence; do not treat
them as validation of today's engine or compare them directly with a new run
without checking environment compatibility.

Original text files contain old `output/...` path references. They are kept
unchanged for provenance; the corresponding files now live in `final_run/`.
Write future runs to a new directory, rather than overwriting this bundle.
