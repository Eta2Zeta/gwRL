#pragma once

#include "game/campaign.hpp"
#include "game/campaign_objective.hpp"

namespace game::campaign {

class CampaignEnv {
  public:
    explicit CampaignEnv(const std::filesystem::path& scenario, std::uint64_t seed = 1,
                         bool trainingActions = false);
    explicit CampaignEnv(Engine engine);
    static CampaignEnv curriculum(const std::filesystem::path& scenario, int calendarRounds,
                                  std::uint64_t seed = 1, bool trainingActions = false);
    bool isTerminal() const { return engine_.state().terminal; }
    std::optional<Id> currentDecisionPlayer() const { return engine_.state().decisionPlayer(); }
    Id currentNation() const { return engine_.state().currentNation(); }
    std::string decisionKind() const;
    std::vector<Action> legalActions() const { return engine_.legalActions(); }
    std::vector<Action> legalInterrupts() const { return engine_.legalInterrupts(); }
    void applyAction(const Action& action);
    void applyInterrupt(const Action& action);
    void resolveChance();
    json::Value chanceRequest() const;
    void applyChanceOutcome(const std::string& expectedKey, const ChanceOutcome&);
    std::array<double, 3> returns() const { return terminalReturns(engine_.state()); }
    json::Value wealth() const { return wealthJson(engine_.state()); }
    // Valid until this environment's next successful mutation. Callers that
    // need an independently mutable snapshot can copy the returned value.
    const json::Value& observation() const;
    json::Value context() const { return *context_; }
    std::shared_ptr<const json::Value> contextSnapshot() const { return context_; }
    std::shared_ptr<const json::Value> observationSnapshot() const;
    CampaignEnv clone() const;
    CampaignEnv cloneForSearch(std::uint64_t seed) const;
    std::string planningKey() const;
    std::string serialize() const { return engine_.serialize(); }
    // Inspection of already recorded events only. No execution RNG or future
    // dice are exposed, and reading does not advance or invalidate the state.
    std::size_t historySize() const { return engine_.state().history.size(); }
    json::Value historySince(std::size_t index) const;
    void restore(const std::string&);
    const Engine& engine() const { return engine_; }

  private:
    struct DecisionCache;
    Engine engine_;
    bool trainingActions_ {false};
    std::shared_ptr<const json::Value> context_;
    // Engine state is exposed as const; successful wrapper mutations are the
    // only invalidation points. Search reseeding leaves decision identity alone.
    std::shared_ptr<DecisionCache> decisionCache_;
};

}  // namespace game::campaign
