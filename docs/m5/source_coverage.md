# M5 source coverage

The local v4.3 rulebook and native map are authoritative inputs. Full relevant
rulebook pages were inspected, including the illustrated geographic region map
on page 74. Source paths and SHA-256 digests are recorded in
`game_content/rules/gw36_movement_v43.json` and verified by scenario loading.

| Implemented rule | Source | Runtime boundary |
| --- | --- | --- |
| Directional/node terrain, combined terrain, cavalry movement | RB §§1.7–1.7.8, pp10–14 | Land paths preserve the final edge per unit; M7 applies combat modifiers |
| Narrow crossings and blocking seas | RB §1.9, p16 | Infantry-class noncombat crossing, Marine attack, printed shared capacity |
| Supply rail/river, facilities, refresh, landfall | RB §1.11, pp16–17 | Held and undamaged since active Player Turn start |
| Burma/Ledo roads | RB §1.12, p17 | Required external endpoints absent, therefore inactive |
| Supply and movement improvements, factory relocation | RB §8.2.1, p49 | Capacity/range bonuses; factory restrictions shared with M6 |
| Enemy land movement stop | RB §9.2, p54 | Register pending M7 battle, including empty attacks |
| Blockade | RB §9.4.6, p60; closed RCL-005 | Surface warships only; all accesses for shared facilities |
| Post-battle blitz | RB §10.5.1, p64 | M7 chooses eligible units and pairings; M5 proves subsequent route |
| Chinese gift and withdrawal | RB §10.10.1, p73 | Real friendly route or reserved adjacent transport capacity |
| Noncombat restrictions, rail regions and gauge | RB §§11.1–11.2.1, pp74–75 | No newly captured destination; each crossed region consumes capacity |
| Aircraft overflight and cargo links | RB §§11.3–11.4.1, pp75–76 | Reusable access/linkage; air/naval modules own full legality |
| Lend-lease final destination | RB §12.4, p80; RCL-010 | Recipient facility exception; naval deliveries never use inland land legs |
| Naval cargo composition | RB §13.1.6, p92 | Withdrawal proof counts at most two units and one non-infantry per transport |
| Constructed rail gauges and damage | RB §13.2.8, p98 | Geography determines broad/narrow, independent of current owner |

## Retained map review

All 31 retained land zones lie in the Asia region drawn on RB p74; the Soviet
region contains no retained territory. Mongolia remains in Asia regardless of
which agent controls its turn. Each retained printed railroad was checked against
white checkered narrow-gauge artwork in the native map. No retained printed rail
crosses a broad/narrow boundary. Dynamic rails into Mongolia use the printed
construction table's broad gauge and therefore can create a new gauge boundary.

The profile fills unknown directional river entries using the shortest path from
the source border to the destination roundel. Existing adopted directional
entries take precedence. River routes remain the explicitly adopted `has_river`
graph; they are not reconstructed from `river_crossing`. In particular, Hunan–
Nanking can carry river supply without a combat river penalty, while an approach
from Kwangtung into Hunan has a combat river penalty. An impassable or cropped
edge is never inferred from geographic proximity.

The full-world map metadata still records broader audit work. This M5 overlay
certifies only the retained closed profile; it does not claim to finish a global
map audit or certify absent naval transit routes.
