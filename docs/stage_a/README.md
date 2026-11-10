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
- [The search keeps a copy of the game at every tree position](search_copies_2026_11_04.md): identical search results on 151 positions with 59% fewer moves played; a matched Mac-profile batch played 184 games per hour while playing instead of 152, for 0.5 GB more peak memory.
- [The coordinator's column lookups, and a fused replacement](coordinator_lookups_2026_11_04.md): the lookups are 22% to 49% of the network's forward pass; PyTorch's embedding_bag makes the pass 23% to 49% faster with identical outputs; not yet in the code.
- [One real training sample](training_sample_2026_11_05.md): what a sample stores, shown with a decision from a game played after one training batch; a fresh network gives every position the same values, so a run's first batch learns little from the search's shares.
- [Choices that are never better](never_better_choices_2026_11_05.md): unloading every unit before the Place Units Phase is not free, since cargo aboard cannot be carpet-bombed, so cargo may stay aboard and an upgrade may not leave a transport with cargo it cannot carry (RCL-021); rail moves where an ordinary move reaches the same zone (3.0% of options) and the printed price under Improved Construction are left out; moves for another of several identical units (10.2%) and skipping the free recruitment roll remain.
- [Upgrades wait while their unit is at sea](upgrades_at_sea_2026_11_06.md): RB 12.3 needs a Supply Path to the unit's land zone, so a unit aboard a ship at sea is no longer offered an upgrade, while one aboard a ship in port still is (RCL-021); in 241 random games such offers at sea fell from 139 to none.
- [How often the depth limit stops a simulation](depth_limit_2026_11_09.md): in a replayed training game, 18 of 68,800 simulations reached the limit of 16 steps and 9 were cut short; without the limit the deepest went 19 steps and no most-visited move changed; the networks' values for one position differ by 2.5 to 17 points, and 9.3% of simulations end at positions another alliance's network rates.
- [What Adam did in one real update](adam_steps_2026_11_09.md): re-running the 5 November update gave generation 1 exactly; in the first step every number with a gradient above about $10^{-6}$ moved by 0.001; one value-head bias shows how the steps then shrink.

The earlier records (the first pilots, the three-round experiment and the
performance work on the replaced graph input) are summarized in the
[project history](../history.md); commit `037cb60` keeps them.
