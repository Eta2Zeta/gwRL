# M0 source reconciliation

Reconciled 21 October 2026 from local sources. This closes the initial Japanese
construction-payment transcription and records exact research-chart values. It
does not implement a construction queue, technology system or combat catalog.

## Evidence and method

- [Rulebook v4.3](</Users/home/Desktop/gwRL/game_content/rules/Global War 1936 v4.3 Rulebook.pdf>): full relevant pages 18, 44-45, 50-51, 67, 79-80, 89-91, 96 and 98-99 were read. The embedded technology chart on page 45 was inspected at its native image resolution; pages 50-51 were also rendered and inspected.
- [Japan NRS v4.3](</Users/home/Desktop/gwRL/game_content/rules/GW36 - NRS - Japan v4.3.pdf>): full build-chart pages 5-8 were read, and the complete image-based setup page 9 was rendered and inspected. Page numbers are one-based PDF pages.
- [Map artwork](/Users/home/Desktop/gwRL/game_content/maps/gw36map.png): the bottom-right build queue was inspected from the original image, crop bounds `(8620, 4510, 9900, 4888)`. Its printed version is v4.0; it supplies the stage layout referenced by the v4.3 rulebook, not an independent replacement for v4.3 prices or setup. The layout agrees with the v4.3 setup labels and construction example.
- [Machine-readable source checks](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m0/catalog_source_checks.json) retain source hashes, queue derivations, research thresholds and the limited capital-ship damage statements checked here.

## Initial Japanese queue payments: resolved

| Ship | July 1936 setup position | Full normal payment schedule | Cumulative already paid | Remaining normal payments | Completed catalog value |
| --- | --- | --- | ---: | --- | ---: |
| Heavy Cruiser | Build queue #2 | 5 / 5 IPP | **5 IPP** | 5 IPP | 10 IPP |
| Fleet Carrier | Build queue #3 | 5 / 5 / 5 IPP | **5 IPP** | 5 IPP, then 5 IPP | 15 IPP |

The derivation uses the queue's actual direction and starting positions:

1. RB section 2.3, page 18 includes ships already in various stages of production
   in the starting setup. Japan NRS page 9 places one Heavy Cruiser in #2 and one
   Fleet Carrier in #3, and explicitly labels #1 as the Place Unit box.
2. The map's queue reads **Stage 3 -> Stage 2 -> Place Units Box**. Fleet Carriers
   are pictured in Stage 3 and Heavy Cruisers in Stage 2, identifying their
   normal starting construction stages. RB section 8.3.2, page 51 independently
   confirms the direction: construction damage pushes a project from stage 2
   *back* to stage 3.
3. RB section 8.3, page 50 says the slash-separated numbers are per-turn costs:
   a Heavy Cruiser at 5/5 costs 10 IPP and takes two Player Turns. Section 7.3,
   page 44 has payment to advance the build queue in Production; section 12.1,
   page 79 places completed units from the Place Units box. Japan NRS page 7
   confirms 5/5 and 5/5/5.
4. Therefore entering the normal starting stage has already paid the first
   installment. Treating the starting stage as unpaid would add a third payment
   or turn to the two-turn Heavy Cruiser and would contradict the stated
   schedule. A queue number is neither the number of paid installments nor an
   additional unpaid stage before the normal schedule begins.

For a normal, undiscounted project with `n` payment stages currently at queue
position `q` (Place Units is position 1), `n - q + 1` installments have been paid.
Both starting ships are at their normal initial paid stage, so each has one
5-IPP installment invested. This is a derived setup amount from the cited stage
and cost rules, not a claim that the NRS separately prints historical payments.

The two setup projects consequently contribute **10 IPP of construction assets**,
or **1.0 to Axis wealth** at the approved 0.1 coefficient. These are opening
assets; do not subtract them again from Japan's 15-IPP opening treasury. Future
payments consume treasury and increase the paid-construction ledger. Completion
replaces that ledger entry with the completed asset's catalog value, counting
the ship once. The user-selected damage deduction still applies where relevant.

At normal payment speed, the Heavy Cruiser can advance #2 -> Place Units in
Japan's July 1936 Production and place that turn if eligible. The Fleet Carrier
can advance #3 -> #2 that turn, then #2 -> Place Units in January 1937 if Japan
makes the payments. These are earliest ordinary completions, not mandatory
purchase decisions or guaranteed placement. Future technology/payment modifiers
must follow their own rules; they do not rewrite the opening paid amounts.

