# M6 source coverage

Sources are local official PDFs, the frozen M0 contract, and the separately identified 2026-10-22 user ruling. The runtime economy profile records source hashes and page references. Relevant tables were reviewed as complete rendered pages, rather than inferred solely from extraction.

| Source | Pages / sections | Implemented responsibility |
| --- | --- | --- |
| Rulebook | p. 45, §8.2 | Research capacity, explicit factory choice, once-per-technology calendar limit, stage III date gate, immediate completion |
| Rulebook | pp. 46–50, §8.2.1 | Catalog technology effects, automatic Airborne conversion, construction alternatives, immediate capacity effects, relocated factory restrictions |
| Rulebook | pp. 50–51, §§8.3–8.6 | National purchase rows, staged queues, facility sites and setbacks, upgrades, paid repairs, capital-ship repair slots and action restriction |
| Rulebook | pp. 52–53, §8.7 | Local lend-lease permissions, recipient declaration, one item per recipient, unit/base/repair/militia credits, general technology-unit restriction |
| Rulebook | pp. 66–67, §10.6.2 | Permanent city IPP loss; unrecoverable destroyed cities; selected-side railroad damage and repair interface |
| Rulebook | pp. 79–80, §§12.1–12.4 | Supplied placement, turn-start possession, capacity snapshots, militia limits, suitable replacement targets, lend-lease route and receiver-next-phase placement |
| Rulebook | p. 82, §§12.7–12.9 | Recruitment remains M4, separate from income; controlled minors do not receive ordinary IPP |
| Rulebook | pp. 92–99, §13.2 | Facility types and locations, city naval limits, factory capture/recovery, repair and production slots, served coasts, foreign railroad consent, route terrain prices |
| Japan national sheet | p. 2 | Six China-control bonuses available even without Major-Power war; absent-country income/events inactive |
| Japan national sheet | p. 4 / rulebook p. 105 | Special Japan-to-controlled-Dadao lend-lease permission |
| CCP and KMT national sheets | p. 3 | Decentralized production; distinct inactive Soviet/Burma purchase prerequisites |
| Frozen M0 contract | Wealth policy | Cumulative already-paid construction remains separate from completed assets; no duplicate queue/completed value |
| User ruling, 2026-10-22 | RCL-010 | Dadao-possessed Chinese Home Country is eligible for Japan-to-Dadao delivery and recipient lend-lease placement, without redefining general homeland |

Construction setback prose and examples were reconciled using the explicit examples on rulebook p. 51. The Elite Airborne lending note on p. 47 is an explicit exception to the generic prohibition on p. 52. Both are recorded as source interpretations, not as developer replies or new user choices.

## Module boundaries

M5 owns movement, supply and blockade proofs, including the dedicated recipient-facility exception for lend-lease. M4 owns the political transfer, evolution, recruitment, warlord and surrender events. M6 evaluates current accounting independently of income collection and supplies the actual collection handler. M7/M8 call the construction/city/facility damage interfaces and carry battle/aircraft decisions. Capital-ship repair accounting is included here; ordinary naval action/port movement and full naval combat remain in M9. No off-map actor, convoy, escort, raiding or interdiction mechanic is introduced.
