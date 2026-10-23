# Retained narrow crossings and naval passage

RB §13.2.7 p98 permits Coastal Artillery to fire when an Enemy Surface Ship
**crosses the printed narrow-crossing line**, including scrambling and entering
port. Being in the same sea zone is not sufficient. The printed blocking sea
for a land crossing therefore does not define a mandatory naval passage.

The retained map needs no mandatory passage overlay for its two crossings:

| Crossing | Reviewed artwork | Why ordinary retained movement can bypass the line |
| --- | --- | --- |
| Hainan–Kwangtung, P41 | [Source crop](evidence/hainan_kwangtung_crossing.png), native map rectangle `(6250,2550)–(7150,3300)` | Water west of the crossing connects around Hainan's south/west coast to outer P41. The Kwangtung port is accessible by that route. P32–P41 movement and P41 port access do not require crossing the dotted line or another sea-zone border. |
| Honshu–Hokkaido, P16 | [Northern source crop](evidence/honshu_hokkaido_crossing.png), native rectangle `(7100,1350)–(8350,2450)`; [southern Japan crop](../map_audits/full_world/evidence/ap_naval_japan.png), rectangle `(7180,1870)–(8110,2630)` | P15 and P16 also share a southern sea frontier off southern Honshu. Ships can use that frontier for the same one-border movement instead of the northern crossing. The retained Honshu and Tokyo facilities facing P16 lie south of the northern line. |

The crops come directly from `game_content/maps/gw36map.png` (9900 × 4888).
Neither the frozen map nor its land-crossing capacities were changed.

The source-backed mandatory retained list is consequently empty:

```json
{"mandatory_naval_passage_paths": []}
```

Do not turn either blocking-sea annotation into automatic passage fire. A future
map can provide explicit passage paths, and a deliberately selected passage can
use the same reaction and three-shots-per-Player-Turn accounting as other Coastal
Artillery fire. An optional passage offers no movement advantage in this retained
graph; no within-sea position or mandatory crossing is inferred. Amphibious
assault shooting remains independently applicable here.
