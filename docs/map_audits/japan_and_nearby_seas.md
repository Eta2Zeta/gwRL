# Japan and nearby seas: map audit, 12 September 2026

Scope: Tokyo, Honshu, Hokkaido, Kyushu and Okinawa; all boundaries of P14, P15,
P16, P32, P33 and P41. The earlier China/Mongolia transcription is retained.
This is a visual transcription with structural regression tests, not a claim
that the entire global map or a playable July 1936 setup is certified.

Sources: `game_content/maps/gw36map.png` (original 9900 × 4888 image),
`game_content/rules/Global War 1936 v4.3 Rulebook.pdf`, especially §1.9/p16
and the Honshu port example on p63. The Japan national sheet's starting units,
factories and construction queues require a separate setup transcription.

## Japanese tiles

All five are Japanese-owned mountain terrain. Tokyo alone is a city land zone,
capital and victory city. None has a printed river route or river-crossing penalty.

| Tile | IPP | Intrinsic facilities | Master-map land neighbors | Master-map sea neighbors |
| --- | ---: | --- | --- | --- |
| Tokyo | **2** (was 3) | Airfield | Honshu | P16 |
| Honshu | 2 | **Airfield added** | Tokyo, Kyushu, Hokkaido | P15, P16 |
| Hokkaido | 1 | None | Honshu, South Sakhalin, Kurile Islands | P7, P15, P16 |
| Kyushu | **2** (was 1) | None | Honshu | P15 |
| Okinawa | 0 | None | None | P33 |

Honshu changed from normal to mountain, Hokkaido from forest to mountain, and
Okinawa from normal to mountain. Tokyo and Kyushu were already mountain.
Tokyo is a compact eastern zone: Honshu wraps west and north of it. Do not add
Tokyo–Hokkaido or Tokyo–P15. The Nagasaki city dot does not make Kyushu a city
land zone.

Every reviewed Japanese land approach has `border_terrain: "mountain"`, in both
directions. Coast edges use land→sea `"coast"` and sea→land `"mountain"`.
Tokyo–Honshu and Honshu–Kyushu are ordinary land connections with railways.
There are no gauge changes on the reviewed Japanese connections.

## Narrow crossings

| Direct land pair | Printed unit capacity | All seas touching the crossing line | Railway |
| --- | ---: | --- | --- |
| Honshu–Hokkaido | 2 | P16 | **False**, corrected from true |
| Hokkaido–South Sakhalin | 1 | P7, P8, P16 | False; missing land pair added |
| Hokkaido–Kurile Islands | 1 | P9, P16 | False; missing land pair added |
| Hainan–Kwangtung | 1 | P41 | False; existing pair retained, blocking sea added |

Rulebook §1.9 says the printed number is a **unit capacity**, not a count of
crossings, and prohibits strategic rail movement across these lines. The rails
on Honshu and Hokkaido visibly stop at opposite shores. The capacity-2 dotted
line is wholly in P16; it is not the P15/P16 boundary.

For compatibility, `narrow_crossings` retains its existing field name but means
the printed capacity on reviewed land pairs. New reciprocal
`narrow_crossing_sea_zones` lists the seas that can block each crossing. These
references do not create coastal adjacency: South Sakhalin and the Kuriles do
not thereby become ordinary P16 coastal neighbors.

`passable: true` on a narrow land pair does **not** grant ordinary unrestricted
movement. The future engine must enforce eligible unit classes, combat versus
non-combat movement, capacity, artillery and enemy sea-presence restrictions.
Narrow markers were cleared from audited Japanese and P41 coast edges and from
P9–P16; capacity belongs to the direct land pair. Other legacy global sea/coast
flags have not been comprehensively migrated and are not authoritative rules.

## Coastal infrastructure

| Tile–sea | Physical facilities | Rail access |
| --- | --- | --- |
| Tokyo–P16 | Major shipyard | True |
| Honshu–P15 | **Two separate major shipyards**, northwest and south | True |
| Honshu–P16 | **Major port**, not minor port | True |
| Hokkaido–P7 | **Major port**, not minor port | True |
| Hokkaido–P15 | None; short coast added | False |
| Hokkaido–P16 | None | False |
| Kyushu–P15 | Major port + major shipyard | True |
| Okinawa–P33 | Minor port + seaplane base | False |

