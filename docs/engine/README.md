# The rules engine

The engine plays the 1936–1941 Japan–China campaign of the board game Global
War 1936, by the printed rules of version 4.3 and the rulings recorded for this
project. It is a C++ library (`include/game/`, `src/`), and Python reaches it as
`gwrl_cpp.CampaignEnv`.

Three things hold everywhere in it:

- **The engine never chooses for a player.** Every choice the rules give
  someone, down to which unit takes a hit, is offered to the alliance entitled
  to it.
- **The engine rolls every die**, as a step of its own that no player controls.
- **Only offered moves can be played.** A move that is not on the current list
  is refused and changes nothing.

This page explains how the engine is built. [The campaign](scenario.md) says
what a game holds at the start, and [section 7](#7-the-rules-by-subject) lists
the pages on each part of the rules.

## 1. The state of a game

Everything about a game at one moment is its *state* (`State` in
`include/game/campaign.hpp`).

| Part of the state | What it holds | At the start |
| --- | --- | --- |
| Nations | For each nation: who plays it, its status, its treasury, its wars and allies, its technologies | 12 nations |
| Territories | Which nation holds each land zone | 31 land zones |
| Units | For each unit: its type, owner and zone, the movement it has left, its damage, what it carries or is carried by | 99 units |
| Facilities | Factories, ports, shipyards, bases and defences, each with its damage | 22 facilities |
| Railroads | One per border, with the damage on each of its two sides | 17 railroads |
| Construction and repairs | Projects being paid for in stages, and repair jobs | 2 ships under construction |
| Politics | The Chinese Truce, capitals, surrenders, warlords waiting to pick a side | the KMT and the CCP at war |
| Battles | Every declared or running battle, with the stage it has reached | none |
| The clock | The round, the nation whose turn it is and the phase | round 1, the CCP, Production |
| Pending work | Decisions waiting for an answer, and a dice roll waiting to be made | none |

Two things are kept beside the state:

- **The definition** never changes during a game: the map, the catalog of
  pieces, the rules data and the turn order. All copies of a game share one.
- **The history** is a log of every move and roll. No rule reads it; it exists
  for replays and for inspection.

A rule may not keep anything of its own between moves. Whatever matters to a
later decision is in the state, so a copy of the state is a complete copy of the
game.

## 2. The calendar

A game is 11 *rounds* of half a year, from July 1936 to July 1941. In every
round four nations take a *national turn*, always in the same order, and every
national turn has five *phases*.

![One round of the campaign. Four national turns in a fixed order: the CCP and then Mongolia, both played by the Comintern; Japan, played by the Axis; the KMT, played by the Allies. After the KMT's turn the next round begins, and after the KMT's turn of round 11 the game ends and is scored. Every national turn has five phases, in this order. Production: buy, pay for what is being built, repair, research. Combat Movement: move the units that will attack, and declare air and sea attacks. Combat: fight every battle; both sides choose casualties and retreats. Noncombat Movement: move everything else, land aircraft, bring ships into port. Place Units: place what was built, recruit, then collect income. The other alliances also choose during a turn: a defender picks its casualties and retreats and may scramble aircraft. A declaration of war on a major power can come between any two moves.](figures/campaign_round.svg)

| Phase | What the nation whose turn it is does | Pages |
| --- | --- | --- |
| Production | Buys units and facilities, pays the next stage of what it is building, repairs, researches, asks to build a railroad across a border and names a lend-lease gift. | [Economy](economy.md) |
| Combat Movement | Moves the units that will attack: land units into enemy land, aircraft onto their missions, ships into contested seas and toward landings. | [Movement](movement.md), [air](air.md), [naval](naval.md) |
| Combat | Fights every battle it declared, in the order it chooses. Both sides choose casualties and retreats; the dice decide the hits. | [Land combat](land_combat.md), [air](air.md), [naval](naval.md) |
| Noncombat Movement | Moves everything else, lands its aircraft, unloads transports and brings ships into port. | [Movement](movement.md), [air](air.md), [naval](naval.md) |
| Place Units | Puts finished units and facilities on the map and delivers lend-lease. The CCP and minors under an alliance recruit by a roll. The CCP and Japan may try to win over a warlord. | [Economy](economy.md), [politics](politics.md) |

When Place Units ends, the nation collects its income and the next nation's
turn begins. A phase can end only when its required work is done: nothing is
waiting for an answer or a roll, and in Combat every battle has been fought or
called off. The game ends after the KMT's turn of round 11 (`Engine::endPhase`
in `src/campaign_runtime.cpp`).

