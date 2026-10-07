# M0 asset purchase-price and repair audit

Audit date: 12 September 2026. Specification only; no reward evaluator or unit
catalog has been implemented by this document.

**5 October 2026 accounting update:** the [M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md)
records the adopted setup-only values (Torpedo Boat Destroyer 5 IPP; Coastal
Submarine 4), full catalog valuation for completed assets, and cumulative
already-paid value for unfinished construction. The source inventory below
predates the exclusion of FEC/USSR. City and cross-owner rail valuation remain
proposed accounting details.

## Result: two unit types need the user's values

These are **valuation-only** choices. Giving them a wealth value must not make
them purchasable; the rules explicitly say they cannot be built.

| Type without a purchase price | Included official starting instances | Published entry | Decision needed |
| --- | --- | --- | --- |
| Torpedo Boat Destroyer | Japan: one in P15 and one in P16; **2 total** | RB p89, §13.1.6: price N/A, cannot be built | Wealth value in IPP per surviving ship |
| Coastal Submarine | Japan: one at Korea/P14 and one in P16; FEC: one in P41; **3 total** | RB p91, §13.1.6: price N/A, cannot be built | Wealth value in IPP per surviving submarine |

The generic catalog also lists **Coastal Defense Ships** at N/A (RB p89), but the
included Japan, Chinese, Mongolian and FEC starting inventories do not contain one,
and none can be purchased or supplied from outside this closed theatre. It is not
a valuation decision needed for this scenario. Do not silently substitute the
price of a Destroyer, Battleship or regular Submarine for a different unit type.

Ports, dockyards, shipyards, factories, airbases and railroads **do have prices**.
The repository's `airfield` label is a data-name reconciliation with the rulebook's
**Airbase**, not evidence of a separate unpriced facility. Confirm that identity
when normalizing definitions; do not value both names as separate assets.

## Sources and review method

- **RB**: [Global War 1936 v4.3 Rulebook](</Users/home/Desktop/gwRL/game_content/rules/Global War 1936 v4.3 Rulebook.pdf>), printed pages (which match PDF page numbers), particularly §§8.2-8.6, 12.2-12.3 and 13.
- **J**: [Japan v4.3 national reference sheet](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - Japan v4.3.pdf>), PDF pp5-8 build charts; p9 setup.
- **K**: [KMT v4.3 national reference sheet](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - KMT v4.3.pdf>), PDF pp3-7 build charts/setup.
- **C**: [CCP v4.3 national reference sheet](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - CCP v4.3.pdf>), PDF pp3-7 build charts/setup.
- **F**: [FEC v4.3 national reference sheet](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - FEC v4.3.pdf>), PDF p6 setup.

Text extraction was cross-checked against rendered purchase tables; setup counts
are cross-checked with the companion M0 setup audits. A numeric price is not a
claim that a nation can buy the item today: national build charts, Major/Minor
status, calendar, technology, placement and capacity remain independent gates.

## Priced land, air and rocket units

These are undiscounted catalog values, not a decision to use historical cost or
current discounted replacement cost in the eventual reward evaluator. J/K/C
Major-Power charts agree with the generic prices below. KMT and CCP retain their
separate, much narrower Minor-Power build charts until evolution. Setup Mountain
Infantry still has its catalog price even where a Minor Power cannot buy it.

