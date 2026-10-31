# Decision, rules and training review — 31 October 2026

This review asks where the regional campaign spends decisions, legal options,
search and network evaluations, and which rules or interface choices could be
simplified. It changes no engine, rule, interface or training code. Every number
was measured at commit `6522736`, which already includes the one-move skip, the
faster move generation and the eleven-round GPU training setup. The
[evidence file](decision_review_2026_10_31.json) holds the exact values, and
`tools/decision_census.py` and `tools/profile_campaign_menu_layers.cpp` reproduce
them.

## Summary

1. **The objective rewards a passive Japan.** Against the same scripted
   opponents, a Japan that never attacks beat the scripted attacking Japan in
   4/4 three-round seeds (Axis return **48.0** versus **36.2**) and 3/4
   eleven-round seeds (**50.8** versus **24.5**). Japan's first attack makes every
   warlord join China at once (+6.6 Allies wealth), ends the KMT–CCP civil war and
   costs about 100 IPP of units. The Stage A finding that Japan did not expand is
   consistent with these incentives, not only with weak learning.
2. **A quarter of the decisions that are still searched can go without changing
   any game outcome.** Battle bookkeeping, two-step one-ship naval orders,
   one-at-a-time purchases and staged flights are 22–27% of searched decisions.
   Three optional rule simplifications raise that to **46–50%**. Training is now
   limited by network evaluations (about 93,000 per eleven-round game), so fewer
   searched decisions mean proportionally fewer evaluations.
3. **The one-move skip covers only the search root.** Inside search trees,
   positions with a single legal action still take **10%** of network
   evaluations, and building ship orders takes another 22%.
4. **Japan's navy is 55–65% of Japan's decisions,** although no opponent has ships
   until KMT or CCP evolves. In a uniform game, naval order steps took 45% of
   search time.
5. **Many search targets are flat.** With 64 simulations, the search at Japan's
   opening (308 options) tried 63 different options, almost all once. In the
   eleven-round game, 60% of Japan's combat-movement decisions have at least 64
   options. The visit-count target there carries little information from the
   search's values.

## Already addressed upstream since 25 October

Measurements for this review began at commit `d1c6729` (25 October). Since then
the main branch has added the one-move skip (about 18% of evaluations), 7.3 times faster
move lists, shared event history between copies, per-position caches, 250–700
learning steps per batch and eleven-round training. Re-measured here, Japan's
opening combat-movement menu now takes **16 ms** instead of 58–68 ms, copying an
engine stays at 0.04–0.15 ms however long the game, and data reuse is no longer
low. Those findings are dropped; the numbers below are all from `6522736`.

## What a game consists of

The scripted policy is `campaign-active-baseline-v2:balanced` for all three
alliances. Uniform play picks any legal option with equal probability, a stand-in
for weak early policies. Current eleven-round training games average about
1,730–1,780 decisions, between the two.

| Workload | Decisions per game | Axis share | One option | Two options | Chance events |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 rounds, scripted, seed 1951 | 579 | 59% | 18.5% | 11.2% | 116 |
| 3 rounds, uniform, seeds 1951–1952 | 648 | 65% | 15.0% | 8.5% | 63 |
| 11 rounds, scripted, seed 1953 | 2,080 | 60% | 17.8% | 12.5% | 418 |

Japan makes about **114–140 decisions per national turn**, and **55–65%** of them
are naval orders.

Four kinds of option dominate the menus. In the eleven-round scripted game,
purchases are 24.4% of all legal options, land routes 23.1%, staged aircraft
flights (`air_fly`) 21.0% and naval order starts 12.9%. Japan's opening
combat-movement menu has 308 options, 169 of them staged flights.

Production menus are mostly construction sites. Japan's first purchase menu has
216 purchases; 187 of them are a facility or railroad at a particular site. In
the KMT's round-two menu of the scripted game, 209 of 213 purchases are
construction at a site, and the only unit choices are militia and two upgrades.
KMT placement menus reach about 90 options because every pending project is
offered at every eligible zone.

## The objective rewards a passive Japan

`tools/decision_census.py incentive` plays each seed twice. Allies and Comintern
always use the scripted policy. The Axis uses either the same scripted policy,
which attacks, or a passive variant that ends combat movement immediately and
passes declaration offers; every other Axis choice is unchanged.

