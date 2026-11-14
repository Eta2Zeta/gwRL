# Economy: income, purchases, construction and research

This module handles money: what a nation earns, what it may buy, how purchases
are paid for in stages and placed on the map, repairs, research and lend-lease.
It is one of the engine's six rules modules
([overview](README.md#7-the-rules-by-subject)).

Code: `include/game/economy.hpp`; `src/economy.cpp`,
`src/economy_lendlease.cpp`; prices and purchase rules come from the catalog
(`include/game/catalog.hpp`, `src/catalog.cpp`). Rules data:
`game_content/rules/gw36_economy_v43.json`.

## 1. Money

The game's money is the IPP. Three nations have a treasury: Japan, the KMT and
the CCP. Mongolia, Dadao and the warlords have none and earn nothing.

A nation's income is collected at the end of each of its turns
(`evaluateIncome`):

- **Land.** The IPP value of every zone it holds.
- **Japan's bonus.** One more IPP for each of Beiping, Hopeh, Shantung,
  Nanking, Hunan and Kwangtung that Japan holds.
- **No capital, no income.** A major power that does not hold its capital
  collects nothing.

Bombing a city lowers its zone's IPP value for good, by one for every 20 points
of damage. Repairing the city does not bring the value back.

The other sources of income in the full game, such as trade and the Burma
Road, need nations or routes this campaign leaves out.

## 2. The Production Phase

Production has two steps.

**Research first, for major powers.** A major power may make one research
attempt per undamaged Major Factory it holds. It names a technology and a
factory (`economy_research`), and the engine rolls a twelve-sided die. It ends
the step with `economy_finish_research`. [Section 6](#6-research) explains the
roll.

**Then spending**, in any order, while the money lasts:

| Move | What it does |
| --- | --- |
| `economy_purchase` | Starts a new unit, facility or upgrade and pays its first stage |
| `economy_advance` | Pays the next stage of something already started |
| `economy_repair` | Pays to repair a facility or a city, 1 IPP for each point of damage |
| `economy_request_rail` | Asks another nation's leave to build a railroad across the border into its land |
| `economy_lease_declare`, `economy_lease_upgrade` | Names a lend-lease gift ([section 7](#7-lend-lease)) |

## 3. Buying

**What a nation may buy** is one row of its build chart
([catalog](scenario.md#5-the-catalog)). Each row names what is bought, its
price in stages, and its conditions: the date, a technology, a limit per turn,
major or minor power status.

**Prices are paid in stages.** A purchase pays the first stage and puts a
*project* in the nation's construction queue. Each later turn the nation may
pay one more stage (`economy_advance`), at most one stage per project per
turn. When every stage is paid, the project is ready to place. Japan starts
with two projects already in its queue, a Heavy Cruiser and a Fleet Carrier,
with 5 IPP paid into each.

**Factories limit production.** What a nation can finish in a turn is capped by
its factories and, for ships, its shipyards. Militia and facilities need no
factory. The KMT and the CCP are a further exception while they are minor
powers: they buy infantry-class units and cavalry without factories.

**Improved Construction changes the price list.** With that technology, a ship
or a facility costs 1 IPP less per stage, or its first two stages can be paid
as one. The printed price is then no longer offered, since it would buy the
same thing for more.

**A facility is bought for a place.** The purchase names the zone, and for a
port, a base or a railroad the border or sea zone it serves. A railroad joins
two land zones:

- **Inside one's own land** it is simply bought.
- **Across the border into another nation's land** the nation asks first
  (`economy_request_rail`), and the other nation approves or declines
  (`economy_approve_rail`, `economy_decline_rail`). Declining costs nothing.
- **One railroad per border** (RCL-019): where one stands or is being built,
  damaged or not, no second can be bought.

## 4. Placing

In the Place Units Phase the nation puts its ready projects on the map
(`economy_place`). The move names the project and where it goes.

- **Where.** In a zone the nation has held since the turn began and that is in
  [supply](movement.md#5-supply). Land and air units appear at a factory with
  capacity left, ships at a shipyard.
- **New things wait a turn.** A facility placed this turn produces nothing this
  turn, and neither does a factory captured this turn.
- **Upgrades replace a piece.** An upgrade is placed onto a unit or facility of
  the type it upgrades, chosen at placement. A unit placed this turn cannot be
  upgraded.
- **No upgrade at sea or into the wrong cargo** (RCL-021). A unit aboard a ship
  at sea is not offered an upgrade, and neither is a unit whose transport could
  not carry the upgraded type. The upgrade waits in the queue.

## 5. Repairs

| What is damaged | Cost | Notes |
| --- | --- | --- |
| A facility | 1 IPP per point | |
| A city | 1 IPP per point | The lost IPP value does not return; a destroyed city cannot be repaired |
| A railroad | 1 IPP per point | Each side of the border is repaired by the nation holding it |
| A capital ship | free | It takes a repair place at a shipyard instead |

Bombing can also hit a project under construction. Every three points of
damage undo one paid stage, and the money is not refunded
(`damageConstruction`).

## 6. Research

A technology has four stages. An attempt succeeds when the die shows at most
the technology's threshold for its current stage, and moves it up one stage.
After the fourth, the technology is complete and works at once. Some
technologies change units on completion: Airborne Doctrine, for example, turns
Airborne Infantry into Elite Airborne Infantry.

- **One attempt per Major Factory per turn**, and the factory cannot research
  in the turn it was placed or moved.
- **One attempt per technology per round.**
- **The third stage is locked before July 1939.**
- **An attempt costs nothing.**

Only major powers research. Japan is one from the start; the KMT and the CCP
are once they have become major powers ([politics](politics.md#4-becoming-a-major-power)).

## 7. Lend-lease

A major power may give another nation a finished unit or base, or pay for a
militia upgrade or a facility repair there (`lendLeasePermitted`). The receiver
must be at war with a major power, and must not be at war with any nation of
the giver's alliance. Japan may also give to Dadao while it controls it; RCL-010
says where such a gift may be delivered.

| Move | Phase | What it does |
| --- | --- | --- |
| `economy_lease_declare` | Production | Names a ready project in the giver's queue and the nation that will get it |
| `economy_lease_upgrade` | Production | Pays for a militia upgrade the receiver places later |
| `economy_lease_repair` | Production | Pays for the repair of one of the receiver's damaged facilities |
| `economy_lease_deliver` | Place Units | Delivers a declared gift, by a supplied route to the receiver |
| `economy_lease_place` | Place Units | The receiver places what it was given |

A giver names one gift per receiver per turn. A gift that cannot be delivered
waits in the queue.

## 8. What the tests cover and what random play shows

Tests: `tests/economy_tests.cpp` and `tests/catalog_tests.cpp`. In 240 random
games every economy move came up except `economy_lease_repair`
([record](../archive/records/move_census_2026_11_14.md)). The printed pages
behind these rules are listed in
[Economy: source coverage](../rules/economy_sources.md) and
[Catalog: source coverage](../rules/catalog_sources.md).
