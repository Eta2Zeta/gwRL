# Three-round learning experiment

Authorized 24 October 2026: at most 12 CPU cores, 30,000,000,000 bytes of memory
and ten hours for a three-round campaign learning experiment. This is a test of
basic useful behavior, not a claim of eleven-round campaign competence.

**Completed 25 October:** [results](three_round_2026_10_25_results.md). Sixty
three-round games and fifteen learning batches completed. Japan acquired no
Chinese Home Country land in either evaluation mode; trained search preserved
more units/wealth than initial search. Checkpointing consumed 60.33% of the
measured training interval. Four unfinished games remain saved for compatible
continuation; the existing supervised plan is complete.

## Preflight correction

The first held-out game exposed a combat bug before any learning update. KMT
infantry retreated from Rehe to Beiping in round one. Its old retreat flag then
incorrectly excluded it from defending Beiping during CCP's following turn.
CCP could capture the zone while that infantry remained alive; a later KMT Low
Morale retreat failed because its attack origin had become hostile.

Retreat participation is now recorded per battle. A withdrawn unit stays out of
its original battle, retains its movement restriction, and can defend in another
battle. The ordinary attack-origin retreat safeguard and the adopted shared-zone
truce rules remain unchanged. This is an implementation correction, not a new
rule interpretation. The new regression follows a genuine Low Morale retreat
through the calendar to an intervening CCP attack and checks defense, movement
restrictions, clone/checkpoint continuation and exact replay.

The failed launch and its runtime/checkpoints are preserved at
`studies/campaign/runs/three-round-10h-2026-10-24/`. It performed four initial
decisions and zero learning updates. The corrected experiment starts fresh in
the sibling `three-round-10h-2026-10-24-r2/` directory with the same initialization,
settings and absolute deadline. No incompatible checkpoint is silently migrated.

Validation after the correction: all 346 Python tests pass (236.796 seconds),
all 26 CTest suites pass (87.35 seconds), and the 33 land-combat fixture groups
pass. The formerly failing held-out seed 40009 now completes three rounds with
fresh parameters identical to the original untrained baseline. That baseline
gained no Chinese land and lost Rehe; it is a comparison point, not evidence of
learning.

### First self-play interruption

The corrected run completed all sixteen initial evaluation games, then stopped
in its first self-play batch at 03:15:28 UTC on 25 October. Search reached a
position with no legal choices: a plain flight had spent the Tokyo tactical
bomber's five movement points reaching hostile Hainan without a landing plan.
The engine had offered that flight but correctly refused phase completion once
the plane was stranded. This needs an engine correction, not a new reward or
search setting.

The saved checkpoint contains four unfinished games at wave 48 and 163 pending
policy samples, with zero completed training games or learning updates. The
last progress record reached wave 57. Some saved policy menus include the
invalid flight, so they must not be silently retagged as corrected data. All
original checkpoints and logs remain intact. The
[interruption record](three_round_2026_10_25_interruption.json) pins the evidence;
compatibility and valid flight/carrier orderings must be checked before recovery.
The original absolute deadline remains unchanged.

The read-only recovery proof matched the first 141 actual transitions and 117
stored policy inputs exactly, then found a changed menu: 21 stranded flights
were removed (316 choices became 295). The board state was identical and the
checkpoint bytes remained unchanged. The old pending targets therefore cannot
be relabelled as corrected data. A fresh first batch is required; the preserved
run has no learned progress to lose.

Plain flights now reject provable landing dead ends. The check uses optimistic
aircraft and carrier reachability, preserving partial flights, deck-vacating
possibilities and aircraft-first/carrier-later sequences. It is a necessary
condition, not a promise that every retained partial plan can be completed.
Actual flight permissions and the final joint landing assignment still apply;
MAP designation is unchanged. The implementation previews one aircraft and
shares a bounded carrier-reachability calculation within a menu.

After this correction, all 346 Python tests pass (233.953 seconds), all 26 CTest
suites pass (71.06 seconds), and all 12 air fixture groups pass. New fixtures
exercise exhausted flights, a positive-fuel dead end, split flight/landing,
both aircraft/carrier orderings, cloning and exact replay.

On four identical saved Japanese combat-movement positions, five fresh-menu
trials per position added a mean 1.59 ms to the position medians (32.10 to
33.69 ms, about 4.9%). Only stranded `air_fly` choices disappeared; other action
counts and all state/RNG snapshots matched. This measures the correctness
check's menu cost, not completed-game throughput or training feasibility.

The replacement run is `three-round-10h-2026-10-24-r3/`. Its
[relaunch record](three_round_2026_10_25_relaunch.json) pins the frozen corrected
runtime, identical initial parameter bits and unchanged settings/deadline.
Initial evaluation runs again under the corrected engine before self-play.
Compatible interruptions still resume unfinished games and all learning/random
state; this explicit fresh start addresses incompatible erroneous menus before
the first learning update. The earlier run remains intact for inspection.

## Question and fixed settings

Does three-round self-play improve Japan's ability to acquire and retain
Chinese Home Country territory against fixed verification opponents?

The scenario retains the approved 99-piece, 37-node setup, complete rules and
`campaign-orders-v1` action interface. Three calendar rounds mean three turns
each for CCP, Mongolia, Japan and KMT; the practice game ends after KMT's third
turn. Its final holdings include KMT's response to Japan's last turn, but not
another CCP/Mongolia turn. The original eleven-round campaign remains intact.

