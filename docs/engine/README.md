# The rules engine

The engine plays the 1936–1941 Japan–China campaign of the board game Global
War 1936, by the printed rules of version 4.3 and the rulings recorded for this
project. It is a C++ library (`include/game/`, `src/`), and Python reaches it as
`gwrl_cpp.CampaignEnv`.

Three things hold everywhere in it:

- **The engine never chooses for a player.** Every decision the rules leave to
  someone, down to which unit takes a hit, is put to the alliance entitled to
  it.
- **The engine rolls every die.** Each roll is a separate event in the game,
  and no player controls it ([section 5](#5-dice)).
- **Only a legal action can be played.** An action that is not on the current
  list of legal actions ([section 3](#3-states-and-actions)) is refused and
  changes nothing.

This page explains how the engine is built. [The campaign](scenario.md) says
what a game holds at the start, and [section 7](#7-the-rules-by-subject) lists
the pages on each part of the rules.

## 1. The state of a game

Everything about a game at one moment is its *state* (`State` in
`include/game/campaign.hpp`): in a board game's words, its position.

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
| The clock | The game round, the nation whose turn it is and the phase | game round 1, the CCP, Production |
| Pending work | Pending decisions: what a rule has asked an alliance to decide, such as which unit takes a hit; and a dice roll waiting to be made | none |

The state holds zones, nations, unit types, facility types, technologies and
the bases of marks as numbers: each one's place in the sorted list of the names
of its kind, the definition's for zones and nations, the catalog's for unit
types, facility types and technologies, and the engine's mark table for marks
(zone 0 is `land_china_beiping`, nation 0 is `ccp`, unit type 0 is
`advanced_artillery`, facility type 0 is `airbase`, mark 0 is
`__campaign_started`). A construction project's type is a unit type or a
facility type number. Units and facilities, which enter and leave a game, are
kept in slot maps that give each a slot of its own and list them in name order.
Everything else, and everything the engine reads or writes, uses names; [names
held as numbers](names.md) explains the numbering and lists the campaign's
tables.

Two things are kept beside the state:

- **The definition** never changes during a game: the map, the catalog of
  pieces, the rules data and the turn order. All copies of a game share one.
- **The history** is a log of every action and every dice roll. No rule reads
  it; it exists for replays and for inspection. A search copy of the game
  ([section 5](#5-dice)) leaves it behind but for its last event, against which
  a move checks that the rules only added to the history, and records the
  events of its own moves (`EventLog::LeftBehind` in
  `include/game/campaign.hpp`).

A rule may not keep anything of its own from one action or dice roll to the
next. Whatever matters to a later decision is in the state, so a copy of the
state is a complete copy of the game.

## 2. The calendar

A game is 11 *game rounds* of half a year, from July 1936 to July 1941. In every
game round four nations take a *national turn*, always in the same order, and
every national turn has five *phases*.

![One game round of the campaign. Four national turns in a fixed order: the CCP and then Mongolia, both played by the Comintern; Japan, played by the Axis; the KMT, played by the Allies. After the KMT's turn the next game round begins, and after the KMT's turn of game round 11 the game ends and is scored. Every national turn has five phases, in this order. Production: buy, pay for what is being built, repair, research. Combat Movement: move the units that will attack, and declare air and sea attacks. Combat: fight every battle; both sides choose casualties and retreats. Noncombat Movement: move everything else, land aircraft, bring ships into port. Place Units: place what was built, recruit, then collect income. The other alliances also choose during a turn: a defender picks its casualties and retreats and may scramble aircraft. A declaration of war on a major power can come between any two actions.](figures/game_round.svg)

| Phase | What the nation whose turn it is does | Pages |
| --- | --- | --- |
| Production | Buys units and facilities, pays the next stage of what it is building, repairs, researches, asks to build a railroad across a border and names a lend-lease gift. | [Economy](economy.md) |
| Combat Movement | Moves the units that will attack: land units into enemy land, aircraft onto their missions, ships into contested seas and toward landings. | [Movement](movement.md), [air](air.md), [naval](naval.md) |
| Combat | Fights every battle it declared, in the order it chooses. Both sides choose casualties and retreats; the dice decide the hits. | [Land combat](land_combat.md), [air](air.md), [naval](naval.md) |
| Noncombat Movement | Moves everything else, lands its aircraft, unloads transports and brings ships into port. | [Movement](movement.md), [air](air.md), [naval](naval.md) |
| Place Units | Puts finished units and facilities on the map and delivers lend-lease. The CCP and minors under an alliance recruit by a roll. The CCP and Japan may try to win over a warlord. | [Economy](economy.md), [politics](politics.md) |

When Place Units ends, the nation collects its income and the next nation's
turn begins. A phase can end only when its required work is done: no decision
is pending, no dice are waiting to be rolled, and in Combat every battle has
been fought or called off. The game ends after the KMT's turn of game round 11
(`Engine::endPhase` in `src/campaign_runtime.cpp`).

Which phase each kind of action belongs to was read off 240 random games
([record](../archive/records/move_census_2026_11_14.md)).

## 3. States and actions

The state at any moment is one of three kinds:

- **a decision:** one alliance must choose one *action* from a list of *legal
  actions*, the actions the rules allow there;
- **a chance event:** dice are waiting to be rolled;
- **the end** of the game, the *terminal state*.

**The list of legal actions** at a decision comes from one of two places
(`Engine::actionMenu`):

- **No decision is pending.** The rules list every action the nation whose
  turn it is may take in this phase. When the phase's required work is done,
  the list also holds `end_phase`.
- **A decision is pending.** A rule has asked an alliance to decide one thing,
  such as which unit takes a hit, and this *pending decision* waits in the
  state ([section 1](#1-the-state-of-a-game)). The list holds only the legal
  actions of the pending decision. The alliance that chooses is often not the
  alliance whose turn it is.

**An action is a small record:** its kind, the nation it is taken for, and
labelled details, such as the unit and its path. The engine's rules can produce
141 kinds of action:

| Family | Kinds | Examples | Page |
| --- | ---: | --- | --- |
| `movement_` | 3 | `movement_route`: a land unit moves along a path | [Movement](movement.md) |
| `land_` | 13 | `land_begin_battle`, `land_take_casualty`, `land_retreat_unit` | [Land combat](land_combat.md) |
| `air_` | 30 | `air_fly`, `air_scramble`, `air_bomb`, `air_land` | [Air](air.md) |
| `naval_` | 62 | `naval_route`, `naval_load`, `naval_declare_assault`, `naval_take_casualty` | [Naval](naval.md) |
| `economy_` | 14 | `economy_purchase`, `economy_place`, `economy_research` | [Economy](economy.md) |
| `politics_`, `truce_`, `influence_`, `recruitment_` | 18 | `politics_declare_war`, `truce_offer`, `influence_roll`, `recruitment_roll` | [Politics](politics.md) |
| `end_phase` | 1 | ends the current phase | this page |

**Long orders are built one part at a time.** In training the engine uses an
order interface made for agents (`trainingCampaignRules` in
`src/campaign_actions.cpp`, version `campaign-orders-v2`). A fleet's move, for
example, takes several decisions: start an order, add ships one at a time,
choose the route. Each of these decisions has a bounded list of legal actions,
an order can only go forward, and a finished battle is cleared away without an
action. The same rules decide what is legal as in the interface for people,
where an order can be edited.

## 4. Applying an action or a dice roll

Three calls change a game (`Engine` in `include/game/campaign.hpp`), and each
is all or nothing:

| Call | When | What it does |
| --- | --- | --- |
| `step(action)` | At a decision | Checks that the action is on the list of legal actions, exactly as listed, then lets the rules apply it |
| `interrupt(action)` | Between two actions | Applies an action taken out of turn ([section 6](#6-actions-taken-out-of-turn)) |
| `resolveChance()` | At a chance event | Rolls the waiting dice and lets the rules apply the result |

After the rules have applied an action or a dice roll, the engine lets them
settle the state (`settle`). Each module brings what it stores about the state
up to date, such as [every nation's income](economy.md#1-money), and the
training interface clears a finished battle, on land or at sea, itself as soon
as the rules offer the action that clears it, exactly as if an alliance had
chosen it ([land combat](land_combat.md#6-finished-battles)). The engine then
checks the new state for consistency and adds the action or the dice roll to
the history. If anything fails on the way, the game is left exactly as it was.
A new game's first state is settled in the same way.

## 5. Dice

An action never rolls dice inside itself. When a rule needs a roll, it posts a
*chance request* in the state: what the roll is for, which dice (six- or
twelve-sided), their modifiers, and which faces are rolled again. The state is
then a chance event. `resolveChance` rolls the dice and hands the faces to the
rule that asked, which carries on from there.

This split is what lets a search copy a game and try the same action with
different dice: the action always leads to the same chance event, and only the
roll differs. The engine keeps separate random streams for the real game and
for search copies, so that a search never uses up the real game's dice.

## 6. Actions taken out of turn

Choosing at a pending decision is one way an alliance acts during another's
turn. There are two more, kept in a second list beside the list of legal
actions (`legalInterrupts`):

- **A declaration of war on a major power** (`politics_declare_war`) can be
  made at almost any moment, also during another nation's turn. War on a minor
  nation is declared differently: by attacking it during Combat Movement.
- **Leave to use railroads** (`movement_grant_rail`): during Noncombat
  Movement, a nation friendly to the one whose turn it is may let that nation
  move by rail through its land this turn.

The second list is empty while a decision is pending and while battles that
must be fought at once are under way: a fight a fleet meets on its route in
Combat Movement, or the battles that breaking the Chinese Truce starts. It
holds no declaration during strategic naval movement either
(`Engine::interruptMenu`, `PoliticsRules::interrupts`).

The engine does not say who is asked first. The adapter the learner uses
(`studies/shared/campaign_adapter.py`) turns the second list into ordinary
decisions. Before each action of the nation whose turn it is, every alliance
with an action in the second list gets a decision of its own, in the order
Axis, Allies, Comintern: take one of its actions there, or decline them all
with the action `pass_interrupt`. An alliance that has declined is not asked
again until the state changes.

## 7. The rules by subject

The rules are six modules, each with its own page. Each module lists its
actions, applies them, and hands everything else on to the next module;
together they are one set of rules (`campaignRules` in
`src/campaign_audit.cpp`).

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
`campaign_state.cpp` (the state), `campaign_runtime.cpp` (actions, dice, phases
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
| `clone` | An independent copy of the game | Playing on from a state without touching it |
| `cloneForSearch` | A copy that rolls from the search's own dice stream and is thrown away afterwards | The simulations of a search |
| `serialize`, `restore` | The whole game as text, and back | Saved games |
| `replay` | A saved game plus a list of recorded actions and dice rolls, played again | Checking that a recorded game is reproducible |
| `planningKey` | A digest that identifies the state exactly: SHA-256 of a compact binary writing of the whole state, without the history and the dice streams | Recognising a state reached twice: the search tree's nodes, the shared lists of legal actions, the recorded history |
| `canonicalKey` | The same state's digest of its canonical text: equal exactly when the planning key is, but two to three times dearer | Comparing states across builds of the engine (`tools/compare_engine_builds.py`) |

Two states with the same planning key have the same list of legal actions, so
the engine builds the list once and shares it between copies. The engine works
out the planning key after every action and every dice roll, for the history
and for that shared list, and the search names its tree's nodes by it. Both
keys come from one walk of the state (`writeState` in
`src/campaign_state.cpp`), which writes either the canonical text, as saved
games hold it, or a binary form without field names and quoting, with zones,
nations and types as their numbers; so the two keys cover the same fields, and
`tests/campaign_env_tests.cpp` checks over a random game that they always pair
up. The binary form depends on the engine's numbering, so the planning key may
change between builds; the canonical key changes only when the saved text
does.

## 9. How the engine is checked

- **Before it applies an action** the engine checks it against the state's
  list of legal actions and refuses an action that is not there (`Engine::step`
  and `allowedBy` in `src/campaign_runtime.cpp`). An action that is itself an
  entry of that list, as the search plays them, is legal as it is; any other,
  such as one from a policy, a replay or Python, must have the exact text of the
  listed action with its identity. A rule module that would check an action
  against its own list of legal actions again skips that check for the action
  the engine has just found (`MenuCheckedAction` in
  `include/game/campaign.hpp`). An action a module builds for itself, such as
  the purchase a railroad consent completes, it still checks.
- **After every action and every dice roll** the engine validates the new
  state's structure (`State::validate`).
- **Rule checks across modules** (`campaignInvariantFailures` in
  `src/campaign_audit.cpp`) look for states no legal play can reach, such as a
  war only one side is in, or a stored income that no longer matches the
  state. The integration tests run them after every action and every dice roll
  of random campaigns four game rounds long, in both interfaces: the one for
  people and the one for agents.
- **Each module has its own test suite** in `tests/`, with small states set up
  by hand for each rule, and one for the name tables and the containers keyed
  by numbers (`tests/names_tests.cpp`): 27 C++ suites in all.
- **Random play** finds what states set up by hand miss.
  `tools/fuzz_campaign_dead_ends.py` plays random games looking for dead ends,
  states where the game has not ended and no legal action exists, and for
  actions that leave the state unchanged.
- **A move that fails in training** after the engine accepted it, such as one
  whose state fails `State::validate`, keeps the position before it and the
  move beside the training run; `tools/replay_failed_move.py` plays it again
  in a fresh process, to tell a defect of the rules from damaged memory
  ([failures in training](../design/README.md#92-running-training-on-the-mac)).
- **A change meant only for speed** must leave play the same.
  `tools/compare_engine_builds.py` plays the same games on two builds and
  compares them: seeded random games at every action, by the legal actions,
  the chosen action and the state reached, and after every dice roll by the
  state reached; and searched games, whose network evaluations are made one
  state at a time, by the actions and dice rolls in order and by the final
  state. It also measures the instructions each build runs.

## 10. What the learner uses

The learner sees the engine through `CampaignEnv`
(`include/game/campaign_env.hpp`, `src/campaign_env.cpp`,
`src/python_bindings.cpp`) and the adapter above it. It asks for the list of
legal actions, applies one, has the dice rolled, copies the game for a search,
and at the end reads the three final scores.
[How gwRL learns, section 2](../design/README.md#2-the-game-as-the-learner-sees-it)
describes the game from that side, and
[section 5](../design/README.md#5-how-a-decision-becomes-numbers) how a
decision becomes the network's input (`src/zone_encoding.cpp`).
