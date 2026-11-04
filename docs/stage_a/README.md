# Stage A: campaign learning records

These records describe the current training pipeline and the rule changes made
for it:

- [Decision, rules and training review](decision_review_2026_10_31.md): the objective rewards a passive Japan; removable decisions, search evaluations and flat targets.
- [Finished battles clear themselves](battle_clearing_2026_10_31.md): 5.2% fewer decisions and 3.8% fewer search evaluations in the same games; truce changes update allies lists at once.
- [Aircraft move once per turn](aircraft_single_move_2026_11_01.md): a plane that flew in Combat Movement no longer flies again in Noncombat Movement; rule verdicts on post-combat landings and repositioning.
- [Combat Movement lists only moves that start a combat](combat_movement_combats_only_2026_11_01.md), for land units and planes: Combat Movement lists about a third of their size; repositioning and split flights happen after the battles; land handed over by an alignment may be entered the same turn.
- [A fixed zone encoding of campaign decisions](zone_encoding_2026_11_02.md): 37 zones answer fixed questions; no look-alike positions or options in 30,259 positions; 49 to 64 times smaller and 5 to 6 times faster to build than the graph input.
- [The network reads the zone encoding](zone_network_2026_11_02.md): the graph input is removed; on the same positions a single forward pass is 7.4 times faster, batched passes 59 times, a training step 43 times, and a stored decision 66 times smaller; the network has 4.6 times more parameters.
- [Bounded AI orders](action_interface_2026_10_24.md): forward-only naval orders and bounded configuration and permission choices, with separate replay compatibility.
- [Where self-play time goes, and the moves each search plays again](search_replays_2026_11_04.md): the coordinator is busy 92% and game threads wait for it 63% of the time; a search's 64 simulations play 75 to 133 moves again on copies of the game, about half of the game threads' own work.

The earlier records (the first pilots, the three-round experiment and the
performance work on the replaced graph input) are summarized in the
[project history](../history.md); commit `037cb60` keeps them.
