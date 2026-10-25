# Sixty additional three-round games — 25 October 2026

Completed: see the [results and recovery limitations](sixty_more_2026_10_25_results.md).

The continuation is launched from the previously trained **generation 15**, with **60 completed games** already retained. Its target is **60 additional completions**, ending at **120 total games / generation 30**. The four games saved during their second round resume first; their eventual completions count toward the additional sixty. This is not a fresh initialization.

The run’s four-hour operational limit starts at **2026-10-25T21:29:20.268948+00:00** and ends at **2026-10-26T01:29:20.268948+00:00** (4:29–8:29 p.m. Chicago time). It includes initial evaluation, training, final evaluation, recovery and downtime. The completed prior ten-hour allocation is unchanged. The initial held-out evaluation was active when this launch record was captured; no new learning result is claimed here. [Launch evidence](sixty_more_2026_10_25_launch.json) records exact plans, hashes and checks.

## Preserved continuation

The original checkpoint SHA-256 is `3fa2022a1e894c9a44937399584600d87d9c308553be561492a951e44eaf5ebd` from frozen commit `88981035ec1d80ff73f5b1d4e3b4c5ec3fd2580d`. It remains unchanged. The exhaustive compatibility proof regenerated **16,175 labeled replay inputs and 665 pending inputs**, checked complete ordered legal menus and active serialized games/RNG, and matched their input fingerprints. No action or die was executed during proof or bootstrap. Models, Adam state, frozen policies, pending examples, replay order and every random-generator state continue.

The explicit migration changes only operational runner limits and reviewed source metadata after proof. The generation-15 checkpoint/archive share immutable storage in the new run directory. A **510,001-byte generation-15 model export** supplies the initial evaluation; generation-zero files are not used. Bootstrap restored the complete learner and rechecked all saved inputs before launch.

## Fixed training and evaluation

Training keeps the approved scenario/rules, three-round horizon, terminal wealth-gap reward, all three alliance policies, 16 simulations per decision, depth cap 16, width 16, one message layer and 2,048 token buckets. Four concurrent games form a collection batch. Each completed batch is followed by 16 sampled Adam steps per agent, 32 examples per step, learning rate 0.001 and replay capacity 16,384. Fifteen further collection/update cycles produce 240 further Adam steps per agent. Unfinished games receive no fabricated terminal labels.

Generation 15 and generation 30 face the same balanced scripted opponents on eight held-out seeds: 40009, 40013, 40031, 40037, 40039, 40063, 40087, 40093. Both network-only and separate 16-simulation/depth-16 search are evaluated, without root noise. Bootstrap verified separation from existing and prospectively generated training seeds.

Primary outcomes are newly held Japanese Chinese Home Country land/IPP, gross acquisitions/losses, Japanese unit removals and terminal wealth. Dadao possession and its acquisition/loss events remain separate supplementary evidence. Both modes require all eight games to finish genuinely; a full list of truncated records is not a completed evaluation. Partial training may still be evaluated, but the pipeline cannot report the sixty-game goal achieved without **120 total terminals, 30 updates, zero bootstrap samples and complete paired evaluation**.

## Resource and recovery envelope

The allowance remains **12 CPU cores and 30,000,000,000 bytes** of memory, including process overhead. Stages run sequentially. Monitoring charges each process the larger of RSS and macOS physical footprint, so compressed pages count. Soft stop is **25 GB**, escalation is **26 GB**, with a 180-second shutdown grace and 0.5-second sampling. An independent guardian enforces the persisted deadline even after a controller failure. These are sampled guards rather than a kernel memory quota.

Full recovery saves use a **30-minute interval**, plus orderly stop, with the preceding complete checkpoint retained. Small model exports follow completed learning updates. Resume uses the same immutable plan and frozen runtime; neither deadlines nor settings reset. The exact command is the run's ignored `resume.sh` at `studies/campaign/runs/three-round-60more-2026-10-25/resume.sh`.

## Preflight evidence and limits

All **451 Python tests** passed. The guarded compatibility proof and test processes completed within their aggregate allowance. A storage-only stress test allocated **16,384 independent numerical observation graphs** plus a **4 GB incompressible workspace reserve**, then saved, loaded and compared every row exactly. Charged peak memory was **22.815 GB**, below its **24 GB** guard. Streamed compressed graph storage reduced the measured four-game checkpoint from **935.9 MB to 99.0 MB** without losing numerical bits or metadata.

That synthetic storage dataset is never training data. Its measured state distribution and workspace reserve do not guarantee every future game's memory demand; live guards remain active. The earlier four-game speed pilot is not a promise that a mature replay buffer will sustain the same rate. Faster completion and prediction loss alone do not demonstrate improved play; the paired held-out outcomes determine the reported result.

The new frozen runtime is commit `cafbd911438983e229099d0079edfe687ddf03eb`, with **449 pinned files**, manifest SHA-256 `825935c5e6ea078631d4bef9c24102564fd510b3587adb51a3fdc710e561524b` and native SHA-256 `6b6718f2cc8d9e1ac77265b4b700935d554f38e5fd970417891199f04f461303`. Raw training, proofs and status files remain ignored under `studies/campaign/runs/three-round-60more-2026-10-25/`.
