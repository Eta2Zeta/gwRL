# Japan-China full-rules theatre: objective, decisions and open work

The approved target, scenario decisions and wealth objective of the regional
campaign, the recorded rule decisions, the verification policy and the open work.
Milestones M0–M11 implemented the rules: see the [M0 review](../m0/README.md)
and the milestone pages linked from the [README](../../README.md). The
[project history](../history.md) records how; commit `037cb60` keeps this
plan's earlier milestone narrative and status notes. Reusable official-rule
decisions live in the
[shared rule clarification register](../../game_content/rules/clarifications.md)
with stable RCL IDs. Record future rule conflicts there for the user's developer
reports.

## 1. Target and boundaries

Build a rules-faithful regional campaign containing Japan, KMT, CCP, all eight
Chinese warlords, and the relevant Mongolian and coastal geography. Use the
existing global map JSON as the geography source, extracting a smaller scenario
through a lossless bridge. Implement all units, facilities and mechanics these
participants can legally use, including capabilities unlocked later by technology
or Chinese evolution to Major Power.

The same rules engine must serve small tests, the regional campaign, and a later
larger map. The small campaign is a smaller **scenario**, not a second simplified
set of combat, movement or production rules.

This is a deliberately **closed regional scenario using v4.3 mechanics**, not a
simulation of the complete global game. Select explicit tiles from the global
map and remove every neighbor outside that set. There are no outside interfaces,
off-map movement, invisible reinforcements, required historical event schedules,
or substitute routes. A rule whose necessary nation, location or route is absent
is explicitly inactive in this profile; its reusable engine handler can still be
implemented for larger scenarios. The authoritative global map retains its real
outside connections; only the extracted copy is closed.

### Approved scenario decisions

| Decision | Current contract | Consequence |
| --- | --- | --- |
| Start | **July 1936**, using the approved official setup projection | 99 deployed pieces: Japan 48, KMT 12, CCP 5, warlords 32, Mongolia 2; 3 setup factories and 19 static facilities. Both ordinary Japanese queue ships are retained with 5 IPP already paid each. |
| Finish | **After the complete July 1941 round** | Eleven half-year rounds: July 1936, January/July 1937-1940, January/July 1941. Finish all included nation turns, reactions and collection before scoring. |
| Learning agents | **Axis, Allies and Comintern** | Three alliance-level policies, not one policy per nation. Nation turns, treasuries, legal relationships and minor controllers remain separate game concepts. |
| Objective | Each alliance maximizes its wealth minus the other two alliances' combined wealth | This is a three-player general-sum benchmark, not territorial conquest or the official global victory condition. |
| Boundary | Closed induced subgraph with all excluded neighbors deleted | No external agents, boundary contracts, aid interfaces or fabricated connections are required. |
| Geography | China/Mongolia area **excluding Tannu Tuva and Hong Kong**, including Manchuria and Korea; Tokyo, Honshu, Hokkaido, Kyushu, Okinawa; P14, P15, P16, P32, P33, P41 | 37 nodes: 31 land and 6 sea; the explicit manifest is authoritative. No automatic addition of reachable global neighbors. |
| Excluded participants/mechanics | No FEC or USSR accounts; no convoy play, interdiction or Kido Butai | Mongolia retains direct Comintern control and the USSR turn position; normal MAP, blockades and independently applicable naval movement/combat remain. |

The default decision mapping is Axis -> Japan, Allies -> KMT, Comintern -> CCP.
Other included national/minor decisions are routed to the alliance entitled to
control them **under the rules**. Mongolia is not a CCP province or a Chinese
warlord. Warlord alignment, national identity and treasury ownership are never
collapsed into the three learning-agent labels. Reward rivalry does not itself
declare war or override the Chinese Truce.

Mongolia is directly controlled by Comintern and takes its movement and
recruitment phases in the normal USSR turn position, as if USSR were present:
**CCP -> Mongolia (USSR slot) -> Japan -> KMT**. Its identity remains Mongolian;
this timing does not create a Soviet participant, account, possession or unlock.

