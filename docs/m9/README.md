# M9: naval, carrier and amphibious operations

**Status: implemented and source exit verified, 23 October 2026.** RCL-014 now
follows the developer clarification supplied by the user: an evacuating fleet
defends and the enemy fleet already at sea attacks, even during a third nation's
turn. The battle resolves during the existing calendar turn and resumes the
suspended operation afterward. This supersedes the earlier provisional roles.

Naval movement supports explicit fleet selection, real sea routes, supplied and
damaged movement, carrier-aircraft independence, transport loading/unloading,
Japanese destroyer transports, and strategic naval movement with actual capacity,
intermediate pickup and destination restrictions. Peaceful sea entry exposes the
printed declaration window before entry. Submarine/MAP reactions resolve during
movement; screening and raider checks preserve their serialized continuations.
Waiting ships stay in their original port until its blockaded exit is cleared.

Naval combat preserves first strike, air superiority, ordinary return fire,
Target Selection, joint casualty consent/disputes, multi-hit damage, transport
losses, submarine protection/submerging, MAP/Destroyer pairing, raider discovery,
scrambling and retreat. Aircraft from a lost defending carrier immediately get
the printed one-movement landing attempt. Surviving carrier aircraft return
without receiving another normal flight allowance.

Amphibious operations require sea clearance, select eligible shore bombarding
ships, resolve shore/Coastal Artillery first strikes, and then use the shared
land battle. Normal-transport non-infantry waits aboard for a surviving first-wave
foothold; Attack Naval Transports supply their printed exception. Marines and
Amphibious Doctrine retain their double-casualty exemptions. Joint shore casualties
remain decisions of the entitled defending policies.

Port operations include end-of-movement berthing, blockade/assault/strategic
restrictions, immediate damaged-port evacuation, temporary Militia crews,
skeleton-crew locks, and Place Units capture/scuttling with damage retained.
Bombing suspends for evacuation and resumes afterward. The shared Coastal
Artillery counter limits firing to three shots per Player Turn.

The [geography review](naval_geography.md) explains why neither retained narrow
crossing is a mandatory naval passage. Ordinary sea entry is not automatically
shot at across a dotted line. Convoy raiding, interdiction and Kido Butai remain
inactive under the frozen campaign profile.

Current targeted coverage: **21 naval-movement groups, 17 naval-combat groups,
and 27 naval-operations groups**, with shared land-combat and air-integration
checks. The [source exit record](source_exit_2026_10_23.json) records the source
findings, test commands and evidence hashes before the RCL-014 role correction;
its provisional-role statements are historical. The
[checkpoint record](/Users/home/Desktop/gwRL/game_content/scenarios/japan_china_1936/m9/checkpoint_2026_10_22.json)
preserves the earlier 22 October partial checkpoint.

Four durable traces verify complete sequences and exact replay:

- [Clear Japan-to-China voyage and landing](evidence/combined_clear_2026_10_23.json).
- [Contested screening followed by reinforcement and landing](evidence/combined_contested_2026_10_23.json).
- [Failed screening and retreat with linked cargo](evidence/combined_retreat_2026_10_23.json).
- [One combined overland/amphibious battle with an overland-only retreat](evidence/combined_overland_amphibious_2026_10_23.json).

The last trace resolves shore fire before the merged land battle. Separate
ordinary land battles remain available; a same-nation attack on the assault's
target waits for its amphibious preparation. Naval air declarations remain
committed until Combat, and an attack on ships in port does not let those ships
scramble out into that port attack. Full 44-turn campaign certification belongs
to M10.
