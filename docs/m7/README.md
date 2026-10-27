# M7: authoritative land combat

> Completed milestone reference. Test counts, timings and next steps below describe this delivery. Use the [project guide](../README.md) for current status and instructions.

**Status: land-battle layer implemented; truce combat reconciled and RCL-012
closed on 22 October 2026.**

When CCP or KMT is active, it attacks in shared truce-ending combat regardless
of land possession. Shared truce-ending battles apply the Low Morale exception:
eligible attacking minor KMT Infantry/Cavalry are eliminated on their normal
attack rolls of 10+.
Termination itself consumes no dice. Defending KMT and Major-Power KMT do not
suffer attacking Low Morale.

Retreats use actual land entry origins. Shared battles reconstruct current-turn
approaches from the active units' movement routes; stationary units and stale
off-turn routes create no origin. A serialized land-entry snapshot excludes
aircraft-only approaches and retains valid origins after the entrant is lost.
There is no arbitrary adjacent-friendly escape. Without an eligible land origin,
ordinary ground units keep fighting, including when accompanied by aircraft.
The printed city/tundra limits still force retreat and eliminate ground units
that cannot retreat.

Third-party automatic termination uses the possessor-defends developer ruling
reported by the user on 22 October. The user clarified that attacking minor KMT
has the same 10+ elimination consequence after automatic termination as after
voluntary termination. This shared-zone rule needs no retreat origin. Ordinary
KMT attacks elsewhere retain their origin-specific Low Morale retreat.

The February Discord defender-capture amendment is announced for v4.4; this
v4.3 layer retains attacker-only capture aftermath.

Automatic evolution-triggered shared-zone battles resolve immediately in the
existing phase. The campaign reachability test uses Japan capturing Chinese
land and giving it to a Chinese faction under RB §10.10.1 p73, crossing 13 IPP
during Japan's Combat phase. The former Japanese influence example was invalid:
foreign-invasion alignment removes independent warlord targets before the truce
is offered. The calendar clock stays fixed. Pending decisions belong to the actual
Chinese faction; ordinary purchases, phase changes and discretionary declarations
wait for the mandatory work. Multiple automatic battles use stable pending queue
order so a third-party active player gets no discretionary ordering choice.
That ordering is an explicit implementation convention because these battles
were not declared through Combat Movement and the source supplies no event order.

M7 replaces the prototype's single-call land combat with serialized battle
progress. Each first-strike volley, ordinary attack volley, defensive return
volley, casualty choice, pairing choice, retreat destination, and disputed
joint-defense choice is part of the campaign state and event history.

`registerLandBattle` accepts validated unit IDs and a separate final approach
origin for every unit. Registration includes empty targets, because minor KMT
Infantry and Cavalry must still test Low Morale. It does not roll or capture.
The attacker chooses which declared battle to begin. `registerAttritionBattle`
records a separate stationary advanced-artillery attack. Normal play declares
these attacks during Combat Movement and resolves them in Combat.

The catalog supplies base statistics, classes, modes, and technology gates.
The battle module applies destination and individual approach terrain, the
highest applicable positive and negative modifier, the separate Japanese
national modifiers, artillery pairing, fortification approach restrictions,
cities, and the first-round durations. Ordinary defending casualties retain
return fire. First-strike casualties are removed before ordinary combat.

Casualty selection is an explicit choice. Target Selection belongs to the
firing player; other casualties belong to the casualty side. Joint defenders
consent to a proposal or request the rulebook's highest-die dispute, including
tie rerolls. The implementation contains no casualty ranking policy.

For ordinary entered-territory attacks, retreat destinations are friendly adjacent
land zones represented in the
attacking approach records. Units can retreat to different eligible origins;
normal movement is exhausted. Airborne and amphibious units cannot retreat.
The city three-round and tundra one-round limits force eligible retreats and
eliminate units unable to retreat. KMT's ordinary Low Morale returns each unit
to its own approach origin and removes it from casualty eligibility. The
voluntary shared-zone truce exception instead eliminates that unit on the same
attacking die.

Winning within two rounds can grant armor a blitz continuation. The attacker
explicitly pairs eligible companions, at one ordinary companion or two
advanced mechanized infantry per armor. M5 validates subsequent movement and
requires companions to follow their named armor to the same target.

M8 supplies defensive scrambling and grounding, transporting-aircraft landings
before an airborne infantry attack, and aircraft landing after combat. M7
supplies first-round fighter priority, AAA timing, separate inherent city AA,
linked airborne transport/cargo losses, and carpet-bombing participation. RCL-001
now uses the developer-corrected combined step 4 for both sides’ Fighters and
AAA, followed by surviving transport landing in step 5.

`BattleState.data` holds all continuations, roll descriptions, pending
casualties, pairings, origins and reaction state. Checkpoints, clone planning
keys, observations, and exact replay retain these values. Module objects are
immutable and have no private battle state.

The source ledger is `game_content/rules/gw36_land_combat_v43.json`.
It records 23 rules, three source-file hashes, the separately identified
user ruling and the later role correction with Discord evidence. Border clashes are inactive:
the closed campaign has neither of the rulebook's listed nation-pair borders.
M9 supplies naval battle creation, amphibious unloading and shore bombardment;
M7's amphibious commitments preserve the corresponding retreat and blitz
restrictions. M10 still owns complete campaign adjudication.

The 32 fixture groups in `land_combat_tests` and 15 groups in
`land_truce_tests` pass. They cover both voluntary breakers and land possessors,
single-die KMT losses in successive rounds, defending/Major/militia exemptions,
real and missing entry origins, aircraft-only approaches, lost entrants,
city/tundra limits, automatic shared-zone Low Morale elimination, automatic evolution,
and exact replay. The ground fixtures include exact enumeration of all
144 joint outcomes for a 2/12 attack against a 4/12 defense, owner and firing
player casualty decisions, first strike, normal return fire, KMT empty attacks,
terrain, fortification approaches, attrition, air/AAA/airborne integration,
blitz capacity, joint-defense disputes, and the retained Dadao identity in
Japan's calendar slot. Multi-turn ground movement, capture, collection and
counterattack are replayed through the composed campaign modules.

The original [M7 verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m7/verification.json)
and earlier correction records remain historical snapshots.
The [shared truce Low Morale verification record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m7/shared_truce_morale_2026_10_22.json)
records the corrected behavior and current integrated checks.

The M10 source audit adds Strategic Rocket regressions: Rockets cannot roll or
absorb casualties; surviving Enemy land units destroy unsupported Rockets.
Aircraft-only raids and remote attrition preserve them. The dated M7 records
remain unchanged; the current M10 checkpoint records this correction.
