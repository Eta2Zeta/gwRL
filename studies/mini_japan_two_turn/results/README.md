# Saved mini-Japan two-turn result

`final_run/` preserves the completed run originally stored in
`output/japan_fpu_optimistic/`. Its eight files, including the trained `.pt` file,
were moved without changing their contents. Checksums are recorded in
`final_run_sha256.json`.

## Run settings and outcome

- 500 training episodes; 500 MCTS simulations per decision.
- Evaluation every 5 episodes; seed 1936.
- Optimistic first-play urgency (the original run directory's identifying name).
- Final deterministic evaluation reward: **9.0**.
- Best recorded deterministic evaluation: **9.0**, first reached at episode 55.
- Best self-play reward: **9.0**, first reached at episode 35.

Start with `final_run/japan_torch_training_summary.txt` and
`final_run/japan_search_reward_over_time.svg`. The metrics JSON includes the full
training and evaluation history; the other two SVGs show how first-purchase
values and policy priors changed during this run.

## What the saved files mean

`japan_torch_policy.pt` contains the model weights at the **end of training**. It
is not a separately saved episode-55 model, and it does not contain optimizer or
replay-buffer state for an exact training resume.

`best_deterministic_checkpoint_trace.txt` is a text record of the best observed
evaluation episode, not a saved model checkpoint. The self-play trace records a
best stochastic training episode. Both traces are useful evidence of what the
run did; neither should be mistaken for the last episode's action sequence.

## Historical environment

This is the latest retained completed run for this study, **not a fresh result
under the current combat rules**. Its traces contain the earlier combat behavior
from before the subsequent shared-resolver corrections. Preserve the reported
scores as historical evidence; do not treat them as validation of today's
engine or compare them directly with a new run without checking environment
compatibility.

Original text files contain old `output/...` path references. They are kept
unchanged for provenance; the corresponding files now live in `final_run/`.
Write future runs to a new directory, rather than overwriting this bundle.
