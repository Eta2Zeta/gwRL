#include "game/japan_training_env.hpp"
#include "game/economy.hpp"

#include <stdexcept>

namespace game {

JapanTrainingEnv::JapanTrainingEnv(std::filesystem::path scenarioPath, std::string trackedNationId,
                                 std::uint64_t seed)
    : CampaignBenchmarkEnv(tinyCampaignBenchmark(scenarioPath), false, seed),
      trackedNation_(benchmarkNation(trackedNationId)) {
    if (!initial_.nations.contains(trackedNation_))
        throw std::runtime_error("Unknown tracked benchmark nation");
}

double JapanTrainingEnv::finalReward() const {
    int territorial = 0;
    for (const auto &[zone, land] : engine().state().territories)
        if (land.possessor == trackedNation_)
            territorial += campaign::effectiveTerritorialIpp(engine().state(), zone);
    return territorial + 0.1 * unitValueFor(trackedNation_) +
           0.1 * enemyUnitValueDestroyedByNation(trackedNation_);
}

} // namespace game
