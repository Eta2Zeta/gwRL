# Aircraft move once per turn — 1 November 2026

Rulebook 11.1: "During Non-combat Movement Phase you may move your units that
did not move during combat movement." Land units and ships already followed
it: any move in Combat Movement marks the unit `combat_move`, and noncombat
moves refuse marked units. Aircraft did not. A plane that flew in Combat
Movement without attacking, stopping in the air or landing, kept its leftover
movement and could fly again in Noncombat Movement. The Tokyo fighter, for
example, could fly to Honshu and land at Kyushu in Combat Movement, then still
had 3 movement points and 22 options in Noncombat Movement. Now it has none.
The [evidence file](aircraft_single_move_2026_11_01.json) holds the exact
values.

## What changed

- A flight in Combat Movement marks the plane `combat_move`, as moves already
  mark land units and ships.
- In Noncombat Movement a marked plane on the ground gets no flight, no
  landing elsewhere and no cargo pickup. It may still unload cargo where it
  stands.
- A marked plane on a carrier that sails in Noncombat Movement is left in the
  air, as every carrier's own aircraft are. It may then land, on the carrier or
  anywhere in reach, but not fly anywhere else.
- Patrols still end in Noncombat Movement (RB 9.3.1). Planes that attacked
  still land right after their battle, in the Combat phase (RB 10.10).
- The landing planner no longer counts a marked plane on a carrier as able to
  fly off and free its seat. In Combat Movement this is slightly stricter than
  before. A move that relied on such a plane taking off again is refused until
  that plane has actually flown off, so the same positions stay reachable in
  another order.

## Effect

- Scripted games do not change. In the matched 3-round and 11-round games the
  choices, dice, final scores and every menu's size are identical: scripted
  play never moves a plane in Combat Movement without attacking.
- Random play changes very little. Six random 3-round games were played on
  the new engine, and the engine before the change listed its menu at the same
  positions. That covered all 338 Noncombat Movement positions where some plane
  had already flown, and every fourth such Combat Movement position (396).
  Combat Movement menus were identical (23,865 options). Noncombat Movement
  menus lost 10 of 8,537 options, all second moves by planes that had flown: 8
  landings elsewhere and 2 flights. Nothing else changed. Random play seldom
  leaves such a plane movement to spare, so this is a rules correction, not a
  menu-size saving.

## Verification

- A new air test covers four planes: one that hopped and landed in Combat
  Movement, one that stayed put, one on patrol, and one whose carrier sails in
  Noncombat Movement. Applying a second flight directly is refused too. The
  test fails on the code before the fix. A second test checks that an ally can
  still board a transport that flew on its owner's own turn, since that
  transport keeps its owner's marks until that nation's next turn.
- C++: all 27 suites pass. `campaign_env` needs about 33 s in this container,
  over its 30-second limit, as before.
- The dead-end search played 60 random eleven-round games. All finished all
  eleven rounds, with no game left without a legal action, no landing-rule
  failure and no stranded aircraft.
- Python: 464 tests, with the same 7 failures and 48 errors as the unchanged
  code, all from this container: 33 need PyTorch, 21 configure more CPU cores
  than its 4, one checks a macOS-only memory measure.

## Rule verdicts

1. **Planes land after combat in the Combat phase, right after their battle.**
   RB 7's order of play lists "Move aircraft returning from combat" under the
   Combat Phase. RB 10.10 says "Aircraft returning from combat must use their
   remaining movement points to return to a suitable landing spot", and the
   bombing sequences end with "Attacker lands his aircraft". The engine already
   does this. Patrols are the exception: they end in Noncombat Movement
   (RB 9.3.1).
2. **Flying without attacking counts as moving.** RB 11.1 speaks of units that
   "did not move", not units that did not attack. RB 7 also lists only these
   for Combat Movement: declaring combats and moving units accordingly,
   screening forces, escorts, raiders, patrols and convoy raiding. Plain
   repositioning is not among them. The engine still allows it for every unit
   type, and planes need it when a sailing carrier leaves them in the air. It
   now counts as the turn's move for every unit type.
3. **Landing and taking off again in one phase is not covered by the
   rulebook.** In this engine it reaches nothing new. Landing does not restore
   movement, and a carrier that sails leaves its planes in the air rather than
   carrying them. It only adds duplicate options, so it is left for the
   complete-orders decision.

## Compatibility

Legal moves changed in both action profiles, so recorded games in which a plane
flew again in Noncombat Movement no longer replay. As in earlier air fixes, the
rules version strings are unchanged.

## Reproduce

From the repository root, after building the C++ tests and the extension:

```sh
build/<dir>/air_tests
./.venv/bin/python tools/fuzz_campaign_dead_ends.py --output OUT --games 60 --rounds 11 --processes 3
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 3 --seeds 1951
./.venv/bin/python tools/decision_census.py census OUT.jsonl --policy balanced --rounds 11 --seeds 1953
```
