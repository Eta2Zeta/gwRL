# Combat Movement lists only moves that start a combat — 1 November 2026

RB 7's order of play gives Combat Movement these tasks: declare combats and
move units accordingly, designate screening forces, escorts and raiders,
assign aircraft on Maritime Air Patrol, and declare convoy raiding. RB 9.1 lists
the combats: land, naval, artillery attrition, border clashes, airborne
assaults, strategic bombing, attacks on ships in port, carpet bombing,
amphibious assaults and convoy raiding. Repositioning is not among them, and
RB 11.1 leaves it to Noncombat Movement for units that have not moved. On the
user's ruling, Combat Movement now offers land units and planes only moves that
start a combat. Ships are not done yet. The
[evidence file](combat_movement_combats_only_2026_11_01.json) holds the exact
values.

## What changed

Land units:

- A land route in Combat Movement, ordinary, towing or across a narrow
  crossing, is offered only if it attacks. It attacks when its target has no
  possessor, or a possessor that is neither the mover nor politically friendly
  to it: an enemy, or a neutral nation, which the attack declares war on. This
  is the engine's existing test for registering a land battle, now shared by
  the menu and the move.
- The route search still passes through friendly land, so a target two zones
  away is still reached through a friendly zone.
- Applying a Combat Movement land move that attacks nothing is refused.
- Blitzes (RB 10.5.1) are unchanged. They are separate orders in the Combat
  phase after a battle won within two rounds, and can never enter friendly land.

Planes:

- A Combat Movement flight is now an attack (ground attack, bombing, escort,
  support, airborne assault or port attack), the start of a patrol, or a stop
  by an air transport or strategic bomber at a land zone where it can pick up
  airborne infantry. RB 9.3.2 lets them pick up airborne infantry "before or
  during their combat movement". Every other stopover is gone.
- A plane already in the air may still land. That covers a plane left in the
  air by a carrier that sailed, and an air transport after collecting
  paratroopers.
- Applying any other Combat Movement flight is refused. The pickup check is
  the same test the menu uses for loading cargo.
- A plane on a carrier that sails needs no stopover of its own: the engine
  leaves it in the air over the carrier's starting zone, from where it can still
  attack or land.
- Split flights remain in Noncombat Movement.

Artillery attrition, Japan's surprise-attack choice, amphibious assaults and
every ship order are unchanged.

## Effect

At the same positions the engine before each change listed exactly the removed
options in addition, and nothing else differed. Each check used six random
3-round games played on the new engine, comparing every fourth Combat Movement
and every fourth Noncombat Movement position:

| Matched positions | Combat Movement options before | after | Removed |
| --- | ---: | ---: | --- |
| Land change (295 positions) | 19,120 | 13,545 (−29%) | 5,575 land moves into friendly land |
| Plane change (214 positions) | 10,317 | 5,832 (−43%) | 4,485 stopovers: 1,784 by tactical bombers, 1,680 by fighters, 1,021 by seaplanes |

Noncombat Movement menus were identical in both checks (151 and 180 positions).

Scripted games play differently after the land change, because the scripted
player used to reposition during Combat Movement:

| Scripted game | 3 rounds: start | land | planes | 11 rounds: start | land | planes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Decisions | 549 | 517 | 525 | 1,971 | 1,908 | 1,908 |
| Combat Movement options | 14,357 | 9,448 | 4,197 | 48,195 | 31,353 | 16,472 |
| Mean Combat Movement list | 71.1 | 54.3 | 24.3 | 65.0 | 48.2 | 25.5 |
| Mean Noncombat Movement list | 42.9 | 40.9 | 31.9 | 37.9 | 87.0 | 86.8 |
| All options in the game | 22,130 | 15,116 | 9,518 | 77,358 | 80,647 | 65,985 |

- Combat Movement lists are now about a third of their size at the start.
- Land repositioning now happens after the battles. In the eleven-round game
  the scripted player made 117 land moves in Noncombat Movement instead of 12,
  and its Noncombat lists more than doubled.
- Final scores changed with the land change (Axis 51.3 → 28.9 in eleven
  rounds). Scripted play is a fixed heuristic, so this says nothing about
  trained play.

## Verification

- A new movement test: armor with friendly zones beside it and enemy land beyond
  one of them is offered only the attack through the friendly zone in Combat
  Movement. A direct repositioning move is refused without changing the state,
  and Noncombat Movement still offers both repositioning moves.
- New air tests: in Combat Movement a fighter is offered attacks but no
  stopover, and a stopover applied directly is refused. A carrier that sails
  leaves its fighter in the air, and the fighter lands on another carrier; in
  Noncombat Movement it then cannot move until its own carrier sails, and then
  may only land. An air transport's only Combat Movement stop is the zone of its
  airborne infantry, which it then loads.
