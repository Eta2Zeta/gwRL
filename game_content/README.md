# Game content

This directory keeps source material and authored game data separate from engine and training code.

Current implementation status (23 October 2026): M0–M12 implementation gates are complete,
including naval source review, two full 44-turn campaign traces and the explicit
multi-agent API/vector search. Reviewed rule profiles supplement the frozen M0
map. [M12](/Users/home/Desktop/gwRL/docs/m12/README.md) adds the verified learning/resume/evaluation pipeline; playing strength remains untested. RCL-012 is
closed; RCL-013 is adopted. RCL-014 and RCL-015 are provisionally adopted. Consult the shared
clarification register for the developer-report list; user interpretations are
not publisher-confirmed errata.

## Rule sources and discussion review

The [annotated HTML rules reader](rules/html/index.html) combines the main
rulebook and all 13 national sheets with separately labeled clarifications,
fixes, unresolved questions and campaign choices. The
[pilot audit](rules/discord_audits/2025-08-26_2025-09-26/README.md) covers all
1,129 visible discussion messages from 26 August through 26 September 2025.
It found no new genuine rule gaps. The active
[clarification register](rules/clarifications.md) excludes questions already
answered by the sources; their earlier records remain in
[archived source checks](rules/source_answered_questions.md).

## Shared catalog

`catalog/gw36_v43/` contains the source-linked M3 unit, facility, technology and
national build definitions used by the campaign engine. It covers every printed
Japanese/Chinese build-chart row and preserves conditional abilities, surviving
damage states and source-only unbuildable types. See the
[M3 record](/Users/home/Desktop/gwRL/docs/m3/README.md) for queries and verification.

## Political rules

`rules/gw36_politics_v43.json` records the source-backed M4 political rules,
explicit retained Home Country memberships, adopted clarifications and the
closed-campaign Dadao controller ruling. The
[M4 implementation record](/Users/home/Desktop/gwRL/docs/m4/README.md) describes
the executable transitions and their boundaries with later rule modules.

## Maps

- `gw36_manual_map.json` is the detailed world graph used for ongoing environment development.
- `gw36_nation_home_country.json` maps nations to their home-country land zones.
- `gw36map.png` is the primary full-map image.
- `gw36map_double.png` places two copies side by side for inspecting map-edge connections.

The world map now uses schema 2 with **539 nodes**, a canonical physical-facility
registry, 15 resolved convoy lines, passages, exceptional routes, crossing records
and coast restrictions. Reviewed edits live in `maps/authoring/`; the generated
`gw36_manual_map_review.json` preserves sources and deferred decisions. See
[implementation status](../docs/map_audits/full_world/implementation.md). Board
images and evidence crops are local, Git-ignored inputs.

Regenerate the JSON map files from the repository root with:

```sh
./.venv/bin/python tools/build_manual_map_json.py
./.venv/bin/python tools/build_nation_home_country_json.py
```

### Directional map edges

An entry in `nodes[A].neighbors` whose `neighbor_id` is B describes **A → B**.
Its `border_terrain` and `river_crossing` describe that direction; the reverse
entry must be authored separately and can differ. A node's `terrain` describes
the territory itself, independently of the crossing.

`border_terrain` is a string for one terrain (e.g. `"desert"`) or a list for
multiple simultaneous first-round crossing terrains. Both French Somaliland →
Abyssinia and Italian Somaliland → Abyssinia explicitly have
`"border_terrain": ["desert", "mountain"]`. The mountain crossing is recorded on
each edge, not inferred from Abyssinia's node terrain. The reverse edges remain
`"border_terrain": "desert"`, and Abyssinia's own `terrain` remains `"mountain"`.

The Abyssinia audit includes seven land neighbors, with a railway only to French
Somaliland. A route merely touching a river does not count as crossing it: neither
direction of Nubia ↔ Abyssinia has `river_crossing`. Abyssinia → Sudan does, but
Sudan → Abyssinia does not, because the crossing is inside Sudan. These corrections
are maintained in `tools/build_manual_map_json.py` as well as the generated JSON.

### Canadian map audit