### Wealth definition and approved accounting decisions

For alliance `i`, the approved income/asset weighting gives:

$$
\begin{aligned}
W_i ={}& \text{current income rate}_i \\
&+ 0.1 \times \bigl(\text{completed unit value}_i + \text{completed infrastructure value}_i + \text{treasury}_i + \text{paid unfinished construction}_i\bigr)
\end{aligned}
$$

$$
R_i = W_i - \sum_{j \ne i} W_j \qquad \text{(the sum runs over the other two alliances)}
$$

$$
\text{completed asset value} = \text{purchase price} - \text{remaining repair price}
$$

The user confirmed income means the **current income-per-turn rate**, not
cumulative collections; one point of that rate has the weight of ten IPP of
assets. Damaged units/facilities use purchase price minus their remaining repair
price; undamaged assets have zero repair deduction. Official setup units and
facilities count even though the learner did not buy them. A destroyed piece is
absent, not a surviving asset. No extra depreciation/floor convention is assumed.

Treasury and paid unfinished construction remain included at the same 0.1 asset
weight in the approved contract. This keeps spending cash on a normally priced asset from
changing wealth merely because its category changed. Repairing an asset similarly
reduces cash while increasing its net value. Do not substitute historical income
or pay the full wealth score repeatedly every turn. The adopted construction
policy scores cumulative already-paid amounts while a project is unfinished.
At completion, replace that entry with the full completed catalog value; do not
count both. The [source reconciliation](../m0/source_reconciliation.md)
establishes 5 IPP already paid for each setup queue ship; do not debit these past
payments from initial cash. Shared facility IDs and rail borders are
valued once, not once per directed access edge. Purchase-price tables for setup-only
types/discounts remain in section 3 and the M0 review. The user approved controlled
minor assets going to their controlling alliance and uncontrolled unaligned
assets going to nobody, without granting extra collection rights. Starting cash
is theatre-adjusted: Japan 15, KMT 6, CCP 2; minors zero; no FEC/USSR accounts. The capped-local
formula is documented in M0 as a scenario derivation, not an official setup rule.

On **21 October 2026**, the user approved the remaining city and railway scoring
choices. A city label has no additional asset price; its income and distinct
facilities still count. Count each undirected railway border once and split its
value 50/50 between the endpoint possessors. Endpoints credited to the same
alliance aggregate to the full value; an uncontrolled minor's share counts
toward nobody. This is scoring attribution only, with no change to railway
access, ownership or movement permissions.

These returns do **not** sum to zero: `sum(R_i) = -sum(W_i)`. Total wealth changes
with production, collection and destruction, so a three-value vector is required;
negating one opponent's value cannot reconstruct another alliance's objective.
This is a finite-horizon wealth benchmark, not a promise of historical strategy
or convergence to one globally best multiplayer policy.


## 2. Training approach

