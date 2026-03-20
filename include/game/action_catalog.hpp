#pragma once

#include "game/action.hpp"
#include "game/game_state.hpp"

#include <string>
#include <unordered_map>
#include <vector>

namespace game {

class ActionCatalog {
  public:
    static ActionCatalog forNation(const GameState& gameState, std::string nationId);

    const Action& actionAt(int actionId) const;
    int indexOf(const Action& action) const;
    std::vector<int> legalActionIds(const std::vector<Action>& legalActions) const;
    std::size_t size() const { return entries_.size(); }

    static std::string signature(const Action& action);

  private:
    std::vector<Action> entries_;
    std::unordered_map<std::string, int> indexBySignature_;
};

}  // namespace game
