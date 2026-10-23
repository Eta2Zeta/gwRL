#pragma once

#include "game/campaign_benchmarks.hpp"

namespace game {

class JapanTrainingEnv : public CampaignBenchmarkEnv {
  public:
    explicit JapanTrainingEnv(std::filesystem::path scenarioPath,
                              std::string trackedNationId = "Japan", std::uint64_t seed = 1);
    JapanTrainingEnv clone() const { return *this; }
    JapanTrainingEnv cloneForSearch(std::uint64_t seed) const {
        auto result = clone(); result.useSearchSeed(seed); return result;
    }
    double finalReward() const;

  private:
    campaign::Id trackedNation_;
};

} // namespace game
