#include "game/search.hpp"

#include "game/campaign_objective.hpp"
#include "game/python_random.hpp"

#include <algorithm>
#include <cmath>
#include <deque>
#include <limits>
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
namespace {

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
    int visits{0};
    SearchValues valueSum{0.0, 0.0, 0.0};
    SearchValues evaluation{0.0, 0.0, 0.0};
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

class Searcher {
  public:
    Searcher(SearchEvaluator& evaluator, const SearchSettings& settings, const std::array<int, 3>& order)
        : evaluator_(evaluator), settings_(settings), order_(order), random_(settings.seed) {}

    SearchOutcome run(std::shared_ptr<const Engine> root, std::uint8_t passed);

  private:
    int reach(std::shared_ptr<const Engine> game, std::uint8_t passed);
    std::vector<Option> options(Node& node);
    SearchValues expand(int index);
    SearchValues bootstrap(int index);
    SearchValues chanceValue(const Node& node);
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
    std::deque<Node> nodes_;
    std::unordered_map<std::string, int> index_;
    std::array<Bounds, 3> bounds_{};
    std::string layout_;
    std::shared_ptr<const ZoneInput> rootInput_;
    std::size_t evaluations_{0};
    std::vector<double> priors_;
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

SearchValues Searcher::expand(int index) {
    Node& node = nodes_[static_cast<std::size_t>(index)];
    if (node.decision.kind == DecisionKind::Terminal) {
        node.evaluation = finite(terminalReturns(node.game->state()));
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
        if (index == 0) rootInput_ = input;
        // probabilities() in studies/shared/multiplayer_mcts.py.
        if (priors_.size() != choices.size())
            throw std::invalid_argument("Policy must provide one finite nonnegative weight per legal action");
        for (const double prior : priors_)
            if (!std::isfinite(prior) || prior < 0)
                throw std::invalid_argument("Policy must provide one finite nonnegative weight per legal action");
        const double total = pythonSum(priors_.data(), priors_.size());
        if (!std::isfinite(total) || total <= 0) throw std::invalid_argument("Policy must have positive finite total weight");
        node.evaluation = finite(values);
        node.edges.reserve(choices.size());
        for (std::size_t i = 0; i < choices.size(); ++i) {
            const double prior = priors_[i] / total;
            node.edges.push_back(Edge{choices[i].action, choices[i].kind, prior, prior});
        }
    }
    node.expanded = true;
    return node.evaluation;
}

SearchValues Searcher::chanceValue(const Node& node) {
    // A chance position has no policy expansion; its cutoff is a value-only evaluation.
    std::shared_ptr<const ZoneInput> input;
    if (evaluator_.readsInput()) input = encode(node, {});
    SearchValues values{};
    priors_.clear();
    evaluator_.evaluate(input, layout_, -1, 0, priors_, values);
    ++evaluations_;
    if (!priors_.empty()) throw std::invalid_argument("A chance evaluation has no policy");
    return finite(values);
}

SearchValues Searcher::bootstrap(int index) {
    const Node& node = nodes_[static_cast<std::size_t>(index)];
    if (node.decision.kind == DecisionKind::Chance) return chanceValue(node);
    return node.expanded ? node.evaluation : expand(index);
}

SearchOutcome Searcher::run(std::shared_ptr<const Engine> rootGame, std::uint8_t passed) {
    layout_ = zoneEncodingSpec(rootGame->state())->version;
    const int root = reach(std::move(rootGame), passed);
    SearchOutcome outcome;
    outcome.layout = layout_;
    {
        Node& node = nodes_[static_cast<std::size_t>(root)];
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
    expand(root);
    Node& rootNode = nodes_[static_cast<std::size_t>(root)];
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

    std::vector<int> path;
    std::vector<std::pair<int, int>> edgesPath;  // (node, edge)
    std::vector<int> onPath;                     // The simulation that last put each node on its path.
    std::vector<double> scores;
    std::vector<std::size_t> tied;
    for (int simulation = 0; simulation < settings_.simulations; ++simulation) {
        const std::uint64_t seed = random_.getrandbits64();
        PythonRandom policyRandom(seed ^ policySeedMix);
        // Walk the tree on its saved positions. Only playing a new move or
        // rolling dice copies one; each copy continues the dice of the last,
        // from one stream started from the simulation's seed.
        std::optional<std::uint64_t> stream;
        const auto copyOf = [&](const Node& node) {
            return node.game->cloneForSearchFrom(stream ? *stream : Engine::searchStreamFor(seed));
        };
        const auto mark = [&](int index) {
            if (onPath.size() <= static_cast<std::size_t>(index)) onPath.resize(nodes_.size(), -1);
            onPath[static_cast<std::size_t>(index)] = simulation;
        };
        const auto visited = [&](int index) {
            return static_cast<std::size_t>(index) < onPath.size() && onPath[static_cast<std::size_t>(index)] == simulation;
        };
        int current = root;
        path.assign(1, root);
        edgesPath.clear();
        mark(root);
        SearchValues values{};
        bool finished = false;
        for (int depth = 0; depth < settings_.maxDepth; ++depth) {
            Node& node = nodes_[static_cast<std::size_t>(current)];
            if (node.decision.kind == DecisionKind::Terminal) {
                values = finite(terminalReturns(node.game->state()));
                finished = true;
                break;
            }
            int successor;
            if (node.decision.kind == DecisionKind::Chance) {
                auto copy = copyOf(node);
                copy.resolveChance();
                stream = copy.searchStream();
                const auto passedNow = passedAfter(node, copy);
                successor = reach(std::make_shared<const Engine>(std::move(copy)), passedNow);
            } else {
                if (!node.expanded) {
                    values = expand(current);
                    finished = true;
                    break;
                }
                const int component = node.decision.owner;
                const bool rootStep = depth == 0;
                const auto& normalizer = bounds_[static_cast<std::size_t>(component)];
                long total = 0;
                for (const auto& edge : node.edges) total += edge.visits;
                const double scale = std::sqrt(static_cast<double>(total) + 1.0);
                scores.resize(node.edges.size());
                double best = -std::numeric_limits<double>::infinity();
                for (std::size_t i = 0; i < node.edges.size(); ++i) {
                    const auto& edge = node.edges[i];
                    const double normalized = edge.visits ? normalizer.normalize(edge.valueSum[static_cast<std::size_t>(component)] / edge.visits) : 1.0;
                    const double prior = rootStep ? edge.selectionPrior : edge.prior;
                    const double score = normalized + settings_.cPuct * prior * scale / (static_cast<double>(edge.visits) + 1.0);
                    scores[i] = score;
                    if (score > best) best = score;
                }
                tied.clear();
                for (std::size_t i = 0; i < scores.size(); ++i)
                    if (scores[i] == best) tied.push_back(i);
                std::sort(tied.begin(), tied.end(), [&](std::size_t a, std::size_t b) { return keyLess(node.edges[a], node.edges[b]); });
                const auto selected = tied[policyRandom.randbelow(static_cast<std::uint32_t>(tied.size()))];
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
                    if (edge.kind == OptionKind::Interrupt) copy.interrupt(*edge.action);
                    else copy.step(*edge.action);
                    stream = copy.searchStream();
                    const auto passedNow = passedAfter(node, copy);
                    successor = reach(std::make_shared<const Engine>(std::move(copy)), passedNow);
                }
                // `node` and `edge` stay valid: nodes live in a deque.
                nodes_[static_cast<std::size_t>(current)].edges[selected].successor = successor;
            }
            // A reversible planning sequence can return to an exact state. Stop at
            // its first repetition and bootstrap, rather than count one simulation
            // repeatedly in the same node and action.
            if (visited(successor)) {
                values = bootstrap(successor);
                finished = true;
                break;
            }
            current = successor;
            path.push_back(current);
            mark(current);
        }
        if (!finished) {
            const Node& node = nodes_[static_cast<std::size_t>(current)];
            values = node.decision.kind == DecisionKind::Terminal ? finite(terminalReturns(node.game->state())) : bootstrap(current);
        }
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

    const Node& node = nodes_[static_cast<std::size_t>(root)];
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

}  // namespace

SearchOutcome searchDecision(const Engine& game, const SearchSchedule& schedule, SearchEvaluator& evaluator,
                             const SearchSettings& settings) {
    // The root keeps a copy, never the game itself: it moves on after the search.
    return searchDecision(std::make_shared<const Engine>(game.cloneForSearch(0)), schedule, evaluator, settings);
}

SearchOutcome searchDecision(std::shared_ptr<const Engine> root, const SearchSchedule& schedule,
                             SearchEvaluator& evaluator, const SearchSettings& settings) {
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
    Searcher searcher(evaluator, settings, schedule.order);
    return searcher.run(std::move(root), schedule.passed);
}

}  // namespace game::campaign