The Canadian pass adds Yukon Territory, District of Mackenzie, Queen Charlotte
Islands, and Ottawa; corrects IPP values, directional terrain, railways, narrow
crossings, coastlines, and printed naval facilities; and excludes tiny corner
contacts. Canadian territories retain the existing `United Kingdom` owner
convention. Ottawa has normal ground and `is_city: true`.

The user-approved opposite-edge links are **District of Mackenzie ↔ District of
Keewatin** and **Alberta-Saskatchewan ↔ Manitoba**. The latter's pre-existing
railway is retained but **not visually verified**. The whole-world pass confirms
Alberta–Upper Midwest; Manitoba–Upper Midwest remains unresolved and is not added.
Ordinary Ottawa sea adjacency remains unresolved. Alaska, Southeast Alaska,
New England and P1 now have their reviewed world connections.

The strip below Ottawa belongs to Quebec: the railway runs **Ottawa ↔ Quebec ↔
Nova Scotia**, with another branch **Quebec ↔ New England**. There is no direct
Ottawa–Nova Scotia or Ottawa–New England edge, and no direct railway between
Nova Scotia and New England. Ontario–Ottawa's two drawn tracks are represented
by one boolean railway connection in each direction.
The St. Lawrence Seaway is annotated on the Ontario–Ottawa–Quebec waterway and
the A24–A18 sea connection; Ottawa controls the canal.

`has_river` records **reciprocal river-route connectivity**, separately from the
directional `river_crossing` combat flag. The Canadian river-connected pairs are
Alaska–Yukon, Yukon–British Columbia, Ontario–Ottawa, Ottawa–Quebec,
Ontario–Great Lakes, and Ontario–The Northeast. For example, Yukon–British
Columbia has a river route but no combat crossing in either direction;
Nova Scotia → Quebec has a destination-side river crossing but no river route
through their shared border. These are map-data corrections, not implementation
of strategic movement, canal control, or enemy-bank restrictions in the engine.

### Rail connections

`railway_connection` is a **boolean or explicit unknown (`null`)** on each neighbor entry. Both directions
agree; two printed tracks across the same border still mean `true`, not two
separately named connections. There are no `railroads` arrays or `rail_id` fields.
`gauge_change` is derived only from independently verified gauges on both sides
of a printed railway; it is unknown where that source review is missing.
Original ownership cannot determine track gauge. Legacy coast rail flags remain
unchanged pending AM-229 and do not authorize rail movement into the sea.

The v4.3 rulebook, §10.6.2 (p. 67), explicitly applies strategic-bombing damage to
all railroads on the chosen border of the targeted land zone. Under §13.2.8
(p. 98), damaged railroads are unusable; maximum damage is 1 in normal terrain
and 2 in other listed terrain, and repair costs 1 IPP per damage point.
The static map flag records **infrastructure presence**, not current damage or
operability. Bombing/repair state and its movement restrictions still belong in
the game state; this data update does not implement them.

### China-theatre map audit

The approved pass covers Chinese and warlord territories, Mongolia, Manchuria,
Tannu Tuva, Korea, Formosa, Hong Kong, Hainan and the adjacent seas. It updates
node terrain/IPP, directional border terrain (including combined terrain),
river routes versus combat crossings, railways, coasts and naval facilities.
Szechwan is 0 IPP, bringing originally KMT territory income to 6; Central Mongolia
is 1 IPP. Hong Kong retains city status and its airfield on mountain terrain.

Key topology corrections:

- Remove Sinkiang–Szechwan, Tibet–Benares, Tibet–Calcutta and Sikang–Calcutta.
- Add Sinkiang–Eastern Kazakhstan, Sinkiang–Turkestan and Tibet–Tsinghai.
- Add Bengal as the impassable Himalayan endpoint for Tibet, Sikang and Yunnan.
  Tibet–Kashmir and Tibet–Nepal are impassable and have no railway.
  Yunnan–Burma remains impassable: the Burma/Ledo Road supply exception does not
  allow ordinary land movement through the Himalayas.
