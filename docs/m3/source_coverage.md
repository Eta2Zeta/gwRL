# M3 source coverage

Reviewed 21 October 2026 against the [M3 acceptance inventory](../plans/japan_china_full_rules_plan.md#m3-implement-complete-unit-and-facility-definitions). The catalog adds definitions and queries; the campaign still requires the later politics, movement, economy and combat milestones.

## Inventory and sources

The five files in [the v4.3 catalog](../../game_content/catalog/gw36_v43/) contain 53 unit types, all 58 surviving damage states, 15 facility types and 16 technologies. Every printed Japan/KMT/CCP build-chart purchase row is represented: 181 printed rows, three derived railroad terrain-price alternatives and 23 source-backed upgrade rows, for 207 rows total. Registration of a foreign or setup-only type does not grant national purchasing rights.

| Catalog | Principal source coverage | Recorded details |
|---|---|---|
| `land_air.json` | Rulebook PDF pp83–89 and92; Japan NRS pp4–6; KMT NRS pp3–5; CCP NRS pp4–5; cited combat chapters | Classes and ordinary values; support, first strike, target selection, airborne cargo, bombing/interception/AAA modes, terrain exceptions and upgrades. Cavalry is a vehicle. |
| `naval.json` | Rulebook PDF pp89–92, technology pp46–49, cited naval movement/combat/port/repair chapters; Japan NRS pp4,7; KMT/CCP NRS p6 | Every surviving capital-ship damage state; bombardment, aircraft groups, cargo, submarine/MAP interactions, repair and national movement exceptions. The damage-value exception below is explicit. |
| `facilities.json` | Rulebook PDF pp92–99; construction/repair pp50–51,79–80; cited bombing/AAA chapters | Staged costs, production/repair capacity, damage limits, upgrades, site restrictions, defenses, railroad route costs and gauge. Detailed factory/dockyard/shipyard tables govern damage and Improved Factories capacity. |
| `technologies.json` | Complete technology table and descriptions, rulebook PDF pp45–50 | Research thresholds/date gate, unlocks, additive modifiers, conversions and conditional effects. Improved Factories and Improved Construction remain distinct. |
| `build_charts.json` | Complete Japan NRS PDF pp5–8 and KMT/CCP NRS pp3–7, including continuation tables and footnotes; cited facility/upgrade rules | Major/minor status, dates, technology gates, shared caps, exact production/placement prerequisites and upgrade alternatives. |

Page numbers above are one-based PDF pages. Each local source record stores its repository path, v4.3 version and SHA-256; individual definitions, modes and rules carry page/section references. Relevant complete source pages and charts were inspected, with rendered tables checked where extraction could collapse columns. [Source regression tests](../../tests/test_m3_catalog_sources.py) check source bytes, reference bounds, chart inventory, independent price/date/cap fixtures and cross-references.

## Recorded source exceptions

**Capital-ship damage.** The local v4.3 text refers to reduced combat values without supplying every damaged battle-board cell. The official publisher's available composite battle-board image was inspected but was too small to certify those cells. It is recorded as search evidence, not value authority. The user supplied this clarification on 21 October 2026:

> Its basically just -2 for each damage of the battleships, and -1 for carriers defending

`user_naval_damage_2026_10_21` records that text and the interpretation stated back to the user: subtract two per damage from Battleship/Heavy Battleship attack, defense and shore bombardment; subtract one per damage from carrier defense. This gives damaged Battleship A6/D6/bombardment2; Heavy Battleship A8/D8/bombardment3 at one damage and A6/D6/bombardment1 at two damage; damaged Fleet/Heavy Fleet Carrier D1. The separately printed movement rule is a flat minus one while damaged, and the unconditional printed carrier capacities remain unchanged. The ruling has no invented PDF page, file or hash. `naval.json` preserves its exact wording, applied interpretation and state-level references.

**Setup-only values.** Torpedo Boat Destroyers and Coastal Submarines retain empty purchase costs and null generic asset values: neither is buildable. Their approved M0 valuation overrides remain five and four IPP per piece respectively in the [frozen scenario contract](../../game_content/scenarios/japan_china_1936/m0/scenario_contract.json). These are scenario valuation inputs, not newly invented generic prices. Coastal Defense Ships are source-only definitions and add no pieces or purchase access to this campaign.

**Campaign exclusions.** Printed convoy modifiers and the precise CCP Soviet-rail and KMT Burma-Road prerequisites are preserved as source data. They do not create outside support nodes or bypass the closed campaign's disabled mechanics. Kidō Butai does not grant a discount in this campaign. These decisions do not rewrite the publisher's full-world rules or the frozen M0 files.

## Conditional data and later execution

Printed base values remain distinct from conditional effects. Japanese Dug in Defense, Surprise Attack, destroyer Marine transport and KMT Low Morale are structured national rules with source references; they do not silently alter every unit's base stats. The same applies to artillery pairing, terrain, submarine target eligibility, facility AA, carrier aircraft combinations, repair timing and technology effects that require a combat or site context.

Catalog queries provide definitions, applicable plain technology modifiers, militia movement, national purchase/date/technology/cap checks, price alternatives and explicit placement prerequisites. Later handlers must establish the actual context, evaluate paths/sites, allocate support/capacity and execute the effects. A returned mode is not permission to skip those conditions. Railroad cost and damage depend on the terrain crossed by its route; an ordinary type-only value does not determine a particular four-IPP route's valuation. Purchase spending, recruitment/evolution, reaction routing, damage/casualties, combat sequencing, repair completion and final wealth accounting remain later milestone work.

The review closed the missing Japanese conditional rules and KMT Low Morale definitions and identified corrections to ordinary port-attack AA and detailed facility capacities. The user ruling closes the capital damage-cell source gap; it does not certify a readable publisher battle-board image or claim completed combat execution.
