#pragma once

#include "game/campaign.hpp"
#include "game/zone_encoding.hpp"

#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace game::campaign {

// The search over one campaign decision, as the learning system's design
// document describes it (docs/design/README.md, "The search"). It runs a whole
// decision's simulations without returning to Python. It is the search of
// studies/shared/multiplayer_mcts.py (VectorMCTS, multiplayer mode, a new tree
// each decision) on the declaration-offer scheduling of
// studies/shared/campaign_adapter.py: given the same network outputs and seed it
// makes the same choices, draws the same random numbers (PythonRandom) and
// returns the same numbers, which tests/test_campaign_native_search.py checks,
// when it asks after each simulation (SearchSettings::simulationsPerRequest).

using SearchValues = std::array<double, 3>;  // Axis, Allies, Comintern, as allianceOrder.

// A position the search asks about, one of several sent together
// (SearchEvaluator::evaluateMany), and its answer.
struct SearchQuestion {
    std::shared_ptr<const ZoneInput> input;  // Null for an evaluator that reads no input.
    int actor{-1};
    std::size_t options{0};
};

struct SearchAnswer {
    std::vector<double> priors;
    SearchValues values{0.0, 0.0, 0.0};
};

// Answers the search's network evaluations. `actor` is the alliance choosing at
// the position (0 Axis, 1 Allies, 2 Comintern), or -1 at a chance position,
// which is rated for its value only and has no options.
class SearchEvaluator {
  public:
    virtual ~SearchEvaluator() = default;
    // Whether evaluate reads the zone input; one that does not is given none.
    virtual bool readsInput() const { return true; }
    // Fills `priors` with one weight per option, in the input's option order.
    virtual void evaluate(const std::shared_ptr<const ZoneInput>& input, const std::string& layout, int actor,
                          std::size_t options, std::vector<double>& priors, SearchValues& values) = 0;
    // Several positions, answered in order: by default one evaluate call each.
    // The inference client sends them to the inference server in one request.
    virtual void evaluateMany(const std::string& layout, const std::vector<SearchQuestion>& questions,
                              std::vector<SearchAnswer>& answers) {
        answers.resize(questions.size());
        for (std::size_t i = 0; i < questions.size(); ++i)
            evaluate(questions[i].input, layout, questions[i].actor, questions[i].options, answers[i].priors,
                     answers[i].values);
    }
};

// The untrained baseline: every option weighs the same and every value is zero
// (UniformEvaluator in studies/shared/multiplayer_mcts.py).
class UniformSearchEvaluator final : public SearchEvaluator {
  public:
    bool readsInput() const override { return false; }
    void evaluate(const std::shared_ptr<const ZoneInput>&, const std::string&, int, std::size_t options,
                  std::vector<double>& priors, SearchValues& values) override {
        priors.assign(options, 1.0);
        values = {0.0, 0.0, 0.0};
    }
};

// The declaration-offer scheduling around the engine's own decision
// (CampaignAdapter): the alliances that have passed on the offer now open, as
// bits 1 << alliance number, and the order in which alliances are offered their
// declarations, by alliance number.
struct SearchSchedule {
    std::uint8_t passed{0};
    std::array<int, 3> order{0, 1, 2};
};

struct SearchSettings {
    int simulations{128};
    double cPuct{1.5};
    int maxDepth{256};
    std::uint64_t seed{1};
    bool rootNoise{false};
    double dirichletAlpha{0.3};
    double dirichletEpsilon{0.25};
    bool searchForcedRoot{false};  // Simulate a one-action root anyway.
    // Simulations whose positions go to the evaluator together, in one request
    // (the design document's section 4.7, "Several simulations in one request").
    // Each one's path counts as visits that lost (a virtual loss) while the
    // others choose theirs, so that they spread over the tree; a simulation that
    // would ask about a position already asked about is dropped and another one
    // walked. One plays the simulations one after another, VectorMCTS's way.
    int simulationsPerRequest{1};
    // Whether the budget counts the visits the root's actions already hold from
    // a reused tree: the search then runs only as many new simulations as bring
    // them to `simulations` visits, and none when they already hold that many.
    // Self-play's fast searches count them (Q-023, the design document's section
    // 7.1); without it every search runs `simulations` new ones.
    bool countReusedVisits{false};
};

struct SearchOutcome {
    // The root's options, in the order of CampaignAdapter.legal_actions, by the
    // adapter's action ids.
    std::vector<std::string> actionIds;
    std::vector<int> visits;
    std::vector<double> policy;
    std::vector<double> priors;
    std::optional<SearchValues> values;  // None when a one-action root was not searched.
    std::vector<std::optional<SearchValues>> actionValues;
    // The root's zone input as the network read it; null when nothing evaluated it.
    std::shared_ptr<const ZoneInput> rootInput;
    std::string layout;  // The zone encoding's version (ZoneEncodingSpec::version).
    std::size_t evaluations{0};  // Network evaluations the search asked for.
    std::size_t positions{0};    // Nodes of its tree.
    bool reused{false};          // Whether the tree already held the root's state.
};

// A game's search tree, kept from one decision to the next. A search given one
// starts from the node of the state it is asked about, keeps everything below
// it and drops the rest; a state the tree never reached starts a new tree
// (VectorMCTS.search with reuse_root in studies/shared/multiplayer_mcts.py).
class SearchTree {
  public:
    SearchTree();
    ~SearchTree();
    SearchTree(const SearchTree&) = delete;
    SearchTree& operator=(const SearchTree&) = delete;
    void clear();
    std::size_t size() const;
    struct Storage;
    Storage& storage() { return *storage_; }

  private:
    std::unique_ptr<Storage> storage_;
};

// A nonterminal decision without legal actions, which is a rules defect. Its
// message is the position, as CampaignAdapter.serialize writes it.
class NoLegalSearchAction : public std::runtime_error {
  public:
    using std::runtime_error::runtime_error;
};

// A move of a simulation that the engine accepted and then failed on, such as
// one whose state fails State::validate. Its message is a JSON object: the
// engine's error, the position before the move as CampaignAdapter.serialize
// writes it, and the move (its kind, the action's id and where the search dice
// stood), so that another process can replay it (tools/replay_failed_move.py).
class SearchMoveFailed : public std::runtime_error {
  public:
    using std::runtime_error::runtime_error;
};

// Search `game` (not changed) at the given scheduling state, in `tree` when one
// is given and in a tree of its own otherwise.
SearchOutcome searchDecision(const Engine& game, const SearchSchedule& schedule, SearchEvaluator& evaluator,
                             const SearchSettings& settings, SearchTree* tree = nullptr);
// The same on a search copy of the game (Engine::cloneForSearch), which the
// search keeps as its root position, unless the tree already holds that state.
SearchOutcome searchDecision(std::shared_ptr<const Engine> root, const SearchSchedule& schedule,
                             SearchEvaluator& evaluator, const SearchSettings& settings, SearchTree* tree = nullptr);

}  // namespace game::campaign