- Both new tests fail on the engine before their change.
- Tests that used Combat Movement stopovers changed accordingly:
  - The split-flight, carrier-launch and controlled-minor landing tests now run
    in Noncombat Movement, where split flights remain.
  - The seed-5090 landing-plan test checks the planner directly.
  - The patrol test checks that no plain flight is offered.
  - The training-interface test's "real progress" move is now an attack on
    KMT-held Hopeh.
- C++: all 27 suites pass. `campaign_env` needs about 35–38 s in this container,
  over its 30-second limit, as before.
- The dead-end search played 60 random eleven-round games after each change.
  All finished all eleven rounds, with no game left without a legal action, no
  landing-rule failure and no stranded aircraft.
- Python: 464 tests, with the same 7 failures and 48 errors as the unchanged
  code, all from this container.

## Land handed over by an alignment

When a minor power aligns, all its land passes to the nation it joins (RB 4.6).
The glossary lists alignment and capture as different ways to gain possession.
RB 11.1 bars Noncombat Movement only from land "captured this Player Turn".
RB 4.6's example lets the Major Power "land aircraft in the Minor Power's land
zones in the same Player Turn".

The engine required land held since the turn began for every move outside
combat. With the Combat Movement filter above, newly aligned land could be
entered in neither phase. For example, a warlord that Japan attacks may join
Dadao, Japan's puppet, at the end of Japan's Combat Phase. Japan then could not
move into that land, or land aircraft there, until its next turn.

On the user's ruling, land that joined the mover, or a nation friendly to it,
this turn may now be entered outside combat:

- by Noncombat Movement land moves, including moves through it;
- by aircraft landing, after combat and in Noncombat Movement (RB 10.10, 11.3);
- by cargo unloaded from aircraft and ships.

Unchanged:

- Land captured or liberated this turn stays closed. So does land that aligned
  and was then captured in the same turn.
- Strategic rail (RB 11.2), supply paths (RB 1.11) and the placement of new
  units and facilities (RB 12.1) still require land possessed since the turn
  began, as those rules say.

An alignment marks each territory it hands over. A capture, liberation or
transfer clears the mark, and so does the start of the next Player Turn. The
network reads the whole observation, so it sees the mark, but only during the
turn in which it applies.

Verification:

- A new movement test: before the alignment, Noncombat Movement offers no move
  into a warlord's land and no landing there. After the warlord joins Japan,
  both are offered. Neither is offered after Japan captures the land, even land
  that joined the KMT earlier in the turn. The test fails on the engine before
  the change.
- A runtime test checks that a new turn removes an old mark and keeps the
  territory's other flags. It fails without that step.
- Matched menus: the engine before the change listed its menu at 788
  positions, every second Combat Movement and Noncombat Movement position of
  six random 3-round games. Every menu was identical. Land had aligned during
  the turn at 36 Noncombat positions, but each time it went to a side the mover
  may not enter: to the KMT or CCP while Japan moved (31), or to the KMT while
  the CCP moved (5).
- 54 more random eleven-round games had 746 Noncombat positions with land
  aligned that turn. At the 17 where some option named such land, the options
  were Japanese flights across land that had just joined the KMT or CCP, and
  the engine before the change listed the same menus. So random play never met
  the new rule. It applies, for example, when a warlord that Japan attacks
  joins Dadao.
- The dead-end search played 60 random eleven-round games, once before and once
  after the turn-start step. All finished all eleven rounds, with no game left
  without a legal action and no notes; each game made the same number of
  decisions in both runs.
- C++: all 27 suites pass. `campaign_env` again needs about 34 s, over its
  30-second limit. Python: 464 tests, with the same 7 failures and 48 errors as
  before, all from this container.

## Not yet covered

- **Supply through land a controlled nation hands over.** RB 1.11 traces
  supply through land "possessed by you or a controlled/Aligned nation, since
  the beginning of the Player Turn". The engine requires the same possessor all
  turn, so land that Dadao hands to Japan carries no Japanese supply path for
  the rest of that turn. This was not changed.
- **Ships** keep their full Combat Movement menus.
  - In the 3-round scripted game, none of the 24,252 lone-ship Combat Movement
    routes entered or passed a zone with enemy warships or patrol planes. 54%
    ended beside enemy land, and the other 46% were plain sailing.
  - A combat-only rule keeps routes into or through zones with enemy warships
    or patrol planes, routes that set up amphibious assaults or shore
    bombardment, moves into zones with units of nations at peace, and moves to
    positions where ships are designated as escorts.
  - The ship-order completion check must then require such a route.
  - This scenario has no convoy lines, so convoy raiding cannot occur in it.

## Compatibility

Legal moves changed in both action profiles, so recorded games with these
Combat Movement moves no longer replay. As in earlier rules fixes, the version
strings are unchanged.

## Reproduce

```sh
build/<dir>/movement_tests
build/<dir>/air_tests
./.venv/bin/python tools/fuzz_campaign_dead_ends.py --output OUT --games 60 --rounds 11 --processes 3
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 3 --seeds 1951
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 11 --seeds 1953
```