Remove Honshu–P7 and Hokkaido–P8. Hokkaido's small southwestern P15 coast is a
finite boundary; its northeastern cape does not reach P9. Honshu's northeastern
port is on P16; both its shipyards are on P15.

Facility types and IDs now normalize **as pairs**, preserving distinct same-type
instances. Honshu's shipyard IDs are `facility_honshu_northwest_major_shipyard`
and `facility_honshu_south_major_shipyard`. This does not reintroduce railroad
IDs: rail remains boolean. Nanking's two access edges still share one port ID.

## Complete audited sea neighbor sets in the master map

| Sea | Sea neighbors | Land neighbors |
| --- | --- | --- |
| P14 | P15, P32 | Beiping, Hopeh, Shantung, Nanking, Rehe, Korea |
| P15 | P7, P14, P16, P32, P33, P34 | Korea, Hokkaido, Honshu, Kyushu |
| P16 | P7, P8, P9, P15, P17, P18, P26, P34, P35 | Hokkaido, Honshu, Tokyo |
| P32 | P14, P15, P33, P41, P42, P43 | Nanking, Hunan, Formosa |
| P33 | P15, P32, P34, P43 | Okinawa |
| P41 | P32, P42, P50 | Annam-Tonkin, Kwangtung, Hong Kong, Hainan, Formosa, Luzon and the Visayas |

P16 gained P7, P8, P17, P18, P26 and P35. The P16/P35 southern boundary is short
but finite. P18 and P26 were added as **endpoint-only nodes**; their other borders
are not audited. All reviewed sea→sea approaches are `"sea"` in both directions.

P41 gained Annam-Tonkin, with a minor port, railway access and a jungle landing
approach. P41→Luzon and the Visayas was corrected to jungle. P41 does not touch
Cochinchina. P16 does not touch Bonin (inside P35) or Kyushu. Tiny corner contacts
were not added.

## Closed scenario consequences and outstanding limitations

The generated scenario now selects 38 nodes: 27 China/Mongolia-area land tiles,
five Japanese tiles, and six seas. Tannu Tuva was removed from the scenario by
user decision after the initial 39-node extraction, but remains in the global
map. The extraction still removes 45 outbound neighbor entries: removing Tannu
Tuva drops its two external edges from the report and adds the two retained
neighbors' edges into Tannu Tuva. The global map retains real outside connections
and reciprocal data.

Hokkaido's P7 port is deliberately absent from the extracted map because P7 is
excluded. Its outside narrow land crossings are removed too. Honshu–Hokkaido and
Hainan–Kwangtung retain their required P16/P41 blocking-sea references. A different
manifest must include all blocking seas for any retained annotated land crossing;
the extractor fails clearly instead of silently rewriting that crossing's rules.

Tannu Tuva's national identity/control/home-country treatment remains unresolved
in the master map, but is deferred and does not affect this scenario's political
setup or wealth attribution because the tile is excluded. Previously flagged
external China borders are cut away, not newly certified. South Sakhalin/Kurile
node identity and terrain were not broadly corrected in this pass, despite the
reviewed Hokkaido-facing crossings. This artifact is static geography, not a
complete starting position or a working full-rules environment.

## Reproducible visual evidence

These crop rectangles use the original image's pixel coordinates
`(left, top, right, bottom)`; no generated imagery was used to infer boundaries.

| Feature | Rectangle |
| --- | --- |
| Tokyo/Honshu boundary and northern facilities | (7470, 1900, 7850, 2410) |
| Honshu's southern shipyard relative to sea boundary | (7480, 2310, 7600, 2480) |
| Hokkaido coasts and three crossing lines | (7550, 1550, 8090, 2060) |
| Rail gap between Honshu and Hokkaido | (7640, 1870, 7780, 2030) |
| Kyushu | (7240, 2280, 7580, 2610) |
| Okinawa | (7200, 2590, 7410, 2820) |
| P16 eastern borders | (7550, 1670, 8330, 2480) |
| P16 southern border | (7520, 2400, 8210, 2700) |
| P32/P33/P41 region | (6520, 2410, 7750, 3300) |
| Annam-Tonkin port/rail | (6490, 2760, 6770, 3130) |
