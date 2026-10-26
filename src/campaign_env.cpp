#include "game/campaign_env.hpp"
#include "game/campaign_audit.hpp"
#include "game/campaign_actions.hpp"
#include "game/catalog.hpp"

#include <stdexcept>
#include <mutex>

namespace game::campaign {
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;

V staticContext(const State& s, bool trainingActions) {
    if (!s.definition->catalog) throw std::runtime_error("Campaign observations require the shared catalog");
    O factions;
    for (const auto& [id, f] : s.definition->factions) {
        A home;
        for (const auto& zone : f.homeCountry) home.emplace_back(zone);
        factions.emplace(id, V(O{{"name", V(f.displayName)}, {"home_country", V(std::move(home))},
            {"home_country_known", V(f.homeCountryKnown)}, {"dormant", V(f.dormant)}}));
    }
    A players;
    for (const auto& player : allianceOrder) players.emplace_back(player);
    O result{{"schema", V(std::string("campaign_entities_v1"))}, {"players", V(std::move(players))},
        {"geography", s.definition->geography}, {"factions", V(std::move(factions))},
        {"catalog", s.definition->catalog->sourceData()}, {"rules", s.definition->rules}};
    if (trainingActions) result["action_interface"] = V(std::string(trainingActionSchema));
    return V(std::move(result));
}
}  // namespace

struct CampaignEnv::DecisionCache {
    std::mutex mutex;
    std::optional<std::string> planningKey;
    std::shared_ptr<const V> observation;
};

CampaignEnv::CampaignEnv(const std::filesystem::path& path, std::uint64_t seed, bool trainingActions)
    : CampaignEnv(Engine::start(loadScenario(path), trainingActions ? trainingCampaignRules() : campaignRules(), seed)) {}

CampaignEnv::CampaignEnv(Engine engine)
    : engine_(std::move(engine)), trainingActions_(engine_.rulesId() == trainingCampaignRules()->id()),
      context_(std::make_shared<const V>(staticContext(engine_.state(), trainingActions_))),
      decisionCache_(std::make_shared<DecisionCache>()) {}

CampaignEnv CampaignEnv::curriculum(const std::filesystem::path& path, int calendarRounds,
                                    std::uint64_t seed, bool trainingActions) {
    auto initial = loadScenario(path);
    auto definition = *initial.definition;
    if (calendarRounds < 1 || calendarRounds > definition.calendarRounds)
        throw std::invalid_argument("Curriculum rounds must be between one and the full campaign horizon");
    const auto baseFingerprint = definition.fingerprint;
    const int targetRounds = definition.calendarRounds;
    definition.scenarioId += "_curriculum_" + std::to_string(calendarRounds);
    definition.calendarRounds = calendarRounds;
    auto rules = definition.rules.asObject();
    rules["curriculum"] = V(O{{"base_definition_fingerprint", V(baseFingerprint)},
        {"calendar_rounds", V(static_cast<double>(calendarRounds))},
        {"full_target_calendar_rounds", V(static_cast<double>(targetRounds))},
        {"full_target_game", V(false)}, {"setup", V(std::string("unchanged_approved_initial_setup"))}});
    definition.rules = V(std::move(rules));
    initial.definition = freezeDefinition(std::move(definition));
    initial.validate();
    return CampaignEnv(Engine::start(std::move(initial), trainingActions ? trainingCampaignRules() : campaignRules(), seed));
}

std::string CampaignEnv::decisionKind() const {
    const auto& s = engine_.state();
    if (s.terminal) return "terminal";
    if (s.chance) return "chance";
    if (!s.decisions.empty()) return s.decisions.back().kind;
    return toString(s.clock.phase);
}

const V& CampaignEnv::observation() const { return *observationSnapshot(); }

std::shared_ptr<const V> CampaignEnv::observationSnapshot() const {
    std::lock_guard lock(decisionCache_->mutex);
    if (decisionCache_->observation) return decisionCache_->observation;
    const auto owner = currentDecisionPlayer();
    A actions, interrupts;
    for (const auto& action : legalActions()) actions.push_back(actionJson(action));
    for (const auto& action : legalInterrupts()) interrupts.push_back(actionJson(action));
    // Entity maps retain every rule status, route/origin, relationship, pending
    // choice and chance request. Geography/catalog registries are shared context.
    // Execution RNG, dice tapes, history and planning hashes are never features.
    decisionCache_->observation = std::make_shared<const V>(O{{"schema", V(std::string("campaign_entities_v1"))}, {"state", engine_.state().observation()},
        {"current_decision_player", owner ? V(*owner) : V(nullptr)},
        {"decision_kind", V(decisionKind())}, {"legal_actions", V(std::move(actions))},
        {"legal_interrupts", V(std::move(interrupts))}});
    return decisionCache_->observation;
}

CampaignEnv CampaignEnv::clone() const { return *this; }
CampaignEnv CampaignEnv::cloneForSearch(std::uint64_t seed) const {
    auto copy = clone();
    copy.engine_ = engine_.cloneForSearch(seed);
    return copy;
}
std::string CampaignEnv::planningKey() const {
    std::lock_guard lock(decisionCache_->mutex);
    if (!decisionCache_->planningKey) decisionCache_->planningKey = engine_.planningKey();
    return *decisionCache_->planningKey;
}
void CampaignEnv::applyAction(const Action& action) {
    auto fresh = std::make_shared<DecisionCache>();
    engine_.step(action);
    decisionCache_ = std::move(fresh);
}
void CampaignEnv::applyInterrupt(const Action& action) {
    auto fresh = std::make_shared<DecisionCache>();
    engine_.interrupt(action);
    decisionCache_ = std::move(fresh);
}
void CampaignEnv::resolveChance() {
    auto fresh = std::make_shared<DecisionCache>();
    engine_.resolveChance();
    decisionCache_ = std::move(fresh);
}
V CampaignEnv::chanceRequest() const {
    const auto& request = engine_.state().chance;
    return request ? chanceRequestJson(*request) : V(nullptr);
}
void CampaignEnv::applyChanceOutcome(const std::string& expectedKey, const ChanceOutcome& outcome) {
    auto fresh = std::make_shared<DecisionCache>();
    engine_.applyChanceOutcome(expectedKey, outcome);
    decisionCache_ = std::move(fresh);
}
void CampaignEnv::restore(const std::string& serialized) {
    auto fresh = std::make_shared<DecisionCache>();
    engine_ = Engine::restore(engine_.state().definition,
                             trainingActions_ ? trainingCampaignRules() : campaignRules(), serialized);
    decisionCache_ = std::move(fresh);
}

V CampaignEnv::historySince(std::size_t index) const {
    const auto& history = engine_.state().history;
    if (index > history.size()) throw std::out_of_range("Past-event index exceeds recorded history");
    A events;
    events.reserve(history.size() - index);
    for (; index < history.size(); ++index) {
        const auto& event = history[index];
        events.emplace_back(O{{"kind", V(event.kind)}, {"payload", event.payload},
                              {"after_state_key", V(event.afterStateKey)}});
    }
    return V(std::move(events));
}
}  // namespace game::campaign
