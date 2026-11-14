# The campaign the engine plays

The engine plays one scenario: the Japan–China theatre of Global War 1936,
from July 1936 to July 1941, cut out of the game's world map. This page says
what is in it at the start and where each part of it is stored. The reasons for
the choices are in the
[approved scenario decisions](../plans/japan_china_full_rules_plan.md#approved-scenario-decisions).
The numbers below were read from the engine's starting position on 14 November
2026.

## 1. In brief

| | |
| --- | --- |
| Calendar | 11 rounds of half a year: July 1936, then every January and July to July 1941 |
| Players | Three alliances: the Axis, the Allies and the Comintern |
| Nations taking turns | The CCP, Mongolia, Japan and the KMT, in that order each round |
| Other nations | Eight Chinese warlords, which take no turn until they join a side |
| Map | 37 zones: 31 land and 6 sea |
| Pieces at the start | 99 units, 22 facilities and 17 railroads |
| Money at the start | Japan 15 IPP, the KMT 6, the CCP 2 |
| What the players play for | Their alliance's wealth minus the other two alliances' wealth, at the end |

IPP, industrial production points, is the game's money. A zone's IPP value is
the income it gives the nation that holds it.

## 2. Nations and alliances

A *nation* owns units, holds land and, if it is a full participant, has a
treasury and a turn. An *alliance* is a player: it chooses every move of the
nations it plays.

| Nation | Played by | Status at the start | Treasury | Units | At war with |
| --- | --- | --- | ---: | ---: | --- |
| Japan | Axis | Major power | 15 | 48 | nobody |
| KMT | Allies | Minor power | 6 | 12 | the CCP |
| CCP | Comintern | Minor power | 2 | 5 | the KMT |
| Mongolia | Comintern | Minor power, with no treasury | none | 2 | nobody |
| Eight warlords | nobody | Unaligned | none | 32 | nobody |

- **The warlords** are the Zhili Clique (Beiping and Hopeh), the Guangxi Clique
  (Kwangtung and Hainan), Mengjiang (Suiyuan), the Ma Clique (Tsinghai), the
  Szechwan Clique (Sikang), the Sinkiang Clique, Tibet and the Yunnan Clique.
  Each is one nation in the engine, such as `warlord_beiping_hopeh`. A warlord
  that aligns with a side is played by that side from then on
  ([politics](politics.md)).
- **Dadao** is a thirteenth nation that does not exist at the start. Japanese
  influence over a warlord can create it as a Japanese-controlled minor.
- **Mongolia** takes its turn in the place the USSR has in the full game. The
  USSR itself is not in the campaign, and neither is the Far East Command.
- **The KMT and the CCP become major powers** when they hold land worth 13 IPP.
  Until then they may move and attack only inside the Chinese Home Country and
  the sea zones next to it.

A nation's *Home Country* is a fixed list of land zones, which rules on supply,
production and militia refer to. Japan's is Hokkaido, Honshu, Kyushu and Tokyo.
The KMT and the CCP share the Chinese Home Country, 25 of the map's land zones:
all of them except Japan's four, Okinawa and Korea. It includes Manchuria,
Formosa, Tibet and Mongolia's four zones.

## 3. The map

Each land zone has a value in IPP, a terrain, and at the start a nation that
holds it. A *city* is a zone marked as one, which changes combat and bombing
there. Railroads join neighbouring land zones, at most one per border.

| Zone | Held at the start by | IPP | Terrain | Starts with |
| --- | --- | ---: | --- | --- |
| Tokyo (city, Japan's capital) | Japan | 2 | mountain | Major Factory, Major Shipyard, Airbase; 1 infantry, 1 fighter, 2 tactical bombers |
| Honshu | Japan | 2 | mountain | 2 Major Shipyards, Major Port, Airbase; 1 motorized infantry |
| Kyushu | Japan | 2 | mountain | Medium Factory, Major Shipyard, Major Port; 1 infantry |
| Hokkaido | Japan | 1 | mountain | 1 infantry |
| Okinawa | Japan | 0 | mountain | Minor Port, Seaplane Base; 1 militia, 1 seaplane |
| Formosa | Japan | 2 | mountain | Major Port; 1 militia, 1 fighter |
| Korea | Japan | 2 | mountain | Minor Port, Airbase; 1 infantry |
| Rehe | Japan | 1 | normal | Minor Factory, Major Port; 2 infantry, 1 militia |
| Eastern Manchuria | Japan | 1 | normal | 2 infantry, 1 cavalry, 1 militia |
| Northern Manchuria | Japan | 1 | normal | 1 mountain infantry, 1 militia |
| Western Manchuria | Japan | 1 | normal | nothing |
| Nanking (city) | KMT | 2 | normal | Major Port; 4 infantry |
| Shantung | KMT | 2 | normal | Major Port, Minor Dockyard; 2 infantry |
| Hunan | KMT | 2 | normal | 2 infantry |
| Szechwan | KMT | 0 | mountain | 1 infantry, 1 militia |
| Kweichow | KMT | 0 | mountain | 2 militia |
| Shensi | CCP | 2 | mountain | 2 mountain infantry, 1 cavalry, 2 militia |
| Central Mongolia | Mongolia | 1 | normal | 1 cavalry |
| Kerulen | Mongolia | 1 | normal | 1 militia |
| Kobdo | Mongolia | 0 | mountain | nothing |
| Ulyassutai | Mongolia | 0 | normal | nothing |
| Beiping (city) | Zhili Clique | 2 | normal | Minor Port; 3 infantry |
| Hopeh | Zhili Clique | 1 | normal | 1 militia |
| Kwangtung | Guangxi Clique | 2 | mountain | Major Port; 2 infantry, 4 militia |
| Hainan | Guangxi Clique | 1 | mountain and jungle | nothing |
| Suiyuan | Mengjiang | 1 | mountain | 2 infantry, 1 cavalry, 2 militia |
| Tsinghai | Ma Clique | 0 | mountain | 1 infantry, 1 cavalry, 2 militia |
| Sikang | Szechwan Clique | 0 | mountain | 2 infantry, 1 militia |
| Sinkiang | Sinkiang Clique | 0 | mountain | 2 infantry |
| Tibet | Tibet | 0 | mountain | 1 mountain infantry, 1 cavalry |
| Yunnan | Yunnan Clique | 1 | mountain | 2 infantry, 4 militia |

The six sea zones are P14, P15, P16, P32, P33 and P41. Japan's fleet starts in
four of them: 24 ships, with 3 carrier aircraft aboard the two carriers in P15.
No other nation has a ship.

The 17 railroads at the start form three groups: Tokyo, Honshu and Kyushu;
Korea and Manchuria; and China from Beiping south to Kwangtung, with branches
to Suiyuan and Shensi. One railroad, from Beiping to Rehe, joins the Chinese
and Manchurian groups. Each is named by its two zones, for example
`rail_land_china_beiping__land_china_hopeh`.

Two pieces are not on the map: Japan starts with a Heavy Cruiser and a Fleet
Carrier under construction, with 5 IPP already paid into each.

The [Campaign Observatory](../../web/campaign_viewer/README.md) draws all of
this on the printed board.

## 4. What is left out

The campaign is closed: a zone outside the 37 does not exist, and nothing moves,
supplies or arrives through one. These parts of the full game are switched off:

- convoys, convoy raiding and escorts, and interdiction;
- Japan's Kido Butai and the light carriers that arrive on war with the USA;
- everything that needs the USSR: border clashes, the CCP's Soviet income bonus
  and the CCP's Soviet purchase unlock.

Blockades, Maritime Air Patrol, amphibious assaults, strategic bombing and the
Chinese nations' rise to major power stay in. The
[core rules ledger](../rules/core_rules_ledger.md) lists every rule with whether
it applies.

## 5. The catalog

The catalog says what each kind of piece is. It is shared game data, not part of
the scenario, and lives in `game_content/catalog/gw36_v43`
(`include/game/catalog.hpp`, `src/catalog.cpp`).

| File | Holds |
| --- | --- |
| `land_air.json` | 37 land, air and rocket unit types: values, classes, abilities |
| `naval.json` | 16 ship types, with their values in every damaged state |
| `facilities.json` | 15 facility types: factories, ports, shipyards, dockyards, bases, defences, the railroad |
| `technologies.json` | 16 technologies: what each needs and what it unlocks |
| `build_charts.json` | 207 purchase rows: what Japan, the KMT and the CCP may buy, when, and at what price |

A unit type being in the catalog does not make it buyable: a nation buys only
from its own rows of the build charts ([economy](economy.md)). Two of Japan's
starting ship types, the Torpedo Boat Destroyer and the Coastal Submarine, have
no purchase row; the scenario gives them values of 5 and 4 IPP for scoring.

## 6. The score

Nothing is scored before the end. After the last turn of round 11, each
alliance's *wealth* is its income per turn plus a tenth of the value of its
units, its facilities and railroads, its treasury and the money paid into
unfinished construction. An alliance's score is its own wealth minus the other
two alliances' wealth (`src/campaign_objective.cpp`). The exact definition,
with its accounting choices, is in the
[plan](../plans/japan_china_full_rules_plan.md#wealth-definition-and-approved-accounting-decisions).

At the start the Axis's wealth is 66.0, the Allies' 12.4 and the Comintern's
4.4. A warlord's pieces count for nobody until it aligns.

## 7. Where the scenario is stored

Everything is under `game_content/scenarios/japan_china_1936`, and
`src/campaign_setup.cpp` loads it.

| File | Holds | Made by |
| --- | --- | --- |
| `manifest.json` | The list of the 37 zones to keep | by hand |
| `map.json` | Those zones cut out of the world map, with every border to an outside zone removed | `tools/build_theatre_scenario.py` |
| `m0/scenario_contract.json` | The campaign's rules of play: calendar, turn order, starting money, what is switched off, how wealth is scored | by hand |
| `m0/japan_setup.json`, `m0/china_minor_setup.json` | The starting pieces | by hand, from the printed setup charts |
| `m1/faction_index.json` | Every nation's identifier and the names the sources use for it | `tools/scenario_factions.py` |

The folders `m0` and `m1` are named after the build stages that made them. The
world map itself is `game_content/maps/gw36_manual_map.json`
([game content](../../game_content/README.md)).

The engine checks what it loads. The rules profiles record the SHA-256 of the
files they depend on, these scenario files among them, and loading stops if one
has changed without its recorded hash. Where each starting piece and price
comes from in the printed game is traced in the
[setup and price audits](../rules/README.md).
