#pragma once

#include "game/campaign_benchmarks.hpp"
#include "game/unit.hpp"

namespace game {

class CompositionBattleEnv : public CampaignBenchmarkEnv {
  public:
    explicit CompositionBattleEnv(int attackerBudget = 10, int defenderBudget = 10,
                                  std::string terrain = "normal", bool isCity = false,
                                  std::uint64_t seed = 1)
        : CampaignBenchmarkEnv(compositionCampaignBenchmark(attackerBudget, defenderBudget,
                                                            terrain, isCity), true, seed) {}
    CompositionBattleEnv clone() const { return *this; }
    CompositionBattleEnv cloneForSearch(std::uint64_t seed) const {
        auto result = clone(); result.useSearchSeed(seed); return result;
    }
    double finalReward() const;
    double terminalRewardFor(std::string_view) const;
    std::string winnerId() const;
    int budgetRemaining(std::string_view nation) const;
    int purchasedUnitCount(std::string_view, UnitKind) const;
};

} // namespace game
