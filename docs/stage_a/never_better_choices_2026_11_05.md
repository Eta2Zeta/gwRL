# Choices that are never better — 5 November 2026

The user proposed that, for training, every unit should be off its transport
before the Place Units Phase: unloaded is never worse than aboard, and the unit
can be loaded again next turn at no cost. They then asked for other choices
that are easily seen never to be better than another one. This record checks
the proposal against the rules and measures the candidates found. The
[evidence file](never_better_choices_2026_11_05.json) holds the exact values.

A choice can be left out, or played automatically, only if in every position
some other choice on the same menu does at least as well. Usually is not
enough: a choice that helps in one rare position makes a different game when it
is removed.

## Units off their transports

Unloading is not never worse, but for a nation's own unit on its own air
transport the rules point the same way:

- **On a ship at sea** nothing can be unloaded: cargo leaves only into an
  adjacent land zone (RB 11.4.1).
- **On a ship going in port** unloading is the player's decision (RB 11.5), and
  either way can be better. Cargo kept aboard is out of a land battle and of
  carpet bombing in that zone, but it sinks with its transport in a port attack.
  Cargo unloaded defends the zone and cannot move for the rest of the Calendar
  Turn.
- **An ally's unit** loads on its own turn and unloads on its next (RB 11.3.1 and
  11.4.1), so it must stay aboard.
- **A nation's own unit on its own air transport.** Staying aboard can be
  better: carpet bombing attacks only land units (RB 10.6.5), and the engine
  leaves cargo out of land battles. But RB 11.3.1 describes the transport
  picking the cargo up before or during its noncombat move and unloading it in
  a Friendly-possessed land zone, and never says it may stay aboard. Unloading
  it when Noncombat Movement ends follows that description. It reached a Place
  Units Phase in 2 of 241 random games
  ([record](zone_name_check_early_end_2026_11_05.md#upgrades-on-units-aboard-a-transport))
  and in none of the 48 below.

So unloading cannot replace the upgrade rule: units at sea, and an ally's units,
are still aboard when upgrades are placed.

## Candidates

Measured in 48 random eleven-round games (seeds 7000 to 7047) with the policy of
`tools/check_zone_names.py`: 63,110 decisions offering 2,007,702 options.

| Choice | Why it is never better | In random games |
| --- | --- | ---: |
| The same move for another of several identical units | units with the same type, owner, zone, damage, movement, origin, route, carrier, cargo, commitments and flags are interchangeable: the positions differ only in the units' names | 204,340 options (10.2%) |
| A strategic rail or river move to a zone the same unit reaches by an ordinary move | both end in the same zone; the rail move spends rail capacity and ends the unit's movement, the ordinary move spends no capacity and leaves at least as much movement | 61,129 options (3.0%) |
| Ending the Place Units Phase without the recruitment roll | the roll is free, a failure changes nothing, and every success gives units, a ship advance or a facility repair; RB 12.7 says controlled minor powers make it | offered in 885 menus beside ending the phase; skipped 472 times |
| The printed price once Improved Construction is developed | for naval units and facilities the discount buys the same thing on the same schedule, one IPP less per stage; RB 8.2.1 offers the discount or the condensed stages, not the printed price | 1,930 options in 12 menus, all in 1 of 240 games (seeds 7000 to 7239) |

Leaving out the first two removes 12.2% of options; 244 menus would be left
with a single option. The third and fourth remove few options but choices the
learner would otherwise have to learn to avoid.

## Choices that look never better but are not

- **Rolling for influence at no cost.** For Japan a roll of 12 always hands the
  warlord to the KMT, so not rolling can be better. Only Japan and a minor CCP
  roll, and a larger stake buys a better chance, a trade of IPP for odds.
- **Declining a destroyer's pairing with a patrol plane** against submarines
  (`naval_decline_pair`). Whether pairing ever costs anything was not settled.
- **Not pairing artillery.** Not offered: every unpaired artillery is paired.
- **Giving up an aircraft that could land.** Not offered: the engine offers it
  only when some aircraft must be lost, or this one has nowhere to land.

## Not counted

The same end of a phase reached by moves in another order (two purchases, two
units' moves) is the largest family of choices that make no difference. Leaving
those out needs a different way of ordering a turn, such as the quantity choice
and fixed placement order proposed on
[31 October](decision_review_2026_10_31.md#interface-changes-that-keep-every-legal-outcome),
not a filter on one menu.

## Method and limits

- The random policy is a stand-in for an untrained learner. Shares under
  trained play will differ; research, and so Improved Construction, is rare
  under it.
- Identical units are found as in `tools/decision_census.py symmetry`: an
  option's unit names are replaced by the units' full states, and options that
  then coincide are counted once. The 31 October review measured 12.0% in
  three-round random games and 15.3% in an eleven-round scripted game.
- Nothing here changes the engine. Each removal would need a check that every
  removed choice is matched on test positions by a kept one with the same or a
  better result, and the rule-based ones the user's decision.
