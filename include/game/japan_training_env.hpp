#pragma once

#include "game/campaign_benchmarks.hpp"

namespace game {

class JapanTrainingEnv : public CampaignBenchmarkEnv {
  public:
    explicit JapanTrainingEnv(std::filesystem::path scenarioPath,
                              std::string trackedNationId = "Japan", std::uint64_t seed = 1);
    JapanTrainingEnv clone() const {
        auto result = *this; result.useOrdinaryEngine(); return result;
    }
    JapanTrainingEnv cloneForSearch(std::uint64_t seed) const {
        auto result = *this; result.useSearchSeed(seed); return result;
    }
    double finalReward() const;

  private:
    campaign::Id trackedNation_;
};

} // namespace game
