# A patrol plane's own choice in a sea battle — 4 November 2026

Ships already in a patrol plane's sea zone may attack it, and the battle is
fought in the Combat Phase. The engine gave the plane in that battle the choice
the rulebook gives aircraft on a carrier (RB 10.7, step 2), after the scrambles,
and destroyed it if it stayed out and its side lost. On the user's ruling
(RCL-020) it now chooses by the patrol rule, before any scramble. The
[evidence file](patrol_choice_2026_11_04.json) holds the exact values.

## The rule

The user ruled on 4 November that a patrol plane and an aircraft on a carrier
choose by different rules, and that the plane chooses before ships scramble.
Recorded as
[RCL-020](../../game_content/rules/clarifications.md#rcl-020-a-patrol-plane-attacked-in-its-own-sea-zone),
in the naval rules profile and in the rules reader:

- The plane may stay out unless the Attacker has aircraft with an attack value
  present (RB 9.3.1 and 9.4), and staying out costs it nothing.
- It chooses before any scramble. If it stays out and nothing else of its side
  defends, there is no battle and nothing to scramble into (RB 10.4).
- Staying out lets those ships pass for the rest of the turn, as in RCL-017.

The scramble ban for the single round a patrol plane fights against entering
ships, during Combat Movement, was already in place (RB 9.3.1: other units may
not take part).

## What changed in the engine

- **The plane chooses first.** A sea battle's first step is now
  `naval_patrol_choices`. Each defending patrol plane is asked
  `naval_patrol_engage` or `naval_patrol_decline` before ships scramble
  (`naval_scramble`) and before fighters do. The single round against entering
  ships keeps the choice made when they entered.
- **Staying out is free.** A plane that stays out leaves the battle, keeps its
  patrol and is never removed with a lost battle. The ships it would have fought
  get the RCL-017 mark `map_declined_combat`. A battle with no defender left ends
  at once.
- **Attacking aircraft hold it.** A patrol plane may stay out, or let ships pass
  as they enter, only if the Attacker has no aircraft with an attack value in the
  zone. Strategic bombers and air transports have none. Before, the engine
  offered the choice regardless.
- **Carrier aircraft are unchanged.** They keep the deck choice
  `air_ground_or_defend`.
- **Screening.** A screening battle, and the battle where a route ends, no longer
  include a patrol plane that let the fleet pass, and now include one that fought
  its single round, which chooses again. The screen wins when the planes left in
  the zone all stayed out or let the fleet pass (RB 9.4.2); before, any of them
  made it lose.
- **One battle a turn.** A patrol plane that already fought a battle that turn
  stays out of another (RB 10.1).

## What changed in the input

New names: the moves `naval_patrol_engage` and `naval_patrol_decline`, the
decision `naval_patrol_participation`, the battle stage `naval_patrol_choices`
and the battle notes `naval_patrol_choices` and `naval_patrol_declined`.

The layout changed from `campaign-zone-v1-a44069d0dfe2c7c0` to
`campaign-zone-v1-1d3c25d19abf2937`:

| Part | Before | After |
| --- | ---: | ---: |
| Board, per zone | 42,520 | 42,737 |
| Position | 6,634 | 6,637 |
| Each move | 12,667 | 12,673 |
| Network parameters, 64×2 | 4,089,928 | 4,104,392 |
| Network parameters, 256×8 | 20,239,624 | 20,297,480 |

Each new battle note brings the usual 91 board questions, and the new stage 35:
one as a stage and 34 as a word a note can hold. The position gains three
questions for the new decision, and a move two kinds and four stage roles.
Networks and checkpoints of the old layout cannot be used with the new one.

## Checks

- **Unit tests.** New cases in `naval_combat_tests`:
  - The plane is asked first, before any scramble.
  - If it stays out, the battle ends with nothing scrambled, the plane keeps its
    patrol and the ship carries the RCL-017 mark; the game replays identically.
  - If it fights, the port's ship is asked to scramble next.
  - Attacking aircraft leave it no choice.
  - Beside a destroyer that loses, it survives.

  New cases in `naval_movement_tests`:
  - A tactical bomber in the zone stops a patrol plane from letting ships pass;
    a strategic bomber does not.
  - A screening battle leaves out a plane that let the fleet pass and includes
    one that fought its single round. When that one stays out, the screen wins
    and the rest sail on.
- **Each part is needed.** Undoing each of seven parts in turn makes a test fail:
  the early end, the attacking-aircraft rule in battle and on entry, the skipped
  deck choice, the screening battle's defenders, the screening result and the
  RCL-017 mark.
- **Suites.** All 26 C++ suites and the Python suite (455 tests, 3 skipped) pass.
- **Random games.** 800 random eleven-round games (seeds 9000 to 9799) found no
  dead end, engine error or move that changes nothing. The 240 games of
  `tools/check_zone_names.py` (seeds 7000 to 7239, 372,917 decisions) met no
  unlisted name. In them the new choice came up 13 times in 11 games (the plane
  stayed out 6 times and fought 7), entry reactions 78 times, none held by
  attacking aircraft, and the deck or ground choice 442 times.
- **Not measured: speed.** A battle with a defending patrol plane asks one
  question instead of another, so no timing was taken.

Found in passing: `tools/check_zone_names.py` compares a scheduled move's label
(`play`, `interrupt`) with `end_phase`, so its early phase ends never happen.
Its games still all finish. Not changed here.
