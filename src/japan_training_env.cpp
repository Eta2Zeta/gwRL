#include "game/japan_training_env.hpp"

#include <algorithm>
#include <stdexcept>

namespace game {

namespace {

const Action& selectAutoplayAction(
    const std::vector<Action>& actions,
    std::string_view currentNation,
    std::string_view trackedNation) {
    const auto endPhaseIt = std::find_if(
        actions.begin(),
        actions.end(),
        [](const Action& action) {
            return action.kind == ActionKind::EndPhase;
        });

    if (currentNation != trackedNation && endPhaseIt != actions.end()) {
        return *endPhaseIt;
    }

    if (actions.size() == 1) {
        return actions.front();
    }

    if (endPhaseIt != actions.end()) {
        return *endPhaseIt;
    }

    return actions.front();
}

}  // namespace

JapanTrainingEnv::JapanTrainingEnv(std::filesystem::path scenarioPath, std::string trackedNationId)
    : scenarioPath_(std::move(scenarioPath)),
      trackedNationId_(std::move(trackedNationId)) {
    const auto initialState = SetupLoader::loadFromFile(scenarioPath_);
    stateEncoder_ = StateEncoder::forNation(initialState, trackedNationId_);
    actionEncoder_ = ActionEncoder::forNation(initialState, trackedNationId_);
    reset();
}

void JapanTrainingEnv::reset() {
    gameState_ = SetupLoader::loadFromFile(scenarioPath_);
    advanceUntilTrackedNationDecision();
}

std::vector<Action> JapanTrainingEnv::legalActions() const {
    return mdp_.legalActions(gameState_);
}

std::vector<double> JapanTrainingEnv::encodeState() const {
    return stateEncoder_.encode(gameState_);
}

std::vector<std::vector<double>> JapanTrainingEnv::encodeLegalActions() const {
    std::vector<std::vector<double>> encodedActions;
    const auto actions = legalActions();
    encodedActions.reserve(actions.size());
    for (const auto& action : actions) {
        encodedActions.push_back(actionEncoder_.encode(action));
    }
    return encodedActions;
}

std::vector<std::string> JapanTrainingEnv::stateFeatureLabels() const {
    return stateEncoder_.featureLabels();
}

std::vector<std::string> JapanTrainingEnv::actionFeatureLabels() const {
    return actionEncoder_.featureLabels();
}

StepResult JapanTrainingEnv::step(const Action& action) {
    if (gameState_.currentNation() != trackedNationId_) {
        throw std::runtime_error("Tracked nation attempted to act while another nation is active");
    }
    const auto result = mdp_.step(gameState_, action);
    advanceUntilTrackedNationDecision();
    return result;
}

double JapanTrainingEnv::finalReward() const {
    return static_cast<double>(gameState_.nation(trackedNationId_).income())
           + 0.1 * static_cast<double>(gameState_.unitCountFor(trackedNationId_));
}

void JapanTrainingEnv::advanceUntilTrackedNationDecision() {
    while (!gameState_.isTerminal()) {
        const auto actions = mdp_.legalActions(gameState_);
        if (actions.empty()) {
            return;
        }
        if (gameState_.currentNation() == trackedNationId_ && actions.size() > 1) {
            return;
        }
        mdp_.step(
            gameState_,
            selectAutoplayAction(actions, gameState_.currentNation(), trackedNationId_));
    }
}

}  // namespace game
