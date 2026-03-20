#pragma once

#include "game/action.hpp"
#include "game/game_state.hpp"

#include <string>
#include <vector>

namespace game {

class ActionEncoder {
  public:
    static ActionEncoder forNation(const GameState& gameState, std::string trackedNationId);

    std::vector<double> encode(const Action& action) const;
    std::vector<std::string> featureLabels() const;
    std::size_t featureCount() const;

    const std::vector<std::string>& zoneOrder() const { return zoneOrder_; }
    const std::string& trackedNationId() const { return trackedNationId_; }
    int maxCombatUnitCount() const { return maxCombatUnitCount_; }

  private:
    std::string trackedNationId_;
    std::vector<std::string> zoneOrder_;
    int maxCombatUnitCount_ {1};
};

}  // namespace game
