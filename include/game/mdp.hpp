#pragma once

#include "game/action.hpp"
#include "game/game_state.hpp"

#include <optional>
#include <string>
#include <vector>

namespace game {

struct StepResult {
    std::string actingNation;
    Phase phaseBefore {Phase::PurchaseUnits};
    Action action;
    bool terminal {false};
    std::optional<std::string> nextNation;
    std::optional<Phase> nextPhase;
};

class SimplifiedChinaMdp {
  public:
    std::vector<Action> legalActions(const GameState& gameState) const {
        if (gameState.isTerminal()) {
            return {};
        }
        return {Action{ActionKind::EndPhase}};
    }

    StepResult step(GameState& gameState, const Action& action) const {
        if (gameState.isTerminal()) {
            throw std::runtime_error("Cannot step a terminal state");
        }
        if (action.kind != ActionKind::EndPhase) {
            throw std::runtime_error("Unsupported action for simplified MDP");
        }

        StepResult result{
            .actingNation = std::string(gameState.currentNation()),
            .phaseBefore = gameState.currentPhase(),
            .action = action,
        };

        gameState.advancePhase();
        result.terminal = gameState.isTerminal();
        if (!result.terminal) {
            result.nextNation = std::string(gameState.currentNation());
            result.nextPhase = gameState.currentPhase();
        }

        return result;
    }
};

}  // namespace game
