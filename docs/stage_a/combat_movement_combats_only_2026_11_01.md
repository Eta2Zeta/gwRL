# Combat Movement lists only land moves that start a combat — 1 November 2026

RB 7's order of play gives Combat Movement these tasks: declare combats and
move units accordingly, designate screening forces, escorts and raiders,
assign aircraft on Maritime Air Patrol, and declare convoy raiding. RB 9.1 lists
the combats: land, naval, artillery attrition, border clashes, airborne
assaults, strategic bombing, attacks on ships in port, carpet bombing,
amphibious assaults and convoy raiding. Repositioning is not among them, and
RB 11.1 leaves it to Noncombat Movement for units that have not moved. On the
user's ruling, Combat Movement now offers a land move only if it starts a
combat. The [evidence file](combat_movement_combats_only_2026_11_01.json) holds
the exact values.

## What changed

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
- Artillery attrition, Japan's surprise-attack choice, amphibious and airborne
  assaults, and every naval and air order are unchanged.

## Effect

- At the same positions the old engine listed exactly the removed moves in
  addition. Six random 3-round games were played on the new engine, and the
  engine before the change listed its menu at every fourth Combat Movement
  position (295) and every fourth Noncombat Movement position (151). Combat
  Movement menus fell from 19,120 to 13,545 options (−29%). All 5,575 removed
  options were land moves into friendly land, and nothing else changed.
  Noncombat Movement menus were identical.
- Scripted games now play differently, because the scripted player used to
  reposition during Combat Movement:

| Scripted game | 3 rounds, before | after | 11 rounds, before | after |
| --- | ---: | ---: | ---: | ---: |
| Decisions | 549 | 517 | 1,971 | 1,908 |
| Combat Movement options | 14,357 | 9,448 (−34%) | 48,195 | 31,353 (−35%) |
| Mean Combat Movement list | 71.1 | 54.3 | 65.0 | 48.2 |
| Noncombat Movement decisions | 24 | 35 | 56 | 161 |
| Mean Noncombat Movement list | 42.9 | 40.9 | 37.9 | 87.0 |
| All options in the game | 22,130 | 15,116 | 77,358 | 80,647 |

- The moves themselves remain: they are now made after the battles. In the
  eleven-round game the scripted player made 117 land moves in Noncombat
  Movement instead of 12, and its Noncombat lists more than doubled, so the game
  as a whole did not get shorter lists. Final scores changed as well (Axis 51.3
  → 28.9 in eleven rounds): scripted play is a fixed heuristic, and this says
  nothing about trained play.

## Verification

- A new movement test: armor with friendly zones beside it and enemy land beyond
  one of them is offered only the attack through the friendly zone in Combat
  Movement, a direct repositioning move is refused without changing the state,
  and Noncombat Movement still offers both repositioning moves. The test fails
  on the code before the change.
- The training-interface test that used a Combat Movement move from Honshu to
  Tokyo as "real progress" now uses an attack on KMT-held Hopeh.
- C++: all 27 suites pass. `campaign_env` needs about 38 s in this container,
  over its 30-second limit, as before.
- The dead-end search played 60 random eleven-round games: all finished all
  eleven rounds, with no game left without a legal action, no landing-rule
  failure and no stranded aircraft.
- Python: 464 tests, with the same 7 failures and 48 errors as the unchanged
  code, all from this container.

## Not yet covered

- **Zones that changed hands this turn without capture,** for example through
  an alignment. Combat Movement could enter them before; Noncombat Movement
  cannot, because it requires zones held since the turn began. RB 11.1 forbids
  only zones "captured this Player Turn". Until that is ruled on, such moves are
  possible in neither phase. None of the 5,575 removed moves at the matched
  positions passed through such a zone.
- **Planes** keep their full Combat Movement menus. Stopovers are a third of all
  Combat Movement options in the eleven-round scripted game. A combat-only rule
  keeps attacks, bombing, escorts, airborne assaults, port attacks and patrols.
  It keeps stopovers only for a plane leaving a carrier that sails later and for
  an air transport collecting troops, which is the complete-orders question.
- **Ships** keep their full menus too. In the 3-round scripted game none of the
  24,252 lone-ship Combat Movement routes entered or passed a zone with enemy
  warships or patrol planes, 54% ended beside enemy land, and the other 46% were
  plain sailing. A combat-only rule keeps routes into or through zones with
  enemy warships or patrol planes, routes that set up amphibious assaults or
  shore bombardment, moves into zones with units of nations at peace, and moves
  to positions where ships are designated as escorts. The ship-order
  completion check must then require such a route. This scenario has no convoy
  lines, so convoy raiding cannot occur in it.

## Compatibility

Legal moves changed in both action profiles, so recorded games with a Combat
Movement land move into friendly land no longer replay. As in earlier rules
fixes, the version strings are unchanged.

## Reproduce

```sh
build/<dir>/movement_tests
./.venv/bin/python tools/fuzz_campaign_dead_ends.py --output OUT --games 60 --rounds 11 --processes 3
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 3 --seeds 1951
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 11 --seeds 1953
```