| Unit type | Purchase price (IPP) | Source | Availability notes relevant to this theatre |
| --- | ---: | --- | --- |
| Militia | 2 | RB p83; J p5; K/C p3-4 | Minor-Power militia movement differs; no factory needed |
| Infantry | 3 | RB p83; J p5; K/C p3-4 | Includes official setup, recruited and free objective Infantry |
| Airborne Infantry | 3 | RB p83; J p5; K/C p4 | Purchase cap 2 per Player Turn |
| Elite Airborne Infantry | 3 | RB pp47,83; J p5; K/C p4 | Airborne Doctrine; cap 2; existing airborne converts automatically |
| Marines | 4 | RB p84; J p5; K/C p4 | Cap 2; no separate priced Japanese SNLF type in v4.3 chart |
| Mountain Infantry | 4 | RB p84; J p5; K/C p4 | Cap 2; official CCP/warlord setup instances count |
| Colonial Infantry | 4 | RB p84; FEC build chart | FEC; only eligible original outside-Home-Country IPP zones, cap 2 |
| Cavalry | 3 | RB p85; J p5; K/C p3-4 | Major Powers cannot purchase after July 1939; setup cavalry remains |
| Motorized Infantry | 4 | RB p85; J p5; K/C p4 | Also obtainable by eligible Infantry upgrade |
| Mechanized Infantry | 4 | RB p85; J p5; K/C p4 | January 1940 gate for these nations |
| Advanced Mechanized Infantry | 4 | RB pp45,85; J p5; K/C p4 | Technology gate |
| Tank Destroyer | 4 | RB p85; J p5; K/C p4 | January 1940; cap 2 |
| Light Armor | 4 | RB p85; J p5; K/C p4 | Major-Power chart gate |
| Medium Armor | 6 | RB p85; J p5; K/C p4 | January 1940 |
| Heavy Armor | 7 | RB pp48,85; J p5; K/C p4 | Technology gate |
| Artillery | 4 | RB p86; J p5; K p3,5; C p3-4 | Chinese minor special purchase prerequisites still apply |
| Self-propelled Artillery | 5 | RB p86; J p5; K p5; C p4 | Major-Power chart gate |
| Advanced Artillery | 4 | RB pp45-46,86; J p5; K p5; C p4 | Technology gate |
| Advanced Self-propelled Artillery | 5 | RB pp46,86; J p5; K p5; C p4 | Technology gate |
| Anti-aircraft Artillery | 4 | RB p87; J p6; K/C p3,5 | Separate from inherent facility AAA; Chinese minor gates apply |
| Fighter | 10 | RB p87; J p6; K/C p5 | Setup/carrier aircraft count separately from carrier |
| Jet Fighter | 11 | RB pp48,87; J p6; K/C p5 | Technology; cap 2 |
| Tactical Bomber | 10 | RB p87; J p6; K/C p5 | Normal national chart |
| Medium Bomber | 10 | RB p87; J p6; K/C p5 | Normal national chart |
| Strategic Bomber | 10 | RB p88; J p6; K/C p5 | January 1940; cap 2 |
| Heavy Strategic Bomber | 11 | RB pp49-50,88; J p6; K/C p5 | Technology; cap 2 |
| Seaplane | 7 | RB p88; J p6; K/C p5 | Normal national chart |
| Air Transport | 8 | RB p88; J p6; K/C p5 | Cargo is a separate asset, not included in transport cost |
| Heavy Air Transport | 9 | RB pp47,89; J p6; K/C p5 | Airborne Doctrine |
| Strategic Rocket | 3 | RB pp50,92; J p6; K/C p5 | Technology; cap 2; consumed after firing |

Gurkhas have a price of 4 IPP (RB p84), but none are retained in setup and their
Nepal prerequisite is outside the closed map. Foreign Legion, Panzergrenadier,
Tiger I, T-34, Katyusha and B-29 also have published prices; they are not
unpriced-unit questions. Their nation/Home-Country-specific access must not be
granted to Japan, KMT or CCP merely because the generic catalog includes them.
The adopted campaign excludes USSR as a participant. Mongolia's direct Comintern
control and use of the USSR turn position do not grant Soviet special units or
create a Soviet production pool.

## Priced naval units

RB §8.3 p50 explicitly defines slash-separated prices as staged payments: a Heavy
Cruiser at `5/5` has a complete price of 10, not 5. All these types are on J/K/C
Major-Power charts (J p7, K/C p6).

| Unit | Stage payments | Full catalog value | Source |
| --- | --- | ---: | --- |
| Destroyer | 7 | 7 | RB p89 |
| Light Cruiser | 9 | 9 | RB p89 |
| Heavy Cruiser | 5 / 5 | 10 | RB p89 |
| Battlecruiser | 7 / 7 | 14 | RB p90 |
| Battleship | 6 / 6 / 6 | 18 | RB p90 |
| Heavy Battleship | 7 / 7 / 7 | 21 | RB p90; Large Ship Construction |
| Light Carrier | 4 / 4 | 8 | RB p90 |
| Fleet Carrier | 5 / 5 / 5 | 15 | RB p90 |
| Heavy Fleet Carrier | 6 / 6 / 6 | 18 | RB p91; Large Ship Construction |
| Submarine | 6 | 6 | RB p91 |
| Advanced Submarine | 7 | 7 | RB p91; technology |
| Naval Transport | 7 | 7 | RB p92 |
| Attack Naval Transport | 7 | 7 | RB p92; Amphibious Doctrine |

## Priced facilities and infrastructure

All listed facilities also appear in the J/K/C Major-Power build charts. A facility
printed on the map counts as a setup asset at its chosen catalog valuation even
though no cash was paid during the episode. Count one physical facility once,
including facilities serving two sea zones. Multiple genuine shipyards on one
island remain multiple assets.

| Facility | Stage payments | Full catalog value | Repair cost / damage limit | Source |
| --- | --- | ---: | --- | --- |
| Minor Factory | 8 | 8 | 1 per point / 5 | RB p93 |
| Medium Factory | 7 / 7 | 14 | 1 per point / 10 | RB p93 |
| Major Factory | 6 / 6 / 6 | 18 | 1 per point / 20 | RB p93 |
| Airbase (map `airfield`) | 3 / 3 | 6 | 1 per point / 3 | RB pp93-94 |
| Seaplane Base | 3 | 3 | 1 per point / 3 | RB pp93-94 |
| Submarine Base | 3 | 3 | 1 per point / 3 | RB pp93-94 |
| Minor Port | 3 | 3 | 1 per point / 1 | RB pp94-95 |
| Major Port | 3 / 3 | 6 | 1 per point / 3 | RB pp94-95 |
| Minor Dockyard | 2 / 2 | 4 | 1 per point / 2 | RB p95 |
| Major Dockyard | 4 / 4 | 8 | 1 per point / 4 | RB p95 |
| Minor Shipyard | 3 / 3 | 6 | 1 per point / 3 | RB p96 |
| Major Shipyard | 5 / 5 | 10 | 1 per point / 5 | RB p96 |
| Fortification | 5 / 5 | 10 | Cannot be strategically bombed; removed on capture | RB pp96-97 |
| Coastal Artillery | 6 | 6 | Cannot be strategically bombed; removed on capture | RB pp97-98 |
| Railroad crossing a normal-terrain border | 2 | 2 | 1 per point / 1 | RB pp98-99 |
| Railroad crossing desert/jungle/marsh/mountain/tundra | 4 | 4 | 1 per point / 2 | RB pp98-99 |

