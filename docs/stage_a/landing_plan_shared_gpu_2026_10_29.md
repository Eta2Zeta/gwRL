# Landing plans and shared GPU self-play — 29 October 2026

Two changes, both on the user's instructions. First, no move may strand an
aircraft: a move is legal only if every aircraft the moving side has in the air
keeps a landing it can still reach, or, where dice or another nation's turn
already left some without one, if it leaves no more of them. Second, the
self-play benchmark evaluates its network in shared batches on the Mac's GPU:
eight game processes play four games each and send every position their
searches ask about to one coordinating process, which evaluates them together.
Training does not use the shared evaluator yet. The
[evidence JSON](landing_plan_shared_gpu_2026_10_29.json) records workloads,
results and provenance; raw outputs remain under
`studies/campaign/runs/landing-plan-2026-10-29/` and
`studies/campaign/runs/shared-gpu-2026-10-29/`.

**Result: with the network on the GPU, a queue that keeps every game slot busy
plays about 24 complete eleven-round games per hour against 14.6 for the
CPU-only setup, 1.66 to 1.73 times as many depending on how the rates are
measured: about 180 complete games in an eight-hour night instead of about 110.
Eight game processes and one coordinating process played 32 games in 82.6
minutes. Under the landing rule all 322 random-play games completed; no move
raised the number of aircraft without a landing, and none was lost.**

## Landing plans

RB 9.3 asks for a landing spot for every attacking aircraft only when Combat
Movement ends, so aircraft may fly before the carriers that will take them. Each
flight used to be checked alone: could some airfield or carrier still be within
reach? That ignored full decks and the other aircraft. In random play, later
legal moves stranded an aircraft in about one game in a hundred, and the engine
then removed it before combat as a last resort. In seed 5090 a second bomber
flew back over sea zone P14 to the light carrier's only seat, which an attacking
bomber at Hopeh also needed, while a fighter without fuel held the fleet carrier
in P15.

Every move must now leave the moving side's airborne aircraft a joint landing
plan:

- each lands ashore within its remaining range, or on a carrier in a zone the
  carrier is in or can still sail to this phase;
- each carrier ends in one zone, and a carrier that sails launches its own
  aircraft first, where its route begins;
- an aircraft on a carrier that can still fly ashore frees its seat.

The plan covers the moving nation's aircraft and those of a minor it controls
and moves, such as Dadao's on Japan's turn. Other nations' patrols land on their
own turns and are lost at a phase end when no landing remains, as RB 9.3.1
prescribes. Flights, landings, attacks and naval air attacks check the plan on
the position itself, previewing where each aircraft would end. Carrier routes
and engagements test the move on a copy of the position, but only when the ships
carry aircraft, or include a carrier while the moving side has aircraft in the
air; so does a carrier entering port, and starting a patrol also tests a copy.

### When aircraft already cannot land

Dice can leave an aircraft with no possible landing, as when a reaction sinks
the carrier an attacker was to return to. So can another nation's turn: RB
9.3.1 removes a patrol only when it alone has no landing spot, so two patrols
can be left sharing one seat. The first version then refused every carrier move
and every air attack for the rest of the phase, and let Combat Movement end only
after every other move had been used up. RB 9.3 loses only the aircraft that
cannot land.

The rule is therefore a count. The engine counts the airborne aircraft that no
reachable plan lands, the shortfall, and no move may raise it. With a complete
plan the shortfall is zero and every check is the one above. An aircraft that
flies must itself keep a landing, so one that is already lost cannot spend its
fuel attacking, and an aircraft in flight that no such plan lands may be given
up. Combat Movement ends once the carriers stand where they land every aircraft
that a plan can land; the fewest aircraft that still cannot land are lost as it
ends and counted in the game state. Noncombat Movement ends only once the
mover's patrols can land as the carriers stand; a patrol with no landing left
can be given up. After combat, a returning aircraft takes a spot that keeps the
others' landings where one exists, and any spot it can reach otherwise.

### Carrier routes

A carrier route is checked wherever it can end: in its last zone; where Enemy
surface warships force a screen, since a lone carrier must stay and fight; where
neutral units raise a peace entry, since a declaration can make them blockers;
and, when a force of several ships leaves port past either, with the ships that
do not screen still in port and their aircraft already launched. Enemy patrol
aircraft, submarines, transports, raiders and escorts do not stop a force, so a
route is not checked where only they stand. Engaging Enemy ships in a carrier's
zone is offered only if it leaves no more aircraft without a landing.

Where a carrier's arrival is uncertain, the plan is conservative. It counts only
routes that meet no unfriendly unit before their last zone, so no screen, peace
entry or reaction attack can stop the carrier short, and it treats a ship that
sailed into Enemy units as staying for their battle. This can forbid a rare
legal play that relies on a carrier screening or fighting its way through to its
aircraft.

One gap remains: a war declared during Combat Movement, by the mover or by a
neutral answering a peaceful entry where a carrier's route ends, can change
which zones aircraft may enter or hold a carrier in battle, and no check follows
it. Random play has not met it.

