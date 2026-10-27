# M0: Chinese and minor-faction setup audit

Status: **M0 specification verified and frozen on 21 October 2026**; not a playable full-rules game state. Scope is July 1936 on the approved 37-node closed theatre (31 land, 6 sea), with Tannu Tuva and Hong Kong excluded. FEC and USSR are not participants. No engine changes are made by this audit.

**21 October 2026 synchronization:** the [M0 review](/Users/home/Desktop/gwRL/docs/m0/README.md)
records the approved campaign scope and scoring decisions. The
[shared rule register](/Users/home/Desktop/gwRL/game_content/rules/clarifications.md)
is canonical for RCL-002 influence, RCL-003 whole-warlord alignment and RCL-004
CCP railroad access. RCL-003 is an adopted user decision. RCL-004 is closed:
on 17 October 2026 the user reported that the developers fixed the wording for
the next version. No publication or version number has been independently checked.
The existing railroad mechanic remains intact. Excluded FEC evidence is retained
below as source provenance only.

The machine-readable counterpart is [china_minor_setup.json](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/china_minor_setup.json). It includes canonical node IDs, ownership/control separately, row-level provenance, source SHA-256 hashes, explicit empty setup rows and cross-check totals. Japanese forces are audited separately.

## Sources and method

The setup tables are embedded images, so text extraction alone misses the KMT, CCP and FEC inventories. All relevant setup tables were rendered and read visually, including column headings and total rows. The first three KMT and CCP national-rules pages, FEC overview, and rulebook pp. 18, 29-30 and 82 were also rendered and inspected; applicable remaining rules and build charts were checked against extracted text. PDF page numbers below are one-based. National reference sheets and the neutral setup chart have no printed page numbers; rulebook PDF page numbers equal printed page numbers.

| Key | Source | Relevant pages |
| --- | --- | --- |
| KMT | [KMT NRS v4.3](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - KMT v4.3.pdf>) | PDF 1-3: nation rules; 4-7: major-power build prices; 7: KMT and warlord setup |
| CCP | [CCP NRS v4.3](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - CCP v4.3.pdf>) | PDF 1-3: nation rules; 4-7: major-power build prices; 7: setup |
| FEC | [FEC NRS v4.3](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - FEC v4.3.pdf>) | PDF 1: income and Commonwealth status; 2: militia/colonial prices; 6: setup |
| Japan | [Japan NRS v4.3](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - Japan v4.3.pdf>) | PDF 9: black land vs blue sea aircraft-count cross-check |
| USSR | [USSR NRS v4.3.1](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - USSR v4.3.1.pdf>) | PDF 1-2: Mongolia control, Soviet income restrictions |
| Neutral | [Neutrals setup v4.3](</Users/home/Desktop/gwRL/game_content/rules/Global War 1936 v4.3 Neutrals setup chart.pdf>) | PDF 1: Mongolia rows |
| RB | [Rulebook v4.3](</Users/home/Desktop/gwRL/game_content/rules/Global War 1936 v4.3 Rulebook.pdf>) | Printed/PDF pages and sections cited below |
| Map | [Audited global map](/Users/home/Desktop/gwRL/game_content/maps/gw36_manual_map.json) | Existing printed-facility and territorial IPP data; not newly re-audited here |

Exact source hashes are in the JSON `sources` object. Source rules are evidence, not instructions to expand this closed theatre or implement future milestones.

## Official retained units

Abbreviations: M = Militia, I = regular Infantry, Mt = Mountain Infantry, C = Cavalry. Every named row below maps to the canonical node ID in the JSON.

