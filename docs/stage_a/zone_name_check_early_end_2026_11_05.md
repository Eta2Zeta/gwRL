# The name check's early phase ends — 5 November 2026

`tools/check_zone_names.py` and the encoding test
`test_every_name_in_random_play_has_a_column` play random games to find names
the network input does not list. Both are meant to end the phase now and then
instead of making a random move, so that some phases do little and others much.
Where the phase can end, the tool ends it at 2, 5 or 10% of decisions depending
on the seed, the test at 5%. Since they were written on 4 November (commit
`1396518`), that never happened. The user asked to fix both. The more varied
games then found a cargo the rules forbid, made by upgrading a unit aboard an
air transport. Following that up showed the engine also upgrades units aboard
ships at sea, which RB 12.3 rules out. The
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
unit chart in 13.1.5), and motorized infantry is vehicle-class. The engine made
the cargo itself, in round 9:

1. In the Production Phase the KMT bought an upgrade of infantry to motorized
   infantry (RB 8.4).
2. In Noncombat Movement a KMT air transport in Sikang loaded an infantry and
   did not fly. The infantry was still aboard when the phase ended.
3. In the Place Units Phase the KMT placed the upgrade on that infantry, which
   became motorized infantry aboard the air transport.

## Upgrades on units aboard a transport

No rule speaks of upgrading a unit aboard a transport. The search covered the
rulebook's upgrade and placement rules (8.4, 12.1 and 12.3), its transport rules
(9.4.3, 11.3.1, 11.4.1 and 11.5), the unit charts, the thirteen national sheets,
the project's clarifications and answered questions, the economy rules profile,
the rules reader's notes and the audited Discord answers. One sentence bears on
it: RB 12.3 requires a Supply Path to the land zone that the unit receiving the
upgrade is in. An earlier version of this record said only that the rules are
silent, which missed this.

The engine offers an upgrade on any of the nation's units of the right type
that is in supply and was not placed this turn, carried or not, and its Supply
Path may end in a sea zone, as naval supply does. A ship in port, and its cargo,
stand in the port's land zone. In 241 random games with the policy above (seeds
7000 to 7239 and 9239), 132 games offered an upgrade on a carried unit, counted
once per unit and round:

| Where the carried unit is | Its zone | What RB 12.3 allows | Offered | Taken | Games |
| --- | --- | --- | ---: | ---: | ---: |
| Aboard a ship at sea | a sea zone | no upgrade: the unit is in no land zone | 151 | 58 | 89 |
| Aboard a ship in port | the port's land zone | an upgrade | 123 | 50 | 78 |
| Aboard a landed air transport | its land zone | an upgrade, but the motorized infantry it makes is cargo an air transport may not carry | 2 | 1 | 2 |

Every offer was an upgrade of infantry to motorized infantry, all by Japan
except the two KMT ones aboard air transports. So the engine breaks RB 12.3 at
sea, and the air transport case is open.

Upgrades are placed in the owner's Place Units Phase, after Noncombat Movement.
The rules let a unit still be aboard then in these cases:

- **On a ship, at sea or in port.** A naval transport may go in port with its
  cargo aboard, since unloading is decided as it berths (RB 11.5). After a
  Strategic Naval Movement the units may remain on board (the example in
  RB 11.4.2). An ally's unit rides from its own turn to its next (RB 11.4.1).
- **An ally's unit on an air transport.** RB 11.3.1 has it load on its own turn
  and unload on its next, so it is aboard through its own Place Units Phase. In
  this scenario the CCP and Mongolia are both in the Comintern, and both may
  own air transports and infantry.

A nation's own unit on its own air transport is another matter. RB 11.3.1 has
the transport pick it up before or during the noncombat move and unload it in a
Friendly-possessed land zone, and never says it may stay aboard afterwards. The
engine lets it stay: when an air transport lands only militia step off, under
the user's militia ruling, and nothing unloads the rest when the phase ends. In
seed 9239 a KMT air transport loaded an infantry and never took off. In seed
7120 one loaded an infantry in round 8, kept it aboard for a whole round, flew
it to Sikang in round 9 and landed without unloading it. Both reached a Place
Units Phase with the infantry aboard. Whether a nation's own unit may stay
aboard its air transport after the noncombat move is a second open question.
Requiring a nation's own cargo to leave its air transports by the end of
Noncombat Movement would remove those two cases, but not an ally's unit aboard.

The user ruled the same day that cargo may stay aboard, and that an upgrade may
not leave a transport carrying a unit it may not carry
([RCL-021](../../game_content/rules/clarifications.md#rcl-021-upgrading-a-unit-aboard-a-transport);
[record](never_better_choices_2026_11_05.md#the-users-decision)). Upgrades of
units aboard ships at sea were still offered until the user barred them on
6 November ([record](upgrades_at_sea_2026_11_06.md)).

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
