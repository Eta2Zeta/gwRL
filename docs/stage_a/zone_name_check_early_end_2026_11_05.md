# The name check's early phase ends — 5 November 2026

`tools/check_zone_names.py` and the encoding test
`test_every_name_in_random_play_has_a_column` play random games to find names
the network input does not list. Both are meant to end the phase now and then
instead of making a random move, so that some phases do little and others much.
Where the phase can end, the tool ends it at 2, 5 or 10% of decisions depending
on the seed, the test at 5%. Since they were written on 4 November (commit
`1396518`), that never happened. The user asked to fix both. The more varied
games then found a cargo the rules forbid. The
[evidence file](zone_name_check_early_end_2026_11_05.json) holds the exact
values.

## What was wrong

- Both looked for the end-phase move by its `kind`. In the Python wrapper they
  use (`make_env`), an action's `kind` is the scheduler's label: `play`,
  `interrupt` or `pass_interrupt`. The engine's own name for the move ends the
  action's id, as in `…:play:end_phase`.
- So no move matched, and every move was uniformly random. The games still all
  finished and met no unlisted name, so the results of 4 November hold for the
  games played. Those games were only less varied than described.

## What changed

- **The lookup.** Both now find the end-phase move by the end of its id, as the
  fuzzer (`tools/fuzz_campaign_dead_ends.py`) already did. This needs no Python
  copy of the move. In three random games (seeds 7000 to 7002, 3,983 menus), the
  id and the engine's move name found the same moves: 2,305 menus offered one,
  none offered two.
- **A count.** Both count the phases they end early. The tool reports the count
  as `early_ends`, and the test fails if no phase was ended early. With the old
  lookup put back, the test fails with "no phase was ended early".

Tests that call the engine directly (`gwrl_cpp.CampaignEnv`, or a wrapper's
`raw` engine) find the move by `kind` correctly, since there `kind` is the
engine's move name. The fuzzer and `tools/check_move_generation.py` already used
the id.

## Results

| Seeds | Games finished | Decisions | Phases ended early | Unlisted names | Questions removed as impossible but reached | Time on 8 workers |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| 7000 to 7239 | 240 of 240 | 313,496 | 8,731 | none | none | 103 s |
| 9000 to 9239 | 240 of 240 | 314,594 | 8,757 | none | one, in seed 9239 | 107 s |

With the old lookup and the same engine, seeds 7000 to 7239 made 372,857
decisions (4 November, after commit `d64117d`). Ending phases early cuts that by
16%. The encoding test's two games took 7.0 seconds, against 8.7 with the old
lookup, measured once each.

## What the new games found

In 178 encoded positions of seed 9239, a KMT air transport carries motorized
infantry (`carried:allies:air_transport:motorized_infantry`). The input had
removed that question as impossible, rightly: in Noncombat Movement an air
transport carries one infantry-class unit and a Heavy Air Transport one
infantry-class, artillery or anti-aircraft artillery unit (RB 11.3.1 and the
unit chart in 13.1.5), and motorized infantry is vehicle-class. The engine made the cargo itself, in round 9:

1. In the Production Phase the KMT bought an upgrade of infantry to motorized
   infantry (RB 8.4).
2. In Noncombat Movement a KMT air transport in Sikang loaded an infantry and
   did not fly. The infantry was still aboard when the phase ended.
3. In the Place Units Phase the KMT placed the upgrade on that infantry, which
   became motorized infantry aboard the air transport.

The engine offers an upgrade on any of the nation's units of the right type
that a Supply Path reaches and that was not placed this turn (RB 12.3), carried
or not. The rules do not say whether a unit aboard a transport may be upgraded.
Making a nation's own cargo leave its air transports when Noncombat Movement
ends would not settle it: RB 11.3.1 lets an ally's unit ride an air transport
through its own Place Units Phase, loading on its own turn and unloading on
its next. How to treat such an upgrade awaits the user's ruling. The engine is
unchanged.

## Earlier records

The random checks recorded on 4 November played without early ends: those in
the records of [railroad repairs](rail_repair_encoding_2026_11_04.md), whose
evidence file names the intended policy, [names](zone_names_2026_11_04.md),
[the patrol choice](patrol_choice_2026_11_04.md),
[a patrol plane's second chance](patrol_second_chance_2026_11_04.md) and
[the patrol fighter](patrol_fighter_screen_2026_11_04.md). The check of
3 November that found 31 missing names most likely did too. On the same seeds it
made 372,935 decisions, close to the 372,857 to 373,049 of 4 November and far
from the 313,496 with early ends. That is inferred from the counts alone.