No learning algorithm has yet been established as best for the full campaign.
The user discussion on 21 October keeps two serious candidates: modern
AlphaZero-style neural-guided stochastic search, and a masked/factorized PPO
policy trained against the same opponent pool without search at every training
decision. Compare strength under equal hardware, training time and decision-time
budgets, using held-out positions, opponents and dice seeds. PPO is a competing
baseline, not merely a fallback. See the [PPO paper](https://arxiv.org/abs/1707.06347).

Three sides do not make search-guided self-play unusable. Its candidate branch
keeps neural policy/value guidance, search-improved move targets and self-play,
with three alliance returns and explicit dice. Consider limited-budget search
and sampled-action improvements against the exact search tests; neither newer
algorithms nor earlier results establish a winner for GW36.
The following stages describe that search-guided candidate and its opponent
pool; comparable direct-policy training uses the same authoritative engine,
objectives and evaluation conditions.

AlphaZero did not permanently assign a frozen policy to one color while training
the other. One network played both sides, guided by MCTS. Search produced policy
targets; completed games supplied outcome targets; training updated the network
and later self-play used its latest parameters. The older **AlphaGo Zero** used a
best-player promotion gate: a candidate replaced the incumbent after winning at
least 55% of their evaluation games. AlphaZero removed that gate and continuously
updated a single network. These are distinct procedures. See the [original
AlphaZero paper, page 3](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphazero-shedding-new-light-on-chess-shogi-and-go/alphazero_preprint.pdf).

Multiplayer AlphaZero has been demonstrated in two small three-player games;
that establishes feasibility, not a convergence guarantee for this campaign.
[Petosa and Balch, 2019](https://arxiv.org/abs/1910.13012). OpenSpiel provides an
independent implementation reference for n-player, general-sum MCTS with chance
nodes and decision-maker-indexed returns. Borrow those conventions, not its
unrelated exploration defaults: retain our tested FPU/PUCT behavior.
[OpenSpiel MCTS](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/algorithms/mcts.h).

### Synchronized self-play

Training uses this synchronized loop, checked first against exact deterministic
and stochastic three-side search fixtures:

1. Keep one policy for each of Axis, Allies and Comintern, with compatible action
   encoding and three-component value predictions.
2. Freeze a snapshot of **all three** policies for a rollout batch. Their legal
   nation/minor decisions produce complete self-play episodes, MCTS visit targets
   and terminal wealth-gap vectors. No policy changes halfway through that batch.
3. Train all three policies from the batch/replay data, routing policy-loss samples
   to the alliance that made each decision. Value targets retain all three sides.
4. Publish the three updated snapshots together and generate the next batch.
   Thus opponents improve between batches; none is the permanently frozen side.
5. Archive checkpoints from the start and evaluate separately against fixed
   scripted and historical **pairs** of opponents, with held-out dice. Compare
   each side's expected wealth gap under the same opponent combinations, not
   scores against opponents that change between evaluations.

At each ordinary search decision, choose using the acting alliance's component
of the value vector (a Max-n-style convention). The two other alliances each
optimize their own wealth gap; do not combine them into a single opponent that
jointly minimizes Japan's reward. This also handles defender choices and multiple
consecutive decisions by the same alliance. At chance nodes, sample the actual
rule-defined dice distribution rather than select favorable outcomes. Keep value
outputs in a fixed alliance order and fixed positive scale; no zero-sum sign flip
or clipping that changes the wealth objective.

### Archived opponents when evaluation shows overfitting

Latest-only co-training can learn to exploit a narrow set of current opponents,
then forget earlier counterstrategies. A small opponent pool is the next planned
robustness layer, not a second unrelated learning algorithm:

- Retain a bounded, diverse set of checkpoints for each side plus simple scripted
  baselines. Mix some historical-opponent games into current self-play; select
  the mix using measured forgetting/cross-play results, not an assumed optimal
  percentage or a huge default training job.
- Rotate the current learner: one game may train Axis against a frozen Allies/
  Comintern pair; another trains Allies; another Comintern. All sides improve
  across training batches; none stays the fixed opponent indefinitely.
- In these fixed-opponent best-response games, the learner's search must sample
  the frozen opponents' **actual deployed action distributions**. Do not secretly
  re-optimize an old opponent with current Max-n search. If a deployed opponent
  includes MCTS, its model/version, search settings and budget are part of the
  opponent policy; a raw neural prior is not an equivalent replacement.
- Record both opponent identities and search modes with experience. Keep recent
  replay for latest-self-play targets; use profile-conditioned value estimates
  or explicitly separated training data/value models for fixed-opponent tasks.
  A board state alone does not determine its value under different continuation
  policies; do not silently mix incompatible targets or reuse their search trees.

This borrows the opponent-mixture motivation of Policy-Space Response Oracles
(PSRO), not its full empirical-game/meta-strategy machinery. Full PSRO would add
payoff estimation across many policy combinations and a meta-solver; that is
unnecessary for the first local implementation. [Lanctot et al., NeurIPS 2017](https://papers.nips.cc/paper_files/paper/2017/hash/3323fe11e9595c09af38fe67567a9394-Abstract.html).

### What success means, and the compute comparison

- First learn short horizons of the same campaign, then increase the horizon to
  the full July 1941 scenario. Do not substitute
  simplified combat or transfer old incompatible value targets/checkpoints blindly.
- Evaluate each side across fixed opponent pairs, several dice seeds and training
  seeds. Report raw wealth components, mean gap, uncertainty, weaker matchups and
  performance with and without search. In a general-sum multiplayer game, a single
  aggregate win rate or rising co-training reward is not sufficient evidence.
- Periodically test an approximate best response: hold two opponents fixed and
  see how much a fresh/improved policy for the third can gain. Repeat for all
  sides. This measures discovered exploitability, not an exact equilibrium proof.
- Start with terminal wealth targets and no arbitrary kill/purchase bonus. Any
  later dense shaping must preserve the stated terminal objective. Test accounting
  for repair, construction completion, setup pieces and captured facilities.
- Compare search-guided training against masked PPO with side-specific
  policies/value estimates and the same opponent pool and objectives. Measure
  strength per training time and decision cost; also test search added to a
  directly learned policy. No candidate is assumed to win beforehand.
  A cooperative shared-reward algorithm is not a drop-in fit for these rival sides.

The aim is **robust performance against a stated, measured opponent distribution**.
There is no promised uniquely best strategy independent of the other two players,
nor a practical guarantee that this self-play procedure converges to equilibrium.

Freezing rollout snapshots is an engineering choice for reproducibility and
consistent search targets. Later asynchronous collection can be considered after
correctness and profiling. Policy parameter sharing across alliances is optional
future experimentation; three decision-making sides are the fixed contract.

### Closed-map applicability policy

The map is deliberately local. No external-world interface is a prerequisite for
this campaign. Missing Burma/Ledo/USSR rail paths, absent aid senders, U.S. trade
conditions, excluded holdings and global event prerequisites do not create
resources, routes or active abilities. Record the corresponding rule as inactive
with its missing prerequisite. The shared engine may implement/test such handlers
on separate complete fixtures for future expanded maps.

Included Formosa and Mongolia retain their source national
identity; Chinese home-country membership alone does not transfer ownership or
give permission to attack. Setup/political interpretation must be resolved where
needed, rather than answered by expanding the map or inventing an outside turn.
Tannu Tuva is not included and its political ambiguity is deferred.

## 3. Recorded rule decisions

1. **Remaining valuation-table details:** current income rate, asset weight 0.1,
   purchase-price-minus-repair valuation and inclusion of setup assets are decided.
   Transcribe prices/repair costs and reconcile non-purchasable setup types,
   discounts and upgrades without assigning setup assets zero merely
   because they were initially free. Cash and paid construction use the same 0.1
   coefficient as the explicit interpretation in section 1. Unpaid future
   construction obligations are not completed assets.
   Minor attribution is now approved: controlled/aligned assets go to the legal
   controller's alliance; uncontrolled unaligned assets go to nobody. Setup-only
   values are adopted: Torpedo Boat Destroyer 5 IPP and Coastal Submarine 4 IPP.
   City and railway scoring were approved on 21 October 2026: city labels have no
   additional asset price; each undirected railway border counts once, split
   50/50 between endpoint possessors. Same-alliance endpoints aggregate to full
   value, and an uncontrolled minor's share counts toward nobody. The railway
   split affects scoring only.
2. **Initial local accounts/setup:** theatre-adjusted cash is authorized and M0
   uses Japan 15, KMT 6 and CCP 2; FEC is excluded. Both ordinary Japanese national
   queue ships are retained and score their cumulative already-paid amounts.
   Source reconciliation establishes 5 IPP paid for each ship, with 5 remaining
   for the Heavy Cruiser and 10 for the Fleet Carrier. USA-triggered Light Carrier
   entries are excluded and carrier attachments are recorded in M0.
   The user chose official pieces on included tiles only; do not import outside
   forces or an assumed full-global budget.
   Use the fixed July 1941 full-round deadline; no extra early terminal rule is
   introduced. Both ships use eligible supplied shipyards; Fleet Carrier placement
   requires a Major Shipyard. P15's Fleet Carrier carries one Fighter and one
   Tactical Bomber; the Light Carrier carries one Fighter.
3. **Warlord foreign-war rolls, adopted RCL-003:** always resolve each whole
   warlord once. Evaluate relevant neighbors across its territories and apply the
   existing alignment table once; the result covers all its territories and units.
4. **Influence spending, adopted RCL-002:** pre-roll spending is capped by the
   unmodified success threshold. Preserve the natural-12 backfire and
   beginning-of-turn influencing-zone requirement.
5. **CCP Soviet route, closed RCL-004:** the user reported on 17 October 2026 that
   the developers fixed the wording for the next version; no publication or version
   number has been independently checked. The mechanic remains unchanged:
   during Production require an undamaged
   railroad from CCP-possessed to Soviet-possessed land, and place qualifying
   purchases in connected CCP-possessed territory. Generic river/sea supply is
   insufficient. The separate **income bonus** requires Soviet Home Country.
   Both abilities are inactive in this USSR-excluded campaign; Mongolia's
   identity and USSR-slot turn do not create Soviet possession.
6. **Map/political uncertainties:** Kobdo-Novosibirsk, southern Sinkiang/Himalayan contacts,
   Sinkiang-to-Eastern Kazakhstan's river penalty, and Tannu Tuva identity remain
   unresolved in the source map. Excluded external edges are cut away, not
   certified by copying. Tannu Tuva is explicitly excluded; defer its national
   identity/home-country/controller interpretation to a future expanded profile.
7. **Rail damage implementation:** all drawn tracks on the chosen border are
   affected. Implement targeted-side ownership, repair responsibility and terrain
   caps from the reconciled sources in the later catalog/movement/economy/combat
   milestones, without bringing back named railroad segments.
8. **In-scope Japanese setup:** preserve the audited starting forces and queue
   stages; no unprinted in-port, damage, cargo or MAP status is invented.
   Printed setup totals include queued ships; do not also instantiate them on-map.
9. **Choice explosion:** player-selected casualties, paths and grouped attacks can
   dominate search. Use equivalent-unit grouping and staged choices, never illegal
   pruning disguised as a game rule.
10. **Stochastic learning:** use exact probability fixtures and held-out evaluations;
   neither deterministic fractional combat nor memorized dice seeds proves robust play.
11. **Version conflicts:** retain source versions and documented interpretations;
    changes invalidate affected rule fixtures and training/checkpoint compatibility.
12. **Kamikaze source check closed:** the ability activates when USA reaches
    Wartime Income. The supposed alternative trigger was our misreading of the
    parenthesized Light Carrier build-queue footnote, not conflicting Kamikaze
    rules. See the shared register's closed-source-check section. No outside
    U.S. event is fabricated for this campaign.

M0 is verified and frozen; source
reconciliation records numeric queue payments and research thresholds. Ship values, queue
scope and scoring, Mongolia timing, starting-cash adjustment, controlled-minor
attribution, city/rail scoring and RCL-002–003/009 are recorded decisions;
RCL-001 now follows the developer’s corrected airborne sequence;
RCL-004–008 and RCL-011 are closed after source/developer checks. RCL-010
remains a campaign interpretation pending developer clarification. RCL-012 is closed: combat roles follow the reported developer ruling, and the
user clarified that attacking KMT has the same elimination consequence after
automatic termination.
RCL-013 is adopted and implemented. RCL-014 now follows the developer clarification
supplied on 23 October 2026: evacuating ships defend and the fleet already at sea
attacks. RCL-015 remains provisionally adopted pending developer clarification.
Tannu Tuva is excluded and is not a blocker.

## 4. Verification policy

Use these layers of verification throughout:

- **Data:** duplicate IDs/keys, valid references, field-preserving projection,
  faction identity, setup totals and national availability.
- **Rules:** a positive case, prohibited case and timing/exception case for each
  applicable clause; explicitly scripted dice for branch coverage.
- **Probability:** exact enumeration for tiny chance events and statistical checks
  for samplers. The test oracle must not simply call the implementation it tests.
- **State:** clone/replay/hash integrity, no accidental hidden information, and
  identical decisions through C++ and Python interfaces.
- **Campaign:** reviewed full-turn traces, random-legal-action stress tests,
  adversarial direct invalid actions, accounting and conservation invariants.
- **Learning:** known-answer puzzles, held-out opponents/seeds, reward-hacking
  checks, training resumption and throughput measurements.

## 5. Open work

- **Playing strength.** No run has yet shown robust strength. Expand learning and
  held-out evaluation across training and dice seeds, starting positions,
  horizons and opponent pairs before claiming it (section 2).
- **Objective.** The [decision review](../stage_a/decision_review_2026_10_31.md)
  found that the approved terminal wealth-gap objective rewards a passive Japan.
  How to address that is open.
- **Opponents and algorithms.** Add archived opponents if evaluation shows
  overfitting, and compare search-guided training with masked PPO under equal
  compute (section 2).
- **Rules.** RCL-010 and RCL-015 await developer clarification; Tannu Tuva's
  identity is deferred to a future expanded map.

## Sources

Rule sources in `game_content/rules/`:

- [Global War 1936 v4.3 Rulebook](<../../game_content/rules/Global War 1936 v4.3 Rulebook.pdf>): pp. 5-7 definitions/home country; pp. 10-17
  geography, movement and supply; pp. 18-19 setup and July 1936 start; pp. 26-31
  relations/warlords; pp. 35-44 war, truce and sequence; pp. 45-82 production,
  combat, movement and placement; pp. 83-99 units/facilities; p. 101 Chinese Civil
  War/evolution; national special abilities in chapter 15.
- [Japan national sheet](<../../game_content/rules/GW36 - NRS - Japan v4.3.pdf>): overview, income, objectives, national abilities,
  build charts and setup.
- [KMT national sheet](<../../game_content/rules/GW36 - NRS - KMT v4.3.pdf>): evolution, Burma/Ledo roads, low morale, production,
  minor/major build charts and setup.
- [CCP national sheet](<../../game_content/rules/GW36 - NRS - CCP v4.3.pdf>): evolution, recruitment, influence, Soviet connection,
  minor/major build charts and setup.
- [Neutrals setup chart](<../../game_content/rules/Global War 1936 v4.3 Neutrals setup chart.pdf>): neutral/Mongolian setup details
  where applicable; cross-check against the Chinese national setup sheets.
- FEC/USSR national sheets where relevant to included territory identity/minor
  control or the applicability ledger, not to create outside interfaces or agents.
- [Original AlphaZero paper](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphazero-shedding-new-light-on-chess-shogi-and-go/alphazero_preprint.pdf),
  page 3, for the continuous latest-network self-play versus AlphaGo Zero
  promotion-gate distinction. The three-policy batch scheme here is our proposed
  adaptation, not a claim about the original implementation.
- [Multiplayer AlphaZero](https://arxiv.org/abs/1910.13012), for limited empirical
  evidence of three-player adaptation; [OpenSpiel MCTS](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/algorithms/mcts.h),
  for concrete multiplayer/chance search conventions; and [PSRO](https://papers.nips.cc/paper_files/paper/2017/hash/3323fe11e9595c09af38fe67567a9394-Abstract.html),
  for opponent-mixture training and overfitting motivation, not a claim that we
  have implemented a league or a game-theoretic solver.
