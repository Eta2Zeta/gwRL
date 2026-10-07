# Asia, Siberia, Indian Ocean and Pacific audit

Audit date: 5 October 2026. **Proposal only: this audit did not change the live map JSON or generator.** This regional review covers 154 existing nodes, 36 missing land tiles, 26 missing printed Pacific sea IDs, 310 stored physical adjacency pairs, and 103 grouped findings. The second native-resolution pass completes the physical neighbor review that the initial draft left open.

Sources are the original 9900 × 4888 `game_content/maps/gw36map.png`, `GW1936_Terrain_Glossary_v1.pdf` pp2–4 and11–12, and the v4.3 rulebook. Evidence crops retain original pixels. Existing Japan/China work supplied context, but it was not treated as certification of Siberia, islands or ocean geometry.

The main result is a reconstruction proposal: missing Soviet territories collapse the northern land graph; India has routes through intervening tiles; several Indonesian islands have invented land/rail links; Australia omits Sydney; and missing central Pacific cells isolate Wake from the world. Many printed sea IDs are attached to misleading geographic names.

## Review artifacts and exact scope

- [Findings](../data/asia_pacific_findings.json): 50 additions, 29 changes, 13 deletions and 11 uncertainties. These are grouped findings, not counts of individual edits.
- [Existing-node ledger](../data/asia_pacific_review.json): 154 records with checked fields, evidence and remaining attribute limitations.
- [Stored-pair ledger](../data/asia_pacific_edge_review.json): all 310 unordered stored pairs touching this region's node set: **258 physical contacts confirmed, 50 proposed deletions and 2 source ambiguities**. A confirmed physical pair may still need rail, passability, terrain or facility corrections; it is not a blanket attribute approval. Shared American coasts use coordinated Americas source review.
- [New-land neighbor ledger](../data/asia_pacific_new_node_neighbors.json): complete physical perimeters for all **36 missing land tiles**, including coasts, impassable contact, ordinary borders and the new West Timor crossing.
- [New-edge rail/gauge ledger](../data/asia_pacific_new_edge_rail_review.json): all **64** distinct land/narrow pairs touching the 36 missing land tiles, including all 61 new-Soviet perimeter pairs and the three Sydney/Timor/Sunda pairs. Results: **16 railway crossings, 47 without railway, one ambiguous Saratov–Ural junction**. Yellow/black identifies broad gauge; white/black identifies narrow/normal gauge. The ambiguity is source overlap, not an uninspected border.
- [Sea-neighbor ledger](../data/asia_pacific_sea_neighbors.json): complete ordinary sea-to-sea perimeter sets for **P1–P75 and I6–I14**, with explicit American/Indian seams. P42–P50 remains separate as uncertain. A9–P1 is the restricted Northern Sea Route (§1.13), not an ordinary neighbor.
- [Directional terrain table](../data/asia_pacific_directional_terrain.json): all **173 express directed river/terrain/reef requirements** on glossary pp2–4 and11–12, plus one non-actionable Vyatka typo row. **119** differ from stored values or target absent edges. “Contains mountain” adds an effect; it does not replace intrinsic jungle. Five “with” river statements retain direction uncertainty.

Within-scope reciprocal comparisons pass for new land and sea sets. These are proposal files, so no engine test or production rebuild is claimed.

## Additions

### Soviet land zones

Zuryenia; Ural (1 IPP); Orenburg; Western Kazakhstan; Central Kazakhstan; Turkmenistan; Vyatka; Yugria; Samoyedia; Lower Tunguska; Sibir; Tobolsk; Yenisei; Evenkiland; Western Yakutia; Northern Yakutia; Eastern Yakutia; Chukotka; Big Diomede Island.

AP-001–019 supply identities, terrain and income; the new-land ledger supplies their full physical neighbor sets. This includes narrow finite borders that a coarse crop misses: Orenburg–Sibir, Evenkiland–Northern Yakutia, and Chukotka–Yakutsk. Yugria and Samoyedia have real A9 coastline in the Ob gulf. Evenkiland and Western/Northern Yakutia reach the map frame with no local sea coastline. Turkmenistan, rather than Turkestan, borders Afghanistan; Turkmenistan also touches the broad impassable barrier toward Sinkiang.

### Islands and Sydney

