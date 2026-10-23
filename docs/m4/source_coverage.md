# M4 political source coverage

The source profile is [gw36_politics_v43.json](/Users/home/Desktop/gwRL/game_content/rules/gw36_politics_v43.json).
It records printed v4.3 rules separately from adopted clarifications and the
frozen closed-campaign contract. This document reports source findings; it does
not certify that every corresponding handler has been implemented or tested.

## Evidence reviewed

Full rulebook pages were read for the terminology, relations, war, surrender,
truce, turn order, diplomacy, combat aftermath, recruitment and Chinese special
rules. The relevant tables and complete pages were also rendered and visually
checked: RB 6, 20, 26-31, 35-36, 38-39, 42-44, 53, 73, 82, 101 and 103-105.
Japan NRS pages 1-4 and KMT/CCP NRS pages 1-3 were read and visually checked,
including objective-row conditions and footnotes. RB pages 5 and 7 supply the
terminology definitions. Printed RB and PDF page numbers coincide.

Original-map crops of China, Mongolia and southeast Asia establish original
roundels and mainland/island geography. The source profile includes hashes of
the PDFs, original map, reviewed map transcription, map crops, identity bridge,
Home Country table, clarification register and approved campaign contract.
Temporary extraction/rendering files are in `tmp/pdfs/m4`; they are not sources
or new campaign decisions.

## Home Country resolution

RB 6 has an explicit table for Japan and KMT/CCP. Its unlisted-nation rule uses
original possessions excluding offshore territories. RB 7 defines original
identity by the printed roundel. Neither current possession nor graph
reachability determines membership.

| Identity | Own retained Home Country |
| --- | --- |
| Japan | Tokyo, Honshu, Hokkaido, Kyushu |
| KMT and CCP | The explicit broad Chinese Home Country table, projected onto the retained map |
| Mongolia | Kobdo, Ulyassutai, Central Mongolia, Kerulen |
| Zhili Clique | Beiping, Hopeh |
| Guangxi Clique | Kwangtung; offshore Hainan excluded |
| Szechwan Clique | Sikang |
| Sinkiang Clique | Sinkiang |
| Mengjiang | Suiyuan |
| Tibet | Tibet |
| Ma Clique | Tsinghai |
| Yunnan Clique | Yunnan |
| Dadao Government | Empty original homeland: it is created during play and has no printed original possessions |

The warlords remain separate political identities. Their special classification
as semi-autonomous Chinese provinces does not grant KMT their original land,
income or assets. Applying the explicit original-identity predicate gives their
own mainland homeland without treating them as ordinary neutral diplomacy
targets. The broad Chinese Home Country used by KMT/CCP is a different entry.

Hainan is therefore Chinese Home Country but not Guangxi's own mainland Home
Country. Mongolia likewise belongs to Chinese Home Country while retaining its
own separate original homeland and nationality. Dadao's Chinese operating
permissions do not give it the KMT/CCP homeland table entry.

The offshore list records retained island geography for the mainland-origin
controlled-minor recruitment rule: Hainan, Formosa, Okinawa, Hokkaido, Honshu,
Kyushu and Tokyo. It must not be applied to subtract islands from Japan's or
KMT/CCP's expressly listed Home Country. The map directly shows Hainan separated
from Kwangtung by sea; its printed narrow crossing does not turn it into mainland.

## Module guide and timing distinctions

| Event | Source-backed behavior | Evidence |
| --- | --- | --- |
| Declaration against a Major Power | Available at permitted event boundaries, including other players' turns; active nation and its Alliance have declaration priority; strategic naval movement is an exception | RB 35, section 5.1 |
| Declaration against a Minor Power | Requires a land-unit combat move against that nation; no free standalone declaration substitutes for it | RB 35 |
| War with a minor | Does not itself make a Major Power non-neutral or activate major-war benefits | RB 26 and 35 |
| Controlled minor | Separate identity; controller moves/defends/recruits it, but cannot declare new wars, collect ordinary income, research or conduct diplomacy for it | RB 26-27 |
| Alignment | Ordinary minors incorporate; CCP/KMT remain separate. Same-Alliance labels alone do not grant shared access or joint attacks | RB 27-28 |
| Foreign attack on China | War applies to China; whole-warlord alignment resolves at the end of attacker Combat, with one adopted table result per faction | RB 30-31; RCL-003 |
| Chinese Truce offer | Both factions decide immediately at the end of foreign attacker's Combat; either evolved faction makes the truce unavailable | RB 42 |
| Voluntary truce break | Optional separation during Combat Movement, break in Combat, remaining mixed stacks fight; no invented prior commitment or retroactive move | RB 42; RCL-007 |
| Evolution | Immediate when possessed land IPP reaches 13; capital choice and one appropriate free factory are the same award as the national objective | RB 101; NRS 1-2; RCL-006 |
| Evolution abilities | CCP recruitment/influence and KMT Low Morale end immediately. Only Decentralized Production survives until the end of that faction's own turn if evolution occurred during it | RB 101; NRS 1 |
| Capture | After resolving each land combat, surviving attacker land units establish possession and update the land-IPP chart; remove fortifications, coastal artillery and construction facilities | RB 73, section 10.10 |
| Allied-major liberation | Immediately return original land to its original same-Alliance Major Power unless it surrendered | RB 73, section 10.10.1 |
| Chinese-land gift | A conquering Major Power can retain nonoriginal Chinese Home Country or give it to a Chinese faction, subject to alignment or the explicit subsequent friendly withdrawal condition | RB 73 |
| Capital loss | Send the losing nation's treasury to the bank; France's first Axis surrender is an explicit separate exception | RB 73, section 10.10.2 |
| Capital relocation | The mandatory relocation list does not include Japan, KMT or CCP; do not invent an automatic replacement capital for them | RB 73, section 10.10.3 |
| Japan surrender | Check Tokyo enemy possession at the end of Japan's own Player Turn | RB 39; Japan NRS 1 |
| KMT surrender | Trigger when KMT possesses no land zones | RB 39; KMT NRS 1 |
| CCP elimination | CCP never surrenders. No surviving units ends the Chinese Civil War; this is distinct from loss of land and from universal campaign termination | RB 38, 101; CCP NRS 1 |
| Controlled-minor recruitment | D12 against non-offshore possessed land count; choose infantry, militia, ship-stage advancement or full facility repair; troop destinations require possession since turn start | RB 82 |
| CCP recruitment | Separate minor-only rule against total possessed land count; infantry or militia only, with Decentralized Production destination constraints | RB 103; CCP NRS 3 |