| Seed | 3 rounds: attack | 3 rounds: passive | 11 rounds: attack | 11 rounds: passive |
| --- | ---: | ---: | ---: | ---: |
| 1951 | 28.1 | 46.2 | 1.3 | 49.7 |
| 1952 | 39.7 | 49.0 | 20.8 | 58.0 |
| 1953 | 31.0 | 48.4 | 51.3 | 44.8 |
| 1954 | 46.1 | 48.2 | 24.5 | 50.7 |
| Mean | 36.2 | 48.0 | 24.5 | 50.8 |

Values are the Axis terminal wealth-gap return. The mechanism is visible in the
three-round games:

- When Japan's first combat phase closes, all warlords align with China. Allies
  wealth rises by **6.6** in every seed, before any conquest pays off.
- Attacking costs 97–121 IPP of Japanese unit value (−9.7 to −12.1 wealth) and
  gains 1–8 income within three rounds.
- The attack ends the KMT–CCP civil war through the Chinese Truce. Because each
  alliance's return is its own wealth minus the other two, a passive Japan gains
  while KMT and CCP weaken each other.

Over eleven rounds the outcome swings with the dice: passive play won three seeds
by 26–48 points, and the attack won seed 1953 by 6.5. The scripted attacker is
crude, and a strong one may do better. But a learner that tries attacks will
usually see them lose, so more compute on the same objective is unlikely to
produce expansion. Before longer training, decide whether this is the intended
behaviour. Options include keeping it and judging learning by the objective
itself, starting a variant with the Japan–China war already declared, or
changing the objective. Each is a design decision, not an optimization.

## Interface changes that keep every legal outcome

These change how a turn is split into decisions, as the earlier naval
`campaign-orders-v1` change did. Every reachable end-of-phase position stays
reachable, and each change should be verified against that standard on test
positions before training on it. Estimated removals come from marking logged
decisions (`tools/decision_census.py savings`); real trajectories will shift.

| Share of all decisions | 3 rounds, scripted | 3 rounds, uniform | 11 rounds, scripted |
| --- | ---: | ---: | ---: |
| P1 Apply single-option decisions automatically | 18.5% | 15.0% | 17.8% |
| P2 Advance battle bookkeeping automatically | 6.7% | 3.0% | 6.4% |
| P3 Order a single ship in one step | 13.3% | 14.2% | 14.4% |
| P4 Buy a quantity of one row at once | 2.8% | 0.4% | 4.2% |
| P5 Place several identical projects at once | 0.7% | 0.1% | 1.4% |
| P6 Fly aircraft only as complete missions | 0.2% | 4.0% | 0.1% |
| **Any of P1–P6** | **37.8%** | **34.1%** | **40.0%** |
| **P2–P6, share of searched decisions** | **23.7%** | **22.5%** | **27.0%** |

- **P1.** The search already returns at once for a single-option root. Applying
  such positions automatically in the adapter would also remove them inside
  search trees, where they still take 10% of evaluations.
- **P2.** During combat the attacker must choose "progress battle" for every stage
  and again to clear a finished battle (`src/land_combat.cpp:1324-1347`). When
  only these steps are offered, their order changes nothing.
- **P3.** A one-ship move is `naval_start_move` then `naval_route`. Offering the
  route directly for a single ship removes one decision per move; multi-ship
  fleets keep the ordered construction.
- **P4, P5.** Purchases and placements happen one item at a time. A quantity
  choice, and a fixed placement order for pending projects, remove repeated steps
  and reorderings. The fixed order also shrinks KMT placement menus from
  projects × zones to zones.
- **P6.** `air_fly` lets an aircraft stop in any reachable zone and continue later.
  The scripted policy attacks with aircraft without ever using it. Staging is
  genuinely needed only for an aircraft leaving a carrier that will move, or an
  air transport collecting cargo, so P6 keeps it for those cases. Staging is also
  where the recent stranded-aircraft dead ends came from. This is the one change
  here that needs careful verification.

Two further changes shrink menus without removing decisions:

- **Treat identical units as one option.** Units with identical type, owner, zone,
  damage, movement, origin, route, cargo and flags are interchangeable, but each
  receives its own copy of every action. Collapsing them removes 12.0% of options
  in three-round uniform games and **15.3%** in the eleven-round game, including
  **55%** of land-route options there (17,909 → 8,080) as identical stacks grow.
