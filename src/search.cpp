#include "game/search.hpp"

#include "game/campaign_objective.hpp"
#include "game/python_random.hpp"

#include <algorithm>
#include <cmath>
#include <deque>
#include <limits>
#include <new>
#include <numeric>
#include <string_view>
#include <unordered_map>
#include <utility>

// The Python search never fuses a multiplication and an addition into one
// rounding, so neither may this file (clang otherwise fuses within an expression).
#if defined(__clang__)
#pragma clang fp contract(off)
#elif defined(__GNUC__)
#pragma GCC optimize("fp-contract=off")
#endif

namespace game::campaign {
// The search's parts. A named namespace, since a SearchTree holds them between searches.
namespace searching {

using V = json::Value;
using O = V::Object;
using A = V::Array;

constexpr std::string_view schedulerSchema = "campaign-interrupt-scheduler-v1";  // CampaignAdapter's SCHEMA
constexpr std::array<std::string_view, 5> phaseKinds{"production", "combat_movement", "combat",
                                                     "non_combat_movement", "place_units"};
constexpr std::uint64_t policySeedMix = 0xD1B54A32D192ED03ULL;

int allianceNumber(const Id& player) {
    for (std::size_t i = 0; i < allianceOrder.size(); ++i)
        if (allianceOrder[i] == player) return static_cast<int>(i);
    throw std::runtime_error("A decision names an unknown alliance");
}

// CampaignEnv::decisionKind.
std::string engineDecisionKind(const State& state) {
    if (state.terminal) return "terminal";
    if (state.chance) return "chance";
    if (!state.decisions.empty()) return state.decisions.back().kind;
    return toString(state.clock.phase);
}

enum class DecisionKind : std::uint8_t { Terminal, Chance, Offer, Play };
// In the order of the adapter's action ids: "interrupt:" sorts before "pass:",
// and a decision's plays are never mixed with interrupts or a pass.
enum class OptionKind : std::uint8_t { Interrupt, Pass, Play };

struct Option {
    const Action* action{nullptr};  // None for a pass.
    OptionKind kind{OptionKind::Play};
};

// One position's decision as CampaignAdapter schedules it.
struct Scheduled {
    DecisionKind kind{DecisionKind::Play};
    int owner{-1};    // The alliance choosing, or -1.
    int offered{-1};  // The alliance offered its declarations, or -1.
    std::string kindName;
    // The menu the options point into: the interrupts of an offer, the moves of a play.
    std::shared_ptr<const std::vector<Action>> menu;
};

Scheduled scheduleOf(const Engine& engine, std::uint8_t passed, const std::array<int, 3>& order) {
    const auto& state = engine.state();
    Scheduled decision;
    decision.kindName = engineDecisionKind(state);
    if (state.terminal) {
        decision.kind = DecisionKind::Terminal;
        if (state.decisionPlayer()) throw std::runtime_error("Chance and terminal states cannot have a policy decision owner");
        return decision;
    }
    if (std::find(phaseKinds.begin(), phaseKinds.end(), decision.kindName) != phaseKinds.end()) {
        auto interrupts = engine.legalInterruptMenu();
        unsigned owners = 0;
        for (const auto& action : *interrupts) owners |= 1U << allianceNumber(action.player);
        for (const int player : order)
            if ((owners >> player & 1U) && !(passed >> player & 1U)) {
                decision.kind = DecisionKind::Offer;
                decision.owner = decision.offered = player;
                decision.kindName = "declaration_offer";
                decision.menu = std::move(interrupts);
                return decision;
            }
    }
    const auto player = state.decisionPlayer();
    decision.owner = player ? allianceNumber(*player) : -1;
    if (decision.kindName == "chance") {
        decision.kind = DecisionKind::Chance;
        if (decision.owner >= 0) throw std::runtime_error("Chance and terminal states cannot have a policy decision owner");
    }
    return decision;
}

struct Edge {
    const Action* action{nullptr};
    OptionKind kind{OptionKind::Play};
    double prior{0.0};
    double selectionPrior{0.0};
    int visits{0};
    SearchValues valueSum{0.0, 0.0, 0.0};
    int successor{-1};  // A move played from a position always reaches the same position.
    // Simulations of the request being gathered whose paths take this edge and
    // whose results have not come back yet (SearchSettings::simulationsPerRequest).
    int pending{0};
};

bool keyLess(const Edge& a, const Edge& b) {
    if (a.kind != b.kind) return a.kind < b.kind;
    if (!a.action || !b.action) return false;
    return a.action->id < b.action->id;
}

struct Node {
    // A copy of the game at this position. Simulations only copy it again, to
    // play one move or roll dice there; nothing plays on it, so a pass, which
    // changes no game state, shares its position's copy.
    std::shared_ptr<const Engine> game;
    std::uint8_t passed{0};
    Scheduled decision;
    bool expanded{false};
    std::vector<Edge> edges;
    std::vector<int> chanceSuccessors;  // The outcomes its dice have reached.
    int visits{0};
    SearchValues valueSum{0.0, 0.0, 0.0};
    SearchValues evaluation{0.0, 0.0, 0.0};
    // Whether evaluation holds the network's value or a terminal state's
    // returns: a state with one legal action is expanded without one.
    bool evaluated{false};
};

struct Bounds {
    double minimum{std::numeric_limits<double>::infinity()};
    double maximum{-std::numeric_limits<double>::infinity()};
    void update(double value) {
        minimum = std::min(minimum, value);
        maximum = std::max(maximum, value);
    }
    double normalize(double value) const {
        return maximum > minimum ? (value - minimum) / (maximum - minimum) : 0.5;
    }
};

SearchValues finite(const SearchValues& values) {
    for (const double value : values)
        if (!std::isfinite(value)) throw std::invalid_argument("Value must have three finite Axis/Allies/Comintern components");
    return values;
}

// Where a simulation's walk down the tree ends, and what it needs asked there.
struct Leaf {
    enum class Need : std::uint8_t {
        Nothing,      // Its value is known: a terminal state's returns, or a value already asked for.
        Expansion,    // A new state with two or more options: its priors and value.
        Rating,       // A state with one option, expanded without asking, where the walk stops: its value.
        ChanceValue,  // A chance state where the walk stops: its value only.
    };
    Need need{Need::Nothing};
    int node{-1};
    SearchValues values{0.0, 0.0, 0.0};  // With Need::Nothing.
    std::vector<Option> options;          // What an expansion or a rating lists.
};

// A simulation whose question is in the request being gathered.
struct Waiting {
    std::vector<int> path;
    std::vector<std::pair<int, int>> edges;  // (node, edge)
    Leaf leaf;
};

}  // namespace searching

struct SearchTree::Storage {
    std::deque<searching::Node> nodes;
    std::unordered_map<std::string, int> index;
};

SearchTree::SearchTree() : storage_(std::make_unique<Storage>()) {}
SearchTree::~SearchTree() = default;
void SearchTree::clear() {
    storage_->nodes.clear();
    storage_->index.clear();
}
std::size_t SearchTree::size() const { return storage_->nodes.size(); }

namespace searching {

class Searcher {
  public:
    Searcher(SearchEvaluator& evaluator, const SearchSettings& settings, const std::array<int, 3>& order,
             SearchTree::Storage& tree)
        : evaluator_(evaluator), settings_(settings), order_(order), random_(settings.seed),
          nodes_(tree.nodes), index_(tree.index) {}

