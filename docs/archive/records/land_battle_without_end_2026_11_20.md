# A land battle that no unit could end — 20 November 2026

At 21:08 on 20 November 2026 a game of the long training run's run started at
16:22 (`tmp/training-2026-11-20b`, commit `1463ff4`) failed after 33 minutes of
play, and its game process kept the position before the failing move, as a
failed move keeps it since choice C of Q-012. The
[evidence file](land_battle_without_end_2026_11_20.json) holds the failed
game's record, the battle, its three units, the decision and the replay's
outcome; the kept position itself is
`tmp/training-2026-11-20b/run/failed-positions/game-1414-seed-7083393789849635443.json`
(its SHA-256 is in the evidence file).

- **The battle.** In Japan's combat phase of game round 8, Japan attacked the
  KMT in Manchuria-Rehe with a Self-propelled Artillery from Korea and an
  Anti-aircraft Artillery landed from sea zone P14 by a Naval Transport; the
  KMT defended with one Anti-aircraft Artillery. After the first round's fire
  Japan chose to retreat, and the engine asked where the Self-propelled
  Artillery should go: Korea was the only choice.
- **The failing move.** A copy of the game that the search played took that
  retreat. The two Anti-aircraft Artillery units were then left: the KMT's,
  which fires only at aircraft and only in the first round, and Japan's, which
  cannot fire at land units either and, having come by sea, cannot retreat.
  Rounds passed with no dice to roll and no choice to make, and after three of
  them within one move the engine stopped the game with "Land battle
  land_battle_42 in land_manchuria_rehe cannot end: rounds pass with no dice and
  no choice" (`retreatDecision` in `src/land_combat.cpp`).
- **The replay.** `tools/replay_failed_move.py`, run with the run's own code on
  21 November, played the move again from the kept position and failed with the
  same error: `same_failure`, a defect of the rules as the engine applies them,
  not damaged memory.
- **How rare.** It is the only game of the long run's four runs, 9,576 games
  trained on from 19 November 19:58 to 21 November 07:40, that failed this way.

## What this shows and does not show

It shows a position that the printed rules give no way out of. Land combat
repeats its rounds "until the battle is over" (Global War 1936 v4.3 rulebook,
section 10.5, page 64, step 10); amphibiously assaulting land units can neither
retreat nor blitz and must continue the attack until combat is resolved
(section 10.8.3, page 71); and Anti-aircraft Artillery fires only in the first
round of combat, at aircraft, though it may be taken as a casualty in any round
(section 10.2, page 61). With only those two units left, no round can resolve
the battle.
[Q-014](../../questions.md#answered) asks how
such a battle should end; it has since been answered, as RCL-023.

It does not show how often the search's copies reach such positions without the
game failing: a copy's failure fails the game only when the search reaches it,
and the engine stops the battle before any loop, so the run spends no time in
it. Nor does it bear on the crashes of game processes: this game failed and
reported its failure, and its process went on.