- **Choose the purchase row before its site.** Japan's purchase menu would drop
  from 216 options to about 44 rows, plus a site step for the few facility
  purchases. This also fixes a prior bias: the policy factorization groups
  purchases by site (`studies/campaign/features.py:281`), so all unit purchases
  share one branch, and a fresh network gives buying a unit only about
  1/(sites + 1) of the purchase probability.

## Rule simplifications that need your decision

These remove real choices, so they change the game. They suit a curriculum stage
and can be switched off later.

| Share of all decisions | 3 rounds, scripted | 3 rounds, uniform | 11 rounds, scripted |
| --- | ---: | ---: | ---: |
| R1 Automatic casualties by a fixed order of loss | 7.8% | 3.3% | 6.0% |
| R2 Automatic retreat rule | 4.3% | 1.0% | 5.1% |
| R3 Warships do not move unless an enemy fleet exists | 21.9% | 32.4% | 24.0% |
| **Any of P1–P6 or R1–R3** | **55.6%** | **56.3%** | **59.0%** |
| **P2–P6 or R1–R3, share of searched decisions** | **45.6%** | **48.6%** | **50.2%** |

- **R3** is the largest. Japan starts with 24 ships, half its units, and only an
  evolved KMT or CCP can build ships. Transports, shore bombardment and strategic
  naval movement matter; free warship movement, patrol and raider designations,
  and in-port bookkeeping mostly do not. Keeping transports and a bombardment
  assignment, and freezing other warships, would also remove most of the naval
  order construction that takes 22% of search evaluations.
- **R1 and R2** remove casualty and retreat choices. Every hit is currently its
  own casualty decision, often taken by the defender in the middle of the
  attacker's turn. With both automated, a whole battle could resolve as one chance
  event instead of a long chain of rolls and choices.
- **Prune options that are almost never useful in this theatre,** such as most
  naval facilities, seaplane and submarine bases, or technologies like radar and
  anti-submarine warfare. This changes menus, not decision counts.

## Where search spends its evaluations

A 64-simulation, depth-16 search with a uniform evaluator was run at every
decision of one three-round game (seed 1953, uniform choices, 691 decisions,
313 s of search). It isolates engine and search cost from network cost, and
counts each expanded decision node as one network evaluation.

| Root decision | Share of decisions | Share of search time |
| --- | ---: | ---: |
| Naval order steps | 32.9% | 44.7% |
| Single option (skipped) | 15.2% | 0.1% |
| Battle bookkeeping | 2.5% | 2.3% |
| Everything else | 49.5% | 52.9% |

| Expanded node kind, 37,961 in total | Share of evaluations |
| --- | ---: |
| Combat movement | 46.8% |
| Naval order construction | 21.7% |
| Single legal action, inside trees | 10.3% |
| Non-combat movement | 9.2% |
| Production | 4.1% |
| Combat, casualties and retreats | 6.1% |
| Other kinds | 1.9% |

Japan's decisions took 79.4% of all search time. Uniform choices move ships more
often than trained play, so the naval shares here are an upper range.

## Training findings

- **Visit-count targets are flat on large menus.** Unvisited children score an
  optimistic value of 1.0, at least as high as any visited child
  (`studies/shared/multiplayer_mcts.py:252`). At Japan's opening, with an
  evaluator returning varied values, 16 simulations visited 16 different options
  once each, and 64 simulations visited 63 options (largest target 0.031). Such a
  target mostly repeats the prior's top choices. 21–29% of searched decisions, and
  60% of Japan's combat-movement decisions in the eleven-round game, have at least
  64 options. Gumbel root search was designed for budgets smaller than the menu
  and uses the search's values in its target.
- **The search cannot see the results of an attack.** Depth 16 covers about a
  seventh of one Japanese turn, so most combat-movement searches end before the
  battle. The decisions removed above would let the same depth reach further.
