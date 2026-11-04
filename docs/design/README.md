# How gwRL learns

This is the central design document of the learning system. It explains, from
the top down, how the program learns to play the 1936–1941 Japan–China
campaign: what the game engine gives the learner, how a move is chosen, what the
networks read and compute, how they are trained, how runs are organised and how
strength is checked. Each layer starts in plain words, then names the code that
does it.

The document is revised whenever a question digs into part of the design (see
`AGENTS.md`). Measurements and the reasons for past changes stay in the dated
[Stage A records](../stage_a/README.md), which this document links to.

Deeper pages:

- [The network's input](network_input.md): how a decision becomes numbers, with
  worked examples.

## Contents

1. [The big picture](#1-the-big-picture)
2. [The game engine: positions, decisions and moves](#2-the-game-engine-positions-decisions-and-moves)
3. [Choosing a move: search](#3-choosing-a-move-search)
4. [What a network reads](#4-what-a-network-reads)
5. [What a network computes](#5-what-a-network-computes)
6. [How the networks learn](#6-how-the-networks-learn)
7. [Running training](#7-running-training)
8. [Measuring strength](#8-measuring-strength)
9. [Known gaps and open questions](#9-known-gaps-and-open-questions)
10. [Glossary](#10-glossary)

## 1. The big picture

Three agents, one per alliance (Axis, Allies and Comintern), learn the campaign
by playing it against each other many thousands of times. Training repeats one
loop:

1. **Play a batch of games.** At every decision, the alliance to move runs a
   search: it imagines possible continuations, guided by its own network, and
   picks a move. The networks do not change during the batch.
2. **Keep some decisions as training samples.** A sample holds the position,
   the moves the search preferred and, once the game is over, how it ended.
3. **Train the three networks** on those samples and recent older ones, so that
   they predict the search's preferences and the final result better.
4. **Save the networks** and play the next batch with them.

```text
  batch of self-play games (networks frozen)
    each decision: search, asking the network many times -> move
    a random share of decisions is kept as samples (5% in the Mac profile)
                    |
                    v  game over: the final scores are attached
  replay buffer of recent samples
                    |
                    v  training steps
  updated networks -> next batch
```

The idea comes from AlphaZero. The search chooses better than the bare network,
the network learns to imitate the search and to predict outcomes, and a better
network makes the next searches better. Whether that works for this game on this
hardware is unproven: no run has yet shown robust playing strength.

## 2. The game engine: positions, decisions and moves

The rules are written in C++ (`src/`, `include/game/`) and reach Python as
`gwrl_cpp.CampaignEnv`, wrapped by `studies/shared/campaign_adapter.py`.

**Nations and alliances.** Each alliance plays for its nations: the Axis for
Japan, the Allies for the KMT, and the Comintern for the CCP and Mongolia. The
eight Chinese warlords start under nobody's control; some rules can later hand
one to an alliance.

**A game is a sequence of positions.** Every position is one of three things:

- **a decision:** one alliance chooses one move from a list of legal moves;
- **a chance event:** the engine rolls dice;
- **the end** of the game, after the eleventh round (1941).

Reactions are decisions too: the defender picks casualties, an attacker chooses
whether to retreat, and so on. A full eleven-round game holds well over a
thousand decisions.

**A legal move is a small record:** a kind plus labelled details. For example:

```text
movement_route   unit = setup_ccp_land_china_shensi_cavalry_1
                 path = [land_china_shensi, land_china_hopeh]
                 combat = true, mode = ordinary
```

Long orders, such as a fleet's, are built one step at a time with bounded
choices: see the [AI order interface](../stage_a/action_interface_2026_10_24.md).

**The final score.** Only the end of the game is scored; there is no reward
along the way. Each alliance's wealth is its income plus a tenth of the value of
its units, its infrastructure, its treasury and its paid construction. Its score
is its own wealth minus the other two alliances' wealth combined
(`src/campaign_objective.cpp`). The three scores form one vector,
`[Axis, Allies, Comintern]`.

**What the learner asks of the engine:** the legal moves, play a move, roll the
dice, is the game over, the final scores, a copy of the game for search, and the
position's planning key, which identifies a position exactly.

## 3. Choosing a move: search

When an alliance must decide, the program does not just ask the network which
move to play. It runs a search (`studies/shared/multiplayer_mcts.py`, class
`VectorMCTS`), made of many simulations: 64 per decision in the Mac profile.

**One simulation** starts from the current position on a copy of the game and
walks forward:

- At a decision, it picks a move by a score that adds two terms:
  - how well the move has done so far in earlier simulations, for the alliance
    that is choosing;
  - how promising the network said the move was (its prior), shrinking as the
    move gets tried more often. The weight of this term is `c_puct` (1.5).
- At a chance event, it rolls the dice.
- It stops at a decision it has not seen before, and asks the deciding alliance's
  network for two things: the position's value for all three alliances, and a
  prior for each legal move.
- It also stops at the end of the game (using the true scores), at a depth limit
  (16 moves in the Mac profile, using the network's value), or when it returns to
  a position already on its path.

The three values found are then added to every position and move on the path.
Each alliance judges moves by its own value: this is Max-N search, not a search
for an equilibrium. Values are rescaled per alliance before they enter the score.

**After all simulations**, the number of times each first move was tried shows the
search's preference. The move actually played is drawn at random in proportion to
these visit counts (temperature 1), and the visit shares become the sample's
policy target (`studies/campaign/learning.py`, `_decide`).

**Exploration.** During training, random noise (Dirichlet, alpha 0.3, mixed in at
25%) is added to the network's priors at the starting position, so the search
sometimes tries moves the network dislikes. Evaluation turns it off.

**A decision with only one legal move** is played at once, with no search and no
network call. It is still recorded as a sample.

## 4. What a network reads

For every position the search asks about, the engine's encoder
(`src/zone_encoding.cpp`) turns the position into one bundle of numbers with three
parts:

1. **The board:** each of the 37 zones (31 land, 6 sea) answers the same 35,407
   zone questions, such as "how many CCP cavalry are here?".
2. **The position as a whole:** 6,621 questions, such as the round, the phase,
   whose turn it is, treasuries and wars.
3. **Each legal move:** 12,114 questions, such as which kind of move it is, which
   unit it moves and which zones it names.

Answers are whole numbers, and only the non-zero ones are stored. Each move is
also linked to the zones it starts from, passes through and acts on, so the
network can read those zones' board answers with the move. Facts that never
change, such as terrain and borders, come with the layout once.

The encoder reads the engine's memory directly; no text is written or parsed.
But the engine identifies everything by name (unit types, marks on units, battle
notes, a move's details), so the encoder translates names into question numbers
through fixed lists. Encoding costs about 0.17 ms per decision, about 4% of a
game process's work.

The details, with worked examples, are in [The network's input](network_input.md).

## 5. What a network computes

Each alliance has its own network: `CampaignPolicyValueNet` in
`studies/campaign/neural.py`. Its size is written width × message layers, such as
64×2 or 256×8. For one position it works in six steps:

1. **One vector per zone.** Every question has its own learned row of numbers, as
   long as the width. For each zone, the network adds up the rows of the questions
   answered there, each weighted by sign(a) × log(1 + |a|) for answer a: an answer
   of 1 counts 0.69, 2 counts 1.10 and 10 counts 2.40, so larger counts matter
   more but not in proportion. It adds a learned row for the zone itself and the
   zone's 39 fixed map facts, such as terrain and production value.
2. **One vector for the position,** built the same way from the position's own
   answers.
3. **Messages along the borders.** In each message layer, every zone sends a
   message along each of the 160 directed borders. The message depends on the
   sender's vector and the border's 22 fixed facts, such as a river or a railway.
   Each zone averages what it receives and updates its vector, and the position
   vector updates from the average zone. After k layers a zone's vector reflects
   zones up to k borders away.
4. **The value:** from the position vector and the mean and maximum over zones,
   three numbers, one per alliance.
5. **A score for each move:** the move's own answers are added up the same way,
   with the network's move rows. The vectors of the zone it starts from and the
   zone it acts on, and the average of its path zones, are joined to that. A small
   layer turns the result, together with the position, into one score.
6. **Probabilities in stages.** The menu's probabilities are built step by step:
   first the move's kind, then what acts, then how it travels, then what it acts
   on, then the exact move. Every listed move gets a probability; none is padded,
   merged or dropped. Which details count as "what acts" and so on comes from the
   roles explained in [The network's input](network_input.md#roles).

**Rows start at zero** (since 3 November 2026). A question that training has never
reached adds nothing, instead of a random row added at full strength. On fixed
data this gave a slightly lower held-out value error (0.0076 against 0.0081) and
the same policy loss: no harm shown, not a strength gain.

**Most of a network is rows:** one per question. A network has 3.60 M parameters
at 64×2 and 18.27 M at 256×8.

Measurements of this network are in the
[zone network record](../stage_a/zone_network_2026_11_02.md).

## 6. How the networks learn

**Samples.** A batch of games is played with all three networks frozen. Of each
game's decisions, a random share is kept: 5% in the Mac profile, because a game's
thousand-odd positions are close to one another. A sample holds the decision's
encoding, the alliance that chose and the search's visit shares.

**Targets.** When the game ends, every sample from it gets the final scores as its
value target, divided by 100 for training. Games cut off before their end are not
used for training in `--complete-episodes` runs.

**Replay.** Samples go into a replay buffer, 8,000 in the Mac profile; the oldest
leave first.

**An update** follows each batch: a fixed number of training steps, 700 in the Mac
profile. Each step draws 32 samples at random and, for each of the three networks:

- **value loss:** the squared error between the network's three values and the
  final scores, on every sample;
- **policy loss:** the cross-entropy between the network's move probabilities and
  the search's visit shares, only on samples where this network's alliance was
  choosing.

Each network takes one Adam step on the sum of the two, and all three step
together (`CampaignLearner.update` in `studies/campaign/learning.py`). The updated
networks are saved as a model export, and the next batch starts.

With the Mac profile's settings, each kept sample is drawn about 13 times before
it leaves the buffer.

## 7. Running training

**Layout.** The Mac profile (`studies/campaign/profiles/mac.json`) runs 8 game
processes of 4 games each. One coordinating process evaluates all their positions
together, on the CPU: for this small network the GPU's cost per call outweighs its
speed. Training uses 11 of the 12 allowed cores and stays within the 30 GB memory
limit. `tools/supervise_campaign_training.py` handles the time budget, restarts and
memory stops. How to start, stop and resume a run is in the
[campaign learning guide](../../studies/campaign/README.md).

**Throughput** is counted as decisions searched per hour, compared at the same
training reuse (each kept sample drawn about 13 times):

| Setup | Network | Decisions per hour |
| --- | --- | ---: |
| 31 October: graph input, network on the GPU | older graph network | about 54,000 |
| 2 November, best: zone input, network on the CPU | 64×2 | about 144,000 |
| Night of 2 November, batches 1–2: batched on the GPU | 256×8 | about 151,000 |

On 2 November the Mac profile played 124 eleven-round games per hour with learning
(64×2, CPU evaluation). The night run's network had about five times the
parameters at no cost in throughput, but it did not make the agents stronger: the
learning, not the speed, is the current limit.

**Failures.** A game that fails costs only that game. Its seed is recorded, and a
rules dead end (a decision with no legal move) saves its position in the run's
`failed-positions/` folder. The random-play fuzzer
(`tools/fuzz_campaign_dead_ends.py`) looks for dead ends and for moves that leave
the game unchanged before long runs.

## 8. Measuring strength

**Held-out evaluation** (`studies/campaign/evaluation.py`) fixes the networks
being tested, turns exploration noise off and plays them against simple scripted
opponents (`balanced` and `cautious`), one side at a time, on seeds that training
never used.

**Repeated-state guard.** Evaluation stops a game after 20 visits to the same full
position and reports it as unfinished, with no final score.

**Evaluation loops, night of 2 November.** In 3 of 26 games the trained networks
repeated one combat-phase move 20 times and were stopped; the untrained networks
never did in 39 games. The move was a patrol plane declaring an attack it had
already declared, which changed nothing: an engine loophole. A search values a
move that changes nothing exactly as the current position, so a network that
preferred the position to the likely battle chose it every time once the noise
was off. The engine stopped offering the duplicate (commit `68ebd15`), and the
fuzzer now flags any move that leaves the game unchanged (`b26511f`). The lesson
is general: search will find and use any move that does nothing, so the engine
must not offer one.

Small samples do not establish strength. The scripted opponents are simple
controls, not expert play.

## 9. Known gaps and open questions

- **31 names missing from the encoder's lists.** They fall into shared "other"
  questions, so the network cannot tell them apart. See
  [names the encoder doesn't know](network_input.md#7-names-the-encoder-doesnt-know).
  The recommended fix keeps the engine's names and checks them against the
  encoder's lists ([why](network_input.md#10-why-the-encoder-translates-names)).
- **Heap corruption.** On the night of 2 November a game process crashed twice
  early in batch 3: the engine freed memory and kept using it. About 4.5 hours of
  replays in builds with memory checks did not reproduce it. Two crashes close
  together and none under changed timing suggest a race between game threads in
  one process, but that is unproven. A ThreadSanitizer run is the suggested next
  step.
- **Learning strength is unmeasured.** Neither the larger network nor the zone
  input has yet made the agents stronger. The
  [decision review](../stage_a/decision_review_2026_10_31.md) found that the
  objective rewards a passive Japan and that search targets are flat on large
  menus.
- **Input pruning left out two rules** it could not prove for the whole game:
  warlords never owning ships or planes, and per-flag unit-class rules.

## 10. Glossary

- **Alliance (player):** Axis, Allies or Comintern; each chooses for its nations.
- **Position (state):** everything about the game at one moment.
- **Decision:** a position where one alliance must choose a move.
- **Legal move (option, action):** one choice the rules allow at a decision.
- **Chance event:** a position where the engine rolls dice.
- **Planning key:** a text that identifies a position exactly.
- **Search (MCTS):** the simulations that pick a move at a decision.
- **Simulation:** one imagined walk forward from the current position.
- **Prior:** the network's probability for a move, before searching.
- **Visit count:** how often the search tried a move.
- **Value:** the network's estimate of the final scores, one per alliance.
- **Question (column):** one numbered input slot with a fixed meaning.
- **Answer:** the whole number a position gives to a question.
- **Family:** a group of questions with one name pattern, such as `units`.
- **Row:** the learned numbers a network keeps for one question.
- **Layout version:** an identifier of the full set of questions and fixed map
  facts; a network refuses inputs of another layout.
- **Sample:** a kept decision with its targets.
- **Replay buffer:** the recent samples that training draws from.
- **Batch:** the games played between two updates.
- **Update:** the training steps after a batch.
- **Model export:** the saved networks after an update.
- **Checkpoint:** a full save of a run, for resuming it.