Under this rule seed 5090 is not stuck at all: the two carriers can swap zones,
the fleet carrier taking both bombers in P14 and the light carrier the fighter
in P15. The old checks, which demanded a complete plan after every single ship
move, never allowed the first half of that swap.

### Reviews

Independent reviews examined the change four times, each after the previous
one's fixes. The first found that route checks looked only where a force first
met other units rather than wherever it can stop, that engaging could hold a
carrier its aircraft needed, that Noncombat Movement could lose patrols without
counting them, that flight previews missed a fighter's effect on Enemy patrols,
that the plan search had no early failure or bound, and that aircraft launched
by a sailing carrier could not use other carriers. The second found that the
aircraft of a minor the mover controls, such as Dadao's, had dropped out of the
plan; that routes were held where only Enemy patrol aircraft stood, or where a
lone carrier left port; and that random play counted a carrier sunk in a
reaction battle as a broken plan. The third found the blocking described above.
The fourth found that a medium bomber, which takes two of a heavy carrier's
three seats, could be left with no legal action, and that ending Combat
Movement could lose two fighters where losing the bomber alone would do; that
entering port, which freezes every other naval move and patrol return for the
rest of the phase, could still leave patrols without a landing; and that route
checks solved more than before even with a complete plan. All confirmed defects
are fixed except the war-declaration gap. When several sets of aircraft lose
equally many, unit order rather than the player decides which are lost.

### Random play

The same 322 seeds as the dead-end search:

| 322 seeded eleven-round games | Before | First attempt | Final |
| --- | ---: | ---: | ---: |
| Games completing all eleven rounds | 322 | 306 | 322 |
| Games with no legal action | 0 | 1 | 0 |
| Games where moves stranded aircraft | not counted | 15 | 0 |
| Moves that raised the shortfall | not checked | not checked | 0 |
| Mean decisions per game | 1,625 | — | 1,651 |

The first attempt had two defects, both found by replaying the failing seeds: a
landing preview kept the fuel the aircraft had before its landing flight, so it
believed the aircraft could take off again if its carrier sailed; and a carrier
in port was treated as launching its aircraft in port, where they can land,
rather than at sea, where the engine leaves them. The final check compares the
shortfall between settled positions of both movement phases, with no naval move
or Chinese-truce battle pending. A rise no larger than the seats of the carriers
that dice sank or damaged counts as dice, and so does one after a declaration of
war, which the engine does not check; ending Combat Movement may lose no more
aircraft than the shortfall. Its first run found a gap that the earlier check,
which looked only at Combat Movement, could not see. In Noncombat Movement a
carrier could unload an aircraft onto adjacent land, which ended the carrier's
move, and in two games it did so while a fighter at sea still needed the carrier
to sail. On the user's ruling a carrier now cannot unload aircraft at all: an
aircraft takes off from it by flying and lands on it where it ends its move. A
carrier entering port falls under the landing rule. Removing carrier unloads
changed the course of 224 of the 322 games, and one of them then met an older
dead end. A submarine that KMT had captured left a port past Japanese cruisers
in Noncombat Movement and was forced to screen, a battle that phase cannot
fight, so KMT had no legal action. The engine's route check already lets
submarines pass Enemy surface warships, so a port exit now forces a screen only
on surface ships. In the final run no rise needed dice or a war to explain it,
and no aircraft was lost as Combat Movement ended.

The engine costs about the same. Per call, building a move list took 1.08 ms
against 1.15 ms before the landing rule, and applying a move 1.22 ms against
1.21 ms (random games on seeds 5000–5002, one process; the games differ, so
their positions do too). Random-play game times also include the test's own
checks and a serialized position per decision, so they overstate the engine's
cost.

## Shared GPU self-play

Each search asks the network about one position at a time, and on the CPU each
game process evaluated its own positions. The GPU is fast only on many positions
at once, so the work had to be gathered across processes:

- Eight game processes run four games each, one per thread, taking seeds from a
  queue. They keep the rules, the search and the preparation of the network's
  input.
- For each evaluation a game thread writes the prepared arrays into its own
  shared-memory buffer and sends a short note through its own pipe, then waits.
- A ninth, coordinating process collects every waiting position, evaluates them
  in one batch per alliance model on the GPU and sends back the move
  probabilities and values.

The coordinator repeats the network's own computation on arrays laid out in
advance by the game processes. On 48 real positions its move probabilities match
the CPU network within 2×10⁻⁷ and its values within 3×10⁻⁵.

Two changes made the coordinator fast enough to matter:

| Coordinator, 32 positions per batch | Time per position |
| --- | ---: |
| First version | 3.3 ms |
| Move probabilities on the CPU, after one copy back | 1.5 ms |
| Inputs sent in two copies that do not wait for the GPU | 0.94 ms |