- **The network reads raw JSON, which makes samples large.** Each observation is
  about 2,500 tree nodes plus every action's own graph and a 33,394-node rules
  context. A stored sample takes about 1.2 MB, so current runs keep only 5–10% of
  positions, and preparing network inputs was 36% of game-process CPU in the
  29 October profile. Unit names such as
  `setup_japan_land_manchuria_rehe_infantry_1` also carry their starting zone as
  tokens forever. A zone-centred encoding (37 zones with unit counts, possession,
  income and facilities, connected by adjacency) would be far smaller, could keep
  every position, and is closer to the game's structure.
- **Most decisions do not need a full search.** KataGo's playout-cap
  randomization runs full searches on a fraction of decisions and records policy
  targets only for those; cheaper searches play the rest. This cuts evaluations
  directly.

## Engine notes

`tools/profile_campaign_menu_layers.cpp` times positions exported from a uniform
three-round game, inside the same per-position scope the engine opens.

| Japan position | History events | Options | Engine menu | Air layer alone |
| --- | ---: | ---: | ---: | ---: |
| Round 1 combat movement | 52 | 308 | 15.9 ms | 9.6 ms |
| Round 2 combat movement | 292 | 258 | 20.1 ms | 9.4 ms |
| Round 3 combat movement | 512 | 145 | 8.8 ms | 4.2 ms |
| Non-combat movement, rounds 1–3 | 182–621 | 37–52 | 6.3–9.9 ms | 0.1 ms |

Aircraft are still about 60% of an opening combat-movement menu, mostly staged
flights (P6). Planning keys cost 0.4–0.9 ms and a transition 0.6–1.1 ms. Starting
a naval order is the exception: 3–8 ms at most positions and 72 ms at one,
because its completion check validates fleet routes.

## Suggested order

1. Decide what the objective should reward, given the incentive results above.
2. Replace the flat visit-count target, for example with Gumbel root search, and
   compare at equal compute.
3. Apply single-option positions automatically in the adapter (P1), so searches
   stop evaluating them inside trees.
4. Build a second training action profile with P2–P6, identical-unit options and
   row-before-site purchases, and check that end-of-phase positions match.
5. Decide which of R1–R3 to use for curriculum training; R3 alone removes most
   naval search work.
6. Replace the raw-JSON input with a compact zone encoding, so every position can
   be kept.

## Method and limits

- Policies are scripted or uniform, not trained, so the shares describe the
  workload, not trained behaviour.
- Removal estimates mark decisions in logged games. They overlap, are counted
  once in each union, and would change once trajectories change.
- "Keeps every legal outcome" is the design target for P1–P6; each needs its own
  verification, especially P6.
- The incentive comparison uses one crude scripted attacker and four seeds per
  horizon. Equal seeds do not give equal dice once actions differ.
- The flat-target check uses a stand-in evaluator with varied values, not trained
  networks. Under the optimistic first-visit value, a visited option is chosen
  again only if it is the best so far and its prior is more than twice that of
  every untried option, so strongly peaked priors allow some revisits.
- Timings come from a 4-vCPU Linux container and are not comparable with Mac
  baselines. The census and search lanes ran four at a time; the native profile
  ran alone.
- `setup.py` passes `-mmacosx-version-min`, which Linux compilers reject. For
  these measurements the same extension sources were compiled directly with
  `g++ -O3 -std=c++20`.

Reproduce from the repository root:

```sh
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 3 --seeds 1951
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy uniform --rounds 3 --seeds 1951 1952
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 11 --seeds 1953
./.venv/bin/python tools/decision_census.py savings OUT.jsonl
./.venv/bin/python tools/decision_census.py symmetry --policy balanced --rounds 11 --seeds 1953
./.venv/bin/python tools/decision_census.py incentive --rounds 3 --seeds 1951 1952 1953 1954
./.venv/bin/python tools/decision_census.py incentive --rounds 11 --seeds 1951 1952 1953 1954
./.venv/bin/python tools/decision_census.py search OUT.jsonl --seed 1953 --simulations 64
./.venv/bin/python tools/decision_census.py targets --simulations 16 64
./.venv/bin/python tools/decision_census.py export POSITIONS --seed 1952
g++ -O2 -std=c++20 -I include -DGWRL_SOURCE_DIR='"'"$PWD"'"' \
    tools/profile_campaign_menu_layers.cpp build/<dir>/libgw_engine.a -o build/profile_menu_layers
build/profile_menu_layers POSITIONS/r0_japan_combat_movement.json 10
```
