#pragma once

#include "game/game_state.hpp"

#include <string>
#include <vector>

namespace game {

class StateEncoder {
  public:
    static StateEncoder forNation(const GameState& gameState, std::string trackedNationId);

    std::vector<double> encode(const GameState& gameState) const;
    std::string encodeKey(const GameState& gameState) const;
    std::vector<std::string> featureLabels() const;
    std::size_t featureCount() const;

    const std::vector<std::string>& zoneOrder() const { return zoneOrder_; }
    const std::vector<std::string>& controllerOrder() const { return controllerOrder_; }
    const std::vector<std::string>& nationOrder() const { return nationOrder_; }
    const std::string& trackedNationId() const { return trackedNationId_; }

  private:
    std::string trackedNationId_;
    std::vector<std::string> zoneOrder_;
    std::vector<std::string> controllerOrder_;
    std::vector<std::string> nationOrder_;
};

}  // namespace game
