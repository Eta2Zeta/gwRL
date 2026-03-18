#pragma once

#include "game/game_state.hpp"

#include <filesystem>

namespace game {

class SetupLoader {
  public:
    static GameState loadFromFile(const std::filesystem::path& filePath);
};

}  // namespace game