Which phase each kind of move belongs to was read off 240 random games
([record](../archive/records/move_census_2026_11_14.md)).

## 3. Positions and moves

A *position* is the state at one moment. It is one of three kinds:

- **a decision:** one alliance must choose one move from a list;
- **a chance event:** dice are waiting to be rolled;
- **the end** of the game.

**The list of moves** at a decision comes from one of two places
(`Engine::actionMenu`):

- **Nothing is waiting.** The rules list every move the nation whose turn it is
  may make in this phase. When the phase's required work is done, the list also
  holds `end_phase`.
- **A decision is waiting.** A rule has asked someone a question, such as which
  unit takes a hit. The list holds that question's answers and nothing else.
  The one who answers is often not the alliance whose turn it is.

**A move is a small record:** its kind, the nation it is made for, and labelled
details, such as the unit and its path. The engine's rules can produce 141
kinds of move:

| Family | Kinds | Examples | Page |
| --- | ---: | --- | --- |
| `movement_` | 3 | `movement_route`: a land unit moves along a path | [Movement](movement.md) |
| `land_` | 13 | `land_begin_battle`, `land_take_casualty`, `land_retreat_unit` | [Land combat](land_combat.md) |
| `air_` | 30 | `air_fly`, `air_scramble`, `air_bomb`, `air_land` | [Air](air.md) |
| `naval_` | 62 | `naval_route`, `naval_load`, `naval_declare_assault`, `naval_take_casualty` | [Naval](naval.md) |
| `economy_` | 14 | `economy_purchase`, `economy_place`, `economy_research` | [Economy](economy.md) |
| `politics_`, `truce_`, `influence_`, `recruitment_` | 18 | `politics_declare_war`, `truce_offer`, `influence_roll`, `recruitment_roll` | [Politics](politics.md) |
| `end_phase` | 1 | ends the current phase | this page |

**Long orders are built step by step.** In training the engine uses an order
interface made for agents (`trainingCampaignRules` in
`src/campaign_actions.cpp`, version `campaign-orders-v2`). A fleet's move, for
example, is several decisions: start an order, add ships one at a time, choose
the route. Each step has a bounded list, an order can only go forward, and a
finished battle is cleared away without a move. The same rules decide what is
legal as in the interface for people, where an order can be edited.

## 4. One step of the game

Three calls change a game (`Engine` in `include/game/campaign.hpp`), and each
is all or nothing:

| Call | When | What it does |
| --- | --- | --- |
| `step(move)` | At a decision | Checks that the move is on the list, exactly as offered, then lets the rules apply it |
| `interrupt(move)` | Between moves | Applies a move made out of turn ([section 6](#6-moves-made-out-of-turn)) |
| `resolveChance()` | At a chance event | Rolls the waiting dice and lets the rules apply the result |

After the rules have applied a move or a roll, the engine lets them take any
steps that offer no choice (`settle`), checks the new state for consistency,
and adds the move to the history. If anything fails on the way, the game is
left exactly as it was.

## 5. Dice

A move never rolls dice inside itself. When a rule needs a roll, it posts a
*chance request* in the state: what the roll is for, which dice (six- or
twelve-sided), their modifiers, and which faces are rolled again. The position
is then a chance event. `resolveChance` rolls the dice and hands the faces to
the rule that asked, which carries on from there.

This split is what lets a search copy a game and try the same move with
different dice: the move always leads to the same chance event, and only the
roll differs. The engine keeps separate random streams for the real game and
for search copies, so that a search never uses up the real game's dice.

## 6. Moves made out of turn

Answers to a waiting decision are one way an alliance moves during another's
turn. There are two more, kept in a second list beside the moves
(`legalInterrupts`):

- **A declaration of war on a major power** (`politics_declare_war`) can be
  made at almost any moment, also during another nation's turn. War on a minor
  nation is declared differently: by attacking it during Combat Movement.
- **Leave to use railroads** (`movement_grant_rail`): during Noncombat
  Movement, a nation friendly to the one whose turn it is may let that nation
  move by rail through its land this turn.

The list is empty while a decision is waiting to be answered, and holds no
declaration during a sea battle or a strategic naval move.

The engine does not say who is asked first. The adapter the learner uses
(`studies/shared/campaign_adapter.py`) turns the list into ordinary decisions.
Before each of the active nation's moves, every alliance that has such a move
is offered them, in the order Axis, Allies, Comintern, and may take one or pass
(`pass_interrupt`). A pass holds until the position changes.

## 7. The rules by subject

The rules are six modules, each with its own page. Each module lists its moves,
applies them, and passes everything else to the next module; together they are
one set of rules (`campaignRules` in `src/campaign_audit.cpp`).

| Subject | Page | Code | Rules data |
| --- | --- | --- | --- |
| Wars, warlords, the Chinese Truce, surrender, recruitment | [Politics](politics.md) | `politics.hpp`; `politics.cpp`, `politics_warlords.cpp`, `politics_influence.cpp` | `gw36_politics_v43.json` |
| Land movement, railroads and supply | [Movement](movement.md) | `movement.hpp`; `movement.cpp` | `gw36_movement_v43.json` |
| Ships, transports, landings and ports | [Naval](naval.md) | `naval.hpp`; `naval.cpp`, `naval_movement.cpp`, `naval_combat.cpp`, `naval_operations.cpp` | `gw36_naval_v43.json` |
| Battles on land | [Land combat](land_combat.md) | `land_combat.hpp`; `land_combat.cpp` | `gw36_land_combat_v43.json` |
| Aircraft: flights, landings, bombing, patrols | [Air](air.md) | `air.hpp`; `air.cpp` | `gw36_air_v43.json` |
| Income, purchases, construction, research, lend-lease | [Economy](economy.md) | `economy.hpp`; `economy.cpp`, `economy_lendlease.cpp` | `gw36_economy_v43.json` |

Headers are in `include/game/`, sources in `src/` and rules data in
`game_content/rules/`. The engine's own parts are `campaign.hpp` with
`campaign_state.cpp` (the state), `campaign_runtime.cpp` (moves, dice, phases
and turns) and `campaign_setup.cpp` (loading the scenario).

**Rules data.** Each module reads a profile, a JSON file that lists its rules
with the page of the rulebook each comes from and the rulings adopted for it.
A profile also records the SHA-256 of every file it depends on. The engine
checks these when it loads the scenario and refuses to start if a file has
changed without its recorded hash. What the rules are, and which apply in this
campaign, is in [Rules and data](../rules/README.md).

## 8. Copies, saved games and replays

| Operation | What it gives | Used for |
| --- | --- | --- |
| `clone` | An independent copy of the game | Playing on from a position without touching it |
| `cloneForSearch` | A copy that rolls from the search's own dice stream and is thrown away afterwards | The simulations of a search |
| `serialize`, `restore` | The whole game as text, and back | Saved games |
| `replay` | A saved game plus a list of recorded moves and rolls, played again | Checking that a recorded game is reproducible |
| `planningKey` | A text that identifies the position exactly: the whole state, without the history and the dice streams | Recognising a position reached twice |

Two positions with the same planning key have the same list of moves, so the
engine builds the list once and shares it between copies.

## 9. How the engine is checked

- **After every step** the engine validates the new state's structure
  (`State::validate`).
- **Rule checks across modules** (`campaignInvariantFailures` in
  `src/campaign_audit.cpp`) look for states no legal play can reach, such as a
  war only one side is in. The integration tests run them after every step of
  whole games.
- **Each module has its own test suite** in `tests/`, with small set-up
  positions for each rule: 26 C++ suites in all.
- **Random play** finds what set-up positions miss.
  `tools/fuzz_campaign_dead_ends.py` plays random games looking for positions
  with no legal move and for moves that change nothing.

## 10. What the learner uses

The learner sees the engine through `CampaignEnv`
(`include/game/campaign_env.hpp`, `src/campaign_env.cpp`,
`src/python_bindings.cpp`) and the adapter above it. It asks for the list of
moves, plays one, has the dice rolled, copies the game for a search, and at the
end reads the three scores. [How gwRL learns, section 2](../design/README.md#2-the-game-as-the-learner-sees-it)
describes the game from that side, and
[section 5](../design/README.md#5-how-a-decision-becomes-numbers) how a position
becomes the network's input (`src/zone_encoding.cpp`).