Andaman (I12); Maldive (I7); Bonin (P35); Midway (P22); Hawaii (P29, 2 IPP); Attu and Kiska (P4); Marshall (P47, 1 IPP); Line (P38); Solomon (P54); Gilbert (P56); Samoa (P66); Gambier (P67); Pitcairn and Easter (P68); Maluku (P51/P52/P62); Dutch Lesser Sunda / West Timor (P60/P61/P63, 1 IPP); Sydney (P72, mountain city, 2 IPP).

Sydney is a separate city polygon bordered by NSW and P72, with an airfield and **one** minor shipyard. The northern P72 minor shipyard belongs to NSW. West Timor is a Dutch island group distinct from Portuguese Timor; keep “Lesser Sunda Islands” as the glossary alias. Portuguese Timor has 0 IPP, P63 coastline and an ordinary land border with Dutch West Timor. Remote British islands retain a separate Great Britain/FEC allocation uncertainty rather than using a terrain-table heading as sufficient ownership evidence.

### Sea cells

Missing printed Pacific IDs: P4, P19, P20, P21, P22, P23, P27, P29, P37, P38, P39, P40, P48, P49, P55, P56, P57, P58, P66, P67, P70, P71, P72, P73, P74 and P75. P76–P78 and their seam arrows are covered by Americas, with reciprocal links incorporated here.

Wake/P36 currently forms an isolated two-node component. P36 actually borders P26/P27/P35/P37/P45/P47. The full native-grid trace also confirms short contacts P1–P5, P11–P23, P13–P24, P22–P29, P24–P30, P27–P37, P34–P45, P60–P61 and P62–P64. These cannot be inferred reliably from sequential numbering. I7–I11 and I9–I13 do not exist; I10–I14 does.

## Terrain, income and identity corrections

| Area | Proposed correction |
|---|---|
| Soviet East | Irkutsk, Angara, Yakutsk, Magadan, Kamchatka, Amur, Chita, Buryatia, Primorsky and both Sakhalin tiles are mountain. Stalino, Vanavara and Southern Yakutia are normal. |
| Novosibirsk | Mountain city, **3 IPP**; preserve `is_city=true` for its circular zone. |
| South Sakhalin | Japanese printed identity; real P7 west coast; no printed minor port; ordinary North/South Sakhalin border without rail. |
| Kashmir | FEC printed roundel and glossary category. |
| Japan and Pacific | Kuriles, Volcano Islands, Tasmania, NZ and Philippines have mountain terrain, with directed landing approaches separately represented. |
| Combined terrain | Hainan, Annam-Tonkin, Malaya, Sarawak, Java, Celebes, Portuguese Timor, Dutch New Guinea and New Guinea have mountain **and** jungle effects. |
| Ceylon | Jungle; I11 small north coast and I12 main coast; dockyard in I11. |
| Australia | WA, NT and SA are normal with specific mountain approaches and impassable border portions, not whole-zone desert. |
| Income | Amur/Chita/Buryatia 1 each; Malaya 2; Sarawak 1; NSW 1; NZ South Island 1; New Britain 0; Portuguese Timor 0. |

Delhi retains city status. A city dot, strategic-objective emblem and victory-city designation are separate concepts; the root report reconciles the ten rulebook victory cities.

## Connections and coast corrections

India needs Bengal–Benares/Calcutta/Burma/Nepal, Benares–Nepal/Punjab/Southern India, Delhi–Southern India and Punjab–Maharashtra. Delete Benares–Burma, Calcutta–Burma, Benares–Maharashtra and Kashmir–Nepal: native junction tracing confirms intervening tiles. Kashmir/Nepal/Afghanistan rail flags are unsupported. Southern Iran–Punjab retains an explicit rail-gap uncertainty.

The Soviet graph lacks links into Novosibirsk, Eastern Kazakhstan and Turkestan, plus the complete new northern zone network. Delete Angara–Chita and Buryatia–Primorsky shortcuts. The printed Trans-Siberian railway follows Novosibirsk–Angara–Buryatia–Chita–Amur–Primorsky. Kamchatka touches P1/P2/P3/P9; Amur touches P2; Primorsky Krai has P2/P7 coast.

Delete invented ordinary land/rail links Borneo–Java, Borneo–Celebes, Portuguese Timor–NT, New Guinea–New Britain and NSW–Tasmania. Real narrow crossings require typed land pairs:

| Pair | Capacity | Blocking seas touching the dotted line |
|---|---:|---|
| Southern India–Ceylon | 1 | I11 |
| Amur–North Sakhalin | 1 | P2 |
| Kamchatka–Kuriles | 1 | P9 |
| Malaya–Sumatra | 1 | P50 |
| Sumatra–Java | 1 | I13, P59 |
| Java–Lesser Sunda / West Timor | 1 | P60, P61 |
| Luzon/Visayas–Mindanao | 1 | P42 |
| NZ North–South | 2 | P73 |

