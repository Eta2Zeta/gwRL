# How gwRL learns

This is the central design document of the learning system: how the program
learns to play the 1936–1941 Japan–China campaign. It builds the system up from
its bricks. Each section defines its parts, with a picture or a real example,
before any later section uses them, and the last sections put the whole training
loop together. One real decision, called decision 612 and introduced in
[section 2](#23-legal-actions-and-the-running-example), is the example throughout.
A section's last part, headed "More detail", can be skipped on a first reading.

**Words.** The document uses the standard terms of reinforcement learning and
machine learning, such as *state*, *action*, *feature*, *embedding*, *forward
pass* and *training step*, and each word means one thing only. A word that has
more than one meaning in common use always carries the word that says which one:
a *training step* or an *Adam step*, never a bare step; a *game round*, never a
bare round. Every term is defined where it is first used and listed in the
[glossary](#12-glossary).

The document is revised whenever a question digs into part of the design (see
`AGENTS.md`). The measurements behind its numbers are in the dated
[records of the archive](../archive/README.md#dated-records), which it links to
as evidence. The page
[The network's input](network_input.md) goes deeper into how a decision becomes
numbers.

## Contents

1. [In brief](#1-in-brief)
2. [The game, as the learner sees it](#2-the-game-as-the-learner-sees-it)
3. [What a network gives at a decision](#3-what-a-network-gives-at-a-decision)
4. [Choosing an action: search](#4-choosing-an-action-search)
   - [4.1 Why search](#41-why-search) · [4.2 One simulation](#42-one-simulation) ·
     [4.3 The PUCT score](#43-the-puct-score-of-an-action) ·
     [4.4 A toy search](#44-a-toy-search) ·
     [4.5 After the simulations](#45-after-the-simulations-visit-counts-and-visit-shares) ·
     [4.6 A real search](#46-a-real-search-decision-612) ·
     [4.7 More detail](#47-more-detail-on-the-search)
5. [How a decision becomes numbers](#5-how-a-decision-becomes-numbers)
   - [5.1 Features and feature values](#51-features-and-feature-values) ·
     [5.2 Three parts](#52-three-parts-zone-features-global-features-and-action-features) ·
     [5.3 Feature matrices](#53-the-input-as-feature-matrices) ·
     [5.4 An action's features](#54-an-actions-features-and-its-zones) ·
     [5.5 Static features](#55-static-features) ·
     [5.6 More detail](#56-more-detail-how-the-encoder-builds-the-input)
6. [Inside a network, brick by brick](#6-inside-a-network-brick-by-brick)
   - [6.1 Vectors](#61-vectors) · [6.2 Linear layers](#62-linear-layers) ·
     [6.3 The embedding layer](#63-the-embedding-layer-embeddings-and-embedding-tables) ·
     [6.4 A zone's vector](#64-a-zones-vector) ·
     [6.5 Global and action vectors](#65-the-global-vector-and-the-action-vectors) ·
     [6.6 Message-passing layers](#66-message-passing-layers-messages-along-the-borders) ·
     [6.7 The values](#67-the-values) ·
     [6.8 The action probabilities](#68-the-action-probabilities) ·
     [6.9 The whole network](#69-the-whole-network) ·
     [6.10 More detail](#610-more-detail-how-other-game-networks-read-their-input)
7. [Self-play and training samples](#7-self-play-and-training-samples)
8. [Training the network](#8-training-the-network)
   - [8.1 The loss](#81-the-loss) · [8.2 The gradient](#82-the-gradient) ·
     [8.3 Adam](#83-adam) ·
     [8.4 Training steps and network updates](#84-one-training-step-and-one-network-update) ·
     [8.5 Which numbers a training step moves](#85-which-numbers-a-training-step-moves) ·
     [8.6 Why small random minibatches](#86-why-small-random-minibatches) ·
     [8.7 How often a training sample is drawn](#87-how-often-a-training-sample-is-drawn)
9. [The whole loop, and running it](#9-the-whole-loop-and-running-it)
10. [Measuring strength](#10-measuring-strength)
11. [Known gaps and open questions](#11-known-gaps-and-open-questions)
12. [Glossary](#12-glossary)

## 1. In brief

Three agents, one per alliance (Axis, Allies and Comintern), learn the campaign
by playing it against each other many thousands of times, in the manner of
AlphaZero. They share one neural network, which is told which alliance is
choosing:

- **They look ahead before they act.** At every decision the agent whose turn
  it is plays possible continuations on copies of the game, a *search*
  (section 4), guided by the network (sections 3, 5 and 6).
- **They keep some of their decisions** as *training samples*: each with what
  the search preferred there and how the game ended (section 7).
- **They learn from them, while they play.** Self-play never stops: after every
  24 games that end, a *network update* adjusts the network to propose what the
  search preferred and to predict how games end (section 8), while the games go
  on, and every game takes up the new network as soon as it is ready. Those
  games and their network update make one *training iteration*. A better
  network makes the next searches better, and the loop repeats (section 9).

Whether that works for this game on this hardware is unproven: no training run
has yet shown robust playing strength ([section 10](#10-measuring-strength)).

## 2. The game, as the learner sees it

The rules are written in C++ (`src/`, `include/game/`) and reach Python as
`gwrl_cpp.CampaignEnv`, wrapped by `studies/shared/campaign_adapter.py`.

### 2.1 Alliances and nations

Each alliance plays for its nations: the Axis for Japan, the Allies for the KMT,
and the Comintern for the CCP and Mongolia. The eight Chinese warlords start
under nobody's control; some rules can later hand one to an alliance.

### 2.2 States: decisions, chance events and the end

A *state* is everything about the game at one moment: in a board game's words,
its position. A game is a chain of states, and each state is one of three kinds:

- **a decision:** one alliance chooses one *action* from a list of *legal
  actions*, the actions the rules allow there;
- **a chance event:** the engine rolls dice;
- **the end** of the game, the *terminal state*, after the eleventh game round
  (1941).

Reactions are decisions too: the defender picks casualties, an attacker chooses
whether to retreat, and so on. A full eleven-round game holds well over a
thousand decisions.

![A row of five states joined by arrows: a decision, where one alliance chooses one legal action; an action leads to the next decision, often by the same alliance; an action leads to a chance event, where the engine rolls dice, say for a battle; the dice lead to further decisions, over a thousand of them; the chain ends after game round 11 with the final scores. Below: one real game, played on 5 November with the networks after one network update (seed 1105), had 1,349 decisions and 183 chance events; its 612th decision is the running example, in game round 5 the Comintern choosing the CCP's Combat Movement from 5 legal actions; it ended Axis +49.0, Allies −63.8, Comintern −106.2.](figures/game_states.svg)

### 2.3 Legal actions, and the running example

**A legal action is a small data structure:** a kind plus labelled details. The
running example of this document is decision 612 of a game the networks played
on 5 November, after their first network update
([record](../archive/records/training_sample_2026_11_05.md)). That run kept a
network for each alliance, the setting before 18 November (`--networks three`,
section 8.4), so the examples speak of the Comintern's network, the one that
chose at decision 612; today one network serves all three alliances and gives
the same kinds of output at every decision. In game round 5,
during the CCP's Combat Movement, the Comintern chooses for the CCP. The CCP's
mountain infantry in Shensi has one movement point left and may attack one of
four neighbouring zones the KMT holds, Hopeh, Suiyuan, Szechwan or Tsinghai, or
the CCP may end its Combat Movement. So the decision has 5 legal actions. The
attack on Hopeh, as the engine writes it:

| Detail | Value |
| --- | --- |
| `kind` | `movement_route` |
| `unit` | `setup_ccp_land_china_shensi_mountain_infantry_1` |
| `path` | `[land_china_shensi, land_china_hopeh]` |
| `combat` | `true` |
| `mode` | `ordinary` |

The other three attacks differ only in the path's second zone. The fifth action,
ending the phase, has the kind `end_phase` and no details. Long orders, such as a
fleet's, are built one part at a time, each part a decision of its own with a
bounded list of legal actions: see
[the rules engine, section 3](../engine/README.md#3-states-and-actions).

### 2.4 The final score

Only the end of the game is scored; there is no reward along the way. Each
alliance's wealth is its income plus a tenth of what its units, its
infrastructure, its treasury and its paid construction are worth. Its *final
score* is its own wealth minus the other two alliances' wealth combined
(`src/campaign_objective.cpp`). The three final scores form one list,
`[Axis, Allies, Comintern]`. The game of decision 612 ended Axis +49.0, Allies
−63.8 and Comintern −106.2.

### 2.5 What the learner asks of the engine

The legal actions, apply an action, roll the dice, is the game over, the final
scores, a copy of the game for search, and the state's *planning key*, a digest
that identifies a state exactly.

## 3. What a network gives at a decision

In reinforcement-learning terms an agent needs a *policy*, how likely it is to
choose each legal action, and a *value function*, how good a state is for it.
Here one neural network gives both, for any decision of any alliance, which its
input names (`CampaignPolicyValueNet` in `studies/campaign/neural.py`; with
`--networks three` each alliance has a network of its own, section 8.4). Given
a decision, it returns:

- **three values:** its estimates of the three alliances' final scores. Inside,
  the network works in hundreds of points: it outputs 0.251 for a final score of
  +25.1.
- **a probability for every legal action,** adding up to 1: its first guess at
  which action to play. The search (section 4) uses these probabilities as the
  actions' *priors*.

This is what the Comintern's network gave at decision 612:

![Left: decision 612, what the network is given: the state (the board, game round 5, Combat Movement, the CCP's turn) and the 5 legal actions: 1 to 4, the mountain infantry in Shensi attacking Hopeh, Suiyuan, Szechwan or Tsinghai, and 5, ending Combat Movement. Middle: the Comintern's network, 4.1 million parameters. Right, what it gives: values, its estimate of each alliance's final score: Axis +25.1, Allies −42.4, Comintern −102.4; and action probabilities, its first guess, which the search uses as priors: 0.10, 0.10, 0.09, 0.18 and 0.53 for actions 1 to 5.](figures/network_outputs.svg)

The network gives values for all three alliances, not only its own, because a
search (section 4) needs to know how each state it reaches looks to whichever
alliance chooses there.

Until section 6 the network is a closed box: what goes in and what comes out is
all the next section needs. Inside are 3.9 million learned numbers, its
*parameters*; training (section 8) adjusts them. Section 5 shows how a decision
is turned into numbers the network can read, and section 6 how it turns them into
values and probabilities.

The first guess is not the last word. At decision 612 the network favoured
ending the phase, 0.53, over the attack on Hopeh, 0.10. The search, looking
ahead, preferred the attack ([section 4.6](#46-a-real-search-decision-612)), and
the game ended with the Comintern at −106.2 where the network had predicted
−102.4.

## 4. Choosing an action: search

### 4.1 Why search

The network answers in one look. A search looks ahead: it plays actions on copies
of the game, asks the network about the states it reaches, and combines the
network's outputs. Where looking ahead finds something the one look missed, the
search chooses better than the network alone. The search is Monte Carlo tree
search in AlphaZero's style (`studies/shared/multiplayer_mcts.py`, class
`VectorMCTS`), made of many *simulations*: 64 per decision in current runs.

### 4.2 One simulation

**Every simulation starts from the same place: the current state,** the *root* of
the search. It plays on its own copy of the game, so the real game does not
change. It does not play to the end of the game: it walks forward only until it
reaches a state that no earlier simulation has asked the network about, asks
about that one, and stops. So the first simulations look one action ahead, and
later ones look further along the continuations that earlier ones found
promising.

**What the simulations find is kept in a tree,** the *search tree*, which the
next simulation reads. Each state the search has met is a *node* of the tree. For
every node, the tree holds the actions tried there, each with its *visit count*,
how many simulations played it, and the total of the values those simulations
found.

**One simulation, in order:**

1. Copy the game at the current state (`clone_for_search`).
2. At a decision the search has already asked the network about, give every
   legal action a PUCT score (section 4.3) and play the action with the highest
   score on the copy; a tie is broken at random.
3. At a chance event, roll the dice on the copy.
4. At a decision no simulation has asked the network about yet, ask the
   network, told which alliance decides there, for the state's values for all
   three alliances and a prior for each legal action, and stop. With a network
   for each alliance, the deciding alliance's network is asked.
5. Stop also at the end of the game, using the true final scores; on returning to
   a state already on this simulation's path; or after 16 actions and dice
   rolls, the depth limit. The last two use an estimate of the state reached
   ([section 4.7](#47-more-detail-on-the-search)).
6. Add the three values found to every state and action on the path, with one
   more visit each.

### 4.3 The PUCT score of an action

In item 2 above, the search gives each legal action a *PUCT score*, the selection
rule of AlphaZero ("predictor plus upper confidence bound applied to trees"). It
is the sum of two terms:

$$
\text{PUCT score} = \underbrace{\frac{\bar v - v_{\min}}{v_{\max} - v_{\min}}}_{\text{value term}} + \underbrace{c_{\text{puct}} \times P \times \frac{\sqrt{N + 1}}{n + 1}}_{\text{exploration term}}
$$

- **The value term, what earlier simulations found.** $\bar v$ is the action's
  average result so far for the alliance that is choosing. A simulation's result
  is the network's value of the state where it stopped, or the true final
  scores at the end of the game. $v_{\min}$ and $v_{\max}$ are the lowest and
  highest averages, for that alliance, that any action anywhere in this search's
  tree has had so far; the range only widens. So the value term places the
  action's average on a scale from 0, the worst seen, to 1, the best. Until the
  search has seen two different averages the scale has no width, and every
  tried action's value term is 0.5. An action no simulation has tried yet gets 1,
  as good as the best, so untried actions usually come first.
- **The exploration term, what the network expected.** $P$ is the action's prior,
  $n$ how many simulations have played this action here, $N$ how many have
  played any action here, and $c_{\text{puct}}$ is 1.5. It is large for an
  action the network likes that has been tried little, and it shrinks each time
  the action is tried.

Each alliance judges actions by its own value: this is Max-N search, not a search
for an equilibrium. Values are rescaled per alliance before they enter the
PUCT score.

### 4.4 A toy search

The current state R has three legal actions, A, B and C. Before the first
simulation the search asks the network about R, which gives priors for A, B and
C: say 0.40, 0.36 and 0.24.

![The search tree after four simulations. Simulations 1, 2 and 3 each try one untried action from R and add the nodes RA, RB and RC at depth 1, asking the network about each. Simulation 4 plays A again, then x, the action with the highest prior at RA, and adds RAx at depth 2.](figures/search_tree.svg)

Simulations 1 to 3 each try an action nobody has tried, and simulation 4 goes one
action deeper. Before each simulation the search scores the three actions, value
term plus exploration term:

| Before simulation | A | B | C | Plays |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 + 0.60 = 1.60 | 1 + 0.54 = 1.54 | 1 + 0.36 = 1.36 | A |
| 2 | 0.5 + 0.42 = 0.92 | 1 + 0.76 = 1.76 | 1 + 0.51 = 1.51 | B |
| 3 | 1 + 0.52 = 1.52 | 0 + 0.47 = 0.47 | 1 + 0.62 = 1.62 | C |
| 4 | 1 + 0.60 = 1.60 | 0 + 0.54 = 0.54 | 0.5 + 0.36 = 0.86 | A |

- **Before simulation 1** nothing has been tried, so every value term is 1 and
  the priors decide.
- **Before simulation 2** A has the only result seen, so its value term is 0.5.
- **Before simulation 3** say A's simulation ended better than B's: A's average
  rescales to 1 and B's to 0. C, untried, still gets 1, and its larger
  exploration term wins.
- **Before simulation 4** say C's result lay halfway between A's and B's, so it
  rescales to 0.5. Each action has one visit of three, so its exploration term is
  $1.5 \times P \times \sqrt{3 + 1} \div (1 + 1)$, 0.60 for A.

So simulation 4 plays A. At RA no action has been tried, so every value term is 1
and the action with the highest prior, x, wins. RAx is new, so the simulation
stops there.

So a simulation chooses its path one action at a time, by these scores, at every
state it passes. It does not look for the deepest branch: it goes deep only
where the scores keep sending it. Each simulation adds one new node to the tree,
so the continuations the scores keep choosing are explored deeper and deeper.

### 4.5 After the simulations: visit counts and visit shares

**Visit counts and visit shares.** After all 64 simulations, the number of times
each action at the root was tried, its visit count, shows the search's
preference. An action's *visit share* is its visit count divided by the number of
simulations; AlphaZero names the visit shares the *search probabilities*. The
action actually played is drawn at random in proportion to the visit counts
(temperature 1), and the visit shares become part of a training sample
(section 7).

**How the visit shares come to differ from the priors.** An action whose
simulations keep scoring better than the others' is chosen again and again,
until its exploration term has shrunk enough for the others to catch up. Actions
whose results are about the same share the remaining simulations roughly in
proportion to their priors, since only the exploration term tells them apart.
So the visit shares end up far from the network's priors mainly where the search
found an action better than the rest: that action gains, and every other action
gives up simulations in proportion to its prior.

**Exploration noise.** During training, random noise (Dirichlet, alpha 0.3,
mixed in at 25%) is added to the network's priors at the root, so the search
sometimes tries actions the network dislikes. Held-out evaluation, which
measures playing strength (section 10), turns it off.

**A decision with only one legal action** is played at once, with no search and
without asking the network.

### 4.6 A real search: decision 612

At decision 612 the noise changed the five priors of [section
3](#3-what-a-network-gives-at-a-decision): it lowered the attack on Hopeh from
0.10 to 0.085 and ending the phase from 0.53 to 0.40, and raised the attacks on
Szechwan and Tsinghai to 0.177 and 0.268. The simulations ran one after another,
numbered 1 to 64 in the order they ran. Each began by scoring the five actions
and playing the action with the highest PUCT score. The figure shows the action
each began with
([trace](../archive/records/training_sample_2026_11_05.md#how-the-64-simulations-were-spent)).

![The 64 simulations of the search at decision 612, numbered in the order they ran, in two rows of 32, each marked with the action it began with. Simulations 1 to 14 tried every action; the two that began with the attack on Hopeh, 6 and 11, stopped before its battle. Simulation 15 was the first to play through the battle, in which the CCP takes Hopeh, at a state rated −101.42. From 15 to 51 the attack on Hopeh was chosen 32 times out of 37; simulation 33's PUCT scores are in the table below. Simulation 53 stopped at the depth limit at a state rated −106.02, and simulations 54 to 64 all began with the other actions.](figures/simulations_at_decision_612.svg)

**Simulations 1 to 14** tried every action. The attack's two, simulations 6 and
11, stopped before its battle, with Hopeh still the KMT's, and scored like every
other action: about −102.2 for the Comintern.

**Simulation 15** was the first to play on through the end of Combat Movement and
the battle, which the CCP won. The network rated the state it reached, with the
CCP holding Hopeh, −101.42: better than any result before it.

**Simulations 15 to 51** began with the attack 32 times out of 37. From 15 on,
all 34 of its simulations stopped at states where the CCP held Hopeh, and the
network rated 24 of them between −101.43 and −101.16; no simulation of another
action did better than −102.16. The table gives the five PUCT scores just before
simulation 33, after 32 simulations:

| Action | Simulations so far ($n$) | Average result for the Comintern ($\bar v$) | Value term | Prior after noise ($P$) | Exploration term | PUCT score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Shensi → Hopeh | 18 | −101.50 | 0.77 | 0.085 | 0.04 | **0.81** |
| Shensi → Suiyuan | 1 | −102.40 | 0.16 | 0.072 | 0.31 | 0.47 |
| Shensi → Szechwan | 1 | −102.63 | 0.00 | 0.177 | 0.76 | 0.76 |
| Shensi → Tsinghai | 7 | −102.26 | 0.25 | 0.268 | 0.29 | 0.54 |
| End Combat Movement | 5 | −102.39 | 0.17 | 0.399 | 0.57 | 0.74 |

**The value term** places an action's average on a scale that runs from the
worst average the search had met so far, which counts as 0, to the best, which
counts as 1. Before simulation 33 these were −102.63, the result of the Szechwan
attack's one simulation, and −101.16, the result of simulation 20, deep in the
attack's continuation. (An action that only one simulation has tried has that
simulation's result as its average.) The attack's average sat 77% of the way up:

$$
\frac{-101.50 - (-102.63)}{-101.16 - (-102.63)} = \frac{1.13}{1.47} \approx 0.77
$$

The other actions' averages lay 0 to 0.37 points above the worst, 0 to 25% of the
way up. The attack's lead over the next best action, Tsinghai, was 0.76 points:
small next to final scores in the tens or hundreds, but the results this search
had seen spanned only 1.47 points, so on its scale the lead was large.

**The exploration term** was small for the attack, because it had already been
tried 18 times:

$$
1.5 \times 0.085 \times \frac{\sqrt{32 + 1}}{18 + 1} \approx 0.04
$$

Szechwan's was 0.76: it had been tried once, and the noise had raised its prior
to 0.177. The attack's PUCT score, 0.81, still beat Szechwan's 0.76, so
simulation 33 began with the attack. Five of simulations 15 to 51, numbers 16,
32, 38, 42 and 51, began with another action, whose exploration term outweighed
the attack's lead at that moment.

**Simulation 53**, one of the attack's, played 16 actions and dice rolls, to the
depth limit, and reached a new state where Japan decides. So the Axis network
rated it, the only one of the search's 64 stops rated by that network alone, and
it put the Comintern at −106.02, far below anything before. Five of the attack's
simulations reached the depth limit: 44, 49, 50, 52 and 53. The low value says
more about the network than the state: simulations 49 and 50 stopped at chance
events, which that run's three networks rated together
([section 4.7](#47-more-detail-on-the-search)), and there the Axis network gave
the Comintern about 5 points less than the Comintern's own network did
([record](../archive/records/depth_limit_2026_11_09.md#simulation-53-at-decision-612)).
The bottom of the scale, at −102.64 since simulation 38 tried Szechwan again,
moved to −106.02, so all five value terms crowded between 0.70 and 0.90, and the
exploration terms decided: 0.025 for the attack after 36 simulations, 0.37 to
0.65 for the others. Simulations 54 to 64 all began with the other actions. So
the attack ended with 36 of the 64, although the exploration noise had lowered
its prior from 0.10 to 0.085.

**The other actions shared what was left, by prior.** Their simulations scored
about the same, −102.3 to −102.5 on average, so only the exploration term told
them apart. That term grows with the prior, so the remaining 28 simulations went
to them roughly in proportion to their priors after the noise, which left each
with a visit share of about half that prior:

| Action | Network's probability | Prior after noise | Visits if the 28 went exactly by that prior | Visits | Visit share |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shensi → Suiyuan | 0.10 | 0.07 | 2.2 | 2 | 0.03 |
| Shensi → Szechwan | 0.09 | 0.18 | 5.4 | 5 | 0.08 |
| Shensi → Tsinghai | 0.18 | 0.27 | 8.2 | 9 | 0.14 |
| End Combat Movement | 0.53 | 0.40 | 12.2 | 12 | 0.19 |

Ending Combat Movement had by far the largest prior, so it lost the most: the
noise cut 0.53 to 0.40, and halving left 0.19. The other three started small.
The noise had raised Szechwan's and Tsinghai's priors, and halving brought them
back near the network's numbers; Suiyuan's fell to a third, but only from 0.10
to 0.03. Their agreement is a coincidence of small numbers, not the search
confirming the network: it found no difference among them.

The attack on Hopeh ended with a visit share of 0.56. The action played was drawn
from the visit shares, and it was the attack.

### 4.7 More detail on the search

**Simulation depth** is how many actions and dice rolls a simulation played from
the root before it stopped. The *depth limit* is the greatest simulation depth
allowed: 16 in current runs (`--max-depth 16` in the training command,
`MctsConfig.max_depth` in the code; held-out evaluation, section 10, takes its
own, 4 unless set). After its 16th action or dice roll a simulation stops wherever
it is, even at a state the tree already holds, and uses an estimate of that
state:

| What the 16th action or dice roll reached | What the simulation uses |
| --- | --- |
| A decision no simulation has asked the network about | The network's value, as at any new state, so the limit changes nothing |
| A decision asked about before | The value the network gave it then; nothing new joins the tree |
| A chance event | The network's value; with a network for each alliance, the average of the three networks' values, since no alliance decides there |

**Why there is a limit.** It is as old as the search (commit `6480d5b`, 23
October). That first version had nothing else to end a simulation caught in a
loop: some sequences of actions could bring the game back to exactly a state
already on the simulation's path, and on such a loop every state is already in
the tree, so the rule to stop at a new state never fires. Two hours later the
search began to stop at such a repetition (item 5 of the list in section 4.2,
commit `47eb3d6`). Since then a simulation ends without the limit too: it never
repeats a state, it stops at the first decision no simulation has asked the
network about, and each simulation adds at most one such decision to the tree, so
no walk can outrun what earlier simulations added. What the limit does now is cap
how far ahead a search can look along one continuation. Like the other learning
settings, 16 is the value of the 2 November speed test (section 9.2), not a tuned
one.

**How much it matters** ([record](../archive/records/depth_limit_2026_11_09.md)). A
replay of the game of decision 612, with the networks after one network update,
ran 68,800 simulations in 1,075 searches: 41% stopped at depth 1, 90% within
depth 5 and 18 at the limit, in 10 searches, all at decisions with two to five
legal actions, where the simulations crowd into few continuations; none returned
to a state already on its path. Nine of the 18 had reached a new state and would
have stopped there anyway; eight stopped at a chance event and one at a known
decision. Searched again without the limit, those ten states' deepest
simulations reached depths of 16 to 19; at five of them 1 to 6 of the 64 visits
moved to other actions, and the most-visited action stayed the same at all ten.
So in this game the limit hardly mattered. At the eight chance events, though,
the three networks' values for the same state differed by 2.5 to 17 points, more
than a search's actions usually differ. One network for all three alliances, the
setting since 18 November, gives a search one network's values everywhere
([section 8.4](#84-one-training-step-and-one-network-update)).
Better-trained networks may crowd the simulations into fewer continuations and
meet the limit more often; that has not been measured.

**What the search remembers.** The tree holds, for every node, identified by its
state's planning key, the actions tried there with their visit counts, value
totals and priors (`Node` and `Edge`), and a saved copy of the game at that state
(`Node.game`). A simulation walks the tree on these saved states. Following an
action already played from a state needs only the tree: the engine rolls no dice
inside an action, so an action from a state always reaches the same state. The
simulation copies a saved state only to play an action no simulation has played
from there yet, or to roll dice. In the toy example, simulation 4 follows A to
RA in the tree alone, copies the saved RA and plays only x.

**The dice.** Each simulation rolls its own dice, from a stream seeded per
simulation, so one action can lead to different outcomes in different
simulations, and the tree keeps a branch per outcome; the real game's dice are
untouched. Each copy a simulation makes continues that simulation's stream where
its last copy left it (`clone_for_search_continuing`), so the dice come out
exactly as if the simulation had played its whole path on one copy.

**A search at a larger decision**
([measurements](../archive/records/search_replays_2026_11_04.md)). At a game-round-5
Japanese Combat Movement decision with 24 legal actions, the network was asked 65
times: once for the root and once per simulation. 24 simulations, all among the
first 31, each tried a different one of the 24 actions and stopped at depth 1.
The other 40 went deeper, 37 of them through two actions, which ended with 27 and
12 of the 64 visits: 21 stopped at depth 2 and the rest at depths of three to
nine. The deepest, at depth nine, chose to end Combat Movement and followed
states earlier simulations had evaluated: the start of a battle, a retreat, a
retreating unit and the next battle, with four dice rolls on the way. The 64
simulations together played 57 actions and 38 dice rolls, and the tree kept 77
nodes. At a decision with 104 legal actions, 55 of the 64 simulations stopped at
depth 1.

**What the copies cost and save.** Every state the search reaches still comes
from the real rules, played by the engine. A saved copy takes about 144 KB, so
that tree held about 11 MB; each tree is dropped after its decision. Until
4 November the tree kept no states, and every simulation copied the root and
played its whole path again: 123 actions instead of 57 in the example, and about
half of the time the game threads (section 9.2) spent not waiting for the network
([measurements](../archive/records/search_replays_2026_11_04.md)). Saving copies
gave identical search results on 151 real states and played 59% fewer actions.
In a matched training iteration it raised games per hour while playing from 152
to 184, for 0.5 GB more peak memory
([record](../archive/records/search_copies_2026_11_04.md)).

## 5. How a decision becomes numbers

A network computes with numbers, so every decision it is asked about is first
turned into numbers: the network's *input*. The engine's encoder
(`src/zone_encoding.cpp`) builds it once per decision. Search copies of the same
state share it, and a training sample stores it (section 7).

### 5.1 Features and feature values

**A feature** is a numbered input slot with one fixed meaning, such as "how many
CCP mountain infantry are in this zone?". Its name, here
`units:ccp:mountain_infantry`, is a readable label for that meaning; the network
only sees the number. A name is built as `family:part:part`. The *feature
family* says what kind of fact it is, `units` being how many units of a nation
and type are somewhere, and the parts say which nation, which unit type, which
zone and so on. The code names a feature a *column* (`zone_columns`), from the
feature matrices of section 5.3.

**A feature value** is a whole number: a count ("how many?"), 1 for "yes", or a
number such as the game round. Almost every feature value is 0, so only the
non-zero feature values are stored.

These are all the non-zero feature values of the zone Shensi at decision 612:

| Feature | Feature value | Meaning |
| --- | ---: | --- |
| `possessor:ccp` | 1 | the CCP holds Shensi |
| `turn_start_possessor:ccp` | 1 | and held it when the turn began |
| `units:ccp:militia` | 1 | one CCP militia is here |
| `units:ccp:mountain_infantry` | 1 | one CCP mountain infantry |
| `unit_stat:comintern:militia:count` | 1 | one Comintern militia |
| `unit_stat:comintern:militia:move_0` | 1 | ... with no movement points left |
| `unit_stat:comintern:mountain_infantry:count` | 1 | one Comintern mountain infantry |
| `unit_stat:comintern:mountain_infantry:move_1` | 1 | ... with 1 movement point left |
| `rail_to:land_china_hopeh` | 1 | a railroad runs from here to Hopeh |

Shensi's other 42,523 zone features have the value 0. Hopeh, next door, has 28
non-zero feature values: the KMT holds it and is building a fortification and a
major shipyard there, and none of its features says a unit is there.

### 5.2 Three parts: zone features, global features and action features

The input for one decision has three parts:

1. **The zones:** each of the 37 zones of the board (31 land, 6 sea) gives values
   to the same list of 42,532 *zone features*, such as
   `units:ccp:mountain_infantry`.
2. **The state as a whole:** one list of 4,076 *global features*, such as the
   game round, the phase, whose turn it is, treasuries and wars.
3. **Each legal action:** every legal action gives values to the same list of
   12,627 *action features* about itself, such as which kind of action it is,
   which unit it moves and which zones it names.

At decision 612 the zones have 840 non-zero feature values, from 2 in Szechwan to
86 in sea zone P14, the global features 176, and the legal actions 80: 19 for
each attack and 4 for ending the phase.

### 5.3 The input as feature matrices

Picture each part as a *feature matrix*: the zones' as one row per zone and one
column per zone feature, the global features' as a single row, and the actions'
as one row per legal action. One row of a feature matrix, all the feature values
of one zone, of the state as a whole or of one legal action, is a *feature
vector*. Almost every entry is 0, and only the non-zero entries are stored.

![Two feature matrices of real feature values from decision 612. The zone features: one row per zone, one column per zone feature; shown are Shensi, Hopeh, Suiyuan, Szechwan and Tsinghai, and 8 of the 42,532 columns. Shensi has the value 1 for possessor:ccp, units:ccp:militia, units:ccp:mountain_infantry and rail_to:land_china_hopeh; Hopeh 1 for possessor:kmt and project:kmt:fortification; Suiyuan 1 for possessor:kmt and 3 for units:kmt:militia; Szechwan 1 for possessor:kmt; Tsinghai 1 for possessor:kmt, 1 for units:kmt:militia and 2 for units:kmt:infantry; every other entry shown is 0. In all, Shensi has 9 non-zero feature values, Hopeh 28, Suiyuan 12, Szechwan 2 and Tsinghai 13, and the 37 zones 840. The global features: one row of 4,076 features, with round 5, completed_rounds 4, rounds_left 7, phase:combat_movement 1, turn_nation:ccp 1, turn_nation:japan 0 and phase:noncombat_movement 0; 176 non-zero feature values in all.](figures/feature_matrices.svg)

A feature vector holds one zone's, the state's global or one legal action's
feature values. In the usual picture of a neural network, the feature vectors
are its input layer, which the network's embedding layer reads
([section 6.3](#63-the-embedding-layer-embeddings-and-embedding-tables)).
A feature vector is input; it is not what section 6 names an embedding, which
holds learned numbers.

### 5.4 An action's features, and its zones

![A feature matrix of real feature values from decision 612's five legal actions, one row per action, with 10 of the 12,627 action-feature columns. Each of the four attacks has the value 1 for kind:movement_route, unit:0_source:ccp:mountain_infantry, unit_stat:0_source:move_1, zone:1_path:land_china_shensi, the path column of its own destination and true:combat, and has 19 non-zero feature values in all; ending the phase has the value 1 for kind:end_phase and has 4. On the right, the action's zones: each attack has Shensi as its source zone and its destination as its target zone; ending the phase names no zone. In all 80 non-zero feature values.](figures/action_features.svg)

These are all 19 feature values of the attack on Hopeh:

| Feature | Feature value | Meaning |
| --- | ---: | --- |
| `schedule:play`, `player:comintern`, `nation:ccp` | 1 each | an ordinary action in play, the Comintern choosing for the CCP |
| `kind:movement_route` | 1 | a movement |
| `parameter:combat`, `parameter:mode`, `parameter:path`, `parameter:unit` | 1 each | it has these four details |
| `unit:0_source:ccp:mountain_infantry` | 1 | the unit that acts is a CCP mountain infantry |
| `unit_stat:0_source:count` | 1 | one unit |
| `unit_stat:0_source:move_1` | 1 | with 1 movement point left |
| `unit_zone:0_source:land_china_shensi` | 1 | standing in Shensi |
| `unit_turn_origin:0_source:land_china_shensi` | 1 | where it started the turn |
| `unit_rank:0_source:0` | 1 | the first of the identical mountain infantry there |
| `zone:1_path:land_china_shensi`, `zone:1_path:land_china_hopeh` | 1 each | its path goes through Shensi and Hopeh |
| `list_length:path` | 2 | the path has 2 zones |
| `value:mode:ordinary` | 1 | ordinary movement |
| `true:combat` | 1 | it starts a combat |

Ending the phase has only the four feature values every action has:
`schedule:play`, `player:comintern`, `nation:ccp` and `kind:end_phase`.

**Zones in an action's features.** A zone feature belongs to its zone's feature
vector, so a zone feature never names its zone. An action involves several
zones, so an action feature about a zone names it inside the feature, as in
`zone:1_path:land_china_hopeh`. The parts `0_source` and `1_path` are *roles*:
they say whether a detail names what acts, the route, or what the action acts on
([details](network_input.md#roles)).

**An action's zones.** Each action also names up to three places on the board:
its *source zone*, the zone it starts from; its *target zone*, the zone it acts
on; and its *path zones* (`action_source`, `action_target` and `path_zone` in the
code). The attack on Hopeh has Shensi as its source zone, Hopeh as its target
zone and Shensi and Hopeh as its path zones; ending the phase names no zone.
Through its zones the network reads those zones' descriptions together with the
action's own feature values
([section 6.8](#68-the-action-probabilities)).

### 5.5 Static features

Some facts never change during a game, so they come with the input layout once,
not with each decision. They are the *static features*:

- **39 static features per zone,** such as terrain, production value, capitals,
  victory cities, original owners and home countries. Shensi's: it is land, worth
  2 IPP, mountainous, originally the CCP's, and part of the CCP's and the KMT's
  home countries; its other 33 static features are 0.
- **22 static features per border.** The map has 80 borders, each counted in both
  directions: 160 *directed borders*. The border from Shensi to Hopeh is land to
  land, crosses a river, carries a railway connection and is passable.

The *layout version*, now `campaign-zone-v1-9e192fe5c085f13e`, is a hash of every
feature name and every static feature. A network refuses inputs of another
layout, and a training run cannot resume across a layout change.

### 5.6 More detail: how the encoder builds the input

The encoder reads the engine's memory directly; no text is written or parsed.
The engine holds zones, nations, unit types, facility types and technologies
as numbers, and each one's number is its index in the encoder's list of its
kind ([names held as numbers](../engine/names.md)). Marks are numbered too, but
the encoder asks about them through its own lists of their names. Everything
else it identifies by name (battle notes, an action's details), so the encoder
translates those names into feature numbers through fixed lists. Encoding costs
about 0.17 ms per decision, about 4% of a game process's work.

[The network's input](network_input.md) explains the feature families, the roles,
how each kind of detail becomes feature values, how the lists of names are kept
complete, which features were removed as impossible, and why the engine works
with names.

## 6. Inside a network, brick by brick

This section opens the box of [section 3](#3-what-a-network-gives-at-a-decision).
It builds a network from small parts and shows each on decision 612, with the
Comintern's network after its first network update, the network that faced that
decision. A network's size is written width × number of message-passing layers,
both explained below: 64×2 here and in the Mac profile's measurements
(section 9.2), 256×8 in the night run of 2 November.
Which plays better, and how big a network this game needs, is
[open](#how-big-should-the-network-and-the-search-be).

In the usual picture of a neural network, the feature vectors of section 5 are
its *input layer*, and linear layers follow. Section 6.2 defines a linear layer,
and section 6.3 shows the first one, the *embedding layer*, which reads the
feature values. Nothing else stands between the feature values and the network.
The embedding layer turns each feature vector into a vector of its own, and
section 6.3 ends with a plan of how the later layers combine those vectors;
section 6.9 draws the whole network.

### 6.1 Vectors

A *vector* is a list of numbers. Inside the network, every zone, the state as a
whole and every legal action is described by a vector of 64 numbers, the
network's *width*. At decision 612, Shensi's vector begins −0.294, 1.957,
−1.422, −0.203, and goes on to 64 numbers ([section 6.4](#64-a-zones-vector)
derives them).

A vector is the network's own description of its zone, of the state or of its
action: no number in it has a meaning chosen by hand. The network computes every
vector from the feature values of section 5 and its parameters, and training
(section 8) adjusts the parameters until the vectors are useful for predicting
values and good actions.

### 6.2 Linear layers

A *linear layer* turns a vector of $n$ numbers into a vector of $m$ numbers: it
multiplies it by a learned matrix of $m \times n$ numbers, its *weights*, adds a
learned vector of $m$ numbers, its *bias*, and most linear layers are then
followed by a fixed *activation function*, GELU, which bends each result. A toy
layer with 3 inputs, 1, 2 and 3, and 2 outputs, $y_1$ and $y_2$, whose weights
are 0.5, 0.2 and 0.1, with bias 0.1, for the first output, and 0.1, 0.3 and
−0.4, with bias 0, for the second:

$$
y_1 = \operatorname{GELU}(0.5 \times 1 + 0.2 \times 2 + 0.1 \times 3 + 0.1) = \operatorname{GELU}(1.3) \approx 1.17
$$

$$
y_2 = \operatorname{GELU}(0.1 \times 1 + 0.3 \times 2 - 0.4 \times 3 + 0) = \operatorname{GELU}(-0.5) \approx -0.15
$$

The figure draws this layer the usual way, as Sutton and Barto do in
*Reinforcement Learning: An Introduction* (2nd edition, section 9.7): each input
and each output is a *neuron* (the book names it a unit), every input neuron has a
*connection* to every output neuron, and every connection carries one weight.

![The toy layer drawn as neurons and connections. Left: three input neurons hold 1, 2 and 3, and two output neurons are y1 and y2. Every input is connected to every output, and each connection carries one learned weight: from input 1, 0.5 to y1 and 0.1 to y2; from input 2, 0.2 and 0.3; from input 3, 0.1 and −0.4. With the biases 0.1 and 0, y1 adds up to 1.3, which GELU turns into 1.17, and y2 to −0.5, which becomes −0.15. Right: the same layer read input by input. The weights that leave one input are its embedding: input 1's embedding is (0.5, 0.1), input 2's (0.2, 0.3) and input 3's (0.1, −0.4). 1 × (0.5, 0.1) + 2 × (0.2, 0.3) + 3 × (0.1, −0.4) + (0.1, 0) = (1.3, −0.5) before the activation function. An input of 0 adds nothing, so its embedding can be skipped.](figures/linear_layer.svg)

**An embedding: the weights that leave one input.** Read by input instead of by
output, the layer is a sum of vectors, one per input. The weights on the
connections that leave one input neuron, one for each output, form that input's
*embedding*: input 1's embedding is (0.5, 0.1). (The name is the usual one where
the inputs are features that are mostly 0, as in section 6.3.) Before the
activation function, the outputs are each input times its embedding, added up,
plus the bias:

$$
(1.3, -0.5) = 1 \times (0.5, 0.1) + 2 \times (0.2, 0.3) + 3 \times (0.1, -0.4) + (0.1, 0)
$$

An input of 0 adds nothing, so a layer can skip the embeddings of its zero
inputs. The network's embedding layer, in section 6.3, has almost only such
inputs.

**The activation function.** GELU multiplies a number by the chance that a
standard normal variable falls below it, $\operatorname{GELU}(x) = x \Phi(x)$:
large positive numbers pass almost unchanged and negative ones are squashed
toward 0. Without such functions any stack of linear layers would amount to a
single multiplication and could only add effects up.

A layer's weights and biases are parameters, adjusted by training (section 8).
When a layer reads several vectors, they are first joined end to end into one:
three vectors of 64 numbers make one of 192.

**Layer normalization** rescales a vector's numbers to an average of 0 and a
spread (standard deviation) of 1, then multiplies each by a learned number and
adds another. It keeps vectors on a common scale, whatever went into them.

### 6.3 The embedding layer: embeddings and embedding tables

**The input layer.** A zone's feature vector (section 5.3) is the input layer for
that zone: one input neuron for each of the 42,532 zone features. An input
neuron holds its feature value after a fixed scaling, explained below, which
turns a feature value of 1 into 0.69 and leaves 0 at 0. The *embedding layer*,
the network's first linear layer, connects every input neuron to each of 64
output neurons, the 64 places of a vector; as the code computes it, it has no
bias and no activation function. Its 64 outputs are the first part of the zone's
vector, to which section 6.4 adds two more.

![Decision 612, the Comintern's network after one network update. Left, the input layer: Shensi's feature vector, one input neuron per zone feature, 42,532 in all, each holding its feature value after a fixed scaling, 0.69 for a feature value of 1 and 0 for a feature value of 0. Shown are features 0 possessor:ccp (0.69), 1 possessor:dadao (0), 14 turn_start_possessor:ccp (0.69), 186 units:ccp:militia (0.69), 188 units:ccp:mountain_infantry (0.69), 304 units:kmt:fighter (0), 9,841 and 9,842, the Comintern militia's count and movement points left (0.69 each), 9,989 and 9,991, the Comintern mountain infantry's count and movement points left (0.69 each), 29,244 rail_to:land_china_hopeh (0.69) and the last, 42,531 battle_order (0). Right, the embedding layer: 64 output neurons, of which outputs 1 to 4 and 64 are shown, with −0.001, 0.137, −0.118, −0.104 and −0.073. Every input neuron has a connection to every output neuron. The connections that leave units:ccp:mountain_infantry carry its embedding, row 188 of the zone embedding table, beginning 0.019, 0.001, −0.030, 0.021. Each output adds up input times weight over its 42,532 connections; the inputs of 0 add nothing, so the output is 0.69 times embedding 0 plus 0.69 times embedding 14 and so on to embedding 29,244, and only 9 embeddings are fetched. In all 42,532 × 64 = 2,722,048 connections, whose weights make up the zone embedding table.](figures/embedding_layer.svg)

**Embeddings and embedding tables.** As in the toy layer, the 64 weights on the
connections that leave one input neuron are that feature's *embedding*. The
embedding layer's weights, stored as a matrix with one row per feature, in
feature order, are an *embedding table*: row $q$ of the table is the embedding of
feature $q$. Each part of the input has its own embedding layer and so its own
embedding table:

| Embedding table | Embeddings | One embedding for each |
| --- | ---: | --- |
| Zone embedding table | 42,532 | zone feature |
| Global embedding table | 4,076 | global feature |
| Action embedding table | 12,627 | action feature |

A feature's number is its embedding's row number: `units:ccp:mountain_infantry`
is zone feature 188, and its embedding is row 188 of the zone embedding table.

**One vector per feature vector.** An embedding layer reads one feature vector at
a time and gives each its own 64 outputs, its own vector. At decision 612 the
input has 43 feature vectors, 37 for the zones, one for the global features and
5 for the legal actions, so the embedding layers give 43 vectors of 64 numbers:
one for each zone, one for the state as a whole and one for each legal action,
not one vector for the whole decision. All 37 zone feature vectors go through the
zone embedding table, with the same weights for every zone, and all 5 action
feature vectors through the action embedding table. In the neurons-and-connections
picture, the Shensi figure above is drawn once for every zone, each time with the
same connections. No embedding layer adds one feature vector's values to
another's (`_bag` in `studies/campaign/neural.py` makes one sum per feature
vector): the vectors meet only in the layers after it, as the plan at the end of
this section shows.

![Decision 612 of the game of 5 November. Left, the input layer: 43 feature vectors, each drawn as a bar with a tick for every non-zero feature value at its column. The zones have 37 feature vectors of 42,532 inputs each, 840 non-zero feature values in all: shown are Shensi with 9, Hopeh 28, Suiyuan 12, Szechwan 2, Tsinghai 13, 31 more zones, and sea zone P14 with 86. The global features are 1 feature vector of 4,076 inputs with 176 non-zero feature values. The legal actions have 5 feature vectors of 12,627 inputs each, 80 non-zero feature values in all: the attacks on Hopeh, Suiyuan, Szechwan and Tsinghai with 19 each, and ending the phase with 4. Middle, the embedding layers: every zone feature vector goes through the zone embedding table, 42,532 embeddings of 64, the same weights for all 37 zones; the global feature vector through the global embedding table, 4,076 embeddings of 64; every action feature vector through the action embedding table, 12,627 embeddings of 64, the same weights for all 5 legal actions. Each feature vector goes through on its own. Right, the outputs: one vector of 64 numbers per feature vector, 43 in all: 37 zone vectors, 1 global vector and 5 action vectors. No embedding layer adds one feature vector to another; the vectors meet only in the layers after it.](figures/embedding_layers.svg)

**Skipping the zeros: an embedding lookup.** Each output adds up all 42,532
inputs, each times its weight, so the 64 outputs together are the sum of every
input times its embedding. An input of 0 adds nothing, and 42,523 of Shensi's
42,532 inputs are 0. So the network fetches only the embeddings of the 9 non-zero
inputs, multiplies each by its input and adds them up. With $x_q$ for the input of
feature $q$ and $e_q$ for its embedding,

$$
\text{output of the embedding layer} = \sum_{q} x_q e_q
$$

where only the features with $x_q \neq 0$ count. Multiplying Shensi's whole
feature vector of 42,532 inputs by the zone embedding table, as a matrix
multiplication, gives the same 64 numbers (checked: equal to within
$3 \times 10^{-8}$, float rounding), but it would multiply 42,523 zeros. Fetching
only the embeddings of the non-zero features is an *embedding lookup*. The
network's numbers live in PyTorch, a library that keeps them in arrays and does
their arithmetic, and the network's code works by *PyTorch calls*, each applying
one function to whole arrays at once
([section 9.2](#92-running-training-on-the-mac) lists the PyTorch calls of a
message-passing layer and what they cost). One PyTorch call, `embedding_bag`,
does the embedding lookup for every zone at once: it fetches each embedding of a
non-zero feature, multiplies it by its input and adds it to its zone's sum,
without first copying the fetched embeddings into a temporary array (`_bag` in
`studies/campaign/neural.py`, since 12 November;
[record](../archive/records/coordinator_lookups_2026_11_12.md)). The embedding
table's view of the same layer, with real embeddings:

![Top: one embedding, the 64 learned numbers the Comintern's network keeps for the zone feature units:ccp:mountain_infantry, row 188 of its zone embedding table after one network update, drawn as 64 coloured cells, blue for negative and red for positive numbers up to ±0.15; its first numbers are 0.019, 0.001, −0.030, 0.021, −0.007, 0.018, −0.015 and −0.028. Left: the zone embedding table, one row per zone feature, 42,532 embeddings of 64 numbers; shown with their row numbers are rows 0 to 3 (possessor:ccp, possessor:dadao, possessor:japan, possessor:kmt), 14 (turn_start_possessor:ccp), 186 and 188 (units:ccp:militia and units:ccp:mountain_infantry), 304 (units:kmt:fighter, still all zeros because no kept training sample had a KMT fighter), 9,841, 9,842, 9,989 and 9,991 (Comintern militia and mountain infantry counts and movement points left), 29,244 (rail_to:land_china_hopeh) and the last, 42,531 (battle_order). The 9 embeddings Shensi's feature values pick are highlighted. A fresh network's embeddings are all zeros; after one network update 1,840 have moved. Right: Shensi's 9 feature values, each 1, enter as ln 2 ≈ 0.69 each, so Shensi's vector starts as 0.69 times embedding 0 plus 0.69 times embedding 14 and so on to embedding 29,244; the sum's first numbers are −0.001, 0.137, −0.118 and −0.104. The network fetches only these 9 embeddings: Shensi's other 42,523 feature values are 0.](figures/embedding_table.svg)

**Feature scaling.** An input neuron holds not its feature value $a$ but a fixed
formula of it, written by hand, not learned (`_signed_log` in
`studies/campaign/features.py`):

$$
x = \operatorname{sign}(a) \ln(1 + |a|)
$$

where $\ln$ is the natural logarithm. Feature values are counts and yes-or-no
flags, so in practice $a \ge 0$ and the input is $\ln(1 + a)$; no feature value
was negative in 60 decisions drawn at random from a game, and the sign only keeps
the formula defined for negative numbers:

| Feature value $a$ | Input $x$ | Compared with a feature value of 1 |
| ---: | ---: | ---: |
| 1 | $\ln 2 \approx 0.69$ | 1 |
| 2 | $\ln 3 \approx 1.10$ | 1.58 |
| 3 | $\ln 4 \approx 1.39$ | 2 |
| 10 | $\ln 11 \approx 2.40$ | 3.46 |
| 100 | $\ln 101 \approx 4.62$ | 6.66 |

Larger counts matter more but not in proportion: ten militia add their embedding
3.46 times as strongly as one, not ten times, so a big stack does not drown out
everything else in its zone. That a feature value of 1 counts 0.69 rather than 1
makes no difference, because the embedding it multiplies is learned and training
can make it as large as it needs; the formula fixes only how counts compare with
one another. Scaling inputs to comparable sizes before a network is common
practice; this formula was chosen, not compared with others
([open question](#how-should-a-count-count)).

**Shensi's sum, in numbers.** Each of Shensi's feature values is 1, so each input
is 0.69. The first 4 of the 64 numbers of each embedding, from the Comintern's
network after one network update:

| Feature | Its embedding's first 4 numbers | × 0.69 |
| --- | --- | --- |
| `possessor:ccp` | −0.006, −0.002, −0.028, −0.010 | −0.004, −0.002, −0.020, −0.007 |
| `turn_start_possessor:ccp` | −0.006, −0.003, −0.027, −0.009 | −0.004, −0.002, −0.019, −0.007 |
| `units:ccp:militia` | −0.016, 0.058, −0.030, −0.042 | −0.011, 0.040, −0.021, −0.029 |
| `units:ccp:mountain_infantry` | 0.019, 0.001, −0.030, 0.021 | 0.013, 0.001, −0.021, 0.014 |
| `unit_stat:comintern:militia:count` | −0.016, 0.047, −0.028, −0.048 | −0.011, 0.033, −0.019, −0.034 |
| `unit_stat:comintern:militia:move_0` | −0.016, 0.047, −0.028, −0.048 | −0.011, 0.033, −0.019, −0.034 |
| `unit_stat:comintern:mountain_infantry:count` | 0.019, 0.001, −0.030, 0.021 | 0.013, 0.001, −0.021, 0.014 |
| `unit_stat:comintern:mountain_infantry:move_1` | 0.012, 0.066, 0.004, −0.038 | 0.008, 0.046, 0.003, −0.027 |
| `rail_to:land_china_hopeh` | 0.008, −0.017, 0.025, 0.005 | 0.006, −0.012, 0.018, 0.003 |
| **Sum** | | **−0.001, 0.137, −0.118, −0.104** |

Two pairs of embeddings are identical, the militia's count and movement points left, and
the mountain infantry's `units` and `count` features: in every training sample so
far these features had non-zero values together, so training moved them alike
([section 8.5](#85-which-numbers-a-training-step-moves)).

**An embedding belongs to a feature, not to a zone.** `units:ccp:mountain_infantry`
has one embedding, the network's own description, in 64 numbers, of "a CCP
mountain infantry is here", added in whichever zone that is true. No number in an
embedding has a meaning chosen by hand. Nor is an embedding computed from the
feature value: it stays the same from state to state until training changes it,
and the feature value only sets how strongly it is added.

**Each of an embedding's numbers is one parameter,** so the zone embedding table
alone holds 42,532 × 64 = 2,722,048 parameters, and the three embedding tables
3.79 million of the network's 3.92 million.

**Embeddings start at zero** (since 3 November 2026), and training moves an
embedding only when it trains on training samples in which the embedding's
feature has a non-zero value
([section 8.5](#85-which-numbers-a-training-step-moves)). After the first network
update of the 5 November run, 1,840 of the zone embedding table's 42,532
embeddings had moved; the embedding of `units:kmt:fighter` was still all zeros,
because no kept training sample had a KMT fighter. Starting at zero means a
feature that training has never reached adds nothing, instead of a random
embedding added at full strength. In a test on a fixed set of saved training
samples it gave a slightly lower value error on training samples held out of
training (0.0076 against 0.0081) and the same policy loss
([section 8.1](#81-the-loss)): no harm shown, not a strength gain.

Computing an embedding layer by adding up the embeddings of its non-zero inputs
is common wherever inputs are mostly 0; chess programs compute their first layer
the same way
([section 6.10](#610-more-detail-how-other-game-networks-read-their-input)).

**What the 43 vectors become.** Each of the 43 vectors so far describes one zone,
the state as a whole or one legal action, from that feature vector alone. The
layers after the embedding layer bring them together, in this order (`_forward`
in `studies/campaign/neural.py`):

| Part of the network | What it reads | What it gives at decision 612 | Section |
| --- | --- | --- | --- |
| Zone vectors | each zone's embedding-layer output, its identity embedding and its static features | 37 zone vectors, one per zone | [6.4](#64-a-zones-vector) |
| Global and action vectors | the global features' and each legal action's embedding-layer output | 1 global vector and 5 action vectors | [6.5](#65-the-global-vector-and-the-action-vectors) |
| Two message-passing layers | each zone's vector, its neighbours' vectors along the borders and the global vector; for the global vector, itself and the average zone vector | 37 zone vectors and 1 global vector, each now informed by the others | [6.6](#66-message-passing-layers-messages-along-the-borders) |
| Summary and values | the global vector, and the average and the largest of the 37 zone vectors | 1 summary vector, then 3 values | [6.7](#67-the-values) |
| Action probabilities | each action vector, the vectors of the action's zones, and the summary | 5 logits, then 5 probabilities | [6.8](#68-the-action-probabilities) |

The action vectors take no part in the message-passing layers or the values: an
action meets the board only in the last part, through its zones, so the values do
not depend on which actions are legal. Section 6.9 draws the whole plan in one
figure.

### 6.4 A zone's vector

A zone's vector, before the borders come in, adds three things and normalizes
the result:

1. **the embedding layer's output:** the embeddings of the zone's non-zero
   feature values, each times its input (section 6.3);
2. **the zone's identity embedding:** 64 learned numbers for each of the 37
   zones, so the network can tell zones apart. Unlike the embedding tables'
   embeddings, these start random;
3. **its 39 static features** (section 5.5), turned into 64 numbers by a linear
   layer without an activation function.

Then layer normalization rescales the sum. For Shensi at decision 612, the first 4
of the 64 numbers:

| Part | First 4 numbers |
| --- | --- |
| 1. The embedding layer: 9 embeddings, each times 0.69 | −0.001, 0.137, −0.118, −0.104 |
| 2. Shensi's identity embedding | 0.204, 1.874, −1.609, 0.437 |
| 3. Its static features, through a linear layer | −0.449, −0.205, 0.425, −0.504 |
| Total | −0.246, 1.807, −1.302, −0.171 |
| After layer normalization: Shensi's vector | −0.294, 1.957, −1.422, −0.203 |

**Still one layer, in the usual picture.** The identity embedding is the
embedding of one more kind of input: 37 input neurons that say which zone this
is, 1 for Shensi and 0 for the other 36. The static features' layer adds 39 input
neurons, one per static feature, and a bias. So everything before the layer
normalization is one linear layer with 42,532 + 37 + 39 = 42,608 inputs, which
the code computes in three pieces.

After one network update the feature values are still a small part of it:
measured over all 64 numbers, the embedding layer's output is about a sixth the
size of Shensi's identity embedding (1.3 against 8.0, root of the sum of squares)
and smaller than its static features' part (2.1). So this early network's
description of Shensi still says mostly "this is Shensi", whatever stands there.
Inferred: that is part of why young networks rate different states much alike.

**One embedding table serves every zone.** `units:ccp:mountain_infantry` has one
embedding, added wherever CCP mountain infantry stand, so what the network learns
about mountain infantry in Shensi applies in Hopeh too. It does not carry across
combinations: KMT infantry has a separate embedding
([open question](#one-embedding-per-combination-or-embeddings-built-from-parts)).

Layer normalization also keeps a busy zone from dominating: sea zone P14, with 86
non-zero feature values at decision 612, does not get a vector many times larger
than Szechwan, with 2.

### 6.5 The global vector and the action vectors

**The global vector** is built the same way from the global feature values and
the global embedding table: its embedding layer adds up the embeddings of its 176
non-zero feature values at decision 612, each times its input, then layer
normalization. It has no identity embedding and no static features.

**An action vector** is built the same way from the action's own feature values
and the action embedding table: 19 embeddings for each attack at decision 612 and
4 for ending the phase, then layer normalization.

The forward pass of each inference batch (section 9.2) does these embedding
lookups for every zone of every state, every state's global features and every
legal action at once: about 6,000 embeddings for an inference batch of four
states ([record](../archive/records/coordinator_lookups_2026_11_04.md)).

### 6.6 Message-passing layers: messages along the borders

A zone vector so far describes only its own zone. *Message-passing layers* let
each zone hear from its neighbours along the 160 directed borders, as in a graph
neural network whose nodes are the zones and whose edges are the borders. In each
message-passing layer:

1. every zone sends a message along each border leaving it: its own vector
   through a linear layer, plus the border's 22 static features, such as a river,
   a railway or a narrow crossing, through another, the sum passed through the
   activation function;
2. every zone averages the messages it receives;
3. every zone adds a *zone correction* to its vector, computed by a linear layer
   (with its activation function and a layer normalization) from its old vector,
   that average and the global vector; then the global vector adds a *global
   correction* computed the same way from itself and the average zone vector.

With $h_z$ for zone $z$'s vector, $u$ for the global vector and $f_{s \to t}$ for
the static features of the border from $s$ to $t$, the message along that border
is

$$
\text{message}_{s \to t} = \operatorname{GELU}\big(\text{layer}_1(h_s) + \text{layer}_2(f_{s \to t})\big)
$$

and then every zone $t$, and after them the global vector, change by

$$
h_t \leftarrow h_t + \text{layer}_3\big(h_t,\ \text{average of the messages into } t,\ u\big)
$$

$$
u \leftarrow u + \text{layer}_4\big(u,\ \text{average of all } h_z\big)
$$

Every zone sends at the same time, so information spreads one border per layer:

![Two panels of a schematic map around Shensi. Message-passing layer 1: every zone hears from its neighbours at the same time: arrows run into Shensi from its four neighbours, Hopeh, Suiyuan, Szechwan and Tsinghai, and into those four from the 12 zones beyond them. After it, Shensi's vector reflects its 4 neighbours. Message-passing layer 2: Shensi hears its neighbours again, and their vectors now carry what they heard from the zones beyond, so after it Shensi's vector also reflects those 12 zones. Every zone sends along all its borders at once, so 2 layers reach zones up to 2 borders away.](figures/message_layers.svg)

After the first message-passing layer Shensi's vector reflects what its four
neighbours hold; after the second, also the 12 zones two borders away, such as
Beiping beyond Hopeh. In general, after $k$ message-passing layers a zone's
vector reflects zones up to $k$ borders away, and through the global vector, from
the second message-passing layer on, the average of all zones. Each
message-passing layer has its own linear layers; a 64×2 network has 2
message-passing layers, its *network depth*.

### 6.7 The values

A linear layer (with its activation function and a layer normalization) combines
the global vector with the average and the largest value, number by number, of
the 37 zone vectors after the message-passing layers into one *summary vector* of
the state. Two more linear layers, the *value head*, turn the summary vector into
three numbers: the predicted final scores of the Axis, the Allies and the
Comintern, in hundreds of points. At decision 612 they were 0.251, −0.424 and
−1.024: +25.1, −42.4 and −102.4 (section 3).

### 6.8 The action probabilities

**A logit for each action.** Each action vector is joined with three zone
vectors, taken after the message-passing layers, through the action's zones
(section 5.4): its source zone, its target zone and the average of its path
zones. An action that names no zone, such as ending the phase, gets a learned "no
zone" vector for the first two and zeros for the path. A linear layer turns these
4 × 64 numbers into one combined vector of the action, and two more, the *policy
head*, turn that, together with the summary vector, into one number, the action's
*logit*: a raw preference, which a softmax turns into a probability. So the
attack on Hopeh reads its own 19 feature values ("a CCP mountain infantry with 1
movement point left, in Shensi, attacking along Shensi–Hopeh") together with
Shensi's vector as its source zone, Hopeh's as its target zone, and the average
of both as its path.

**From logits to probabilities: softmax.** A list of logits becomes probabilities
that add up to 1 by a *softmax*: each logit $s_i$ becomes

$$
p_i = \frac{e^{s_i}}{\sum_j e^{s_j}}
$$

so a higher logit means a higher probability, and only differences between
logits matter.

**A hierarchical softmax.** The softmax is not taken over all legal actions at
once. The legal actions are grouped four times over, in four *levels*: by kind,
then within a kind by what acts, then by how it travels, then by what it acts on.
At each level a small learned head gives every group a logit, from the summary
vector and the average combined vector of the group's actions, and a softmax over
the groups under one parent turns those logits into probabilities that add up to
1. Last, a softmax over the actions' own logits, among the actions of one final
group, picks the exact action. An action's probability is the product of the
probabilities along its branch of the tree of groups (`_readout` in
`studies/campaign/neural.py`):

![A tree of groups from decision 612 through the levels kind, what acts, how it travels, what it acts on and the action. Kind: a movement with probability 0.469, or ending the phase with 0.531. Under a movement, what acts: the mountain infantry, probability 1, the only unit that can move. How it travels: to Hopeh 0.219, to Suiyuan 0.204, to Szechwan 0.184, to Tsinghai 0.394. What it acts on: no split, probability 1. The actions' probabilities, the products along their paths: 0.102, 0.096, 0.086 and 0.185 for the four attacks, and 0.531 for ending the phase, whose later levels have one branch each.](figures/hierarchical_softmax.svg)

These four attacks name their destination only as the last zone of their path,
not in a detail of their own, so "what it acts on" does not split them, and
their destinations separate them at "how it travels". The action's target zone
(section 5.4) does use the path's last zone, so the network still reads Hopeh's
vector as the zone the attack acts on ([details](network_input.md#roles)).

At a larger decision the levels split more: at the CCP's first Combat Movement
decision of one game, with 13 legal actions, three units could each move to four
zones, so "what acts" had three branches under "a movement"
([the input page](network_input.md#2-three-parts) describes that decision).
Every legal action gets a probability; none is padded, merged or dropped. Which
details count as "what acts" and so on comes from the roles explained in
[The network's input](network_input.md#roles).

### 6.9 The whole network

All the bricks together, for decision 612:

![For decision 612 at width 64: the 37 zone feature vectors, one per zone, with 840 non-zero feature values in all, go through the zone embedding table of 42,532 embeddings, the embedding layer, each on its own, to 37 zone vectors; the global feature vector, with 176 non-zero feature values, through the global embedding table of 4,076 embeddings to one global vector; the 5 action feature vectors, with 80 non-zero feature values in all, through the action embedding table of 12,627 embeddings to 5 action vectors, one per legal action. Two message-passing layers update every zone vector from its neighbours along the 160 directed borders and from the global vector, and the global vector from the average zone. A linear layer turns the global vector and the zones' mean and maximum into a summary vector, and the value head turns that into three values, one per alliance. Each action vector is joined with the vectors of its source zone, its target zone and its path zones; with the summary vector, the policy head turns it into the action's logit, giving 5 logits and 5 probabilities, built by a hierarchical softmax.](figures/network_structure.svg)

**Its size.** A 64×2 network has 3,924,424 parameters. Most, 3.79 million or 97%,
are the embeddings of the three embedding tables; the other layers hold the rest.
At 256×8 there are 19.58 million, 77% of them embeddings, since wider layers
weigh more. A decision reads only the embeddings of its non-zero features: at
decision 612, 1,096 embedding lookups (840 + 176 + 80) of 581 different
embeddings, out of 59,235.

**A fresh network gives every state the same values.** Its embeddings are all
zero, so every feature value adds nothing: each zone's vector is only its identity
embedding and its static features, the same in every state, and so are the global
vector, the summary vector and the values. On 5 November a fresh 64×2 network
gave the same three values at four different states of a game
([record](../archive/records/training_sample_2026_11_05.md#a-fresh-network-gives-every-position-the-same-values)).
Its action probabilities still differ between actions, because an action's
combined vector also carries the vectors of its zones.

Measurements of this network are in the
[zone network record](../archive/records/zone_network_2026_11_02.md).

### 6.10 More detail: how other game networks read their input

Reading a decision through an embedding layer is the usual way to read sparse
inputs. The shape of the network after it follows published networks for games
played on maps rather than AlphaZero's grids:

| Network | Its input | Its first linear layer | Its action output |
| --- | --- | --- | --- |
| AlphaGo Zero, for Go | 17 grids of 19 × 19 numbers, each 0 or 1 | a convolution: at every point, the same learned numbers for the facts at and around that point | a fixed list of 362: one per point and one for passing |
| Stockfish's NNUE, for chess | for each side's view, 40,960 numbers, at most 30 of them 1 (HalfKP) | adds up the weights that leave its non-zero inputs | none: it gives a value only |
| DipNet, for Diplomacy | the features of each of the board's 81 locations | a graph convolution along the map's adjacency | one order per location in turn, invalid orders masked |
| This network | 42,532 zone features per zone, 4,076 global features and 12,627 action features per legal action, almost all 0 | adds up the embeddings of its non-zero inputs, with one embedding table for every zone | one logit per legal action, from the action's own vector |

**The embedding layer is the usual first layer.** Adding up the weights of the
few non-zero inputs, instead of multiplying them all, is how a layer is computed
wherever inputs are mostly 0. Sutton and Barto describe it for linear value
functions over binary features, such as tile coding (section 9.5.4). Stockfish's
NNUE computes its first layer this way and, after a move, adds and subtracts
only the weights of the inputs that changed
([nnue-pytorch documentation](https://github.com/official-stockfish/nnue-pytorch/blob/master/docs/nnue.md)).
AlphaGo Zero's first convolution does the same on a grid: its inputs are 0 or 1,
so at each point it adds up learned numbers for the facts at and around that
point, with the same numbers at every point, as one embedding table serves every
zone here (Sutton and Barto, section 16.6.2, describe its input).

**Why not a grid.** The 37 zones are not a grid: each has its own neighbours,
along 160 directed borders, so messages travel along borders (section 6.6)
rather than across a grid. A zone can have values for any of 42,532 features,
where a point of a Go board has 17. And the legal actions are no fixed list:
decision 612 has 5, others over a hundred (section 4.7), and their kinds change
with the phase. So the network gives every legal action a logit from its own
vector (section 6.8) instead of keeping one output for each possible action.

**Networks for games on maps.** Networks for games on an irregular map, with many
kinds of unit and a changing list of orders, are built like this one: a vector
for each place or unit, layers that mix the vectors along the map's connections
or by attention, and a score for each order from vectors of its own. DipNet, a
network for the board game Diplomacy, is a published example
([Paquette et al. 2019](https://arxiv.org/abs/1909.02128)): its 16
graph-convolution layers mix the locations' vectors along the map, and it writes
the orders one location at a time. Layers like the message-passing layers of
section 6.6 make a *graph neural network*, in which the global vector plays the
part of a vector shared by the whole graph
([Battaglia et al. 2018](https://arxiv.org/abs/1806.01261)).

**This project's own choices.** Three choices are this project's own and have not
been compared with alternatives: one embedding per named combination of facts,
such as one for CCP mountain infantry and another for KMT infantry
([open question](#one-embedding-per-combination-or-embeddings-built-from-parts));
the logarithm that scales a feature value
([open question](#how-should-a-count-count)); and the grouping of legal actions
into the levels of section 6.8.

## 7. Self-play and training samples

### 7.1 A training iteration's games

Training learns from self-play in *training iterations*. In the Mac profile
self-play never stops: 24 games are in play at a time, in 6 game processes of 4
games each ([section 9.2](#92-running-training-on-the-mac)), and a game thread
that finishes a game starts the next at once. After every 24 games that end, a
network update trains the network on their training samples and older ones
(section 8.4), beside the games, which go on; when it is done, every game takes
up the new network at once ([section 9.1](#91-the-training-loop)). A training
iteration is those 24 games and their network update. At every decision the
alliance to act searches (section 4) and plays the action drawn from the visit
shares. Training can also alternate between playing and learning, as the Windows
profile does: a training iteration's 24 games then start together with the
network held fixed, and the network update runs when the last of them has
ended. The code and the dated records name a training iteration's games a
*batch* (as in the flag `--transitions-per-batch`); this document keeps "batch"
for the inference batches of section 9.2.

The settings in sections 7 and 8 are those of the Mac training command in the
[campaign learning guide](../../studies/campaign/README.md#training-on-the-mac),
which names them the speed test's settings, not tuned values. The worked
examples come from the 5 November run, when a training iteration played 32
games, in 8 game processes, and a network update was 700 training steps. Today a
network update is 525 training steps, which draws each kept training sample as
often from training iterations of 24 games (section 8.7).

**Which decisions are kept.** A random 5% of each game's decisions, because a
game's thousand-odd states are close to one another. A decision with only one
legal action, played without a search, can be kept too: its visit share is 1, so
it teaches only the values. Every game is played to its end. A guard,
`--transitions-per-batch`, stops a game that runs far too long, 20,000 states in
the Mac command against about 1,500 in a normal game. Then the run stops, to be
resumed with a higher guard (`--extend-episode-budget`), and the game is
discarded without training samples. In self-play that never stops, the other
games then in play are lost too, and the resumed run starts new ones; in
alternating training iterations, the training iteration's games are discarded
and played again from the same seeds.

### 7.2 What a training sample stores

A *training sample* is one decision of a self-play game, saved so that training
can show it to the network again and compare its outputs with better ones. It
stores four things (`_decide` and `play_episode` in `studies/campaign/learning.py`):

| Part | What it stores | What training does with it |
| --- | --- | --- |
| 1. What the network read | The decision's input (section 5): the non-zero zone, global and action feature values, and each legal action's zones. It is not a copy of the game. | Shows the decision to the network again. |
| 2. Who chose | The alliance to act. | The input names it already; with a network for each alliance, only that alliance's network learns action probabilities from the training sample, and all three learn values from it. |
| 3. How the search split its simulations | Each legal action's visit share (section 4.5). | The *policy target*: the action probabilities the network should give. |
| 4. How the game ended | The three alliances' final scores, written into every training sample of the game when it ends. | The *value target*: the values the network should predict, the final scores divided by 100. |

**Decision 612, as a training sample.** The game of decision 612 was played for
this example and kept every decision
([record](../archive/records/training_sample_2026_11_05.md)); this is its training
sample:

![One real training sample, from game round 5 of a self-play game: the Comintern chooses the CCP's Combat Movement. 1, what the network read: 840 non-zero zone feature values from all 37 zones, 176 global feature values, 80 action feature values for the five legal actions, and each action's zones, 12 KB in all; in Hopeh, for example, possessor:kmt = 1 and project:kmt:major_shipyard = 1. 2, who chose: the Comintern, for the CCP. 3, how the search split its 64 simulations, stored as visit shares: the mountain infantry in Shensi attacking Hopeh 36 visits, visit share 0.56, the network's own probability 0.10, the action played; attacking Suiyuan 2, 0.03, 0.10; attacking Szechwan 5, 0.08, 0.09; attacking Tsinghai 9, 0.14, 0.18; ending Combat Movement 12, 0.19, 0.53. 4, how the game ended, stored as the value target: Axis +49.0, the network predicted +25.1; Allies −63.8, predicted −42.4; Comintern −106.2, predicted −102.4.](figures/training_sample.svg)

Part 1 is the input of section 5, 12 KB in all. Part 3 is the search of
[section 4.6](#46-a-real-search-decision-612): its visit shares differ most from
the network's probabilities for the attack on Hopeh and for ending Combat
Movement, both because the search found the attack better than the rest. Part 4
is the game's end: Axis +49.0, Allies −63.8 and Comintern −106.2, which every
training sample of the game stores. The record counts 191 non-zero global feature
values, not 176: when it was made, twelve more said that a nation's income had
been worked out and three that Japan, the KMT and the CCP keep a treasury. Both
are true of every state, and those features have since been removed.

### 7.3 Why these targets

**The visit shares.** The network answers in one look. The search also asks it
about every state its 64 simulations reach, and returns most often to the
actions whose continuations score best for the alliance choosing (section 4). At
decision 612, the one look did not see that the attack would take Hopeh; the
simulations that played through the battle did. Where the search finds a
difference, its split is therefore a better judgment than the network's first
guess. Training moves the network's probabilities toward the split, so the
network's next first guesses come closer to what a search would conclude, and
the searches after the next network update start from them.

**The final scores** are what really happened after the decision, so they teach
the network to predict how a state will end.

**In a run's first training iteration** the visit shares carry little. A fresh
network gives every state the same values ([section 6.9](#69-the-whole-network)),
so a search in the first training iteration splits its simulations by the
network's arbitrary first guesses, the exploration noise and the rare game ends
it reaches; only the final scores carry information. From the second training
iteration on, the values differ between states.

## 8. Training the network

Training changes a network's parameters so that, on the saved training samples,
its action probabilities come closer to the visit shares and its values closer
to the final scores. This section builds that from its parts: a number that
measures how far off the network is, the *loss*; the direction that lowers it,
the *gradient*; the rule that changes the parameters once, an *Adam step*; and
the schedule of those changes, the *training steps* of a *network update*.

### 8.1 The loss

The loss has two parts. On one training sample, with the network's values $v_k$,
the final scores divided by 100 as $z_k$, the visit shares $\pi_m$ and the
network's probabilities $p_m$:

- **the value loss** is the average squared error of the three values:

$$
L_{\text{value}} = \frac{1}{3} \sum_{k=1}^{3} \left( v_k - z_k \right)^2
$$

- **the policy loss** is the *cross-entropy* between the visit shares and the
  probabilities:

$$
L_{\text{policy}} = -\sum_{m} \pi_m \ln p_m
$$

On decision 612's training sample, for the Comintern's network:

| Alliance | Value $v_k$ | Target $z_k$ | Error | Squared |
| --- | ---: | ---: | ---: | ---: |
| Axis | 0.251 | 0.490 | −0.239 | 0.057 |
| Allies | −0.424 | −0.638 | 0.214 | 0.046 |
| Comintern | −1.024 | −1.062 | 0.038 | 0.001 |
| **Value loss, the average** | | | | **0.035** |

| Action | Visit share $\pi_m$ | Probability $p_m$ | Visit share × (−ln probability) |
| --- | ---: | ---: | ---: |
| Shensi → Hopeh | 0.5625 | 0.102 | 1.282 |
| Shensi → Suiyuan | 0.0313 | 0.096 | 0.073 |
| Shensi → Szechwan | 0.0781 | 0.086 | 0.192 |
| Shensi → Tsinghai | 0.1406 | 0.185 | 0.238 |
| End Combat Movement | 0.1875 | 0.531 | 0.119 |
| **Policy loss, the sum** | | | **1.903** |

The cross-entropy is lowest when the probabilities equal the visit shares, here
1.221, the visit shares' own entropy; the gap of 0.682, the *Kullback–Leibler
divergence* (KL divergence) of the probabilities from the visit shares, is what
training can remove on this training sample. Most of the loss comes from the attack on Hopeh,
to which the search gave 0.56 and the network 0.10.

In a training step the two losses are averaged over the training samples of the
training step's minibatch: the value loss over all of them, and the policy loss
over all of them too, since the network serves all three alliances; with a
network for each alliance, a network's policy loss is averaged over those where
its own alliance chose (section 8.4). The training step lowers their sum.

### 8.2 The gradient

A training step nudges each of the network's 3.92 million parameters the way that
lowers the loss. For that, training first works out every parameter's *gradient*
(`loss.backward()`): how fast the loss on the training step's minibatch would
change if that one number were raised a little. A positive gradient means that
raising the number would raise the loss, so it should go down; a negative one,
that it should go up. The larger the gradient, the more the loss responds to that
number.

**An example.** The value head's last layer adds a learned bias to every
Comintern value the network predicts. In the first training step of the
5 November network update, the fresh network predicted the Comintern's final
scores 109 points too high on average on that training step's minibatch, so
raising that bias would have raised the loss further: its gradient was positive,
0.728, and the training step lowered it
([record](../archive/records/adam_steps_2026_11_09.md)).

### 8.3 Adam

The plainest rule, gradient descent, moves every parameter against its
gradient by a fixed multiple of it, the *learning rate*. Its changes then follow
the gradients' sizes, which differ enormously: in the first training step of the
5 November network update, the Comintern network's nonzero gradients ranged from
$4 \times 10^{-17}$ to 171. And a gradient from 32 random training samples is
noisy: it points a little differently in every training step. Training uses Adam
instead (`torch.optim.Adam` in `CampaignLearner._optimizer`), a standard
optimizer built for both problems (Kingma and Ba, *Adam: A Method for Stochastic
Optimization*, 2015). For every parameter it keeps two running averages, both
starting at zero:

- $m$, the average of the parameter's recent gradients: each Adam step keeps 90%
  of it and adds 10% of the new gradient $g$, so it mostly reflects the last ten
  or so training steps;
- $v$, the average of its recent squared gradients: each Adam step keeps 99.9% of
  it and adds 0.1% of the new gradient squared, so its square root is the
  gradient's typical size over roughly the last thousand training steps.

At Adam step number $t$, counted over the whole run, Adam moves the parameter by

$$
\Delta = -\eta \times \frac{\hat m}{\sqrt{\hat v} + \epsilon},
\qquad
\hat m = \frac{m}{1 - 0.9^{t}},
\qquad
\hat v = \frac{v}{1 - 0.999^{t}}
$$

where $\eta$ is the learning rate, 0.001. The divisions by $1 - 0.9^{t}$ and
$1 - 0.999^{t}$ correct the averages for having started at zero, which would
otherwise make them too small in the first Adam steps, and $\epsilon = 10^{-8}$
only keeps the division safe. Apart from the learning rate, these are PyTorch's
defaults.

The fraction cancels the gradient's size and keeps how steadily it points one
way. A parameter whose gradients keep their sign moves about 0.001 per Adam step,
whether they are large or small; one whose gradients keep changing sign has a
small average beside its typical size and moves much less. In the very first
Adam step the corrected averages are the gradient and its size, so every
parameter moves by exactly the learning rate, unless its gradient is so small
that $\epsilon$ counts. **An Adam step**, the optimizer step, is this rule applied
once to every parameter of one network, by `optimizer.step()`. The network has
its own Adam, whose averages carry over from one network update to the next and
are saved in checkpoints, the full saves from which a run can resume; with a
network for each alliance, each of the three networks has its own.

**A real network update, run again**
([record](../archive/records/adam_steps_2026_11_09.md)). Re-running the
5 November network update from that run's fresh networks and its 1,611 training
samples gave exactly the networks that network update had produced. In the first
Adam step, 211,741 of the Comintern network's 221,675 parameters with a nonzero
gradient moved by 0.001, to within 0.00001; the rest had gradients below about
$10^{-6}$, where $\epsilon$ shrinks the change. The bias of section 8.2 shows how
the Adam steps change after that:

| Adam step | Gradient | Average gradient ($\hat m$) | Typical size ($\sqrt{\hat v}$) | Change |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.728 | 0.728 | 0.728 | −0.001000 |
| 2 | 0.322 | 0.514 | 0.563 | −0.000914 |
| 3 | 0.099 | 0.361 | 0.463 | −0.000780 |
| 4 | −0.004 | 0.255 | 0.401 | −0.000635 |
| 5 | −0.066 | 0.176 | 0.360 | −0.000490 |
| 10 | 0.027 | 0.046 | 0.257 | −0.000178 |
| 50 | −0.00006 | 0.003 | 0.115 | −0.000026 |
| 700 | −0.016 | −0.0013 | 0.030 | +0.000044 |

From Adam step 4 on, the gradients pointed now one way, now the other (356 of the
700 were negative), so their average shrank, while the typical size still
remembered the large first gradients: at Adam step 700 the first gradient still
made up 60% of the average squared gradient. The changes shrank accordingly. The
average still leaned the first way, so the bias kept falling until Adam step 39;
over all 700 Adam steps it moved by 0.78 points of predicted final score. The
network's other parameters did most of the correcting: in the first Adam step
each of them with a gradient also moved by 0.001, the way that lowered the loss.
The network's value loss was 0.62 on the first training step's minibatch and
0.0065 on the fourth training step's, after three Adam steps: an error of about
79 points per value, then 8 (root mean square). These are training samples it is
trained on, so this measures fit, not foresight.

### 8.4 One training step, and one network update

**Where training samples wait: the replay buffer.** A training sample is made in
a game process at the moment of its decision, and its final scores are added when
its game ends. The game processes hand their training samples to the main
training process, which adds a game's training samples to its *replay buffer*
when the game ends (in alternating training iterations, once all the games of
the training iteration have ended). The replay buffer is a list of the latest
training samples, at most 8,000, from which the oldest leave first. On 5 November
one training iteration kept 1,611 training samples from 33,062 decisions, so a
full replay buffer holds about the last five training iterations' training
samples
([record](../archive/records/training_sample_2026_11_05.md#the-update-after-the-batch)).

**A network update** follows each training iteration's games. It runs in the main
training process, on the CPU: beside the games, which go on, in self-play that
never stops, as in the Mac profile (section 9.1); while the game processes wait,
in alternating training iterations. It is many *training steps* one after
another, 700 in the 5 November run and 525 today. Each training step does four
things (`CampaignLearner.update` in `studies/campaign/learning.py`):

1. **Draw a minibatch.** It picks 32 different training samples at random from
   the whole replay buffer, the training step's *minibatch*, so one training step
   mixes decisions of many games and of all three alliances. Nothing is played: a
   training step only reads stored decisions.
2. **Read.** The network reads the 32 decisions at once. For every decision it
   gives its three values and its action probabilities, those of the alliance
   that was choosing there, which its input names.
3. **Compare.** It computes its losses (section 8.1), averaged over the 32
   training samples. On 5 November a minibatch held 16 of the Axis's decisions on
   average, and 8 each of the Allies' and the Comintern's.
4. **Adam step.** The network takes one Adam step (section 8.3) to lower the sum
   of its two losses.

The next training step draws a new minibatch of 32. After the last, the network
is saved as a *model export*, and every game takes it up at once
(section 9.1). The network after $k$ network updates is *generation* $k$; a fresh
network is generation 0. Playing takes minutes and the training steps under a
minute: on 5 November the 32 games took 851 seconds and the 700 training steps
49, on 15 November a training iteration of today's 24 games played in 499
seconds, also 64×2, and on 17 November a network update's 525 training steps
took 13.7 seconds beside the games
([record](../archive/records/one_network_comparison_2026_11_17.md#speed)).

![Where a training step's minibatch of 32 training samples comes from. 1: self-play plays 24 games at a time, in 6 game processes of 4 games each, and a game that ends is replaced at once; at each decision a random draw keeps it as a training sample with chance 5%, and when a game ends its final scores are added to its training samples; on 5 November 32 games kept 1,611 training samples from 33,062 decisions. 2: when a game ends, its training samples join the replay buffer in the main training process, the latest 8,000 training samples, about five network updates' worth of games, drawn as five bars from the oldest games, whose training samples leave first, to the newest; purple dots spread over all five bars mark one training step's minibatch of 32, drawn at random. 3: one training step, 525 per network update, each with a new minibatch: draw 32 different training samples at random from the whole replay buffer; the network reads all 32 at once; it compares its values with the final scores and its action probabilities with the visit shares, on all 32; its input names who chose each; the network takes one Adam step. 4: after the last training step every game takes up the new network at once. With a 64×2 network on the CPU, 24 games finish about every 5 minutes, and a network update's 525 training steps take about 14 seconds beside the games, which go on.](figures/training_update.svg)

**One network for all three alliances.** The network's input tells it which
alliance is choosing, in the global feature `deciding_player`
(`src/zone_encoding.cpp`), and the inference server evaluates every state with
it, a chance state once, in one forward pass of one network (section 9.2). The
owner chose one network on 18 November
([Q-010](../questions.md#answered)), from matched runs of the Mac profile on
17 November, 3.7 hours of training each
([record](../archive/records/one_network_comparison_2026_11_17.md)):

- **It is faster.** One network played 21.6% more decisions an hour than a
  network for each alliance. The inference server sets the pace of self-play on
  the Mac (section 9.2), and with one network the inference server's forward
  pass took 20% less time per network evaluation, and a network update 61%
  less. On the Mac's GPU
  the same states through one network took 15% to 38% less time (section 9.3).
- **It learned the values as well.** On each game before training on it, the
  one network's value head explained 15.4% of the variance of those games' final
  scores, and the three networks' value heads 13.1% of theirs (section 10); the
  two runs' held-out evaluation games scored alike.
- **A search compares one network's values.** With a network for each alliance a
  search compares values that different networks gave. On 9 November, with
  networks after one network update, their values for one alliance differed by
  2.5 to 17 points at the same state (section 4.7), while the best and worst
  actions' average results in a search lay a median 1.45 points apart, and in one
  game 9.3% of the simulations stopped at states rated by another alliance's
  network than the choosing one's
  ([record](../archive/records/depth_limit_2026_11_09.md#positions-rated-by-another-alliances-network)).
- **Its action probabilities fit its searches less well:** the one network's
  KL divergence from its searches' visit shares was 0.273, against 0.252 for the
  three networks, most of the gap at Axis decisions; the gap's cause is open
  ([known gaps](#known-gaps)).

**A network for each alliance.** `--networks three` keeps three networks
instead, the setting before 18 November. In a training step each of them reads
the minibatch, gives its values for all 32 decisions and its action
probabilities for those where its own alliance chose, and takes its own Adam
step. The inference server evaluates each state with the deciding alliance's
network and a chance state with all three, averaging their values
(section 9.2).

In the training command the minibatch size, 32, is `--batch-size` and the number
of training steps per network update is `--epochs`. The second name misleads: a
training step does not go through the whole replay buffer, as an epoch would.

### 8.5 Which numbers a training step moves

Every training sample passes through the linear layers, so nearly all of their
parameters change in every training step. An embedding is different: like any
weight whose input is 0, its gradient is zero unless its feature has a non-zero
value in one of the minibatch's training samples, because the embedding of a
feature with value 0 was never added in. So a training step changes the
embeddings of the features those training samples have, and Adam's average $m$,
which loses a tenth each Adam step without a new gradient, keeps moving a
recently used embedding for a few dozen training steps more. An embedding whose
feature has never had a non-zero value in a trained training sample stays at
zero. Checked with a test loss on two real decisions: the first training step
gave a gradient to exactly the 150 embeddings its decision uses and changed only
those; the second training step also moved the 59 embeddings that only the first
decision used.

**After the first network update of the 5 November run:**

| Embedding table | Embeddings moved, Axis network | Allies | Comintern | Embeddings in the embedding table |
| --- | ---: | ---: | ---: | ---: |
| Zone embedding table | 1,840 | 1,840 | 1,840 | 42,532 |
| Global embedding table | 670 | 670 | 670 | 4,076 |
| Action embedding table | 948 | 430 | 242 | 12,627 |

The embedding tables of that run had 2,812 more embeddings than today's. Of the
embeddings removed since, only fifteen had moved: twelve said that a nation's
income had been worked out and three that Japan, the KMT or the CCP keeps a
treasury, each true of every state. They are among the 670. No other removed
embedding had moved: each feature asked about something that cannot happen
([list](network_input.md#8-features-removed-as-impossible)).

That run kept a network for each alliance. Its three networks moved the same
zone and global embeddings, because every network learns values from every
training sample. Action embeddings feed only the action probabilities, which
each of those networks learned from its own alliance's decisions alone, so each
moved the embeddings of the action features its own decisions used. One network,
the setting since 18 November, learns its action probabilities from every
decision, so it moves the action embeddings of all three alliances' decisions.

**Features that always have non-zero values together get identical embeddings.**
Of the Comintern network's 1,840 moved zone embeddings, only 1,480 were different
from one another. Two features with the same values in every training sample get
the same gradient in every training step and stay identical, such as
`units:ccp:mountain_infantry` and `unit_stat:comintern:mountain_infantry:count` in
section 6.3. The network cannot tell them apart until some training sample has
one without the other.

### 8.6 Why small random minibatches

One training sample's gradient points the way that one decision would move the
parameters. The average over a minibatch of 32 different decisions comes nearer
to the way the game's decisions in general would: the random error of an average
of $n$ independent training samples shrinks like $1/\sqrt{n}$. And one training
step on 32 decisions costs far less than 32 training steps on one: in a separate
timing on a busy machine it took 78 ms, and a training step on a single training
sample 21 ms (the network update's own training steps took 70 ms each)
([record](../archive/records/training_sample_2026_11_05.md#the-update-after-the-batch)).
Averaging all 8,000 in every training step would read 250 times as many
decisions per training step but shrink that error only about 16 times,
$\sqrt{250}$. So for the same time, many cheap training steps with a little noise
make more progress than a few exact ones; that is the usual reasoning behind
small minibatches, not something measured here. Drawing at random keeps a
minibatch from being 32 neighbouring states of one game, which would push the
network 32 times in nearly the same direction; keeping only 5% of decisions
serves the same purpose. Both choices are standard. DQN, which learned Atari
games, took minibatches of 32 experiences drawn at random from a replay memory;
AlphaGo trained its value network on one state from each self-play game;
AlphaGo Zero took minibatches of 2,048 states drawn at random from its latest
500,000 games (Sutton and Barto, *Reinforcement Learning: An Introduction*, 2nd
edition, sections 16.5, 16.6.1 and 16.6.2). Whether minibatches of 32 and these
numbers of training steps suit this game has not been tested.

### 8.7 How often a training sample is drawn

Each network update draws 700 × 32 = 22,400 times. Once the replay buffer is
full, a training sample is drawn 2.8 times per network update and stays about
five network updates, until newer training samples push it out:

$$
\text{draws per training sample} \approx \underbrace{\frac{700 \times 32}{8{,}000}}_{\text{per network update}} \times \underbrace{\frac{8{,}000}{1{,}611}}_{\text{network updates in the buffer}} = \frac{22{,}400}{1{,}611} \approx 14
$$

The replay buffer's size cancels: it sets how old a training sample may be, about
five training iterations, not how often a training sample is drawn. Longer games
keep more training samples per training iteration, and each is then drawn less
often: 8 times on 31 October, when a training iteration of longer games kept
about 2,750 training samples
([record](../archive/records/training_sample_2026_11_05.md#draws-per-kept-sample-in-recorded-runs)).
A run's first training samples are drawn more often, because the replay buffer is
not yet full: in the first network update of the 5 November run, its 1,611
training samples shared all 22,400 draws, 14 each in that one network update.

Today's 525 training steps keep this for training iterations of 24 games: they
draw 525 × 32 = 16,800 times, 700 for each game of a training iteration as
before. A training iteration of 24 games kept 1,354 training samples on
15 November, so each would be drawn about 12 times; those games were longer than
on 5 November.

## 9. The whole loop, and running it

### 9.1 The training loop

With all the bricks in place, training runs self-play and network updates side
by side, in a loop of four steps:

1. **Self-play, game after game** (section 7.1). At every decision, the alliance
   to act runs a search (section 4), guided by the network (sections 3, 5
   and 6), and picks an action. A game thread that finishes a game starts the
   next at once.
2. **Keep some decisions as training samples** (section 7.2): what the network
   read, how the search split its simulations and, added when the game ends, the
   final scores. A finished game's training samples join the replay buffer at
   once.
3. **Train the network** in a network update after every 24 games that end,
   on the replay buffer's training samples (section 8), so that its action
   probabilities come closer to the search's visit shares and its values closer
   to the final scores. The network update runs beside self-play, which goes on
   with the network it has.
4. **Take up the new network.** When the network update is done, the inference
   server answers every game with the new network from its next inference batch
   on, and the run saves it.

![The training loop of self-play that never stops. 1: self-play plays game after game with the newest network; at every decision the alliance to act searches, asking the network many times, and a random 5% of decisions are kept as training samples. When a game ends, its final scores are added to its training samples. 2: the training samples join a replay buffer of recent training samples; a training sample records what the network read, how many simulations began with each action and, once the game ends, the final scores. 3: after every 24 finished games, a network update's training steps train the network, one for all three alliances, beside self-play: its action probabilities shift toward the search's visit shares and its predicted final scores toward the real ones. 4: when the network update is done, every game takes up the new network at once.](figures/training_loop.svg)

A *training iteration* is one turn of this loop: 24 games that ended and the
network update that trains on them. A game may so be played by more than one
version of the network. Each training sample records the version that answered
its search's last evaluation, and each game the decisions at which its version
changed (`network_versions` in `play_episode`, `studies/campaign/learning.py`).
AlphaZero trained this way: its one network was updated continually instead of
in iterations, and its self-play always used the latest parameters, while 5,000
TPUs played and 16 others trained
([preprint](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphazero-shedding-new-light-on-chess-shogi-and-go/alphazero_preprint.pdf),
pages 3 and 4). Here the network update runs on a thread of the inference
server's process (`self_play_never_stops` in `studies/campaign/run.py`, run with
`--continuous`), which needs the inference server on the CPU (section 9.2).

Training can also alternate between playing and learning, as the Windows profile
does, whose inference server runs on the GPU. A training iteration's 24 games
then start together with the network held fixed, and the network update runs
when the last of them has ended, so self-play stands still while the last games
finish and while the network updates (section 9.2).

The idea comes from AlphaZero. The search chooses better than the bare network,
the network learns to imitate the search and to predict outcomes, and a better
network makes the next searches better. Whether that works for this game on this
hardware is unproven: no training run has yet shown robust playing strength.

### 9.2 Running training on the Mac

**Layout.** The Mac profile (`studies/campaign/profiles/mac.json`) runs 6 game
processes of 4 games each. One *inference server*, the main training process,
runs the network for all their states together, on the CPU: for this small
network the GPU's cost per forward pass outweighs its speed. In self-play that
never stops, the same process runs the network updates, on a thread of their own
(section 9.1). Training stays within the
owner's allowance of 9 cores, the Mac's 10 performance cores less one for
everything else, and 30 GB of memory. `tools/supervise_campaign_training.py`
handles the time budget, restarts and memory stops. It counts one core for each
game process, one for the inference server, one for the network updates in
self-play that never stops and one for itself, but a game process
keeps 1.2 to 1.5 cores busy, because its game threads can compute at once
(below). So the layout was chosen by the load it puts on the Mac: 6 processes
kept about 9 cores busy, and 7, which also fit the count, about 10
([record](../archive/records/nine_core_layouts_2026_11_15.md)). Since the engine
work of 16 November the 6 keep only about 7 busy, because the inference server
now sets the pace ([record](../archive/records/engine_speed_in_training_2026_11_16.md)).
How to start, stop and resume a training run is in the
[campaign learning guide](../../studies/campaign/README.md).

**The inference server.** Game threads do not run the network themselves; the
inference server, which the tools and the dated records name the *coordinator*,
does it for all of them (`SharedEvaluatorServer` in
`studies/campaign/shared_evaluator.py`). A *network evaluation* is a network's
output for one state, its priors and values. When a game thread's search needs a
network evaluation, the thread writes the state's input, a few arrays of whole
numbers, into its own block of *shared memory*, memory that its game process and
the inference server can both read. Then it sends a short note of where those
arrays lie, its *inference request*, through its own *pipe*, a channel the
operating system keeps between two processes, and waits.

The inference server works in *inference batches*. Each time it is free, it takes
every inference request waiting at that moment as one inference batch: it reads
their notes, collates their states, evaluates them all in one forward pass of the
network, and sends each state's priors and values back through
the pipe its inference request came by, as lists of numbers. The number of states
in an inference batch is its *inference batch size*. *Collating* the inference
batch joins the arrays of all its states end to end, one array of each kind for
the whole forward pass, and shifts each state's indices to point into the joined
arrays (`pack_zone_arrays` in `studies/campaign/features.py`). The states keep
the order in which their inference requests were taken, and a chance state
appears once. If decision 612 came seventh in an inference batch of 8 states,
after three of the Axis and three of the Allies, its 37 zone vectors would be
numbers 222 to 258 of the forward pass's 296 zone vectors, counting from 0, and
every index in its arrays that names one of its zones would grow by 222 (figure
below). With a network for each alliance (`--networks three`) the forward pass
puts each network's states together, the Axis's first, then the Allies' and the
Comintern's; each network's linear layers read only its own alliance's states,
so every output is that network's own, up to floating-point rounding; and a
chance state, which all three networks rate, appears once for each
(`NetworkStack` in `studies/campaign/neural.py`). The forward pass gives every
legal action of every state the logarithm of its probability (section 6.8). The
inference server turns each state's logarithms into its priors on the CPU, one
state at a time, after copying them back from the GPU's memory when the forward
pass ran there (`collect` in `studies/campaign/shared_evaluator.py`).

**What a forward pass looks like.** A *forward pass* runs the network over the
states of one inference batch, collated. Each state keeps its own vectors through
the whole network of section 6: its 37 zone vectors, its global vector and an
action vector for each of its legal actions. But the vectors of all the inference
batch's states lie in the same arrays: in an inference batch of 8 states, the
forward pass's zone vectors are one array of 8 × 37 = 296 vectors of 64 numbers
each. Every layer of section 6, the embedding layer, the message-passing layers,
the summary and the heads, works on such whole arrays, so on all the inference
batch's states at once. The figure shows the forward pass of an inference batch
of 8 states, three of the Axis, three of the Allies and two of the Comintern,
decision 612 among them; its PyTorch calls are those the record cited below
counted:

![The forward pass of an inference batch of 8 states with one network for all three alliances: 3 states of the Axis, 3 of the Allies and 2 of the Comintern, decision 612 among them. Part 1: each state brings 37 zone vectors, a global vector and an action vector for each of its legal actions; collated, the forward pass's zone vectors are one array of 296 vectors of 64 numbers, in the order of their inference requests: the Axis's zone vectors 0 to 110, the Allies' 111 to 221, the Comintern's 222 to 295, decision 612's 222 to 258. Part 2: the forward pass is a list of PyTorch calls, each one for all 8 states: the embedding layer, message-passing layer 1, message-passing layer 2, then the summary, the heads and the outputs. Message-passing layer 1 is 21 PyTorch calls: every zone's message 1, every border's message with its border's own term 4, each zone's average of the messages it receives 3, a zone's inputs side by side 3, the zone correction 3, adding it 1, the average zone beside the global vector 2, the global correction 3, adding it 1. Message-passing layer 2 is the same 21; the embedding layer, summary, heads and outputs are 96; 138 in all, for 1 state as for 8. A network for each alliance calls each network's linear layers on its own states, between a split and a join: 247 PyTorch calls for these 8. Part 3: one PyTorch call, the network's linear for every zone's message, multiplies all 296 zone vectors by its 64 × 64 message weights: 296 × 64 output numbers of 64 multiply-adds each, 1,212,416 multiply-adds or 2,424,832 FLOPs, an eighth of them for decision 612. One output number, the first of Shensi's message at decision 612 by the Comintern's network of 5 November, is −0.294 × w1 + 1.957 × w2 − 1.422 × w3 − 0.203 × w4 and so on to w64, plus a bias: 64 multiply-adds, each two FLOPs. A PyTorch call's time is its call overhead, the same for 1 state or 8, then its FLOPs, which grow with the states.](figures/inference_batch_forward_pass.svg)

**What a forward pass is made of: PyTorch calls.** A forward pass is a list of
PyTorch calls (section 6.3), each applying one function to whole arrays, for all
the inference batch's states at once. PyTorch's documentation names such a
function an *operator*. With one network, a message-passing layer (section 6.6)
is the 21 PyTorch calls below, however many states the inference batch holds and
whichever alliances choose at them. The forward pass keeps each state's zone
vectors together, an array of states by 37 zones by the width, and every state
has the same map, so its borders are fixed indices along the zones
(`_state_layers` in `studies/campaign/neural.py`). For decision 612's zones, as
for any state's:

| PyTorch calls | What they do |
| --- | --- |
| `linear` | every zone's message: the 37 zone vectors times the layer's message weights |
| `select`, `index_select`, `add`, `gelu` | each of the 160 directed borders takes its source zone's message, adds the border's own term, which `select` picks from the network's, and passes the sum through the GELU activation function |
| `new_zeros`, `index_add_`, `div` | each zone adds up the messages arriving at it and divides by their number |
| `unsqueeze`, `expand`, `cat` | each zone's vector, the messages it received and the global vector, side by side |
| `linear`, `gelu`, `layer_norm`, `add` | the zone correction, added to each zone's vector |
| `mean`, `cat` | the average zone vector beside the global vector |
| `linear`, `gelu`, `layer_norm`, `add` | the global correction, added to the global vector |

On a GPU `index_add_` adds the messages with atomic additions, which PyTorch's
compiler could not build there. The compiled zone and position layers (section
9.3) therefore average with a fixed matrix instead: 37 rows and 160 columns,
holding 1 divided by the zone's number of incoming borders where a border ends at
the zone, times the messages, one `matmul`. It does more arithmetic, 5,920
multiply-adds per state and number of the width against 160 additions, and in
forward passes as written it was 5% to 10% slower on the Mac's GPU, so those
keep the additions
([record](../archive/records/compiled_forward_2026_11_18.md)).

**What a PyTorch call computes: FLOPs.** A *floating-point operation*, or *FLOP*,
is one multiplication or one addition of two numbers. Each output number of a
linear layer is a sum of products, one for each input: the input times its
weight, added to the sum. A *multiply-add* like that is two FLOPs. The toy layer
of section 6.2, with 3 inputs and 2 outputs, does 6 multiply-adds, 12 FLOPs. In
the messages' `linear` PyTorch call at decision 612, the first number of Shensi's
message adds up Shensi's 64 numbers, −0.294, 1.957, −1.422, −0.203 and so on
(section 6.4), each times its weight: 64 multiply-adds. Shensi's whole message is
64 such numbers, 4,096 multiply-adds, and the PyTorch call does the same for all
37 zones: 151,552 multiply-adds, 303,104 FLOPs, for one state. Only the three
`linear` PyTorch calls of a message-passing layer do much arithmetic: at 64×2
about 614,000 multiply-adds for one state. Each other PyTorch call goes over at
most about ten thousand numbers for each state, adding, dividing or passing each
through the GELU activation function, or does no arithmetic at all: `view`, for
one, only reads the same numbers as an array of another shape. Counting only the
multiply-adds of its linear layers, a whole forward pass of the 64×2 network does
about 3.4 million FLOPs for each state with 14 legal actions (section 9.3).

**How the states enter.** How many PyTorch calls a forward pass makes does not
depend on how many states the inference batch holds; how many FLOPs those calls
do grows in proportion to them. A forward pass of the 64×2 network on one CPU
core is 138 PyTorch calls, for 1 state as for 8, as in the figure: 42 for the two
message-passing layers and 96 for the rest, the embedding layer's embedding
lookups, the summary, the value and policy heads and the outputs. With a network
for each alliance and states of all three alliances it is 247 PyTorch calls:
each network's linear layers, with their activation functions and layer
normalizations, are called on that network's own states, between a split of the
forward pass's vectors by network and a join, which adds 20 PyTorch calls to each
message-passing layer and 69 elsewhere. On the GPU 24 or 25 more PyTorch calls
carry the states' arrays over, and at 512×16 a forward pass is 432 to 456
PyTorch calls with one network, 821 to 846 with a network for each alliance
([record](../archive/records/compiled_forward_2026_11_18.md#pytorch-calls)).
The FLOPs, by contrast, follow the states: in the figure's forward pass, the
network's `linear` PyTorch call for the messages multiplies the zone vectors of
all 8 states, 296 of them, in one PyTorch call, eight times decision 612's
303,104 FLOPs.

A PyTorch call costs a fixed *call overhead*, whatever the size of its arrays:
Python's and PyTorch's own work to check the arrays, choose a routine and make
room for the result, and on the GPU, handing the PyTorch call over. Then it costs
its FLOPs, which grow with the states. A forward pass of the 64×2 network over
one state takes one core 0.45 ms, 3.1 µs a PyTorch call, of which at most about
2.1 µs is the call overhead, since the same core does a state's 3.4 million FLOPs
in about 0.14 ms in large inference batches. An inference batch of 8 states pays
the same 138 call overheads as an inference batch of one (with a network for each
alliance, 247 when its states belong to all three), so its time per state is much
lower: on one core a forward pass of 8 states took 1.67 ms, about 0.21 ms a state
([record](../archive/records/pass_calls_2026_11_17.md#what-the-calls-cost)). A
PyTorch call is not a training step either: a training step (section 8.4) reads a
minibatch of 32 training samples and changes the network's weights once, and each
of its parts is itself many PyTorch calls.

On one core the call overhead is in fact well below the bound of 2.1 µs. A
forward pass of 8 states of all three alliances made with 82 fewer PyTorch calls
was only about 0.05 ms faster, about 0.7 µs a PyTorch call. And an 8-state
forward pass of the 64×2 network spends about 1.1 ms of its 1.4 ms on FLOPs, at
the rate one core reaches in large inference batches (worked out;
[record](../archive/records/grouped_layers_2026_11_17.md#what-this-does-and-does-not-show)).

**What a forward pass costs.** A forward pass costs much more than its
arithmetic alone. In a training iteration timed with the profiler on 17 November,
a forward pass of the 64×2 network on one core took 0.40 ms for one state,
0.82 ms for four and 1.41 ms for eight: about 0.27 ms plus 0.14 ms a state
([record](../archive/records/coordinator_rounds_2026_11_17.md#the-training-batch)).
Native samples of the inference server in that training iteration put about 43%
of its busy time in arithmetic, the GELU activation function (section 6.2) alone
14%, mostly in the border messages (section 6.6). About 31% went to Python's and
PyTorch's own work around the PyTorch calls, where their call overheads lie, and
12% to allocating and copying memory. At about 0.7 µs each, the call overheads
come to some 0.1 to 0.18 ms for that day's 146 to 258 PyTorch calls, part of the forward
pass's fixed cost of about 0.27 ms; the rest is the forward pass's own Python
work and turning the inference batch's arrays into tensors (inferred). That
training iteration kept a network for each alliance; in training with one
network, that night, a forward pass took 20% less time per network evaluation,
154 µs against 192 µs
([record](../archive/records/one_network_comparison_2026_11_17.md#speed)).

**What an inference batch costs.** An inference batch costs its forward pass and
the *request handling* around it, the inference server's work outside the forward
pass. In the same training iteration the inference server spent two thirds of its
time in forward passes, 13% collating, 6% reading the inference requests from the
pipes and shared memory, turning the outputs into priors and sending the replies,
and 9% waiting for inference requests
([record](../archive/records/coordinator_rounds_2026_11_17.md#the-training-batch)).
In training iterations of the Mac profile, whose 6 game processes of 4 games keep
24 *concurrent games*, games being played at the same moment, an inference batch
held about 8 states and took the inference server about 0.62 ms plus 0.13 ms for
each state, from reading the inference requests' arrays to the outputs, about
0.21 ms a state in all, and the inference server was busy about 96% of the time
([record](../archive/records/engine_speed_in_training_2026_11_16.md#what-limits-training-now)).
So the more states wait for an inference batch, the less each costs. While all 24
games play, an inference batch holds about 10 states, fewer as the training
iteration's games end, and one when its last game plays alone
([record](../archive/records/coordinator_rounds_2026_11_17.md#the-batchs-tail); below).

**What the cores and the GPU do.** In the Mac profile the GPU does nothing, and
all the cores work at the same time. A game thread works in the engine and the
search, listing legal actions, applying them on copies of the game and building
the network's input, until a state needs a network evaluation. Then it sends the
inference server an inference request and waits for the reply. The engine
releases Python's lock while it works, so the four game threads of a process can
compute at once, and a thread that waits leaves its core to the others. That is
why each process plays four games: in a 15 November training iteration a game
thread computed about a third of the time, yet the 24 game threads and the
inference server kept about 9 cores busy, and since the engine work of
16 November about 7. The inference server, on a core of its own, answers
inference batch after inference batch.

The M4 Max has 10 performance cores and 4 efficiency cores. An efficiency core
runs at 2.6 GHz instead of 3.8 and, in the game processes, does about 42% of a
performance core's work in a second. The allowance leaves one performance core for
the Mac's other work. When that work needs more, the training no longer fits on
the performance cores. In two training iterations timed with the profiler on
16 November other work kept about 4 cores busy. macOS then ran 27% to 29% of the
game processes' CPU time on the efficiency cores. The game processes waited for a
free core half to three quarters as long as they computed, and the inference
server a tenth to a fifth as long
([record](../archive/records/self_play_limits_2026_11_16.md#the-two-batches)).

![A schematic timeline. The four game threads of one game process take turns: each works in the engine, listing legal actions, applying an action on a copy of the game and building the network's input, then sends an inference request and waits until the inference server answers it in its next inference batch, then works again. While one thread waits, others work. Five more game processes do the same. The inference server, on one core, runs inference batch after inference batch: one forward pass on the CPU for all waiting inference requests. The GPU is idle.](figures/self_play_timeline.svg)

**Why the network runs on the CPU.** A forward pass on the Mac's GPU has a larger
fixed cost than a forward pass on one CPU core. A forward pass of the 64×2 network
over one state takes 2.1 ms on the GPU and 0.46 ms on one core, and over 16 states
4.7 ms and 2.7 ms
([record](../archive/records/network_and_search_cost_2026_11_14.md#the-network)).
An inference batch holds about 8 states (above), so one core answers it sooner.
The GPU is faster only for larger networks and larger inference batches
([section 9.3](#93-what-a-larger-network-and-a-longer-search-cost)). The GPU has
never limited self-play. When the inference server ran its forward passes there,
up to the night of 2 November, a network with five times the parameters played
about as many decisions per hour as the small one on the CPU (table below): the
engine and each forward pass's fixed costs set the pace, not the GPU's arithmetic.

**The Windows PC.** The owner's second machine is a PC with an 8-core Intel
i7-9700K, 16 GB of memory and an NVIDIA RTX 3060 Ti GPU. Its profile
(`studies/campaign/profiles/windows.json`; [training on
Windows](../../studies/campaign/README.md#training-on-windows)) runs 6 game
processes of 4 games, as the Mac's does, but the inference server's forward passes
run on the GPU, through *CUDA*, NVIDIA's software for computing on its GPUs. There
too the inference server probably set the pace. On the night of 14 November, in
three-round games with the 64×2 network, an inference batch held about 10 states
and its forward pass took 7.6 ms, collating included, and the inference server
waited for inference requests only 5.6% of the time
([record](../archive/records/three_round_training_2026_11_14.md#training)).

**The game processes** do most of the CPU work: about 65 ms per decision since
the engine work of 16 November, against 110 to 117 ms just before it
([record](../archive/records/engine_speed_in_training_2026_11_16.md)). A training
iteration timed with the profiler before that work showed where their time went:
the engine and its encoding of states for the network took 80% of the game
threads' CPU time. Listing a state's legal actions took 37%, about 1.0 ms each
time. Applying an action took 22% (0.6 ms), encoding a state 10% (0.26 ms),
copying the game for the search 5% and rolling dice 4%. The search's and the
adapter's Python and the inference requests took the rest
([record](../archive/records/self_play_limits_2026_11_16.md#a-game-threads-time)).
Inside the engine a few rule checks take the most. Enumerating and checking the
routes a naval force could sail takes about a quarter of the engine's time.
Finding landing plans for aircraft in flight takes a seventh. The economy's legal
actions, movement allowances and Supply Paths take about a tenth each. By kind of
work, 59% of the engine's time went to comparing names, allocating memory,
looking up maps and copying memory, and 41% to the rules' own logic, while the
state kept its zones, units, facilities and nations in maps keyed by name
([record](../archive/records/self_play_limits_2026_11_16.md#inside-the-engine)).
The engine now holds zones, nations, unit types, facility types, technologies
and the bases of marks as numbers, and keeps units and facilities in slot maps
found through a hash table, which together took 23.9% of the instructions out
of a searched game with play unchanged
([zones](../archive/records/zone_numbers_2026_11_16.md),
[nations](../archive/records/nation_numbers_2026_11_16.md),
[unit types](../archive/records/unit_type_numbers_2026_11_16.md),
[marks](../archive/records/mark_numbers_2026_11_16.md),
[facility types](../archive/records/facility_type_numbers_2026_11_16.md),
[slot maps](../archive/records/slot_maps_2026_11_16.md)); the rules still refer
to units and facilities by name ([names held as numbers](../engine/names.md)).
While the engine lists a state's legal actions, it keeps a cache of facts about
that state, such as whether a zone is in supply for a nation, so that each is
worked out once (`PositionScope` in `include/game/position_facts.hpp`). Applying
an action opens the same cache for the checks it makes while the state is still
unchanged, such as whether a fleet's chosen route is legal, and closes it before
the action changes anything. The supply search also works out only once per
search which naval facilities it may use. Since these two changes, applying an
action takes about 0.6 ms in random play instead of 1.1 ms
([record](../archive/records/supply_cache_2026_11_14.md)). An action is also
checked only once. The engine looks the chosen action up in the state's list of
legal actions, and the economy, which used to list all its legal actions again to
check an economy action, skips that check for an action the engine has found
(`MenuCheckedAction` in `include/game/campaign.hpp`). The check of the whole state
after every action reads the map's index and builds an error message only when it
fails. In random play these make applying an action take 29% fewer instructions,
and in training iterations the game processes ran 10.6% fewer instructions per
decision ([record](../archive/records/move_checks_2026_11_16.md)).

**What limits self-play** is the inference server. In two matched pairs of
Mac-profile training iterations after the engine work of 16 November, it was busy
about 96% of the time with inference batches of about 8 states, the training kept
only about 7 of its 9 cores busy, and it played about 301,000 decisions an hour
while playing ([record](../archive/records/engine_speed_in_training_2026_11_16.md)).
Less engine work per decision now buys decisions per hour only by filling the
inference server's inference batches: the game threads ask sooner, more states
wait for each inference batch, and each costs less. That is how the engine work of
16 November raised it, with inference batches of about 5 states before and 8
after; the rest of its saving left cores idle. By the inference server's cost
above, inference batches of all 24 game threads would answer about 31% more
states a second than inference batches of 8 (inferred); larger inference batches
need more concurrent games. Otherwise the inference server's own cost has to fall,
each inference batch's fixed part and the network's arithmetic, or part of its
work move elsewhere
([section 9.3](#93-what-a-larger-network-and-a-longer-search-cost)). Before that
work, which of the inference server and the cores set the pace depended on the
Mac's other work
([record](../archive/records/move_checks_2026_11_16.md#training-batches)).

**Self-play that never stops.** Alternating training iterations pay for their
end twice: self-play stands still while a training iteration's last games finish,
and again while the network updates. In a training iteration timed with the
profiler on 17 November, 23 games ended between 231 and 299 seconds and the
longest, 1,445 decisions, played alone until 332 seconds: for the last tenth of
the playing time the inference batches held one state each and the other game
threads waited, which cost about 9% of the decisions an hour (worked out from
each game's decisions and time;
[record](../archive/records/coordinator_rounds_2026_11_17.md#the-batchs-tail)).
With the inference server on the GPU, training iterations of 63 concurrent games
at 256×8 lost 10% to 14% of their decisions an hour the same way on 18 November
([record](../archive/records/gpu_training_compiled_2026_11_18.md#the-games-uneven-ends)).
The network update after the profiled training iteration of 17 November took
about 22 seconds. Self-play that never stops
(section 9.1) plays through both. In two matched pairs of runs of four network
updates the same day, it played 6.5% and 12.5% more decisions per wall-clock hour
in steady play, its inference batches held about 10.5 states against 8.5, and the
cores the run kept busy no longer fell to about 2 at each training iteration's
end ([record](../archive/records/self_play_never_stops_2026_11_17.md)). Its
network updates take longer, 34 to 48 seconds, because the trainer thread runs
in the inference server's process and the two take turns at Python's lock: while
a network update runs, the inference server answers about 29% fewer evaluations
a second, which costs about 3% of the decisions an hour (worked out;
[record](../archive/records/self_play_never_stops_2026_11_17.md#the-inference-server-while-a-network-update-runs)).

**Throughput** is counted as decisions searched per hour, with learning settings
under which each kept training sample was drawn 8 to 12 times
([section 8.7](#87-how-often-a-training-sample-is-drawn)). Decisions per hour is
the speed of one setup, a network and a search;
[section 9.3](#93-what-a-larger-network-and-a-longer-search-cost) shows how it
changes with the network's size and the search's budget. Measured on the Mac:

| Setup | Network | Decisions per hour |
| --- | --- | ---: |
| 31 October: graph input, network on the GPU | older graph network | about 54,000 |
| 2 November, best: zone input, network on the CPU | 64×2 | about 144,000 |
| Night of 2 November, training iterations 1–2: inference batches on the GPU | 256×8 | about 151,000 |

Graph input was the network input until 2 November, replaced then by the zone
input of section 5.

On 2 November the Mac profile played 124 eleven-round games per hour with learning
(64×2, network evaluations on the CPU). The night run's network had about five
times the parameters at no cost in throughput. In its 467 games it did not make
the agents stronger, but so few games cannot show whether a larger network helps
([open question](#how-big-should-the-network-and-the-search-be)).

On 4 November the search began keeping a copy of the game at each tree node
([section 4.7](#47-more-detail-on-the-search)). In a matched training iteration of
the Mac profile, with little training, that raised decisions per hour while
playing by 15.5%, from about 162,000 to 188,000. Games per hour rose more, from
152 to 184, because that training iteration's games were shorter
([record](../archive/records/search_copies_2026_11_04.md)).

On 12 November the fused embedding lookup cut the inference server's time per
network evaluation by 18%. In two matched pairs of Mac-profile training
iterations, decisions per hour while playing rose by 17.6%, from about 192,700 to
226,600, and games per hour from 182 to 211
([record](../archive/records/coordinator_lookups_2026_11_12.md)).

On 14 November applying an action began to use the state's cache (above). In
matched Mac-profile training iterations the game processes used 16% less CPU per
decision, but decisions per hour while playing rose only about 3%, from about
246,200 to 254,200, a smaller difference than between runs of the same code: the
inference server limited the layout
([record](../archive/records/supply_cache_2026_11_14.md#training-batches)).

The same day the inference server began answering each inference batch in one
forward pass of the three networks instead of one forward pass per alliance
(above), which made an inference batch about a third cheaper. In matched
Mac-profile training iterations, on a Mac whose other work used about 2.3 cores,
decisions per hour while playing rose by 13%, from about 222,500 to 252,200, and
the training used 9.9 cores instead of 8.9
([record](../archive/records/coordinator_one_pass_2026_11_14.md#matched-training-batches)).

On 15 November the owner lowered the allowance from 12 cores to 9, and the
profile went from 8 game processes to 6, which keep about 9 cores busy. In one
training iteration each, 7 processes played about 229,000 decisions an hour while
playing, 6 about 192,000 and 5 about 201,000; one training iteration each cannot
separate 6 from 5. Against the 252,200 of 8 processes the change costs about a
quarter of the decisions an hour, on slightly different code and not in matched
training iterations ([record](../archive/records/nine_core_layouts_2026_11_15.md)).

On 16 November the engine came to hold its names as numbers, to keep units and
facilities in slot maps and to digest a binary writing of the state for its
planning key ([names held as numbers](../engine/names.md),
[planning key](../archive/records/planning_key_2026_11_16.md)). In two matched
pairs of Mac-profile training iterations against the engine before that work,
decisions per hour while playing rose 26%, from about 239,000 to 301,000, and
games per hour from 222 to 288; the game processes used 43% less CPU per decision
([record](../archive/records/engine_speed_in_training_2026_11_16.md)).

**Failures.** A game that fails costs only that game. Its seed is recorded, and a
rules dead end (a decision with no legal action) saves its state in the training
run's `failed-positions/` folder. Two random-play checks run before long training
runs: the fuzzer (`tools/fuzz_campaign_dead_ends.py`) looks for dead ends and for
actions that leave the game unchanged, and `tools/check_zone_names.py` for names
the network's input does not list.

### 9.3 What a larger network and a longer search cost

Training has so far used the 64×2 network and 64 simulations per decision, far
less than published game-playing systems used
([open question](#how-big-should-the-network-and-the-search-be)). A larger
system costs in three places: the network's arithmetic, on the CPU or the GPU;
the engine's work for each simulation, on the CPU; and the search trees, in
memory. Each was measured on 14 November, on states from two scripted
eleven-round games
([record](../archive/records/network_and_search_cost_2026_11_14.md)).

**The network.** Most of a forward pass's arithmetic is the message-passing
layers' linear layers, applied to each of the 37 zones (section 6.6), so it grows
with the width squared times the number of message-passing layers. It is counted
below in FLOPs (section 9.2), two for each multiply-add of the linear layers, for
a state with 14 legal actions
([record](../archive/records/network_and_search_cost_2026_11_14.md#the-network)).
Most of the parameters, by contrast, are embeddings of the embedding tables, of
which a decision reads only a few hundred (section 6.9), so the parameter count
says little about the cost.

A forward pass costs two parts (section 9.2): the call overheads of its PyTorch
calls, which hardly depend on the inference batch size, and the arithmetic, which
grows with it. On one CPU core the first part is small and the arithmetic slow.
On the GPU the first part is larger, since the inference server's core hands
every PyTorch call to the GPU and the forward pass ends only when the GPU has
finished and its outputs are copied back, and the arithmetic is fast. So a forward
pass of the 64×2 network over an inference batch of 64 states takes one core
10.3 ms, 22 times its 0.46 ms for one state, but the GPU 6.5 ms, about three times
its 2.1 ms for one. The GPU pays only with large inference batches. States
evaluated per second through the inference server's own code, which collates the
inference batch, runs the forward pass and copies the outputs back
([record](../archive/records/network_and_search_cost_2026_11_14.md#the-network)):

![Three line charts side by side, for networks of 64×2, 256×8 and 512×16, of states evaluated per second against the inference batch size, 1, 4, 16, 64 and 256 states, on logarithmic scales. On the GPU the rate rises with the inference batch size: at 64×2 from 485 to 20,916, at 256×8 from 217 to 6,552, at 512×16 from 178 to 1,903. On one CPU core it rises at most 40% beyond 16 states: at 64×2 from 2,198 to about 6,000, at 256×8 from 360 to 658, at 512×16 from 87 to 166. One core is faster in small inference batches up to 256×8, the GPU in large ones, and at 512×16 in every inference batch size. A shaded band from 8 to 24 states marks today's layout.](figures/inference_batch_rates.svg)

Beyond 16 states an inference batch on one core gains at most 40%: its arithmetic
is already most of the cost. The GPU's rate keeps rising until its arithmetic
fills it, the sooner the larger the network: from inference batches of 64 states
to 256 it doubles at 64×2 but rises only 16% at 512×16, where the GPU then does
about 2.5 trillion FLOPs a second, against about 0.2 trillion for one core. In
inference batches of one state one core is faster up to 256×8; in inference
batches of 64 the GPU is 7 to 9 times as fast as one core for the three larger
networks. On the GPU the inference server's core takes about 5.6 µs to make each
PyTorch call of a forward pass, and its own work, collating the inference batch
and making the PyTorch calls, is about two thirds of every 64×2 forward pass,
40% to 60% of a 256×8 forward pass of 8 to 64 states, and only a tenth of a
512×16 forward pass of 256, where the GPU's arithmetic takes the rest
([record](../archive/records/pass_calls_2026_11_17.md#what-the-calls-cost)).
Real inference batches saved from a training iteration, replayed through the
inference server's code, divide the same way. In the inference batches as saved,
7.4 states on average, making the PyTorch calls took 1.6 ms of a 2.75 ms
inference batch at 64×2 and 5.4 ms of 11.7 ms at 512×16, and the GPU was slower
than one core at 64×2 but 1.7 and 3.7 times as fast at 256×8 and 512×16. Merged
16 at a time, 119 states an inference batch, a 512×16 inference batch waited 84%
of its time for the GPU's arithmetic, a 64×2 inference batch only 30%
([record](../archive/records/coordinator_rounds_2026_11_17.md#replayed-rounds-on-the-gpu)).
Half precision, and the forward pass compiled whole as written (below), were
tried on those inference batches and did not pay. Fewer PyTorch calls do let the
GPU do more: the same states through
one network instead of three took 15% to 38% less time an inference batch
([record](../archive/records/network_split_2026_11_17.md#inference-batches-on-the-gpu)),
which is one reason one network serves all three alliances since 18 November
(section 8.4). The rates below were measured on 14 November with a network for
each alliance, the three stacked as the inference server stacks them, so one
network's forward pass is somewhat faster; they are in states evaluated per
second
([record](../archive/records/network_and_search_cost_2026_11_14.md#the-network)):

| Network | Arithmetic per state | One CPU core, inference batches of 16 | GPU, inference batches of 64 | GPU, inference batches of 256 |
| --- | ---: | ---: | ---: | ---: |
| 64×2 | 3.4 million FLOPs | 5,850 | 9,840 | 20,900 |
| 128×4 | 23 million | 2,210 | 7,970 | 13,500 |
| 256×8 | 173 million | 577 | 4,500 | 6,550 |
| 384×12 | 565 million | 267 | 2,620 | 3,350 |
| 512×16 | 1,320 million | 125 | 1,640 | 1,900 |

Four threads on one forward pass are at most about twice as fast as one core, and
slower than one core on inference batches of a few states. Training adds little:
with 5% of decisions kept and each drawn about ten times, the network trains on
about half a training sample per decision, against 50 or more network evaluations
per decision in self-play.

**The search.** A simulation costs the game process about the same CPU whatever
the network and however many simulations a search runs: 1.23 ms of a core at 64
simulations, 1.26 ms at 256 and 1.29 ms at 1,024, measured alone on the Mac with
the engine of 14 November. In the 14 November training iterations the same work
cost about twice as much, about 2.4 ms per network evaluation (120 ms per
decision, about 50 network evaluations), with every core busy and four games to a
process; the gap has not been broken down. With the engine of 16 November it
costs about 1.3 ms per network evaluation in training (65 ms per decision, about
51 network evaluations)
([record](../archive/records/engine_speed_in_training_2026_11_16.md)).
A search keeps a copy of the game at each node of its tree
([section 4.7](#47-more-detail-on-the-search)), about 160 to 230 KB each, so a
search tree holds about 11 MB at 64 simulations, 56 MB at 256 and 250 MB at 1,024
until its action is chosen. Each concurrent game (section 9.2) holds one search
tree.

**Which part limits.** Count both parts in network evaluations. A search asks for
roughly one network evaluation per simulation (section 4.2), and decisions with a
single legal action are not searched, so a decision uses about 50 network
evaluations at 64 simulations, 197 at 256 and 612 at 800. Each network evaluation
needs engine work from a core for games, about 1.3 ms in training, and part of
a forward pass. So the 7 cores for games that the 9-core allowance leaves can
feed the network about 5,400 network evaluations a second, whatever its size, and
the network can evaluate as many states a second as the table above gives for its
size and device. Self-play runs at the lower of the two rates:

$$\text{decisions per hour} = \frac{3600}{\text{network evaluations per decision}} \times \min\left(\frac{\text{cores for games}}{\text{core seconds per network evaluation}}, \text{states the network evaluates per second}\right)$$

![A line chart on a logarithmic scale of network evaluations per second for networks of 64×2, 128×4, 256×8, 384×12 and 512×16 on the Mac. A flat line at about 5,400 a second is what the engine work of the 7 cores for games can feed, the same for every network. The network on the GPU, in inference batches of 64 states, evaluates 9,840 states a second at 64×2 falling to 1,640 at 512×16, and crosses the flat line between 128×4 and 256×8. The network on one CPU core, in inference batches of 16, evaluates 5,850 at 64×2, just above the flat line, falling to 125 at 512×16. Self-play gets the lower rate: the cores' up to 128×4, the GPU's from 256×8 on.](figures/evaluation_supply.svg)

**How decisions per hour changes with the network and the search.** The
network's size changes only the second rate, and the search's budget divides
both. Worked out for the Mac, with 7 cores for games, one for the inference server
and one for the supervisor, the network on whichever is faster of one core, in
inference batches of 16 states, and the GPU, in inference batches of 64, and
30 GB, decisions per hour are:

| Network | 64 simulations | 256 simulations | 800 simulations | Limited by |
| --- | ---: | ---: | ---: | --- |
| 64×2 | 386,000 | 94,000 | 29,000 | the cores |
| 128×4 | 386,000 | 94,000 | 29,000 | the cores |
| 256×8 | 324,000 | 82,000 | 25,000 | the GPU |
| 384×12 | 188,000 | 48,000 | 14,500 | the GPU |
| 512×16 | 118,000 | 30,000 | 9,200 | the GPU |

Down a column of the table, decisions per hour stays the same while the cores limit. Up to
128×4, a network with about 7 times the arithmetic of 64×2, the engine sets the
pace and the larger network costs nothing. From 256×8 on the GPU limits, and
decisions per hour falls, but much less than the arithmetic grows: 512×16 has
about 390 times the arithmetic of 64×2 and plays about a third as many decisions
an hour, because the GPU's rate falls only six times over that range; a forward
pass of a small network costs it mostly fixed overhead. Before the engine work of
16 November, with the cores' rate about half as high, the engine set the pace up
to 256×8: on the night of 2 November a 256×8 network on the GPU played about as
many decisions an hour as the 64×2 network on the CPU (section 9.2). With the
network on one CPU core, as in today's profile, the inference server already
limits at 64×2 (section 9.2), and the network's arithmetic alone would limit from
128×4 on, so every larger network needs the GPU.

Along a row of the table, decisions per hour falls in proportion to the simulations, whatever
limits: four times the simulations, about a quarter of the decisions. So which
part limits depends on the network, not on the search. A game has about 1,000
decisions (the 14 November training iterations averaged about 940), so 100,000
games take about 11 days at 386,000 decisions an hour, 44 days at 94,000 and 453
days at 9,200.

The table is worked out from the measurements above, not measured in training
runs, by the method of the 14 November study with the engine's cost of 16
November: 0.065 s of CPU per decision at 64 simulations, scaled to larger
searches as the study scaled 0.120
([record](../archive/records/network_and_search_cost_2026_11_14.md#which-part-limits-worked-out);
[engine cost](../archive/records/engine_speed_in_training_2026_11_16.md)). Today's
setup, the 64×2 network on one CPU core, is not in the table: there the inference
server limits, at about 301,000 decisions an hour measured, where the cores could
feed about 386,000. With the engine of 14 November the table gave 210,000 for the
cores where a 15 November training iteration measured about 192,000
([record](../archive/records/nine_core_layouts_2026_11_15.md)), so read every
rate as an upper bound, about a tenth too high, and every number of days as a
lower bound.

**Where an inference batch's states come from.** An inference batch holds the
inference requests waiting when it starts, and a game asks for one network
evaluation at a time: its search plays one simulation after another, and a
simulation that reaches a new state waits for its network evaluation before the
next begins (`_expand` in `studies/shared/multiplayer_mcts.py`). So an inference
batch holds at most one state for each concurrent game. An inference batch of 64
states needs about 128 concurrent games, half of them waiting in the inference
batch while the other half work in the engine, and each holds its search tree in
memory. At 800 simulations 30 GB holds the search trees of only about 115 games
beside the processes' other memory, so inference batches hold about 57 states.
Today's layout has 24 concurrent games, and its inference batches on the CPU hold
about 10 states while all 24 play, about 8 over a whole training iteration, and
one at its end (section 9.2). It could never fill an inference batch of 64, and in
inference batches of 4 and of 16 states the GPU gives 11% and 35% of its rate in
inference batches of 64 at 64×2, and 25% and 56% at 512×16. So moving the network
to the GPU means more concurrent games as well. A search could instead ask for
several network evaluations at once: choose a few new states before asking,
steering each later choice away from the paths already chosen, and wait for all
of them together. That would fill inference batches with fewer games and less
memory, but it changes which states a search explores, so it is a change of the
search, to be checked like one; it has not been tried.

**Comparing setups.** Decisions per hour is the speed of one setup, a network and
a search. It compares two versions of the code on the same setup, as the matched
training iterations of section 9.2 do, but not two setups: a larger network or a
longer search plays fewer decisions an hour, and whether its better searches
teach more per hour is unmeasured
([open question](#how-big-should-the-network-and-the-search-be)). To judge a
change of the code at a size not yet trained, measure the rate it changes and
work out the rest with the formula. A change to the engine or the search changes
the cores' rate, which is the same for every network. It raises decisions per hour
wherever the cores limit, but only until the cores' line in the figure reaches the
network's line above it. With the GPU in inference batches of 64, a cheaper engine
can now pay up to about 1.8 times at 64×2, about 1.5 times at 128×4 and not at all
from 256×8 on, where the GPU already limits; inference batches of 256 would let it
pay about 1.2 times at 256×8, with four times the concurrent games. With the
network on one core, as today, the inference server is busy about 96% of the time
and the cores are not (section 9.2), so at 64×2 a cheaper engine gains only as far
as it fills the inference server's inference batches. A change to the inference
server changes the network's rate, and matters only where the network or the
inference server limits.

**The inference server's levers.** The inference server has three levers, which
weigh differently on the two devices. Larger inference batches gain little on one
core beyond about 16 states, and much on the GPU: at least up to 256 states for
the small networks, and up to about 64 for 512×16. Fewer PyTorch calls, or
smaller call overheads, gain little on one core, where a call overhead is under
a microsecond and an inference batch is mostly FLOPs, and most on the GPU in
small inference batches of small networks, where the call overheads are most of
a forward pass's time.
Cheaper arithmetic gains on one core in any inference batch, but on the GPU only
in large inference batches of large networks, where the arithmetic fills it. From
256×8 on the network needs the GPU, so there the inference server's speed is the
GPU's, and these levers are what would raise it. The levers take the forms below,
beside two changes around the forward pass: leaner request handling and a second
inference server. The first, fewer PyTorch calls, came with one network for all
three alliances on 18 November, and the second, compiling, is built for the zone
and position layers as a setting; the others are not built. Half precision was
tried on real inference batches saved from a training iteration and did not pay
as it stands; which of the others pay, and how much, is open:

- **Fewer PyTorch calls.** One network for all three alliances makes a forward
  pass's PyTorch calls one network's, 138 at 64×2 on one core. A network for
  each alliance makes 247 when an inference batch holds states of all three: 44%
  to 47% of its PyTorch calls, at sizes from 64×2 to 512×16, split the forward
  pass's vectors by network, call each network's linear layer on that network's
  part and join the results (`_by_network` in `studies/campaign/neural.py`;
  [record](../archive/records/compiled_forward_2026_11_18.md#pytorch-calls)).
  The same states through one network took 15% less time on one core and 15% to
  38% less on the GPU
  ([record](../archive/records/network_split_2026_11_17.md)), and in matched
  training runs on the Mac one network played 21.6% more decisions an hour
  ([record](../archive/records/one_network_comparison_2026_11_17.md#speed);
  section 8.4). Two ways to keep three networks with fewer PyTorch calls did not
  pay. A *grouped matrix product*, one PyTorch call that multiplies each
  network's states by that network's own weights, cut a three-alliance forward
  pass of the 64×2 network from 258 PyTorch calls to 176, but on one core real
  inference batches were no faster, and on the Mac's GPU PyTorch's grouped
  product, the private function `torch._grouped_mm`, is about twice as slow as
  the split ([record](../archive/records/grouped_layers_2026_11_17.md)). A
  *padded product*, one standard batched matrix product (`torch.baddbmm`) with
  each network's states padded with empty ones to the largest network's count,
  would double the states and the arithmetic, since the Axis decides at two
  thirds of the states; a stand-in for it was slower than the split from 60
  states on, by 12% to 66%
  ([record](../archive/records/network_split_2026_11_17.md)).
- **Smaller call overheads: compiling.** PyTorch's compiler, `torch.compile`,
  reads a set of PyTorch calls once, ahead of the forward passes it serves, and
  writes routines that each do the work of several PyTorch calls, such as a
  linear layer's matrix product, its GELU activation function and the addition
  after it. Compiled code pays fewer call overheads and moves its numbers through
  memory fewer times. Its routines work best for arrays of fixed sizes, while a
  forward pass's arrays change size with the inference batch size. With
  `--compiled-forward` the inference server compiles one network's zone and
  position layers, from the zone vectors through the message-passing layers to
  the state vectors and the values, for fixed numbers of states, the *state
  buckets* 1, 2, 3, 4, 6, 8, 10, 12, 16, 20 and so on up to 512, each at most a
  third more than the one below (`STATE_BUCKETS` and `compiled_state_layers` in
  `studies/campaign/neural.py`). An inference batch is padded to the next bucket
  with empty states, whose zone and position vectors start at zero, and each
  bucket is compiled when an inference batch first needs it. The parts whose
  sizes follow the legal actions, the embedding lookups, the actions' vectors and
  the policy readout, run as written, and a network for each alliance never
  compiles, since each network's count of states would set its own array sizes.
  On the saved inference batches, the compiled layers took 6% to 9% less time per
  inference batch on the Mac's GPU than the same layers as written, at 256×8 and
  512×16 as saved, about 9 states, and 21% to 24% less merged 8 at a time, about
  60 states. At 64×2, where the layers they compile are a smaller part of the
  time, they were 9% slower on the GPU and about as fast on one core
  ([record](../archive/records/compiled_forward_2026_11_18.md#speed)). In
  training at 256×8 on the Mac's GPU, with 63 concurrent games whose inference
  batches held about 24 states, two matched pairs of training iterations played
  4.6% more decisions an hour with the compiled layers on average, while two
  runs of one setting differed by 5% to 6%. So a gain in training is not
  established; from the forward pass's timings alone a gain of about 10% would
  be expected, an inference
  ([record](../archive/records/gpu_training_compiled_2026_11_18.md)). Their
  outputs equal the uncompiled ones up to rounding. Compiling the buckets an inference
  batch first needs takes time: with PyTorch's compile cache empty, about 17
  seconds for the buckets of the inference batches as saved at 256×8, 36 seconds
  merged 8 at a time at 512×16, and a minute on one core at 64×2. PyTorch keeps
  the compiled code on disk, and a later run starts with it. The setting is off
  unless given. Fewer passes through memory matter most on the GPU, where the matrix
  products are only 41% to 45% of a forward pass's time at every size, and the
  rest is operations that each read and write whole arrays with little
  arithmetic, such as additions, GELU and joins of vectors side by side; at
  512×16 the per-border work of the message-passing layers alone, along each
  state's 160 borders, is 28% to 32%
  ([record](../archive/records/network_split_2026_11_17.md#where-the-gpus-time-goes)).
  Compiled whole and as it was written, the forward pass had never been faster:
  PyTorch compiled it again for each new mix of states, and larger inference
  batches made it write GPU code that did not build
  ([record](../archive/records/coordinator_rounds_2026_11_17.md#compiling)).
  The actions' vectors and the policy readout are not compiled yet. On an NVIDIA
  GPU, such as the Windows PC's (section 9.2), a *CUDA graph* goes further:
  PyTorch records a forward pass's PyTorch calls on the GPU once, and each later
  forward pass of the same inference batch size replays the record with a single
  call overhead; it has not been tried.
- **Cheaper arithmetic: half precision.** The network computes with numbers of
  32 bits, which keep about 7 significant digits; that is the float rounding of
  section 6.3. *Half-precision* numbers take 16 bits and keep about 3. A forward
  pass in half precision moves half as many bytes, and many GPUs compute with such
  numbers faster, but its outputs differ from the 32-bit ones by much more than
  rounding, so it would be checked like a change of the network. Under PyTorch's
  automatic mixed precision, which does the matrix products in 16 bits and keeps
  sums and normalizations in 32, the saved inference batches ran 5% to 23% slower
  on the GPU, since the conversions add PyTorch calls, while priors moved by at
  most 0.00023 and values by at most 0.10; on one core bfloat16, another 16-bit
  format, made them 92% slower ([record](../archive/records/coordinator_rounds_2026_11_17.md#half-precision)).
- **Leaner request handling.** Outside the forward pass, the inference server
  reads the inference requests' notes from the pipes, collates the inference batch
  in Python, turns the outputs into priors one state at a time and sends the
  replies through the pipes as lists: its request handling (section 9.2). In a
  training iteration timed with the profiler on 17 November collating took 13%
  of the inference server's time, and the rest of the request handling 6%
  ([record](../archive/records/coordinator_rounds_2026_11_17.md#the-training-batch)).
  Writing the replies into shared memory, turning all the states' outputs into
  priors at once, and collating in the engine's C++ with fewer copies would
  shorten that part of an inference batch.
- **Larger inference batches.** More concurrent games fill larger inference
  batches, each game with its search tree in memory, and so would a search that
  asks for several network evaluations at once (both above, where an inference
  batch's states come from). On the GPU the inference server's core could also
  collate the next inference batch while the GPU computes the current one; now it
  waits for each forward pass's outputs before its next inference batch. In
  alternating training iterations, a training iteration's end empties its
  inference batches too, since its last games play alone; self-play that never
  stops has no such end (section 9.2).
- **A second inference server**, serving half the game processes, would add
  capacity without making an inference batch cheaper: each inference server would
  find about half as many states waiting, and smaller inference batches cost more
  per state. It was not built on 14 November, when the cores were nearly all busy
  ([record](../archive/records/coordinator_one_pass_2026_11_14.md#other-ways-considered));
  since the engine work of 16 November about 2 of the 9 are idle (section 9.2).

Each form can be checked on real inference batches saved from a training
iteration (`tools/profile_coordinator.py --save-every`) and replayed through the
inference server's code on one core or on the GPU, with a network of any size, as
saved or merged into larger inference batches: the replay times each part of an
inference batch's handling and compares two versions' replies
(`tools/replay_coordinator_rounds.py`; with `--networks one`, one network
evaluates all the states). `tools/time_forward_operations.py` times each
operation of a forward pass on such inference batches, and
`tools/benchmark_network_sizes.py` times forward passes of sampled states, as
for the rates above.

Three things follow, inferred:

- **The engine is the main cost of a simulation.** A network evaluation takes
  about 1.3 ms of a core in the engine and 0.15 to 0.22 ms of the GPU at 256×8.
  Keeping the Mac's GPU busy, in inference batches of 64, takes about 13 cores for
  games at 64×2, 10 at 128×4, 6 at 256×8, 3 at 384×12 and 2 at 512×16: the 7 of
  the allowance keep it busy from 256×8 on, and all 10 performance cores would
  nearly keep it busy at 128×4.
- **Memory grows with the search.** A search tree holds about 0.24 MB per
  simulation, so at 800 simulations each concurrent game holds about 190 MB, and
  memory, not the GPU, sets how many games can fill an inference batch.
- **What each part of a computer buys.** More cores, like a cheaper engine, raise
  the cores' line in the figure, and with it decisions per hour wherever the cores
  limit. A faster GPU raises its line and moves the crossing to larger networks,
  but helps only with enough cores to feed it, about one core for every 750
  network evaluations a second at the engine's cost of 16 November: a GPU ten
  times as fast as the Mac's would need about ten times the cores, unless the
  engine gets cheaper. Memory must hold a search tree for every concurrent game.

### 9.4 How the Campaign Observatory shows a game

The Campaign Observatory is a viewer for recorded games, apart from training. It
lets you stop a recorded game at any event and inspect both the board and the
decision facing the player there. Python prepares the recording.
The browser draws it with HTML, CSS, JavaScript and SVG.

**From play to replay.** On a fresh training run whose games are played inside
the training process (without `--episode-workers`), `--record-replay` writes a
`replay.jsonl` trace. It records the actual actions, resolved dice and search
statistics for the legal actions at each recorded decision. To turn the trace
into a viewable game, Python starts a separate copy of the C++ engine from the
recorded seed. It applies each action or dice event in order and checks the
resulting state against the trace. The exported JSON contains the scenario map,
the factions (nations and alliances), one initial state and a list of events.
Each event carries just the changes needed to advance the board, alongside its
action and search details or its dice record.
[Recorder](../../studies/campaign/learning.py) · [Replay
builder](../../studies/campaign/replay.py)

**From replay to screen.** A local Python server serves the selected recording and
the frontend files directly from `web/campaign_viewer/`. The browser loads the
JavaScript as native modules. The server can also follow a growing trace. With
*Follow latest* enabled, the browser checks every two seconds and the server
applies newly completed records. For offline viewing, the same Python module can
package the recording, board image, styles and scripts into one HTML file. [Server
and HTML export](../../studies/campaign/viewer.py) · [Launch
commands](../../web/campaign_viewer/README.md)

**How the browser draws a state.** The HTML defines the map, inspector,
timeline and analysis panels. The stylesheet arranges them. When you move the
timeline, `model.js` applies recorded changes from the current state or a
cached earlier one. In `app.js`, `seek()` compares the selected state with its
predecessor and redraws the panels. The SVG uses the pixel coordinates of the
China campaign board image. Each of the 31 land pins marks its printed territory
roundel, and each of the six sea pins sits inside its zone. Scenario connections
and recorded movement routes use the same pins. Zooming enlarges the board under
them. The labels keep a minimum screen size, adding location names and stacks by
nation as space allows. Selecting a label opens its full location record at any
zoom. [Layout](../../web/campaign_viewer/index.html) · [Board
coordinates](../../web/campaign_viewer/map-layout.js) ·
[Styles](../../web/campaign_viewer/style.css) · [Replay
model](../../web/campaign_viewer/model.js) · [Rendering and
controls](../../web/campaign_viewer/app.js)

For example, at event 12 of the viewer's test game (seed 1951), its event journal
records Ma Clique joining KMT after the CCP attack, and the map's card for
Tsinghai now shows KMT possession. Going back one event restores Ma Clique. The
search panel looks forward from whichever board you select. If the next event is a
decision with saved search data, it shows the legal actions, the network's
priors, the simulations' visit counts and the action actually played. If the next
event is a dice roll, the combat and dice panel shows the outcome once you go
forward. [Replay example and checks](../../tools/verify_campaign_replay_viewer.mjs)

## 10. Measuring strength

**Held-out evaluation** (`studies/campaign/evaluation.py`) fixes the networks
being tested, turns exploration noise off and plays them against simple scripted
opponents (`balanced` and `cautious`), one side at a time, on seeds that training
never used. It measures playing strength; it is not a network evaluation
(section 9.2).

**Repeated-state guard.** Held-out evaluation stops a game after 20 visits to the
same full state and reports it as unfinished, with no final score.

**Held-out evaluation loops, night of 2 November.** In 3 of 26 games the trained
networks repeated one combat-phase action 20 times and were stopped; the
untrained networks never did in 39 games. The action was a patrol plane declaring
an attack it had already declared, which changed nothing: an engine loophole. A
search values an action that changes nothing exactly as the current state, so a
network that preferred the state to the likely battle chose it every time once
the noise was off. The engine stopped offering the duplicate (commit `68ebd15`),
and the fuzzer now flags any action that leaves the game unchanged (`b26511f`).
The lesson is general: search will find and use any action that does nothing, so
the engine must not offer one.

**Generation 0 is nearly passive with the noise off.** A fresh network, generation
0, gives every state the same values (section 6.9), so its search has little to go
on. On 14 November, the untrained networks playing one alliance against the
scripted opponents ended almost every phase at once. The Axis made 23 decisions a
game, against 338 for the scripted Axis. In self-play, with noise and the action
drawn from the visit shares, the same networks made 208 Axis decisions a game
([record](../archive/records/three_round_training_2026_11_14.md)). So comparing a
trained network with generation 0 compares it with a player that does almost
nothing. Over three game rounds, and over eleven on 18 November, that is the
best Axis player measured (see
[the objective](#is-the-final-wealth-gap-the-right-goal)).

A few games do not establish strength. The scripted opponents are simple
controls, not expert play.

**Losses on fresh games.** Between held-out evaluations, a run shows how well
its network learns by how well it predicts each game before training on it. In
self-play that never stops, each game that ends is first scored by the network
serving self-play, with section 8.1's value loss and the KL divergence of the
action probabilities from the visit shares, by alliance (`fresh_game_losses` in
`studies/campaign/learning.py`). Two runs play different games, whose final
scores can be predicted more or less well, so a run's value loss is compared
beside the variance of its games' final scores, which is the value loss of
always predicting their mean. The *explained variance* is one minus the value
loss divided by that variance. On 17 November one network's value loss was 18%
higher than three networks', but its games' final scores varied 21% more, and
the two explained 15.4% and 13.1% of that variance
([record](../archive/records/one_network_comparison_2026_11_17.md#learning-on-each-game-before-training-on-it)).
`tools/compare_training_runs.py` reports both for each hour of a run.

## 11. Known gaps and open questions

Known gaps are parts of the system that are missing, broken or unmeasured. Open
design questions are choices the design made without testing the alternative;
each says what the design does now, what the alternative would be, what is
measured and what would settle it.

### Known gaps

- **Some details are summarized, not named.** Tests check the names the
  engine's source writes, and in 480 random games no name falls into an "other"
  feature. But a mark's argument other than a place or a nation, such as which
  railroad was damaged this turn, is counted for the whole state, and a battle
  note's numbers are added into one feature value. Four marks a nation can carry
  are known to be on no list, because the engine puts their names together in a
  variable. See
  [names the encoder doesn't know](network_input.md#keeping-the-lists-complete).
- **Heap corruption.** On the night of 2 November a game process crashed twice
  early in training iteration 3: the engine freed memory and kept using it. About
  4.5 hours of replays in builds with memory checks did not reproduce it. Two
  crashes close together and none under changed timing suggest a race between
  game threads in one process, but that is unproven. A ThreadSanitizer run is the
  suggested next check.
- **No training run has yet made the agents stronger.** The most games a training
  run has played is 792 three-round games, on the PC on the night of 14 November
  ([record](../archive/records/three_round_training_2026_11_14.md)). Earlier runs
  played at most about 500. Both are far fewer than published systems needed
  ([how big](#how-big-should-the-network-and-the-search-be)). In that run:
  - The value heads learned each alliance's average final score.
  - On 24 held-out seeds, no trained network beat the scripted policy in its seat
    by a clear margin.
  - Training made the Axis more active, away from the passive play that scores
    best over three game rounds.
  - Its settings could not test the main question. Within three game rounds a
    passive Axis wins whatever is learned, and a 64×2 network relates each zone
    to about a third of the map
    ([how big](#how-big-should-the-network-and-the-search-be)).

  Two design questions below may also be part of the reason: the
  [objective](#is-the-final-wealth-gap-the-right-goal) and
  [flat search targets](#are-64-simulations-enough-when-there-are-many-legal-actions).
- **One network's action probabilities fit its searches less well** than a
  network for each alliance did. In the matched runs of 17 November, at 64×2,
  the one network's KL divergence from its searches' visit shares was 0.273,
  against 0.252 for the three networks, most of the gap at Axis decisions, 0.318
  against 0.289, while both runs' searches spread their visits alike
  ([record](../archive/records/one_network_comparison_2026_11_17.md#learning-on-each-game-before-training-on-it)).
  The cause is not measured: the one network holds three alliances' strategies
  in the parameters of one 64×2 network, where three networks have three times
  as many, and the comparison was one run of each. The same comparison at a
  larger network size would show whether size closes the gap; every run records
  the fit by alliance (`fresh_games` in `manifest.json`).
- **Input pruning left out two rules** it could not prove for the whole game:
  warlords never owning ships or planes, and per-flag unit-class rules. Nor
  does each kind of thing have its own list of marks yet, so some global features
  pair a nation, or the game as a whole, with a mark that only units or
  territories carry
  ([what is still asked](network_input.md#what-the-global-features-ask-about-a-nation)).
- **The inference server limits self-play on the Mac.** Since the engine work of
  16 November it is busy about 96% of the time while the training keeps about 7
  of its 9 cores busy
  ([record](../archive/records/engine_speed_in_training_2026_11_16.md)), so in the
  Mac profile a faster engine plays more decisions an hour only as far as it fills
  the inference server's inference batches. An inference batch costs the
  inference server about 0.62 ms besides 0.13 ms a state (section 9.2); a seventh
  game process, now that cores are idle, would fill its inference batches further,
  which is untested. The inference server's own levers, none of them built, are
  listed in section 9.3, with the first measurements of three of them. In
  self-play that never stops the network updates run on a thread of the
  inference server's process, and while one runs the inference server answers
  about 29% fewer evaluations a second, about 3% of the decisions an hour; a
  trainer process of its own would avoid that, which is untested
  ([record](../archive/records/self_play_never_stops_2026_11_17.md#the-inference-server-while-a-network-update-runs)).
  Within the engine, listing a state's legal actions now
  costs the most each time, and checking a naval route copies the whole state and
  works out its carriers' reach and supply again with no cache
  ([record](../archive/records/naval_route_checks_2026_11_16.md)). When the
  Mac's other work needs more than one core, part of the training runs on the
  efficiency cores
  ([record](../archive/records/self_play_limits_2026_11_16.md)).

### Open design questions

#### One embedding per combination, or embeddings built from parts?

**Now.** Every feature names a full combination and has its own embedding
(section 6.3). `unit_stat:axis:infantry:move_1`, an Axis infantry with one
movement point left, and `unit_stat:allies:infantry:move_1`, the same for the
Allies, share nothing. What training learns about one does not carry over to the
other, and a combination that training rarely meets keeps an embedding near zero.

**Alternative.** Build each embedding from its parts: one embedding for the
alliance, one for the unit type, one for the property. Every part is trained
wherever it appears, and the embedding tables shrink about tenfold: unit
statistics would need 5 + 45 + 74 = 124 part embeddings instead of their 13,321
combination embeddings, and the three embedding tables about 6,400 embeddings
instead of 59,235.

**The catch.** Added parts lose which part went with which. With Axis infantry
with one movement point left and Axis tanks with two in one zone, a sum of parts
cannot tell whether the infantry or the tanks have the one movement point, and
the layers after the embedding lookup would have to learn what the current
embeddings give directly. Combining each feature's parts through a small learned
layer, or keeping a combination embedding alongside the parts, keeps that
distinction at some cost per feature.

**Measured:** nothing yet. **Would settle it:** both versions trained with equal
compute, compared on held-out value error and in held-out evaluation games.

#### How big should the network and the search be?

**Now.** The Mac profile runs a 64×2 network (section 6) with 64 simulations per
decision (section 4), and no training run has played more than about 500
eleven-round games: the night run of 2 November played 467, with a 256×8 network.
After $k$ message-passing layers a zone's vector reflects zones up to $k$ borders
away (section 6.6). The map is 7 borders across, from Tokyo to Sinkiang, and two
zones are on average 3.2 borders apart. So a 64×2 network relates each zone to
about a third of the others, and to the average of all zones through the global
vector; 7 message-passing layers would relate every zone to every other.
Inferred, not measured: in China many threats are three or more borders away.

**How big published networks are.** AlphaZero's networks, and most that
followed them, are stacks of *residual blocks*. A residual block is two
convolutions (section 6.10), each a linear layer applied at every point of the
board to the vectors at and around that point, and the residual block adds their
result to its input. A message-passing layer here is two linear layers as well
(section 6.6), and where a convolution carries information one point further, a
message-passing layer carries it one border further. So residual blocks there
compare with message-passing layers here, and widths with widths. Parameters
compare too, since both kinds of network apply the same learned numbers at every
point or zone, but arithmetic grows also with the number of points: 361 in Go, 64
in chess, 37 zones here.

| Network | Game | Residual blocks or message-passing layers | Width | Parameters | FLOPs per network evaluation | Receptive field |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| [AlphaGo Zero](https://discovery.ucl.ac.uk/id/eprint/10045895/1/agz_unformatted_nature.pdf), first run | Go, 361 points | 20 | 256 | 23 million | 16 billion | 2.2 |
| AlphaGo Zero, second run | Go | 40 | 256 | 46 million | 33 billion | 4.4 |
| [AlphaZero](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphazero-shedding-new-light-on-chess-shogi-and-go/alphazero_preprint.pdf) | chess, 64 squares | 20 | 256 | 23 million | 3 billion | 5.6 |
| [KataGo](https://arxiv.org/abs/1902.10565), 2019 run, four sizes in turn | Go | 6, 10, 15, 20 | 96, 128, 192, 256 | 1, 3, 10, 24 million | 0.8, 2.2, 7, 17 billion | 0.8 to 2.3 |
| [DORA](https://arxiv.org/abs/2110.02924), a transformer | Diplomacy, 81 locations | 5 or 10 | 192 or 224 | 9 to 25 million | not worked out | the whole map in every block |
| [AlphaZero.jl](https://jonathan-laurent.github.io/AlphaZero.jl/stable/tutorial/connect_four/) | Connect Four, 42 points | 5 | 128 | 1.5 million | 120 million | 1.8 |
| [TD-Gammon 2.1](https://www.bkgm.com/articles/tesauro/tdl.html) | backgammon | 1 | 80 | about 20,000 | about 40,000 | the whole board in its one layer |
| This project, 64×2 | this game, 37 zones | 2 | 64 | 0.13 million | 3.4 million | 0.3 |
| This project, 256×8 | this game | 8 | 256 | 4.4 million | 173 million | 1.1 |
| This project, 512×16 | this game | 16 | 512 | 30 million | 1.3 billion | 2.3 |

The published networks' parameters and FLOPs are worked out here from their
published sizes, counting the convolutions' parameters and two FLOPs per
multiply-add of each convolution at every point, as section 9.3 counts this
network's; their output layers add little. DORA's parameters are as published;
TD-Gammon's are estimated from its 198 board inputs and a few more input features
(Sutton and Barto, section 16.1). This project's counts are for one of its three
networks and leave out the embedding tables (section 6.3), which have no
counterpart in those networks: 3.8 million parameters at 64×2, 15.2 million at
256×8 and 30.3 million at 512×16. The *receptive field* here is how many points
or borders the layers carry information, divided by the largest distance on the
board: 18 king steps in Go, 7 in chess, 6 in Connect Four and 7 borders here.
KataGo's networks, like this one through its global vector, also hand every point
a summary of the whole board.

Against these, the 64×2 network is small in every measure: a quarter of the
usual width of 256; an eighth of the parameters of KataGo's first network and
about a 170th of AlphaZero's; about a 220th of the arithmetic of KataGo's first
network and a 900th of AlphaZero's; and a receptive field of a third of the map.
A 256×8 network is about as large as the smallest published ones: more parameters
than KataGo's first two networks or AlphaZero.jl's, less arithmetic than
KataGo's, since it has 37 zones to their 361 points, and a receptive field of the
whole map. A 512×16 network has a little more than AlphaZero's parameters, under
half its arithmetic and the receptive field of KataGo's final network.

**What those sizes were enough for.** TD-Gammon 2.1's 80 hidden neurons played
backgammon at a strong master level after 1.5 million games. KataGo's first
network reached strong amateur strength after 0.4 million games, its second
strong professional strength after 1.0 million and its third superhuman strength
after 2.5 million, at searches of 1,600 nodes (tables 6 and 7 of its paper). In
two-player Diplomacy, each larger transformer DORA tried played better, up to
25 million parameters, and a graph network of 47 million like earlier Diplomacy
networks played worse than all three (table 2 of its paper), so the kind of
network mattered as well as its size.

**How the size was chosen.** None of these sizes follows from a rule; each was
found by trying sizes. KataGo began small and grew its network three times
during the run: it trained the next size on the same games and switched when the
larger network's loss caught up with the smaller one's, at 0.75, 1.75 and 7.5
days. In a study of AlphaZero on Connect Four and Pentago
([Neumann and Gros 2022](https://arxiv.org/abs/2210.00849)), strength grew as a
power of the number of parameters while compute lasted, and the number of
parameters $N$ that did best for a compute budget $C$ grew as

$$N \propto C^{0.62}$$

so ten times the compute called for about four times the parameters. Larger
networks also played better after the same number of games. Extrapolated, the
trend puts AlphaGo Zero and AlphaZero well below the best size for their
compute, by up to a hundred times, but the study's networks were small
multilayer networks on two small games, and its authors leave open whether the
trend carries over.

**Their searches and games.** The same systems searched more and played many
more games:

| System | Simulations per decision | Self-play games | Hardware and time |
| --- | --- | ---: | --- |
| AlphaGo Zero, first run | 1,600 | 4.9 million | 3 days |
| AlphaGo Zero, second run | 1,600 | 29 million | about 40 days |
| AlphaZero, chess | 800 | 44 million | 9 hours, 5,000 TPUs playing |
| KataGo, 2019 run | 600 to 1,000 on a quarter of the decisions, 100 to 200 on the rest | 4.2 million | 19 days, at most 28 GPUs |
| [Gumbel MuZero](https://openreview.net/forum?id=bERaNdoegnO), 9×9 Go | from 2 to 200; it learned even with 2 | not stated | not stated |
| DORA, two-player Diplomacy | an equilibrium search each turn | not stated | 192 GPUs, about a week per training stage |
| AlphaZero.jl, Connect Four | 600 | 75,000 | one GPU, about a day |
| TD-Gammon 2.1 | none; a 2-ply lookahead in play | 1.5 million | not stated |
| This project | 64 | at most about 500 per training run | the Mac |

A game here has about 1,000 decisions, many more than a game of chess or Go has
moves, so it holds more decisions to learn from, but its final score comes much
later. Published work on war and strategy board games is small: an
AlphaZero-style agent for a hex-and-counter wargame was trained on a 5×5 map
with two kinds of unit and grew weaker on larger maps
([arXiv 2502.13918](https://arxiv.org/abs/2502.13918)).

**What it would cost here.** On the Mac, at least about 51 days per 100,000 games
at 256×8 with 256 simulations and at least about 450 days at 512×16 with 800
simulations, both limited by its GPU in inference batches of 64 states
([section 9.3](#93-what-a-larger-network-and-a-longer-search-cost), whose rates
are upper bounds). Three months of eight-hour nights, about 720 hours, would
play at most about 59,000 games at the first size and 6,600 at the second.
AlphaGo Zero's first run played 4.9 million games, 49 times as many as 100,000,
and KataGo's 2019 run 4.2 million.

**Unmeasured:** whether a larger network or a longer search learns faster here
for the same compute, whether network depth or width matters more, and how many
games this game needs. In Hex, the strength a fixed amount of compute buys falls
predictably as the board grows, and compute spent in training can stand in for
search at play time ([Jones 2021](https://arxiv.org/abs/2104.03113)). Gumbel
search learned with a few simulations where plain search failed, so the search
budget and the search method are one question.

**Would settle it:** a ladder of training runs at growing sizes, each given the
same compute and compared in held-out evaluation (section 10), with the search's
targets checked as in
[the question on 64 simulations](#are-64-simulations-enough-when-there-are-many-legal-actions),
then repeated with more compute; or one long training run that grows its network,
as KataGo's did. Inferred from the published networks, not measured: a first
ladder would run from 64×2 through 256×8, the smallest of the measured sizes whose
layers reach across the map, to 512×16, a little more than AlphaZero's
parameters. The size that does best for a budget is the target for that budget,
and section 9.3's costs at that size say which part of a computer limits it, and
so what hardware it needs.

#### How should a count count?

**Now.** A feature value $a$ adds its feature's embedding times
$\operatorname{sign}(a)\ln(1 + |a|)$
([section 6.3](#63-the-embedding-layer-embeddings-and-embedding-tables)): 1 counts
0.69, 2 counts 1.10 and 10 counts 2.40. The formula was chosen, not compared.

**Alternatives:** counts in proportion, or separate features for count ranges
(1, 2 to 3, 4 to 7, more), so each range learns its own effect. **Would settle
it:** held-out value error on fixed data first, which is cheap, then games.

#### Is the final wealth gap the right goal?

**Now.** Each alliance maximizes its wealth minus the other two alliances'
combined wealth after the July 1941 game round, the approved objective
([plan](../plans/japan_china_full_rules_plan.md#wealth-definition-and-approved-accounting-decisions)).

**Measured.** In the [decision
review](../archive/records/decision_review_2026_10_31.md#the-objective-rewards-a-passive-japan),
a Japan that never attacks beat the scripted attacking Japan in 4 of 4 three-round
seeds and 3 of 4 eleven-round seeds. Japan's first attack makes every warlord join
China at once, ends the KMT–CCP civil war and costs about 100 IPP of units. So the
goal itself may teach a passive Japan, however well the networks learn.

On 24 held-out three-round seeds on 14 November, an untrained Axis network that
ended almost every phase at once beat the scripted Axis by 10.5 ± 2.3 points,
scoring higher in 19 seeds. After 792 three-round games of training, the Axis
moved and fought far more and scored 12.9 ± 2.2 below the untrained network
([record](../archive/records/three_round_training_2026_11_14.md)). Over eleven
game rounds on 16 held-out seeds on 18 November, the untrained Axis networks of
two runs scored +39.7 and +42.2 with 86 and 73 decisions a game, against +26.0
for the scripted Axis with 1,118. After 3.7 hours of training the two runs' Axis
networks made 856 and 780 decisions a game and scored +6.5 and +8.3, 33.2 ± 5.2
and 33.9 ± 4.1 points below their untrained networks
([record](../archive/records/one_network_comparison_2026_11_17.md#held-out-evaluation)).

**Would settle it:** the owner's decision on the objective. A changed objective
can be checked first with the same scripted comparison.

#### Are 64 simulations enough when there are many legal actions?

**Now.** A search runs 64 simulations, and the visit share each action at the
root received becomes the policy target (section 4.5).

**Measured** on 31 October: at Japan's opening, with 308 legal actions, the
search tried 63 of them, almost all once, and in an eleven-round game 60% of
Japan's Combat Movement decisions had at least 64 legal actions
([decision review](../archive/records/decision_review_2026_10_31.md#training-findings)).
Such targets say little more than which actions were tried. Since then Combat
Movement decisions have shrunk to about a third as many legal actions
([record](../archive/records/combat_movement_combats_only_2026_11_01.md)); the
spread of policy targets has not been measured again.

**Alternatives:** more simulations where there are many legal actions, fewer legal
actions per decision, or Gumbel root search, which the review suggests because it
was designed for fewer simulations than legal actions. **Would settle it:**
measuring the policy targets on today's decisions, then comparing learning at
equal compute.

#### Search-guided self-play or direct policy learning, and which opponents?

**Now.** AlphaZero-style: every decision is searched, and all three alliances play
with their latest network.

**Open.** The [plan](../plans/japan_china_full_rules_plan.md#2-training-approach)
keeps masked PPO, a policy trained without a search at every decision, as a
competing method, and older networks as extra opponents for when held-out
evaluation shows overfitting to the current ones. Neither has been tried.
**Would settle it:** the equal-compute comparison the plan describes.

#### Should the engine leave out actions that are never better?

**Now.** Since 5 November the engine leaves out two actions that do what another
legal action of the same decision does, at greater cost, on the user's decision:
a strategic rail move to a zone the unit also reaches by an ordinary move, which
spends rail capacity and ends the unit's movement, and the printed price once
Improved Construction offers the discount (RB 8.2.1 offers the discount or the
condensed stages). In random games they were 3.0% of legal actions and, in 1 game
of 240, 1,930 legal actions. The engine still offers copies of one action for each
of several identical units, and lets a player skip the free recruitment roll.

**Alternative.** Leave those out too:

| Action | Why it is never better | In random games |
| --- | --- | ---: |
| The same action for another of several identical units | the states differ only in the units' names | 10.2% of legal actions |
| Ending the Place Units Phase without the recruitment roll | the roll is free and every result helps (RB 12.7) | skipped 472 times in 48 games |

**The catch.** An action may go only if it is never better in any state, and some
that look so are not. Cargo kept aboard a landed air transport cannot be
carpet-bombed, since carpet bombing attacks only land units, so taking every unit
off its transport before the Place Units Phase would change the game. The user
kept that choice and instead barred upgrades that would leave a transport with
cargo it may not carry
([RCL-021](../../game_content/rules/clarifications.md#rcl-021-upgrading-a-unit-aboard-a-transport)).
Merging identical units touches the list of legal actions, the network input and
the search, so it needs its own check.

**Measured:** the percentages above
([record](../archive/records/never_better_choices_2026_11_05.md)). Fewer legal
actions would also help the 64 simulations of the question above. **Would settle
it:** the user's decision on the two left, then learning compared at equal
compute.

## 12. Glossary

Terms in the order the document introduces them. Each means one thing only; the
last two lists give the words that need a qualifier and the names the code and
the dated records use instead.

**The game (section 2)**

- **Alliance (player):** Axis, Allies or Comintern; each chooses for its nations.
- **State:** everything about the game at one moment, its position in a board
  game's words.
- **Decision:** a state where one alliance must choose an action.
- **Action:** one choice at a decision. A **legal action** is an action the rules
  allow there.
- **Chance event:** a state where the engine rolls dice.
- **Terminal state:** the end of the game, after the eleventh game round.
- **Game round:** one of the game's eleven rounds, the last in July 1941.
- **Final score:** an alliance's wealth minus the other two alliances' combined
  wealth at the end of the game.
- **Planning key:** a digest that identifies a state exactly.
- **Decision 612:** the running example: game round 5 of a game played on
  5 November, the Comintern choosing the CCP's Combat Movement from 5 legal
  actions.

**What a network gives (section 3)**

- **Network:** it turns a decision into three values and a probability for
  every legal action; one network serves all three alliances, or, with
  `--networks three`, each alliance has its own.
- **Policy:** how likely an agent is to choose each legal action.
- **Value:** a network's estimate of an alliance's final score, in hundreds of
  points.
- **Prior:** a network's probability for an action, as the search uses it.
- **Parameters:** all the numbers training adjusts: the weights and biases of
  the linear layers, the embeddings among them, and the identity embeddings.

**Search (section 4)**

- **Search (MCTS):** the simulations that pick an action at a decision.
- **Simulation:** one imagined walk forward from the root, on a copy of the game.
- **Root:** the current state, where every simulation of a search starts.
- **Search tree:** what a search remembers between simulations.
- **Node:** a state the search tree holds, with its planning key, the statistics
  of the actions tried there and a saved copy of the game at that state.
- **Visit count:** how many simulations played an action.
- **PUCT score:** an action's value term, its average result rescaled between the
  worst and best averages seen, plus its exploration term, a bonus from its prior
  that shrinks each time the action is tried.
- **Visit share:** an action's visit count divided by the number of simulations;
  AlphaZero's search probability.
- **Exploration noise:** random noise mixed into the priors at the root, during
  training.
- **Simulation depth:** how many actions and dice rolls a simulation played from
  the root before it stopped.
- **Depth limit:** the greatest simulation depth allowed, 16 in current runs; a
  simulation that reaches it stops and uses an estimate of the state there.

**The input (section 5)**

- **Input:** a decision turned into numbers: the non-zero zone, global and action
  feature values, and each legal action's zones.
- **Feature:** one numbered input slot with a fixed meaning. The code names it a
  column.
- **Feature value:** the whole number a decision gives a feature; only non-zero
  feature values are stored.
- **Feature family:** a group of features with one name pattern, such as `units`.
- **Zone features, global features, action features:** the three lists of
  features: 42,532 that every zone has, 4,076 about the state as a whole and
  12,627 that every legal action has.
- **Feature matrix:** one part of the input pictured as a matrix with one row per
  zone or per legal action, or a single row for the global features, and one
  column per feature.
- **Feature vector:** one row of a feature matrix: all the feature values of one
  zone, of the state as a whole or of one legal action.
- **Role:** the part of an action feature's name, such as `0_source`, that says
  how the action relates to the unit or zone a detail names.
- **An action's zones:** its source zone, the zone it starts from; its target
  zone, the zone it acts on; and its path zones.
- **Static features:** 39 per zone and 22 per directed border, the same in every
  state.
- **Layout version:** an identifier of the full set of features and static
  features; a network refuses inputs of another layout.

**The network (section 6)**

- **Vector:** a list of numbers. The vectors that describe a zone, the state as a
  whole or a legal action inside a network have as many numbers as the width.
- **Width:** how many numbers each of those vectors and each embedding has: 64 in
  a 64×2 network.
- **Linear layer:** a multiplication by a learned matrix, the layer's weights,
  plus a learned bias, usually followed by the GELU activation function.
- **Neuron and connection:** in the usual drawing of a layer, each input and
  output is a neuron, and each weight a connection from an input neuron to an
  output neuron.
- **Activation function:** a fixed function applied to each number a linear layer
  gives; here GELU, $x \Phi(x)$.
- **Layer normalization:** rescaling a vector to an average of 0 and a spread of
  1, then a learned scale and shift for each number.
- **Input layer:** the feature vectors as the network's input, one input neuron
  per feature.
- **Embedding:** the weights on the connections that leave one input neuron, one
  per output; for a feature, the learned vector added in wherever the feature has
  a non-zero value.
- **Embedding table:** an embedding layer's weights, a matrix with one row per
  feature: the zone, global and action embedding tables.
- **Embedding layer:** the network's first linear layer, which reads one feature
  vector, without bias or activation function; the zones, the global features and
  the legal actions each have their own.
- **Feature scaling:** the fixed formula $\operatorname{sign}(a)\ln(1 + |a|)$
  that turns a feature value $a$ into its input neuron's value.
- **Embedding lookup:** computing an embedding layer by fetching only the
  embeddings of its non-zero inputs, each times its input, and adding them up.
- **Identity embedding:** a zone's own learned numbers, as many as the width,
  which let the network tell zones apart.
- **Zone vector, global vector, action vector:** the vectors that describe a
  zone, the state as a whole and a legal action.
- **Message-passing layer:** one layer in which every zone hears from its
  neighbours along the borders; a 64×2 network has 2.
- **Network depth:** the number of message-passing layers.
- **Summary vector:** one vector of the state, from the global vector and the
  zone vectors' average and maximum.
- **Value head:** the linear layers that turn the summary vector into three
  values.
- **Policy head:** the linear layers that turn an action's combined vector and the
  summary vector into the action's logit.
- **Logit:** an action's or a group's raw preference, which a softmax turns into
  a probability.
- **Softmax:** turning logits into probabilities that add up to 1.
- **Hierarchical softmax, level:** the softmaxes by which action probabilities are
  built, one level after another: kind, what acts, how it travels, what it acts
  on, and the action.

**Training samples and training (sections 7 and 8)**

- **Training iteration:** one turn of the training loop: 24 games that ended (in
  the Mac profile) and the network update that trains on them. In self-play that
  never stops the games go on through the network update; in alternating
  training iterations they start together with the network held fixed, and the
  network update follows the last of them. The code and the dated records call a
  training iteration's games a batch.
- **Self-play that never stops:** training in which the game threads play one
  game after another while network updates run beside them, and every game takes
  up the new network at once (section 9.1; `--continuous`).
- **Training sample:** one saved decision: what the network read, who chose, how
  the search split its simulations among the legal actions and the final scores.
- **Policy target:** a training sample's visit shares, the action probabilities a
  network is trained toward.
- **Value target:** a training sample's final scores, divided by 100, the values
  a network is trained toward.
- **Loss:** a number that measures how far a network's outputs are from the
  training samples' targets: the value loss, a squared error, plus the policy
  loss, a cross-entropy. Training lowers it.
- **Cross-entropy:** the policy loss, lowest when the action probabilities equal
  the visit shares.
- **Kullback–Leibler divergence (KL divergence):** the cross-entropy less the
  visit shares' own entropy: zero only when the action probabilities equal the
  visit shares.
- **Gradient:** for one parameter, how fast the loss would change if that number
  were raised a little.
- **Learning rate:** how far Adam moves a parameter in one Adam step while its
  gradients keep their sign: 0.001.
- **Adam step:** one change of every parameter of a network by the Adam
  optimizer: against the average of its recent gradients, divided by their
  typical size, times the learning rate.
- **Replay buffer:** the latest training samples, at most 8,000, that training
  draws from.
- **Minibatch:** the 32 training samples one training step draws at random from
  the replay buffer; the training command's `--batch-size`.
- **Training step:** one minibatch, read by the network, and one Adam step. The
  training command names the number of training steps per network update
  `--epochs`.
- **Network update:** the training steps after a training iteration's games, 525
  in the Mac training command; in self-play that never stops they run beside the
  games.
- **Generation:** the network after a given number of network updates; a fresh
  network is generation 0.
- **Model export:** the saved network after a network update.
- **Checkpoint:** a full save of a training run, for resuming it.

**Running it (section 9)**

- **Game process:** an operating-system process that plays several games, one
  per game thread; the Mac profile runs 6 of 4.
- **Game thread:** a thread that plays one game, searching at every decision.
- **Concurrent games:** the games being played at the same moment, each holding
  its search tree in memory.
- **Inference server:** the process that runs the network for every game's
  states and sends each game thread its priors and values; the tools and the
  dated records name it the coordinator.
- **Network evaluation:** a network's output for one state, its priors and values;
  a search asks for about one per simulation.
- **Inference request:** a game thread's request for one state's network
  evaluation.
- **Shared memory:** memory that two processes can both read; a game thread
  writes each inference request's arrays into its own block of it.
- **Pipe:** a channel the operating system keeps between two processes; each
  game thread sends its inference requests' notes and receives its replies
  through its own.
- **Inference batch:** the states the inference server evaluates together: every
  inference request waiting when it starts, answered in one forward pass. Its
  number of states is the *inference batch size*.
- **Collating:** joining the arrays of an inference batch's states end to end for
  one forward pass, with each state's indices shifted to point into the joined
  arrays; with a network for each alliance, each network's states together.
- **Forward pass:** one run of the network over all the states of an inference
  batch at once. Each state keeps its own vectors, but every PyTorch call works on
  the arrays that hold them all.
- **PyTorch call:** one instruction to PyTorch, the library that does the
  network's arithmetic, to apply one function, such as a matrix product or GELU,
  to whole arrays at once. A forward pass is a list of 138 to 846 PyTorch calls,
  however many states it holds; a PyTorch call is not a training step.
- **Call overhead:** what a PyTorch call costs whatever the size of its arrays:
  Python's and PyTorch's work to check them, choose a routine and make room for
  the result, and on the GPU, handing the PyTorch call over.
- **FLOP (floating-point operation):** one multiplication or one addition of two
  numbers.
- **Multiply-add:** one input times its weight, added to an output's sum: two
  FLOPs. A linear layer is made of them; the linear layers of a 64×2 forward pass
  do about 3.4 million FLOPs for each state with 14 legal actions.
- **Request handling:** the inference server's work for an inference batch outside
  the forward pass: reading the inference requests' notes from the pipes and
  their arrays from shared memory, collating, turning the outputs into priors and
  sending the replies through the pipes.
- **Decisions per hour:** decisions searched per hour across all concurrent games,
  the measure of self-play speed for one network and search. It falls in
  proportion to the search's simulations, and with the network's size only where
  the network, not the cores, limits (section 9.3).
- **Windows PC:** the owner's second training machine, with an NVIDIA GPU on
  which its inference server runs the forward passes (section 9.2).
- **CUDA:** NVIDIA's software for computing on its GPUs.

**The inference server's levers (section 9.3)**

- **Grouped matrix product:** one PyTorch call that multiplies each network's
  states by that network's own weights.
- **Padded product:** one batched matrix product of three networks, each
  network's states padded with empty ones to the largest network's count.
- **Compiling a forward pass:** having PyTorch's compiler, `torch.compile`, turn
  a forward pass's PyTorch calls, once and ahead of time, into fewer routines that
  each do the work of several PyTorch calls; built for one network's zone and
  position layers (`--compiled-forward`).
- **State bucket:** one of the fixed numbers of states the zone and position
  layers are compiled for; an inference batch is padded with empty states to the
  next one.
- **CUDA graph:** a forward pass's PyTorch calls recorded once on an NVIDIA GPU and
  replayed with a single call overhead.
- **Half precision:** numbers of 16 bits, with about 3 significant digits,
  instead of the 32 bits, with about 7, that the network computes with.
- **Second inference server:** a second inference server serving half the game
  processes.

**Measuring strength and size (sections 10 and 11)**

- **Held-out evaluation:** games of fixed networks, without exploration noise,
  against scripted opponents on seeds training never used; it measures playing
  strength.
- **Explained variance:** one minus a value loss divided by the variance of the
  same games' final scores: the share of the final scores' spread that the
  network's values account for, 0 for always predicting the mean and 1 for
  exact values.
- **Residual block:** two convolutions whose result is added to their input;
  AlphaZero's networks are stacks of them, as this one is a stack of
  message-passing layers.
- **Receptive field:** how many points or borders a network's layers carry
  information, divided by the largest distance on its board: 0.3 for a 64×2
  network here.

**Words that always carry a qualifier**

| Word | Its meanings here, each always written in full |
| --- | --- |
| step | a *training step* (section 8.4); an *Adam step* (section 8.3). A simulation's actions and dice rolls are counted as its *simulation depth*. |
| batch | a *minibatch* of training samples (section 8.4); an *inference batch* of states (section 9.2) |
| round | a *game round*, one of the game's eleven |
| evaluation | a *network evaluation* (section 9.2); *held-out evaluation*, which measures strength (section 10) |
| update | a *network update* (section 8.4); a message-passing layer changes a zone vector or the global vector by a *correction* (section 6.6) |
| depth | *simulation depth* (section 4.7); *network depth* (section 6.6) |
| score | the *final score* (section 2.4); the *PUCT score* (section 4.3) |
| value | a network's *value* (section 3); a *feature value* (section 5.1) |
| unit | a game unit, such as mountain infantry; the network's units are called *neurons* (section 6.2) |
| move | a unit's movement in the game, as in Combat Movement or an ordinary move; a choice at a decision is an *action* |
| row | a row of a named matrix or table: a feature matrix's row is a *feature vector*, an embedding table's row an *embedding* |

**Names in the code and the dated records**

| Name there | This document's term |
| --- | --- |
| coordinator (`tools/profile_coordinator.py`, the dated records), `SharedEvaluatorServer` | inference server |
| round (`tools/replay_coordinator_rounds.py`, the dated records) | inference batch |
| pass, network pass | forward pass |
| batch, training batch (supervisor, `--transitions-per-batch`, the dated records) | a training iteration's games |
| position (`batch.positions`, `PositionScope`, `failed-positions/`, the dated records) | state |
| column (`zone_columns`, `global_columns`, `action_columns`) | feature |
| question, answer (the dated records) | feature, feature value |
| row (the dated records) | embedding |
| option (`option_table`, `option_encoder`) | legal action |
| `--batch-size` | minibatch size |
| `--epochs` | training steps per network update |
| `--max-depth` | depth limit |