    SearchOutcome run(std::shared_ptr<const Engine> root, std::uint8_t passed);

  private:
    int reach(std::shared_ptr<const Engine> game, std::uint8_t passed);
    void retain(int root);
    std::vector<Option> options(Node& node);
    void expandRoot(int index);
    // A new state's edges, from the priors the network gave its options, and its value.
    void expandWith(int index, const std::vector<Option>& choices, const std::vector<double>& priors,
                    const SearchValues& values);
    // One simulation's walk from the root, which fills `path` and `edgesPath`
    // and ends where it needs a question asked or knows its value.
    Leaf walk(int number, std::vector<int>& path, std::vector<std::pair<int, int>>& edgesPath);
    // What a walk that stops at a node needs: at the depth limit, or where it
    // would reach a state it has already passed.
    Leaf stopAt(int index);
    SearchValues answered(const Leaf& leaf, const SearchAnswer& answer);
    void backup(const std::vector<int>& path, const std::vector<std::pair<int, int>>& edgesPath,
                const SearchValues& values);
    std::shared_ptr<const ZoneInput> encode(const Node& node, const std::vector<Option>& options) const;
    std::string actionId(const Node& node, const Option& option) const;
    std::string position(const Node& node) const;
    std::uint8_t passedAfter(const Node& from, const Engine& to) const {
        return to.stateKey() == from.game->stateKey() ? from.passed : 0;
    }

