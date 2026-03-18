#pragma once

#include "game/action.hpp"
#include "game/game_state.hpp"

#include <stdexcept>
#include <string>
#include <vector>

namespace game {

class Agent {
  public:
    explicit Agent(std::string nationId) : nationId_(std::move(nationId)) {}
    virtual ~Agent() = default;

    const std::string& nationId() const { return nationId_; }

    virtual Action chooseAction(const GameState& gameState, const std::vector<Action>& legalActions) = 0;

  private:
    std::string nationId_;
};

class PassAgent final : public Agent {
  public:
    explicit PassAgent(std::string nationId) : Agent(std::move(nationId)) {}

    Action chooseAction(const GameState&, const std::vector<Action>& legalActions) override {
        if (legalActions.empty()) {
            throw std::runtime_error("PassAgent was asked to choose from an empty action list");
        }
        return legalActions.front();
    }
};

}  // namespace game
