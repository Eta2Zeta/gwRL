#pragma once

#include "game/action_encoder.hpp"
#include "game/mdp.hpp"
#include "game/setup_loader.hpp"
#include "game/state_encoder.hpp"

#include <filesystem>
#include <string>
#include <vector>

namespace game {

class JapanTrainingEnv {
  public:
    explicit JapanTrainingEnv(std::filesystem::path scenarioPath, std::string trackedNationId = "Japan");

    void reset();

    bool isTerminal() const { return gameState_.isTerminal(); }
    std::string currentNation() const { return std::string(gameState_.currentNation()); }
    std::string currentPhase() const { return std::string(toString(gameState_.currentPhase())); }

    std::vector<Action> legalActions() const;
    std::vector<double> encodeState() const;
    std::vector<std::vector<double>> encodeLegalActions() const;
    std::vector<std::string> stateFeatureLabels() const;
    std::vector<std::string> actionFeatureLabels() const;

    StepResult step(const Action& action);
    double finalReward() const;

    int completedTurnsFor(std::string_view nationId) const { return gameState_.completedTurnsFor(nationId); }
    int nationIncome(std::string_view nationId) const { return gameState_.nation(nationId).income(); }
    int nationTreasury(std::string_view nationId) const { return gameState_.nation(nationId).treasury(); }
    int unitCountFor(std::string_view nationId) const { return gameState_.unitCountFor(nationId); }

  private:
    void advanceUntilTrackedNationDecision();

    std::filesystem::path scenarioPath_;
    std::string trackedNationId_;
    SimplifiedChinaMdp mdp_;
    GameState gameState_;
    StateEncoder stateEncoder_;
    ActionEncoder actionEncoder_;
};

}  // namespace game
