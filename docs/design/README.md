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
`VectorMCTS`), made of many simulations: 64 per decision in current runs.

**Every simulation starts from the same place: the current position.** It plays
on its own copy of the game, so the real game does not change. It does not play
to the end of the game: it walks forward only until it reaches a position that no
earlier simulation has asked the network about, asks about that one, and stops.
So the first simulations look one move ahead, and later ones look further along
the lines that earlier ones found promising. What the simulations find is kept
in a tree, which the next simulation reads.

**One simulation, step by step:**

1. Copy the game at the current position (`clone_for_search`).
2. At a decision the search has already evaluated, give every legal move a
   score and play the move with the highest score on the copy; a tie is broken
   at random. The score adds two terms:
   - **what earlier simulations found:** the move's average result so far for
     the alliance that is choosing, rescaled so that the worst and best move
     averages seen in this search become 0 and 1. A simulation's result is the
     network's value of the position where it stopped, or the true final scores
     at the end of the game. A move no simulation has tried yet gets 1, as good
     as the best, so untried moves usually come first;
   - **what the network expected:** `c_puct` (1.5) × the move's prior × √(visits
     of all moves here + 1) ÷ (this move's visits + 1). It is large for a move the
     network likes that has been tried little.
3. At a chance event, roll the dice on the copy.
4. At a decision no simulation has evaluated yet, ask the deciding alliance's
   network for the position's value for all three alliances and a prior for each
   legal move, and stop.
5. Stop also at the end of the game (using the true scores), at the depth limit
   (using the network's value), or on returning to a position already on this
   simulation's path.
6. Add the three values found to every position and move on the path, with one
   more visit each.

Each alliance judges moves by its own value: this is Max-N search, not a search
for an equilibrium. Values are rescaled per alliance before they enter the score.

**Depth** is how many steps a simulation walked from the current position before
it stopped, counting moves and dice rolls. The limit is 16 in current runs.

**How the tree grows: a toy example.** The current position R has three legal
moves, A, B and C. Before the first simulation the network evaluates R, which
gives priors for A, B and C.

```text
simulation 1   R --A--> RA                  RA is new: ask the network, stop    depth 1
simulation 2   R --B--> RB                  RB is new: ask the network, stop    depth 1
simulation 3   R --C--> RC                  RC is new: ask the network, stop    depth 1
simulation 4   R --A--> RA --x--> RAx       RAx is new: ask the network, stop   depth 2
```

Simulations 1 to 3 each try a move nobody has tried. Simulation 4 scores the three
moves again. Say the network's priors are A 0.5, B 0.3 and C 0.2, and the results
so far rescale to A 1, C 0.5 and B 0. Each move has one visit of three, so its
second term is 1.5 × prior × √4 ÷ 2: A scores 1 + 0.75 = 1.75, B 0 + 0.45 = 0.45
and C 0.5 + 0.3 = 0.8, and the simulation plays A. At RA no move has been tried, so
every first term is 1 and the move with the highest prior, x, wins. RAx is new, so
the simulation stops there.

So a simulation chooses its path one step at a time, by these scores, at every
position it passes. It does not look for the deepest branch: it goes deep only
where the scores keep sending it. Each simulation adds one new position to the
tree, so the lines the scores keep choosing are explored deeper and deeper.

**What the search remembers.** The tree holds, for every position the search has
met, identified by its planning key, the moves tried there with their visit
counts, value totals and priors (`Node` and `Edge`), and a saved copy of the game
at that position (`Node.game`). A simulation walks the tree on these saved
positions. Following a move already played from a position needs only the tree:
the engine rolls no dice inside a move, so a move from a position always reaches
the same position. The simulation copies a saved position only to play a move no
simulation has played from there yet, or to roll dice. In the toy example,
simulation 4 follows A to RA in the tree alone, copies the saved RA and plays only
x.

**The dice.** Each simulation rolls its own dice, from a stream seeded per
simulation, so one move can lead to different outcomes in different simulations,
and the tree keeps a branch per outcome; the real game's dice are untouched.
Each copy a simulation makes continues that simulation's stream where its last
copy left it (`clone_for_search_continuing`), so the dice come out exactly as if
the simulation had played its whole path on one copy.

**A real example** ([measurements](../stage_a/search_replays_2026_11_04.md)). At a
round-5 Japanese Combat Movement decision with 24 legal moves, the network was
asked 65 times: once for the current position and once per simulation. 24
simulations, all among the first 31, each tried a different one of the 24 moves
and stopped after one step. The other 40 went deeper, 37 of them through two
moves, which ended with 27 and 12 of the 64 visits: 21 stopped after two steps
and the rest after three to nine. The deepest, nine steps, chose to end Combat
Movement and followed positions earlier simulations had evaluated: the start of a
battle, a retreat, a retreating unit and the next battle, with four dice rolls on
the way. The 64
simulations together played 57 moves and 38 dice rolls, and the tree kept 77
positions. At a decision with 104 legal moves, 55 of the 64 simulations stopped
after one step.

**What the copies cost and save.** Every position the search evaluates still comes
from the real rules, played by the engine. A saved copy takes about 144 KB, so
that tree held about 11 MB; each tree is dropped after its decision. Until
4 November the tree kept no positions, and every simulation copied the current
position and played its whole path again: 123 moves instead of 57 in the example,
and about half of the time game threads spent not waiting for the network
([measurements](../stage_a/search_replays_2026_11_04.md)). Saving copies gave
identical search results on 151 real positions and played 59% fewer moves. In a
matched training batch it raised games per hour while playing from 152 to 184,
for 0.5 GB more peak memory ([record](../stage_a/search_copies_2026_11_04.md)).

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

1. **The board:** each of the 37 zones (31 land, 6 sea) answers the same 42,520
   zone questions, such as "how many CCP cavalry are here?".
2. **The position as a whole:** 6,634 questions, such as the round, the phase,
   whose turn it is, treasuries and wars.
3. **Each legal move:** 12,667 questions, such as which kind of move it is, which
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
`studies/campaign/neural.py`. For a decision it returns three **values**, its
estimates of the three alliances' final scores, and a **probability** for every
legal move, its first guess at which moves the search should try. Its size is
written width × message layers: 64×2 in the Mac profile's measurements, 256×8 in
the night run of 2 November. The examples below use 64×2 and the decision of
[the input page](network_input.md#2-three-parts): game seed 5, the CCP's first
Combat Movement decision, with 13 legal moves.

**The structure.** Inside the network, every zone, the position as a whole and
every legal move is described by a *vector*: a list of numbers, as many as the
width. For that decision:

```text
the input                    learned table          vectors of 64 numbers
board: 326 answers,     ->   zone table,       ->   37 zone vectors
  filed by zone                42,520 rows
position: 119 answers   ->   position table,   ->   1 position vector
                               6,634 rows
moves: 244 answers,     ->   move table,       ->   13 move vectors
  filed by move                12,667 rows

then:
  2 message layers   every zone vector is updated from its neighbours' vectors,
                     along the 160 directed borders, and from the position
                     vector; the position vector from the average zone
  value              position vector + the zones' mean and maximum
                     -> a summary vector -> 3 numbers, one per alliance
  policy             each move vector + the vectors of the zones it starts
                     from, acts on and passes through, + the summary
                     -> 13 scores -> 13 probabilities, in stages
```

**Learned rows.** A network is a large set of numbers that training adjusts
(section 6), its *parameters*: 4,089,928 of them at 64×2. Almost all, 97%, sit in
three tables that hold one row of 64 numbers for every question: 42,520 rows for
the zone questions, 6,634 for the position's and 12,667 for the moves'. A
question's row is what an answer to that question adds to a vector: the
network's own description, in 64 numbers, of "a CCP cavalry is here" or "the CCP
possesses this zone". No number in a row has a meaning chosen by hand. Training
moves them until the answers that matter push the vectors in useful directions.

**Learned layers** hold most of the other 3%. A learned layer multiplies a vector
by a learned table of numbers and adds a learned vector; most then bend the
result with a fixed curve (GELU). Without the curves, any stack of layers would
amount to a single multiplication and could only add effects up.

**A zone's vector is a sum of rows.** Shensi answers 12 of the 42,520 zone
questions in that decision ([listed here](network_input.md#3-questions-and-answers));
its other 42,508 answers are zero. Each answered question picks out its own row
from the zone table, multiplied by a weight that grows with the answer a,
sign(a) × log(1 + |a|): an answer of 1 counts 0.69, 2 counts 1.10 and 10 counts
2.40, so larger counts matter more but not in proportion. Shensi's vector starts
as the sum of those 12 weighted rows. Here are three of the twelve, with the width
cut to 3 and invented row numbers (a fresh network's rows are all zero, and a
trained network's numbers mean nothing one by one):

```text
question             answer  weight  its row (3 numbers)    weight × row
possessor:ccp           1     0.69   [ 0.50  0.10 -0.20]    [ 0.35  0.07 -0.14]
units:ccp:cavalry       1     0.69   [ 0.20 -0.40  0.30]    [ 0.14 -0.28  0.21]
units:ccp:militia       2     1.10   [ 0.10  0.30  0.00]    [ 0.11  0.33  0.00]
                                                     sum:   [ 0.60  0.12  0.07]
```

The other nine answers add their rows the same way, and the real rows have 64
numbers. Hopeh, next door, answers 8 questions, among them a warlord militia and
three railroads, so its vector starts as a sum of 8 rows.

**One table serves every zone.** `units:ccp:cavalry` has one row, added wherever
CCP cavalry stand, so what the network learns about cavalry in Shensi applies in
Hopeh too. To tell the zones apart, each zone vector also gets a learned row for
the zone itself, and its 39 fixed map facts, such as production value, terrain
and original owner, through a learned layer. Then its 64 numbers are rescaled to
a standard spread (layer normalization), so a zone with 43 answers, like sea zone
P15 with Japan's fleet, does not get a vector many times larger than a zone with
one.

**Why this is called a lookup.** Picture the board input as a table with one
line per zone and one column per question, almost all zeros:

```text
                    possessor:  units:ccp:  possessor:warlord_  rail_to:land_   ...
                    ccp         cavalry     beiping_hopeh       china_shensi
land_china_shensi   1           1           0                   0
land_china_hopeh    0           0           1                   1
... 35 more zones, 42,520 columns in all
```

That is why questions are also called columns. Multiplying each zone's whole line
of 42,520 weighted answers by the zone table, as a textbook network layer would,
gives the same 37 sums (checked on Shensi, up to float rounding), but for
Shensi alone it would multiply 42,508 zeros. So the network fetches only the rows
of the answered columns, a *column lookup*, and adds them up: 689 rows for this
decision, 326 + 119 + 244.

**Three kinds of sums.** The position vector is the same kind of sum over the
position's 119 answers, with the position table, and each move vector over the
move's own answers, with the move table: 21 rows for the cavalry attack on Hopeh
([its answers](network_input.md#example-1-a-cavalry-attack)), 4 for `end_phase`. A
coordinator call (section 7) does this for every zone of every position, every
position and every move at once: about 6,000 rows for a call of four positions
([record](../stage_a/coordinator_lookups_2026_11_04.md)).

**Messages along the borders.** A zone vector so far describes only its own zone.
The map has 80 borders, each counted in both directions: 160 directed borders. In
each message layer:

1. every zone sends a message along each border leaving it: its own vector through
   a learned layer, plus the border's 22 fixed facts, such as a river, a railway or
   a narrow crossing, through another, the sum bent by the curve;
2. every zone averages the messages it receives;
3. every zone adds a correction to its vector, computed by a learned layer from its
   old vector, that average and the position vector; then the position vector adds
   a correction computed from itself and the average zone vector.

Shensi borders Hopeh, Suiyuan, Szechwan and Tsinghai. After the first layer its
vector reflects what they hold, such as Hopeh's warlord militia; after the second,
also what borders them, such as Beiping next to Hopeh. Through the borders, after
k layers a zone's vector reflects zones up to k borders away; through the position
vector, from the second layer on, it also reads the average of all zones.

**The value.** A learned layer combines the position vector with the mean and the
maximum of the 37 zone vectors into one summary vector of the position. Two more
learned layers turn the summary into three numbers: the predicted final scores of
the Axis, the Allies and the Comintern, divided by 100.

**A score for each move.** Each move vector is rescaled like the zone vectors and
joined with three zone vectors, taken after the message layers: the zone it starts
from, the zone it acts on and the average of its path zones. A move that names no
zone, such as `end_phase`, gets a learned "no zone" vector for the first two and
zeros for the path. A learned layer turns these 4 × 64 numbers into one combined
vector of the move, and two more turn that, with the summary, into one score. So
the cavalry attack on Hopeh reads its own 21 answers ("a CCP cavalry with 2 moves
left, in Shensi, attacking along Shensi–Hopeh") together with Shensi's vector as
its start, Hopeh's as the zone it acts on, and the average of both as its path.

**Probabilities in stages.** The moves are grouped by kind, then by what acts, then
by how it travels, then by what it acts on. At each stage the network scores every
group from the summary and the average combined vector of the group's moves, and
gives the groups under one parent probabilities that add up to 1; the exact move
comes last. In that decision:

| Stage | Groups | In this decision |
| --- | ---: | --- |
| Kind | 2 | a movement (12 moves), ending the phase (1) |
| What acts | 4 | the cavalry, the first and the second mountain infantry (4 moves each), and ending the phase |
| How it travels | 13 | each unit to Hopeh, Suiyuan, Szechwan or Tsinghai, and ending the phase |
| What it acts on | 13 | no further split: these moves name no target apart from their path |
| The exact move | 13 | one move in each group |

So the probability of the cavalry attack on Hopeh is P(a movement) × P(the cavalry,
among the three units) × P(to Hopeh, among its four destinations). Every listed
move gets a probability; none is padded, merged or dropped. Which details count as
"what acts" and so on comes from the roles explained in
[The network's input](network_input.md#roles).

**Rows start at zero** (since 3 November 2026). A question that training has never
reached adds nothing, instead of a random row added at full strength. On fixed
data this gave a slightly lower held-out value error (0.0076 against 0.0081) and
the same policy loss: no harm shown, not a strength gain.

**Most of a network is rows:** 3.96 M of the 4.09 M parameters at 64×2 (97%), and
15.83 M of 20.24 M at 256×8 (78%), whose wider layers weigh more. A decision reads
only the rows of its answers: 689 of 61,821 in that example.

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

**The coordinator.** Game threads do not run the network themselves. A game
thread that needs an evaluation writes the position's input into shared memory
and waits. In each round the coordinator reads every waiting request, groups them
by alliance network, merges each group into one batch, runs that network once and
sends back each position's priors and values (`studies/campaign/shared_evaluator.py`).
A larger batch costs less per position: 0.70 ms for one position, 1.38 ms for
four ([record](../stage_a/coordinator_lookups_2026_11_04.md)). On 2 November the
network's forward pass was three quarters of the coordinator's time, and the
column lookups (section 5) were its largest single part, 26%
([profile](../stage_a/search_replays_2026_11_04.md#2-november-one-profiled-training-batch)).
Since the search keeps copies of its positions, the coordinator is busy 90% of the
time and limits this layout.

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

On 4 November the search began keeping a copy of the game at each tree position
(section 3). In a matched batch of the Mac profile, with little training, that
raised decisions per hour while playing by 15%, from about 162,000 to 188,000;
the coordinator, busy 90% of the time, now limits that layout
([record](../stage_a/search_copies_2026_11_04.md)).

**Failures.** A game that fails costs only that game. Its seed is recorded, and a
rules dead end (a decision with no legal move) saves its position in the run's
`failed-positions/` folder. Two random-play checks run before long runs: the
fuzzer (`tools/fuzz_campaign_dead_ends.py`) looks for dead ends and for moves
that leave the game unchanged, and `tools/check_zone_names.py` for names the
network's input does not list.

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

- **Some details are summarized, not named.** Since 4 November no name in 480
  random games falls into an "other" question, and tests check the names the
  engine's source writes. But a mark's argument other than a place or a nation,
  such as which railroad was damaged this turn, is counted for the whole
  position, and a battle note's numbers are added into one answer. See
  [names the encoder doesn't know](network_input.md#keeping-the-lists-complete).
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
- **The coordinator limits the Mac layout.** It was busy 90% of the time in the
  latest matched batch. A fused column lookup (PyTorch's `embedding_bag`) made the
  network's forward pass 23% to 49% faster with identical outputs
  ([record](../stage_a/coordinator_lookups_2026_11_04.md)); it is not yet in the
  code. More games per process, for larger batches, and a second coordinator are
  the other options, untested.

## 10. Glossary

- **Alliance (player):** Axis, Allies or Comintern; each chooses for its nations.
- **Position (state):** everything about the game at one moment.
- **Decision:** a position where one alliance must choose a move.
- **Legal move (option, action):** one choice the rules allow at a decision.
- **Chance event:** a position where the engine rolls dice.
- **Planning key:** a text that identifies a position exactly.
- **Search (MCTS):** the simulations that pick a move at a decision.
- **Simulation:** one imagined walk forward from the current position, on a copy
  of the game.
- **Depth:** how many steps, moves and dice rolls, a simulation walked from the
  current position before it stopped.
- **Search tree:** what a search remembers between simulations: for each position
  it has met, its planning key, the statistics of the moves tried there and a
  saved copy of the game at that position.
- **Prior:** the network's probability for a move, before searching.
- **Visit count:** how often the search tried a move.
- **Value:** the network's estimate of the final scores, one per alliance.
- **Question (column):** one numbered input slot with a fixed meaning.
- **Answer:** the whole number a position gives to a question.
- **Family:** a group of questions with one name pattern, such as `units`.
- **Vector:** a list of numbers, as many as the width, that describes a zone, the
  position or a move inside a network.
- **Width:** how many numbers each vector and row has: 64 in a 64×2 network.
- **Row:** the learned numbers, as many as the width, that a network keeps for one
  question. An answer adds its question's row, weighted, to a vector.
- **Column lookup:** fetching the rows of the questions a position answers and
  adding them up.
- **Parameters:** all the numbers training adjusts: the rows and the learned layers.
- **Layout version:** an identifier of the full set of questions and fixed map
  facts; a network refuses inputs of another layout.
- **Sample:** a kept decision with its targets.
- **Replay buffer:** the recent samples that training draws from.
- **Batch:** the games played between two updates.
- **Update:** the training steps after a batch.
- **Model export:** the saved networks after an update.
- **Checkpoint:** a full save of a run, for resuming it.
