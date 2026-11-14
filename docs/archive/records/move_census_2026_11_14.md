# Where each kind of move is offered — 14 November 2026

The [engine pages](../../engine/README.md) say in which phase each kind of move
is made and who chooses it. Those statements were read off the code and checked
against random play. This record gives the random play. The
[data file](move_census_2026_11_14.json) holds every count.

## Setup

Commit `c8bb1be`. `tools/move_census.py` played 240 eleven-round games, seeds
9000 to 9239, through the same environment training uses (`make_env`), on 8
worker processes. Every move was drawn uniformly at random, except that where
the phase could end it was ended with probability 2%, 5% or 10%, depending on
the seed, so that some phases did little and others much.

```sh
./.venv/bin/python tools/move_census.py docs/archive/records/move_census_2026_11_14.json \
  --games 240 --workers 8 --first-seed 9000
```

## Results

| | |
| --- | ---: |
| Games finished | 240 of 240 |
| Decisions | 312,365 |
| Decisions per game: least, median, most | 972, 1,286, 1,829 |
| Longest list of moves at one decision | 620 |
| Kinds of move met | 93 of the engine's 141, and the adapter's `pass_interrupt` |

**Phases.** Every kind met was offered in the phases the engine pages name. The
data file lists, for each kind, the phases, the nations, the decision it
answered if any, its details and one example with its seed.

**Kinds not met.** 48 kinds never came up:

| Family | Not met |
| --- | --- |
| Truce | all five: `truce_offer`, `truce_decline_offer`, `truce_accept`, `truce_reject`, `truce_break` |
| Politics, recruitment | `politics_relocate_neutral`, `recruitment_advance_ship`, `recruitment_repair_facility` |
| Movement | `movement_factory_rail`, `movement_grant_rail` |
| Economy | `economy_lease_repair` |
| Land combat | `land_casualty_accept`, `land_casualty_dispute`, `land_declare_attrition`, `land_pair_blitz`, `land_finish_blitz_pairing`, `land_select_surprise_zone` |
| Air | `air_assault`, `air_blitz`, `air_rocket_attack`, `air_artillery_city_bomb`, `air_resume_bombing`, `air_choose_technology_loss`, `air_allied_load`, `air_allied_unload` |
| Naval | 23 kinds: the four `naval_entry_` kinds, `naval_cancel_move`, `naval_force_remove`, `naval_carrier_land`, `naval_finish_battle`, the casualty and shore `_accept` and `_dispute` kinds, `naval_pair_destroyer`, `naval_decline_pair`, the three port evacuation kinds, `naval_raider_slip`, `naval_raider_stay`, `naval_screen_remove`, `naval_screen_continue_route`, `naval_screen_stop_route`, `naval_select_surprise_zone` |

**Dice.** 41,720 chance events: 34,633 for land combat, 2,846 for research,
2,613 for recruitment, 548 for shore fire, 358 for warlords picking a side, 236
for influence, 231 for ships in captured ports, 157 for naval combat, 62 for
bombing damage (the only six-sided rolls) and 36 for anti-aircraft fire.

## What this does and does not show

- **Measured:** the counts above, for uniformly random play at this commit.
- **Not shown:** that a kind not met cannot occur. Random play rarely builds
  the positions those kinds need: the Chinese Truce, for one, was never
  offered. Their evidence is the engine's test suites.
- **Not shown:** what good play looks like. Random games differ from the
  agents' games in how often each move comes up.
