#pragma once

#include "game/campaign.hpp"
#include "game/campaign_objective.hpp"

namespace game::campaign {

class CampaignEnv {
  public:
    explicit CampaignEnv(const std::filesystem::path& scenario, std::uint64_t seed = 1);
    explicit CampaignEnv(Engine engine);
    static CampaignEnv curriculum(const std::filesystem::path& scenario, int calendarRounds,
                                  std::uint64_t seed = 1);
    bool isTerminal() const { return engine_.state().terminal; }
    std::optional<Id> currentDecisionPlayer() const { return engine_.state().decisionPlayer(); }
    Id currentNation() const { return engine_.state().currentNation(); }
    std::string decisionKind() const;
    std::vector<Action> legalActions() const { return engine_.legalActions(); }
    std::vector<Action> legalInterrupts() const { return engine_.legalInterrupts(); }
    void applyAction(const Action& action) { engine_.step(action); planningKey_.reset(); }
    void applyInterrupt(const Action& action) { engine_.interrupt(action); planningKey_.reset(); }
    void resolveChance() { engine_.resolveChance(); planningKey_.reset(); }
    std::array<double, 3> returns() const { return terminalReturns(engine_.state()); }
    json::Value wealth() const { return wealthJson(engine_.state()); }
    json::Value observation() const;
    json::Value context() const { return *context_; }
    CampaignEnv clone() const;
    CampaignEnv cloneForSearch(std::uint64_t seed) const;
    std::string planningKey() const;
    std::string serialize() const { return engine_.serialize(); }
    void restore(const std::string&);
    const Engine& engine() const { return engine_; }

  private:
    Engine engine_;
    std::shared_ptr<const json::Value> context_;
    // Engine state is exposed as const; successful wrapper mutations are the
    // only invalidation points. Search reseeding leaves decision identity alone.
    mutable std::optional<std::string> planningKey_;
};

}  // namespace game::campaign
