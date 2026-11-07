# Upgrades wait while their unit is at sea — 6 November 2026

RB 12.3 requires a Supply Path to the land zone that the unit receiving an
upgrade is in. A unit aboard a ship at sea is in no land zone, yet the engine
offered it upgrades: after
[RCL-021](../../game_content/rules/clarifications.md#rcl-021-upgrading-a-unit-aboard-a-transport)
barred upgrades into cargo a transport may not carry, random games still had
139 such offers in 85 of 241 games, 43 of them taken
([record](never_better_choices_2026_11_05.md#checks)). Asked on 6 November
whether to bar them, as RB 12.3's wording implies, the user answered "Yes, bar
them". The ruling is part of RCL-021. The
[evidence file](upgrades_at_sea_2026_11_06.json) holds the exact values.

## What changed

- **The rule.** A unit aboard a ship at sea is not offered an upgrade. The
  upgrade stays on the build queue until it can reach a suitable unit, as
  RB 12.3 provides when it cannot reach one, and the Place Units Phase ends as
  before when no upgrade can be placed.
- **Ships in port.** A ship in port is located in the land zone of its Naval
  Facility (RB 11.5), and the engine gives the ship and its cargo that zone.
  Cargo aboard a ship in port may still be upgraded, within RCL-021's limits on
  what the transport carries.
- **Which units.** The build charts have two unit upgrades: infantry to
  motorized infantry and militia to infantry. No ship is upgraded, so the rule
  touches only land units aboard ships.
- **The code.** In `src/economy.cpp` one function, `upgradeUnitLegal`, now
  decides whether a bought upgrade may be placed on a unit, and adds that the
  unit stands in a land zone, checked before the Supply Path. Both places that
  offer a unit upgrade use it; before, each listed the same conditions. A
  militia upgrade received by lend-lease was already placed only on a militia
  in a land zone of the recipient's Home Country (RB 12.4), so that path is
  unchanged.
- **The records.** RCL-021 in the rule register, with its new hash in the
  politics profile; the economy profile's upgrades rule
  (`unit_in_land_zone_required`, source `user_upgrade_at_sea_2026_11_06`); and
  the rules reader's note, now also shown at RB 11.5.

## Checks

- **Test.** In `upgradesWaitAtSea` (`tests/economy_tests.cpp`) a naval
  transport off Tokyo carries an infantry and a militia, and Japan has bought an
  upgrade for each. At sea neither is offered, although a Supply Path reaches
  that sea zone. Once the ship is in port at Tokyo, both are.
- **Mutations.** Without the land-zone condition the new test fails. Barring
  every carried unit instead fails RCL-021's test, which lets a militia aboard
  an air transport become infantry.
- **Suites.** All 26 C++ suites and the Python suite (455 tests, 3 skipped)
  pass.
- **Random games.** Menus changed, so games differ from earlier runs with the
  same seeds. 800 random eleven-round games (seeds 9000 to 9799) found no dead
  end, engine error or move that changes nothing. The name check met no
  unlisted name and no question removed as impossible: 314,977 decisions in
  seeds 7000 to 7239 and 312,365 in seeds 9000 to 9239, with 8,848 and 8,790
  phases ended early.
- **Not measured: speed.** The change adds one lookup per candidate unit. No
  timing was taken.

Upgrades offered on carried units, in the 241 random games of the earlier count
(seeds 7000 to 7239 and 9239), counted once per unit and round:

| Where the carried unit is | Run | Offered | Taken | Games |
| --- | --- | ---: | ---: | ---: |
| Aboard a ship at sea | 5 November, after RCL-021 | 139 | 43 | 85 |
| Aboard a ship at sea | 6 November | 0 | 0 | 0 |
| Aboard a ship in port | 5 November, after RCL-021 | 101 | 30 | 59 |
| Aboard a ship in port | 6 November | 92 | 33 | 59 |
| Aboard an air transport | both | 0 | 0 | 0 |

## Method and limits

- The random policy is that of `tools/check_zone_names.py`: uniform random
  moves, with the phase ended early at 2, 5 or 10% of decisions depending on the
  seed. Shares under trained play will differ.
- A nation's own unit may stay aboard its own air transport after the
  Noncombat Movement Phase, and the engine allows it. RB 11.3.1 lets the
  transport pick its cargo up before or during its noncombat move and keep
  moving after it unloads in a Friendly-possessed land zone, but does not
  require it to unload. This record first called it an open question, as the
  design document and the
  [record of 5 November](zone_name_check_early_end_2026_11_05.md#upgrades-on-units-aboard-a-transport)
  did; the user pointed out the same day that the rule says no such thing.