Revised coasts include Siam I11/P50; Sumatra I12/I13/P50/P59; Borneo P50/P59/P60; Sarawak P50/P51; Java I13/P59/P60/P61; Celebes P51/P60/P62; Maluku P51/P52/P62; Dutch New Guinea P52/P62; New Guinea P53/P64; New Britain P53. Native review resolves the short Borneo P50, Sarawak P51 and Java P60 segments. Mindanao has P42/P50/P51, with no P52.

Australian coasts are WA P61/P63/P69/P70, NT P63, SA P70, Queensland P63/P64/P71/P72, NSW P70/P72, Sydney P72 and Tasmania P72. NZ and New Caledonia are P73. Both NT–SA and Queensland–SA lie entirely inside the impassable Outback; NT–Queensland has a traversable northern segment. Reef restrictions from P64/P71/P72 prohibit amphibious assault into Queensland, not normal naval movement.

## Naval facilities: fresh review on 6 October 2026

The [naval re-audit ledger](../data/naval_reaudit_asia_pacific.json) supersedes earlier facility interpretations. It covers **88 coastal land entries**, all **55 currently stored physical claims on 48 territories**, every AP facility proposal, and a fresh coast scan. It identifies **54 facilities with confirmed territory/type/access**, plus **one real P50 major port with unresolved Philippine island-group ownership**. Thirteen current minor-port claims have no supporting facility symbol and should be deleted. Equal totals before and after do not mean the records agree: locations, types, access and missing physical instances differ substantially.

The important corrections to the previous audit are:

- **Maharashtra** owns three separate naval facilities: I6 minor port, I6 major port and I7 major dockyard. The earlier Southern India dockyard assignment and Maharashtra I7 major-port assignment were wrong. Southern India has its east-coast I11 minor port.
- **South Australia**, not NSW, owns the P70 major port west of their straight political border. NSW owns the northern P72 minor shipyard; Sydney owns the separate southern P72 minor shipyard.
- **Primorsky Krai**, not Amur, owns the northern minor shipyard on the P2/P7 sea seam. The Amur river is also the political boundary here. Record one yard with both sea accesses, plus the separate Vladivostok P7 major port. Amur's proposed P7 coast is withdrawn.
- **Borneo** has a P60 minor port and a separate P60 seaplane base; neither belongs to Sarawak. **Sumatra** has one P50 minor port, without P59 access. **Java** has a P59 minor dockyard. **New Britain** has a P53 major port.
- **North Island, NZ**, has a P73 major port. **Caroline Islands** retains its real major port but needs explicit P46 access instead of intrinsic-only storage.

Fresh review preserves the adopted distinctions: two separate Honshu P15 major shipyards remain two physical instances; Nanking's single major port retains one shared ID with P14/P32 accesses. Kola has a minor shipyard and a separate major port, both A8. Calcutta has a minor shipyard and a separate major port, both I11. Ceylon's major dockyard accesses I11 only. Midway has a minor port and a submarine base, Hawaii a major dockyard, Marshall a minor port, and Turkmenistan a Caspian minor port.

Remove unsupported naval instances from Western Australia, South Sakhalin, Celebes, Portuguese Timor, Dutch New Guinea, New Guinea, Fiji, New Hebrides, Wake, Tasmania and NZ South Island. Also delete the fabricated Philippine minor ports; retain the Luzon P50 submarine base and the one unassigned P50 major port. The ledger provides evidence even for empty facility lists. Plain anchors, circular-anchor dockyards, crane shipyards, vertical-submarine bases and green seaplane bases were checked separately from airfields and national/objective emblems.

The Philippine major port is recorded once under `unassigned_facilities`, with candidate owners Luzon/Visayas and Mindanao (AP-095). Its P50 access and type are confirmed; its territory is not. The Manila convoy land endpoint retains this uncertainty. The East Asian Line ends at the NSW P72 shipyard above Sydney's city boundary.

Rulebook §13.2.8 derives facility rail access from whole-zone railway coverage and mutable railway state; a separate drawn spur to every facility is not a prerequisite.

## Residual uncertainties and representation decisions

The new-edge rail pass leaves Saratov–Ural direct railway access uncertain because political lines, rivers and tracks overlap at the Volga junction (AP-099). Ural is still known to have zone-wide rail coverage through other confirmed railway borders.