A river crossing is not by itself an additional railroad price tier. Determine
rail terrain by the printed direct border route (§13.2.8), not blindly by one
destination's intrinsic terrain. Railroad damage is one state per physical
border, and all artwork tracks on that border are affected together (§10.6.2
p67). For wealth, deduplicate that border and decide attribution when opposite
ends have different owners; do not sum two directed-neighbor copies.

## Repair and accounting consequences that need to remain explicit

1. **Capital-ship repairs cost zero IPP.** RB §8.6 p51 and §12.2 p79 consume
   dockyard/shipyard repair slots instead. Under the user's literal
   `purchase_price - remaining_repair_price`, a damaged Battleship or Carrier has
   the same wealth value as an undamaged one, despite reduced combat/movement.
   A separate damage discount would be a new user choice, not a rules correction.
2. **Negative facility values are possible under the literal formula.** A Major
   Factory costs 18 but may sustain 20 damage; its resulting value is -2 before
   the 0.1 weight. No zero floor has been authorized. Destroyed/removed assets
   are absent, and are not negative-valued surviving facilities.
3. **Cities are terrain/economy, not purchasable facilities.** They have no build
   price. Recommended scope is to account for their current IPP rate and all
   distinct facilities within them, with no extra standalone city-asset value.
   City bombing/repair (RB pp66-67,51) remains real even without a city asset price.
4. **Discounts versus valuation are distinct.** Improved Construction reduces
   facility/naval payments by 1 per stage, or accelerates early stages; Kido Butai
   discounts Capital Ships by another 1 per stage (RB pp21,46). The published
   undiscounted price exists, so these are not missing prices. The adopted policy
   uses full catalog price for completed assets, even when acquisition was
   discounted. A free recruitment or evolution award therefore retains its
   catalog value. Kido Butai is excluded from this campaign.
5. **Upgrades are not necessarily cost-neutral under catalog valuation.** Militia
   (2) plus a 2-IPP upgrade becomes Infantry (3); Minor Port (3) plus a 4-IPP
   upgrade becomes Major Port (6). Those price differences are printed rules,
   not transcription errors. Upgrade costs: Infantry to Motorized +1; Minor to
   Medium Factory +7; Medium to Major Factory +6; Minor to Major Dockyard +5;
   Minor to Major Shipyard +5 (RB pp51,93-96).
6. **Adopted construction value is the cumulative already-paid amount**, replacing
   that ledger entry with full completed catalog value at completion. Official
   setup queues must identify the correct stage and paid amount; initial amounts
   require source reconciliation rather than a new user choice. Japan's
   USA-triggered Light Carrier queue entries are excluded from this campaign.
   Repairs purchased but not yet completed and construction
   pushed backward by bombing require an explicit accounting convention before
   implementing dense rewards.
7. **Temporary ship-crew Militia is not a second purchased asset.** RB §11.5 p78
   temporarily supplies Militia in land combat; count the ship once. Likewise,
   inherent facility AAA is part of the facility, not a free 4-IPP AAA unit.

## Future acceptance tests (not implemented here)

- `VALUE-001`: exactly two missing in-scope type values are requested; a null
  value fails valuation validation rather than silently becoming zero.
- `VALUE-002`: setup Infantry, purchased Infantry and free recruited Infantry
  follow the same approved completed-asset valuation convention.
- `VALUE-003`: two directed edges and two sea accesses to one facility contribute
  one value; two distinct Honshu shipyards contribute two.
- `VALUE-004`: a 5/5 Heavy Cruiser totals 10 when complete, but the construction
  ledger contains only paid stages before completion, never both categories.
- `VALUE-005`: damaged capital ship deducts zero under the literal repair-price
  formula; damaged Major Factory with 20 remaining repair cost is -2 unless the
  user explicitly authorizes another convention.
- `VALUE-006`: neutral warlord assets count toward nobody; rule-controlled minor
  assets aggregate once to its controlling alliance without creating treasury or
  income collection forbidden by the minor's rules.
- `VALUE-007`: physical city IPP loss changes income rate; inherent AAA and
  temporary crew Militia create no additional wealth.
- `VALUE-008`: applying a price discount changes expenditure without silently
  changing the selected catalog/historical/replacement valuation policy.