Training begins with fresh neural parameters. All three alliance policies learn
through self-play; the models stay frozen during each four-game collection
batch. Training uses 16 simulations per decision, search depth 16, hidden width
16, one message layer, 2,048 token buckets, Adam learning rate 0.001, 16 sampled
updates of batch size 32 per alliance after each completed collection batch,
and replay capacity 16,384. These are fixed experimental settings, not an
established optimal configuration. The network architecture is deliberately
the measured pilot architecture; it may prove insufficient.

Only genuine three-round terminal wealth-gap outcomes label training samples.
There is no territory reward bonus, demonstration warm start, bootstrap label
for an unfinished game, or alteration to combat/randomness. A 5,000-wave
execution guard saves unfinished games without an update; reaching it is a
diagnostic stop, not a loss or successful game.

This experiment uses the verified CPU path. Apple MPS/CUDA support and a GPU
simulator are separate engineering work, not assumed speed improvements here.

## Evaluation

Initial and final Japan/Axis face the same versioned balanced scripted opponents
on eight held-out seeds: 40009, 40013, 40031, 40037, 40039, 40063, 40087 and 40093.
Actual generated training seeds are checked for overlap. The evaluation uses
both maximum-probability network-only choices and a separate 16-simulation,
depth-16 search, with no root noise. Search improvement and learned policy
improvement are reported separately.

The evaluation records new Japanese possessions within the authoritative KMT
Chinese Home Country, their printed IPP values, losses of initial holdings,
acquisition/recapture/loss events, removed Japanese units, completion and actual
terminal wealth. Home Country includes land outside mainland China; each result
stores the exact zone set and excludes initially Japanese land from new gains.
Dadao possession remains separate. Acquisition by influence/alignment is not
mislabelled as a combat capture. Removed unit identities may include surrender
or other forced removal, rather than combat casualties alone.

The main evidence is the paired initial-to-final change in newly held land/IPP
and army losses on completed games, alongside wealth and completion. Equal
seeds do not guarantee identical dice events after different policy actions.
Eight seeds give a limited behavioral test, not broad playing-strength proof.
Unfinished evaluations receive no terminal score or terminal expansion average.

## Execution and recovery

`tools/run_three_round_experiment.py` orchestrates initialization, initial
evaluation, supervised training, and final paired evaluation. A persisted plan
sets the absolute deadline and reserves time for final evaluation. Reissuing the
same plan resumes its completed stages; it never replenishes the deadline.
Source code and the native extension are copied from a committed revision into
the ignored run directory's `runtime/` snapshot before launch. Future changes
to the main checkout therefore do not change a running experiment.

Training is supervised by `tools/supervise_campaign_training.py`. Explicit BLAS
and tensor limits keep four search workers, four tensor threads and coordinators
within twelve cores. The pipeline samples aggregate process-tree resident memory
and stops below 30 GB with a safety margin. Sampling can miss brief peaks or
count shared pages more than once; it is not a kernel-enforced allocation cap.
On macOS, a process-scoped `caffeinate` prevents idle sleep while the job runs.
An independent deadline guardian remains active if either controller crashes.
The internal 25 GB soft stop and 26 GB escalation threshold leave headroom
below the authorized 30 GB. Four search workers, four tensor threads and four
coordinators (runner, supervisor, pipeline and guardian) form the conservative
twelve-core budget. Final evaluation runs after training, not concurrently.

The training checkpoint contains models, Adam state, replay, pending unlabeled
samples, frozen policies, unfinished games and all execution/search/sampling
random states. Checkpoints are flushed before atomic replacement;
`checkpoint.pt.previous` preserves the preceding complete checkpoint. SIGINT or
SIGTERM finishes the current search wave/update and saves. A crash resumes the
last completed checkpoint and may repeat work since that save. Backup recovery
is explicit; incompatible sources or configuration are rejected.

The final evaluation uses an immutable checkpoint snapshot, so later training
resumption cannot silently change its weights. Completed evaluation seed/mode
files are reused after interruption; an interrupted evaluation game restarts
from its seed. Training and unfinished self-play resume from their checkpoint,
independently of inspection replay recording.

New recovery regressions compare actual SIGINT, SIGTERM, abrupt SIGKILL and
damaged-latest-file recovery with uninterrupted execution. Supervisor tests cover
fixed budgets, process locks, resource stops and bounded transient retries.

Large models, progress logs, evaluation events, frozen runtime and raw resource
measurements remain ignored under
`studies/campaign/runs/three-round-10h-2026-10-24-r3/`. Curated launch/result evidence
will identify the source revision, native hash, settings, timings, counts and
the limits of any learning conclusion.

The [original launch record](three_round_2026_10_24_launch.json) and
[current relaunch record](three_round_2026_10_25_relaunch.json) pin the runtime
and initial checkpoint hashes. The absolute deadline was 2026-10-25 12:27:28 UTC
(7:27:28 a.m. Chicago); the pipeline completed at 11:33:03 UTC (6:33:03 a.m.).
During execution, `resume.sh` was the fixed recovery entry point and could not
extend that deadline. The completed plan does not launch more training. A future
authorized allocation can continue from the preserved checkpoint. The completion
follow-up is removed after the result report is published.
