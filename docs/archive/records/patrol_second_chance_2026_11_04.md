# A patrol plane's second chance against ships it let pass — 4 November 2026

Earlier on 4 November the user ruled that a patrol plane that lets ships pass
settles combat with them for the turn (RCL-017), and the engine was changed to
match. Asked to weigh RB 0.3 against that ruling, the user reversed it the same
day: the ships may attack the plane anew, and it may accept. The
[evidence file](patrol_second_chance_2026_11_04.json) holds the exact values.

## The rule

Recorded as
[RCL-017](../../../game_content/rules/clarifications.md#rcl-017-a-patrol-planes-second-chance-against-ships-it-let-pass),
revised, in the naval rules profile and in the rules reader:

- RB 0.3 lists a patrol plane's refusal among the ways units at war come to
  share a sea zone. Such units take no part in combat until one power makes a
  new combat move against the others there.
- So the ships a patrol plane let pass may attack it later in Combat Movement.
  In the Combat Phase it chooses again by the patrol rule
  ([RCL-020](patrol_choice_2026_11_04.md)), before any scramble: it may stay
  out unless the Attacker has aircraft with an attack value present.
- If it stays out, it has declined combat again. If it fights and survives, it
  stops an amphibious assault from its sea zone (RB 10.8.1), which is then
  called off (RCL-018).
- Until they attack it anew, it is not in their screening battle or the battle
  where their route ends, and it does not count against their screening or
  their landing (RB 9.4.2 and 10.8.1). This part is unchanged.

## What changed in the engine

- **The attack is offered again.** The ships' force selection offers
  `naval_engage_force` against any Enemy unit at sea in their zone, a patrol
  plane that let them pass included, and the battle takes the plane in as a
  defender. Before, the plane was left out, and with nothing else there the
  attack was not offered.
- **Fighting ends the letting pass.** `patrolLetPass` is now false for a plane
  that has fought a battle this turn. On an Enemy turn a patrol plane fights
  battles only in the Combat Phase, after the ships it let pass have moved, so
  this marks a plane that accepted an attack. It then counts against their
  screening and their landing. Each plane's own choice counts: when two planes
  share a zone and one stays out while the other fights, only the one that
  stayed out still lets the ships pass.
- **Unchanged.** The ships still carry the mark `map_declined_combat` while
  they stay in the plane's zone. A plane that let them pass still does not hold
  them there when the engine works out where a carrier can still sail
  (`navalEndZones`), since units may freely leave a shared zone (RB 0.3).

No name was added, so the network input is unchanged: the layout stays
`campaign-zone-v1-1d3c25d19abf2937`. Some positions now have more legal moves.

## Known limits

- Ships whose route ended in the plane's zone in a battle with other defenders
  are committed to that battle and cannot then attack the plane anew. Other
  ships of the Attacker in the zone can, and their attack joins that battle.
- A continuing force that sails on in the Combat Phase, after a screening
  battle, may enter the zone of a patrol plane that already fought there that
  turn. If the plane lets it pass, it still counts against that force's landing
  there, because it has fought a battle this turn. The engine reads RB 10.8.1's
  exemption as one for a plane that has declined combat, not for one that has
  fought.

## Checks

- **Unit test.** `naval_movement_tests` case "patrol plane may fight ships it
  let pass": a KMT patrol fighter in P15 lets a Japanese transport and its
  escort pass.
  - The transport may still declare its landing in Korea, and both ships may
    attack the plane.
  - The escort attacks it, and the battle's only defender is the plane. In the
    Combat Phase the plane is asked first whether to fight.
  - If it stays out, nothing is lost and the landing may begin.
  - If it fights and sinks the escort, the landing is called off and the
    infantry stays aboard.
  - A ship that started the turn beside the plane may engage it, and a ship
    entering later gets a fresh choice, as before.
- **Each part is needed.** Undoing each of three parts in turn makes the test
  fail: leaving the plane out of the attack, not offering the attack, and
  keeping the exemption for a plane that fought.
- **Suites.** All 26 C++ suites and the Python suite (455 tests, 3 skipped)
  pass.
- **Random games.**
  - 800 random eleven-round games (seeds 9000 to 9799) found no dead end,
    engine error or move that changes nothing.
  - The 240 games of `tools/check_zone_names.py` (seeds 7000 to 7239, 372,910
    decisions) met no unlisted name.
  - In 480 games with the same random policy (seeds 7000 to 7479), patrol
    planes let ships pass 71 times. Ships attacked a plane that had let them
    pass once, in seed 7021: a captured KMT transport attacked the two Japanese
    patrol planes in P15. In the Combat Phase each was asked first and stayed
    out, so the battle ended at once with nothing scrambled into it.
- **Not measured: speed.** The change adds one flag lookup when the engine asks
  whether a plane let ships pass, and makes the attack check cheaper. No timing
  was taken.
