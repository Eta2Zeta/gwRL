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

## Not yet covered

- **Zones that changed hands this turn without capture,** for example through
  an alignment. Combat Movement could enter them before; Noncombat Movement
  cannot, because it requires zones held since the turn began. RB 11.1 forbids
  only zones "captured this Player Turn". Until that is ruled on, such moves are
  possible in neither phase. None of the 5,575 removed land moves at the
  matched positions passed through such a zone.
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
