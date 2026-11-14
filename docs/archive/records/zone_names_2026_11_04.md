# Every name the engine writes gets a question — 4 November 2026

The network input translates the engine's names into questions through fixed
lists, and a name missing from its list falls into a shared "other" question. A
random check on 3 November found 31 missing names. The railroad ones were fixed
earlier the same day ([record](rail_repair_encoding_2026_11_04.md)); the user
then asked to fix all the rest. Looking for them turned up more:
- two prices;
- 20 battle notes that only the engine's source names;
- one mark;
- the words in battle notes, which the encoder dropped without counting them.

Now 480 random games meet no unlisted name, and tests read the engine's source
for new ones. The [evidence file](zone_names_2026_11_04.json) holds the exact
values.

## What was missing

| Group | Names | Before | Now |
| --- | --- | --- | --- |
| Battle notes seen in random games | 16, such as `naval_pairing_done`, `reaction_context`, `map_attack` and `air_hit_queue` | `battle_data:other` | their own questions |
| Battle notes only the engine's source names | 20, such as `port_evacuation` (a fleet slipping out of a damaged port), `disputing_nations` and `casualty_proposal` (disputed casualties), `truce_breaker` (a battle that ends the Chinese Truce) | would have been `battle_data:other` | their own questions |
| Words in battle notes | the battle's next step (`defender_fire`, `round_end`, ...), its situation (`port_attack`, `movement_map`, ...), its result (`attacker_wins`, ...), a bombing target (`rail`, `city`, ...), the side or unit classes a hit may take, nations and players | dropped, not even counted | `battle_data_word:<note>:<word>` |
| Values in moves | `local` (fighters intercepting from the zone itself), `improved_construction_discount` and `improved_construction_combine` | `value:<label>:other`; the two prices made two different moves identical | their own questions |
| Repairs on the board | a city (the CCP repairing Beiping, 80 times in 240 games) and a construction project (none seen) | skipped | `repair:<nation>:city:*` and `repair:<nation>:construction:*` at its zone |
| Marks | `surprise_attack_linked_land`: the land zone Japan's surprise attack links to a sea battle | `other` | its own question, also at the zone |

Words in battle notes were the largest silent loss. In 48 random games the
encoder dropped words in 20 notes, among them `rolling_phase` (which side fires),
`context` (a port attack, a screening battle, ...), `result` and `target_kind`
(whether a bombing hits a facility or a railroad). The unknown-name report could
not show them, because the encoder never tried to translate them.

How a battle note is now read:

- a name is tried as a unit, zone, facility, construction project or railroad;
- a name ending in a number that is none of these belongs to something no
  longer in the game, such as a unit lost earlier this turn or a ship's crew that
  fought in a port, and is skipped;
- any other name is a word. 33 notes hold words, and the words are 107: the 52
  battle stage names, 22 other listed words, 17 unit classes, 13 nations and 3
  players. A word in any other note, or an unlisted word, is counted in an
  "other" row and reported.

The move questions about a railroad's two zones, `rail_zone`, were renamed
`rail_endpoint`: the user found the old name confusing, and the engine calls
each side of a railroad's border an endpoint.

## How the lists stay complete

- **The engine's source.** Five tests read the rule code and fail on a name
  without a question:
  - battle notes written or read through the battle code's note helpers;
  - marks;
  - words written into battle notes and move details;
  - battle stages;
  - prices.
- **Whole games.** The encoding test now plays two whole eleven-round random
  games, about 4 seconds each, instead of one three-round game, and fails on any
  unlisted name.
- **Many games.** `tools/check_zone_names.py` plays hundreds of random games and
  reports any unlisted name with the seeds that met it.

A name written in some other way and met in no random game can still reach an
"other" question. It is counted and reported, never dropped.

## Size and cost

The layout changed from `campaign-zone-v1-40973ed0dcbeb890` to
`campaign-zone-v1-a44069d0dfe2c7c0`:

| Part | Before | After |
| --- | ---: | ---: |
| Board, per zone | 35,439 | 42,520 |
| Position | 6,621 | 6,634 |
| Each move | 12,381 | 12,667 |
| Network parameters, 64×2 | 3.62 M | 4.09 M |
| Network parameters, 256×8 | 18.35 M | 20.24 M |

Most new board questions come from two sources:
- each new battle note brings the same 91 questions as every other note (3,276 in
  all);
- the words bring 3,672.

None are removed as impossible: which words a note can hold is not provable from
the rules. A new question starts at zero and adds nothing until it is answered.
Only non-zero answers are stored, so encoding does not slow down with more
questions: 0.169 and 0.173 ms per decision in two runs, against 0.164 ms. The
other engine calls were 2 to 5% slower in the same runs too. The networks are
13% (64×2) and 10% (256×8) larger; how that changes training speed was not
measured.

## Checks

- Random games, encoding every decision:

  | Seeds | Decisions | Games finished | Unlisted names |
  | --- | ---: | ---: | --- |
  | 7000 to 7239 | 373,049 | 240 of 240 | none |
  | 9000 to 9239 | 372,113 | 240 of 240 | none |

  Each run takes about two minutes on 8 workers.
- Tests:
  - two new C++ tests: battle notes keep their words; repairs and rare values have
    questions;
  - the five source checks and the whole-game test above;
  - all 26 C++ suites pass.

## Not changed

Some details are summarized rather than named:

- a mark's argument, unless it is a place or a nation: which railroad or facility
  was damaged this turn, for example, is counted for the whole position;
- the numbers and true values in a battle note are added into one answer;
- the field names inside a note, and things no longer in the game.