The two unresolved **stored physical pairs** are Kobdo–Novosibirsk's tiny city-arc junction and P42–P50 at the Philippine island-group divide. Source ambiguities also remain for Tannu Tuva affiliation, Philippine major-port ownership, the Vyatka glossary self-reference, some direction-neutral river wording, remote British island allocation, and political contact representation beneath the broad Himalayan barrier.

Railway/gauge transcription for all proposed new-node land and narrow borders is complete, including explicit absence where no track crosses. Sydney–NSW uses the printed narrow/normal gauge; the recorded Soviet track crossings use the printed yellow broad-gauge symbol. Whole-zone coastal rail coverage is derived under §13.2.8. A complete named river transport overlay remains a proposed schema layer: combat river-crossing statements alone do not establish its route continuity or bank-control rules. The physical perimeters and all express glossary approach requirements are complete.

## Finding index

| ID | Category | Finding |
|---|---|---|
| AP-001 | add | Missing Soviet land tile: Zuryenia |
| AP-002 | add | Missing Soviet land tile: Ural |
| AP-003 | add | Missing Soviet land tile: Orenburg |
| AP-004 | add | Missing Soviet land tile: Western Kazakhstan |
| AP-005 | add | Missing Soviet land tile: Central Kazakhstan |
| AP-006 | add | Missing Soviet land tile: Turkmenistan |
| AP-007 | add | Missing Soviet land tile: Vyatka |
| AP-008 | add | Missing Soviet land tile: Yugria |
| AP-009 | add | Missing Soviet land tile: Samoyedia |
| AP-010 | add | Missing Soviet land tile: Lower Tunguska |
| AP-011 | add | Missing Soviet land tile: Sibir |
| AP-012 | add | Missing Soviet land tile: Tobolsk |
| AP-013 | add | Missing Soviet land tile: Yenisei |
| AP-014 | add | Missing Soviet land tile: Evenkiland |
| AP-015 | add | Missing Soviet land tile: Western Yakutia |
| AP-016 | add | Missing Soviet land tile: Northern Yakutia |
| AP-017 | add | Missing Soviet land tile: Eastern Yakutia |
| AP-018 | add | Missing Soviet land tile: Chukotka |
| AP-019 | add | Missing Soviet land tile: Big Diomede Island |
| AP-020 | add | Missing island tile: Andaman Islands |
| AP-021 | add | Missing island tile: Maldive Islands |
| AP-022 | add | Missing island tile: Bonin |
| AP-023 | add | Missing island tile: Midway |
| AP-024 | add | Missing island tile: Hawaii |
| AP-025 | add | Missing island tile: Attu and Kiska |
| AP-026 | add | Missing island tile: Marshall Islands |
| AP-027 | add | Missing island tile: Line Islands |
| AP-028 | add | Missing island tile: Solomon Islands |
| AP-029 | add | Missing island tile: Gilbert Islands |
| AP-030 | add | Missing island tile: Samoa |
| AP-031 | add | Missing island tile: Gambier Islands |
| AP-032 | add | Missing island tile: Pitcairn Island |
| AP-033 | add | Missing island tile: Easter Island |
| AP-034 | add | Missing island tile: Maluku Islands |
| AP-035 | add | Missing island tile: Lesser Sunda Islands / West Timor |
| AP-036 | add | Sydney is a separate land zone, not a city inside New South Wales |
| AP-037 | change | Replace tundra/normal/jungle assignments with printed mountain terrain |
| AP-038 | change | Local mountain/desert graphics do not make these entire land zones mountain/desert/tundra |
| AP-039 | change | Land zones with simultaneous mountain and jungle terrain |
| AP-040 | change | Ceylon is jungle terrain |
| AP-041 | change | South Sakhalin is Japanese territory |
| AP-042 | change | Kashmir uses the FEC roundel |
| AP-043 | change | Novosibirsk is a mountain city worth 3 IPP |
| AP-044 | change | Printed IPP corrections across Soviet East, Malaya and Oceania |
| AP-045 | change | Use the printed Volcano Islands label |
| AP-046 | add | Restore missing Indian/Bengal land borders |
| AP-047 | delete | Remove four nonexistent Indian land shortcuts |
| AP-048 | delete | Remove rail service fabricated in Afghanistan/Kashmir/Nepal |
| AP-049 | uncertain | Southern Iran–Punjab printed rail gap |
| AP-050 | change | Southern India–Ceylon is a capacity-1 narrow crossing without rail |
| AP-051 | change | Correct Indian coastal sea IDs |
| AP-052 | change | Indian printed facilities need physical-instance records |
| AP-053 | add | Missing Burma–Annam-Tonkin / Siam–Annam-Tonkin borders |
| AP-054 | add | Restore central Siberian links into isolated endpoints |
| AP-055 | delete | Remove invented rail network north of the Trans-Siberian route |
| AP-056 | delete | Remove long-distance Soviet adjacency shortcuts |
| AP-057 | add | Amur coastal access and mainland–North Sakhalin narrow crossing |
| AP-058 | add | South Sakhalin western coast touches P7 |
| AP-059 | delete | South Sakhalin has no printed minor port |
| AP-060 | change | Primorsky Krai major port and separate northern minor shipyard |
| AP-061 | add | Kamchatka–Kurile capacity-1 narrow crossing |
| AP-062 | delete | Remove fabricated inter-island land/rail links |
| AP-063 | change | Actual narrow island pairs require capacity, sea blockers and no rail |
| AP-064 | add | Missing narrow land pairs at Malacca and Lesser Sunda chain |
| AP-065 | change | Timor node conflates Portuguese Timor and Dutch West Timor |
| AP-066 | change | Philippine coasts and facilities need reassignment |
| AP-067 | change | Correct Borneo and eastern Indies coast IDs |
| AP-068 | change | Indonesian/Papuan facilities are not generic minor ports |
| AP-069 | change | Australian coastal sea IDs and facilities |
| AP-070 | change | Outback blocks the whole Northern Territory–South Australia border |
| AP-071 | add | Northern Territory–Queensland ordinary border |
| AP-072 | delete | Clear invented Australian/Papuan rail connections |
| AP-073 | change | New Zealand and New Caledonia are in P73 |
| AP-074 | delete | Remove unsupported Pacific island ports |
| AP-075 | add | Missing printed Pacific island infrastructure |
| AP-076 | change | Replace I6–I14 Indian Ocean sea-neighbor sets from native perimeter trace |
| AP-077 | delete | Remove I6 long-range adjacency to Western Australia/Ceylon |
| AP-078 | change | Persian Gulf coastal endpoints belong to I6, not I7 |
| AP-079 | add | Missing numbered Pacific sea zones |
| AP-080 | change | Replace P1–P75 Pacific sea-neighbor sets from native perimeter trace |
| AP-081 | delete | Remove seven confirmed Pacific sea shortcuts |
| AP-082 | change | Replace misleading sea-zone descriptions with printed IDs |
| AP-083 | uncertain | South China/India/Himalayan impassable boundary treatment |
| AP-084 | uncertain | Kobdo–Novosibirsk tiny border and Tannu Tuva state identity |
| AP-085 | uncertain | Glossary/map ambiguity: Vyatka self-reference and omitted Yugria |
| AP-086 | uncertain | Represent river transport separately from combat river crossings |
| AP-087 | add | Reconnect Wake/P36 to the six visible surrounding seas |
| AP-088 | add | Restore P18/P19/P20/P21/P26/P27 Pacific grid boundaries |
| AP-089 | change | Apply source-enumerated directional river and mountain/desert approaches |
| AP-090 | add | Kamchatka and P3 are missing real Bering coasts and sea borders |
| AP-091 | change | Kola coast IDs and printed naval facilities |
| AP-092 | uncertain | Unlabeled USA roundel inside P27 has no identified land outline |
| AP-093 | uncertain | Manchurian printed original identity is different from Japan control |
| AP-094 | uncertain | Remote British Pacific ownership allocation requires explicit reconciliation |
| AP-095 | uncertain | Philippine major-port owner and Manila convoy endpoint land node |
| AP-096 | change | Queensland–South Australia shared border is entirely inside the Outback |
| AP-097 | add | Restore Siam west coast and complete Sumatra coastal perimeter |
| AP-098 | uncertain | P42–P50 open-water contact at the Philippine island-group divide |
| AP-099 | uncertain | Direct Saratov–Ural railway connection at the dense Volga junction |
| AP-100 | delete | Remove nonexistent naval facilities from Celebes, Portuguese Timor and both New Guinea territories |
| AP-101 | delete | Delete Western Australia’s unsupported minor port |
| AP-102 | change | Give the existing Caroline Islands major port explicit P46 access |
| AP-103 | delete | Delete fabricated Philippine minor-port instances |