### Placement remains national and conditional

RB section 12.1, page 79 requires a supplied shipyard with available capacity,
possessed since the beginning of the Player Turn. Section 13.2.5, page 96 gives
Minor Shipyards one normal production/repair slot and Major Shipyards five;
both are useless while damaged. Allied shipyard use does not grant production.

- A **Heavy Cruiser is not a Capital Ship** and may be placed at an eligible
  **Minor or Major Shipyard**.
- A **Fleet Carrier is a Capital Ship** and requires an eligible **Major
  Shipyard**.
- A port or dockyard alone is not a ship-production site. No starting tile is
  assigned to either national queue entry. The user-approved theatre policy
  limits the choice to eligible retained shipyards.
- Surface Ships built at Major Shipyards may be placed in port. A failed
  placement caused by a declaration of war changing the Supply Path leaves the
  unit in the Place Units box under section 12.1; do not create a phantom site.

The parenthesized Light Carrier entries are separate USA-war-triggered entries
identified by the footnote on Japan NRS page 9. They remain excluded from this
campaign and are not part of these two paid projects.

## Research-chart transcription: resolved

The chart embedded in RB section 8.2, page 45 has four destination columns:
**Stage I, Stage II, Stage III, Complete**. Each listed threshold is the minimum
successful D12 result for advancing into that column. All four columns use the
same threshold within a technology row.

| Threshold in each column | Technologies |
| --- | --- |
| **7+** | Advanced Mechanized Infantry; Advanced Artillery; Radar; Anti-Submarine Warfare; Improved Factories; Improved Construction; Airborne Doctrine; Amphibious Doctrine |
| **8+** | Heavy Armor; Jet Fighters; Long-range Aircraft; Advanced Submarines; Large Ship Construction; Improved Logistics |
| **9+** | Heavy Strategic Bombers; Strategic Rockets |

The red July 1939 line lies before Stage III. The accompanying text forbids
developing Stage III before July 1939, grants one technology roll per undamaged
possessed Major Factory, permits only one roll for a technology per Calendar
Turn, and makes the technology available immediately on completion. The chart's
USA/USSR objective symbols and income prerequisites are source context; they
create no foreign participant or starting technology in this campaign.

This supplies R045's exact source values. Implementing the research state,
availability checks, effects and tests remains later catalog/economy work.

## Remaining catalog and railroad work belongs to later milestones

**Capital ships:** RB section 13.1.6, pages 90-91 supplies undamaged statistics,
hits to sink and prose damage modifiers. These statements are transcribed in
the companion JSON. RB section 8.6, page 51 confirms zero-IPP Capital Ship
repairs, one repair slot per repaired hit, and the action restriction while
repairing. The naval entries also refer to the battle board for damaged combat
effectiveness. This pass does not certify a complete battle-board matrix,
especially every Heavy Battleship damage state and bombardment interaction.
That is the **M3 complete-unit-catalog gate** and later naval acceptance work.
All retained setup ships start undamaged; no missing damaged-state cell blocks
this M0 initial inventory or its approved monetary valuation.

**Railroads:** RB section 13.2.8, pages 98-99 supplies border construction prices
(2 IPP normal terrain; 4 IPP desert/jungle/marsh/mountain/tundra), maximum damage
(1/2 respectively), and 1 IPP repair per damage point. Terrain follows the
direct roundel-to-roundel route at the border, not either endpoint's intrinsic
terrain alone. The source requires permission when building toward another
nation and excludes non-controlled neutral nations; Japan NRS page 8 also
expressly requires peace with the other nation. RB section 10.6.2, page 67
targets one border of the attacked land zone, affects all tracks on that border,
requires war only with the targeted zone's owner, and illustrates a damage
marker on that owner's side.

The user's one-asset-per-undirected-border valuation and equal endpoint shares
are settled scoring rules. They do not invent joint repair permission or erase
the targeted side of a bombing action. Encoding route-derived rail cost,
targeted-side damage/repair permissions and executable rail fixtures remains
**M3/M5/M6/M8 implementation work**, as already assigned in the milestone plan.
The source checks above identify the relevant clauses; they do not claim those
handlers or tests are implemented.

No additional user choice is required by these transcription items to reconcile
the approved M0 contract. M0 synchronization, data verification and freeze are
reported separately in the main review; full catalog certification is not
claimed here.