    SearchEvaluator& evaluator_;
    const SearchSettings& settings_;
    std::array<int, 3> order_;
    PythonRandom random_;
    std::deque<Node>& nodes_;
    std::unordered_map<std::string, int>& index_;
    std::array<Bounds, 3> bounds_{};
    std::string layout_;
    std::shared_ptr<const ZoneInput> rootInput_;
    std::size_t evaluations_{0};
    std::vector<double> priors_;
    int root_{0};
    std::vector<int> onPath_;  // The walk that last put each node on its path.
    std::vector<int> asked_;   // The request whose question is about each node.
    std::vector<double> scores_;
    std::vector<std::size_t> tied_;
};

int Searcher::reach(std::shared_ptr<const Engine> game, std::uint8_t passed) {
    // CampaignAdapter.planning_key: the engine's state and the passes, under fixed rules and order.
    std::string key = game->stateKey();
    key.push_back(static_cast<char>('0' + passed));
    const auto [found, inserted] = index_.try_emplace(std::move(key), static_cast<int>(nodes_.size()));
    if (!inserted) return found->second;
    auto& node = nodes_.emplace_back();
    node.decision = scheduleOf(*game, passed, order_);
    node.game = std::move(game);
    node.passed = passed;
    return found->second;
}

void Searcher::retain(int root) {
    // The root and every node below it, by edges and dice outcomes; the root
    // becomes node 0. VectorMCTS._retain.
    std::vector<int> renumbered(nodes_.size(), -1), order;
    std::vector<int> stack{root};
    while (!stack.empty()) {
        const int index = stack.back();
        stack.pop_back();
        if (renumbered[static_cast<std::size_t>(index)] >= 0) continue;
        renumbered[static_cast<std::size_t>(index)] = static_cast<int>(order.size());
        order.push_back(index);
        const Node& node = nodes_[static_cast<std::size_t>(index)];
        for (const auto& edge : node.edges)
            if (edge.successor >= 0) stack.push_back(edge.successor);
        for (const int successor : node.chanceSuccessors) stack.push_back(successor);
    }
    std::deque<Node> kept;
    for (const int index : order) {
        Node node = std::move(nodes_[static_cast<std::size_t>(index)]);
        for (auto& edge : node.edges)
            if (edge.successor >= 0) edge.successor = renumbered[static_cast<std::size_t>(edge.successor)];
        for (auto& successor : node.chanceSuccessors) successor = renumbered[static_cast<std::size_t>(successor)];
        kept.push_back(std::move(node));
    }
    std::unordered_map<std::string, int> index;
    for (auto& [key, number] : index_)
        if (renumbered[static_cast<std::size_t>(number)] >= 0) index.emplace(key, renumbered[static_cast<std::size_t>(number)]);
    nodes_ = std::move(kept);
    index_ = std::move(index);
}

std::vector<Option> Searcher::options(Node& node) {
    std::vector<Option> result;
    const auto& decision = node.decision;
    if (decision.kind == DecisionKind::Offer) {
        for (const auto& action : *decision.menu)
            if (allianceNumber(action.player) == decision.offered) result.push_back({&action, OptionKind::Interrupt});
        result.push_back({nullptr, OptionKind::Pass});
        return result;
    }
    if (decision.owner < 0) throw std::invalid_argument("A policy decision must name its entitled player");
    if (!node.decision.menu) node.decision.menu = node.game->legalActionMenu();
    result.reserve(node.decision.menu->size());
    for (const auto& action : *node.decision.menu) result.push_back({&action, OptionKind::Play});
    return result;
}

std::shared_ptr<const ZoneInput> Searcher::encode(const Node& node, const std::vector<Option>& options) const {
    // CampaignAdapter.zone_input: the decision's scheduling and its options.
    ZoneSchedule schedule;
    const auto& decision = node.decision;
    if (decision.owner >= 0) schedule.owner = allianceOrder[static_cast<std::size_t>(decision.owner)];
    schedule.decisionKind = decision.kindName;
    if (decision.offered >= 0) schedule.offered = allianceOrder[static_cast<std::size_t>(decision.offered)];
    std::vector<Id> passed;
    for (std::size_t player = 0; player < allianceOrder.size(); ++player)
        if (node.passed >> player & 1U) passed.push_back(allianceOrder[player]);
    std::sort(passed.begin(), passed.end());
    schedule.passed = std::move(passed);
    for (const int player : order_) schedule.order.push_back(allianceOrder[static_cast<std::size_t>(player)]);
    std::vector<ZoneOption> zoneOptions;
    zoneOptions.reserve(options.size());
    for (const auto& option : options) {
        ZoneOption zoneOption;
        zoneOption.kind = option.kind == OptionKind::Play ? "play" : option.kind == OptionKind::Interrupt ? "interrupt" : "pass_interrupt";
        zoneOption.player = allianceOrder[static_cast<std::size_t>(decision.owner)];
        zoneOption.action = option.action;
        zoneOptions.push_back(std::move(zoneOption));
    }
    return std::make_shared<const ZoneInput>(encodeZoneInput(node.game->state(), schedule, zoneOptions));
}

std::string Searcher::actionId(const Node& node, const Option& option) const {
    std::string id(schedulerSchema);
    switch (option.kind) {
        case OptionKind::Play: return id.append(":play:").append(option.action->id);
        case OptionKind::Interrupt: return id.append(":interrupt:").append(option.action->id);
        case OptionKind::Pass: return id.append(":pass:").append(allianceOrder[static_cast<std::size_t>(node.decision.offered)]);
    }
    return id;
}

std::string Searcher::position(const Node& node) const {
    // CampaignAdapter.serialize.
    A order, passed;
    for (const int player : order_) order.emplace_back(allianceOrder[static_cast<std::size_t>(player)]);
    std::vector<Id> names;
    for (std::size_t player = 0; player < allianceOrder.size(); ++player)
        if (node.passed >> player & 1U) names.push_back(allianceOrder[player]);
    std::sort(names.begin(), names.end());
    for (auto& name : names) passed.emplace_back(std::move(name));
    return canonicalJson(V(O{{"schema", V(std::string(schedulerSchema))}, {"raw", V(node.game->serialize())},
                             {"order", V(std::move(order))}, {"passed", V(std::move(passed))},
                             {"anchor", V(node.game->planningKey())}}));
}

void Searcher::expandWith(int index, const std::vector<Option>& choices, const std::vector<double>& priors,
                          const SearchValues& values) {
    // probabilities() in studies/shared/multiplayer_mcts.py.
    Node& node = nodes_[static_cast<std::size_t>(index)];
    if (priors.size() != choices.size())
        throw std::invalid_argument("Policy must provide one finite nonnegative weight per legal action");
    for (const double prior : priors)
        if (!std::isfinite(prior) || prior < 0)
            throw std::invalid_argument("Policy must provide one finite nonnegative weight per legal action");
    const double total = pythonSum(priors.data(), priors.size());
    if (!std::isfinite(total) || total <= 0) throw std::invalid_argument("Policy must have positive finite total weight");
    node.evaluation = finite(values);
    node.evaluated = true;
    node.edges.reserve(choices.size());
    for (std::size_t i = 0; i < choices.size(); ++i) {
        const double prior = priors[i] / total;
        node.edges.push_back(Edge{choices[i].action, choices[i].kind, prior, prior});
    }
    node.expanded = true;
}

void Searcher::expandRoot(int index) {
    // The root is asked about even with one option (searchForcedRoot); VectorMCTS._expand.
    Node& node = nodes_[static_cast<std::size_t>(index)];
    if (node.decision.kind == DecisionKind::Terminal) {
        node.evaluation = finite(terminalReturns(node.game->state()));
        node.evaluated = true;
    } else if (node.decision.kind == DecisionKind::Chance) {
        node.evaluation = {0.0, 0.0, 0.0};
    } else {
        const auto choices = options(node);
        if (choices.empty()) throw NoLegalSearchAction(position(node));
        std::shared_ptr<const ZoneInput> input;
        if (evaluator_.readsInput()) input = encode(node, choices);
        SearchValues values{};
        priors_.clear();
        evaluator_.evaluate(input, layout_, node.decision.owner, choices.size(), priors_, values);
        ++evaluations_;
        rootInput_ = input;
        expandWith(index, choices, priors_, values);
        return;
    }
    node.expanded = true;
}

Leaf Searcher::stopAt(int index) {
    // VectorMCTS._bootstrap: a forced state is rated only once a walk stops at it.
    Node& node = nodes_[static_cast<std::size_t>(index)];
    Leaf leaf;
    leaf.node = index;
    if (node.decision.kind == DecisionKind::Terminal) {
        leaf.values = finite(terminalReturns(node.game->state()));
        return leaf;
    }
    if (node.decision.kind == DecisionKind::Chance) {
        leaf.need = Leaf::Need::ChanceValue;  // A value-only evaluation, not kept.
        return leaf;
    }
    if (!node.expanded) {
        auto choices = options(node);
        if (choices.empty()) throw NoLegalSearchAction(position(node));
        if (choices.size() > 1) {
            leaf.need = Leaf::Need::Expansion;
            leaf.options = std::move(choices);
            return leaf;
        }
        node.edges.push_back(Edge{choices.front().action, choices.front().kind, 1.0, 1.0});
        node.expanded = true;
    }
    if (!node.evaluated) {
        leaf.need = Leaf::Need::Rating;
        leaf.options = {Option{node.edges.front().action, node.edges.front().kind}};
        return leaf;
    }
    leaf.values = node.evaluation;
    return leaf;
}

Leaf Searcher::walk(int number, std::vector<int>& path, std::vector<std::pair<int, int>>& edgesPath) {
    const std::uint64_t seed = random_.getrandbits64();
    PythonRandom policyRandom(seed ^ policySeedMix);
    // Walk the tree on its saved positions. Only playing a new move or rolling
    // dice copies one; each copy continues the dice of the last, from one stream
    // started from the walk's seed.
    std::optional<std::uint64_t> stream;
    const auto copyOf = [&](const Node& node) {
        return node.game->cloneForSearchFrom(stream ? *stream : Engine::searchStreamFor(seed));
    };
    // A move that fails on a copy leaves no position behind, so the error
    // names the node's position, the move and where the dice stood.
    const auto moveFailed = [&](const Node& node, const std::exception& error, const char* kind, const Id& action) {
        const auto dice = stream ? *stream : Engine::searchStreamFor(seed);
        O move{{"kind", V(std::string(kind))}, {"search_stream", V(std::to_string(dice))}};
        if (!action.empty()) move.emplace("id", V(action));
        O failure{{"error", V(std::string(error.what()))}, {"move", V(std::move(move))}};
        try {
            failure.emplace("position", V(position(node)));
        } catch (const std::exception& unwritable) {
            // A damaged position may not serialize; the rest still says what failed.
            failure.emplace("position_error", V(std::string(unwritable.what())));
        }
        return SearchMoveFailed(canonicalJson(V(std::move(failure))));
    };
    const auto mark = [&](int index) {
        if (onPath_.size() <= static_cast<std::size_t>(index)) onPath_.resize(nodes_.size(), -1);
        onPath_[static_cast<std::size_t>(index)] = number;
    };
    const auto visited = [&](int index) {
        return static_cast<std::size_t>(index) < onPath_.size() && onPath_[static_cast<std::size_t>(index)] == number;
    };
    int current = root_;
    path.assign(1, root_);
    edgesPath.clear();
    mark(root_);
    for (int depth = 0; depth < settings_.maxDepth; ++depth) {
        Node& node = nodes_[static_cast<std::size_t>(current)];
        if (node.decision.kind == DecisionKind::Terminal) {
            Leaf leaf;
            leaf.node = current;
            leaf.values = finite(terminalReturns(node.game->state()));
            return leaf;
        }
        int successor;
        if (node.decision.kind == DecisionKind::Chance) {
            auto copy = copyOf(node);
            try {
                copy.resolveChance();
            } catch (const std::bad_alloc&) {
                throw;
            } catch (const std::exception& error) {
                throw moveFailed(node, error, "chance", Id{});
            }
            stream = copy.searchStream();
            const auto passedNow = passedAfter(node, copy);
            successor = reach(std::make_shared<const Engine>(std::move(copy)), passedNow);
            auto& reached = nodes_[static_cast<std::size_t>(current)].chanceSuccessors;
            if (std::find(reached.begin(), reached.end(), successor) == reached.end()) reached.push_back(successor);
        } else {
            if (!node.expanded) {
                auto choices = options(node);
                if (choices.empty()) throw NoLegalSearchAction(position(node));
                if (choices.size() > 1) {
                    Leaf leaf;
                    leaf.need = Leaf::Need::Expansion;
                    leaf.node = current;
                    leaf.options = std::move(choices);
                    return leaf;
                }
                // A forced state gets its one edge without an evaluation: the walk
                // plays its action and goes on (VectorMCTS._expand).
                node.edges.push_back(Edge{choices.front().action, choices.front().kind, 1.0, 1.0});
                node.expanded = true;
            }
            const int component = node.decision.owner;
            const bool rootStep = depth == 0;
            const auto& normalizer = bounds_[static_cast<std::size_t>(component)];
            // Simulations of the request being gathered count as visits that
            // lost: their paths' edges look worse until their results come back.
            long total = 0;
            for (const auto& edge : node.edges) total += edge.visits + edge.pending;
            const double scale = std::sqrt(static_cast<double>(total) + 1.0);
            scores_.resize(node.edges.size());
            double best = -std::numeric_limits<double>::infinity();
            for (std::size_t i = 0; i < node.edges.size(); ++i) {
                const auto& edge = node.edges[i];
                double normalized;
                if (edge.pending == 0)
                    normalized = edge.visits ? normalizer.normalize(edge.valueSum[static_cast<std::size_t>(component)] / edge.visits) : 1.0;
                else
                    normalized = edge.visits ? normalizer.normalize(edge.valueSum[static_cast<std::size_t>(component)] / edge.visits) *
                                                   edge.visits / (edge.visits + edge.pending)
                                             : 0.0;
                const double prior = rootStep ? edge.selectionPrior : edge.prior;
                const double score = normalized + settings_.cPuct * prior * scale / (static_cast<double>(edge.visits + edge.pending) + 1.0);
                scores_[i] = score;
                if (score > best) best = score;
            }
            tied_.clear();
            for (std::size_t i = 0; i < scores_.size(); ++i)
                if (scores_[i] == best) tied_.push_back(i);
            std::sort(tied_.begin(), tied_.end(), [&](std::size_t a, std::size_t b) { return keyLess(node.edges[a], node.edges[b]); });
            const auto selected = tied_[policyRandom.randbelow(static_cast<std::uint32_t>(tied_.size()))];
            edgesPath.emplace_back(current, static_cast<int>(selected));
            auto& edge = node.edges[selected];
            if (edge.successor >= 0) {
                successor = edge.successor;
            } else if (edge.kind == OptionKind::Pass) {
                // A pass changes no game state, rolls no dice and needs no copy.
                if (!stream) stream = Engine::searchStreamFor(seed);
                successor = reach(node.game, static_cast<std::uint8_t>(node.passed | (1U << node.decision.offered)));
            } else {
                auto copy = copyOf(node);
                try {
                    if (edge.kind == OptionKind::Interrupt) copy.interrupt(*edge.action);
                    else copy.step(*edge.action);
                } catch (const std::bad_alloc&) {
                    throw;
                } catch (const std::exception& error) {
                    throw moveFailed(node, error, edge.kind == OptionKind::Interrupt ? "interrupt" : "action",
                                     edge.action->id);
                }
                stream = copy.searchStream();
                const auto passedNow = passedAfter(node, copy);
                successor = reach(std::make_shared<const Engine>(std::move(copy)), passedNow);
            }
            // `node` and `edge` stay valid: nodes live in a deque.
            nodes_[static_cast<std::size_t>(current)].edges[selected].successor = successor;
        }
        // A reversible planning sequence can return to an exact state. Stop at its
        // first repetition and bootstrap, rather than count one simulation
        // repeatedly in the same node and action.
        if (visited(successor)) return stopAt(successor);
        current = successor;
        path.push_back(current);
        mark(current);
    }
    return stopAt(current);
}

SearchValues Searcher::answered(const Leaf& leaf, const SearchAnswer& answer) {
    Node& node = nodes_[static_cast<std::size_t>(leaf.node)];
    switch (leaf.need) {
        case Leaf::Need::Expansion:
            expandWith(leaf.node, leaf.options, answer.priors, answer.values);
            return node.evaluation;
        case Leaf::Need::Rating:
            if (answer.priors.size() != 1)
                throw std::invalid_argument("Policy must provide one finite nonnegative weight per legal action");
            node.evaluation = finite(answer.values);
            node.evaluated = true;
            return node.evaluation;
        case Leaf::Need::ChanceValue:
            if (!answer.priors.empty()) throw std::invalid_argument("A chance evaluation has no policy");
            return finite(answer.values);
        case Leaf::Need::Nothing:
            break;
    }
    return leaf.values;
}

void Searcher::backup(const std::vector<int>& path, const std::vector<std::pair<int, int>>& edgesPath,
                      const SearchValues& values) {
    for (const int index : path) {
        Node& node = nodes_[static_cast<std::size_t>(index)];
        ++node.visits;
        for (std::size_t c = 0; c < 3; ++c) node.valueSum[c] += values[c];
    }
    for (const auto& [nodeIndex, edgeIndex] : edgesPath) {
        auto& edge = nodes_[static_cast<std::size_t>(nodeIndex)].edges[static_cast<std::size_t>(edgeIndex)];
        ++edge.visits;
        for (std::size_t c = 0; c < 3; ++c) {
            edge.valueSum[c] += values[c];
            bounds_[c].update(edge.valueSum[c] / edge.visits);
        }
    }
}

SearchOutcome Searcher::run(std::shared_ptr<const Engine> rootGame, std::uint8_t passed) {
    layout_ = zoneEncodingSpec(rootGame->state())->version;
    SearchOutcome outcome;
    outcome.layout = layout_;
    // Keep the subtree of the root's state from earlier searches, or start anew.
    std::string rootKey = rootGame->stateKey();
    rootKey.push_back(static_cast<char>('0' + passed));
    if (const auto found = index_.find(rootKey); found != index_.end()) {
        outcome.reused = true;
        retain(found->second);
    } else {
        nodes_.clear();
        index_.clear();
    }
    root_ = reach(std::move(rootGame), passed);  // Node 0, kept or new.
    {
        Node& node = nodes_[static_cast<std::size_t>(root_)];
        const bool policy = node.decision.kind == DecisionKind::Offer || node.decision.kind == DecisionKind::Play;
        if (policy && !settings_.searchForcedRoot) {
            const auto choices = options(node);
            if (choices.empty()) throw NoLegalSearchAction(position(node));
            if (choices.size() == 1) {
                // Nothing to decide: no evaluation, no simulations and no value estimate.
                outcome.actionIds = {actionId(node, choices.front())};
                outcome.visits = {0};
                outcome.policy = {1.0};
                outcome.priors = {1.0};
                outcome.actionValues = {std::nullopt};
                outcome.positions = nodes_.size();
                return outcome;
            }
        }
    }
    if (!nodes_[static_cast<std::size_t>(root_)].expanded) expandRoot(root_);
    // Noise belongs to this search's root alone, and the value bounds start
    // from the kept tree's actions, as the searches that made them left them.
    for (auto& node : nodes_)
        for (auto& edge : node.edges) {
            edge.selectionPrior = edge.prior;
            if (edge.visits)
                for (std::size_t c = 0; c < 3; ++c) bounds_[c].update(edge.valueSum[c] / edge.visits);
        }
    Node& rootNode = nodes_[static_cast<std::size_t>(root_)];
    if (settings_.rootNoise && !rootNode.edges.empty()) {
        // Dirichlet noise over the root's options in action id order.
        std::vector<std::size_t> order(rootNode.edges.size());
        std::iota(order.begin(), order.end(), std::size_t{0});
        std::sort(order.begin(), order.end(), [&](std::size_t a, std::size_t b) {
            return keyLess(rootNode.edges[a], rootNode.edges[b]);
        });
        std::vector<double> noise;
        noise.reserve(order.size());
        for (std::size_t i = 0; i < order.size(); ++i) noise.push_back(random_.gammavariate(settings_.dirichletAlpha, 1.0));
        const double total = pythonSum(noise.data(), noise.size());
        const double epsilon = settings_.dirichletEpsilon;
        for (std::size_t i = 0; i < order.size(); ++i) {
            auto& edge = rootNode.edges[order[i]];
            const double share = total != 0.0 ? noise[i] / total : 1.0 / static_cast<double>(order.size());
            edge.selectionPrior = (1.0 - epsilon) * edge.prior + epsilon * share;
        }
    }

    // The new simulations: the whole budget, or, when the budget counts the
    // visits the root's actions hold from a reused tree, what they lack of it.
    int budget = settings_.simulations;
    if (settings_.countReusedVisits) {
        long held = 0;
        for (const auto& edge : rootNode.edges) held += edge.visits;
        budget = static_cast<int>(std::max(0L, static_cast<long>(budget) - held));
    }

    // The simulations, gathered into requests of up to simulationsPerRequest
    // questions. A walk that ends at a known value is backed up at once; one
    // that needs a question waits, its path's edges counted as visits that lost,
    // until the request's answers come back. A walk whose question is already in
    // the request is dropped and does not count, and after as many drops as the
    // request holds questions it is sent as it is. With one simulation a request
    // this is VectorMCTS's search, simulation by simulation.
    const int perRequest = std::max(1, settings_.simulationsPerRequest);
    std::vector<int> path;
    std::vector<std::pair<int, int>> edgesPath;
    std::vector<Waiting> waiting;
    std::vector<SearchQuestion> questions;
    std::vector<SearchAnswer> answers;
    int done = 0, walks = 0, request = 0;
    while (done < budget) {
        ++request;
        waiting.clear();
        questions.clear();
        int dropped = 0;
        while (done + static_cast<int>(waiting.size()) < budget &&
               static_cast<int>(waiting.size()) < perRequest && dropped < perRequest) {
            Leaf leaf = walk(walks++, path, edgesPath);
            if (leaf.need == Leaf::Need::Nothing) {
                backup(path, edgesPath, leaf.values);
                ++done;
                continue;
            }
            if (asked_.size() <= static_cast<std::size_t>(leaf.node)) asked_.resize(nodes_.size(), 0);
            if (asked_[static_cast<std::size_t>(leaf.node)] == request) {
                ++dropped;
                continue;
            }
            asked_[static_cast<std::size_t>(leaf.node)] = request;
            const Node& node = nodes_[static_cast<std::size_t>(leaf.node)];
            SearchQuestion question;
            question.actor = leaf.need == Leaf::Need::ChanceValue ? -1 : node.decision.owner;
            question.options = leaf.options.size();
            if (evaluator_.readsInput()) question.input = encode(node, leaf.options);
            questions.push_back(std::move(question));
            for (const auto& [nodeIndex, edgeIndex] : edgesPath)
                ++nodes_[static_cast<std::size_t>(nodeIndex)].edges[static_cast<std::size_t>(edgeIndex)].pending;
            waiting.push_back(Waiting{path, edgesPath, std::move(leaf)});
        }
        if (waiting.empty()) continue;
        evaluator_.evaluateMany(layout_, questions, answers);
        if (answers.size() != questions.size()) throw std::runtime_error("The evaluator answered another number of positions");
        evaluations_ += questions.size();
        for (std::size_t i = 0; i < waiting.size(); ++i) {
            const auto& simulation = waiting[i];
            for (const auto& [nodeIndex, edgeIndex] : simulation.edges)
                --nodes_[static_cast<std::size_t>(nodeIndex)].edges[static_cast<std::size_t>(edgeIndex)].pending;
            backup(simulation.path, simulation.edges, answered(simulation.leaf, answers[i]));
            ++done;
        }
    }

    const Node& node = nodes_[static_cast<std::size_t>(root_)];
    long total = 0;
    for (const auto& edge : node.edges) total += edge.visits;
    for (const auto& edge : node.edges) {
        outcome.actionIds.push_back(actionId(node, Option{edge.action, edge.kind}));
        outcome.visits.push_back(edge.visits);
        outcome.policy.push_back(total ? static_cast<double>(edge.visits) / static_cast<double>(total) : edge.prior);
        outcome.priors.push_back(edge.prior);
        if (edge.visits) {
            SearchValues mean{};
            for (std::size_t c = 0; c < 3; ++c) mean[c] = edge.valueSum[c] / edge.visits;
            outcome.actionValues.emplace_back(finite(mean));
        } else {
            outcome.actionValues.emplace_back(std::nullopt);
        }
    }
    SearchValues mean{};
    for (std::size_t c = 0; c < 3; ++c) mean[c] = node.valueSum[c] / node.visits;
    outcome.values = finite(mean);
    outcome.rootInput = rootInput_;
    outcome.evaluations = evaluations_;
    outcome.positions = nodes_.size();
    return outcome;
}

}  // namespace searching

SearchOutcome searchDecision(const Engine& game, const SearchSchedule& schedule, SearchEvaluator& evaluator,
                             const SearchSettings& settings, SearchTree* tree) {
    // The root keeps a copy, never the game itself: it moves on after the search.
    return searchDecision(std::make_shared<const Engine>(game.cloneForSearch(0)), schedule, evaluator, settings, tree);
}

SearchOutcome searchDecision(std::shared_ptr<const Engine> root, const SearchSchedule& schedule,
                             SearchEvaluator& evaluator, const SearchSettings& settings, SearchTree* tree) {
    if (!root) throw std::invalid_argument("The search needs a root position");
    if (settings.simulations <= 0 || settings.maxDepth <= 0)
        throw std::invalid_argument("Simulation budget and maximum depth must be positive");
    if (!std::isfinite(settings.cPuct) || settings.cPuct < 0) throw std::invalid_argument("PUCT constant must be finite and nonnegative");
    if (!std::isfinite(settings.dirichletAlpha) || settings.dirichletAlpha <= 0)
        throw std::invalid_argument("Dirichlet concentration must be positive and finite");
    if (!(settings.dirichletEpsilon >= 0 && settings.dirichletEpsilon <= 1))
        throw std::invalid_argument("Dirichlet mixture must be between zero and one");
    auto order = schedule.order;
    std::sort(order.begin(), order.end());
    if (order != std::array<int, 3>{0, 1, 2}) throw std::invalid_argument("Interrupt order must contain each alliance exactly once");
    if (schedule.passed > 7) throw std::invalid_argument("Passes name an unknown alliance");
    SearchTree own;
    searching::Searcher searcher(evaluator, settings, schedule.order, (tree ? *tree : own).storage());
    return searcher.run(std::move(root), schedule.passed);
}

}  // namespace game::campaign
