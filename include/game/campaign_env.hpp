#pragma once

#include "game/campaign.hpp"
#include "game/campaign_objective.hpp"

namespace game::campaign {

class CampaignEnv {
  public:
    explicit CampaignEnv(const std::filesystem::path& scenario, std::uint64_t seed = 1);
    explicit CampaignEnv(Engine engine);
    bool isTerminal() const { return engine_.state().terminal; }
    std::optional<Id> currentDecisionPlayer() const { return engine_.state().decisionPlayer(); }
    Id currentNation() const { return engine_.state().currentNation(); }
    std::string decisionKind() const;
    std::vector<Action> legalActions() const { return engine_.legalActions(); }
    std::vector<Action> legalInterrupts() const { return engine_.legalInterrupts(); }
    void applyAction(const Action& action) { engine_.step(action); }
    void applyInterrupt(const Action& action) { engine_.interrupt(action); }
    void resolveChance() { engine_.resolveChance(); }
    std::array<double, 3> returns() const { return terminalReturns(engine_.state()); }
    json::Value wealth() const { return wealthJson(engine_.state()); }
    json::Value observation() const;
    json::Value context() const { return *context_; }
    CampaignEnv clone() const;
    CampaignEnv cloneForSearch(std::uint64_t seed) const;
    std::string planningKey() const { return engine_.planningKey(); }
    std::string serialize() const { return engine_.serialize(); }
    void restore(const std::string&);
    const Engine& engine() const { return engine_; }

  private:
    Engine engine_;
    std::shared_ptr<const json::Value> context_;
};

}  // namespace game::campaign
