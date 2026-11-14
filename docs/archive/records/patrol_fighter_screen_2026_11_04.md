# A patrol fighter bars the way on — 4 November 2026

RB 9.3.1 lets surviving ships continue their move after a patrol plane's single
round against them, with one exception: if the plane is a Fighter, a screening
force is required to continue moving (RB 9.4.2). The engine let ships sail on
past a fighter as past any other patrol plane. At the user's request it now
applies the exception. The [evidence file](patrol_fighter_screen_2026_11_04.json)
holds the exact values.

## The rule as the engine reads it

- **When it applies.** A Fighter or Jet Fighter on patrol has fought entering
  ships for its single round and survived. A plane that let them pass and a
  patrol bomber or seaplane are unchanged.
- **What the ships may do.** If their route goes on beyond its sea zone, they
  may divide into a screening force, which stays to fight in the Combat Phase,
  and a continuing force, which waits for the screen. Or they may end their
  whole move in the fighter's zone (`naval_screen_stop_route`), since they owe
  no further combat there.
- **No sailing on later.** Ships that stop in the fighter's zone, or whose route
  ends there, may not start another voyage that phase, which would continue
  their move without a screen. The engine counts their movement as spent. They
  may still attack the fighter where they are.
- **The screening battle.** The fighter chooses again whether to fight, before
  any scramble ([RCL-020](patrol_choice_2026_11_04.md)). If it stays out, it has
  declined combat, the screen wins and the continuing force sails on (RB 9.4.2).
  If it fights and survives, the screen has lost and the continuing force turns
  back to the sea zone it came from.
- **Submarines.** A fleet of submarines alone still sails on. RB 9.4 says of
  submarines entering a patrol plane's zone that the survivors of its single
  round may continue, and they could never win a screen against a fighter,
  which they cannot hit.
- **A lone raider.** A Battlecruiser raider, which cannot divide, may instead try
  to slip through (RB 9.4.4), as past other Enemy units.

## What changed in the engine

- `encounter` asks for a screen when a fighter that fought the ships still
  stands in their way on. The fighter is recognized from what the engine already
  records: its single round stamps it with this turn's battle mark, and the
  ships lose the mark of having been let pass when a patrol engages them. A
  fighter that fought earlier ships that turn and lets these pass does not bar
  them.
- The screening choice also offers to end the move when only such a fighter
  bars the way.
- Ending the move, or a route that ends beside such a fighter, counts the
  ships' movement as spent (`endVoyage`). Before this, a random game (seed 7193)
  showed the gap: a transport stopped beside the fighter, then began a second
  voyage and sailed on.

No name was added, so the network input is unchanged: the layout stays
`campaign-zone-v1-1d3c25d19abf2937`. Some positions now have different legal
moves.

## Known limit

Two nations' patrol planes in one sea zone react one nation at a time, and the
ships carry a single let-pass mark. If one nation's fighter fights them and
another nation's plane then lets them pass, the fighter no longer bars their
way.

## Checks

- **Unit test.** `naval_movement_tests` case "patrol fighter bars the way on":
  two Japanese destroyers sail from P16 through P15, where a KMT fighter
  patrols, towards P14.
  - After the fighter's single round they are asked for a screen, and may stop
    instead. Ships that stop cannot start another voyage that phase.
  - With one destroyer screening, the screening battle faces the fighter. If it
    stays out, the other destroyer sails on to P14. If it fights and sinks the
    screening destroyer, the other turns back to P16.
  - If the fighter lets them pass, they sail on. A patrol tactical bomber does
    not bar them, and after a bomber's round at the end of their route they may
    still sail on later.
  - When their route ends in P15, they get no screen and no battle, and cannot
    sail on later. A third destroyer that the same fighter later lets pass sails
    on.
- **Each part is needed.** Undoing each of eight parts in turn makes the test
  fail: the barrier itself, the offer to stop, the let-pass mark, keeping the
  barrier out of a route's last zone, limiting it to fighters, and the three
  ends of a voyage (after stopping, at a route's end, and only for fighters).
- **Suites.** All 26 C++ suites and the Python suite (455 tests, 3 skipped)
  pass.
- **Random games.**
  - 800 random eleven-round games (seeds 9000 to 9799) found no dead end,
    engine error or move that changes nothing.
  - The 240 games of `tools/check_zone_names.py` (seeds 7000 to 7239, 372,857
    decisions) met no unlisted name.
  - In 480 games with the same random policy (seeds 7000 to 7479), patrol
    planes fought entering ships' single round 74 times. A screen owed only to
    a fighter came up in one game, seed 7193: a captured KMT transport leaving
    port into P14 met a Japanese patrol fighter, stopped, and then attacked it
    where it stood. In the Combat Phase the fighter accepted and Japan scrambled
    two ships.
- **Not measured: speed.** The engine looks at the patrol planes that already
  reacted, once more per zone a fleet enters. No timing was taken.
