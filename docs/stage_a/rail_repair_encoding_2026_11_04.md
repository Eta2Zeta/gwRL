# Railroads named by their border, and railroad repairs encoded — 4 November 2026

A random check on 3 November found 31 names missing from the network input's
lists ([design page](../design/network_input.md#7-names-the-encoder-doesnt-know)).
Twelve were railroad names and one was the label `damage`, all from railroad
repair moves: the input lost which railroad a repair mends and filed its amount
as an unknown number. On the user's ruling (RCL-019), a border holds at most one
railroad. A railroad is therefore named by its two zones, and the input now
describes it by them. The [evidence file](rail_repair_encoding_2026_11_04.json)
holds the exact values.

## The rule

The user confirmed on 3 November that each side of a railroad's border holds its
own damage and that the nation possessing a side repairs it at 1 IPP per point,
and on 4 November that a difficult border takes up to 2 damage on each side.
On 4 November the user also adopted one railroad per border as an equivalence ruling:
a second railroad would give nothing that repairing the first does not. Bombing
damages every railroad on a border together (RB 10.6.2), and repairing both
sides at their maximum costs the building price (2 IPP in normal terrain, 4 in
difficult terrain). Recorded as
[RCL-019](../../game_content/rules/clarifications.md#rcl-019-one-railroad-per-border-damaged-and-repaired-by-side),
in the economy and air rules profiles and in the rules reader.

## What changed in the engine

- **Building was already refused.** A railroad purchase is not offered on a
  border with a railroad, damaged or not, or with a railroad under construction,
  and placement checks again. A new test covers each case.
- **Names.** Railroads on the starting map were already named by their border,
  such as `rail_land_china_hopeh__land_china_shensi`. Railroads built during play
  were named by a counter, such as `economy_rail_8`. They now get their border's
  name too, with the two zones stored in alphabetical order.
- **State checks.** A saved state is refused if a railroad is not named by its
  border, which also rules out two railroads on one border, or if a railroad
  repair does not name the side it mends.
- **One side effect on random games.** A railroad built during play no longer
  uses a number from the counter that also names units and facilities bought
  later. So random games diverge from earlier runs with the same seed after a
  railroad is built: the legal choices are the same, but the menu lists them in
  a different order.

## What changed in the input

A railroad repair move, such as Japan's in random-play seed 7004:

```text
economy_repair   target   = rail_land_manchuria_northern__land_manchuria_western
                 endpoint = land_manchuria_northern
                 damage   = 1
```

| Before | After |
| --- | --- |
| `value:target:other`: some unknown name | `rail_endpoint:2_target:land_manchuria_northern`, `rail_endpoint:2_target:land_manchuria_western`: the railroad's two zones, its endpoints; `rail_damage:2_target:land_manchuria_northern = 1`: the damage on each side |
| `zone:3_other:land_manchuria_northern`: the side, with no role | `zone:2_target:land_manchuria_northern`: the side, as what the move acts on |
| `parameter:other`, `number:other = 1` | `parameter:damage`, `number:damage = 1` |

- `endpoint` joined the role table as a `2_target` label, and `damage` joined
  the list of known labels.
- On the board, a repair under way also says which border it is on:
  `rail_repair_toward:<zone across>`, holding the damage still to be repaired,
  on the repaired side's row.
- Railroads join land zones only, so the new railroad questions have no
  sea-zone versions. Each new family keeps a `~impossible` question that would
  count any such case.

The layout changed from `campaign-zone-v1-edcfe0583896a5da` to
`campaign-zone-v1-40973ed0dcbeb890`:

| Part | Before | After |
| --- | ---: | ---: |
| Board, per zone | 35,407 | 35,439 |
| Position | 6,621 | 6,621 |
| Each move | 12,114 | 12,381 |
| Network parameters, 64×2 | 3.60 M | 3.62 M |
| Network parameters, 256×8 | 18.27 M | 18.35 M |

Networks and checkpoints of the old layout cannot be used with the new one; a
new run starts fresh.

## Checks

- **Unit tests.** Two railroads that meet at one zone now give repair moves with
  different answers and different "what it acts on" groups. A repair acts on the
  side being repaired. Nothing in a repair is filed as unknown. All 26 C++ suites
  pass.
- **Random games.** The same 240 random eleven-round games as on 3 November
  (seeds 7000 to 7239) were encoded again: 373,049 decisions, all games
  finished. No railroad name, no `damage` label and no `~impossible` question
  appeared. 20 missing names remain, against 31: the 16 battle notes, the city
  repair target and `local`, as before, and two that the 3 November run never
  met. These are the price methods `improved_construction_discount` (1,195 times)
  and `improved_construction_combine` (452 times). They occur only once a nation
  has completed Improved Construction, which happened in one game, seed 7078.
  They have been in the engine since its first commit; this run reached them
  because its games diverged after railroads were built.
- **Encoding time.** On the three random games used on 3 November (4,786
  decisions), encoding took 0.164 ms per decision on average, against 0.166 ms
  then: no measurable change.

## Not changed

- The other 20 missing names, fixed later the same day
  ([record](zone_names_2026_11_04.md)). That change also renamed the move
  questions `rail_zone`, as this change first named them, to `rail_endpoint`.
- Marks that say when a railroad or facility was damaged, repaired or built this
  turn (`logistics_damaged_turn:<name>`, `logistics_start_damaged:<name>`,
  `logistics_rail_created_turn:<name>`) are still counted for the whole position,
  not at the railroad's zones. They matter only for supply and lend-lease routes
  that need a railroad undamaged since the start of the turn.
- The older railroad questions `rail_to` and `rail_damage_toward` keep their
  sea-zone versions.
