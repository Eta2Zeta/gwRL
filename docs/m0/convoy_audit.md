# M0 reference: source convoy routes in the selected seas

Status: **source reference only; convoy play and interdiction are excluded from this campaign by user choice**. This audit checks the six selected sea zones against the original `game_content/maps/gw36map.png`. Diagnostic crops were used for inspection; the original map was not edited. The approved 37-node profile has no active convoy actions, losses or income. Normal MAP and blockades remain active.

Machine-readable source evidence: [convoy_audit.json](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/convoy_audit.json). These routes are not an active M0 dependency.

## Source finding: one printed convoy is geographically local

| Printed convoy | Owner / loss cap | Printed route | Closed-theatre classification |
| --- | --- | --- | --- |
| **Nagasaki Line** | Japan; **5 IPP** | Rehe - P14 - P15 - Kyushu | Geographically local; disabled by campaign choice |
| **Tokyo Line** | Japan; **5 IPP** | Tokyo - P16 - P34 - P33 - P32 - P41 - P50 terminal arc near Singapore | Excluded: P34 and the P50 terminal are outside the theatre |

The Nagasaki line is visibly attached to Rehe at one end and Kyushu at the other. Its Japanese roundel and blue `5` appear in P14. Both endpoint territories and its two sea-zone segments are in the 37-node map. The route is disabled by explicit user choice, rather than by geographic clipping. This source distinction is preserved for a future scenario that enables convoy play.

The Tokyo line's Japanese roundel and blue `5` are in P32. North of Okinawa it passes through the excluded P34 before reaching P16/Tokyo. To the south it continues out of P41 into P50, ending at an arc near Singapore. It does not end at Formosa or Hong Kong. Keeping disconnected retained fragments or connecting them around absent P34 would invent a new convoy, contrary to the closed-map policy.

Coverage of the selected zones is: Nagasaki in **P14/P15**; Tokyo in **P16/P33/P32/P41**. No additional convoy line was observed in these six zones. The nearby U.S. Manila line, labelled 3 IPP, runs outside this set through the P43/P42 area toward the Philippines/P50; it is not the line in P41. The ANZAC East Indies line, labelled 2 IPP, is also outside the selected seas. Their complete global routes were not audited because that is unnecessary to establish the local result.

## Source rule meaning (inactive in this campaign)

Rulebook **1.5, PDF/printed page 10**, defines line ownership by roundel, the number as **maximum potential IPP loss**, and sea endpoints by arcs. A land-ended line closes when either land endpoint becomes enemy-possessed. A closed line cannot be raided.

Rulebook **10.9, pages 71-72**, permits eligible enemy Battlecruisers, submarines and aircraft on Maritime Air Patrol to raid open lines. Successful losses go **to the bank**, not to the attacker. The maximum is shared for each **whole line per Player Turn**, not independently for each sea zone or raider.

Consequently, Nagasaki's `5` is **not an extra 5 IPP of income**, and does not change Japan's audited 15-IPP starting local base income or 15-IPP adjusted treasury. It limits losses from raiding. Two raids split between P14 and P15 must use the same remaining line cap.

## Map data and future scenarios

The canonical world map and general extractor support convoy identity, ownership,
endpoints, routes and loss caps. The current campaign explicitly excludes this
layer; its projected map must not activate Nagasaki merely because all route nodes
are present. Source routes remain in the global map and this audit.

A future scenario that enables convoys should test land-endpoint
closure/reopening, exact full-route retention, shared cap/reset timing, legal
raiders and no phantom income. Those gameplay features are outside the current
campaign; do not create a separate hard-coded Nagasaki battle rule in the MDP.

## Source identity

- Original map SHA-256: `f0e4c34846470eec355db4ccaf6e98d5c0876e9e67abc3eac2cd85a64562f3ba`.
- Global War 1936 v4.3 Rulebook SHA-256: `240d04e5bb9d20928f375ce115836c360ad614fc6215da8b901d7a1806eef11d`.
- The map is the visual source for endpoints, route segments, names, owners and caps; the cited rulebook sections supply the closure and raiding semantics.