- Add the one-unit Hainan–Kwangtung narrow crossing and Hunan–P32 coast.
- Remove Northern Manchuria–Amur's railway; retain the Chita route and its gauge
  change. Add the Annam-Tonkin–Kwangtung railway and reviewed port rail access.
- Add Kwangtung's P41 major port; remove Korea's duplicate P15 port. Nanking's
  P14 and P32 entries retain the same shared physical port ID.
- Remove P7–P14; add P7–P8, P7–P15, P14–P32 and P15–P16. P15 is labeled Sea of
  Japan and P32 East China Sea. Reviewed sea-to-sea terrain is `sea` both ways.

Bengal (jungle, 1 IPP, FEC) and Turkestan (normal, 0 IPP, Soviet Union) are new
external endpoints, **not fully audited outside their China-facing borders**.
The derived home-country file is refreshed to match current territory IDs.
Bengal is not part of the FEC's explicit home-country list.

Unresolved matters are deliberately retained: Kobdo–Novosibirsk adjacency,
obscured southern Sinkiang/Himalayan contacts, and Tannu Tuva's national identity
versus control/home-country treatment. The new Sinkiang → Eastern Kazakhstan
combat river flag remains an **unverified false default**. Annam-Tonkin →
Kwangtung's jungle-plus-mountain entry is an image interpretation, not an
official published ruling. Tiny corner contacts were not added as neighbors.

Run the focused map regression checks from the repository root:

```sh
./.venv/bin/python -m unittest discover -s tests -p 'test_manual_map.py'
```

## Japan and nearby sea audit (12 September 2026)

The five requested Japanese tiles and P14/P15/P16/P32/P33/P41 are reviewed in
[the audit report](/Users/home/Desktop/gwRL/docs/map_audits/japan_and_nearby_seas.md).
Corrections include Tokyo/Kyushu IPP, mountain terrain, Japanese coast/rail/port
data, Honshu's two distinct P15 shipyards, the capacity-2 Honshu–Hokkaido narrow
crossing, missing P16 sea borders and Annam-Tonkin's P41 port.

Facility type/ID arrays represent paired physical instances; repeated types are
allowed with distinct IDs. Reviewed direct narrow crossings now name their
blocking seas in `narrow_crossing_sea_zones`; the existing `narrow_crossings`
field stores printed unit capacity, not a count of crossing lines. Railroad
presence remains a single boolean per border.

The global map now has 407 nodes. P18/P26 are new P16 boundary endpoints, not
fully audited sea zones. Existing outside-region warnings still apply.

## Rule sources

- `Global War 1936 v4.3 Rulebook.pdf` is the main source rulebook.
- `Global War 1936 v4.3 Neutrals setup chart.pdf` contains neutral-power setup material.
- `GW36 - NRS - *.pdf` are the national reference sheets, including FEC, KMT and CCP.
- [Rule clarifications and open questions](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md)
  is the shared register for unclear official wording, adopted project readings,
  and corrected audit mistakes. It is not publisher-issued errata. Scenario
  choices stay in the campaign documentation, not in this register.

## Scenarios

- `japan_china_1936/` contains a closed 37-node map projection (31 land, 6 sea;
  Tannu Tuva and Hong Kong excluded)
  and campaign specification. See its [README](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/README.md)
  for extraction commands, scope and limitations; it is not yet a playable setup.
  Its `m0/` data adds source-audited official setup, theatre-adjusted accounts
  and approved decisions, with 99 deployed pieces, 3 setup factories and 19 static
  facilities. FEC/USSR accounts, convoys, interdiction and Kido Butai are excluded.
  The [M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md) links the rules
  checklist, price tables, source reconciliation and the verified M0 specification
  frozen on 21 October 2026 (106 repository tests passed). The
  [M2 engine foundation](/Users/home/Desktop/gwRL/docs/m2/README.md) now loads the
  setup into shared C++ state and supplies action validation, turn/reaction
  timing, separate RNG streams and replay. Gameplay modules remain later work;
  current verification passes six CTest suites and 119 Python tests.
- `china_simplified_setup.json` defines the six-zone China training environment.
- `manual_battles/` contains deterministic battle fixtures used by the debug runner.