| Owner | Included location | Starting pieces | Source row |
| --- | --- | --- | --- |
| KMT | Szechwan | 1 M, 1 I | KMT PDF 7, Szechwan |
| KMT | Shantung | 2 I | KMT PDF 7, Shantung |
| KMT | Kweichow | 2 M | KMT PDF 7, Kweichow |
| KMT | Hunan | 2 I | KMT PDF 7, Hunan |
| KMT | Nanking | 4 I | KMT PDF 7, Nanking |
| CCP | Shensi | 2 M, 2 Mt, 1 C | CCP PDF 7, Shensi |
| Sinkiang warlord | Sinkiang | 2 I | KMT PDF 7, Sinkiang |
| Tsinghai warlord | Tsinghai | 2 M, 1 I, 1 C | KMT PDF 7, Tsinghai |
| Tibet warlord | Tibet | 1 Mt, 1 C | KMT PDF 7, Tibet |
| Suiyuan warlord | Suiyuan | 2 M, 2 I, 1 C | KMT PDF 7, Suiyuan |
| Beiping/Hopeh warlord | Beiping | 3 I | KMT PDF 7, Beiping |
| Beiping/Hopeh warlord | Hopeh | 1 M | KMT PDF 7, Hopeh |
| Sikang warlord | Sikang | 1 M, 2 I | KMT PDF 7, Sikang |
| Yunnan warlord | Yunnan | 4 M, 2 I | KMT PDF 7, Yunnan |
| Kwangtung/Hainan warlord | Kwangtung | 4 M, 2 I | KMT PDF 7, Kwangtung |
| Kwangtung/Hainan warlord | Hainan | None listed | Complete KMT PDF 7 setup; ownership RB 4.9, p. 30 |
| Mongolia | Central Mongolia | 1 C | Neutral PDF 1, Central Mongolia |
| Mongolia | Kerulen | 1 M | Neutral PDF 1, Kerulen |
| Mongolia | Kobdo, Ulyassutai | None listed | Complete Mongolia rows, Neutral PDF 1 |

Cross-checks:

- KMT = 3 M + 9 I = **12 pieces**, matching its printed column totals.
- Warlords = 14 M + 14 I + 1 Mt + 3 C = **32 pieces**, matching all four printed column totals. There are **eight factions**, not nine: Beiping and Hopeh share one faction; Kwangtung and empty Hainan share another.
- CCP = **5**, Mongolia = **2**.
- Total retained in this audit = **51 pieces**: 20 M, 23 I, 3 Mt, 5 C. Together with Japan's 48, the campaign has **99 deployed pieces**.
- No additional setup facility markers or construction queues are listed for these retained forces. This does not remove facilities already printed on the map.

## Static facilities and valuation

The setup overlay references these five existing physical facilities, rather than adding copies. Together with Japan's 14, the campaign retains **19 static facilities**, plus Japan's three additional setup factories.

| Land zone | Retained physical facility | Access |
| --- | --- | --- |
| Beiping | Minor Port | P14 |
| Shantung | Major Port; Minor Dockyard | P14 |
| Nanking | Major Port, one shared physical ID | P14 and P32 |
| Kwangtung | Major Port | P41 |

Retained rail-border infrastructure comes directly from the map; no second railroad inventory is inferred from artwork or the setup charts. Each undirected border counts once for scoring, with 50% of its value credited to each endpoint possessor. Same-alliance endpoints aggregate to full value; an uncontrolled minor's share counts toward nobody. This scoring allocation does not change railway access or control.

Every retained unit type in this audit has a catalog purchase price even if its minor faction cannot currently buy it. CCP's starting Mountain Infantry is valued at its 4-IPP catalog price. Ports and dockyards also have listed prices. City labels have no additional asset price; their income and distinct facilities still count.

## Excluded FEC source evidence

The original FEC PDF 6 Hong Kong/P41 row contains one Infantry on Hong Kong and
one Fighter, one Coastal Submarine and one Light Carrier in P41. The aircraft's
blue count identifies it as carrier-based; the Infantry count is black. This
land/sea convention is corroborated by Japan's Formosa/P32 and P15 rows. All four
FEC pieces are excluded even though P41 remains in the map. Hong Kong's Airbase
and Major Dockyard are also excluded. No FEC cash, turn, production or diplomatic
state is created. These source rows preserve provenance, not active setup.

## Initial politics, alliance wealth and local money

KMT and CCP are respectively Allies and Comintern members (RB 4.3, p. 26), but start as independent minor powers, do not align with anybody before evolution, and are already fighting their civil war. Their national ledgers remain separate. Japan does not begin at war with China merely because this campaign is called the China war.

