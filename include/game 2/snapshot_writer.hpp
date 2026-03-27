#pragma once

#include "game/game_state.hpp"

#include <filesystem>

namespace game {

class SnapshotWriter {
  public:
    static void writeState(
        const GameState& gameState,
        const std::filesystem::path& filePath,
        int stepIndex);
};

}  // namespace game