On the Mac's GPU each separate small operation has a fixed cost: turning one
position's scores into probabilities took about 1 ms, and each blocking copy to
the GPU waited about 2 ms for earlier work to finish.

### Choosing the setup

Five-minute probes of the full eleven-round workload, with the CPU-only run's
settings:

| Setup | Evaluations per second | Requests per serving round | Coordinator busy | Game-process cores used |
| --- | ---: | ---: | ---: | ---: |
| 4 games per process | 635 | 12.0 | 94% | 8.8 |
| 6 games per process | 480 | 15.5 | 91% | 8.3 |
| 4 games per process, game processes at lower priority | 518 | 11.8 | 94% | 7.6 |

Every game slot played throughout these probes, which saw only the opening
rounds; they choose the setup, and the comparison with the CPU-only run uses
complete runs. More games per process made bigger batches but slowed
everything, because the game processes then compete with the coordinator for
cores; lowering their priority starved them instead. An earlier probe at four
games per process measured 602 per second with only 15 of its 32 games playing:
the seed queue can look empty to a process that asks before the seeds arrive,
so those game slots quit at once. Game slots now wait for a seed or an explicit
stop.

### The 32-game run

The run repeated the CPU-only run's production-like settings: hidden size 64,
two message layers, 16,384 token buckets, 64 simulations, depth cap 16, eleven
rounds, one thread per game and no learning updates. It played seeds 1951–1982
with PyTorch 2.14 and the engine of commit b89e86d, which had the landing rule
but not the later review fixes; those change only rare positions. The CPU-only
run played seeds 1951–1960 with PyTorch 2.11 and the engine before the landing
rule (873058a), which costs about the same per call.

| Eleven-round games | CPU only, 28 October | Shared GPU, 29 October |
| --- | ---: | ---: |
| Processes | 10, one game each | 8 with four games each, and a coordinator |
| Completed / failed | 10 / 0 | 32 / 0 |
| Batch wall time | 2,847 s | 4,958 s |
| Complete games per hour, one batch | 12.6 | 23.2 |
| Seconds per game: mean, range | 2,461; 2,066–2,847 | 4,562; 3,868–4,958 |
| Evaluations per game, mean | 84,928 | 84,123 |
| Evaluations per second, long run | 345 | 566 |
| Games per hour, long run | 14.6 | 24.2 |
| Complete games in eight hours, estimated | about 110 | about 180 |
| CPU cores used, average over the run | 7.8 | 8.2 |
| Peak charged memory | 9.14 GB | 10.0 GB |

A batch waits for its slowest game, and its rate depends on how many games it
holds, so the long-run rate is the fair comparison. A game needs about 84,000
evaluations in both setups, so games per hour follow from evaluations per
second. The GPU run's 566 per second was measured while all 32 games were
playing. The CPU-only run kept no record over time, so its 345 is the average
over each game's whole length; that includes the end of its run, when fewer
games ran and each may have gone faster. Averaged the same way, the GPU run
gives 25.3 games per hour, 1.73 times as many; the all-playing rate gives 1.66.

Each game takes longer, 76 minutes against 41, because four games share each
game process and every game waits on one coordinator; but 32 games play at once
instead of ten. The eight-hour estimates play each slot's games back to back at
the long-run pace, with game lengths drawn from each run, and count only games
that finish. They differ by 1.6 times, a little less than the hourly rates,
because the GPU's longer games leave more of them unfinished when the night
ends; the CPU-only figure matches its earlier estimate.

The coordinator now limits the speed. It was busy evaluating for 89% of the run,
and the games spent 59% of their time waiting for it, 13% preparing inputs
(about 7 ms of a game thread's time per position, including waits for the other
threads in its process) and 27% searching and simulating moves. Each serving
round collected 9.8 waiting positions on average, but they divide among the
three alliances' models, so a model call averaged 4.1 positions; a quarter of
calls held a single position.

Timed alone on 455 positions from random play
(`tools/profile_shared_coordinator.py`), a model call of four positions took 6.1
ms: 0.7 ms merging the positions' arrays, 0.4 ms sending them, 1.8 ms issuing
the network's 285 separate tensor operations, 2.9 ms waiting for the GPU and 0.3
ms reading the results. The GPU's time grows by about 0.65 ms per position,
mostly encoding each position's observation graph, which averages 3,650 nodes
and 10,900 edges built from 23,400 input tokens; at 32 positions it is
two-thirds of the call. So a call costs about 3 ms however small, and each
position adds about 0.9 ms: larger calls would cut the cost per position by at
most about 40%. Evaluating the three models in one call would save the fixed
part of two calls per round, and a cheaper observation-graph encoding would cut
the part that grows; neither has been tried. More games per process made larger
calls in the probes but slowed the games more.

The run stayed within the planned nine processes and the allowance, at most
10.0 GB of the 30 GB. Its long-run rate, 566 evaluations per second, is below
the five-minute probe's 635, which saw only the opening rounds. No learning
updates ran, so training adds to these times, and nothing here measures playing
strength. The same seeds do not force identical games.