The eight warlords start unaligned and uncontrolled. RB 4.9 describes them as part of KMT *to outside nations*, but expressly says they are not Originally KMT. That wording is not permission to assign their land, units, production or wealth to KMT at setup. Under the user's wealth policy, their assets initially belong to no alliance; a later rule-defined alignment/control changes attribution.

The source setup has Mongolia USSR-controlled (RB 4.7, p. 29; USSR PDF 1). The adopted campaign instead keeps **Mongolia distinct and directly controlled by Comintern**, with no USSR participant or account. Its movement and recruitment occur in the normal USSR turn position, as if USSR were present: **CCP -> Mongolia (USSR slot) -> Japan -> KMT**. This timing does not create Soviet possessions or unlock Soviet abilities. Mongolia's two starting pieces count toward Comintern wealth, and its four included mainland territories initially give a recruitment threshold of 4 on D12. Controlled minor powers collect no IPP income (RB 4.5, p. 27; 12.7 and 12.9, p. 82), so Mongolia's 2 printed territorial IPP must not become 2 IPP of starting cash or Soviet income.

RB 2.4, p. 18 grants each nation starting IPPs equal to its published starting income. The theatre-adjusted cash convention selected for this campaign caps that official grant at the printed IPP of retained **directly possessed** territory; controlled minors are not added. This is an explicit scenario convention, not an alleged official local-game rule.

| Ledger | Official cash / starting rate | Retained directly possessed printed IPP | Local starting cash |
| --- | --- | --- | --- |
| KMT | 6 | 6 | 6 |
| CCP | 2 | 2 | 2 |
| Mongolia | No IPP collection | 2, but controlled | 0 |
| Each unaligned warlord | No independently spendable setup treasury | Not credited to an alliance | 0 |

KMT and CCP retain all their starting land, so cropping does not change their 6 and 2 IPP starting rates. FEC and USSR have no campaign accounts. Mongolia's direct Comintern control credits its assets without creating minor income collection.

## National-rule acceptance checklist

This is a specification checklist, not a claim that the tests or mechanics already exist.

| Rule / source | Timing and decision owner | Required behavioral test |
| --- | --- | --- |
| KMT/CCP movement boundary, NRS PDF 1; RB 14.3.1 p. 101 | Each faction while a minor | Can move only within Chinese Home Country and its adjacent seas, then additionally obey the 37-node closed map; Korea is not Chinese Home Country merely because retained. |
| KMT declarations, KMT PDF 2 | KMT combat movement | Cannot attack other Allies; warlords/Mongolia require prior CCP elimination; generic war condition does not erase these exceptions. |
| CCP declarations, CCP PDF 2 | CCP combat movement | Cannot attack other Comintern; may attack warlords; other-nation condition requires evolution or their presence/possession in Chinese Home Country. |
| Warlord alignment, RB 4.9 pp. 30-31; adopted RCL-003 | End of attacker's Combat Phase | CCP/Dadao attack aligns the attacked warlord's remaining territory/units with KMT unless KMT surrendered; eligible later KMT attack can revive CCP. Foreign-invasion alignment evaluates the relevant neighbors across each warlord's territories, applies the alignment table once per whole warlord, and transfers the whole faction together. |
| Chinese truce, RB 6.6 p. 42 | Both KMT and CCP at end of foreign attacker's Combat Phase | Both must consent; joint defense/movement does not merge possessions; either can break it and evolution terminates it; resolve mixed stacks and KMT low morale correctly. |
| Decentralized production, KMT/CCP PDF 3 | Purchasing/placement by owning Chinese faction | Eligible infantry-class/cavalry placement in possessed Chinese Home Country held since turn start; newly captured land is not immediately a placement point. |
| KMT low morale, KMT PDF 3 | Every relevant attacking infantry/cavalry roll | Natural roll 10-12 returns regular Infantry/Cavalry to its own origin even against an empty zone; retreating pieces cannot absorb losses; Mountain Infantry is not regular Infantry; disabled after evolution. |
| CCP recruitment, CCP PDF 3 | CCP Place Units Phase | One roll, initially succeeds on 1; choice of one Infantry or two Militia; recruitment is not IPP income; ends on evolution. |
| CCP spreading influence, CCP PDF 3; RB 15.2 pp. 103-104 | CCP Place Units Phase | One eligible target faction; buy roll modifiers before rolling, capped by original influence threshold; natural 12 still backfires to KMT; all remaining faction land and units transfer. |
| Evolution, KMT/CCP PDF 1; RB 14.3.1 p. 101 | On reaching at least 13 possessed land IPP | Capital selection and exactly one free factory of city-appropriate size; flag once-only asset award; change national abilities without removing the current-turn decentralized-placement exception. |
| Mongolia campaign control/timing; RB 4.7 p. 29 source context | Mongolia uses normal USSR turn position, after CCP and before Japan | Direct Comintern control preserves Mongolian identity; movement follows normal phases; no Soviet participant, account, possession or ability is created. Peacetime minor control does not permit declaring new wars. |
| Controlled-minor recruitment, RB 12.7 p. 82 | Place Units in Mongolia's USSR-slot turn | Mongolia starts threshold 4, not 2 or a count including excluded Tannu Tuva; choose troops, one ship stage, or full facility repair only if a legal target exists; recruitment is not automatic cash. |
| Setup vs purchase restrictions, RB 2.3 p. 18; NRS setup rows | Initialization only | Do not reject starting Kweichow's two militia or CCP's mountain infantry because a contemporary purchase rule would prevent creating that exact stack/type. |
| CCP civil-war end vs surrender, CCP PDF 1; RB 14.3 p. 101 and 4.9 p. 30 | Unit elimination / later warlord attack | Civil war ends when one faction has no surviving units; CCP never surrenders and can be revived. Do not irreversibly delete the Comintern learner. |
| Material strategic awards, KMT/CCP PDF 2 | Rule-defined achievement/placement | Count free evolution factories and CCP One China reward pieces as assets if awarded; victory-point reward replacement does not silently remove material rule rewards. |