Political capture notifications must come from resolved movement/combat. They do
not prove that a route, attack, supply path or landing was legal. Likewise, a
political entitlement does not replace a later economy or placement handler.

## National objectives and closed-campaign exclusions

RB 20 makes objective bonuses effective when conditions are met. Recurring
per-turn unit/facility awards use the Place Units Phase. The campaign's approved
wealth objective replaces standard victory-point scoring; it does not silently
remove retained national ability bonuses.

CCP's One China objective has different point and bonus conditions. The point
condition excludes Formosa and Hainan when checking KMT's Chinese Home Country
possessions. The one-time three Cavalry plus two Infantry award requires CCP to
possess land **at KMT surrender**. KMT retaining only Formosa/Hainan is not its
surrender and does not by itself trigger those units. CCP NRS 2 gives no special
placement destination for that award: retain the entitlement and apply the
appropriate ordinary placement rules, rather than inventing a destination.

Japan's Pacific Buffer Zone, Access to Resources and Asia for Asians objectives
require territories outside the closed map. Kido Butai is explicitly disabled.
Mongolia's retained turn and direct Comintern control do not create USSR,
Soviet possession, Soviet abilities, Soviet supply endpoints or research.
RB 4.6 ordinarily incorporates a Minor Power that aligns with a Major Power;
Mongolia is not one of its separate-nation exceptions. Its specific RB 4.7
recipient is USSR. Combining those rules with the campaign's retained Mongolian
identity means that a shared enemy with CCP does not create a new, separate
Mongolia/CCP alignment granting common defense or access.

Ordinary diplomacy requires a Major Power at war with another Major Power, an
eligible neutral nation, supply to that nation's own Home Country, and the
Major Factory capacity in RB 53. Chinese warlords use their special influence
and alignment rules; Mongolia is already a Comintern minor. There are no
ordinary neutral diplomacy targets in this retained campaign. The generic
source rule is retained without adding external nations or inventing targets.

## Explicit alignment outcomes after KMT surrender

RB 104-105, the two national ability rows, and adopted RCL-002 give a natural
12 to KMT without a surrender exception. RB 5.7 prohibits liberation to a
surrendered nation, but does not prohibit alignment. The explicit stay-neutral
exception in RB 4.9 applies to a CCP/Dadao attack, not an influence backfire.
Accordingly, the profile preserves the unconditional backfire: the warlord's
actual remaining land and units align with KMT, and KMT's no-land surrender
condition ceases. This reactivation follows from combining those source clauses;
the sources do not contain an express “revive KMT” sentence. It restores no
previously erased units or cash, invents no replacement capital, and resets no
prior evolution or objective award. It is not recorded as a new user ruling.

The same paragraph distinction applies to foreign-invasion alignment. RB 4.9's
foreign-invasion paragraph and table prescribe automatic or rolled KMT outcomes,
and adopted RCL-003 expressly preserves the automatic KMT result. A KMT result
therefore transfers the whole surviving warlord even if KMT surrendered earlier,
with the same narrowly limited reactivation. The preceding paragraph's explicit
exception remains in force for direct CCP/Dadao attacks: those warlords stay
neutral when KMT has surrendered. Applying that exception to every alignment
would erase outcomes the later source table still prescribes.

## Source limits to preserve

- **One China placement:** the award amount and surrender-time condition are
  explicit; its objective row supplies no special destination. An award record
  and the ordinary placement service can preserve that distinction.
- **No remaining controller after surrender:** RB 38 says a surrendering
  nation's controlled minors transfer to another member of the same Alliance.
  If Japan surrenders while Dadao remains separate, this closed profile has no
  other retained Axis Major Power. The printed rule does not provide a fallback
  controller. On 2026-10-21 the user resolved this boundary: “Keep Dadao separate,
  controlled directly by the Axis agent (recommended)”. Dadao therefore remains
  a separate Axis minor with its land, units, existing wars and recruitment,
  directly controlled by the Axis player; it gains no ordinary income or
  external controller. Its existing Japanese turn slot is retained to preserve
  the approved calendar. This is recorded as a campaign override, not a printed
  rule or a change to frozen M0.

The source profile does not add generic early termination, infer surrender
from zero units, merge Mongolia with CCP, convert printed owner labels into
present control, or modify the frozen M0-M3 artifacts.