## Closed-theatre consequences and resolved interpretations

- **Burma/Ledo Road:** Burma and Bengal are excluded; conditions cannot be met by treating missing territory as Allied-owned. The KMT minor's road-based artillery/AA purchase unlock and +2 Burma Road bonus are unavailable. It can still reach the broader build chart through in-map major-power evolution (KMT PDF 1-3; RB 1.12 p. 17).
- **CCP +2 income bonus:** requires a rail connection to Soviet-possessed **Home Country** held since turn start. No Soviet Home Country is included, so this bonus is unavailable in this closed geography (CCP PDF 2).
- **Comintern Brothers is different:** the closed RCL-004 retains the requirement for an undamaged railroad from CCP-possessed land to Soviet-possessed land during Production, with qualifying purchases placed in connected CCP-possessed territory. It requires Soviet possession, rather than Soviet Home Country, but remains inactive throughout this USSR-excluded campaign. Mongolia's identity and USSR-slot timing do not provide Soviet possession (CCP PDF 3; RB 15.2 p. 103).
- **FEC/Hong Kong are excluded.** FEC production, colonial placement, Commonwealth timing and reactions are inactive in this campaign. No outside supply, treasury or forces are created from the source-only FEC rows.
- **Closed railroad clarification (RCL-004):** use the specific Comintern Brothers undamaged-railroad requirement during Production, including its placement restriction. Generic river or sea supply does not substitute for that railroad. The user reported the developers' next-version wording fix on 17 October 2026.
- **Adopted whole-warlord alignment (RCL-003):** each warlord receives one alignment result for all its territories and units. Evaluate relevant neighboring factions across that warlord's territories and apply the existing alignment table once. Beiping/Hopeh and Kwangtung/Hainan each remain one faction for this procedure.
- **Influence adjacency and payments:** preserve the rule-defined Influencing Zone and passability requirements, not just a count of every geometric neighbor. A natural 12 backfires regardless of paid modifiers (CCP PDF 3; Japan's analogous rule is in the separate national audit).
- **Setup-only Japanese values:** Torpedo Boat Destroyer 5 IPP and Coastal Submarine 4 IPP are approved scoring values; neither becomes purchasable.

M0 leaves these artifacts as auditable data and test obligations. It does not simulate production, make game decisions, train agents or alter the existing small scenario's mechanics.
